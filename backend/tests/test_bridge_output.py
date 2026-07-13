"""ARCH-8 PR-2 — the BridgeClient adapter: catalog parsing, both actuation endpoints,
§5b error mapping, and the composition wiring (`setup_bridge_output`).

Adapter-level tests stub the one transport seam (`_request_json`) — the REST
contract shapes come from the pinned artifacts in `locveil-commons/contracts/`.
"""

from types import SimpleNamespace

import aiohttp
import pytest

from locveil_voice.config.models import BridgeOutputConfig, CoreConfig
from locveil_voice.core.catalog_service import CatalogService
from locveil_voice.core.interfaces.output import OutputModality
from locveil_voice.intents.context_models import RequestContext
from locveil_voice.intents.device_commands import (
    DEVICE_COMMAND_METADATA_KEY,
    DeviceCommand,
    GroupScope,
    RoomGroupCommand,
)
from locveil_voice.intents.models import IntentResult
from locveil_voice.outputs.manager import OutputManager
from locveil_voice.outputs.bridge import (
    BRIDGE_UNREACHABLE,
    BridgeClient,
    parse_catalog,
)
from locveil_voice.runners.composition import setup_bridge_output


# --- catalog parsing (golden-shaped payload, per the pinned CatalogResponse) ---------------------

CATALOG_PAYLOAD = {
    "version": "91909b54bfb4b593",
    "rooms": [
        {"id": "bedroom", "names": {"ru": "Спальня", "en": "Bedroom"},
         "aliases": None, "devices": ["bedroom_spots", "bedroom_heating"],
         "group_defaults": {"light": "bedroom_spots"}},
        {"id": "living_room", "names": {"ru": "Гостиная"},
         "aliases": {"ru": ["зал"]}, "devices": ["scenario_manager"],
         "group_defaults": None},
    ],
    "devices": [
        {"id": "bedroom_spots", "room": "bedroom", "names": {"ru": "Споты"},
         "aliases": None,
         "capabilities": [
             {"name": "power", "group": "light",
              "actions": [{"name": "on", "params": None}, {"name": "off", "params": None}]},
             {"name": "brightness", "group": "brightness",
              "actions": [{"name": "set", "params": [
                  {"name": "level", "type": "range", "required": True, "default": None,
                   "min": 0.0, "max": 100.0, "unit": "%", "values": None,
                   "options_from": None}]}]},
         ]},
        {"id": "bedroom_heating", "room": "bedroom", "names": {"ru": "Обогрев"},
         "aliases": {"ru": ["радиаторы"]},
         "capabilities": [
             {"name": "climate", "group": "climate",
              "actions": [{"name": "set_setpoint", "params": [
                  {"name": "temp", "type": "float", "required": True, "default": None,
                   "min": 5.0, "max": 30.0, "unit": "°C", "values": None,
                   "options_from": None}]}],
              "fields": [{"name": "room_temperature", "type": "float", "unit": "°C",
                          "labels": {"ru": "температура в комнате"}}]},
         ]},
        {"id": "scenario_manager", "room": "living_room", "names": {"ru": "Сценарии"},
         "capabilities": [
             {"name": "scenario", "group": "scenario",
              "actions": [{"name": "set", "params": [
                  {"name": "value", "type": "enum", "required": True, "default": None,
                   "min": None, "max": None, "unit": None,
                   "values": [{"wire": "movie_vhs", "canonical": "movie_vhs",
                               "labels": {"ru": "Кино с видеокассеты"}}],
                   "options_from": None}]}]},
             {"name": "apps", "group": "apps",
              "actions": [{"name": "launch", "params": [
                  {"name": "app", "type": "string", "required": True, "default": "YouTube",
                   "min": None, "max": None, "unit": None, "values": None,
                   "options_from": "apps"}]}]},
         ]},
    ],
}


def test_parse_catalog_full_shape():
    cat = parse_catalog(CATALOG_PAYLOAD)
    assert cat.version == "91909b54bfb4b593"
    # rooms: aliases + group_defaults (None → empty)
    assert cat.room("living_room").surfaces("ru") == ("Гостиная", "зал")
    assert cat.group_default("bedroom", "light") == "bedroom_spots"
    assert cat.group_default("living_room", "light") is None
    # group overlay drives group_members
    assert [d.id for d in cat.group_members("bedroom", "light")] == ["bedroom_spots"]
    # typed params: range with unit
    level = (cat.device("bedroom_spots").capability("brightness")
             .action("set").param("level"))
    assert (level.min, level.max, level.unit, level.required) == (0.0, 100.0, "%", True)
    # enum triplets
    value = (cat.device("scenario_manager").capability("scenario")
             .action("set").param("value"))
    assert value.values[0].canonical == "movie_vhs"
    assert value.values[0].labels["ru"] == "Кино с видеокассеты"
    # options_from (dynamic set) has no values
    app = (cat.device("scenario_manager").capability("apps")
           .action("launch").param("app"))
    assert app.options_from == "apps" and app.values is None
    # sensor fields with units + ru labels
    fld = cat.device("bedroom_heating").capability("climate").field_spec("room_temperature")
    assert fld.unit == "°C" and fld.labels["ru"] == "температура в комнате"
    # device aliases
    assert cat.device("bedroom_heating").surfaces("ru") == ("Обогрев", "радиаторы")


