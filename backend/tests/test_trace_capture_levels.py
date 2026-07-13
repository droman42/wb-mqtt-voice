"""
ARCH-19 slice 3 — capture levels (utterance / segmenter+vad_frames / raw) + streaming bits.

Unit-tests the building blocks in isolation (the full streaming pipeline needs VAD/ASR):
- VoiceSegmenter per-segment vad_frame slicing,
- the workflow's raw rolling buffer + per-level segment capture,
- the shared core create/save helpers.
"""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from locveil_voice.config.models import AssetConfig, TraceConfig
from locveil_voice.core.trace_context import (
    TraceContext, make_trace, save_trace, resolve_traces_dir, replay_request,
)
from locveil_voice.utils.audio_data import AudioData
from locveil_voice.workflows.audio_processor import VoiceSegment, VoiceSegmenter
from locveil_voice.workflows.voice_assistant import UnifiedVoiceAssistantWorkflow


def _frame(ts, *, rate=16000, nbytes=320):
    return AudioData(data=b"\x00" * nbytes, timestamp=ts, sample_rate=rate, channels=1)


class TestVoiceSegmentVadFrames(unittest.TestCase):
    def _segmenter(self, collect):
        # Bypass the heavy __init__ (VAD provider discovery); exercise the pure slice logic.
        s = object.__new__(VoiceSegmenter)
        s._collect_vad_frames = collect
        s._vad_verdicts = []
        return s

    def test_default_segment_has_empty_vad_frames(self):
        seg = VoiceSegment(audio_chunks=[], start_timestamp=0, end_timestamp=0,
                           total_duration_ms=0, chunk_count=0)
        self.assertEqual(seg.vad_frames, [])

    def test_slices_to_window_and_rebases_t_ms(self):
        s = self._segmenter(collect=True)
        s._vad_verdicts = [
            {"ts": 0.90, "is_voice": False, "energy": 0.001, "threshold": 0.01},  # before window
            {"ts": 1.00, "is_voice": True, "energy": 0.05, "threshold": 0.01},    # window start
            {"ts": 1.20, "is_voice": True, "energy": 0.04, "threshold": 0.01},
            {"ts": 1.50, "is_voice": False, "energy": 0.002, "threshold": 0.01},  # window end
            {"ts": 1.80, "is_voice": True, "energy": 0.06, "threshold": 0.01},    # after window
        ]
        frames = s._collect_segment_vad_frames(1.00, 1.50)
        self.assertEqual([f["t_ms"] for f in frames], [0, 200, 500])
        self.assertEqual(frames[0]["is_voice"], True)
        # the post-window verdict survives for the next segment; window+older are consumed
        self.assertEqual([v["ts"] for v in s._vad_verdicts], [1.80])

    def test_noop_when_not_collecting(self):
        s = self._segmenter(collect=False)
        s._vad_verdicts = [{"ts": 1.0, "is_voice": True, "energy": 0.1, "threshold": 0.01}]
        self.assertEqual(s._collect_segment_vad_frames(0.0, 2.0), [])


class TestRawRollingBuffer(unittest.TestCase):
    def _wf(self, *, capture_raw, max_s=5.0):
        wf = object.__new__(UnifiedVoiceAssistantWorkflow)
        wf._capture_raw = capture_raw
        wf._raw_frame_buffer = []
        wf._raw_buffer_max_s = max_s
        return wf

    def test_buffer_trims_by_duration(self):
        wf = self._wf(capture_raw=True, max_s=1.0)
        # 16kHz mono, 320 bytes = 160 samples = 10ms per frame; 1s bound ≈ 100 frames
        for i in range(300):
            wf._buffer_raw_frame(_frame(ts=i * 0.01, nbytes=320))
        # bounded well under the unbounded 300
        self.assertLessEqual(len(wf._raw_frame_buffer), 110)
        self.assertGreater(len(wf._raw_frame_buffer), 90)

    def test_raw_audio_for_segment_slices_and_consumes(self):
        wf = self._wf(capture_raw=True, max_s=10.0)
        for i in range(10):
            wf._raw_frame_buffer.append(_frame(ts=i * 0.1, rate=44100, nbytes=100))
        seg = VoiceSegment(audio_chunks=[], start_timestamp=0.2, end_timestamp=0.5,
                           total_duration_ms=0, chunk_count=0)
        audio, fmt = wf._raw_audio_for_segment(seg)
        self.assertEqual(len(audio), 4 * 100)          # ts 0.2,0.3,0.4,0.5
        self.assertEqual(fmt["rate"], 44100)
        # frames up to end_ts consumed; later frames remain
        self.assertTrue(all(f.timestamp > 0.5 for f in wf._raw_frame_buffer))

    def test_raw_audio_for_segment_empty_returns_none(self):
        wf = self._wf(capture_raw=True)
        seg = VoiceSegment(audio_chunks=[], start_timestamp=0.0, end_timestamp=1.0,
                           total_duration_ms=0, chunk_count=0)
        self.assertEqual(wf._raw_audio_for_segment(seg), (None, None))


