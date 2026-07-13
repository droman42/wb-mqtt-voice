#!/usr/bin/env python3
"""repin — generalized consumed-contract re-pin + release-time staleness check (BUILD-24).

The scripted replacement for hand-copy re-pins (`../locveil-commons/process/contracts.md`):
each consumed contract family below is fetched from its OWNER repo's committed artifacts at
a family-named tag (`<family>-vN`), copied verbatim into the pin folder, and stamped with a
strict `PIN.json` (core fields + `files` sha256 map + conformance pointer) that the vendored
contract-guard verifies on every commit.

    python3 scripts/repin.py <family> [--tag TAG]   re-pin (default: the owner's newest tag)
    python3 scripts/repin.py --check                staleness gate: red when any pin trails
                                                    its owner's newest family tag

`--check` is a RELEASE-TIME gate (run it from the REL flow / `make -C eval repin-check`),
never a cross-repo push gate: an owner tagging a new version must not break this repo's CI
(contracts.md §5) — it goes red here only when WE check, and the fix is a deliberate re-pin.
Untagged families (an owner that hasn't stamped the surface yet) pin at the owner's `main`
and go stale when the owner's committed artifact no longer matches the pinned bytes.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Family registry: who owns it, which committed files form the artifact, where the pin
# copies live (`dests` — a family with several consumers updates ALL of them in one run at
# the same tag, so the copies can never diverge), and which local test is each copy's
# layer-2 conformance. `mirror` names owner-STAMP extras copied into PIN.json (consumers
# assert them, e.g. commons test_contracts_pin.py).
FAMILIES = {
    "catalog": {
        "owner_repo": "locveil-bridge",
        "owner_dir": REPO_ROOT / "../locveil-bridge",
        "files": ["contracts/catalog/catalog.golden.json",
                  "contracts/catalog/openapi.json",
                  "contracts/catalog/STAMP.json"],
        "dests": [
            {"path": REPO_ROOT / "contracts/pins/catalog",
             "conformance": "backend/tests/test_catalog_contract_conformance.py"},
            {"path": REPO_ROOT / "../locveil-commons/contracts/pins/catalog",
             "conformance": "locveil-commons eval/tests/test_contracts_pin.py"},
        ],
        "mirror": ["bridge_commit", "catalog_version"],
    },
    "report-protocol": {
        "owner_repo": "locveil-commons",
        "owner_dir": REPO_ROOT / "../locveil-commons",
        "files": ["contracts/report-protocol/report-protocol.json",
                  "contracts/report-protocol/STAMP.json"],
        "dests": [
            {"path": REPO_ROOT / "contracts/pins/report-protocol",
             "conformance": "backend/tests/test_report_protocol_conformance.py"},
        ],
        "mirror": [],
    },
    "esp32-site": {
        "owner_repo": "locveil-satellite",
        "owner_dir": REPO_ROOT / "../locveil-satellite",
        "files": ["provisioning/ansible/templates/esp32-site.conf.j2",
                  "contracts/esp32-site/STAMP.json"],
        "dests": [
            {"path": REPO_ROOT / "contracts/pins/esp32-site",
             "conformance": "backend/tests/test_arch36_tls_e2e.py"},
        ],
        "mirror": [],
    },
}


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, check=True).stdout.strip()


def _git_bytes(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, check=True).stdout


def _newest_tag(repo: Path, family: str) -> str | None:
    def parse(tag: str) -> tuple[int, ...]:
        m = re.fullmatch(rf"{re.escape(family)}-v(\d+(?:\.\d+)*)", tag)
        return tuple(int(x) for x in m.group(1).split(".")) if m else ()
    tags = [t for t in _git(repo, "tag", "-l", f"{family}-v*").splitlines() if parse(t)]
    return max(tags, key=parse) if tags else None


def repin(family: str, tag: str | None) -> int:
    spec = FAMILIES[family]
    owner = spec["owner_dir"].resolve()
    tag = tag or _newest_tag(owner, family)
    ref = tag or "main"
    if tag:
        version = tag[len(family) + 2:]  # "<family>-v" prefix
    else:
        version = None
        print(f"note: {spec['owner_repo']} has no {family}-v* tag yet — pinning at main "
              "(version/tag stay null until the owner stamps)")
    owner_commit = _git(owner, "rev-parse", f"{ref}^{{commit}}")

    blobs: dict[str, bytes] = {}
    files: dict[str, str] = {}
    mirrored: dict[str, object] = {}
    for path in spec["files"]:
        blob = _git_bytes(owner, "show", f"{ref}:{path}")
        name = path.rsplit("/", 1)[-1]
        blobs[name] = blob
        files[name] = hashlib.sha256(blob).hexdigest()
        if name == "STAMP.json" and spec["mirror"]:
            stamp = json.loads(blob)
            mirrored = {k: stamp[k] for k in spec["mirror"] if k in stamp}
        print(f"  {name}  {files[name][:12]}…  ({spec['owner_repo']} @ {ref})")

    for dest_spec in spec["dests"]:
        dest = dest_spec["path"].resolve()
        dest.mkdir(parents=True, exist_ok=True)
        for name, blob in blobs.items():
            (dest / name).write_bytes(blob)
        pin = {"contract": family, "version": version, "tag": tag,
               "owner_repo": spec["owner_repo"], "owner_commit": owner_commit,
               "pinned_by": "locveil-voice scripts/repin.py (BUILD-24)",
               "pin_date": date.today().isoformat(),
               **mirrored,
               "files": files, "conformance": dest_spec["conformance"]}
        (dest / "PIN.json").write_text(json.dumps(pin, indent=2, ensure_ascii=False) + "\n",
                                       encoding="utf-8")
        print(f"pinned {family} @ {ref} → {dest}")
        print(f"  conformance: {dest_spec['conformance']}")
    return 0


def check() -> int:
    stale = 0
    for family, spec in FAMILIES.items():
        owner = spec["owner_dir"].resolve()
        newest = _newest_tag(owner, family)
        for dest_spec in spec["dests"]:
            dest = dest_spec["path"].resolve()
            where = f"{family} ({dest})"
            pin_path = dest / "PIN.json"
            if not pin_path.is_file():
                print(f"  STALE {where}: no PIN.json — never pinned")
                stale += 1
                continue
            pin = json.loads(pin_path.read_text(encoding="utf-8"))
            if newest:
                if pin.get("tag") != newest:
                    print(f"  STALE {where}: pinned {pin.get('tag') or 'untagged'}, "
                          f"owner's newest is {newest} — run scripts/repin.py {family}")
                    stale += 1
                else:
                    print(f"  ok    {where}: {newest}")
            else:
                drifted = [p.rsplit('/', 1)[-1] for p in spec["files"]
                           if hashlib.sha256(_git_bytes(owner, "show", f"main:{p}")).hexdigest()
                           != pin.get("files", {}).get(p.rsplit('/', 1)[-1])]
                if drifted:
                    print(f"  STALE {where}: owner's committed {', '.join(drifted)} no longer "
                          f"matches the pin — run scripts/repin.py {family}")
                    stale += 1
                else:
                    print(f"  ok    {where}: untagged, bytes match owner main")
    if stale:
        print(f"\nSTALE: {stale} pin(s) trail their owner. Re-pin deliberately, "
              "then re-run the conformance tests.")
        return 1
    print("\nOK: every pin is at its owner's newest version.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[1])
    parser.add_argument("family", nargs="?", choices=sorted(FAMILIES),
                        help="consumed contract family to re-pin")
    parser.add_argument("--tag", help="owner tag to pin (default: newest family tag)")
    parser.add_argument("--check", action="store_true",
                        help="staleness gate: red when a pin trails its owner")
    args = parser.parse_args()
    if args.check:
        if args.family or args.tag:
            parser.error("--check takes no family/--tag")
        return check()
    if not args.family:
        parser.error("give a family to re-pin, or --check")
    return repin(args.family, args.tag)


if __name__ == "__main__":
    sys.exit(main())
