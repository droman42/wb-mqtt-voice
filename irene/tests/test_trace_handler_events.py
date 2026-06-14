"""
ARCH-19 slice 4 — handler `trace_event()` call-sites (D-5).

The trace_event mechanism itself is covered in test_trace_envelope; here we verify the
HANDLER wiring: a key step records a handler_event when a trace is active, nothing when
not, and the instrumented modules keep referencing trace_event (regression guard).
"""

import asyncio
import inspect
import unittest
from types import SimpleNamespace

from ..core.trace_context import TraceContext, trace_scope, get_current_trace
from ..intents.handlers.timer import TimerIntentHandler


class _Ctx:
    """Minimal UnifiedConversationContext stand-in for the timer-cancel path."""
    def __init__(self):
        self.active_actions = {"timer_1": {"domain": "timers"}}
        self.language = "ru"
        self.cancelled = []

    def cancel_action(self, domain):
        self.cancelled.append(domain)


def _timer_handler():
    # Bypass the heavy __init__ (donations/templates); stub the one template lookup the path uses.
    h = object.__new__(TimerIntentHandler)
    h._get_template = lambda *a, **k: "ok"
    return h


class TestTimerHandlerEvents(unittest.TestCase):
    def test_cancel_records_handler_event(self):
        h, ctx = _timer_handler(), _Ctx()
        intent = SimpleNamespace(entities={})
        trace = TraceContext(enabled=True)
        with trace_scope(trace):
            asyncio.run(h._handle_cancel_timer(intent, ctx))
        self.assertEqual(ctx.cancelled, ["timers"])
        labels = [(e["handler"], e["label"]) for e in trace.handler_events]
        self.assertIn(("timer", "timer_cancel"), labels)
        ev = next(e for e in trace.handler_events if e["label"] == "timer_cancel")
        self.assertEqual(ev["data"]["count"], 1)

    def test_no_event_without_active_trace(self):
        h, ctx = _timer_handler(), _Ctx()
        intent = SimpleNamespace(entities={})
        # No trace_scope → trace_event is a no-op; the handler still works.
        self.assertIsNone(get_current_trace())
        asyncio.run(h._handle_cancel_timer(intent, ctx))
        self.assertEqual(ctx.cancelled, ["timers"])

    def test_disabled_trace_records_nothing(self):
        h, ctx = _timer_handler(), _Ctx()
        intent = SimpleNamespace(entities={})
        trace = TraceContext(enabled=False)
        with trace_scope(trace):
            asyncio.run(h._handle_cancel_timer(intent, ctx))
        self.assertEqual(trace.handler_events, [])


class TestInstrumentationPresent(unittest.TestCase):
    """Guard against silent removal of the call-sites during future edits."""

    def test_modules_call_trace_event(self):
        from ..intents.handlers import (
            timer, conversation, text_enhancement_handler, translation_handler,
        )
        for mod, min_calls in [
            (timer, 3),                      # set, cancel, stop
            (conversation, 2),               # reference, conversation
            (text_enhancement_handler, 3),   # enhance, improve, correct
            (translation_handler, 2),        # translate_text, translate_specific
        ]:
            src = inspect.getsource(mod)
            self.assertGreaterEqual(
                src.count("trace_event("), min_calls + 0,  # +import line not counted (no parens)
                f"{mod.__name__} lost trace_event call-sites")


if __name__ == "__main__":
    unittest.main()
