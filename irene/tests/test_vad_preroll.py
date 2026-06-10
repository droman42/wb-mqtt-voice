"""ARCH-18 PR-5 — the pre-roll is sized from the active VAD provider's detection_latency_ms, not a magic 4.

The voice segment feeds the wake word, so the pre-roll must cover the engine's onset lag or the wake-word
start is clipped (silero's 100 ms was being clipped by the old 4 frames ≈ 92 ms).
"""
from irene.workflows.audio_processor import VoiceSegmenter
from irene.config.models import VADConfig


def _seg(voice_frames_required):
    return VoiceSegmenter(VADConfig(default_provider="energy",
                                    providers={"energy": {"voice_frames_required": voice_frames_required}}))


def test_preroll_covers_detection_latency():
    seg = _seg(2)  # energy: 2 * 25 ms = 50 ms latency
    # the pre-buffer (frames × nominal frame ms) must hold at least the engine's detection latency
    assert seg.pre_buffer_size * 23 >= seg.vad_engine.detection_latency_ms


def test_preroll_scales_with_latency():
    lo = _seg(2)   # 50 ms
    hi = _seg(8)   # 200 ms
    assert hi.pre_buffer_size > lo.pre_buffer_size  # higher latency → bigger pre-roll
