"""Per-model LLM token budgets (QUAL-52 PR1).

The providers no longer truncate at the arbitrary 150 — they default to the model's real max_output
and cap any requested value at it.
"""

from irene.utils.llm_capabilities import capabilities_for, output_budget


def test_known_models_have_real_budgets():
    assert capabilities_for("deepseek-chat").max_output == 8000
    assert capabilities_for("gpt-4o").context_window == 128_000
    assert capabilities_for("claude-haiku-4-5").max_output == 8192


def test_versioned_id_resolves_by_longest_prefix():
    assert capabilities_for("claude-haiku-4-5-20251001").max_output == 8192
    assert capabilities_for("gpt-4o-2024-08-06").context_window == 128_000
    # gpt-4o-mini must win over gpt-4o for the mini id (longest-prefix match)
    assert capabilities_for("gpt-4o-mini").context_window == 128_000


def test_unknown_model_uses_conservative_fallback():
    caps = capabilities_for("some-future-model-x")
    assert caps.context_window == 8192 and caps.max_output == 2048


def test_output_budget_defaults_to_model_max_not_150():
    assert output_budget("deepseek-chat", None) == 8000   # the point: no more arbitrary 150
    assert output_budget("deepseek-chat") == 8000


def test_output_budget_caps_request_at_model_max():
    assert output_budget("deepseek-chat", 500) == 500       # within the cap
    assert output_budget("deepseek-chat", 99_999) == 8000   # capped at the model max
    assert output_budget("gpt-4", 99_999) == 4096           # different model, different cap
