"""Characterization tests for the voice runner wiring (TEST-7 Phase D).

The existing ``test_voice_runner.py`` covers the two pure config methods. This file covers the
post-core wiring that the runner is actually responsible for, using ``object.__new__`` + a
``SimpleNamespace`` core so no heavy ``BaseRunner``/core construction is needed:

  * ``check_voice_dependencies`` / ``_check_dependencies`` — the sounddevice availability probe
    (both the present and the ``ImportError`` paths, the latter forced via ``sys.modules``).
  * ``list_audio_devices`` / ``_handle_runner_utility_options`` — the ``--list-devices`` utility.
  * ``_post_core_setup`` — microphone start/already-active/missing/no-core branches.
  * ``_start_voice_audio_workflow`` — local SPEECH output registration, the skip-wake-word decision,
    the result loop, and the early-return + re-raise error paths.

The real microphone capture loop (``_execute_runner_logic`` keep-alive + a live audio stream) needs
hardware and a booted core, so it is intentionally left to the smoke harness.
"""

import asyncio
import builtins
import contextlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from locveil_voice.runners.voice_runner import (
    VoiceRunner,
    check_voice_dependencies,
    list_audio_devices,
)


def _arun(coro):
    return asyncio.run(coro)


def _runner():
    # Bypass BaseRunner.__init__; the wiring methods only touch attributes we set explicitly.
    return object.__new__(VoiceRunner)


_MISSING = object()


@contextlib.contextmanager
def _no_sounddevice():
    """Force ``import sounddevice`` to raise ImportError, then restore sys.modules exactly."""
    saved = sys.modules.get("sounddevice", _MISSING)
    sys.modules["sounddevice"] = None  # CPython: a None entry makes `import` raise ImportError
    try:
        yield
    finally:
        if saved is _MISSING:
            sys.modules.pop("sounddevice", None)
        else:
            sys.modules["sounddevice"] = saved


@contextlib.contextmanager
def _with_sounddevice():
    """Make ``import sounddevice`` succeed with a stub — HERMETIC 'present' (no real PortAudio
    native lib needed, so this holds on a headless CI runner)."""
    saved = sys.modules.get("sounddevice", _MISSING)
    sys.modules["sounddevice"] = SimpleNamespace(__name__="sounddevice")
    try:
        yield
    finally:
        if saved is _MISSING:
            sys.modules.pop("sounddevice", None)
        else:
            sys.modules["sounddevice"] = saved


@contextlib.contextmanager
def _sounddevice_raises(exc):
    """Force ``import sounddevice`` to raise `exc` (e.g. OSError: PortAudio not found) — models the
    package-present-but-native-lib-absent case the probe must survive."""
    saved = sys.modules.pop("sounddevice", _MISSING)
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "sounddevice":
            raise exc
        return real_import(name, *args, **kwargs)

    try:
        with patch.object(builtins, "__import__", side_effect=fake_import):
            yield
    finally:
        if saved is not _MISSING:
            sys.modules["sounddevice"] = saved


# --------------------------------------------------------------------------- fakes for the core

class _OutputManager:
    def __init__(self):
        self.added = {}
        self.fallback = None

    async def add_output(self, name, output):
        self.added[name] = output

    def designate_conversational_fallback(self, name):
        self.fallback = name


class _ComponentManager:
    def __init__(self, components):
        self._components = components

    def get_component(self, name):
        return self._components.get(name)


class _WorkflowManager:
    def __init__(self, results=None, raise_exc=None):
        self._results = results or []
        self._raise = raise_exc
        self.calls = None

    def _get_audio_stream(self, mic_input):
        return ("audio-stream-for", mic_input)

    def process_audio_stream(self, **kwargs):
        self.calls = kwargs
        results, raise_exc = self._results, self._raise

        async def _gen():
            if raise_exc is not None:
                raise raise_exc
            for r in results:
                yield r

        return _gen()


def _result(text="привет", actions=None):
    return SimpleNamespace(text=text, action_metadata=actions)


