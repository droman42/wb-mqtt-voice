"""ARCH-18 PR-4b — asr boundary conformance.

The mic pipeline delivers canonical audio (PR-3), so `process_audio` TRUSTS canonical and does no resampling.
Direct entries whose audio may arrive at any rate (the `/transcribe` file upload) conform at their boundary
via `_conform_to_rate`. (`/stream` requires canonical 16 kHz on the wire — the satellite contract.)
"""
import pytest

from irene.components.asr_component import ASRComponent
from irene.intents.models import AudioData


def _audio(rate, n=1600):
    return AudioData(data=b"\x00\x00" * n, timestamp=0.0, sample_rate=rate, channels=1)


async def test_conform_resamples_when_rate_differs():
    out = await ASRComponent._conform_to_rate(_audio(44100, 4410), 16000)
    assert out.sample_rate == 16000


async def test_conform_is_noop_when_already_at_target():
    a = _audio(16000)
    assert await ASRComponent._conform_to_rate(a, 16000) is a


async def test_conform_is_noop_when_no_target_rate():
    a = _audio(44100)
    assert await ASRComponent._conform_to_rate(a, None) is a


async def test_conform_is_fatal_when_resampling_disabled():
    with pytest.raises(ValueError):
        await ASRComponent._conform_to_rate(_audio(44100), 16000, allow_resampling=False)
