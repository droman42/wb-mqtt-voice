"""
Context-Based Entity Resolution System

This module implements context-aware entity resolution capabilities that use
client identification, device context, and conversation history to enhance
entity extraction and provide better understanding of user intents.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from ..intents.models import Intent
from ..intents.context_models import UnifiedConversationContext
from ..intents.device_catalog import CatalogDevice, CatalogRoom, DeviceCatalog
from ..intents.ports import DeviceCatalogPort
from .client_registry import get_client_registry
from .donations import EntityType
from ..utils.units import parse_duration, TIME_UNITS  # the one shared time-unit parser + surface table

# Required rapidfuzz import for fuzzy matching
from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)


@dataclass
class EntityResolutionResult:
    """Result of entity resolution with confidence and metadata"""
    resolved_value: Any
    original_value: str
    confidence: float
    resolution_type: str  # "exact", "fuzzy", "contextual", "inferred", "ambiguous", "uncovered_room"
    metadata: Dict[str, Any]


# --- catalog surface matching (ARCH-8 PR-3 / QUAL-35 resolver half) -------------------------------
#
# Spoken references arrive inflected («в детской» → «Детская», «на радиаторах» → «радиаторы»), so
# matching is normalized (case, ё→е) + fuzzy over each entry's full surface set (name + aliases in
# the request locale). Deterministic exact match always wins; the fuzzy band below it tolerates RU
# morphology without spaCy — the T2 tier (QUAL-35) deepens this later.

_MORPH_FUZZ_THRESHOLD = 80  # score floor for an inflected-form match
_STEM_MATCH_SCORE = 90      # what a shared-stem match scores (above threshold, below exact)


def _norm(text: str) -> str:
    return text.lower().replace("ё", "е").strip()


def _stem_match(a: str, b: str) -> bool:
    """RU-inflection heuristic: same word if the shared prefix leaves ≤3 trailing chars on both.

    Russian case/gender endings are at most ~3 characters («детск|ой»/«детск|ая»,
    «кухн|е»/«кухн|я», «радиатор|ах»/«радиатор|ы»); requiring a ≥4-char shared stem keeps
    short unrelated words apart («зал» vs «залив», «печь» vs «печенье»). Plain fuzz.ratio
    punishes short words too hard for this (детской/детская = 71)."""
    prefix = 0
    for ca, cb in zip(a, b):
        if ca != cb:
            break
        prefix += 1
    return prefix >= 4 and prefix >= max(len(a), len(b)) - 3


def _surface_score(ref_norm: str, surfaces: Tuple[str, ...]) -> int:
    """Best match score (0..100) of a normalized reference against an entity's surfaces."""
    best = 0
    for surface in surfaces:
        surface_norm = _norm(surface)
        if surface_norm == ref_norm:
            return 100
        score = int(fuzz.ratio(ref_norm, surface_norm))
        if score < _STEM_MATCH_SCORE and _stem_match(ref_norm, surface_norm):
            score = _STEM_MATCH_SCORE
        if score > best:
            best = score
    return best


def match_catalog_room(room_reference: str, catalog: DeviceCatalog,
                       locale: str) -> Optional[CatalogRoom]:
    """Match a spoken/registered room reference to a catalog room (id, name, or alias)."""
    ref_norm = _norm(room_reference)
    best_room, best_score = None, 0
    for room in catalog.rooms:
        if room.id == room_reference:  # registrations may carry catalog ids directly
            return room
        score = _surface_score(ref_norm, room.surfaces(locale))
        if score > best_score:
            best_room, best_score = room, score
    return best_room if best_score >= _MORPH_FUZZ_THRESHOLD else None


def resolve_default_room(context: UnifiedConversationContext,
                         catalog: DeviceCatalog) -> Optional[str]:
    """D-15 rule 3: no room mentioned → the client's primary room, as a catalog room id."""
    room_name = context.get_room_name()
    if not room_name:
        return None
    room = match_catalog_room(room_name, catalog, context.language or "ru")
    return room.id if room else None


def _client_covered_rooms(context: UnifiedConversationContext) -> List[str]:
    """The requesting client's covered rooms (ARCH-22 D-14), [] when unconstrained.

    A satellite covers specific rooms; a whole-house channel (web, CLI) has no registration
    or no covered list — an empty result means "no constraint", per D-15."""
    client_id = getattr(context, "client_id", None)
    if not client_id:
        return []
    registration = get_client_registry().get_client(client_id)
    if registration is None:
        return []
    covered = list(registration.covered_rooms or [])
    if registration.room_name and registration.room_name not in covered:
        covered.append(registration.room_name)  # primary is always covered
    return covered


