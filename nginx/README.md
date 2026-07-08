# ESP32 fleet-provisioning plane (Plane B)

The device-fleet / provisioning plane for the ESP32 voice satellites (ARCH-22, design
`docs/design/esp32_satellite.md`). It is **deliberately separate from Irene** — it runs as
**nginx + openssl + a few scripts** directly on the Wirenboard controller (WB7), **not** in the Irene
or wb-mqtt-bridge container. Rationale: it's security-critical PKI + static serving, it must not depend
on Irene being up, and the WB7 is tiny (~1 GB RAM / 2 GB disk, armv7) — another service is the wrong
weight.

## What it does

| Endpoint | Zone | Purpose |
|---|---|---|
| `GET  http://<host>:8081/esp32/provision/ca.crt` | **:8081 bootstrap** | the home-CA cert (public trust anchor) — the device fetches it to trust the server |
| `PUT  http://<host>:8081/esp32/provision/pending/<client_id>.csr` | **:8081 bootstrap** | the device submits its CSR (public; the private key never leaves the device) |
| `GET  http://<host>:8081/esp32/provision/cert/<client_id>.crt` | **:8081 bootstrap** | the device polls for its signed cert (404 until an operator approves) |
| `GET  https://<host>/esp32/firmware/...` | **:443 mTLS** | OTA firmware images (only provisioned devices, by client cert) |
| `GET  https://<host>/esp32/models/...` | **:443 mTLS** | µWW/µVAD model artifacts (manifest + `.tflite`) |

**Two zones, by design:**
- **`:8081` provisioning bootstrap** — a dedicated port, NOT `:80`: the WB admin UI is served
  by this same nginx on `:80`, and a server block claiming the bare IP there would steal it
  (ARCH-41; both ports are ansible variables). Everything here is *public* (a CA cert, a CSR, a signed cert; no
  secrets, the device key never leaves the device). The security gate is the **human approval**, not the
  transport. Solves the cert chicken-and-egg without a bootstrap secret.
- **`:443` mTLS operations** — `ssl_verify_client on` against the home CA, so only a **provisioned device
  with a CA-signed cert** can pull firmware/models. This is also where Irene's `/ws/audio*` is reverse-
  proxied **if Irene runs on this host** (enabled by setting `esp32_irene_upstream` — since the release deploys Irene ON the controller, set it to `127.0.0.1:8080`).

## Approval model (CSR-approval, D-17) — the operator CLI

A device's CSR is **never auto-signed**. Approval is a deliberate human step, done **over SSH** with the
`esp32-provision` CLI. The CLI runs as **root**, which is *why it's a CLI and not a web page*: signing needs
the CA private key (`/etc/esp32-ca/ca.key`, mode `600`, root-only). A web page served by nginx runs as
`www-data` and cannot read that key — so a web "approve" button would require either weakening the key's
permissions or running a root-privileged web CGI (more attack surface). The root CLI over SSH avoids both.
(A future config-ui "Device Provisioning" view could call these same scripts via a thin endpoint — but the
CLI is the v1 surface: simplest and most isolated for a once-per-device, crown-jewel operation.)

### Commands

```sh
esp32-provision list                  # show every pending CSR: client_id, subject, pubkey SHA-256
esp32-provision approve <client_id>   # review + sign with the home CA -> publish the device cert
esp32-provision revoke  <client_id>   # drop a pending CSR (rejected / mistaken submission)
esp32-provision status                # counts: pending vs issued
```

### Provisioning a new device — runbook

