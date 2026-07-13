"""Silero VAD provider — SileroVAD-ONNX via sherpa-onnx (ARCH-18 PR-2).

Wraps `SileroVADEngine`. As an adapter it resolves the model path AND downloads the model through the
AssetManager (asset name `silero_vad` — distinct from the silero TTS asset name; ASSET-4): the download
happens once in `_do_initialize` (lock, temp+rename, partial-download healing — never on the audio hot
path), and the segmenter falls back to `energy` if initialization fails. 64-bit only — VAD runs in Irene
only for a local mic; the WB7 satellite does VAD on-device.
"""

from types import SimpleNamespace
from typing import Any, Dict, List

from .base import VADProvider
from ...utils.audio_data import AudioData
from ...utils.vad import VADResult
from ...utils.loader import safe_import

# Asset identity (ASSET-4): 'silero' is taken by silero TTS in the AssetManager's namespace map,
# so this provider's assets live under 'silero_vad'; the directory stays `models/<vad>/` so
# already-deployed volumes keep their `models/vad/silero_vad.onnx` unchanged.
ASSET_NAME = "silero_vad"
MODEL_ID = "silero_vad"  # + '.onnx' extension from get_asset_config


class SileroVADProvider(VADProvider):
    """SileroVAD voice activity detection (sherpa-onnx runtime)."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        from ...core.assets import get_asset_manager  # adapters may import core (inward)
        from ...utils.vad_silero import SileroVADEngine
        self._model_url = self.config.get("model_url") or None  # TOML override; None → class default URL
        model_path = get_asset_manager().get_model_path(ASSET_NAME, MODEL_ID)
        # SileroVADEngine reads attributes off a config object; map this provider's [vad.providers.silero]
        # block ({threshold, voice/silence_duration_ms}) onto the names it expects.
        ns = SimpleNamespace(
            silero_threshold=self.config.get("threshold", 0.5),
            voice_duration_ms=self.config.get("voice_duration_ms", 100),
            silence_duration_ms=self.config.get("silence_duration_ms", 200),
        )
        self._engine = SileroVADEngine(ns, model_path)

    async def _do_initialize(self) -> None:
        """Fetch `silero_vad.onnx` via the AssetManager (no-op when already on the volume)."""
        from ...core.assets import get_asset_manager
        await get_asset_manager().download_model(ASSET_NAME, MODEL_ID, url_override=self._model_url)

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

    def detection_latency_ms(self, frame_ms: float) -> int:
        # Duration-based: fires after `min_speech_duration` (voice_duration_ms) of speech — independent of
        # the frame size, so frame_ms is ignored.
        return int(self.config.get("voice_duration_ms", 100))

    @classmethod
    def _get_default_model_urls(cls) -> Dict[str, str]:
        from ...utils.vad_silero import DEFAULT_SILERO_URL
        return {MODEL_ID: DEFAULT_SILERO_URL}

    @classmethod
    def _get_default_directory(cls) -> str:
        return "vad"  # keep the pre-ASSET-4 on-disk location: models/vad/silero_vad.onnx

    @classmethod
    def _get_default_extension(cls) -> str:
        return ".onnx"

    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        # asr-onnx = the sherpa-onnx runtime it reuses; vad-silero = numpy (no longer a base dep,
        # BUG-33) — kept OUT of asr-onnx, which the numpy-free armv7 image installs for sherpa.
        return ["asr-onnx", "vad-silero"]  # extra group names (build contract)

    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        return {"linux.ubuntu": [], "linux.alpine": [], "macos": [], "windows": []}
