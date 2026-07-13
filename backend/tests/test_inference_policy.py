"""Shared InferencePolicy — the sherpa-onnx thread budget (ARCH-24 T5).

Used by the sherpa ASR, VAD and Piper-TTS providers so num_threads is set consistently.
"""

from locveil_voice.utils.inference_policy import InferencePolicy


def test_explicit_override_wins():
    assert InferencePolicy.for_platform(8).num_threads == 8
    assert InferencePolicy.for_platform(3).num_threads == 3


def test_armv7_is_conservative(monkeypatch):
    monkeypatch.setattr("locveil_voice.utils.inference_policy.platform.machine", lambda: "armv7l")
    assert InferencePolicy.for_platform().num_threads == 2  # headroom for the co-tenant bridge
    assert InferencePolicy.for_platform(override=4).num_threads == 4  # override still wins


def test_64bit_uses_up_to_four(monkeypatch):
    monkeypatch.setattr("locveil_voice.utils.inference_policy.platform.machine", lambda: "x86_64")
    assert 1 <= InferencePolicy.for_platform().num_threads <= 4


def test_zero_or_none_override_falls_through():
    assert InferencePolicy.for_platform(0).num_threads >= 1
    assert InferencePolicy.for_platform(None).num_threads >= 1
    assert InferencePolicy.for_platform().provider == "cpu"
