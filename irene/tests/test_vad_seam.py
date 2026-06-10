"""Tests for the VAD engine seam (ARCH-10 PR-4).

Covers the parts that hold without sherpa-onnx installed: the `VADEngine` port, the
engine selector config, and the silero engine's numpy-free-input PCM conversion.
SileroVAD execution itself is validated at WB7 re-validation.
"""

import array

import pytest

from irene.utils.vad import VADEngine, SimpleVAD, AdvancedVAD
from irene.utils.vad_silero import SileroVADEngine
from irene.config.models import VADConfig


class TestVADPort:
    def test_energy_engines_implement_the_port(self):
        assert issubclass(SimpleVAD, VADEngine)
        assert issubclass(AdvancedVAD, VADEngine)

    def test_silero_engine_implements_the_port(self):
        assert issubclass(SileroVADEngine, VADEngine)

    def test_simple_vad_is_engine_instance(self):
        assert isinstance(SimpleVAD(), VADEngine)

    def test_port_default_reset_is_noop(self):
        # default reset() on the base does nothing and doesn't raise
        assert SimpleVAD().reset() is None


class TestSelectorConfig:
    def test_default_is_energy(self):
        assert VADConfig().default_provider == "energy"

    def test_silero_selectable(self):
        assert VADConfig(default_provider="silero").default_provider == "silero"

    def test_unknown_provider_accepted_resolved_at_discovery(self):
        # ARCH-18: the enum validator is gone — the provider set is the entry-points, so any string is
        # config-valid and resolved (falling back to energy) at discovery time, not rejected here.
        assert VADConfig(default_provider="bogus").default_provider == "bogus"

    def test_silero_threshold_bounds(self):
        assert VADConfig(silero_threshold=0.5).silero_threshold == 0.5
        with pytest.raises(Exception):
            VADConfig(silero_threshold=1.5)


class TestSileroPcmConversion:
    def test_pcm16_to_float(self):
        data = array.array("h", [0, 16384, -16384, 32767]).tobytes()
        out = SileroVADEngine._to_float(data)
        assert out.dtype.name == "float32"
        assert out.shape[0] == 4
        assert out[0] == 0.0
        assert abs(out[1] - 0.5) < 1e-6
        assert all(-1.0 <= float(x) <= 1.0 for x in out)

    def test_empty(self):
        assert SileroVADEngine._to_float(b"").shape[0] == 0

    def test_odd_trailing_byte_dropped(self):
        data = array.array("h", [1, 2, 3]).tobytes() + b"\x01"
        assert SileroVADEngine._to_float(data).shape[0] == 3
