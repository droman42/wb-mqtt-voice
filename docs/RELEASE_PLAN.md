# Irene — Release Plan

The single active tracker for the road to release. Supersedes the legacy `docs/TODO.md` +
`docs/TODO/TODO0x` (refactor-era, mostly complete — to be archived under DOC-2).

**Target:** _TBD_ · **Status:** reviving (paused ~Sep 2025, restarted May 2026) · **Version:** 15.0.0

## Definition of release (exit criteria) — _draft, refine_

- [ ] Clean `uv sync`; boots in CLI **and** WebAPI modes on x86_64, and as a Docker image.
- [ ] CI green (re-enabled, current action versions).
- [ ] No phantom-reference / runtime `NameError` bugs; pyright (standard) at/under an agreed threshold.
- [ ] Import layering honored: no real cycles, no backwards cross-layer imports per an agreed contract.
- [ ] Test suite runs and passes; coverage understood.
- [ ] Models point to current versions with live download URLs.
- [ ] Docs accurate at the release version; quickstart works end-to-end.
- [ ] **`config-ui` builds (`tsc && vite build`), type-checks clean, and is functional against the release backend.**

---

## Invariants (apply to EVERY task)

1. **Work on `main`; branch only when explicitly asked.**
2. **`configs/config-master.toml` is the canonical config reference** (a release-time `config-example.toml` is a later story).
3. **Architecture target = Hexagonal**; dependencies point inward (domain → application → ports → adapters). Don't add backwards/cross-layer imports (enforced by ARCH-5 import-linter once in place).
4. **`config-ui` must stay functional.** It is a first-class consumer of backend contracts. Any task that changes
   one of these **must update config-ui in the same change and leave it building/type-checking clean**:
   - **Donation schema/format** (`assets/donations/v1.0.json`, `ParameterSpec`/`MethodDonation` shape) → config-ui
     editors (`ParameterSpecEditor`, `Token/SlotPatternsEditor`, `Examples/LemmasEditor`), its **AJV** validation, and `src/types/*`.
   - **Config schema** (`CoreConfig` / `config-master.toml`) → `ConfigSection` editors, `/configuration/config*` calls, `src/types/*`.
   - **REST API endpoints / parameter schemas / analysis endpoints** → `src/utils/apiClient.ts`, the analysis components.
   - Definition-of-done addendum for such tasks: `cd config-ui && npm run type-check && npm run build` passes.
   - Directly-gated tasks: **DOC-5b, DOC-4, DOC-7, QUAL-7, QUAL-10/11, ARCH-1/2/3, BUILD-4.**
5. **Review docs stay in sync (living, not write-once).** Detailed findings live in `docs/review/*` (and design
   docs in `docs/design/*`); the plan links to them via the index below. When a task derived from a review doc is
   completed or its finding changes, **update the corresponding review doc in the same change** — mark findings
   resolved/obsolete and update status (as we did with "Remediation round 1" in `phase0_static_baseline.md`). A
   contract-/finding-touching task is not *done* until its review doc reflects reality. Each new review adds a row
   to the index below.

---

## Review documents (findings index)

