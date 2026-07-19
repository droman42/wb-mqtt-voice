# Irene — Release Journal
> Older sections: docs/archive/journal/2026-07-07_2026-07-09.md
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

- **2026-07-19 — QUAL-60 DONE: long conversations stop forgetting — the window now compresses what it
  drops.** The pre-work analysis mattered: it established that the turn window (10 turns), not the token
  budget (57k+ effective), is what actually forgets — so summarization triggers on window overflow, and
  the QUAL-52 token layer stays the untouched backstop. Shape: dropped turns pool in a bounded buffer;
  every 5 dropped turns one LLM call merges them into a rolling summary that lives OUTSIDE the message
  list (immune to both trim layers) and enters the prompt as a localized system context line. Two
  failure modes were designed against, not just the obvious one: a raised call keeps the buffer for the
  next attempt, and — subtler — the QUAL-15 never-raise chain's console-floor "unavailable" text is
  explicitly recognized (from the same localization asset that seeds the floor) and refused as a
  summary. Degradation target is exact: behave like BUG-18 plain windowing, never worse. One deliberate
  non-decision: cadence is a named constant, not config — no new surface until someone needs the knob.

- **2026-07-19 — BUG-44 DONE: the owner's "budget seems too tiny" question defused a five-day bomb.**
  What started as a QUAL-60 analysis question («we have DeepSeek v4 pro configured now, right?»)
  surfaced two facts: the configs pin `deepseek-chat`, which is a rolling alias now serving V4-Flash —
  and DeepSeek retires that alias on 2026-07-24, after which every deployment's LLM tier would have
  silently dropped to the console floor. Repointed to the explicit `deepseek-v4-flash` everywhere
  (6 configs + master + provider + schema), refreshed the QUAL-52 capability table to the V4 reality
  (1M context / 384K output vs the V3-era 64k/8k), kept `max_tokens = 8000` as a deliberate
  spoken-reply ceiling, and repointed the commons eval judge riding the same alias. The budget tests
  now exercise trim logic through explicit window overrides — capability bumps stop breaking them.

- **2026-07-19 — BUILD-46 DONE: staleness sweep #2 — the machinery is now routine.** Same shape as
  BUILD-45, one day later: the nag surfaced two owner-side moves (commons cut scope-v7.2 fixing the
  rotation parser that misread ##-style journals; the bridge cut catalog-v1.9 refining the
  `device_unreachable` 503 semantics for handler-reported reachability failures), and one task
  discharged both. The scope-guard re-vendor was a byte copy + tag bump — notably the CLAUDE.md block
  markers did NOT move, because the v7.2 STAMP attests the pinned block text is unchanged; markers
  track block provenance, not tool version. The catalog re-pin was doc-prose-only (golden untouched)
  and voice's existing `err_device_unreachable` mapping already speaks the refined semantics.
  Everything green on the first run: 8/8 staleness rows, 5+8 conformance, the new guard validating
  the very ledger entry that records its own arrival.

- **2026-07-19 — QUAL-85 DONE: the drift factory is closed — two schema copies stopped being copies.**
  The sweep's third task, and the deletions ran deeper than the filing knew. The hand-written component
  schema tree turned out to be pure fiction (nothing validated against its field content at runtime) —
  it is now DERIVED: a component's schema IS its CoreConfig section model, so the
  `dashboard_enabled`-style drift class cannot recur. The "dead chain" behind the resampling fields
  turned out to be the ENTIRE `config/validator.py` — 956 lines with zero importers, including a whole
  ArchitectureValidator nobody ever called; deleted whole under the standing dead-code rule, four config
  fields, two audio_helpers functions and seven config-master lines with it. The coherence guard earned
  its keep mid-sweep: it flagged `auto_create_dirs` the moment its only visible reader died, and the
  investigation showed the field is honored by AssetConfig itself (allowlisted with the reason). On the
  UI side the owner chose the strong fix: all 30 config interfaces in api.ts are now
  `components['schemas']` aliases over the generated OpenAPI types — check and build passed on the first
  try, which is the whole argument. Suite 1452 green, config-validator CI-mode clean, pyright 0.

- **2026-07-19 — BUG-37 DONE: the first sentence a user hears from the headline feature now sounds
  like a person said it.** «Сейчас 24.125 градусов» is gone three ways at once. The handler rounds the
  spoken value (metadata keeps the raw reading for machines); the Russian decimal path finally does
  what its docstring promised for years — `decimal_to_text_ru` was a money formatter pressed into
  general service, reading 24.5 as «двадцать четыре пятьдесят», and now reads «двадцать четыре целых
  пять десятых» system-wide (every spoken Russian decimal went through it, not just temperatures);
  and units decline by the numeral in both languages via template-side `|`-forms + a small
  `plural_form` util — «один градус», «24 градуса», «пять градусов», "1 degree". The money path is
  byte-untouched, verified by test. Suite grew to 1453 green.

