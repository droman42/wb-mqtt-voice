"""ARCH-18 PR-3 — canonical audio-format derivation (the negotiation core)."""
import pytest

from locveil_voice.utils.audio_negotiation import (
    AudioContract, CanonicalFormat, derive_canonical, AudioNegotiationError,
)


def _c(rates, fmts=("pcm16",), ch=1):
    return AudioContract(supported_rates=list(rates), preferred_rate=rates[0],
                         supported_formats=list(fmts), preferred_format=fmts[0], channels=ch)


def test_downsamples_capture_to_consumer_rate():
    canon = derive_canonical(_c([44100]), [_c([16000]), _c([16000])])
    assert canon == CanonicalFormat(16000, "pcm16", 1)


def test_picks_highest_feasible_common_rate():
    # consumers all accept 16k and 8k; capture can reach both → pick the higher (better quality).
    canon = derive_canonical(_c([48000]), [_c([16000, 8000]), _c([16000, 8000])])
    assert canon.rate == 16000


def test_fatal_when_consumer_needs_more_than_capture_can_give():
    with pytest.raises(AudioNegotiationError):
        derive_canonical(_c([16000]), [_c([48000])])   # would require upsampling


def test_fatal_when_no_common_consumer_rate():
    with pytest.raises(AudioNegotiationError):
        derive_canonical(_c([48000]), [_c([16000]), _c([8000])])


def test_no_consumers_uses_source_preference():
    canon = derive_canonical(_c([22050], fmts=("float32",)), [])
    assert canon == CanonicalFormat(22050, "float32", 1)


def test_canonical_format_is_pcm16_by_default():
    canon = derive_canonical(_c([16000], fmts=("pcm16", "float32")),
                             [_c([16000], fmts=("pcm16", "float32"))])
    assert canon.format == "pcm16"


def test_canonical_is_pcm16_even_for_float32_only_consumer():
    # int16↔float32 are lossless, so a float32-needing consumer converts from the canonical pcm16 itself —
    # format never forces a negotiation failure.
    canon = derive_canonical(_c([16000], fmts=("pcm16",)), [_c([16000], fmts=("float32",))])
    assert canon.format == "pcm16"


def test_channels_downmix_ok_but_upmix_fatal():
    assert derive_canonical(_c([16000], ch=2), [_c([16000], ch=1)]).channels == 1
    with pytest.raises(AudioNegotiationError):
        derive_canonical(_c([16000], ch=1), [_c([16000], ch=2)])


def test_valid_pin_is_honored():
    pin = CanonicalFormat(16000, "pcm16", 1)
    assert derive_canonical(_c([44100]), [_c([16000])], pin=pin) is pin


def test_infeasible_pin_raises():
    with pytest.raises(AudioNegotiationError):
        derive_canonical(_c([16000]), [_c([16000])], pin=CanonicalFormat(48000, "pcm16", 1))


def test_empty_supported_rates_rejected():
    with pytest.raises(ValueError):
        AudioContract(supported_rates=[], preferred_rate=16000)
