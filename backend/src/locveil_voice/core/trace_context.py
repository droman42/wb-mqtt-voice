"""
Trace Context System for Pipeline Execution Tracing

This module provides the TraceContext class for collecting detailed pipeline
execution traces with conditional collection to ensure zero overhead when
tracing is disabled.

Features:
- Binary audio data handling with base64 conversion
- Sensitive data sanitization
- Context snapshot recording
- Performance timing collection
"""

import base64
import dataclasses
import hashlib
import json
import logging
import re
import time
import traceback
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Iterator, List, Optional

from ..intents.context_models import UnifiedConversationContext

logger = logging.getLogger(__name__)

# ARCH-19 slice 1 — ambient access to the live trace (D-3).
# A process-global contextvar set at the request boundary (`trace_scope`) so the
# TraceLogger and handler `trace_event()` can find the active trace without threading
# it through every signature. Hexagon-clean: `core` is already imported by the domain
# (handlers reach `core.metrics`/`core.client_registry` today), so this adds no new edge.
current_trace: ContextVar[Optional["TraceContext"]] = ContextVar("current_trace", default=None)


def get_current_trace() -> Optional["TraceContext"]:
    """Return the trace bound to the current context, or None."""
    return current_trace.get()


@contextmanager
def trace_scope(trace: Optional["TraceContext"]) -> Iterator[Optional["TraceContext"]]:
    """Bind `trace` as the ambient `current_trace` for the duration of the block.

    No-op-safe: a None trace simply binds None (so callers can wrap unconditionally).
    Always resets the contextvar on exit, even on exception.
    """
    token = current_trace.set(trace)
    try:
        yield trace
    finally:
        current_trace.reset(token)


def trace_event(label: str, data: Optional[Dict[str, Any]] = None, *, handler: str = "") -> None:
    """Record a handler sub-step (D-5) on the active trace — a no-op when none is set.

    Handlers call this unconditionally; it finds `current_trace` and appends a
    `handler_events` record. Cheap and side-effect-free when tracing is off.
    """
    trace = current_trace.get()
    if trace is None or not trace.enabled:
        return
    trace.add_handler_event(handler=handler, label=label, data=data or {})


# ARCH-19 slice 5 (D-12) — the `--step` seam. A replay's `--step` sets a global pause hook; every
# minted trace picks it up (see make_trace), and `trace_step()` awaits it at each pipeline stage
# boundary. No-op in normal operation (no hook set). The hook is `async (stage, data) -> None`.
StepHook = Callable[[str, Dict[str, Any]], Awaitable[None]]
_step_hook: Optional["StepHook"] = None


def set_step_hook(hook: Optional["StepHook"]) -> None:
    """Install (or clear) the global step hook used by `replay_trace --step`."""
    global _step_hook
    _step_hook = hook


async def trace_step(stage: str, data: Optional[Dict[str, Any]] = None) -> None:
    """Pause point at a pipeline stage boundary — awaits the active trace's step hook if set.

    No-op when no trace is active or no `--step` hook is installed, so the pipeline pays nothing.
    """
    trace = current_trace.get()
    if trace is None or not trace.enabled:
        return
    hook = getattr(trace, "step_hook", None)
    if hook is None:
        return
    trace.current_stage = stage
    await hook(stage, data or {})


class TraceLogger(logging.Handler):
    """A global logging handler that appends records to the ACTIVE trace (D-4, ARCH-19 slice 2).

    Installed once on the root logger at startup; inert unless `current_trace` is set + enabled,
    so it costs nothing on normal traffic. Captures records at/above its level **plus full
    exception stack traces**, each tagged with the trace's current stage + `t_ms`, and is bounded
    by `max_records` so a chatty request can't blow the file up. Never raises out of `emit`.
    """

    def __init__(self, level: int = logging.INFO, max_records: int = 500):
        super().__init__(level=level)
        self.max_records = max_records

    def emit(self, record: logging.LogRecord) -> None:
        trace = current_trace.get()
        if trace is None or not trace.enabled:
            return
        if len(trace.logs) >= self.max_records:
            return
        try:
            exc_text = None
            if record.exc_info:
                exc_text = "".join(traceback.format_exception(*record.exc_info))
            trace.add_log(
                level=record.levelname,
                logger_name=record.name,
                stage=getattr(trace, "current_stage", None),
                message=record.getMessage(),
                exc_text=exc_text,
            )
        except Exception:  # logging must never crash the app
            self.handleError(record)


# Redact trace values whose key NAMES a secret. CR-A9: match on word TOKENS, not raw substrings — the
# old substring test nuked legitimate diagnostic fields (`session_id` ⊃ "session", `keyword` /
# `matched_keys` ⊃ "key", `author` ⊃ "auth"). `session` is intentionally absent: a session *id* is not a
# secret; an actual session secret would be `session_token` / `session_key`, caught via `token` / `key`.
_SENSITIVE_KEY_TOKENS = {
    'password', 'passwd', 'pwd', 'secret', 'token', 'key', 'auth', 'authorization',
    'credential', 'credentials', 'bearer', 'private', 'cookie', 'jwt', 'oauth',
    'cert', 'certificate',
}
_KEY_TOKEN_RE = re.compile(r'[a-z0-9]+')


