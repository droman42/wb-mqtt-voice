# Input / Output architecture (ARCH-14 / ARCH-15)

**Status:** design DRAFT 2026-06-07 (design session with user, consolidated from a 5-point brief).
Supersedes the aspirational `docs/architecture.md` §5.1–5.2 ("Inputs → InputManager → Command Queue →
Workflow" + "OutputManager") which is v13-era and was never built. Sits on top of the already-DECIDED
session/identity model (`dataflow_reconciliation.md` Q2/Q3, implemented in QUAL-28) and the WS
driving-adapter (ARCH-6). Co-designed with the smart-home output seams of ARCH-7
(`mqtt_integration.md` §3 — Flow 1 / Flow 2).

> **Why this exists.** A trivial CLI bug — `irene.runners.cli` interactive mode silently swallows typed
> lines — turned out to be the visible tip of a structural gap: input consumption is ad-hoc per-runner,
> there is **no output abstraction at all** (`irene/outputs/` does not exist; async/F&F output hard-wires
> the one global TTS/audio sink), and the system assumes exactly one input + one output (hence one runner
> per channel). This document defines the target I/O architecture; the CLI bug is its first implementation
> slice and becomes structurally impossible under it.

---

## 1. The decision in one line

**Input and output are symmetric, configurable, hexagonal adapter sets, multiplexed by one daemon and
routed by physical identity.** A single process hosts many concurrent **input** adapters and many
concurrent **output** adapters; every utterance carries a *format* (which selects the workflow entry
stage) and an *origin identity* (which selects where results are delivered). Runners stop implementing
channels and become thin config-preset launchers.

```
 capture          format          ┌───────────────┐   result          delivery
 mechanism   ─▶  (entry stage) ─▶ │   workflow    │ ─▶ (modality) ─▶  adapter
 (Input)                          └───────────────┘                   (Output)
   console/mic/web/ws/...    after-ASR / at-ASR / ...        console/audio/web/ws/mqtt/...
        │                                                              ▲
        └───────────── origin identity (resolve_physical_id) ──────────┘
                         + event bus: delivery subscriber │ observer subscribers
```

---

## 2. Two axes: **format** vs **input** (Point 1)

These are orthogonal and must be modelled separately (today they are conflated in per-runner skip-flags).

- **Format** = *the what*. Prescribes the **workflow entry point**: `audio` enters at voice-trigger/ASR,
  `text` enters *after* ASR, etc. This is the pipeline-stage selector.
- **Input** = *the how*. The **capture mechanism**: console (stdin), microphone, web app (web runner),
  WebSocket, file, … Pure transport.

**Relationship is many-to-many:** the same *format* arrives over different *inputs* (`text` from console
*or* a web textbox *or* a WS text frame; `audio` from a local mic *or* a WS binary stream).

**Today:** format is *implicitly* encoded by `RequestContext` flags hand-set per runner — `skip_asr`
(text path, `workflow_manager.py:453`), `skip_wake_word` (`webapi_router.py:814`), `wants_audio`.
**Target:** format becomes a **first-class value** (`InputFormat` enum `{VOICE, AUDIO, TEXT}`), and the
workflow derives the entry stage from it.

> **Reconciliation (PR-1, done):** the brief said `InputData.format`, but `InputData` is a *type alias*
> `Union[str, AudioData]` (`core/interfaces/input.py:23`) — it can't carry a field. The live entry path is
> `RequestContext`-based, and `(skip_wake_word, skip_asr)` already *was* the de-facto format encoding. So
> `InputFormat` landed on **`RequestContext.input_format`** as the single source of truth (the legacy flags
> are now its derived projection — a clean bijection: VOICE=(F,F), AUDIO=(T,F), TEXT=(T,T)).
> `configure_pipeline_stages` selects the entry stage from `input_format`. The daemon path (**PR-5**) will
> stamp `format` on the input *envelope* the adapter yields; until then it's set at the workflow entry
> methods (`process_text_input` → TEXT; audio entries infer from the wake-word distinction).

---

## 3. Output as the symmetric twin (Point 2)

Output is the missing half of the hexagon (`irene/core/interfaces/input.py` exists; there is no
`output.py`; there is no `irene/outputs/`). It is built as the mirror of input:

- **Configurable via TOML.** An `[outputs]` section declares which output adapters are enabled (mirroring
  how `[inputs]` / components / providers are configured). This is net-new config surface (→ config-ui, §9).
- **The output adapter drives the delivery format.** The workflow produces a **format-neutral**
  `IntentResult`; it hands the result to a configured **OutputPort**; the *output* decides how to render
  it (console text, TTS-synthesize-and-play, WS frame, MQTT publish). Clean seam: the workflow never
  knows the wire format.
- **Channel pairing.** console-out delivers where console-in happened; web-out where web-in happened;
  ws-out over the originating ws connection. The pairing key is the **origin identity** (§6).
- **Modality / capability matrix.** A result has a **modality** (`text`, `audio/speech`, `device_command`,
  structured `event`). Each output **declares which modalities it can carry**. Not every result fits every
  output (voice playback over MQTT is encodable but not natural). The seam therefore needs an explicit
  **negotiation/fallback rule** (§3.1) — this rule is the real design content, more than the plumbing.
- **Subsumes ARCH-7's two seams as ordinary outputs:** Flow 2 *actuation* (`DeviceCommand → ActuationPort
  → BridgeClient`) and the deferred Flow 1 *content-agnostic OutputPort* (`irene/{room}/event`) become two
  entries in the configurable output set — not special cases. MQTT and "voice" are the two outputs that
  need the most care (MQTT is naturally a text/event/device output; "voice" is the one modality tightly
  coupled to a local audio device today).

### 3.1 Modality negotiation (the policy knob)

When the result modality is not carriable by the selected output:
1. **Degrade** if a defined downgrade exists (`speech → text`: deliver the spoken text as text).
2. **Drop + log** if no downgrade is sensible (e.g. raw audio over a text-only console).
3. **Error** only if the handler marked the result delivery-critical.
Default per (modality, output) pairs is tabulated in the implementation; the *default of the default* is
**degrade-then-drop**, never silently mis-deliver.

### 3.2 Delivery is request/response — `deliver()` returns a `DeliveryResult` (D-6)

Every output's delivery returns a result: `OutputPort.deliver(result, context) -> DeliveryResult`.
- **Terminal channels** (console / web / ws-text / room-event): `DeliveryResult` = trivial ack/nack; callers
  ignore it.
- **Bridge / MQTT actuation channel** (ARCH-8): `DeliveryResult` is **rich** — `{success, echoed_value,
  error_code}` (ARCH-7's ~500 ms synchronous value-echo + 6-code error enum). The actuating handler
  **awaits** it *in-turn* under a **bounded timeout** (timeout → degraded confirmation "не уверен,
  выполнилось ли" rather than blocking the turn) and composes the origin-paired confirmation from it.

So `device_command` is a genuine delivery **modality** routed (capability-routed, designated) to the bridge
output — *not* a separate port-shape. An actuation intent emits **two** outputs: the `device_command` to the
bridge (awaited) + the conversational confirmation to the origin. **MQTT is just another output channel;
ARCH-8 implements it under this `OutputPort`/`DeliveryResult` contract.** `DeviceCatalogPort` (catalog pull)
stays a separate read/query port, not an output. Actuation thus flows through OutputManager → onto the event
bus → observable by the debug tap (§5).

---

## 4. Many-to-many daemon (Point 3)

The current "one runner = one channel, processes mutually exclusive" model is replaced by **one daemon**
hosting concurrent input + output adapter registries.

- **InputManager / OutputManager become real coordinators** — registries of *concurrently-active* adapters
  (not the dead `_input_queue`; not a vestigial factory). The InputManager finally has an honest job.
- **Runtime attach/detach.** Adapters can be registered/removed at runtime, not only enumerated at boot
  (today `InputManager.initialize()` discovers once). Required by the debug-attach scenario.
- **Routing-by-origin is mandatory, not optional.** Concurrent streams must not cross: an ESP32-audio
  request's result goes to MQTT while a debug-CLI request's result goes back to that CLI — in the same
  process, at the same time. Resolved by §6.

**Motivating scenario (user):** Irene runs on a smart-home controller consuming an ESP32 audio stream and
delivering via MQTT; on noticing odd behaviour, the operator **attaches a CLI app from a notebook** doing
text in/out — concurrently — to reproduce a failure and gather debugging data, while production channels
keep running. The "CLI from notebook" is a **remote `text`-format channel** (a ws/socket text adapter
pairing an input+output over one connection) — *not* local stdin, and *not* a different runner. It reuses
the ARCH-6 WS driving-adapter shape with `format=text`.

---

## 5. Delivery vs observation: one event bus, two subscriber kinds (Points 3–4)

The debug operator wants **both** reproduce *and* observe live traffic. These are two different mechanisms
that must not be fused:

- **Primary delivery** — point-to-point, origin-addressed, *affects* the system (the OutputManager, §3).
- **Observation / tap** — publish/subscribe, read-only, *side-effect-free*: an observer sees traffic it did
  not originate (the live ESP32↔MQTT exchange).

**One pipeline event bus, two subscriber kinds.** The daemon publishes lifecycle events at each pipeline
boundary; **OutputManager subscribes for delivery** (origin-filtered); **observers subscribe for
monitoring** (filtered by what they want to watch).

- **Event vocabulary (define once, reuse for `/trace`, live-observe, metrics):**
  `input.received` · `asr.transcript` · `intent.recognized` (+confidence) · `result.produced` ·
  `output.delivered` · `error`. The existing `/trace/command` + `/trace/audio` endpoints
  (`webapi_router.py`) are request-scoped consumers of exactly this vocabulary — the live tap is the same
  stream, subscribed continuously.
- **Observers see the trace projection, not raw audio.** A text debug-CLI wants transcripts/intents/results,
  not ESP32 PCM. Raw-audio tap is a separate, opt-in, expensive mode.
- **Subscription filters keyed by identity:** "watch the kitchen ESP32" / "watch everything" → filter by
  `room_name` / `client_id` / `session_id` / `source` (same key as delivery, §6).
- **Gating.** A tap that can observe *all* traffic exposes every utterance and device action system-wide;
  it MUST be auth/config-gated — a deliberate debug attach, not an open subscription. (Smart-home
  controller, real actuation, voice in the home.)

---

## 6. Addressing model (the spine)

The routing key already exists and is already built — `resolve_physical_id(client_id, room_name,
session_id)` (`client_registry.py:568-580`), returning `client_id or room_name or session_id`, on the
already-implemented session-vs-identity split (Model 2, QUAL-28):

- **session** = ephemeral conversation-state bucket, TTL-evicted.
- **physical identity** = persistent room/client/device, first-class on `RequestContext`.

Two delivery timings, two address kinds:

| Result kind | Addresses | Rationale |
|---|---|---|
| Sync result; F&F **ack** | the **live originating connection** | it is still there (request/response) |
| F&F **deferred notification** | the **persistent physical identity** (room/device) → its *current* output | the ephemeral channel may be gone; a kitchen timer must still announce **in the kitchen** |

This is *why* F&F is keyed by `physical_id` not `session_id` (already true — `ActionRecord` carries both).
The deferred notification resolves `physical_id → whatever output currently serves that room/device`, not
the dead session.

**Origin-unreachable fallback (D-3, LOCKED):** **drop + log** by default — and the completion stays queryable
via the action-store history (no information lost). **No cross-channel fallback** (never announce in the
wrong room). Before dropping, for *persistent/reconnectable* targets (room/device served by MQTT or a WS
satellite expected to return), **re-resolve `physical_id → current output` and give the transport a bounded
retry window + backoff**; deliver if it returns. *Ephemeral* targets (detached debug-CLI, observers) → drop
immediately. The reconnect window is the only bounded hold; an open-ended TTL-queue stays deferred.

---

## 7. Fire-and-forget is not special (Point 4)

F&F is the same output path, twice:

- **Immediate ack** ("ставлю таймер на 5 минут") — already an `IntentResult`; routes exactly like a sync
  result, to the originating channel's output.
- **Deferred notification** ("таймер сработал") — today the *only* thing that bypasses everything to hit
  the global TTS/log sink (`NotificationService._deliver_via_tts → self.audio_component.play_file`,
  `notifications.py:377-380`). **Target:** it becomes an ordinary `result.produced`/`action.completed`
  event on the bus; **OutputManager delivers it**, origin-addressed + modality-matched + observable.

**`NotificationService` is demoted from deliverer to producer.** It (or the action-store done-callback)
emits the completion event; OutputManager owns delivery. The session's `notification_preferences` fold in
as **output-selection hints**, not a separate delivery mechanism. F&F is currently **live** (QUAL-28 +
QUAL-9, verified) — so this is a *re-route of a working path*, not a revival.

---

## 8. Runners → profile launchers (Point 5)

Runners are **kept as convenience entry points** but demoted from channel *implementations* to thin
**config-preset launchers** over the one daemon, and must **strictly follow** this design (no bespoke
channel logic, ever).

- **They stop being:** `CLIRunner` owning a `prompt_toolkit` loop; `webapi_runner` hand-wiring routes as
  input; `vosk_runner` reaching into `_sources`. All capture/delivery logic moves into adapters +
  managers + bus.
- **They become:** named presets that boot the daemon with an input-set + output-set —
  `irene-cli` = *console-in + console-out*; `irene-webapi` = *web/ws-in + web/ws-out*;
  `irene-vosk` = *mic-in + local-audio-out*. These are now config, not code.
- **Config-override capability is preserved as config layering:**
  `CLI flags > runner preset > config file > defaults`. `--port`, `-c`, `--enable-tts`, `--input`,
  `--output` resolve to *adapter toggles + settings in the unified config*, never to branching code. (Strictly
  more flexible: `irene-cli --also-enable web` becomes meaningful.)
- **Properties bought:** (1) the double-reader bug is **structurally impossible** — console input is one
  adapter consumed by the daemon, the runner never reads stdin; (2) **identical behaviour** across entry
  points (same adapters → bus → workflow → OutputManager path); (3) many-to-many is just "enable more
  adapters" / runtime-attach.
- **Runner meta-commands** (`help`, `status`) are **already** `system.*` intents (`SystemIntentHandler`,
  `system.py:125-133` — `system.help/status/version/info/language_switch`). D-4 (LOCKED): **delete** the
  runner REPL string-interception (`base.py:344-348`) and route through those existing intents (uniform over
  all channels, observable on the bus). Only true transport/connection control stays adapter-local.

---

## 9. config-ui impact

Net-new config surface ⇒ config-ui work (Invariant #4 — it consumes the backend config contract):

- **New `[outputs]` editor** mirroring the existing inputs/components config (enable/disable per output
  adapter + per-adapter settings). Backend must expose output adapters in the schema the config-ui
  introspects (the `auto_registry` schema path), so the generic ConfigSection renders them.
- **Inputs editor** gains the **format** dimension (per-input declared format) and the many-to-many reality
  (multiple inputs enabled at once — today the UI assumes a single `default_input`).
- **Modality/capability matrix** may warrant a read-only display (which outputs can carry which result
  modalities) so a misconfiguration (e.g. only an MQTT output enabled for a voice profile) is visible.
- **Observation/tap** is an operational/debug surface — likely *not* config-ui (it's a runtime attach), but
  the **gating** config (who may tap) is config-ui.
- Reuse the just-landed generic widgets (UI-9 `KeyValueEditor`, etc.); no bespoke per-adapter UI if the
  schema is introspectable.

---

## 10. Decisions (LOCKED 2026-06-07, design session)

- **D-1 — Format vocabulary → LOCKED.** Closed 3-value enum on `InputData`, each naming its workflow entry
  stage: `voice` (enter at voice-trigger), `audio` (enter at ASR), `text` (enter at NLU, after ASR). No
  `transcript` format. `file`/`binary_audio` are *transport* (input-adapter concern), not formats. Format is
  stamped **per-message** on multi-modal connections (frame type decides). Derived skip-flags replace the
  per-runner hand-set booleans.
- **D-2 — Output selection → LOCKED.** **Modality-routed.** Conversational (`text`/`speech`) →
  **origin-paired** (1 target). Actuation (`device_command`) / event → **capability-routed to a designated
  single output** (no fan-out → no double-actuation). **Handler override** allowed. **Opt-in explicit
  broadcast target** for whole-home announce (handler-chosen, never default). Observers are the separate tap
  (D-5), not part of delivery selection.
- **D-3 — Origin-unreachable F&F → LOCKED.** **drop + log** default; completion stays queryable via the
  existing action-store history (no info lost). **No cross-channel fallback** (never wrong-room). **Bounded
  reconnect/re-resolve before dropping** for *persistent/reconnectable* targets (room/device MQTT or WS
  satellite): re-resolve `physical_id → current output`, bounded retry window + backoff, deliver if it
  returns. **Ephemeral** targets (detached debug-CLI, observers) → drop immediately. Reconnect window is the
  only bounded hold; open-ended TTL-queue deferred.
- **D-4 — Meta-commands → LOCKED.** `help`/`status`/`version`/`info` are **already** `system.*` intents
  (`SystemIntentHandler`, `system.py:125-133`). **Delete** the runner REPL string-interception
  (`base.py:344-348`); route through the existing intents (uniform over all channels, observable on the bus).
  Only true transport/connection control stays adapter-local.
- **D-5 — Observation transport + gating → LOCKED.** One **authenticated WS** connection, dual-role (text
  input+output *and* observe subscription via message types), reusing the ARCH-6 ws infra. **Config-gated,
  off by default**, **shared-token** auth, **localhost-first in PR-6** (remote token-authed attach right
  after — same code, flip the bind). Trace projection by default; **raw-audio opt-in** (separate flag, same
  gate). Identity-scoped server-side filters. All-or-nothing authz in v1 (no per-room ACL).
- **D-6 — ARCH-8 convergence → LOCKED.** **MQTT/bridge actuation is just another output channel.** One
  `OutputPort.deliver() -> DeliveryResult` abstraction (§3.2); `device_command` is a real delivery modality
  (D-2); `ActuationPort` collapses into the bridge `OutputPort`; `DeviceCatalogPort` stays a separate read
  port. **Bounded await** on the bridge echo → degraded confirmation on timeout. **ARCH-8 implements the
  bridge output under ARCH-15's `OutputPort`/`DeliveryResult` contract**; ARCH-8 PR-1 (domain/fake) runs now
  in parallel; the bridge adapter co-designs + lands on ARCH-15 PR-2's interface (so `DeliveryResult` is
  spec'd to carry the echo/error). Reconciled into ARCH-7 by PR-9 (§12).

---

## 11. Hexagon seams (what's new vs reused)

- **Reused:** `InputPort` (`core/interfaces/input.py`); `RequestContext` identity fields; `resolve_physical_id`
  + `ClientRegistry` action store; the WS driving-adapter (ARCH-6); the trace vocabulary; `ActuationPort`
  (ARCH-7/8) as one output.
- **New:** `OutputPort` (`core/interfaces/output.py`) + `DeliveryResult` (request/response delivery, §3.2) +
  `irene/outputs/` adapter package; a real `OutputManager`; the **pipeline event bus** (delivery +
  observation subscribers); `InputData.format`;
  the `[outputs]` config + schema; runtime attach/detach on the managers; the daemon multiplexer that
  today is split across mutually-exclusive runners.
- **Demoted:** runners → presets; `NotificationService` → event producer; the dead `InputManager._input_queue`
  / `WebInput.listen` / `WorkflowManager._start_audio_workflow` family → deleted.

---

## 12. Implementation plan (sliced — ARCH-15)

Ordered so value lands early and nothing is built that §6/§5 will reshape. Each slice is independently
landable and gated (`pyright` 0 · import-linter · dep-validator · `check_scope` · backend suite no-net-regression
· config-ui `npm run check`+`build` where touched).

- **PR-0 — CLI bug stopgap (ship now, design-compatible).** Stop auto-starting the `cli` source under the
  interactive runner (mirror the `web` guard, `manager.py:129`); runner keeps owning its REPL *for now*.
  Pure bugfix, no architecture change, unblocks interactive CLI immediately. Explicitly a stopgap that PR-5
  supersedes.
- **PR-1 — Format as first-class. ✓ DONE 2026-06-07.** `InputFormat` enum `{VOICE, AUDIO, TEXT}` (D-1) on
  `RequestContext.input_format` as the single source of truth (legacy `skip_*` flags = derived projection;
  see §2 reconciliation note — `InputData` is a Union alias, not a class). `configure_pipeline_stages` selects
  the entry stage from it; `process_text_input` passes `input_format=TEXT` (no more hand-set booleans); audio
  entries infer it back-compat. Behaviour-preserving (equivalence-tested vs the prior skip-flag logic).
- **PR-2 — OutputPort + OutputManager + event bus (core, fake adapters). ✓ DONE 2026-06-07.**
  `core/interfaces/output.py` (`OutputPort` ABC mirroring `InputPort`, `OutputModality{TEXT,SPEECH,
  DEVICE_COMMAND,EVENT}`, `DeliveryResult` with rich echo/error_code for the bridge §3.2, and the pure
  `negotiate()` §3.1 matrix); `core/event_bus.py` (`EventType` vocabulary §5, `PipelineEvent`, `EventBus`
  pub/sub with `identity_filter` + subscriber-failure isolation); `irene/outputs/` package + `OutputManager`
  (registry/lifecycle + D-2 routing: conversational→origin-paired, actuation/event→designated-single,
  +broadcast; negotiation; optional `output.delivered` emission). `irene.outputs` added to the hexagon
  import-linter contracts (ARCH-1/2/3/11/12). Adapter-free — exercised by fakes (`test_output_port`,
  `test_event_bus`, `test_output_manager`, 18 tests). Workflow wiring = PR-3.
- **PR-3 — Real text outputs + origin routing.** console output + ws/web text output; wire origin-addressed
  delivery via `resolve_physical_id` (§6). Sync results now flow input→workflow→output through the bus for
  text channels.
- **PR-4 — F&F + notifications re-routed.** Demote `NotificationService` to producer; deferred notifications
  delivered by OutputManager addressed by persistent physical identity (§6, §7); origin-unreachable fallback
  (D-3). Timer end-to-end: ack to origin, completion to room/device output.
- **PR-5 — Daemon multiplexer + runners-as-presets.** One process, concurrent input+output registries,
  runtime attach/detach; runners become config-preset launchers with layered overrides (§8); **PR-0's
  stopgap removed** (console input is now a single daemon-consumed adapter — double-reader structurally
  impossible). Meta-commands per D-4.
- **PR-6 — Observation tap.** Continuous trace-event subscription + identity filters + gating (§5, D-5);
  remote debug-CLI attach (text format) reusing the ARCH-6 ws shape.
- **PR-7 — config-ui.** `[outputs]` editor + inputs `format`/multi-input + capability-matrix display +
  tap-gating config (§9). Lands as the backend `[outputs]` schema (PR-2/PR-3) comes online.
- **PR-8 — Audio/MQTT outputs + ARCH-8 convergence.** Local-audio output (the "voice" modality), MQTT
  event output (Flow 1), and ARCH-8's bridge actuation as a request/response `OutputPort`/`DeliveryResult`
  (D-6, §3.2). Deepens the two flagged-hard cases (MQTT, voice).
- **PR-9 — Cross-task reconciliation sweep (runs last).** Once the I/O contracts are real:
  1. **Explicitly revisit ARCH-7** (`mqtt_integration.md`) — adjust the smart-home design to this I/O
     architecture: `ActuationPort` re-expressed as the bridge `OutputPort`/`DeliveryResult`, `device_command`
     as a delivery modality (D-2), `DeviceCatalogPort` as a read port, the canonical-command flow restated as
     `device_command` output (awaited) + origin-paired confirmation, actuation-on-the-bus/observability,
     bounded-await/degraded-confirmation. Update the ARCH-7 doc + ledger so ARCH-8 builds against the
     reconciled design.
  2. **Sweep every other unfinished ARCH/QUAL item** (esp. ARCH-8, ARCH-10, QUAL-35, and any open task
     touching input/output/session/identity/notifications) to verify whether this design affects it; amend
     the affected ledger entries (+ docs) per Invariants #5/#8. Emit a short reconciliation note in the
     journal listing what was / wasn't affected.

PR-0 is the only thing needed to unblock today; PR-1/PR-2 can begin immediately and in parallel; the rest
sequence behind them. **PR-9 runs last** — reconcile the remaining backlog once the contracts are concrete.
