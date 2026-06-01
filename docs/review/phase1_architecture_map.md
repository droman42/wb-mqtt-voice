# ARCH-0 — Architecture map, documentation harmonization, and pattern review

**Date:** 2026-06-01 · **Scope:** `irene/` (202 modules, ~64k LOC) + the `docs/` set · **Method:** deterministic
module-level import graph + three code-vs-doc verification passes.

This document covers both ARCH-0 goals: **Goal 1 — harmonize the documentation** (what's out of sync and the
fix plan) and **Goal 2 — review the architecture and recommend a target pattern**.

---

## 0. Headline findings

1. **The codebase is already ~80% Hexagonal (Ports & Adapters)** — it just doesn't say so and doesn't enforce
   it. `core/interfaces/*` are ports, `providers/*` are adapters, `components/*` are application services that
   select adapters via config, and entry-points are the adapter registry. **Recommendation (Goal 2): adopt
   Hexagonal explicitly and enforce it with an import contract.** (§5)
2. **The "giant import SCC" from Phase 0 was largely a measurement artifact.** At *module* granularity there
   are only **2 real cycles**, both small and contained — not a system-wide ball of mud. (§2.2)
3. **The #1 real defect is a god-module: `intents/models.py` (in-degree 67).** It conflates audio I/O
   primitives, intent-domain types, and conversation context, so every layer reaches *up* into `intents` to
   get them. Splitting it dissolves most of the 24 backwards edges. (§2.4)
4. **`docs/architecture.md` is substantially stale below its v15 banner** — fictional managers, endpoints,
   runners, and a "planned (TODO)" framing for systems that are fully built. (§3)
5. **The real data flow differs from the documented pipeline** — VAD is a segment-accumulation gate (not a
   peer stage), NLU and "Intent Recognition" are one stage, TTS/audio is text-path-only, and several
   first-class stages (context/session, fire-and-forget actions, tracing, metrics) are undocumented. (§4)

---

## 1. Layer model (as intended) and the real import graph

Inferred layer ranks (low = foundational; a module should depend only sideways or downward):

| Rank | Packages | Role |
|---|---|---|
| 0 | `utils`, `api`, `__version__`, `external` | primitives / helpers |
| 1 | `config` | configuration models + loading |
| 2 | `core`, `plugins` | engine, managers, interfaces (ports) |
| 3 | `intents` | intent domain + handlers |
| 4 | `providers` | adapters to external tech |
| 5 | `components` | application services (coordinate providers) |
| 6 | `workflows` | pipeline orchestration |
| 7 | `inputs`, `web_api` | delivery/IO |
| 8 | `runners` | composition entry points |
| 9 | `tools`, `analysis`, `examples`, `tests` | peripheral |

> Note: this ranking is *partly wrong by construction* — e.g. `providers` (adapters) sit below `components`
> here, but a clean hexagon would put both adapters and delivery on the *outside*. The map below is what the
> rank model flags; §5 proposes the corrected target.

Graph: **202 modules, 648 intra-`irene` edges.**

### 2.1 Real cycles (module-level SCCs) — only two

**SCC-1 (config ↔ schema-registry ↔ configuration_component) — the genuine architectural knot:**
```
irene.config.auto_registry  ⇄  irene.config.schemas
irene.config.auto_registry  ⇄  irene.components.configuration_component
irene.config.manager → migration → schemas → auto_registry → (manager via configuration_component)
```
`config` (rank 1) reaches *up* into `components` (rank 5): `config/auto_registry.py` imports
`components/configuration_component.py`. The schema auto-registry and a component are mutually dependent.
**This is a real inversion** and the cause of the config-side cycle.

**SCC-2 (inputs base ⇄ its subclasses) — contained, low severity:**
```
irene.inputs.base  ⇄  {cli, microphone, web}
```
A base module importing its own concrete implementations (factory/registry anti-pattern), but fully contained
within `inputs/`. Easy fix (lazy import or a registry seam); low blast radius.

