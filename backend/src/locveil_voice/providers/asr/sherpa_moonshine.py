"""Moonshine ASR on the sherpa-onnx runtime (I18N-2) — the armv7 (WB7) English ASR.

A subclass of `SherpaOnnxASRProvider`, not a `model_type`, because Moonshine diverges from the base's
VOSK/Whisper families on all three axes the base assumes are shared:
- **Distribution** — a k2-fsa GitHub-release `.tar.bz2` (URL + extract, like Piper voices), NOT an HF
  model-pack; so it downloads via `AssetManager.download_model`, not `download_model_pack`.
- **Pack shape** — a merged `.ort` export (`encoder_model.ort` + `decoder_model_merged.ort` + tokens),
  NOT the 4 `.onnx` transducer members.
- **Construction** — the merged decoder isn't exposed by `OfflineRecognizer.from_moonshine()` (it only
  takes the older 4-file layout), so the recognizer is built directly from `OfflineMoonshineModelConfig`
  with `merged_decoder=…`.

Isolating those here keeps the base clean (HF packs + public `from_*` factories). Everything else is
inherited: `transcribe_audio`/`_decode` (offline — Moonshine is offline, `supports_streaming` is False,
so `/ws/audio` uses the batch branch and dodges the streaming-branch defect BUG-13), `get_capabilities`,
`get_supported_languages` (→ the model's language), `warm_up`, and the build/deps metadata.

Runs on sherpa-onnx >= 1.12 (merged-decoder support); the armv7 pin is 1.12.36 with the onnxruntime
`.so` alignment patch + a bookworm base (BUG-14). Proven on the WB7: RTF ~0.7, ~134 MB RSS.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Callable, Dict

from .sherpa_onnx import SherpaOnnxASRProvider

logger = logging.getLogger(__name__)


class SherpaMoonshineASRProvider(SherpaOnnxASRProvider):
    """Offline Moonshine ASR via sherpa-onnx `OfflineRecognizer` (merged-decoder config)."""

    _K2_RELEASE = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Moonshine defaults differ from the base (which defaults to the RU vosk pack). English-only,
        # offline — so no streaming (batch branch), and the language is English unless overridden.
        self.model_id = config.get("model", "moonshine-tiny-en")
        self.default_language = config.get("default_language", "en")
        self._is_streaming = False

    def get_provider_name(self) -> str:
        return "sherpa_moonshine"

    # ------------------------------------------------------------- recognizer
    @staticmethod
    def _resolve_pack(model_dir: Path) -> Dict[str, Path]:
        """Locate the merged-Moonshine members in an extracted pack (the `.tar.bz2` expands into a
        `sherpa-onnx-moonshine-*` subdir, so search recursively)."""
        try:
            encoder = next(p for p in model_dir.rglob("encoder*.ort") if p.is_file())
            merged = next(p for p in model_dir.rglob("*decoder*merged*.ort") if p.is_file())
            tokens = next(p for p in model_dir.rglob("tokens.txt") if p.is_file())
        except StopIteration as e:
            raise RuntimeError(
                f"Moonshine pack at {model_dir} is missing encoder_model.ort / "
                f"decoder_model_merged.ort / tokens.txt"
            ) from e
        return {"encoder": encoder, "merged_decoder": merged, "tokens": tokens}

    async def _do_load_recognizer(self) -> None:
        # (BUG-13: load-locking lives in the base `_load_recognizer`; this is the guarded body.)
        import sherpa_onnx
        # sherpa-onnx's Python objects are dynamically built and the merged-decoder path isn't in its
        # typed public API (from_moonshine only exposes the old 4-file layout), so build against `Any`.
        so: Any = sherpa_onnx

        # URL + extract (the .tar.bz2 GitHub release), NOT the HF model-pack path the base uses.
        model_dir = await self.asset_manager.download_model(self.get_provider_name(), self.model_id)
        files = self._resolve_pack(Path(model_dir))

        def build() -> Any:
            # The merged decoder isn't exposed by the from_moonshine() helper, so build the config
            # directly. `_Recognizer` is the native pybind class the sherpa Python factories construct;
            # grab it from from_moonshine's globals so we track whatever the installed version uses.
            recognizer_cls = so.OfflineRecognizer.from_moonshine.__globals__.get("_Recognizer")
            if recognizer_cls is None:  # pragma: no cover - defensive: sherpa API drift
                raise RuntimeError("sherpa-onnx: could not resolve the internal OfflineRecognizer class")
            model_config = so.OfflineModelConfig(
                moonshine=so.OfflineMoonshineModelConfig(
                    encoder=str(files["encoder"]),
                    merged_decoder=str(files["merged_decoder"]),
                ),
                tokens=str(files["tokens"]),
                num_threads=self.policy.num_threads,
                provider="cpu",
            )
            recognizer_config = so.OfflineRecognizerConfig(
                model_config=model_config,
                feat_config=so.FeatureExtractorConfig(sampling_rate=16000, feature_dim=80),
                decoding_method=self.decoding_method,
            )
            rec: Any = so.OfflineRecognizer.__new__(so.OfflineRecognizer)
            rec.recognizer = recognizer_cls(recognizer_config)
            rec.config = recognizer_config
            return rec

        build_fn: Callable[[], Any] = build
        # onnxruntime graph init is blocking — keep it off the event loop (same as the base).
        self._recognizer = await asyncio.to_thread(build_fn)
        logger.info(f"Loaded sherpa-onnx Moonshine recognizer: model={self.model_id} "
                    f"threads={self.policy.num_threads}")

    # ------------------------------------------------------ asset / build meta
    @classmethod
    def _get_default_directory(cls) -> str:
        return "sherpa_moonshine"

    @classmethod
    def _get_default_model_urls(cls) -> Dict[str, Any]:
        # k2-fsa GitHub-release `.tar.bz2` (extracted into sherpa_moonshine/<model_id>/). Offline,
        # English-only, ~43 MB int8 merged .ort — the newer quantized export (NOT the 123 MB -int8 build).
        return {
            "moonshine-tiny-en": {
                "url": f"{cls._K2_RELEASE}/sherpa-onnx-moonshine-tiny-en-quantized-2026-02-27.tar.bz2",
                "extract": True,
                "size": "~43 MB int8 (English, offline)",
                "description": "Moonshine tiny (quantized, merged .ort) — armv7 WB7 English ASR",
            },
        }
