"""Energy VAD provider — the dependency-free built-in (ARCH-18 PR-2).

Wraps `SimpleVAD` / `AdvancedVAD`: a plain `SimpleVAD` unless zero-crossing-rate or adaptive thresholding
is enabled, in which case the adaptive `AdvancedVAD`. The default engine.
"""

from typing import Any, Dict, List

from .base import VADProvider
from ...utils.audio_data import AudioData
from ...utils.vad import SimpleVAD, AdvancedVAD, VADResult


class EnergyVADProvider(VADProvider):
    """Energy / zero-crossing voice activity detection (no extra dependencies)."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        g = self.config.get
        if g("use_zero_crossing_rate", True) or g("adaptive_threshold", False):
            self._engine = AdvancedVAD(
                threshold=g("energy_threshold", 0.01),
                sensitivity=g("sensitivity", 0.5),
                voice_frames_required=g("voice_frames_required", 2),
                silence_frames_required=g("silence_frames_required", 5),
                use_zcr=g("use_zero_crossing_rate", True),
                noise_percentile=g("noise_percentile", 15),
                voice_multiplier=g("voice_multiplier", 3.0),
            )
        else:
            self._engine = SimpleVAD(
                threshold=g("energy_threshold", 0.01),
                sensitivity=g("sensitivity", 0.5),
                voice_frames_required=g("voice_frames_required", 2),
                silence_frames_required=g("silence_frames_required", 5),
            )

    def get_provider_name(self) -> str:
        return "energy"

    def process_frame(self, audio_data: AudioData) -> VADResult:
        return self._engine.process_frame(audio_data)

    def reset(self) -> None:
        self._engine.reset()

    def detection_latency_ms(self, frame_ms: float) -> int:
        # Fires after `voice_frames_required` consecutive voice frames — its latency IS a frame count, so it
        # scales with the real frame duration (ARCH-18 PR-5: derived from canonical, no hardcoded ms/frame).
        return round(int(self.config.get("voice_frames_required", 2)) * frame_ms)

    def calibrate(self, audio_samples: List[AudioData]) -> bool:
        return self._engine.calibrate_threshold(audio_samples)

    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        return ["vad-energy"]  # numpy: utils/vad.py does the DSP (no longer a base dep — BUG-33)

    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        return {"linux.ubuntu": [], "linux.alpine": [], "macos": [], "windows": []}
