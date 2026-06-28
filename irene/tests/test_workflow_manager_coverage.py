"""
Characterization tests for the WorkflowManager request-routing spine (TEST-7 Phase D).

Covers the public entry points (process_text_input / process_audio_input /
process_audio_stream), the save-every-request trace helpers
(_maybe_create_trace / _save_trace_if_enabled / _traces_dir / _replay_request),
and the pipeline-event publisher. Heavy construction is bypassed with
object.__new__ + SimpleNamespace stubs; the active workflow is a hand-rolled stub
so no real models / discovery are touched. All async is driven by asyncio.run so
no event loop leaks between tests, and trace files land in TemporaryDirectory so
no global state is mutated.
"""

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ..config.models import TraceConfig
from ..core.workflow_manager import WorkflowManager, WorkflowMode
from ..core.event_bus import EventType
from ..intents.models import IntentResult
from ..utils.audio_data import AudioData


def _arun(coro):
    return asyncio.run(coro)


def _config(*, trace_enabled=False, traces_dir=None, assets_traces_root=None):
    """A duck-typed config carrying only the [trace] + [assets] surface the helpers read."""
    return SimpleNamespace(
        trace=TraceConfig(enabled=trace_enabled, traces_dir=traces_dir),
        assets=SimpleNamespace(
            traces_root=Path(assets_traces_root) if assets_traces_root else Path("/tmp/irene-traces-unused")
        ),
    )


class _WorkflowStub:
    """Minimal active-workflow stand-in implementing the concrete entry points."""

    name = "unified_voice_assistant"

    def __init__(self, result=None, stream_results=None, raise_exc=None):
        self._result = result or IntentResult(text="готово", success=True)
        self._stream_results = stream_results or []
        self._raise_exc = raise_exc
        self.calls = []

    async def process_text_input(self, text, context, trace_context):
        self.calls.append(("text", text, context, trace_context))
        if self._raise_exc:
            raise self._raise_exc
        return self._result

    async def process_audio_input(self, audio_data, context, trace_context):
        self.calls.append(("audio", audio_data, context, trace_context))
        if self._raise_exc:
            raise self._raise_exc
        return self._result

    async def process_audio_stream(self, audio_stream, context):
        self.calls.append(("stream", audio_stream, context))
        for r in self._stream_results:
            yield r


class _Bus:
    def __init__(self, fail=False):
        self.events = []
        self._fail = fail

    async def publish(self, event):
        if self._fail:
            raise RuntimeError("bus down")
        self.events.append(event)


def _manager(*, active_workflow=None, config=None, event_bus=None):
    m = object.__new__(WorkflowManager)
    m.component_manager = SimpleNamespace()
    m.config = config or _config()
    m.event_bus = event_bus
    m.workflows = {}
    m.workflow_states = {}
    m.active_workflow = active_workflow
    m.active_mode = WorkflowMode.UNIFIED if active_workflow else None
    return m


