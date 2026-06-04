"""Unit tests for the sherpa-onnx ASR provider (ARCH-10 / PR-1).

Covers the parts that must hold without sherpa-onnx installed: the numpy-free
PCM/WAV→float conversion (armv7 has no numpy), the inference policy, and the
EntryPointMetadata build contract.
"""

import array
import io
import wave

from irene.providers.asr.sherpa_onnx import SherpaOnnxASRProvider, SherpaInferencePolicy


def _pcm16_bytes(samples):
    a = array.array("h", samples)
    return a.tobytes()


class TestToFloatSamples:
    def test_raw_pcm16_roundtrip(self):
        samples = [0, 16384, -16384, 32767, -32768]
        floats, rate = SherpaOnnxASRProvider._to_float_samples(_pcm16_bytes(samples), 16000)
        assert rate == 16000
        assert len(floats) == len(samples)
        assert floats[0] == 0.0
        assert abs(floats[1] - 0.5) < 1e-6
        assert all(-1.0 <= f <= 1.0 for f in floats)

    def test_empty(self):
        assert SherpaOnnxASRProvider._to_float_samples(b"", 16000) == ([], 16000)

    def test_odd_trailing_byte_dropped(self):
        data = _pcm16_bytes([1, 2, 3]) + b"\x01"  # one stray byte
        floats, rate = SherpaOnnxASRProvider._to_float_samples(data, 16000)
        assert len(floats) == 3  # trailing odd byte ignored, no crash

    def test_wav_container_uses_header_rate(self):
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(8000)  # deliberately != default
            w.writeframes(_pcm16_bytes([100, -100, 200, -200]))
        floats, rate = SherpaOnnxASRProvider._to_float_samples(buf.getvalue(), 16000)
        assert rate == 8000  # taken from the WAV header, not the default
        assert len(floats) == 4


class TestInferencePolicy:
    def test_explicit_override_wins(self):
        assert SherpaInferencePolicy.for_platform(8).num_threads == 8

    def test_default_is_positive(self):
        assert SherpaInferencePolicy.for_platform().num_threads >= 1

    def test_zero_or_none_override_falls_back(self):
        assert SherpaInferencePolicy.for_platform(0).num_threads >= 1
        assert SherpaInferencePolicy.for_platform(None).num_threads >= 1


class TestBuildContract:
    def test_python_dependencies_is_group_name(self):
        # CONTRACT: extra GROUP NAME, not a requirement string (build runs `uv sync --extra`).
        assert SherpaOnnxASRProvider.get_python_dependencies() == ["asr-onnx"]

    def test_platform_dependencies_alsa(self):
        deps = SherpaOnnxASRProvider.get_platform_dependencies()
        assert deps["linux.ubuntu"] == ["libasound2"]
        assert set(deps) == {"linux.ubuntu", "linux.alpine", "macos", "windows"}

    def test_platform_support(self):
        assert "linux.ubuntu" in SherpaOnnxASRProvider.get_platform_support()

    def test_model_packs_declared(self):
        urls = SherpaOnnxASRProvider._get_default_model_urls()
        assert "vosk-model-small-ru" in urls
        assert urls["vosk-model-small-ru"]["repo"] == "alphacep/vosk-model-small-ru"


class TestModelPacks:
    """PR-2: whisper packs (no joiner) vs transducer packs (joiner)."""

    def test_transducer_pack_has_joiner(self):
        urls = SherpaOnnxASRProvider._get_default_model_urls()
        assert urls["vosk-model-small-ru"]["members"] == ["encoder", "decoder", "joiner", "tokens"]

    def test_whisper_pack_has_no_joiner(self):
        urls = SherpaOnnxASRProvider._get_default_model_urls()
        assert "whisper-base" in urls
        assert urls["whisper-base"]["members"] == ["encoder", "decoder", "tokens"]
        assert urls["whisper-base"]["repo"] == "csukuangfj/sherpa-onnx-whisper-base"

    def test_pick_files_whisper_3_members_int8(self):
        from irene.core.assets import AssetManager
        siblings = [
            "base-encoder.int8.onnx", "base-encoder.onnx",
            "base-decoder.int8.onnx", "base-decoder.onnx", "base-tokens.txt",
        ]
        picks = AssetManager._pick_pack_files(siblings, "int8", ["encoder", "decoder", "tokens"])
        assert picks == {
            "encoder": "base-encoder.int8.onnx",
            "decoder": "base-decoder.int8.onnx",
            "tokens": "base-tokens.txt",
        }
        assert "joiner" not in picks

    def test_pick_files_transducer_default_members(self):
        from irene.core.assets import AssetManager
        siblings = ["encoder.onnx", "encoder.int8.onnx", "decoder.int8.onnx", "joiner.int8.onnx", "tokens.txt"]
        picks = AssetManager._pick_pack_files(siblings, "int8")  # default 4 members
        assert set(picks) == {"encoder", "decoder", "joiner", "tokens"}
        assert picks["encoder"] == "encoder.int8.onnx"  # int8 preferred
