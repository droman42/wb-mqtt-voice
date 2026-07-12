"""
Client Registration System

Manages client identification, capabilities, and room/device context for ESP32 nodes,
web clients, and other system endpoints. Provides unified client registration and
discovery for context-aware processing.
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path

from ..config.models import AssetConfig  # ARCH-28: state_root for persisted registrations

logger = logging.getLogger(__name__)


@dataclass
class ClientDevice:
    """Represents a device available in a client context"""
    id: str
    name: str
    type: str  # "light", "switch", "sensor", "speaker", "tv", etc.
    capabilities: Dict[str, Any] = field(default_factory=dict)
    location: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClientRegistration:
    """Complete client registration with identity and capabilities"""
    client_id: str
    room_name: str  # the PRIMARY room (ARCH-22 D-14: `primary_room` is an alias of this)
    name: Optional[str] = None  # human-friendly device name (ARCH-22 D-14)
    # ARCH-22 D-14: the rooms this device manages. The resolver (ARCH-7/QUAL-35) treats the primary
    # room as implicitly covered; carried ready-but-inert until those handlers land.
    covered_rooms: List[str] = field(default_factory=list)
    # ARCH-22: the device's output AudioContract {rate, channels, width} — drives the reply conform.
    audio_out: Dict[str, Any] = field(default_factory=dict)
    firmware_version: Optional[str] = None
    model_version: Optional[str] = None
    # ARCH-47: version-reporting fields — what the device was built against, reported at
    # register so the registry can flag staleness (the stale-pin tripwire; the config-ui
    # surfacing is ARCH-48). protocol_version pairs with the served WS_PROTOCOL_VERSION;
    # wake_pack_version is the flashed wake-pack tag (`wake-pack-vN`) — ESP32-honest,
    # optional for clients that do their own wake-word management.
    protocol_version: Optional[str] = None
    wake_pack_version: Optional[str] = None
    language: str = "ru"
    location: Optional[str] = None
    client_type: str = "unknown"  # "esp32", "web", "mobile", "desktop"

    # Device capabilities
    available_devices: List[ClientDevice] = field(default_factory=list)
    
    # Client capabilities
    capabilities: Dict[str, bool] = field(default_factory=dict)
    
    # Registration metadata
    registered_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    source_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert registration to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClientRegistration':
        """Create registration from dictionary. Tolerant of extra keys (ARCH-6: the WS handshake frame
        also carries control fields like `type`/`sample_rate`/`wants_audio`) — only known registration
        fields are used; devices likewise keep only ClientDevice fields."""
        import dataclasses
        data = dict(data)  # don't mutate the caller's frame
        # ARCH-22 D-14: `primary_room` is an alias for `room_name` (the canonical primary room).
        if "room_name" not in data and "primary_room" in data:
            data["room_name"] = data["primary_room"]
        reg_fields = {f.name for f in dataclasses.fields(cls)}
        dev_fields = {f.name for f in dataclasses.fields(ClientDevice)}

        devices = [ClientDevice(**{k: v for k, v in device.items() if k in dev_fields})
                   if isinstance(device, dict) else device
                   for device in (data.get('available_devices') or [])]

        registration_data = {k: v for k, v in data.items() if k in reg_fields}
        registration_data['available_devices'] = devices
        return cls(**registration_data)

    @property
    def primary_room(self) -> str:
        """ARCH-22 D-14: the primary room is the canonical `room_name`."""
        return self.room_name
    
    def update_last_seen(self):
        """Update last seen timestamp"""
        self.last_seen = time.time()
    
    def get_device_by_name(self, device_name: str) -> Optional[ClientDevice]:
        """Find device by name with fuzzy matching"""
        device_name_lower = device_name.lower()
        
        # Exact match first
        for device in self.available_devices:
            if device.name.lower() == device_name_lower:
                return device
        
        # Partial match fallback
        for device in self.available_devices:
            if device_name_lower in device.name.lower():
                return device
        
        return None


@dataclass
class ActionRecord:
    """Runtime-only record of a live fire-and-forget action (QUAL-28).

    Lives in the ``ClientRegistry`` action store, NOT on the persisted registration record —
    it holds a live ``asyncio.Task`` ref and must never be serialized or survive a restart.
    Keyed by the unique ``action_name`` (its identity); ``domain`` is a secondary index used by
    the contextual-command resolver.
    """
    action_name: str                         # unique identity = the store key
    domain: str                              # router index, e.g. "timers" / "audio_playback"
    physical_id: str                         # the stable scope this action belongs to
    task: Optional[asyncio.Task] = None      # live task ref — authoritative liveness signal
    started_at: float = field(default_factory=time.time)
    expected_end: Optional[float] = None     # bounded actions (timers): started_at + duration (+grace)
    status: str = "running"
    timed_out: bool = False                  # set by the timeout monitor before it cancels (BUG-19:
                                             # lets the done-callback distinguish timeout from user-cancel)
    deliberate_cancel: bool = False          # set BEFORE .cancel() by paths that revoke the promise
                                             # (user cancel, store-cap eviction); an unmarked cancel is
                                             # process teardown — the durable record must then survive
                                             # for restart reconciliation (ARCH-28 shutdown discipline)
    durable: bool = False                    # ARCH-28: a persisted record exists; completion must delete it
    redeliver: bool = False                  # ARCH-28 D-6: completion notice survives an offline reply channel
    session_id: Optional[str] = None         # conversation that launched it (informational)
    room_id: Optional[str] = None
    source: Optional[str] = None             # originating channel (cli/web/ws/…) for deferred-result addressing (ARCH-15 PR-4)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_live(self) -> bool:
        """Authoritative liveness: live iff the task is still running.

        Falls back to the TTL (``expected_end``) when there is no task ref, and finally to
        'assume live' so we never reap something we can't prove is dead.
        """
        if self.task is not None:
            return not self.task.done()
        if self.expected_end is not None:
            return time.time() <= self.expected_end
        return True


class ClientRegistry:
    """
    Central registry for client identification and capabilities.

    Manages registration, discovery, and context information for all clients
    including ESP32 nodes, web clients, and other system endpoints.

    Also owns the **runtime-only action store** (QUAL-28): a non-persisted table of live
    fire-and-forget actions keyed by ``physical_id`` → ``action_name`` → ``ActionRecord``. It is
    deliberately separate from ``self.clients`` (the persisted registrations) so it never
    serializes and never survives a restart.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.clients: Dict[str, ClientRegistration] = {}

        # Runtime-only action store (QUAL-28): physical_id -> {action_name -> ActionRecord}.
        # NEVER persisted (holds live task refs; must not survive a restart). _save_registrations
        # only serializes self.clients, so this attribute is excluded by construction.
        self._actions: Dict[str, Dict[str, ActionRecord]] = {}
        # Completed-action history, also runtime-only and physical-identity-scoped (so it survives
        # conversation-session eviction, per Q3). Capped per identity.
        self._recent_actions: Dict[str, List[Dict[str, Any]]] = {}
        self._failed_actions: Dict[str, List[Dict[str, Any]]] = {}
        self._action_error_count: Dict[str, Dict[str, int]] = {}

        # Configuration
        self.registration_timeout = self.config.get('registration_timeout', 3600)  # 1 hour
        self.persistent_storage = self.config.get('persistent_storage', True)
        # ARCH-28: registrations live under the asset-managed state tree (volume-mounted —
        # survives container replacement). The old default was cwd-relative `cache/`, i.e.
        # INSIDE the container: registrations silently died with it. Legacy files are
        # migrated on first load (see _load_registrations).
        explicit_path = self.config.get('storage_path')
        if explicit_path:
            self.storage_path = Path(explicit_path)
        elif self.persistent_storage:
            self.storage_path = AssetConfig().state_root / 'client_registry.json'
        else:
            self.storage_path = Path('client_registry.json')  # inert (persistence disabled)
        self.max_actions_per_identity = self.config.get('max_actions_per_identity', 32)

        # Load existing registrations
        if self.persistent_storage:
            self._load_registrations()
    
    async def register_client(self, registration: ClientRegistration) -> bool:
        """
        Register a new client or update existing registration.
        
        Args:
            registration: Client registration information
            
        Returns:
            True if registration successful
        """
        try:
            registration.update_last_seen()
            self.clients[registration.client_id] = registration
            
            logger.info(f"Registered client '{registration.client_id}' in room '{registration.room_name}' "
                       f"with {len(registration.available_devices)} devices")
            
            # Save to persistent storage
            if self.persistent_storage:
                self._save_registrations()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register client '{registration.client_id}': {e}")
            return False
    
    async def register_esp32_node(self, client_id: str, room_name: str, 
                                 devices: List[Dict[str, Any]], 
                                 source_address: Optional[str] = None,
                                 language: str = "ru") -> bool:
        """
        Register an ESP32 node with its device capabilities.
        
        Args:
            client_id: ESP32 node identifier (e.g., "kitchen_node")
            room_name: Human-readable room name (e.g., "Кухня")
            devices: List of device specifications
            source_address: IP address of the ESP32 node
            language: Primary language for this node
            
        Returns:
            True if registration successful
        """
        # Convert device specs to ClientDevice objects
        client_devices = []
        for device_spec in devices:
            device = ClientDevice(
                id=device_spec.get('id', ''),
                name=device_spec.get('name', ''),
                type=device_spec.get('type', 'unknown'),
                capabilities=device_spec.get('capabilities', {}),
                location=room_name,
                metadata=device_spec.get('metadata', {})
            )
            client_devices.append(device)
        
        # Create ESP32 registration
        registration = ClientRegistration(
            client_id=client_id,
            room_name=room_name,
            language=language,
            client_type="esp32",
            available_devices=client_devices,
            capabilities={
                "voice_input": True,
                "audio_output": True,
                "local_processing": True,
                "wake_word_detection": True
            },
            source_address=source_address,
            metadata={
                "device_type": "esp32",
                "firmware_version": "unknown"
            }
        )
        
        return await self.register_client(registration)
    
    async def register_web_client(self, client_id: str, room_name: str,
                                 user_agent: Optional[str] = None,
                                 language: str = "ru") -> bool:
        """
        Register a web client.
        
        Args:
            client_id: Web client identifier
            room_name: Room name selected by user
            user_agent: Browser user agent string
            language: Preferred language
            
        Returns:
            True if registration successful
        """
        registration = ClientRegistration(
            client_id=client_id,
            room_name=room_name,
            language=language,
            client_type="web",
            available_devices=[],  # Web clients typically don't have devices
            capabilities={
                "voice_input": True,
                "audio_output": True,
                "text_input": True,
                "visual_output": True
            },
            user_agent=user_agent,
            metadata={
                "device_type": "web_browser",
                "interface": "web"
            }
        )
        
        return await self.register_client(registration)
    
    def get_client(self, client_id: str) -> Optional[ClientRegistration]:
        """
        Get client registration by ID.
        
        Args:
            client_id: Client identifier
            
        Returns:
            ClientRegistration or None if not found
        """
        return self.clients.get(client_id)
    
    def get_clients_by_room(self, room_name: str) -> List[ClientRegistration]:
        """
        Get all clients in a specific room.
        
        Args:
            room_name: Room name to search for
            
        Returns:
            List of client registrations in the room
        """
        room_name_lower = room_name.lower()
        return [client for client in self.clients.values() 
                if client.room_name.lower() == room_name_lower]
    
    def get_all_rooms(self) -> List[str]:
        """
        Get list of all registered room names.
        
        Returns:
            List of unique room names
        """
        return list(set(client.room_name for client in self.clients.values()))
    
    def get_devices_by_type(self, device_type: str) -> List[tuple[str, ClientDevice]]:
        """
        Get all devices of a specific type across all clients.
        
        Args:
            device_type: Device type to search for
            
        Returns:
            List of (client_id, device) tuples
        """
        devices = []
        for client_id, client in self.clients.items():
            for device in client.available_devices:
                if device.type == device_type:
                    devices.append((client_id, device))
        return devices
    
    async def update_client_last_seen(self, client_id: str) -> bool:
        """
        Update last seen timestamp for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            True if client found and updated
        """
        if client_id in self.clients:
            self.clients[client_id].update_last_seen()
            
            # Save to persistent storage
            if self.persistent_storage:
                self._save_registrations()
            
            return True
        return False
    
    async def unregister_client(self, client_id: str) -> bool:
        """
        Unregister a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            True if client was found and removed
        """
        if client_id in self.clients:
            del self.clients[client_id]
            logger.info(f"Unregistered client '{client_id}'")
            
            # Save to persistent storage
            if self.persistent_storage:
                self._save_registrations()
            
            return True
        return False
    
    async def cleanup_expired_clients(self) -> int:
        """
        Remove clients that haven't been seen recently.

        Deliberately NOT auto-wired into the periodic sweep (QUAL-58 decision): nothing
        refreshes ``last_seen`` during a long-lived WS connection, so auto-expiry would
        unregister a live-but-quiet satellite and drop its room/device metadata. Callable
        for admin/manual housekeeping; auto-expiry needs a liveness touch first.

        Returns:
            Number of clients removed
        """
        current_time = time.time()
        expired_clients = []
        
        for client_id, client in self.clients.items():
            if current_time - client.last_seen > self.registration_timeout:
                expired_clients.append(client_id)
        
        for client_id in expired_clients:
            await self.unregister_client(client_id)
        
        if expired_clients:
            logger.info(f"Cleaned up {len(expired_clients)} expired client registrations")
        
        return len(expired_clients)
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            Statistics about registered clients
        """
        stats = {
            "total_clients": len(self.clients),
            "total_rooms": len(self.get_all_rooms()),
            "total_devices": sum(len(client.available_devices) for client in self.clients.values()),
            "clients_by_type": {},
            "devices_by_type": {}
        }
        
        # Count by client type
        for client in self.clients.values():
            client_type = client.client_type
            stats["clients_by_type"][client_type] = stats["clients_by_type"].get(client_type, 0) + 1
        
        # Count by device type
        for client in self.clients.values():
            for device in client.available_devices:
                device_type = device.type
                stats["devices_by_type"][device_type] = stats["devices_by_type"].get(device_type, 0) + 1
        
        return stats
    
    # ------------------------------------------------------------------ #
    # Runtime action store (QUAL-28) — zombie-resistant, never persisted.  #
    # Reaper layers: (1) completion callback removes; (2) read-time        #
    # liveness filter; (3) periodic sweep reap_dead_actions(), driven by   #
    # the ContextManager cleanup loop (QUAL-58 — it previously had no      #
    # runtime caller); (4) TTL via ActionRecord.expected_end + a hard      #
    # per-identity cap.                                                    #
    # ------------------------------------------------------------------ #

    def add_action(self, record: ActionRecord) -> None:
        """Register a live action under its physical_id, keyed by action_name."""
        table = self._actions.setdefault(record.physical_id, {})
        displaced = table.get(record.action_name)
        if displaced is not None and displaced.is_live():
            # BUG-19: a name collision used to silently drop the live record from the store while
            # its task kept running untracked. Names are collision-proof now (uuid suffixes), so
            # this is a caller bug — scream. The displaced task keeps its own done-callback
            # (identity-safe removal means it can no longer evict this successor).
            logger.error(f"Action-name collision for '{record.physical_id}/{record.action_name}': "
                         f"a live action is being displaced from the store (caller bug)")
        table[record.action_name] = record
        # Layer 4: opportunistically reap dead entries, then enforce the hard cap.
        self._reap_identity(record.physical_id)
        table = self._actions.get(record.physical_id, {})
        if len(table) > self.max_actions_per_identity:
            oldest = min(table.values(), key=lambda r: r.started_at)
            table.pop(oldest.action_name, None)
            # BUG-19: cancel the evicted task — eviction used to drop the record while the task
            # kept running as an untracked zombie. Cancelling routes it through its own
            # done-callback (history records "cancelled").
            if oldest.task is not None and not oldest.task.done():
                oldest.deliberate_cancel = True  # eviction revokes the promise — reap durably too
                oldest.task.cancel()
            logger.warning(f"Action store cap ({self.max_actions_per_identity}) hit for "
                           f"'{record.physical_id}'; evicted + cancelled oldest action "
                           f"'{oldest.action_name}'")

    def get_action(self, physical_id: str, action_name: str) -> Optional[ActionRecord]:
        """Fetch a specific action, applying the read-time liveness filter (layer 2)."""
        rec = self._actions.get(physical_id, {}).get(action_name)
        if rec is not None and not rec.is_live():
            self.remove_action(physical_id, action_name, expected=rec)
            return None
        return rec

    def get_live_actions(self, physical_id: str) -> List[ActionRecord]:
        """All live actions for a physical_id (dead entries reaped first — layer 2)."""
        self._reap_identity(physical_id)
        return list(self._actions.get(physical_id, {}).values())

    def get_live_actions_by_domain(self, physical_id: str, domain: str) -> List[ActionRecord]:
        """Live actions in a domain — the secondary index the contextual resolver uses."""
        return [r for r in self.get_live_actions(physical_id) if r.domain == domain]

    def remove_action(self, physical_id: str, action_name: str,
                      expected: Optional[ActionRecord] = None) -> Optional[ActionRecord]:
        """Remove an action (layer 1 — called from the completion callback).

        ``expected`` (BUG-19): identity guard — when given, the entry is removed only if it IS
        that record. Without it, a displaced action's done-callback could evict a live successor
        registered under the same name.
        """
        table = self._actions.get(physical_id)
        if not table:
            return None
        if expected is not None and table.get(action_name) is not expected:
            return None
        rec = table.pop(action_name, None)
        if not table:
            self._actions.pop(physical_id, None)
        return rec

    def _reap_identity(self, physical_id: str) -> int:
        """Drop dead actions for one physical_id; returns count reaped."""
        table = self._actions.get(physical_id)
        if not table:
            return 0
        dead = [name for name, rec in table.items() if not rec.is_live()]
        for name in dead:
            table.pop(name, None)
        if not table:
            self._actions.pop(physical_id, None)
        return len(dead)

    def get_all_live_actions(self) -> List[Dict[str, Any]]:
        """Snapshot of every live action across identities (ARCH-28 D-9 — the observability
        surface: /monitoring/actions). Read-only; dead entries reaped per identity first."""
        snapshot: List[Dict[str, Any]] = []
        for physical_id in list(self._actions.keys()):
            for rec in self.get_live_actions(physical_id):
                snapshot.append({
                    "action_name": rec.action_name,
                    "domain": rec.domain,
                    "physical_id": rec.physical_id,
                    "room_id": rec.room_id,
                    "session_id": rec.session_id,
                    "source": rec.source,
                    "started_at": rec.started_at,
                    "deadline": rec.expected_end,
                    "durable": rec.durable,
                    "redeliver": rec.redeliver,
                    "handler": (rec.metadata or {}).get("handler"),
                })
        return snapshot

    def reap_dead_actions(self) -> int:
        """Periodic sweep across all identities (layer 3); returns count reaped."""
        total = 0
        for physical_id in list(self._actions.keys()):
            total += self._reap_identity(physical_id)
        if total:
            logger.debug(f"Action store reaper removed {total} dead action(s)")
        return total

    # --- completed-action history (physical-identity-scoped, runtime-only) --- #

    def record_completed_action(self, record: 'ActionRecord', success: bool, error: Optional[str] = None) -> None:
        """Record a completed/failed/cancelled action in the per-identity history (caps: 10 recent /
        20 failed). Called once from the F&F done-callback — the single completion chokepoint."""
        pid = record.physical_id
        info = {"action": record.action_name, "domain": record.domain, "started_at": record.started_at,
                "completed_at": time.time(), "success": success, "error": error,
                "status": "completed" if success else "failed"}
        recent = self._recent_actions.setdefault(pid, [])
        recent.append(info)
        if len(recent) > 10:
            self._recent_actions[pid] = recent[-10:]
        if not success:
            failed = self._failed_actions.setdefault(pid, [])
            failed.append(info)
            if len(failed) > 20:
                self._failed_actions[pid] = failed[-20:]
            ec = self._action_error_count.setdefault(pid, {})
            ec[record.domain] = ec.get(record.domain, 0) + 1

    def get_recent_actions(self, physical_id: str) -> List[Dict[str, Any]]:
        return list(self._recent_actions.get(physical_id, []))

    def prune_stale_history(self, max_age_seconds: float = 3600.0) -> int:
        """Drop per-identity completed-action history whose NEWEST entry is older than the TTL
        (QUAL-58 M5). The per-identity lists are capped (10 recent / 20 failed) but the identity
        KEYS were never deleted — with session-derived physical ids, every ephemeral session that
        ran a fire-and-forget action left a permanent keyset entry. History is short-term context
        ("what just happened here"), so an hour-stale identity has nothing left to say. Driven by
        the ContextManager cleanup loop alongside reap_dead_actions(). Returns identities pruned."""
        now = time.time()
        stale = []
        for pid in set(self._recent_actions) | set(self._failed_actions) | set(self._action_error_count):
            entries = self._recent_actions.get(pid, []) + self._failed_actions.get(pid, [])
            newest = max((e.get("completed_at", 0.0) for e in entries), default=0.0)
            if now - newest > max_age_seconds:
                stale.append(pid)
        for pid in stale:
            self._recent_actions.pop(pid, None)
            self._failed_actions.pop(pid, None)
            self._action_error_count.pop(pid, None)
        if stale:
            logger.debug(f"Pruned completed-action history for {len(stale)} stale identit(ies)")
        return len(stale)

    def get_failed_actions(self, physical_id: str) -> List[Dict[str, Any]]:
        return list(self._failed_actions.get(physical_id, []))

    def get_action_error_count(self, physical_id: str) -> Dict[str, int]:
        return dict(self._action_error_count.get(physical_id, {}))

    def _save_registrations(self):
        """Save registrations to persistent storage"""
        try:
            # Ensure directory exists
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert registrations to dict format
            data = {
                client_id: registration.to_dict() 
                for client_id, registration in self.clients.items()
            }
            
            # Save to JSON file
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved {len(self.clients)} client registrations to {self.storage_path}")
            
        except Exception as e:
            logger.error(f"Failed to save client registrations: {e}")
    
    def _load_registrations(self):
        """Load registrations from persistent storage (with legacy-path migration, ARCH-28)."""
        try:
            load_path = self.storage_path
            migrating = False
            if not load_path.exists():
                # Legacy home: cwd-relative cache/ (pre-ARCH-28) — read it once and re-home
                # the file under <assets_root>/state/ so it survives container replacement.
                legacy = Path('cache/client_registry.json')
                if legacy.exists() and legacy.resolve() != self.storage_path.resolve():
                    load_path = legacy
                    migrating = True
                else:
                    logger.info("No existing client registrations found")
                    return

            with open(load_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Convert dict data back to registration objects
            for client_id, registration_data in data.items():
                try:
                    registration = ClientRegistration.from_dict(registration_data)
                    self.clients[client_id] = registration
                except Exception as e:
                    logger.warning(f"Failed to load registration for client '{client_id}': {e}")

            logger.info(f"Loaded {len(self.clients)} client registrations from {load_path}")
            if migrating and self.clients:
                logger.info(f"Migrating client registrations {load_path} → {self.storage_path}")
                self._save_registrations()

        except Exception as e:
            logger.error(f"Failed to load client registrations: {e}")


def resolve_physical_id(client_id: Optional[str], room_name: Optional[str], session_id: str) -> str:
    """The single seam mapping a request/context to its stable action-scope id (QUAL-28).

    The action store + contextual-command resolution key off the *physical origin* (room/device),
    which is what lets a later "stop" find an action even after the conversation session expires.

    Today ``client_id``/``room_name`` are usually unpopulated, so this falls back to the
    session-derived id — already a stable per-origin scope for the current paths. **ARCH-6**
    (the WS/ESP32 `ClientRegistry` registration handshake) populates ``client_id``/``room_name``,
    at which point this transparently returns the physical identity — **this is the only function
    that changes to activate the room/device story** (no re-refactor elsewhere).
    """
    return client_id or room_name or session_id


# Global client registry instance
_client_registry: Optional[ClientRegistry] = None


def get_client_registry() -> ClientRegistry:
    """Get the global client registry instance"""
    global _client_registry
    if _client_registry is None:
        _client_registry = ClientRegistry()
    return _client_registry


def initialize_client_registry(config: Optional[Dict[str, Any]] = None) -> ClientRegistry:
    """Initialize the global client registry with configuration"""
    global _client_registry
    _client_registry = ClientRegistry(config)
    return _client_registry
