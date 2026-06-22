"""
Text Enhancement Intent Handler - Text improvement commands

Handles text enhancement/improvement commands that were previously hardcoded
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


class TextEnhancementIntentHandler(IntentHandler):
    """
    Handles text enhancement intents - text improvement via LLM.
    
    Features:
    - Text improvement and correction
    - Text reformulation
    - Grammar and style enhancement
    """
    
    _error_template = 'error_enhancement'

    
    def __init__(self):
        super().__init__()
        self._llm_component: Optional[LLMPort] = None

    # Build dependency methods (TODO #5 Phase 2)
    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        """Text enhancement handler needs no external dependencies"""
        return []
        
    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        """Text enhancement handler has no system dependencies"""
        return {
            "linux.ubuntu": [],
            "linux.alpine": [],
            "macos": [],
            "windows": []
        }
    async def execute(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Execute text enhancement intent"""
        # Use donation-driven routing exclusively
        return await self.execute_with_donation_routing(intent, context)
        
    async def _handle_enhance_text(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle text enhancement request"""
        llm_component = await self._get_llm_component()
        if not llm_component:
            return self._error_result(context, "LLM component not available")
        
        # Extract text to enhance from command using LLM component helper method
        text_to_enhance = llm_component.extract_text_from_command(intent.raw_text)
        
        # Use language from context (detected by NLU)
        language = context.language
        
        if text_to_enhance:
            try:
                enhanced = await llm_component.enhance_text(text_to_enhance, task="improve", language=context.language, trace_context=self._trace_context)
                trace_event("llm_call", {"method": "enhance_text", "task": "improve",
                                         "chars_in": len(text_to_enhance), "chars_out": len(enhanced or "")},
                            handler="text_enhancement")
                response_text = self._get_template("enhanced_text", language, enhanced=enhanced)
                    
                self.logger.info(f"Text enhancement completed")
                
                return IntentResult(
                    text=response_text,
                    should_speak=True,
                    metadata={
                        "action": "enhance",
                        "original_text": text_to_enhance,
                        "enhanced_text": enhanced,
                        "language": language
                    },
                    success=True
                )
            except Exception as e:
                self.logger.error(f"Text enhancement error: {e}")
                return self._error_result(context, f"Text enhancement failed: {e}")
        else:
            return self._error_result(context, "Could not extract text to enhance")
        
    async def _handle_improve_text(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle text improvement request"""
        llm_component = await self._get_llm_component()
        if not llm_component:
            return self._error_result(context, "LLM component not available")
        
        # Extract text to improve from intent entities
        text_to_improve = intent.entities.get("text")
        
        if not text_to_improve:
            # Try to extract from original command using LLM component
            text_to_improve = llm_component.extract_text_from_command(intent.raw_text)
            
        if not text_to_improve:
            return self._error_result(context, "Text to improve not found")
        
        # QUAL-34: optional improvement_type (CHOICE) steers the LLM via a focus directive.
        focus = self.get_param(intent, "improvement_type", default=None)
        try:
            improved = await llm_component.enhance_text(text_to_improve, task="improve", language=context.language, focus=focus, trace_context=self._trace_context)
            trace_event("llm_call", {"method": "enhance_text", "task": "improve", "focus": focus,
                                     "chars_in": len(text_to_improve), "chars_out": len(improved or "")},
                        handler="text_enhancement")

            # Use language from context (detected by NLU)
            language = context.language
            
            response_text = self._get_template("improved_text", language, improved=improved)
            
            self.logger.info(f"Text improvement completed")
            
            return IntentResult(
                text=response_text,
                should_speak=True,
                metadata={
                    "action": "improve",
                    "original_text": text_to_improve,
                    "improved_text": improved,
                    "language": language
                },
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"Text improvement error: {e}")
            return self._error_result(context, f"Text improvement failed: {e}")
            
    async def _handle_correct_text(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle text correction request"""
        llm_component = await self._get_llm_component()
        if not llm_component:
            return self._error_result(context, "LLM component not available")
        
        # Extract text to correct from intent entities
        text_to_correct = intent.entities.get("text")
        
        if not text_to_correct:
            # Try to extract from original command using LLM component
            text_to_correct = llm_component.extract_text_from_command(intent.raw_text)
            
        if not text_to_correct:
            return self._error_result(context, "Text to correct not found")
        
        # QUAL-34: optional correction_type (CHOICE) steers the LLM via a focus directive.
        focus = self.get_param(intent, "correction_type", default=None)
        try:
            corrected = await llm_component.enhance_text(text_to_correct, task="grammar_correction", language=context.language, focus=focus, trace_context=self._trace_context)
            trace_event("llm_call", {"method": "enhance_text", "task": "grammar_correction", "focus": focus,
                                     "chars_in": len(text_to_correct), "chars_out": len(corrected or "")},
                        handler="text_enhancement")

            # Use language from context (detected by NLU)
            language = context.language
            
            response_text = self._get_template("corrected_text", language, corrected=corrected)
            
            self.logger.info(f"Text correction completed")
            
            return IntentResult(
                text=response_text,
                should_speak=True,
                metadata={
                    "action": "correct",
                    "original_text": text_to_correct,
                    "corrected_text": corrected,
                    "language": language
                },
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"Text correction error: {e}")
            return self._error_result(context, f"Text correction failed: {e}")
    
    async def _get_llm_component(self) -> Optional[LLMPort]:
        """Return the injected LLM capability port (QUAL-24).

        Injected by the application via
        IntentComponent.post_initialize_handler_dependencies; the domain never
        reaches into core for it.
        """
        return self._llm_component
        
    # Build dependency methods (TODO #5 Phase 2)
    # Configuration metadata: No configuration needed
    # This handler delegates to LLM component and uses JSON donations only
    # No get_config_schema() method = no configuration required