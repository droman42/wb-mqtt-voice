"""ARCH-28 — durable-action substrate (docs/design/durable_actions.md).

Covers: the atomic-JSON store port, persist-at-launch + delete-at-completion through the F&F
choke point, the startup reconciler (re-arm / fire-late / expire), the timer's rearm hook, the
undelivered-notice queue + TTL, and — the flagship — the RESTART test (persist + restore + test
ship together, per the design's anti persist-without-restore rule).
"""

import asyncio
import logging
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from irene.core.client_registry import ClientRegistry
from irene.core.durable_actions import (
    DurableActionRecord,
    GRACE_WINDOW_SECONDS,
    JsonFileDurableActionStore,
    UndeliveredNotice,
    reconcile_durable_actions,
    set_durable_action_store,
)
from irene.intents.handlers.base import IntentHandler
from irene.intents.handlers.timer import TimerIntentHandler


# --------------------------------------------------------------------------- harness

class _Handler(IntentHandler):
    async def execute(self, intent, context):  # pragma: no cover
        ...

    async def can_handle(self, intent):  # pragma: no cover
        return True


def _handler():
    h = object.__new__(_Handler)
    h.name = "durable_test"
    h.logger = logging.getLogger("test.durable")
    h._timeout_tasks = {}
    h._completion_tasks = set()
    h._metrics_collector = None
    h._notification_service = None
    return h


class _Env:
    """Fresh registry + fresh tmp-file store, both patched into handlers/base."""

    def __init__(self, tmp_path):
        self.store = JsonFileDurableActionStore(tmp_path / "durable_actions.json")

    def __enter__(self):
        self.reg = ClientRegistry({"persistent_storage": False})
        self._p = patch("irene.intents.handlers.base.get_client_registry", return_value=self.reg)
        self._p.start()
        set_durable_action_store(self.store)
        return self

    def __exit__(self, *exc):
        self._p.stop()
        set_durable_action_store(None)
        return False


def _record(name="timer_1", handler="TimerIntentHandler", deadline=None, **kw):
    return DurableActionRecord(
        action_name=name, domain="timers", handler=handler, physical_id="kitchen",
        started_at=kw.pop("started_at", time.time()), deadline=deadline,
        session_id="s1", metadata={"language": "ru", "completion_message": "чайник готов"},
        rearm={"method": "_run_timer", "params": kw.pop("params", {"duration_seconds": 600})},
        **kw)


# --------------------------------------------------------------------------- store

def test_store_roundtrip_and_delete(tmp_path):
    store = JsonFileDurableActionStore(tmp_path / "a.json")
    store.save(_record("t1"))
    store.save(_record("t2"))
    assert {r.action_name for r in store.load_all()} == {"t1", "t2"}
    store.delete("t1")
    assert {r.action_name for r in store.load_all()} == {"t2"}
    # upsert, not append
    store.save(_record("t2", params={"duration_seconds": 5}))
    assert len(store.load_all()) == 1


def test_store_survives_corrupt_file(tmp_path):
    path = tmp_path / "a.json"
    path.write_text("{not json")
    store = JsonFileDurableActionStore(path)
    assert store.load_all() == []          # never wedge on a bad file
    store.save(_record("t1"))              # and it heals on the next write
    assert len(store.load_all()) == 1


def test_undelivered_pop_matches_and_ttl_drops(tmp_path):
    store = JsonFileDurableActionStore(tmp_path / "a.json")
    store.add_undelivered(UndeliveredNotice(physical_id="kitchen", action_name="t1",
                                            domain="timers", message="готово"))
    store.add_undelivered(UndeliveredNotice(physical_id="hall", action_name="t2",
                                            domain="timers", message="другая комната"))
    store.add_undelivered(UndeliveredNotice(physical_id="kitchen", action_name="t3",
                                            domain="timers", message="просрочено",
                                            created_at=time.time() - GRACE_WINDOW_SECONDS - 10))
    drained = store.pop_undelivered(["kitchen"])
    assert [n.action_name for n in drained] == ["t1"]      # TTL-expired t3 dropped, hall kept
    assert [n.action_name for n in store.pop_undelivered(["hall"])] == ["t2"]


# --------------------------------------------------------------------------- launch/completion wiring

