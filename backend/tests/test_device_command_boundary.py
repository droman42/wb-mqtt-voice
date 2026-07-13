"""ARCH-8 PR-1 — the canonical-command boundary objects + the capturing fake bridge.

Covers the domain types (`DeviceCommand`/`RoomGroupCommand` in both fixture and
wire shapes), the catalog model's group/`group_defaults` queries (VWB-23), the
`CatalogService` lazy-refresh seam (ARCH-26), and the capturing DEVICE_COMMAND
output delivering end-to-end through the OutputManager's designated routing.
"""

import pytest

from locveil_voice.core.catalog_service import CatalogService
from locveil_voice.core.interfaces.output import DeliveryResult, OutputModality
from locveil_voice.intents.context_models import RequestContext
from locveil_voice.intents.device_catalog import (
    CatalogActionSpec,
    CatalogCapability,
    CatalogDevice,
    CatalogParamSpec,
    CatalogRoom,
    DeviceCatalog,
    ValueLabel,
)
from locveil_voice.intents.device_commands import (
    DEVICE_COMMAND_METADATA_KEY,
    DeviceCommand,
    GroupScope,
    RoomGroupCommand,
)
from locveil_voice.intents.models import IntentResult
from locveil_voice.outputs.device_command import OUTPUT_TYPE, CapturingDeviceCommandOutput
from locveil_voice.outputs.manager import OutputManager


# --- a hand-built catalog slice (bedroom, per the pinned golden's shapes) ----------------------

def _catalog() -> DeviceCatalog:
    power = CatalogCapability(name="power", group="light",
                              actions=(CatalogActionSpec("on"), CatalogActionSpec("off")))
    climate = CatalogCapability(
        name="climate", group="climate",
        actions=(CatalogActionSpec("on"), CatalogActionSpec("off"),
                 CatalogActionSpec("set_setpoint", params=(
                     CatalogParamSpec(name="temp", type="float", required=True,
                                      min=5.0, max=30.0, unit="°C"),))))
    scenario = CatalogCapability(
        name="scenario", group="scenario",
        actions=(CatalogActionSpec("set", params=(
            CatalogParamSpec(name="value", type="enum", required=True, values=(
                ValueLabel(wire="movie_vhs", canonical="movie_vhs",
                           labels={"ru": "Кино с видеокассеты"}),)),)),
                 CatalogActionSpec("off")))
    return DeviceCatalog(
        version="test-1",
        rooms=(CatalogRoom(id="bedroom", names={"ru": "Спальня"},
                           devices=("bedroom_spots", "bedroom_sconce", "bedroom_heating"),
                           group_defaults={"light": "bedroom_spots"}),),
        devices=(
            CatalogDevice(id="bedroom_spots", room="bedroom", names={"ru": "Споты"},
                          capabilities=(power,)),
            CatalogDevice(id="bedroom_sconce", room="bedroom", names={"ru": "Бра слева"},
                          aliases={"ru": ("ночники",)}, capabilities=(power,)),
            CatalogDevice(id="bedroom_heating", room="bedroom", names={"ru": "Обогрев"},
                          aliases={"ru": ("радиаторы",)}, capabilities=(climate,)),
            CatalogDevice(id="scenario_manager", room="bedroom", names={"ru": "Сценарии"},
                          capabilities=(scenario,)),
        ))


# --- command shapes ----------------------------------------------------------------------------

def test_device_command_fixture_and_wire_shapes():
    cmd = DeviceCommand(device_id="bedroom_heating", capability="climate",
                        action="set_setpoint", params={"temp": 22})
    assert cmd.to_dict() == {"kind": "actuate", "device_id": "bedroom_heating",
                             "capability": "climate", "action": "set_setpoint",
                             "params": {"temp": 22}}
    assert cmd.request_body() == {"capability": "climate", "action": "set_setpoint",
                                  "params": {"temp": 22}}


def test_room_group_command_fixture_and_wire_shapes():
    cmd = RoomGroupCommand(room_id="bedroom", group="light", action="off",
                           scope=GroupScope.ALL)
    assert cmd.to_dict() == {"kind": "room-group", "room_id": "bedroom",
                             "group": "light", "action": "off", "scope": "all"}
    # params omitted from the wire body when absent (RoomCanonicalRequest allows null)
    assert cmd.request_body() == {"group": "light", "action": "off", "scope": "all"}


def test_room_group_default_scope_is_auto():
    assert RoomGroupCommand(room_id="bedroom", group="cover", action="close").scope \
        is GroupScope.AUTO


# --- catalog model (VWB-23 queries) --------------------------------------------------------------

def test_group_members_follow_capability_group_tags():
    cat = _catalog()
    lights = cat.group_members("bedroom", "light")
    assert {d.id for d in lights} == {"bedroom_spots", "bedroom_sconce"}
    # the climate device is NOT reachable through the light group
    assert all(d.id != "bedroom_heating" for d in lights)


