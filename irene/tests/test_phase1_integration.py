"""Client-registry + request→conversation context seam.

Survivors of the pre-refactor "phase1 integration" scaffolding (TEST-7). Only the behaviors that
are LIVE and covered nowhere else are kept here, re-asserted at the public/port level:

  * `ClientRegistry` node/web registration and room lookup (the action-store side lives in
    test_action_store; registration + room indexing is only exercised here).
  * `ContextManager.get_context_with_request_info` — the RequestContext → UnifiedConversationContext
    transfer that the entry adapters depend on.

Dropped as covered elsewhere or not-in-this-build:
  * temporal entity resolution → test_context_aware_nlu::test_entity_resolver_temporal_entities
  * language-default contracts (RequestContext.language / UnifiedConversationContext default) →
    test_language_source_of_truth (QUAL-36)
  * device/location entity resolution → unbuilt smart-home resolution (ARCH-6/ARCH-8); the current
    resolver intentionally returns `_resolution_failed` until physical devices/rooms are registered.
"""

import pytest

from irene.intents.context import ContextManager
from irene.workflows.base import RequestContext
from irene.core.client_registry import ClientRegistry


@pytest.fixture
def client_registry():
    """A non-persistent registry (no disk side effects)."""
    return ClientRegistry({"persistent_storage": False})


@pytest.fixture
def context_manager():
    return ContextManager(session_timeout=3600, max_history_turns=10)


class TestClientRegistration:
    """Registration + room-index contract of ClientRegistry (Russian room/device names)."""

    @pytest.mark.asyncio
    async def test_esp32_node_registration_records_devices_and_capabilities(self, client_registry):
        devices = [
            {"id": "light1", "name": "Кухонный свет", "type": "light",
             "capabilities": {"dimmable": True}},
            {"id": "sensor1", "name": "Датчик температуры", "type": "sensor",
             "capabilities": {"temperature": True}},
        ]

        assert await client_registry.register_esp32_node(
            client_id="kitchen_esp32",
            room_name="Кухня",
            devices=devices,
            source_address="192.168.1.100",
            language="ru",
        )

        client = client_registry.get_client("kitchen_esp32")
        assert client is not None
        assert client.client_id == "kitchen_esp32"
        assert client.room_name == "Кухня"
        assert client.language == "ru"
        assert client.client_type == "esp32"
        assert len(client.available_devices) == 2
        # ESP32 nodes are voice-capable by construction.
        assert client.capabilities["voice_input"] is True
        assert client.source_address == "192.168.1.100"

    @pytest.mark.asyncio
    async def test_web_client_registration_marks_visual_output(self, client_registry):
        assert await client_registry.register_web_client(
            client_id="web_living_room",
            room_name="Гостиная",
            user_agent="Mozilla/5.0 (Chrome)",
            language="ru",
        )

        client = client_registry.get_client("web_living_room")
        assert client is not None
        assert client.client_type == "web"
        assert client.room_name == "Гостиная"
        # A web client has no physical devices but does have a screen.
        assert client.available_devices == []
        assert client.capabilities["visual_output"] is True
        assert client.user_agent == "Mozilla/5.0 (Chrome)"

    @pytest.mark.asyncio
    async def test_room_index_groups_clients_and_lists_rooms(self, client_registry):
        await client_registry.register_esp32_node("kitchen_esp32", "Кухня", [])
        await client_registry.register_web_client("kitchen_web", "Кухня")
        await client_registry.register_web_client("living_room_web", "Гостиная")

        kitchen = client_registry.get_clients_by_room("Кухня")
        assert len(kitchen) == 2
        assert all(c.room_name == "Кухня" for c in kitchen)

        living = client_registry.get_clients_by_room("Гостиная")
        assert [c.client_id for c in living] == ["living_room_web"]

        # Lookup is case-insensitive on the room name.
        assert len(client_registry.get_clients_by_room("кухня")) == 2

        rooms = client_registry.get_all_rooms()
        assert set(rooms) == {"Кухня", "Гостиная"}

    @pytest.mark.asyncio
    async def test_unknown_client_lookup_returns_none(self, client_registry):
        # Off-path: nothing registered → no client, no rooms, empty room query.
        assert client_registry.get_client("nope") is None
        assert client_registry.get_clients_by_room("Кухня") == []
        assert client_registry.get_all_rooms() == []


class TestRequestToConversationContext:
    """`get_context_with_request_info` is the seam entry adapters use to seed a conversation."""

    @pytest.mark.asyncio
    async def test_request_fields_transfer_to_conversation_context(self, context_manager):
        request = RequestContext(
            source="esp32",
            session_id="sess-1",
            client_id="kitchen_esp32",
            room_name="Кухня",
            device_context={"available_devices": [
                {"id": "light1", "name": "Кухонный свет", "type": "light"},
                {"id": "speaker1", "name": "Колонка", "type": "speaker"},
            ]},
            language="ru",
        )

        ctx = await context_manager.get_context_with_request_info("sess-1", request)

        assert ctx.client_id == "kitchen_esp32"
        assert ctx.language == "ru"
        assert ctx.request_source == "esp32"
        assert ctx.get_room_name() == "Кухня"

        devices = ctx.get_device_capabilities()
        assert {d["name"] for d in devices} == {"Кухонный свет", "Колонка"}

    @pytest.mark.asyncio
    async def test_unspecified_request_language_does_not_override_seed(self, context_manager):
        # QUAL-36 at the seam: language=None must not stomp the session's seeded language.
        request = RequestContext(source="cli", session_id="sess-2", language=None)
        ctx = await context_manager.get_context_with_request_info("sess-2", request)
        assert ctx.language == "ru"  # the structural seed, not overwritten by None

    @pytest.mark.asyncio
    async def test_no_request_context_yields_a_bare_session(self, context_manager):
        # Off-path: callers may invoke with no RequestContext at all.
        ctx = await context_manager.get_context_with_request_info("sess-3", None)
        assert ctx.session_id == "sess-3"
        assert ctx.client_id is None
        assert ctx.get_device_capabilities() == []

    @pytest.mark.asyncio
    async def test_device_name_resolution_exact_and_miss(self, context_manager):
        request = RequestContext(
            client_id="test_client",
            session_id="sess-4",
            room_name="Кухня",
            device_context={"available_devices": [
                {"id": "light1", "name": "Кухонный свет", "type": "light"},
                {"id": "light2", "name": "Kitchen Light", "type": "light"},
                {"id": "tv1", "name": "Телевизор Samsung", "type": "tv"},
            ]},
            language="ru",
        )
        ctx = await context_manager.get_context_with_request_info("sess-4", request)

        # Exact match in either script.
        assert ctx.get_device_by_name("Кухонный свет")["id"] == "light1"
        assert ctx.get_device_by_name("Kitchen Light")["id"] == "light2"
        # No plausible match → None (not a wrong-device false positive).
        assert ctx.get_device_by_name("несуществующее устройство") is None
