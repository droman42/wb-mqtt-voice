"""
Problem Report Intent Handler — «сообщи о проблеме» (ARCH-30 design, ARCH-31 build).

Two-turn dialog: the intent fires → the handler arms a VERBATIM capture (the workflow consumes
the next utterance raw, before the QUAL-44 arbitration — a description like «свет не включается»
must never execute as a command) → the description lands back here and is handed to the report
service (the ARCH-32 delivery path). With reporting unconfigured the intent answers honestly at
turn one and never arms anything. Full design: docs/design/problem_reports.md.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from .base import IntentHandler
from ..models import Intent, IntentResult
from ..context_models import UnifiedConversationContext

logger = logging.getLogger(__name__)

_RETRY_WINDOW_S = 48 * 3600   # keep trying for two days, then announce failure (durable default)
_RETRY_INTERVAL_S = 300       # one attempt every 5 minutes while spooled

# Recognition constants for ending the capture (not user-facing speech — replies come from
# templates). Matched against the whole trimmed utterance, casefolded, trailing punctuation off.
_CANCEL_WORDS = frozenset({
    "отмена", "отменить", "не важно", "неважно", "забудь",
    "cancel", "never mind", "nevermind", "forget it",
})


class ReportIntentHandler(IntentHandler):
    """Files user problem reports through the configured report service (ARCH-30)."""

    def __init__(self):
        super().__init__()
        # Injected by the composition root when [reports] is enabled (ARCH-32). None ⇒ the
        # intent answers that reporting isn't set up — the dialog is never armed half-working.
        self.report_service: Optional[Any] = None
        self.capture_ttl_seconds: float = 90.0

    def set_report_service(self, service: Optional[Any],
                           capture_ttl_seconds: float = 90.0) -> None:
        """Inject the delivery service + the D-5 capture window (from `[reports]`)."""
        self.report_service = service
        self.capture_ttl_seconds = capture_ttl_seconds

    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        return []

    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        return {"linux.ubuntu": [], "linux.alpine": [], "macos": [], "windows": []}

    async def execute(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        return await self.execute_with_donation_routing(intent, context)

    async def is_available(self) -> bool:
        return True

    @staticmethod
    def _is_cancel(text: str) -> bool:
        return text.strip().rstrip(".!,").casefold() in _CANCEL_WORDS

    async def _handle_problem(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        language = context.language
        if self.report_service is None:
            return IntentResult(
                text=self._get_template("err_unconfigured", language),
                should_speak=True, success=False,
                error="problem reporting not configured ([reports] disabled)")

        description = self.get_param(intent, "description", default=None)
        if not description:
            # Turn 1: arm the verbatim capture — the workflow hands the NEXT utterance straight
            # back to this intent as `description`, raw (design §2).
            context.set_pending_clarification(
                "report.problem", "description", intent.raw_text,
                mode="verbatim", ttl_seconds=self.capture_ttl_seconds)
            return IntentResult(
                text=self._get_template("ask_description", language),
                should_speak=True,
                metadata={"clarification": True, "clarification_reason": "report_description"})

        # Turn 2: the captured description (or an escape word).
        if self._is_cancel(str(description)):
            return IntentResult(text=self._get_template("cancelled", language),
                                should_speak=True)

        try:
            status = await self.report_service.submit(str(description), context)
        except Exception as e:
            logger.error(f"Problem report submission failed: {e}")
            return IntentResult(
                text=self._template_or("err_failed", language,
                                       "Не получилось отправить отчёт."),
                should_speak=True, success=False, error=str(e))

        if status == "rate_limited":
            return IntentResult(text=self._get_template("err_rate_limited", language),
                                should_speak=True, success=False,
                                error="report rate limit reached (D-7)")

        if status == "spooled":
            # The "I'll send it when I'm online" promise outlives this interaction and must
            # survive a restart → durable action (ARCH-27 invariant), re-armed via
            # rearm_durable_action below. Completion speaks in the request language (BUG-4).
            await self.execute_fire_and_forget_with_context(
                self._retry_spooled_reports,
                action_name="report_retry",
                domain="report",
                context=context,
                timeout=_RETRY_WINDOW_S + 60,
                completion_message=self._get_template("confirm_sent", language),
                durable=True,
                deadline_ts=time.time() + _RETRY_WINDOW_S,
            )
            return IntentResult(text=self._get_template("confirm_spooled", language),
                                should_speak=True, metadata={"report_status": status})

        return IntentResult(text=self._get_template("confirm_sent", language),
                            should_speak=True, metadata={"report_status": status})

    async def _retry_spooled_reports(self, deadline_ts: float, **_kwargs) -> str:
        """Durable retry loop: deliver every spooled report, checking every few minutes until
        the deadline. Idempotent across duplicate launches — a report another loop already
        delivered simply isn't in the spool anymore."""
        while time.time() < deadline_ts:
            service = self.report_service
            if service is None:
                raise RuntimeError("report service disappeared while reports were spooled")
            ids = service.spooled_ids()
            if not ids:
                return "delivered"
            for report_id in ids:
                await service.retry_spooled(report_id)
            if not service.spooled_ids():
                return "delivered"
            await asyncio.sleep(_RETRY_INTERVAL_S)
        raise RuntimeError("report retry window expired with undelivered reports")

    async def rearm_durable_action(self, record) -> bool:
        """ARCH-28: re-arm the spool-retry promise after a restart with its remaining window."""
        params = dict((record.rearm or {}).get("params") or {})
        deadline_ts = float(params.get("deadline_ts") or 0)
        if deadline_ts <= time.time():
            return False  # window passed — the reconciler announces expiry
        metadata = record.metadata or {}
        await self.execute_fire_and_forget_action(
            self._retry_spooled_reports,
            action_name=record.action_name,
            domain=record.domain,
            physical_id=record.physical_id,
            owner_session_id=record.session_id,
            room_id=record.room_id,
            source=record.source,
            timeout=(deadline_ts - time.time()) + 60,
            language=metadata.get("language"),
            completion_message=metadata.get("completion_message"),
            durable=True,
            redeliver_on_reconnect=record.redeliver,
            deadline_ts=deadline_ts,
        )
        logger.info(f"Re-armed report retry ({record.action_name}) after restart")
        return True
