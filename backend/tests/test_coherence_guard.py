"""TEST-22 — the code↔config↔entry-points coherence guard (ARCH-50 §H).

The failure class no gate caught before the ARCH-50 review: hand-maintained maps drifting
from pyproject's entry-point groups, config fields declared but read by nothing, and TOML
keys surviving field deletions unnoticed (nested models silently ignore extras). All three
directions are asserted hermetically here — no network, no model loads.

Scope notes:
- (a) is anchored on `utils/namespaces.py` (ARCH-57): the ONE registry every former hand-map
  imports. If the registry mirrors pyproject, the consumers can't drift.
- (b) is a textual reader search: a field with ZERO occurrences outside its declaration site
  (and the TOML template generator, which is pure serialization) is declared-but-never-read.
  Fields whose name also occurs for unrelated reasons can slip through — this guard catches
  the egregious class, not every instance. The allowlist below must stay TINY and each entry
  must carry a reason.
- (c) master-completeness (every model field present in config-master) is asserted by
  `test_master_config_completeness_toplevel.py`; here we add the REVERSE direction: no live
  TOML carries a key the models no longer declare.
"""

import re
import tomllib
from pathlib import Path
from typing import Any, Dict, Set

import pytest
from pydantic import BaseModel

from locveil_voice.utils.namespaces import (
    ALL_NAMESPACES,
    COMPONENTS_NAMESPACE,
    INTENT_HANDLERS_NAMESPACE,
    INPUTS_NAMESPACE,
    PROVIDER_NAMESPACES,
    WORKFLOWS_NAMESPACE,
)
from locveil_voice.config import models as config_models
from locveil_voice.config.models import CoreConfig

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "backend" / "src" / "locveil_voice"
_CONFIG_DIR = _REPO_ROOT / "config"
_PYPROJECT = _REPO_ROOT / "backend" / "pyproject.toml"

# The nine live TOMLs (QUAL-83 pinned the set; orphans were deleted).
_LIVE_TOMLS = sorted(_CONFIG_DIR.glob("*.toml"))

# (b) fields that ARE legitimately declared without a same-named textual read.
# Every entry needs a reason; additions should be rare and reviewed.
_READER_ALLOWLIST: Dict[str, str] = {
    # read DYNAMICALLY by InputManager's generic wiring: getattr(cfg, f"{name}_config")
    # per discovered entry-point name (ARCH-56) — a textual search can't see it.
    "cli_config": "ARCH-56 dynamic per-input config lookup",
    "web_config": "ARCH-56 dynamic per-input config lookup",
    "microphone_config": "ARCH-56 dynamic per-input config lookup",
}


# --------------------------------------------------------------------------- (a) registry ≡ pyproject


def _pyproject_groups() -> Set[str]:
    eps = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))["project"]["entry-points"]
    return set(eps.keys())


def test_namespace_registry_mirrors_pyproject():
    """ALL_NAMESPACES must be exactly pyproject's entry-point groups — no phantom, no gap."""
    groups = _pyproject_groups()
    assert set(ALL_NAMESPACES) == groups, (
        f"utils/namespaces.py drifted from pyproject entry-points: "
        f"only-in-registry={set(ALL_NAMESPACES) - groups}, only-in-pyproject={groups - set(ALL_NAMESPACES)}")


def test_provider_namespaces_cover_every_provider_group():
    """PROVIDER_NAMESPACES must map exactly the locveil_voice.providers.* groups, keyed by family."""
    provider_groups = {g for g in _pyproject_groups() if g.startswith("locveil_voice.providers.")}
    assert set(PROVIDER_NAMESPACES.values()) == provider_groups
    for key, group in PROVIDER_NAMESPACES.items():
        assert group == f"locveil_voice.providers.{key}", (key, group)


def test_non_provider_constants_exist_in_pyproject():
    groups = _pyproject_groups()
    for const in (COMPONENTS_NAMESPACE, WORKFLOWS_NAMESPACE, INTENT_HANDLERS_NAMESPACE, INPUTS_NAMESPACE):
        assert const in groups, const


