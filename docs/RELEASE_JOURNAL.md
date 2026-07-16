# Irene — Release Journal
> Older sections: docs/archive/journal/2026-07-04_2026-07-06.md

The single **active** chronological log for the release effort ("what happened, when, and why"). Append-only;
newest entries near the top of each dated section.

- **This file holds NO task status and NO scope.** The authoritative task ledger (scope + status) is
  [`RELEASE_PLAN.md`](./RELEASE_PLAN.md); findings/rationale live in `docs/review/*` + `docs/design/*`.
- Entries reference task IDs (e.g. `QUAL-27`) but never assert their status — check the ledger for that.
- **Older entries are frozen in archives** (`one-active-journal`), newest first:
  [`docs/archive/journal/2026-07-04_2026-07-06.md`](archive/journal/2026-07-04_2026-07-06.md)
  (2026-07-04 … 2026-07-06),
  [`docs/archive/journal/2026-06-23_to_2026-07-02.md`](archive/journal/2026-06-23_to_2026-07-02.md)
  (2026-06-23 … 2026-07-02),
  [`docs/archive/journal/2026-06-15_to_2026-06-22.md`](archive/journal/2026-06-15_to_2026-06-22.md)
  (2026-06-15 … 2026-06-22), [`docs/archive/journal/pre-2026-06-15.md`](archive/journal/pre-2026-06-15.md)
  (2026-05-31 … 2026-06-14). This file keeps **2026-07-07 onward**; grep an archive when reconciliation needs older history.

---

## Action journal

- **2026-07-16 — BUG-43 DONE: EN whisper finally hears English.** Same-day close of the guard's
  sharpest first-run catch. Verified before fixing: the main voice pipeline passes no language to
  ASR, so the component's `default_language` really was the decode hint — and it was pinned to "ru"
  on the EN images, because the `[asr] default_language = "en"` those profiles set was never a
  declared field and got silently dropped at parse. The fix is the QUAL-36 pattern: ASR now takes
  its language default from the ONE canonical `CoreConfig.default_language` at initialize, the
  per-section reads and their "ru" literals are gone, the stale TOML lines are dropped, and the
  guard's allowlist is empty again. Regression test locks the wiring for both languages. Suite 1426
  green. Note for the next EN image deploy: English recognition quality should visibly improve —
  whisper had been decoding English speech with a Russian hint since the EN profiles were born.

- **2026-07-16 — TEST-22 DONE: the coherence guard is live — and its first run caught six more lies.**
  The closing leg of the ARCH-50 remediation. `test_coherence_guard.py` asserts the three directions
  no gate covered: the namespace registry mirrors pyproject (with a no-stray-literals sweep — 29
  restatements across 11 files got replaced with registry imports on the spot), every declared config
  field has a runtime reader (allowlist: exactly the three dynamically-read `*_config` fields, each
  with its reason), and no live TOML carries a key the models don't declare — the reverse direction
  that silent extra-ignoring had left unguarded forever. The first run earned its keep immediately:
  stray keys my own QUAL-83 strip missed, dead workflow sub-tables, the analyzer's unreachable
  boolean-handler "Method 2", and two genuine discoveries — the handler-config sections in ALL seven
  full profiles were misplaced (`[intent_system.handlers.conversation]` instead of
  `[intent_system.conversation]`), silently dropped since inception and saved only by the values
  repeating the model defaults; and `[asr] default_language` was never a declared field at all, so
  the EN profiles' whisper decode hint has been "ru" — filed as BUG-43 (fix wires the canonical
  QUAL-36 language policy). Guard 14/14, suite 1425 green, analyzer parity verified, all profiles
  valid. **The ARCH-50 remediation is complete: all eight [release] tasks landed in two unattended
  batches, seven commits, every gate green.** QUAL-84/85 remain [deferred] by design.

- **2026-07-16 — ARCH-55 DONE: what the config says is what loads — resilience is declared, not
  conjured.** The behavioral leg. Six components stopped second-guessing the operator: tts and audio
  no longer force console into the enabled set, silently conjure it when everything else dies, or
  seed their defaults with it; voice_trigger no longer materializes an openwakeword engine with a
  literal `hey_jarvis` wake word (zero usable engines is now a loud inactive state — and wake engines
  formally have no fallback chain, they're alternatives); asr/llm lost their `"vosk"`/`"openai"` seed
  literals; the LLM degrade chain is exactly config's `fallback_providers` (the deployment TOMLs
  already declared console there, so production behavior is unchanged — the difference is that an
  operator can now actually turn the floor OFF). VAD got the ruling's mechanism in full:
  `fallback_providers` on `VADConfig`, walked on load-or-init failure, fatal when exhausted — and the
  standalone profiles declare `["energy"]` explicitly, which converts yesterday's ARCH-54 discovery
  (silero silently degrading to energy for lack of baked deps) from an invisible substitution into
  visible, chosen config. Three tests that asserted the old implicit fallbacks now assert the new
  contract. Suite 1411 green, all profiles valid, armv7 gate green, config-ui green.

- **2026-07-16 — ARCH-56 DONE: the inputs entry-point group is real now; the runners group is gone.**
  The `locveil_voice.inputs` group had been registered since inception and read by nothing —
  InputManager hardcoded three imports and three if-branches. It now discovers adapters from the
  group generically: the `[inputs]` flag matching the entry-point name enables, the
  `[inputs.<name>_config]` model configures (the microphone adapter learned its config model's field
  names on the way), and mic-style post-setup is structural via `initialize()`. A third-party input
  is now a pyproject entry point plus a config flag, no manager edit. The `runners` group went the
  other way — deleted outright, since runners launch via `python -m` and nothing ever discovered
  them; the canonical registry re-asserts ≡ pyproject's 12 remaining groups. Parity smoke: same
  source sets as the old wiring, CLI auto-start intact. Suite 1411 green, contracts 11/11, lockfile
  clean.

- **2026-07-16 — ARCH-53 DONE: handlers declare their own component ports.** First leg of the second
  unattended batch (53 → 56 → 55 → TEST-22). The QUAL-24 central wiring table in intent_component —
  six handler names mapped to injected component attributes, plus a by-name special case for
  provider_control — is gone. Each handler now declares `{attribute: component}` via a
  `get_capability_ports()` classmethod (the same self-description pattern as
  `requires_configuration()`), the injection loop is generic, and the registry special-case is
  structural (any handler declaring `set_component_registry()` gets it — provider_control is the only
  one, verified). A runtime assertion confirmed the declared ports across all 15 entry-point handlers
  reproduce the retired table exactly. Adding a handler with component needs no longer touches
  intent_component. Suite 1411 green, contracts 11/11.

- **2026-07-16 — ARCH-54 DONE: one enablement authority — and the analyzer had three latent bugs under
  the old one.** Final leg of the four-task sweep. The per-section `enabled` flags are deleted from all
  ten component configs and the silent parse-time force-sync with them; `[components]` is now the only
  place a component turns on, for the runtime AND the build analyzer alike. Rewiring the analyzer to
  that authority surfaced how much the dual-flag world had been hiding: its intent-handler analysis had
  never executed once (the gate read a `[intents]` section no TOML ever had), VAD provider dependencies
  never reached any image (the 8-name hand-list skipped `vad` — the standalone image has been silently
  falling back to energy VAD because silero's onnx deps were never baked), and every profile's
  validation was reporting phantom "provider not found" errors. All three are fixed; all six profiles
  now analyze valid, the armv7 torch-free gate stays green (after correcting
  `NLUAnalysisComponent`'s falsely-required `nlu-spacy` — spacy is optional there, as the running WB7
  deployment proves). Also caught mid-leg: yesterday's ComponentLoader deletion had left one caller
  alive inside `validate_entry_point_consistency`, masked by its own broad except — now it discovers via
  the loader directly with no hand-list. Three guides' TOML examples updated to show `[components]`.
  Suite 1411 green, contracts 11/11, config-ui check+build green. The unattended batch (ARCH-57 →
  ARCH-52 → QUAL-83 → ARCH-54) is complete: four commits, each gate-verified.

- **2026-07-16 — QUAL-83 DONE: ~30 fictional config fields and four dead code units, gone.** Third leg of
  the sweep, and the widest diff: every field ARCH-50 catalogued as declared-but-never-read is deleted
  from the models, the TOML template, all live TOMLs, and the config-ui contract — the AssetConfig
  download/cache block (none of whose eleven knobs ever throttled, verified, or retried a download), two
  whole handler-config models whose handlers never took config, the MemoryManager leftovers, and the
  scattered singles. The NLU-analysis capabilities endpoint now reports the canonical top-level language
  policy instead of a hardcoded `["ru","en"]` (QUAL-36). Dead code out: `get_provider_capabilities` (the
  PROD-8 delegation, discharged), `EnhancedHandlerManager` (with it dies the third, file-scan-based
  handler-discovery mechanism), `ComponentLoader`/`ComponentRegistry`, and the manager's caller-less
  `add_handler`/`remove_handler` + legacy name-derived patterns — a handler reaching registration without
  a donation now raises instead of guessing. The four orphan TOMLs are deleted and `full.toml` with them
  (its one test consumer repointed to a live profile). One over-strip — profile lines for a still-live
  resample field — was caught by the master-completeness gate and restored: the gate earning its keep
  mid-sweep. En route, a NEW instance of the ARCH-50 pattern surfaced and is filed as QUAL-85:
  `config/schemas.py` is a whole parallel hand-maintained schema tree still declaring fields this sweep
  deleted, and the ASR/VT resampling fields' only reader is itself caller-less. Suite 1411 green,
  contracts 11/11, config-ui check+build green.

- **2026-07-16 — ARCH-52 DONE: the seed finding is dead — intent-handler loading tells no more lies.**
  Second leg of the remediation sweep. The two config fields the BUILD-36 bounce exposed as pure fiction
  (`auto_discover`/`discovery_paths` — declared, plumbed, documented, skip-listed, never read) are
  deleted everywhere: model, both intent_component plumbing sites, analyzer skip-set, all 8 TOMLs, and
  the config-ui contract (openapi re-dumped, types regenerated, check+build green). The handler
  namespace is one constant now, shared by the manager, the config validator, and the contract
  validator. The cwd-relative `Path("assets")` family — the QUAL-59 bug class that survived in three
  more places — is replaced by one self-validating resolver (env root → cwd → package-relative, each
  gated on `donations/` actually being there), proven from a foreign cwd. And the hardcoded fallback
  domain-priorities dict is gone: broken priorities now fail the boot loudly instead of silently
  running with made-up numbers. Suite 1417 green, contracts 11/11.

- **2026-07-16 — ARCH-57 DONE: one namespace registry, and the VAD dropdown lives.** First of the
  ARCH-50 remediation sweep (owner-ordered batch: 57 → 52 → QUAL-83 → 54, unattended). The five
  independently-drifting component→namespace maps now all derive from `utils/namespaces.py`, whose
  `ALL_NAMESPACES` is asserted identical to pyproject's 13 entry-point groups. Two silent omissions of
  `vad` die with it: startup validation now checks `[vad]` name-ref fields, and `/config/providers/vad`
  resolves — the config-ui VAD provider dropdown had been rendering empty off a 404 the widget swallowed
  as a console warning. The build analyzer's fallback list loses the phantom `locveil_voice.outputs`
  group, and its component module paths now come from entry-point values instead of a naming convention
  that minted the nonexistent `intent_system_component` module — baseline diff across all 6 Docker
  profiles shows exactly that one correction and nothing else. En route, a fresh latent finding for the
  ARCH-54 leg: the analyzer's intent-handler analysis has never run — its gate reads `[intents]` while
  every TOML says `[intent_system]`. Suite 1417 green, contracts 11/11.

- **2026-07-16 — ARCH-50 DONE: the dynamic-loading sweep — the config was lying in ~40 places.** The
  review the BUILD-36 rename bounce demanded: everywhere the entry-points-or-config contract promises
  dynamism, is the code actually listening? Mostly no. The seed generalized into seven finding classes
  (`docs/review/dynamic_loading_hardcodings_review.md`): ~30 declared-but-never-read config fields (the
  whole `AssetConfig` download/cache block among them — downloads were never verified, retried, or
  throttled by any of those knobs); a silent parse-time force-sync making `[components]` overwrite each
  section's `enabled` while the build analyzer reads the raw overwritten value (image and runtime can
  disagree about what's enabled); provider names (`console`, `openwakeword`, `hey_jarvis`, `vosk`,
  `openai`, `energy`) force-added or pinned in six components past what config says; five hand-maintained
  component→namespace maps drifting independently — two forgot `vad`, and one of those backs the
  config-ui provider dropdown, so the VAD provider selector has been silently rendering EMPTY (live bug);
  two decorative entry-point groups nothing reads (`inputs` — InputManager hardcodes its three classes —
  and `runners`) plus a phantom `outputs` group and a phantom module path in the analyzer; four dead code
  units including the PROD-8-delegated `get_provider_capabilities`. Verdicts came out of a three-round
  interactive session under one governing ruling — **no config overrides: honor or delete**. The
  intent-handler path itself proved healthy at the core (entry-points discovery, config-filtered,
  donation-registered) with the conversation handler's context special-casing sanctioned as the one
  exception. Remediation filed: ARCH-52..57 + QUAL-83 + TEST-22 (a full code↔config↔entry-points
  coherence guard) all `[release]`; QUAL-84 `[deferred]`. ARCH-42 (core-py loader extraction) is now
  unblocked — its council-locked predecessor delivered the inventory it needs.

- **2026-07-15 — BUILD-40: scope-guard re-pinned `scope-v5`→`scope-v6` (commons HK-10 / IMPL-2).** The
  new version (1.3.0) adds the UNREFERENCED-evidence check — the "fourth direction" of evidence-doc
  discipline: a file on disk under `docs/review`/`docs/design` that no ledger entry (active or DONE)
  references by path or basename is forgotten scope, flagged at `warn`. Re-vendored the file verbatim
  from commons `scope-v6:packages/scope-guard/scope_guard.py`; added the explicit `unreferenced = "warn"`
  toggle to `[evidence]` (matching how `unindexed` is spelled out, though the commons default already
  warns) and re-stamped the config header. Simulated the rule at intake before pinning — the voice tree
  has zero unreferenced review/design docs, so the pin lands green (1.3.0 EXIT 0). Housekeeping caught in
  the same change: the `ledger-guard` CI step's name still said "vendored at scope-v3", stale since the
  v4/v5 re-pins → corrected to `scope-v6`. No `[claude]` re-hash — v6 changes only the guard code and
  evidence defaults, not any pinned CLAUDE.md block.
