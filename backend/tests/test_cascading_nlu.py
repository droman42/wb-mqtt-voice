"""Cascading NLU provider coordination — contract tests.

Exercises ``NLUComponent.recognize`` as a port: providers are tried in
``provider_cascade_order``, each gated by its own confidence threshold; the
winner's name and attempt count land in ``entities["_recognition_provider"]`` /
``entities["_cascade_attempts"]``; when everything misses, a fallback intent is
returned. The component is built with ``object.__new__`` so no heavy
initialization (donations, real providers, config models) runs.
"""

from types import SimpleNamespace
from typing import Dict, Optional

import pytest

from locveil_voice.intents.models import Intent
from locveil_voice.intents.context_models import UnifiedConversationContext
from locveil_voice.components.nlu_component import NLUComponent


class FakeNLUProvider:
    """Minimal NLU provider stub.

    ``recognize`` only calls ``recognize_with_parameters`` and reads
    ``intent.confidence`` — so that is the entire surface we need to fake.
    """

    def __init__(self, name: str, confidence: float = 0.8, should_fail: bool = False):
        self.name = name
        self.confidence = confidence
        self.should_fail = should_fail
        self.call_count = 0

    async def recognize_with_parameters(self, text: str, context: UnifiedConversationContext) -> Intent:
        self.call_count += 1
        if self.should_fail:
            raise RuntimeError(f"provider {self.name} failed")
        return Intent(
            name="test.intent",
            entities={"provider": self.name, "call_count": self.call_count},
            confidence=self.confidence,
            raw_text=text,
        )


# Per-provider confidence thresholds, mirroring a real NLU config block.
PROVIDER_THRESHOLDS = {
    "fast_provider": {"confidence_threshold": 0.8},
    "medium_provider": {"confidence_threshold": 0.7},
    "slow_provider": {"confidence_threshold": 0.6},
}


def make_component(
    providers: Dict[str, FakeNLUProvider],
    *,
    cascade_order=None,
    global_threshold: float = 0.7,
    max_attempts: int = 4,
    cache: bool = False,
    fallback: str = "conversation.general",
) -> NLUComponent:
    """Build an NLUComponent wired only with what ``recognize`` touches."""
    comp = object.__new__(NLUComponent)
    comp.providers = providers
    comp.confidence_threshold = global_threshold
    comp.fallback_intent = fallback
    comp.provider_cascade_order = cascade_order or list(providers.keys())
    comp.max_cascade_attempts = max_attempts
    comp.cascade_timeout_ms = 200
    comp.cache_recognition_results = cache
    comp.cache_ttl_seconds = 300
    comp._recognition_cache = {}
    comp.default_provider = None
    # _get_provider_confidence_threshold reads self.core.config.nlu.providers
    comp.core = SimpleNamespace(
        config=SimpleNamespace(nlu=SimpleNamespace(providers=PROVIDER_THRESHOLDS))
    )
    return comp


@pytest.fixture
def providers() -> Dict[str, FakeNLUProvider]:
    return {
        "fast_provider": FakeNLUProvider("fast", confidence=0.9),
        "medium_provider": FakeNLUProvider("medium", confidence=0.8),
        "slow_provider": FakeNLUProvider("slow", confidence=0.7),
    }


@pytest.fixture
def sample_context() -> UnifiedConversationContext:
    return UnifiedConversationContext(
        session_id="test_session",
        user_id="test_user",
        client_id="test_client",
        language="ru",
    )


@pytest.mark.asyncio
async def test_successful_first_provider(providers, sample_context):
    """First provider clears its threshold → no cascading."""
    comp = make_component(providers)

    result = await comp.recognize("test input", sample_context)

    assert result.entities["_recognition_provider"] == "fast_provider"
    assert result.entities["_cascade_attempts"] == 1
    assert result.entities["provider"] == "fast"

    assert providers["fast_provider"].call_count == 1
    assert providers["medium_provider"].call_count == 0
    assert providers["slow_provider"].call_count == 0


@pytest.mark.asyncio
async def test_cascade_to_second_provider(providers, sample_context):
    """Below-threshold first provider cascades to the second."""
    providers["fast_provider"].confidence = 0.5  # below fast's 0.8 threshold
    comp = make_component(providers)

    result = await comp.recognize("test input", sample_context)

    assert result.entities["_recognition_provider"] == "medium_provider"
    assert result.entities["_cascade_attempts"] == 2
    assert result.entities["provider"] == "medium"

    assert providers["fast_provider"].call_count == 1
    assert providers["medium_provider"].call_count == 1
    assert providers["slow_provider"].call_count == 0