class ContextualEntityResolver:
    """
    Context-aware entity resolver that uses client identification, device
    capabilities, and conversation history to resolve entity references.
    
    This implements the entity resolution capabilities described in the 
    Intent Keyword Donation Architecture document.
    """
    
    def __init__(self, asset_loader=None, catalog_port: Optional[DeviceCatalogPort] = None):
        self.logger = logging.getLogger(f"{__name__}.ContextualEntityResolver")
        self.asset_loader = asset_loader

        # Entity type resolvers (the device/room pair is catalog-backed when the bridge is wired)
        self.device_resolver = DeviceEntityResolver(asset_loader, catalog_port=catalog_port)
        self.location_resolver = LocationEntityResolver(asset_loader, catalog_port=catalog_port)
        self.temporal_resolver = TemporalEntityResolver()
        self.quantity_resolver = QuantityEntityResolver()

        # QUAL-35(b) — the Q7b atomic swap: declared `entity_type` (ParameterSpec, QUAL-29 Q6)
        # drives resolver dispatch; the `_is_*` name-heuristics survive only as the fallback for
        # GENERIC/undeclared params. Built lazily from the donations the asset loader carries.
        self._entity_types_by_intent: Optional[Dict[str, Dict[str, EntityType]]] = None

    def _declared_entity_type(self, intent_name: str, entity_name: str) -> Optional[EntityType]:
        """The donation-declared EntityType for this intent's parameter, or None if undeclared."""
        if self._entity_types_by_intent is None:
            self._entity_types_by_intent = self._build_entity_type_map()
        return self._entity_types_by_intent.get(intent_name, {}).get(entity_name)

    def _spoken_room_word(self, intent: Intent) -> Optional[str]:
        """The RAW room word this utterance carried, found by declared type rather than by the
        param name (`room`), so a donation is free to call it something else.

        Raw, not `room_resolved`: entity resolution walks `intent.entities` in donation order, so the
        room may still be unresolved when the device is resolved. Matching the word against the
        catalog at the point of use removes that ordering dependency entirely (BUG-38).
        """
        if self._entity_types_by_intent is None:
            self._entity_types_by_intent = self._build_entity_type_map()
        for param, etype in self._entity_types_by_intent.get(intent.name, {}).items():
            if etype in (EntityType.ROOM, EntityType.LOCATION):
                value = intent.entities.get(param)
                if isinstance(value, str) and value.strip():
                    return value
        return None

    def _build_entity_type_map(self) -> Dict[str, Dict[str, EntityType]]:
        donations = getattr(self.asset_loader, "donations", None) or {}
        mapping: Dict[str, Dict[str, EntityType]] = {}
        for donation in donations.values():
            shared = {p.name: p.entity_type for p in donation.global_parameters}
            for method in donation.method_donations:
                intent_name = f"{donation.handler_domain}.{method.intent_suffix}"
                per_param = dict(shared)
                per_param.update({p.name: p.entity_type for p in method.parameters})
                mapping[intent_name] = per_param
        return mapping
    
    async def resolve_entities(self, intent: Intent, context: UnifiedConversationContext) -> Dict[str, Any]:
        """
        Resolve all entities in the intent using context-aware resolution.
        
        Args:
            intent: Intent with entities to resolve
            context: UnifiedConversationContext with client and device information
            
        Returns:
            Dictionary with resolved entities and resolution metadata
        """
        resolved_entities = intent.entities.copy()
        resolution_metadata = {}
        
        for entity_name, entity_value in intent.entities.items():
            if isinstance(entity_value, str) and entity_value.strip():
                # Try different resolution strategies
                resolution_result, attempted_kind = await self._resolve_single_entity(
                    entity_name, entity_value, intent, context
                )

                if resolution_result:
                    resolved_entities[f"{entity_name}_resolved"] = resolution_result.resolved_value
                    resolved_entities[f"{entity_name}_confidence"] = resolution_result.confidence
                    resolved_entities[f"{entity_name}_resolution_type"] = resolution_result.resolution_type

                    resolution_metadata[entity_name] = resolution_result.metadata

                    self.logger.debug(f"Resolved entity '{entity_name}': '{entity_value}' -> "
                                    f"{resolution_result.resolved_value} ({resolution_result.resolution_type})")
                elif attempted_kind in ("device", "location"):
                    # We classified this as a device/room reference and tried to resolve it, but found no
                    # match. Mark it so the fail-loud / clarification boundary (QUAL-30) can distinguish
                    # "unresolvable reference" from "never a resolvable entity". (Device/room resolution
                    # becomes fully real once ARCH-6 registers physical devices/rooms.)
                    resolved_entities[f"{entity_name}_resolution_failed"] = True
                    self.logger.debug(f"Entity '{entity_name}'='{entity_value}' classified as {attempted_kind} "
                                      f"but did not resolve — marked _resolution_failed")

        # QUAL-35 Slice 3 (F94): a donation-declared DEVICE param the extraction regexes missed —
        # pre-verbal word order («на кухне вытяжку включи») defeats the post-verb captures — gets
        # one last chance: scan the utterance itself for catalog device names (stem-grade only).
        if self._entity_types_by_intent is None:
            self._entity_types_by_intent = self._build_entity_type_map()
        for param, etype in self._entity_types_by_intent.get(intent.name, {}).items():
            if etype is not EntityType.DEVICE or param in intent.entities:
                continue
            scanned = await self.device_resolver.scan_utterance(
                intent.raw_text, context, spoken_room=self._spoken_room_word(intent))
            if scanned is not None:
                resolved_entities[f"{param}_resolved"] = scanned.resolved_value
                resolved_entities[f"{param}_confidence"] = scanned.confidence
                resolved_entities[f"{param}_resolution_type"] = scanned.resolution_type
                resolution_metadata[param] = scanned.metadata
                self.logger.debug(f"Utterance scan resolved device param '{param}': "
                                  f"{scanned.resolved_value} ({scanned.resolution_type})")

        # Add resolution metadata
        if resolution_metadata:
            resolved_entities["_resolution_metadata"] = resolution_metadata

        return resolved_entities

    async def _resolve_single_entity(self, entity_name: str, entity_value: str,
                                   intent: Intent, context: UnifiedConversationContext) -> Tuple[Optional[EntityResolutionResult], Optional[str]]:
        """Resolve a single entity using the appropriate strategy.

        Returns ``(result, attempted_kind)`` where ``attempted_kind`` ∈
        {device, location, temporal, quantity, None} names the resolver that ran (or None if the
        entity matched no resolvable class) — so the caller can mark an attempted-but-unresolved
        device/location reference (``_resolution_failed``) without flagging every plain parameter.

        Dispatch is DECLARATIVE first (ARCH-8 PR-3 / QUAL-35(b), the Q7b swap): a donation-declared
        non-generic `entity_type` selects the resolver outright. The `_is_*_entity` name/value
        heuristics remain only as the fallback for GENERIC/undeclared params — existing donations
        all declare generic, so their behavior is unchanged until the smart-home donations (PR-4)
        declare device/room."""

        declared = self._declared_entity_type(intent.name, entity_name)
        if declared is EntityType.DEVICE:
            # D-15 rule 1 (BUG-38): the room named in the utterance scopes the device search.
            return await self.device_resolver.resolve(
                entity_value, context, spoken_room=self._spoken_room_word(intent)), "device"
        if declared in (EntityType.ROOM, EntityType.LOCATION):
            return await self.location_resolver.resolve(entity_value, context), "location"
        # PERSON has no resolver yet; GENERIC/undeclared falls through to the heuristics.

        # Device entity resolution
        if self._is_device_entity(entity_name, entity_value, intent):
            return await self.device_resolver.resolve(entity_value, context), "device"

        # Location entity resolution
        if self._is_location_entity(entity_name, entity_value, intent):
            return await self.location_resolver.resolve(entity_value, context), "location"

        # Temporal entity resolution
        if self._is_temporal_entity(entity_name, entity_value, intent):
            return await self.temporal_resolver.resolve(entity_value, context), "temporal"

        # Quantity entity resolution
        if self._is_quantity_entity(entity_name, entity_value, intent):
            return await self.quantity_resolver.resolve(entity_value, context), "quantity"

        return None, None
    
    def _is_device_entity(self, entity_name: str, entity_value: str, intent: Intent) -> bool:
        """Check if entity is a device reference based on intent domain and generic entity name patterns"""
        # Primary: Check intent domain for device-related intents
        if intent.domain in ["device", "smart_home", "iot", "home_automation"]:
            return True
        
        # Secondary: Check for generic device entity naming patterns
        generic_device_patterns = [
            "device", "target", "appliance", "устройство", "цель"
        ]
        
        if any(pattern in entity_name.lower() for pattern in generic_device_patterns):
            return True
        
        return False
    
    def _is_location_entity(self, entity_name: str, entity_value: str, intent: Intent) -> bool:
        """Check if entity is a location reference based on generic entity name patterns"""
        # Check for generic location entity naming patterns
        generic_location_patterns = [
            "location", "place", "destination", "area", "zone",
            "место", "локация", "расположение", "зона"  # Russian equivalents
        ]
        
        return any(pattern in entity_name.lower() for pattern in generic_location_patterns)
    
    def _is_temporal_entity(self, entity_name: str, entity_value: str, intent: Intent) -> bool:
        """Check if entity is a time/date reference based on entity name patterns and value patterns"""
        # Check entity name patterns (common entity naming conventions)
        temporal_entity_names = [
            "time", "date", "when", "duration", "timeout", "delay", "schedule",
            "время", "дата", "длительность", "таймаут", "расписание"  # Russian equivalents
        ]
        
        # Check entity name patterns
        if any(pattern in entity_name.lower() for pattern in temporal_entity_names):
            return True
        
        # Check entity value patterns (time formats)
        time_patterns = r'\d+:\d+|\d+\s*(hours?|minutes?|seconds?|часов?|часа|минут?|мин|секунд?|сек)'
        return bool(re.search(time_patterns, entity_value.lower()))
    
    def _is_quantity_entity(self, entity_name: str, entity_value: str, intent: Intent) -> bool:
        """Check if entity is a quantity/number reference based on entity name patterns and value patterns"""
        # Check entity name patterns (common entity naming conventions)
        quantity_entity_names = [
            "number", "count", "amount", "quantity", "value", "level", "percent", "percentage",
            "число", "количество", "сумма", "объем", "размер", "процент"  # Russian equivalents
        ]
        
        # Check entity name patterns
        if any(pattern in entity_name.lower() for pattern in quantity_entity_names):
            return True
        
        # Check entity value patterns (contains numbers)
        return bool(re.search(r'\d+', entity_value))


