"""BUG-16 — session-metrics lifecycle: the process-lifetime MetricsCollector must not retain
an entry for every session ever seen.

The leak: ``record_session_start`` stored the session action under the QUAL-9 key shape
``"session_{sid}:session"`` plus a per-session DomainMetrics entry, but ``record_session_end``
checked ``domain in _active_actions`` with the bare domain — never a match — so neither was
ever removed, and REST/WS session minting made that per-request permanent growth.
"""

from irene.core.metrics import MetricsCollector


def test_session_end_completes_action_and_drops_domain_entry():
    mc = MetricsCollector()
    mc.record_session_start("s1")
    assert "session_s1:session" in mc._active_actions
    assert "session_s1" in mc._domain_metrics

    mc.record_session_end("s1")

    # the leak: both of these used to survive forever
    assert "session_s1:session" not in mc._active_actions
    assert "session_s1" not in mc._domain_metrics
    assert mc._system_metrics["current_concurrent_actions"] == 0
    # ended session leaves only a compact summary in the bounded ring
    assert [s["session_id"] for s in mc._recent_sessions] == ["s1"]


def test_session_end_is_idempotent():
    mc = MetricsCollector()
    mc.record_session_start("s1")
    mc.record_session_end("s1")
    mc.record_session_end("s1")  # double-end (lazy path + sweep) must not double-record
    assert len(mc._recent_sessions) == 1


def test_collector_footprint_is_bounded_across_many_sessions():
    mc = MetricsCollector()
    for i in range(150):
        mc.record_session_start(f"s{i}")
        mc.record_session_end(f"s{i}")

    assert len(mc._recent_sessions) == 100  # ring, not one entry per session ever
    assert not mc._active_actions
    assert not any(d.startswith("session_") for d in mc._domain_metrics)

    analytics = mc.get_session_analytics()
    assert analytics["overview"]["total_sessions"] == 150  # lifetime scalar survives the ring
    assert analytics["overview"]["active_sessions"] == 0
    assert analytics["overview"]["average_session_duration"] >= 0.0


def test_analytics_active_check_uses_real_action_key():
    mc = MetricsCollector()
    mc.record_session_start("live")
    analytics = mc.get_session_analytics()
    # the old bare-domain check reported 0 active sessions even while one was live
    assert analytics["overview"]["active_sessions"] == 1
    assert analytics["active_sessions"][0]["session_id"] == "live"


def test_reset_clears_session_tracking():
    mc = MetricsCollector()
    mc.record_session_start("s1")
    mc.record_session_end("s1")
    mc.reset_metrics()
    assert len(mc._recent_sessions) == 0
    assert mc.get_session_analytics()["overview"]["total_sessions"] == 0
