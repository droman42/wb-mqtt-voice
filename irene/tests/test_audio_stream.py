"""ARCH-20: raw-PCM streaming-output helpers + contract wiring."""

import io
import wave

import pytest

from irene.utils.audio_stream import (
    collect_pcm,
    is_wav,
    iter_frames,
    parse_wav,
    width_to_alsa_format,
)


def _make_wav(pcm: bytes, rate: int, channels: int, width: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def test_is_wav():
    assert is_wav(b"RIFF\x00\x00\x00\x00WAVEfmt ")
    assert not is_wav(b"\x00\x01\x02\x03raw pcm bytes")
    assert not is_wav(b"RIFF")  # too short


def test_width_to_alsa_format():
    assert width_to_alsa_format(1) == "U8"
    assert width_to_alsa_format(2) == "S16_LE"
    assert width_to_alsa_format(4) == "S32_LE"
    assert width_to_alsa_format(99) == "S16_LE"  # unknown -> safe default


def test_parse_wav_roundtrips_pcm_and_format():
    pcm = b"\x01\x00\x02\x00\x03\x00\x04\x00"  # 4 mono 16-bit frames
    wav = _make_wav(pcm, rate=16000, channels=1, width=2)
    out_pcm, rate, channels, width = parse_wav(wav)
    assert out_pcm == pcm
    assert (rate, channels, width) == (16000, 1, 2)


def test_iter_frames_blocks():
    pcm = b"abcdefg"
    assert list(iter_frames(pcm, 3)) == [b"abc", b"def", b"g"]
    with pytest.raises(ValueError):
        list(iter_frames(pcm, 0))


@pytest.mark.asyncio
async def test_collect_pcm_drains_stream():
    async def gen():
        yield b"aa"
        yield b"bb"
        yield b"cc"

    assert await collect_pcm(gen()) == b"aabbcc"


@pytest.mark.asyncio
async def test_console_provider_play_stream_pcm_contract():
    """Console provider accepts the raw-PCM keyword contract without error."""
    from irene.providers.audio.console import ConsoleAudioProvider

    provider = ConsoleAudioProvider({"simulate_timing": False})

    async def gen():
        yield b"\x00\x01" * 8

    await provider.play_stream(gen(), sample_rate=16000, channels=1, sample_width=2)


@pytest.mark.asyncio
async def test_component_play_stream_forwards_pcm_kwargs():
    """The component bridges bytes -> iterator and forwards (rate, channels, width)."""
    from irene.components.audio_component import AudioComponent

    captured = {}

    class _FakeProvider:
        async def play_stream(self, pcm_stream, *, sample_rate, channels, sample_width, **kwargs):
            captured["rate"] = sample_rate
            captured["channels"] = channels
            captured["width"] = sample_width
            captured["pcm"] = await collect_pcm(pcm_stream)

    component = AudioComponent()
    component.providers = {"fake": _FakeProvider()}
    component.default_provider = "fake"

    await component.play_stream(b"\x10\x20\x30\x40", sample_rate=22050, channels=2, sample_width=2)

    assert captured == {"rate": 22050, "channels": 2, "width": 2, "pcm": b"\x10\x20\x30\x40"}
