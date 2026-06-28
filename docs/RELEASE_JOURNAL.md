# Irene — Release Journal

The single **active** chronological log for the release effort ("what happened, when, and why"). Append-only;
newest entries near the top of each dated section.

- **This file holds NO task status and NO scope.** The authoritative task ledger (scope + status) is
  [`RELEASE_PLAN.md`](./RELEASE_PLAN.md); findings/rationale live in `docs/review/*` + `docs/design/*`.
- Entries reference task IDs (e.g. `QUAL-27`) but never assert their status — check the ledger for that.
- **Older entries are frozen in archives** (`one-active-journal`), newest first: [`docs/archive/journal/pre-2026-06-15.md`](archive/journal/pre-2026-06-15.md)
  (2026-05-31 … 2026-06-14). This file keeps **2026-06-15 onward**; grep an archive when reconciliation needs older history.

---

## Action journal

### 2026-06-28
- **BUG-8 DONE — config-ui DonationsPage composite-key + stale-state defects (the first remediation from the config-ui
  review).** Everything keyed by `${handler}:${language}` now: the 404-fallback no longer stores under the bare handler
  (which caused an **infinite reload loop** + stuck spinner), the validation *catch* stores the error under the key the
  tab indicator reads, the `globalParamNames` memo gained its missing `selectedLanguage` dep (and shed a copy-pasted
  `eslint-disable`), and CrossLanguageValidation renders behind a guarded `selectedHandlerInfo` instead of a non-null
  assertion that crashed if the handler left the list mid-reload. Gate: config-ui `npm run check` + `build` green.
  Remaining review correctness findings: BUG-9 (stale-request overwrite), BUG-10 (unreachable blocking dialog).
- **config-ui review (`config_ui_review.md`) — quality/dup/dead/correctness pass.** 8 finder angles → 1-vote verify.
  Found **5 confirmed + 2 plausible correctness bugs** (404 reload loop, stale-request overwrite, unreachable blocking
  dialog, wrong-key validation error, stale memo), **type-contract drift** in `types/api.ts` (CoreConfig/NLUConfig/
  VADConfig behind the backend — defeats the type-check half of `config-ui-stays-functional` while the editor keeps
  working off the backend schema), **6 duplications** (~500+ lines: apiClient CRUD quintet ×4, Templates/Prompts page
  clones, list/key/card editor primitives), **dead exports** (ESLint only flags unused *locals*), and efficiency +
  hardcoded-list/altitude smells. Baseline `npm run check`/`build` pass — the defects are exactly what those gates
  don't catch. Remediation filed: **BUG-8/9/10** (correctness) + **UI-11** (drift) / **UI-12** (dup) / **UI-13** (dead)
  / **UI-14** (efficiency+altitude), all `[deferred]`. No fixes applied (review → tasks, per `review-then-remediate`).
- **TEST-14 DONE — trace↔WAV unification (record once, test twice).** A golden audio trace already carries its captured
  audio (the bytes `--listen` plays), so a new `irene-replay-trace --extract-wav <file.wav>` decodes it to a standard
  WAV — one golden trace now serves both the offline replay tier AND the live WS suite, no re-recording with a mic.
  Pure trace→WAV transform (standalone CLI mode, no core/replay); writes at the captured rate/channels (Irene's 16 kHz
  mono PCM16 → directly usable as a fixture). Documented in `eval/README`. Gates: suite 1109 passed (+3 tests),
  pyright 0, import-linter 9/9. **Closes the trace-driven system-testing series** (TEST-11→12→13→14); no trace-playback
  TEST- tasks remain open.
- **TEST-13 DONE — failure-trace capture for the live WS suite (S2).** Two pieces: (D-6) when tracing is on, the
  `WorkflowManager` entry points stamp the trace `request_id` onto `result.metadata` — the `/ws/audio` response already
  spreads `result.metadata`, so each case correlates exactly to its saved `<request_id>.json` (no handler change,
  additive, config-ui N/A); (D-13) a new project-agnostic `eval_commons.failures` helper (eval-commons `e740c80`) reads
  the promptfoo results JSON and keeps only the FAILING cases' traces under `traces/failures/`, pruning the rest —
  reusable by wb-mqtt-bridge unchanged. Wired into `eval/Makefile`'s `ws` target behind `TRACE=1` and documented in
  `eval/README` (incl. the offline `--record-out`-on-mismatch tier, D-7, which already existed). A failed case is now
  replayable from the *actual* failing run (`irene-replay-trace --listen --step`). Gates: suite 1106 passed (+ 2
  workflow_manager tests; eval-commons +6), pyright 0, import-linter 9/9. Trace-playback wiring now leaves only
  **TEST-14** (trace↔WAV unification) open.
- **BUG-7 DONE — ru oblique-case numerals normalize to digits.** ovos (ru) reads only nominative numerals, so «одну
  секунду»/«двух минут»/«тридцати пяти» stayed as words and «тридцать одну» even broke to "30 одну". Fix at the
  normalizer altitude (`text_processing.py`): remap the oblique cardinals ovos misses → nominative before ovos (digit
  conversion incl. compounds then fires). Mapped only the forms ovos actually misses; excluded words that collide with
  non-numeric meanings so plain text is never mangled («о семью детях» stays). Verified «одну секунду» → "1 сек",
  «тридцать одну секунду» → "31 сек". Suite 1104 passed, pyright 0, import-linter 9/9. Normalizer-only. Surfaced as the
  BUG-6 bonus finding (had been parked on QUAL-35; resolved here instead).
- **BUG-6 DONE — the "unit story": timer-unit fix + consolidate 3 parsers to one + remove the dead DURATION stub.**
  "set a timer for one second" → "1 min" because the en `unit` param lacked `choice_surfaces` (ru had them) so the weak
  CHOICE extraction defaulted to "minutes", and the correct text fallback was bypassed once `duration` was extracted.
  Right altitude: one shared bilingual parser `irene/utils/units.py` (`TIME_UNITS` + `parse_duration`), made
  authoritative in the timer. Consolidated the 3 unconnected time-unit parsers (timer, `TemporalEntityResolver`,
  `QuantityEntityResolver`) to it. Removed `ParameterType.DURATION` (declared, never coerced, unused) across enum +
  hybrid matcher + contract JSON schema + config-ui (incl. regenerated gen types). Verified "one second" → "1 sec".
  Gates: suite 1103 passed, pyright 0, import-linter 9/9, 12/12 profiles, config-ui green. The general units layer
  (percent/°C) is filed onto **QUAL-35** to be designed *with* smart-home (units come from the bridge device catalog);
  ru «одну/одна» normalize gap noted there. Scoped time-only for now, per user.
- **BUG-4 DONE — per-language defaults + fire-and-forget completion language (all 3 sub-issues, right altitude).**
  Three related defects, one theme (per-language state not threaded to where messages render): (1) donation
  `default_value` flattened to ru → now assembled per-language (`ParameterSpec.default_value_by_language`), threaded via
  `Intent.language` (set in the orchestrator), resolved strictly by request language in `get_param`; (2) **fire-and-
  forget completion language** (the user's catch — a timer is F&F): capture the request language + the rendered
  completion message into the `ActionRecord`, replay at completion; the notification service stopped hardcoding English.
  Verified: en timer → "Timer set for 10 min. Message: Timer completed!" + the deferred completion fires "Timer
  completed!"; ru unchanged. (3) datetime en localization filled (`days_ordinal`/`hours`/`periods`/`special_hours`).
  Suite 1086 passed, pyright 0, import-linter 9/9, 12/12 profiles, config-ui green. The donation en alias/choice
  *enrichment* sweep (non-functional, respect the technical-identifier rule) split out as **BUG-5**.
- **BUG-3 DONE — English replies, at the right altitude: a TTS normalizer was corrupting NLU input.** Deeper analysis
  (per request, "not only timer related") found the en→ru reply was a *symptom of input corruption*: the `prepare`
  normalizer transliterates Latin→Cyrillic ("set a timer"→«сэт е таймё») and ran at the `asr_output` (pre-NLU) stage,
  so English never reached NLU as English → script detection saw Cyrillic → `ru` → every handler replied Russian.
  `prepare` is TTS-only (also spells symbols out), so the fix is to run it at `tts_input` only — schema default +
  `config-master` (the only config pinning it; the rest inherit the default; all 12 profiles validate). Plus: the
  detector's no-signal case now falls back to script (non-Cyrillic ⇒ English) instead of None→default; and the timer's
  own literals are localized (`_format_duration` units, message fallback). English now understood + replied correctly
  across handlers. Suite 1086 passed (2 old-behavior tests updated), pyright 0, import-linter 9/9. Residual noted: the
  timer donation's `message` default_value is Russian (a separate donation-localization concern).
- **BUG-1 DONE — spelled-out numbers now reach parameter extraction (general fix, ru + en).** Research (not just ru)
  found the codebase only ever did DIGITS→WORDS (synthesis) and every extractor matched `\d+` — so English ("ten
  minutes") was broken identically. Added `normalize_numbers_to_digits` (ovos `numbers_to_digits`, ru+en, idempotent,
  safe-degrade) and — after a good catch that a provider-local fix misses spaCy/LLM — applied it **once at the cascade
  entry** (`ContextAwareNLUProcessor.process_with_context`), so every recognizer + the spaCy donation patterns + (via
  normalized `raw_text`) handler text-fallbacks see digits. Also gave the timer's `_parse_timer_from_text` English
  units (it was ru-only). Verified ru/en spelled + compound + digit regression all set the timer; suite 1086 passed,
  pyright 0, import-linter 9/9, 10 new tests. Unblocks a natural-speech timer golden + the WS UX timer case.
- **TEST-12 DONE — config overrides (`--set`) + offline golden-trace replay surface; BUG-2 fixed, BUG-1 filed.**
  Trying to record a golden trace exposed that you couldn't override config settings without hand-editing files.
  Fixed: **`--set DOTTED.KEY=VALUE`** on the base runner (`config/manager.py apply_dotted_overrides`, applied
  pre-validation so Pydantic coerces+validates; strict — an explicit `--set` never silently falls back; 8 tests).
  Built the **golden-trace surface**: `eval/trace.promptfooconfig.yaml` drives `irene-replay-trace` through the
  existing `cli_provider` (assert `exit_code === 0`), `make replay`/`replay-judge`, a committed seed golden
  (`timer_set_10min.json`) that replays green under the WB7 config, `eval/traces/README.md`, the 4th surface in
  `howto-new-test.md`. Also made `diff_output` normalize volatile timestamps (a timer's `started_at`) so deterministic
  handlers stay green goldens. Two bugs surfaced and a new **`BUG` workstream** filed:
  - **BUG-2 (fixed)** — stale `TTS requires Audio` check in `voice_assistant.py` (a drifted duplicate of the canonical
    `CoreConfig` validator, missing the `audio_playback_enabled` condition) rejected the valid WB7 satellite config in
    any runner that didn't force audio on. It was masked by `webapi_runner` hard-setting `components.audio`. Removed the
    duplicate; suite 1074 passed; the WB7 golden replays green with no workaround.
  - **BUG-1 (open)** — spelled-out Russian numerals don't set a timer («десять минут» → no timer; «10 минут» works);
    the golden uses the digit form pending the fix.
  (Reverted the reactive `--set` I'd added to the replay tool — BUG-2's fix made the local-replay workaround unneeded.)
- **TEST-11 DONE (design) — trace-driven system testing → `docs/design/trace_system_testing.md`.** Uses the shipped
  trace record/replay (ARCH-19) two ways: an **offline deterministic regression surface** (committed golden traces
  replayed via `irene-replay-trace --local` through the existing `cli_provider`, asserting `exit_code === 0`; tiered
  `trace-system` vs DeepSeek-judged `trace-ux`) and **failure-trace capture** (always-trace + keep-on-failure for the
  live WS suite via a small `request_id`-in-metadata enabler; `--record-out`-on-mismatch offline) so a failed case is
  replayable (`--listen`/`--step`). No new `eval-commons` code for the core surface. Design done ≠ shipped → filed
  **TEST-12** (offline surface), **TEST-13** (failure-tracing + SUT enabler), **TEST-14** (trace↔WAV, phase 2).
  **Resolved the design's three open questions** (now D-12/13/14; design AGREED): D-12 — `trace-system` is not
  release-gating yet but promotes on a trigger (covers the core paths + 2 consecutive green CI runs); D-13 — the
  keep-on-failure post-step is a generic `eval-commons` helper (reusable by the bridge), not a per-project step; D-14 —
  seed a small deterministic golden set now and grow it from real failures (failure-tracing feeds the golden set).
- **TEST-10 DONE — WS audio fixtures are now versioned.** A blanket `*.wav` ignore had accidentally swept the eval
  fixtures in, making the WS suite un-runnable in CI (no mic) and non-reproducible (re-record → different WER). Carved
  `!eval/fixtures/*.wav` out of the ignore; other `*.wav` stay ignored. Fixtures are test inputs, not stray audio.
  `fixtures/README.md` updated. The deeper "golden traces as reviewable regression inputs" direction is in the
  trace-system-testing design.
- **DOC-9 DONE — user-facing eval guide.** Added `docs/guides/howto-new-test.md` (+ decision diagram
  `howto-test.dot/png`) in the established `howto-*` voice: pick a surface (CLI contract / WS system / WS UX-judged),
  author a case in each, record the fixture (`make record`), keep cases endpoint-agnostic (TARGET/CONFIG). Wired into
  the howto index (`CONTRIBUTING.md` "Add a test" + the top-level `README` pointer, beside add-an-intent/model/language)
  and cross-linked from `eval/README.md` as the walkthrough to its reference. Closes the "how do I add a test?" gap
  surfaced once the recorder made the WS suite actually authorable.
- **TEST-9 DONE — voice-fixture recorder wired into `eval/` (W6).** The recorder itself (design + W1–W5) was built and
  pushed in the sibling **eval-commons** repo (`eval-fixture-record`: mic capture → 16 kHz/mono/PCM16, worklist derived
  from the promptfoo YAML, interactive keep/redo); it lives there because eval-commons is the shared lower layer and
  must not import a consumer's audio stack (cycle). This repo's W6 wiring: `make record`/`record-list`/`record-devices`/
  `setup-record`; `profiles/recording.env.example` (real file git-ignored); `reference` added to the `light_unreachable`
  judge case so the recorder has a script (§5 decision); `fixtures/README.md` + `eval/README.md` repointed at
  `make record`. Verified end-to-end (`record-list` derives both fixtures, console script resolves, `make cli` 5/5).
  Unblocks the WS suite's fixture gap — recording the WAVs is now a clean manual step. eval-commons has no ledger; its
  side is tracked in its design doc §13 + commit `965153c`.
- **API execution-result contract review → QUAL-54 (done) + QUAL-55 (filed).** Surfaced while wiring the `eval/` WS
  suite: the `ws_audio_provider` reads `metadata.intent_name`, which `/ws/audio` never emits. Reviewed the execution
  surfaces and found a **family** of inconsistencies (no shared result serializer) — captured in
  `docs/review/api_result_contract_review.md` (F1 reply field `response` vs `text`; F2 3-way intent split; F3 one
  response model, two metadata payloads; F4 `confidence` placement; F5 internal `intent_name` read always `None`).
  **QUAL-54 (targeted, done):** `/ws/audio` now surfaces `intent_name` (remapped from `original_intent`) at both send
  sites + `workflow_manager` pipeline events read `original_intent` (fixing the live `None`). `test_pipeline_events`'s
  fake used the wrong key (`intent_name`), masking the bug — corrected to `original_intent`, now a faithful regression.
  Full suite 1066 passed, pyright 0, import-linter 9/9. **QUAL-55 (open):** one canonical serializer across all five
  surfaces (retires F1/F3/F4 + rest of F2; `config-ui` co-change). Unblocks the eval WS intent case.
- **UI-10 DONE — config-ui major dependency upgrades; all 8 Dependabot alerts cleared.** The 6 the housekeeping pass
  couldn't touch needed breaking majors outside the declared ranges, so they were a deliberate version decision (filed
  as UI-10, done same session): `vite ^5`→`^8.1.0` (+ `@vitejs/plugin-react`→`^6`; vite 8 = rolldown bundler) cleared
  the 3 vite advisories + esbuild; `react-syntax-highlighter ^15`→`^16` cleared prismjs (the only runtime one — `Prism`
  API unchanged); `@typescript-eslint ^6`→`^8` (eslint kept at 8.57 — stayed on eslintrc, no flat-config migration)
  cleared the minimatch ReDoS. ts-eslint 8's stricter type-checked config surfaced 6 lint errors (5 auto-fixed, 1
  optional-catch). `npm run check` + `build` + vitest 40/40 green; `npm audit` → 0 vulnerabilities. Upgraded
  incrementally (gate after each major) so breakage stayed isolated.
