"""TEST-7 Phase D — characterization tests for the unified voice-assistant workflow.

Targets the pure helpers + entry seams of ``irene.workflows.voice_assistant`` that do NOT
require real models / a booted core: the raw-frame rolling buffer, the per-segment trace
capture, conversation-context creation, and the text/audio entry points + the seed/step
trace hooks in ``_process_pipeline``.

Method follows the project new-code recipe (cf. test_trace_replay / test_voice_runner):
- ``object.__new__`` to bypass the heavy ``__init__``; only the attributes a method reads
  are set.
- ports/providers are SimpleNamespace async stubs.
- ``asyncio.run`` per test (hermetic, no shared loop); no global singletons mutated.
The full ASR/VAD run needs models and is left to the smoke harness.
"""

import asyncio
import logging
import unittest
from types import SimpleNamespace

from ..core.trace_context import TraceContext, trace_scope
from ..config.manager import ConfigValidationError
from ..intents.models import AudioData, IntentResult, Intent
from ..workflows.audio_processor import VoiceSegment
from ..workflows.voice_assistant import UnifiedVoiceAssistantWorkflow


def _arun(coro):
    return asyncio.run(coro)


def _frame(data: bytes, *, timestamp: float, sample_rate: int = 16000,
           channels: int = 1) -> AudioData:
    return AudioData(data=data, timestamp=timestamp, sample_rate=sample_rate,
                     channels=channels, format="pcm16")


def _new_workflow() -> UnifiedVoiceAssistantWorkflow:
    """A workflow instance without running the heavy __init__/initialize()."""
    wf = object.__new__(UnifiedVoiceAssistantWorkflow)
    wf.logger = logging.getLogger("test.voice_assistant")
    # Defaults the helpers under test read:
    wf._capture_raw = False
    wf._raw_frame_buffer = []
    wf._raw_buffer_max_s = 10.0
    return wf


# ---------------------------------------------------------------------------
# _buffer_raw_frame — bounded rolling buffer trimmed by total duration
# ---------------------------------------------------------------------------
class TestBufferRawFrame(unittest.TestCase):
    def test_appends_under_bound(self):
        wf = _new_workflow()
        # 16000 Hz * 1 ch * 2 bytes -> 32000 bytes == 1.0 s. Three 0.1 s frames stay.
        f = _frame(b"\x00" * 3200, timestamp=0.0)
        wf._buffer_raw_frame(_frame(b"\x00" * 3200, timestamp=0.0))
        wf._buffer_raw_frame(_frame(b"\x00" * 3200, timestamp=0.1))
        wf._buffer_raw_frame(f)
        self.assertEqual(len(wf._raw_frame_buffer), 3)

    def test_trims_oldest_over_bound(self):
        wf = _new_workflow()
        wf._raw_buffer_max_s = 0.25  # bound below the accumulated total
        # each 3200-byte frame == 0.1 s; five frames == 0.5 s > 0.25 s bound
        for i in range(5):
            wf._buffer_raw_frame(_frame(b"\x00" * 3200, timestamp=i * 0.1))
        # trim keeps at least 1 frame and stays at/under the bound
        total_s = sum(len(f.data) / (f.channels * 2 * f.sample_rate)
                      for f in wf._raw_frame_buffer)
        self.assertGreaterEqual(len(wf._raw_frame_buffer), 1)
        self.assertLessEqual(total_s, 0.25 + 1e-6)
        # newest frame is always retained (oldest are dropped first)
        self.assertEqual(wf._raw_frame_buffer[-1].timestamp, 0.4)

    def test_never_trims_below_one(self):
        wf = _new_workflow()
        wf._raw_buffer_max_s = 0.0  # impossible bound
        wf._buffer_raw_frame(_frame(b"\x00" * 3200, timestamp=0.0))
        wf._buffer_raw_frame(_frame(b"\x00" * 3200, timestamp=0.1))
        self.assertEqual(len(wf._raw_frame_buffer), 1)


