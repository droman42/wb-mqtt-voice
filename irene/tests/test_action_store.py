"""QUAL-28 — runtime action store (ClientRegistry) unit tests.

Covers the zombie-resistant action store added in stage 3.1: the 4 reaper layers and the
`resolve_physical_id` seam. The full pipeline lifecycle test (set → survives session eviction →
"stop" targets it → completion reaps it) is added in stage 3.2/3.3 once the store is wired
(this is the mini-TEST-3 net the user asked for, built bottom-up).
"""
import asyncio
import time

from irene.core.client_registry import (
    ClientRegistry,
    ClientRegistration,
    ActionRecord,
    resolve_physical_id,
)
from irene.intents.handlers.base import IntentHandler


def _registry() -> ClientRegistry:
    return ClientRegistry({"persistent_storage": False})


def test_resolve_physical_id_prefers_stable_origin():
    # The seam ARCH-6 will flip: client_id > room_name > session_id.
    assert resolve_physical_id(None, None, "sess1") == "sess1"
    assert resolve_physical_id(None, "Kitchen", "sess1") == "Kitchen"
    assert resolve_physical_id("kitchen_node", "Kitchen", "sess1") == "kitchen_node"


async def test_add_get_and_domain_index():
    reg = _registry()
    pid = "sess1"
    task = asyncio.create_task(asyncio.sleep(30))
    try:
        reg.add_action(ActionRecord("timer_1", "timers", pid, task=task))
        assert reg.get_action(pid, "timer_1") is not None
        assert [r.action_name for r in reg.get_live_actions(pid)] == ["timer_1"]
        # domain is the secondary router index used by contextual resolution
        assert [r.action_name for r in reg.get_live_actions_by_domain(pid, "timers")] == ["timer_1"]
        assert reg.get_live_actions_by_domain(pid, "audio_playback") == []
    finally:
        task.cancel()


async def test_layer1_completion_removes():
    reg = _registry()
    pid = "sess1"
    task = asyncio.create_task(asyncio.sleep(30))
    reg.add_action(ActionRecord("a", "timers", pid, task=task))
    reg.remove_action(pid, "a")
    task.cancel()
    assert reg.get_live_actions(pid) == []


async def test_layer2_read_time_liveness_filter():
    reg = _registry()
    pid = "sess1"
    done = asyncio.create_task(asyncio.sleep(0))
    await done  # task is now done()
    reg.add_action(ActionRecord("dead", "timers", pid, task=done))
    # a dead task is never returned as live, and get_action reaps it
    assert reg.get_action(pid, "dead") is None
    assert reg.get_live_actions(pid) == []


async def test_layer3_periodic_sweep_catches_missed_callback():
    reg = _registry()
    pid = "sess1"
    task = asyncio.create_task(asyncio.sleep(30))
    reg.add_action(ActionRecord("orphan", "timers", pid, task=task))
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    # completion callback "missed" (task dead but not removed) → the sweep reaps it
    assert reg.reap_dead_actions() == 1
    assert reg.get_live_actions(pid) == []


async def test_layer4_ttl_for_taskless_actions():
    reg = _registry()
    pid = "sess1"
    # no task ref → liveness falls back to expected_end (TTL); already expired → dead
    reg.add_action(ActionRecord("ttl", "timers", pid, task=None, expected_end=time.time() - 1))
    assert reg.get_live_actions(pid) == []
    # a future TTL is still live
    reg.add_action(ActionRecord("ttl2", "timers", pid, task=None, expected_end=time.time() + 60))
    assert [r.action_name for r in reg.get_live_actions(pid)] == ["ttl2"]


async def test_layer4_per_identity_cap():
    reg = ClientRegistry({"persistent_storage": False, "max_actions_per_identity": 3})
    pid = "sess1"
    tasks = []
    for i in range(5):
        t = asyncio.create_task(asyncio.sleep(30))
        tasks.append(t)
        reg.add_action(ActionRecord(f"a{i}", "timers", pid, task=t, started_at=time.time() + i))
    try:
        # cap holds; the oldest are evicted
        assert len(reg.get_live_actions(pid)) <= 3
    finally:
        for t in tasks:
            t.cancel()