### 2.2 Reassessment of Phase-0 §F
The Phase-0 package-level result ("one SCC across 9 packages, 11 two-cycles") **over-counted** — package
grouping collapses unrelated modules together. At module level the truth is **2 small SCCs + 5 direct
2-cycles** (3 of which are the contained `inputs` pattern). The system is **not** cyclic spaghetti; the real
problems are **directional violations**, not cycles.

### 2.3 Backwards (upward) edges — 24 total, grouped by root cause
| Root cause | Edges | Fix |
|---|---|---|
| **`intents.models` misplacement** (audio/IO + context types live in the intent layer) | `utils.audio_helpers→intents.models`, `utils.vad→intents.models`, `core.{entity_resolver,trace_context,workflow_manager}→intents.models`, `core.engine→intents.context`, `intents.context→workflows.base` | **ARCH-1** split `intents.models` (§2.4) |
| **config reaching up** | `config.validator→core.components`, `config.auto_registry→components.configuration_component`, `utils.logging→config.models` | **ARCH-2** invert config↔core / config↔components |
| **components reaching into delivery/tooling** | `components.{asr,tts}→web_api.asyncapi`, `components.nlu_analysis→analysis.*` | move web schema generation behind a port; treat `analysis` as a peripheral adapter |
| **core orchestrating outward** (engine/workflow_manager → inputs/workflows/components base) | `core.components→components.base`, `core.workflow_manager→workflows.base`, `core.{engine,workflow_manager}→inputs.base` | mostly composition-root behavior; legitimize via DI in the hexagon (§5) |
| **utils→core.metrics** | `utils.vad→core.metrics` | metrics should be a port injected into utils, or vad shouldn't emit metrics directly |

### 2.4 The god-module: `intents/models.py` (in-degree **67**, by far the highest)
It currently defines, in one file in the intent layer: `AudioData`, `WakeWordResult` (generic IO primitives) ·
`Intent`, `IntentResult` (intent domain) · `UnifiedConversationContext`, `ConversationState`, `ContextLayer`
(conversation/session). Because audio/context primitives live here, **everything** (utils, core, providers,
inputs, components, workflows) imports *up* into `intents`.

**Top import hubs (coupling/placement candidates):**
| in-degree | module | layer | assessment |
|---|---|---|---|
| 67 | `intents.models` | 3 | **split** — audio/IO → rank 0/2; context → its own module; intent types stay |
| 51 | `config.models` | 1 | OK (config is foundational; everyone reads config) |
| 28 | `utils.loader` | 0 | OK |
| 21 | `core.engine` | 2 | OK (composition root) |
| 17 | `core.assets` | 2 | OK |
| 16 | `utils.audio_helpers` | 0 | OK (direction) |
| 16 | `intents.handlers.base` | 3 | OK |

**ARCH-1 (generalized):** split `intents/models.py` into
`AudioData`/`WakeWordResult` → a foundational `irene/core/audio.py` (or `irene/io/`); conversation context →
`irene/core/context_models.py`; intent types stay in `intents/`. Keep a thin re-export shim during migration.
This removes the bulk of §2.3's backwards edges and the audio_helpers `TYPE_CHECKING` band-aid in one move.

> **✅ ARCH-1 DONE (2026-06-01) — with two intentional placement changes from the sketch above (no TYPE_CHECKING).**
> (a) `AudioData`/`WakeWordResult` → **`irene/utils/audio_data.py`** (not `core/audio.py`): a zero-dep leaf at
> rank 0 so `utils.audio_helpers`/`utils.vad` import it **sideways** rather than creating the `utils→core` upward
> edge this very review flags as a violation class (§2.3). The `audio_helpers` `TYPE_CHECKING` band-aid is gone
> (real import; no cycle). (b) Conversation context → **`irene/intents/context_models.py`** (not
> `core/context_models.py`): context references `Intent`/`IntentResult`, which are **domain peers**, so the clean
> home is the *same domain package* — a real one-directional sideways import (`context_models → models`; `models`
> does **not** import back), giving **no cycle and no `TYPE_CHECKING`**. Putting context in `core/` (as sketched)
> would invert the domain reference (`core → intents`) and force a `TYPE_CHECKING` shim — rejected. Net: the
> §2.3 **audio** backwards edges (utils→intents) are dissolved; the **context** edges
> (`core.{entity_resolver,trace_context,workflow_manager} → intents.context_models`) are reclassified as
> legitimate **application→domain** (inward) under the §5 hexagon, not violations. 45 importers re-pointed; full
> suite unchanged (176/55, zero regression); TEST-0 green.

