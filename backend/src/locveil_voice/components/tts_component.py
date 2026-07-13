"""
TTS Component - Coordinator for multiple TTS providers

This component implements the fundamental component pattern from the refactoring plan.
It manages multiple TTS providers through configuration-driven instantiation
and provides unified web APIs and voice command interfaces.
"""

import asyncio
import inspect
import logging
import base64
import time
from typing import Dict, Any, List, Optional, Type
from pathlib import Path
from datetime import datetime

from pydantic import BaseModel

from .base import Component
from ..core.interfaces.tts import TTSPlugin
from ..core.interfaces.webapi import WebAPIPlugin
from ..core.trace_context import TraceContext
from ..core.session_manager import SessionManager
from ..intents.ports import TTSPort  # QUAL-24: domain capability port (application implements it)

# Import TTS provider base class and dynamic loader
from ..providers.tts import TTSProvider
from ..utils.loader import dynamic_loader
from ..utils.audio_stream import PCMStream

logger = logging.getLogger(__name__)


class TTSComponent(Component, TTSPlugin, WebAPIPlugin, TTSPort):
    """
    TTS component that coordinates multiple TTS providers.
    
    Features:
    - Configuration-driven provider instantiation
    - Unified web API (/tts/* endpoints)
    - Voice command interface for TTS control
    - Provider fallback and load balancing
    - Runtime provider switching
    """
    
    @property
    def name(self) -> str:
        return "tts"
        
    @property
    def version(self) -> str:
        return "1.0.0"
        
    @property
    def description(self) -> str:
        return "TTS component coordinating multiple TTS providers with unified API"
        

        
    @property
    def optional_dependencies(self) -> list[str]:
        return ["torch", "pyttsx3", "vosk", "fastapi"]
        
    @property
    def enabled_by_default(self) -> bool:
        return True
        
    @property  
    def category(self) -> str:
        return "tts"
        
    @property
    def platforms(self) -> list[str]:
        return []  # All platforms
    

    def get_component_dependencies(self) -> list[str]:
        """Get list of required component dependencies."""
        return ["audio"]  # TTS needs audio component to play generated speech
    
    def __init__(self):
        super().__init__()
        self.providers: Dict[str, TTSProvider] = {}
        self._loaded_providers: Dict[str, TTSProvider] = {}  # Cache for lazy-loaded providers
        self.default_provider: Optional[str] = "console"
        self.fallback_providers: List[str] = ["console"]
        self.core = None
        self._provider_configs: Dict[str, Dict[str, Any]] = {}  # Cache provider configs
        self._lazy_loading_enabled: bool = True  # Feature flag for lazy loading
        
        # Dynamic provider discovery from entry-points (replaces hardcoded classes)
        self._provider_classes: Dict[str, type] = {}
        
    async def initialize(self, core) -> None:
        """Initialize providers with concurrent loading and lazy loading support"""
        await super().initialize(core)
        self.core = core
        
        # Get configuration first to determine enabled providers (V14 Architecture)
        config = getattr(core.config, 'tts', None)
        if not config:
            # Create default config if missing
            from ..config.models import TTSConfig
            config = TTSConfig()
        
        # Convert Pydantic model to dict for backward compatibility with existing logic
        if hasattr(config, 'model_dump'):
            config_dict = config.model_dump()
        elif hasattr(config, 'dict'):
            config_dict = config.dict()
        else:
            # FATAL: Invalid configuration - cannot proceed with hardcoded defaults
            raise ValueError(
                "TTSComponent: Invalid configuration object received. "
                "Expected a valid TTSConfig instance, but got an invalid config. "
                "Please check your configuration file for proper v14 tts section formatting."
            )
        
        # Add TTS-specific settings not in v14 config but needed for backward compatibility
        config_dict["lazy_loading"] = True
        config_dict["concurrent_initialization"] = True
        
        # Use the converted config dict
        config = config_dict
            
        self.default_provider = config.get("default_provider", "console")
        self.fallback_providers = config.get("fallback_providers", ["console"])
        self._lazy_loading_enabled = config.get("lazy_loading", True)
        concurrent_init = config.get("concurrent_initialization", True)
        
        # Cache provider configurations for lazy loading
        self._provider_configs = config.get("providers", {})
        
        # Discover only enabled providers from entry-points (configuration-driven filtering)
        enabled_providers = [name for name, provider_config in self._provider_configs.items()
                            if provider_config.get("enabled", False)]
        # What the operator EXPLICITLY enabled — the console fallback appended below is implicit, so
        # its absence must never abort startup (BUG-36 checks below use this list, not the appended one).
        configured_providers = list(enabled_providers)

        # Always include console as fallback if not already included
        if "console" not in enabled_providers and self._provider_configs.get("console", {}).get("enabled", True):
            enabled_providers.append("console")

        self._provider_classes = dynamic_loader.discover_providers("locveil_voice.providers.tts", enabled_providers)
        logger.info(f"Discovered {len(self._provider_classes)} enabled TTS providers: {list(self._provider_classes.keys())}")

        # BUG-36 kind 1 — a configured provider must at least IMPORT. Instantiation may legitimately be
        # deferred here (lazy loading), so this checks the discovered classes, not the instances.
        self._require_loadable_providers("locveil_voice.providers.tts", configured_providers, self._provider_classes)
        
        if self._lazy_loading_enabled:
            # Lazy loading: Only load essential providers immediately
            await self._initialize_essential_providers()
        else:
            # Traditional loading: Load all providers
            if concurrent_init:
                await self._initialize_providers_concurrent()
            else:
                await self._initialize_providers_sequential()
        
        # Ensure we have at least one provider
        if not self.providers and not self._lazy_loading_enabled:
            await self._load_fallback_provider()

        if not self._lazy_loading_enabled:
            # Eager path: report anything that imported but could not initialize (kind 2 — loud, not fatal).
            self._note_inactive_providers(configured_providers, self.providers)

        # BUG-36: the default must be a provider that exists, not "whatever survived". Silently
        # speaking through a different engine than the configured one is the same lie as a component
        # vanishing at import time. (Runtime fallback remains the job of the fallback chain.)
        if self.default_provider not in self._provider_classes:
            raise ValueError(
                f"TTS default_provider={self.default_provider!r} did not load — enable a "
                f"[tts.providers.{self.default_provider}] section, or point default_provider at one of: "
                f"{', '.join(sorted(self._provider_classes)) or 'none'}")


        logger.info(f"Universal TTS plugin initialized with {len(self.providers)} providers (lazy loading: {self._lazy_loading_enabled})")
    
    async def _initialize_essential_providers(self) -> None:
        """Initialize only essential providers for lazy loading"""
        essential_providers = ["console"]  # Always load console as fallback
        
        # Add default provider if it's different from console
        if self.default_provider and self.default_provider not in essential_providers:
            essential_providers.append(self.default_provider)
        
        for provider_name in essential_providers:
            if provider_name in self._provider_classes:
                provider_config = self._provider_configs.get(provider_name, {})
                if provider_config.get("enabled", provider_name == "console"):  # Console enabled by default
                    await self._load_single_provider(provider_name, provider_config)
    
    async def _initialize_providers_concurrent(self) -> None:
        """Initialize providers concurrently for better performance"""
        provider_configs = self._provider_configs
        
        # Create initialization tasks
        init_tasks = []
        for provider_name, provider_class in self._provider_classes.items():
            provider_config = provider_configs.get(provider_name, {})
            if provider_config.get("enabled", False):
                task = asyncio.create_task(
                    self._init_single_provider(provider_name, provider_config)
                )
                init_tasks.append((provider_name, task))
        
        if not init_tasks:
            logger.warning("No TTS providers enabled in configuration")
            return
        
        # Wait for all providers to initialize
        results = await asyncio.gather(*[task for _, task in init_tasks], return_exceptions=True)
        
        # Process results
        for (provider_name, _), result in zip(init_tasks, results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to initialize TTS provider {provider_name}: {result}")
            elif isinstance(result, TTSProvider):  # Explicit type check for TTSProvider
                self.providers[provider_name] = result
                logger.info(f"Concurrently initialized TTS provider: {provider_name}")
            else:
                logger.warning(f"TTS provider {provider_name} initialization returned unexpected type: {type(result)}")
    
    async def _initialize_providers_sequential(self) -> None:
        """Initialize providers sequentially (traditional method)"""
        provider_configs = self._provider_configs
        
        for provider_name, provider_class in self._provider_classes.items():
            provider_config = provider_configs.get(provider_name, {})
            if provider_config.get("enabled", False):
                await self._load_single_provider(provider_name, provider_config)
    
    async def _init_single_provider(self, provider_name: str, provider_config: Dict[str, Any]) -> Optional[TTSProvider]:
        """Initialize a single provider (for concurrent initialization)"""
        try:
            provider_class = self._provider_classes[provider_name]
            provider = provider_class(provider_config)
            
            if await provider.is_available():
                return provider
            else:
                logger.warning(f"TTS provider {provider_name} not available (dependencies missing)")
                return None
        except TypeError as e:
            logger.error(f"TTS provider {provider_name} missing required abstract methods: {e}")
            return None
        except Exception as e:
            logger.warning(f"Failed to load TTS provider {provider_name}: {e}")
            return None
    
    async def _load_single_provider(self, provider_name: str, provider_config: Dict[str, Any]) -> bool:
        """Load a single provider (for sequential and lazy loading)"""
        try:
            provider_class = self._provider_classes[provider_name]
            provider = provider_class(provider_config)
            
            if await provider.is_available():
                self.providers[provider_name] = provider
                logger.info(f"Loaded TTS provider: {provider_name}")
                return True
            else:
                logger.warning(f"TTS provider {provider_name} not available (dependencies missing)")
                return False
        except TypeError as e:
            logger.error(f"TTS provider {provider_name} missing required abstract methods: {e}")
            return False
        except Exception as e:
            logger.warning(f"Failed to load TTS provider {provider_name}: {e}")
            return False
    
    async def _load_provider_lazy(self, provider_name: str) -> Optional[TTSProvider]:
        """Load provider only when first used (lazy loading)"""
        if provider_name in self._loaded_providers:
            return self._loaded_providers[provider_name]
        
        if provider_name not in self._provider_classes:
            logger.error(f"Unknown TTS provider: {provider_name}")
            return None
        
        provider_config = self._provider_configs.get(provider_name, {})
        if not provider_config.get("enabled", False):
            logger.warning(f"TTS provider {provider_name} not enabled in configuration")
            return None
        
        try:
            provider_class = self._provider_classes[provider_name]
            provider = provider_class(provider_config)
            
            if await provider.is_available():
                self._loaded_providers[provider_name] = provider
                self.providers[provider_name] = provider  # Add to active providers
                logger.info(f"Lazy-loaded TTS provider: {provider_name}")
                return provider
            else:
                logger.warning(f"TTS provider {provider_name} not available (dependencies missing)")
                return None
        except Exception as e:
            logger.error(f"Failed to lazy-load TTS provider {provider_name}: {e}")
            return None
    
    async def _load_fallback_provider(self) -> None:
        """Load fallback console provider if no providers are available"""
        try:
            # Use entry-points discovery for fallback provider
            console_class = dynamic_loader.get_provider_class("locveil_voice.providers.tts", "console")
            if console_class:
                console_provider = console_class({"enabled": True, "color_output": True})
                self.providers["console"] = console_provider
                logger.info("Fallback: Loaded console TTS provider via entry-points")
            else:
                logger.error("Console TTS provider not found in entry-points")
        except Exception as e:
            logger.error(f"Failed to load fallback console provider: {e}")
    
    async def _conform_to_sink(self, audio_data, rate, channels):
        """Conform synthesized audio DOWN to the streaming caller's sink (its requested rate/channels, CD
        default) via the SHARED `core.audio_negotiator.to_sink` (ARCH-18 PR-4c — the output mirror of
        `to_canonical`). Conform-down ONLY: a caller that asks for a higher rate than the TTS engine produces
        receives the engine's native rate (any device plays lower); read the result's `sample_rate`/`channels`
        for the actual output. No-op (pass-through) when the negotiator isn't wired."""
        from ..utils.audio_negotiation import AudioContract
        negotiator = getattr(self.core, "audio_negotiator", None)
        if negotiator is None:
            return audio_data
        r = int(rate or 44100)
        c = int(channels or 2)
        sink = AudioContract([r], r, ["pcm16"], "pcm16", c)
        return await negotiator.to_sink(audio_data, sink)

    # TTSPlugin interface - delegates to providers
    async def synthesize_to_file(self, text: str, output_path: Path, trace_context: Optional[TraceContext] = None, **kwargs) -> None:
        """Generate audio file with optional synthesis tracing"""
        
        # Fast path - existing logic when no tracing
        if not trace_context or not trace_context.enabled:
            # Original implementation unchanged - delegate to provider
            provider_name = kwargs.get("provider", self.default_provider)
            
            # Try to get provider, with lazy loading if enabled
            provider = await self._get_provider(provider_name)
            
            if provider:
                try:
                    await provider.synthesize_to_file(text, output_path, **kwargs)
                except Exception as e:
                    logger.error(f"TTS provider {provider_name} failed: {e}")
                    await self._synthesize_with_fallback(text, output_path, **kwargs)
            else:
                logger.warning(f"TTS provider {provider_name} not available")
                await self._synthesize_with_fallback(text, output_path, **kwargs)
            return
        
        # Trace path - detailed synthesis tracking
        stage_start = time.time()
        provider_name = kwargs.get("provider", self.default_provider)
        synthesis_metadata = {
            "input_text_length": len(text),
            "input_word_count": len(text.split()),
            "provider": provider_name,
            "auto_play": getattr(self, 'auto_play', False),
            "component_name": self.__class__.__name__
        }
        
        try:
            # Execute original synthesis logic via provider
            provider = await self._get_provider(provider_name)
            if provider:
                await provider.synthesize_to_file(text, output_path, **kwargs)
                synthesis_metadata.update({
                    "synthesis_success": True,
                    "output_file": str(output_path),
                    "provider_used": getattr(provider, 'name', provider_name)
                })
            else:
                # Fallback handling
                await self._synthesize_with_fallback(text, output_path, **kwargs)
                synthesis_metadata.update({
                    "synthesis_success": True,
                    "output_file": str(output_path),
                    "provider_used": "fallback"
                })
            
        except Exception as e:
            synthesis_metadata.update({
                "synthesis_success": False,
                "error": str(e)
            })
            raise
        
        trace_context.record_stage(
            stage_name="tts_synthesis",
            input_data=text,
            output_data=output_path,  # Path object - will be read and converted to base64 by _sanitize_for_trace()
            metadata=synthesis_metadata,
            processing_time_ms=(time.time() - stage_start) * 1000
        )
    
    async def stop_synthesis(self) -> None:
        """Stop current synthesis (TTSPort, QUAL-24).

        Best-effort: delegates to the active provider's `stop_synthesis` if it
        exposes one. Current TTS providers synthesize to a file and do not
        support mid-synthesis interruption, so this is a graceful no-op there
        rather than an error.
        """
        provider = self.providers.get(self.default_provider) if self.default_provider else None
        stop = getattr(provider, "stop_synthesis", None)
        if callable(stop):
            result = stop()
            if inspect.isawaitable(result):
                await result
        else:
            self.logger.debug("stop_synthesis requested; active TTS provider does not support interruption")

    async def cancel_synthesis(self) -> None:
        """Cancel current synthesis (TTSPort, QUAL-24) — same semantics as stop for TTS."""
        await self.stop_synthesis()

    async def speak(self, text: str, **kwargs) -> str:
        """
        Convert text to speech and save to timestamped file.

        Args:
            text: Text to convert to speech
            **kwargs: Engine-specific parameters (voice, speed, etc.)

        Returns:
            str: Filename of the generated audio file
        """
        # Generate timestamped filename in current directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
        filename = f"tts_{timestamp}.wav"
        output_path = Path.cwd() / filename
        
        # Use existing synthesize_to_file implementation
        await self.synthesize_to_file(text, output_path, **kwargs)
        
        return filename
    
    async def to_file(self, text: str, output_path: Path, **kwargs) -> None:
        """
        Convert text to speech and save to specified file.
        
        Args:
            text: Text to convert to speech
            output_path: Where to save the audio file
            **kwargs: Engine-specific parameters
        """
        # Delegate to existing synthesize_to_file implementation
        await self.synthesize_to_file(text, output_path, **kwargs)

    async def synthesize_to_stream(self, text: str, **kwargs) -> PCMStream:
        """Synthesize ``text`` to a raw-PCM stream via the selected provider (ARCH-21).

        The producer twin of `AudioComponent.play_stream`: returns a `PCMStream` (format header + async
        PCM frame iterator) a sink can consume directly. Mirrors `synthesize_to_file`'s provider selection
        and fallback. Each provider streams natively or via the base buffer-then-stream simulation."""
        provider_name = kwargs.get("provider", self.default_provider)
        provider = await self._get_provider(provider_name)
        if provider is not None:
            try:
                return await provider.synthesize_to_stream(text, **kwargs)
            except Exception as e:
                logger.error(f"TTS provider {provider_name} streaming failed: {e}")
        return await self._stream_with_fallback(text, provider_name, **kwargs)

    async def synthesize_and_stream_to(self, audio_component, text: str, **kwargs) -> bool:
        """Synthesize ``text`` to PCM, conform DOWN to the output sink (§8), and stream it on
        ``audio_component`` (ARCH-21). The shared local-speech *stream* path used by both the sync
        workflow reply and the `AudioSpeechOutput` delivery port.

        Returns ``False`` (the caller should fall back to file playback) when no audio negotiator is
        wired or the selected provider can't produce a PCM stream (e.g. text-only console)."""
        from ..intents.models import AudioData
        from ..utils.audio_stream import collect_pcm

        negotiator = getattr(self.core, "audio_negotiator", None)
        if negotiator is None:
            return False
        try:
            stream = await self.synthesize_to_stream(text, **kwargs)
        except Exception as e:
            # Includes NotImplementedError (text-only/MP3 providers) and the no-streamable-provider
            # RuntimeError — any streaming failure means the caller should fall back to file playback.
            logger.debug(f"TTS streaming unavailable ({e}); caller should use file playback")
            return False

        pcm = await collect_pcm(stream.frames)
        producer = AudioData(data=pcm, timestamp=time.time(), sample_rate=stream.sample_rate,
                             channels=stream.channels, format="pcm16")
        conformed = await negotiator.to_sink(producer)
        await audio_component.play_stream(conformed.data, sample_rate=conformed.sample_rate,
                                          channels=conformed.channels, sample_width=stream.sample_width)
        return True

    async def _stream_with_fallback(self, text: str, failed_provider: str, **kwargs) -> PCMStream:
        """Try fallback providers' streaming synthesis when the primary fails (ARCH-21)."""
        for fallback_provider in self.fallback_providers:
            if fallback_provider != failed_provider and fallback_provider in self.providers:
                try:
                    result = await self.providers[fallback_provider].synthesize_to_stream(text, **kwargs)
                    logger.info(f"Used fallback TTS provider for stream: {fallback_provider}")
                    return result
                except Exception as e:
                    logger.warning(f"Fallback TTS provider {fallback_provider} streaming failed: {e}")
                    continue
        logger.error("All TTS providers failed for streaming synthesis")
        raise RuntimeError("No TTS providers available for streaming synthesis")

    def get_supported_voices(self) -> List[str]:
        """Get voices from all available providers"""
        voices = []
        for provider_name, provider in self.providers.items():
            provider_voices = provider.get_capabilities().get("voices", [])
            # Prefix with provider name for uniqueness
            voices.extend([f"{provider_name}:{voice}" for voice in provider_voices])
        return voices
    
    def get_supported_languages(self) -> List[str]:
        """Get languages from all available providers"""
        languages = set()
        for provider in self.providers.values():
            provider_languages = provider.get_capabilities().get("languages", [])
            languages.update(provider_languages)
        return list(languages)
    
    async def is_available(self) -> bool:
        """Check if at least one provider is available"""
        return len(self.providers) > 0
    
    async def _get_provider(self, provider_name: str) -> Optional[TTSProvider]:
        """Get provider with lazy loading support"""
        # First check if provider is already loaded
        if provider_name in self.providers:
            return self.providers[provider_name]
        
        # If lazy loading is enabled, try to load the provider
        if self._lazy_loading_enabled:
            provider = await self._load_provider_lazy(provider_name)
            if provider:
                return provider
        
        return None
    
    async def _synthesize_with_fallback(self, text: str, output_path: Path, **kwargs) -> None:
        """Try fallback providers when primary fails"""
        for fallback_provider in self.fallback_providers:
            if fallback_provider in self.providers:
                try:
                    await self.providers[fallback_provider].synthesize_to_file(text, output_path, **kwargs)
                    logger.info(f"Used fallback TTS provider: {fallback_provider}")
                    return
                except Exception as e:
                    logger.warning(f"Fallback TTS provider {fallback_provider} failed: {e}")
                    continue
        
        # All providers failed
        logger.error("All TTS providers failed")
        raise RuntimeError("No TTS providers available")
    
    # Public methods for intent handler delegation

    
    def set_default_provider(self, provider_name: str) -> bool:
        """Set default TTS provider - simple atomic operation"""
        # Map common names to actual provider names
        provider_mapping = {
            "силеро": "silero_v3",
            "силеро3": "silero_v3", 
            "силеро4": "silero_v4",
            "консоль": "console",
            "системный": "pyttsx",
            "воск": "vosk_tts"
        }
        
        # Try direct match first
        if provider_name in self.providers:
            self.default_provider = provider_name
            return True
            
        # Try mapped name
        mapped_name = provider_mapping.get(provider_name.lower())
        if mapped_name and mapped_name in self.providers:
            self.default_provider = mapped_name
            return True
            
        return False
    
    def switch_provider(self, provider_name: str) -> bool:
        """Override base method with TTS-specific provider name mapping"""
        return self.set_default_provider(provider_name)
    
    def get_providers_info(self) -> str:
        """Implementation of abstract method - Get TTS providers information"""
        if not self.providers:
            return "Нет доступных TTS провайдеров"
        
        info = []
        info.append(f"Доступные TTS провайдеры ({len(self.providers)}):")
        info.append(f"Текущий: {self.default_provider}")
        info.append("")
        
        for provider_name, provider in self.providers.items():
            capabilities = provider.get_capabilities()
            voices = capabilities.get("voices", [])
            languages = capabilities.get("languages", [])
            quality = capabilities.get("quality", "unknown")
            
            info.append(f"• {provider_name} ({quality} качество)")
            info.append(f"  Голоса: {', '.join(voices[:3])}{'...' if len(voices) > 3 else ''}")
            info.append(f"  Языки: {', '.join(languages)}")
            info.append("")
        
        return "\n".join(info)
    

    # WebAPIPlugin interface - unified API
    def get_router(self) -> Optional[Any]:
        """Get FastAPI router with TTS endpoints"""
        if not self.is_api_available():
            return None
            
        try:
            from fastapi import APIRouter, HTTPException  # type: ignore
            from ..config.models import TTSConfig
            from ..api.schemas import (
                TTSRequest, TTSResponse, TTSProvidersResponse,
                TTSConfigureResponse
            )
            import tempfile

            router = APIRouter()
                
            @router.post("/speak", response_model=TTSResponse)
            async def unified_speak(request: TTSRequest):
                """
                Enhanced TTS endpoint with audio format control
                
                Supports configurable audio output format including sample rate, 
                channels, and format specification. Uses AudioData infrastructure
                for high-quality resampling and format conversion.
                """
                try:
                    provider_name = request.provider or self.default_provider
                    
                    if provider_name not in self.providers:
                        raise HTTPException(404, f"Provider '{provider_name}' not available")
                    
                    provider = self.providers[provider_name]
                    if not await provider.is_available():
                        raise HTTPException(503, f"Provider '{provider_name}' temporarily unavailable")
                    
                    # Extract provider-specific parameters
                    kwargs = {
                        "language": request.language
                    }
                    if request.speaker:
                        kwargs["speaker"] = request.speaker
                    
                    # Get audio configuration with defaults
                    from ..api.schemas import AudioConfigRequest
                    audio_config = request.audio_config or AudioConfigRequest()
                    
                    # Create temporary file for synthesis
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                        temp_path = Path(temp_file.name)
                    
                    try:
                        # Synthesize audio to file
                        await provider.synthesize_to_file(
                            request.text,
                            temp_path,
                            **kwargs
                        )
                        
                        # Read and convert audio to requested format
                        from ..intents.models import AudioData
                        
                        # Check if this is a text-only provider (like console)
                        capabilities = provider.get_capabilities()
                        provider_formats = capabilities.get("formats", ["wav"])
                        
                        if "wav" not in provider_formats and "audio" not in provider_formats:
                            # Handle text-only providers (console, debug, etc.)
                            logger.debug(f"Provider {provider_name} is text-only, reading as text")
                            
                            # Read as text and convert to fake audio data
                            with open(temp_path, 'r', encoding='utf-8') as f:
                                text_content = f.read()
                            
                            # Convert text to bytes (fake audio for consistency)
                            text_bytes = text_content.encode('utf-8')
                            audio_base64 = base64.b64encode(text_bytes).decode('utf-8')
                            
                            # Create metadata for text output
                            audio_metadata = {
                                "sample_rate": audio_config.sample_rate,
                                "channels": audio_config.channels,
                                "format": "text",  # Indicate this is text, not audio
                                "duration_ms": len(text_content) * 10,  # Estimate 10ms per character
                                "file_size": len(text_bytes),
                                "content_type": "text"
                            }
                            
                        else:
                            # Handle actual audio providers
                            logger.debug(f"Provider {provider_name} generates audio, processing with AudioData")
                            
                            # Read generated audio file
                            with open(temp_path, 'rb') as f:
                                audio_bytes = f.read()
                            
                            # Get provider capabilities to determine source format
                            provider_sample_rate = capabilities.get("sample_rate", 22050)
                            provider_channels = capabilities.get("channels", 1)
                            
                            # Create AudioData object
                            audio_data = AudioData(
                                data=audio_bytes,
                                timestamp=time.time(),
                                sample_rate=provider_sample_rate,
                                channels=provider_channels,
                                format="wav",
                                metadata={
                                    'source': 'tts_http_provider',
                                    'provider': provider_name,
                                    'text': request.text,
                                    'language': request.language
                                }
                            )
                            
                            # ARCH-18 PR-4c: conform DOWN to the caller's sink (CD default), then read the
                            # actual rate/channels (conform-down may keep a lower native rate).
                            audio_data = await self._conform_to_sink(audio_data, audio_config.sample_rate, audio_config.channels)
                            target_rate = audio_data.sample_rate
                            target_channels = audio_data.channels

                            # Extract PCM data and encode as base64
                            pcm_data = audio_data.data
                            audio_base64 = base64.b64encode(pcm_data).decode('utf-8')
                            
                            # Calculate audio metadata
                            bytes_per_ms = (target_rate * target_channels * 2) // 1000  # 16-bit PCM
                            duration_ms = len(pcm_data) / bytes_per_ms
                            
                            audio_metadata = {
                                "sample_rate": target_rate,
                                "channels": target_channels,
                                "format": audio_config.format,
                                "duration_ms": duration_ms,
                                "file_size": len(pcm_data),
                                "content_type": "audio"
                            }
                        
                        return TTSResponse(
                            success=True,
                            provider=provider_name,
                            text=request.text,
                            audio_content=audio_base64,
                            audio_metadata=audio_metadata
                        )
                        
                    finally:
                        # Clean up temporary file
                        if temp_path.exists():
                            temp_path.unlink()
                    
                except Exception as e:
                    logger.error(f"TTS API error: {e}")
                    return TTSResponse(
                        success=False,
                        provider=request.provider or self.default_provider or "console",
                        text=request.text,
                        error=str(e)
                    )
            
            @router.get("/providers", response_model=TTSProvidersResponse)
            async def list_providers():
                """Discovery endpoint for all provider capabilities"""
                result = {}
                for name, provider in self.providers.items():
                    result[name] = {
                        "available": await provider.is_available(),
                        "parameters": provider.get_parameter_schema(),
                        "capabilities": provider.get_capabilities()
                    }
                
                return TTSProvidersResponse(
                    success=True,
                    providers=result,
                    default=self.default_provider or "console"
                )
            
            @router.post("/configure", response_model=TTSConfigureResponse)
            async def configure_tts(config_update: TTSConfig):
                """Configure TTS settings using unified TOML schema"""
                try:
                    
                    # Apply runtime configuration without TOML persistence
                    config_dict = config_update.model_dump()
                    
                    self._apply_provider_config(config_dict)
                    
                    # Update enabled providers if provided (would require re-initialization)
                    providers_config = config_dict.get("providers", {})
                    if providers_config:
                        logger.info(f"TTS runtime provider configuration updated for {len(providers_config)} providers")
                    
                    # Update fallback providers
                    fallback_providers = config_dict.get("fallback_providers", [])
                    if fallback_providers:
                        logger.info(f"TTS fallback providers updated: {fallback_providers}")
                    
                    return TTSConfigureResponse(
                        success=True,
                        message="TTS configuration applied successfully using unified schema",
                        default_provider=self.default_provider,
                        enabled_providers=list(self.providers.keys()),
                        fallback_providers=fallback_providers
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to configure TTS with unified schema: {e}")
                    return TTSConfigureResponse(
                        success=False,
                        message=f"Failed to apply TTS configuration: {str(e)}",
                        default_provider=self.default_provider,
                        enabled_providers=list(self.providers.keys()),
                        fallback_providers=[]
                    )
            
            return router
            
        except ImportError:
            logger.warning("FastAPI not available for TTS web API")
            return None
    
    def get_api_prefix(self) -> str:
        """Get URL prefix for TTS API endpoints"""
        return "/tts"
    
    def get_api_tags(self) -> list[str]:
        """Get OpenAPI tags for TTS endpoints"""
        return ["Text-To-Speech"]

    # ARCH-21 PR-4: the /tts/stream + /tts/binary WebSocket endpoints were removed (untested
    # request/response synthesis API that contradicts reply-to-device delivery). No WS endpoints
    # remain. (QUAL-18 later retired the AsyncAPI machinery those endpoints were documented with;
    # the live WS protocols are documented in docs/guides/websocket-api.md.)

    # Build dependency methods (TODO #5 Phase 2)
    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        """TTS component needs web API functionality"""
        return ["web-api"]  # FastAPI/uvicorn web stack
    
    # Config interface methods (Phase 3 - Configuration Architecture Cleanup)
    @classmethod
    def get_config_class(cls) -> Type[BaseModel]:
        """Return the Pydantic config model for this component"""
        from ..config.models import TTSConfig
        return TTSConfig
    
    @classmethod
    def get_config_path(cls) -> str:
        """Return the TOML path to this component's config (V14 Architecture)"""
        return "tts" 