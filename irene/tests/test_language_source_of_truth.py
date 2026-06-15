"""
QUAL-36 — single language source-of-truth, offline/deterministic guards.

Proves the installation-agnostic contract: the canonical config default seeds the session, detection
clamps to the supported set → default, the session carries the supported list, machine-context labels
localize by the session language, and an unspecified request never stomps the seed. Language literals
here are allowed (tests).
"""
import asyncio
from pathlib import Path

import pytest

from irene.intents.context import ContextManager
from irene.intents.context_models import UnifiedConversationContext
from irene.core.intent_asset_loader import IntentAssetLoader, AssetLoaderConfig
from irene.intents.handlers.conversation import ConversationIntentHandler


def _run(coro):
    return asyncio.run(coro)


def test_session_seeds_from_canonical_default_english():
    """An English-primary instance seeds new sessions with English — not a hardcoded 'ru'."""
    cm = ContextManager(default_language="en", supported_languages=["en", "ru"])
    ctx = _run(cm.get_or_create_context("s-en"))
    assert ctx.language == "en"
    assert ctx.supported_languages == ["en", "ru"]


def test_session_seeds_arbitrary_default():
    """Source-of-truth is config, not a baked pair: a de-primary instance seeds 'de'."""
    cm = ContextManager(default_language="de", supported_languages=["de", "en"])
    ctx = _run(cm.get_or_create_context("s-de"))
    assert ctx.language == "de"


def test_request_unspecified_does_not_override_seed():
    """QUAL-36: RequestContext with no explicit language must not stomp the session's seeded value."""
    from irene.workflows.base import RequestContext
    rc = RequestContext()
    assert rc.language is None  # "unspecified", resolved downstream to the session language
    assert RequestContext(language="en").language == "en"


def test_context_labels_localize_by_session_language():
    """Machine-context labels for the LLM follow the session language (T7, folded from QUAL-16)."""
    loader = IntentAssetLoader(Path("assets"), AssetLoaderConfig(validate_method_existence=False))
    _run(loader.load_all_assets(["conversation"]))

    handler = ConversationIntentHandler()
    handler.asset_loader = loader
    handler._asset_loader_initialized = True

    en = handler._context_label("session", "en", room="kitchen", device_count=2)
    ru = handler._context_label("session", "ru", room="kitchen", device_count=2)
    assert en == "Session: kitchen (2 devices)"
    assert ru.startswith("Сессия:")
    assert en != ru


def test_context_label_offline_fallback_when_no_asset():
    """Missing localization degrades to a minimal English label, never a crash (offline-first)."""
    handler = ConversationIntentHandler()  # no asset loader attached
    assert handler._context_label("actions", "en", active_count=1, recent_count=0) == "Actions: 1 active, 0 recent"


def test_unified_context_structural_default_is_valid():
    """The structural dataclass default remains a concrete, valid language (no None on the hot path)."""
    assert UnifiedConversationContext(session_id="x").language == "ru"