def test_parse_catalog_requires_version():
    with pytest.raises(KeyError):
        parse_catalog({"rooms": [], "devices": []})


# --- the transport-stubbed client ----------------------------------------------------------------

class StubBridge(BridgeClient):
    """BridgeClient with the one transport seam replaced by scripted responses."""

    def __init__(self, *responses):
        super().__init__("http://bridge.test:8000")
        self.requests = []
        self._responses = list(responses)

    async def _request_json(self, method, path, body=None):
        self.requests.append((method, path, body))
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _command_result(cmd) -> IntentResult:
    return IntentResult(text="включаю", metadata={DEVICE_COMMAND_METADATA_KEY: cmd})


_CTX = RequestContext(source="test")


async def test_device_form_posts_to_device_endpoint():
    bridge = StubBridge((200, {"success": True, "device_id": "bedroom_spots",
                               "capability": "power", "action": "on",
                               "state": {"power": "on"}, "error": None}))
    cmd = DeviceCommand(device_id="bedroom_spots", capability="power", action="on")
    dr = await bridge.deliver(_command_result(cmd), _CTX, OutputModality.DEVICE_COMMAND)
    assert bridge.requests == [("POST", "/devices/bedroom_spots/canonical",
                                {"capability": "power", "action": "on", "params": None})]
    assert dr.delivered and dr.error_code is None
    assert dr.echoed_value == {"power": "on"}


async def test_room_form_posts_to_room_endpoint_with_scope():
    member_results = [{"device_id": "bedroom_spots", "status": "executed"},
                      {"device_id": "bedroom_sconce", "status": "no_op"}]
    bridge = StubBridge((200, {"success": True, "room_id": "bedroom", "group": "light",
                               "action": "on", "scope_applied": "fan_out",
                               "results": member_results, "error": None}))
    cmd = RoomGroupCommand(room_id="bedroom", group="light", action="on",
                           scope=GroupScope.ALL)
    dr = await bridge.deliver(_command_result(cmd), _CTX, OutputModality.DEVICE_COMMAND)
    assert bridge.requests == [("POST", "/rooms/bedroom/canonical",
                                {"group": "light", "action": "on", "scope": "all"})]
    # the per-member aggregate rides echoed_value — PR-4 speaks partial failures from it
    assert dr.delivered and dr.echoed_value == member_results


async def test_structured_error_maps_to_error_code_and_detail():
    bridge = StubBridge((400, {"success": False, "device_id": "bedroom_spots",
                               "error": {"code": "param_invalid", "message": "out of range",
                                         "field": "level", "reason": "out_of_range"}}))
    cmd = DeviceCommand(device_id="bedroom_spots", capability="brightness",
                        action="set", params={"level": 250})
    dr = await bridge.deliver(_command_result(cmd), _CTX, OutputModality.DEVICE_COMMAND)
    assert not dr.delivered
    assert dr.error_code == "param_invalid"
    assert "field=level" in dr.detail and "reason=out_of_range" in dr.detail


async def test_unstructured_failure_becomes_internal_error():
    bridge = StubBridge((500, {"detail": "boom"}))
    cmd = DeviceCommand(device_id="x", capability="power", action="on")
    dr = await bridge.deliver(_command_result(cmd), _CTX, OutputModality.DEVICE_COMMAND)
    assert not dr.delivered and dr.error_code == "internal_error"


# BUG-40: on non-2xx the real bridge raises HTTPException(detail=resp.model_dump()), so the
# canonical body arrives one level down in FastAPI's `detail` envelope — the adapter must unwrap.

def _wrapped_error(code: str, message: str, **extra) -> dict:
    return {"detail": {"success": False, "capability": "power", "action": "on",
                       "error": {"code": code, "message": message, **extra},
                       "no_op": False, "skipped_reason": None}}


@pytest.mark.parametrize("status,code", [
    (400, "param_invalid"),
    (400, "capability_not_supported"),
    (404, "device_not_found"),
    (503, "device_unreachable"),
    (500, "internal_error"),
])
async def test_wrapped_canonical_error_unwraps_fastapi_detail(status, code):
    bridge = StubBridge((status, _wrapped_error(code, "nope")))
    cmd = DeviceCommand(device_id="x", capability="power", action="on")
    dr = await bridge.deliver(_command_result(cmd), _CTX, OutputModality.DEVICE_COMMAND)
    assert not dr.delivered
    assert dr.error_code == code
    assert "nope" in (dr.detail or "")


async def test_wrapped_param_invalid_carries_field_and_reason():
    bridge = StubBridge((400, _wrapped_error("param_invalid", "out of range",
                                             field="value", reason="out_of_range")))
    cmd = DeviceCommand(device_id="children_room_hvac", capability="temperature",
                        action="set", params={"value": 42})
    dr = await bridge.deliver(_command_result(cmd), _CTX, OutputModality.DEVICE_COMMAND)
    assert not dr.delivered and dr.error_code == "param_invalid"
    assert "field=value" in dr.detail and "reason=out_of_range" in dr.detail


