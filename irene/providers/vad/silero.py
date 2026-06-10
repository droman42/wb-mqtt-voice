"""Silero VAD provider — SileroVAD-ONNX via sherpa-onnx (ARCH-18 PR-2).

Wraps `SileroVADEngine`. As an adapter it resolves the model path through the AssetManager **directly**
(the old workflow-side path injection is gone). 64-bit only — VAD runs in Irene only for a local mic; the
WB7 satellite does VAD on-device.
"""

from types import SimpleNamespace
from typing import Any, Dict, List

from .base import VADProvider
from ...utils.audio_data import AudioData
from ...utils.vad import VADResult
from ...utils.loader import safe_import


class SileroVADProvider(VADProvider):
    """SileroVAD voice activity detection (sherpa-onnx runtime)."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        from ...core.assets import get_asset_manager  # adapters may import core (inward)
        from ...utils.vad_silero import SileroVADEngine
        model_path = get_asset_manager().get_model_path("vad", "silero_vad.onnx")
        # SileroVADEngine reads attributes off a config object; the provider config is a dict.
        self._engine = SileroVADEngine(SimpleNamespace(**self.config), model_path)

    def get_provider_name(self) -> str:
        return "silero"

    async def is_available(self) -> bool:
        if safe_import("sherpa_onnx") is None:
            self._set_status(self.status.__class__.UNAVAILABLE, "sherpa-onnx not installed (extra: asr-onnx)")
            return False
        return True

    def process_frame(self, audio_data: AudioData) -> VADResult:
        return self._engine.process_frame(audio_data)

    def reset(self) -> None:
        self._engine.reset()

    @property
    def detection_latency_ms(self) -> int:
        # Fires after `min_speech_duration` (voice_duration_ms) of speech.
        return int(self.config.get("voice_duration_ms", 100))

    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        return ["asr-onnx"]  # reuses the sherpa-onnx runtime; extra group name (build contract)

    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        return {"linux.ubuntu": [], "linux.alpine": [], "macos": [], "windows": []}

    @classmethod
    def get_platform_support(cls) -> List[str]:
        return ["linux.ubuntu", "linux.alpine", "macos", "windows"]
