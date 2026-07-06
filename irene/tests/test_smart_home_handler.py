"""ARCH-8 PR-4 — the smart-home handler end-to-end (minus ASR/NLU phrase matching).

Each test mirrors a crossover fixture (`eval-commons/contracts/crossover_fixtures.json`):
extracted params go through the REAL ContextualEntityResolver (PR-3, Q7b declarative dispatch
against the real smart_home donation), then the REAL handler, dispatcher, OutputManager and
the capturing fake bridge — asserting the captured canonical command equals the fixture's
`expect` and the spoken text is sane. The full utterance→command suite (with NLU) is TEST-18
Slice B; this is the handler-level acceptance PR-4 builds against.
"""

from pathlib import Path

import pytest

from irene.core.catalog_service import CatalogService
from irene.core.device_command_dispatcher import DeviceCommandDispatcher
from irene.core.entity_resolver import ContextualEntityResolver
from irene.core.intent_asset_loader import AssetLoaderConfig, IntentAssetLoader
from irene.core.interfaces.output import DeliveryResult, OutputModality
from irene.intents.context_models import UnifiedConversationContext
from irene.intents.handlers.smart_home import SmartHomeIntentHandler
from irene.intents.models import Intent
from irene.outputs.device_command import OUTPUT_TYPE, CapturingDeviceCommandOutput
from irene.outputs.manager import OutputManager

