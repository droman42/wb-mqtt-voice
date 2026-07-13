"""
sherpa-onnx ASR provider — ONNX inference for the alphacep VOSK Zipformer2 family.

Part of ARCH-10 / PR-1 (see docs/design/onnx_inference_layer.md). Runs **alongside**
the Kaldi `vosk` and torch `whisper` providers — a config choice, not a replacement.

Model families on one provider/runtime, selected by config `model_type`:
- `vosk-transducer`      → `OfflineRecognizer.from_transducer` (encoder/decoder/joiner/tokens, offline)
- `whisper`             → `OfflineRecognizer.from_whisper`    (encoder/decoder/tokens, no joiner)
- `vosk-streaming` (RU) / `zipformer-streaming` (EN) → `OnlineRecognizer.from_transducer` (online/streaming)

Whisper-ONNX (PR-2) drops torch from 64-bit ASR images that don't otherwise need it.

Design notes baked in here:
- **numpy-free** audio conversion (stdlib `array`) — the armv7 image installs no numpy (it is not a
  base dependency; PiWheels' armv7 wheel needs a system libopenblas nothing ships — BUG-33).
- multi-file **model packs** (encoder/decoder/joiner/tokens) resolved + first-run
  downloaded via the AssetManager into the mounted asset folder (§6).
- a small **inference policy** (num_threads per platform, §5.2b).
- the model load (~38 s onnxruntime graph init on armv7) is absorbed by `warm_up()` when
  `preload_models=True` (the `embedded-armv7` profile sets it).
"""

import array
import asyncio
import io
import logging
import wave
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Tuple

from .base import ASRProvider
from ...utils.inference_policy import InferencePolicy

logger = logging.getLogger(__name__)


# ARCH-24 T5: the inference policy moved to `utils.inference_policy` and is now shared by the
# sherpa-onnx ASR, VAD and Piper-TTS providers. `SherpaInferencePolicy` kept as a back-compat alias.
SherpaInferencePolicy = InferencePolicy


