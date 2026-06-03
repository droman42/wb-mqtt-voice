# Irene — Release Plan

The single active tracker for the road to release. Supersedes the legacy `docs/TODO.md` +
`docs/TODO/TODO0x` (refactor-era, mostly complete — to be archived under DOC-2).

**Target:** _TBD_ · **Status:** reviving (paused ~Sep 2025, restarted May 2026) · **Version:** 15.0.0

## Definition of release (exit criteria) — _draft, refine_

> **Scope gate (Invariant #6):** release ships only when **every task tagged `[release]` is `[x]`**. Tasks default to
> `[release]` unless explicitly marked `[deferred]` (post-release). Run `scripts/check_scope.py` at each gate to prove
> nothing has drifted (orphan findings, dead links, contradictory status). The exit criteria below are the
> human-readable summary of that gate.

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
5. **Read review docs at START; record outcomes in the ledger + journal at COMPLETION — AFFIRMATIVE &
   NON-NEGOTIABLE until release.** _(Refined 2026-06-02 to a single status home — see Invariant #6.)_
   - **At task START:** read **not only the ledger item but also its related review doc(s)** (per the index below)
     for full context — the ledger item is a spine entry; the review doc holds the evidence, file:line refs, detail.
   - **At task COMPLETION:** flip status in **this ledger** and add a dated entry to **`RELEASE_JOURNAL.md`** —
     **in the same change.** Do **not** re-edit the review doc's status (it is frozen evidence carrying a one-time
     `→ tracked as <ID>` pointer). The **only** reason to edit a review doc is if a *finding itself* is wrong/obsolete
     — then annotate the finding (not a status flip). This kills the dual-status drift while keeping evidence honest.
6. **SINGLE TASK LEDGER (this file is the only source of scope + status).** Every release task has **exactly one ID
   here**; review/design docs may *surface findings* but **a finding is not scope until it has a ledger ID**. No task
   (or its status) lives only in a review doc. Each task is tagged **`[release]`** (must ship) or **`[deferred]`**
   (post-release); **release is blocked until every `[release]` task is `[x]`** (Definition-of-release gate). Run
   `scripts/check_scope.py` at each gate — it flags orphan findings (no ID), dead evidence links, and review-doc
   status markers that contradict the ledger.
7. **ONE JOURNAL.** `RELEASE_JOURNAL.md` is the **only** chronological log. No dated journals / "remediation round" /
   "status update" logs anywhere else (ledger or review docs). Journal entries reference task IDs but never assert
   their status.
8. **TASK-START RECONCILIATION — no stale, redundant, or mis-scoped work.** Tasks are interdependent (esp. the Gate-2
   foundational refactors QUAL-27/28/29, which will touch the surface of many later tasks). Before starting **any**
   task, reconcile it against current reality — **not just the ledger/review doc (Invariant #5), but also**:
   - **`RELEASE_JOURNAL.md`** — what actually landed since this task was written, and
   - **the code itself** — does the described problem still exist, unchanged, in the place the task assumes?
   - **Classify:** (a) **valid as written** → proceed; (b) **partially addressed** by prior work → narrow to the
     remainder; (c) **already fully addressed** → close as obsolete; (d) **scope drifted** (earlier changes moved the
     surface/approach) → redefine.
   - **For (b)/(c)/(d): STOP and consult the user** with the proposed scope change **before** doing the work or
     editing the ledger. **Never silently** proceed on stale work, or expand/shrink/close/redefine scope. On the
     user's approval, update the ledger (status/description) + add a `RELEASE_JOURNAL.md` entry recording the change.
   _Pairs with #5: #5 loads the context; #8 verifies the task is still the right task._
9. **NO `TYPE_CHECKING` / no `if TYPE_CHECKING:` import guards.** Imports are honest: if a type can be imported at
   runtime, import it at module top (plainly) and annotate with the real symbol — not a stringized forward ref behind
   a guard. A `TYPE_CHECKING` block is a **band-aid for an import cycle**, and a cycle is an architecture smell: it
   means dependencies don't point inward (Invariant #3). The fix is to **break the cycle** (move the shared type to a
   lower layer / use a port), not to hide it from the runtime. Hard third-party deps (e.g. `pydantic`, in
   `pyproject.toml`) are never optional, so guarding their imports is pure ceremony. When touching a file that has a
   `TYPE_CHECKING` block, remove it: hoist the import if there's no cycle, or fix the cycle if there is. _(Tracked as
   QUAL-32 for the residual repo-wide sweep; new code must comply from the start.)_

