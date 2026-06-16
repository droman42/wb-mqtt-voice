# Docker builds

Irene ships as three Docker images, one per deployment role and CPU architecture. Each image installs only
what its config profile needs — the [build analyzer](build-system.md) turns the profile into a minimal
dependency set at build time — and bakes that one profile in. The differences between the three are the CPU
they target, the speech models they carry, and whether they run the microphone locally:

| Image | Architecture | Role |
|---|---|---|
| `wb-mqtt-voice-standalone` | x86_64 | Full local voice box — mic → wake-word → ASR → intent → TTS → playback. |
| `wb-mqtt-voice-aarch64` | aarch64 (WB8.5 / Pi) | Satellite server — ASR + intent + TTS for ESP32 satellites; no local mic. |
| `wb-mqtt-voice-armv7` | armv7 (WB7) | Satellite server, smaller models; no local mic. |

On the satellites the ESP32 owns the microphone, voice activity detection, wake-word, and playback; the
container only does recognition and speech synthesis and streams the reply back over the web API. The
standalone image is the one that drives audio hardware itself.

## Published images

Each image is published to the GitHub Container Registry and tagged `latest`, `sha-<short>`, and
`v<date>-<sha>`:

```bash
docker pull ghcr.io/droman42/wb-mqtt-voice-standalone:latest
docker pull ghcr.io/droman42/wb-mqtt-voice-aarch64:latest
docker pull ghcr.io/droman42/wb-mqtt-voice-armv7:latest
```

## Config and assets

The config profile is **baked into the image** at `/app/runtime-config.toml` — you do not supply a config
file at run time. To change settings, mount your own file over it or point `IRENE_CONFIG_FILE` at a mounted
path.

Assets — donation phrasings, prompts, templates, and the downloaded speech models — live **outside** the
image under a single assets root, so they survive upgrades and can be shared between containers. Mount a host
directory at `/app/assets`:

- The donations / prompts / templates tree is published alongside each image build as an `irene-assets-<target>`
  artifact. Extract it into your host assets directory once.
- Speech models are **not** in the image; they download into the same directory on first boot and stay there.

| Env var | Default | Purpose |
|---|---|---|
| `IRENE_CONFIG_FILE` | `/app/runtime-config.toml` | The active config (baked; override by mounting). |
| `IRENE_ASSETS_ROOT` | `/app/assets` | Root for models, cache, credentials, and the bundled assets. |

The container runs as a non-root user and exposes the web API on **port 6000**.

## Running

**Satellite server** (aarch64 / armv7) — recognition + synthesis over the web API, no audio device needed:

```bash
docker run --rm -p 6000:6000 \
  -v ./assets:/app/assets \
  ghcr.io/droman42/wb-mqtt-voice-aarch64:latest
```

**Standalone** (x86_64) — drives the local microphone and speaker, so it needs the host sound devices:

```bash
docker run --rm -p 6000:6000 \
  --device /dev/snd \
  -v ./assets:/app/assets \
  ghcr.io/droman42/wb-mqtt-voice-standalone:latest
```

Both serve the full web API on 6000 alongside their primary input.

## Compose

```yaml
services:
  irene:
    image: ghcr.io/droman42/wb-mqtt-voice-aarch64:latest
    ports: ["6000:6000"]
    volumes: ["./assets:/app/assets"]
    restart: unless-stopped
```

## Building locally

The published images cover the standard targets; build locally to change the baked profile or develop a new
one. The build context is the repo root, and each Dockerfile lives in `docker/`:

```bash
# standalone / x86_64
docker build -f docker/Dockerfile.x86_64 \
  --build-arg CONFIG_PROFILE=standalone-x86_64 -t irene-standalone .

# aarch64 — needs buildx for cross-builds
docker buildx build --platform linux/arm64 -f docker/Dockerfile.aarch64 \
  --build-arg CONFIG_PROFILE=embedded-aarch64 -t irene-aarch64 .

# armv7
docker buildx build --platform linux/arm/v7 -f docker/Dockerfile.armv7 \
  --build-arg CONFIG_PROFILE=embedded-armv7 -t irene-armv7 .
```

`CONFIG_PROFILE` names a file in `configs/`. To see what a profile will pull before building:

```bash
uv run python -m irene.tools.build_analyzer --config configs/standalone-x86_64.toml --docker
uv run python -m irene.tools.build_analyzer --list-profiles
```

## How the image is built

Each Dockerfile uses three stages:

1. **analyzer** — runs the build analyzer on `CONFIG_PROFILE` → the precise dependency and system-package list.
2. **builder** — creates a virtual environment and installs only those system and Python dependencies into it.
3. **runtime** — a lean image that copies the finished environment, the baked config, a non-root user, and a
   health check; nothing build-only is left behind.

The armv7 and aarch64 builds pull their wheels from PiWheels so native packages don't compile from source. The
spaCy language models are installed as packaged wheels at build time (unlike the runtime-downloaded speech
models), so each image carries only the model tier its profile actually loads rather than every language and
size.

A new config profile needs no Dockerfile change — add a `.toml` to `configs/`, check it with the analyzer, and
pass its name as `CONFIG_PROFILE`. New providers are entry-point-discovered, so they need no Dockerfile change
either (see [adding a model](howto-new-model.md)).