# ---------------------------------------------------------------------------
# _raw_audio_for_segment — reconstruct pre-canonical audio from the buffer
# ---------------------------------------------------------------------------
class TestRawAudioForSegment(unittest.TestCase):
    def _segment(self, start, end) -> VoiceSegment:
        return VoiceSegment(audio_chunks=[], start_timestamp=start, end_timestamp=end,
                            total_duration_ms=(end - start) * 1000, chunk_count=0)

    def test_reconstructs_in_window_and_consumes(self):
        wf = _new_workflow()
        wf._raw_frame_buffer = [
            _frame(b"AA", timestamp=0.0),
            _frame(b"BB", timestamp=0.5),
            _frame(b"CC", timestamp=1.0),
            _frame(b"DD", timestamp=2.0),  # after the segment end -> retained
        ]
        audio_bytes, fmt = wf._raw_audio_for_segment(self._segment(0.0, 1.0))
        self.assertEqual(audio_bytes, b"AABBCC")
        self.assertEqual(fmt["rate"], 16000)
        self.assertEqual(fmt["channels"], 1)
        self.assertEqual(fmt["format"], "pcm16")
        # frames up to end_ts consumed; only the later frame remains
        self.assertEqual([f.timestamp for f in wf._raw_frame_buffer], [2.0])

    def test_no_frames_returns_none(self):
        wf = _new_workflow()
        wf._raw_frame_buffer = [_frame(b"ZZ", timestamp=5.0)]
        audio_bytes, fmt = wf._raw_audio_for_segment(self._segment(0.0, 1.0))
        self.assertIsNone(audio_bytes)
        self.assertIsNone(fmt)
        # the out-of-window frame is still dropped if it is <= end_ts; here it is later -> kept
        self.assertEqual([f.timestamp for f in wf._raw_frame_buffer], [5.0])


# ---------------------------------------------------------------------------
# _capture_segment_input — record the segment into a real TraceContext
# ---------------------------------------------------------------------------
class TestCaptureSegmentInput(unittest.TestCase):
    def _segment(self, *, combined, vad_frames=None, start=0.0, end=1.0) -> VoiceSegment:
        return VoiceSegment(audio_chunks=[], start_timestamp=start, end_timestamp=end,
                            total_duration_ms=1000, chunk_count=1,
                            combined_audio=combined, vad_frames=vad_frames or [])

    def test_utterance_level_uses_combined_audio(self):
        wf = _new_workflow()  # _capture_raw=False -> utterance/segmenter path
        trace = TraceContext(enabled=True)
        trace.capture_level = "utterance"
        combined = _frame(b"\x01\x02\x03\x04", timestamp=0.0)
        seg = self._segment(combined=combined,
                            vad_frames=[{"t_ms": 10, "is_voice": True,
                                         "energy": 0.5, "threshold": 0.1}])
        wf._capture_segment_input(trace, seg)
        self.assertEqual(trace._input["kind"], "audio")
        self.assertEqual(trace._input["capture_level"], "utterance")
        self.assertEqual(trace._canonical, {"rate": 16000, "format": "pcm16", "channels": 1})
        self.assertEqual(len(trace.vad_frames), 1)
        self.assertTrue(trace.vad_frames[0]["is_voice"])

    def test_raw_level_prefers_buffer(self):
        wf = _new_workflow()
        wf._capture_raw = True
        wf._raw_frame_buffer = [
            _frame(b"RR", timestamp=0.1),
            _frame(b"SS", timestamp=0.2),
        ]
        trace = TraceContext(enabled=True)
        trace.capture_level = "raw"
        combined = _frame(b"\x09\x09", timestamp=0.0)
        seg = self._segment(combined=combined, start=0.0, end=1.0)
        wf._capture_segment_input(trace, seg)
        # raw bytes from the buffer, NOT the canonical combined audio
        import base64
        self.assertEqual(base64.b64decode(trace._input["audio_base64"]), b"RRSS")
        # canonical contract still recorded from the combined segment
        self.assertEqual(trace._canonical["rate"], 16000)

    def test_raw_level_falls_back_to_segment_when_no_buffer(self):
        wf = _new_workflow()
        wf._capture_raw = True
        wf._raw_frame_buffer = []  # nothing covers the window
        trace = TraceContext(enabled=True)
        trace.capture_level = "raw"
        combined = _frame(b"\xaa\xbb", timestamp=0.0)
        wf._capture_segment_input(trace, self._segment(combined=combined))
        import base64
        self.assertEqual(base64.b64decode(trace._input["audio_base64"]), b"\xaa\xbb")

    def test_no_combined_audio_records_empty(self):
        wf = _new_workflow()
        trace = TraceContext(enabled=True)
        wf._capture_segment_input(trace, self._segment(combined=None))
        import base64
        self.assertEqual(base64.b64decode(trace._input["audio_base64"]), b"")
        # no canonical contract recorded when there is no combined audio
        self.assertIsNone(trace._canonical)


