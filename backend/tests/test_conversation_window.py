"""BUG-18 — the LLM conversation store must respect ``max_context_length``.

The leak: ``handler_contexts["conversation"]["messages"]`` (and domain-thread message
lists) appended per turn with no trim anywhere — ``max_context_length`` was read from
config and never applied — so a stable room-scoped session grew its LLM history (and
its per-turn prompt) for days. Fixed with a rolling window: last N turns (2 messages
per turn), the seed system prompt pinned; same bound applied to domain threads.
"""

import asyncio

from locveil_voice.intents.context_models import UnifiedConversationContext
from locveil_voice.intents.handlers.conversation import ConversationIntentHandler
from locveil_voice.intents.models import Intent


# --------------------------------------------------------------------------- #
# model layer: trim_handler_messages / add_to_thread windowing
# --------------------------------------------------------------------------- #

def _ctx() -> UnifiedConversationContext:
    return UnifiedConversationContext(session_id="win-test")


def test_trim_pins_seed_system_prompt_and_windows_the_tail():
    ctx = _ctx()
    hc = ctx.get_handler_context("conversation")
    hc["messages"] = [{"role": "system", "content": "seed"}] + [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"} for i in range(10)
    ]

    ctx.trim_handler_messages("conversation", 4)

    messages = ctx.get_handler_context("conversation")["messages"]
    assert messages[0] == {"role": "system", "content": "seed"}  # pinned, not counted
    assert [m["content"] for m in messages[1:]] == ["m6", "m7", "m8", "m9"]


def test_trim_is_noop_under_the_limit_and_without_seed():
    ctx = _ctx()
    hc = ctx.get_handler_context("conversation")
    hc["messages"] = [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]

    ctx.trim_handler_messages("conversation", 4)
    assert len(ctx.get_handler_context("conversation")["messages"]) == 2

    ctx.trim_handler_messages("conversation", 1)
    assert [m["content"] for m in ctx.get_handler_context("conversation")["messages"]] == ["b"]


def test_add_to_thread_windows_when_max_given():
    ctx = _ctx()
    for i in range(10):
        ctx.add_to_thread("timers", "user", f"t{i}", max_messages=4)

    messages = ctx.get_thread_messages("timers")
    assert [m["content"] for m in messages] == ["t6", "t7", "t8", "t9"]

    # without max the legacy behavior (caller-managed) is preserved
    for i in range(3):
        ctx.add_to_thread("music", "user", f"u{i}")
    assert len(ctx.get_thread_messages("music")) == 3


# --------------------------------------------------------------------------- #
# handler layer: many turns stay bounded end-to-end
# --------------------------------------------------------------------------- #

class _LLMStub:
    def __init__(self):
        self.prompt_sizes = []

    async def is_available(self):
        return False  # keeps the QUAL-60 summarizer out — this test is the pure BUG-18 window

    async def generate_response(self, messages, trace_context=None, **kwargs):
        self.prompt_sizes.append(len(messages))
        return "ответ"


def test_many_turns_keep_messages_and_prompt_bounded():
    handler = ConversationIntentHandler(config={"max_context_length": 2})
    llm = _LLMStub()
    handler.set_llm_component(llm)
    ctx = _ctx()

    for i in range(8):
        intent = Intent(name="conversation.general", entities={},
                        confidence=0.9, raw_text=f"вопрос номер {i}")
        result = asyncio.run(handler._handle_continue_conversation(intent, ctx))
        assert result.success, result.error

    messages = ctx.get_handler_context("conversation")["messages"]
    # window = 2 turns × 2 messages; no seed system prompt in this flow
    assert len(messages) <= 4
    assert messages[-1] == {"role": "assistant", "content": "ответ"}
    assert messages[-2]["content"] == "вопрос номер 7"
    # the per-turn LLM prompt stops growing once the window is full
    assert max(llm.prompt_sizes) <= 4 + 2  # window + injected context messages headroom
    assert llm.prompt_sizes[-1] == llm.prompt_sizes[-2]