- **2026-07-19 — BUG-39 DONE: the unanswerable clarification, answered.** First of a three-task
  local-fruit sweep (BUG-39 → BUG-37 → QUAL-85, one commit each; owner intake rulings taken up front).
  Three same-named ACs used to produce «Какой именно: Кондиционер или Кондиционер или Кондиционер?» —
  a question whose only answer is repeating yourself. The owner chose the room-led shape: one name in
  several rooms now asks «Кондиционер есть в нескольких комнатах — в какой: Спальня, Детская или
  Гостиная?» (rooms spoken in nominative, so no declension machinery), mixed lists qualify only the
  colliding names, and a genuine within-room collision falls back to the device id rather than lying
  by omission. Answerability verified against the QUAL-31 resume path: the room answer re-runs
  combined with the original utterance, and the resolver's existing room scoping picks the right
  device. Four-case test file added; smart-home guide gained the one sentence a user needs.

- **2026-07-18 — BUILD-45 DONE: the first routine staleness sweep of the new era — checked, filed,
  discharged in one pass.** An owner "check all pins" hours after the PROD-26 rollout found exactly
  what the machinery predicted it would: the bridge's afternoon (VWB-43 catalog-v1.8, commons IMPL-8
  contract-guard-v3.1) had moved two owners past voice's pins, and the `[[tool]]` manifest + the
  bridge's `re-pin owed: voice, commons` verdict made both findings visible without any prose
  archaeology. One task, one sweep: catalog re-pinned at both dests in one multi-dest run (STAMP-only
  minor — the golden and openapi bytes didn't move), contract-guard re-vendored at v3.1 (ARTIFACTS-PATH
  is a no-op on voice's stamps). One deliberate reading recorded: the owner's new `artifacts` list
  enumerates its `contracts/catalog/README.md`, but the pin keeps the three-file set — the flat pin
  layout's own README occupies that basename, and the owner README is version-pinned through the STAMP
  and `owner_commit` anyway. Everything green: 8/8 staleness rows, 5+8 conformance tests, both guards.

- **2026-07-18 — ARCH-58 DONE: the estate's first vendored runtime code is live — and the strict pin
  earned its keep on first contact.** The core-py migration ran exactly as designed two days ago:
  `.repin.toml` gained the `core-py` family (declared once, in the new format — the PROD-26 sequencing
  paid off), the engine came back as a byte-identical vendored copy with voice's singleton in the new
  `utils/entry_points.py`, 18 source files + 2 tests swept, `utils/loader.py` finally shed the
  DynamicLoader and the fossil py3.8/pkg_resources compat block, and `startup_validation` swapped its
  hand-rolled entry-point enumeration for the engine's `list_registered`. The story of the day: the
  VERY FIRST strict pin refused `core-py-v1` — the tag was cut before the STAMP landed, so the tagged
  tree couldn't satisfy pins-complete-and-verbatim — and commons cut `core-py-v1.1` (packaging
  correction, artifact bytes unchanged) within the hour. The owner ruling that runtime code needs
  mechanical discipline, not convention, proved itself before a single line of consumer code ran.
  Acceptance clean across the board: suite 1433 green, analyzer JSON byte-identical on all 6 profiles,
  import contracts 11/11, all guards + the staleness gate green. Voice's half of PROD-8 is closed;
  bridge CORE-7 codes against the same tag next.

- **2026-07-18 — BUILD-44 DONE (answered same day) → ASSET-6 filed [deferred]: the wake-pack promise
  to the satellite is on record.** Voice confirms the satellite's three asks: the multi-model pack
  ships only as a tagged `wake-pack` bump (their publish-refusal on drifted bytes is correct behavior,
  not an obstacle); the STAMP's flat file→sha256 enumeration — the surface their flash-time
  verification parses — stays stable across v1.x, with per-word grouping strictly additive and major
  reserved for verification-surface breaks; and the drift their OPS-13 smoke test caught live (HF
  `main` moved under the pinned `irina.json`) gets discharged AT the bump — re-stamp or restore, plus
  the switch from mutable `/resolve/main/` to immutable `/resolve/<hf_revision>/` URLs in both the
  STAMP and the in-code catalog. ASSET-6 holds the execution, gated only on the next trained words
  (Валера/Наташа) arriving from the wakeword-training sibling. With this, all four PROD-26 build items
  plus the filing response are done — the board write-back closes voice's half of the sweep.

- **2026-07-18 — DOC-14 DONE: the trace file format is a stamped contract — `trace-format-v1`.** The
  saved-trace JSON has been load-bearing since ARCH-19 (and doubly so since ARCH-38 put a controller
  trace inside every satellite merged file), but its shape lived as a code literal and narrative prose.
  Now the tracing guide carries the normative field reference ("The trace file format (reference)" —
  controller envelope, satellite additions, and the compatibility rule: additive keys keep the version,
  readers ignore unknown keys), the code writes `TRACE_FORMAT_VERSION`, and
  `contracts/trace-format/STAMP.json` + the tag land in the same change with a version-triple test in
  the ws-protocol mold. New CLAUDE.md invariant `trace-format-doc-canonical`; the manifest node carries
  the canonical carve-out. One limit found live: the commons docs-manifest schema caps declared
  surfaces at 10, so the trace-format glob-trigger mapping waits for the next schema bump. This was the
  last build item of the PROD-26 sweep — what remains is the BUILD-44 answer and the board write-back.