class SherpaOnnxASRProvider(ASRProvider):
    """Offline ASR via sherpa-onnx (k2-fsa) running VOSK Zipformer2 ONNX models."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        from ...core.assets import get_asset_manager
        self.asset_manager = get_asset_manager()

        # Model pack selection (id resolves against _get_default_model_urls()).
        self.model_id: str = config.get("model", "vosk-model-small-ru")
        # Model family: "vosk-transducer" (RU Zipformer2, offline) | "whisper" (whisper-onnx) |
        # streaming transducer ("vosk-streaming" RU | "zipformer-streaming" EN — same online path).
        self.model_type: str = config.get("model_type", "vosk-transducer")

        self.default_language: str = config.get("default_language", "ru")
        self.sample_rate: int = config.get("sample_rate", 16000)
        self.feature_dim: int = config.get("feature_dim", 80)
        self.decoding_method: str = config.get("decoding_method", "greedy_search")
        self.policy = InferencePolicy.for_platform(config.get("num_threads"))
        self._is_streaming = self.model_type in (
            "vosk-streaming", "vosk-streaming-transducer", "zipformer-streaming", "streaming-transducer")

        self._recognizer: Any = None
        # BUG-13: the boot warm-up task and the first request used to RACE _load_recognizer
        # (the None-check guards only the entry, not the whole download+build body) — two
        # recognizer instances, 2× model RAM. One loads, the other waits.
        self._load_lock = asyncio.Lock()

        preload_models = config.get("preload_models", False)
        if preload_models:
            # Pay the ~38 s graph-init at boot, off the first-utterance critical path.
            self._warmup_task = asyncio.create_task(self.warm_up())  # QUAL-58: hold the ref (unreferenced tasks are GC-cancellable mid-load)

    # ------------------------------------------------------------------ identity
    def get_provider_name(self) -> str:
        return "sherpa_onnx"

    # ----------------------------------------------------------------- lifecycle
    async def is_available(self) -> bool:
        try:
            import sherpa_onnx  # noqa: F401
        except ImportError:
            logger.warning("sherpa-onnx not installed — sherpa_onnx ASR provider unavailable")
            return False
        # Available if the pack is present locally or downloadable (descriptor configured).
        # Key on get_provider_name(), not a literal, so subclasses (e.g. sherpa_moonshine) resolve
        # their own asset namespace rather than the base's.
        provider = self.get_provider_name()
        pack_dir = self.asset_manager.get_model_path(provider, self.model_id)
        if pack_dir.exists():
            return True
        return bool(self.asset_manager.get_model_info(provider, self.model_id))

    async def _load_recognizer(self) -> None:
        """Load once, under the lock — concurrent callers (warm-up + first request) wait
        instead of double-loading (BUG-13). Subclasses override :meth:`_do_load_recognizer`."""
        if self._recognizer is not None:
            return
        async with self._load_lock:
            if self._recognizer is not None:
                return
            await self._do_load_recognizer()

    async def _do_load_recognizer(self) -> None:
        import sherpa_onnx

        # First-run download of the multi-file pack into the mounted asset folder (§6).
        # The descriptor declares its member set (transducer=4 files, whisper=3).
        files = await self.asset_manager.download_model_pack(self.get_provider_name(), self.model_id)

        build: Callable[[], Any]
        if self.model_type == "vosk-transducer":
            def build_transducer():
                return sherpa_onnx.OfflineRecognizer.from_transducer(
                    encoder=str(files["encoder"]),
                    decoder=str(files["decoder"]),
                    joiner=str(files["joiner"]),
                    tokens=str(files["tokens"]),
                    num_threads=self.policy.num_threads,
                    sample_rate=self.sample_rate,
                    feature_dim=self.feature_dim,
                    decoding_method=self.decoding_method,
                )
            build = build_transducer
        elif self.model_type in ("whisper", "whisper-onnx"):
            # Whisper has no joiner and its own fixed frontend (no sample_rate/feature_dim
            # here). "" language → whisper's own language detection.
            language = "" if self.default_language in (None, "", "auto") else self.default_language

            def build_whisper():
                return sherpa_onnx.OfflineRecognizer.from_whisper(
                    encoder=str(files["encoder"]),
                    decoder=str(files["decoder"]),
                    tokens=str(files["tokens"]),
                    num_threads=self.policy.num_threads,
                    decoding_method=self.decoding_method,
                    language=language,
                    task="transcribe",
                )
            build = build_whisper
        elif self._is_streaming:
            # Online/streaming transducer (chunk-wise encoder). Endpoint detection on so
            # transcribe_stream can segment utterances live.
            def build_streaming():
                return sherpa_onnx.OnlineRecognizer.from_transducer(
                    tokens=str(files["tokens"]),
                    encoder=str(files["encoder"]),
                    decoder=str(files["decoder"]),
                    joiner=str(files["joiner"]),
                    num_threads=self.policy.num_threads,
                    sample_rate=self.sample_rate,
                    feature_dim=self.feature_dim,
                    decoding_method=self.decoding_method,
                    enable_endpoint_detection=True,
                )
            build = build_streaming
        else:
            raise NotImplementedError(
                f"model_type '{self.model_type}' not supported "
                "(use 'vosk-transducer', 'whisper', 'vosk-streaming', or 'zipformer-streaming')"
            )

        # onnxruntime graph init is blocking (~38 s on armv7) — keep it off the loop.
        self._recognizer = await asyncio.to_thread(build)
        logger.info(
            f"Loaded sherpa-onnx recognizer: model={self.model_id} "
            f"type={self.model_type} threads={self.policy.num_threads}"
        )

    async def warm_up(self) -> None:
        try:
            logger.info(f"Warming up sherpa-onnx ASR model: {self.model_id}")
            await self._load_recognizer()
            logger.info(f"sherpa-onnx model {self.model_id} warmed up")
        except Exception as e:
            # Don't raise — allow lazy loading on first transcription.
            logger.error(f"Failed to warm up sherpa-onnx model: {e}")

    # ------------------------------------------------------------- transcription
    async def transcribe_audio(self, audio_data: bytes, **kwargs) -> str:
        try:
            if self._recognizer is None:
                await self._load_recognizer()

            samples, rate = self._to_float_samples(
                audio_data, kwargs.get("sample_rate", self.sample_rate)
            )
            if not samples:
                return ""

            decode = self._decode_online_oneshot if self._is_streaming else self._decode
            text = await asyncio.to_thread(decode, samples, rate)
            return text.strip()
        except Exception as e:
            logger.error(f"sherpa-onnx transcription error: {e}")
            return ""

    def _decode(self, samples: List[float], rate: int) -> str:
        """Offline recognizer: decode the whole buffer at once."""
        stream = self._recognizer.create_stream()
        stream.accept_waveform(rate, samples)
        self._recognizer.decode_stream(stream)
        return stream.result.text or ""

    def _decode_online_oneshot(self, samples: List[float], rate: int) -> str:
        """Online recognizer over a complete buffer: feed, pad tail, finish, drain."""
        rec = self._recognizer
        stream = rec.create_stream()
        stream.accept_waveform(rate, samples)
        stream.accept_waveform(rate, [0.0] * int(rate * 0.3))  # tail padding flushes the last words
        stream.input_finished()
        while rec.is_ready(stream):
            rec.decode_stream(stream)
        return rec.get_result(stream) or ""

    @property
    def supports_streaming(self) -> bool:
        """Real incremental recognition + server-side endpointing exists only for the
        streaming model types (`OnlineRecognizer`)."""
        return self._is_streaming

    async def transcribe_stream(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[str]:
        """Text-only view of the stream (partials + finalized segments). Thin wrapper over
        :meth:`transcribe_stream_segments` for callers that don't need the final/partial flag."""
        async for text, _is_final in self.transcribe_stream_segments(audio_stream):
            yield text

    async def transcribe_stream_segments(
        self, audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[Tuple[str, bool]]:
        """``(text, is_final)`` per segment.

        For an **offline** model_type: buffer the stream and emit one final segment
        (the base default). For a **streaming** model_type (`vosk-streaming`): feed chunks
        to the `OnlineRecognizer`, emitting partials (``is_final=False``) and a finalized
        segment (``is_final=True``) on each model endpoint, plus an EOF finalize when the
        stream ends.
        """
        if not self._is_streaming:
            async for seg in super().transcribe_stream_segments(audio_stream):
                yield seg
            return

        if self._recognizer is None:
            await self._load_recognizer()
        rec: Any = self._recognizer
        stream = rec.create_stream()
        last = ""

        async for chunk in audio_stream:
            samples, rate = self._to_float_samples(chunk, self.sample_rate)
            if not samples:
                continue

            def step():
                stream.accept_waveform(rate, samples)
                while rec.is_ready(stream):
                    rec.decode_stream(stream)
                return (rec.get_result(stream) or ""), rec.is_endpoint(stream)

            text, endpoint = await asyncio.to_thread(step)
            if endpoint:
                if text:
                    yield text.strip(), True
                rec.reset(stream)
                last = ""
            elif text and text != last:
                yield text.strip(), False
                last = text

        def finalize():
            stream.input_finished()
            while rec.is_ready(stream):
                rec.decode_stream(stream)
            return rec.get_result(stream) or ""

        final = await asyncio.to_thread(finalize)
        if final and final.strip() != last:
            yield final.strip(), True

    @staticmethod
    def _to_float_samples(data: bytes, default_rate: int):
        """Raw 16-bit PCM (or a WAV blob) -> (float list in [-1, 1], sample_rate).

        numpy-free (stdlib `array`/`wave`) so it runs on armv7, which installs no numpy.
        """
        if not data:
            return [], default_rate
        # Accept a WAV container too (e.g. file-upload endpoints), not just raw PCM.
        if data[:4] == b"RIFF":
            with wave.open(io.BytesIO(data), "rb") as w:
                rate = w.getframerate()
                frames = w.readframes(w.getnframes())
        else:
            rate = default_rate
            frames = data
        arr = array.array("h")
        arr.frombytes(frames[: len(frames) // 2 * 2])  # int16 pairs; drop a trailing odd byte
        return [s / 32768.0 for s in arr], rate

    # -------------------------------------------------------------- capabilities
    def get_supported_languages(self) -> List[str]:
        if self.model_type in ("whisper", "whisper-onnx"):
            return ["ru", "en", "auto"]  # whisper packs are multilingual
        # transducer / streaming packs are single-language (RU vosk, EN zipformer) — the pack's own.
        return [self.default_language]

    def get_supported_formats(self) -> List[str]:
        return ["pcm16", "wav", "raw"]

    def get_preferred_sample_rates(self) -> List[int]:
        return [16000]

    def supports_sample_rate(self, rate: int) -> bool:
        return rate == 16000  # Zipformer2 feature frontend is trained at 16 kHz

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "languages": self.get_supported_languages(),
            "formats": self.get_supported_formats(),
            "streaming": self._is_streaming,   # true for model_type="vosk-streaming"
            "real_time": self._is_streaming,
            "confidence_scores": False,
            "offline": not self._is_streaming,
            "model_based": True,
        }

    # -------------------------------------------------------- asset / build meta
    @classmethod
    def _get_default_directory(cls) -> str:
        return "sherpa_onnx"

    @classmethod
    def _get_default_cache_types(cls) -> List[str]:
        return ["models", "runtime"]

    @classmethod
    def _get_default_model_urls(cls) -> Dict[str, Any]:
        # Multi-file packs — resolved by AssetManager.download_model_pack via the HF API
        # (picks encoder/decoder/joiner + tokens, int8 preferred). Apache-2.0.
        transducer = ["encoder", "decoder", "joiner", "tokens"]
        whisper = ["encoder", "decoder", "tokens"]  # no joiner
        return {
            "vosk-model-small-ru": {
                "type": "sherpa-pack",
                "repo": "alphacep/vosk-model-small-ru",
                "members": transducer,
                "prefer": "int8",
                "size": "~27MB int8",
            },
            "vosk-model-ru": {
                "type": "sherpa-pack",
                "repo": "alphacep/vosk-model-ru",
                "members": transducer,
                "prefer": "int8",
                "size": "large (64-bit only)",
            },
            # Streaming (online) transducer — repo also ships offline int8, so prefer the
            # chunk-wise "chunk64" export. Use with model_type="vosk-streaming".
            "vosk-model-small-streaming-ru": {
                "type": "sherpa-pack",
                "repo": "alphacep/vosk-model-small-streaming-ru",
                "members": transducer,
                "prefer": "chunk64",
                "streaming": True,
                "size": "small streaming",
            },
            # (English armv7 ASR is offline Moonshine — see `sherpa_moonshine.py` / I18N-2. The earlier
            # streaming zipformer-en-20M was rejected: online models drop the utterance head on bounded
            # commands. The `zipformer-streaming` model_type stays here as a generic online-transducer alias.)
            # Whisper exported to ONNX (sherpa-onnx) — multilingual, 64-bit only.
            "whisper-tiny": {
                "type": "sherpa-pack",
                "repo": "csukuangfj/sherpa-onnx-whisper-tiny",
                "members": whisper,
                "prefer": "int8",
                "size": "tiny multilingual",
            },
            "whisper-base": {
                "type": "sherpa-pack",
                "repo": "csukuangfj/sherpa-onnx-whisper-base",
                "members": whisper,
                "prefer": "int8",
                "size": "base multilingual",
            },
            # The aarch64 satellite's ASR (ARCH-24): better Russian than tiny/base, fits the WB8/Pi
            # 4 GB budget (~470 MB int8 on disk, ~0.8 GB RAM). Too big for the armv7 WB7 (vosk-small there).
            "whisper-small": {
                "type": "sherpa-pack",
                "repo": "csukuangfj/sherpa-onnx-whisper-small",
                "members": whisper,
                "prefer": "int8",
                "size": "small multilingual (~470 MB int8, 64-bit only)",
            },
        }

    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        # CONTRACT: pyproject [project.optional-dependencies] GROUP NAME, not a
        # requirement string (build runs `uv sync --extra asr-onnx`). The per-arch
        # version split lives in the extra's PEP 508 markers — including `sherpa-onnx-core`
        # (the native libs/onnxruntime, split out of the main wheel since 1.13) for non-armv7.
        return ["asr-onnx"]

    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        # sherpa-onnx is self-contained: the wheel VENDORS libasound (auditwheel) and onnxruntime
        # comes from the `sherpa-onnx-core` wheel (a Python dep, not a system package) — so import +
        # inference need NO system packages. `libasound2`/`alsa-lib` are kept only as a runtime safety
        # net for actual audio I/O; the capture/playback providers (sounddevice/aplay) own that need.
        # macOS/Windows wheels are fully self-contained (empty lists).
        return {
            "linux.ubuntu": ["libasound2"],
            "linux.alpine": ["alsa-lib"],
            "macos": [],
            "windows": [],
        }
