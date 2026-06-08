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

## Coding rules

These aren't style preferences — each is enforced by a CI gate (below):

1. **Dependencies point inward (the hexagon).** The domain reaches no outer layer, adapters don't import the
   application, provider families stay independent. A backwards import fails the build. See the
   [architecture overview](docs/architecture/overview.md).
2. **No `TYPE_CHECKING` import guards.** If a type is importable at runtime, import it at module top and
   annotate with the real symbol. An `if TYPE_CHECKING:` block is a band-aid for an import cycle — break the
   cycle (move the shared type down / use a port), don't hide the import from the runtime.
3. **pyright stays at zero, with no suppressions.** Fix the code; never add a rule suppression to
   `pyrightconfig.json`.
4. **Heavy libraries stay optional.** A provider's third-party deps go behind a `pyproject` extra and are
   declared on the provider — never imported at module top level for a provider nobody configured. This is
   what keeps a build small (see the [build system](docs/guides/build-system.md)).
5. **Donations are the source of truth.** An intent's phrasing, parameters and wiring live in its donation,
   not scattered through code — change the donation, not three files.
6. **config-ui stays green.** If you change a backend contract (donation schema, config schema, a REST
   endpoint), update config-ui in the same change so its workflow stays clean.

## Gates

CI runs two workflows on every push / PR, and **every gate hard-fails**. Run them locally before you push.

**Backend** (`.github/workflows/backend-health.yml`) — prefix each with `uv run`:

| Gate | Command |
|---|---|
| Hexagon import contracts | `lint-imports` |
| No `TYPE_CHECKING` guards | `python scripts/check_no_type_checking.py` |
| Type checking (0 errors) | `pyright` |
| All config profiles valid | `python -m irene.tools.build_analyzer --validate-all-profiles` |
| All config files valid (schema + completeness) | `python -m irene.tools.config_validator_cli --config-dir configs/` |
| Provider dependencies resolve | `python -m irene.tools.dependency_validator --validate-all` |

CI installs `uv sync --frozen --all-extras` so pyright can resolve every provider's optional imports.
**Deferred (not yet gating):** the full `pytest` suite (until the stale-test cleanup lands) and `black`/`isort`
(until the tree is formatted).

**Frontend** (`.github/workflows/frontend-health.yml`) — run inside `config-ui/`:

| Gate | Command |
|---|---|
| Type-check + lint + orphans | `npm run check` |
| Build | `npm run build` |
| Tests (vitest) | `npm run test` |

## Code style

Match the code around you. There is no house formatter to appease, and **mass "reformat / reorder imports /
PEP-8 everything" pull requests won't be merged** — they bury real changes in noise. Keep a diff to the
change you are actually making.
