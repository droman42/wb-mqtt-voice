"""
Speech Recognition Intent Handler - ASR configuration

Handles speech recognition configuration commands that were previously hardcoded
in ASRComponent. Delegates to ASRComponent for actual functionality.
"""

import logging
from typing import List, Dict, Optional

from .base import IntentHandler
from ...core.trace_context import trace_event  # ARCH-19 (D-5): opt-in, no-op when no trace is active
from ..models import Intent, IntentResult
from ..context_models import UnifiedConversationContext
from ..ports import ASRPort

logger = logging.getLogger(__name__)


class SpeechRecognitionIntentHandler(IntentHandler):
    """
    Handles speech recognition intents - ASR configuration.
    
    Features:
    - ASR provider switching
    - ASR provider information display
    - Language switching for ASR
    - ASR configuration management
    """
    
    _error_template = 'error_configuration'

    
    def __init__(self):
        super().__init__()
        self._asr_component: Optional[ASRPort] = None

    # Build dependency methods (TODO #5 Phase 2)
    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        """Speech recognition handler needs no external dependencies"""
        return []
        
    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        """Speech recognition handler has no system dependencies"""
        return {
            "linux.ubuntu": [],
            "linux.alpine": [],
            "macos": [],
            "windows": []
        }
    async def execute(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Execute speech recognition intent"""
        # Use donation-driven routing exclusively
        return await self.execute_with_donation_routing(intent, context)
        
    async def _handle_show_recognition(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle show ASR providers request"""
        asr_component = await self._get_asr_component()
        if not asr_component:
            return self._error_result(context, "ASR component not available")
        
        info = asr_component.get_providers_info()
        
        # Use language from context (detected by NLU)
        language = context.language
        
        self.logger.info(f"ASR providers info requested")
        
        return IntentResult(
            text=info,
            should_speak=True,
            metadata={
                "action": "show_recognition",
                "language": language
            },
            success=True
        )
        
    async def _handle_switch_asr_provider(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle ASR provider switching request"""
        asr_component = await self._get_asr_component()
        if not asr_component:
            return self._error_result(context, "ASR component not available")
        
        # Extract provider name from intent entities or text
        provider_name = intent.entities.get("provider")
        if not provider_name:
            provider_name = asr_component.parse_provider_name_from_text(intent.raw_text)
        
        if not provider_name:
            return self._error_result(context, "Provider name not specified")
        
        # Use language from context (detected by NLU)
        language = context.language
        
        success = asr_component.set_default_provider(provider_name)
        trace_event("provider_switch", {"component": "asr", "provider": provider_name,
                                        "success": bool(success)}, handler="speech_recognition")

        if success:
            message = self._get_template("provider_switched", language, provider_name=provider_name)
        else:
            message = self._get_template("provider_unavailable", language, provider_name=provider_name)
        
        self.logger.info(f"ASR provider switch to {provider_name} - success: {success}")
        
        return IntentResult(
            text=message,
            should_speak=True,
            metadata={
                "action": "switch_provider",
                "provider": provider_name,
                "success": success,
                "language": language
            },
            success=success
        )
        
    async def _handle_switch_language(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle ASR language switching request"""
        asr_component = await self._get_asr_component()
        if not asr_component:
            return self._error_result(context, "ASR component not available")
        
        # Extract language from intent entities
        target_language = intent.entities.get("language", "русский")
        
        success, message = await asr_component.switch_language(target_language)
        
        # Use language from context (detected by NLU)
        language = context.language
        
        self.logger.info(f"ASR language switch to {target_language} - success: {success}")
        
        return IntentResult(
            text=message,
            should_speak=True,
            metadata={
                "action": "switch_language",
                "target_language": target_language,
                "success": success,
                "language": language
            },
            success=success
        )
        
    async def _handle_configure_quality(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle ASR quality configuration request"""
        # Extract quality setting from intent entities
        quality = intent.entities.get("quality", "high")
        
        # Use language from context (detected by NLU)
        language = context.language
        
        # TODO: Implement quality configuration logic
        response_text = self._get_template("quality_not_implemented", language, quality=quality)
        
        self.logger.info(f"ASR quality configuration request: {quality}")
        
        return IntentResult(
            text=response_text,
            should_speak=True,
            metadata={
                "action": "configure_quality",
                "quality": quality,
                "language": language,
                "implemented": False
            },
            success=False
        )
        
    async def _handle_configure_microphone(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle microphone configuration request"""
        # Extract microphone device from intent entities
        microphone = intent.entities.get("microphone", "default")
        
        # Use language from context (detected by NLU)
        language = context.language
        
        # TODO: Implement microphone configuration logic
        response_text = self._get_template("microphone_not_implemented", language, microphone=microphone)
        
        self.logger.info(f"Microphone configuration request: {microphone}")
        
        return IntentResult(
            text=response_text,
            should_speak=True,
            metadata={
                "action": "configure_microphone",
                "microphone": microphone,
                "language": language,
                "implemented": False
            },
            success=False
        )
    
    async def _get_asr_component(self) -> Optional[ASRPort]:
        """Return the injected ASR capability port (QUAL-24).

        Injected by the application via
        IntentComponent.post_initialize_handler_dependencies; the domain never
        reaches into core for it.
        """
        return self._asr_component
        
    # Build dependency methods (TODO #5 Phase 2)
    # Configuration metadata: No configuration needed
    # This handler delegates to ASR component and uses asset loader for provider mappings
    # No get_config_schema() method = no configuration required
