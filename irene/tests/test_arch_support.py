"""Provider architecture-support taxonomy (ARCH-24 T3).

torch / standalone-onnxruntime / pymicro providers can't run on armv7 (no wheel); they must declare
`get_supported_architectures()` without 'armv7l' so the T3 build gate can fail an armv7 image that
enables them. The sherpa-onnx + pure-python providers keep the all-arch default.
"""

import importlib

import pytest

from irene.core.metadata import EntryPointMetadata


def _cls(modpath, name):
    return getattr(importlib.import_module(modpath), name)


def test_base_default_supports_all_three_archs():
    assert EntryPointMetadata.get_supported_architectures() == ["x86_64", "aarch64", "armv7l"]


ARMV7_EXCLUDED = [
    ("irene.providers.tts.silero_v3", "SileroV3TTSProvider"),
    ("irene.providers.tts.silero_v4", "SileroV4TTSProvider"),
    ("irene.providers.tts.vosk", "VoskTTSProvider"),
    ("irene.providers.tts.piper_ruaccent", "PiperRuAccentTTSProvider"),
    ("irene.providers.asr.whisper", "WhisperASRProvider"),
    ("irene.providers.voice_trigger.openwakeword", "OpenWakeWordProvider"),
    ("irene.providers.voice_trigger.microwakeword", "MicroWakeWordProvider"),
    ("irene.providers.vad.microvad", "MicroVADProvider"),
]

ARMV7_CAPABLE = [
    ("irene.providers.asr.sherpa_onnx", "SherpaOnnxASRProvider"),
    ("irene.providers.tts.piper", "PiperTTSProvider"),
    ("irene.providers.tts.console", "ConsoleTTSProvider"),
    ("irene.providers.vad.energy", "EnergyVADProvider"),
]


@pytest.mark.parametrize("modpath,name", ARMV7_EXCLUDED)
def test_armv7_incapable_providers_exclude_armv7l(modpath, name):
    archs = _cls(modpath, name).get_supported_architectures()
    assert "armv7l" not in archs
    assert set(archs) == {"x86_64", "aarch64"}


@pytest.mark.parametrize("modpath,name", ARMV7_CAPABLE)
def test_armv7_capable_providers_keep_armv7l(modpath, name):
    assert "armv7l" in _cls(modpath, name).get_supported_architectures()
