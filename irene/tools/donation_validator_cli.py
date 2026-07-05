"""Donation validation gate (QUAL-67) — schema + contract-wiring, warnings are failures.

QUAL-66 swept the contract-wiring warnings to zero, which is what makes this gate possible:
from here on, ANY wiring warning — a declared-but-unread param, an undeclared `_handle_*`
method — fails the build instead of scrolling past in a boot log. Runs the exact validation
the runtime loader runs (schema strict + `validate_contracts`), over every donation directory
under `assets/donations/`, with no discovery dependence on which handlers a config enables.

CI usage (backend-health gate):  python -m irene.tools.donation_validator_cli --ci-mode
Local:                           irene-donation-validate
"""

import argparse
import asyncio
import sys
from pathlib import Path

from ..core.contract_validator import validate_contracts
from ..core.intent_asset_loader import AssetLoaderConfig, IntentAssetLoader, base_handler_name


def _discover_handler_names(assets_root: Path) -> list:
    """Every donation directory ships; the gate validates ALL of them, not a config's subset.

    Handler MODULE names are inconsistent about the `_handler` suffix (`timer.py` vs
    `random_handler.py`), so pick whichever variant has a module — the wiring validator
    resolves the handler source by this name."""
    handlers_dir = Path(__file__).resolve().parents[1] / "intents" / "handlers"
    donations_dir = assets_root / "donations"
    names = []
    for d in sorted(donations_dir.iterdir()):
        if not d.is_dir() or not (d / "contract.json").exists():
            continue
        short = base_handler_name(d.name)
        names.append(short if (handlers_dir / f"{short}.py").exists() else d.name)
    return names


async def _run(assets_root: Path) -> int:
    handler_names = _discover_handler_names(assets_root)
    if not handler_names:
        print(f"ERROR: no donation directories found under {assets_root / 'donations'}")
        return 2

    loader = IntentAssetLoader(assets_root, AssetLoaderConfig(strict_mode=True))
    try:
        await loader.load_all_assets(handler_names)
    except Exception as e:
        print(f"FAIL: donation loading/schema validation raised: {e}")
        return 1

    failures = []
    for warning in loader.warnings:
        failures.append(f"loader: {warning}")

    report = validate_contracts(loader.donations, strict_parameters=False)
    for handler in report.handlers:
        for error in handler.errors:
            failures.append(f"{handler.handler_name}: ERROR {error}")
        for warning in handler.warnings:
            failures.append(f"{handler.handler_name}: {warning}")

    checked = sum(h.methods_checked for h in report.handlers)
    if failures:
        print(f"FAIL: {len(failures)} finding(s) across {len(handler_names)} handlers "
              f"({checked} methods checked) — warnings are FAILURES here (QUAL-67):")
        for finding in failures:
            print(f"  - {finding}")
        return 1

    print(f"OK: {len(handler_names)} handlers, {checked} contract methods, "
          f"0 errors, 0 warnings (schema strict + wiring, warnings-as-errors)")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Donation schema + contract-wiring gate")
    parser.add_argument("--assets-root", type=Path, default=Path("assets"),
                        help="Assets root containing donations/ (default: ./assets)")
    parser.add_argument("--ci-mode", action="store_true",
                        help="Reserved for parity with the other gates (behavior is identical)")
    args = parser.parse_args()
    sys.exit(asyncio.run(_run(args.assets_root)))


if __name__ == "__main__":
    main()