def test_group_default_and_surfaces():
    cat = _catalog()
    assert cat.group_default("bedroom", "light") == "bedroom_spots"
    assert cat.group_default("bedroom", "cover") is None
    assert cat.device("bedroom_heating").surfaces("ru") == ("Обогрев", "радиаторы")
    assert cat.room("bedroom").surfaces("ru") == ("Спальня",)


def test_typed_params_reachable_through_the_model():
    spec = (_catalog().device("bedroom_heating")
            .capability("climate").action("set_setpoint").param("temp"))
    assert spec is not None
    assert (spec.min, spec.max, spec.unit) == (5.0, 30.0, "°C")


# --- CatalogService (ARCH-26 lazy-refresh seam) --------------------------------------------------

async def test_service_serves_nothing_before_first_pull():
    svc = CatalogService()
    assert svc.catalog() is None
    assert await svc.refresh() is None  # no fetcher wired (pre-PR-2) → soft None


async def test_service_refresh_swaps_snapshot():
    cat = _catalog()

    async def fetch() -> DeviceCatalog:
        return cat

    svc = CatalogService(fetcher=fetch)
    assert await svc.refresh() is cat
    assert svc.catalog() is cat


async def test_service_refresh_failure_keeps_previous_snapshot():
    cat = _catalog()

    async def failing_fetch() -> DeviceCatalog:
        raise ConnectionError("bridge unreachable")

    svc = CatalogService(fetcher=failing_fetch)
    svc.set_catalog(cat)
    assert await svc.refresh() is None
    assert svc.catalog() is cat  # the last good snapshot survives


# --- the capturing fake bridge -------------------------------------------------------------------

def _command_result(cmd) -> IntentResult:
    return IntentResult(text="включаю", metadata={DEVICE_COMMAND_METADATA_KEY: cmd})


async def test_capture_returns_rich_echo():
    out = CapturingDeviceCommandOutput()
    cmd = DeviceCommand(device_id="bedroom_spots", capability="power", action="on")
    dr = await out.deliver(_command_result(cmd), RequestContext(source="test"),
                           OutputModality.DEVICE_COMMAND)
    assert out.captured == [cmd]
    assert dr.delivered and dr.error_code is None
    assert dr.echoed_value == cmd.to_dict()


async def test_capture_captures_both_address_forms():
    out = CapturingDeviceCommandOutput()
    device_form = DeviceCommand(device_id="bedroom_spots", capability="power", action="on")
    room_form = RoomGroupCommand(room_id="bedroom", group="light", action="on")
    for cmd in (device_form, room_form):
        await out.deliver(_command_result(cmd), RequestContext(source="test"),
                          OutputModality.DEVICE_COMMAND)
    assert out.captured == [device_form, room_form]
    assert [c.to_dict()["kind"] for c in out.captured] == ["actuate", "room-group"]


async def test_result_without_command_is_dropped_loudly():
    out = CapturingDeviceCommandOutput()
    dr = await out.deliver(IntentResult(text="oops"), RequestContext(source="test"),
                           OutputModality.DEVICE_COMMAND)
    assert dr.dropped and not dr.delivered
    assert DEVICE_COMMAND_METADATA_KEY in (dr.detail or "")
    assert out.captured == []


async def test_scripted_responder_drives_error_paths():
    def bridge_says_no(command) -> DeliveryResult:
        return DeliveryResult(output_name=OUTPUT_TYPE,
                              modality=OutputModality.DEVICE_COMMAND,
                              delivered=False, error_code="device_unreachable")

    out = CapturingDeviceCommandOutput(responder=bridge_says_no)
    cmd = DeviceCommand(device_id="bedroom_spots", capability="power", action="on")
    dr = await out.deliver(_command_result(cmd), RequestContext(source="test"),
                           OutputModality.DEVICE_COMMAND)
    assert out.captured == [cmd]  # still captured — the command WAS emitted
    assert not dr.delivered and dr.error_code == "device_unreachable"


# --- end-to-end through the OutputManager (D-2 designated routing) -------------------------------

async def test_designated_routing_delivers_command_to_the_capture_output():
    out = CapturingDeviceCommandOutput()
    mgr = OutputManager()
    await mgr.add_output(OUTPUT_TYPE, out)
    mgr.designate(OutputModality.DEVICE_COMMAND, OUTPUT_TYPE)

    cmd = RoomGroupCommand(room_id="bedroom", group="light", action="on")
    results = await mgr.deliver(_command_result(cmd), RequestContext(source="ws"),
                                OutputModality.DEVICE_COMMAND)
    assert len(results) == 1 and results[0].delivered
    assert results[0].echoed_value == cmd.to_dict()
    assert out.captured == [cmd]


async def test_undesignated_device_command_goes_nowhere():
    mgr = OutputManager()
    await mgr.add_output(OUTPUT_TYPE, CapturingDeviceCommandOutput())
    # no designate() → no target (never falls back to conversational routing)
    cmd = DeviceCommand(device_id="bedroom_spots", capability="power", action="on")
    results = await mgr.deliver(_command_result(cmd), RequestContext(source="ws"),
                                OutputModality.DEVICE_COMMAND)
    assert results == []
