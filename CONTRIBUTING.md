# Contributing

Two principles first, inherited from the project's roots and still true:

- Build what you'll actually use, and run it on a real system before sending it.
- Prefer additive changes. The architecture is built so most contributions — a new command, a new engine, a
  new language — need no core changes at all.

## Setup

```
uv sync --project backend
```

Then run it (CLI, web API, or the config UI) per the [quickstart](docs/QUICKSTART.md). Start from a
[lightweight profile](docs/guides/configuration.md#profiles) so you don't pull heavy models you don't need.

## Most changes are additive

Before touching the core, check whether what you want is one of these — each is a self-contained guide:

- **[Add an intent](docs/guides/howto-new-intent.md)** — a new command (a method plus a donation), or a
  whole new handler.
- **[Add a model](docs/guides/howto-new-model.md)** — a new engine for wake word, VAD, ASR, TTS or LLM.
- **[Add a language](docs/guides/howto-new-language.md)** — donations, config, and the models to swap.
- **[Add a test](docs/guides/howto-new-test.md)** — a declarative YAML case (CLI contract, streaming-ASR
  system, or judged UX), and recording its audio fixture.

If you aren't sure where a change belongs, the [architecture overview](docs/architecture/overview.md) maps
the pieces.

## Contracts and pinned copies

Anything this repo shares with a sibling — the wire protocol, the bridge's device catalog, the
problem-report format — is a **contract** with a version stamp and a registry:
[`contracts/README.md`](contracts/README.md) indexes what this repo owns and what it consumes.
The consumed copies under `contracts/pins/` are verbatim, hash-sealed snapshots of another
repo's artifacts: **never edit them by hand** — they move only through `make -C eval repin`,
followed by the conformance test each pin names.

## Tests and evaluation

Unit and conformance tests live in `backend/tests/` and run with `uv run --project backend pytest`. The
declarative system suites (CLI contracts, streaming-ASR, device commands, judged UX) live in
[`eval/`](eval/README.md) — read that README before touching anything test-related; the
execution logic deliberately lives in a sibling repo, and `eval/` here carries only the YAML.

## Documentation is part of done

Every user-facing document is registered in [`docs/manifest.json`](docs/manifest.json) — if
your change alters behavior a registered doc describes, update the doc in the same change
(diagrams too: edit the `.dot` source and regenerate the image). A new user-facing doc needs
a manifest node in the same commit — the test suite fails otherwise.

## Coding rules

These aren't style preferences — each is enforced by a CI gate (below):

1. **Dependencies point inward (the hexagon).** The domain reaches no outer layer, adapters don't import the
   application, provider families stay independent. A backwards import fails the build. See the
   [architecture overview](docs/architecture/overview.md).
2. **No `TYPE_CHECKING` import guards.** If a type is importable at runtime, import it at module top and
   annotate with the real symbol. An `if TYPE_CHECKING:` block is a band-aid for an import cycle — break the
   cycle (move the shared type down / use a port), don't hide the import from the runtime.
3. **pyright stays at zero, with no suppressions.** Fix the code; never add a rule suppression to
   `backend/pyrightconfig.json`.
4. **Heavy libraries stay optional.** A provider's third-party deps go behind a `pyproject` extra and are
   declared on the provider — never imported at module top level for a provider nobody configured. This is
   what keeps a build small (see the [build system](docs/guides/build-system.md)).
5. **Donations are the source of truth.** An intent's phrasing, parameters and wiring live in its donation,
   not scattered through code — change the donation, not three files.
6. **config-ui stays green.** If you change a backend contract (donation schema, config schema, a REST
   endpoint), update config-ui in the same change so its workflow stays clean.

## Gates

CI runs two workflows on every push / PR, and **every gate hard-fails**. Run them locally before you push.

**Backend** (`.github/workflows/backend-health.yml`) — run from the repo root:

| Gate | Command |
|---|---|
| Hexagon import contracts | `cd backend && uv run lint-imports` |
| No `TYPE_CHECKING` guards | `uv run --project backend check-no-type-checking locveil_voice` |
| Type checking (0 errors) | `cd backend && uv run pyright` |
| All config profiles valid | `uv run --project backend python -m locveil_voice.tools.build_analyzer --validate-all-profiles` |
| All config files valid (schema + completeness) | `uv run --project backend python -m locveil_voice.tools.config_validator_cli --config-dir config/` |
| Provider dependencies resolve | `uv run --project backend python -m locveil_voice.tools.dependency_validator --validate-all` |

CI installs `uv sync --project backend --frozen --all-extras` so pyright can resolve every provider's optional imports.
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
