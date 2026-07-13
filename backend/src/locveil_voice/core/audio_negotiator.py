"""Audio negotiator — derives the canonical format from config and transforms capture to it once (ARCH-18 PR-3).

Built once at workflow init from the audio config (mic + the audio consumers: VAD / wake / ASR). It derives the
canonical encoding via `utils.audio_negotiation.derive_canonical` — **fatal at startup** if no canonical
satisfies everyone — and then `to_canonical()` transforms each captured frame to it **once** at the input
boundary (via `AudioTranscoder`), recording a trace event. Downstream stages see canonical audio.

Contracts are **declared by the parties**: the enabled input adapters (`audio_contract()`) for the capture, and
the active VAD/wake/ASR providers for the consumers; the authoritative `[asr]`/`[voice_trigger]` config rate
overrides a provider's preference, and an optional `[audio] canonical_*` pin overrides the derived canonical.
"""

import array
import logging
import sys
import time
from typing import Optional

from ..config.models import CoreConfig
from .trace_context import TraceContext
from ..utils.audio_data import AudioData
from ..utils.audio_helpers import AudioTranscoder
from ..utils.audio_negotiation import AudioContract, CanonicalFormat, derive_canonical

logger = logging.getLogger(__name__)

_VAD_RATE = 16000  # the VAD providers are 16 kHz
# ARCH-18 PR-4c: default OUTPUT sink when nothing's declared — full CD (44.1 kHz / pcm16 / stereo).
_CD_SINK = AudioContract([44100], 44100, ["pcm16"], "pcm16", 2)


