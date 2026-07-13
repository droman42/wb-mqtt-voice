"""ASSET-4 — silero VAD model goes through the AssetManager, never the audio hot path.

Covers the four findings of the 2026-07-04 VAD review:
- the `silero_vad` asset identity resolves to SileroVADProvider's asset config (no
  generic-defaults fallback), keeping the pre-ASSET-4 on-disk path `models/vad/silero_vad.onnx`;
- downloads run through `AssetManager.download_model` (temp+rename, partial healing) with the
  TOML `model_url` override honored via `url_override`;
- the engine itself never downloads — a missing model is a loud FileNotFoundError;
- the segmenter falls back to `energy` when the configured provider can't initialize.
"""

import pytest

from locveil_voice.config.models import AssetConfig, VADConfig
from locveil_voice.core.assets import AssetManager
from locveil_voice.providers.vad.silero import SileroVADProvider
from locveil_voice.utils.vad_silero import DEFAULT_SILERO_URL, SileroVADEngine
from locveil_voice.workflows.audio_processor import VoiceSegmenter


def make_manager(tmp_path) -> AssetManager:
    return AssetManager(AssetConfig(assets_root=tmp_path))


def patch_download(monkeypatch, manager, payload=b"onnx-bytes", calls=None):
    """Replace the network fetch, keeping the whole download_model flow (temp file, rename)."""
    async def fake_download(url, target_path):
        if calls is not None:
            calls.append(url)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(payload)
    monkeypatch.setattr(manager, "_download_file", fake_download)


# --------------------------------------------------------------------------------------
# Asset identity: 'silero_vad' → SileroVADProvider (not the silero TTS entry, not fallback)
# --------------------------------------------------------------------------------------

def test_silero_vad_asset_identity_resolves_provider_class(tmp_path):
    manager = make_manager(tmp_path)
    asset_config = manager._get_provider_asset_config("silero_vad")
    # Came from SileroVADProvider.get_asset_config, not the generic-defaults fallback.
    assert asset_config["model_urls"] == {"silero_vad": DEFAULT_SILERO_URL}
    assert asset_config["directory_name"] == "vad"
    assert asset_config["file_extension"] == ".onnx"


def test_silero_vad_model_path_is_unchanged_on_disk(tmp_path):
    """Already-deployed volumes keep working: the path is the pre-ASSET-4 one."""
    manager = make_manager(tmp_path)
    path = manager.get_model_path("silero_vad", "silero_vad")
    assert path == tmp_path / "models" / "vad" / "silero_vad.onnx"


def test_silero_vad_asset_name_does_not_collide_with_tts(tmp_path):
    """'silero' stays the TTS asset identity; the VAD one is separate."""
    manager = make_manager(tmp_path)
    tts_config = manager._get_provider_asset_config("silero")
    assert tts_config["model_urls"] != {"silero_vad": DEFAULT_SILERO_URL}


# --------------------------------------------------------------------------------------
# Download path: AssetManager machinery + url_override
# --------------------------------------------------------------------------------------

async def test_download_model_fetches_silero_vad_from_class_default(tmp_path, monkeypatch):
    manager = make_manager(tmp_path)
    calls = []
    patch_download(monkeypatch, manager, calls=calls)

    path = await manager.download_model("silero_vad", "silero_vad")

    assert calls == [DEFAULT_SILERO_URL]
    assert path == tmp_path / "models" / "vad" / "silero_vad.onnx"
    assert path.read_bytes() == b"onnx-bytes"


async def test_download_model_honors_url_override(tmp_path, monkeypatch):
    """The [vad.providers.silero] model_url TOML override rides the same robust path."""
    manager = make_manager(tmp_path)
    calls = []
    patch_download(monkeypatch, manager, calls=calls)

    await manager.download_model("silero_vad", "silero_vad", url_override="https://mirror/x.onnx")

    assert calls == ["https://mirror/x.onnx"]


async def test_download_model_heals_partial_silero_vad_file(tmp_path, monkeypatch):
    """An interrupted download (empty file) is re-downloaded, not trusted forever (F1)."""
    manager = make_manager(tmp_path)
    patch_download(monkeypatch, manager)
    partial = tmp_path / "models" / "vad" / "silero_vad.onnx"
    partial.parent.mkdir(parents=True)
    partial.touch()  # 0 bytes — the exact artifact the old engine-side guard trusted

    path = await manager.download_model("silero_vad", "silero_vad")

    assert path.read_bytes() == b"onnx-bytes"


# --------------------------------------------------------------------------------------
# Engine: no download, loud failure
# --------------------------------------------------------------------------------------

def test_engine_missing_model_is_loud_and_offline(tmp_path):
    from types import SimpleNamespace
    engine = SileroVADEngine(SimpleNamespace(), tmp_path / "nope.onnx")
    with pytest.raises(FileNotFoundError, match="provider initialization"):
        engine._ensure()


# --------------------------------------------------------------------------------------
# Provider init + segmenter fallback (F2/F3: warmup at startup, energy fallback)
# --------------------------------------------------------------------------------------

async def test_provider_do_initialize_downloads_via_asset_manager(monkeypatch):
    seen = {}
    async def fake_download_model(self, provider, model_id, force=False, url_override=None):
        seen.update(provider=provider, model_id=model_id, url_override=url_override)
    monkeypatch.setattr(AssetManager, "download_model", fake_download_model)

    provider = SileroVADProvider({"model_url": "https://mirror/y.onnx"})
    await provider._do_initialize()

    assert seen == {"provider": "silero_vad", "model_id": "silero_vad",
                    "url_override": "https://mirror/y.onnx"}


async def test_segmenter_falls_back_to_energy_when_silero_init_fails(monkeypatch):
    async def boom(self):
        raise RuntimeError("download failed")
    async def available(self):
        return True
    monkeypatch.setattr(SileroVADProvider, "_do_initialize", boom)
    monkeypatch.setattr(SileroVADProvider, "is_available", available)

    segmenter = VoiceSegmenter(VADConfig(default_provider="silero"))
    assert segmenter.vad_engine.get_provider_name() == "silero"

    await segmenter.initialize()

    assert segmenter.vad_engine.get_provider_name() == "energy"


async def test_segmenter_initialize_keeps_healthy_provider(monkeypatch):
    segmenter = VoiceSegmenter(VADConfig(default_provider="energy"))
    await segmenter.initialize()
    assert segmenter.vad_engine.get_provider_name() == "energy"