- **config-ui dependency housekeeping — lockfile-only, no ledger ID** (per the `every-task-in-the-ledger`
  carve-out). `npm audit fix` lifted `@babel/core`→7.29.7 and `js-yaml`→4.2.0 in `config-ui/package-lock.json`;
  `package.json` intent unchanged, `npm run check && npm run build` green. Cleared 2 of 8 Dependabot alerts. The
  other 6 need **breaking major upgrades outside the declared ranges** — `vite ^5`→6/8 (3 vite alerts + esbuild),
  `react-syntax-highlighter ^15`→16 (prismjs), `@typescript-eslint ^6`→8 (minimatch) — i.e. deliberate version
  decisions, not housekeeping; to be carried as a ledger task, not auto-applied.
- **Work-process redesign: ledger split + journal rotation (size control).** The ledger and journal had grown to
  ~71k / ~88k tokens (~159k combined; 106 of 127 ledger tasks done, 264 journal entries), past the point where the
  harness keeps them resident — every task that obeys `read-at-start-record-at-completion`/`task-start-reconciliation` was paying to load mostly-closed history.
  Completed work is reference-by-ID, not working-set, so it can be archived without losing the trail. Changes:
  - **`one-active-journal` amended** — "one journal" → "one *active* journal + frozen dated archives." The old wording ("no
    dated journals anywhere else") forbade the fix, though its real target is *drift* (two competing **live** logs).
    Reworded to permit append-only, frozen, greppable archives under `docs/archive/journal/` outside the default-read
    path, with a discoverability pointer at the top of the active journal.
  - **`single-task-ledger` extended** — the ledger now spans two files: active `RELEASE_PLAN.md` (open + paused/partial) +
    frozen `RELEASE_PLAN_DONE.md` (completed `[x]`, by workstream). One ledger, every ID in exactly one file; on
    completion a task **moves** active → done. `scripts/check_scope.py` now reads both for declarations (else
    references to completed tasks read as orphans) — verified 0 orphans / 0 dead links after the split.
  - **Split executed:** 106 completed tasks moved to `RELEASE_PLAN_DONE.md`; active ledger 71k → ~10k tokens.
  - **First journal rotation:** sections dated 2026-05-31 … 2026-06-14 frozen into
    `docs/archive/journal/pre-2026-06-15.md`; active journal keeps 2026-06-15 onward, 88k → ~23k tokens.
  - **Invariants relocated to `CLAUDE.md` + numbering retired.** All 10 invariants moved to `CLAUDE.md` →
    "Development process — invariants" (single source of truth, always in context = always enforced); the ledger's
    Invariants section is now just a pointer. To kill drift permanently, invariants are referenced by **stable name**
    (slug: `work-on-main`, `single-task-ledger`, `task-start-reconciliation`, …), **not number** — names survive
    add/remove/reorder so references never break. The ~134 `#N` refs in the frozen archives + review docs are left
    intact and resolve via a one-time number→name **legend** in `CLAUDE.md`; the 27 live refs in the active
    ledger/journal were converted to slugs. Net default-read working set: ~159k → ~33k tokens.
  - **Three development-process invariants added** (numbering retired, so no renumbering): `every-task-in-the-ledger`
    (file every task before working it, regardless of source — chat / GitHub issue / code-review finding),
    `design-then-implement` (a feature/redesign task delivers a **design doc**; implementation is filed as follow-up
    tasks on completion), `review-then-remediate` (a review — chat-requested or via `/code-review` — is a task that
    delivers a **review doc**; findings are filed as fresh tasks). Formalizes the intake + design/review pipelines the
    repo already followed informally.
  - **Journal rotation trigger defined** in `one-active-journal` (was permissive-but-undated): at each gate, if the
    active journal exceeds ~1500 lines / ~40k tokens, freeze the oldest whole dated sections into the newest archive
    until back under ~1000 lines / ~25k tokens. Closes the only "when" gap — task-moves were already per-completion.
  - **`user-facing-docs-are-done` scope widened** to add `docs/QUICKSTART.md` (always) + non-root `README*` (e.g.
    `eval/README.md`) — the latter **only when the task touches that README's directory/subsystem** (locality gate, so
    it isn't a "re-audit every README" burden). Closes the scope gaps surfaced when reviewing the invariant.
  - **`every-task-in-the-ledger` carve-out for routine dependency housekeeping** (surfaced while porting the
    invariants to the sister project `wb-mqtt-bridge`): a lockfile-only bump that doesn't change `pyproject.toml` /
    `config-ui/package.json` intent (`npm audit fix`, `uv lock` refresh, Dependabot lock refresh) needs no ledger ID —
    just a journal line on completion; deliberate version decisions still need a task. Keeps the two repos' invariant
    sets in sync (same rule, two dialects).

### 2026-06-22
- **Platform-list centralization (review CR-C9) — `docs/review/codebase_review_2026-06-21.md`.** The OS-platform list
  `["linux.ubuntu","linux.alpine","macos","windows"]` was hardcoded in 52 `get_platform_support()` overrides +
  `build_analyzer` (×3) + `dependency_validator` choices + 2 test assertions. Added `SUPPORTED_PLATFORMS` to
  `core/metadata.py` (canonical `get_platform_support` returns it); **deleted 46 redundant overrides** (handlers/
  components/providers/workflows/inputs now inherit the default — validator uses `hasattr` so inherited is fine); kept
  `aplay` (linux-only restriction) + 3 single-platform test fixtures; `BaseRunner`/`InputManager` + tools + 2 test
  assertions reference the constant. **Build-safe by proof:** a golden snapshot of all 60 entry points'
  `get_platform_support()` is byte-identical before/after (only `aplay` non-default) and `--validate-all` stays 60/60, so
  `build_analyzer` sees identical values. CPU-arch gating (`get_supported_architectures` — the armv7/torch/sherpa lib
  path) is a separate method, untouched. Net −244 LOC / 53 files. Gates: suite 1066 passed, pyright 0, import-linter 9/9,
  12 profiles valid. CR-C9's standalone dedup is done; **ARCH-25 (WB7/WB8 on-device bring-up) remains a separate
  hardware-gated task** (not a review item). With this, **the whole-codebase review (§A/§B/§C/§D) is fully resolved.**
  Review tracker + this ledger updated.
- **Provider `/configure` gate dedup — CR-C8 completed (review) — `docs/review/codebase_review_2026-06-21.md`.** The
  byte-identical "set `default_provider` if it names a loaded provider, else warn and keep" block in 6 components'
  `/configure` endpoints (audio/asr/tts/llm/nlu/voice_trigger) → one base method `Component._apply_provider_config`.
  The `/providers` endpoints (×6) were assessed and deliberately left un-unified — they genuinely diverge (try/except
  only in asr/llm, defensive `getattr` in nlu, distinct per-provider fields + response models); a forced helper would
  change error-path behavior or be a leaky abstraction. New `test_apply_provider_config.py`. Gates: suite 1063 passed,
  pyright 0, import-linter 9/9. This closes CR-C8 (its is_api_available + MetricsPushMixin parts landed earlier in the
  CR-C6/C7/C8 pass); **review §C is now fully resolved** (CR-C9 belongs to ARCH-25). Review tracker + this ledger updated.
- **WebAPIPlugin component-walk dedup (review CR-C12) — `docs/review/codebase_review_2026-06-21.md`.** The "iterate
  `component_manager.get_components()`, filter `isinstance(.., WebAPIPlugin)`, build `(name, component)`" walk was
  reimplemented (with differing guards/logging) in `web_server._mount_component_routers` and `webapi_router` AsyncAPI
  spec generation. Extracted `web_api_components(core)` into `core/interfaces/webapi.py` (beside `WebAPIPlugin`) — it
  degrades to `[]` (warns) when there's no component manager or the lookup fails. Both walks now call it; the
  `/debug/asyncapi` endpoint (3rd `get_components()` site, lists *all* components) also reports `web_api_component_names`
  via the helper. New `test_web_api_components.py`. Gates: suite 1059 passed, pyright 0, import-linter 9/9. Review
  tracker + this ledger updated.
- **spaCy init dedup (review CR-C5) — `docs/review/codebase_review_2026-06-21.md`.** `_initialize_spacy` and
  `_initialize_spacy_with_assets` were ~75 near-identical lines; `is_available()`/`recognize()` branched on
  `self.asset_manager` to pick one while `_do_initialize` always used the assets variant — a fix could land on only some
  paths. Merged into a single `_initialize_spacy` (per-model asset step guarded by `if self.asset_manager:`, best-effort
  → degrades to a direct `spacy.load`); dropped the variant's always-no-op self-acquisition block so the no-asset
  "legacy path" still leaves `asset_manager` untouched. All three call sites collapse to the one method; existing
  `test_spacy_asset_integration.py` exercises both branches. Net −70 LOC. Gates: suite 1059 passed, pyright 0,
  import-linter 9/9. Review tracker + this ledger updated.
- **Asset-name / asset-path helper dedup (review CR-C10) — `docs/review/codebase_review_2026-06-21.md`.**
  `_get_asset_handler_name` was defined verbatim in `intent_asset_loader.py` and `cross_language_validator.py` (drifted —
  only the loader's validated), the inverse `[:-8]` was inlined 3×, and `assets_root / "<category>" / …` construction was
  repeated in ~30 methods. Extracted pure module helpers `asset_dir_name` / `base_handler_name` and an `_asset_path(*segments)`
  method (single source of the `assets/<category>/…` layout). The loader's `_get_asset_handler_name` keeps the CR-A15
  validation choke point; `cross_language_validator` imports `asset_dir_name` (its copy removed); 3 `[:-8]` blocks →
  `base_handler_name`; 32 path constructions → `_asset_path`. New `test_asset_naming.py`. Gates: suite 1052 passed,
  pyright 0, import-linter 9/9 (new core→core edge holds), 12 profiles valid. Review tracker + this ledger updated.
- **Handler base-class consolidation (review CR-C11) — `docs/review/codebase_review_2026-06-21.md`.** `can_handle` /
  `_get_template` / `_error_result` were copy-pasted across ~13 handlers and had drifted. Hoisted canonical versions to
  `IntentHandler` (base): donation-pattern `can_handle`; `_get_template` with the asset key derived from the module
  (`_template_asset` property) and always-format (unfilled placeholder is fatal); `_error_result` rendering
  `self._error_template` (default `error_general`). Removed 12 `can_handle` (all but `conversation` — genuine
  `fallback_conditions` override), 12 `_get_template`, 6 `_error_result`; 5 handlers set the `_error_template` class
  attr. **Drift fixed via donation data, not code:** `timer`/`datetime` were the only handlers missing `domain_patterns`
  in their contract (the reason for their hardcoded domain check) — added `domain_patterns: ["timer"]` / `["datetime"]`
  to `contract.json` (language-neutral; `ru.json`/`en.json` need no change) and dropped the overrides. `greetings` keeps
  its distinct `_get_template_data` (returns `List[str]`, not the scalar `_get_template`). Net −665 LOC across 14 files.
  Gates: suite 1052 passed / 0 failed, pyright 0, import-linter 9/9, 12 profiles valid. Review tracker + this ledger updated.
- **Retired the duplicate boot-time handler validator (review CR-C13) — `docs/review/codebase_review_2026-06-21.md`.**
  `intent_asset_loader._validate_method_existence` imported each handler module + scanned its classes per donation to
  check method existence (`hasattr`), duplicating the contract validator (`validate_contract_wiring`), which imports
  each handler once and does the stricter `callable(getattr(...))` check (both raise `DonationDiscoveryError`). Deleted
  the method + call. **User approved the config-ui/schema change**, so did the full removal: dropped the
  `validate_method_existence` flag from `AssetLoaderConfig`, `DonationValidationConfig`, the `asset_validation` default,
  4 config TOMLs (config-master + 3 build profiles), and 5 tests. config-ui needs no change — it has no specific
  reference (`asset_validation` is a free-form `Dict[str, Any]`). Hardened `AssetLoaderConfig` to absorb unknown/stale
  keys (`**_ignored`) so the `AssetLoaderConfig(**config.asset_validation)` unpack can't crash on a leftover key. New
  `test_asset_loader_config.py`. Gates: 12 profiles valid (`config-master-canonical`), suite 1050 passed / 0 failed, pyright 0,
  import-linter 9/9. Review tracker + this ledger updated.
- **Audio playback made real (review CR-A5) — `docs/review/codebase_review_2026-06-21.md`.** Purpose: system/
  notification sounds (e.g. a timer-done chime) from a local media library. The play/stop fire-and-forget actions were
  simulated (`sleep` + a 10% `random` failure; real call commented out), and play *couldn't* be wired because the domain
  `AudioPort` didn't expose `play_file` (only the component did). Added `play_file` to `AudioPort` (component already
  implements it → satisfied), wired `_start_audio_playback_action` → `play_file(path)` and
  `_stop_audio_playback_action` → `stop_playback()` (honest — no "assume success"), and dropped `random`/`sleep`. Added a
  **provisional** `_resolve_media_file` (`<assets_root>/audio/<name>` with a single-safe-segment + stay-in-dir traversal
  guard, since the name comes from an utterance) — clearly marked to be replaced when the text→media mapping is redone;
  non-`local` source → clean "unsupported". Tests rewritten (`test_audio_playback_handler_coverage.py`) to exercise the
  real path via a stub port. Gates: suite 1050 passed / 0 failed, pyright 0, import-linter 9/9. **Review §A is now fully
  resolved.** Note: `<assets_root>/audio/` is the media dir (currently empty — drop sound files there). Review tracker +
  this ledger updated.
- **CR-A6 follow-up: switched the donation-source access to the component DI pattern.** The initial CR-A6 reached the
  NLU component's `asset_loader` via `core.component_manager.get_component("nlu")` (a "core-reach" the newer QUAL-24
  port code avoids). Tightened to the injected pattern: `NLUAnalysisComponent.get_component_dependencies()` now returns
  `["nlu"]`, so the manager topo-orders NLU first and injects it; `_get_asset_loader()` reads it via
  `self.get_dependency("nlu")` (dropped the stored `self._core`). Suite 1048 passed, pyright 0, import-linter 9/9.
