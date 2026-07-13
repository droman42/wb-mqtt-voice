"""
TraceInput — an InputPort that replays a saved trace's audio (ARCH-19 D-9).

"The microphone, sourced from a trace file": it decodes the trace's inline PCM and yields it as
a stream of AudioData frames, so a segmenter/raw-level replay can re-enter the *streaming* pipeline
(VAD → wake → ASR) exactly like a live mic — without standing up the InputManager. The utterance
level does not use this (it re-enters pre-segmented via process_audio_input).

The trace stores the captured audio as one assembled blob (not per-frame), so we re-chunk it into
fixed frames here; VAD re-segments it fresh on replay, so the exact framing is not significant.
"""

import logging
from typing import AsyncIterator

from ..core.interfaces.input import InputPort
from ..intents.models import AudioData

logger = logging.getLogger(__name__)


class TraceInput(InputPort):
    """Yields a saved trace's audio as AudioData frames for streaming replay."""

    def __init__(self, audio_bytes: bytes, sample_rate: int = 16000, channels: int = 1,
                 format: str = "pcm16", frame_ms: int = 20, base_timestamp: float = 0.0):
        self._audio = audio_bytes or b""
        self.sample_rate = sample_rate or 16000
        self.channels = channels or 1
        self.format = format or "pcm16"
        self.frame_ms = frame_ms
        self._base_ts = base_timestamp
        self._listening = False

    async def start_listening(self) -> None:
        self._listening = True

    async def stop_listening(self) -> None:
        self._listening = False

    def get_input_type(self) -> str:
        return "trace"

    def _frame_bytes(self) -> int:
        bytes_per_sample = max(1, self.channels) * 2  # pcm16 = 2 bytes/sample/channel
        return max(bytes_per_sample,
                   int(self.sample_rate * self.frame_ms / 1000) * bytes_per_sample)

    async def listen(self) -> AsyncIterator[AudioData]:  # narrower than InputPort's InputData — only audio
        """Yield the decoded audio as monotonically-timestamped frames, then stop."""
        if not self._listening:
            return
        frame_bytes = self._frame_bytes()
        dt = self.frame_ms / 1000.0
        ts = self._base_ts
        for off in range(0, len(self._audio), frame_bytes):
            if not self._listening:
                break
            chunk = self._audio[off:off + frame_bytes]
            if not chunk:
                break
            yield AudioData(data=chunk, timestamp=ts, sample_rate=self.sample_rate,
                            channels=self.channels, format=self.format)
            ts += dt
