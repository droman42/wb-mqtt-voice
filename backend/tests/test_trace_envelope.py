"""
ARCH-19 slice 1 — the faithful `replay` envelope spine.

Covers the net-new surface: the `current_trace` contextvar + `trace_scope`,
the no-op-safe `trace_event()`, the un-sanitised envelope recorders, and
`build_envelope`/`to_file` producing the self-contained §2 JSON.
"""

import base64
import json
import unittest

from locveil_voice.core.trace_context import (
    TraceContext,
    current_trace,
    get_current_trace,
    trace_event,
    trace_scope,
)
from locveil_voice.intents.context_models import UnifiedConversationContext


class _Result:
    """Minimal IntentResult stand-in for record_output."""
    def __init__(self):
        self.text = "готово"
        self.success = True
        self.action_metadata = [{"domain": "timer", "action": "set"}]


class TestTraceScopeContextvar(unittest.TestCase):
    def test_scope_sets_and_resets(self):
        self.assertIsNone(get_current_trace())
        trace = TraceContext(enabled=True)
        with trace_scope(trace):
            self.assertIs(get_current_trace(), trace)
        self.assertIsNone(get_current_trace())

    def test_scope_resets_on_exception(self):
        trace = TraceContext(enabled=True)
        with self.assertRaises(ValueError):
            with trace_scope(trace):
                self.assertIs(current_trace.get(), trace)
                raise ValueError("boom")
        self.assertIsNone(current_trace.get())

    def test_none_scope_is_safe(self):
        with trace_scope(None):
            self.assertIsNone(get_current_trace())


class TestTraceEvent(unittest.TestCase):
    def test_noop_without_active_trace(self):
        # No scope set → must not raise, nothing recorded anywhere.
        trace_event("orphan", {"x": 1})
        self.assertIsNone(get_current_trace())

    def test_noop_when_disabled(self):
        trace = TraceContext(enabled=False)
        with trace_scope(trace):
            trace_event("timer_set", {"duration_s": 300}, handler="timer")
        self.assertEqual(trace.handler_events, [])

    def test_records_on_active_trace(self):
        trace = TraceContext(enabled=True)
        with trace_scope(trace):
            trace_event("timer_set", {"duration_s": 300}, handler="timer")
        self.assertEqual(len(trace.handler_events), 1)
        ev = trace.handler_events[0]
        self.assertEqual(ev["handler"], "timer")
        self.assertEqual(ev["label"], "timer_set")
        self.assertEqual(ev["data"], {"duration_s": 300})
        self.assertIn("t_ms", ev)


class TestEnvelopeRecorders(unittest.TestCase):
    def test_record_audio_input_is_full_and_base64(self):
        trace = TraceContext(enabled=True)
        audio = b"\x00\x01" * 2048  # 4 KB — would be truncated by the 1 MB sanitiser; not here
        trace.record_input("audio", audio_bytes=audio,
                           audio_format={"rate": 16000, "channels": 1}, capture_level="utterance")
        self.assertEqual(trace.capture_level, "utterance")
        env_in = trace.build_envelope()["replay"]["input"]
        self.assertEqual(env_in["kind"], "audio")
        self.assertEqual(base64.b64decode(env_in["audio_base64"]), audio)
        self.assertEqual(env_in["format"], {"rate": 16000, "channels": 1})

    def test_record_text_input(self):
        trace = TraceContext(enabled=True)
        trace.record_input("text", text="поставь таймер")
        self.assertEqual(trace.build_envelope()["replay"]["input"],
                         {"kind": "text", "text": "поставь таймер"})

    def test_config_digest_is_stable_and_subset_recorded(self):
        a = TraceContext(enabled=True)
        b = TraceContext(enabled=True)
        subset = {"vad": {"threshold": 0.01}, "asr": {"provider": "vosk"}}
        a.record_config(subset, provider_models={"asr": "vosk-ru-0.22"})
        b.record_config(dict(subset))
        self.assertTrue(a._config_digest.startswith("sha256:"))
        self.assertEqual(a._config_digest, b._config_digest)  # order-independent
        self.assertEqual(a._provider_models, {"asr": "vosk-ru-0.22"})

    def test_record_output_oracle(self):
        trace = TraceContext(enabled=True)
        trace.record_output(_Result())
        self.assertEqual(trace.recorded_output,
                         {"text": "готово", "success": True,
                          "actions": [{"domain": "timer", "action": "set"}]})

    def test_seed_context_is_json_safe(self):
        trace = TraceContext(enabled=True)
        ctx = UnifiedConversationContext(session_id="kitchen", client_id="kitchen",
                                         room_name="Кухня", language="ru")
        trace.record_seed_context(ctx)
        seed = trace._seed_context
        # conversation_state is an enum on the dataclass — must serialise to a primitive
        json.dumps(seed)  # must not raise
        self.assertEqual(seed["session_id"], "kitchen")
        self.assertEqual(seed["room_name"], "Кухня")

    def test_disabled_recorders_are_noop(self):
        trace = TraceContext(enabled=False)
        trace.record_input("text", text="x")
        trace.record_request({"a": 1})
        trace.record_output(_Result())
        trace.record_config({"k": "v"})
        env = trace.build_envelope()
        self.assertIsNone(env["replay"]["input"])
        self.assertIsNone(env["recorded_output"])
        self.assertEqual(env["execution"], {})


class TestEnvelopeBuildAndSave(unittest.TestCase):
    def _full_trace(self):
        trace = TraceContext(enabled=True, request_id="req-1")
        trace.record_input("audio", audio_bytes=b"abcd", audio_format={"rate": 16000})
        trace.record_request({"source": "audio", "room": "Кухня"})
        trace.record_canonical(16000, "pcm16", 1)
        trace.record_config({"vad": {"threshold": 0.01}})
        trace.record_output(_Result())
        with trace_scope(trace):
            trace_event("timer_set", {"duration_s": 300}, handler="timer")
        return trace

    def test_envelope_shape(self):
        env = self._full_trace().build_envelope()
        self.assertEqual(env["trace_version"], 1)
        self.assertEqual(env["request_id"], "req-1")
        self.assertIn("saved_at", env)
        self.assertEqual(env["replay"]["canonical"], {"rate": 16000, "format": "pcm16", "channels": 1})
        self.assertEqual(len(env["handler_events"]), 1)
        self.assertNotIn("vad_frames", env)  # absent when empty (utterance/raw)

    def test_vad_frames_present_when_filled(self):
        trace = TraceContext(enabled=True)
        trace.add_vad_frame(t_ms=0, is_voice=False, energy=0.002, threshold=0.01)
        self.assertEqual(len(trace.build_envelope()["vad_frames"]), 1)

    def test_to_file_roundtrips(self):
        import tempfile
        from pathlib import Path
        trace = self._full_trace()
        with tempfile.TemporaryDirectory() as d:
            out = trace.to_file(Path(d) / "nested" / "trace.json")
            self.assertTrue(out.exists())
            loaded = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(loaded["request_id"], "req-1")
        self.assertEqual(base64.b64decode(loaded["replay"]["input"]["audio_base64"]), b"abcd")
        self.assertEqual(loaded["recorded_output"]["text"], "готово")


if __name__ == "__main__":
    unittest.main()
