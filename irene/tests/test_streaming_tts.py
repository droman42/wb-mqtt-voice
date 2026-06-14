"""ARCH-21 PR-1: TTS synthesize_to_stream port + base buffer-then-stream simulation."""

import wave
from pathlib import Path

import pytest

from irene.providers.tts.base import TTSProvider
from irene.utils.audio_stream import PCMStream, collect_pcm


class _WavTTSProvider(TTSProvider):
    """Minimal WAV-producing provider exercising the base simulation."""

    def __init__(self, pcm: bytes, rate: int, channels: int, width: int):
        super().__init__({})
        self._pcm, self._rate, self._channels, self._width = pcm, rate, channels, width

    async def synthesize_to_file(self, text: str, output_path: Path, **kwargs) -> None:
        with wave.open(str(output_path), "wb") as w:
            w.setnchannels(self._channels)
            w.setsampwidth(self._width)
            w.setframerate(self._rate)
            w.writeframes(self._pcm)

    def get_capabilities(self):
        return {"formats": ["wav"]}

    def get_provider_name(self) -> str:
        return "wavfake"

    async def is_available(self) -> bool:
        return True


class _TextTTSProvider(TTSProvider):
    """Text-only provider (like console) — base simulation must reject it clearly."""

    async def synthesize_to_file(self, text: str, output_path: Path, **kwargs) -> None:
        output_path.write_text(text, encoding="utf-8")

    def get_capabilities(self):
        return {"formats": ["text"]}

    def get_provider_name(self) -> str:
        return "textfake"

    async def is_available(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_base_simulation_yields_pcm_and_format():
    pcm = b"\x01\x00\x02\x00\x03\x00\x04\x00" * 500
    provider = _WavTTSProvider(pcm, rate=22050, channels=1, width=2)

    stream = await provider.synthesize_to_stream("привет")

    assert isinstance(stream, PCMStream)
    assert (stream.sample_rate, stream.channels, stream.sample_width) == (22050, 1, 2)
    assert await collect_pcm(stream.frames) == pcm


@pytest.mark.asyncio
async def test_base_simulation_chunks_into_multiple_frames():
    pcm = b"\xaa\xbb" * 4000  # well over one ~1024-sample block
    provider = _WavTTSProvider(pcm, rate=16000, channels=1, width=2)

    stream = await provider.synthesize_to_stream("x")
    chunks = [c async for c in stream.frames]

    assert len(chunks) > 1  # genuinely chunked
    assert b"".join(chunks) == pcm


@pytest.mark.asyncio
async def test_base_simulation_rejects_non_wav_provider():
    provider = _TextTTSProvider({})
    with pytest.raises(NotImplementedError):
        await provider.synthesize_to_stream("not audio")


@pytest.mark.asyncio
async def test_component_delegates_to_selected_provider():
    from irene.components.tts_component import TTSComponent

    pcm = b"\x10\x20\x30\x40" * 100
    component = TTSComponent()
    component.providers = {"wavfake": _WavTTSProvider(pcm, 44100, 2, 2)}
    component.default_provider = "wavfake"
    component._lazy_loading_enabled = False

    stream = await component.synthesize_to_stream("hello")

    assert (stream.sample_rate, stream.channels, stream.sample_width) == (44100, 2, 2)
    assert await collect_pcm(stream.frames) == pcm
