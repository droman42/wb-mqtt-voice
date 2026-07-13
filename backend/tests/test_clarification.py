"""QUAL-30 Grade-1 clarification boundary — focused tests.

A missing required parameter (raised by `IntentHandler.get_param`) must surface as a single-turn,
localized **explain-and-ask** at the handler-execute boundary — not a silent wrong-action and not a
generic error. (Per-handler activation rides QUAL-34; LLM phrasing rides QUAL-15; device/room
clarification rides ARCH-6 — out of scope here.)
"""
from pathlib import Path

import pytest

from locveil_voice.core.intent_asset_loader import IntentAssetLoader, AssetLoaderConfig
from locveil_voice.core.donations import (
    HandlerDonation, MethodDonation, ParameterSpec, ParameterType, MissingRequiredParameter,
)
from locveil_voice.intents.handlers.base import IntentHandler
from locveil_voice.intents.models import Intent
from locveil_voice.intents.context_models import UnifiedConversationContext


class _ClarifyHandler(IntentHandler):
    async def execute(self, intent, context):  # pragma: no cover - routed via donation
        ...

    async def can_handle(self, intent):  # pragma: no cover
        return True

    @classmethod
    def get_python_dependencies(cls):
        return []

    @classmethod
    def get_platform_dependencies(cls):
        return {"linux.ubuntu": []}

    @classmethod
    def get_platform_support(cls):
        return ["linux.ubuntu"]

    async def _handle_set(self, intent, context):
        # required param, NO caller default → get_param raises MissingRequiredParameter
        self.get_param(intent, "duration")
        return self._create_error_result("unreached", "x")


def _handler(loader) -> _ClarifyHandler:
    h = _ClarifyHandler()
    h.set_asset_loader(loader)
    h.set_donation(HandlerDonation(
        schema_version="1.1", handler_domain="demo", description="demo",
        method_donations=[MethodDonation(
            method_name="_handle_set", intent_suffix="set", description="demo", phrases=["x"],
            parameters=[ParameterSpec(name="duration", type=ParameterType.INTEGER, required=True,
                                      description="Продолжительность таймера")])]))
    return h


async def _loader() -> IntentAssetLoader:
    loader = IntentAssetLoader(Path("assets"), AssetLoaderConfig())
    await loader.load_all_assets(["timer"])
    return loader


def test_get_param_raises_structured_missing_required():
    """The typed accessor raises a structured exception carrying the param + description."""
    import asyncio
    # asyncio.run, not get_event_loop(): the latter raises "no current event loop" once another
    # async test has closed the thread's loop (order-dependent — passed alone, failed in-suite).
    loader = asyncio.run(_loader())
    h = _handler(loader)
    intent = Intent(name="demo.set", entities={}, confidence=0.9, raw_text="x")
    with pytest.raises(MissingRequiredParameter) as ei:
        h.get_param(intent, "duration")
    assert ei.value.param_name == "duration"
    assert "Продолжительность" in ei.value.description


async def test_missing_required_becomes_localized_clarification():
    loader = await _loader()
    # the system clarification template set is loaded even though it's not an enabled handler
    assert loader.get_template("clarification", "missing_parameter", "ru") is not None

    h = _handler(loader)
    ctx = UnifiedConversationContext(session_id="t")
    ctx.language = "ru"
    res = await h.execute_with_donation_routing(
        Intent(name="demo.set", entities={}, confidence=0.9, raw_text="поставь таймер"), ctx)

    # explain-and-ask: a successful conversational turn, flagged, localized, speaks
    assert res.success is True
    assert res.should_speak is True
    assert res.metadata.get("clarification") is True
    assert res.metadata.get("parameter") == "duration"
    assert "подскажите" in res.text          # rendered from the RU template, not the generic error
    assert "error processing your request" not in res.text


async def test_clarification_localizes_by_context_language():
    loader = await _loader()
    h = _handler(loader)
    ctx = UnifiedConversationContext(session_id="t")
    ctx.language = "en"
    res = await h.execute_with_donation_routing(
        Intent(name="demo.set", entities={}, confidence=0.9, raw_text="set a timer"), ctx)
    assert res.metadata.get("clarification") is True
    assert "one more detail" in res.text     # EN template frame