### 2.5 Other structural notes
- **Dead input path:** `InputManager` pumps an internal `_input_queue` (`inputs/base.py:299-314`) that **nothing
  in the core loop consumes**; the audio stream is driven directly by the runner
  (`vosk_runner.py:269 → workflow_manager._get_audio_stream`). Either wire the queue or remove it — it's a
  confusing latent seam.
- **`config` package import side-effects:** importing `config` triggers import-time schema validation
  (`config/__init__.py`) which pulls `auto_registry`→`configuration_component`; this amplifies SCC-1 and makes
  any `core→config.models` import risk a cycle (the reason `core/assets.py` needed a `TYPE_CHECKING` shim).

---

## 2bis. Architecture pattern review (Goal 2)

See §5 for the full recommendation and target. Short version: **the existing provider/component/interface/
entry-point split *is* Ports & Adapters** — formalize it as **Hexagonal**, fix the boundary leaks above, and
add an **import-linter contract** so the architecture is enforced in CI and can't silently rot again.

---

## 3. Goal 1a — `architecture.md` harmonization (it's stale below the banner)

The v15 banner is accurate but the body is largely v13-era. Concrete corrections required:

| Area | Problem | Fix |
|---|---|---|
| Engine model / top diagram | Shows `OutputManager` + `CommandProcessor` — **neither exists**; puts NLU/orchestrator/registry on the engine | `AsyncVACore` = component_manager, input_manager, context_manager, timer_manager, workflow_manager (`core/engine.py:41`); NLU/orchestrator/registry live in `IntentComponent` |
| Intent/donation narrative | Describes donation + keyword-first NLU as "planned (TODO #4/#5)", `get_keywords()` API | **Fully implemented**: `core/donations.py`, `core/intent_asset_loader.py`, `providers/nlu/hybrid_keyword_matcher.py`; handlers use `set_donation()`/`get_donation()` |
| Workflows §4.2 | Body still describes 3 workflow classes (Voice/Text/APIService) | One `UnifiedVoiceAssistantWorkflow`; delete the multi-lane diagrams |
| Web API §7 | Most endpoints fictional (`/intents/recognize`, `/intents/execute`, `/intents/keywords*`, `/workflow/*`, `/build/analyze`, `/ws/audio/binary`) | Real routes (prefixed via `get_api_prefix()`): `/nlu/recognize`, `/intents/{handlers,status,donations/*,actions/*}`, `/text_processing/*`, `/voice_trigger/switch_provider`, `/asr/{transcribe,stream,binary}`, `/tts/*`, `/llm/*`, `/audio/*`, `/monitoring/*`, top-level `/execute/command`, `/execute/audio`, `/trace/*`, `/status`, `/health`, `/components` (`runners/webapi_router.py`) |
| Runners §8 | Invents `VoiceAssistantRunner`, `VoiceTriggerRunner` | Only `CLIRunner`, `WebAPIRunner`, `VoskRunner`, `SettingsManagerRunner` |
| Components diagram/table | `WebAPIComponent` (none); handler list of 6 incl. nonexistent `WeatherHandler` | 11 components incl. `IntentComponent`, `ConfigurationComponent`, `NLUAnalysisComponent`; **14** handlers |
| `get_deployment_profile()` §2.6 | "Smart Voice Assistant / Text Assistant / …" | Real: `voice / api / headless / custom(N)` (`core/components.py:369`) |
| Counts/versions | "77 entry-points", `14.0.0` in body examples | **58** entry-points (+10 scripts); **15.0.0** |
| Sequence diagrams | Omit VAD's real role; show NLU and "Intent Recognition" as 2 stages | Add VAD segment-gate; merge NLU/Intent Recognition (see §4) |

