"""Provider architecture-support taxonomy (ARCH-24 T3).

torch / standalone-onnxruntime / pymicro providers can't run on armv7 (no wheel); they must declare
`get_supported_architectures()` without 'armv7l' so the T3 build gate can fail an armv7 image that
enables them. The sherpa-onnx + pure-python providers keep the all-arch default.
"""

import importlib

import pytest

from locveil_voice.core.metadata import EntryPointMetadata


def _cls(modpath, name):
    return getattr(importlib.import_module(modpath), name)


def test_base_default_supports_all_three_archs():
    assert EntryPointMetadata.get_supported_architectures() == ["x86_64", "aarch64", "armv7l"]


ARMV7_EXCLUDED = [
    ("locveil_voice.providers.tts.silero_v3", "SileroV3TTSProvider"),
    ("locveil_voice.providers.tts.silero_v4", "SileroV4TTSProvider"),
    ("locveil_voice.providers.tts.vosk", "VoskTTSProvider"),
    ("locveil_voice.providers.tts.piper_ruaccent", "PiperRuAccentTTSProvider"),
    ("locveil_voice.providers.asr.whisper", "WhisperASRProvider"),
    ("locveil_voice.providers.voice_trigger.openwakeword", "OpenWakeWordProvider"),
    ("locveil_voice.providers.voice_trigger.microwakeword", "MicroWakeWordProvider"),
    ("locveil_voice.providers.vad.microvad", "MicroVADProvider"),
]

ARMV7_CAPABLE = [
    ("locveil_voice.providers.asr.sherpa_onnx", "SherpaOnnxASRProvider"),
    ("locveil_voice.providers.tts.piper", "PiperTTSProvider"),
    ("locveil_voice.providers.tts.console", "ConsoleTTSProvider"),
    ("locveil_voice.providers.vad.energy", "EnergyVADProvider"),
]


@pytest.mark.parametrize("modpath,name", ARMV7_EXCLUDED)
def test_armv7_incapable_providers_exclude_armv7l(modpath, name):
    archs = _cls(modpath, name).get_supported_architectures()
    assert "armv7l" not in archs
    assert set(archs) == {"x86_64", "aarch64"}


@pytest.mark.parametrize("modpath,name", ARMV7_CAPABLE)
def test_armv7_capable_providers_keep_armv7l(modpath, name):
    assert "armv7l" in _cls(modpath, name).get_supported_architectures()