Living findings behind the tasks (Invariant #5). `[x]` = exists; others are produced by their review task.

| Doc (`docs/review/` unless noted) | Covers | Backs |
|---|---|---|
| `phase0_static_baseline.md` `[x]` | static baseline: phantom refs, hidden type debt, dead code, layering | QUAL-1/2 ✓, QUAL-3/4/5/6, TEST-1 |
| `phase1_architecture_map.md` `[x]` | architecture map, doc-harmonization audit, hexagon target | ARCH-0 ✓, ARCH-1..8, DOC-4/5✓/5b/6✓ |
| `fire_and_forget_review.md` `[x]` | F&F lifecycle + gap analysis (6 legacy issues re-validated) | QUAL-8 ✓, QUAL-9, TEST-3, DOC-4 |
| `parameter_extraction_review.md` `[x]` | text→parameters review + gaps | QUAL-10 ✓, QUAL-11, TEST-4, DOC-7, UI-1/2/3, QUAL-22 |
| `text_processing_review.md` `[x]` | text-processor subsystem review + LLM-text-proc question | QUAL-12 ✓, QUAL-13, TEST-5 |
| `llm_usage_review.md` `[x]` | LLM usage + offline-first + NLU-LLM decision | QUAL-14 ✓, QUAL-15, QUAL-16 |
| `streaming_api_review.md` | AsyncAPI streaming-API tooling | QUAL-17/18 |
| `esp32_wakeword_review.md` | ESP32 + wakeword keep/fix/cut | QUAL-19/20 |
| `docs/design/mqtt_integration.md` | MQTT output-port design | ARCH-7/8 |
| `docs/design/onnx_inference_layer.md` | shared sherpa-onnx inference layer (ASR/TTS/wakeword) | ARCH-9/10 |
| `config-ui/docs/donation_editor_ux.md` | human-friendly donations editor design | UI-1/2/3 |

---

## How to use this file

- **Workstreams** are stable buckets. **Tasks** are the unit of work — sized to one coherent commit/PR,
  with a stable ID (referenced in commit messages, e.g. `ARCH-1: …`).
- Status: `- [ ]` open · `- [x]` done · `- [~]` paused/partial · annotate `BLOCKED`/`DEFERRED`/`DOING` + reason inline. Priority `P0–P2`.
- Individual lint findings live in the review docs (e.g. `docs/review/phase0_static_baseline.md`) and
  **roll up** into a task here — keep this file a spine, not a dumping ground.
- Record what actually happened (and decisions) in the **Action journal** at the bottom.

---

## Workstreams

### Architecture & Refactor (ARCH)
Target pattern: **Hexagonal (Ports & Adapters)** — SIGNED OFF 2026-06-01. Code is already ~80% there
(interfaces=ports, providers=adapters, components=app services, entry-points=registry).
See `docs/review/phase1_architecture_map.md` §5.
- [x] **ARCH-0** (P1) — Architecture MAP & document (Goal 1 doc-sync findings + Goal 2 pattern). → `docs/review/phase1_architecture_map.md`
- [ ] **ARCH-1** (P0) — Split the `intents/models.py` god-module (in-degree 67): move `AudioData`/`WakeWordResult`
      to a foundational module and conversation-context types to their own; re-point importers downward; drop the
      `audio_helpers.py` `TYPE_CHECKING` band-aid. Dissolves most backwards edges. Done when: domain has no
      outward deps for these types; ruff/pyright clean; imports OK.
- [ ] **ARCH-2** (P0) — Break config↔core / config↔components: schema auto-registry must not import
      `configuration_component`; `config/validator.py:222` must not import `core.components` (inject/move
      `discover_providers`); remove import-time schema-validation side-effects; drop the `core/assets.py`
      `TYPE_CHECKING` band-aid. Resolves SCC-1 and the `core→config` cycle.
- [ ] **ARCH-3** (P1) — Stop components importing delivery/tooling: put web-schema generation
      (`components.{asr,tts}→web_api.asyncapi`) behind a port; treat `analysis` as a driven adapter
      (`components.nlu_analysis→analysis.*`).
- [ ] **ARCH-4** (P2) — Formalize ports: every provider category has an interface in `core/interfaces`; adapters depend only on it.
- [ ] **ARCH-5** (P1) — Add an **import-linter** contract (layered + independence) wired into CI so the hexagon is enforced and can't regress. _Makes "follows the architecture" verifiable._
- [ ] **ARCH-6** (P2) — Resolve the dead `InputManager._input_queue` seam (wire as driving port, or delete). Fix the contained `inputs.base ⇄ subclasses` cycle (SCC-2).
- [ ] **ARCH-7** [MQTT] (P-TBD) — **Design session** (needs live collaboration): place MQTT publication as a driven
      **output adapter** in the hexagon (intent result/action → output port → MQTT adapter). Defines the general
      output-port seam — MQTT is the **first non-audio output** (today output is TTS/audio-only via
      `_handle_tts_output`; there is no `irene/outputs/` package). Evaluate placement (output adapter vs
      fire-and-forget action type [FAF] vs MQTT intent handlers per `docs/intent_mqtt.md`); integrate
      `ClientRegistry`/`DeviceEntityResolver` for room/device topics; define topic schema (HA convention?) + config
      model; reconcile/supersede `docs/intent_mqtt.md`. → `docs/design/mqtt_integration.md`.
- [ ] **ARCH-8** [MQTT] (P-TBD) — Implement per ARCH-7 (output-port seam + MQTT adapter + config + handler/action
      integration + tests). Split into PR-sized tasks from the design.
- [ ] **ARCH-9** [INFER] (P-TBD) — **Design session** (needs live collaboration): a **shared sherpa-onnx (k2-fsa)
      inference layer** behind the existing ASR/TTS/VoiceTrigger ports. Today inference is **provider-owned and
      fragmented** — whisper→torch, silero v3/v4→torch, vosk→Kaldi C++, openWakeWord & vosk-tts→onnxruntime
      (black-boxed); 2–3 runtimes loaded in one process, no shared session/asset management. Key enabler:
      **`onnxruntime 1.22.1` is already a transitive dep** (via `openwakeword` + `vosk-tts`); zero direct use in
      `irene/`. sherpa-onnx is one ONNX runtime spanning **ASR** (EN+RU Zipformer, streaming+offline), **TTS**
      (100+ VITS/40+ langs incl. RU), **wake-word/KWS**, and **VAD** — int8 and edge-sized (RU small 45MB→21MB,
      full 1.9GB→929MB, WER 6.1), serving the offline + **[ESP32]** goals. **Constraint (user, do not violate):
      NOT a rip-and-replace.** Whisper and Silero stay **first-class** — both are genuinely strong and target
      **different deployment profiles** (they'd never co-exist in one real deployment); sherpa-onnx is an
      **additional backend family**, not a replacement. **Also explore sherpa-onnx variants of those models**
      (Whisper exported to ONNX runs under sherpa-onnx; Silero-VAD is ONNX) so the *same* models can optionally
      run on the unified runtime — dropping torch from edge images while keeping the models. Hexagonal placement:
      adapters stay behind their ports; "**sherpa runtime + model-asset loader**" becomes a shared driven-adapter/
      infra service (extends `core/assets.py`). Explicitly **avoid** a generic torch+onnx+Kaldi abstraction
      (leaky, low value) — the real shared seam is the ONNX runtime itself. Decisions for the session: modality
      order (ASR-RU spike first); **RU TTS quality A/B** (sherpa VITS/Piper vs Silero v4 — the one non-obvious
      win); **wake-word consolidation** (sherpa KWS vs openWakeWord/microWakeWord — intersects **QUAL-19/20
      [ESP32]**); config model + Invariant #4; dependency/image + armv7 impact of the sherpa-onnx wheel.
      Intersects ASR/TTS providers, ASSET (model zoo/format), ARCH-4 (ports). → `docs/design/onnx_inference_layer.md`.
- [ ] **ARCH-10** [INFER] (P-TBD) — Implement per ARCH-9. First spike: a **sherpa-onnx ASR provider** (RU Zipformer
      int8) on a shared runtime+asset helper, alongside vosk/whisper; then expand per the design (TTS family,
      wake-word) keeping whisper/silero as first-class options. Gated by Invariant #4 (provider config →
      config-ui). Split into PR-sized tasks from the design.

### Code Quality & Review (QUAL)
- [x] **QUAL-1** — Phase-0 static baseline (ruff/pyright/vulture/validators/import-graph). → `docs/review/phase0_static_baseline.md` (6e39886)
- [x] **QUAL-2** — Review round 1: phantom-reference `NameError`s + method shadowing. → b6cd282
- [ ] **QUAL-3** (P1) — Category D wiring: `Monitoring`/`Configuration` define `get_python_dependencies` as an
      unbound instance method; the 4 runners miss the metadata methods. Done when: `dependency_validator --validate-all` passes 58/58.
- [ ] **QUAL-4** (P1) — Type-safety debt: re-tighten `mypy.ini`/`pyrightconfig.json` and burn down the ~1063
      standard-mode pyright errors (subdivide after ARCH lands). Refs: §E.
- [ ] **QUAL-5** (P2) — Cruft: 360 unused imports, 62 star-imports, vulture dead-code pool. Refs: §G.
- [ ] **QUAL-6** (P2) — Config schema gap: 9 `CoreConfig` fields without section models (import-time warning). Refs: §H.
- [ ] **QUAL-7** (P2) — `configs/config-master.toml` puts train-schedule under `[intent_system.handlers.train_schedule]`,
      but the model field is `IntentSystemConfig.train_schedule` (→ `[intent_system.train_schedule]`). The
      config-master section is orphaned/ignored. Reconcile config-master with the model. (Found during DOC-5.)
- [x] **QUAL-8** [FAF] (P1) — Fire-and-forget full review & gap analysis. **DONE 2026-06-01** →
      `docs/review/fire_and_forget_review.md` (5×P0, 8×P1, 6×P2). Verdict: **F&F is broken end-to-end** and the
      legacy `docs/fire_forget_issues.md` "✅ COMPLETED" is **materially false** (banner added). Legacy issues:
      #4 FIXED, #6 FIXED-but-moot, #1 & #5 CHANGED-still-broken, #2 CHANGED-unreachable, #3 CONFIRMED. Plan
      correction: ~13 call sites in 3 handlers, not "~83".
- [ ] **QUAL-9** [FAF] (P1) — Remediate F&F (ranked in the review). **P0s:** (1) **timers crash on launch** —
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
- [ ] **QUAL-11** [PEX] (P1) — Remediate parameter-extraction gaps (ranked in the review). **P0s:** (1) fix the
      default `provider_cascade_order` — it names non-existent providers (`keyword_matcher`/`spacy_rules_sm`/
      `spacy_semantic_md` vs real `hybrid_keyword_matcher`/`spacy_nlu`, `nlu_component.py:380`) + add a startup
      assertion; (2) decide the slot/extraction-pattern story (implement, or remove the dead author-visible fields);
      (3) make required-param a real contract on a **shared** extraction base (raise on missing-required, stop
      swallowing, always apply `default_value`, unify spaCy+hybrid → deterministic param surface); (4) de-fatalize
      the entity resolvers (degrade, don't crash the request, when the asset loader isn't wired); (5) **QUAL-22**
      (finish/delete the context-enhancement stub). **P1s:** typed `ParameterSpec`-driven entity accessor on
      `IntentHandler`; fix first-match span→value; default `_md` spaCy models for similarity; unify duplicate device
      resolution. Gated by Invariant #4 (config-ui).
- [x] **QUAL-12** [TXTPROC] (P2) — Text-processor subsystem review. **DONE 2026-06-01** →
      `docs/review/text_processing_review.md` (5×P0, 6×P1, 6×P2). Verdict: the subsystem is **mostly decorative at
      runtime** — `process()` is hardcoded to stage `"general"`, so only `general_text_processor` ever runs (on ASR
      output); the `asr_output`/`tts_input` stages are never routed; **TTS synthesizes raw text** (no normalization
      call site); the `[text_processor.normalizers.*]` config tree is **dead** (never read); the WebAPI 500s on a
      phantom `self.processor`; `number_text_processor` duplicates `asr_text_processor` and is unreachable;
      `NumberTextProcessor.process()` calls a non-existent method. **LLM-for-text-processing answer:** architecturally
      possible (open provider interface + DI), not wired today (only the dead `universal_llm` path), and should only
      be an **opt-in online-only `asr_output` stage** augmenting the deterministic default — never on the default path.
- [ ] **QUAL-13** [TXTPROC] (P1) — Refine per QUAL-12: **collapse + wire.** (1) Collapse the 4 providers into ONE
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
- [ ] **QUAL-15** [LLM] (P1) — Act on QUAL-14. **P0s:** (1) implement a real local LLM fallback (console/echo at
      minimum, ideally a local-model provider) + register its entry-point, OR drop `console` from configs and
      document LLM as online-only; add a startup assertion that every `default_provider`/`fallback_providers`
      resolves to a discovered provider; (2) make `fallback_providers` actually iterate at runtime (mirror
      TTS/audio, not `keys()[0]`); (3) give `generate_response` a graceful offline outcome (don't raise). **P1s:**
      `openai.is_available()` local check; per-call timeouts + client reuse; fix the dead ASR `universal_llm`
      lookup; stop `enhance_text` masking failures as success; `silero_v3.is_available()` local check. NLU-LLM
      assist (local, opt-in) deferred behind ARCH-9/10 + QUAL-11.
- [ ] **QUAL-16** [PROMPTS] (P1) — Prompt hardening for ALL LLM use cases: audit every prompt — asset YAML
      (`assets/prompts/<handler>/<lang>.yaml`) **and inline-in-code prompts** (translation/text_enhancement/
      conversation handlers) — and rewrite for clarity, guardrails, output-format constraints, persona
      consistency, and prompt-injection resistance. Establish a prompt-authoring convention. Gated by Invariant #4
      (config-ui `PromptEditor`). Done when: prompts hardened + `docs/guides/PROMPTING_GUIDE.md` exists.
- [ ] **QUAL-17** [STREAMAPI] (P2, must-before-release) — Critically review the streaming-API exposure: the
      hand-rolled **AsyncAPI 2.6.0** generator (`irene/web_api/asyncapi.py`: `@websocket_api` decorators,
      `WebSocketRegistry`, custom Pydantic→AsyncAPI conversion) + the `@asyncapi/web-component@2.6.4` renderer at
      `/asyncapi`, documenting the WebSocket endpoints (`/asr/stream`, `/asr/binary`, `/ws`). Evaluate modern
      alternatives (AsyncAPI 3.0, maintained generator libraries, current renderers/Studio) — simpler/more
      maintainable today? Done when: `docs/review/streaming_api_review.md` exists with a keep/upgrade/replace recommendation.
- [ ] **QUAL-18** [STREAMAPI] (P-TBD) — Act on QUAL-17 (upgrade/replace the AsyncAPI generator + renderer).
- [ ] **QUAL-19** [ESP32] (P2, last pre-release) — Full review & questioning of the ESP32 + wakeword story:
      ESP32 firmware subsystem (ESP-IDF nodes/common/tools, embedded microWakeWord model **not committed**,
      binary-WS audio streaming) — functional vs aspirational; the backend **microWakeWord provider is largely a
      placeholder** (stub feature extraction; depends on trained models but training was removed at `886d4d1`;
      HF model download = **TODO11, still Open**); openWakeWord (works) vs microWakeWord (broken/redundant?);
      residual training dead-code; armv7/embedded build viability (`Dockerfile.armv7`, `embedded-armv7`); ESP32
      docs accuracy. Intersects ASSET-2 (wakeword model URLs). Done when: `docs/review/esp32_wakeword_review.md`
      exists with a **keep/fix/cut** recommendation per piece {ESP32 firmware, microWakeWord, armv7, training refs}.
- [ ] **QUAL-20** [ESP32] (P-TBD) — Act on QUAL-19 (complete TODO11 + real feature extraction, OR cut/archive
      microWakeWord + ESP32 + residual training refs; reconcile armv7; close TODO11 accordingly).
- [ ] **QUAL-21** (P1) — **Prod bug found via TEST-2**: `ComponentConfig` field drift not propagated to all callers.
      The component fields are now `{asr, audio, tts, nlu, text_processor, llm, voice_trigger, intent_system,
      monitoring, nlu_analysis, configuration}` — there is **no** `audio_output`, `microphone`, or `web_api`
      (mic/web moved to `config.inputs.*` / `config.system.web_api_enabled`; `audio_output`→`audio`). But
      `irene/runners/settings_runner.py` (the `irene-settings` Gradio runner) still does
      `config.components.audio_output` (L279) and `ComponentConfig(audio_output=…, microphone=…, web_api=…)` (L305)
      → **would crash on launch**. `irene/examples/{dependency_demo,component_demo,config_demo}.py` have the same
      stale kwargs. Fix the runner against the real model (and inputs/system split); update/retire the examples.
      Not done in the TEST pass because the mic/web migration is non-trivial (needs the inputs/system split, not a
      rename). Verify `irene-settings` boots after.

- [ ] **QUAL-22** [PEX] (P2) — **Stubbed feature found via TEST-2, confirmed by QUAL-10**: context-aware NLU
      enhancement is a no-op. `ContextAwareNLUProcessor._disambiguate_with_device_context` (`nlu_component.py`
      157-187 — the method QUAL-22 first called `_enhance_intent`) computes `enhanced_entities`
      (`output_capabilities`, `context_suggestion`, `preferred_output_device`) but then **returns the original
      intent unchanged** (comment: "for now, return original"); location inference (`location_resolved`) is
      unimplemented. Either finish the enhancement (apply enhanced_entities / wire capability + location context)
      or remove the dead logic. Relates to QUAL-10 [PEX]. xfail tests: `test_client_capability_context`,
      `test_room_context_inference`.

### Tests (TEST)
> **Strategy (decided 2026-06-01): do NOT keep repairing the existing suite.** Most tests were written against
> pre-refactor code and will be invalidated by the ARCH refactors (ARCH-1..5) and the code reviews (QUAL-8/10/12/14).
> Fixing them now is throwaway work. The TEST-1/TEST-2 pass already extracted the real value — it **proved the suite
> runs** and surfaced concrete prod findings (QUAL-21, QUAL-22, the text_processor trace fix). The current state
> (166 pass / 56 fail / 13 skip / 2 xfail, all committed) stands as a **partial safety net**; the remaining 56
> failures are left **intentionally unfixed**. The real test effort is **TEST-7: rewrite the suite after the
> architecture + code reviews land** (gated). TEST-3/4/5/6 are coverage goals folded into that rewrite.
- [x] **TEST-1** (P1) — Fix broken tests referencing removed/renamed symbols. **DONE 2026-06-01**:
      `ConversationContext`→`UnifiedConversationContext` (rename); `TTLCache`/`ContextualCommandPerformanceManager`/
      `initialize_performance_manager` were **deleted** (v13→v15 contextual-command unification) → those tests
      skipped-with-reason; `Intent.text`→`raw_text`, `ComponentConfig.audio_output`→`audio` renamed in tests.
- [~] **TEST-2** (P1) — **PAUSED 2026-06-01 (deliberate — see strategy note).** Suite now **runs** and is a
      partial safety net: 136/100/0 → **166 passed / 56 failed / 13 skipped / 2 xfailed** (committed). Cleared:
      async config, symbol renames, obsolete skips, hardcoded-path bug, and the fixture-wiring cluster. The
      remaining 56 drift failures are **left unfixed on purpose** (will be obsoleted by ARCH/review then rewritten,
      TEST-7). Diagnosed-but-not-fixed clusters (for whoever does the rewrite): `test_cascading_nlu`
      provider-metadata (`entities["provider"]` vs `_recognition_provider`, ~7 — design-intent question),
      VAD/ASR metrics dict-vs-object (~8), `spacy_asset_integration` mock-vs-MagicMock (2), attr renames
      (`IntentResult.error_type`, `SpaCyNLUProvider.model_name`, `IntentRegistry._handlers`,
      `IntentComponent.get_system_status`), phase4 contextual-command + assertions. Value already banked:
      **QUAL-21**, **QUAL-22**, text_processor trace fix.
- [ ] **TEST-7** (P1) — **Rewrite the test suite against the stabilized architecture.** GATED by: ARCH-1..5
      (structure settled + import-linter) **and** the code reviews (QUAL-8/10/12/14) landing. Replace the
      pre-refactor suite (which the TEST-1/2 pass kept *running* but not green) with tests written to the hexagon:
      ports/adapters seams, the unified workflow, and real fixtures (e.g. the localization-asset loader pattern
      from `test_context_aware_nlu`). Absorbs the coverage goals below (TEST-3/4/5/6) and decides, per failing
      cluster left by TEST-2, rewrite-vs-delete. Done when: suite is green (or green-modulo-documented-xfail) and
      coverage is understood/trusted.
- [ ] **TEST-6** (P2) — _(folded into TEST-7)_ Restore ASR provider-fallback + resampling coverage (the 7 phase7
      tests skipped in TEST-1 called the removed `_handle_sample_rate_mismatch`; feature lives in
      `AudioProcessor.resample_audio_data`).
- [ ] **TEST-3** [FAF] (P2) — _(coverage goal for TEST-7)_ Fire-and-forget lifecycle coverage (launch → completion
      → error → cleanup → context propagation). Scope after QUAL-8.
- [ ] **TEST-4** [PEX] (P1) — _(coverage goal for TEST-7)_ Parameter-extraction coverage (user-flagged as key):
      the 8 ParameterTypes, the 4 entity resolvers, pattern matching; rebuild around `test_parameter_schema_unification`/
      `test_context_aware_nlu`/`test_cascading_nlu`/`test_web_api_parameter_schemas`.
- [ ] **TEST-5** [TXTPROC] (P2) — _(coverage goal for TEST-7)_ Text-processor / normalizer coverage, after QUAL-12/13.

### Build & CI (BUILD)
- [x] **BUILD-1** (P0) — Verify clean `uv sync` + CLI and WebAPI boot at v15. **DONE 2026-06-01** (`bab6f97`):
      `uv sync --extra all` clean; `--check-deps` 5/5; **WebAPI** boots (workflow READY, 10 routers) and
      `POST /execute/command "привет"` → `greeting.hello` end-to-end; **CLI** boots and (after fix) headless
      `--command "привет"` works. Found+fixed a real bug: `--headless` disabled `nlu`/`text_processor` while the
      unified workflow requires `nlu` → headless could never execute a command. Observed (already-logged) cosmetics:
      QUAL-6 schema warning on boot; CLI banner still says "v14" (DOC-3 sibling).
- [ ] **BUILD-2** (P1) — Re-enable CI (`config-validation.yml` is manual-only; update deprecated
      `upload-artifact@v3` / `setup-python@v4`).
- [ ] **BUILD-3** (P2) — **DEFERRED to the release phase (decided 2026-06-01): Docker builds are an end-stage
      task**, after the architecture/code work settles (image contents, extras, and armv7 viability all depend on
      the post-refactor shape — incl. QUAL-19/20 [ESP32] and ARCH-9/10 [INFER] for the sherpa-onnx/runtime
      footprint). Then verify the minimal x86_64 Docker build (builder feeds analyzer package names to
      `uv sync --extra`, which expects extra *names* — confirm/fix) + container boots CLI/WebAPI. Gates
      Definition-of-release item #1. Refs: README-DOCKER, build audit.
- [ ] **BUILD-4** (P1) — config-ui builds & type-checks clean (`npm ci && npm run type-check && npm run build`;
      `dist` is git-ignored). Per Invariant #4 this is an **ongoing gate** — add it to CI (BUILD-2) so backend
      contract changes that break config-ui are caught.

### Models & Assets (ASSET)
- [x] **ASSET-1** — Refresh stale model IDs (Anthropic→Claude 4.x, Whisper large-v3, ElevenLabs multilingual_v2, spaCy 3.8, gpt-4→gpt-4o-mini). → fc85306
- [ ] **ASSET-2** (P1) — Liveness-check all model download URLs after the pause (`models.silero.ai` → prefer
      torch.hub as a hedge; openWakeWord v0.5.1; alphacephei vosk). **Caveat:** test **off the VPN/proxy** before
      declaring any host dead — this network uses fake-IP mode (every host resolves into `198.18.0.0/15`), which is
      normal; the real failure signal is a connection **stall/ERR**, not the IP. Verified 2026-06-01: silero.ai,
      alphacephei, github, whisper-CDN and PyPI all reachable and serving real bytes (silero served the real 40MB
      `v4_ru.pt`), so the "silero flaky/dead" reputation was at least partly the proxy stall, not the host.
- [ ] **ASSET-3** (P2) — DEFERRED — Migrate `lingua-franca` off the abandoned MycroftAI git pin to the OVOS
      successors (`ovos-number-parser`/`ovos-date-parser`), or mirror/vendor. Refs: `pyproject.toml` note.

### Documentation (DOC)
- [x] **DOC-1** — Sync README/architecture to v15; archive ~28 historical docs to `docs/archive/`. → 4a55519
- [ ] **DOC-2** (P2) — Archive completed `docs/TODO/TODO0x`; mark `docs/TODO.md` superseded by this file; keep open TODO11 + partials.
- [ ] **DOC-3** (P2) — Fix cosmetic stale-version strings: "v13" in `irene/core/engine.py` docstrings/logs and the
      "v14" CLI banner in `irene/runners/cli.py` (`--help` description). Should read v15.
- [ ] **DOC-4** (P1) — Rewrite `architecture.md` to the harmonized current state **+ chosen target pattern**
      (do after pattern sign-off, so it's written once). Refs: phase1_architecture_map §3, §4, §5.
      Must also **document the fire-and-forget action flow** [FAF] (currently undocumented) and **retire
      `docs/fire_forget_issues.md`** once QUAL-8/9 land.
- [x] **DOC-5** (P1) — Fixed docs that CONTRADICT code: `donations_flow.md` + `intent_donation.md` (donation
      paths → `assets/donations/<handler>_handler/<lang>.json`, schema → `assets/donations/v1.0.json`),
      `ASSET_MANAGEMENT.md` (12 TOML-nesting fixes `[providers.X]`→`[X.providers]`), `train_schedule_handler.md`
      (env → `IRENE_INTENT_SYSTEM__TRAIN_SCHEDULE__*`), `voice_trigger.md` (YAML→TOML), and authoritative
      correction banners on `guides/DONATION_FILE_SPECIFICATION.md` + `plugins/universal_tts.md`.
- [ ] **DOC-5b** (P2) — Full regeneration of `guides/DONATION_FILE_SPECIFICATION.md` from the Pydantic
      `HandlerDonation`/`MethodDonation` models (currently fixed via banner only; body still uses old field names).
- [ ] **DOC-7** [PEX] (P1) — Canonical parameter-extraction reference (the design doc was archived; nothing
      current): authoring `ParameterSpec`, ParameterType semantics, token/slot pattern format, entity resolution,
      handler consumption of `intent.entities`. → `docs/guides/PARAMETER_EXTRACTION_GUIDE.md`. Derived from QUAL-10.
- [x] **DOC-6** (P2) — Archived stale historical-plan docs (`config_schemas`, `language_support`,
      `configuration_guide`, `PIPELINE_IMPLEMENTATION`, `irene_current`) → `docs/archive/`.

### UI / config-ui (UI)
React/Vite donation+config editor. Front-end feature/UX work (the BUILD-4 build gate stays under Build & CI).
Governed by Invariant #4 (config-ui must stay functional).
- [ ] **UI-1** [DEDITOR] (P2) — Design a human-friendly donation/pattern authoring model: an abstraction over raw
      spaCy `token_patterns`/`slot_patterns` usable by a non-spaCy intent developer (literals, parameter slots
      mapped to the 8 ParameterTypes + entity resolvers, optionality/repetition, synonyms/lemmas) + an
      **"advanced (raw spaCy)" escape hatch**. → `config-ui/docs/donation_editor_ux.md`. **Depends on QUAL-10 [PEX].**
      (Today `TokenPatternsEditor`/`SlotPatternsEditor` expose raw spaCy directly; `ParameterSpecEditor` is already fine.)
- [ ] **UI-2** [DEDITOR] (P2) — Bidirectional translation layer (human model ↔ spaCy token/slot patterns) with
      round-trip fidelity + validation (must emit schema-valid spaCy). Decide frontend-only vs. a backend
      `compile/decompile` endpoint reusing the real spaCy logic.
- [ ] **UI-3** [DEDITOR] (P2) — Reimplement `TokenPatternsEditor`/`SlotPatternsEditor` on the new model (retain
      raw-spaCy advanced mode); add "test pattern against sample text" via the NLU recognize endpoint.

### Release Readiness (REL)
- [ ] **REL-1** (P0) — Sign off the Definition-of-release checklist above (fill target + criteria).
- [ ] **REL-2** (P1) — `config-example.toml` + quickstart finalization (the release-time config story).
- [ ] **REL-3** (P1) — Version bump / changelog / tag.

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