# ---------------------------------------------------------------------------
# trace helpers
# ---------------------------------------------------------------------------
class TestTraceHelpers(unittest.TestCase):
    def test_maybe_create_trace_passthrough(self):
        m = _manager(config=_config(trace_enabled=True))
        sentinel = object()
        # An explicitly-passed trace is honoured as-is (the /trace endpoint case).
        self.assertIs(m._maybe_create_trace(sentinel), sentinel)

    def test_maybe_create_trace_mints_when_enabled(self):
        m = _manager(config=_config(trace_enabled=True))
        trace = m._maybe_create_trace(None)
        self.assertIsNotNone(trace)
        self.assertTrue(trace.enabled)

    def test_maybe_create_trace_none_when_disabled(self):
        m = _manager(config=_config(trace_enabled=False))
        self.assertIsNone(m._maybe_create_trace(None))

    def test_traces_dir_override(self):
        with tempfile.TemporaryDirectory() as d:
            m = _manager(config=_config(traces_dir=d))
            self.assertEqual(m._traces_dir(), Path(d))

    def test_traces_dir_defaults_to_assets_root(self):
        with tempfile.TemporaryDirectory() as d:
            m = _manager(config=_config(assets_traces_root=d))
            self.assertEqual(m._traces_dir(), Path(d))

    def test_replay_request_scrapes_context(self):
        ctx = SimpleNamespace(source="cli", session_id="s1", wants_audio=True,
                              skip_wake_word=True, skip_asr=False,
                              room_name="Кухня", client_id="kitchen")
        env = WorkflowManager._replay_request(ctx)
        self.assertEqual(env["source"], "cli")
        self.assertEqual(env["session_id"], "s1")
        self.assertEqual(env["room"], "Кухня")
        self.assertEqual(env["client_id"], "kitchen")
        self.assertTrue(env["wants_audio"])

    def test_save_trace_if_enabled_writes_file(self):
        with tempfile.TemporaryDirectory() as d:
            m = _manager(config=_config(trace_enabled=True, traces_dir=d))
            trace = m._maybe_create_trace(None)
            trace.record_input("text", text="привет")
            m._save_trace_if_enabled(trace)
            files = list(Path(d).glob("*.json"))
            self.assertEqual(len(files), 1)
            doc = json.loads(files[0].read_text(encoding="utf-8"))
            self.assertEqual(doc["request_id"], trace.request_id)

    def test_save_trace_if_enabled_noop_when_disabled(self):
        with tempfile.TemporaryDirectory() as d:
            m = _manager(config=_config(trace_enabled=False, traces_dir=d))
            m._save_trace_if_enabled(None)
            self.assertEqual(list(Path(d).glob("*.json")), [])


# ---------------------------------------------------------------------------
# _publish_pipeline_event
# ---------------------------------------------------------------------------
class TestPublishEvent(unittest.TestCase):
    def test_noop_without_bus(self):
        m = _manager()  # event_bus None
        ctx = SimpleNamespace(session_id="s", client_id=None, room_name=None, source="cli")
        # Should simply return without raising.
        _arun(m._publish_pipeline_event(EventType.INPUT_RECEIVED, ctx, {"x": 1}))

    def test_publishes_event_with_origin(self):
        bus = _Bus()
        m = _manager(event_bus=bus)
        ctx = SimpleNamespace(session_id="s", client_id="c", room_name="r", source="cli")
        _arun(m._publish_pipeline_event(EventType.RESULT_PRODUCED, ctx, {"text": "ok"}))
        self.assertEqual(len(bus.events), 1)
        ev = bus.events[0]
        self.assertEqual(ev.type, EventType.RESULT_PRODUCED)
        self.assertEqual(ev.session_id, "s")
        self.assertEqual(ev.payload, {"text": "ok"})

    def test_publish_swallows_bus_error(self):
        bus = _Bus(fail=True)
        m = _manager(event_bus=bus)
        ctx = SimpleNamespace(session_id="s", client_id=None, room_name=None, source="cli")
        # A failing bus must not propagate out of the publisher.
        _arun(m._publish_pipeline_event(EventType.INPUT_RECEIVED, ctx, {}))


