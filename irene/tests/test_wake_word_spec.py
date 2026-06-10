"""QUAL-20 — the uniform WakeWordSpec across voice-trigger providers.

Wake words are a per-provider list of {name, model, threshold, language}. These tests lock:
  1. the config-schema path exposes the array item schema (so config-ui renders a structured editor);
  2. the provider base normalizes specs (dicts, pydantic objects, and bare-string tolerance).
"""
from irene.config.auto_registry import AutoSchemaRegistry
from irene.config.models import WakeWordSpec
from irene.providers.voice_trigger.base import VoiceTriggerProvider


def test_config_schema_exposes_wake_word_items():
    """The /config/schema extraction must carry items.properties for wake_words (config-ui editor)."""
    for provider in ("openwakeword", "microwakeword"):
        schema = AutoSchemaRegistry.get_provider_schemas()["voice_trigger"][provider]
        fields = AutoSchemaRegistry._extract_model_schema(schema)["fields"]
        ww = fields["wake_words"]
        assert ww["type"] == "array"
        assert ww["items"]["type"] == "object"
        assert set(ww["items"]["properties"]) == {"name", "model", "threshold", "language"}


def test_base_normalizes_spec_dicts_and_strings():
    norm = VoiceTriggerProvider._normalize_wake_words([
        {"name": "irene", "model": "wake/irene_ru", "threshold": 0.7, "language": "ru"},
        "okay_nabu",                                  # bare string → name == model, defaults
        WakeWordSpec(name="alexa", model="alexa"),    # pydantic object
    ])
    assert [s["name"] for s in norm] == ["irene", "okay_nabu", "alexa"]
    assert norm[0] == {"name": "irene", "model": "wake/irene_ru", "threshold": 0.7, "language": "ru"}
    assert norm[1]["model"] == "okay_nabu" and norm[1]["threshold"] == 0.8 and norm[1]["language"] == "en"
    assert norm[2]["model"] == "alexa"


def test_base_skips_nameless_entries():
    assert VoiceTriggerProvider._normalize_wake_words([{"threshold": 0.9}, {"model": "x"}]) == [
        {"name": "x", "model": "x", "threshold": 0.8, "language": "en"},
    ]