class DeviceEntityResolver:
    """Resolver for device-related entities.

    Catalog-backed when the bridge is wired (ARCH-8 PR-3): spoken references resolve against the
    real device catalog — `names` + `aliases` per locale, RU-morphology-tolerant, room-context
    disambiguation, name-level ambiguity surfaced as candidates (the clarify path), and the
    ARCH-26 lazy re-pull on a miss. Falls back to the legacy client-context path (ESP32-announced
    devices + localization type-inference) when no catalog is available."""

    def __init__(self, asset_loader=None, catalog_port: Optional[DeviceCatalogPort] = None):
        self.asset_loader = asset_loader
        self.catalog_port = catalog_port
        self.logger = logging.getLogger(f"{__name__}.DeviceEntityResolver")
        self._assets_warned = False  # warn-once guard for missing/empty localization assets

    def _warn_assets_once(self, message: str) -> None:
        """Log a degradation warning at most once per resolver (avoid per-request log spam)."""
        if not self._assets_warned:
            self.logger.warning(message)
            self._assets_warned = True

    def _load_device_types(self, language: str = "en") -> Dict[str, List[str]]:
        """Load device type keywords from localization files.

        Best-effort: returns {} (with a one-time warning) when the asset loader isn't wired yet or
        the localization data is missing/empty, rather than raising. The resolver then simply skips
        type-inference matching and degrades — a device utterance must never abort the whole request
        just because deferred asset coordination hasn't run (QUAL-11 P0 #4)."""
        if not self.asset_loader:
            self._warn_assets_once(
                "DeviceEntityResolver: asset loader not wired — skipping device type-inference "
                "(exact/fuzzy device-name matching still works)."
            )
            return {}

        try:
            device_localization = self.asset_loader.localizations.get("devices", {})
            device_data = device_localization.get(language, {})

            if not device_data and language != "en":
                # Fallback to English
                device_data = device_localization.get("en", {})

            device_types = device_data.get("device_types", {}) if device_data else {}
            if not device_types:
                self._warn_assets_once(
                    f"DeviceEntityResolver: no device type mappings for language '{language}' "
                    f"in assets/localization/devices/ — skipping type-inference."
                )
                return {}

            # Convert to expected format
            result = {}
            for device_type, config in device_types.items():
                keywords = config.get("keywords", [])
                aliases = config.get("aliases", [])
                result[device_type] = keywords + aliases

            return result
        except Exception as e:
            self._warn_assets_once(
                f"DeviceEntityResolver: failed to load device types from localization files: {e} — "
                f"skipping type-inference."
            )
            return {}
    
    
    async def resolve(self, device_reference: str, context: UnifiedConversationContext,
                      spoken_room: Optional[str] = None) -> Optional[EntityResolutionResult]:
        """
        Resolve device reference — against the bridge catalog when wired, else client context.

        `spoken_room`: the raw room word the utterance carried, if any. It scopes the catalog search
        (D-15 rule 1 — the named room is king, BUG-38).
        """
        if self.catalog_port is not None:
            result = await self._resolve_from_catalog(device_reference, context,
                                                      spoken_room=spoken_room)
            if result is not None:
                return result
            if self.catalog_port.catalog() is not None:
                # a real catalog had no match — the legacy path can't do better; don't fall through
                return None
            # still no catalog (bridge unreachable since boot) → legacy path below applies

        available_devices = context.get_device_capabilities()
        if not available_devices:
            return None

        device_reference_lower = device_reference.lower().strip()
        return self._resolve_from_client_context(device_reference, device_reference_lower,
                                                 available_devices, context)

    async def _resolve_from_catalog(self, device_reference: str,
                                    context: UnifiedConversationContext,
                                    _retried: bool = False,
                                    spoken_room: Optional[str] = None) -> Optional[EntityResolutionResult]:
        """Resolve against the bridge catalog; ARCH-26 lazy re-pull once on a miss.

        `spoken_room` is the RAW room word from the utterance («в спальне»), when the intent carried
        one. It is matched here rather than read from `room_resolved`, because entity resolution
        loops over `intent.entities` in donation order — the sibling `room` may not be resolved yet
        when `target` is (BUG-38).
        """
        assert self.catalog_port is not None
        catalog = self.catalog_port.catalog()
        if catalog is None:
            if _retried:
                return None
            await self.catalog_port.refresh()
            return await self._resolve_from_catalog(device_reference, context, _retried=True,
                                                    spoken_room=spoken_room)

        locale = context.language or "ru"
        ref_norm = _norm(device_reference)

        scored: List[Tuple[int, CatalogDevice]] = []
        for device in catalog.devices:
            score = _surface_score(ref_norm, device.surfaces(locale))
            if score >= _MORPH_FUZZ_THRESHOLD:
                scored.append((score, device))

        if not scored:
            if _retried:
                return None
            # a resolution miss is the ARCH-26 staleness signal — one re-pull, one retry
            fresh = await self.catalog_port.refresh()
            if fresh is None or fresh.version == catalog.version:
                return None
            return await self._resolve_from_catalog(device_reference, context, _retried=True,
                                                    spoken_room=spoken_room)

        best = max(score for score, _ in scored)
        candidates = [device for score, device in scored if score == best]
        return self._result_from_candidates(candidates, best, device_reference,
                                            catalog, locale, context, spoken_room)

    @staticmethod
    def _in_room(candidates: List[CatalogDevice], room_id: str) -> List[CatalogDevice]:
        """Devices of the target room, plus the whole-house aggregates.

        `global` devices (`all_lights`, `oven_power`, `heating_control`, …) are addressable from
        anywhere — the same carve-out the covered-rooms check makes — so «включи духовку на кухне»
        must not filter out an `oven_power` that lives in no room.
        """
        return [d for d in candidates if d.room == room_id or d.room == "global"]

    def _result_from_candidates(self, candidates: List[CatalogDevice], best: int,
                                device_reference: str, catalog: DeviceCatalog, locale: str,
                                context: UnifiedConversationContext,
                                spoken_room: Optional[str] = None) -> EntityResolutionResult:
        """Top-scored candidates → the handler-facing result (shared by the reference path and
        the utterance scan): room scoping, then payload or ambiguity.

        D-15: **the room named in the utterance is king** (BUG-38). It scopes the candidate set
        ALWAYS — including a single candidate, which is how «включи торшер в спальне» used to switch
        on the living-room floor lamp, the only «торшер» in the house. When the named room holds none
        of them, the answer is a refusal, not a quiet retarget to another room. Only when no room was
        named does the client's own room apply (rule 3), and there it stays a tie-break hint: it may
        narrow an ambiguity, never contradict the user.
        """
        room = match_catalog_room(spoken_room, catalog, locale) if spoken_room else None
        if room is not None:
            scoped = self._in_room(candidates, room.id)
            if not scoped:
                # named room, no such device in it → refuse; the handler speaks it (BUG-38)
                return EntityResolutionResult(
                    resolved_value=None,
                    original_value=device_reference,
                    confidence=0.0,
                    resolution_type="no_device_in_room",
                    metadata={"match_type": "catalog_wrong_room", "score": best,
                              "room_id": room.id,
                              "candidates": [d.id for d in candidates],
                              "catalog_version": catalog.version})
            candidates = scoped
        elif len(candidates) > 1:
            # D-15 rule 3: no room named → the requesting client's room breaks the tie («эппл»
            # names both Apple TVs). A hint, not an override: an empty intersection changes nothing.
            room_id = resolve_default_room(context, catalog)
            if room_id is not None:
                in_room = self._in_room(candidates, room_id)
                if in_room:
                    candidates = in_room

        if len(candidates) > 1:
            # name-level ambiguity («ночники» = two sconces) → candidates for the clarify path
            return EntityResolutionResult(
                resolved_value=[self._device_payload(d, locale) for d in candidates],
                original_value=device_reference,
                confidence=0.5,
                resolution_type="ambiguous",
                metadata={"match_type": "catalog_ambiguous", "score": best,
                          "candidates": [d.id for d in candidates],
                          "catalog_version": catalog.version})

        device = candidates[0]
        return EntityResolutionResult(
            resolved_value=self._device_payload(device, locale),
            original_value=device_reference,
            confidence=best / 100.0,
            resolution_type="exact" if best == 100 else "fuzzy",
            metadata={"match_type": "catalog", "score": best,
                      "device_id": device.id, "catalog_version": catalog.version})

    _SCAN_WORD_RE = re.compile(r"[а-яёa-z0-9]+")

    async def scan_utterance(self, text: str,
                             context: UnifiedConversationContext,
                             spoken_room: Optional[str] = None) -> Optional[EntityResolutionResult]:
        """Last-resort device spotting for utterances whose word order defeated the extraction
        regexes («на кухне вытяжку включи» — the device stands BEFORE the verb, so the post-verb
        capture never fires). Scores every content word against the catalog and accepts only
        exact/stem-grade hits (≥ _STEM_MATCH_SCORE): a scan has no extraction signal around it,
        so fuzzy-grade (≥80) would false-positive on generic words. Never triggers the ARCH-26
        re-pull — a scan miss is the normal case, not a staleness signal.

        `spoken_room` scopes the result exactly as on the reference path (BUG-38) — this path is the
        one «на кухне вытяжку включи» takes, so it needs the room every bit as much."""
        if self.catalog_port is None:
            return None
        catalog = self.catalog_port.catalog()
        if catalog is None:
            return None
        locale = context.language or "ru"
        best_score = 0
        best_devices: List[CatalogDevice] = []
        for word in self._SCAN_WORD_RE.findall(text.lower()):
            if len(word) < 3:
                continue
            ref_norm = _norm(word)
            for device in catalog.devices:
                score = _surface_score(ref_norm, device.surfaces(locale))
                if score < _STEM_MATCH_SCORE:
                    continue
                if score > best_score:
                    best_score, best_devices = score, [device]
                elif score == best_score and device not in best_devices:
                    best_devices.append(device)
        if not best_devices:
            return None
        return self._result_from_candidates(best_devices, best_score, text,
                                            catalog, locale, context, spoken_room)

    @staticmethod
    def _device_payload(device: CatalogDevice, locale: str) -> Dict[str, Any]:
        """The resolved-device shape handlers consume (enough to build a DeviceCommand)."""
        return {"device_id": device.id,
                "room": device.room,
                "name": device.names.get(locale) or device.names.get("ru") or device.id,
                "capabilities": [cap.name for cap in device.capabilities]}

    def _resolve_from_client_context(self, device_reference: str, device_reference_lower: str,
                                     available_devices: List[Dict[str, Any]],
                                     context: UnifiedConversationContext) -> Optional[EntityResolutionResult]:
        """Legacy path: ESP32-announced device capabilities + localization type-inference."""
        
        # 1. Exact name match
        for device in available_devices:
            device_name = device.get("name", "").lower()
            if device_name == device_reference_lower:
                return EntityResolutionResult(
                    resolved_value=device,
                    original_value=device_reference,
                    confidence=1.0,
                    resolution_type="exact",
                    metadata={"match_type": "exact_name", "device_id": device.get("id")}
                )
        
        # 2. Fuzzy name matching using rapidfuzz
        device_names = [device.get("name", "") for device in available_devices]
        best_match = process.extractOne(device_reference, device_names, scorer=fuzz.ratio)
        
        if best_match and best_match[1] >= 70:  # 70% similarity threshold
            for device in available_devices:
                if device.get("name", "") == best_match[0]:
                    return EntityResolutionResult(
                        resolved_value=device,
                        original_value=device_reference,
                        confidence=best_match[1] / 100.0,
                        resolution_type="fuzzy",
                        metadata={"match_type": "fuzzy_name", "similarity": best_match[1]}
                    )
        
        # 3. Type-based matching using localization files
        # Determine language from context
        language = context.language
        device_types = self._load_device_types(language)
        
        for device_type, keywords in device_types.items():
            if any(keyword in device_reference_lower for keyword in keywords):
                # Find devices of this type
                matching_devices = [d for d in available_devices 
                                  if d.get("type", "").lower() == device_type]
                
                if matching_devices:
                    # If only one device of this type, return it
                    if len(matching_devices) == 1:
                        return EntityResolutionResult(
                            resolved_value=matching_devices[0],
                            original_value=device_reference,
                            confidence=0.8,
                            resolution_type="contextual",
                            metadata={"match_type": "type_inference", "device_type": device_type}
                        )
                    else:
                        # Multiple devices, return list
                        return EntityResolutionResult(
                            resolved_value=matching_devices,
                            original_value=device_reference,
                            confidence=0.6,
                            resolution_type="contextual",
                            metadata={"match_type": "type_multiple", "device_type": device_type, 
                                    "count": len(matching_devices)}
                        )
        
        return None


