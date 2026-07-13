"""
System Intent Handler - Essential system commands for Intent System

Provides system control and information commands.
Adapted from core_commands.py for the new intent architecture.
"""

import logging
import time
from datetime import datetime
from typing import List, Optional, Dict, Any, Type
from ...__version__ import __version__

from pydantic import BaseModel

from .base import IntentHandler
from ...core.donations import ParameterExtractionError
from ...core.trace_context import trace_event  # ARCH-19 (D-5): opt-in, no-op when no trace is active
from ..models import Intent, IntentResult
from ..context_models import UnifiedConversationContext

logger = logging.getLogger(__name__)


class SystemIntentHandler(IntentHandler):
    """
    Handles system control and status intents.
    
    Features:
    - System shutdown/restart
    - Status queries
    - Volume control
    - Time/date queries
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.start_time = time.time()
        
        # Configuration injection via Pydantic SystemHandlerConfig
        if config:
            self.config = config
            self.allow_shutdown = config.get("allow_shutdown", False)
            self.allow_restart = config.get("allow_restart", False)
            self.info_detail_level = config.get("info_detail_level", "basic")
            logger.info(f"SystemIntentHandler initialized with config: allow_shutdown={self.allow_shutdown}, allow_restart={self.allow_restart}, info_detail_level={self.info_detail_level}")
        else:
            # Fallback defaults (should not be used in production with proper config)
            self.config = {
                "allow_shutdown": False,
                "allow_restart": False,
                "info_detail_level": "basic"
            }
            self.allow_shutdown = False
            self.allow_restart = False
            self.info_detail_level = "basic"
            logger.warning("SystemIntentHandler initialized without configuration - using fallback defaults")

    # Build dependency methods (TODO #5 Phase 2)
    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        """System handler needs no external dependencies - pure Python logic"""
        return []
        
    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        """System handler has no system dependencies - pure Python logic"""
        return {
            "linux.ubuntu": [],
            "linux.alpine": [],
            "macos": [],
            "windows": []
        }
    # Configuration metadata methods
    @classmethod
    def get_config_schema(cls) -> Type[BaseModel]:
        """Return configuration schema for system handler"""
        from ...config.models import SystemHandlerConfig
        return SystemHandlerConfig
    
    @classmethod
    def get_config_defaults(cls) -> Dict[str, Any]:
        """Return default configuration values matching TOML"""
        return {
            "allow_shutdown": False,     # matches config-master.toml line 445
            "allow_restart": False,      # matches config-master.toml line 446
            "info_detail_level": "basic" # matches config-master.toml line 447
        }
    async def execute(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Execute system intent"""
        try:
            # Use language from context (detected by NLU)
            language = context.language
            
            if intent.action == "help" or intent.name == "system.help":
                return await self._handle_help_request(intent, context)
            elif intent.action == "status" or intent.name == "system.status":
                return await self._handle_status_request(intent, context)
            elif intent.action == "version" or intent.name == "system.version":
                return await self._handle_version_request(intent, context)
            elif intent.action == "info" or intent.name == "system.info":
                return await self._handle_info_request(intent, context)
            elif intent.action == "language_switch" or intent.name == "system.language_switch":
                # dispatched here by action, not by donation routing — the helper deliberately
                # does NOT carry the `_handle_` prefix (QUAL-66: that prefix promises a donation entry)
                return await self._do_language_switch(intent, context)
            else:
                # Default: provide general system information
                return await self._handle_general_info(intent, context)
                
        except ParameterExtractionError as e:
            # QUAL-30 / CR-A16: a structured parameter failure → conversational clarification, not a
            # swallowed error. Self-routing handlers bypass execute_with_donation_routing's boundary,
            # so re-establish it here before the broad catch.
            self.logger.info(f"Clarification needed for {intent.name}: {e}")
            return await self._clarify(intent, context, e)
        except Exception as e:
            logger.error(f"System intent execution failed: {e}")
            language = context.language
            return IntentResult(
                text=self._get_template("command_error", language),
                should_speak=True,
                success=False,
                error=str(e)
            )
    
    async def is_available(self) -> bool:
        """System commands are always available"""
        return True
    async def _handle_help_request(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle help/assistance request"""
        # Use language from context (detected by NLU)
        language = context.language
        
        # QUAL-34: optional `topic` (string) — the help subject the user asked about, consumed + surfaced.
        topic = self.get_param(intent, "topic", default=None)

        help_text = self._get_template("help", language)

        return IntentResult(
            text=help_text,
            should_speak=True,
            metadata={
                "help_type": "general",
                "topic": topic,
                "language": language,
                "capabilities_listed": True
            }
        )
    
    async def _handle_status_request(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle system status request"""
        # Use language from context (detected by NLU)
        language = context.language
        
        uptime_seconds = time.time() - self.start_time
        uptime_hours = int(uptime_seconds // 3600)
        uptime_minutes = int((uptime_seconds % 3600) // 60)
        
        if language == "en":
            if uptime_hours > 0:
                uptime_str = f"{uptime_hours} hours and {uptime_minutes} minutes"
            else:
                uptime_str = f"{uptime_minutes} minutes"
        else:
            if uptime_hours > 0:
                uptime_str = f"{uptime_hours} часов и {uptime_minutes} минут"
            else:
                uptime_str = f"{uptime_minutes} минут"
        
        # QUAL-34: optional `component` (string) — status scope requested by the user, consumed + surfaced.
        component = self.get_param(intent, "component", default=None)

        # TODO #15: Move hardcoded version to TOML configuration (not JSON donations)
        version = __version__
        status_text = self._get_template("status", language, uptime_str=uptime_str, version=version)

        return IntentResult(
            text=status_text,
            should_speak=True,
            metadata={
                "status": "running",
                "uptime_seconds": uptime_seconds,
                "version": version,
                "component": component,
                "language": language
            }
        )
    
    async def _handle_version_request(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle version information request"""
        # Use language from context (detected by NLU)
        language = context.language
        
        version = __version__
        version_text = self._get_template("version", language, version=version)
        
        return IntentResult(
            text=version_text,
            should_speak=True,
            metadata={
                "version": version,
                "architecture": "intent-based",
                "language": language
            }
        )
    
    async def _handle_info_request(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle general information request. QUAL-33: honour the declared `info_type` CHOICE param
        (canonical: system | performance) — was previously ignored."""
        language = context.language
        session_stats = self._get_session_stats(context)
        info_type = (intent.entities.get("info_type") or "system").strip().lower()

        if info_type == "performance":
            from ...core.metrics import get_metrics_collector
            perf = get_metrics_collector().get_performance_summary()
            uptime_seconds = time.time() - self.start_time
            uptime_hours = int(uptime_seconds // 3600)
            uptime_minutes = int((uptime_seconds % 3600) // 60)
            if uptime_hours > 0:
                uptime_str = (f"{uptime_hours} hours and {uptime_minutes} minutes" if language == "en"
                              else f"{uptime_hours} часов и {uptime_minutes} минут")
            else:
                uptime_str = f"{uptime_minutes} minutes" if language == "en" else f"{uptime_minutes} минут"
            info_text = self._get_template(
                "performance", language,
                uptime_str=uptime_str,
                total_actions=perf.get("total_actions", 0),
                success_rate=f"{perf.get('success_rate', 0.0) * 100:.0f}%",
                avg_duration=f"{perf.get('average_duration', 0.0):.2f}s",
            )
        else:  # system (default)
            info_type = "system"
            info_text = self._get_template(
                "info", language,
                version=__version__,
                session_start_time=datetime.fromtimestamp(context.created_at).strftime('%H:%M'),
                message_count=len(context.conversation_history),
                session_id=context.session_id
            )

        return IntentResult(
            text=info_text,
            should_speak=True,
            metadata={"info_type": info_type, "session_info": session_stats, "language": language}
        )
    
    async def _handle_general_info(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle general system information request"""
        # Use language from context (detected by NLU)
        language = context.language
        
        version = __version__
        info_text = self._get_template("general", language, version=version)
        
        return IntentResult(
            text=info_text,
            should_speak=True,
            metadata={
                "type": "general_info",
                "language": language
            }
        )
    
    async def _do_language_switch(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """
        Handle language switching requests.
        
        Phase 3: Language switching support implementation.
        """
        target_language = intent.entities.get('language')

        # Validate against the canonical supported set carried on the session (QUAL-36) — no baked ["ru","en"]
        if not target_language or target_language not in context.supported_languages:
            return IntentResult(
                text=self._get_template("language_unsupported", context.language),
                should_speak=True
            )
        
        # Update context and preferences using context manager
        try:
            # Use the injected context manager to update language preference (QUAL-24)
            if self.context_manager is not None:
                await self.context_manager.update_language_preference(context.session_id, target_language)
            else:
                # Fallback: update context directly
                context.language = target_language
                context.user_preferences['language'] = target_language
        except Exception as e:
            logger.warning(f"Could not access context manager for language update: {e}")
            # Fallback: update context directly
            context.language = target_language
            context.user_preferences['language'] = target_language

        trace_event("language_switch", {"target_language": target_language}, handler="system")

        # Announce the switch IN the target language (template keyed by target_language).
        response = self._get_template("language_changed", target_language)
        
        return IntentResult(
            text=response,
            should_speak=True,
            metadata={'language_changed': target_language},
            success=True
        )
    
    def _get_session_stats(self, context: UnifiedConversationContext) -> Dict[str, Any]:
        """Get session statistics"""
        return {
            "session_id": context.session_id,
            "created_at": context.created_at,
            "last_updated": context.last_updated,
            "message_count": len(context.conversation_history),
            "session_duration": time.time() - context.created_at
        }
    
 