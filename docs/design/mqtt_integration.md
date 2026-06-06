# Smart-home integration design (ARCH-7 / ARCH-8)

**Status:** design session, drafted 2026-06-06. Decisions locked with the user; the cross-project
**bridge contract is a draft** pending the wb-mqtt-bridge session (see
[`voice_integration_contract_draft.md`](../../../wb-mqtt-bridge/docs/voice_integration_contract_draft.md)
in the sister repo). Implementation = **ARCH-8**, sliced in §10.

> Supersedes `docs/archive/intent_mqtt.md` (the v13-era "MQTT intent handler with runtime method
> generation" design — explicitly rejected, see §2).

---

## 1. The decision in one line

**Irene does not own smart-home device knowledge or MQTT conventions.** The sister project
**`wb-mqtt-bridge` is the single device authority**; Irene is a pure voice front-end that (a) pulls a
device/room/capability **catalog** from the bridge on startup and (b) sends **canonical device
commands** to the bridge, which translates them to native commands and the right MQTT/transport
convention. Irene speaks one small canonical vocabulary end-to-end and is blind to wb-rules vs Home
Assistant vs anything else.

```
  utterance ──▶ Irene (NLU + resolution) ──canonical DeviceCommand──▶ wb-mqtt-bridge ──▶ {native WB | AV | HA later}
                     ▲                                                      │
                     └────────────── catalog pull (devices/rooms/caps) ◀────┘
```

## 2. Why — and what this rejects

The real deployment is one Wirenboard 7 controller that is **both the MQTT broker and the home**.
Everything lives on its broker under the WB convention `/devices/{dev}/controls/{ctrl}`:

- **Native WB gear** (managed by `wb-mqtt-serial` + `wb-rules`, *not* in wb-mqtt-bridge today): lights
  & dimmers (`wb-mr6c`, `wb-mdm3`, `wb-mrgbw-d`), curtains (`dooya`), HVAC, per-room multi-sensors
  (`wb-msw-v3`), metering, leak. Control names are hardware-technical; there is no device-type
  taxonomy, capability model, or room mapping in the raw topic tree.
- **wb-mqtt-bridge's virtual devices** (AV gear with no native WB support): TVs, Apple TVs, eMotiva —
  published onto the *same* broker, but *with* rich capability maps + param schemas + rooms.

Two rejected alternatives:

- **Irene → raw broker directly.** Irene would re-implement the device/capability/room model
  wb-mqtt-bridge already has, only for the native half, against a semantically poor topic tree, with a
  large hand-authored overlay. Two fidelity levels, duplicated modeling, Irene shaped to one vendor.
- **The archived `intent_mqtt.md` design** (fat `MQTTDynamicHandler` owning an MQTT client + HA
  discovery + **runtime Python method generation** inside an intent handler). This fuses domain +
  transport + a discovery subsystem into a vertical silo — the opposite of the hexagon, and the
  QUAL-era "generate it at runtime" anti-pattern. Dropped entirely.

The chosen split puts device knowledge and convention-handling in the project **built** for it
(wb-mqtt-bridge is a hexagonal device-control bridge with capability maps), and keeps Irene a thin,
convention-agnostic voice layer. The agnosticism boundary moves to the correct place: **the bridge
owns conventions; Irene owns voice.**

## 3. Two output flows (the seam, named)

MQTT/the bridge surfaces in two architecturally different places. Naming them keeps the design honest:

- **Flow 2 — actuation (primary).** "Включи свет в гостиной." The intent *is* device control. The
  domain resolves it to a canonical `DeviceCommand`; an `ActuationPort` carries it; the bridge-client
  adapter POSTs it to the bridge; the bridge translates + actuates. This is the WB7 use case and the
  substrate **QUAL-35** (T2/T3 device NLU) builds on. **Goes via the bridge over REST**, not raw MQTT.
- **Flow 1 — content-agnostic output (secondary, deferred).** Ship an `IntentResult` to a non-audio
  sink (announce a response, publish "timer fired" as an event). The exact analog of
  `_handle_tts_output` — workflow-driven, parallel to TTS, domain-unaware. Defined here for
  completeness; **low priority, no confirmed consumer yet**, raw-MQTT (not the bridge). See §7.

These are **separate seams with separate adapters** — do not fuse them.

## 4. Hexagonal placement (Irene side)

```
DOMAIN        device IntentHandler ──resolves utterance──▶ DeviceCommand (canonical, convention-blind)
  │                  │ depends on (ABC, intents/ports.py — the QUAL-24 pattern)
PORTS         ActuationPort          DeviceCatalogPort                 OutputPort (Flow 1)
  │                  │ implemented inward by (application components import nothing outward)
APPLICATION   ActuationService ─────────┐         CatalogService
  │                                      │ holds                  │ holds
ADAPTERS      providers/outputs/bridge:  BridgeClient (REST)      └─ providers/outputs/mqtt (Flow 1)
                   ├─ GET  catalog/rooms/capabilities  (startup pull → DeviceCatalog)
                   └─ POST canonical action            (Flow 2 actuation)
```

- **`DeviceCommand`** (new domain type, `irene/intents/`): `room_or_device_ref`, `capability`,
  `action`, `params: dict`. No topic, no broker, no native command name. This is the
  "domain-typed command, never a topic" boundary.
- **`ActuationPort`** / **`DeviceCatalogPort`** (ABCs in `intents/ports.py`): the QUAL-24 pattern —
  device handlers depend only on these; the application `ActuationService`/`CatalogService` inherit
  them and inject inward (components import nothing → no new edges; enforced by the import-linter).
- **`BridgeClient`** adapter under a new `irene.providers.outputs` entry-point group: owns the HTTP
  client, base URL/auth, retries, and the REST contract with the bridge. The **only** module that
  knows the bridge exists.
- **DeviceCatalog** (in-memory, built from the startup pull): the device/room/capability/param model
  the NLU and `DeviceEntityResolver` consume — this is what turns today's all-`generic` `entity_type`
  into real `device`/`room` entries (the ARCH-6/QUAL-35 device-half substrate).

`DeviceCatalog` is **not** `ClientRegistry`. ClientRegistry = what's physically wired to a given ESP32
satellite (room context for *a microphone*). DeviceCatalog = everything actuable in the house. They
intersect on **room** (both carry room names) but serve different jobs; the catalog references rooms
the bridge defines.

## 5. The Irene ↔ bridge contract

Two halves. **Transport = REST both ways** (synchronous `CommandResponse` gives Irene a result to
*speak* — "готово" / "не получилось"; raw MQTT can't correlate a response). Optional MQTT
**state**-subscribe for "is the light on?" queries is a later nice-to-have, not in v1.

### 5a. Read — catalog pull (startup, must-have)

On boot Irene pulls and builds the DeviceCatalog:

| Irene needs | Bridge surface (today, confirmed) |
|---|---|
| device + room + scenario lists | `GET /system` |
| rooms with **ru names** + device membership | `GET /room/list`, `GET /room/{id}` → `{room_id, names:{ru,en,de}, devices:[…]}` |
| per-device **capabilities** + param schemas (canonical view) | the Layer-3 capability/layout manifest (`GET /devices/{id}/layout`) — see bridge draft §B |

Since actuation is **canonical**, the read side reads the **capability** view (not raw native command
names) so read and write vocabularies match: Irene learns *"living_room_tv, in Гостиная, supports
`volume`(0–100), `power`, `input`(hdmi1/hdmi2…)"* and speaks `volume.set` back. One vocabulary.

**Refresh:** startup-pull is the must-have. For live changes the bridge already has `POST /reload`
and could publish an MQTT nudge (e.g. `irene/catalog/dirty`) that Irene subscribes to → re-pull.
Optional.

### 5b. Write — canonical actuation (must-have, **needs a new bridge endpoint**)

The gap: the bridge's action endpoint (`POST /devices/{id}/action {action, params}`) takes **native**
command names; its capability map (canonical→native) is **internal-only** (UI/scenario rendering).
To let Irene speak canonical, the bridge must expose its existing internal translation on the input
path — a small addition wrapping the capability reconciler. Proposed shape (bridge session decides):

```
POST /devices/{device_id}/capability/{capability}/{action}
  body: { params: { level: 50 } }
  ->   { success, device_id, capability, action, state, error }
```

Irene's `BridgeClient.actuate(DeviceCommand)` POSTs this and maps the response to a spoken result.
**Full spec of the ask is in the bridge draft** (sister repo) — this doc records only the Irene-side
expectation.

## 6. Resolution flow (utterance → DeviceCommand)

```
ASR text ──▶ NLU (QUAL-35 T2/T3) ──▶ intent: device-control
                                       entities: device/room ref, capability, action, value
        ──▶ DeviceEntityResolver (against DeviceCatalog + room list)
                 ├─ resolve room  ("в гостиной" → room_id via ru names)
                 ├─ resolve device ("телевизор" → device in that room)
                 └─ resolve capability+action ("сделай громче" → volume.up)
        ──▶ validate/clarify params against the catalog schema (QUAL-30 / QUAL-31)
                 ("какую яркость?" when range param missing/out of bounds)
        ──▶ DeviceCommand ──ActuationPort──▶ BridgeClient ──▶ bridge ──▶ speak CommandResponse
```

- **NLU (QUAL-35):** today's T1 NLU can't carry device+room+capability+value. The T2/T3 tiers are the
  paired prerequisite — ARCH-7/8 define the seams; QUAL-35 authors the device handlers + NLU on top.
- **Entity resolution:** the DeviceCatalog populates real `device`/`room`/`location` entities, so the
  `entity_type`-driven resolver swap (relocated from ARCH-6, owned with QUAL-35) finally has substrate
  instead of being an inert branch.
- **Clarification/slot-filling:** the per-param schema from the catalog is exactly what QUAL-30
  (deterministic single-turn) and QUAL-31 (multi-turn slot-filling) need to ask "какую яркость?" and
  validate the answer before publish.

## 7. Flow 1 — content-agnostic output (deferred)

A thin `OutputPort` called by the workflow beside `_handle_tts_output`, fanning an `IntentResult` to
enabled non-audio sinks (a raw-MQTT `providers/outputs/mqtt` adapter publishing e.g.
`irene/{room}/event`). Domain-unaware; gated by config like `wants_audio`. **Deferred** — no confirmed
consumer yet; defined so the output seam is complete and Flow 2 isn't mistaken for it. If/when a
consumer appears (an event bus, an announcement speaker), it lands as its own small slice.

## 8. Config + entry-points

- New entry-point group `irene.providers.outputs` (`bridge` for Flow 2; `mqtt` for Flow 1 later).
- `OutputConfig` / `ActuationConfig` in `config/models.py` (bridge base URL, auth, timeouts,
  `enabled`, default sink) + a registered schema in `config/schemas.py` + `auto_registry.py`
  (Invariant #4 — the same schema seam ARCH-10 hit). Surfaced in `config-master.toml`.
- No new heavy deps for Flow 2 (an async HTTP client; `aiohttp` is already in core). Flow 1's raw-MQTT
  adapter would add an MQTT client lib when built.

## 9. Failure modes (fail-loud, not fail-fatal)

- **Bridge down at boot:** empty DeviceCatalog. Device commands clarify-or-fail gracefully (QUAL-30);
  the rest of the assistant is unaffected. Never block startup on the bridge.
- **Bridge down at actuation:** `ActuationService` returns a failed result with a spoken apology; no
  crash. The QUAL-27 data-contract rule (a failed result carries a reason) applies.
- **Unknown device/room/capability:** resolution fails → clarification ("какое устройство?"), not a
  silent no-op.

## 10. PR slicing (ARCH-8 implementation)

Gated on the bridge session landing the contract (§5b) and at least a thin slice of native-device
onboarding in the bridge.

- **PR-1** — `DeviceCommand` domain type + `ActuationPort`/`DeviceCatalogPort` (ABCs) + the
  application services; import-linter clean. No adapter yet (unit-tested against a fake).
- **PR-2** — `BridgeClient` adapter (REST) + `irene.providers.outputs` group + config/schema +
  startup catalog pull → DeviceCatalog. Validated against a recorded bridge response / live bridge.
- **PR-3** — wire DeviceCatalog into `DeviceEntityResolver` (real `device`/`room` entities) — the
  ARCH-6 device-half activation, done with QUAL-35.
- **PR-4** — one reference device intent handler end-to-end (utterance → DeviceCommand → bridge →
  spoken result), proving the seam. Broad device coverage + T2/T3 NLU = QUAL-35.
- **(later)** — Flow 1 OutputPort + raw-MQTT adapter, if/when a consumer appears.

## 11. Open questions for the bridge session

Carried in the bridge draft; mirrored here so ARCH-8 knows its dependencies:

1. **Canonical action endpoint** — exact path/shape; reuse of the internal capability reconciler;
   error semantics suitable for spoken feedback.
2. **Catalog read surface** — does the existing Layer-3 layout manifest expose enough
   (capability + param schema + ru labels) for voice, or is a dedicated `/voice/catalog` endpoint
   cleaner? Optional MQTT catalog-dirty nudge.
3. **Native-device onboarding** — a generic WB-passthrough driver for relays/dimmers/curtains/HVAC
   (the existing `WirenboardIRDevice` is IR-blaster-specific); room assignment in `rooms.json`;
   capability maps for the new device classes. This is the bulk of the effort and is bridge-side.
4. **Room model parity** — confirm `rooms.json` ru names are the resolution key Irene matches on.

## 12. Cross-project tracking

- **Irene side:** ARCH-7 (this design) → ARCH-8 (implement, §10) + QUAL-35 (device NLU + handlers).
- **Bridge side:** tracked in `wb-mqtt-bridge/docs/action_plan.md`; the requirements are drafted in
  `wb-mqtt-bridge/docs/voice_integration_contract_draft.md` for the bridge session. ARCH-8 is blocked
  on that work.
