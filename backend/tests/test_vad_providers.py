"""ARCH-18 PR-2 — the VAD provider family + segmenter discovery (replaces the if-else).

VAD engines are now `locveil_voice.providers.vad` providers, discovered via entry-points and selected by
`[vad] default_provider`. These tests lock discovery, the energy provider's behavior, and the segmenter's
build/fallback path.
"""
import pytest

from locveil_voice.utils.loader import dynamic_loader
from locveil_voice.providers.vad.energy import EnergyVADProvider
from locveil_voice.config.models import VADConfig
from locveil_voice.intents.models import AudioData
from locveil_voice.workflows.audio_processor import VoiceSegmenter


def _frame(pcm: bytes = b"\x00\x00" * 320) -> AudioData:
    return AudioData(data=pcm, timestamp=0.0, sample_rate=16000, channels=1)


def test_all_three_providers_discoverable():
    classes = dynamic_loader.discover_providers("locveil_voice.providers.vad", ["energy", "silero", "microvad"])
    assert {"energy", "silero", "microvad"} <= set(classes)


def test_energy_provider_processes_and_reports_latency():
    p = EnergyVADProvider({"energy_threshold": 0.01, "voice_frames_required": 2})
    r = p.process_frame(_frame())
    assert r.is_voice is False                       # silence
    assert p.get_provider_name() == "energy"
    assert p.detection_latency_ms(20.0) == 40         # ARCH-18 PR-5: 2 frames × the real frame_ms (20)
    assert p.calibrate([_frame()]) in (True, False)  # energy supports calibration (no raise)
    p.threshold = 0.2                                 # delegated to the engine
    assert p.threshold == 0.2


def test_segmenter_builds_energy_by_default():
    seg = VoiceSegmenter(VADConfig(default_provider="energy"))
    assert seg.vad_engine.get_provider_name() == "energy"


def test_segmenter_falls_back_to_energy_on_unknown_provider():
    # ARCH-18: an unknown default_provider is config-valid (no enum validator) and resolves to energy.
    seg = VoiceSegmenter(VADConfig(default_provider="does_not_exist"))
    assert seg.vad_engine.get_provider_name() == "energy"
