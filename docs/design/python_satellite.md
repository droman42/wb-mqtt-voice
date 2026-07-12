# Python satellite (`irene-satellite`) — room node without firmware

**Status: AGREED 2026-07-06 (interactive design session, ARCH-35). S-1..S-9 all user-approved
(P-1..P-4 accepted as proposed and renumbered S-6..S-9).**

A first-class satellite deployment mode and the release-critical test client in one: the full
satellite-side pipeline — microphone → VAD → wake word → stream to the controller — running on
any Python-capable box (laptop for testing, a Pi + mic as a real room node), speaking the same
wire contract the future ESP32 firmware will implement. Unblocks ARCH-25 items (3)/(4), which
are unverifiable today (no ESP32 firmware exists), and exercises the fleet TLS plane end to end.

## 1. Decisions

- **S-1 — Both entry modes, default `single`.** `single` is ESP32-faithful (the device VADs and
  wakes locally, streams one bounded utterance); `--mode streaming` covers the ARCH-10
  server-authoritative endpointing that ARCH-25 (3) names explicitly.
- **S-2 — Wake word on by default, `--no-wake` to bypass.** Default is the faithful gate
  (microWakeWord «Ирина» — the same packs the ESP32 will run); `--no-wake` streams every VAD
  utterance for rapid testing.
- **S-3 — `[satellite]` config section**, not CLI-args-only: config-driven like every other
  deployment concern, editable in config-ui (type parity per `config-ui-stays-functional`).
  CLI flags override individual fields for ad-hoc test runs (`--server`, `--room`, `--mode`,
  `--no-wake`).
- **S-4 — First-class product mode from day one.** Runner + console script + config profile +
  user guide ship together; a Pi with a mic running `irene-satellite` is a supported room node,
  not a lab hack.
- **S-5 — The fleet TLS plane (nginx Plane B) is part of this work and fully tested.** The
  emulator implements the device-side provisioning dance (keypair → CSR → poll for the approved
  cert) and connects over `wss://` with mTLS through the nginx `/ws/` proxy — the first real
  client of the CSR-approval flow (D-17) before any firmware exists. Plain `ws://` remains for
  local/dev (TLS is a property of the deployment, not the protocol).

## 2. Composition (everything but §3–4 already exists)

```
MicrophoneInput → AudioNegotiator (canonical 16 kHz mono) → VoiceSegmenter (VAD)
    → voice-trigger gate («Ирина», skipped with --no-wake)
    → SatelliteLink (§3, new): /ws/audio client
Reply: /ws/audio/reply client (§4, new) → audio component playback
```

Components on in the satellite profile: `audio` (playback), `voice_trigger`, VAD; **off**: asr,
nlu, llm, tts, intent_system, text_processor — the controller owns understanding. The runner
follows the existing BaseRunner pattern (cli/webapi/voice precedent; not gated on ARCH-16).

## 3. The wire contract — `/ws/audio` (uplink)

The maintained protocol reference is **`docs/guides/websocket-api.md`** (the
`ws-protocol-doc-canonical` invariant); this section holds the design rationale and defers to
it. The ESP32 firmware implements the same protocol. The client core is ADAPTED from locveil-commons' `ws_audio_provider` (proven against
local + wb7); the runner takes no runtime dependency on the test framework.

```
client → TEXT   {"type":"register","client_id":..,"room_name":..,"sample_rate":16000,
                 "wants_audio":true,"mode":"single"|"streaming","wants_trace":false}
server → TEXT   {"type":"registered","client_id":..,"session_id":..,"trace":true|false}
client → BINARY PCM16 mono frames (paced, frame_ms≈32)
client → TEXT   {"type":"end"}                      # single mode: utterance boundary
server → TEXT   {"type":"partial","text":..}        # streaming mode only, 0+
server → TEXT   {"type":"response", ...canonical result shape...}
server → TEXT   {"type":"trace","request_id":..,"trace":{...}}  # only when trace granted (ARCH-37)
```

