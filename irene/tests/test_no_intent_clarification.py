"""QUAL-37 — targeted no-intent clarification (offline, deterministic).

When the NLU fails to recognize a command but guesses a likely domain, the offline (no-LLM) conversation
fallback offers a TARGETED explain-and-ask ("Did you want to set a timer?") instead of the generic
"didn't understand" line. Purely template-driven (offline guarantee), localized by the user's language,
and deterministic. Falls through to the generic responder when there's no guess or the domain is unknown.
"""
import asyncio
from pathlib import Path

import pytest

from irene.core.intent_asset_loader import IntentAssetLoader, AssetLoaderConfig
from irene.intents.handlers.conversation import ConversationIntentHandler
from irene.intents.context_models import UnifiedConversationContext
from irene.intents.models import Intent


def _run(coro):
    # asyncio.run creates+closes a fresh loop per call. The old get_event_loop().run_until_complete
    # raised "no current event loop" once another async test had closed the thread's loop — an
    # order-dependent failure (passed alone, failed in the full suite).
    return asyncio.run(coro)


def _handler() -> ConversationIntentHandler:
    loader = IntentAssetLoader(Path("assets"), AssetLoaderConfig(validate_method_existence=False))
    _run(loader.load_all_assets(["conversation"]))
    h = ConversationIntentHandler()
    h.asset_loader = loader
    h._asset_loader_initialized = True
    return h


def _fallback(h, language, likely_domain, text="бла бла"):
    ctx = UnifiedConversationContext(session_id="s")
    ctx.language = language
    intent = Intent(name="conversation.general",
                    entities={"_fallback_context": {"likely_domain": likely_domain}},
                    confidence=0.0, raw_text=text)
    return _run(h._handle_fallback_without_llm(intent, ctx))


def test_targeted_clarification_russian():
    r = _fallback(_handler(), "ru", "timer")
    assert r.metadata["targeted"] is True
    assert r.metadata["likely_domain"] == "timer"
    assert "поставить таймер" in r.text
    assert r.success is True


def test_targeted_clarification_english():
    r = _fallback(_handler(), "en", "audio")
    assert r.metadata["targeted"] is True
    assert "play music" in r.text


def test_generic_when_no_domain_guess():
    r = _fallback(_handler(), "ru", None)
    assert r.metadata["targeted"] is False
    assert r.metadata["likely_domain"] is None
    # the generic responder echoes the unrecognized text
    assert "бла бла" in r.text


def test_unknown_domain_falls_through_to_generic():
    r = _fallback(_handler(), "en", "totally_unknown_domain")
    assert r.metadata["targeted"] is False


def test_targeted_is_deterministic_and_offline():
    """Same input → identical targeted text (no random), and no LLM was consulted."""
    h = _handler()
    a = _fallback(h, "ru", "datetime")
    b = _fallback(h, "ru", "datetime")
    assert a.text == b.text
    assert a.metadata["llm_required"] is False
    assert "узнать время или дату" in a.text