- **2026-07-15 — UI-23 done: voice fetches reach the controller, not the shell.** Commons IMPL-6
  answered the owner's first-controller-run question — how do plugins learn the WB7's IP and port —
  with `PageProps.backends` (deployment facts in the owner-edited shell config, never in build
  artifacts). Voice consumed it the same hour: the page wrapper re-points the api singleton at
  `backends.api` synchronously during render — deliberately not an effect, because React fires child
  effects first and the pages' mount-time loads would have raced ahead against the shell origin. The
  retired-nginx-era fallback chain stays for shells with no backends configured, its comments now
  honest about being a fallback. One recorded wrinkle: the shell polls status() outside any page, so
  the very first poll can use the fallback before a page mounts — a contract gap to raise if it ever
  bites in practice.

- **2026-07-15 — op: RU armv7 image published (bakes QUAL-78).** Owner-requested dispatch, run
  29425139761 green end-to-end: backend-health (suite + pyright + gate trio), frontend-health (the
  restructured sibling-commons job), and the armv7×ru publish matrix — `locveil-voice-armv7` on GHCR
  at `latest`/`sha-1a52a45`/`v20260715-…`, models-not-baked and size-budget guards passing. First
  published armv7 image carrying the QUAL-78 healthcheck log filter — the sprint close-slot's image
  half; the WB7 pull + `/health` smoke remain the owner's deploy step.

- **2026-07-15 — UI-20 done: the editor works offline — Monaco ships in the bundle.** The HK-11
  side-find closed: `@monaco-editor/react` no longer reaches for jsdelivr at runtime. Monaco 0.53
  (0.55 deliberately pinned back — its dompurify has open advisories, and the 0-vulns bar stands) is
  bundled with the loader pointed at the local instance and the editor worker inlined as a blob, so
  nothing about the import-map load path can break worker resolution. Monaco's own laziness carried
  over for free: the 3 MB editor core and the per-language grammars are code-split chunks fetched
  relative to the plugin entry — local files under the shell mount, loaded only when a diff view
  opens. One honest residual: the CDN URL string survives in the bundle as the loader package's inert
  default config, dead on a branch the provided instance short-circuits. Zero external requests at
  runtime; the privacy-first product no longer phones a CDN to show its own config diff.

- **2026-07-15 — UI-21 + UI-22 done: the last shims of the old world — window.confirm, bare title=,
  and the plugin's own fixed bottom bars — are gone.** Hours after commons shipped IMPL-4 (Toast +
  AlertDialog, ui-kit 0.1.1) and IMPL-5 (ActionBar/ActionBarHost, ui-kit 0.1.2 + workbench-v1.1),
  voice consumed both. The three window.confirm calls in the save flow became one promise-shaped
  AlertDialog with identical control flow; 45 native title= attributes across 28 files became kit
  Tooltips (icon-only buttons keep their accessible names via aria-label — the sweep added them
  everywhere a title used to be the only label, an a11y improvement the old attributes never
  delivered); and both bottom bars now register into the ActionBar bus, rendered by the shell's host
  in normal flex flow — the fixed-positioning wrappers and the DonationsPage padding hack are deleted,
  so stylebook §8 holds without exception in the plugin. The HK-11 singleton architecture did the
  heavy lifting: one shared bus instance across shell and plugin by construction, no prop drilling,
  no contract change. Toast has no call sites yet — the bus is there when a real UX need appears.
  Gates: check + plugin build + vitest 44/44 + served-shell smoke with the new kit. UI-22 written back
  onto commons IMPL-5 as its first consumer.

- **2026-07-15 — UI-16 done: the config editor stops guessing — the schema now says.** The port arc's
  last row closed by building the backend metadata it was blocked on. The sections endpoint declares
  which sections are live-testable components (one map, beside the API identities it names — the
  text_processor→text_processing remap now exists in exactly one place, test-guarded), and every
  specialized widget is chosen by a `widget` hint the Pydantic fields declare — 23 hints placed by
  mechanically auditing every model field against the old frontend name/path predicates, which are
  deleted. The audit also caught what guessing had cost: list fields like `fallback_providers` matched
  the single-value provider select, whose onChange would replace the array with a string — that
  corruption path is gone, deliberately not preserved. E10 dissolved at intake: the 21 English attribute
  descriptions were dead data nobody rendered, so the i18n bypass was removed by deleting them. The
  owner's mid-session contract question sharpened the verification: the hints do flow into the
  `ui-openapi` artifact through the component model schemas — an additive regeneration under the drift
  guard, no STAMP bump. A cwd lesson for the books: the first full-suite run from `backend/` "failed"
  76 tests; identical failures without the change — CI runs from the repo root because tests resolve
  assets cwd-relative, and from the root the suite is 1417/7 green with two new tests.

- **2026-07-15 — UI-19 done: the whole editor wears the steel.** The sprint's flagged biggest slice —
  35 composites and 6 pages, 1051 raw Tailwind palette classes — went onto the design system in one
  session, executed as five parallel agents over disjoint file sets against a single brief distilled
  from the stylebook, then swept and re-gated centrally. The mechanical half is total: zero raw palette
  classes remain anywhere in the tree, both themes ride the tokens, and the status vocabulary
  (pristine/edited/tested/persisted/conflict) now carries every state surface through chips, alerts and
  the literal token recipes (verified extracted into the shipped CSS, light and dark). The structural
  half swapped ~60 raw buttons, 12 selects, 3 tab bars, the one hand-rolled modal, ~20 feedback boxes
  and the fake loaders onto kit primitives — while 9 native selects stayed deliberately (radix forbids
  the empty-string placeholder semantics they legitimately use) and the pattern-card editors, LanguageTabs
  chrome and Monaco panes stayed custom per the stylebook's own carve-out. Honest leftovers, all filed
  or upstream-gated: window.confirm and bare title= wait for commons IMPL-4 → UI-21; the two fixed
  bottom bars wait for a plugin-contract bottom-slot surface that doesn't exist yet. Gates: check +
  plugin build + vitest 44/44 + shell smoke. The port arc is now UI-18 ✓ UI-17 ✓ UI-19 ✓ — of the
  sprint's voice rows only UI-16 remains.

- **2026-07-15 — BUILD-39: the push-day CI restore — and BUILD-38's fix turned out to be a fix for
  git, not for the action.** The day's push (BUILD-38 + intake + UI-18 + UI-17) failed both path-gated
  jobs, run 29417879036. contract-guard: `fetch-tags: true` is silently IGNORED by actions/checkout@v4
  on its shallow fetch-by-SHA path — the run's own checkout log shows the fetch carried no tag refspec,
  so the 4× TAG-MISSING false alarm fired exactly as before; the BUILD-38 simulation had proven the git
  command, not the action's wiring of it. The version-proof form is an explicit
  `git fetch --tags --depth=1 origin` step, re-simulated green from a bare shallow clone. The finding is
  bigger than voice: commons' own workflow carries the identical latent line, PROD-25's "one-line fix
  class" convention is amended, the bridge gets a verify-OPS-30 heads-up (checkout@v6 may behave
  differently), and satellite's pending delegation inherits the corrected form. frontend-health: the
  Workbench-era sibling `file:` deps (locveil-ui-kit, the workbench contract) don't exist in a lone CI
  checkout — npm made dangling symlinks and tsc failed 12×. The job now checks out voice and
  locveil-commons side by side and builds the kit before the unchanged gate, so the dev-phase
  consumption model holds in CI too.

- **2026-07-15 — UI-17 done: config-ui is now the Voice tab of the Workbench — the standalone app is
  gone.** The plugin conversion landed hours after its foundation: `src/plugin.tsx` default-exports the
  contract's `WorkbenchPlugin` with the six real pages (Overview, Header, Layout, Sidebar and the
  language switcher deleted — shell chrome owns navigation, locale and theme now), the status slot
  carrying what the old Header showed (connection + handler count, RU/EN), and i18n gone plugin-local
  behind the shell's locale signal. The build is a vite library: ESM entry with the HK-11 singleton set
  external (verified as bare specifiers in dist), preflight-free styles, and a build-emitted manifest
  fragment whose peers pass the shell's strict check. The whole loading path was driven live against the
  served shell — runtime-config lists voice beside the demo plugin, manifest → entry → styles all 200 —
  making it the Workbench's first real product plugin (commons `workbench.config.json` now mounts it).
  Three intake decisions on record: voice keeps its own backend-base mechanism (the contract's PageProps
  carries only locale), the report hook honestly names the voice-first ARCH-30 path (no REST write
  surface exists, and one would be PROD-4-gated), and the standalone container retired with the app
  (Dockerfile/nginx/publish job removed; the WB7 was never running it). The `config-ui-stays-functional`
  DoD is re-anchored to the plugin build in CLAUDE.md, same change, per the HK-11 owner ruling. Gates:
  check + plugin build + vitest 44/44 + docs-manifest 8/8; QUICKSTART, INSTALL, build-docker and the
  config-ui README all teach the Workbench story now.

- **2026-07-15 — UI-18 done: config-ui stands on the design system.** The port arc's foundation slice
  landed in one session: eslint-9 flat config (rule set carried over verbatim, type-aware gate verified
  still firing), `locveil-ui-kit` wired in (sibling `file:` dep, Tailwind preset, blued-steel tokens at
  the entry — both themes now ship in the bundle), and all nine hand-built primitives rebuilt on kit
  primitives behind their existing prop APIs, so the 35 composites compile untouched and wait for UI-19.
  The satisfying rhyme: the kit's `StatusVariant` vocabulary (pristine/edited/tested/persisted/conflict)
  is exactly config-ui's workflow-state enum — the council took voice's states as canon, and now voice
  consumes them back. First-consumer duty paid too: the adoption build immediately exposed a latent kit
  bug (StatusChip classes assembled via template literal — invisible to Tailwind's extractor, and the
  `${h}` pseudo-class it did extract broke lightningcss minification); fixed upstream as commons IMPL-3
  with voice's green build as the live proof. Gates: check + build + vitest 44/44; chip recipes verified
  down to the generated utilities in the shipped CSS.

- **2026-07-15 — sprint-02 intake: the port arc lands in the ledger (UI-17 narrowed; UI-18/UI-19/UI-20
  filed).** The sprint-02 §4 split turned the XL-in-disguise UI-17 into a three-task arc: **UI-18**
  (kit-first foundation — eslint-9 flat, `ui-kit-v1` dep + preset/tokens, the 9 hand-built primitives
  rebuilt on kit primitives) and **UI-19** (port body — 35 composites + 7 pages, the sprint's flagged
  largest risk) are new IDs; **UI-17** keeps the plugin conversion and its PROD-24 write-back role. The
  HK-11 council corrections are folded into UI-17's text (shell loads built bundles at runtime via native
  ESM + import map — the `file:`-deps sentence is superseded; lib-mode build externalizes the frozen
  singleton set with router pinned major 6; the standalone app RETIRES at UI-17 with the
  `config-ui-stays-functional` DoD re-anchored to the plugin build), and the council's Monaco-CDN
  side-find checked out live (`@monaco-editor/react` default loader = jsdelivr at runtime) → filed as
  **UI-20**. Both write-backs (UI-17 corrections + UI-20) recorded in the HK-11 board entry. One sprint
  side-find dissolved at reconciliation: the ci.yml guard-version prose was already fixed by BUILD-38
  earlier today.

- **2026-07-15 — BUILD-38: the contract-guard CI job can now actually see the tags it checks.**
  Board PROD-25 (filed off the bridge's OPS-30 incident) delegated "checkout fix + v2 re-pin" to
  voice — but intake reconciliation found the re-pin already landed (BUILD-37, 2026-07-14); the
  bridge's sweep had read the two labels BUILD-37 missed (`ci.yml` step name, `contracts/README.md`
  registry line), both still saying v1. Net effect: v2's `TAG-MISSING` rule was already live here
  against a tag-less `actions/checkout` — the path-gated job would have fired 4 false alarms on the
  next `contracts/**` push, exactly the commons situation. Fix: `fetch-tags: true` on the guard
  job's checkout + the two label bumps. Proven by simulation: a `--no-tags --depth 1` clone of this
  repo fails 4× TAG-MISSING, the same clone passes after fetching tags. BUILD-38 written back into
  the board entry.

- **2026-07-14 — QUAL-78 done: the healthcheck's 2.9k daily access lines are out of the log.** A
  `logging.Filter` on `uvicorn.access` drops 2xx `/health` + `/ready` probe lines at the emitting logger,
  installed in `_build_uvicorn_server` (the choke point both serve paths share); non-2xx probes stay —
  a failing probe is the event worth seeing. The live verification (a real uvicorn server driven through
  the mixin) caught a placement trap the unit tests could not: `uvicorn.Config.__init__` applies its
  dictConfig, which RESETS the `uvicorn.access` logger's filters — attached before Config, the filter is
  silently wiped and every probe still logs. Attached after, verified: two 200-probes dropped, a normal
  request and a 503 probe both logged. 6 new tests; suite 1415 pass / 7 skip.

