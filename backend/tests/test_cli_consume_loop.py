"""ARCH-15 PR-5b — the interactive runner consumes the single CLI source (no own reader).

`_run_interactive_loop` now drains `CLIInput.listen()` and routes each line through the workflow,
rendering results via the shared OutputManager — instead of running its own prompt_toolkit reader.
This proves: lines are processed in order, delivered to the origin-paired console output, and the
loop stops on `quit` (transport-local) without processing anything after it.
"""

import logging
from types import SimpleNamespace

import pytest

from locveil_voice.intents.models import IntentResult
from locveil_voice.outputs.console import ConsoleOutput
from locveil_voice.outputs.manager import OutputManager
from locveil_voice.runners.base import InteractiveRunnerMixin


class _FakeSource:
    def __init__(self, items):
        self._items = items

    async def listen(self):
        for item in self._items:
            yield item


class _FakeWorkflowManager:
    def __init__(self):
        self.seen = []

    async def process_text_input(self, text, session_id=None, wants_audio=False,
                                 client_context=None, trace_context=None):
        self.seen.append((text, client_context))
        return IntentResult(text=f"echo:{text}")


class _FakeCore:
    def __init__(self, source, wm):
        self.input_manager = SimpleNamespace(_sources={"cli": source})
        self.workflow_manager = wm
        self.is_running = True


class _Holder(InteractiveRunnerMixin):
    def __init__(self, core, output_manager):
        self.core = core
        self.runner_config = SimpleNamespace(name="CLI")
        self._logger = logging.getLogger("test")
        self._output_manager = output_manager


async def _console_om(sink):
    om = OutputManager()
    await om.add_output("console", ConsoleOutput(sink=sink, origin="cli"))
    return om


async def test_consume_loop_processes_then_quits():
    captured = []
    om = await _console_om(captured.append)
    source = _FakeSource(["привет", "quit", "should-not-run"])
    wm = _FakeWorkflowManager()
    holder = _Holder(_FakeCore(source, wm), om)

    rc = await holder._run_interactive_loop(SimpleNamespace(quiet=True, enable_tts=False))

    assert rc == 0
    # "привет" processed (channel=cli) and delivered to the console; "quit" stops the loop before
    # "should-not-run" is ever seen.
    assert wm.seen == [("привет", {"source": "cli"})]
    assert captured == ["📝 echo:привет"]


async def test_consume_loop_skips_blank_lines():
    captured = []
    om = await _console_om(captured.append)
    source = _FakeSource(["", "  ", "время", "exit"])
    wm = _FakeWorkflowManager()
    holder = _Holder(_FakeCore(source, wm), om)

    rc = await holder._run_interactive_loop(SimpleNamespace(quiet=True, enable_tts=False))

    assert rc == 0
    assert [t for t, _ in wm.seen] == ["время"]
    assert captured == ["📝 echo:время"]


async def test_missing_cli_source_returns_error():
    holder = _Holder(SimpleNamespace(input_manager=SimpleNamespace(_sources={})), None)
    rc = await holder._run_interactive_loop(SimpleNamespace(quiet=True, enable_tts=False))
    assert rc == 1
