"""Local audio/voice output adapter (ARCH-15 PR-8) — the SPEECH channel.

Wraps the TTS + audio components: `deliver()` synthesizes `result.text` to a temp WAV and plays it
on the local device. Carries SPEECH **and** TEXT (a voice device speaks everything — a TEXT result
is rendered as speech), so the §3.1 negotiation never has to drop a conversational result here.

This is the real SPEECH `OutputPort` whose existence lets PR-8 retire the PR-5a legacy-TTS fallback
in NotificationService and restore pure D-3 (drop+log when no output serves an identity).
"""

import logging
import uuid
from pathlib import Path
from typing import Optional, Set

from ..core.interfaces.output import DeliveryResult, OutputModality, OutputPort
from ..intents.models import IntentResult
from ..intents.context_models import RequestContext

logger = logging.getLogger(__name__)


class AudioSpeechOutput(OutputPort):
    """Speak a result on the local device via the TTS + audio components."""

    def __init__(self, tts_component, audio_component, *, origin: Optional[str] = None,
                 name: str = "audio", temp_dir: str = "/tmp", playback_mode: str = "file") -> None:
        self._tts = tts_component
        self._audio = audio_component
        self._origin = origin
        self._name = name
        self._temp_dir = temp_dir
        # ARCH-21: "stream" conforms to the sink and streams raw PCM (shared with the sync workflow
        # path via the TTS component); "file" plays a temp WAV. Mirrors [audio] playback_mode.
        self._playback_mode = playback_mode

    def supported_modalities(self) -> Set[OutputModality]:
        # A voice device speaks both spoken results and plain text (text → speech).
        return {OutputModality.SPEECH, OutputModality.TEXT}

    async def is_available(self) -> bool:
        return self._tts is not None and self._audio is not None

    async def deliver(self, result: IntentResult, context: RequestContext,
                      modality: OutputModality) -> DeliveryResult:
        if not (self._tts and self._audio):
            return DeliveryResult.drop(self._name, modality, detail="TTS/audio component unavailable")
        text = result.text or ""
        if not text.strip():
            return DeliveryResult.ok(self._name, OutputModality.SPEECH)  # nothing to speak
        temp_path: Optional[Path] = None
        try:
            # ARCH-21: stream mode conforms to the sink and streams raw PCM (shared path on the TTS
            # component); degrades to file when streaming is unavailable (text-only provider / no
            # negotiator). This keeps deferred F&F speech on the same path as sync replies.
            if self._playback_mode == "stream" and await self._tts.synthesize_and_stream_to(self._audio, text):
                return DeliveryResult.ok(self._name, OutputModality.SPEECH)

            temp_path = Path(self._temp_dir) / f"speech_{uuid.uuid4().hex}.wav"
            await self._tts.synthesize_to_file(text, temp_path)
            await self._audio.play_file(temp_path)
            return DeliveryResult.ok(self._name, OutputModality.SPEECH)
        except Exception as e:
            logger.error(f"AudioSpeechOutput delivery failed: {e}")
            return DeliveryResult.drop(self._name, modality, detail=str(e))
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

    def get_output_type(self) -> str:
        return self._name

    def origin_key(self) -> Optional[str]:
        return self._origin
