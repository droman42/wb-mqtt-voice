"""ARCH-18 PR-3 — AudioNegotiator (config-derived canonical + transform-once at the boundary)."""
import tomllib
from pathlib import Path

import pytest

from irene.config.models import CoreConfig
from irene.workflows.audio_negotiator import AudioNegotiator
from irene.intents.models import AudioData

CONFIG_DIR = Path("configs")


@pytest.mark.parametrize("name", [p.stem for p in Path("configs").glob("*.toml")])
def test_every_config_derives_a_canonical(name):
    """No shipped config is an infeasible audio negotiation (would be fatal at startup)."""
    cfg = CoreConfig(**tomllib.load(open(CONFIG_DIR / f"{name}.toml", "rb")))
    neg = AudioNegotiator.from_config(cfg)
    assert neg.canonical.rate == 16000          # all consumers (asr/vt/vad) are 16 kHz
    assert neg.canonical.channels == 1


async def test_to_canonical_downsamples_then_noops():
    cfg = CoreConfig(**tomllib.load(open(CONFIG_DIR / "config-master.toml", "rb")))  # mic 44.1k
    neg = AudioNegotiator.from_config(cfg)

    # 44.1k frame -> resampled to 16k
    pcm = b"\x00\x00" * 4410
    out = await neg.to_canonical(AudioData(data=pcm, timestamp=0.0, sample_rate=44100, channels=1))
    assert out.sample_rate == 16000

    # already-canonical frame -> returned unchanged (same object)
    canon_frame = AudioData(data=b"\x00\x00" * 1600, timestamp=0.0, sample_rate=16000, channels=1)
    assert await neg.to_canonical(canon_frame) is canon_frame


class _MockConsumer:
    """A consumer provider declaring an arbitrary audio contract."""
    def __init__(self, rates):
        from irene.utils.audio_negotiation import AudioContract
        self._c = AudioContract(list(rates), rates[0], ["pcm16"], "pcm16", 1)

    def audio_contract(self):
        return self._c


def test_from_pipeline_uses_provider_declared_contracts():
    from irene.providers.vad.energy import EnergyVADProvider
    cfg = CoreConfig(**tomllib.load(open(CONFIG_DIR / "config-master.toml", "rb")))  # mic 44.1k
    # VAD provider declares 16 kHz; with asr/vt disabled the canonical comes purely from the provider.
    cfg.asr.enabled = False
    cfg.voice_trigger.enabled = False
    neg = AudioNegotiator.from_pipeline(cfg, vad_provider=EnergyVADProvider({}))
    assert neg.canonical.rate == 16000


def test_provider_capability_used_when_config_rate_unset():
    cfg = CoreConfig(**tomllib.load(open(CONFIG_DIR / "config-master.toml", "rb")))  # mic 44.1k
    cfg.vad.enabled = False
    cfg.asr.enabled = False
    cfg.voice_trigger.enabled = True
    cfg.voice_trigger.sample_rate = None              # no operator override → use the provider's capability
    neg = AudioNegotiator.from_pipeline(cfg, wake_provider=_MockConsumer([8000]))
    assert neg.canonical.rate == 8000                 # the provider's declared rate, not a config number


def test_authoritative_config_overrides_provider_capability():
    cfg = CoreConfig(**tomllib.load(open(CONFIG_DIR / "config-master.toml", "rb")))
    cfg.vad.enabled = False
    cfg.asr.enabled = False
    cfg.voice_trigger.enabled = True
    cfg.voice_trigger.sample_rate = 16000             # authoritative override
    neg = AudioNegotiator.from_pipeline(cfg, wake_provider=_MockConsumer([8000]))
    assert neg.canonical.rate == 16000                # operator pin wins over the provider's 8 kHz


def test_source_uses_enabled_input_not_irrelevant_mic_config():
    # Satellite/WS-primary: mic disabled, web enabled. The source must be the WS delivery (16 kHz),
    # NOT the (irrelevant) mic config — else a 16 kHz consumer would look infeasible.
    cfg = CoreConfig(**tomllib.load(open(CONFIG_DIR / "config-master.toml", "rb")))
    cfg.inputs.microphone = False
    cfg.inputs.web = True
    cfg.inputs.microphone_config.sample_rate = 8000   # irrelevant — mic is disabled
    neg = AudioNegotiator.from_config(cfg)            # 16 kHz consumers + 16 kHz WS source → feasible
    assert neg.canonical.rate == 16000


def test_config_pin_is_honored_and_infeasible_pin_is_fatal():
    from irene.utils.audio_negotiation import AudioNegotiationError
    cfg = CoreConfig(**tomllib.load(open(CONFIG_DIR / "config-master.toml", "rb")))  # mic 44.1k
    cfg.audio.canonical_rate = 16000                  # feasible pin
    assert AudioNegotiator.from_config(cfg).canonical.rate == 16000

    cfg2 = CoreConfig(**tomllib.load(open(CONFIG_DIR / "development.toml", "rb")))   # mic 16k
    cfg2.audio.canonical_rate = 48000                 # exceeds the capture → fatal
    with pytest.raises(AudioNegotiationError):
        AudioNegotiator.from_config(cfg2)


async def test_to_canonical_downmixes_stereo_to_mono():
    cfg = CoreConfig(**tomllib.load(open(CONFIG_DIR / "development.toml", "rb")))    # canonical 16k/mono
    neg = AudioNegotiator.from_config(cfg)
    # 16 kHz stereo frame (interleaved int16, 2 ch) → downmixed to mono, rate already canonical
    stereo = b"\x10\x00\x20\x00" * 100                # 100 stereo frames -> 200 int16
    out = await neg.to_canonical(AudioData(data=stereo, timestamp=0.0, sample_rate=16000, channels=2))
    assert out.channels == 1
    assert len(out.data) == len(stereo) // 2          # mono has half the samples


def test_infeasible_config_is_fatal():
    """A consumer needing a higher rate than the mic can deliver fails loudly at from_config."""
    from irene.utils.audio_negotiation import AudioNegotiationError
    cfg = CoreConfig(**tomllib.load(open(CONFIG_DIR / "development.toml", "rb")))
    cfg.inputs.microphone_config.sample_rate = 16000
    cfg.asr.enabled = True
    cfg.asr.sample_rate = 48000          # would require upsampling from the 16 kHz mic
    with pytest.raises(AudioNegotiationError):
        AudioNegotiator.from_config(cfg)