class AudioNegotiator:
    """Holds the negotiated canonical (input) format + the output sink, and transforms audio to each."""

    def __init__(self, canonical: CanonicalFormat):
        self.canonical = canonical
        self.output_sink: AudioContract = _CD_SINK  # ARCH-18 PR-4c; resolved in from_pipeline

    @classmethod
    def from_pipeline(cls, config: CoreConfig, *, vad_provider=None, wake_provider=None,
                      asr_provider=None, audio_provider=None) -> "AudioNegotiator":
        """Capability-driven build (ARCH-18): the **active providers declare** their `AudioContract`s, and
        the operator's AUTHORITATIVE `[asr]`/`[voice_trigger]` sample-rate (if set) overrides the provider's
        preference. Falls back to the config-only contract for any party whose provider isn't available.
        Raises `AudioNegotiationError` (fatal) if no canonical satisfies everyone.
        """
        source = cls._source_contract(config)

        labeled = []  # (label, contract) — kept for the startup summary (§7)
        if config.vad.enabled:
            labeled.append(("vad", vad_provider.audio_contract() if vad_provider is not None
                            else AudioContract([_VAD_RATE], _VAD_RATE)))
        if config.voice_trigger.enabled:
            base = wake_provider.audio_contract() if wake_provider is not None else None
            labeled.append(("wake", cls._with_override(base, config.voice_trigger.sample_rate,
                                                       config.voice_trigger.channels)))
        if config.asr.enabled:
            base = asr_provider.audio_contract() if asr_provider is not None else None
            labeled.append(("asr", cls._with_override(base, config.asr.sample_rate, config.asr.channels)))

        consumers = [c for _, c in labeled]
        derived = derive_canonical(source, consumers)
        canonical = cls._apply_config_pin(config, source, consumers, derived)
        cls._log_startup_summary(source, labeled, canonical)
        neg = cls(canonical)
        neg.output_sink = cls._resolve_output_sink(config, audio_provider)
        return neg

    @staticmethod
    def _resolve_output_sink(config: CoreConfig, audio_provider) -> AudioContract:
        """The local OUTPUT sink (ARCH-18 PR-4c): the active audio provider's declared capability, with an
        optional `[audio]` `output_rate`/`output_channels` override; **CD** when neither specifies."""
        base = audio_provider.audio_contract() if audio_provider is not None else _CD_SINK
        ac = getattr(config, "audio", None)
        rate = getattr(ac, "output_rate", None) or max(base.supported_rates)
        channels = getattr(ac, "output_channels", None) or base.channels
        return AudioContract([rate], rate, ["pcm16"], "pcm16", channels)

    @staticmethod
    def _log_startup_summary(source, labeled, canonical: CanonicalFormat) -> None:
        """§7 one-time startup summary: the negotiated canonical + EVERY party's declared contract."""
        lines = [f"Audio pipeline canonical = {canonical.rate}Hz/{canonical.format}/{canonical.channels}ch",
                 f"  capture(source): rates={source.supported_rates} ch={source.channels}"]
        for label, c in labeled:
            lines.append(f"  consumer[{label}]: rates={c.supported_rates} fmt={c.preferred_format} ch={c.channels}")
        logger.info("\n".join(lines))

    @staticmethod
    def _source_contract(config: CoreConfig) -> AudioContract:
        """The capture contract = the ENABLED input adapters' declared delivery (mirrors their
        `audio_contract()`): mic at its configured rate, web/ESP32-satellite at 16 kHz. The canonical must be
        reachable from EVERY enabled input (downsample only), so the binding rate is the lowest of them."""
        inp = config.inputs
        rates = []
        if getattr(inp, "microphone", False):
            rates.append(inp.microphone_config.sample_rate)
        if getattr(inp, "web", False):
            rates.append(16000)  # WebInput.audio_contract(): the web/satellite stream is 16 kHz
        if not rates:
            rates.append(inp.microphone_config.sample_rate)
        rate = min(rates)
        return AudioContract([rate], rate, ["pcm16"], "pcm16", inp.microphone_config.channels)

    @staticmethod
    def _apply_config_pin(config: CoreConfig, source, consumers, derived: CanonicalFormat) -> CanonicalFormat:
        """Apply an optional operator pin from `[audio] canonical_*` over the derived canonical (partial pins
        fill from the derived value), validated for feasibility (fatal if infeasible)."""
        ac = getattr(config, "audio", None)
        if not ac or not (ac.canonical_rate or ac.canonical_format or ac.canonical_channels):
            return derived
        pinned = CanonicalFormat(ac.canonical_rate or derived.rate,
                                 ac.canonical_format or derived.format,
                                 ac.canonical_channels or derived.channels)
        return derive_canonical(source, consumers, pin=pinned)  # validates; raises if infeasible

    @staticmethod
    def _with_override(base: Optional[AudioContract], authoritative_rate, channels) -> AudioContract:
        """Apply the AUTHORITATIVE config rate over a provider's declared contract (operator pins it). If the
        provider didn't declare one, fall back to the config rate alone."""
        fmts = base.supported_formats if base else ["pcm16"]
        pref_fmt = base.preferred_format if base else "pcm16"
        if authoritative_rate:
            return AudioContract([authoritative_rate], authoritative_rate, fmts, pref_fmt, channels)
        if base is not None:
            return base
        return AudioContract([_VAD_RATE], _VAD_RATE, fmts, pref_fmt, channels)

    @classmethod
    def from_config(cls, config: CoreConfig) -> "AudioNegotiator":
        """Config-only build (no live providers) — the simple path used for early validation + tests."""
        return cls.from_pipeline(config)

    async def to_canonical(self, audio_data: AudioData,
                           trace_context: Optional[TraceContext] = None) -> AudioData:
        """Transform `audio_data` to the canonical format once — downmix (channels) then resample (rate).
        No-op if it already matches."""
        if audio_data.sample_rate == self.canonical.rate and audio_data.channels == self.canonical.channels:
            return audio_data

        t0 = time.time()
        out = audio_data
        method = "none"
        # 1) channels — downmix to the canonical count (we never up-mix to invent channels)
        if out.channels != self.canonical.channels:
            if self.canonical.channels == 1 and out.channels > 1:
                out = self._downmix_to_mono(out)
            else:
                logger.warning("Audio negotiator: cannot up-mix %d->%d channels; leaving as-is",
                               out.channels, self.canonical.channels)
        # 2) rate — resample to the canonical rate
        if out.sample_rate != self.canonical.rate:
            conv = AudioTranscoder.get_optimal_conversion_path(out.sample_rate, self.canonical.rate, "general")
            method = getattr(conv, "value", str(conv))
            out = await AudioTranscoder.resample_audio_data(out, self.canonical.rate, conv)

        if trace_context:
            trace_context.record_stage(
                "audio_negotiate",
                {"sample_rate": audio_data.sample_rate, "channels": audio_data.channels},
                {"sample_rate": out.sample_rate, "channels": out.channels},
                {"canonical": f"{self.canonical.rate}Hz/{self.canonical.format}/{self.canonical.channels}ch",
                 "method": method},
                (time.time() - t0) * 1000.0,
            )
        return out

    async def to_sink(self, audio_data: AudioData, sink: Optional[AudioContract] = None,
                      trace_context: Optional[TraceContext] = None) -> AudioData:
        """Conform a producer's audio (e.g. TTS) DOWN to an output `sink`'s capability (ARCH-18 PR-4c) —
        the OUTPUT mirror of `to_canonical`. `sink` defaults to the resolved local output sink (CD if
        unspecified). Conform-down ONLY: any device plays lower, so pass through when the producer is `<=`
        the sink, and downsample/downmix only when it exceeds it; never upsample."""
        sink = sink or self.output_sink
        sink_rate = max(sink.supported_rates)
        if audio_data.sample_rate <= sink_rate and audio_data.channels <= sink.channels:
            return audio_data  # already playable by the sink

        t0 = time.time()
        out = audio_data
        method = "none"
        if out.channels > sink.channels and sink.channels == 1:
            out = self._downmix_to_mono(out)
        if out.sample_rate > sink_rate:
            conv = AudioTranscoder.get_optimal_conversion_path(out.sample_rate, sink_rate, "general")
            method = getattr(conv, "value", str(conv))
            out = await AudioTranscoder.resample_audio_data(out, sink_rate, conv)

        if trace_context:
            trace_context.record_stage(
                "audio_output_conform",
                {"sample_rate": audio_data.sample_rate, "channels": audio_data.channels},
                {"sample_rate": out.sample_rate, "channels": out.channels},
                {"sink": f"<={sink_rate}Hz/{sink.channels}ch", "method": method},
                (time.time() - t0) * 1000.0,
            )
        return out

    @staticmethod
    def _downmix_to_mono(audio_data: AudioData) -> AudioData:
        """Average interleaved int16 channels down to mono, preserving the AudioData subtype.

        numpy-free (stdlib `array`): this sits on the live audio path, and numpy is not installed on
        the armv7 image (BUG-33) — a lazy `import numpy` here would have raised on the first
        multi-channel frame instead of at startup.
        """
        ch = audio_data.channels
        arr = array.array("h")
        arr.frombytes(audio_data.data)
        if sys.byteorder == "big":
            arr.byteswap()  # 'h' is native-endian; the PCM contract is little-endian
        if ch > 1:
            # int(x / ch), not x // ch — matches numpy's mean().astype(int16) truncation toward zero
            mixed = array.array("h", (int(sum(arr[i:i + ch]) / ch) for i in range(0, len(arr) - ch + 1, ch)))
            arr = mixed
        if sys.byteorder == "big":
            arr.byteswap()
        return type(audio_data)(data=arr.tobytes(), timestamp=audio_data.timestamp,
                                sample_rate=audio_data.sample_rate, channels=1)