def _key_tokens(key: Any) -> set:
    """Word tokens of a dict key, splitting on separators AND camelCase, so `sessionId` / `session_id`
    both → {session, id} and `keyword` → {keyword} (not {key, word}). Used to redact only keys whose
    token actually names a secret."""
    spaced = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', str(key))
    return set(_KEY_TOKEN_RE.findall(spaced.lower()))


class TraceContext:
    """
    Context object for collecting detailed pipeline execution traces
    
    This class provides conditional trace collection with zero overhead
    when tracing is disabled, and comprehensive data collection when enabled.
    
    Features:
    - Stage-by-stage execution recording
    - Binary audio data conversion to base64
    - Conversation context snapshots
    - Performance timing collection
    - Sensitive data sanitization
    """
    
    def __init__(self, enabled: bool = False, request_id: Optional[str] = None, 
                 max_stages: int = 100, max_data_size_mb: int = 10):
        """
        Initialize trace context with production safety limits
        
        Args:
            enabled: Whether trace collection is enabled
            request_id: Unique identifier for this trace request
            max_stages: Maximum number of stages to record (prevents memory issues)
            max_data_size_mb: Maximum total data size in MB (prevents memory exhaustion)
        """
        self.enabled = enabled
        self.request_id = request_id or str(uuid.uuid4())
        self.stages: List[Dict[str, Any]] = []
        self.start_time = time.time()
        self.context_snapshots: Dict[str, Any] = {"before": None, "after": None}

        # Phase 8: Production safety limits
        self.max_stages = max_stages
        self.max_data_size_bytes = max_data_size_mb * 1024 * 1024
        self._current_data_size = 0
        self._stages_dropped = 0
        self._data_size_exceeded = False

        # ARCH-19 slice 1 — the un-sanitised `replay` envelope + the sidecar lists.
        # `stages`/`context_snapshots` above stay the SANITISED human view (export_trace);
        # everything below is FAITHFUL (un-redacted, un-truncated) so a saved trace is
        # re-runnable + listenable. Populated by record_*; serialised by build_envelope/to_file.
        # Call-sites for some of these land in later slices (config→2, vad→3, logs→2, seed→5);
        # the fields + recorders exist now so the envelope schema is complete from slice 1.
        self.capture_level: str = "utterance"          # utterance | segmenter | raw (D-2)
        self.current_stage: Optional[str] = None        # set at stage boundaries; tags TraceLogger records + drives --step
        self.step_hook: Optional["StepHook"] = None     # ARCH-19 D-12: set on replay --step, awaited by trace_step()
        self._input: Optional[Dict[str, Any]] = None   # faithful input: kind + format + audio_base64/text
        self._request: Optional[Dict[str, Any]] = None  # provider/language/skip_*/session/room/wants_audio
        self._canonical: Optional[Dict[str, Any]] = None  # canonical audio contract (rate/format/channels)
        self._seed_context: Optional[Dict[str, Any]] = None  # the "before" context, faithful (replay seeds from it)
        self._config_subset: Optional[Dict[str, Any]] = None  # settings that shaped this run (D-10)
        self._config_digest: Optional[str] = None      # quick equality check (sha256 of the subset)
        self._provider_models: Optional[Dict[str, Any]] = None  # model ids for the cross-system mismatch report
        self.recorded_output: Optional[Dict[str, Any]] = None  # the oracle a replay diffs against (D-6)
        self.vad_frames: List[Dict[str, Any]] = []     # segmenter level only (slice 3)
        self.logs: List[Dict[str, Any]] = []           # TraceLogger records (slice 2)
        self.handler_events: List[Dict[str, Any]] = []  # trace_event() records (D-5)
    
    def record_stage(self, stage_name: str, input_data: Any, output_data: Any, 
                    metadata: Dict[str, Any], processing_time_ms: float) -> None:
        """
        Record detailed stage execution information with production safety checks
        
        Args:
            stage_name: Name of the pipeline stage
            input_data: Input data for the stage
            output_data: Output data from the stage
            metadata: Additional metadata about stage execution
            processing_time_ms: Processing time in milliseconds
        """
        # Phase 8: Fast path - zero overhead when disabled
        if not self.enabled:
            return
        
        # Phase 8: Production safety - check stage limits
        if len(self.stages) >= self.max_stages:
            self._stages_dropped += 1
            if self._stages_dropped == 1:  # Only log once
                logger.warning(f"Trace stage limit ({self.max_stages}) exceeded, dropping subsequent stages")
            return
        
        # Phase 8: Production safety - check data size limits
        if self._data_size_exceeded:
            return
            
        # Sanitize data before size check (only when enabled)
        sanitized_input = self._sanitize_for_trace(input_data)
        sanitized_output = self._sanitize_for_trace(output_data)
        
        # Estimate stage data size
        stage_data = {
            "stage": stage_name,
            "input": sanitized_input,
            "output": sanitized_output,
            "metadata": metadata,
            "processing_time_ms": processing_time_ms,
            "timestamp": time.time()
        }
        
        # Phase 8: Production safety - rough data size estimation
        stage_size = self._estimate_data_size(stage_data)
        if self._current_data_size + stage_size > self.max_data_size_bytes:
            self._data_size_exceeded = True
            logger.warning(f"Trace data size limit ({self.max_data_size_bytes / 1024 / 1024:.1f}MB) exceeded, stopping trace collection")
            return
        
        self._current_data_size += stage_size
        self.stages.append(stage_data)
    
    def record_context_snapshot(self, when: str, context: UnifiedConversationContext) -> None:
        """
        Record conversation context state snapshots with production error handling
        
        Args:
            when: When the snapshot was taken ("before" or "after")
            context: UnifiedConversationContext to snapshot
        """
        # Phase 8: Ultra-fast path - immediate return when disabled
        if not self.enabled:
            return
        
        try:
            # Phase 8: Production reliability - safe context snapshot
            snapshot = {}
            
            # Safely extract active actions
            try:
                snapshot["active_actions"] = context.active_actions.copy() if context.active_actions else {}
            except Exception as e:
                snapshot["active_actions"] = {"error": f"Failed to copy active_actions: {str(e)}"}
            
            # Safely extract conversation history info
            try:
                history_length = len(context.conversation_history) if hasattr(context, 'conversation_history') and context.conversation_history else 0
                snapshot["conversation_history_length"] = history_length
                snapshot["recent_intents"] = context.conversation_history[-3:] if history_length > 0 else []
            except Exception as e:
                snapshot["conversation_history_length"] = 0
                snapshot["recent_intents"] = []
                snapshot["history_error"] = str(e)
            
            # Safely extract session information
            try:
                snapshot["session_id"] = getattr(context, 'session_id', 'unknown')
                snapshot["user_id"] = getattr(context, 'user_id', None)
            except Exception as e:
                snapshot["session_id"] = "unknown"
                snapshot["user_id"] = None
                snapshot["session_error"] = str(e)
            
            # NEW: Room context from session unification
            try:
                snapshot["client_id"] = getattr(context, 'client_id', None)
                snapshot["room_name"] = getattr(context, 'room_name', None)
            except Exception as e:
                snapshot["client_id"] = None
                snapshot["room_name"] = None
                snapshot["room_context_error"] = str(e)
            
            # NEW: Handler contexts (replaces ConversationSession)
            try:
                handler_contexts = getattr(context, 'handler_contexts', {})
                snapshot["handler_contexts"] = {
                    handler: {
                        "message_count": len(ctx.get("messages", [])),
                        "conversation_type": ctx.get("conversation_type", "unknown"),
                        "created_at": ctx.get("created_at", 0)
                    }
                    for handler, ctx in handler_contexts.items()
                } if handler_contexts else {}
            except Exception as e:
                snapshot["handler_contexts"] = {"error": f"Failed to extract handler contexts: {str(e)}"}
            
            # NEW: Enhanced fire-and-forget tracking
            try:
                snapshot["recent_actions_count"] = len(getattr(context, 'recent_actions', []))
                snapshot["failed_actions_count"] = len(getattr(context, 'failed_actions', []))
                snapshot["action_error_count"] = getattr(context, 'action_error_count', {}).copy()
            except Exception as e:
                snapshot["recent_actions_count"] = 0
                snapshot["failed_actions_count"] = 0
                snapshot["action_error_count"] = {}
                snapshot["action_tracking_error"] = str(e)
            
            # NEW: Room-scoped device context
            try:
                available_devices = getattr(context, 'available_devices', [])
                snapshot["available_devices_count"] = len(available_devices)
                snapshot["device_types"] = list(set(
                    device.get("type", "unknown") for device in available_devices
                )) if available_devices else []
                snapshot["language"] = getattr(context, 'language', 'unknown')
            except Exception as e:
                snapshot["available_devices_count"] = 0
                snapshot["device_types"] = []
                snapshot["language"] = "unknown"
                snapshot["device_context_error"] = str(e)
            
            # NEW: Memory usage from unification
            try:
                if hasattr(context, 'get_memory_usage_estimate'):
                    memory_usage = context.get_memory_usage_estimate()
                    snapshot["memory_usage"] = {
                        "total_mb": memory_usage.get("total_mb", 0.0),
                        "total_bytes": memory_usage.get("total_bytes", 0),
                        "breakdown_summary": {
                            key: data.get("bytes", 0) if isinstance(data, dict) else 0
                            for key, data in memory_usage.get("breakdown", {}).items()
                        }
                    }
                else:
                    snapshot["memory_usage"] = {"total_mb": 0.0, "total_bytes": 0, "breakdown_summary": {}}
            except Exception as e:
                snapshot["memory_usage"] = {
                    "total_mb": 0.0, 
                    "total_bytes": 0, 
                    "error": f"Memory estimation failed: {str(e)}"
                }
            
            # NEW: Timestamps for change analysis
            try:
                snapshot["created_at"] = getattr(context, 'created_at', 0)
                snapshot["last_activity"] = getattr(context, 'last_activity', 0)
                snapshot["snapshot_timestamp"] = time.time()
            except Exception as e:
                snapshot["created_at"] = 0
                snapshot["last_activity"] = 0
                snapshot["snapshot_timestamp"] = time.time()
                snapshot["timestamp_error"] = str(e)
            
            self.context_snapshots[when] = snapshot
            
        except Exception as e:
            # Phase 8: Production reliability - never fail trace recording
            logger.warning(f"Failed to record context snapshot for '{when}': {e}")
            self.context_snapshots[when] = {
                "error": f"Snapshot recording failed: {str(e)}",
                "timestamp": time.time()
            }
    
    def _sanitize_for_trace(self, data: Any) -> Any:
        """
        Sanitize sensitive data and handle binary audio data in trace output with production error handling
        
        This method handles:
        - Sensitive data removal (passwords, tokens, API keys)
        - Binary audio data conversion to base64
        - AudioData objects with metadata preservation
        - File path handling for audio files
        - Large string truncation
        - Production-safe error handling
        
        Args:
            data: Data to sanitize for trace output
            
        Returns:
            Sanitized data safe for trace storage
        """
        try:
            return self._do_sanitize(data)
        except Exception as e:
            # Phase 8: Production reliability - never fail sanitization
            logger.warning(f"Data sanitization failed: {e}")
            return {
                "type": "sanitization_error",
                "error": str(e),
                "data_type": type(data).__name__,
                "fallback_repr": str(data)[:100] + "..." if len(str(data)) > 100 else str(data)
            }
    
    def _do_sanitize(self, data: Any) -> Any:
        """
        Internal sanitization implementation (separated for error handling)
        """
        if isinstance(data, dict):
            # Phase 8: redact values whose key names a secret, recurse into the rest. CR-A9: match on
            # key word-TOKENS (see _key_tokens / _SENSITIVE_KEY_TOKENS), not raw substrings — the old
            # substring test redacted legitimate fields (session_id / keyword / matched_keys / author).
            sanitized = {}
            for k, v in data.items():
                if _key_tokens(k) & _SENSITIVE_KEY_TOKENS:
                    sanitized[k] = "[REDACTED]"
                else:
                    sanitized[k] = self._do_sanitize(v)
            return sanitized
            
        elif isinstance(data, list):
            # Recursively sanitize list items
            return [self._do_sanitize(item) for item in data]
            
        elif isinstance(data, str):
            # Phase 8: Enhanced truncation with size information
            max_length = 2000  # Increased for better debugging but still safe
            if len(data) > max_length:
                return {
                    "type": "truncated_string",
                    "original_length": len(data),
                    "truncated_content": data[:max_length],
                    "note": f"String truncated from {len(data)} to {max_length} characters"
                }
            return data
            
        elif isinstance(data, bytes):
            # Phase 8: Enhanced binary handling with size limits
            max_binary_size = 1024 * 1024  # 1MB limit for binary data in traces
            if len(data) > max_binary_size:
                return {
                    "type": "large_binary_data",
                    "size_bytes": len(data),
                    "note": f"Binary data too large ({len(data)} bytes) for trace inclusion",
                    "sample_data": base64.b64encode(data[:1024]).decode('utf-8') + "...[truncated]"
                }
            return {
                "type": "binary_audio_data",
                "size_bytes": len(data),
                "base64_data": base64.b64encode(data).decode('utf-8')
            }
            
        elif hasattr(data, 'data') and isinstance(data.data, bytes):
            # Phase 8: Enhanced AudioData handling with size limits
            max_audio_size = 1024 * 1024  # 1MB limit for audio data in traces
            audio_size = len(data.data)
            
            result = {
                "type": "audio_data_object",
                "size_bytes": audio_size,
                "sample_rate": getattr(data, 'sample_rate', None),
                "channels": getattr(data, 'channels', None),
                "format": getattr(data, 'format', None),
                "duration_ms": getattr(data, 'duration_ms', None)
            }
            
            if audio_size > max_audio_size:
                result.update({
                    "note": f"Audio data too large ({audio_size} bytes) for trace inclusion",
                    "sample_data": base64.b64encode(data.data[:1024]).decode('utf-8') + "...[truncated]"
                })
            else:
                result["base64_data"] = base64.b64encode(data.data).decode('utf-8')
            
            return result
            
        elif isinstance(data, Path):
            # Phase 8: Enhanced file path handling with size limits
            try:
                if data.exists() and data.suffix.lower() in ['.wav', '.mp3', '.ogg', '.flac', '.aac', '.m4a']:
                    file_size = data.stat().st_size
                    max_file_size = 1024 * 1024  # 1MB limit for files in traces
                    
                    result = {
                        "type": "audio_file_path",
                        "file_path": str(data),
                        "size_bytes": file_size,
                        "file_extension": data.suffix.lower()
                    }
                    
                    if file_size > max_file_size:
                        result.update({
                            "note": f"Audio file too large ({file_size} bytes) for trace inclusion",
                            "sample_data": "[File content not included due to size limit]"
                        })
                    else:
                        with open(data, 'rb') as f:
                            file_content = f.read()
                        result["base64_data"] = base64.b64encode(file_content).decode('utf-8')
                    
                    return result
                else:
                    return {"type": "file_path", "path": str(data), "exists": data.exists()}
            except Exception as e:
                return {"type": "file_path_error", "path": str(data), "error": str(e)}
                
        elif hasattr(data, '__dict__'):
            # Handle objects with attributes by converting to dict
            try:
                return self._do_sanitize(data.__dict__)
            except Exception:
                return {"type": "object", "class": data.__class__.__name__, "repr": str(data)[:500]}
                
        return data
    
    def _estimate_data_size(self, data: Any) -> int:
        """
        Estimate the memory size of data structure for production safety
        
        Args:
            data: Data structure to estimate size for
            
        Returns:
            Estimated size in bytes
        """
        try:
            # Simple estimation based on string representation
            # This is approximate but sufficient for production safety
            import sys
            if hasattr(sys, 'getsizeof'):
                return sys.getsizeof(str(data))
            else:
                # Fallback: rough estimation based on string length
                return len(str(data)) * 2
        except Exception:
            # Safe fallback if size estimation fails
            return 1024  # Assume 1KB for unknown objects
    
    def get_trace_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the trace execution
        
        Returns:
            Dictionary with trace summary information
        """
        if not self.enabled or not self.stages:
            return {"enabled": self.enabled, "stages": 0}
            
        total_time = sum(stage.get("processing_time_ms", 0) for stage in self.stages)
        stage_breakdown = {stage["stage"]: stage.get("processing_time_ms", 0) for stage in self.stages}
        
        return {
            "request_id": self.request_id,
            "total_stages": len(self.stages),
            "total_processing_time_ms": total_time,
            "stage_breakdown": stage_breakdown,
            "context_snapshots_recorded": len([k for k, v in self.context_snapshots.items() if v is not None]),
            "execution_start_time": self.start_time,
            # Phase 8: Production safety information
            "production_safety": {
                "stages_dropped": self._stages_dropped,
                "data_size_exceeded": self._data_size_exceeded,
                "current_data_size_mb": round(self._current_data_size / 1024 / 1024, 2),
                "max_data_size_mb": round(self.max_data_size_bytes / 1024 / 1024, 2),
                "max_stages": self.max_stages
            }
        }
    
    def export_trace(self) -> Dict[str, Any]:
        """
        Export complete trace data for API responses
        
        Returns:
            Complete trace data structure for external consumption
        """
        if not self.enabled:
            return {"enabled": False, "message": "Tracing was disabled for this request"}
            
        return {
            "request_id": self.request_id,
            "pipeline_stages": self.stages,
            "context_evolution": {
                "before": self.context_snapshots.get("before"),
                "after": self.context_snapshots.get("after"),
                "changes": self._calculate_context_changes()
            },
            "performance_metrics": {
                "total_processing_time_ms": sum(
                    stage.get("processing_time_ms", 0) for stage in self.stages
                ),
                "stage_breakdown": {
                    stage["stage"]: stage.get("processing_time_ms", 0) 
                    for stage in self.stages
                },
                "total_stages": len(self.stages),
                "execution_start_time": self.start_time,
                "trace_overhead_estimate_ms": len(self.stages) * 0.1  # Estimated overhead per stage
            }
        }
    
    # ------------------------------------------------------------------
    # ARCH-19 slice 1 — faithful `replay` envelope recorders + save.
    # These are FAITHFUL (no sanitiser): they store the full audio and the
    # un-redacted settings so the trace is re-runnable. No-op when disabled.
    # ------------------------------------------------------------------

    def _t_ms(self) -> int:
        """Milliseconds since the trace started — the timeline used by logs/events/frames."""
        return int((time.time() - self.start_time) * 1000)

    def record_input(self, kind: str, *, audio_bytes: Optional[bytes] = None,
                     audio_format: Optional[Dict[str, Any]] = None, text: Optional[str] = None,
                     capture_level: Optional[str] = None) -> None:
        """Record the faithful replay input — the FULL utterance, not the 1 MB sanitiser cap.

        `kind` is "audio" (base64 the bytes inline, no WAV) or "text".
        """
        if not self.enabled:
            return
        if capture_level:
            self.capture_level = capture_level
        if kind == "audio":
            self._input = {
                "kind": "audio",
                "format": audio_format or {},
                "audio_base64": base64.b64encode(audio_bytes or b"").decode("utf-8"),
                "capture_level": self.capture_level,
            }
        else:
            self._input = {"kind": "text", "text": text or ""}

    def record_request(self, request: Dict[str, Any]) -> None:
        """Record the request envelope (provider/language/skip_*/session/room/wants_audio)."""
        if not self.enabled:
            return
        self._request = dict(request)

    def record_canonical(self, rate: int, fmt: str, channels: int) -> None:
        """Record the canonical audio contract a replay conforms to."""
        if not self.enabled:
            return
        self._canonical = {"rate": rate, "format": fmt, "channels": channels}

    def record_seed_context(self, context: "UnifiedConversationContext") -> None:
        """Snapshot the 'before' context faithfully — replay seeds a fresh context from it (D-6)."""
        if not self.enabled:
            return
        self._seed_context = self._seed_snapshot(context)

    def record_config(self, config_subset: Dict[str, Any],
                      provider_models: Optional[Dict[str, Any]] = None) -> None:
        """Record the config subset that shaped this run (+ a digest for quick equality) (D-10)."""
        if not self.enabled:
            return
        self._config_subset = self._json_safe(config_subset)
        self._config_digest = self._digest(self._config_subset)
        if provider_models is not None:
            self._provider_models = self._json_safe(provider_models)

    def record_output(self, result: Any) -> None:
        """Record the oracle a replay diffs against — text/success/actions (D-6)."""
        if not self.enabled:
            return
        self.recorded_output = {
            "text": getattr(result, "text", None),
            "success": bool(getattr(result, "success", False)),
            "actions": getattr(result, "action_metadata", None) or [],
        }

    def add_handler_event(self, *, handler: str, label: str, data: Dict[str, Any]) -> None:
        """Append a `trace_event()` record (used via the module-level `trace_event`)."""
        if not self.enabled:
            return
        self.handler_events.append({
            "t_ms": self._t_ms(), "handler": handler, "label": label,
            "data": self._json_safe(data),
        })

    def add_log(self, *, level: str, logger_name: str, stage: Optional[str],
                message: str, exc_text: Optional[str] = None) -> None:
        """Append a TraceLogger record (call-site lands in slice 2; recorder lives here)."""
        if not self.enabled:
            return
        self.logs.append({
            "t_ms": self._t_ms(), "level": level, "logger": logger_name,
            "stage": stage, "message": message, "exc_text": exc_text,
        })

    def add_vad_frame(self, *, t_ms: int, is_voice: bool, energy: float, threshold: float) -> None:
        """Append a per-frame VAD verdict (segmenter level; call-site lands in slice 3)."""
        if not self.enabled:
            return
        self.vad_frames.append({
            "t_ms": t_ms, "is_voice": bool(is_voice), "energy": energy, "threshold": threshold,
        })

    def build_envelope(self) -> Dict[str, Any]:
        """Assemble the self-contained §2 trace document (replay + execution + sidecars)."""
        execution: Dict[str, Any] = {}
        if self.enabled:
            exported = self.export_trace()
            execution = {
                "pipeline_stages": exported.get("pipeline_stages", []),
                "context_evolution": exported.get("context_evolution", {}),
                "performance_metrics": exported.get("performance_metrics", {}),
            }
        envelope: Dict[str, Any] = {
            "trace_version": 1,
            "request_id": self.request_id,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "replay": {
                "input": self._input,
                "request": self._request,
                "canonical": self._canonical,
                "seed_context": self._seed_context,
                "config_subset": self._config_subset,
                "config_digest": self._config_digest,
                "provider_models": self._provider_models,
            },
            "execution": execution,
            "logs": self.logs,
            "handler_events": self.handler_events,
            "recorded_output": self.recorded_output,
        }
        # segmenter-level only — keep the key absent when empty (utterance/raw don't fill it)
        if self.vad_frames:
            envelope["vad_frames"] = self.vad_frames
        return envelope

    def to_file(self, path: Any) -> Path:
        """Write the envelope as self-contained JSON. `path` is the destination file."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(self.build_envelope(), ensure_ascii=False, indent=2),
                       encoding="utf-8")
        return out

    @staticmethod
    def _seed_snapshot(context: "UnifiedConversationContext") -> Dict[str, Any]:
        """A faithful, JSON-safe snapshot of the conversation context for re-seeding on replay."""
        try:
            raw = dataclasses.asdict(context)
        except Exception as e:  # not a dataclass / odd nested value — fall back to attributes
            logger.warning(f"seed-context asdict failed ({e}); falling back to attribute scrape")
            raw = {k: getattr(context, k, None) for k in (
                "session_id", "client_id", "room_name", "language", "supported_languages",
                "conversation_history", "handler_contexts", "state_context", "user_id",
            )}
        return TraceContext._json_safe(raw)

    @staticmethod
    def _digest(obj: Any) -> str:
        """sha256 of the canonical JSON form, prefixed `sha256:` for quick equality checks."""
        blob = json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
        return "sha256:" + hashlib.sha256(blob).hexdigest()

    @staticmethod
    def _json_safe(obj: Any) -> Any:
        """Recursively coerce to JSON-serialisable values (enums→value, bytes→base64, etc.)."""
        if obj is None or isinstance(obj, (bool, int, float, str)):
            return obj
        if isinstance(obj, dict):
            return {str(k): TraceContext._json_safe(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set)):
            return [TraceContext._json_safe(v) for v in obj]
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode("utf-8")
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return TraceContext._json_safe(dataclasses.asdict(obj))
        value = getattr(obj, "value", None)  # Enum and similar
        if value is not None and not callable(value):
            return TraceContext._json_safe(value)
        isoformat = getattr(obj, "isoformat", None)  # datetimes
        if callable(isoformat):
            try:
                return isoformat()
            except Exception:
                pass
        return str(obj)

    def _calculate_context_changes(self) -> Dict[str, Any]:
        """
        Enhanced context change analysis for UnifiedConversationContext
        
        Analyzes changes between before/after context snapshots including
        room context, handler contexts, fire-and-forget tracking, and memory usage.
        
        Returns:
            Dictionary describing comprehensive context changes during execution
        """
        before = self.context_snapshots.get("before", {})
        after = self.context_snapshots.get("after", {})
        
        if not before or not after:
            return {"summary": "Incomplete context tracking", "error": "Missing before or after snapshot"}
        
        # Existing active actions analysis
        before_actions = before.get("active_actions", {})
        after_actions = after.get("active_actions", {})
        
        actions_added = []
        actions_removed = []
        
        # Find added actions
        for domain, action_info in after_actions.items():
            if domain not in before_actions:
                actions_added.append({"domain": domain, "action": action_info})
        
        # Find removed actions
        for domain, action_info in before_actions.items():
            if domain not in after_actions:
                actions_removed.append({"domain": domain, "action": action_info})
        
        history_entries_added = after.get("conversation_history_length", 0) - before.get("conversation_history_length", 0)
        
        # NEW: Room context changes
        room_context_changed = (
            before.get("client_id") != after.get("client_id") or
            before.get("room_name") != after.get("room_name")
        )
        
        # NEW: Language changes
        language_changed = before.get("language") != after.get("language")
        
        # NEW: Handler context changes
        before_handlers = set(before.get("handler_contexts", {}).keys())
        after_handlers = set(after.get("handler_contexts", {}).keys())
        handler_contexts_modified = []
        
        for handler in before_handlers.union(after_handlers):
            before_ctx = before.get("handler_contexts", {}).get(handler, {})
            after_ctx = after.get("handler_contexts", {}).get(handler, {})
            
            if before_ctx != after_ctx:
                handler_contexts_modified.append({
                    "handler": handler,
                    "message_count_before": before_ctx.get("message_count", 0),
                    "message_count_after": after_ctx.get("message_count", 0),
                    "messages_added": after_ctx.get("message_count", 0) - before_ctx.get("message_count", 0)
                })
        
        # NEW: Fire-and-forget tracking changes
        recent_actions_added = after.get("recent_actions_count", 0) - before.get("recent_actions_count", 0)
        failed_actions_added = after.get("failed_actions_count", 0) - before.get("failed_actions_count", 0)
        
        # NEW: Device context changes
        devices_changed = before.get("available_devices_count") != after.get("available_devices_count")
        device_types_before = set(before.get("device_types", []))
        device_types_after = set(after.get("device_types", []))
        device_types_added = list(device_types_after - device_types_before)
        device_types_removed = list(device_types_before - device_types_after)
        
        # NEW: Memory usage changes
        before_memory = before.get("memory_usage", {})
        after_memory = after.get("memory_usage", {})
        try:
            memory_usage_delta_mb = after_memory.get("total_mb", 0) - before_memory.get("total_mb", 0)
        except (TypeError, ValueError):
            # Handle cases where memory usage values are not numeric (e.g., MagicMock in tests)
            memory_usage_delta_mb = 0.0
        
        # NEW: Activity tracking
        try:
            activity_time_delta = after.get("last_activity", 0) - before.get("last_activity", 0)
        except (TypeError, ValueError):
            # Handle cases where activity values are not numeric (e.g., MagicMock in tests)
            activity_time_delta = 0.0
        
        # Generate comprehensive summary
        changes_summary = []
        if actions_added:
            changes_summary.append(f"Added {len(actions_added)} active actions")
        if actions_removed:
            changes_summary.append(f"Removed {len(actions_removed)} active actions")
        if history_entries_added > 0:
            changes_summary.append(f"Added {history_entries_added} conversation entries")
        if handler_contexts_modified:
            changes_summary.append(f"Modified {len(handler_contexts_modified)} handler contexts")
        if room_context_changed:
            changes_summary.append("Room context changed")
        if language_changed:
            changes_summary.append("Language changed")
        if devices_changed:
            changes_summary.append("Device context changed")
        try:
            if abs(memory_usage_delta_mb) > 0.1:
                changes_summary.append(f"Memory usage changed by {memory_usage_delta_mb:.2f}MB")
        except (TypeError, ValueError):
            # Handle cases where memory_usage_delta_mb is not numeric
            pass
        
        return {
            # Existing analysis
            "active_actions_added": actions_added,
            "active_actions_removed": actions_removed,
            "conversation_history_entries_added": history_entries_added,
            "total_active_actions_before": len(before_actions),
            "total_active_actions_after": len(after_actions),
            
            # NEW: Room context changes
            "room_context_changed": room_context_changed,
            "room_id_before": before.get("client_id"),
            "room_id_after": after.get("client_id"),
            "room_name_before": before.get("room_name"),
            "room_name_after": after.get("room_name"),
            
            # NEW: Language changes
            "language_changed": language_changed,
            "language_before": before.get("language"),
            "language_after": after.get("language"),
            
            # NEW: Handler context changes
            "handler_contexts_modified": handler_contexts_modified,
            "handler_contexts_count_before": len(before_handlers),
            "handler_contexts_count_after": len(after_handlers),
            
            # NEW: Fire-and-forget changes
            "recent_actions_added": recent_actions_added,
            "failed_actions_added": failed_actions_added,
            "action_error_count_before": len(before.get("action_error_count", {})),
            "action_error_count_after": len(after.get("action_error_count", {})),
            
            # NEW: Device context changes
            "devices_changed": devices_changed,
            "device_count_before": before.get("available_devices_count", 0),
            "device_count_after": after.get("available_devices_count", 0),
            "device_types_added": device_types_added,
            "device_types_removed": device_types_removed,
            
            # NEW: Memory usage changes
            "memory_usage_delta_mb": round(memory_usage_delta_mb, 3),
            "memory_usage_before_mb": before_memory.get("total_mb", 0),
            "memory_usage_after_mb": after_memory.get("total_mb", 0),
            
            # NEW: Activity tracking
            "activity_time_delta_seconds": round(activity_time_delta, 3) if isinstance(activity_time_delta, (int, float)) else 0.0,
            "execution_duration_seconds": round(
                (after.get("snapshot_timestamp", 0) - before.get("snapshot_timestamp", 0)), 3
            ) if all(isinstance(x, (int, float)) for x in [after.get("snapshot_timestamp", 0), before.get("snapshot_timestamp", 0)]) else 0.0,
            
            # Enhanced summary
            "summary": "; ".join(changes_summary) if changes_summary else "No significant changes detected"
        }


