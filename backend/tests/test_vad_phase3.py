"""
VAD ↔ workflow integration contracts (TEST-7 rewrite).

These assert the CURRENT public/port behaviour of `UnifiedVoiceAssistantWorkflow`'s VAD wiring,
not the pre-refactor internals the old Phase-3 script poked at. The contract today (QUAL-46 / ARCH-18):

- VAD is configured from an injected `config` COMPONENT (`workflow.get_component('config').vad`),
  not from a `_vad_processing_enabled` flag (gone) or `UnifiedVoiceAssistantWorkflowConfig.enable_vad_processing`.
- VAD is mandatory ONLY when microphone input is enabled (ARCH-24 T4): the mic streams raw chunks that
  must be segmented. With no microphone (web/ESP32 deliver bounded utterances), VAD is optional and
  `initialize()` leaves `audio_processor_interface = None`.
- `initialize()` fails loud when the config component is absent ("Configuration not available") or when
  VAD is disabled **while a microphone is enabled** ("VAD is required when microphone input is enabled").
- `AudioProcessorInterface.get_metrics()` returns a plain dict (no `.average_processing_time_ms`
  attribute access — metrics are dict-keyed now).
"""

import asyncio
from types import SimpleNamespace
from typing import AsyncIterator, List

import pytest

from locveil_voice.workflows.voice_assistant import UnifiedVoiceAssistantWorkflow
from locveil_voice.workflows.audio_processor import AudioProcessorInterface, VoiceSegment
from locveil_voice.workflows.base import RequestContext
from locveil_voice.config.models import VADConfig, UnifiedVoiceAssistantWorkflowConfig
from locveil_voice.config.manager import ConfigValidationError
from locveil_voice.intents.models import AudioData, IntentResult
from locveil_voice.intents.context_models import UnifiedConversationContext
from tests.test_vad_basic import generate_test_audio_data


# --------------------------------------------------------------------------- helpers


class _MockASR:
    """Minimal ASR component: returns a fixed transcription for any segment."""
    async def process_audio(self, audio_data):
        await asyncio.sleep(0)
        return "test recognition result"

    def reset_provider_state(self):
        pass


class _MockContextManager:
    """Context manager honouring the current port: get_context_with_request_info(session_id, ctx)."""
    async def get_context_with_request_info(self, session_id, request_context):
        return UnifiedConversationContext(session_id=session_id, user_id="test_user")


class _MockIntentOrchestrator:
    async def execute(self, intent, conversation_context, trace_context=None):
        return IntentResult(text="ok", confidence=0.9)


def _config_component(*, vad_enabled: bool = True, mic_enabled: bool = False) -> SimpleNamespace:
    """A stand-in for the injected `config` component the workflow reads VAD + system from."""
    return SimpleNamespace(
        vad=VADConfig(enabled=vad_enabled),
        system=SimpleNamespace(microphone_enabled=mic_enabled),
    )


def _workflow(*, with_config: bool = True, vad_enabled: bool = True,
              mic_enabled: bool = False) -> UnifiedVoiceAssistantWorkflow:
    """Build a workflow with the required components wired (and optionally the config component)."""
    workflow = UnifiedVoiceAssistantWorkflow()
    components = {
        "asr": _MockASR(),
        "nlu": _MockASR(),  # presence-only; required component
        "intent_orchestrator": _MockIntentOrchestrator(),
        "context_manager": _MockContextManager(),
        "tts": None,
        "audio": None,
        "text_processor": None,
    }
    if with_config:
        components["config"] = _config_component(vad_enabled=vad_enabled, mic_enabled=mic_enabled)
    workflow.components = components
    return workflow


def _stage_config() -> UnifiedVoiceAssistantWorkflowConfig:
    return UnifiedVoiceAssistantWorkflowConfig()


async def _audio_stream(sequence: List[tuple], chunk_ms: float = 50) -> AsyncIterator:
    for audio_type, count in sequence:
        for _ in range(count):
            yield generate_test_audio_data(chunk_ms, audio_type=audio_type)
            await asyncio.sleep(0)


# --------------------------------------------------------------------------- initialize() contract


async def test_initialize_wires_vad_from_injected_config():
    """With a config component carrying enabled VAD, initialize builds the audio processor interface."""
    workflow = _workflow(with_config=True, vad_enabled=True)

    await workflow.initialize(_stage_config())

    assert workflow.initialized is True
    assert workflow.audio_processor_interface is not None
    # The interface wraps the VAD config it was built from (default provider = "energy").
    assert workflow.audio_processor_interface.processor.config.default_provider == "energy"
    # No negotiator component injected → stays None (the no-op canonical path).
    assert workflow.audio_negotiator is None


async def test_initialize_raises_when_config_component_missing():
    """No injected config component → fail loud with the 'Configuration not available' contract."""
    workflow = _workflow(with_config=False)

    with pytest.raises(ConfigValidationError) as exc:
        await workflow.initialize(_stage_config())

    assert "Configuration not available" in str(exc.value)
    assert workflow.audio_processor_interface is None


async def test_initialize_raises_when_vad_disabled_and_mic_enabled():
    """VAD disabled WITH microphone input → fail loud (ARCH-24 T4): the mic streams raw chunks that
    must be segmented, so VAD is mandatory whenever a microphone is enabled."""
    workflow = _workflow(with_config=True, vad_enabled=False, mic_enabled=True)

    with pytest.raises(ConfigValidationError) as exc:
        await workflow.initialize(_stage_config())

    assert "VAD" in str(exc.value)
    assert "microphone" in str(exc.value).lower()


