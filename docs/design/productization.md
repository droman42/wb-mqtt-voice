# Productization — the Domovoy umbrella (voice ↔ bridge ↔ satellite)

**Status: AGREED 2026-07-08 (joint productization session, BUILD-20 — run from `~/development`
with both repos' CLAUDE.md + memory loaded, acting as both projects' Claude). D-1..D-12
user-approved. This document is the shared spec (the `problem_reports.md` precedent: shared
spec in one home, per-side specifics defer to it); the bridge's side is
`../wb-mqtt-bridge/docs/design/productization_bridge.md`. MIGRATION NOTE: once D-2's commons
restructuring lands (BUILD-21), this document moves to `domovoy-commons/docs/design/` and a
pointer stays here.**

Two products that are valuable standalone — Irene (the voice assistant) and wb-mqtt-bridge
(the smart-home hub) — and much more valuable together: **a fully local, privacy-first,
Russian-first voice-controlled smart home**. They are contract-coupled (the canonical
`DeviceCommand` boundary, ARCH-26), not code-coupled, which is what makes a joint product
possible without merging anything. This design defines the umbrella: name, shared-asset
homes, cross-repo idea discipline, work/release coordination, and delivery harmonization.

## 1. Agreed decisions

- **D-1 — Product name: Domovoy (Домовой)**, pending an availability sweep (GitHub/PyPI/domain
  — first commons-board task; known benign collision: the dormant PyPI `domovoi` AWS toolkit).
  The Slavic household spirit: lives in the house, guards it, **never leaves** — the privacy
  story in one word. The wake-word personas (Ирина, Валера, Наташа) are *voices of* the
  product, not the product. Runners-up recorded: Penates, Terem, Ochag. Rejected: Irene Suite
  (brands the suite on one persona; bridge-standalone users under a voice brand), `wb-*`
  (contradicts the hardware-neutral ambition, see D-4's HA example), Domostroy (connotations).

- **D-2 — Exactly ONE umbrella repo = eval-commons, repurposed and renamed `domovoy-commons`.**
  No new commons repos (no separate wb-ui-kit / wb-contracts / wb-ops repos). eval-commons is
  already the neutral ground both products touch, already has pin discipline and a CLAUDE.md.
  Renaming keeps GitHub redirects; the `file://` refs + `pip install -e ../eval-commons` paths
  in both repos' `eval/` get a one-time update. Target layout:

  ```
  domovoy-commons/
  ├── board/            # cross-repo initiative ledger (PROD-N)      — regime 3
  ├── process/          # ops spec, shared invariant blocks, report policy spec
  ├── docs/design/      # cross-repo design docs
  ├── eval/             # the test framework, as today (own package + tag)
  ├── packages/core-py/ # shared runtime code: logging, dynamic loader — regime 2
  ├── packages/ui-kit/  # stylebook + shared components (next release)
  ├── contracts/        # pins of product-owned artifacts + crossover fixtures — regime 1
  └── site/             # landing page (GitHub Pages)
  ```

- **D-3 — Three ownership regimes inside the commons** (this is the conceptual hygiene that
  makes one repo safe):
  1. **Generated contracts — owned by a product repo; commons holds only pins.** The catalog /
     openapi stay bridge-owned; the WS wire protocol (`docs/guides/websocket-api.md`) stays
     voice-owned. `cross-repo-source-of-truth` is unchanged. `crossover_fixtures.json` is
     genuinely bidirectional and stays co-owned in `contracts/`.
  2. **Co-owned shared code — commons owns it; products pin versions.** The eval framework,
     and the first two extractions (D-8). Ownership *flips* on extraction: voice stops owning
     the loader and becomes consumer #1.
  3. **Process & product artifacts — commons owns them.** Board, ops spec, invariant blocks,
     compat manifests, landing page.
  Packages are **versioned separately by prefixed tags** (`eval-vX`, `core-py-vX`, `ui-kit-vX`,
  own `pyproject.toml`/`package.json` each) so a test-framework tweak never forces a version
  event on a production dependency.

- **D-4 — Cross-repo idea discipline: `design-then-implement`, lifted one level.** The commons
  gets a light ledger (`PROD-N` in `board/`), journal, memory dir; **cross-repo idea sessions
  run from the commons repo** (its CLAUDE.md instructs loading sibling context). A cross-repo
  idea = a PROD design task; deliverable = a design doc. **Placement rule:** a design defining
  a concept/contract both products consume lives in commons `docs/design/`; a design whose
  primary artifact is one repo's code lives in that repo's `docs/design/` even when the
  session ran in commons. On completion the PROD task **delegates**: per-repo implementation
  tasks, each verified at intake per the receiving repo's `task-start-reconciliation` and
  given a local ID. The board entry lists the delegated IDs but **never asserts their status**
  (per-repo ledgers own status; `one-active-journal` principle applied to the board).
  Stress-test example, recorded as a future PROD design: **Home Assistant support in parallel
  to Wirenboard** — if the canonical DeviceCommand contract survives HA unchanged, voice gets
  zero tasks (HA = a new driven adapter behind the bridge's ports + maybe a contract minor
  bump); if voice *does* need changes, the contract leaked WB-specifics. The delegation
  pattern itself is an architectural finding.

- **D-5 — The board entry IS the outbox (uncommitted cross-repo filings retired).** Today a
  sibling filing sits uncommitted in the receiver's working tree — fragile (invisible until
  noticed, lost to a `git clean`). New mechanism: the delegation text is **committed in
  commons** (co-owned ground — being writable by both sides is its purpose; the
  no-cross-repo-writes rule doesn't apply to it). Receiving session pulls the delegation,
  verifies, files under a local ID, writes that ID back to the board entry. Nothing lives
  uncommitted; intake verification survives intact. (Until BUILD-21 lands, the old uncommitted
  mechanism remains in force — this session's own bridge filings use it, a deliberate last use.)

- **D-6 — The ESP32 satellite is a THIRD PRODUCT repo, `domovoy-satellite` — starts NOW.**
  Not part of commons (it's a product with its own lifecycle: PCB spins/BOM/enclosures move on
  a hardware cadence, SKIDL/KiCad + ESP-IDF/PlatformIO toolchain, gerber/firmware-binary
  artifacts). Full per-repo kit: own CLAUDE.md (same invariant family; leans on the bridge's
  `HW-GATED` marker), ledger, journal. **Relocation:** the satellite-side design corpus moves
  out of voice (`docs/design/esp32_satellite.md` + the superseded `ws_esp32_transport.md`
  lineage, `docs/architecture/esp32.md`, the `esp32-*.dot/png` diagrams); the top-level
  `ESP32/` tree (docs + firmware) is **outdated and is DELETED, not migrated** (user verdict
  2026-07-08; dead-code rule — the satellite repo starts from the design docs + the live wire
  protocol, not from that code). What STAYS in voice: everything server-side — the WS protocol
  doc (voice owns the server half of the wire; `ws-protocol-doc-canonical` already names ESP32
  firmware as a client), `irene/satellite/` (the Python satellite runner, release-critical),
  the client registry/provisioning/CSR code, the nginx Plane-B ansible glue, and frozen
  review/archive docs (`docs/review/esp32_wakeword_review.md`, `docs/archive/*`). The
  satellite repo **pins** the WS protocol by version, exactly as voice pins the bridge catalog.

- **D-7 — Common firmware/PCB pieces across future satellite variants live WITHIN
  domovoy-satellite** — they graduate to commons only if a second firmware-consuming repo ever
  exists (rule of two, D-8).

- **D-8 — Shared-code extraction rule (rule of two):** code moves into
  `commons/packages/core-py` only when the second consumer is real and committed — nothing
  speculative. **First two extractions, filed now:** (1) the **dynamic code loader** (voice
  owns today; bridge adoption wanted — voice becomes consumer #1, bridge #2); (2) the
  **logging scheme** (startup-rollover + timed-rotation family that BUG-30 hand-ported
  verbatim from the bridge — the exact drift pattern this design retires). The rest surface
  naturally. `ui-kit` enters as a commons package next release (stylebook + shared React
  components consumed as a versioned npm package by both config UIs); it gets its own repo
  only if it ever needs its own cadence.

- **D-9 — Config UI: two apps + shared kit now; one-shell-with-plugins stays reachable.** The
  kit's component boundaries are designed so a future single configurator shell with
  per-product plugins remains possible next release — but no plugin framework before two real
  plugins exist.

- **D-10 — Work coordination: KEEP the per-repo ledgers; no GitHub Projects / Jira.** The
  ledger system's properties (in-context every session, greppable, machine-guarded by
  `check_scope.py`, offline, versioned with the code) are exactly right for a one-person +
  Claude shop; external trackers coordinate *people*. What was missing is only the cross-repo
  layer — solved by D-4/D-5's board.

- **D-11 — Releases: per-component semver + calver compatibility sets.** Each component keeps
  its own semver + changelog (voice **0.5.x** — renumbered from the inherited `15.0.0`, which claimed
  fourteen major releases that never happened; see REL-4 — bridge toward 1.0, contract explicitly
  semver-ish: additive = minor / breaking = major, ui-kit + firmware when they exist). A **suite release
  is a tested-together statement, not a lockstep version**: a manifest in commons — e.g.
  "Domovoy 2026.07 = voice v0.5.0 + bridge v1.0.0 + contract v1.4 + images …" — gated on the
  eval-commons cross-suites passing against exactly those pins. **Contract distribution
  formalized:** the bridge tags contract releases (`contract-vN`, artifacts attached); the
  voice re-pin becomes a script (`make repin CONTRACT=vN` writing the stamp) + a
  staleness check at voice gates (pin vs newest bridge contract tag) — staleness becomes a
  machine failure, not a memory note. No separate contracts repo.

- **D-12 — Delivery harmonization (BUILD-18 made concrete) + the CLAUDE.md fix.** The
  converged ops pattern (sdcard clone update-time-only, `/mnt/data/<name>-config` runtime
  tree, repo-owns-config rsync, `.env` secrets, systemd oneshot with `RequiresMountsFor=
  /mnt/data` ONLY, GHCR pull-not-build, log rotation, 127.0.0.1 healthchecks, start-period >
  fleet boot) is written ONCE as a **normative ops spec** in `commons/process/` with a
  conformance checklist each repo's `ops/` satisfies; shared *scripts* are extracted only when
  a third consumer arrives (satellite / BUILD-13 Pi image — rule of three). **Shared CLAUDE.md
  invariants** get one normative source in `commons/process/`; each repo keeps its copy
  between markers (CLAUDE.md must live in-repo to be in-context) with a drift-guard script
  (check_scope spirit, contract-pin mechanic) failing when a marked block diverges. Genuinely
  per-repo invariants (`ws-protocol-doc-canonical`, `durable-actions`) stay outside markers;
  same-slug-different-meaning cases are **renamed apart** (`config-master-canonical`: voice =
  one canonical TOML exists; bridge = the JSON tree is canonical, no single file).
  **Landing page** = `commons/site/` (GitHub Pages): the joint story, per-product blurbs +
  screenshots, honest quickstart, routing into per-repo docs — narrative + routing ONLY, never
  duplicating reference material (`user-facing-docs-are-done` principle); the suite manifest
  is its "current release" section. **Problem-report policy** (envelope, redaction regex, rate
  limits, retention, labels — today mirrored in prose across two designs) becomes one
  normative spec in `commons/process/`; `wb-user-reports` stays a separate private repo (a
  privacy boundary, not an organizational one) and consumes the spec, as do both collectors.
  Spec-level unification only — no shared library across Python/TS at household scale.

## 2. Drift inventory (BUILD-18 evidence, verified this session)

Real divergences between the two CLAUDE.md rule sets (the D-12 markers/guard target these):
- `config-master-canonical` — same slug, **opposite meanings** (rename apart).
- Priority tags `[P0]-[P2]` + the alias file exist only on the bridge.
- `check_scope.py` runs in bridge CI (`ledger-guard`); voice runs it manually at gates.
- `work-on-main` — bridge specifies commit granularity + no-PRs; voice doesn't.
- File naming (`RELEASE_PLAN`/`RELEASE_JOURNAL` vs `action_plan`/`action_plan_journal`) —
  acceptable dialect, recorded so the invariant blocks parameterize over it.
- NOT drift (checked, contrary to first impression): journal direction — both are
  newest-on-top.
Beyond CLAUDE.md: the hand-copy code convergences (log rotation BUG-30/OPS-12; update.sh
shapes; INSTALL.md structure; retention constants) — retired by D-8/D-12.

## 3. Commons seed backlog (transplant into `board/` as PROD-N at BUILD-21)

1. Name availability sweep (GitHub/PyPI/domain) → lock D-1.
2. Repo rename + restructure to the D-2 layout; re-point both consumers' `eval/` refs.
3. Board bootstrap (PROD ledger conventions, CLAUDE.md for commons incl. the D-4 session rule).
4. Normative ops spec (D-12) + per-repo conformance delegations.
5. Shared CLAUDE.md invariant blocks + drift guard (D-12) + per-repo adoption delegations.
6. Problem-report policy spec (D-12).
7. Contract tagging + scripted re-pin + staleness gate (D-11) — delegations both sides.
8. core-py package bootstrap; loader + logging extractions (D-8).
9. Landing page (D-12) + suite manifest (D-11).
10. ui-kit package (D-8/D-9, next release).
11. FUTURE PROD design: Home Assistant in parallel to Wirenboard (D-4's stress test).

## 4. Follow-up tasks filed from this design

Voice (this ledger): **BUILD-21** (commons bootstrap: sweep + rename + restructure + re-point),
**BUILD-22** (domovoy-satellite bootstrap + D-6 relocation/deletion), **BUILD-23** (CLAUDE.md
invariant blocks + drift guard, voice side), **BUILD-24** (scripted re-pin + staleness check,
voice side), **ARCH-42** (extract dynamic loader → core-py, design first), **ARCH-43**
(extract logging → core-py, design first); **BUILD-18** annotated (narrows to voice-side ops
conformance once the D-12 spec exists).

Bridge (filed uncommitted per `cross-repo-source-of-truth` — the last use of the old
mechanism, see D-5): proposed **VWB-29** (contract release tagging + artifacts), **CORE-7**
(adopt core-py dynamic loader), **OPS-14** (adopt core-py logging), **OPS-15** (ops-spec
conformance), **OPS-16** (invariant blocks + drift guard, bridge side) — sibling design note
`docs/design/productization_bridge.md`.

Repo census after this design: voice, bridge, **domovoy-commons** (renamed eval-commons),
**domovoy-satellite** (new), wb-user-reports (private) — plus the pre-existing library
siblings (asyncwebostv, pymotivaxmc2, wakeword-training), unaffected.
