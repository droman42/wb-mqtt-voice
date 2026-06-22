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
        duration = self.get_param(intent, 'duration', None)
        unit = self.get_param(intent, 'unit', 'minutes')
        message = self.get_param(intent, 'message', self._get_template("timer_completed_default", "ru"))

        # If no duration in entities, try to parse from text
        if not duration:
            duration, unit, message = self._parse_timer_from_text(intent.raw_text)
        
        if not duration:
            language = context.language
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
            language = context.language
            time_str = self._format_duration(duration_seconds)
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
    
    def _parse_timer_from_text(self, text: str) -> tuple[Optional[int], str, str]:
        """Parse timer parameters from natural language text"""
        text_lower = text.lower()
        
        # TODO: These parsing patterns are now migrated to timer.json duration parameter extraction_patterns
        # Common patterns for timer duration
        patterns = [
            r"(\d+)\s*(секунд|сек)",
            r"(\d+)\s*(минут|мин)",
            r"(\d+)\s*(час|часа|часов)",
            r"на\s+(\d+)\s*(секунд|сек|минут|мин|час|часа|часов)",
            r"через\s+(\d+)\s*(секунд|сек|минут|мин|час|часа|часов)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                duration = int(match.group(1))
                unit_text = match.group(2)
                
                # Map Russian units to standard units
                if unit_text in ['секунд', 'сек']:
                    unit = 'seconds'
                elif unit_text in ['минут', 'мин']:
                    unit = 'minutes'
                elif unit_text in ['час', 'часа', 'часов']:
                    unit = 'hours'
                else:
                    unit = 'seconds'
                
                # Try to extract message
                message = self._extract_timer_message(text)
                
                return duration, unit, message
        
        return None, 'seconds', self._get_template("timer_completed_default", "ru")
    
    def _extract_timer_message(self, text: str) -> str:
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
        return self._get_template("timer_completed_default", "ru")
    
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
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds} сек"
        elif seconds < 3600:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            if remaining_seconds == 0:
                return f"{minutes} мин"
            else:
                return f"{minutes} мин {remaining_seconds} сек"
        else:
            hours = seconds // 3600
            remaining_minutes = (seconds % 3600) // 60
            if remaining_minutes == 0:
                return f"{hours} ч"
            else:
                return f"{hours} ч {remaining_minutes} мин"
    
    async def _run_timer(self, duration_seconds: int, message: str, session_id: str, timer_id: str) -> str:
        """The timer itself: sleep for the duration, then announce completion.

        This coroutine *is* the action-store task (registered by the F&F launch). When it returns (or
        is cancelled), the store done-callback reaps it and fires the completion/cancel notification.
        No nested tasks, no parallel `active_timers` book-keeping (that was the over-engineering).
        """
        await asyncio.sleep(duration_seconds)
        logger.info(f"🔔 Timer {timer_id} completed: {message}")
        return timer_id

    async def cleanup(self) -> None:
        """No local timer state to clean up — running timers are store-owned tasks (QUAL-28)."""
        return None