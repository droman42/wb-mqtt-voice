"""
TEST-7 Phase D — characterization tests for the replay-trace CLI wiring.

The pure helpers (diff_output / apply_config_subset / model_mismatches / seed_context_fields)
and TraceReplayer.load are already covered by test_trace_replay.py. Here we cover the *wiring*
of TraceReplayer with a fake core (object.__new__ + SimpleNamespace workflow_manager /
context_manager): _seed, the three _reinject branches (text / audio-utterance / audio-stream),
_listen, the --step seam (_step_trace / _interactive_step), close(), run(), the report
formatter, and main_async's return-code wiring.

NOT covered here (needs real models / build_core → smoke harness): TraceReplayer.build() and
the argparse entry point main().
"""

import asyncio
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from locveil_voice import core as _core_pkg  # noqa: F401  (ensure package import)
from locveil_voice.core import trace_context as _tc
from locveil_voice.core.trace_context import TraceContext, set_step_hook
from locveil_voice.tools.replay_trace import TraceReplayer, _print_report, main_async, write_trace_audio_to_wav


def _arun(coro):
    return asyncio.run(coro)


class _Result:
    def __init__(self, text="готово", success=True, actions=None):
        self.text = text
        self.success = success
        self.action_metadata = actions or []


def _replayer(**over):
    """A TraceReplayer with construction bypassed and sane defaults the wiring can override."""
    r = object.__new__(TraceReplayer)
    r.trace_path = Path("dummy.json")
    r.config_path = Path("configs/config-master.toml")
    r.mode = "local"
    r.record_out = None
    r.do_listen = False
    r.do_step = False
    r.trace = {}
    r.replay = {}
    r.recorded = {}
    r.core = None
    for k, v in over.items():
        setattr(r, k, v)
    return r


# --------------------------------------------------------------------------------------------
# _seed
# --------------------------------------------------------------------------------------------

class TestSeed(unittest.TestCase):
    def _make_core(self):
        ctx = SimpleNamespace(client_id=None, room_name=None, language=None,
                              conversation_history=None, handler_contexts=None,
                              state_context=None, user_id=None, supported_languages=None)
        seen = {}

        async def get_or_create_context(session_id):
            seen["session_id"] = session_id
            return ctx

        core = SimpleNamespace(context_manager=SimpleNamespace(
            get_or_create_context=get_or_create_context))
        return core, ctx, seen

    def test_seed_uses_session_id_and_populates_fields(self):
        core, ctx, seen = self._make_core()
        r = _replayer(core=core, replay={"seed_context": {
            "session_id": "sess-42", "client_id": "kitchen", "room_name": "Кухня"}})
        sid = _arun(r._seed())
        self.assertEqual(sid, "sess-42")
        self.assertEqual(seen["session_id"], "sess-42")
        self.assertEqual(ctx.client_id, "kitchen")
        self.assertEqual(ctx.room_name, "Кухня")

    def test_seed_defaults_session_id_when_absent(self):
        core, ctx, seen = self._make_core()
        r = _replayer(core=core, replay={})  # no seed_context at all
        sid = _arun(r._seed())
        self.assertEqual(sid, "replay_session")
        self.assertEqual(seen["session_id"], "replay_session")


# --------------------------------------------------------------------------------------------
# _step_trace seam
# --------------------------------------------------------------------------------------------

class TestStepTrace(unittest.TestCase):
    def test_none_when_step_disabled(self):
        r = _replayer(do_step=False)
        self.assertIsNone(r._step_trace())

    def test_trace_with_hook_when_step_enabled(self):
        r = _replayer(do_step=True)
        t = r._step_trace()
        self.assertIsInstance(t, TraceContext)
        self.assertTrue(t.enabled)
        self.assertEqual(t.step_hook, r._interactive_step)  # bound method equality
        self.assertEqual(t.step_hook.__func__, TraceReplayer._interactive_step)


# --------------------------------------------------------------------------------------------
# _reinject — the three input branches
# --------------------------------------------------------------------------------------------

class TestReinjectText(unittest.TestCase):
    def test_text_path_calls_process_text_input(self):
        captured = {}

        async def process_text_input(text, session_id=None, trace_context=None):
            captured.update(text=text, session_id=session_id, trace_context=trace_context)
            return _Result(text="echo")

        core = SimpleNamespace(workflow_manager=SimpleNamespace(
            process_text_input=process_text_input))
        r = _replayer(core=core, replay={"input": {"kind": "text", "text": "привет"}})
        out = _arun(r._reinject("s1"))
        self.assertEqual(out.text, "echo")
        self.assertEqual(captured["text"], "привет")
        self.assertEqual(captured["session_id"], "s1")
        self.assertIsNone(captured["trace_context"])  # do_step False