# a golden-shaped house slice: every capability kind the fixtures exercise
CATALOG_PAYLOAD = {
    "version": "test-house-1",
    "rooms": [
        {"id": "bedroom", "names": {"ru": "Спальня"}, "devices": [],
         "group_defaults": {"light": "bedroom_spots"}},
        {"id": "children_room", "names": {"ru": "Детская"}, "devices": [],
         "group_defaults": {"light": "children_room_spots"}},
        {"id": "living_room", "names": {"ru": "Гостиная"}, "aliases": {"ru": ["зал"]},
         "devices": [], "group_defaults": {"light": "living_room_spots"}},
        {"id": "cabinet", "names": {"ru": "Кабинет"}, "devices": []},
        {"id": "kitchen", "names": {"ru": "Кухня"}, "devices": []},
        {"id": "shower", "names": {"ru": "Душевая"}, "devices": []},
        {"id": "global", "names": {"ru": "Весь дом"}, "aliases": {"ru": ["квартира"]},
         "devices": []},
    ],
    "devices": [
        {"id": "children_room_tv", "room": "children_room", "names": {"ru": "Телевизор"},
         "aliases": {"ru": ["телек"]},
         "capabilities": [
             {"name": "power", "group": "power", "actions": [{"name": "on"}, {"name": "off"}]},
             {"name": "playback", "group": "playback",
              "actions": [{"name": "play"}, {"name": "pause"}, {"name": "stop"}]},
             {"name": "input", "group": "input",
              "actions": [{"name": "set", "params": [
                  {"name": "value", "type": "string", "required": True,
                   "options_from": "inputs"}]}]},
             {"name": "apps", "group": "apps",
              "actions": [{"name": "launch", "params": [
                  {"name": "app", "type": "string", "required": True,
                   "options_from": "apps"}]}]}]},
        {"id": "appletv_children", "room": "children_room", "names": {"ru": "Apple TV"},
         "aliases": {"ru": ["эппл"]},
         "capabilities": [
             {"name": "power", "group": "power", "actions": [{"name": "on"}, {"name": "off"}]},
             {"name": "playback", "group": "playback",
              "actions": [{"name": "play"}, {"name": "pause"}]}]},
        {"id": "appletv_living", "room": "living_room", "names": {"ru": "Apple TV"},
         "aliases": {"ru": ["эппл"]},
         "capabilities": [
             {"name": "power", "group": "power", "actions": [{"name": "on"}, {"name": "off"}]}]},
        {"id": "children_room_spots", "room": "children_room", "names": {"ru": "Споты"},
         "capabilities": [
             {"name": "power", "group": "light", "actions": [{"name": "on"}, {"name": "off"}]},
             {"name": "brightness", "group": "brightness",
              "actions": [{"name": "set", "params": [
                  {"name": "level", "type": "range", "required": True,
                   "min": 0.0, "max": 100.0, "unit": "%"}]}]}]},
        {"id": "bedroom_spots", "room": "bedroom", "names": {"ru": "Споты"},
         "capabilities": [
             {"name": "power", "group": "light", "actions": [{"name": "on"}, {"name": "off"}]}]},
        {"id": "bedroom_sconce", "room": "bedroom", "names": {"ru": "Бра"},
         "capabilities": [
             {"name": "power", "group": "light", "actions": [{"name": "on"}, {"name": "off"}]}]},
        {"id": "bedroom_heating", "room": "bedroom", "names": {"ru": "Обогрев"},
         "aliases": {"ru": ["радиаторы"]},
         "capabilities": [
             {"name": "climate", "group": "climate",
              "actions": [{"name": "on"}, {"name": "off"},
                          {"name": "set_setpoint", "params": [
                              {"name": "temp", "type": "float", "required": True,
                               "min": 5.0, "max": 30.0, "unit": "°C"}]}],
              "fields": [{"name": "setpoint", "unit": "°C"},
                         {"name": "room_temperature", "unit": "°C"}]}]},
        {"id": "bedroom_hvac", "room": "bedroom", "names": {"ru": "Кондиционер"},
         "aliases": {"ru": ["кондей"]},
         "capabilities": [
             {"name": "climate", "group": "climate",
              "actions": [{"name": "on"}, {"name": "off"},
                          {"name": "set_setpoint", "params": [
                              {"name": "temp", "type": "float", "required": True,
                               "min": 16.0, "max": 31.0, "unit": "°C"}]}],
              "fields": [{"name": "temperature", "unit": "°C",
                          "labels": {"ru": "уставка"}},
                         {"name": "room_temperature", "unit": "°C"}]}]},
        {"id": "mf_amplifier", "room": "living_room", "names": {"ru": "Усилитель"},
         "capabilities": [
             {"name": "input", "group": "input",
              "actions": [{"name": "set", "params": [
                  {"name": "value", "type": "enum", "required": True,
                   "values": [{"wire": "cd", "canonical": "cd", "labels": None},
                              {"wire": "aux1", "canonical": "aux1", "labels": None},
                              {"wire": "phono", "canonical": "phono", "labels": None}]}]}]}]},
        {"id": "living_room_spots", "room": "living_room", "names": {"ru": "Споты"},
         "capabilities": [
             {"name": "power", "group": "light", "actions": [{"name": "on"}, {"name": "off"}]}]},
        {"id": "living_room_curtain_left", "room": "living_room", "names": {"ru": "Штора слева"},
         "aliases": {"ru": ["шторы"]},
         "capabilities": [
             {"name": "cover", "group": "cover",
              "actions": [{"name": "open"}, {"name": "close"}]}]},
        {"id": "living_room_tulle_left", "room": "living_room", "names": {"ru": "Тюль слева"},
         "capabilities": [
             {"name": "cover", "group": "cover",
              "actions": [{"name": "open"}, {"name": "close"}]}]},
        {"id": "cabinet_roller_left", "room": "cabinet", "names": {"ru": "Левый ролл"},
         "aliases": {"ru": ["жалюзи"]},
         "capabilities": [
             {"name": "cover", "group": "cover",
              "actions": [{"name": "open"}, {"name": "close"}]}]},
        {"id": "cabinet_roller_right", "room": "cabinet", "names": {"ru": "Правый ролл"},
         "aliases": {"ru": ["жалюзи"]},
         "capabilities": [
             {"name": "cover", "group": "cover",
              "actions": [{"name": "open"}, {"name": "close"}]}]},
        {"id": "all_lights", "room": "global", "names": {"ru": "Весь свет"},
         "capabilities": [
             {"name": "power", "group": "light", "actions": [{"name": "on"}, {"name": "off"}]}]},
        {"id": "all_plugs", "room": "global", "names": {"ru": "Розетки"},
         "capabilities": [
             {"name": "power", "group": "power", "actions": [{"name": "on"}, {"name": "off"}]}]},
        {"id": "kitchen_hood", "room": "kitchen", "names": {"ru": "Вытяжка"},
         "capabilities": [
             {"name": "fan", "group": "fan",
              "actions": [{"name": "set", "params": [
                  {"name": "level", "type": "range", "required": True,
                   "min": 0.0, "max": 4.0}]}, {"name": "off"}]}]},
        {"id": "shower_sauna_sensors", "room": "shower", "names": {"ru": "Сенсоры сауны"},
         "capabilities": [
             {"name": "sensor", "group": "sensor",
              "fields": [{"name": "temperature", "unit": "°C"},
                         {"name": "humidity", "unit": "%"}]}]},
        {"id": "video", "room": "living_room", "names": {"ru": "Заппити"},
         "aliases": {"ru": ["заппити"]},
         "capabilities": [
             {"name": "playback", "group": "playback",
              "actions": [{"name": "play_pause"}, {"name": "stop"}, {"name": "next"}]}]},
        {"id": "scenario_manager", "room": "living_room", "names": {"ru": "Сценарии"},
         "capabilities": [
             {"name": "scenario", "group": "scenario",
              "actions": [{"name": "set", "params": [
                  {"name": "value", "type": "enum", "required": True,
                   "values": [
                       {"wire": "movie_vhs", "canonical": "movie_vhs",
                        "labels": {"ru": "Кино с видеокассеты"}},
                       {"wire": "movie_appletv", "canonical": "movie_appletv",
                        "labels": {"ru": "Кино с Apple TV"}}]}]},
                          {"name": "off"}]}]},
    ],
}


