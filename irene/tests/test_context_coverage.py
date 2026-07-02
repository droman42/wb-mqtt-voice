"""Characterization tests for ``irene.intents.context.ContextManager`` (TEST-7 Phase D).

Focus: the session-layer contract that is pure-ish and does NOT require a booted core,
real models, or the background cleanup task —

  * ``get_or_create_context`` — the canonical session creator (language/supported-set
    seeding from the injected CoreConfig defaults, idempotency, metrics start).
  * ``get_context`` — the non-creating accessor and its eviction side effect.
  * ``get_context_with_request_info`` — room/device/language/source injection from a
    ``RequestContext`` and the no-request / no-overwrite paths.
  * ``_effective_last_active`` / ``_cleanup_expired_sessions`` — eviction by the max of
    both activity clocks.

The manager is constructed directly (it is cheap), and its global ``metrics_collector``
singleton reference is replaced with an instance-level recorder so the tests stay
hermetic (no mutation of the process-wide metrics singleton) and order-independent.
"""

import asyncio
import time

from irene.intents.context import ContextManager
from irene.intents.context_models import RequestContext, UnifiedConversationContext


class _MetricsStub:
    """Records the session lifecycle calls ContextManager makes, nothing more."""

    def __init__(self):
        self.started = []
        self.ended = []

    def record_session_start(self, session_id):
        self.started.append(session_id)

    def record_session_end(self, session_id):
        self.ended.append(session_id)


def _make_manager(**kwargs):
    """A ContextManager with the metrics singleton swapped for a local recorder.

    Replacing the *instance* attribute leaves the real global singleton untouched, so
    these tests never pollute cross-test global state.
    """
    cm = ContextManager(**kwargs)
    cm.metrics_collector = _MetricsStub()
    return cm


# --------------------------------------------------------------------------- #
# get_or_create_context: creation, seeding, idempotency, metrics
# --------------------------------------------------------------------------- #

def test_get_or_create_seeds_default_language_and_supported_set():
    cm = _make_manager(default_language="en", supported_languages=["en", "de"],
                       max_history_turns=7)

    ctx = asyncio.run(cm.get_or_create_context("kitchen"))

    assert isinstance(ctx, UnifiedConversationContext)
    assert ctx.session_id == "kitchen"
    # canonical default + supported set seeded from the injected config (QUAL-36)
    assert ctx.language == "en"
    assert ctx.supported_languages == ["en", "de"]
    assert ctx.max_history_turns == 7
    # stored, and a session-start metric emitted exactly once
    assert cm.sessions["kitchen"] is ctx
    assert cm.metrics_collector.started == ["kitchen"]


def test_supported_languages_defaults_to_default_language_when_omitted():
    cm = _make_manager(default_language="ru")
    # constructor invariant: supported set falls back to [default_language]
    assert cm.supported_languages == ["ru"]
    ctx = asyncio.run(cm.get_or_create_context("s1"))
    assert ctx.supported_languages == ["ru"]


def test_get_or_create_is_idempotent():
    cm = _make_manager()

    first = asyncio.run(cm.get_or_create_context("room"))
    second = asyncio.run(cm.get_or_create_context("room"))

    assert first is second
    # only one session minted -> only one start metric
    assert cm.metrics_collector.started == ["room"]
    assert len(cm.sessions) == 1


def test_seeded_supported_languages_is_a_copy_not_a_shared_reference():
    cm = _make_manager(default_language="ru", supported_languages=["ru", "en"])
    ctx = asyncio.run(cm.get_or_create_context("s"))
    ctx.supported_languages.append("fr")
    # mutating the session's list must not corrupt the manager's canonical list
    assert cm.supported_languages == ["ru", "en"]


# --------------------------------------------------------------------------- #
# get_context: non-creating accessor + eviction
# --------------------------------------------------------------------------- #

def test_get_context_returns_none_for_unknown_session_without_creating():
    cm = _make_manager()

    result = asyncio.run(cm.get_context("never-seen"))

    assert result is None
    # non-creating: no session spawned, no start metric
    assert cm.sessions == {}
    assert cm.metrics_collector.started == []


def test_get_context_returns_live_session():
    cm = _make_manager()
    created = asyncio.run(cm.get_or_create_context("live"))

    fetched = asyncio.run(cm.get_context("live"))

    assert fetched is created


def test_get_context_evicts_expired_session_and_records_end():
    cm = _make_manager(session_timeout=1)
    ctx = asyncio.run(cm.get_or_create_context("stale"))
    # push BOTH activity clocks well into the past so the session is unambiguously expired
    old = time.time() - 10_000
    ctx.last_activity = old
    ctx.last_updated = old

    result = asyncio.run(cm.get_context("stale"))

    assert result is None
    assert "stale" not in cm.sessions
    assert cm.metrics_collector.ended == ["stale"]


def test_get_context_keeps_session_alive_via_either_clock():
    cm = _make_manager(session_timeout=1)
    ctx = asyncio.run(cm.get_or_create_context("mixed"))
    # last_updated is ancient, but last_activity is fresh -> max() keeps it alive
    ctx.last_updated = time.time() - 10_000
    ctx.last_activity = time.time()

    result = asyncio.run(cm.get_context("mixed"))

    assert result is ctx
    assert cm.metrics_collector.ended == []


# --------------------------------------------------------------------------- #
# _effective_last_active: max of both clocks
# --------------------------------------------------------------------------- #