class TestReinjectAudioUtterance(unittest.TestCase):
    def test_utterance_builds_audiodata_and_calls_process_audio_input(self):
        import base64
        captured = {}

        async def process_audio_input(audio, session_id=None, client_context=None,
                                      trace_context=None):
            captured.update(audio=audio, session_id=session_id, client_context=client_context)
            return _Result(text="from-audio")

        core = SimpleNamespace(workflow_manager=SimpleNamespace(
            process_audio_input=process_audio_input))
        payload = base64.b64encode(b"\x01\x02\x03\x04").decode()
        r = _replayer(core=core, replay={"input": {
            "kind": "audio", "capture_level": "utterance", "audio_base64": payload,
            "format": {"rate": 8000, "channels": 2, "format": "pcm16"}}})
        out = _arun(r._reinject("s2"))
        self.assertEqual(out.text, "from-audio")
        self.assertEqual(captured["session_id"], "s2")
        self.assertEqual(captured["client_context"], {"skip_asr": False})
        self.assertEqual(captured["audio"].data, b"\x01\x02\x03\x04")
        self.assertEqual(captured["audio"].sample_rate, 8000)
        self.assertEqual(captured["audio"].channels, 2)

    def test_utterance_defaults_format_when_missing(self):
        captured = {}

        async def process_audio_input(audio, session_id=None, client_context=None,
                                      trace_context=None):
            captured["audio"] = audio
            return _Result()

        core = SimpleNamespace(workflow_manager=SimpleNamespace(
            process_audio_input=process_audio_input))
        # no audio_base64, no format → defaults (rate 16000, ch 1, pcm16), empty bytes
        r = _replayer(core=core, replay={"input": {
            "kind": "audio", "capture_level": "utterance"}})
        _arun(r._reinject("s3"))
        self.assertEqual(captured["audio"].data, b"")
        self.assertEqual(captured["audio"].sample_rate, 16000)
        self.assertEqual(captured["audio"].channels, 1)


class TestReinjectStream(unittest.TestCase):
    def test_segmenter_level_drives_process_audio_stream(self):
        import base64
        seen = {}

        async def process_audio_stream(frame_iter, session_id=None, skip_wake_word=None):
            seen.update(session_id=session_id, skip_wake_word=skip_wake_word)
            count = 0
            async for _frame in frame_iter:  # consume the TraceInput chunker
                count += 1
            seen["frames"] = count
            yield _Result(text="r1")
            yield _Result(text="r2")  # last one wins

        core = SimpleNamespace(workflow_manager=SimpleNamespace(
            process_audio_stream=process_audio_stream))
        payload = base64.b64encode(b"\x00" * 1000).decode()
        r = _replayer(core=core, replay={"input": {
            "kind": "audio", "capture_level": "segmenter", "audio_base64": payload,
            "format": {"rate": 16000, "channels": 1}}})
        out = _arun(r._reinject("s4"))
        self.assertEqual(out.text, "r2")
        self.assertEqual(seen["session_id"], "s4")
        self.assertTrue(seen["skip_wake_word"])
        self.assertGreater(seen["frames"], 0)

    def test_stream_returns_none_when_no_results(self):
        import base64

        async def process_audio_stream(frame_iter, session_id=None, skip_wake_word=None):
            async for _ in frame_iter:
                pass
            return
            yield  # pragma: no cover — makes this an async generator

        core = SimpleNamespace(workflow_manager=SimpleNamespace(
            process_audio_stream=process_audio_stream))
        payload = base64.b64encode(b"\x00" * 320).decode()
        r = _replayer(core=core, replay={"input": {
            "kind": "audio", "capture_level": "raw", "audio_base64": payload}})
        self.assertIsNone(_arun(r._reinject("s5")))


# --------------------------------------------------------------------------------------------
# _listen (D-11) — best-effort playback
# --------------------------------------------------------------------------------------------

