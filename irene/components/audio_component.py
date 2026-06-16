"""
Audio Component - Audio coordinator managing multiple providers

Implements the fundamental component pattern for audio playback functionality.
Manages multiple audio providers based on configuration and provides unified web APIs.
"""

import logging
import time
from typing import Dict, Any, List, Optional, Type
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File  # type: ignore
from pydantic import BaseModel

from .base import Component
from ..core.interfaces.audio import AudioPlugin
from ..core.interfaces.webapi import WebAPIPlugin
from ..core.trace_context import TraceContext
from ..intents.ports import AudioPort  # QUAL-24: domain capability port (application implements it)


# Import audio provider base class and dynamic loader
from ..providers.audio import AudioProvider
from ..utils.loader import dynamic_loader

logger = logging.getLogger(__name__)


class AudioComponent(Component, AudioPlugin, WebAPIPlugin, AudioPort):
    """
    Audio Component that manages multiple audio providers.
    
    Features:
    - Configuration-driven provider instantiation
    - Unified web API (/audio/*)
    - Voice commands for audio control
    - Fallback and load balancing
    - Runtime provider switching
    """
    

    def get_service_dependencies(self) -> Dict[str, type]:
        """Get list of required service dependencies."""
        return {}  # No service dependencies
    
    @property
    def name(self) -> str:
        return "audio"
        
    @property
    def version(self) -> str:
        return "1.0.0"
        
    @property
    def description(self) -> str:
        return "Audio component managing multiple audio backends"
        

        
    @property
    def optional_dependencies(self) -> list[str]:
        """All audio provider dependencies are optional"""
        return ["sounddevice", "soundfile", "numpy", "miniaudio", "termcolor"]
        
    @property
    def enabled_by_default(self) -> bool:
        """Universal audio enabled by default"""
        return True
        
    @property  
    def category(self) -> str:
        """Plugin category"""
        return "audio"
        
    @property
    def platforms(self) -> list[str]:
        """Supported platforms (empty = all platforms)"""
        return []
    
    def __init__(self):
        super().__init__()
        self.providers: Dict[str, AudioProvider] = {}
        self.default_provider: Optional[str] = "console"
        self.fallback_providers: List[str] = ["console"]
        
        # Dynamic provider discovery from entry-points (replaces hardcoded classes)
        self._provider_classes: Dict[str, type] = {}
        
        # Runtime state
        self._current_provider = None

        # Resolved temp-audio directory (QUAL-4c: captured at init from CoreConfig.assets,
        # since the hexagon refactor removed direct `self.core` access).
        self._temp_audio_dir: Optional[Path] = None

    async def initialize(self, core) -> None:
        """Initialize the universal audio plugin"""
        await super().initialize(core)
        
        # Capture the temp-audio directory from the assets config for later endpoint use
        self._temp_audio_dir = core.config.assets.temp_audio_dir

        # Get configuration first to determine enabled providers (V14 Architecture)
        config = getattr(core.config, 'audio', None)
        if not config:
            # Create default config if missing
            from ..config.models import AudioConfig
            config = AudioConfig()
        
        # Convert Pydantic model to dict for backward compatibility with existing logic
        if hasattr(config, 'model_dump'):
            config_dict = config.model_dump()
        elif hasattr(config, 'dict'):
            config_dict = config.dict()
        else:
            # FATAL: Invalid configuration - cannot proceed with hardcoded defaults
            raise ValueError(
                "AudioComponent: Invalid configuration object received. "
                "Expected a valid AudioConfig instance, but got an invalid config. "
                "Please check your configuration file for proper v14 audio section formatting."
            )
        
        # Use the converted config dict
        config = config_dict
        
        # Update settings from config
        if isinstance(config, dict):
            self.default_provider = config.get("default_provider", self.default_provider)
            self.fallback_providers = config.get("fallback_providers", self.fallback_providers)
        else:
            # Handle config object case
            if hasattr(config, 'default_provider'):
                self.default_provider = config.default_provider
            if hasattr(config, 'fallback_providers'):
                self.fallback_providers = config.fallback_providers
        
        # Instantiate enabled providers
        providers_config = getattr(config, 'providers', {})
        if isinstance(config, dict):
            providers_config = config.get('providers', {})
        
        # Discover only enabled providers from entry-points (configuration-driven filtering)
        enabled_providers = [name for name, provider_config in providers_config.items() 
                            if provider_config.get("enabled", False)]
        
        # Always include console as fallback if not already included
        if "console" not in enabled_providers and providers_config.get("console", {}).get("enabled", True):
            enabled_providers.append("console")
            
        self._provider_classes = dynamic_loader.discover_providers("irene.providers.audio", enabled_providers)
        logger.info(f"Discovered {len(self._provider_classes)} enabled audio providers: {list(self._provider_classes.keys())}")
        
        enabled_count = 0
        
        for provider_name, provider_class in self._provider_classes.items():
            provider_config = providers_config.get(provider_name, {})
            if provider_config.get("enabled", False):
                try:
                    provider = provider_class(provider_config)
                    if await provider.is_available():
                        self.providers[provider_name] = provider
                        enabled_count += 1
                        logger.info(f"Loaded audio provider: {provider_name}")
                    else:
                        logger.warning(f"Audio provider {provider_name} not available (dependencies missing)")
                except TypeError as e:
                    logger.error(f"Audio provider {provider_name} missing required abstract methods: {e}")
                except Exception as e:
                    logger.warning(f"Failed to load audio provider {provider_name}: {e}")
        
        # Ensure we have at least one provider
        if not self.providers:
            logger.warning("No audio providers available, creating console provider as fallback")
            try:
                # Use entry-points discovery for fallback provider
                console_class = dynamic_loader.get_provider_class("irene.providers.audio", "console")
                if console_class:
                    console_provider = console_class({"enabled": True, "color_output": True})
                    self.providers["console"] = console_provider
                    self.default_provider = "console"
                    self.fallback_providers = ["console"]
                    enabled_count = 1
                else:
                    logger.error("Console audio provider not found in entry-points")
                    raise RuntimeError("No audio providers available")
            except Exception as e:
                logger.error(f"Failed to create fallback console audio provider: {e}")
                raise RuntimeError("No audio providers available")
        
        # Set default to first available if current default not available
        if self.default_provider not in self.providers:
            self.default_provider = list(self.providers.keys())[0]
            
        logger.info(f"Universal audio plugin initialized with {enabled_count} providers. Default: {self.default_provider}")
    
    # AudioPlugin interface - delegates to providers
    async def play_file(self, file_path: Path, trace_context: Optional[TraceContext] = None, **kwargs) -> None:
        """Play an audio file with optional playback tracing"""
        
        # Fast path - existing logic when no tracing
        if not trace_context or not trace_context.enabled:
            # Original implementation unchanged
            provider_name = kwargs.get("provider", self.default_provider)
            
            if provider_name in self.providers:
                try:
                    await self.providers[provider_name].play_file(file_path, **kwargs)
                    self._current_provider = provider_name
                except Exception as e:
                    logger.error(f"Audio playback failed with provider {provider_name}: {e}")
                    await self._play_with_fallback(file_path, provider_name, **kwargs)
            else:
                logger.warning(f"Provider '{provider_name}' not available, using fallback")
                await self._play_with_fallback(file_path, provider_name, **kwargs)
            return
        
        # Trace path - detailed playback tracking
        stage_start = time.time()
        provider_name = kwargs.get("provider", self.default_provider)
        playback_metadata = {
            "file_path": str(file_path),
            "file_exists": file_path.exists(),
            "file_size_bytes": file_path.stat().st_size if file_path.exists() else 0,
            "provider": provider_name,
            "component_name": self.__class__.__name__
        }
        
        try:
            if provider_name in self.providers:
                try:
                    await self.providers[provider_name].play_file(file_path, **kwargs)
                    self._current_provider = provider_name
                    playback_metadata.update({
                        "playback_success": True,
                        "provider_used": provider_name,
                        "fallback_used": False
                    })
                except Exception as e:
                    logger.error(f"Audio playback failed with provider {provider_name}: {e}")
                    await self._play_with_fallback(file_path, provider_name, **kwargs)
                    playback_metadata.update({
                        "playback_success": True,
                        "provider_used": "fallback",
                        "fallback_used": True,
                        "original_error": str(e)
                    })
            else:
                logger.warning(f"Provider '{provider_name}' not available, using fallback")
                await self._play_with_fallback(file_path, provider_name, **kwargs)
                playback_metadata.update({
                    "playback_success": True,
                    "provider_used": "fallback",
                    "fallback_used": True,
                    "reason": "provider_not_available"
                })
            
        except Exception as e:
            playback_metadata.update({
                "playback_success": False,
                "error": str(e)
            })
            raise
        
        trace_context.record_stage(
            stage_name="audio_playback",
            input_data=file_path,  # Path object - will be read and converted to base64 by _sanitize_for_trace()
            output_data={"playback_completed": True},
            metadata=playback_metadata,
            processing_time_ms=(time.time() - stage_start) * 1000
        )
    
    async def play_stream(self, audio_data: bytes, *, sample_rate: int = 44100,
                          channels: int = 1, sample_width: int = 2, **kwargs) -> None:
        """Play raw PCM bytes through the active provider's streaming backend (ARCH-20)."""
        provider_name = kwargs.get("provider", self.default_provider)

        # Convert bytes to a one-shot async iterator (buffer-then-stream).
        async def byte_stream():
            yield audio_data

        if provider_name in self.providers:
            try:
                await self.providers[provider_name].play_stream(
                    byte_stream(), sample_rate=sample_rate, channels=channels,
                    sample_width=sample_width, **kwargs)
                self._current_provider = provider_name
            except Exception as e:
                logger.error(f"Audio stream playback failed with provider {provider_name}: {e}")
                await self._stream_with_fallback(
                    audio_data, provider_name, sample_rate=sample_rate,
                    channels=channels, sample_width=sample_width, **kwargs)
        else:
            await self._stream_with_fallback(
                audio_data, provider_name, sample_rate=sample_rate,
                channels=channels, sample_width=sample_width, **kwargs)
    
    async def stop_playback(self) -> None:
        """Stop current audio playback"""
        if self._current_provider and self._current_provider in self.providers:
            await self.providers[self._current_provider].stop_playback()

        # Stop all providers as fallback
        for provider in self.providers.values():
            try:
                await provider.stop_playback()
            except Exception as e:
                logger.debug(f"Error stopping provider: {e}")

    async def pause_audio(self) -> None:
        """Pause current audio playback (AudioPort, QUAL-24) — delegates to the active provider."""
        if self._current_provider and self._current_provider in self.providers:
            await self.providers[self._current_provider].pause_playback()

    async def resume_audio(self) -> None:
        """Resume paused audio playback (AudioPort, QUAL-24) — delegates to the active provider."""
        if self._current_provider and self._current_provider in self.providers:
            await self.providers[self._current_provider].resume_playback()
    
    def get_supported_formats(self) -> list[str]:
        """Get union of all supported formats from all providers"""
        formats = set()
        for provider in self.providers.values():
            formats.update(provider.get_supported_formats())
        return list(formats)
    
    def get_playback_devices(self) -> list[Dict[str, Any]]:
        """Get devices from current provider"""
        if self.default_provider in self.providers:
            return self.providers[self.default_provider].get_playback_devices()
        return []
    
    async def set_output_device(self, device_id: str) -> None:
        """Set output device on current provider"""
        if self.default_provider in self.providers:
            await self.providers[self.default_provider].set_output_device(device_id)
    
    async def set_volume(self, volume: float) -> None:
        """Set volume on all providers"""
        for provider in self.providers.values():
            try:
                await provider.set_volume(volume)
            except Exception as e:
                logger.debug(f"Error setting volume on provider: {e}")
    
    # Public methods for intent handler delegation

    
    def set_default_provider(self, provider_name: str) -> bool:
        """Set default audio provider - simple atomic operation"""
        if provider_name in self.providers:
            self.default_provider = provider_name
            return True
        return False
    
    def get_providers_info(self) -> str:
        """Implementation of abstract method - Get audio providers information"""
        return self._get_providers_info()
    
    def parse_provider_name_from_text(self, text: str) -> Optional[str]:
        """Override base method with audio-specific logic"""
        # First try base implementation
        result = super().parse_provider_name_from_text(text)
        if result:
            return result
        
        # Audio-specific logic
        return self._parse_provider_name(text.lower())
    
    # WebAPIPlugin interface - unified API
    def get_router(self) -> APIRouter:
        """Get FastAPI router for audio endpoints using centralized schemas"""
        from ..config.models import AudioConfig
        from ..api.schemas import (
            AudioPlayResponse, AudioStreamResponse, AudioStopResponse,
            AudioDevicesResponse,
            AudioProvidersResponse,
            AudioConfigureResponse
        )
        
        router = APIRouter()
        
        @router.post("/play", response_model=AudioPlayResponse)
        async def play_audio(
            file: UploadFile = File(...),
            provider: Optional[str] = None,
            volume: Optional[float] = None,
            device: Optional[str] = None
        ):
            """Upload and play an audio file"""
            provider_name = provider or self.default_provider
            
            if provider_name not in self.providers:
                raise HTTPException(404, f"Provider '{provider_name}' not available")
            
            # Save uploaded file to configured temp directory
            import uuid
            from ..config.models import CoreConfig
            
            # Get temp audio directory from configuration (captured at initialize())
            temp_dir = self._temp_audio_dir if self._temp_audio_dir is not None else CoreConfig().assets.temp_audio_dir
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename
            filename = file.filename or "audio_file"
            suffix = Path(filename).suffix if filename else ".wav"
            unique_filename = f"{uuid.uuid4()}{suffix}"
            temp_path = temp_dir / unique_filename
            
            # Write uploaded content to file
            content = await file.read()
            temp_path.write_bytes(content)
            
            try:
                # Build parameters
                kwargs: Dict[str, Any] = {"provider": provider_name}
                if volume is not None:
                    kwargs["volume"] = volume
                if device is not None:
                    kwargs["device"] = device
                
                # Play the file
                await self.play_file(temp_path, **kwargs)
                
                return AudioPlayResponse(
                    success=True,
                    provider=provider_name,
                    file=file.filename,
                    size=len(content)
                )
                
            finally:
                # Clean up temporary file
                if temp_path.exists():
                    temp_path.unlink()
        
        @router.post("/stream", response_model=AudioStreamResponse)
        async def play_audio_stream(
            audio_data: bytes,
            format: str = "wav",
            provider: Optional[str] = None,
            volume: Optional[float] = None
        ):
            """Play audio from raw data stream.

            ARCH-20: playback is PCM-only. A posted WAV container is parsed down to its
            PCM payload + format; otherwise the bytes are treated as raw 16-bit PCM at
            the canonical 44.1 kHz / mono. (External contract unchanged — Invariant #4.)
            """
            provider_name = provider or self.default_provider

            if provider_name not in self.providers:
                raise HTTPException(404, f"Provider '{provider_name}' not available")

            kwargs: Dict[str, Any] = {"provider": provider_name}
            if volume is not None:
                kwargs["volume"] = volume

            from ..utils.audio_stream import is_wav, parse_wav
            if is_wav(audio_data):
                pcm, rate, ch, width = parse_wav(audio_data)
            else:
                pcm, rate, ch, width = audio_data, 44100, 1, 2

            await self.play_stream(pcm, sample_rate=rate, channels=ch, sample_width=width, **kwargs)

            return AudioStreamResponse(
                success=True,
                provider=provider_name,
                format=format,
                size=len(audio_data)
            )
        
        @router.post("/stop", response_model=AudioStopResponse)
        async def stop_audio():
            """Stop current audio playback"""
            await self.stop_playback()
            return AudioStopResponse(
                success=True,
                message="Audio playback stopped"
            )
        
        @router.get("/providers", response_model=AudioProvidersResponse)
        async def list_providers():
            """List all available audio providers and their capabilities"""
            result = {}
            for name, provider in self.providers.items():
                result[name] = {
                    "available": await provider.is_available(),
                    "parameters": provider.get_parameter_schema(),
                    "capabilities": provider.get_capabilities(),
                    "formats": provider.get_supported_formats()
                }
            
            return AudioProvidersResponse(
                success=True,
                providers=result,
                default=self.default_provider or "console",
                fallbacks=self.fallback_providers
            )
        
        @router.get("/devices", response_model=AudioDevicesResponse)
        async def list_devices(provider: Optional[str] = None):
            """List available audio output devices"""
            provider_name = provider or self.default_provider
            
            if provider_name not in self.providers:
                raise HTTPException(404, f"Provider '{provider_name}' not available")
            
            devices = self.providers[provider_name].get_playback_devices()
            return AudioDevicesResponse(
                success=True,
                provider=provider_name,
                devices=devices
            )
        
        @router.post("/configure", response_model=AudioConfigureResponse)
        async def configure_audio(config_update: AudioConfig):
            """Configure audio settings using unified TOML schema"""
            try:
                
                # Apply runtime configuration without TOML persistence
                config_dict = config_update.model_dump()
                
                # Update default provider if provided
                if config_dict.get("default_provider"):
                    if config_dict["default_provider"] in self.providers:
                        self.default_provider = config_dict["default_provider"]
                    else:
                        logger.warning(f"Audio provider '{config_dict['default_provider']}' not available")
                
                # Update fallback providers
                fallback_providers = config_dict.get("fallback_providers", [])
                if fallback_providers:
                    logger.info(f"Audio fallback providers updated: {fallback_providers}")
                
                # Update enabled providers if provided (would require re-initialization)
                providers_config = config_dict.get("providers", {})
                if providers_config:
                    logger.info(f"Audio runtime provider configuration updated for {len(providers_config)} providers")
                
                return AudioConfigureResponse(
                    success=True,
                    message="Audio configuration applied successfully using unified schema",
                    default_provider=self.default_provider,
                    enabled_providers=list(self.providers.keys()),
                    fallback_providers=fallback_providers
                )
                
            except Exception as e:
                logger.error(f"Failed to configure audio with unified schema: {e}")
                return AudioConfigureResponse(
                    success=False,
                    message=f"Failed to apply audio configuration: {str(e)}",
                    default_provider=self.default_provider,
                    enabled_providers=list(self.providers.keys()),
                    fallback_providers=[]
                )
        
        return router
    
    def get_api_prefix(self) -> str:
        """Get URL prefix for audio API endpoints"""
        return "/audio"
    
    def get_api_tags(self) -> List[str]:
        """Get OpenAPI tags for audio endpoints"""
        return ["Audio Playback"]
    
    # Helper methods
    async def _play_with_fallback(self, file_path: Path, failed_provider: str, **kwargs) -> None:
        """Attempt playback with fallback providers"""
        for fallback in self.fallback_providers:
            if fallback != failed_provider and fallback in self.providers:
                try:
                    logger.info(f"Trying fallback audio provider: {fallback}")
                    await self.providers[fallback].play_file(file_path, **kwargs)
                    self._current_provider = fallback
                    return
                except Exception as e:
                    logger.warning(f"Fallback provider {fallback} also failed: {e}")
        
        raise RuntimeError("All audio providers failed")
    
    async def _stream_with_fallback(self, audio_data: bytes, failed_provider: str, *,
                                    sample_rate: int = 44100, channels: int = 1,
                                    sample_width: int = 2, **kwargs) -> None:
        """Attempt stream playback with fallback providers"""
        async def byte_stream():
            yield audio_data

        for fallback in self.fallback_providers:
            if fallback != failed_provider and fallback in self.providers:
                try:
                    logger.info(f"Trying fallback audio provider for stream: {fallback}")
                    await self.providers[fallback].play_stream(
                        byte_stream(), sample_rate=sample_rate, channels=channels,
                        sample_width=sample_width, **kwargs)
                    self._current_provider = fallback
                    return
                except Exception as e:
                    logger.warning(f"Fallback provider {fallback} also failed for stream: {e}")

        raise RuntimeError("All audio providers failed for stream playback")
    
    def _parse_provider_name(self, command: str) -> Optional[str]:
        """Extract provider name from voice command"""
        for provider_name in self.providers.keys():
            if provider_name in command:
                return provider_name
        return None
    
    def _get_providers_info(self) -> str:
        """Get formatted information about available providers"""
        if not self.providers:
            return "Нет доступных аудио провайдеров"
        
        info_lines = [f"Доступные аудио провайдеры ({len(self.providers)}):"]
        for name, provider in self.providers.items():
            status = "✅" if name == self.default_provider else "⚪"
            capabilities = provider.get_capabilities()
            formats = ", ".join(capabilities.get("formats", [])[:3])  # Show first 3 formats
            info_lines.append(f"{status} {name}: {formats}")
        
        info_lines.append(f"По умолчанию: {self.default_provider}")
        return "\n".join(info_lines)
    
    # Build dependency methods (TODO #5 Phase 2)
    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        """Audio component needs web API functionality"""
        return [
            "fastapi>=0.100.0", 
            "uvicorn>=0.20.0",
            "python-multipart>=0.0.6"  # Required for file upload endpoints
        ]
    
    # Config interface methods (Phase 3 - Configuration Architecture Cleanup)
    @classmethod
    def get_config_class(cls) -> Type[BaseModel]:
        """Return the Pydantic config model for this component"""
        from ..config.models import AudioConfig
        return AudioConfig
    
    @classmethod
    def get_config_path(cls) -> str:
        """Return the TOML path to this component's config (V14 Architecture)"""
        return "audio" 