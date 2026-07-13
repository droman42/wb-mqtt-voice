"""
Voice Trigger Plugin Interface — wake-word detection.

Capability port (ARCH-4) that the voice-trigger component implements. Adapters
(openWakeWord / microWakeWord) implement the separate `VoiceTriggerProvider`
base in `providers/voice_trigger/base.py`.
"""

from abc import abstractmethod

from ..metadata import EntryPointMetadata
from ...utils.audio_data import AudioData, WakeWordResult


class VoiceTriggerPlugin(EntryPointMetadata):
    """Interface for voice-trigger capability: detect a wake word in audio."""

    @abstractmethod
    async def detect(self, audio_data: AudioData) -> WakeWordResult:
        """Detect whether the wake word is present in the given audio."""
        ...
