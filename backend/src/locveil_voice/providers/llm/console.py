"""
Console LLM Provider — the offline floor (QUAL-15).

A deterministic, dependency-free, no-network LLM provider. It is NOT a real language model: it is the
honest offline floor that makes `fallback_providers=["console"]` resolve, stops `generate_response` from
crashing when no cloud LLM is reachable, and gives a clean localized "a language model isn't available"
message instead of a stack trace. A real offline LLM (a local model) is the ARCH-9/10 [INFER] story.

The component's `is_available()` deliberately does NOT count this stub as a real LLM, so callers that
gate LLM-vs-their-own-fallback (e.g. the conversation handler's template path) are unaffected.
"""

import logging
from typing import Dict, Any, List

from .base import LLMProvider

logger = logging.getLogger(__name__)

# Absolute last-resort only (the localized text lives in assets/localization/llm/<lang>.yaml and is
# injected into `_responses` by the component; this fires only if both the asset and config are absent).
_LAST_RESORT = "Sorry, a language model isn't available right now."


class ConsoleLLMProvider(LLMProvider):
    """Deterministic offline-floor LLM (no network, no key, always available)."""

    # Marks this as a stub so the component can exclude it from "a real LLM is available".
    is_stub: bool = True

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Per-language messages ({lang: text}). Source priority: the component injects the localized
        # asset (assets/localization/llm/<lang>.yaml) into this dict; an optional `responses`/`response`
        # in TOML can pre-seed it; else the single _LAST_RESORT is used.
        self._responses: Dict[str, str] = {}
        if isinstance(config.get("responses"), dict):
            self._responses.update(config["responses"])
        elif config.get("response"):
            self._responses = {"ru": config["response"], "en": config["response"]}
        self._default_language = config.get("default_language", "ru")

    def _message(self, **kwargs) -> str:
        # default_language is injected from the ONE canonical source (QUAL-36); no local "ru".
        lang = kwargs.get("language") or self._default_language
        return self._responses.get(lang) or self._responses.get(self._default_language) or _LAST_RESORT

    @classmethod
    def _get_default_credentials(cls) -> List[str]:
        return []  # no API key

    @classmethod
    def _get_default_model_urls(cls) -> Dict[str, str]:
        return {}  # no downloads

    async def is_available(self) -> bool:
        """Always available — that's the whole point of an offline floor."""
        return True

    async def chat_completion(self, messages: List[Dict], **kwargs) -> str:
        """Return the localized 'unavailable' message (no real generation)."""
        return self._message(**kwargs)

    async def enhance_text(self, text: str, task: str = "improve", **kwargs) -> str:
        """No-op enhancement — return the original text unchanged (the honest offline floor for
        enhance tasks like translation/grammar; can't enhance without a model)."""
        return text

    def get_available_models(self) -> List[str]:
        return ["console"]

    def get_supported_tasks(self) -> List[str]:
        return ["improve", "translation", "grammar_correction", "summarize", "expand"]

    def get_provider_name(self) -> str:
        return "console"

    def validate_config(self) -> bool:
        return True

    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        return []  # pure-Python

    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        return {"linux.ubuntu": [], "linux.alpine": [], "macos": [], "windows": []}
