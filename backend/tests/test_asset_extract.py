"""AssetManager archive extraction — .tar.bz2 support (ARCH-24 T2 / Piper) + partial-download safety (BUG-15).

Piper TTS voices ship as k2-fsa `.tar.bz2` archives (model.onnx + tokens.txt + espeak-ng-data/).
`_extract_archive` previously only dispatched .tar/.tar.gz/.tgz (and Path.suffix on `foo.tar.bz2`
is just `.bz2`), so a Piper voice would fail with "Unsupported archive format". These cover the
fix: dispatch by full name + bzip2 header magic, with tarfile's `r:*` doing the decompression.

BUG-15 adds the partial-download guarantees: a download whose extraction is interrupted/fails must
not leave a broken-but-present pack at the model path (extraction stages then swaps), and an
empty/partial path from a prior failed run must be re-downloaded, not trusted as a cache hit.
"""

import asyncio
import tarfile
from types import SimpleNamespace

import pytest

from locveil_voice.core.assets import AssetManager

try:
    import bz2  # noqa: F401
    _HAS_BZ2 = True
except ImportError:
    # The dev/CI interpreter (custom-built /usr/local CPython) lacks the bz2 module, like _sqlite3.
    # Real deployment images use python:3.11-slim (Debian, libbz2 present), so this is env-only.
    _HAS_BZ2 = False

needs_bz2 = pytest.mark.skipif(not _HAS_BZ2, reason="interpreter built without the bz2 module (env-only; Docker images have it)")


def _make_targz(path, **members):
    with tarfile.open(path, "w:gz") as t:
        _add(t, members)


def _make_tarbz2(path, **members):
    with tarfile.open(path, "w:bz2") as t:
        _add(t, members)


def _add(t, members):
    import io
    for arcname, data in members.items():
        info = tarfile.TarInfo(arcname)
        info.size = len(data)
        t.addfile(info, io.BytesIO(data))


def _extract(tmp_path, archive, url):
    am = object.__new__(AssetManager)  # _extract_archive uses no instance state
    target = tmp_path / "out"
    asyncio.run(am._extract_archive(archive, target, model_url=url))
    return target


@needs_bz2
def test_extract_tar_bz2_by_name(tmp_path):
    arc = tmp_path / "vits-piper-ru_RU-irina-medium.tar.bz2"
    _make_tarbz2(arc, **{"voice/model.onnx": b"onnx", "voice/tokens.txt": b"tok",
                         "voice/espeak-ng-data/ru_dict": b"d"})
    out = _extract(tmp_path, arc, url="https://example/vits-piper-ru_RU-irina-medium.tar.bz2")
    assert (out / "voice" / "model.onnx").read_bytes() == b"onnx"
    assert (out / "voice" / "espeak-ng-data" / "ru_dict").exists()


@needs_bz2
def test_extract_tar_bz2_by_header_when_url_unknown(tmp_path):
    # No tell-tale URL/extension → must fall back to the bzip2 (BZh) header magic.
    arc = tmp_path / "voice.bin"
    _make_tarbz2(arc, **{"model.onnx": b"x"})
    out = _extract(tmp_path, arc, url=None)
    assert (out / "model.onnx").read_bytes() == b"x"


def test_extract_tar_gz_still_works(tmp_path):
    arc = tmp_path / "pack.tar.gz"
    _make_targz(arc, **{"a.txt": b"a"})
    out = _extract(tmp_path, arc, url="https://example/pack.tar.gz")
    assert (out / "a.txt").read_bytes() == b"a"


# ── BUG-15: partial-download safety ─────────────────────────────────────────────────────────────

def test_is_populated_download(tmp_path):
    empty_dir = tmp_path / "empty"; empty_dir.mkdir()
    assert AssetManager._is_populated_download(empty_dir) is False           # empty dir → not a hit
    full = tmp_path / "full"; (full / "sub").mkdir(parents=True); (full / "sub" / "m.onnx").write_bytes(b"x")
    assert AssetManager._is_populated_download(full) is True                 # nested file counts
    empty_file = tmp_path / "e.bin"; empty_file.write_bytes(b"")
    assert AssetManager._is_populated_download(empty_file) is False          # 0-byte file → not a hit
    good_file = tmp_path / "g.bin"; good_file.write_bytes(b"data")
    assert AssetManager._is_populated_download(good_file) is True


def _make_am(tmp_path, model_path, extract_impl):
    """A barebones AssetManager wired for _download_model_impl: fake path/info + a stub downloader,
    with a pluggable _extract_archive to simulate success or failure."""
    am = object.__new__(AssetManager)
    am.config = SimpleNamespace(cache_root=tmp_path / "cache")
    am.get_model_path = lambda provider, model_id: model_path
    am.get_model_info = lambda provider, model_id: {"url": "https://ex/pack.tar.bz2", "extract": True}

    async def _fake_download(url, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"archive-bytes")

    am._download_file = _fake_download
    am._extract_archive = extract_impl
    return am


def test_failed_extraction_leaves_no_partial(tmp_path):
    # An extraction that creates the dir then dies (e.g. missing bz2) must not leave a partial pack.
    model_path = tmp_path / "models" / "piper" / "amy"

    async def _boom(archive, target, url):
        target.mkdir(parents=True, exist_ok=True)   # mimic _extract_archive's first step
        raise RuntimeError("bz2 module missing")

    am = _make_am(tmp_path, model_path, _boom)
    with pytest.raises(RuntimeError):
        asyncio.run(am._download_model_impl("piper", "amy", force=False))
    assert not model_path.exists()                   # no broken-but-present pack left behind


def test_empty_partial_is_reextracted_not_skipped(tmp_path):
    # A stale empty dir from a prior failed run must be re-downloaded, not trusted as "already exists".
    model_path = tmp_path / "models" / "piper" / "amy"
    model_path.mkdir(parents=True)
    calls = {"n": 0}

    async def _ok(archive, target, url):
        calls["n"] += 1
        target.mkdir(parents=True, exist_ok=True)
        (target / "model.onnx").write_bytes(b"onnx")

    am = _make_am(tmp_path, model_path, _ok)
    out = asyncio.run(am._download_model_impl("piper", "amy", force=False))
    assert calls["n"] == 1                            # extraction ran (did not skip on the empty dir)
    assert (out / "model.onnx").read_bytes() == b"onnx"


def test_populated_pack_is_a_cache_hit(tmp_path):
    # The happy path still short-circuits: a populated pack is returned without re-downloading.
    model_path = tmp_path / "models" / "piper" / "amy"
    model_path.mkdir(parents=True); (model_path / "model.onnx").write_bytes(b"onnx")

    async def _should_not_run(archive, target, url):
        raise AssertionError("must not re-extract a populated pack")

    am = _make_am(tmp_path, model_path, _should_not_run)
    out = asyncio.run(am._download_model_impl("piper", "amy", force=False))
    assert out == model_path
