# Irene — Release Journal

The **single** chronological log for the release effort ("what happened, when, and why"). Append-only;
newest entries near the top of each dated section.

- **This file holds NO task status and NO scope.** The authoritative task ledger (scope + status) is
  [`RELEASE_PLAN.md`](./RELEASE_PLAN.md); findings/rationale live in `docs/review/*` + `docs/design/*`.
- Entries reference task IDs (e.g. `QUAL-27`) but never assert their status — check the ledger for that.

---

## Action journal

### 2026-06-01
- **ARCH-0** — Architecture map + doc-harmonization audit + pattern review. → `docs/review/phase1_architecture_map.md`.
  Key results: module-level graph shows only **2 real cycles** (Phase-0's "giant SCC" was a package-grouping
  artifact); the #1 defect is the `intents/models.py` god-module (in-degree 67) forcing most backwards edges;
  `architecture.md` body is stale below its banner (fictional managers/endpoints/runners, TODO-vs-DONE);
  real data flow differs from docs (VAD is a segment-gate, NLU==Intent-Recognition, TTS text-path-only).
- **Goal 2 decision:** **Hexagonal (Ports & Adapters)** SIGNED OFF. Refined ARCH-1..6 + DOC-4/5/6.
- **DOC-6** — archived 5 stale plan docs (config_schemas, language_support, configuration_guide,
  PIPELINE_IMPLEMENTATION, irene_current) → `docs/archive/`.
- **DOC-5** — harmonized the contradicts-code docs (donation paths/schema, asset TOML nesting, train env
  prefix, voice_trigger YAML→TOML) + correction banners on the donation spec and universal_tts. Found a
  config-master train-schedule nesting bug → QUAL-7. Donation-spec full rewrite deferred → DOC-5b.
- **Macro-task intake (9 threads)** — analyzed and split into workstreams:
  1. [FAF] fire-and-forget review → QUAL-8/9, TEST-3, DOC-4 note.
  2. [PEX] parameter extraction → QUAL-10/11, TEST-4, DOC-7.
  3. config-ui-stays-functional → **Invariant #4** + DoR checkbox + BUILD-4→P1 ongoing gate.
  4. [DEDITOR] human-friendly donations editor → **new UI workstream** UI-1/2/3.
  5. [TXTPROC] text-processor review → QUAL-12/13, TEST-5.
  6. [LLM]/[PROMPTS] LLM usage + offline-first + prompt hardening → QUAL-14/15/16.
  7. [MQTT] smart-home output → ARCH-7 (design session) / ARCH-8; surfaces the missing output-port seam.
  8. [STREAMAPI] streaming-API exposure (hand-rolled AsyncAPI 2.6.0) → QUAL-17/18 (P2, must-before-release).
  9. [ESP32] ESP32 + wakeword (microWakeWord placeholder, training removed, TODO11 open) → QUAL-19/20 (keep/fix/cut).
  Cross-cutting sequencing: **QUAL-10 [PEX]** gates DOC-7 + UI-1/2/3; the reviews (QUAL-8/10/12/14) precede their
  refactors and **ARCH-1** (context split); Invariant #4 gates the contract-touching tasks; QUAL-12↔ASSET-3.
- **Invariant #5** added (review docs stay in sync) + a **Review-documents index** linking the plan to
  `docs/review/*` + `docs/design/*`. Completing a finding-derived task includes updating its review doc.
- **VOSK model re-audit (ASSET follow-up to ASSET-1).** Bumped VOSK **TTS** model `tts-ru-0.8-multi` →
  **`0.9-multi`** (latest; `1.0` is 404; size note 500MB→780MB). → `34f8e71`. Fixed a latent **ASR** bug: `en_us`
  pointed at the **full 1.8GB** `en-us-0.22` while labeled "42MB" under a "small models" comment → repointed to
  `vosk-model-small-en-us-0.15.zip` (40MB, verified live); full model kept under the `en` key (label corrected). → `a5189b6`.
  ASR versions otherwise already latest for the vosk runtime (small-ru-0.22, ru-0.42, de-0.21, es-0.42, fr-0.22).
- **Key discovery → motivates ARCH-9 [INFER].** The "newer" RU models on alphacephei (`ru-0.54`, `small-ru-0.52`)
  are **NOT vosk-runtime models** — empirically loading `small-ru-0.52` with our `vosk 0.3.45` fails
  (`model.cc:122 does not contain model files`); the dir is `encoder/decoder/joiner.int8.onnx` + `decode.py`
  importing `sherpa_onnx`. They are **sherpa-onnx Zipformer2** models needing a different runtime. So **do NOT
  bump the vosk URLs to 0.5x** (would break ASR) — but this surfaced that sherpa-onnx unifies ASR/TTS/wakeword/VAD
  on one ONNX runtime we **already ship transitively** (onnxruntime 1.22.1 via openwakeword + vosk-tts). Logged as
  **ARCH-9/10 [INFER]** (broad design session) with the constraint that whisper & silero remain first-class.

- **BUILD-1 DONE** (`bab6f97`). First actual run of the system post-revival. `uv sync --extra all` resolves/
  installs clean (353 pkgs; torch 2.7.1, vosk 0.3.45, spaCy, whisper, lingua-franca git dep all OK). `irene-cli
  --check-deps` → 5/5 components available. **WebAPI**: `irene-webapi` boots to uvicorn (workflow READY, 10
  routers, 104 OpenAPI paths); `POST /execute/command {"command":"привет"}` → 200 `greeting.hello` conf 1.0,
  real RU response — full spaCy-NLU→intent→handler chain works; graceful SIGINT shutdown clean. **CLI**: boots +
  shuts down clean; **bug found & fixed** — `--headless` set `nlu=False/text_processor=False` but the unified
  workflow requires `nlu` ("Required component 'nlu' not available"), so headless could boot but never execute a
  command; now enables nlu+text_processor (llm optional) and `--headless --command "привет"` returns a greeting.
  Cosmetics noted: QUAL-6 schema warning prints on every boot; CLI `--help` banner still says "v14" → folded into
  DOC-3. Not yet covered: Docker boot (BUILD-3), interactive REPL, audio/voice path (needs devices + models).

