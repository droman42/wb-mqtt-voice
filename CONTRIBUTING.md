# Contributing

Two principles first, inherited from the project's roots and still true:

- Build what you'll actually use, and run it on a real system before sending it.
- Prefer additive changes. The architecture is built so most contributions — a new command, a new engine, a
  new language — need no core changes at all.

## Setup

```
uv sync
```

Then run it (CLI, web API, or the config UI) per the [quickstart](docs/QUICKSTART.md). Start from a
[lightweight profile](docs/guides/configuration.md#profiles) so you don't pull heavy models you don't need.

## Most changes are additive

Before touching the core, check whether what you want is one of these — each is a self-contained guide:

- **[Add an intent](docs/guides/howto-new-intent.md)** — a new command (a method plus a donation), or a
  whole new handler.
- **[Add a model](docs/guides/howto-new-model.md)** — a new engine for wake word, VAD, ASR, TTS or LLM.
- **[Add a language](docs/guides/howto-new-language.md)** — donations, config, and the models to swap.

If you aren't sure where a change belongs, the [architecture overview](docs/architecture/overview.md) maps
the pieces.

## The boundaries that matter

Two rules keep the system maintainable, and both are enforced rather than merely requested:

- **Respect the hexagon.** Dependencies point inward, across a port — the domain reaches no outer layer,
  adapters don't import the application, and so on. The boundaries are checked by `lint-imports` (nine
  contracts); a backwards import fails the build. See the [overview](docs/architecture/overview.md).
- **Keep heavy things optional.** A new engine's libraries go behind an extra and are declared on the
  provider — never imported at module top level for a provider nobody configured. This is what lets Irene
  run small (see the [build system](docs/guides/build-system.md)).

And one source-of-truth rule: an intent's phrasing, parameters and wiring live in its **donation**, not
scattered through code. Change the donation, not three files.

## Before you open a PR

Run the gates locally — the same ones CI runs:

```
uv run pytest                 # tests
lint-imports                  # the hexagonal contracts
irene-config-validate         # config schema
irene-dependency-validate     # provider dependencies resolve
```

## Code style

Match the code around you. There is no house formatter to appease, and **mass "reformat / reorder imports /
PEP-8 everything" pull requests won't be merged** — they bury real changes in noise. Keep a diff to the
change you are actually making.
