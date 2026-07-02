"""
TEST-3 — fire-and-forget lifecycle coverage (the handler-base machinery).

The store (ClientRegistry) + the happy launch→complete path are covered by test_action_store.py;
this file targets the UNCOVERED branches of `IntentHandler`'s F&F machinery (handlers/base.py 45%):
completion, error, cancel, launch-failure, cleanup, metrics/notification scheduling, and the
handler-level cancel_action / get_active_actions. Hermetic: a minimal concrete handler via
object.__new__, a fresh ClientRegistry per test (get_client_registry patched), asyncio.run only.
"""

import asyncio
import logging
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from irene.core.client_registry import ClientRegistry, ActionRecord
from irene.intents.handlers.base import IntentHandler


class _Handler(IntentHandler):
    async def execute(self, intent, context):  # pragma: no cover - not exercised here
        ...

    async def can_handle(self, intent):  # pragma: no cover
        return True


def _handler(*, metrics=None, notifier=None):
    """A handler with only the F&F machinery wired (skip the heavy __init__)."""
    h = object.__new__(_Handler)
    h.name = "faf_test"
    h.logger = logging.getLogger("test.faf")
    h._timeout_tasks = {}
    h._completion_tasks = set()
    h._metrics_collector = metrics
    h._notification_service = notifier
    return h


async def _settle():
    # let task done-callbacks (scheduled via loop.call_soon) run
    await asyncio.sleep(0)
    await asyncio.sleep(0)


class _RegistryPatch:
    """Context manager: a fresh ClientRegistry visible to handlers/base get_client_registry()."""
    def __enter__(self):
        self.reg = ClientRegistry({"persistent_storage": False})  # hermetic (ARCH-28 path default)
        self._p = patch("irene.intents.handlers.base.get_client_registry", return_value=self.reg)
        self._p.start()
        return self.reg

    def __exit__(self, *exc):
        self._p.stop()
        return False


class TestLifecycle(unittest.TestCase):
    def test_launch_registers_then_completion_reaps_and_records_success(self):
        async def run():
            with _RegistryPatch() as reg:
                async def action():
                    return "done"
                h = _handler()
                await h.execute_fire_and_forget_action(
                    action, action_name="a1", domain="timers", physical_id="kitchen",
                    owner_session_id="s1", timeout=0)
                rec = reg.get_action("kitchen", "a1")
                self.assertIsNotNone(rec)           # registered before the call returns
                await rec.task
                await _settle()
                self.assertIsNone(reg.get_action("kitchen", "a1"))   # reaped on completion
                recent = reg.get_recent_actions("kitchen")
                self.assertEqual(len(recent), 1)
                self.assertTrue(recent[0]["success"])
        asyncio.run(run())

    def test_error_reaps_and_records_failure(self):
        async def run():
            with _RegistryPatch() as reg:
                async def boom():
                    raise RuntimeError("boom")
                h = _handler()
                await h.execute_fire_and_forget_action(
                    boom, action_name="a2", domain="timers", physical_id="kitchen", timeout=0)
                rec = reg.get_action("kitchen", "a2")
                await asyncio.gather(rec.task, return_exceptions=True)
                await _settle()
                self.assertIsNone(reg.get_action("kitchen", "a2"))
                recent = reg.get_recent_actions("kitchen")
                self.assertFalse(recent[0]["success"])
                self.assertIn("boom", recent[0]["error"])
                self.assertEqual(len(reg.get_failed_actions("kitchen")), 1)
        asyncio.run(run())

    def test_cancel_records_cancelled(self):
        async def run():
            with _RegistryPatch() as reg:
                async def forever():
                    await asyncio.sleep(60)
                h = _handler()
                await h.execute_fire_and_forget_action(
                    forever, action_name="a3", domain="timers", physical_id="kitchen", timeout=0)
                rec = reg.get_action("kitchen", "a3")
                rec.task.cancel()
                await asyncio.gather(rec.task, return_exceptions=True)
                await _settle()
                self.assertIsNone(reg.get_action("kitchen", "a3"))
                self.assertEqual(reg.get_recent_actions("kitchen")[0]["error"], "cancelled")
        asyncio.run(run())

    def test_launch_failure_returns_failed_metadata(self):
        async def run():
            with _RegistryPatch() as reg:
                reg.add_action = lambda rec: (_ for _ in ()).throw(RuntimeError("store down"))

                async def action():
                    return None
                h = _handler()
                meta = await h.execute_fire_and_forget_action(
                    action, action_name="a4", domain="timers", physical_id="kitchen", timeout=0)
                entry = meta["active_actions"]["a4"]
                self.assertEqual(entry["status"], "failed")
                self.assertTrue(entry["failed_at_startup"])
        asyncio.run(run())

    def test_timeout_monitor_registered_then_cleaned_on_completion(self):
        async def run():
            with _RegistryPatch():
                async def quick():
                    return None
                h = _handler()
                await h.execute_fire_and_forget_action(
                    quick, action_name="a5", domain="timers", physical_id="kitchen", timeout=30)
                # a positive timeout starts a monitor keyed physical_id:action_name
                self.assertIn("kitchen:a5", h._timeout_tasks)
                await _settle()
                await _settle()
                # completion's _on_action_done pops + cancels the monitor
                self.assertNotIn("kitchen:a5", h._timeout_tasks)
        asyncio.run(run())


