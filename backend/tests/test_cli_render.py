"""ARCH-15 PR-3 — the CLI runner renders results through the output hexagon (origin=cli)."""

from types import SimpleNamespace

import pytest

from locveil_voice.intents.models import IntentResult
from locveil_voice.outputs.console import ConsoleOutput
from locveil_voice.outputs.manager import OutputManager
from locveil_voice.runners.base import InteractiveRunnerMixin


class _Holder(InteractiveRunnerMixin):
    """Minimal carrier of the mixin for testing _render_result in isolation."""

    def __init__(self, output_manager=None):
        self.runner_config = SimpleNamespace(name="CLI")
        if output_manager is not None:
            self._output_manager = output_manager


async def _console_manager(sink):
    m = OutputManager()
    await m.add_output("console", ConsoleOutput(sink=sink, origin="cli"))
    return m


async def test_render_delivers_through_output_manager():
    captured = []
    holder = _Holder(await _console_manager(captured.append))
    await holder._render_result(IntentResult(text="hey"), SimpleNamespace(quiet=False))
    assert captured == ["📝 hey"]


async def test_render_fallback_prints_when_no_output_manager(capsys):
    holder = _Holder()  # no output manager wired
    await holder._render_result(IntentResult(text="hey"), SimpleNamespace(quiet=False))
    assert "📝 hey" in capsys.readouterr().out


async def test_render_quiet_fallback_emits_nothing(capsys):
    holder = _Holder()
    await holder._render_result(IntentResult(text="hey"), SimpleNamespace(quiet=True))
    assert capsys.readouterr().out == ""


async def test_render_empty_text_noop():
    captured = []
    holder = _Holder(await _console_manager(captured.append))
    await holder._render_result(IntentResult(text=""), SimpleNamespace(quiet=False))
    assert captured == []
