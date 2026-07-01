"""SherpaMoonshineASRProvider — offline Moonshine on the sherpa-onnx runtime (I18N-2).

Light unit tests (no model download / no real sherpa session): the URL-tarball catalog, the merged-.ort
pack resolver, and the offline/English defaults that differ from the base VOSK provider.
"""
import asyncio

from irene.providers.asr.sherpa_moonshine import SherpaMoonshineASRProvider


def test_catalog_is_a_github_tarball():
    urls = SherpaMoonshineASRProvider._get_default_model_urls()
    assert set(urls) == {"moonshine-tiny-en"}
    d = urls["moonshine-tiny-en"]
    assert d["extract"] is True  # a .tar.bz2 GitHub release (URL+extract), NOT an HF model-pack
    assert d["url"].endswith("sherpa-onnx-moonshine-tiny-en-quantized-2026-02-27.tar.bz2")
    assert "k2-fsa/sherpa-onnx/releases" in d["url"]
    assert SherpaMoonshineASRProvider._get_default_directory() == "sherpa_moonshine"


def test_offline_english_defaults():
    p = SherpaMoonshineASRProvider({})
    assert p.get_provider_name() == "sherpa_moonshine"
    assert p.model_id == "moonshine-tiny-en"        # subclass default, not the base's RU vosk pack
    assert p.default_language == "en"
    assert p.supports_streaming is False            # offline → batch branch → dodges BUG-13
    assert p.get_supported_languages() == ["en"]


def test_is_available_resolves_under_own_namespace(monkeypatch):
    # Regression (I18N-8): the inherited is_available() must key on get_provider_name()
    # ("sherpa_moonshine"), not the base's hardcoded "sherpa_onnx". Before the fix it looked up
    # moonshine-tiny-en under the sherpa_onnx namespace, missed, and the ASR component dropped the
    # provider ("not available (dependencies missing)") → /ws/audio rejected audio.
    p = SherpaMoonshineASRProvider({})
    seen = {}

    class _Path:
        def exists(self):
            return False  # force the descriptor branch

    def fake_get_model_path(provider, model_id):
        seen["path"] = provider
        return _Path()

    def fake_get_model_info(provider, model_id):
        seen["info"] = (provider, model_id)
        return {"url": "x"} if provider == "sherpa_moonshine" else None

    monkeypatch.setattr(p.asset_manager, "get_model_path", fake_get_model_path)
    monkeypatch.setattr(p.asset_manager, "get_model_info", fake_get_model_info)

    assert asyncio.run(p.is_available()) is True
    assert seen["path"] == "sherpa_moonshine"                     # not "sherpa_onnx"
    assert seen["info"] == ("sherpa_moonshine", "moonshine-tiny-en")


def test_resolve_pack_finds_merged_ort_members(tmp_path):
    # The .tar.bz2 expands into a sherpa-onnx-moonshine-* subdir — resolve recursively.
    inner = tmp_path / "sherpa-onnx-moonshine-tiny-en-quantized-2026-02-27"
    inner.mkdir()
    (inner / "encoder_model.ort").write_bytes(b"e")
    (inner / "decoder_model_merged.ort").write_bytes(b"d")
    (inner / "tokens.txt").write_text("t")
    files = SherpaMoonshineASRProvider._resolve_pack(tmp_path)
    assert files["encoder"].name == "encoder_model.ort"
    assert files["merged_decoder"].name == "decoder_model_merged.ort"
    assert files["tokens"].name == "tokens.txt"
