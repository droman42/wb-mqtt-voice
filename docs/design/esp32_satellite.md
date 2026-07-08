# ESP32 voice satellite — consolidated design (ARCH-22)

**Status:** DRAFT 2026-06-14 (interactive design session). **Authoritative** consolidated design for the ESP32
voice satellite. **Supersedes** `ws_esp32_transport.md` and the stale firmware spec `ESP32/docs/irene_firmware.md`;
**folds** `docs/review/esp32_wakeword_review.md` (micro stack keep/fix/cut) and `onnx_inference_layer.md §10/§11`
(WB7-satellite vs standalone split); **incorporates** ARCH-21 reply-to-device. Backs **ARCH-22**.

> **Governing principle (D-1):** the **backend is authoritative**; the quarantined `ESP32/firmware/` draft (rev 2,
> Jul 2025) is **inspiration only**. Where firmware and backend disagree, the firmware adapts.

This session designs the full satellite and implements the **backend** pieces (see §13). The **firmware itself is
a tracked rewrite**, not built here (§14).

---

## 1. Device shape & scope

- **D-2 — Headless voice satellite.** Just the **board + microphone + speaker** in a **3D-printed case**. **No
  display, touch, RTC, or UI**, no weather/clock. Board = ESP32-S3 class (≥8 MB PSRAM); memory requirements are
  **bump-able** if the design demands it. (The draft's UI/display/touch/RTC subsystems are dropped.)
- **D-3 — ESP-IDF + PlatformIO** (`framework = espidf`), **not Arduino**. `common/` as an IDF component;
  per-node `[env:…]`; deps via `lib_deps` / IDF components (notably `esp-tflite-micro`).
- **D-4 — Pure MQTT-unaware voice terminal.** The device sees **audio in / audio out only**. All NLU →
  `DeviceCommand` → bridge → MQTT/native actuation is **backend-side** (ARCH-7/8). The device's reply channel
  carries **SPEECH/TEXT only — never `DEVICE_COMMAND`/`EVENT`**.

## 2. Topology

```
                          ┌──────────────── ESP32-S3 satellite ────────────────┐
   mic ─→ I2S ─→ micro-features ─→ µWW (.tflite) ─→ wake     capture 16k/mono   │
                              └─→ µVAD (.tflite) ─→ gate + end-of-utterance hint │
   speaker ←─ I2S ←── playback 22.05k/mono ←──────────────── reply PCM          │
                          └─────────────────────────────────────────────────────┘
            │  input WS /ws/audio  (PCM up + end-hint)        ▲ reply WS /ws/audio/reply (PCM down)
            ▼                                                 │
                          ┌──────────────── WB7 / 64-bit server ────────────────┐
                          │ streaming ASR (endpointing) → NLU → intent → TTS     │
                          │ actuation → bridge (MQTT/native)                     │
                          └──────────────────────────────────────────────────────┘
```

Two deployment scenarios (ARCH-9 §10/§11):
- **Satellite (this doc):** ESP32 does wake + VAD + capture + playback; the server does ASR/NLU/TTS/actuation and
  **does not** run wake/VAD for this path.
- **Standalone 64-bit (local-mic):** one box runs everything incl. its own VAD + wake — out of scope here.

## 3. Implementation review (Phase 1 summary)

The quarantined draft is **two-tier**. **Real/production-grade:** I2S DMA capture (16k/mono/20 ms + 300 ms
pre-roll), on-device microWakeWord (INT8 TFLite-Micro, ~25 ms), energy VAD, FreeRTOS state machine, mTLS WebSocket
+ reconnect, NVS config, OTA framework. **Stub/skeleton:** the **entire audio-output path** (`i2s_driver.write_frame`
never called, ES8311 codec a 23-line stub), reply handling (binary RX is a `// could be added` stub), and the
UI/touch/RTC. Its **wire protocol predates the backend** (sends `/stt`, `{"config":…}`, `{"eof":1}`, ignores
replies). Verdict: the acquisition/wake/TLS half is reusable *inspiration*; the protocol + output path are the gap.

## 4. Wire protocol (T1)

Two WebSocket connections (mTLS terminated at **nginx**; the app sees plain WS):

### 4.1 Input — `/ws/audio` (exists)
`register` (first text frame) → binary PCM frames (20 ms) → `{"type":"end"}` → server `{"type":"response", success}`.

`register` schema (extended this session):
```json
{ "type":"register", "client_id":"...", "name":"...",
  "primary_room":"...", "covered_rooms":["...","..."],
  "sample_rate":16000, "wants_audio":true,
  "audio_out":{"rate":22050,"channels":1,"width":16},
  "firmware_version":"...", "model_version":"..." }
```
The satellite declares **identity + capability only** — *not* smart-home devices (it's MQTT-unaware, D-4).
The device/room catalogue is owned by the bridge (ARCH-7/8); Irene resolves "the kitchen light" against
*that*, not the registration. (`ClientRegistration.available_devices` is a vestigial ARCH-6 field — a
candidate for code cleanup.)
Server → `{"type":"registered", "client_id", "session_id"}`.

### 4.2 Reply — `/ws/audio/reply` (NEW, device listens)
Device opens it and listens; `register-reply` carries `client_id`; the server pairs an ARCH-21 `RemoteAudioOutput`
(`origin_key == client_id`). Per reply:
```
{"type":"speak_begin", "rate":22050, "channels":1, "width":16, "seq":N}
  [binary PCM frames]
{"type":"speak_end", "seq":N}
```
Disconnect → server unregisters the output. Reply conforms DOWN to the device's `audio_out` contract (ARCH-21
`to_sink`). **D-4:** carries SPEECH/TEXT only.

### 4.3 Codec & format
- **D — raw PCM both directions** (Opus is a future bandwidth optimization). Capture **16 kHz/mono/16-bit**;
  reply **22.05 kHz/mono/16-bit** (D-8).
- **D — input response frame minimal** (`{"type":"response", success, error?}` — an ack/LED-state hint); the spoken
  reply is **only** on the reply channel.

### 4.4 End-of-utterance (D-5, D-6)
- **Single mic v1** (D-5) — far-field/TV robustness via a 2-mic array is a v2 upgrade (§14).
- **Device emits `{"type":"end"}`** on µVAD trailing-silence (700 ms) ∥ max-window (8 s) ∥ session-end — a
  **stream-boundary HINT**, NVS-tunable.
- **Server ASR endpointing is authoritative (D-6) — target; fallback active.** *Today* `/ws/audio` accumulates the
  buffer until `{"type":"end"}` and runs **batch ASR** — the **permanent floor** (a non-streaming provider like
  whisper can *only* batch-on-end) and a correct implementation of the wire contract. The **target** adds an
  **opportunistic** server-side endpoint when the configured ASR can stream (sherpa-onnx `OnlineRecognizer` /
  vosk-streaming): a **new no-VAD streaming path** feeds PCM into `transcribe_stream` and finalizes on the model's
  endpoint (decoded-token timing, not raw energy) — the real defense for the background-noise (TV) case. **NOT**
  `process_audio_stream` (that's the VAD-segmented mic path, wrong for the no-server-VAD ESP32 path). **Deferred to
  ARCH-10** — it's deployment-gated (needs a streaming ASR + the WB7) and testable only there; the wire contract is
  **unchanged** by the deferral (device sends the same frames + end-frame; only the server-internal ASR handling
  gains the enhancement).

## 5. On-device audio I/O + hardware (T2)

- **D-7 — half-duplex v1.** **Digital I2S MEMS mic** (ICS-43434-class) + **MAX98357A** I2S DAC/amp + speaker.
  **v2 (deferred, §14):** ES8311 codec + analog mic + self-authored driver → enables AEC / barge-in / full-duplex.
- **D-8 — specs.** Capture **16 kHz/mono/16-bit/20 ms + ~300 ms pre-roll**; playback **22.05 kHz/mono/16-bit**
  (device declares `audio_out = {22050,1,16}`); end-of-utterance hint **700 ms** silence + **8 s** cap (NVS-tunable).
  Mic and amp sit on **separate I2S peripherals** (capture-16k / playback-22k coexist).
- **Playback path (absent in the draft) is built**: reply PCM (`speak_begin`→frames→`speak_end`) → I2S out → amp →
  speaker. Mic-port acoustic design in the 3D case is the dominant single-mic quality lever.

## 6. Wake-word + microVAD "micro" stack (T3)

Premise (QUAL-19/20): **one `.tflite` artifact, two runtimes** — runs on-device (TFLite-Micro) **and** server-side
(`pymicro-wakeword.from_config`).

- **D-9 — Device wake stack = ported microWakeWord on ESP-IDF.** `esp-tflite-micro` + the **TFLite-Micro
  `micro_features` frontend** (the exact op `pymicro-features` wraps — **NOT** the draft's hand-rolled MFCC) +
  **µVAD (`pymicro-vad` tflite)** gating + the end-of-utterance silence hint (replacing the draft's energy VAD).
  ESPHome's `micro_wake_word` is the **reference implementation, not a dependency** (we're ESP-IDF, D-3 — we port
  its logic). Using the wrong frontend breaks the same-artifact guarantee (threshold no longer transfers).
- **D-10 — Shared contract = the microWakeWord manifest (JSON + co-located `.tflite`), byte-identical device+server.**
  Server already consumes it (QUAL-20); device loads the same. Per-unit custom model (microwakeword.com), tracked by
  `model_version` (§4.1), stored per §7. Bonus: the identical model can run server-side on a captured trace for
  wake-behavior debugging (ties to ARCH-19).

## 7. Inference & models (T4)

- **D-11 — Inference split (satellite).** Device = wake + µVAD + end-hint + capture + playback. Server = the
  **configured ASR** (streaming endpoint opportunistically, D-6) + NLU + TTS + actuation. No server-side wake/VAD.
- **D-12 — Device model storage = dedicated flash data partition** (manifest + `.tflite`, **runtime-loaded**), not
  compiled into the app. Flash: **OTA A/B app · NVS (config) · models** — config + models **survive an app OTA** and
  update **independently** (firmware / model / config are three separately-versioned things). Resolves the
  C-header-can't-be-pushed problem.
- **D-13 — Model push.** **Production:** versioned **HTTPS GET from WB7** (`GET /esp32/model/{ref}`, mTLS at nginx);
  device reports `model_version`, fetches on mismatch, integrity-checks (hash), atomic partition swap. **Dev-cycle:**
  upload via the **device admin UI** (§9). Server hosts the artifact via the AssetManager (same artifact ⇒ D-10).

## 8. Identity & multi-room (T5)

- **D-14 — Identity = stable `client_id` + `name` + `primary_room` + `covered_rooms[]`.** `client_id` **is the
  device** = the reply-to-device physical identity; **`resolve_physical_id` is unchanged for output** (origin-pairs
  on `client_id`; rooms don't affect reply-to-device). The `register` handshake + `ClientRegistration` + registry
  **carry** primary + covered rooms (back-compat: `room_name` aliases `primary_room`). Ready-but-inert, the ARCH-6
  pattern.
- **D-15 — Multi-room resolution policy** (spec for the room resolver; **owned by ARCH-7/QUAL-35**, needs the bridge
  catalog ARCH-8 + RU-morphology room matching). Given utterance + `(primary_room, covered_rooms)` + global room set
  **R** (catalog):
  1. Scan the utterance for a room name (always).
  2. If room `r` mentioned: `r ∈ covered_rooms` → **target = r** ("свет на кухне" from `primary=living_room` →
     `kitchen`); `r ∈ R` but `r ∉ covered_rooms` → **voice error** "<room> is not managed by this device" (SPEECH,
     **no actuation**); `r ∉ R` → not a room, fall through.
  3. No room mentioned → **target = `primary_room`**.
  - *Undefined (not blocking):* two rooms in one utterance.
  - This session **carries** the data only; the resolver lands with ARCH-7/QUAL-35.

## 9. Provisioning & lifecycle (T6)

Based on the proven **mitsubishi2wb** pattern (SoftAP captive portal + web admin UI), ESP-IDF-ported.

- **D-16 — Two-stage provisioning.**
  - **Stage 1 — AP captive portal** (device isolated, **no WB7 route**): collect **WiFi creds + WB7 address**
    (offline-only data). Save → reboot to STA. (`esp_wifi` AP + `esp_http_server` + captive-DNS + `esp_netif`;
    AP-fallback if WiFi fails; `mdns` hostname.)
  - **Stage 2 — STA admin UI** (`http://<host>.local`, device now reaches WB7): autonomous **CSR → CA cert
    exchange** (D-17), then **identity / rooms (picked from the bridge catalog) / model** via the admin UI. Cert
    exchange is **never** in AP mode.
  - **Admin UI v1: no password, no button-gating** (trusted home LAN). **v2 (§14):** admin password + config-button
    gating (short = enable ~10 min window; long = factory-reset to AP); optional HTTPS-self-signed portal.
- **D-17 — Cert provisioning = CSR-approval via config-ui** (no token). Device generates its keypair (private key
  **never leaves the device**), submits its CSR unauthenticated in Stage 2 → **pending queue on WB7** → operator
  approves in **config-ui** (sees `client_id` + CSR fingerprint) → WB7 CA signs → device fetches its cert. Trust
  anchor = config-ui admin access. nginx does the mTLS verification.
- **D-18 — OTA = A/B + `esp_https_ota` from WB7** (`GET /esp32/firmware/{ref}`, mTLS at nginx). Device reports
  `firmware_version`, fetches on mismatch, writes the inactive slot, validates, reboots, **auto-rollback** on boot
  failure. NVS config + models partitions are **preserved** (D-12).
- Config stored in **NVS** (survives OTA); web assets embedded / `www` partition.

## 10. Backend cross-cutting (T7)

- **Voice-confirmation of actuation (T-B)** — sequenced `DEVICE_COMMAND → bridge rich DeliveryResult → derive text →
  SPEECH to origin device`. **Opt-in via config** (`confirm_actuation_by_voice`); phrasing from the bridge echo
  (success → "готово"/device-specific; error-code → spoken error). **Device-transparent** (reply audio via ARCH-21).
  **Owned by / implemented with ARCH-8** — design item, not built here.
- **Device-half resolver** (D-15 semantics) — **owned by ARCH-7/QUAL-35 + ARCH-8 catalog**; not re-opened here.

## 11. Decision log

| # | Decision |
|---|---|
| D-1 | Backend authoritative; firmware draft = inspiration only |
| D-2 | Headless voice satellite (board + mic + speaker, 3D case); no display/UI; memory bump-able |
| D-3 | ESP-IDF + PlatformIO; not Arduino |
| D-4 | Device is a pure MQTT-unaware voice terminal; smart-home stays backend (ARCH-7/8) |
| D-5 | Single mic v1 (2-mic array = v2) |
| D-6 | Server-streaming ASR endpointing is the target & authority; device end-frame is a hint. **Fallback (accumulate-until-end + batch ASR) is the permanent floor & active; the streaming enhancement is deferred to ARCH-10** |
| D-7 | Half-duplex v1: digital I2S mic + MAX98357A; ES8311 + analog + self-driver = v2 |
| D-8 | Capture 16k/mono/16-bit/20ms/300ms pre-roll; playback 22.05k/mono/16-bit; end-hint 700ms/8s |
| D-9 | Device wake stack = ported microWakeWord on ESP-IDF (TFLite-Micro micro-features frontend + µVAD); not the draft's MFCC/energy VAD |
| D-10 | Shared contract = the microWakeWord manifest (JSON + `.tflite`), byte-identical device+server |
| D-11 | Inference split: device wake/µVAD; server = configured ASR (opportunistic streaming endpoint) + NLU/TTS/actuation |
| D-12 | Device models in a flash data partition (runtime-loaded); OTA A/B · NVS · models; config+models survive OTA |
| D-13 | Model push: prod = HTTPS-from-WB7 (versioned, hashed); dev = admin UI. **Amended: served by Plane-B nginx static from `/srv/esp32/models/` (operator-managed), NOT Irene's AssetManager** |
| D-14 | Identity = client_id + name + primary_room + covered_rooms[]; resolve_physical_id unchanged for output |
| D-15 | Multi-room resolution policy (impl → ARCH-7/QUAL-35 + ARCH-8 catalog; data carried now) |
| D-16 | Two-stage SoftAP→STA provisioning + web admin UI (v1 no-auth/no-button; v2 adds them) |
| D-17 | Cert provisioning = CSR-approval (no token); private key stays on device. **Amended: Plane-B home CA on the WB7; approval via the `esp32-provision` CLI over SSH (dedicated/LAN-only > config-ui for a once-per-device op); config-ui may call the same scripts later** |
| D-18 | OTA A/B + esp_https_ota from WB7; config/models preserved; auto-rollback |

## 12. Backend implementation plan (Phase 4 — this session builds backend only)

1. **Reply channel** — `/ws/audio/reply` WS endpoint + `register-reply` → `OutputManager.add_output(client_id,
   RemoteAudioOutput)` on connect, `remove_output` on disconnect; `CallbackReplyChannel` adapter (the ARCH-21
   device-half). **✓ DONE** (`d8b1c70`).
2. **`register` extension** — `audio_out`, `primary_room`/`covered_rooms`, `firmware_version`/`model_version` in
   `ClientRegistration` + the `/ws/audio` handler (D-14); back-compat `room_name` alias. **✓ DONE** (`fa56978`).
3. **Streaming endpointing (D-6)** — a **new no-VAD streaming path** feeding the configured ASR's `transcribe_stream`
   + endpoint, opportunistic; accumulate-until-`end` + batch ASR stays the permanent fallback (active today).
   **DEFERRED to ARCH-10** — deployment-gated (streaming ASR + WB7), testable only there; the wire contract is
   unchanged. *(Not `process_audio_stream` — that's the VAD-segmented mic path.)*
**★ Plane A / Plane B split (refined 2026-06-14, WB7 SSH recon).** Items 4–6 are **not Irene** — they're a
separate **fleet-provisioning plane (Plane B)** that runs as **nginx + openssl + scripts directly on the WB7**, not
in any container. Rationale: it's security-critical PKI + static serving, must not depend on Irene being up, and the
WB7 is tiny (~1 GB RAM / 2 GB disk, armv7 — another service is the wrong weight; Irene isn't even deployed there).
**Plane A (Irene voice pipeline) is complete for ESP32** with #1+#2 (#3 → ARCH-10). Plane B lives in the repo at
**`nginx/`** (an Ansible playbook the operator runs on the controller).

4. **Asset serving** → **Plane B: nginx static.** `GET https://<host>/esp32/{firmware,models}/…` behind
   `ssl_verify_client on`. **No Irene endpoint.** Operator/CI publishes files into `/srv/esp32/{firmware,models}/`
   (the per-node model is operator-managed there — amends D-13: *not* served by Irene's AssetManager, which is for
   Irene's own server-side models in the standalone-64-bit scenario).
5. **CSR-approval / CA** → **Plane B: openssl home-CA + nginx + CLI.** Two zones: `:8081` bootstrap (dedicated port — the WB admin UI owns the controller's `:80`, ARCH-41; public CA cert +
   CSR `PUT` + signed-cert `GET`; no secrets cross — the device key never leaves it; the **human approval is the
   gate**) and `:443` mTLS operations. Approval is **`esp32-provision {list,approve,revoke}`** over SSH (amends D-17:
   a dedicated, LAN-only CLI — more isolated than config-ui for a once-per-device crown-jewel op; config-ui can call
   the same scripts later). EC (`prime256v1`) keys throughout (light for the device handshake). CSR treated as
   untrusted input (client_id validated, signed by file). Proven end-to-end with openssl.
6. **Ops (WB7)** → **Plane B Ansible playbook** (`nginx/ansible/deploy.yml`): creates the layout, installs the
   scripts, inits the CA once, templates + enables the nginx site, validates + reloads. Idempotent.

Plane-A items land within the Irene invariants (net-0, pyright 0, config-ui green, contracts); Plane B is a deploy
artifact (no Irene code), validated by `bash -n` + an end-to-end openssl dry-run.

## 13. Ledger closure (Phase 5)

On completion ARCH-22 **closes/absorbs**: **QUAL-45** (end-of-utterance + on-device VAD/wake contract — input *and*
output protocol), the **ARCH-21** reply-channel device-half handoff, and the ESP32 pieces of **ARCH-6** (transport)
/ **ARCH-9** (split) / **ARCH-10** (the ESP32-relevant inference; WB7 hardware re-validation done via SSH, §14).

## 14. Deferred / v2 / out of scope

- **Firmware rewrite itself** — the C++ ESP-IDF build (per `esp32_wakeword_review.md` quarantine → fresh build).
  Tracked separately; **not built this session** (backend only).
- **v2 hardware/features:** 2-mic array + beamforming (far-field/TV); ES8311 + analog mic + AEC + **barge-in**
  (full-duplex); Opus on the wire; admin-UI password + button-gating + HTTPS portal.
- **Owned elsewhere:** D-15 resolver (ARCH-7/QUAL-35 + ARCH-8 catalog); T-B voice-confirmation (ARCH-8);
  multi-room-per-utterance (undefined).
- **WB7 streaming-ASR validation** — doable now via SSH (I have access), not deferred.

## 15. Open residuals
- Opus-vs-PCM revisit if a multi-satellite deployment strains WiFi.
- The reply-channel `seq`/utterance-boundary semantics under rapid back-to-back replies.
- Admin-UI ↔ config-ui division for dev-cycle model upload (both can serve it).
