"""ASSET-5 — wake-word model packs through the AssetManager (`docs/design/wakeword_models.md`).

Hermetic (no network, no pymicro-wakeword needed): the AssetManager's fetch is patched at the
`_download_file` seam so the whole pack flow (staging, atomic rename, healing) runs for real, and
the provider's resolution rungs are driven with a fake `pmw` namespace.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

from locveil_voice.config.models import AssetConfig
from locveil_voice.core.assets import AssetManager
from locveil_voice.providers.voice_trigger.microwakeword import MicroWakeWordProvider

_HF = "https://huggingface.co/droman42/microwakeword-irina-ru/resolve/main"
IRINA_JSON = f"{_HF}/irina.json"
IRINA_TFLITE = f"{_HF}/irina.tflite"


def make_manager(tmp_path) -> AssetManager:
    return AssetManager(AssetConfig(assets_root=tmp_path))


def patch_download(monkeypatch, manager, calls=None, fail_on=None):
    """Replace the network fetch, keeping staging/rename/healing real."""
    async def fake_download(url, target_path):
        if calls is not None:
            calls.append(url)
        if fail_on and url.endswith(fail_on):
            raise RuntimeError("network down")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(b"data:" + url.encode())
    monkeypatch.setattr(manager, "_download_file", fake_download)


# --------------------------------------------------------------------------------------
# Released catalog (rung 4 source): irina pack, directory-shaped paths
# --------------------------------------------------------------------------------------

def test_catalog_has_irina_pack(tmp_path):
    cfg = make_manager(tmp_path)._get_provider_asset_config("microwakeword")
    assert cfg["model_urls"]["irina"]["files"] == {
        "irina.json": IRINA_JSON, "irina.tflite": IRINA_TFLITE}
    assert cfg["file_extension"] == ""  # models are DIRECTORY packs


def test_model_path_is_directory_shaped(tmp_path):
    path = make_manager(tmp_path).get_model_path("microwakeword", "irina")
    assert path == tmp_path / "models" / "microwakeword" / "irina"


# --------------------------------------------------------------------------------------
# Multi-file pack download: atomicity, healing, ad-hoc packs
# --------------------------------------------------------------------------------------

async def test_download_model_fetches_pack(tmp_path, monkeypatch):
    manager = make_manager(tmp_path)
    calls = []
    patch_download(monkeypatch, manager, calls=calls)

    pack_dir = await manager.download_model("microwakeword", "irina")

    assert sorted(p.name for p in pack_dir.iterdir()) == ["irina.json", "irina.tflite"]
    assert set(calls) == {IRINA_JSON, IRINA_TFLITE}


async def test_failed_pack_download_leaves_nothing(tmp_path, monkeypatch):
    """One file of the pack fails → no half-pack lands, no staging dir survives."""
    manager = make_manager(tmp_path)
    patch_download(monkeypatch, manager, fail_on=".tflite")

    with pytest.raises(RuntimeError):
        await manager.download_model("microwakeword", "irina")

    root = tmp_path / "models" / "microwakeword"
    assert not (root / "irina").exists()
    assert not list(root.glob(".*.incomplete"))


async def test_empty_pack_dir_is_healed(tmp_path, monkeypatch):
    """An interrupted earlier run (empty dir) is re-downloaded, not trusted forever."""
    manager = make_manager(tmp_path)
    patch_download(monkeypatch, manager)
    (tmp_path / "models" / "microwakeword" / "irina").mkdir(parents=True)

    pack_dir = await manager.download_model("microwakeword", "irina")

    assert sorted(p.name for p in pack_dir.iterdir()) == ["irina.json", "irina.tflite"]


async def test_download_model_files_adhoc_and_cached(tmp_path, monkeypatch):
    """Ad-hoc packs (manifest-URL rung) download once, then short-circuit."""
    manager = make_manager(tmp_path)
    calls = []
    patch_download(monkeypatch, manager, calls=calls)
    files = {"word.json": "https://example.org/m/word.json",
             "word.tflite": "https://example.org/m/word.tflite"}

    first = await manager.download_model_files("microwakeword", "custom", files)
    again = await manager.download_model_files("microwakeword", "custom", files)

    assert first == again == tmp_path / "models" / "microwakeword" / "custom"
    assert len(calls) == 2  # second call hit the populated check, no re-download


# --------------------------------------------------------------------------------------
# Provider resolution rungs (fake pmw — no wheel, no network)
# --------------------------------------------------------------------------------------

def fake_pmw(record):
    return SimpleNamespace(
        MicroWakeWord=SimpleNamespace(
            from_config=lambda path: record.append(("config", Path(path))) or "DETECTOR",
            from_builtin=lambda model: record.append(("builtin", model)) or "DETECTOR",
        ),
        Model={"ALEXA": "alexa", "OKAY_NABU": "okay_nabu",
               "HEY_JARVIS": "hey_jarvis", "HEY_MYCROFT": "hey_mycroft"},
    )


def spec(name, model):
    return {"name": name, "model": model, "threshold": 0.8, "language": "en"}


async def test_rung2_builtin_resolves_without_assets(tmp_path):
    provider = MicroWakeWordProvider({"wake_words": []})
    provider.asset_manager = None  # any asset touch would explode — builtins must not need it
    record = []

    detector = await provider._build_detector(fake_pmw(record), spec("alexa", "alexa"))

    assert detector == "DETECTOR"
    assert record == [("builtin", "alexa")]


async def test_rung3_manifest_url_fetches_sibling_pack(tmp_path):
    provider = MicroWakeWordProvider({"wake_words": []})
    seen = {}
    pack_dir = tmp_path / "custom"
    pack_dir.mkdir()

    async def fake_files(asset, model_id, files):
        seen.update(asset=asset, model_id=model_id, files=files)
        return pack_dir
    provider.asset_manager = SimpleNamespace(download_model_files=fake_files)
    record = []

    detector = await provider._build_detector(
        fake_pmw(record), spec("custom", "https://example.org/m/word.json"))

    assert detector == "DETECTOR"
    assert seen["files"] == {"word.json": "https://example.org/m/word.json",
                             "word.tflite": "https://example.org/m/word.tflite"}
    assert record == [("config", pack_dir / "word.json")]


async def test_rung4_catalog_pack_resolves_manifest_in_dir(tmp_path):
    provider = MicroWakeWordProvider({"wake_words": []})
    pack_dir = tmp_path / "irina"
    pack_dir.mkdir()
    (pack_dir / "irina.json").write_text("{}")

    async def fake_download(asset, model_id):
        assert (asset, model_id) == ("microwakeword", "irina")
        return pack_dir
    provider.asset_manager = SimpleNamespace(download_model=fake_download)
    record = []

    detector = await provider._build_detector(fake_pmw(record), spec("irina", "irina"))

    assert detector == "DETECTOR"
    assert record == [("config", pack_dir / "irina.json")]


async def test_unresolvable_word_is_skipped_not_fatal(tmp_path):
    provider = MicroWakeWordProvider({"wake_words": []})

    async def no_model(asset, model_id):
        raise ValueError("No model configuration found")
    provider.asset_manager = SimpleNamespace(download_model=no_model)

    detector = await provider._build_detector(fake_pmw([]), spec("ghost", "ghost"))
    assert detector is None


def test_supported_words_advertise_catalog():
    provider = MicroWakeWordProvider({"wake_words": []})
    supported = provider.get_supported_wake_words()
    assert "irina" in supported     # released catalog
    assert "alexa" in supported     # built-in
