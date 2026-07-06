# wb-mqtt-voice — agent notes

## Development process — invariants (apply to EVERY task)

The always-on working discipline for development in this repo (the task ledger drives the release effort today,
but these rules apply to any task). **Single source of truth** (relocated here from `docs/RELEASE_PLAN.md` on
2026-06-27 so they're always in context = always enforced). Referenced by **name** (stable slug), never by number
— names survive adding/removing/reordering, so references never break.

- **`work-on-main`** — Work on `main`; branch only when explicitly asked.
- **`config-master-canonical`** — `configs/config-master.toml` is the canonical config reference (a release-time
  `config-example.toml` is a later story).
- **`hexagonal-architecture`** — Architecture target = Hexagonal; dependencies point inward (domain → application →
  ports → adapters). Don't add backwards/cross-layer imports (enforced by the import-linter contracts).
- **`config-ui-stays-functional`** — `config-ui` is a first-class consumer of backend contracts. Any task that changes
  one of these **must update config-ui in the same change and leave it building/type-checking clean**:
  - **Donation schema/format** (`assets/donations/v1.0.json`, `ParameterSpec`/`MethodDonation` shape) → config-ui
    editors (`ParameterSpecEditor`, `Token/SlotPatternsEditor`, `Examples/LemmasEditor`), its **AJV** validation, `src/types/*`.
  - **Config schema** (`CoreConfig` / `config-master.toml`) → `ConfigSection` editors, `/configuration/config*` calls, `src/types/*`.
  - **REST API endpoints / parameter schemas / analysis endpoints** → `src/utils/apiClient.ts`, the analysis components.
  - Definition-of-done addendum: `cd config-ui && npm run check && npm run build` passes (`check` = type-check **+**
    the strict ESLint gate). _Pairs with `user-facing-docs-are-done` — config-ui is the user-facing **app**._
- **`cross-repo-source-of-truth`** — for any artifact **shared with a sibling repo**, know which side *owns* it and
  don't write across the boundary the wrong way.
  - **The Irene↔bridge catalog / canonical-command contract is owned by `../wb-mqtt-bridge`** (its generator / source
    of truth). This repo is a **consumer**: it **pins its own copy** into `eval-commons/contracts/` — a one-way
    *inward*, version-stamped sync from the bridge's committed artifacts (TEST-17) — and never hand-edits that copy,
    treats it as source, or writes into the bridge repo (re-pin when the bridge's artifact moves).
  - **`../eval-commons` is the shared test framework** — test *execution logic* (providers/scorers/judge) lives there,
    changed **there not here** (this repo carries only eval YAML + the thin `eval/Makefile`; see *Testing &
    evaluation*). This repo *does* write to `eval-commons` (it co-develops the framework and owns the contract pin
    above) — the asymmetry with the bridge, which only reads it.
  - **Cross-repo task filings arrive uncommitted, either direction.** When voice-side work spawns a sibling task (e.g.
    the bridge emitting the artifact), file it into that repo's ledger **but leave it uncommitted** for its maintainer
    to verify against live code + accept; symmetrically, a filing that lands **here** from a sibling is verified before
    accepting (`task-start-reconciliation`) and then needs its own ID (`every-task-in-the-ledger`).
  - The contract's *content* (schemas/endpoints/task pairing) lives in `docs/design/mqtt_integration.md` §14 + the
    `voice-bridge-catalog-contract` memory — **referenced, not duplicated here** (avoid drift). Pairs with
    `../wb-mqtt-bridge/CLAUDE.md`'s same-named invariant (the other direction).
- **`read-at-start-record-at-completion`** — AFFIRMATIVE & NON-NEGOTIABLE until release.
  - **At task START:** read **not only the ledger item but also its related review doc(s)** (per the ledger's index)
    — the ledger item is a spine entry; the review doc holds the evidence, file:line refs, detail.
  - **At task COMPLETION:** flip status in the ledger and add a dated entry to `RELEASE_JOURNAL.md` — **in the same
    change.** Do **not** re-edit a review doc's status (frozen evidence with a one-time `→ tracked as <ID>` pointer);
    the only reason to edit a review doc is if a *finding itself* is wrong/obsolete (annotate, don't flip status).
- **`single-task-ledger`** — The ledger is the only source of scope + status. Every release task has **exactly one ID**;
  review/design docs may *surface findings* but **a finding is not scope until it has a ledger ID**. Each task is tagged
  **`[release]`** or **`[deferred]`**; release is blocked until every `[release]` task is `[x]`. Run
  `scripts/check_scope.py` at each gate (flags orphan findings, dead evidence links, contradictory status markers).
  - **The ledger spans two files:** active `docs/RELEASE_PLAN.md` (open + paused/partial) + frozen
    `docs/RELEASE_PLAN_DONE.md` (completed `[x]`, by workstream). One ledger — every ID in exactly one file; on
    completion a task **moves** active → done (same change as the journal entry).
- **`every-task-in-the-ledger`** — No work happens without a ledger entry, **regardless of where the task came from**
  — a chat request, a GitHub issue, a code-review finding, a TODO spotted mid-task. The first action on any new piece
  of work is to file it: give it an ID and a `[release]`/`[deferred]` tag *before* starting. External sources merely
  *surface* work; it is not scope until it lives in the ledger (the intake door that `single-task-ledger` guards).
  - **Carve-out — routine dependency housekeeping:** a lockfile-only dependency bump that does **not** change
    `pyproject.toml` / `config-ui/package.json` intent (e.g. `npm audit fix`, a `uv lock` refresh, a Dependabot lock
    refresh) does **not** need its own ledger ID. It still gets a `one-active-journal` line on completion, and any bump
    that *is* a deliberate version decision (a new dep, a major upgrade, a pin change) is a normal task and **does**
    need an ID.
- **`design-then-implement`** — A task that **adds a feature or redesigns** an existing one is a **design task**: its
  deliverable is a **design document** — a new file under `docs/design/`, or an edit to the existing design for a
  redesign — referenced from the ledger entry and listed in the ledger's review/design index. Completing it means *the
  design is done and recorded*, **not** that code shipped. On completion, **file the implementation follow-up task(s)**
  in the ledger (they then flow through normal task discipline). Keep design and implementation as separate tasks — so
  the design is reviewable before any code is built.
- **`review-then-remediate`** — A **review** — requested in chat (name what to review) or run via the `/code-review`
  skill — is itself a **review task** in the ledger. Its deliverable is a **review document** (frozen evidence under
  `docs/review/`, carrying the one-time `→ tracked as <ID>` pointers per `read-at-start-record-at-completion`). On
  completion, **file new ledger tasks** for the findings worth acting on — a finding isn't scope until it has an ID
  (`single-task-ledger`). Mirrors `design-then-implement`: the review produces the document; the fixes are fresh tasks.
- **`one-active-journal`** — `docs/RELEASE_JOURNAL.md` is the only **active** chronological log (the single place new
  entries are appended). No competing live logs anywhere else. Entries reference task IDs but never assert status.
  - **Archival is allowed:** older entries are **frozen** into dated files under `docs/archive/journal/`
    (append-only, never re-edited, greppable, **outside the default-read path**). Only the active journal is read at
    task start; an archive is consulted when a `task-start-reconciliation` grep points to it. Leave a pointer at the
    top of the active journal to the newest archive.
  - **When to rotate (checked at each gate, alongside `scripts/check_scope.py`):** if the active journal exceeds
    **~1500 lines / ~40k tokens** (high-water), freeze the **oldest whole dated sections** (never split a day) into
    the newest `docs/archive/journal/` file until it is back under **~1000 lines / ~25k tokens** (low-water), then
    update the pointer. Same trigger discipline as task-moves, but periodic rather than per-event.
- **`task-start-reconciliation`** — no stale, redundant, or mis-scoped work. Before starting **any** task, reconcile it
  against current reality — not just the ledger/review doc (`read-at-start-record-at-completion`), but also
  `RELEASE_JOURNAL.md` (what actually landed) **and the code itself** (does the problem still exist where the task
  assumes?). Classify: (a) **valid** → proceed; (b) **partially addressed** → narrow; (c) **already addressed** →
  close obsolete; (d) **scope drifted** → redefine. **For (b)/(c)/(d): STOP and consult the user** before doing the
  work or editing the ledger. _Pairs with `read-at-start-record-at-completion`: that one loads the context; this one
  verifies the task is still the right task._
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
- **`user-facing-docs-are-done`** — The user-facing docs — `docs/architecture/*`, `docs/guides/*`,
  `docs/QUICKSTART.md`, and top-level `README*` — are narrative explanations for a reader who does **not** know the
  codebase or the release plan. **A non-root `README*`** (e.g. `eval/README.md`) is also in scope, **but only when the
  task touches code in that README's directory/subsystem** (the local README documents the local code; don't audit
  every README on every task). For **every** task, before completion check whether the change alters behavior any
  in-scope doc describes; if so, update them **in the same change**, matching the document's voice — **no internal tracking language** (task IDs, ledger/journal refs, gate
  counts, file:line, raw internal symbols/config keys) unless the doc already teaches them as user-facing names.
  **Diagrams are docs too:** update the source (`docs/images/*.dot`) and regenerate the image in the existing visual
  style. _Pairs with `config-ui-stays-functional` (the user-facing **app**; this is the user-facing **docs**)._

- **`problem-report-inbox`** — problem reports (ARCH-30) land as tickets in the private
  `droman42/wb-user-reports` repo; a cloud Claude triages each and leaves it needing the owner (a fix PR open on
  this repo, or a `needs-owner` escalation). **At the start of a new or resumed session, do a quick, non-blocking
  check** — `gh issue list --repo droman42/wb-user-reports --label needs-owner --label lens:voice --state open`
  plus the `fix-pr-open` variant — and if anything is waiting, **mention the count in one line** and offer
  `/inbox`. Never auto-enter the review; the owner decides when. (Skill: `.claude/skills/inbox/`. A `gh` failure —
  no network, no auth — is silently skipped; this check must never block or noise up a normal session.)

**Legend — historical numbers → names.** Frozen journal/ledger archives and review docs reference these invariants by
their old number (numbering retired 2026-06-27). Resolve here:
`#1`→`work-on-main` · `#2`→`config-master-canonical` · `#3`→`hexagonal-architecture` · `#4`→`config-ui-stays-functional`
· `#5`→`read-at-start-record-at-completion` · `#6`→`single-task-ledger` · `#7`→`one-active-journal`
· `#8`→`task-start-reconciliation` · `#9`→`no-type-checking` · `#10`→`user-facing-docs-are-done`.

## Testing & evaluation

Declarative tests (CLI contracts, streaming-ASR system tests, Russian UX judging) live in
**[`eval/`](eval/README.md) — read that README before touching anything test-related.**

Key things it establishes (don't rediscover the hard way):
- All test *execution logic* (providers, scorers, judge) lives in the sibling repo
  **`../eval-commons`** — this repo carries only YAML + a thin `eval/Makefile`. Change behavior
  there, not here.
- Run tests via `make` from `eval/` (it wires the `uv` venv + global `promptfoo`), e.g.
  `make cli` (no prerequisites), `make ws TARGET=local|wb7`, `make ux`.
- Tests parameterize over two external axes — **TARGET** (local vs the WB7 controller) and
  **CONFIG** (which Irene config the SUT runs) — via `eval/profiles/*.env`. Never bake an
  endpoint or config into a test case.
- promptfoo env refs are `{{env.VAR}}`, not `${VAR}`.

Status: `make cli` passes; the WS/UX suites are pending recorded audio fixtures and Russian
judge calibration (see `eval/README.md` → Notes/TODO).