class TestLaunchWiring(unittest.TestCase):
    def test_durable_launch_persists_and_completion_deletes(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            async def run():
                with _Env(Path(td)) as env:
                    async def action(duration_seconds):
                        return "ok"
                    h = _handler()
                    await h.execute_fire_and_forget_action(
                        action, action_name="d1", domain="timers", physical_id="kitchen",
                        owner_session_id="s1", timeout=60, durable=True,
                        redeliver_on_reconnect=True, duration_seconds=600)
                    persisted = env.store.load_all()
                    self.assertEqual(len(persisted), 1)          # persisted at launch
                    self.assertEqual(persisted[0].rearm["params"], {"duration_seconds": 600})
                    self.assertTrue(persisted[0].redeliver)
                    rec = env.reg.get_action("kitchen", "d1")
                    self.assertTrue(rec.durable)
                    await rec.task
                    await asyncio.sleep(0); await asyncio.sleep(0)
                    self.assertEqual(env.store.load_all(), [])   # deleted at completion
            asyncio.run(run())

    def test_ephemeral_launch_never_touches_the_store(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            async def run():
                with _Env(Path(td)) as env:
                    async def action():
                        return "ok"
                    h = _handler()
                    await h.execute_fire_and_forget_action(
                        action, action_name="e1", domain="audio", physical_id="kitchen", timeout=0)
                    self.assertFalse(env.store.path.exists())
            asyncio.run(run())

    def test_durable_launch_with_unserializable_kwargs_fails_loud(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            async def run():
                with _Env(Path(td)) as env:
                    async def action(bad):
                        return "ok"
                    h = _handler()
                    meta = await h.execute_fire_and_forget_action(
                        action, action_name="d2", domain="timers", physical_id="kitchen",
                        timeout=0, durable=True, bad=object())
                    status = meta["active_actions"]["d2"]
                    self.assertEqual(status["status"], "failed")   # no silent half-launch
                    self.assertTrue(status.get("failed_at_startup"))
                    self.assertIsNone(env.reg.get_action("kitchen", "d2"))
                    self.assertFalse(env.store.path.exists())
            asyncio.run(run())


# --------------------------------------------------------------------------- reconciler (the restart test)

class _NotifyStub:
    def __init__(self):
        self.sent = []

    async def send_action_completion_notification(self, **kw):
        self.sent.append(kw)
        return True


class TestRestartRecovery(unittest.TestCase):
    def test_future_deadline_rearms_via_handler_and_deletes_old_record(self):
        """THE restart test: launch durable → 'restart' (fresh store instance over the same
        file) → reconcile → the handler re-arms and the old record is superseded."""
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            async def run():
                path = Path(td)
                with _Env(path) as env:
                    async def action(duration_seconds):
                        await asyncio.sleep(30)
                    h = _handler()
                    await h.execute_fire_and_forget_action(
                        action, action_name="t9", domain="timers", physical_id="kitchen",
                        owner_session_id="s1", timeout=600, durable=True, duration_seconds=600)
                    rec = env.reg.get_action("kitchen", "t9")
                    rec.task.cancel()  # process "dies": the task never completes...
                    # ...but suppress the done-callback's delete by making the cancel look
                    # like a crash: re-save the record the callback removed.
                    await asyncio.gather(rec.task, return_exceptions=True)
                    await asyncio.sleep(0); await asyncio.sleep(0)
                    env.store.save(_record("t9", handler="_Handler", deadline=time.time() + 595,
                                           params={"duration_seconds": 600}))

                # "restart": a NEW store instance over the same file
                store2 = JsonFileDurableActionStore(path / "durable_actions.json")
                rearmed = []

                class _RearmHandler:
                    async def rearm_durable_action(self, record):
                        rearmed.append(record)
                        return True

                stats = await reconcile_durable_actions(
                    store2, {"_Handler": _RearmHandler()}, _NotifyStub())
                self.assertEqual(stats["rearmed"], 1)
                self.assertEqual([r.action_name for r in rearmed], ["t9"])
                self.assertEqual(store2.load_all(), [])   # old record never survives reconcile
            asyncio.run(run())

    def test_missed_within_grace_fires_with_apology(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            async def run():
                store = JsonFileDurableActionStore(Path(td) / "a.json")
                store.save(_record("t1", deadline=time.time() - 60))  # missed 1 min ago
                notify = _NotifyStub()
                stats = await reconcile_durable_actions(store, {}, notify)
                self.assertEqual(stats["fired_late"], 1)
                self.assertIn("Извините", notify.sent[0]["completion_message"])
                self.assertIn("чайник готов", notify.sent[0]["completion_message"])
                self.assertEqual(store.load_all(), [])
            asyncio.run(run())

    def test_missed_beyond_grace_announces_expiry(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            async def run():
                store = JsonFileDurableActionStore(Path(td) / "a.json")
                store.save(_record("t1", deadline=time.time() - GRACE_WINDOW_SECONDS - 60))
                notify = _NotifyStub()
                stats = await reconcile_durable_actions(store, {}, notify)
                self.assertEqual(stats["expired"], 1)
                self.assertIn("истёк", notify.sent[0]["completion_message"])
                self.assertEqual(store.load_all(), [])
            asyncio.run(run())

    def test_unknown_handler_expires_instead_of_wedging(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            async def run():
                store = JsonFileDurableActionStore(Path(td) / "a.json")
                store.save(_record("t1", handler="GoneHandler", deadline=time.time() + 500))
                stats = await reconcile_durable_actions(store, {}, _NotifyStub())
                self.assertEqual(stats["expired"], 1)
                self.assertEqual(store.load_all(), [])
            asyncio.run(run())


# --------------------------------------------------------------------------- timer rearm hook

class TestTimerRearm(unittest.TestCase):
    def _timer(self):
        h = object.__new__(TimerIntentHandler)
        h.name = "timer"
        h.logger = logging.getLogger("test.timer")
        h.timer_counter = 0
        h._timeout_tasks = {}
        h._completion_tasks = set()
        h._metrics_collector = None
        h._notification_service = None
        return h

    def test_rearm_relaunches_with_remaining_time_and_bumps_counter(self):
        async def run():
            h = self._timer()
            captured = {}

            async def fake_launch(func, **kw):
                captured.update(kw)
                return {}

            h.execute_fire_and_forget_action = fake_launch
            record = _record("timer_7", started_at=time.time() - 100,
                             params={"duration_seconds": 600, "message": "чайник готов",
                                     "session_id": "s1", "timer_id": "timer_7"})
            ok = await h.rearm_durable_action(record)
            assert ok
            assert captured["action_name"] == "timer_7"          # identity reused (D-8)
            assert 495 <= captured["duration_seconds"] <= 500     # 600 - ~100 elapsed
            assert captured["durable"] is True
            assert h.timer_counter == 7                          # no post-restart name collision
        asyncio.run(run())

    def test_rearm_refuses_when_deadline_effectively_passed(self):
        async def run():
            h = self._timer()
            record = _record("timer_1", started_at=time.time() - 700,
                             params={"duration_seconds": 600})
            assert await h.rearm_durable_action(record) is False
        asyncio.run(run())
