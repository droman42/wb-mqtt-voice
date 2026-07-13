"""ARCH-8 PR-3 / QUAL-35 resolver half — catalog-backed device/room resolution.

Covers: surface matching over catalog names+aliases (RU-morphology-tolerant),
room-context disambiguation, name-level ambiguity → candidates (the clarify
path), the ARCH-26 lazy re-pull on a miss, the D-15 multi-room coverage policy
(incl. the `global` exemption), and the Q7b swap (donation-declared
`entity_type` drives dispatch; heuristics only for generic/undeclared).
"""

import pytest

from locveil_voice.core.catalog_service import CatalogService
from locveil_voice.core.client_registry import ClientRegistration, get_client_registry
from locveil_voice.core.donations import (
    EntityType,
    HandlerDonation,
    MethodDonation,
    ParameterSpec,
    ParameterType,
)
from locveil_voice.core.entity_resolver import (
    ContextualEntityResolver,
    DeviceEntityResolver,
    LocationEntityResolver,
    match_catalog_room,
    resolve_default_room,
)
from locveil_voice.intents.context_models import UnifiedConversationContext
from locveil_voice.intents.models import Intent
from locveil_voice.outputs.bridge import parse_catalog

CATALOG_PAYLOAD = {
    "version": "test-cat-1",
    "rooms": [
        {"id": "bedroom", "names": {"ru": "Спальня"}, "devices": [],
         "group_defaults": {"light": "bedroom_spots"}},
        {"id": "children_room", "names": {"ru": "Детская"}, "aliases": {"ru": ["сынарник"]},
         "devices": []},
        {"id": "living_room", "names": {"ru": "Гостиная"}, "aliases": {"ru": ["зал"]},
         "devices": []},
        {"id": "kitchen", "names": {"ru": "Кухня"}, "devices": []},
        {"id": "global", "names": {"ru": "Весь дом"}, "aliases": {"ru": ["квартира"]},
         "devices": []},
    ],
    "devices": [
        {"id": "children_room_tv", "room": "children_room",
         "names": {"ru": "Телевизор"}, "aliases": {"ru": ["телек"]},
         "capabilities": [{"name": "power", "group": "power",
                           "actions": [{"name": "on"}, {"name": "off"}]}]},
        {"id": "appletv_children", "room": "children_room",
         "names": {"ru": "Apple TV"}, "aliases": {"ru": ["эппл"]},
         "capabilities": [{"name": "power", "group": "power",
                           "actions": [{"name": "on"}, {"name": "off"}]}]},
        {"id": "appletv_living", "room": "living_room",
         "names": {"ru": "Apple TV"}, "aliases": {"ru": ["эппл"]},
         "capabilities": [{"name": "power", "group": "power",
                           "actions": [{"name": "on"}, {"name": "off"}]}]},
        {"id": "bedroom_sconce_left", "room": "bedroom",
         "names": {"ru": "Бра слева"}, "aliases": {"ru": ["ночники"]},
         "capabilities": [{"name": "power", "group": "light",
                           "actions": [{"name": "on"}, {"name": "off"}]}]},
        {"id": "bedroom_sconce_right", "room": "bedroom",
         "names": {"ru": "Бра справа"}, "aliases": {"ru": ["ночники"]},
         "capabilities": [{"name": "power", "group": "light",
                           "actions": [{"name": "on"}, {"name": "off"}]}]},
        {"id": "bedroom_heating", "room": "bedroom",
         "names": {"ru": "Обогрев"}, "aliases": {"ru": ["радиаторы"]},
         "capabilities": [{"name": "climate", "group": "climate",
                           "actions": [{"name": "set_setpoint", "params": [
                               {"name": "temp", "type": "float", "required": True,
                                "min": 5.0, "max": 30.0, "unit": "°C"}]}]}]},
        {"id": "all_lights", "room": "global",
         "names": {"ru": "Весь свет"},
         "capabilities": [{"name": "power", "group": "light",
                           "actions": [{"name": "on"}, {"name": "off"}]}]},
    ],
}


