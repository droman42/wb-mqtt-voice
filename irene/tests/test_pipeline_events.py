"""ARCH-15 PR-6a — the WorkflowManager publishes canonical pipeline events onto the shared bus.

`process_text_input`/`process_audio_input` emit `input.received` + `result.produced` carrying the
origin identity, so the observation tap (PR-6b) and metrics can subscribe. No-op without a bus.
"""

import pytest

from irene.core.event_bus import EventBus, EventType
from irene.core.workflow_manager import WorkflowManager
from irene.intents.models import IntentResult


class _FakeWorkflow:
    async def process_text_input(self, text, context, trace_context=None):
        return IntentResult(text=f"re:{text}", metadata={"intent_name": "greetings.hello"})


def _collect(sink):
    async def _h(ev):
        sink.append(ev)
    return _h


def _wm(event_bus):
    wm = WorkflowManager(component_manager=None, config=None, event_bus=event_bus)
    wm.active_workflow = _FakeWorkflow()
    return wm


async def test_publishes_input_received_and_result_produced():
    bus = EventBus()
    events = []
    bus.subscribe(_collect(events))

    wm = _wm(bus)
    result = await wm.process_text_input("привет", session_id="s1", client_context={"source": "cli"})

    assert result.text == "re:привет"
    types = [e.type for e in events]
    assert types == [EventType.INPUT_RECEIVED, EventType.RESULT_PRODUCED]


async def test_events_carry_identity_and_payload():
    bus = EventBus()
    events = []
    bus.subscribe(_collect(events))

    wm = _wm(bus)
    await wm.process_text_input("привет", session_id="s1", client_context={"source": "cli"})

    received = next(e for e in events if e.type is EventType.INPUT_RECEIVED)
    produced = next(e for e in events if e.type is EventType.RESULT_PRODUCED)
    assert received.source == "cli" and received.session_id == "s1"
    assert received.payload == {"text": "привет", "format": "text"}
    assert produced.payload["text"] == "re:привет"
    assert produced.payload["intent"] == "greetings.hello"
    assert produced.payload["success"] is True


async def test_no_bus_is_noop():
    wm = _wm(None)  # no event bus wired
    result = await wm.process_text_input("привет", session_id="s1", client_context={"source": "cli"})
    assert result.text == "re:привет"  # must not raise
