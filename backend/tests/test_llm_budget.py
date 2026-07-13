"""Budget-aware prompting (QUAL-52 PR2) — dependency-free token estimate + trim-to-fit."""

import pytest

from locveil_voice.utils.llm_capabilities import (
    estimate_tokens, input_budget, fit_messages, context_window_for,
)


def test_estimate_tokens_is_byte_based_and_conservative_for_cyrillic():
    assert estimate_tokens("") == 0
    assert estimate_tokens("hello world") == len("hello world".encode("utf-8")) // 4 + 1
    ru = "привет мир"
    # Cyrillic = 2 bytes/char → bytes/4 over-counts vs the English chars/4 rule (the safe direction).
    assert estimate_tokens(ru) > len(ru) // 4


def test_input_budget_reserves_room_for_output():
    # context 64000, margin 0.9 → 57600 usable, minus the reserved output.
    assert input_budget(64_000, 8000) == int(64_000 * 0.9) - 8000


def test_context_window_from_registry_or_config_override():
    assert context_window_for("deepseek-chat") == 64_000          # from the model registry
    assert context_window_for("deepseek-chat", 100_000) == 100_000  # config override wins (custom model)
    assert context_window_for("some-unknown-model") == 8_192       # conservative fallback


def test_fit_messages_passthrough_when_within_budget():
    msgs = [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}]
    assert fit_messages(msgs, "deepseek-chat", 100) == msgs


def test_fit_messages_trims_oldest_keeps_system_and_final():
    big = "x" * 200_000  # ~50k tokens each
    msgs = [
        {"role": "system", "content": "S"},
        {"role": "user", "content": big},        # oldest → dropped
        {"role": "assistant", "content": big},
        {"role": "user", "content": "current"},  # final → always kept
    ]
    kept = fit_messages(msgs, "deepseek-chat", 1000)
    assert kept[0]["role"] == "system"
    assert kept[-1]["content"] == "current"
    assert len(kept) < len(msgs)


def test_fit_messages_raises_when_system_prompt_alone_overflows():
    msgs = [
        {"role": "system", "content": "x" * 2_000_000},  # ~500k tokens > any budget
        {"role": "user", "content": "hi"},
    ]
    with pytest.raises(ValueError):
        fit_messages(msgs, "deepseek-chat", 1000)