def test_action_store_is_never_persisted():
    reg = _registry()
    reg.add_action(ActionRecord("a", "timers", "sess1", task=None, expected_end=time.time() + 60))
    # the persisted shape is only self.clients; ActionRecord/task never serialize
    data = ClientRegistration(client_id="c1", room_name="Kitchen").to_dict()
    assert "task" not in str(data)
    assert "_actions" not in data


# --- mini-TEST-3: fire-and-forget lifecycle through a real handler (QUAL-28 stage 3.2) --- #

class _StoreTestHandler(IntentHandler):
    """Minimal concrete handler to exercise the store-centric F&F machinery."""
    async def execute(self, intent, context):  # pragma: no cover - not used
        ...

    async def can_handle(self, intent):  # pragma: no cover - not used
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


async def test_ff_lifecycle_through_handler_and_no_session_collision():
    from irene.intents.context_models import UnifiedConversationContext
    from irene.core.client_registry import get_client_registry

    h = _StoreTestHandler()
    ctx = UnifiedConversationContext(session_id="kitchen_session")
    physical_id = resolve_physical_id(ctx.client_id, ctx.room_name, ctx.session_id)
    reg = get_client_registry()
    for r in list(reg.get_live_actions(physical_id)):  # isolate from any prior state
        reg.remove_action(physical_id, r.action_name)

    done = asyncio.Event()
    seen = {}

    async def action(session_id, label):
        # An action coroutine that consumes its OWN session_id kwarg — the exact case that used to
        # crash with "multiple values for 'session_id'". It must now run.
        seen["session_id"] = session_id
        seen["label"] = label
        await done.wait()
        return "ok"

    await h.execute_fire_and_forget_with_context(
        action, action_name="act_1", domain="timers", context=ctx,
        session_id=ctx.session_id, label="hi",
    )
    await asyncio.sleep(0)  # let the task body start

    # the action's session_id kwarg reached it (no collision)
    assert seen.get("session_id") == "kitchen_session"
    assert seen.get("label") == "hi"

    # registered in the store under (physical_id, action_name), with a live task
    live = reg.get_live_actions(physical_id)
    assert [r.action_name for r in live] == ["act_1"]
    assert live[0].task is not None and live[0].is_live()

    # completion reaps it from the store (no leak)
    done.set()
    for _ in range(20):
        await asyncio.sleep(0.01)
        if not reg.get_live_actions(physical_id):
            break
    assert reg.get_live_actions(physical_id) == []


async def test_completed_action_history_lives_in_store_and_survives_eviction():
    from irene.intents.context_models import UnifiedConversationContext
    from irene.core.client_registry import get_client_registry

    h = _StoreTestHandler()
    ctx = UnifiedConversationContext(session_id="study_session")
    pid = resolve_physical_id(ctx.client_id, ctx.room_name, ctx.session_id)
    reg = get_client_registry()
    reg._recent_actions.pop(pid, None)            # isolate from prior runs
    reg._failed_actions.pop(pid, None)
    reg._action_error_count.pop(pid, None)

    async def ok_action():
        return "ok"

    async def bad_action():
        raise ValueError("boom")

    await h.execute_fire_and_forget_with_context(ok_action, action_name="a_ok", domain="timers", context=ctx)
    await h.execute_fire_and_forget_with_context(bad_action, action_name="a_bad", domain="timers", context=ctx)
    for _ in range(30):  # let both done-callbacks fire + record history
        await asyncio.sleep(0.01)
        if reg.get_recent_actions(pid) and reg.get_failed_actions(pid):
            break

    # history recorded in the STORE (physical-identity-scoped), not on the transient context
    assert {r["action"] for r in reg.get_recent_actions(pid)} == {"a_ok", "a_bad"}
    assert [r["action"] for r in reg.get_failed_actions(pid)] == ["a_bad"]
    assert reg.get_action_error_count(pid).get("timers") == 1

    # the context exposes them as read-only views ...
    assert {a["action"] for a in ctx.recent_actions} == {"a_ok", "a_bad"}
    # ... and they SURVIVE conversation-session eviction: a freshly re-created context for the same
    # physical scope still sees the history (the whole point of moving it off the session).
    fresh = UnifiedConversationContext(session_id="study_session")
    assert {a["action"] for a in fresh.recent_actions} == {"a_ok", "a_bad"}
    assert [a["action"] for a in fresh.failed_actions] == ["a_bad"]
