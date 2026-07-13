"""
ElevenLabs TTS Provider

ElevenLabs neural voice synthesis provider implementation.
Provides high-quality text-to-speech using cloud-based AI models.
"""

import os
from typing import Dict, Any, List
from pathlib import Path
import logging

from .base import TTSProvider
from ...utils.audio_stream import PCMStream

logger = logging.getLogger(__name__)


class ElevenLabsTTSProvider(TTSProvider):
    """
    ElevenLabs TTS Provider - High-quality neural voice synthesis
    
    Enhanced in TODO #4 Phase 1 with intelligent asset defaults.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize ElevenLabs provider with configuration
        
        Args:
            config: Provider configuration containing:
                - api_key_env: Environment variable name for API key (deprecated - uses asset manager)
                - voice_id: Default voice ID to use
                - model: Model to use for synthesis
                - stability: Voice stability setting (0-1)
                - similarity_boost: Voice similarity boost (0-1)
        """
        super().__init__(config)  # Proper ABC inheritance
        
        # Asset management integration - single source of truth
        from ...core.assets import get_asset_manager
        self.asset_manager = get_asset_manager()
        
        # Use asset manager for credentials - unified pattern
        credentials = self.asset_manager.get_credentials("elevenlabs")
        self.api_key = credentials.get("elevenlabs_api_key") or os.getenv("ELEVENLABS_API_KEY")
            
        self.voice_id = config.get("voice_id", "default")
        self.model = config.get("model", "eleven_multilingual_v2")
        self.stability = config.get("stability", 0.5)
        self.similarity_boost = config.get("similarity_boost", 0.5)
        self.base_url = "https://api.elevenlabs.io/v1"
        # ARCH-21: streaming requests raw PCM (not MP3) so it flows through the PCM-only output path.
        # ElevenLabs `output_format=pcm_<rate>` returns signed-16 mono PCM. 44100 needs a paid tier; 22050
        # is broadly available.
        self.output_pcm_rate = config.get("output_pcm_rate", 22050)
        
    @classmethod
    def _get_default_extension(cls) -> str:
        """ElevenLabs provides audio streams, no persistent files"""
        return ".mp3"
    
    @classmethod
    def _get_default_directory(cls) -> str:
        """ElevenLabs uses runtime cache only"""
        return "elevenlabs"
    
    @classmethod
    def _get_default_credentials(cls) -> List[str]:
        """ElevenLabs requires API key credential"""
        return ["ELEVENLABS_API_KEY"]
    
    @classmethod
    def _get_default_cache_types(cls) -> List[str]:
        """Uses runtime cache for temporary audio data only"""
        return ["runtime"]
    
    @classmethod
    def _get_default_model_urls(cls) -> Dict[str, str]:
        """ElevenLabs is API-based, no model downloads"""
        return {}
    
    async def is_available(self) -> bool:
        """Check if ElevenLabs API is available"""
        if not self.api_key:
            logger.warning("ElevenLabs API key not found")
            return False
            
        try:
            import httpx  # type: ignore
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/voices",
                    headers={"xi-api-key": self.api_key},
                    timeout=5.0
                )
                return response.status_code == 200
        except ImportError:
            logger.warning("httpx library not available for ElevenLabs")
            return False
        except Exception as e:
            logger.warning(f"ElevenLabs API check failed: {e}")
            return False
    
    async def synthesize_to_file(self, text: str, output_path: Path, **kwargs) -> None:
        """Generate audio file using ElevenLabs"""
        voice_id = kwargs.get("voice_id", self.voice_id)
        stability = kwargs.get("stability", self.stability)
        similarity_boost = kwargs.get("similarity_boost", self.similarity_boost)
        
        try:
            audio_data = await self._generate_audio(
                text, voice_id, stability, similarity_boost
            )
            
            with open(output_path, "wb") as f:
                f.write(audio_data)
                
            logger.info(f"ElevenLabs audio saved to: {output_path}")

        except Exception as e:
            # CR-A8: re-raise like the other TTS providers (silero/vosk/piper). Swallowing made the method
            # appear to succeed while writing no file → the caller read a non-existent WAV and the TTS
            # fallback chain never engaged.
            logger.error(f"ElevenLabs file generation failed: {e}")
            raise RuntimeError(f"ElevenLabs file generation failed: {e}") from e
    
    async def synthesize_to_stream(self, text: str, **kwargs) -> PCMStream:
        """Native streaming override (ARCH-21): request raw PCM (not MP3) from ElevenLabs so it flows
        through the PCM-only output path. The base buffer-then-stream simulation can't be used here
        because `synthesize_to_file` writes MP3."""
        voice_id = kwargs.get("voice_id", self.voice_id)
        stability = kwargs.get("stability", self.stability)
        similarity_boost = kwargs.get("similarity_boost", self.similarity_boost)
        rate = int(kwargs.get("output_pcm_rate", self.output_pcm_rate))

        pcm = await self._generate_pcm(text, voice_id, stability, similarity_boost, rate)

        async def _frames():
            yield pcm

        return PCMStream(sample_rate=rate, channels=1, sample_width=2, frames=_frames())

    async def _generate_pcm(self, text: str, voice_id: str, stability: float,
                            similarity_boost: float, rate: int) -> bytes:
        """Call the ElevenLabs API requesting raw signed-16 mono PCM at ``rate`` Hz."""
        url = f"{self.base_url}/text-to-speech/{voice_id}"
        params = {"output_format": f"pcm_{rate}"}
        payload = {
            "text": text,
            "model_id": self.model,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost
            }
        }
        headers = {
            "Accept": "audio/pcm",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        try:
            import httpx  # type: ignore
            async with httpx.AsyncClient() as client:
                response = await client.post(url, params=params, json=payload, headers=headers, timeout=30.0)
                response.raise_for_status()
                return response.content
        except Exception as e:
            logger.error(f"ElevenLabs PCM API call failed: {e}")
            raise

    async def _generate_audio(self, text: str, voice_id: str,
                            stability: float, similarity_boost: float) -> bytes:
        """Call ElevenLabs API to generate audio"""
        url = f"{self.base_url}/text-to-speech/{voice_id}"
        
        payload = {
            "text": text,
            "model_id": self.model,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost
            }
        }
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        try:
            import httpx  # type: ignore
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, 
                    json=payload, 
                    headers=headers,
                    timeout=30.0  # Longer timeout for audio generation
                )
                response.raise_for_status()
                return response.content
        except Exception as e:
            logger.error(f"ElevenLabs API call failed: {e}")
            raise
    
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return provider capabilities"""
        return {
            "languages": ["en", "ru", "es", "fr", "de", "it", "pt", "pl", "hi", "ar"],
            "formats": ["mp3"],
            "quality": "high",
            "real_time": True,
            "custom_voices": True,
            "cloud_based": True,
            "neural": True,
            "emotional_range": True,
            "voice_cloning": True
        }
    
    def get_provider_name(self) -> str:
        return "elevenlabs"
    
    # Build dependency methods (TODO #5 Phase 1)
    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        """ElevenLabs TTS requires its API client runtime dependencies"""
        return ["tts-elevenlabs"]  # Build extra: tts-elevenlabs
        
    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        """ElevenLabs is cloud-based, no system dependencies"""
        return {
            "linux.ubuntu": [],
            "linux.alpine": [],
            "macos": [],
            "windows": []
        }