- **NLU-analysis donation loaders implemented (review CR-A6) — `docs/review/codebase_review_2026-06-21.md`.**
  `_get_context_units` / `_get_all_intent_units` were `return []` stubs, so the NLU-analysis endpoints always reported
  "healthy / no conflicts". Implemented them to enumerate the loaded donations off the NLU component's
  `IntentAssetLoader` (`get_all_handlers_with_languages` → `get_language_phrasing_for_editing`) and build one
  `IntentUnit` per (handler, language); the context variant excludes the candidate handler. Resolved lazily through
  `core` so it degrades to empty (no crash) before the donation source is up. **Bonus:** fixed `_donation_to_intent_unit`
  — it read `methods` (a dict), but real donations use `method_donations` (a list), so even the realtime path produced
  empty units; now reads the real shape with a legacy fallback. New `test_nlu_analysis_loaders.py`. Gates: suite 1047
  passed / 0 failed, pyright 0, import-linter 9/9. Review §A now clear except CR-A5 (audio_playback — next). Review
  tracker + this ledger updated.
- **Cyrillic/script-detection dedup (review CR-C3) — `docs/review/codebase_review_2026-06-21.md`.** The `Ѐ–ӿ` Cyrillic
  test (+ latin/CJK ranges) was copy-pasted across 6 sites in 5 files (`spacy_provider`, `hybrid_keyword_matcher`,
  `nlu/llm` — which used literal `"Ѐ"`/`"ӿ"` bounds — `nlu_component`'s char-count→ratio, and `analysis/hybrid_analyzer`
  ×2). Extracted one source of truth `irene/utils/text_script.py` (`is_cyrillic`/`is_latin`/`is_cjk`,
  `contains_cyrillic`, `cyrillic_char_count`, `detect_language_by_script`) and refactored all six to it — the three NLU
  providers in one cascade can no longer drift on the ru/en split. Pure foundation module; ARCH-12 import contract
  holds. New `test_text_script.py`. Gates: suite 1040 passed / 0 failed, pyright 0, import-linter 9/9. Review tracker +
  this ledger updated.
- **Correctness trio (review CR-A10/A11/A16) — `docs/review/codebase_review_2026-06-21.md`.** **CR-A10:**
  `asr/base.audio_contract` read the voice-trigger-only `get_supported_sample_rates` (never present on ASR) → the
  contract was always `[16000]`; now calls the real `get_preferred_sample_rates()`. **CR-A11:**
  `voice_synthesis._handle_speak_text` crashed on an explicit `text: null` entity (`.get("text", raw_text)` only falls
  back when the key is absent) → now coalesces `entities.get("text") or raw_text or ""`. **CR-A16:** the 5 self-routing
  handlers (`conversation`/`datetime`/`greetings`/`system`/`timer`) override `execute()` and bypass
  `execute_with_donation_routing`'s QUAL-30 boundary, so a `ParameterExtractionError` would be swallowed by their broad
  `except` → added an `except ParameterExtractionError → self._clarify(...)` clause to each, restoring the
  explain-and-ask clarification path. New `test_correctness_a10_a11_a16.py`. Gates: suite 1036 passed / 0 failed,
  pyright 0, import-linter 9/9. Review §A is now clear except CR-A5/A6 (genuine feature-completion). Review tracker +
  this ledger updated.
- **Asset-loader path-traversal hardening (review CR-A15, security) — `docs/review/codebase_review_2026-06-21.md`.**
  User-supplied `handler_name` / `domain` / `language` flowed unsanitized into `assets_root / … / <segment>` reads AND
  writes in `intent_asset_loader.py` (some via FastAPI path params). Added `_safe_path_segment()` (single traversal-safe
  segment only — no separators, `..`, leading dot, absolute, or NUL) and applied it everywhere: `handler_name` via the
  single choke point `_get_asset_handler_name` (covers all handler-derived paths), `domain`/`language` at the top of the
  10 editing/save/reload methods. Fail-closed (raises `ValueError` or returns the method's failure sentinel — both block
  the escape). New `test_asset_path_traversal.py` asserts nothing escapes the root and valid inputs still work. Gates:
  suite 1031 passed / 0 failed, pyright 0, import-linter 9/9. Review tracker + this ledger updated.
- **Tracing pair fixed (review CR-A7/A9) — `docs/review/codebase_review_2026-06-21.md`.** **CR-A7:**
  `workflow_manager.process_text_input` lost the trace when the workflow raised (no try/except; `_save_trace_if_enabled`
  sat after the `trace_scope` block) — observability gone exactly when a bug fired. Now mirrors `process_audio_input`:
  records a `workflow_manager_text_error` stage + saves the trace, then **re-raises** (callers convert it to
  HTTPException 500 — return-error-result would have turned 500s into 200s). **CR-A9:** trace-value redaction was
  raw-substring matching, so `session_id` (⊃ session), `keyword`/`matched_keys` (⊃ key), and `author` (⊃ auth) were all
  `[REDACTED]`. Switched to word-TOKEN matching (`_key_tokens` splits on separators + camelCase) and dropped `session`
  from the secret set; real secrets (`api_key`, `access_token`, `authorization`, `password`, …) still redact. New
  `test_trace_fixes.py`. Gates: suite 1024 passed / 0 failed, pyright 0, import-linter 9/9. Review tracker + this
  ledger updated.
- **Silero TTS cleanups (review CR-A12/A13) — `docs/review/codebase_review_2026-06-21.md`.** **CR-A12:**
  `silero_v3.is_available` did a blocking `requests.head(model_url, timeout=5)` inside an async method (the QUAL-15
  anti-pattern) — now local-only (`torch` present), matching v4; the model still downloads lazily and fails through the
  fallback chain. **CR-A13:** `silero_v4._download_model` hardcoded the RU wheel URL, ignoring `self.model_url`/
  `model_id`; now uses `self.model_url` like v3. Both fixes made the two methods identical (modulo the `self._version`
  log label the base already parameterizes), so **hoisted `is_available` + `_download_model` into `SileroTTSBase`** and
  dropped the per-class overrides — finishing the CR-C6 dedup these bugs had blocked. New regression tests in
  `test_tts_provider_fixes.py`. Gates: suite 1021 passed / 0 failed, pyright 0, import-linter 9/9. Review tracker + this
  ledger updated.
- **Standalone correctness fixes (review CR-A4/A8) — `docs/review/codebase_review_2026-06-21.md`.** **CR-A4:**
  `tts/vosk.py is_available` probed the wrong asset namespace `("vosk","tts")` (matched nothing) → a clean install
  reported vosk-TTS unavailable and never downloaded the model; now queries `("vosk_tts","ru_multi")` as the rest of the
  provider does. **CR-A8:** `tts/elevenlabs.py synthesize_to_file` swallowed errors and returned without writing a file
  (caller then read a non-existent WAV, fallback chain never engaged); now re-raises `RuntimeError` like silero/vosk/
  piper. New `test_tts_provider_fixes.py` (correct-namespace probe + raise-on-failure / no-phantom-file). Gates: suite
  1016 passed / 0 failed, pyright 0, import-linter 9/9. Review tracker + this ledger updated.
- **Provider-base duplication dedup (review CR-C6/C7/C8) — `docs/review/codebase_review_2026-06-21.md`.** Behavior-
  preserving base/mixin extractions, run as 3 parallel specialists over disjoint files (llm/, tts/, components/), then
  verified together. **CR-C6:** new `silero_base.py::SileroTTSBase` holds the ~80%-shared Silero body; `silero_v3`/
  `silero_v4` subclass it and override only the genuinely-different bits (model URLs, `is_available`, synthesis engine,
  speakers). **CR-C7:** hoisted the byte-identical `_GENERIC_SYSTEM_FALLBACK`/`_LLM_TEMPERATURE` + default
  `get_supported_tasks` into `LLMProvider`; dropped redundant `get_platform_*` overrides; left genuinely per-provider
  bits alone. **CR-C8 (partial):** `is_api_available` → one `Component` base copy; metrics-push trio → `MetricsPushMixin`
  (ASR + voice_trigger); the `/configure`(×7) + `/providers`(×6) FastAPI route handlers deferred to a dedicated pass
  (per-component response models; not worth the route-behavior risk). Added typed stubs for subclass-provided members so
  pyright stays 0 without `TYPE_CHECKING` (`no-type-checking`). ~−180 lines across the three. Gates: suite 1013 passed / 0
  failed, pyright 0, import-linter 9/9. Review tracker + this ledger updated.
- **Dead-code sweep (review CR-B) — `docs/review/codebase_review_2026-06-21.md`.** Removed 22 verified-dead methods +
  a no-op fallback stub + an orphaned example package, across `irene/core/` (debug_tools, analytics_dashboard, metrics,
  workflow_manager, components), `irene/components/base.py` (the dead `Component.start`/`is_dependencies_available`
  path), `irene/runners/` (cli + base interactive-help/status + dependency-status helpers), two intent handlers, and
  `silero_v3` (duplicate `raise`). **CR-B3:** `_attempt_fallback_initialization` (always returned False) deleted and
  `_handle_component_failure` collapsed to its real behavior. **CR-B9/B10/B11:** dropped the unused `python-modules.txt`
  build output, the empty `config-writing` extra (+ 3 umbrella refs; `headless` now base-only), and the orphaned
  `irene/examples/` (6 demos). **CR-B12** was already done (QUAL-20 cut Porcupine). **CR-B4 KEPT — not dead:** the
  `client_registry` ESP32 methods are tested (`test_phase1_integration.py`) + documented in the current
  `docs/architecture/client-registry.md` (ESP32 fleet, ARCH-22/25). `uv.lock` regenerated. Gates: suite 1013 passed / 0
  failed, pyright 0, import-linter 9/9. Review tracker + this ledger updated.
- **BUILD-7 doc/dup review cluster fixed (CR-C1/C2/C4, CR-D1–D4) — `docs/review/codebase_review_2026-06-21.md`.**
  Dedup: **CR-C1** collapsed the spaCy model `@`-URL wheel specs to one `_SPACY_MODEL_SPECS` constant in
  `spacy_provider.py` (referenced by both `get_python_dependencies` and `get_asset_config`); **CR-C2** replaced the two
  hand-rolled `>=`/`==`-only package-name ladders in `dependency_validator.py` with one shared regex
  `_extract_package_name()` — also fixing the latent bug where `<`/`~=`/`!=` specs (base `numpy<2`) fell through to a
  literal and warned falsely (new `test_dependency_validator.py`); **CR-C4** dropped the redundant base-dep
  re-listings (`numpy`, `aiohttp`) from the `wake-onnx`/`wake-tflite` extras. Docs: **CR-D1/D2/D3**
  (`howto-new-model.md`, `build-system.md`, `howto-new-intent.md`) now teach the extra-NAME contract for
  `get_python_dependencies` (was teaching raw specs — a new-provider author would have produced a dead extra);
  **CR-D4** replaced the stale "~2.5 GB" image-size estimate in the `[tool.uv.index]` comment with the confirmed
  6.44 → 3.16 GB. `uv.lock` regenerated. Gates: suite 1013 passed / 0 failed, pyright 0, import-linter 9/9. Remaining
  review items still open (CR-A4–A16 minus done, CR-B, CR-C3/5–13, CR-D5 done in the CR-A1 group).
