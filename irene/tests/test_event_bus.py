"""ARCH-15 PR-2 — the pipeline event bus (publish/subscribe, identity filters, isolation)."""

import pytest

from irene.core.event_bus import EventBus, EventType, PipelineEvent, identity_filter


def _ev(t=EventType.RESULT_PRODUCED, **kw):
    return PipelineEvent(type=t, **kw)


async def test_publish_fans_out_to_subscribers():
    bus = EventBus()
    seen_a, seen_b = [], []
    bus.subscribe(_collect(seen_a))
    bus.subscribe(_collect(seen_b))

    await bus.publish(_ev(session_id="s1"))

    assert len(seen_a) == 1 and len(seen_b) == 1
    assert seen_a[0].session_id == "s1"


async def test_identity_filter_scopes_delivery():
    bus = EventBus()
    kitchen, all_events = [], []
    bus.subscribe(_collect(kitchen), identity_filter(room_name="Кухня"))
    bus.subscribe(_collect(all_events))

    await bus.publish(_ev(room_name="Кухня"))
    await bus.publish(_ev(room_name="Спальня"))

    assert [e.room_name for e in kitchen] == ["Кухня"]
    assert len(all_events) == 2


async def test_type_filter():
    bus = EventBus()
    got = []
    bus.subscribe(_collect(got), identity_filter(types=[EventType.OUTPUT_DELIVERED]))
    await bus.publish(_ev(EventType.RESULT_PRODUCED))
    await bus.publish(_ev(EventType.OUTPUT_DELIVERED))
    assert [e.type for e in got] == [EventType.OUTPUT_DELIVERED]


async def test_subscriber_failure_is_isolated():
    bus = EventBus()
    good = []

    async def _boom(e):
        raise RuntimeError("observer crashed")

    bus.subscribe(_boom)
    bus.subscribe(_collect(good))

    # Must not raise — a bad observer never breaks the publisher or other subscribers.
    await bus.publish(_ev())
    assert len(good) == 1


async def test_unsubscribe():
    bus = EventBus()
    got = []
    unsub = bus.subscribe(_collect(got))
    await bus.publish(_ev())
    unsub()
    await bus.publish(_ev())
    assert len(got) == 1
    assert bus.subscriber_count == 0


# --- helpers (collectors must be async handlers) -------------------------------------------

def _collect(sink):
    async def _h(e):
        sink.append(e)
    return _h