# ---------------------------------------------------------------------------
# _create_conversation_context — delegate to the context manager / fail loud
# ---------------------------------------------------------------------------
class TestCreateConversationContext(unittest.TestCase):
    def test_delegates_to_context_manager(self):
        wf = _new_workflow()
        seen = {}
        sentinel = SimpleNamespace(session_id="s1")

        async def get_ctx(*, session_id, request_context):
            seen["session_id"] = session_id
            seen["request_context"] = request_context
            return sentinel

        wf.context_manager = SimpleNamespace(get_context_with_request_info=get_ctx)
        ctx = SimpleNamespace(session_id="s1")
        out = _arun(wf._create_conversation_context(ctx))
        self.assertIs(out, sentinel)
        self.assertEqual(seen["session_id"], "s1")
        self.assertIs(seen["request_context"], ctx)

    def test_missing_manager_raises(self):
        wf = _new_workflow()
        wf.context_manager = None
        with self.assertRaises(ConfigValidationError):
            _arun(wf._create_conversation_context(SimpleNamespace(session_id="s1")))


# ---------------------------------------------------------------------------
# _process_pipeline — seed/step trace hooks, single history writer, metrics
# ---------------------------------------------------------------------------
def _pipeline_workflow(*, text_processing=False):
    wf = _new_workflow()
    wf._text_processing_enabled = text_processing
    wf.text_processor = None

    async def nlu_process(text, ctx, trace, original_text=None):
        wf._seen_nlu = {"text": text, "original_text": original_text}
        # Text-aware (QUAL-44): a full command recognizes confidently, a bare fragment
        # («на пять минут») falls back low — else the arbitration probe would classify
        # every clarification answer as a fresh command and never combine.
        if "таймер" in text:
            return Intent(name="timer.set", entities={}, confidence=0.9, raw_text=original_text)
        return Intent(name="conversation.general", entities={}, confidence=0.3,
                      raw_text=original_text)

    async def orch_execute(intent, ctx, trace):
        return IntentResult(text="готово", success=True, confidence=0.9)

    wf.nlu = SimpleNamespace(process=nlu_process)
    wf.intent_orchestrator = SimpleNamespace(execute=orch_execute)
    wf.metrics_collector = SimpleNamespace(
        record_intent_recognition=lambda **kw: wf.__dict__.setdefault("_metric", kw))
    return wf


def _conv_ctx(pending=None):
    state = {"turns": [], "pending": pending}

    def take_pending():
        p = state["pending"]
        state["pending"] = None
        return p

    def record_turn(*, user_text, response, intent):
        state["turns"].append((user_text, response, intent))

    return SimpleNamespace(
        session_id="sess-1", take_pending_clarification=take_pending,
        record_turn=record_turn, conversation_history=[], active_actions={},
        handler_contexts={}, state_context={}, _state=state,
    )


