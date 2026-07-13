"""The in-memory device catalog — the shared *world* commands resolve against (ARCH-8 PR-1).

Typed mirror of the bridge's `GET /system/catalog` response (`CatalogResponse`,
pinned in `locveil-commons/contracts/` — contract v1.1 + VWB-23 room-scoped group
addressing). The NLU/`DeviceEntityResolver` consume this model to turn spoken
surfaces into canonical commands: device/room `names`+`aliases` per locale, the
capability `group` overlay the noun lexicon binds to («свет» → the capabilities
tagged `light`, never the `power`-group plugs/oven), each room's
`group_defaults`, and typed action params (a param carries EITHER stable enum
`values` triplets OR `options_from`, a dynamic set enumerated at resolution
time).

This module is the data model only. Building it from the live bridge (HTTP pull
+ JSON parsing, ARCH-8 PR-2) is adapter work; the domain never learns where the
catalog came from. DeviceCatalog is **not** ClientRegistry: the registry is
what's physically wired to a satellite (room context for a *microphone*), the
catalog is everything actuable in the house (`mqtt_integration.md` §4).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class ValueLabel:
    """One enum value as a `{wire, canonical, labels}` triplet (§5a).

    `labels` are the spoken surfaces (QUAL-29 model), `canonical` is the token
    Irene sends in params; `wire` is informational (authoritative on the bus).
    """
    wire: str
    canonical: str
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CatalogParamSpec:
    """A typed action parameter (`CatalogParam`, contract v1.1).

    Carries EITHER `values` (a stable enum) OR `options_from` (the name of a
    dynamic set fetched at resolution time via `GET /devices/{id}/options/…`),
    never both.
    """
    name: str
    type: str
    required: bool = False
    default: Any = None
    min: Optional[float] = None
    max: Optional[float] = None
    unit: Optional[str] = None
    values: Optional[Tuple[ValueLabel, ...]] = None
    options_from: Optional[str] = None


@dataclass(frozen=True)
class CatalogActionSpec:
    """One action a capability offers (e.g. `power.on`, `climate.set_setpoint`)."""
    name: str
    params: Tuple[CatalogParamSpec, ...] = ()

    def param(self, name: str) -> Optional[CatalogParamSpec]:
        for p in self.params:
            if p.name == name:
                return p
        return None


@dataclass(frozen=True)
class CatalogFieldSpec:
    """One readable state field of a `sensor`-shaped capability (the read flow, §5c)."""
    name: str
    type: str = "float"
    unit: Optional[str] = None
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CatalogCapability:
    """A device capability: its actions (write) and/or fields (read), plus the
    semantic `group` the room-form addressing targets (VWB-23)."""
    name: str
    group: Optional[str] = None
    actions: Tuple[CatalogActionSpec, ...] = ()
    fields: Tuple[CatalogFieldSpec, ...] = ()

    def action(self, name: str) -> Optional[CatalogActionSpec]:
        for a in self.actions:
            if a.name == name:
                return a
        return None

    def field_spec(self, name: str) -> Optional[CatalogFieldSpec]:
        for f in self.fields:
            if f.name == name:
                return f
        return None


@dataclass(frozen=True)
class CatalogDevice:
    id: str
    room: Optional[str] = None
    names: Dict[str, str] = field(default_factory=dict)
    aliases: Dict[str, Tuple[str, ...]] = field(default_factory=dict)
    capabilities: Tuple[CatalogCapability, ...] = ()

    def capability(self, name: str) -> Optional[CatalogCapability]:
        for cap in self.capabilities:
            if cap.name == name:
                return cap
        return None

    def surfaces(self, locale: str) -> Tuple[str, ...]:
        """Every spoken surface for this device in `locale`: its name + aliases."""
        out: List[str] = []
        name = self.names.get(locale)
        if name:
            out.append(name)
        out.extend(self.aliases.get(locale, ()))
        return tuple(out)


@dataclass(frozen=True)
class CatalogRoom:
    id: str
    names: Dict[str, str] = field(default_factory=dict)
    aliases: Dict[str, Tuple[str, ...]] = field(default_factory=dict)
    devices: Tuple[str, ...] = ()
    group_defaults: Dict[str, str] = field(default_factory=dict)

    def surfaces(self, locale: str) -> Tuple[str, ...]:
        """Every spoken surface for this room in `locale`: its name + aliases."""
        out: List[str] = []
        name = self.names.get(locale)
        if name:
            out.append(name)
        out.extend(self.aliases.get(locale, ()))
        return tuple(out)


@dataclass(frozen=True)
class DeviceCatalog:
    """One pulled catalog snapshot (content-versioned by the bridge)."""
    version: str
    rooms: Tuple[CatalogRoom, ...] = ()
    devices: Tuple[CatalogDevice, ...] = ()

    def room(self, room_id: str) -> Optional[CatalogRoom]:
        for r in self.rooms:
            if r.id == room_id:
                return r
        return None

    def device(self, device_id: str) -> Optional[CatalogDevice]:
        for d in self.devices:
            if d.id == device_id:
                return d
        return None

    def devices_in_room(self, room_id: str) -> Tuple[CatalogDevice, ...]:
        return tuple(d for d in self.devices if d.room == room_id)

    def group_members(self, room_id: str, group: str) -> Tuple[CatalogDevice, ...]:
        """The room's devices carrying a capability tagged with `group` (VWB-23)."""
        return tuple(d for d in self.devices_in_room(room_id)
                     if any(cap.group == group for cap in d.capabilities))

    def group_default(self, room_id: str, group: str) -> Optional[str]:
        """The room's configured default device id for `group`, if declared."""
        room = self.room(room_id)
        return room.group_defaults.get(group) if room else None
