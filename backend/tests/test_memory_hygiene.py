"""QUAL-58 — memory-hygiene sweep regressions (arch_memory_review_2026-07-02.md M4–M8).

M4: resampling cache byte budget + oversized-entry bypass.
M5: per-identity completed-action history TTL prune.
M7: bounded notification queue + lazy consumer start.
M8: trace-directory rotation.
(M6 — wiring the registry sweep into the ContextManager loop — is plain call-wiring in
`_cleanup_expired_contexts`; the swept functions themselves are covered here and in
test_action_store.py.)
"""

import asyncio
import time

from locveil_voice.core.client_registry import ClientRegistry
from locveil_voice.core.notifications import NotificationService, NotificationMessage, NotificationType
from locveil_voice.core.trace_context import _prune_trace_dir
from locveil_voice.utils.audio_helpers import AudioTranscoder


# --------------------------------------------------------------------------- #
# M4 — resampling cache bounds
# --------------------------------------------------------------------------- #

def test_oversized_resample_results_bypass_the_cache():
    AudioTranscoder.clear_cache()
    big = b"\x00" * (AudioTranscoder._max_entry_bytes + 1)
    AudioTranscoder._cache_store(("big",), big)
    assert AudioTranscoder.get_cache_stats()["cache_size"] == 0
    assert AudioTranscoder.get_cache_stats()["cache_bytes"] == 0


def test_cache_evicts_fifo_on_byte_budget():
    AudioTranscoder.clear_cache()
    original = AudioTranscoder._max_cache_bytes
    AudioTranscoder._max_cache_bytes = 1000
    try:
        for i in range(5):
            AudioTranscoder._cache_store((i,), b"\x00" * 400)  # 5 × 400B > 1000B budget
        stats = AudioTranscoder.get_cache_stats()
        assert stats["cache_bytes"] <= 1000
        assert stats["cache_size"] == 2  # only the 2 newest fit
        assert (4,) in AudioTranscoder._resampling_cache
        assert (0,) not in AudioTranscoder._resampling_cache
    finally:
        AudioTranscoder._max_cache_bytes = original
        AudioTranscoder.clear_cache()


def test_cache_byte_accounting_on_overwrite_and_clear():
    AudioTranscoder.clear_cache()
    AudioTranscoder._cache_store(("k",), b"\x00" * 100)
    AudioTranscoder._cache_store(("k",), b"\x00" * 50)  # overwrite must not double-count
    assert AudioTranscoder.get_cache_stats()["cache_bytes"] == 50
    AudioTranscoder.clear_cache()
    assert AudioTranscoder.get_cache_stats()["cache_bytes"] == 0


# --------------------------------------------------------------------------- #
# M5 — identity-history TTL prune
# --------------------------------------------------------------------------- #

def _seed_history(registry, pid, completed_at):
    registry._recent_actions[pid] = [{"action": "t", "domain": "timers",
                                      "completed_at": completed_at, "success": False}]
    registry._failed_actions[pid] = list(registry._recent_actions[pid])
    registry._action_error_count[pid] = {"timers": 1}


def test_prune_stale_history_drops_old_identities_keeps_fresh():
    registry = ClientRegistry(config={"persistent_storage": False})
    _seed_history(registry, "dead-session", time.time() - 7200)
    _seed_history(registry, "live-session", time.time() - 60)

    pruned = registry.prune_stale_history(max_age_seconds=3600)

    assert pruned == 1
    for store in (registry._recent_actions, registry._failed_actions, registry._action_error_count):
        assert "dead-session" not in store
        assert "live-session" in store


# --------------------------------------------------------------------------- #
# M7 — notification queue bounds + lazy consumer
# --------------------------------------------------------------------------- #

def _note(title="t"):
    return NotificationMessage(type=NotificationType.SYSTEM_STATUS, title=title,
                               message="m", session_id="s")


def test_send_notification_lazy_starts_the_consumer():
    async def scenario():
        service = NotificationService()  # the getter-minted shape: never initialize()d
        assert not service._running
        ok = await service.send_notification(_note())
        assert ok and service._running and service._processing_task is not None
        await asyncio.sleep(0)  # let the consumer pick it up (no handlers -> drained)
        await service.stop()
    asyncio.run(scenario())


def test_full_queue_drops_with_warning_instead_of_growing():
    async def scenario():
        service = NotificationService()
        service._running = True  # pretend a (stalled) consumer exists; don't start it
        service._notification_queue = asyncio.Queue(maxsize=1)
        assert await service.send_notification(_note("first")) is True
        assert await service.send_notification(_note("overflow")) is False
        assert service._notification_queue.qsize() == 1
        assert service._metrics["failed_deliveries"] == 1
    asyncio.run(scenario())


# --------------------------------------------------------------------------- #
# M8 — trace rotation
# --------------------------------------------------------------------------- #

def test_prune_trace_dir_keeps_newest(tmp_path):
    for i in range(7):
        f = tmp_path / f"trace_{i}.json"
        f.write_text("{}")
        ts = time.time() - (100 - i)
        import os
        os.utime(f, (ts, ts))
    (tmp_path / "notes.txt").write_text("kept")  # non-json untouched

    _prune_trace_dir(tmp_path, max_files=3)

    remaining = sorted(f.name for f in tmp_path.glob("trace_*.json"))
    assert remaining == ["trace_4.json", "trace_5.json", "trace_6.json"]
    assert (tmp_path / "notes.txt").exists()
