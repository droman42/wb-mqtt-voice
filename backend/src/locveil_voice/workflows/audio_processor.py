"""
Universal Audio Processor with VAD State Management

This module implements the universal audio processing layer that provides
voice activity detection and voice segment accumulation for the Irene
Voice Assistant. It works identically in both voice trigger modes.

Phase 2 Implementation: State Machine - Universal Audio Processing
"""

import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, AsyncIterator, Awaitable, Callable

from ..intents.models import AudioData
from ..config.models import VADConfig
from ..utils.vad import VADResult
from ..utils.loader import dynamic_loader
from ..utils.audio_helpers import calculate_audio_energy, estimate_optimal_vad_threshold
from ..core.metrics import get_metrics_collector

_PREROLL_MARGIN_FRAMES = 2  # ARCH-18 PR-5: safety frames added to the detection-latency-derived pre-roll

logger = logging.getLogger(__name__)


class VoiceActivityState(Enum):
    """Voice activity detection states for the universal audio processor"""
    SILENCE = "silence"
    VOICE_ONSET = "voice_onset"
    VOICE_ACTIVE = "voice_active"
    VOICE_ENDED = "voice_ended"


@dataclass
class VoiceSegment:
    """Represents a complete voice segment with metadata"""
    audio_chunks: List[AudioData]
    start_timestamp: float
    end_timestamp: float
    total_duration_ms: float
    chunk_count: int
    combined_audio: Optional[AudioData] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    # ARCH-19 (segmenter/raw capture levels) — per-frame VAD verdicts spanning this segment's
    # window (pre-roll → voice-ended): {t_ms, is_voice, energy, threshold}. Empty unless the
    # segmenter was built with collect_vad_frames=True (startup --trace gate). Lets a replay see
    # where VAD fired over the audio and tune [vad.providers.*].
    vad_frames: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds"""
        return self.total_duration_ms / 1000.0
    
    def normalize_for_asr(self, target_rms: float = 0.1) -> 'VoiceSegment':
        """
        Create a copy of this voice segment with normalized audio for ASR processing.
        
        This prevents ASR clipping when VAD was triggered by loud audio.
        
        Args:
            target_rms: Target RMS level for ASR (0.05-0.2 recommended)
            
        Returns:
            New VoiceSegment with normalized audio
        """
        if not self.combined_audio:
            return self
        
        try:
            from locveil_voice.utils.vad import _apply_dynamic_range_compression
            import numpy as np
            
            # Convert audio data to numpy array and normalize to [-1.0, 1.0] range
            audio_int16 = np.frombuffer(self.combined_audio.data, dtype=np.int16)
            audio_array = audio_int16.astype(np.float32) / 32767.0  # Normalize to [-1.0, 1.0]
            
            # Apply dynamic range compression (now works with proper normalized range)
            normalized_array = _apply_dynamic_range_compression(audio_array, target_rms)
            
            # Convert back to int16 range and bytes (no double scaling!)
            normalized_int16 = (normalized_array * 32767.0).astype(np.int16)
            normalized_bytes = normalized_int16.tobytes()
            
            # Create new AudioData with normalized audio
            from locveil_voice.intents.models import AudioData
            normalized_audio = AudioData(
                data=normalized_bytes,
                sample_rate=self.combined_audio.sample_rate,
                channels=self.combined_audio.channels,
                timestamp=self.combined_audio.timestamp
            )
            
            # Create new VoiceSegment with normalized audio
            normalized_segment = VoiceSegment(
                audio_chunks=self.audio_chunks,  # Keep original chunks
                start_timestamp=self.start_timestamp,
                end_timestamp=self.end_timestamp,
                total_duration_ms=self.total_duration_ms,
                chunk_count=self.chunk_count,
                combined_audio=normalized_audio,
                metadata={**self.metadata, 'normalized_for_asr': True, 'target_rms': target_rms}
            )
            
            return normalized_segment
            
        except Exception as e:
            logger.warning(f"Failed to normalize audio for ASR: {e}")
            return self


# Phase 4: AdvancedMetrics removed - all metrics functionality now unified in MetricsCollector
# Any advanced metrics needed should be implemented as methods in MetricsCollector for unified collection

class VoiceSegmenter:
    """
    Handles VAD state management and voice segment accumulation.
    
    This processor provides a universal audio processing layer that works
    identically in both voice trigger modes:
    - With Voice Trigger: VAD → Wake Word Detection → VAD → ASR Processing
    - Without Voice Trigger: VAD → Direct ASR Processing
    
    Key Features:
    - Voice activity detection with hysteresis
    - Voice segment accumulation and buffering
    - Timeout protection for long speech segments
    - Edge case handling (short bursts, continuous speech, cutoffs)
    - Performance monitoring and metrics
    """
    
    def __init__(self, vad_config: VADConfig, collect_vad_frames: bool = False):
        """
        Initialize the universal audio processor.

        Args:
            vad_config: VAD configuration object
            collect_vad_frames: ARCH-19 — when True, retain per-frame VAD verdicts and attach
                them to each completed VoiceSegment (segmenter/raw trace levels). Gated at startup
                by the --trace flag so production traffic pays nothing.
        """
        self.config = vad_config
        self.vad_state = VoiceActivityState.SILENCE

        # ARCH-19: per-frame VAD verdict ring (absolute frame timestamps); sliced per segment on
        # completion. Bounded so a long silence can't grow it unbounded.
        self._collect_vad_frames = collect_vad_frames
        self._vad_verdicts: List[Dict[str, Any]] = []
        
        # Select the VAD provider via entry-points discovery (ARCH-18 PR-2) — replaces the engine
        # if-else; `[vad] default_provider` picks energy / silero / microvad.
        self.vad_engine = self._build_vad_provider(vad_config)
        
        # Voice segment buffering
        self.voice_buffer: List[AudioData] = []
        self.voice_segment_start_time: Optional[float] = None
        
        # Pre-buffering to capture audio before VAD triggers (prevents missing speech onset).
        # ARCH-18 PR-5: the pre-roll is sized LAZILY on the first frame, from the ACTIVE VAD engine's
        # detection latency at the REAL canonical frame duration (no magic ms/frame constant) — the voice
        # segment feeds the wake word, so the pre-roll must cover the onset lag or the wake-word start is
        # clipped. For a frame-count engine (energy) the frame_ms cancels → preroll = frames + margin.
        self.pre_buffer: List[AudioData] = []
        self.pre_buffer_size: Optional[int] = None   # sized on the first frame (see _size_preroll)
        self.voice_segment_start_timestamp: Optional[float] = None
        
        # Timeout and buffer management
        self.max_segment_duration_s = vad_config.max_segment_duration_s
        self.buffer_size_limit = vad_config.buffer_size_frames
        
        # Performance metrics (Phase 1: Unified metrics integration)
        self.metrics_collector = get_metrics_collector()
        
        # Callbacks for voice segment processing
        self.voice_segment_callback: Optional[Callable] = None
        
        logger.info(f"VoiceSegmenter initialized: provider={vad_config.default_provider}, "
                   f"max_segment={vad_config.max_segment_duration_s}s, "
                   f"buffer={vad_config.buffer_size_frames} frames")

    def _build_vad_provider(self, vad_config: VADConfig):
        """Discover + instantiate the configured VAD provider (ARCH-18 PR-2).

        Selection is `[vad] default_provider` resolved through the `locveil_voice.providers.vad` entry-points,
        replacing the old engine if-else. Falls back to `energy` (always available) if the named provider
        isn't registered. The provider config is the (flat) VAD config dict; the chosen provider reads its
        own fields.
        """
        default = getattr(vad_config, "default_provider", None) or "energy"
        all_cfg = vad_config.model_dump() if hasattr(vad_config, "model_dump") else dict(vad_config)
        classes = dynamic_loader.discover_providers("locveil_voice.providers.vad", [default, "energy"])
        provider_cls = classes.get(default) or classes.get("energy")
        if provider_cls is None:
            raise RuntimeError(
                f"No VAD provider '{default}' registered and no 'energy' fallback available"
            )
        name = default if default in classes else "energy"
        if default not in classes:
            logger.warning(f"VAD provider '{default}' not found; falling back to 'energy'")
        provider_cfg = (all_cfg.get("providers") or {}).get(name, {})
        self._provider_cfg = provider_cfg  # the active provider's block (energy params for calibration)
        self._all_provider_cfg = all_cfg.get("providers") or {}  # kept for the energy fallback (ASSET-4)
        provider = provider_cls(provider_cfg)
        logger.info(f"VAD provider: {provider.get_provider_name()}")
        return provider

    async def initialize(self) -> None:
        """Async provider warmup (ASSET-4). Providers that need assets fetch them HERE — through the
        AssetManager (lock, temp+rename, partial-download healing) — never on the per-frame hot path.
        If the configured provider can't come up (model download failed, optional dep missing), fall
        back to `energy` (always available, no assets) so voice detection keeps working instead of
        silently reporting silence every frame."""
        provider = self.vad_engine
        try:
            if await provider.is_available():
                await provider.initialize()
                return
            reason = "provider reports unavailable (missing optional dependency?)"
        except Exception as e:
            reason = str(e)
        if provider.get_provider_name() == "energy":
            raise RuntimeError(f"energy VAD failed to initialize: {reason}")
        logger.error(
            f"VAD provider '{provider.get_provider_name()}' failed to initialize ({reason}); "
            f"falling back to 'energy'"
        )
        classes = dynamic_loader.discover_providers("locveil_voice.providers.vad", ["energy"])
        self._provider_cfg = self._all_provider_cfg.get("energy", {})
        self.vad_engine = classes["energy"](self._provider_cfg)
        await self.vad_engine.initialize()

    def set_voice_segment_callback(self, callback: Callable[[VoiceSegment], None]):
        """
        Set callback function for voice segment processing.
        
        Args:
            callback: Async function to call when voice segment is complete
        """
        self.voice_segment_callback = callback
    
    async def calibrate_vad_threshold(self, calibration_audio: List[AudioData]) -> bool:
        """
        Calibrate VAD threshold using provided audio samples.
        
        Args:
            calibration_audio: List of AudioData samples for calibration
            
        Returns:
            True if calibration was successful, False otherwise
        """
        try:
            success = self.vad_engine.calibrate(calibration_audio)
            if success:
                logger.info("VAD threshold calibration completed successfully")
            else:
                logger.warning("VAD threshold calibration failed")
            return success
        except Exception as e:
            logger.error(f"Error during VAD calibration: {e}")
            return False
    
    def _size_preroll(self, frame: AudioData) -> None:
        """Size the pre-roll from the active VAD engine's detection latency at THIS frame's real duration
        (ARCH-18 PR-5). preroll = ceil(detection_latency_ms / frame_ms) + margin; for a frame-count engine
        the frame_ms cancels → frames + margin. Derived from the canonical frame, no magic ms/frame."""
        samples = len(frame.data) / max(1, frame.channels * 2)  # int16 PCM
        frame_ms = (samples / frame.sample_rate * 1000.0) if frame.sample_rate else 0.0
        if frame_ms <= 0:
            self.pre_buffer_size = _PREROLL_MARGIN_FRAMES
            return
        latency_ms = max(0, int(self.vad_engine.detection_latency_ms(frame_ms)))
        self.pre_buffer_size = math.ceil(latency_ms / frame_ms) + _PREROLL_MARGIN_FRAMES
        logger.info(f"VAD pre-roll sized to {self.pre_buffer_size} frames "
                    f"(frame≈{frame_ms:.0f}ms, detection latency {latency_ms}ms)")

    async def process_audio_chunk(self, audio_data: AudioData) -> Optional[VoiceSegment]:
        """
        Process a single audio chunk and return complete voice segment if available.
        
        This is the main entry point for audio processing. It handles VAD state
        management and voice segment accumulation.
        
        Args:
            audio_data: AudioData chunk to process
            
        Returns:
            VoiceSegment if a complete voice segment is ready, None otherwise
        """
        start_time = time.time()

        try:
            # ARCH-18 PR-5: size the pre-roll from the real (canonical) frame duration on the first frame
            if self.pre_buffer_size is None:
                self._size_preroll(audio_data)

            # Maintain pre-buffer for capturing audio before VAD triggers
            self.pre_buffer.append(audio_data)
            if self.pre_buffer_size and len(self.pre_buffer) > self.pre_buffer_size:
                self.pre_buffer.pop(0)  # Remove oldest frame
            
            # Perform VAD on the audio chunk
            vad_result = self.vad_engine.process_frame(audio_data)

            # ARCH-19: retain the per-frame verdict (absolute ts) for the segmenter/raw trace
            # levels; sliced to the segment window on completion. Off (no cost) unless --trace.
            if self._collect_vad_frames:
                self._vad_verdicts.append({
                    "ts": audio_data.timestamp,
                    "is_voice": bool(vad_result.is_voice),
                    "energy": float(vad_result.energy_level),
                    "threshold": float(getattr(vad_result, "adaptive_threshold", 0.0)),
                })
                cap = (self.buffer_size_limit or 0) + (self.pre_buffer_size or 64) + 64
                if len(self._vad_verdicts) > cap:
                    self._vad_verdicts = self._vad_verdicts[-cap:]

            # Update metrics (Phase 1: Unified metrics integration)
            processing_time = (time.time() - start_time) * 1000
            self.metrics_collector.record_vad_chunk_processed(processing_time, vad_result.is_voice)
            
            # Debug logging every 50 chunks to see activity (Phase 1: Unified metrics integration)
            vad_metrics = self.metrics_collector.get_vad_metrics()
            if vad_metrics["total_chunks_processed"] % 50 == 0:
                logger.debug(f"VAD processed {vad_metrics['total_chunks_processed']} chunks, "
                           f"current energy: {vad_result.energy_level:.6f}, "
                           f"threshold: {vad_result.adaptive_threshold:.6f}, "
                           f"voice detected: {vad_result.is_voice}")
                           
            # Log voice detection events
            if vad_result.is_voice and self.vad_state == VoiceActivityState.SILENCE:
                logger.info(f"🎤 Voice activity detected! Energy: {vad_result.energy_level:.6f}, "
                          f"threshold: {vad_result.adaptive_threshold:.6f}, "
                          f"confidence: {vad_result.confidence:.3f}")
            
            # Phase 5: Update advanced metrics (Phase 1: Unified metrics integration)
            cache_hit = getattr(vad_result, 'cache_hit', False)
            if cache_hit:
                self.metrics_collector.record_vad_cache_hit()
            else:
                self.metrics_collector.record_vad_cache_miss()
            
            # Record quality metrics in unified collector
            self.metrics_collector.record_vad_quality_metrics(
                vad_result.energy_level,
                getattr(vad_result, 'zcr_value', 0.0),
                vad_result.confidence
            )
            
            # Handle state transitions based on VAD result
            voice_segment = await self._handle_vad_state_transition(audio_data, vad_result)
            
            # Check for timeout protection
            if self.voice_buffer and self._is_segment_timeout():
                logger.warning(f"Voice segment timeout after {self.max_segment_duration_s}s, forcing completion")
                self.metrics_collector.record_vad_timeout()
                voice_segment = await self._force_voice_segment_completion()
            
            # Check for buffer overflow protection
            if len(self.voice_buffer) > self.buffer_size_limit:
                logger.warning(f"Voice buffer overflow ({len(self.voice_buffer)} > {self.buffer_size_limit}), forcing completion")
                self.metrics_collector.record_vad_buffer_overflow()
                voice_segment = await self._force_voice_segment_completion()
            
            return voice_segment
            
        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")
            # Reset state on error to prevent corruption
            await self._reset_voice_state()
            return None
    
    async def _handle_vad_state_transition(self, audio_data: AudioData, vad_result: VADResult) -> Optional[VoiceSegment]:
        """
        Handle VAD state transitions and voice segment management.
        
        Args:
            audio_data: Current audio data chunk
            vad_result: VAD detection result
            
        Returns:
            VoiceSegment if voice segment is complete, None otherwise
        """
        previous_state = self.vad_state
        
        # State transition logic (same for both voice trigger modes)
        if self.vad_state == VoiceActivityState.SILENCE and vad_result.is_voice:
            # Voice onset detected
            self.vad_state = VoiceActivityState.VOICE_ONSET
            await self._handle_voice_onset(audio_data, vad_result)
            
        elif self.vad_state in [VoiceActivityState.VOICE_ONSET, VoiceActivityState.VOICE_ACTIVE] and vad_result.is_voice:
            # Voice continues
            self.vad_state = VoiceActivityState.VOICE_ACTIVE
            await self._handle_voice_active(audio_data, vad_result)
            
        elif self.vad_state == VoiceActivityState.VOICE_ACTIVE and not vad_result.is_voice:
            # Voice ended
            self.vad_state = VoiceActivityState.VOICE_ENDED
            voice_segment = await self._handle_voice_ended()
            self.vad_state = VoiceActivityState.SILENCE
            return voice_segment
            
        elif self.vad_state == VoiceActivityState.SILENCE and not vad_result.is_voice:
            # Continue silence - skip processing (already counted in record_vad_chunk_processed)
            pass
        
        # Log state changes for debugging
        if previous_state != self.vad_state:
            logger.debug(f"VAD state transition: {previous_state.value} → {self.vad_state.value} "
                        f"(voice={vad_result.is_voice}, confidence={vad_result.confidence:.3f})")
        
        return None
    
    async def _handle_voice_onset(self, audio_data: AudioData, vad_result: VADResult):
        """
        Handle voice onset - start new voice segment with pre-buffered audio.
        
        Args:
            audio_data: Audio data chunk
            vad_result: VAD detection result
        """
        # Start new voice segment with pre-buffered audio to capture speech onset
        self.voice_buffer = self.pre_buffer.copy()  # Include pre-buffered frames
        if audio_data not in self.voice_buffer:  # Avoid duplicate if current frame already in pre-buffer
            self.voice_buffer.append(audio_data)
        
        self.voice_segment_start_time = time.time()
        self.voice_segment_start_timestamp = audio_data.timestamp
        
        logger.debug(f"Voice onset detected: energy={vad_result.energy_level:.4f}, "
                    f"confidence={vad_result.confidence:.3f}, "
                    f"pre-buffered {len(self.pre_buffer)} frames")
    
    async def _handle_voice_active(self, audio_data: AudioData, vad_result: VADResult):
        """
        Handle ongoing voice activity - accumulate audio data.
        
        Args:
            audio_data: Audio data chunk
            vad_result: VAD detection result
        """
        # Accumulate voice data
        self.voice_buffer.append(audio_data)
        
        # Log periodic status for long segments
        if len(self.voice_buffer) % 20 == 0:  # Every ~500ms at 25ms chunks
            duration = time.time() - self.voice_segment_start_time if self.voice_segment_start_time else 0
            logger.debug(f"Voice segment active: {len(self.voice_buffer)} chunks, {duration:.1f}s duration")
    
    def _collect_segment_vad_frames(self, start_ts: float, end_ts: float) -> List[Dict[str, Any]]:
        """Slice the retained VAD verdicts to this segment's window, re-based to t_ms from start.

        Returns [] when not collecting. Consumes the used (and now-stale older) verdicts so the
        ring doesn't carry a finished segment's frames into the next one.
        """
        if not self._collect_vad_frames or not self._vad_verdicts:
            return []
        frames = [
            {"t_ms": round(max(0.0, (v["ts"] - start_ts)) * 1000),
             "is_voice": v["is_voice"], "energy": v["energy"], "threshold": v["threshold"]}
            for v in self._vad_verdicts if start_ts <= v["ts"] <= end_ts
        ]
        # drop everything up to and including this segment's end
        self._vad_verdicts = [v for v in self._vad_verdicts if v["ts"] > end_ts]
        return frames

    async def _handle_voice_ended(self) -> Optional[VoiceSegment]:
        """
        Handle voice end - create complete voice segment.

        Returns:
            Complete VoiceSegment object
        """
        if not self.voice_buffer:
            logger.warning("Voice ended but no audio buffer available")
            return None
        
        # Calculate segment metadata
        end_time = time.time()
        end_timestamp = self.voice_buffer[-1].timestamp
        chunk_count = len(self.voice_buffer)
        
        # Calculate duration based on actual audio data (FIXED: was using wall-clock time difference)
        # This ensures the duration reflects the actual audio content, not processing time
        if self.voice_buffer:
            first_chunk = self.voice_buffer[0]
            total_audio_bytes = sum(len(chunk.data) for chunk in self.voice_buffer)
            bytes_per_sample = 2  # 16-bit PCM = 2 bytes per sample
            total_samples = total_audio_bytes // (bytes_per_sample * first_chunk.channels)
            total_duration_ms = (total_samples / first_chunk.sample_rate) * 1000
            
            # Debug logging to verify the fix
            wall_clock_duration_ms = (end_time - self.voice_segment_start_time) * 1000 if self.voice_segment_start_time else 0
            logger.debug(f"Voice segment creation: {chunk_count} chunks, {total_audio_bytes} bytes")
            logger.debug(f"Duration calculation - Data-based: {total_duration_ms:.1f}ms, Wall-clock: {wall_clock_duration_ms:.1f}ms")
            if abs(total_duration_ms - wall_clock_duration_ms) > 100:  # More than 100ms difference
                logger.info(f"⚠️ Voice segment duration fix applied: {wall_clock_duration_ms:.1f}ms → {total_duration_ms:.1f}ms")
        else:
            total_duration_ms = 0
        
        # Create voice segment
        voice_segment = VoiceSegment(
            audio_chunks=self.voice_buffer.copy(),
            start_timestamp=self.voice_segment_start_timestamp or 0,
            end_timestamp=end_timestamp,
            total_duration_ms=total_duration_ms,
            chunk_count=chunk_count,
            metadata={
                'vad_state_transitions': True,
                'chunk_size_bytes': sum(len(chunk.data) for chunk in self.voice_buffer),
                'average_energy': sum(calculate_audio_energy(chunk) for chunk in self.voice_buffer) / chunk_count,
                'processing_mode': 'universal_vad'
            }
        )
        
        # Combine audio chunks into single AudioData
        voice_segment.combined_audio = await self._combine_audio_buffer(self.voice_buffer)

        # ARCH-19: attach the per-frame VAD verdicts spanning this segment (segmenter/raw levels)
        voice_segment.vad_frames = self._collect_segment_vad_frames(
            voice_segment.start_timestamp, end_timestamp)

        # Update metrics (Phase 1: Unified metrics integration)
        self.metrics_collector.record_vad_voice_segment(total_duration_ms)
        
        # Phase 5: Advanced voice segment metrics now handled in unified collector
        # All metrics are recorded via record_vad_voice_segment() above
        
        # Reset voice state
        await self._reset_voice_state()
        
        logger.info(f"Voice segment completed: {chunk_count} chunks, {total_duration_ms:.1f}ms duration, "
                   f"{len(voice_segment.combined_audio.data)} bytes")
        
        return voice_segment
    
    async def _force_voice_segment_completion(self) -> Optional[VoiceSegment]:
        """
        Force completion of current voice segment (timeout/overflow protection).
        
        Returns:
            VoiceSegment if buffer contains data, None otherwise
        """
        if not self.voice_buffer:
            return None
        
        logger.debug("Forcing voice segment completion due to timeout/overflow")
        
        # Temporarily set state to VOICE_ENDED to trigger completion
        self.vad_state = VoiceActivityState.VOICE_ENDED
        
        voice_segment = await self._handle_voice_ended()
        
        # Return to SILENCE state
        self.vad_state = VoiceActivityState.SILENCE
        
        return voice_segment
    
    async def _reset_voice_state(self):
        """Reset voice processing state."""
        self.voice_buffer.clear()
        self.voice_segment_start_time = None
        self.voice_segment_start_timestamp = None
        self.vad_state = VoiceActivityState.SILENCE
    
    def _is_segment_timeout(self) -> bool:
        """Check if current voice segment has exceeded timeout."""
        if not self.voice_segment_start_time:
            return False
        
        duration = time.time() - self.voice_segment_start_time
        return duration > self.max_segment_duration_s
    
    async def _combine_audio_buffer(self, audio_chunks: List[AudioData]) -> AudioData:
        """
        Combine multiple audio chunks into a single AudioData object.
        
        Args:
            audio_chunks: List of AudioData chunks to combine
            
        Returns:
            Combined AudioData object
        """
        if not audio_chunks:
            raise ValueError("Cannot combine empty audio buffer")
        
        if len(audio_chunks) == 1:
            return audio_chunks[0]
        
        # Combine audio data
        combined_data = b''.join(chunk.data for chunk in audio_chunks)
        
        # Use metadata from first chunk as base
        first_chunk = audio_chunks[0]
        last_chunk = audio_chunks[-1]
        
        # Calculate total duration based on actual audio data size (FIXED: was using timestamp difference)
        # This fixes the critical bug where timestamp differences don't reflect actual audio content duration
        bytes_per_sample = 2  # 16-bit PCM = 2 bytes per sample
        total_samples = len(combined_data) // (bytes_per_sample * first_chunk.channels)
        duration_ms = (total_samples / first_chunk.sample_rate) * 1000
        
        # Debug logging to verify the fix
        timestamp_duration_ms = (last_chunk.timestamp - first_chunk.timestamp) * 1000
        logger.debug(f"Audio combination: {len(audio_chunks)} chunks, {len(combined_data)} bytes")
        logger.debug(f"Duration calculation - Data-based: {duration_ms:.1f}ms, Timestamp-based: {timestamp_duration_ms:.1f}ms")
        if abs(duration_ms - timestamp_duration_ms) > 100:  # More than 100ms difference
            logger.info(f"⚠️ Duration calculation fix applied: {timestamp_duration_ms:.1f}ms → {duration_ms:.1f}ms")
        
        return AudioData(
            data=combined_data,
            timestamp=first_chunk.timestamp,
            sample_rate=first_chunk.sample_rate,
            channels=first_chunk.channels,
            format=first_chunk.format,
            metadata={
                **first_chunk.metadata,
                'combined_chunks': len(audio_chunks),
                'total_duration_ms': duration_ms,
                'chunk_timestamps': [chunk.timestamp for chunk in audio_chunks],
                'vad_processed': True
            }
        )
    
    async def process_audio_stream(self, audio_stream: AsyncIterator[AudioData]) -> AsyncIterator[VoiceSegment]:
        """
        Process an entire audio stream and yield voice segments.
        
        Args:
            audio_stream: Async iterator of AudioData chunks
            
        Yields:
            VoiceSegment objects when complete voice segments are detected
        """
        async for audio_data in audio_stream:
            voice_segment = await self.process_audio_chunk(audio_data)
            
            if voice_segment:
                yield voice_segment
                
                # Call callback if configured
                if self.voice_segment_callback:
                    try:
                        await self.voice_segment_callback(voice_segment)
                    except Exception as e:
                        logger.error(f"Error in voice segment callback: {e}")
    
    def get_processing_metrics(self) -> Dict[str, Any]:
        """Get current processing metrics from unified collector."""
        return self.metrics_collector.get_vad_metrics()
    
    # Phase 4: reset_metrics() removed - use MetricsCollector.reset_metrics() for unified metrics reset
    
    def get_current_state(self) -> Dict[str, Any]:
        """
        Get current processor state for debugging/monitoring.
        
        Returns:
            Dictionary with current state information
        """
        return {
            'vad_state': self.vad_state.value,
            'buffer_size': len(self.voice_buffer),
            'segment_duration_s': (
                time.time() - self.voice_segment_start_time 
                if self.voice_segment_start_time else 0
            ),
            'metrics': self.metrics_collector.get_vad_metrics(),
            'config': {
                'threshold': self._provider_cfg.get('energy_threshold', self.vad_engine.threshold),
                'sensitivity': self._provider_cfg.get('sensitivity', 0.0),
                'max_duration_s': self.config.max_segment_duration_s,
                'buffer_limit': self.config.buffer_size_frames
            }
        }
    
    def get_advanced_metrics(self) -> Dict[str, Any]:
        """Get Phase 5 advanced metrics from unified collector."""
        # Calculate efficiency metrics and record them
        vad_metrics = self.metrics_collector.get_vad_metrics()
        audio_duration_ms = vad_metrics["total_chunks_processed"] * 23  # Assuming 23ms chunks
        buffer_ratio = len(self.voice_buffer) / max(1, self.config.buffer_size_frames)
        
        # Calculate efficiency metrics
        if audio_duration_ms > 0:
            real_time_factor = vad_metrics["total_processing_time_ms"] / audio_duration_ms
            processing_efficiency = 1.0 / max(real_time_factor, 0.001)  # Avoid division by zero
        else:
            real_time_factor = 0.0
            processing_efficiency = 1.0
        
        # Record efficiency metrics to unified collector
        self.metrics_collector.record_vad_efficiency(real_time_factor, processing_efficiency, buffer_ratio)
        
        # Return advanced metrics from unified collector
        return self.metrics_collector.get_vad_advanced_metrics()
    
    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics from unified collector (Phase 1: Complete integration)."""
        basic_metrics = self.get_processing_metrics()
        advanced_metrics = self.get_advanced_metrics()
        
        return {
            'basic_metrics': basic_metrics,
            'advanced_metrics': advanced_metrics,
            'performance_overview': {
                'efficiency_score': advanced_metrics.get('processing_efficiency', 0.0),
                'real_time_factor': advanced_metrics.get('real_time_factor', 0.0),
                'cache_effectiveness': basic_metrics.get('cache_hit_rate', 0.0),
                'detection_stability': advanced_metrics.get('average_confidence', 0.0)
            }
        }
    
    # Phase 4: reset_advanced_metrics() removed - use MetricsCollector.reset_metrics() for unified metrics reset
    
    async def calibrate_threshold(self, calibration_audio: List[AudioData], 
                                noise_percentile: Optional[int] = None) -> float:
        """
        Calibrate VAD threshold based on environment audio samples.
        
        Args:
            calibration_audio: List of audio samples for calibration
            noise_percentile: Percentile for noise estimation (uses config default if None)
            
        Returns:
            Suggested optimal threshold
        """
        if noise_percentile is None:
            noise_percentile = int(self._provider_cfg.get('noise_percentile', 15))

        optimal_threshold = estimate_optimal_vad_threshold(
            calibration_audio,
            noise_percentile=noise_percentile,
            voice_multiplier=float(self._provider_cfg.get('voice_multiplier', 3.0))
        )

        logger.info(f"VAD threshold calibration: current={self.vad_engine.threshold:.4f}, "
                   f"suggested={optimal_threshold:.4f}")
        
        return optimal_threshold
    
    def update_threshold(self, new_threshold: float):
        """
        Update VAD threshold dynamically.
        
        Args:
            new_threshold: New threshold value (0.0-1.0)
        """
        if not 0.0 <= new_threshold <= 1.0:
            raise ValueError(f"Threshold must be between 0.0 and 1.0, got {new_threshold}")
        
        old_threshold = self.vad_engine.threshold
        # Update the active VAD provider's threshold (the engine owns it now).
        self.vad_engine.threshold = new_threshold
        
        logger.info(f"VAD threshold updated: {old_threshold:.4f} → {new_threshold:.4f}")


