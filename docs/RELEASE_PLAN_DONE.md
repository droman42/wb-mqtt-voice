# Irene — Completed Release Tasks (frozen archive)

Frozen, append-only record of **completed** (`[x]`) release tasks, split out of
[`RELEASE_PLAN.md`](./RELEASE_PLAN.md) to keep the active ledger readable (Invariant #6 still
owns scope+status; this is its done-history). Organized by workstream, IDs preserved so open
tasks and the journal resolve their references here. **Do not re-edit** — closed work only;
rationale/chronology lives in [`RELEASE_JOURNAL.md`](./RELEASE_JOURNAL.md).

---

### Architecture & Refactor (ARCH)
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
      **★ ARCH-22 (2026-06-14):** the WS transport is consolidated into **`docs/design/esp32_satellite.md`** (which supersedes
      `ws_esp32_transport.md`). The intertwined "return channel" (WS audio response to the device) landed as the ARCH-22
      reply channel `/ws/audio/reply` (esp32_satellite.md §4.2), and the `register` handshake was extended on
      `ClientRegistration` with `audio_out`/`name`/`primary_room`/`covered_rooms`/`firmware_version`/`model_version` (D-14).
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
- [x] **ARCH-9** [INFER] — **✓ DONE 2026-06-04.** **★ ARCH-22 (2026-06-14):** the §10/§11 WB7-satellite-vs-standalone
      VAD+wake split is folded into **`docs/design/esp32_satellite.md`** (D-11 inference split; D-9/D-10 micro stack). _Orig:_
      (design deliverable `docs/design/onnx_inference_layer.md` complete; all
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
- [x] **ARCH-10** [INFER] — **DONE (implementation) 2026-06-16.** All PR slices + the ESP32 streaming-endpoint are
      code-complete; the WB7/WB8 **on-device re-validation** this task used to carry is now its own item, **ARCH-25**
      (satellite hardware bring-up). Implement per ARCH-9, sliced PR-1..5 (design §12). **PR-1/2/3/4 DONE 2026-06-04**
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
      → **ARCH-25** (satellite hardware bring-up; user/hardware-gated).
      Build/Docker corrections = BUILD-5/3.
      **★ OWNS the ESP32 streaming-endpoint (ARCH-22 #3 / D-6, deferred here 2026-06-14) — BUILT + seam-tested 2026-06-16,
      device-validation hardware-gated:** a **new no-VAD streaming path** for `/ws/audio` that feeds the configured ASR's
      streaming segmenter + finalizes on the model endpoint (sherpa-onnx `OnlineRecognizer`), opportunistic —
      server-authoritative end-of-utterance for the background-noise/TV case. NOT `process_audio_stream` (that's the
      VAD-segmented mic path). **Implementation:** the ASR port grew a typed `transcribe_stream_segments` →
      `(text, is_final)` (concrete buffer-once default in `asr/base.py`; sherpa override does real `OnlineRecognizer`
      endpointing yielding partials + endpoint-/EOF-finalized segments) + a `supports_streaming` capability flag; the ASR
      **component** exposes a pass-through (provider stays behind the port); `/ws/audio` gains a branch selected by the
      device's `mode:"streaming"` register field AND `supports_streaming()` — partials go back as `{"type":"partial"}`,
      each finalized segment is injected via `workflow_manager.process_text_input` (enters at **Text Processing** → NLU →
      Intent → Response, same tail as the batch path; ASR just runs at the edge instead of inside the workflow). No
      wire-contract break — `{"type":"end"}` still honored as a hard finalize; non-streaming ASR falls through to the batch
      floor. 4 seam tests (fake streaming ASR) green; suite 1007, pyright 0, 9/9 contracts. **Remaining:** real endpoint
      RTF/latency validation on the WB7 → **ARCH-25**. _Note:_ in streaming mode ASR runs at the adapter,
      so the request traces as a **text** input — no per-provider ASR-stage trace for these utterances (matters to QUAL-53).
      The accumulate-until-`end` + batch-ASR path in `/ws/audio` stays the permanent floor. See `esp32_satellite.md`
      §4.4/§12.
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
- [x] **ARCH-18** [AUDIO] (P-TBD) — **Implement ARCH-17, sliced PR-1..6 (`audio_pipeline.md` §13). DONE 2026-06-10.** **PR-1 DONE
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
      contracts, suite 81=81 (+~26 tests). **PR-4a+4b DONE 2026-06-10**: 4a collapsed the 3 TTS resample dups into one
      `_conform_output_audio`; 4b made `asr.process_audio` + `voice_trigger.detect` **trust canonical** (conform once at
      each entry boundary — mic via `to_canonical`, `/asr/transcribe` via `_conform_to_rate`, `/stream`=canonical-wire;
      the per-consumer resampling was untested zero-value code, rewritten clean test-first) + §7 startup summary logs
      every party's contract. pyright 0, 9/9, suite 81=81 (+~31 tests). _(Input-path **endpoint unification** landed
      2026-06-10 as a 4b follow-up: hoisted `AudioNegotiator`→`core` as a SHARED service, `/asr/transcribe`→`to_canonical`,
      deleted `/asr/stream`+`/asr/binary`, confirmed `/ws/audio` already VAD-free; QUAL-45 filed for the ESP32 firmware
      end-of-utterance contract.)_ **PR-4c DONE 2026-06-10 (§8, D-8..D-13)** = symmetric
      **output**: sink-driven contract (audio provider `audio_contract()` + `[audio]` `output_rate`/`output_channels`
      override, **CD default**), `AudioNegotiator.to_sink` conform-**down-only** (traced), TTS retired
      `_conform_output_audio`→`_conform_to_sink` at all 3 streaming sites (caller = sink, CD default; response carries
      the actual conform-down rate). PCM-only; local file playback untouched (intentionally file-based). 5 tests,
      pyright 0/9-9/config-ui green/suite 81=81. _(The streaming caller IS the sink for now; a generic remote/streaming
      AudioSink stays future-addable.)_ **PR-5 DONE 2026-06-10**: pre-roll sized lazily from the active VAD provider's
      `detection_latency_ms(frame_ms)` at the REAL canonical frame duration — kills the magic `4` AND the 23/25 ms/frame
      constants. Latency declaration harmonized (energy frame-count→`frames+2`; silero `voice_duration_ms`; microvad new
      `detection_latency_ms` TOML field+schema, config-ui green); also fixes energy undersized for big chunks. Suite 81=81. **Order: PR-5 → PR-4c (symmetric output, design-first) → PR-6.** **PR-6 DONE 2026-06-10
      (FINAL) — user-facing docs + diagrams:** rewrote `vad.md` (provider family + `[vad.providers.*]` nesting),
      updated `audio.md` (canonical input + output sink/CD-default/conform-down), `voice-trigger.md` +
      `howto-new-model.md`; added a "The audio front-end" section to `architecture/dataflow.md` + a new Graphviz
      diagram `docs/images/audio-pipeline.dot/.png` (mic/satellite/file → AudioNegotiator → VAD → wake → ASR, + TTS →
      sink). Stale-term sweep across guides/architecture clean. Invariant #4:
      the `[vad.providers.*]` schema change updates config-ui in the same PR (PR-2). VAD providers wrap the existing
      energy/silero/microvad engines (no new ML). **ARCH-18 COMPLETE — all of PR-1..6 + the input-path unification done.**
- [x] **ARCH-19** [TRACE] (P-TBD) `[deferred]` — **DONE 2026-06-14 (slices 1–6).** Trace persistence + playback
      (`docs/design/trace_persistence.md`, design COMPLETE D-1..D-18). Persist an utterance-execution trace to a
      **self-contained JSON** (audio **base64 inline, no WAV**) so it can be **listened to** AND **replayed** through the
      pipeline (regression + VAD tuning). Adds an opt-in save+replay layer over today's ephemeral `TraceContext` (normal
      traffic unchanged). LOCKED decisions D-1..D-10: 3 configurable **capture levels** (utterance / segmenter+`vad_frames`
      / raw; live-mic raw behind `--trace-raw-mic`); a **`current_trace` contextvar in `core`** (hexagon-clean — domain
      already imports core) as the spine for a **`TraceLogger`** (configurable threshold + exception traces) and handler
      **`trace_event()`**; replay's audio source = a lightweight **`TraceInput`** (`InputPort`) for the stream levels
      (utterance reuses `process_audio_input`), **seeds a fresh context from `seed_context`** + **diffs** vs
      `recorded_output` (not bit-exact — LLM non-determinism); **two replay modes** `--local` (default; run through the
      replayer's pipeline + mismatch report — the VAD-tuning case) / `--reproduce` (apply the trace's captured
      **config subset**); models out of scope for now (dev system is a superset of testers'). Trigger = runner `--trace`
      now → `[trace]` TOML (config-ui) later, **save every request**. CLI playback (D-11..14): **listen** via the audio
      component (OS output), **`--step`** (pause per stage), **`--record-out`** a second trace (tester's + local replay
      for comparison); `vad_recording_test` **deleted** once its harness is ported (base64 not WAV, fix `to_canonical`).
      **Design COMPLETE 2026-06-14 — D-1..D-18 locked, §13 open questions all resolved:** D-15 replay = CLI-only v1
      (endpoint deferred); D-16 `--reproduce` fails clearly on a missing model (no degrade — that's `--local`); D-17
      save-all gated solely on the startup `--trace` flag (no ring/on-error, manual retention); D-18 trace stays
      file-only, lightweight `trace_saved` pointer-event once ARCH-15's bus exists. Slices §12 — **ready for
      implementation.** **Slice 1 (spine) DONE 2026-06-14:** `current_trace` contextvar + `trace_scope` + no-op-safe
      `trace_event()` + the faithful `replay` envelope on `TraceContext` (`record_input`/`record_request`/
      `record_canonical`/`record_seed_context`/`record_config`→digest/`record_output` + `handler_events`/`logs`/
      `vad_frames` holders) + `build_envelope`/`to_file` (§2 JSON); contextvar + input/request/output capture wired
      at the two `WorkflowManager` request boundaries; 15 new tests; 9/9 import contracts kept. **Slice 2
      (TraceLogger + `[trace]` config + `--trace`) DONE 2026-06-14:** global `TraceLogger` handler (inert unless a
      trace is active; captures records ≥ `log_threshold` + exception tracebacks, bounded by `max_log_records`)
      installed once at runner startup; new `[trace]` `CoreConfig` section (`TraceConfig`: enabled/capture_level/
      capture_raw_mic/log_threshold/traces_dir/caps) + `AssetConfig.traces_root` default + auto-registry section
      order/title; `--trace`/`--trace-raw-mic` runner flags flip it; **save-every-request** wired into both
      `WorkflowManager` batch boundaries (`_maybe_create_trace`→`to_file(<traces_dir>/<request_id>.json)`), gated
      solely on the startup flag (D-17). `config-master.toml` gains `[trace]`; config-ui builds clean with **zero
      changes** (schema-driven sections — Invariant #4 ✓). 16 new tests; 9/9 contracts kept. **Slice 3 (capture
      levels + streaming path) DONE 2026-06-14 (user-approved scope: one-trace-per-utterance + all 3 levels incl.
      raw live-mic):** `VoiceSegment.vad_frames` + `VoiceSegmenter` per-frame verdict collection (gated by a startup
      `collect_vad_frames` flag), sliced to each segment's window on completion; the streaming path now mints **one
      trace per VoiceSegment** — `_capture_segment_input` records the assembled canonical segment (utterance/segmenter)
      or the pre-canonical audio reconstructed from a bounded **raw rolling buffer** in `_canonical_stream` (raw level,
      via `--trace-raw-mic` → `capture_level=raw`), attaches `vad_frames`, binds the contextvar around `_process_pipeline`,
      records the oracle + saves. The legacy `vad_recording_test` 44.1 kHz-VAD bug is inherently fixed (capture runs
      in the real canonical pipeline — VAD sees 16 kHz). Shared create/save helpers (`make_trace`/`save_trace`/
      `resolve_traces_dir`/`replay_request`) lifted into `core.trace_context` and reused by `WorkflowManager` + the
      workflow. 12 new tests; 9/9 contracts kept; VAD/audio suites net-zero (15 pre-existing TEST-2 failures). **Slice 4
      (handler `trace_event` call-sites, D-5) DONE 2026-06-14:** opt-in `trace_event()` (the slice-1 contextvar helper,
      bound during handler execution in both paths) wired by rule — **every fire-and-forget launch traced once
      generically (`action_launched {domain,action}`) at the base choke point `execute_fire_and_forget_with_context`**
      (covers timer, voice_synthesis, audio_playback + any future F&F handler without per-site edits), **plus explicit
      events for synchronous side-effects:** timer set/cancel/stop, the **7 LLM call-sites** (`conversation` ×2,
      `text_enhancement` ×3, `translation` ×2), and provider/ASR/language switches (`provider_control`,
      `speech_recognition`, `system.language_switch`). Pure-compute handlers (datetime/greetings/random, read-only
      system_service) deliberately NOT instrumented — no key step beyond the response text already in `recorded_output`.
      F&F actions run in detached tasks (stale contextvar snapshot) → launch events live in the synchronous request
      path. Purely additive; domain→core edge pre-existed (`base.py`), 9/9 contracts kept. **Device-command MQTT events
      deferred (Invariant #8): no real send/publish call-site exists yet** — device handlers are stubs/ports pending the
      bridge layer (ARCH-7/8). 6 new tests; handler suites net-zero (21 pre-existing TEST-2 failures). **Slice 5
      (replay tool) DONE 2026-06-14 (user-approved: full scope incl. `--step`):** wired the deferred **`seed_context`
      capture** at the single spine (`_process_pipeline`, covers batch + per-utterance streaming); new
      **`TraceInput`** (`InputPort`, D-9 — chunks the trace's audio into frames for streaming re-entry); new
      **`irene/tools/replay_trace.py`** (`irene-replay-trace`): load → `build_core` → seed fresh context → re-inject
      (utterance via `process_audio_input`, segmenter/raw via `TraceInput`→`process_audio_stream`, text via
      `process_text_input`) → **diff vs `recorded_output`**; **`--local`/`--reproduce`** (D-10; `--reproduce` overlays
      the captured `config_subset` and **fails clearly on a model the replayer lacks**, D-16); **`--listen`** (D-11,
      audio component, best-effort), **`--step`** (D-12 — a `trace_step()` async pause seam at the pipeline stage
      boundaries, hook reached via the contextvar / global for streaming-minted traces, no-op otherwise),
      **`--record-out`** (D-13 — reuses the save-every-request machinery into a chosen dir). 15 new unit tests (pure
      diff/subset/model-mismatch/seed + `TraceInput` chunker + `--step` seam + load round-trip); the full e2e run needs
      real models (`build_core`) so it's manual/integration. 9/9 contracts kept; pipeline suites net-zero (24
      pre-existing TEST-2 failures). Invariant #4 N/A. **Slice 6 (retire `vad_recording_test` + docs) DONE
      2026-06-14 — ARCH-19 COMPLETE:** deleted `irene/tools/vad_recording_test.py` + its `irene-vad-recording-test`
      entry point (its purpose was already ported in slices 2/3 — `capture_level=segmenter` on a mic session
      captures `vad_frames` + base64 audio with VAD at canonical 16 kHz, and replay tunes from it, D-8/D-14; no code
      or config still referenced it). New user guide `docs/guides/tracing.md` (runner `--trace`/`--trace-raw-mic`,
      the three capture levels, the `[trace]` config, and the `irene-replay-trace` tool incl. `--local`/`--reproduce`/
      `--listen`/`--step`/`--record-out`); `vad.md` Tuning now points to the trace-based workflow; README guides
      index updated. All six slices shipped; 9/9 contracts; trace suite net-zero.
- [x] **ARCH-20** [AUDIO] (P-TBD) `[deferred]` — **DONE 2026-06-14 (PR-1..4).** Streamable audio output: real
      `play_stream`, new self-contained `miniaudio` provider, unstreamable providers dropped, TTS local playback
      wired through the streaming path. **PR-1** dropped `audioplayer` (file-only) + `simpleaudio` (archived,
      WAV-buffer-only) end-to-end + bumped `sounddevice→0.5.x`/`soundfile→0.13`. **PR-2** replaced the file-only
      stubs with a **raw-PCM `play_stream` contract** (`utils/audio_stream.py`: `collect_pcm`/`parse_wav`): real
      `sounddevice` `RawOutputStream` (thread-blocking write) + `aplay` raw stdin (true incremental); REST
      `/audio/stream` parses WAV→PCM, external contract unchanged. **PR-3** added the `miniaudio` provider
      (`PlaybackDevice` + pull generator; `get_platform_dependencies()=={}` on every OS). **PR-4** added the
      `[audio] playback_mode = "file" | "stream"` flag (default `file`); `stream` does synth→`parse_wav`→
      `to_sink` (§8 conform-down)→`play_stream`, degrading to `play_file` for text-only providers / no negotiator.
      **Reconciliation (Invariant #8):** all TTS providers are file-only at the provider level, so "stream mode"
      reads back the synthesis WAV rather than a file-free synth path (a future per-provider enhancement); the
      ledger's "wire **playback** through play_stream" is fully met. **`console` KEPT** (user 2026-06-14) as the
      safe headless default + fallback; the original "retire console" step is dropped. Invariant #4 green
      (config-ui check+build each PR); pyright 0 on all touched files; net-0 regression across PR-1..4 (81 =
      baseline). Docs: `docs/guides/audio.md` rewritten (4-provider table, streaming, `playback_mode`). _Original
      scope below._ Closes the file-only-output limitation ARCH-18/PR-4c deferred
      (intentionally, never task-tracked): research (2026-06-13) found **all five providers' `play_stream` are stubs**
      (buffer → temp WAV → `play_file`) — file-only is unimplemented code, not a library wall. Decision: **keep only
      streamable backends.** Scope — **(1)** implement **real** `play_stream`: **sounddevice** via `RawOutputStream`
      (plain PCM buffers, cross-OS), **aplay** via stdin pipe (Linux); **(2)** add a new **`miniaudio`** provider
      ([pyminiaudio], self-contained — **no system lib**, bundled WASAPI/CoreAudio/ALSA backends, cross-OS incl. RPi,
      MIT, maintained) via `PlaybackDevice` + generator → gives **≥2 streamable backends on every OS** (sounddevice +
      miniaudio, different stacks; +aplay on Linux); **(3)** **drop `audioplayer`** (file-only) **+ `simpleaudio`**
      (archived/unmaintained, buffer-only) — remove providers, entry-points, deps, `system_dependencies`/dependency
      catalog refs; **(4)** bump **sounddevice→0.5.x, soundfile→0.13/0.14**; **(5)** wire **TTS local playback through
      `play_stream`** (the actual "make output streamable" — completes `audio_pipeline.md` §8); **(6)** the
      async→sync **generator bridge** (`play_stream` is async, sounddevice-callback/miniaudio-generator are pull-sync).
      Gates: Invariant #4 (audio provider list → config-ui), `dependency_validator`/`build_analyzer` (extra changes),
      update `docs/guides/audio.md` provider table. _(Research findings in the 2026-06-13 journal; `console` stub
      kept/retired per taste — not an audio output.)_
- [x] **ARCH-21** [AUDIO][TTS] (P-TBD) `[deferred]` — **DONE 2026-06-14 (PR-1..5).** **★ ARCH-22:** the deferred
      reply-channel **device-half** handoff landed in ARCH-22 — `/ws/audio/reply` + `CallbackReplyChannel` pair the PR-5
      `RemoteAudioOutput` to the device (esp32_satellite.md §4.2; `d8b1c70`). _Orig:_ Streaming TTS +
      output-seam delivery unification. **PR-5 server seam** (`outputs/remote_audio.py`: `RemoteAudioOutput`
      `OutputPort` + `ReplyChannel` Protocol) lands the reply-to-device (D-4) delivery — `origin_key==physical_id`
      routes via the existing `OutputManager` origin-pairing, `synthesize_to_stream`→conform to the **device's**
      `AudioContract`→push over the channel; built protocol-agnostic + fake-client/real-OutputManager tested. **★
      Handoff:** the device-facing reply-channel WS endpoint + connect/disconnect registration + wire frame
      protocol + F&F-offline policy are owned by the **ESP32 design session** (`ws_esp32_transport.md` / QUAL-45) —
      ARCH-21 ships the server abstraction it plugs into. pyright 0, config-ui green, net-0 regression across all
      5 PRs (81 = baseline). _Design + reframe below._
      **Streaming TTS + output-seam delivery unification**
      (design 2026-06-14, `docs/design/streaming_tts.md`). The **producer twin** of ARCH-20: that task made
      *playback* stream raw PCM, but the **TTS producer is file-only at the contract level** (only
      `TTSProvider.synthesize_to_file`), so ARCH-20 PR-4's `stream` mode is an **interim bridge**
      (`synthesize_to_file → parse_wav → to_sink → play_stream` — real conform + streaming backend, but **no
      latency win**, and `parse_wav` exists only because the port can't hand back PCM). Subsumes the smaller "true
      streaming TTS synthesis" framing. **Reconciliation finding:** delivery is fragmented across **three** surfaces
      doing the same synth+emit — `_handle_tts_output` (sync reply; PR-4 updated), `AudioSpeechOutput.deliver`
      (`outputs/audio.py`, ARCH-15 `OutputPort`, deferred F&F — **PR-4 did NOT touch it, still `play_file`**), and
      the WS `/tts/stream`+`/tts/binary` endpoints in the TTS component (chunk a *finished* buffer). **Locked
      decisions (D-1..D-3):** **D-1** delivery belongs at the **output seam** (ARCH-15 `OutputPort`/`OutputManager`),
      NOT in the TTS component and NOT as an audio provider (providers are config-selected local-device singletons;
      a WS client is dynamic/per-connection → a remote `AudioSink`/`OutputPort` sibling to `AudioSpeechOutput`,
      consuming the producer's PCM stream via the `play_stream`/`AudioSink` contract + `to_sink`; §8 D-13). **D-2**
      KEEP every provider — "streaming" is a delivery-layer chunking concern decoupled from the engine; **base-class
      simulation** (synth→read→yield) covers all, with **native overrides** where the engine supports it (elevenlabs
      true-stream + MP3→PCM decode; silero v3/v4 via `apply_tts` samples; sherpa-onnx TTS per-chunk callback when
      ARCH-9/10 lands). Dropping non-streaming engines would leave only cloud elevenlabs and gut offline-first RU
      TTS — rejected. **D-3** `synthesize_to_file` STAYS (file deliverable + `playback_mode="file"`); the port grows
      an additive `synthesize_to_stream`. **Slices §5:** PR-1 port + base simulation ✓ · PR-2 local playout (incl.
      `AudioSpeechOutput`, fixing the ARCH-20-PR-4 file-only inconsistency) consumes the producer + retire the
      `parse_wav` bridge ✓ · PR-3 native overrides (silero v3/v4, elevenlabs PCM) + capabilities matrix ✓ · PR-4
      **delete** the vestigial WS synthesis endpoints ✓ · PR-5 origin-addressed reply-to-device (server seam).
      **★ D-4 reply-to-device (user 2026-06-14):** output is **origin-addressed** — input from a WS device → reply
      back to that **device** (NOT the same connection: a **separate reply-channel WS** the device listens on),
      the device's `AudioContract` drives the conform; local input → local output; clean per-deployment config
      (WS-satellite = no `[audio]`/mic). **Invariant #8 scope change (user-approved 2026-06-14):** PR-4 was "move WS
      delivery into a remote-sink OutputPort" but that needs live-connection push infra that doesn't exist
      (`ClientRegistry` holds metadata only; `/ws/audio` replies text-only) = ESP32-transport scope. **Redefined:**
      PR-4 = delete `/tts/stream`+`/tts/binary` (untested twins of the deleted ASR endpoints; contradict
      reply-to-device); PR-5 = the reply-to-device **server seam** (reply-channel WS + live-connection registry by
      physical id + remote `AudioSink` `OutputPort` + `OutputManager` origin routing), built protocol-agnostic +
      fake-client-tested, with the device protocol + F&F-offline policy finalized in the ESP32 design session
      (`ws_esp32_transport.md`/QUAL-45). Open questions §6.
- [x] **ARCH-22** [ESP32][WS] (P-TBD) `[deferred]` — **DONE 2026-06-14 — full ESP32 review + consolidated design session**
      (started 2026-06-14; deliverable `docs/design/esp32_satellite.md` — being written interactively). **Container/umbrella**
      that (a) reviews the current implementation (firmware draft **+** backend contract), (b) consolidates the ESP32 design
      topics scattered across the ledger, and (c) folds in the user's not-in-ledger inputs — producing **ONE** consolidated
      ESP32 design doc, implementing the missing **backend** pieces, and closing the ESP32 design tasks (or the ESP32 pieces
      of bigger tasks). **Phase 1 (implementation review) DONE:** the quarantined `ESP32/firmware/` draft (rev 2, Jul 2025,
      ~5.2k LoC) is a real on-device audio-acquisition + microWakeWord(INT8 TFLite-Micro) + microVAD + mTLS-WS pipeline, but
      its wire protocol **predates every backend decision** (sends `/stt` + `{"config":…}` + `{"eof":1}`, ignores replies, no
      audio-out path) and its UI/output/codec halves are stubs. **Locked decisions:** **D-1** backend authoritative, firmware
      draft = inspiration only; **D-2** headless voice satellite (board + mic + speaker, 3D-printed case; no display/touch/RTC/
      UI; memory bump-able); **D-3** ESP-IDF + PlatformIO (not Arduino); **D-4** device is a pure MQTT-unaware voice terminal
      (audio in / audio out only; all smart-home/MQTT/actuation stays backend per ARCH-7/8). **Topics T1–T7** (each maps to
      ledger items): T1 WS transport+wire protocol (ARCH-6 input ✓ + QUAL-45 end-of-utterance + ARCH-21 reply-to-device
      device-half + capability declaration); T2 on-device audio I/O + **hardware selection** (mic, speaker+amp) + the absent
      playback path; T3 microWakeWord+microVAD "micro" stack (QUAL-19/20 — same `.tflite` artifact device+server); T4
      inference + models (ARCH-9/10 WB7-satellite-vs-standalone split, model storage/format/**push**; ARCH-10 ESP32
      streaming piece done, WB7 re-validation → ARCH-25); T5 identity + multi-room (ARCH-6/QUAL-28); T6 provisioning + lifecycle [**T-A**: WiFi, certs/
      mTLS, OTA config-preserving, model push]; T7 backend cross-cutting [**T-B** voice-confirmation of actuation, depends
      ARCH-8; + device-half resolver ownership note → ARCH-7/QUAL-35, not re-opened here]. **Closes/absorbs on completion:**
      QUAL-45 (input+output protocol), ARCH-21 reply-channel device-half handoff, the ESP32 pieces of ARCH-6/ARCH-9/ARCH-10.
      The **firmware rewrite itself** (the C++ effort) is tracked as a separate deferred item (quarantine → fresh build per
      `esp32_wakeword_review.md`); this session implements **backend only**. **Phase 2 (design) DONE — D-1..D-18 locked;
      Phase 3 DONE — consolidated `docs/design/esp32_satellite.md` (backend plan §12).** **Phase 4 (backend) IN PROGRESS:**
      #1 reply channel `/ws/audio/reply` ✓ (`d8b1c70`); #2 `register` extension (D-14 identity/multi-room/audio_out) ✓
      (`fa56978`); **#3 streaming-endpointing (D-6) DEFERRED → ARCH-10** (Invariant #8: it's a new no-VAD streaming path,
      deployment-gated on a streaming ASR + WB7, testable only there; the accumulate-until-`end` + batch-ASR **fallback is
      the permanent floor and active** — `/ws/audio` correctly implements the wire contract; the wire/firmware design is
      unchanged by the deferral). **#4 asset serving + #5 CSR/CA + #6 ops RECLASSIFIED →
      Plane B (NOT Irene), 2026-06-14 (WB7 SSH recon):** they're a **fleet-provisioning plane** that runs as nginx +
      openssl + scripts **directly on the WB7** (tiny armv7 box, ~1 GB RAM; Irene isn't even deployed there) —
      implemented in the repo at **`nginx/`** (Ansible playbook + EC home-CA + two-zone nginx [:80 bootstrap / :443
      mTLS] + `esp32-provision` approval CLI; CSR-approval flow proven end-to-end with openssl). **Plane A (Irene
      voice pipeline) is COMPLETE for ESP32** (#1 reply channel, #2 register; #3 → ARCH-10). Amends D-13 (models =
      Plane-B nginx static, not Irene AssetManager) + D-17 (approval = WB7 CLI, not config-ui). **Phase 5 (closure) DONE
      2026-06-14:** closed QUAL-45 (subsumed); amended ARCH-6/7-via-ARCH-8/ARCH-9/ARCH-10/ARCH-21/QUAL-19/QUAL-20/QUAL-35
      with `esp32_satellite.md` pointers; filed ARCH-23 (firmware rewrite). **ARCH-22 deliverables complete** (review +
      consolidated design doc + Plane-A backend + Plane-B `nginx/` + closure); the firmware rewrite is ARCH-23, #3 is ARCH-10.
- [x] **ARCH-24** [ASR][TTS][IO] — **DONE 2026-06-16.** All five tranches code-complete: **T1** (Whisper→sherpa via the
      `model_type` discriminator + whisper-small pack), **T2** (`piper` + `piper_ruaccent` TTS providers), **T3** (armv7
      torch-ban CI gate, `backend-health.yml`; provider platform taxonomy + `dependency_validator --platforms`), **T4**
      (the three baked target configs — `embedded-armv7` / `embedded-aarch64` / `standalone-x86_64`), **T5** (the shared
      `inference_policy` / `torch_model_cache` sherpa helpers, with tests). The three images build green on GHCR
      (packaging = **BUILD-3**). **Sole remainder = on-device verification (RU parity + A53/A7 RTF + boot), hardware-gated
      — owned by ARCH-25's WB7/WB8 hardware re-validation and the Definition-of-release gate, NOT open engineering scope.**
      _Original analysis below._ **Torch-free inference & the armv7 voice stack.** Research/analysis
      session **DONE 2026-06-15** (no code); deliverable **`docs/design/torch_free_armv7_voice.md`** + the real WB7 ground
      truth (SSH'd 192.168.110.250: Cortex-A7 quad armv7l, 1 GB RAM — **~712 MB available after SprutHub was stopped+disabled
      2026-06-15** (was ~367 MB; SprutHub's JVM held ~352 MB) + 256 MB swap; disk on **`/mnt/data` 2.3 GB free** (not the
      cramped rootfs), glibc 2.31, py3.9, dockerized deploy). **Topology corrected:** ESP32 satellites own VAD + voice-trigger
      + mic/playback; WB7 Irene = **ASR/NLU/intent/TTS only** (no server VAD, no local audio, no `config-ui`), running as a
      container beside `wb-mqtt-bridge` + `wb-mqtt-ui` — three-container budget ≈ 410–570 MB of 712. **Thesis (revises ARCH-9
      for armv7 only — torch stays on 64-bit):**
      drop torch from the default/armv7 build by (T1) **Whisper → sherpa-onnx — ALREADY IMPLEMENTED** (the `sherpa_onnx`
      provider branches on `model_type`: `whisper`→`from_whisper`, `sherpa_onnx.py:128-143`; tiny/base packs declared). One
      provider + `model_type` discriminator — NOT a separate provider, NOT a base/derived split. **`whisper-small` pack ADDED
      2026-06-15** (`csukuangfj/sherpa-onnx-whisper-small`, int8, HF-verified live; + test `test_whisper_small_pack_for_aarch64`;
      suite 931 green, pyright 0, contracts 9/9) → **T1 code-complete; only on-device verify (RU parity + A53 RTF) remains,
      gated on WB8 hardware.** (Whisper barred from WB7 by RAM; vosk-small stays the armv7 ASR.) Plus a
      **T5** refactor — when T2 lands, factor a thin `SherpaSession`/`InferencePolicy` helper shared by the sherpa ASR/VAD/TTS
      family (silero VAD currently ignores the thread policy) + optional `TorchModelCache` for silero_v3/v4 (torch `whisper.py`
      doesn't need it). And (T2) **two Piper
      TTS providers** via sherpa `OfflineTts`/VITS (`ru_RU` voices): base **`piper`** (espeak-ng, all envs incl. armv7 — the
      WB7 TTS) + **`piper_ruaccent`** which **subclasses `piper`** and adds RUAccent stress preprocessing, **x86_64/aarch64
      only** (RUAccent needs the standalone onnxruntime wheel — armv7 ORT wall; same wall blocks vosk_tts). **Key finding:** no torch-free Silero TTS exists or
      can exist (Silero refuses ONNX export — issue #283; undisclosed Tacotron-lineage; sherpa has no loader) → Piper is the
      replacement, accepting weaker espeak-ng Russian stress (RUAccent closes the gap on 64-bit). (T3) add `armv7l` to the
      provider platform taxonomy + extend CI `dependency_validator --platforms` so any armv7 profile enabling a torch provider
      **fails the build**, and evolve the `embedded-armv7` profile from headless-ASR-satellite → **ASR+TTS satellite-server**
      (TTS synthesis on + stream PCM back to the ESP32; VAD/voice-trigger/mic/playback stay off — ESP32's job). **Gating
      check ✅ VERIFIED 2026-06-15 on the real WB7:** `sherpa-onnx==1.10.46` cp39 armv7l wheel imports + the `.so` runs on
      glibc 2.31/Cortex-A7 and exposes both `OfflineRecognizer` and `OfflineTts`/`OfflineTtsVitsModelConfig` (Piper) — the
      one-engine premise holds. Completing T1+T2 is the clean resolution for the deferred **torch ×4 / transformers ×1**
      Dependabot alerts (commits 05aa763/4e05a38) — no risky major bumps. **No code until scheduled + green-lit.**

### Code Quality & Review (QUAL)
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

### Tests (TEST)
- [x] **TEST-11** [EVAL] (P2) `[deferred]` — **DONE 2026-06-27 (design).** Design for trace-driven system testing →
      `docs/design/trace_system_testing.md`. Uses the shipped ARCH-19 trace record/replay as (1) an **offline,
      deterministic, CI-able regression surface** — committed golden traces under `eval/traces/`, replayed via
      `irene-replay-trace --local` through the existing `cli_provider` (assert `exit_code === 0`), tiered
      `trace-system` (exit-code) vs `trace-ux` (DeepSeek judge) — and (2) **failure-trace capture**: always-trace +
      keep-on-failure for the live WS suite (with a small SUT enabler — `request_id` in `/ws/audio` metadata) and
      `--record-out`-on-mismatch offline, so a failed case ships a replayable trace (`--listen`/`--step`). Folds in
      the fixture-versioning fix (TEST-10) and a trace↔WAV unification idea. **Completing the design ≠ shipped:** filed
      implementation slices **TEST-12/13/14**.
- [x] **TEST-10** [EVAL] (P2) `[release]` — **DONE 2026-06-27.** Version the WS audio fixtures: carved
      `!eval/fixtures/*.wav` out of the repo's blanket `*.wav` ignore (`.gitignore`). The blanket rule had swept the
      fixtures in by accident (generic "don't commit audio"), which made the WS suite **un-runnable in CI** (no mic)
      and **non-reproducible** (re-recording → different waveform → different WER). Fixtures are versioned test inputs,
      not stray audio. Verified the carve-out (eval/fixtures wav committable; other `*.wav` still ignored) and updated
      `fixtures/README.md`. Small files; git-lfs only if they grow. _(Strategic follow-up — golden traces as the
      reviewable regression inputs — is covered by the trace-system-testing design.)_
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
- [x] **BUILD-3** (P2) — **DONE 2026-06-16.** All three images build green on GHCR
      (`ghcr.io/droman42/wb-mqtt-voice-{standalone,aarch64,armv7}`) via the per-target `workflow_dispatch` workflow:
      configs baked, the whole `assets/` tree externalized as the mounted assets-root, all runners serve the web API
      alongside their primary input (shared `WebServerMixin`, entrypoint dropped), spaCy model wheels trimmed per profile,
      and the user-facing `docs/guides/build-docker.md` rewritten (Invariant #10). **Sole remainder — container boots on
      real hardware — IS the Definition-of-release item #1 gate (ARCH-25-owned WB7/WB8 re-validation), tracked there, not
      as open BUILD-3 scope.** _Original scope below._ **SCOPE EXPANDED 2026-06-15 — now the packaging thread of ARCH-24** (the architecture has settled,
      so image contents are decidable). **Three image targets, each = one role + one config + one manually-triggerable
      (`workflow_dispatch`) buildx→GHCR workflow** (mirroring the bridge's `v<date>-<sha>`+`latest` tagging):
      **Split by ARCHITECTURE (canonical matrix: `docs/design/torch_free_armv7_voice.md` §5); torch contained to ONE image:**
      **(standalone) `Dockerfile.x86_64`** (repurpose) — x86_64 full local `voice` runner (mic→VAD→wake→ASR→NLU→TTS→playback);
      **torch** stack — existing torch Whisper + **Silero v4**; config = **baked default + external override** (built full-deps
      so an override reaches any provider). **(aarch64) NEW `Dockerfile.aarch64`** — WB8.5/Pi satellite-server; **sherpa**
      (torch-free): **Whisper-small via sherpa** + **Piper+RUAccent**; **baked** `embedded-aarch64.toml`. **(armv7)
      `Dockerfile.armv7`** — WB7 satellite-server; **sherpa** (torch-free): vosk-small + **Piper-direct**; **baked**
      `embedded-armv7.toml` (redo — current stub is bad). The two ARM satellites are the same role (ESP32 owns VAD/VT/audio),
      differing only in model allowance. **WB8.5 = aarch64** (Allwinner T507 Cortex-A53, 4 GB, Debian 11): torch *runs* there
      (aarch64 wheels exist) but is **deliberately excluded** (footprint + A53 latency) — sherpa with bigger models instead.
      Provider work: standalone = **none** (existing torch providers); aarch64 = **T1+T2**; armv7 = **T2** → **T1's sole
      consumer is aarch64**. **ORDERING (corrected 2026-06-15): the interactive sessions come AFTER the ARCH-24
      providers are implemented** — a config can't reference `default_provider="piper"` (or a Whisper-in-sherpa model) before
      the provider exists, and a Dockerfile/image can't be built/booted around providers that aren't there. Sequence:
      **(prereq) implement ARCH-24 T1 (Whisper→sherpa) + T2 (`piper`/`piper_ruaccent`) providers → then (0 ✓ targets locked
      2026-06-15) → (1–3, interactive) config per target → (4, interactive) Dockerfile design (baked-in vs mounted:
      models/config/assets/logs volumes, ports, `/dev/snd`, entrypoint, extras) → (5) per-image workflow.** Carries forward
      the BUILD-5 Dockerfile fixes (armv7 Debian base, `intent_validator`
      removal) for real build/boot verification on hardware. **Progress 2026-06-16:** **all 3 target configs DONE** —
      `embedded-armv7.toml` (sherpa+vosk-small / piper-irina / keyword→llm), `embedded-aarch64.toml`
      (sherpa+whisper-small / piper_ruaccent / keyword→spaCy(sm)→llm), `standalone-x86_64.toml` (torch whisper-small /
      silero_v4-baya / keyword→spaCy(md)→llm, full local pipeline). Satellites audio-off (relaxed the `CoreConfig`
      TTS↔Audio rule for headless TTS); all 14 configs + arch gates green. **Steps 4–5 DONE 2026-06-16 — all three
      images build green on GHCR** (`ghcr.io/droman42/wb-mqtt-voice-{armv7,aarch64,standalone}`, tags
      `latest`/`sha-<short>`/`v<date>-<sha>`). **Dockerfile design (step 4):** realigned to the wb-mqtt-bridge 3-stage
      pattern (analyzer→builder(`uv venv /opt/venv` + `uv pip install`)→lean runtime `COPY --from=builder`); **config
      baked** (`COPY` profile → `/app/runtime-config.toml`, `IRENE_CONFIG_FILE` env, no entrypoint script); **assets
      fully externalized** — the whole `assets/` tree is the mount and the assets-root (`IRENE_ASSETS_ROOT=/app/assets`,
      models/cache/credentials resolve under it), shipped as a CI archive artifact (mirrors how the bridge ships configs);
      **web_port 8000→6000** across all configs (8000 is the bridge's); runners now serve the **full web API alongside**
      their primary input (voice_runner blocking-serve + mic background; cli_runner REPL foreground + web background;
      webapi web-only) via a shared `WebServerMixin`, config-from-env drops the entrypoint. **Per-image workflow (step
      5):** `.github/workflows/build-images.yml` — `workflow_dispatch` per target, buildx→GHCR, gha cache scoped per
      target, assets archive artifact. **Repo hygiene:** Dockerfiles + `derive_build_reqs.py` moved under `docker/`;
      added repo-root `.dockerignore`. **spaCy trim (2026-06-16):** the pip-distributed spaCy model wheels are baked at
      build time (not runtime-downloaded), so `derive_build_reqs.py --config` now keeps only the first-preference model
      per supported language — aarch64 4→2 (sm pair), standalone 4→2 (md pair), armv7 unaffected; aligned to spaCy 3.8.0
      wheels. **Build patterns fixed (all 3 Dockerfiles):** analyzer needs `.[web-api]` (components import fastapi);
      `COPY --from` resolves at stage root; uv ignores pip.conf → `UV_EXTRA_INDEX_URL=piwheels` + `UV_INDEX_STRATEGY=
      unsafe-best-match` on ARM; dropped `uvicorn[standard]` (uvloop/httptools/watchfiles compile from source, need Rust)
      → plain `uvicorn`; spaCy `name @ URL` specs go one-per-line via `uv pip install -r` (unquoted `$(cat)` shell-splits
      the embedded spaces). **User-facing docs (Invariant #10) DONE 2026-06-16** — rewrote `docs/guides/build-docker.md`
      for the published-image (GHCR pull) flow, the three target roles, baked config + mounted assets-root, the
      satellite-vs-standalone run commands, and local-build instructions. **REMAINING (release-phase tail, hardware-gated):
      on-hardware boot verification** (WB7 armv7 / WB8.5 aarch64). _Original deferred note below._ **DEFERRED to the release phase
      (decided 2026-06-01): Docker builds are an end-stage
      task**, after the architecture/code work settles (image contents, extras, and armv7 viability all depend on
      the post-refactor shape — incl. QUAL-19/20 [ESP32] and ARCH-9/10 [INFER] for the sherpa-onnx/runtime
      footprint). Then verify the minimal x86_64 Docker build (builder feeds analyzer package names to
      `uv sync --extra`, which expects extra *names* — confirm/fix, now owned by **BUILD-5**) + container boots
      CLI/WebAPI. Gates Definition-of-release item #1. Refs: `docs/guides/build-docker.md`, build audit.
- [x] **BUILD-4** (P1) — DONE 2026-06-08: new **`frontend-health.yml`** workflow (push/PR on `config-ui/**`) runs the
      config-ui gates as hard checks — `npm ci`, `npm run check` (type-check + strict ESLint + orphans), `npm run build`,
      `npm run test` (vitest: 40 tests). All green today; satisfies the Invariant-#4 ongoing config-ui gate.
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
- [x] **BUILD-7** `[release]` [BUILD] (P2) — **DONE 2026-06-21.** Docker images de-bloated + the BUILD-5-deferred
      `get_python_dependencies()` extra-names migration finished. The standalone (torch) image was ~6.44 GB; a
      docker-export audit of all 3 *published* images proved **no assets/models are baked** (`/app/assets` empty, 0 model
      files; satellites 763 MB / 233 MB) — the bloat was default-PyPI torch pulling ~3.4 GB of unused NVIDIA CUDA +
      Triton into a `device="cpu"` runner. Pinned torch/torchaudio to the CPU wheel index (`[[tool.uv.index]]` explicit +
      `[tool.uv.sources]`). **Constraint:** `uv pip` honors sources for the project's own optional-deps
      (`uv pip install .[extra]`) but NOT for loose `-r` specs — so torch had to leave `pip-specs.txt` for an extra,
      which required fixing providers that returned raw specs instead of extra-names (the `metadata.py` contract).
      Migrated **31** providers/components/inputs/handlers to return extra-NAMES (or `[]`); added 10 granular per-provider
      extras + made `tts`/`llm`/`audio-output`/`audio-input`/`nlu` umbrellas; `dependency_validator` made
      extra-name-aware. spaCy models stay raw `@`-URL specs (the one exception → `derive._spacy_keep` still trims
      per-config). Removed the `Dockerfile.x86_64` cpu-torch two-step bridge (torch now CPU-pins via the
      `advanced-asr`/`tts-silero` extras). `uv.lock`: torch `2.12.1+cpu`, **0 nvidia packages**, `uv lock --check` green.
      Local gates: `ast.parse` all edits, every returned extra-name exists in pyproject, no remaining raw specs except
      spaCy URLs. **Build-confirmed 2026-06-21** (all 3 GHCR images rebuilt, green): standalone **6.44 GB → 3.16 GB**
      uncompressed (3198 MB → 955 MB compressed, −70% on the wire) — nvidia packages **2724 MB → 0**, torch `2.12.1+cpu`
      (1075 → 584 MB); satellites byte-identical (aarch64 763 MB, armv7 233 MB — no torch). Re-audited: still **0 models
      baked** (`/app/assets` empty); aarch64 spaCy trim verified (provider declares 4, config preferences 2 `sm` →
      exactly `ru_core_news_sm` + `en_core_web_sm` pulled, `md` tier trimmed). **Parked follow-up — triton:** `triton`
      (688 MB) still rides in via `openai-whisper` (its **only** requirer; imported lazily + try/except-guarded in
      `whisper/triton_ops.py`, so unused on a `device="cpu"` box → safe to drop → standalone ~2.47 GB). Two approaches
      scoped (uv `override-dependencies` vs a Dockerfile `uv pip uninstall triton`) but **deferred**. NOT removable:
      numba/llvmlite (~160 MB) — `whisper/timing.py:7` does a top-level `import numba`, required for `import whisper`.
      **Flagged (not fixed):** `Component.start`→`is_dependencies_available` `__import__`s the returned strings — dead
      code (ComponentManager uses `initialize()`; nothing calls `.start()`), but now a landmine since returns are
      extra-names; remove or rewrite later.

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
- [x] **DOC-9** [EVAL] (P2) `[release]` — **DONE 2026-06-27.** User-facing guide for the eval harness:
      `docs/guides/howto-new-test.md` (matches the `howto-*` recipe voice + a decision diagram
      `docs/images/howto-test.{dot,png}`). Walks through the three surfaces (CLI contract, WS system, WS UX-judged),
      authoring a case in each, recording the audio fixture (`make record`), and keeping cases endpoint-agnostic
      (TARGET/CONFIG). **Wired into the howto index** like its siblings: listed in `CONTRIBUTING.md` ("Add a test",
      beside add-an-intent/model/language) and the top-level `README` pointer; also cross-linked from `eval/README.md`
      (reference ⟷ walkthrough). No internal tracking language in the prose (user-facing-docs voice). Complements the
      existing `eval/README.md` + `fixtures/README.md` rather than duplicating them.
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
- [x] **DOC-6** (P2) — Archived stale historical-plan docs (`config_schemas`, `language_support`,
      `configuration_guide`, `PIPELINE_IMPLEMENTATION`, `irene_current`) → `docs/archive/`.
- [x] **DOC-7** [PEX] (P1) — DONE 2026-06-08: the parameter-extraction reference is covered across the new
      canonical set rather than one file — `guides/DONATION_FILE_SPECIFICATION.md` (the `ParameterSpec` schema +
      the ParameterType and entity_type enums), `architecture/intents.md` (extraction patterns, `get_param`,
      handler consumption of `intent.entities`), and `architecture/nlu.md` (token/slot pattern format). Closed as
      covered; the standalone `PARAMETER_EXTRACTION_GUIDE.md` was not needed.

### UI / config-ui (UI)
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

