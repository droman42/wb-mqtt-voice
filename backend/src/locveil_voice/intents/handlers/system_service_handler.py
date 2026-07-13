"""
System Service Intent Handler - Service status and statistics

Replaces the AsyncServiceDemoPlugin with modern intent-based architecture.
Provides system service status and statistics information.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict

from .base import IntentHandler
from ..models import Intent, IntentResult
from ..context_models import UnifiedConversationContext

logger = logging.getLogger(__name__)


class SystemServiceIntentHandler(IntentHandler):
    """
    Handles system service intents - status checks and statistics.
    
    Features:
    - Service status information
    - Service statistics and metrics
    - System health information
    - Uptime tracking
    """
    
    def __init__(self):
        super().__init__()
        self._status_count = 0
        self._last_heartbeat = None
        self._start_time = datetime.now()

    # Build dependency methods (TODO #5 Phase 2)
    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        """System service handler needs no external dependencies - pure Python logic"""
        return []
        
    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        """System service handler has no system dependencies - pure Python logic"""
        return {
            "linux.ubuntu": [],
            "linux.alpine": [],
            "macos": [],
            "windows": []
        }
    async def execute(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Execute system service intent"""
        # Use donation-driven routing exclusively
        try:
            return await self.execute_with_donation_routing(intent, context)
        except Exception as e:
            logger.error(f"System service intent execution failed: {e}")
            # Use language from context (detected by NLU) for error response
            language = context.language
            error_text = self._get_template("general_error", language)
            
            return IntentResult(
                text=error_text,
                should_speak=True,
                success=False,
                error=str(e)
            )
        
    async def _handle_service_status(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle service status request"""
        # Simulate heartbeat update
        self._status_count += 1
        self._last_heartbeat = datetime.now()
        
        # Use language from context (detected by NLU)
        language = context.language

        # QUAL-34: optional component scope (string) — consumed and surfaced in metadata.
        component = self.get_param(intent, "component", default=None)

        # Format response using external template
        status_text = self._get_template(
            "service_status_info",
            language,
            heartbeats=self._status_count,
            last_heartbeat=self._last_heartbeat.strftime('%H:%M:%S'),
            uptime=self._get_uptime(language)
        )
        
        self.logger.info(f"Service status requested - heartbeat #{self._status_count}")
        
        return IntentResult(
            text=status_text,
            should_speak=True,
            metadata={
                "status": "running",
                "heartbeats": self._status_count,
                "last_heartbeat": self._last_heartbeat.isoformat(),
                "uptime_seconds": (datetime.now() - self._start_time).total_seconds(),
                "component": component,
                "language": language
            },
            success=True
        )
        
    async def _handle_service_stats(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle service statistics request"""
        # Simulate async data collection
        await asyncio.sleep(0.1)
        
        # Update heartbeat
        self._status_count += 1
        self._last_heartbeat = datetime.now()
        
        # Use language from context (detected by NLU)
        language = context.language

        # QUAL-34: optional metric_type (CHOICE) — the requested metric scope, consumed + surfaced.
        metric_type = self.get_param(intent, "metric_type", default=None)

        # Format response using external template
        stats_text = self._get_template(
            "service_stats_info",
            language,
            total_heartbeats=self._status_count
        )
        
        self.logger.info(f"Service statistics requested - heartbeat #{self._status_count}")
        
        return IntentResult(
            text=stats_text,
            should_speak=True,
            metadata={
                "total_heartbeats": self._status_count,
                "service_running": True,
                "background_tasks": 1,
                "memory_efficient": True,
                "non_blocking": True,
                "resource_usage": "minimal",
                "metric_type": metric_type,
                "language": language
            },
            success=True
        )
        
    async def _handle_service_health(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle service health check request"""
        # Simulate health check
        await asyncio.sleep(0.05)
        
        # Update heartbeat
        self._status_count += 1
        self._last_heartbeat = datetime.now()
        
        # Use language from context (detected by NLU)
        language = context.language
        
        # Calculate health metrics
        uptime_seconds = (datetime.now() - self._start_time).total_seconds()
        health_score = min(100, int(95 + (self._status_count * 0.1)))  # Simulate improving health
        
        # Format response using external template
        health_text = self._get_template(
            "service_health_info",
            language,
            health_score=health_score,
            uptime=self._get_uptime(language),
            last_activity=self._last_heartbeat.strftime('%H:%M:%S')
        )

        # QUAL-34: optional `detailed` (bool) appends a verbose breakdown.
        detailed = self.get_param(intent, "detailed", default=False)
        if detailed:
            health_text = f"{health_text} {self._get_template('service_health_detail', language, heartbeats=self._status_count, uptime=self._get_uptime(language))}"

        self.logger.info(f"Service health check - score: {health_score}%, detailed={detailed}")

        return IntentResult(
            text=health_text,
            should_speak=True,
            metadata={
                "health_score": health_score,
                "uptime_seconds": uptime_seconds,
                "last_activity": self._last_heartbeat.isoformat(),
                "issues_detected": 0,
                "performance": "optimal",
                "detailed": detailed,
                "language": language
            },
            success=True
        )
    

    
    def _get_uptime(self, language: str) -> str:
        """Get service uptime using external templates with language support"""
        if not self._last_heartbeat:
            return self._get_template("uptime_no_heartbeats", language)
            
        # Calculate uptime based on start time
        uptime_seconds = (datetime.now() - self._start_time).total_seconds()
        
        if uptime_seconds < 60:
            return self._get_template("uptime_seconds", language, seconds=int(uptime_seconds))
        elif uptime_seconds < 3600:
            minutes = int(uptime_seconds // 60)
            # Handle pluralization based on language
            if language == "ru":
                plural_y = "ы" if minutes in [2, 3, 4] and minutes not in [12, 13, 14] else ""
                return self._get_template("uptime_minutes", language, minutes=minutes, plural_y=plural_y)
            else:
                plural_s = "s" if minutes != 1 else ""
                return self._get_template("uptime_minutes", language, minutes=minutes, plural_s=plural_s)
        else:
            hours = int(uptime_seconds // 3600)
            # Handle pluralization based on language
            if language == "ru":
                plural_ov = "ов" if hours > 4 or hours == 0 or hours in [11, 12, 13, 14] else ""
                return self._get_template("uptime_hours", language, hours=hours, plural_ov=plural_ov)
            else:
                plural_s = "s" if hours != 1 else ""
                return self._get_template("uptime_hours", language, hours=hours, plural_s=plural_s)
            

    # Build dependency methods (TODO #5 Phase 2)
    # Configuration metadata: No configuration needed
    # This handler provides system service information using asset loader templates
    # No get_config_schema() method = no configuration required
