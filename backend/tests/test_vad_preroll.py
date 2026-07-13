"""ARCH-18 PR-5 — pre-roll sized from the active VAD provider's detection latency at the REAL canonical
frame duration (no magic frame-ms constant).

`detection_latency_ms(frame_ms)` lets each engine express its onset lag given the actual frame duration the
segmenter observes: energy is frame-count-based (so it scales with frame_ms and the pre-roll collapses to
`voice_frames_required + margin`); silero/microvad are duration-based (ms, frame_ms-independent).
"""
from locveil_voice.workflows.audio_processor import VoiceSegmenter
from locveil_voice.config.models import VADConfig
from locveil_voice.config.schemas import MicroVADProviderSchema
from locveil_voice.intents.models import AudioData


def _seg(voice_frames_required):
    return VoiceSegmenter(VADConfig(default_provider="energy",
                                    providers={"energy": {"voice_frames_required": voice_frames_required}}))


def _frame(ms, rate=16000):
    samples = int(rate * ms / 1000)
    return AudioData(data=b"\x00\x00" * samples, timestamp=0.0, sample_rate=rate, channels=1)


def test_energy_latency_tracks_the_real_frame_duration():
    seg = _seg(3)
    assert seg.vad_engine.detection_latency_ms(20.0) == 60    # 3 frames × 20 ms
    assert seg.vad_engine.detection_latency_ms(93.0) == 279   # adapts to a big (93 ms) chunk, no magic 25


async def test_energy_preroll_is_frames_plus_margin_independent_of_frame_ms():
    # for a frame-count engine the frame_ms cancels: pre-roll = voice_frames_required + margin
    for frame_ms in (20.0, 93.0):
        seg = _seg(3)
        await seg.process_audio_chunk(_frame(frame_ms))
        assert seg.pre_buffer_size == 3 + 2


async def test_higher_voice_frames_required_gives_bigger_preroll():
    lo = _seg(2); await lo.process_audio_chunk(_frame(23.0))
    hi = _seg(8); await hi.process_audio_chunk(_frame(23.0))
    assert hi.pre_buffer_size > lo.pre_buffer_size


def test_microvad_detection_latency_is_a_config_field():
    assert MicroVADProviderSchema(detection_latency_ms=45).detection_latency_ms == 45