def _core(*, results=None, raise_exc=None, has_mic=True, has_voice_trigger=True,
          tts=_MISSING, audio=_MISSING, output_manager=True, component_manager=True,
          workflow_manager=True):
    sources = {"microphone": SimpleNamespace(name="mic")} if has_mic else {}
    tts_c = object() if tts is _MISSING else tts
    audio_c = object() if audio is _MISSING else audio
    components = {
        "tts": tts_c,
        "audio": audio_c,
        "voice_trigger": object() if has_voice_trigger else None,
    }
    return SimpleNamespace(
        config=SimpleNamespace(
            audio=SimpleNamespace(playback_mode="file"),
            asr=SimpleNamespace(default_provider="whisper"),
        ),
        output_manager=_OutputManager() if output_manager else None,
        component_manager=_ComponentManager(components) if component_manager else None,
        input_manager=SimpleNamespace(_sources=sources, _active_sources=set()),
        workflow_manager=_WorkflowManager(results=results, raise_exc=raise_exc)
        if workflow_manager else None,
    )


# --------------------------------------------------------------------------- dependency probe

class TestDependencyProbe(unittest.TestCase):
    def test_check_voice_dependencies_present(self):
        with _with_sounddevice():
            self.assertTrue(check_voice_dependencies())

    def test_check_voice_dependencies_absent(self):
        with _no_sounddevice():
            self.assertFalse(check_voice_dependencies())

    def test_check_voice_dependencies_oserror_degrades(self):
        # package present but PortAudio native lib missing → OSError on import → must return False,
        # not crash (the probe's job is to report availability).
        with _sounddevice_raises(OSError("PortAudio library not found")):
            self.assertFalse(check_voice_dependencies())

    def test_check_dependencies_check_deps_flag_delegates(self):
        runner = _runner()
        args = SimpleNamespace(check_deps=True, quiet=True)
        with _with_sounddevice():
            self.assertTrue(_arun(runner._check_dependencies(args)))
        with _no_sounddevice():
            self.assertFalse(_arun(runner._check_dependencies(args)))

    def test_check_dependencies_probe_present(self):
        runner = _runner()
        args = SimpleNamespace(check_deps=False, quiet=True)
        with _with_sounddevice():
            self.assertTrue(_arun(runner._check_dependencies(args)))

    def test_check_dependencies_probe_oserror_degrades(self):
        runner = _runner()
        with _sounddevice_raises(OSError("PortAudio library not found")):
            self.assertFalse(_arun(runner._check_dependencies(
                SimpleNamespace(check_deps=False, quiet=True))))

    def test_check_dependencies_probe_absent_quiet_and_verbose(self):
        runner = _runner()
        with _no_sounddevice():
            self.assertFalse(_arun(runner._check_dependencies(
                SimpleNamespace(check_deps=False, quiet=True))))
            self.assertFalse(_arun(runner._check_dependencies(
                SimpleNamespace(check_deps=False, quiet=False))))


# --------------------------------------------------------------------------- utility options

class TestUtilityOptions(unittest.TestCase):
    def test_list_audio_devices_unavailable(self):
        with patch("locveil_voice.utils.audio_devices.is_audio_available", return_value=False):
            # Should print a hint and return without touching print_audio_devices/hardware.
            self.assertIsNone(list_audio_devices())

    def test_list_audio_devices_available(self):
        with patch("locveil_voice.utils.audio_devices.is_audio_available", return_value=True), \
                patch("locveil_voice.utils.audio_devices.print_audio_devices") as printer:
            list_audio_devices()
            printer.assert_called_once()

    def test_handle_utility_list_devices(self):
        runner = _runner()
        with patch("locveil_voice.runners.voice_runner.list_audio_devices") as lister:
            rc = _arun(runner._handle_runner_utility_options(
                SimpleNamespace(list_devices=True)))
            self.assertEqual(rc, 0)
            lister.assert_called_once()

    def test_handle_utility_no_option(self):
        runner = _runner()
        self.assertIsNone(_arun(runner._handle_runner_utility_options(
            SimpleNamespace(list_devices=False))))


# --------------------------------------------------------------------------- _post_core_setup

