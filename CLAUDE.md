# wb-mqtt-voice — agent notes

## Testing & evaluation

Declarative tests (CLI contracts, streaming-ASR system tests, Russian UX judging) live in
**[`eval/`](eval/README.md) — read that README before touching anything test-related.**

Key things it establishes (don't rediscover the hard way):
- All test *execution logic* (providers, scorers, judge) lives in the sibling repo
  **`../eval-commons`** — this repo carries only YAML + a thin `eval/Makefile`. Change behavior
  there, not here.
- Run tests via `make` from `eval/` (it wires the `uv` venv + global `promptfoo`), e.g.
  `make cli` (no prerequisites), `make ws TARGET=local|wb7`, `make ux`.
- Tests parameterize over two external axes — **TARGET** (local vs the WB7 controller) and
  **CONFIG** (which Irene config the SUT runs) — via `eval/profiles/*.env`. Never bake an
  endpoint or config into a test case.
- promptfoo env refs are `{{env.VAR}}`, not `${VAR}`.

Status: `make cli` passes; the WS/UX suites are pending recorded audio fixtures and Russian
judge calibration (see `eval/README.md` → Notes/TODO).
