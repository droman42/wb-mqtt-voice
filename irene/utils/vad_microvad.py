"""microVAD engine (pymicro-vad) — the `microvad` VAD implementation (QUAL-20).

64-bit only: VAD runs in Irene only in the standalone local-mic scenario (the WB7 delegates VAD to the
ESP32). `pymicro-vad` (rhasspy, Apache-2.0) is self-contained — it bundles the model and a precompiled
tflite C lib, and shares the same `pymicro-features` micro frontend as the microWakeWord provider, so the
two form one coherent "micro" stack (and match the ESP32's on-device VAD). Unlike silero, it needs no
model download / asset path.

`MicroVad.process_10ms(bytes) -> float` consumes exactly 10 ms of 16 kHz / 16-bit mono PCM (320 bytes);
this wraps it into the per-frame `VADEngine` port, buffering odd frame sizes into 10 ms chunks.
"""

import logging
import time

from .vad import VADEngine, VADResult
from .audio_data import AudioData

logger = logging.getLogger(__name__)

# 10 ms of 16 kHz / 16-bit mono PCM = 160 samples = 320 bytes — the unit pymicro-vad consumes.
_CHUNK_BYTES = 320


class MicroVADEngine(VADEngine):
    """Per-frame voice activity via pymicro-vad (microVAD)."""

    def __init__(self, vad_config):
        self.threshold = float(getattr(vad_config, "microvad_threshold", 0.5))
        self._buffer = bytearray()
        self._vad = None  # lazy: built on first frame

    def _ensure(self):
        if self._vad is None:
            from pymicro_vad import MicroVad
            self._vad = MicroVad()
            logger.info(f"microVAD engine ready (threshold={self.threshold})")
        return self._vad

    def process_frame(self, audio_data: AudioData) -> VADResult:
        t0 = time.time()
        prob = 0.0
        try:
            vad = self._ensure()
            data = audio_data.data if isinstance(audio_data.data, (bytes, bytearray)) else bytes(audio_data.data)
            self._buffer.extend(data)
            while len(self._buffer) >= _CHUNK_BYTES:
                chunk = bytes(self._buffer[:_CHUNK_BYTES])
                del self._buffer[:_CHUNK_BYTES]
                prob = max(prob, float(vad.process_10ms(chunk)))
        except Exception as e:
            logger.error(f"microVAD error: {e}")
        is_voice = prob > self.threshold
        return VADResult(
            is_voice=is_voice,
            confidence=prob,
            energy_level=0.0,
            timestamp=getattr(audio_data, "timestamp", 0.0),
            processing_time_ms=(time.time() - t0) * 1000.0,
        )

    def reset(self) -> None:
        self._buffer.clear()
        if self._vad is not None:
            self._vad.reset()