- **CR-A1 group fixed (standalone-runtime cluster) — `docs/review/codebase_review_2026-06-21.md`.** **CR-A1 (P0):** the
  shipped x86_64 standalone served no web API — `voice_runner._post_core_setup` `await`ed the infinite mic loop, so
  `_setup_web_server` never ran. Now launched as a tracked background task (`asyncio.create_task` + done-callback to
  surface a mic crash + cancel-on-shutdown in `_execute_runner_logic`). Bundled the same-path / same-boot items:
  **CR-D5** (web banner advertised deleted `/asr/stream,/asr/binary` → real `/ws/audio` + `/ws/audio/reply` +
  `/ws/observe` + `/ws/output`), **CR-B2** (deleted the dead `set_input_manager` + `_start_audio_workflow`→
  `_run_workflow`→`_get_input_source` audio-start cluster in `workflow_manager`; live `_get_audio_stream` kept),
  **CR-A2** (ASR reconciles `default_provider` to a provider that actually loaded — was hard-failing every request when
  the configured default failed to load), **CR-A3** (ASR `initialize` re-raises so the ComponentManager degradation
  path engages instead of reporting healthy-with-zero-providers), **CR-A14** (monitoring `_start_time` set in
  `__init__` → uptime no longer always ~0). **Tests:** added `TestMicTaskLifecycle` (CR-A1 regression — a never-returning
  mic workflow must not block web setup) replacing the `AsyncMock` stub that hid the bug; updated the `_post_core_setup`
  assertions to the background-task contract; fixed 2 stale **BUILD-7** metadata tests (`test_miniaudio_provider_metadata`,
  `test_classmethod_build_metadata`) asserting the old raw-spec return. **Gates:** suite 1010 passed / 0 failed, pyright 0,
  import-linter 9/9. CR-A5 (audio_playback simulation) + CR-A6 (nlu_analysis stub loaders) re-confirmed but deferred
  (feature-completion). Review tracker + this ledger updated.

### 2026-06-21
- **Whole-codebase review filed → `docs/review/codebase_review_2026-06-21.md`.** 7 parallel finder passes
  (subsystem + cross-cutting dead-code/duplication/doc-claim specialists) over `irene/` + `docker/` + `pyproject.toml`
  + `docs/guides/`. 47 findings with stable IDs: 16 correctness (CR-A), 13 dead/zombie (CR-B), 13 duplication (CR-C),
  5 stale user-facing doc claims (CR-D). Top items verified against source by hand. **Headline (CR-A1, P0):** the
  shipped x86_64 standalone image's web API never starts — `voice_runner._post_core_setup` `await`s the infinite mic
  loop (`:232`) instead of `create_task`, so `_setup_web_server` never runs (CI green only because the test stubs the
  method). Also: ASR never reconciles `default_provider` to a loaded provider (CR-A2); `audio_playback` "play" is a
  shipped simulation (CR-A5); `nlu_analysis` endpoints always report "healthy" via stub loaders (CR-A6). Cross-refs
  recorded (CR-B1→BUILD-7, CR-C1/2/4/D1-4→BUILD-7, CR-C9→ARCH-25, CR-A12→QUAL-15, CR-A16→QUAL-30). **Unaddressed —
  to be triaged/fixed one-by-one or in groups later.** Doc registered in the RELEASE_PLAN review-doc table.
- **Docker images de-bloated (CPU-only torch) + finished the BUILD-5-deferred `get_python_dependencies()` extra-names
  migration (BUILD-7).** The standalone (torch) image was ~6.44 GB. An audit (docker-export of all 3 *published* images)
  proved **no model assets are baked** — `/app/assets` is an empty mount, 0 model files in any image; the satellites are
  763 MB / 233 MB. The bloat was the default PyPI torch dragging ~3.4 GB of unused NVIDIA CUDA + Triton wheels into a
  `device="cpu"` runner (nvidia 2724 MB + triton 696 MB + CUDA-laden torch 1075 MB). Fix: pin torch/torchaudio to the
  CPU wheel index via `[[tool.uv.index]]` (explicit) + `[tool.uv.sources]`. **Key finding:** the `uv pip` interface
  IGNORES `[tool.uv.sources]` for loose `-r` specs but HONORS them for the project's own optional-deps
  (`uv pip install .[extra]`) — so the pin only lands if torch arrives via an EXTRA, not a raw spec in `pip-specs.txt`.
  torch was a raw spec because providers (whisper/silero) declared raw pip specs in `get_python_dependencies()`,
  violating the `metadata.py` contract (it returns extra-NAMES). So finished the migration: **31** providers/components/
  inputs/handlers now return extra-names (or `[]` for base-dep-only); added 10 granular per-provider extras
  (`tts-silero`/`tts-pyttsx`/`tts-elevenlabs`/`tts-vosk`, `asr-vosk`, `audio-sounddevice`/`audio-miniaudio`,
  `llm-openai`/`llm-anthropic`, `nlu-spacy`) and turned `tts`/`llm`/`audio-output`/`audio-input`/`nlu` into umbrellas;
  `dependency_validator` made extra-name-aware. spaCy language models STAY as raw `@`-URL specs (the one justified
  exception) so `derive._spacy_keep` keeps trimming them per-config. The `Dockerfile.x86_64` cpu-torch two-step bridge
  was **removed** — torch now CPU-pins automatically through the `advanced-asr`/`tts-silero` extras. `uv.lock`
  regenerated: torch `2.12.1+cpu`, **0 nvidia packages**, `uv lock --check` green. Runtime-safe: the only import-based
  consumer (`Component.start`→`is_dependencies_available`) is dead code (ComponentManager uses `initialize()`; nothing
  calls `.start()`) — flagged for cleanup, not touched. **Build-confirmed (all 3 images rebuilt green):** standalone
  **6.44 GB → 3.16 GB** (nvidia 2724 MB → 0, torch `2.12.1+cpu`); satellites byte-identical (763 MB / 233 MB); still 0
  models baked; aarch64 spaCy trim verified (4 declared → 2 `sm` pulled). `triton` (688 MB, `openai-whisper`'s sole
  requirer, unused on CPU) parked as a follow-up; numba/llvmlite must stay (top-level import in whisper).