def test_effective_last_active_takes_max_of_both_clocks():
    ctx = UnifiedConversationContext(session_id="x")
    ctx.last_updated = 100.0
    ctx.last_activity = 250.0
    assert ContextManager._effective_last_active(ctx) == 250.0

    ctx.last_updated = 500.0
    ctx.last_activity = 250.0
    assert ContextManager._effective_last_active(ctx) == 500.0


def test_effective_last_active_tolerates_none_clocks():
    ctx = UnifiedConversationContext(session_id="x")
    ctx.last_updated = None
    ctx.last_activity = None
    # both None -> coerced to 0.0, no crash
    assert ContextManager._effective_last_active(ctx) == 0.0


# --------------------------------------------------------------------------- #
# get_context_with_request_info: room / device / language / source injection
# --------------------------------------------------------------------------- #

def test_request_info_injects_room_device_language_and_source():
    cm = _make_manager(default_language="ru")
    rc = RequestContext(
        source="web",
        client_id="kitchen",
        room_name="Кухня",
        language="en",
        metadata={"trace": "abc"},
        device_context={
            "available_devices": [{"name": "lamp"}],
            "device_capabilities": {"tts": True},
        },
    )

    ctx = asyncio.run(cm.get_context_with_request_info("kitchen_session", rc))

    assert ctx.client_id == "kitchen"
    assert ctx.room_name == "Кухня"
    assert ctx.available_devices == [{"name": "lamp"}]
    assert ctx.client_metadata["device_capabilities"] == {"tts": True}
    assert ctx.request_source == "web"
    # language explicitly carried and differs from seed -> overrides
    assert ctx.language == "en"
    # request metadata merged onto client_metadata
    assert ctx.client_metadata["trace"] == "abc"
    # activity timestamp freshly stamped
    assert time.time() - ctx.last_activity < 5


def test_request_info_room_name_falls_back_to_device_context():
    cm = _make_manager()
    rc = RequestContext(
        source="api",
        client_id="hall",
        device_context={"room_name": "Гостиная"},
    )

    ctx = asyncio.run(cm.get_context_with_request_info("hall_session", rc))

    assert ctx.client_id == "hall"
    assert ctx.room_name == "Гостиная"


def test_request_info_does_not_overwrite_existing_room_identity():
    cm = _make_manager()
    existing = asyncio.run(cm.get_or_create_context("sess"))
    existing.client_id = "original_client"
    existing.room_name = "OriginalRoom"

    rc = RequestContext(source="web", client_id="other_client", room_name="OtherRoom")
    ctx = asyncio.run(cm.get_context_with_request_info("sess", rc))

    assert ctx is existing
    # already-set identity is preserved (room-scoped boundary protection)
    assert ctx.client_id == "original_client"
    assert ctx.room_name == "OriginalRoom"


def test_request_info_with_none_request_context_just_returns_context():
    cm = _make_manager(default_language="ru")

    ctx = asyncio.run(cm.get_context_with_request_info("plain", None))

    assert ctx.session_id == "plain"
    assert ctx.client_id is None
    assert ctx.room_name is None
    # seeded language untouched, activity stamped
    assert ctx.language == "ru"
    assert time.time() - ctx.last_activity < 5


def test_request_info_does_not_override_language_when_unspecified():
    cm = _make_manager(default_language="ru")
    # language=None means "use the session's resolved language" (QUAL-36)
    rc = RequestContext(source="web", language=None)

    ctx = asyncio.run(cm.get_context_with_request_info("s", rc))

    assert ctx.language == "ru"


# --------------------------------------------------------------------------- #
# _cleanup_expired_sessions: bulk eviction gated by cleanup_interval
# --------------------------------------------------------------------------- #

def test_cleanup_expired_sessions_removes_only_stale_ones():
    cm = _make_manager(session_timeout=1)
    stale = asyncio.run(cm.get_or_create_context("stale"))
    fresh = asyncio.run(cm.get_or_create_context("fresh"))

    old = time.time() - 10_000
    stale.last_activity = old
    stale.last_updated = old
    fresh.last_activity = time.time()
    fresh.last_updated = time.time()

    # force the interval gate open so cleanup actually runs this call
    cm.last_cleanup = time.time() - cm.cleanup_interval - 1
    asyncio.run(cm._cleanup_expired_sessions())

    assert "stale" not in cm.sessions
    assert "fresh" in cm.sessions


def test_cleanup_expired_sessions_closes_session_metrics():
    """BUG-16: bulk eviction must close out session metrics (the sweep used to skip
    record_session_end entirely, leaking one collector entry per session forever)."""
    cm = _make_manager(session_timeout=1)
    stale = asyncio.run(cm.get_or_create_context("stale"))
    old = time.time() - 10_000
    stale.last_activity = old
    stale.last_updated = old

    cm.last_cleanup = time.time() - cm.cleanup_interval - 1
    asyncio.run(cm._cleanup_expired_sessions())

    assert cm.metrics_collector.ended == ["stale"]


def test_remove_context_closes_session_metrics():
    """BUG-16: the background loop evicts via remove_context — same close-out seam."""
    cm = _make_manager()
    asyncio.run(cm.get_or_create_context("bg"))
    asyncio.run(cm.remove_context("bg"))
    assert cm.metrics_collector.ended == ["bg"]
    assert "bg" not in cm.sessions


def test_cleanup_skips_when_interval_not_elapsed():
    cm = _make_manager(session_timeout=1)
    stale = asyncio.run(cm.get_or_create_context("stale"))
    old = time.time() - 10_000
    stale.last_activity = old
    stale.last_updated = old

    # last_cleanup just happened -> gate closed -> no removal despite expiry
    cm.last_cleanup = time.time()
    asyncio.run(cm._cleanup_expired_sessions())

    assert "stale" in cm.sessions
