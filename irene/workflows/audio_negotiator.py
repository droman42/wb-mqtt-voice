"""Audio negotiator — derives the canonical format from config and transforms capture to it once (ARCH-18 PR-3).

Built once at workflow init from the audio config (mic + the audio consumers: VAD / wake / ASR). It derives the
canonical encoding via `utils.audio_negotiation.derive_canonical` — **fatal at startup** if no canonical
satisfies everyone — and then `to_canonical()` transforms each captured frame to it **once** at the input
boundary (via `AudioTranscoder`), recording a trace event. Downstream stages see canonical audio.

The per-party contracts are derived from the *config* sample rates (the authoritative `[asr]`/`[voice_trigger]`
rates + the 16 kHz VAD requirement) — config is the declared contract.
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
        mc = config.inputs.microphone_config
        source = AudioContract([mc.sample_rate], mc.sample_rate, channels=mc.channels)

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

        canonical = derive_canonical(source, consumers)
        logger.info("Audio canonical format negotiated: %dHz/%s/%dch (capture %dHz, %d consumer contract(s))",
                    canonical.rate, canonical.format, canonical.channels, mc.sample_rate, len(consumers))
        return cls(canonical)

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
        """Transform `audio_data` to the canonical format once. No-op if it already matches."""
        if audio_data.sample_rate == self.canonical.rate and audio_data.channels == self.canonical.channels:
            return audio_data
        if audio_data.channels != self.canonical.channels:
            logger.warning("Audio negotiator: channel mismatch %d->%d not converted (mono expected)",
                           audio_data.channels, self.canonical.channels)

        t0 = time.time()
        method = AudioTranscoder.get_optimal_conversion_path(audio_data.sample_rate, self.canonical.rate, "general")
        out = await AudioTranscoder.resample_audio_data(audio_data, self.canonical.rate, method)
        if trace_context:
            trace_context.record_stage(
                "audio_negotiate",
                {"sample_rate": audio_data.sample_rate, "channels": audio_data.channels},
                {"sample_rate": out.sample_rate, "channels": out.channels},
                {"canonical": f"{self.canonical.rate}Hz/{self.canonical.format}",
                 "method": getattr(method, "value", str(method))},
                (time.time() - t0) * 1000.0,
            )
        return out
