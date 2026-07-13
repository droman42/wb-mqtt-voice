"""
Anthropic LLM Provider

Anthropic Claude LLM provider implementation.
Provides high-quality text enhancement and chat capabilities.
"""

import os
from typing import Dict, Any, List
import logging

from .base import LLMProvider, _GENERIC_SYSTEM_FALLBACK, _LLM_TEMPERATURE
from ...utils.llm_capabilities import output_budget, fit_messages

logger = logging.getLogger(__name__)


class AnthropicLLMProvider(LLMProvider):
    """Anthropic Claude LLM Provider"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Anthropic provider with configuration
        
        Args:
            config: Provider configuration containing:
                - api_key_env: Environment variable name for API key (deprecated - uses asset manager)
                - default_model: Default model to use
                - max_tokens: Maximum tokens in response
        """
        super().__init__(config)  # Proper ABC inheritance
        
        # Asset management integration for credentials
        from ...core.assets import get_asset_manager
        self.asset_manager = get_asset_manager()
        
        # Get API key through asset manager or fallback to config
        credentials = self.asset_manager.get_credentials("anthropic")
        self.api_key = credentials.get("anthropic_api_key") or os.getenv(config.get("api_key_env", "ANTHROPIC_API_KEY"))
        
        if not self.api_key and config.get("api_key_env"):
            logger.warning("Using legacy api_key_env config. Consider using ANTHROPIC_API_KEY environment variable.")
            
        self.default_model = config.get("default_model", "claude-haiku-4-5-20251001")
        self.max_tokens = config.get("max_tokens")  # None -> model max_output (QUAL-52)
        self.context_window = config.get("context_window")  # None -> model capability (QUAL-52)
        self.timeout = config.get("timeout", 30)  # per-call timeout (s) — never hang offline
        
    @classmethod
    def _get_default_extension(cls) -> str:
        """Anthropic is API-based, no persistent files"""
        return ""
    
    @classmethod
    def _get_default_directory(cls) -> str:
        """Anthropic directory for temp files"""
        return "anthropic"
    
    @classmethod
    def _get_default_credentials(cls) -> List[str]:
        """Anthropic needs API key"""
        return ["ANTHROPIC_API_KEY"]
    
    @classmethod
    def _get_default_cache_types(cls) -> List[str]:
        """Anthropic uses runtime cache for API responses"""
        return ["runtime"]
    
    @classmethod
    def _get_default_model_urls(cls) -> Dict[str, str]:
        """Anthropic is API-based, no model downloads"""
        return {}
    
    async def is_available(self) -> bool:
        """Check if Anthropic API is available"""
        try:
            import anthropic  # noqa: F401  # availability probe
            return self.api_key is not None
        except ImportError:
            logger.warning("Anthropic library not available")
            return False
    
    async def enhance_text(self, text: str, task: str = "improve", **kwargs) -> str:
        """Enhance text using Anthropic Claude. The hardened, externalized system prompt is resolved by
        the component and passed in `system_prompt` (QUAL-16)."""
        model = kwargs.get("model") or self.default_model  # Handle None model parameter
        max_tokens = output_budget(model, kwargs.get("max_tokens", self.max_tokens))
        system_prompt = kwargs.get("system_prompt") or _GENERIC_SYSTEM_FALLBACK

        try:
            from anthropic import AsyncAnthropic  # type: ignore
            from anthropic.types import TextBlock
            client = AsyncAnthropic(api_key=self.api_key, timeout=self.timeout)

            response = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=_LLM_TEMPERATURE,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": text}
                ]
            )

            # `content` is a discriminated union of blocks; take the first text block
            # (skipping any thinking/tool-use blocks), "" if none present.
            text_out = next((b.text for b in response.content if isinstance(b, TextBlock)), "")
            return text_out.strip()
            
        except Exception as e:
            logger.error(f"Anthropic enhancement failed: {e}")
            raise  # QUAL-15: signal failure so the component's fallback chain takes over
    
    async def chat_completion(self, messages: List[Dict], **kwargs) -> str:
        """Generate chat completion using Anthropic Claude"""
        model = kwargs.get("model") or self.default_model  # Handle None model parameter
        max_tokens = output_budget(model, kwargs.get("max_tokens", self.max_tokens))
        messages = fit_messages(messages, model, max_tokens, context_window=self.context_window)  # QUAL-52: input within context window
        
        try:
            from anthropic import AsyncAnthropic  # type: ignore
            from anthropic.types import TextBlock
            client = AsyncAnthropic(api_key=self.api_key, timeout=self.timeout)

            # Convert messages format for Anthropic (extract system message if present)
            system_message = ""
            user_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    user_messages.append(msg)
            
            response = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=_LLM_TEMPERATURE,
                system=system_message if system_message else _GENERIC_SYSTEM_FALLBACK,
                messages=user_messages
            )
            
            # `content` is a discriminated union of blocks; take the first text block
            # (skipping any thinking/tool-use blocks), "" if none present.
            text_out = next((b.text for b in response.content if isinstance(b, TextBlock)), "")
            return text_out.strip()

        except Exception as e:
            logger.error(f"Anthropic chat completion failed: {e}")
            raise  # QUAL-15: signal failure so the component falls through to the next provider / console
    
    def get_available_models(self) -> List[str]:
        """Return list of available Anthropic models"""
        return [
            "claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5-20251001",
            "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"
        ]
    
    # get_supported_tasks() inherited from LLMProvider (identical cloud task set, CR-C7).

    def get_provider_name(self) -> str:
        """Return provider identifier"""
        return "anthropic"

    # Build dependency methods (TODO #5 Phase 1)
    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        """Anthropic requires the llm-anthropic build extra"""
        return ["llm-anthropic"]  # Build extra: llm-anthropic

    # get_platform_dependencies()/get_platform_support() inherited from EntryPointMetadata —
    # the base defaults (no system deps, all platforms) are byte-identical (CR-C7).

    def get_capabilities(self) -> Dict[str, Any]:
        """Return Anthropic provider capabilities"""
        return {
            "models": self.get_available_models(),
            "tasks": self.get_supported_tasks(),
            "streaming": True,  # Anthropic supports streaming
            "multimodal": True,  # Claude 3 supports images
            "function_calling": True,  # Tool use support
            "high_quality": True,  # Very high quality
            "multilingual": True,  # Supports many languages
            "cloud_based": True,  # Requires internet connection
            "safety_focused": True,  # Strong safety measures
            "large_context": True  # Large context windows
        } 