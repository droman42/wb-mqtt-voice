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
   - Definition-of-done addendum for such tasks: `cd config-ui && npm run check && npm run build` passes
     (`check` = type-check **+** the strict ESLint gate, harmonized with `../wb-mqtt-bridge/ui` in UI-6).
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
| `esp32_wakeword_review.md` `[x]` | ESP32 + wakeword keep/fix/cut + microWakeWord upstream study | QUAL-19 ✓, QUAL-20 ✓ |
| `docker_build_review.md` `[x]` | Docker/build verification (entry-point renames, armv7 base, build-analyzer drift) | BUILD-5, BUILD-3 |
| `docs/design/mqtt_integration.md` `[x]` (DONE 2026-06-06; bridge contract AGREED) | smart-home integration — bridge is the single device authority, Irene speaks canonical commands | ARCH-7/8 |
| `docs/design/ws_esp32_transport.md` `[x]` | WS streaming-input driving adapter + ESP32 satellite transport | ARCH-6 |
| `docs/design/onnx_inference_layer.md` `[x]` (complete 2026-06-04; ASR/platform/build + VAD/wake-word all resolved) | shared sherpa-onnx inference layer — ASR-centric; WB7 armv7 feasibility proven on hardware | ARCH-9/10 |
| `docs/design/io_architecture.md` (DRAFT 2026-06-07) | symmetric configurable hexagonal I/O — format-vs-input, OutputPort + modality matrix, daemon multiplexing, event-bus delivery+observation, F&F via OutputManager, runners-as-presets | ARCH-14/15 |
| `docs/design/audio_pipeline.md` `[x]` (2026-06-10) | audio I/O negotiation+transformation seam (input twin of ARCH-15) — VAD provider family, canonical transform-once + derived/fatal negotiation, pre-roll contract, AudioTranscoder/VoiceSegmenter/AudioNegotiator, symmetric in+out, traced | ARCH-17 ✓, ARCH-18 |
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
- [x] **ARCH-6** [WS] (P1) — **DONE 2026-06-03 (transport + identity activation + SCC-2); device-half relocated to QUAL-35.**
      Built the **WS streaming-input DRIVING adapter** `/ws/audio` (`webapi_router.py`): registration handshake →
      `ClientRegistry` → stream raw PCM → **full** pipeline (`process_audio_input`, `skip_wake_word=True` since wake is
      on-device) → response frame. The handshake threads `client_id`/`room_name`/`device_context` into `client_context`,
      so **`resolve_physical_id` now returns the physical origin** (room/device) — the "room/device story switches on"
      with no seam rewrite (it already returned `client_id or room_name or session_id`). Made `ClientRegistration.from_dict`
      tolerant of the handshake's control keys. Removed the dead P0-8 base64 `AUDIO_DATA:` branch (`inputs/web.py`).
      Design: `docs/design/ws_esp32_transport.md` (server-first; the in-repo ESP32 firmware is stale → inspiration only).
      Tests: `test_ws_driving_input.py` (3 — activation seam, from_dict, end-to-end handshake→pipeline via TestClient).
      **Deferred (device-half → relocated to ARCH-7 [MQTT] + QUAL-35):** authoring non-generic `entity_type`/`room_context`
      + the `_is_device_entity`/`_is_location_entity` resolver swap + room_context resolve-or-clarify — at design time NO
      device/room handlers exist (all 13 `entity_type` decls `generic`; no MQTT handler), so doing it now = the ledger's
      own "inert branch". **SCC-2 cycle FIXED (not via service-locator — cf. QUAL-24):** the cycle was `inputs.base` (the
      `InputSource` PORT) co-located with the `InputManager` ORCHESTRATOR that imports the concrete adapters. Split them —
      `InputManager` → new `irene/inputs/manager.py` (the input-layer composition point, imports adapters explicitly); the
      port module now imports NO adapters. Clean DAG `base ← {cli,web,microphone} ← manager`; **locked by a new
      import-linter contract** ("Input port does not import its adapters"). _Original
      reframing below._ The dead `InputManager._input_queue` + base64 `AUDIO_DATA:` path (P0-8) is a broken
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
- [x] **ARCH-7** [MQTT] — **✓ DONE 2026-06-06** (design session; deliverable `docs/design/mqtt_integration.md`, and the
      cross-project bridge contract AGREED with the user in the bridge session — `wb-mqtt-bridge/docs/
      voice_integration_contract_draft.md`, status AGREED 2026-06-06). **Approach REDEFINED (Invariant #8(d), approved):**
      replaced the original "Irene owns an MQTT output adapter + topic schema + device-topic resolution" with
      **bridge-as-single-authority** — `wb-mqtt-bridge` owns all device knowledge + MQTT/home-automation conventions
      (native WB gear *and* AV); **Irene is a pure voice front-end** that pulls a capability-shaped **catalog** and sends
      **canonical `DeviceCommand`s** (capability.action+params); the bridge translates to native + transport. Irene is
      blind to wb-rules vs Home Assistant. Rejected: Irene→raw-broker, and the archived `intent_mqtt.md` fat-handler/
      runtime-method-gen design. **Agreed contract:** (A) `POST /devices/{id}/canonical {capability,action,params}`, 6-code
      structured error enum, 500 ms synchronous value-topic echo; (B) `GET /system/catalog` (dedicated, flat, all-locales
      rooms+devices, read-only `sensor` capability, one-device-one-room [`global` = room of whole-house AGGREGATE
      devices, e.g. `all_lights`; "выключи свет везде" = Irene fires ONE command at that aggregate device, never iterates
      rooms / synthesizes a group]) + retained
      `bridge/catalog/version` refresh nudge; (C) bridge-side native onboarding (generic `WbPassthroughDevice` driver +
      capability-adapter composition + caps `brightness`/`color`/`cover`/`climate`/`sensor`; wb-rules stays, bridge mirrors
      state). **Hexagon (Irene):** `DeviceCommand` + `ActuationPort`/`DeviceCatalogPort` (QUAL-24 ABC pattern) +
      `BridgeClient` REST adapter under a new `irene.providers.outputs` group + in-memory `DeviceCatalog` (distinct from
      `ClientRegistry`). Substrate for **QUAL-35** (T2/T3 device NLU + the relocated `entity_type`/`_is_device_entity`→
      declarative resolver swap). Implementation = ARCH-8. **Design extended 2026-06-07 (ARCH-15 PR-9.1):**
      `mqtt_integration.md` §13 reconciles the seam shapes with the I/O architecture (bridge = `OutputPort`, see ARCH-8).
- [ ] **ARCH-8** [MQTT] (P-TBD) — **UNBLOCKED 2026-06-06** (contract AGREED); **RECONCILED with the I/O architecture
      2026-06-07 (ARCH-15 PR-9.1) — build against `mqtt_integration.md` §13**: bridge actuation is a **request/response
      `OutputPort`** returning the rich `DeliveryResult` (echo/error), `device_command` is a delivery **modality**
      capability-routed to the `designate(DEVICE_COMMAND,"bridge")` output, `DeviceCatalogPort` stays a read port, Flow-1
      event is a terminal `OutputPort`; the `ActuationPort` ABC is **dropped** (the bridge IS an OutputPort). ARCH-8 thus
      stands on PR-2 (`OutputPort`/`DeliveryResult`), PR-5a (process-wide OutputManager), D-2 (designated routing) — all
      landed; actuation is observable on the event bus (PR-6b) for free. Implement per
      `docs/design/mqtt_integration.md` §10 **as amended by §13**, against the agreed bridge contract, aligned to the **vertical slice**
      ("включи свет в детской", one `wb-mr6c` channel): **PR-1** `DeviceCommand` + `ActuationPort`/`DeviceCatalogPort` +
      application services (adapter-free, fake bridge — **can start now**); **PR-2** `BridgeClient` REST adapter +
      `irene.providers.outputs` group + config/schema + `GET /system/catalog` pull → `DeviceCatalog` + `bridge/catalog/
      version` subscribe; **PR-3** wire `DeviceCatalog` into `DeviceEntityResolver` (real device/room entities, ru-name
      match — ARCH-6 device-half, with QUAL-35); **PR-4** reference device handler end-to-end (`power.on` → canonical →
      echo → spoken confirm + error-code→speech + `param_invalid`→clarify); **PR-5** sensor read (`GET /devices/{id}/state`).
      (No "everywhere" fan-out — "выключи свет везде" = an Actuate against the `global` `all_lights` aggregate device, on
      PR-4's path.) PR-2+ integrate as the bridge's slice comes online. Broad
      device coverage + T2/T3 NLU = QUAL-35.
- [x] **ARCH-9** [INFER] — **✓ DONE 2026-06-04** (design deliverable `docs/design/onnx_inference_layer.md` complete; all
      open questions resolved — sherpa one-provider ASR, WB7 armv7 feasibility proven on hardware, two build corrections,
      AssetManager+warm-up, contribution-principle invariant, and VAD+wake-word for **both** scenarios: WB7=ESP32-satellite
      delegated, standalone-64bit = two mutually-exclusive wake-word providers + two mutually-exclusive VAD impls.
      Implementation = ARCH-10, sliced into PR-1..5 in §12). — **Design session** (needs live collaboration): a **shared sherpa-onnx (k2-fsa)
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
- [~] **ARCH-10** [INFER] (P-TBD) — Implement per ARCH-9, sliced PR-1..5 (design §12). **PR-1/2/3/4 DONE 2026-06-04**
      (`6e1a88a`, `b373633`, `4902438`, `b5dd978`): (PR-1/2/3) `sherpa_onnx` ASR provider alongside vosk/whisper —
      **three families on one runtime via `model_type`**: `vosk-transducer` (`from_transducer`) + `whisper`
      (`from_whisper`, no joiner) + `vosk-streaming` (`OnlineRecognizer`, real incremental `transcribe_stream` w/ endpoint
      segmentation). numpy-free PCM/WAV→float (armv7-safe); `SherpaInferencePolicy`; **AssetManager member-aware
      multi-file model-pack download** (HF; transducer=4/int8, whisper=3, streaming=chunk64); `asr-onnx` extra w/ arch
      markers; Invariant #4 via `SherpaOnnxASRProviderSchema`. (PR-4) **VAD engine seam** — `VADEngine` ABC port +
      `energy` (existing, unchanged) / `silero` (SileroVAD-ONNX via sherpa-onnx) **toml-selected, mutually exclusive**,
      64-bit only; hexagon-clean (workflows injects the asset path; utils stays core-free per ARCH-12 #9); 11 seam tests.
      29 unit tests total; 0 net suite regressions. **PR-5 wake-word — SUBSUMED BY QUAL-20 (2026-06-09, per QUAL-19).** The wake-word greenfield is now owned end-to-end
      by QUAL-20 (fix backend µWW via `pymicro-wakeword` + openWakeWord polish + uniform `WakeWordSpec` + server-side
      microVAD + cut Porcupine + armv7 config). ARCH-10's residual scope here is closed; see `esp32_wakeword_review.md`.
      _Original PARKED note (2026-06-04) retained for history:_ Reconciliation
      (contradicts the design's "both hallucinated" premise): **`openwakeword` is functional** (real upstream model URLs,
      real `predict()`, English catalog) — *not* a stub; **`microwakeword` is the real stub** (`_extract_features` returns
      `np.random`, hallucinated `*_v1.0` catalog, 404 model URL, training removed `886d4d1` — QUAL-19); **Porcupine** =
      dead code (schema/config, no impl). **Decision pending:** microwakeword (A) implement-real+experimental / (B)
      cut-archive per QUAL-20 / (C) thin; + openwakeword polish (extra split `wake-onnx`/`wake-tflite`, ONNX default,
      custom `model_path` for a trained RU wake word, build-contract fix, cut Porcupine). **Flag — RESOLVED
      2026-06-10:** `import sherpa_onnx` failed on x86_64 (`libonnxruntime.so` not found) because sherpa-onnx
      **≥1.13 split its native libs (onnxruntime + C-API) into a separate `sherpa-onnx-core` wheel** that the
      `asr-onnx` extra wasn't pulling — so only armv7 (self-contained 1.10.46) worked. Fixed by adding
      `sherpa-onnx-core>=1.13; platform_machine!='armv7l'` to the extra; `import sherpa_onnx` now succeeds on
      x86_64 (verified). (sherpa vendors libasound; needs no system packages — the ALSA in
      `get_platform_dependencies` is a runtime safety net, owned really by the audio-I/O providers.) Wheel
      matrix verified: sherpa works on armv7/x86_64/aarch64/win/macos; pymicro-wakeword on all but armv7;
      pymicro-vad on Linux x86_64/aarch64 only (extras now carry honest markers). WB7 hardware re-validation
      deferred to ARCH-10 completion (user).
      Build/Docker corrections = BUILD-5/3.
- [x] **ARCH-11** `[release]` (P1) — **DONE 2026-06-03 (S1-S4, commits 64c4050·0453b12·b64be87·+S4).** Inverted all 4
      `core → inputs/workflows/components.base` composition-root edges + locked them with the import-linter contract "Core
      does not import the outer layers (ARCH-11)" (8th contract; teeth-checked: a planted `core→inputs` import breaks it).
      Decision (c) applied (input/Component/Workflow ports rooted on `EntryPointMetadata` in `core/interfaces`); all manager
      construction moved to `runners/composition.build_core`; `RequestContext` imported inward from domain. Legacy
      `irene/plugins/` teardown + `PluginInterface` removal remain split to **ARCH-13** (core→plugins incidentally already
      clean). 8/8 contracts kept, suite 85=85 FAILED (0 net regression across all 4 stages). _Original plan retained below._
      **Fix the `core → inputs/workflows/components.base` composition-root edges
      properly — REVOKES the ARCH-5 reclassification.** _**Reconciled + decisions locked 2026-06-03 (ready to execute as a
      staged refactor):**_ prerequisites met (ARCH-6 ✓, QUAL-28 ✓). **4 edges:** (1) `workflow_manager→inputs.base.
      InputSource` (type in 3 sigs); (2) `core/components.py→components.base.Component` (24× type/TypeVar/isinstance);
      (3) `workflow_manager→workflows.base.{Workflow,RequestContext}` — note `RequestContext` actually lives in
      `intents/context_models.py` (domain), only re-exported by workflows.base → core can import it directly (inward);
      (4) `engine.py→inputs.manager.InputManager` (**construction**). **User decisions:** edge-4 construction → **move
      ALL manager construction (Component/Input/Workflow) out of `AsyncVACore` into the runners/a composition module**
      (purest; touches every runner); input abstraction → **consolidate `InputSource`+`InputPlugin` into ONE port**.
      **★ HIERARCHY-FORK DISCUSSION — RESOLVED 2026-06-03 (decision locked):** the two parallel base hierarchies were
      `EntryPointMetadata` (class-level discovery/build/asset metadata; the **live** base of `Component`/`ProviderBase`/
      `InputSource`/`Workflow`/`IntentHandler`) vs `PluginInterface` (instance-level lifecycle `name`/`version`/`initialize`/
      `shutdown`; base of the `core/interfaces/*` capability ports). **Investigation finding:** `PluginInterface` is a
      **near-dead legacy skin** — the capability ports (`ASRPlugin`/`TTSPlugin`/`InputPlugin`/…) have **0 concrete
      subclasses** (used only as MI mixins alongside `Component`, e.g. `class ASRComponent(Component, ASRPlugin, WebAPIPlugin)`,
      or as `isinstance` markers); `core/interfaces/input.InputPlugin` is a **dead duplicate** of `inputs.base.InputSource`
      (0 readers); and the whole `irene/plugins/` system (`BasePlugin`/`AsyncPluginManager`/`PluginRegistry`) is **dormant** —
      `engine.py:95` calls `load_plugins()` with no paths → the builtin branch is `pass` → **verified loads exactly 0 plugins**
      (`_plugins` stays `{}`; all status endpoints reading `core.plugin_manager._plugins` report 0). **DECISION (c):** retire
      `PluginInterface` and re-root all ports onto the single clean base `EntryPointMetadata` (imports only abc+typing → zero
      outward deps; the `core/interfaces` port layer is already import-clean). This gives clean dependency *direction* +
      enforceable import-linter contracts. _Two acknowledged asterisks (not direction violations, so contracts stay green):_
      `EntryPointMetadata` remains a "fat" root (conflates capability with build/packaging metadata — purist split deferred,
      gold-plating for Gate 2); and ARCH-12's residual upward edges survive until ARCH-12.
      **DECISION (scope) — STAGE THE TEARDOWN.** Full (c) (deleting `PluginInterface`) would *force* touching the legacy
      system (its `AsyncPluginManager`/`BasePlugin`/registry are typed on `PluginInterface`), and that legacy manager is read
      via the QUAL-24 service-locator pattern (`getattr(core, 'plugin_manager')._plugins`) at **~8 status/debug/health sites**
      (`runners/cli.py:369`, `runners/base.py:388`, `webapi_runner.py:406`, `webapi_router.py` ×6, `core/components.py:276`).
      To keep ARCH-11 a single-purpose, bisectable hexagon commit right before Gate 2, the legacy teardown is **split to
      ARCH-13**. **ARCH-11 scope:** invert the 4 edges + re-root the capability ports onto `EntryPointMetadata` +
      consolidate the input port (delete the dead `core/interfaces/input.InputPlugin`, land `InputPort` in `core/interfaces`
      that `core` imports inward and `inputs/` adapters implement) + add the import-linter contracts. **ARCH-13 scope (filed):**
      remove the dormant `irene/plugins/` system, complete `PluginInterface`'s deletion, and rewire the ~8 service-locator
      status readers (all currently report 0). **Staging (each leaves a working app):** S1 input-port consolidation +
      re-root onto EntryPointMetadata · S2 Component+Workflow ports in `core/interfaces` + core imports them · S3 construction
      inversion (managers→composition/runners, AsyncVACore port-typed) · S4 import-linter contracts forbidding
      `core→{inputs,workflows,components}.base` + remove the ARCH-5 exemptions. **Progress: ✓ S1 DONE 2026-06-03** —
      consolidated the input port into `core/interfaces/input.InputPort(EntryPointMetadata)` (+`InputData`); deleted the
      dead `InputPlugin` and stripped its dormant refs from `plugins/manager.py`; adapters (cli/microphone/web) + `InputManager`
      now implement/type against `InputPort`; `inputs/base.py` reduced to the adapter-side `ComponentNotAvailable`;
      `workflow_manager.py` imports the port inward (`core→inputs.base` input edge **removed** — 1 of 4 edges done). Verified:
      import-linter 7/7 kept (SCC-2 contract holds), suite 85=85 FAILED (0 net regression). **✓ S2 DONE 2026-06-03** — added
      thin ABC ports `core/interfaces/component.ComponentPort` + `workflows`-side `core/interfaces/workflow.WorkflowPort`
      (both `EntryPointMetadata`-rooted, declaring only the generic manager-facing surface; component-specific methods like
      TTS `synthesize_to_file` stay duck-typed as today). Fat bases now implement them (`Component(ComponentPort)`,
      `Workflow(WorkflowPort)`); `core/components.py` + `core/workflow_manager.py` type against the ports (incl. the runtime
      `issubclass(WorkflowPort)` discovery gate); `RequestContext` now imported inward from `intents.context_models` directly.
      **Edges 2 & 3 removed** (`core→components.base`, `core→workflows.base` — verified zero remaining core imports of either).
      3 of 4 edges done. Verified: import-linter 7/7 kept, suite 85=85 FAILED (0 net regression). **✓ S3 DONE 2026-06-03** —
      construction inversion. New composition root `irene/runners/composition.build_core(config, config_path)` constructs ALL
      7 managers (component/plugin/input/context/timer/metrics/workflow) and injects them into `AsyncVACore`, whose `__init__`
      is now keyword-only DI and constructs nothing. `engine.py` no longer imports `inputs.manager` (**edge 4 removed**) nor
      `plugins.manager` (bonus — `core→plugins` gone, eases ARCH-13); the two outward managers are typed `Any` in core to keep
      the edge out. Single production call site `runners/base.py` + the 2 `examples/` demos route through `build_core`.
      **ALL 4 EDGES REMOVED.** Verified: zero `core→{inputs,plugins}` imports, `build_core` assembles a working core,
      import-linter 7/7 kept, suite 85=85 FAILED (0 net regression). **✓ S4 DONE 2026-06-03 — ARCH-11 COMPLETE.** Added the
      8th import-linter contract "Core does not import the outer layers (ARCH-11)" (`source=irene.core`, forbidden
      `irene.{inputs,workflows,components}`). No literal ARCH-5 exemptions existed to remove — ARCH-5 left these edges
      *unenforced* (added no contract), so adding the contract IS the revocation. Teeth-checked (planted `core→inputs`
      import → BROKEN; reverted → 8 kept). 8/8 contracts kept, contracts-test green, suite 85=85 FAILED (0 net regression).
      _Original below._
      (which deemed them "legitimate composition-root behavior" and
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
- [x] **ARCH-12** `[release]` (P2) — **DONE 2026-06-03.** Removed both residual upward edges + locked utils with a 9th
      import-linter contract. **Edge 1** (`utils.vad → core.metrics`): turned out to be a **dead import** —
      `get_metrics_collector` was imported but never called (Phase-4 leftover after VAD metrics unified into
      `MetricsCollector`); deleted it. **Edge 2** (`utils.logging → config.models`): the `LogLevel` enum (a standalone
      5-value enum) was **relocated into `utils.logging`** and re-exported from `config.models` — so the edge inverts to
      `config → utils` (downward, allowed) while every `from config.models import LogLevel` keeps resolving; dropped the
      now-dead `from enum import Enum` in `config.models`. Added contract **"Utils (foundation) depends on nothing upward
      (ARCH-12)"** (`source=irene.utils`, forbids core/config/components/intents/workflows/inputs/providers/runners/web_api)
      — teeth-checked (planted `utils→config` → BROKEN). Verified: no cycle, 9/9 contracts kept, suite 85=85 FAILED (0 net
      regression). Closes the last `phase1_architecture_map.md` §2.3 backwards-edge findings.
- [x] **ARCH-13** `[release]` (P2) — **DONE 2026-06-03.** Retired the dormant `irene/plugins/` legacy system. Re-rooted
      the **8 capability ports** (`ASR/TTS/Audio/LLM/NLU/TextProcessor/VoiceTrigger/WebAPI Plugin`) off `PluginInterface`
      onto `EntryPointMetadata` (completing decision (c) — MRO smoke-checked: the `Component`+port diamond resolves, real
      components instantiate); **deleted** `irene/plugins/` (`AsyncPluginManager`/`BasePlugin`/`PluginRegistry`/`builtin/`)
      + `core/interfaces/plugin.py` (`PluginInterface`/`PluginManager`); stripped the plugin lifecycle from `engine.py`
      (init/load/unload calls + the injected `plugin_manager` param) and its construction from `runners/composition`;
      rewired the **~8 service-locator status readers** (`cli.py`/`base.py` dropped the "Plugins loaded" line; `webapi_router`
      ×4 + `webapi_runner` plugin blocks removed; `components.py` service-map entry dropped) — all reported 0; cleaned the
      dead `irene.plugins.builtin` refs in `build_analyzer.py`. `core→plugins` was already clean (ARCH-11/S3 byproduct).
      Verified: all modules import, 8/8 contracts kept, suite 85=85 FAILED (0 net regression), no live refs to retired
      symbols remain (only provider docstrings note the historical paths). _Original below._ Retire the dormant
      `irene/plugins/` legacy system (split out of ARCH-11,
      2026-06-03). **Verified dead:** `engine.py:95` calls `AsyncPluginManager.load_plugins()` with no paths → builtin
      branch is `pass` → loads **exactly 0 plugins** (`_plugins == {}`); there is no `irene.plugins` entry-point group in
      `pyproject.toml`. **Scope:** (1) delete `irene/plugins/` (`manager.py` `AsyncPluginManager`, `base.py` `BasePlugin`,
      `registry.py` `PluginRegistry`) + the `engine.py:56/84/95/127` lifecycle wiring; (2) complete the removal of
      `core/interfaces/plugin.PluginInterface` begun in ARCH-11 (after the capability ports re-root onto `EntryPointMetadata`,
      `PluginInterface` has no remaining subclasses); (3) rewire the **~8 service-locator status readers** that introspect
      `core.plugin_manager._plugins`/`.plugin_count` (`runners/cli.py:369`, `runners/base.py:388`, `webapi_runner.py:406`,
      `webapi_router.py` ×6, `core/components.py:276`) — all currently report 0, so they become either a removed field or a
      report sourced from the real component/handler registries. **Why split from ARCH-11:** keeps the hexagon-inversion
      commit single-purpose and bisectable before Gate 2; the status-endpoint regression surface here is verified in
      isolation. Same DI/anti-service-locator family as QUAL-24. Slot: AFTER ARCH-11; post-Gate-2 acceptable.
- [x] **ARCH-14** [IO] (P-TBD) — **DESIGN — symmetric, configurable, hexagonal I/O architecture; deliverable
      `docs/design/io_architecture.md` (DRAFT 2026-06-07, design session with user).** Triggered by a CLI bug
      (`irene.runners.cli` interactive silently swallows typed lines — two concurrent `prompt_toolkit.prompt()` readers race
      for the same TTY: the runner's own `_run_interactive_loop` vs the auto-started `CLIInput._input_loop` whose
      `_command_queue` nobody drains), which exposed three structural gaps: input consumption is ad-hoc per-runner (the
      `InputManager._input_queue` "Command Queue" of `architecture.md` §5.1 is dead-by-decision, `dataflow_reconciliation.md`
      Q4/P0-8; every runner bypasses it); there is **no output abstraction at all** (`irene/outputs/` does not exist;
      async/F&F output hard-wires the one global TTS/audio sink, `notifications.py:377-380`); and the system assumes exactly
      one input + one output (hence one mutually-exclusive runner per channel). **Design decided (consolidated from the
      user's 5-point brief — supersedes the earlier A/B framing, both of which were too narrow):** (1) **format vs input**
      are orthogonal — *format* (`text`/`audio`) selects the workflow entry stage, *input* is the capture mechanism;
      many-to-many. (2) **Output is the symmetric twin** — TOML-configurable `[outputs]`, the output adapter drives delivery
      format, channel-paired, governed by a **modality/capability matrix** with degrade-then-drop negotiation; subsumes
      ARCH-7 Flow 1/Flow 2 as ordinary outputs. (3) **One daemon multiplexes many concurrent inputs+outputs** with runtime
      attach/detach; routing-by-origin mandatory. (4) **One pipeline event bus, two subscriber kinds** — OutputManager
      (delivery, origin-addressed) + observers (read-only tap, identity-filtered, gated) — reusing the existing `/trace`
      vocabulary; supports the operator's reproduce-AND-observe-live debug scenario. (5) **F&F is not special** — ack +
      deferred notification both route through OutputManager (sync/ack → live connection; deferred → **persistent physical
      identity** via `resolve_physical_id`, so a kitchen timer announces in the kitchen after session eviction);
      `NotificationService` demoted deliverer→producer. (6) **Runners → thin config-preset launchers** (kept as convenience +
      config-override via layering `flags>preset>file>defaults`; the double-reader bug becomes structurally impossible).
      Spine = the already-built session-vs-identity split (QUAL-28) + `resolve_physical_id`. **Decisions D-1..D-6 LOCKED
      2026-06-07** (§10): D-1 3-value format enum (`voice`/`audio`/`text`); D-2 modality-routed (conversational→origin-paired,
      actuation/event→designated, +opt-in broadcast); D-3 drop+log+history with bounded reconnect for persistent targets;
      D-4 delete REPL meta-commands → existing `system.*` intents; D-5 authenticated-WS tap, shared-token, localhost-first;
      D-6 **MQTT/bridge actuation = just another output channel** via `OutputPort.deliver()->DeliveryResult` (rich echo for
      the bridge, bounded await), `ActuationPort`→bridge `OutputPort`, `DeviceCatalogPort` stays a read port. Implementation =
      **ARCH-15** (sliced PR-0..9, design §12). Refs: `io_architecture.md`, ARCH-6 (WS driving-adapter template), ARCH-7/8
      (output seams — reconciled by ARCH-15 PR-9), QUAL-28 (identity), `dataflow_reconciliation.md` Q2/Q3/Q4.
- [x] **ARCH-15** [IO] (P-TBD) — **DONE 2026-06-07 — the I/O hexagon is fully delivered (PR-0..9).** Symmetric
      configurable hexagonal I/O per `docs/design/io_architecture.md`: input `format` first-class; `OutputPort`/
      `OutputManager`/`DeliveryResult` + modality routing/negotiation; pipeline `EventBus`; F&F delivery + observation
      tap + web-app push, all identity-addressed; config-driven `[outputs]`; local audio/voice SPEECH output (pure D-3);
      ARCH-7 reconciled (§13) to feed ARCH-8; master-config completeness extended. **PR-10 DEFERRED → ARCH-16** (daemon
      multiplexer + runners→thin presets + remote text-attach channel — a large internal refactor of low incremental
      user value; the working system already runs all channels and the webapi process already hosts concurrent WS
      channels; decision 2026-06-07 to consider the hexagon complete rather than rush it). Minor follow-ons also in
      ARCH-16: the PR-6c web-app JS render + the PR-7 capability-matrix display. _Slice log below._
      **PR-0 ✓ DONE 2026-06-07** CLI double-reader stopgap — stopped auto-starting `cli` in
      `InputManager._auto_start_configured_sources` (`inputs/manager.py`; the source stays registered in `_sources`, just not
      started), mirroring the existing `web` guard; the runner's own `_run_interactive_loop` is now the sole stdin reader, so
      typed lines stop being swallowed by the competing `CLIInput._input_loop` (whose `_command_queue` had no consumer).
      `irene/tests/test_input_manager_autostart.py` (2) guards it. Design-compatible; superseded by PR-5. **PR-1 ✓ DONE 2026-06-07** `InputFormat` enum
      `{VOICE,AUDIO,TEXT}` first-class on `RequestContext.input_format` (single source of truth; legacy `skip_*`
      flags = derived bijection) → `configure_pipeline_stages` selects entry stage from it; `process_text_input`
      passes `input_format=TEXT`. Reconciled vs design (`InputData` is a Union alias, so format lives on
      RequestContext; envelope-stamping deferred to PR-5). Behaviour-preserving, equivalence-tested. **PR-2 ✓ DONE 2026-06-07** `OutputPort`
      (`core/interfaces/output.py`: ABC + `OutputModality` + `DeliveryResult` rich echo/error §3.2 + `negotiate()` §3.1) +
      `core/event_bus.py` (`EventType` vocabulary + `PipelineEvent` + `EventBus` pub/sub + `identity_filter`, failure-isolated)
      + `irene/outputs/` + `OutputManager` (D-2 routing: origin-paired / designated-single / broadcast; negotiation;
      `output.delivered` emission). `irene.outputs` added to hexagon contracts (ARCH-1/2/3/11/12). Adapter-free (fakes, 18
      tests). Workflow wiring = PR-3. **PR-3 ✓ DONE 2026-06-07** real text outputs
      (`ConsoleOutput` + `CallbackTextOutput`) + origin routing by **channel** (`RequestContext.source`
      repurposed to the channel now PR-1 freed it from the format label); CLI runner renders via
      `OutputManager`+`ConsoleOutput` (origin-paired, print fallback). Reconciliation: sync pairs on the live
      channel, not `resolve_physical_id` (that's PR-4's deferred-identity path). Also dropped all `TYPE_CHECKING`
      from the PR-2/3 output modules (direct imports, mirroring `input.py`). **PR-4 ✓ DONE 2026-06-07** F&F/notifications re-routed through OutputManager
      (producer-demote `NotificationService` via `set_output_manager`; `_deliver_notification` delivers the
      completion addressed by the action's identity — `source`/`physical_id`/`room` threaded from `ActionRecord`
      onto `NotificationMessage`; legacy global-TTS bypassed, LOG kept; origin-unreachable → drop+log+history,
      D-3). Wired the dead `request_source` field; captured `source` on `ActionRecord`. Opt-in (composition wiring
      = PR-5; bounded reconnect = PR-8). Recovered 1 baseline drift test (request_source flow); baseline now 83. **PR-5a ✓ DONE 2026-06-07** process-wide
      OutputManager wired (composition→engine [Any-typed] + injected into NotificationService via
      MonitoringComponent [object-only]; closes PR-4 opt-in → F&F delivery live; CLIRunner registers
      ConsoleOutput on the *shared* OM; migration fallback to legacy TTS when no output for an identity, so
      voice-announce doesn't regress — pure D-3 restored at PR-8). **PR-5b ✓ DONE 2026-06-07** interactive runner
      consumes the single CLIInput source (`_run_interactive_loop` drains `listen()` → workflow → shared OM
      instead of owning a `prompt_toolkit` reader); PR-0 stopgap removed (cli auto-start re-enabled) → one
      reader + one consumer ⇒ double-reader structurally impossible; `help`/`status` → `system.*` intents (D-4),
      only `quit` transport-local. Full multi-channel daemon multiplexer (web/ws/mqtt concurrent + runtime
      attach/detach + runners→pure presets) is a follow-on; PR-5b lands the CLI consume loop as the first instance. **PR-6a ✓ DONE 2026-06-07** process-wide
      `EventBus` wired (composition builds it, shared by OutputManager + WorkflowManager, injected into engine);
      `process_text_input`/`process_audio_input` publish `input.received`+`result.produced` (origin identity carried),
      OutputManager publishes `output.delivered` → observation stream live end-to-end (`asr.transcript`/`intent.recognized`
      deferred). **PR-6b ✓ DONE 2026-06-07** gated `/ws/observe`
      tap (shared-token + localhost-first auth via `core/observe.authorize_observer`; identity-filtered live `EventBus`
      stream via `subscribe_to_queue`, bounded queue drops-oldest so a slow tap can't stall publish; `system.observe_token`
      / `observe_allow_remote` config). **PR-6c ✓ DONE 2026-06-07 (backend)** web built-in-app
      push output: `/ws/output` registers a `CallbackTextOutput` keyed by per-connection `client_id`; OutputManager
      `_origin_output` now prefers a `client_id` (physical-identity) match before the channel match, so deferred F&F
      routes to the exact browser connection (not a random one); added `remove_output`. Frontend follow-on: the
      app's JS must open `/ws/output`, thread its `client_id` into POSTs, and render pushed frames (web-template edit).
      **ARCH-15 PR-6 COMPLETE (6a+6b+6c).** **PR-7 ✓ DONE 2026-06-07** config-driven outputs +
      config-ui editor: backend `OutputConfig` (`[outputs]` on CoreConfig: console/console_prefix/web_push) auto-generates
      a config-ui section (AutoSchemaRegistry; order/title added); adapter registration config-gated (CLIRunner console
      gate+prefix, `/ws/output` web_push gate). Frontend renders for free (schema-driven; UI-9 generic widgets; labels
      from Pydantic descriptions) — `npm run check`+`build` green, no UI code change. multi-input already representable;
      per-input `format` is derived (no editor surface); capability-matrix display deferred (optional). **PR-8 ✓ DONE 2026-06-07** local audio/voice SPEECH
      output ONLY — NO MQTT: `AudioSpeechOutput` (`outputs/audio.py`, TTS+audio synth→play, carries SPEECH+TEXT); vosk
      registers it + designates it the OutputManager **conversational fallback** (new: unmatched conversational result →
      designated local speaker), which solves voice addressing (source `voice`/`audio_stream`, no room) and lets the
      PR-5a legacy-TTS fallback be **retired → pure D-3 restored**. No broker code — all MQTT is ARCH-8's. **PR-9** (runs last) cross-task
      reconciliation: **(1) ✓ DONE 2026-06-07** revisit **ARCH-7** → fed ARCH-8 via `mqtt_integration.md` §13 (banner +
      reconciliation section: bridge=request/response `OutputPort`+rich `DeliveryResult`, `device_command` modality,
      `DeviceCatalogPort` read port, Flow-1 terminal `OutputPort`, `ActuationPort` dropped, observable on the bus;
      §13 wins over §3–§10) + amended ARCH-7/ARCH-8 ledger entries; the entire MQTT build still lives in ARCH-8 (PR-9.1
      only produced the spec). **(2) ✓ DONE 2026-06-07** swept every other
      unfinished ARCH/QUAL item (no-impact: ARCH-10/QUAL-18/19/20/31; aligned: QUAL-32 — new I/O modules already
      TYPE_CHECKING-free; uses-the-design: QUAL-35 — device handlers emit `device_command` via the §13 bridge `OutputPort`;
      ARCH-8 reconciled in 9.1) — amended QUAL-32/QUAL-35 with pointers, journal sweep note. **Extended
      `get_master_config_completeness`** to cover top-level config sections + scalar fields (was `*.providers.*` only;
      scalar via key-text-search so commented optionals like `observe_token` aren't false-missing; Dict/nested fields
      checked at section granularity) → catches `[outputs]`/`observe_*`-class drift automatically; `test_master_config_
      completeness_toplevel.py` (6). **ARCH-15 PR-9 COMPLETE (9.1+9.2).** **PR-10** daemon multiplexer + runners→thin
      presets (concurrent input+output registries + runtime attach/detach §4; layered-override presets §8) — the web/vosk
      *consume/preset* unification rides here (their *outputs* arrive in PR-6/PR-8); CLI's PR-5b consume loop is the first
      instance to generalize; closes the runners-as-presets endgame. Gates per slice: `pyright` 0 · import-linter ·
      dep-validator · `check_scope` · backend suite no-net-regression · config-ui `npm run check`+`build` where touched.
      Refs: ARCH-14, ARCH-6, ARCH-7/8, QUAL-28.
- [ ] **ARCH-16** [IO] (P-deferred) — **I/O daemon multiplexer + runners→thin presets (deferred ARCH-15 PR-10).**
      The I/O hexagon (ARCH-15) is complete and every channel runs; this is the internal-cleanliness endgame, deferred
      2026-06-07 as low-incremental-value / higher-risk. Scope: (a) **remote interactive text-attach channel** (e.g.
      `/ws/cli` — attach a debug-CLI from a notebook, text in/out, routed through the workflow + OutputManager,
      origin-paired; the *reproduce* half of the operator scenario, pairing with the PR-6b `/ws/observe` *observe* half) —
      the highest-value, low-risk piece, additive + testable; (b) **runners → thin config-preset launchers** over **one
      daemon multiplexer** that consumes all active input sources concurrently (generalising PR-5b's CLI consume loop) +
      **runtime attach/detach** (§4/§8) — fuses the CLI/webapi/vosk shapes; the larger, riskier refactor (low e2e
      coverage on interactive paths). Also carries the small ARCH-15 follow-ons: **PR-6c web-app JS** (open `/ws/output`,
      thread `client_id` into POSTs, render pushed frames — web-template edit) and **PR-7 capability-matrix display**
      (read-only outputs×modalities). Refs: `io_architecture.md` §4/§8/§12 (PR-10), ARCH-15, ARCH-6.
- [x] **ARCH-17** [AUDIO] — **DESIGN — audio input/output negotiation + transformation seam; deliverable
      `docs/design/audio_pipeline.md` (design session 2026-06-10).** The **input twin of ARCH-15**: unifies three
      threads the audio chain (mic→VAD→wake→ASR) never got a clean contract layer for — **(1)** VAD becomes a
      **lightweight provider family** (`VADPort` + `irene.providers.vad`: energy/silero/microvad; entry-points + nested
      `[vad.providers.*]` config; no web/manager), killing the 4-way if-else and the scattered-knowledge bugs; **(2)**
      **pre-roll becomes a declared contract** — a VAD provider exposes `detection_latency_ms`, the `VoiceSegmenter`
      sizes the pre-buffer from it (replaces the magic `4`; the segment feeds the wake word, so this is detection
      correctness); **(3)** audio **encoding (rate/format/channels) becomes a derived, negotiated, transform-once,
      *traced* contract** — one **canonical** internal format derived as the common denominator of declared
      `AudioContract`s (config can pin; **fatal startup error** if none satisfies all parties). Harmonized, function-named,
      direction-shared set: **`AudioTranscoder`** (rename of `AudioProcessor`, absorbs `AudioFormatConverter`; one
      transform primitive for input AND output — collapses the 3 duplicated TTS resample blocks), **`VoiceSegmenter`**
      (rename of `UniversalAudioProcessor` minus the if-else), **`AudioNegotiator`** (derive/validate/drive + trace).
      Symmetric in+out (output TTS→playback negotiates through the same transcoder, traced). Supersedes
      `onnx_inference_layer.md` §11.2's "small seam." Decisions D-1..D-7 LOCKED 2026-06-10 (§12). Implementation = ARCH-18.
- [~] **ARCH-18** [AUDIO] (P-TBD) — **Implement ARCH-17, sliced PR-1..6 (`audio_pipeline.md` §13).** **PR-1 DONE
      2026-06-10** (`AudioProcessor`→`AudioTranscoder` rename everywhere — kills the `UniversalAudioProcessor` name
      collision; behavior-preserving, pyright 0, suite 83=83). _Reconciliation:_ `AudioFormatConverter` is a **used,
      tested convenience layer** (not the dead duplicate the plan assumed), so its dissolution moved to PR-3/PR-4 —
      **`AudioFormatConverter` is deleted by the end of ARCH-18**, its transform methods folded onto the
      transcoder/negotiator + the 3 TTS resample dups collapsed (PR-4). **PR-2 DONE 2026-06-10** (3 commits + the
      rename): VAD provider family (`VADProvider` in `providers/vad/base.py` — the **adapter-port**, not a separate
      `core/interfaces` port — + energy/silero/microvad adapters wrapping the engines + entry-points + `[vad.providers.*]`
      schemas via auto_registry/config-ui; all 12 configs nested) + `VoiceSegmenter` (extract the if-else → discovery,
      energy fallback; `UniversalAudioProcessor`→`VoiceSegmenter` rename). **Folded the one real bug** (deleted the
      `vad_implementation` validator); re-reconciliation found the `calibrate_threshold` "bug" benign (the ABC already
      no-ops it) → it's just the `VADProvider.calibrate` default-no-op. config-ui green; suite 81 failed (down from 83,
      nesting fixed 2; 2 stale flat-config tests → TEST-7); pyright 0, 9/9 contracts, dep 58/58. **PR-3 DONE 2026-06-10**
      (5 commits): `AudioContract` + `derive_canonical` (utils, common-denominator + fatal); **party-declared
      contracts** — `audio_contract()` on the VAD/wake/ASR provider bases, `AudioNegotiator.from_pipeline` gathers the
      active providers' contracts (config rate as override) → capability-driven, not config-authoritative; canonical
      derived + validated (fatal) at workflow init; `to_canonical` transforms capture **once** at the
      `process_audio_input` boundary (traced `audio_negotiate` stage). **`AudioFormatConverter` folded + deleted** — its
      convert/streaming are now `AudioTranscoder` methods, `supports_format`→`supports_audio_file_format` module fn.
      _(Initially shipped config-derived + with the AFC fold deferred; both gaps closed on review.)_ pyright 0, 9/9
      contracts, suite 81=81 (+~26 tests). **PR-4** symmetric **output** negotiation (TTS→playback through the
      negotiator/transcoder, traced) + collapse the 3 TTS resample dups + remove redundant per-consumer resampling. **PR-5** pre-roll contract (`detection_latency_ms` → segmenter sizing). **PR-6
      (FINAL) — user-facing docs + diagrams:** update `docs/guides/{vad,voice-trigger,audio}.md` + architecture docs for
      the new component + negotiation seam, and **re-author the affected dataflow/audio diagrams** in `docs/images/`
      (mic→VAD→wake→ASR flow + the transform/negotiation seam; PNG/JPEG per the docs rules, no mermaid). Invariant #4:
      the `[vad.providers.*]` schema change updates config-ui in the same PR (PR-2). VAD providers wrap the existing
      energy/silero/microvad engines (no new ML).

### Code Quality & Review (QUAL)
- [x] **QUAL-1** — Phase-0 static baseline (ruff/pyright/vulture/validators/import-graph). → `docs/review/phase0_static_baseline.md` (6e39886)
- [x] **QUAL-2** — Review round 1: phantom-reference `NameError`s + method shadowing. → b6cd282
- [x] **QUAL-3** (P1) — **DONE 2026-06-06.** Category D wiring. **Reconciled (Invariant #8): the entry-point total is now
      55, not §D's 58** (the `settings` runner was removed in QUAL-21); validator was 50/55 with 11 errors. **Fixes:**
      (a) `MonitoringComponent`/`ConfigurationComponent` `get_python_dependencies` were unbound **instance** methods →
      made `@classmethod` (matching the `EntryPointMetadata` `@classmethod @abstractmethod` contract) — this also cleared
      4 of the QUAL-4d Cluster-A override-incompat errors (43→39); (b) the 3 runners `cli`/`vosk`/`webapi` (via their
      shared `BaseRunner`) lacked the entry-point metadata methods → added `@classmethod` `get_python_dependencies`/
      `get_platform_dependencies`/`get_platform_support` to `BaseRunner` (runners coordinate components, so no Python deps
      of their own by default; cascades to all 3). **Done-criterion met: `irene-dependency-validate --validate-all` =
      55/55 passed, 0 errors.** Verified: 9/9 import contracts kept, suite 84=baseline. _The remaining QUAL-4d Cluster A
      (39: `name`/`is_available`/`initialize`/`set_default_provider` port alignments) is the non-QUAL-3 remainder._
- [x] **QUAL-4** (P1) — **✓ DONE 2026-06-06.** Type-safety debt: drove **standard-mode pyright to ZERO** (the release
      gate) via a **by-rule ratchet** — `uv run pyright` now reports **0 errors at full standard mode with an empty
      suppression list** (762 baseline → 0; `pyright==1.1.410` pinned; the lone scoped exception is the documented
      Pydantic file-directive in `irene/api/schemas.py`). All five slices done: **4a** gate · **4b** None-safety (238) ·
      **4c** phantom-attrs (163) · **4d** override-compat (87) · **4e** type-tail (261). The burn-down doubled as a
      bug-hunt: ~25+ genuine latent bugs fixed across 4b–4e (None-derefs, phantom attrs, a microWakeWord `metadata`
      TypeError swallowed as not-detected, a sync method being `await`ed, `min_items`→`min_length`, `callable`-as-type,
      a broken `default_factory`, an `UnboundLocalError`, …). Verified throughout: 9/9 import contracts, validator 55/55,
      suite 84=baseline. Drive **standard-mode pyright to ZERO** (the release gate) via a **by-rule
      ratchet**, and re-tighten the config. Refs: §E. **Reconciled 2026-06-06 (Invariant #8(b), user-approved):** the §E
      baseline of 1,107 has fallen to **762 errors / 172 files** at standard mode (accurate venv-resolved count, pyright
      1.1.410, tests excluded) — the ARCH/QUAL refactors fixed ~31% incidentally. **Target = zero at standard** (user
      decision; a numeric threshold invites drift). **Subdivision (by-rule, each slice ENABLES its rule in
      `pyrightconfig.json` so it can't regress — the end state is an empty suppression list):**
      - **4a ✓ DONE 2026-06-06** — established the gate. `pyrightconfig.json` rewritten to `typeCheckingMode=standard` +
        venv-wired (`venvPath`/`venv`) and **the 20 currently-erroring rules suppressed → gate green at 0**; pinned
        `pyright==1.1.410` in the `dev` extra (diagnostics vary by version); removed the duplicate `[tool.pyright]` block
        from `pyproject.toml` (JSON config is the single source of truth). Canonical gate command = `uv run pyright`
        (exit 1 on any error; requires a full-extras env — `uv sync --all-extras`). Verified 0 errors; suite 84=baseline
        (config-only, no runtime change). Wiring into CI = BUILD-2.
      - **4b ✓ DONE 2026-06-06** — `reportOptionalMemberAccess` (238) cleared and the rule **enabled** (deleted its
        suppression — the ratchet moved up). Big lever: a typed `_require_asset_loader()` helper in `intent_component.py`
        took it 91→0 (the `.config` accesses resolved as a side effect); the long tail (147 across 35 files) fixed by
        explicit None-guards matching each file's idiom (handlers degrade gracefully; required deps fail-loud via the
        file's own exception type; lazy optional-dep handles restored to their declared `Any`). **Hexagon preserved**
        (user-flagged): 9/9 import-linter contracts kept, domain (`intents/`) + `utils/` gained ZERO outward imports
        (guards use None-checks/builtins/`Any` only); the one new import is `intent_component→core.intent_asset_loader`
        (allowed components→core). Verified: 0 `reportOptionalMemberAccess` repo-wide, gate green with the rule enforced,
        suite 84=baseline (no behavior regression).
      - **4c ✓ DONE 2026-06-06** — `reportAttributeAccessIssue` (163) cleared and the rule **enabled**. The high-value
        slice: ~15 were **genuine latent bugs**, not type noise — e.g. `voice_trigger_component._resampling_metrics` never
        initialized (a Phase-1 migration dropped the init, kept the `+=`, so the first resample raised
        AttributeError-as-failure); `monitoring_component` read non-existent `DomainMetrics.success_rate`/`.avg_duration`;
        `nlu_component` language loop used a wrong dict key (dead code); `config/models.py` shadowed the module `logger`
        (UnboundLocalError on the orphaned-config path); `audio_processor` wrote a read-only `config.threshold` property +
        called `calibrate_threshold` missing on the silero VAD engine; `validator.py` checked removed `SystemConfig`
        fields. Type-only fixes: `datetime._get_localization_data` return `Dict[str,List[str]]`→`Dict[str,Any]` (29);
        `DomainMetrics` 6 lazily-seeded sub-metric fields declared (13, with the `hasattr`→truthiness seed-guard flip to
        avoid a KeyError regression); `InteractiveRunnerMixin` mixin-attr annotations (10, which exposed 4 `self.core`
        None-accesses I then guarded); `TextProcessingRequest.context` field added (9). **Hexagon preserved (user-flagged):
        9/9 contracts kept; the `.core`/`self.core` phantoms fixed WITHOUT re-introducing `self.core` or a core import
        (config captured at init); ports widened only where it's a genuine shared contract (`WebAPIPlugin.name`); new
        imports all inward (components→config/providers, core→intents-domain).** Done across one in-file helper + targeted
        fixes + 5 verified sub-agents. Verified: 0 `reportAttributeAccessIssue` + 0 `reportOptionalMemberAccess` repo-wide,
        gate green with both rules enforced, suite 84=baseline (no regression despite the real bug fixes).
      - **4d ✓ DONE 2026-06-06** — `reportIncompatible{Method,Variable}Override` (87) cleared, both rules **enabled**.
        **A — port-hierarchy harmonization (done):** `name` → read-only `@property` on `WebAPIPlugin`/`ComponentPort`
        (all 11 components already implement it; removed the now-dead `Component.__init__` dynamic `self.name` branch);
        **`is_available` → async everywhere** (user decision — capability ports + inputs + `tts_component` made `async`,
        with the `await` cascade propagated through `inputs/manager.py`'s sources, matching the already-async
        `Component.base`); `set_default_provider` base/port param `name`→`provider_name`; `default_provider`→`Optional[str]`;
        `initialize` made **required** on `Component.base`+`ComponentPort` (the 9 impls revert to `(self, core)`) — **note:
        my earlier `(self, core=None)` attempt regressed the 4b gate (untyped `=None` → `core` inferred `None` → 20
        `reportOptionalMemberAccess`, committed in 37f245a without running the full `uv run pyright`; fixed by requiring
        core); singletons (`get_status`→async, `extract_*` port params, `get_component` via `ComponentPort` extends
        `ComponentControlPort` [core→intents, contract-permitted], `process_audio_stream` async-gen stub, `get_config_schema`
        aligned to the inherited classmethod). **Hexagon: 9/9 import contracts kept; one new inward import
        (core/interfaces→intents.ports).** **C — schemas (40):** Pydantic field/Config
        narrowing (`success: Literal[False]`, discriminator `type`, inner `class Config`) is by-design, not a bug; pyright's
        invariant-class-var rule doesn't fit it → scoped-off via a documented file-level `# pyright:
        reportIncompatibleVariableOverride=false` in `irene/api/schemas.py` only (rule stays enforced everywhere else;
        wire shape unchanged → config-ui unaffected). **B — ASR `transcribe_stream` (4):** abstract base was `async def`
        (coroutine) while impls are async generators → made the base a plain `def …-> AsyncIterator[str]` (async-gen
        overrides are covariant-compatible). Verified end-to-end: gate green with 4b+4c+4d all enforced, 9/9 contracts,
        validator 55/55, suite 84=baseline.
      - **4e ✓ DONE 2026-06-06** — the type-tail (261: `reportArgumentType`/`reportCallIssue`/`reportPossiblyUnbound`/
        `reportReturnType`/… ) cleared; **all remaining suppressions deleted → empty list = full standard mode.** `schemas.py`
        (71) was mostly Pydantic v1-isms with clean v2 fixes: `Field(example=…)`→`json_schema_extra={"example": …}` (66),
        a broken `default_factory=PerformanceMetrics` (required fields → would crash; made the field required), 4 `timestamp`
        overrides given the base default. The 190-file tail was cleared by 6 verified sub-agents (mostly `param: T = None`
        → `Optional[T]`, untyped-3rd-party `cast`s, possibly-unbound inits, and real bugs). **Flagged for follow-up (real
        logic bugs surfaced, type-fix applied but deeper fix deferred):** `config/manager.py` `_generate_*_sections` drops
        all but the last section header in generated TOML; the `intent_asset_loader` validators emit `{field,message,
        severity}` dicts but `api.schemas.ValidationError` needs `{type,message,path}` (would 500 on a real validation
        error). _Original tail estimate below._ the tail (`reportArgumentType` 113, `reportCallIssue` 91, `reportPossiblyUnboundVariable` 27,
        `reportReturnType` 17, `reportGeneralTypeIssues` 14, + ~20 long-tail) → empty suppression list = full standard mode
        on. Decide `mypy.ini` disposition here (retire vs align — pyright is the gate; running both is redundant).
        Hotspot `intent_component.py` (97 errors, 18%) spans 4b–4e.
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
- [ ] **QUAL-18** [STREAMAPI] (P-TBD) — Act on QUAL-17 (per `streaming_api_review.md` §5): **(1)** vendor + wire the
      official `@asyncapi/web-component` at `/asyncapi`, delete the bespoke renderer (≈ −900 LOC); **(2)** fix the
      lossy `_clean_property_for_asyncapi` union/nullable handling; **(3, scoped separately)** emit AsyncAPI 3.0 +
      binary message bindings for ESP32 frames; **(4)** retire/repoint the docstring `x-` extension parser.
- [x] **QUAL-19** [ESP32] (P2, last pre-release) — **DONE 2026-06-09** (interactive review session + upstream study).
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
- [x] **QUAL-20** `[release]` [ESP32] (P-TBD) — **DONE 2026-06-09 — wake-word + microVAD rebuild (5 commits
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
      `libtensorflowlite_c` coverage on aarch64 at the BUILD-3 image stage. WB7 hw re-val stays with ARCH-10. _Original
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
      wheel platform coverage (x86_64/aarch64). WB7 hw re-val stays with ARCH-10 completion.
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
- [ ] **QUAL-44** `[deferred]` [DFLOW] (P2, enhancement; split from QUAL-31) — **Answer-vs-new-command arbitration on a
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
- [ ] **QUAL-35** `[release]` [PEX][MQTT] (P-TBD) — **Declarative NLU tiers T2 + T3 — MUST-HAVE for smart-home/MQTT
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
      handshake). Gated by Invariant #4 (any donation-schema change → config-ui;
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
- [ ] **TEST-8** [PORTS] (P1) — _(coverage goal for TEST-7)_ **Capability-port handler coverage (surfaced by QUAL-24).**
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

### Build & CI (BUILD)
- [x] **BUILD-1** (P0) — Verify clean `uv sync` + CLI and WebAPI boot at v15. **DONE 2026-06-01** (`bab6f97`):
      `uv sync --extra all` clean; `--check-deps` 5/5; **WebAPI** boots (workflow READY, 10 routers) and
      `POST /execute/command "привет"` → `greeting.hello` end-to-end; **CLI** boots and (after fix) headless
      `--command "привет"` works. Found+fixed a real bug: `--headless` disabled `nlu`/`text_processor` while the
      unified workflow requires `nlu` → headless could never execute a command. Observed (already-logged) cosmetics:
      QUAL-6 schema warning on boot; CLI banner still says "v14" (DOC-3 sibling).
- [x] **BUILD-2** (P1) — DONE 2026-06-08: rebuilt CI as two health workflows with **enabled** push/PR triggers.
      **`backend-health.yml`** (renamed from `config-validation.yml`) — hard gates (no continue-on-error):
      `lint-imports` (hexagon), `scripts/check_no_type_checking.py`, `pyright` (QUAL-4 0-error gate),
      `build_analyzer --validate-all-profiles`, `config_validator_cli --config-dir configs/` (config schema +
      master-config completeness), and `dependency_validator --validate-all`. Installs the toolchain via
      `uv sync --frozen --extra dev`; deprecated `setup-python@v4`/`upload-artifact@v3` replaced (python v5; the
      report-artifact machinery dropped); the phantom `intent_validator` step removed. Deferred gates placeholdered:
      pytest (until the TEST- items resolve), black/isort (until the tree is formatted). **Known honest-red
      (accepted):** `config_validator_cli` fails on 3 stale fixtures — tracked as **BUILD-6**. Done together with
      **BUILD-4** (frontend).
- [ ] **BUILD-3** (P2) — **DEFERRED to the release phase (decided 2026-06-01): Docker builds are an end-stage
      task**, after the architecture/code work settles (image contents, extras, and armv7 viability all depend on
      the post-refactor shape — incl. QUAL-19/20 [ESP32] and ARCH-9/10 [INFER] for the sherpa-onnx/runtime
      footprint). Then verify the minimal x86_64 Docker build (builder feeds analyzer package names to
      `uv sync --extra`, which expects extra *names* — confirm/fix, now owned by **BUILD-5**) + container boots
      CLI/WebAPI. Gates Definition-of-release item #1. Refs: `docs/guides/build-docker.md`, build audit.
- [x] **BUILD-4** (P1) — DONE 2026-06-08: new **`frontend-health.yml`** workflow (push/PR on `config-ui/**`) runs the
      config-ui gates as hard checks — `npm ci`, `npm run check` (type-check + strict ESLint + orphans), `npm run build`,
      `npm run test` (vitest: 40 tests). All green today; satisfies the Invariant-#4 ongoing config-ui gate.
- [x] **BUILD-6** `[release]` [QUAL] (P2) — **DONE 2026-06-09.** All 12 configs now validate; `config_validator_cli
      --config-dir configs/ --ci-mode` is green → backend-health Gate 5 goes green. Each failure was a *required*
      provider-schema field (no default) missing from the fixture: **(1)** `vad-production.toml` — added the required
      `api_key = "${ELEVENLABS_API_KEY}"` to its active `tts.elevenlabs` default and `api_key = "${OPENAI_API_KEY}"` to
      its active `llm.openai` default (mirroring the canonical `config-master.toml` placeholder style); **(2)**
      `vosk-test.toml` — added the schema-required `credentials_path`/`project_id` to the *disabled* `asr.google_cloud`
      block (the validator schema-checks declared providers even when `enabled = false`, exactly as it does for the
      kept-but-disabled `whisper` block, which passed only because all its fields default); **(3)** `vad-testing.toml` —
      the `CoreConfig` `extra_forbidden` error was a top-level `[testing]` section (4 ad-hoc VAD scenario sub-tables)
      that **nothing in the codebase reads** (no `CoreConfig.testing` field, no consumer in `irene/`) — removed as dead
      config. No schema/contract touched → no config-ui impact (Invariant #4 N/A). Verified: 12/12 valid,
      `build_analyzer --validate-all-profiles` ✓, `dependency_validator` 55/55 ✓ both platforms, suite 83=83 FAILED (0
      net regression — the failing VAD tests are pre-existing TEST-7 staleness, unrelated to the removed section: their
      `scenario_a/b` are *generated audio* fixtures, not the `[testing]` block). _Original task below._ **Fix the 3
      config fixtures that fail `config_validator_cli`** (the
      backend-health Gate 5 honest-red, surfaced 2026-06-08): `vad-production.toml` (invalid `elevenlabs` tts + `openai`
      llm provider configs — the `elevenlabs` block was a minimal BUILD-5 placeholder that needs the real schema fields),
      `vad-testing.toml` (a `CoreConfig`-level validation error), `vosk-test.toml` (invalid `google_cloud` asr config).
      `build_analyzer --validate-all-profiles` already passes (the providers exist); this is the deeper provider-config
      *schema* validation. Done when `config_validator_cli --config-dir configs/ --ci-mode` is green (backend CI goes
      green).
- [x] **BUILD-5** (P2) — **DONE 2026-06-08** (outcome summary at the end of this item). **Verify conditional/profile-driven
      build analysis (`build_analyzer`) still works vs the
      pre-pause (~Sep 2025) baseline.** The revival churned everything the analyzer reads — entry-points, providers,
      models (ASSET-1/2), and it removed surfaces (`train_schedule` handler QUAL-34, `settings` runner QUAL-21) — and
      **ARCH-13 just edited `build_analyzer.py`** (dropped the now-deleted `irene.plugins.builtin` discovery + a fallback
      namespace). So the analyzer's emitted build requirements may have drifted or broken. **`build_analyzer` =** the
      `irene-build-analyze` tool (`python -m irene.tools.build_analyzer`) that reads a config/profile and emits the
      minimal build requirements (which `--extra`s / system packages / python modules per platform) so a *conditional*
      image carries only what a profile needs — it feeds the Docker build (cf. **BUILD-3**, which it gates). **Checks:**
      (1) `--list-profiles` + `--validate-all-profiles` pass; (2) `--config <profile>` (minimal/voice/full) emits sane,
      non-empty requirements with **no references to deleted modules** (esp. `irene.plugins.builtin`); (3) entry-point
      namespace discovery (`_discover_entry_point_namespaces`) resolves cleanly against the current `pyproject.toml`
      `[project.entry-points]`; (4) the emitted `--extra` names are real extras `uv sync --extra` accepts (the BUILD-3
      caveat); (5) `--docker --platform {ubuntu,alpine}` requirement sets look right. **Baseline compare:** diff today's
      per-profile output against the analyzer's behavior at the pre-pause commit (git history) and explain every delta as
      intentional (new/removed providers, model refresh) vs a regression. Consider landing a small regression test
      (golden per-profile requirement sets) so this can't silently rot — coordinate with TEST-7. **(6) armv7 image base
      Alpine→Debian (ARCH-9):** `onnx_inference_layer.md §4.7/§9` proved sherpa-onnx has no musl build, so `Dockerfile.armv7`
      must switch `python:3.11-alpine`→`arm32v7/python:3.11-slim-bullseye` and the analyzer's armv7 path must emit the
      `linux.ubuntu` (apt) set, not `linux.alpine` (apk) — verify the marker-driven `asr-onnx` extra + `libasound2` resolve
      on the Debian armv7 path. (Image build/boot itself stays BUILD-3, release phase.) **(7) two build-blocking
      Dockerfile bugs** surfaced 2026-06-08 — both Dockerfiles invoke the non-existent `irene.tools.intent_validator`,
      and `Dockerfile.armv7` has an `ubuntu_packages` NameError; findings + line refs in
      `docs/review/docker_build_review.md`. Refs: build audit, `docs/guides/build-docker.md`,
      `docs/review/docker_build_review.md`, BUILD-3, `docs/design/onnx_inference_layer.md` §4.7/§9 (ARCH-9).
      **— OUTCOME (2026-06-08):** Reconciliation (Invariant #8) found the feared analyzer drift was a non-issue —
      `--list-profiles`, namespace discovery (`_discover_entry_point_namespaces`), and `--config/--docker` all sane;
      ARCH-13 had already cleaned the `plugins.builtin` refs. **(A) config hygiene:** `--validate-all-profiles` was red
      on 6 profiles (incl. canonical `config-master`, Invariant #2); root cause was the `text_processor` component vs
      `text_processing` provider-namespace mismatch plus stale `general_text_processor` / `openai`-TTS provider refs. Per
      user decision, **renamed the provider entry-point + module dir + port interface + the component `category`**
      `text_processing`→`text_processor` (no aliases — consistent with every other capability) and fixed the 5 stale
      configs → **all 12 profiles VALID**. **(B/§7):** removed the non-existent `intent_validator` call from both
      Dockerfiles; fixed the armv7 `ubuntu_packages` NameError; fixed a latent x86_64 `system_packages` key bug
      (`ubuntu`→`linux.ubuntu`). **(C/§6):** migrated `Dockerfile.armv7` Alpine→Debian (`arm32v7/python:3.11-slim-bullseye`,
      apk→apt, reads the `linux.ubuntu` apt set the analyzer already emits — `libasound2` + the `asr-onnx` extra resolve).
      9/9 import contracts kept; full suite 83 failed = baseline (no net regression). Image **build/boot** stays BUILD-3
      (release phase; armv7 on hardware). Optional golden per-profile regression test deferred to TEST-7.

### Models & Assets (ASSET)
- [x] **ASSET-1** — Refresh stale model IDs (Anthropic→Claude 4.x, Whisper large-v3, ElevenLabs multilingual_v2, spaCy 3.8, gpt-4→gpt-4o-mini). → fc85306
- [x] **ASSET-2** (P1) — **Liveness-checked ALL model download URLs. DONE 2026-06-03.** Swept every model URL in
      `irene/` (33 → 29 after fixes), range-GET each. **Hosts all healthy** (silero.ai served the real 40MB `v4_ru.pt`;
      alphacephei/vosk, github releases/openWakeWord v0.5.1, openai whisper-CDN, github/spacy-models all 200/206 serving
      bytes). **2 real defects fixed:** (1) **whisper `tiny`** had a **truncated 40-char hash** (`whisper.py:85`) → 404;
      restored the full 64-char canonical hash (the other 6 whisper URLs were correct). (2) **silero v4 `en/de/es/fr`**
      were declared but **404** — silero's v4 line is **Russian-only** (`v4_ru` ✓, even `v4_ua` exists; the western langs
      never shipped v4 and stay at v3); trimmed `silero_v4` catalog to `v4_ru` and pointed non-RU TTS at `silero_v3`
      (its en/de/es models are live). **1 dead URL left, by design → QUAL-19:** the microWakeWord `micro_speech.tflite`
      (`microwakeword.py:436`, github `tensorflow/tflite-micro` raw path moved) — but that provider is a known placeholder
      (stub feature-extraction; a TF *demo* model, not a real wakeword model), so it's the ESP32/wakeword review's
      keep-fix-cut call, not a URL patch. **Caveat honored:** network is fake-IP mode (all hosts → `198.18.0.0/15`,
      normal); judged on bytes-served vs stall, not the IP. **Torch.hub hedge:** unneeded — `models.silero.ai` is healthy.
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
- [x] **DOC-2** (P2) — DONE 2026-06-08: archived the entire `docs/TODO/` subfolder + `docs/TODO.md` to
      `docs/archive/` (superseded by this plan). The open TODO11/microWakeWord work is tracked under
      QUAL-19/20 (`esp32_wakeword_review.md`), not the TODO folder, so nothing was lost.
- [x] **DOC-3** (P2) — DONE 2026-06-08: version-display strings now read v15 — `core/engine.py` (module
      docstring + startup log), the runner `--help` banner (`runners/base.py:131`, which the CLI inherits), and
      the `tts_demo`/`async_demo` print banners. Deliberately left: the `config_migrator`/`config/migration`
      v13→v14 strings (functional config-schema-version identifiers) and the "v13/v14 architecture"
      era-descriptor docstrings/comments.
- [x] **DOC-4** (P1) — DONE 2026-06-08: fulfilled by the new canonical documentation set. `architecture.md`
      is replaced by `docs/architecture/*` (harmonized current state + the hexagonal target pattern); the
      **fire-and-forget action flow** [FAF] is documented in `architecture/dataflow.md` +
      `architecture/client-registry.md`; and `docs/fire_forget_issues.md` is **retired** to `docs/archive/`
      (its current verdicts live in `docs/review/fire_and_forget_review.md`).
- [x] **DOC-5** (P1) — Fixed docs that CONTRADICT code: `donations_flow.md` + `intent_donation.md` (donation
      paths → `assets/donations/<handler>_handler/<lang>.json`, schema → `assets/donations/v1.0.json`),
      `ASSET_MANAGEMENT.md` (12 TOML-nesting fixes `[providers.X]`→`[X.providers]`), `train_schedule_handler.md`
      (env → `IRENE_INTENT_SYSTEM__TRAIN_SCHEDULE__*`), `voice_trigger.md` (YAML→TOML), and authoritative
      correction banners on `guides/DONATION_FILE_SPECIFICATION.md` + `plugins/universal_tts.md`.
- [x] **DOC-5b** (P2) — DONE 2026-06-08: regenerated `guides/DONATION_FILE_SPECIFICATION.md` for the v1.1
      two-part model (language-neutral `contract.json` + per-language `<lang>.json`), with full field reference
      from `donation_contract_v1.1.json` (method/param schema, type + entity_type enums) and the cross-language
      validation rule. Old single-file/v1.0 body + drift banner replaced.
- [x] **DOC-7** [PEX] (P1) — DONE 2026-06-08: the parameter-extraction reference is covered across the new
      canonical set rather than one file — `guides/DONATION_FILE_SPECIFICATION.md` (the `ParameterSpec` schema +
      the ParameterType and entity_type enums), `architecture/intents.md` (extraction patterns, `get_param`,
      handler consumption of `intent.entities`), and `architecture/nlu.md` (token/slot pattern format). Closed as
      covered; the standalone `PARAMETER_EXTRACTION_GUIDE.md` was not needed.
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
- [ ] **UI-4** [WORKFLOWVIZ] (P-deferred) — A config-ui **"Workflow Control" / pipeline-visualization page** (live
      React-Flow DAG of the component/provider pipeline, per-stage input/output inspection, provider switching, SSE
      updates). **Source design archived** at `docs/archive/workflow_control.md` (Sep-2025, never built). **Strongly
      gated — do NOT start before Gate 2:** the design assumes a clean pipeline, but QUAL-25 proved the real dataflow
      is broken at many hops (visualizing it now would faithfully render broken flow), and it specs `/workflow/*`
      endpoints that `architecture.md` §7 flags as **fictional** (they'd have to be built for real). Relates to the
      `MonitoringPage` placeholder and the **ARCH-7 [MQTT]** output-seam work (both touch live pipeline observability).
      Re-scope against the *fixed* pipeline + real endpoints when it's actually picked up. Captured from a config-ui
      doc reviewed during QUAL-25 (2026-06-02).
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

### Release Readiness (REL)
- [ ] **REL-1** (P0) — Sign off the Definition-of-release checklist above (fill target + criteria).
- [ ] **REL-2** (P1) — `config-example.toml` + quickstart finalization (the release-time config story).
      _Progress 2026-06-07 (tester-handover prep):_ drafted **`docs/QUICKSTART.md`** (install → config → run CLI/WebAPI/
      config-ui → in/out-of-scope → reporting), and **fixed the `env-example.txt` template** (the quickstart's `.env`
      source crashed a fresh run: it enabled TTS but used the wrong field `AUDIO_OUTPUT`, leaving Audio off → invalid
      config). Recommends the lightweight `minimal`/`api-only` profiles for first run. **Remaining for release:** a curated
      `config-example.toml` (vs the heavy `config-master.toml`), final README pointer, and a friendlier runner message on
      config-validation failure.
- [ ] **REL-3** (P1) — Version bump / changelog / tag.

---

_**Chronology lives in [`RELEASE_JOURNAL.md`](./RELEASE_JOURNAL.md)** — this file is the task ledger only
(scope + status). Findings/rationale: `docs/review/*` + `docs/design/*`._
