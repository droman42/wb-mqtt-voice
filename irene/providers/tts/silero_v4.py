"""
Silero v4 TTS Provider - Neural text-to-speech using Silero models v4

Similar to SileroV3TTSProvider but using Silero v4 models with enhanced features.
Provides high-quality multilingual neural TTS using Silero v4 models.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List

from .base import TTSProvider
from ...utils.audio_stream import PCMStream, float_to_pcm16

logger = logging.getLogger(__name__)


class SileroV4TTSProvider(TTSProvider):
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
    _model_cache: Dict[str, Any] = {}
    _cache_lock = asyncio.Lock()  # Protect concurrent access to cache
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize SileroV4TTSProvider with configuration"""
        super().__init__(config)
        self._available = False
        self._model = None
        self._device = None
        self._torch: Any = None  # dynamically-imported optional torch module handle

        # Asset management integration - single source of truth
        from ...core.assets import get_asset_manager
        self.asset_manager = get_asset_manager()
        
        # Use asset manager for model paths - unified pattern
        # Get the provider directory (not a specific model file)
        asset_config = self.asset_manager._get_provider_asset_config("silero_v4")
        directory_name = asset_config.get("directory_name", "silero_v4")
        self.model_path = self.asset_manager.config.models_root / directory_name
            
        # Model selection is model_id-routed (consistent with sherpa/whisper/vosk): the file lands at
        # get_model_path("silero_v4", model_id) -> silero_v4/<model_id>.pt. `model_file` is still
        # honored as an explicit path override; `model_url` defaults to the model_id's descriptor URL.
        self.model_id = config.get("model", "v4_ru")
        _model_urls = self._get_default_model_urls()
        self.model_url = config.get("model_url", _model_urls.get(self.model_id, _model_urls["v4_ru"]))
        self.model_file = (
            self.model_path / config["model_file"] if config.get("model_file")
            else self.asset_manager.get_model_path("silero_v4", self.model_id)
        )
        # QUAL-38: number-spelling language matches the loaded MODEL (default model is Russian).
        self.language = config.get("language", "ru")
        self.default_speaker = config.get("default_speaker", "xenia")
        self.sample_rate = config.get("sample_rate", 48000)
        self.torch_device = config.get("torch_device", "cpu")
        
        # Available speakers (expanded in v4)
        self._speakers = ["xenia", "aidar", "baya", "kseniya", "eugene", "random"]
        
        # Try to import dependencies
        try:
            import torch  # type: ignore
            self._torch = torch
            self._device = torch.device(self.torch_device)
            self._available = True
            logger.info("Silero v4 TTS provider dependencies available")
        except ImportError:
            self._available = False
            logger.warning("Silero v4 TTS provider dependencies not available (torch required)")
        
        # Initialize model on startup if requested
        preload_models = config.get("preload_models", False)
        if preload_models and self._available:
            # Schedule model loading for startup
            import asyncio
            asyncio.create_task(self.warm_up())
    
    async def is_available(self) -> bool:
        """Check if provider dependencies are available and functional"""
        return self._available and self._torch is not None
    
    @classmethod
    def _get_default_extension(cls) -> str:
        """Silero v4 models use .pt format"""
        return ".pt"
    
    @classmethod
    def _get_default_directory(cls) -> str:
        """Silero v4 directory for model storage"""
        return "silero_v4"
    
    @classmethod
    def _get_default_credentials(cls) -> List[str]:
        """Silero v4 doesn't need credentials"""
        return []
    
    @classmethod
    def _get_default_cache_types(cls) -> List[str]:
        """Silero v4 uses models and runtime cache"""
        return ["models", "runtime"]
    
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

    async def warm_up(self) -> None:
        """Warm up by preloading the Silero v4 model"""
        try:
            logger.info("Warming up Silero v4 TTS model...")
            await self._ensure_model_loaded()
            logger.info("Silero v4 TTS model warmed up successfully")
        except Exception as e:
            logger.error(f"Failed to warm up Silero v4 model: {e}")
            # Don't raise - let the provider work with lazy loading
    
    
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

    # Build dependency methods (TODO #5 Phase 1)
    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        """Silero v4 requires PyTorch for model inference"""
        return ["torch>=1.13.0"]
        
    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        """Platform-specific system packages for Silero v4"""
        return {
            "linux.ubuntu": ["libsndfile1"],
            "linux.alpine": ["libsndfile"],
            "macos": ["libsndfile"],  # macOS includes audio libraries
            "windows": []  # Windows package management differs
        }
        
    @classmethod
    def get_platform_support(cls) -> List[str]:
        """Silero v4 supports all platforms"""
        return ["linux.ubuntu", "linux.alpine", "macos", "windows"]

    @classmethod
    def get_supported_architectures(cls) -> List[str]:
        return ["x86_64", "aarch64"]  # torch has no armv7 wheel (ARCH-24 T3)

    async def _ensure_model_loaded(self) -> None:
        """Ensure model is loaded and ready with caching optimization"""
        if not self._available:
            raise RuntimeError("Silero v4 TTS provider not available (torch dependency missing)")
            
        if not self._model:
            # Try to get model from cache first
            cache_key = f"{self.model_file}:{self.torch_device}"
            await self._get_or_load_cached_model(cache_key)
            
        if not self._model:
            raise RuntimeError("Failed to load Silero v4 model")
    
    async def _get_or_load_cached_model(self, cache_key: str) -> None:
        """Get model from cache or load it if not cached"""
        async with self._cache_lock:
            # Check if model is already cached
            if cache_key in self._model_cache:
                self._model = self._model_cache[cache_key]
                logger.info(f"Using cached Silero v4 model: {cache_key}")
                return
            
            # Model not in cache, load it
            try:
                await self._load_model_async()
                
                # Cache the loaded model
                self._model_cache[cache_key] = self._model
                logger.info(f"Silero v4 model loaded and cached: {cache_key}")
                
            except Exception as e:
                logger.error(f"Failed to load Silero v4 model: {e}")
                raise
    
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
        
    def _download_model(self, model_path: Path) -> None:
        """Download model using legacy method (called from thread)"""
        if not self._torch:
            return
            
        try:
            # Silero v4 model URL - this may need to be updated when v4 is officially released
            model_url = "https://models.silero.ai/models/tts/ru/v4_ru.pt"
            self._torch.hub.download_url_to_file(model_url, str(model_path))
            logger.info(f"Silero v4 model downloaded to: {model_path}")
        except Exception as e:
            logger.error(f"Failed to download Silero v4 model: {e}")
            raise
            
    def _load_model(self, model_path: Path) -> None:
        """Load model from file (called from thread)"""
        if not self._torch:
            return
            
        try:
            # For v4, the loading mechanism might be different from v3
            # This assumes similar structure to v3, but may need adjustment
            self._model = self._torch.package.PackageImporter(str(model_path)).load_pickle("tts_models", "model")
            self._model.to(self._device)
            logger.info("Silero v4 model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Silero v4 model: {e}")
            raise
            
    async def _normalize_text_async(self, text: str) -> str:
        """Normalize text asynchronously"""
        # Basic text normalization
        normalized = text.replace("…", "...")
        
        # Modern number-to-text conversion using migrated utilities
        try:
            from ...utils.text_processing import all_num_to_text_async
            normalized = await all_num_to_text_async(normalized, language=self.language)
            logger.debug("Applied number-to-text normalization")
        except Exception as e:
            logger.debug(f"Text normalization failed, using original: {e}")
            
        return normalized
        
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