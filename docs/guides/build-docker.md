# Docker builds

Irene builds multi-platform Docker images that install only what a chosen config profile needs — the
[build analyzer](build-system.md) turns the profile into a minimal dependency set at build time. Two
Dockerfiles, one per architecture:

- **`Dockerfile.x86_64`** — Python 3.11 on Debian slim; desktop, server, cloud.
- **`Dockerfile.armv7`** — Python 3.11 on Alpine; Raspberry Pi and embedded.

> **Status:** the Dockerfiles currently carry two build-blocking bugs (a missing `intent_validator` tool and
> an `ubuntu_packages` reference) — see [the Docker build review](../review/docker_build_review.md). The
> commands below are the intended procedure; they run once those fixes land (BUILD-5).

## Build

Each build takes a `CONFIG_PROFILE` build-arg (a file in `configs/`):

```bash
# x86_64 (default profile: minimal)
docker build -f Dockerfile.x86_64 --build-arg CONFIG_PROFILE=voice -t irene:voice-x86 .

# armv7 — needs buildx (default profile: embedded-armv7)
docker buildx build --platform linux/arm/v7 -f Dockerfile.armv7 \
  --build-arg CONFIG_PROFILE=embedded-armv7 -t irene:embedded-arm .
```

To see what a profile will pull before building:

```bash
uv run python -m irene.tools.build_analyzer --config configs/voice.toml --docker
uv run python -m irene.tools.build_analyzer --list-profiles
```

## Profiles

| Profile | For |
|---|---|
| `minimal` | text-only, ultra-light (the x86_64 default) |
| `api-only` | web API server |
| `voice` | full voice pipeline |
| `embedded-armv7` | Raspberry Pi / armv7 (the armv7 default) |
| `full` / `development` | everything (+ debugging) |

## How the image is built

Both Dockerfiles use three stages:

1. **analyzer** — runs the build analyzer on `CONFIG_PROFILE` → the precise dependency + system-package list.
2. **builder** — installs uv, then only those system and Python dependencies.
3. **runtime** — a minimal image with just the analyzed deps, a non-root user, and a health check.

armv7 additionally maps Debian package names to Alpine equivalents and pre-compiles bytecode.

## Runtime

- **Build arg:** `CONFIG_PROFILE` (default `minimal` on x86_64, `embedded-armv7` on armv7).
- **Env:** `IRENE_CONFIG_FILE` (default `/app/runtime-config.toml`), `PYTHONPATH=/app`.
- **Port:** `6000` — the web API (the container runs `webapi_runner --port 6000`).

```bash
docker run --rm -p 6000:6000 -v ./cache:/app/cache irene:voice-x86
```

## Compose

```yaml
services:
  irene:
    build:
      context: .
      dockerfile: Dockerfile.x86_64
      args: { CONFIG_PROFILE: voice }
    ports: ["6000:6000"]
    volumes: ["./cache:/app/cache"]
    restart: unless-stopped
```

A new config profile needs no Dockerfile change — add a `.toml` to `configs/`, check it with the analyzer, and
pass its name as `CONFIG_PROFILE`. New providers are entry-point-discovered, so they need no Dockerfile change
either (see [adding a model](howto-new-model.md)).
