"""
Context-aware NLU — port/contract tests.

Covers the live context-aware recognition seam:
  ContextAwareNLUProcessor.process_with_context() → context injection + entity resolution,
  ContextualEntityResolver.resolve_entities() → temporal resolution,
and the UnifiedConversationContext device/room lookup helpers.

Notes on scope (TEST-7):
  * `Intent(...)` no longer carries `session_id` — the session id lives on the context
    (UnifiedConversationContext.session_id), see irene/intents/models.py.
  * Device/room *resolution success* (exact / type-inference against the in-context device
    list) is live behavior of ContextualEntityResolver and is asserted here. The unbuilt
    MQTT/bridge resolution (`*_resolution_failed`, ARCH-8) is intentionally NOT exercised.

`_LocalizationAssetLoader` is the reference asset-loader fixture pattern: it backs the
Device/Location resolvers with the real assets/localization/ YAMLs without standing up a
full IntentAssetLoader (the live NLU component rebuilds the resolver with the real loader
during provider loading).
"""

from pathlib import Path

import pytest
import yaml
from unittest.mock import AsyncMock, MagicMock

from irene.intents.models import Intent
from irene.intents.context_models import UnifiedConversationContext
from irene.components.nlu_component import ContextAwareNLUProcessor, NLUComponent
from irene.core.entity_resolver import ContextualEntityResolver


class _LocalizationAssetLoader:
    """Minimal asset-loader stub exposing `.localizations` loaded from the real
    assets/localization/ YAMLs, so the Device/Location entity resolvers work in tests
    without a full IntentAssetLoader."""

    def __init__(self):
        self.localizations = {}
        base = Path(__file__).resolve().parents[2] / "assets" / "localization"
        for domain in ("devices", "rooms"):
            self.localizations[domain] = {}
            for lang in ("en", "ru"):
                f = base / domain / f"{lang}.yaml"
                if f.exists():
                    self.localizations[domain][lang] = yaml.safe_load(f.read_text()) or {}


