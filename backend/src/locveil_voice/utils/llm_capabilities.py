"""Per-model LLM token budgets (QUAL-52).

The real context-window + max-output capabilities of the supported models, so the providers stop
using the arbitrary `max_tokens=150` (which truncated replies) and the component can do budget-aware
prompting (QUAL-52 PR2). Values are the documented limits as of 2026; a conservative fallback covers
unknown/new models. No dependency — pure data + a lookup.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


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


def estimate_tokens(text: str) -> int:
    """Approximate token count, dependency-free (QUAL-52 — no tiktoken, so the path stays armv7-safe).

    **utf-8 bytes / 4**: accurate for English (1 byte/char ≈ chars/4) and naturally *conservative* for
    Cyrillic (2 bytes/char ≈ chars/2), which tokenizes ~2× denser. It's a budget guard, not exact
    accounting — over-estimating just trims a little more, never overflows.
    """
    if not text:
        return 0
    return len(text.encode("utf-8")) // 4 + 1


def context_window_for(model: str, override: Optional[int] = None) -> int:
    """The input context-window (tokens) for `model`: the config `override` if set, else the model's
    documented capability. Lets a deployment pin the budget for a custom/unknown model."""
    if override and override > 0:
        return int(override)
    return capabilities_for(model).context_window


def input_budget(context_window: int, reserved_output: int, margin: float = 0.9) -> int:
    """Max input tokens that still leave room for `reserved_output` within `context_window`,
    keeping a `margin` of headroom for the estimate's slack."""
    usable = int(context_window * margin)
    return max(0, usable - reserved_output)


def fit_messages(messages: List[Dict[str, str]], model: str, reserved_output: int,
                 margin: float = 0.9, context_window: Optional[int] = None) -> List[Dict[str, str]]:
    """Trim oldest non-system messages so the estimated input fits the model's context budget (leaving
    room for `reserved_output`). `context_window` overrides the model's documented window (config).
    **System messages and the final message are always kept.** Raises if the kept set still overflows —
    that means the prompt itself is too big and must be scoped upstream (e.g. the QUAL-50 catalog reduced
    to the relevant rooms/capabilities), not blindly truncated."""
    cw = context_window_for(model, context_window)
    budget = input_budget(cw, reserved_output, margin)

    def total(msgs: List[Dict[str, str]]) -> int:
        return sum(estimate_tokens(m.get("content", "")) for m in msgs)

    if total(messages) <= budget:
        return messages
    system = [m for m in messages if m.get("role") == "system"]
    rest = [m for m in messages if m.get("role") != "system"]
    while len(rest) > 1 and total(system + rest) > budget:
        rest.pop(0)  # drop the oldest non-system turn, keep the most recent + the final message
    kept = system + rest
    if total(kept) > budget:
        raise ValueError(
            f"LLM input exceeds the {model} budget ({total(kept)} > {budget} tokens) even after trimming "
            f"history — reduce/scope the system prompt")
    return kept