def test_no_stray_namespace_literals_outside_the_registry():
    """No runtime module restates an entry-point group as a string literal (ARCH-57's point).

    The registry itself and this test are the only allowed spellings; pyproject is the artifact
    of record, not python source.
    """
    pattern = re.compile(
        r'["\'](?:' + "|".join(re.escape(g) for g in sorted(ALL_NAMESPACES)) + r')["\']')
    offenders = []
    for py in _SRC_ROOT.rglob("*.py"):
        if py.name == "namespaces.py":
            continue
        for lineno, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.split("#")[0]
            if pattern.search(stripped):
                offenders.append(f"{py.relative_to(_REPO_ROOT)}:{lineno}: {line.strip()}")
    assert not offenders, (
        "entry-point group restated as a literal (import it from utils/namespaces.py instead):\n"
        + "\n".join(offenders))


# --------------------------------------------------------------------------- (b) every field has a reader


def _all_declared_fields() -> Dict[str, Set[str]]:
    """field name -> set of 'Model.field' declaration sites across config/models.py models."""
    fields: Dict[str, Set[str]] = {}
    for name in dir(config_models):
        obj = getattr(config_models, name)
        if isinstance(obj, type) and issubclass(obj, BaseModel) and obj.__module__ == config_models.__name__:
            for fname in obj.model_fields:
                fields.setdefault(fname, set()).add(f"{name}.{fname}")
    return fields


def _runtime_corpus() -> str:
    """Concatenated runtime source, minus the declaration site and the pure-serialization template."""
    chunks = []
    for py in _SRC_ROOT.rglob("*.py"):
        rel = py.relative_to(_SRC_ROOT).as_posix()
        if rel in ("config/models.py", "config/manager.py"):
            continue
        chunks.append(py.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def test_every_config_field_has_a_runtime_reader():
    """A declared field must occur somewhere in runtime source — else it is config fiction.

    This is the check that would have caught the ARCH-50 seed (`discovery_paths`/
    `auto_discover`) and the ~30 QUAL-83 deletions on the day they went dead.
    """
    corpus = _runtime_corpus()
    dead = {}
    for fname, sites in _all_declared_fields().items():
        if fname in _READER_ALLOWLIST:
            continue
        if not re.search(r"\b" + re.escape(fname) + r"\b", corpus):
            dead[fname] = sorted(sites)
    assert not dead, (
        "declared-but-never-read config fields (honor or delete — ARCH-50 ruling; "
        "if a field is legitimately read only dynamically, allowlist it WITH a reason):\n"
        + "\n".join(f"  {k}: {v}" for k, v in sorted(dead.items())))


# --------------------------------------------------------------------------- (c) TOMLs ≡ schema (reverse)


def _known_keys(model: type) -> Dict[str, Any]:
    """Recursive {field: sub-model-or-None} tree for a Pydantic model; open dicts map to Ellipsis."""
    tree: Dict[str, Any] = {}
    for fname, finfo in model.model_fields.items():
        ann = finfo.annotation
        # unwrap Optional[...]
        args = getattr(ann, "__args__", ())
        candidates = [ann, *args]
        sub = next((c for c in candidates
                    if isinstance(c, type) and issubclass(c, BaseModel)), None)
        if sub is not None:
            tree[fname] = _known_keys(sub)
        else:
            origin = getattr(ann, "__origin__", None)
            tree[fname] = ... if origin is dict else None
    return tree


def _walk(prefix: str, data: Dict[str, Any], tree: Dict[str, Any], unknown: list) -> None:
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if key not in tree:
            unknown.append(path)
            continue
        sub = tree[key]
        if sub is ...:  # open Dict[str, ...] — provider blocks etc., anything goes
            continue
        if isinstance(value, dict):
            if isinstance(sub, dict):
                _walk(path, value, sub, unknown)
            else:
                unknown.append(f"{path} (table where scalar declared)")


@pytest.mark.parametrize("toml_path", _LIVE_TOMLS, ids=lambda p: p.name)
def test_live_tomls_carry_no_unknown_keys(toml_path: Path):
    """No live TOML carries a key the models no longer declare.

    Nested models silently IGNORE extra keys, so a field deletion leaves stale TOML lines
    lying to their reader forever — this is the reverse direction master-completeness
    doesn't check.
    """
    data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    unknown: list = []
    _walk("", data, _known_keys(CoreConfig), unknown)
    # Known-stale keys awaiting their own fix — each entry names the ledger task.
    # (Empty since BUG-43 wired the canonical language policy; keep the mechanism.)
    toml_allowlist: Dict[str, str] = {}
    unknown = [u for u in unknown if u not in toml_allowlist]
    assert not unknown, f"{toml_path.name} carries keys no config model declares:\n  " + "\n  ".join(unknown)