class TestProcessPipeline(unittest.TestCase):
    def test_seed_and_step_hooks_fire(self):
        wf = _pipeline_workflow()
        conv = _conv_ctx()
        trace = TraceContext(enabled=True)
        seen_steps = []

        async def hook(stage, data):
            seen_steps.append(stage)

        trace.step_hook = hook

        async def run():
            with trace_scope(trace):
                return await wf._process_pipeline(
                    input_data="поставь таймер", context=SimpleNamespace(),
                    conversation_context=conv, trace_context=trace,
                    skip_wake_word=True, skip_asr=True)

        result = _arun(run())
        self.assertEqual(result.text, "готово")
        # seed context recorded once from the before-snapshot
        self.assertIsNotNone(trace._seed_context)
        self.assertIsNotNone(trace.context_snapshots["before"])
        self.assertIsNotNone(trace.context_snapshots["after"])
        # step hook awaited at every stage boundary
        self.assertEqual(seen_steps, ["text_processing", "nlu", "intent"])
        # SINGLE history writer recorded the literal input
        self.assertEqual(conv._state["turns"], [("поставь таймер", "готово", "timer.set")])
        # metrics recorded
        self.assertEqual(wf._metric["intent_name"], "timer.set")

    def test_pending_clarification_prepends_original(self):
        wf = _pipeline_workflow()
        conv = _conv_ctx(pending={"original_text": "поставь таймер",
                                  "intent_name": "timer.set",
                                  "missing_param": "duration"})

        async def run():
            return await wf._process_pipeline(
                input_data="на пять минут", context=SimpleNamespace(),
                conversation_context=conv, trace_context=None,
                skip_wake_word=True, skip_asr=True)

        _arun(run())
        # NLU saw the combined original + answer as the effective text
        self.assertEqual(wf._seen_nlu["original_text"], "поставь таймер на пять минут")
        # but conversation history records the LITERAL this-turn input
        self.assertEqual(conv._state["turns"][0][0], "на пять минут")

    def test_uninitialised_pipeline_raises(self):
        wf = _new_workflow()
        wf.nlu = None
        wf.intent_orchestrator = None
        wf._text_processing_enabled = False
        wf.text_processor = None
        conv = _conv_ctx()

        async def run():
            return await wf._process_pipeline(
                input_data="hi", context=SimpleNamespace(),
                conversation_context=conv, trace_context=None,
                skip_wake_word=True, skip_asr=True)

        with self.assertRaises(ConfigValidationError):
            _arun(run())

    def test_text_processing_stage_invoked(self):
        wf = _pipeline_workflow(text_processing=True)

        async def tp_process(text, ctx, trace):
            return text.upper()

        wf.text_processor = SimpleNamespace(process=tp_process)
        conv = _conv_ctx()

        async def run():
            return await wf._process_pipeline(
                input_data="hi", context=SimpleNamespace(),
                conversation_context=conv, trace_context=None,
                skip_wake_word=True, skip_asr=True)

        _arun(run())
        # processed (normalized) text reached NLU
        self.assertEqual(wf._seen_nlu["text"], "HI")
        # original literal still went to raw_text/original_text
        self.assertEqual(wf._seen_nlu["original_text"], "hi")


# ---------------------------------------------------------------------------
# process_text_input — text entry point (happy + error path)
# ---------------------------------------------------------------------------
class TestProcessTextInput(unittest.TestCase):
    def _wf(self):
        wf = _pipeline_workflow()
        wf.initialized = True
        sentinel = _conv_ctx()

        async def get_ctx(*, session_id, request_context):
            return sentinel

        wf.context_manager = SimpleNamespace(get_context_with_request_info=get_ctx)
        wf._sentinel_ctx = sentinel
        return wf

    def test_happy_path_no_tts(self):
        wf = self._wf()
        ctx = SimpleNamespace(source="cli", session_id="s", wants_audio=False)
        result = _arun(wf.process_text_input("привет", ctx))
        self.assertTrue(result.success)
        self.assertEqual(result.text, "готово")

    def test_error_path_returns_failure_result(self):
        wf = self._wf()

        # make context creation blow up -> caught, returns a fail IntentResult
        async def boom(*, session_id, request_context):
            raise RuntimeError("ctx exploded")

        wf.context_manager = SimpleNamespace(get_context_with_request_info=boom)
        ctx = SimpleNamespace(source="cli", session_id="s", wants_audio=False)
        result = _arun(wf.process_text_input("привет", ctx))
        self.assertFalse(result.success)
        self.assertEqual(result.confidence, 0.0)
        self.assertIn("ctx exploded", result.error)


# ---------------------------------------------------------------------------
# _process_single_audio_pipeline — the off/no-op audio paths (no models)
# ---------------------------------------------------------------------------
class TestSingleAudioPipelineGuards(unittest.TestCase):
    def _wf(self):
        wf = _new_workflow()
        wf._voice_trigger_enabled = False
        wf._asr_enabled = False
        wf.voice_trigger = None
        wf.asr = None
        return wf

    def test_asr_skipped_for_audio_returns_failure(self):
        wf = self._wf()
        audio = _frame(b"\x00" * 320, timestamp=0.0)
        ctx = SimpleNamespace(skip_wake_word=True, skip_asr=False)

        async def run():
            return await wf._process_single_audio_pipeline(
                audio_data=audio, context=ctx, conversation_context=_conv_ctx(),
                trace_context=None)

        result = _arun(run())
        self.assertFalse(result.success)
        self.assertEqual(result.metadata["reason"], "asr_required_for_audio")


if __name__ == "__main__":
    unittest.main()
