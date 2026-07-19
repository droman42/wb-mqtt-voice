# DONE-ledger archive 002 (frozen — never re-edit; IDs stay resolvable to scope-guard via this directory)

- [x] **ARCH-23** [ESP32] (P-TBD) `[deferred]` — **✓ EXPORT-CLOSED 2026-07-12 (BUILD-22/PROD-15) → `../locveil-satellite`
      FW-1.** The ESP32 firmware rewrite (build the headless voice-satellite firmware to the ARCH-22
      `esp32_satellite.md` contract, replacing the quarantined draft) is now the satellite product repo's work —
      re-filed there as **FW-1** (`HW-GATED`, gated on its DES-3 execution-layer decision; the HK-4 per-device-apps
      amendment noted inline). No voice-side remainder: the design doc moved with it, the `ESP32/` draft tree was
      deleted (2026-07-08 verdict), and the wire protocol the firmware builds against stays here as
      `docs/guides/websocket-api.md` (pinned by the satellite repo).
      docs: none — export-close bookkeeping; the doc moves rode BUILD-22 (retro-verdict, BUILD-35 cutover).
- [x] **ARCH-42** [COMMONS][PROCESS] `[deferred]` — **✓ DONE 2026-07-16. DESIGN: extract the
      entry-point discovery engine to `locveil-commons/packages/core-py`** (BUILD-20 D-8; PROD-8
      council scope, reconciled at intake same day; hard predecessor ARCH-50 delivered its inventory
      first, per the sequencing lock). Deliverable landed:
      `docs/design/core_py_loader_extraction.md` — AGREED in a 2-round interactive owner session.
      Decisions: shared module **`entry_point_loader`** ships the `DynamicLoader` CLASS ONLY
      (consumers own their singleton — the shared artifact stays state-free); surface = faithful
      extract (py3.8/pkg_resources compat dies; both repos pin 3.11) + three deltas: optional
      `base_class=` validation (bridge's inline DevicePort check becomes the engine's native
      rejection path — the rule-of-two feature), `get_provider_class` loads the single named EP
      (no more importing the whole group to fetch one class; analyzer seam unaffected), and
      `list_registered` (names WITHOUT importing — voice `startup_validation` + bridge
      `dump_catalog` are the two consumers). Consumption = **vendored module at `core-py-vN` tags**
      (the guards' model, hermetic Docker) with **STRICT pin enforcement** — contracts/pins/core-py
      PIN.json + a byte-identity conformance test between pin and importable copy, because this is
      the estate's first vendored RUNTIME code. Voice migration = FULL 20-file import sweep to a
      new voice-owned `utils/entry_points.py` singleton (owner ruling over a loader.py shim);
      metadata quartet, `utils/namespaces.py`, aux helpers, and bridge's `class_loader.py` all stay
      put; ARCH-43 (logging) stays parked. §5 records the bridge CORE-7 adoption contract
      (base_class native, loader never in domain/, no golden drift, zero new import-linter
      exceptions). Follow-up filed: **ARCH-58 `[release]`** (the voice migration, gated on commons
      cutting `core-py-v1`); board PROD-8 written back — the skeleton is unblocked (ARCH-50 ✓ +
      ARCH-42 ✓). docs: none — design doc (internal); no manifest node describes loader internals.
- [x] **ARCH-44** [HW][SEC] `[deferred]` — **✓ EXPORT-CLOSED 2026-07-12 (BUILD-22/PROD-15) → `../locveil-satellite`
      DES-5.** The device-certificate lifecycle design (revocation + renewal — `esp32-provision revoke` only drops
      pending CSRs; issued certs trusted 825 days with no `ssl_crl` and no renewal path; surfaced by the ARCH-25
      provisioning round-trip 2026-07-09) travels with the Plane-B provisioning tree, which moved to satellite
      `provisioning/` in the same change — re-filed there as **DES-5** with the finding text intact. Voice keeps
      only the tether: the pinned `contracts/esp32-site.conf.j2` copy that `test_arch36_tls_e2e.py` renders.
      docs: none — export-close bookkeeping; the doc moves rode BUILD-22 (retro-verdict, BUILD-35 cutover).
- [x] **ARCH-46** `[release]` [PROCESS][FEEDBACK] — **✓ DONE 2026-07-11 (same-day intake→completion). PROD-14/HK-3
      voice delegation: reports re-point residue + `report-protocol-v1` consumption.** The voice half of the board
      delegation (`../locveil-commons/board/BOARD.md` PROD-14 Phase 2; normative spec:
      `../locveil-commons/process/problem-reports.md` + machine core tagged `report-protocol-v1`). **Narrowed at
      intake:** the delegation's slug-sweep list (inbox skill ×4, `problem-report-inbox` invariant ×2,
      config-master example) and the "enable `[reports]` in the WB7 profile" find were already done by BUILD-31
      earlier the same day. Shipped: **(1)** `/inbox` drift fixes — ping-pong guard in the needs-owner handover
      step + the bridge's affirmative post-merge ledger wording + a labels-are-contract note; **(2)**
      `eval/profiles/targets/wb7.env` port 6000→8080 (the PROD-14 Phase-1 smoke find; the deployed WB7 image
      serves 8080 per `ops/INSTALL.md`); **(3)** protocol consumption — machine core pinned at
      `contracts/report-protocol.pin.json` (tag `report-protocol-v1` @ commons `8fb983f`; new `contracts/` home +
      README with the re-pin command) + `irene/tests/test_report_protocol_conformance.py` (11 tests: emitted
      labels / title prefixes both sources / bundle-path template / envelope required fields via `build_envelope`,
      and the six deployment profiles' `[reports].repo` vs the pin's slug registry) + a
      `cross-repo-source-of-truth` bullet in CLAUDE.md naming the commons as the protocol owner; **(4)**
      `docs/design/problem_reports.md` shared sections (§5 envelope, §7 choreography) restructured into pointers
      to the commons spec, ARCH-30 status untouched — the first pass was **BOUNCED by the commons verification**
      (delivered annotate-and-defer: ownership headers added but the §5/§7 bodies stayed — the two-copies pattern
      the spec §1 forbids); the real lift-out landed same-day: §5/§7 bodies replaced by pointers + the voice-side
      remainder (D-11 rationale as decision record, the outcome-3a later-note), stale §7.3/§7.4 cross-refs
      re-pointed to the core/spec (incl. the `report_bundle.py` docstring); **(5)** `lens-voice.md` co-ownership re-review in
      `locveil/locveil-reports` (VWB-26 pattern) — all repo claims verified (checkout path, `CROSS_REPO_TOKEN`,
      test paths, `irene-cli -c/-e`, bundle member names, labels/handover schema vs the core); one stale claim
      (`eval-commons` catalog comparison) fixed in reports-repo commit `1ca251e`. ARCH-46 written back into the
      PROD-14 board entry (commons `50bf906`).
