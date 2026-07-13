"""Piper TTS provider — VITS via sherpa-onnx OfflineTts (ARCH-24 T2).

Torch-free neural TTS on the **same sherpa-onnx runtime** the ASR + VAD providers use — so it runs
on armv7 (WB7) and aarch64/x86_64 alike, the only ONNX engine that works on the 32-bit target.

Voices are the k2-fsa Piper exports (`vits-piper-ru_RU-<voice>-medium`), each a self-contained
`.tar.bz2` pack: `model.onnx` + `tokens.txt` + `espeak-ng-data/`. espeak-ng phonemization is
statically linked **inside** sherpa-onnx and the data dir ships in the pack, so there is **no system
`espeak-ng` (or bz2) package to install**. Phonemization uses espeak-ng's built-in Russian rules;
the `piper_ruaccent` subclass (PR3, 64-bit only) overrides `_prepare_text` to add an explicit
stress/homograph pass.

Design notes:
- **numpy-free** float→PCM conversion (stdlib `array`) — armv7 has no numpy wheel (same policy as
  the sherpa ASR provider).
- one provider, the **voice** selected by config (like `sherpa_onnx` selects `model_type`).
- the onnxruntime graph init is blocking — built off the event loop in `warm_up()`/first synth.
- uses the shared `InferencePolicy` (utils.inference_policy) for the thread budget — consistent with
  the sherpa-onnx ASR + VAD providers (ARCH-24 T5).
"""

import array
import asyncio
import logging
import sys
import wave
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .base import TTSProvider
from ...utils.audio_stream import PCMStream
from ...utils.inference_policy import InferencePolicy

logger = logging.getLogger(__name__)


def _float_to_pcm16(samples) -> bytes:
    """float [-1, 1] (list or array-like) -> little-endian int16 PCM, **numpy-free** (Piper runs on
    armv7, where numpy is deliberately not installed — it is not a base dependency, see pyproject;
    sherpa's `generate()` returns a plain float list there)."""
    out = array.array("h")
    out.extend(max(-32768, min(32767, int(s * 32767.0))) for s in samples)
    if sys.byteorder == "big":
        out.byteswap()  # 'h' is native-endian; force little-endian for the PCM contract
    return out.tobytes()


