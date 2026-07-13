"""ARCH-15 PR-7 — config-driven outputs: the `[outputs]` config section + adapter gating."""

import json
from types import SimpleNamespace

import pytest

from locveil_voice.config.models import CoreConfig, OutputConfig
from locveil_voice.config.auto_registry import AutoSchemaRegistry
from locveil_voice.outputs.manager import OutputManager


def test_output_config_defaults():
    cfg = OutputConfig()
    assert cfg.console is True
    assert cfg.console_prefix == "📝 "
    assert cfg.web_push is True


def test_core_config_has_outputs_section():
    cfg = CoreConfig()
    assert isinstance(cfg.outputs, OutputConfig)


def test_outputs_is_an_auto_generated_schema_section():
    # The config-ui `[outputs]` editor renders from this auto-generated section (no hardcoding).
    order = AutoSchemaRegistry.get_section_order_and_titles()
    assert "outputs" in order["section_order"]
    assert order["section_titles"]["outputs"] == "📤 Output Channels"
    # placed right after inputs (core sections first)
    so = order["section_order"]
    assert so.index("outputs") == so.index("inputs") + 1
    assert AutoSchemaRegistry.get_section_model("outputs") is OutputConfig


def _app(web_push: bool):
    pytest.importorskip("fastapi")
    from fastapi import FastAPI
    from locveil_voice.runners.webapi_router import create_webapi_router

    outputs = SimpleNamespace(web_push=web_push)
    core = SimpleNamespace(output_manager=OutputManager(),
                           config=SimpleNamespace(outputs=outputs),
                           workflow_manager=None, component_manager=None, plugin_manager=None)
    app = FastAPI()
    app.include_router(create_webapi_router(core, asset_loader=None, web_input=None, start_time=0.0))
    return app


def test_ws_output_rejected_when_web_push_disabled():
    from fastapi.testclient import TestClient
    with TestClient(_app(web_push=False)).websocket_connect("/ws/output") as ws:
        ws.send_text(json.dumps({"client_id": "browser_abc"}))
        msg = ws.receive_json()
        assert msg["type"] == "error" and "unavailable" in msg["error"]


def test_ws_output_allowed_when_web_push_enabled():
    from fastapi.testclient import TestClient
    with TestClient(_app(web_push=True)).websocket_connect("/ws/output") as ws:
        ws.send_text(json.dumps({"client_id": "browser_abc"}))
        msg = ws.receive_json()
        assert msg["type"] == "connected" and msg["client_id"] == "browser_abc"
