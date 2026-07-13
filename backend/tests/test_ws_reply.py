"""ARCH-22 #1 — ESP32 reply channel: CallbackReplyChannel framing + /ws/audio/reply lifecycle."""

import json

import pytest

from locveil_voice.core.interfaces.output import OutputModality
from locveil_voice.intents.context_models import RequestContext
from locveil_voice.outputs.remote_audio import CallbackReplyChannel
from locveil_voice.utils.audio_negotiation import AudioContract
from locveil_voice.utils.audio_stream import PCMStream


@pytest.mark.asyncio
async def test_callback_reply_channel_frames_begin_pcm_end():
    sent = []

    async def send_json(d):
        sent.append(("json", d))

    async def send_bytes(b):
        sent.append(("bytes", bytes(b)))

    ch = CallbackReplyChannel(AudioContract([22050], 22050, ["pcm16"], "pcm16", 1),
                              send_json, send_bytes, chunk_bytes=8)
    pcm = b"\x01\x02" * 10  # 20 bytes
    await ch.send_audio(pcm, sample_rate=22050, channels=1, sample_width=2)

    assert sent[0] == ("json", {"type": "speak_begin", "rate": 22050, "channels": 1, "width": 16, "seq": 1})
    assert sent[-1] == ("json", {"type": "speak_end", "seq": 1})
    body = b"".join(b for t, b in sent if t == "bytes")
    assert body == pcm
    assert len([1 for t, _ in sent if t == "bytes"]) > 1  # genuinely chunked
    assert ch.is_connected() is True


def _build_app():
    from fastapi import FastAPI
    from locveil_voice.runners.webapi_router import create_webapi_router
    from locveil_voice.outputs.manager import OutputManager

    class _FakeTTS:
        async def synthesize_to_stream(self, text, **kw):
            async def _f():
                yield b"\x00\x00"
            return PCMStream(16000, 1, 2, _f())

    class _PassNeg:
        output_sink = None

        async def to_sink(self, audio_data, sink=None, trace_context=None):
            return audio_data

    class _CM:
        def get_component(self, name):
            return _FakeTTS() if name == "tts" else None

    om = OutputManager()

    class _Core:
        def __init__(self):
            self.output_manager = om
            self.audio_negotiator = _PassNeg()
            self.component_manager = _CM()
            self.config = None
            self.plugin_manager = None
            self.workflow_manager = None

    router = create_webapi_router(_Core(), asset_loader=None, web_input=None, start_time=0.0)
    app = FastAPI()
    app.include_router(router)
    return app, om


def test_ws_audio_reply_registers_routes_and_deregisters():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    app, om = _build_app()

    with TestClient(app).websocket_connect("/ws/audio/reply") as ws:
        ws.send_text(json.dumps({"type": "register-reply", "client_id": "kitchen_node",
                                 "audio_out": {"rate": 22050, "channels": 1, "width": 16}}))
        ack = ws.receive_json()
        assert ack["type"] == "registered" and ack["client_id"] == "kitchen_node"

        # A SPEECH result from this device origin-routes to its RemoteAudioOutput.
        ctx = RequestContext(session_id="s", client_id="kitchen_node")
        targets = om.select(OutputModality.SPEECH, ctx)
        assert len(targets) == 1 and targets[0].origin_key() == "kitchen_node"

    # After disconnect the output is deregistered.
    assert om.select(OutputModality.SPEECH, RequestContext(session_id="s", client_id="kitchen_node")) == []


def test_ws_audio_reply_rejects_bad_first_frame():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    app, _ = _build_app()
    with TestClient(app).websocket_connect("/ws/audio/reply") as ws:
        ws.send_text(json.dumps({"type": "register", "client_id": "x"}))  # wrong type
        msg = ws.receive_json()
        assert msg["type"] == "error"