@pytest.mark.asyncio
async def test_cascade_through_all_providers(providers, sample_context):
    """First two miss their thresholds, the last one wins at attempt 3."""
    providers["fast_provider"].confidence = 0.5    # below 0.8
    providers["medium_provider"].confidence = 0.4  # below 0.7
    providers["slow_provider"].confidence = 0.7    # >= 0.6 → wins
    comp = make_component(providers)

    result = await comp.recognize("test input", sample_context)

    assert result.entities["_recognition_provider"] == "slow_provider"
    assert result.entities["_cascade_attempts"] == 3
    assert result.entities["provider"] == "slow"

    assert providers["fast_provider"].call_count == 1
    assert providers["medium_provider"].call_count == 1
    assert providers["slow_provider"].call_count == 1


@pytest.mark.asyncio
async def test_fallback_when_all_providers_miss(providers, sample_context):
    """No provider clears its threshold → honest no-match fallback intent."""
    for provider in providers.values():
        provider.confidence = 0.2
    comp = make_component(providers)

    result = await comp.recognize("test input", sample_context)

    assert result.name == "conversation.general"
    assert result.entities["_recognition_provider"] == "fallback"
    # Three providers in the cascade order → three attempts before giving up.
    assert result.entities["_cascade_attempts"] == 3
    # QUAL-30: fallback is an honest no-match, not a confident recognition.
    assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_provider_specific_thresholds(providers, sample_context):
    """Each provider is gated by its own threshold, not just the global one."""
    # 0.75 is below fast's 0.8 but above medium's 0.7.
    providers["fast_provider"].confidence = 0.75
    providers["medium_provider"].confidence = 0.75
    comp = make_component(providers)

    result = await comp.recognize("test input", sample_context)

    assert result.entities["_recognition_provider"] == "medium_provider"
    assert result.entities["_cascade_attempts"] == 2


@pytest.mark.asyncio
async def test_provider_exception_is_treated_as_miss(providers, sample_context):
    """A raising provider is swallowed and the cascade continues."""
    providers["fast_provider"].should_fail = True
    comp = make_component(providers)

    result = await comp.recognize("test input", sample_context)

    assert result.entities["_recognition_provider"] == "medium_provider"
    assert result.entities["_cascade_attempts"] == 2

    assert providers["fast_provider"].call_count == 1
    assert providers["medium_provider"].call_count == 1


@pytest.mark.asyncio
async def test_max_cascade_attempts_limit(providers, sample_context):
    """Cascading stops once max_cascade_attempts is reached."""
    for provider in providers.values():
        provider.confidence = 0.2
    comp = make_component(providers, max_attempts=2)

    result = await comp.recognize("test input", sample_context)

    assert result.entities["_cascade_attempts"] == 2
    assert providers["fast_provider"].call_count == 1
    assert providers["medium_provider"].call_count == 1
    assert providers["slow_provider"].call_count == 0  # never reached


@pytest.mark.asyncio
async def test_recognition_caching(providers, sample_context):
    """A repeat utterance is served from cache without re-hitting providers."""
    comp = make_component(providers, cache=True)

    result1 = await comp.recognize("test input", sample_context)
    result2 = await comp.recognize("test input", sample_context)

    assert result1.entities["provider"] == result2.entities["provider"] == "fast"
    assert providers["fast_provider"].call_count == 1  # second call cached


@pytest.mark.asyncio
async def test_unavailable_provider_is_skipped(providers, sample_context):
    """A provider missing from the registry is skipped but still counts as an attempt."""
    del providers["medium_provider"]
    providers["fast_provider"].confidence = 0.5  # below 0.8 → miss
    comp = make_component(
        providers,
        cascade_order=["fast_provider", "medium_provider", "slow_provider"],
    )

    result = await comp.recognize("test input", sample_context)

    # fast missed, medium skipped, slow won — three cascade positions consumed.
    assert result.entities["_recognition_provider"] == "slow_provider"
    assert result.entities["provider"] == "slow"
    assert result.entities["_cascade_attempts"] == 3


@pytest.mark.asyncio
async def test_no_providers_raises(sample_context):
    """Recognition with an empty provider registry fails loud (no silent fallback)."""
    comp = make_component({})

    with pytest.raises(RuntimeError):
        await comp.recognize("test input", sample_context)
