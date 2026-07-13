"""
AudioTranscoder.resample_audio_data — contract tests.

Replaces the old Phase-7 timing/throughput/memory benchmarks (flaky wall-clock
assertions that drifted on the resampler internals). This asserts the *public*
resampling contract instead:

  - no-op path (source == target) preserves data and flags resampling_applied=False
  - real resample returns AudioData at the target rate with metadata preserved
  - the cache reports hits/misses, stamps `cache_hit` on results, and evicts
    FIFO at `_max_cache_size`
  - every ConversionMethod yields target-rate output
"""

import asyncio
import time

import numpy as np

from locveil_voice.utils.audio_helpers import AudioTranscoder, ConversionMethod
from locveil_voice.intents.models import AudioData


def create_test_audio(sample_rate: int, duration: float = 0.1, channels: int = 1,
                      freq: float = 440.0) -> AudioData:
    """Generate deterministic 16-bit PCM sine-wave audio at the given rate."""
    samples = int(sample_rate * duration * channels)
    t = np.linspace(0, duration, samples, False)
    audio_int16 = (np.sin(2 * np.pi * freq * t) * 32767).astype(np.int16)
    return AudioData(
        data=audio_int16.tobytes(),
        timestamp=time.time(),
        sample_rate=sample_rate,
        channels=channels,
        format="pcm16",
        metadata={"test_data": True},
    )


def _resample(audio, target, method=ConversionMethod.POLYPHASE):
    return asyncio.run(AudioTranscoder.resample_audio_data(audio, target, method))


# --------------------------------------------------------------------------- #
# No-op / passthrough path
# --------------------------------------------------------------------------- #

def test_same_rate_is_noop_and_preserves_data():
    audio = create_test_audio(16000)
    out = _resample(audio, 16000)

    assert out.sample_rate == 16000
    assert out.data == audio.data                       # bytes untouched
    assert out.metadata["resampling_applied"] is False
    assert out.metadata["original_sample_rate"] == 16000
    # caller metadata is carried through
    assert out.metadata["test_data"] is True


def test_same_rate_does_not_touch_cache():
    AudioTranscoder.clear_cache()
    audio = create_test_audio(16000)
    _resample(audio, 16000)
    stats = AudioTranscoder.get_cache_stats()
    assert stats["cache_hits"] == 0
    assert stats["cache_misses"] == 0
    assert stats["cache_size"] == 0


# --------------------------------------------------------------------------- #
# Real resample path
# --------------------------------------------------------------------------- #

def test_resample_changes_rate_and_preserves_metadata():
    AudioTranscoder.clear_cache()
    audio = create_test_audio(44100, duration=0.1)
    out = _resample(audio, 16000)

    assert out.sample_rate == 16000
    assert out.channels == audio.channels
    assert out.format == audio.format
    assert out.timestamp == audio.timestamp
    assert out.metadata["resampling_applied"] is True
    assert out.metadata["original_sample_rate"] == 44100
    assert out.metadata["resampling_method"] == ConversionMethod.POLYPHASE.value
    assert out.metadata["cache_hit"] is False
    # downsample => fewer samples => fewer bytes
    assert 0 < len(out.data) < len(audio.data)


def test_all_conversion_methods_yield_target_rate():
    AudioTranscoder.clear_cache()
    for method in ConversionMethod:
        audio = create_test_audio(48000, duration=0.05)
        out = _resample(audio, 16000, method)
        assert out.sample_rate == 16000, f"{method} did not hit target rate"
        assert len(out.data) > 0
        assert out.metadata["resampling_method"] == method.value


def test_upsample_increases_sample_count():
    AudioTranscoder.clear_cache()
    audio = create_test_audio(16000, duration=0.1)
    out = _resample(audio, 44100)
    assert out.sample_rate == 44100
    assert len(out.data) > len(audio.data)


# --------------------------------------------------------------------------- #
# Cache contract
# --------------------------------------------------------------------------- #

def test_get_cache_stats_shape():
    AudioTranscoder.clear_cache()
    stats = AudioTranscoder.get_cache_stats()
    assert set(stats) == {
        "cache_hits", "cache_misses", "hit_rate", "cache_size", "max_cache_size",
        "cache_bytes", "max_cache_bytes",  # QUAL-58 M4: byte budget
    }
    # empty cache => no division-by-zero, hit_rate defined
    assert stats["hit_rate"] == 0.0
    assert stats["cache_size"] == 0


def test_second_identical_call_is_a_cache_hit():
    AudioTranscoder.clear_cache()
    audio = create_test_audio(44100, duration=0.1)

    first = _resample(audio, 16000)
    assert first.metadata["cache_hit"] is False

    second = _resample(audio, 16000)
    assert second.metadata["cache_hit"] is True
    assert second.data == first.data                    # identical resampled bytes

    stats = AudioTranscoder.get_cache_stats()
    assert stats["cache_hits"] == 1
    assert stats["cache_misses"] == 1
    assert 0.0 < stats["hit_rate"] <= 1.0


def test_clear_cache_resets_counters_and_entries():
    AudioTranscoder.clear_cache()
    audio = create_test_audio(44100, duration=0.1)
    _resample(audio, 16000)
    assert AudioTranscoder.get_cache_stats()["cache_size"] >= 1

    AudioTranscoder.clear_cache()
    stats = AudioTranscoder.get_cache_stats()
    assert stats["cache_size"] == 0
    assert stats["cache_hits"] == 0
    assert stats["cache_misses"] == 0


def test_cache_evicts_fifo_at_max_size():
    original_max = AudioTranscoder._max_cache_size
    AudioTranscoder._max_cache_size = 5
    AudioTranscoder.clear_cache()
    try:
        # Each distinct source rate => distinct cache key => fills past capacity.
        for i in range(12):
            audio = create_test_audio(16000 + i * 1000, duration=0.05)
            _resample(audio, 44100)
            assert AudioTranscoder.get_cache_stats()["cache_size"] <= 5

        assert AudioTranscoder.get_cache_stats()["cache_size"] == 5
    finally:
        AudioTranscoder._max_cache_size = original_max
        AudioTranscoder.clear_cache()


def test_extreme_ratios_still_resample_to_target():
    AudioTranscoder.clear_cache()
    for source, target in [(8000, 96000), (96000, 8000), (11025, 48000)]:
        audio = create_test_audio(source, duration=0.05)
        out = _resample(audio, target, ConversionMethod.ADAPTIVE)
        assert out.sample_rate == target, f"{source}->{target} missed target"
        assert len(out.data) > 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
