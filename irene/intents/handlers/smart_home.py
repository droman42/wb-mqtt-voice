"""Smart-home device handler (ARCH-8 PR-4 + QUAL-35 T1) — utterance → canonical command → speech.

The reference handler of the vertical slice: it turns a resolved smart-home intent into ONE
canonical command on the Irene↔bridge boundary and speaks the rich delivery outcome.

Address-form routing follows the depth doctrine (`canonical_first.md` §10, VWB-23): resolve only
as deep as the utterance specifies.

- A **group noun** («свет», «шторы», «жалюзи» — the donation's `group_noun` CHOICE, whose
  canonical values ARE catalog `CatalogCapability.group` names) → a **room-group command**
  `{room, group, action, scope}`; the BRIDGE picks the device via its `group_defaults`.
  Singular → `scope: auto`; «весь»/«все» → `scope: all` (force fan-out).
- A **named device** (the `target` param, resolved by the catalog-backed resolver, PR-3) → a
  **device command** `{device_id, capability, action, params}`. Scenarios ride this form.
- **No target at all** («поставь на паузу», «поставь 22 градуса») → capability lookup in the
  request room: one capable device → device form; several → clarification (F20/F21, the v1
  policy — priorities are QUAL-63).

Everything spoken comes from `assets/templates/smart_home/`; the §5b error-code enum maps to
phrases, `param_invalid`/ambiguity arm a one-shot clarification (QUAL-30/31), and a room-group
delivery speaks its per-member aggregate incl. partial failures («…, бра не ответило» — §10.4).

Dependencies (injected, QUAL-24): `DeviceCatalogPort` (the world) +
`DeviceCommandDeliveryPort` (awaited delivery). No HTTP, no bridge knowledge here.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from ..models import Intent, IntentResult
from ..context_models import UnifiedConversationContext
from ..device_catalog import CatalogDevice, DeviceCatalog
from ..device_commands import CanonicalCommand, DeviceCommand, GroupScope, RoomGroupCommand
from ..ports import DeviceCatalogPort, DeviceCommandDeliveryPort
from .base import IntentHandler
from ...core.donations import MissingRequiredParameter
# the ONE surface-normalization + RU-stem truth — shared with the catalog resolver so a value
# matched here behaves identically to a device name matched there
from ...core.entity_resolver import _norm, _stem_match, _MORPH_FUZZ_THRESHOLD, _STEM_MATCH_SCORE

# «весь свет» / «все шторы» — the plural/total signal → scope: all (VWB-23)
_ALL_SCOPE_RE = re.compile(r"\b(?:весь|все|всё|everywhere|all)\b", re.IGNORECASE)

# read quantities → the catalog field names that carry them, preference-ordered (PR-5).
# `room_temperature` is the measured value on climate devices; bare `temperature` is the
# dedicated sensors' field (on HVAC `temperature` is the SETPOINT — hence the ordering).
_QUANTITY_FIELDS = {
    "temperature": ("temperature", "room_temperature"),
    "humidity": ("humidity",),
}

# capability each method actuates, in preference order when a device carries several
_METHOD_CAPABILITY = {
    "power": ("power",),
    "cover": ("cover",),
    "climate": ("climate",),
    "brightness": ("brightness",),
    "playback": ("playback",),
    "scenario": ("scenario",),
}


class SmartHomeIntentHandler(IntentHandler):
    """Actuates the house through the bridge boundary — one utterance, one canonical command."""

    def __init__(self):
        super().__init__()
        self.catalog_port: Optional[DeviceCatalogPort] = None
        self.command_port: Optional[DeviceCommandDeliveryPort] = None

    def set_device_command_services(self, catalog_port: DeviceCatalogPort,
                                    command_port: DeviceCommandDeliveryPort) -> None:
        """Application injection (QUAL-24): the catalog world + the awaited delivery seam."""
        self.catalog_port = catalog_port
        self.command_port = command_port

    async def can_handle(self, intent: Intent) -> bool:
        return intent.domain == "smart_home"

    async def execute(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        return await self.execute_with_donation_routing(intent, context)

    # --- shared plumbing ---------------------------------------------------------------------

    def _catalog(self) -> Optional[DeviceCatalog]:
        return self.catalog_port.catalog() if self.catalog_port is not None else None

    def _lang(self, context: UnifiedConversationContext) -> str:
        return context.language or "ru"

    def _no_catalog_result(self, language: str) -> IntentResult:
        return IntentResult(text=self._get_template("err_no_catalog", language),
                            should_speak=True, success=False,
                            error="smart home catalog unavailable")

    async def _ask_slot(self, intent: Intent, context: UnifiedConversationContext,
                        param: str) -> IntentResult:
        """Explain-and-ask for one missing slot via the shared QUAL-30 boundary (arms the
        one-shot QUAL-31 resume). The spoken detail comes from this handler's templates."""
        detail = self._get_template(f"slot_{param}", self._lang(context))
        return await self._clarify(intent, context,
                                   MissingRequiredParameter(param, intent.name, detail))

    def _device_name(self, device: CatalogDevice, language: str) -> str:
        return device.names.get(language) or device.names.get("ru") or device.id

    def _room_spoken_name(self, catalog: DeviceCatalog, room_id: str, language: str) -> str:
        room = catalog.room(room_id)
        if room is None:
            return room_id
        return room.names.get(language) or room.names.get("ru") or room.id

    def _group_noun_surface(self, intent: Intent, group: str, language: str) -> str:
        """The word the user actually said for the group («жалюзи», not "cover") — recovered
        from the donation's choice_surfaces; falls back to the first declared surface."""
        spec = self._find_param_spec(intent, "group_noun")
        surfaces = (spec.choice_surfaces or {}).get(group, []) if spec else []
        text_norm = intent.raw_text.lower()
        for surface in surfaces:
            if re.search(rf"\b{re.escape(surface.lower())}\w*", text_norm):
                return surface
        return surfaces[0] if surfaces else group

    def _verified_group_noun(self, intent: Intent) -> Optional[str]:
        """The extracted group noun, kept only if one of its surfaces stands as a word in the
        utterance — the CHOICE fuzzy match alone would let «подсветка потолка» (a NAMED accent
        light) trigger the light group and break the depth doctrine."""
        group = self.get_param(intent, "group_noun", None)
        if not group:
            return None
        spec = self._find_param_spec(intent, "group_noun")
        surfaces = list((spec.choice_surfaces or {}).get(group, [])) if spec else []
        surfaces.append(group)  # the canonical is self-matchable (en: "light")
        text_norm = intent.raw_text.lower()
        for surface in surfaces:
            if re.search(rf"(?:^|\s){re.escape(surface.lower())}(?:\s|$)", text_norm):
                return group
        return None

    def _requested_room(self, intent: Intent, context: UnifiedConversationContext,
                        catalog: DeviceCatalog) -> Tuple[Optional[str], Optional[IntentResult]]:
        """The room the command addresses: the mentioned room (already resolved by PR-3's
        D-15 pass) or the client's room. Returns (room_id, error_result)."""
        language = self._lang(context)
        # the raw extracted room word (donation param `room`) — its RESOLVED form is what we
        # consume below; kept here for the miss log so an unmatched room isn't silently dropped
        raw_room = self.get_param(intent, "room", None)
        if intent.entities.get("room_resolution_type") == "uncovered_room":
            resolved = intent.entities.get("room_resolved") or {}
            return None, IntentResult(
                text=self._get_template("err_uncovered_room", language,
                                        room=resolved.get("name", "")),
                should_speak=True, success=False, error="room not covered by this device")
        resolved = intent.entities.get("room_resolved")
        if isinstance(resolved, dict) and resolved.get("room_id"):
            return resolved["room_id"], None
        if raw_room:
            self.logger.debug(f"room word '{raw_room}' did not resolve to a catalog room; "
                              f"falling back to the client's room")
        room_name = context.get_room_name()
        if room_name:
            from ...core.entity_resolver import match_catalog_room
            room = match_catalog_room(room_name, catalog, language)
            if room is not None:
                return room.id, None
        return None, None

    # --- delivery + speech ---------------------------------------------------------------------

    async def _deliver(self, command: CanonicalCommand,
                       context: UnifiedConversationContext) -> Optional[Any]:
        if self.command_port is None:
            return None
        return await self.command_port.deliver_device_command(command, context)

    async def _speak_outcome(self, delivery: Optional[Any], ok_text: str, language: str,
                       catalog: Optional[DeviceCatalog] = None,
                       clarify_intent: Optional[Intent] = None,
                       context: Optional[UnifiedConversationContext] = None) -> IntentResult:
        """Map the rich DeliveryResult (§5b) — or its absence — to speech."""
        if delivery is None:
            return IntentResult(text=self._get_template("err_not_sure", language),
                                should_speak=True, success=False,
                                error="device command delivery unavailable/timed out")

        if delivery.delivered:
            partial = self._failed_members(delivery, catalog, language)
            if partial:
                return IntentResult(
                    text=self._get_template("confirm_partial", language,
                                            ok=ok_text, failed=partial),
                    should_speak=True,
                    metadata={"device_command_echo": delivery.echoed_value})
            return IntentResult(text=ok_text, should_speak=True,
                                metadata={"device_command_echo": delivery.echoed_value})

        code = delivery.error_code or "internal_error"
        if code == "param_invalid" and clarify_intent is not None and context is not None:
            # §5b: field+reason ride DeliveryResult.detail — the clarify path takes over
            return await self._clarify(clarify_intent, context, MissingRequiredParameter(
                "param", clarify_intent.name, delivery.detail or ""))
        template_key = {
            "device_not_found": "err_device_not_found_bridge",
            "capability_not_supported": "err_capability",
            "action_not_supported": "err_action",
            "param_invalid": "err_param_invalid",
            "device_unreachable": "err_device_unreachable",
            "internal_error": "err_internal",
            "bridge_unreachable": "err_bridge_down",
        }.get(code, "err_internal")
        return IntentResult(text=self._get_template(template_key, language),
                            should_speak=True, success=False,
                            error=f"bridge error {code}: {delivery.detail}")

    def _failed_members(self, delivery: Any, catalog: Optional[DeviceCatalog],
                        language: str) -> Optional[str]:
        """Names of room-group members that failed/skipped (the §10.4 aggregate speech)."""
        echoed = delivery.echoed_value
        if not isinstance(echoed, list):
            return None
        failed_names: List[str] = []
        for member in echoed:
            if isinstance(member, dict) and member.get("status") in ("failed", "skipped"):
                device_id = member.get("device_id", "")
                device = catalog.device(device_id) if catalog else None
                failed_names.append(self._device_name(device, language) if device else device_id)
        return ", ".join(failed_names) if failed_names else None

    def _ambiguous_result(self, intent: Intent, context: UnifiedConversationContext,
                          candidates: List[Dict[str, Any]], param: str) -> IntentResult:
        """Name-level or capability-level ambiguity → one-shot clarification (v1 policy; QUAL-63
        adds priority rules later)."""
        language = self._lang(context)
        options = " или ".join(c.get("name", c.get("device_id", "?")) for c in candidates) \
            if language == "ru" else \
            " or ".join(c.get("name", c.get("device_id", "?")) for c in candidates)
        context.set_pending_clarification(intent.name, param, intent.raw_text)
        return IntentResult(
            text=self._get_template("clarify_which", language, options=options),
            should_speak=True,
            metadata={"clarification": True, "clarification_reason": "ambiguous_device",
                      "candidates": [c.get("device_id") for c in candidates]})

    # --- target selection ------------------------------------------------------------------------

    def _resolved_target(self, intent: Intent) -> Tuple[Optional[Dict[str, Any]],
                                                        Optional[List[Dict[str, Any]]], bool]:
        """(device, ambiguous_candidates, resolution_failed) from the PR-3 resolver output."""
        resolved = intent.entities.get("target_resolved")
        if intent.entities.get("target_resolution_type") == "ambiguous" \
                and isinstance(resolved, list):
            return None, resolved, False
        if isinstance(resolved, dict):
            return resolved, None, False
        return None, None, bool(intent.entities.get("target_resolution_failed"))

    def _capable_devices(self, catalog: DeviceCatalog, room_id: Optional[str],
                         capability: str, language: str) -> List[Dict[str, Any]]:
        devices = catalog.devices_in_room(room_id) if room_id else catalog.devices
        return [{"device_id": d.id, "room": d.room, "name": self._device_name(d, language)}
                for d in devices if d.capability(capability) is not None]

    def _pick_capability(self, device: CatalogDevice, wanted: Tuple[str, ...]) -> Optional[str]:
        for name in wanted:
            if device.capability(name) is not None:
                return name
        return None

    # --- the actuation core ------------------------------------------------------------------------

    async def _actuate(self, intent: Intent, context: UnifiedConversationContext, *,
                       kind: str, device_action: str, group_action: Optional[str] = None,
                       params: Optional[Dict[str, Any]] = None,
                       ok_key_device: str = "", ok_key_room: str = "") -> IntentResult:
        """Shared depth-doctrine routing for power/cover: group noun → room form; named device →
        device form; ambiguity → clarify."""
        language = self._lang(context)
        catalog = self._catalog()
        if catalog is None:
            return self._no_catalog_result(language)

        group = self._verified_group_noun(intent)
        if group is not None:
            return await self._room_group(intent, context, catalog, group=group,
                                          action=group_action or device_action,
                                          ok_key=ok_key_room)

        device, ambiguous, failed = self._resolved_target(intent)
        if ambiguous:
            return self._ambiguous_result(intent, context, ambiguous, "target")
        if device is None:
            original = self.get_param(intent, "target", None) or intent.raw_text
            if failed:
                return IntentResult(text=self._get_template("err_device_not_found", language,
                                                            ref=str(original)),
                                    should_speak=True, success=False,
                                    error=f"unresolvable device reference: {original}")
            # no target and no group noun — nothing to actuate on
            return await self._ask_slot(intent, context, "target")

        catalog_device = catalog.device(device["device_id"])
        if catalog_device is None:
            return IntentResult(text=self._get_template("err_device_not_found", language,
                                                        ref=device.get("name", device["device_id"])),
                                should_speak=True, success=False, error="device left the catalog")
        capability = self._pick_capability(catalog_device, _METHOD_CAPABILITY[kind])
        if capability is None:
            return IntentResult(
                text=self._get_template("err_capability", language),
                should_speak=True, success=False,
                error=f"{catalog_device.id} lacks {kind} capability")

        command = DeviceCommand(device_id=catalog_device.id, capability=capability,
                                action=device_action, params=params)
        delivery = await self._deliver(command, context)
        ok_text = self._get_template(ok_key_device, language,
                                     name=self._device_name(catalog_device, language),
                                     **(params or {}))
        return await self._speak_outcome(delivery, ok_text, language, catalog,
                                   clarify_intent=intent, context=context)

    async def _room_group(self, intent: Intent, context: UnifiedConversationContext,
                          catalog: DeviceCatalog, *, group: str, action: str,
                          ok_key: str) -> IntentResult:
        language = self._lang(context)
        room_id, room_error = self._requested_room(intent, context, catalog)
        if room_error is not None:
            return room_error
        if room_id is None:
            return await self._ask_slot(intent, context, "room")

        # bind the noun to catalog truth: the room must actually have members of this group
        if not catalog.group_members(room_id, group) and catalog.group_default(room_id, group) is None:
            return IntentResult(
                text=self._get_template("err_no_group_in_room", language,
                                        noun=self._group_noun_surface(intent, group, language),
                                        room=self._room_spoken_name(catalog, room_id, language)),
                should_speak=True, success=False,
                error=f"room {room_id} has no {group} group members")

        scope = GroupScope.ALL if _ALL_SCOPE_RE.search(intent.raw_text) else GroupScope.AUTO
        command = RoomGroupCommand(room_id=room_id, group=group, action=action, scope=scope)
        delivery = await self._deliver(command, context)
        ok_text = self._get_template(ok_key, language,
                                     noun=self._group_noun_surface(intent, group, language),
                                     room=self._room_spoken_name(catalog, room_id, language))
        return await self._speak_outcome(delivery, ok_text, language, catalog,
                                   clarify_intent=intent, context=context)

    async def _single_capable_or_clarify(self, intent: Intent,
                                         context: UnifiedConversationContext,
                                         capability: str) -> Tuple[Optional[CatalogDevice],
                                                                   Optional[IntentResult]]:
        """No named target: exactly one `capability`-capable device in the room → it; several →
        clarify (the F20/F21 v1 policy); none → spoken miss."""
        language = self._lang(context)
        catalog = self._catalog()
        if catalog is None:
            return None, self._no_catalog_result(language)

        device, ambiguous, failed = self._resolved_target(intent)
        if ambiguous:
            return None, self._ambiguous_result(intent, context, ambiguous, "target")
        if device is not None:
            catalog_device = catalog.device(device["device_id"])
            if catalog_device is not None:
                return catalog_device, None
        if failed:
            original = self.get_param(intent, "target", None) or ""
            return None, IntentResult(
                text=self._get_template("err_device_not_found", language, ref=str(original)),
                should_speak=True, success=False, error="unresolvable device reference")

        room_id, room_error = self._requested_room(intent, context, catalog)
        if room_error is not None:
            return None, room_error
        capable = self._capable_devices(catalog, room_id, capability, language)
        if not capable:
            return None, IntentResult(
                text=self._get_template("err_nothing_capable", language),
                should_speak=True, success=False,
                error=f"no {capability}-capable device in scope")
        if len(capable) > 1:
            return None, self._ambiguous_result(intent, context, capable, "target")
        return catalog.device(capable[0]["device_id"]), None

    # --- donation-routed methods ---------------------------------------------------------------

    async def _handle_power_on(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        return await self._actuate(intent, context, kind="power", device_action="on",
                                   ok_key_device="confirm_on", ok_key_room="confirm_room_on")

    async def _handle_power_off(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        return await self._actuate(intent, context, kind="power", device_action="off",
                                   ok_key_device="confirm_off", ok_key_room="confirm_room_off")

    async def _handle_cover_open(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        return await self._actuate(intent, context, kind="cover", device_action="open",
                                   ok_key_device="confirm_open", ok_key_room="confirm_room_open")

    async def _handle_cover_close(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        return await self._actuate(intent, context, kind="cover", device_action="close",
                                   ok_key_device="confirm_close", ok_key_room="confirm_room_close")

    async def _handle_set_setpoint(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        language = self._lang(context)
        temp = self.get_param(intent, "temp", None)
        if temp is None:
            return await self._ask_slot(intent, context, "temp")
        device, error = await self._single_capable_or_clarify(intent, context, "climate")
        if error is not None:
            return error
        assert device is not None
        catalog = self._catalog()

        # contract-backed pre-validation (§5b: most param_invalid never round-trips)
        capability = device.capability("climate")
        action = capability.action("set_setpoint") if capability else None
        spec = action.param("temp") if action else None
        if spec is not None and ((spec.min is not None and temp < spec.min)
                                 or (spec.max is not None and temp > spec.max)):
            context.set_pending_clarification(intent.name, "temp", intent.raw_text)
            return IntentResult(
                text=self._get_template("err_param_range", language,
                                        min=spec.min, max=spec.max,
                                        unit=spec.unit or ""),
                should_speak=True,
                metadata={"clarification": True, "clarification_reason": "out_of_range"})

        command = DeviceCommand(device_id=device.id, capability="climate",
                                action="set_setpoint", params={"temp": temp})
        delivery = await self._deliver(command, context)
        ok_text = self._get_template("confirm_setpoint", language, temp=temp,
                                     name=self._device_name(device, language))
        return await self._speak_outcome(delivery, ok_text, language, catalog,
                                   clarify_intent=intent, context=context)

    async def _handle_set_brightness(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        language = self._lang(context)
        level = self.get_param(intent, "level", None)
        if level is None:
            return await self._ask_slot(intent, context, "level")
        device, error = await self._single_capable_or_clarify(intent, context, "brightness")
        if error is not None:
            return error
        assert device is not None
        command = DeviceCommand(device_id=device.id, capability="brightness",
                                action="set", params={"level": level})
        delivery = await self._deliver(command, context)
        ok_text = self._get_template("confirm_brightness", language, level=level,
                                     name=self._device_name(device, language))
        return await self._speak_outcome(delivery, ok_text, language, self._catalog(),
                                   clarify_intent=intent, context=context)

    async def _handle_playback_pause(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        language = self._lang(context)
        device, error = await self._single_capable_or_clarify(intent, context, "playback")
        if error is not None:
            return error
        assert device is not None
        command = DeviceCommand(device_id=device.id, capability="playback",
                                action="pause", params=None)
        delivery = await self._deliver(command, context)
        ok_text = self._get_template("confirm_pause", language,
                                     name=self._device_name(device, language))
        return await self._speak_outcome(delivery, ok_text, language, self._catalog(),
                                   clarify_intent=intent, context=context)

    async def _handle_scenario_start(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        return await self._scenario(intent, context, start=True)

    async def _handle_scenario_stop(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        return await self._scenario(intent, context, start=False)

    async def _scenario(self, intent: Intent, context: UnifiedConversationContext, *,
                        start: bool) -> IntentResult:
        """Scenario enums ride the device form: match the spoken words against the scenario
        device's `{wire, canonical, labels}` triplets (QUAL-29 — labels are the surfaces, the
        canonical goes on the wire). Exact-ru-label matching is T1; the transliteration-tolerant
        tier («эппл ти ви» → "Apple TV") is QUAL-35 T2."""
        language = self._lang(context)
        catalog = self._catalog()
        if catalog is None:
            return self._no_catalog_result(language)

        room_id, room_error = self._requested_room(intent, context, catalog)
        if room_error is not None:
            return room_error
        scenario_devices = [d for d in (catalog.devices_in_room(room_id) if room_id else catalog.devices)
                            if d.capability("scenario") is not None]
        if not scenario_devices and room_id:
            scenario_devices = [d for d in catalog.devices if d.capability("scenario") is not None]
        if not scenario_devices:
            return IntentResult(text=self._get_template("err_nothing_capable", language),
                                should_speak=True, success=False, error="no scenario device")
        device = scenario_devices[0]

        if not start:
            command = DeviceCommand(device_id=device.id, capability="scenario",
                                    action="off", params=None)
            delivery = await self._deliver(command, context)
            return await self._speak_outcome(delivery, self._get_template("confirm_scenario_off", language),
                                       language, catalog, clarify_intent=intent, context=context)

        capability = device.capability("scenario")
        action = capability.action("set") if capability else None
        spec = action.param("value") if action else None
        values = spec.values or () if spec else ()
        best_label, best_canonical, best_score = None, None, 0
        from rapidfuzz import fuzz
        text_norm = intent.raw_text.lower().replace("ё", "е")
        for value in values:
            label = value.labels.get(language) or value.labels.get("ru") or value.canonical
            score = int(fuzz.partial_ratio(label.lower().replace("ё", "е"), text_norm))
            if score > best_score:
                best_label, best_canonical, best_score = label, value.canonical, score
        if best_canonical is None or best_score < 85:
            options = ", ".join((v.labels.get(language) or v.canonical) for v in values[:5])
            context.set_pending_clarification(intent.name, "scenario", intent.raw_text)
            return IntentResult(text=self._get_template("clarify_scenario", language, options=options),
                                should_speak=True,
                                metadata={"clarification": True,
                                          "clarification_reason": "unknown_scenario"})

        command = DeviceCommand(device_id=device.id, capability="scenario",
                                action="set", params={"value": best_canonical})
        delivery = await self._deliver(command, context)
        ok_text = self._get_template("confirm_scenario", language, label=best_label)
        return await self._speak_outcome(delivery, ok_text, language, catalog,
                                   clarify_intent=intent, context=context)

    # --- the read flow (ARCH-8 PR-5, §5c) --------------------------------------------------------

    def _find_readable(self, catalog: DeviceCatalog, room_id: Optional[str],
                       field_names: Tuple[str, ...]) -> Optional[Tuple[CatalogDevice, str, str]]:
        """(device, capability, field) carrying one of `field_names`, dedicated `sensor`
        capabilities first (a sensors box beats a climate unit for «какая температура»);
        field-name preference order breaks ties within a device."""
        devices = catalog.devices_in_room(room_id) if room_id else catalog.devices
        candidates: List[Tuple[int, int, CatalogDevice, str, str]] = []
        for device in devices:
            for capability in device.capabilities:
                if capability.name == "sensor":
                    effective = field_names
                else:
                    # on climate devices the bare `temperature` field is the SETPOINT
                    # («уставка») — the measured value is `room_temperature`; prefer it
                    effective = tuple(sorted(field_names,
                                             key=lambda f: 0 if f.startswith("room_") else 1))
                for rank, field_name in enumerate(effective):
                    if capability.field_spec(field_name) is not None:
                        sensor_rank = 0 if capability.name == "sensor" else 1
                        candidates.append((sensor_rank, rank, device, capability.name, field_name))
        if not candidates:
            return None
        candidates.sort(key=lambda c: (c[0], c[1]))
        _, _, device, capability_name, field_name = candidates[0]
        return device, capability_name, field_name

    async def _handle_read_state(self, intent: Intent,
                                 context: UnifiedConversationContext) -> IntentResult:
        """«какая температура в спальне» → resolve room → readable device/field →
        GET state via the read port → speak the value with the catalog's unit. A read
        never actuates and never rides the OutputManager (§13.3)."""
        language = self._lang(context)
        catalog = self._catalog()
        if catalog is None:
            return self._no_catalog_result(language)

        quantity = self.get_param(intent, "quantity", None)
        if quantity not in _QUANTITY_FIELDS:
            return await self._ask_slot(intent, context, "quantity")
        room_id, room_error = self._requested_room(intent, context, catalog)
        if room_error is not None:
            return room_error

        found = self._find_readable(catalog, room_id, _QUANTITY_FIELDS[quantity])
        if found is None and room_id is not None:
            found = self._find_readable(catalog, None, _QUANTITY_FIELDS[quantity])
        if found is None:
            return IntentResult(text=self._get_template("err_no_sensor", language),
                                should_speak=True, success=False,
                                error=f"no readable {quantity} field in scope")
        device, capability_name, field_name = found

        assert self.catalog_port is not None
        state = await self.catalog_port.read_state(device.id)
        value = state.get(field_name) if isinstance(state, dict) else None
        if value is None:
            return IntentResult(text=self._get_template("err_not_sure", language),
                                should_speak=True, success=False,
                                error=f"state read failed for {device.id}.{field_name}")
        if isinstance(value, float) and value == int(value):
            value = int(value)
        return IntentResult(
            text=self._get_template(f"read_{quantity}", language, value=value,
                                    name=self._device_name(device, language)),
            should_speak=True,
            metadata={"read": {"device_id": device.id, "capability": capability_name,
                               "field": field_name, "value": value}})

    # --- select-form capabilities (QUAL-65, VWB-19 §11) -------------------------------------------

    @staticmethod
    def _match_option(spoken: str, options: List[str]) -> Optional[str]:
        """Match a spoken value against an option set: normalized exact (case/ё/spacing),
        then shared-stem, then fuzzy. Technical identifiers are self-matchable (the
        donation-choice-surfaces rule); Cyrillic↔Latin transliteration is QUAL-35 T2."""
        from rapidfuzz import fuzz
        spoken_norm = _norm(spoken).replace(" ", "")
        best, best_score = None, 0
        for option in options:
            option_norm = _norm(str(option)).replace(" ", "")
            if option_norm == spoken_norm:
                return str(option)
            score = int(fuzz.ratio(spoken_norm, option_norm))
            if score < _STEM_MATCH_SCORE and _stem_match(spoken_norm, option_norm):
                score = _STEM_MATCH_SCORE
            if score > best_score:
                best, best_score = str(option), score
        return best if best_score >= _MORPH_FUZZ_THRESHOLD else None

    async def _selectable_options(self, device: CatalogDevice, capability_name: str,
                                  action_name: str, param_name: str) -> Optional[List[str]]:
        """The valid values for a select-form param: static `values` canonicals from the
        catalog (by_value), or the runtime set via `options_from` (parametric — the
        read port fetches + caches it)."""
        capability = device.capability(capability_name)
        action = capability.action(action_name) if capability else None
        spec = action.param(param_name) if action else None
        if spec is None:
            return None
        if spec.values:
            return [v.canonical for v in spec.values]
        if spec.options_from and self.catalog_port is not None:
            return await self.catalog_port.read_options(device.id, spec.options_from)
        return None

    async def _select_value(self, intent: Intent, context: UnifiedConversationContext, *,
                            capability: str, action: str, param: str, spoken: str,
                            device: CatalogDevice, ok_key: str) -> IntentResult:
        """Shared tail of input/app selection: enumerate the valid set, match the spoken
        value, emit the canonical command; a miss clarifies naming what IS available."""
        language = self._lang(context)
        options = await self._selectable_options(device, capability, action, param)
        if options is None:
            return IntentResult(text=self._get_template("err_no_options", language,
                                                        name=self._device_name(device, language)),
                                should_speak=True, success=False,
                                error=f"no option set for {device.id}.{capability}")
        matched = self._match_option(spoken, options)
        if matched is None:
            context.set_pending_clarification(intent.name, param, intent.raw_text)
            return IntentResult(
                text=self._get_template("clarify_option", language,
                                        options=", ".join(str(o) for o in options[:6])),
                should_speak=True,
                metadata={"clarification": True, "clarification_reason": "unknown_option",
                          "options": options})
        command = DeviceCommand(device_id=device.id, capability=capability,
                                action=action, params={param: matched})
        delivery = await self._deliver(command, context)
        ok_text = self._get_template(ok_key, language, value=matched,
                                     name=self._device_name(device, language))
        return await self._speak_outcome(delivery, ok_text, language, self._catalog(),
                                         clarify_intent=intent, context=context)

    async def _handle_input_select(self, intent: Intent,
                                   context: UnifiedConversationContext) -> IntentResult:
        """«переключи усилитель на cd» → input.set {value} (VWB-19: `set` is the reserved
        canonical action for select-form capabilities; by_value validates offline,
        parametric enumerates at resolution time)."""
        spoken = self.get_param(intent, "value", None)
        if not spoken:
            return await self._ask_slot(intent, context, "value")
        device, error = await self._single_capable_or_clarify(intent, context, "input")
        if error is not None:
            return error
        assert device is not None
        return await self._select_value(intent, context, capability="input", action="set",
                                        param="value", spoken=str(spoken), device=device,
                                        ok_key="confirm_input")

    async def _handle_app_launch(self, intent: Intent,
                                 context: UnifiedConversationContext) -> IntentResult:
        """«запусти youtube на телеке» → apps.launch {app} — the launchable set is
        runtime-dynamic (installed apps), enumerated via options_from."""
        spoken = self.get_param(intent, "app", None)
        if not spoken:
            return await self._ask_slot(intent, context, "app")
        device, error = await self._single_capable_or_clarify(intent, context, "apps")
        if error is not None:
            return error
        assert device is not None
        return await self._select_value(intent, context, capability="apps", action="launch",
                                        param="app", spoken=str(spoken), device=device,
                                        ok_key="confirm_app")
