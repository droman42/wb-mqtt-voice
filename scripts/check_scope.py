#!/usr/bin/env python3
"""
check_scope.py — release-scope drift guard (invariant `single-task-ledger`).

The task ledger (docs/RELEASE_PLAN.md) is the single source of scope + status.
Review/design docs are frozen evidence that link UP to ledger task IDs. This script
proves nothing has drifted between them. Run it at each gate; wire into CI later.

Reports (and exits non-zero on) :
  1. ORPHAN finding      — a task ID referenced in a review/design doc but NOT declared
                           in the ledger (scope hiding in a review doc — `single-task-ledger`).
  2. DEAD evidence link  — a file named in the ledger's "Review documents" index that
                           does not exist on disk.
  3. UNINDEXED review    — a docs/review/*.md that the ledger index never references
                           (stray evidence / possible un-rolled-up scope).

Informational (never fails the build):
  - Ledger status summary (open / done / paused per workstream).

Usage:  python scripts/check_scope.py        (from repo root)
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "docs" / "RELEASE_PLAN.md"            # active: open + paused/partial tasks + the index
LEDGER_DONE = ROOT / "docs" / "RELEASE_PLAN_DONE.md"  # frozen: completed [x] tasks (one ledger, two files)
REVIEW_DIRS = [ROOT / "docs" / "review", ROOT / "docs" / "design"]

# Workstream prefixes that denote a real task ID (avoids matching P0-1, v1.0, file:line, …)
ID_RE = re.compile(r"\b((?:ARCH|QUAL|TEST|UI|DOC|BUILD|ASSET|REL|BUG|I18N)-\d+)\b")
# A task DECLARATION line in the ledger:  - [ ] **QUAL-27** …   /  - [x] **ARCH-5** …
DECL_RE = re.compile(r"^- \[([ x~])\] \*\*((?:ARCH|QUAL|TEST|UI|DOC|BUILD|ASSET|REL|BUG|I18N)-\d+)\*\*")


def declared_ids(text: str) -> dict[str, str]:
    """ID -> status char (' '=open, 'x'=done, '~'=paused) from ledger declaration lines."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        m = DECL_RE.match(line)
        if m:
            out[m.group(2)] = m.group(1)
    return out


def indexed_evidence_files(text: str) -> dict[str, bool]:
    """Map each index-row evidence file -> exists-marker (`[x]` on its row).

    A row marked `[x]` asserts the file exists (so a missing file = DEAD link); rows
    without `[x]` are planned docs produced later by their review task (not yet expected).
    """
    out: dict[str, bool] = {}
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        m = re.search(r"`([\w./-]+\.md)`", line)
        if not m:
            continue
        out[m.group(1)] = ("`[x]`" in line)
    return out


def main() -> int:
    if not LEDGER.exists():
        print(f"FATAL: ledger not found at {LEDGER}", file=sys.stderr)
        return 2
    ledger_text = LEDGER.read_text(encoding="utf-8")
    # The ledger spans two files (`single-task-ledger`): active + frozen done-archive. Declarations
    # come from BOTH (else references to completed tasks read as orphans); the index lives
    # only in the active file.
    done_text = LEDGER_DONE.read_text(encoding="utf-8") if LEDGER_DONE.exists() else ""
    declared = declared_ids(ledger_text + "\n" + done_text)
    indexed = indexed_evidence_files(ledger_text)

    review_files = sorted(p for d in REVIEW_DIRS if d.exists() for p in d.glob("*.md"))

    orphans: dict[str, set[str]] = {}      # id -> set(files referencing it)
    unindexed: list[str] = []
    for p in review_files:
        rel = p.relative_to(ROOT).as_posix()
        text = p.read_text(encoding="utf-8")
        for tid in set(ID_RE.findall(text)):
            if tid not in declared:
                orphans.setdefault(tid, set()).add(rel)
        # is this review doc referenced by the ledger index (by basename)?
        if p.name not in {Path(f).name for f in indexed}:
            unindexed.append(rel)

    # dead evidence links: index marks a file `[x]` (exists) but it's missing on disk.
    # Files without `[x]` are planned docs produced later by their review task — not dead.
    on_disk = {p.name for p in review_files}
    dead: list[str] = []
    for f, exists_marked in indexed.items():
        if exists_marked and Path(f).name not in on_disk:
            dead.append(f)

    # stranded completions: a task DECLARED [x] in the ACTIVE file violates single-task-ledger —
    # completion must MOVE the entry to the done-archive in the same change, not flip it in place
    # (three entries drifted exactly this way on 2026-07-06 before this check existed).
    stranded = re.findall(r"^- \[x\] \*\*([A-Z]+-\d+)\*\*", ledger_text, flags=re.M)

    # misfiled tasks: a task's ID prefix must match its enclosing workstream section, in BOTH
    # files (a BUILD task under "### Architecture (ARCH)" is a filing error — twice on 2026-07-06).
    def misfiled(text: str, which: str) -> list[str]:
        out, section = [], None
        for line in text.split("\n"):
            if line.startswith("### "):
                m = re.search(r"\(([A-Z]+)\)", line)
                section = m.group(1) if m else None
            m = re.match(r"^- \[[ x]\] \*\*([A-Z]+)-(\d+)\*\*", line)
            if m and section and m.group(1) != section:
                out.append(f"{m.group(1)}-{m.group(2)} under ({section}) [{which}]")
        return out
    misplaced = misfiled(ledger_text, "active") + misfiled(done_text, "done")

    failed = False
    print("== check_scope: release-scope drift guard ==\n")

    if stranded:
        failed = True
        print("STRANDED completions ([x] task entries still in the ACTIVE plan — move them to RELEASE_PLAN_DONE.md):")
        for tid in stranded:
            print(f"  - {tid}")
        print()
    if misplaced:
        failed = True
        print("MISFILED tasks (ID prefix does not match the enclosing workstream section):")
        for t in misplaced:
            print(f"  - {t}")
        print()
    if orphans:
        failed = True
        print("ORPHAN findings (task ID in a review/design doc but NOT in the ledger):")
        for tid, files in sorted(orphans.items()):
            print(f"  - {tid}  (referenced in: {', '.join(sorted(files))})")
        print()
    if dead:
        failed = True
        print("DEAD evidence links (ledger index names a file that doesn't exist):")
        for f in sorted(dead):
            print(f"  - {f}")
        print()
    if unindexed:
        # informational-strong: stray evidence not wired into the ledger index
        print("UNINDEXED review docs (exist on disk but not in the ledger index):")
        for f in sorted(unindexed):
            print(f"  - {f}")
        print()

    # informational status summary
    done = sum(1 for s in declared.values() if s == "x")
    paused = sum(1 for s in declared.values() if s == "~")
    open_ = sum(1 for s in declared.values() if s == " ")
    print(f"Ledger: {len(declared)} tasks  —  {done} done · {open_} open · {paused} paused.")

    if failed:
        print("\nFAIL: scope drift detected (orphan findings and/or dead links). Reconcile the ledger.")
        return 1
    print("\nOK: no orphan findings, no dead evidence links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
