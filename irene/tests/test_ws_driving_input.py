"""ARCH-6 — WebSocket streaming-input driving adapter + room/device activation.

Proves the core contract: the registration handshake populates the physical identity so
`resolve_physical_id` returns the room/device origin (not the ephemeral session id), and the
`/ws/audio` adapter runs handshake → stream → full pipeline → response. The device-model half
(entity_type/room_context) is deferred to ARCH-7/QUAL-35.
"""
import json

import pytest

from irene.core.client_registry import resolve_physical_id, ClientRegistration


def test_resolve_physical_id_activates_on_registered_client():
    """The single activation seam: a registered client_id/room becomes the action-scope id."""
    # Before ARCH-6 (no handshake): falls back to the session id.
    assert resolve_physical_id(None, None, "sess-123") == "sess-123"
    # After the handshake populates client_id: the physical origin wins.
    assert resolve_physical_id("kitchen_node", "Кухня", "sess-123") == "kitchen_node"
    # room without client_id still beats the session.
    assert resolve_physical_id(None, "Кухня", "sess-123") == "Кухня"


def test_client_registration_from_handshake_payload():
    """The handshake JSON maps onto ClientRegistration/ClientDevice with no model change."""
    reg = ClientRegistration.from_dict({
        "type": "register",
        "client_id": "kitchen_node",
        "room_name": "Кухня",
        "available_devices": [
            {"id": "kitchen_light", "name": "потолочный свет", "type": "light",
             "capabilities": {"dimmable": True}, "location": "Кухня"}
        ],
    })
    assert reg.client_id == "kitchen_node"
    assert reg.room_name == "Кухня"
    assert len(reg.available_devices) == 1
    assert reg.available_devices[0].type == "light"


def test_registration_carries_arch22_d14_fields():
    """ARCH-22 D-14: register carries name + primary/covered rooms + audio_out + versions; `primary_room`
    aliases `room_name`; extra wire keys (type/wants_audio) are ignored."""
    reg = ClientRegistration.from_dict({
        "type": "register",
        "client_id": "hall_node",
        "name": "Прихожая",
        "primary_room": "Прихожая",                      # alias for room_name
        "covered_rooms": ["Прихожая", "Кухня"],
        "audio_out": {"rate": 22050, "channels": 1, "width": 16},
        "firmware_version": "1.2.0",
        "model_version": "jarvis-2026.06",
        "wants_audio": True,
    })
    assert reg.room_name == "Прихожая" and reg.primary_room == "Прихожая"
    assert reg.covered_rooms == ["Прихожая", "Кухня"]
    assert reg.audio_out["rate"] == 22050
    assert reg.firmware_version == "1.2.0" and reg.model_version == "jarvis-2026.06"
    assert reg.name == "Прихожая"


def test_ws_audio_adapter_handshake_and_pipeline():
    """End-to-end adapter: register → stream PCM → response, with the pipeline stubbed.

    Verifies the handshake registers the node and that the streamed utterance is dispatched to
    workflow_manager.process_audio_input with the client identity threaded into client_context.
    """
    fastapi = pytest.importorskip("fastapi")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from irene.runners.webapi_router import create_webapi_router
    from irene.core.client_registry import get_client_registry

    captured = {}

    class _WM:
        async def process_audio_input(self, audio_data, session_id=None, wants_audio=False,
                                      client_context=None, trace_context=None):
            captured["client_context"] = client_context
            captured["audio_len"] = len(audio_data.data)

            class _R:
                text = "готово"
                success = True
                metadata = {"ok": True}
            return _R()

    class _Core:
        def __init__(self):
            self.workflow_manager = _WM()
            self.config = None
            self.component_manager = None
            self.plugin_manager = None

    router = create_webapi_router(_Core(), asset_loader=None, web_input=None, start_time=0.0)
    app = FastAPI()
    app.include_router(router)

    with TestClient(app).websocket_connect("/ws/audio") as ws:
        ws.send_text(json.dumps({"type": "register", "client_id": "kitchen_node",
                                 "room_name": "Кухня", "sample_rate": 16000}))
        ack = ws.receive_json()
        assert ack["type"] == "registered" and ack["client_id"] == "kitchen_node"
        ws.send_bytes(b"\x00\x01" * 320)  # one 20ms-ish PCM chunk
        ws.send_text(json.dumps({"type": "end"}))
        resp = ws.receive_json()
        assert resp["type"] == "response" and resp["text"] == "готово"

    # the node is registered, and identity was threaded into the pipeline call
    assert "kitchen_node" in get_client_registry().clients
    assert captured["client_context"]["client_id"] == "kitchen_node"
    assert captured["client_context"]["room_name"] == "Кухня"
    assert captured["client_context"]["skip_wake_word"] is True
