"""Conversation / session context models.

Split out of ``intents/models.py`` (ARCH-1). These are **domain** types and live
in the ``intents`` (domain) package alongside ``Intent``/``IntentResult``, which
they reference via a normal sibling import. The dependency is one-directional —
``context_models -> models`` (``models`` does NOT import this module) — so there
is no cycle and no ``TYPE_CHECKING`` band-aid.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from rapidfuzz import fuzz, process

from ..core.session_manager import SessionManager  # ARCH-5: RequestContext session-id gen
from ..core.client_registry import get_client_registry, resolve_physical_id, ActionRecord  # QUAL-28: action store


class ConversationState(Enum):
    """Represents the current state of a conversation session"""
    IDLE = "idle"                    # No active conversation
    CONVERSING = "conversing"        # Active LLM conversation  
    CLARIFYING = "clarifying"        # Resolving ambiguous intent
    CONTEXTUAL = "contextual"        # Processing contextual command (already working)


@dataclass
class UnifiedConversationContext:
    """Unified conversation context replacing both ConversationContext and ConversationSession
    
    CRITICAL: Maintains room/client-scoped session boundaries for fire-and-forget action tracking
    and contextual command resolution (TODO16 compatibility).
    
    DESIGN: Single-user, multi-room system where sessions represent physical locations.
    """
    
    # Core identification (room-scoped sessions preserved)
    session_id: str                   # Room-based: "kitchen_session", "living_room_session"
    client_id: Optional[str] = None   # Room ID: "kitchen", "living_room"
    room_name: Optional[str] = None   # Human-readable: "Кухня", "Гостиная"
    
    # System-level context (from old ConversationContext)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    client_metadata: Dict[str, Any] = field(default_factory=dict)
    available_devices: List[Dict[str, Any]] = field(default_factory=list)
    # Resolved session language + the instance's supported set — both seeded from the ONE canonical
    # config source (QUAL-36) by ContextManager. Downstream reads these instead of importing config or
    # baking literals. `language` is an invariant: always a valid member of `supported_languages`.
    language: str = "ru"
    supported_languages: List[str] = field(default_factory=lambda: ["ru", "en"])

    # Fire-and-forget action tracking. QUAL-28: active_actions AND the completed-action history
    # (recent_actions/failed_actions/action_error_count) are no longer stored fields — they are
    # read-only views over the long-lived, physical-identity-scoped ClientRegistry store, so they all
    # survive conversation-session eviction (per Q3). See the properties below.
    
    # Handler-specific contexts (replaces ConversationSession approach)
    handler_contexts: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Conversation state management (Phase 2)
    conversation_state: ConversationState = ConversationState.IDLE
    state_context: Dict[str, Any] = field(default_factory=dict)  # State-specific context
    state_changed_at: float = field(default_factory=time.time)

    # QUAL-31 Grade-2 multi-turn slot-filling. When a handler asks the user to supply a missing
    # required parameter (QUAL-30 `_clarify`), the original command is remembered here so the NEXT
    # turn can be read as the answer and used to resume it. Kept on the session and decoupled from
    # `conversation_state` on purpose (that enum's CLARIFYING value carries the unrelated no-intent
    # fallback meaning, and CLARIFYING→CLARIFYING is an invalid transition that would break re-asks).
    # One-shot: consumed by exactly the next turn, or dropped when the session is evicted after the
    # idle window (so it "expires with the Q2 idle window" without a separate timer).
    pending_clarification: Optional[Dict[str, Any]] = None
    
    # Unified timestamps
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    
    # Legacy compatibility fields (from ConversationContext)
    user_id: Optional[str] = None
    current_intent_context: Optional[str] = None
    last_intent_timestamp: Optional[float] = None
    preferred_output_device: Optional[str] = None
    client_capabilities: Dict[str, bool] = field(default_factory=dict)
    timezone: Optional[str] = None
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    notification_preferences: Dict[str, Any] = field(default_factory=lambda: {
        "action_completion": {
            "enabled": True,
            "long_running_threshold": 30.0,  # seconds
            "delivery_methods": ["tts", "log"],  # tts, log, ui, push
            "priority_filter": "important"  # all, important, critical
        },
        "action_failure": {
            "enabled": True,
            # ARCH-28 (D-5): failures are announced by DEFAULT — the user asked for something
            # and it didn't happen; that is never below the notification threshold. (Was
            # critical-only, which silently swallowed ordinary F&F failures.)
            "critical_only": False,
            "delivery_methods": ["tts", "log"],
            "retry_notifications": False
        },
        "system_status": {
            "enabled": True,
            "delivery_methods": ["log"],
            "include_metrics": False
        }
    })
    # (QUAL-28) `memory_management` config blob removed — it was dead state for the deleted MemoryManager.
    timestamp: float = field(default_factory=time.time)
    request_source: str = "unknown"  # "microphone", "web", "api", etc.
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_updated: float = field(default_factory=time.time)
    # QUAL-28 stage 4: conversation_history is the SINGLE history list; max_history_turns is its window.
    max_history_turns: int = 10
    # Disambiguation context for follow-up resolution (set on demand by ContextManager).
    disambiguation_context: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        # Sync metadata with client_metadata
        if self.metadata and not self.client_metadata:
            self.client_metadata.update(self.metadata)
    
    # Combined methods from both old classes
    def get_room_name(self) -> Optional[str]:
        """Get human-readable room name from client context"""
        if self.room_name:
            return self.room_name
        if self.client_id:
            return self.client_metadata.get('room_name', self.client_id)
        return None
    
    def get_device_capabilities(self) -> List[Dict[str, Any]]:
        """Get list of devices available in this client context"""
        return self.client_metadata.get('available_devices', self.available_devices)
    
    def get_device_by_name(self, device_name: str) -> Optional[Dict[str, Any]]:
        """Find device by name using fuzzy matching"""
        devices = self.get_device_capabilities()
        
        # Exact match first
        for device in devices:
            if device.get('name', '').lower() == device_name.lower():
                return device
        
        # Fuzzy match fallback using rapidfuzz
        device_names = [device.get('name', '') for device in devices]
        best_match = process.extractOne(device_name, device_names, scorer=fuzz.ratio)
        
        if best_match and best_match[1] >= 70:  # 70% similarity threshold
            for device in devices:
                if device.get('name', '') == best_match[0]:
                    return device
        
        return None
    
    # Handler-specific context management
    def get_handler_context(self, handler_name: str) -> Dict[str, Any]:
        """Get handler-specific context (e.g., LLM conversation history)"""
        if handler_name not in self.handler_contexts:
            if handler_name == "conversation":
                # Initialize conversation handler with threading support (Phase 3)
                self.handler_contexts[handler_name] = {
                    "messages": [],
                    "conversation_type": "chat", 
                    "model_preference": "",
                    "created_at": time.time(),
                    "threads": {}  # Domain-specific conversation threads
                }
            else:
                # Standard handler context for non-conversation handlers
                self.handler_contexts[handler_name] = {
                    "messages": [],
                    "conversation_type": "chat", 
                    "model_preference": "",
                    "created_at": time.time()
                }
            
            # NEW: Restore conversation history for conversation handler
            if handler_name == "conversation" and self.conversation_history:
                self._restore_conversation_history_to_handler_context(handler_name)
        
        return self.handler_contexts[handler_name]
    
    def clear_handler_context(self, handler_name: str, keep_system: bool = True):
        """Clear handler-specific context (e.g., LLM history)"""
        context = self.get_handler_context(handler_name)
        if keep_system and context.get("messages") and context["messages"][0].get("role") == "system":
            system_msg = context["messages"][0]
            context["messages"] = [system_msg]
        else:
            context["messages"] = []

    def trim_handler_messages(self, handler_name: str, max_messages: int) -> None:
        """Window a handler's LLM message list to the last ``max_messages`` entries (BUG-18).

        The seed system prompt at index 0 (the ``clear_handler_context(keep_system=True)``
        convention) is pinned and does not count toward the window. Without this bound the
        list grew per turn for the life of the session — for stable room-scoped sessions,
        effectively forever.
        """
        if max_messages <= 0:
            return
        context = self.get_handler_context(handler_name)
        messages = context.get("messages") or []
        pinned = messages[:1] if messages and messages[0].get("role") == "system" else []
        tail = messages[len(pinned):]
        if len(tail) > max_messages:
            context["messages"] = pinned + tail[-max_messages:]

    def _restore_conversation_history_to_handler_context(self, handler_name: str):
        """Convert general conversation_history to LLM message format"""
        messages = []
        
        # Convert recent conversation history to LLM format
        recent_history = self.conversation_history[-self.max_history_turns:]
        
        for interaction in recent_history:
            if interaction.get("user_text"):
                messages.append({
                    "role": "user", 
                    "content": interaction["user_text"]
                })
            if interaction.get("response"):
                messages.append({
                    "role": "assistant", 
                    "content": interaction["response"]
                })
        
        self.handler_contexts[handler_name]["messages"] = messages
    
    # CRITICAL: Fire-and-forget action management (preserved from ConversationContext)
    # ---- Fire-and-forget actions: read-only views + store-backed mutators (QUAL-28) ---- #
    @property
    def _action_pid(self) -> str:
        """The physical scope id this context's actions live under (room/device → session)."""
        return resolve_physical_id(self.client_id, self.room_name, self.session_id)

    @property
    def active_actions(self) -> Dict[str, Dict[str, Any]]:
        """Read-only view of live actions for this scope: ``{action_name: info}`` (from the store)."""
        out: Dict[str, Dict[str, Any]] = {}
        for r in get_client_registry().get_live_actions(self._action_pid):
            out[r.action_name] = {**r.metadata, "action": r.action_name, "domain": r.domain,
                                  "started_at": r.started_at, "expected_end": r.expected_end,
                                  "status": r.status, "session_id": r.session_id, "room_id": r.room_id}
        return out

    @property
    def recent_actions(self) -> List[Dict[str, Any]]:
        """Read-only view of completed actions for this scope (from the store; survives eviction)."""
        return get_client_registry().get_recent_actions(self._action_pid)

    @property
    def failed_actions(self) -> List[Dict[str, Any]]:
        """Read-only view of failed actions for this scope (from the store; survives eviction)."""
        return get_client_registry().get_failed_actions(self._action_pid)

    @property
    def action_error_count(self) -> Dict[str, int]:
        """Read-only per-domain error counts for this scope (from the store)."""
        return get_client_registry().get_action_error_count(self._action_pid)

    def add_active_action(self, action_name: str, action_info: Dict[str, Any]):
        """Register a (task-less) action in the store — best-effort. The handler-base launch performs the
        primary registration with a real task ref; this path is for callers that don't have one."""
        get_client_registry().add_action(ActionRecord(
            action_name=action_name,
            domain=action_info.get("domain", action_name),
            physical_id=self._action_pid,
            task=None,
            expected_end=action_info.get("timeout_at"),
            status=action_info.get("status", "running"),
            session_id=self.session_id,
            room_id=self.client_id or self.room_name,
            metadata={k: v for k, v in action_info.items() if k not in ("domain", "status", "started_at")},
        ))
        self.last_updated = time.time()
    
    def complete_action(self, key: str, success: bool = True, error: Optional[str] = None):
        """Back-compat alias — remove the action (by action_name or domain) as completed."""
        self.remove_completed_action(key, success=success, error=error)

    def has_active_action(self, domain: str) -> bool:
        """Whether any live action exists in the given domain."""
        return bool(get_client_registry().get_live_actions_by_domain(self._action_pid, domain))

    def get_active_action_domains(self) -> List[str]:
        """Domains that currently have live actions."""
        return list({r.domain for r in get_client_registry().get_live_actions(self._action_pid)})
    
    def remove_completed_action(self, key: str, success: bool = True, error: Optional[str] = None) -> bool:
        """Remove an action from the ACTIVE store (by ``action_name`` or ``domain``). The completion
        HISTORY (recent/failed) is recorded by the F&F done-callback — the single completion chokepoint —
        not here, to avoid double-counting."""
        registry = get_client_registry()
        pid = self._action_pid
        rec = registry.get_action(pid, key)
        if rec is not None:
            registry.remove_action(pid, key)
            self.last_updated = time.time()
            return True
        removed = False
        for rec in registry.get_live_actions_by_domain(pid, key):
            registry.remove_action(pid, rec.action_name)
            removed = True
        if removed:
            self.last_updated = time.time()
        return removed
    
    # Additional fire-and-forget management methods
    def cancel_action(self, domain: str, reason: str = "User requested cancellation") -> bool:
        """Cancel all live actions in a domain by cancelling their tasks (the done-callback then reaps
        them from the store). Returns whether anything was cancelled."""
        registry = get_client_registry()
        pid = self._action_pid
        cancelled = False
        for rec in registry.get_live_actions_by_domain(pid, domain):
            if rec.task is not None and not rec.task.done():
                rec.deliberate_cancel = True  # user revoked the promise — the durable record dies too
                rec.task.cancel()
            else:
                registry.remove_action(pid, rec.action_name)
            cancelled = True
        if cancelled:
            self.last_updated = time.time()
        return cancelled

    def update_action_status(self, key: str, status: str, error: Optional[str] = None) -> bool:
        """Update the status of a live action (by action_name or domain) in the store."""
        registry = get_client_registry()
        pid = self._action_pid
        rec = registry.get_action(pid, key)
        recs = [rec] if rec is not None else registry.get_live_actions_by_domain(pid, key)
        for rec in recs:
            rec.status = status
            if error:
                rec.metadata["error"] = error
        if recs:
            self.last_updated = time.time()
        return bool(recs)

    def get_cancellable_actions(self) -> List[str]:
        """Domains with live (cancellable) actions."""
        return self.get_active_action_domains()
    
    # Legacy compatibility methods from ConversationContext
    def set_client_context(self, client_id: str, metadata: Dict[str, Any]):
        """Set client identification and metadata"""
        self.client_id = client_id
        self.client_metadata = metadata
        # Update available devices from metadata
        if 'available_devices' in metadata:
            self.available_devices = metadata['available_devices']
        # Update room name if provided
        if 'room_name' in metadata:
            self.room_name = metadata['room_name']
        self.last_updated = time.time()
    
    def record_turn(self, user_text: str, response: str, intent: Optional[str] = None):
        """Record one conversation turn — the SINGLE history writer (QUAL-28 stage 4).

        The workflow calls this exactly once per request. There is no parallel ``history`` list and
        no per-layer double-write; the window is the configured ``max_history_turns`` (P1-q — the
        field is now honoured instead of a hardcoded cap).
        """
        self.conversation_history.append({
            "timestamp": time.time(),
            "user_text": user_text,
            "response": response,
            "intent": intent,
            "client_id": self.client_id
        })
        if len(self.conversation_history) > self.max_history_turns:
            self.conversation_history = self.conversation_history[-self.max_history_turns:]
        self.last_updated = time.time()
        
        self.last_updated = time.time()
    
    def get_recent_intents(self, limit: int = 3) -> List[str]:
        """Get recent intent names for context"""
        recent = []
        for interaction in reversed(self.conversation_history[-limit:]):
            if interaction.get('intent'):
                recent.append(interaction['intent'])
        return recent
    
    def has_capability(self, capability: str) -> bool:
        """Check if client has specific capability"""
        return self.client_capabilities.get(capability, False)
    
    def get_device_types(self) -> Set[str]:
        """Get set of device types available in this context"""
        devices = self.get_device_capabilities()
        return {device.get('type', 'unknown') for device in devices}
    
    def get_recent_action_domains(self, limit: int = 3) -> List[str]:
        """Get recent action domains for disambiguation"""
        recent_domains = []
        for action in reversed(self.recent_actions[-limit:]):
            domain = action.get('domain')
            if domain and domain not in recent_domains:
                recent_domains.append(domain)
        return recent_domains
    
    def _classify_error(self, error: str) -> str:
        """Classify error type for better error handling"""
        if not error:
            return 'unknown'
        
        error_lower = error.lower()
        
        if 'timeout' in error_lower or 'timed out' in error_lower:
            return 'timeout'
        elif 'connection' in error_lower or 'network' in error_lower:
            return 'network'
        elif 'permission' in error_lower or 'access' in error_lower:
            return 'permission'
        elif 'not found' in error_lower or '404' in error_lower:
            return 'not_found'
        elif 'unavailable' in error_lower or 'service' in error_lower:
            return 'service_unavailable'
        elif 'cancelled' in error_lower or 'canceled' in error_lower:
            return 'cancelled'
        else:
            return 'runtime'
    
    def _is_critical_failure(self, domain: str, error: Optional[str]) -> bool:
        """Determine if a failure is critical and should be reported to users"""
        if not error:
            return False
        
        error_lower = error.lower()
        
        # Critical failures that should be reported
        critical_indicators = [
            'permission denied',
            'access denied',
            'authentication failed',
            'service unavailable',
            'critical error',
            'fatal error'
        ]
        
        # Check if this domain has had too many failures recently
        error_count = self.action_error_count.get(domain, 0)
        if error_count >= 3:  # 3 or more failures in this domain
            return True
        
        return any(indicator in error_lower for indicator in critical_indicators)
    
    # User notification system methods
    def should_notify_completion(self, domain: str, duration: float) -> bool:
        """Check if action completion should trigger user notification"""
        prefs = self.notification_preferences.get("action_completion", {})
        if not prefs.get("enabled", True):
            return False
        
        threshold = prefs.get("long_running_threshold", 30.0)
        return duration >= threshold
    
    def should_notify_failure(self, domain: str, error: Optional[str], is_critical: bool) -> bool:
        """Check if action failure should trigger user notification"""
        prefs = self.notification_preferences.get("action_failure", {})
        if not prefs.get("enabled", True):
            return False
        
        if prefs.get("critical_only", True):
            return is_critical
        
        return True
    
    def get_notification_methods(self, notification_type: str) -> List[str]:
        """Get delivery methods for a notification type"""
        prefs = self.notification_preferences.get(notification_type, {})
        return prefs.get("delivery_methods", ["log"])
    
    def update_notification_preferences(self, notification_type: str, preferences: Dict[str, Any]) -> None:
        """Update notification preferences for a specific type"""
        if notification_type not in self.notification_preferences:
            self.notification_preferences[notification_type] = {}
        
        self.notification_preferences[notification_type].update(preferences)
        self.last_updated = time.time()
    
    def get_notification_summary(self) -> Dict[str, Any]:
        """Get summary of notification settings and recent notifications"""
        return {
            "preferences": self.notification_preferences.copy(),
            "recent_notifications": getattr(self, '_recent_notifications', []),
            "notification_count": getattr(self, '_notification_count', 0)
        }
    
    def get_failed_actions(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent failed actions for error reporting"""
        return self.failed_actions[-limit:] if self.failed_actions else []
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of action errors for monitoring"""
        return {
            'total_failed_actions': len(self.failed_actions),
            'error_count_by_domain': self.action_error_count.copy(),
            'recent_critical_failures': [
                action for action in self.failed_actions[-10:] 
                if action.get('is_critical', False)
            ]
        }
    
    def has_critical_failures(self) -> bool:
        """Check if there are any recent critical failures"""
        return any(
            action.get('is_critical', False) 
            for action in self.failed_actions[-5:]  # Check last 5 failures
        )
    
    # Memory management methods (Phase 1.3 MemoryManager compatibility)
    def get_memory_usage_estimate(self) -> Dict[str, Any]:
        """Estimate memory usage of unified context data"""
        import sys
        
        try:
            # Calculate approximate memory usage for all context data
            conversation_size = sum(sys.getsizeof(str(item)) for item in self.conversation_history)
            handler_contexts_size = sum(sys.getsizeof(str(ctx)) for ctx in self.handler_contexts.values())
            active_actions_size = sum(sys.getsizeof(str(action)) for action in self.active_actions.values())
            recent_actions_size = sum(sys.getsizeof(str(action)) for action in self.recent_actions)
            failed_actions_size = sum(sys.getsizeof(str(action)) for action in self.failed_actions)
            metadata_size = sys.getsizeof(str(self.client_metadata))
            devices_size = sum(sys.getsizeof(str(device)) for device in self.available_devices)
            
            total_bytes = (
                conversation_size + handler_contexts_size + active_actions_size +
                recent_actions_size + failed_actions_size + metadata_size + devices_size
            )
            
            return {
                "total_bytes": total_bytes,
                "total_mb": total_bytes / (1024 * 1024),
                "breakdown": {
                    "conversation_history": {
                        "entries": len(self.conversation_history),
                        "bytes": conversation_size
                    },
                    "handler_contexts": {
                        "handlers": len(self.handler_contexts),
                        "bytes": handler_contexts_size
                    },
                    "active_actions": {
                        "entries": len(self.active_actions),
                        "bytes": active_actions_size
                    },
                    "recent_actions": {
                        "entries": len(self.recent_actions),
                        "bytes": recent_actions_size
                    },
                    "failed_actions": {
                        "entries": len(self.failed_actions),
                        "bytes": failed_actions_size
                    },
                    "client_metadata": {
                        "bytes": metadata_size
                    },
                    "available_devices": {
                        "entries": len(self.available_devices),
                        "bytes": devices_size
                    }
                }
            }
        except Exception as e:
            return {
                "total_bytes": 0,
                "total_mb": 0.0,
                "error": str(e),
                "breakdown": {}
            }
    
    # Conversation state management methods (Phase 2)
    def transition_state(self, new_state: ConversationState, context: Optional[Dict[str, Any]] = None) -> bool:
        """Transition to a new conversation state with optional context"""
        old_state = self.conversation_state
        
        # Validate state transition
        if not self._is_valid_transition(old_state, new_state):
            return False
        
        # Update state
        self.conversation_state = new_state
        self.state_changed_at = time.time()
        self.last_activity = time.time()
        
        # Update state context
        if context:
            self.state_context.update(context)
        else:
            # Clear context for new state if no context provided
            self.state_context.clear()
        
        return True
    
    def _is_valid_transition(self, from_state: ConversationState, to_state: ConversationState) -> bool:
        """Check if a state transition is valid"""
        # Define valid state transitions
        valid_transitions = {
            ConversationState.IDLE: [ConversationState.CONVERSING, ConversationState.CLARIFYING, ConversationState.CONTEXTUAL],
            ConversationState.CONVERSING: [ConversationState.IDLE, ConversationState.CLARIFYING, ConversationState.CONTEXTUAL],
            ConversationState.CLARIFYING: [ConversationState.CONVERSING, ConversationState.IDLE],
            ConversationState.CONTEXTUAL: [ConversationState.IDLE, ConversationState.CONVERSING]
        }
        
        return to_state in valid_transitions.get(from_state, [])
    
    def get_conversation_state(self) -> ConversationState:
        """Get current conversation state"""
        return self.conversation_state
    
    def get_state_context(self) -> Dict[str, Any]:
        """Get current state context"""
        return self.state_context.copy()
    
    def get_state_duration(self) -> float:
        """Get duration in current state (seconds)"""
        return time.time() - self.state_changed_at
    
    def is_state(self, state: ConversationState) -> bool:
        """Check if currently in specific state"""
        return self.conversation_state == state
    
    def update_state_context(self, key: str, value: Any) -> None:
        """Update a specific key in state context"""
        self.state_context[key] = value
        self.last_activity = time.time()

    # --- QUAL-31: multi-turn clarification (slot-filling) ---------------------------------------
    def set_pending_clarification(self, intent_name: str, missing_param: str, original_text: str,
                                  mode: str = "combine",
                                  ttl_seconds: Optional[float] = None) -> None:
        """Arm a one-shot clarification: remember that we asked the user to supply ``missing_param``
        for ``intent_name`` (whose triggering utterance was ``original_text``), so the next turn can be
        interpreted as the answer and used to resume the original command (QUAL-31 Grade 2).

        Modes (ARCH-31): ``combine`` (default — the QUAL-31/44 behavior: the answer is glued onto
        the original utterance and re-understood, with new-command arbitration) or ``verbatim``
        (the next utterance IS the answer, consumed raw with no NLU arbitration — a problem
        description like «свет не включается» must never execute as a command). ``ttl_seconds``
        sets ``expires_at``; the workflow drops an expired record silently. Combine mode keeps its
        historical no-expiry behavior unless a TTL is passed."""
        self.pending_clarification = {
            "intent_name": intent_name,
            "missing_param": missing_param,
            "original_text": original_text,
            "created_at": time.time(),
            "mode": mode,
            "expires_at": (time.time() + ttl_seconds) if ttl_seconds else None,
        }
        self.last_activity = time.time()

    def take_pending_clarification(self) -> Optional[Dict[str, Any]]:
        """Pop the pending clarification, if any, clearing it (one-shot). Returns the record so the
        caller can resume the original intent; ``None`` if nothing is pending. Clearing here is what
        makes a clarification consumed by exactly the next turn."""
        pending = self.pending_clarification
        self.pending_clarification = None
        return pending
    
    def clear_state_context(self) -> None:
        """Clear all state context data"""
        self.state_context.clear()
        self.last_activity = time.time()
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get summary of current conversation state"""
        return {
            "current_state": self.conversation_state.value,
            "state_duration": self.get_state_duration(),
            "state_context": self.state_context.copy(),
            "last_state_change": self.state_changed_at
        }
    
    # Conversation threading methods (Phase 3)
    def get_conversation_thread(self, domain: str) -> Dict[str, Any]:
        """Get or create a domain-specific conversation thread"""
        handler_context = self.get_handler_context("conversation")
        
        if domain not in handler_context["threads"]:
            handler_context["threads"][domain] = {
                "messages": [],
                "last_activity": time.time(),
                "active_context": {},
                "created_at": time.time()
            }
        
        return handler_context["threads"][domain]
    
    def add_to_thread(self, domain: str, role: str, content: str, context: Optional[Dict[str, Any]] = None,
                      max_messages: Optional[int] = None) -> None:
        """Add a message to a domain-specific conversation thread.

        ``max_messages`` (BUG-18): when given, the thread is windowed to the last
        ``max_messages`` entries after the append — thread message lists grew per
        turn without bound otherwise.
        """
        thread = self.get_conversation_thread(domain)

        message = {
            "role": role,
            "content": content,
            "timestamp": time.time()
        }

        if context:
            message["context"] = context

        thread["messages"].append(message)
        if max_messages and len(thread["messages"]) > max_messages:
            thread["messages"] = thread["messages"][-max_messages:]
        thread["last_activity"] = time.time()
        self.last_activity = time.time()
    
    def get_thread_messages(self, domain: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get messages from a domain-specific thread"""
        thread = self.get_conversation_thread(domain)
        messages = thread["messages"]
        
        if limit:
            return messages[-limit:]
        return messages
    
    def update_thread_context(self, domain: str, context: Dict[str, Any]) -> None:
        """Update the active context for a domain thread"""
        thread = self.get_conversation_thread(domain)
        thread["active_context"].update(context)
        thread["last_activity"] = time.time()
        self.last_activity = time.time()
    
    def get_thread_context(self, domain: str) -> Dict[str, Any]:
        """Get the active context for a domain thread"""
        thread = self.get_conversation_thread(domain)
        return thread["active_context"].copy()
    
    def clear_thread(self, domain: str, keep_context: bool = True) -> None:
        """Clear a domain-specific conversation thread"""
        thread = self.get_conversation_thread(domain)
        thread["messages"] = []
        thread["last_activity"] = time.time()
        
        if not keep_context:
            thread["active_context"] = {}
    
    def get_active_threads(self, since_seconds: int = 300) -> List[str]:
        """Get list of domain threads that have been active recently"""
        handler_context = self.get_handler_context("conversation")
        current_time = time.time()
        
        active_domains = []
        for domain, thread in handler_context["threads"].items():
            if current_time - thread["last_activity"] < since_seconds:
                active_domains.append(domain)
        
        return active_domains
    
    def get_thread_summary(self, domain: str) -> Dict[str, Any]:
        """Get summary information about a domain thread"""
        thread = self.get_conversation_thread(domain)
        
        return {
            "domain": domain,
            "message_count": len(thread["messages"]),
            "last_activity": thread["last_activity"],
            "created_at": thread.get("created_at", 0),
            "active_context_keys": list(thread["active_context"].keys()),
            "age_seconds": time.time() - thread.get("created_at", time.time())
        }
    
    def get_all_threads_summary(self) -> Dict[str, Any]:
        """Get summary of all conversation threads"""
        handler_context = self.get_handler_context("conversation")
        
        summaries = {}
        for domain in handler_context["threads"]:
            summaries[domain] = self.get_thread_summary(domain)
        
        return {
            "total_threads": len(handler_context["threads"]),
            "active_threads": len(self.get_active_threads()),
            "threads": summaries
        }

class InputFormat(Enum):
    """ARCH-15 PR-0..1 (D-1): the *format* axis — what the input is, which prescribes the
    workflow ENTRY stage (orthogonal to the *input* axis = the capture mechanism, §io_architecture §2).

    Three values, each naming its entry point into the pipeline
    (voice_trigger → ASR → text_processing → NLU → …):
      - VOICE: enter at voice-trigger (always-listening audio that must be woken: local mic)
      - AUDIO: enter at ASR (already-triggered audio: WS push-to-talk, ESP32 satellite)
      - TEXT:  enter at NLU, after ASR (console, web textbox, WS text frame)

    `file`/`binary_audio` are *transport* (an input-adapter concern), not formats.

    This is the single source of truth for the pipeline-entry decision; the legacy
    ``(skip_wake_word, skip_asr)`` flags on RequestContext are a derived projection of it
    (bijection over the meaningful combinations — the 4th combo "wake-word on + ASR off" is
    nonsensical and never occurs).
    """
    VOICE = "voice"
    AUDIO = "audio"
    TEXT = "text"

    def to_flags(self) -> "tuple[bool, bool]":
        """Project to the legacy ``(skip_wake_word, skip_asr)`` pair."""
        return {
            InputFormat.VOICE: (False, False),
            InputFormat.AUDIO: (True, False),
            InputFormat.TEXT: (True, True),
        }[self]

    @classmethod
    def from_flags(cls, skip_wake_word: bool, skip_asr: bool) -> "InputFormat":
        """Recover the format from the legacy flags (back-compat for callers still passing them).

        ``skip_asr`` implies TEXT (text always skips both stages); otherwise ``skip_wake_word``
        distinguishes already-triggered AUDIO from full VOICE.
        """
        if skip_asr:
            return cls.TEXT
        return cls.AUDIO if skip_wake_word else cls.VOICE


# ARCH-5: RequestContext moved here from workflows/base.py so the domain (intents) no
# longer imports up into workflows (it's request-context data — a domain type).
class RequestContext:
    """Context for a single request through the workflow with client identification."""
    
    def __init__(self,
                 source: str = "unknown",
                 session_id: Optional[str] = None, 
                 wants_audio: bool = False,
                 skip_wake_word: bool = False,
                 skip_asr: bool = False,
                 input_format: Optional["InputFormat"] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 client_id: Optional[str] = None,
                 room_name: Optional[str] = None,
                 device_context: Optional[Dict[str, Any]] = None,
                 language: Optional[str] = None):
        """
        Initialize request context with client identification support.
        
        Args:
            source: Source of the request (e.g., "microphone", "web", "cli", "esp32")
            session_id: Session identifier for context management (auto-generated if None)
            wants_audio: Whether the response should include audio output
            skip_wake_word: DERIVED from input_format (legacy flag; pass input_format instead)
            skip_asr: DERIVED from input_format (legacy flag; pass input_format instead)
            input_format: The format/entry-stage selector (VOICE/AUDIO/TEXT). When None, inferred
                from the legacy skip_* flags for back-compat. This is the single source of truth.
            metadata: Additional request metadata
            client_id: Client/node identifier (e.g., "kitchen_node", "living_room_esp32")
            room_name: Human-readable room name (e.g., "Кухня", "Kitchen")
            device_context: Available devices and capabilities in this client context
            language: Language EXPLICITLY carried by this request, or None when unspecified (QUAL-36).
                None means "use the session's resolved language" — the seeded context.language is NOT
                overridden. An adapter only passes a value when it actually knows the request language.
        """
        self.source = source
        # QUAL-28 (P0-6): the literal "default" must NOT bypass session derivation — it would
        # collapse every request into one shared context (cross-request/room/user leak). Treat
        # "default"/empty as "derive a real id".
        if not session_id or session_id == "default":
            session_id = SessionManager.generate_session_id(source)
        self.session_id = session_id
        self.wants_audio = wants_audio
        # ARCH-15 PR-1 (D-1): `input_format` is the first-class pipeline-entry selector and the
        # single source of truth; the legacy `(skip_wake_word, skip_asr)` flags are derived from
        # it. Back-compat: callers that still pass the flags get the format inferred from them.
        if input_format is None:
            input_format = InputFormat.from_flags(skip_wake_word, skip_asr)
        self.input_format = input_format
        self.skip_wake_word, self.skip_asr = input_format.to_flags()
        self.metadata = metadata or {}
        
        # Client identification and context
        self.client_id = client_id
        self.room_name = room_name
        self.device_context = device_context or {}
        self.language = language
        
        # Merge client context into metadata for backward compatibility
        if client_id:
            self.metadata["client_id"] = client_id
        if room_name:
            self.metadata["room_name"] = room_name
        if device_context:
            self.metadata["device_context"] = device_context
        if language:
            self.metadata["language"] = language