class TestListen(unittest.TestCase):
    def test_noop_for_text_input(self):
        r = _replayer(replay={"input": {"kind": "text", "text": "hi"}})
        _arun(r._listen())  # must not raise, no core access

    def test_skips_when_no_audio_component(self):
        core = SimpleNamespace(component_manager=SimpleNamespace(
            get_component=lambda name: None))
        r = _replayer(core=core, replay={"input": {"kind": "audio", "audio_base64": ""}})
        _arun(r._listen())  # warns + returns, no raise

    def test_plays_stream_when_component_present(self):
        import base64
        from locveil_voice.components.audio_component import AudioComponent
        played = {}

        # AudioComponent.play_stream takes raw PCM BYTES (not an async generator); _listen must
        # pass the decoded bytes. The component must be a real AudioComponent (isinstance gate).
        async def play_stream(data, sample_rate=None, channels=None, sample_width=None):
            played.update(data=data, sample_rate=sample_rate,
                          channels=channels, sample_width=sample_width)

        audio_comp = object.__new__(AudioComponent)
        audio_comp.play_stream = play_stream
        core = SimpleNamespace(component_manager=SimpleNamespace(
            get_component=lambda name: audio_comp))
        payload = base64.b64encode(b"WAVE").decode()
        r = _replayer(core=core, replay={"input": {
            "kind": "audio", "audio_base64": payload, "format": {"rate": 22050, "channels": 2}}})
        _arun(r._listen())
        self.assertEqual(played["data"], b"WAVE")
        self.assertEqual(played["sample_rate"], 22050)
        self.assertEqual(played["channels"], 2)

    def test_swallows_playback_exception(self):
        def boom(name):
            raise RuntimeError("device gone")

        core = SimpleNamespace(component_manager=SimpleNamespace(get_component=boom))
        r = _replayer(core=core, replay={"input": {"kind": "audio", "audio_base64": ""}})
        _arun(r._listen())  # exception swallowed → no raise


# --------------------------------------------------------------------------------------------
# _interactive_step (D-12)
# --------------------------------------------------------------------------------------------

class TestInteractiveStep(unittest.TestCase):
    def test_early_return_when_disabled(self):
        r = _replayer()
        r._step_disabled = True
        with mock.patch("builtins.input", side_effect=AssertionError("input must not be called")):
            buf = io.StringIO()
            with redirect_stdout(buf):
                _arun(r._interactive_step("nlu", {"x": 1}))
        self.assertEqual(buf.getvalue(), "")  # nothing printed

    def test_enter_continues_and_prints_stage(self):
        r = _replayer()
        with mock.patch("builtins.input", return_value=""):
            buf = io.StringIO()
            with redirect_stdout(buf):
                _arun(r._interactive_step("asr", {"text": "x" * 500}))
        out = buf.getvalue()
        self.assertIn("stage: asr", out)
        self.assertIn("text:", out)
        self.assertFalse(getattr(r, "_step_disabled", False))

    def test_c_disables_further_steps(self):
        r = _replayer()
        with mock.patch("builtins.input", return_value="c"):
            buf = io.StringIO()
            with redirect_stdout(buf):
                _arun(r._interactive_step("vad", {}))
        self.assertTrue(r._step_disabled)

    def test_q_aborts_with_systemexit(self):
        r = _replayer()
        with mock.patch("builtins.input", return_value="q"):
            buf = io.StringIO()
            with redirect_stdout(buf):
                with self.assertRaises(SystemExit):
                    _arun(r._interactive_step("nlu", {}))

    def test_eof_treated_as_continue_to_end(self):
        r = _replayer()
        with mock.patch("builtins.input", side_effect=EOFError):
            buf = io.StringIO()
            with redirect_stdout(buf):
                _arun(r._interactive_step("nlu", {}))
        self.assertTrue(r._step_disabled)  # EOF → "c"


# --------------------------------------------------------------------------------------------
# run() — orchestration + step-hook lifecycle
# --------------------------------------------------------------------------------------------