- **TEST-1 DONE / TEST-2 DOING** — first test-suite run post-revival. Added `[tool.pytest.ini_options]`
  (`asyncio_mode=auto` — unblocked ~23 async tests that errored as "not natively supported"; testpaths; silenced
  Pydantic V1 deprecation flood). Fixed broken refs: `ConversationContext`→`UnifiedConversationContext`,
  `Intent.text`→`raw_text`, `ComponentConfig.audio_output`→`audio`; skipped deleted-subsystem tests (TTLCache /
  perf-manager / removed `_handle_sample_rate_mismatch` seam, 13 skipped) with reasons; fixed a hardcoded
  `cwd='/home/.../Irene-Voice-Assistant'` test bug. Suite **100 failed→68 failed, 136→156 passed**. Commits
  `…`(asyncio+rename), `…`(skips+cwd), `…`(audio_output/Intent). **Prod bug surfaced → QUAL-21** (settings_runner
  + examples use removed ComponentConfig fields audio_output/microphone/web_api → would crash). Remaining 68 drift
  failures tracked in TEST-2; **TEST-6** added (rewrite ASR-fallback tests).

- **Strategy decision — stop repairing tests; rewrite post-ARCH/review; Docker last.** The TEST-1/2 pass took the
  suite from 136/100 to 166/56/13/2xf and banked the real value (it runs; found QUAL-21, QUAL-22, a trace-metadata
  fix). Continuing to fix the remaining 56 is throwaway work — those tests target pre-refactor code that ARCH-1..5
  + the QUAL reviews will invalidate. So **TEST-2 PAUSED** (partial safety net, remaining failures intentionally
  unfixed), and the real effort is **TEST-7: rewrite the suite once architecture + reviews land** (TEST-3/4/5/6
  folded in as coverage goals). **BUILD-3 (Docker) DEFERRED to the release phase** — image/extras/armv7 depend on
  the post-refactor shape (incl. ARCH-9/10 [INFER], QUAL-19/20 [ESP32]). Net active path now: **reviews +
  architecture**, then test rewrite, then Docker + release.

- **QUAL-10 [PEX] DONE** → `docs/review/parameter_extraction_review.md` (4-layer parallel deep-read + synthesis;
  6×P0/11×P1/12×P2). Headline: donation-driven extraction is largely aspirational — `slot_patterns`/`token_patterns`/
  `ParameterSpec.extraction_patterns` are validated-then-discarded **dead code**; spaCy param-extraction self-labels a
  "Phase-2 stub"; required-param errors never raise; the two providers extract with **divergent contracts**; entity
  resolvers **fatally crash** on asset-loader timing while the rest silently no-ops; and the **default
  `provider_cascade_order` names providers that don't exist** (only shipped configs setting it explicitly avoid total
  failure). Remediation ranked into **QUAL-11** (P0s first); confirms+absorbs **QUAL-22**; informs DOC-7, UI-1/2/3,
  TEST-4. Also explains the parked `test_cascading_nlu` failures (`_recognition_provider` vs bare `provider`).

- **QUAL-14 [LLM] DONE** → `docs/review/llm_usage_review.md` (3-layer parallel deep-read; 3×P0/9×P1/12×P2).
  **NLU confirmed LLM-free.** Headline: offline-first works for recognized intents, but the LLM stage's offline
  fallback is **fictional** — the `console` LLM provider doesn't exist (verified: no `console.py`, no entry-point),
  `fallback_providers` is never used at runtime (uses arbitrary `keys()[0]`), and `generate_response` re-raises
  offline; only the conversation handler's independent `is_available()` template-gate saves the pipeline. Also: ASR
  LLM-enhancement is dead code (`universal_llm` plugin lookup that returns None), `enhance_text` masks failures as
  success (failed translation returns untranslated input), prompts are triplicated inline + provider-language-locked
  (→ QUAL-16). **NLU-LLM decision: keep NLU deterministic/offline; LLM assist only opt-in + LOCAL, gated on
  ARCH-9/10 [INFER] + QUAL-11.** Remediation → QUAL-15.

- **QUAL-12 [TXTPROC] DONE** → `docs/review/text_processing_review.md` (3-layer parallel deep-read; 5×P0/6×P1/6×P2).
  Verdict: the subsystem is **decorative** — `process()` is hardcoded to stage `"general"` (verified), so only
  `general_text_processor` runs; `asr_output`/`tts_input` stages are never routed; **TTS gets raw text** (no call
  site — verified); the `[text_processor.normalizers.*]` config tree is dead; the WebAPI 500s on an unassigned
  `self.processor`; `number_text_processor` is a redundant unreachable dup of `asr_text_processor`. Recommendation →
  QUAL-13 **collapse to one config-driven processor + actually wire the two real stages**. **Added question
  answered:** LLM *can* back a text-processor (open interface + DI) but isn't wired (only the dead `universal_llm`
  path); should be **opt-in online-only**, augmenting the deterministic default, never on the default path. Surfaced
  a 3rd instance of the systemic **"configured names that don't resolve"** bug (dead stages here; phantom `console`
  LLM in QUAL-14; phantom cascade names in QUAL-10) → a shared startup-assertion fix.

- **QUAL-8 [FAF] DONE** → `docs/review/fire_and_forget_review.md` (3-layer parallel deep-read; 5×P0/8×P1/6×P2).
  **F&F is broken end-to-end** (verified): **timers crash on launch** (duplicate `session_id` kwarg → TypeError, only
  ValueError caught); the **domain-vs-action_name key mismatch** makes `remove_completed_action` always miss →
  `active_actions` leaks unbounded and completion/metrics/notifications (all nested in the failing `if remove...`
  block) never fire; completion callbacks call the **non-existent `get_or_create_context`**. Re-validated the 6
  legacy issues (1 FIXED, 1 fixed-but-moot, 2 changed-still-broken, 1 unreachable, 1 confirmed) — the Sep-2025 doc's
  "COMPLETED" is false (banner added). Remediation → **QUAL-9** (P0s first), then TEST-3. **This is the 4th
  "plumbed-but-dead" subsystem** (with QUAL-10/12/14) — a cross-cutting wire-up integration test + startup
  assertions would catch the whole class. **Review wave (QUAL-8/10/12/14) COMPLETE** — ARCH refactors unblocked.

