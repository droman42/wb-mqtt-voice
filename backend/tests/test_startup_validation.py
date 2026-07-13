"""Unit tests for QUAL-23 startup provider-name validation.

Fast, offline, deterministic — drives `validate_provider_configuration` with
synthetic config dicts (no boot). Relies on the real registered entry-points
in the installed venv (llm: console/openai/deepseek/anthropic; nlu:
hybrid_keyword_matcher/spacy_nlu; tts: console/...).
"""

from locveil_voice.core.startup_validation import validate_provider_configuration


def test_flags_phantom_llm_provider():
    """A configured-but-unregistered LLM provider is flagged; registered ones are not.

    NOTE: `llm.console` USED to be the phantom example (QUAL-14/15) but is now a registered
    offline-floor stub entry-point, so it must NOT be flagged — we use a genuinely-unregistered
    name to keep the phantom-detection path under test.
    """
    cfg = {
        "llm": {
            "enabled": True,
            "default_provider": "openai",
            "fallback_providers": ["ghost_provider", "console"],
            "providers": {"openai": {"enabled": True}, "ghost_provider": {"enabled": True},
                          "console": {"enabled": True}},
        }
    }
    issues = validate_provider_configuration(cfg)
    assert any("provider 'ghost_provider'" in i and i.startswith("llm.") for i in issues), issues
    # registered providers must NOT be flagged (console is now a real offline-floor stub)
    assert not any("provider 'openai'" in i for i in issues), issues
    assert not any("provider 'console'" in i for i in issues), issues


def test_all_good_names_no_issues():
    cfg = {
        "llm": {"enabled": True, "default_provider": "openai", "fallback_providers": []},
        "nlu": {"enabled": True, "provider_cascade_order": ["hybrid_keyword_matcher", "spacy_nlu"]},
        # tts `console` IS a registered entry-point — must not be flagged
        "tts": {"enabled": True, "default_provider": "console", "fallback_providers": ["console"]},
    }
    assert validate_provider_configuration(cfg) == []


def test_disabled_component_is_skipped():
    cfg = {"llm": {"enabled": False, "fallback_providers": ["does_not_exist"]}}
    assert validate_provider_configuration(cfg) == []


def test_flags_bad_nlu_cascade_name():
    """The historical bad cascade default name (QUAL-10) must be caught when configured."""
    cfg = {"nlu": {"enabled": True, "provider_cascade_order": ["keyword_matcher", "spacy_nlu"]}}
    issues = validate_provider_configuration(cfg)
    assert any("provider 'keyword_matcher'" in i for i in issues), issues
    assert not any("provider 'spacy_nlu'" in i for i in issues), issues