@pytest.fixture(scope="module")
async def loader():
    ldr = IntentAssetLoader(Path("assets"), AssetLoaderConfig(strict_mode=True))
    await ldr.load_all_assets(["smart_home"])
    assert ldr.get_donation("smart_home") is not None, "smart_home donation failed to load"
    return ldr


class Harness:
    """The PR-4 vertical slice minus NLU: resolver → handler → dispatcher → capturing bridge."""

    def __init__(self, loader, responder=None):
        from irene.outputs.bridge import parse_catalog
        self.catalog_service = CatalogService()
        self.catalog_service.set_catalog(parse_catalog(CATALOG_PAYLOAD))
        self.capture = CapturingDeviceCommandOutput(responder=responder)
        self.state_reads: list = []

        async def read_state(device_id: str):
            self.state_reads.append(device_id)
            return {"temperature": 23.5, "humidity": 41.0,
                    "room_temperature": 22.4, "setpoint": 22.0}

        self.catalog_service.set_state_reader(read_state)
        self.options_reads: list = []

        async def read_options(device_id: str, kind: str):
            self.options_reads.append((device_id, kind))
            return {"inputs": ["hdmi1", "hdmi2", "av"],
                    "apps": ["YouTube", "Netflix", "Кинопоиск"]}.get(kind)

        self.catalog_service.set_options_reader(read_options)
        self.output_manager = OutputManager()
        self.resolver = ContextualEntityResolver(loader, catalog_port=self.catalog_service)
        self.handler = SmartHomeIntentHandler()
        self.handler.donation = loader.get_donation("smart_home")
        self.handler._donation_initialized = True
        self.handler.asset_loader = loader
        self.handler._asset_loader_initialized = True
        self.handler.set_device_command_services(
            self.catalog_service, DeviceCommandDispatcher(self.output_manager))

    async def start(self):
        await self.output_manager.add_output(OUTPUT_TYPE, self.capture)
        self.output_manager.designate(OutputModality.DEVICE_COMMAND, OUTPUT_TYPE)
        return self

    async def run(self, suffix: str, raw_text: str, entities: dict,
                  room: str | None = None) -> tuple:
        """Resolve entities (real PR-3 pass), execute the handler, return (result, captured)."""
        context = UnifiedConversationContext(session_id="s", room_name=room, language="ru")
        intent = Intent(name=f"smart_home.{suffix}", entities=dict(entities),
                        confidence=1.0, raw_text=raw_text, domain="smart_home")
        intent.entities = await self.resolver.resolve_entities(intent, context)
        result = await self.handler.execute(intent, context)
        return result, [c.to_dict() for c in self.capture.captured]


