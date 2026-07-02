"""
Timer Intent Handler - Timer operations for Intent System

Handles timer creation, management, and cancellation.
Adapted from timer_plugin.py for the new intent architecture.
"""

import asyncio
import re
import time
import logging
from typing import Dict, List, Optional, Any, Type

from pydantic import BaseModel

from .base import IntentHandler
from ...core.donations import ParameterExtractionError
from ..models import Intent, IntentResult
from ..context_models import UnifiedConversationContext
from ...core.trace_context import trace_event  # ARCH-19 (D-5): opt-in, no-op when no trace is active
from ...utils.units import parse_duration  # shared bilingual time-unit parsing (the one place)

logger = logging.getLogger(__name__)


class TimerIntentHandler(IntentHandler):
    """
    Handles timer-related intents with natural language parsing.
    
    Features:
    - Natural language time parsing
    - Multiple concurrent timers
    - Timer management and cancellation
    - Context-aware timer storage
    - Async timer execution
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        # QUAL-28: timers live in the action store (registered by the F&F launch), not a local dict.
        self.timer_counter = 0
        
        # Phase 5: Configuration injection via Pydantic TimerHandlerConfig
        if config:
            self.config = config
            self.min_seconds = config.get("min_seconds", 1)
            self.max_seconds = config.get("max_seconds", 86400)
            self.unit_multipliers = config.get("unit_multipliers", {'seconds': 1, 'minutes': 60, 'hours': 3600, 'days': 86400})
            logger.info(f"TimerIntentHandler initialized with config: min_seconds={self.min_seconds}, max_seconds={self.max_seconds}")
        else:
            # Fallback defaults (should not be used in production with proper config)
            self.config = {
                "min_seconds": 1,
                "max_seconds": 86400,
                "unit_multipliers": {'seconds': 1, 'minutes': 60, 'hours': 3600, 'days': 86400}
            }
            self.min_seconds = 1
            self.max_seconds = 86400
            self.unit_multipliers = {'seconds': 1, 'minutes': 60, 'hours': 3600, 'days': 86400}
            logger.warning("TimerIntentHandler initialized without configuration - using fallback defaults")

    # Build dependency methods (TODO #5 Phase 2)
    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        """Timer handler needs no external dependencies - pure Python logic"""
        return []
        
    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        """Timer handler has no system dependencies - pure Python logic"""
        return {
            "linux.ubuntu": [],
            "linux.alpine": [],
            "macos": [],
            "windows": []
        }
    # Configuration metadata methods
    @classmethod
    def get_config_schema(cls) -> Type[BaseModel]:
        """Return configuration schema for timer handler"""
        from ...config.models import TimerHandlerConfig
        return TimerHandlerConfig
    
    @classmethod
    def get_config_defaults(cls) -> Dict[str, Any]:
        """Return default configuration values matching TOML"""
        return {
            "min_seconds": 1,        # matches config-master.toml line 427
            "max_seconds": 86400     # matches config-master.toml line 428
        }
    async def execute(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Execute timer intent"""
        try:
            if intent.action == "set" or intent.name == "timer.set":
                return await self._handle_set_timer(intent, context)
            elif intent.action == "cancel" or intent.name == "timer.cancel":
                return await self._handle_cancel_timer(intent, context)
            elif intent.action == "list" or intent.name == "timer.list":
                return await self._handle_list_timers(intent, context)
            elif intent.action == "status" or intent.name == "timer.status":
                return await self._handle_timer_status(intent, context)
            else:
                # Default: try to set timer from natural language
                return await self._handle_set_timer(intent, context)
                
        except ParameterExtractionError as e:
            # QUAL-30 / CR-A16: a structured parameter failure → conversational clarification, not a
            # swallowed error. Self-routing handlers bypass execute_with_donation_routing's boundary,
            # so re-establish it here before the broad catch.
            self.logger.info(f"Clarification needed for {intent.name}: {e}")
            return await self._clarify(intent, context, e)
        except Exception as e:
            logger.error(f"Timer intent execution failed: {e}")
            # Determine language for error response
            language = context.language
            error_text = self._get_template("general_error", language)
            
            return IntentResult(
                text=error_text,
                should_speak=True,
                success=False,
                error=str(e)
            )
    
    async def is_available(self) -> bool:
        """Timer functionality is always available"""
        return True
    async def _handle_set_timer(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle timer creation intent with fire-and-forget action execution"""
        # Extract timer parameters via the donation-driven typed accessor (QUAL-11):
        # - duration: required int; pass an explicit None so a miss degrades to text-parsing (below)
        #   instead of raising;
        # - unit/message: the declared per-language default_value wins (was a hardcoded 'seconds' that
        #   ignored the donation's "minutes" default — the latent "5 минут → 5 seconds" bug).
        language = context.language
        duration = self.get_param(intent, 'duration', None)
        unit = self.get_param(intent, 'unit', 'minutes')
        message = self.get_param(intent, 'message', self._get_template("timer_completed_default", language))

        # The utterance's own value+unit is authoritative: the shared bilingual duration parser reads
        # "one second"/«одну секунду» reliably, where the per-param CHOICE unit extraction mis-defaulted
        # the unit ("one second" → "1 minute"). Fall back to the structured NLU duration+unit only when
        # the text carries no duration at all (e.g. a param-driven invocation).
        parsed = parse_duration(intent.raw_text, language)
        if parsed:
            duration, unit = parsed
            message = self._extract_timer_message(intent.raw_text, language)

        if not duration:
            error_text = self._get_template("timer_duration_parse_error", language)
            return IntentResult(
                text=error_text,
                should_speak=True,
                success=False
            )
        
        try:
            # Convert to seconds
            duration_seconds = self._convert_to_seconds(int(duration), unit)
            
            # Generate timer ID for action tracking
            self.timer_counter += 1
            timer_id = f"timer_{self.timer_counter}"
            
            # Register a sleeper action in the store; it fires when the duration elapses. The F&F
            # timeout is duration + grace so the timeout monitor never pre-empts the timer's own
            # completion. Cancellation/listing/status all read this back from the store.
            action_metadata = await self.execute_fire_and_forget_with_context(
                self._run_timer,
                action_name=timer_id,
                domain="timers",
                context=context,
                timeout=duration_seconds + 5.0,
                completion_message=message,   # BUG-4/F&F: announced (in the request language) when the timer fires
                durable=True,                  # ARCH-28: a timer is a promise — it survives a restart
                redeliver_on_reconnect=True,   # D-6: the ring survives a briefly-offline satellite too
                duration_seconds=duration_seconds,
                message=message,
                session_id=context.session_id,
                timer_id=timer_id
            )
            # (The launch itself is traced generically as `action_launched` in the base F&F helper;
            # this adds the timer-specific detail the generic event can't carry.)
            trace_event("timer_set", {"duration_s": duration_seconds, "timer_id": timer_id},
                        handler="timer")

            # Format response using template
            time_str = self._format_duration(duration_seconds, language)
            response = self._get_template("timer_set_success", language, time_str=time_str, message=message)
            
            return self.create_action_result(
                response_text=response,
                action_name=timer_id,
                domain="timers",
                should_speak=True,
                action_metadata=action_metadata
            )
            
        except ValueError as e:
            language = context.language
            error_text = self._get_template("timer_set_error", language, error=str(e))
            return IntentResult(
                text=error_text,
                should_speak=True,
                success=False
            )
    
    def _session_timer_names(self, context: UnifiedConversationContext) -> List[str]:
        """Live timer action_names for this scope, read from the action store."""
        return [name for name, info in context.active_actions.items() if info.get("domain") == "timers"]

    async def _handle_cancel_timer(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Cancel a specific timer (by id) or all timers — by cancelling their store tasks."""
        timer_id = intent.entities.get('timer_id')
        active = self._session_timer_names(context)
        language = context.language

        if not active:
            return IntentResult(text=self._get_template("timer_no_active", language), should_speak=True)
        if timer_id and timer_id not in active:
            return IntentResult(text=self._get_template("timer_cancel_not_found", language, timer_id=timer_id),
                                should_speak=True, success=False)

        # Cancel the timer task(s); the store done-callback reaps them. (A specific-id cancel currently
        # cancels the domain — fine for the common single-timer case.)
        context.cancel_action("timers")
        trace_event("timer_cancel", {"timer_id": timer_id, "count": len(active)}, handler="timer")
        if timer_id:
            return IntentResult(text=self._get_template("timer_cancel_success", language, timer_id=timer_id),
                                should_speak=True)
        return IntentResult(text=self._get_template("timer_cancel_all_success", language, count=len(active)),
                            should_speak=True)
    
    async def _handle_stop_timer(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """
        Handle domain-specific timer stop intent (timer.stop).
        
        Phase 2 TODO16: Standardized stop handling - only receives resolved intents.
        """
        language = context.language
        active = self._session_timer_names(context)
        if not active:
            return IntentResult(text=self._get_template("stop_no_timers", language),
                                should_speak=True, success=True)
        context.cancel_action("timers")  # cancel all timer tasks; the store reaps them
        trace_event("timer_stop", {"count": len(active)}, handler="timer")
        return IntentResult(text=self._get_template("stop_all_timers", language, count=len(active)),
                            should_speak=True)
    
    async def _handle_pause_timer(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """
        Handle domain-specific timer pause intent (timer.pause).
        
        Phase 2 TODO16: Standardized contextual command handling.
        """
        # NOTE: a sleeping timer task can't truly be paused; this flags status only (the prior
        # implementation was likewise cosmetic). Marks the timers "paused" in the store.
        language = context.language
        active = self._session_timer_names(context)
        if not active:
            return IntentResult(text=self._get_template("pause_no_active_timers", language),
                                should_speak=True, success=True)
        context.update_action_status("timers", "paused")
        return IntentResult(text=self._get_template("pause_timers", language, count=len(active)),
                            should_speak=True, success=True)
    
    async def _handle_resume_timer(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """
        Handle domain-specific timer resume intent (timer.resume).
        
        Phase 2 TODO16: Standardized contextual command handling.
        """
        language = context.language
        paused = [name for name, info in context.active_actions.items()
                  if info.get("domain") == "timers" and info.get("status") == "paused"]
        if not paused:
            return IntentResult(text=self._get_template("resume_no_paused_timers", language),
                                should_speak=True, success=True)
        context.update_action_status("timers", "running")
        return IntentResult(text=self._get_template("resume_timers", language, count=len(paused)),
                            should_speak=True, success=True)
    
    async def _handle_list_timers(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle list timers intent"""
        language = context.language
        timers = [(name, info) for name, info in context.active_actions.items() if info.get("domain") == "timers"]
        if not timers:
            return IntentResult(text=self._get_template("timer_list_empty", language), should_speak=True)

        now = time.time()
        timer_list = []
        for timer_id, info in timers:
            end = info.get("expected_end")
            remaining = int(end - now) if end else None
            if remaining is None or remaining > 0:
                time_str = self._format_duration(remaining) if remaining else "?"
                timer_list.append(f"Таймер {timer_id}: {time_str}")

        if not timer_list:
            return IntentResult(text=self._get_template("timer_list_expired", language), should_speak=True)

        timer_list_str = "\n".join(timer_list)
        response = self._get_template("timer_list_active", language, count=len(timer_list), timer_list=timer_list_str)
        return IntentResult(text=response, should_speak=True, metadata={"active_timer_count": len(timer_list)})
    
    async def _handle_timer_status(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle timer status inquiry intent"""
        language = context.language
        timers = [(name, info) for name, info in context.active_actions.items() if info.get("domain") == "timers"]
        if not timers:
            return IntentResult(text=self._get_template("timer_no_active", language), should_speak=True)

        # Most recently started timer
        timer_id, info = max(timers, key=lambda x: x[1].get("started_at", 0))
        now = time.time()
        end = info.get("expected_end")
        remaining = int(end - now) if end else 0
        if remaining <= 0:
            response = self._get_template("timer_status_expired", language, timer_id=timer_id)
        else:
            time_str = self._format_duration(remaining)
            response = self._get_template("timer_status_remaining", language, timer_id=timer_id, time_str=time_str)
        return IntentResult(text=response, should_speak=True,
                            metadata={"timer_id": timer_id, "remaining_seconds": max(0, remaining)})
    
    def _extract_timer_message(self, text: str, language: str = "ru") -> str:
        """Extract custom message from timer text"""
        # TODO: These message patterns are now migrated to timer.json message parameter extraction_patterns
        # Look for message patterns
        message_patterns = [
            r"сообщение[:\s]+(.*)",
            r"напомни[:\s]+(.*)",
            r"скажи[:\s]+(.*)",
        ]
        
        for pattern in message_patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(1).strip()
        
        # Use template default value
        return self._get_template("timer_completed_default", language)
    
    def _convert_to_seconds(self, duration: int, unit: str) -> int:
        """Convert duration to seconds using injected configuration"""
        # Phase 5: Use injected unit multipliers from configuration
        multiplier = self.unit_multipliers.get(unit, 1)
        total_seconds = duration * multiplier
        
        # Use configured limits
        if total_seconds < self.min_seconds:
            raise ValueError(f"Время таймера слишком мало (минимум {self.min_seconds} секунд)")
        if total_seconds > self.max_seconds:
            max_hours = self.max_seconds // 3600
            raise ValueError(f"Время таймера слишком велико (максимум {max_hours} часов)")
        
        return total_seconds
    
    def _format_duration(self, seconds: int, language: str = "ru") -> str:
        """Format duration in human-readable format, in the request language (BUG-3)."""
        sec, minute, hour = (("sec", "min", "h") if language == "en" else ("сек", "мин", "ч"))
        if seconds < 60:
            return f"{seconds} {sec}"
        elif seconds < 3600:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            if remaining_seconds == 0:
                return f"{minutes} {minute}"
            else:
                return f"{minutes} {minute} {remaining_seconds} {sec}"
        else:
            hours = seconds // 3600
            remaining_minutes = (seconds % 3600) // 60
            if remaining_minutes == 0:
                return f"{hours} {hour}"
            else:
                return f"{hours} {hour} {remaining_minutes} {minute}"
    
    async def _run_timer(self, duration_seconds: int, message: str, session_id: str, timer_id: str) -> str:
        """The timer itself: sleep for the duration, then announce completion.

        This coroutine *is* the action-store task (registered by the F&F launch). When it returns (or
        is cancelled), the store done-callback reaps it and fires the completion/cancel notification.
        No nested tasks, no parallel `active_timers` book-keeping (that was the over-engineering).
        """
        await asyncio.sleep(duration_seconds)
        logger.info(f"🔔 Timer {timer_id} completed: {message}")
        return timer_id

    async def rearm_durable_action(self, record) -> bool:
        """ARCH-28 D-3: re-arm a persisted timer after a restart with its REMAINING time.

        The persisted `rearm.params` are the original launch kwargs; the fire moment is
        `started_at + duration_seconds` (the record's deadline minus the +5s monitor grace).
        Relaunches through the normal F&F path reusing the persisted action_name (D-8), and
        bumps `timer_counter` past the re-armed name so new timers can't collide with it.
        """
        params = dict((record.rearm or {}).get("params") or {})
        original_duration = int(params.get("duration_seconds", 0))
        if original_duration <= 0:
            return False
        remaining = int(record.started_at + original_duration - time.time())
        if remaining < 1:
            return False  # deadline effectively passed — reconciler handles fire-late/expiry

        # Post-restart the counter starts at 0 again; keep minted names ahead of re-armed ones.
        try:
            suffix = int(record.action_name.rsplit("_", 1)[1])
            self.timer_counter = max(self.timer_counter, suffix)
        except (IndexError, ValueError):
            pass

        params["duration_seconds"] = remaining
        metadata = record.metadata or {}
        await self.execute_fire_and_forget_action(
            self._run_timer,
            action_name=record.action_name,
            domain=record.domain,
            physical_id=record.physical_id,
            owner_session_id=record.session_id,
            room_id=record.room_id,
            source=record.source,
            timeout=remaining + 5.0,
            language=metadata.get("language"),
            completion_message=metadata.get("completion_message"),
            durable=True,
            redeliver_on_reconnect=record.redeliver,
            **params
        )
        logger.info(f"Re-armed timer {record.action_name}: {remaining}s remaining after restart")
        return True

    async def cleanup(self) -> None:
        """No local timer state to clean up — running timers are store-owned tasks (QUAL-28)."""
        return None