---

## Review documents (findings index)

Living findings behind the tasks (Invariant #5). `[x]` = exists; others are produced by their review task.

| Doc (`docs/review/` unless noted) | Covers | Backs |
|---|---|---|
| `phase0_static_baseline.md` `[x]` | static baseline: phantom refs, hidden type debt, dead code, layering | QUAL-1/2 ✓, QUAL-3/4/5/6, TEST-1 |
| `phase1_architecture_map.md` `[x]` | architecture map, doc-harmonization audit, hexagon target | ARCH-0 ✓, ARCH-1..8, ARCH-11/12, DOC-4/5✓/5b/6✓ |
| `fire_and_forget_review.md` `[x]` | F&F lifecycle + gap analysis (6 legacy issues re-validated) | QUAL-8 ✓, QUAL-9, TEST-3, DOC-4 |
| `parameter_extraction_review.md` `[x]` | text→parameters review + gaps | QUAL-10 ✓, QUAL-11, QUAL-35, TEST-4, DOC-7, UI-1/2/3, QUAL-22 |
| `text_processing_review.md` `[x]` | text-processor subsystem review + LLM-text-proc question | QUAL-12 ✓, QUAL-13, TEST-5 |
| `llm_usage_review.md` `[x]` | LLM usage + offline-first + NLU-LLM decision | QUAL-14 ✓, QUAL-15, QUAL-16 |
| `dataflow_review.md` `[x]` | full input→action flow map + defect hunt (~9 P0/~20 P1; gates Gate 2) | QUAL-25 ✓, QUAL-26 ✓, DOC-8 |
| `dataflow_reconciliation.md` `[x]` | QUAL-26 review-of-reviews — 10 intended-vs-today decisions + Gate 2 framing | QUAL-26 ✓ → QUAL-27..31, QUAL-9/11/13/15/16/22/23, ARCH-6/7, DOC-7/8 |
| `qual29_choices_decisions.md` | QUAL-29 interactive CHOICE canonical-model decisions (5 cases + parallel-set map + build plan) | QUAL-29 |
| `declared_param_audit.md` | audit: 19 declared-but-unconsumed donation params across 11 handlers (Bucket A dead / B bypassed) | QUAL-34, QUAL-11 |
| `streaming_api_review.md` `[x]` | AsyncAPI streaming-API tooling — Hybrid: replace renderer / keep+improve generator | QUAL-17 ✓, QUAL-18 |
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
- **This file = scope + status only.** Record what happened / decisions in **`RELEASE_JOURNAL.md`** (Invariant #7).
  Tag each task **`[release]`** or **`[deferred]`**; the release gate is "every `[release]` task `[x]`" (Invariant #6).

---

## Sequencing (phased roadmap — decided 2026-06-01)

The review wave (QUAL-8/10/12/14) is done. Its P0s are **not one species**: some are *surgical bug fixes*
(architecture-independent), some are *refactor-flavored* (they ARE subsystem architecture work). They sequence
differently. Key constraint: **there is no test safety net right now** (TEST-2 paused; full rewrite = TEST-7 later),
and the structural refactors **move code** — so blind refactoring/fixing is the main risk. Phases:

- **Gate 0 — verification net + cheap guard (do FIRST, before touching structure):**
  - **TEST-0** — a minimal end-to-end smoke harness (boot + a few real flows: command→intent, set a timer, extract
    a parameter). Small refactor safety net, **distinct from the TEST-7 rewrite**. It's the "wire-up integration
    test" all four reviews said is missing — would have caught every review P0.
  - **QUAL-23** — the startup-assertion ("every configured provider/stage/action name resolves to something real").
    Cheap; catches 3 of 4 review P0 *classes* (cascade names, console provider, dead stages) and stops regressions.
- **Gate 1 — structural foundation:** **ARCH-1** (split god-module) → **ARCH-2** (config↔core cycle) →
  **ARCH-4** (formalize ports) → **ARCH-5** (import-linter; folds in QUAL-23). **DOC-4** in parallel (pin the target).
  **✓ COMPLETE 2026-06-02.**
- **Gate 1.5 — dataflow review + reconciliation. ✓ COMPLETE 2026-06-02.** **QUAL-25** (full input→action flow map +
  defect hunt → `dataflow_review.md`, ~9 P0/~20 P1) → **QUAL-26** (review-of-reviews, live: 10 intended-vs-today
  decisions + finalized Gate 2 framing → `dataflow_reconciliation.md`). Surfaced a 4th cross-cutting theme
  (data-contract integrity) and emitted QUAL-27..31.
- **Gate 2 — the cross-cutting systemic remediation + review P0s (downstream of Gate 1.5; framing per QUAL-26):**
  - **Cross-cutting principles** (the lens; full text in the QUAL section): **① fail-loud** · **② shared bases** ·
    **③ config-truth (deployment-aware)** · **④ data-contract integrity**.
  - **Foundational tasks first:** **QUAL-27** (data-contract fixes; ✓ DONE) + **QUAL-28** (context & action-store
    refactor; ✓ DONE 2026-06-02) as the structural base → **QUAL-29** (donation format split; precedes declarative
    device-resolution) remains.
  - **Per-subsystem on top:** **QUAL-9** [FAF], **QUAL-11** [PEX], **QUAL-13** [TXTPROC], **QUAL-15** [LLM],
    **QUAL-16** [PROMPTS], **QUAL-22**, **QUAL-23** + **QUAL-30** (clarification Grade 1).
  - **Later / design-gated:** **QUAL-31** (slot-filling feature) · **ARCH-6** (WS ESP32 input) + **ARCH-7** (output
    seam / MQTT) design sessions · **DOC-7/DOC-8**.

**One-line rule:** *fix the data contracts and the context split first; the per-subsystem P0s ride that foundation.*

---

## Workstreams

### Architecture & Refactor (ARCH)
Target pattern: **Hexagonal (Ports & Adapters)** — SIGNED OFF 2026-06-01. Code is already ~80% there
(interfaces=ports, providers=adapters, components=app services, entry-points=registry).
See `docs/review/phase1_architecture_map.md` §5.
- [x] **ARCH-0** (P1) — Architecture MAP & document (Goal 1 doc-sync findings + Goal 2 pattern). → `docs/review/phase1_architecture_map.md`
- [x] **ARCH-1** (P0) — Split the `intents/models.py` god-module (in-degree 67). **DONE 2026-06-01** (`cdf8a81`
      audio, `a996dba` context). (1) `AudioData`/`WakeWordResult` → **`irene/utils/audio_data.py`** (zero-dep
      leaf), dropping the `audio_helpers.py` `TYPE_CHECKING` band-aid (real sideways import now). (2)
      `UnifiedConversationContext`/`ConversationState`/`ContextLayer` → **`irene/intents/context_models.py`**, with
      45 importers re-pointed; `Intent`/`IntentResult` stay in `intents/models.py` (thin audio shim retained).
      **Placement deviates from the review sketch (core/) on purpose — NO TYPE_CHECKING:** audio went to `utils`
      (not `core`) to avoid a `utils→core` upward edge; context stayed in the `intents` **domain** package (not
      `core`) because it references `Intent`/`IntentResult` (domain peers) — a real one-directional sideways import
      (`context_models→models`), no cycle, no band-aid. The remaining `core.{entity_resolver,trace_context,
      workflow_manager}→intents.context_models` edges are legitimate **application→domain** (inward) under the
      hexagon, not violations. Verified: no cycle, full suite unchanged (176/55, zero regression), TEST-0 green.
- [x] **ARCH-2** (P0) — Break config↔core / config↔components (SCC-1). **DONE 2026-06-01** (`59f4ae8` + `044ff62`).
      (A) `config/validator.py` discovers providers via `utils.loader.dynamic_loader` (config→utils, downward) —
      no more `from ..core.components import discover_providers` (which `core.components` didn't even export). (B)
      moved the 5 pure schema-extraction methods from `ConfigurationComponent` into `AutoSchemaRegistry` (their
      natural home) — `auto_registry` no longer imports the component; the component delegates downward. (C)
      removed the import-time `validate_schema_integrity()`/`validate_master_config_completeness()` calls from
      `config/__init__.py` (the side effect that amplified SCC-1 and spammed "Schema warning" on every `import
      config`) — now runs once, explicitly, from `ConfigManager.load_config`. (D) **dropped the `core/assets.py`
      `AssetConfig` TYPE_CHECKING band-aid** — `from ..config.models import AssetConfig` is a clean downward
      import now. Verified: no cycle, bare `import config` silent, validation still runs once on load, full suite
      unchanged (176/55, zero regression). **Gate 1: ARCH-3/4/5 next.**
- [x] **ARCH-3** (P1) — Stop components importing delivery/tooling. **DONE 2026-06-01** (`03fc44b`).
      **Edge 1 (code fix):** `asr`/`tts` components imported `web_api.asyncapi` (the `@websocket_api` decorator +
      `extract_websocket_specs_from_router`) — application→delivery. Moved `web_api/asyncapi.py` →
      **`irene/api/asyncapi.py`** (rank-0; its only irene deps were `__version__` + `api.schemas`, and its fastapi
      import was docstring-only), re-pointed all importers. **Components now import no `web_api` module** — the
      AsyncAPI mechanism is a neutral rank-0 port both sides depend on downward. **Edge 2 (classification, no code):**
      `components.nlu_analysis→analysis.*` — verified `analysis` is a **clean, self-contained driven adapter** (no
      inward imports into components/workflows/web_api), and `NLUAnalysisComponent` is its dedicated wrapper (the
      adapter boundary). Per the review's "treat analysis as a driven adapter", this is a legitimate
      application→driven-adapter relationship; a port for one-consumer tooling would be over-engineering. **ARCH-5
      import-linter rule:** forbid `components → web_api`/`analysis` generally, but **allow `nlu_analysis → analysis`**
      as the adapter boundary. Verified: full suite unchanged (176/55, zero regression), TEST-0 green.
- [x] **ARCH-4** (P2) — Formalize ports. **DONE 2026-06-02** (`df93a15`). Found a healthy **two-layer** port
      structure: component-capability ports (`core/interfaces/*Plugin`, implemented by components) + adapter ports
      (`providers/*/base.py *Provider`, inherited by adapters). **Audit:** adapter ports exist for all 7 categories
      and **no adapter imports a sibling concrete adapter** (adapters depend only on their abstraction ✓).
      **Gap-filled** (the 3 categories with no capability port): added `core/interfaces/{nlu,text_processing,
      voice_trigger}.py` (`NLUPlugin`/`TextProcessorPlugin`/`VoiceTriggerPlugin`, one `@abstractmethod` each typed
      with real domain types — **no TYPE_CHECKING**, cycle-verified) and made the 3 components inherit their port.
      (Chosen scope: capability-port gap-fill; the `*Provider` adapter ports stay in `providers/` — already clean.
      The bigger "unify the two hierarchies" move was considered and deferred as over-engineering for P2.) Verified:
      all 3 components instantiate + `isinstance` their port, no cycle, functional suite unchanged. **Gate 1: ARCH-5
      (import-linter) is the capstone next.**
- [x] **ARCH-5** (P1) — Add an **import-linter** contract so the hexagon is enforced and can't regress.
      **DONE 2026-06-02** (`27a85c3`). Added `import-linter` (dev dep) + `[tool.importlinter]` contracts in
      pyproject + `irene/tests/test_import_contracts.py` (runs them in the suite — enforced now; ready for CI when
      BUILD-2 lands). **6 contracts, 0 broken:** domain depends on nothing outward (ARCH-1); config no upward
      (ARCH-2); components no delivery + only `nlu_analysis→analysis` (ARCH-3); adapters no application + provider
      categories independent (ARCH-4). Residual fix (no TYPE_CHECKING): moved `RequestContext` (last
      domain→workflows edge) into `intents/context_models.py`. The linter **caught a real anti-pattern → QUAL-24**
      (8 handlers use `get_core()` service-locator; ignored in the domain contract with a comment, tracked
      separately). _The deliverable that makes "follows the architecture" verifiable._ **Gate 1 COMPLETE
      (ARCH-1..5 ✓).** _Note (2026-06-02): the `core→inputs/workflows/components.base` edges were left unenforced here
      as "composition-root behavior" — that reclassification is **REVOKED → ARCH-11** (fix via DI + add the contract)._
- [ ] **ARCH-6** [WS] (P1) — **REFRAMED by QUAL-26 (Q4): WebSocket streaming-input driving adapter — the primary
      ESP32 transport.** The dead `InputManager._input_queue` + base64 `AUDIO_DATA:` path (P0-8) is a broken
      placeholder to be **replaced by a proper WS streaming adapter**, not patched. Design (needs a **design session**):
      wake word runs **on-device (ESP32)** → device streams audio over WS (`skip_wake_word=True` server-side) → server
      ASR → pipeline; the WS connection also runs the **`ClientRegistry` registration handshake** (room +
      `available_devices`) — the linchpin that populates the Q6/QUAL-28 physical-identity store (resolves P1-j at its
      root). Also fix the contained `inputs.base ⇄ subclasses` cycle (SCC-2). Server-side voice-trigger (+ the
      `WakeWordResult` bug) is only for non-ESP32 local-mic. Intertwined with **ARCH-7** (the return channel: WS audio
      response to the ESP32 + MQTT smart-home actuation). → `docs/design/ws_esp32_transport.md`.
      **★ ROOM/DEVICE ACTIVATION POINT (Q1 timing decision, 2026-06-02):** this is *when the room/device story switches
      on.* QUAL-28/29/11 leave everything "room-ready" (action store + context split with device fields; declarative
      `entity_type`/`room_context`; device resolvers that degrade gracefully) — all keyed off a single
      **`resolve_physical_id(request)`** seam that today returns the session-derived id. **ARCH-6 changes only that one
      function** to return the registered `client_id`/room from the WS handshake, activating real room/device keying +
      device resolution with **no re-refactor**. Sequence: do ARCH-6's design session **after the Gate-2 foundation
      (QUAL-28/29/11) stabilizes**; it's one of the 3 design-gated threads (ARCH-6 [WS] · ARCH-7 [MQTT] · ARCH-9 [INFER]).
      **★ OWNS `entity_type`/`room_context` CONSUMPTION (moved from QUAL-11, user 2026-06-03):** QUAL-29 declared
      `entity_type` (device/location/room/person/generic) + `room_context` (required/none/conditional) but all 66 decls
      are `generic` and nothing reads them, so the declarative resolver swap would be an **inert branch** until there are
      real rooms/devices. ARCH-6 is where that becomes real, so it owns: **(a)** authoring the non-generic `entity_type`/
      `room_context` on the handlers that take device/room params; **(b)** replacing the brittle `_is_device_entity`/
      `_is_location_entity` name-heuristics (`entity_resolver.py`) with `entity_type`-driven resolver selection (the Q7b
      "typed accessor IS the replacement" swap — atomic, no broken window); **(c)** the `room_context` resolve-or-clarify
      policy (with QUAL-30). QUAL-11 left the seam clean (resolvers degrade gracefully; duplicate device path unified;
      `_resolution_failed` markers). Pairs with **QUAL-35** (T2/T3 NLU for the complex device commands MQTT needs).
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
- [ ] **ARCH-11** `[release]` (P1) — **Fix the `core → inputs/workflows/components.base` composition-root edges
      properly — REVOKES the ARCH-5 reclassification** (which deemed them "legitimate composition-root behavior" and
      left them unenforced; user reverses that 2026-06-02). Edges: `core.{engine,workflow_manager}→inputs.base`,
      `core.workflow_manager→workflows.base`, `core.components→components.base`. **Fix = invert via DI/ports:** the
      composition root (runners) injects concrete inputs/workflows/components into the core managers through
      `core/interfaces` ports, so `core` depends on abstractions, not concrete delivery/application modules. Then add
      **import-linter contract(s)** forbidding `core → inputs`/`workflows`/`components.base` (remove any exemption),
      satisfying the Definition-of-release "no backwards cross-layer imports" criterion. **Slot/sequencing: lands
      AFTER ARCH-6** (inputs become a proper WS driving adapter — the input-side DI seam) **and QUAL-28** (the
      `workflow_manager`/context refactor reshapes the `core→workflows` edge); ARCH-11 is the final hexagon-tightening
      that makes those two coherent and enforced. Refs: `phase1_architecture_map.md` §2.3 (core-orchestrating-outward
      row, "legitimize via DI"), §5 step 6.
- [ ] **ARCH-12** `[deferred]` (P2) — **Residual upward edges** (benign, no functional impact; not import-linter
      violations today). `utils.vad → core.metrics` (metrics should be a port injected into utils, or vad shouldn't
      emit metrics directly) and `utils.logging → config.models` (a `LogLevel` enum reach-up). Captured to close the
      single-ledger gap (Invariant #6) — these were the only findings living solely in a review doc
      (`phase1_architecture_map.md` §2.3). Deferred: do post-Gate-2 (or alongside ARCH-11) if cheap.

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
- [ ] **QUAL-18** [STREAMAPI] (P-TBD) — Act on QUAL-17 (per `streaming_api_review.md` §5): **(1)** vendor + wire the
      official `@asyncapi/web-component` at `/asyncapi`, delete the bespoke renderer (≈ −900 LOC); **(2)** fix the
      lossy `_clean_property_for_asyncapi` union/nullable handling; **(3, scoped separately)** emit AsyncAPI 3.0 +
      binary message bindings for ESP32 frames; **(4)** retire/repoint the docstring `x-` extension parser.
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
- [ ] **QUAL-24** (P2) — **Service-locator → DI in handlers (found by ARCH-5).** 8 intent handlers
      (`speech_recognition`, `audio_playback`, `voice_synthesis`, `system`, `conversation`, `provider_control`,
      `text_enhancement`, `translation`) fetch components via `from ...core.engine import get_core` →
      `core.component_manager.get_component(...)` — a service-locator that makes the **domain reach into the
      composition root** (transitively pulling components/inputs/workflows). Convert to **dependency injection**
      (inject the needed components via the existing handler-DI path, like the monitoring component injection),
      then **remove the `ignore_imports` exception** from the ARCH-5 domain contract so it enforces with no
      escape hatch. Domain-cleanliness; relates to ARCH-1.
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

#### Cross-cutting systemic remediation — principles (the Gate 2 lens)
_Apply to every remediation task below (from the 4 review docs + QUAL-25/26). Source: `dataflow_reconciliation.md`._
- **① Fail-loud** — raise structured exceptions → catch at ONE handler/orchestrator boundary → typed
  `IntentResult(success=False, error=…)`; **never swallow, guess a default, or return-original-on-failure.** The
  user-facing form is a **conversational clarification** (explain + ask), not an error dump; missing-required and
  no-intent both clarify. Backed by a **donation-driven typed accessor** (one place enforces required-vs-optional).
- **② Shared bases** — one NLU extraction base (donation-`ParameterSpec`-driven), one LLM prompt source (= the
  LLM-independent hardening layer), one normalization seam (contains the `lingua_franca`/`Runorm` debt), one F&F
  write-back, one result-construction contract. No copy-paste-then-diverge.
- **③ Config-truth (deployment-aware)** — every key is schema-known with **no dead trees** (consumed by *some*
  codepath in *some* profile) **and** every *enabled* component/provider/stage resolves to real code. `config-master`
  is a valid curated **superset**; deployment configs are minimal subsets — the check must not flag the superset.
- **④ Data-contract integrity** — a model field means **one thing end-to-end**; no rename residue
  (`Intent.text`/`raw_text`, `WakeWordResult.word`/`wake_word`, action key `action_name`/`domain`, session scope).
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
- [ ] **QUAL-31** [DFLOW] (P2, feature) — **Clarification UX — Grade 2 (multi-turn slot-filling).** `pending_clarification`
      on the conversation session + `ConversationState = awaiting-clarification` + a pipeline pre-check that fills the
      slot from the next turn and completes the original intent (symmetric to the F&F `contextual` check, but transient).
      Expires with the Q2 idle window. Follow-up to QUAL-30.
- [ ] **QUAL-32** `[release]` [QUAL] (P2) — **Purge `TYPE_CHECKING` import guards repo-wide (Invariant #9).** ~13 files
      still carry an `if TYPE_CHECKING:` block (`core/metadata.py`, `core/interfaces/webapi.py`, several
      `intents/handlers/*.py`, `utils/audio_helpers.py`, …). For each: if there's no real import cycle, hoist the import
      to module top and de-stringize the annotation; if there **is** a cycle, fix it at the architecture level (break
      the upward edge — move the shared type down / route via a port, per Invariant #3) rather than re-guard. Done when
      `grep -rn TYPE_CHECKING irene/ --include=*.py` returns nothing (outside prose/docstrings) and imports/smoke stay
      green. _Two files already cleared opportunistically (2026-06-02): `intents/handlers/conversation.py` + `timer.py`
      (the QUAL-28 touch surface)._
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
- [ ] **QUAL-35** `[release]` [PEX][MQTT] (P-TBD) — **Declarative NLU tiers T2 + T3 — MUST-HAVE for smart-home/MQTT
      (gated on ARCH-7/8). Split out of QUAL-11 (2026-06-03, user).** QUAL-11 deliberately shipped the **lightweight (T1)**
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
      (smart-home actuation) — complex device commands are unusable on T1 alone. Also activates the `entity_type`/
      `room_context` resolution authored under **ARCH-6**. Gated by Invariant #4 (any donation-schema change → config-ui;
      note the parked T2 pattern fields already exist, so no new schema surface unless extended). Refs:
      `parameter_extraction_review.md` (T2 = the "dead best mechanisms" themes 1+3), QUAL-11 (T1 baseline), Q6/Q7.
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

### Tests (TEST)
> **Strategy (decided 2026-06-01): do NOT keep repairing the existing suite.** Most tests were written against
> pre-refactor code and will be invalidated by the ARCH refactors (ARCH-1..5) and the code reviews (QUAL-8/10/12/14).
> Fixing them now is throwaway work. The TEST-1/TEST-2 pass already extracted the real value — it **proved the suite
> runs** and surfaced concrete prod findings (QUAL-21, QUAL-22, the text_processor trace fix). The current state
> (166 pass / 56 fail / 13 skip / 2 xfail, all committed) stands as a **partial safety net**; the remaining 56
> failures are left **intentionally unfixed**. The real test effort is **TEST-7: rewrite the suite after the
> architecture + code reviews land** (gated). TEST-3/4/5/6 are coverage goals folded into that rewrite.
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
- [x] **ASSET-3** (P2) — **DONE 2026-06-03 (with QUAL-13 Stage 1).** Migrated `lingua-franca` (abandoned MycroftAI git
      pin) → **`ovos-number-parser>=0.5.1`** (maintained OVOS successor, on PyPI, pure-Python → no armv7 wheel concern).
      Investigation found irene's real usage was tiny (`pronounce_number` + the stateless successor needs `lang=` per
      call, no global `load_language`) — confined to `irene/utils/text_processing.py`. **Russian now routes through the
      dependency-free in-repo pure-Python path** (`num_to_text_ru`/`decimal_to_text_ru` — better than ovos's literal
      "точка", and works on edge **without** the extra); non-ru uses ovos (degrades to raw digits if the optional extra
      is absent). `load_language` shim → no-op. Removed the dead git pin from `pyproject.toml` + lock; `ovos-date-parser`
      NOT added (irene needs no date parsing). _(Remaining: the 4 provider files' lingua-franca dep-hint strings are
      deleted with those providers in QUAL-13 Stage 2; examples still import lingua_franca — demo-only, harmless.)_

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
- [ ] **DOC-8** (P1) — **Data & context-models map** → `docs/guides/DATA_MODELS.md`. **Downstream of QUAL-25
      [DFLOW]** (re-categorized 2026-06-02): this is the *write-up* that distills the dataflow **review** into a
      concise developer reference; the investigation/findings now live in QUAL-25 → `docs/review/dataflow_review.md`.
      Do this **after** QUAL-25 lands, consuming its map + confirmed model lifecycle. A concise reference for how
      the pipeline's models play together — **when each is needed and why** (the request-scoped vs session-scoped
      distinction is the key confusion to resolve). Cover the cast + responsibilities: **`RequestContext`**
      (per-*request* input metadata — source, session_id, wants_audio, skip flags, client/room/device, language;
      created at the entry by the runner/web/cli) · **`UnifiedConversationContext`** (persistent per-*session* state
      — history, active/recent/failed actions, devices, `ConversationState`, `ContextLayer`; keyed by `session_id`,
      fetched via `ContextManager`) · **`Intent`** (NLU output) · **`IntentResult`** (handler output) ·
      **`AudioData`/`WakeWordResult`** (IO primitives). Document the **lifecycle**: `RequestContext` →
      `ContextManager.get_context(session_id)` → `UnifiedConversationContext` → `NLU → Intent` →
      `orchestrator.execute → IntentResult` → `context.add_to_history(...)`. State where each now lives post-ARCH-1/5
      (`intents/context_models.py`, `intents/models.py`, `utils/audio_data.py`). DOC-4 links to it. Refs:
      `phase1_architecture_map.md` §4.

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
- [ ] **UI-4** [WORKFLOWVIZ] (P-deferred) — A config-ui **"Workflow Control" / pipeline-visualization page** (live
      React-Flow DAG of the component/provider pipeline, per-stage input/output inspection, provider switching, SSE
      updates). **Source design archived** at `docs/archive/workflow_control.md` (Sep-2025, never built). **Strongly
      gated — do NOT start before Gate 2:** the design assumes a clean pipeline, but QUAL-25 proved the real dataflow
      is broken at many hops (visualizing it now would faithfully render broken flow), and it specs `/workflow/*`
      endpoints that `architecture.md` §7 flags as **fictional** (they'd have to be built for real). Relates to the
      `MonitoringPage` placeholder and the **ARCH-7 [MQTT]** output-seam work (both touch live pipeline observability).
      Re-scope against the *fixed* pipeline + real endpoints when it's actually picked up. Captured from a config-ui
      doc reviewed during QUAL-25 (2026-06-02).
- [ ] **UI-5** `[release]` [DEDITOR] (P1) — **Rebuild the donations editor on the v1.1 split model (config-ui;
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
      DoD: `cd config-ui && npm run type-check && npm run build` passes + the editing page round-trips contract +
      phrasing. **This is the remaining Invariant #4 obligation deferred from QUAL-29 (user-approved 2026-06-03).**

### Release Readiness (REL)
- [ ] **REL-1** (P0) — Sign off the Definition-of-release checklist above (fill target + criteria).
- [ ] **REL-2** (P1) — `config-example.toml` + quickstart finalization (the release-time config story).
- [ ] **REL-3** (P1) — Version bump / changelog / tag.

---

_**Chronology lives in [`RELEASE_JOURNAL.md`](./RELEASE_JOURNAL.md)** — this file is the task ledger only
(scope + status). Findings/rationale: `docs/review/*` + `docs/design/*`._
