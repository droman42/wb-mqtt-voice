"""VAD provider base — the voice-activity-detection capability port (ARCH-18 PR-2).

VAD was a 4-way if-else over util engine classes in `VoiceSegmenter`. It is now a lightweight
provider family (`irene.providers.vad`): each provider wraps a VAD engine and is discovered via entry-points
+ selected by `[vad] default_provider`, exactly like the other provider families — no component/manager
apparatus (VAD is a per-frame hot-path primitive, not a request/response service).

Providers expose `detection_latency_ms` so the segmenter can size its pre-roll to the engine's onset lag
(ARCH-17 Q1), and `calibrate` (default no-op; energy opts in).
"""

import logging
from abc import abstractmethod
from typing import Any, Dict, List

from ..base import ProviderBase
from ...utils.audio_data import AudioData
from ...utils.vad import VADResult
from ...utils.audio_negotiation import AudioContract

logger = logging.getLogger(__name__)


class VADProvider(ProviderBase):
    """Base class for voice-activity-detection providers (energy / silero / microvad)."""

    @abstractmethod
    def process_frame(self, audio_data: AudioData) -> VADResult:
        """Classify one audio chunk as voice/silence."""
        ...

    def reset(self) -> None:
        """Reset per-utterance state (default no-op)."""
        return None

    @property
    @abstractmethod
    def detection_latency_ms(self) -> int:
        """How long (ms) of speech this engine needs before it reports voice — the segmenter sizes its
        pre-roll buffer from this so the wake-word onset is never clipped (ARCH-17 Q1)."""
        ...

    def calibrate(self, audio_samples: List[AudioData]) -> bool:
        """Calibrate the detection threshold from sample audio. Default no-op for engines with a fixed,
        model-internal threshold (silero/microvad); the energy provider overrides it."""
        return False

    @property
    def threshold(self) -> float:
        """Detection threshold, delegated to the wrapped engine (dynamic-threshold updates)."""
        return float(getattr(getattr(self, "_engine", None), "threshold", 0.0))

    @threshold.setter
    def threshold(self, value: float) -> None:
        engine = getattr(self, "_engine", None)
        if engine is not None and hasattr(engine, "threshold"):
            engine.threshold = value

    async def is_available(self) -> bool:
        """Available iff the underlying engine can be constructed (overridden where deps are optional)."""
        return True

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "sample_rates": [16000],
            "channels": [1],
            "formats": ["pcm16"],
            "detection_latency_ms": self.detection_latency_ms,
        }

    def audio_contract(self) -> AudioContract:
        """What this VAD engine needs from the pipeline (ARCH-18): 16 kHz / pcm16 / mono."""
        return AudioContract([16000], 16000, ["pcm16"], "pcm16", 1)
