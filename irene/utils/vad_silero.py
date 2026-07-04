"""SileroVAD engine (sherpa-onnx) — the `silero` VAD implementation (ARCH-10 PR-4).

64-bit only: VAD runs in Irene only in the standalone local-mic scenario (the WB7
delegates VAD to the ESP32, §11). So this reuses sherpa-onnx (already present via the
`asr-onnx` extra on 64-bit) and numpy (a core dep) — no new dependencies.

sherpa-onnx's VAD is segment-oriented; this wraps it into the per-frame `VADEngine`
port via `is_speech_detected()`, so it's a drop-in alternative to the energy engine.
The `silero_vad.onnx` model is downloaded once into the asset/models folder (a mounted
volume in production) by the ADAPTER (`providers/vad/silero.py`) through the
AssetManager at provider initialization (ASSET-4) — this engine only loads the file
(utils must not import core, ARCH-12 contract #9) and fails loudly if it's missing.
"""

import logging
import time
from pathlib import Path

from .vad import VADEngine, VADResult
from .audio_data import AudioData

logger = logging.getLogger(__name__)

DEFAULT_SILERO_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx"
)


class SileroVADEngine(VADEngine):
    """Per-frame voice activity via sherpa-onnx's SileroVAD."""

    def __init__(self, vad_config, model_path):
        self.sample_rate = 16000
        self.threshold = float(getattr(vad_config, "silero_threshold", 0.5))
        self.min_speech_s = getattr(vad_config, "voice_duration_ms", 100) / 1000.0
        self.min_silence_s = getattr(vad_config, "silence_duration_ms", 200) / 1000.0
        # The asset path is injected by the adapter (providers/vad/silero.py), which also
        # downloads the model via the AssetManager before first use (ASSET-4) — utils must
        # not import core (ARCH-12 contract #9).
        self._model_path = Path(model_path)
        self._vad = None  # lazy: built on first frame (inits onnxruntime)

    def _ensure(self):
        if self._vad is not None:
            return self._vad
        if not (self._model_path.exists() and self._model_path.stat().st_size > 0):
            # No download here: the adapter's _do_initialize owns that (with the AssetManager's
            # lock/atomicity/partial-healing). Reaching this means init was skipped or failed.
            raise FileNotFoundError(
                f"SileroVAD model missing: {self._model_path} — provider initialization "
                f"did not run or its download failed (see startup log)"
            )
        import sherpa_onnx
        from .inference_policy import InferencePolicy

        cfg = sherpa_onnx.VadModelConfig()
        cfg.silero_vad.model = str(self._model_path)
        cfg.silero_vad.threshold = self.threshold
        cfg.silero_vad.min_silence_duration = self.min_silence_s
        cfg.silero_vad.min_speech_duration = self.min_speech_s
        cfg.sample_rate = self.sample_rate
        cfg.num_threads = InferencePolicy.for_platform().num_threads  # ARCH-24 T5: shared thread budget
        self._vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=30)
        logger.info(f"SileroVAD engine ready (threshold={self.threshold}, threads={cfg.num_threads})")
        return self._vad

    def process_frame(self, audio_data: AudioData) -> VADResult:
        t0 = time.time()
        is_voice = False
        try:
            vad = self._ensure()
            samples = self._to_float(audio_data.data)
            if samples.size:
                vad.accept_waveform(samples)
                is_voice = bool(vad.is_speech_detected())
        except Exception as e:
            logger.error(f"SileroVAD error: {e}")
        return VADResult(
            is_voice=is_voice,
            confidence=1.0 if is_voice else 0.0,
            energy_level=0.0,
            timestamp=getattr(audio_data, "timestamp", 0.0),
            processing_time_ms=(time.time() - t0) * 1000.0,
        )

    def reset(self) -> None:
        if self._vad is not None:
            self._vad.reset()

    @staticmethod
    def _to_float(data: bytes):
        """Raw 16-bit PCM -> float32 numpy array in [-1, 1] (numpy is a core dep)."""
        import numpy as np
        if not data:
            return np.zeros(0, dtype="float32")
        n = len(data) // 2 * 2  # drop a trailing odd byte
        return np.frombuffer(data[:n], dtype="<i2").astype("float32") / 32768.0
