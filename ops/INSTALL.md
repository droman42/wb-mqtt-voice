# Installing Irene on a Wirenboard controller

The controller runs prebuilt images pulled from the GitHub Container Registry — it never builds
anything. This directory is the whole deployment: a compose file, a ten-line update script, and a
systemd unit. The pattern (and most of the muscle memory) is the same as the sibling
`wb-mqtt-bridge` deployment.

Two things live on the controller:

- **a git checkout of this repository** — brings the compose file, this script, and the
  git-owned assets content (donation phrasings, prompts, templates, localization);
- **the `.assets/` data directory** (gitignored, next to the checkout's `ops/`) — the mounted
  assets root: the synced content above, plus everything the assistant writes: downloaded speech
  models, cache, and durable state (timers survive restarts because their records live here).

## Install

```sh
cd /mnt/data
git clone https://github.com/droman42/wb-mqtt-voice.git
cd wb-mqtt-voice/ops
./update.sh            # syncs assets, pulls images, starts the stack
```

Then wire it to boot:

```sh
ln -s /mnt/data/wb-mqtt-voice/ops/wb-mqtt-voice.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now wb-mqtt-voice
```

The web API answers on port **6000** (`curl http://localhost:6000/health`). Speech models
download into `.assets/` on first boot — the first start takes a few minutes; subsequent starts
reuse them.

## Update

```sh
cd /mnt/data/wb-mqtt-voice
git pull
./ops/update.sh
```

`update.sh` re-syncs the git-owned assets subtrees (and **only** those — downloaded models and
runtime state are never touched), pulls the newest images, restarts the stack, and prunes old
image layers to keep flash usage in check.

## Rolling back

Every published image also carries an immutable `vYYYYMMDD-<sha>` tag (see the package pages on
GHCR). Pin it in `docker-compose.yml`:

```yaml
    image: ghcr.io/droman42/wb-mqtt-voice-armv7:v20260702-abc1234
```

and run `docker compose up -d`. Return to `:latest` the same way.

## Variants

- **English deployment** — switch the image to the `-en` variant
  (`ghcr.io/droman42/wb-mqtt-voice-armv7-en`); language is baked into the image, nothing else
  changes.
- **The configuration editor** — not part of the standard deployment. Bring it up on demand:

  ```sh
  docker compose --profile ui up -d      # serves on port 3000, talks to Irene on :6000
  docker compose --profile ui down       # and away again
  ```

## Recovery notes

- The container is stateless: removing it (or the image) loses nothing — everything that matters
  lives in `.assets/` and the git checkout.
- A corrupted model download can be deleted from `.assets/models/…`; it re-downloads on the next
  start.
- Memory: the compose file caps Irene at 800 MB — if the assistant is OOM-killed on a busy
  controller, check `docker stats` and tune the cap (the ASR/TTS models are the big consumers).
