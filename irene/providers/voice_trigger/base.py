"""
Voice Trigger Provider Base Classes

Defines the interface for voice trigger/wake word detection providers.
"""

import logging
from abc import abstractmethod
from typing import Dict, Any, List

from ..base import ProviderBase
from ...intents.models import AudioData, WakeWordResult

logger = logging.getLogger(__name__)


class VoiceTriggerProvider(ProviderBase):
    """
    Base class for voice trigger/wake word detection providers.
    
    Implements the common interface for wake word detection engines
    like OpenWakeWord and microWakeWord.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # QUAL-20: wake words are a uniform list of WakeWordSpec-shaped entries {name, model, threshold,
        # language} across all providers. Tolerate bare strings (name == model) for convenience.
        self.wake_word_specs = self._normalize_wake_words(config.get('wake_words', []))
        self.wake_words = [s['name'] for s in self.wake_word_specs]   # back-compat: the name list
        self.threshold = config.get('threshold', 0.8)
        self.sample_rate = config.get('sample_rate', 16000)
        self.channels = config.get('channels', 1)

    @staticmethod
    def _normalize_wake_words(raw: Any) -> List[Dict[str, Any]]:
        """Coerce the configured wake words to a list of dicts {name, model, threshold, language},
        accepting bare strings, dicts, or pydantic WakeWordSpec objects."""
        specs: List[Dict[str, Any]] = []
        for item in raw or []:
            if isinstance(item, str):
                name = item
                model, threshold, language = item, 0.8, "en"
            elif isinstance(item, dict):
                name = item.get("name") or item.get("model") or ""
                model = item.get("model") or name
                threshold = float(item.get("threshold", 0.8))
                language = item.get("language", "en")
            else:  # pydantic WakeWordSpec (or any attr-bearing object)
                name = getattr(item, "name", "") or getattr(item, "model", "")
                model = getattr(item, "model", "") or name
                threshold = float(getattr(item, "threshold", 0.8))
                language = getattr(item, "language", "en")
            if name:
                specs.append({"name": name, "model": model, "threshold": threshold, "language": language})
        return specs
        
    @abstractmethod
    async def detect_wake_word(self, audio_data: AudioData) -> WakeWordResult:
        """
        Detect wake word in audio data.
        
        Args:
            audio_data: Audio data to analyze
            
        Returns:
            WakeWordResult with detection status and metadata
        """
        pass
    
    @abstractmethod
    def get_supported_wake_words(self) -> List[str]:
        """
        Get list of wake words supported by this provider.
        
        Returns:
            List of supported wake words
        """
        pass
    
    def get_parameter_schema(self) -> Dict[str, Any]:
        """
        Auto-generate parameter schema from Pydantic model.
        
        Returns:
            Dictionary describing configurable parameters
        """
        from irene.config.auto_registry import AutoSchemaRegistry
        
        # Extract component type from module path
        component_type = self.__class__.__module__.split('.')[-2]  # e.g., 'tts', 'audio'
        provider_name = self.get_provider_name()
        
        return AutoSchemaRegistry.get_provider_parameter_schema(component_type, provider_name)
    
    @abstractmethod
    def get_supported_sample_rates(self) -> List[int]:
        """
        Get list of supported sample rates (Phase 3).
        
        Returns:
            List of supported sample rates in Hz
        """
        pass
    
    @abstractmethod
    def get_default_sample_rate(self) -> int:
        """
        Get default/optimal sample rate for this provider (Phase 3).
        
        Returns:
            Default sample rate in Hz
        """
        pass
    
    @abstractmethod
    def supports_resampling(self) -> bool:
        """
        Check if this provider supports automatic resampling (Phase 3).
        
        Returns:
            True if provider can handle resampling internally
        """
        pass
    
    @abstractmethod
    def get_default_channels(self) -> int:
        """
        Get default number of audio channels for this provider (Phase 3).
        
        Returns:
            Default number of channels (1 for mono, 2 for stereo)
        """
        pass
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get provider capabilities and metadata.
        
        Returns:
            Dictionary with provider capabilities
        """
        return {
            "wake_words": self.get_supported_wake_words(),
            "sample_rates": [16000, 22050, 44100],
            "channels": [1],
            "formats": ["pcm16"],
            "real_time": True,
            "configurable_threshold": True,
            "multiple_wake_words": len(self.get_supported_wake_words()) > 1
        }
    
    async def set_wake_words(self, wake_words: List[str]) -> bool:
        """
        Set active wake words.
        
        Args:
            wake_words: List of wake words to activate
            
        Returns:
            True if successfully set
        """
        supported = self.get_supported_wake_words()
        valid_words = [word for word in wake_words if word in supported]
        
        if not valid_words:
            self.logger.warning(f"No valid wake words from {wake_words}. Supported: {supported}")
            return False
        
        self.wake_words = valid_words
        self.logger.info(f"Active wake words set to: {valid_words}")
        return True
    
    async def set_threshold(self, threshold: float) -> bool:
        """
        Set detection threshold.
        
        Args:
            threshold: Detection threshold (0.0 - 1.0)
            
        Returns:
            True if successfully set
        """
        if not 0.0 <= threshold <= 1.0:
            self.logger.warning(f"Invalid threshold {threshold}, must be between 0.0 and 1.0")
            return False
        
        self.threshold = threshold
        self.logger.info(f"Detection threshold set to: {threshold}")
        return True
    
    def validate_config(self) -> bool:
        """Validate voice trigger provider configuration."""
        if not isinstance(self.wake_words, list) or not self.wake_words:
            self.logger.error("wake_words must be a non-empty list")
            return False
        
        if not 0.0 <= self.threshold <= 1.0:
            self.logger.error(f"threshold must be between 0.0 and 1.0, got {self.threshold}")
            return False
        
        if self.sample_rate not in [8000, 16000, 22050, 44100, 48000]:
            self.logger.error(f"Unsupported sample rate: {self.sample_rate}")
            return False
        
        return True 