# ----------------------------------------------------------------------------
# ARCH-19 — shared create/save helpers (used by both the batch boundary in
# WorkflowManager and the per-utterance streaming path in the workflow). Configs
# are duck-typed (attributes read, not imported) so `core` keeps no edge to config.
# ----------------------------------------------------------------------------

def replay_request(context: Any) -> Dict[str, Any]:
    """The faithful request envelope (ARCH-19 §2) scraped off a RequestContext."""
    return {
        "source": getattr(context, "source", None),
        "session_id": getattr(context, "session_id", None),
        "wants_audio": getattr(context, "wants_audio", None),
        "skip_wake_word": getattr(context, "skip_wake_word", None),
        "skip_asr": getattr(context, "skip_asr", None),
        "room": getattr(context, "room_name", None),
        "client_id": getattr(context, "client_id", None),
    }


def make_trace(trace_config: Any) -> Optional["TraceContext"]:
    """Mint an enabled TraceContext from `[trace]` config, or None when tracing is off (D-17)."""
    if not trace_config or not getattr(trace_config, "enabled", False):
        return None
    trace = TraceContext(enabled=True,
                         max_stages=trace_config.max_stages,
                         max_data_size_mb=trace_config.max_data_size_mb)
    trace.capture_level = trace_config.capture_level
    trace.step_hook = _step_hook  # workflow-minted traces (streaming) inherit the --step hook
    return trace