- **2026-07-14 — TEST-20 done (BUG-42 folded in): the satellite-recorder flake was a coin flip on file
  mtimes.** The two tasks turned out to be one defect filed from two vantage points — TEST-20 saw it
  intermittent in isolation (3/8, 2026-07-09), BUG-42 saw it order-dependent in the full suite and
  mis-diagnosed cross-file state leakage (2026-07-11). The recorder is innocent: uuid filenames, T-5
  deterministic finalization. The test sorted the two trace files by `st_mtime` — and two back-to-back
  writes tie on the kernel's coarse timestamp clock 196/200 times, so `files[0]` was filesystem hash
  order of two uuids. First fix attempt (select by `declined` marker) failed 30/30 and taught the real
  shape: BOTH envelopes are trace-declined; the discriminator is the uplink payload (error vs response).
  Final fix selects by content. Pre-fix 8/20 red in isolation (falsifying BUG-42's "passes in
  isolation"); post-fix 0/40, file 14/14, full suite 1409 pass / 7 skip. CI's random red — the one that
  "teaches everyone to ignore failures" — is gone.

- **2026-07-14 — PROD-24 intake: the Workbench delegations filed as ARCH-51 + UI-17.** The board's
  Workbench shell council (PROD-24, decided 2026-07-14; commons `docs/design/workbench.md`) delegated two
  voice items. Reconciled clean against the repo: config-ui is 7 pages (Overview + 6 — matching the
  council's "6 pages after Overview + Header retire"), `Header.tsx` is where connection/health status
  lives today (→ the plugin status slot), `config-master.toml` carries the `[satellite]`/`[vad]`/
  `[voice_trigger]` sections the device-owned config page would edit, and the satellite runner is
  client-only (no server surface — the endpoint design adds one). Filed: **ARCH-51** (satellite-local
  config endpoint design; dev-phase shape, PROD-4 auth binding condition) and **UI-17** (the sprint-01
  "declared, IDs at intake" config-ui adoption task, grown by the council: Workbench plugin + ui-kit
  adoption, 6-page cut, status-slot wiring; travels with UI-16). IDs written back into the board entry. The HK-9 dependency
  audit's side-find executed: ARCH-42/43 + BUILD-18 were still "gated on BUILD-21" (closed 2026-07-11) —
  re-anchored to their real gates (commons PROD-8 / PROD-4); UI-4's Gate-2 block discharged (the
  remediation core is fully DONE; the fictional-endpoints + re-scope conditions stand); the sequencing
  block's "QUAL-29 remains" corrected. Executed by the commons session on owner instruction, filed and
  completed in one change per the quick-task precedent.
- **2026-07-14 — BUILD-37: contract-guard re-vendored @ v2 (PROD-22).** The TAG-MISSING rule arrives
  (bridge-caught false green at catalog-v1.7); voice passes clean — all four owned-contract tags
  already exist. Executed by the commons session on owner instruction, filed and completed in one
  change per the quick-task precedent.
- **2026-07-14 — BUILD-36 WB7 install deployed clean.** The controller upgrade — `git pull` + the
  one-time `ops/cutover-env-locveil-voice.sh` (`.env` token-key rename → `update.sh` image pull/restart →
  `/health` smoke) — landed without incident on the published armv7/ru image (`v20260713-a946dab`; code ==
  HEAD). The deferred tail of the closed BUILD-36 is now fully deployed (repo + controller); no
  breakage-BUG needed.

- **2026-07-13 — BUILD-36 closed: the Python layout & naming migration (PROD-21/HK-8), owner-closed
  ahead of the WB7 install.** `irene`→`locveil_voice` + `backend/` src-layout + `configs/`→`config/` +
  env family `IRENE_*`→`LOCVEIL_VOICE_*` + console-script rename (with `irene-*` aliases), across 13
  commits (`85dcc4d`…`b95f3b9`); catalog re-pinned v1.5→v1.7; ui-openapi bumped v1.1; the x86_64 image
  build+boot verified locally (`/health` healthy, in-build component gate green), ARM via the multi-arch
  CI dispatch. The commons PROD-21 bounce (stale `discovery_paths` + `IRENE_*` config comments) was fixed
  — and its requested tripwire proof surfaced that `discovery_paths` is a **vestigial** config field (the
  handler manager hardcodes its discovery namespace and never reads it), which filed **ARCH-50** to review
  all such hardcodings/overrides against the dynamic build-and-loading contract. Owner closed the task with
  the WB7 image rebuild + env cutover explicitly deferred: any controller breakage becomes a fresh BUG.

- **2026-07-13 — ARCH-49 filed: the language-asset re-cut, designed before touched.** An owner analysis
  session asked what actually separates `assets/templates/` from `assets/localization/` — answer: the
  phase-2/3 hardcode extractions split by the SHAPE of what was lifted (strings vs dicts), not by role,
  and the seam leaks in four places (output templates inside localization/datetime, a non-handler
  templates key, and two technical-mapping "localizations" forked per language with identical content).
  Owner picked the role-axis re-cut — `responses/` (what Irene says) vs `lexicon/` (what she listens
  with), technical mappings evicted to donations/config — and the schema question got settled in the
  same session: YAML stays on disk, schemas validate the parsed content, and the checks that matter most
  aren't schemas at all (cross-language key parity, placeholder parity). Filed `[deferred]` as a design
  task; the design doc comes first, implementation follow-ups from it.

- **2026-07-12 — DOC-11 + DOC-12 + BUILD-35 executed (same-day): voice speaks the docs convention.** The
  whole PROD-17 delegation, in dependency order. The live stale fixes first: the docker guide and the WS
  Python example now say 8080 like the images they describe, the QUICKSTART profile table stops calling
  Wirenboard controllers "ESP32 satellites", and the satellite guide hands off to the provisioning
  runbook where the certificate plane actually lives. Then the manifest: 60 nodes over 8 roots — every
  guide, architecture story, diagram pair, the README/QUICKSTART/INSTALL/CONTRIBUTING front doors — with
  10 surface→glob triggers, the websocket-api node carrying the canonical carve-out, and an 8-check
  coherence test in the normal suite (a doc without a node now fails CI; so does a verdict naming a
  ghost node). Last, the teeth: scope-guard re-pinned at `scope-v5`, the docs-verdict rule live from
  today — which promptly retro-flagged all nine of today's earlier completions, each now carrying its
  honest verdict (the rule caught its own rollout day; a good sign). CONTRIBUTING gained the contracts,
  eval, and docs-discipline front-door sections. Suite green, both guards green, block byte-verified.

- **2026-07-12 — PROD-17 intake: the user-docs convention lands in the voice ledger.** The HK-6 council
  (two rounds, all three keepers) decided the org docs convention — normative
  `../locveil-commons/process/user-docs.md` + the manifest schema; commons shipped scope-guard 1.2.0
  (`scope-v5`, the docs-verdict presence rule) and the template seeds. Voice's delegation reconciled —
  every stale-doc claim verified against the tree (the port-6000 quartet and the WS example line are
  real: all images serve 8080; the QUICKSTART "ESP32 satellite controllers" label is wrong — WB7/WB8
  are Wirenboard controllers; the HF wake-word link is live, checked by today's wake-pack re-pin;
  `satellite.md` indeed lacks a provisioning pointer). Filed: DOC-11 `[release]` (the live fixes),
  DOC-12 `[release]` (manifest + coherence test + CONTRIBUTING links), BUILD-35 `[release]` (dialect
  rewrite + `scope-v5` re-pin with `docs_verdict_since`). IDs written back to the board.

- **2026-07-12 — esp32-site pin upgraded to the stamped form (`esp32-site-v1`) — mechanical re-pin,
  no ledger task (the block re-pin carve-out spirit).** The satellite's OPS-3 cut tagged the Plane-B
  template surface, so voice's pre-tag artifact-copy pin filled in exactly what its own PIN.json
  anticipated: `version`/`tag` now `1`/`esp32-site-v1`, the owner's STAMP carried verbatim, template
  bytes unchanged (same sha256 the pre-tag pin held — the satellite tagged byte-identical, as its tag
  message promised). `repin.py`'s esp32-site family gained the owner STAMP file; one `make repin
  CONTRACT=esp32-site` did the rest, and the untagged-family branch of `repin-check` retires from use.
  TLS e2e green from the pinned template, contract-guard 0 warnings, all pins current at owner tags.

- **2026-07-12 — BUILD-34 executed (same-day): the catalog contract now fails fast, locally.** The
  owner's completeness ruling closed the corner flagged in HK-5: voice consumes the catalog REST API at
  runtime yet had no push-time schema check — conformance lived only in the release-cadence cross-suite.
  Voice now holds the bridge's FULL `catalog-v1.5` artifact set at `contracts/pins/catalog/` (a pin is
  complete by definition; usage never shapes it), and `repin.py` grew multi-destination families: one
  `make repin CONTRACT=catalog` writes the local pin and the commons crossover pin at the same tag, so
  the two copies cannot diverge; `repin-check` walks every copy. The new named suite test binds both
  directions of the boundary to the pinned schemas — inbound (`parse_catalog` accepts the pinned golden,
  golden IS a `CatalogResponse`) and outbound (`DeviceCommand`/`RoomGroupCommand` wire bodies validate
  as `CanonicalActionRequest`/`RoomCanonicalRequest`, examples drawn from the golden itself). A bridge
  reshape now reddens voice's own CI on the next push instead of waiting for the cross-suite. Suite
  1401/7 skipped, guard clean, all four pin copies current.

- **2026-07-12 — BUILD-26 executed: the UI's view of the API can no longer silently rot.** The last of
  the PROD-16 voice batch. `config-ui/openapi.json` — the committed generated schema config-ui's types
  are built from — now has a drift guard in the standard suite: `test_openapi_drift.py` assembles the
  schema exactly as `scripts/dump_openapi.py` does and fails on any delta, with the regeneration command
  in the failure message (the REL-4 four-missing-schemas incident becomes a red test instead of a
  discovery). As the convention's repo-internal instance it also got its surface: `contracts/ui-openapi/`
  STAMP + pointer README, registry row, tag `ui-openapi-v1` — the stamp versions the convention surface
  while the guard keeps the bytes exact. Reconciled at start: today's dump matches the committed file
  (REL-4 fixed the instance; this task shipped the mechanism). config-ui gen:api-types/check/build green.

- **2026-07-12 — BUILD-24 executed: re-pins are a script, staleness is a gate — and the first real
  re-pin already ran.** The bridge cut `catalog-v1.5` today (VWB-29), which opened this task's gate the
  same day it was picked up. `scripts/repin.py` knows every consumed family (catalog, report-protocol,
  esp32-site — owner, artifact paths, destination, conformance test) and does the whole hand-copy ritual
  in one command: fetch the owner's committed artifacts at the newest family tag, write verbatim copies,
  stamp a strict `PIN.json` the vendored contract-guard hash-verifies on every commit. `make repin` /
  `make repin-check` wrap it from `eval/`; the check is a release-time gate by design — an owner tagging
  a new version never breaks voice's CI, it goes red only when we ask at release. The catalog pin in
  commons is now strict (golden byte-identical at v1.5, openapi/STAMP refreshed, legacy warnings cleared
  down to the one co-owned fixtures pin), commons suite 40/40, all three families report current.

- **2026-07-12 — ARCH-47 executed: the wire protocol and the wake pack now know their own versions.**
  The convention's first voice-owned surfaces. The WS protocol's version lives as a triple — the
  "Protocol version: 1" header in `websocket-api.md`, the served `WS_PROTOCOL_VERSION` constant (now in
  every `registered` ack on both satellite channels), and `contracts/ws-protocol/STAMP.json` — with a
  conformance test that fails any bump missing a leg; tagged `ws-protocol-v1`. The wake pack got its
  sidecar stamp (`wake-pack-v1`): sha256s of the published HF pack (irina.json + irina.tflite, revision
  recorded) without forking the third-party manifest, and the same test pins the stamp to the in-code
  released catalog. `register` now carries the device's build-truth (`protocol_version`,
  `firmware_version`, `wake_pack_version`) — the Python runner reports the first two; the flashed-pack
  field is honestly left to ESP32 firmware. The doc gained the register-fields prose and both ack shapes
  in the same change. The staleness *comparison* (registry REST + config-ui surfacing) filed as ARCH-48
  rather than riding — the fields had to exist first. The satellite can now upgrade its commit-pin to a
  stamped pin. Suite 1395/7 skipped, WS suites 28/28, pyright 0, contracts 11/11, contract-guard clean.

- **2026-07-12 — BUILD-33 executed: contract-guard v1 vendored, both enforcement rails live.** The
  commons coherence checker rides the same consumption model the scope guard proved: a single stdlib
  file vendored byte-exact at its pinned tag (`contract-guard-v1`, verified against the tag before
  copying), never edited locally, moved only by re-pin. The pre-commit hook now runs both guards in
  sequence, and CI gained a `contracts` paths-filter plus a path-gated `contract-guard` job shaped
  like `ledger-guard` — a contract-surface commit pays for the check it earns, nothing else does.
  With BUILD-32's tree already strict, the guard is green at zero warnings from its first commit.

- **2026-07-12 — BUILD-32 executed (same-day): voice `contracts/` now wears the org shape.** The two
  consumed pins moved under `contracts/pins/<name>/` — report-protocol carries the owner's STAMP verbatim
  plus a strict `PIN.json` (sha256 file map, conformance pointer, tag `report-protocol-v1`); esp32-site
  becomes the convention's first pre-tag artifact-copy pin (owner commit + content hash now, version/tag
  null until the satellite stamps that surface). Both copies proved byte-identical to their owner
  artifacts before moving. The registry README is direction-labeled per the spec, and every consumer
  followed in the same change: both conformance tests, the eval device suite re-pointed at commons'
  restructured `contracts/pins/{crossover-fixtures,catalog}/`, the CLAUDE.md ownership bullet, the
  `/inbox` skill, the problem-reports design pointers. Proof: contract-guard v1 runs green with zero
  warnings (stricter than the legacy-tolerant commons tree itself), report-protocol conformance 11/11,
  the hermetic TLS e2e renders the template from its new home, and `make device-tests` regenerates
  byte-identically. BUILD-33 (vendor the guard) now has a clean tree to guard.

- **2026-07-12 — PROD-16 intake: the contracts convention lands in the voice ledger.** The HK-5 council
  (one round, all three product keepers) decided the org-wide contract convention — normative spec at
  `../locveil-commons/process/contracts.md`, contract-guard v1 tagged, the commons-side restructure and
  eval re-point already executed. Voice's delegation reconciled against repo reality — every claim held:
  the catalog pin now lives at commons `contracts/pins/catalog/` while three voice eval files still point
  at the old flat paths, and this repo's `contracts/` is still flat. Filed: ARCH-47 UNGATED and rescoped
  in place as the convention's first voice instance (`ws-protocol-v1` + the wake-pack sidecar stamp);
  BUILD-24 rescoped to be born against the final bridge layout (generalized `make repin`, release-time
  staleness, never push gates); BUILD-32 filed `[release]` (pins-shape restructure + the eval re-point —
  immediate per the q3 ruling, so the release gate deliberately grows); BUILD-33 filed `[release]`
  (vendor contract-guard v1, BUILD-30 consumption model); BUILD-26 annotated to cite the convention.
  Local IDs written back into the board's PROD-16 entry.

- **2026-07-12 — ARCH-47 gated on the contracts council (owner decision).** The version-stamp work is
  better decided once, for all the contract surfaces (five dialects across the repos), than invented here
  ad hoc — ARCH-47 now carries a GATED note (do not pick up standalone) and rides board **HK-5**, the
  parked contracts-in-general council seed. No urgency lost: the satellite's interim commit-pin holds,
  and its FW phase (the first real consumer) is gated behind satellite DES-3 anyway.

- **2026-07-12 — index housekeeping: `satellite_tracing.md` row added.** The ARCH-37 design doc (AGREED
  2026-07-07) was never indexed — both its tasks (ARCH-37/38) closed same-day and are already archived,
  so the omission was cosmetic, but it kept scope-guard warning UNINDEXED on every commit. Row added to
  the design index; the guard is warning-free again. Mechanical fix, no scope change — no ledger task.

- **2026-07-12 — `cross-repo-board` block re-pinned @ scope-v4 (PROD-15 close follow-through).** The
  shared block now names `../locveil-satellite` as the fourth sibling; block text between the markers +
  the `.scope-guard.toml` hash updated from the commons source per the `process/claude-md.md` §3 flow
  (mechanical re-pin, no other content change — no ledger task, same spirit as the lockfile carve-out).
  PROD-15 itself closed on the board the same day.

- **2026-07-12 — BUILD-22 executed: locveil-satellite lives, the ESP32 estate left this repo.** Three
  commits across two repos. Satellite `121f3d0`: template instantiation @ scope-v3 (shared-block hashes
  byte-identical to ours), repo-local LAW per HK-4, born backlog seeded — the first commit passed its own
  scope-guard hook. Satellite `37dcac5`: design corpus + the Plane-B tree imported (`nginx/` →
  `provisioning/`), `esp32_satellite.md` §4.1–4.3 demoted to a pointer at our `websocket-api.md`, imported
  tasks DES-5 (ex ARCH-44) + FW-1 (ex ARCH-23) filed there. Voice side (this commit): `ESP32/` deleted,
  `nginx/` removed, pointer stubs left at the three moved doc paths, `contracts/esp32-site.conf.j2` pinned
  (satellite-owned now; re-pin command in `contracts/README.md`) and `test_arch36_tls_e2e.py` re-pointed at
  the pin — **re-run green (1 passed)**. `ops/INSTALL.md`, `README.md`, two guides, `python_satellite.md`
  §5 and the `irene/satellite/provisioning.py` docstring re-pointed. **WB7 ops handover:** the deployed
  Plane B on the controller is untouched (nginx site, CA, scripts all live); future `deploy.yml` runs
  happen from `../locveil-satellite/provisioning/ansible/` — the operator-local `inventory.ini` +
  `group_vars/all.yml` were copied there on disk (gitignored both sides, now deleted here with the tree).
  ARCH-23/ARCH-44 export-closed with pointers; BUILD-22 moved to the DONE ledger.

- **2026-07-12 — PROD-15 intake: the locveil-satellite delegation reconciled and filed.** The HK-4
  council decision (four rounds; arc in `../locveil-commons/board/BOARD_DONE.md`, delegation text in the
  PROD-15 board entry) delegates the satellite bootstrap + ESP32 estate lift-out to this repo. Verified
  per `task-start-reconciliation`: the org repo `locveil/locveil-satellite` already exists (owner action
  done — LICENSE+README stub, sibling working copy not yet cloned); the frozen BUILD-22 text disagreed
  with the decision in two places — the nginx Plane-B tree now MOVES (with a pinned `esp32-site.conf.j2`
  copy kept here so `irene/tests/test_arch36_tls_e2e.py` keeps running), and ARCH-23/ARCH-44
  export-close with pointers instead of staying deferred here. BUILD-22 REDEFINED in place (dated);
  NEW ARCH-47 filed (WS-protocol version stamp + wake-pack pin surface + `register` version-reporting
  fields — the contract surface satellite pins). Both local IDs written back into the PROD-15 board
  entry (commons-side commit, same intake). Execution is BUILD-22 itself, next.

- **2026-07-11 — ARCH-46 bounce (commons verification) → lift-out landed.** The commons-side verification of
  the PROD-14 voice delegation accepted items 1–3 + the smoke finds but bounced item 4: the
  `problem_reports.md` restructure had been delivered annotate-and-defer — ownership headers over §5/§7 with
  the bodies kept in full, i.e. two complete copies of the shared vocabulary, exactly what
  `process/problem-reports.md` §1 forbids. Fixed as agreed in HK-3 round 2: §5 and §7 bodies are now pointers
  to the commons spec + the pinned core, keeping only the voice-side remainder (§5: `build_envelope` is the
  writer seam, contents-API/base64 mechanics; §7: the D-11 model-policy *rationale* as decision record —
  the policy itself is the spec's — and the outcome-3a later-note; per-lens judgment explicitly deferred to
  the co-owned `lens-voice.md`). Stale cross-refs to the lifted anchors re-pointed: D-2's «§7.3» → the core's
  `handover_comment`, §4's «§7.4» → commons spec §3, and the same leak-fence ref in the `report_bundle.py`
  docstring. The DONE ledger row was annotated with the bounce rather than reopened — the record was wrong,
  not the scope, and the correction landed the same day.

- **2026-07-11 — ARCH-46: PROD-14/HK-3 delegation executed — voice consumes `report-protocol-v1`.** The wire
  surface the collector emits is no longer convention: the commons machine core is pinned at
  `contracts/report-protocol.pin.json` (new `contracts/` home for externally-owned pins, README carries the
  re-pin command) and `test_report_protocol_conformance.py` (11 green) asserts `build_envelope`'s labels,
  title prefixes (both sources), bundle-path template, and envelope required fields against it — plus the six
  deployment profiles' `[reports].repo` against the pin's slug registry, so the next rename can't silently
  strand tickets. `/inbox` caught up with the bridge's skill (ping-pong guard in the handover step, the
  affirmative post-merge ledger wording); `wb7.env` lost its stale port 6000 (deployed image serves 8080 —
  the WS/UX suites would have dialed a closed port on the freshly deployed controller);
  `problem_reports.md` §5/§7 now defer to the commons spec (banner + pointers, ARCH-30 record untouched);
  CLAUDE.md's `cross-repo-source-of-truth` names the commons as protocol owner. Cross-repo commits:
  reports `1ca251e` (lens-voice re-review — one stale `eval-commons` claim fixed; the rest verified true),
  commons `50bf906` (Voice ID written back; the bridge wrote back VWB-35/36/37 the same day). The user-facing
  guide `docs/guides/problem-reporting.md` checked — written at user altitude, no slug/port/label mentions,
  nothing to update.

- **2026-07-11 — ARCH-46 intake: the PROD-14/HK-3 voice delegation pulled from the board.** Verified per
  `task-start-reconciliation` against repo reality: the delegation's slug-sweep list is largely already
  satisfied — BUILD-31 (earlier today) re-pointed the inbox skill, the `problem-report-inbox` invariant,
  config-master's example, and the six deployment profiles, and also covered the "enable `[reports]` in the
  canonical WB7 profile" Phase-1 find. Narrowed scope filed as ARCH-46: `/inbox` drift fixes (ping-pong guard +
  affirmative post-merge ledger wording, both present in the bridge's skill and absent here), the stale
  `wb7.env` port (6000→8080 — the deployed image serves 8080), `report-protocol-v1` pin + conformance test,
  `problem_reports.md` shared-section pointers to the commons spec, and the `lens-voice.md` co-ownership
  re-review (VWB-26 pattern). Lens claims pre-verified at intake: checkout path `code/locveil-voice`,
  `$CROSS_REPO_TOKEN` env name, `irene-cli -c/-e` flags, `test_qual64_matcher_scoring.py`, and the bundle
  member names all check out; the one stale claim found is an `eval-commons` mention (renamed repo). ARCH-46
  written back into the PROD-14 board entry as the Voice ID.

- **2026-07-11 — BUILD-31: problem reporting switched ON in all six deployment profiles; reports repo
  references follow the rename to `locveil/locveil-reports`.** User question ("why don't the docker configs
  have a reports section?") uncovered a structural sync miss from ARCH-31: the `[reports]` section went into
  master + example, but the six deployment configs only got the `report` *handler* — so the Pydantic default
  (`enabled=false, repo=""`) applied, and BUILD-15's `IRENE_REPORTS_TOKEN` plumbing could never activate
  anything (the token arrived; the config gate in `setup_problem_reporting` never opened, and
  `ops/INSTALL.md` misleadingly implied the token alone sufficed). All six profiles now carry
  `[reports] enabled=true, repo="locveil/locveil-reports"` — activation is exactly token-presence, matching
  what INSTALL.md promises (its Secrets section now says so explicitly). The rename discovery: the reports
  repo didn't just change name, it **moved to the `locveil` org** (`droman42/wb-user-reports` →
  `locveil/locveil-reports`, verified via `gh` redirect; `droman42/locveil-reports` is a 404) — references
  updated in CLAUDE.md (`problem-report-inbox`), the `/inbox` skill, master's `repo` example comment,
  `github_report.py` docstring, and a rename note on design D-1 (historical mentions left frozen).
  **Operational flag for the owner:** fine-grained PATs are minted per resource owner — a PAT created under
  `droman42` for the old repo does NOT reach an org-owned repo; the device token in the WB7 `.env` (and the
  `REPORTS_CROSS_REPO_TOKEN` secret, if PAT-based) must be re-minted under the `locveil` org or reports will
  spool/fail silently. `[satellite]`'s absence from the profiles was checked and confirmed intentional
  (controller ≠ room node). All 14 configs parse with the expected reports state; config gates + report
  tests green.

- **2026-07-11 — BUILD-23: CLAUDE.md joins the shared-block regime (HK-2/PROD-5) — second board delegation
  consumed, same day.** Narrowed at intake exactly as the delegation pre-specified (the "separate drift-guard
  script" wording was dead; scope-guard's `claudemd` hash rule from `scope-v3` is the drift guard — the
  narrowing was owner-approved at the HK-2 council, so no fresh consult was needed). Both pinned digest blocks
  (`shared-invariants`, `cross-repo-board`) now sit in CLAUDE.md between `locveil:begin/end` markers,
  byte-identical to `../locveil-commons/process/claude-blocks/` at `scope-v3`; the six long-form shared
  invariants they replace came out, with voice specifics condensed into the new `ledger-dialect` bullet —
  CLAUDE.md net-shrank 165→160 lines (HK-2's hard criterion). Scope-guard re-pinned `scope-v2`→`scope-v3`
  (1.1.0), `[claude]` hash section added, hashes verified against `--hash-blocks`, tamper test red/green.
  The stale pre-board "filings arrive uncommitted" bullet in `cross-repo-source-of-truth` was rewritten
  (board-as-outbox vs direct operational filings); `config-master-canonical` renamed to `config-master-file`
  (legend row records it; the bridge takes `config-master-tree`); CI `ledger` paths-filter gained `CLAUDE.md`;
  BUILD-22 now must instantiate `process/new-repo-template/` rather than freehand the satellite repo.

- **2026-07-11 — BUILD-30: ledger discipline now guarded by the commons scope-guard (`scope-v2`) — first
  board-as-outbox delegation consumed.** Pulled the PROD-13/HK-1 delegation from the commons board, verified
  every claim against the live tree (both advertised pre-existing findings were real: the DONE I18N section sat
  in 1,2,8,3,7,4,5,6 order — invisible to the old checker's regex — and the DONE ledger was over the new
  4000-line hard ceiling), filed it as BUILD-30 and wrote the ID back to the board. Cutover: vendored
  `scripts/scope_guard.py` + `.scope-guard.toml`, retired `scripts/check_scope.py`, re-pointed the CI
  `ledger-guard` job and paths-filter, committed `hooks/pre-commit` (+ one-time `git config core.hooksPath
  hooks`), updated the `single-task-ledger`/`one-active-journal` invariant text and the gate wording. Both
  rotations ran via `--rotate` in their own commit: journal 1510→708 (2026-07-04..06 frozen), DONE ledger
  4273→1930 (125 entries frozen to `docs/archive/ledger/`), verified lossless by line-multiset diff. **The
  first rotation attempt found a real bug in scope-v1:** `rotate_journal` wrote archives char-per-line and
  silently truncated the kept journal (tuple double-indexing after unpacking) — the bridge session hit the
  identical bug minutes earlier during its OPS-22 rotation and landed the fix as `scope-v2` (commons `09a9025`);
  this repo's corrupted first-pass commits were rebuilt (nothing had been pushed). Regime 2 worked as designed:
  the bug was fixed once, commons-side, and consumed by re-pin. Pre-existing, unchanged: the
  `docs/design/satellite_tracing.md` unindexed-review warning (warn-only, predates the cutover).

- **2026-07-11 — BUILD-29 controller cutover CONFIRMED on hardware.** Owner made the new GHCR packages
  public (org policy first blocked the Public option — fixed at org Settings → Packages → allow public
  package creation) and ran `ops/migrate-to-locveil.sh` on the WB7: migration reported successful, the
  controller now runs `locveil-voice` end to end (unit, runtime tree, image, container). Nothing on the
  box says wb-mqtt anymore.

- **2026-07-11 — BUILD-29: deployment identity renamed — nothing on the controller will say wb-mqtt
  after the migration script runs.** Second act of the rename day (owner call: complete the re-pointing
  down to the metal before continuing). Images (`locveil-voice-*`, `locveil-voice-ui`), container, systemd
  unit (`locveil-voice.service`), runtime tree (`/mnt/data/locveil-voice-config`), clone path, INSTALL flow
  — all renamed repo-side in one pass, coordinated with the bridge's OPS-21. The two API-visible bridge-name
  description strings updated with the full contract chain regenerated (openapi 7-line delta — REL-4 had
  already absorbed the BUILD-26 drift; config-ui types regen + check + build green). New
  `ops/migrate-to-locveil.sh` executes the controller cutover in one run (old unit out → tree mv with
  models/state/.env intact → update.sh under the new identity → new unit in → old images dropped);
  sequencing: CI publish + package-visibility flip FIRST, then the script on the WB7. Full pytest surfaced
  a pre-existing order-dependent flake (satellite recorder test; identical on the pre-change tree) → BUG-42.

- **2026-07-11 — BUILD-21: the repo is `locveil-voice` now — commons bootstrap consumed, eval re-pointed,
  name sweep, container user + GHCR namespace.** The owner locked the product name **Locveil** (superseding
  BUILD-20's "Domovoy"), claimed the `locveil` GitHub org, and transferred/renamed all three repos + local
  dirs; the commons side of BUILD-21 landed as `locveil-commons@52126da` (D-2 layout with the eval framework
  under `eval/`, the PROD board live, the decision record migrated there — a pointer remains at
  `docs/design/productization.md`). This change is the voice tail: every `eval/` ref re-pointed to
  `../../locveil-commons/eval` (contracts at `../../locveil-commons/contracts`); operative docs/comments swept
  to the new names (history and live deployment identifiers deliberately untouched — the runtime rename is
  filed as BUILD-29); `useradd domovoy` → `locveil` in the three backend Dockerfiles (uid 1000 unchanged —
  lands at the next image publish); GHCR pull refs/docs cut over to `ghcr.io/locveil/*` (CI already publishes
  by `github.repository_owner`; **one CI publish must run before the next controller `update.sh`**, else the
  compose pull 404s — old `droman42/*` images remain pullable). Found along the way: the dir rename had
  bricked the `.venv` (absolute shebangs in every console script — the eval suite errored with
  `FileNotFoundError: irene-config-validate`); rebuilt with `uv sync --all-extras` + the sqlite shim, then
  `make setup` re-installed `locveil-eval` (the renamed distribution) from the new path. Gates: `make cli`
  5/5, `make device-auto` tier-1 48/48, pytest on touched files 83/83, `check_scope.py` green. The bridge's
  mirror re-point is delegated on the commons board (PROD-2) — its first board-as-outbox pull; its `.venv`
  will be bricked the same way.
- **2026-07-10 — TEST-21 + BUG-41: bridge v0.6.0 consumed — re-pin, and the 5 s timeout that would have
  re-broken the AC path; v0.5.2 tagged as the retest pair for bridge v0.6.0.** The bridge cut its 0.6.0
  release; the contract delta was version-only (`openapi.json` `0.5.0`→`0.6.0` in two places, golden
  byte-identical, catalog still `5622ba7a1a78102a`) → re-pinned @ bridge `e965385`, eval-commons 40/40,
  pushed (`3fd9091`). **The real find was adjacent (BUG-41):** their DRV-29 fix (accepted + implemented
  same day — the filing was *consumed on acceptance*, not erased) holds the canonical response open up to
  `gate.poll_timeout_ms` = **15 s** on all six MitsubishiHvac capabilities, and voice's `BridgeClient` total
  timeout was **5 s** — sized for the retired "~500 ms echo" world. Typical AC echo is 5–7 s: voice would
  have spoken «мост не отвечает» for working commands about half the time (the morning's clean retest was
  luck), recreating the DRV-29 dishonesty one hop upstream. Bumped to **20 s** across the model default, the
  client default, and all 8 configs — `update.sh` delivers config, so the WB7 gets it without an image pull.
  Their VWB-34 (publish confirmation-timing in the contract) is the permanent home for this number; until
  then it is pinned prose. **Versioning note (user decision):** synchronized labels ≠ equal numbers — each
  side tags the state tested against the other's tag, and PIN.json records the pairing
  (`bridge_version: 0.6.0`). Retest pair: **voice v0.5.2 ↔ bridge v0.6.0**.

- **2026-07-10 — BUG-40 fixed: bridge errors speak with their real names; v0.5.1 tagged.** The one-level
  mismatch: on non-2xx the bridge raises `HTTPException(detail=resp.model_dump())`, so the canonical body
  arrives wrapped in FastAPI's `detail` envelope — `_to_delivery_result` read `success`/`error`/`state` at the
  top level, saw `{}`, and stamped `internal_error` for **every** failure (the whole handler template map dead,
  the `param_invalid` → clarification path never once fired against a real bridge). Fix: unwrap `detail` when it
  is a dict; a string `detail` keeps the genuinely-unstructured branch. Tests that encode the *wire* shape now:
  wrapped payloads for 5 canonical codes, wrapped `param_invalid` with `field`/`reason`, and a handler-level
  test proving `param_invalid` arms the one-shot clarify (QUAL-30/31). Suite 1379 pass (lone failure = the
  TEST-20 flake, passes in isolation). With BUG-40 done the `[release]` queue is empty again → **v0.5.1**
  (patch axis: bug fixes + consuming the bridge's DRV-28 contract; voice's own outward contracts unchanged,
  `ARCH_GENERATION` still 5). CHANGELOG gains the 0.5.1 section and 0.5.0 loses its stale *(unreleased)* marker.
  WB7 image build dispatched from the tagged commit.

- **2026-07-10 — Bridge's echo-window fix (DRV-29 arc) verified on hardware: the AC command now reports an
  honest success.** The bridge side reported the fix implemented and redeployed; retest «включи кондиционер в
  детской» → `success: true`, «Включила Кондиционер», and the `device_command_echo` in the response carries the
  **confirmed** post-echo state (`power: on`, `mode: cool`, `setpoint: 20.0`, `room_temperature: 25.0`,
  `reachable: true`) — the bridge waited out the Mitsubishi's slow (~7 s) confirm cycle instead of 503-ing at
  500 ms. This closes the loop on yesterday's finding that every AC command reported failure while succeeding;
  the DRV-29 verdict/ledger flip is the bridge's own bookkeeping. Remaining DRV-28 smoke item unchanged: a mode
  change («кондиционер в детской на охлаждение» → `mode.set {value: cool}`) has still never been voice-tested.

- **2026-07-10 — First DRV-28 smoke on the WB7: the new dialect works end-to-end; the error the user heard was
  a timing artifact — bridge DRV-29 filed.** Both sides turned out to be redeployed already (voice and bridge
  each hold catalog `5622ba7a1a78102a`). «выключи кондиционер в детской» → voice resolved the room, picked the
  **new** `power` capability off the live catalog and posted `power.off` — QUAL-81's binding verified on
  hardware, and the AC's `/state` is fully typed now (`power/mode/fan/vane/widevane/setpoint/room_temperature`,
  `reachable: true`).
  The spoken answer, though, was «Что-то пошло не так на стороне моста» — and the timeline shows the command
  **worked**: command at `08:36:23.9`, the bridge's global 500 ms echo window (`CANONICAL_ECHO_TIMEOUT_S`)
  expired → `503 device_unreachable`, and the real echo arrived **~7 s later** (`08:36:31`), flipping the state
  to `power: off`. The mitsubishi2wb firmware confirms on its own cycle — seconds, not the milliseconds a WB
  relay takes — so **every AC command reports failure while succeeding**. Same signature as the 2026-07-09
  living-room attempt; systematic. Filed as bridge **DRV-29** (uncommitted; the filing notes that the previous
  uncommitted filing was silently erased, and points at this journal as the durable copy of the evidence).
  Two voice-side notes: BUG-40 made the message *worse* (the structured `device_unreachable` collapsed to
  «что-то пошло не так»), but even fixed it would speak a failure for a working command — the fix is genuinely
  bridge-side. And the mode-change path — dead firmware-side until their DRV-26, never voice-tested — is still
  the missing smoke item.

- **2026-07-10 — QUAL-81: the DRV-28 HVAC contract consumed — re-pin `5622ba7a1a78102a`, per-device dialect
  binding.** The bridge's overnight note: the three ACs are `MitsubishiHvac` now, six capabilities replacing
  `climate` (`power`, `mode`/`fan`/`vane`/`widevane` `.set{value}`, `temperature.set{value}` 16–31 °C); floors
  keep `climate`; canonical vocabularies and labels unchanged. Their DRV-26 also fixed what our 2026-07-09
  testing implied but nobody knew: the firmware speaks numeric indices and **silently dropped every mode/fan
  command ever sent** — the wire tables carried label strings.
  Verified before pinning (artifacts committed, golden's own version matches, exactly 3 devices changed), then
  consumed in both repos. eval-commons `ee66fd8`: golden+openapi+STAMP+PIN, fixtures migrated
  (F80/F81/F96/F32), and **F21 exposed a real schema gap** — the bare «поставь двадцать два градуса» clarify now
  spans candidates binding *different* capabilities (`climate` on the floor heater, `temperature` on the AC), so
  the clarify expect's `capability` accepts a list, guard updated, 40/40.
  Voice side: hardcoded `climate.set_setpoint`/`set_mode`/`set_fan` became a per-device **binding table** — new
  dialect first, old as fallback — because the WB7 bridge still serves the old vocabulary until its own
  redeploy, and deploy order must not matter. The capability picker takes an any-of tuple (F21's case).
  `_QUANTITY_FIELDS` deliberately unchanged: the sauna sensor still carries a genuine `temperature` field —
  and the audit found that pre-DRV-28, «какая температура» in an AC room had been answering the **setpoint**
  (the AC advertised `temperature` = its set target, first in our preference order); the rename retires that
  wrong answer with no voice change. Harness stub migrated to the new shape (all 47 tests pass against it),
  7 new tests incl. an old-dialect `children_split_legacy` proving the fallback — and **no mode/fan handler
  tests had existed at all**, the same blind spot as the firmware's. Suite 1373, pyright 0, 11/11.
  No action yet, logged: bridge VWB-32 (the 2026-07-09 controller reboot wiped all retained MQTT messages —
  mosquitto persistence is off — so `bridge/catalog/version` is missing until they republish at startup) and
  VWB-33 (language-data ownership convention design; half of it is our donations, they will coordinate).
  **Hardware smoke owed after their WB7 redeploy** — mode changes were never testable before DRV-26.

- **2026-07-09 — BUG-38 verified on the WB7; the retest immediately found BUG-40.** Deployed
  `v20260709-7b3e773`. The command that switched on the wrong lamp an hour earlier now refuses:
  «включи торшер в спальне» → `success: false`, «Спальня: не нашла там «торшер».», and
  `living_room_floor_lamp.power` stayed `off` across the call. «выключи кондиционер в гостиной» resolved to
  `living_room_hvac` with **no clarification** — the room did its work; «выключи кондиционер» with no room still
  reports the three-way ambiguity rather than guessing; and the group-noun path is untouched. Four properties,
  four commands.
  But the resolved HVAC command spoke «Что-то пошло не так на стороне моста», and that turned out to be ours.
  The bridge had answered precisely — `503`, `error.code = "device_unreachable"`, "No state echo within 500 ms"
  — **nested under FastAPI's `detail`**. `_to_delivery_result` reads `success`/`error`/`state` at the top level,
  so on any non-2xx it finds `{}`, logs *"bridge returned HTTP 503 without a structured error"* while printing
  the structured error, and stamps `internal_error`. The bridge raises
  `HTTPException(status_code=…, detail=resp.model_dump())` for **every** canonical failure, so the entire error
  taxonomy is dead: `err_capability`, `err_device_unreachable`, `err_device_not_found_bridge` are unreachable,
  and the `param_invalid` → one-shot clarification (QUAL-30/31, §5b) **can never have fired** against a real
  bridge. Filed **BUG-40** `[release]`.
  It survived because the tests encode the wrong assumption: every stub feeds a *string* detail
  (`{"detail": "boom"}`), never the dict-wrapped canonical envelope the bridge actually sends. A green suite
  proving the opposite of the truth — the same shape as this morning's `Success: 3, Failed: 0`.

- **2026-07-09 — BUG-38 fixed: the room the user names is king. Confirmed on hardware first.** With the owner's
  authorisation, the bug was reproduced on the WB7 rather than argued from code: the living-room floor lamp `off`,
  the bedroom holding no floor lamp at all, and «включи торшер в спальне» → `success: true`, «Включила Торшер»,
  `device_id: living_room_floor_lamp`, lamp `on`. Plain REST, no satellite, no client room. Lamp restored.
  Two holes, one root. `_result_from_candidates` narrowed by room only under `if len(candidates) > 1`, so a
  **uniquely-named** device skipped the room check entirely — and «торшер» is unique in this house. Separately,
  the device path never consumed the `uncovered_room` refusal the resolver already produces, so a satellite
  naming a room it does not cover would actuate anyway (D-15 rule 2b demands speech and *no actuation*). Lights
  had always worked only because «свет» is a group noun, routed to `_room_group`, which calls the D-15 pass that
  the device branch never called.
  Fixed in the resolver so every device-name path inherits it — power, cover, playback, `read_state`, and the
  `scan_utterance` path «на кухне вытяжку включи» takes. The **raw** room word is threaded down from
  `_resolve_single_entity`, not `room_resolved`: entity resolution walks `intent.entities` in donation order, so
  the sibling room may still be unresolved when the device resolves; matching the word at the point of use
  removes the ordering dependency entirely. Scoping now runs **always**, keeping `room == target` **or**
  `room == "global"` — 8 of 79 devices are whole-house aggregates the resolver already exempts, and a blanket
  filter would have broken «включи печь на кухне» (verified against the live golden). A named room holding no such
  device refuses, with a new template mirroring `err_no_group_in_room`'s shape so the room's nominative name needs
  no case agreement: «Спальня: не нашла там «Торшер».» Rule 3 is untouched — with no room spoken, the client's
  room narrows an ambiguity but never contradicts the user.
  Eight regression tests, all against the shapes that made this subtle: the refusal, unique-match scoping,
  spoken-room-beats-client-room, ambiguity dissolved by room, `global` survival, unknown-room fall-through,
  within-room ambiguity preserved (BUG-39's territory), rule 3 unchanged. pyright caught a real
  `room_id: str | None` hole in my first draft. Suite 1366 pass — the single failure is the TEST-20 flake,
  re-verified in isolation, not this diff. Needs a rebuild to reach the WB7.

- **2026-07-09 — DRV-23/DRV-25 verified live, both directions; then «включи кондиционер в гостиной» found
  BUG-38/39.** After the bridge redeploy, voice restarted and pulled `16eee0f2f7832995` (`mirrored` gone from
  `/state`). The full cycle now runs honestly on hardware: «включи свет» → relay `1`, `state.power = 'on'`;
  «какая температура» → `24.1875` read from the top level; «выключи свет» → relay `0`, `state.power = 'off'`,
  `status: "executed"` with no `skipped_reason`. The command I predicted this morning would silently no-op
  transmits correctly — for two reasons, both of which contradict my filing: their guard reads the right field,
  and the belief it reads is now true.
  Then the owner tried «включи кондиционер в гостиной» and got
  `«Какой именно: Кондиционер или Кондиционер или Кондиционер?»` — three candidates, the spoken room ignored.
  **BUG-38** `[release]`: lights work only because «свет» is a *group noun*, routed to `_room_group`, which calls
  `_requested_room()` — "the D-15 pass". The named-device branch never calls it; ambiguity is decided upstream in
  `entity_resolver._result_from_candidates`, whose sole narrowing is `resolve_default_room(context, catalog)`,
  documented in its own docstring as *"D-15 rule 3: no room mentioned → the client's primary room"*. Only rule 3
  exists. The disambiguator asks which room the *speaker* is in, never which room the speaker *named*.
  The REST symptom is the benign one. On a satellite with a primary room the same code **silently actuates the
  wrong room**: from the living room, «включи кондиционер в спальне» narrows to the speaker's room, switches on
  `living_room_hvac`, and answers «Включила кондиционер» — while D-15 rule 2 demands the named room, or a spoken
  refusal and *no actuation*. Nothing compares the spoken room to `catalog_device.room` on that branch. Latent
  purely because every test so far went through REST, which carries no client room. Hence `[release]`: it blocks
  the next tag and any satellite deployment.
  **BUG-39** `[deferred]`: the clarification cannot be answered — all three devices are named «Кондиционер», and
  `_ambiguous_result` builds the prompt from `name` alone though the payloads carry `room`. It survives BUG-38's
  fix, because two sconces in one room still collide.

- **2026-07-09 — QUAL-80: golden re-pinned `8159b4b0…` → `16eee0f2f7832995`, and the loop closes.** The bridge
  asked for the re-pin; both driving fixes were caused by our WB7 testing. **DRV-23** — WB-passthrough devices
  now expose feedback at top-level `state.<field>`, exactly the read path we depend on, and the `mirrored` bucket
  is retired. **DRV-25** — `power` becomes a *readable* field on the 39 relay-switch devices, canonical
  `on`/`off`. That is our own «какая температура» failure and our own `state.power = 'off'` observation, returning
  as a contract change.
  Verified rather than trusted before pinning: the golden's own `version` is `16eee0f2f7832995`; **39 of 79**
  devices changed, each gaining a `fields` entry on `power` (enum, wire `"1"/"0"` → canonical `"on"/"off"`, ru/en
  labels); no devices added or removed; zero `mirrored` occurrences; `openapi.json` byte-identical, so it was not
  re-copied and config-ui's generated types are untouched. One-way inward sync; `PIN.bridge_commit` mirrors
  `STAMP.bridge_commit` (`9714c3c3…`), never the repo HEAD (`cc5d4b4`) — the convention QUAL-75 once broke and
  `test_pin_matches_stamp` now guards. eval-commons `5427063`: 40/40, pin guards 10/10. Voice-side `parse_catalog`
  reads the new shape; unit suite 1358 pass; purely additive, since `_QUANTITY_FIELDS` still searches only
  `temperature`/`humidity`.
  Two corrections to yesterday's record, both against us. The bridge **disproved the write-path half** of our
  DRV-23 filing with an on→off→off repro: their idempotence guard reads `state.mirrored` directly, and
  `skipped_reason: "idempotence"` is DRV-5's AV-driver helper, not this driver. We had inferred it from reading
  and never executed it. And the claim that voice *needs* readable `power` was overstated: `read_state`'s
  `quantity` is a `choice` of `temperature`/`humidity` only, QUAL-68 reads `level`/`setpoint`, and ARCH-39 reads
  the canonical command **response** (`no_op`, `skipped_reason`), never believed state. DRV-25 gives us the field
  anyway, which unblocks a future spoken «свет включён?» — but we did not need it, and said so.
  **Not live yet:** the WB7 serves the old catalog until the bridge image is rebuilt and redeployed. A sensor
  read and a switch read want re-verifying against the controller afterwards.
  Process note: our DRV-23 filing was **erased** from the bridge's working tree — not in `HEAD`, not on disk.
  They independently took the ID, verified, reframed and fixed it, so nothing was lost in substance. But an
  uncommitted cross-repo artifact evaporated silently, which is BUILD-20 D-5's board-as-outbox argument with a
  real incident behind it instead of a hypothetical.

- **2026-07-09 — The bridge fixed DRV-23; sensor questions answer, and immediately expose BUG-37.** «какая
  температура в кабинете» now returns `success: true`, `room_temperature = 24.125`, «Сейчас 24.125 градусов —
  Тёплый пол». The bridge projects its mirrored fields to the top level, and voice reads `state.<field>` per the
  ARCH-8 contract, unchanged. The **`power` half of DRV-23 is not yet confirmed**: belief, `mirrored` and the
  relay topic all read `off/0/0` right now, and a consistent state proves only that nothing contradicts — it
  takes a toggle to prove the projection.
  What the working read path revealed is ours. The sentence a user would *hear* is
  «Сейчас двадцать четыре двенадцать градусов»: (a) the handler only narrows integral floats, so `24.125` reaches
  the template raw; (b) `all_num_to_text` renders a fraction as a second whole number and drops digits
  (`24.5 → «двадцать четыре пятьдесят»`, `2.75 → «два семьдесят пять»`) — a **general** text-processing defect,
  not a temperature one; (c) the template hardcodes «градусов», so `1 → «один градусов»` and `24 → «двадцать
  четыре градусов»` (English `"1 degrees"` likewise). Filed as **BUG-37** `[deferred]`.
  The pattern is by now familiar: this has been broken since the read path was written, and no gate could see it
  because the path never returned a value — the bug needed a *working* dependency to become visible. Today's
  score for "found only by running the real thing on real hardware" stands at eight.

- **2026-07-09 — Answered the bridge's DRV-23 question, and the answer is worse than either side assumed.** They
  asked which field Irene reads — `state.power` or `mirrored.power` — since that decides whether their
  state/mirror decoupling is a live integration bug or cosmetic. **Irene reads the top-level field; `mirrored`
  does not appear anywhere in the voice codebase.** `outputs/bridge.py:230` unwraps `payload.get("state")` and
  falls back to the whole flat payload; `smart_home.py:631` then does `state.get(field_name)` by the name the
  catalog advertises.
  So: live, not cosmetic — and the **read** path is hit harder than the idempotence path we started from. Voice
  only reads `temperature`/`humidity` today (`_QUANTITY_FIELDS`), never `power` — but on exactly the devices
  carrying those fields, the values live *only* inside `mirrored`: `cabinet_floor` reports top-level
  `{"power": "off"}` with `mirrored {"room_temperature": 24.125, …}`. Run end-to-end on the box, «какая
  температура в кабинете» returns `success: false`,
  `error: "state read failed for cabinet_floor.room_temperature"`, and Irene says «Не уверена, что получилось» —
  while the number sits in `mirrored`. **Every spoken sensor question is broken on those devices**, independently
  of the `power` idempotence skip. Both findings, and the answer, are in the bridge's DRV-23 (uncommitted).
  Voice will keep reading top-level `state.<field>`: that is the ARCH-8 contract (`mqtt_integration.md` §5c) and
  `mirrored` is not part of it. Whether the projection is missing or `mirrored` is secretly authoritative, the
  fix is bridge-side; we changed nothing here.
  Filed **QUAL-79** `[deferred]` from the same session: the `confidence` in every intent-result response is a
  success flag, not a confidence. Only 4 of 120 `IntentResult(...)` constructions set it (`1.0` success / `0.0`
  error in `handlers/base.py`); the rest take the `1.0` default, and the canonical serializer publishes that.
  The recognition confidence — the number the cascade gates on — never reaches a client: «включи свет» was
  recognized at **0.76** against a 0.70 threshold while the response claimed `1.0`. And the failed read-state
  reply above *also* reported `confidence: 1.0` alongside `success: false`, so it is not even reliably the flag
  it duplicates. QUAL-55 canonicalized where the field sits without asking what it means.

- **2026-07-09 — «включи свет в кабинете» → the light came on. Text in, photons out.** BUILD-27 landed and the
  assistant actuated real hardware for the first time: `smart_home.power_on` recognized by
  `hybrid_keyword_matcher` (0.76), «кабинет» resolved against the freshly-pulled catalog to `cabinet_spots`, a
  canonical `DeviceCommand` crossed the ARCH-8 boundary to the bridge, the relay closed, and the lamp in the
  owner's office lit up. Confirmed against ground truth, not just the API's word: the retained MQTT topic
  `/devices/wb-mr6c_51/controls/K4` reads `1`, and the owner looked.
  Getting there needed the networking fix. `[outputs.bridge] enabled = false` in every embedded profile, so the
  catalog was never fetched — and flipping the flag alone would have failed, because under our `ports:` mapping
  `base_url = "http://localhost:8000"` pointed at the *container*, not the controller (verified from inside:
  `127.0.0.1:8000` refused, gateway `172.17.0.1:8000` → 200). The bridge's compose already used
  `network_mode: host` — it must, to reach mosquitto on `localhost:1883` — so ours was the odd one out. Voice
  now shares the host network, the shipped config line became true as written, and the catalog loaded:
  `version (none) -> 8159b4b0068d1c63, 79 devices / 11 rooms` — **the same catalog_version pinned in
  eval-commons**, so voice, bridge and the test contract demonstrably agree on the device model.
  **The command also found a bridge bug.** `GET /devices/cabinet_spots/state` returns `"power": "off"` while
  `"mirrored": {"power": "1"}` and the relay is physically on — stable across reads, not a lag. The bridge sees
  the raw feedback but never maps `state_topics.power` into the believed capability value. Consequence: DRV-5's
  idempotence guard compares desired against *believed*, so «выключи свет» on a lit lamp would compare `off` vs
  believed `off`, transmit nothing, return `skipped_reason: "idempotence"`, and leave the light on while every
  client reports success. Filed as bridge **DRV-23** (uncommitted, `cross-repo-source-of-truth`). It is the
  belief-may-be-wrong scenario DRV-5 documents — reproduced on a **two-way** device, where the belief should
  never have been wrong. It also hands **ARCH-39** its first real motivating case.
  Startup ordering, raised by the owner, is filed as **BUILD-28** `[deferred]`: three containers, two compose
  projects, no `depends_on` — voice races the bridge for the catalog and leans on the ARCH-26 lazy refresh when
  it loses. The permanent answer spans both repos and belongs on the commons PROD board, not here.

- **2026-07-09 — REL-4: the version stops lying. `15.0.0` → `0.5.0`.** The owner's objection was exact: `15.0.0`
  claims a fifteenth major release, and there was never a first. The only tags this repo ever carried are `8.1`
  (inherited 2023 upstream history) and `v12-final`. His scheme — major `0` because the API is not frozen, minor
  `5` because it is the fifth design generation — turns out to fit 0.x semver rather than fight it: under 0.x the
  *minor* is the breaking axis, which is exactly where a new design generation belongs. The third part of the
  idea, patch = "15th iteration overall", was the one thing that could not survive: patch's only job is counting
  backwards-compatible fixes, and the first bugfix would have destroyed the meaning. That fact now lives in prose
  (CHANGELOG + `__version__.py`), where a reader understands it and no resolver misreads it.
  The change also improved the code. `MAJOR_VERSION` never meant "package major" — it printed `V15 Components`,
  the *architecture generation* — so it became an explicit `ARCH_GENERATION = 5`, no longer derived from the
  version. The log now reads `V5 Components`, which is what it always meant.
  Two dividends from looking rather than assuming. **The 13 configs' `version = "15.0.0"` lines were deleted, not
  updated**: `CoreConfig.version` already defaults to `__version__`, so they were unvalidated copies that could
  only drift — and `configs/config-example.md` proved it, still carrying `14.0.0`, a whole major behind. And
  regenerating `config-ui/openapi.json` revealed the committed artifact was **stale**: four schemas
  (`BridgeOutputConfig`, `ReportsConfig`, `SatelliteConfig`, `SatelliteTLSConfig`) had been added to the API and
  never re-dumped, so config-ui has been type-checking against an old backend. Nothing in CI regenerates it →
  **BUILD-26** `[deferred]`.
  Cross-repo cost was zero, as estimated: the bridge never reads our version (its `15` hits are a lockfile
  `node` engines range and a slice number), eval-commons stamps only `bridge_version`. The single stale claim —
  D-11's "voice 15.x" — was corrected in `productization.md`. I had earlier argued that D-11 "already decided
  15.x cross-repo"; reading it, that was a parenthetical describing the status quo, not a constraint anything
  builds against, and I withdrew the argument. Verified live: `/health` → `"version":"0.5.0"`,
  `openapi.info.version` = `0.5.0`, startup logs `V5 Components`, all 14 configs parse and inherit it.
  pyright 0, import-linter 11/11, 1358 tests, config-ui check + build green.

- **2026-07-09 — ARCH-25 DONE: the WB7 is up, and the reboot test passed. Scope is complete.** The controller
  boots the `embedded-armv7` image from `/mnt/data`, downloads and loads sherpa-onnx ASR (26 MB) + Piper irina
  (79 MB), and answers a live Russian command — «который час» → «11:35», `datetime.current_time`, confidence 1.0.
  Then the acceptance criterion, cold: `uptime` 3 min, unit `enabled`/`active`, `Result=success`, `NRestarts=0`,
  **zero** dependency failures, no `/mnt/sdcard` anywhere in the boot transaction, container `(healthy)`, compose
  re-read `.env` at boot, `Requested: 9, Running: 9, Missing: 0, Failed: 0`, `/health` 200 with
  `inactive_providers: {}`, and Plane B back unaided (`:8081` → 200, `:443` no-cert → 400). This is precisely the
  failure the bridge hit live and that BUILD-19 designed around blind; it held.
  Worth stating plainly: **the bring-up found six defects that every gate we own had missed** — BUG-31, BUG-32,
  BUG-33, BUG-34, BUG-35, BUG-36 — because every one of those gates runs on x86_64 and the box is armv7. Two of
  them (no ASR at all; the process reporting that as healthy) would have shipped in the release tag. The build
  gate added in BUG-36 now runs inside each image on its own architecture, which closes that hole for the next
  one. With ARCH-25 closed, `check_scope.py` reports **no open `[release]` tasks** — 25 remain, all `[deferred]`.
  Only the version tag stands between here and release; the number itself is under discussion.

- **2026-07-09 — BUG-36 fixed: a broken assistant can no longer report itself healthy.** Four independently
  "graceful" decisions composed into the lie. The loader logged an ImportError at WARNING and dropped it. The
  component manager built its enabled set by iterating **what loaded** and filtering by config — so a component
  you enabled that failed to import was neither initialized nor failed, it was absent from the universe.
  `_failed_components` only ever saw components that were discovered and then raised, so `Failed:` structurally
  could not be non-zero. And `get_deployment_profile()` counted the *config*, so the line printed intent (6)
  beside reality (3). Even `run_startup_validation` was no help: it resolves entry-point **names** in package
  metadata, which succeeds whether or not the module imports.
  Now the config is the authority: anything `[components]` names that did not load is recorded with the loader's
  reason (the loader returns its failures instead of only logging them), the summary reads
  `Requested / Running / Missing / Failed to initialize` at ERROR, and a missing component **aborts startup** —
  unless it is one of the observability surfaces (`monitoring`, `nlu_analysis`, `configuration`), which degrade
  and force `/health` to 503 so Docker and systemd see it.
  At the provider level the owner ruled that a configured provider which doesn't come up means the component
  isn't ready. Implementing that surfaced a real conflict, and **running the change is what found it**: strict
  everywhere refused to boot the keyless smoke suite — i.e. it would have bricked any controller without a
  DeepSeek key, breaking the offline promise `INSTALL.md` makes and that `fallback_providers = ["console"]`
  exists for. So the rule split by failure kind, with the owner's agreement: **cannot import** (no entry point,
  or `libopenblas.so.0`) is a broken build → fatal; **imports but reports unavailable** (no API key, no network)
  is anticipated → logged at ERROR and published on `/health.inactive_providers`, loud but never fatal.
  Two more silences died on the way: `llm_component` swallowed its own initialization exception and merely
  warned "No LLM providers available"; and `asr` reconciled its default to *whatever survived* (CR-A2), quietly
  transcribing with an engine nobody chose. Finally, a **build gate** (`docker/verify_components.py`, wired into
  all three Dockerfiles) now imports every component and provider the baked profile enables, in that image, on
  that architecture. It would have caught BUG-33 before publish — every other gate we own runs on x86_64, where
  numpy vendors its own openblas. Verified live both ways: keyless boot → 200 with
  `inactive_providers: {llm.deepseek: …}`; a bogus configured provider → exit 1 naming it. 1358 tests pass,
  including the six hermetic smoke tests that started this.

- **2026-07-09 — BUG-35 fixed: the runners stop overwriting `[components]`; TEST-20 filed.** `webapi_runner`
  rewrote eight of the eleven `[components]` flags immediately after the TOML loaded, and `--enable-tts` was
  `action="store_true", default=True` — a flag that can never be False, so TTS and the audio component were
  hardcoded on by something that looked configurable. That is why `embedded-armv7`'s `audio = false` ("no local
  speaker") ran the audio component anyway. Only `audio` *visibly* diverged by luck: the embedded profiles happen
  to set every other overridden flag to exactly what the runner forced. The rest of the damage was invisible —
  no text-only deployment (ASR forced on, paying sherpa's ~38 s graph init), no server-side wake word, no way to
  drop monitoring, and `[components]` a lie in config-master.toml and config-ui.
  The sharpest detail: **each runner's own validator was unreachable.** It runs at `base.py:311`, *after* the
  override at `:282` has set every value it checks — so `intent_system must be enabled` could never fire. The
  code that would have caught a bad config was disabled by the code that made configs meaningless.
  `io_architecture.md` sanctions `CLI flags > runner preset > config file`, but scopes the preset to an
  input-set + output-set; component enablement was never in its remit. So: presets force only input topology,
  `--enable-tts`/`--no-tts` is a real tri-state that defers to the file when unset, and structural requirements
  became live validation that refuses to start naming the key. `voice_runner` got the same treatment;
  `satellite_runner` was left alone (it forces components *off* — deny-by-default for a thin device).
  Verified against the real profiles rather than fixtures: `embedded-armv7` under webapi now reports
  `runner-changed components: NONE — config honoured`, `audio=False`; `--no-tts` overrides; `standalone-x86_64`
  validates clean; each disabled requirement now errors. `test_voice_runner.py` asserted the old forcing and was
  rewritten to the new contract. While running the suite a failure appeared, was **checked against a stashed
  tree rather than blamed on the diff**, and turned out to be a pre-existing flake (3/8 on clean HEAD) —
  filed as **TEST-20** `[deferred]`.

- **2026-07-09 — BUG-33 + BUG-34 fixed: numpy is no longer a base dependency.** The owner chose Option B over
  shipping `libopenblas0`: rather than adding a 10 MiB system library so a broken PiWheels numpy can import on a
  board that never calls it, numpy stops being a base dependency and moves into the extras of the providers that
  actually import it — `wake-onnx`, `nlu-spacy`, `audio-sounddevice`, `audio-miniaudio`, `audio-output`,
  `tts-silero`, plus new `vad-energy` / `vad-silero`. Those last two exist precisely because the silero VAD
  reuses `asr-onnx`, and `asr-onnx` is what the armv7 image installs for sherpa — folding numpy in there would
  have put a PiWheels numpy straight back on the board. `providers/vad/{energy,silero}.py` declare the new
  extras, so the **dynamic build picks it up with no new machinery**: `build_analyzer --config
  embedded-armv7.toml` now resolves to `['asr-onnx', 'llm-openai', 'web-api']`, numpy absent, `libopenblas`
  unnecessary anywhere. This is what the code always intended — both armv7-critical providers were written
  numpy-free on purpose, and their comments (*"armv7 has no numpy wheel"*) were simply wrong; PiWheels ships one,
  and that wrong belief is why nobody declared its system library.
  BUG-34 fixed alongside, because with numpy *absent* rather than merely broken the eager imports would fail
  harder. Two layers: the package `__init__`s of `components/` and `providers/{asr,audio,nlu,voice_trigger}/`
  now import only their ABC and expose concrete classes via a PEP-562 `__getattr__` (the shape
  `providers/vad/__init__.py` already had), so importing one component no longer imports the other eight; and
  the three module-scope numpy imports are guarded, failing with the name of the extra to install instead of an
  `AttributeError` on `None`. The one unguarded numpy call site on the live audio path,
  `audio_negotiator._downmix_to_mono`, was rewritten with stdlib `array` and checked bit-identical to the numpy
  version across 900 random multi-channel buffers (`int(x/ch)`, not `x//ch` — numpy truncates toward zero).
  Verified by importing every component and the runner against a fake `numpy` that raises `ImportError`: all
  import with numpy absent, all still work with it present. pyright 0 errors — the annotations became an
  `NDArray = Any` alias, since `no-type-checking` rules out a `TYPE_CHECKING` import. import-linter 11/11,
  27 VAD/resampling tests green, `uv lock` refreshed. BUG-35 (runner overwrites `[components]`) and BUG-36
  (nine failures reported as `Success: 3, Failed: 0`) remain open — the second one is why this shipped at all.

- **2026-07-09 — The WB7 assistant has no ASR: BUG-33/34/35/36 filed.** The owner noticed the piper voice
  downloaded but no ASR model ever did. It is not a config problem — the delivered `irene.toml` is read
  correctly. `libopenblas.so.0` is absent from the armv7 image, numpy cannot import, and **nine of twelve
  components die**: asr, nlu, intent_system, text_processor, configuration, monitoring, nlu_analysis,
  voice_trigger, unified_voice_assistant. The assistant on the rack can synthesize speech and call an LLM, and
  can neither hear nor understand.
  Chain, established with a throwaway container on the box (`--rm`, production container untouched):
  **(1) BUG-33** — numpy on armv7 comes from **PiWheels** (`Tag: cp311-cp311-linux_armv7l`), which links the
  *system* openblas and ships no `numpy.libs/`; PyPI's manylinux wheels bundle it (the aarch64 image carries
  `numpy.libs/libopenblas64_…so`, so it is **not** affected). Nothing declares the dep: `derive_build_reqs.py`
  derives runtime packages from *provider-declared* system packages, and this is a transitive C dep of a wheel.
  `apt-get install libopenblas0` in a scratch container makes numpy, sherpa_onnx and all five probed components
  import. **(2) BUG-34** — the blast radius: `components/__init__.py` eagerly imports every component, and line 8
  drags in `openwakeword.py`'s module-scope `import numpy` for a provider this profile **disables**. Survivors
  (tts/asr/llm/audio, lines 4–7) live only because they were already in `sys.modules`; everything past line 8
  dies. The providers themselves lazy-import correctly — `tts/piper.py` imports `sherpa_onnx` inside a method,
  which is exactly why **Piper TTS kept working while ASR did not** (sherpa_onnx itself imports fine without
  openblas; it was never the problem). **(3) BUG-35** — the owner asked why `audio` initialized when the profile
  says `audio = false`: `webapi_runner._modify_config_for_runner` overwrites the whole `[components]` block
  after the TOML loads (`config.components.audio = args.enable_tts`, `asr = True`, …). Forcing web-only *input*
  is this runner's job; silently overriding component enablement defeats repo-owns-config. **(4) BUG-36** — the
  worst part: after nine import failures the runner logged `Success: 3, Failed: 0`, then
  `all configured provider names resolve to registered entry-points ✓`, then `Irene started successfully`, exit
  0, `/health` 200, Docker `healthy`. Nothing failed loudly. `Failed: 0` counts components that failed to
  *initialize*, not ones never discovered.
  Fix shape for BUG-33 deferred to the owner ("let's do the numpy fix clean"). Investigation only — no code
  touched, the running container left as it was.

- **2026-07-09 — Irene is running on the WB7; ARCH-45 + QUAL-78 filed from the first boot.** The container came
  up `healthy` on `v20260709-7224ff7`, secrets present, models downloading. The owner asked why the bridge logs
  a uvicorn banner immediately and Irene does not: the runners initialize in opposite order. Irene does
  `core.start()` **first** (`base.py:117`), then builds the FastAPI app (`_post_core_setup`, :127) and only then
  runs `uvicorn.serve()` (`_execute_runner_logic`, :130) — the banner appeared ~8 s in. `wb-api` does the
  inverse, booting uvicorn and initializing devices inside FastAPI's lifespan. Neither is wrong; Irene's
  endpoints operate *on* the core, so it has nothing to serve until the core exists.
  The first boot's timeline corrected an assumption baked into today's healthcheck: **model downloads are not on
  the startup path.** TTS reports `lazy loading: True` and the piper voice only begins downloading at
  `09:15:39`, after uvicorn is already answering — which is why `/health` returned 200 throughout and the
  container went healthy in ~2 min, not the 300 s the start-period allows. That grace is generous, not
  necessary. It also exposed that **`healthy` does not mean ready**: `/health` is a static string, so the
  container advertises health while it cannot yet speak → **ARCH-45** `[deferred]` (design a readiness signal;
  revisit the start-period once it exists). And the probe now access-logs a line every 30 s forever →
  **QUAL-78** `[deferred]` (filter 2xx `/health` off `uvicorn.access`, keep failures).
  Confirmed for the reboot test: the `.env` written after the first `update.sh` was picked up on the container's
  recreate (both variables present inside it), and the unit's `WorkingDirectory` is the runtime tree, so compose
  reads that same `.env` at every boot.

- **2026-07-09 — BUILD-25: config-ui runs non-root, and its healthcheck could never have passed.** The owner
  noticed the UI image was the last one still building as root — not controller-deployed, but published and run
  on workstations against the assistant's API. Dropped it to the base image's `nginx` user (uid 101); nothing
  needed uid 0 since nginx binds 3000 and the entrypoint only writes inside the html root. The real risk was the
  official nginx entrypoint, whose behaviour changes for uid≠0 — if `/docker-entrypoint.d/40-runtime-config.sh`
  had stopped running, the app would have silently fallen back to a default API base rather than failing. Built
  and ran it to check: the hook executes, `runtime-config.js` is written both with and without `API_BASE_URL`.
  **Verification then turned up a latent BUILD-9 bug:** the healthcheck probed `http://localhost:3000/`, but
  `listen 3000` binds IPv4 only, musl resolves `localhost` to `::1` first, and busybox wget does not fall back —
  `wget` inside the container got *connection refused* from a server serving 200 to the outside. Every config-ui
  container ever published would have sat `unhealthy` forever. Fixed to `127.0.0.1` (what the bridge's UI always
  used); Docker now reports `healthy`. Two stale comments went with it (`:6000` → 8080; "compose ships it
  disabled" → the service was removed). **Third image-level defect today found only by running the artifact
  rather than reading it** — after BUG-31/32 on the ansible plane. The pattern is now unambiguous: anything
  hardware- or deploy-gated in this repo has never been executed, and reading it does not substitute.

- **2026-07-09 — ARCH-25 pre-flight: the install guide audited against the box, three defects fixed.** Before
  running the container install, `ops/INSTALL.md` was checked claim-by-claim against the scripts and the live
  controller. Most of it held (layout, `update.sh` working from either invocation, public clone + all four public
  GHCR packages, `/health` prefix-less on 8080, `.env` semantics, `rsync`/`git`/`docker` compose v2.38.2 present).
  Three things did not:
  **(1) The healthcheck was a lie.** All three Dockerfiles ran `CMD python -c "import irene"` — green as soon as
  the interpreter starts, regardless of whether the API bound, the config parsed, or the runner died, with
  `--start-period=10s`. Replaced with a real probe of `http://127.0.0.1:8080/health` (both runners mount it at
  root via `WebServerMixin`) and a start-period that survives first-boot model downloads: 300s on the two ARM
  images, 180s on x86_64. Modeled on the bridge's `backend/Dockerfile` (180s + a real urlopen), which is where
  the owner remembered the slow-start tuning from.
  **(2) Rolling back / Variants told you to do the wrong thing.** "Pin it in `docker-compose.yml` and run
  `docker compose up -d`" names neither copy: pinning the *deployed* copy is reverted by the next `update.sh`
  (`cp docker-compose.yml "$RUNTIME_DIR/"`), and running compose from the clone's `ops/` starts a **second
  project named `ops`** with no `.env` (compose names projects after the directory — verified on the box:
  the bridge runs as project `mqtt-bridge-config`). Both rules now stated explicitly.
  **(3) `CONFIG_PROFILE` did not stick.** One plain `./update.sh` on a WB8.5 would re-deliver the armv7 profile
  over `irene.toml`, undetected. It is now recorded in `<runtime>/config-profile` on first use and reused after;
  an unknown name exits 2. Validation happens *before* recording — the first cut wrote the bad value first, so a
  typo would have poisoned every later run; caught by exercising it against a scratch runtime tree.
  Also: the container user is now **`domovoy`** (uid 1000 unchanged — the uid is the contract that crosses the
  bind mount; the name tracks the product and changes with the final name decision), and `build-docker.md` lost
  its last stale port-6000 reference. Non-root is deliberate and stays: the bridge's root container is the
  outlier, not us. Fixes ride under ARCH-25 (owner's scoping); the image must be rebuilt for the healthcheck to
  take effect, so the install tag moves off `v20260708-86d0134`.

- **2026-07-09 — Plane B proven end-to-end on the WB7; ARCH-44 filed from what the round-trip exposed.** The
  owner ran the full provisioning flow against the live controller: CSR `PUT` → **201**, `esp32-provision list`
  shows subject + pubkey fingerprint, `approve` signs and consumes the CSR, the device poll flips **404 → 200**,
  and the issued cert opens the mTLS zone — `:443 /esp32/models/` returns **403** with the client cert (handshake
  accepted, directory listing refused) against **400** without one. Cert carries `CA:FALSE` +
  `TLS Web Client Authentication`; its public key matches the device key. Every claim in `nginx/README.md` about
  the happy path now has evidence behind it.
  **What the exercise exposed:** the plane can issue device certs but never withdraw them. `revoke` only deletes
  a *pending* CSR; after `approve` the cert is trusted for its full 825 days, because the mTLS zone verifies
  against the CA with no CRL — and deleting the published `.crt` is meaningless, the device already has it. No
  renewal story either: a batch provisioned together expires together. Filed **ARCH-44** `[deferred]` (design:
  revocation + renewal, and a verb naming that distinguishes *drop a pending CSR* from *revoke an issued cert*).
  The README's safety section now states the limit plainly instead of implying `revoke` withdraws access.

- **2026-07-09 — BUG-32: the approval CLI installed under a name nothing documents.** The owner ran the
  bootstrap round-trip on the box: the device CSR `PUT` to `:8081` returned **201** (WebDAV path proven), and
  then `esp32-provision list` → `команда не найдена`. The play copied all three scripts verbatim, so the CLI was
  `esp32-provision.sh`, while the README, D-17 and the script's own `usage()` say `esp32-provision`. Approving a
  CSR is the only way this plane is ever used, so the documented runbook was unrunnable. The operator CLI now
  installs without the extension (the two helpers keep `.sh` — both are called by absolute path), plus a
  `state: absent` sweep of the old name. Re-ran: `changed=2`, CA untouched under its `creates:` guard,
  `esp32-provision list` prints the pending CSR + pubkey fingerprint. **Same root cause as BUG-31, minutes
  apart: the playbook had never been run end-to-end against a real controller** — ARCH-22 shipped it
  hardware-gated, and hardware gating hides exactly this class of defect. Worth remembering when BUILD-13 (Pi
  image) and the satellite repo's own ops land.

- **2026-07-09 — Plane B is live on the WB7; BUG-31 filed + fixed on the way in.** Installed the ESP32
  fleet-provisioning plane (ARCH-22 Plane B, `nginx/ansible`) on the controller. Pre-flight found `:443` and
  `:8081` free, `nginx-extras` present with `--with-http_dav_module`, no CA — but also that the playbook's
  opening `apt: name=[nginx, openssl] state=present` was a live grenade: the box has no `nginx` metapackage, so
  apt would have resolved it and upgraded the very nginx serving the Wirenboard admin UI (simulated: nginx-extras
  deb11u5→u8 + openssl + five module packages). Filed **BUG-31** before touching code, replaced the apt task with
  a probe + `assert` (also asserting the WebDAV module the CSR `PUT` needs — `nginx-light` would have failed only
  at runtime), and the `--check` dry run promptly caught that `command` is skipped under check mode, so the probe
  needed `check_mode: false`. Deploy then ran clean (7 changed, 0 failed). Verified: packages still deb11u5,
  admin UI `:80` → 200, `:8081` `ca.crt` → 200 (CN=HomeVoice ESP32 CA, 10y), `:8081/` → 404, `:443` without a
  client cert → 400, CA key `600`. Server cert issued **CN=192.168.110.250** with
  `IP:192.168.110.250, DNS:wirenboard-AF3TQCCE, DNS:assistant.lan` — there is no LAN DNS on this network (neither
  `wb7` nor `assistant.lan` resolves, the box calls itself `wirenboard-AF3TQCCE`), which is exactly the DNS-less
  bootstrap case ARCH-41's dedicated port exists for. Irene's `/ws/` is proxied from `127.0.0.1:8080` behind mTLS,
  ready for the container that isn't deployed yet. The full CSR→approve→mTLS round-trip is **left for the owner**
  to run: agent-driven cert signing on the production CA was (correctly) refused by the permission classifier.

- **2026-07-08 — BUILD-20 DONE (filed + completed same day) — the joint productization design session:
  the product is called Domovoy.** Run from `~/development` with both repos' CLAUDE.md + memory loaded,
  acting as both projects' Claude — the session the release-endgame memory anticipated. Six topics +
  three follow-up rounds, all user-decided; deliverable `docs/design/productization.md` (D-1..D-12).
  The shape: **one** umbrella repo — eval-commons repurposed + renamed `domovoy-commons` (no new
  commons sprawl; three ownership regimes keep contract pins / co-owned code / process artifacts from
  blurring; per-package prefixed tags) — plus a **third product repo `domovoy-satellite`** starting now
  (ESP32 design corpus relocates out of this repo; the top-level `ESP32/` tree ruled outdated and slated
  for deletion, not migration; the WS protocol doc STAYS here — satellite pins it like voice pins the
  bridge catalog). Cross-repo ideas get the `design-then-implement` discipline lifted a level: PROD
  design tasks in the commons board, delegation entries committed there ("the board entry IS the
  outbox" — retires the fragile uncommitted sibling filings; this session's own bridge filings are the
  deliberate last use of the old way). Coordination stays on the per-repo ledgers (GitHub
  Projects/Jira explicitly rejected — the ledgers' in-context/greppable/machine-guarded properties are
  the point); releases = per-component semver + calver "Domovoy 2026.xx" compatibility manifests gated
  on the eval cross-suites; the contract re-pin becomes scripted + machine-checked (D-11). BUILD-18's
  drift inventory is now recorded evidence (design §2 — including a correction: journal direction is
  NOT drift, both repos are newest-on-top). Housekeeping verified in passing: the contracts re-pin to
  bridge golden `8159b4b0068d1c63` has already landed (STAMP matches — the bridge-side "voice must
  re-pin" note was stale). Filed: BUILD-21 (commons bootstrap), BUILD-22 (satellite bootstrap +
  relocation), BUILD-23 (invariant blocks + drift guard), BUILD-24 (scripted re-pin + staleness gate),
  ARCH-42 (loader extraction design), ARCH-43 (logging extraction design); BUILD-18 narrowed; bridge
  intake (uncommitted): VWB-29, CORE-7, OPS-14/15/16 + `productization_bridge.md`.

- **2026-07-08 — ARCH-41 DONE (same-day pull-forward, interactive) — Plane-B ports settled without
  touching a single client line.** The discussion opened with recon that reframed the filed problem:
  the WB admin UI turns out to be served by the controller's SYSTEM nginx on `:80` (user's live
  `ss`), and our ansible role deploys into that same nginx — so the collision was routing, not
  binding: our `:80` block claims the bare IP and would steal `http://<ip>/` from the admin UI,
  while dropping the IP would break DNS-less bootstrap. Decision (user-approved): the bootstrap
  zone gets a dedicated `:8081`, mTLS keeps the verified-free `:443`, both as ansible variables
  with `default()` fallbacks. The S-7 hermetic e2e lost its port-replace hack (it now renders the
  vars directly — "no test-plumbing deviation left") and stayed green along with the full satellite
  suite; `bootstrap_url`/`server_url` being full URLs meant zero code changes. Docs swept end to
  end, including a deploy pre-flight `ss` check in the nginx README. ESP32 firmware doesn't exist
  yet — this was the last free moment to move the ports.

- **2026-07-08 — BUILD-19 DONE + ARCH-41 filed — the bridge's reboot lesson landed here before it
  could hurt.** The bridge's compose cutover failed its reboot test today: their unit was rooted on
  the SD card, which is a lazy automount — the hard mount requirement dragged the card's fsck into
  early boot, the chain failed before the slow device enumerated, and oneshot never retries. Their
  note ("has that service ever survived an actual reboot, or only compose restarts?") had a clean
  answer for voice: never deployed, zero exposure — we fixed the identical flaw between image
  publish and first install. Voice now follows their `e88aa84` rule: the clone is an update-time
  artifact; `update.sh` deploys the compose file into the runtime tree and runs compose from there;
  the unit references only `/mnt/data`; `.env` lives next to the deployed compose; the unit file is
  copied (not symlinked) into `/etc/systemd/system` — our INSTALL's `ln -s` onto the card was its
  own boot-time landmine. Their verified port map also exposed that Plane-B nginx wants `:80`
  where the WB admin UI already lives — filed as ARCH-41 to decide before any TLS-satellite
  testing at the rack. Same-day correction (user): the `ui` service left the controller compose
  entirely — config-ui is not deployed on the controller at all (repo owns the config; the editor
  runs on a workstation, per `build-docker.md`, whose stale pre-BUG-29 port-6000 refs got fixed
  in passing).

- **2026-07-08 — BUILD-17 DONE + BUILD-18 filed — the repo owns the config; harmonization deferred
  to next release.** The last open thread from the ops walk closed with the user's call: bridge
  semantics. The baked-in-image TOML (where config-ui saves silently died on every update) is
  replaced by delivery: `update.sh` copies the profile TOML (`CONFIG_PROFILE`, default
  `embedded-armv7`) into the runtime tree's `config/irene.toml` on every update, compose mounts it
  read-only and points `IRENE_CONFIG_FILE` at it. On-box edits now fail loudly instead of vanishing
  — config changes travel through the repo, like the bridge's. The wider observation — the two
  repos keep hand-copying each other's ops patterns with local dialects — is now BUILD-18
  `[deferred]`: inventory the drift and harmonize build/installation/rules next release.

- **2026-07-08 — BUG-30 DONE (filed + completed same day) — log rotation ported from the bridge.**
  The user's "are our logs rotating, or one endless file?" had the ugly answer: rename-at-startup
  only, then a plain `FileHandler` growing without bound for the container's whole
  `restart: unless-stopped` life, old renames never pruned — a slow disk-fill pointed at
  `/mnt/data` (which also holds durable state and docker's data-root), made *persistent* by the
  very logs mount BUILD-15 added. Fix = the bridge's exact scheme (`bootstrap.py::setup_logging`):
  startup rollover into the `irene.log.<stamp>.log` family, `TimedRotatingFileHandler` at midnight
  with 30-day retention (plus the suffix/extMatch pairing that makes backupCount actually delete),
  and a prune sweep for the startup-renamed siblings the handler can't match. The problem-report
  bundle's same-day log glob moved to the new family in the same change. Rotation tests rewritten
  (7), bundle tests green, pyright clean.

- **2026-07-08 — BUILD-16 DONE (filed + completed same day) — two-disk layout, converged at the live
  WB7 shell onto the bridge's REL-2 pattern.** The user's `df` opened it (`/mnt/data` 2.3 GB free,
  SD card 61 GB empty) and three iterations closed it: first a dot-dirs-on-card draft with a nested
  state mount, then a docker-data-root correction (it stays at the controller's existing
  `/mnt/data/.docker`), and finally the user pointed at what the bridge actually does — **clone on
  the card as delivery vehicle, the whole runtime tree on `/mnt/data`, update.sh rsyncing between
  them** — and voice now mirrors it exactly: `/mnt/sdcard/wb-mqtt-voice` (clone + compose + `.env`)
  → `/mnt/data/mqtt-voice-config/{assets,logs}` (the only container mounts; durable state sits
  inside `assets/state/` naturally). An SD card death costs the clone and `.env`, nothing else. The
  systemd unit refuses to start with either disk unmounted (`RequiresMountsFor`). Hours-later
  amendment of BUILD-15, same files.

- **2026-07-08 — BUILD-15 DONE (filed + completed same day) — the ops deployment is rack-ready.**
  Walking the install story ahead of ARCH-25 (user question: "which mounts? how do tokens reach the
  container?") exposed that the answer was "one mount, and they don't": no logs mount (file logs
  accumulating in the container layer on flash), no env plumbing at all for `DEEPSEEK_API_KEY` /
  `IRENE_REPORTS_TOKEN` (the LLM tier and problem reporting could never activate on a controller
  deploy), plus a latent uid-1000-vs-root EACCES on the bind mounts that only the rack would have
  caught. All fixed on the bridge's proven pattern — checkout at `/mnt/data/mqtt-voice-config`
  (user-directed twin of `mqtt-bridge-config`), `.assets`/`.logs` mounts, `ops/.env` secrets file,
  chown in update.sh — and INSTALL.md now also covers the aarch64 image variant and points to the
  nginx Plane-B deploy with the `esp32_irene_upstream` wiring seam. Three fewer surprises at the rack.

- **2026-07-08 — QUAL-77 DONE + ARCH-39/ARCH-40 filed — the bridge's desync-repair surface is pinned;
  voice adoption designed-for but deferred.** The bridge maintainer left a handoff note (DRV-5/SCN-11:
  `skipped_reason` idempotence-skip marker + reserved `force` param + scenario
  `reconcile_preview`/`force_reconcile`); all claims verified against the bridge's `contracts/openapi.json`
  at `c32068e` and re-pinned into eval-commons (`7cfd5a7`, catalog/STAMP unchanged, suite 40/40). The
  note's "re-pin the catalog first" worry was already satisfied by QUAL-76 the day before. Voice-side
  analysis with the user: the cross-turn confirmation the device flow needs already exists (the QUAL-31
  one-shot `pending_clarification` slot); the real gap is `_to_delivery_result` dropping
  `no_op`/`skipped_reason`; the scenario flow leans on ARCH-28 durable F&F for its ~25 s executions.
  Decision: post-release — two separate `[deferred]` design tasks filed (ARCH-39 device-level force-confirm,
  ARCH-40 scenario force-reconcile), safety posture recorded in both (never auto-force; the confirmation
  slot IS the human feedback channel).

- **2026-07-07 — QUAL-76 DONE (filed + completed same day).** The bridge published a
  rack-verified catalog (`8159b4b0`, bridge `40f0452`): auralic learns `previous`, zappiti power
  is a toggle. Routine inward re-pin — no fixture binds either device, so only the fixtures doc's
  stamp moved. The re-pin surfaced a silent slip: QUAL-75's PIN.json wrote the bridge repo HEAD
  into `bridge_commit` where the guard expects `STAMP.bridge_commit` (the generator's commit),
  so eval-commons' `test_pin_matches_stamp` had been red since 2026-07-06 without anyone running
  the full suite. Convention restored and documented in the PIN itself; eval-commons 40/40
  (`14ac383`, pushed).

- **2026-07-07 — DOC-10 DONE (filed + completed same day).** The lesson from the ARCH-38
  catch-up became a rule: `websocket-api.md` is now the `ws-protocol-doc-canonical` invariant —
  the WS protocol's single source of truth, updated in the same change as any endpoint or frame
  shape, with design docs deferring to it. And eval-commons got its first CLAUDE.md, seeded with
  the mirror rule (its providers implement that document, never reverse-engineer the protocol)
  plus the contracts-pin ownership rule. The protocol now has one book, and both repos know it.

- **2026-07-07 — ARCH-38 doc/profile catch-up (user review).** Two gaps closed in the same
  breath: `configs/satellite.toml` gained its `[trace]` stanza (off by default, `--trace` flips
  it; segmenter level so satellite traces carry the VAD-tuning frames), and the hand-written
  WebSocket protocol document — `docs/guides/websocket-api.md`, the real protocol reference —
  now teaches `wants_trace`/the `trace` grant/the per-response trace frame, plus the mTLS
  certificate-identity rule on both `/ws/audio` and the reply channel.

- **2026-07-07 — ARCH-38 DONE — satellite tracing shipped, hours after its design.** `--trace` on
  a room node now means something real: one merged file per utterance with the device story (raw
  mic ring, VAD frames, wake-gate verdicts including the skips, the wire exchange with RTT, the
  reply exactly as played) and the controller's execution trace nested inside — delivered as an
  in-band trace frame after each response, granted explicitly at registration, gated by the new
  default-off `[trace] allow_remote_request`. A missing or declined controller half is recorded,
  not fatal. `irene-replay-trace --show-controller` prints the nested half; the captured
  utterance stays replayable for VAD tuning. Suite 1353, pyright 0, 11/11 contracts, config-ui
  clean. The board is back to ARCH-25 + the tag — now with the debugging kit bring-up wanted.

- **2026-07-07 — ARCH-37 DONE (filed + designed same day) → ARCH-38 filed [release].** Satellite
  tracing designed in session: one utterance, one trace, two machines. The satellite gets its
  device story back (`--trace` was silently inert on a room node — raw mic, VAD frames, wake-gate
  verdicts, uplink, reply as played), and the §3 wire contract grows `wants_trace` (default false,
  ESP32-honest) with the controller's execution trace returning as an in-band frame after each
  response — through the mTLS proxy unchanged, gated by a new default-off `[trace]
  allow_remote_request` on the controller. One merged self-contained file per utterance,
  satellite-side. eval-commons needs no change (additive default). Retagged nothing; the release
  gate grows by one deliberate task because bring-up debugging wants this in hand.

