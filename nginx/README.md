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
| `GET  http://<host>/esp32/provision/ca.crt` | **:80 bootstrap** | the home-CA cert (public trust anchor) — the device fetches it to trust the server |
| `PUT  http://<host>/esp32/provision/pending/<client_id>.csr` | **:80 bootstrap** | the device submits its CSR (public; the private key never leaves the device) |
| `GET  http://<host>/esp32/provision/cert/<client_id>.crt` | **:80 bootstrap** | the device polls for its signed cert (404 until an operator approves) |
| `GET  https://<host>/esp32/firmware/...` | **:443 mTLS** | OTA firmware images (only provisioned devices, by client cert) |
| `GET  https://<host>/esp32/models/...` | **:443 mTLS** | µWW/µVAD model artifacts (manifest + `.tflite`) |

**Two zones, by design:**
- **`:80` provisioning bootstrap** — everything here is *public* (a CA cert, a CSR, a signed cert; no
  secrets, the device key never leaves the device). The security gate is the **human approval**, not the
  transport. Solves the cert chicken-and-egg without a bootstrap secret.
- **`:443` mTLS operations** — `ssl_verify_client on` against the home CA, so only a **provisioned device
  with a CA-signed cert** can pull firmware/models. This is also where Irene's `/ws/audio*` is reverse-
  proxied **if Irene runs on this host** (commented in the template — Irene typically runs elsewhere).

## Approval model (CSR-approval, D-17)

A device's CSR is **not** auto-signed. The operator approves over SSH:

```sh
esp32-provision list                 # show pending CSRs: client_id + subject + fingerprint
esp32-provision approve kitchen_node # validate + sign with the home CA -> publish the cert
esp32-provision revoke  kitchen_node # drop a pending CSR
```

The private CA key (`/etc/esp32-ca/ca.key`, mode 600, root-only) is **never** web-served and never leaves
the controller. The signing scripts treat the CSR as untrusted input (the `client_id` is validated against
`^[A-Za-z0-9_-]+$`; the CSR is signed by *file*, never interpolated into a shell). A future config-ui
"Device Provisioning" view can call these same scripts via a thin endpoint — but the CLI is the v1 surface
(simplest, most isolated for a once-per-device, crown-jewel operation).

## Keys

EC (`prime256v1`) throughout — far lighter than RSA-4096 for the ESP32's mTLS handshake, and smaller certs.

## Layout on the controller

```
/etc/esp32-ca/                 # PRIVATE (root 700) — never web-served
  ca.key  ca.crt               # the home CA
  server.key  server.crt       # the WB7 server cert (signed by the CA), used by :443
/srv/esp32/                    # web roots (public artifacts only)
  provision/ca.crt             #   :80  the public CA cert
  provision/pending/<id>.csr   #   :80  device-submitted CSRs (nginx writes, www-data)
  provision/cert/<id>.crt      #   :80  signed device certs (sign script writes)
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

## What this plane does NOT do

- It is **not** Irene and not the bridge. Irene's ESP32 backend (reply channel, register handshake, ASR)
  lives in the Irene repo (ARCH-22 Plane A) and is unaffected.
- It does not run the wake/ASR/TTS — that's Irene (wherever it's deployed).
- Model *authoring* (microwakeword.com training) is upstream; this plane only *serves* the artifact.