class LocationEntityResolver:
    """Resolver for location/room entities.

    Catalog-backed when the bridge is wired (ARCH-8 PR-3): room references resolve against the
    catalog's rooms (names + aliases per locale — «зал» → living_room, «квартира» → global,
    RU-morphology-tolerant), then the ARCH-22 **D-15 multi-room policy** applies: a mentioned room
    the client covers → that room; a real room the client does NOT cover → `uncovered_room` (the
    handler speaks the error, no actuation); not a room at all → legacy path fall-through."""

    def __init__(self, asset_loader=None, catalog_port: Optional[DeviceCatalogPort] = None):
        self.asset_loader = asset_loader
        self.catalog_port = catalog_port
        self.logger = logging.getLogger(f"{__name__}.LocationEntityResolver")
        self._assets_warned = False  # warn-once guard for missing/empty localization assets

    def _warn_assets_once(self, message: str) -> None:
        """Log a degradation warning at most once per resolver (avoid per-request log spam)."""
        if not self._assets_warned:
            self.logger.warning(message)
            self._assets_warned = True

    def _load_location_keywords(self, language: str = "en") -> Dict[str, List[str]]:
        """Load location keywords from localization files.

        Best-effort: returns {} (with a one-time warning) when the asset loader isn't wired yet or
        the data is missing/empty, rather than raising. resolve() then skips "here"-inference and
        degrades to exact/fuzzy room matching — a location utterance must never abort the request
        just because deferred asset coordination hasn't run (QUAL-11 P0 #4)."""
        if not self.asset_loader:
            self._warn_assets_once(
                "LocationEntityResolver: asset loader not wired — skipping 'here'-inference "
                "(exact/fuzzy room matching still works)."
            )
            return {}

        try:
            room_localization = self.asset_loader.localizations.get("rooms", {})
            room_data = room_localization.get(language, {})

            if not room_data and language != "en":
                # Fallback to English
                room_data = room_localization.get("en", {})

            room_keywords = room_data.get("room_keywords", {}) if room_data else {}
            if not room_keywords:
                self._warn_assets_once(
                    f"LocationEntityResolver: no location keywords for language '{language}' "
                    f"in assets/localization/rooms/ — skipping 'here'-inference."
                )
                return {}

            return room_keywords
        except Exception as e:
            self._warn_assets_once(
                f"LocationEntityResolver: failed to load location keywords from localization files: {e} — "
                f"skipping 'here'-inference."
            )
            return {}
    
    
    async def resolve(self, location_reference: str, context: UnifiedConversationContext) -> Optional[EntityResolutionResult]:
        """
        Resolve location reference — catalog rooms + D-15 policy when wired, else client context.
        """
        if self.catalog_port is not None:
            catalog = self.catalog_port.catalog()
            if catalog is None:
                await self.catalog_port.refresh()
                catalog = self.catalog_port.catalog()
            if catalog is not None:
                result = self._resolve_room_d15(location_reference, context, catalog)
                if result is not None:
                    return result
                # not a catalog room → fall through (here-indicators / client-metadata rooms)

        location_lower = location_reference.lower().strip()
        
        # 1. Current room inference using localization files
        current_room = context.get_room_name()
        # Determine language from context
        language = context.language
        location_keywords = self._load_location_keywords(language)
        here_keywords = location_keywords.get("here_indicators", [])
        
        if current_room and any(keyword in location_lower for keyword in here_keywords):
            return EntityResolutionResult(
                resolved_value=current_room,
                original_value=location_reference,
                confidence=0.9,
                resolution_type="contextual",
                metadata={"match_type": "current_room", "room_name": current_room}
            )
        
        # 2. Room name matching from client metadata
        available_rooms = context.client_metadata.get("available_rooms", [])
        if available_rooms:
            # Exact match
            for room in available_rooms:
                if isinstance(room, dict):
                    room_name = room.get("name", "").lower()
                else:
                    room_name = str(room).lower()
                
                if room_name == location_lower:
                    return EntityResolutionResult(
                        resolved_value=room,
                        original_value=location_reference,
                        confidence=1.0,
                        resolution_type="exact",
                        metadata={"match_type": "room_name"}
                    )
            
            # Fuzzy match using rapidfuzz
            room_names = [r.get("name", str(r)) if isinstance(r, dict) else str(r) 
                        for r in available_rooms]
            best_match = process.extractOne(location_reference, room_names, scorer=fuzz.ratio)
            
            if best_match and best_match[1] >= 75:
                return EntityResolutionResult(
                    resolved_value=best_match[0],
                    original_value=location_reference,
                    confidence=best_match[1] / 100.0,
                    resolution_type="fuzzy",
                    metadata={"match_type": "room_fuzzy", "similarity": best_match[1]}
                )

        return None

    def _resolve_room_d15(self, location_reference: str, context: UnifiedConversationContext,
                          catalog: DeviceCatalog) -> Optional[EntityResolutionResult]:
        """Match a catalog room, then apply the D-15 coverage policy (esp32_satellite.md §8).

        Returns None when the reference is not a catalog room (D-15 rule 2c: fall through)."""
        locale = context.language or "ru"
        room = match_catalog_room(location_reference, catalog, locale)
        if room is None:
            return None

        spoken_name = room.names.get(locale) or room.names.get("ru") or room.id
        payload = {"room_id": room.id, "name": spoken_name}
        covered = _client_covered_rooms(context)
        if covered:
            covered_ids = set()
            for entry in covered:
                covered_room = match_catalog_room(entry, catalog, locale)
                if covered_room is not None:
                    covered_ids.add(covered_room.id)
            # `global` is addressable from anywhere — «выключи весь свет в квартире» is not
            # a per-room ask, and the whole-house aggregates live there by design (§5a).
            if room.id not in covered_ids and room.id != "global":
                # D-15 rule 2b: a real room this client does not manage → spoken error, no actuation
                return EntityResolutionResult(
                    resolved_value=payload,
                    original_value=location_reference,
                    confidence=1.0,
                    resolution_type="uncovered_room",
                    metadata={"match_type": "d15_uncovered", "room_id": room.id,
                              "catalog_version": catalog.version})

        return EntityResolutionResult(
            resolved_value=payload,
            original_value=location_reference,
            confidence=1.0,
            resolution_type="exact" if _norm(location_reference) in
            tuple(_norm(s) for s in room.surfaces(locale)) or location_reference == room.id
            else "fuzzy",
            metadata={"match_type": "catalog_room", "room_id": room.id,
                      "catalog_version": catalog.version})


