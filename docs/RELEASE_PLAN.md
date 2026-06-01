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
| `fire_and_forget_review.md` | F&F lifecycle + gap analysis | QUAL-8/9, TEST-3 |
| `parameter_extraction_review.md` | text→parameters review + gaps | QUAL-10/11, TEST-4, DOC-7 |
| `text_processing_review.md` | text-processor subsystem review | QUAL-12/13, TEST-5 |
| `llm_usage_review.md` | LLM usage + offline-first | QUAL-14/15 |
| `streaming_api_review.md` | AsyncAPI streaming-API tooling | QUAL-17/18 |
| `esp32_wakeword_review.md` | ESP32 + wakeword keep/fix/cut | QUAL-19/20 |
| `docs/design/mqtt_integration.md` | MQTT output-port design | ARCH-7/8 |
| `docs/design/onnx_inference_layer.md` | shared sherpa-onnx inference layer (ASR/TTS/wakeword) | ARCH-9/10 |
| `config-ui/docs/donation_editor_ux.md` | human-friendly donations editor design | UI-1/2/3 |

---

## How to use this file

- **Workstreams** are stable buckets. **Tasks** are the unit of work — sized to one coherent commit/PR,
  with a stable ID (referenced in commit messages, e.g. `ARCH-1: …`).
- Status: `- [ ]` open · `- [x]` done · annotate `BLOCKED`/`DEFERRED`/`DOING` + reason inline. Priority `P0–P2`.
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
- [ ] **QUAL-8** [FAF] (P1) — Fire-and-forget full review & gap analysis. Map the lifecycle end-to-end: launch
      (`intents/handlers/base.py execute_fire_and_forget_with_context`, ~83 call sites), action metadata, context
      state (`active_actions`/`recent_actions`/`failed_actions`/`action_error_count` + `add/remove_active_action`
      in `UnifiedConversationContext`), completion/timeout/cleanup (`cleanup_timeout_tasks`), and monitoring/
      metrics/notifications integration. **Re-validate the 6 issues in `docs/fire_forget_issues.md`** (Sep 2025,
      pre-context-unification) against current code. Done when: `docs/review/fire_and_forget_review.md` exists with
      each prior issue marked confirmed/fixed/changed, new gaps captured, and a ranked remediation list.
