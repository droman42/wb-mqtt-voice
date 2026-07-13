"""Audio format negotiation — the canonical-format derivation (ARCH-18 PR-3).

The audio pipeline carries ONE canonical encoding (rate / format / channels); the capture is transformed to
it once at the input boundary, and every consumer (VAD, wake, ASR) sees canonical. The canonical is **derived**
as the common denominator of the parties' declared `AudioContract`s — the format all consumers require that
the capture can be brought *down* to (downsample / downmix / reformat; never upsample to invent data). If no
canonical satisfies everyone, that's a **fatal config error** at startup (`AudioNegotiationError`).

This module is the pure logic only (lives in `utils`, no upward deps). The per-utterance transform + trace
events are wired in the workflow layer; the `AudioTranscoder` does the actual conversion.
"""

from dataclasses import dataclass, field
from typing import List, Optional


class AudioNegotiationError(Exception):
    """No canonical audio format can satisfy every party (a fatal startup misconfiguration)."""


@dataclass
class AudioContract:
    """What an audio party can deliver (a capture source) or needs (a consumer: VAD / wake / ASR)."""
    supported_rates: List[int]
    preferred_rate: int
    supported_formats: List[str] = field(default_factory=lambda: ["pcm16"])
    preferred_format: str = "pcm16"
    channels: int = 1

    def __post_init__(self) -> None:
        if not self.supported_rates:
            raise ValueError("AudioContract.supported_rates must be non-empty")


@dataclass(frozen=True)
class CanonicalFormat:
    """The single internal audio encoding the pipeline carries."""
    rate: int
    format: str
    channels: int


def derive_canonical(source: AudioContract,
                     consumers: List[AudioContract],
                     pin: Optional[CanonicalFormat] = None) -> CanonicalFormat:
    """Derive the canonical format from the capture `source` + the `consumers`' contracts.

    - **rate**: the highest rate every consumer supports that the source can be brought *down* to
      (`<= max(source rates)`). One-directional — we never upsample.
    - **channels**: the consumers' channel need (typically mono), if the source has at least that many.
    - **format**: a format all consumers accept (int16 preferred; int16↔float32 are lossless either way).

    An optional `pin` (operator override) is validated against the same feasibility and used as-is if it holds.
    Raises `AudioNegotiationError` if no canonical satisfies everyone.
    """
    if not consumers:
        # No consumers (e.g. text pipeline) — canonical is just what the source prefers.
        return CanonicalFormat(source.preferred_rate, source.preferred_format, source.channels)

    source_max_rate = max(source.supported_rates)

    # --- rate ---
    common_rates = set(consumers[0].supported_rates)
    for c in consumers[1:]:
        common_rates &= set(c.supported_rates)
    feasible = sorted(r for r in common_rates if r <= source_max_rate)
    if not feasible:
        raise AudioNegotiationError(
            f"No common consumer rate is reachable from the capture (source max {source_max_rate} Hz; "
            f"consumer rate sets {[c.supported_rates for c in consumers]}). Upsampling is not allowed."
        )
    rate = max(feasible)

    # --- channels --- (consumers need at most this; the source must have >= that many to downmix)
    need_channels = max(c.channels for c in consumers)
    if source.channels < need_channels:
        raise AudioNegotiationError(
            f"Consumers need {need_channels} channel(s) but the capture provides {source.channels}."
        )
    channels = need_channels

    # --- format --- a FREE pick: int16↔float32 are losslessly inter-convertible, so a consumer that needs
    # float32 simply converts from the canonical at its own boundary. Default to the compact pcm16 (the
    # capture default); never a negotiation failure for these two formats.
    fmt = "pcm16"

    derived = CanonicalFormat(rate, fmt, channels)

    # --- operator pin --- (must itself be feasible for everyone)
    if pin is not None:
        _validate_pin(pin, source, consumers, source_max_rate)
        return pin
    return derived


def _validate_pin(pin: CanonicalFormat, source: AudioContract,
                  consumers: List[AudioContract], source_max_rate: int) -> None:
    if pin.rate > source_max_rate:
        raise AudioNegotiationError(f"Pinned rate {pin.rate} Hz exceeds the capture's {source_max_rate} Hz "
                                    f"(upsampling is not allowed).")
    for c in consumers:
        if pin.rate not in c.supported_rates:
            raise AudioNegotiationError(f"Pinned rate {pin.rate} Hz is not accepted by a consumer "
                                        f"(supports {c.supported_rates}).")
        # format isn't checked — int16↔float32 are losslessly inter-convertible, so any pin format works.
        if c.channels > pin.channels:
            raise AudioNegotiationError(f"Pinned {pin.channels} channel(s) is below a consumer's need "
                                        f"({c.channels}).")
    if source.channels < pin.channels:
        raise AudioNegotiationError(f"Pinned {pin.channels} channel(s) exceeds the capture's {source.channels}.")