async def test_initialize_ok_when_vad_disabled_and_no_microphone():
    """ARCH-24 T4 satellite-server: no microphone (web/ESP32 deliver bounded utterances) → VAD is
    optional; initialize must NOT raise, and the audio processor interface stays None."""
    workflow = _workflow(with_config=True, vad_enabled=False, mic_enabled=False)

    await workflow.initialize(_stage_config())

    assert workflow.audio_processor_interface is None


async def test_initialize_requires_no_workflow_config():
    """initialize() with no stage config at all is a hard error (stages cannot be left undefined)."""
    workflow = _workflow(with_config=True)

    with pytest.raises(ValueError):
        await workflow.initialize(None)


# --------------------------------------------------------------------------- metrics contract


def test_get_metrics_returns_dict_not_object():
    """AudioProcessorInterface.get_metrics() is dict-keyed (the Phase-3 attribute drift)."""
    interface = AudioProcessorInterface(VADConfig(enabled=True))

    metrics = interface.get_metrics()

    assert isinstance(metrics, dict)
    # Keys the workflow's logging path reads via .get(...) must exist.
    for key in ("total_chunks_processed", "voice_segments_detected",
                "average_processing_time_ms", "timeout_events", "buffer_overflow_count"):
        assert key in metrics, key
    # These are no longer attributes — accessing them as such must fail.
    assert not hasattr(metrics, "average_processing_time_ms")


# --------------------------------------------------------------------------- streaming behaviour


class _FakeInterface:
    """Lightweight stand-in for AudioProcessorInterface that yields one voice segment.

    Lets us assert the WORKFLOW's routing contract (asr_result → _process_pipeline → yield) without
    depending on energy-VAD tuning, which is the segmenter's concern (covered by the Phase-2 tests).
    """
    def __init__(self):
        self.processor = SimpleNamespace(
            config=SimpleNamespace(default_provider="energy", max_segment_duration_s=10))

    def _segment(self) -> VoiceSegment:
        audio = AudioData(data=b"\x00\x00" * 160, sample_rate=16000, channels=1, timestamp=0.0)
        return VoiceSegment(audio_chunks=[audio], start_timestamp=0.0, end_timestamp=0.1,
                            total_duration_ms=100.0, chunk_count=1, combined_audio=audio)

    async def process_audio_pipeline(self, audio_stream, context, handler):
        # Drain the stream (the workflow may have wrapped it) then emit one segment.
        async for _ in audio_stream:
            pass
        seg = self._segment()
        await handler(seg, context)
        yield seg

    async def process_voice_segment_for_mode(self, voice_segment, context, asr, vt, wake_detected):
        return {"type": "asr_result", "result": "test recognition result", "mode": "direct_asr"}

    def get_metrics(self):
        return {"total_chunks_processed": 3, "voice_segments_detected": 1,
                "silence_chunks_skipped": 0, "average_processing_time_ms": 0.0,
                "buffer_overflow_count": 0, "timeout_events": 0}


async def test_process_audio_stream_routes_asr_result_to_pipeline():
    """Streaming routing contract: an asr_result segment flows through _process_pipeline and yields it.

    Energy-VAD tuning is the segmenter's job (Phase-2 tests); here the interface is stubbed so the
    workflow's own orchestration seam is what gets exercised.
    """
    workflow = _workflow(with_config=True, vad_enabled=True)
    await workflow.initialize(_stage_config())
    workflow.audio_processor_interface = _FakeInterface()

    captured = {}

    async def fake_pipeline(input_data, context, conversation_context, trace_context=None,
                            skip_wake_word=False, skip_asr=False):
        captured["input"] = input_data
        return IntentResult(text=f"processed: {input_data}", confidence=0.9)

    workflow._process_pipeline = fake_pipeline

    context = RequestContext(source="test", skip_wake_word=True, session_id="s1")

    results = []
    async for result in workflow.process_audio_stream(_audio_stream([("speech_like", 2)]), context):
        results.append(result)

    assert len(results) == 1
    assert isinstance(results[0], IntentResult)
    # The ASR transcription from the segment is what fed the pipeline.
    assert captured["input"] == "test recognition result"
    assert results[0].text == "processed: test recognition result"


async def test_process_audio_stream_without_interface_yields_error_result():
    """Off-path: a workflow with no audio processor interface yields a failed IntentResult, not a crash."""
    workflow = _workflow(with_config=True, vad_enabled=True)
    # Mark initialized so process_audio_stream does not re-run initialize(), and force the
    # missing-interface branch.
    workflow.initialized = True
    workflow.context_manager = _MockContextManager()
    workflow.audio_processor_interface = None
    workflow.audio_negotiator = None

    context = RequestContext(source="test", skip_wake_word=True, session_id="s2")

    results = []
    async for result in workflow.process_audio_stream(_audio_stream([("silence", 1)]), context):
        results.append(result)

    assert len(results) == 1
    assert results[0].success is False
    assert results[0].error


# --------------------------------------------------------------------------- config model defaults


def test_workflow_config_defaults_enable_vad_and_stages():
    """UnifiedVoiceAssistantWorkflowConfig defaults: VAD + every pipeline stage on."""
    default = UnifiedVoiceAssistantWorkflowConfig()

    # enable_vad_processing default flipped to True after the VAD-required refactor.
    assert default.enable_vad_processing is True
    assert default.voice_trigger_enabled is True
    assert default.asr_enabled is True
    assert default.nlu_enabled is True
    assert default.intent_execution_enabled is True

    # Explicit overrides are honoured.
    custom = UnifiedVoiceAssistantWorkflowConfig(asr_enabled=False)
    assert custom.asr_enabled is False
