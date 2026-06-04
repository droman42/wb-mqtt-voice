# Irene — Release Journal

The **single** chronological log for the release effort ("what happened, when, and why"). Append-only;
newest entries near the top of each dated section.

- **This file holds NO task status and NO scope.** The authoritative task ledger (scope + status) is
  [`RELEASE_PLAN.md`](./RELEASE_PLAN.md); findings/rationale live in `docs/review/*` + `docs/design/*`.
- Entries reference task IDs (e.g. `QUAL-27`) but never assert their status — check the ledger for that.

---

## Action journal

### 2026-06-04
- **ARCH-10 PR-3 DONE (`4902438`) — streaming ASR via `OnlineRecognizer` (`model_type="vosk-streaming"`).** Third
  model family on the provider: `OnlineRecognizer.from_transducer` with endpoint detection. `transcribe_stream` now does
  **real incremental streaming** for online models (feed chunks → emit partials → segment + `reset` on each endpoint →
  flush tail on `input_finished`); offline model_types keep the buffer-then-transcribe fallback; `transcribe_audio`
  one-shots the online recognizer (feed + tail-pad + finish + drain). Pack `vosk-model-small-streaming-ru` (verified on
  HF) — **key gotcha:** that repo ships *both* offline (`encoder.int8.onnx`) and streaming (`encoder.chunk64.onnx`)
  exports, so the descriptor uses `prefer="chunk64"` to select the online variant (PR-2's member-aware
  `_pick_pack_files` handles it). The big `vosk-model-streaming-ru` has a different layout (no chunk64) → addable later.
  Capabilities reflect streaming/real_time/offline by model_type; config-master surfaces the option. No assets/pyproject/
  schema change. 18 sherpa unit tests; **0 net suite regressions**. Streaming execution validated at WB7 re-validation
  (sherpa still won't import on the x86 dev box).
- **ARCH-10 PR-2 DONE (`b373633`) — Whisper-ONNX on the same `sherpa_onnx` provider.** A second offline model family
  on one provider/runtime, selected by config `model_type`: `whisper` → `OfflineRecognizer.from_whisper`
  (encoder/decoder/tokens — **no joiner**, whisper's own frontend; `language=""` = auto-detect), `vosk-transducer`
  stays default. Drops torch from 64-bit ASR images that don't otherwise need it. **AssetManager pack download made
  member-aware** (descriptor `members`: transducer=4 files / whisper=3) so `download_model_pack` + `_pick_pack_files`
  fetch exactly the right set; whisper packs = `csukuangfj/sherpa-onnx-whisper-{tiny,base}` (verified on HF: int8
  encoder/decoder + tokens, no joiner). config-master comments surface the option; no pyproject/lock/schema change
  (same `asr-onnx` extra; `model_type` already in the schema). Unit tests for both member sets; **0 net suite
  regressions**. **Flag:** `import sherpa_onnx` fails on the x86 dev box (`libonnxruntime.so` not found in the
  uv-installed wheel) — armv7/WB7 is proven, so this is an x86-image concern for **BUILD-3**; can't exercise sherpa
  execution locally until resolved (the from_whisper/from_transducer API is documented/stable, so code follows it).
- **ARCH-10 PR-1 DONE (`6e1a88a`) — `sherpa_onnx` ASR provider (offline VOSK Zipformer2).** New provider behind the ASR
  port running the alphacep VOSK Zipformer2 ONNX family via `OfflineRecognizer.from_transducer`, alongside vosk/whisper.
  **numpy-free** PCM/WAV→float (stdlib `array`/`wave`) so it runs on armv7; `SherpaInferencePolicy` (platform
  num_threads); lazy load + `warm_up()` gated by `preload_models` (absorbs the ~38 s graph-init). **AssetManager**
  gained additive **multi-file model-pack** download (`download_model_pack`: resolves encoder/decoder/joiner/tokens from
  the HF repo, int8 preferred, into the mounted asset folder; single-file path untouched). Build contract done **right**
  (`get_python_dependencies()->["asr-onnx"]`); `asr-onnx` pyproject extra carries the PEP 508 arch split
  (armv7l==1.10.46 / else >=1.11, no torch) + entry-point + added to `all`. Profiles: `embedded-armv7` and `full`
  switched off whisper (torch — can't run on armv7) to `sherpa_onnx` (small-ru edge / big vosk-model-ru 64-bit);
  canonical block in config-master. **Invariant #4 turned out to be a real schema seam** (not just raw TOML): registered
  `SherpaOnnxASRProviderSchema` in `config/schemas.py` + `AutoSchemaRegistry` — the master-config completeness tests
  caught the missing schema and now pass. Unit tests (numpy-free conversion, policy, build contract). **0 net new suite
  failures** (84 vs 85 baseline — one pre-existing config-completeness failure incidentally fixed). WB7 hardware
  re-validation deferred to ARCH-10 completion (user). **Remaining:** PR-2 whisper-onnx · PR-3 streaming · PR-4 VAD ·
  PR-5 wake-word.
- **ARCH-9 DONE → `docs/design/onnx_inference_layer.md` complete.** Closing additions after the draft: (a) confirmed the
  **system-dependency** path and found the **armv7 image must move Alpine→glibc/Debian** — sherpa-onnx has no musl build
  (proven on WB7: `import sherpa_onnx` fails on Alpine, works on `arm32v7/python:3.11-slim-bullseye`); the contribution
  *mechanism* is fine, only the base/pkg-manager/platform-key flip (apk→apt, `linux.alpine`→`linux.ubuntu`). (b) Recorded
  the **contribution principle as an invariant** (providers self-declare deps → build_analyzer collects enabled → Dockerfiles
  consume); *what* is contributed and the platform taxonomy are mutable (alpine now vestigial). (c) **VAD + wake-word
  resolved for both scenarios:** **WB7** delegates both to an **ESP32 satellite** (microWakeWord C-header + numeric VAD →
  WS to Irene → offline ASR `skip_wake_word=True`; matches ARCH-6/`ws_esp32_transport.md` exactly → armv7 image is ASR-only,
  `tflite-runtime` moot). **Standalone 64-bit** (the only path where Irene does its own): **two wake-word providers**
  (`openwakeword` ONNX / `microwakeword` tflite) **mutually exclusive via toml**, and **two VAD impls** (`energy` bug-fixed
  / `silero` SileroVAD-onnx) **mutually exclusive via toml**; today's voice-trigger providers are hallucinated cruft →
  **greenfield rebuild** (QUAL-19/20); sherpa-KWS is the future swap-in once a Russian base model exists. ARCH-10 sliced
  PR-1..5 (§12). Draft history below.
- **ARCH-9 design session (drafting) → `docs/design/onnx_inference_layer.md`.** Re-anchored the task on its
  real trigger (the new **alphacep VOSK** Zipformer2-ONNX models + which Irene models have sherpa-onnx counterparts), not
  a generic sherpa survey. **Proved armv7 feasibility on the real target (Wirenboard 7.2, A40i)** — SSH'd in, ran the
  alphacep `vosk-model-small-ru` in an `arm32v7/python:3.11-slim` container (matching the deployment): **correct Russian
  transcript, RTF 1.15, 110 MB RSS, 27 MB int8 model, 38 s load**. Key empirical findings baked into the doc: pin
  **`sherpa-onnx==1.10.46`** (1.13.2 has an armv7 `libonnxruntime.so` ELF-alignment bug), **`onnxruntime` has no armv7
  wheel** (so vosk-tts/plain-onnx can't run on the edge; sherpa works because it bundles its own ort), **`libasound2`**
  needed, **offline + small-model only on armv7**, **WB7 is Debian/glibc** (not Alpine). **Decisions locked:** new
  `sherpa_onnx` ASR provider running **alongside** vosk/whisper; **offline-first** (streaming later); **Whisper-ONNX in
  scope** (drops torch); ASR-centric (TTS/wake-word not sherpa targets — silero stays torch, vosk-tts stays its own ort
  as a config story, wake stays TFLite — no RU sherpa-KWS); **armv7 = no TTS**. Shared seam = **AssetManager extension +
  thread/CPU policy**, NOT a shared session runtime. Per-platform **dependency functions** (PEP 508 arch markers,
  libasound2, no torch) documented; build_analyzer marker-passthrough flagged for BUILD-5. WB7 test artifacts cleaned up
  (base image + key kept for the VAD/wake-word benchmarks). **Open: VAD + wake-word placement** (next).
- **QUAL-39 DONE — audited the 19 untyped REST endpoints; typed the UI-5-critical donations contract pair + `/health`
  (Option 2).** The audit immediately found what the task was filed to catch: `GET/PUT /donations/{handler}/contract`
  (UI-5's target) were untyped. Reconciliation: among the 19, config-ui/UI-5 consume **only** the contract pair — its
  status/config/NLU reads already hit typed endpoints (`/intents/status`, `/configuration/config/status`), not the
  untyped system ones (so the "+3 system endpoints" idea was dropped; typed only `/health`). **Approach refined by a
  discovery:** the contract body is a passthrough of `contract.json`, which has a **canonical JSON Schema**
  (`donation_contract_v1.1.json`, `additionalProperties: true`) — a strict Pydantic body would drift from it AND drop
  fields on the editor's GET→PUT. So typed the **envelopes** (`DonationContractResponse`/`DonationContractUpdateResponse`,
  mirroring the language models) and left the body `Dict[str,Any]`. **Symmetry analysis (user asked how the language part
  is delivered):** the phrasing side already does exactly this — `LanguageDonationContentResponse.donation_data:
  Dict[str,Any]` passthrough + its own schema `donation_language_v1.1.json` — so the contract fix brings it to **parity**;
  UI-5 generates both BODY types from the two JSON Schemas, envelopes from OpenAPI (updated UI-5's note). Classified the
  rest: (b) legit-dynamic/non-JSON (asyncapi/html/prometheus/components/debug) documented; non-UI-5 hygiene (asr/monitoring/
  nlu_analysis/system-status) deferred. Verified: models accept the real GET/PUT shapes incl. passthrough extras, modules
  import, suite 85=85 (0 net regression).
- **config-ui ↔ `../wb-mqtt-bridge/ui` stack comparison + harmonization kickoff (pre-UI-1/2/3/5).** Compared the two UI
  stacks: same foundation (React 18 / Vite 5 / TS-strict / Tailwind / react-router 6) but very different altitude — the
  bridge is a tested, lint-gated, MUI + react-query + zustand + OpenAPI-generated dashboard; config-ui is a lean,
  test-less, un-linted Monaco editor on native `fetch` + ~37KB hand-written types. **User decisions:**
  (1) **Strict linting (insisted) → UI-6:** added a **bridge-identical** `.eslintrc.cjs` (type-aware
  `recommended-type-checked`; `no-floating-promises`/`no-misused-promises` errors; `any`-noise rules off) + the eslint
  devDeps + `lint`/`lint:fix`/`check` scripts at `--max-warnings 0`; fixed the runtime↔types version skew
  (`@types/react` 19→18, `@types/node` 24→20 to match `react@18`); added `engines`. `npm run type-check` stays green.
  The strict gate immediately surfaced **71 pre-existing issues** incl. a **real latent bug** (`PromptEditor.tsx`
  variable `description:` shadowed by the prompt-description branch — fixed). **Cleaned up all 71 (user-directed):**
  51 async → `void`/arg-aware-wrap, 14 `exhaustive-deps` → disable+reason (mount loads, fns not memoized → adding deps
  loops), 5 type-assertions auto-fixed; `npm run check` + build green (no test net → type-check/build are the safety net).
  Folded the strict lint into the Invariant-#4 config-ui DoD + BUILD-4 (now `npm run check && npm run build`). **UI-6 DONE.** (2) **Data-layer: "stop fighting
  type drift" → generation-only, folded into UI-5:** rebuild UI-5's `src/types/*` by **generating** from the FastAPI
  OpenAPI schema (`openapi-typescript`), not hand-authoring — the backend is ~80% typed (104/123 routes have a
  `response_model`). Prereq: a backend script to dump `app.openapi()` to a committed `openapi.json`. **axios + react-query
  ruled OUT** (config-ui is load-edit-save, not a server-cache dashboard). (3) **Filed QUAL-39** to audit the ~19 routes
  that return raw `dict` (weak generated types) — gates UI-5's generated-type quality. No behavioral code changed yet.

### 2026-06-03
- **QUAL-7 CLOSED-AS-OBSOLETE (Invariant #8, user-approved).** Surfaced while reconciling the QUAL-3..7 static-baseline
  backlog against Gate-2 relevance: QUAL-7's premise (a `train_schedule` config-master-vs-model mismatch) no longer exists
  — the `train_schedule` handler + config/assets were removed in **QUAL-34**. Verified `train_schedule` is absent from
  `config-master.toml`, `config/models.py`, and all of `irene/`/`assets/`/`configs/`. Nothing to reconcile → closed, no code
  change. (QUAL-3..6 remain valid static-baseline cleanup, none on the Gate-2 critical path.)
- **QUAL-24 DONE — service-locator → domain-owned ports in 8 handlers (Invariant #3, user-approved Option A).**
  Process note: I initially started this by grepping code and nearly committed to injecting `component_manager` (which
  removes the *import* but leaves the domain runtime-coupled to a core registry — an Invariant #3 violation). The user
  stopped me, pointed to the Invariants. Re-anchored on #3/#5/#8/#9, read the invariants + `phase1_architecture_map.md`
  (§2.3–2.5: intents=domain, core=application; `intents→core` is the outward sin), and brought a hexagon-compliant
  proposal. **User chose Option A (domain-owned ports).** Added `irene/intents/ports.py` (Protocols: `LLMPort`/`TTSPort`/
  `AudioPort`/`ASRPort`, shared `ComponentControlPort`, `ComponentControlRegistryPort`); the 8 handlers depend only on
  these; `IntentComponent.post_initialize_handler_dependencies` injects the real components inward as structural impls
  (components import nothing → no new edges). `system` reuses the already-injected `context_manager`; `provider_control`
  gets the registry port. Removed `get_core()` from every handler + the ARCH-1 `ignore_imports` hatch — **ARCH-1 now holds
  with no hatch (9/9 kept)**, proving the transitive `intents→core.engine→{components,inputs,workflows}` pull is gone.
  Honored Invariant #9 (removed `TYPE_CHECKING` guards in the 6 touched handlers that had them; the 2 untouched handlers'
  guards stay for QUAL-32). Caught a latent bug: the old `await component_manager.get_component(...)` awaited a **sync**
  method, so the get_core fallback was already broken — injection is what actually worked. Invariant #4: no backend
  contract changed → config-ui untouched. Suite 85=85 FAILED (0 net regression). **Hardening (user-directed, same
  session):** user asked "who implements the ports?" — verified, and it surfaced that the ports (consumer-defined)
  faithfully captured 4 **pre-existing dead handler calls** (`stop_synthesis`/`cancel_synthesis`/`pause_audio`/`resume_audio`
  with no implementer) AND that the old injection only wired `conversation` (the other 5 handlers were getting `None`). Per
  the user's directive, converted the ports from Protocols to **ABCs** and made the application **components inherit** them
  (`components→intents.ports` = application→domain, inward; 9/9 contracts kept) so unimplemented methods fail at
  instantiation. Implemented the 4: audio pause/resume delegate to providers (real); TTS stop/cancel are honest best-effort
  (providers can't interrupt). Removed the orphaned global-core service-locator (`get_core`/`set_core`/`_global_core`) from
  `engine.py` — zero callers, no test referenced it. The now-wired-but-untested handler paths are **filed as TEST-8**
  (capability-port handler coverage, a TEST-7 coverage goal).
- **ARCH-12 DONE — removed the last two residual upward edges; locked `utils` with contract #9.** Edge 1
  (`utils.vad → core.metrics`) was a **dead import** (`get_metrics_collector` imported but never called — a Phase-4
  leftover after VAD metrics unified into `MetricsCollector`); deleted it. Edge 2 (`utils.logging → config.models`):
  relocated the standalone `LogLevel` enum **into `utils.logging`** and re-exported it from `config.models`, inverting
  the edge to `config → utils` (downward, allowed) while every `from config.models import LogLevel` still resolves;
  dropped the now-dead `from enum import Enum` in `config.models`. Added the 9th import-linter contract "Utils
  (foundation) depends on nothing upward" (`source=irene.utils`, forbids all 9 sibling layers), teeth-checked (planted
  `utils→config` → BROKEN). One self-inflicted hiccup: the teeth-check's `git checkout -- vad.py` clobbered the
  uncommitted edge-1 edit (restoring the dead import); re-applied it and re-verified clean — lesson: don't `git checkout`
  a file with uncommitted edits to undo a planted violation. Verified: no cycle, 9/9 contracts kept, suite 85=85 FAILED
  (0 net regression). Synced `phase1_architecture_map.md` §2.3 (Invariant #5) — closes the last backwards-edge findings
  there. The whole hexagon (ARCH-1..6, 11, 12) is now clean *and* enforced by contracts.
- **ARCH-13 DONE — retired the dormant `irene/plugins/` legacy system.** Reconciliation surfaced that ARCH-11/S2 had
  re-rooted only the Component/Workflow ports — the **8 capability ports still extended `PluginInterface`** — so completing
  decision (c) was a prerequisite here (the ARCH-13 entry had anticipated this). Probed the risk surface first: nothing
  reads `.version`/`.description`/`.configure()` via the plugin contract (components get `.name` from `Component.__init__`,
  lifecycle from `ComponentPort`), so re-rooting only *relaxes* abstract requirements — can't break instantiation, only MRO
  (caught at import). Re-rooted all 8 ports onto `EntryPointMetadata` (script-driven), MRO-smoke-checked the
  `Component`+port diamond on real components. Then **deleted** `irene/plugins/` (`AsyncPluginManager`/`BasePlugin`/
  `PluginRegistry`/`builtin/`) + `core/interfaces/plugin.py`; stripped the plugin lifecycle from `engine.py` (init/load/
  unload + the injected `plugin_manager` param/attr) and its construction from `runners/composition.build_core`; rewired the
  ~8 service-locator status readers (`cli.py`/`base.py` "Plugins loaded" line dropped; `webapi_router` ×4 sites +
  `webapi_runner` plugin blocks removed — the `hasattr`-guarded ones were already graceful; `components.py` service-map
  entry dropped); cleaned dead `irene.plugins.builtin` refs in `build_analyzer.py`. NB: distinct from **QUAL-24** (that's
  `get_core()` in intent *handlers* — different sites, still open). Verified: all affected modules import, 8/8 contracts
  kept, suite **85=85 FAILED** (0 net regression), no live refs to retired symbols (only provider docstrings note the old
  paths). `core→plugins` was already clean from ARCH-11/S3.
- **ARCH-11 S4 DONE — locked the inversion; ARCH-11 COMPLETE.** Added the 8th import-linter contract "Core does not import
  the outer layers (ARCH-11)" (`source=irene.core`, forbidden `irene.{inputs,workflows,components}`). Found there were **no
  literal ARCH-5 exemptions** to remove — ARCH-5 had simply left these composition-root edges *unenforced* (added no
  contract at all), so adding the enforcing contract IS the revocation. Guarded against the `irene.core.components` vs
  `irene.components` package-name gotcha (different packages — no false positive). **Teeth-checked**: planted a temporary
  `core→inputs.manager` import → contract went BROKEN (7 kept/1 broken); reverted → 8 kept. The generic contracts test
  (`test_import_contracts.py`) covers the new contract automatically; updated its docstring. **8/8 contracts kept**, suite
  **85=85 FAILED** (0 net regression). **ARCH-11 closed across S1-S4** (4 edges inverted, decision (c) applied, construction
  moved to the composition root, all locked). Legacy `irene/plugins/` teardown stays split to ARCH-13 (core→plugins is
  incidentally already clean as an S3 byproduct).
- **ARCH-11 S3 DONE — construction inversion (edge 4 removed; all 4 edges now done).** Topology was friendly: a single
  production instantiation (`runners/base.py:85`, inherited by every runner) plus two `examples/` demos. Added the
  composition root `irene/runners/composition.build_core(config, config_path)` which constructs ALL 7 managers
  (component/plugin/input/context/timer/metrics/workflow, preserving the original dependency order — input/workflow need the
  component manager) and injects them into `AsyncVACore`. `AsyncVACore.__init__` is now keyword-only DI and constructs
  nothing; it **no longer imports `inputs.manager`** (edge 4) **nor `plugins.manager`** (bonus: `core→plugins` gone, which
  de-risks ARCH-13) — those two outward managers are typed `Any` in core so the edge stays out. Routed `runners/base.py` +
  both demos through `build_core`. Verified: zero `core→{inputs,plugins}` imports remain, `build_core(CoreConfig())`
  assembles a core with all 7 managers wired, import-linter **7/7 kept**, suite **85=85 FAILED** (0 net regression).
  NEXT = S4 — add the import-linter contracts forbidding `core→{inputs,workflows,components}.base` and remove the ARCH-5
  exemptions, which *locks* the whole inversion so it can't silently regress.
- **ARCH-11 S2 DONE — Component + Workflow ports into `core/interfaces` (edges 2 & 3 removed).** Both `Component` (400 LOC)
  and `Workflow` (257 LOC) turned out to be fat *shared concrete bases* (provider switching, DI, health — `name`/`providers`/
  `initialized` are `__init__` attrs), not thin interfaces, and `core` had **no `isinstance(Component/Workflow)`** checks and
  reached component-specific methods (`synthesize_to_file`, `play_file`) by duck-typing. So rather than relocate the fat code
  into the port layer, I followed the codebase's own `ASRPlugin` pattern: thin ABC ports declaring only the generic
  manager-facing surface. Added `core/interfaces/component.ComponentPort` (initialize/shutdown/inject_dependency/
  get_dependency/get_component_dependencies/get_service_dependencies + name/providers/initialized) and
  `core/interfaces/workflow.WorkflowPort` (initialize/add_component/process_audio_stream/process_text_input/shutdown +
  name/components/initialized) — both `EntryPointMetadata`-rooted (decision c). Fat bases now `Component(ComponentPort)` /
  `Workflow(WorkflowPort)`. `core/components.py` and `core/workflow_manager.py` type against the ports; caught + re-pointed
  the **runtime `issubclass(workflow_class, Workflow)` discovery gate** (a 2nd `workflows.base` import site) to `WorkflowPort`;
  `RequestContext` now imported inward from `intents.context_models` directly (the ledger-flagged domain re-export). Verified:
  no core import of `components.*`/`workflows.*` remains, smoke `issubclass` checks pass for `ASRComponent` +
  `UnifiedVoiceAssistantWorkflow`, import-linter **7/7 kept**, suite **85=85 FAILED** (0 net regression). 3 of 4 edges done;
  NEXT = S3 (construction inversion — edge 4: `engine.py→inputs.manager`, move manager construction to composition/runners).
- **ARCH-11 S1 DONE — input-port consolidation + re-root onto EntryPointMetadata.** First of the 4 staged edges.
  Landed the single input port as `core/interfaces/input.InputPort(EntryPointMetadata)` (+ the `InputData` value type),
  replacing both the former `inputs.base.InputSource` (which created the `core→inputs.base` edge) and the dead duplicate
  `InputPlugin` (was `PluginInterface`-rooted, 0 subclasses). Adapters (CLI/microphone/web) and `InputManager` now
  implement/type against `InputPort`, importing it inward from `core/interfaces`; `inputs/base.py` shrank to just the
  adapter-side `ComponentNotAvailable`. `workflow_manager.py` imports the port inward (3 sigs) → the input edge is
  **removed**. Stripped the now-dead `InputPlugin` refs from the dormant `plugins/manager.py` (behavior-preserving — it
  loads 0 plugins; the `_input_plugins`/`get_input_plugins` bits were always empty). Verified: import-linter **7/7 kept**
  (the SCC-2 `inputs.base`-no-adapters contract still holds), full suite **85=85 FAILED** vs stashed baseline (0 net
  regression). NEXT = S2 (Component+Workflow ports into `core/interfaces`, core imports them).
- **ARCH-11 hierarchy-fork RESOLVED + staging locked (discussion, no code yet).** Opened the deferred ARCH-11 session
  with the `EntryPointMetadata`-vs-`PluginInterface` decision, as agreed. Traced the real graph instead of trusting the
  summary: the live architecture is `EntryPointMetadata`-rooted (every real adapter/component extends it); `PluginInterface`
  is a **near-dead legacy skin** — capability ports have **0 concrete subclasses** (MI mixins only), `core/interfaces/input.
  InputPlugin` is a dead duplicate of `inputs.base.InputSource`, and the whole `irene/plugins/` manager is dormant.
  **Empirically verified it loads 0 plugins:** `engine.py:95` calls `load_plugins()` with no paths → builtin branch is
  `pass` → `_plugins` stays `{}`; the ~8 `core.plugin_manager._plugins` status readers all report 0. **Decision (c):**
  retire `PluginInterface`, re-root all ports onto the single clean base `EntryPointMetadata` (abc+typing only; the
  `core/interfaces` port layer is already import-clean) → clean dependency direction + enforceable contracts. Honest
  asterisks recorded: `EntryPointMetadata` stays a "fat" root (concern-bleed, not a direction violation — purist split is
  Gate-2 gold-plating) and ARCH-12's residual edges survive. **Scope staged:** full (c) forces touching the legacy system
  (typed on `PluginInterface`) which is read via the QUAL-24 service-locator pattern at ~8 status sites — so the teardown
  is **split to new ARCH-13** to keep ARCH-11 a single-purpose, bisectable hexagon commit before Gate 2. ARCH-11 = invert
  4 edges + re-root ports + consolidate input port + contracts; ARCH-13 = delete `irene/plugins/`, finish `PluginInterface`
  removal, rewire the 8 readers. Locked into the ARCH-11 ledger entry + filed ARCH-13.
- **ARCH-6 CORE DONE — WS streaming-input driving adapter + room/device activation (design + implement, per user).**
  Reconciliation up front (with the user): scoped to the **transport + identity core**, because the **device-model half**
  has no substrate yet (no device/room handlers, all 13 `entity_type` decls `generic`, no MQTT handler) — authoring it now
  would be the ledger's own "inert branch", so it's **relocated to ARCH-7 [MQTT] + QUAL-35**. ESP32 firmware is stale →
  designed **server-first** (`docs/design/ws_esp32_transport.md`). Built `/ws/audio` (`webapi_router.py`): registration
  handshake → `ClientRegistry.register_client` → stream raw PCM (16k/mono binary frames) → `process_audio_input` with
  `skip_wake_word=True` (on-device wake) → response frame. The pipeline entry already accepted `client_context`
  (`client_id`/`room_name`/`device_context`), and `resolve_physical_id` already returned `client_id or room_name or
  session_id` — so the activation is exactly: **the handshake populates those, and the physical origin keys the action
  store**, no seam rewrite. Made `ClientRegistration.from_dict` tolerant of the handshake's control keys (`type`/
  `sample_rate`/`wants_audio`). Removed the dead P0-8 base64 `AUDIO_DATA:` branch (`inputs/web.py`); kept `_input_queue`
  (it's live — CLI/mic input). Tests: `test_ws_driving_input.py` (3 — incl. an end-to-end TestClient handshake→pipeline
  with a stubbed core). **SCC-2 cycle FIXED — and the user caught a wrong first approach.** My initial instinct
  (entry-point/runtime discovery) would have been a **service-locator** — the exact pattern this project is removing
  (QUAL-24). The correct fix is dependency *separation*, not service-location: `inputs.base` mixed the `InputSource`
  PORT with the `InputManager` ORCHESTRATOR (which legitimately imports the concrete adapters). Split them —
  `InputManager` → `irene/inputs/manager.py` (the input-layer composition point); `base.py` now imports NO adapters →
  clean DAG `base ← {cli,web,microphone} ← manager`, deps point inward to the port. **Locked with a new import-linter
  contract** ("Input port does not import its adapters") so it can't regress. Also corrected the device-half hand-off
  bookkeeping: QUAL-35 now explicitly OWNS the `entity_type`/`room_context` authoring + `_is_device_entity` swap (it had
  stale-pointed back to ARCH-6); ARCH-7 references the device handlers as its substrate. 0 net regressions; 7/7 import
  contracts kept. **ARCH-6 fully DONE `[x]`** (device-half is QUAL-35's, tracked).
- **ASSET-2 DONE — liveness-checked every model download URL; fixed 2 real defects.** Swept all 33 model URLs in
  `irene/` (range-GET each, judging on bytes-served vs stall per the fake-IP caveat — all hosts resolve into
  `198.18.0.0/15`, normal). Hosts all healthy: silero.ai served the real 40MB `v4_ru.pt`; alphacephei/vosk, github
  releases (openWakeWord v0.5.1), openai whisper-CDN, github/spacy-models (3.7.0) all 200/206. **Fixed:** (1) the whisper
  `tiny` URL had a **truncated 40-char hash** → 404; restored the full 64-char canonical hash (cross-checked against the
  installed openai-whisper `_MODELS`; the other 6 were correct). (2) silero `v4_en/de/es/fr` were declared but **404** —
  silero's v4 line is **Russian-only** (`v4_ru` ✓, `v4_ua` exists; western langs stay at v3); trimmed the `silero_v4`
  catalog to `v4_ru` and documented that non-RU TTS uses `silero_v3` (its en/de/es are live). **Left dead by design →
  QUAL-19:** microWakeWord's `micro_speech.tflite` (github tflite-micro raw moved) — a TF demo model in a known-placeholder
  provider, so it's the ESP32/wakeword keep-fix-cut call. Torch.hub hedge not needed (silero healthy). Updated the
  `irene-stale-models` memory (URL liveness-check now closed). Providers import clean; 0 net suite regressions.
- **QUAL-34 DONE — declared-but-unconsumed donation params triaged per-handler WITH the user, then wired-or-removed.**
  The user drove the wire-vs-remove call for each of the 19 (and asked good clarifying questions — e.g. confirmed the
  conversation handler is fundamentally raw_text→LLM so its `topic`/`query_topic`/`context_reference` slots add nothing;
  flagged `train_schedule` as bogus → remove the whole handler; chose to BUILD capability rather than minimize surface).
  **Outcome:** removed 9 params + the whole train_schedule handler; wired 10 via the typed `get_param` accessor (the same
  accessor that activates the QUAL-30 clarification boundary). Highlights: `voice_synthesis.voice` migrated off the
  raw_text re-parse to the canonical NLU entity (Bucket B); `datetime.relative` got a real date-offset + localized
  lead template (`date_relative`/`relative_leads`, "Завтра: …" / "Tomorrow: …"); `greetings.time_of_day` honours an
  explicit "good evening" over the clock; `text_enhancement.{improvement_type,correction_type}` steer the LLM via a
  SYSTEM-prompt focus directive (kept out of the user text, QUAL-16 injection-safe); the system/system_service params
  are consumed (with `detailed` a real verbosity toggle) where the handlers have real data, surfaced-as-scope where
  they're generic stubs. **Surface fixes:** several CHOICE params had wrong-English ru surfaces / missing en surfaces
  (e.g. correction_type, metric_type) — authored proper bilingual ones per the donation-choice-surfaces rule.
  **Discipline:** committed in 3 parts (removals → 2a wirings → 2b wirings); caught a missed
  `assets/templates/train_schedule_handler/` (part 1's `git rm` only took the donations dir — user flagged "did we
  remove ALL assets?"). New `test_qual34_param_wiring.py`; audit doc marked resolved; 0 net suite regressions across all
  parts; donations load 0 warnings. The declared-param audit is now clean.
- **QUAL-21 DONE — settings-runner `ComponentConfig` crash-bug resolved by REMOVAL (user decision).** The
  `irene-settings` Gradio runner constructed `ComponentConfig(audio_output=…, microphone=…, web_api=…)` — fields
  removed in the architecture migration (mic/web → `config.inputs.*` / `config.system.web_api_enabled`,
  `audio_output`→`audio`) → crash on launch. User judged the runner obsolete ("garbage") → **removed** rather than
  fixed: config management is now config-ui's TOML editor / direct file edits. Deleted `settings_runner.py` (462 LOC)
  + both pyproject registrations + `runners/__init__.py` exports; scrubbed README, `architecture.md` (usage block +
  the "Settings Режим" Mermaid subgraph), `tools/migrate_runners.py`. **Retired all 4 stale demo examples**
  (`component_demo`/`dependency_demo`/`config_demo`/`utilities_demo` — they demoed the removed optional-components
  model; user picked "retire all 4" via AskUserQuestion) and fixed `examples/__init__.py` (it imported `config_demo`).
  Verified: runners + examples import clean, the 3 remaining runner scripts resolve, no stale `ComponentConfig` kwargs
  remain in `irene/` (the leftover `audio_output`/`microphone` hits are device-capability keys / device enumeration /
  the intentional v13→v14 migration reader), 0 net suite regressions. Net −~900 LOC of dead runner+demo code.
- **QUAL-37 [DFLOW] DONE — targeted no-intent clarification (offline path).** The signal
  (`_fallback_context.likely_domain`, computed by `_create_fallback_intent`) was already consumed on the ONLINE path
  (QUAL-16's `_build_fallback_context_prompt` injects the guessed topic into the LLM prompt); the gap was the OFFLINE
  (no-LLM) path, which gave a generic "didn't understand «…»" responder. Now `_handle_fallback_without_llm` reads
  `likely_domain` and, when it maps to a known domain, returns a **deterministic, localized, offline** targeted
  explain-and-ask ("Возможно, вы хотели поставить таймер?" / "Did you want to set a timer?") — new `fallback_targeted`
  template + a `fallback_domain_labels` map (domain→friendly action phrase) added to the existing
  `assets/localization/conversation/{ru,en}.yaml`; otherwise it falls through to the generic responder (no guess /
  unknown domain). Result metadata gains `targeted`/`likely_domain`. Both fallback paths now consume the NLU's guess.
  Tests: `test_no_intent_clarification.py` (5) — targeted ru/en, generic + unknown-domain fall-through, determinism +
  offline; 0 net suite regressions. **Ledger hygiene (user-flagged):** there were two QUAL-37 entries — the QUAL-36
  done-edit had only matched the first 2 lines of the old QUAL-36 entry, orphaning the rest of its body under a stray
  duplicate QUAL-37 header; removed the corrupted block, leaving the single correct QUAL-37 (now `[x]`).
- **QUAL-38 [DFLOW][I18N] DONE — processing-language config-derive + inline-bilingual externalization (carved from QUAL-36).**
  **Key correction during reconciliation:** the carve-out spec framed (a) as "thread from context", but the processing
  language is the **audio-MODEL/deployment** language (which number-spelling/transcription rules to apply), NOT the session
  language — spelling numbers in the session language while synthesizing with a different-language voice would mismatch.
  So the correct (and lighter) fix is **config/model-derive**, not a request-threading refactor of the QUAL-13 pipeline
  (which would have introduced that bug; the pipeline's "language is request-scoped in principle" comment was the gap, now
  corrected). **(a)** `convert_numbers_to_words` → language-required (caller already threads `request.language`);
  `PrepareNormalizer` gains a config `language` and stops falling back to inline `"ru"`; `unified.py` threads the per-normalizer
  deployment language to both number normalizers; `silero_v3|v4` derive `self.language` from model config (default `*_ru.pt`
  → ru); `asr_component` transcribe endpoint resolves to `self.default_language`. Left the standalone `utils/text_processing.py`
  library defaults and the Pydantic request-schema `"ru"` defaults as documented library/API defaults. **(b)** Re-classified
  the ~33 `== 'ru'` branches: the genuine **inline RU/EN strings** were only in 4 handlers — externalized voice_synthesis (6)
  + system (3) + provider_control (5, NEW template dir + a `_get_template` method) to template assets, and unified
  random_handler (3) by adding `{error}` to the ru templates so the `== 'ru'` arg-branch could go. **Kept as legitimate**
  (done-criteria allows): `system_service_handler` Russian **pluralization grammar** (the strings were already templated; the
  branch only computes plural suffixes) and the Russian command-keyword **parsing** in voice_synthesis. **Verified:** all new
  templates load + resolve in ru/en; precise mine-vs-baseline diff = **0 new failures**. Closes the QUAL-36 carve-out.
- **QUAL-36 [DFLOW][I18N] DONE — single language source-of-truth; hardcoded `"ru"` purged from the session path.**
  **Reconciliation found the spec was incomplete:** not one language source but FOUR competing declarations
  (`CoreConfig.language="en-US"` in locale form *and* actually consumed; `nlu.default_language`/`supported_languages`;
  `nlu_analysis.languages.*`; `IntentAssetLoader`'s own `"ru"`/`["ru","en"]`). Surfaced the conflict via AskUserQuestion;
  user chose **promote to a top-level canonical `CoreConfig.default_language` + `supported_languages` (2-letter)** read
  at the composition root and injected inward — `nlu.*`/`en-US`/asset-loader derive/retire. **Implementation, correctness-
  first (establish the invariant BEFORE deleting fallbacks):** added the canonical fields + removed the `nlu.*` duplicates
  (config-master.toml synced); injected `default_language`+`supported_languages` into `ContextManager` (mirrors the existing
  `max_history_turns` DI) and seeded sessions; repointed NLU detection to the canonical source + made `_analyze_text_language`
  return `None` on no-signal (caller applies the default, clamped to supported); threaded canonical into NLU **and** LLM
  provider configs. Then **deleted all 67 `context.language or "ru"` fallbacks** → bare reads; ripped out the timer/audio/
  voice-synthesis `_get_language` Cyrillic-sniff heuristics; **fixed a real bug — `hybrid_keyword_matcher` defaulted to `'en'`
  while everything else defaulted `'ru'`**, so an unset language partitioned keywords wrongly; made handler `language="ru"`
  default params required (keyword-only where they followed defaulted args). Added **`context.supported_languages`** (seeded
  from canonical) so the `system.py` language-switch validates against it — no baked `["ru","en"]`. **A real non-RU bug
  caught:** `RequestContext.language` defaulted to `"ru"`, and the request→session merge overrides on any truthy value — so
  an unspecified request would STOMP an English seed; changed the default to `None` ("unspecified"). **T7 (folded from
  QUAL-16):** localized the LLM machine-context labels (`Currently active:`/`Session:`/`Recent activity:`/`Thread:`/`Actions:`/
  `Flow:`/`Context:`) → `assets/localization/conversation/{ru,en}.yaml` + a `_context_label` resolver keyed by user language
  (with an offline English last-resort, console-floor pattern). **Folder-naming note (user-flagged live):** localization uses
  bare domain dirs (`conversation/`, like `voice_synthesis/`/`datetime/`), distinct from the `_handler`-suffixed prompt/template
  dirs — both key to `"conversation"` via the loader; verified, not a duplicate. **Verification:** new
  `test_language_source_of_truth.py` (6 tests) proves English-primary AND arbitrary-language (`de`) seeding, detection clamp,
  `supported_languages` on context, label localization, and the no-stomp contract; updated the one test that encoded the old
  `RequestContext`→`"ru"` default; **precise mine-vs-baseline diff = 0 new failures** (the perf/VAD timing tests are flaky and
  fluctuate run-to-run). **Carve-out → QUAL-38** (filed): processing-language defaults (number-spelling/silero/ASR/text-proc)
  + inline bilingual handler messages (`== 'ru'` branches) are a distinct concern from the session source-of-truth. Hexagonal
  held: domain reads `context.language`/`context.supported_languages`, never imports config; the composition root injects.
- **QUAL-17 [STREAMAPI] DONE — critical review of the streaming-API exposure; keep/upgrade/replace filed.** Found the
  surface is **two** independently hand-rolled subsystems, not one: a 474-LOC code-first generator
  (`irene/api/asyncapi.py` — `@websocket_api`/`WebSocketRegistry`/custom Pydantic→AsyncAPI **2.6.0**) **and** a fully
  bespoke **923-LOC renderer** at `/asyncapi` (`assets/web/{templates/asyncapi.html, static/js/asyncapi.js,
  static/css/asyncapi.css}`). **Three ledger-description corrections** (recorded in the review doc): the renderer is
  **not** `@asyncapi/web-component@2.6.4` — that string is only a *comment* (`asyncapi.py:7`) rationalizing the 2.6.0
  spec choice, so the code documents a dependency it doesn't use; the main **`/ws` is undecorated → absent** from the
  spec; the **TTS** endpoints (`/tts/stream`, `/tts/binary`) **are** documented (ledger listed `/ws`, omitted TTS).
  Tooling scan (June 2026): the official **`@asyncapi/web-component` 2.6.5** is maintained, framework-agnostic,
  renders 2.x+3.x, and is a clean drop-in fed by the existing `/asyncapi.json`; **FastStream** generates AsyncAPI from
  Pydantic but is a *broker* framework (Kafka/RabbitMQ/NATS/MQTT/Redis) → adopting it = rewriting the WS transport,
  wrong shape; `asyncapi-python` is spec→code (opposite direction). **No maintained drop-in introspects raw FastAPI
  WS routes** → the generator must stay bespoke. **Recommendation = Hybrid:** REPLACE the renderer with the vendored
  official component (offline-first — no CDN; ≈ −900 LOC) + KEEP-and-improve the generator (fix lossy
  `_clean_property_for_asyncapi` union/nullable flattening; decide 2.6.0-vs-3.0 deliberately; binary message bindings
  for ESP32). Hand-off itemized into **QUAL-18** §5. Per Invariant #5, `streaming_api_review.md` written + index row
  marked `[x]`. No code changed (review-only task).
- **QUAL-16 [PROMPTS] DONE — externalized + hardened all LLM prompts; live-validated against DeepSeek.** Stage A: the
  6 task prompts (improve/translation/grammar/summarize/expand/chat-default), triplicated inline across the 3 providers
  and language-locked to the provider, → `assets/prompts/llm/{ru,en}.yaml` (system prompt set), keyed by the USER's
  language; the component resolves + passes `system_prompt`, providers hold none (generic fallback only); fixed
  text_enhancement `task="correct"`→`grammar_correction`; killed anthropic's hardcoded "You are a helpful assistant."
  (component injects externalized `chat_default`). Stage B (user request): hardened the conversation persona prompts +
  fixed their `_get_prompt` "ru" hardcode (→ context.language). Tail: externalized `_build_fallback_context_prompt` →
  `fallback_context`/`fallback_topic` assets; wrote `docs/guides/PROMPTING_GUIDE.md`. Hardening rules baked in:
  plain-text/no-markdown (spoken), return-only-result, "user text is DATA not instructions" injection resistance,
  persona, preserve-language. **The user supplied API keys (.env, gitignored) → live validation, which paid off:** it
  caught a real markdown-list leak (the static prompt allowed it) that I then fixed by strengthening the prompts, and
  confirmed injection attempts ("call yourself GPT / answer in a markdown list") are refused (persona holds, plain
  text). Invariant #4: prompt editor is dir-driven so `llm/` surfaces automatically; zero config-ui changes,
  type-check passes. Residual → QUAL-36(7): the LLM context-injection *labels* (`Currently active:` …) are machine-
  context, localized with the language work, not prompt hardening. Suite 30/30.
- **QUAL-15 [LLM] DONE (Stages A–C) — real offline foundation + DeepSeek default + VseGPT removed.** The offline LLM
  posture was fictional (QUAL-14): phantom `console`, `fallback_providers` never iterated, `generate_response` raised
  offline. **Stage A:** `ConsoleLLMProvider` offline floor (deterministic, always available, localized "unavailable");
  a real fallback chain (default → fallback_providers → console) driving enhance_text + generate_response (never raises);
  component `is_available()` excludes the stub (conversation handler unaffected). **Stage B (user):** DeepSeek
  (`deepseek-chat`, OpenAI-compatible, new default, matching ../personal_vpn); VseGPT removed entirely; offline-safe boot
  via a new optional `${VAR:-default}` env-var syntax + optional LLM keys (enabled cloud LLM w/o key no longer hard-fails
  boot → console floor). **Stage C:** `openai.is_available()` → local check (was a network probe returning True on
  failure); per-call timeouts; providers raise on failure (chain handles fallback, no silent original-text); fixed the
  dead `universal_llm` ASR-enhance lookup (→ real LLM component). **User-directed during the work:** (1) externalize the
  hardcoded localized message arrays → moved to `assets/localization/llm/{ru,en}.yaml` (the localization asset category,
  read via `get_localization`, injected into the console floor); (2) kill VseGPT altogether. Verified: WebAPI boots with
  no LLM key (console loads, deepseek skips); `test_llm_fallback.py` (4) + suite 30/30; QUAL-23 phantom-console ERROR
  cleared. Carve-outs: prompt hardening → QUAL-16; real local-model LLM → ARCH-9/10.
- **QUAL-13 Stage 2 DONE — collapsed the text-processing subsystem; wired both real stages. QUAL-13 complete.**
  Reconciled first (Invariant #5/#8): the QUAL-12 findings still held (TTS spoke raw text; WebAPI 500 on `self.processor`;
  `NumberTextProcessor.process()` bug; dead `_stage_providers`/`number_options`/normalizers config tree). User chose the
  full collapse. Built **`UnifiedTextProcessor`** — one config-driven provider that reads per-normalizer `stages` lists
  and applies a fixed-order chain (numbers → prepare → runorm) for the requested stage. Stages are now data, not classes.
  Deleted the 4 stage-specific providers (asr/general/tts/number) + their entry-points + 4 config schemas (→ one
  `UnifiedTextProcessorProviderSchema`); collapsed `config-master` + `TextProcessorConfig` onto the single `normalizers`
  tree (dropped the dead `[providers.*]` split + `number_options`). **Wired both stages:** `process(stage="asr_output")`
  for the ASR→NLU path; **added the missing `tts_input` normalization in `_handle_tts_output` before `synthesize_to_file`**
  — the actual TTS-correctness win (responses now get numbers→words/symbols normalization; RUNorm available, opt-in).
  Rewrote the 3 broken WebAPI endpoints onto the unified provider's `stage_map`/`normalizers_for_stage`. RUNorm now
  `enabled=false` by default (documented HF-model-download offline hazard). Verified: chains correct per stage, "5 минут"→
  "пять минут", disabled normalizers don't run; `test_text_processing.py` (5) + full suite 26/26; WebAPI boots (smoke).
  **Carve-outs:** optional `llm_text_processor` + the dead `universal_llm` ASR-enhance path → QUAL-15. **QUAL-13 done (Stages 1+2).**
- **QUAL-13 Invariant #4 — VERIFIED config-ui is schema-agnostic (user-prompted; corrected my earlier carve-out).** I had
  initially carved a config-ui text-processor-editor update to UI-5. Wrong: the config editing is fully schema-driven —
  `ConfigurationPage` fetches the backend Pydantic schema (`getConfigSchema()`) and renders each section through a
  generic recursive `ConfigSection` (renders the `providers` tree + nested `normalizers` dynamically; only a
  `text_processor`↔`text_processing` name alias is component-specific). The `TextProcessorConfig` TS type is already
  generic (`Record<string,Record<string,any>>`), so the collapsed shape matches. Changed zero config-ui files; ran
  `npm run type-check` **and** `npm run build` — both pass clean. So QUAL-13 carries **no** config-ui debt; Invariant #4
  satisfied for the config surface. (The donations editor UI-5 deferral is unrelated — that's the donations schema, not config.)
- **QUAL-13 Stage 1 + ASSET-3 DONE — lingua-franca → ovos-number-parser.** Investigated the abandoned MycroftAI git pin
  vs successors (research agent + WebSearch): irene's real usage is tiny (`pronounce_number` only; the stateless OVOS
  successor needs `lang=` per call, no global `load_language`), confined to `irene/utils/text_processing.py`, with a
  pure-Python Russian fallback as the default path. Migrated to **`ovos-number-parser>=0.5.1`** (maintained, PyPI,
  pure-Python → no armv7 concern); ru now routes through the **dependency-free** pure-Python path (proper Russian vs
  ovos's literal "точка", works on edge without the extra), non-ru → ovos (degrades to raw digits if absent). Threaded
  `language` into the regex callbacks via `functools.partial`; `load_language` → no-op; removed the git pin from
  pyproject + lock (`ovos-date-parser` not added — no date parsing needed). Verified ru+en number→words; suite 21/21.
  This is QUAL-13 Stage 1 (de-risk number normalization before the full provider-collapse); **closes ASSET-3**.
- **QUAL-30 [DFLOW] Grade-1 clarification DONE (deterministic responder).** Built the single fail-loud → explain-and-ask
  boundary that the QUAL-11 typed accessor was set up to feed. Reconciled first (Invariant #5/#8): the single catch
  point is `execute_with_donation_routing` (base.py:270 — it already wraps the routed method and maps everything to a
  generic error); `get_param` already raises but nothing caught it; the fallback intent carries a fake `confidence=1.0`;
  templates load per-enabled-handler only. **Implementation:** (1) `get_param` raises structured
  **`MissingRequiredParameter`** (param/description/intent); (2) the boundary catches the `ParameterExtractionError`
  family **before** the generic error → new base **`_clarify()`** → localized single-turn `IntentResult`
  (`success=True`, `metadata.clarification=True`, speaks); (3) deterministic responder via a new **system** template set
  `assets/templates/clarification/{ru,en}.yaml` — and taught `_load_templates` to load system sets unconditionally (not
  tied to an enabled handler), `get_template` handles language→default so **no language hardcoded**; (4) fixed the fake
  `confidence=1.0` → `0.0` (honest no-match; routing keys on `_recognition_provider`, verified safe — smoke's
  offline-conversation test still green). Verified both languages render; `test_clarification.py` (3) green; full suite
  21/21. **Scope (with user's text-first priority):** deterministic path is the offline guarantee = the must-have; **LLM
  phrasing deferred to QUAL-15** (the review frames LLM as the opt-in enhancement, and the LLM foundation is shaky per
  QUAL-14); **device/room → ARCH-6**; **per-handler activation → QUAL-34** (only timer uses the accessor today, with a
  caller default, so nothing triggers clarification in production yet — the mechanism is ready for the migration). Grade
  2 (multi-turn slot-filling) stays QUAL-31.
- **Filed QUAL-36 — single language source-of-truth; purge hardcoded language codes (user observation 2026-06-03).**
  User spotted a hardcoded `"ru"` in a handler and suspected it was systemic — verified: it is. Audit found `context.
  language or "ru"` at **63 handler sites** + `entity_resolver` ×2; context-ignoring hardcodes (`timer._get_language`
  re-detects + `return "ru"`, ignoring the NLU's detected language; `context.py:86` seeds sessions `"ru"`); a real
  **inconsistency bug** (`hybrid_keyword_matcher:422` defaults `'en'` vs everything else `'ru'`); `language="ru"` default
  params; baked `["ru","en"]` sets. **Target architecture (decided with user):** config declares **supported-languages +
  default** → the **session resolves language ONCE** (detection clamped to the supported list, silent fallback to default
  if unconfident/out-of-list) → **downstream just reads `context.language`** with NO fallback/re-detection/literals. The
  insight: don't relocate the default to 70 sites — make `context.language` an **invariant** and DELETE the fallbacks
  (theme ④ "a field means one thing end-to-end"). **Hexagonal (user-required):** config values are read at the
  composition root and **injected inward** (`ContextManager` gets `default_language` to seed with — same DI as its
  `max_history_turns`; NLU component gets supported-list+default to clamp detection); domain never imports config. The
  config fields already exist (`config/models.py:315-316`). User chose: seed-context-read-context-only + silent fallback.
  _Not yet implemented — filed for a focused pass._
- **Donation CHOICE-surface audit + correction (user observation; QUAL-29 migration quality).** Verified Russian
  `choice_surfaces` across all 30 CHOICE params / 14 handlers. Two findings, opposite directions:
  **(1)** The genuinely-missing-Russian bug (the timer-class) was only `timer.unit` — fixed in QUAL-11 Stage D. All
  other **user-facing** CHOICE params (datetime/system/quality/language-names/time-of-day) correctly carry Russian.
  **(2)** The migration's actual systematic flaw was the **inverse — it wrongly *translated* technical identifiers**
  (model/driver/service names, which per the user must **never** be translated; the canonical token is the spoken
  identifier and is self-matchable). Worst case: `speech_recognition.provider` had `azure→"облако"` (literal "cloud"),
  plus `whisper→виспер`, `vosk→воск`, `google_cloud→гугл`; `voice_synthesis.provider` had `silero→силеро`, etc.
  **Stripped both consumed provider params' `choice_surfaces` back to canonical** (English identifier). _Left alone:_
  the transliterations embedded in the **parked T2 `token_patterns`/`slot_patterns`** (inactive at runtime → QUAL-35
  decides whether ASR-transliteration aids belong there); `voice_synthesis.voice` (dead → QUAL-34, and `xenia`/`aidar`
  are real names «Ксения»/«Айдар» a Russian would actually say — a genuine nuance to decide when wiring it); the dead
  user-facing `system_service.metric_type` / `text_enhancement.correction_type` (→ QUAL-34 wire-then-author). **Authoring
  rule established: technical identifiers (models/drivers/services) stay canonical; only user-facing concept choices get
  localized surfaces.** Smoke green.
- **QUAL-9 [FAF] DONE — tail reconciled to metrics re-key + TEST-3; everything else already in QUAL-28.** Per the
  task-start reconciliation (Invariant #8), verified against current code that QUAL-28 had absorbed the entire F&F P0
  set AND most of the documented tail (timeout monitor `wait_for`, duplicate write-back processor deletion, timer-
  cancellation cleanup, capture-before-pop). The only genuinely-open items were the **per-action metrics re-key** and
  **TEST-3** (user-approved this narrowed scope before work). Fixed `metrics._active_actions`: keyed by the unique
  `(domain, action_name)` pair instead of `domain` alone — two concurrent same-domain actions (e.g. two timers,
  `domain="timers"`) used to clobber each other's metric, so completion popped the wrong one and the first leaked as
  perpetually-running. `record_action_completion` now takes `action_name`; updated all 9 callers (6 internal synchronous
  helpers + 3 F&F sites in `base.py`); `get_active_actions_summary` reads `action.domain`. Added the TEST-3 seed
  `test_metrics_concurrent_same_domain_no_clobber`. `test_set_timer_end_to_end` green end-to-end (QUAL-11 recognition +
  QUAL-28 F&F). Suite 18/18. **The QUAL-11 + QUAL-9 arc the user picked — timers working end-to-end — is complete.**
- **Decision (user) — QUAL-11 goes LIGHTWEIGHT (T1); the heavy NLU tiers split out. Filed QUAL-35; entity_type → ARCH-6.**
  Worked through the slot/extraction-pattern fork (P0 #2) and the entity_type fork (Q7b) together — they're the **same
  species** (heavy declarative extraction), and a three-tier picture clarified the call: **T1** = keyword/NER + regex +
  CHOICE surfaces + lemmas (what `hybrid_keyword_matcher`, the hot path, actually runs); **T2** = spaCy `Matcher`/
  `EntityRuler` slot-filling (the authored-but-discarded `token_patterns`/`slot_patterns`/`extraction_patterns`);
  **T3** = dependency-parse / local-LLM NLU. Key facts that drove it: the cascade is `[hybrid, spacy]` fast→slow with a
  0.7 gate, so **T2 lives only in the spaCy fallback** (hybrid explicitly ignores advanced patterns) — and all 66
  `entity_type` decls are `generic`, so entity_type dispatch would be an inert branch. T1 covers the easy ~80%; T2's
  sweet spot is real but narrow (compound durations "2 часа 30 минут"→150min, source/dest by preposition, multi
  param=value in any order, free-text spans, morphology at real-home scale); T3 (negation "кроме", anaphora "его",
  conditionals "если") is what **neither** T1 nor T2 reach. **User's call:** T2+T3 are a **must-have for smart-home/MQTT**
  (not overkill there) → **filed QUAL-35 `[PEX][MQTT]`** (T2 in the spaCy fallback + T3 via local-LLM; gated on ARCH-7/8;
  patterns **parked, not deleted** — optionality preserved, no authoring lost, no schema change so no UI-5 impact).
  **entity_type/room_context consumption + the heuristic swap (Q7b) → moved into ARCH-6** (activates with real
  room/device registration; ARCH-6 now explicitly owns authoring the non-generic types + the `_is_device/location_entity`
  → `entity_type` swap). QUAL-11 keeps only the safe cleanup (dedupe device path + `_resolution_failed`) and refocuses its
  remaining energy on the universal hot-path wins: shared extraction base + required-param contract + typed accessor.
- **QUAL-11 [PEX] Stage E — QUAL-22 (deleted dead disambiguation stub) + P1-t (`_create_error_result` de-shadowed). QUAL-11 lightweight scope COMPLETE.**
  **QUAL-22:** deleted `ContextAwareNLUProcessor._disambiguate_with_device_context` — it computed `enhanced_entities`
  (output_capabilities / context_suggestion / preferred_output_device) then `return intent` unchanged ("for now, return
  original"), dead since inception; the caller now uses the intent directly. Real capability/room-aware disambiguation
  needs registered devices → ARCH-6, not a no-op. Removed the 2 QUAL-22 xfail tests + `test_device_not_found_suggestions`
  (the latter asserted the `available_devices` suggestions from the Stage-C-deleted duplicate path). **P1-t:** 6 handlers
  shadowed the base `_create_error_result(text, error, metadata)` with an **incompatible**
  `_create_error_result(intent, context, error)` — a footgun (the same call meant different things per handler). Renamed
  all 6 to `_error_result(context, error)` (dropped the unused `intent`) across 31 call sites, so `_create_error_result`
  has **one** canonical signature project-wide; each handler keeps its own localized template body. Suite 17/17.
  **QUAL-11 done (lightweight T1 scope): Stages A–E.** Carve-outs tracked elsewhere: T2/T3 patterns → QUAL-35;
  `entity_type` swap → ARCH-6; per-handler `get_param` migration → QUAL-34.
- **QUAL-11 [PEX] Stage D — shared coercion base + typed `get_param` accessor; fixed a latent timer-unit bug.**
  (1) **Shared coercion (theme ②):** lifted the duplicated `_convert_and_validate_parameter` (identical in both NLU
  providers — the "two contracts" divergence) onto **`ParameterSpec.coerce()`** in `core/donations.py`; both providers
  now delegate, so the parameter surface is identical regardless of which won the cascade. (2) **Provider default-on-
  failure fix (P0 #3):** the hybrid extraction loop no longer silently drops a param when coercion raises — it applies
  the declared `default_value` (or leaves it absent for the accessor to enforce required), never swallows. (3) **Typed
  accessor (P1 #6):** added **`IntentHandler.get_param(intent, name, default)`** — finds the donation `ParameterSpec`
  (`_find_param_spec`), coerces via the shared base, applies the declared `default_value`, and raises
  `ParameterExtractionError` on missing-required-no-default (fail-loud → QUAL-30 clarification). One handler-boundary
  read replacing ad-hoc `intent.entities.get(...)` with bespoke defaults. (4) **Latent correctness bug found + fixed on
  the headline exemplar:** "поставь таймер на 5 минут" was silently creating a **5-second** timer — the timer `unit`
  CHOICE had **English-only `choice_surfaces`** (no «минут»/«секунд»/«час»), so unit never extracted, and the handler
  **hardcoded `'seconds'`**, ignoring the donation's `default_value="minutes"`. Authored Russian unit surfaces +
  adopted `get_param` in the timer handler (donation default wins). Verified: "5 минут"→unit=minutes, "30 секунд"→
  seconds; **hardened TEST-0** to assert the response says "5 мин" (not "5 сек"). Suite 17/17.
  _Remaining QUAL-11: `_create_error_result` unification (P1-t) + QUAL-22 (Stage E); the per-handler `get_param`
  migration folds into QUAL-34 (same handlers/files — consume the declared param via the accessor)._
- **QUAL-11 [PEX] Stage C — unified the duplicate device path, added `_resolution_failed`, made parked patterns honest.**
  (1) **Duplicate device resolution removed:** `ContextAwareNLUProcessor._resolve_device_entities` (a hardcoded
  English-only keyword path that re-resolved devices with a different strategy and wrote `{e}_device_id`/`_device_type`/
  `available_devices` keys **no handler reads**) deleted — the asset-driven `ContextualEntityResolver.resolve_entities`
  is now the single device/location/temporal/quantity resolution path. (2) **`_resolution_failed` markers:**
  `_resolve_single_entity` now returns `(result, attempted_kind)`; an entity classified as device/location that fails to
  resolve gets `{name}_resolution_failed=True` so the QUAL-30 clarification boundary can tell "unresolvable reference"
  from "never a resolvable entity" (verified: device-ish `target` marked, plain `topic` not). (3) **Parked T2 patterns
  made honest:** `spacy_provider._validate_and_store_spacy_patterns` now documents that `advanced_patterns` is
  validated-but-never-applied (the live contract is T1; T2 = QUAL-35), ending the silent validate-then-discard footgun.
  Heuristic `_is_device/location_entity` dispatch stays (the `entity_type` swap is ARCH-6). Maintained suite green (17/17).
- **QUAL-11 [PEX] Stage B — de-fatalized the entity resolvers (P0 #4).** `DeviceEntityResolver._load_device_types`
  and `LocationEntityResolver._load_location_keywords` raised uncaught `RuntimeError` ("fatal configuration error")
  when the asset loader wasn't wired or localization data was missing/empty — and the resolver is built **asset-less**
  (injected later in `post_initialize_coordination`), so any device/location utterance before/without successful
  coordination **aborted the whole request**. The location path was worst: `_load_location_keywords` is called
  unconditionally at the top of `resolve()`. Both helpers now **degrade best-effort** — warn-once + return `{}` —
  so resolve() skips the asset-dependent inference (device type-inference / "here"-inference) but exact/fuzzy
  name matching still works and the request proceeds. Verified: both resolvers return `None` (not raise) with a
  null asset loader; maintained suite green (17/17). _(`_resolution_failed` markers + duplicate-path unify are
  Stage C.)_
- **QUAL-11 [PEX] Stage A — fixed the timer recognition gap (root cause) + the phantom cascade defaults.
  `test_set_timer_end_to_end` flips xfail→PASS.** Reconciled QUAL-11 against current code first (Invariant #8):
  every P0/P1 still live as written (nothing silently fixed by QUAL-23/27/29) → valid, proceed.
  - **Root cause of the recognition gap (verified empirically, not the review's "threshold too high" guess):**
    a **Cyrillic normalization asymmetry** in `hybrid_keyword_matcher._normalize_text`. It applied
    `NFKD` + combining-mark stripping, which folds precomposed Cyrillic **«й»→«и»** and **«ё»→«е»** (`таймер`→
    `таимер`). But regex patterns are built from the **raw** donation phrase (`таймер`, with «й») and matched
    against normalized text — so `\bпоставь таймер\b` could never match `поставь таимер на 5 минут`. This
    silently broke recognition for **every** Russian phrase containing й/ё (а huge class: таймер, какой, мой…).
    Fix: normalize with **`NFC` (compose), no combining-strip** — patterns and text are symmetric again; English
    unaffected. (The NFKD+strip only ever provided Latin accent-folding, irrelevant for a RU/EN assistant.)
  - **Phantom cascade defaults (P0 #1):** `provider_cascade_order` defaulted to
    `["keyword_matcher","spacy_rules_sm","spacy_semantic_md"]` — all three non-existent; the
    `"keyword_matcher"` always-on fallback was phantom too. Repointed both to the real entry-points
    (`hybrid_keyword_matcher`, `spacy_nlu`). QUAL-23 only *asserts* these at startup; it never fixed the default,
    so a config omitting the order recognized nothing.
  - **Result:** the timer flow now works end-to-end (recognition this stage + F&F from QUAL-28); the TEST-0
    `test_set_timer_end_to_end` xfail is removed and now a real green assertion. Maintained suite green
    (smoke + action-store + import-contracts: 17/17). **QUAL-11 remains open** — Stage A is the recognition/
    cascade slice; the shared-extraction-base + required-param contract, resolver de-fatalization, entity_type
    consumption, typed accessor, `_create_error_result` unification, and QUAL-22 are the remaining stages.

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
- **Audit (user) — "do handlers consume every declared param?" NO; filed QUAL-34.** Swept all 14 handlers (declared
  params from each `contract.json` vs whether the name is read in the handler `.py`). **19 of ~56 params across 11 of
  14 handlers are never read as `intent.entities[...]`** (7 CHOICE) — the QUAL-33 bug class is systemic. Two buckets:
  **A — genuinely dead** (feature not built; spot-confirmed `greetings.time_of_day`, `text_enhancement.improvement_
  type`, `system_service.metric_type`; `datetime` reads zero entities so all of its are dead) → wire-or-remove per the
  QUAL-33 precedent. **B — bypassed** (handler re-parses `intent.raw_text` instead of the NLU entity; spot-confirmed
  `voice_synthesis.voice` → `voice_name`) → folds into **QUAL-11** (typed accessor; QUAL-25 P1-r/P1-s). Recorded the
  full table in `docs/review/declared_param_audit.md`; filed **QUAL-34** `[release]` for the per-param triage. _Did not
  auto-fix — disposition is per-param (build vs stop-declaring), user's call._
- **QUAL-33 (system half) — wired `system.info_type`; canonical set reduced to `[system, performance]`. QUAL-33 DONE.**
  `_handle_info_request` now branches on `info_type` (was ignored). Per user, the canonical set was **reduced to
  `[system, performance]`** — `configuration` and `logs` REMOVED from the donation contract entirely ("no handlers, no
  donations"): there's no in-memory log buffer and the full system config isn't reachable from the handler, and the
  honest fix for "declares an option it can't serve" is to **not declare it**. `performance` renders real metrics —
  `get_metrics_collector().get_performance_summary()` (total_actions/success_rate/avg_duration) + uptime — via a new
  bilingual `performance` template (`system_handler/{en,ru}.yaml`); `system` (default) keeps the existing info template.
  Authored bilingual `choice_surfaces` for `info_type` (en: system/performance + synonyms like perf/metrics/stats; ru:
  система/производительность/нагрузка/…). Verified: template placeholders render (no KeyError); surfaces resolve
  ("производительность"→performance, "о системе"→system); donations schema-valid; smoke + store + contracts green.
  **QUAL-33 complete** (both halves). ru surfaces are a proposal pending native-speaker review.
- **QUAL-33 (datetime half) — wired `datetime.format`; the handler now honours its declared CHOICE param.**
  All three datetime handlers (`current_time`/`current_date`/`current_datetime`) read `intent.entities["format"]`
  (canonical, normalised by the NLU) and branch: time → 12hour (`12:40 AM`) / 24hour (`00:40`) / verbose (the natural
  template, default); date → short (locale numeric) / iso (`2026-06-03`) / full=verbose (template, default); datetime →
  iso (ISO-8601) / unix (epoch) / readable (compact) / verbose (default). Non-verbose paths return before the locale
  template (no asset-loader dependency). **Authored bilingual `choice_surfaces`** for all format params in `datetime_
  handler/{en,ru}.json` (e.g. `24hour` ← "24 hour"/"24-hour"/"military" · "24 часа"/"24-часовой"; `verbose` ←
  "in words" · "словами"/"прописью") — this is what makes the format reachable (QUAL-29's matcher extracts CHOICE via
  surfaces, not the placeholder `.*` patterns). Verified: "24 часа"→24hour, "словами"→verbose; handler renders each
  format. Lang files still schema-valid; smoke + store + contracts green. _Russian surfaces are my proposal — flag for
  review._ Remaining: the system.info_type **full feature** (real per-category content — user-approved scope).
- **QUAL-29 Stage G (backend) — REST API + loader fully retire the v1.0 per-language-with-params concept. QUAL-29
  backend DONE; config-ui editor rebuild carved to UI-5 (user-approved Invariant #4 deferral).** User chose to retire
  the old concept properly rather than ship a compatibility shim, accepting the config-ui donations-editing page breaks
  at runtime now (it still BUILDS — the frontend compiles against its own `api.ts`). **Loader:** added the v1.1 editing
  API — `get/save_contract` (neutral core) + `get/save_language_phrasing` + `validate_contract_data`/
  `validate_phrasing_data` (against the v1.1 schemas); **retired** `get/save_donation_for_language` (which did
  `HandlerDonation(**lang_file)` → crashed under v1.1); fixed `get_available_languages_for_handler` +
  `get_all_handlers_with_languages` to exclude `contract.json` (was surfacing "contract" as a language);
  `validate_cross_language_consistency` reworked to method-phrasing completeness (parameter parity is structural now).
  **REST (`intent_component.py`):** added `GET/PUT /donations/{handler}/contract`; the per-`{language}` GET/PUT/validate/
  create endpoints now serve/accept **phrasing-only**; `GET /donations/schema` returns **both** v1.1 schemas
  (`{contract, language}`); **removed** the dead `POST /donations/{handler}/sync-parameters`. Verified: editing
  round-trip works (contract 7 methods, ru phrasing has no params-with-type, both validate clean); smoke + store +
  contracts green. **Remaining Invariant #4 obligation = UI-5** (rebuild the config-ui donations editor on the v1.1
  split: contract editor + phrasing editor + choice_surfaces/entity_type/room_context editors; coordinate with
  UI-1/2/3 — one redesign, not two). QUAL-33 (datetime/system handler-wiring) still pending.
- **QUAL-29 scope clarification (user) — REST API = unfinished Stage G; datetime gap filed as QUAL-33.** User flagged
  that the donation **REST API still serves v1.0 concepts** and the datetime gap is unclosed. Grounded both: the REST
  surface (`get_donation_schema` → `assets/v1.0.json`; the per-`{language}` GET/PUT/validate/create/delete treating a
  lang file as a full donation-with-params; the dead `sync-parameters`; loader `get/save_donation_for_language`) is the
  **config-ui/Invariant #4 obligation = QUAL-29 Stage G** — QUAL-29 stays `[~]` until it lands (documented explicitly in
  `qual29_choices_decisions.md` Stage G). The **datetime gap is a distinct handler bug** (datetime.py reads no entities,
  so its declared `format` is dead) — filed as **QUAL-33** (with system.info_type, same class: handlers ignoring declared
  CHOICE params + authoring the deferred ru surfaces the validator already flags). Not part of the format split; doable
  standalone.
- **QUAL-29 Stages E + F — validator shrink + v1.1 JSON schemas. Smoke green.** (E) Rewrote
  `cross_language_validator` for v1.1: parameter parity is now structural (single-source contract) so
  `validate_parameter_consistency` was repurposed to **CHOICE surface completeness** (flags canonical tokens lacking
  per-language surfaces — correctly surfaces the deferred datetime.format/system.info_type gaps); `sync_parameters_
  across_languages` is now a **no-op** (nothing to sync); `validate_method_completeness` + `suggest_translations`
  reworked to read the v1.1 raw structure (contract method list + per-language phrases). Report dataclass shapes kept
  so the 3 config-ui REST endpoints stay stable (Invariant #4). (F) Wrote `assets/donation_contract_v1.1.json` +
  `assets/donation_language_v1.1.json` (the schemas the migrated `$schema` keys reference) and wired
  `_validate_donation_schema` into the loader (guarded by `validate_json_schema`, graceful if jsonschema absent).
  Verified all **14 contracts + 28 language files validate** against the schemas, and they're now enforced at load.
  Remaining (QUAL-29): config-ui (Stage G, Invariant #4) + dead-param handler-wiring follow-ups (Stage H).
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