class TestRun(unittest.TestCase):
    def _core(self, result):
        ctx = SimpleNamespace(client_id=None, room_name=None, language=None,
                              conversation_history=None, handler_contexts=None,
                              state_context=None, user_id=None, supported_languages=None)

        async def get_or_create_context(session_id):
            return ctx

        async def process_text_input(text, session_id=None, trace_context=None):
            return result

        return SimpleNamespace(
            context_manager=SimpleNamespace(get_or_create_context=get_or_create_context),
            workflow_manager=SimpleNamespace(process_text_input=process_text_input))

    def test_run_diffs_against_recorded(self):
        core = self._core(_Result(text="готово"))
        r = _replayer(core=core,
                      replay={"input": {"kind": "text", "text": "go"},
                              "seed_context": {"session_id": "s"}},
                      recorded={"text": "готово", "success": True, "actions": []})
        report = _arun(r.run())
        self.assertTrue(report["match"])

    def test_run_step_hook_set_and_cleared(self):
        core = self._core(_Result())
        r = _replayer(core=core, do_step=True,
                      replay={"input": {"kind": "text", "text": "go"},
                              "seed_context": {"session_id": "s"}},
                      recorded={"text": "готово", "success": True})
        self.assertIsNone(_tc._step_hook)
        try:
            _arun(r.run())
            self.assertIsNone(_tc._step_hook)  # restored to None in finally
        finally:
            set_step_hook(None)  # safety net — never pollute global

    def test_run_invokes_listen_when_enabled(self):
        import base64
        listened = {}

        async def get_or_create_context(session_id):
            return SimpleNamespace()

        async def process_audio_input(audio, session_id=None, client_context=None,
                                      trace_context=None):
            return _Result(text="готово")

        from locveil_voice.components.audio_component import AudioComponent

        async def play_stream(data, sample_rate=None, channels=None, sample_width=None):
            listened["played"] = data  # raw bytes, per AudioComponent.play_stream

        audio_comp = object.__new__(AudioComponent)
        audio_comp.play_stream = play_stream
        core = SimpleNamespace(
            context_manager=SimpleNamespace(get_or_create_context=get_or_create_context),
            workflow_manager=SimpleNamespace(process_audio_input=process_audio_input),
            component_manager=SimpleNamespace(get_component=lambda name: audio_comp))
        payload = base64.b64encode(b"snd").decode()
        r = _replayer(core=core, do_listen=True, replay={
            "input": {"kind": "audio", "capture_level": "utterance", "audio_base64": payload},
            "seed_context": {"session_id": "s"}},
            recorded={"text": "готово", "success": True})
        report = _arun(r.run())
        self.assertTrue(report["match"])
        self.assertEqual(listened["played"], b"snd")

    def test_run_handles_none_result(self):
        # a stream that yields nothing → _reinject returns None → report is the not-matched sentinel
        async def get_or_create_context(session_id):
            return SimpleNamespace()

        async def process_audio_stream(frame_iter, session_id=None, skip_wake_word=None):
            async for _ in frame_iter:
                pass
            return
            yield  # pragma: no cover

        core = SimpleNamespace(
            context_manager=SimpleNamespace(get_or_create_context=get_or_create_context),
            workflow_manager=SimpleNamespace(process_audio_stream=process_audio_stream))
        r = _replayer(core=core, replay={
            "input": {"kind": "audio", "capture_level": "raw", "audio_base64": ""},
            "seed_context": {"session_id": "s"}})
        report = _arun(r.run())
        self.assertFalse(report["match"])
        self.assertEqual(report["fields"], {})


# --------------------------------------------------------------------------------------------
# close()
# --------------------------------------------------------------------------------------------

class TestClose(unittest.TestCase):
    def test_close_noop_without_core(self):
        r = _replayer(core=None)
        _arun(r.close())  # no raise

    def test_close_stops_core(self):
        stopped = {}

        async def stop():
            stopped["yes"] = True

        r = _replayer(core=SimpleNamespace(stop=stop))
        _arun(r.close())
        self.assertTrue(stopped["yes"])

    def test_close_swallows_stop_error(self):
        async def stop():
            raise RuntimeError("nope")

        r = _replayer(core=SimpleNamespace(stop=stop))
        _arun(r.close())  # swallowed


# --------------------------------------------------------------------------------------------
# _print_report formatter
# --------------------------------------------------------------------------------------------

class TestPrintReport(unittest.TestCase):
    def test_match_report(self):
        r = _replayer(mode="local", record_out=None)
        report = {"match": True, "fields": {
            "text": {"match": True, "recorded": "a", "replayed": "a"}}}
        buf = io.StringIO()
        with redirect_stdout(buf):
            _print_report(report, r)
        out = buf.getvalue()
        self.assertIn("MATCH", out)
        self.assertIn("--local", out)
        self.assertNotIn("recorded:", out)  # matched field doesn't dump detail

    def test_mismatch_report_dumps_detail_and_record_out(self):
        r = _replayer(mode="reproduce", record_out=Path("out/dir"))
        report = {"match": False, "fields": {
            "text": {"match": False, "recorded": "x", "replayed": "y"}}}
        buf = io.StringIO()
        with redirect_stdout(buf):
            _print_report(report, r)
        out = buf.getvalue()
        self.assertIn("MISMATCH", out)
        self.assertIn("recorded: x", out)
        self.assertIn("replayed: y", out)
        self.assertIn("out/dir", out)