**Accurate sections to keep:** §2.5 VAD, Phase-3 monitoring, the dynamic-loading *mechanism*, the high-level
data-flow ordering.

## 3bis. Goal 1b — other docs (sync status)

| Status | Docs | Action |
|---|---|---|
| **CONTRADICTS code** | `guides/DONATION_FILE_SPECIFICATION.md` (fictional JSON schema), `donations_flow.md` + `intent_donation.md` (wrong donation paths: real is `assets/donations/<handler>/<lang>.json`), `ASSET_MANAGEMENT.md` (TOML nesting inverted: real is `[tts.providers.<name>]`), `train_schedule_handler.md` (env prefix `IRENE_INTENT_SYSTEM__TRAIN_SCHEDULE__*`), `plugins/universal_tts.md` (plugin-era → `TTSComponent`/`[tts]`), `voice_trigger.md` (YAML→TOML; `tflite-runtime`) | **fix** (P1) |
| **STALE / historical plan** | `configuration_guide.md`, `config_schemas.md`, `language_support.md`, `PIPELINE_IMPLEMENTATION.md`, `irene_current.md` | **archive** (banners mostly present) |
| **IN-SYNC** | `architecture.md` (banner), `runtime_configure.md`, `CLIENT_REGISTRY.md`, `intent_mqtt.md` (deferred), VAD guides, `HANDLER_DEVELOPMENT_GUIDE.md` (mostly), AUDIO guides | keep; minor version-label drift only |

Canonical anchors going forward: `architecture.md`, `configs/config-master.toml` + `configs/config-example.md`,
`runtime_configure.md`, `CLIENT_REGISTRY.md`, the VAD guides.

---

## 4. Goal 1c — real data flow vs documented pipeline

Documented: `Audio → VAD → Voice Trigger → ASR → Text Processing → NLU → Intent Recognition → Intent Execution → TTS → Audio Output`

**Reality:** one `UnifiedVoiceAssistantWorkflow` with **three entry methods** converging on a shared text
pipeline `_process_pipeline()`:

```
ENTRY A  Text / CLI         process_text_input      skip_wake_word + skip_asr
ENTRY B  Web single audio   process_audio_input     skip_wake_word; VAD bypassed
ENTRY C  Mic stream         process_audio_stream    VAD-gated; wake-word optional
                                   │
   A,B,C ─────────────────────────┴─────────► _process_pipeline(text):
        1. Text Processing  (if enabled)         text_processor.process→improve
        2. NLU              (always)             nlu.process→recognize_with_context   ← NLU == "Intent Recognition" (ONE stage)
        3. Intent Execution (always)             intent_orchestrator.execute(...)     ← method is execute(), not execute_intent()
        4. Fire-and-forget action metadata       _process_action_metadata
        5. Context/history update                conversation_context.add_to_history
   (TTS→Audio only on ENTRY A with wants_audio + should_speak)
```

For the **streaming** path, VAD is the **front gate**: raw chunks → `UniversalAudioProcessor.process_audio_chunk`
→ VAD state machine accumulates a whole `VoiceSegment`; the segment then goes to **either** voice-trigger
(wake-word mode) **or** directly to ASR (`skip_wake_word`). So VAD is a *segmentation/accumulation layer that
gates both trigger and ASR*, **not** a peer stage feeding the trigger. The **single-audio web path bypasses VAD
entirely**.

**Doc corrections:** add VAD's segment-gate role; merge NLU/Intent-Recognition; mark TTS/Audio as
text-path-only/flag-gated; add the undocumented first-class stages — **context/session management,
fire-and-forget actions, tracing (`TraceContext`), metrics, ASR normalization**. (Full call-site map retained
in the ARCH-0 working notes.)