1. **Flash + Stage-1** the device (WiFi creds + this controller's address). On first STA boot it generates an
   EC keypair (private key **stays on the device**), builds a CSR, and `PUT`s it to
   `http://<host>/esp32/provision/pending/<client_id>.csr`. It then polls
   `http://<host>/esp32/provision/cert/<client_id>.crt` (404 until you approve).
2. **See it arrive** — on the controller:
   ```sh
   ssh root@<controller>
   esp32-provision list
   #   PENDING  kitchen_node
   #     subject:       CN = kitchen_node
   #     pubkey-sha256: 5742d564e22c1143...a4a8e994
   ```
3. **Verify before signing.** Confirm the `client_id`/`CN` is the device you expect, and (ideally)
   cross-check the `pubkey-sha256` against what the device shows in its admin UI. **Signing grants the device
   mTLS access to firmware + models — only approve devices you recognise.**
4. **Approve** (or reject):
   ```sh
   esp32-provision approve kitchen_node   # -> /srv/esp32/provision/cert/kitchen_node.crt
   esp32-provision revoke  rogue_node     # -> drops the CSR, nothing signed
   ```
5. **Device finishes** — its next poll returns the cert; it stores it in NVS and connects the `:443` mTLS
   endpoints. Done — re-provisioning only happens on a factory-reset.

### Safety properties

- The CA private key never leaves the controller and is never web-served (it lives in `/etc/esp32-ca`, outside
  every web root).
- The signing scripts treat the CSR as **untrusted input**: `client_id` must match `^[A-Za-z0-9_-]+$` (no path
  traversal / shell injection), the CSR must self-verify (`openssl req -verify`) before signing, and it is
  signed **by file** — never interpolated into a shell.
- Nothing on the `:8081` bootstrap zone is secret (a public CA cert, a CSR, a signed cert; the device key never
  crosses it), so the **human approval is the only gate** — there is no bootstrap password to manage or leak.

## Keys

EC (`prime256v1`) throughout — far lighter than RSA-4096 for the ESP32's mTLS handshake, and smaller certs.

## Layout on the controller

```
/etc/esp32-ca/                 # PRIVATE (root 700) — never web-served
  ca.key  ca.crt               # the home CA
  server.key  server.crt       # the WB7 server cert (signed by the CA), used by :443
/srv/esp32/                    # web roots (public artifacts only)
  provision/ca.crt             #   :8081 the public CA cert
  provision/pending/<id>.csr   #   :8081 device-submitted CSRs (nginx writes, www-data)
  provision/cert/<id>.crt      #   :8081 signed device certs (sign script writes)
  firmware/...                 #   :443 OTA images   (operator/CI publishes)
  models/<client_id>/...       #   :443 model packs  (operator publishes the per-node artifact)
/usr/local/bin/
  esp32-ca-init.sh  esp32-sign-csr.sh  esp32-provision.sh
```

## Publishing firmware / models

Plain file copies into the mTLS web roots (no app):

```sh
# firmware (PlatformIO build output), versioned:
install -D -m644 .pio/build/<env>/firmware.bin  /srv/esp32/firmware/<version>/firmware.bin
# per-node model pack (microWakeWord manifest + tflite):
install -D -m644 jarvis.json   /srv/esp32/models/kitchen_node/jarvis.json
install -D -m644 jarvis.tflite /srv/esp32/models/kitchen_node/jarvis.tflite
```

The device reports `firmware_version` / `model_version` in its `register` frame (Irene side); on a
mismatch it fetches the new artifact from `:443` over mTLS (esp32_satellite.md D-13/D-18).

## Deploy

```sh
cd nginx/ansible
cp inventory.example.ini inventory.ini          # set the controller host/ip
cp group_vars/all.example.yml group_vars/all.yml # set server_name etc.
ansible-playbook -i inventory.ini deploy.yml
```

The playbook is **idempotent**: it creates the layout, installs the scripts, runs the CA init **once**
(guarded on `ca.key`), templates the nginx site, and reloads nginx after `nginx -t`. It never overwrites an
existing CA.

Pre-flight, on the controller: `ss -tlnp | grep -E ':443 |:8081 '` — both must be free (`:80` is the WB
admin UI on the same nginx, which is exactly why the bootstrap zone doesn't use it; override
`esp32_http_port`/`esp32_https_port` in `group_vars/all.yml` if your box differs).

## What this plane does NOT do

- It is **not** Irene and not the bridge. Irene's ESP32 backend (reply channel, register handshake, ASR)
  lives in the Irene repo (ARCH-22 Plane A) and is unaffected.
- It does not run the wake/ASR/TTS — that's Irene (wherever it's deployed).
- Model *authoring* (microwakeword.com training) is upstream; this plane only *serves* the artifact.
