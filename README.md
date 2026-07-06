# Irene

An offline-first voice assistant for the home — speech in, intents out, no cloud round-trip by
default. It runs locally on its own and couples to a smart home over MQTT when you want it to.

Russian-first, English supported. Version 15.0.0 · Python 3.11+ · MIT.

> **Status — pre-release, under active development.** The architecture is settled and the core works
> (CLI and web API, intent handling, timers, smart-home control through
> [wb-mqtt-bridge](docs/guides/smart-home.md), the browser config UI), and Docker images publish to
> GHCR. The ESP32 voice satellite and on-device deployment await hardware bring-up.
>
> First run: `uv run irene-cli -c configs/config-example.toml` — see the
> [Quickstart](docs/QUICKSTART.md).

## Highlights

- **Offline by default.** The whole text-and-intent pipeline runs with no internet and no API keys.
  Cloud LLM/ASR/TTS are opt-in, never required.
- **Understands, doesn't just match.** A cheap keyword matcher handles the common cases and spaCy
  handles the hard ones — both driven by declarative *donation* files instead of hardcoded phrasing.
- **Ships only what you use.** Components and providers are discovered via entry-points and loaded
  only when configured, so a deployment stays as small as its config.
- **Smart-home ready.** A small canonical command vocabulary pairs with `wb-mqtt-bridge` to drive
  Wirenboard and other gear — Irene stays device-agnostic; the bridge owns the hardware.
- **Reports its own bugs.** Say «сообщи о проблеме», describe it in your own words, and Irene files
  a ticket with the logs and context a developer needs — privately, offline-tolerant, no account.
- **One core, many front-ends.** CLI, a web API plus a browser config UI, and (planned) ESP32 voice
  satellites — all on one hexagonal core.

## Documentation

- **[Architecture](docs/architecture/overview.md)** — the hexagon, its ports and seams, and how
  everything fits (workflow, data-flow, components and providers).
  - **[Data models](docs/architecture/data-models.md)** — the objects a request travels as, and the
    three lifetimes: request, session (a room), durable.
  - **[Intents](docs/architecture/intents.md)** — orchestration, donations, parameter extraction,
    fire-and-forget vs synchronous handlers.
  - **[NLU](docs/architecture/nlu.md)** — donation-driven recognition; the cheap keyword matcher
    versus spaCy (and what spaCy actually is).
  - **[MQTT integration](docs/architecture/mqtt.md)** *(planned)* — canonical device commands and
    the `wb-mqtt-bridge` pairing.
  - **[ESP32 voice satellite](docs/architecture/esp32.md)** *(planned)* — streaming-audio room nodes
    and how they fit the whole picture.
- **[Asset management](docs/guides/asset-management.md)** — the models and caches, and how they're
  handled at runtime.
- **[Build system](docs/guides/build-system.md)** — how minimal, configuration-driven builds are
  put together.
- **[Docker builds](docs/guides/build-docker.md)** — multi-platform images that ship only what a
  config profile needs.
- **[Configuration](docs/guides/configuration.md)** — the TOML configuration model, end to end.
- **[Problem reporting](docs/guides/problem-reporting.md)** — «сообщи о проблеме»: describe an issue
  in your own words; Irene files it with everything a developer needs, privately.
- **[Smart-home control](docs/guides/smart-home.md)** — voice control of a Wirenboard home through
  wb-mqtt-bridge: rooms, devices, scenarios, and sensor questions.
- **[Tracing & replay](docs/guides/tracing.md)** — record a request to a self-contained file, then listen
  to it or replay it through the pipeline to debug and tune.
- **[Contributing](CONTRIBUTING.md)** — developer setup and how-tos: adding an intent, a model, a
  language, or a test.
- **[Quickstart](docs/QUICKSTART.md)** — install it, run it, talk to it.

## Acknowledgement

Inspired by [janvarev/Irene-Voice-Assistant](https://github.com/janvarev/Irene-Voice-Assistant),
the original Russian offline assistant of the same name.

## License

MIT — see [LICENSE](LICENSE).