def _service(payload=CATALOG_PAYLOAD) -> CatalogService:
    svc = CatalogService()
    svc.set_catalog(parse_catalog(payload))
    return svc


def _ctx(room_name=None, client_id=None, language="ru") -> UnifiedConversationContext:
    return UnifiedConversationContext(session_id="test_session", client_id=client_id,
                                      room_name=room_name, language=language)


# --- device resolution ---------------------------------------------------------------------------

async def test_exact_alias_resolves_device():
    resolver = DeviceEntityResolver(catalog_port=_service())
    result = await resolver.resolve("телек", _ctx(room_name="Детская"))
    assert result.resolution_type == "exact"
    assert result.resolved_value["device_id"] == "children_room_tv"
    assert "power" in result.resolved_value["capabilities"]


async def test_room_context_disambiguates_shared_alias():
    resolver = DeviceEntityResolver(catalog_port=_service())
    result = await resolver.resolve("эппл", _ctx(room_name="Гостиная"))
    assert result.resolved_value["device_id"] == "appletv_living"
    result = await resolver.resolve("эппл", _ctx(room_name="Детская"))
    assert result.resolved_value["device_id"] == "appletv_children"


async def test_no_room_context_yields_ambiguous_candidates():
    resolver = DeviceEntityResolver(catalog_port=_service())
    result = await resolver.resolve("эппл", _ctx())
    assert result.resolution_type == "ambiguous"
    assert set(result.metadata["candidates"]) == {"appletv_children", "appletv_living"}


async def test_same_room_pair_stays_ambiguous():
    # «ночники» names BOTH bedroom sconces — room context cannot split them; the clarify
    # path gets candidates (v1 policy; the pair dissolves when a compound device arrives)
    resolver = DeviceEntityResolver(catalog_port=_service())
    result = await resolver.resolve("ночники", _ctx(room_name="Спальня"))
    assert result.resolution_type == "ambiguous"
    assert set(result.metadata["candidates"]) == {"bedroom_sconce_left", "bedroom_sconce_right"}


async def test_inflected_form_matches_fuzzily():
    resolver = DeviceEntityResolver(catalog_port=_service())
    result = await resolver.resolve("радиаторах", _ctx(room_name="Спальня"))
    assert result.resolution_type == "fuzzy"
    assert result.resolved_value["device_id"] == "bedroom_heating"


async def test_miss_triggers_lazy_refresh_once():
    stale = {"version": "stale-0", "rooms": CATALOG_PAYLOAD["rooms"], "devices": []}
    pulls = []

    async def fetch():
        pulls.append(1)
        return parse_catalog(CATALOG_PAYLOAD)

    svc = CatalogService(fetcher=fetch)
    svc.set_catalog(parse_catalog(stale))
    resolver = DeviceEntityResolver(catalog_port=svc)
    result = await resolver.resolve("телек", _ctx(room_name="Детская"))
    assert result is not None and result.resolved_value["device_id"] == "children_room_tv"
    assert len(pulls) == 1  # exactly one re-pull (ARCH-26: at most one stale round-trip)


async def test_genuine_miss_after_refresh_returns_none():
    resolver = DeviceEntityResolver(catalog_port=_service())
    assert await resolver.resolve("несуществующее", _ctx()) is None


# --- room resolution + D-15 ----------------------------------------------------------------------

def test_match_catalog_room_by_name_alias_id_and_inflection():
    catalog = parse_catalog(CATALOG_PAYLOAD)
    assert match_catalog_room("Детская", catalog, "ru").id == "children_room"
    assert match_catalog_room("детской", catalog, "ru").id == "children_room"  # inflected
    assert match_catalog_room("зал", catalog, "ru").id == "living_room"        # alias
    assert match_catalog_room("living_room", catalog, "ru").id == "living_room"  # raw id
    assert match_catalog_room("гараж", catalog, "ru") is None                  # not a room


