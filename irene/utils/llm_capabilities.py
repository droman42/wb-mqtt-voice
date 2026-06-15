"""Per-model LLM token budgets (QUAL-52).

The real context-window + max-output capabilities of the supported models, so the providers stop
using the arbitrary `max_tokens=150` (which truncated replies) and the component can do budget-aware
prompting (QUAL-52 PR2). Values are the documented limits as of 2026; a conservative fallback covers
unknown/new models. No dependency — pure data + a lookup.
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class ModelCapabilities:
    context_window: int   # total input + output token budget the model accepts
    max_output: int       # max tokens the model will generate in one response


# Documented limits (2026). Extend as models are added.
_CAPABILITIES: Dict[str, ModelCapabilities] = {
    # DeepSeek (OpenAI-compatible API)
    "deepseek-chat":     ModelCapabilities(context_window=64_000, max_output=8_000),
    "deepseek-reasoner": ModelCapabilities(context_window=64_000, max_output=8_000),
    # OpenAI
    "gpt-4o":            ModelCapabilities(context_window=128_000, max_output=16_384),
    "gpt-4o-mini":       ModelCapabilities(context_window=128_000, max_output=16_384),
    "gpt-4":             ModelCapabilities(context_window=8_192,   max_output=4_096),
    "gpt-3.5-turbo":     ModelCapabilities(context_window=16_385,  max_output=4_096),
    # Anthropic Claude (4.x)
    "claude-haiku-4-5":  ModelCapabilities(context_window=200_000, max_output=8_192),
    "claude-sonnet-4-6": ModelCapabilities(context_window=200_000, max_output=8_192),
    "claude-opus-4-8":   ModelCapabilities(context_window=200_000, max_output=8_192),
}

# Conservative fallback for unknown models — small budgets so we never over-promise.
_FALLBACK = ModelCapabilities(context_window=8_192, max_output=2_048)


def capabilities_for(model: str) -> ModelCapabilities:
    """The model's documented budgets, or a conservative fallback.

    Matches exact id first, then the longest registered prefix (so versioned ids like
    `gpt-4o-2024-08-06` or `claude-haiku-4-5-20251001` resolve to their base model).
    """
    if model in _CAPABILITIES:
        return _CAPABILITIES[model]
    best = ""
    for name in _CAPABILITIES:
        if model.startswith(name) and len(name) > len(best):
            best = name
    return _CAPABILITIES[best] if best else _FALLBACK


def output_budget(model: str, requested: Optional[int] = None) -> int:
    """The output-token cap for `model`: `requested` bounded by the model's real `max_output`, or the
    model's `max_output` when unset (replacing the old arbitrary 150). The cap is a ceiling — the model
    stops on its own for short replies."""
    cap = capabilities_for(model).max_output
    if requested and requested > 0:
        return min(int(requested), cap)
    return cap
