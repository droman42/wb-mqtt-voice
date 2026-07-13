"""ARCH-24 T3 build gate: a profile that enables an armv7-incapable provider must fail on armv7l.

`IreneBuildAnalyzer.validate_architecture(config, arch)` returns errors for enabled providers that
don't list `arch` in get_supported_architectures(). The CI runs it for the armv7 profile so a
torch/onnxruntime provider can't silently ship in the armv7 image.
"""

from locveil_voice.tools.build_analyzer import IreneBuildAnalyzer


def test_armv7_profile_passes_the_gate():
    # embedded-armv7 enables only armv7-capable providers (sherpa_onnx ASR, console).
    assert IreneBuildAnalyzer().validate_architecture("configs/embedded-armv7.toml", "armv7l") == []


def test_torch_provider_in_a_profile_fails_on_armv7():
    # config-master's asr fallback is `whisper` (torch) — must be flagged on armv7l.
    errors = IreneBuildAnalyzer().validate_architecture("configs/config-master.toml", "armv7l")
    assert errors, "expected the gate to flag torch/onnxruntime providers on armv7l"
    assert any("whisper" in e and "armv7l" in e for e in errors)


def test_x86_64_runs_everything():
    # Every provider supports x86_64, so no profile should fail there.
    assert IreneBuildAnalyzer().validate_architecture("configs/config-master.toml", "x86_64") == []
