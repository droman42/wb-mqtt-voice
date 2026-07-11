# DONE-ledger archive 001 (frozen — never re-edit; IDs stay resolvable to scope-guard via this directory)

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
- [x] **ARCH-8** [MQTT] (P-TBD) `[release]` — **DONE 2026-07-05 — all five PRs landed in one arc; the
      device suite proves the slice: 19/23 crossover fixtures green live (`make device-auto`), every red
      owned elsewhere (F40/F42 → QUAL-64 matcher tune, F41/F06 → QUAL-35 T2).**
      **★ PR-5 DONE 2026-07-05 (closes ARCH-8):** the sensor-read flow — `read_state(device_id)` joined
      `DeviceCatalogPort` (a QUERY, §13.3 — reads never touch the OutputManager), `CatalogService` gained a
      wired state-reader, `BridgeClient.get_device_state` GETs `/devices/{id}/state` (fail-soft None);
      handler `_handle_read_state` + donation method (quantity CHOICE temperature/humidity → catalog
      fields, room via D-15): dedicated `sensor` capabilities preferred, and on climate devices
      `room_temperature` is read — bare `temperature` there is the SETPOINT («уставка»), a wrong-value
      trap the tests pin. F30–F32 green live (incl. the F32 any-of equivalence). 5 new tests (suite 1255,
      pyright 0, 11 contracts). **User-facing docs delivered with completion:** `docs/guides/smart-home.md`
      (+ README link) — the promise deferred since PR-2. _Orig:_ **GATE MET 2026-07-05** (was BLOCKED 2026-07-04 on bridge
      `SCN-4`+`VWB-15`): all bridge prerequisites landed and were verified against the committed artifacts —
      `SCN-4` (scenarios became per-room `scenario_manager_*` catalog devices with a `scenario.set` enum:
      voice-drivable through the ordinary CHOICE path, **no special-casing needed**), `VWB-15` (`contracts/`
      artifacts + CI drift guard), **`VWB-20` contract patch v1.1** (typed `CatalogParam` incl.
      `unit`/`values`/`options_from`; ru+en enum labels; `aliases` schema; empty capability husks SUPPRESSED —
      the parser will not see actionless/fieldless entries), **`VWB-21`** (household alias vocabulary authored:
      34 devices + 3 rooms, e.g. «зал»→living_room). **Sequencing: TEST-17 pins v1.1 FIRST** (bridge `59f4f46`,
      catalog `7a1149c7` — DONE, since re-pinned @ `91909b54` post-VWB-23), then PR-1.
      **★ PR-1 DONE 2026-07-05:** the boundary objects landed — `intents/device_commands.py`
      (`DeviceCommand` + `RoomGroupCommand`/`GroupScope`, both address forms, fixture-shaped `to_dict()` +
      wire-shaped `request_body()`; commands ride `IntentResult.metadata[DEVICE_COMMAND_METADATA_KEY]`),
      `intents/device_catalog.py` (typed catalog model incl. `CatalogParamSpec` values-XOR-options_from,
      capability `group`, room `group_defaults` + `group_members`/`group_default` queries),
      `DeviceCatalogPort` in `intents/ports.py` (read + async `refresh()` = the ARCH-26 lazy seam),
      `core/catalog_service.py` (`CatalogService` implements the port; fetcher wired by PR-2; refresh
      failure keeps the last good snapshot), and `outputs/device_command.py`
      (`CapturingDeviceCommandOutput` — the TEST-18 capture point; scripted responder for §5b error paths).
      No `ActuationPort` (§13.6). 15 unit tests (both forms through the OutputManager's designated
      routing); suite 1201 green, pyright 0. **+ a new import-linter contract** ("Domain ports and
      boundary types stay pure") pinning `intents/{ports,models,device_commands,device_catalog}`
      against `irene.core` — ARCH-1 can't catch that inversion (intents-as-a-whole has sanctioned core
      edges); all 11 contracts kept.
      **★ PR-2 DONE 2026-07-05:** `providers/outputs/bridge.py` — `BridgeClient` OutputPort (the ONLY
      module that knows the bridge exists): POSTs both address forms (`/devices/{id}/canonical` +
      `/rooms/{room_id}/canonical`), maps §5b structured errors → `error_code`/detail
      (`param_invalid` field+reason preserved for clarify), transport failure → spoken
      `bridge_unreachable` (never raises into the pipeline); `parse_catalog` → domain `DeviceCatalog`
      (typed params, group overlay, `group_defaults`, aliases, enum triplets, `options_from`) —
      **verified against the real pinned golden** (79 devices/11 rooms @ `91909b54`, all VWB-23
      semantics). ~~Placement per §13.1: `irene.providers.outputs` entry-point group~~ **(superseded
      same day, user decision: ALL OutputPorts live in `irene/outputs/` — moved to
      `outputs/bridge.py`, the entry-point group retired, the design doc §4/§8/§10/§13.1 amended
      with dated notes; the composition imports + registers it directly).** The 6 docker-image
      configs (`standalone-x86_64`/`embedded-aarch64`/`embedded-armv7` ×ru/en) gained explicit
      `[outputs]` + `[outputs.bridge]` blocks (disabled; flipped at ARCH-25 bring-up) — all 6
      validate against `CoreConfig`. Wiring: `[outputs.bridge]` config
      (`BridgeOutputConfig`: enabled/base_url/timeout; config-master + config-ui types co-changed,
      `npm run check`+`build` clean), `CatalogService` built in `build_core` (engine attr),
      `setup_bridge_output()` in composition called runner-agnostically from the base runner post
      `core.start()` — registers + designates DEVICE_COMMAND, wires the fetcher, startup pull
      non-fatal (lazy retry per ARCH-26). ~~`bridge/catalog/version` subscribe~~ (dropped by ARCH-26 —
      no MQTT client). 13 new tests; suite 1214 green, pyright 0, 11 contracts kept. **User-facing
      smart-home doc prose deliberately deferred to PR-4/PR-5** (no guide describes device control
      until the feature exists end-to-end).
      **★ PR-3 DONE 2026-07-05 (+ the QUAL-35 RESOLVER HALF — its (b) and the resolver side of (c)):**
      `entity_resolver.py` is catalog-backed. **(1) Q7b atomic swap (QUAL-35 b):**
      `ContextualEntityResolver` dispatches by donation-declared `entity_type` FIRST (map built from
      `asset_loader.donations`); the `_is_*_entity` name-heuristics survive only as the
      GENERIC/undeclared fallback — existing donations all declare generic, so nothing changed until
      PR-4's smart-home donations declare device/room. **(2) Device resolution:**
      names+aliases per locale against the catalog, exact + RU-morphology-tolerant matching (shared-stem
      heuristic: ≥4-char stem, ≤3-char endings — plain fuzz.ratio scores «детской»/«детская» only 71),
      room-context disambiguation («эппл» → the requesting room's Apple TV), name-level ambiguity →
      `resolution_type="ambiguous"` + candidates (the clarify path's input; «ночники» stays ambiguous
      by design until the compound device), ARCH-26 lazy re-pull exactly once on a miss.
      **(3) Room resolution + D-15 (ARCH-22):** catalog rooms by name/alias/id («зал»→living_room,
      «квартире»→global fuzzy), then the coverage policy — covered room → target; real-but-uncovered →
      `uncovered_room` (spoken error, no actuation); **`global` exempt** (whole-house asks work from
      any satellite); no room → `resolve_default_room` (primary). Legacy client-context paths kept as
      fallback when no catalog (bridge disabled/unreachable). Wired via `nlu_component`
      (`_catalog_port()` → `core.catalog_service`). 14 new tests + live spot-checks against the real
      pinned golden (12/12 incl. every device-form fixture's resolution leg). Suite 1228 green,
      pyright 0, 11 contracts kept. **QUAL-35 remaining after this:** (a) T1 donations (PR-4), (c)
      handler-side room_context policy (PR-4 w/ QUAL-30), T2/T3 tiers + units + options_from
      transliteration (post-suite evidence).
      **★ PR-4 DONE 2026-07-05 (+ QUAL-35 (a) T1 donations + the handler side of (c)) — the
      vertical slice closes.** `intents/handlers/smart_home.py` (`SmartHomeIntentHandler`, domain
      `smart_home`, 9 donation-routed methods: power on/off, cover open/close, set_setpoint,
      set_brightness, playback_pause, scenario start/stop) + the T1 donation
      (`assets/donations/smart_home_handler/` contract+ru+en — **first donation with non-generic
      `entity_type`**: `target`=device / `room`=room, which is what activates the PR-3 Q7b swap
      live) + templates (`assets/templates/smart_home_handler/`, feminine ru). **The noun lexicon
      is the donation's `group_noun` CHOICE** — canonical values ARE catalog `group` names
      (light/cover), ru surfaces свет/шторы/жалюзи/занавески — with a handler-side word-boundary
      verification so «подсветка потолка» (a NAME containing «свет») stays device-form (depth
      doctrine); «весь/все» → `scope: all`. Delivery: `DeviceCommandDeliveryPort` (new domain
      port, Any-typed to stay pure) implemented by `core/device_command_dispatcher.py` over the
      OutputManager under a 7s bound; injected with the catalog port via
      `handler_manager.set_device_command_services` from `intent_component.initialize`. Speech:
      §5b error enum → templates, `param_invalid` + ambiguity + missing slots → QUAL-30/31
      clarifications (F20 playback / F21 climate encode the v1 clarify policy), catalog-backed
      setpoint range pre-validation, per-member aggregate speech names failed members (§10.4),
      no-bridge/no-catalog degrade paths. Handler enabled in config-master + all 6 docker configs;
      `smart_home = 80` domain priority. **22 fixture-mirroring tests** (real resolver → real
      handler → real OutputManager → capturing bridge; F01/02/04/05/07/08 device-form,
      F10/11/12/14/15/16 room-form, F20/21 clarify, F40/42 scenario, partial-aggregate + error +
      degrade paths) + **live webapi verification**: «включи свет в детской» → `smart_home.power_on`
      through the REAL NLU cascade (greetings/timer unaffected). Suite 1250 green, pyright 0,
      11 contracts. **TEST-18 tier-1 fixtures are now green-able** — Slice B (the eval-commons
      capture provider) turns them executable. User-facing smart-home guide prose: deferred to
      PR-5 (ARCH-8 completion). Side-fix: `.python-version` 3.11.4→3.11.12 (the dev-venv
      `_bz2`/`_sqlite3` trap's root cause). NEXT: PR-5 (sensor read) or TEST-18 Slice B. **Build notes from the 2026-07-04/05 contract analysis (recorded from
      chat):** PR-2's catalog parser codes against typed `CatalogParam` — a param carries EITHER `values`
      (stable enum `{wire,canonical,labels}` triplets) OR `options_from` (a dynamic set enumerated at
      resolution time via `GET /devices/{id}/options/<kind>` — installed apps etc.); PR-3's resolver consumes
      `names`+`aliases` per locale. Donations stay device-agnostic — the catalog supplies the entity/value
      vocabulary at runtime; donations are NEVER generated from the contract (ARCH-26 lazy refresh decouples
      the deploy cycles). **★ VWB-23 addendum (2026-07-05; re-pinned @ bridge `ee0a71d` / catalog
      `91909b54`): the boundary is ADDRESS-FORM POLYMORPHIC** — three canonical forms: device
      (`POST /devices/{id}/canonical`), scenario (rides the device form via `scenario_manager_*`), and
      **room-group** (`POST /rooms/{room_id}/canonical {group, action, params?, scope: auto|all|one}` —
      the depth doctrine: resolve only as deep as the utterance specifies; a bare capability noun is a
      room-group command, the BRIDGE picks the target via `group_defaults`). PR-1 models BOTH command shapes
      and the capturing `OutputPort` captures both; PR-2 parses `CatalogCapability.group` +
      `CatalogRoom.group_defaults` and adds the room endpoint to `BridgeClient`; PR-4 adds the noun lexicon
      («свет»→`light`, «шторы»→`cover` — bound to catalog `group` truth, not convention), the
      singular/«весь»→`scope auto/all` mapping, and speaks the per-member aggregate response incl.
      partial failures (`canonical_first.md` §10.4 pre-scripts it: «включила весь свет, бра не ответило»).
      _Orig:_ **★ ARCH-22 (2026-06-14):** the **voice-confirmation of actuation** feature (T-B,
      `docs/design/esp32_satellite.md` §10) rides this task — a sequenced `DEVICE_COMMAND → bridge rich DeliveryResult →
      derive text → SPEECH to the origin device` (opt-in `confirm_actuation_by_voice`; device-transparent, reply via
      ARCH-21). Implement it with ARCH-8's rich `DeliveryResult`. **★ Catalog contract amended 2026-06-15:** the bridge's
      `/system/catalog` now projects controllable enum fields' `values` as `{wire, canonical, labels}` triplets (bridge
      §P3.7 #26) — ARCH-8's `DeviceCatalog` parses them and device-enum resolution rides the **QUAL-29 surface→canonical**
      path (`labels`=surfaces, `canonical`=token; bridge translates `canonical`→`wire`). See `mqtt_integration.md` §5a.
      _Orig:_ **UNBLOCKED 2026-06-06** (contract AGREED); **RECONCILED with the I/O architecture
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
      device coverage + T2/T3 NLU = QUAL-35. **★ ARCH-26 (2026-07-01):** catalog refresh is **lazy** (no MQTT client on
      Irene — §5a/§14); PR-1's fake bridge **is** the capturing `OutputPort` the producer contract test (TEST-18) uses;
      PR-2/PR-3 catalog parsing builds against the committed contract artifact (**TEST-17**, gated on bridge **VWB-15**).
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
- [x] **ARCH-25** [INFER][HW] `[release]` — **DONE 2026-07-09.** WB7 (armv7) hardware bring-up, on the real
      controller. The `embedded-armv7` image boots from `/mnt/data`, the web API answers on **:8080**, the
      delivered config + mounted assets root resolve, sherpa-onnx ASR (vosk-small, 26 MB) and Piper TTS
      (irina, 79 MB) download on first boot and load, and a live Russian command round-trips:
      «который час» → «11:35», `intent_name: datetime.current_time`, confidence 1.0 — i.e. text-processing →
      NLU → intent execution all work on the A7. **REBOOT TEST PASSED** (the acceptance criterion, and the
      failure mode the bridge hit live): `uptime` 3 min, unit `enabled`/`active`, `Result=success`,
      `NRestarts=0`, **zero** dependency failures and no `/mnt/sdcard` in the boot transaction, container
      `(healthy)`, compose re-read `.env` at boot (`DEEPSEEK_API_KEY` present in the container), components
      `Requested: 9, Running: 9, Missing: 0, Failed: 0`, `/health` 200 with `inactive_providers: {}`, and
      Plane B back on its own (`:8081` ca.crt → 200, `:443` without a client cert → 400).
      The bring-up **found six defects that every existing gate had missed**, because they all run on x86_64:
      **BUG-31** (the ansible plane would have apt-upgraded the nginx serving the WB admin UI), **BUG-32**
      (the approval CLI installed under a name no doc uses), **BUG-33** (no `libopenblas` → numpy dead → no
      ASR/NLU/intents), **BUG-34** (one disabled provider's import killed nine components), **BUG-35** (the
      runners overwrote the operator's `[components]`), **BUG-36** (all of the above reported as
      `Success: 3, Failed: 0`, exit 0, healthy). Also filed from it: ARCH-44, ARCH-45, QUAL-78, TEST-20.
      Image: `ghcr.io/droman42/wb-mqtt-voice-armv7:v20260709-6c0c0b6`. **WB8.5/aarch64 on-device validation is
      NOT covered here** — no such hardware yet; the aarch64 image is built + gate-verified but unbooted.
- [x] **ARCH-26** [MQTT][DESIGN] (P3) `[deferred]` — **DONE 2026-07-01 (design; interactive session with the user).**
      Two Irene↔bridge catalog-contract questions settled and recorded in `docs/design/mqtt_integration.md` (banner +
      §5a + §8 + §12 + §13.3 + new **§14**). **(1) Catalog refresh = lazy** — startup pull + re-pull on a
      resolution/actuation miss (self-correcting, ≤1 stale round-trip); Irene runs **no MQTT client** and does **not**
      subscribe to `bridge/catalog/version`, resolving the §5a-vs-§8 contradiction in favour of no-MQTT (the retained
      topic stays a bridge concern; proactive freshness via bridge SSE is a future optional). **(2) A committed
      development contract artifact + bidirectional contract-testing seam** — the bridge's openapi `/openapi.json`
      (already carries `CatalogResponse` **and** the canonical action-request body) + a curated golden catalog ("the
      works") + a real WB7 dump, canonical home **eval-commons**; the canonical `DeviceCommand` is the boundary object,
      with `{utterance → expected canonical command}` crossover fixtures both sides test against (Irene = producer via
      PR-1's capturing fake bridge; bridge = consumer of crafted commands). **Follow-ups filed:** **TEST-17** (the
      eval-commons contract bundle), **TEST-18** (the `device_command` capture provider + producer tests) — both this
      ledger; **VWB-15** (emit the artifact) + **VWB-16** (consumer test) — the `wb-mqtt-bridge` ledger. Gates ARCH-8
      PR-1/PR-2/PR-3. Deliverable per `design-then-implement`.
- [x] **ARCH-27** [FAF][DESIGN] (P2) `[release]` — **DONE 2026-07-02 (design agreed, interactive session).**
      Durable-action substrate + handler-authoring rules designed and recorded at `docs/design/durable_actions.md`
      (D-1…D-10, all user-confirmed): explicit opt-in durability (`durable=True`; timer = only consumer today,
      future smart-home handlers required it — user scope statement), atomic-JSON store behind
      `DurableActionStorePort` (SQLite = later swap behind the same port), re-arm-by-relaunch startup reconciler
      with fire-with-apology (≤1h grace) / expiry-announcement for missed deadlines, failure notifications
      announced by default (success sub-30s stays quiet), handler-declared `redeliver_on_reconnect` (at-least-once
      for flagged durable actions, drained on client re-registration), retry machinery CUT (unblocks QUAL-61 —
      all three cuts confirmed), BUG-19 naming = the identity contract (re-arm reuses the persisted name),
      minimal read-only `/monitoring/actions[/history]`, rules bind via a new `howto-new-intent.md` section +
      `CLAUDE.md` `durable-actions` invariant (both land with the implementation). Bridge comparative lessons
      baked in: delete-at-completion atomically (anti stale-intent resurrection), persist+restore+restart-test
      ship together (anti persist-without-restore rot). Implementation follow-up filed: **ARCH-28** (7 slices).
- [x] **ARCH-28** [FAF] (P2) `[release]` — **DONE 2026-07-02.** Durable-action substrate implemented per
      `docs/design/durable_actions.md`, all 7 slices: **(1)** `AssetConfig.state_root` (`<assets_root>/state/`,
      auto-created) + `DurableActionStorePort` + `JsonFileDurableActionStore` (atomic temp+rename, corrupt-file-safe)
      + schema-v1 records + `client_registry.json` default relocated to `state/` with legacy `cache/` read-fallback
      migration; **(2)** launch choke point takes `durable=`/`redeliver_on_reconnect=` (keyword-only), persists at
      launch (JSON-validates re-arm kwargs BEFORE task creation — fail loud), deletes at completion inside the
      done-callback (same operation as the in-memory removal); timer launches `durable=True, redeliver=True`;
      **(3)** `engine.start()` runs `reconcile_durable_actions` after components / before inputs: future deadline →
      handler `rearm_durable_action` (timer override relaunches with remaining time, reuses the persisted name,
      bumps `timer_counter` past it), missed ≤1h → fire-with-apology (ru/en), older / unknown handler / re-arm
      failure → expiry announcement; old record always deleted; **(4)** redeliver-flagged completions that drop on
      an offline output are queued as `UndeliveredNotice` (TTL = 1h grace, `created_at` preserved so re-drops don't
      extend it) and drained on `/ws/audio/reply` re-attach; **(5)** failure notifications announced by default
      (`critical_only` → False; sub-30s success suppression kept); **(6)** read-only `/monitoring/actions` +
      `/monitoring/actions/history` (new `LiveActionsResponse`/`ActionHistoryResponse`; contract regenerated —
      108 paths, config-ui `gen:api-types` + `check` + `build` green); **(7)** docs — `howto-new-intent.md`
      "Long-running actions" section (the §3 contract in prose), `durable-actions` **CLAUDE.md invariant**,
      `client-registry.md` durable-actions paragraph (+ corrected its stale auto-expiry claim from QUAL-58).
      **The restart test ships with it** (`test_durable_actions.py`, 12 tests: store roundtrip/corruption, persist-
      at-launch + delete-at-completion, ephemeral-never-touches-disk, fail-loud unserializable launch, restart →
      re-arm with fresh store instance, fire-late apology, expiry, unknown-handler safety, timer remaining-time +
      counter bump, undelivered TTL/matching). The reconciler's future-deadline-with-missing-handler branch was
      caught wrong by these tests and fixed (announce-expired, not fire-early). Gates: 1156 passed / 7 skipped;
      pyright clean (11 files); import-linter 9/9. QUAL-61 now fully unblocked.
- [x] **ARCH-29** [WAKE][ASSET] (P2) `[release]` — **DONE 2026-07-04 (interactive design session).** Server-side
      wake-word model acquisition design → `docs/design/wakeword_models.md`. Decisions: a wake-word model is a
      **v2 two-file pack** (manifest + sibling `.tflite`, `from_config` resolves relative); **4-rung resolution**
      (local path → wheel built-ins [the 4 stock EN packs ship inside pymicro-wakeword, zero download — «Alexa»
      is the EN counterpart of «Ирина» for free] → v2 manifest URL [the escape hatch for microwakeword.com +
      not-yet-released HF models] → released catalog on the provider class, piper-voices pattern, starting with
      `irina` @ HF `droman42/microwakeword-irina-ru`); downloads only via AssetManager (multi-file `files:`
      support, ASSET-4 rule: no provider self-downloads); trigger layer stays **semantics-free** (word→room
      deferred to ARCH-22/QUAL-35 where a consumer exists); roster: «Ирина» → next «Валера»/«Наташа», «Борис»
      dropped (2 syllables). Implementation follow-up filed + completed same-day: **ASSET-5**.
- [x] **ARCH-30** `[release]` [FEEDBACK][DESIGN] — **DONE 2026-07-06 (same-day interactive design session).
      Problem reporting end-to-end — design AGREED**: `docs/design/problem_reports.md` (D-1..D-11). Key
      decisions: private triage home **`wb-user-reports`** (both code repos are PUBLIC — bundles narrate the
      household; shared intake with the future bridge UI button); **one Claude, two lenses** — voice→bridge
      delegation is a label flip + structured handover comment on the SAME ticket (ping-pong guard: one bounce
      each way, then owner); verbatim-capture dialog rides QUAL-30/31 with a pre-QUAL-44 check (a description
      like «свет не включается» must never execute as a command; TTL 90s configurable, cancel words, no
      re-prompt loops); bundle = last-10 turns + F&F/durable action records + always-on 5-trace ring buffer +
      day's log + redacted config + catalog version (NOT just the previous utterance — user's Q2 answered);
      delivery via ARCH-27 durable spool; 30-day bundle retention; leak fence for the public boundary;
      no-registry v1 ⇒ unclear reports always escalate with the reply pre-drafted in the reporter's language;
      D-11 model policy: `claude-fable-5` for the whole run, pinned in one env var. Implementation filed:
      **ARCH-31/32/33 + BUILD-12** here, **VWB-25** into the bridge (uncommitted, per
      `cross-repo-source-of-truth`). Raw audio, user registry, curated public issues = explicitly v2.
- [x] **ARCH-31** `[release]` [FEEDBACK] — **DONE 2026-07-06. Problem-report dialog + verbatim capture
      (voice side).** Pending-clarification gains `mode` ("combine" default = unchanged QUAL-31/44
      behavior; "verbatim" = the next utterance IS the answer) + `expires_at`; the workflow pre-check
      consumes verbatim RAW — no text processing, no NLU, no QUAL-44 (pinned by test: «свет в спальне не
      включается» lands as `description`, NLU never consulted) — and drops an EXPIRED record silently
      (D-5). New `report` handler (`report.problem`) + donation (contract/ru/en, D-9 phrases) + templates
      (6 keys × ru/en) + pyproject ENTRY-POINT (the miss the smoke suite caught: handlers discover via
      entry-points, not files); cancel words as recognition constants; service seam `set_report_service`
      (ARCH-32 injects; None ⇒ honest «Отправка отчётов не настроена» at turn 1, nothing armed — verified
      live). `ReportsConfig` (`[reports]`: enabled=false, capture_ttl_seconds=90) in CoreConfig + master +
      example + ALL 6 docker configs' handler lists (+ config-ui type parity, check+build green). Tests:
      7 dialog/workflow cases + 3 routing cases (no collisions: «расскажи о себе»→system.about,
      «что такое…»→reference intact). Suite 1318, device gate 48/48, donation gate 15 handlers 0/0,
      config gate 13/13, pyright 0. User-facing docs land with ARCH-32 (feature is off until delivery exists).
- [x] **ARCH-32** `[release]` [FEEDBACK] — **DONE 2026-07-06. Support bundle + delivery (voice side).**
      **Ring:** `core/request_ring.py` — always-on rolling request synopses (input/processed text, NLU
      provider+confidence, outcome; 500-char clips; depth = `[reports] ring_size`), appended at the pipeline
      tail via a DEFENSIVE tap (a diagnostics buffer must never fail a request — the coverage suite proved
      the point immediately). **Bundle:** `core/report_bundle.py` — description + conversation window +
      registry recent/failed actions + ring dump + day's logs (gzipped) + REDACTED config (secret-shaped
      keys/bearers out, household context stays — D-1) + metadata (version/profile/arch/language/room/
      catalog version). **Envelope §5:** `build_envelope` — title/body/labels + bundle repo path (shared
      voice/bridge intake format). **Delivery:** `outputs/github_report.py` (contents PUT + issues POST,
      fine-grained PAT from `[reports] token_env`); `core/report_service.py` — rate limit (D-7 3/h,10/day →
      "rate_limited" + new template), SPOOL-before-network to `<assets_root>/state/reports/` (crash
      safety), sent/spooled statuses; **the retry promise is a DURABLE ACTION** (ARCH-27 invariant honored:
      handler launches `report_retry` durable=True with JSON deadline kwargs + `rearm_durable_action`
      override — 5-min attempts for 48h, completion speaks in the request language, expiry announces via
      the substrate). **Wiring:** `setup_problem_reporting` beside `setup_bridge_output` (ring sized always;
      service only when enabled + repo + token — else the honest off state). Master `[reports]` fully
      documented; api.ts parity (check+build green). **Docs:** `docs/guides/problem-reporting.md` + house-
      style diagram + README (guides list, Highlights bullet — and the stale 'smart-home (planned)' fixed).
      Tests: 9 new (ring/redaction/bundle/envelope/service flows) + tightened ARCH-31 durable-launch case.
      Suite 1327, device gate 48/48, donation gate 15/0/0, configs 13/13, pyright 0. E2E against the real
      repo awaits BUILD-12 (provisioning).
- [x] **ARCH-33** `[release]` [FEEDBACK] — **DONE 2026-07-06. Owner review loop (`/inbox`), voice side.**
      `.claude/skills/inbox/SKILL.md`: gathers the queue from the SOURCE OF TRUTH (the reports repo, not this
      repo's PR list) — `fix-pr-open` + `needs-owner` tickets, lens:voice — then walks them ONE AT A TIME,
      each waiting for the owner's decision. The fix-PR path's load-bearing instruction: **verify the finding
      independently, never trust the triage** (the cloud reasons from a bundle it can't re-run; a report is
      often a transient or a dev-session artifact — PR #1 is the live example) → reproduce/refute → merge/
      revise/reject. The needs-owner path presents the triage's reporter-language reply draft for approval
      (no user registry in v1, so the owner relays out-of-band). Leak fence restated (bundle data stays out
      of public PRs); read-only until an explicit decision. **CLAUDE.md `problem-report-inbox` invariant:** a
      non-blocking session-start `gh` check mentions any waiting items in one line + offers `/inbox`, never
      auto-enters, silently skips on gh failure. Verified live: the queue queries correctly surface ticket #2
      (fix-pr-open → PR #1), zero needs-owner. **The problem-reporting workstream (ARCH-30→34, BUILD-12) is
      complete bar ARCH-34 (deferred v1.1).** PR #1 is `/inbox`'s first real customer.
- [x] **ARCH-34** `[release]` [FEEDBACK] — **DONE 2026-07-06. Bridge-evidence enrichment for smart-home
      reports.** Filed `[deferred]` v1.1 the same morning; retagged `[release]` and shipped the same evening
      once QUAL-75 lifted the dependency gate (bridge VWB-28 / contract v1.4). Every report filed while
      `[outputs.bridge]` is wired now carries the bridge's own redacted `EvidenceEnvelope`
      (`BridgeClient.fetch_report_evidence` → `GET /reports/evidence`, B-11): dispatch ring, MQTT window,
      live states, persisted-vs-live diffs — under `bridge/evidence.json` in the bundle. Design points held:
      NOT gated on the smart-home heuristic (over-attach is free; the ring-derived `smart_home_involved`
      flag rides metadata as a triage discriminator instead); **unreachable IS evidence** — every failure
      mode (transport, 429 gzip-guard, unexpected status, even a crashing fetcher) degrades to a verbatim
      `bridge/unavailable.json`, never fatal to the report; the envelope is consumed as the bridge-owned
      contract (pinned @ v1.4, QUAL-75). Composition: fetcher wired in `setup_problem_reporting` via the
      new `OutputManager.get_output` (runs right after `setup_bridge_output`); issue body's environment
      line names the evidence status. Triage side: `lens-voice.md` now reads `bridge/` first when
      `smart_home_involved` — the payoff is diagnosing bridge-involved bugs WITHOUT a lens handover.
      Tests: +6 (collector attach/unavailable/absent, envelope note, fetcher crash-safety, client status
      matrix) — suite 1337, pyright 0. Docs: design §3 table, guide + regenerated flow diagram, CHANGELOG.
- [x] **ARCH-35** `[release]` [SATELLITE][DESIGN] — **DONE 2026-07-06 (same-day interactive session).
      Python satellite design AGREED**: `docs/design/python_satellite.md` (S-1..S-9). The analysis found
      nearly everything already exists — the voice runner composes mic/VAD/wake/playback, and eval-commons'
      `ws_audio_provider` already speaks the COMPLETE /ws/audio protocol (both modes, proven vs wb7) — so
      the genuinely new surface is the reply-audio leg, live-mic pacing, lifecycle, and the S-5 TLS scope
      the user added: the emulator is the FIRST client of the fleet security plane (CSR-approval D-17 +
      mTLS wss through nginx Plane B), validating it before any ESP32 firmware exists. First-class product
      mode (a Pi room node), `[satellite]` config section with config-ui parity, hermetic TLS e2e in CI.
      Unblocks ARCH-25 (3)/(4), which were otherwise unverifiable (no firmware). Implementation filed:
      **ARCH-36** `[release]`; **BUILD-13** `[deferred]` (Pi image, S-8).
- [x] **ARCH-36** `[release]` [SATELLITE] — **DONE 2026-07-06. `irene-satellite` — the Python room node**
      (design ARCH-35 §1-9, S-1..S-9 all delivered; gates ARCH-25 items (3)/(4)). **(1)** `SatelliteConfig` +
      `SatelliteTLSConfig` in CoreConfig, config-ui type parity (`api.ts`), `[satellite]`/`[satellite.tls]`
      documented in config-master, curated `configs/satellite.toml` (mic+vad+trigger+audio on, understanding
      OFF — validator-clean). **(2)** `irene/satellite/` — `SatelliteLink` (persistent /ws/audio uplink, both
      modes, ~32ms frames, backoff 1→30s re-register) + `SatelliteReplyClient` (§4 speak_begin/PCM/speak_end
      → audio-component playback), aiohttp (base dep — no runtime dep on eval-commons). **(3)**
      `SatelliteRunner` + `irene-satellite` console script + runners entry-point (ARCH-31 lesson applied);
      wake gate = armed-window rule (`_in_armed_window`: wake fires → the NEXT segment that STARTS in the
      8s window is the command — the wake word's own segment is naturally skipped; «Ирина», pause, command);
      streaming mode = continuous pump, server-authoritative endpointing, VAD/wake bypassed (the always-on
      device model). **(4)** TLS: `provisioning.py` first-run dance (EC key via openssl CLI — key never
      leaves the box — → PUT CSR to the :80 dav zone → poll while printing the operator's `esp32-provision
      approve` line), creds at `<assets_root>/credentials/satellite/` (S-6); **finding (b) CLOSED**: nginx
      header renamed `X-Client-Cert-CN`→`X-Client-Cert-DN` (value was always the full DN) and BOTH WS
      endpoints now enforce cert-CN == claimed client_id (`_client_cert_cn`, legacy header accepted; absent
      header = local/dev, no binding). **(5)** tests: 10-test unit/loopback suite (S-9: SatelliteLink vs the
      REAL /ws/audio server over TCP via uvicorn; reply client vs the §4 contract; provisioning dance vs a
      stub bootstrap zone with real openssl CSRs) + **S-7 hermetic Plane-B e2e** (renders the ansible
      template, throwaway CA, docker nginx on host network: CSR→approve→mTLS-wss→real header injection →
      identity binding proven positive AND negative + no-cert refusal — 4.3s, skips cleanly without docker).
      **(6)** `docs/guides/satellite.md` + satellite-flow diagram + README (highlights/docs/status) +
      QUICKSTART run mode + CHANGELOG. `irene.satellite` added to 4 import-linter forbidden lists (11/11
      kept). Suite 1349 green, pyright 0, config-ui check+build clean. Live-mic behavior stays ARCH-25.
- [x] **ARCH-37** `[release]` [SATELLITE][DESIGN] — **DONE 2026-07-07 (same-day interactive session).
      Satellite tracing design** — the end-to-end utterance trace across two machines. Deliverable:
      `docs/design/satellite_tracing.md` (T-1..T-6 AGREED): in-band WS delivery with `wants_trace` as a
      first-class §3 contract field (default false — the ESP32 implements the field; grant acknowledged in
      the `registered` ack); controller gate `[trace] allow_remote_request` default off, declines recorded
      satellite-side; ONE merged self-contained file written by the satellite (device stages + nested
      `controller_trace` + `reply_audio`, ARCH-19 rotation); full device story (raw mic, VAD frames, wake
      armed-window verdicts, uplink lifecycle, reply as played); single-mode scope (streaming = always-on
      model, no device story to trace); eval-commons unaffected (additive default-false field, and the WS
      protocol is not part of the bridge pin). `python_satellite.md` §3 amended in the same change (single
      written truth). Implementation filed as **ARCH-38** `[release]`.
- [x] **ARCH-38** `[release]` [SATELLITE] — **DONE 2026-07-07 (same day as its ARCH-37 design). Satellite
      tracing — the end-to-end utterance trace.** All six design-§4 stages: **(1)**
      `TraceConfig.allow_remote_request` (default false) + config-ui parity + config-master; **(2)** server:
      `wants_trace` register field (contract default false), grant acknowledged in the `registered` ack,
      per-utterance remote `TraceContext` threaded through BOTH /ws/audio branches, `{"type":"trace"}` frame
      after each response (`_send_trace`); remote traces are shipped, never saved controller-side unless its
      own `[trace] enabled` says so; **(3)** `SatelliteLink.wants_trace` + `trace_granted` + bounded
      `_await_trace` into `last_trace` (missing frame degrades to None, never an error); **(4)**
      `SatelliteTraceRecorder` (`irene/satellite/trace.py`): raw-mic ring (30s bound), VAD frames
      (segmenter `collect_vad_frames` now live under --trace), wake/gate rolling events (skips visible),
      uplink stage with RTT + verbatim response/error, reply audio captured at the playback seam; merged
      envelope (`controller_trace` = unwrapped remote envelope | {declined} | {missing}; `reply_audio`;
      `raw_mic`) saved with ARCH-19 rotation; deterministic finalize (reply / next utterance / shutdown —
      no timers, T-5); single mode only, streaming warns and continues untraced; **(5)** replay tool
      `--show-controller` (pure display transform, the --extract-wav pattern); **(6)** satellite + tracing
      guides, CHANGELOG. Tests +4 (grant frame-follows-response vs the REAL server over TCP, default-off
      decline with clean second utterance, merged-envelope shape, declined+next-utterance finalize).
      Suite 1353, pyright 0, 11/11 contracts, config-ui clean, master config validates. eval-commons
      untouched (T-6).
- [x] **ARCH-41** `[release]` [TLS][HW] — **DONE 2026-07-08 (filed + completed same day; retagged
      `[deferred]`→`[release]` on user pull-forward; interactive discussion first, per request). Plane-B
      ports settled: bootstrap zone → dedicated `:8081`, mTLS stays `:443`, both ansible variables.**
      Live-WB7 recon reframed the problem: the WB admin UI is served by the SYSTEM nginx on `:80` (user's
      `ss`), and our ansible role deploys a site into that same nginx (`sites-enabled/*` include verified
      live) — so the conflict was never a port *bind*, it was *routing*: our `:80` server block claims the
      bare IP in `server_name`, which would steal `http://<ip>/` from the admin UI (and dropping the IP
      breaks DNS-less-home bootstrap). Resolution: the bootstrap zone gets its OWN port (`esp32_http_port`,
      default **8081**); `:443` verified free and stays (`esp32_https_port`, default **443** — inside one
      nginx a future WB https-admin coexists via SNI/name routing, no bind conflict possible). Template
      `listen` lines parametrized with `default()` filters (old `group_vars/all.yml` keeps working); the S-7
      hermetic e2e now renders its high ports as template vars — its `.replace()` port hack deleted ("no
      test-plumbing deviation left"). Client code needed ZERO changes (`bootstrap_url`/`server_url` are full
      URLs). Docs swept: `nginx/README.md` (zone table, rationale, deploy pre-flight `ss` check),
      `satellite.md`, `esp32_satellite.md` D-17, `python_satellite.md` §6, both config TOMLs' comments,
      `SatelliteTLSConfig` descriptions, provisioning docstring/error. Satellite suite 15/15 (incl. the TLS
      e2e), pyright 0/0, config-ui check green.
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
- [x] **BUG-1** [NLU/TIMER] (P2) `[release]` — **DONE 2026-06-28.** Spelled-out numbers didn't reach parameter
      extraction — «поставь таймер на десять минут» recognized `timer.set` but extracted no duration; «на 10 минут»
      worked. **General research (ru + en)** found it was **never Russian-specific**: every extractor matched `\d+`
      only, and the codebase only ever did DIGITS→WORDS (synthesis), never the reverse (comprehension) — English
      ("ten minutes") was broken identically. **Fix at the cascade entry** (not one provider): added
      `normalize_numbers_to_digits` (wraps `ovos-number-parser` `numbers_to_digits`, ru+en, idempotent, degrades to
      unchanged on unsupported lang) and call it **once in `ContextAwareNLUProcessor.process_with_context`** before the
      cascade — so the keyword matcher, spaCy, the LLM tier, the spaCy donation patterns, and (via normalized
      `raw_text`) handler text-fallbacks all see digits. Also fixed the timer's own `_parse_timer_from_text` fallback
      (it had **Russian-only units** — added English `minutes?/seconds?/hours?` + the normalize, since its donation
      param has no type so NLU never extracts its duration). The trace keeps the verbatim utterance (`record_input`
      runs upstream). Verified: ru/en spelled + compound («двадцать пять»→25, "twenty five"→25) + digit regression all
      set the timer; suite 1086 passed, pyright 0, import-linter 9/9, 10 new tests. _(Note: response still renders ru
      for en input — a separate response-localization concern, not extraction. Related debt left as-is: spaCy param
      extraction stub, entity_resolver word-numbers 0–10.)_
- [x] **BUG-2** [WORKFLOW] (P2) `[release]` — **DONE 2026-06-28.** Stale `TTS requires Audio` validation rejected
      valid satellite configs. `workflows/voice_assistant.py` had a duplicate of the TTS↔Audio check that
      **unconditionally** required the Audio component when TTS was present — a stale copy that never got the
      `system.audio_playback_enabled` condition the **canonical** `CoreConfig` validator already has
      (`config/models.py`: "satellite delivers TTS over the output seam"). So `embedded-armv7.toml` (`audio = false`,
      TTS rides the ESP32 output seam) failed to build its workflow in any runner that didn't force audio on. It was
      **masked** because `webapi_runner._modify_config_for_runner` hard-sets `components.audio = args.enable_tts` (True
      by default) — so `irene-webapi` silently ran with audio enabled, while `irene-replay-trace` honored the config and
      hit the stale check. **Fix:** removed the duplicate workflow check; the config-model validator is the single
      source of truth. Verified: full suite 1074 passed (no test relied on it), and the WB7-config golden now replays
      green with no workaround. Surfaced while recording a golden trace (TEST-12). _Noted but not changed: the webapi
      runner overriding component config is its own smell — relevant to the `--set` work, worth a future look._
- [x] **BUG-3** [NLU/I18N] (P3) `[deferred]` — **DONE 2026-06-28.** "Reply language doesn't follow request language"
      turned out to be **input corruption, not response localization** (deeper analysis, per the request). Root cause:
      the **`prepare` text normalizer transliterates Latin→Cyrillic** ("set a timer"→«сэт е таймё») and it ran at the
      **`asr_output` (pre-NLU) stage** — so English never reached NLU as English; `detect_language_by_script` then
      saw Cyrillic → `ru`, and every handler replied Russian. `prepare` is a **TTS** normalizer (it also spells symbols
      out, "$"→"доллар"); it has no business before comprehension. **Fix at the right altitude:** `prepare` runs at
      `tts_input` only — both the schema default (`config/models.py`) and `config-master.toml` (the only config that
      pinned it; all others inherit the default — verified across all 12, validator green). Plus two robustness/polish
      fixes: `_analyze_text_language`'s no-signal case now falls back to **script** (non-Cyrillic ⇒ English) instead of
      `None`→default('ru'); and the timer's own literals are localized (`_format_duration` units ru/en, the message
      fallback uses the request language). Verified: English now reaches NLU intact, detection → `en`, replies follow
      the request language across handlers; «set a timer for ten minutes» → "Timer set for 10 min…", ru unchanged.
      Suite 1086 passed (2 tests that encoded the old None→ru behavior updated), pyright 0, import-linter 9/9, 12/12
      profiles valid. _Residual (separate mechanism, not chased): the timer donation's `message` param `default_value`
      is Russian and `get_param` returns it regardless of language, so an uncustomized en reply still ends "Message:
      Таймер завершён!" — a donation-default localization concern, candidate follow-up._
- [x] **BUG-4** [NLU/I18N/DONATION] (P3) `[deferred]` — **DONE 2026-06-28.** Three related per-language defects, all
      "state not threaded to where messages render" (deeper research + the right altitude, per request):
      **(1) Donation `default_value` not language-resolved** — assembly (`_assemble_v11_donation`) flattened it to the
      ru primary; now it captures per-language defaults (`ParameterSpec.default_value_by_language`), the request
      language is threaded onto the `Intent` (set in the orchestrator from `context.language`, no get_param call-site
      churn), and `get_param` resolves strictly by request language (a param that declares per-language defaults but not
      for this language falls through to the caller default, not the ru leak). **(2) Fire-and-forget completion
      language** (the user's catch — set-timer is F&F): the request language + the request-language-rendered completion
      message are captured into the `ActionRecord` at registration and replayed at completion, and the notification
      service stopped hardcoding English (renders in the captured language / speaks the carried message). Verified
      end-to-end: en «set a timer for ten minutes» → "Timer set for 10 min. Message: Timer completed!" and the deferred
      completion fires "Timer completed!"; ru unchanged. **(3) Translation gap** — datetime en localization was missing
      `days_ordinal`/`hours`/`periods`/`special_hours` (ru/en keys now match). Gates: suite 1086 passed (+ new
      `test_param_language`, F&F test fixed for the new metadata), pyright 0, import-linter 9/9, 12/12 profiles valid,
      config-ui check+build green (the new ParameterSpec field is runtime-only, not authored in donation files). The
      donation en alias/choice **enrichment** sweep (non-functional) split out as **BUG-5**.
- [x] **BUG-5** [NLU/I18N/DONATION] (P3) `[deferred]` — **DONE 2026-07-06 (user pulled it forward — an EN tester is
      waiting). Donation EN recognition enrichment**, gap re-measured fresh (the BUG-4-era numbers held: 27 alias
      params + 10 choice params). Added EN `aliases` to all 27 (concept synonyms — "faces", "reminder", "engine",
      "into"…) and EN `choice_surfaces` to the 5 CONCEPT choices (system language ru→"russian"; timer unit
      second/sec/min/hrs…; quality ultra→"maximum"; provider_control component asr→"speech recognition"…);
      the identifier CHOICEs (provider/voice names) deliberately got NOTHING per `donation-choice-surfaces-rule` —
      canonicals self-match in EN. **smart_home taken into account** (user): structural parity was already clean,
      but 9 methods were phrase-THIN (1-2 EN vs 3-9 RU) — enriched to concept parity (mute/menu-nav/presence/
      cover-position/hvac-fan…). One regression caught by A/B probing during the work: "set a timer for ten minutes"
      had NO exact pattern (article-blind "set timer") and lived on a 0.01 fuzzy margin my keyword additions tipped —
      fixed at the root with article-tolerant phrases ("set a timer", "timer for") → exact match at 1.00 (the
      QUAL-64/Slice-3 lesson applied to EN). Pre-existing EN misroutes found while probing (NOT this task, seed
      evidence for the EN-fixture effort): "cancel the timer"→voice_synthesis.cancel, "switch asr to whisper"→
      smart_home.input_select, "translate hello to german"→greeting.hello, bare "pause"→audio.stop.
      Gates: donation validator 0/0, suite 1299, device gate 48/48 (RU untouched).
- [x] **BUG-6** [PEX/UNITS] (P3) `[deferred]` — **DONE 2026-06-28.** Timer-unit fix + consolidation + dead-stub removal
      (the "unit story", scoped time-only per user). **Bug:** "set a timer for one second" → "1 min" — the en timer
      `unit` param has no `choice_surfaces` (ru does), so the weak per-param CHOICE extraction couldn't match "second"
      and fell back to the `default_value: "minutes"`, and since `duration` *was* extracted the bilingual text fallback
      that parses it correctly was bypassed. **Fix at altitude:** the utterance's own value+unit is now authoritative —
      one shared bilingual parser `irene/utils/units.py` (`TIME_UNITS` table + `parse_duration`/`duration_to_seconds`,
      spelled→digits first), and the timer trusts it over the per-param CHOICE. **Consolidation:** the 3 unconnected
      time-unit parsers normalized to that one place — `timer._parse_timer_from_text` (deleted), `entity_resolver`
      `TemporalEntityResolver` (now calls `parse_duration`) and `QuantityEntityResolver` (time entries reuse `TIME_UNITS`;
      percent/degrees kept as the future-layer nucleus). **Dead-stub removal:** `ParameterType.DURATION` deleted (declared
      but never coerced, unused by the timer) — enum + `hybrid_keyword_matcher` branch + `donation_contract_v1.1.json`
      schema enum + config-ui (`ContractEditor` + regenerated `donation-contract.gen.ts`). Verified: "one second" → "1
      sec", ru/en 10-min + "2 hours" correct. Gates: suite 1103 passed (+ `test_units`; 2 tests redirected/removed),
      pyright 0, import-linter 9/9, 12/12 profiles, config-ui check+build green. General units-of-measurement layer
      (percent/°C) **filed onto QUAL-35** to design *with* smart-home (user: done together); ru «одну/одна» normalize gap
      noted there too.
- [x] **BUG-7** [NLU/I18N] (P3) `[deferred]` — **DONE 2026-06-28.** ru oblique-case numerals didn't normalize to
      digits. `ovos-number-parser` (ru) reads only **nominative** numerals, so the oblique-case forms common in speech
      stayed as words — «одну секунду» (one), «двух минут», «без пяти», «тридцати пяти» — and it even broke compounds
      («тридцать одну» → "30 одну"). Fix at the normalizer altitude (`irene/utils/text_processing.py`): remap the oblique
      cardinals ovos misses → nominative **before** ovos, so digit conversion incl. compounds fires. Only the forms ovos
      actually misses are mapped (одна/одной/одним→1 and сорока→40 already work, so absent); words colliding with
      non-numeric meanings are excluded so plain text is never mangled (verified «о семью детях»/«семья» untouched).
      Surfaced as the bonus finding while fixing BUG-6 (it was noted onto QUAL-35; resolved here instead). Verified:
      «одну секунду» → "1 сек", «тридцать одну секунду» → "31 сек". Gates: suite 1104 passed (+ oblique-case test),
      pyright 0, import-linter 9/9. Normalizer-only — no schema/config-ui surface.
- [x] **BUG-8** [UI] (P3) `[deferred]` — **DONE 2026-06-28.** config-ui DonationsPage composite-key + stale-state
      defects (review `config_ui_review.md` §A). All keyed by `` `${handler}:${language}` `` now: **(A1)** the
      404-fallback stored the empty donation under the bare handler name while the load effect read the composite key →
      **infinite reload loop** + stuck spinner for any handler lacking a donation file in the active language; hoisted
      `donationKey` above the try so both branches agree. **(A4)** the validation *catch* stored the error under the
      bare handler, so the language tab's indicator (reads the composite key) never showed it; hoisted the key and use
      it in the catch. **(A5)** `globalParamNames` memo read `selectedLanguage` but omitted it from deps (under a
      copy-pasted `eslint-disable`) → wrong-language autocomplete on a cached-language switch; added the dep and dropped
      the now-unneeded disable. **(A7)** `handlersList.find(...)!` then `handlerInfo.languages.length` crashed if the
      selected handler left the list mid-reload; resolve a guarded `selectedHandlerInfo` and gate the
      CrossLanguageValidation render on it. Gate (`config-ui-stays-functional`): `npm run check` (type-check + strict
      ESLint incl. `--report-unused-disable-directives` + orphans) and `npm run build` both green. BUG-9/10 (the other
      review correctness findings) remain open.
- [x] **BUG-9** [UI] (P3) `[deferred]` — **DONE 2026-06-28.** config-ui real-time analysis stale-request overwrite
      (review `config_ui_review.md` §A2). `useRealtimeAnalysis.performAnalysis` read the abort signal off
      `abortControllerRef.current` *after* the await — by then the ref points at the newest controller, so a slow earlier
      response passed the guard and clobbered newer conflicts. Fix: hold THIS invocation's `AbortController` in a local
      and guard both the success and catch paths on `controller.signal` (the ref still tracks the latest for
      abort-previous + unmount cleanup). Also threaded the signal through `apiClient.analyzeDonation` → `post(…, {signal})`
      → `request`/`fetch`, so a superseded analysis actually **cancels its network request** instead of only flipping a
      flag (`post` gained an optional `RequestOptions` arg, backward-compatible). (A6) hardened the unguarded `.conflicts`
      derefs — `result.conflicts || []` (success + cached) and `validationResult?.conflicts?.filter` — against a
      malformed payload missing the array. Gate (`config-ui-stays-functional`): `npm run check` + `npm run build` green.
      BUG-10 (unreachable blocking dialog) remains open.
- [x] **BUG-10** [UI] (P3) `[deferred]` — **DONE 2026-06-28.** config-ui enhanced-mode blocking-conflicts dialog
      unreachable (review `config_ui_review.md` §A3). Blocking conflicts disable the Apply button (`canSaveNLU` requires
      `!hasBlockingConflicts`), so the dialog's only opener — an `if (hasBlockingConflicts)` branch inside the disabled
      handler — could never run. Fix: added a dedicated **"Review blocking conflicts (N)"** trigger in `ApplyChangesBar`
      (shown when `useEnhancedValidation && hasBlockingConflicts`) that opens the dialog **read-only** (no `onResolve` →
      no dead Resolve buttons; the previous `onResolve` was a `console.log` TODO), removed the unreachable handler
      branch, and added the `applyBar.reviewBlockingConflicts` i18n key (en + ru). User triage (2026-06-28) chose to
      **build real resolution** → filed as **UI-15** (design-then-implement); this is the read-only foundation it builds
      on. Gate (`config-ui-stays-functional`): `npm run check` + `npm run build` green (orphan check confirms the dialog
      is no longer dead). Closes the config-ui-review correctness cluster (BUG-8/9/10); cleanup UI-11..14 + feature UI-15
      remain.
- [x] **BUG-11** [ASR][CONFIG] (P2) `[release]` — **DONE 2026-06-30.** Misconfigured-ASR configs failed every audio
      request at runtime instead of failing fast. **Origin disproven:** the first `make ws TARGET=local` reported "ASR
      provider 'whisper' not available", which I first hypothesised as `/ws/audio` ignoring the configured provider —
      **wrong.** Deep research (a static map agent + a live instrumented repro) proved a cleanly-launched `embedded-armv7`
      SUT transcribes the recording correctly via `sherpa_onnx` (one ASR instance, `process_audio` uses the configured
      provider, no `whisper` override; verified «Таймер установлен на 10 мин» `success:true`). The "whisper" error came
      from running the broken **`voice.toml`** (`[asr] default_provider="whisper"` with **no `[asr.providers.whisper]`** →
      zero providers loaded → the CR-A2 reconcile guard at `asr_component.py:169` only fires when `providers` is
      non-empty, so the dangling default failed every request) + a self-inflicted stale-process artifact (my
      `pkill -f irene-webapi` self-killed the management shell). **Fixes (user-approved):** **(B)** deleted the 4 stale
      broken configs (`voice`/`minimal`/`development`/`api-only`) and repointed **every** reference —
      `test_audio_negotiator` (→ `full.toml`), `build_analyzer` + `config_validator` docstrings, the live
      `cli.promptfooconfig` config-validate case (→ `embedded-armv7`), eval `Makefile CONFIG`/`voice.env`, `QUICKSTART`
      (rewritten to copy `config-master` + toggle `[components]`), 3 guides, the issue template, `env-example`, and the
      `build-system` diagram (`.dot` + regenerated PNG). **(A)** `asr_component` now **raises at init** when an enabled
      ASR loaded zero providers (was a silent warning → per-request 404s). **(C)** eval WS-suite default config
      `voice` → `embedded-armv7` (ASR-capable). **(D)** reconciled the dual default — `schemas.py` ASR `default_provider`
      `"whisper"`/`["whisper"]` → `""`/`[]` (matches the runtime `ASRConfig`). Configs 13→9. Gates: pyright 0,
      config-validator 9/9, suite 1105 passed, import-linter 9/9; armv7 SUT re-verified transcribing post-fix. _Open
      follow-up (not BUG-11): the promptfoo `make ws` harness run hung where a direct WS client succeeds — a harness-level
      issue to chase before the WS suite is green end-to-end._
- [x] **BUG-12** [EVAL][WS] (P2) `[release]` — **DONE 2026-06-30.** `make ws` reported the SUT failing ("ASR provider
      'whisper' not available") while a direct WS client succeeded — **not a hang, not the provider, not a stale SUT.**
      Root cause: **promptfoo's response cache.** An early `make ws` against a mis-launched SUT cached the "whisper"
      failure for each fixture in `~/.promptfoo/cache/cache.json`, and every later run **replayed the cached failure
      without contacting `:6000`** — proven by the SUT log showing **zero `/ws/audio` requests** during a `make ws` run,
      while `PROMPTFOO_CACHE_ENABLED=false` made the same run hit the live SUT (4 `provider=sherpa_onnx` requests) and
      return the correct «Таймер установлен на 10 мин». The eval-commons `ws_audio_provider` was correct all along
      (`call_api` succeeded directly). **Fix:** `eval/Makefile` exports `PROMPTFOO_CACHE_ENABLED := false` — every surface
      in this harness is a *live* test (CLI argparse, WS-to-SUT, DeepSeek judge), so caching can only mask reality;
      cleared the poisoned cache. **Verified:** plain `make ws` now runs live — the ASR case **passes** (sherpa
      transcript) and the intent case confirms `timer.set` live; `make cli` still 5/5. Remaining 1 fail (WER vs
      reply-text) → **TEST-15**; 2 UX errors need `DEEPSEEK_API_KEY`. _Credit: the user's "isn't the ws port different?"
      nudge reframed it from "SUT bug" to "the request never reaches the SUT" → the cache._
- [x] **BUG-13** [ASR][WS] (P3) `[deferred]` — **DONE 2026-07-02 (re-scoped with the user after
      reconciliation).** **The filed 30s hang does not reproduce**: live repro (RU streaming pack
      `vosk-model-small-streaming-ru`, `mode="streaming"`, bounded utterance + `{"type":"end"}`) gets a response —
      the provider's EOF-finalize (in the tree since 2026-06-04) works, and the eval provider does send `end`. The
      original 4/4-timeout existed only in the few-hours zipformer-en-20M window on 2026-07-01; that model was
      rejected (endpoint chops bounded commands — confirmed live: the online model loses the duration in "таймер
      на 10 минут") and removed from the catalog the same day, so the exact conditions left the tree. **The repro
      surfaced 3 real defects in the streaming branch, fixed now (user: "re-scope + fix"):** **(1)** the branch
      served ONE utterance then closed the connection — now a `while` loop with batch-floor parity (each
      end/idle/finalize re-arms; fresh recognizer stream per utterance); **(2)** a bounded client that stops
      sending WITHOUT `end` hung forever (bounded audio never trips the model endpoint; `receive()` blocked) — new
      `WS_STREAMING_IDLE_TIMEOUT_SECONDS = 10` force-finalizes the utterance; **(3)** boot warm-up and the first
      request RACED `_load_recognizer` → two recognizer instances, 2× model RAM — double-checked `asyncio.Lock`
      in the base loader (`_do_load_recognizer` split; Moonshine subclass inherits), live-verified: 1 load (was 2).
      Also: stale `embedded-armv7-en.toml` header (claimed zipformer; body is Moonshine) corrected. Regression: 2
      new WS tests (multi-utterance on one socket; no-end force-finalize with patched timeout) + the legacy fake
      made sherpa-honest (empty stream finalizes to nothing). Live verification: 3 utterances on one connection
      (with end ×2, without end ×1) all answered, single model load. Suite 1158 passed / 7 skipped; pyright clean.
- [x] **BUG-14** [ASR][BUILD] (P3) `[deferred]` — **DONE 2026-07-01 (fix implemented + proven on the WB7; full image
      buildx validation is the remaining deploy checkpoint).** sherpa-onnx ≥1.12 (needed for Moonshine's merged `.ort`
      decoder, EN ASR) failed to load on the WB7 two ways — the bundled onnxruntime `.so` has **64 KB-aligned LOAD
      segments** the WB7's 4 KB-page loader rejects (`ELF load command … not properly aligned`), and sherpa's C++ module
      needs **GLIBCXX_3.4.30** (GCC 12) which bullseye lacks. Diagnosed via SSH to root@192.168.110.250 (both fail on host
      py3.9 + a py3.11 container, PyPI & PiWheels; onnxruntime has no armv7 wheel — sherpa bundles it). Reconciled the
      "proven on hardware" claim: `onnx_inference_layer.md` §4 documented the ELF issue and pinned 1.10.46 (which has no
      Moonshine support) — the pincer. **Fix (user-approved: build the libs in Docker):** (1) armv7 Docker base
      bullseye→**bookworm** (GLIBCXX_3.4.30; +4.4 MB); (2) **`docker/patch_onnx_align.py`** rewrites the onnxruntime `.so`
      `PT_LOAD` `p_align` 64K→4K in the built venv (idempotent; safe no-op on 64-bit / non-ONNX configs); (3) bump the
      armv7 sherpa pin `1.10.46`→**`1.12.36`** (`pyproject.toml` + `uv.lock`; serves BOTH RU vosk `from_transducer` and
      EN Moonshine — the ru/en split needs no per-config machinery, `CONFIG_PROFILE` already drives it). **Proven on the
      WB7:** patched sherpa 1.12.36 on bookworm imports and runs Moonshine — RTF ~0.7, 134 MB RSS, both fixtures perfect.
      Unblocks I18N-2 (Moonshine) + streaming + newer sherpa on armv7. aarch64/x86_64 unaffected. WB7 left clean. (Full
      `docker buildx build` of the armv7 image is untested — as it was before this, per §4.7 — a deploy-time checkpoint.)
- [x] **BUG-15** [ASSET] (P2) `[release]` — **DONE 2026-07-01.** `AssetManager.download_model` treated a model path's
      mere existence as a completed download (`if model_path.exists()`), so an **interrupted or failed extraction** left a
      **broken-but-present** pack that was never re-downloaded — a permanently-wedged model recoverable only by a manual
      `rm`. Surfaced in I18N-8: a pre-`_bz2` failed extraction left empty `piper/amy` + `piper/irina` dirs, and the next
      boot skipped them → Piper warm-up failed ("missing model.onnx / tokens.txt / espeak-ng-data"). Two failure modes,
      both fixed in `irene/core/assets.py`: (1) **non-atomic extraction** — `_extract_archive` unpacked straight into the
      final path (and the `except` only cleaned the archive, not the half-written dir); now it stages into
      `.<name>.incomplete` and **renames into place only on success** (atomic on one filesystem), removing the staging dir
      on any error. (2) **existence ≠ complete** — the cache check now skips only a **populated** path (a non-empty file,
      or a directory holding ≥1 file, via `_is_populated_download`); an empty/partial path is cleared and re-downloaded.
      `download_model_pack` already validated members (non-empty), so it was unaffected. Deployment-relevant (any
      interrupted first-boot download on the WB7/satellites would wedge a model). Tests: 4 new in `test_asset_extract.py`
      (helper truth-table + failed-extract-leaves-nothing + empty-partial-re-downloads + populated-is-a-hit). Gates:
      pyright 0, suite **1120**, import-linter 9/9. Filed + fixed in one change (chat-requested).
- [x] **BUG-16** [METRICS][MEM] (P2) `[release]` — **DONE 2026-07-02.** Metrics session leak: `record_session_end`
      checked `domain in _active_actions` while entries are keyed `"{domain}:{action_name}"` (QUAL-9 shape) — never a
      match, so every session ever seen left a permanent `ActionMetric` + `DomainMetrics` entry in the singleton
      collector, growing on every REST call/WS connection (QUAL-57 §M1). Fix (metrics.py): complete the session action
      under the real `"{domain}:session"` key, **pop** the per-session `DomainMetrics` entry, keep a compact summary in
      a bounded `_recent_sessions` deque(100) + lifetime `_total_sessions_started` scalar; `get_session_analytics`
      active-check fixed to the real key, aggregates now = live sessions + recent ring, `total_sessions` = lifetime
      scalar (response gains additive `recent_sessions`; the `/monitoring/sessions` REST model is built from system
      metrics — unchanged, config-ui unaffected). Fix (context.py): eviction closes metrics via ONE seam —
      `remove_context` now calls `record_session_end`, and both the lazy sweep and `get_context` expiry route through
      it (previously the sweep skipped metrics entirely). Idempotent double-end safe. Regression:
      `test_metrics_sessions.py` (5 tests: drop-on-end, idempotency, bounded footprint across 150 sessions, real-key
      active check, reset) + 2 eviction-seam tests in `test_context_coverage.py`. Evidence:
      `docs/review/arch_memory_review_2026-07-02.md` §M1.
- [x] **BUG-17** [WS][MEM] (P2) `[release]` — **DONE 2026-07-02.** `/ws/audio` batch floor accumulated per-utterance
      PCM without any bound — a client that never sends `{"type":"end"}` (buggy satellite firmware) grew ~115 MB/h per
      connection (QUAL-57 §M2). Fix: `WS_MAX_UTTERANCE_SECONDS = 60` module constant; the utterance loop computes
      `max_utterance_bytes` from the registered sample rate and **force-finalizes** on overflow (the VAD path's
      `max_segment_duration_s` semantics — the accumulated audio is processed as an utterance, `metadata.overflow=true`,
      warning logged, loop continues; deliberately a constant, not config — a new config key would drag CoreConfig +
      config-ui along for a safety net no user should tune). Regression: `test_ws_audio_batch_overflow_force_finalizes`
      (overflow finalizes without an end frame + the connection stays usable). `dataflow.md` sentence updated
      (`user-facing-docs-are-done`). Evidence: `docs/review/arch_memory_review_2026-07-02.md` §M2.
- [x] **BUG-18** [INTENTS][LLM][MEM] (P2) `[release]` — **DONE 2026-07-02.** LLM conversation store was unbounded —
      `max_context_length` was config-read and never applied, so `handler_contexts["conversation"]["messages"]` and
      domain-thread lists grew per turn for the session's life (days, for stable room-scoped sessions), and each turn
      shipped the full history to the LLM (QUAL-57 §M3). Fix (user chose **window now + file summarization**, →
      QUAL-60): **(1)** `UnifiedConversationContext.trim_handler_messages(handler, max)` — rolling window over the
      message list, seed system prompt at index 0 pinned (the existing `clear_handler_context(keep_system=True)`
      convention) and not counted; **(2)** `add_to_thread(..., max_messages=)` windows domain threads at append;
      **(3)** `ConversationIntentHandler` enforces via `_trim_llm_context` at both append seams (after the user
      append — BEFORE the LLM call, capping prompt size — and after the assistant append) and passes the bound to
      both thread sites. Semantics: `max_context_length` = TURNS kept (×2 messages); config descriptions clarified in
      `config/models.py` + `config-master.toml` (shape unchanged; config-ui `npm run check` + `build` pass).
      Regression: `test_conversation_window.py` (4 tests: pin+window, no-op under limit, thread windowing,
      8-turn e2e with LLM stub proving messages ≤ window and per-turn prompt size stops growing). Full suite 1132
      passed / 7 skipped; pyright clean. Evidence: `docs/review/arch_memory_review_2026-07-02.md` §M3.
- [x] **BUG-19** [FAF] (P2) `[release]` — **DONE 2026-07-02.** Action-store correctness fixes independent of the
      ARCH-27 design (QUAL-56 F2/F3). **(1) Collision-proofing + identity safety:** audio/TTS action names get a
      uuid suffix (same-ms launches used to collide); `remove_action` gained an `expected=` identity guard (the
      done-callback passes its own record, so a displaced action's completion can no longer evict a live successor
      under the same key); `add_action` screams on live-record displacement (caller bug). **(2)** the 32/identity
      cap eviction now **cancels** the evicted task (was: untracked zombie). **(3) Failure unmasking at the choke
      point:** `execute_fire_and_forget_action` wraps the coroutine with a falsy-return check — the handler
      `return True/False` convention was IGNORED, so coroutines that swallowed their own exceptions were recorded
      as SUCCESS; now `False` → RuntimeError → failure path. The two exception-swallow blocks
      (`voice_synthesis_handler`, `audio_playback_handler`) re-raise to preserve the real error text. All 14
      bool-convention sites are covered centrally — future handlers inherit it. **(4) timeout ≠ cancel:**
      `ActionRecord.timed_out` set by the monitor before cancelling; history records `"timeout"` (was
      indistinguishable `"cancelled"`) and metrics finally get `timeout_occurred=True`. Regression: 4 new tests in
      `test_fire_and_forget_coverage.py` (falsy-return failure, timeout vs user-cancel ×2, displaced-callback
      guard) + 2 in `test_action_store.py` (cap-evict cancels, identity guard); 1 outdated test updated to the new
      contract (speak failure now raises). Full suite 1144 passed / 7 skipped; pyright clean.
- [x] **BUG-20** [TEST] (P2) `[release]` — **DONE 2026-07-02 (filed + fixed same day; surfaced by the QUAL-61 gate
      runs).** The smoke suite's "offline degrades gracefully" test was **not offline**: the SUT subprocess inherited
      real LLM keys from the developer shell (the eval judge's `DEEPSEEK_API_KEY`) AND from the repo-root `.env`
      that every runner `load_dotenv()`s — so the test made a **live DeepSeek call** and flaked whenever the API
      answered slower than the 25s client timeout (the mysterious 59s full-suite runs WERE the slow-API runs;
      causality was backwards from the "load flake" hypothesis journaled under ARCH-28). Fix: the smoke fixtures
      launch the SUT with every `*_API_KEY` **blanked, not stripped** — dotenv never overrides an existing var, so
      an empty value beats both leak paths (`_offline_env()` collects key names from the shell env AND `.env`).
      Result: the offline degrade path is proven genuinely fast (smoke 6/6 in 12.5s), and the full suite dropped
      from 24–59s to ~20s — it had been quietly calling DeepSeek on every run. Regression-proof by construction
      (the test now fails if the degrade path ever regresses, instead of being rescued by a live LLM).
- [x] **BUG-21** [BUILD][TOOLS] (P2) `[release]` — **DONE 2026-07-02 (filed + fixed same day; surfaced by the
      BUILD-9 live CI runs + the user's local `--validate-all-profiles` output).** Double defect in the
      build-analyzer validation gate: **(1) stale rule** — "TTS providers enabled but no audio output providers
      configured" flagged all four satellite profiles as INVALID, but that combination is the ARCH-22 design:
      satellites synthesize TTS and stream the reply over the WS reply channel with deliberately no local audio
      provider. Fixed: the analyzer records `system.web_api_enabled` on `BuildRequirements` and errors only when TTS
      has NEITHER a local audio provider NOR the web-API reply channel (a truly dead TTS). **(2) swallowed exit
      code** — `--validate-all-profiles` printed ❌ INVALID and `return 0` unconditionally, so the CI gate (old
      backend-health AND the new ci.yml) had been decorative all along; it now exits 1 when any profile is invalid.
      Also in this change: `test_smoke_e2e.VENV_BIN` resolves console scripts next to `sys.executable` instead of
      the hardcoded `.venv/bin` (absent in the pip-based CI env — run-4 failure). Verified: all 12 profiles VALID,
      tool exit honest, full suite 1156 passed / 7 skipped.
- [x] **BUG-22** [WEBAPI] (P2) `[release]` — **DONE 2026-07-05 (found + fixed during TEST-18 Slice B).**
      **`room_alias` validation on `/execute/command` NEVER worked live:** `web_server.py` built its own fresh
      `IntentAssetLoader` and loaded ONLY web templates, so the router's localization consumers saw empty data
      — every room-scoped request got 400 «Invalid room alias … Valid aliases: []» (latent since the endpoint
      gained room support; TEST-18 was the first real caller). Fix: `_setup_web_asset_loader` now PREFERS the
      intent system's fully-loaded asset loader (donations/templates/localizations/web templates), keeping the
      fresh web-templates-only loader as the fallback for a core without the intent system. Also extended
      `assets/localization/rooms/{ru,en}.yaml` with the house's rooms (children_room, cabinet, hall, entrance,
      shower, wardrobe, global) — the aliases the validation accepts.
- [x] **BUG-23** [TXTPROC] (P2) `[release]` — **DONE 2026-07-05 (found live by the TEST-18 device suite,
      fixture F51: `spoken: "hdmiодин"`).** **The `numbers` normalizer (digits→WORDS — the SYNTHESIS
      direction) ran on `asr_output`,** fighting the BUG-1 words→digits pre-NLU normalization and
      corrupting alphanumeric values before extraction («hdmi1»→«hdmiодин»; «25»→«двадцать пять»→
      mis-reparsed — the real cause of F06's range error, previously misattributed to T2 compound
      numerals). Same disease `prepare` had (BUG-3). Fix: `tts_input`-only in the pydantic defaults +
      config-master + explicit `[text_processor.normalizers.*]` blocks in all 6 docker configs.
      **En-route (user question): the 3 `-en` configs inherited `latin_to_cyrillic: true` by default —
      an ENGLISH deployment would transliterate its entire TTS input to Cyrillic** (unheard only because
      on-device EN TTS validation rides ARCH-25); the `-en` blocks now set `latin_to_cyrillic = false` +
      `language = "en"` (QUAL-38 per-normalizer deployment language). Default-stage regression test added.
- [x] **BUG-24** [NLU][TXTPROC] (P2) `[release]` — **DONE 2026-07-05 (found live by the TEST-18 device
      suite, fixture F06).** **BUG-1's words→digits normalizer destroyed «тёплый пол»:**
      `ovos_number_parser.numbers_to_digits(ru)` maps a STANDALONE «пол» to 0.5 («тёплый пол» → «тёплый
      0.5») — the floor-heating device reference became unresolvable. Fix in
      `utils/text_processing.normalize_numbers_to_digits`: standalone «пол» is guarded through the
      conversion via a sentinel unless followed by a measure word («пол часа» still → «0.5 часа»);
      inflections were never converted anyway. Regression-tested (incl. alphanumeric pass-through).
- [x] **BUG-25** `[release]` [CLI][UX] — **DONE 2026-07-06 (filed + completed same day; found live by the
      user's first interactive multi-turn CLI session). Every other interactive command was SWALLOWED +
      the prompt looked hung after each reply.** Two defects, one session: **(1)** `CLIInput`'s single
      command queue had TWO racing consumers — the runner's interactive loop (real) and
      `InputManager._listen_to_source`, feeding an internal queue that NOTHING drains (dataflow review
      **P0-8**'s dead pipe — the ARCH-15 PR-5b comment eliminated the double READER but missed the double
      CONSUMER). asyncio alternates queue waiters: command #1 processed, #2 gone. Fix: the dead pipe
      deleted outright (`_listen_to_source`/`_input_queue`/callerless `get_next_input`) — the manager owns
      source lifecycle ONLY. **(2)** the reader re-prompts before the reply arrives, and the reply printed
      OVER the active prompt (terminal looked hung until the next Enter). Fix: `PromptSession.prompt_async`
      + `patch_stdout` — output (sync replies AND deferred results, e.g. a timer firing later) inserts
      ABOVE the prompt and redraws it. 2 regression tests (manager-never-consumes + two-commands-in-order);
      suite 1302, pyright 0.
- [x] **BUG-26** `[release]` [NLU] — **DONE 2026-07-06 (filed + completed same day). «расскажи о себе» lost
      to conversation.reference BY LOAD ORDER — an exact raw-score tie.** `system.about` owns the literal
      phrase, but the authored boosts cancelled the QUAL-64 specificity edge to the last digit
      (about: spec 1.2 × boost 1.1 == reference: spec 1.1 × boost 1.2 == 1.4256) and the stable sort fell
      back to donation load order. Fix at both depths: **(1)** the matcher's pattern sort now tie-breaks on
      the MATCHED pattern's token count, then intent name — deterministic, boot-order-free (QUAL-64 closed
      constant ties; this closes manufactured ones); **(2)** system.about boost 1.1 → 1.2 (an exact
      full-utterance phrase deserves to win outright). 5 routing regression cases both directions
      («что такое …»/«кто такой …»/«расскажи о погоде» stay reference; «справка» stays help). Bonus:
      «расскажи о себе» now answers OFFLINE («Я Ирина, …») — no LLM needed for the self-introduction.
- [x] **BUG-27** `[release]` [I18N] — **DONE 2026-07-06 (filed + completed same day). «сколько времени» →
      "12:54 PM" — a US-format reply in a Russian conversation.** Root cause: the ru donation shipped
      `default_value: "12hour"` for the time format, preempting the handler's own designed default (the
      natural-language «Сейчас … дня» path) and rendering `%I:%M %p`. («который час» escaped by accident:
      its «час» token fuzzy-matched the «24 часа» choice surface → 24hour.) Fix: ru default → verbose (the
      natural path), and the EXPLICIT ru 12-hour rendering says the day period in words from the existing
      localization table («1:11 дня»), never "%p".
- [x] **BUG-28** `[release]` [ARCH][F&F] — **DONE 2026-07-06 (the problem-reporting system's FIRST
      self-caught bug: filed by voice report → diagnosed by cloud triage → PR reviewed via `/inbox` →
      merged `e1dd319`). Durable actions died silently across GRACEFUL restarts** — two compounding
      defects, both independently verified at review: **(1)** `_on_action_done` deleted the persisted
      record on ANY cancellation, including teardown-cancel (SIGTERM/docker restart) — durability only
      worked across hard crashes, violating the design's own D-2 exit discipline; also emitted a spurious
      «сбой действия … cancelled» at every shutdown; **(2)** `reconcile_durable_actions` deleted the record
      in a `finally` AFTER a successful re-arm — re-arm re-persists under the SAME `action_name` (D-8), so
      the delete destroyed the fresh record; one restart unhooked the promise. The masking test hand-re-saved
      the record. Fix (triage-authored, owner-reviewed): `ActionRecord.deliberate_cancel` marker (BUG-19
      `timed_out` pattern; set by user-cancel + eviction) — unmarked cancel = teardown → record survives,
      no failure notification; reconciler deletes only consumed records. Flagship regression: set → restart
      → re-arm → restart → still re-arms. Suite 1331, pyright 0 on the integration merge.
- [x] **BUG-29** `[release]` [UI][CONFIG] — **DONE 2026-07-06. Default `web_port` 6000 → 8080 —
      the config-ui could not reach the backend from ANY browser** (found in the REL-3 manual functional
      pass; the exact class of defect no automated test catches — `curl` is happy on 6000, a browser is not).
      Port 6000 is X11, on Chromium/Firefox's hard-blocked list → every config-ui request failed
      `net::ERR_UNSAFE_PORT` before leaving the browser (a retry-storm of 35k+ requests). Violated
      `config-ui-stays-functional` on the shipped defaults. Swept 6000→8080 (word-boundary, 16000 sample
      rates untouched) across all 13 configs, the `CoreConfig.web_port` model default (the source of truth),
      the config-ui `defaultApiBase()` + generated openapi default, `ops/docker-compose.yml`, all 3
      Dockerfiles (CMD/EXPOSE), `ops/INSTALL.md`, QUICKSTART (was inconsistently 8000). 8080 chosen (user):
      browser-safe, no collision with the bridge (8000) or config-ui (3000). Verified: default boot binds
      8080; config gate 13/13; config-ui check+build green.
- [x] **BUG-30** `[release]` [OPS][LOGGING] — **DONE 2026-07-08 (filed + completed same day; found while
      walking the ops story — user: "are our logs rotating, or one endless file?"). Unbounded file logging
      fixed — the bridge's rotation scheme ported verbatim.** Before: `setup_logging` renamed the previous
      log at startup then opened a plain `FileHandler` — one endless file for the whole (weeks-long,
      `restart: unless-stopped`) container run, and the startup renames accumulated forever; a disk-fill
      aimed at `/mnt/data`, which also carries durable state + docker's data-root. Now (mirror of bridge
      `app/bootstrap.py::setup_logging`): **fresh file per startup** (`_startup_rollover` into the
      `irene.log.<stamp>.log` sibling family; empty file reused) + **`TimedRotatingFileHandler` at
      midnight** with `backupCount=LOG_RETENTION_DAYS=30` and the custom `suffix`/`extMatch` pair (without
      which backupCount deletes nothing) + **`_prune_old_logs`** sweeping startup-renamed siblings past
      retention (the handler's cleanup can't see those). The report bundle's same-day glob moved to the new
      family (`report_bundle.py::_todays_logs`). `test_logging_rotation.py` rewritten (7 tests); bundle
      tests 4/4; pyright 0/0. Docker's json-file caps only ever bounded stdout — the file channel was the
      uncapped one.
- [x] **BUG-31** [OPS][HW] `[release]` — **DONE 2026-07-09.** Plane-B ansible managed nginx/openssl packages and
      would have upgraded the controller's web server mid-deploy. Found while installing the plane on wb7 for
      ARCH-25: the box has `nginx-common` + **`nginx-extras`** (serving the WB admin UI on :80) but no `nginx`
      metapackage, so `apt: name=[nginx, openssl] state=present` resolved it and `apt-get -s` showed a
      version-matched cascade — nginx-extras deb11u5→u8, openssl, and five `libnginx-mod-*` — plus an nginx
      restart. Fixed by **asserting instead of installing**: a `check_mode: false` probe of `nginx -V` /
      `openssl version`, then an `assert` that both exist *and* that the build carries
      **`--with-http_dav_module`** — the `:8081` bootstrap zone takes the device CSR over a WebDAV `PUT`, so
      `nginx-light` would pass `nginx -t` and then refuse every submission. (The `check_mode: false` is
      load-bearing: `command` is skipped under `--check`, and the assert then fires on empty results — caught by
      dry-running the fix.) Also gitignored the operator-local `inventory.ini` / `group_vars/all.yml`, and fixed
      the README runbook's pre-ARCH-41 portless bootstrap URLs. Deployed to wb7: packages verifiably still at
      deb11u5, admin UI on :80 → 200, `:8081` ca.crt → 200, `:443` without a client cert → 400.
- [x] **BUG-32** [OPS][HW] `[release]` — **DONE 2026-07-09.** The operator CLI installed under a name nothing
      documents. `deploy.yml` copied all three scripts verbatim, landing the approval CLI at
      `/usr/local/bin/esp32-provision.sh`, while `nginx/README.md`, `esp32_satellite.md` D-17, and the script's
      own `usage()` all invoke **`esp32-provision`** — so on the WB7 the documented approval runbook died at
      `esp32-provision list` → `команда не найдена`, and approving a CSR is the *only* way this plane is ever
      used. Fixed: the operator CLI installs without the extension; the two internal helpers keep `.sh` (both are
      invoked by absolute path — by the play, and by `esp32-provision` calling `esp32-sign-csr.sh`); a
      `state: absent` task removes the mis-named binary from any box that ran the old play. Re-ran on wb7:
      `changed=2` (exactly the rename + the removal), CA init correctly no-op under its `creates:` guard,
      `esp32-provision list` now prints the pending CSR + pubkey fingerprint. Same root cause as **BUG-31**,
      filed minutes earlier: the playbook had never been executed end-to-end against a real controller. The
      bootstrap zone itself is proven — a real device CSR `PUT` to `:8081` returned **201**.
- [x] **BUG-33** [BUILD][HW] `[release]` — **DONE 2026-07-09.** The armv7 image had no `libopenblas.so.0`, so
      numpy could not import and the assistant had no ASR, NLU or intents. numpy's own error is misleading; the
      chained cause is `libopenblas.so.0: cannot open shared object file`. armv7 only: numpy there comes from
      **PiWheels** (`Tag: cp311-cp311-linux_armv7l`), which links the *system* openblas and ships no
      `numpy.libs/`, while PyPI's manylinux wheels bundle it (aarch64 verified unaffected). Nothing declared it —
      `get_platform_dependencies()` is provider-scoped, and numpy was a **base** dependency owned by no provider
      (the CR-C4 "numpy is base, don't re-list" note is what created the blind spot).
      **Fixed by Option B (owner's call): numpy is no longer a base dependency.** It moved into the extras of the
      providers that actually import it — `wake-onnx`, `nlu-spacy`, `audio-sounddevice`, `audio-miniaudio`,
      `audio-output`, `tts-silero`, plus new `vad-energy` / `vad-silero` (deliberately NOT `asr-onnx`, which is
      what armv7 installs for sherpa). `providers/vad/{energy,silero}.py` now declare them, so the dynamic build
      picks it up: `build_analyzer --config embedded-armv7.toml` resolves to `['asr-onnx','llm-openai','web-api']`
      with **no numpy**, and no `libopenblas0` is needed anywhere. This matches the code's own long-standing
      intent — `asr/sherpa_onnx.py` and `tts/piper.py` were written numpy-free *for armv7* (their comments claimed
      "armv7 has no numpy wheel", which is false and now corrected). `core/audio_negotiator._downmix_to_mono` was
      the one unguarded numpy call site on the live audio path; rewritten with stdlib `array`, verified
      bit-identical to the numpy version across 900 random multi-channel buffers.
- [x] **BUG-34** [ARCH][BUILD] `[release]` — **DONE 2026-07-09.** One optional provider's missing dependency took
      out nine components, and which survived depended on line order. `components/__init__.py` eagerly imported
      every component; its line 8 pulled `voice_trigger_component` → `providers/voice_trigger/__init__.py` →
      `openwakeword.py`'s module-scope `import numpy` — for a provider `embedded-armv7` **disables**. The
      survivors (`tts`, `asr`, `llm`, `audio`, lines 4–7) lived only by already being in `sys.modules`. Fixed in
      two layers: (1) the package `__init__`s of `components/`, `providers/{asr,audio,nlu,voice_trigger}/` now
      import only the ABC and expose concrete classes through a PEP-562 `__getattr__` (the shape
      `providers/vad/__init__.py` already had), so importing one component never imports the other eight; (2) the
      three module-scope numpy imports (`utils/vad.py`, `providers/nlu/spacy_provider.py`,
      `providers/voice_trigger/openwakeword.py`) are guarded, with `SimpleVAD.__init__` raising a message that
      names the extra to install and the two providers reporting unavailable rather than crashing. Verified by
      importing every component and the runner against a fake `numpy` that raises `ImportError` — all import with
      numpy absent, all still work with it present; `pyright` 0 errors (annotations moved to an `NDArray = Any`
      alias, since the `no-type-checking` invariant rules out a `TYPE_CHECKING` import); import-linter 11/11;
      27 VAD/resampling tests pass.
- [x] **BUG-35** [ARCH][CONFIG] `[release]` — **DONE 2026-07-09.** The runners overwrote the config file's
      `[components]` block. `webapi_runner._modify_config_for_runner` assigned eight of the eleven flags
      unconditionally (`audio = args.enable_tts`, `asr = True`, `nlu`, `intent_system`, `monitoring`,
      `text_processor`, `tts`, `voice_trigger = False`) right after the TOML loaded (`base.py:282`), and
      `--enable-tts` was declared `action="store_true", default=True` — a flag that **can never be False**, so
      TTS and audio were hardcoded on by something that looked configurable. `voice_runner` forced five
      components plus `vad.enabled` the same way. Consequences: `embedded-armv7`'s `audio = false` ("no local
      speaker") ran the audio component anyway; a text-only web deployment could not disable ASR (paying the
      ~38 s sherpa graph init and the model download); server-side `voice_trigger` was unreachable;
      `[components]` was a lie in `config-master.toml` and config-ui, against `config-master-canonical` and
      repo-owns-config (BUILD-17). Worse, **each runner's own validator was dead code** — it runs at
      `base.py:311`, after the override had already set every value it inspects, so `intent_system`/`asr`/
      `web_api_enabled` errors could never fire.
      Fixed: the preset now forces only the **input topology** (its identity per `io_architecture.md`, whose
      precedence bullet is clarified — presets own the input/output set, never `[components]`), `--enable-tts`
      became a real tri-state (`--enable-tts` / `--no-tts`, default = honour the file), and structural
      requirements became **live validation** that refuses to start naming the exact key (webapi: intent_system,
      nlu; voice: asr, audio, intent_system, nlu, text_processor, vad.enabled), plus warnings for legal-but-
      surprising choices (asr off; voice_trigger on without a local mic). `satellite_runner` deliberately
      untouched: it forces components *off*, which is deny-by-default for a thin device. Verified against the
      real profiles: `embedded-armv7` under webapi now reports `runner-changed components: NONE — config
      honoured` with `audio=False`, `--no-tts` overrides the file, `standalone-x86_64` under voice validates
      clean; disabling a required component now errors instead of being silently switched on. Safe to drop the
      audio component on the web path — `voice_assistant.py:169` treats it as optional and the dependency
      resolver skips deps that aren't enabled. `test_voice_runner.py` rewritten to the new contract (10 pass),
      pyright 0, import-linter 11/11.
- [x] **BUG-36** [ARCH][OPS] `[release]` — **DONE 2026-07-09.** Nine components failed to load and the runner
      reported `Success: 3, Failed: 0`, exit 0, `/health` 200, Docker `healthy`. Four independently "graceful"
      decisions composed into a lie: (1) `utils/loader.py` logged an ImportError at WARNING and dropped it;
      (2) `core/components.py` computed the enabled set by iterating **what loaded** and filtering by config, so
      an enabled-but-unimportable component was neither initialized nor failed — it was *absent from the
      universe*; (3) `_failed_components` only ever saw components that were discovered and then raised, so the
      counter could not be non-zero; (4) `get_deployment_profile()` counted the *config*, printing intent (6)
      beside reality (3). `run_startup_validation` passed because it resolves entry-point **names** in metadata,
      which succeeds whether or not the module imports.
      Fixed: the config is now the authority (`requested` from `[components]`), anything it names that did not
      load is recorded with the loader's reason (the loader now *returns* its failures), and the summary line
      reports `Requested / Running / Missing / Failed to initialize` at ERROR. A missing component **aborts
      startup** (`RequiredComponentsUnavailable`) unless it is one of the observability surfaces
      (`monitoring`, `nlu_analysis`, `configuration`), which degrade instead — and while any is degraded
      `/health` returns **503**, so Docker/systemd see the truth. Provider level, per the owner's ruling that a
      configured provider that doesn't come up means the component isn't ready, split by failure kind:
      **kind 1** (cannot import / no entry point — a broken build, BUG-33's class) fails the component and so
      aborts; **kind 2** (imports but reports unavailable — no `DEEPSEEK_API_KEY`, no network) is an anticipated
      condition the profiles cover with `fallback_providers = ["console"]` and `INSTALL.md` promises, so it logs
      at ERROR and is published on `/health.inactive_providers` — loud, never fatal. This distinction was found
      by *running* the change: strict-everywhere refused to boot the keyless smoke suite, i.e. it would have
      bricked any controller without a DeepSeek key. Also: `llm_component` swallowed its own init exception
      entirely and warned "No LLM providers available"; it now raises. `asr`'s CR-A2 "reconcile the default to
      whatever survived" swap is gone — the configured default must be usable. **Build gate added**
      (`docker/verify_components.py`, wired into all three Dockerfiles): every component + provider the baked
      profile enables must import *in that image, on that architecture*, after the lean-down. It would have
      caught BUG-33 before publish; every other gate runs on x86_64, where numpy vendors its own openblas.
      Verified live both ways: keyless boot → 200 + `inactive_providers: {llm.deepseek: …}`; a bogus configured
      provider → exit 1 naming it. pyright 0, import-linter 11/11, 1358 tests pass incl. the 6 hermetic smoke.
- [x] **BUG-38** [MQTT][NLU][SAFETY] `[release]` — **DONE 2026-07-09.** A named device ignored the room the
      user spoke, and actuated one somewhere else. **Confirmed on the WB7 before fixing** (owner authorised the
      test): with the living-room floor lamp `off` and the bedroom holding no floor lamp at all,
      «включи торшер в спальне» returned `success: true`, «Включила Торшер», `device_id: living_room_floor_lamp`,
      and the living-room lamp went `on`. No satellite, no client room — plain REST. Lamp restored afterwards.
      Cause: `_result_from_candidates` narrowed by room only under `if len(candidates) > 1`, so a uniquely-named
      device skipped the room check entirely; and the device path never consumed the `uncovered_room` refusal the
      resolver already produces (D-15 rule 2b), so a satellite naming a room it does not cover actuated anyway.
      Lights had always worked only because «свет» is a *group noun*, routed to `_room_group`, which calls the
      D-15 pass the device branch never called.
      Fixed in the resolver, so every device-name path inherits it (power, cover, playback, `read_state`, and the
      `scan_utterance` path «на кухне вытяжку включи» takes): the raw room word is threaded down from
      `_resolve_single_entity` — raw, not `room_resolved`, because entity resolution walks `intent.entities` in
      donation order and the sibling room may be unresolved when the device resolves — matched with
      `match_catalog_room`, and the candidate set is scoped **always**, keeping `room == target` **or**
      `room == "global"` (8 of 79 devices are whole-house aggregates the resolver already exempts; a blanket
      filter would have broken «включи печь на кухне»). Named room holding no such device → new
      `no_device_in_room` result → the handler speaks a **new template** `err_no_device_in_room`
      («Спальня: не нашла там «Торшер».» / `"{room}: I couldn't find “{ref}” there."`), mirroring
      `err_no_group_in_room`'s shape so the room's nominative name needs no case agreement. `uncovered_room` now
      refuses on the device path too. When **no** room is spoken, rule 3 is unchanged: the client's room stays a
      tie-break hint that may narrow an ambiguity but never contradicts the user.
      8 regression tests in `test_catalog_resolution.py` (refusal, unique-match scoping, spoken-room-beats-client-
      room, ambiguity resolved by room, `global` survival, unknown-room fall-through, within-room ambiguity
      preserved for BUG-39, rule-3 unchanged). Suite 1366 pass (the lone failure is the TEST-20 flake, verified),
      pyright 0 — it caught a real `room_id: str | None` hole in the first draft — import-linter 11/11, smoke 6/6.
      **Needs a voice rebuild + redeploy to reach the WB7.**
- [x] **BUG-40** [MQTT][APICONTRACT] `[release]` — **DONE 2026-07-10.** Every bridge error collapsed to
      `internal_error`: voice never unwrapped FastAPI's `detail`. Found on the WB7 (2026-07-09) while re-testing
      BUG-38 («выключи кондиционер в гостиной» → the bridge answered a precise `503 device_unreachable`, the user
      heard «Что-то пошло не так на стороне моста»), and hit again on both 2026-07-10 AC smokes. The bridge raises
      `HTTPException(status_code=…, detail=resp.model_dump())` for every canonical failure, so on non-2xx the
      canonical body arrives one level down in FastAPI's `detail` envelope — while `_to_delivery_result`
      (`outputs/bridge.py`) read `success`/`error`/`state` at the **top level**, saw `{}`, and stamped
      `internal_error`. Blast radius was the whole taxonomy: the handler's template map (`err_device_unreachable`,
      `err_device_not_found_bridge`, `err_capability`…) was unreachable, and the `param_invalid` → one-shot
      clarification path (QUAL-30/31, §5b) could never fire because `field`/`reason` lived inside the dropped
      envelope. **Why it survived:** every existing test fed a *string* detail — only the unstructured branch was
      ever exercised.
      Fixed by unwrapping `payload["detail"]` when it is a dict, before the existing field reads; a string
      `detail` stays on the genuinely-unstructured branch (`503 "Service not fully initialized"`). Regression
      tests: wrapped-envelope payloads for 5 canonical codes + a wrapped `param_invalid` carrying `field`/`reason`
      (`test_bridge_output.py`), and a handler-level test that a bridge-side `param_invalid` **arms the one-shot
      clarification** (`test_smart_home_handler.py` — that path had demonstrably never run against a real
      bridge). Suite 1379 pass (lone failure = the TEST-20 flake, verified passing in isolation). Shipped in
      **v0.5.1**.
- [x] **BUG-41** [MQTT][CONFIG] `[release]` — **DONE 2026-07-10. Voice's 5 s HTTP timeout is shorter than the
      bridge's now-honest slow-echo wait — every gated AC command would time out while succeeding.** Found
      while consuming the bridge's v0.6.0 release cut (TEST-21): their DRV-29 fix makes `/devices/{id}/canonical`
      hold the response open up to the capability's `gate.poll_timeout_ms` — **15 000 ms on all six
      `MitsubishiHvac` capabilities** (derived from the firmware's packet rotation: ~13 s worst case, 5–7 s
      typical) — and their ledger states plainly: *"voice's HTTP timeout must exceed 15 s."* Voice's
      `BridgeClient` used `aiohttp.ClientTimeout(total=5.0)`; the config description still said the timeout
      "covers the bridge's ~500 ms actuation echo-wait" — an assumption DRV-29 retired. With a 5–7 s typical
      echo, voice would speak `BRIDGE_UNREACHABLE` («мост не отвечает») for a *working* AC command roughly half
      the time — the same dishonest-failure class DRV-29 just fixed bridge-side, recreated one hop upstream (the
      morning's clean «включи кондиционер в детской» retest was luck, not margin). Fix: `timeout_seconds`
      **5.0 → 20.0** (15 s worst case + margin; sits under the workflow's `command_timeout_seconds = 30`) in the
      `BridgeOutputConfig` default, the `BridgeClient` constructor default, and all 8 configs carrying
      `[outputs.bridge]` (master, example, 4 embedded, 2 standalone) — config is delivered by `update.sh`, so
      the deployed WB7 gets the value without waiting for an image pull. One test updated (asserted the old
      default). Suite 1379 pass (lone failure = the TEST-20 flake). config-ui untouched: the schema shape is
      unchanged, only the default moved. Shipped in **v0.5.2**. Successor concern → bridge **VWB-34** (publish
      confirmation-timing in the contract so this number stops being out-of-band folklore).
- [x] **I18N-1** [DESIGN] (P3) `[deferred]` — **DONE 2026-07-01 (design; no code).** Real English deployment design →
      **`docs/design/multilingual_deployment.md`**. Three read-only investigations established: (1) language
      auto-detection is wired only to text-understanding + response strings, **not** ASR/TTS (`switch_language` is a TODO
      stub; `persist_language_preference` + `[nlu_analysis.languages]` are dead config) → the voice pipeline is
      **monolingual per config**; (2) the config language flag drives the text side automatically but ASR/TTS model paths
      are independent per-provider fields; (3) the WS eval runs `wants_audio=false` → TTS isn't exercised in eval (but is
      needed for real deployment). **Model finding:** sherpa-onnx (ASR) + Piper (TTS) already span all three Docker
      arches torch-free, with English models size-matched to the Russian stack — only **one new ASR asset** (armv7) is
      genuinely required; whisper is multilingual on 64-bit (config-only), and English Piper voices are a catalog
      generalization. armv7 EN ASR is a spike (zipformer-en-20M vs moonshine-tiny-en); EN Piper voice = `amy`. Eval =
      one-bulk-per-language (`LANG` axis). **Completing the design ≠ shipped:** filed implementation slices
      **I18N-2/3/4/5/6** (active ledger). Web-sourced (sherpa-onnx HF/PyPI arm32, k2-fsa Piper release, Moonshine).
- [x] **I18N-2** [ASSET] (P3) `[deferred]` — **DONE 2026-07-01.** armv7 (WB7) English ASR = offline
      **`sherpa-onnx-moonshine-tiny-en-quantized-2026-02-27`** (43 MB merged `.ort`, English-only), implemented as a
      subclass **`SherpaMoonshineASRProvider(SherpaOnnxASRProvider)`** (`irene/providers/asr/sherpa_moonshine.py`,
      entry point `sherpa_moonshine`). The subclass isolates the three axes where Moonshine diverges from the base's
      VOSK/Whisper families: **distribution** (a k2-fsa GitHub-release `.tar.bz2` → `AssetManager.download_model`
      URL+extract, not an HF model-pack), **pack shape** (merged `encoder_model.ort` + `decoder_model_merged.ort` +
      `tokens.txt`, resolved recursively), and **construction** (the merged decoder isn't exposed by
      `OfflineRecognizer.from_moonshine()`, so the recognizer is built directly from `OfflineMoonshineModelConfig(…,
      merged_decoder=…)` via the internal `_Recognizer` grabbed from the factory's globals — tracks whatever sherpa
      version is installed). Everything else inherits: offline `transcribe_audio`/`_decode` (`supports_streaming` False →
      `/ws/audio` batch branch → **dodges BUG-13**), capabilities, warm-up, build/deps meta. Swapped
      `configs/embedded-armv7-en.toml` ASR to `sherpa_moonshine` and **retired** the rejected `zipformer-en-20M` catalog
      entry in `sherpa_onnx.py` (the `zipformer-streaming` model_type stays as a generic online-transducer alias).
      **Prerequisite BUG-14 ✓** (bookworm base + `patch_onnx_align.py` + sherpa 1.12.36; Moonshine proven on the WB7,
      RTF ~0.7 / 134 MB RSS). **Validated end-to-end on x86_64** (sherpa 1.13.2): transcribes both real recorded
      fixtures cleanly (`light_unreachable`, `timer_10min`). Gates: pyright 0, config-validator ✓, suite **1113** (+3
      new Moonshine unit tests), import-linter 9/9. Design §2d. Follow-up: **I18N-8** (green English `make ws` — needs a
      bz2-capable env for the `.tar.bz2` extraction; the dev `.venv` Python lacks `libbz2`).
- [x] **I18N-3** [ASSET] (P3) `[deferred]` — **DONE 2026-07-01.** English Piper TTS voices for the two torch-free
      satellites (armv7/aarch64). Generalized the `ru_RU`-hardcoded catalog (`irene/providers/tts/piper.py`) to a
      `locale` parameter and added `en_US-amy-medium` (default) + `lessac`/`ryan` — same k2-fsa `.tar.bz2` medium packs,
      same sherpa-onnx runtime, no provider/runtime change. `get_capabilities` now reports the per-instance language
      (`ru-RU`/`en-US`) instead of a hardcoded `ru-RU` (so `piper_ruaccent`, always RU, still reports RU). Tests updated
      (descriptor set now ru∪en; new en-language capability test). Gates: pyright 0, suite 1107, import-linter 9/9.
- [x] **I18N-4** [CONFIG] (P3) `[deferred]` — **DONE 2026-07-01.** English deployment configs for all three arches +
      made the Russian configs explicitly RU-only (symmetry, user-requested). New: `configs/embedded-armv7-en.toml`
      (ASR `zipformer-en-20M`/`zipformer-streaming` per I18N-2; TTS Piper `amy`), `configs/embedded-aarch64-en.toml`
      (ASR `whisper-small` multilingual — config-only; TTS plain Piper `amy`, `piper_ruaccent` disabled),
      `configs/standalone-x86_64-en.toml` (ASR torch-whisper — config-only; TTS `silero_v3 v3_en`, `put_accent`/`put_yo`
      off; wake word already `hey_jarvis`). Each flips `default_language`/`supported_languages` + `[asr]` &
      `[asr.providers.*].default_language` to `en`, `auto_detect_language=false`, workflow `default_language="en"`, and
      the NLU keyword-matcher `default_language`. **Symmetry:** the three RU configs now set `default_language="ru"` +
      `supported_languages=["ru"]` + `auto_detect_language=false` (were implicitly bilingual via the schema default +
      auto-detect, which only ever changed the reply *string*, never ASR/TTS). `config-master.toml` untouched (the
      comprehensive `["ru","en"]` reference). No `CoreConfig` schema change (config-ui unaffected). Doc: added an
      English worked-example pointer to `docs/guides/howto-new-language.md`. Gates: config-validator ✓ (12 configs),
      suite **1110 passed** (+3 = the parametrized per-config canonical test now covers the `-en` files), pyright 0.
      Design §4.
- [x] **I18N-5** [EVAL] (P3) `[deferred]` — **DONE 2026-07-01 (bilingual eval harness; English audio recording split to
      I18N-8).** Built + validated the multilingual eval harness. Design (user-confirmed): **fixtures/traces partitioned
      by language subdirectory** (`fixtures/<lang>/`, `traces/<lang>/`) — same scenario filenames across languages so
      coverage parity is a directory diff; moved the Russian assets into `ru/`. Added an **`EVAL_LANG`** axis to
      `eval/Makefile` (default `ru`, derived from the `*-en` CONFIG name; named `EVAL_LANG` not `LANG` to avoid clobbering
      the POSIX locale var) driving the fixture/trace subdir (`{{env.EVAL_LANG}}`) + `--filter-metadata
      language=$(EVAL_LANG)` (promptfoo ANDs it with `kind=ux`), plus `EVAL_ROOM` (Кухня/Kitchen — the room name is echoed
      in the failure reply). Cases duplicated per language + tagged `metadata.language`; EN config profiles
      `profiles/configs/*-en.env`; **EN rubrics** `shared/rubrics/en-ux.yaml` (eval-commons `4ece478`, co-equal). **RU ws
      cases migrated to the co-equal rubrics** (closes the TEST-16 loop); fixed a stale `voice` config ref in
      `eval/README`. **Validated:** RU suite green under the new layout (`make ws CONFIG=embedded-armv7` = **4/4**); EN
      rubrics **7/7** live against DeepSeek. **The mic-recorded English fixtures + golden trace are tracked as I18N-8**
      (the one piece not doable headless). Design §3.
- [x] **I18N-6** [CONTENT] (P3) `[deferred]` — **DONE 2026-07-01 (audit only, no fill).** Audited `en.json` vs `ru.json`
      across all **13 handlers** three ways: (1) **structural parity** — identical method sets + parameter specs, no
      stubs, all `language="en"` (13/13); (2) **phrase coverage** — genuine idiomatic English everywhere, adequate even
      where the count is below Russian (English needs fewer variants); (3) examples/token-patterns/action-patterns
      comparable. The **only** systematic difference is **empty English lemmas** (0 in 10/13) — and that is
      **appropriate, not a gap**: the keyword matcher treats `lemmas` as *additive* keywords "if available"
      (`hybrid_keyword_matcher.py:315-317`); Russian lemmas are morphological roots (`поставить`/`таймер`) that normalize
      its heavy inflection, whereas English carries base forms in its multi-word phrases and relies on fuzzy matching
      (`threshold 0.8`) for its light inflection. Adding single-word English lemmas (`set`/`stop`/`time`) would *hurt*
      precision by over-matching common words. **Conclusion (user-confirmed):** English intent coverage is at functional
      parity with Russian; no donation changes needed. No code/asset change. Design §2.
- [x] **I18N-7** [ASSET] (P3) `[deferred]` — **DONE 2026-07-01.** Silero v3 English for the x86_64 standalone (torch TTS
      parity; Silero froze English at `v3_en`). Adjusted the existing `silero_v3` provider (not a new one) to pull
      speakers + accent + language **by model**: `_SPEAKERS_BY_MODEL` (`v3_ru` → RU set; `v3_en` → `en_0…en_117`),
      default-speaker fallback to the model's first, `put_accent`/`put_yo` default off for non-RU **and** omitted from
      `apply_tts`/`save_wav` (Russian-only semantics), `get_capabilities` language + `stress_placement` feature by model,
      assistant-name speaker map empty for non-RU, and the size-log lookup uses the selected `model_id` (was hardcoded
      `v3_ru`). **Verified with real synthesis** (torch): `v3_en.pt` = 57 MB (≈ `v4_ru` size), 119 speakers,
      `apply_tts(en_0)` produced audio cleanly. Tests added (EN speaker set / default / accent-off / capabilities). Gates:
      pyright 0, suite 1107, import-linter 9/9.
- [x] **I18N-8** [EVAL] (P3) `[deferred]` — **DONE 2026-07-01.** English eval assets — the mic-dependent tail of the
      I18N-5 harness — now recorded, and the **English suite runs green end-to-end**. `fixtures/en/{timer_10min,
      light_unreachable}.wav` (16 kHz mono PCM16) + `traces/en/timer_set_10min.json` (an **audio-input** golden captured
      from a live `embedded-armv7-en` run, so replay re-runs Moonshine ASR → a stronger regression than the ru text-golden).
      **`make ws TARGET=local CONFIG=embedded-armv7-en` = 4/4** (Moonshine ASR: WER ✓ + intent ✓ + DeepSeek-UX ✓) and
      **`make replay CONFIG=embedded-armv7-en` = 1/1** (offline, matches the oracle). **Runtime fix landed with it:** the
      base sherpa `is_available()` hardcoded the `sherpa_onnx` asset namespace, so the ASR component dropped the
      `sherpa_moonshine` subclass at boot ("not available (dependencies missing)") and `/ws/audio` rejected audio with
      `asr_required_for_audio` — now keyed on `get_provider_name()` (`sherpa_onnx.py` `is_available` + `download_model_pack`),
      with a regression test. Also confirmed the full EN stack boots clean (Moonshine ASR + Piper `amy` TTS; an earlier
      amy warm-up error was a stale pre-`_bz2` empty model dir, cleared). Gates: pyright 0, suite **1116** (+1 regression),
      import-linter 9/9. Design §3. _The stale-partial fragility this surfaced (`AssetManager` trusting a dir's mere
      existence) is now **BUG-15** (filed + fixed)._
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
- [x] **BUILD-8** [BUILD][DESIGN] (P3) `[deferred]` — **DONE 2026-07-02 (design agreed, interactive).** The
      "additional asks" arrived: organize this repo's build the way `../wb-mqtt-bridge` does. Two comparative
      maps (voice vs bridge build machinery) fed the design at `docs/design/build_release_process.md`; four
      decisions user-confirmed: **(D-2)** RU images keep unsuffixed names, EN adds `-en` (6 backend packages);
      **(D-4)** config-ui ships as a bridge-style nginx image (`wb-mqtt-voice-ui`, one multi-arch manifest) but
      is NOT deployed to the controller yet; **(D-3)** publishing stays manual — one dispatch drives the whole
      targets×languages matrix, gated on green health jobs (today's `build-images.yml` can publish from a red
      tree); **(D-5)** `ops/` deploy-by-pull with assets arriving by `git pull` + rsync (replaces the manual
      GHA-artifact download), state subtrees never touched. **User hard requirement audited (D-6): ML model
      files are NOT baked into images** (runtime stages copy only code+venv; `/app/assets` empty; models
      download at runtime) — the one deliberate exception is the profile's spaCy NLU wheel (~15–45MB, one per
      language); image bulk is dependency weight (torch on standalone). Guards specified: empty-`/app/assets`
      assertion + per-image size budgets in the publish workflow. Also: adopt `py-dev-gates@v0.1.1`, run
      `check_scope.py` in CI, keep the analyzer stage + buildx caching (voice is ahead of the bridge there).
      Stale `docker_build_review.md` annotated obsolete (pre-BUG-14 reality). Follow-ups filed: **BUILD-9**
      (ci.yml + matrix + guards + UI image) and **BUILD-10** (`ops/`), both `[release]`.
- [x] **BUILD-9** [BUILD] (P2) `[release]` — **DONE 2026-07-02.** Bridge-aligned CI/publish workflow implemented
      per `build_release_process.md` D-1…D-4/D-6/D-7. **`ci.yml`** replaces `backend-health` + `frontend-health` +
      `build-images` (all three deleted): `changes` path-filter → `ledger-guard` (`check_scope.py` now runs in CI) +
      `backend-health` (**py-dev-gates@v0.1.1** with `install-extras: all,dev` for the lint-imports/no-type-checking/
      pyright trio; NEW `uv lock --check` step keeps lockfile honesty since the gate env is pip-resolved; the voice
      gates + pytest kept) + `frontend-health`; publish jobs are dispatch-only, `needs:` green health (the
      publish-from-red-tree hole is closed). **Matrix:** a `plan` job expands `targets`/`languages` choice inputs
      (default all) into ≤6 backend builds — RU unsuffixed, EN `-en`, per-`<target>-<language>` buildx cache, tag
      triple unchanged. **D-6 guards live:** after push, the image is pulled by digest and the run FAILS if
      `/app/assets` is non-empty; size vs per-target budget (placeholders 3.5/4.5/10 GB — tighten after the first
      dispatch prints actuals to the summary). **UI image:** `config-ui/Dockerfile` (node:22 → nginx:alpine, ONE
      multi-arch manifest amd64+arm64+armv7) + nginx.conf + entrypoint writing `/runtime-config.js` from
      `API_BASE_URL`; `apiClient` default = injected base → else `http://<page-hostname>:6000` (D-4 amended at
      implementation: **no proxy** — Irene's API has no path prefix and serves permissive CORS; runtime-config
      pattern instead). The assets GHA artifact is gone (BUILD-10's git-pull sync replaces it; the guide bridges the
      gap with a manual rsync note). Docs: `build-docker.md` rewritten (7-package table, EN pulls, dispatch UX, D-6
      guarantee, UI image section). **Verified:** UI image built + smoke-run locally (runtime-config injection, SPA
      fallback, healthy 200s); config-ui `check`/`build`/`test` green (40 tests); `ci.yml` YAML-parses; the live
      expression paths validate on the first real dispatch (noted). No backend code touched.
- [x] **BUILD-10** [BUILD][OPS] (P2) `[release]` — **DONE 2026-07-02.** The `ops/` deploy story per
      `build_release_process.md` D-5 (bridge "deploy = pull, not build"): **`ops/docker-compose.yml`** (Irene on
      `:6000`, `../.assets` mount — gitignored — mem 800m/1.5 cpu with tune-at-bring-up note, log caps; the
      config-ui service behind a compose **profile** `ui` so D-4's "not on the controller" is one
      `--profile ui up` away); **`ops/update.sh`** — syncs the git-owned assets subtrees (donations/localization/
      prompts/templates/web + the two contract schemas, enumerated explicitly with `rsync --delete` per subtree)
      into the assets mount, then `compose pull && up -d && image prune -f`; runtime-owned subtrees
      (models/cache/state/traces/credentials) provably untouched — **verified with a sandbox sync test** (planted
      model + durable-action record survived); **`ops/wb-mqtt-voice.service`** systemd oneshot;
      **`ops/INSTALL.md`** (install/update/rollback/variants/recovery, bridge style — incl. the EN-image switch
      and the vYYYYMMDD-sha rollback pin). Deploy loop on the WB = `git pull && ./ops/update.sh` — the manual
      assets-artifact download is fully retired. `build-docker.md` deployment section rewritten around `ops/`
      (`user-facing-docs-are-done`). Compose YAML + script syntax validated; the on-WB7 run folds into ARCH-25
      bring-up as designed. _Closes the BUILD-8 arc: design → BUILD-9 (CI/publish, first fully green run
      `7e2c50b`) → BUILD-10 (ops)._
- [x] **BUILD-11** [BUILD][DOCKER] (P1) `[release]` — **DONE 2026-07-06. First real publish dispatch + boot
      validation.** Dispatch `28774806674` (all targets × all languages + config-ui) — every job green, first
      artifacts ever on GHCR: `wb-mqtt-voice-{standalone,aarch64,armv7}[-en]` + `wb-mqtt-voice-ui`.
      **(2)** D-6 guards fired for real on all 6 backend images (empty `/app/assets` by digest ✓, budgets ✓);
      placeholder budgets replaced with real-size-derived: **armv7 248 MB → 500 MB budget, aarch64 718 MB →
      1.5 GB, standalone 2.86 GB → 4 GB** (≈2×/1.4× headroom — a breach now means a real regression).
      **(3)** `standalone-x86_64` boot-validated locally via `ops/docker-compose.yml` + override (scratch assets
      root seeded per `update.sh`): health on :6000 in ~15 s, «который час» executed end-to-end, first-boot
      downloads landed in the mounted volume (whisper `small.pt`, microwakeword `irina` pack, silero_v4, spaCy
      cache — 357 MB+). ARM images passed the in-CI structural checks; their on-device boot is ARCH-25 (1).
      **(4)** sizes recorded in the journal. Zero defects surfaced — no BUGs filed. Observation for ARCH-25/
      REL-2: the RU image logs harmless `en_core_web_md not installed` ERRORs (spaCy en preference list in the
      config; degrades gracefully to ru).
- [x] **BUILD-12** `[release]` [FEEDBACK][CI] — **DONE 2026-07-06. `wb-user-reports` bootstrapped + the
      full loop smoke-proven live.** Repo created (sibling `../wb-user-reports`), labels, both lens files,
      triage + prune workflows, secrets (`CLAUDE_CODE_OAUTH_TOKEN`, `REPORTS_CROSS_REPO_TOKEN`), Claude App
      on all three repos, device PAT. **Live smoke:** «сообщи о проблеме» → ticket #2 + bundle committed to
      the repo → triage ran → posted analysis, flipped `fix-pr-open`, and OPENED a fix PR on wb-mqtt-voice
      (the device→ticket→triage→PR loop, all four triage actions). The smoke flushed THREE CI-config gaps in
      the authored workflow, each fixed on the reports repo (none in shipped code): `id-token: write` (Claude
      action OIDC), `GH_TOKEN` in the step env (gh write auth), and `--allowedTools` (the action's default
      tool gate denied every gh/uv/pytest call — 26 denials, the real culprit behind the silent no-ops). Loop
      safety confirmed working: the triage's own comment/label re-fires were `[bot]`-skipped. **PR #1 is a
      PROPOSAL awaiting owner review** (durable-action restart survival — plausible but triggered by
      dev-session process kills; the first item for ARCH-33's `/inbox`). Note: the design's leak-fence +
      owner-review model is what makes an auto-opened PR safe — it is reviewed, never merged by the bot.
- [x] **BUILD-15** `[release]` [BUILD][OPS] — **DONE 2026-07-08 (filed + completed same day; user-directed
      layout + gaps found while walking the ops story pre-ARCH-25). Controller deployment hardened:
      bridge-twin layout, logs mount, secrets plumbing, ownership fix, doc gaps.** (1) Checkout relocated to
      **`/mnt/data/mqtt-voice-config`** (twin of `mqtt-bridge-config`) — compose/systemd/update.sh/INSTALL.md
      all repointed. (2) **`.logs/` mount** (`/app/logs`): every runner writes `logs/irene.log` + timestamped
      rotations (`base.py` `_setup_logging`), previously accumulating unbounded in the container's writable
      layer on flash. (3) **Secrets plumbing existed nowhere**: compose now passes `DEEPSEEK_API_KEY` (LLM
      tier — QUAL-50 enabled it in deployment configs but the key could never arrive) + `IRENE_REPORTS_TOKEN`
      (problem reporting) from a documented `ops/.env` (chmod 600, gitignored; the bridge's exact pattern).
      (4) **uid mismatch fixed**: container runs `USER irene` (uid 1000) but update.sh runs as root on the
      controller — first model download would have failed EACCES at the rack; update.sh now chowns both data
      dirs. (5) INSTALL.md gains the **aarch64 variant** entry and the **satellite TLS plane** section
      (pointer to `nginx/README.md` + the `esp32_irene_upstream: 127.0.0.1:8080` wiring seam). `docker
      compose config` + `sh -n` clean; `.logs/` gitignored. Directly de-risks ARCH-25 items (LLM tier +
      reporting live at the rack; log flash-wear).
- [x] **BUILD-16** `[release]` [BUILD][OPS] — **DONE 2026-07-08 (filed + completed same day; user-directed
      from the live WB7 shell, converged in three steps to the bridge's REL-2 pattern). Two-disk deployment
      layout: SD-card clone = delivery vehicle, `/mnt/data` = the runtime tree.** Final layout: clone at
      **`/mnt/sdcard/wb-mqtt-voice`** (repo name, like the bridge's `/mnt/sdcard/wb-mqtt-bridge`); the
      container mounts ONLY **`/mnt/data/mqtt-voice-config/{assets,logs}`** (twin of `mqtt-bridge-config`);
      `update.sh` bridges the two — rsyncs the git-owned assets subtrees clone→runtime, mkdirs+chowns to
      uid 1000. Durable state needs no special mount (its `<assets_root>/state/` sits inside the runtime
      tree on `/mnt/data`); an SD card death costs only the clone + `ops/.env`. Docker data-root stays at
      the controller's existing `/mnt/data/.docker` (user-corrected; a draft had it moving to the card).
      systemd unit: `WorkingDirectory` on the card, `RequiresMountsFor=/mnt/sdcard /mnt/data`. Iterations
      same-day: dot-dirs-on-card + nested state mount → user pointed at the bridge's actual sdcard-clone +
      rsync-to-runtime split → mirrored exactly. Dead `.assets/`/`.logs/` gitignore entries removed. Amends
      BUILD-15 (same files, hours later); `docker compose config` + `sh -n` clean.
- [x] **BUILD-17** `[release]` [BUILD][OPS] — **DONE 2026-07-08 (filed + completed same day; user decision:
      "same as bridge — repo owns the config"). Config delivery: the baked-in-image TOML becomes a
      repo-delivered, read-only mount.** Found while answering "where does the TOML live?": the config was
      baked at `/app/runtime-config.toml` and config-ui saves wrote into the container's writable layer —
      silently discarded on every `update.sh` image recreate. Resolution (bridge semantics, user-chosen over
      box-owns-config): `update.sh` copies `configs/$CONFIG_PROFILE.toml` (default `embedded-armv7`;
      variants documented for aarch64/-en) → `/mnt/data/mqtt-voice-config/config/irene.toml` on EVERY
      update — repo wins, on-box edits are overwritten; compose mounts it **`:ro`** at `/app/config` and
      sets `IRENE_CONFIG_FILE=/app/config/irene.toml` (the image CMD doesn't pin `-c`, so the env override
      lands cleanly; the baked TOML remains as the image's standalone fallback). config-ui on the controller
      is thereby a browser/validator — its save fails loudly on the ro mount instead of silently vanishing
      (documented in INSTALL.md). Cross-project build/install/rules harmonization filed as **BUILD-18**
      `[deferred]` (next release).
- [x] **BUILD-19** `[release]` [BUILD][OPS] — **DONE 2026-07-08 (filed + completed same day; the bridge's
      live reboot failure, relayed cross-repo — voice had the identical time bomb, caught BEFORE first
      deploy). Boot must not depend on the SD card.** The bridge's reboot test failed because its unit was
      rooted on the lazily-automounted card (`RequiresMountsFor=/mnt/sdcard` forced the card's mount +
      `systemd-fsck` into the early boot transaction before the device enumerated; `Type=oneshot` never
      retries) — and our unit had the exact pre-fix shape, built this morning by mirroring their layout
      hours before their lesson. Fix (their `e88aa84` rule, adapted): **the clone is an update-time
      artifact; everything boot needs lives in the runtime tree.** `update.sh` now DEPLOYS
      `docker-compose.yml` into `/mnt/data/mqtt-voice-config/` and runs all compose commands from there;
      the unit is `WorkingDirectory=/mnt/data/mqtt-voice-config` + `RequiresMountsFor=/mnt/data` only;
      `.env` moves to the runtime tree (next to the deployed compose, so both start paths see identical
      env); the unit is **copied** to `/etc/systemd/system`, not symlinked (a symlink onto the unmounted
      card is unreadable to systemd at boot — our own INSTALL had `ln -s`).
      The compose project-name migration gotcha is moot for voice (nothing deployed yet — the fix landed
      between image publish and first install). The nginx `:80`-vs-WB-admin-UI conflict filed as
      **ARCH-41** `[deferred]`. `sh -n` + `docker compose config` clean. _Same-day correction (user): the
      **`ui` service was removed from the controller compose entirely** — config-ui is NOT deployed on the
      controller (a 3001 port remap from the first pass lived for minutes); with repo-owns-config
      (BUILD-17) the editor runs on a workstation when wanted (`build-docker.md` "The configuration
      editor" — whose two stale port-6000 refs from before BUG-29 were fixed in the same change)._
- [x] **BUILD-20** `[deferred]` [BUILD][OPS][PROCESS] — **DONE 2026-07-08 (filed + completed same day;
      joint productization design session, run from `~/development` acting as both repos' Claude).** The
      cross-project productization design: product name **Domovoy** (pending availability sweep), ONE
      umbrella = eval-commons renamed `domovoy-commons` (three ownership regimes: product-owned contract
      pins / co-owned shared code / process+product artifacts, per-package prefixed tags), PROD-board
      cross-repo idea discipline with board-as-outbox (retires uncommitted sibling filings),
      `domovoy-satellite` as a third product repo (ESP32 estate relocates; the outdated top-level `ESP32/`
      tree deleted, not migrated), rule-of-two shared-code extractions (dynamic loader + logging first),
      config UI = two apps + shared kit (one-shell-with-plugins stays reachable), ledgers KEPT over
      GitHub Projects/Jira, per-component semver + calver suite compatibility manifests, contract
      tagging + scripted re-pin + staleness gate, normative ops spec + shared CLAUDE.md invariant blocks
      with drift guard, landing page in `commons/site/`, problem-report policy spec unified. Deliverable:
      `docs/design/productization.md` (D-1..D-12 + drift inventory + commons seed backlog) + sibling
      `../wb-mqtt-bridge/docs/design/productization_bridge.md` (uncommitted, intake). Follow-ups filed:
      BUILD-21/22/23/24, ARCH-42/43, BUILD-18 narrowed; bridge intake VWB-29, CORE-7, OPS-14/15/16.
- [x] **BUILD-21** `[deferred]` [COMMONS][PROCESS] — **DONE 2026-07-11. Commons bootstrap: name lock + rename +
      restructure + re-point** (BUILD-20 D-1/D-2/D-3). (1) Sweep ran 2026-07-08 under "Domovoy"; owner
      superseded and LOCKED **Locveil** 2026-07-11 (`locveil.com`/`.ru` registered, GitHub org `locveil`
      claimed; record: `../locveil-commons/docs/design/locveil_domain_registration.md`). (2) OWNER: all three
      repos transferred+renamed under the org (`locveil/locveil-{commons,voice,bridge}`, redirects live) +
      local dir renames. (3)+(4) Commons side landed as `locveil-commons@52126da`: D-2 layout (eval framework →
      `eval/`, distribution `locveil-eval`, import package unchanged `eval_commons`), PROD board
      (`board/BOARD.md` PROD-1..11 from the seed backlog) + `board/JOURNAL.md` + umbrella CLAUDE.md/README,
      decision record migrated (pointer left at `docs/design/productization.md` here). (5) Voice re-point
      (this change): eval/ refs → `../../locveil-commons/eval` (contracts at `../../locveil-commons/contracts`),
      name sweep of operative docs/comments (history — journal/DONE/archives/reviews/CHANGELOG — and live
      deployment identifiers untouched → BUILD-29), `domovoy`→`locveil` container user in the three backend
      Dockerfiles (uid 1000 unchanged; takes effect at next image publish), GHCR namespace cutover in pull
      refs/docs to `ghcr.io/locveil/*` (CI already publishes via `github.repository_owner`; **owner must run
      one CI publish before the next controller `update.sh`**, old `ghcr.io/droman42/*` images stay pullable),
      `.venv` rebuilt (dir rename had broken every console-script shebang) + sqlite shim re-run. Gates:
      `make cli` 5/5, `make device-auto` tier-1 48/48, touched-file pytest 83/83. Bridge-side re-point arrives
      via the commons board (PROD-2 — the first board-as-outbox delegation, D-5).
- [x] **BUILD-25** [UI][SEC] `[release]` — **DONE 2026-07-09.** config-ui image ran as root: the runtime stage
      was a bare `FROM nginx:alpine` with no `USER`, the posture the backend images deliberately reject. Not
      deployed on the controller, but published to GHCR and run on workstations against the assistant's API.
      Now `USER nginx` (uid 101) with `/usr/share/nginx/html`, `/var/cache/nginx` and a pre-created
      `/var/run/nginx.pid` chowned to it (that directory stays root-owned), and the base image's `user`
      directive stripped — meaningless without uid 0 and it warned on every start. Nothing needed uid 0: nginx
      binds 3000 and the entrypoint writes only inside the html root. Verified by building + running: uid 101,
      `/docker-entrypoint.d/40-runtime-config.sh` still executes (the official entrypoint's behaviour does
      change for uid≠0, so this was the risk — `runtime-config.js` is written, with and without `API_BASE_URL`),
      SPA + fallback + no-store config all serve 200, zero warnings.
      **Found while verifying: the healthcheck could never have passed.** It probed
      `http://localhost:3000/`, but `listen 3000` binds IPv4 only while musl resolves `localhost` to `::1`
      first and busybox wget does not fall back — `wget` inside the container returned *connection refused*
      against a server answering fine from outside. Every published config-ui container was destined to sit
      `unhealthy` forever (latent since BUILD-9; the bridge's UI dodged it with `127.0.0.1`). Now `127.0.0.1`,
      and Docker reports **healthy**. Also fixed the file's two stale comments: the `:6000` API fallback (8080
      since BUG-29) and "the ops/ compose ships it disabled" (the service was removed outright).
- [x] **BUILD-27** [OPS][MQTT] `[release]` — **DONE 2026-07-09.** The voice container joins the host network and
      bridge actuation is on. `[outputs.bridge] enabled = false` in every embedded profile meant the device
      catalog was never fetched (zero bridge lines in the WB7 log), and flipping it alone would have failed:
      under our `ports:` mapping `base_url = "http://localhost:8000"` resolved to the *container* —
      `127.0.0.1:8000` → connection refused from inside it, gateway `172.17.0.1:8000` → HTTP 200. The bridge's
      own compose already used `network_mode: host` (it must, to reach WB's mosquitto on `localhost:1883`); ours
      was the odd one out. Voice now shares the host network too, so the shipped `localhost:8000` is true as
      written, the `ports:` mapping is dropped (the runner binds `0.0.0.0:8080`, so Plane B's
      `esp32_irene_upstream: 127.0.0.1:8080` is unaffected), and the two products stop networking differently.
      Enabled in the four embedded profiles; standalone stays off. **Verified on the WB7 after redeploy:**
      `NetworkMode: host`, `✅ Bridge output registered + designated for DEVICE_COMMAND`,
      `device catalog refreshed: version (none) -> 8159b4b0068d1c63, 79 devices / 11 rooms` — the same
      `catalog_version` pinned in `eval-commons/contracts/PIN.json`, so voice, bridge and the test contract agree
      on the device model. Then the **first real end-to-end command on hardware**: «включи свет в кабинете» →
      `smart_home.power_on` (hybrid_keyword_matcher, 0.76) → catalog resolves «кабинет» to `cabinet_spots` →
      canonical `DeviceCommand` → bridge → relay → **the light physically turned on** (retained
      `/devices/wb-mr6c_51/controls/K4` = `1`). Text in, photons out. Follow-ups filed: **BUILD-28** `[deferred]`
      (one compose, real startup order — bound for the commons PROD board) and bridge **DRV-23** (its believed
      `power` never tracks the state topic, so the opposite command idempotence-skips).
- [x] **BUILD-29** [OPS][BUILD] `[deferred]` — **DONE 2026-07-11 (repo side; controller migration = owner
      script run). Deployment-identity rename to Locveil** (BUILD-21 residue; coordinated with bridge OPS-21,
      same session). Everything renamed in one pass: image basenames → `locveil-voice-{armv7,aarch64,
      standalone}[-en]` + `locveil-voice-ui` (ci.yml matrix + build-docker.md), `container_name:
      locveil-voice`, runtime tree `/mnt/data/mqtt-voice-config` → `/mnt/data/locveil-voice-config`
      (compose volumes, update.sh RUNTIME_DIR, INSTALL.md layout), systemd unit `ops/wb-mqtt-voice.service`
      → `ops/locveil-voice.service` (git mv + content), clone path `/mnt/sdcard/locveil-voice` + clone URL,
      and the two API-visible `Field(description=…)` strings (`irene/config/models.py` → "locveil-bridge")
      with the full generated-contract chain per `config-ui-stays-functional`: `dump_openapi.py` regen
      (7-line delta — the BUILD-26 241-line drift was already regenerated at REL-4), `gen:api-types`,
      `npm run check` + `build` green. **NEW `ops/migrate-to-locveil.sh`**: one-time controller migration
      (retire old unit → down old stack from old tree → mv runtime tree with models/state/.env intact →
      `update.sh` under the new identity → install+enable new unit → drop old-name images); `sh -n` +
      `docker compose config` clean. Gates: pytest 1379 passed / 1 pre-existing order-dependent flake
      (reproduced on the pre-change tree, filed BUG-42), `make cli` 5/5, check_scope green. Sequencing:
      CI publish must create + owner must make PUBLIC the new GHCR packages before the migration script
      runs on the WB7.
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
- [x] **ASSET-4** [VAD][ASSET] (P2) `[release]` — **DONE 2026-07-04. Silero VAD model download moved into the
      AssetManager; engine never downloads.** (Chat-surfaced VAD review 2026-07-04; findings were inline in this
      entry — no review doc.) Was: `SileroVADEngine._ensure()` ran a raw synchronous `urllib.request.urlretrieve`
      on the **first audio frame** — no temp+rename/partial healing (a truncated `silero_vad.onnx` passed the
      `size > 0` guard forever), blocked the event loop with no timeout, retried the blocking download every
      frame on failure while VAD silently reported silence, and the `"vad"` pseudo-provider fell to AssetManager's
      generic-defaults fallback (WARNING at startup; `silero` collides with silero **TTS** in
      `provider_namespace_map`). Fix: asset identity **`silero_vad`** → `('irene.providers.vad', 'silero')` tuple
      mapping in `provider_namespace_map` (+ `irene.providers.vad` in the search namespaces);
      `SileroVADProvider` declares `_get_default_model_urls/_directory/_extension` (on-disk path unchanged:
      `models/vad/silero_vad.onnx`) and downloads in async `_do_initialize` via
      `AssetManager.download_model(..., url_override=)` (new param — TOML `model_url` override rides the robust
      path); new `VoiceSegmenter.initialize()` warmup seam (called from the workflow's async init) **falls back
      to `energy`** if the configured provider can't come up; engine raises loud `FileNotFoundError` if the model
      is missing. Stale docstrings fixed (`utils/vad.py` port, `vad_silero.py`); `docs/guides/vad.md` updated;
      dead `create_audio_processor`/`process_audio_with_vad` deleted. microVAD needs no asset work — model is
      compiled into the `pymicro-vad` wheel (`micro_vad_cpp.abi3.so`); energy has no model. Tests:
      `test_vad_assets.py` (10). Verified live: real GitHub download through AssetManager + dead-URL → energy
      fallback.
- [x] **ASSET-5** [WAKE][ASSET] (P2) `[release]` — **DONE 2026-07-04. Wake-word packs through the AssetManager**
      (implements ARCH-29 / `docs/design/wakeword_models.md`; first RU model «Ирина» consumed from HF —
      the wakeword-training factory's first handoff). AssetManager: multi-file model support (`files:
      {filename: url}` catalog entries → `_download_files_pack`, staging dir + atomic rename, existing
      lock/populated-check/healing) + `download_model_files()` for ad-hoc packs. MicroWakeWordProvider:
      4-rung `_build_detector` (local manifest / wheel built-ins / v2 manifest URL with sibling-`.tflite`
      derivation / released catalog `{irina: HF droman42/microwakeword-irina-ru}`), `_get_default_extension`
      → `""` (directory packs `models/microwakeword/<word>/`), catalog advertised in
      `get_supported_wake_words`; catalog-fetch failures log WARNING (unknown words stay debug). Configs:
      `standalone-x86_64` → microwakeword/«Ирина» (0.97), `standalone-x86_64-en` → microwakeword/Alexa (0.9);
      config-master example block. Docs: `voice-trigger.md` rewritten (model sourcing + RU words section),
      «Борис»→«Валера»/«Наташа» roster fix in `esp32.md` + `esp32-fit.dot` (png regenerated). Tests:
      `test_wakeword_assets.py` (11, hermetic — fake pmw + patched fetch). **Verified live:** irina pack
      downloaded from HF via AssetManager (60,968-byte tflite), real pymicro-wakeword detectors: silence
      negative, **16/16 synthetic + 6/6 real household «Ирина» recordings detected @0.97** (initial 0/16 was
      a harness artifact — clips ending exactly at the word need trailing audio to flush the sliding window;
      mic streams always have it).
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
- [x] **DOC-6** (P2) — Archived stale historical-plan docs (`config_schemas`, `language_support`,
      `configuration_guide`, `PIPELINE_IMPLEMENTATION`, `irene_current`) → `docs/archive/`.
- [x] **DOC-7** [PEX] (P1) — DONE 2026-06-08: the parameter-extraction reference is covered across the new
      canonical set rather than one file — `guides/DONATION_FILE_SPECIFICATION.md` (the `ParameterSpec` schema +
      the ParameterType and entity_type enums), `architecture/intents.md` (extraction patterns, `get_param`,
      handler consumption of `intent.entities`), and `architecture/nlu.md` (token/slot pattern format). Closed as
      covered; the standalone `PARAMETER_EXTRACTION_GUIDE.md` was not needed.
- [x] **DOC-8** (P1) `[release]` — **DONE 2026-07-06. Data & context-models map — shipped as
      `docs/architecture/data-models.md`** (placement + naming adjusted with the user: the architecture
      family — created after this task was filed — is the natural home; lowercase user-facing name, family
      prose voice, house-style diagram `docs/images/data-models.dot/png`). The page answers the task's key
      confusion (request- vs session-scoped) with the **three-lifetimes frame**: dies-with-the-request
      (`RequestContext` = routing+identity never memory; `Intent` deliberately session-blind, `raw_text`
      literal; `IntentResult` failure-must-carry-reason; `AudioData`/`WakeWordResult`), lives-with-the-session
      (`UnifiedConversationContext` — a session is a ROOM, not a person; windowed history single-writer,
      pending clarification, ~30 min expiry; narrow hydration bridge, single minting path), survives-restarts
      (client registry, physical identity — the timer-knows-its-room story). Content verified against
      TODAY'S code (post QUAL-27/28/36, BUG-4, ARCH-27/28), NOT transcribed from the defect-era QUAL-25
      snapshot. Linked from README's architecture list + cross-linked from `dataflow.md`.
- [x] **DOC-9** [EVAL] (P2) `[release]` — **DONE 2026-06-27.** User-facing guide for the eval harness:
      `docs/guides/howto-new-test.md` (matches the `howto-*` recipe voice + a decision diagram
      `docs/images/howto-test.{dot,png}`). Walks through the three surfaces (CLI contract, WS system, WS UX-judged),
      authoring a case in each, recording the audio fixture (`make record`), and keeping cases endpoint-agnostic
      (TARGET/CONFIG). **Wired into the howto index** like its siblings: listed in `CONTRIBUTING.md` ("Add a test",
      beside add-an-intent/model/language) and the top-level `README` pointer; also cross-linked from `eval/README.md`
      (reference ⟷ walkthrough). No internal tracking language in the prose (user-facing-docs voice). Complements the
      existing `eval/README.md` + `fixtures/README.md` rather than duplicating them.
- [x] **DOC-10** `[release]` [EVAL] — **DONE 2026-07-07 (filed + completed same day, user request). The
      WebSocket protocol document is now an INVARIANT, both sides of the sibling boundary.** New CLAUDE.md
      invariant **`ws-protocol-doc-canonical`**: `docs/guides/websocket-api.md` is the single source of
      truth for the WS wire protocol (hand-written reference, deliberately not generated tooling); any WS
      endpoint/message-shape change updates it in the same change; design docs defer to it
      (`python_satellite.md` §3's "single written truth" claim re-pointed accordingly). Sibling seed:
      `../eval-commons/CLAUDE.md` CREATED (the repo had none) naming that document as the protocol truth
      its `ws_audio_provider` implements — plus the standing contracts-pin rule (never hand-edit, owned by
      voice's re-pin flow) and the execution-logic-lives-here framing, so both repos run the discipline.
