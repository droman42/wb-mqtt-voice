"""Audio negotiator — derives the canonical format from config and transforms capture to it once (ARCH-18 PR-3).

Built once at workflow init from the audio config (mic + the audio consumers: VAD / wake / ASR). It derives the
canonical encoding via `utils.audio_negotiation.derive_canonical` — **fatal at startup** if no canonical
satisfies everyone — and then `to_canonical()` transforms each captured frame to it **once** at the input
boundary (via `AudioTranscoder`), recording a trace event. Downstream stages see canonical audio.

Contracts are **declared by the parties**: the enabled input adapters (`audio_contract()`) for the capture, and
the active VAD/wake/ASR providers for the consumers; the authoritative `[asr]`/`[voice_trigger]` config rate
overrides a provider's preference, and an optional `[audio] canonical_*` pin overrides the derived canonical.
"""

import logging
import time
from typing import Optional

from ..config.models import CoreConfig
from ..core.trace_context import TraceContext
from ..utils.audio_data import AudioData
from ..utils.audio_helpers import AudioTranscoder
from ..utils.audio_negotiation import AudioContract, CanonicalFormat, derive_canonical

logger = logging.getLogger(__name__)

_VAD_RATE = 16000  # the VAD providers are 16 kHz


class AudioNegotiator:
    """Holds the negotiated canonical format and transforms capture to it once."""

    def __init__(self, canonical: CanonicalFormat):
        self.canonical = canonical

    @classmethod
    def from_pipeline(cls, config: CoreConfig, *, vad_provider=None, wake_provider=None,
                      asr_provider=None) -> "AudioNegotiator":
        """Capability-driven build (ARCH-18): the **active providers declare** their `AudioContract`s, and
        the operator's AUTHORITATIVE `[asr]`/`[voice_trigger]` sample-rate (if set) overrides the provider's
        preference. Falls back to the config-only contract for any party whose provider isn't available.
        Raises `AudioNegotiationError` (fatal) if no canonical satisfies everyone.
        """
        source = cls._source_contract(config)

        consumers = []
        if config.vad.enabled:
            consumers.append(vad_provider.audio_contract() if vad_provider is not None
                             else AudioContract([_VAD_RATE], _VAD_RATE))
        if config.voice_trigger.enabled:
            base = wake_provider.audio_contract() if wake_provider is not None else None
            consumers.append(cls._with_override(base, config.voice_trigger.sample_rate,
                                                config.voice_trigger.channels))
        if config.asr.enabled:
            base = asr_provider.audio_contract() if asr_provider is not None else None
            consumers.append(cls._with_override(base, config.asr.sample_rate, config.asr.channels))

        derived = derive_canonical(source, consumers)
        canonical = cls._apply_config_pin(config, source, consumers, derived)
        logger.info("Audio canonical format negotiated: %dHz/%s/%dch (capture<=%dHz, %d consumer contract(s))",
                    canonical.rate, canonical.format, canonical.channels, max(source.supported_rates), len(consumers))
        return cls(canonical)

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

    @staticmethod
    def _downmix_to_mono(audio_data: AudioData) -> AudioData:
        """Average interleaved int16 channels down to mono, preserving the AudioData subtype."""
        import numpy as np
        arr = np.frombuffer(audio_data.data, dtype=np.int16)
        if audio_data.channels > 1:
            arr = arr.reshape(-1, audio_data.channels).mean(axis=1).astype(np.int16)
        return type(audio_data)(data=arr.tobytes(), timestamp=audio_data.timestamp,
                                sample_rate=audio_data.sample_rate, channels=1)