# ---------------------------------------------------------------------------
# process_text_input
# ---------------------------------------------------------------------------
class TestProcessTextInput(unittest.TestCase):
    def test_routes_to_active_workflow_no_trace(self):
        wf = _WorkflowStub(result=IntentResult(text="ответ", success=True,
                                               metadata={"intent_name": "timer.set"}))
        bus = _Bus()
        m = _manager(active_workflow=wf, event_bus=bus, config=_config(trace_enabled=False))
        result = _arun(m.process_text_input("привет", session_id="sess1"))
        self.assertEqual(result.text, "ответ")
        # Workflow was invoked with the text and a None trace (tracing off).
        kind, text, ctx, trace = wf.calls[0]
        self.assertEqual(kind, "text")
        self.assertEqual(text, "привет")
        self.assertIsNone(trace)
        # Two pipeline events: INPUT_RECEIVED then RESULT_PRODUCED.
        self.assertEqual([e.type for e in bus.events],
                         [EventType.INPUT_RECEIVED, EventType.RESULT_PRODUCED])

    def test_source_taken_from_client_context(self):
        wf = _WorkflowStub()
        m = _manager(active_workflow=wf, config=_config())
        _arun(m.process_text_input("hi", client_context={"source": "web", "client_id": "kx"}))
        _, _, ctx, _ = wf.calls[0]
        self.assertEqual(ctx.source, "web")
        self.assertEqual(ctx.client_id, "kx")

    def test_saves_trace_when_enabled(self):
        with tempfile.TemporaryDirectory() as d:
            wf = _WorkflowStub(result=IntentResult(text="готово", success=True))
            m = _manager(active_workflow=wf,
                         config=_config(trace_enabled=True, traces_dir=d))
            result = _arun(m.process_text_input("команда", session_id="s2"))
            self.assertEqual(result.text, "готово")
            # A faithful trace was minted, bound and persisted for this request.
            _, _, _, trace = wf.calls[0]
            self.assertIsNotNone(trace)
            self.assertTrue(trace.enabled)
            files = list(Path(d).glob("*.json"))
            self.assertEqual(len(files), 1)
            doc = json.loads(files[0].read_text(encoding="utf-8"))
            self.assertEqual(doc["replay"]["input"]["kind"], "text")
            self.assertEqual(doc["recorded_output"]["text"], "готово")

    def test_stamps_request_id_on_result_when_tracing(self):
        # D-6 (TEST-13): the trace request_id is surfaced on result.metadata so the /ws/audio
        # response metadata can correlate a request → its saved <request_id>.json (exact match).
        with tempfile.TemporaryDirectory() as d:
            wf = _WorkflowStub(result=IntentResult(text="готово", success=True))
            m = _manager(active_workflow=wf, config=_config(trace_enabled=True, traces_dir=d))
            result = _arun(m.process_text_input("команда", session_id="s3"))
            rid = result.metadata.get("request_id")
            self.assertIsNotNone(rid)
            saved = list(Path(d).glob("*.json"))[0]
            self.assertEqual(saved.stem, rid)  # the stamp equals the trace filename
            self.assertEqual(json.loads(saved.read_text(encoding="utf-8"))["request_id"], rid)

    def test_no_request_id_stamped_when_tracing_off(self):
        wf = _WorkflowStub(result=IntentResult(text="ok", success=True))
        m = _manager(active_workflow=wf, config=_config(trace_enabled=False))
        result = _arun(m.process_text_input("cmd", session_id="s4"))
        self.assertNotIn("request_id", result.metadata or {})

    def test_raises_when_no_workflow_available(self):
        m = _manager(active_workflow=None, config=_config())

        async def _noop(name):
            return False  # on-demand creation leaves workflows empty

        m.create_workflow_on_demand = _noop
        with self.assertRaises(RuntimeError):
            _arun(m.process_text_input("hi"))


