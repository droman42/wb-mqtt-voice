# eval/ — declarative system, CLI & UX tests for wb-mqtt-voice

Pure-YAML test cases. All execution logic lives in the shared **`eval-commons`** package
(sibling repo: `../../eval-commons`) — see its `ARCHITECTURE.md`. This directory carries only
YAML + a thin Makefile (deployment glue, no test logic).

## Layout

```
eval/
  Makefile                     # the only entrypoint — owns the (target × config) matrix
  cli.promptfooconfig.yaml     # CLI contract tests (argparse console scripts)
  ws.promptfooconfig.yaml      # streaming-ASR system + UX tests over /ws/audio
  profiles/
    targets/{local,wb7}.env    # WHERE the SUT is  → WS_AUDIO_URL, HEALTH_URL, MQTT_*
    configs/*.env              # WHICH config it runs (local bring-up) → IRENE_CONFIG_FILE
  fixtures/                    # audio fixtures (git-ignored; see fixtures/README.md)
```

## The two run axes (both external to the test YAML)

| Axis | Selects | Mechanism | Applies to |
|---|---|---|---|
| **TARGET** | `local` vs `wb7` (remote controller) | `profiles/targets/<TARGET>.env` → `{{env.WS_AUDIO_URL}}` | system suites (ws) |
| **CONFIG** | `voice` / `standalone` / `embedded-*` / `custom` | `profiles/configs/<CONFIG>.env` → `IRENE_CONFIG_FILE` | local SUT bring-up |

Test cases never change across combinations. `TARGET` just swaps the endpoint; `CONFIG` is a
deployment concern (what the SUT runs) — for `wb7` it's whatever is deployed on the controller.

## Surfaces

| Config | Kind | Needs running | Needs key | Needs fixtures | Status |
|---|---|---|---|---|---|
| `cli.promptfooconfig.yaml` | CLI contracts | nothing | no | no | ✅ **passing (5/5)** |
| `ws.promptfooconfig.yaml` (system) | ASR + intent | Irene on the target | no | yes (WAV) | ⏳ pending fixtures |
| `ws.promptfooconfig.yaml` (ux) | DeepSeek judge | Irene on the target | `DEEPSEEK_API_KEY` | yes (WAV) | ⏳ pending fixtures + calibration |

## Setup (uv)

```bash
# 1. Runner — promptfoo, installed globally (Node CLI)
npm install -g promptfoo

# 2. Shared providers/assertions into the project venv (uv-managed; already present here)
make setup                       # = uv pip install --python ../.venv/bin/python -e ../../eval-commons

# 3. Env for the UX judge only
cp ../../eval-commons/examples/.env.example .env   # set DEEPSEEK_API_KEY
export $(grep -v '^#' .env | xargs)
```

The Makefile points promptfoo at the project venv (`PROMPTFOO_PYTHON`) and prepends the venv
`bin` to `PATH`, so the Python providers import `eval_commons` and the `irene-*` console
scripts resolve. No `activate` needed when going through `make`.

## Run

```bash
make cli                                   # CLI contracts — runs today, no prerequisites
make ws  TARGET=local                      # WS suite vs a locally-running Irene (start it first: make serve)
make ws  TARGET=wb7                        # WS suite vs Irene on the WB7 controller
make ux  TARGET=local                      # only the DeepSeek-judged UX cases
make serve CONFIG=voice                    # bring Irene up locally with a config (foreground)
make compare CONFIGS="voice standalone"    # WER/UX comparison across configs (local bring-up loop)
make view                                  # results UI
```

For model comparison, `make compare` writes `results-ws-<target>-<config>.json` per config so you
can diff WER side by side. Keep the `reference:` fixed; expect WER to differ per model — that's the
measurement (so read the scores, don't lean on a single hard threshold during comparison).

## Conventions & gotchas (read before editing)

These are non-obvious and have already caused (and cost) bugs — keep them in mind:

- **Provider/assertion code lives in `../../eval-commons`, NOT here.** This dir is pure YAML +
  the Makefile. To change *how* a test runs (a provider, the WER scorer, the judge), edit the
  sibling `eval-commons` repo — don't add Python here, and don't look for it here.
- **promptfoo env substitution is `{{env.VAR}}` (Nunjucks, resolved at config-load time) — NOT
  `${VAR}`.** `${VAR}` is passed through literally and fails silently. The endpoint must always
  come from `{{env.WS_AUDIO_URL}}` (set by the target profile), never hard-coded.
- **Run through `make`, not bare `promptfoo`.** The Makefile sets `PROMPTFOO_PYTHON` to the
  project venv and prepends its `bin` to `PATH`; without that, the Python providers can't import
  `eval_commons` and the `irene-*` console scripts don't resolve. promptfoo is a **global** npm
  install; everything Python is **`uv`**-managed in `../.venv`.
- **`irene-config-validate` writes its report (including errors) to STDOUT, not stderr, and exits
  1 on invalid/missing config.** Assert on `stdout` + `exit_code`, never `stderr`.
- **The two axes (TARGET, CONFIG) belong in `profiles/*.env`, never in a test case.** Test YAML
  stays identical across local/wb7 and across configs. If you're tempted to fork a test per
  target/config, that's the signal to use a profile instead.

## Notes / TODO

- **Record the fixtures** before the WS suite can run — `fixtures/{timer_10min,light_unreachable}.wav`,
  16 kHz mono PCM16 (see `fixtures/README.md`). This is the only blocker for the system/UX surfaces.
- **Intent name** in the intent case is a placeholder (`timer.set`) — confirm against a live run.
- **DeepSeek-as-judge on Russian is unvalidated.** Hand-score a few replies and check agreement
  before trusting UX pass/fail in CI (eval-commons `ARCHITECTURE.md` §7.1). Treat UX verdicts as
  indicative for now.
- **`serve`/`compare`** launch Irene with `uv run irene-webapi --port 6000`; adjust the command in
  the Makefile if your runner takes the config/port differently.
- **Next refinement:** once the WS suite has run once, the inline cases can be split into
  `tests/ws/*.yaml` (one file per scenario). Kept inline for now — only a handful of cases, and it
  avoids assumptions about promptfoo's external-test-file path resolution until verified live.
- **Future surfaces:** the bridge smart-home path (REST via promptfoo's native `https` provider;
  retained `bridge/catalog/version` via `eval-commons`' `mqtt_provider`) lands as an `http`/`mqtt`
  config beside these — zero extra shared code.
```
