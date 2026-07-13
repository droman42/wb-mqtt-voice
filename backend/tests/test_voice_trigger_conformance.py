"""ARCH-18 PR-4b — voice_trigger trusts canonical.

detect()'s only caller is the mic pipeline, which delivers canonical audio (PR-3). So detect() must hand the
audio to the wake provider unchanged — no per-frame resampling.
"""
from locveil_voice.components.voice_trigger_component import VoiceTriggerComponent
from locveil_voice.intents.models import AudioData, WakeWordResult


class _MockWakeProvider:
    def __init__(self):
        self.seen_rate = None

    async def detect_wake_word(self, audio_data):
        self.seen_rate = audio_data.sample_rate
        return WakeWordResult(detected=True, confidence=0.9, word="irene")

    def get_provider_name(self):
        return "mock"


async def test_detect_passes_canonical_audio_through_unchanged():
    comp = VoiceTriggerComponent()
    provider = _MockWakeProvider()
    comp.providers = {"mock": provider}
    comp.default_provider = "mock"
    comp.active = True

    audio = AudioData(data=b"\x00\x00" * 1600, timestamp=0.0, sample_rate=16000, channels=1)
    result = await comp.detect(audio)

    assert result.detected
    assert provider.seen_rate == 16000  # handed to the provider unchanged, no resample
