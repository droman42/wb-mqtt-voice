#!/usr/bin/env python3
"""Derive the flat Docker build inputs from the build-analyzer's JSON output.

The analyzer (`irene.tools.build_analyzer --json`) emits build-requirements.json for a config profile;
this turns it into the small files the builder/runtime stages consume — keeping the Dockerfiles free of
inline multiline Python (which the Dockerfile parser cannot handle).

Usage:  python derive_build_reqs.py <build-requirements.json>  [--platform linux.ubuntu]  [--out /tmp]
Writes (into --out, default /tmp): system-packages.txt, python-deps.txt, uv-extras.txt, python-modules.txt
"""
import argparse
import json
import re
from pathlib import Path

# A pyproject EXTRA name (e.g. "asr-onnx") vs a package SPEC (e.g. "fastapi>=0.100.0", "uvicorn[standard]").
# The analyzer's `python_dependencies` mixes both: extra names go to `uv sync --extra`, specs to `uv pip
# install`. (The cleaner fix — have the analyzer map provider deps to the extra that provides them and emit
# extra names only — is tracked as the BUILD-5 "confirm/fix uv sync --extra" item.)
_EXTRA_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9._-]*$")
# Build-only apt packages — needed in the builder stage, NOT the (lean) runtime image.
_BUILD_ONLY = {"build-essential", "pkg-config", "gcc", "g++", "make", "cmake"}


def _is_build_only(pkg: str) -> bool:
    return pkg in _BUILD_ONLY or pkg.endswith("-dev")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("requirements", help="path to build-requirements.json")
    ap.add_argument("--platform", default="linux.ubuntu", help="system-package set to extract")
    ap.add_argument("--out", default="/tmp", help="output directory for the flat files")
    args = ap.parse_args()

    data = json.loads(Path(args.requirements).read_text())
    out = Path(args.out)

    pkgs = data.get("system_packages", {}).get(args.platform, [])
    deps = data.get("python_dependencies", [])
    modules = data.get("python_modules", [])

    extra_names = [d for d in deps if _EXTRA_NAME.match(d)]
    pip_specs = [d for d in deps if not _EXTRA_NAME.match(d)]

    # The bridge-style install target: `uv pip install .[extra1,extra2]` (or just `.`), plus the loose
    # package specs, into the /opt/venv the runtime image copies.
    target = "." if not extra_names else f".[{','.join(extra_names)}]"

    runtime_pkgs = [p for p in pkgs if not _is_build_only(p)]

    (out / "system-packages.txt").write_text(" ".join(pkgs))            # all (builder stage)
    (out / "runtime-packages.txt").write_text(" ".join(runtime_pkgs))   # lean (runtime stage)
    (out / "pip-target.txt").write_text(target)
    (out / "pip-specs.txt").write_text(" ".join(pip_specs))
    (out / "python-modules.txt").write_text("\n".join(modules))

    print(f"📦 apt packages ({len(pkgs)}): {pkgs}")
    print(f"📦 runtime apt ({len(runtime_pkgs)}): {runtime_pkgs}")
    print(f"🐍 install target: {target}")
    print(f"🐍 pip specs ({len(pip_specs)}): {pip_specs}")
    print(f"📋 modules: {len(modules)}")


if __name__ == "__main__":
    main()