---

## 5. Goal 2 — recommended architecture pattern: **Hexagonal (Ports & Adapters)**

### Why hexagonal (vs Clean / Onion)
The code already has the hexagon's parts; they're just not named or enforced:
- **Ports** = `irene/core/interfaces/{tts,asr,audio,llm,input,webapi,...}` (ABCs).
- **Adapters** = `irene/providers/*` (whisper/vosk/elevenlabs/openai/…) and `irene/inputs/*`, `irene/runners/*`,
  `irene/web_api/*` (driving/driven adapters).
- **Application services** = `irene/components/*` (select + coordinate adapters via config).
- **Adapter registry** = entry-points + `DynamicLoader` (the canonical hexagonal "wire adapters by config").
- **Domain** = intents + donations + the pipeline use-cases (`workflows`).

Clean Architecture would also fit but adds concentric-ring ceremony; Hexagonal maps 1:1 onto the existing
provider/component/interface/entry-point split, so it's the **lowest-friction formalization** and the easiest to
enforce.

### Target rings and the one rule
```
        DRIVING ADAPTERS                 DRIVEN ADAPTERS
   runners / web_api / inputs  ──►  ┌───────────────┐  ◄── providers/* (asr,tts,llm,audio,vad,voice_trigger)
                                    │  APPLICATION   │       analysis/*, external services
                                    │  components/*  │
                                    │  workflows/*   │
                                    │  ┌──────────┐  │
                                    │  │  DOMAIN  │  │   intents/* + donations + domain models
                                    │  │ (no deps │  │   (Intent, IntentResult, context, AudioData*)
                                    │  │ outward) │  │
                                    │  └──────────┘  │
                                    └───────────────┘
              ports = core/interfaces/* (the boundary both sides depend on)
```
**The rule:** dependencies point **inward**. Domain depends on nothing; application depends on domain + ports;
adapters depend on ports; nothing inward imports an adapter or a delivery module. `config` is **composition/
infra** — read by the composition root, not depended-upon-by-being-imported-up-into.

### What it takes to get there (the gap = the §2/§3 leaks)
1. **ARCH-1** — split `intents/models.py`; move IO/context primitives inward/foundational so the domain has no
   outward deps and layers stop reaching up into `intents`.
2. **ARCH-2** — break `config→core`/`config↔components`: the schema auto-registry must not import a component;
   `validator` must not import `core.components` (inject `discover_providers` or move it). Remove import-time
   schema validation side-effects.
3. **ARCH-3** — components must not import `web_api`/`analysis` directly: put web-schema generation behind a
   port; treat `analysis` as a driven adapter.
4. **ARCH-4** — formalize ports: ensure every provider category has an interface in `core/interfaces` and
   adapters depend only on it.
5. **ARCH-5** — add an **import-linter** contract (layered + independence rules) wired into CI so the hexagon is
   enforced and can't regress. *This is the deliverable that makes "follows the architecture" verifiable.*
6. **ARCH-6** — resolve the dead `InputManager` queue (wire it as the driving port, or delete it).

This sequencing fixes the real defects, dissolves the backwards edges, and lets `architecture.md` be rewritten
to describe a hexagon that the code actually obeys.

---

## 6. Tasks emitted to `RELEASE_PLAN.md`
- **ARCH-1..6** as above (supersedes the old ARCH-1/2 stubs).
- **DOC-4** rewrite `architecture.md` to the harmonized current state **+ the chosen target pattern** (do after
  the pattern is signed off, so it's written once).
- **DOC-5** fix the CONTRADICTS-code docs (donation spec/paths, asset TOML nesting, train env prefix,
  universal_tts, voice_trigger YAML→TOML).
- **DOC-6** archive the stale historical-plan docs (`config_schemas`, `language_support`, `configuration_guide`,
  `PIPELINE_IMPLEMENTATION`, `irene_current`).