async def test_room_resolves_with_alias_and_metadata():
    resolver = LocationEntityResolver(catalog_port=_service())
    result = await resolver.resolve("зал", _ctx())
    assert result.resolution_type == "exact"
    assert result.resolved_value == {"room_id": "living_room", "name": "Гостиная"}


async def test_d15_uncovered_room_is_flagged_not_actuated():
    registry = get_client_registry()
    await registry.register_client(ClientRegistration(
        client_id="esp32_kids", room_name="Детская", covered_rooms=["children_room"]))
    try:
        resolver = LocationEntityResolver(catalog_port=_service())
        # a real room the satellite does NOT cover → uncovered_room (spoken error, no actuation)
        result = await resolver.resolve("кухне", _ctx(client_id="esp32_kids"))
        assert result.resolution_type == "uncovered_room"
        assert result.resolved_value["room_id"] == "kitchen"
        # a covered room resolves normally
        result = await resolver.resolve("детской", _ctx(client_id="esp32_kids"))
        assert result.resolution_type in ("exact", "fuzzy")
        assert result.resolved_value["room_id"] == "children_room"
        # `global` is exempt: whole-house asks work from any satellite
        result = await resolver.resolve("квартире", _ctx(client_id="esp32_kids"))
        assert result.resolution_type != "uncovered_room"
        assert result.resolved_value["room_id"] == "global"
    finally:
        await registry.unregister_client("esp32_kids")


async def test_unconstrained_client_reaches_any_room():
    resolver = LocationEntityResolver(catalog_port=_service())
    result = await resolver.resolve("кухне", _ctx())  # no client registration → no constraint
    assert result.resolution_type in ("exact", "fuzzy")
    assert result.resolved_value["room_id"] == "kitchen"


def test_resolve_default_room_maps_context_room_to_catalog_id():
    catalog = parse_catalog(CATALOG_PAYLOAD)
    assert resolve_default_room(_ctx(room_name="Спальня"), catalog) == "bedroom"
    assert resolve_default_room(_ctx(), catalog) is None


# --- the Q7b swap (declared entity_type drives dispatch) -----------------------------------------

def _donation_with_typed_params() -> HandlerDonation:
    return HandlerDonation(
        schema_version="1.1",
        handler_domain="smarthome",
        method_donations=[MethodDonation(
            method_name="power_on",
            intent_suffix="power_on",
            phrases=["включи"],
            parameters=[
                ParameterSpec(name="target", type=ParameterType.STRING,
                              entity_type=EntityType.DEVICE),
                ParameterSpec(name="where", type=ParameterType.STRING,
                              entity_type=EntityType.ROOM),
                ParameterSpec(name="note", type=ParameterType.STRING,
                              entity_type=EntityType.GENERIC),
            ])])


class _FakeAssetLoader:
    def __init__(self, donations):
        self.donations = donations
        self.localizations = {}


async def test_declared_entity_types_drive_dispatch():
    loader = _FakeAssetLoader({"smarthome": _donation_with_typed_params()})
    resolver = ContextualEntityResolver(loader, catalog_port=_service())
    # neither "target" nor "where" matches the legacy name-heuristics; only the
    # declared entity_type routes them to the device/room resolvers
    intent = Intent(name="smarthome.power_on", entities={"target": "телек", "where": "детской"},
                    confidence=1.0, raw_text="включи телек в детской", domain="smarthome")
    resolved = await resolver.resolve_entities(intent, _ctx())
    assert resolved["target_resolved"]["device_id"] == "children_room_tv"
    assert resolved["where_resolved"]["room_id"] == "children_room"
    # the GENERIC param is untouched by device/room resolution
    intent2 = Intent(name="smarthome.power_on", entities={"note": "телек"},
                     confidence=1.0, raw_text="", domain="smarthome")
    resolved2 = await resolver.resolve_entities(intent2, _ctx())
    assert "note_resolved" not in resolved2


