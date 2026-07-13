# Build system

A capable voice assistant can pull in some heavy company — PyTorch and Whisper for ASR, spaCy for NLU, ONNX
runtimes, TFLite for wake words. A text-only or API-only deployment shouldn't have to carry any of it. So in
Irene **the configuration decides the dependencies**, not a single monolithic requirements list.

## Dependencies are declared, per provider

Nothing heavy is a core dependency. Each provider **declares its own** — `get_python_dependencies` returns the
`pyproject.toml` **extra group(s)** it needs *by name* (e.g. `["advanced-asr"]`, not a raw `package>=x` spec),
and `get_platform_dependencies` (system libraries, per OS) — and the matching libraries sit behind those
optional **extras** in `pyproject.toml` (`advanced-asr`, `tts`, `voice-trigger`, `asr-onnx`, …). Install the
core and you have a working text assistant; add an extra and you add that capability.

## A build is computed from a config

You don't hand-pick extras. The **build analyzer** reads a config and works out exactly what it needs:

![Minimal, config-driven builds](../images/build-system.png)

```
uv run --project backend python -m locveil_voice.tools.build_analyzer --config config/embedded-armv7.toml
```

It walks the enabled components and providers, collects their declared dependencies and the intent JSON files
they require, and produces the minimal set for that profile — which is what a container build then installs.
A `embedded-armv7.toml` deployment never lists torch; a voice profile lists only the speech libraries it actually
configured.

## Why it runs lean, too

The same mechanism that keeps the build small keeps the running process small. Providers are loaded through
**entry-points**, and only the ones the config enables are ever imported. A provider you didn't configure is
never touched — so its heavy libraries aren't imported, aren't in memory, and (thanks to the analyzer) need
not be installed at all. Configuration is the single lever for both.

## Tooling

Two console scripts back the build system:

- `locveil-voice-build-analyze` (= `python -m locveil_voice.tools.build_analyzer`) — turn a config into its minimal
  requirements (used above, and by the Docker builds).
- `locveil-voice-dependency-validate` (= `python -m locveil_voice.tools.dependency_validator`) — check that a provider's
  declared dependencies resolve on a target platform: `--validate-all` sweeps every entry-point, `--platforms`
  cross-checks several at once, `--json` for CI.

## Deployment

- **Docker** — multi-platform images that bake in only a profile's dependencies. See
  [Docker builds](build-docker.md).
- **As a systemd service** — point a unit at the venv's `webapi_runner`:

  ```ini
  [Unit]
  Description=Irene Voice Assistant
  After=network.target sound.target

  [Service]
  Type=simple
  User=locveil
  Group=audio
  WorkingDirectory=/opt/locveil-voice
  ExecStart=/opt/locveil-voice/.venv/bin/python -m locveil_voice.runners.webapi_runner
  Restart=always

  [Install]
  WantedBy=multi-user.target
  ```

  Then `sudo systemctl daemon-reload && sudo systemctl enable --now locveil-voice`.

## External provider packages

A provider doesn't have to live in this repo. Ship a provider class in your own package, declare it under the
matching `locveil_voice.providers.<family>` entry-point in *your* `pyproject.toml`, and Irene discovers it like any
built-in — validate it with `locveil-voice-dependency-validate`, then enable it in config. The class shape is the
[provider recipe](howto-new-model.md).
