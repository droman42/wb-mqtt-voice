"""ARCH-10 — server-authoritative streaming ASR on `/ws/audio` (the no-VAD path).

The model marks end-of-utterance (sherpa `OnlineRecognizer`), not the device. These tests pin the
seam: the typed `(text, is_final)` contract, the provider capability flag, and the `/ws/audio`
branch that fires NLU once per finalized segment while forwarding partials. The device-signalled
batch loop stays the permanent floor and is exercised by `test_ws_driving_input`.
"""
import json
import types

from locveil_voice.intents.models import IntentResult

import pytest

from locveil_voice.providers.asr.base import ASRProvider


async def _stream(*chunks):
    for c in chunks:
        yield c


class _Offline(ASRProvider):
    """Minimal concrete ASR provider: no streaming, buffer-then-finalize."""
    def get_provider_name(self) -> str:
        return "offline_fake"

    async def transcribe_audio(self, audio_data: bytes, **kwargs) -> str:
        return f"heard:{len(audio_data)}"

    def transcribe_stream(self, audio_stream):  # required by the ABC, unused here
        ...

    # Remaining ASRProvider abstracts — trivial stubs (not exercised by these tests).
    def is_available(self) -> bool:
        return True

    def get_supported_languages(self):
        return ["ru"]

    def get_supported_formats(self):
        return ["pcm16"]

    def get_preferred_sample_rates(self):
        return [16000]

    def supports_sample_rate(self, sample_rate: int) -> bool:
        return True


@pytest.mark.asyncio
async def test_base_segments_default_buffers_to_one_final():
    """The base default consumes the whole stream and emits exactly one finalized segment —
    the safe behavior for offline providers (no incremental endpointing)."""
    p = _Offline({})
    segs = [s async for s in p.transcribe_stream_segments(_stream(b"ab", b"cd", b"ef"))]
    assert segs == [("heard:6", True)]
    assert p.supports_streaming is False


def test_sherpa_supports_streaming_tracks_model_type():
    """Only the OnlineRecognizer model types advertise streaming; offline ones don't."""
    from locveil_voice.providers.asr.sherpa_onnx import SherpaOnnxASRProvider
    assert SherpaOnnxASRProvider({"model_type": "vosk-streaming"}).supports_streaming is True
    assert SherpaOnnxASRProvider({"model_type": "vosk-transducer"}).supports_streaming is False
    assert SherpaOnnxASRProvider({"model_type": "whisper"}).supports_streaming is False


def _make_app(core):
    from fastapi import FastAPI
    from locveil_voice.runners.webapi_router import create_webapi_router
    app = FastAPI()
    app.include_router(create_webapi_router(core, asset_loader=None, web_input=None, start_time=0.0))
    return app


def test_ws_streaming_path_fires_nlu_per_final_segment():
    """mode=streaming + a streaming-capable ASR → server endpointing: partials are forwarded,
    each finalized segment runs through process_text_input and returns a response."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    captured = {"texts": []}

    class _ASR:
        def supports_streaming(self, provider=None):
            return True

        async def transcribe_stream_segments(self, audio_stream, **kwargs):
            received = bytearray()
            async for chunk in audio_stream:           # drains until {"type":"end"} / disconnect
                received.extend(chunk)
            if not received:
                return  # BUG-13 re-arm cycle with no audio → nothing to finalize (like sherpa)
            captured["stream_len"] = len(received)
            for seg in [("привет", False), ("привет мир", True), ("спасибо", True)]:
                yield seg

    class _CM:
        def __init__(self, asr):
            self._asr = asr
        def get_component(self, name):
            return self._asr if name == "asr" else None
        def get_components(self):
            return {}

    class _WM:
        async def process_text_input(self, text, session_id=None, wants_audio=False,
                                     client_context=None, trace_context=None):
            captured["texts"].append(text)
            captured["client_context"] = client_context
            return IntentResult(text=f"ответ: {text}",
                                         metadata={}, should_speak=True)

    class _Core:
        def __init__(self):
            self.workflow_manager = _WM()
            self.config = None
            self.component_manager = _CM(_ASR())
            self.plugin_manager = None
            self.output_manager = None

    with TestClient(_make_app(_Core())).websocket_connect("/ws/audio") as ws:
        ws.send_text(json.dumps({"type": "register", "client_id": "kitchen_node",
                                 "room_name": "Кухня", "mode": "streaming", "sample_rate": 16000}))
        assert ws.receive_json()["type"] == "registered"
        ws.send_bytes(b"\x00\x01" * 320)
        ws.send_text(json.dumps({"type": "end"}))
        partial = ws.receive_json()
        assert partial == {"type": "partial", "text": "привет"}
        r1 = ws.receive_json()
        assert r1["type"] == "response" and r1["text"] == "ответ: привет мир"
        r2 = ws.receive_json()
        assert r2["type"] == "response" and r2["text"] == "ответ: спасибо"

    assert captured["texts"] == ["привет мир", "спасибо"]   # NLU once per FINAL, not per partial
    assert captured["stream_len"] == 640
    assert captured["client_context"]["skip_wake_word"] is True


def test_ws_streaming_request_falls_back_to_batch_when_asr_not_streaming():
    """mode=streaming but the ASR can't endpoint → the device-signalled batch floor runs instead
    (process_audio_input on the accumulated utterance)."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    captured = {}

    class _ASR:
        def supports_streaming(self, provider=None):
            return False

    class _CM:
        def get_component(self, name):
            return _ASR() if name == "asr" else None
        def get_components(self):
            return {}

    class _WM:
        async def process_audio_input(self, audio_data, session_id=None, wants_audio=False,
                                      client_context=None, trace_context=None):
            captured["audio_len"] = len(audio_data.data)
            return IntentResult(text="готово", metadata={})

    class _Core:
        def __init__(self):
            self.workflow_manager = _WM()
            self.config = None
            self.component_manager = _CM()
            self.plugin_manager = None
            self.output_manager = None

    with TestClient(_make_app(_Core())).websocket_connect("/ws/audio") as ws:
        ws.send_text(json.dumps({"type": "register", "client_id": "n1", "room_name": "Зал",
                                 "mode": "streaming"}))
        assert ws.receive_json()["type"] == "registered"
        ws.send_bytes(b"\x00\x01" * 160)
        ws.send_text(json.dumps({"type": "end"}))
        assert ws.receive_json()["text"] == "готово"

    assert captured["audio_len"] == 320


