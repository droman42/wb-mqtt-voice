# Build & Release Process — bridge-aligned redesign (BUILD-8)

**Status:** design AGREED 2026-07-02 (interactive session; four decisions user-confirmed). Implementation →
**BUILD-9** (CI/publish workflow) + **BUILD-10** (`ops/` deploy story).
**Requirement source:** the BUILD-8 ledger entry (add English image builds; "additional asks" gathered at task
start) + the user's directive to **organize this repo's build the way `../locveil-bridge` organizes its** +
one hard requirement: **model files must never be baked into images** (§6 audit + guards).
**Evidence base:** two comparative maps (this repo's build machinery; the bridge's) — summarized in §1;
`docs/guides/build-docker.md` / `build-system.md` remain the operator/concept guides and are updated by the
implementation tasks.

---

## 1. What we take from the bridge (and what we already had)

The bridge's build discipline, distilled: **one path-filtered workflow** where every push pays only for the
checks it earns; **image publishing is a manual, gated act** (`workflow_dispatch`, `needs:` green checks in the
same graph); **externalized Python gates** (`droman42/py-dev-gates@v0.1.1`); the **ledger guard runs in CI**;
and **deploy = pull, not build**, driven by a tiny `ops/` directory (compose + `update.sh` + systemd unit),
with config-as-code arriving by `git pull` and mutable state isolated.

Already aligned here (kept as-is): GHCR + `GITHUB_TOKEN`-only auth; the `latest` / `sha-<short>` /
`vYYYYMMDD-<sha>` tag triple; the 3-stage lean-venv Dockerfiles; PiWheels + flash-awareness. Already **ahead**
of the bridge (kept, explicitly not "aligned away"): the analyzer-driven stage-1 that computes each profile's
minimal dependency set, and per-target buildx GHA caching (`scope=<target>`; the bridge builds `no-cache`).

## 2. Decisions

### D-1 — One workflow, gated graph (replaces three disconnected ones)
`backend-health.yml`, `frontend-health.yml` and `build-images.yml` merge into a single **`ci.yml`**:
- **`changes`** job (dorny/paths-filter): `backend` (`irene/**, configs/**, pyproject.toml, uv.lock, docker/**`),
  `ui` (`config-ui/**`), `ledger` (`docs/**` + the vendored `scripts/scope_guard.py` + `.scope-guard.toml`),
  each also matching the workflow file.
- **`ledger-guard`** — `scripts/scope_guard.py --config .scope-guard.toml` runs in CI (the commons scope-guard
  vendored at a pinned `scope-vX` tag; BUILD-30 superseded the local `check_scope.py` this design originally named).
- **`backend-health`** — the shared trio via **`droman42/py-dev-gates@v0.1.1`** (import-linter,
  check-no-type-checking, pyright) + the voice-specific gates kept verbatim (build-analyzer
  `--validate-all-profiles`, config validator `--ci-mode`, dependency validator, the ARCH-24 armv7 arch gate)
  + `pytest`. Runs when `backend` changed or a dispatch requests images.
- **`frontend-health`** — unchanged content (`npm ci / check / build / test`), same file.
- **Publish jobs** (D-3) — `workflow_dispatch` only, **`needs:` their green health jobs**. Today's standalone
  `build-images.yml` can publish from a red tree; that hole closes. `issue-triage.yml` stays separate (not build).

### D-2 — The matrix and naming: RU unsuffixed, EN suffixed
Dispatch inputs: **`targets`** (armv7 / aarch64 / standalone; default all) × **`languages`** (ru / en; default
both) + **`build_ui`** (bool, D-4) → a build matrix (≤6 backend images/run). Naming (user decision):
- **RU keeps today's names** — `locveil-voice-armv7|aarch64|standalone` (existing deployments' `:latest`
  keeps meaning what it meant).
- **EN adds a name suffix** — `locveil-voice-armv7-en` etc.; `CONFIG_PROFILE` maps to the existing `*-en`
  profiles. Six GHCR packages; each new one needs the known one-time public-visibility flip (documented).
