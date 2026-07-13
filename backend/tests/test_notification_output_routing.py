"""ARCH-15 PR-4 — F&F notifications re-routed through the OutputManager, addressed by identity.

NotificationService is demoted to a producer: when an OutputManager is wired it owns delivery
(addressed by the action's channel/identity), with drop+log when the identity has no attached
output (D-3). Without an OutputManager the legacy LOG path still works (back-compat).
"""

import pytest

from locveil_voice.core.notifications import (
    DeliveryMethod,
    NotificationMessage,
    NotificationPriority,
    NotificationService,
)
from locveil_voice.outputs.console import ConsoleOutput
from locveil_voice.outputs.manager import OutputManager


async def _service_with_console(sink, origin="cli"):
    om = OutputManager()
    await om.add_output("console", ConsoleOutput(sink=sink, origin=origin))
    svc = NotificationService()
    svc.set_output_manager(om)
    return svc


async def test_completion_delivered_to_origin_channel():
    captured = []
    svc = await _service_with_console(captured.append, origin="cli")

    note = NotificationMessage(message="таймер сработал", source="cli",
                               session_id="s1", physical_id="s1")
    await svc._deliver_notification(note)

    assert captured == ["📝 таймер сработал"]


async def test_no_output_for_identity_does_not_reach_wrong_channel():
    captured = []
    svc = await _service_with_console(captured.append, origin="cli")

    # Originating channel is "ws" — no ws output attached. The OutputManager delivers nothing, so
    # NotificationService falls back to legacy methods (PR-5 migration fallback) — but crucially it
    # never mis-delivers to the cli console. Must not raise; the cli console stays empty.
    note = NotificationMessage(message="done", source="ws", session_id="s1", physical_id="s1")
    await svc._deliver_notification(note)

    assert captured == []  # never the wrong channel; completion stays in action-store history


async def test_high_priority_requests_speech_modality_degrades_to_text():
    """A HIGH-priority completion wants SPEECH; a TEXT-only console degrades it (§3.1) and still delivers."""
    captured = []
    svc = await _service_with_console(captured.append, origin="cli")

    note = NotificationMessage(message="сбой", source="cli", session_id="s1",
                               priority=NotificationPriority.HIGH)
    await svc._deliver_notification(note)

    assert captured == ["📝 сбой"]


async def test_legacy_log_path_without_output_manager():
    svc = NotificationService()  # no OutputManager wired
    svc._delivery_handlers[DeliveryMethod.LOG] = svc._deliver_via_log  # as initialize() would

    note = NotificationMessage(message="x", delivery_methods=[DeliveryMethod.LOG])
    # Must not raise; legacy LOG delivery still works.
    await svc._deliver_notification(note)
    assert note.delivery_status.get(DeliveryMethod.LOG) is True


async def test_send_completion_threads_addressing_onto_message():
    """send_action_completion_notification carries source/physical_id/room onto the queued message."""
    svc = NotificationService()  # context_manager None → defaults to LOG, still builds + queues

    await svc.send_action_completion_notification(
        session_id="s1", domain="timers", action_name="timer_42", duration=300.0, success=True,
        source="cli", physical_id="kitchen", room_name="Кухня")

    queued = await svc._notification_queue.get()
    assert queued.source == "cli"
    assert queued.physical_id == "kitchen"
    assert queued.room_name == "Кухня"