- [ ] **QUAL-9** [FAF] (P-TBD) — Remediate confirmed F&F gaps (populated by QUAL-8). Candidates pending
      confirmation: action-metadata key mismatch (`active_actions` plural vs `active_action` singular, issue #1),
      completion write-back + context-manager/callback integration (#2, #6), error propagation (#5), cleanup/
      memory leak (#3), error-handling consistency (#4).
- [ ] **QUAL-10** [PEX] (P1) — Text→parameters (parameter extraction) full review: conceptual + code +
      architecture. Map end-to-end: donation `ParameterSpec`/`ParameterType` (8 types) + `token_patterns`/
      `slot_patterns`/`extraction_patterns` → spaCy Matcher extraction (`providers/nlu/hybrid_keyword_matcher.py`,
      `spacy_provider.py`) → `ContextualEntityResolver` + Device/Location/Temporal/Quantity resolvers
      (`core/entity_resolver.py`) → `Intent.entities` → handler consumption; incl. the `irene/analysis/*` tooling
      and the web-API parameter-schema surface (`get_parameter_schema`). Reality-check
      `docs/archive/parameter_extraction.md`. Done when: `docs/review/parameter_extraction_review.md` exists with
      gaps + severity + ranked remediation.
- [ ] **QUAL-11** [PEX] (P-TBD) — Remediate confirmed parameter-extraction gaps (populated by QUAL-10).
- [ ] **QUAL-12** [TXTPROC] (P2) — Text-processor subsystem review: role/functionality of the 4 providers
      (`asr`/`general`/`tts`/`number_text_processor`), the 3 normalizers (`NumberNormalizer`/`PrepareNormalizer`/
      `RunormNormalizer` in `utils/text_normalizers.py`), and the **double stage-routing** (provider-per-stage
      classes vs config `[text_processor.normalizers.*].stages`). Decide what's justified vs legacy-from-old-Irene
      (ASR & Number processors both compose only `NumberNormalizer` = likely redundant). Intersects ASSET-3
      (`NumberNormalizer` uses lingua-franca). Done when: `docs/review/text_processing_review.md` exists with a
      keep/merge/collapse recommendation + ranked remediation.
- [ ] **QUAL-13** [TXTPROC] (P-TBD) — Refine per QUAL-12 (likely collapse the 4 providers into one config-driven
      `TextProcessor` and unify stage routing).
- [ ] **QUAL-14** [LLM] (P1) — LLM usage review: map every LLM invocation in the flow (`conversation`,
      `translation_handler`, `text_enhancement_handler` + `LLMComponent` + 3 providers), what each uses it for,
      and the **offline-first posture** — confirm NLU is LLM-free (spaCy + keyword) per the original offline plan;
      document where internet is required vs optional and graceful degradation when offline (fallback to console).
      Analyze: **should NLU use an LLM?** (usefulness vs offline-first; e.g. optional online LLM-NLU with spaCy
      offline fallback). Done when: `docs/review/llm_usage_review.md` exists with recommendations.
- [ ] **QUAL-15** [LLM] (P-TBD) — Act on QUAL-14 (NLU-LLM decision; offline graceful-degradation hardening).
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

### Tests (TEST)
- [ ] **TEST-1** (P1) — Fix broken tests referencing removed/renamed symbols (`ConversationContext`→
      `UnifiedConversationContext`, `TTLCache`, `ContextualCommandPerformanceManager`). 16 undefined-name refs.
- [ ] **TEST-2** (P1) — Get the suite running green; assess coverage and trustworthiness.
- [ ] **TEST-3** [FAF] (P2) — Fire-and-forget lifecycle test coverage (launch → completion → error → cleanup →
      context propagation). Scope after QUAL-8 maps current coverage.
- [ ] **TEST-4** [PEX] (P1) — Parameter-extraction test coverage (user-flagged as key): assess existing tests
      (`test_parameter_schema_unification`, `test_context_aware_nlu`, `test_cascading_nlu`,
      `test_web_api_parameter_schemas`), fix broken ones, fill gaps across the 8 ParameterTypes, the 4 entity
      resolvers, and pattern matching. Coupled to TEST-1 (some of these may be in the broken-test set).
- [ ] **TEST-5** [TXTPROC] (P2) — Text-processor / normalizer test coverage, after QUAL-12/13 settle the model.

### Build & CI (BUILD)
- [x] **BUILD-1** (P0) — Verify clean `uv sync` + CLI and WebAPI boot at v15. **DONE 2026-06-01** (`bab6f97`):
      `uv sync --extra all` clean; `--check-deps` 5/5; **WebAPI** boots (workflow READY, 10 routers) and
      `POST /execute/command "привет"` → `greeting.hello` end-to-end; **CLI** boots and (after fix) headless
      `--command "привет"` works. Found+fixed a real bug: `--headless` disabled `nlu`/`text_processor` while the
      unified workflow requires `nlu` → headless could never execute a command. Observed (already-logged) cosmetics:
      QUAL-6 schema warning on boot; CLI banner still says "v14" (DOC-3 sibling).
- [ ] **BUILD-2** (P1) — Re-enable CI (`config-validation.yml` is manual-only; update deprecated
      `upload-artifact@v3` / `setup-python@v4`).
- [ ] **BUILD-3** (P1) — Verify the minimal Docker build (x86_64 builder feeds analyzer package names to
      `uv sync --extra`, which expects extra *names* — confirm/fix). Refs: README-DOCKER, build audit.
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
