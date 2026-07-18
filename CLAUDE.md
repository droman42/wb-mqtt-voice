# locveil-voice — agent notes

## Development process — invariants (apply to EVERY task)

The always-on working discipline for development in this repo (the task ledger drives the release effort today,
but these rules apply to any task). **Single source of truth** (relocated here from `docs/RELEASE_PLAN.md` on
2026-06-27 so they're always in context = always enforced). Referenced by **name** (stable slug), never by number
— names survive adding/removing/reordering, so references never break.

- **`work-on-main`** — Work on `main`; branch only when explicitly asked.
- **`config-master-file`** — `config/config-master.toml` is the canonical config reference (a release-time
  `config-example.toml` is a later story). _Renamed from `config-master-canonical` 2026-07-11 (HK-2: the bridge's
  same-named rule renamed apart as `config-master-tree`); frozen archives keep the old slug._
- **`hexagonal-architecture`** — Architecture target = Hexagonal; dependencies point inward (domain → application →
  ports → adapters). Don't add backwards/cross-layer imports (enforced by the import-linter contracts).
- **`config-ui-stays-functional`** — `config-ui` is a first-class consumer of backend contracts. Any task that changes
  one of these **must update config-ui in the same change and leave it building/type-checking clean**:
  - **Donation schema/format** (`assets/donations/v1.0.json`, `ParameterSpec`/`MethodDonation` shape) → config-ui
    editors (`ParameterSpecEditor`, `Token/SlotPatternsEditor`, `Examples/LemmasEditor`), its **AJV** validation, `src/types/*`.
  - **Config schema** (`CoreConfig` / `config-master.toml`) → `ConfigSection` editors, `/configuration/config*` calls, `src/types/*`.
  - **REST API endpoints / parameter schemas / analysis endpoints** → `src/utils/apiClient.ts`, the analysis components.
  - Definition-of-done addendum: `cd config-ui && npm run check && npm run build` passes (`check` = type-check **+**
    the strict ESLint gate; **`build` = the Voice Workbench plugin bundle + manifest fragment** — the standalone app
    retired at UI-17 per the HK-11 owner ruling; the shell consuming it is commons `packages/workbench`).
    _Pairs with `user-facing-docs-are-done` — config-ui is the user-facing **app**._
- **`ws-protocol-doc-canonical`** — `docs/guides/websocket-api.md` is the **single source of truth for the
  WebSocket wire protocol** (`/ws/audio`, `/ws/audio/reply`, `/ws/output`, `/ws/observe`) — a hand-written
  reference, deliberately not generated tooling. Any change to a WS endpoint or message shape (the
  `webapi_router` WS endpoints, `backend/src/locveil_voice/satellite/`) **updates that document in the same change** — it is what
  clients are built against (the satellite runner, the future ESP32 firmware, locveil-commons'
  `ws_audio_provider`). Design docs hold rationale and **defer to it** (e.g. `python_satellite.md` §3 points
  there); never duplicate frame tables elsewhere. Sibling rule: `../locveil-commons/CLAUDE.md` names this
  document as the protocol truth its providers implement.
- **`cross-repo-source-of-truth`** — for any artifact **shared with a sibling repo**, know which side *owns* it and
  don't write across the boundary the wrong way.
  - **The Irene↔bridge catalog / canonical-command contract is owned by `../locveil-bridge`** (its generator / source
    of truth). This repo is a **consumer** holding TWO stamped copies that move together via `scripts/repin.py`
    (one command, same tag — never let them diverge): the **local push-time pin** `contracts/pins/catalog/`
    (BUILD-34; hermetic schema conformance in `test_catalog_contract_conformance.py`) and the **shared crossover
    pin** in `../locveil-commons/contracts/pins/catalog/` (TEST-17; the eval framework's mock bridge + the
    release-cadence cross-suite). Both are one-way *inward* syncs from the bridge's tagged artifacts — never
    hand-edit a copy, treat it as source, or write into the bridge repo.
  - **The problem-report wire protocol is owned by `../locveil-commons`** (HK-3/PROD-6): the machine core
    `contracts/report-protocol/report-protocol.json` (moved from `process/report-protocol/` at the PROD-16
    restructure), tagged `report-protocol-vN`; normative prose `process/problem-reports.md`. This repo **pins**
    it at `contracts/pins/report-protocol/` (one-way inward sync — never hand-edit; re-pin on a vN bump, see
    the pin folder's README) and validates the collector's emitted surface against the pin in
    `backend/tests/test_report_protocol_conformance.py`.
  - **Contract layout/coherence is guarded by the vendored `scripts/contract_guard.py`** (commons
    `packages/contract-guard/`, pinned `contract-guard-v3`, BUILD-33/BUILD-37/BUILD-41) — same consumption model as the
    scope guard: **never edit the vendored file**, re-pin to move. Registry + per-pin mechanics:
    `contracts/README.md`; convention: `../locveil-commons/process/contracts.md`.
  - **`../locveil-commons/eval` is the shared test framework** — test *execution logic* (providers/scorers/judge) lives there,
    changed **there not here** (this repo carries only eval YAML + the thin `eval/Makefile`; see *Testing &
    evaluation*). This repo *does* write to `locveil-commons` (it co-develops the framework and owns the contract pin
    above) — the asymmetry with the bridge, which only reads it.
  - **Cross-repo work travels two ways** (the pre-board uncommitted-filing mechanism is retired): a cross-repo
    *initiative* goes through the **board** (`cross-repo-board` block below — delegation text committed in the PROD
    entry, local ID written back); a direct *operational* filing (a bug report against the bridge, a contract
    request) stays repo-to-repo — and any filing that lands here is verified per `task-start-reconciliation` and
    gets its own local ID before work starts.
  - The contract's *content* (schemas/endpoints/task pairing) lives in `docs/design/mqtt_integration.md` §14 + the
    `voice-bridge-catalog-contract` memory — **referenced, not duplicated here** (avoid drift). Pairs with
    `../locveil-bridge/CLAUDE.md`'s same-named invariant (the other direction).
- **`read-at-start-record-at-completion`** — AFFIRMATIVE & NON-NEGOTIABLE until release.
  - **At task START:** read **not only the ledger item but also its related review doc(s)** (per the ledger's index)
    — the ledger item is a spine entry; the review doc holds the evidence, file:line refs, detail.
  - **At task COMPLETION:** flip status in the ledger and add a dated entry to `RELEASE_JOURNAL.md` — **in the same
    change.** Do **not** re-edit a review doc's status (frozen evidence with a one-time `→ tracked as <ID>` pointer);
    the only reason to edit a review doc is if a *finding itself* is wrong/obsolete (annotate, don't flip status).
- **`ledger-dialect`** — voice's instantiation of the shared ledger triad (pinned `shared-invariants` block below;
  mechanics: `../locveil-commons/process/ledger-discipline.md`): active `docs/RELEASE_PLAN.md` + frozen
  `docs/RELEASE_PLAN_DONE.md` (workstream sections by ID prefix, IDs ascending; every task tagged `[release]` or
  `[deferred]` — release is blocked until every `[release]` task is `[x]`) + journal `docs/RELEASE_JOURNAL.md`
  (entries reference IDs, never assert status); rotation archives under `docs/archive/`. Guard: vendored
  `scripts/scope_guard.py` + `.scope-guard.toml` (BUILD-30 cutover) — **never edit the vendored file**; re-pin.
  - Design deliverables live under `docs/design/`, review deliverables (frozen evidence) under `docs/review/`;
    both are listed in the ledger's review/design index, and fixes/implementations are filed as fresh tasks.
  - **Carve-out:** a lockfile-only dependency bump that doesn't change `pyproject.toml` / `config-ui/package.json`
    intent needs no ledger ID (journal line only); a deliberate version decision is a normal task and does.
  - **At intake** (per `task-start-reconciliation`): a task found narrowed, already-addressed, or scope-drifted
    means **STOP and consult the owner** before doing the work or editing the ledger.
- **`no-type-checking`** — No `if TYPE_CHECKING:` import guards. Imports are honest: if a type can be imported at
  runtime, import it at module top and annotate with the real symbol. A `TYPE_CHECKING` block is a band-aid for an
  import cycle, and a cycle is an architecture smell (dependencies not pointing inward — `hexagonal-architecture`). The
  fix is to **break the cycle** (move the shared type to a lower layer / use a port), not hide it from the runtime.
  When touching a file that has such a block, remove it. _(QUAL-32 tracks the residual sweep; new code complies from the start.)_
- **`durable-actions`** — A fire-and-forget action that **promises effects beyond the current interaction**
  (fires later, changes/reports something later) MUST be launched with `durable=True`, and its handler MUST
  override `rearm_durable_action` (JSON-serializable launch kwargs; re-arm reuses the record's `action_name`).
  Never hand-roll future scheduling (`asyncio.sleep` promises / ad-hoc `create_task` timers) outside the F&F
  launch — invisible to stop/listing, dies silently on restart. Full contract: `docs/design/durable_actions.md`
  §3 (design) + `docs/guides/howto-new-intent.md` (authoring prose). The substrate persists to
  `<assets_root>/state/` — asset-managed and volume-mounted, **never** the deletable `cache/`.
- **`user-facing-docs-are-done`** — voice's dialect of the org docs convention (normative:
  `../locveil-commons/process/user-docs.md`; shared digest in the pinned block below). **The scope authority is
  `docs/manifest.json`** — every user-facing doc is a manifest node (roots: `README*`, `CONTRIBUTING.md`,
  `docs/QUICKSTART.md`, `docs/guides/`, `docs/architecture/`, `docs/images/`, **`ops/INSTALL.md`**), coherence-tested
  by `backend/tests/test_docs_manifest.py`; a new doc gets its node in the same commit. A non-root `README*` (e.g.
  `eval/README.md`) stays in scope when the task touches that subsystem. For **every** task, before completion:
  does the change alter behavior a manifest node describes? Record the answer as the **docs-verdict line in the
  DONE-ledger entry** (`docs: <node-ids>` / `docs: none — <why>`; enforced by scope-guard from
  `docs_verdict_since`); staleness you cause is fixed in the same change, staleness you discover is filed against
  the next release gate. Docs are narrative for a reader who does **not** know the codebase — **no internal
  tracking language** (task IDs, ledger refs, gate counts, file:line, raw internal symbols) unless the doc already
  teaches them as user-facing names. **Diagrams are docs too:** a `.dot` source and its render are one unit —
  update both. _Pairs with `config-ui-stays-functional` (the user-facing **app**; this is the user-facing **docs**)._

- **`problem-report-inbox`** — problem reports (ARCH-30) land as tickets in the private
  `locveil/locveil-reports` repo (renamed/moved from `droman42/wb-user-reports` 2026-07-11; old name redirects);
  a cloud Claude triages each and leaves it needing the owner (a fix PR open on
  this repo, or a `needs-owner` escalation). **At the start of a new or resumed session, do a quick, non-blocking
  check** — `gh issue list --repo locveil/locveil-reports --label needs-owner --label lens:voice --state open`
  plus the `fix-pr-open` variant — and if anything is waiting, **mention the count in one line** and offer
  `/inbox`. Never auto-enter the review; the owner decides when. (Skill: `.claude/skills/inbox/`. A `gh` failure —
  no network, no auth — is silently skipped; this check must never block or noise up a normal session.)

## Shared process (pinned blocks — `../locveil-commons/process/claude-md.md`; edit the sources in `process/claude-blocks/`, then re-pin)

<!-- locveil:begin shared-invariants scope-v5 -->
**Locveil shared process invariants** — digest; normative source: `../locveil-commons/process/`
(`ledger-discipline.md`, `claude-md.md`, `user-docs.md`). On disagreement the process files
win. Never edit this block in place — edit in commons, then re-pin (`process/claude-md.md` §3).

- **ledger triad** — active ledger + DONE ledger + one rotating journal; completion MOVES
  the entry to DONE and journals it in the same change; rotation only via an explicit
  `scope_guard.py --rotate` in its own commit; watermarks + mechanics:
  `process/ledger-discipline.md`.
- **every-task-in-the-ledger** — no work without a ledger ID; a doc finding becomes scope
  only when a ledger task declares it.
- **task-start-reconciliation** — before executing any task, verify its claims against repo
  reality; narrow or redefine at intake rather than executing stale text.
- **design-then-implement** — non-trivial changes get a reviewed design doc before code.
- **review-then-remediate** — review findings become ledger tasks before they get fixed.
- **user-facing-docs-are-done** — every completion entry records a docs verdict
  (`docs: <node-ids>` or `docs: none — <why>`) against the repo's `docs/manifest.json`;
  caused staleness is fixed in the same change, discovered staleness is filed against the
  next release gate; scope + manifest schema + style: `process/user-docs.md`.
- **Enforcement** — vendored `scope_guard.py` at a pinned `scope-vX` tag + committed
  pre-commit hook + path-gated `ledger-guard` CI job; hooks and CI run `--check` only.
<!-- locveil:end shared-invariants -->

<!-- locveil:begin cross-repo-board scope-v4 -->
**Locveil cross-repo: the board.** The repos are SIBLINGS on disk — `../locveil-commons`
(umbrella: board, `process/`, shared packages), `../locveil-voice`, `../locveil-bridge`,
`../locveil-satellite`.
Cross-repo initiatives live at `../locveil-commons/board/BOARD.md` (`PROD-N`; council
topics `HK-N`; completed entries in `BOARD_DONE.md`). Delegations arrive as board-as-outbox
text committed inside a PROD entry: pull it, verify per `task-start-reconciliation`, file
it under a LOCAL task ID, execute locally, then write that ID back into the board entry.
The board never asserts a delegated task's status — this repo's ledger owns it. Direct
operational filings between product repos (bug reports, contract requests) stay
repo-to-repo and don't need the board. Cross-repo design sessions and the council run FROM
locveil-commons (convention: `../locveil-commons/process/council.md`); decisions land on
the board, never in chat.
<!-- locveil:end cross-repo-board -->

<!-- locveil:begin contract-triad scope-v7.1 -->
**Locveil contract triad** — digest; normative: `../locveil-commons/process/contracts.md`
(§2–§5) + `process/ledger-discipline.md` §7 (HK-12). On disagreement those files win.
Never edit this block in place — edit in commons, then re-pin (`process/claude-md.md` §3).

- **surface-with-the-artifact** — creating or bumping a versioned surface cuts its owned
  `contracts/<name>/` STAMP + `<family>-vN` tag + registry row in the SAME change; new
  stamps enumerate `artifacts`; an enumerated artifact edited without a version move
  fails at commit (contract-guard v3 CONTENT-DRIFT/ORPHAN-TAG).
- **pins-complete-and-verbatim** — a pin = the owner's full tagged artifact set,
  byte-identical + owner STAMP verbatim + strict PIN.json; it moves ONLY by a deliberate
  re-pin ledger task (the vendored repin tool) — never hand-edits, never auto-fetch.
- **contracts-verdict** — every completion entry records `contracts: <what moved>` or
  `contracts: none — <why>`; "moved" = created, bumped, or FIRST CONSUMED a cross-repo
  surface; owner-side bumps add `re-pin owed: <consumers>`.
- **staleness ladder (§5)** — pre-commit `repin --check` warns (offline-safe, tokenless
  remote-first); push CI fails only on touch-the-family / release workflows / major-gap
  (per-repo config); the `.repin.toml` `[[tool]]` manifest watches vendored guard tags.
<!-- locveil:end contract-triad -->

**Legend — historical numbers → names.** Frozen journal/ledger archives and review docs reference these invariants by
their old number (numbering retired 2026-06-27). Resolve here:
`#1`→`work-on-main` · `#2`→`config-master-file` (was `config-master-canonical`, renamed 2026-07-11) ·
`#3`→`hexagonal-architecture` · `#4`→`config-ui-stays-functional` · `#5`→`read-at-start-record-at-completion`
· `#6`→`single-task-ledger` · `#7`→`one-active-journal` · `#8`→`task-start-reconciliation`
· `#9`→`no-type-checking` · `#10`→`user-facing-docs-are-done`. The names `single-task-ledger` /
`one-active-journal` now resolve to the **ledger triad** (`shared-invariants` block + `ledger-dialect`);
`every-task-in-the-ledger`, `task-start-reconciliation`, `design-then-implement`, `review-then-remediate`
live in the pinned block above (normative: `../locveil-commons/process/`).

## Testing & evaluation

Declarative tests (CLI contracts, streaming-ASR system tests, Russian UX judging) live in
**[`eval/`](eval/README.md) — read that README before touching anything test-related.**

Key things it establishes (don't rediscover the hard way):
- All test *execution logic* (providers, scorers, judge) lives in the sibling repo
  **`../locveil-commons/eval`** — this repo carries only YAML + a thin `eval/Makefile`. Change behavior
  there, not here.
- Run tests via `make` from `eval/` (it wires the `uv` venv + global `promptfoo`), e.g.
  `make cli` (no prerequisites), `make ws TARGET=local|wb7`, `make ux`.
- Tests parameterize over two external axes — **TARGET** (local vs the WB7 controller) and
  **CONFIG** (which Irene config the SUT runs) — via `eval/profiles/*.env`. Never bake an
  endpoint or config into a test case.
- promptfoo env refs are `{{env.VAR}}`, not `${VAR}`.

Status: `make cli` passes; the WS/UX suites are pending recorded audio fixtures and Russian
judge calibration (see `eval/README.md` → Notes/TODO).