class TestPostCoreSetup(unittest.TestCase):
    def _runner_with_stubbed_workflow(self, core):
        runner = _runner()
        runner.core = core
        runner._start_voice_audio_workflow = AsyncMock()
        return runner

    def test_starts_inactive_microphone(self):
        started = []

        async def start_source(name):
            started.append(name)
            return True

        im = SimpleNamespace(_sources={"microphone": object()}, _active_sources=set(),
                             start_source=start_source)
        core = SimpleNamespace(input_manager=im,
                               config=SimpleNamespace(asr=SimpleNamespace(default_provider="whisper")))
        runner = self._runner_with_stubbed_workflow(core)
        _arun(runner._post_core_setup(SimpleNamespace(quiet=True)))
        self.assertEqual(started, ["microphone"])
        runner._start_voice_audio_workflow.assert_called_once()
        self.assertIsInstance(runner._mic_task, asyncio.Task)  # CR-A1: launched as a background task, not awaited

    def test_start_failure_does_not_raise(self):
        async def start_source(name):
            return False

        im = SimpleNamespace(_sources={"microphone": object()}, _active_sources=set(),
                             start_source=start_source)
        core = SimpleNamespace(input_manager=im,
                               config=SimpleNamespace(asr=SimpleNamespace(default_provider="x")))
        runner = self._runner_with_stubbed_workflow(core)
        _arun(runner._post_core_setup(SimpleNamespace(quiet=True)))
        runner._start_voice_audio_workflow.assert_called_once()
        self.assertIsInstance(runner._mic_task, asyncio.Task)  # CR-A1: launched as a background task, not awaited

    def test_already_active_microphone_not_restarted(self):
        started = []

        async def start_source(name):
            started.append(name)
            return True

        im = SimpleNamespace(_sources={"microphone": object()},
                             _active_sources={"microphone"}, start_source=start_source)
        core = SimpleNamespace(input_manager=im,
                               config=SimpleNamespace(asr=SimpleNamespace(default_provider="x")))
        runner = self._runner_with_stubbed_workflow(core)
        _arun(runner._post_core_setup(SimpleNamespace(quiet=True)))
        self.assertEqual(started, [])  # already active → no start_source call

    def test_missing_microphone_source(self):
        started = []

        async def start_source(name):
            started.append(name)
            return True

        im = SimpleNamespace(_sources={}, _active_sources=set(), start_source=start_source)
        core = SimpleNamespace(input_manager=im,
                               config=SimpleNamespace(asr=SimpleNamespace(default_provider="x")))
        runner = self._runner_with_stubbed_workflow(core)
        _arun(runner._post_core_setup(SimpleNamespace(quiet=True)))
        self.assertEqual(started, [])
        runner._start_voice_audio_workflow.assert_called_once()
        self.assertIsInstance(runner._mic_task, asyncio.Task)  # CR-A1: launched as a background task, not awaited

    def test_no_core_skips_mic_block_but_still_starts_workflow(self):
        runner = self._runner_with_stubbed_workflow(None)
        _arun(runner._post_core_setup(SimpleNamespace(quiet=True)))
        runner._start_voice_audio_workflow.assert_called_once()
        self.assertIsInstance(runner._mic_task, asyncio.Task)  # CR-A1: launched as a background task, not awaited

    def test_verbose_banner_path(self):
        async def start_source(name):
            return True

        im = SimpleNamespace(_sources={"microphone": object()}, _active_sources={"microphone"},
                             start_source=start_source)
        core = SimpleNamespace(input_manager=im,
                               config=SimpleNamespace(asr=SimpleNamespace(default_provider="vosk")))
        runner = self._runner_with_stubbed_workflow(core)
        # quiet=False exercises the banner print branch (reads config.asr.default_provider).
        _arun(runner._post_core_setup(SimpleNamespace(quiet=False)))
        runner._start_voice_audio_workflow.assert_called_once()
        self.assertIsInstance(runner._mic_task, asyncio.Task)  # CR-A1: launched as a background task, not awaited


# --------------------------------------------------------------- CR-A1: mic task lifecycle