class TemporalEntityResolver:
    """Resolver for time and date entities"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.TemporalEntityResolver")
    
    async def resolve(self, temporal_reference: str, context: UnifiedConversationContext) -> Optional[EntityResolutionResult]:
        """
        Resolve temporal references using context and patterns.
        """
        temporal_lower = temporal_reference.lower().strip()
        
        # Time pattern matching
        time_pattern = re.search(r'(\d{1,2}):(\d{2})', temporal_reference)
        if time_pattern:
            hours, minutes = time_pattern.groups()
            return EntityResolutionResult(
                resolved_value={"hours": int(hours), "minutes": int(minutes)},
                original_value=temporal_reference,
                confidence=0.95,
                resolution_type="exact",
                metadata={"match_type": "time_pattern", "format": "HH:MM"}
            )
        
        # Duration (value + time unit) via the shared bilingual parser — the one place time units live.
        parsed = parse_duration(temporal_lower)
        if parsed:
            value, unit = parsed
            return EntityResolutionResult(
                resolved_value={"value": value, "unit": unit},
                original_value=temporal_reference,
                confidence=0.9,
                resolution_type="exact",
                metadata={"match_type": "duration_pattern", "unit": unit}
            )
        
        # Relative time references (Russian + English)
        relative_times = {
            # Russian terms
            "сейчас": {"relative": "now", "offset": 0},
            "потом": {"relative": "future", "offset": None},
            "позже": {"relative": "future", "offset": None},
            "скоро": {"relative": "future", "offset": "short"},
            "вскоре": {"relative": "future", "offset": "short"},
            "сегодня": {"relative": "today", "offset": 0},
            "завтра": {"relative": "tomorrow", "offset": 1},
            "вчера": {"relative": "yesterday", "offset": -1},
            # English terms
            "now": {"relative": "now", "offset": 0},
            "later": {"relative": "future", "offset": None},
            "soon": {"relative": "future", "offset": "short"},
            "today": {"relative": "today", "offset": 0},
            "tomorrow": {"relative": "tomorrow", "offset": 1},
            "yesterday": {"relative": "yesterday", "offset": -1}
        }
        
        for keyword, time_info in relative_times.items():
            if keyword in temporal_lower:
                return EntityResolutionResult(
                    resolved_value=time_info,
                    original_value=temporal_reference,
                    confidence=0.8,
                    resolution_type="contextual",
                    metadata={"match_type": "relative_time", "keyword": keyword}
                )
        
        return None


class QuantityEntityResolver:
    """Resolver for quantity and number entities"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.QuantityEntityResolver")
    
    async def resolve(self, quantity_reference: str, context: UnifiedConversationContext) -> Optional[EntityResolutionResult]:
        """
        Resolve quantity references with unit inference.
        """
        quantity_lower = quantity_reference.lower().strip()
        
        # Number extraction
        number_pattern = re.search(r'(\d+(?:\.\d+)?)', quantity_reference)
        if number_pattern:
            number = float(number_pattern.group(1))
            
            # Unit inference (Russian + English). Non-time units (percent/degrees) stay here as the
            # nucleus of the future general unit-of-measurement layer; the TIME units reuse the ONE
            # shared surface table (no duplicate sec/min/hour lists).
            unit_patterns = {
                "percent": [
                    # Russian
                    "%", "процент", "процента", "процентов",
                    # English
                    "percent", "percentage"
                ],
                "degrees": [
                    # Russian
                    "градус", "градуса", "градусов", "°",
                    # English
                    "degrees", "degree"
                ],
                **{u: list(surfaces) for u, (_mult, surfaces) in TIME_UNITS.items()},
                "times": [
                    # Russian
                    "раз", "раза", "x",
                    # English
                    "times", "time", "x"
                ],
                "count": [
                    # Russian
                    "штук", "штука", "штуки", "элемент", "элемента", "элементов",
                    "предмет", "предмета", "предметов", "вещь", "вещи", "вещей",
                    # English
                    "items", "things", "pieces"
                ]
            }
            
            inferred_unit = "count"  # default
            for unit, keywords in unit_patterns.items():
                if any(keyword in quantity_lower for keyword in keywords):
                    inferred_unit = unit
                    break
            
            return EntityResolutionResult(
                resolved_value={"value": number, "unit": inferred_unit},
                original_value=quantity_reference,
                confidence=0.85,
                resolution_type="exact",
                metadata={"match_type": "number_with_unit", "inferred_unit": inferred_unit}
            )
        
        # Word numbers (Russian + English)
        word_numbers = {
            # Russian numbers
            "ноль": 0, "один": 1, "одна": 1, "одно": 1, "два": 2, "две": 2, 
            "три": 3, "четыре": 4, "пять": 5, "шесть": 6, "семь": 7, 
            "восемь": 8, "девять": 9, "десять": 10,
            # English numbers
            "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "none": 0, "a": 1, "an": 1
        }
        
        for word, number in word_numbers.items():
            if word in quantity_lower:
                return EntityResolutionResult(
                    resolved_value={"value": number, "unit": "count"},
                    original_value=quantity_reference,
                    confidence=0.8,
                    resolution_type="contextual",
                    metadata={"match_type": "word_number", "word": word}
                )
        
        return None 