- [x] **ARCH-47** [WS][SATELLITE] `[deferred]` — **✓ DONE 2026-07-12 (PROD-16 delegation — the contracts
      convention's first voice instance; filed at PROD-15 intake, ungated+rescoped at PROD-16 intake).**
      The two voice-owned satellite-facing artifacts got their version surfaces. **ws-protocol** (tag
      **`ws-protocol-v1`**): `contracts/ws-protocol/` STAMP + pointer README (artifact stays
      `docs/guides/websocket-api.md` per `ws-protocol-doc-canonical`); doc-header "**Protocol version:
      1**" line; served constant `irene/core/ws_protocol.py::WS_PROTOCOL_VERSION` added to BOTH
      `registered` acks (`/ws/audio` + `/ws/audio/reply`); version-triple conformance test
      `irene/tests/test_ws_protocol_version.py` (doc header = constant = STAMP). **wake-pack** (tag
      **`wake-pack-v1`**): sidecar STAMP over the unmodified ASSET-5 HF pack (irina.json/irina.tflite
      sha256s fetched from the published artifacts, HF revision recorded); same test asserts the stamp
      mirrors the in-code released catalog (`_get_default_model_urls`) so the sidecar can't drift.
      **register version-reporting**: `ClientRegistration` gained `protocol_version` +
      `wake_pack_version` (firmware/model existed); the satellite runner's link reports
      `protocol_version` + `firmware_version` (= package version; `wake_pack_version` is ESP32-honest —
      firmware territory). Doc updated in the same change (register fields prose + both ack shapes).
      The registry/config-ui staleness flag FILED SEPARATELY as ARCH-48 (decision point exercised).
      Verified: new conformance 4/4, WS+satellite suites 28/28, full suite 1395 passed/7 skipped,
      pyright 0 on touched files, import contracts 11/11, contract-guard 0 warnings.
      docs: guides/websocket-api
- [x] **ARCH-50** [ARCH][BUILD] `[release]` — **✓ DONE 2026-07-16. ★ REVIEW: hardcodings & config overrides
      that violate dynamic build-and-loading.** Filed 2026-07-13 (owner, from the BUILD-36/PROD-21 bounce);
      PROD-8 council addendum 2026-07-16 (carries the dead `get_provider_capabilities`, hard predecessor of
      ARCH-42). Deliverable landed: `docs/review/dynamic_loading_hardcodings_review.md` — frozen evidence for
      the full sweep (backend + tools + TOMLs + config-ui touchpoints), verdicts ruled in a 3-round
      interactive owner session (governing ruling: **no config overrides** — a declared field is honored or
      deleted, never silently out-voted). Findings: the seed confirmed end-to-end (literal handler namespace;
      `discovery_paths`/`auto_discover` declared+plumbed+documented+never-read); ~30 dead config fields
      (whole `AssetConfig` download/cache block, two dead handler-config models, partial families); dual
      enable-flag authority with a silent 8-of-11 force-sync while the build analyzer reads the raw loser;
      provider-name literals/force-adds in 6 components (incl. the literal `hey_jarvis` wake-word); five
      independently-drifting component→namespace maps — two missing `vad`, one causing a LIVE config-ui bug
      (VAD provider dropdown renders empty via `/config/providers/vad` 404); decorative `inputs`/`runners`
      entry-point groups + phantom `locveil_voice.outputs` + phantom `intent_system_component` module path;
      4 dead code units (`get_provider_capabilities` per the PROD-8 delegation, `EnhancedHandlerManager`,
      `ComponentLoader`, `add_handler`/`remove_handler`+legacy pattern fallback); heuristic domain literals.
      Conversation-context special-casing sanctioned as the ONE intent-path exception (owner). Remediation
      filed per `review-then-remediate`: **ARCH-52/53/54/55/56/57, QUAL-83, TEST-22** (all `[release]`) +
      **QUAL-84** `[deferred]`. Unblocks ARCH-42 (the council's sequencing lock — the loader-extraction
      design consumes this inventory). docs: none — review-only change (frozen evidence under `docs/review/`,
      no behavior altered; the remediation tasks carry their own docs verdicts).
- [x] **ARCH-52** [ARCH][CONFIG] `[release]` — **✓ DONE 2026-07-16. Intent-handler loading: dead discovery
      config deleted, one namespace constant, shared assets-root resolver, fail-hard priorities**
      (ARCH-50 F-A1/F-A2/F-A3). `IntentHandlerListConfig.auto_discover` + `discovery_paths` deleted
      end-to-end: model, `intent_component` plumbing ×2, build-analyzer skip-set, all 8 TOMLs,
      `config-ui/openapi.json` re-dumped + `openapi.gen.ts` regenerated + `api.ts` interface trimmed
      (`config-ui-stays-functional`: check + build green). The handler namespace is now the ONE
      `INTENT_HANDLERS_NAMESPACE` constant (utils/namespaces.py) consumed by `intents/manager.py`,
      `config/models.py` (validator), `core/contract_validator.py`. New
      `resolve_intent_assets_root()` (core/intent_asset_loader.py) — env root if it holds `donations/`,
      else cwd `assets/`, else package-relative repo root; raises when nothing validates — adopted at all
      four sites (manager, nlu_component ×2, web_server), retiring the QUAL-59-class cwd-relative
      `Path("assets")`; verified resolving correctly from a foreign cwd with unset/bogus/valid env. The
      hardcoded fallback domain-priorities dict is gone — a priorities-loading failure now raises at
      startup (fail-hard ruling). Verified: full suite 1417 passed / 7 skipped, import contracts 11/11,
      config-ui `npm run check` + `build` green. docs: none — the deleted fields appear in no manifest
      node (config-file comments only); no user-visible behavior changed on the happy path.
- [x] **ARCH-53** [ARCH] `[release]` — **✓ DONE 2026-07-16. Capability ports are handler-declared
      metadata** (ARCH-50 F-A4). `IntentHandler.get_capability_ports()` classmethod (default `{}`,
      the `requires_configuration()` pattern) declares `{attribute: component_name}`; the six handlers
      with component needs override it (conversation→llm, translation/text_enhancement→llm,
      voice_synthesis→tts, audio_playback→audio, speech_recognition→asr). `intent_component`'s
      injection loop is now generic — the QUAL-24 central `capability_ports` table is deleted, and the
      `provider_control_handler` name special-case became structural (`hasattr(set_component_registry)`
      — verified the only declarer). Runtime assertion at completion: entry-point-loaded declarations
      across all 15 handlers exactly reproduce the retired table. New handlers self-describe; adding a
      component need no longer edits intent_component. Verified: full suite 1411 passed / 7 skipped,
      import contracts 11/11. docs: none — internal wiring mechanics; `howto-new-intent` doesn't teach
      port injection (a future authoring-doc mention rides the next howto touch).
- [x] **ARCH-54** [ARCH][CONFIG] `[release]` — **✓ DONE 2026-07-16. `[components]` is the single enable
      authority** (ARCH-50 F-C1). The per-section `enabled` field is deleted from ALL TEN component configs
      (the 8 force-synced + `MonitoringConfig`/`NLUAnalysisConfig`, which had never even been synced) and
      the silent parse-time force-sync (`models.py` `validate_system_dependencies`) is gone. Runtime
      readers swapped to `components.*`: `audio_negotiator` (wake/asr contract gates), `voice_runner`
      (redundant twin check dropped), `satellite_runner` (its runtime overrides now write the authority),
      `nlu_analysis_component` (gate on `components.nlu_analysis`); `IntentSystemConfig`'s handler
      validator lost its enabled gate (it validates structural coherence, which holds regardless of
      runtime enablement — the non-empty-handlers rule was already enforced unconditionally by the field
      validator). **Build analyzer reworked to the same authority** — and the rework surfaced/fixed three
      latent analyzer bugs: (1) the intent-handler analysis had NEVER run (its gate read a phantom
      `[intents]` section; now `[components].intent_system` + `[intent_system.handlers]`) — handler
      modules + donation contract paths now reach requirements; (2) the provider-family loop's 8-name
      hand-list silently skipped `vad`, so VAD provider deps never reached images (standalone now
      correctly gains `vad-silero`+`asr-onnx` — the runtime had been falling back to energy VAD after a
      silent init failure); (3) profile validation errors ("Provider 'asr' not found in namespace
      components") cleared — all profiles now analyze `valid: true`. The ARCH-57-deferred
      `component_names` hand-lists are retired by this rewrite. Also fixed en route:
      `validate_entry_point_consistency` still called the QUAL-83-deleted `ComponentLoader` (masked by its
      own broad except — now `dynamic_loader` + `model_fields`, no hand-list); and
      `NLUAnalysisComponent.get_python_dependencies` falsely declared `nlu-spacy` REQUIRED (spacy is
      optional-with-degrade there — the armv7 deployment proves it; the dep rides the `spacy_nlu`
      provider's own metadata where enabled), keeping armv7's lean dep set intact + T3 arch gate green.
      TOML template generators + 9 live TOMLs stripped ([vad]/[inputs.*]/[satellite*]/[trace]/[reports]
      `enabled` fields survive — they're not components); openapi re-dumped, config-ui types regenerated +
      `api.ts` trimmed (check+build green); old TOMLs with a stale per-section `enabled` still parse
      (nested models ignore extras). Verified: full suite 1411 passed / 7 skipped,
      `--validate-all-profiles` all valid, armv7l arch gate green, config-validator CI-mode all valid,
      import contracts 11/11. docs: guides/audio, guides/voice-trigger, guides/howto-new-model — TOML
      examples showing the retired per-section `enabled = true` now show the `[components]` block instead;
      guides/satellite + guides/vad untouched (their `enabled` fields live on).
- [x] **ARCH-55** [ARCH][QUAL] `[release]` — **✓ DONE 2026-07-16. Provider loading honors config
      strictly — no force-adds, no name literals** (ARCH-50 §D; strict-config ruling). **tts/audio:**
      init defaults + config-read literals → config-only (`None`/`[]`); console force-add into the
      enabled set removed (what the operator enabled IS the loading set); the last-resort console
      conjuring (`_load_fallback_provider` / the inline audio block) deleted — zero surviving providers
      now raises with a fix-the-config message; lazy "essential" set = configured default + fallback
      chain (was `["console"]` + console-enabled-by-default); request-time/schema `or "console"`
      dropped (BUG-36 guarantees a loaded default). **voice_trigger:** openwakeword init defaults +
      force-add + the conjured fallback with the literal `hey_jarvis` wake-word deleted (decision point
      resolved: NO `fallback_providers` field — wake engines are alternatives, not a cascade, per
      guides/voice-trigger; zero engines → loud error, component stays inactive, BUG-36 reports).
      **asr/llm:** `"vosk"`/`"openai"` literals → config-only; the LLM chain is EXACTLY config's
      default+fallbacks — the implicit terminal-console append removed (deployment TOMLs already
      declare console in `fallback_providers`, verified); console localized-message injection now keys
      on `isinstance(ConsoleLLMProvider)`, not the name. **vad:** `VADConfig` gains
      `fallback_providers` (default `[]`) — the ruling's "resilience is DECLARED" mechanism; both
      energy-literal fallback paths in `audio_processor` (unregistered default + init-failure) now walk
      the CONFIGURED list and raise when nothing declared remains; the standalone profiles (silero
      default) declare `["energy"]` explicitly; config-master documents the field
      (master-completeness gate green). Three tests asserting the old implicit behavior rewritten to
      the new contract (fatal-without-declaration + declared-fallback-works). Residual name strings
      audited: only pip package names, Russian speech-alias maps, telemetry keys — none drive loading.
      Verified: full suite 1411 passed / 7 skipped, `--validate-all-profiles` valid, armv7l gate green,
      config-validator valid, contracts 11/11, openapi re-dumped + config-ui types updated
      (check+build green). docs: guides/vad — silero prose now teaches declared fallback +
      `fallback_providers` table row; guides/audio already documented the declared form.
      **ADDENDUM 2026-07-16 (CI catch, fixed same day):** CI's full-extras pyright flagged 4
      `str | None` → `str` errors this task introduced (the removed `or "console"`/`or "openai"`
      literals had been doing double duty as type narrowing at the API response sites). Fix:
      `Component.resolved_default_provider` property (raises on the impossible-post-init None — no
      literal reintroduced) at all 4 sites, AND the audit closed a real gap: LLM never enforced the
      BUG-36 default check tts/audio have — added with the correct kind-1/kind-2 split (default must
      LOAD; merely-unavailable degrades per QUAL-15 — the first draft wrongly made offline-unavailable
      fatal and the smoke suite's offline tests caught it immediately). Suite 1426 green, pyright
      clean on touched files.
- [x] **ARCH-56** [ARCH] `[release]` — **✓ DONE 2026-07-16. InputManager consumes the
      `locveil_voice.inputs` entry-points; the decorative `runners` group is deleted** (ARCH-50
      F-F1/F-F2; owner chose adopt-over-delete for inputs). `_discover_input_sources` is a generic
      entry-point loop: enablement from the `[inputs]` boolean flag matching the EP name, settings from
      the `[inputs.<name>_config]` model passed as `model_dump()` kwargs, availability checked first,
      post-configure setup structural (`initialize()` — the microphone is the only declarer). The three
      direct adapter imports + per-class if-branches are gone; `MicrophoneInput.configure_input` learned
      its config model's field names (`sample_rate`/`chunk_size`) alongside its historical spellings.
      The `locveil_voice.runners` group is deleted from pyproject (nothing ever read it — runners launch
      via `python -m`; Dockerfile CMDs unchanged) and `ALL_NAMESPACES` re-asserted ≡ pyproject's now-12
      groups after an editable-install refresh. Behavior parity smoke: flags on/off produce exactly the
      old source sets, CLI auto-start intact. Verified: full suite 1411 passed / 7 skipped, import
      contracts 11/11, `uv lock --check` clean. docs: none — no manifest node describes input discovery
      mechanics or the runners entry-points.
- [x] **ARCH-57** [ARCH][QUAL][UI] `[release]` — **✓ DONE 2026-07-16. One canonical component→namespace
      map; analyzer module paths from entry-point values — the live config-ui VAD dropdown 404 fixed**
      (ARCH-50 F-E1/F-E2). New `utils/namespaces.py`: `PROVIDER_NAMESPACES` (8 families incl. `vad`) +
      the group constants + `ALL_NAMESPACES`, asserted ≡ pyproject's 13 entry-point groups at completion.
      Adopted: `core/assets.py` (map values + the cross-family search sweep), `core/startup_validation.py`
      (gains `vad` — its name-ref fields are now startup-validated), `configuration_component.py`
      (`/config/providers/vad` now resolves → the `provider_select` dropdown for `vad.default_provider`
      populates), `config/validator.py` (gains `vad`+`text_processor`), `build_analyzer.py` fallback list
      (phantom `locveil_voice.outputs` gone). Analyzer component module paths now come from entry-point
      VALUES — the convention-derived phantom `locveil_voice.components.intent_system_component` is out,
      the real `intent_component` in; verified by baseline diff over all 6 Docker profiles (exactly that
      one delta, nothing else moved). NOTE: the analyzer's 8-of-11 `component_names` hand-lists are
      retired in ARCH-54's `_analyze_components` rewrite (same sweep) — the sections-reading logic they
      feed is replaced wholesale there. Verified: full suite 1417 passed / 7 skipped, import contracts
      11/11, pyright delta clean on touched files. docs: none — internal map unification; no manifest
      node describes the providers endpoint's component coverage (the UI fix restores doc-implied
      behavior without changing any documented claim).
- [x] **ARCH-58** `[release]` [ARCH][COMMONS] — **DONE 2026-07-18 — the voice core-py migration: the
      estate's first vendored RUNTIME code is live** (ARCH-42 design §4; PROD-8/PROD-26 sequencing held —
      BUILD-43's `.repin.toml` landed first, so the family was declared once, in the new format).
      **Owner-side flaw found + fixed at the very first pin:** `core-py-v1` was tagged BEFORE the
      "PROD-8 amended" commit added `contracts/core-py/STAMP.json`, so the v1 tree carries no STAMP and
      a pins-complete-and-verbatim pin could not be assembled from it — commons cut **`core-py-v1.1`**
      (packaging correction, artifact bytes diff-verified UNCHANGED; STAMP note records it; commons
      journal entry). The strict-pin ruling vindicated by its first mechanical use. Landed voice-side:
      `core-py` family in `.repin.toml` → `contracts/pins/core-py/` (artifact + owner STAMP verbatim +
      strict PIN.json @ `core-py-v1.1`) + pin README + registry row; importable copy
      `utils/entry_point_loader.py` (byte-identical, sha256 `c40438bd…`); voice-owned singleton module
      `utils/entry_points.py` (`dynamic_loader = DynamicLoader()` — cache + BUG-36 failure-ledger
      semantics unchanged); **full import sweep** — 18 source files + 2 tests moved to
      `utils.entry_points` (incl. the mixed voice_trigger import split and the `build_analyzer` seam);
      `utils/loader.py` shrank to the aux helpers (DynamicLoader + the py3.8/pkg_resources compat block
      DELETED, ~140 lines); `startup_validation._registered_provider_names` adopted the engine's
      `list_registered` (names-without-import, rule-of-two); identity test
      `backend/tests/test_core_py_pin_identity.py` (runtime↔pin byte-identity, PIN sha256, PIN↔STAMP
      coherence, singleton serves the pinned class). **Acceptance, all green:** full suite 1433 passed /
      7 skipped; analyzer JSON **byte-identical across all 6 profiles** (before/after capture);
      import contracts **11/11** (utils stays the bottom layer); `--validate-all-profiles` valid;
      pyright no new findings (env-only missing-import noise); both guards + `repin --check --fail-on
      any` green (7 pins/tools + core-py current).
      docs: none — behavior-neutral engine swap; the architecture/build docs describe entry-point
      discovery conceptually and no manifest node names the internal module
      contracts: core-py FIRST CONSUMED @ core-py-v1.1 (strict byte-identity pin — the first vendored
      RUNTIME code); owner-side v1→v1.1 packaging correction cut in commons as part of this task
- [x] **QUAL-5** (P2) — **✓ DONE 2026-06-06.** Cruft cleanup. **Reconciled (Invariant #8): counts fell during QUAL-4's
      import churn** (F401 360→237, star-imports 62→5+57 F405, F841 22→15). **Cleared the verifiable cruft to ZERO:**
      unused imports (189 ruff-auto-fixed + the 41 unsafe-to-autofix tail classified — pure availability probes →
      `importlib.util.find_spec`, side-effecting probes → documented `# noqa: F401`, genuine leftovers deleted);
      star-imports (`api/__init__.py` + `utils/__init__.py` `from .x import *` → explicit re-export lists; the package
      `__all__`s now define the public surface); unused vars (removed, side-effecting RHS preserved). Verified: `ruff
      --select F401,F403,F405,F841` clean, **`uv run pyright` 0** (catches any wrongly-removed still-used import as an
      undefined name), package imports OK, 9/9 contracts, suite 84=baseline. **Vulture pool NOT pursued (user decision):**
      ran it (753 candidates @ conf 60) and confirmed §G's "noisy/candidate, not confirmed dead" — it is
      **false-positive-dominated** (flags live entry-point components like `ConfigurationComponent` and FastAPI
      `response_model` Pydantic schemas as "unused"); a bulk cleanup would risk breaking dynamically-loaded code, and
      genuine dead code was already removed during the refactors (ARCH-13 legacy plugins, QUAL-21 settings runner,
      QUAL-24/34 dead handlers/params). Refs: §G.
- [x] **QUAL-6** (P2) — **DONE 2026-06-06.** Resolved the startup "CoreConfig fields without section models"
      warning as a **structural false positive** (Invariant #8): `validate_schema_coverage` compared the
      section-model registry against *all* `CoreConfig` fields, but the registry — by construction — only ever
      holds Pydantic-model fields, so every scalar top-level field (the 11 instance-identity + runtime knobs:
      `name/version/debug/log_level/default_language/supported_languages/language/timezone/
      max_concurrent_commands/command_timeout_seconds/context_timeout_minutes`) was *permanently* reported
      "missing." Fix: factored the "is this annotation a section model" predicate into a shared
      `AutoSchemaRegistry._resolve_section_model()` used by **both** `get_section_models` and the coverage check;
      the check now compares against the actual section fields, so a non-empty diff means a real registration
      drop (worth a warning) rather than expected scalars. Scalars are intentionally section-less (documented
      inline in `CoreConfig`). No config-structure / TOML / env-var / read-site changes. Verified: warning gone
      (`validate_schema_coverage().warnings == []`), 16/16 sections still registered, full pyright 0,
      `test_config_schemas`+`test_import_contracts` 14/14, dependency validator 55/55, suite 84=baseline. Refs: §H.
- [x] **QUAL-7** (P2) — **CLOSED-AS-OBSOLETE 2026-06-03 (Invariant #8, user-approved).** Premise no longer exists: the
      `train_schedule` handler + its config/assets were **removed in QUAL-34**, so there is no `train_schedule` config-vs-model
      mismatch to reconcile (verified: `train_schedule` absent from `config-master.toml`, `config/models.py`, and all of
      `irene/`/`assets/`/`configs/`). _Original: `configs/config-master.toml` put train-schedule under
      `[intent_system.handlers.train_schedule]` while the model field was `IntentSystemConfig.train_schedule` — orphaned/ignored.
      (Found during DOC-5.)_
- [x] **QUAL-8** [FAF] (P1) — Fire-and-forget full review & gap analysis. **DONE 2026-06-01** →
      `docs/review/fire_and_forget_review.md` (5×P0, 8×P1, 6×P2). Verdict: **F&F is broken end-to-end** and the
      legacy `docs/fire_forget_issues.md` "✅ COMPLETED" is **materially false** (banner added). Legacy issues:
      #4 FIXED, #6 FIXED-but-moot, #1 & #5 CHANGED-still-broken, #2 CHANGED-unreachable, #3 CONFIRMED. Plan
      correction: ~13 call sites in 3 handlers, not "~83".
- [x] **QUAL-9** [FAF] (P1) — **DONE 2026-06-03.** **Tail reconciled (Invariant #8, user-approved 2026-06-03):** a
      code reconciliation found QUAL-28 had absorbed even more than credited — dup-`session_id` crash, `action_name`
      keying, `get_or_create_context`, strong task refs, bounded+reaped store, **timeout monitor `wait_for`** (already
      `base.py`), **duplicate write-back processor** (both `_process_action_metadata*` already deleted), **timer-
      cancellation cleanup** (already store-owned), and **capture-before-pop** (record passed by reference) were ALL
      already done. The only genuinely-open tail items were **(1)** the per-action **metrics re-key** and **(2)** TEST-3.
      Both landed 2026-06-03: `metrics._active_actions` now keyed by the unique `(domain, action_name)` pair (was
      `domain` alone → two same-domain timers clobbered each other's metric; the first leaked as perpetually-running);
      `record_action_completion` takes `action_name`; all 9 callers updated; **TEST-3 seed** added
      (`test_metrics_concurrent_same_domain_no_clobber` + the existing F&F-lifecycle tests in `test_action_store.py`).
      `test_set_timer_end_to_end` is green (the F&F half + QUAL-11 recognition half — timers work end-to-end). _Original
      remediation framing:_ Remediate F&F (ranked in the review). **★ MERGED 2026-06-02 (user, Invariant #8):** the
      F&F **launch + completion** path (`base.py`) is the same code as QUAL-28's action-store relocation (the
      authoritative liveness = the task ref, created in the launch), so the launch/completion fixes — **(1)** dup-`session_id`
      crash, **(2)** `action_name` keying, **(3)** `get_or_create_context` (now real), **(4)** task refs, **(5)**
      unbounded leak — **move into QUAL-28 stage 3.2/3.3** (registered into the runtime store with the real task ref +
      fire completion). **QUAL-9's remaining tail:** per-action **metrics re-key** (`metrics.py` domain→action_name),
      **delete the duplicate** `workflow_manager._process_action_metadata_integration`, **timeout monitor** `wait_for`
      (not flat-sleep) + capture-before-pop, finish timer-cancellation cleanup (`timer.py`), then **TEST-3**. Gated by
      Invariant #4. _Original P0/P1 detail below (mostly absorbed by QUAL-28):_
      **P0s:** (1) **timers crash on launch** —
      duplicate `session_id` kwarg in `execute_fire_and_forget_with_context` (`base.py:125`+kwargs vs
      `timer.py:228`) → `TypeError`, only `ValueError` caught → timer creation fails outright; (2) **domain vs
      action_name key mismatch** — launch stores `active_actions[action_name]` (`base.py:500`), removal keys by
      `domain` (`base.py:636`) → `remove_completed_action` always misses → leak + dead completion/metrics/
      notifications; fix by keying everything on the unique `action_name` (also fixes same-domain clobber); (3)
      **`get_or_create_context` doesn't exist** (only `get_context`) — called in `base.py:633`/`notifications.py:174,229`/
      `debug_tools.py:101` → swallowed `AttributeError`; (4) **action tasks orphaned** (GC-cancellable) — hold strong
      refs; (5) **`active_actions` unbounded** — bound + prune (MemoryManager skips it). **P1s:** timeout monitor
      `wait_for` not flat-sleep; capture-before-pop; collapse the two write-back processors; per-action metrics keying;
      finish timer-cancellation cleanup (`timer.py:631`). Then **TEST-3** lifecycle coverage. Gated by Invariant #4.
- [x] **QUAL-10** [PEX] (P1) — Text→parameters (parameter extraction) full review. **DONE 2026-06-01** →
      `docs/review/parameter_extraction_review.md` (6×P0, 11×P1, 12×P2). Verdict: donation-driven extraction is
      largely **aspirational** — in practice it's spaCy NER + per-param regex + heuristics with **no contract
      enforcement**; the richest author-facing mechanisms (`slot_patterns`/`token_patterns`/`ParameterSpec.
      extraction_patterns`) are validated-then-discarded **dead code**; the two NLU providers extract with divergent
      contracts; failures are swallowed silently; resolvers *fatally crash* on asset-loader timing while the rest
      *silently no-ops*.
- [x] **QUAL-11** [PEX] (P1) — **DONE (lightweight T1 scope, 2026-06-03; Stages A–E).** Remediate parameter-extraction gaps (ranked in the review).
      **Stage A DONE (2026-06-03):** fixed the **timer recognition gap at its root** — a Cyrillic normalization
      asymmetry in `hybrid_keyword_matcher._normalize_text` (NFKD+combining-strip folded «й»→«и»/«ё»→«е», so raw
      donation patterns like `таймер` never matched normalized input → every й/ё phrase silently unrecognized);
      switched to non-destructive `NFC`. Also fixed P0 #1 — the phantom default `provider_cascade_order`
      (`keyword_matcher`/`spacy_rules_sm`/`spacy_semantic_md` → real `hybrid_keyword_matcher`/`spacy_nlu`) and the
      phantom `keyword_matcher` always-on fallback. `test_set_timer_end_to_end` flipped **xfail→PASS** (timer works
      end-to-end: recognition + QUAL-28 F&F).
      **Stage B DONE (2026-06-03):** de-fatalized the entity resolvers (P0 #4) — `_load_device_types`/
      `_load_location_keywords` no longer raise uncaught `RuntimeError` (which aborted any device/location request
      before deferred asset-coordination ran); they now warn-once + return `{}`, so resolve() degrades (skips
      type/here-inference, keeps exact/fuzzy name matching) instead of crashing.
      **Decision (2026-06-03, user) — QUAL-11 takes the LIGHTWEIGHT extraction contract (T1):** keyword/NER + regex +
      CHOICE surfaces + lemmas (what the hybrid matcher — the hot path — actually runs). The heavy declarative tiers
      are split OUT of QUAL-11, not built here:
      • **P0 #2 (slot/token/extraction patterns = T2 spaCy-Matcher slot-filling) → PARKED, retargeted to QUAL-35**
        (must-have for smart-home/MQTT, ARCH-7/8). NOT removed (keeps the authored patterns + the option); but the
        silent validate-then-discard is made honest (the active contract is T1; T2 is a tracked future). No schema
        change → no UI-5 impact.
      • **`entity_type`/`room_context` consumption + the `_is_device_entity`/`_is_location_entity` heuristic swap (Q7b)
        → MOVED to ARCH-6** (activates with real room/device registration; all 66 `entity_type` decls are `generic`
        today, so the dispatch would be inert until ARCH-6 authors them). QUAL-11 keeps only the **safe, now-valuable
        cleanup**: unify the duplicate device-resolution path + add `_resolution_failed` markers.
      **Stage C DONE (2026-06-03):** unified the duplicate device resolution (deleted the hardcoded English-only
      `_resolve_device_entities` in `nlu_component.py` — it re-resolved with a different strategy + wrote keys nothing
      read; the asset-driven `ContextualEntityResolver` is now the single path); added `_resolution_failed` markers
      (scoped to attempted-but-unresolved device/location refs, for the QUAL-30 boundary); made the parked T2 patterns
      **honest** — `spacy_provider._validate_and_store_spacy_patterns` now documents that `advanced_patterns` is
      validated-but-not-applied (QUAL-35), killing the silent validate-then-discard footgun.
      **Stage D DONE (2026-06-03):** shared coercion base — `ParameterSpec.coerce()` (both NLU providers delegate; the
      "two contracts" divergence collapsed) + hybrid default-on-coercion-failure fix (P0 #3, no silent drop); typed
      **`IntentHandler.get_param(intent, name, default)`** accessor (P1 #6 — spec-driven coerce + declared default +
      required→`ParameterExtractionError`, the fail-loud → QUAL-30 boundary). Found+fixed a latent correctness bug on the
      timer exemplar: "5 минут" was creating a **5-second** timer (unit CHOICE had English-only `choice_surfaces` + the
      handler hardcoded `'seconds'` over the donation's `"minutes"` default) — authored Russian unit surfaces + adopted
      `get_param` in timer; TEST-0 hardened to assert "5 мин".
      **Stage E DONE (2026-06-03):** QUAL-22 — deleted the dead `_disambiguate_with_device_context` stub (computed then
      returned the intent unchanged; real capability-disambiguation is ARCH-6) + its 3 obsolete tests; P1-t — the 6
      handlers that shadowed `_create_error_result` with an incompatible `(intent, context, error)` signature renamed to
      `_error_result(context, error)` (31 call sites), so the error-result primitive has one canonical signature.
      _Per-handler `get_param` migration (the other ~10 handlers off ad-hoc `.get`) folds into **QUAL-34** — same
      handlers/files; consuming a declared param via the typed accessor IS QUAL-34's "wire-or-remove"._
      _Original P0/P1 detail below (P0 #2 → QUAL-35; P0 #4 ✓ Stage B; the entity_type half of P0 #4 → ARCH-6):_
      **P0s:** (1) fix the default `provider_cascade_order`
      default `provider_cascade_order` — it names non-existent providers (`keyword_matcher`/`spacy_rules_sm`/
      `spacy_semantic_md` vs real `hybrid_keyword_matcher`/`spacy_nlu`, `nlu_component.py:380`) + add a startup
      assertion; (2) decide the slot/extraction-pattern story (implement, or remove the dead author-visible fields);
      (3) make required-param a real contract on a **shared** extraction base (raise on missing-required, stop
      swallowing, always apply `default_value`, unify spaCy+hybrid → deterministic param surface); (4) de-fatalize
      the entity resolvers (degrade, don't crash the request, when the asset loader isn't wired) **and replace the
      brittle `_is_device_entity`/`_is_location_entity` heuristics + hardcoded device-domain set with the declarative
      `entity_type`-driven selection from the QUAL-29 contract (deletion moved here from QUAL-29 so the swap is atomic —
      the typed accessor IS the replacement, Q7b);** (5) **QUAL-22**
      (finish/delete the context-enhancement stub). **P1s:** typed `ParameterSpec`-driven entity accessor on
      `IntentHandler`; fix first-match span→value; default `_md` spaCy models for similarity; unify duplicate device
      resolution; **unify `_create_error_result` (P1-t, moved here from QUAL-27): the base uses `(text, error,
      metadata)` but 6 handlers override with `(intent, context, error)` — pick one canonical signature for the result
      helpers as part of the shared handler base.** Gated by Invariant #4 (config-ui). **Concrete failing case (found by TEST-0):** `поставь таймер
      на 5 минут` is not recognized (→ `conversation.general`) despite the timer donation being loaded — fix +
      verify via TEST-0's `test_set_timer_end_to_end` (currently xfail).
- [x] **QUAL-12** [TXTPROC] (P2) — Text-processor subsystem review. **DONE 2026-06-01** →
      `docs/review/text_processing_review.md` (5×P0, 6×P1, 6×P2). Verdict: the subsystem is **mostly decorative at
      runtime** — `process()` is hardcoded to stage `"general"`, so only `general_text_processor` ever runs (on ASR
      output); the `asr_output`/`tts_input` stages are never routed; **TTS synthesizes raw text** (no normalization
      call site); the `[text_processor.normalizers.*]` config tree is **dead** (never read); the WebAPI 500s on a
      phantom `self.processor`; `number_text_processor` duplicates `asr_text_processor` and is unreachable;
      `NumberTextProcessor.process()` calls a non-existent method. **LLM-for-text-processing answer:** architecturally
      possible (open provider interface + DI), not wired today (only the dead `universal_llm` path), and should only
      be an **opt-in online-only `asr_output` stage** augmenting the deterministic default — never on the default path.
- [x] **QUAL-13** [TXTPROC] (P1) — **DONE 2026-06-03 (collapse + wire; Stages 1+2).** **(1) Collapsed** the 4 stage-
      specific providers → ONE config-driven **`UnifiedTextProcessor`** (`providers/text_processing/unified.py`): stages
      are now DATA — per-normalizer `stages` lists in `[text_processor.normalizers.*]` drive a fixed-order chain
      (numbers → prepare → runorm). Deleted the 4 provider files + entry-points + their config schemas (→ one
      `UnifiedTextProcessorProviderSchema`); collapsed `config-master`/`TextProcessorConfig` onto the single
      `normalizers` tree (dropped the dead `[providers.*]` split + `number_options`). **(2) Wired both real stages:**
      `process(text, stage="asr_output")` passes the caller's stage (ASR path, `voice_assistant.py`); **added the
      missing `tts_input` normalization before TTS synthesis** (`_handle_tts_output` — TTS spoke raw text before, so
      number/symbol normalization never ran on responses). **(3) Deleted the dead:** `self.processor` WebAPI 500 bug
      (3 endpoints rewritten onto the unified provider's introspection), `NumberTextProcessor.process()`,
      `_stage_providers`, the never-read `number_options`/duplicate config tree. **(4) Deps documented:** RUNorm is now
      **opt-in (`enabled=false`)** with a "downloads a HF model" note (offline hazard); lingua-franca → ovos-number-parser
      (Stage 1 / ASSET-3). Tests: `test_text_processing.py` (5, green); suite 26/26. **Carve-outs (deferred, not blockers):**
      (5) optional `llm_text_processor` (asr_output) → **QUAL-15** (gated on a real LLM); the dead `universal_llm`
      ASR-enhance path (`asr_component.py`) → **QUAL-15** (LLM territory). **Invariant #4 SATISFIED (verified 2026-06-03,
      user-prompted):** config-ui's config editing is **schema-agnostic** — `ConfigurationPage` fetches the backend
      Pydantic schema (`getConfigSchema()`) and renders each section via a generic recursive `ConfigSection` (it renders
      the `providers` tree + nested `normalizers` dynamically; the only `text_processor`-specific code is a name alias).
      The `TextProcessorConfig` TS type already uses generic `Record<string,Record<string,any>>` dicts, so the new shape
      matches. Zero config-ui files changed; `npm run type-check` **and** `npm run build` pass clean. No UI-5 carve-out
      needed for the config editor. _Original spec:_ Refine per QUAL-12: **collapse + wire.** (1) Collapse the 4 providers into ONE
      config-driven `TextProcessor` with ordered **per-stage normalizer chains** (make the config tree real, delete
      the provider-per-stage classes + redundant `number` provider); (2) **actually wire the two real stages** —
      `process()` must pass the caller's stage (`asr_output` at `voice_assistant.py:383`) and **add the missing
      `tts_input` call before TTS synthesis** (`:707`) so Russian TTS normalization (RUNorm) actually runs; (3)
      delete the dead (`self.processor` WebAPI bug, `NumberTextProcessor.process()`, `_stage_providers`, the
      `number_options` keys that map to nothing); (4) document real deps (RUNorm runtime model download, lingua-franca
      ru-only fallback); (5) optionally add a disabled-by-default online `llm_text_processor` (asr_output). Gated by
      Invariant #4 (config-ui). Intersects ASSET-3, QUAL-15.
- [x] **QUAL-14** [LLM] (P1) — LLM usage + offline-first review. **DONE 2026-06-01** →
      `docs/review/llm_usage_review.md` (3×P0, 9×P1, 12×P2). **NLU confirmed LLM-free**; offline-first is real for
      recognized intents but the **LLM stage's offline fallback is a phantom** — the configured `console` LLM
      provider **does not exist** (no class/entry-point), `fallback_providers` is never used at runtime, and
      `generate_response` hard-fails offline. The pipeline survives offline only because the conversation handler
      independently `is_available()`-gates to templates. **NLU-LLM recommendation: keep NLU deterministic +
      offline-first; any LLM assist must be opt-in and LOCAL (not cloud) — gated on a real local LLM, which ties to
      ARCH-9/10 [INFER]. Fix the offline foundation + QUAL-11 extraction first.** Prompt inventory captured for QUAL-16.
- [x] **QUAL-15** [LLM] (P1) — **DONE 2026-06-03 (Stages A–C).** Act on QUAL-14: the offline LLM foundation was
      fictional (phantom `console`, `fallback_providers` never iterated, `generate_response` raised offline).
      **Stage A (P0s):** real **`ConsoleLLMProvider`** offline floor (+ entry-point) — deterministic, no network, always
      available, localized "unavailable" message; `fallback_providers` now actually iterates via a shared chain
      (default → fallback_providers → console terminal) driving both `enhance_text` and `generate_response`;
      `generate_response` never raises (console terminates the chain). The component's `is_available()` override
      excludes the console stub (the conversation handler keeps preferring its own template — no regression). Clears the
      QUAL-23 phantom-console startup ERROR. Localized text externalized to **`assets/localization/llm/{ru,en}.yaml`**
      (the localization asset category, via `get_localization`) — no hardcoded message arrays.
      **Stage B (user):** added **DeepSeek** (`deepseek-chat`/DeepSeek-V3, OpenAI-compatible at api.deepseek.com, the new
      `default_provider`, matching `../personal_vpn`) and **removed VseGPT entirely** (provider/entry-point/schema/
      credential/alias/configs). **Offline-safe boot:** added optional env-var syntax **`${VAR:-default}`** + made LLM
      api_keys optional, so an enabled cloud LLM with no key no longer hard-fails boot (provider declines → console floor).
      **Stage C (P1s):** `openai.is_available()` → LOCAL check (was a network probe that returned True even on failure);
      per-call timeouts on openai/anthropic/deepseek; providers now **raise** on call failure (was silent original-text /
      canned string) so the chain handles fallback; fixed the dead ASR `universal_llm` lookup (→ the real LLM component,
      gated on a real model). Tests: `test_llm_fallback.py` (4); suite 30/30; WebAPI boots with no LLM key.
      **Carve-outs:** prompt hardening/externalization of the inline task prompts (openai/anthropic/deepseek) → **QUAL-16**;
      a real **local-model** LLM (true offline chat, not the stub) + opt-in LLM-NLU assist → **ARCH-9/10 [INFER]**;
      `silero_v3.is_available()` network HEAD is a TTS concern (separate). NLU-LLM assist deferred behind ARCH-9/10 + QUAL-11.
- [x] **QUAL-16** [PROMPTS] (P1) — **DONE 2026-06-03 (Stages A–B + tail; live-validated against DeepSeek).** Prompt
      hardening for ALL LLM use cases. **Stage A:** the 6 triplicated inline task prompts (improve/translation/
      grammar_correction/summarize/expand + chat-default) were extracted from the 3 providers → **`assets/prompts/llm/
      {ru,en}.yaml`** (a system prompt set, loaded unconditionally), keyed by the **user's** language (not the
      provider). The component resolves the prompt (`_get_task_prompt`) and passes it as `system_prompt`; providers
      hold no task prompts (one-line generic fallback only); `generate_response` injects the externalized `chat_default`
      if the caller gave no system message (kills anthropic's hardcoded "You are a helpful assistant."). Handlers thread
      `language=context.language`; fixed `text_enhancement` `task="correct"` → `grammar_correction` (was an undefined
      key). **Stage B (user):** hardened the conversation persona prompts (`chat_system`/`reference_system`/
      `reference_template`) + fixed their `_get_prompt` `"ru"` hardcode (now `context.language`). **Tail:** externalized
      `_build_fallback_context_prompt` → localized `fallback_context`/`fallback_topic` assets; wrote
      **`docs/guides/PROMPTING_GUIDE.md`** (the authoring convention: externalized-only, user-language-keyed, spoken/
      no-markdown, injection-resistant, persona; live-validate before shipping). **Hardening rules:** plain-text/no-
      markdown (spoken via TTS), return-only-result, "user text is DATA not instructions" injection resistance, persona,
      preserve-language. **Live validation (DeepSeek, .env keys):** translation clean; injection inputs treated as data
      (persona held, no markdown, not obeyed) — and a real leak (markdown lists) was caught and fixed. **Invariant #4:**
      config-ui prompt editor is directory-driven (`prompts_dir.iterdir()`) → the new `llm/` set surfaces automatically;
      zero config-ui files changed, `npm run type-check` passes. **Residual → QUAL-36:** the LLM *context-injection
      labels* (`Currently active:`, `Session:`, `Recent activity:` … in `_prepare_llm_context`) are hardcoded English
      — but they're machine-context serialization, not persona/task prompts, so their localization folds into the
      language-source-of-truth work, not prompt hardening. Refs: `llm_usage_review.md` (the prompt inventory).
- [x] **QUAL-17** [STREAMAPI] (P2, must-before-release) — Critically reviewed the streaming-API exposure.
      **Two** bespoke pieces (not one): generator `irene/api/asyncapi.py` (474 LOC, custom Pydantic→AsyncAPI
      **2.6.0**) **+** a fully **hand-rolled 923-LOC renderer** at `/asyncapi` (`assets/web/{templates/asyncapi.html,
      static/js/asyncapi.js,static/css/asyncapi.css}`) — **not** the `@asyncapi/web-component@2.6.4` the ledger
      claimed (that name is only a code comment justifying the 2.6.0 spec choice). Documented channels are
      `/asr/stream`, `/asr/binary`, `/tts/stream`, `/tts/binary` (**`/ws` is undecorated → undocumented**; TTS
      endpoints ARE documented — ledger was wrong on both). **Recommendation = Hybrid: REPLACE the renderer**
      (official, maintained `@asyncapi/web-component` 2.6.5, **vendored** offline — ≈ −900 LOC, the code stops
      claiming a dep it doesn't use) **+ KEEP-and-improve the generator** (no maintained drop-in introspects raw
      FastAPI WS routes; FastStream = broker framework, wrong shape; fix lossy `_clean_property_for_asyncapi`;
      decide 2.6.0-vs-3.0 deliberately). Done: `docs/review/streaming_api_review.md` with keep/upgrade/replace rec.
- [x] **QUAL-18** [STREAMAPI] (P-TBD) `[release]` — **DONE 2026-07-04, RE-SCOPED at task start (user, interactive)
      from "swap renderer, keep generator" to "retire the AsyncAPI subsystem, replace with a user-facing protocol
      guide".** Reconciliation killed the original plan's premise: the live `/asyncapi.json` emitted
      **`channels: {}`** (verified against a running server) — every documented channel (`/asr/stream|binary`,
      `/tts/stream|binary`) had been deleted by later work (ARCH-21 PR-4, ARCH-10) while the four REAL WS
      endpoints (`/ws/audio`, `/ws/audio/reply`, `/ws/observe`, `/ws/output`) were never in the spec; the
      "code-first can't drift" premise self-refuted (decorators document claims, not `send_json` reality).
      2026 ecosystem re-check: renderer solved (`@asyncapi/react-component` v3.1.3, offline-vendorable) but NO
      maintained FastAPI-WS→AsyncAPI introspector exists (fastws dead since 2023); user chose retirement over
      spec-as-artifact/rebuild. **Deleted (~2,000 LOC):** `irene/api/asyncapi.py` (474), `irene/web_api/`,
      bespoke renderer (`asyncapi.html`/`.js`/`.css`, 923), 7 dead WS message models in `api/schemas.py` (343),
      `get_websocket_spec` interface + ASR override, `_generate_asyncapi_spec` + 4 routes
      (`/asyncapi{,.json,.yaml}`, `/debug/asyncapi`), `irene.web_api` refs in import-linter contracts.
      **Replaced by:** `docs/guides/websocket-api.md` — all four live WS protocols frame-by-frame (register
      handshake, streaming/batch utterance loops + BUG-13/17 bounds, canonical QUAL-55 response frame,
      `speak_begin/PCM/speak_end`, missed-announcement redelivery, `/ws/output` client_id pairing,
      `/ws/observe` token gate + filters, a runnable Python example) + `docs/images/ws-protocols.{dot,png}`
      (house style) + links from `dataflow.md`/`esp32.md`/`howto-new-test.md`; web index page repointed
      (it also listed the deleted `/asr/stream|binary`). Verified live: `/asyncapi*` → 404, index renders the
      guide pointer. Suite 1180 green; 10 import contracts kept; smoke green.
- [x] **BUG-37** [NLU][TTS][UX] `[deferred]` — **✓ DONE 2026-07-19. Spoken sensor readings were unrounded,
      mis-vocalized and ungrammatical** («Сейчас 24.125 градусов — Тёплый пол»; latent until the bridge's
      DRV-23 made `read_state` return values). All three compounding defects fixed:
      **(a) rounding** — the read-state path now rounds the SPOKEN value to an integer (language-agnostic;
      both quantities read today are integers in speech) while `metadata.read.value` keeps the raw sensor
      reading for machine consumers.
      **(b) the Russian decimal reading** — `decimal_to_text_ru` keeps its money path verbatim (units given)
      and gains the real mathematical fraction reading when called bare (the TTS path): «двадцать четыре
      целых пять десятых», denominator by decimal depth (десятых/сотых/тысячных, quantized at 3), trailing
      zeros stripped, feminine agreement («две целых одна десятая»), docstring promise finally true. Fixes
      EVERY spoken Russian decimal system-wide (`all_num_to_text` feeds the TTS text-processing stage and
      silero), not just temperatures.
      **(c) numeral-unit agreement, both languages** — new `plural_form` util (RU three forms + 11–14
      exception; EN singular|plural; single form invariant) + `_unit_form`/`_speakable_number` handler
      helpers; templates carry `|`-separated forms (`unit_degrees`/`unit_percent`/`unit_minutes`, minutes
      accusative) and `{unit}` placeholders across read_temperature/read_humidity/confirm_setpoint/
      confirm_brightness/confirm_position(_room)/confirm_cleaning_delay in BOTH template sets — «один
      градус / 24 градуса / пять градусов», "1 degree / 24 degrees". Blast radius checked: the money path
      and `normalize_numbers_to_digits` untouched; full suite 1453 green. Tests: new
      `test_spoken_numbers.py` (decimal reading 10 cases, plural_form RU/EN, all_num_to_text integration);
      F30/F31/F32 assertions moved to the rounded+declined speech. docs: none — the smart-home guide
      describes sensor reads at a granularity the rounding doesn't alter (no doc shows raw decimals).
      contracts: none — spoken-text only; `metadata.read.value` (the machine surface) unchanged.
- [x] **BUG-39** [MQTT][UX] `[deferred]` — **✓ DONE 2026-07-19. The ambiguity clarification lists identical
      names, so it cannot be answered.** «включи кондиционер в гостиной» asked: *«Какой именно: Кондиционер
      или Кондиционер или Кондиционер?»* `_ambiguous_result` (`smart_home.py:253`) built the prompt from
      `c.get("name")` alone, while the candidate payloads carry `room`. Fix (owner phrasing ruling at intake:
      room-led): all-candidates-share-one-name asks by room via the new `clarify_which_room` template
      («Кондиционер есть в нескольких комнатах — в какой: Спальня, Детская или Гостиная?» — rooms stay
      nominative, no declension machinery); a mixed list qualifies only the colliding names («Кондиционер —
      Спальня»); when the rooms coincide too (two sconces in one room) the device id is the last honest
      qualifier. The answer resumes through the QUAL-31 combined re-run, so naming the room resolves the
      original command — verified answerable by design. Same code serves the capability-level path, fixed
      once; distinct-name lists unchanged. Tests: new `test_smart_home_ambiguity.py` (4 cases: room-led,
      mixed, within-room fallback, plain regression); handler + resolution suites green. Related: QUAL-63
      (priority rules) may later avoid asking at all. docs: guides/smart-home (room-qualified clarification
      sentence added). contracts: none — spoken-text change only; no versioned surface moved.
- [x] **BUG-42** [TEST] `[deferred]` — **Order-dependent flake:
      `test_arch36_satellite.py::test_recorder_declined_and_next_utterance_finalizes` fails in the full
      suite, passes in isolation** (its file also passes alone, 14/14). Reproduced identically on
      2026-07-11 pre- and post-BUILD-29 trees (1 failed / 1379 passed both times), so it is
      cross-file state leakage (another test's residue), not a recent regression. **CLOSED 2026-07-14 —
      FOLDED INTO TEST-20.** Same test, same defect: the diagnosis above was wrong — the failure DOES
      reproduce in isolation (8/20 measured at fix time), so cross-file leakage is falsified; one
      load-sensitive root cause (the test's mtime-ordering coin flip), fixed under TEST-20.
      docs: none — folded into TEST-20; test-internal.
- [x] **BUG-43** [ASR][CONFIG][I18N] `[deferred]` — **✓ DONE 2026-07-16 (filed same day by TEST-22's
      first run; pulled forward by the owner). `[asr] default_language` never arrived — the EN
      profiles' whisper decode hint was "ru".** Severity VERIFIED before fixing: the main voice
      pipeline calls `asr.process_audio(audio_data, trace_context)` with NO language kwarg
      (`voice_assistant.py:846`), so `self.default_language` — stuck at "ru" because `ASRConfig` never
      declared the field and the section's `model_dump()` dropped the TOML value — really did drive EN
      transcription. Fix per QUAL-36 (language policy is CANONICAL at CoreConfig top level, no
      per-section twins): `ASRComponent.initialize` now sets `self.default_language =
      core.config.default_language` before provider loading; the per-section reads with their "ru"
      literals are gone; the `[asr] default_language` lines are dropped from the three EN profiles
      (the surviving `default_language` entries are the canonical top-level one and open provider
      blocks the providers themselves read); the coherence-guard allowlist entry is removed (the
      mechanism stays, empty). Regression test added (canonical wiring asserted for en+ru); wiring
      also verified live for both languages. Verified: full suite 1426 passed / 7 skipped, guard
      14/14, import contracts 11/11. docs: none — `howto-new-language` already teaches exactly the
      canonical top-level field this fix wires to.
- [x] **BUG-44** [LLM][CONFIG] `[deferred]` — **✓ DONE 2026-07-19 (filed + completed same session; found
      answering an owner budget question).** **DeepSeek repoint: the configured `deepseek-chat` id is a
      legacy alias DeepSeek retires 2026-07-24 15:59 UTC** — five days out; past that date all six
      deployment configs' LLM tier (conversation + the QUAL-50 LLM NLU tier) would fall to the console
      floor. The alias last serves deepseek-v4-flash (non-thinking), so the repoint pins that id
      explicitly: `model = "deepseek-v4-flash"` in config-master + all 6 deployment configs, provider
      default + `get_available_models` + provider-schema default moved. **Budget refresh rides along**
      (the owner's "budget seems too tiny" instinct — V4 family is 1M context / 384K max output vs the
      pinned V3-era 64k/8k): capability table gains `deepseek-v4-flash`/`deepseek-v4-pro` at
      1_048_576/384_000, the legacy aliases kept mapped to the same budgets until retirement (a
      straggler config gets real budgets, not the 8k fallback); config `context_window` raised to
      1048576; `max_tokens` KEPT at 8000 as a deliberate spoken-reply ceiling (comment says so).
      Budget tests moved to the v4 ids; the fit_messages trim/overflow tests now exercise via explicit
      `context_window=64_000` overrides so they stop chasing capability bumps. Cross-repo rider: the
      commons eval judge (`eval/shared/deepseek-judge.yaml` + ARCHITECTURE.md snippet) rode the same
      retiring alias — repointed in commons (voice co-develops eval). Verified: budget suites 12
      passed, config-validator ci-mode all 8 configs valid, openapi drift + coherence gates green.
      docs: none — no manifest doc names the model id (checked guides/README/QUICKSTART/example).
      contracts: none — provider config + capability data; no versioned surface moved.
- [x] **BUILD-22** `[deferred]` [SATELLITE][PROCESS] — **✓ DONE 2026-07-12 (same-day intake→completion; REDEFINED
      at intake per PROD-15/HK-4 — two reversals vs the frozen BUILD-20 D-6/D-7 text: the nginx Plane-B tree MOVES,
      and ARCH-23/ARCH-44 export-close).** locveil-satellite bootstrap + ESP32 estate relocation. Shipped:
      **(1)** `locveil-satellite` instantiated from `../locveil-commons/process/new-repo-template/` @ scope-v3
      (satellite `121f3d0`): CLAUDE.md with the pinned shared blocks (hashes byte-identical to this repo's) +
      repo-local LAW (esp32-only-charter, phase-gates DES→PCB→FW, hw-gated, per-device-tags, per-device-apps,
      consumer-pins, no-execution-toolchain-at-bootstrap), ledger triad seeded with the PROD-15 born backlog
      (DES-1..4, OPS-1..2), vendored guard + hook + `ledger-guard` CI — first commit passed the hook; skeleton
      `components/ boards/ provisioning/ contracts/`. **(2)** Design corpus migrated (satellite `37dcac5`):
      `esp32_satellite.md` (§4.1–4.3 wire tables demoted to a pointer at `docs/guides/websocket-api.md` + the
      satellite's contracts pin), `ws_esp32_transport.md` (frozen lineage), `docs/architecture/esp32.md`,
      `esp32-{fit,turn}` diagrams — pointer stubs left at all three old doc paths, frozen history stays here.
      **(3)** Top-level `ESP32/` tree DELETED (2026-07-08 verdict, reconfirmed HK-4). **(4)** `nginx/` →
      satellite `provisioning/`; voice keeps the pinned `contracts/esp32-site.conf.j2` (new contracts-README row
      with the re-pin command) and `test_arch36_tls_e2e.py` renders the pin — re-run green (1 passed); operator
      inventory/group_vars copied on disk + gitignored satellite-side; `ops/INSTALL.md`/README/guides re-pointed;
      WB7 ops handover journaled (deployed plane untouched). **(5)** ARCH-23 → satellite FW-1 and ARCH-44 →
      satellite DES-5, both export-closed above. STAYED here (reconfirmed): `websocket-api.md`
      (`ws-protocol-doc-canonical`), `irene/satellite/` + the Python satellite docs, client registry/CSR code,
      frozen reviews/archives. Sibling: ARCH-47 (WS version stamp / wake-pack pin surface) remains open.
      docs: readme, install, arch/esp32, guides/satellite (retro-verdict, BUILD-35 cutover)
- [x] **BUILD-23** `[deferred]` [PROCESS] — **DONE 2026-07-11 (narrowed at intake per the PROD-5 delegation:
      the "separate drift-guard script" wording was dead — scope-guard's `claudemd` hash rule IS the drift
      guard, shipped in `scope-v3`).** Shared CLAUDE.md blocks — voice-side adoption (HK-2/PROD-5, normative
      `../locveil-commons/process/claude-md.md`). Inserted both pinned digest blocks (`shared-invariants`,
      `cross-repo-board`) between `locveil:begin/end` markers at `scope-v3`; deleted the six long-form shared
      invariants they replace (`single-task-ledger`, `one-active-journal`, `every-task-in-the-ledger`,
      `design-then-implement`, `review-then-remediate`, `task-start-reconciliation` — voice specifics kept as
      the compact `ledger-dialect` bullet; CLAUDE.md 165→160 lines, hard no-growth criterion met). Re-pinned
      scope-guard at `scope-v3` (1.1.0) + `[claude]` hash section in `.scope-guard.toml` (hashes match
      `--hash-blocks`; tamper test fails correctly, restore passes). Rewrote the retired pre-board
      uncommitted-intake bullet in `cross-repo-source-of-truth` (board-as-outbox vs direct operational
      filings). Renamed `config-master-canonical` → **`config-master-file`** (CLAUDE.md + legend row +
      `docs/design/multilingual_deployment.md`; frozen archives untouched; bridge renames apart as
      `config-master-tree`). CI paths-filter gained `CLAUDE.md` per the HK-2 convention. BUILD-22 gained the
      dependency: instantiate `process/new-repo-template/`, never freehand.
- [x] **BUILD-24** `[deferred]` [COMMONS][TEST] — **DONE 2026-07-12 (PROD-16 delegation; BUILD-20 D-11 /
      PROD-7).** Scripted contract re-pin + release-time staleness gate, born against the final bridge
      layout. **`scripts/repin.py`** — a generalized, family-registry-driven tool (catalog /
      report-protocol / esp32-site: owner repo, committed artifact paths, pin destination, conformance
      pointer): `repin <family> [--tag]` fetches the owner's committed artifacts at the newest (or given)
      family tag via `git show`, writes verbatim copies + a STRICT `PIN.json` (core fields, `files`
      sha256 map, conformance pointer, mirrored owner-STAMP extras — commons `test_pin_matches_stamp`
      asserts `bridge_commit`/`catalog_version`); `--check` is the staleness gate (pinned tag vs owner's
      newest family tag; untagged families compare pinned bytes vs owner `main`) — RELEASE-TIME only,
      never a cross-repo push gate (convention §5). Make surface: `make repin CONTRACT=… [TAG=…]` +
      `make repin-check` in `eval/Makefile`; `eval/README.md` documents the flow. **First real run
      executed:** catalog re-pinned at the bridge's fresh **`catalog-v1.5`** (VWB-29 landed bridge-side
      today — the gate opened) → golden byte-identical, openapi/STAMP refreshed, commons catalog
      `PIN.json` upgraded legacy→strict (contract-guard warnings 3→1, only the co-owned
      crossover-fixtures pin still pending its own task), commons pin README re-pin flow rewritten to
      the scripted path (commons `08eabe0`). Verified: commons eval suite 40/40, `repin-check` green
      across all three families, pyright 0.
      docs: eval/readme
- [x] **BUILD-26** [BUILD][UI] `[deferred]` — **DONE 2026-07-12 (PROD-16 delegation — the convention's
      repo-internal instance).** `config-ui/openapi.json` (found stale during REL-4: four config-section
      schemas never re-dumped; that instance was fixed then — this task shipped the missing MECHANISM).
      Chose the keep-committed + drift-guard arm (the contract-pin mechanic, per the PROD-16 note):
      **`irene/tests/test_openapi_drift.py`** rebuilds the schema in-process exactly as
      `scripts/dump_openapi.py` does (same `build_app`) and fails on ANY drift with the regeneration
      command in the message — runs in the standard suite, so the CI backend job gates it; skips cleanly
      without the webapi extra. Convention surface: **`contracts/ui-openapi/`** STAMP + pointer README
      (artifact stays `config-ui/openapi.json`; STAMP versions the convention surface, not each
      regeneration — content moves with code under the guard), registry row, tag **`ui-openapi-v1`**.
      Reconciled at start: current dump == committed (NO drift today). `config-ui-stays-functional`:
      `gen:api-types` re-run (types already current), `npm run check` + `npm run build` green.
      Contract-guard 0 warnings with the third owned surface registered.
      docs: none — repo-internal generated-contract guard; no manifest doc describes the schema artifact.
- [x] **BUILD-30** `[release]` [PROCESS][CI] — **DONE 2026-07-11.** Scope-guard cutover — the commons ledger
      guard consumed at the pinned tag **`scope-v2`** (PROD-13 / HK-1 delegation, board entry
      `../locveil-commons/board/BOARD.md`; normative convention `../locveil-commons/process/ledger-discipline.md`).
      Replaced `scripts/check_scope.py` with the commons-owned, config-driven `scope_guard.py` (regime 2 —
      behavior changes in commons only, moves by re-pin): vendored `scripts/scope_guard.py` + authored
      `.scope-guard.toml` (from the commons starter, verified against this tree); retired the local checker and
      re-pointed the CI `ledger-guard` job + `ledger` paths-filter (`.github/workflows/ci.yml`); committed
      `hooks/pre-commit` + one-time `core.hooksPath hooks` running `--check`; invariant text updated
      (`single-task-ledger`, `one-active-journal` in CLAUDE.md; RELEASE_PLAN.md gate wording; the two design
      docs naming the old checker) in the same change; DONE-ledger rotation adopted + the overdue journal
      rotation run via `--rotate` in its own commit (journal 1510→708, DONE 4273→1930, verified lossless);
      required-task-tags rule ON. Fixed the two pre-existing findings invisible to the old checker: unsorted
      DONE I18N section, DONE ledger over the 4000-line hard ceiling. Cutover proof held: vendored tool green
      before the local script was deleted. **Found a real scope-v1 bug on the first rotation attempt** —
      `rotate_journal` exploded section bodies char-per-line (tuple double-indexing); hit concurrently by
      bridge OPS-22, fixed commons-side as `scope-v2` (`09a9025`), which this task pins.
- [x] **BUILD-31** `[deferred]` [OPS][CONFIG] — **DONE 2026-07-11 (filed + completed same day; user-directed).
      Problem reporting enabled in all six deployment profiles + reports-repo rename adopted.** Root cause
      (found at intake, user question): ARCH-31 added `[reports]` to master/example and the `report` handler
      to all six docker configs, but never the **section** — profiles fell back to the Pydantic default
      (`enabled=false, repo=""`), so BUILD-15's token plumbing could never activate reporting on a controller
      (`setup_problem_reporting` returns early; INSTALL.md's "token lets reports file themselves" was false).
      All six profiles (`embedded-{armv7,aarch64}{,-en}`, `standalone-x86_64{,-en}`) now carry
      `[reports] enabled=true, repo="locveil/locveil-reports"` — the token is the only activation switch,
      degrading to the honest off state without it. Rename adopted repo-wide: the reports repo moved
      `droman42/wb-user-reports` → **`locveil/locveil-reports`** (org move, verified via `gh` — old name
      redirects, `droman42/locveil-reports` is 404); updated CLAUDE.md `problem-report-inbox`, `/inbox` skill
      (all `gh` commands), master `repo` example comment, `github_report.py` docstring, design D-1 rename
      note (frozen mentions annotated, not rewritten). User-facing docs per `user-facing-docs-are-done`:
      `docs/guides/problem-reporting.md` (profiles ship enabled; token completes it; own-repo path kept) +
      `ops/INSTALL.md` Secrets (org-minted PAT requirement + re-mint warning after owner moves).
      `[satellite]` absence from profiles confirmed intentional at intake (controller ≠ room node) — not
      touched. **Owner follow-up (operational, not code): re-mint the device PAT under the `locveil` org** —
      a `droman42`-owned fine-grained PAT cannot reach the org repo. Verified: 14/14 configs parse with
      expected reports state, master completeness/alignment + arch gates 18/18, report tests 25/25.
- [x] **BUILD-32** `[release]` [PROCESS][TEST] — **DONE 2026-07-12 (filed + completed same day; PROD-16
      delegation, council HK-5).** `contracts/` restructured to the convention's uniform pins shape
      (`../locveil-commons/process/contracts.md` §2 — immediate per q3, no grandfathering). Consumed pins
      moved to `contracts/pins/<name>/` with strict `PIN.json` (files sha256 map + conformance pointer):
      `report-protocol/` (artifact renamed to the owner's `report-protocol.json`, owner `STAMP.json` copied
      verbatim, tag `report-protocol-v1` @ `8fb983f`) and `esp32-site/` (pre-tag artifact-copy pin @
      satellite `37dcac5`; `version`/`tag` explicitly null until the owner stamps — fills at re-pin). Both
      copies verified byte-identical to their owner artifacts before the move. Registry
      `contracts/README.md` rewritten direction-labeled (Owned: `ws-protocol`/`wake-pack` arrive with
      ARCH-47; Consumed: the two pins; the commons-held catalog/crossover pins cross-referenced); per-pin
      READMEs carry the re-pin commands. Every consumer followed in the same change: the two conformance
      tests, `eval/Makefile` (`FIXTURES_JSON`, mock-bridge `--catalog`) +
      `device.promptfooconfig.yaml`/`device.tests.yaml` headers re-pointed at commons
      `contracts/pins/{crossover-fixtures,catalog}/`, the CLAUDE.md `cross-repo-source-of-truth` bullet
      (incl. the owner artifact's post-restructure home), the `/inbox` skill, `problem_reports.md` design
      pointers, two docstrings. Verified: contract-guard v1 green with ZERO warnings, report-protocol
      conformance 11/11, hermetic TLS e2e passes from the new template path, `make device-tests`
      regenerates byte-identically (header path aside).
      docs: none — contracts layout + tooling paths; the touched files are process-internal, not manifest docs.
- [x] **BUILD-33** `[release]` [PROCESS][CI] — **DONE 2026-07-12 (filed + completed same day; PROD-16
      delegation).** Contract-guard v1 vendored per the BUILD-30 scope-guard consumption model:
      `scripts/contract_guard.py` taken byte-exact from commons tag **`contract-guard-v1`** (tag verified ==
      commons working tree before vendoring; NEVER edit — re-pin to move, pin recorded in
      `contracts/README.md`). Wired: `hooks/pre-commit` now runs scope-guard then contract-guard (both
      `--check` only, hooks never mutate); CI gained a `contracts` paths-filter
      (`contracts/**`, `scripts/contract_guard.py`, the workflow itself) + a path-gated `contract-guard`
      job mirroring `ledger-guard`. CLAUDE.md `cross-repo-source-of-truth` teaches the vendored-file rule.
      Coherence layer only — scope-guard stays ledger-only. Verified: hook runs both guards green
      (contract-guard 0 warnings on the BUILD-32 tree).
      docs: none — enforcement tooling only (hook + CI job); no user-facing behavior changed.
- [x] **BUILD-34** `[release]` [PROCESS][TEST] — **DONE 2026-07-12 (filed + completed same day; PROD-16
      follow-up delegation — the completeness ruling's first instance, owner decision).** The LOCAL
      complete catalog pin, closing voice's push-time schema-conformance gap (voice consumes the catalog
      REST API at runtime — `parse_catalog`/`CatalogResponse` inbound, `CanonicalActionRequest`/
      `RoomCanonicalRequest` outbound — but its conformance was exercised only by the release-cadence
      cross-suite in commons). Shipped: **(1)** `contracts/pins/catalog/` holding the owner's FULL tagged
      set at `catalog-v1.5` (golden + openapi + STAMP byte-identical; a pin is always complete — usage
      never shapes it, contracts.md §2) + strict `PIN.json`; **(2)** `scripts/repin.py` generalized to
      multi-destination families — `make repin CONTRACT=catalog` writes BOTH the local pin and the
      commons crossover pin in ONE run at the same tag (per-dest conformance pointers; `repin-check` now
      walks every copy of every family — 4 pin copies, all green); **(3)** the NEW named push-time test
      `irene/tests/test_catalog_contract_conformance.py` (hermetic, normal CI suite): pin↔STAMP↔golden
      coherence, golden validates as `CatalogResponse`, `parse_catalog` accepts the pinned bytes,
      `DeviceCommand.request_body()` validates as `CanonicalActionRequest` (example built from the
      golden's own first actionable capability), `RoomGroupCommand.request_body()` as
      `RoomCanonicalRequest` — the commons crossover suite stays the deep gate; **(4)** registry README
      catalog row + cross-reference note reworked, per-pin README, CLAUDE.md
      `cross-repo-source-of-truth` bullet now teaches the two-copies-move-together rule, eval/README
      updated. contract-guard picked the pin up with zero changes (0 warnings). Verified: new test 5/5,
      full suite 1401 passed / 7 skipped, pyright 0, repin idempotent (commons copy byte-stable).
      docs: eval/readme
- [x] **BUILD-35** `[release]` [PROCESS][CI] — **DONE 2026-07-12 (filed + completed same day; PROD-17
      delegation).** Docs-convention dialect + scope-guard re-pin. Vendored `scripts/scope_guard.py`
      re-pinned at commons tag **`scope-v5`** (1.2.0 — the docs-verdict presence/syntax rule on
      completion entries); `.scope-guard.toml` gained `docs_verdict_since = "2026-07-12"` + the
      `shared-invariants` block re-pinned (byte-verified against the commons source; new digest line
      carries the docs-verdict invariant) with its recomputed sha256. CLAUDE.md
      `user-facing-docs-are-done` rewritten as the voice dialect of
      `../locveil-commons/process/user-docs.md`: `docs/manifest.json` is the scope authority,
      `ops/INSTALL.md` + `eval/README.md` enter scope via their nodes, completions carry the verdict
      line. The cutover retro-flagged NINE same-day completions (ARCH-23/44/47,
      BUILD-22/24/26/32/33/34) — each annotated with its honest retro-verdict in this change (real node
      updates: `guides/websocket-api` for ARCH-47, `eval/readme` for BUILD-24/34, BUILD-22's four; the
      rest `none` with cause). Verified: scope-guard 1.2.0 green, both hooks green, manifest coherence
      8/8 incl. the verdict-ids-resolve check against these very lines.
      docs: none — process dialect + enforcement re-pin; no manifest doc's content changed.
- [x] **BUILD-36** `[release]` [BUILD][ARCH][OPS][DOCKER] — **DONE 2026-07-13 (board PROD-21 / council
      HK-8; owner-closed with the WB7 install explicitly deferred — controller breakage becomes a fresh
      BUG).** Python backend layout & naming migration — one tree churn, executed + verified across commits
      1/n–13/n (`85dcc4d`…`b95f3b9`). **Layout/rename:** `irene/`→`backend/src/locveil_voice/` (src-layout),
      tests→`backend/tests/` (outside the package), uniform `irene`→`locveil_voice` (imports, 13 entry-point
      groups, import-linter contracts, dist `locveil-voice` +11 self-ref extras, dynamic version), the 3
      `__file__`-relative fixes + one cwd-relative `Path("irene/…")`, and the tooling root-detection the
      pyproject-in-`backend`/data-at-root split needs. **Config:** `configs/`→`config/` (singular);
      config-ui OpenAPI regen (schema names `irene__`→`locveil_voice__`) → **ui-openapi v1.1** bump + tag.
      **Eval/lock:** eval venv→`backend/.venv`; `uv.lock` regen. **Env & scripts (step 6):** pydantic
      `env_prefix` + explicit vars `IRENE_*`→`LOCVEIL_VOICE_*`; console scripts `locveil-voice-*` (+`irene-*`
      aliases for one release); docker-compose/INSTALL keys + the scripted `ops/cutover-env-locveil-voice.sh`
      (renames the one hand-edited `.env` token key, delivers compose, smokes `/health`). **Docker (step 7):**
      3 Dockerfiles (src-layout, `config/`, module paths, `LOCVEIL_VOICE_*`) + `verify_components` entry-point
      groups + `.dockerignore **/.venv`; **docs sweep** of 18 manifest nodes to the split-layout invocation
      model. **Cross-repo:** catalog re-pinned v1.5→v1.7 (bridge CORE-10 follow-through, both copies);
      board write-back; `install-irene.sh` deleted (orphaned bare-metal installer). **PROD-21 bounce
      resolved** (`b95f3b9`): 8 `discovery_paths` flipped + stale env/run refs swept across the 8 configs
      + `config-example.md` — and the requested tripwire proof showed `discovery_paths` is VESTIGIAL
      (`IntentHandlerManager.initialize` hardcodes the namespace, never reads it), so it was never
      boot-breaking → filed **ARCH-50** (review all such hardcodings/overrides vs dynamic build-and-loading).
      **Verified:** lint-imports 11/11, pytest 1408 passed, build-analyzer 14/14 profiles, config-ui
      check+build, contract-guard; the x86_64 image BUILDS + BOOTS locally (`/health` healthy; in-build
      `verify_components` gate "all 11 components import"); ARM images share the recipe (multi-arch CI
      dispatch). Persona "Irene" + deployment identity (`irene.toml`, `irene.log`, `~/.cache/irene`, the
      compose service key `irene`) kept per `python-layout.md` §3. **NOT part of this closure (owner's
      install):** rebuild/deploy the 6 GHCR images + boot-verify + `sh ops/cutover-env-locveil-voice.sh`
      on the WB7 — any breakage → a fresh BUG.
      docs: readme, contributing, quickstart, install, guides/asset-management, guides/audio, guides/build-docker, guides/build-system, guides/configuration, guides/howto-new-intent, guides/howto-new-language, guides/howto-new-model, guides/howto-new-test, guides/problem-reporting, guides/satellite, guides/tracing, guides/vad, guides/voice-trigger
- [x] **BUILD-37** [PROCESS] — **DONE 2026-07-14 (filed + completed same session; board PROD-22
  delegation, executed by the commons session on owner instruction): re-vendor contract-guard @
  `contract-guard-v2`.** `scripts/contract_guard.py` replaced byte-identical to the tag (1.1.0 —
  adds `TAG-MISSING`: an owned STAMP naming a git tag that doesn't exist now FAILS; the false-green
  class the bridge caught at catalog-v1.7). Check green, 0 warnings — all four voice contract tags
  resolve (`ws-protocol-v1`, `wake-pack-v1`, `ui-openapi-v1.1`, `docs-manifest-v1`). CLAUDE.md pin
  reference bumped v1→v2. docs: none — vendored tool + the dialect pin line only.
- [x] **BUILD-38** [PROCESS] — **DONE 2026-07-15 (filed + completed same session; board PROD-25
  delegation): contract-guard CI checkout fetches tags.** Intake reconciliation: the board's sweep
  ("voice is vendored at v1, the gap bites at the v2 re-pin") was stale — BUILD-37 had already
  re-vendored v2 on 2026-07-14 but left the v1 labels in the `ci.yml` step name and
  `contracts/README.md` (the lines the bridge sweep read), so the `TAG-MISSING` rule was live
  against a bare checkout and the job was latently broken NOW, commons-style. The re-pin half of
  the delegation was therefore already done; this task is the remaining checkout fix + the stale
  labels. Change: `fetch-tags: true` on the `contract-guard` job's checkout (per
  `process/contracts.md` §4; shallow stays); step-name + registry labels v1→v2. Verified by
  simulating CI locally: a `--no-tags --depth 1` clone fails 4× TAG-MISSING (the exact board
  signature), same clone after `git fetch --tags` is green; working-tree check green, 0 warnings.
  Voice ID written back into board PROD-25. docs: none — CI workflow + internal contracts
  registry label only.
- [x] **BUILD-39** [PROCESS] — **DONE 2026-07-15 (filed + completed same session; the push-day CI
  restore after run 29417879036 failed both gated jobs).** (a) **contract-guard: BUILD-38's
  `fetch-tags: true` does not work** — actions/checkout@v4 ignores the flag on its shallow
  fetch-by-SHA path (the run's checkout log shows a fetch with NO tag refspec; all four voice contract
  tags exist on origin). BUILD-38's simulation had validated `git fetch --tags` — the right *git*
  behavior — but not the *action's* wiring of it. Fix: an explicit `git fetch --tags --depth=1 origin`
  step before the guard (version-proof; re-simulated: bare shallow clone → fetch step → guard green,
  repo stays shallow). Cross-repo: the same latent bug sits in commons' workflow and possibly the
  bridge's checkout@v6 variant — correction recorded on board PROD-25 (commons executes its own fix;
  bridge verifies OPS-30; satellite's pending delegation inherits the explicit-step form). (b)
  **frontend-health: the UI-18/UI-17 sibling `file:` deps don't exist in a lone CI checkout** (npm
  produced dangling symlinks; tsc: `Cannot find module 'locveil-ui-kit'` ×12). Fix: the job checks out
  voice + locveil-commons side by side (both public; paths `locveil-voice/` + `locveil-commons/`),
  builds the ui-kit dist, then runs the unchanged gate (`npm ci` + check + build + test) — the
  dev-phase consumption model now holds in CI too. **Second round trip (run 29418418208):**
  contract-guard fix confirmed GREEN live; frontend-health exposed one more sibling gap — the
  workbench contract ships as SOURCE types (`exports "./contract"` → `src/contract.ts`), so voice's
  tsc checks that file and its `react` import resolves from the workbench's OWN tree → the job also
  runs `npm ci` in `packages/workbench` (failure reproduced locally by hiding its node_modules, fix
  proven by fresh `npm ci` → check green). docs: none — CI workflow only.
- [x] **BUILD-40** `[release]` [PROCESS][CI] — **DONE 2026-07-15 (filed + completed same session; commons
      scope-v6 / HK-10 delegation).** Vendored `scripts/scope_guard.py` re-pinned `scope-v5`→`scope-v6`
      (1.2.0→1.3.0 — the **UNREFERENCED-evidence** check, HK-10 ruling 1 / IMPL-2: the fourth direction —
      a doc on disk under `docs/review`/`docs/design` that NO ledger entry, active or DONE, references by
      path or basename is forgotten scope). `.scope-guard.toml` gained the explicit `unreferenced = "warn"`
      toggle in `[evidence]` (the commons default is already `warn`; spelled out to match `unindexed`) and
      its header re-stamped to `scope-v6 per BUILD-40`. Also swept the **stale CI comment** — the
      `ledger-guard` step said "vendored at scope-v3" (never updated through the v4/v5 re-pins) → `scope-v6`.
      No `[claude]` block re-hash: v6 touches only the guard code + evidence defaults, no CLAUDE.md content.
      **Verified at intake:** simulated the new rule against the tree — every doc under `docs/review`/`docs/design`
      is referenced, zero unreferenced warnings. **Verified after:** scope-guard 1.3.0 green (EXIT 0), the
      pre-commit hook path unchanged (`--check` only).
      docs: none — enforcement-tool re-pin; no manifest doc's content changed.
- [x] **BUILD-41** `[release]` [PROCESS][CONTRACTS] — **DONE 2026-07-18 (PROD-26 / HK-12 sweep, filed +
      completed same session; ONE commit with BUILD-42 — the keepers' one-sweep-per-repo condition).**
      Vendored `scripts/contract_guard.py` re-pinned `contract-guard-v2`→`contract-guard-v3` (1.1.0→3.0.0 —
      major now tracks the tag family): **ORPHAN-TAG** (registry-keyed reverse of TAG-MISSING),
      **CONTENT-DRIFT** (STAMPs enumerating `artifacts` are byte-frozen at their tag; voice's existing
      stamps carry no `artifacts` key and opt out unchanged), **VENDORABLE-UNREGISTERED** + `--relax-tags`
      (mid-bump tolerance). Voice deliberately ships **no `.contract-guard.toml`** — absent config = empty
      vendorable roots (the no-heuristic posture recorded at delegation). `hooks/pre-commit` contract-guard
      line gains `--relax-tags` + the mid-bump comment; CI `contract-guard` step re-stamped v2→v3 with the
      strict/no-relax posture spelled out; `contracts/README.md` guard paragraph v2→v3 + the §5
      staleness-is-repin's-job pointer (BUILD-43); CLAUDE.md `cross-repo-source-of-truth` mention v2→v3.
      **Verified:** contract-guard 3.0.0 green on the live tree in both hook (`--relax-tags`) and strict
      modes, zero warnings — all four owned tags + three pins pass the new rules.
      docs: none — enforcement tooling + process surfaces only; no manifest node's content changed.
      contracts: contract-guard consumed-tool pin bumped v2→v3 (its `[[tool]]` manifest row lands with
      BUILD-43's `.repin.toml`).
- [x] **BUILD-42** `[release]` [PROCESS] — **DONE 2026-07-18 (PROD-26 / HK-12 sweep, filed + completed
      same session; ONE commit with BUILD-41).** Vendored `scripts/scope_guard.py` re-pinned
      `scope-v6`→`scope-v7.1` (1.3.0→1.4.0): **CONTRACTS-VERDICT** — `.scope-guard.toml` gains
      `contracts_verdict_since = "2026-07-18"` (the sweep date; earlier completions frozen; spec
      `../locveil-commons/process/ledger-discipline.md` §7) — plus **UNKNOWN-PREFIX**. The v7.1 blocks
      release: the **`contract-triad`** pinned block pasted into CLAUDE.md between fresh
      `locveil:begin/end contract-triad scope-v7.1` markers, sha256 registered as the third
      `[[claude.blocks]]` entry. Intake reconciliation HELD: `shared-invariants` + `cross-repo-board`
      block hashes verified current at scope-v7.1 — only the new third block lands, no re-pin of the
      existing two. CI ledger-guard comment scope-v6→scope-v7.1; toml header re-stamped `per BUILD-42`.
      **Verified:** scope-guard 1.4.0 green live — this entry and BUILD-41's are the first to carry the
      verdict line the new rule enforces (retro on rollout day per the HK-6 precedent).
      docs: none — process/guard surfaces only (CLAUDE.md, `.scope-guard.toml`, hook, CI are not
      manifest nodes).
      contracts: scope consumed-tool pin bumped v6→v7.1; contract-triad block FIRST CONSUMED (pinned
      into CLAUDE.md between markers + hashed).
- [x] **BUILD-43** `[release]` [PROCESS][CONTRACTS] — **DONE 2026-07-18 (PROD-26 / HK-12; filed +
      completed same session; SEQUENCED BEFORE ARCH-58 so the core-py family is declared once, in the
      new format).** The org promotion of this repo's own BUILD-24 engine came home: `scripts/repin.py`
      is now the VENDORED commons tool at `repin-v1` (single stdlib file, replaces the local engine
      wholesale — never edit, re-pin to move). The FAMILIES dict converted to **`.repin.toml`**:
      `catalog` keeps its multi-dest (local push-time pin + the commons crossover copy, ONE run at one
      tag — the HK-12 commons-only cross-repo-dest carve-out, now tool-enforced), `report-protocol`,
      `esp32-site`, plus the `[[tool]]` vendored-tools manifest (scope-guard@`scope-v7.1`,
      contract-guard@`contract-guard-v3`, repin@`repin-v1` — the tag↔copy relationship out of prose).
      `make repin`/`repin-check` stay wired via `--config ../.repin.toml`; `repin-check` runs
      `--fail-on any` (today's release-gate semantics on the §5 ladder); `hooks/pre-commit` gained the
      warn stage (`--check --fail-on none || true`, offline-safe). Swept en route: the stale
      `catalog-v1.5` tag in the registry's consumed table (pins were at v1.7; the row now defers to
      `PIN.json`) and `eval/README.md`'s pre-HK-12 "staleness is checked at release time" prose → the
      severity ladder. **Verified:** `--check --fail-on any` green live — 4 pin dests + 3 tools all
      current (real ls-remote); `--fail-on none` exits 0; catalog re-pin DRY-RUN wrote both dests at
      `catalog-v1.7` (artifact bytes identical, PIN re-stamped), then restored.
      docs: eval/readme (repin/staleness paragraph — caused staleness fixed in the same change)
      contracts: repin FIRST CONSUMED as a vendored tool @ repin-v1; `.repin.toml` becomes the family
      registry (no pin content moved — all pins verified current).
- [x] **BUILD-44** `[deferred]` [CONTRACTS][SATELLITE] — **DONE 2026-07-18 (answered the day it was
      filed — the PROD-26 sweep pulled it, exactly as the filing anticipated; repo-to-repo filing by
      locveil-satellite, HK-12 round-1 greenlight).** The wake-pack v1.x bump confirmation — voice
      CONFIRMS, three commitments on record:
      **(1) Tagged bumps only.** The multi-model pack (one wake model per unit, ≥3 near-term per DES-7)
      ships as a tagged `wake-pack` version bump, NEVER an out-of-band edit of published files. The
      satellite's publish-refusal on drifted bytes is correct behavior to keep; the pack stays voice's
      UNMODIFIED third-party artifact (the wake-pack STAMP's own note already encodes the policy:
      words added = minor, replacing a published model file = major).
      **(2) The multi-word STAMP-shape ruling (voice's call, as asked):** the verification surface the
      satellite parses — files enumerated FLAT with per-file sha256 — stays stable across all of v1.x;
      adding words extends that enumeration, and any per-word grouping metadata is additive (readers
      ignore unknown keys). Only a change that breaks the existing flash-time hash-verification parse
      is major (v2).
      **(3) The drift addendum:** at the bump voice (a) reconciles/re-stamps the current upstream
      `irina.json` bytes (or restores the originals on HF), and (b) switches ALL STAMP + in-code
      catalog URLs (`_get_default_model_urls` builds `/resolve/main/` today) to immutable
      `/resolve/<hf_revision>/` refs — the STAMP already carries `hf_revision` — so a third-party
      `main` move can never invalidate a pinned pack again. On the cut: `re-pin owed: satellite`.
      Execution filed as **ASSET-6** `[deferred]` (the cut waits for the next trained words from the
      wakeword-training sibling; the answer needed no code today).
      docs: none — a contract-policy answer; the voice-trigger guide + STAMP move together at the
      ASSET-6 cut
      contracts: none moved — this entry COMMITS the wake-pack v1.x versioning policy (owner-side
      promise); the actual `wake-pack-v1.x` cut with `re-pin owed: satellite` lands via ASSET-6
- [x] **BUILD-45** `[release]` [PROCESS][CONTRACTS] — **DONE 2026-07-18 (filed + completed same
      session; owner ask: "check all pins" → both findings as ONE task, one sweep).** The two
      staleness findings from the first post-PROD-26 `repin --check` — both exhaust of the bridge's
      same-day rollout afternoon — discharged in one pass. **(1) catalog re-pinned v1.7→v1.8 at BOTH
      dests** (one multi-dest run; VWB-43's STAMP-only minor — `catalog.golden.json`/`openapi.json`
      verified byte-identical across the tags; the STAMP's `artifacts` went repo-root-relative and the
      repo-root-README false-drift trap was defused). Discharges the bridge's recorded
      `re-pin owed: voice, commons` — the first owed-downstream verdict retired by its consumer. Pin
      set deliberately stays `golden + openapi + STAMP` (matching commons' declared family): the
      owner's `artifacts` now also enumerates `contracts/catalog/README.md`, but the consumer pin
      folders carry their OWN README (basename collision in the flat pin layout) and the owner
      README's version is already pinned via STAMP verbatim + `owner_commit` — recorded as the
      deliberate pins-complete-and-verbatim reading for owner-side doc pointers. **(2) contract-guard
      re-vendored v3→v3.1** (3.1.0 — IMPL-8's ARTIFACTS-PATH rule, repo-root-only `artifacts` entries;
      a no-op on voice's own stamps — none carries an `artifacts` array); `[[tool]]` `pinned_tag`
      bumped; registry/CLAUDE.md/CI version mentions moved v3→v3.1. **Verified:**
      `repin --check --fail-on any` fully green (5 pins + 3 tools); catalog conformance 5 passed;
      commons crossover conformance (`eval/tests/test_contracts_pin.py`) 8 passed; both guards green
      at 1.4.0 / 3.1.0.
      docs: none — pin metadata + enforcement tooling only; no manifest node's content changed
      contracts: catalog pin bumped v1.7→v1.8 (both dests, one run — bridge's `re-pin owed`
      discharged); contract-guard consumed-tool pin bumped v3→v3.1
- [x] **BUILD-46** `[deferred]` [PROCESS][CONTRACTS] — **✓ DONE 2026-07-19 (filed + completed same
      session; owner: "file the scope-guard v7.2 re-vendor + other modified contracts repin task and
      do it").** The second routine staleness sweep — two findings from `repin --check`, one pass.
      **(1) scope_guard.py re-vendored scope-v7.1→v7.2** (commons IMPL-9: rotation-parser fix — the
      DATED pattern demanded the date flush against the heading marks, so ##-style journals parsed as
      zero sections and `--rotate` refused; self-reports 1.4.1). Byte copy from the tag; `[[tool]]`
      `pinned_tag` bumped; version mentions re-stamped (.scope-guard.toml header, ci.yml step name).
      The three CLAUDE.md pinned-block markers deliberately stay at their tags (scope-v5/v4/v7.1) —
      markers record when each BLOCK's text last moved, and the v7.2 STAMP states block text is
      unchanged from v7.1 (sha256s in .scope-guard.toml still match).
      **(2) catalog re-pinned v1.8→v1.9 at BOTH dests in one multi-dest run** (bridge VWB-31). The
      delta is a documentation-string-only refinement of the `/canonical` `device_unreachable` (503)
      semantics — handler-reported reachability failures now surface as 503 alongside the echo
      timeout; `catalog.golden.json` byte-untouched, no schema shapes moved, and voice already maps
      `device_unreachable` → `err_device_unreachable`, so consumption needs no code change. The v1.9
      STAMP's `artifacts` are now repo-root-relative (contract-guard v3.1 ARTIFACTS-PATH world) and
      still enumerate the owner README — the BUILD-45 three-file-set reading stands.
      Verified: `repin --check --fail-on any` fully green (5 pins + 3 tools); catalog conformance 5
      passed; commons crossover conformance 8 passed; scope-guard 1.4.1 green on this ledger.
      docs: none — enforcement tooling + pin metadata; no manifest node's content changed
      contracts: catalog pin bumped v1.8→v1.9 (both dests, one run); scope-guard consumed-tool pin
      bumped v7.1→v7.2
- [x] **DOC-11** `[release]` [DOC] — **DONE 2026-07-12 (filed + completed same day; PROD-17 delegation,
      the HK-6 live stale fixes — all five claims verified at intake).** (a) `build-docker.md` port-6000
      quartet → 8080 (run commands ×2, prose, compose snippet — every Dockerfile serves 8080); (b)
      `websocket-api.md` Python example `ws://localhost:6000` → 8080; (c) `guides/satellite.md` gained
      the pointer sentence to the locveil-satellite provisioning runbook (placed in "Securing the
      connection" — the section that hands off to the controller-side plane); (d) voice-trigger HF link
      VERIFIED live (today's wake-pack re-pin fetched from that exact repo) — no change; (e) QUICKSTART
      profile table mislabel fixed: `embedded-*` are Wirenboard controllers (WB7/WB8), not "ESP32
      satellite controllers". Post-fix sweep: zero `:6000` references remain across the user-facing tree.
      docs: guides/build-docker, guides/websocket-api, guides/satellite, quickstart
- [x] **DOC-12** `[release]` [DOC][PROCESS] — **DONE 2026-07-12 (filed + completed same day; PROD-17
      delegation).** The docs manifest + its guards. `docs/manifest.json` authored: 8 roots (incl.
      `ops/INSTALL.md` and `eval/README.md`), 10 repo-owned surfaces with glob triggers, **60 nodes** —
      every guide/architecture doc, QUICKSTART, README, CONTRIBUTING, INSTALL, the arch/esp32 MOVED
      tombstone (status banner), and all 29 diagram `.dot`+render pairs as one-unit diagram nodes;
      `guides/websocket-api` carries the canonical{invariant,stamp,guard} carve-out
      (`ws-protocol-doc-canonical` / `contracts/ws-protocol/STAMP.json` / the version-triple test).
      `contracts/docs-manifest/` STAMP (`docs-manifest-v1` — version tracks the commons SCHEMA
      generation, never node churn) + pointer README + registry row (INTERNAL), tag created. Coherence
      test `irene/tests/test_docs_manifest.py` (8 checks): commons-schema validation (skips without the
      sibling — CI-hermetic), id/path uniqueness, node paths exist, root-tree bijection (a doc without a
      node fails), diagram pairs complete, covers⊆surfaces, floor classes populated, DONE-ledger verdict
      node-ids resolve. CONTRIBUTING.md gained the contracts-registry, tests-and-eval, and
      documentation-is-part-of-done sections. Manifest schema-valid (strict — no `$comment` allowed).
      docs: contributing
- [x] **DOC-13** [DOC][PROCESS] — **DONE 2026-07-14 (filed + completed same change; commons PROD-23
      delegation — the HK-9 round-1 dependency audit's stale-gate side-find; all claims verified at
      intake).** Stale gate-prose sweep of the active ledger: every "gated on X" line checked against
      X's real status. Four stale, re-anchored: **ARCH-42** + **ARCH-43** "Gated on BUILD-21" (closed
      2026-07-11) → commons **PROD-8**, the actual `core-py` package home; **BUILD-18**'s
      "(gated on BUILD-21)" → commons **PROD-4**, the ops-spec home; **UI-4**'s "do NOT start before
      Gate 2" → DISCHARGED (the Gate-2 remediation core QUAL-27..31 + per-subsystem tasks are all in
      this ledger; the standing conditions — fictional `/workflow/*` endpoints + re-scope-before-pickup
      — kept explicit). Sequencing block's "QUAL-29 remains" corrected (✓ DONE) with a core-complete
      note. One gate verified LIVE and kept as-is: QUAL-82's VWB-33 gate (bridge-side open, PROD-18).
      docs: none — ledger prose only; no manifest node describes individual plan entries.
- [x] **DOC-14** `[release]` [DOC][CONTRACTS] — **DONE 2026-07-18 (filed + completed same session;
      PROD-26 delegation — the sweep's fourth voice task; the ws-protocol model, per the freshly pinned
      contract-triad block).** The utterance-trace JSON format is now a stamped doc-canonical contract.
      Intake reconciliation HELD (board's "shape lives only in the design doc" was slightly narrow: the
      format is SHIPPED — `trace_context.py` emits `trace_version: 1` since ARCH-19, the satellite merged
      shape rides on it since ARCH-38 — and the tracing guide described it narratively, but nothing
      normative and nothing versioned). Landed: **"The trace file format (reference)"** section in
      `docs/guides/tracing.md` (top-level field table + the satellite merged additions
      `controller_trace`/`raw_mic`/`reply_audio` + the compatibility rule: additive keys keep the
      version, readers ignore unknown keys); code constant `TRACE_FORMAT_VERSION = 1` in
      `core/trace_context.py` (the envelope literal promoted); `contracts/trace-format/` STAMP + pointer
      README + registry row + tag **`trace-format-v1`** in the SAME change (no `artifacts`
      byte-enumeration — prose evolves; the normative surface is the tested triple, ws-protocol's
      posture); new CLAUDE.md invariant `trace-format-doc-canonical`; manifest `guides/tracing` node
      gains the canonical{invariant,stamp,guard} carve-out; version-triple test
      `backend/tests/test_trace_format_version.py` (doc line ↔ constant ↔ STAMP + envelope smoke).
      NOTE: a dedicated `trace-format` manifest SURFACE hit the commons schema's 10-surface cap —
      trigger globs deferred to the next docs-manifest schema bump (the canonical carve-out is wired;
      only the glob-trigger mapping waits). **Verified:** the three conformance suites green
      (trace-format 3, docs-manifest, ws-protocol — 15 tests); both guards green.
      docs: guides/tracing (the new reference section IS the artifact)
      contracts: trace-format-v1 CREATED (STAMP + tag + registry row same change); consumers today are
      in-repo (replay tool, satellite merged-trace writer) — no re-pin owed yet; the eval framework's
      trace scorers pin it when they land.