- **Sequencing decided + encoded** (new "Sequencing" section). Review-wave P0s split into *surgical bug fixes*
  (architecture-independent) vs *refactor-flavored* (subsystem architecture work). Phasing: **Gate 0** = TEST-0
  (smoke net) + QUAL-23 (startup name-resolution assertion) → **Gate 1** = ARCH-1→2→4→5 (+DOC-4) → **Gate 2** = P0s
  by type (bug P0s ride the smoke net; refactor P0s ride the ports). Added **TEST-0** (P0, refactor safety net,
  distinct from the TEST-7 rewrite) and **QUAL-23** (P1, the cross-cutting fix for the 4×-observed
  "configured-name-doesn't-resolve" class). Rationale: no test net exists today + ARCH-1/2 move code, so a thin
  smoke harness gates the structural work; the name-resolution assertion is the cheap guard that catches most P0
  classes at once.

- **QUAL-23 DONE** (Gate 0 complete) → `irene/core/startup_validation.py` + wired in `core/components.py` +
  `irene/tests/test_startup_validation.py` (4✓). Startup assertion: every configured provider name
  (default/fallback/cascade + enabled provider blocks) must resolve to a registered entry-point. Non-fatal ERROR by
  default; `IRENE_STARTUP_STRICT=1` raises. On config-master it flags exactly the phantom `console` LLM (QUAL-15),
  zero false positives. TEST-0 still green. **Gate 0 (TEST-0 + QUAL-23) is now complete → Gate 1 (ARCH-1/2/4/5)
  unblocked.** Per Invariant #5, synced llm_usage/parameter_extraction/text_processing review docs (each now notes
  the startup guard; QUAL-15 not *done* until the startup ERROR clears).

