"""Regression tests for the tracing fixes (review CR-A7, CR-A9)."""
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from irene.core.trace_context import TraceContext
from irene.core.workflow_manager import WorkflowManager, WorkflowMode


def _arun(coro):
    return asyncio.run(coro)


class TestTraceRedaction(unittest.TestCase):
    """CR-A9: redact only keys whose word-token names a secret — not substring matches."""

    def test_legit_fields_preserved(self):
        tc = object.__new__(TraceContext)
        data = {
            "session_id": "s-1", "sessionId": "s-2", "keyword": "включи",
            "matched_keys": ["a", "b"], "author": "irene", "intent_name": "timer.set",
        }
        self.assertEqual(tc._do_sanitize(data), data)  # nothing redacted

    def test_secrets_redacted_including_nested(self):
        tc = object.__new__(TraceContext)
        out = tc._do_sanitize({
            "api_key": "x", "password": "p", "access_token": "t",
            "nested": {"authorization": "Bearer z", "session_id": "keep"},
        })
        self.assertEqual(out, {
            "api_key": "[REDACTED]", "password": "[REDACTED]", "access_token": "[REDACTED]",
            "nested": {"authorization": "[REDACTED]", "session_id": "keep"},
        })


class TestTextPathTracePersistsOnError(unittest.TestCase):
    """CR-A7: process_text_input must save the trace (with an error stage) when the workflow raises,
    and re-raise (callers convert it to HTTP 500)."""

    def _manager(self, failing_workflow, trace):
        wm = object.__new__(WorkflowManager)
        wm.active_workflow = failing_workflow
        wm.active_mode = WorkflowMode.UNIFIED
        wm.workflows = {"unified_voice_assistant": failing_workflow}
        wm._maybe_create_trace = lambda tc: trace
        wm._replay_request = lambda ctx: {}
        wm._publish_pipeline_event = AsyncMock()
        wm._save_trace_if_enabled = MagicMock()
        return wm

    def test_trace_saved_and_reraised_on_workflow_error(self):
        boom = RuntimeError("nlu blew up")
        wf = SimpleNamespace(process_text_input=AsyncMock(side_effect=boom))
        trace = MagicMock()
        trace.enabled = True
        wm = self._manager(wf, trace)

        with self.assertRaises(RuntimeError):
            _arun(wm.process_text_input(text="привет", session_id="sess-1"))

        # The trace was persisted on the error path (was lost before CR-A7) ...
        wm._save_trace_if_enabled.assert_called_once_with(trace)
        # ... carrying an error stage.
        stages = [c.kwargs.get("stage_name") for c in trace.record_stage.call_args_list]
        self.assertIn("workflow_manager_text_error", stages)


if __name__ == "__main__":
    unittest.main()