class TestMicTaskLifecycle(unittest.TestCase):
    """The standalone serves the web API alongside the mic. The mic workflow runs an infinite loop, so
    it must be launched as a BACKGROUND task — never awaited — or the web server never starts (CR-A1)."""

    def test_blocking_mic_workflow_does_not_block_web_setup(self):
        # Regression: with the old `await self._start_voice_audio_workflow()`, this hangs forever and the
        # web server is never set up. The fix runs it as a task, so _post_core_setup completes.
        runner = _runner()
        runner.core = None  # skip the mic-start block; focus on the workflow-launch ordering

        async def _never_returns():
            await asyncio.Event().wait()  # models the never-ending mic loop

        runner._start_voice_audio_workflow = _never_returns
        web_setup = []

        async def _setup_web_server(args):
            web_setup.append(True)
            runner.app = None

        runner._setup_web_server = _setup_web_server

        async def _scenario():
            await runner._post_core_setup(SimpleNamespace(quiet=True))
            # Reached here despite the never-ending workflow → web setup ran (CR-A1 fixed).
            self.assertEqual(web_setup, [True])
            self.assertIsInstance(runner._mic_task, asyncio.Task)
            self.assertFalse(runner._mic_task.done())  # still running in the background
            await runner._cancel_mic_task()
            self.assertTrue(runner._mic_task.done())

        _arun(_scenario())

    def test_mic_task_crash_is_surfaced(self):
        # A crash inside the background mic workflow must be logged by the done-callback (an orphaned
        # task would swallow it). _on_mic_task_done reads task.exception() → must not raise.
        runner = _runner()

        async def _boom():
            raise RuntimeError("mic exploded")

        async def _scenario():
            task = asyncio.ensure_future(_boom())
            runner._mic_task = task
            with self.assertLogs("locveil_voice.runners.voice_runner", level="ERROR") as cm:
                task.add_done_callback(runner._on_mic_task_done)
                try:
                    await task
                except RuntimeError:
                    pass
                await asyncio.sleep(0)  # let the done-callback run
            self.assertTrue(any("stopped unexpectedly" in m for m in cm.output))

        _arun(_scenario())

    def test_cancel_mic_task_noop_when_absent(self):
        runner = _runner()
        runner._mic_task = None
        _arun(runner._cancel_mic_task())  # must not raise


# --------------------------------------------------------------------------- _start_voice_audio_workflow

class TestStartVoiceAudioWorkflow(unittest.TestCase):
    def _run(self, core):
        runner = _runner()
        runner.core = core
        return runner, _arun(runner._start_voice_audio_workflow())

    def test_no_workflow_manager_returns_early(self):
        core = _core(workflow_manager=False)
        runner, _ = self._run(core)
        # Nothing registered, no exception.
        self.assertEqual(core.output_manager.added, {})

    def test_no_core_returns_early(self):
        runner = _runner()
        runner.core = None
        # Must not raise.
        _arun(runner._start_voice_audio_workflow())

    def test_happy_path_registers_output_and_runs_with_wake_word(self):
        core = _core(results=[_result("включи свет", actions={"k": 1}),
                              _result("", actions=None),
                              _result("   ", actions=None)],
                     has_voice_trigger=True)
        runner, _ = self._run(core)
        # Local SPEECH output registered + designated conversational fallback.
        self.assertIn("audio", core.output_manager.added)
        self.assertEqual(core.output_manager.fallback, "audio")
        # voice_trigger present → wake word NOT skipped; correct client context + wants_audio.
        calls = core.workflow_manager.calls
        self.assertFalse(calls["skip_wake_word"])
        self.assertTrue(calls["wants_audio"])
        self.assertEqual(calls["client_context"]["runner"], "voice")
        self.assertIsNotNone(calls["audio_stream"])

    def test_skip_wake_word_when_voice_trigger_absent(self):
        core = _core(results=[], has_voice_trigger=False)
        runner, _ = self._run(core)
        self.assertTrue(core.workflow_manager.calls["skip_wake_word"])

    def test_speech_output_unavailable_when_tts_missing(self):
        core = _core(results=[], tts=None)  # is_available() → False
        runner, _ = self._run(core)
        self.assertNotIn("audio", core.output_manager.added)
        self.assertIsNone(core.output_manager.fallback)
        # Workflow still proceeds.
        self.assertIsNotNone(core.workflow_manager.calls)

    def test_no_output_manager_skips_registration(self):
        core = _core(results=[], output_manager=False)
        runner, _ = self._run(core)
        self.assertIsNotNone(core.workflow_manager.calls)

    def test_missing_microphone_source_returns_after_registration(self):
        core = _core(results=[], has_mic=False)
        runner, _ = self._run(core)
        # Output got registered before the mic lookup, but the stream never started.
        self.assertIn("audio", core.output_manager.added)
        self.assertIsNone(core.workflow_manager.calls)

    def test_stream_exception_is_logged_and_reraised(self):
        core = _core(raise_exc=RuntimeError("boom"))
        runner = _runner()
        runner.core = core
        with self.assertRaises(RuntimeError):
            _arun(runner._start_voice_audio_workflow())


if __name__ == "__main__":
    unittest.main()