# --------------------------------------------------------------------------------------------
# main_async — return-code wiring (build/run/close patched; build needs real models)
# --------------------------------------------------------------------------------------------

class TestMainAsync(unittest.TestCase):
    def _args(self, **over):
        base = dict(trace=Path("t.json"), config=Path("c.toml"), reproduce=False,
                    record_out=None, listen=False, step=False)
        base.update(over)
        return SimpleNamespace(**base)

    def test_returns_zero_on_match(self):
        async def fake_build(self):
            return None

        async def fake_run(self):
            return {"match": True, "fields": {}}

        async def fake_close(self):
            return None

        with mock.patch.object(TraceReplayer, "load", lambda self: None), \
             mock.patch.object(TraceReplayer, "build", fake_build), \
             mock.patch.object(TraceReplayer, "run", fake_run), \
             mock.patch.object(TraceReplayer, "close", fake_close):
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = _arun(main_async(self._args()))
        self.assertEqual(rc, 0)

    def test_returns_two_on_mismatch_and_closes_on_error(self):
        closed = {}

        async def fake_build(self):
            return None

        async def fake_run(self):
            return {"match": False, "fields": {}}

        async def fake_close(self):
            closed["yes"] = True

        with mock.patch.object(TraceReplayer, "load", lambda self: None), \
             mock.patch.object(TraceReplayer, "build", fake_build), \
             mock.patch.object(TraceReplayer, "run", fake_run), \
             mock.patch.object(TraceReplayer, "close", fake_close):
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = _arun(main_async(self._args(reproduce=True)))
        self.assertEqual(rc, 2)
        self.assertTrue(closed["yes"])

    def test_close_runs_even_when_run_raises(self):
        closed = {}

        async def fake_build(self):
            return None

        async def fake_run(self):
            raise RuntimeError("boom")

        async def fake_close(self):
            closed["yes"] = True

        with mock.patch.object(TraceReplayer, "load", lambda self: None), \
             mock.patch.object(TraceReplayer, "build", fake_build), \
             mock.patch.object(TraceReplayer, "run", fake_run), \
             mock.patch.object(TraceReplayer, "close", fake_close):
            with self.assertRaises(RuntimeError):
                _arun(main_async(self._args()))
        self.assertTrue(closed["yes"])  # close() ran in the finally


class TestExtractWav(unittest.TestCase):
    """TEST-14 (D-9): one golden trace → the WS WAV fixture (record once, test twice)."""

    def _audio_trace(self, pcm: bytes, *, rate=16000, channels=1, fmt="pcm16"):
        import base64
        return {"replay": {"input": {
            "kind": "audio",
            "audio_base64": base64.b64encode(pcm).decode("ascii"),
            "format": {"rate": rate, "channels": channels, "format": fmt},
        }}}

    def test_extracts_pcm_to_readable_wav(self):
        import tempfile
        import wave
        pcm = b"\x01\x02\x03\x04" * 400  # 1600 bytes → 800 frames mono 16-bit
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "nested" / "fixture.wav"
            info = write_trace_audio_to_wav(self._audio_trace(pcm, rate=16000), out)
            self.assertTrue(out.exists())  # parent dir auto-created
            self.assertEqual((info["rate"], info["channels"], info["frames"]), (16000, 1, 800))
            with wave.open(str(out), "rb") as w:
                self.assertEqual(w.getframerate(), 16000)
                self.assertEqual(w.getnchannels(), 1)
                self.assertEqual(w.getsampwidth(), 2)
                self.assertEqual(w.readframes(w.getnframes()), pcm)  # round-trips exactly

    def test_rejects_text_trace(self):
        with self.assertRaises(ValueError):
            write_trace_audio_to_wav({"replay": {"input": {"kind": "text", "text": "hi"}}}, Path("/tmp/x.wav"))

    def test_rejects_unsupported_sample_format(self):
        with self.assertRaises(ValueError):
            write_trace_audio_to_wav(self._audio_trace(b"\x00\x00", fmt="opus"), Path("/tmp/x.wav"))


if __name__ == "__main__":
    unittest.main()
