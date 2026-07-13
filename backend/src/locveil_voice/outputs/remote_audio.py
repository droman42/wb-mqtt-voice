"""Remote audio output (ARCH-21 PR-5) — reply-to-device over a WS reply channel.

**D-4 (reply-to-device):** output is origin-addressed. A WS device's reply goes back to that **device** over a
**separate reply-channel WS** it listens on (not the input connection). Each connected device is a
`RemoteAudioOutput` whose `origin_key()` is the device's physical id, so the existing `OutputManager`
conversational origin-pairing routes a result from that device straight here — for both sync replies and
deferred fire-and-forget. The reply is synthesized to a PCM stream (ARCH-21 producer), conformed DOWN to the
**device's** declared `AudioContract`, and pushed over the channel.

This is the protocol-agnostic **server seam**: `ReplyChannel` is the only coupling point. The device-facing wire
protocol (handshake, frame format, offline policy) + the WS endpoint that constructs and registers these outputs
(`OutputManager.add_output(physical_id, output)` on connect, `remove_output` on disconnect) are finalized in the
ESP32 design session (`ws_esp32_transport.md` / QUAL-45).
"""

import logging
import time
from typing import Any, Optional, Protocol, Set

from ..core.interfaces.output import DeliveryResult, OutputModality, OutputPort
from ..intents.models import AudioData, IntentResult
from ..intents.context_models import RequestContext
from ..utils.audio_negotiation import AudioContract
from ..utils.audio_stream import collect_pcm

logger = logging.getLogger(__name__)


class ReplyChannel(Protocol):
    """A device's live reply connection: its declared output capability + a raw-PCM push.

    The WS implementation wraps a Starlette `WebSocket` (ESP32 design); tests use a fake that captures.
    """

    @property
    def contract(self) -> AudioContract: ...

    def is_connected(self) -> bool: ...

    async def send_audio(self, pcm: bytes, *, sample_rate: int, channels: int, sample_width: int) -> None: ...


class CallbackReplyChannel:
    """A `ReplyChannel` that emits the `speak_begin → PCM → speak_end` wire protocol (ARCH-22 §4.2)
    via injected async callbacks, so the transport (a WebSocket) stays in the web layer and this stays
    transport-agnostic + unit-testable.

    Args:
        contract: the device's declared output `AudioContract` (drives `to_sink`).
        send_json: async callable sending a control frame (dict) — the WS `send_json`.
        send_bytes: async callable sending a raw PCM chunk (bytes) — the WS `send_bytes`.
        chunk_bytes: PCM is sent in frame-aligned blocks of ~this size.
    """

    def __init__(self, contract: AudioContract, send_json, send_bytes, *, chunk_bytes: int = 4096) -> None:
        self._contract = contract
        self._send_json = send_json
        self._send_bytes = send_bytes
        self._chunk_bytes = chunk_bytes
        self._connected = True
        self._seq = 0

    @property
    def contract(self) -> AudioContract:
        return self._contract

    def is_connected(self) -> bool:
        return self._connected

    def disconnect(self) -> None:
        self._connected = False

    async def send_audio(self, pcm: bytes, *, sample_rate: int, channels: int, sample_width: int) -> None:
        self._seq += 1
        seq = self._seq
        await self._send_json({"type": "speak_begin", "rate": sample_rate, "channels": channels,
                               "width": sample_width * 8, "seq": seq})
        frame = max(1, channels * sample_width)
        block = max(frame, (self._chunk_bytes // frame) * frame)
        for i in range(0, len(pcm), block):
            await self._send_bytes(pcm[i:i + block])
        await self._send_json({"type": "speak_end", "seq": seq})


class RemoteAudioOutput(OutputPort):
    """Speak a result back to a specific remote device over its reply channel (D-4)."""

    def __init__(self, physical_id: str, channel: ReplyChannel, tts_component: Any, negotiator: Any,
                 *, name: Optional[str] = None) -> None:
        self._physical_id = physical_id
        self._channel = channel
        self._tts = tts_component
        self._negotiator = negotiator
        self._name = name or f"remote:{physical_id}"

    def supported_modalities(self) -> Set[OutputModality]:
        # A voice device speaks both spoken results and plain text (text → speech).
        return {OutputModality.SPEECH, OutputModality.TEXT}

    async def is_available(self) -> bool:
        return self._tts is not None and self._negotiator is not None and self._channel.is_connected()

    async def deliver(self, result: IntentResult, context: RequestContext,
                      modality: OutputModality) -> DeliveryResult:
        text = result.text or ""
        if not text.strip():
            return DeliveryResult.ok(self._name, OutputModality.SPEECH)  # nothing to speak
        if not self._channel.is_connected():
            # Reply-to-device offline. Drop for now; queue/retry policy is an ESP32-design decision.
            return DeliveryResult.drop(self._name, modality, detail="reply channel offline")
        try:
            stream = await self._tts.synthesize_to_stream(text)
            pcm = await collect_pcm(stream.frames)
            producer = AudioData(data=pcm, timestamp=time.time(), sample_rate=stream.sample_rate,
                                 channels=stream.channels, format="pcm16")
            # Conform DOWN to the DEVICE's declared contract (not the local sink).
            conformed = await self._negotiator.to_sink(producer, self._channel.contract)
            await self._channel.send_audio(conformed.data, sample_rate=conformed.sample_rate,
                                           channels=conformed.channels, sample_width=stream.sample_width)
            return DeliveryResult.ok(self._name, OutputModality.SPEECH)
        except Exception as e:
            logger.error(f"RemoteAudioOutput delivery to {self._physical_id} failed: {e}")
            return DeliveryResult.drop(self._name, modality, detail=str(e))

    def get_output_type(self) -> str:
        return "remote_audio"

    def origin_key(self) -> Optional[str]:
        return self._physical_id