Tag triple unchanged per package. Rejected: language-in-tag (ambiguous `latest`), rename-all-to-`-ru` (breaks
every existing reference for symmetry's sake).

### D-3 — Publishing stays manual, one dispatch for the whole matrix
Bridge parity (user-confirmed): push/PR runs only the fast gates; images build **only on dispatch**, defaulting
to the full matrix, each job `needs:` green health. Per-scope buildx cache retained (cache scope =
`<target>-<language>`). The assets artifact step is **dropped from the workflow** — assets travel by `git pull`
(D-5). Rejected: auto-publish on push (≤6 QEMU builds per push is hostile to a push-to-main solo flow);
git-tag releases (a ceremony neither repo has; **version→tag coupling recorded as deferred** — both repos
currently hand-bump versions that are never stamped into images, and fixing that is a joint decision for later).

### D-4 — config-ui ships as a bridge-style nginx image — but not to the controller (yet)
A seventh package **`locveil-voice-ui`**: `nginx:alpine` serving the built `dist/`, **one multi-arch
manifest** (amd64+arm64+armv7 — static files are arch-independent, so this adds no matrix burden). Built on
the `build_ui` dispatch toggle, `needs: frontend-health`.
_Amended at implementation (BUILD-9): **no nginx proxy** — the bridge's `/api` proxy doesn't map onto Irene
(whose API has no path prefix), and Irene already serves permissive CORS. Instead, the bridge's
**runtime-config pattern**: the entrypoint writes `/runtime-config.js` from an `API_BASE_URL` env var;
empty/absent defaults to `http://<page-hostname>:6000` in the app, which covers both dev and the
UI-next-to-backend deployment with zero configuration._ **User scope note: it is NOT deployed on the controller
for now** — the `ops/` compose (D-5) ships with the UI service **commented out / profile-gated**, ready to
enable when the donation editor graduates from developer tool to operator tool. This closes the
"CI builds it, then it goes nowhere" drift with a real ship path that costs nothing at deploy time.

### D-5 — `ops/` + assets by git-pull (deploy = pull, not build)
New **`ops/`** directory, bridge pattern adapted:
- **`docker-compose.yml`** — the Irene service (`:6000`, `restart unless-stopped`, mem limits sized for the
  target, json-file log caps) with `IRENE_ASSETS_ROOT` volume-mounted from the controller's data partition;
  the UI service present but disabled by default (D-4). Image tag pinned/`latest` per the bridge's rollback
  convention (pin `vYYYYMMDD-<sha>` to roll back).
- **`update.sh`** (~15 lines) — **sync assets, then pull**: rsync the repo checkout's `assets/` content
  (donations, templates, prompts, localization — the git-owned subdirectories, enumerated explicitly) into the
  writable assets root, then `docker compose pull && up -d --remove-orphans && docker image prune -f`.
  **Never touches** the runtime-owned subtrees (`models/`, `cache/`, `state/`, `traces/`, `credentials/`) —
  the same config-as-code / state-as-data split the bridge enforces with `.state/`. This **replaces the
  per-build GHA assets artifact** and its manual download (today's weakest link).
- **`locveil-voice.service`** — systemd oneshot (`docker compose up -d` / `down`), after docker+network.
- **`ops/INSTALL.md`** — WB install/update/rollback walkthrough in the bridge's `INSTALL.md` style.
Deploy loop on the controller = `git pull` (assets + ops) → `./ops/update.sh` (images). The voice repo is
checked out on the controller exactly as the bridge repo already is.

### D-6 — Models are NOT baked — audited, and now guarded (user hard requirement)
**Audit result (2026-07-02, by construction):** the runtime stages copy only `irene/` + the builder venv;
`assets/` enters **only the analyzer stage** (dep computation — never shipped); `/app/assets` is created
empty; all ASR/TTS/wake ML models download at runtime via the AssetManager. **One deliberate exception:**
the profile's **spaCy NLU model wheel** (e.g. `ru_core_news_md`, ~15–45 MB) is a pip package inside the venv
— trimmed to exactly one per profile language by `derive_build_reqs._spacy_keep`; it stays (offline-first NLU;
it is a Python dependency, not an asset). The large images the suspicion came from are **dependency** weight —
chiefly **torch** in the standalone image (`advanced-asr`) — already minimized per-profile by the analyzer.
**Guards added by BUILD-9:** (1) a publish-workflow step that runs the built image and **fails if
`/app/assets` is non-empty**; (2) a **per-image size budget** check (thresholds measured at implementation
from current sizes + headroom) with the size printed to the job summary — so a future "oops, baked the
models" regression is caught at build, not on the WB7's flash.

### D-7 — Adopt `py-dev-gates`, keep the voice-specific gate suite
The shared composite action replaces the hand-inlined trio in `backend-health` (one less thing to drift
between siblings); the build-analyzer/config/dependency/arch gates and pytest remain repo-local steps. The
commented-out black/isort gate stays deferred (unchanged scope).

## 3. Implementation plan

- **BUILD-9 — CI/publish workflow**: `ci.yml` per D-1/D-2/D-3/D-6/D-7 (changes-gating, ledger-guard,
  py-dev-gates, dispatch matrix with naming map, empty-assets + size-budget guards, drop the assets artifact);
  `config-ui/` nginx image + Dockerfile per D-4; delete the three superseded workflows; update
  `docs/guides/build-docker.md` (new dispatch UX, 7-package table, EN images) — `user-facing-docs-are-done`.
- **BUILD-10 — `ops/` deploy story**: the D-5 directory (compose, update.sh with the explicit asset-subdir
  sync list, systemd unit, INSTALL.md); `build-docker.md` deployment section rewritten around it.
- Sequencing: BUILD-9 first (BUILD-10's compose references the new image names). Both verifiable without
  hardware except the final on-WB7 `update.sh` run (folds into the existing ARCH-25 bring-up).

## 4. Rejected / deferred

Auto-publish on push · git-tag releases + version-stamped tags (deferred, joint decision with the bridge —
both repos hand-bump versions today) · language-in-tag naming · renaming RU packages to `-ru` ·
config-ui on the controller (D-4 leaves it one compose-uncomment away) · baking config-ui into backend
images · replacing the analyzer stage with bridge-style install-everything (ours is better) · removing
per-target buildx cache (ours is better) · UI e2e tests in CI (the bridge defers the same gap).

## 5. Stale-evidence note

`docs/review/docker_build_review.md` (2026-06-08) describes a pre-BUG-14 reality — Alpine armv7 base and two
"build-blocking" defects, all since resolved (bookworm migration, BUG-14 proven on WB7). An obsolescence
annotation is added to that doc alongside this design (finding-correction edit, permitted for obsolete
findings); its still-live item is BUILD-5 (analyzer extras-vs-specs cleanup), unaffected by this design.