- **ARCH-1 DONE** (`cdf8a81` + `a996dba`) — split the `intents/models.py` god-module (in-degree 67). IO primitives
  → `utils/audio_data.py` (dropped the `audio_helpers` TYPE_CHECKING band-aid); context types →
  `intents/context_models.py`; 45 importers re-pointed. **User-directed clean solution: NO TYPE_CHECKING** — context
  stays in the `intents` domain package (peer of `Intent`) with a real one-directional sideways import, so no cycle
  and no band-aid (deviates from the review's `core/` sketch, which would have inverted the dep). Verified: no
  cycle, full suite unchanged (176/55, zero regression), TEST-0 green. Per Invariant #5, synced
  `phase1_architecture_map.md` with the placement rationale. **Gate 1 underway: ARCH-2 next.**

- **ARCH-2 DONE** (`59f4ae8` + `044ff62`) — broke SCC-1 (config↔core / config↔components). validator→dynamic_loader
  (config→utils), schema-extraction cluster moved into AutoSchemaRegistry (auto_registry imports no component),
  import-time schema-validation side effect removed (no more "Schema warning" spam; runs once in load_config), and
  the `core/assets.py` AssetConfig TYPE_CHECKING band-aid dropped (clean downward import). config now has no upward
  imports. Verified: no cycle, full suite unchanged (176/55, zero regression). Per Invariant #5, synced
  `phase1_architecture_map.md` §2.1 (SCC-1 resolved). **Gate 1: ARCH-1 ✓, ARCH-2 ✓ — ARCH-3 next.**

- **ARCH-3 DONE** (`03fc44b`) — stop components importing delivery/tooling. Moved `web_api/asyncapi.py` →
  `api/asyncapi.py` (rank-0 port) so asr/tts components stop importing `web_api`; verified `analysis` is a clean
  driven adapter wrapped by `nlu_analysis_component` (classification for the ARCH-5 linter, no code change).
  Verified: full suite unchanged (176/55), TEST-0 green. Per Invariant #5, synced `phase1_architecture_map.md` §2.3.
  **Gate 1: ARCH-1 ✓, ARCH-2 ✓, ARCH-3 ✓ — ARCH-4 (formalize ports) → ARCH-5 (import-linter) next.**

### 2026-06-02
- **QUAL-29 Stage D — extraction surface→canonical normalization. Smoke green.** Added
  `ParameterSpec.surface_to_canonical()` ({surface_lower: canonical}, all languages; canonical maps to itself).
  Rewrote the 4 CHOICE consumption spots — `hybrid_keyword_matcher` (fuzzy) + `spacy_provider` (similarity), both
  match + validate — to match against the SURFACE forms and **emit the canonical token**, normalizing any surface to
  canonical before validation. Threaded `choice_surfaces`/`entity_type` through the spaCy param-spec serialize/restore
  cache (else a cache round-trip dropped them). Now the handler always receives the language-neutral value regardless
  of spoken language — verified: `"доброе утро"`→`morning`, `"вечером"`→`evening`, `"good morning"`→`morning`. This
  activates the canonical model and centralizes the RU→EN normalization that handlers like `provider_control` did
  by hand. Remaining (QUAL-29): validator shrink, v1.1 JSON schemas, config-ui, dead-param handler-wiring follow-ups.
- **QUAL-29 backend Stages A–C — model + migration + loader (v1.0→v1.1 split). Smoke green.** (1) **Model**
  (`donations.py`): added `EntityType`/`RoomContext` enums, `ParameterSpec.entity_type` (default generic) +
  `choice_surfaces` ({canonical: [surfaces]}), `MethodDonation.room_context` (default none); `choices` redefined as the
  **canonical** (language-neutral) token list; schema_version → `1.1`. (2) **Migration** (`scripts/migrate_donations_v11.py`):
  split all 14 handlers into `<handler>/contract.json` (neutral core) + `<handler>/{en,ru}.json` (phrasing); encodes the
  5 CHOICE cases + auto-derives the 6 clean-parallel surface maps; **fixed 2 latent data bugs** — ru `handler_domain`
  localised to Cyrillic (`таймер`/`случайно` → canonical ASCII) and the divergent CHOICE sets per the recorded
  decisions. (3) **Loader** (`intent_asset_loader.py`): `_load_language_separated_donations` now loads contract+lang as
  raw JSON and `_assemble_v11_donation` merges them — neutral core from the contract, phrasing **accumulated across
  languages** (phrases/lemmas/token_patterns/extraction_patterns/aliases/examples — **fixes the old
  first-language-wins drop** where ru patterns were silently discarded), `choice_surfaces` assembled as
  {canonical: [canonical]+all-language-surfaces} so the canonical token is always self-matchable. `convert_to_keyword_
  donations` threads `entity_type`/`choice_surfaces` to the NLU. Verified: all 14 handlers assemble valid donations;
  greetings `time_of_day` → `{morning:[morning,утро],…}`; translation `target_language` → free entity. **Remaining
  (this task):** extraction surface→canonical normalization (hybrid + spacy), validator shrink, v1.1 JSON schemas,
  config-ui (types/AJV/editors), + follow-up tasks for the dead-param handler wiring (datetime.format, system.info_type).
- **QUAL-29 STARTED — donation format split; 4 design decisions locked with user (Invariant #5/#8 reconciliation).**
  Verified the task is valid as written: the language-neutral `ParameterSpec` core (`name`/`type`/`required`/`choices`/
  `min_value`/`max_value`) IS physically duplicated across `<handler>/en.json` + `ru.json` (28 files, 14 handlers), and
  is **already diverging** (e.g. `timer.set` `message.default_value` is absent in en but `"Таймер завершён!"` in ru).
  The loader's `_merge_language_donations` silently takes params/`token_patterns`/`slot_patterns` from whichever
  language iterates first — a latent "first-language-wins" bug. **Decisions:** (1) **Layout** =
  `<handler>/contract.json` (neutral) + `<handler>/{en,ru}.json` (phrasing), joined by `method_name#intent_suffix` +
  param `name`. (2) **Tie-break = Russian wins** on any en/ru divergence in a neutral field (primary language; also
  resolves the first-wins bug deterministically). (3) **`default_value` is per-language** (language-specific default
  text is real; canonical defaults repeat harmlessly). (4) **Scope change — heuristic deletion moved QUAL-29 → QUAL-11.**
  `entity_resolver._is_device_entity`/`_is_location_entity` are LIVE (`nlu_component.py:38/62`), and their
  entity_type-driven replacement is the Q7b typed accessor (QUAL-11). QUAL-29 only ADDS the `entity_type` (default
  `generic`) + `room_context` (default `none`) declarations; QUAL-11 swaps the resolver atomically. QUAL-29 stays
  first (it provides the contract QUAL-11 consumes — confirmed the dependency direction with the user). Field
  partition (neutral vs per-language) mapped from the timer donation: neutral = intent_name_patterns, action_domain_
  priority, method name/suffix/boost/room_context, param name/type/required/choices/min/max/pattern/entity_type;
  per-language = phrases/lemmas/token_patterns/slot_patterns/negative_patterns/stop_command_patterns/action_patterns/
  examples + per-param description/extraction_patterns/aliases/default_value.
- **QUAL-28 Stage 4 — history windowing; one list, one writer, one method. QUAL-28 now fully DONE (all 4 stages).**
  The dataflow review's P1-q (conversation turn modeled 2–3× per request) traced to three writers over two parallel
  lists: the orchestrator's `add_user_turn`+`add_assistant_turn` (`orchestrator.py:297-298`, which also wrote
  `conversation_history` via `add_to_history`) **and** the workflow's `add_to_history` (`voice_assistant.py:411`) — so
  every turn was recorded twice, and `history` vs `conversation_history` were redundant copies. Collapsed to a single
  model: **(1)** deleted the legacy `history` field + `__post_init__` copy; **(2)** replaced `add_to_history` with the
  one canonical writer **`record_turn(user_text, response, intent)`**, called **once** at the workflow level (the only
  `orchestrator.execute` caller is `voice_assistant`, immediately followed by `record_turn` — verified no other
  intent-processing path needs its own write); **(3)** removed the orchestrator's parallel turn-write; **(4)** wired
  **`max_history_turns`** — `record_turn` and the LLM-history-restore now trim to the configured window instead of a
  hardcoded `[-10:]` (kills the P2 "config-that-lies": the field existed but was ignored). Deleted the now-dead
  `add_user_turn`/`add_assistant_turn`/`_trim_history`/`get_recent_context` on the context, plus **5 dead
  `ContextManager` methods** (`add_user_turn`/`add_assistant_turn`/`get_conversation_history`/
  `process_intent_with_context`/`update_context_with_result` — all confirmed zero-caller repo-wide) and the now-unused
  `Intent`/`IntentResult` imports in `context_models.py` + `context.py`. Stat readers (`context.py` ×2, `system.py` ×2)
  repointed `.history` → `.conversation_history`. _Boundary note:_ `max_history_turns` is settable via
  `ContextManager(max_history_turns=…)`/`.configure()`, but is **not** yet a `config-master.toml` key — exposing it as
  config is a config-ui-gated change (Invariant #4), out of this stage's "make the field functional" scope. Smoke + 10
  store tests + import contracts green; scope guard clean.
- **Invariant #9 added — no `TYPE_CHECKING` import guards (+ QUAL-32 to sweep the residue).** User flagged
   `TYPE_CHECKING` as a no-go for this project: it's a band-aid for an import cycle, and a cycle violates the
   inward-pointing hexagon (Invariant #3) — fix the cycle, don't hide it from the runtime; and hard deps like
   `pydantic` are never optional so guarding them is pure ceremony. Codified as **Invariant #9**. Cleared the two
   files in this session's touch surface: `conversation.py` + `timer.py` both guarded `from pydantic import BaseModel`
   (used only in `get_config_schema(cls) -> Type[BaseModel]`) — hoisted to a plain top import, de-stringized the
   annotation; both schemas still resolve (`ConversationHandlerConfig` / `TimerHandlerConfig`). Filed **QUAL-32** for
   the ~13 remaining files repo-wide. Smoke + store + contracts green.
- **QUAL-28 Stage 3b — retired the `ContextLayer` indirection; conversation handler consumes context directly.**
  Invariant #8 caught the map-agent's claim that `ContextLayer` was already dead — a grep showed it was *live*,
  used only inside `conversation.py` via `resolve_layered_context`/`get_contextual_summary`. So the scope became
  migrate-then-retire (not "already gone"). Rewrote the conversation handler's context **consumption** to use direct
  model accessors (`room_name`/`available_devices`/`get_thread_summary`/`active_actions`/`recent_actions`/
  `conversation_history`/`state_context`) instead of the layered-resolution dict-walking: `_build_progressive_context_
  summary` + `_get_context_coordination_summary` rewritten, `_summarize_context_layer` deleted, `context_layers_used`
  now counts present slices via a `sum([...])`. Then deleted the now-unreferenced machinery from `context_models.py`:
  the `ContextLayer` enum + `resolve_context`/`_resolve_session_context`/`_resolve_thread_context`/`_resolve_action_
  context`/`_resolve_intent_context`/`resolve_layered_context`/`get_contextual_summary` (~115 lines). Note: only the
  context *assembly* moved here — the LLM prompt/provider logic stays in QUAL-15/16. Smoke + 10 store tests +
  import contracts green; scope guard clean.
- **QUAL-28 Stage 3.3 — completed the field split properly (correcting the earlier "subsumed" overstatement).** On
  challenge, re-audited the context fields: the lifetime-critical `active_actions` relocation was done, but
  `recent_actions`/`failed_actions`/`action_error_count` were **still on the transient context** (died on eviction,
  contra the Q3 action-store design) and a dead `memory_management` config blob (for the deleted MemoryManager)
  remained. Both now fixed: **(a)** the completed-action history moved into the `ClientRegistry` store
  (per-`physical_id`, capped 10 recent / 20 failed; recorded once by the F&F done-callback — the single completion
  chokepoint), exposed on the context as read-only properties — so it **survives session eviction** (new test:
  history visible to a freshly-recreated context for the same scope). **(b)** the dead `memory_management` field
  deleted (no consumers). `remove_completed_action` simplified to active-store removal only (no double-counting).
  Now ALL F&F state (active + history) is in the long-lived store; the context is the transient session with views.
  10 store tests + smoke + contracts green.
- **QUAL-28 Stage 3.3 — context field split assessed as SUBSUMED (Invariant #8).** _[Superseded by the entry above —
  the assessment was an overstatement; recent/failed-action history and the dead memory_management blob were genuine
  residuals, now fixed.]_ The Q2 goal (long-lived
  physical-identity store vs short-lived conversation session) is achieved by the store-relocation: `active_actions`
  (the state that must outlive the conversation) now lives in the `ClientRegistry` store and survives session
  eviction. The residual identity fields on the context (`client_id`/`room_name`/`available_devices`/`language`) are
  request-hydrated each turn — not long-lived state needing a separate store (ARCH-6 populates them into
  `ClientRegistry`). The conversation session (history/state) stays on the now-transient, idle-evicted context. A
  formal dataclass split would be cosmetic field-grouping with no behavior change and real risk (35-importer surface),
  so it's **not done** as a separate refactor. **3.3 substantively complete** (resolver physical_id · kill
  extract_room · eviction-unify · non-creating-get · field-split subsumed). Remaining QUAL-28: 3b (conversation
  context-assembly + retire ContextLayer) + 4 (history windowing).
- **QUAL-28 Stage 3.3 — non-creating `get` split.** `get_context` is now non-creating (returns the existing,
  non-expired context or `None`, no side effects) so a blank/typo'd session id can't silently spawn a shared session;
  `get_or_create_context` is the canonical (and only) creator. Migrated all 11 callers that need a context to
  `get_or_create_context` (the 9 internal context.py mutators + the text-processor and /nlu API endpoints, whose
  "NO CREATION" comments were aspirational — the old `get_context` always created). Imports + contracts + smoke +
  store tests green (15 passed).
- **QUAL-28 Stage 3.3 — kill `extract_room_from_session` + eviction-unify.** Removed the lossy
  `extract_room_from_session` heuristic (P1-o) and its only consumer `get_session_type` (both unused externally); room
  identity now comes only from the explicit `RequestContext` fields (Q2; ARCH-6 populates them) — the Priority-2
  session-id parse in `get_context_with_request_info` is gone. **Eviction unified** on a new `_effective_last_active`
  = `max(last_updated, last_activity)`; all three checks (the get_context inline check, the lazy
  `_cleanup_expired_sessions`, the background `_is_context_expired`) now use it, so a session kept alive via one clock
  but not the other is never evicted prematurely (P1-p). Imports + contracts + smoke + store tests green (15 passed).
- **QUAL-28 Stage 3.3 (start) — contextual resolver reads the store by `physical_id`.** `resolve_contextual_command_
  ambiguity`/`_resolve_contextual_command_internal` now take `physical_id` (not `session_id`) and read live actions
  straight from the action store — no `self.sessions[session_id]` lookup — so a "стоп"/"pause" still resolves **after
  the conversation session has been evicted** (the action outlives the session). Orchestrator passes
  `resolve_physical_id(client_id, room_name, session_id)`. This closes F&F eviction-survival on the read side (the
  write side was already store-backed). Import contracts + smoke + store tests green (15 passed). (The old
  `test_phase4_*` callers pass `session_id` — they're in the intentionally-unfixed pre-refactor suite, TEST-7.)
- **QUAL-28 Stage 3.2 — dead-code cleanup + timer simplification.** Removed the orphaned
  `workflow_manager._process_action_metadata_integration` + base.py `_handle_action_completion`/
  `_update_context_on_completion`/`_validate_action_metadata`. **Timer rewritten store-centric:** the old
  `_create_timer_action` *returned immediately* and spawned a nested `timer_callback` task that fired *another* F&F
  notification + kept a parallel `active_timers` dict — so with the store the timer's ActionRecord completed instantly
  and was reaped (timers never actually persisted). Replaced with `_run_timer` = a plain `sleep(duration)` + announce
  that **is** the store task; dropped `active_timers` and the 6 nested/helper methods; migrated all 7 handlers
  (set/cancel/stop/pause/resume/list/status) to read/cancel via `context.active_actions` + `cancel_action`. set_timer
  launches with `timeout = duration + grace` so the monitor never pre-empts; list/status read remaining from the
  store's `expected_end` (now exposed on the `active_actions` view). Minor accepted simplifications: a specific-id
  cancel cancels the domain (single-timer common case); pause/resume are status-flags only (a sleeping task can't truly
  pause — the prior impl was likewise cosmetic); list no longer shows the per-timer message. Smoke + store tests green.
- **QUAL-28 Stage 3.2 — reader migration (the store is now the F&F source of truth).** `context.active_actions` is
  now a **read-only property** over the `ClientRegistry` action store (keyed by the context's `physical_id`), so every
  reader auto-migrates — orchestrator (contextual interception), `context.py` resolver, conversation summary, NLU
  injection, trace snapshot, debug — all now read the store. The write/cancel methods (`add_active_action`/
  `remove_completed_action`/`cancel_action`/`update_action_status`/`has_active_action`/`get_active_action_domains`)
  are **store-backed** (cancel = cancel the task → the done-callback reaps it). Removed both write-backs
  (`voice_assistant._process_action_metadata` + `workflow_manager._process_action_metadata_integration` call sites)
  since the launch registers directly. Actions now **survive conversation-session eviction** (they live in the store,
  not the session). Import contracts + smoke + 9 store tests green (15 passed). **Cleanup left for a later pass (dead,
  uncalled):** `workflow_manager._process_action_metadata_integration` body + base.py `_handle_action_completion`/
  `_update_context_on_completion`. **3.3 refinement:** make the `context.py` resolver read the store by `physical_id`
  directly (today via the session context — works while the session is alive; true eviction-survival on the read side
  needs the physical_id pass-through).
- **QUAL-28 Stage 3.2 — store-centric F&F machinery (launch/completion/timeout) rewritten.** Per user, done
  store-centric (no session-threading), not the rejected `tracking_session_id` patch. `execute_fire_and_forget_*`
  now: resolves `physical_id` from the context, registers an `ActionRecord` **with the real task** in the
  `ClientRegistry` store, and the done-callback **reaps from the store** + fires metrics/notifications **off the
  record** (no `get_or_create_context` session lookup). Identity params are **keyword-only**, so the dup-`session_id`
  crash is fixed **by removal** — an action coroutine's own `session_id` kwarg now flows through (`_create_timer_action`
  case). Timeout monitor uses `wait_for` not flat-sleep; completion tasks held to avoid the orphan-GC bug.
  `mini-TEST-3` lifecycle test added (launch → store has it (live task) → completion reaps it; + the no-collision
  case). **Transitional:** old `context.active_actions` is still populated by the existing write-back (readers
  unchanged → no regression) while the store is now the real source of truth. **Next:** migrate readers
  (orchestrator/`context.py` resolver/conversation/nlu) to the store by `physical_id`; remove `context.active_actions`
  + the write-back + the now-dead `_handle_action_completion`/`_update_context_on_completion`. Import contracts +
  smoke + 9 action-store tests green.
- **QUAL-9 → QUAL-28 MERGE (user, Invariant #8).** Tracing the 3.2 relocation surfaced that (a) readers must hit the
  store by `physical_id` *independently of the session* to get eviction-survival (not a context façade), and (b) the
  authoritative liveness = the task ref, which is created in the F&F **launch** (`base.py`) — QUAL-9 territory. The
  QUAL-28/QUAL-9 split is artificial at that seam, so the **launch + completion** fixes move into QUAL-28 stage
  3.2/3.3 (one clean pass over `base.py`, fully testable via mini-TEST-3). QUAL-9 re-scoped to its tail (metrics
  re-key, delete the duplicate write-back, timeout monitor, timer-cancel cleanup, TEST-3). Ledger entries updated.
- **QUAL-28 Stage 3.1 — action-store skeleton (additive, nothing consumes it yet).** Added to `ClientRegistry`: an
  `ActionRecord` (action_name identity · domain index · live task ref · TTL) and a **runtime-only, non-persisted**
  action store keyed by `physical_id → action_name`, with the **4 reaper layers** (completion-remove · read-time
  liveness filter · periodic sweep · TTL + per-identity cap). Added the **`resolve_physical_id(client_id, room_name,
  session_id)`** seam (client_id > room > session; the one function ARCH-6 flips). New `tests/test_action_store.py`
  (8 tests, all green) — the bottom-up start of mini-TEST-3. Smoke unaffected. Next: 3.2 relocate `active_actions` +
  wire consumers.
- **QUAL-28 Stage-3 design decisions (with user) — incl. the Q1 room/device timing.**
  - **Q1 (room/device story timing):** the room/device story **activates at ARCH-6** (the WS/ESP32 `ClientRegistry`
    registration handshake that *populates* room/client/devices). QUAL-28/29/11 make everything **"room-ready"** (the
    store + context split with device fields, declarative `entity_type`/`room_context`, gracefully-degrading device
    resolvers) — none require a populated room. The whole thing pivots on a single **`resolve_physical_id(request)`**
    seam: today it returns the session-derived id; **ARCH-6 changes only that one function** to return the registered
    `client_id`/room → clean *activation*, not a re-refactor. ARCH-6 gets its design session **after the Gate-2
    foundation (QUAL-28/29/11) stabilizes** (one of the 3 design-gated threads ARCH-6/7/9). ARCH-7 (MQTT) acts on it.
  - **Q2 (action-store home):** **`ClientRegistry`** is the home, realized as a **runtime-only (non-persisted) sub-store**
    keyed by `physical_id` — *not* a field on the persisted registration record (it holds live `asyncio` task refs and
    must never serialize or survive a restart). `ClientRegistry` = persistent registration table (devices/room) + this
    runtime state table (`active_actions` + task refs); the reaper operates on the runtime table; JSON persistence
    ignores it.
  - **Sequencing (decoupled from ARCH-6):** the store + reaper + eviction-survival land **now** keyed by the
    best-available stable id; room/device keying upgrades transparently when ARCH-6 lands. Documented on the QUAL-28 +
    ARCH-6 ledger entries.
- **QUAL-28 Stage 2 — session-id hygiene.** Forbid the literal `"default"` at the `RequestContext` chokepoint
  (`"default"`/empty → derive a real id; P0-6 collapse fixed); the 3 `workflow_manager` entries default to `None` and
  **re-read `context.session_id`** so the local var reflects the derived id (it's reused by the action-metadata
  write-back). Added a real `ContextManager.get_or_create_context` → the 5 phantom callers (base.py/notifications/
  debug_tools) that were `AttributeError`-ing now resolve. Smoke green. **Scope (Invariant #8):** eviction-unify, the
  non-creating-`get` split, and `kill extract_room_from_session` moved to Stage 3 (they need the timestamp-touch audit /
  caller migration / room-as-field from the restructure). **NEXT: checkpoint, then Stage 3 (the structural cut).**
- **QUAL-28 STARTED (staged) — Stage 1: deleted dead `MemoryManager`.** Removed the module + all 7 `monitoring_component`
  wiring sites (init/shutdown/status/2 debug endpoints/accessor/providers-info) + the unused `MemoryStatusResponse`
  import. Confirmed dead first (only consumer was monitoring; called non-existent context methods). Smoke green.
  Staged plan recorded on the ledger (① MemoryManager ✓ → ② session-id hygiene → ③ context model + action store + a
  mini-TEST-3 → ③b migrate consumers + retire ContextLayer → ④ history windowing); checkpoint with user before ③.
  **Invariant #8 catch:** the map agent + Q4 claimed `ContextLayer`/progressive-context was dead — verification showed
  it's **live in `conversation.py`** (LLM context summary). Re-scoped to **migrate-then-retire in §3b** (user-approved);
  review finding annotated. Dead `memory_management_enabled` config key deferred to Q9 (config-ui coord).
- **QUAL-27 DONE — data-contract fixes** (commits `cebb77e` + 2 follow-ups). `Intent.text`→`raw_text` sweep (14
  sites + orchestrator; P0-1 command-surface crashes gone); NLU stamps `raw_text` = original utterance via a
  boundary override in `nlu_component.process(original_text=)`; `WakeWordResult.word` rename (P1-b); **deleted
  `Intent.session_id`** (field + 6 ctor kwargs + metrics read → `context.session_id` + fallback param);
  `IntentResult.__post_init__` enforces `success=False ⟹ error` (P1-a, one backstop over ~35 sites). Smoke green
  throughout. **Scope change (Invariant #8, user-approved):** P1-t (`_create_error_result` unification) found to be
  **6 handlers not 2** + a shared-bases concern → moved to **QUAL-11**; review finding annotated. **NEXT: QUAL-29
  (donation split) + QUAL-28 (context/action refactor) — the Gate-2 foundation.**
- **Invariant #8 added — task-start reconciliation** (user). Before starting any task, reconcile it against
  `RELEASE_JOURNAL.md` + the current code (not just the ledger/review doc per #5): classify valid / partially-done /
  fully-done-obsolete / scope-drifted, and **consult the user before any scope change** — no silent stale/redundant
  work. Important given Gate-2's interdependent tasks (QUAL-27/28/29 will pre-touch QUAL-9/11/13).
- **Doc-architecture restructure + scope-drift guard** (`cdd2dab`) — separated the three concerns into one home each:
  `RELEASE_PLAN.md` = task ledger (scope+status), new `RELEASE_JOURNAL.md` = the one journal, `docs/review/*` = frozen
  evidence (bannered). Refined Invariant #5 to a single status home; added #6 (single ledger + `[release]`/`[deferred]`
  tagging + ship-gate) and #7 (one journal). Added `scripts/check_scope.py` (orphan findings / dead links / unindexed;
  green at 72 tasks).
- **Uncaptured-work audit + ARCH-11/12 added** — audited all 8 review docs vs the ledger: **0 genuinely uncaptured
  findings** (all map direct or as defensible roll-ups). The only work living solely in a review doc were 2 benign
  phase1 residual edges → captured as **ARCH-12** `[deferred]` (`utils.vad→core.metrics`, `utils.logging→config.models`)
  to close the Invariant-#6 gap. Per user, **revoked the ARCH-5 reclassification** of the `core→inputs/workflows/
  components.base` edges as "legitimate" → **ARCH-11** `[release]` will fix them via DI/ports + add the import-linter
  contract (slotted after ARCH-6 + QUAL-28, taking today's input-adapter + context-refactor decisions into account).
- **QUAL-26 DONE — review-of-reviews complete** → `docs/review/dataflow_reconciliation.md`. Live Q&A, **10 issues
  decided** (committed per-decision so it was interruption-safe). Gate 1.5 closed. Key intended-vs-today calls:
  **(Q1)** `raw_text` = original utterance (fixes P0-1); **(Q2)** **Model 2 — split identity from session**
  (long-lived physical-identity store for `active_actions`+devices vs short-lived idle-window conversation session);
  **(Q3)** dedicated zombie-resistant `action_name`-keyed action store; **(Q4)** delete MemoryManager/ContextLayer/
  Intent.session_id, **WebSocket = primary ESP32 transport** (reframes ARCH-6); **(Q6)** declarative device/room via a
  **donation format split** (language-neutral contract + per-language phrasing; `entity_type` + tri-state
  `room_context`); **(Q7)** fail-loud → conversational **clarification** (configurable LLM/deterministic) + typed
  donation-driven accessor; **(Q8)** shared bases (one extraction base / one prompt source = LLM-indep hardening / one
  normalization seam containing the `lingua_franca`+`Runorm` debt); **(Q9)** deployment-aware config-truth (config-master
  is a valid superset); **(Q10)** hybrid framing — **4-theme principles block + discrete tasks QUAL-27..31.** Surfaced a
  4th cross-cutting theme (**data-contract integrity**). Per Invariant #5, plan + both review docs updated together.
  **NEXT: Gate 2 implementation** — QUAL-27 (fast) → QUAL-29 + QUAL-28 (foundation) → per-subsystem.
- **QUAL-25 DONE** → `docs/review/dataflow_review.md`. Ran 5 parallel tracer agents (entry adapters · text-proc/NLU/
  orchestrator · handler boundary · F&F/output · context-model lifecycle), each cross-referencing the 4 prior QUAL
  reviews, then adversarially verified the headline NEW P0s against source. **~9 P0, ~20 P1.** Headline: **a
  `Intent.text`→`raw_text` field rename was never propagated** — `intent.text` read at 14 unguarded sites in 7
  handlers + `Intent(text=…)` at orchestrator.py:217 → most of the command surface AttributeErrors, masked as a
  generic error (the smoke test only covers entity-only handlers, so it stayed green). Other NEW P0s: session_id=
  "default" collapses all sessions (cross-request leak); MemoryManager cleanup loop dead; InputManager/WebSocket
  input path dead (overlaps ARCH-6); required-params unenforced. CONFIRMS all FAF P0s + TXTPROC raw-TTS. **Surfaced a
  4th cross-cutting theme: "data-contract drift"** (model contracts silently disagree across boundaries). §2 answers
  the DOC-8 request-vs-session question; §4+§6 = the QUAL-26 agenda. Per Invariant #5, plan + review doc updated
  together. **NEXT: QUAL-26 (review-of-reviews, live collaboration).**
- **QUAL-25 BROADENED + QUAL-26 added** (user) — (1) QUAL-25 scope widened from "analyze the context/result types"
  to a **full input→action dataflow** analysis (every entry modality: voice/ASR, text, stream → NLU → orchestrator →
  handler → F&F → output). (2) The user expects QUAL-25 to reveal inconsistencies that **cut across the earlier
  reviews**, so added **QUAL-26 [DFLOW] — "review-of-reviews"**: a follow-up live-collaboration session that
  consolidates all review docs and **decides intended-behaviour-vs-today** per contradiction. QUAL-26 (not Gate 2)
  is now where the cross-cutting framing is finalized and remediation tasks numbered. Gate 1.5 = QUAL-25 → QUAL-26;
  cross-cutting IDs (if discrete) shift to QUAL-27/28/….
- **DOC-8 RE-CATEGORIZED** (user correction) — yesterday's DOC-8 was filed as a plain doc task ("write
  `DATA_MODELS.md`"), but end-to-end dataflow clarity is a **macro-task that needs its own review first** (same
  species as ARCH-0 / the QUAL-8/10/12/14 wave). Created **QUAL-25 [DFLOW]** — a **map + findings** review →
  `docs/review/dataflow_review.md`; **DOC-8 demoted** to the downstream write-up that consumes it. Sequencing:
  inserted **Gate 1.5** (QUAL-25) **before Gate 2** — the cross-cutting systemic remediation (fail-loud + typed
  handler-boundary accessor / shared bases / config-truth) is now **downstream of the dataflow review**, since
  "fail-loud + typed accessor" *is* dataflow design. The cross-cutting framing decision (principles block vs
  discrete QUAL IDs) is deferred until QUAL-25 lands, to be informed by its findings. New tag **[DFLOW]**; index row
  added.
- **DOC-8 captured** (user request) — need a reference for how the pipeline's models play together (when/why each):
  `RequestContext` (request-scoped) vs `UnifiedConversationContext` (session-scoped), `Intent`/`IntentResult`,
  `AudioData`/`WakeWordResult`. → `docs/guides/DATA_MODELS.md` + a model-interplay note added to
  `phase1_architecture_map.md` §4. The request-vs-session distinction (sharpened by ARCH-1/5) is the key thing to
  clarify.
- **ARCH-5 DONE** (`27a85c3`) — the capstone. import-linter (dev dep) + 6 `[tool.importlinter]` contracts encoding
  ARCH-1..4 + a pytest test (`test_import_contracts.py`) enforcing them in the suite. **6 kept / 0 broken.** Fixed
  the last residual domain→workflows edge by moving `RequestContext` into `intents/context_models.py` (no
  TYPE_CHECKING; per the user-affirmed clean approach). The linter caught a real service-locator anti-pattern (8
  handlers `get_core()`) → logged **QUAL-24** (ignored-with-comment in the contract for now). Per the standing "ask
  before deciding" rule, got sign-off on: residual-edge handling (fix vs ignore), enforcement (pytest vs file-only),
  and the service-locator decision (ignore+follow-up) via AskUserQuestion before each. Fixed a self-inflicted
  regression mid-task (the moved RequestContext needed its `SessionManager` import). Per Invariant #5, synced
  `phase1_architecture_map.md` §5. **GATE 1 COMPLETE: ARCH-1..5 ✓ — the code provably obeys the hexagon.**
- **ARCH-4 DONE** (`df93a15`) — formalized the port layer. Found a healthy two-layer structure (component-capability
  `*Plugin` ports + adapter `*Provider` ports); audit confirmed adapters depend only on their abstraction. Filled the
  3 missing capability ports (`core/interfaces/{nlu,text_processing,voice_trigger}.py`) with real-domain-typed
  abstract methods (no TYPE_CHECKING) and wired the components. **User instruction mid-task: "ask me before making
  decisions"** — paused and got explicit sign-off on scope (gap-fill vs unify vs audit-only) and on port typing
  (real domain types) via AskUserQuestion before implementing. Verified: components instantiate + isinstance their
  port, no cycle, functional suite unchanged (perf-test flakiness only). Per Invariant #5, synced
  `phase1_architecture_map.md` §5. **Gate 1: ARCH-1✓ ARCH-2✓ ARCH-3✓ ARCH-4✓ — ARCH-5 (import-linter) is the capstone.**

### 2026-05-31
- **Revival analysis** — full doc + code + build + asset audit; established real version is 15.0.0, single
  `UnifiedVoiceAssistantWorkflow`, web API is a router (not a component), 58 entry-points (not "77").
- **DOC-1** — README/architecture synced to v15; ~28 historical docs `git mv` → `docs/archive/` (+ index);
  deprecation banners on `irene_current.md`, `configuration_guide.md`, `PIPELINE_IMPLEMENTATION.md`. → 4a55519
- **ASSET-1** — stale model IDs refreshed; `uv.lock` regenerated (spaCy 3.8.14). → fc85306
- lingua-franca abandoned-upstream tech-debt note added to `pyproject.toml`. → 3e20cd0 (see ASSET-3)
- **QUAL-1** — Phase-0 static baseline filed. → 6e39886
- **QUAL-2** — review round 1: fixed phantom-reference `NameError`s + method shadowing (16 files, +24/−206);
  verified no regressions. → b6cd282
- **Decisions:** work directly on `main`, branch only when explicitly asked · `config-master.toml` stays the
  canonical config (config-example is a release-time story) · architecture defects masked by `TYPE_CHECKING`
  (AudioData misplacement, config→core cycle) to be mapped first (ARCH-0) then fixed (ARCH-1/2), not patched piecemeal.
