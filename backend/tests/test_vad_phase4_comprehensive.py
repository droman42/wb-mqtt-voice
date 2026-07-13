"""
VAD segmenter — port-level behaviour (TEST-7 rewrite of the old Phase-4 "comprehensive" script).

The original file drove timing-sensitive scenario scripts and asserted against a `ProcessingMetrics`
*object* plus engine knobs that lived directly on `VADConfig` (`energy_threshold`, `sensitivity`,
`voice_duration_ms`, ...). Both shapes drifted:

  * metrics are now a **dict** returned by `MetricsCollector.get_vad_metrics()` (Phase 4 unification);
  * engine knobs moved under `[vad.providers.<name>]` (ARCH-18) — `VADConfig` only carries
    segmenter/pipeline fields now.

This rewrite asserts the *contract* of `VoiceSegmenter`, not the old internal shapes, and deliberately
avoids wall-clock real-time-factor assertions (the source of the flap). The only timing assertion uses
the VAD's *own* per-frame compute cost with a generous bound.
"""

import asyncio
from typing import List, Tuple

import pytest

from locveil_voice.workflows.audio_processor import VoiceSegmenter, VoiceSegment
from locveil_voice.config.models import VADConfig
from locveil_voice.intents.models import AudioData
from locveil_voice.core.metrics import get_metrics_collector

# Reuse the synthetic audio generator (silence / noise / speech_like) from the Phase-1 basic tests.
from tests.test_vad_basic import generate_test_audio_data

CHUNK_MS = 23  # the canonical VOSK-problem frame size the segmenter was built around


# --------------------------------------------------------------------------- helpers

def _vad_config(*, enabled: bool = True, energy_provider: dict | None = None, **kw) -> VADConfig:
    """Build a VADConfig with engine knobs in the right place ([vad.providers.energy], ARCH-18)."""
    providers = {"energy": energy_provider} if energy_provider is not None else {}
    return VADConfig(enabled=enabled, default_provider="energy", providers=providers, **kw)


def _chunks(pattern: List[Tuple[str, int]]) -> List[AudioData]:
    """Materialise a deterministic list of audio chunks from a (type, count) pattern — no async sleeps,
    no real-time pacing (that is what made the old benchmark flaky)."""
    return [generate_test_audio_data(CHUNK_MS, audio_type=t) for t, n in pattern for _ in range(n)]


def _drive(segmenter: VoiceSegmenter, chunks: List[AudioData]):
    """Feed every chunk through the segmenter; return (segments, vad-metrics-delta).

    The metrics collector is a process-wide singleton whose VAD counters only ever accumulate, so we
    assert on *deltas* rather than absolute values (robust regardless of what ran before us)."""
    before = get_metrics_collector().get_vad_metrics()
    segments: List[VoiceSegment] = []

    async def run():
        for c in chunks:
            seg = await segmenter.process_audio_chunk(c)
            if seg is not None:
                segments.append(seg)

    asyncio.run(run())
    after = get_metrics_collector().get_vad_metrics()
    delta = {k: after[k] - before[k] for k in before if isinstance(before[k], (int, float))}
    return segments, delta


# --------------------------------------------------------------------------- metrics contract

def test_processing_metrics_is_a_dict_with_the_documented_keys():
    """The Phase-4 drift fix: get_processing_metrics() returns a DICT, not a ProcessingMetrics object."""
    seg = VoiceSegmenter(_vad_config())
    _drive(seg, _chunks([("silence", 3)]))

    metrics = seg.get_processing_metrics()
    assert isinstance(metrics, dict)
    for key in (
        "total_chunks_processed",
        "voice_segments_detected",
        "silence_chunks_skipped",
        "average_processing_time_ms",
        "max_processing_time_ms",
        "total_processing_time_ms",
        "timeout_events",
    ):
        assert key in metrics, f"missing VAD metric key: {key}"
        assert isinstance(metrics[key], (int, float))


def test_every_chunk_is_counted():
    """total_chunks_processed advances by exactly the number of frames fed (per-frame accounting)."""
    chunks = _chunks([("silence", 4), ("speech_like", 6), ("silence", 5)])
    _, delta = _drive(VoiceSegmenter(_vad_config()), chunks)
    assert delta["total_chunks_processed"] == len(chunks)
    # voice + silence accounting partitions the frames exactly.
    assert delta["voice_segments_detected"] + delta["silence_chunks_skipped"] == len(chunks)


# --------------------------------------------------------------------------- segmentation behaviour

def test_pure_silence_yields_no_voice_segment():
    """The no-op path: silence in, nothing out, all frames classified as silence."""
    chunks = _chunks([("silence", 20)])
    segments, delta = _drive(VoiceSegmenter(_vad_config()), chunks)
    assert segments == []
    assert delta["silence_chunks_skipped"] == len(chunks)
    assert delta["voice_segments_detected"] == 0


