"""QUAL-55 — the canonical IntentResult → API projection.

The five execution surfaces (REST /execute/*, /trace/* final_result, WS /ws/audio response
frames) must all route through `serialize_intent_result` — one shape, no drift
(`docs/review/api_result_contract_review.md` F1–F4).
"""

from locveil_voice.api.serializers import serialize_intent_result
from locveil_voice.api.schemas import CommandResponse
from locveil_voice.intents.models import IntentResult

CANONICAL_KEYS = {"text", "success", "error", "confidence", "intent_name", "timestamp", "metadata"}


def make_result(**kw) -> IntentResult:
    defaults = dict(text="готово", metadata={"original_intent": "timer.set", "execution_time": 0.01},
                    confidence=0.9)
    defaults.update(kw)
    return IntentResult(**defaults)


def test_canonical_keys_exactly():
    assert set(serialize_intent_result(make_result())) == CANONICAL_KEYS


def test_intent_name_lifted_from_original_intent():
    payload = serialize_intent_result(make_result())
    assert payload["intent_name"] == "timer.set"          # F2: top-level, from the producer's key
    assert payload["metadata"]["original_intent"] == "timer.set"  # raw metadata untouched


def test_confidence_and_text_top_level():
    payload = serialize_intent_result(make_result())
    assert payload["text"] == "готово"                    # F1: canonical name
    assert payload["confidence"] == 0.9                   # F4: always top-level


def test_extra_metadata_merges_never_replaces():
    payload = serialize_intent_result(
        make_result(), extra_metadata={"filename": "a.wav", "file_size_bytes": 42})
    assert payload["metadata"]["filename"] == "a.wav"     # F3: extras ride inside metadata
    assert payload["metadata"]["original_intent"] == "timer.set"  # ...alongside, not instead


def test_empty_metadata_and_none_text_are_safe():
    payload = serialize_intent_result(IntentResult(text="", metadata={}))
    assert payload["text"] == ""
    assert payload["intent_name"] is None
    assert payload["metadata"] == {}


def test_failure_carries_error():
    payload = serialize_intent_result(IntentResult(text="", success=False, error="boom"))
    assert payload["success"] is False and payload["error"] == "boom"


def test_payload_constructs_command_response():
    """The REST surfaces build CommandResponse directly from the payload — keys must line up."""
    response = CommandResponse(**serialize_intent_result(make_result()),
                               session_id="s1", room_alias=None)
    assert response.text == "готово"
    assert response.intent_name == "timer.set"
    assert response.confidence == 0.9
