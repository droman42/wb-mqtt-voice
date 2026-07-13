# Docker builds

Irene ships as a family of Docker images: one per deployment role, CPU architecture, and **language**. Each
image installs only what its config profile needs — the [build analyzer](build-system.md) turns the profile
into a minimal dependency set at build time — and bakes that one profile in. Russian images carry the
original, unsuffixed names; English variants add an `-en` suffix:

| Image | Architecture | Role |
|---|---|---|
| `locveil-voice-standalone` / `-standalone-en` | x86_64 | Full local voice box — mic → wake-word → ASR → intent → TTS → playback. |
| `locveil-voice-aarch64` / `-aarch64-en` | aarch64 (WB8.5 / Pi) | Satellite server — ASR + intent + TTS for ESP32 satellites; no local mic. |
| `locveil-voice-armv7` / `-armv7-en` | armv7 (WB7) | Satellite server, smaller models; no local mic. |
| `locveil-voice-ui` | multi-arch (one manifest) | The configuration editor as a static site (see below). |

On the satellites the ESP32 owns the microphone, voice activity detection, wake-word, and playback; the
container only does recognition and speech synthesis and streams the reply back over the web API. The
standalone image is the one that drives audio hardware itself.

## Published images

Each image is published to the GitHub Container Registry and tagged `latest`, `sha-<short>`, and
`v<date>-<sha>` (pin the date tag to roll back):

```bash
docker pull ghcr.io/locveil/locveil-voice-standalone:latest      # Russian
docker pull ghcr.io/locveil/locveil-voice-armv7-en:latest        # English
docker pull ghcr.io/locveil/locveil-voice-ui:latest              # configuration editor
```

Publishing is a deliberate act, not a side effect of pushing code: every push runs the fast health checks,
and images are built only when the CI workflow is dispatched manually — one dispatch builds the whole
matrix by default (all architectures × both languages + the UI), and each image is gated on its green
checks. Narrow a dispatch with the workflow inputs, e.g.:

```bash
gh workflow run CI                                    # everything
gh workflow run CI -f targets=armv7 -f languages=en -f build_ui=false
```

Every published backend image is verified at build time to ship an **empty** `/app/assets` — speech models
are never baked in — and its size is checked against a per-target budget and reported in the run summary.

## Config and assets

The config profile is **baked into the image** at `/app/runtime-config.toml` — you do not supply a config
file at run time. To change settings, mount your own file over it or point `LOCVEIL_VOICE_CONFIG_FILE` at a mounted
path.

Assets — donation phrasings, prompts, templates, and the downloaded speech models — live **outside** the
image under a single assets root, so they survive upgrades and can be shared between containers. Mount a host
directory at `/app/assets`:

- The donations / prompts / templates tree lives in this repository under `assets/` and travels by
  `git pull`: on a controller, `ops/update.sh` syncs it from the checkout into the assets directory as part of
  every update (see [`ops/INSTALL.md`](../../ops/INSTALL.md)); elsewhere, copy it once with
  `rsync -a assets/ /path/to/assets/` and refresh after pulling.
- Speech models are **not** in the image; they download into the same directory on first boot and stay there.
- Runtime state the assistant writes (`models/`, `cache/`, `state/`, `traces/`) lives under the same root —
  never delete it as part of an assets refresh.

| Env var | Default | Purpose |
|---|---|---|
| `LOCVEIL_VOICE_CONFIG_FILE` | `/app/runtime-config.toml` | The active config (baked; override by mounting). |
| `LOCVEIL_VOICE_ASSETS_ROOT` | `/app/assets` | Root for models, cache, credentials, and the bundled assets. |

The container runs as a **non-root user (uid 1000)** and exposes the web API on **port 8080**. The
uid is the part that matters: it is what the host sees on bind-mounted directories, so any
directory you mount for models, logs, or state must be owned by uid 1000 or the container cannot
write to it. Its healthcheck polls `/health` on that port, with a long start-period because the
first boot downloads the speech models.

## Running

**Satellite server** (aarch64 / armv7) — recognition + synthesis over the web API, no audio device needed:

```bash
docker run --rm -p 8080:8080 \
  -v ./assets:/app/assets \
  ghcr.io/locveil/locveil-voice-aarch64:latest
```

**Standalone** (x86_64) — drives the local microphone and speaker, so it needs the host sound devices:

```bash
docker run --rm -p 8080:8080 \
  --device /dev/snd \
  -v ./assets:/app/assets \
  ghcr.io/locveil/locveil-voice-standalone:latest
```

Both serve the full web API on 8080 alongside their primary input.

## Compose and controller deployment

The repository ships a ready deployment under [`ops/`](../../ops/INSTALL.md): a compose file (Irene plus the
optional configuration editor behind a compose profile), a ten-line update script that syncs assets and pulls
images, and a systemd unit — on a Wirenboard the whole loop is `git pull && ./ops/update.sh`. For a quick
ad-hoc compose elsewhere:

```yaml
services:
  irene:
    image: ghcr.io/locveil/locveil-voice-aarch64:latest
    ports: ["8080:8080"]
    volumes: ["./assets:/app/assets"]
    restart: unless-stopped
```

## Building locally

The published images cover the standard targets; build locally to change the baked profile or develop a new
one. The build context is the repo root, and each Dockerfile lives in `docker/`:

```bash
# standalone / x86_64
docker build -f docker/Dockerfile.x86_64 \
  --build-arg CONFIG_PROFILE=standalone-x86_64 -t locveil-voice-standalone .

# aarch64 — needs buildx for cross-builds
docker buildx build --platform linux/arm64 -f docker/Dockerfile.aarch64 \
  --build-arg CONFIG_PROFILE=embedded-aarch64 -t locveil-voice-aarch64 .

# armv7
docker buildx build --platform linux/arm/v7 -f docker/Dockerfile.armv7 \
  --build-arg CONFIG_PROFILE=embedded-armv7 -t locveil-voice-armv7 .
```

`CONFIG_PROFILE` names a file in `config/`. To see what a profile will pull before building:

```bash
uv run --project backend python -m locveil_voice.tools.build_analyzer --config config/standalone-x86_64.toml --docker
uv run --project backend python -m locveil_voice.tools.build_analyzer --list-profiles
```

## The configuration editor image

The donation/configuration editor ships as `locveil-voice-ui`: a small nginx container serving the built
static app on **port 3000**, published as a single multi-arch manifest (the same tag runs on x86_64, aarch64,
and armv7). It is not part of the standard controller deployment — run it wherever convenient when you need
to edit donations or configuration:

```bash
docker run --rm -p 3000:3000 ghcr.io/locveil/locveil-voice-ui:latest
```

By default the app talks to Irene on **the same host it is served from**, port 8080. Point it elsewhere with
the `API_BASE_URL` environment variable:

```bash
docker run --rm -p 3000:3000 -e API_BASE_URL=http://192.168.110.250:8080 \
  ghcr.io/locveil/locveil-voice-ui:latest
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

A new config profile needs no Dockerfile change — add a `.toml` to `config/`, check it with the analyzer, and
pass its name as `CONFIG_PROFILE`. New providers are entry-point-discovered, so they need no Dockerfile change
either (see [adding a model](howto-new-model.md)).