# ---------------------------------------------------------------------------
# process_audio_input
# ---------------------------------------------------------------------------
class TestProcessAudioInput(unittest.TestCase):
    def _audio(self):
        return AudioData(data=b"\x00\x01" * 8, timestamp=0.0, sample_rate=16000, channels=1)

    def test_routes_audiodata_to_workflow(self):
        wf = _WorkflowStub(result=IntentResult(text="распознано", success=True))
        bus = _Bus()
        m = _manager(active_workflow=wf, event_bus=bus, config=_config())
        result = _arun(m.process_audio_input(self._audio(), session_id="a1"))
        self.assertEqual(result.text, "распознано")
        self.assertEqual(wf.calls[0][0], "audio")
        self.assertEqual([e.type for e in bus.events],
                         [EventType.INPUT_RECEIVED, EventType.RESULT_PRODUCED])

    def test_raw_bytes_returns_error_result(self):
        wf = _WorkflowStub()
        m = _manager(active_workflow=wf, config=_config())
        result = _arun(m.process_audio_input(b"rawbytes"))
        self.assertFalse(result.success)
        self.assertIn("Audio processing failed", result.text)
        self.assertEqual(result.metadata["source"], "workflow_manager_audio")
        # The workflow was never invoked for invalid input.
        self.assertEqual(wf.calls, [])

    def test_wrong_type_returns_error_result(self):
        wf = _WorkflowStub()
        m = _manager(active_workflow=wf, config=_config())
        result = _arun(m.process_audio_input(12345))  # neither bytes nor AudioData
        self.assertFalse(result.success)
        self.assertIn("audio_data must be", result.error)

    def test_saves_trace_on_audio_happy_path(self):
        with tempfile.TemporaryDirectory() as d:
            wf = _WorkflowStub(result=IntentResult(text="ok", success=True))
            m = _manager(active_workflow=wf,
                         config=_config(trace_enabled=True, traces_dir=d))
            _arun(m.process_audio_input(self._audio(), session_id="a2"))
            files = list(Path(d).glob("*.json"))
            self.assertEqual(len(files), 1)
            doc = json.loads(files[0].read_text(encoding="utf-8"))
            self.assertEqual(doc["replay"]["input"]["kind"], "audio")

    def test_error_path_records_stage_and_saves_trace(self):
        with tempfile.TemporaryDirectory() as d:
            # Workflow blows up mid-processing AFTER a trace is minted → error stage saved.
            wf = _WorkflowStub(raise_exc=RuntimeError("asr boom"))
            m = _manager(active_workflow=wf,
                         config=_config(trace_enabled=True, traces_dir=d))
            result = _arun(m.process_audio_input(self._audio(), session_id="a3"))
            self.assertFalse(result.success)
            self.assertIn("asr boom", result.text)
            files = list(Path(d).glob("*.json"))
            self.assertEqual(len(files), 1)
            doc = json.loads(files[0].read_text(encoding="utf-8"))
            stage_names = [s["stage"] for s in doc["execution"]["pipeline_stages"]]
            self.assertIn("workflow_manager_audio_error", stage_names)


# ---------------------------------------------------------------------------
# process_audio_stream
# ---------------------------------------------------------------------------
class TestProcessAudioStream(unittest.TestCase):
    def test_yields_workflow_results(self):
        results = [IntentResult(text="один", success=True),
                   IntentResult(text="два", success=True)]
        wf = _WorkflowStub(stream_results=results)
        m = _manager(active_workflow=wf, config=_config())

        async def _stream():
            if False:
                yield None  # make this an async generator

        async def _collect():
            return [r async for r in m.process_audio_stream(_stream(), session_id="st1",
                                                            skip_wake_word=True)]

        got = _arun(_collect())
        self.assertEqual([r.text for r in got], ["один", "два"])
        # source reflects skip_wake_word=True → "audio_stream"
        _, _, ctx = wf.calls[0]
        self.assertEqual(ctx.source, "audio_stream")
        self.assertTrue(ctx.skip_wake_word)

    def test_voice_source_when_wake_word_kept(self):
        wf = _WorkflowStub(stream_results=[])
        m = _manager(active_workflow=wf, config=_config())

        async def _stream():
            if False:
                yield None

        async def _collect():
            return [r async for r in m.process_audio_stream(_stream(), skip_wake_word=False)]

        self.assertEqual(_arun(_collect()), [])
        _, _, ctx = wf.calls[0]
        self.assertEqual(ctx.source, "voice")
        self.assertFalse(ctx.skip_wake_word)


if __name__ == "__main__":
    unittest.main()
