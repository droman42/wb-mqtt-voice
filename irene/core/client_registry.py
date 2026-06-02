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
    room_name: str
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
        """Create registration from dictionary"""
        # Convert device dicts back to ClientDevice objects
        devices_data = data.get('available_devices', [])
        devices = [ClientDevice(**device) if isinstance(device, dict) else device 
                  for device in devices_data]
        
        # Create registration with devices
        registration_data = data.copy()
        registration_data['available_devices'] = devices
        
        return cls(**registration_data)
    
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
    session_id: Optional[str] = None         # conversation that launched it (informational)
    room_id: Optional[str] = None
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
    
    def __init__(self, config: Dict[str, Any] = None):
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
        self.storage_path = Path(self.config.get('storage_path', 'cache/client_registry.json'))
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
                                 source_address: str = None,
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
                                 user_agent: str = None,
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
    # liveness filter; (3) periodic sweep reap_dead_actions(); (4) TTL via #
    # ActionRecord.expected_end + a hard per-identity cap.                  #
    # ------------------------------------------------------------------ #

    def add_action(self, record: ActionRecord) -> None:
        """Register a live action under its physical_id, keyed by action_name."""
        table = self._actions.setdefault(record.physical_id, {})
        table[record.action_name] = record
        # Layer 4: opportunistically reap dead entries, then enforce the hard cap.
        self._reap_identity(record.physical_id)
        table = self._actions.get(record.physical_id, {})
        if len(table) > self.max_actions_per_identity:
            oldest = min(table.values(), key=lambda r: r.started_at)
            table.pop(oldest.action_name, None)
            logger.warning(f"Action store cap ({self.max_actions_per_identity}) hit for "
                           f"'{record.physical_id}'; evicted oldest action '{oldest.action_name}'")

    def get_action(self, physical_id: str, action_name: str) -> Optional[ActionRecord]:
        """Fetch a specific action, applying the read-time liveness filter (layer 2)."""
        rec = self._actions.get(physical_id, {}).get(action_name)
        if rec is not None and not rec.is_live():
            self.remove_action(physical_id, action_name)
            return None
        return rec

    def get_live_actions(self, physical_id: str) -> List[ActionRecord]:
        """All live actions for a physical_id (dead entries reaped first — layer 2)."""
        self._reap_identity(physical_id)
        return list(self._actions.get(physical_id, {}).values())

    def get_live_actions_by_domain(self, physical_id: str, domain: str) -> List[ActionRecord]:
        """Live actions in a domain — the secondary index the contextual resolver uses."""
        return [r for r in self.get_live_actions(physical_id) if r.domain == domain]

    def remove_action(self, physical_id: str, action_name: str) -> Optional[ActionRecord]:
        """Remove an action (layer 1 — called from the completion callback)."""
        table = self._actions.get(physical_id)
        if not table:
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
        """Load registrations from persistent storage"""
        try:
            if not self.storage_path.exists():
                logger.info("No existing client registrations found")
                return
            
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert dict data back to registration objects
            for client_id, registration_data in data.items():
                try:
                    registration = ClientRegistration.from_dict(registration_data)
                    self.clients[client_id] = registration
                except Exception as e:
                    logger.warning(f"Failed to load registration for client '{client_id}': {e}")
            
            logger.info(f"Loaded {len(self.clients)} client registrations from {self.storage_path}")
            
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


def initialize_client_registry(config: Dict[str, Any] = None) -> ClientRegistry:
    """Initialize the global client registry with configuration"""
    global _client_registry
    _client_registry = ClientRegistry(config)
    return _client_registry
