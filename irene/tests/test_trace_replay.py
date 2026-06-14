"""
ARCH-19 slice 5 — replay tool building blocks + the --step seam + seed wiring.

The full end-to-end replay needs real models (build_core); here we unit-test the pure pieces
(diff, config-subset overlay, model-mismatch, seed reconstruction), the TraceInput chunker, the
trace_step/--step hook seam, and the TraceReplayer.load round-trip from a saved envelope.
"""

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ..config.models import TraceConfig
from ..core.trace_context import (
    TraceContext, trace_scope, trace_step, set_step_hook, make_trace,
)
from ..inputs.trace_input import TraceInput
from ..tools.replay_trace import (
    diff_output, apply_config_subset, model_mismatches, seed_context_fields, TraceReplayer,
)


def _arun(coro):
    return asyncio.run(coro)


class _Result:
    def __init__(self, text="готово", success=True, actions=None):
        self.text = text
        self.success = success
        self.action_metadata = actions or []


class TestDiffOutput(unittest.TestCase):
    def test_match(self):
        rec = {"text": "готово", "success": True, "actions": []}
        rep = diff_output(_Result(), rec)
        self.assertTrue(rep["match"])
        self.assertTrue(all(f["match"] for f in rep["fields"].values()))

    def test_text_mismatch(self):
        rep = diff_output(_Result(text="другое"), {"text": "готово", "success": True})
        self.assertFalse(rep["match"])
        self.assertFalse(rep["fields"]["text"]["match"])
        self.assertTrue(rep["fields"]["success"]["match"])

    def test_text_whitespace_insensitive(self):
        rep = diff_output(_Result(text="  готово  "), {"text": "готово", "success": True})
        self.assertTrue(rep["fields"]["text"]["match"])


class TestConfigSubset(unittest.TestCase):
    def test_apply_known_skip_unknown(self):
        cfg = SimpleNamespace(vad=SimpleNamespace(threshold=0.01), asr=SimpleNamespace(provider="vosk"))
        notes = apply_config_subset(cfg, {"vad": {"threshold": 0.5, "nope": 1}, "ghost": {"x": 1}})
        self.assertEqual(cfg.vad.threshold, 0.5)
        self.assertTrue(any("vad.threshold" in n for n in notes))
        self.assertTrue(any("skip vad.nope" in n for n in notes))
        self.assertTrue(any("skip ghost" in n for n in notes))

    def test_model_mismatch_detected(self):
        cfg = SimpleNamespace(asr=SimpleNamespace(providers={"whisper": {}}))
        self.assertEqual(model_mismatches({"asr": "vosk"}, cfg), [("asr", "vosk")])

    def test_model_present_no_mismatch(self):
        cfg = SimpleNamespace(asr=SimpleNamespace(providers={"vosk": {}}))
        self.assertEqual(model_mismatches({"asr": "vosk"}, cfg), [])

    def test_no_introspection_assumes_present(self):
        cfg = SimpleNamespace(asr=SimpleNamespace())  # no .providers → superset assumption
        self.assertEqual(model_mismatches({"asr": "vosk"}, cfg), [])


class TestSeedFields(unittest.TestCase):
    def test_populates_settable(self):
        ctx = SimpleNamespace(client_id=None, room_name=None, language="ru",
                              conversation_history=[], handler_contexts={}, state_context={},
                              user_id=None, supported_languages=["ru"])
        seed_context_fields(ctx, {"client_id": "kitchen", "room_name": "Кухня",
                                  "conversation_history": [{"u": "hi"}], "missing": "ignored"})
        self.assertEqual(ctx.client_id, "kitchen")
        self.assertEqual(ctx.room_name, "Кухня")
        self.assertEqual(ctx.conversation_history, [{"u": "hi"}])


class TestTraceInput(unittest.TestCase):
    def test_chunks_into_frames(self):
        ti = TraceInput(b"\x00" * 1000, sample_rate=16000, channels=1, frame_ms=20)

        async def collect():
            await ti.start_listening()
            return [f async for f in ti.listen()]

        frames = _arun(collect())
        # 16000 * 0.02 * 2 bytes = 640-byte frames → 1000 bytes = 640 + 360
        self.assertEqual(len(frames), 2)
        self.assertEqual(len(frames[0].data), 640)
        self.assertEqual(len(frames[1].data), 360)
        self.assertEqual(frames[0].sample_rate, 16000)
        self.assertEqual(frames[0].timestamp, 0.0)
        self.assertAlmostEqual(frames[1].timestamp, 0.02, places=4)

    def test_no_frames_until_started(self):
        ti = TraceInput(b"\x00" * 640)

        async def collect():
            return [f async for f in ti.listen()]  # never start_listening

        self.assertEqual(_arun(collect()), [])


class TestStepSeam(unittest.TestCase):
    def test_trace_step_awaits_hook(self):
        seen = []

        async def hook(stage, data):
            seen.append((stage, data))

        trace = TraceContext(enabled=True)
        trace.step_hook = hook

        async def run():
            with trace_scope(trace):
                await trace_step("nlu", {"intent": "timer.set"})

        _arun(run())
        self.assertEqual(seen, [("nlu", {"intent": "timer.set"})])
        self.assertEqual(trace.current_stage, "nlu")

    def test_trace_step_noop_without_hook(self):
        trace = TraceContext(enabled=True)  # no step_hook

        async def run():
            with trace_scope(trace):
                await trace_step("nlu", {})  # must not raise

        _arun(run())

    def test_make_trace_inherits_global_hook(self):
        async def hook(stage, data):
            pass
        set_step_hook(hook)
        try:
            t = make_trace(TraceConfig(enabled=True))
            self.assertIs(t.step_hook, hook)
        finally:
            set_step_hook(None)
        # cleared globally → a fresh trace has no hook
        self.assertIsNone(make_trace(TraceConfig(enabled=True)).step_hook)


class TestReplayerLoad(unittest.TestCase):
    def _write_trace(self, d):
        trace = TraceContext(enabled=True, request_id="rq-1")
        trace.record_input("audio", audio_bytes=b"abcd", audio_format={"rate": 16000, "channels": 1})
        trace.record_request({"source": "audio", "room": "Кухня"})
        trace.record_output(_Result())
        path = Path(d) / "rq-1.json"
        trace.to_file(path)
        return path

    def test_load_reads_replay_and_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._write_trace(d)
            r = TraceReplayer(path, Path("configs/config-master.toml"))
            r.load()
            self.assertEqual(r.replay["input"]["kind"], "audio")
            self.assertEqual(r.recorded["text"], "готово")

    def test_load_rejects_non_replayable(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "bad.json"
            path.write_text(json.dumps({"replay": {}}), encoding="utf-8")
            r = TraceReplayer(path, Path("configs/config-master.toml"))
            with self.assertRaises(ValueError):
                r.load()


if __name__ == "__main__":
    unittest.main()
