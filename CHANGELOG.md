# Changelog

## 15.0.0 — the revival release *(unreleased — tag pending hardware validation)*

The first release of the revived Irene: a ground-up modernization of the
[janvarev/Irene-Voice-Assistant](https://github.com/janvarev/Irene-Voice-Assistant) lineage,
rebuilt as an async, configuration-driven, hexagonal-architecture voice assistant. Russian-first,
English supported, offline by default.

### Architecture

- **Hexagonal core (ports & adapters).** Speech engines, transports and smart-home back-ends are
  swappable adapters around a pure intent domain; dependencies point inward and the layering is
  machine-enforced. See [Architecture](docs/architecture/overview.md).
- **One unified pipeline, many entries.** Microphone, ESP32 satellite stream, uploaded audio, web
  API and CLI all converge on the same voice-trigger → ASR → text → NLU → intent → reply pipeline,
  with stages skipped per entry point.
- **Configuration-driven composition.** Components and providers load only when configured — a
  deployment is exactly as large as its config. Curated first-run config
  (`configs/config-example.toml`), documented reference (`configs/config-master.toml`), and baked
  profiles for armv7 / aarch64 / x86_64 targets.

### Understanding

- **Donation-driven NLU.** All recognition vocabulary lives in declarative per-handler JSON
  donations (phrases, parameters, localized choice surfaces) — validated against a schema and a
  contract-wiring gate in CI. A fast keyword/pattern matcher carries the common cases; an optional
  LLM tier (DeepSeek out of the box) recovers fuzzy phrasings and colloquialisms; recognition is
  transliteration-tolerant («ютуб» finds YouTube).
- **Multi-turn dialogs.** Missing-parameter clarification resumes the original command with your
  answer; a fresh command spoken instead of an answer is detected and executed, not glued on.
- **Russian morphology throughout** — inflected device names, compound numerals, natural spoken
  date/time; English works alongside with per-language donations and templates.

### Capabilities

- **Smart-home control** through the companion
  [wb-mqtt-bridge](https://github.com/droman42/wb-mqtt-bridge): lights, covers, climate
  (including HVAC modes), brightness, volume, playback, inputs and apps, scenarios, sensor
  readings — resolved against a live device catalog, addressed per device or per room, honest
  clarifying questions on ambiguity. See the [smart-home guide](docs/guides/smart-home.md).
- **Timers and reminders with durable delivery**: fire-and-forget actions are keyed to the room
  (not the conversation), survive restarts, apologize when late, and never fail silently.
- **Problem reporting by voice** («сообщи о проблеме»): describe an issue in your own words and
  Irene files it privately with the logs and context a developer needs — offline-tolerant, with
  automated triage on the receiving side. When the smart home is connected, the report also
  carries the bridge's own evidence snapshot (recent device commands, live states). See the
  [problem-reporting guide](docs/guides/problem-reporting.md).
- **Voice satellite support**: ESP32 room nodes stream finished utterances over WebSocket with
  server-side wake-word packs (Russian «Ирина» shipped) and per-room reply routing.

### Operations

- **Docker images on GHCR** for all three targets (Russian and English variants) plus the
  browser configuration UI — models are never baked into images (they download into a mounted
  assets root on first use), sizes are budgeted in CI, and controller deployment is
  pull-based (`ops/`).
- **Tracing & replay**: any request can be recorded to a self-contained file and replayed
  through the pipeline for debugging or regression listening.
- **Layered test nets**: a ~1300-case unit suite, offline-hermetic smoke end-to-end tests, and a
  declarative eval suite (CLI contracts, streaming ASR, device-command producer tests against a
  pinned bridge contract) — all CI-gated, together with pyright at zero errors and
  import-boundary contracts.

### Compatibility

- Python 3.11+, `uv`-managed. Configuration is TOML (`-c configs/config-example.toml` to start).
- The v13-era plugin API of the original lineage is not compatible; skills are now intent
  handlers with JSON donations (see [the how-to](docs/guides/howto-new-intent.md)).