@pytest.fixture
async def harness(loader):
    return await Harness(loader).start()


# --- device-form fixtures -------------------------------------------------------------------------

async def test_f01_power_on_named_device(harness):
    result, captured = await harness.run("power_on", "включи телек",
                                         {"target": "телек"}, room="Детская")
    assert captured == [{"kind": "actuate", "device_id": "children_room_tv",
                         "capability": "power", "action": "on", "params": None}]
    assert result.success and "Телевизор" in result.text


async def test_f02_power_off_alias_room_disambiguated(harness):
    result, captured = await harness.run("power_off", "выключи эппл",
                                         {"target": "эппл"}, room="Гостиная")
    assert captured == [{"kind": "actuate", "device_id": "appletv_living",
                         "capability": "power", "action": "off", "params": None}]


async def test_f04_aggregate_is_a_device(harness):
    result, captured = await harness.run("power_off", "выключи розетки",
                                         {"target": "розетки"})
    assert captured == [{"kind": "actuate", "device_id": "all_plugs",
                         "capability": "power", "action": "off", "params": None}]


async def test_f05_setpoint_on_named_device(harness):
    result, captured = await harness.run("set_setpoint", "поставь на радиаторах 22 градуса",
                                         {"target": "радиаторах", "temp": 22.0},
                                         room="Спальня")
    assert captured == [{"kind": "actuate", "device_id": "bedroom_heating",
                         "capability": "climate", "action": "set_setpoint",
                         "params": {"temp": 22.0}}]


async def test_f07_brightness_single_capable_in_room(harness):
    result, captured = await harness.run("set_brightness", "сделай яркость 30 процентов",
                                         {"level": 30}, room="Детская")
    assert captured == [{"kind": "actuate", "device_id": "children_room_spots",
                         "capability": "brightness", "action": "set",
                         "params": {"level": 30}}]


async def test_f08_named_device_stays_device_form(harness):
    # depth doctrine: «тюль слева» is a NAME — device form even though the room has a cover group
    result, captured = await harness.run("cover_close", "закрой тюль слева",
                                         {"target": "тюль слева"}, room="Гостиная")
    assert captured == [{"kind": "actuate", "device_id": "living_room_tulle_left",
                         "capability": "cover", "action": "close", "params": None}]


# --- room-group fixtures (VWB-23) ------------------------------------------------------------------

async def test_f10_bare_light_noun_goes_room_form(harness):
    result, captured = await harness.run("power_on", "включи свет в детской",
                                         {"group_noun": "light", "room": "детской"})
    assert captured == [{"kind": "room-group", "room_id": "children_room",
                         "group": "light", "action": "on", "scope": "auto"}]
    assert result.success


async def test_f11_context_room_when_none_mentioned(harness):
    result, captured = await harness.run("power_off", "выключи свет",
                                         {"group_noun": "light"}, room="Спальня")
    assert captured == [{"kind": "room-group", "room_id": "bedroom",
                         "group": "light", "action": "off", "scope": "auto"}]


async def test_f12_ves_signals_scope_all(harness):
    result, captured = await harness.run("power_off", "выключи весь свет в спальне",
                                         {"group_noun": "light", "room": "спальне"})
    assert captured == [{"kind": "room-group", "room_id": "bedroom",
                         "group": "light", "action": "off", "scope": "all"}]


async def test_f14_global_room_alias(harness):
    result, captured = await harness.run("power_off", "выключи весь свет в квартире",
                                         {"group_noun": "light", "room": "квартире"})
    assert captured == [{"kind": "room-group", "room_id": "global",
                         "group": "light", "action": "off", "scope": "all"}]