def test_ws_streaming_serves_multiple_utterances_per_connection():
    """BUG-13 (re-scoped): each {"type":"end"} finalizes ONE utterance and the connection
    re-arms for the next — batch-floor parity (used to close after the first response)."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    class _ASR:
        def __init__(self):
            self.calls = 0

        def supports_streaming(self, provider=None):
            return True

        async def transcribe_stream_segments(self, audio_stream, **kwargs):
            self.calls += 1
            n = 0
            async for chunk in audio_stream:
                n += len(chunk)
            if n:  # empty re-arm cycles (idle/disconnect) finalize to nothing, like sherpa
                yield (f"утт{self.calls}", True)

    class _CM:
        def __init__(self, asr):
            self._asr = asr
        def get_component(self, name):
            return self._asr if name == "asr" else None
        def get_components(self):
            return {}

    class _WM:
        async def process_text_input(self, text, session_id=None, wants_audio=False,
                                     client_context=None, trace_context=None):
            return IntentResult(text=f"ответ: {text}",
                                         metadata={}, should_speak=True)

    class _Core:
        def __init__(self):
            self.workflow_manager = _WM()
            self.config = None
            self.component_manager = _CM(_ASR())
            self.plugin_manager = None
            self.output_manager = None

    with TestClient(_make_app(_Core())).websocket_connect("/ws/audio") as ws:
        ws.send_text(json.dumps({"type": "register", "client_id": "kitchen_node",
                                 "room_name": "Кухня", "mode": "streaming", "sample_rate": 16000}))
        assert ws.receive_json()["type"] == "registered"

        ws.send_bytes(b"\x00\x01" * 320)
        ws.send_text(json.dumps({"type": "end"}))
        assert ws.receive_json()["text"] == "ответ: утт1"

        # the connection survives — second utterance, same socket
        ws.send_bytes(b"\x00\x01" * 320)
        ws.send_text(json.dumps({"type": "end"}))
        assert ws.receive_json()["text"] == "ответ: утт2"


def test_ws_streaming_bounded_client_without_end_is_force_finalized(monkeypatch):
    """BUG-13 (re-scoped): a bounded client that stops sending WITHOUT an end frame used to
    hang forever (bounded audio never trips the model endpoint; receive() blocked). The idle
    timeout now force-finalizes the utterance."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from locveil_voice.runners import webapi_router as wr

    monkeypatch.setattr(wr, "WS_STREAMING_IDLE_TIMEOUT_SECONDS", 0.3)

    class _ASR:
        def supports_streaming(self, provider=None):
            return True

        async def transcribe_stream_segments(self, audio_stream, **kwargs):
            n = 0
            async for chunk in audio_stream:
                n += len(chunk)
            if n:
                yield ("таймер на десять минут", True)

    class _CM:
        def __init__(self, asr):
            self._asr = asr
        def get_component(self, name):
            return self._asr if name == "asr" else None
        def get_components(self):
            return {}

    class _WM:
        async def process_text_input(self, text, session_id=None, wants_audio=False,
                                     client_context=None, trace_context=None):
            return IntentResult(text=f"ответ: {text}",
                                         metadata={}, should_speak=True)

    class _Core:
        def __init__(self):
            self.workflow_manager = _WM()
            self.config = None
            self.component_manager = _CM(_ASR())
            self.plugin_manager = None
            self.output_manager = None

    with TestClient(_make_app(_Core())).websocket_connect("/ws/audio") as ws:
        ws.send_text(json.dumps({"type": "register", "client_id": "kitchen_node",
                                 "room_name": "Кухня", "mode": "streaming", "sample_rate": 16000}))
        assert ws.receive_json()["type"] == "registered"
        ws.send_bytes(b"\x00\x01" * 320)
        # NO end frame — the idle timeout must finalize and answer anyway
        resp = ws.receive_json()
        assert resp["type"] == "response" and resp["text"] == "ответ: таймер на десять минут"