class PiperTTSProvider(TTSProvider):
    """Offline VITS/Piper TTS via sherpa-onnx `OfflineTts`. Base for `piper_ruaccent` (PR3)."""

    _K2_RELEASE = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        from ...core.assets import get_asset_manager
        self.asset_manager = get_asset_manager()

        # The voice IS the model id (routed to piper/<voice>/ by the AssetManager, like sherpa packs).
        self.voice: str = config.get("voice", config.get("model", "irina"))
        self.language: str = config.get("language", "ru")
        self.speaker_id: int = int(config.get("speaker_id", 0))
        self.speed: float = float(config.get("speed", 1.0))
        self.num_threads: int = InferencePolicy.for_platform(config.get("num_threads")).num_threads

        self._tts: Any = None  # sherpa_onnx.OfflineTts, lazily built

        if config.get("preload_models", False):
            self._warmup_task = asyncio.create_task(self.warm_up())  # QUAL-58: hold the ref (unreferenced tasks are GC-cancellable mid-load)

    def get_provider_name(self) -> str:
        return "piper"

    async def is_available(self) -> bool:
        try:
            import sherpa_onnx  # noqa: F401
        except ImportError:
            logger.warning("sherpa-onnx not installed — piper TTS provider unavailable")
            return False
        return bool(self.asset_manager.get_model_info("piper", self.voice))

    # ------------------------------------------------------------- voice pack
    @staticmethod
    def _resolve_pack(model_dir: Path) -> Dict[str, Path]:
        """Locate model.onnx + tokens.txt + espeak-ng-data/ in an extracted Piper pack (the k2-fsa
        `.tar.bz2` expands to a `vits-piper-...` subdir, so search recursively)."""
        try:
            onnx = next(p for p in sorted(model_dir.rglob("*.onnx")) if p.is_file())
            tokens = next(p for p in model_dir.rglob("tokens.txt") if p.is_file())
            data_dir = next(p for p in model_dir.rglob("espeak-ng-data") if p.is_dir())
        except StopIteration as e:
            raise RuntimeError(
                f"Piper voice pack at {model_dir} is missing model.onnx / tokens.txt / espeak-ng-data"
            ) from e
        return {"model": onnx, "tokens": tokens, "data_dir": data_dir}

    async def _ensure_loaded(self) -> None:
        if self._tts is not None:
            return
        import sherpa_onnx

        model_dir = await self.asset_manager.download_model("piper", self.voice)  # extracts the .tar.bz2
        files = self._resolve_pack(Path(model_dir))

        def build():
            cfg = sherpa_onnx.OfflineTtsConfig(
                model=sherpa_onnx.OfflineTtsModelConfig(
                    vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                        model=str(files["model"]),
                        tokens=str(files["tokens"]),
                        data_dir=str(files["data_dir"]),
                    ),
                    provider="cpu",
                    num_threads=self.num_threads,
                ),
                max_num_sentences=1,
            )
            if hasattr(cfg, "validate") and not cfg.validate():
                raise RuntimeError(f"sherpa-onnx OfflineTtsConfig.validate() failed for piper voice '{self.voice}'")
            return sherpa_onnx.OfflineTts(cfg)

        # onnxruntime graph init is blocking — keep it off the event loop.
        self._tts = await asyncio.to_thread(build)
        logger.info(f"Loaded piper voice '{self.voice}' (threads={self.num_threads})")

    async def warm_up(self) -> None:
        try:
            logger.info(f"Warming up piper voice '{self.voice}'...")
            await self._ensure_loaded()
        except Exception as e:
            logger.error(f"Failed to warm up piper voice {self.voice}: {e}")  # lazy-load on first synth

    # --------------------------------------------------- text-prep hook (PR3)
    async def _prepare_text(self, text: str) -> str:
        """Pre-synthesis text shaping. Base = identity (espeak-ng handles phonemes + stress).
        `piper_ruaccent` overrides ONLY this to inject explicit Russian stress marks."""
        return text

    # ------------------------------------------------------------- synthesis
    def _generate_pcm(self, text: str, speaker_id: int, speed: float) -> Tuple[bytes, int]:
        audio = self._tts.generate(text, sid=speaker_id, speed=speed)
        return _float_to_pcm16(audio.samples), int(audio.sample_rate)

    async def synthesize_to_stream(self, text: str, **kwargs) -> PCMStream:
        """Native streaming (ARCH-21): sherpa produces the whole waveform in memory, yield it as
        int16 PCM directly — no WAV round-trip."""
        await self._ensure_loaded()
        prepared = await self._prepare_text(text)
        sid = int(kwargs.get("speaker_id", self.speaker_id))
        speed = float(kwargs.get("speed", self.speed))
        pcm, rate = await asyncio.to_thread(self._generate_pcm, prepared, sid, speed)

        async def _frames():
            yield pcm

        return PCMStream(sample_rate=rate, channels=1, sample_width=2, frames=_frames())

    async def synthesize_to_file(self, text: str, output_path: Path, **kwargs) -> None:
        await self._ensure_loaded()
        prepared = await self._prepare_text(text)
        sid = int(kwargs.get("speaker_id", self.speaker_id))
        speed = float(kwargs.get("speed", self.speed))
        pcm, rate = await asyncio.to_thread(self._generate_pcm, prepared, sid, speed)
        await asyncio.to_thread(self._write_wav, output_path, pcm, rate)

    @staticmethod
    def _write_wav(output_path: Path, pcm: bytes, rate: int) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(pcm)

    # ---------------------------------------------------------- capabilities
    _LANG_TAG = {"ru": "ru-RU", "en": "en-US"}

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            # per-instance language (the configured voice's locale) — the catalog now spans ru + en.
            "languages": [self._LANG_TAG.get(self.language, self.language)],
            "voices": list(self._get_default_model_urls().keys()),
            "formats": ["wav"],
            "features": ["neural_synthesis", "offline", "streaming"],
            "quality": "medium",
            "speed": "fast",
        }

    # ------------------------------------------------------ asset / build meta
    @classmethod
    def _get_default_directory(cls) -> str:
        return "piper"

    @classmethod
    def _get_default_cache_types(cls) -> List[str]:
        return ["models", "runtime"]

    @classmethod
    def _get_default_model_urls(cls) -> Dict[str, Any]:
        # k2-fsa Piper voices (medium). Each is a self-contained `.tar.bz2` pack
        # (model.onnx + tokens.txt + espeak-ng-data/); `extract` tells the AssetManager to unpack
        # it into piper/<voice>/ on first run. Same pack shape + sherpa runtime for every locale, so
        # English is just a different locale in the URL (I18N-3) — no provider/runtime change.
        def voice(name: str, note: str, locale: str = "ru_RU") -> Dict[str, Any]:
            return {
                "url": f"{cls._K2_RELEASE}/vits-piper-{locale}-{name}-medium.tar.bz2",
                "extract": True,
                "size": "~60-75 MB",
                "description": note,
            }

        return {
            # Russian (ru_RU) — the satellite default persona
            "irina": voice("irina", "female — best-quality ru voice (alphacephei eval)"),
            "ruslan": voice("ruslan", "male"),
            "denis": voice("denis", "male"),
            "dmitri": voice("dmitri", "male"),
            # English (en_US) — I18N-3. `amy` is the default EN voice (female, close to the ru persona).
            "amy": voice("amy", "female — default en_US voice", "en_US"),
            "lessac": voice("lessac", "neutral en_US", "en_US"),
            "ryan": voice("ryan", "male en_US", "en_US"),
        }

    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        # The sherpa-onnx runtime (the same `asr-onnx` extra the ASR/VAD providers use). espeak-ng is
        # statically linked inside sherpa-onnx; the espeak-ng-data ships in the voice pack. No torch.
        return ["asr-onnx"]

    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        # sherpa-onnx is self-contained (vendors libasound, bundles piper-phonemize). No system
        # espeak-ng/bz2 needed (bz2 is in the python base; espeak-ng-data ships in the pack).
        return {"linux.ubuntu": ["libasound2"], "linux.alpine": ["alsa-lib"], "macos": [], "windows": []}
