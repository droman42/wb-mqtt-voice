# Installing Irene on a Wirenboard controller

The controller runs prebuilt images pulled from the GitHub Container Registry — it never builds
anything. This directory is the whole deployment: a compose file, a short update script, and a
systemd unit. The pattern (and most of the muscle memory) is the same as the sibling
`wb-mqtt-bridge` deployment.

**Disk layout rule: re-obtainable data goes to the big SD card; `/mnt/data` is the runtime
environment.** The Wirenboard's root filesystem (~2 GB) and `/mnt/data` (~5 GB) are small
flash; `/mnt/sdcard` is large. Everything that can be re-cloned or re-downloaded — the git
checkout, speech models, logs — lives on the card; durable state (timer records, the report
spool) lives on `/mnt/data`:

- **the git checkout** at `/mnt/sdcard/mqtt-voice-config` — the compose file, this script, and
  the git-owned assets content (donation phrasings, prompts, templates, localization);
- **`.assets/`** (gitignored, in the checkout root → on the card) — the mounted assets root
  (`/app/assets` inside the container): the synced content above plus downloaded speech models,
  cache and traces;
- **`/mnt/data/mqtt-voice-state`** — mounted over `/app/assets/state`, the durable-state
  subtree (timers survive restarts *and* an SD card death because their records live here);
- **`.logs/`** (gitignored, in the checkout root → on the card) — the mounted log directory
  (`/app/logs` inside the container): `irene.log` plus timestamped rotations. Mounted so logs
  neither bloat the container's writable layer nor vanish on recreate.

Docker's data-root is already configured on the controller (`/mnt/data/.docker`) and stays
where it is — the Irene image fits there comfortably.

## Install

```sh
cd /mnt/sdcard
git clone https://github.com/droman42/wb-mqtt-voice.git mqtt-voice-config
cd mqtt-voice-config/ops
./update.sh            # creates + syncs the data dirs, pulls images, starts the stack
```

Then wire it to boot:

```sh
ln -s /mnt/sdcard/mqtt-voice-config/ops/wb-mqtt-voice.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now wb-mqtt-voice
```

The web API answers on port **8080** (`curl http://localhost:8080/health`). Speech models
download into `.assets/` on first boot — the first start takes a few minutes; subsequent starts
reuse them.

## Secrets

Two optional cloud integrations read their keys from the container's environment; both degrade
cleanly to "off" when the key is absent (the assistant still runs fully offline):

- `DEEPSEEK_API_KEY` — the cloud LLM tier of intent recognition;
- `IRENE_REPORTS_TOKEN` — the GitHub token that lets spoken problem reports file themselves
  (fine-grained PAT for the private reports repo, Issues + Contents read/write).

Put them in an `ops/.env` file next to the compose file — compose reads it automatically on
both start paths (the systemd unit and `update.sh` run compose from this directory):

```sh
cat > /mnt/sdcard/mqtt-voice-config/ops/.env <<'EOF'
DEEPSEEK_API_KEY=sk-XXXXXXXX
IRENE_REPORTS_TOKEN=github_pat_XXXXXXXX
EOF
chmod 600 /mnt/sdcard/mqtt-voice-config/ops/.env
```

The file is gitignored; `git pull` never touches it. After adding or changing it, re-run
`docker compose up -d` (or `./update.sh`).

## Update

```sh
cd /mnt/sdcard/mqtt-voice-config
git pull
./ops/update.sh
```

`update.sh` re-syncs the git-owned assets subtrees (and **only** those — downloaded models and
runtime state are never touched), fixes ownership for the container user, pulls the newest
images, restarts the stack, and prunes old image layers to keep flash usage in check.

## Rolling back

Every published image also carries an immutable `vYYYYMMDD-<sha>` tag (see the package pages on
GHCR). Pin it in `docker-compose.yml`:

```yaml
    image: ghcr.io/droman42/wb-mqtt-voice-armv7:v20260702-abc1234
```

and run `docker compose up -d`. Return to `:latest` the same way.

## Variants

- **aarch64 controller (WB8.5 / Pi)** — switch the image to the aarch64 build
  (`ghcr.io/droman42/wb-mqtt-voice-aarch64`); everything else is identical. The armv7 default
  in the compose file targets the WB7.
- **English deployment** — switch the image to the `-en` variant
  (`ghcr.io/droman42/wb-mqtt-voice-armv7-en` / `-aarch64-en`); language is baked into the
  image, nothing else changes.
- **The configuration editor** — not part of the standard deployment. Bring it up on demand:

  ```sh
  docker compose --profile ui up -d      # serves on port 3000, talks to Irene on :8080
  docker compose --profile ui down       # and away again
  ```

## Satellite TLS plane (optional)

Room satellites that connect over mutual TLS (`wss://`) need the fleet-provisioning plane —
nginx + a tiny home CA serving the certificate bootstrap and the mTLS gate. It deliberately
runs **outside** this container, directly on the controller (security-critical PKI must not
depend on Irene being up). It is deployed separately, via ansible — see
[`nginx/README.md`](../nginx/README.md) for the design, the operator runbook
(`esp32-provision approve …`) and the deploy playbook. One wiring point connects the two
planes: set `esp32_irene_upstream: 127.0.0.1:8080` in the nginx `group_vars` so `/ws/audio*`
proxies to the container installed here. Satellites on a trusted network can skip all of this
and connect over plain `ws://` directly to :8080.

## Recovery notes

- The container is stateless: removing it (or the image) loses nothing — everything that matters
  lives in the mounted directories and the git checkout.
- **An SD card death loses nothing precious.** Everything on the card is re-obtainable: re-clone
  the repo, re-run `./update.sh`, and models re-download on the next start. Durable state
  (timers, spooled reports) sits on `/mnt/data/mqtt-voice-state` and reattaches as-is.
- A corrupted model download can be deleted from `.assets/models/…`; it re-downloads on the next
  start.
- Memory: the compose file caps Irene at 800 MB — if the assistant is OOM-killed on a busy
  controller, check `docker stats` and tune the cap (the ASR/TTS models are the big consumers).
