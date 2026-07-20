"""QUAL-86 — the NLU cascade trace records per-provider attempts (the QUAL-53 prerequisite).

The `nlu_cascade` stage used to record only the FINAL result, so a recorded trace could not
explain WHY an utterance fell through to the LLM tier. Now every attempt carries which
provider tried, its outcome (recognized / low_confidence / no_intent / unavailable / error),
the confidence vs the threshold it was judged by, and — for low-confidence abstentions —
the intent it would have guessed. The records travel on the transport key
``entities["_cascade_trace"]`` and are popped into the trace stage by
``process`` (stripped on the untraced fast path).
"""

from types import SimpleNamespace
from typing import Dict, Optional

import pytest

from locveil_voice.components.nlu_component import NLUComponent
from locveil_voice.intents.context_models import UnifiedConversationContext
from locveil_voice.intents.models import Intent


class FakeNLUProvider:
    def __init__(self, name: str, confidence: float = 0.8, should_fail: bool = False,
                 returns_none: bool = False, intent_name: str = "test.intent"):
        self.name = name
        self.confidence = confidence
        self.should_fail = should_fail
        self.returns_none = returns_none
        self.intent_name = intent_name

    async def recognize_with_parameters(self, text: str,
                                        context: UnifiedConversationContext) -> Optional[Intent]:
        if self.should_fail:
            raise RuntimeError(f"provider {self.name} exploded")
        if self.returns_none:
            return None
        return Intent(name=self.intent_name, entities={}, confidence=self.confidence,
                      raw_text=text)


PROVIDER_THRESHOLDS = {
    "fast_provider": {"confidence_threshold": 0.8},
    "slow_provider": {"confidence_threshold": 0.6},
}


def make_component(providers: Dict[str, FakeNLUProvider], cascade_order=None) -> NLUComponent:
    comp = object.__new__(NLUComponent)
    comp.providers = providers
    comp.confidence_threshold = 0.7
    comp.fallback_intent = "conversation.general"
    comp.provider_cascade_order = cascade_order or list(providers.keys())
    comp.max_cascade_attempts = 4
    comp.cascade_timeout_ms = 200
    comp.cache_recognition_results = False
    comp.cache_ttl_seconds = 300
    comp._recognition_cache = {}
    comp.default_provider = None
    comp.core = SimpleNamespace(
        config=SimpleNamespace(nlu=SimpleNamespace(providers=PROVIDER_THRESHOLDS)))
    return comp


def _ctx() -> UnifiedConversationContext:
    return UnifiedConversationContext(session_id="trace-test", language="ru")


@pytest.mark.asyncio
async def test_low_confidence_attempt_records_what_it_would_have_guessed():
    comp = make_component({
        "fast_provider": FakeNLUProvider("fast", confidence=0.5,
                                         intent_name="smart_home.power_on"),
        "slow_provider": FakeNLUProvider("slow", confidence=0.9,
                                         intent_name="timer.set"),
    })
    result = await comp.recognize("включи свет", _ctx())

    trace = result.entities["_cascade_trace"]
    assert [a["provider"] for a in trace] == ["fast_provider", "slow_provider"]

    first, second = trace
    assert first["outcome"] == "low_confidence"
    assert first["confidence"] == 0.5 and first["threshold"] == 0.8
    assert first["intent_name"] == "smart_home.power_on"  # the QUAL-53 gold: what it WOULD have said
    assert "duration_ms" in first

    assert second["outcome"] == "recognized"
    assert second["confidence"] == 0.9 and second["threshold"] == 0.6
    assert result.entities["_recognition_provider"] == "slow_provider"


@pytest.mark.asyncio
async def test_fall_through_records_the_whole_story_on_the_fallback_intent():
    comp = make_component({
        "fast_provider": FakeNLUProvider("fast", returns_none=True),
        "slow_provider": FakeNLUProvider("slow", should_fail=True),
    })
    result = await comp.recognize("непонятное", _ctx())

    assert result.entities["_recognition_provider"] == "fallback"
    trace = result.entities["_cascade_trace"]
    assert [a["outcome"] for a in trace] == ["no_intent", "error"]
    assert "exploded" in trace[1]["error"]
    assert all("duration_ms" in a for a in trace)


@pytest.mark.asyncio
async def test_unavailable_provider_is_recorded_not_skipped_silently():
    comp = make_component(
        {"slow_provider": FakeNLUProvider("slow", confidence=0.9)},
        cascade_order=["ghost_provider", "slow_provider"])
    result = await comp.recognize("текст", _ctx())

    trace = result.entities["_cascade_trace"]
    assert trace[0] == {"provider": "ghost_provider", "outcome": "unavailable",
                        "duration_ms": trace[0]["duration_ms"]}
    assert trace[1]["outcome"] == "recognized"


@pytest.mark.asyncio
async def test_traced_run_moves_records_into_the_stage_and_out_of_entities():
    comp = make_component({"fast_provider": FakeNLUProvider("fast", confidence=0.9)})
    # process → recognize_with_context → context_processor; wire the minimal
    # context processor straight through to the cascade
    comp.context_processor = SimpleNamespace(
        process_with_context=lambda text, context: comp.recognize(text, context))

    recorded = {}

    class _Trace:
        enabled = True

        def record_stage(self, stage_name, input_data, output_data, metadata,
                         processing_time_ms):
            recorded.update(stage=stage_name, metadata=metadata, output=output_data)

    result = await comp.process("включи свет", _ctx(), _Trace())

    assert recorded["stage"] == "nlu_cascade"
    attempts = recorded["metadata"]["cascade_attempts"]
    assert attempts and attempts[0]["provider"] == "fast_provider"
    assert attempts[0]["outcome"] == "recognized"
    assert recorded["metadata"]["final_provider"] == "fast_provider"
    # popped out of entities — the stage is the records' home
    assert "_cascade_trace" not in result.entities
    assert "_cascade_trace" not in recorded["output"]["entities"]


@pytest.mark.asyncio
async def test_untraced_fast_path_strips_the_transport_key():
    comp = make_component({"fast_provider": FakeNLUProvider("fast", confidence=0.9)})
    comp.context_processor = SimpleNamespace(
        process_with_context=lambda text, context: comp.recognize(text, context))

    result = await comp.process("включи свет", _ctx(), None)
    assert "_cascade_trace" not in result.entities
    assert result.entities["_recognition_provider"] == "fast_provider"