- **2026-07-18 — BUILD-43 DONE: the repin engine this repo invented comes home as a vendored tool.**
  BUILD-24's `scripts/repin.py` was promoted org-wide by commons (HK-12/PROD-26, `packages/repin/` at
  `repin-v1`) and voice now consumes its own idea back: the vendored file replaces the local engine, the
  FAMILIES dict became `.repin.toml` (catalog's two-dest run — local pin + commons crossover — is now
  tool-enforced as the only legal cross-repo write), and the `[[tool]]` manifest watches the vendored
  guard tags so "which tag is scripts/X.py at" stops being prose. The pre-commit hook gained the §5 warn
  stage; `make repin-check` is the `--fail-on any` release gate. Live check green across 4 pin dests +
  3 tools, including a real tokenless ls-remote against all three owner repos; a catalog dry-run wrote
  both dests at `catalog-v1.7` and was restored. En route: the registry's consumed table had quietly
  rotted (`catalog-v1.5` prose vs v1.7 pins) — the row now defers to `PIN.json`. ARCH-58 will declare
  `core-py` as the next family in the new format, first live test of the strict byte-identity pin.

- **2026-07-18 — BUILD-41 + BUILD-42 DONE (one commit): the HK-12 enforcement sweep lands — voice now
  runs contract-guard v3 and scope-guard v7.1, and carries the contract-triad block.** The PROD-26
  delegation arrived with the commons build already complete (repin-v1 / contract-guard-v3 / scope-v7.1
  all tagged same-day), so the sweep was pure adoption: both guards re-vendored at their new tags in a
  single commit, the hook's contract-guard line now tolerates mid-bump commits (`--relax-tags`) while CI
  stays strict, and `contracts_verdict_since` is set to today — from here every completion entry answers
  the contracts question (`contracts: <what moved>` / `contracts: none — <why>`) the way it has answered
  the docs question since HK-6. The third pinned block (contract-triad: surface-with-the-artifact,
  pins-complete-and-verbatim, contracts-verdict, the §5 staleness ladder) sits in CLAUDE.md between
  fresh markers with its hash registered; the two existing blocks verified current at scope-v7.1 and
  did not move. Both guards green on the live tree before and after the ledger flip. Next in the sweep:
  BUILD-43 (the repin engine this repo invented comes home as a vendored tool), DOC-14 (trace-format
  stamp), the BUILD-44 answer to satellite.

- **2026-07-16 — ARCH-42 DONE: the core-py loader extraction is designed — the council's sequencing
  lock is fully discharged.** Interactive session, two rounds, on top of a same-day foundation that
  didn't exist this morning: ARCH-50's inventory plus its remediation left the engine small and
  honest (the namespace registry, no hand-maps, the coherence guard watching). The design
  (`docs/design/core_py_loader_extraction.md`): commons ships `entry_point_loader` as class-only —
  each consumer owns its process singleton — with three surface deltas beyond the faithful extract:
  `base_class=` validation (bridge's hand-rolled DevicePort check becomes the engine's native
  rejection path, failures ledgered by name), single-EP `get_provider_class` (fetching one class no
  longer imports the whole group), and `list_registered` for names-without-import (voice's startup
  validation and bridge's offline `dump_catalog` are the rule-of-two). Consumption is the guards'
  vendored-at-tag model but with STRICT enforcement — pin folder, sha256, and a byte-identity test
  between the pin and the importable copy — because this is the estate's first vendored code that
  RUNS in production. Voice's migration (full 20-file sweep to a new `utils/entry_points.py`
  singleton) is filed as ARCH-58 [release], gated on commons cutting `core-py-v1`; the board's
  PROD-8 got its write-back: surface known, skeleton unblocked. Bridge's CORE-7 now has a concrete
  §5 to code against instead of board prose.

- **2026-07-16 — ARCH-55 addendum: CI's pyright caught what the local venv couldn't.** The
  backend-health gate (full provider extras) flagged four `str | None` type errors from the ARCH-55
  literal removal — the deleted `or "console"`/`or "openai"` had been silently doing type-narrowing
  duty at the API response sites. Fixed with one honest primitive: `resolved_default_provider` on the
  component base (raises on the impossible-post-init None instead of inventing a name). The audit also
  closed a real gap: LLM never had the BUG-36 default check tts/audio carry — and the first draft of
  it was wrong in an instructive way, treating offline-unavailable as fatal until the smoke suite's
  offline-degrade tests failed the boot: the correct split is kind-1 (default cannot LOAD → fatal) vs
  kind-2 (loaded but unavailable → the QUAL-15 chain degrades). Suite 1426 green, touched-file pyright
  clean, contracts 11/11.

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

