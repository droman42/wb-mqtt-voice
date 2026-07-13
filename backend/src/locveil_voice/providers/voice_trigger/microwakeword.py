"""
microWakeWord Voice Trigger Provider

Server-side wake-word detection backed by **pymicro-wakeword** (OHF-Voice, Apache-2.0) — the same
"micro" stack that runs on the ESP32 satellites on-device. The library bundles the micro_speech feature
frontend, the streaming tflite inference, and a precompiled tflite C lib, so this provider is a thin
adapter (QUAL-20): it resolves each configured wake word to a `MicroWakeWord` and streams
16 kHz / 16-bit mono PCM through it in 10 ms chunks.

A wake-word model is a **two-file v2 pack** — a JSON manifest + the streaming `.tflite` it references
*relative to itself* (`from_config` loads `manifest_dir / config["model"]`). Resolution order per
configured word (`docs/design/wakeword_models.md`, ARCH-29/ASSET-5):
1. local manifest path (pre-release testing of a just-trained model);
2. built-in — the four stock EN packs ship INSIDE the pymicro-wakeword wheel (zero download);
3. v2 manifest URL — microwakeword.com or a not-yet-cataloged HF model; the sibling `.tflite` is
   fetched with it through the AssetManager (`download_model_files`);
4. the released catalog below (`_get_default_model_urls`) — RU words trained in the in-house
   factory and published to HF (`droman42/microwakeword-<word>-ru`), one line per released word.

64-bit only — the WB7/armv7 target wakes on-device (ESP32), so this never enters the armv7 image.
See `docs/review/esp32_wakeword_review.md` and `docs/design/onnx_inference_layer.md` §11.

Upstream: https://github.com/OHF-Voice/pymicro-wakeword
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from .base import VoiceTriggerProvider
from ...intents.models import AudioData, WakeWordResult
from ...utils.loader import safe_import

logger = logging.getLogger(__name__)

# 10 ms of 16 kHz / 16-bit mono PCM = 160 samples = 320 bytes — the unit pymicro-wakeword consumes.
_CHUNK_BYTES = 320

# Built-in models shipped inside pymicro-wakeword (English). Aliases map friendly names → enum members.
_BUILTIN_ALIASES = {
    "okay_nabu": "OKAY_NABU", "nabu": "OKAY_NABU",
    "hey_jarvis": "HEY_JARVIS", "jarvis": "HEY_JARVIS",
    "hey_mycroft": "HEY_MYCROFT", "mycroft": "HEY_MYCROFT",
    "alexa": "ALEXA",
}


class MicroWakeWordProvider(VoiceTriggerProvider):
    """microWakeWord provider — thin adapter over `pymicro-wakeword`.

    Each configured wake word resolves to one streaming detector:
    - a **built-in** model (``okay_nabu``/``hey_jarvis``/``hey_mycroft``/``alexa``), or
    - a **custom** model — ``model_path`` pointing at a microwakeword.com manifest (``.json``) or a
      ``.tflite`` (the per-ESP32-unit custom Russian-name model).

    The library owns the feature frontend, the streaming state, the sliding window and the probability
    cutoff — this class only marshals audio and reports detections.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Lazily built in _do_initialize: one detector per wake word + a shared feature extractor.
        self._detectors: List[Any] = []
        self._features: Any = None
        self._detector_words: List[str] = []
        self._pcm_buffer = bytearray()  # carries sub-10 ms remainders between detect calls

        # Asset management — custom models are deployment-supplied (resolved to a local path).
        from ...core.assets import get_asset_manager
        self.asset_manager = get_asset_manager()

    def get_provider_name(self) -> str:
        return "microwakeword"

    async def is_available(self) -> bool:
        """Available iff pymicro-wakeword imports and at least one detector builds."""
        if safe_import('pymicro_wakeword') is None:
            self._set_status(self.status.__class__.UNAVAILABLE,
                             "pymicro-wakeword not installed (extra: wake-tflite)")
            return False
        if not self._detectors:
            await self._initialize_detectors()
        return bool(self._detectors)

    async def _do_initialize(self) -> None:
        await self._initialize_detectors()

    async def _initialize_detectors(self) -> None:
        """Build one `MicroWakeWord` per configured wake word + the shared feature extractor."""
        pmw = safe_import('pymicro_wakeword')
        if pmw is None:
            raise ImportError("pymicro-wakeword not installed (extra: wake-tflite)")

        self._features = pmw.MicroWakeWordFeatures()
        self._detectors = []
        self._detector_words = []

        for spec in self.wake_word_specs:
            detector = await self._build_detector(pmw, spec)
            if detector is not None:
                self._detectors.append(detector)
                self._detector_words.append(spec["name"])

        if not self._detectors:
            raise RuntimeError(
                f"No microWakeWord model resolved for wake words {self.wake_words!r}"
            )
        logger.info("microWakeWord ready: %d detector(s) for %s", len(self._detectors), self._detector_words)

    async def _build_detector(self, pmw: Any, spec: Dict[str, Any]) -> Optional[Any]:
        """Resolve a wake word's `model` ref to a `MicroWakeWord` — the 4-rung chain (ASSET-5)."""
        model_ref = str(spec["model"] or spec["name"])

        # 1) Local manifest path (pre-release testing of a just-trained model). No copy, no download.
        if model_ref.endswith(".json") and Path(model_ref).exists():
            return pmw.MicroWakeWord.from_config(model_ref)

        # 2) Built-in — the four stock EN packs inside the pymicro-wakeword wheel (zero download,
        #    byte-identical to the esphome v2 repo). Check the model ref, then the label.
        for candidate in (model_ref, spec["name"]):
            member = _BUILTIN_ALIASES.get(str(candidate).lower())
            if member is not None:
                return pmw.MicroWakeWord.from_builtin(pmw.Model[member])

        # 3) v2 manifest URL (microwakeword.com, a not-yet-cataloged HF repo, ...). The .tflite is
        #    the manifest's sibling (v2 manifests reference it relative), fetched with it into
        #    models/microwakeword/<name>/ via the AssetManager (staging + atomic rename).
        if model_ref.startswith(("http://", "https://")) and model_ref.endswith(".json"):
            stem = model_ref.rsplit("/", 1)[-1][:-len(".json")]
            files = {
                f"{stem}.json": model_ref,
                f"{stem}.tflite": model_ref[:-len(".json")] + ".tflite",
            }
            try:
                pack_dir = await self.asset_manager.download_model_files(
                    "microwakeword", spec["name"], files)
                return pmw.MicroWakeWord.from_config(Path(pack_dir) / f"{stem}.json")
            except Exception as e:
                logger.warning("microWakeWord: failed to fetch pack for '%s' from %s: %s",
                               spec["name"], model_ref, e)
                return None

        # 4) Released catalog (asset-managed pack under models/microwakeword/<word>/).
        try:
            pack_dir = Path(await self.asset_manager.download_model("microwakeword", model_ref))
            manifest = next(pack_dir.glob("*.json"), None)
            if manifest is not None:
                return pmw.MicroWakeWord.from_config(manifest)
        except ValueError as e:  # not in the catalog — expected for unknown words, stay quiet
            logger.debug("No catalog microWakeWord model for '%s': %s", model_ref, e)
        except Exception as e:  # IS in the catalog but the fetch/load failed — must be visible
            logger.warning("microWakeWord: catalog pack for '%s' failed to fetch/load: %s",
                           model_ref, e)

        logger.warning("microWakeWord: no built-in, URL, or catalog model for '%s' (%s) — skipped",
                       spec["name"], model_ref)
        return None

    async def detect_wake_word(self, audio_data: AudioData) -> WakeWordResult:
        """Stream PCM through every detector in 10 ms chunks; report the first wake-word hit."""
        if not self._detectors or self._features is None:
            return WakeWordResult(detected=False, confidence=0.0, timestamp=audio_data.timestamp)

        self._pcm_buffer.extend(self._to_pcm_bytes(audio_data.data))

        detected_word: Optional[str] = None
        while len(self._pcm_buffer) >= _CHUNK_BYTES:
            chunk = bytes(self._pcm_buffer[:_CHUNK_BYTES])
            del self._pcm_buffer[:_CHUNK_BYTES]
            for features in self._features.process_streaming(chunk):
                for word, detector in zip(self._detector_words, self._detectors):
                    if detector.process_streaming(features):
                        detected_word = word
                        break
                if detected_word:
                    break
            if detected_word:
                break

        if detected_word is None:
            return WakeWordResult(detected=False, confidence=0.0, timestamp=audio_data.timestamp)

        # Reset streaming state so the same utterance can't re-trigger immediately.
        self._reset_streams()
        return WakeWordResult(
            detected=True, confidence=1.0, word=detected_word, timestamp=audio_data.timestamp,
            metadata={"provider": "microwakeword", "wake_word": detected_word},
        )

    @staticmethod
    def _to_pcm_bytes(data: Any) -> bytes:
        """Coerce AudioData payload to 16-bit mono PCM bytes (numpy-free fast path for bytes)."""
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
        np = safe_import('numpy')
        if np is not None:
            return np.asarray(data, dtype=np.int16).tobytes()
        return bytes(data)

    def _reset_streams(self) -> None:
        self._pcm_buffer.clear()
        for detector in self._detectors:
            detector.reset()
        if self._features is not None:
            self._features.reset()

    def get_supported_wake_words(self) -> List[str]:
        """Built-ins + the released catalog + any custom words that resolved to a detector."""
        builtin = set(_BUILTIN_ALIASES)
        catalog = set(self._get_default_model_urls())
        return sorted(builtin | catalog | set(self._detector_words))

    def get_supported_sample_rates(self) -> List[int]:
        return [16000]

    def get_default_sample_rate(self) -> int:
        return 16000

    def supports_resampling(self) -> bool:
        # The micro frontend expects exactly 16 kHz — resampling is handled upstream in the pipeline.
        return False

    def get_default_channels(self) -> int:
        return 1

    def get_capabilities(self) -> Dict[str, Any]:
        capabilities = super().get_capabilities()
        capabilities.update({
            "custom_models": True,
            "streaming": True,
            "offline": True,
            "low_power": True,
            "unified_with_esp32": True,   # same artifact runs on-device and server-side
            "sample_rates": [16000],
            "formats": ["pcm16"],
            "inference_framework": "pymicro-wakeword (tflite)",
            "model_format": ".tflite",
        })
        return capabilities

    async def cleanup(self) -> None:
        for detector in self._detectors:
            try:
                detector.close()
            except Exception:
                pass
        self._detectors = []
        self._detector_words = []
        self._features = None
        self._pcm_buffer.clear()
        logger.info("microWakeWord cleaned up")

    # --- Build / asset metadata -----------------------------------------------------------------
    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        """microWakeWord on a bundled tflite C lib + micro frontend (no tflite-runtime); extra: wake-tflite."""
        return ["wake-tflite"]  # Build extra: wake-tflite

    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        return {"linux.ubuntu": [], "linux.alpine": [], "macos": [], "windows": []}
    @classmethod
    def get_supported_architectures(cls) -> List[str]:
        return ["x86_64", "aarch64"]  # pymicro-wakeword has no armv7 wheel (ARCH-24 T3)

    @classmethod
    def _get_default_extension(cls) -> str:
        return ""  # each model is a DIRECTORY pack: microwakeword/<word>/<word>.json + .tflite (ASSET-5)

    @classmethod
    def _get_default_directory(cls) -> str:
        return "microwakeword"

    @classmethod
    def _get_default_credentials(cls) -> List[str]:
        return []

    @classmethod
    def _get_default_cache_types(cls) -> List[str]:
        return ["models"]

    @classmethod
    def _get_default_model_urls(cls) -> Dict[str, Any]:
        """The RELEASED wake-word catalog — v2 two-file packs (manifest + sibling .tflite),
        one line per validated word (`docs/design/wakeword_models.md` D-2 rung 4).

        The four stock EN words are NOT here: they ship inside the pymicro-wakeword wheel
        (`from_builtin`, rung 2). RU words come from the in-house training factory
        (~/development/wakeword-training) published to the user's HF repos; each new validated
        word («Валера», «Наташа», ...) is a one-line addition here, filed as its consume-task.
        """
        def hf_ru(word: str, note: str) -> Dict[str, Any]:
            base = f"https://huggingface.co/droman42/microwakeword-{word}-ru/resolve/main"
            return {
                "files": {f"{word}.json": f"{base}/{word}.json",
                          f"{word}.tflite": f"{base}/{word}.tflite"},
                "size": "~150 KB",
                "description": note,
            }
        return {
            "irina": hf_ru("irina", "Russian wake word «Ирина» (CC BY-NC-SA; validated 2026-07-04)"),
        }