async def test_f15_cover_noun_goes_room_form(harness):
    # «шторы» is BOTH a device alias and a group noun — the group noun wins (depth doctrine)
    result, captured = await harness.run("cover_close", "закрой шторы",
                                         {"group_noun": "cover"}, room="Гостиная")
    assert captured == [{"kind": "room-group", "room_id": "living_room",
                         "group": "cover", "action": "close", "scope": "auto"}]


async def test_f16_jalousie_room_form(harness):
    result, captured = await harness.run("cover_open", "подними жалюзи",
                                         {"group_noun": "cover"}, room="Кабинет")
    assert captured == [{"kind": "room-group", "room_id": "cabinet",
                         "group": "cover", "action": "open", "scope": "auto"}]


async def test_depth_doctrine_false_positive_noun_rejected(harness):
    # the CHOICE fuzzy layer may flag «подсветку» as the light group; the word-boundary
    # verification must reject it and keep the named-device path (here: unresolvable → spoken miss)
    result, captured = await harness.run("power_on", "включи подсветку потолка",
                                         {"group_noun": "light", "target": "подсветку потолка"},
                                         room="Детская")
    assert captured == []  # no room-group command was emitted
    assert not result.success and "подсветку потолка" in result.text


# --- clarifications (v1 ambiguity policy; QUAL-63 adds priorities later) ---------------------------

async def test_f20_playback_ambiguity_clarifies(harness):
    result, captured = await harness.run("playback_pause", "поставь на паузу", {},
                                         room="Детская")
    assert captured == []
    assert result.metadata.get("clarification") is True
    assert set(result.metadata.get("candidates", [])) == {"children_room_tv", "appletv_children"}


async def test_f21_climate_ambiguity_clarifies(harness):
    result, captured = await harness.run("set_setpoint", "поставь 22 градуса",
                                         {"temp": 22.0}, room="Спальня")
    assert captured == []
    assert result.metadata.get("clarification") is True
    assert set(result.metadata.get("candidates", [])) == {"bedroom_heating", "bedroom_hvac"}


async def test_setpoint_out_of_range_pre_validates(harness):
    result, captured = await harness.run("set_setpoint", "поставь на радиаторах 99 градусов",
                                         {"target": "радиаторах", "temp": 99.0},
                                         room="Спальня")
    assert captured == []  # §5b: contract-backed pre-validation, no round-trip
    assert result.metadata.get("clarification") is True
    assert "5" in result.text and "30" in result.text


# --- scenarios (device form, QUAL-29 label→canonical) ----------------------------------------------

async def test_f40_scenario_by_ru_label(harness):
    result, captured = await harness.run("scenario_start", "включи кино с видеокассеты", {},
                                         room="Гостиная")
    assert captured == [{"kind": "actuate", "device_id": "scenario_manager",
                         "capability": "scenario", "action": "set",
                         "params": {"value": "movie_vhs"}}]
    assert "Кино с видеокассеты" in result.text


async def test_f42_scenario_off(harness):
    result, captured = await harness.run("scenario_stop", "выключи кино", {},
                                         room="Гостиная")
    assert captured == [{"kind": "actuate", "device_id": "scenario_manager",
                         "capability": "scenario", "action": "off", "params": None}]


# --- delivery outcomes → speech (§5b + §10.4) ------------------------------------------------------

async def test_partial_aggregate_names_failed_members(loader):
    def partial_responder(command):
        return DeliveryResult.ok(OUTPUT_TYPE, OutputModality.DEVICE_COMMAND,
                                 echoed_value=[
                                     {"device_id": "bedroom_spots", "status": "executed"},
                                     {"device_id": "bedroom_sconce", "status": "failed"}])
    h = await Harness(loader, responder=partial_responder).start()
    result, captured = await h.run("power_on", "включи весь свет",
                                   {"group_noun": "light"}, room="Спальня")
    assert captured and captured[0]["scope"] == "all"
    assert "не ответили" in result.text and "Бра" in result.text