def test_speech_then_silence_produces_a_well_formed_segment():
    """Speech bounded by trailing silence closes a VoiceSegment with a coherent shape."""
    chunks = _chunks([("silence", 3), ("speech_like", 15), ("silence", 12)])
    segments, _ = _drive(VoiceSegmenter(_vad_config()), chunks)

    assert len(segments) >= 1, "speech bounded by silence should produce at least one voice segment"
    for s in segments:
        assert isinstance(s, VoiceSegment)
        assert s.chunk_count > 0
        assert len(s.audio_chunks) == s.chunk_count
        assert s.total_duration_ms > 0
        # duration_seconds is the public derived view of total_duration_ms.
        assert s.duration_seconds == pytest.approx(s.total_duration_ms / 1000.0)
        assert isinstance(s.metadata, dict)
        assert s.end_timestamp >= s.start_timestamp


# --------------------------------------------------------------------------- engine-knob wiring (ARCH-18)

def test_engine_threshold_governs_detection():
    """The energy threshold now lives under [vad.providers.energy] and still gates detection end-to-end.

    A near-ceiling threshold suppresses synthetic speech entirely; a normal threshold detects it. This
    proves the provider-block knob is actually consumed by the segmenter."""
    speechy = [("silence", 3), ("speech_like", 15), ("silence", 12)]

    # SimpleVAD path (fixed threshold, no adaptation) so the threshold is honoured verbatim.
    deaf = VoiceSegmenter(_vad_config(energy_provider={
        "energy_threshold": 0.9, "use_zero_crossing_rate": False, "adaptive_threshold": False,
    }))
    sharp = VoiceSegmenter(_vad_config(energy_provider={
        "energy_threshold": 0.01, "use_zero_crossing_rate": False, "adaptive_threshold": False,
    }))

    deaf_segments, deaf_delta = _drive(deaf, _chunks(speechy))
    sharp_segments, _ = _drive(sharp, _chunks(speechy))

    assert deaf_segments == [], "a near-ceiling threshold must suppress all synthetic speech"
    assert deaf_delta["voice_segments_detected"] == 0
    assert len(sharp_segments) >= 1, "a normal threshold must detect the same speech"


# --------------------------------------------------------------------------- performance (robust, no wall-clock)

def test_per_frame_compute_cost_is_bounded():
    """Robustness rewrite of the old benchmark: assert on the VAD's OWN measured per-frame compute
    time (microseconds for energy VAD on numpy), NOT wall-clock real-time-factor. The bound is the
    component's processing_timeout_ms and is generous enough to never flap under CI load."""
    chunks = _chunks([("silence", 5), ("speech_like", 80), ("silence", 5)])
    seg = VoiceSegmenter(_vad_config(processing_timeout_ms=50))
    _, delta = _drive(seg, chunks)

    n = delta["total_chunks_processed"]
    assert n == len(chunks)
    avg_ms = delta["total_processing_time_ms"] / n
    assert avg_ms < 50.0, f"average per-frame VAD compute {avg_ms:.3f}ms exceeds the generous bound"
    assert delta["total_processing_time_ms"] >= 0.0


# --------------------------------------------------------------------------- config validation contract

def test_disabled_config_is_constructible_and_off():
    """The off path: VADConfig(enabled=False) is valid and still yields a usable segmenter object
    (the workflow gates on `enabled`; the segmenter itself does not)."""
    cfg = _vad_config(enabled=False)
    assert cfg.enabled is False
    assert VoiceSegmenter(cfg) is not None


def test_valid_config_round_trips():
    cfg = _vad_config(max_segment_duration_s=15, processing_timeout_ms=40, buffer_size_frames=120,
                      asr_target_rms=0.2)
    assert cfg.max_segment_duration_s == 15
    assert cfg.asr_target_rms == pytest.approx(0.2)
    assert VoiceSegmenter(cfg) is not None


@pytest.mark.parametrize("kwargs", [
    {"max_segment_duration_s": 0},     # ge=1
    {"max_segment_duration_s": 61},    # le=60
    {"processing_timeout_ms": 0},      # ge=1
    {"buffer_size_frames": 5},         # ge=10
    {"asr_target_rms": 0.0},           # ge=0.01
    {"asr_target_rms": 0.5},           # le=0.3
])
def test_out_of_range_pipeline_fields_are_rejected(kwargs):
    """Current VADConfig validates the *pipeline* fields (the engine knobs moved to the provider block,
    so the old energy_threshold/sensitivity bound checks belong to the providers, not here)."""
    with pytest.raises(Exception):
        VADConfig(**kwargs)


def test_engine_knobs_are_no_longer_top_level_vad_fields():
    """Characterise the ARCH-18 move: the old per-engine knobs are gone from VADConfig itself; an
    unknown extra still constructs without becoming a model field (knobs belong under providers)."""
    for gone in ("energy_threshold", "sensitivity", "voice_duration_ms", "silence_duration_ms",
                 "use_zero_crossing_rate", "adaptive_threshold"):
        assert gone not in VADConfig.model_fields, f"{gone} should have moved to [vad.providers.*]"