async def test_transport_failure_is_spoken_not_raised():
    bridge = StubBridge(aiohttp.ClientConnectionError("refused"))
    cmd = DeviceCommand(device_id="x", capability="power", action="on")
    dr = await bridge.deliver(_command_result(cmd), _CTX, OutputModality.DEVICE_COMMAND)
    assert not dr.delivered and dr.error_code == BRIDGE_UNREACHABLE


async def test_result_without_command_is_dropped():
    bridge = StubBridge()
    dr = await bridge.deliver(IntentResult(text="oops"), _CTX, OutputModality.DEVICE_COMMAND)
    assert dr.dropped and bridge.requests == []


async def test_fetch_catalog_parses_and_raises_on_http_error():
    bridge = StubBridge((200, CATALOG_PAYLOAD), (503, {"detail": "starting"}))
    cat = await bridge.fetch_catalog()
    assert cat.version == "91909b54bfb4b593"
    assert bridge.requests[0] == ("GET", "/system/catalog", None)
    with pytest.raises(RuntimeError):
        await bridge.fetch_catalog()


# --- composition wiring (setup_bridge_output) ----------------------------------------------------

def _core(enabled: bool):
    config = CoreConfig()
    config.outputs.bridge.enabled = enabled
    return SimpleNamespace(config=config, output_manager=OutputManager(),
                           catalog_service=CatalogService())


async def test_setup_disabled_registers_nothing():
    core = _core(enabled=False)
    await setup_bridge_output(core)
    assert core.output_manager.select(OutputModality.DEVICE_COMMAND, _CTX) == []
    assert core.catalog_service.catalog() is None


async def test_setup_enabled_registers_designates_and_pulls(monkeypatch):
    core = _core(enabled=True)

    async def fake_fetch(self):
        return parse_catalog(CATALOG_PAYLOAD)

    monkeypatch.setattr(BridgeClient, "fetch_catalog", fake_fetch)
    monkeypatch.setattr(BridgeClient, "start", _noop_start)
    await setup_bridge_output(core)

    targets = core.output_manager.select(OutputModality.DEVICE_COMMAND, _CTX)
    assert len(targets) == 1 and targets[0].get_output_type() == "bridge"
    # the startup pull landed through the wired fetcher
    assert core.catalog_service.catalog().version == "91909b54bfb4b593"


async def test_setup_survives_bridge_down_at_startup(monkeypatch):
    core = _core(enabled=True)

    async def failing_fetch(self):
        raise aiohttp.ClientConnectionError("refused")

    monkeypatch.setattr(BridgeClient, "fetch_catalog", failing_fetch)
    monkeypatch.setattr(BridgeClient, "start", _noop_start)
    await setup_bridge_output(core)

    # the actuation channel is registered even though the catalog pull failed —
    # the ARCH-26 lazy refresh retries on first use
    targets = core.output_manager.select(OutputModality.DEVICE_COMMAND, _CTX)
    assert len(targets) == 1
    assert core.catalog_service.catalog() is None


async def _noop_start(self):
    return None


def test_bridge_config_defaults():
    cfg = BridgeOutputConfig()
    assert cfg.enabled is False
    assert cfg.base_url == "http://localhost:8000"
    # BUG-41: must exceed the bridge's slowest gated echo-wait (HVAC confirms up to ~15 s)
    assert cfg.timeout_seconds == 20.0


async def test_get_device_options_success_and_failure():
    bridge = StubBridge((200, {"success": True, "data": ["cd", "aux1", "phono"]}),
                        (404, {"success": False, "detail": "no such option set"}),
                        aiohttp.ClientConnectionError("refused"))
    assert await bridge.get_device_options("mf_amplifier", "inputs") == ["cd", "aux1", "phono"]
    assert bridge.requests[0] == ("GET", "/devices/mf_amplifier/options/inputs", None)
    assert await bridge.get_device_options("mf_amplifier", "nope") is None
    assert await bridge.get_device_options("mf_amplifier", "inputs") is None  # transport down


async def test_fetch_report_evidence_all_outcomes_never_raise():
    envelope = {"generated_at": "2026-07-06T12:00:00Z", "bridge": {"version": "1.4"}}
    bridge = StubBridge((200, envelope),
                        (429, {"detail": "rate limited"}),
                        (500, {"detail": "boom"}),
                        aiohttp.ClientConnectionError("refused"))
    assert await bridge.fetch_report_evidence() == {"status": "attached", "envelope": envelope}
    assert bridge.requests[0] == ("GET", "/reports/evidence", None)
    assert (await bridge.fetch_report_evidence())["status"] == "rate_limited"
    out = await bridge.fetch_report_evidence()
    assert out["status"] == "error" and out["http_status"] == 500
    out = await bridge.fetch_report_evidence()
    assert out["status"] == "unreachable" and "refused" in out["error"]