async def test_bridge_error_code_becomes_speech(loader):
    def unreachable(command):
        return DeliveryResult(output_name=OUTPUT_TYPE, modality=OutputModality.DEVICE_COMMAND,
                              delivered=False, error_code="device_unreachable")
    h = await Harness(loader, responder=unreachable).start()
    result, _ = await h.run("power_on", "включи телек", {"target": "телек"}, room="Детская")
    assert not result.success
    assert "не отвечает" in result.text


async def test_no_designated_output_speaks_degraded(loader):
    h = Harness(loader)  # NOT started: no designated DEVICE_COMMAND output (bridge disabled)
    result, _ = await h.run("power_on", "включи телек", {"target": "телек"}, room="Детская")
    assert not result.success
    assert "Не уверена" in result.text


async def test_no_catalog_speaks_not_connected(loader):
    h = await Harness(loader).start()
    h.catalog_service._catalog = None  # bridge never reachable
    context = UnifiedConversationContext(session_id="s", room_name="Детская", language="ru")
    intent = Intent(name="smart_home.power_on", entities={"target": "телек"},
                    confidence=1.0, raw_text="включи телек", domain="smart_home")
    result = await h.handler.execute(intent, context)
    assert not result.success and "не подключён" in result.text


# --- reads (ARCH-8 PR-5, §5c) -----------------------------------------------------------------

async def test_f30_temperature_prefers_dedicated_sensor(harness):
    result, captured = await harness.run("read_state", "какая температура в душевой",
                                         {"quantity": "temperature", "room": "душевой"})
    assert captured == []  # a read never actuates
    assert harness.state_reads == ["shower_sauna_sensors"]
    assert result.metadata["read"] == {"device_id": "shower_sauna_sensors",
                                       "capability": "sensor", "field": "temperature",
                                       "value": 23.5}
    assert "23.5" in result.text


async def test_f31_humidity(harness):
    result, _ = await harness.run("read_state", "какая влажность в душевой",
                                  {"quantity": "humidity", "room": "душевой"})
    assert result.metadata["read"]["field"] == "humidity"
    assert "41" in result.text


async def test_f32_room_temperature_not_setpoint(harness):
    # bedroom has NO dedicated sensor; both climate devices carry room_temperature —
    # and the hvac's bare `temperature` field is the SETPOINT, which must NOT be read
    result, _ = await harness.run("read_state", "какая температура в спальне",
                                  {"quantity": "temperature", "room": "спальне"})
    read = result.metadata["read"]
    assert read["device_id"] in ("bedroom_heating", "bedroom_hvac")
    assert read["field"] == "room_temperature"
    assert "22.4" in result.text


async def test_read_no_sensor_speaks_miss(harness):
    result, _ = await harness.run("read_state", "какая влажность в кабинете",
                                  {"quantity": "humidity", "room": "кабинете"})
    # no humidity field in cabinet → house-wide fallback finds the shower sensors
    assert result.metadata["read"]["device_id"] == "shower_sauna_sensors"


async def test_read_state_failure_degrades(loader):
    h = await Harness(loader).start()

    async def broken(device_id: str):
        return None

    h.catalog_service.set_state_reader(broken)
    result, _ = await h.run("read_state", "какая температура в душевой",
                            {"quantity": "temperature", "room": "душевой"})
    assert not result.success and "Не уверена" in result.text


# --- select-form capabilities (QUAL-65, VWB-19) --------------------------------------------------

async def test_f50_by_value_input_validates_offline(harness):
    result, captured = await harness.run("input_select", "переключи усилитель на cd",
                                         {"target": "усилитель", "value": "cd"},
                                         room="Гостиная")
    assert captured == [{"kind": "actuate", "device_id": "mf_amplifier",
                         "capability": "input", "action": "set",
                         "params": {"value": "cd"}}]
    assert harness.options_reads == []  # by_value: static values, zero round-trips


