"""`--set DOTTED.KEY=VALUE` config overrides (locveil_voice.config.manager.apply_dotted_overrides)."""
import pytest

from locveil_voice.config.manager import apply_dotted_overrides


def test_json_typed_coercion():
    data = {}
    apply_dotted_overrides(data, [
        "trace.enabled=true",
        "nlu.confidence_threshold=0.5",
        "trace.max_stages=200",
        "system.name=null",
    ])
    assert data["trace"]["enabled"] is True            # bool, not the string "true"
    assert data["nlu"]["confidence_threshold"] == 0.5  # float
    assert data["trace"]["max_stages"] == 200          # int
    assert data["system"]["name"] is None              # null


def test_bare_string_when_not_json():
    data = {}
    apply_dotted_overrides(data, ["trace.traces_dir=eval/traces"])
    assert data["trace"]["traces_dir"] == "eval/traces"  # a path stays a string


def test_creates_nested_sections_and_overrides_existing():
    data = {"trace": {"enabled": False, "capture_level": "utterance"}}
    apply_dotted_overrides(data, ["trace.enabled=true", "nlu.providers.keyword.enabled=true"])
    assert data["trace"]["enabled"] is True                       # overrode the existing value
    assert data["trace"]["capture_level"] == "utterance"          # untouched sibling
    assert data["nlu"]["providers"]["keyword"]["enabled"] is True  # created the whole path


def test_empty_overrides_noop():
    data = {"a": 1}
    assert apply_dotted_overrides(data, None) == {"a": 1}
    assert apply_dotted_overrides(data, []) == {"a": 1}


@pytest.mark.parametrize("bad", ["nokey", "=value", "  =x"])
def test_malformed_raises(bad):
    with pytest.raises(ValueError, match="KEY=VALUE"):
        apply_dotted_overrides({}, [bad])


def test_section_collision_raises():
    # `trace` is a scalar here, so descending into `trace.enabled` is invalid.
    with pytest.raises(ValueError, match="not a config section"):
        apply_dotted_overrides({"trace": 5}, ["trace.enabled=true"])
