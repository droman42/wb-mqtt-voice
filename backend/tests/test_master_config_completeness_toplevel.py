"""ARCH-15 PR-9.2 — get_master_config_completeness covers top-level sections + scalar fields.

Previously it only validated `*.providers.*`, so reference drift like the missing `[outputs]` section
or `observe_*` fields went uncaught. These tests prove the extended check passes on the real
config-master and *catches* a simulated missing section / missing scalar field.
"""

from pathlib import Path
from typing import Optional

import pytest

from locveil_voice.config.auto_registry import AutoSchemaRegistry


def test_is_scalar_annotation():
    f = AutoSchemaRegistry._is_scalar_annotation
    assert f(str) and f(int) and f(float) and f(bool)
    assert f(Optional[str]) and f(Optional[int])
    # non-scalars (tables) are NOT scalar fields
    assert not f(dict) and not f(list)
    from locveil_voice.config.models import OutputConfig
    assert not f(OutputConfig)


def test_real_config_master_is_complete():
    r = AutoSchemaRegistry.get_master_config_completeness()
    assert r["valid"], r
    assert r["missing_top_level_sections"] == []
    assert r["missing_fields"] == []


def _drifted(tmp_path: Path, transform) -> Path:
    text = Path("configs/config-master.toml").read_text(encoding="utf-8")
    out = tmp_path / "drifted.toml"
    out.write_text(transform(text), encoding="utf-8")
    return out


def test_detects_missing_top_level_section(tmp_path):
    # rename [outputs] AND its sub-tables so the parsed config no longer has an `outputs`
    # table — a surviving [outputs.bridge] would implicitly recreate the parent table (TOML
    # super-table semantics), which the completeness check rightly counts as present.
    path = _drifted(tmp_path, lambda t: (t.replace("\n[outputs]\n", "\n[outputs_renamed]\n")
                                          .replace("\n[outputs.", "\n[outputs_renamed.")))
    r = AutoSchemaRegistry.get_master_config_completeness(path)
    assert not r["valid"]
    assert "outputs" in r["missing_top_level_sections"]


def test_detects_missing_scalar_field(tmp_path):
    # drop the live `observe_allow_remote = false` line (the prose mention doesn't match the key regex)
    path = _drifted(tmp_path, lambda t: t.replace("\nobserve_allow_remote = false", "\n# (removed for test)"))
    r = AutoSchemaRegistry.get_master_config_completeness(path)
    assert not r["valid"]
    assert "system.observe_allow_remote" in r["missing_fields"]


def test_commented_scalar_counts_as_documented(tmp_path):
    # observe_token ships COMMENTED in config-master; it must still count as documented (not missing).
    r = AutoSchemaRegistry.get_master_config_completeness()
    assert "system.observe_token" not in r["missing_fields"]
