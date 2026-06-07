"""ARCH-15 PR-2 — OutputManager: D-2 modality routing + §3.1 negotiation + bus emission.

Exercised with fake OutputPorts (PR-2 is adapter-free; real adapters land in PR-3+).
"""

from typing import Set

import pytest

from irene.core.event_bus import EventBus, EventType
from irene.core.interfaces.output import DeliveryResult, OutputModality, OutputPort
from irene.intents.context_models import RequestContext
from irene.intents.models import IntentResult
from irene.outputs.manager import OutputManager

T, S, D, E = (OutputModality.TEXT, OutputModality.SPEECH,
              OutputModality.DEVICE_COMMAND, OutputModality.EVENT)


class FakeOutput(OutputPort):
    """A recording fake — captures every deliver() call."""

    def __init__(self, name: str, modalities: Set[OutputModality], origin: str | None = None,
                 echo=None):
        self._name = name
        self._modalities = modalities
        self._origin = origin
        self._echo = echo
        self.calls = []  # list[(modality, text)]

    def supported_modalities(self) -> Set[OutputModality]:
        return self._modalities

    async def deliver(self, result, context, modality) -> DeliveryResult:
        self.calls.append((modality, result.text))
        return DeliveryResult.ok(self._name, modality, echoed_value=self._echo)

    def get_output_type(self) -> str:
        return self._name

    def origin_key(self):
        return self._origin


def _result(text="hi"):
    return IntentResult(text=text)


def _ctx(source="cli"):
    return RequestContext(source=source)


async def _mgr(*outs):
    m = OutputManager()
    for o in outs:
        await m.add_output(o.get_output_type(), o)
    return m


async def test_conversational_is_origin_paired():
    cli = FakeOutput("cli", {T}, origin="cli")
    ws = FakeOutput("ws", {T}, origin="ws")
    m = await _mgr(cli, ws)

    res = await m.deliver(_result(), _ctx(source="cli"), T)

    assert len(res) == 1 and res[0].delivered and res[0].output_name == "cli"
    assert cli.calls == [(T, "hi")] and ws.calls == []


async def test_no_origin_match_delivers_nothing():
    ws = FakeOutput("ws", {T}, origin="ws")
    m = await _mgr(ws)
    res = await m.deliver(_result(), _ctx(source="cli"), T)
    assert res == [] and ws.calls == []


async def test_actuation_is_capability_routed_to_designated_single():
    bridge = FakeOutput("bridge", {D}, echo="on")
    other = FakeOutput("bridge2", {D})
    m = await _mgr(bridge, other)
    m.designate(D, "bridge")

    res = await m.deliver(_result("включи свет"), _ctx(source="cli"), D)

    # exactly one delivery (no double-actuation), to the designated bridge, with rich echo
    assert len(res) == 1 and res[0].output_name == "bridge"
    assert res[0].echoed_value == "on"
    assert bridge.calls == [(D, "включи свет")] and other.calls == []


async def test_broadcast_hits_all_capable_outputs():
    a = FakeOutput("a", {T}, origin="cli")
    b = FakeOutput("b", {T}, origin="ws")
    c = FakeOutput("c", {D})  # not text-capable → excluded
    m = await _mgr(a, b, c)

    res = await m.deliver(_result(), _ctx(source="cli"), T, broadcast=True)

    delivered = {r.output_name for r in res if r.delivered}
    assert delivered == {"a", "b"} and c.calls == []


async def test_speech_degrades_to_text():
    # origin output only supports TEXT; SPEECH degrades to TEXT (§3.1).
    cli = FakeOutput("cli", {T}, origin="cli")
    m = await _mgr(cli)

    res = await m.deliver(_result(), _ctx(source="cli"), S)

    assert len(res) == 1 and res[0].delivered
    assert res[0].modality is T and res[0].degraded_from is S
    assert cli.calls == [(T, "hi")]


async def test_undeliverable_modality_is_dropped():
    cli = FakeOutput("cli", {T}, origin="cli")
    m = await _mgr(cli)
    # EVENT is designated nowhere and not conversational → no target selected.
    res = await m.deliver(_result(), _ctx(source="cli"), E)
    assert res == []


async def test_delivery_emits_output_delivered_event():
    bus = EventBus()
    events = []

    async def _obs(e):
        events.append(e)

    bus.subscribe(_obs)
    cli = FakeOutput("cli", {T}, origin="cli")
    m = OutputManager(event_bus=bus)
    await m.add_output("cli", cli)

    await m.deliver(_result(), _ctx(source="cli"), T)

    assert len(events) == 1
    assert events[0].type is EventType.OUTPUT_DELIVERED
    assert events[0].payload["output"] == "cli" and events[0].payload["delivered"] is True


async def test_lifecycle_start_stop():
    cli = FakeOutput("cli", {T}, origin="cli")
    m = await _mgr(cli)
    await m.start()
    assert "cli" in m._active
    await m.stop()
    assert m._active == []