### 2026-06-16
- **ARCH-10 closed (implementation); WB7/WB8 hardware bring-up split out as ARCH-25.** With the streaming-endpoint
  sliver landed, ARCH-10's software scope is 100% complete (all PR slices, the VAD seam, the ESP32 streaming endpoint —
  all green). The only thing it still carried was the WB7/WB8 **on-device re-validation**, which ARCH-10 was also the
  named convergence point for (ARCH-24/BUILD-3, QUAL-19/20 all defer their hardware verification "to ARCH-10
  completion"). Rather than hold the whole INFER implementation open behind a hardware pass — or close it and orphan
  that obligation — split the hardware work into a dedicated **ARCH-25** (`[release]`, satellite hardware bring-up:
  boot, ASR RTF/latency, on-device streaming-endpoint validation, TTS reply, aarch64 wake-word) and repointed every
  "stays with ARCH-10" reference (ARCH-23 T4, the ARCH-24 + BUILD-3 closures, QUAL-19, QUAL-20) at it. ARCH-10 is now
  `[x]`; ARCH-25 gates Definition-of-release item #1. Net: the inference-layer *implementation* reads as done; the
  hardware obligation has an explicit, accurately-named home instead of hiding inside a `[~]`.
- **ARCH-10 — ESP32 server-authoritative streaming-endpoint built + seam-tested (device-validation hardware-gated).**
  Wired the no-VAD `/ws/audio` path so the ASR *model* marks end-of-utterance (sherpa `OnlineRecognizer`), for the
  always-on / background-noise / TV case where the device can't endpoint. The ASR port gained a typed
  `transcribe_stream_segments` yielding `(text, is_final)` — a concrete buffer-once default in `asr/base.py` (safe for
  offline providers) and a sherpa override that does real incremental endpointing (partials + endpoint-/EOF-finalized
  segments) — plus a `supports_streaming` capability flag. The ASR component exposes a thin pass-through so the provider
  stays behind the port. `/ws/audio` got a branch, selected by the device's `mode:"streaming"` register field AND
  `supports_streaming()`: partials are forwarded as `{"type":"partial"}`, and each finalized segment is injected via
  `workflow_manager.process_text_input`. **Confirmed against the code where the streaming ASR result reaches the next
  stage:** `process_text_input` enters the unified pipeline at **Text Processing → NLU → Intent → Response** (skip_asr /
  skip_wake_word only skip the audio front-end), so the streamed transcript gets the same normalization tail as the batch
  audio path — the only difference is ASR running at the edge vs. inside the workflow. Backward-compatible: `{"type":"end"}`
  still works as a hard finalize, and a non-streaming ASR falls through to the device-signalled batch floor. Also fixed a
  stale `workflow_manager.py` comment that wrongly said the TEXT entry "enters at NLU" (it enters at Text Processing). 4
  new seam tests (`test_ws_streaming_asr.py`, fake streaming ASR) green; suite 1007 passed, pyright 0, 9/9 import
  contracts. Real endpoint RTF/latency validation waits on the WB7 hardware re-val. Trade-off recorded: streaming-mode
  utterances trace as a *text* input, so there's no per-provider ASR-stage trace for them (relevant to QUAL-53).
- **ARCH-24 + BUILD-3 closed.** With the images green, the docs rewritten, and a re-check of every tranche — T1/T2
  providers, T3 armv7 torch-ban CI gate, T4 the three baked configs, T5 the `inference_policy`/`torch_model_cache`
  sherpa helpers (all present with tests) — both items are engineering-complete. The only outstanding work is
  on-hardware boot / on-device verification (WB7 armv7, WB8.5 aarch64), which is hardware-gated and already owned
  downstream by ARCH-10's WB7/WB8 re-validation and the Definition-of-release gate (BUILD-3 "Gates Definition-of-release
  item #1"). Holding the two dev tasks open for it duplicated that tracking and understated the engineering state, so
  both are marked `[x]` with the hardware remainder pointed at where it lives.
- **ARCH-24 / BUILD-3 — user-facing Docker guide rewritten (`user-facing-docs-are-done`).** Rewrote
  `docs/guides/build-docker.md` to match the shipped reality: the three published images (`wb-mqtt-voice-{standalone,
  aarch64,armv7}` on GHCR) with their role/architecture table, the standalone-vs-satellite split (standalone drives
  `/dev/snd`; satellites are web-only), the baked-config + mounted-assets-root contract, `docker run`/compose recipes
  against the published tags, and a local-build section (context = repo root, `docker/Dockerfile.*`, `CONFIG_PROFILE`).
  Dropped the stale two-Dockerfile / port-8000 / `minimal|api-only|voice` content and all internal references
  (task IDs, review-doc links, status banners) per the user-facing-prose rule. README + `build-system.md` cross-links
  checked — both generic and still accurate, no diagram to regenerate. This closes the documentation tail of the
  ARCH-24/BUILD-3 packaging work; only on-hardware boot verification (WB7/WB8.5) remains.
- **BUILD-3 — all three images build green on GHCR; spaCy model wheels trimmed config-aware.** Closed out the
  Dockerfile-design + per-image-workflow steps. The three Dockerfiles were realigned to the wb-mqtt-bridge 3-stage
  shape (analyzer → builder building into `/opt/venv` via `uv` → lean runtime that `COPY --from=builder`s the venv),
  with the **config baked** (`COPY` profile → `/app/runtime-config.toml`, `IRENE_CONFIG_FILE`, no entrypoint script)
  and the **whole `assets/` tree externalized** as the mount *and* the assets-root (`IRENE_ASSETS_ROOT=/app/assets`;
  models/cache/credentials resolve underneath), shipped as a CI archive artifact the way the bridge ships configs. All
  runners now serve the **full web API alongside** their primary input through a new `WebServerMixin` (voice = blocking
  serve + mic background; cli = REPL foreground + web background; webapi = web-only), and config-from-env let the
  entrypoint script go. `web_port` moved 8000→6000 everywhere (8000 is the bridge's). Added
  `.github/workflows/build-images.yml` (`workflow_dispatch` per target → buildx → GHCR, per-target gha cache, assets
  artifact). Repo hygiene: Dockerfiles + `derive_build_reqs.py` moved under `docker/`; added a repo-root `.dockerignore`.
  Five build patterns had to be fixed across all three Dockerfiles before they went green — analyzer needs `.[web-api]`
  (components import fastapi); `COPY --from` paths resolve at the *stage* root not WORKDIR; `uv` ignores `pip.conf` so
  ARM builders need `UV_EXTRA_INDEX_URL=piwheels` + `UV_INDEX_STRATEGY=unsafe-best-match` (else numpy/pyyaml/rapidfuzz
  compile from source); `uvicorn[standard]` drags in uvloop/httptools/watchfiles (watchfiles needs Rust) → dropped to
  plain `uvicorn`; spaCy `name @ URL` specs must go one-per-line through `uv pip install -r` because an unquoted
  `$(cat …)` shell-splits the embedded spaces. **Why the spaCy trim:** spaCy language models are PEP 508
  direct-reference *wheels* installed at build time (unlike the runtime-downloaded whisper/vosk/piper/silero assets),
  and the provider statically lists every model+tier — so an image baked all four (ru/en × sm/md). `derive_build_reqs.py
  --config <profile>` now reads the profile's `nlu.spacy_nlu.language_preferences` and keeps only the first-preference
  model per supported language; build logs confirm aarch64 ships the **sm** pair and standalone the **md** pair (each
  dropped 2). Aligned the baked wheels to spaCy **3.8.0** to match ASSET-1's model refresh. Remaining for the release
  phase: on-hardware boot (WB7/WB8.5) and the user-facing `build-docker.md` rewrite.
- **ARCH-24 T4 / BUILD-3 — standalone (x86_64) config built; all 3 target configs DONE.** New
  `configs/standalone-x86_64.toml`: the lone non-satellite target — a full local voice runner
  (mic→VAD→wake→ASR→NLU→TTS→playback) on the one torch image. ASR = `whisper` (torch) small, TTS = `silero_v4` (torch)
  voice **baya** (female, matches the satellites' persona), NLU = keyword → **spaCy(md)** → llm (the x86 box has room for
  the mid-size model), VAD = silero, wake-word = openWakeWord, mic + speaker on, monitoring/nlu_analysis/dashboard on
  (full image). It's the image's baked default; the x86_64 image is built full-deps so a mounted/env override (entrypoint,
  step 4) can reach any provider. Validates; x86_64 arch gate passes (20 modules / 21 py deps); all 14 configs green.
  **The three target configs (armv7 / aarch64 / standalone) are now complete → BUILD-3 next: the shared Dockerfile-design
  session, then per-image workflows + on-hardware build/boot.**
- **ARCH-24 T4 / BUILD-3 — aarch64 (WB8.5/Pi satellite) config built.** New `configs/embedded-aarch64.toml`: same
  back-half satellite role as armv7, but 4 GB + no ORT wall lets it run the bigger torch-free models — ASR =
  `sherpa_onnx` + **whisper-small** (`model_type=whisper`, num_threads=4 per the user — heavy model on the A53), TTS =
  **`piper_ruaccent`** (irina; RUAccent Russian stress) with plain `piper` + console fallback, NLU = keyword →
  **spaCy(small: ru_core_news_sm)** → llm (the 64-bit deterministic tier the WB7 can't have, per the user) → llm. audio
  off, VAD/voice_trigger off, monitoring/nlu_analysis kept (traces), `[trace]` toggle present (off). torch deliberately
  excluded (footprint + A53 latency). Validates; arch gate passes (aarch64-compatible, 16 modules / 14 py deps); all 13
  configs green. **BUILD-3 next: standalone config**, then the shared Dockerfile-design session + per-image workflows.
- **ARCH-24 T4 / BUILD-3 — armv7 (WB7 satellite) config built; CoreConfig TTS↔Audio rule relaxed.** Resumed the
  armv7 config session (unblocked by QUAL-50/51). Rewrote the stale `configs/embedded-armv7.toml` as the back-half
  satellite stack from the deployment matrix: ASR = `sherpa_onnx` + vosk-small (whisper-small barred by WB7 RAM; Kaldi
  vosk has no armv7 wheel), TTS = `piper` direct voice **irina**, NLU = `hybrid_keyword_matcher` → **`llm`** cascade (no
  spaCy — no armv7 wheel), LLM = deepseek (NLU fallback + conversation) with console floor. Decisions (with the user):
  ASR `num_threads=2` (leave 2 A7 cores for the co-hosted wb-mqtt-bridge/ui); keep monitoring + nlu_analysis ON for now
  (traces) with a documented build-time lean-down; **audio component DISABLED** (no speaker — the workflow no-ops local
  playout, and the TTS reply rides the output seam / RemoteAudioOutput, finalized in the ESP32 transport work). Added a
  documented `[trace]` toggle (off; for QUAL-53). VAD/voice_trigger off (ESP32 owns them). **Surfaced + relaxed** the
  `CoreConfig` "TTS requires Audio" cross-validator (`models.py`): it predated the output seam: now it requires Audio
  only when `system.audio_playback_enabled` is true — a headless satellite may run TTS without local Audio. Parallel CLI
  warning conditioned the same way; `test_tts_audio_separation` updated (raise-when-local + ok-for-headless); `audio.md`
  reconciled (Inv #10). All 12 configs validate; suite 1001 green, pyright 0, contracts 9/9. **BUILD-3 next:** aarch64 +
  standalone config sessions, then the Dockerfiles + per-image workflows.
- **QUAL-51 — classifier prompt tightened + live-validated; QUAL-53 split out.** Interactive requirements session first
  (scope, prompt-language strategy, validation approach, few-shot source). Reworked the inline classifier prompt:
  conservative abstain-when-unsure framing, explicit JSON contract + verbatim-evidence anti-hallucination, and the
  taxonomy + few-shot **filtered to the utterance language** by script. Few-shot = hand-written abstain exemplars per
  language + auto-sourced positives from donation `examples`. Decisions (with the user): English-only instructions (they
  work cross-lingually; the taxonomy/utterance carry the language), classifier keys off `context.language`, prompt kept
  **inline** because it's assembled from donations at runtime (not a static asset) — `prompting.md` now documents that one
  generated exception (Inv #10). Tuned the `missing_parameter` clarification template (en+ru). Built a live eval harness
  (`scripts/eval_llm_nlu.py`) + bilingual fixture (24 cases over the real 54-intent taxonomy, DeepSeek via `.env`): scored
  **24/24** after correcting two over-specified fixture cases (the model legitimately preferred `translation.specific` and
  abstained on a vague help request). Added offline prompt-logic tests (test_llm_nlu.py → 18). The keyword-matcher-feedback
  half isn't automatable in a prompt session — split to **QUAL-53** (trace-driven cheap-tier analysis), which first needs
  the NLU cascade trace enriched to record per-provider attempts (today only the final result is traced). Suite green,
  pyright 0, contracts 9/9.
- **`user-facing-docs-are-done` added (user-facing docs are part of "done") + QUAL-50 doc correction.** Prompted by a slip in the
  QUAL-50 doc update: `architecture/nlu.md` had picked up internal tracking language (a task ID, raw config keys, an
  internal class name) that doesn't belong in user-facing prose, and its cascade diagram wasn't updated. Filed Invariant
  #10: every task must check whether the user-facing docs (`architecture/*`, `guides/*`, `README*`) need updating, match
  their explanatory voice (no task IDs / ledger refs / internal symbols), and update + regenerate any diagram the change
  affects in the established visual style. Reworked the `nlu.md` language-model-tier paragraph into the document's voice
  and regenerated `images/nlu-cascade.png` (+ `.dot`) to show the optional language-model stage (dashed, same palette).
- **QUAL-50 — LLM NLU classifier built (cascade fallback).** New `irene/providers/nlu/llm.py` `LLMNLUProvider`: behaves
  like keyword/spaCy — `recognize_with_parameters` makes one deterministic `LLMPort.generate_response` call (temp 0.0 from
  QUAL-52 PR4), classifies into a donation-taxonomy intent + extracts raw param spans, and returns a **plain `Intent`** or
  `None`. No structured output, no catalog in the prompt — grounding stays in the shared `ContextualEntityResolver`
  downstream (the QUAL-52-PR3-revert lesson, applied). Derived confidence: abstain unless intent∈donations [gate] + an
  evidence span actually in the text [anti-hallucination]; else `0.7 + 0.25×required-coverage` so a missing required param
  still clears the threshold and the handler's QUAL-30 `_clarify` asks for it. Injection mirrors the conversation handler
  (`set_llm_component(LLMPort)`, soft-injected from `core.component_manager` — no hard dep, no-LLM builds still start).
  Wiring: schema registered, `[nlu.providers.llm]` opt-in block, pyproject entry-point; default cascade unchanged. Contracts
  held — a provider importing `intents.ports.LLMPort` is ARCH-4-legal (forbids only components/workflows). `test_llm_nlu.py`
  (13). Suite 995 green, pyright 0, contracts 9/9, config-ui type-checks (Inv #4). Unblocks ARCH-24 T4; prompt → QUAL-51.
- **QUAL-52 PR4 — dropped the temperature / fine-tuning knobs.** Per "temperature and fine-tunings aren't needed": removed
  `temperature` from the 3 LLM provider schemas, config-master, and the providers' config/kwargs plumbing (plus the dead
  `top_p`/`frequency_penalty`/`presence_penalty` no provider ever read); each provider now uses a fixed module-level
  `_LLM_TEMPERATURE = 0.0` — deterministic is what every LLM use here wants (ASR correction, translation, the QUAL-50
  classifier). Whisper ASR's decoding `temperature` untouched (different concern). config-ui: no typed temperature field
  (free-form params dict) → nothing to sync, openapi unchanged. Suite 982 green, pyright 0, contracts 9/9.
- **QUAL-52 PR3 REVERTED — structured/JSON LLM output rested on a wrong premise.** PR3 added `generate_structured` +
  `response_format` json_object plumbing as "the path the QUAL-50 NLU classifier returns through". On re-examination (you
  flagged it) that's wrong: an NLU provider returns a **plain `Intent`** {name, entities, confidence}, identical to
  keyword/spaCy — there is no place in the cascade for a bespoke structured object. Parameter extraction is the provider's
  `extract_parameters` step; catalog grounding is the **shared** `ContextualEntityResolver` applied downstream to *every*
  provider's Intent. So the LLM classifier needs only a plain text classification call + the existing extract/resolve — not
  a generic JSON-dict capability on the component. Reverted `generate_structured`/`_parse_json_response`/the response_format
  pass-through/`test_llm_structured.py` (commit `beb08e3`); kept PR1 (budgets) + PR2 (fit_messages) — independent and
  correct. QUAL-50 design corrected in the ledger (plain Intent, raw spans not catalog IDs, no `LLMPort.generate_structured`).

### 2026-06-15
- **QUAL-52 PR2 follow-up — `context_window` in config (you flagged: only the output side was defined).** PR1 put the
  output budget (`max_tokens` → model max) into config but the input `context_window` lived only in the code registry.
  Added `context_window` to the LLM provider config + schemas (deepseek 64000 / gpt-4o 128000 / claude 200000) and a
  `context_window_for(model, override)` resolver; the providers pass it to `fit_messages`, so the budget is now fully
  config-defined (input + output), defaulting from the registry but overridable for custom models. Suite 982 green,
  pyright 0, contracts 9/9, config-ui builds (Inv #4).
- **QUAL-52 PR2 — budget-aware prompting (dependency-free).** Added `estimate_tokens` (**utf-8 bytes/4** — accurate for
  English, conservative for Cyrillic, no tiktoken so the path stays armv7-safe), `input_budget` (context_window × 0.9 −
  reserved_output), and `fit_messages` (trim oldest non-system turns to fit; **always keep system + the final message**;
  raise if the system prompt alone overflows — the QUAL-50 catalog must be scoped upstream, not blindly truncated). Wired
  `fit_messages` into all 3 providers' `chat_completion` (the multi-turn / catalog path; single-shot `enhance_text`
  untouched). `test_llm_budget.py` (5). Suite 981 green, pyright 0, contracts 9/9. Next PR3: structured/JSON output.
- **QUAL-52 PR1 — real per-model LLM token budgets.** New `utils/llm_capabilities.py`: `ModelCapabilities`
  (context_window + max_output) for deepseek / gpt-4o / 4o-mini / 4 / 3.5 / claude-4.x + a conservative fallback;
  `output_budget(model, requested)` caps any request at the model's real `max_output` and defaults to it — replacing the
  arbitrary `max_tokens=150` that truncated replies. Wired into all 3 cloud providers (deepseek/openai/anthropic: default
  None → model max, bound the per-call output). config-master + the provider schemas now carry each model's real max_output
  (8000/16384/8192), not 150. `test_llm_capabilities.py` (5). Inv #4: config-ui builds. Suite 976 green, pyright 0,
  contracts 9/9, configs valid. Next PR2: budget-aware prompting (utf-8 bytes/4 input estimate + trim oversized context).
- **QUAL-50 design confirmed + filed QUAL-52 (LLM component rework) as its prerequisite.** Confidence is **derived**, not
  the LLM's self-rating: intent ∈ donation-set [gate] + fraction of required params that resolve against catalog/context +
  an evidence span the LLM must quote; commands need ALL required params resolved (missing → CLARIFYING; unresolvable →
  abstain), queries are lenient. Grounding 1(b): the prompt carries the live catalog + identity/session/context. Structured
  JSON output. User flagged today's LLM handling as crude + token-budget-blind → **QUAL-52** (real per-model budgets +
  budget-aware prompting + structured output + drop fine-tuning) **first**, then QUAL-50 → QUAL-51 → resume armv7 config.
- **ARCH-24 T4 (armv7 config session) — VAD made mic-conditional + filed QUAL-50/51.** Started the armv7 config session
  (deriving from config-master, the existing profiles being stale). Two findings corrected the plan: (1) **VAD** — the
  unified workflow hardcoded "VAD required for all audio" and raised if `[vad]` disabled; per the user (a MUST + correct),
  VAD is mandatory **only when microphone input is enabled** (mic streams raw ~23 ms chunks needing segmentation;
  web/ESP32 deliver bounded utterances → no server VAD). `voice_assistant.py` init now gates the raise on
  `system.microphone_enabled` and leaves `audio_processor_interface=None` when mic-off; `test_vad_phase3.py` reframed
  (raises only with mic on; no-raise+None when mic off). Suite 971 green. (The runtime no-VAD bounded→ASR path is ESP32
  integration, ARCH-22/23.) (2) **NLU** — spaCy has no armv7 wheel, so on a missed command we want an **LLM *classifier***
  fallback (recovers fuzzy commands), not just the conversation chat fallback (which doesn't execute). Filed **QUAL-50**
  (`LLMNLUProvider` — last NLU-cascade resort; deliberately revises the QUAL-15/16 LLM-free-NLU stance, last-resort only)
  + **QUAL-51** (prompt-tightening session for the classifier + keyword-matcher config). Confirmed the multi-turn
  clarification exists (`conversation.py` `ConversationState.CLARIFYING` + QUAL-37). **The armv7 config now depends on
  QUAL-50** (providers-before-configs), so the config session pauses there.
- **ARCH-24 T5 PR2 — TorchModelCache (T5 COMPLETE).** Extracted the silero v3/v4 copy-pasted model cache (class-level
  dict + `asyncio.Lock` + `_get_or_load_cached_model`) to `utils/torch_model_cache.TorchModelCache` (async, lock-guarded
  `get_or_load`: loads once per key, serializes concurrent first loads). Both silero providers now hold
  `_model_cache = TorchModelCache()` + a small `_load_model_returning` loader; ~25 dup lines × 2 removed. torch whisper
  untouched (library-cached). `test_torch_model_cache.py` (3). Suite 970 green, pyright 0, contracts 9/9, no-TYPE_CHECKING
  clean. **T5 complete → ARCH-24 code threads T1/T2/T3/T5 all done; only T4 (BUILD-3 images + config sessions) remains.**
- **ARCH-24 T5 PR1 — shared InferencePolicy.** Extracted the sherpa thread/CPU budget (was `SherpaInferencePolicy` in the
  ASR provider, a duplicated `_num_threads` in piper, and ignored by silero VAD) to `utils/inference_policy.InferencePolicy`.
  Now shared by sherpa ASR + Piper TTS + silero VAD (which now sets `cfg.num_threads` — sherpa's `VadModelConfig` has it).
  `SherpaInferencePolicy` kept as a back-compat alias; piper's `_num_threads` removed. Decided a full `SherpaSession`
  build-helper isn't worth it — the session APIs (`from_transducer`/`from_whisper`/`OfflineTts`/`VAD`) don't unify; only the
  thread budget is shared. `test_inference_policy.py` (4). Suite 967 green, pyright 0, contracts 9/9 (utils→utils +
  providers→utils legal), no-TYPE_CHECKING clean. Next: PR2 — `TorchModelCache` for silero v3/v4.
- **ARCH-24 T3 PR2 — the armv7 build gate (T3 tooling COMPLETE).** `IreneBuildAnalyzer.validate_architecture(config,
  arch)` reuses the enabled-provider analysis + `get_supported_architectures()` to flag a profile enabling an
  arch-incapable provider; new `--arch` CLI flag exits nonzero on failure. Wired into `backend-health.yml`
  (`build_analyzer --config embedded-armv7 --arch armv7l`) — a torch/onnxruntime provider in the WB7 image now fails CI.
  Verified: embedded-armv7 passes; config-master fails on armv7l (whisper fallback) and passes on x86_64. `test_arch_gate.py`
  (3). Suite 964 green, pyright 0, contracts 9/9, YAML valid. T3 mechanical work done (taxonomy + gate); the
  embedded-armv7→satellite-server profile *content* is the BUILD-3 config session, now guarded by the gate.
- **ARCH-24 T3 PR1 — architecture-support taxonomy.** User chose the explicit-arch-method approach (over markers/hybrid).
  New `EntryPointMetadata.get_supported_architectures()` (default `[x86_64, aarch64, armv7l]`); 8 armv7-incapable providers
  override to `["x86_64","aarch64"]`: silero_v3/v4 + whisper (torch — no armv7 wheel), vosk_tts + piper_ruaccent +
  openwakeword (standalone onnxruntime — no armv7 wheel), microwakeword + microvad (pymicro). The PEP 508 extra markers
  stay as the install-time guard. `test_arch_support.py` (13). Suite 961 green, pyright 0, contracts 9/9,
  dependency_validator 118/118 (additive). Next: PR2 — the `build_analyzer --arch` profile gate + CI step.
- **ARCH-24 T2 PR3 — PiperRuAccentTTSProvider (T2 COMPLETE).** Subclass of `PiperTTSProvider` (entry point
  `piper_ruaccent`) overriding ONLY `_prepare_text` to run RUAccent (Russian stress `+`/ё) before the inherited sherpa
  synth. New `tts-ruaccent` extra (`ruaccent>=1.5.8; platform_machine != 'armv7l'` — 64-bit only; armv7 resolves to
  nothing, like pymicro); deps `["asr-onnx","tts-ruaccent"]`. Full integration (the PR2 lesson): `PiperRuAccentProviderSchema`
  registered + `[tts.providers.piper_ruaccent]` config-master block (8/8 TTS). **User caught** that `RUAccent.load()`
  downloads its NN models from HF and defaults `workdir` to its own (ephemeral, maybe read-only) package dir → pointed it
  at `models_root/ruaccent/` (mounted volume). `test_piper_ruaccent.py` (5; accentizer mocked — no model pull). Gates:
  suite 948 green, schema-unification 19/19, pyright 0, contracts 9/9, no-TYPE_CHECKING clean, dependency_validator
  118/118, config_validator valid, config-ui builds; uv.lock += ruaccent/python-crfsuite. **Open:** the RUAccent `+` ↔
  espeak stress-bridge is an on-device A/B item. T2 done; ARCH-24 remaining: T3 (taxonomy/validator/profile) / T4 (BUILD-3
  packaging) / T5 (shared helpers).
- **ARCH-24: config-master + parameter schema for piper (Inv #2/#4 — gaps from PR2/T1).** User caught that PR2 added the
  `piper` provider without the canonical `config-master.toml` block (it documents every provider — was 6/7 TTS) and that
  T1's `whisper-small` pack wasn't in the sherpa `model` list. The completeness test (`test_parameter_schema_unification`)
  enforces config-master↔schema alignment: adding the `[tts.providers.piper]` block first surfaced it as **orphaned** (no
  registered schema). Fixed properly: new `PiperProviderSchema(TTSProviderSchema)` (voice/speaker_id/speed/num_threads/
  preload_models) registered in `auto_registry`; added the config-master block (now **7/7 TTS** = all entry points) +
  `whisper-small` to the sherpa `model` comment. **Inv #4:** config-ui builds + type-checks clean — it consumes providers
  **dynamically** via the `/config/providers` endpoint (no per-provider typing in `openapi.gen.ts`), so the new provider is
  additive. Gates: suite 943, schema-unification 14/14, pyright 0, contracts 9/9, config_validator valid.
- **ARCH-24 T2 PR2 — PiperTTSProvider (base).** New `providers/tts/piper.py` + entry point `piper`: VITS via sherpa-onnx
  `OfflineTts` (the one armv7 ONNX engine), one provider with the `voice` chosen by config (irina/ruslan/denis/dmitri
  k2-fsa packs → `download_model(extract=True)` → `piper/<voice>/`, resolved recursively since the tarball nests).
  `synthesize_to_file` + native-streaming `synthesize_to_stream`; **numpy-free** PCM conversion (armv7 has no numpy wheel —
  same policy as the sherpa ASR provider); `_prepare_text` hook that PR3's ruaccent subclass overrides. Deps = `asr-onnx`;
  no torch, no system espeak-ng/bz2 (espeak statically linked in sherpa, espeak-ng-data ships in the pack, bz2 in the
  python base). sherpa `OfflineTts*` API verified against the installed wheel. `test_piper_tts.py` (7). Gates: suite 943
  green, pyright 0, contracts 9/9, no-TYPE_CHECKING clean, dependency_validator 58/58, build_analyzer + config_validator
  valid; uv.lock unchanged. Inv #4 N/A (free-form provider config). Next: PR3 ruaccent subclass.
- **ARCH-24 T2 started — PR1: asset-layer `.tar.bz2` support (Piper prerequisite).** Piper TTS voices ship as k2-fsa
  `.tar.bz2` (model.onnx + tokens.txt + `espeak-ng-data/`; both ru voices irina/ruslan verified live at the k2-fsa
  release). `_extract_archive` only dispatched .tar/.tar.gz/.tgz (and `Path.suffix` on `foo.tar.bz2` is `.bz2`), header
  check knew gzip not bzip2 → a Piper voice would fail "Unsupported archive format". Extended dispatch (full-name match +
  bzip2 `BZh`/xz magic; tarfile `r:*` decompresses). New `test_asset_extract.py`. **Env finding:** the custom dev/CI
  CPython (/usr/local 3.11.4) was built **without `bz2`** (like `_sqlite3`) → bz2 tests `skipif`; Docker `python:3.11-slim`
  has libbz2 so real extraction works. Suite 936 green / 9 skipped, pyright 0, contracts 9/9. Next: PR2 PiperTTSProvider.
- **QUAL-49 — silero model-id routing fix.** The ARCH-24 asset-routing analysis (how multi-model providers route models
  to subfolders) found silero v3/v4 were the only providers bypassing the `get_model_path(provider, model_id)` router —
  flat `<dir>/<config:model_file>` with a shared default, so v3 languages could collide on one file. Fixed: route via
  `get_model_path("silero_v{3,4}", model_id)`, model_url from the descriptor, download via the real provider name (drops
  the `"silero"`-fallback + copy hack). `test_silero_routing.py` (4). Inv #4 N/A (free-form provider config). Suite 935
  green, pyright 0, contracts 9/9. Relates to ARCH-24 T5 (done early). _(Also confirmed sherpa already subfolders by
  model_id — `sherpa_onnx/<model_id>/`; the routing lives in the AssetManager, not the provider.)_
- **ARCH-24 formally started — T1 finished (code).** Task-start reconciliation (Inv #8): T1 = case (b) partially
  addressed (the `model_type=whisper` branch + tiny/base packs + their tests already shipped under ARCH-10 PR-2, confirmed
  in `onnx_inference_layer.md`); narrowed to "add the `whisper-small` pack + test" (user-approved "we do the rest of T1").
  Read the backing review doc (Inv #5). Verified `csukuangfj/sherpa-onnx-whisper-small` live on HF (HTTP 200,
  `small-{encoder,decoder}.int8.onnx` + `small-tokens.txt`) before wiring it. Added the `whisper-small` descriptor to
  `sherpa_onnx.py` `_get_default_model_urls()` + `test_whisper_small_pack_for_aarch64`. Suite 931 passed / 0 failed (+1),
  pyright 0, import contracts 9/9; Inv #4 N/A (no contract/schema/config-ui change), Inv #9 N/A (no TYPE_CHECKING). **T1
  code-complete; the on-device verify (RU parity + A53 RTF) stays an open check — gated on WB8 hardware (none on hand).**
- **ARCH-24: T1 found already-implemented; added T5 (shared-runtime helpers).** Code-read of `irene/providers/asr/
  sherpa_onnx.py`: Whisper-via-sherpa is **already done** — the provider branches on `model_type` (`whisper`→`from_whisper`,
  `:128-143`; tiny/base packs declared `:358-372`). It's ONE provider with a `model_type` discriminator (not a separate
  provider, not a base/derived split — the branch surface is ~3 points; decode/audio/asset/policy all shared). So T1
  shrinks to "add a whisper-small pack + verify on aarch64"; T2 (Piper) is the real new provider work. Also analysed the
  "no common inference-engine abstraction" question: it's **mostly inherent + deliberate** (ARCH-9 abstracted assets, not
  sessions; per-library APIs don't unify; ORT bundled in sherpa) with one **narrow intra-runtime gap** → filed **T5**:
  factor a thin `SherpaSession`/`InferencePolicy` helper (sherpa ASR+VAD+TTS; silero VAD currently ignores the thread
  policy) when T2 lands, + optional `TorchModelCache` for silero_v3/v4 (torch `whisper.py` doesn't need it — library-cached).
  Also confirmed the **ESP32 reply channel is already implemented** (`outputs/remote_audio.py` `speak_begin→PCM→speak_end`).
- **ARCH-24/BUILD-3 target matrix finalized — 3 images by architecture, torch in one.** Consolidated a run of decisions:
  (1) Dockerfiles split **by arch** — `Dockerfile.x86_64`→standalone full-voice, NEW `Dockerfile.aarch64`→WB8/Pi satellite,
  `Dockerfile.armv7`→WB7 satellite. (2) Researched **WB8.5 = aarch64** (Allwinner T507 Cortex-A53, 4 GB, Debian 11) →
  Whisper-on-sherpa is feasible there, and **torch aarch64 wheels exist** (verified on PyPI) but torch is **deliberately
  excluded** from aarch64. (3) **Per-target stacks:** standalone = torch (Whisper + Silero v4); both ARM satellites =
  torch-free sherpa (aarch64: Whisper-small + Piper+RUAccent; armv7: vosk-small + Piper-direct). (4) Provider work — T1's
  sole consumer is aarch64; T2 serves both satellites; standalone needs no new providers (supersedes the "64-bit optional"
  framing). (5) **Config strategy** — bake for the two satellites; baked-default + external override (full-dep build) for
  standalone. All recorded in the design doc (new §5 "Deployment matrix" = source of truth) + BUILD-3. No implementation.
- **BUILD-3 reopened as ARCH-24's packaging thread — three Docker images.** Coupled the deferred Docker-build task to
  ARCH-24 now the architecture has settled. Three targets, each = one role + one config + one manual `workflow_dispatch`
  workflow: **A** 64-bit satellite-server (x86_64/aarch64 — WB8.5/Pi, bigger models), **B** armv7 WB7 satellite-server
  (vosk-small + piper-direct; redo the bad `embedded-armv7.toml`), **C** NEW standalone full-`voice` runner (arch TBD →
  Session 4). User refinement: **A & B are the same satellite-server role** (ESP32 owns VAD/VT/audio), differing only by HW
  tier + model allowance. Two profile-parameterized Dockerfiles exist (`Dockerfile.x86_64`, `.armv7`); C's is new.
  Interactive sessions to follow: config per target → Dockerfile design (baked vs mounted) → per-image workflow.
- **ARCH-24 gating check VERIFIED on the real WB7 — sherpa-onnx 1.10.46 does TTS.** The whole "one ONNX engine for both
  ASR + TTS on armv7" plan hung on whether the pinned `sherpa-onnx==1.10.46` armv7 wheel exposes `OfflineTts` (the box's
  glibc 2.31 blocks the newer `sherpa-onnx-core` wheels, so 1.10.46 is the ceiling). Tested directly without touching the
  system Python: downloaded `sherpa_onnx-1.10.46-cp39-cp39-linux_armv7l.whl` (14.5 MB), unzipped, imported via PYTHONPATH —
  the `.so` **loads and runs** on glibc 2.31/Cortex-A7 and exposes `OfflineRecognizer` **and** `OfflineTts` +
  `OfflineTtsVitsModelConfig` (Piper/VITS) + Matcha/Kokoro configs. Cleaned up the throwaway dir. Gate ✅; doc + ledger updated.
- **WB7 controller investigation + SprutHub stopped → ARCH-24 budget reconciled.** Diagnosed the controller's memory:
  the elephant was **SprutHub** (Java hub under `/mnt/data/makesimple`, ~352 MB RSS = 59% of used RAM); Node-RED was a
  red herring (not installed/running). Per the user's plan (bridge + dockerized Irene will run on WB7, SprutHub retired),
  **stopped + disabled both `spruthub.service` and `spruthub-update.service`** (reversible, no files removed) → available
  RAM **364 → 712 MB**. Reconciled the ARCH-24 WB7 budget against reality and **corrected the design doc**: (1) ESP32
  satellites own VAD + voice-trigger + mic/playback → WB7 Irene is ASR/NLU/intent/TTS only (no Silero-VAD, no local audio);
  (2) Irene's `config-ui` not deployed on WB7 (`wb-mqtt-ui` is) — three containers (bridge + wb-mqtt-ui + Irene); (3) disk
  budget is `/mnt/data` (2.3 GB free, docker root there), not the 785 MB rootfs; (4) post-SprutHub 712 MB available. Bridge
  armv7 images already on GHCR (`ghcr.io/droman42/*`, linux/armv7, latest = `8c39b88` 2026-05-31 — 92 commits behind main,
  rebuild needed before deploy). Three-container budget ≈ 430–490 MB disk / 410–570 MB RAM → fits with headroom.
- **ARCH-24 research session — torch-free inference & the armv7 voice stack (no code).** Started from the deferred
  torch/transformers Dependabot alerts (commits 05aa763/4e05a38) + the user's need for a self-contained VAD+ASR+TTS on
  the Wirenboard 7. Mapped the real torch surface (opt-in `advanced-asr` + Silero TTS; `transformers` only transitive via
  the default-off `runorm`), researched replacements (Whisper→sherpa-onnx confirmed; **no torch-free Silero TTS exists or
  can — Silero refuses ONNX export, issue #283 — so Piper is the path**, with RUAccent for Russian stress on 64-bit only),
  and SSH'd the actual WB7 (192.168.110.250) for ground truth: Cortex-A7 quad armv7l, **~367 MB available RAM** + 256 MB
  swap, **784 MB free disk**, glibc 2.31, py3.9 — which bars Whisper *and* vosk_tts on WB7 and pins sherpa at 1.10.46.
  Deliverable `docs/design/torch_free_armv7_voice.md`; filed **ARCH-24** (`[deferred]`, T1 Whisper→sherpa / T2 new Piper
  TTS provider / T3 armv7 platform-taxonomy + validator gate + standalone profile). Also bumped safe Dependabot deps
  (uv.lock + config-ui) — 65→14 open alerts, the 14 remainder all gated behind risky majors → folded into ARCH-24.
- **TEST-7 kicked off — gate lifted, approach locked, Phase A (coverage tooling + baseline) done.** The TEST-7 gate
  (ARCH-1..5 + QUAL-8/10/12/14) is fully `[x]`, so the suite rewrite is unblocked. Locked the approach with the user
  (6 decisions — see the ledger): same contract-level method as the release-plan new code, 100% green, delete stale
  outright, all clusters in one sweep (incl. the new-code wiring gaps), Phases A+B solo then a multi-agent workflow,
  and **pytest-cov + closing the gap is mandatory**. **Phase A:** hit an environment wall — the runtime CPython
  (3.11.4 at /usr/local/bin, shared with wb-mqtt-bridge) is built WITHOUT the stdlib `_sqlite3` extension, which
  `coverage.py` requires. Investigated the sister project (user's steer): it ships `pysqlite3-binary` and aliases
  `sys.modules['sqlite3'] = pysqlite3` via a hand-placed `sitecustomize.py` in site-packages. Mirrored it but made it
  reproducible — committed `sitecustomize.py` (source of truth) + `scripts/install_sqlite_shim.sh` (copies it into the
  venv's site-packages, where the interpreter auto-imports it at startup, before coverage's plugin-load `import
  sqlite3`). A root conftest was tried first and rejected — coverage imports sqlite3 too early for it. Along the way
  the venv had drifted to py3.12 (from a `--python 3.12` probe); restored it to 3.11.4 via the system interpreter,
  pinned `.python-version` (gitignored, local-only) to prevent re-drift, and re-synced `--all-extras` (CI's setup) to
  restore spacy/nlu/audio so the full suite collects. Added `pytest-cov` + `pysqlite3-binary` to the `dev` extra
  (uv.lock +187, additions only — no re-pins). **Baseline measured: 45.6% line coverage (17,546/38,488 across 265
  modules).** The number confirms the thesis — the request hot-path is the cold zone (`workflow_manager` 20%,
  `core/components` 20%, `context` 25%, `nlu_component` 38%, `orchestrator` 41%), new pure-logic is well-covered
  (`trace_context` 76%, `trace_input` 89%), new wiring is thin (`replay_trace`/`voice_runner` 34%). Suite still at its
  baseline (82 failed / 472 passed / 15 skipped — the ±1 is a coverage-perturbed timing benchmark, not a regression).
  Next: Phase B triage + risk-ranked worklist, then the workflow.
- **MQTT design reconciled with the bridge's value-label layer + moved-doc link fixed (both repos).** Validity check
  (no-code analysis, requested): the bridge had ~40 commits since `mqtt_integration.md` was last updated (2026-06-07),
  mostly hygiene — but two touch the contract. (1) The cross-project contract doc **moved**
  (`wb-mqtt-bridge/docs/voice_integration_contract_draft.md` → `docs/design/…`), so the Irene doc's two links were stale.
  (2) A **value-label translation layer** landed (bridge §P3.7 #26, 2026-06-09 — *postdates* both docs' AGREED-2026-06-06
  status): `/system/catalog` now projects controllable enum fields' `values` as **`{wire, canonical, labels}`** triplets
  (`CatalogValueLabel`) instead of bare strings, explicitly for voice — Irene matches the spoken `labels` in-locale and
  posts the `canonical` token; the bridge translates `canonical`↔`wire`. The CORE contract is otherwise intact (canonical
  `POST /devices/{id}/canonical`, `GET /system/catalog`, the `error.code` enum, the `bridge/catalog/version` nudge — all
  unchanged). Reconciliations made: **Irene `mqtt_integration.md`** — fixed both links, added a top reconciliation note,
  and a §5a value-label bullet (device-enum resolution rides the **QUAL-29 surface→canonical** CHOICE mechanism — no new
  mechanism; flagged the bridge's still-"owed-work" param introspection as a best-effort caveat); **ARCH-8 ledger** —
  a catalog-contract-amended pointer; **bridge `voice_integration_contract_draft.md`** (sister repo) — a "Value-labels
  for controllable enum fields" §B subsection + a status-line amendment. The design's foundation was valid throughout;
  it was just *behind* the bridge on enum handling. (Historical journal entries referencing the old contract-doc path
  are frozen and left as-is.)
- **TEST-5 DONE — text-processor / normalizer coverage; ALL TEST- tasks now closed.** The provider
  (`UnifiedTextProcessor`) was already covered (`test_text_processing.py`); added `test_text_normalizers_coverage.py`
  (11 tests) for the actual normalizers (`utils/text_normalizers.py`) + the component's live methods: **NumberNormalizer**
  (ru digit→words via the dependency-free path, no-number passthrough, empty), **PrepareNormalizer** (the pure-Cyrillic
  fast-return / Latin→Cyrillic transcription / inline number processing / changeLatin=skip branches), **RunormNormalizer**
  missing-dependency degradation (patched the `runorm` import to fail → returns input, never downloads the model), and
  `TextProcessorComponent.process` no-provider passthrough + `convert_numbers_to_words` (+ its error degradation).
  Reconciliation (`task-start-reconciliation`): the review's "process() hardcodes the `general` stage / TTS gets no normalization"
  headline was remediated by **QUAL-13** — `process(..., stage="asr_output")` routes by stage now — so tests target the
  current code. `text_normalizers.py` **25%→58%**, `text_processor_component` 29%→30%, overall 53.1%→53.3%. No product
  bugs surfaced. Deliberately not chased: the review-confirmed dead stage routing, the broken text-processing WebAPI
  (QUAL-12 finding), and Runorm's model-download path (offline hazard). **With TEST-5 closed, every TEST- task (0–8) is
  done** — suite green at 930 passed (plain pytest), overall coverage 45.6%→53.3% across TEST-7 Phases + the TEST-3/4/5
  follow-ups.
- **TEST-4 DONE — parameter-extraction coverage (the P1 residual).** Covered TEST-4's named scope: **the 8
  ParameterTypes** via `HybridKeywordMatcherProvider._extract_by_type` — INTEGER/FLOAT/BOOLEAN/CHOICE(fuzzy
  surface→canonical)/DURATION/STRING branches plus the DATETIME/ENTITY fallthrough — and `_convert_and_validate_parameter`
  (the shared `coerce`) + `validate_config` (`test_param_extraction_coverage.py`); and **the 4 entity resolvers**
  Temporal (HH:MM / ru+en duration / relative) and Quantity (number + unit inference) as pure parsers, plus Device/Location
  **graceful-degradation** with no asset loader (`test_entity_resolver_coverage.py`). Reconciliation (`task-start-reconciliation`): the
  `parameter_extraction_review.md` flagged a **P0 fatal-crash** in Device/Location `resolve()` when the asset loader is
  unwired — verified that QUAL-11 P0 #4 **already fixed it** (`_load_device_types` now returns `{}` with a warn-once), so
  the tests assert the degradation rather than a bug to surface. Coverage: `hybrid_keyword_matcher` **0%→19%**,
  `entity_resolver` **62%→79%**, `donations` 87%→89%; overall 52.6%→53.1%. 18 tests; no product bugs surfaced; suite
  green (918 passed under cov / 0 failed). The donation-driven `recognize()` pipeline (the bulk of hybrid's 675 stmts)
  and the dead-code-heavy `spacy_provider` (21%) are out of scope — integration-level / review-confirmed dead.
- **TEST-3 DONE — fire-and-forget lifecycle coverage.** The action store (`ClientRegistry`, 76%) + the happy
  launch→complete path were already covered by `test_action_store.py`; the gap was the `IntentHandler` F&F machinery
  (`handlers/base.py` 45%). Added `test_fire_and_forget_coverage.py` (11 hermetic tests — minimal concrete handler via
  `object.__new__`, a fresh `ClientRegistry` patched into `get_client_registry`, `asyncio.run`) covering the
  previously-untested branches: launch registers in the store; completion reaps + records success; **error** → failure
  history (`error`/`failed_actions`); **cancel** → recorded "cancelled"; **launch-failure** (store raises) → failed
  metadata with `failed_at_startup`; the positive-timeout monitor is registered then popped+cancelled on completion;
  `cleanup_timeout_tasks` cancels+clears; metrics `record_action_start`/`record_action_completion`; notification
  scheduled only when the action is session-owned; and the handler-level `cancel_action` (true/false) + `get_active_actions`.
  Reconciliation (`task-start-reconciliation`): the `fire_and_forget_review.md` findings describe the PRE-remediation broken lifecycle —
  QUAL-9/QUAL-28 rebuilt it on the physical-identity-scoped store, so tests target the current working code, not the old
  bugs. `handlers/base.py` 45%→52%; overall 52.3%→52.6%; no product bugs surfaced. Suite green at **901 passed** (plain
  pytest). _Note: one pre-existing timing test (`test_zero_overhead_when_disabled`) is flaky under `--cov` (coverage
  instrumentation breaks its "zero overhead" assertion) — not a CI concern (the gate is plain pytest), flagged for a
  possible skip-under-coverage follow-up._
- **CI Tests gate red on a second real bug (PortAudio/OSError) — surfaced + fixed (user-approved).** With pyright
  green, the newly-enabled Tests gate ran and failed on the GitHub runner (Python 3.11.15) — 3 `test_voice_runner_coverage`
  tests raised `OSError: PortAudio library not found`. Root cause = a **real robustness bug in QUAL-46's voice_runner**:
  `check_voice_dependencies()` / `_check_dependencies()` catch only `ImportError`, but `import sounddevice` raises
  **`OSError`** when the package is installed without the PortAudio native lib (exactly a headless CI box / a server
  deployment) — so the dependency *probe crashes* instead of reporting "unavailable". Surfaced with options per the
  standing rule; user chose **fix the code** → broadened both probes to `except (ImportError, OSError)` (degrade, never
  crash). Also made the Phase-D tests **hermetic** (they had asserted the real environment had working sounddevice):
  added `_with_sounddevice()` (stub → present) and `_sounddevice_raises(exc)` (models the OSError), and added two tests
  asserting the graceful degradation — so the fix is locked in and the suite no longer depends on a system audio lib.
  Full suite 890 passed; pyright 0; no other test touches PortAudio.
- **CI red since ARCH-19 slice 5 — fixed (pyright); avoiding `cast` surfaced a real bug in my own tool.** CI had
  failed every run since `ARCH-19 slice 5` (the replay tool) — **5 pyright errors in `irene/tools/replay_trace.py`**
  (I'd checked import-linter + tests but never run pyright there). The Tests step never ran (gated behind pyright), so
  the green local suite was masked. Fixes: typed `self.core: Optional[AsyncVACore]` + `assert ... is not None` narrowing
  (real runtime checks, not band-aids); narrowed `TraceInput.listen() -> AsyncIterator[AudioData]` at the source (legal
  covariant override) instead of a call-site `cast`; and for the audio component used `isinstance(audio, AudioComponent)`
  narrowing instead of `cast(Any, audio)`. The user pushed back ("isn't cast a dirty trick?") — correct: `cast(Any)` is
  a typed `# type: ignore`, and here it was **hiding a genuine bug** — `_listen` passed an async generator to
  `AudioComponent.play_stream`, which takes raw **bytes** (it buffers→streams internally), so `--listen` would have
  silently failed (swallowed by its try/except). Fixed `_listen` to pass the decoded bytes, and updated the 2 Phase-D
  coverage tests that had pinned the buggy contract (fake `SimpleNamespace` audio + async-gen) to a real `AudioComponent`
  receiving bytes. Verified: pyright 0 errors, all other CI gates pass locally (no-TYPE_CHECKING / config profiles /
  config files / dependency resolution), full suite 888 passed, 9/9 import contracts. Audited `cast` across all product
  code (user request): **12 usages, 0 dirty** — all cast an under-typed *third-party* return (sounddevice/pyttsx
  `query_devices`/`getProperty`, the OpenAI SDK `ChatCompletionMessageParam`) to its known concrete shape, so the call
  stays checked; one `cast(object, …)`→`isinstance` is exemplary. **No `cast(Any, …)` anywhere** — the only one was
  mine, now gone. _Lesson: run pyright locally on new code (not just import-linter + tests); the honest line is
  `cast(ConcreteType, untyped_external_value)` ✅ vs `cast(Any, our_value)` ❌ — the latter is a typed `# type: ignore`
  that disables checking and conceals bugs (it hid this one)._
- **TEST-7 DONE + folded-in TEST tasks reconciled + full-suite pytest is now a CI gate.** Marked **TEST-7 `[x]`**
  (suite rewritten + 100% green, coverage 45.6→52.3%; the `workflow_manager`/`context` deep-pipeline residual accepted
  as integration/smoke-level, user-approved). Reconciled the tasks "folded into TEST-7" honestly against measured
  coverage — closed the genuinely-complete ones, kept the rest open with the specific residual: **DONE** → **TEST-2**
  (the paused suite-stabilization, subsumed — its `56→82 failed` drift is now `0`), **TEST-8** (all 5 capability
  handlers covered through their ports + graceful-degradation: text_enhancement 99% / speech_recognition 97% /
  translation 97% / audio_playback 80% / voice_synthesis 65% — the QUAL-24 repair is finally verified), **TEST-6**
  (ASR fallback + resampling restored — `test_phase7_performance` rewritten to `resample_audio_data`, `audio_processor`
  71%, `asr_component` fallback covered). **STILL OPEN (honest residual)** → **TEST-4** P1 (recognition cascade covered
  but the extraction internals are not — `hybrid_keyword_matcher` at **0%**, the 8 ParameterTypes / 4 resolvers
  unexercised), **TEST-3** (F&F *launch* covered, *lifecycle* completion/cleanup not), **TEST-5** (text-processor not
  targeted, 29%). **CI:** the full pytest suite was explicitly deferred in `backend-health.yml` ("becomes a hard gate
  once … TEST-7"); that precondition is met, so enabled it — `uv run python -m pytest irene/tests/` is now a hard gate
  alongside the existing import-linter / no-TYPE_CHECKING / pyright / config-validation / dependency gates. (Plain
  pytest needs no sqlite shim — that's only for `--cov`.) Suite verified green (888 passed / 0 failed); 9/9 contracts.
- **TEST-7 Phase D — coverage fill 45.6% → 52.3% (13-agent workflow; recovered from a mid-run crash).** Fanned out
  one agent per Tier-1 target — the cold spine (`workflow_manager`, `core/components`, `nlu_component`, `context`,
  `voice_assistant`, `asr_component`), the 5 capability-port handlers (TEST-8), and the new-code wiring
  (`replay_trace`, `voice_runner`) — each writing a new `test_<module>_coverage.py` of characterization tests at the
  seam, instructed to be hermetic (`asyncio.run`, no global-state pollution — the Phase-C lesson) and to SURFACE (never
  fix) any product bug. The main loop crashed before the workflow's verifier ran, so its result/findings were lost, but
  all 13 files were written to the tree. Recovered by hand: confirmed all 13 collect + are substantial + genuine
  (spot-checked `context` = eviction/dual-clock/room-injection, `workflow_manager` = trace helpers/event publishing,
  `nlu` = language detection — real behavior, not coverage-padding). The new tests EXPOSED one more latent
  `asyncio.get_event_loop().run_until_complete` anti-pattern (in the pre-existing `test_clarification.py` — passed
  alone, failed in-suite once an `asyncio.run` test closed the loop first); fixed it → `asyncio.run`, same class as the
  Phase-C `no_intent_clarification` fix. **Result: 888 passed / 0 failed / 7 skipped; overall coverage 52.3%
  (+6.7).** Standout gains on the new-code wiring (`voice_runner` 34→85%, `replay_trace` 34→82%) and spine
  (`core/components` 20→56%, `nlu_component` 38→59%, `voice_assistant` 48→72%, `asr_component` 25→46%); residual-cold
  are `workflow_manager` (29%) + `context` (31%) whose deep pipeline paths need a booted core (smoke territory).
  **No product bugs surfaced** (transcripts show no findings; no bug-skips in the files). 9/9 import contracts; no
  product code touched. _Lesson banked: the per-agent isolation check missed the order-dependency; the full-suite
  green run (and a workflow-level full-suite gate) is what catches it — and the crash cost us the verifier that would
  have._
- **TEST-7 Phase C — suite to 100% green (82 → 0 failed).** Ran a 19-agent workflow + verifier per the locked plan
  (delete stale / rewrite drifted to current contracts / SURFACE-never-fix product code). Deleted 4 stale pre-refactor
  files (phase4 ×3 + phase6, built on the removed `ContextualCommandPerformanceManager`) and rewrote 13 drifted
  clusters to current port/public contracts (NLU `_recognition_provider` cascade, `Intent` signature, VAD metrics
  dict-vs-object + `energy_threshold` relocation, spaCy MagicMock, the ARCH-19 `record_stage` trace contract, …);
  net −3,555 test lines; spot-checked two rewrites as genuine (assert real behavior incl. off-paths), not gamed.
  Fixed an order-dependent failure myself: `test_no_intent_clarification` used `asyncio.get_event_loop().run_until_complete`
  (passed alone, failed in-suite once another async test closed the loop) → `asyncio.run`. That left **3 reds = 2
  fix-code questions**, surfaced to the user with options per the standing rule (never fix product code autonomously);
  the user chose test/config fixes for both: (a) `device_id` is the live `MicrophoneInputConfig` field name (the
  planned `→device` alignment was never implemented) — removed it from the alignment test's deprecated list and cleaned
  the machine-specific `device_id = 7` to the `None` default in `config-master.toml` (`config-master-canonical`); (b) `llm.console`
  is a *registered* offline-floor stub with no runtime params by design (entry-point at pyproject:262) — exempted
  declared stubs in `test_parameter_schema_unification` (mirroring the existing text-processor carve-out) and rewrote
  the stale `test_flags_phantom_llm_console` (console is no longer unregistered; switched to a genuinely-unregistered
  name so phantom-detection stays covered). **Suite now 558 passed / 0 failed / 7 skipped; 9/9 import contracts;
  config-master loads.** No product code changed in the whole phase. Next: Phase D (risk-ranked coverage fill).
- **TEST-7 Phase B — triage worklist + risk-ranked coverage (`docs/review/test7_triage.md`).** Captured one-line
  tracebacks for all 82 failures and clustered them by root-cause signature → verdicts: **~28 delete, ~50 rewrite,
  3 fix-code.** Deletes are the pre-refactor "phase" scaffolding (the 21-strong phase4 contextual cluster — all 16
  `'NoneType' has no attribute 'active_actions'` failures live there — built on the deleted `ContextualCommandPerformanceManager`;
  phase1/6 integration; the unbuilt-ARCH-8 device/location-resolution cases; a removed text-processor module). Rewrites
  are drift-to-current-contract (NLU `entities['provider']`→recognition-provider, `Intent(session_id=…)` signature,
  VAD metrics dict-vs-object + `energy_threshold` moved under `[vad.providers.energy]`, spaCy mock-vs-MagicMock,
  ARCH-19 trace-internal drift in `component_trace_integration`). Verdict-driving rule applied throughout: does the
  behavior still exist? Surfaced **3 fix-code suspects** (the TEST-1/2-style real-bug finds): `config-master.toml`
  hardcodes a machine-specific `device_id = 7` in the canonical reference (`config-master-canonical`); the `llm.console` stub has an
  empty parameter schema; and a VAD-requirement error message that touches the QUAL-46 path. Also produced the
  risk-ranked coverage table (gap × churn × hot-path × defect-history): Tier-1 = `workflow_manager` (20%/15 commits),
  `core/components` (20%), `nlu_component` (38%/603 stmts/16 commits), `context` (25%), `voice_assistant` (48%/most-churned),
  `asr_component` (25%), and the 5 capability-port handlers (TEST-8, unverified after QUAL-24). This worklist is the
  input to the Phase C/D multi-agent workflow.
- **QUAL-47 (final sweep item) — retired the dead `test_vad_sibilant_fix.py` debug script + its orphaned config.**
  Verified-then-deleted: `tools/test_vad_sibilant_fix.py` was **already broken** — it imported
  `UniversalAudioProcessor` from `workflows.audio_processor`, a class renamed to `VoiceSegmenter` in the ARCH-18
  refactor, so the script raised `ImportError` on load and could not run. Not an entry point, not imported by any
  code or test; its only references were itself and one archive doc (`docs/archive/VAD_SIBILANT_FIX.md`, left as
  record). Removed it plus its sole companion **`configs/vad-sibilant-fix.toml`** (a one-off test config referenced
  by nothing else). No live references remain. The `tools/` dir now holds only active tooling
  (`generate_schemas.py`).
- **QUAL-48 — removed the v13→v14 runtime config-migration path (decision: remove).** The last v13/v14 relic after the
  QUAL-47 sweep. `irene/config/migration.py` (637 lines — `V13ToV14Migrator`, `migrate_config`,
  `ConfigurationCompatibilityChecker`, `create_migration_backup`) was *live* but guarded: `config/manager.py:_dict_to_config`
  called `ConfigurationCompatibilityChecker.requires_migration(data)` and only auto-migrated a **v13-format** config —
  impossible to hit on v15.0.0. Reconciled the full surface first (`task-start-reconciliation`): only two importers (`config/__init__.py`
  re-exports + `manager.py`), no tests, no other code. Deleted the module; removed the import + the migration guard in
  `_dict_to_config` (the normal path — env-var resolve → `CoreConfig.model_validate` — is untouched); removed the import
  block + the 5 `__all__` entries from `config/__init__.py`. Net effect: a v13 config now fails at pydantic validation
  with a plain error rather than silently transforming — the right behaviour on v15, where v13 is unsupported. Verified:
  config-master/minimal/api-only all load clean, the `irene.config` re-exports still resolve, no lingering reference to
  any migration symbol, 9/9 import contracts, and the config/manager test suites are net-zero (7 pre-existing TEST-2
  failures, identical with the change stashed — nothing depended on auto-migration). `config-ui-stays-functional` N/A. _Irene no longer
  carries any v13/v14 migration code or tooling._
- **QUAL-47 (extended) — swept for stale migrators, retired two more; surfaced one live-code finding (QUAL-48).**
  Broadened the verify-then-delete sweep across `tools/`, `irene/tools/`, `scripts/`. Retired two more standalone
  migrators (neither an entry point, neither imported by any code or test): **`tools/migrate_to_universal_plugins.py`**
  (migrates configs to the long-done "Universal Plugin + Provider" refactor — only references were two `docs/archive/*`
  guides, left as record) and **`scripts/migrate_donations_v11.py`** (the QUAL-29 donation v1.0→v1.1 migration — verified
  spent: QUAL-29 is `[x]` and the assets are already in the v1.1 layout, 13 `contract.json` + per-lang phrasing files).
  Both deleted; no code/config references remain; package imports clean. The sweep also surfaced
  **`irene/config/migration.py`** — v13→v14 migration utilities that are **NOT a tool**: they're live runtime code
  imported by `config/__init__.py` + `config/manager.py` and invoked in `_dict_to_config` (guarded by
  `ConfigurationCompatibilityChecker.requires_migration`, so it only fires for a v13-format config — never on v15). Per
  the verify-before-delete discipline (it's wired into config loading, I didn't author it), I did **not** touch it —
  filed it as **QUAL-48** `[deferred]` to decide keep-as-safety-net vs remove-as-code-change. Other tool files reviewed
  and kept (active): `generate_schemas.py`, `dump_openapi.py`, `check_scope.py`, `build_analyzer`, `config_validator_cli`,
  `dependency_validator`, `replay_trace`, `batch_cross_language_validation.py`. (`tools/test_vad_sibilant_fix.py` is a
  one-off VAD debug script — left for now, not a migrator.)
- **QUAL-47 — retired obsolete v13/v14 migration tools (QUAL-46 follow-up).** Verified-then-deleted, per the
  before-deleting discipline: confirmed the project is on **15.0.0**, both tools target long-past versions, and
  neither is imported by any runtime code or test. **`irene/tools/config_migrator.py`** (a v13→v14 config-file
  migrator) — removed the file and its `irene-config-migrate` `[project.scripts]` entry; not reused by
  `config_validator_cli` or anything else. **`tools/migrate_runners.py`** (legacy `runva_*.py` → v13 runner mapper)
  — removed; it was already **broken by QUAL-46** because it referenced `irene.runners.vosk_runner`/`VoskRunner`/
  `run_vosk`, which no longer exist. Only references anywhere were two `docs/archive/*` historical notes, left as
  record. Package re-syncs (entry points valid), the deleted modules import-fail as expected, no lingering code/config
  references, 9/9 import contracts. One sibling migrator remains (`tools/migrate_to_universal_plugins.py`, also
  pre-v15) — noted, not in scope.
- **QUAL-46 — vosk runner generalized into a config-driven voice runner.** Analysis (no-code, requested) found the
  `VoskRunner` was already a full end-to-end microphone pipeline (mic → VAD → [wake word, if configured] → ASR → text
  → NLU → intent → spoken reply, + deferred F&F speech), but **artificially coupled to vosk** by exactly two gates: an
  `import vosk` dependency probe (failed startup without the package) and a config-validation rule that errored unless
  `asr.default_provider == "vosk"`. The processing path itself never touched vosk — it delegates to the generic ASR
  component — so the coupling was vestigial. **Removed both gates:** the runner now declares only `sounddevice` as its
  hard dep (microphone capture) and validates *any* configured + enabled ASR provider; the chosen provider's own deps
  are the component system's job (`irene-dependency-validate`). **Renamed** throughout — `vosk_runner.py`→`voice_runner.py`
  (via `git mv`, history preserved), `VoskRunner`→`VoiceRunner`, `run_vosk`→`run_voice`, and the entry points
  `irene-vosk`→`irene-voice` (both the `[project.scripts]` and `[project.entry-points."irene.runners"]` registrations)
  plus the `runners/__init__` exports — a clean rename with no back-compat alias (pre-release). **Fixed a latent VAD
  inconsistency** spotted in the analysis: the streaming mic path *requires* VAD (the workflow raises if it's off), yet
  the runner force-enabled asr/audio/intent/text_processor/nlu but not vad — so a VAD-off config failed deep in workflow
  init with an opaque error. The runner now also forces `vad.enabled=True` (consistent with the other components);
  `voice_trigger` stays purely config-driven (the runner already auto-skips the wake word when it's absent). Docs: added
  a "Voice (microphone)" run-mode section to `QUICKSTART.md` (config-driven ASR, the `python -m` and installed-script
  forms, `--list-devices`/`--check-deps`/`--trace`) — this also closes the earlier doc-gap where the runner was
  undocumented. New `test_voice_runner.py` (8 tests: provider-agnostic validation across vosk/whisper/sherpa_onnx/
  google_cloud + the force-rules incl. VAD). 9/9 import contracts kept; runner/vad suites net-zero (4 pre-existing
  TEST-2 failures, verified by stash); no test imported the old module (only a same-named scenario function). Invariant
  #4 N/A. Left untouched: the v13-era `tools/migrate_runners.py` (maps the old runner name as a v13→v14 migration target;
  obsolete, flagged for retirement alongside `config_migrator`).

