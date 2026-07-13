"""QUAL-31 Grade-2 clarification — multi-turn slot-filling.

Grade 1 (QUAL-30) asks for a missing required parameter in a single turn but abandons the original
command. Grade 2 makes the ask a real dialogue turn: the handler arms a one-shot `pending_clarification`
on the session, and the pipeline reads the NEXT utterance as the answer — prepending the original
utterance so the full understanding pipeline resumes the original intent on the combined text.

Covered here:
  1. `_clarify` arms `pending_clarification` with the original command + the asked-for slot.
  2. `pending_clarification` is one-shot (consumed by exactly the next turn).
  3. The pipeline pre-check resumes by feeding NLU the COMBINED utterance and clears the pending marker.
"""
from pathlib import Path

import pytest

from locveil_voice.core.intent_asset_loader import IntentAssetLoader, AssetLoaderConfig
from locveil_voice.core.donations import HandlerDonation, MethodDonation, ParameterSpec, ParameterType
from locveil_voice.intents.handlers.base import IntentHandler
from locveil_voice.intents.models import Intent, IntentResult
from locveil_voice.intents.context_models import UnifiedConversationContext
from locveil_voice.workflows.voice_assistant import UnifiedVoiceAssistantWorkflow


class _ClarifyHandler(IntentHandler):
    async def execute(self, intent, context):  # pragma: no cover - routed via donation
        ...

    async def can_handle(self, intent):  # pragma: no cover
        return True

    @classmethod
    def get_python_dependencies(cls):
        return []

    @classmethod
    def get_platform_dependencies(cls):
        return {"linux.ubuntu": []}

    @classmethod
    def get_platform_support(cls):
        return ["linux.ubuntu"]

    async def _handle_set(self, intent, context):
        # required param, NO caller default → get_param raises → _clarify boundary
        self.get_param(intent, "duration")
        return self._create_error_result("unreached", "x")


async def _handler() -> _ClarifyHandler:
    loader = IntentAssetLoader(Path("assets"), AssetLoaderConfig())
    await loader.load_all_assets(["timer"])
    h = _ClarifyHandler()
    h.set_asset_loader(loader)
    h.set_donation(HandlerDonation(
        schema_version="1.1", handler_domain="demo", description="demo",
        method_donations=[MethodDonation(
            method_name="_handle_set", intent_suffix="set", description="demo", phrases=["x"],
            parameters=[ParameterSpec(name="duration", type=ParameterType.INTEGER, required=True,
                                      description="Продолжительность таймера")])]))
    return h


async def test_clarify_arms_pending_clarification():
    """The Grade-1 boundary also leaves a resumable marker for Grade 2."""
    h = await _handler()
    ctx = UnifiedConversationContext(session_id="t")
    ctx.language = "ru"
    assert ctx.pending_clarification is None

    await h.execute_with_donation_routing(
        Intent(name="demo.set", entities={}, confidence=0.9, raw_text="поставь таймер"), ctx)

    pending = ctx.pending_clarification
    assert pending is not None
    assert pending["intent_name"] == "demo.set"
    assert pending["missing_param"] == "duration"
    assert pending["original_text"] == "поставь таймер"


def test_pending_clarification_is_one_shot():
    ctx = UnifiedConversationContext(session_id="t")
    ctx.set_pending_clarification("demo.set", "duration", "поставь таймер")
    first = ctx.take_pending_clarification()
    assert first is not None and first["missing_param"] == "duration"
    # consumed: a second take (the turn after the answer) sees nothing
    assert ctx.take_pending_clarification() is None
    assert ctx.pending_clarification is None


class _FakeNLU:
    """Text-aware fake: recognizes the utterances in `known` confidently; everything else
    (bare slot answers, fragments) falls back low-confidence — the realistic shape the
    QUAL-44 arbitration depends on. Records every call."""
    fallback_intent = "conversation.general"
    confidence_threshold = 0.7

    def __init__(self, known=None):
        self.calls = []  # list of (text, original_text)
        self._known = known or {}

    @property
    def seen_text(self):
        return self.calls[-1][0] if self.calls else None

    @property
    def seen_original(self):
        return self.calls[-1][1] if self.calls else None

    async def process(self, text, context, trace_context, original_text=None):
        self.calls.append((text, original_text))
        name, confidence = self._known.get(text, ("conversation.general", 0.3))
        return Intent(name=name, entities={}, confidence=confidence,
                      raw_text=original_text or text)


