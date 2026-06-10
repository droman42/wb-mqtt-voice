"""
ASR Provider Base Classes

Abstract base class for all ASR (Automatic Speech Recognition) implementations.
Following ABC inheritance pattern for type safety and runtime validation.
"""

from abc import abstractmethod
from typing import Dict, Any, List, AsyncIterator, Optional

from ..base import ProviderBase


class ASRProvider(ProviderBase):
    """
    Abstract base class for speech recognition implementations.
    
    Enhanced in TODO #4 Phase 1 with proper ProviderBase inheritance.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with provider-specific configuration
        
        Args:
            config: Provider-specific configuration dictionary
        """
        # Call ProviderBase.__init__ to get status tracking, logging, etc.
        super().__init__(config)
    
    @abstractmethod
    async def transcribe_audio(self, audio_data: bytes, **kwargs) -> str:
        """Transcribe audio data to text
        
        Args:
            audio_data: Raw audio bytes to transcribe
            **kwargs: Provider-specific parameters (language, confidence_threshold, etc.)
            
        Returns:
            Transcribed text string
        """
        pass
    
    @abstractmethod
    def transcribe_stream(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[str]:
        """Transcribe streaming audio data

        Returns an async iterator of transcribed text chunks. Implementations are
        async generators (`async def` + `yield`); the base is declared as a plain
        `def` returning `AsyncIterator[str]` so those async-generator overrides are
        type-compatible (an async generator IS an AsyncIterator). QUAL-4d.

        Args:
            audio_stream: Async iterator of audio chunks

        Yields:
            Transcribed text chunks as they become available
        """
        ...
    
    def get_parameter_schema(self) -> Dict[str, Any]:
        """Auto-generate parameter schema from Pydantic model
        
        Returns:
            Dictionary describing available parameters, types, and defaults
        """
        from irene.config.auto_registry import AutoSchemaRegistry
        
        # Extract component type from module path
        component_type = self.__class__.__module__.split('.')[-2]  # e.g., 'tts', 'audio'
        provider_name = self.get_provider_name()
        
        return AutoSchemaRegistry.get_provider_parameter_schema(component_type, provider_name)
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """Return list of supported language codes
        
        Returns:
            List of language codes (e.g., ['ru', 'en', 'es'])
        """
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Return list of supported audio formats
        
        Returns:
            List of format strings (e.g., ['wav', 'mp3', 'flac'])
        """
        pass
    
    @abstractmethod
    def get_preferred_sample_rates(self) -> List[int]:
        """Return list of preferred sample rates in order of preference (Phase 3)
        
        Returns:
            List of sample rates in Hz, ordered by preference (best first)
        """
        pass
    
    @abstractmethod
    def supports_sample_rate(self, rate: int) -> bool:
        """Check if this provider supports a specific sample rate (Phase 3)
        
        Args:
            rate: Sample rate in Hz to check
            
        Returns:
            True if the sample rate is supported, False otherwise
        """
        pass
    
    async def set_language(self, language: str) -> None:
        """Set the recognition language (optional override)
        
        Args:
            language: Language code to set
            
        Note:
            Default implementation does nothing. Override if dynamic language
            switching is supported by the provider.
        """
        pass
    
    def reset(self, language: Optional[str] = None) -> bool:
        """Reset provider state to prevent contamination between utterances
        
        This method should clear any internal state that might persist between
        transcription calls, ensuring clean processing for each new utterance.
        
        Args:
            language: Language code to reset (None = reset all languages)
            
        Returns:
            True if reset was successful, False otherwise
            
        Note:
            Default implementation does nothing and returns True. Override this
            method if your provider maintains internal state that needs clearing.
            This is particularly important for providers like VOSK that cache
            recognizer instances with persistent internal state.
        """
        return True
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return provider capabilities (optional override)
        
        Returns:
            Dictionary with capability information
        """
        return {
            "languages": self.get_supported_languages(),
            "formats": self.get_supported_formats(),
            "streaming": True,  # Most providers support streaming
            "real_time": False,  # Override if real-time processing supported
            "confidence_scores": False  # Override if confidence scores provided
        }

    def audio_contract(self):
        """What this ASR engine needs from the pipeline (ARCH-18). ASR is 16 kHz-standard; a provider with
        a `get_supported_sample_rates` is honoured if present."""
        from ...utils.audio_negotiation import AudioContract
        get_rates = getattr(self, "get_supported_sample_rates", None)
        rates: List[int] = [16000]
        if callable(get_rates):
            result: Any = get_rates()
            if result:
                rates = [int(r) for r in result]
        return AudioContract(rates, rates[0], ["pcm16"], "pcm16", 1)