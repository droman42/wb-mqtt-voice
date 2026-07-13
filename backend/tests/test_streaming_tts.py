"""ARCH-21 PR-1: TTS synthesize_to_stream port + base buffer-then-stream simulation."""

import wave
from pathlib import Path

import pytest

from locveil_voice.providers.tts.base import TTSProvider
from locveil_voice.utils.audio_stream import PCMStream, collect_pcm


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
    from locveil_voice.components.tts_component import TTSComponent

    pcm = b"\x10\x20\x30\x40" * 100
    component = TTSComponent()
    component.providers = {"wavfake": _WavTTSProvider(pcm, 44100, 2, 2)}
    component.default_provider = "wavfake"
    component._lazy_loading_enabled = False

    stream = await component.synthesize_to_stream("hello")

    assert (stream.sample_rate, stream.channels, stream.sample_width) == (44100, 2, 2)
    assert await collect_pcm(stream.frames) == pcm


def _component_with_provider(provider, *, negotiator):
    from types import SimpleNamespace

    from locveil_voice.components.tts_component import TTSComponent

    component = TTSComponent()
    component.providers = {provider.get_provider_name(): provider}
    component.default_provider = provider.get_provider_name()
    component._lazy_loading_enabled = False
    component.core = SimpleNamespace(audio_negotiator=negotiator)
    return component


class _PassThroughNegotiator:
    async def to_sink(self, audio_data, sink=None, trace_context=None):
        return audio_data


@pytest.mark.asyncio
async def test_synthesize_and_stream_to_streams_conformed_pcm():
    """The shared stream path: synthesize -> to_sink -> audio.play_stream; returns True."""
    pcm = b"\x01\x00\x02\x00" * 200
    provider = _WavTTSProvider(pcm, rate=22050, channels=1, width=2)
    component = _component_with_provider(provider, negotiator=_PassThroughNegotiator())

    captured = {}

    class _FakeAudio:
        async def play_stream(self, data, *, sample_rate, channels, sample_width, **kw):
            captured.update(data=data, rate=sample_rate, channels=channels, width=sample_width)

    ok = await component.synthesize_and_stream_to(_FakeAudio(), "привет")

    assert ok is True
    assert captured == {"data": pcm, "rate": 22050, "channels": 1, "width": 2}


@pytest.mark.asyncio
async def test_synthesize_and_stream_to_returns_false_without_negotiator():
    provider = _WavTTSProvider(b"\x00\x00" * 50, 16000, 1, 2)
    component = _component_with_provider(provider, negotiator=None)

    ok = await component.synthesize_and_stream_to(object(), "x")
    assert ok is False


@pytest.mark.asyncio
async def test_synthesize_and_stream_to_returns_false_for_non_streamable_provider():
    provider = _TextTTSProvider({})
    component = _component_with_provider(provider, negotiator=_PassThroughNegotiator())

    ok = await component.synthesize_and_stream_to(object(), "not audio")
    assert ok is False


def test_float_to_pcm16_conversion():
    import numpy as np

    from locveil_voice.utils.audio_stream import float_to_pcm16

    out = float_to_pcm16(np.array([0.0, 1.0, -1.0, 0.5], dtype=np.float32))
    samples = np.frombuffer(out, dtype="<i2")
    assert list(samples) == [0, 32767, -32767, 16383]


@pytest.mark.asyncio
async def test_silero_v4_native_override_yields_int16_pcm(monkeypatch):
    """Silero v4 override: apply_tts samples -> int16 PCM stream, no WAV round-trip."""
    import numpy as np

    from locveil_voice.providers.tts.silero_v4 import SileroV4TTSProvider
    from locveil_voice.utils.audio_stream import float_to_pcm16

    provider = SileroV4TTSProvider.__new__(SileroV4TTSProvider)
    provider._available = True
    provider.default_speaker = "xenia"
    provider.sample_rate = 48000
    provider._speakers = ["xenia"]

    samples = np.array([0.0, 0.25, -0.25, 0.75], dtype=np.float32)

    class _FakeModel:
        def apply_tts(self, text, speaker, sample_rate):
            return samples

    provider._model = _FakeModel()

    async def _noop():
        return None

    async def _passthrough(t):
        return t

    monkeypatch.setattr(provider, "_ensure_model_loaded", _noop)
    monkeypatch.setattr(provider, "_normalize_text_async", _passthrough)

    stream = await provider.synthesize_to_stream("привет")

    assert (stream.sample_rate, stream.channels, stream.sample_width) == (48000, 1, 2)
    assert await collect_pcm(stream.frames) == float_to_pcm16(samples)


@pytest.mark.asyncio
async def test_elevenlabs_override_wraps_pcm(monkeypatch):
    """ElevenLabs override returns a PCMStream of the raw PCM the API hands back."""
    from locveil_voice.providers.tts.elevenlabs import ElevenLabsTTSProvider

    provider = ElevenLabsTTSProvider.__new__(ElevenLabsTTSProvider)
    provider.voice_id = "v"
    provider.stability = 0.5
    provider.similarity_boost = 0.5
    provider.output_pcm_rate = 22050

    pcm = b"\x11\x22\x33\x44" * 10

    async def _fake_generate_pcm(text, voice_id, stability, similarity_boost, rate):
        assert rate == 22050
        return pcm

    monkeypatch.setattr(provider, "_generate_pcm", _fake_generate_pcm)

    stream = await provider.synthesize_to_stream("hello")

    assert (stream.sample_rate, stream.channels, stream.sample_width) == (22050, 1, 2)
    assert await collect_pcm(stream.frames) == pcm
