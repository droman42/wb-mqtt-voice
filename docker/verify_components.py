#!/usr/bin/env python
"""Build-time gate: every component + provider the baked profile enables must actually import.

Run in each image's runtime stage, against the config it bakes. Catches the class of defect that
BUG-33 shipped: the armv7 image had no `libopenblas.so.0`, numpy could not import, nine components
died at entry-point load — and nothing noticed until the box was on a rack, because everything that
could have caught it (CI gates, the smoke suite) runs on x86_64, where numpy is a manylinux wheel
that vendors its own openblas.

Imports only. No models are downloaded, no config is executed, no service starts.

    python docker/verify_components.py /app/runtime-config.toml
"""
import importlib.metadata as md
import sys
import tomllib
from pathlib import Path


def _entry_points(group: str) -> dict:
    return {ep.name: ep for ep in md.entry_points(group=group)}


def _check(group: str, names: list[str], failures: list[str]) -> None:
    eps = _entry_points(group)
    for name in names:
        ep = eps.get(name)
        if ep is None:
            failures.append(f"{group}:{name} — no entry point is registered under this name")
            continue
        try:
            ep.load()
        except Exception as e:  # ImportError, or anything a module raises at import
            failures.append(f"{group}:{name} — {type(e).__name__}: {e}")


def main() -> int:
    config_path = Path(sys.argv[1])
    config = tomllib.loads(config_path.read_text())
    failures: list[str] = []

    components = [name for name, on in config.get("components", {}).items() if on is True]
    _check("irene.components", components, failures)

    # Providers the profile explicitly enables, per component section that has a `providers` table.
    for section in components:
        providers = config.get(section, {}).get("providers", {})
        enabled = [name for name, cfg in providers.items()
                   if isinstance(cfg, dict) and cfg.get("enabled") is True]
        if enabled:
            _check(f"irene.providers.{section}", enabled, failures)

    if failures:
        print(f"\n✗ {config_path.name}: {len(failures)} enabled entry point(s) do not import:\n", file=sys.stderr)
        for f in failures:
            print(f"    {f}", file=sys.stderr)
        print("\nThis image would start with those components missing. Fix the dependencies "
              "(see pyproject extras + get_platform_dependencies) rather than shipping it.\n", file=sys.stderr)
        return 1

    print(f"✓ {config_path.name}: all {len(components)} enabled components and their providers import")
    return 0


if __name__ == "__main__":
    sys.exit(main())