async def test_f51_parametric_input_enumerates_at_runtime(harness):
    result, captured = await harness.run("input_select", "переключи телек на hdmi1",
                                         {"target": "телек", "value": "hdmi1"},
                                         room="Детская")
    assert captured == [{"kind": "actuate", "device_id": "children_room_tv",
                         "capability": "input", "action": "set",
                         "params": {"value": "hdmi1"}}]
    assert ("children_room_tv", "inputs") in harness.options_reads


async def test_f52_app_launch_matches_case_insensitively(harness):
    result, captured = await harness.run("app_launch", "запусти youtube на телеке",
                                         {"app": "youtube", "target": "телеке"},
                                         room="Детская")
    assert captured == [{"kind": "actuate", "device_id": "children_room_tv",
                         "capability": "apps", "action": "launch",
                         "params": {"app": "YouTube"}}]
    assert "YouTube" in result.text


async def test_unknown_option_clarifies_naming_the_set(harness):
    result, captured = await harness.run("input_select", "переключи усилитель на кассету",
                                         {"target": "усилитель", "value": "кассету"},
                                         room="Гостиная")
    assert captured == []
    assert result.metadata.get("clarification") is True
    assert "cd" in result.text  # the available set is spoken


async def test_options_fetch_failure_degrades(loader):
    h = await Harness(loader).start()

    async def broken(device_id: str, kind: str):
        return None

    h.catalog_service.set_options_reader(broken)
    result, captured = await h.run("input_select", "переключи телек на hdmi1",
                                   {"target": "телек", "value": "hdmi1"}, room="Детская")
    assert captured == []
    assert not result.success and "список" in result.text


async def test_options_cache_avoids_refetch(harness):
    for _ in range(2):
        await harness.run("app_launch", "запусти netflix на телеке",
                          {"app": "netflix", "target": "телеке"}, room="Детская")
    apps_reads = [r for r in harness.options_reads if r[1] == "apps"]
    assert len(apps_reads) == 1  # second command served from the 30s TTL cache


# --- transliteration-tolerant matching (QUAL-35 Slice 1) -----------------------------------------

async def test_f53_app_spoken_in_cyrillic(harness):
    # «ютуб» ↔ "YouTube": the option's Cyrillic pronunciation hint closes the alphabet gap
    result, captured = await harness.run("app_launch", "запусти ютуб на телеке",
                                         {"app": "ютуб", "target": "телеке"}, room="Детская")
    assert captured == [{"kind": "actuate", "device_id": "children_room_tv",
                         "capability": "apps", "action": "launch",
                         "params": {"app": "YouTube"}}]


async def test_app_netflix_spoken_in_cyrillic(harness):
    result, captured = await harness.run("app_launch", "запусти нетфликс на телеке",
                                         {"app": "нетфликс", "target": "телеке"}, room="Детская")
    assert captured and captured[0]["params"] == {"app": "Netflix"}


async def test_f41_scenario_label_with_latin_name(harness):
    # «эппл ти ви» ↔ label «Кино с Apple TV» (acronym TV spelled «ти ви» in the hint)
    result, captured = await harness.run("scenario_start", "включи кино с эппл ти ви", {},
                                         room="Гостиная")
    assert captured == [{"kind": "actuate", "device_id": "scenario_manager",
                         "capability": "scenario", "action": "set",
                         "params": {"value": "movie_appletv"}}]
    assert "Apple TV" in result.text


# --- Slice 2 Part A ------------------------------------------------------------------------------

async def test_power_verb_reaches_climate(harness):
    result, captured = await harness.run("power_on", "включи обогрев",
                                         {"target": "обогрев"}, room="Спальня")
    assert captured == [{"kind": "actuate", "device_id": "bedroom_heating",
                         "capability": "climate", "action": "on", "params": None}]


