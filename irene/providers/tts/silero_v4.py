"""
Silero v4 TTS Provider - Neural text-to-speech using Silero models v4

Similar to SileroV3TTSProvider but using Silero v4 models with enhanced features.
Provides high-quality multilingual neural TTS using Silero v4 models.

CR-C6: shared logic lives in `silero_base.SileroTTSBase`; this module overrides only the
v4-specific bits (model URLs/directory, speaker list, soundfile-based synthesis).
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any

from .silero_base import SileroTTSBase
from ...utils.audio_stream import PCMStream, float_to_pcm16
from ...utils.torch_model_cache import TorchModelCache

logger = logging.getLogger(__name__)


class SileroV4TTSProvider(SileroTTSBase):
    """
    Silero v4 TTS provider for high-quality neural text-to-speech.

    Features:
    - High-quality neural TTS using Silero v4 models
    - Enhanced multilingual support
    - Multiple speakers and languages
    - Improved quality and naturalness
    - Async model loading and speech generation
    - Model caching optimization for performance
    """

    # Class-level model cache for sharing across instances
    _model_cache = TorchModelCache()  # class-level cache shared across instances (ARCH-24 T5)

    # Version-specific defaults (see SileroTTSBase)
    _version = "v4"
    _default_model_id = "v4_ru"
    _default_sample_rate = 48000
    _default_speakers = ["xenia", "aidar", "baya", "kseniya", "eugene", "random"]
    _model_info_id = "v4_ru"

    @classmethod
    def _get_default_directory(cls) -> str:
        """Silero v4 directory for model storage"""
        return "silero_v4"

    @classmethod
    def _get_default_model_urls(cls) -> Dict[str, str]:
        """Silero v4 model URLs. ASSET-2 (verified 2026-06-03): silero's v4 line is Russian-only —
        v4_en/de/es/fr were declared but 404 (they never shipped; those languages stay at v3). Use the
        silero_v3 provider for non-Russian TTS (its en/de/es models are live)."""
        return {
            "v4_ru": "https://models.silero.ai/models/tts/ru/v4_ru.pt",
        }

    async def synthesize_to_file(self, text: str, output_path: Path, **kwargs) -> None:
        """Convert text to speech and save to audio file"""
        if not self._available:
            raise RuntimeError("Silero v4 TTS provider not available")

        # Extract parameters
        speaker = kwargs.get('speaker', self.default_speaker)
        sample_rate = kwargs.get('sample_rate', self.sample_rate)

        # Validate speaker
        if speaker not in self._speakers:
            logger.warning(f"Unknown speaker: {speaker}, using default: {self.default_speaker}")
            speaker = self.default_speaker

        # Generate speech using Silero v4 model
        try:
            # Ensure model is loaded
            await self._ensure_model_loaded()

            # Normalize text for better pronunciation
            normalized_text = await self._normalize_text_async(text)

            # Generate speech with specified parameters
            await self._generate_speech_async(
                normalized_text, output_path, speaker, sample_rate
            )

            logger.info(f"Silero v4 speech generated: {output_path}")

        except Exception as e:
            logger.error(f"Failed to generate Silero v4 speech: {e}")
            raise RuntimeError(f"TTS generation failed: {e}")

    async def synthesize_to_stream(self, text: str, **kwargs) -> PCMStream:
        """Native streaming override (ARCH-21): Silero already produces the waveform in memory via
        `apply_tts` (the same call `synthesize_to_file` uses), so yield it as int16 PCM directly — no
        WAV round-trip."""
        if not self._available:
            raise RuntimeError("Silero v4 TTS provider not available")

        speaker = kwargs.get('speaker', self.default_speaker)
        sample_rate = kwargs.get('sample_rate', self.sample_rate)
        if speaker not in self._speakers:
            logger.warning(f"Unknown speaker: {speaker}, using default: {self.default_speaker}")
            speaker = self.default_speaker

        await self._ensure_model_loaded()
        normalized_text = await self._normalize_text_async(text)
        pcm = await asyncio.to_thread(self._synthesize_pcm_blocking, normalized_text, speaker, sample_rate)

        async def _frames():
            yield pcm

        return PCMStream(sample_rate=sample_rate, channels=1, sample_width=2, frames=_frames())

    def _synthesize_pcm_blocking(self, text: str, speaker: str, sample_rate: int) -> bytes:
        """Run Silero v4 `apply_tts` and convert the waveform to int16 PCM (called from a thread)."""
        if not self._model:
            raise RuntimeError("Silero v4 model not loaded")
        audio = self._model.apply_tts(text=text, speaker=speaker, sample_rate=sample_rate)
        samples = audio.detach().cpu().numpy() if hasattr(audio, "detach") else audio
        return float_to_pcm16(samples)

    def get_capabilities(self) -> Dict[str, Any]:
        """Return provider capabilities information"""
        return {
            "languages": ["ru-RU", "en-US"],
            "voices": self._speakers,
            "formats": ["wav"],
            "features": [
                "neural_synthesis",
                "multi_speaker",
                "multilingual",
                "high_quality",
                "async_generation"
            ],
            "quality": "very_high",
            "speed": "medium"
        }

    def get_provider_name(self) -> str:
        """Get unique provider identifier"""
        return "silero_v4"

    async def _load_model_async(self) -> None:
        """Load Silero v4 model asynchronously"""
        # Ensure model file exists
        self.model_file.parent.mkdir(parents=True, exist_ok=True)

        if not self.model_file.exists():
            # Get model info from asset manager
            model_info = self.asset_manager.get_model_info("silero", "v4_ru")
            if model_info:
                logger.info(f"Downloading Silero v4 model (size: {model_info.get('size', 'unknown')})")

            try:
                # Try asset manager download first
                downloaded_path = await self.asset_manager.download_model("silero_v4", self.model_id)
                if downloaded_path != self.model_file:
                    # Copy to expected location if different
                    import shutil
                    shutil.copy2(downloaded_path, self.model_file)
            except Exception as e:
                logger.warning(f"Asset manager download failed, using legacy method: {e}")
                await asyncio.to_thread(self._download_model, self.model_file)

        # Load model
        logger.info(f"Loading Silero v4 model from {self.model_file}...")
        await asyncio.to_thread(self._load_model, self.model_file)


    async def _generate_speech_async(self, text: str, output_path: Path,
                                   speaker: str, sample_rate: int) -> None:
        """Generate speech asynchronously"""
        await asyncio.to_thread(
            self._generate_speech_blocking,
            text, output_path, speaker, sample_rate
        )

    def _generate_speech_blocking(self, text: str, output_path: Path,
                                speaker: str, sample_rate: int) -> None:
        """Generate speech in blocking mode (called from thread)"""
        if not self._model or not self._torch:
            raise RuntimeError("Model not loaded or torch not available")

        try:
            # Generate audio data using Silero v4 model
            audio_data = self._model.apply_tts(
                text=text,
                speaker=speaker,
                sample_rate=sample_rate
            )

            # Convert to appropriate format and save
            import soundfile as sf  # type: ignore
            sf.write(str(output_path), audio_data, sample_rate)

            logger.debug(f"Generated speech file: {output_path}")

        except Exception as e:
            logger.error(f"Speech generation failed: {e}")
            raise