class TestContextAwareNLU:
    """Context-aware NLU processing seam."""

    @pytest.fixture
    def mock_nlu_component(self):
        """A NLUComponent stub whose `recognize` is injectable.

        spec=NLUComponent doesn't expose the instance attr `core`; the context-aware path
        reads core.config.nlu (_should_redetect_language). Wire a minimal config so language
        re-detection is disabled and the recognized language is left intact.
        """
        nlu_component = MagicMock(spec=NLUComponent)
        nlu_component.recognize = AsyncMock()
        nlu_component.core = MagicMock()
        nlu_component.core.config.nlu.auto_detect_language = False
        return nlu_component

    @pytest.fixture
    def context_processor(self, mock_nlu_component):
        """Context-aware processor whose entity resolver is backed by the real
        localization assets (device/room mappings)."""
        processor = ContextAwareNLUProcessor(mock_nlu_component)
        processor.entity_resolver = ContextualEntityResolver(_LocalizationAssetLoader())
        return processor

    @pytest.fixture
    def sample_context_kitchen(self):
        context = UnifiedConversationContext(
            session_id="test_session",
            user_id="test_user",
            client_id="kitchen_node",
            language="en",
            timezone="UTC",
        )
        context.set_client_context(
            "kitchen_node",
            {
                "room_name": "Kitchen",
                "available_devices": [
                    {"id": "kitchen_light_1", "name": "Kitchen Light",
                     "type": "light", "capabilities": ["brightness", "color"]},
                    {"id": "kitchen_speaker_1", "name": "Kitchen Speaker",
                     "type": "speaker", "capabilities": ["volume", "play", "pause"]},
                    {"id": "coffee_maker_1", "name": "Coffee Maker",
                     "type": "appliance", "capabilities": ["brew", "timer"]},
                ],
            },
        )
        return context

    @pytest.fixture
    def sample_context_living_room(self):
        context = UnifiedConversationContext(
            session_id="test_session_2",
            user_id="test_user",
            client_id="living_room_node",
            language="en",
            timezone="UTC",
        )
        context.set_client_context(
            "living_room_node",
            {
                "room_name": "Living Room",
                "available_devices": [
                    {"id": "tv_1", "name": "Smart TV",
                     "type": "tv", "capabilities": ["power", "volume", "channel"]},
                    {"id": "living_room_lights_1", "name": "Living Room Lights",
                     "type": "light", "capabilities": ["brightness", "dimming"]},
                    {"id": "soundbar_1", "name": "Soundbar",
                     "type": "speaker", "capabilities": ["volume", "bass", "treble"]},
                ],
            },
        )
        return context

    @pytest.mark.asyncio
    async def test_device_resolution_exact_match(self, context_processor, sample_context_kitchen):
        """Exact device-name reference resolves to the in-context device, and the
        client/room context is injected into the enhanced intent's entities."""
        context_processor.nlu_component.recognize.return_value = Intent(
            name="device.control",
            entities={"device": "Kitchen Light", "action": "turn_on"},
            confidence=0.9,
            raw_text="turn on the kitchen light",
        )

        result = await context_processor.process_with_context(
            "turn on the kitchen light", sample_context_kitchen
        )

        # Resolved device is the full in-context device record (id lives on it).
        device = result.entities["device_resolved"]
        assert device["name"] == "Kitchen Light"
        assert device["type"] == "light"
        assert device["id"] == "kitchen_light_1"
        assert result.entities["device_resolution_type"] == "exact"

        # Client/room context injected.
        assert result.entities["client_id"] == "kitchen_node"
        assert result.entities["room_name"] == "Kitchen"

    @pytest.mark.asyncio
    async def test_device_resolution_type_inference(self, context_processor, sample_context_living_room):
        """A bare device-type word ("tv") resolves to the sole device of that type via
        localization keyword type-inference."""
        context_processor.nlu_component.recognize.return_value = Intent(
            name="device.control",
            entities={"device": "tv", "action": "turn_on"},
            confidence=0.8,
            raw_text="turn on tv",
        )

        result = await context_processor.process_with_context(
            "turn on tv", sample_context_living_room
        )

        device = result.entities["device_resolved"]
        assert device["name"] == "Smart TV"
        assert device["type"] == "tv"

    @pytest.mark.asyncio
    async def test_unknown_device_not_resolved(self, context_processor, sample_context_kitchen):
        """A device reference with no in-context match yields no `device_resolved`
        (off-path: resolution simply does not fabricate a device)."""
        context_processor.nlu_component.recognize.return_value = Intent(
            name="device.control",
            entities={"device": "nonexistent gadget", "action": "turn_on"},
            confidence=0.7,
            raw_text="turn on the nonexistent gadget",
        )

        result = await context_processor.process_with_context(
            "turn on the nonexistent gadget", sample_context_kitchen
        )

        assert "device_resolved" not in result.entities
        # Original entity + client context are still present.
        assert result.entities["device"] == "nonexistent gadget"
        assert result.entities["client_id"] == "kitchen_node"

    @pytest.mark.asyncio
    async def test_context_enhancement_conversation_history(self, context_processor, sample_context_kitchen):
        """Recent intents from conversation history are injected into the enhanced entities."""
        sample_context_kitchen.record_turn("what's the weather like", "It's sunny today", "weather.current")
        sample_context_kitchen.record_turn("set a timer for 10 minutes", "Timer set for 10 minutes", "timer.set")

        context_processor.nlu_component.recognize.return_value = Intent(
            name="system.status",
            entities={},
            confidence=0.8,
            raw_text="how are things",
        )

        result = await context_processor.process_with_context("how are things", sample_context_kitchen)

        recent_intents = result.entities["recent_intents"]
        assert "timer.set" in recent_intents
        assert "weather.current" in recent_intents

    @pytest.mark.asyncio
    async def test_entity_resolver_temporal_entities(self):
        """Duration entities are resolved to a structured {value, unit} by the temporal resolver."""
        resolver = ContextualEntityResolver()
        intent = Intent(
            name="timer.set",
            entities={"duration": "5 minutes", "message": "Coffee ready"},
            confidence=0.9,
            raw_text="set timer for 5 minutes",
        )
        context = UnifiedConversationContext(session_id="test")

        resolved = await resolver.resolve_entities(intent, context)

        duration = resolved["duration_resolved"]
        assert duration["value"] == 5
        assert duration["unit"] == "minutes"


class TestContextDeviceLookup:
    """UnifiedConversationContext device/room lookup helpers (bilingual)."""

    @pytest.fixture
    def context(self):
        ctx = UnifiedConversationContext(session_id="test", client_id="kitchen")
        ctx.set_client_context(
            "kitchen",
            {
                "room_name": "Кухня",  # Russian room name
                "available_devices": [
                    {"id": "light1", "name": "Кухонный свет", "type": "light"},
                    {"id": "light2", "name": "Kitchen Light", "type": "light"},
                ],
            },
        )
        return ctx

    def test_get_device_by_name_exact_bilingual(self, context):
        ru = context.get_device_by_name("Кухонный свет")
        assert ru is not None
        assert ru["name"] == "Кухонный свет"

        en = context.get_device_by_name("Kitchen Light")
        assert en is not None
        assert en["name"] == "Kitchen Light"

    def test_get_room_name_uses_metadata(self, context):
        assert context.get_room_name() == "Кухня"

    def test_get_device_by_name_fuzzy(self, context):
        # "Kitchen" is a high-similarity prefix of "Kitchen Light" (>= 70% threshold).
        device = context.get_device_by_name("Kitchen")
        assert device is not None
        assert device["name"] == "Kitchen Light"

    def test_get_device_by_name_no_match(self, context):
        assert context.get_device_by_name("zzz totally unrelated") is None