class TestCaptureSegmentInput(unittest.TestCase):
    def _wf(self, *, capture_raw):
        wf = object.__new__(UnifiedVoiceAssistantWorkflow)
        wf._capture_raw = capture_raw
        wf._raw_frame_buffer = []
        wf._raw_buffer_max_s = 10.0
        return wf

    def _segment(self, with_frames):
        combined = AudioData(data=b"\x01\x02" * 50, timestamp=1.0, sample_rate=16000, channels=1)
        seg = VoiceSegment(audio_chunks=[], start_timestamp=1.0, end_timestamp=1.5,
                           total_duration_ms=500, chunk_count=5, combined_audio=combined)
        if with_frames:
            seg.vad_frames = [{"t_ms": 0, "is_voice": True, "energy": 0.05, "threshold": 0.01}]
        return seg

    def test_utterance_level_records_combined_audio_and_canonical(self):
        wf = self._wf(capture_raw=False)
        trace = TraceContext(enabled=True)
        trace.capture_level = "segmenter"
        wf._capture_segment_input(trace, self._segment(with_frames=True))
        env = trace.build_envelope()
        self.assertEqual(env["replay"]["input"]["kind"], "audio")
        self.assertEqual(env["replay"]["canonical"], {"rate": 16000, "format": "pcm16", "channels": 1})
        self.assertEqual(len(env["vad_frames"]), 1)

    def test_raw_level_uses_buffer_then_falls_back(self):
        wf = self._wf(capture_raw=True)
        # raw frame at native 44.1k covering the window
        wf._raw_frame_buffer = [_frame(ts=1.2, rate=44100, nbytes=80)]
        trace = TraceContext(enabled=True)
        trace.capture_level = "raw"
        wf._capture_segment_input(trace, self._segment(with_frames=False))
        fmt = trace.build_envelope()["replay"]["input"]["format"]
        self.assertEqual(fmt["rate"], 44100)  # came from the raw buffer, not the 16k segment


class TestCoreHelpers(unittest.TestCase):
    def test_make_trace_off_when_disabled(self):
        self.assertIsNone(make_trace(None))
        self.assertIsNone(make_trace(TraceConfig(enabled=False)))

    def test_make_trace_carries_level_and_caps(self):
        t = make_trace(TraceConfig(enabled=True, capture_level="raw", max_stages=7))
        self.assertTrue(t.enabled)
        self.assertEqual(t.capture_level, "raw")
        self.assertEqual(t.max_stages, 7)

    def test_resolve_traces_dir_override_and_default(self):
        assets = AssetConfig(assets_root=Path("/tmp/a"))
        self.assertEqual(resolve_traces_dir(TraceConfig(enabled=True), assets), Path("/tmp/a/traces"))
        self.assertEqual(resolve_traces_dir(TraceConfig(enabled=True, traces_dir="/x/y"), assets),
                         Path("/x/y"))

    def test_save_trace_gated_on_config(self):
        with tempfile.TemporaryDirectory() as d:
            assets = AssetConfig(assets_root=Path(d))
            trace = TraceContext(enabled=True, request_id="rq")
            self.assertIsNone(save_trace(trace, TraceConfig(enabled=False), assets))
            self.assertEqual(list(Path(d).glob("**/*.json")), [])
            out = save_trace(trace, TraceConfig(enabled=True), assets)
            self.assertTrue(out.exists())
            self.assertEqual(json.loads(out.read_text())["request_id"], "rq")

    def test_replay_request_scrape(self):
        ctx = SimpleNamespace(source="voice", session_id="s1", wants_audio=True,
                              skip_wake_word=False, skip_asr=False, room_name="Кухня",
                              client_id="kitchen")
        req = replay_request(ctx)
        self.assertEqual(req["room"], "Кухня")
        self.assertEqual(req["client_id"], "kitchen")
        self.assertEqual(req["source"], "voice")


if __name__ == "__main__":
    unittest.main()