async def test_power_verb_reaches_hood_fan(harness):
    result, captured = await harness.run("power_on", "включи вытяжку",
                                         {"target": "вытяжку"}, room="Кухня")
    assert captured == [{"kind": "actuate", "device_id": "kitchen_hood",
                         "capability": "fan", "action": "set", "params": {"level": 2}}]
    result, captured2 = await harness.run("power_off", "выключи вытяжку",
                                          {"target": "вытяжку"}, room="Кухня")
    assert captured2[-1] == {"kind": "actuate", "device_id": "kitchen_hood",
                             "capability": "fan", "action": "off", "params": None}


async def test_volume_set_with_range_validation(harness):
    result, captured = await harness.run("volume_set", "громкость 30 на телеке",
                                         {"level": 30, "target": "телеке"}, room="Детская")
    assert captured == [{"kind": "actuate", "device_id": "children_room_tv",
                         "capability": "volume", "action": "set", "params": {"level": 30}}]


async def test_playback_play_falls_back_to_play_pause(harness):
    result, captured = await harness.run("playback_play", "продолжи на заппити",
                                         {"target": "заппити"}, room="Гостиная")
    assert captured == [{"kind": "actuate", "device_id": "video",
                         "capability": "playback", "action": "play_pause", "params": None}]


async def test_cover_position_room_form_halfway(harness):
    result, captured = await harness.run("cover_position", "шторы наполовину",
                                         {"group_noun": "cover"}, room="Гостиная")
    assert captured == [{"kind": "room-group", "room_id": "living_room", "group": "cover",
                         "action": "set_position", "scope": "auto"}]
    assert "50" in result.text


# --- QUAL-35 Slice 3 — hard-phrasing fixes ----------------------------------------------------------

async def test_f92_raw_target_group_noun_goes_room_form(harness):
    # QUAL-50 LLM entities carry the spoken noun in `target`, never the donation CHOICE param —
    # «свет» must still ride the depth doctrine into the room form (F92)
    result, captured = await harness.run("power_off", "выруби свет",
                                         {"target": "свет"}, room="Спальня")
    assert captured == [{"kind": "room-group", "room_id": "bedroom",
                         "group": "light", "action": "off", "scope": "auto"}]


async def test_f95_raw_target_cover_noun_goes_room_form(harness):
    result, captured = await harness.run("cover_close", "прикрой шторы",
                                         {"target": "шторы"}, room="Гостиная")
    assert captured == [{"kind": "room-group", "room_id": "living_room",
                         "group": "cover", "action": "close", "scope": "auto"}]


async def test_f93_power_verb_off_on_playback_only_device(harness):
    # the tape-deck class: playback capability, no power — power verbs map to stop/play (F93)
    result, captured = await harness.run("power_off", "глуши заппити",
                                         {"target": "заппити"}, room="Гостиная")
    assert captured == [{"kind": "actuate", "device_id": "video",
                         "capability": "playback", "action": "stop", "params": None}]


async def test_power_on_playback_only_device_falls_back_to_play_pause(harness):
    # «Заппити» has no plain `play` — the toggle stands in, mirroring the playback_play fallback
    result, captured = await harness.run("power_on", "вруби заппити",
                                         {"target": "заппити"}, room="Гостиная")
    assert captured == [{"kind": "actuate", "device_id": "video",
                         "capability": "playback", "action": "play_pause", "params": None}]


async def test_f94_preverbal_device_resolved_by_utterance_scan(harness):
    # no target entity at all — the post-verb extraction regex can't capture pre-verbal
    # «вытяжку»; the resolver's utterance scan must spot the catalog device (F94)
    result, captured = await harness.run("power_on", "на кухне вытяжку включи",
                                         {}, room="Кухня")
    assert captured == [{"kind": "actuate", "device_id": "kitchen_hood",
                         "capability": "fan", "action": "set", "params": {"level": 2}}]


async def test_utterance_scan_stays_quiet_without_a_device_word(harness):
    # scan is stem-grade only: an utterance with no catalog name in it must still clarify,
    # not false-positive on generic words
    result, captured = await harness.run("power_on", "включи", {}, room="Спальня")
    assert captured == []
    assert result.metadata.get("clarification") or not result.success
