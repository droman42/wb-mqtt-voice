"""PiperTTSProvider — VITS via sherpa-onnx OfflineTts (ARCH-24 T2, PR2).

Construction-free / light-construction unit tests (no model download, no real sherpa session):
the voice descriptors, deps/platform contract, the numpy-free PCM conversion, the pack resolver,
and the base text-prep hook (which `piper_ruaccent` overrides in PR3).
"""

import asyncio

from locveil_voice.providers.tts.piper import PiperTTSProvider, _float_to_pcm16


def test_voice_descriptors_are_extractable_tarballs():
    urls = PiperTTSProvider._get_default_model_urls()
    ru = {"irina", "ruslan", "denis", "dmitri"}
    en = {"amy", "lessac", "ryan"}  # I18N-3
    assert set(urls) == ru | en
    for name, d in urls.items():
        assert d["extract"] is True
        locale = "ru_RU" if name in ru else "en_US"
        assert d["url"].endswith(f"vits-piper-{locale}-{name}-medium.tar.bz2")
        assert "k2-fsa/sherpa-onnx/releases" in d["url"]


def test_english_voice_reports_en_us_language():
    # I18N-3: a config selecting an en_US voice reports en-US, not the ru default.
    p = PiperTTSProvider({"voice": "amy", "language": "en"})
    assert p.voice == "amy"
    assert p.get_capabilities()["languages"] == ["en-US"]
    assert "amy" in p.get_capabilities()["voices"]


def test_deps_are_sherpa_runtime_no_torch():
    assert PiperTTSProvider.get_python_dependencies() == ["asr-onnx"]
    plat = PiperTTSProvider.get_platform_dependencies()
    # No system espeak-ng / bz2 — sherpa bundles the phonemizer; bz2 is in the python base.
    flat = [p for v in plat.values() for p in v]
    assert not any("espeak" in p or "bz2" in p for p in flat)


def test_platform_support_includes_linux_for_armv7_target():
    # The WB7 TTS — sherpa-onnx is the only armv7 ONNX engine; declared support spans the std set.
    assert "linux.ubuntu" in PiperTTSProvider.get_platform_support()


def test_float_to_pcm16_is_numpy_free_and_correct():
    # Matches utils.float_to_pcm16 scaling (s*32767): 0.0->0, 1.0->32767, -1.0->-32767; LE int16.
    def le(n):
        return n.to_bytes(2, "little", signed=True)
    assert _float_to_pcm16([0.0, 1.0, -1.0]) == le(0) + le(32767) + le(-32767)
    # out-of-range inputs clamp to the int16 limits (no overflow/wrap).
    assert _float_to_pcm16([2.0, -2.0]) == le(32767) + le(-32768)


def test_resolve_pack_finds_nested_voice_files(tmp_path):
    # The k2-fsa tarball expands to a vits-piper-... subdir — the resolver must search recursively.
    inner = tmp_path / "vits-piper-ru_RU-irina-medium"
    (inner / "espeak-ng-data").mkdir(parents=True)
    (inner / "ru_RU-irina-medium.onnx").write_bytes(b"onnx")
    (inner / "tokens.txt").write_text("tok")
    files = PiperTTSProvider._resolve_pack(tmp_path)
    assert files["model"].name.endswith(".onnx")
    assert files["tokens"].name == "tokens.txt"
    assert files["data_dir"].name == "espeak-ng-data" and files["data_dir"].is_dir()


def test_base_prepare_text_is_identity():
    # The base does no stress shaping (espeak-ng does); piper_ruaccent (PR3) overrides this.
    p = PiperTTSProvider({"voice": "irina"})
    assert asyncio.run(p._prepare_text("привет мир")) == "привет мир"
    assert p.voice == "irina"
    assert "irina" in p.get_capabilities()["voices"]
