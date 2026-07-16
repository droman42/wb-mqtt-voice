# Irene — Completed Release Tasks (frozen archive)

Frozen, append-only record of **completed** (`[x]`) release tasks, split out of
[`RELEASE_PLAN.md`](./RELEASE_PLAN.md) to keep the active ledger readable (Invariant #6 still
owns scope+status; this is its done-history). Organized by workstream, IDs preserved so open
tasks and the journal resolve their references here. **Do not re-edit** — closed work only;
rationale/chronology lives in [`RELEASE_JOURNAL.md`](./RELEASE_JOURNAL.md).

---

### Architecture & Refactor (ARCH)
- [x] **ARCH-23** [ESP32] (P-TBD) `[deferred]` — **✓ EXPORT-CLOSED 2026-07-12 (BUILD-22/PROD-15) → `../locveil-satellite`
      FW-1.** The ESP32 firmware rewrite (build the headless voice-satellite firmware to the ARCH-22
      `esp32_satellite.md` contract, replacing the quarantined draft) is now the satellite product repo's work —
      re-filed there as **FW-1** (`HW-GATED`, gated on its DES-3 execution-layer decision; the HK-4 per-device-apps
      amendment noted inline). No voice-side remainder: the design doc moved with it, the `ESP32/` draft tree was
      deleted (2026-07-08 verdict), and the wire protocol the firmware builds against stays here as
      `docs/guides/websocket-api.md` (pinned by the satellite repo).
      docs: none — export-close bookkeeping; the doc moves rode BUILD-22 (retro-verdict, BUILD-35 cutover).
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
### Code Quality & Review (QUAL)
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
- [x] **QUAL-19** [ESP32] (P2, last pre-release) — **DONE 2026-06-09** (interactive review session + upstream study).
      **★ ARCH-22 (2026-06-14):** the **device-side** of the micro stack is now designed in `docs/design/esp32_satellite.md`
      (D-9 ported microWakeWord on ESP-IDF with the TFLite-Micro micro-features frontend + µVAD; D-10 the same `.tflite`
      manifest artifact device+server) — the realization of this review's "one pipeline, device + server" goal.
      Deliverable `docs/review/esp32_wakeword_review.md` — keep/fix/cut per piece {ESP32 firmware, on-device wake+VAD,
      backend microWakeWord, openWakeWord, Porcupine, server VAD, armv7, training refs}. **Key findings:** (1) the
      design's "both server wake providers hallucinated" premise was **wrong** — `openwakeword` works; only
      `microwakeword` is a stub. (2) **Upstream microWakeWord now ships server-side Python libs**
      (`pymicro-wakeword`/`pymicro-vad`/`pymicro-features`, Apache-2.0, maintained) bundling the micro frontend +
      tflite inference + a precompiled tflite C lib → the backend provider is **fixable as a thin wrapper, not a DSP
      hand-port**, and `from_config` loads **custom** `.tflite`+manifest (the per-unit RU plan). (3) microWakeWord +
      microVAD are **one "micro" stack** running identically on the ESP32 (TFLite-Micro) and server-side from the
      **same artifact** — the "one pipeline, device+server" goal is now real. **Decisions:** ESP32 firmware = keep as
      quarantined reference; backend µWW = FIX via pymicro-wakeword; openWakeWord = keep, demote to quick-start;
      Porcupine = CUT; add server-side **microVAD** as a 3rd `VADEngine`; armv7 = no server wake (on-device); training
      refs = cut in-repo. **Config:** uniform wake-word selection stays **per-provider** (consistent with ASR/LLM) via
      a shared `WakeWordSpec={name,model,threshold,language}` sub-schema. **De-tangle (Invariant #6):** QUAL-20 now owns
      the whole wake+microVAD rebuild; **ARCH-10 PR-5 is subsumed by QUAL-20**. Design folded into
      `onnx_inference_layer.md` §11 + `ws_esp32_transport.md`. _Original spec:_ Full review & questioning of the ESP32 +
      wakeword story (firmware functional-vs-aspirational; backend microWakeWord placeholder; openWakeWord vs
      microWakeWord; armv7; docs; TODO11). Intersects ASSET-2.
- [x] **QUAL-20** `[release]` [ESP32] (P-TBD) — **★ ARCH-22 (2026-06-14):** server-side micro stack stays as built; the
      **device-side** µWW/µVAD design + the shared-artifact contract are in `docs/design/esp32_satellite.md` D-9/D-10.
      **DONE 2026-06-09 — wake-word + microVAD rebuild (5 commits
      `bb5382e`·`a980448`·`e00f918`·`be52e0e`·this).** All 8 agreed items landed, each commit green (pyright 0, 9/9
      contracts, config/dep/build gates, 0 net suite regression; config-ui check+build+vitest green). **(1)** backend
      `microwakeword` is now a thin adapter over **`pymicro-wakeword`** (np.random stub + hand-rolled tflite plumbing
      deleted; streams 10 ms chunks; built-in + `from_config` custom models); **(2)** `wake-tflite` extra (drops
      `tflite-runtime`); **(3)** openWakeWord polished (ONNX default, `wake-onnx` extra, per-spec custom model);
      **(4)** uniform **`WakeWordSpec={name,model,threshold,language}`** per-provider (NOT a component-level lift —
      consistent with ASR/LLM; component-level kept as an optional override) + a generic config-ui `ArrayOfObjectsEditor`
      + backend array-items schema extraction (Invariant #4); **(5)** server-side **`microvad`** `VADEngine` over
      **`pymicro-vad`** beside energy/silero; **(6)** Porcupine orphan cut, `embedded-armv7.toml` server-wake disabled
      (on-device), no residual training refs; **(7)** custom models are deployment-supplied (built-ins for dev),
      TODO11 closed; **(8)** real runtime tests (microWakeWord detect/alias/silence, WakeWordSpec parse + schema-items,
      microVAD seam). User docs updated: `voice-trigger.md` (rewrite), `vad.md` (microvad), `howto-new-model.md` (VAD
      seam). **Build-time verify (open):** the `pymicro-*` wheels import + detect on x86 here; confirm
      `libtensorflowlite_c` coverage on aarch64 at the BUILD-3 image stage. WB7 hw re-val stays with ARCH-25. _Original
      spec below._ **Act on QUAL-19 — wake-word + microVAD rebuild (redefined 2026-06-09;
      subsumes ARCH-10 PR-5).** 64-bit-only (armv7 wakes on-device). Per `esp32_wakeword_review.md` "Agreed plan":
      **(1)** backend `microwakeword` = thin wrapper over **`pymicro-wakeword`** (delete the np.random `_extract_features`
      + manual feature-buffer/tflite plumbing/consecutive-detection, `microwakeword.py:237-330`; stream 10 ms/160-sample
      16 kHz chunks); one instance per wake-word entry via `from_config`/explicit ctor; **(2)** `wake-tflite` extra
      (`pymicro-wakeword`, carries its tflite C lib → drop `tflite-runtime`), 64-bit markers; **(3)** openWakeWord
      polish (ONNX default, `wake-onnx` extra, custom `model_path`); **(4)** uniform per-provider **`WakeWordSpec=
      {name,model,threshold,language}`** sub-schema across both providers + config-ui `wake_words` array editor
      (Invariant #4); **(5)** server-side **`microvad`** `VADEngine` over **`pymicro-vad`**, toml-selectable beside
      energy/silero (extends the ARCH-10 PR-4 seam); **(6)** cut Porcupine orphan schema; fix `embedded-armv7.toml`
      (no server wake provider; on-device); cut in-repo training refs + reconcile ESP32 docs; **(7)** assets =
      deployment-supplied custom models (optional `from_builtin` English dev quick-start), close TODO11; **(8)** tests
      (builtin-model detection + `from_config` custom smoke + microVAD seam). **Verify at build:** `libtensorflowlite_c`
      wheel platform coverage (x86_64/aarch64). WB7 hw re-val stays with ARCH-25.
- [x] **QUAL-21** (P1) — **Prod bug (`ComponentConfig` field drift) — RESOLVED BY REMOVAL. DONE 2026-06-03.** The
      `irene-settings` Gradio runner (`settings_runner.py`, 462 LOC) constructed `ComponentConfig(audio_output=…,
      microphone=…, web_api=…)` — fields that no longer exist (mic/web moved to `config.inputs.*` /
      `config.system.web_api_enabled`; `audio_output`→`audio`) → **crash on launch**; same stale kwargs in 4 demo
      examples. **User decision:** the settings runner is obsolete — **removed** rather than fixed (config is now
      edited via config-ui's TOML editor or the file directly). **Deleted** `settings_runner.py` + both pyproject
      registrations (`[project.scripts] irene-settings`, the `irene.runners` `settings` entry-point) +
      `runners/__init__.py` exports; cleaned README, `architecture.md` (usage + the "Settings Режим" diagram subgraph),
      and `tools/migrate_runners.py`. **Retired all 4 stale demos** (`component_demo`, `dependency_demo`, `config_demo`,
      `utilities_demo` — built around the removed optional-components model; user-confirmed) + fixed `examples/__init__.py`.
      **Verified:** `irene.runners`/`irene.examples` import clean; the 3 remaining runner scripts (cli/webapi/vosk) resolve;
      no stale `ComponentConfig` kwargs remain in `irene/` (the residual `audio_output`/`microphone` hits are device-cap
      dict keys, device enumeration, and the intentional v13→v14 migration reader); 0 net suite regressions.
- [x] **QUAL-22** [PEX] (P2) — **DONE 2026-06-03 (removed; resolved within QUAL-11 Stage E).** Chose *remove* over
      *finish*: the stub was dead since inception and real capability/room-aware disambiguation needs registered devices
      (ARCH-6), not a no-op. Deleted `_disambiguate_with_device_context` (caller uses the intent directly) + the 2 xfail
      tests + `test_device_not_found_suggestions`. _Original finding:_ **Stubbed feature found via TEST-2, confirmed by QUAL-10**: context-aware NLU
      enhancement is a no-op. `ContextAwareNLUProcessor._disambiguate_with_device_context` (`nlu_component.py`
      157-187 — the method QUAL-22 first called `_enhance_intent`) computes `enhanced_entities`
      (`output_capabilities`, `context_suggestion`, `preferred_output_device`) but then **returns the original
      intent unchanged** (comment: "for now, return original"); location inference (`location_resolved`) is
      unimplemented. Either finish the enhancement (apply enhanced_entities / wire capability + location context)
      or remove the dead logic. Relates to QUAL-10 [PEX]. xfail tests: `test_client_capability_context`,
      `test_room_context_inference`.
- [x] **QUAL-23** (P1, Gate 0) — **Startup name-resolution assertion.** **DONE 2026-06-01** →
      `irene/core/startup_validation.py` (+ wired in `core/components.py` after coordination; unit tests in
      `irene/tests/test_startup_validation.py`, 4✓). Checks every configured `default_provider`/`fallback_providers`/
      `provider_cascade_order` and every enabled `[<component>.providers.<name>]` resolves to a **registered
      entry-point** (names enumerated, not loaded — optional-dep import failures don't false-positive). Non-fatal by
      default (logs a clear ERROR per unresolved name so a shipped config still boots); `IRENE_STARTUP_STRICT=1`
      raises (CI / TEST-0). Verified on config-master: flags exactly the phantom **`console` LLM** (fallback +
      enabled block — the QUAL-15 bug), zero false positives (TTS/audio `console` are real → pass; NLU cascade
      clean). Folds into ARCH-5 (CI). Note: text-processor **stage-routing** completeness (dead `command_input`
      stage) is provider-name-orthogonal → stays under QUAL-13.
- [x] **QUAL-24** (P2) — **DONE 2026-06-03 (approach refined + user-approved, Invariant #8).** Service-locator → DI in
      8 handlers. **Approach (user chose Option A — domain-owned ports, over the entry's looser "inject components"
      sketch, to truly satisfy Invariant #3):** added domain-owned capability **ports** `irene/intents/ports.py`
      (`LLMPort`/`TTSPort`/`AudioPort`/`ASRPort` + shared `ComponentControlPort` + `ComponentControlRegistryPort`,
      **ABCs** — see hardening below); the 8 handlers now depend only on these domain abstractions and the application
      (`IntentComponent.post_initialize_handler_dependencies`) injects the real components inward. `system` uses the
      already-injected `context_manager`;
      `provider_control` gets the registry port. **Removed** the `from ...core.engine import get_core` service-locator
      from every handler and the **`ignore_imports` escape hatch** from the ARCH-1 contract — ARCH-1 now holds with
      **no hatch** (9/9 contracts kept), proving the transitive `intents→core.engine→{components,inputs,workflows}`
      pull is severed. Opportunistic Invariant #9: removed the `TYPE_CHECKING`/`pydantic` guards in the 6 touched
      handlers that had them. Found a latent bug en route (the old `await component_manager.get_component(...)` awaited a
      **sync** method — the fallback was already broken; injection is what worked). **Invariant #4:** no backend
      contract changed (internal DI only) → config-ui untouched. Verified: suite 85=85 FAILED (0 net regression).
      **Hardening (user-directed, same session):** (1) **ports are ABCs, and the application components now INHERIT
      them** (`LLMComponent(…, LLMPort)`, `TTSComponent(…, TTSPort)`, `AudioComponent(…, AudioPort)`,
      `ASRComponent(…, ASRPort)`, `ComponentManager(ComponentControlRegistryPort)`) — `components→intents.ports` is
      application→domain (inward, legal; 9/9 contracts kept). Nominal inheritance means an unimplemented port method now
      **fails at instantiation** (startup), not as a latent `AttributeError`. (2) That enforcement surfaced **4 methods with
      no implementer** (consumer-defined ports faithfully captured pre-existing **dead handler calls**): implemented them —
      `AudioComponent.pause_audio`/`resume_audio` delegate to the active provider's `pause_playback`/`resume_playback`
      (real); `TTSComponent.stop_synthesis`/`cancel_synthesis` are honest best-effort (TTS providers can't interrupt → graceful
      no-op, no crash). NB: injection also **repaired latent breakage** — only `conversation` was injected before, so the other
      5 capability handlers were getting `None` (compounded by the await-sync bug); they're now wired for the first time (no
      test covers these paths — **filed as TEST-8**). (3) **Removed** the orphaned global-core service-locator
      (`get_core`/`set_core`/`_global_core`) from `engine.py` — zero callers; no test referenced it (the 3 flagged files
      matched on `llm_component`, not `get_core`). All verified: components instantiate (ABC), 9/9 contracts, suite 85=85.
- [x] **QUAL-25** [DFLOW] (P1) — **End-to-end dataflow & context-models review.** **DONE 2026-06-02** →
      `docs/review/dataflow_review.md` (~9 P0, ~20 P1, long P2 tail; 5 parallel tracers → synthesis →
      adversarial-verify on the headline NEW P0s). **Headline NEW finding: a field rename `Intent.text`→`raw_text`
      was never propagated** — `intent.text` is read at 14 unguarded sites across 7 handlers + `Intent(text=…)` at
      `orchestrator.py:217`, so TTS-speak/translation/text-enhance/provider-switch/ASR-audio-provider/contextual
      commands all `AttributeError`, masked by the orchestrator as a generic error (verified vs source). Other NEW
      P0s: `session_id="default"` collapses all sessions (cross-request/room/user leak); `MemoryManager` cleanup loop
      dead (calls non-existent methods); `InputManager._input_queue`/WebSocket `AUDIO_DATA:` input path dead
      (captured mic/web audio dropped — overlaps ARCH-6); required-params never enforced. **CONFIRMS** the FAF P0s
      (timer crash, key-mismatch completion death, `get_or_create_context`) and TXTPROC (TTS gets raw text). Found a
      **4th cross-cutting theme — "data-contract drift"** (model contracts silently disagree across boundaries:
      `Intent.text`/`raw_text`, `WakeWordResult.word`/`wake_word`, action key `action_name`/`domain`, session scope)
      — these are refactor residue the relaxed pyright (Phase-0 §E) was configured not to see. §2 resolves the DOC-8
      request-vs-session question (→ DOC-8 write-up). §4+§6 are the **QUAL-26** agenda. **Spawns:** QUAL-26
      (reconcile) + new P0s for the Gate 2 backlog (numbered in QUAL-26) + DOC-8.
- [x] **QUAL-26** [DFLOW] (P1) — **Review-of-reviews: reconcile inconsistencies, decide intended-vs-actual.**
      **DONE 2026-06-02** → `docs/review/dataflow_reconciliation.md` (live Q&A, 10 issues decided, committed
      per-decision). Consolidated all review docs + the QUAL-25 dataflow findings and decided **intended-vs-today** for
      each. Headline decisions: **Model 2 — split identity from session** (physical-identity store holds `active_actions`
      + devices, long-lived; conversation session holds history, short-lived idle-window); **dedicated zombie-resistant
      action store** (`action_name`-keyed); **`raw_text` = original utterance** (P0-1 fix); **declarative device/room
      via a donation format split** (language-neutral contract + per-language phrasing; `entity_type` + `room_context`
      tri-state); **fail-loud → conversational clarification** (configurable LLM/deterministic); **WebSocket = primary
      ESP32 transport** (reframes ARCH-6). Surfaced a **4th cross-cutting theme: data-contract integrity.** Finalized
      Gate 2 framing (hybrid: principles block + discrete tasks) and emitted **QUAL-27…31** (below). See the doc for
      the full per-issue rationale.
- [x] **QUAL-27** `[release]` [DFLOW] (P0) — **Data-contract fixes (theme ④).** **DONE 2026-06-02.**
      `Intent.text`→`raw_text` at all 14 handler sites + `orchestrator.py:217` (P0-1, the biggest single defect;
      `raw_text` = **original utterance** via a boundary override in `nlu_component.process(..., original_text=)`, NLU
      stops overwriting it — Q1); `WakeWordResult.word` consumer rename (P1-b, 4 sites); **deleted `Intent.session_id`**
      (field + 6 provider/component ctor kwargs + the orchestrator metrics read → `context.session_id` + the redundant
      `_create_fallback_intent` param); enforced the `IntentResult` error contract via `__post_init__`
      (`success=False` ⟹ non-empty `error`, P1-a — one backstop over all ~35 sites). Smoke green throughout
      (5 passed / 1 xfailed). **Scope change (Invariant #8, user-approved):** P1-t (`_create_error_result` signature
      unification) was found to be **6 handlers, not 2**, and is a shared-bases (theme ②) base-vs-handlers split →
      **moved to QUAL-11** (handler-base/typed-accessor consolidation). Refs: `dataflow_reconciliation.md` Q1/Q7.
- [x] **QUAL-28** `[release]` [DFLOW] (P0) — **Context & session refactor (Q2/Q3; foundational). DONE (all 4 stages).** Split
      `UnifiedConversationContext` → a **long-lived physical-identity store** (room/device/client; holds
      `active_actions` + device capabilities; `ClientRegistry` = device source-of-truth) + a **short-lived conversation
      session** (history + `ConversationState`). **Dedicated zombie-resistant action store**, `action_name`-keyed
      (`domain` = router index), 4-layer reaping (completion callback · read-time liveness filter · periodic sweep ·
      TTL+cap). **Session lifecycle:** idle-window (T=10m / voice ~5m, configurable) + sliding history window (N=15,
      wire `max_history_turns`); per-modality boundaries (voice=wake-word burst, WS=connection, REST=conversation-id).
      Forbid the literal `"default"` (P0-6); split `get`/`get_or_create`; **kill `extract_room_from_session`** (P1-o);
      unify eviction on `last_activity`. Delete `MemoryManager` (P0-7). Refs: Q2/Q3/Q4.
      **Staging (2026-06-02):** ① delete `MemoryManager` (**DONE** — module + monitoring wiring) → ② session-id hygiene
      (**DONE** — forbid literal `"default"` in `RequestContext` + re-read the derived id in the 3 `workflow_manager`
      entries; added real `get_or_create_context` fixing the 5 phantom `AttributeError` callers) → ③ new context model +
      action store (+ a **focused action-lifecycle test**, mini-TEST-3, no regression net else) (**DONE** — incl. the
      Stage-3.3 field split: completed-action history moved into the store, survives eviction) → ③b **migrate consumers
      + retire `ContextLayer`** (**DONE** — conversation handler's context assembly rewritten onto direct accessors;
      `ContextLayer` enum + all `resolve_*context`/`resolve_layered_context`/`get_contextual_summary` machinery deleted)
      → ④ history windowing (**DONE** — collapsed the parallel `history`/`conversation_history` lists into the single
      `conversation_history`, written by **one** method `record_turn` at **one** site (the workflow); deleted the legacy
      `history` field + `add_user_turn`/`add_assistant_turn`/`add_to_history`/`_trim_history`/`get_recent_context` and
      the orchestrator's parallel turn-write (P1-q triple-write killed); `max_history_turns` now actually drives the
      window — both `record_turn` and the LLM-restore read it instead of a hardcoded 10 (was the "config-that-lies"
      P2). Also removed 4 dead `ContextManager` turn methods (`add_user_turn`/`add_assistant_turn`/
      `get_conversation_history`/`process_intent_with_context`/`update_context_with_result`).). **Moved ②→③ (Invariant #8):** eviction-unify (needs the
      `last_activity` timestamp-touch audit), the non-creating-`get` split (needs caller migration), and
      `kill extract_room_from_session` (needs room-as-explicit-field) ride the Stage-3 restructure. **Scope correction (Invariant #8):**
      `ContextLayer`/progressive-context is **NOT dead** (Q4 mis-scoped it) — it's live in `conversation.py` (builds the
      LLM context summary). So **migrate-then-retire** in ③b (rewrite the conversation handler's context *assembly* onto
      the new model; its LLM prompt/provider logic stays QUAL-15/16). Deferred to Q9: the now-dead
      `memory_management_enabled` config key + the context `memory_management` block (config-ui coord, Invariant #4).
      **Stage-3 design (decided 2026-06-02 with user):** (a) **action store = a runtime-only (non-persisted) sub-store
      on `ClientRegistry`** keyed by `physical_id` — NOT a field on the persisted registration record (it holds live
      `asyncio` task refs for the reaper and must never serialize / survive a restart). `ClientRegistry` keeps its
      persistent registration table (devices/room) + this new runtime state table. (b) **Single
      `resolve_physical_id(request)` seam** — today returns the session-derived id; **ARCH-6 changes only this one
      function** to return the registered `client_id`/room (so the room/device story is a clean *activation*, not a
      re-refactor). (c) **Decoupled from ARCH-6** (incremental): the store + reaper + eviction-survival land now keyed
      by the best-available stable id; room/device keying upgrades when ARCH-6 populates identity. See the **Q1 timing
      decision** recorded in `RELEASE_JOURNAL.md` + ARCH-6.
- [x] **QUAL-29** [DFLOW] (P1) — **Donation format split (Q6; precedes declarative device-resolution). DONE (backend) —
      config-ui editor rebuild carved to UI-5 (user-approved Invariant #4 deferral 2026-06-03).** Split
      donations into a **language-neutral contract** (method list + invariant `ParameterSpec` core: name/type/required/
      choices/min-max + **`entity_type`** {device/location/room/person/generic} + per-method **`room_context`**
      {required/none/conditional}) + **per-language files** (phrases/lemmas/token/slot patterns + language-specific
      `extraction_patterns`/`aliases`/`default_value`/`description`). Schema `v1.0`→`v1.1`; update the loader
      (`core/donations.py`, `core/intent_asset_loader.py`); shrink `cross_language_validator` to phrasing-completeness.
      Intersects DOC-5b, DOC-7, UI-1/2/3.
      **Decisions (2026-06-02, user):** (1) **Layout** = `assets/donations/<handler>/contract.json` (neutral core) +
      `<handler>/{en,ru}.json` (phrasing only, joined by `method_name#intent_suffix` + param `name`). (2) **Migration
      tie-break:** where en/ru diverge on a neutral field, **Russian wins** (it's the primary language; also fixes the
      latent loader bug where `_merge_language_donations` silently took params/patterns from whichever language iterated
      first). (3) **`default_value` lives in the per-language files** (handles language-specific default text like the
      timer completion message, which already diverges en/ru today; canonical defaults like `unit="minutes"` just
      repeat harmlessly). (4) **SCOPE CHANGE — heuristic deletion MOVED to QUAL-11.** `entity_resolver._is_device_entity`
      /`_is_location_entity` are **live** (`nlu_component.py:38/62` call them every request), and the entity_type-driven
      *replacement* is the Q7b typed accessor (QUAL-11). So QUAL-29 only ADDS the `entity_type`/`room_context`
      declarations (defaulted conservatively: `entity_type="generic"`, `room_context="none"` — humans refine); the
      heuristics stay live until QUAL-11 swaps in the declarative resolver atomically (no broken window). QUAL-29 stays
      **first** — it provides the contract QUAL-11 consumes.
- [x] **QUAL-30** [DFLOW] (P1) — **Clarification UX — Grade 1. DONE 2026-06-03 (deterministic responder; carve-outs
      tracked).** Built the **single fail-loud boundary → explain-and-ask** mechanism: `get_param` now raises a structured
      **`MissingRequiredParameter`** (param_name/description/intent_name); the handler base's `execute_with_donation_
      routing` catches the `ParameterExtractionError` family **before** the generic error and calls a new base
      **`_clarify()`** responder → a single-turn, **localized, speak-able** `IntentResult` (`success=True`,
      `metadata.clarification=True`). Responder is **deterministic + localized** via a new system template set
      `assets/templates/clarification/{ru,en}.yaml` (loaded unconditionally, not per-handler; `get_template` handles the
      language→default fallback so no language is hardcoded). Fixed the fake **`confidence=1.0`** NLU fallback → `0.0`
      (honest no-match; routing keys on `_recognition_provider`, so safe). Tests: `test_clarification.py` (3, green).
      **Carve-outs (not blockers — gated elsewhere):** **LLM phrasing** ("use an LLM if present") deferred to the
      **QUAL-15** LLM foundation (deterministic is the offline guarantee — the must-have; LLM is the review's opt-in
      enhancement); **device/room clarification** → **ARCH-6** (no registered devices yet); **per-handler activation** →
      **QUAL-34** (handlers adopt `get_param` for required params — only timer uses the accessor today, with a caller
      default, so nothing triggers it in production yet); **no-intent** clarification already exists via the conversation
      fallback (now with honest confidence). Grade 2 (multi-turn slot-filling) is **QUAL-31**.
      **Residuals — extend the fail-loud family (slotted, not forgotten):** (a) **`InvalidParameter`** (out-of-range /
      bad-choice, distinct from missing) → **QUAL-34** (per-handler, build the exception + decide clarify-vs-default);
      (b) **`UnresolvedDevice`** raise→clarify when `room_context=required` can't resolve → **ARCH-6** (it owns the
      resolve-or-clarify policy; today resolvers degrade with a `_resolution_failed` marker, don't raise); (c) **targeted
      no-intent clarification** — today no-intent gives a *generic* "didn't understand, try X" (offline) or LLM chat
      (online); the NLU already computes `_fallback_context.likely_domain` ("probably timer") but **nothing uses it** for
      a "did you mean to set a timer?" prompt — **enhancement beyond Grade-1 scope → QUAL-37** (keeps QUAL-30 a clean `[x]`; 7d's "explain-and-ask" is met generically). **System** errors (component down) correctly
      stay graceful errors (not clarifications); their hardcoded English message → QUAL-36. Refs: Q7. _Original spec:_
      At the fail-loud boundary, convert structured failures into explain-and-ask; configurable responder; fix
      `confidence=1.0`.
- [x] **QUAL-31** [DFLOW] (P2, feature) — **Clarification UX — Grade 2 (multi-turn slot-filling). DONE 2026-06-09.**
      A clarifying ask is now a real dialogue turn: the QUAL-30 `_clarify` boundary arms a one-shot
      **`pending_clarification`** on the session (`UnifiedConversationContext.set_pending_clarification` — original
      intent name + asked-for slot + the triggering utterance), and a **pipeline pre-check** at the head of
      `BaseWorkflow._process_pipeline` reads the NEXT turn as the answer: it **prepends the original utterance** and
      re-runs the FULL understanding pipeline (text-processing → NLU → extraction → coercion) on the combined text —
      so *no separate slot-extractor* is needed and CHOICE/range/typed coercion all apply for free. Covers **text
      and voice** (both `process_text_input` and the audio paths converge on `_process_pipeline`). **Design choices
      vs. the original sketch (Invariant #8(d), narrowed):** (1) used a **dedicated `pending_clarification` field**, NOT
      the `ConversationState` enum — its `CLARIFYING` value already carries the unrelated *no-intent fallback* meaning
      (conversation handler) and `CLARIFYING→CLARIFYING` is an invalid transition that would have broken re-asks; the
      field's presence is the trigger, fully decoupled from the existing state machine. (2) **Expiry rides session
      eviction** — pending lives on the per-session context, which `ContextManager` drops after `session_timeout`
      (the Q2 idle window), and it's consumed by exactly the next turn, so no separate timer is needed. (3) **Re-asks
      append** — a resumed turn calls NLU with the combined text as `original_text`, so if the handler clarifies again
      `_clarify` re-arms with it (multi-slot via successive rounds). Tests: `test_qual31_slot_filling.py` (4 — arming,
      one-shot consumption, combined-utterance resume, normal-turn untouched); QUAL-30's 3 still green. No donation/
      config/REST contract touched → config-ui N/A. Verified: pyright 0, 9/9 import contracts, no-TYPE_CHECKING clean,
      suite 83=83 FAILED (0 net regression; +4 new passing). **Known limitation → QUAL-44:** the resume pre-check
      assumes the next turn IS the answer; if the user instead barks a new command it gets combined into a garbled
      utterance (bounded only by one-shot consumption + idle expiry). _Original spec:_ `pending_clarification`
      on the conversation session + `ConversationState = awaiting-clarification` + a pipeline pre-check that fills the
      slot from the next turn and completes the original intent (symmetric to the F&F `contextual` check, but transient).
      Expires with the Q2 idle window. Follow-up to QUAL-30.
- [x] **QUAL-32** `[release]` [QUAL] (P2) — **DONE 2026-06-08** (outcome at end of item). **Purge `TYPE_CHECKING` import guards repo-wide (Invariant #9).** _ARCH-15
      PR-9.2 note: the new I/O modules (`core/interfaces/output.py`, `core/event_bus.py`, `core/observe.py`,
      `outputs/*`) were authored TYPE_CHECKING-free (direct imports, per the PR-3 user directive), so they add **nothing**
      to this purge surface._ ~13 files
      still carry an `if TYPE_CHECKING:` block (`core/metadata.py`, `core/interfaces/webapi.py`, several
      `intents/handlers/*.py`, `utils/audio_helpers.py`, …). For each: if there's no real import cycle, hoist the import
      to module top and de-stringize the annotation; if there **is** a cycle, fix it at the architecture level (break
      the upward edge — move the shared type down / route via a port, per Invariant #3) rather than re-guard. Done when
      `grep -rn TYPE_CHECKING irene/ --include=*.py` returns nothing (outside prose/docstrings) and imports/smoke stay
      green. _Two files already cleared opportunistically (2026-06-02): `intents/handlers/conversation.py` + `timer.py`
      (the QUAL-28 touch surface)._
      **— OUTCOME (2026-06-08):** Reconciliation (Invariant #8) — only **4** real guards remained, not ~13 (prior
      refactors cleared the rest; the `utils/audio_helpers.py` + `intents/context_models.py` hits are *comments*, not
      guards). Purged all 4: `core/interfaces/webapi.py` + `intents/handlers/system_service_handler.py` (empty `pass`
      blocks removed) and `core/metadata.py` + `intents/handlers/random_handler.py` (hoisted `from pydantic import
      BaseModel` — a hard dep, no cycle — and de-stringized the `Type[BaseModel]` annotations). **Added a build-time
      gate** mirroring the hexagon `lint-imports` story: `scripts/check_no_type_checking.py` (AST-based, so it ignores
      comments/strings) + a wrapping test `irene/tests/test_no_type_checking.py` + a hard-failing CI step in
      `config-validation.yml` — CI breaks if a guard reappears (negative-tested). 9/9 import contracts kept; suite 83
      failed = baseline (no net regression).
- [x] **QUAL-33** `[release]` [DFLOW] (P2) — **Handlers ignore declared CHOICE params (surfaced by QUAL-29). DONE.**
      Two handlers DECLARED a CHOICE parameter their code never read — a genuine bug the format split exposed.
      **(a) `datetime.format` — DONE:** all three handlers (`current_time`/`current_date`/`current_datetime`) now branch
      on the canonical `format` (time: 12hour/24hour/verbose · date: short/iso/full=verbose · datetime: iso/unix/
      readable/verbose), rendering via `strftime` with the natural template as the verbose default. **(b) `system.info_
      type` — DONE (user-reduced scope):** `_handle_info_request` branches on `info_type`; the canonical set was
      **reduced to `[system, performance]`** — `configuration`/`logs` REMOVED from the donation entirely (user 2026-06-03:
      "no handlers, no donations" — not declaring options we don't implement is the *fix* for this bug class, not a
      regression). `performance` renders real metrics (`get_metrics_collector().get_performance_summary()` + uptime) via
      a new bilingual `performance` template; `system` keeps the existing info. **Authored bilingual `choice_surfaces`**
      for both (`datetime.format` en+ru; `system.info_type` en+ru), making the values reachable (QUAL-29's matcher
      extracts CHOICE via surfaces). Validator now reports `datetime`/`system` surface-complete. _ru surfaces are a
      proposal pending native-speaker review._ Refs: `qual29_choices_decisions.md` Cases 1–2.
- [x] **QUAL-34** `[release]` [DFLOW] (P2) — **Triage declared-but-unconsumed donation params. DONE 2026-06-03 (per-
      handler triage with user input).** All 19 resolved: **removed 9** (`audio_playback.file_path`;
      `conversation.{topic,query_topic,context_reference}` — query_topic was wrongly `required`, a latent clarification
      bug; `datetime.{location,timezone}`; `greetings.return_time`; `timer.retain`); **removed the whole `train_schedule`
      handler** (bogus external-API handler — code/donation/templates/demo/doc/config/registration); **wired 10 via the
      typed `get_param` accessor + bilingual choice_surfaces** (`voice_synthesis.voice` Bucket-B migration off raw_text;
      `datetime.relative` real date-offset; `greetings.time_of_day` explicit greeting; `text_enhancement.{improvement_type,
      correction_type}` LLM focus directive; `system_service.{component,metric_type,detailed}` + `system.{topic,component}`
      — `detailed` a real verbosity toggle, rest consumed-as-scope where handlers are generic). Fixed wrong-English ru
      surfaces + missing en surfaces on several CHOICE params. New `test_qual34_param_wiring.py` (3) + audit doc marked
      resolved; 0 net suite regressions; donations load 0 warnings. **Original triage detail follows.** The QUAL-33 bug class
      is **not** limited to datetime/system: **19 of ~56 declared
      params across 11 of 14 handlers are never read as `intent.entities[...]`** (7 are CHOICE params). Two buckets:
      **A — genuinely dead** (feature not built; e.g. `greetings.time_of_day`, `text_enhancement.improvement_type`,
      `system_service.metric_type`, `datetime.relative/location/timezone`, `conversation.topic/query_topic/context_
      reference`) → per-param **wire-or-remove** (the QUAL-33 precedent: build the feature, or stop declaring it; for
      CHOICE params kept, author bilingual `choice_surfaces`). **B — bypassed** (feature works but re-parses
      `intent.raw_text` instead of the NLU entity; e.g. `voice_synthesis.voice` → `voice_name`) → **fold into QUAL-11**
      (typed `ParameterSpec` accessor; same as QUAL-25 P1-r/P1-s). Also decide the `language`-as-pseudo-param pattern
      (declared CHOICE in most handlers but satisfied by `context.language`). Done when every declared param is either
      consumed or removed, and the audit re-runs clean. **Per-handler adoption of `IntentHandler.get_param` (QUAL-11
      Stage D) folds in here** — migrating each handler off ad-hoc `intent.entities.get(...)` to the typed accessor IS
      "consume the declared param" (and resolves Bucket B's raw_text bypass at the same site). The timer handler is the
      done reference (Stage D). **Also (extends QUAL-30's fail-loud family):** per handler, decide **invalid-value**
      behavior — build/raise **`InvalidParameter`** (review Q7b: out-of-range / not-in-choices, *distinct* from
      missing-required) → flows through the existing `_clarify` boundary; vs clamp to the declared `default_value`.
      Today `get_param` either clamps-to-default (silent) or raises `MissingRequiredParameter` (mislabeling an invalid
      required value as "missing") — fix the distinction here. Refs: `declared_param_audit.md`, QUAL-11, QUAL-30, QUAL-33, Q6/Q7.
- [x] **QUAL-35** `[release]` [PEX][MQTT] — **DONE 2026-07-06 (Slice 3 closed it — evidence-first, interactive).**
      **Slice 3 record:** authored the tier-2 hard-phrasing fixtures (F90–F98 measurable + F100–F102 relative
      adjustments) and ran the two-leg measurement (baseline vs the QUAL-50 LLM tier). The scoreboard said the wins
      were NOT in a new NLU tier; what got built instead: **(a)** group-noun routing for RAW NLU entities
      (`_group_for_surface` — LLM puts «свет»/«шторы» in `target`, never the CHOICE param; F92/F95),
      **(b)** power-verb → playback play/stop fallback (tape-deck class; F93), **(c)** resolver `scan_utterance`
      (stem-grade catalog spotting when word order defeats the post-verb extraction regex; F94),
      **(d)** donation pattern fixes — mode-worded hvac phrases (the greedy «кондиционер на» routed a setpoint
      sentence to hvac_mode at conf 1.00 where NO fallback tier can ever help; F96) + «звук на» volume_set pattern
      with mute out-specified (threshold coin-flip actuated volume up/down; F97). **Final: tier-1 gate 47/47
      (F94/F96/F97/F98 graduated in); tier-2 `NLU=llm` 5/8 — red = F100–F102 only (→ QUAL-68).** Colloquial lexicon
      («вруби»/«глуши») deliberately NOT added to donations — the LLM tier covers it (already enabled in ALL 6
      deployment configs since QUAL-50/51 — the 'disabled in deployments' note was stale) and the smart-home guide
      now documents the teach-a-word-via-donations recipe instead (user decision). **spaCy T2 leg DROPPED on
      evidence** (zero smart-home patterns exist; `spacy_provider` never consumes `token_patterns` at recognition;
      no fixture uniquely needed it) → revival, if ever, lives in QUAL-53. **Excluded by design** (recorded in the
      fixture-file header): anaphora, multi-command/negation, source→dest, free-text spans. 10 new unit tests;
      suite 1299; pyright 0. _Restructure + historical spine below (kept as the record):_
      landed): what remains runs in THREE SLICES; the historical prose below is the record, the slices are
      the plan.** **Already satisfied elsewhere** (task-start reconciliation): (a) typed `entity_type`
      donations ✓ ARCH-8 PR-4; (b) the Q7b declarative swap ✓ PR-3; (c) D-15 room policy + missing-room
      clarify ✓ PR-3/PR-4; resolver note (1) `options_from` dance ✓ QUAL-65; note (3) input fence lifted ✓;
      the units *requirement* (catalog `unit` + range pre-validation) ✓ PR-4; **"compound numerals need T2"
      is a dead theory** — F05/F06/F07 pass at T1 (the failures were BUG-23/24 pipeline corruption).
      **The slices:**
      • **Slice 1 — transliteration-tolerant matching (note 2) — DONE 2026-07-05.**
        `utils/text_normalizers.latin_to_cyrillic_hint` (cached): Latin words through the in-house TTS
        transcription engine ("YouTube"→«ютуб» exactly), ALL-CAPS acronyms spelled with English letter
        names (TV→«ти ви» — the engine would expand «тэлевижен»); consumed by the handler's
        `_match_option` (options with Latin also match their pronunciation hint) and the scenario label
        scorer, with «э»→«е» folding so transcription variants don't lose points. **Acceptance met:
        F41 + F53 green live, `make device-auto` → 25/27** — the only red left is F40/F42 (QUAL-64,
        user-parked). F41/F42/F53 retiered to 1 (eval-commons `30e174c`); tier 2 now means exactly the
        Slice-3 set. 3 handler tests + hint unit coverage; suite 1269 green.
      • **Slice 2 — capability breadth — SCOPE DECIDED 2026-07-05 (interactive, item-by-item), DOING.**
        **WIRE:** `volume` all four (up/down/set/mute_toggle); `playback` everything (play/stop/next/
        previous/ff/rewind; `play_pause` as the fallback where a device lacks the split actions — the
        `video` device has only the toggle); `cover.set_position` in BOTH address forms (device +
        room-group with `params{pct}`; «наполовину»→50); `climate` on/off via power-verb fallback
        («включи обогрев» fails today — power verbs only see `power` caps); kitchen-hood `fan` (power
        verbs → `set(2)`/`off`; explicit levels; «на полную»→catalog max 4); `tracks` audio/subtitles
        (no eject); `screen` aspect ratios; `menu` nav subset up/down/left/right/ok/back/home (user:
        needed for track dialogs on some devices — exit/menu/settings excluded); `presence` home/away
        («мы дома»/«мы уходим»); `cleaning` start + set_delay(minutes); **`water_supply` alarm on/off
        only** (not heating_control's). **SKIP (recorded exclusions):** `pointer`, `power.toggle`,
        `seasonal_mode` (twice-a-year deliberate act vs ASR misfire), heating_control `alarm`, **all
        four valves — PERMANENT voice fence** (consequence-heavy plumbing, like the power-fan-out
        fence). **CONTRACT-BLOCKED:** HVAC `set_mode`/`set_fan` — bare string params, no triplets/
        options_from (the G5 disease, third instance) → **bridge VWB-24 filed (uncommitted)**; wire
        after the re-pin that types them. Vanes never. Each wired item = donation method + handler
        method + crossover fixtures (PR-4 pattern). Adjudications ride along: `set_position`'s `%`
        settles units-generalization; `room_context` enforcement gets a keep-or-close call.
        **Part A DONE 2026-07-05** (`bedc867`): volume all-four (dB ranges honest via shared range
        pre-validation), playback play/stop/next/previous + seek-CHOICE with `play_pause` fallback,
        `cover.set_position` both forms («наполовину»→50), power-verb fallback → climate.on/off +
        hood fan set(2)/off. Fixtures F60–F67 ALL GREEN live first run — **33/35** (red = F40/F42 =
        QUAL-64 only). 5 handler tests; suite 1274, pyright 0. **Part B DONE 2026-07-05:** tracks audio/subtitles («смени» verbs — «переключи» is
        input_select's in the matcher's scoring, QUAL-64 family), screen aspects (CHOICE + target),
        menu nav CHOICE (7 directions), presence home/away, cleaning start + set_delay, water alarm
        (device narrowed by the alarm+leaks capability PAIR — never an id literal). Fixtures
        F70–F75; live **39/41** — only F40/F42 (QUAL-64) red. **Slice 2 COMPLETE.** Adjudications:
        units-generalization SETTLED (dB volume, % position/brightness, °C setpoint all ride the one
        catalog-range pre-validation path — no further abstraction); `room_context` declarative
        enforcement CLOSED as satisfied-by-implementation.
      • **Slice 2a — HVAC mode/fan (VWB-24 consumed) — DOING 2026-07-05.** The bridge accepted +
        implemented VWB-24 (set_mode/set_fan params typed). Scope: re-pin the contract into
        eval-commons (guards will flag stale fixtures), wire `_handle_hvac_mode` (+fan if triplets
        landed for it) via the CHOICE path against the typed values, fixtures («кондиционер на
        охлаждение»), vanes stay unwired. **DONE 2026-07-05:** re-pinned @ `a17a63b0` (VWB-24 v1.3 —
        full ru/en/de triplets, e.g. cool→«охлаждение»; wire≠canonical now: "COOL"/"cool" — the
        fixture guard learned to validate CANONICAL, which is what Irene sends per §5a);
        `_hvac_choice` matches spoken vs the device's OWN triplets (labels+canonicals through
        `_match_option`), device picked ACTION-aware (only HVACs carry set_mode — heaters must not
        clarify into it); set_fan's param is named `fan`. Fixtures F80/F81 green live — **41/43**,
        red = F40/F42 (QUAL-64) only. Gotcha hardened: a STALE mock bridge squatting on the port
        served an old golden silently (empty mode values) — `device-auto` now clears the port first.
      • **Slice 3 — hard-phrasing tier, evidence-first (absorbs old T2 AND T3).** Author the fixtures for
        the genuinely hard phrasings (multi-param «яркость 30 и температуру 22», role/preposition
        «со спальни на кухню», free-text spans, negation «все кроме торшера», anaphora «сделай его поярче»),
        then measure BOTH existing mechanisms against them: the parked spaCy patterns activated as the
        cascade fallback, and the **QUAL-50 LLM NLU tier enabled in config** (built, donation-grounded,
        DeepSeek-through-LLMPort, abstains offline — currently NOT enabled in any deployment config). Build
        only what the scoreboard says is missing. Sequencing: AFTER the QUAL-64 matcher tune, so the
        fallback tiers are built against a tuned first tier. **The old T3 bullet's "local-LLM / local-only"
        framing is OBSOLETE** (pre-dates QUAL-50/QUAL-14): the universal fallback is the configured LLM
        provider (DeepSeek with an API key), offline = graceful degradation — no separate T3 task exists.
      QUAL-35 CLOSES at Slice 3. _Historical spine below (kept as the record):_
      **★ ARCH-22 (2026-06-14) supplies the multi-room resolution SPEC
      (D-15, `docs/design/esp32_satellite.md`):** no room → primary; a covered room in the utterance → that room; a known
      (catalog) room NOT covered → spoken error "this room is not managed by this device". Needs the bridge catalog
      (ARCH-8) for the global room set + RU-morphology room matching. ARCH-22 already **carries** `primary_room`/
      `covered_rooms` on `ClientRegistration` (D-14); this task implements the resolver that consumes them. _Orig:_
      **Declarative NLU tiers T2 + T3 — MUST-HAVE for smart-home/MQTT
      (gated on ARCH-7/8). Split out of QUAL-11 (2026-06-03, user).** _ARCH-15 PR-9.2 note: the device handlers QUAL-35
      authors **emit a `device_command`-modality result delivered via the OutputManager to the designated bridge
      `OutputPort`** and await its rich `DeliveryResult` (echo/error → spoken confirm; `param_invalid` → clarify) — per
      `mqtt_integration.md` §13 (ARCH-8). No bespoke ActuationPort._ QUAL-11 deliberately shipped the **lightweight (T1)**
      extraction contract — keyword/NER + regex + CHOICE surfaces + lemmas, which is what the `hybrid_keyword_matcher`
      (the hot path) actually runs. T1 covers the easy ~80% of commands but **fails on the complex commands smart-home
      control needs.** This task builds the two heavier tiers when MQTT/smart-home lands:
      • **T2 — spaCy `Matcher`/`EntityRuler` slot-filling** (the currently-**parked** `token_patterns`/`slot_patterns`/
        `extraction_patterns`, authored across all 14 handlers but validated-then-discarded today). Implement in the
        **spaCy provider as the cascade fallback** (lemma/POS-aware recognition + span→`ParameterSpec` slot extraction).
        Wins where T1 provably fails: **compound values** ("таймер на 2 часа 30 минут" → 150 min, not 2), **two
        same-type entities by role/preposition** ("со спальни **на** кухню" → source vs dest), **multiple param=value
        pairs in any order** ("яркость 30 и температуру 22"), **free-text spans into a slot** ("напомни выключить
        плиту"), and **morphology/name-collisions at real-home scale** (`{LEMMA: лампа}` vs `{LEMMA: лампочка}`,
        deterministic vs fuzzy). _Stop the silent validate-then-discard now (QUAL-11 Stage C documents the patterns as
        parked here)._
      • **T3 — dependency-parse / local-LLM NLU** for what T2 **also** can't do (linear Matcher has no scope):
        **negation/exceptions** ("все лампы **кроме** торшера"), **anaphora** ("сделай **его** поярче"), **conditionals**
        ("**если** темно, включи свет"). Ties to the local-LLM-assist lane (QUAL-15) + ARCH-9/10 [INFER]; opt-in,
        local-only.
      **Sequencing:** design with **ARCH-7** (MQTT/output-port + room/device model) and land before/with **ARCH-8**
      (smart-home actuation) — complex device commands are unusable on T1 alone. **OWNS the device-half relocated
      from ARCH-6 (2026-06-03):** ARCH-6 deferred the `entity_type`/`room_context` *consumption* because at its build
      time NO device/room handlers existed (all decls `generic`) — that work lives HERE, where the device handlers do.
      So this task: **(a)** authors the non-generic `entity_type`/`room_context` (device/location/room/person) on the
      smart-home handlers it builds; **(b)** replaces the brittle `_is_device_entity`/`_is_location_entity` name-heuristics
      (`entity_resolver.py`) with declarative `entity_type`-driven resolver selection (the Q7b "typed accessor IS the
      replacement" atomic swap); **(c)** implements the `room_context` resolve-or-clarify policy (with QUAL-30). ARCH-6
      left the seam ready (`resolve_physical_id` returns the registered physical id; `ClientRegistry` populated by the WS
      handshake). Gated by `config-ui-stays-functional` (any donation-schema change → config-ui;
      note the parked T2 pattern fields already exist, so no new schema surface unless extended). Refs:
      `parameter_extraction_review.md` (T2 = the "dead best mechanisms" themes 1+3), QUAL-11 (T1 baseline), Q6/Q7.
      • **★ Units-of-measurement layer (design WITH this task — user, 2026-06-28).** Smart-home commands carry units
        (dimming **%**, climate **°C**, …), the same value+unit shape time already needs. BUG-6 consolidated the **time**
        family into `irene/utils/units.py` (`TIME_UNITS` table + `parse_duration`) and **removed the dead `DURATION`
        param-type stub** (it never had a `coerce()` branch). Do NOT build a general units abstraction speculatively —
        design it HERE, against the real device-unit requirements: generalize `units.py` to a value+unit type with
        **canonical normalization + externalized (donation/catalog) unit surfaces** so timer + dimming + temperature
        share ONE path. The bridge catalog (ARCH-8) declares each device's unit — that's the requirement source.
        **★ Satisfied bridge-side 2026-07-05 (VWB-20 v1.1): 27 action params carry `unit` (°C on `set_setpoint`,
        % on brightness/position) in the typed `CatalogParam`.**
        `QuantityEntityResolver` (`entity_resolver.py`) already holds the non-time nucleus (percent/degrees). _(The ru
        oblique-case numeral gap noted here was resolved separately as BUG-7.)_
      • **★ Resolver-design notes from the contract analysis (2026-07-04/05, chat → recorded here):**
        **(1) CHOICE resolution gains a SECOND surface source** — a `CatalogParam` with `options_from` (e.g.
        `apps.launch app`) enumerates its surfaces at RESOLUTION time via `GET /devices/{id}/options/<kind>`,
        not from the catalog; generalize the ARCH-26 lazy-miss pattern (resolve → miss → re-fetch → retry once)
        plus a short-TTL per-device cache — this round-trip sits inside a voice command's latency budget.
        **(2) Dynamic-set surfaces need transliteration-tolerant matching:** the options endpoint returns
        device-reported proper nouns ("YouTube", "Netflix") while RU ASR yields «ютуб»/«нетфликс» — the
        resolver must match Cyrillic↔Latin phonetically/transliterated, NOT by exact equality (per
        `donation-choice-surfaces-rule` the contract stays canonical; matching is Irene's job).
        **(3) ~~The v1 command set EXCLUDES input switching~~ FENCE LIFTED 2026-07-05 (bridge VWB-19 +
        voice QUAL-65):** `input.set {value}` + `apps.launch {app}` implemented — by_value sets validate
        offline against catalog `values`; parametric/app sets enumerate at resolution time via the
        note-(1) `options_from` dance (now BUILT: `read_options` on the port + 30s TTL cache). Only
        Cyrillic-spoken-Latin matching («ютуб») remains T2 — note (2).
        **(4) The depth doctrine (VWB-23, 2026-07-05):** resolve only as deep as the utterance specifies —
        a named device → device-canonical; a bare capability noun («включи свет», «закрой шторы») → a
        room-group command (`{room, group, action, scope}`); the noun lexicon binds group nouns to catalog
        `CatalogCapability.group` values, NOT to convention; singular → `scope: auto` (the bridge's
        `group_defaults` picks the device), «весь»/plural → `scope: all`.
        **(5) No power-group fan-out promises** in donations — the bridge allow-lists fan-out to
        `light`+`cover` only and 409s the rest by design («выключи все розетки» must not work).
        **(6) Same-room capability ambiguity: v1 CLARIFIES** (user decision 2026-07-05; TEST-18 fixtures
        F20/F21 are the spec) — don't build priority config into the v1 resolver; priority rules are
        **QUAL-63** (later release).
- [x] **QUAL-36** `[release]` [DFLOW][I18N] (P1) — **Single language source-of-truth; purge hardcoded language codes
      (theme ④; user observation 2026-06-03). DONE 2026-06-03.** **Consolidation decision (user, mid-task):** found FOUR
      competing declarations (`CoreConfig.language="en-US"` locale-form, `nlu.default_language`/`supported_languages`,
      `nlu_analysis.languages.*`, `IntentAssetLoader`'s own); user chose **promote to top-level `CoreConfig.default_language`
      + `supported_languages` (2-letter)** as the one canonical source — read at the composition root, injected inward.
      **Delivered:** (1) canonical top-level config fields; removed the `nlu.*` duplicates; deprecated the `en-US` field;
      config-master.toml updated. (2) `ContextManager` injected `default_language`+`supported_languages` (mirrors
      `max_history_turns`); `engine.py` wires them; seed fixed. (3) NLU detection reads canonical + clamps; `_analyze_text_
      language` returns `None` (no signal) → caller applies default; providers receive canonical via config injection. (4)
      invariant established. (5) **deleted all 67 `or "ru"` fallbacks** → bare `context.language`; ripped out the timer/audio/
      voice-synthesis `_get_language` re-detection heuristics; **fixed the `hybrid_keyword_matcher` `'en'`-vs-`'ru'` divergence
      bug**; made handler `language="ru"` default params required (T4). (6) language-switch validation (`system.py`) now reads
      the new **`context.supported_languages`** (seeded from canonical) — no baked `["ru","en"]`. (7) **localized the LLM
      context-injection labels** → `assets/localization/conversation/{ru,en}.yaml` (`_context_label`, by user language).
      **Verified:** new `test_language_source_of_truth.py` (6) proves en-primary + arbitrary-language seeding/clamp/labels/
      no-stomp; suite at baseline parity (0 regressions). **Carve-out → QUAL-38:** processing-language defaults (number-spelling
      utils / silero TTS / ASR / text-processor) + inline bilingual handler messages (`== 'ru'` branches) are a distinct
      concern, filed separately. Refs: `RELEASE_JOURNAL.md` 2026-06-03, QUAL-16.
- [x] **QUAL-37** `[deferred]` [DFLOW] (P2) — **Targeted no-intent clarification (enhancement; split from QUAL-30).
      DONE 2026-06-03.** The online (LLM) path already consumed `_fallback_context.likely_domain` (via
      `_build_fallback_context_prompt`, QUAL-16); the gap was the **offline** path. **Delivered:** `_handle_fallback_
      without_llm` now reads `likely_domain` and, when it matches a known domain, emits a **deterministic, localized,
      offline** targeted clarification ("Возможно, вы хотели поставить таймер?" / "Did you want to set a timer?") via a
      new `fallback_targeted` template + a `fallback_domain_labels` map (domain→friendly action phrase) in
      `assets/localization/conversation/{ru,en}.yaml`; falls through to the generic responder when there's no guess /
      unknown domain. Metadata now carries `targeted`/`likely_domain`. **Verified:** new `test_no_intent_clarification.py`
      (5) covers targeted ru/en, generic fall-through, unknown-domain fall-through, determinism + offline; 0 net suite
      regressions. **Ledger fix:** removed a corrupted duplicate QUAL-37 header that had orphaned QUAL-36's old body
      (collateral from the QUAL-36 done-edit). Refs: QUAL-30, QUAL-16, Q7.
- [x] **QUAL-38** `[deferred]` [DFLOW][I18N] (P2) — **Processing-language threading + inline-bilingual purge (carved from
      QUAL-36). DONE 2026-06-03.** **Key correction:** the processing language is the **audio-MODEL/deployment** language
      (which number-spelling/transcription rules to apply), NOT the session language — spelling numbers in the session
      language but synthesizing with a different-language voice would mismatch. So the fix is **config/model-derive**, not
      request-threading (which would introduce that bug; the QUAL-13 "request-scoped" comment was the gap). **(a) delivered:**
      `convert_numbers_to_words` made language-required (caller threads `request.language`); `PrepareNormalizer` gets a config
      `language` (was falling back to inline `"ru"`); `unified.py` threads the per-normalizer deployment language to both
      number normalizers; `silero_v3|v4` derive `self.language` from model config (default model is `*_ru.pt` → `"ru"`);
      `asr_component` transcribe endpoint resolves to `self.default_language` not a literal. (Library `utils/text_processing.py`
      defaults + the Pydantic request-schema `"ru"` defaults left as documented API/library defaults.) **(b) delivered:**
      externalized the genuine inline RU/EN strings — **voice_synthesis (6)** → `voice_synthesis_handler` templates,
      **system (3)** → `system_handler` templates, **provider_control (5)** → NEW `provider_control_handler` templates + a
      `_get_template` method; unified **random_handler (3)** error templates (added `{error}` to the ru side, dropped the
      `== 'ru'` branch). **Kept (legitimate, per done-criteria):** `system_service_handler` Russian pluralization grammar
      (strings already templated), and Russian command-keyword *parsing*. **Verified:** templates load + resolve ru/en; 0 net
      suite regressions. Done: processing language derives from model/config; handler user-facing strings externalized.
- [x] **QUAL-39** [API] (P2) — **DONE 2026-06-04 (Option 2, user-approved).** Audited the **19** routes lacking a
      `response_model` (104/123 already typed). **Key finding (the reason this task existed):** the **donations contract
      pair** `GET/PUT /donations/{handler}/contract` — UI-5's primary target — were the only **UI-5-consumed** untyped
      endpoints; reconciliation showed config-ui's other status/config/NLU reads already hit typed endpoints
      (`/intents/status`, `/configuration/config/status`, …), **not** the untyped system ones. **Done:** typed the contract
      pair's **envelopes** — `DonationContractResponse` / `DonationContractUpdateResponse` (`api/schemas.py`) — and `/health`
      (`HealthResponse`). **Contract/phrasing BODY stays `Dict[str, Any]` passthrough on purpose:** both have a **canonical
      JSON Schema** (`assets/donation_contract_v1.1.json` + `assets/donation_language_v1.1.json`, both
      `additionalProperties: true`); a strict Pydantic body would **drift from the schema AND drop fields on the editor's
      GET→PUT round-trip**. **Symmetry analysis (the donation_language question):** the language/phrasing side already does
      exactly this — `LanguageDonationContentResponse` with `donation_data: Dict[str, Any]` passthrough — so typing the
      contract envelope brings it to **parity** with the phrasing endpoints; the strong **body types** for config-ui are
      generated from the two JSON Schemas, the **envelopes** from OpenAPI (see UI-5). **Classified (b) legitimately
      dynamic / non-JSON — documented, not typed:** `/dashboard/html`, `/`, `/asyncapi`(+`.yaml`) (HTML/YAML),
      `/prometheus` (text exposition), `/asyncapi.json` + `/debug/asyncapi` (generated spec/debug docs), `/components`
      (conditional keys). **Deferred general hygiene (non-UI-5, type later if wanted):** asr `/providers`/`/reset`/
      `/transcribe`, monitoring `/contextual-commands`(+`/performance`), nlu_analysis `/capabilities`/`/statistics`,
      `/system/status` (config-ui doesn't consume it — Overview uses `/intents/status`). Verified: models accept the real
      GET/PUT shapes incl. passthrough extras, suite 85=85 (0 net regression). (Found 2026-06-04.)
- [x] **QUAL-40** `[release]` (P2) — **DONE 2026-06-07.** Generated-TOML section headers no longer dropped. **Was:**
      `ConfigManager._generate_provider_sections` / `_generate_normalizer_sections` (`config/manager.py`) built a
      per-iteration `section = "[base_path.<name>]"` header but **never appended it to `sections`**; the closing
      `"\n".join([section] + sections)` kept only the **last** header (and mis-placed it at the very top), so every
      provider/normalizer header except the last was dropped → the generated TOML collapsed all entries' keys under one
      section. **Fix:** `sections.append(...)` the header at the start of each iteration and join plainly (dropped the
      `[section] +` prepend + the dead `section = ""` init). **Verified round-trip:** new
      `test_config_section_generation.py` (3) asserts every header survives and the output re-parses via `tomllib` back to
      the original `{provider/normalizer: {...}}` nesting (the round-trip assertion fails on the old code — keys would
      collapse under the single surviving header). Backend-only (generated-TOML *content* fix; no contract/shape change),
      so config-ui's TOML-editor surface just receives correct TOML — no config-ui code change. Gates: pyright 0,
      import-contracts 9/9, dep-validator 55/55, check_scope clean, suite 84=baseline (+3).
- [x] **QUAL-41** `[release]` (P2) — **DONE 2026-06-07.** `IntentAssetLoader` validator output now matches
      `api.schemas.ValidationError`. **Was:** `validate_template_data` / `validate_prompt_data` /
      `validate_localization_data` (`core/intent_asset_loader.py`) emitted error/warning dicts keyed `{field, message,
      severity}`, but `api.schemas.ValidationError` requires `{type, message}` (+ optional `path`/`line`), so
      `ValidationError(**err)` in `intent_component.py`'s template/prompt/localization editing endpoints raised a pydantic
      error (missing required `type`) → **HTTP 500 whenever those endpoints hit a real validation error**. **Fix (chose
      "align validator output to schema" over a boundary mapper):** rewrote all three validators (incl.
      `_validate_domain_specific_localization`) to emit canonical `{type, message, path}` — the **same shape the sibling
      `validate_phrasing_data`/`validate_contract_data` already produce** (`field`→`path`; `severity` dropped, already
      encoded by the errors-vs-warnings list; `type` carries a category: `structure`/`missing_field`/`value`/`validation`).
      No consumer read `field`/`severity` (all 9 endpoint sites only `ValidationError(**err)`). **Invariant #4:** config-ui's
      template/prompt editors already read `.message` (via `any` casts: TemplatesPage/PromptsPage) → render correctly now;
      `npm run check` + `build` stay clean (no config-ui change needed). **Regression test:** `test_asset_validation_schema.py`
      (3) constructs the schema models from each validator's failing-input output — the exact path that used to 500. Gates:
      pyright 0, import-contracts 9/9, dep-validator 55/55, check_scope clean, suite 84=baseline (+3). **Also fixed
      (user-directed, same change):** `DonationsPage.tsx:859` read `err.msg` on the **phrasing** validation response while
      `validate_phrasing_data` emits `message` (canonical) — a pre-existing latent display bug on the UI-5/QUAL-29 surface
      (the adjacent warnings map already read `.message`); `err.msg`→`err.message`, config-ui check + build green.
- [x] **QUAL-42** `[release]` [DVALIDATE] (P1) — **Donation contract↔code validator + LLM translation services.
      DONE 2026-06-06 (user-directed: "do this validator right away").** Closed the real gap the donation-validation
      investigation found: nothing reconciled a **contract** against the **handler code** it drives (only contract→method
      existence; never params, never reverse coverage). **Delivered (backend):**
      **(1)** `core/contract_validator.py` — `ContractWiringValidator` introspects each handler class + AST-scans the
      module for parameter reads (`get_param`/`get_typed_param`/`intent.entities`). **Severity split (deliberate, to
      avoid false-positive boot failures):** an **unwired contract method (no callable on the class) is FATAL** — raises
      `DonationDiscoveryError`; **soft warnings** = a declared parameter never read (legitimately context-sourced, e.g.
      `language`), or a `_handle_*` method no contract declares (reverse coverage). A `strict_parameters` flag promotes
      param warnings to fatal (ratchet). **(2) Startup integration** — `IntentAssetLoader.load_all_assets` runs the
      validator over all loaded donations, **fail-fast on unwired methods**, and caches the report. Verified: the 14
      shipped handlers validate **0 fatal / 13 useful warnings** (boot stays green). **(3) Endpoints (intent_component,
      via injected `LLMPort`):** `GET /donations/validation` (the startup wiring report → UI); `POST
      /donations/{h}/validate-translation` (**LLM** meaning/consistency QA — deepseek default, else any supported
      provider with a key; **no LLM → `llm_available:false` + "validate manually" message**); `POST /donations/{h}/translate`
      (**LLM** translation *service*, content-aware replacement for the dead phrase-count `suggest-translations`; same
      graceful no-LLM path). **(4)** 8 schemas in `api/schemas.py`; design doc `donation_editor_ux.md` §9 updated for the
      UI. **Tests:** `test_contract_validator.py` (7, incl. an all-real-handlers 0-fatal guard). Gates: pyright 0,
      import-contracts 9/9, dep-validator 55/55, suite 84=baseline (+7 passing). _Decision logged:_ LLM translation
      validation is **on-demand (endpoint), not per-boot** — avoids per-startup token cost/fragility; structural wiring
      validation is the always-on startup part. Refs: `parameter_extraction_review.md`, donation-validation investigation.
- [x] **QUAL-43** [DVALIDATE] (P2) — **DONE 2026-06-06.** Removed the donation v1.0 dead validation code and
      **repointed the build analyzer at the v1.1 schemas** (user-directed mid-task). **Removed:** the dead v1.0
      schema-validation chain in `IntentAssetLoader` (`load_donation_on_demand` / `_load_and_validate_donation` /
      `_validate_json_schema` / `validate_donation_data` — 0 callers; the *v1.1* `_validate_donation_schema` stays);
      `irene/tools/intent_validator.py` + its `irene-intent-validate` script + `assets/v1.0.json`; the orphaned
      `CrossLanguageValidator.sync_parameters_across_languages` (+ its dead confidence/lang-detect helpers and the
      `TranslationSuggestions` dataclass); the rule-based `suggest_translations` method + the
      `POST /donations/{h}/suggest-translations` endpoint; the dead schemas `SyncParameters{Request,Response}`,
      `SuggestTranslations{Request,Response}`, `TranslationSuggestionsSchema`, `MissingPhraseInfo`. **Build analyzer
      rewritten:** `_validate_intent_json_files` now validates each enabled handler's `assets/donations/<h>/contract.json`
      (against `donation_contract_v1.1.json`) + its `<lang>.json` phrasing (against `donation_language_v1.1.json`) via
      `jsonschema` — the old path pointed at the non-existent v1.0 monolithic `<h>.json`, so it would have emitted false
      "file not found" build errors. Verified the real handlers validate clean + a missing contract is flagged.
      **Regenerated** the committed `openapi.json` (109→108 paths; suggest-translations gone) + the frontend types.
      Gates: pyright 0, import-contracts 9/9, dep-validator 55/55, backend suite 84=baseline, `cd config-ui && npm run
      check && npm run build` pass. _Original scope:_
      **Remove donation v1.0 dead validation code (split from UI-5 scope decision, 2026-06-06).**
      The v1.1 split (QUAL-29) + the new wiring validator (QUAL-42) left v1.0-era validation as dead weight: **(1)**
      `IntentAssetLoader._validate_json_schema()` validating against `assets/v1.0.json` (reachable only via the legacy
      `_load_and_validate_donation` / unused `validate_donation_data` paths); **(2)** `irene/tools/intent_validator.py`
      (standalone CLI validating v1.0.json, not wired into the loader/API); **(3)** `assets/v1.0.json` itself; **(4)** the
      orphaned `CrossLanguageValidator.sync_parameters_across_languages()` no-op + its now-unused
      `POST /donations/{h}/sync-parameters`-era plumbing; **(5)** the rule-based `suggest_translations()` + its
      `POST /donations/{h}/suggest-translations` endpoint, **once UI-5 stops calling it** (superseded by QUAL-42's LLM
      `translate`). **Sequencing:** do AFTER UI-5 lands (so removing the suggest-translations endpoint doesn't break the
      old UI mid-flight). Verify no remaining importers; gates: pyright 0, import-contracts 9/9, dep-validator 55/55,
      suite ≤baseline. Found during the donation-validation investigation + UI-5 scoping.
- [x] **QUAL-44** `[release]` — **DONE 2026-07-05** _(un-deferred same day, user — the TEST-18 device suite
      made the defect reproducible: an armed clarification consumed the next same-room command as its
      answer, poisoning F51–F53 in cascade)_. **Implemented exactly as scoped:** the resume pre-check
      (`voice_assistant.py`) now runs NLU on the BARE new utterance first; a confident (≥ the NLU
      component's threshold), non-fallback recognition is a fresh command — the pending clarification is
      dropped (logged) and the utterance processes clean; anything else (bare fragment / low-confidence /
      fallback) combines as before. Trade-off settled per the entry's own lean: one extra NLU pass on
      clarifying turns only; abandonment is silent (no spoken acknowledgment — the fresh command's own
      reply is the acknowledgment). Regression tests: new-command abandons, low-confidence still combines,
      bare-answer path stays green (the fakes became text-aware — an everything-recognizes-at-0.9 fake
      would have defeated the arbitration silently). Live proof: F52 flipped green; F42 stopped producing
      combine-garbage. [DFLOW] (P2, enhancement; split from QUAL-31) — _Orig:_ **Answer-vs-new-command arbitration on a
      clarifying turn.** QUAL-31's resume pre-check (`workflows/voice_assistant.py` `_process_pipeline`, the
      `take_pending_clarification` branch) **unconditionally** treats the turn that follows a clarification as the answer:
      it prepends the original utterance and re-runs NLU on the combined text. That is the intended flow ("answer with
      just the missing value"), but if the user instead **abandons the clarification and barks a new command** ("какая
      погода?" after being asked a timer duration), the combine yields a garbled utterance ("поставь таймер какая
      погода?") that can misroute or no-op. Today this is bounded only by one-shot consumption (the bad turn clears the
      marker) + idle-window expiry — acceptable for the P2 feature, but not robust. **Scope:** add deterministic
      arbitration before combining — e.g. run NLU on the **bare answer first**; if it independently recognizes as a
      **confident, non-fallback** intent (a real, different command), drop the pending clarification and process the
      answer **fresh**; otherwise (bare fragment / low-confidence / fallback) treat it as the slot answer and combine as
      today. **Trade-off to settle:** an extra NLU pass on clarifying turns only (cheap, rare) vs. a lighter
      confidence/phrase heuristic; also decide whether a brand-new command should *cancel* the pending intent silently or
      acknowledge the abandonment. Pairs with QUAL-31 (this is its known limitation) and the F&F `contextual` resolution
      (same "is this turn about the prior context or a fresh request?" question). Done when a new-command answer routes
      to the new command (not the garbled combine) with a regression test, and the legitimate slot-answer path stays
      green. Refs: QUAL-31, QUAL-30, Q7.
- [x] **QUAL-45** [WS][ESP32] (P2) `[deferred]` — **DONE (design) 2026-06-14 — SUBSUMED BY ARCH-22.** The ESP32
      audio-streaming protocol (end-of-utterance + on-device VAD/wake contract) is now fully specified in
      **`docs/design/esp32_satellite.md`** — wire protocol §4 (`{"type":"end"}` device hint + server-authoritative ASR
      endpointing, D-5/D-6), the on-device microWakeWord+microVAD contract (D-9/D-10), and the single-mic/no-server-VAD
      split (D-11). The *firmware* implementation of the end-of-utterance signaling rides the **tracked firmware rewrite**
      (esp32_satellite.md §14), not this task. _Original below._ **ESP32 audio-streaming protocol: end-of-utterance signal
      + on-device VAD/wake contract.** Filed from the ARCH-18 endpoint reconciliation (2026-06-10). The **server already** consumes a
      `{"type":"end"}` control frame on `/ws/audio` to bound an utterance (one session = one utterance = one ASR;
      `webapi_router.py:824-835`) and ARCH-18 makes that path skip server VAD+wake (they run on-device). **Device-side TODO
      (ESP32 review):** define + implement the firmware's end-of-utterance signaling (emit `{"type":"end"}` at on-device
      VAD silence; **default = end of WS session** if a firmware doesn't send it), plus the on-device VAD/wake contract the
      server now assumes. Doc: `docs/review/esp32_wakeword_review.md` + `docs/design/ws_esp32_transport.md`.
- [x] **QUAL-46** [IO] (P2) `[deferred]` — **DONE 2026-06-15.** Generalize the vosk runner into a config-driven
      **voice runner** (follows ARCH-15's "runners-as-presets — config, not code"). The old `VoskRunner` was a full
      end-to-end mic pipeline (mic → VAD → [wake] → ASR → NLU → intent → TTS) but **artificially gated to vosk** by
      two checks — an `import vosk` dependency probe and a validation rule forcing `asr.default_provider == "vosk"` —
      while the actual processing path was already provider-agnostic (delegates to the ASR component). **Removed both
      gates:** the runner now requires only `sounddevice` (its real dep — mic capture) and validates *any* configured
      + enabled ASR provider (vosk/whisper/sherpa_onnx/google_cloud); ASR-provider deps are the component system's
      concern (`irene-dependency-validate`). **Renamed** `vosk_runner.py`→`voice_runner.py`, `VoskRunner`→`VoiceRunner`,
      `run_vosk`→`run_voice`, entry points `irene-vosk`→`irene-voice` + the `irene.runners` discovery entry + the
      `runners/__init__` exports (clean rename, no alias — pre-release). **Fixed the latent VAD inconsistency:** the mic
      pipeline structurally requires VAD (the workflow raises if it's off) yet the runner forced asr/audio/nlu/etc but
      not vad — now it forces `vad.enabled=True` too, so a VAD-off config fails clearly in the runner, not deep in
      workflow init. (`voice_trigger` stays config-driven — the runner auto-skips the wake word when it's absent.)
      Docs: new "Voice (microphone)" section in `QUICKSTART.md` (config-driven ASR, both invocation forms, `--trace`).
      New `test_voice_runner.py` (8 tests: provider-agnostic validation + the force-rules incl. VAD). 9/9 import
      contracts; runner/vad suites net-zero (4 pre-existing TEST-2 failures). Invariant #4 N/A (no config schema/endpoint
      change — purely a runner gate + rename). _Note: the v13-era `tools/migrate_runners.py` still maps the old name as
      a v13→v14 migration target; left untouched (obsolete, like `config_migrator` — flagged separately → QUAL-47)._
- [x] **QUAL-47** [WS] (P2) `[deferred]` — **DONE 2026-06-15.** Retire the obsolete one-time migration tools (the
      QUAL-46 follow-up). On v15.0.0, both target long-past versions and neither is imported by runtime code:
      **`irene/tools/config_migrator.py`** (v13→v14 config migration; entry point `irene-config-migrate`) and
      **`tools/migrate_runners.py`** (legacy `runva_*.py`→v13 runners — already broken by the QUAL-46 rename, since it
      referenced `vosk_runner`/`VoskRunner`/`run_vosk`). Deleted both + removed the `irene-config-migrate`
      `[project.scripts]` entry. No tests/code referenced them (only two `docs/archive/*` historical mentions, left as
      record). Package re-syncs clean; 9/9 import contracts. **Sweep extended 2026-06-15** — retired two more
      standalone (un-imported, non-entry-point) migrators verified spent/obsolete: **`tools/migrate_to_universal_plugins.py`**
      (old plugin→provider config migration; only refs were two `docs/archive/*` guides) and
      **`scripts/migrate_donations_v11.py`** (QUAL-29 donation v1.0→v1.1 — **QUAL-29 is `[x]` and the assets are already
      v1.1**: 13 `contract.json` + per-lang files, so the one-time migration is applied/spent). Surfaced a related
      finding kept OUT of scope → **QUAL-48**: `irene/config/migration.py` is *live* v13→v14 runtime auto-migration.
      **Also retired 2026-06-15** the dead one-off VAD debug script **`tools/test_vad_sibilant_fix.py`** (already broken —
      it imported `UniversalAudioProcessor`, renamed to `VoiceSegmenter` in ARCH-18, so it `ImportError`ed; not an entry
      point, not imported) + its orphaned companion **`configs/vad-sibilant-fix.toml`** (referenced only by that script).
      The sibilant fix itself is long shipped (`docs/archive/VAD_SIBILANT_FIX.md`, left as record).
- [x] **QUAL-48** [DFLOW] (P2) `[deferred]` — **DONE 2026-06-15 (decision: remove).** Removed the v13→v14 runtime
      config-migration path — the last v13/v14 relic after QUAL-47 retired the standalone migrators. `irene/config/migration.py`
      (637 lines: `V13ToV14Migrator`/`migrate_config`/`ConfigurationCompatibilityChecker`/`create_migration_backup`) was
      wired into `config/manager.py:_dict_to_config`, guarded by `requires_migration(data)` so it only fired for a
      **v13-format** config — which never occurs on v15.0.0. Deleted the module; dropped the import + the guard block in
      `manager.py` (the normal env-resolve → `model_validate` path is unchanged); removed the import + 5 `__all__` entries
      from `config/__init__.py`. A v13 config now fails plainly at pydantic validation instead of silently morphing —
      correct for v15 (v13 is unsupported). No test depended on auto-migration (verified net-zero vs baseline); all shipped
      configs (config-master/minimal/api-only) load clean; re-exports intact; 9/9 import contracts. Invariant #4 N/A.
- [x] **QUAL-49** [INFER] (P2) `[deferred]` — **DONE 2026-06-15.** Silero TTS model-id routing fix (surfaced from the
      ARCH-24 asset-routing analysis; relates to **ARCH-24 T5** — done early). `silero_v3`/`silero_v4` were the **only**
      providers that bypassed the AssetManager model-id router: they placed the model at `<dir>/<config:model_file>` with a
      **shared default** (`v3_ru.pt`/`v4_ru.pt`), so two v3 languages — v3_ru/en/de/es all share the `silero/` dir — that
      both left `model_file` at the default resolved to the **same file** (latent collision), inconsistent with the
      sherpa/whisper/vosk `get_model_path(provider, model_id)` convention. **Fix:** route the path via
      `get_model_path("silero_v{3,4}", model_id)` (→ `silero/<id>.pt` / `silero_v4/<id>.pt`, distinct per model_id); derive
      `model_url` from the selected model_id's descriptor (legacy torch.hub-fallback safety); route the download through the
      real provider name (`download_model("silero_v4", model_id)`, not the non-existent `"silero"` fallback that silently
      failed into the legacy path + a copy hack). Explicit `model_file` still honored as an override (back-compat). New
      `test_silero_routing.py` (4 tests incl. the anti-collision property). **Invariant #4 N/A** (TTS provider config is
      free-form `Dict[str,Any]`, `models.py:191` — not schema/config-ui-typed). Gates: suite 935 green, pyright 0, contracts 9/9.
- [x] **QUAL-50** [NLU][LLM] (P2) — **LLM NLU classifier as a cascade fallback provider** (decided 2026-06-15 in the
      ARCH-24 T4 armv7 config session). New `LLMNLUProvider(NLUProvider)`: when the deterministic providers (keyword +
      spaCy-on-64-bit) don't recognize an utterance, ask the **LLM to classify** it into a known intent **and extract its
      parameters** (intent taxonomy sourced from the donation/bridge catalog) — recovering fuzzy *commands* the keyword
      matcher misses. Slots into `provider_cascade_order` **after** keyword/spaCy (last NLU resort, before the
      `conversation.general` fallback). **Deliberately revises the QUAL-15/16 "NLU is LLM-free" stance — but only as a
      last-resort fallback**: the deterministic path stays primary and offline still works (keyword → conversation
      templates). Needs `[llm]` enabled with a provider (cloud = HTTP, so armv7-viable, but adds online dependency + latency
      for fuzzy commands). Full provider integration (the PR2 lesson): `LLMNLUProviderSchema` registered +
      `[nlu.providers.llm]` config-master block + `get_supported_architectures()`. **Gates the ARCH-24 T4 armv7 config**
      (which wants keyword→llm NLU — providers-before-configs). When low-confidence/missing-param: hand to the conversation
      handler's CLARIFYING multi-turn (already in place — `conversation.py` `ConversationState.CLARIFYING` + QUAL-37
      targeted clarification; verify it elicits a **missing required parameter**, not just domain-level specificity).
      **Design (confirmed 2026-06-15; corrected 2026-06-16):** the provider returns a **plain `Intent`**
      {name, entities, confidence, raw_text} via `recognize_with_parameters` — **identical to keyword/spaCy, no special
      output** (the earlier "rich structured JSON object" plan was wrong; see QUAL-52 below). It does what every NLU provider
      does: **classify** (LLM picks one intent name from the donation taxonomy, or abstain → `None`) + **extract params**
      (`extract_parameters`), then returns the Intent. **Catalog grounding is NOT the LLM's job** — the shared
      `ContextualEntityResolver` (run by `ContextAwareNLUProcessor` downstream, for *every* provider) canonicalizes entities
      against the live catalog/context. So the LLM emits **raw entity spans** ("kitchen", "lamp"), not canonical IDs — the
      shared resolver grounds them. The classification call is a **plain text** `chat_completion` (no
      `LLMPort.generate_structured`, no structured-output capability). **Confidence is DERIVED, written to the standard
      `Intent.confidence`:** (i) intent ∈ donation set [hard gate], (ii) fraction of **required params that resolve** against
      catalog/context [the real signal], (iii) an **evidence span** the LLM must quote [anti-hallucination]; LLM
      self-report/logprobs are a weak prior only. **Commands** accept only if intent-valid + evidence + ALL required params
      resolved (missing → CLARIFYING; unresolvable / no-evidence → abstain); **queries** accept on intent-valid + evidence.
      **DEPENDS ON QUAL-52** (the reworked, budget-aware LLM component — *not* its structured output, which was reverted).
      **Built 2026-06-16:** `irene/providers/nlu/llm.py` `LLMNLUProvider` — `_initialize_from_donations` builds the
      taxonomy + `parameter_specs` from the same donations; `recognize_with_parameters` makes one deterministic
      `LLMPort.generate_response` call, parses locally, and returns a plain `Intent` or `None`. Abstains on
      no-LLM / offline / unparseable / intent∉donations / evidence-not-in-text; else confidence = `0.7 + 0.25 × required-coverage`
      (a missing required param still clears the threshold → the handler's QUAL-30 `_clarify` asks — verified at
      `handlers/base.py:285,302`). Injection mirrors the conversation handler: `set_llm_component(LLMPort)`, soft-injected by
      `NLUComponent.post_initialize_coordination` via `core.component_manager.get_component('llm')` (no hard dep → no-LLM
      builds still start). `LLMNLUProviderSchema` registered + `[nlu.providers.llm]` (enabled=false, opt-in) + pyproject
      entry-point; default cascade unchanged. Arch = all (cloud HTTP is armv7-safe). Tests `test_llm_nlu.py` (13). Gates:
      suite 995 green, pyright 0, contracts 9/9 (provider→`intents.ports` is ARCH-4-legal), config-ui type-checks (Inv #4).
      **Unblocks ARCH-24 T4** (armv7 config can now use `keyword→llm`). Prompt wording is a first cut → **QUAL-51**.
- [x] **QUAL-51** [NLU][LLM] (P2) — **Prompt-tightening session for QUAL-50** (DONE 2026-06-16; interactive scope agreed
      with the user). Tightened the inline classifier system prompt: conservative "abstain when unsure" framing, an explicit
      JSON output contract + anti-hallucination (verbatim evidence), and the taxonomy + few-shot **filtered to the utterance
      language** (by script). Few-shot = hand-written **abstain** exemplars per language (the key last-resort lesson) +
      **auto-sourced positives** from each intent's donation `examples`. Kept the prompt **inline** (per the user's call) —
      it's *dynamically assembled* from donations (taxonomy + examples), so it isn't a static authored asset like the
      `assets/prompts/*` task prompts; `docs/guides/prompting.md` updated to document this one generated exception (Inv #10).
      Decisions: instructions **English-only** (LLMs follow them cross-lingually; taxonomy/utterance carry the language),
      classifier keys off the **input** language (`context.language`), not the system default. Tuned the
      `missing_parameter` clarification template (en+ru) — warmer, invites the answer. **Validation:** new live harness
      `scripts/eval_llm_nlu.py` + bilingual fixture `scripts/eval_llm_nlu_cases.yaml` (24 cases, real 54-intent taxonomy,
      DeepSeek via `.env`) — **24/24** after two fixture corrections (clear/fuzzy/missing-param/abstain/ambiguous all clean).
      Offline prompt-logic tests in `test_llm_nlu.py` (now 18). Gates: suite green, pyright 0, contracts 9/9. The
      keyword-matcher-feedback half is **not** automatable here → split out as **QUAL-53**.
- [x] **QUAL-52** [LLM] (P2) — **LLM component rework: real token budgets + budget-aware prompting** (surfaced 2026-06-15;
      **prerequisite for QUAL-50**; DONE 2026-06-16). Today's LLM handling used arbitrary/meaningless config knobs and was
      **token-budget-blind**. Reworked `llm_component` + providers (deepseek/openai/anthropic) + the LLM config schema:
      **(1) PR1 ✓** real **per-model token budgets** (`llm_capabilities` registry: context window + max output from actual
      model capabilities, dropping the arbitrary 150). **(2) PR2 ✓** **budget-aware prompting** — `estimate_tokens`
      (utf-8 bytes/4, dependency-free), `fit_messages` trims oldest/keeps system+final to fit the input budget;
      `context_window` exposed in config. **(3) PR3 ✗ REVERTED (2026-06-16):** first-class structured/JSON output
      (`generate_structured` + `response_format`) was built on a **wrong premise** — that the QUAL-50 NLU classifier returns
      a bespoke structured object. It does not: an NLU provider returns a **plain `Intent`**, param extraction is the
      provider's `extract_parameters` step, and catalog grounding is the **shared** `ContextualEntityResolver` downstream. So
      the classifier needs only a plain text call — no generic JSON-dict capability on the component (commit `beb08e3`).
      **(4) PR4 ✓** **dropped the unneeded fine-tuning** — `temperature` removed from schemas/config/providers (+ dead
      `top_p`/`frequency_penalty`/`presence_penalty`); providers now use a fixed deterministic `0.0`. **Invariant #4:**
      config-ui has no typed temperature field (free-form params dict) → nothing to sync, openapi unchanged. (QUAL-15/16
      console-LLM fallback / `fallback_providers` — left as-is; not in scope here.)
- [x] **QUAL-54** [APICONTRACT] (P2) `[release]` — **DONE 2026-06-27.** Targeted fix of the live-bug subset from
      `docs/review/api_result_contract_review.md` (F2 WS half + F5): the `/ws/audio` response now surfaces intent under
      `intent_name` (remapped from the orchestrator's `original_intent`, keeping the raw metadata) at both send sites
      (`webapi_router.py` streaming + batch), and the two `workflow_manager.py` pipeline-event emitters (`:482`,`:637`)
      now read `original_intent` instead of the never-populated `intent_name` (the field was always `None` in prod).
      Root masking cause fixed too: `test_pipeline_events.py`'s fake returned `metadata={"intent_name":…}` (wrong key) —
      now mirrors the real `original_intent` contract, so it's a faithful regression test. Unblocks the `eval/` WS
      intent case (provider reads `metadata.intent_name`). Gates: full suite 1066 passed / 9 skipped, pyright 0,
      import-linter 9/9. `config-ui-stays-functional` N/A (additive WS metadata + internal logging; config-ui doesn't
      consume `/ws/audio`). Full 5-way unification → QUAL-55.
- [x] **QUAL-55** [APICONTRACT] (P2) `[release]` — **DONE 2026-07-04. One canonical `IntentResult → API`
      serializer across the five execution surfaces** (retires F1/F3/F4 + the rest of F2,
      `docs/review/api_result_contract_review.md`). New `irene/api/serializers.py` →
      `serialize_intent_result(result, extra_metadata=None)`: canonical keys `text` (F1 — `/execute/*` renamed
      from `response`), `success`/`error`, `confidence` top-level (F4), `intent_name` lifted from the
      orchestrator's `original_intent` (F2), `timestamp`, raw `metadata` with endpoint extras merged IN, never
      replacing (F3). All five surfaces route through it: REST `/execute/command|audio` (`CommandResponse`
      reshaped: `text`/`confidence`/`intent_name` fields; the invented "executed successfully" fallback prose
      dropped — fail-loud ①), `/trace/command|audio` `final_result`, both WS `/ws/audio` response frames
      (supersedes QUAL-54's metadata-injection). Co-changes: **config-ui** `openapi.json` re-dumped +
      `openapi.gen.ts` regenerated, `npm run check` + `build` green (no runtime component consumed the old
      field); **eval-commons** `ws_audio_provider` reads top-level `intent_name` with metadata fallback (spans
      SUT versions). WS test fakes replaced with the real `IntentResult` (a wrong-shaped fake is how F5 hid a
      live None — same lesson). Tests: `test_api_result_serializer.py` (7); smoke e2e asserts the canonical
      keys against a live server. Suite 1180 green; 10 import contracts kept.
- [x] **QUAL-56** [QUAL][REVIEW][ARCH] (P3) `[deferred]` — **DONE 2026-07-02.** F&F design critiqued through the
      durable-execution lens + (user-requested) comparative analysis of `wb-mqtt-bridge` device-state persistence.
      Deliverable: `docs/review/faf_durable_execution_review.md`. Verdict: **zero on every durability axis by
      explicit design** — in-memory store ("NEVER persisted"), restart = silent total loss (a 24h timer vanishes;
      "list timers" denies it existed), no scheduler durability (`AsyncTimerManager` = dead capability), no
      idempotency (+ live-record overwrite on name collision), delivery at-most-once with 5 silent-drop points
      (failure notifications suppressed by default), retry machinery dead config, no recovery, aggregate-only
      amnesiac observability. Bridge comparison: right persistence shape to borrow (generic key→JSON SQLite behind a
      port, chokepoint dirty-write, ephemeral filter, reconcile-by-diff restore, shutdown-artifact protection) + two
      cautionary failure modes (persist-without-restore rot; stale `active_scenario` resurrecting on restart — filed
      to the bridge as **VWB-18**, uncommitted). User scope statements recorded: future handlers will require
      durability → platform substrate; "a fix + rules for new handlers would be required". Follow-ups filed:
      **ARCH-27** (substrate design + handler rules), **BUG-19** (store/status correctness), **QUAL-61** (dead
      capability removal, gated on ARCH-27's keep-or-cut).
- [x] **QUAL-57** [QUAL][REVIEW][ARCH] (P2) `[release]` — **DONE 2026-07-02.** **General architecture review +
      memory-overconsumption analysis** (user-requested). Deliverable: `docs/review/arch_memory_review_2026-07-02.md`.
      Method: 3 parallel deep-reads (architecture map / multi-turn memory audit / F&F QUAL-8 re-verification +
      `create_task` census); the 3 headline memory findings spot-verified directly. **Verdicts:** architecture =
      top-quartile for its class (enforced hexagonal layering — zero live violations, entry-point provider model,
      donation-driven NLU cascade, true streaming-ASR seam) but not SOTA at the interaction layer (no barge-in,
      whole-utterance TTS, no per-client concurrency isolation, weak session continuity — A1–A4 recorded for user
      decision, not filed). **F&F path now clean:** all 10 QUAL-8 findings resolved by the QUAL-28 store redesign
      (re-verified). **Live memory risk moved to the request path:** metrics session leak growing on every REST
      call/WS connection (→ BUG-16), uncapped `/ws/audio` batch PCM accumulator ≈115 MB/h per bad client (→ BUG-17),
      untrimmed LLM conversation store with dead `max_context_length` config (→ BUG-18); small-item sweep → QUAL-58;
      capability drift + dead code → QUAL-59. A5 (no action durability) confirms QUAL-56's premise — that task stands.
- [x] **QUAL-58** [MEM][QUAL] (P3) `[deferred]` — **DONE 2026-07-02.** Memory-hygiene sweep (QUAL-57 M4–M8), all five
      items: **(M4)** `AudioTranscoder._resampling_cache` now bounded by BYTES too — 4 MB total budget + 1 MB
      per-entry bypass (full TTS replies / long utterances are never cached; they were the tens-of-MB retention),
      FIFO eviction on either bound, `cache_bytes` in stats; **(M5)** `ClientRegistry.prune_stale_history(3600s)` —
      per-identity completed-action history keys (`_recent_actions`/`_failed_actions`/`_action_error_count`) are
      dropped once their newest entry is an hour stale (keysets grew monotonically with session-derived ids);
      **(M6)** the ContextManager cleanup loop (every `cleanup_interval`) now drives `reap_dead_actions()` (the
      advertised layer-3 sweep finally has a runtime caller — docstring corrected) + the M5 prune;
      `cleanup_expired_clients` deliberately stays manual — nothing refreshes `last_seen` on a live WS connection,
      so auto-expiry would unregister a live-but-quiet satellite (documented in its docstring); **(M7)**
      `NotificationService` queue bounded (maxsize 1000, `put_nowait` + drop-with-warning on overflow — never blocks
      the F&F completion path) and `send_notification` lazily starts the processing loop, killing the consumer-less
      getter-minted-instance path; the six provider `warm_up` preloads hold their task refs
      (`self._warmup_task` — were GC-cancellable mid-model-load); **(M8)** trace dir rotated to the newest
      `MAX_TRACE_FILES = 500` on every save (each file embeds full base64 audio; constant not config — same
      safety-net reasoning as BUG-17). Regression: `test_memory_hygiene.py` (7 tests across M4/M5/M7/M8);
      cache-stats shape test extended. Full suite 1139 passed / 7 skipped; pyright clean on all 11 touched files.
      Evidence: `docs/review/arch_memory_review_2026-07-02.md` §M4–M8.
- [x] **QUAL-59** [API][QUAL] (P3) `[deferred]` — **DONE 2026-07-02.** Capability drift + dead code (QUAL-57 A6/A7);
      user directive: dead code **removed**, not repaired. **(A6)** `/system/capabilities` now derives
      `nlu/voice_trigger/text_processing` provider lists from the loaded components' `providers` dicts and
      `workflows` from `workflow_manager.workflows` (the hardcoded lists advertised the long-gone
      `continuous_listening` workflow and missed the `llm` NLU provider); regression
      `test_capabilities_endpoint.py`. **(A7) deleted outright:** the domain-keyed dead Phase-3.5 action-management
      interface in `handlers/base.py` (`cancel_action`, `get_active_actions`, `get_action_status`,
      `list_all_actions`, `cancel_all_actions`, `inspect_action`, `get_action_management_capabilities` — would
      mis-cancel/double-record if ever wired; −300 LOC) plus the handler-side action-debugger wiring
      (`set_action_debugger`, attr, import; monitoring keeps its own debugger endpoints); the two `/intents/actions/*`
      REST stubs ("Full implementation requires session context") + their 3 orphaned schema classes; the zero-caller
      ContextManager introspection machinery (`get_context_for_intent_processing`, `get_recent_intent_patterns`,
      `get_dominant_domain`, `get_session_statistics`, `cleanup_session` — which also bypassed the BUG-16 metrics
      seam — `get_active_session_count`); the 2 tests that only exercised deleted methods. **Fixed (live code):**
      cwd-dependent paths in `nlu_component` now package-relative (handler dir from `handlers_pkg.__file__`, assets
      root from module parents). Stale `metrics.py` key comment was already fixed in BUG-16. **Contract artifacts
      regenerated** (endpoints removed → `scripts/dump_openapi.py` + config-ui `npm run gen:api-types`; apiClient
      never used the stubs). Gates: 1138 passed / 7 skipped; pyright clean on all 7 touched files; import-linter
      9/9 kept; config-ui `check` + `build` pass. Evidence: `docs/review/arch_memory_review_2026-07-02.md` §A6/A7.
- [x] **QUAL-61** [QUAL][FAF] (P3) `[deferred]` — **DONE 2026-07-02.** Dead-capability removal, all three cuts per
      ARCH-27 D-7 (user preference: dead code removed). **(1)** Retry machinery: `_execute_with_retry` +
      `_is_transient_failure` deleted (−98 LOC), `max_retries`/`retry_delay` launch params removed from both F&F
      launch methods, retry metadata keys dropped from the action record; **(2)** `AsyncTimerManager`: `core/timers.py`
      deleted + all wiring (engine ctor/attr/start/stop, composition root, `core/__init__` export, the
      `service_mapping['timer_manager']` entry) — the durable store + reconciler IS the scheduler (ARCH-28);
      **(3)** dead inspection path: `inspect_active_action` + `InspectionLevel`/`ActionInspectionResult`/
      `TestActionConfig` + vestigial history/test-action state removed from `debug_tools.py` (67 lines remain:
      `get_debugging_status` for the live `/debug` endpoint), `monitoring_component.get_action_debugger()` accessor
      removed; `NotificationMessage.retry_count`/`max_retries` fields removed (written, never read). Gates: 1156
      passed / 7 skipped; pyright clean (8 files); lint-imports 10/10.
- [x] **QUAL-62** [ARCH][QUAL] (P2) `[release]` — **DONE 2026-07-02 (filed + completed same day, user-requested
      ARCH-28 follow-up).** The new `DurableActionStorePort` seam is now reflected in the hexagon gate: 10th
      import-linter contract **"Durable-action store is reached only through its seam (ARCH-28)"** — no
      application/delivery/adapter layer (`components/workflows/providers/web_api/runners/inputs/outputs`) may
      import `irene.core.durable_actions`; the three sanctioned gateways (`intents.handlers.base` choke point,
      `core.engine` reconciler, `core.notifications` redelivery) are `ignore_imports` edges so chains THROUGH the
      seam pass while new direct imports fail. The contract proved itself during introduction: it flagged the
      transitive `webapi_router → notifications → durable_actions` chain until the gateway edges were sanctioned.
      Design doc D-2 annotated. Gates: lint-imports 10/10 kept; `test_import_contracts.py` green.
- [x] **QUAL-64** `[deferred]` [NLU] (P2) — **DONE 2026-07-05 (interactive). Keyword-matcher scoring tune** (filed from the first TEST-18
      device-suite run, 2026-07-05 — the matcher was NEVER tuned; user decision: leave the affected fixtures
      red and tune deliberately). **Evidence:** short verb phrases beat longer specific ones — «включи кино с
      видеокассеты» → `smart_home.power_on` 0.70 (should be `scenario_start`, phrase «включи кино»); «выключи
      кино» → `power_off` 0.72 despite `scenario_stop` carrying that EXACT phrase with boost 1.3 (boost does
      not overcome the short-phrase preference); both then dip under the 0.7 confidence threshold in the live
      cascade → `conversation.general`/LLM. **Scope:** phrase-length/specificity weighting + boost semantics in
      `hybrid_keyword_matcher` scoring; acceptance = TEST-18 fixtures F40/F42 green (`make device-auto`) with
      NO regression across the other handlers' routing (the suite + the WS suite are the safety net).
      Pairs with QUAL-53 (trace-driven improvement process — this is its first concrete, pre-collected case).
      **RESOLUTION (user chose specificity+boost):** the disease was a TIE, not weighting — every
      pattern hit in a method tier scored an identical constant, the stable sort broke ties by
      donation LOAD ORDER («выключи кино»: bare «выключи» beat the exact «выключи кино» by loading
      first), and the donation `boost` was never consulted in the pattern stage. New score:
      `pattern_conf × method_boost × (1+0.1×(tokens−1), cap 1.3) × donation_boost`; `intent_boosts`
      stored at load. F70's phrase workaround retired (fixture restored to «переключи субтитры» as a
      permanent regression). 15-case routing test over the full 14-donation set. **Acceptance
      exceeded: `make device-auto` 43/43 (100%)**; suite 1329, pyright 0. Bonus fence: the
      device-auto pkill needed the `[e]` bracket trick (it was killing its own recipe shell).
- [x] **QUAL-65** [PEX][MQTT] (P2) `[release]` — **DONE 2026-07-05 (filed + completed same day; user-requested
      intake: bridge VWB-19 landed input/app canonical routing — consume it before QUAL-35).**
      **Input switching + app launch by voice**, against the re-pinned contract @ bridge `3bed556` /
      catalog `dbfd2855` (`canonical_first.md` §11: `set` is the reserved canonical action for select-form
      capabilities). **eval-commons (`cc1cba9`):** re-pin (ru-labels guard refined — `labels: null` legal on
      by_value technical identifiers, non-null still requires ru); fixtures re-authored + **F50–F53**
      (by_value input / parametric input / app launch / «ютуб» transliteration-t2); the input-switching
      exclusion lifted; mock bridge serves `GET /devices/{id}/options/{kind}` (by_value → catalog keys,
      parametric → deterministic stand-ins). **Voice:** `read_options(device_id, kind)` joined
      `DeviceCatalogPort` — the QUAL-35 resolver-note-(1) `options_from` dance PULLED FORWARD
      (`CatalogService` 30s-TTL cache; `BridgeClient.get_device_options` fail-soft; composition-wired);
      handler `_handle_input_select` + `_handle_app_launch` share one option matcher built on the
      resolver's OWN normalization (`_norm`/`_stem_match` — one surface-matching truth); miss → clarify
      naming what IS available; donation methods + templates ru/en. 10 new tests (suite 1262, pyright 0,
      11 contracts; eval-commons 40). **Live: F50 green end-to-end** (by_value, zero round-trips); suite
      20/27 — F51–F53 red are NOT routing: the run exposed **QUAL-44 session-bleed** (an armed
      clarification consumes the next same-room case as its answer; matcher probe routes all three
      correctly at 0.75–0.79) → QUAL-44 un-deferred (user) + `make device` runs `-j 1` (shared per-room
      sessions make parallel cases inherent cross-talk). Guide updated (inputs/apps section + limits).
- [x] **QUAL-66** [QUAL][DONATION] (P3) `[release]` — **DONE 2026-07-05 (filed + completed same day,
      user-requested after asking what the "Contract wiring" warnings were).** **Contract-wiring
      warnings swept 21 → 0**, turning the loader's validator from ambient noise into a meaningful
      tripwire. Three families: **(1)** dead `language` globals removed from 9 donations (handlers read
      `context.language` since QUAL-36; the param was never consumed) + `conversation.session_id`
      (lives on the context per QUAL-27) — NOT touched: `system`/`speech_recognition`, whose `language`
      param is the TARGET language for switching, genuinely read (the validator's silence there proved
      the point; an over-eager first sweep removed them and the warning list itself caught the error);
      **(2)** `voice_synthesis_handler`'s declared-but-unread `provider` param removed (the handler
      parses it from raw text); **(3)** two internal helpers renamed off the `_handle_` prefix
      (`_do_language_switch`, `_fallback_without_llm`) — the prefix promises a donation entry, these
      are dispatched internally. Two tests updated (one had RELIED on the drift existing as its live
      example — now exercises the check with declare-nothing). Suite 1289 green; device suite 43/43.
- [x] **QUAL-67** [QUAL][CI][DONATION] (P3) `[release]` — **DONE 2026-07-05 (filed + completed same
      day, user-requested — the payoff of QUAL-66's zero baseline).** **Donation validation is now a
      build + CI gate:** new `irene-donation-validate` (`irene/tools/donation_validator_cli.py`) runs
      the exact runtime validation (schema strict + `validate_contracts`) over EVERY donation
      directory under `assets/donations/` (module-aware discovery — handler modules are inconsistent
      about the `_handler` suffix) with **warnings-as-errors**: a declared-but-unread param or an
      undeclared `_handle_*` method now FAILS the build instead of scrolling past in a boot log.
      Wired into `ci.yml` backend-health beside the config/dependency/build-analyzer gates (gates
      every image publish = the build gate). Verified both ways: green on the clean tree
      (14 handlers, 86 methods, 0/0), red on an injected canary param. Suite 1289 green.
- [x] **QUAL-69** `[release]` [MQTT] — **DONE 2026-07-06 (filed + completed same day). Consume the bridge's
      open-questions catalog patch: wardrobe_spots ru alias «свет» (catalog `a17a63b0` → `acc1e18b`,
      bridge commit `aa031d2`).** Inward re-pin of all three artifacts (catalog + STAMP + openapi — the
      openapi also picked up the committed canonicalAction/Capability/Param schema rename we hadn't synced);
      PIN.json stamped. Voice-side analysis: NO code change — the depth doctrine is ordering-protected (the
      group-noun check precedes device resolution on every path, incl. the Slice-3 `_group_for_surface` and
      `scan_utterance` legs), so a device carrying the group noun as an ALIAS cannot demote «свет» to
      device-form. **New fixture F17** («включи свет в гардеробе» → room-group wardrobe/light/auto) pins
      that interaction; guard 8/8, device tier-1 gate **48/48**.
- [x] **QUAL-70** `[release]` [UX][CLI] — **DONE 2026-07-06 (filed + completed same day, user request).
      Clean REPL: interactive runners log to file + trace only.** Two console-noise sources silenced for
      the CLI: (1) the root console handler — `_setup_logging` now keys `enable_console` off
      `supports_interactive` (CLI off, WebAPI/voice unchanged); `--debug` deliberately brings console
      logs back; (2) the embedded background uvicorn — `_serve_in_background` builds it with
      `log_config=None` + `access_log=False`, so its loggers propagate to the root handlers (file)
      instead of scribbling over the prompt; the FOREGROUND webapi server is untouched (docker logs
      depend on it). Verified live: `irene-cli -c configs/config-example.toml` shows banners + replies
      only; `logs/irene.log` carries the full log; `--debug` restores 500+ console lines. Suite 1300,
      pyright 0.
- [x] **QUAL-71** `[release]` [I18N] — **DONE 2026-07-06 (filed + completed same day). Hardcoded Russian
      reply strings swept out of handlers → templates.** Seven literals found (5 in conversation.py — incl.
      the «справочный режим недоступен» the user hit — plus datetime + greetings error fallbacks); all now
      resolve through the template system (ru + en authored; new `assets/templates/datetime_handler/`).
      Error-path nuance: a template call inside an `except` must never mask the ORIGINAL failure — new
      `_template_or(name, lang, fallback)` base helper: localized when assets are healthy, last-resort
      literal when the template system itself is broken (a unit test caught exactly this).
- [x] **QUAL-72** `[release]` [PROCESS] — **DONE 2026-07-06 (filed + completed same day; user caught the
      drift). `check_scope.py` now flags STRANDED completions** — a `- [x] **ID**` task entry still in the
      ACTIVE plan is a `single-task-ledger` violation (completion must MOVE the entry to the done-archive in
      the same change), and the gate silently accepted it: three same-day completions (BUILD-12, ARCH-33,
      REL-3) were flipped in place instead of moved, and every gate run since passed. Entries moved; the
      guard now fails on the class (canary-verified both directions). The gate that exists to catch drift
      must catch the maintainer's own drift first.
- [x] **QUAL-73** `[release]` [PROCESS] — **DONE 2026-07-06 (filed + completed same day; user caught it,
      second guard-hardening of the evening). Tasks filed into WRONG workstream sections** — BUILD-13 landed
      under ARCH (filed in-place at ARCH-35's completion) and BUG-29 at the tail of QUAL in the done file
      (the insert-before-next-header pattern drops entries into the PRECEDING section). Both moved.
      `check_scope.py` now fails on any ID-prefix / enclosing-section mismatch in EITHER ledger file
      (canary-verified), and CLAUDE.md's `single-task-ledger` states the section rule explicitly. Same
      lesson as QUAL-72: conventions the maintainer can violate under tempo must be machine-checked.
- [x] **QUAL-74** `[release]` [PROCESS] — **DONE 2026-07-06 (filed + completed same day; the user's THIRD
      ledger-discipline catch of the evening). Sections now sort ascending by ID, gate-enforced.** The
      done-archive had grown in completion order (56 ordering violations, most historical) and the day's
      in-place filings added more in the active file. Convention SET (user): entries ascend by ID within
      each workstream section, both files; a completion is INSERTED at its sorted position, not appended.
      Both files mechanically resorted (205 entries, zero loss — asserted), `check_scope.py` fails on
      out-of-order IDs (canary-verified), CLAUDE.md `single-task-ledger` states it. Completes the evening's
      guard triad with QUAL-72 (stranded [x]) + QUAL-73 (misfiled sections).
- [x] **QUAL-75** `[release]` [MQTT] — **DONE 2026-07-06 (filed + completed same day). Consume the bridge's
      contract v1.4 (VWB-28): re-pin @ `fc8eb31`** — openapi gains `POST /reports` + `GET /reports/evidence`
      with the **`EvidenceEnvelope`** schema (the B-11 read seam our ARCH-34 amendment asked for, delivered
      same-day); catalog golden byte-unchanged (`acc1e18b`) so all 48 device fixtures stand untouched;
      eval-commons guard 8/8. **ARCH-34's dependency gate is now LIFTED** — the endpoint exists and its
      envelope is pinned; ARCH-34 stays `[deferred]` by the v1.1 scope decision, but activation is now
      pure voice-side work (bounded call + `bridge/` bundle subtree + envelope-pin expectation).
- [x] **QUAL-76** `[release]` [MQTT] — **DONE 2026-07-07 (filed + completed same day). Consume the bridge's
      rack-verified catalog: re-pin @ `8159b4b0` (bridge `40f0452`)** — auralic gains a `previous` action,
      zappiti power becomes a **toggle** (was on/off); openapi unchanged, contract stays v1.4. Zero crossover
      fixtures bind the changed devices, so only the fixtures doc's `catalog_version` stamp moved. **Bonus
      catch:** QUAL-75's PIN.json had recorded the bridge repo HEAD in `bridge_commit` instead of mirroring
      `STAMP.bridge_commit` (the generator's commit), leaving eval-commons' `test_pin_matches_stamp` guard
      red unnoticed — convention restored, eval-commons suite 40/40 (eval-commons `14ac383`).
- [x] **QUAL-77** `[release]` [MQTT] — **DONE 2026-07-08 (filed + completed same day). Consume the bridge's
      DRV-5/SCN-11 desync-repair contract surface: openapi re-pin @ bridge `c32068e`** — `CanonicalActionResponse`
      gains `skipped_reason` (idempotence-skip marker: nothing transmitted, belief may be wrong), `force` becomes
      a reserved param bypassing idempotence guards, and two scenario endpoints land (`reconcile_preview` /
      `force_reconcile`). Pure additions (+317 lines); catalog + STAMP byte-unchanged so `PIN.bridge_commit`
      stays per the guard convention; eval-commons 40/40 (`7cfd5a7`). Voice-side adoption analyzed with the user
      (bridge maintainer's handoff note) and filed as **ARCH-39** (device-level 2-turn force-confirm) +
      **ARCH-40** (scenario force-reconcile via voice), both `[deferred]` post-release design tasks.

- [x] **QUAL-78** [OPS] `[deferred]` — **DONE 2026-07-14. The container healthcheck spams the log with one
      access line per probe.** Since the honest `HEALTHCHECK` landed (ARCH-25, 2026-07-09) uvicorn
      access-logged every probe: `INFO: 127.0.0.1:… - "GET /health HTTP/1.1" 200 OK` every 30 s, forever —
      ~2.9k lines/day drowning real events and burning the BUG-30 rotation budget. Fix as prescribed: a
      `logging.Filter` on `uvicorn.access` (`_HealthProbeAccessFilter`, `runners/web_server.py`) dropping
      2xx `/health` **and** `/ready` (covered ahead of ARCH-45), installed in `_build_uvicorn_server` — the
      single choke point both serve paths share. Non-2xx probes stay visible (a failing probe is exactly the
      event worth seeing); query strings don't unhide a probe; exact paths only (`/healthz` etc. unaffected).
      One subtlety the live verification caught: the filter must attach AFTER `uvicorn.Config(...)` — its
      `__init__` applies uvicorn's dictConfig, which resets the `uvicorn.access` logger's filters (attached
      before, the filter is silently wiped). Verified against a real uvicorn server driven through
      `_build_uvicorn_server`: two 200-probes dropped, a normal 200 request and a 503 probe both logged.
      6 new tests (`test_web_server_logging.py`, incl. no-duplicate-on-rebuild); suite 1415 pass / 7 skip;
      pyright clean on the changed files.
      docs: none — removes internal log noise; no manifest doc describes access-log contents.
- [x] **QUAL-80** [MQTT][TEST] `[release]` — **DONE 2026-07-09.** Golden catalog re-pinned
      `8159b4b0068d1c63` → **`16eee0f2f7832995`** (bridge commit `9714c3c3…`), at the bridge's request. Both
      driving fixes came out of the WB7 bring-up: **DRV-23** — WB-passthrough devices now expose feedback at
      top-level `state.<field>`, the read path voice depends on (`mqtt_integration.md` §5c), with the internal
      `mirrored` bucket retired; and **DRV-25** — `power` becomes a *readable* field on the 39 relay-switch
      devices, canonical `on`/`off`. Verified before pinning rather than trusting the request: golden's own
      `version` is `16eee0f2f7832995`; **39 of 79** devices changed, each gaining a `fields` entry on the `power`
      capability (enum, wire `"1"/"0"` → canonical `"on"/"off"`, ru/en labels); no devices added or removed;
      zero `mirrored` occurrences remain; `openapi.json` byte-identical, so it was not re-copied and config-ui's
      generated types are untouched (`config-ui-stays-functional` needs nothing). One-way inward sync per
      `cross-repo-source-of-truth`; `PIN.bridge_commit` mirrors `STAMP.bridge_commit`, never the repo HEAD
      (`cc5d4b4`) — the convention `test_pin_matches_stamp` guards, and which QUAL-75 once broke. Fixture stamp
      bumped; no fixture binds capability `fields`. eval-commons `5427063`: suite 40/40, pin guards 10/10.
      Voice side: `parse_catalog` reads the new shape (`cabinet_spots` `power` → `enum` field), unit suite 1358
      pass, and the change is purely additive — `_QUANTITY_FIELDS` still searches only `temperature`/`humidity`.
      **Not yet live:** the WB7 serves the old catalog until the bridge image is rebuilt and redeployed; a sensor
      read and a switch read want re-verifying against the controller afterwards.

- [x] **QUAL-81** [MQTT][TEST] `[release]` — **DONE 2026-07-10.** DRV-28 HVAC contract consumed: golden
      re-pinned `16eee0f2…` → **`5622ba7a1a78102a`** (bridge `eef4e8cc…`; one pin covers their DRV-25/26/28 arc),
      and the HVAC intent mapping moved off hardcoded `climate.*`. The three ACs are `MitsubishiHvac` with six
      capabilities (`power`, `mode`/`fan`/`vane`/`widevane` `.set{value}`, `temperature.set{value}` 16–31 °C);
      floors keep `climate`. Verified against their committed artifacts before pinning: exactly the 3 `*_hvac`
      devices changed, openapi +1 schema (`MitsubishiHvacState`).
      Voice: a per-device **binding table** (`_SETPOINT_BINDINGS`/`_CHOICE_BINDINGS`, new dialect first, old as
      fallback) drives `_handle_set_setpoint` and `_hvac_choice`, so the handler is correct against EITHER live
      catalog — the bridge's WB7 redeploy is still owed, and deploy order must not matter.
      `_single_capable_or_clarify`/`_capable_devices` accept an any-of capability tuple (set-temperature is
      `climate` on a floor, `temperature` on an AC — exactly fixture F21's clarify). `_QUANTITY_FIELDS`
      unchanged: `shower_sauna_sensors` still carries a `temperature` field that IS the measurement; the AC's
      old `temperature` field was its SETPOINT, so «какая температура» in an AC room had been answering the set
      target — a latent wrong answer the DRV-28 rename itself retired (comment records it).
      eval-commons (`ee66fd8`): fixtures migrated with the contract (F80→`mode.set{value:cool}`,
      F81→`fan.set{value:speed_2}`, F96→`temperature.set{value:22}`, F32's hvac read target →`temperature`);
      **F21 exposed a fixture-schema gap** — its two clarify candidates now bind different capabilities, so the
      clarify expect's `capability` accepts a list ("every candidate carries at least one of these") with the
      guard test updated; suite 40/40. Voice tests: the harness stub migrated to the DRV-28 shape (all 47
      existing tests pass against it — F21's clarify spans both dialects through the any-of picker), plus 7 new
      (new-dialect setpoint/mode/fan incl. the ru-label match, range check on the `value` spec, and a
      `children_split_legacy` old-dialect device proving the fallback). **Notable: no mode/fan handler tests
      existed at all** — the same blind spot that let the firmware drop every mode command (their DRV-26).
      pyright 0, import-linter 11/11, suite 1373. Heads-ups logged, no voice action: bridge VWB-32 (retained
      catalog-version topic wiped by the reboot), VWB-33 (language-data ownership design — half ours, they
      coordinate). **Hardware smoke owed AFTER the bridge's WB7 redeploy:** «включи кондиционер в детской» →
      `power.on`; a mode change → `mode.set` (dead firmware-side until DRV-26); «какая температура в детской» →
      `room_temperature`.

- [x] **QUAL-83** [QUAL][CONFIG] `[release]` — **✓ DONE 2026-07-16. Dead config-field + dead-code sweep**
      (ARCH-50 §B/F-F3; every deletion re-verified by grep before removal). **Config fields deleted (~30):**
      the whole `AssetConfig` download/cache block (11); `DateTimeHandlerConfig` + `GreetingsHandlerConfig`
      whole (+ their `IntentSystemConfig` fields + validator-map entries); 4 of 5 `ContextualCommandsConfig`
      (`latency_threshold_ms` stays — the one read); 5 `MonitoringConfig` (`debug_tools_enabled` +
      `notifications_default_channel` verified LIVE and kept); 3 `NLUAnalysisPerformanceConfig`;
      `NLUAnalysisLanguagesConfig` whole — and the capabilities endpoint now reports the CANONICAL
      top-level language policy set at initialize (QUAL-36) instead of a `["ru","en"]` literal; singles:
      mic `auto_resample`/`resample_quality` (+ dead validator), `VoiceTriggerConfig.buffer_seconds`/
      `strict_validation`, `NLUConfig.persist_language_preference`, `VADConfig.processing_timeout_ms`,
      workflow `monitoring_enabled`/`enable_vad_processing`, web `websocket_enabled`/`rest_api_enabled`,
      CLI `prompt_prefix`/`history_enabled`. **Dead code deleted:** `get_provider_capabilities` (PROD-8
      delegation discharged), `EnhancedHandlerManager` (63 lines incl. the third file-scan discovery
      mechanism), `ComponentRegistry`+`ComponentLoader` (+ config exports), `add_handler`/`remove_handler`
      + the legacy `_get_handler_patterns` (donation-less registration now raises explicitly;
      `reload_handlers` stays). **Orphan TOMLs deleted:** vad-development/vad-production/vad-testing/
      vosk-test; `full.toml` deleted too — `test_audio_negotiator.py` repointed to
      `standalone-x86_64.toml` (same mic-16k role; 22/22 green). TOML template generator + all live TOMLs
      stripped (one over-strip — `[asr]`/`[voice_trigger]` `resample_quality`, still model-live — caught
      by the master-completeness gate and restored); `config-ui/openapi.json` re-dumped, types
      regenerated, `api.ts` trimmed; check + build green. Verified: full suite 1411 passed / 7 skipped,
      config-validator CI-mode all valid, master-completeness valid, import contracts 11/11.
      **Discovered en route → filed QUAL-85 [deferred]:** `config/schemas.py` parallel schema tree;
      ASR/VT resampling fields whose only reader (`resolve_audio_config`) is itself caller-less; api.ts
      hand-interface drift. docs: guides/vad — the `processing_timeout_ms` row removed from the [vad]
      field table (the field is gone); no other manifest node describes deleted fields.
### Bugs (BUG)
- [x] **BUG-42** [TEST] `[deferred]` — **Order-dependent flake:
      `test_arch36_satellite.py::test_recorder_declined_and_next_utterance_finalizes` fails in the full
      suite, passes in isolation** (its file also passes alone, 14/14). Reproduced identically on
      2026-07-11 pre- and post-BUILD-29 trees (1 failed / 1379 passed both times), so it is
      cross-file state leakage (another test's residue), not a recent regression. **CLOSED 2026-07-14 —
      FOLDED INTO TEST-20.** Same test, same defect: the diagnosis above was wrong — the failure DOES
      reproduce in isolation (8/20 measured at fix time), so cross-file leakage is falsified; one
      load-sensitive root cause (the test's mtime-ordering coin flip), fixed under TEST-20.
      docs: none — folded into TEST-20; test-internal.
### Tests (TEST)
- [x] **TEST-0** (P0) — Minimal end-to-end smoke/integration harness (refactor safety net, Gate 0). **DONE
      2026-06-01** → `irene/tests/test_smoke_e2e.py` (**5 passed / 1 xfailed**, ~21s; boots the WebAPI runner once
      as a subprocess + a CLI headless check). Green flows: WebAPI boots, `привет`→`greeting.hello`, `/nlu/recognize`
      responds, LLM-offline conversation degrades gracefully (200, no crash — guards QUAL-14/15), CLI headless
      executes. ~~**xfail:** `test_set_timer_end_to_end`~~ — **now a real PASS** (the timer breakage closed: QUAL-9
      F&F via QUAL-28 + QUAL-11 Stage A recognition fix, 2026-06-03); the smoke suite guards it green. **New finding via TEST-0:** `поставь таймер на 5 минут` is **not recognized** (falls to
      `conversation.general`) *despite the timer donation being loaded* — a recognition/matching gap → logged under
      QUAL-11. So timers are **doubly broken** (recognition AND the F&F launch crash). Still TODO: wire into CI (BUILD-2).
- [x] **TEST-1** (P1) — Fix broken tests referencing removed/renamed symbols. **DONE 2026-06-01**:
      `ConversationContext`→`UnifiedConversationContext` (rename); `TTLCache`/`ContextualCommandPerformanceManager`/
      `initialize_performance_manager` were **deleted** (v13→v15 contextual-command unification) → those tests
      skipped-with-reason; `Intent.text`→`raw_text`, `ComponentConfig.audio_output`→`audio` renamed in tests.
- [x] **TEST-2** (P1) — **DONE 2026-06-15 — SUBSUMED BY TEST-7.** The deliberately-paused suite-stabilization is
      complete: TEST-7 rewrote/deleted the drifted clusters and greened the suite (the `56→82 failed` drift this task
      tracked is now `0 failed`). Closed as subsumed. _Original paused note below._ **PAUSED 2026-06-01 (deliberate — see strategy note).** Suite now **runs** and is a
      partial safety net: 136/100/0 → **166 passed / 56 failed / 13 skipped / 2 xfailed** (committed). Cleared:
      async config, symbol renames, obsolete skips, hardcoded-path bug, and the fixture-wiring cluster. The
      remaining 56 drift failures are **left unfixed on purpose** (will be obsoleted by ARCH/review then rewritten,
      TEST-7). Diagnosed-but-not-fixed clusters (for whoever does the rewrite): `test_cascading_nlu`
      provider-metadata (`entities["provider"]` vs `_recognition_provider`, ~7 — design-intent question),
      VAD/ASR metrics dict-vs-object (~8), `spacy_asset_integration` mock-vs-MagicMock (2), attr renames
      (`IntentResult.error_type`, `SpaCyNLUProvider.model_name`, `IntentRegistry._handlers`,
      `IntentComponent.get_system_status`), phase4 contextual-command + assertions. Value already banked:
      **QUAL-21**, **QUAL-22**, text_processor trace fix.
- [x] **TEST-3** [FAF] (P2) — **DONE 2026-06-15.** Fire-and-forget lifecycle coverage. The store + happy launch→complete
      path were already covered (`test_action_store.py`, `client_registry` 76%); added `test_fire_and_forget_coverage.py`
      (11 tests) for the previously-uncovered `IntentHandler` F&F machinery: launch-registers, completion-reaps-and-records-
      success, **error** → failure history, **cancel** → "cancelled", **launch-failure** → failed metadata, timeout-monitor
      register+reap, `cleanup_timeout_tasks`, metrics start/completion, notification scheduling (owned vs no-session), and
      the handler `cancel_action`/`get_active_actions`. **`handlers/base.py` 45%→52%** (and the whole F&F lifecycle
      launch→complete→error→cancel→cleanup is now exercised). Hermetic (object.__new__ handler, fresh patched
      ClientRegistry, asyncio.run). No product bugs surfaced. The deferred-result *delivery routing* through the
      OutputManager (ARCH-15) stays integration/smoke-level. Suite green (901 passed, plain pytest).
- [x] **TEST-4** [PEX] (P1) — **DONE 2026-06-15.** Parameter-extraction coverage. Its named scope is now covered:
      **the 8 ParameterTypes** via `HybridKeywordMatcher._extract_by_type` (INTEGER/FLOAT/BOOLEAN/CHOICE/DURATION/STRING
      branches + DATETIME/ENTITY fallthrough) + `_convert_and_validate_parameter`/`validate_config`
      (`test_param_extraction_coverage.py`), and **the 4 entity resolvers** Temporal/Quantity (pure parsers, full) +
      Device/Location (graceful degradation with no asset loader — verifies the QUAL-11 P0 #4 fix; the review's old
      fatal-crash is gone) (`test_entity_resolver_coverage.py`). 18 tests; `hybrid_keyword_matcher` 0%→19%,
      `entity_resolver` 62%→79%, `donations` 87%→89%. No product bugs surfaced. The remaining ~80% of
      `hybrid_keyword_matcher` (the donation-driven keyword/fuzzy `recognize()` pipeline) needs loaded donations + spaCy
      and is integration/smoke-level — out of TEST-4's "8 ParameterTypes / 4 resolvers / pattern-matching" unit scope;
      `spacy_provider` (21%) is mostly the review-confirmed dead Matcher/EntityRuler code (not worth chasing).
- [x] **TEST-5** [TXTPROC] (P2) — **DONE 2026-06-15.** Text-processor / normalizer coverage. The provider
      (`UnifiedTextProcessor`) was already covered by `test_text_processing.py`; added `test_text_normalizers_coverage.py`
      (11 tests) for the actual normalizers + the component's live methods: **NumberNormalizer** (ru digit→words,
      no-number passthrough, empty), **PrepareNormalizer** (pure-Cyrillic fast passthrough / Latin→Cyrillic transcription /
      inline number processing / `changeLatin=skip`), **RunormNormalizer** missing-dependency degradation (no model
      download), and `TextProcessorComponent.process` no-provider passthrough + `convert_numbers_to_words`. **`text_normalizers.py`
      25%→58%**; `text_processor_component` 29%→30%. Reconciliation (Invariant #8): the `text_processing_review.md`
      "process() hardcodes the general stage" finding was fixed by **QUAL-13** (`process(..., stage="asr_output")` routes
      by stage now). No product bugs surfaced. The remaining component % is the review-confirmed **dead** stage routing +
      the broken text-processing WebAPI (a known QUAL-12 finding) + `RunormNormalizer`'s model path (offline hazard) —
      deliberately not chased.
- [x] **TEST-6** (P2) — **DONE 2026-06-15 (TEST-7 Phase C/D).** ASR provider-fallback + resampling coverage restored:
      the `test_phase7_performance` resampling-latency tests were rewritten to `AudioProcessor.resample_audio_data`
      (`audio_processor.py` 71%), and the ASR provider-selection/fallback surface is covered by `test_asr_component_coverage`
      (`asr_component.py` 46%; the new test file 98%). Individual ASR providers' model-loading internals stay uncovered
      (smoke/model territory) — out of TEST-6's fallback+resampling scope. _Original:_ Restore ASR provider-fallback +
      resampling coverage (the 7 phase7 tests skipped in TEST-1 called the removed `_handle_sample_rate_mismatch`).
- [x] **TEST-7** (P1) — **DONE 2026-06-15 — suite rewritten + 100% green; coverage 45.6%→52.3%; full-suite pytest is
      now a hard CI gate (`backend-health.yml`).** Residual deep-pipeline coverage (`workflow_manager` 29%, `context`
      31%) accepted as integration/smoke-level (user-approved). Phases A–D below. Gate lifted** (ARCH-1..5 ✓ + QUAL-8/10/12/14 ✓ all `[x]`). Rewrite the
      test suite against the stabilized architecture; absorbs TEST-2 (the paused suite) + the coverage goals
      TEST-3/4/5/6/8. **Approach LOCKED with user 2026-06-15 (6 decisions):** (1) **same method as the release-plan
      new-code** — contract-level unit tests at the ports/seams (`object.__new__`/`SimpleNamespace`, test the
      off-paths, co-located), smoke (`test_smoke_e2e`) as the e2e backstop; (2) **100% green** (no xfail tail);
      (3) **delete** stale tests outright; (4) **all clusters in one sweep** (incl. the new-code wiring gaps —
      `replay_trace`/`voice_runner`/trace wiring); (5) **Phases A+B solo, then a multi-agent workflow** for the bulk
      rewrite/coverage (C/D); (6) **`pytest-cov` + closing the coverage gap is MANDATORY** (measurement is part of DoD).
      Triage rule per failing test: behavior gone → delete; behavior live but asserts a drifted internal → rewrite to
      the port/public contract; test right, code wrong → fix the code (TEST-1/2 banked QUAL-21/22 this way). **Phase A
      DONE 2026-06-15:** added `pytest-cov` + `pysqlite3-binary` (the runtime CPython 3.11.4 is built without stdlib
      `_sqlite3`, which coverage needs — mirrored wb-mqtt-bridge's pysqlite3 alias via a committed `sitecustomize.py`
      + `scripts/install_sqlite_shim.sh`; pinned `.python-version` 3.11.4 locally to stop a 3.12 drift). **Baseline
      coverage = 45.6% lines (17,546/38,488), 265 modules.** Confirmed the thesis: the request hot-path is the cold
      zone (`workflow_manager` 20%, `core/components` 20%, `context` 25%, `asr_component` 25%, `nlu_component` 38%,
      `orchestrator` 41%, `voice_assistant` 48%), while new pure-logic is well-covered (`trace_context` 76%,
      `trace_input` 89%) but new wiring is thin (`replay_trace` 34%, `voice_runner` 34%). Suite baseline restored at
      82 failed / 472 passed / 15 skipped (the ±1 is a coverage-perturbed timing benchmark). **Phase B DONE
      2026-06-15 → `docs/review/test7_triage.md`:** triaged all 82 failures into ~28 delete / ~50 rewrite / 3 fix-code,
      and risk-ranked the cold spine into Tiers (Tier-1 = `workflow_manager` 20%, `core/components` 20%, `nlu_component`
      38%, `context` 25%, `voice_assistant` 48%, `asr_component` 25%, + the 5 capability handlers/TEST-8). Biggest
      cluster (phase4 contextual, 21) = DELETE (built on the deleted perf-manager; behavior re-covered fresh). 3
      real-bug suspects surfaced: a machine-specific `device_id = 7` hardcoded in `config-master.toml` (Invariant #2),
      `llm.console` empty param schema, and a VAD-requirement error-message contract (touches QUAL-46). **NEXT: Phase
      C/D = the multi-agent workflow** (green the suite per-cluster, then coverage-fill per Tier-1 module). Done when:
      100% green + Tier-1 cold subsystems covered (confirmed by pytest-cov). **Phase C (green the suite) — bulk DONE
      2026-06-15 via a 19-agent workflow + verifier:** deleted 4 stale files (phase4 ×3 + phase6) and rewrote 13 drifted
      clusters to current port/public contracts (net −3,555 test lines; spot-checked genuine, not gamed). Fixed an
      order-dependent event-loop failure in `test_no_intent_clarification` (`asyncio.get_event_loop().run_until_complete`
      → `asyncio.run`; passed alone, failed in-suite). **Suite 82→3 failed / 555 passed.** The remaining **3 reds are
      the 2 fix-code decisions surfaced to the user** (per the rule: never fix product code autonomously): (a) `device_id`
      in `config-master` — the alignment test wants `device_id`→`device` but the model still uses `device_id`; +
      machine-specific `= 7` value; (b) `llm.console` empty parameter schema (offline-floor stub) flagged by 2 tests.
      **Phase C COMPLETE 2026-06-15 — suite 100% GREEN (558 passed / 0 failed / 7 skipped, from 82 failed).** User
      decided both fix-code questions as test/config fixes (no product-schema change): (a) `device_id` is the live
      `MicrophoneInputConfig` field (the `→device` rename was never done) → dropped from the alignment test's
      deprecated-names list + cleaned the machine-specific `device_id = 7` to the `None` default in `config-master`;
      (b) `llm.console` is a *registered* offline-floor stub (entry-point exists) with no runtime params by design →
      exempted declared stubs in the schema test (like text-processors) + rewrote the stale phantom test (console is no
      longer unregistered; uses a genuinely-unregistered name to keep phantom-detection covered). **Phase D
      (coverage fill) DONE 2026-06-15 via a 13-agent workflow:** new characterization tests at the seams for the Tier-1
      spine + 5 capability handlers + new-code wiring (~329 tests, 13 `test_*_coverage.py` files). **Overall coverage
      45.6% → 52.3%.** Big gains: `voice_runner` 34→85%, `replay_trace` 34→82%, `voice_assistant` 48→72%,
      `core/components` 20→56%, `nlu_component` 38→59%, `asr_component` 25→46%. Residual-cold (deep pipeline paths that
      need a booted core — smoke territory, not unit): `workflow_manager` 20→29%, `context` 25→31%. **No product bugs
      surfaced** (agents covered clearly-correct behavior; nothing to decide). The workflow run crashed mid-flight (lost
      its verifier/result), recovered by hand: all 13 files were written + genuine (spot-checked, not gamed); fixed one
      latent `asyncio.get_event_loop()` anti-pattern the new tests EXPOSED in `test_clarification.py` (same class as the
      Phase-C `no_intent_clarification` fix). **Suite 100% green (888 passed / 0 failed / 7 skipped); 9/9 contracts; no
      product code changed.** Optional follow-up: a deep-path round for `workflow_manager`/`context` (or accept as
      integration-level).
- [x] **TEST-8** [PORTS] (P1) — **DONE 2026-06-15 (TEST-7 Phase D).** All 5 capability handlers now covered through
      their injected ports + the graceful-degradation-when-absent path (the QUAL-24 bug class): `text_enhancement` 99%,
      `speech_recognition` 97%, `translation` 97%, `audio_playback` 80%, `voice_synthesis` 65% (the residual is the
      model-dependent TTS execution → smoke). The QUAL-24 repair is now verified. _Original scope below._
      **Capability-port handler coverage (surfaced by QUAL-24).**
      QUAL-24 found that only `conversation` was ever injected — the **5 other capability handlers**
      (`voice_synthesis`, `audio_playback`, `speech_recognition`, `translation`, `text_enhancement`) were silently
      getting `None` for their component (compounded by an await-sync bug) and are now **wired for the first time**
      via domain-owned ports (`irene/intents/ports.py`). **No test exercises these handler→port paths** — so the repair
      is unverified. Cover: (1) the injection wiring itself — `IntentComponent.post_initialize_handler_dependencies`
      sets each handler's port (and `provider_control`'s registry) and handlers degrade gracefully when a component is
      absent; (2) each handler's actions through its injected port — LLM `generate_response`/`enhance_text`/`extract_*`,
      TTS `speak` + the **best-effort `stop_synthesis`/`cancel_synthesis`** (graceful no-op, no crash), Audio `play_file`
      + the **provider-delegated `pause_audio`/`resume_audio`/`stop_playback`**, ASR `switch_language`; (3) ABC
      enforcement — a component missing a port method fails at instantiation (regression guard for the ports↔components
      contract). Fixtures: the localization-asset-loader pattern + fake port impls. Relates to QUAL-24, ARCH-1.
- [x] **TEST-9** [EVAL] (P2) `[release]` — **DONE 2026-06-27.** Wired the eval-commons voice-fixture recorder (W6 of
      `../eval-commons/docs/design/fixture_recorder.md`) into this repo's `eval/`: `make record` / `record-list` /
      `record-devices` / `setup-record` targets (recorder invoked as `python -m eval_commons.record.cli`);
      committed `profiles/recording.env.example` (machine-local `recording.env` git-ignored); **added `reference` to
      the `light_unreachable` judge case** so the recorder has a line to read (§5 decision — inert to the test, it's
      judge-only) — TODO in the YAML to confirm the target stays unreachable on a live run; repointed
      `fixtures/README.md` + `eval/README.md` at `make record` (kept the ffmpeg/TTS recipe as the alternative). Verified:
      `make record-list` derives both fixtures, `eval-fixture-record` console script resolves, `make record-devices`
      lists inputs, `make cli` still 5/5. Recording the WAVs themselves is the remaining manual (human-at-mic) step,
      which this unblocks. `config-ui-stays-functional` N/A. The recorder code + its design live in eval-commons (its
      own repo/process).
- [x] **TEST-10** [EVAL] (P2) `[release]` — **DONE 2026-06-27.** Version the WS audio fixtures: carved
      `!eval/fixtures/*.wav` out of the repo's blanket `*.wav` ignore (`.gitignore`). The blanket rule had swept the
      fixtures in by accident (generic "don't commit audio"), which made the WS suite **un-runnable in CI** (no mic)
      and **non-reproducible** (re-recording → different waveform → different WER). Fixtures are versioned test inputs,
      not stray audio. Verified the carve-out (eval/fixtures wav committable; other `*.wav` still ignored) and updated
      `fixtures/README.md`. Small files; git-lfs only if they grow. _(Strategic follow-up — golden traces as the
      reviewable regression inputs — is covered by the trace-system-testing design.)_
- [x] **TEST-11** [EVAL] (P2) `[deferred]` — **DONE 2026-06-27 (design).** Design for trace-driven system testing →
      `docs/design/trace_system_testing.md`. Uses the shipped ARCH-19 trace record/replay as (1) an **offline,
      deterministic, CI-able regression surface** — committed golden traces under `eval/traces/`, replayed via
      `irene-replay-trace --local` through the existing `cli_provider` (assert `exit_code === 0`), tiered
      `trace-system` (exit-code) vs `trace-ux` (DeepSeek judge) — and (2) **failure-trace capture**: always-trace +
      keep-on-failure for the live WS suite (with a small SUT enabler — `request_id` in `/ws/audio` metadata) and
      `--record-out`-on-mismatch offline, so a failed case ships a replayable trace (`--listen`/`--step`). Folds in
      the fixture-versioning fix (TEST-10) and a trace↔WAV unification idea. **Completing the design ≠ shipped:** filed
      implementation slices **TEST-12/13/14**.
- [x] **TEST-12** [EVAL] (P2) `[deferred]` — **DONE 2026-06-28.** Offline golden-trace replay surface (S1 of
      `trace_system_testing.md`) **+ the config-override enabler the user asked for.** (1) **`--set DOTTED.KEY=VALUE`**
      config overrides — `apply_dotted_overrides` in `config/manager.py` (JSON-typed coercion, applied pre-validation so
      Pydantic coerces+validates, strict: an explicit `--set` never silently falls back to defaults), wired into the
      base runner (all `irene-*` runners); 8 unit tests. No more hand-editing temp config files to tweak a setting.
      (2) **Replay surface:** `eval/trace.promptfooconfig.yaml` drives `irene-replay-trace -t … --config … --local`
      through the existing `cli_provider` (assert `exit_code === 0`) — no new `eval-commons` code; `make replay` /
      `replay-judge`; committed seed golden `eval/traces/timer_set_10min.json` (text trace, ~12 KB, portable) that
      replays **green** under the pure WB7 config; `eval/traces/README.md` + the 4th surface in `howto-new-test.md`.
      (3) **`diff_output` now normalizes volatile timestamps** (`_strip_volatile`) so a fire-and-forget action's
      `started_at` doesn't break an otherwise-deterministic golden (+ tests). Recording surfaced **BUG-1** (spelled-ru
      numerals; golden uses the digit form) and **BUG-2** (stale TTS↔Audio check — fixed here). The natural-speech timer
      golden + the `trace-ux` LLM tier await BUG-1.
- [x] **TEST-13** [EVAL] (P2) `[deferred]` — **DONE 2026-06-28.** Failure-trace capture for the live WS suite (S2,
      design `trace_system_testing.md`). **D-6 SUT enabler:** when tracing is on, `WorkflowManager.process_text_input`/
      `process_audio_input` stamp the trace `request_id` onto `result.metadata` (the `/ws/audio` response already
      spreads `result.metadata`, so it surfaces with no handler change); additive, gated on tracing; config-ui N/A.
      **D-13 keep-on-failure helper:** new project-agnostic `eval_commons.failures` (eval-commons `e740c80`) — reads the
      promptfoo results JSON and copies each FAILING case's `<traces_dir>/<request_id>.json` into `traces/failures/`
      (prunes the rest); robust to promptfoo nesting/version drift; reusable by wb-mqtt-bridge unchanged. Wired into the
      thin `eval/Makefile` `ws` target behind `TRACE=1` (preserves promptfoo's exit code) + documented in `eval/README`.
      **D-7 offline tier:** already satisfied — `irene-replay-trace --record-out` keeps the replayed trace on a mismatch
      (the replay diffs `{text,success,actions}`); documented in the README. Reconciliation: `--record-out` pre-existed
      (TEST-12); `/ws/audio` already had `intent_name` (QUAL-54) but not `request_id`. Gates: suite 1106 passed (+ 2
      workflow_manager tests for the stamp; eval-commons +6), pyright 0, import-linter 9/9. Remaining: **TEST-14**
      (trace↔WAV).
- [x] **TEST-14** [EVAL] (P3) `[deferred]` — **DONE 2026-06-28.** Trace↔WAV unification (S3 / D-9): a golden audio
      trace already carries its captured audio (base64 PCM16, the same bytes `--listen` plays), so a new
      `irene-replay-trace --extract-wav <file.wav>` decodes it to a standard WAV — **record once, test twice** (one
      golden trace serves both the offline replay tier *and* the live WS suite, no re-recording with a mic). It's a pure
      trace→WAV transform: a standalone CLI mode that builds no core and runs no replay; writes at the captured
      rate/channels (Irene's 16 kHz mono PCM16 → directly usable as a WS fixture; eval-commons `conform` aligns target
      format if ever needed). Module fn `write_trace_audio_to_wav` (rejects text traces / non-PCM16). Documented in
      `eval/README` (record-once-test-twice). Gates: suite 1109 passed (+3 extract-wav tests), pyright 0, import-linter
      9/9. **This closes the trace-driven system-testing series** (TEST-11 design → TEST-12 offline replay → TEST-13
      live-WS failure capture → TEST-14 trace↔WAV); no TEST- trace-playback tasks remain open.
- [x] **TEST-15** [EVAL][WS] (P3) `[deferred]` — **DONE 2026-07-01.** The WS system suite now asserts ASR/WER for
      offline ASR. **task-start-reconciliation flipped the premise:** the ledger assumed the SUT had to be changed to
      surface the recognized transcript, but a live probe showed the SUT **already** exposes it at
      `metadata.audio_processing.transcribed_text` on the batch path (`_process_single_audio_pipeline` writes it; the
      `/ws/audio` handler forwards it in `_meta`). So the fix is **eval-side only** (user-confirmed approach): the shared
      `ws_audio_provider` (in `../eval-commons`) now resolves the transcript in priority order —
      `metadata.audio_processing.transcribed_text` → last streaming `partial` → reply text — so WER scores the
      *recognized speech*, not the assistant's reply. **No SUT change.** Verified live against `configs/embedded-armv7`:
      `make ws TARGET=local` = **4/4 pass** (WER 0 on `«поставь таймер на десять минут»`; intent `timer.set`; both
      DeepSeek-judged UX cases pass with `DEEPSEEK_API_KEY` set), `make cli` still 5/5. Cleared the now-confirmed
      intent-name + unreachable-device TODOs in `ws.promptfooconfig.yaml`; refreshed `eval/README` (WER tier works, UX
      runs live). **This closes the trace-driven system-testing implementation slices** (TEST-12/13/14/15); the WS
      suite is fully green where a local SUT can assert it. (DeepSeek Russian judge *calibration* remains advisory, not
      a blocker — a standing UX-tier note, not a TEST- task.)
- [x] **TEST-16** [EVAL][UX] (P3) `[deferred]` — **DONE 2026-07-02 (user suspected obsolete; reconciliation
      showed it was blocked on the user's own gold labels — completed interactively in-session).** The DeepSeek
      Russian UX judge is now **calibrated against native-Russian-speaker gold labels**: a regenerated 20-case set
      (the 2026-07-01 probe lived in a session scratchpad and was gone), user-labeled live (16 confident + 4
      borderline, excluded from κ), graded through the same llm-rubric→DeepSeek path against the SHIPPED rubrics.
      Iterations with re-measure-all discipline: shipped rubric 81%/κ0.625 (judge too strict on terse replies,
      lenient on bureaucratese — the OPPOSITE bias profile of the Claude-labeled probe, vindicating the human
      gate) → terse-passes/bureaucratese-fails/next-step-optional 94%/κ0.875 → in-condition mixed-language example
      **16/16, κ=1.0 in-sample, verdicts stable across repeat runs**. All four borderlines got defensible verdicts.
      **Housed** in eval-commons `examples/ru-ux-calibration/` (set + gold + scorer + README, commit `4dd73d7`).
      **Rubric infrastructure fixed en route:** the documented `file://…yaml#anchor` pattern NEVER worked in
      promptfoo (fragment treated as filename — why the live suite had inline copies); shared rubrics split into
      per-rubric `{ru,en}/*.txt` files, the yaml files retired, ARCHITECTURE §7.1 flipped to CALIBRATED, and the
      live `ws.promptfooconfig.yaml` UX cases (RU+EN ×4) now reference the shared files directly (path proven live
      from `eval/`). EN rubrics carry the same structural improvements, marked uncalibrated. **Gate met: Russian
      UX pass/fail is CI-trustworthy** — standing caveats: κ is in-sample (add fresh negatives as suites grow) and
      the calibration set must be re-run after ANY rubric edit.
- [x] **TEST-17** [EVAL][MQTT] (P2) `[release]` — **DONE 2026-07-05. The Irene↔bridge contract pinned into
      `eval-commons/contracts/`** (ARCH-26 §14 one-way inward sync; eval-commons `e571241`). Pinned byte-identical
      from `wb-mqtt-bridge/contracts/` @ bridge `59f4f46` / catalog `7a1149c7` (contract patch **v1.1** + alias
      vocabulary — pinning deliberately waited for VWB-20 so the first pin is the only pin): (a)
      `openapi.json` (CatalogResponse + typed `CatalogParam` + canonical action shapes); (b) `catalog.golden.json`
      (11 rooms + `global` aggregates + scenario managers, aliases, ru/en enum labels, units); plus the bridge
      `STAMP.json`, a voice-side `PIN.json` (commit/version/date of the pin), and a consumer-story
      `contracts/README.md` (re-pin procedure). (e) **The pin is load-bearing**: `tests/test_contracts_pin.py`
      (8) validates the golden against the pinned `CatalogResponse` JSON Schema (the two halves can't disagree),
      checks STAMP↔PIN↔golden version agreement, and asserts the v1.1 shape guarantees (aliases authored, ru
      enum labels, °C/% units, `values`-XOR-`options_from`, no empty husks) — re-pinning a pre-patch artifact
      fails loudly. **Carve-outs:** (c) the real WB7 dump joins when the bridge's `ops/` cutover happens (its
      own README tracks it); (d) the `{utterance → canonical command}` crossover fixtures co-develop with
      ARCH-8 PR-1 / TEST-18 (recorded there). `jsonschema` added to eval-commons dev extra.
- [x] **TEST-18** [EVAL][MQTT] (P3) `[deferred]` — **DONE 2026-07-05. The `device_command` capture provider + Irene
      producer contract tests (ARCH-26 §14) — the suite EXISTS and RUNS: first scoreboard 16/23** (all tier-1
      actuation + clarify green; red = 3 reads → ARCH-8 PR-5, F40/F42 scenario routing → QUAL-64 matcher
      tuning [user decision: leave red, tune later], F41 transliteration + F06 compound numeral → QUAL-35
      T2 evidence). Two slices (fixtures-first fold, user 2026-07-05):
      • **Slice A — crossover fixtures — DONE 2026-07-05** (interactive; eval-commons `941e245`; step 0
        re-pin @ bridge `ee0a71d` / catalog `91909b54` was `e0d6b45`). Deliverable:
        **`eval-commons/contracts/crossover_fixtures.json` — 23 fixtures** against the pinned catalog, all
        four expect kinds `actuate | room-group | read | clarify`, tiered 1/2 (green-able with the QUAL-35
        T1 donation baseline vs needs T2 units/transliteration), **guarded by
        `tests/test_crossover_fixtures.py`** (8 tests: every binding verified against the golden — device
        ids/capabilities/actions/param ranges/enums/rooms/groups/fields + fixtures↔pin version agreement;
        16/16 green together with the pin guards — a re-pin flags stale fixtures loudly). Coverage: aliases
        («телек»/«эппл»/«радиаторы»/«пол»), typed params with °C/% ranges, scenario enum via ru label
        («кино с видеокассеты» → `movie_vhs`) + a transliteration case («эппл ти ви» → `movie_appletv`),
        room-group scope `auto` vs «весь»→`all`, room aliases «зал»/«квартира», the depth-doctrine
        named-device case («закрой тюль слева» stays device-form), the power-fence cases («печь»/«розетки»
        reachable by NAME only). **The 3 open decisions resolved (user 2026-07-05):** light-subset pair
        nouns («ночники»/«тумбочки»/«полки») **DROPPED from v1** — user will add bridge-side compound
        devices later (those fixtures return with that re-pin); same-room capability ambiguity → **CLARIFY
        in v1** (F20 playback, F21 climate), priority rules = later release → **QUAL-63**; sensor reads
        **INCLUDED** (F30–F32, incl. `any_of` for the physically-equivalent bedroom room-temperature
        sources). Immediately consumable by bridge VWB-16; voice-side this is the acceptance spec ARCH-8
        PR-3/PR-4 build toward (test-first).
        _Orig:_ **(UNGATED — startable now, pure data against the TEST-17 pin).** Author the
        `{utterance → expected canonical command}` set into `eval-commons/contracts/` next to the pinned golden:
        every parse+resolution path the golden exercises — power on/off via alias («включи свет в детской»),
        ranged setters with units («поставь 22 градуса в спальне» → `climate.set_setpoint {temp: 22}`), percent
        («яркость на 30»), cover, aggregates («выключи свет везде» → `all_lights`), scenario enums by ru label
        («кино с видеокассеты» → `scenario.set {value: movie_vhs}`), room-alias forms («в зале»), sensor read.
        Immediately consumable by the bridge's VWB-16 consumer half; voice-side they are the **acceptance spec
        PR-3/PR-4 build toward** (test-first — the resolver meets a pre-existing failing suite, not post-hoc
        assertions). NO input-switching fixtures (bridge VWB-19 gate, per QUAL-35 note).
      • **Slice B — DONE 2026-07-05** (eval-commons `1bc7b03` + voice eval wiring): built as a **mock-bridge
        capture** (refines §14.3's in-process capture — operationally superior: `eval_commons/mock_bridge.py`
        serves the PINNED golden at `/system/catalog` and records every canonical POST fixture-shaped, so the
        run also exercises the real `BridgeClient` wire serialization + the real startup catalog pull);
        `device_command_provider` drives `/execute/command`, `device_command_assert` compares against the
        fixture `expect`, `fixtures_to_tests` GENERATES the promptfoo cases (fixtures stay the single source
        of truth). Voice side: `eval/device.promptfooconfig.yaml` + `make device / device-auto` (derives the
        SUT config — env cannot override nested TOML) + EXECUTE_URL/BRIDGE_CAPTURE_URL in the target profiles.
        _Orig:_ **(~~gated on ARCH-8 PR-1~~ UNGATED 2026-07-05).** A new eval-commons
        promptfoo provider drives Irene with an utterance and returns the emitted canonical `DeviceCommand`
        (captured by the PR-1 capturing bridge `OutputPort`, not POSTed) for assertion against the Slice-A
        fixtures + the pinned openapi schema — the **producer** half of the bidirectional contract (the bridge's
        consumer half = VWB-16). **Text-input first** (isolates NLU→resolver→handler, deterministic, no
        audio/bridge); audio→canonical later (recorded RU fixtures, WS-suite pattern). The full suite turns
        EXECUTABLE at ARCH-8 PR-4 + the QUAL-35 T1 donation baseline. ~~Gated on TEST-17~~ (pinned 2026-07-05).
        Design §14.

- [x] **TEST-20** [TEST] `[deferred]` — **DONE 2026-07-14.**
      **`test_arch36_satellite.py::test_recorder_declined_and_next_utterance_finalizes` is flaky (~3/8).**
      Failed intermittently in isolation on a clean tree (measured 2026-07-09, 3/8; confirmed not caused by
      the BUG-35 change — reproduced with that diff stashed). The task-start decision ("test bug or product
      race?") came down firmly on **test bug**: the recorder itself is deterministic (T-5 finalization, uuid
      filenames — no overwrite possible). Root cause: the test ordered the two written trace files by
      `st_mtime`, and back-to-back writes tie on the kernel's coarse file-timestamp clock almost always
      (measured 196/200 ties), leaving "order" = filesystem hash order of two random uuid names — a coin
      flip. Fix: identify the finalized first utterance by CONTENT (its dropped-uplink payload; both
      envelopes carry `declined` since both decline tracing) instead of on-disk order. Evidence: pre-fix
      8/20 red in isolation; post-fix 0/40 in isolation, file 14/14, full suite 1409 passed / 7 skipped.
      **BUG-42 folded in** — same test, same root cause seen from the full-suite vantage; its "cross-file
      state leakage, passes in isolation" diagnosis is falsified by the isolation reproductions (one
      load-sensitive cause, not two defects).
      docs: none — test-internal fix; no user-facing surface changed.
- [x] **TEST-21** [EVAL][MQTT] `[release]` — **DONE 2026-07-10. Re-pin @ bridge v0.6.0 release cut** (the
      TEST-17 inward sync, filed-and-done same day off the bridge's release tag). Bridge commit `e965385`
      (HEAD at pin `46584f0`), bridge version **0.6.0**. The delta was version-only: `openapi.json` changed in
      exactly two places (`0.5.0` → `0.6.0`), `catalog.golden.json` **byte-identical**, catalog version
      unchanged (`5622ba7a1a78102a`) — so no fixture or code impact. PIN.json updated (bridge_commit mirrors
      STAMP.bridge_commit per the TEST-17 rule); eval-commons suite 40/40; eval-commons `3fd9091` pushed.
      This pin records the release pairing: **voice v0.5.2 ↔ bridge v0.6.0**.

### Internationalization (I18N)
### Build & CI (BUILD)
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
### Models & Assets (ASSET)
### Documentation (DOC)
- [x] **DOC-5b** (P2) — DONE 2026-06-08: regenerated `guides/DONATION_FILE_SPECIFICATION.md` for the v1.1
      two-part model (language-neutral `contract.json` + per-language `<lang>.json`), with full field reference
      from `donation_contract_v1.1.json` (method/param schema, type + entity_type enums) and the cross-language
      validation rule. Old single-file/v1.0 body + drift banner replaced.
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

### UI / config-ui (UI)
- [x] **UI-1** [DEDITOR] (P2) — **DONE 2026-06-06.** Designed the human-friendly donation/pattern authoring model →
      `config-ui/docs/donation_editor_ux.md`. **Persona-driven** (author knows handlers, **zero spaCy/NLU**): the model
      is **five everyday cards + an Advanced escape hatch** (a word [+"include its forms"] / one-of-several-words /
      a number / any word / the rest), all in example-sentence language — "token/lemma/regex/pattern" never surface.
      Organizing principle: **the v1.1 split IS the clean/spaCy line** → two editors, a clean **Contract Editor** (no
      spaCy; the good half of `ParameterSpecEditor`) and a **Phrasing Editor** that quarantines all raw spaCy. The
      three pattern locations (`token_patterns`/`slot_patterns`/`extraction_patterns`) collapse to two questions
      ("what might the user say?" / "how to find each value?"). Grounded in a 28-file survey (real spaCy vocabulary is
      small; regex mostly reduces to friendly cards). **Decisions settled here (user-approved):** translation layer is
      **frontend-only** (`patternModel.ts`, lossless-by-construction round-trip, backend keeps validate + test-match);
      raw spaCy survives as an **advanced escape hatch behind a button**, never default; **structural-first phasing**
      (UI-5 ships the functional editor + all scaffolding with the existing raw editors as interim, UI-3 swaps the
      cards into the one widget — no double build). **Scope correction (supersedes prior note):** `ParameterSpecEditor`
      is NOT "already fine" — it embeds raw `extraction_patterns` + a regex `pattern` that move to the phrasing side, so
      all three editors are in scope. **Surfaced UI-7** (config-ui-wide i18n). **Depended on QUAL-10 [PEX] ✓.**
- [x] **UI-2** [DEDITOR] (P2) — **DONE 2026-06-06.** Built the bidirectional translation layer as the
      **frontend-only** pure module `config-ui/src/utils/patternModel.ts` (decision settled in UI-1 §4 — no backend
      compile/decompile endpoint). `decompileToken`/`compileToken` (+ pattern/slot/extraction-pattern wrappers) map
      raw spaCy token dicts ↔ the human **card** model (word [TEXT/LOWER/LEMMA] / one-of [IN or alternation-regex] /
      number [LIKE_NUM or digit-regex] / any-word / the-rest / **advanced**), with the §3.3 regex reductions and
      optional/repeat ↔ `OP:"?"`/`"+"`. **Lossless by construction:** each friendly card preserves its source encoding
      and anything else is stored **verbatim** in an `advanced` card, so `compile(decompile(x))` deep-equals `x` for
      every token. **Proven** by `patternModel.test.ts` (40 tests): unit cases that lock the §3.2/§3.3 mapping + the
      **required round-trip across all 28 real phrasing files** + a guard that >50% of real tokens map to friendly
      cards (no trivial all-advanced pass). Added **vitest** + a `test` script; updated the UI-8 orphan guard to treat
      test files as entry points (a module covered by a test is intentional). The §3.4 per-parameter merge/split is
      provided at the label level (extraction/slot helpers preserve labels verbatim); the param↔label association is
      applied by **UI-3** using the contract. DoD met: `npm test` (40/40), `npm run check` (type-check + lint + orphan
      guard) + `npm run build` pass. This is the engine **UI-3** sits on.
- [x] **UI-3** [DEDITOR] (P2) — **DONE 2026-06-06.** Reimplemented the pattern editors on the UI-2 card model and
      added test-against-text. **`CardEditor`** (one word card: the 5 friendly kinds + per-card **"Advanced"** escape
      hatch → `SpacyAttributeEditor`, with "Back to cards" via `decompileToken`; "include its forms" toggle +
      optional/can-repeat). **`CardPatternsEditor`** (replaces `TokenPatternsEditor` — a list of "ways of saying it";
      controlled over `SpacyPattern[]` but keeps decompiled cards in local state and only compiles on edits, so the
      raw editor stays stable and Cancel/revert re-syncs). **`SlotCardPatternsEditor`** (replaces `SlotPatternsEditor`).
      **`PatternTester`** (UI-1 §6): a sample-sentence box → the **real recognizer** `POST /nlu/recognize`
      (`apiClient.recognizeText`) showing the recognized intent + filled values + a match/no-match badge vs the
      method's intent. Rewired the phrasing method editor to the card editors ("What might the user say?" / "How to
      find each value" / "Does this work?"); **deleted** the raw `TokenPatternsEditor`/`SlotPatternsEditor` and the
      v1.0 lemma↔token-pattern auto-sync (the per-card "forms" toggle replaces it). **§3.4 polish folded in:**
      **`ExtractionFillersEditor`** (on the UI-2 `FillerPattern` helpers) edits each contract parameter's
      `extraction_patterns` as labelled card rows, **grouped under the parameter** (with `choice_surfaces` for
      choice/entity params) — closing the per-param extraction surface that had been un-editable since UI-5 removed
      `ParameterSpecEditor`; method-level `slot_patterns` stay as "Shared value slots" referenced by label. DoD met:
      `npm test` 40/40, `npm run check` (type-check + lint + orphan guard) + `npm run build` pass. **Sits on UI-2.**
- [x] **UI-5** `[release]` [DEDITOR] (P1) — **DONE 2026-06-06.** Rebuilt the donations editor on the v1.1 split model
      (config-ui), with the QUAL-42 validations wired in and the v1.0 cruft removed. **Delivered (6 green slices):**
      **(0)** type-gen toolchain — backend `scripts/dump_openapi.py` → committed `config-ui/openapi.json` (109 paths,
      built from the runner's router factory + component routers with `core=None`, since routes build independently of
      request state); `gen:api-types` generates `src/types/openapi.gen.ts` (envelopes, via openapi-typescript) +
      `donation-{contract,language}.gen.ts` (bodies, via json-schema-to-typescript from the two v1.1 JSON Schemas).
      **(1)** `apiClient` → v1.1: `getDonationContract`/`updateDonationContract` + the QUAL-42 `getContractValidation`/
      `validateTranslation`/`translateDonation`; **removed the dead `syncParameters` (404) and rule-based
      `suggestTranslations`** (superseded by the LLM service). **(2)** `src/types/donations.ts` — generated contract/
      phrasing + envelope types (no hand-maintained drift). **(3)** new **ContractEditor** (structural: per-method
      room_context + param specs name/type/required/canonical-choices/min-max/entity_type/pattern; method names
      read-only) and **DonationValidationPanel** (QUAL-42 wiring report + LLM validate/draft, with the graceful no-LLM
      message). **(4)** new **ChoiceSurfacesEditor** (canonical → per-language spoken forms) wired into the phrasing
      method editor. **(5)** reworked the cross-language panel + LanguageTabs — **dropped the sync button/handler/prop**
      end-to-end (params are single-source under v1.1). **Drive-by:** fixed a stale `configureIntentSystem` path
      (`/intent_system/configure` → `/intents/configure`, a 404 the codegen coverage-check surfaced). **Interim/deferred
      (by design):** the raw spaCy pattern editors remain (human-card model = UI-3); editor chrome i18n = UI-7; backend
      v1.0 dead-validation removal = QUAL-43. **DoD met:** `cd config-ui && npm run check && npm run build` pass; the
      page round-trips contract + phrasing + choice_surfaces. Design: `donation_editor_ux.md` §9. **This clears the
      Invariant #4 debt deferred from QUAL-29.** _Original scope below:_
      **Rebuild the donations editor on the v1.1 split model (config-ui;
      Invariant #4 debt from QUAL-29).** QUAL-29 retired the v1.0 per-language-with-params concept on the **backend**
      (contract.json = neutral core; `<lang>.json` = phrasing) and the REST API now reflects it (`GET/PUT
      /donations/{handler}/contract`; the per-`{language}` endpoints serve phrasing; `/donations/schema` → both v1.1
      schemas; `sync-parameters` removed). **The config-ui frontend still targets the old endpoints/shape and its
      donations-editing page is therefore non-functional at runtime** (it still *builds* — TS compiles against its own
      `api.ts`). Rebuild it: **(1)** `apiClient.ts` → the v1.1 endpoints (contract get/put; phrasing get/put/validate/
      create/delete; drop `syncParameters`); **(2)** `src/types/*` → split `DonationData` into a **contract** type
      (params: name/type/required/**canonical** choices/min-max/**entity_type**, per-method **room_context**) + a
      **phrasing** type (phrases/lemmas/patterns/examples + per-param description/extraction_patterns/aliases/
      default_value/**choice_surfaces**); **(3)** a **contract editor** (one per handler) + a per-language **phrasing
      editor**; `ParameterSpecEditor` → canonical choices + `entity_type`/`room_context`, and a **`choice_surfaces`
      editor** (canonical → per-language spoken forms); **(4)** rework the cross-language panel (param parity is
      structural now — surface-completeness + method-phrasing only; drop the sync button). **Coordinate with UI-1/2/3**
      (same files: `DonationsPage`, the editors, `LanguageTabs`) — do it as ONE donations-editor redesign, not twice.
      **★ TYPE GENERATION — folded in (user-approved 2026-06-04, "stop fighting type drift"):** step (2) is done by
      **generating** `src/types/*` from the backend OpenAPI schema (`openapi-typescript`), **not** by hand-authoring them
      — hand-maintained types are the drift source this task exists to fix (Invariant #4). The backend is ~80% typed
      (104/123 routes carry a Pydantic `response_model`), so generation yields real types. **Prerequisite (backend side):**
      add a small script that dumps `app.openapi()` (static, no running server) to a **committed** `openapi.json`,
      regenerated on contract change — mirrors the bridge's committed-schema model; then a frontend `gen:api-types` script
      (`openapi-typescript <schema> -o src/types/openapi.gen.ts`) like `../wb-mqtt-bridge/ui`. **Transport stays the
      existing `fetch`-based `apiClient.ts`** (typed against the generated `paths`; optionally the tiny `openapi-fetch`).
      **OUT OF SCOPE (user, 2026-06-04): axios and react-query** — config-ui's job is load-edit-save, not server-cache;
      we adopt generation only, not the bridge's full data-layer pattern. **Two-source generation (settled by QUAL-39):**
      the donation **contract/phrasing BODY** types generate from their **canonical JSON Schemas**
      (`assets/donation_contract_v1.1.json` + `assets/donation_language_v1.1.json`, via `json-schema-to-typescript`) — the
      body stays a `Dict[str,Any]` passthrough in the API (the schemas allow `additionalProperties`; strict modeling would
      drop fields on GET→PUT). The **envelopes** (and everything else) generate from **OpenAPI** (`openapi-typescript`);
      QUAL-39 typed the previously-untyped contract envelopes so they're now strong too. DoD: `cd config-ui && npm run check` (type-check + the harmonized strict lint) **&&
      npm run build** passes + the editing page round-trips contract + phrasing.
      **This is the remaining Invariant #4 obligation deferred from QUAL-29 (user-approved 2026-06-03).**
- [x] **UI-6** `[release]` (P1) — **DONE 2026-06-04. config-ui stack harmonization with `../wb-mqtt-bridge/ui` (precedes UI-1/2/3/5).**
      **strict linting (user-insisted, same level as the bridge)** — added a bridge-identical
      `.eslintrc.cjs` (type-aware `@typescript-eslint/recommended-type-checked`; `no-floating-promises`/`no-misused-promises`
      as errors; the `any`-noise rules off), the `eslint`/`@typescript-eslint/*` + react-hooks/react-refresh devDeps, and
      `lint`/`lint:fix`/`check` scripts at `--max-warnings 0`; **fixed the runtime↔types version skew** (`@types/react`
      19→18, `@types/react-dom` 19→18, `@types/node` 24→20 to match `react@18`); added `engines: node>=18`.
      **Cleanup DONE (user: "clean up all 71 now"):** resolved all **71** the strict gate surfaced across 19 files so
      `npm run lint` (`--max-warnings 0`) + `npm run check` pass — incl. a **real latent bug fixed** (`PromptEditor.tsx`
      variable `description:` lines were shadowed by the prompt-`description:` branch and never parsed; added a
      `currentSection !== 'variables'` guard). Approach: **51 async** → `void`/arg-aware-wrap (preserves today's
      non-awaiting behavior); **14 `exhaustive-deps`** → `eslint-disable` + reason (mount/scoped loads; load fns aren't
      memoized, so adding deps would loop); **5** redundant type-assertions auto-fixed. No test net → verified by
      type-check + build (both green; `--report-unused-disable-directives` confirms every disable is needed). **ON GREEN
      (done):** folded the strict lint into the Invariant-#4 config-ui DoD + **BUILD-4** (now `npm run check && npm run build`).
      **OUT OF SCOPE (user, 2026-06-04):** axios, react-query (config-ui is load-edit-save, not a server-cache dashboard);
      OpenAPI **type generation** was folded into **UI-5** (generation-only), not here. Refs: stack comparison
      (journal 2026-06-04), `../wb-mqtt-bridge/ui/.eslintrc.cjs`.
- [x] **UI-7** [DEDITOR/I18N] (P2) — **DONE 2026-06-07.** config-ui is now fully bilingual (**ru + en**), adding more
      languages cheap. Adopted **`react-i18next`** (`i18next ^23` / `react-i18next ^13`, the bridge's declared versions —
      which only *declared* them, never wired them, so the setup is from scratch) under `src/i18n/`: namespaced TS
      bundles (`locales/{en,ru}/{common,layout,donations,configuration,prompts,templates,localizations,monitoring,overview}.ts`),
      a typed `t()` (CustomTypeOptions off the `en` bundle → mistyped keys are build errors + autocomplete), and a global
      **`LanguageSwitcher`** in the Header (persisted to localStorage, default `ru` / fallback `en`, `<html lang>` synced).
      **Completeness is compiler-enforced:** the RU bundle is typed `DeepStringify<typeof en>`, so any missing/extra/misnested
      RU key fails the build — the "language files are complete" guarantee, statically. **The two language axes stay
      orthogonal:** the UI-chrome language (switcher) is independent of the donation *content* language (`LanguageTabs`).
      Retrofitted **every** config-ui page + component (chrome, donation editor track incl. the §3.2 card vocabulary, and
      all 6 admin pages) via partitioned slices; the §3.2 card labels/help read naturally in both languages.
      Orphan guard hardened in passing (side-effect imports `import './i18n'` + `*.d.ts` exemption). DoD met:
      `npm run check` (type-check + lint 0-warn + orphan guard) + `npm run build` + `npm test` 40/40 all green. Conventions:
      `config-ui/docs/i18n_retrofit_spec.md`. Design: `config-ui/docs/donation_editor_ux.md` §7. Refs: UI-1/2/3/5.
- [x] **UI-8** (P3) — **DONE 2026-06-06.** Swept the config-ui orphans + added a guard so they can't reaccumulate.
      A reachability sweep from `src/main.tsx`/`App.tsx` (now following dynamic `import()` too) confirmed **5** modules
      unreachable with **zero** references anywhere (no dynamic/string/registry use): deleted
      `src/components/editors/{AudioOutputConfigSection,KeyValueOfStringArray,ObjectArrayEditor}.tsx`,
      `src/utils/testWorkflow.ts`, and — **decision on the borderline `src/utils/spacyAttributes.ts`** — removed it too:
      it's a 392-line spaCy attribute catalog that nothing imports; the live advanced editor uses a *different* helper
      (`spacyAttributeHelpers.ts`, kept) and UI-3's card vocabulary is survey-grounded, so UI-3 doesn't need it (git
      history preserves it if a richer attribute picker is ever wanted). **Guard added:** `scripts/find-orphans.mjs`
      (reachability check) + `check:orphans` script, **wired into `npm run check`** — the root cause was that
      `--max-warnings 0` can't see unused *exports*. DoD met: `npm run check` (type-check + lint + orphan guard) +
      `npm run build` pass; no unreachable non-`*.gen.*` modules remain. Refs: UI-5.
      A reachability analysis from the app entry (`src/main.tsx`/`App.tsx`) flagged modules unreachable yet present —
      the strict ESLint gate can't catch unused *exports* (`--max-warnings 0` only sees unused locals/imports). UI-5
      removed the v1.0 *donation* orphans; these remaining ones are **pre-existing and non-donation**, so they were left
      out of UI-5 scope: `src/components/editors/{AudioOutputConfigSection,KeyValueOfStringArray,ObjectArrayEditor}.tsx`
      + `src/utils/testWorkflow.ts`. **Verify each is genuinely dead** (no dynamic/lazy import, not referenced by a
      route/registry the static sweep can't see) before deleting. **Borderline — decide, don't auto-delete:**
      `src/utils/spacyAttributes.ts` (a spaCy attribute catalog) is currently unreferenced but may be reused by **UI-3**'s
      human-card pattern model — keep if UI-3 will consume it, else remove. Consider adding the reachability check as a
      lint/CI guard so orphans don't reaccumulate. DoD: `cd config-ui && npm run check && npm run build` pass; no
      unreachable non-`*.gen.*` modules remain (or each remaining one has a documented reason). Refs: UI-5.
- [x] **UI-9** [DEDITOR] (P2) — **DONE 2026-06-07.** Free-form dict (map) config fields now render an editable
      key/value table instead of a dead-end warning. **Root cause (verified end-to-end):** the backend schema
      generator maps any `Dict[str, X]` field to `type: "object"` (`config/auto_registry.py:329`) but only attaches
      `properties` for nested *Pydantic models* (`_extract_nested_object_schema`), so free-form maps like
      `domain_priorities` (`Dict[str, int]`) arrive with `type: "object"` and **no `properties`**. config-ui's
      `ConfigSection` only promotes object fields to a collapsible subsection when `type==='object' && properties`
      (`ConfigSection.tsx:262`); without `properties` the field fell through to `ConfigWidget`'s `case 'object'`, whose
      sole job was the yellow `objectFieldWarning` placeholder ("should be a collapsible section") — so **every**
      free-form map field showed the warning, not just `domain_priorities`. **Fix (config-ui only, no backend/contract
      change):** `ConfigWidget`'s `case 'object'` now branches on `schema.properties` — absent → render the existing
      `KeyValueEditor` (add/rename/delete entries with value coercion); present → keep the warning, since a *fixed-shape*
      object reaching the factory is a genuine routing bug worth surfacing. Single touch point because both render paths
      (simple-field `renderField` and direct widget calls) funnel through `ConfigWidget`. Reused the already-present
      `KeyValueEditor` (the deleted `KeyValueOfStringArray` from UI-8 was a different, string-array variant). DoD met:
      `cd config-ui && npm run check` (type-check + lint 0-warn + orphan guard) + `npm run build` green. Refs: UI-5/UI-8.
- [x] **UI-10** [DEPS] (P2) `[release]` — **DONE 2026-06-27.** config-ui major dependency upgrades clearing the 6
      Dependabot alerts the lockfile-only housekeeping couldn't (all needed breaking majors outside the declared
      ranges): `vite ^5`→`^8.1.0` + `@vitejs/plugin-react ^4`→`^6.0.3` (3 vite advisories + esbuild dev-server; vite 8
      uses the rolldown bundler), `react-syntax-highlighter ^15`→`^16.1.1` (prismjs DOM-clobbering — the only runtime
      one; `Prism` + prism style imports unchanged), `@typescript-eslint ^6`→`^8.62.0` + `eslint ^8.45`→`^8.57.1`
      (minimatch ReDoS in lint tooling — stayed on eslintrc, **no eslint-9 flat-config migration**). ts-eslint 8's
      stricter `recommended-type-checked` surfaced 6 lint errors: 5 unnecessary-type-assertions auto-fixed, 1 unused
      catch binding → optional-catch (`apiClient.ts`). Gate green: `npm run check` (type-check + lint + orphans) +
      `npm run build` + vitest 40/40; `npm audit` → **0 vulnerabilities**. `package.json` intent changed (deliberate
      version decision, per the `every-task-in-the-ledger` carve-out — vs. the 2 lockfile-only bumps done as housekeeping).
- [x] **UI-11** [UI] (P3) `[deferred]` — **DONE 2026-06-28.** config-ui type-contract drift in `src/types/api.ts`
      (review `config_ui_review.md` §B) — restores the type-check half of `config-ui-stays-functional`. Realigned the 4
      drifted types to the backend `CoreConfig` (verified against the generated `openapi.gen.ts` + `irene/config/
      models.py`): **(B1)** added `outputs: OutputConfig` + `trace: TraceConfig` to `CoreConfig` and defined those
      interfaces; **(B2)** added canonical `default_language`/`supported_languages` (QUAL-36), kept `language` as the
      deprecated legacy field; **(B3)** removed the phantom `default_language`/`supported_languages` from `NLUConfig`
      (they live on `CoreConfig`); **(B4)** rewrote `VADConfig` to the ARCH-18 shape (dropped ~10 phantom flat per-engine
      fields, added `default_provider` + `providers`). **Zero consumer churn** — grep confirmed no component read any
      drifted field (the editor renders from the backend schema), so the realign is pure type-accuracy. Gate
      (`config-ui-stays-functional`): `npm run check` + `npm run build` green. _Durable follow-up considered: the
      generated `openapi.gen.ts` is current but unused while hand-written `api.ts` is consumed — making `api.ts` derive
      from the generated schema would prevent recurrence, but that's a larger structural refactor (sub-interface
      consumers) left for a future call. `ajv`/`ajv-formats` remain unused deps (client validation is backend-delegated)._
- [x] **UI-12** [UI] (P3) `[deferred]` — **DONE 2026-06-28.** config-ui duplication consolidation (review §C). **The two
      genuinely-clean dedups done; C2–C5 assessed and declined as over-credited.** **C1** — the `apiClient` per-language
      CRUD quintet (donations/templates/prompts/localizations, ~250 dup lines) → 6 shared private helpers + thin typed
      wrappers; call sites/signatures/requests unchanged; 12 now-unused `*Request` imports removed (`123ce3b`). **C6** —
      the `CardPatternsEditor`/`ExtractionFillersEditor` controlled decompile→compile scaffold → `useDecompiledPatterns`
      hook (`99c1432`). Both type-proven & behavior-preserving; gate green. **C2–C5 assessed-divergent** (annotated in
      the review doc): the pages/editors are *same-concept, divergent-presentation*, not clones — C2's two pages diverge
      in ~10 (often intentional) behaviors; C3's list editors carry per-row conflict badges (Lemmas) / index+styling
      (Spacy) so they aren't faithful `ArrayOfStringsEditor` swaps; C4/C5's `TemplateKeyEditor` already uses
      `ArrayOfStringsEditor` and has read-only keys while `LocalizationKeyEditor` adds a type-switch + domain hints —
      merging would **change UX**, not dedup. Net: ~280 lines genuinely removed (C1+C6); the §C over-credit recorded so
      it isn't re-litigated. Two optional micro-consistency wins (Localization array → `ArrayOfStringsEditor`; object
      branches → `KeyValueEditor`) noted, not pursued (UX-touching, no meaningful dup). Decisions: C2 skip + C2–C5 close
      both user calls (2026-06-28). Gate (`config-ui-stays-functional`): `npm run check` + `npm run build` green.
- [x] **UI-13** [UI] (P3) `[deferred]` — **DONE 2026-06-28.** config-ui dead-code removal (review §D — unused *exports*,
      which ESLint's unused-locals rule can't see). Each verified 0 external refs before deleting; the gate (type-check)
      would catch a mis-call. Removed: `types/index.ts` 8 never-imported utility aliases (Maybe/Optional/RequiredKeys/
      ChangeHandler/ClickHandler/AsyncClickHandler/ApiMethod/LoadingState; kept `ConnectionStatus`); `types/components.ts`
      8 dead interfaces (TokenPatternsEditorProps, SlotPatternsEditorProps, HandlerListProps, ConfigSection+ConfigField,
      SearchFilters, BulkOperationResult, MonitoringData; 239→174 lines); `spacyAttributeHelpers.ts` `validateSpacyAttribute`;
      `safeStringify.ts` `wouldShowObjectObject`. **Plus folded in:** the 12 hand-written `*Request` types in `api.ts`
      that C1 (UI-12) orphaned (the same-named `openapi.gen.ts` schemas are separate/generated), and the unused
      `ajv`/`ajv-formats` deps (UI-11 §B finding — `npm uninstall`; not imported anywhere). Gate
      (`config-ui-stays-functional`): `npm run check` (type-check + lint + orphans) + `npm run build` green — confirming
      everything removed was truly dead.
- [x] **UI-14** [UI] (P3) `[deferred]` — **DONE 2026-06-28.** config-ui efficiency + hardcoded-list/altitude (review
      §E). **Efficiency (behavior-preserving, gate-green):** E1 derived `hasChanges` instead of the state-via-effect
      anti-pattern on both Templates/Prompts pages (removed the effect + the redundant `setHasChanges(false)` calls —
      verified each coincided with `data===original`); E2 `TomlPreview` debounce → `useRef` (no re-render per keystroke);
      E3 all 14 `JSON.parse(JSON.stringify)` deep-copies → `structuredClone`; E5 memoized LemmasEditor's nested-loop
      suggestion scan + per-row conflict map. **E4 skipped** (`performAnalysis` also runs from a manual path → threading
      `currentHash` risks a cache-key mismatch; minor perf, real risk). **Altitude:** E6 the `ContractEditor`
      PARAMETER_TYPES/ENTITY_TYPES/ROOM_CONTEXTS dropdowns now derive from `satisfies Record<Union,…>` keys, so a backend
      donation-enum change **fails the build** instead of silently dropping options (the review's drift concern, fixed at
      compile time since a TS union can't be enumerated at runtime). **E7/E9/E10 spun out as UI-16** — E7 (component
      roster) + E9 (widget heuristics) are **blocked on backend schema metadata** (no `is_component`/`widget` hint
      exists); E10 (spaCy-attr i18n) is niche/low-value. **E8 assessed non-issue** — `LanguageTabs` display names are
      inherently UI + degrade gracefully; the `['en','ru']` fallback is a defensible default. Gate
      (`config-ui-stays-functional`): `npm run check` + `npm run build` green. Like UI-12, the review's §E altitude items
      were partly over-credited (most need backend signals or are non-issues); the genuine config-ui wins (efficiency +
      E6 drift-guard) are done.
- [x] **UI-16** [UI] (P3) `[deferred]` — **DONE 2026-07-15 (sprint-02 port arc, the travel-with row —
      the backend-metadata blocker dissolved by building the metadata).** **config-ui schema-driven
      sections/widgets + the spaCy-attr E10 finding** (review §E, spun out of UI-14). **E7:** the sections
      endpoint (`/configuration/config/schema/sections`) now returns **`component_sections`** — section →
      live-testable component name, sourced from `CONFIGURABLE_COMPONENT_SECTIONS` in the configuration
      component (adjacent to the API identities it names; the `text_processor→text_processing` divergence
      lives there ONCE, guarded by a new test asserting every key is a real CoreConfig section + a
      ComponentConfig flag). `ConfigurationPage` + `ConfigSection` derive the Test/Workflow roster from it
      (`testableComponent` prop) — both frontend hardcoded rosters + remap tables DELETED. **E9:**
      `_extract_model_schema` propagates a **`widget`** hint from `json_schema_extra`; 23 hints declared
      (`provider_select` ×8 incl. the component-schema base, `input_select`, `microphone_select`,
      `readonly` ×2, `env_var` ×7, `audio_output_select` ×4 on the audio provider schemas) — chosen by a
      mechanical audit of every model field against the old frontend predicates; the `ConfigWidget`
      factory now dispatches on `schema.widget` and the name/path heuristic stack is DELETED (the runtime
      `${...}`-value env detection stays — values can be env refs on any string field). Deliberate
      non-preservations, recorded: `fallback_providers`/`provider_cascade_order` (List fields) no longer
      hit the single-value ProviderSelect — the old name-match would REPLACE the array with a string on
      edit (a latent shape-corruption path); they fall to the array editor. `provider_class`/`provider`
      (NLU internals) render as plain strings. **E10 narrowed at execution intake:** the 21 English
      attribute descriptions were **dead data** — no caller ever rendered them (the picker shows keys
      only) — so per `dead-code-remove-not-fix` the i18n bypass was removed by deleting them
      (`SPACY_ATTRIBUTE_SUGGESTIONS` keys-only list; attribute keys stay technical per
      `donation-choice-surfaces-rule`). **Contract note (owner question answered in-session):** the REST
      surface is the `ui-openapi` repo-internal contract — the hints DO reach the generated artifact via
      the component model schemas, an additive regeneration (widget keys + one docstring), NOT a breaking
      reshape → `dump_openapi.py` re-run + `gen:api-types` (+3 lines), **no STAMP bump** per the
      convention; drift guard green. **Verified:** backend suite **1417/7 skip** (CI-style from repo root
      — the first from-`backend/` run's 76 failures were cwd-relative asset resolution, reproduced
      identically WITHOUT the change), 2 new tests (roster coherence + hints-reach-payload incl. nested);
      config-ui check + plugin build + vitest 44/44. docs: none — internal schema plumbing; config-ui
      behavior described in manifest nodes (edit/test/persist flows) is unchanged.
- [x] **UI-17** [UI][COMMONS] `[deferred]` — **DONE 2026-07-15 (sprint-02 port arc; the PROD-24 write-back
      ID; HK-11 corrections applied at intake the same day).** **config-ui → the Voice Workbench plugin.**
      `src/plugin.tsx` default-exports the `WorkbenchPlugin` (contract types from
      `locveil-workbench/contract`, devDep `file:`): **6-page cut** (donations, templates, prompts,
      localizations, monitoring, configuration) — `OverviewPage`, `Header`, `Layout`, `Sidebar` and
      `LanguageSwitcher` DELETED (shell chrome owns nav/locale/theme; the retiring components' types,
      `layout`/`overview` i18n namespaces, and the router usage went with them — the 6 surviving pages are
      router-free); the **status slot** preserves the Header's visibility (`checkConnection` +
      `getIntentStatus` → level ok/error + RU/EN text with handler count, shell-polled); **i18n =
      plugin-local instance** following the shell's `PageProps.locale` signal (persistence + `<html lang>`
      dropped — chrome owns both; collision-free by construction since react-i18next bundles per-plugin).
      **Packaging (HK-11)**: vite **lib build** → `dist/index.js` (ESM, singleton set external — verified
      bare specifiers in dist), `style.css` (Tailwind **preflight off**, tokens shell-owned), build-emitted
      `manifest.json` fragment (peers `^18/^18/^6/^0.1` — passes the shell's strict check incl. the 0.x
      strict-minor rule); `npm run dev` = `vite build --watch` per the HK-11 dev loop; orphan-guard entry →
      `plugin.tsx`. **Intake decisions recorded:** (a) contract-as-code has NO `backendTarget` (IMPL-1
      simplified `PageProps` to `{locale}`) — voice keeps its own base-URL mechanism (same-host:8080 +
      `window.__IRENE_API_BASE__` override; the nginx runtime-injection file retired with the container);
      (b) voice has NO REST report-write surface (intake is the ARCH-30 spoken dialog) — `reportHook` is a
      minimal in-plugin handler naming the voice-first path, a real write endpoint stays PROD-4-auth-gated;
      (c) **the standalone container fate** (side-find routed here): RETIRED with the app — `Dockerfile` /
      `nginx.conf` / `docker-entrypoint.sh` / `public/runtime-config.js` deleted, the `publish-ui` CI job +
      `build_ui` dispatch input removed (`locveil-voice-ui` stops publishing; existing GHCR tags remain
      pullable but frozen); the WB7 deployment was never affected (compose carries no UI service).
      **`config-ui-stays-functional` DoD re-anchored to the plugin build in CLAUDE.md (same change, HK-11
      owner ruling q5).** Shell mount landed in commons `workbench.config.json` (two real plugins now).
      **Verified:** `npm run check` + plugin build + vitest 44/44 + docs-manifest 8/8; full HTTP loading
      path against the served shell (runtime-config → voice manifest → entry 200 → styles 200); dist carries
      the default export and zero `process.env`. Browser render remains the honest caveat (IMPL-1
      precedent) — one `npm run serve` away. docs: quickstart, install, guides/build-docker (+ the non-root
      `config-ui/README.md`, rewritten — it still described the pre-UI-13 AJV standalone).
- [x] **UI-18** [UI][COMMONS] `[deferred]` — **DONE 2026-07-15 (filed + completed same session; sprint-02
      port-arc split, "voice UI-18" foundation row).** **Kit-first foundation: eslint-9 flat + `ui-kit-v1`
      + the 9 hand-built primitives swapped onto kit primitives.** (a) **eslint-9 flat config**: eslint
      8.57→9, `.eslintrc.cjs` → `eslint.config.mjs` (`typescript-eslint` meta-package, react-hooks 5), rule
      set preserved verbatim incl. the type-aware tuning — verified live via `--print-config`
      (`no-floating-promises`/`no-misused-promises`/`await-thenable` all error); `--ext` dropped from the
      lint script (v9), lint scope unchanged (ts/tsx). (b) **`locveil-ui-kit` file: sibling dep** +
      `presets:[preset]` + kit-dist content glob + `tokens.css` at the entry — both themes in the bundle
      (`.dark` class strategy; the standalone app stays light until a toggle exists — shell-owned at UI-17).
      (c) All **9 primitives** (`src/components/ui/`) rebuilt on kit primitives with their local prop APIs
      intact (composites untouched — that's UI-19): Badge→StatusChip (default/success/warning/error/info →
      pristine/persisted/edited/conflict/tested; custom→kit Badge outline), Input/TextArea→kit
      Input/Textarea+Label (a11y improved: `useId` replaces label-text ids), Toggle→kit Checkbox,
      Section→Card+Icon (collapse kept), ConfigurationStatus→Alert+Icon, TestConfigButton +
      WorkflowActionButtons→kit Button (variant/size mapped; conflict pill→StatusChip),
      WorkflowStatusIndicator→StatusChip (the state enum IS the kit `StatusVariant` set). **Side-find
      fixed upstream: commons IMPL-3** — the kit's StatusChip built classes via a template literal, so
      Tailwind never generated the real recipes (chips unstyled in every consumer) and the extracted `${h}`
      pseudo-candidate broke lightningcss minification (this build failure found it); fixed in the kit
      (static per-variant class map), voice's build is the live verification. Intake reconciliation: the
      sprint's "ci.yml guard-version prose batches in" side-find was already fixed by BUILD-38 — nothing to
      batch. **Verified:** `npm run check` (tsc + eslint strict + orphans) green, `npm run build` green,
      vitest 44/44, all five chip recipes + both theme token sets present in the built CSS (checked at the
      generated-utility level), HTTP smoke over `vite preview` (app + hashed assets served; browser render
      is one `npm run dev` away — IMPL-1-style honest caveat). docs: none — visual restyle of internal
      primitives; no manifest node describes config-ui's appearance (QUICKSTART's config-ui section is
      functional and unchanged).

- [x] **UI-19** [UI][COMMONS] `[deferred]` — **DONE 2026-07-15 (sprint-02 port arc, the flagged
      largest-risk row — landed same-day as its foundation).** **Full port body: 35 composites + 6 pages
      onto `locveil-ui-kit` primitives + tokens.** Real size at execution intake: ~11.7k lines / **1051
      raw palette class instances → 0** (checked mechanically over the whole tree; the planning "~32k /
      7 pages" was inflated — Overview had retired at UI-17). Executed as five parallel agents over
      disjoint file sets against one normative brief distilled from the stylebook; every file re-gated.
      **Structural swaps:** ~60 raw buttons → kit `Button` (variant/size per role; destructive actions →
      `destructive`/`text-destructive`, icon-only → ghost icon); **12 native selects → radix `Select`**
      (static/clean value sets) with **9 kept native** and token-styled (all carry legitimate
      `value=""` placeholder/sentinel semantics radix forbids — ConfigWidgets ×4, spaCy editors ×2,
      microphone device picker, LanguageTabs ×2); view-mode switchers → kit `Tabs` ×3 (Prompt/Template/
      Localization editors); the hand-rolled fixed-overlay modal → kit `Dialog` (BlockingConflictsDialog);
      ~20 feedback boxes → kit `Alert` (destructive/accent/default; kit has no warning variant — warning
      icons carry the edited-hue recipe); fake pulse-div loaders → kit `Skeleton`; search/text controls →
      kit `Input`/`Textarea`; booleans → kit `Checkbox`, range → kit `Slider`. **Meaning:** status pills →
      the local Badge/StatusChip vocabulary; inline status text/icons use the full-literal token recipes
      (Tailwind-extractable — verified present in the shipped CSS, light + dark, all five hues); no `*-50`
      washes survive. Pattern-card editors, LanguageTabs chrome, Monaco/syntax panes stayed custom per
      stylebook §7 (tokens only). **Recorded deviations:** `window.confirm` ×3 + native `title=` stay
      (`ui-kit-v1` ships no Toast/AlertDialog — commons IMPL-4 → voice UI-21); the two `fixed bottom-0`
      action bars (ApplyChangesBar, Localizations save bar) stay token-styled in place — the shell's
      bottom action-bar slot exists in chrome but the plugin contract exposes no API for it yet (a
      workbench-vX contract surface, PROD-24 arc); dense-row micro-icons keep explicit small sizes
      (stylebook's banned pattern is `!`-overrides, none used). **Verified:** whole-tree palette grep = 0;
      `npm run check` (tsc + eslint strict + orphans) green; plugin build green (lightningcss clean);
      vitest 44/44; recipe utilities confirmed in `dist/style.css` both themes; shell HTTP smoke (manifest
      → entry → styles 200). Browser render = the standing honest caveat (owner's `npm run serve` away).
      docs: none — appearance-only restyle; no manifest node describes config-ui's look, and the
      UI-17-era run instructions are unchanged.
- [x] **UI-20** [UI] `[deferred]` — **DONE 2026-07-15 (the HK-11 write-back side-find).** **Monaco
      bundled locally — no CDN at runtime.** `monaco-editor` **0.53.0** added (0.55 pinned back: it
      depends on a dompurify with open advisories — 0.53 keeps the 0-vulns bar; read-only DiffEditor
      usage unaffected); `src/utils/monacoLoader.ts` points `@monaco-editor/react`'s loader at the
      bundled instance (`loader.config({ monaco })`) and inlines the editor worker as a blob
      (`?worker&inline` — no worker-asset path to break under the import-map load); both consumers
      (TomlPreview, DiffViewer) import it at module top, so config runs before any render. Monaco's own
      dynamic imports code-split the dist (lazy editor core ~3 MB + per-language chunks, ALL LOCAL,
      resolved relative to the entry — exactly the ESM mechanism the HK-11 runtime assembly serves);
      monaco css folded into `style.css`. **Honest residual:** the jsdelivr URL still appears ONCE in
      the bundle as `@monaco-editor/loader`'s inert default-config object — dead data on a branch the
      provided instance short-circuits; zero external requests at runtime. Verified: check + build +
      vitest 44/44; served-shell smoke (entry, lazy editor core, a language chunk, styles — all 200
      from the plugin mount). TOML stays plaintext in the diff view (monaco ships no TOML grammar —
      unchanged from the CDN build). docs: none — invisible when online, works offline now; no
      manifest node describes the editor's loading mechanics.
- [x] **UI-21** [UI][COMMONS] `[deferred]` — **DONE 2026-07-15 (same session as its ungating —
      commons IMPL-4 shipped Toast/AlertDialog as ui-kit 0.1.1/`ui-kit-v1.1`).** **Toast/AlertDialog/
      Tooltip adoption sweep.** `window.confirm` ×3 (all in `ApplyChangesBar`'s save flow) → one
      promise-shaped kit **AlertDialog** (`askConfirm()` resolves the dialog's Cancel/Save-anyway
      choice — identical control flow to the old blocking confirm; new `applyBar.confirmTitle`/
      `saveAnyway` keys, RU+EN). **45 native `title=` sites → kit `Tooltip`** across 28 files (agent
      sweep + owner-files pass): icon-only triggers keep their accessible name via `aria-label`;
      dynamic/conditional expressions moved verbatim; multi-line titles (TestConfigButton preview,
      ConflictBadge) render `whitespace-pre-line`; one `TooltipProvider` at the plugin page root.
      Remaining `title=` occurrences are React component props (Section headings), not native
      tooltips — audited. Toast itself: no call sites yet (nothing user-facing needed it — the kit bus
      is available for future use; adopting it for save-success feedback is deliberate UX work, not a
      sweep). docs: none — interaction affordance polish; no manifest node describes tooltip behavior.
- [x] **UI-22** [UI][COMMONS] `[deferred]` — **DONE 2026-07-15 (filed + completed same session;
      IMPL-5 first consumer).** **Both bottom bars render through the shell's ActionBar slot.**
      `ApplyChangesBar` and the LocalizationsPage save bar now render `<ActionBar>` children into the
      kit's HK-11-singleton bus; the shell's `ActionBarHost` (workbench-v1.1, normal flex flow) owns
      the border/surface shell — the local `fixed bottom-0 … z-50 shadow-lg` wrappers and the
      DonationsPage `pb-20` overlap hack are DELETED; zero `fixed bottom-0` remains in the plugin
      (stylebook §8 now holds). Single-occupancy is safe by construction (the two bars live on
      different pages; latest-wins covers any transition). Verified: check + plugin build + vitest
      44/44; served-shell smoke — the shell dist carries `wb-bottom-slot`/Toaster, the rebuilt plugin
      (peers `^0.1` ≙ kit 0.1.2 under the 0.x strict-minor rule) serves entry+styles 200 and imports
      ActionBar/AlertDialog/TooltipProvider through the import map. Browser render = the standing
      caveat. docs: none — layout mechanics; no manifest node describes the bar placement.
- [x] **UI-23** [UI][COMMONS] `[deferred]` — **DONE 2026-07-15 (filed + completed same session;
      IMPL-6 consumer adjustment — voice was BROKEN against the controller until this).** **apiClient
      follows the shell-declared backend (`PageProps.backends.api`).** IMPL-6 (workbench-v1.2, additive)
      finally delivers the PROD-24-promised per-plugin backend targets: deployment facts (WB7 IP + port)
      live in the owner-edited shell config and reach pages as `PageProps.backends`. Before this, voice's
      `page()` wrapper destructured only `{ locale }` and apiClient resolved via the retired-nginx-era
      chain (build-time injection global + same-hostname fallback) — under the shell, same-hostname is
      the SHELL origin, so every fetch hit the serve script instead of the WB7. Fix: `setBaseUrl()` on
      the singleton + the wrapper re-points it **synchronously during render** — deliberately NOT a
      `useEffect`: React runs child effects before parent effects, so an effect here would fire AFTER the
      page's mount-time data loads and the first fetches would still hit the shell origin. The old chain
      stays as the explicit no-backends-configured fallback (comments rewritten to say so). Known
      wrinkle, recorded: `status()` is shell-polled outside any page — its first poll on activation can
      race the first page render and use the fallback once; the base sticks after that (contract gap if
      it ever matters: backends don't reach the plugin object, only pages). Verified: check + build +
      vitest 44/44; served runtime-config carries `{"api": "http://192.168.1.50:8080"}` for the voice
      mount. docs: none — deployment wiring internals; QUICKSTART's "talks to :8080" story unchanged
      (same-host dev still works via the fallback).
### Release Readiness (REL)
- [x] **REL-1** (P0) `[release]` — **DONE 2026-07-04 (interactive session). Definition-of-release SIGNED OFF.**
      Decisions: **(1) release artifact** = version tag **+ first real GHCR publish** (backend
      `standalone-x86_64`/`embedded-aarch64`/`embedded-armv7` RU-at-minimum + config-ui image), boot-validated
      where hardware allows → filed **BUILD-11** (dispatch + boot-check + real size budgets; the Docker clause
      was unproven — no `workflow_dispatch` had ever run); **(2) explicit scope tags** on all previously
      untagged open tasks — ARCH-8, QUAL-18, DOC-8, REL-2, REL-3 all `[release]` (user kept QUAL-18 and DOC-8
      in scope); **(3) coverage criterion** replaced with the three named nets (unit suite + smoke e2e + eval
      `make cli`) — no coverage-%; **(4) target** = milestone "scope-complete" (release when every `[release]`
      task is `[x]`), no calendar date. Criteria reconciled against reality at sign-off: 6 of 8 already met and
      checked with evidence (uv sync/boots, CI green, pyright **0 errors** standard mode, 10 import-linter
      contracts, three nets green, live model URLs); remaining open: docs/quickstart (REL-2), config-ui
      functional pass + Docker boot (REL-3 + BUILD-11). Checklist rewritten in `RELEASE_PLAN.md` header.
- [x] **REL-2** (P1) `[release]` — **DONE 2026-07-06. The release-time config story, driven by live
      first-touch evidence** (the user's own bare-`irene-cli` stumble earlier the same day became the
      acceptance test). Shipped: **(1) `configs/config-example.toml`** — curated text-first starter
      (hybrid NLU only, no model downloads, no keys; web API alongside; smart_home enabled with the
      bridge off → honest «умный дом не подключён»; every disabled capability comments its upgrade-path
      section in config-master) — boots + answers live («который час» → the time), passes the CI config
      gate (13/13 valid); **(2) the friendly no-config failure** — `requires_config_file=True` for the
      CLI + WebAPI runners (voice already had it): bare and `--headless` invocations now print "No
      configuration found … -c configs/config-example.toml … IRENE_CONFIG_FILE … QUICKSTART" instead of
      leaking component internals (the silent default-config fall-back could never work — empty NLU
      provider list); Docker unaffected (images bake `IRENE_CONFIG_FILE`); **(3) README** — stale status
      paragraph corrected (smart-home built, GHCR images real) + first-run one-liner; **(4) QUICKSTART
      finalized** — example-config-first flow, console-script invocations, smart-home moved from
      "not implemented" to in-scope-with-bridge, GHCR images noted, test count refreshed.
      Suite 1300, config gate 13/13, pyright 0.
- [x] **REL-3** (P1) `[release]` — **DONE 2026-07-06 (bar the tag ceremony). Version / changelog /
      functional pass.** Version **held at 15.0.0 for the entire release** (user 2026-07-06 — the bump rides
      the NEXT release, not this one), so the 'bump' is a confirmed no-op. `CHANGELOG.md` authored (the
      revival release — architecture / understanding / capabilities / operations) + README-linked. config-ui
      MANUAL functional pass PASSED against the running backend (the exit-criterion's human check) —
      sections incl. the new `reports`, donations, templates, localizations, ru/en switch, monitoring all
      live — and it earned its keep by catching **BUG-29** (default `web_port` 6000 was X11 / browser-blocked;
      swept to 8080). **The `git tag v15.0.0` is deliberately NOT created here:** the release artifact requires
      ARM boot validation (ARCH-25) and a clean `check_scope.py` (every `[release]` task `[x]`), so the tag is
      the FINAL release act, cut when ARCH-25 closes. REL-3's own deliverables (version decision, changelog,
      functional pass) are complete.

- [x] **REL-4** [REL] `[release]` — **DONE 2026-07-09.** Version renumbered `15.0.0` → **`0.5.0`**. The old number
      asserted fourteen prior major releases of this codebase; the only tags this repo ever carried are `8.1`
      (inherited 2023 upstream history) and `v12-final`. Owner's scheme: major `0` = the public API is not frozen
      (BUILD-21/22/23 will rename the package and extract the loader/logging), minor `5` = the fifth design
      generation — which fits 0.x semver exactly, since under 0.x the minor *is* the breaking axis. The "15th
      iteration overall" lineage fact moved to prose (CHANGELOG + `__version__.py`), because in the patch field it
      would collide with the only job patch has and be destroyed by the first bugfix.
      `irene/__version__.py` is the single source; `pyproject` (`attr`), FastAPI `info.version`, `/health` and
      `CoreConfig.version` all derive from it. `MAJOR_VERSION` — which never meant "package major", it printed
      `V15 Components`, i.e. the *architecture generation* — became an explicit `ARCH_GENERATION = 5`, no longer
      derived from the version (the log now reads `V5 Components`). **Deleted the `version = "15.0.0"` line from
      all 13 configs**: `CoreConfig.version` already defaults to `__version__`, so they were unvalidated copies
      that could only drift — and `configs/config-example.md` proved the point, still carrying `14.0.0`, a whole
      major behind. `config-master.toml` keeps a comment explaining the omission instead of a value.
      Regenerating `config-ui/openapi.json` also revealed it was **stale**: four schemas (`BridgeOutputConfig`,
      `ReportsConfig`, `SatelliteConfig`, `SatelliteTLSConfig`) had been added to the API and never re-dumped;
      nothing in CI regenerates it (filed as BUILD-26). Cross-repo cost was **zero** — the bridge never reads our
      version and eval-commons stamps only `bridge_version`; the one stale claim, D-11's "voice 15.x", was
      corrected in `productization.md`. Verified live: `/health` → `"version":"0.5.0"`, `openapi.info.version` =
      `0.5.0`, startup logs `V5 Components`, all 14 configs parse and inherit the version. pyright 0,
      import-linter 11/11, 1358 tests pass, `config-ui` check + build green.
