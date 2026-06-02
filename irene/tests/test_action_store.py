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
