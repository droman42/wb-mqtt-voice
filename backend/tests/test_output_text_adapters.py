"""ARCH-15 PR-3 — real text output adapters + origin-routed delivery through the OutputManager."""

import pytest

from locveil_voice.core.interfaces.output import OutputModality
from locveil_voice.intents.context_models import RequestContext
from locveil_voice.intents.models import IntentResult
from locveil_voice.outputs.console import ConsoleOutput
from locveil_voice.outputs.text import CallbackTextOutput
from locveil_voice.outputs.manager import OutputManager

T = OutputModality.TEXT


async def test_console_output_renders_to_sink():
    captured = []
    out = ConsoleOutput(sink=captured.append, origin="cli", prefix="📝 ")
    dr = await out.deliver(IntentResult(text="привет"), RequestContext(source="cli"), T)
    assert dr.delivered and dr.output_name == "console"
    assert captured == ["📝 привет"]
    assert out.origin_key() == "cli"
    assert out.supported_modalities() == {T}


async def test_callback_text_output_invokes_send():
    sent = []

    async def _send(text):
        sent.append(text)

    out = CallbackTextOutput(_send, name="ws_text", origin="ws")
    dr = await out.deliver(IntentResult(text="hi"), RequestContext(source="ws"), T)
    assert dr.delivered and dr.output_name == "ws_text"
    assert sent == ["hi"]
    assert out.origin_key() == "ws"


async def test_console_origin_paired_via_manager():
    """A CLI-originated result routes to the console output and nowhere else."""
    captured = []
    console = ConsoleOutput(sink=captured.append, origin="cli")

    async def _ws_send(text):  # pragma: no cover - must NOT be called
        captured.append(("WS", text))

    ws = CallbackTextOutput(_ws_send, name="ws_text", origin="ws")

    m = OutputManager()
    await m.add_output("console", console)
    await m.add_output("ws_text", ws)

    res = await m.deliver(IntentResult(text="ok"), RequestContext(source="cli"), T)

    assert len(res) == 1 and res[0].output_name == "console"
    assert captured == ["📝 ok"]  # ws never called


async def test_ws_origin_paired_via_manager():
    """Same manager, a ws-originated result routes to the ws output."""
    sent = []

    async def _send(text):
        sent.append(text)

    console_hits = []
    console = ConsoleOutput(sink=console_hits.append, origin="cli")
    ws = CallbackTextOutput(_send, name="ws_text", origin="ws")

    m = OutputManager()
    await m.add_output("console", console)
    await m.add_output("ws_text", ws)

    res = await m.deliver(IntentResult(text="ok"), RequestContext(source="ws"), T)

    assert len(res) == 1 and res[0].output_name == "ws_text"
    assert sent == ["ok"] and console_hits == []
