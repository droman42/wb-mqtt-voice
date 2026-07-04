"""
Phase 2 VAD tests — VoiceSegmenter state machine + AudioProcessorInterface.

TEST-7 rewrite: the VAD config was nested (ARCH-18 — the per-engine energy knobs moved under
`[vad.providers.energy]`) and the processing metrics are now plain dicts from the unified
MetricsCollector (not a ProcessingMetrics object). These tests assert the *port/public* contract:
the VoiceSegmenter state machine, the dict-shaped metrics, the timeout/overflow protection counters,
and the mode-specific (wake-word / direct-ASR) handoff — including the off / no-component paths.
"""

import asyncio
import time
from typing import List, AsyncIterator

import numpy as np
import pytest
from pydantic import ValidationError

from irene.workflows.audio_processor import (
    VoiceActivityState, VoiceSegment,
    VoiceSegmenter, AudioProcessorInterface,
)
from irene.config.models import VADConfig
from irene.intents.models import AudioData
from irene.core.metrics import get_metrics_collector

# Reuse the synthetic-audio generator from the Phase 1 tests.
from irene.tests.test_vad_basic import generate_test_audio_data


# --------------------------------------------------------------------------------------
# Helpers / mocks
# --------------------------------------------------------------------------------------

def make_vad_config(**energy_overrides) -> VADConfig:
    """Build a VADConfig with the energy engine knobs in their post-ARCH-18 home.

    The energy-engine fields (energy_threshold, voice_frames_required, ...) live under
    `[vad.providers.energy]` now — the component-level VADConfig only carries segmentation
    concerns. Component-level overrides can still be passed via the dunder-free kwargs by
    pre-extracting them; here we keep it simple and only nest energy knobs.
    """
    return VADConfig(
        enabled=True,
        default_provider="energy",
        providers={"energy": {"energy_threshold": 0.01, **energy_overrides}},
    )


class MockRequestContext:
    def __init__(self, skip_wake_word: bool = False):
        self.skip_wake_word = skip_wake_word
        self.source = "test"
        self.session_id = "test_session"


class MockASRComponent:
    async def process_audio(self, audio_data: AudioData):
        await asyncio.sleep(0.001)
        return "test recognition result"


class MockVoiceTriggerComponent:
    def __init__(self, detection_rate: float = 1.0):
        self.detection_rate = detection_rate

    async def process_audio(self, audio_data: AudioData):
        await asyncio.sleep(0.001)
        detected = np.random.random() < self.detection_rate
        return {
            'detected': detected,
            'confidence': 0.8 if detected else 0.1,
            'wake_word': 'irene' if detected else None,
        }


async def generate_test_audio_stream(sequence: List[tuple],
                                      chunk_duration_ms: float = 50) -> AsyncIterator[AudioData]:
    """Yield AudioData chunks per a [(audio_type, count), ...] description."""
    for audio_type, count in sequence:
        for _ in range(count):
            yield generate_test_audio_data(chunk_duration_ms, audio_type=audio_type)
            await asyncio.sleep(0.001)


def _make_voice_segment() -> VoiceSegment:
    chunk = generate_test_audio_data(100, audio_type="speech_like")
    return VoiceSegment(
        audio_chunks=[chunk],
        start_timestamp=time.time(),
        end_timestamp=time.time() + 0.1,
        total_duration_ms=100,
        chunk_count=1,
        combined_audio=chunk,
    )


# Keys the unified MetricsCollector exposes for VAD (the dict contract that replaced
# the old ProcessingMetrics object).
_VAD_METRIC_KEYS = {
    "total_chunks_processed",
    "voice_segments_detected",
    "silence_chunks_skipped",
    "average_processing_time_ms",
    "total_processing_time_ms",
    "buffer_overflow_count",
    "timeout_events",
}


# --------------------------------------------------------------------------------------
# Config contract (ARCH-18 nesting)
# --------------------------------------------------------------------------------------

def test_vad_config_nests_engine_knobs_under_providers():
    """The energy-engine knobs live under [vad.providers.energy], not flat on VADConfig."""
    config = make_vad_config(energy_threshold=0.02, voice_frames_required=3)

    # Component-level segmentation fields remain on the model.
    assert config.enabled is True
    assert config.default_provider == "energy"
    assert config.max_segment_duration_s == 10  # default

    # The old flat engine fields are gone from the model surface.
    assert not hasattr(config, "energy_threshold")
    assert not hasattr(config, "sensitivity")
    assert not hasattr(config, "voice_frames_required")

    # ...and live under the provider block instead.
    assert config.providers["energy"]["energy_threshold"] == 0.02
    assert config.providers["energy"]["voice_frames_required"] == 3


def test_vad_config_validation_bounds():
    """Component-level segmentation fields are still bounds-validated."""
    # max_segment_duration_s: ge=1, le=60
    with pytest.raises(ValidationError):
        VADConfig(max_segment_duration_s=0)
    with pytest.raises(ValidationError):
        VADConfig(max_segment_duration_s=61)

    # asr_target_rms: ge=0.01, le=0.3
    with pytest.raises(ValidationError):
        VADConfig(asr_target_rms=0.5)

    ok = VADConfig(max_segment_duration_s=15, asr_target_rms=0.2)
    assert ok.max_segment_duration_s == 15
    assert ok.asr_target_rms == 0.2


# --------------------------------------------------------------------------------------
# VoiceSegmenter state machine + dict metrics
# --------------------------------------------------------------------------------------