def resolve_traces_dir(trace_config: Any, assets_config: Any) -> Path:
    """Where trace files land: `[trace] traces_dir` override, else `<assets_root>/traces`."""
    override = getattr(trace_config, "traces_dir", None) if trace_config else None
    if override:
        return Path(override).expanduser()
    return assets_config.traces_root


# QUAL-58 (M8): every trace file embeds the FULL utterance audio as base64 — an always-on
# traced deployment grows the trace dir without bound. Rotation cap: newest files win. A
# constant, not config — a disk safety net, not a tunable (same reasoning as BUG-17's cap).
MAX_TRACE_FILES = 500


def _prune_trace_dir(traces_dir: Path, max_files: int = MAX_TRACE_FILES) -> None:
    """Delete the oldest trace JSONs beyond ``max_files`` (QUAL-58 M8). Best-effort."""
    try:
        files = sorted(traces_dir.glob("*.json"), key=lambda f: f.stat().st_mtime)
        for stale in files[:-max_files] if max_files > 0 else []:
            stale.unlink()
        if len(files) > max_files > 0:
            logger.debug(f"Trace rotation removed {len(files) - max_files} old trace(s) from {traces_dir}")
    except OSError as e:
        logger.warning(f"Trace rotation failed for {traces_dir}: {e}")


def save_trace(trace: Optional["TraceContext"], trace_config: Any, assets_config: Any) -> Optional[Path]:
    """Persist a trace to `<traces_dir>/<request_id>.json` — only when startup tracing is on (D-17).

    After each save the directory is rotated to the newest ``MAX_TRACE_FILES`` (QUAL-58 M8).
    """
    if trace is None or not trace.enabled:
        return None
    if not trace_config or not getattr(trace_config, "enabled", False):
        return None
    try:
        out = resolve_traces_dir(trace_config, assets_config) / f"{trace.request_id}.json"
        trace.to_file(out)
        logger.debug(f"Saved trace {trace.request_id} → {out}")
        _prune_trace_dir(out.parent)
        return out
    except Exception as e:
        logger.error(f"Failed to save trace {trace.request_id}: {e}")
        return None
