"""
Translation Intent Handler - Text translation commands

Handles text translation commands that were previously hardcoded
in LLMComponent. Delegates to LLMComponent for actual functionality.
"""

import logging
from typing import List, Dict, Optional

from .base import IntentHandler
from ...core.trace_context import trace_event  # ARCH-19 (D-5): opt-in, no-op when no trace is active
from ..models import Intent, IntentResult
from ..context_models import UnifiedConversationContext
from ..ports import LLMPort

logger = logging.getLogger(__name__)


class TranslationIntentHandler(IntentHandler):
    """
    Handles translation intents - text translation via LLM.
    
    Features:
    - Text translation between languages
    - Language detection and specification
    - Translation request parsing
    """
    
    _error_template = 'error_translation'

    
    def __init__(self):
        super().__init__()
        self._llm_component: Optional[LLMPort] = None

    # Build dependency methods (TODO #5 Phase 2)
    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        """Translation handler needs no external dependencies"""
        return []
        
    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        """Translation handler has no system dependencies"""
        return {
            "linux.ubuntu": [],
            "linux.alpine": [],
            "macos": [],
            "windows": []
        }
    async def execute(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Execute translation intent"""
        # Use donation-driven routing exclusively
        return await self.execute_with_donation_routing(intent, context)
        
    async def _handle_translate_text(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle text translation request"""
        llm_component = await self._get_llm_component()
        if not llm_component:
            return self._error_result(context, "LLM component not available")
        
        # Extract text and target language from command using LLM component helper methods
        text_and_lang = llm_component.extract_translation_request(intent.raw_text)
        
        # Use language from context (detected by NLU) for response
        language = context.language
        
        if text_and_lang:
            text, target_lang = text_and_lang
            try:
                translated = await llm_component.enhance_text(text, task="translation", target_language=target_lang, language=context.language, trace_context=self._trace_context)
                trace_event("llm_call", {"method": "enhance_text", "task": "translation",
                                         "target_language": target_lang, "chars_in": len(text),
                                         "chars_out": len(translated or "")}, handler="translation")
                response_text = self._get_template("translation_result", language, translated=translated)
                    
                self.logger.info(f"Translation completed: {text} -> {target_lang}")
                
                return IntentResult(
                    text=response_text,
                    should_speak=True,
                    metadata={
                        "action": "translate",
                        "original_text": text,
                        "target_language": target_lang,
                        "translated_text": translated,
                        "language": language
                    },
                    success=True
                )
            except Exception as e:
                self.logger.error(f"Translation error: {e}")
                return self._error_result(context, f"Translation failed: {e}")
        else:
            return self._error_result(context, "Could not extract text to translate")
        
    async def _handle_translate_specific(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle specific text translation with extracted entities"""
        llm_component = await self._get_llm_component()
        if not llm_component:
            return self._error_result(context, "LLM component not available")
        
        # Use language from context (detected by NLU) first
        language = context.language
        
        # Extract text and target language from intent entities
        text_to_translate = intent.entities.get("text")
        target_language = intent.entities.get("target_language", self._get_template("default_target_language", language))
        
        if not text_to_translate:
            # Try to extract from original command using LLM component
            extraction_result = llm_component.extract_translation_request(intent.raw_text)
            if extraction_result:
                text_to_translate, target_language = extraction_result
            else:
                return self._error_result(context, "Text to translate not found")
        
        try:
            translated = await llm_component.enhance_text(
                text_to_translate, 
                task="translation", 
                target_language=target_language,
                language=context.language,
                trace_context=self._trace_context
            )
            trace_event("llm_call", {"method": "enhance_text", "task": "translation",
                                     "target_language": target_language, "chars_in": len(text_to_translate),
                                     "chars_out": len(translated or "")}, handler="translation")

            response_text = self._get_template("translation_result", language, translated=translated)
            
            self.logger.info(f"Specific translation: {text_to_translate} -> {target_language}")
            
            return IntentResult(
                text=response_text,
                should_speak=True,
                metadata={
                    "action": "translate_specific",
                    "original_text": text_to_translate,
                    "target_language": target_language,
                    "translated_text": translated,
                    "language": language
                },
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"Translation error: {e}")
            return self._error_result(context, f"Translation failed: {e}")
    
    async def _get_llm_component(self) -> Optional[LLMPort]:
        """Return the injected LLM capability port (QUAL-24).

        Injected by the application via
        IntentComponent.post_initialize_handler_dependencies; the domain never
        reaches into core for it.
        """
        return self._llm_component
        
    # Build dependency methods (TODO #5 Phase 2)
    # Configuration metadata: No configuration needed
    # This handler delegates to LLM component and uses asset loader for language mappings
    # No get_config_schema() method = no configuration required