# Integration interface for workflows

class AudioProcessorInterface:
    """
    Interface for workflow integration with the universal audio processor.
    
    This provides a clean handoff to existing ASR/voice trigger components
    while maintaining backward compatibility.
    """
    
    def __init__(self, vad_config: VADConfig, collect_vad_frames: bool = False):
        """
        Initialize audio processor interface.

        Args:
            vad_config: VAD configuration object
            collect_vad_frames: ARCH-19 — retain per-frame VAD verdicts on each VoiceSegment
                (segmenter/raw trace levels). Defaults off; set from the startup --trace gate.
        """
        self.processor = VoiceSegmenter(vad_config, collect_vad_frames=collect_vad_frames)
        self.vad_config = vad_config  # Store config for normalization settings

    async def initialize(self) -> None:
        """Warm up the VAD provider (asset download / fallback) — see VoiceSegmenter.initialize (ASSET-4)."""
        await self.processor.initialize()

    async def process_audio_pipeline(self, 
                                   audio_stream: AsyncIterator[AudioData],
                                   context: Any,  # RequestContext
                                   voice_segment_handler: Callable[[VoiceSegment, Any], Awaitable[None]]) -> AsyncIterator[VoiceSegment]:
        """
        Process audio pipeline with VAD integration.
        
        This method provides the main integration point for workflows to use
        VAD processing with clean handoff to existing components.
        
        Args:
            audio_stream: Input audio stream 
            context: Request context from workflow
            voice_segment_handler: Handler function for complete voice segments
            
        Yields:
            VoiceSegment objects for further processing
        """
        # Use VAD processing (always enabled)
        logger.debug("Using universal VAD audio processing")
        async for voice_segment in self.processor.process_audio_stream(audio_stream):
            # Call workflow handler
            try:
                await voice_segment_handler(voice_segment, context)
            except Exception as e:
                logger.error(f"Error in voice segment handler: {e}")
            
            yield voice_segment
    
    async def process_voice_segment_for_mode(self, 
                                           voice_segment: VoiceSegment, 
                                           context: Any,  # RequestContext
                                           asr_component = None,
                                           voice_trigger_component = None,
                                           wake_word_detected: bool = False) -> Dict[str, Any]:
        """
        Process voice segment according to the current mode (with/without wake word).
        
        This implements the mode-specific processing logic from the VAD design:
        - Mode A (skip_wake_word=False): Wake word detection first, then ASR
        - Mode B (skip_wake_word=True): Direct ASR processing
        
        Args:
            voice_segment: Complete voice segment to process
            context: Request context
            asr_component: ASR component instance
            voice_trigger_component: Voice trigger component instance  
            wake_word_detected: Current wake word detection state
            
        Returns:
            Processing result dictionary
        """
        combined_audio = voice_segment.combined_audio
        
        if context.skip_wake_word:
            # Mode B: Direct ASR processing
            logger.debug("Mode B: Direct ASR processing of voice segment")
            
            if asr_component:
                try:
                    # Try normalized audio first (if enabled), with fallback to original
                    asr_result = ""
                    audio_processing_method = "original"
                    
                    if getattr(self.vad_config, 'normalize_for_asr', True):
                        target_rms = getattr(self.vad_config, 'asr_target_rms', 0.15)
                        normalized_segment = voice_segment.normalize_for_asr(target_rms=target_rms)
                        audio_for_asr = normalized_segment.combined_audio
                        logger.debug(f"Audio normalized for ASR (target RMS: {target_rms})")
                        
                        # Try normalized audio first
                        asr_result = await asr_component.process_audio(audio_for_asr)
                        audio_processing_method = "normalized"
                        
                        # Fallback to original audio if normalization produced empty result
                        if (not asr_result or not asr_result.strip()) and getattr(self.vad_config, 'enable_fallback_to_original', True):
                            logger.debug("Normalized audio produced empty result, trying original audio")
                            asr_result = await asr_component.process_audio(combined_audio)
                            audio_processing_method = "fallback_original"
                    else:
                        logger.debug("Audio normalization disabled, using original audio")
                        asr_result = await asr_component.process_audio(combined_audio)
                    
                    logger.debug(f"ASR processing method: {audio_processing_method}")
                    return {
                        'type': 'asr_result',
                        'result': asr_result,
                        'voice_segment': voice_segment,
                        'mode': 'direct_asr',
                        'audio_processing_method': audio_processing_method
                    }
                except Exception as e:
                    logger.error(f"ASR processing failed: {e}")
                    # Reset ASR provider state after processing failure
                    if asr_component and hasattr(asr_component, 'reset_provider_state'):
                        asr_component.reset_provider_state()
                        logger.debug("Reset ASR provider state after processing failure")
                    return {
                        'type': 'error',
                        'error': str(e),
                        'voice_segment': voice_segment
                    }
            else:
                logger.warning("ASR component not available for Mode B processing")
                return {
                    'type': 'error',
                    'error': 'ASR component not available',
                    'voice_segment': voice_segment
                }
        else:
            # Mode A: Wake word detection first
            if not wake_word_detected:
                logger.debug("Mode A: Wake word detection on voice segment")
                
                if voice_trigger_component:
                    try:
                        wake_result = await voice_trigger_component.process_audio(combined_audio)
                        return {
                            'type': 'wake_word_result',
                            'result': wake_result,
                            'voice_segment': voice_segment,
                            'mode': 'wake_word_detection'
                        }
                    except Exception as e:
                        logger.error(f"Wake word detection failed: {e}")
                        return {
                            'type': 'error',
                            'error': str(e),
                            'voice_segment': voice_segment
                        }
                else:
                    logger.warning("Voice trigger component not available for Mode A processing")
                    return {
                        'type': 'error',
                        'error': 'Voice trigger component not available',
                        'voice_segment': voice_segment
                    }
            else:
                # Wake word already detected, process as command
                logger.debug("Mode A: ASR processing of command after wake word")
                
                if asr_component:
                    try:
                        # Try normalized audio first (if enabled), with fallback to original
                        asr_result = ""
                        audio_processing_method = "original"
                        
                        if getattr(self.vad_config, 'normalize_for_asr', True):
                            target_rms = getattr(self.vad_config, 'asr_target_rms', 0.15)
                            normalized_segment = voice_segment.normalize_for_asr(target_rms=target_rms)
                            audio_for_asr = normalized_segment.combined_audio
                            logger.debug(f"Audio normalized for ASR (target RMS: {target_rms})")
                            
                            # Try normalized audio first
                            asr_result = await asr_component.process_audio(audio_for_asr)
                            audio_processing_method = "normalized"
                            
                            # Fallback to original audio if normalization produced empty result
                            if (not asr_result or not asr_result.strip()) and getattr(self.vad_config, 'enable_fallback_to_original', True):
                                logger.debug("Normalized audio produced empty result, trying original audio")
                                asr_result = await asr_component.process_audio(combined_audio)
                                audio_processing_method = "fallback_original"
                        else:
                            logger.debug("Audio normalization disabled, using original audio")
                            asr_result = await asr_component.process_audio(combined_audio)
                        
                        logger.debug(f"ASR processing method: {audio_processing_method}")
                        return {
                            'type': 'asr_result',
                            'result': asr_result,
                            'voice_segment': voice_segment,
                            'mode': 'command_after_wake',
                            'audio_processing_method': audio_processing_method
                        }
                    except Exception as e:
                        logger.error(f"ASR processing failed: {e}")
                        # Reset ASR provider state after processing failure
                        if asr_component and hasattr(asr_component, 'reset_provider_state'):
                            asr_component.reset_provider_state()
                            logger.debug("Reset ASR provider state after command processing failure")
                        return {
                            'type': 'error',
                            'error': str(e),
                            'voice_segment': voice_segment
                        }
                else:
                    logger.warning("ASR component not available for command processing")
                    return {
                        'type': 'error',
                        'error': 'ASR component not available',
                        'voice_segment': voice_segment
                    }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get processing metrics from the audio processor."""
        return self.processor.get_processing_metrics()
    
    def get_state(self) -> Dict[str, Any]:
        """Get current processor state."""
        return self.processor.get_current_state()
    
    async def calibrate(self, calibration_audio: List[AudioData]) -> float:
        """Calibrate VAD threshold based on environment."""
        return await self.processor.calibrate_threshold(calibration_audio)


# Export public interface - Phase 4: ProcessingMetrics removed, metrics now unified in MetricsCollector
__all__ = [
    'VoiceActivityState',
    'VoiceSegment',
    'VoiceSegmenter',
    'AudioProcessorInterface',
]
