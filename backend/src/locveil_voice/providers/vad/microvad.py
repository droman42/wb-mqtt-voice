"""microVAD provider — pymicro-vad (ARCH-18 PR-2).

Wraps `MicroVADEngine`. Self-contained (bundles its model + tflite C lib), shares the micro frontend with
the microWakeWord provider. 64-bit Linux only (no Windows/macOS/armv7 wheel — see `vad-tflite` extra).
"""

from types import SimpleNamespace
from typing import Any, Dict, List

from .base import VADProvider
from ...utils.audio_data import AudioData
from ...utils.vad import VADResult
from ...utils.loader import safe_import


class MicroVADProvider(VADProvider):
    """microVAD voice activity detection (pymicro-vad)."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        from ...utils.vad_microvad import MicroVADEngine
        # Map this provider's [vad.providers.microvad] block ({threshold}) onto the engine's name.
        self._engine = MicroVADEngine(SimpleNamespace(microvad_threshold=self.config.get("threshold", 0.5)))

    def get_provider_name(self) -> str:
        return "microvad"

    async def is_available(self) -> bool:
        if safe_import("pymicro_vad") is None:
            self._set_status(self.status.__class__.UNAVAILABLE, "pymicro-vad not installed (extra: vad-tflite)")
            return False
        return True

    def process_frame(self, audio_data: AudioData) -> VADResult:
        return self._engine.process_frame(audio_data)

    def reset(self) -> None:
        self._engine.reset()

    def detection_latency_ms(self, frame_ms: float) -> int:
        # Duration-based (pymicro-vad decides per 10 ms chunk); operator-tunable via config, default 30 ms.
        return int(self.config.get("detection_latency_ms", 30))

    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        return ["vad-tflite"]  # extra group name (build contract)

    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        return {"linux.ubuntu": [], "linux.alpine": [], "macos": [], "windows": []}
    @classmethod
    def get_supported_architectures(cls) -> List[str]:
        return ["x86_64", "aarch64"]  # pymicro-vad has no armv7 wheel (ARCH-24 T3)
