"""
Silero v3 TTS Provider - Neural text-to-speech using Silero models v3

Converted from irene/plugins/builtin/silero_v3_tts_plugin.py to provider pattern.
Provides high-quality Russian neural TTS using Silero v3.1 models.

CR-C6: shared logic lives in `silero_base.SileroTTSBase`; this module overrides only the
v3-specific bits (model URLs/directory, speaker-by-assistant-name handling, accent/yo synthesis).
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any

from .silero_base import SileroTTSBase
from ...utils.audio_stream import PCMStream, float_to_pcm16
from ...utils.torch_model_cache import TorchModelCache

logger = logging.getLogger(__name__)


class SileroV3TTSProvider(SileroTTSBase):
    """
    Silero v3 TTS provider for high-quality neural text-to-speech.

    Features:
    - High-quality neural TTS using Silero v3.1 models
    - Multiple Russian speakers (xenia, aidar, baya, kseniya, eugene)
    - Text normalization and accent placement
    - Async model loading and speech generation
    - Speaker selection based on configuration
    - Graceful handling of missing dependencies
    - Model caching optimization for performance

    Enhanced in TODO #4 Phase 1 with intelligent asset defaults.
    """

    # Class-level model cache for sharing across instances
    _model_cache = TorchModelCache()  # class-level cache shared across instances (ARCH-24 T5)

    # Version-specific defaults (see SileroTTSBase)
    _version = "v3"
    _default_model_id = "v3_ru"
    _default_sample_rate = 24000
    _default_speakers = ["xenia", "aidar", "baya", "kseniya", "eugene"]
    _model_info_id = "v3_ru"

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize SileroV3TTSProvider with configuration.

        Args:
            config: Provider configuration including model_path, default_speaker, etc.
        """
        super().__init__(config)
        # v3-specific synthesis controls
        self.put_accent = config.get("put_accent", True)
        self.put_yo = config.get("put_yo", True)
        self.threads = config.get("threads", 4)

        # Speaker mapping based on assistant name
        self.speaker_by_assname = config.get("speaker_by_assname", {
            "николай|николаю": "aidar",
            "ирина|ирине": "xenia"
        })

    @classmethod
    def _get_default_directory(cls) -> str:
        """Silero v3 models stored in dedicated silero directory"""
        return "silero"

    @classmethod
    def _get_default_model_urls(cls) -> Dict[str, str]:
        """Default Silero v3 model URLs"""
        return {
            "v3_ru": "https://models.silero.ai/models/tts/ru/v3_1_ru.pt",
            "v3_en": "https://models.silero.ai/models/tts/en/v3_en.pt",
            "v3_de": "https://models.silero.ai/models/tts/de/v3_de.pt",
            "v3_es": "https://models.silero.ai/models/tts/es/v3_es.pt"
        }

    async def synthesize_to_file(self, text: str, output_path: Path, **kwargs) -> None:
        """
        Convert text to speech and save to audio file.

        Args:
            text: Text to convert to speech
            output_path: Path where to save the audio file
            **kwargs: speaker, sample_rate, put_accent, put_yo, core
        """
        if not self._available or not self._model:
            await self._ensure_model_loaded()

        try:
            # Extract parameters
            speaker = kwargs.get('speaker', self.default_speaker)
            sample_rate = kwargs.get('sample_rate', self.sample_rate)
            put_accent = kwargs.get('put_accent', self.put_accent)
            put_yo = kwargs.get('put_yo', self.put_yo)

            # Resolve speaker by assistant name if configured
            core = kwargs.get('core')
            if core and hasattr(core, 'cur_callname'):
                cur_callname = getattr(core, 'cur_callname', '')
                if cur_callname:
                    for name_pattern, mapped_speaker in self.speaker_by_assname.items():
                        name_variants = name_pattern.split('|')
                        if cur_callname.lower() in [n.lower() for n in name_variants]:
                            speaker = mapped_speaker
                            break

            # Validate speaker
            if speaker not in self._speakers:
                logger.warning(f"Unknown speaker: {speaker}, using default: {self.default_speaker}")
                speaker = self.default_speaker

            # Normalize text
            processed_text = await self._normalize_text_async(text)

            logger.debug(f"Generating TTS with speaker: {speaker}, sample_rate: {sample_rate}")

            # Generate speech asynchronously
            await self._generate_speech_async(
                processed_text, output_path, speaker, sample_rate, put_accent, put_yo
            )

        except Exception as e:
            logger.error(f"Failed to generate speech file with Silero v3: {e}")
            raise RuntimeError(f"TTS file generation failed: {e}")


    def get_capabilities(self) -> Dict[str, Any]:
        """Return provider capabilities information"""
        return {
            "languages": ["ru-RU"],
            "voices": self._speakers,
            "formats": ["wav"],
            "features": [
                "neural_synthesis",
                "multi_speaker",
                "stress_placement",
                "text_normalization",
                "async_generation"
            ],
            "quality": "high",
            "speed": "medium"
        }

    def get_provider_name(self) -> str:
        """Get unique provider identifier"""
        return "silero_v3"

    async def _load_model_async(self) -> None:
        """Load Silero model asynchronously using asset management"""
        if not self._torch:
            return

        # Ensure model directory exists
        self.model_file.parent.mkdir(parents=True, exist_ok=True)

        # Download model if not present using asset manager or legacy method
        if not self.model_file.exists():
            logger.info("Downloading Silero v3 model...")

            # Get model info from asset manager
            model_info = self.asset_manager.get_model_info("silero", "v3_ru")
            if model_info:
                logger.info(f"Downloading Silero v3 model (size: {model_info.get('size', 'unknown')})")

            try:
                # Try asset manager download first
                downloaded_path = await self.asset_manager.download_model("silero_v3", self.model_id)
                if downloaded_path != self.model_file:
                    # Copy to expected location if different
                    import shutil
                    shutil.copy2(downloaded_path, self.model_file)
            except Exception as e:
                logger.warning(f"Asset manager download failed, using legacy method: {e}")
                await asyncio.to_thread(self._download_model, self.model_file)

        # Load model
        logger.info(f"Loading Silero v3 model from {self.model_file}...")
        await asyncio.to_thread(self._load_model, self.model_file)

    async def synthesize_to_stream(self, text: str, **kwargs) -> PCMStream:
        """Native streaming override (ARCH-21): run Silero `apply_tts` and yield the waveform as int16
        PCM directly, instead of `save_wav` + a temp-file round-trip."""
        if not self._available or not self._model:
            await self._ensure_model_loaded()

        speaker = kwargs.get('speaker', self.default_speaker)
        sample_rate = kwargs.get('sample_rate', self.sample_rate)
        put_accent = kwargs.get('put_accent', self.put_accent)
        put_yo = kwargs.get('put_yo', self.put_yo)
        if speaker not in self._speakers:
            logger.warning(f"Unknown speaker: {speaker}, using default: {self.default_speaker}")
            speaker = self.default_speaker

        processed_text = await self._normalize_text_async(text)
        pcm = await asyncio.to_thread(
            self._synthesize_pcm_blocking, processed_text, speaker, sample_rate, put_accent, put_yo)

        async def _frames():
            yield pcm

        return PCMStream(sample_rate=sample_rate, channels=1, sample_width=2, frames=_frames())

    def _synthesize_pcm_blocking(self, text: str, speaker: str, sample_rate: int,
                                 put_accent: bool, put_yo: bool) -> bytes:
        """Run Silero v3 `apply_tts` and convert the waveform to int16 PCM (called from a thread)."""
        if not self._model:
            raise RuntimeError("Silero v3 model not loaded")
        audio = self._model.apply_tts(text=text, speaker=speaker, sample_rate=sample_rate,
                                      put_accent=put_accent, put_yo=put_yo)
        samples = audio.detach().cpu().numpy() if hasattr(audio, "detach") else audio
        return float_to_pcm16(samples)

    async def _generate_speech_async(self, text: str, output_path: Path,
                                   speaker: str, sample_rate: int,
                                   put_accent: bool, put_yo: bool) -> None:
        """Generate speech asynchronously"""
        await asyncio.to_thread(
            self._generate_speech_blocking,
            text, output_path, speaker, sample_rate, put_accent, put_yo
        )

    def _generate_speech_blocking(self, text: str, output_path: Path,
                                speaker: str, sample_rate: int,
                                put_accent: bool, put_yo: bool) -> None:
        """Generate speech in blocking mode (called from thread)"""
        if not self._model:
            raise RuntimeError("Silero v3 model not loaded")

        try:
            # Generate audio
            generated_path = self._model.save_wav(
                text=text,
                speaker=speaker,
                put_accent=put_accent,
                put_yo=put_yo,
                sample_rate=sample_rate
            )

            # Move to desired location
            generated_path = Path(generated_path)
            if output_path.exists():
                output_path.unlink()
            generated_path.rename(output_path)

            logger.debug(f"Silero v3 speech generated: {output_path}")

        except Exception as e:
            logger.error(f"Silero v3 speech generation error: {e}")
            raise
