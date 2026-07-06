"""ARCH-31 — problem-report dialog: verbatim capture (design docs/design/problem_reports.md §2).

The dangerous case this pins: a problem DESCRIPTION reads like a command. In combine mode the
QUAL-44 arbitration would recognize «свет в спальне не включается» as a confident smart-home
intent and EXECUTE it. Verbatim mode consumes the next utterance raw — no text processing, no
NLU, no arbitration — and hands it to the report intent as its `description`.
"""
import time
from pathlib import Path

import pytest

from irene.core.intent_asset_loader import IntentAssetLoader, AssetLoaderConfig
from irene.intents.handlers.report import ReportIntentHandler
from irene.intents.models import Intent, IntentResult
from irene.intents.context_models import UnifiedConversationContext
from irene.workflows.voice_assistant import UnifiedVoiceAssistantWorkflow


class _RecordingNLU:
    fallback_intent = "conversation.general"
    confidence_threshold = 0.7

    def __init__(self):
        self.calls = []

    async def process(self, text, context, trace_context, original_text=None):
        self.calls.append(text)
        return Intent(name="smart_home.power_on", entities={}, confidence=0.95,
                      raw_text=original_text or text)


class _RecordingOrchestrator:
    def __init__(self):
        self.executed = []

    async def execute(self, intent, context, trace_context):
        self.executed.append(intent)
        return IntentResult(text="ok", should_speak=True, success=True)


def _workflow():
    wf = UnifiedVoiceAssistantWorkflow()
    wf.nlu = _RecordingNLU()
    wf.intent_orchestrator = _RecordingOrchestrator()
    wf._text_processing_enabled = False
    return wf


# --- workflow: the verbatim pre-check --------------------------------------------------------------

async def test_verbatim_consumes_command_looking_text_raw():
    wf = _workflow()
    ctx = UnifiedConversationContext(session_id="t")
    ctx.set_pending_clarification("report.problem", "description", "сообщи о проблеме",
                                  mode="verbatim", ttl_seconds=90)

    await wf._process_pipeline(input_data="свет в спальне не включается", context=None,
                               conversation_context=ctx, skip_wake_word=True, skip_asr=True)

    assert wf.nlu.calls == [], "verbatim capture must never consult NLU (QUAL-44 would hijack)"
    assert len(wf.intent_orchestrator.executed) == 1
    intent = wf.intent_orchestrator.executed[0]
    assert intent.name == "report.problem"
    assert intent.entities["description"] == "свет в спальне не включается"
    assert ctx.pending_clarification is None  # one-shot
    # the turn is in history exactly once (the single writer)
    assert len(ctx.conversation_history) == 1


async def test_expired_verbatim_falls_through_to_normal_command():
    wf = _workflow()
    ctx = UnifiedConversationContext(session_id="t")
    ctx.set_pending_clarification("report.problem", "description", "сообщи о проблеме",
                                  mode="verbatim", ttl_seconds=90)
    ctx.pending_clarification["expires_at"] = time.time() - 1  # user walked away (D-5)

    await wf._process_pipeline(input_data="включи свет", context=None,
                               conversation_context=ctx, skip_wake_word=True, skip_asr=True)

    assert wf.nlu.calls, "expired capture: the utterance is an ordinary command again"
    executed = wf.intent_orchestrator.executed
    assert executed and executed[0].name == "smart_home.power_on"


def test_combine_mode_default_keeps_no_expiry():
    ctx = UnifiedConversationContext(session_id="t")
    ctx.set_pending_clarification("timer.set", "duration", "поставь таймер")
    pending = ctx.take_pending_clarification()
    assert pending["mode"] == "combine"
    assert pending["expires_at"] is None


# --- handler: the two-turn dialog -------------------------------------------------------------------

class _FakeReportService:
    def __init__(self, status="sent"):
        self.status = status
        self.submitted = []

    async def submit(self, description, context):
        self.submitted.append(description)
        return self.status


async def _report_handler(service):
    loader = IntentAssetLoader(Path("assets"), AssetLoaderConfig(strict_mode=True))
    await loader.load_all_assets(["report"])
    h = ReportIntentHandler()
    h.set_asset_loader(loader)
    h.donation = loader.get_donation("report")
    h._donation_initialized = True
    h._asset_loader_initialized = True
    h.set_report_service(service, capture_ttl_seconds=90)
    return h


def _intent(**entities):
    return Intent(name="report.problem", entities=dict(entities), confidence=1.0,
                  raw_text=entities.get("description", "сообщи о проблеме"), domain="report")


async def test_turn1_arms_verbatim_and_asks():
    h = await _report_handler(_FakeReportService())
    ctx = UnifiedConversationContext(session_id="t", language="ru")
    result = await h.execute(_intent(), ctx)
    assert "Опишите проблему" in result.text
    pending = ctx.pending_clarification
    assert pending is not None and pending["mode"] == "verbatim"
    assert pending["intent_name"] == "report.problem"
    assert pending["expires_at"] is not None


async def test_turn2_submits_description():
    service = _FakeReportService()
    h = await _report_handler(service)
    ctx = UnifiedConversationContext(session_id="t", language="ru")
    result = await h.execute(_intent(description="таймер не сработал утром"), ctx)
    assert service.submitted == ["таймер не сработал утром"]
    assert result.success and "Отчёт отправлен" in result.text


async def test_turn2_spooled_speaks_offline_variant_and_launches_durable_retry():
    h = await _report_handler(_FakeReportService(status="spooled"))
    launches = []

    async def _record_launch(action_func, **kwargs):
        launches.append(kwargs)
        return {"status": "started"}

    h.execute_fire_and_forget_with_context = _record_launch  # the ARCH-27 seam, stubbed
    ctx = UnifiedConversationContext(session_id="t", language="ru")
    result = await h.execute(_intent(description="что-то сломалось"), ctx)
    assert "как только появится" in result.text
    # the retry promise is DURABLE (survives restarts) with a JSON-serializable deadline
    assert len(launches) == 1
    assert launches[0]["durable"] is True
    assert launches[0]["action_name"] == "report_retry"
    assert isinstance(launches[0]["deadline_ts"], float)


async def test_cancel_word_ends_dialog_without_filing():
    service = _FakeReportService()
    h = await _report_handler(service)
    ctx = UnifiedConversationContext(session_id="t", language="ru")
    result = await h.execute(_intent(description="отмена"), ctx)
    assert service.submitted == []
    assert "не буду отправлять" in result.text


async def test_unconfigured_answers_honestly_and_never_arms():
    h = await _report_handler(None)
    h.set_report_service(None)
    ctx = UnifiedConversationContext(session_id="t", language="ru")
    result = await h.execute(_intent(), ctx)
    assert result.success is False
    assert "не настроена" in result.text
    assert ctx.pending_clarification is None
