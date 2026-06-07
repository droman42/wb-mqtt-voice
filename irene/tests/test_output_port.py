"""ARCH-15 PR-2 — OutputPort contract: DeliveryResult + the §3.1 modality negotiation matrix."""

import pytest

from irene.core.interfaces.output import (
    DeliveryResult,
    OutputModality,
    negotiate,
)

T, S, D, E = (OutputModality.TEXT, OutputModality.SPEECH,
              OutputModality.DEVICE_COMMAND, OutputModality.EVENT)


def test_negotiate_carries_when_supported():
    assert negotiate(T, {T}) is T
    assert negotiate(S, {S, T}) is S
    assert negotiate(D, {D}) is D


def test_negotiate_degrades_speech_to_text():
    # SPEECH not carriable but TEXT is → degrade to TEXT.
    assert negotiate(S, {T}) is T


def test_negotiate_drops_when_no_path():
    assert negotiate(S, {D}) is None          # speech, no text, no degrade
    assert negotiate(D, {T}) is None          # device_command never degrades to text
    assert negotiate(T, set()) is None         # nothing supported


def test_delivery_result_helpers():
    ok = DeliveryResult.ok("console", T)
    assert ok.delivered and not ok.dropped and ok.modality is T

    dropped = DeliveryResult.drop("mqtt", S, detail="no audio")
    assert dropped.dropped and not dropped.delivered and dropped.detail == "no audio"


def test_delivery_result_rich_bridge_fields():
    """The bridge actuation channel returns echo + error_code (D-6)."""
    dr = DeliveryResult.ok("bridge", D, echoed_value=1, error_code=None)
    assert dr.echoed_value == 1 and dr.error_code is None