def test_segmenter_initial_state_and_metrics_shape():
    """A fresh segmenter is in SILENCE and exposes dict-shaped metrics (not an object)."""
    processor = VoiceSegmenter(make_vad_config())

    assert isinstance(processor, VoiceSegmenter)
    assert processor.vad_state == VoiceActivityState.SILENCE

    metrics = processor.get_processing_metrics()
    assert isinstance(metrics, dict)
    assert _VAD_METRIC_KEYS.issubset(metrics.keys())


async def test_segmenter_detects_voice_segment():
    """silence → speech → silence yields a complete VoiceSegment and bumps dict metrics."""
    processor = VoiceSegmenter(make_vad_config())

    before = processor.get_processing_metrics()["total_chunks_processed"]

    test_sequence = [("silence", 3), ("speech_like", 8), ("silence", 8)]
    voice_segments = []
    chunk_count = 0
    async for chunk in generate_test_audio_stream(test_sequence):
        chunk_count += 1
        segment = await processor.process_audio_chunk(chunk)
        if segment:
            voice_segments.append(segment)

    assert len(voice_segments) >= 1
    seg = voice_segments[0]
    assert seg.chunk_count >= 1
    assert seg.total_duration_ms > 0
    assert seg.combined_audio is not None

    # Metrics are dicts: total processed advanced by exactly the chunks we fed.
    after = processor.get_processing_metrics()
    assert after["total_chunks_processed"] - before == chunk_count


async def test_voice_segment_timeout_records_dict_counter():
    """Long continuous speech forces completion and increments timeout_events (dict access)."""
    # High silence_frames_required so the (amplitude-modulated) speech doesn't end the segment
    # naturally — the 1s wall-clock timeout is what must force completion.
    config = make_vad_config(voice_frames_required=1, silence_frames_required=50)
    config.max_segment_duration_s = 1  # short timeout
    processor = VoiceSegmenter(config)

    before = processor.get_processing_metrics()["timeout_events"]

    async for chunk in generate_test_audio_stream([("speech_like", 50)], chunk_duration_ms=50):
        await processor.process_audio_chunk(chunk)
        await asyncio.sleep(0.05)  # real-time pacing so the 1s timeout actually elapses

    after = processor.get_processing_metrics()["timeout_events"]
    assert after - before > 0


async def test_buffer_overflow_records_dict_counter():
    """Speech exceeding buffer_size_frames forces completion and bumps buffer_overflow_count."""
    # High silence_frames_required so the segment doesn't end naturally; the small buffer is what
    # must force completion. Long timeout isolates the overflow path from the timeout path.
    config = make_vad_config(voice_frames_required=1, silence_frames_required=20)
    config.buffer_size_frames = 10
    config.max_segment_duration_s = 30
    processor = VoiceSegmenter(config)

    before = processor.get_processing_metrics()["buffer_overflow_count"]

    async for chunk in generate_test_audio_stream([("speech_like", 40)]):
        await processor.process_audio_chunk(chunk)

    after = processor.get_processing_metrics()["buffer_overflow_count"]
    assert after - before > 0


# --------------------------------------------------------------------------------------
# AudioProcessorInterface — mode-specific processing + off paths
# --------------------------------------------------------------------------------------

async def test_mode_b_direct_asr():
    """skip_wake_word=True → direct ASR; result carries the asr_result/direct_asr contract."""
    interface = AudioProcessorInterface(make_vad_config())
    result = await interface.process_voice_segment_for_mode(
        _make_voice_segment(), MockRequestContext(skip_wake_word=True),
        asr_component=MockASRComponent(), voice_trigger_component=MockVoiceTriggerComponent(),
    )
    assert result['type'] == 'asr_result'
    assert result['mode'] == 'direct_asr'


async def test_mode_a_wake_word_then_command():
    """skip_wake_word=False → wake-word detection first, then ASR once detected."""
    interface = AudioProcessorInterface(make_vad_config())
    segment = _make_voice_segment()
    ctx = MockRequestContext(skip_wake_word=False)
    asr = MockASRComponent()
    vt = MockVoiceTriggerComponent(detection_rate=1.0)

    detect = await interface.process_voice_segment_for_mode(
        segment, ctx, asr, vt, wake_word_detected=False)
    assert detect['type'] == 'wake_word_result'
    assert detect['mode'] == 'wake_word_detection'

    command = await interface.process_voice_segment_for_mode(
        segment, ctx, asr, vt, wake_word_detected=True)
    assert command['type'] == 'asr_result'
    assert command['mode'] == 'command_after_wake'


async def test_mode_b_missing_asr_component_is_error():
    """Off path: Mode B with no ASR component returns a structured error, not a crash."""
    interface = AudioProcessorInterface(make_vad_config())
    result = await interface.process_voice_segment_for_mode(
        _make_voice_segment(), MockRequestContext(skip_wake_word=True),
        asr_component=None, voice_trigger_component=None,
    )
    assert result['type'] == 'error'
    assert 'ASR component not available' in result['error']


async def test_mode_a_missing_voice_trigger_is_error():
    """Off path: Mode A with no voice-trigger component returns a structured error."""
    interface = AudioProcessorInterface(make_vad_config())
    result = await interface.process_voice_segment_for_mode(
        _make_voice_segment(), MockRequestContext(skip_wake_word=False),
        asr_component=MockASRComponent(), voice_trigger_component=None,
        wake_word_detected=False,
    )
    assert result['type'] == 'error'
    assert 'Voice trigger component not available' in result['error']


async def test_interface_metrics_pass_through_is_dict():
    """The interface surfaces the same dict-shaped metrics contract as the segmenter."""
    interface = AudioProcessorInterface(make_vad_config())
    metrics = interface.get_metrics()
    assert isinstance(metrics, dict)
    assert _VAD_METRIC_KEYS.issubset(metrics.keys())
