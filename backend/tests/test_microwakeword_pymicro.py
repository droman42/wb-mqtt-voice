"""QUAL-20 — microWakeWord provider over pymicro-wakeword (real runtime smoke).

The provider was a stub (`np.random` feature extraction — which would trigger randomly). It is now a thin
adapter over `pymicro-wakeword`: real micro frontend + streaming tflite inference. These tests run the real
library against a built-in model and assert sane wiring (builds detectors, no false-trigger on silence,
clean teardown). A true-positive test needs a wake-word audio clip we don't ship, so detection-positive is
left to integration/hardware; silence-stays-negative is the meaningful regression guard here.

Skips cleanly if the optional `pymicro-wakeword` extra isn't installed.
"""
import pytest

pytest.importorskip("pymicro_wakeword")

from locveil_voice.providers.voice_trigger.microwakeword import MicroWakeWordProvider
from locveil_voice.intents.models import AudioData


def _audio(pcm: bytes) -> AudioData:
    return AudioData(data=pcm, timestamp=0.0, sample_rate=16000, channels=1)


async def test_builds_builtin_detectors():
    p = MicroWakeWordProvider({"wake_words": ["okay_nabu", "hey_jarvis"]})
    await p._do_initialize()
    assert len(p._detectors) == 2
    assert p._detector_words == ["okay_nabu", "hey_jarvis"]
    # built-in catalog is advertised
    assert "okay_nabu" in p.get_supported_wake_words()
    await p.cleanup()
    assert p._detectors == []


async def test_silence_does_not_trigger():
    """The np.random stub would fire on silence; the real frontend must not."""
    p = MicroWakeWordProvider({"wake_words": ["okay_nabu"]})
    await p._do_initialize()
    # 1 s of digital silence in 100 ms frames (3200 bytes each)
    silence = b"\x00\x00" * 1600
    detected = False
    for _ in range(10):
        res = await p.detect_wake_word(_audio(silence))
        detected = detected or res.detected
    assert detected is False
    await p.cleanup()


async def test_unknown_wake_word_without_model_raises():
    """A wake word with no built-in and no custom model resolves to no detector → fail loud on init."""
    p = MicroWakeWordProvider({"wake_words": ["totally_unknown_phrase"]})
    with pytest.raises(RuntimeError):
        await p._do_initialize()


async def test_aliases_resolve():
    p = MicroWakeWordProvider({"wake_words": ["jarvis", "nabu"]})
    await p._do_initialize()
    assert len(p._detectors) == 2   # jarvis→HEY_JARVIS, nabu→OKAY_NABU
    await p.cleanup()