async def test_undeclared_params_keep_legacy_heuristics():
    # intent.domain "device" → the old heuristic path still routes to the device resolver
    resolver = ContextualEntityResolver(None, catalog_port=_service())
    intent = Intent(name="device.turn_on", entities={"device": "телек"},
                    confidence=1.0, raw_text="включи телек", domain="device")
    resolved = await resolver.resolve_entities(intent, _ctx(room_name="Детская"))
    assert resolved["device_resolved"]["device_id"] == "children_room_tv"


# --- D-15 rule 1: the room named in the utterance is KING (BUG-38) ---------------------------------
#
# Regression cover for a live wrong-room actuation: on the WB7, «включи торшер в спальне» switched on
# the LIVING-ROOM floor lamp — the only «торшер» in the house — because the room filter ran only when
# candidates tied (`if len(candidates) > 1`). A uniquely-named device skipped the room check entirely.


async def test_spoken_room_refuses_when_it_has_no_such_device():
    """«включи телевизор в спальне» — the bedroom has no TV. Refuse; never retarget elsewhere."""
    resolver = DeviceEntityResolver(catalog_port=_service())
    result = await resolver.resolve("телевизор", _ctx(), spoken_room="спальне")
    assert result.resolution_type == "no_device_in_room"
    assert result.resolved_value is None
    assert result.metadata["room_id"] == "bedroom"
    # the device it would have actuated before the fix is reported, for the log/trace
    assert result.metadata["candidates"] == ["children_room_tv"]


async def test_spoken_room_scopes_a_unique_match():
    """Same unique device, named with its own room → resolves normally."""
    resolver = DeviceEntityResolver(catalog_port=_service())
    result = await resolver.resolve("телевизор", _ctx(), spoken_room="детской")
    assert result.resolved_value["device_id"] == "children_room_tv"


async def test_spoken_room_beats_the_clients_own_room():
    """King: «эппл в гостиной» said from the children's room targets the LIVING-ROOM Apple TV."""
    resolver = DeviceEntityResolver(catalog_port=_service())
    result = await resolver.resolve("эппл", _ctx(room_name="Детская"), spoken_room="гостиной")
    assert result.resolved_value["device_id"] == "appletv_living"


async def test_spoken_room_resolves_what_would_otherwise_be_ambiguous():
    resolver = DeviceEntityResolver(catalog_port=_service())
    ambiguous = await resolver.resolve("эппл", _ctx())
    assert ambiguous.resolution_type == "ambiguous"
    scoped = await resolver.resolve("эппл", _ctx(), spoken_room="гостиной")
    assert scoped.resolution_type != "ambiguous"
    assert scoped.resolved_value["device_id"] == "appletv_living"


async def test_global_devices_survive_the_room_filter():
    """`all_lights` lives in no room; «весь свет в спальне» must not filter it away."""
    resolver = DeviceEntityResolver(catalog_port=_service())
    result = await resolver.resolve("весь свет", _ctx(), spoken_room="спальне")
    assert result.resolved_value["device_id"] == "all_lights"


async def test_unknown_room_word_falls_through():
    """D-15: `r ∉ R` → it was not a room word; resolve as if none was mentioned."""
    resolver = DeviceEntityResolver(catalog_port=_service())
    result = await resolver.resolve("телевизор", _ctx(), spoken_room="подвале")
    assert result.resolved_value["device_id"] == "children_room_tv"


async def test_within_room_ambiguity_survives_room_scoping():
    """Both sconces are «ночники» in ONE room — the room cannot split them (BUG-39 owns the prompt)."""
    resolver = DeviceEntityResolver(catalog_port=_service())
    result = await resolver.resolve("ночники", _ctx(), spoken_room="спальне")
    assert result.resolution_type == "ambiguous"
    assert set(result.metadata["candidates"]) == {"bedroom_sconce_left", "bedroom_sconce_right"}


async def test_client_room_remains_a_tiebreak_hint_when_no_room_is_spoken():
    """Rule 3 unchanged: with no room named, the client's room may narrow — never contradict."""
    resolver = DeviceEntityResolver(catalog_port=_service())
    result = await resolver.resolve("эппл", _ctx(room_name="Гостиная"))
    assert result.resolved_value["device_id"] == "appletv_living"
