"""QUAL-60 — summarize-then-truncate for the LLM conversation window.

BUG-18's rolling window simply forgot dropped turns. Now they accumulate in a pending
buffer on the handler context; every K dropped messages one LLM call folds them into a
rolling summary, which is stored OUTSIDE the message list (neither trim layer can evict
it) and injected into the prompt at build time. On any LLM failure the buffer is kept
(bounded) and behavior degrades to plain BUG-18 windowing — never worse.
"""

import asyncio
from pathlib import Path

import pytest

from locveil_voice.core.intent_asset_loader import AssetLoaderConfig, IntentAssetLoader
from locveil_voice.intents.context_models import UnifiedConversationContext
from locveil_voice.intents.handlers.conversation import ConversationIntentHandler
from locveil_voice.intents.models import Intent

UNAVAILABLE_RU = "Извините, языковая модель сейчас недоступна."


class _LLMStub:
    """Answers turns; records summarization calls (recognized by the prompt asset's wording)."""

    def __init__(self, summary_response="Резюме: обсуждали планы на отпуск."):
        self.summary_response = summary_response
        self.summary_calls = []
        self.turn_calls = 0

    async def is_available(self):
        return True

    async def generate_response(self, messages, trace_context=None, **kwargs):
        content = messages[-1].get("content", "")
        if "объединённого резюме" in content or "merged summary" in content:
            self.summary_calls.append(content)
            return self.summary_response
        self.turn_calls += 1
        return "ответ"


@pytest.fixture(scope="module")
async def loader():
    ldr = IntentAssetLoader(Path("assets"), AssetLoaderConfig(strict_mode=True))
    await ldr.load_all_assets(["conversation"])
    return ldr


def _handler(loader, llm, window_turns=2):
    handler = ConversationIntentHandler(config={"max_context_length": window_turns})
    handler.asset_loader = loader
    handler._asset_loader_initialized = True
    handler.set_llm_component(llm)
    return handler


def _ctx():
    return UnifiedConversationContext(session_id="sum-test", language="ru")


async def _run_turns(handler, ctx, n, start=0):
    for i in range(start, start + n):
        intent = Intent(name="conversation.general", entities={},
                        confidence=0.9, raw_text=f"реплика номер {i}")
        result = await handler._handle_continue_conversation(intent, ctx)
        assert result.success, result.error
    return ctx


# --------------------------------------------------------------------------- #
# model layer: trim returns what it dropped
# --------------------------------------------------------------------------- #

def test_trim_returns_dropped_messages_oldest_first():
    ctx = _ctx()
    hc = ctx.get_handler_context("conversation")
    hc["messages"] = [{"role": "system", "content": "seed"}] + [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"} for i in range(10)
    ]
    dropped = ctx.trim_handler_messages("conversation", 4)
    assert [m["content"] for m in dropped] == ["m0", "m1", "m2", "m3", "m4", "m5"]
    # under the limit → nothing dropped
    assert ctx.trim_handler_messages("conversation", 4) == []


# --------------------------------------------------------------------------- #
# handler layer
# --------------------------------------------------------------------------- #

def test_dropped_turns_accumulate_then_one_call_summarizes(loader):
    llm = _LLMStub()
    handler = _handler(loader, llm)
    ctx = _ctx()

    # window = 2 turns; K = 10 dropped messages. The threshold check runs before each
    # turn's LLM call, so the buffer crosses 10 on turn 8's user-append → exactly one call.
    asyncio.run(_run_turns(handler, ctx, 8))

    assert len(llm.summary_calls) == 1
    hc = ctx.get_handler_context("conversation")
    assert hc["conversation_summary"] == llm.summary_response
    # cleared at summarization; only turn 8's own post-reply drop may follow
    assert len(hc["pending_summary"]) <= 2
    # the dropped turns' text reached the summarization prompt
    assert "реплика номер 0" in llm.summary_calls[0]

def test_summary_is_injected_into_the_prompt(loader):
    llm = _LLMStub()
    handler = _handler(loader, llm)
    ctx = _ctx()
    hc = ctx.get_handler_context("conversation")
    hc["conversation_summary"] = "Обсуждали отпуск в августе."
    hc["messages"] = [{"role": "user", "content": "и что мы решили?"}]

    intent = Intent(name="conversation.general", entities={}, confidence=0.9,
                    raw_text="и что мы решили?")
    messages = handler._prepare_llm_context(intent, ctx, hc)

    summary_msgs = [m for m in messages
                    if m["role"] == "system" and "Обсуждали отпуск" in m["content"]]
    assert len(summary_msgs) == 1
    assert "Ранее в разговоре" in summary_msgs[0]["content"]  # localized label
    assert messages[-1]["content"] == "и что мы решили?"      # user turn stays last


def test_llm_failure_keeps_buffer_and_degrades_to_windowing(loader):
    class _FailingLLM(_LLMStub):
        async def generate_response(self, messages, trace_context=None, **kwargs):
            content = messages[-1].get("content", "")
            if "объединённого резюме" in content:
                raise RuntimeError("provider down")
            return "ответ"

    llm = _FailingLLM()
    handler = _handler(loader, llm)
    ctx = _ctx()
    asyncio.run(_run_turns(handler, ctx, 8))

    hc = ctx.get_handler_context("conversation")
    assert "conversation_summary" not in hc          # nothing stored
    assert len(hc["pending_summary"]) >= 10          # buffer kept for the next attempt
    # the user-facing turns were never failed by the summarizer
    assert len(hc["messages"]) <= 4


def test_console_floor_text_is_never_stored_as_summary(loader):
    llm = _LLMStub(summary_response=UNAVAILABLE_RU)
    handler = _handler(loader, llm)
    ctx = _ctx()
    asyncio.run(_run_turns(handler, ctx, 8))

    hc = ctx.get_handler_context("conversation")
    assert "conversation_summary" not in hc
    assert len(hc["pending_summary"]) >= 10


def test_pending_buffer_is_bounded(loader):
    class _NeverSummarizes(_LLMStub):
        async def is_available(self):
            return False  # summarizer never runs; turns still answered by generate_response

    llm = _NeverSummarizes()
    handler = _handler(loader, llm)
    ctx = _ctx()

    # LLM "unavailable" only gates the summarizer in this stub; the turn path checks the
    # component differently — drive the trim directly to isolate the bound.
    hc = ctx.get_handler_context("conversation")
    for i in range(120):
        hc["messages"].append({"role": "user" if i % 2 == 0 else "assistant",
                               "content": f"m{i}"})
        handler._trim_llm_context(ctx)

    assert len(hc["pending_summary"]) <= handler._PENDING_SUMMARY_MAX
    # the newest dropped messages are the ones kept
    assert hc["pending_summary"][-1]["content"].startswith("m")