class TestMetricsAndNotifications(unittest.TestCase):
    def test_metrics_start_and_completion_recorded(self):
        calls = []

        class _Metrics:
            def record_action_start(self, **k): calls.append(("start", k))
            def record_action_completion(self, **k): calls.append(("done", k))

        async def run():
            with _RegistryPatch() as reg:
                async def action():
                    return None
                h = _handler(metrics=_Metrics())
                await h.execute_fire_and_forget_action(
                    action, action_name="m1", domain="timers", physical_id="kitchen", timeout=0)
                await reg.get_action("kitchen", "m1").task
                await _settle()
        asyncio.run(run())
        kinds = [c[0] for c in calls]
        self.assertEqual(kinds, ["start", "done"])
        self.assertTrue(calls[1][1]["success"])

    def test_completion_schedules_notification_when_owned(self):
        async def run():
            with _RegistryPatch():
                class _Notifier:
                    async def deliver(self, *a, **k):
                        return None
                h = _handler(notifier=_Notifier())
                done = asyncio.create_task(asyncio.sleep(0))
                await done
                rec = ActionRecord(action_name="n1", domain="timers", physical_id="kitchen",
                                   task=done, session_id="s1")

                async def _fake_notify(*a, **k):
                    return None
                with patch.object(h, "_notify_action_result", _fake_notify):
                    h._on_action_done(rec, done)
                    self.assertEqual(len(h._completion_tasks), 1)
                    await _settle()

        asyncio.run(run())

    def test_completion_no_notification_without_session(self):
        async def run():
            with _RegistryPatch():
                h = _handler(notifier=SimpleNamespace())
                done = asyncio.create_task(asyncio.sleep(0))
                await done
                rec = ActionRecord(action_name="n2", domain="timers", physical_id="kitchen",
                                   task=done, session_id=None)  # no owner → no notification
                h._on_action_done(rec, done)
                self.assertEqual(len(h._completion_tasks), 0)
        asyncio.run(run())


class TestCleanupAndHandlerHelpers(unittest.TestCase):
    def test_cleanup_timeout_tasks_cancels_and_clears(self):
        async def run():
            h = _handler()
            h._timeout_tasks = {
                "k:1": asyncio.create_task(asyncio.sleep(60)),
                "k:2": asyncio.create_task(asyncio.sleep(60)),
            }
            tasks = list(h._timeout_tasks.values())
            await h.cleanup_timeout_tasks()
            self.assertEqual(h._timeout_tasks, {})
            self.assertTrue(all(t.cancelled() for t in tasks))
        asyncio.run(run())



class TestBug19Correctness(unittest.TestCase):
    """BUG-19 — store/status correctness (QUAL-56 F2/F3)."""

    def test_false_return_is_recorded_as_failure(self):
        # The bool convention: coroutines that swallow their own errors `return False` —
        # this used to be recorded as SUCCESS.
        async def run():
            with _RegistryPatch() as reg:
                async def swallowed_failure():
                    return False
                h = _handler()
                await h.execute_fire_and_forget_action(
                    swallowed_failure, action_name="f1", domain="audio",
                    physical_id="kitchen", timeout=0)
                rec = reg.get_action("kitchen", "f1")
                await asyncio.gather(rec.task, return_exceptions=True)
                await _settle()
                recent = reg.get_recent_actions("kitchen")
                self.assertFalse(recent[0]["success"])
                self.assertIn("reported failure", recent[0]["error"])
        asyncio.run(run())

    def test_timeout_is_recorded_as_timeout_not_cancelled(self):
        async def run():
            with _RegistryPatch() as reg:
                async def slow():
                    await asyncio.sleep(30)
                completions = []
                metrics = SimpleNamespace(
                    record_action_start=lambda **kw: None,
                    record_action_completion=lambda **kw: completions.append(kw))
                h = _handler(metrics=metrics)
                await h.execute_fire_and_forget_action(
                    slow, action_name="t1", domain="timers", physical_id="kitchen",
                    timeout=0.01)
                rec = reg.get_action("kitchen", "t1")
                await asyncio.gather(rec.task, return_exceptions=True)
                await _settle()
                recent = reg.get_recent_actions("kitchen")
                self.assertEqual(recent[0]["error"], "timeout")   # was: "cancelled"
                self.assertTrue(completions[0]["timeout_occurred"])
        asyncio.run(run())

    def test_user_cancel_still_recorded_as_cancelled(self):
        async def run():
            with _RegistryPatch() as reg:
                async def slow():
                    await asyncio.sleep(30)
                h = _handler()
                await h.execute_fire_and_forget_action(
                    slow, action_name="c1", domain="timers", physical_id="kitchen", timeout=0)
                rec = reg.get_action("kitchen", "c1")
                rec.task.cancel()
                await asyncio.gather(rec.task, return_exceptions=True)
                await _settle()
                self.assertEqual(reg.get_recent_actions("kitchen")[0]["error"], "cancelled")
        asyncio.run(run())

    def test_displaced_records_callback_cannot_evict_successor(self):
        # Name collision: old record displaced from the store; when its task finishes, its
        # done-callback must NOT remove the live successor registered under the same key.
        async def run():
            with _RegistryPatch() as reg:
                async def first():
                    await asyncio.sleep(0.01)
                async def second():
                    await asyncio.sleep(30)
                h = _handler()
                await h.execute_fire_and_forget_action(
                    first, action_name="dup", domain="timers", physical_id="kitchen", timeout=0)
                old_rec = reg.get_action("kitchen", "dup")
                await h.execute_fire_and_forget_action(
                    second, action_name="dup", domain="timers", physical_id="kitchen", timeout=0)
                new_rec = reg.get_action("kitchen", "dup")
                self.assertIsNot(new_rec, old_rec)
                await asyncio.gather(old_rec.task, return_exceptions=True)
                await _settle()
                # the successor survives the displaced record's completion callback
                self.assertIs(reg.get_action("kitchen", "dup"), new_rec)
                new_rec.task.cancel()
                await asyncio.gather(new_rec.task, return_exceptions=True)
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
