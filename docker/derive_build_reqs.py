#!/usr/bin/env python3
"""Derive the flat Docker build inputs from the build-analyzer's JSON output.

The analyzer (`locveil_voice.tools.build_analyzer --json`) emits build-requirements.json for a config profile;
this turns it into the small files the builder/runtime stages consume — keeping the Dockerfiles free of
inline multiline Python (which the Dockerfile parser cannot handle).

Usage:  python derive_build_reqs.py <build-requirements.json>  [--platform linux.ubuntu]  [--out /tmp]
                                    [--config config/<profile>.toml]
Writes (into --out, default /tmp): system-packages.txt, runtime-packages.txt, pip-target.txt,
pip-specs.txt. --config trims spaCy models to the tier the profile loads.
"""
import argparse
import json
import re
from pathlib import Path
from typing import Optional

# A pyproject EXTRA name (e.g. "asr-onnx") vs a package SPEC (e.g. "fastapi>=0.100.0", "uvicorn[standard]").
# The analyzer's `python_dependencies` mixes both: extra names go to `uv sync --extra`, specs to `uv pip
# install`. (The cleaner fix — have the analyzer map provider deps to the extra that provides them and emit
# extra names only — is tracked as the BUILD-5 "confirm/fix uv sync --extra" item.)
_EXTRA_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9._-]*$")
# Build-only apt packages — needed in the builder stage, NOT the (lean) runtime image.
_BUILD_ONLY = {"build-essential", "pkg-config", "gcc", "g++", "make", "cmake"}


def _is_build_only(pkg: str) -> bool:
    return pkg in _BUILD_ONLY or pkg.endswith("-dev")


# spaCy language models (e.g. ru_core_news_md) are PEP 508 direct-reference specs distributed via pip —
# NOT runtime-downloaded like the other models (whisper/vosk/piper/silero). The provider lists every
# model+tier, so an image would bake all four; we trim to the ONE the config actually loads (the first
# language_preferences entry per supported language).
_SPACY_MODEL = re.compile(r"_core_(news|web)_")


def _spacy_keep(config_path: Optional[str]) -> Optional[set]:
    """The spaCy model names the config actually loads — first `language_preferences` entry per supported
    language. Returns None when there's no config or no spaCy preferences (→ don't trim)."""
    if not config_path:
        return None
    import tomllib
    cfg = tomllib.loads(Path(config_path).read_text())
    prefs = cfg.get("nlu", {}).get("providers", {}).get("spacy_nlu", {}).get("language_preferences", {})
    if not prefs:
        return None
    supported = set(cfg.get("supported_languages", []))
    keep = set()
    for lang, models in prefs.items():
        if (not supported or lang in supported) and models:
            keep.add(models[0])  # first preference = the model the provider loads at runtime
    return keep


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("requirements", help="path to build-requirements.json")
    ap.add_argument("--platform", default="linux.ubuntu", help="system-package set to extract")
    ap.add_argument("--out", default="/tmp", help="output directory for the flat files")
    ap.add_argument("--config", help="config profile TOML — trims spaCy models to the one(s) it loads")
    args = ap.parse_args()

    data = json.loads(Path(args.requirements).read_text())
    out = Path(args.out)

    pkgs = data.get("system_packages", {}).get(args.platform, [])
    deps = data.get("python_dependencies", [])

    extra_names = [d for d in deps if _EXTRA_NAME.match(d)]
    pip_specs = [d for d in deps if not _EXTRA_NAME.match(d)]

    # Trim spaCy models to the one(s) the config actually loads (drops unused tiers + languages).
    keep = _spacy_keep(args.config)
    if keep is not None:
        kept = [s for s in pip_specs
                if not (_SPACY_MODEL.search(s.split("@", 1)[0].strip())
                        and s.split("@", 1)[0].strip() not in keep)]
        if len(kept) != len(pip_specs):
            print(f"🧹 spaCy models kept {sorted(keep)} (dropped {len(pip_specs) - len(kept)})")
        pip_specs = kept

    # The bridge-style install target: `uv pip install .[extra1,extra2]` (or just `.`), plus the loose
    # package specs, into the /opt/venv the runtime image copies.
    target = "." if not extra_names else f".[{','.join(extra_names)}]"

    runtime_pkgs = [p for p in pkgs if not _is_build_only(p)]

    (out / "system-packages.txt").write_text(" ".join(pkgs))            # all (builder stage)
    (out / "runtime-packages.txt").write_text(" ".join(runtime_pkgs))   # lean (runtime stage)
    (out / "pip-target.txt").write_text(target)
    # ONE spec per line → consumed via `uv pip install -r`. Critical for PEP 508 direct references
    # (e.g. spaCy models `name @ https://…whl`) whose internal spaces an unquoted shell `$(cat …)`
    # would split into broken args.
    (out / "pip-specs.txt").write_text("\n".join(pip_specs) + ("\n" if pip_specs else ""))

    print(f"📦 apt packages ({len(pkgs)}): {pkgs}")
    print(f"📦 runtime apt ({len(runtime_pkgs)}): {runtime_pkgs}")
    print(f"🐍 install target: {target}")
    print(f"🐍 pip specs ({len(pip_specs)}): {pip_specs}")


if __name__ == "__main__":
    main()