class _FakeOrchestrator:
    async def execute(self, intent, context, trace_context):
        return IntentResult(text="ok", should_speak=True, success=True, confidence=0.9)


async def test_pipeline_resumes_with_combined_utterance():
    """A BARE slot answer (recognizes as nothing on its own) is prepended with the original
    utterance and fed to NLU; the one-shot marker is cleared. The QUAL-44 arbitration probe
    runs first and correctly classifies the fragment as an answer."""
    wf = UnifiedVoiceAssistantWorkflow()
    fake_nlu = _FakeNLU(known={"поставь таймер на 5 минут": ("timer.set", 0.9)})
    wf.nlu = fake_nlu
    wf.intent_orchestrator = _FakeOrchestrator()
    wf._text_processing_enabled = False   # skip Stage 1 so we read NLU's input directly

    ctx = UnifiedConversationContext(session_id="t")
    ctx.set_pending_clarification(intent_name="timer.set", missing_param="duration",
                                  original_text="поставь таймер")

    result = await wf._process_pipeline(
        input_data="на 5 минут", context=None, conversation_context=ctx,
        skip_wake_word=True, skip_asr=True)

    assert result.success is True
    # call 1 = the QUAL-44 arbitration probe on the bare answer; call 2 = the real pass
    assert fake_nlu.calls[0][0] == "на 5 минут"
    # NLU's real pass saw the COMBINED utterance, not just the bare answer
    assert fake_nlu.seen_text == "поставь таймер на 5 минут"
    assert fake_nlu.seen_original == "поставь таймер на 5 минут"
    # one-shot consumed
    assert ctx.pending_clarification is None


async def test_pipeline_abandons_clarification_for_new_command():
    """QUAL-44: a turn that independently recognizes as a confident, non-fallback intent is a NEW
    COMMAND — the pending clarification is dropped and the utterance is processed fresh, never
    glued onto the old one («поставь таймер переключи телек на hdmi1»)."""
    wf = UnifiedVoiceAssistantWorkflow()
    fake_nlu = _FakeNLU(known={"переключи телек на hdmi1": ("smart_home.input_select", 0.79)})
    wf.nlu = fake_nlu
    wf.intent_orchestrator = _FakeOrchestrator()
    wf._text_processing_enabled = False

    ctx = UnifiedConversationContext(session_id="t")
    ctx.set_pending_clarification(intent_name="timer.set", missing_param="duration",
                                  original_text="поставь таймер")

    await wf._process_pipeline(
        input_data="переключи телек на hdmi1", context=None, conversation_context=ctx,
        skip_wake_word=True, skip_asr=True)

    # the real pass ran on the BARE new command — no combine anywhere
    assert fake_nlu.seen_text == "переключи телек на hdmi1"
    assert all("поставь таймер" not in text for text, _ in fake_nlu.calls)
    assert ctx.pending_clarification is None


async def test_pipeline_low_confidence_command_still_combines():
    """QUAL-44 boundary: a turn that recognizes only WEAKLY (below the threshold) is treated as
    the answer — combining stays the default for anything short of a confident fresh command."""
    wf = UnifiedVoiceAssistantWorkflow()
    fake_nlu = _FakeNLU(known={"телек": ("smart_home.power_on", 0.4)})
    wf.nlu = fake_nlu
    wf.intent_orchestrator = _FakeOrchestrator()
    wf._text_processing_enabled = False

    ctx = UnifiedConversationContext(session_id="t")
    ctx.set_pending_clarification(intent_name="smart_home.playback_pause",
                                  missing_param="target", original_text="поставь на паузу")

    await wf._process_pipeline(
        input_data="телек", context=None, conversation_context=ctx,
        skip_wake_word=True, skip_asr=True)

    assert fake_nlu.seen_text == "поставь на паузу телек"


async def test_pipeline_normal_turn_unaffected():
    """No pending clarification → the utterance flows through unchanged (no prepend)."""
    wf = UnifiedVoiceAssistantWorkflow()
    fake_nlu = _FakeNLU()
    wf.nlu = fake_nlu
    wf.intent_orchestrator = _FakeOrchestrator()
    wf._text_processing_enabled = False

    ctx = UnifiedConversationContext(session_id="t")
    await wf._process_pipeline(
        input_data="который час", context=None, conversation_context=ctx,
        skip_wake_word=True, skip_asr=True)

    assert fake_nlu.seen_text == "который час"