`wants_trace` defaults to `false` (a device that doesn't ask never sees a trace frame); the
`registered` ack's `trace` field is the explicit grant — the controller honors the request only
when its `[trace] allow_remote_request` is on. Full design: `satellite_tracing.md` (ARCH-37).

Registration carries the D-14 identity (client_id, room) — the satellite is a registered
client: room-scoped sessions, «включи свет» resolves to ITS room, deferred completions address
it. Lifecycle: persistent connection with re-register on reconnect (exponential backoff,
1→30 s); one utterance per `end` cycle in single mode.

## 4. The wire contract — `/ws/audio/reply` (downlink)

```
client → TEXT   {"type":"register-reply","client_id":..,"audio_out":{"rate":22050,"channels":1}}
server → TEXT   {"type":"registered","client_id":..}
server → TEXT   {"type":"speak_begin", ...}   then BINARY PCM frames   then {"type":"speak_end"}
```

The emulator plays the framed PCM through the local audio component. Server behavior already
live: on reply-channel connect the controller drains undelivered completion notices (a timer
that rang during a satellite reboot speaks on reconnect — ARCH-28 D-6). The emulator's
reconnect test makes this a covered path for the first time.

## 5. TLS / provisioning (S-5) — the device side of Plane B

Against the Plane-B tree as deployed by its ansible role *(written as this repo's `nginx/`;
moved 2026-07-12 to `../locveil-satellite/provisioning/` — BUILD-22/PROD-15; the deployed WB7
plane and these zones are unchanged)*:

1. **Bootstrap (`http://<host>/esp32/provision/…`):** on first run with TLS configured and no
   cert present, the emulator generates an EC keypair (private key never leaves the box),
   submits `PUT pending/<client_id>.csr`, and polls `cert/<client_id>.crt`.
2. **Operator approval** stays human-over-SSH (`esp32-provision approve <client_id>`) — the
   emulator prints exactly this command while polling.
3. **Operations:** with the cert issued, the satellite connects
   `wss://<host>/ws/audio` + `/ws/audio/reply` with client cert + CA pinning
   (`ssl_verify_client on` upstream; nginx injects `X-Client-Cert-DN` — renamed from
   `X-Client-Cert-CN` at implementation, since the value was always the full subject DN; Irene
   enforces cert-CN == claimed `client_id` on both WS endpoints — finding (b)).

- **S-6 (accepted) — key material location:** `<assets_root>/credentials/satellite/`
  (`sat.key` 600, `sat.crt`, `ca.crt`) — the existing credentials dir, asset-managed, never in
  git or configs.
- **S-7 (accepted) — CI-able TLS test:** a hermetic e2e that renders the ansible nginx template
  with a throwaway CA into a docker nginx, runs the full CSR→approve (scripted)→mTLS-wss cycle
  against a local Irene — so the security plane has a regression test that needs no WB7.

## 6. `[satellite]` config section

```toml
[satellite]
enabled = false                    # the satellite runner requires this section
server_url = "ws://wb7:8080"       # controller; wss://host443 engages TLS (§5)
client_id = "kitchen_satellite"
room_name = "Кухня"
mode = "single"                    # "single" | "streaming"
wake_word_required = true          # --no-wake overrides per run
audio_out_rate = 22050
audio_out_channels = 1
# [satellite.tls] — present ⇒ wss expected
# ca_cert / client_cert / client_key = paths (default: <assets_root>/credentials/satellite/)
# bootstrap_url = "http://wb7:8081" # the provisioning zone (dedicated port, ARCH-41)
```

CoreConfig gains `SatelliteConfig` (+ config-ui type parity + the schema-driven section appears
automatically — the `reports` precedent). Config profile `configs/satellite.toml` ships
(mic+vad+trigger+audio on, everything else off).

## 7. Deliverables & docs (S-4)

Runner `irene/runners/satellite_runner.py` + console script `irene-satellite`; `SatelliteLink`
uplink client + reply-channel client (likely `irene/inputs/`-adjacent or a dedicated
`irene/satellite/` module — implementer's call at the right altitude); `configs/satellite.toml`;
user guide `docs/guides/satellite.md` (running a room node on a laptop/Pi, the provisioning
runbook from the device's perspective, diagram) + README links; QUICKSTART gains the satellite
as a run mode.

- **S-8 (accepted):** an aarch64 docker image for Pi deployment is a **deferred follow-up**
  (filed at completion), not v1 — bare `uv run irene-satellite` covers the release need.
- **S-9 (accepted):** loopback e2e in the unit suite (satellite pipeline against an in-process
  server over `ws://`, WAV-injected mic) + the S-7 TLS e2e; live-mic behavior stays a manual
  ARCH-25 item.

## 8. What this deliberately does not replace

- `make ws TARGET=wb7` (recorded-fixture conformance) stays the reproducible protocol gate.
- The eventual ESP32 firmware still validates the micro-stack (I2S, PSRAM, on-device tflite);
  this work burns in the server contract and the security plane first, in the right order.

## 9. Implementation (tasks to file at design completion)

1. `SatelliteConfig` + config-ui parity + `configs/satellite.toml`.
2. `SatelliteLink` (uplink, both modes) + reply-channel client + playback wiring.
3. Runner + console script + reconnect/backoff lifecycle.
4. TLS: provisioning dance + mTLS connect (S-6 storage) + the S-7 hermetic e2e.
5. Loopback e2e + unit tests (framing, register shapes, reconnect, wake gate).
6. Guide + diagram + README/QUICKSTART.
7. Deferred follow-up filing: Pi/aarch64 satellite image (S-8).
