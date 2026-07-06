# eval/ — declarative system, CLI & UX tests for wb-mqtt-voice

Pure-YAML test cases. All execution logic lives in the shared **`eval-commons`** package
(sibling repo: `../../eval-commons`) — see its `ARCHITECTURE.md`. This directory carries only
YAML + a thin Makefile (deployment glue, no test logic).

> **Writing a new test?** Start with the recipe: **[How to add a test](../docs/guides/howto-new-test.md)**
> (and [recording fixtures](fixtures/README.md)). This file is the reference; that guide is the walkthrough.

## Layout

```
eval/
  Makefile                     # the only entrypoint — owns the (target × config × lang) matrix
  cli.promptfooconfig.yaml     # CLI contract tests (argparse console scripts)
  ws.promptfooconfig.yaml      # streaming-ASR system + UX tests over /ws/audio (ru + en cases)
  trace.promptfooconfig.yaml   # offline golden-trace regression (per-language)
  profiles/
    targets/{local,wb7}.env    # WHERE the SUT is  → WS_AUDIO_URL, HEALTH_URL, MQTT_*
    configs/*.env              # WHICH config it runs (local bring-up) → IRENE_CONFIG_FILE
  fixtures/<lang>/             # audio fixtures per language — committed test inputs (see fixtures/README.md)
  traces/<lang>/               # golden traces per language (see traces/README.md)
```

## The three run axes (all external to the test YAML)

| Axis | Selects | Mechanism | Applies to |
|---|---|---|---|
| **TARGET** | `local` vs `wb7` (remote controller) | `profiles/targets/<TARGET>.env` → `{{env.WS_AUDIO_URL}}` | system suites (ws) |
| **CONFIG** | `embedded-armv7[-en]` / `embedded-aarch64[-en]` / `standalone[-en]` / `custom` | `profiles/configs/<CONFIG>.env` → `IRENE_CONFIG_FILE` | local SUT bring-up |
| **EVAL_LANG** | `ru` (default) / `en` | derived from the CONFIG name (`*-en` → `en`); picks `fixtures/<lang>/` + the `language` case filter | ws + trace suites |

Test cases never change across combinations. `TARGET` swaps the endpoint; `CONFIG` is what the SUT
runs (for `wb7`, whatever is deployed); `EVAL_LANG` picks which language's cases + fixtures run — cases
are duplicated per language and tagged, so one run = one language. `EVAL_LANG` tracks `CONFIG` (a `-en`
config runs the English set) unless overridden, e.g. `EVAL_LANG=en` for a remote English SUT.

## Surfaces

| Config | Kind | Needs running | Needs key | Needs fixtures | Status |
|---|---|---|---|---|---|
| `cli.promptfooconfig.yaml` | CLI contracts | nothing | no | no | ✅ **passing (5/5)** |
| `ws.promptfooconfig.yaml` (system) | ASR + intent | Irene on the target | no | yes (WAV) | ✅ ru live + en live (WER ✓ + intent ✓; `make ws CONFIG=embedded-armv7-en` = 4/4, Moonshine ASR) |
| `ws.promptfooconfig.yaml` (ux) | DeepSeek judge | Irene on the target | `DEEPSEEK_API_KEY` | yes (WAV) | ✅ ru live; en live (rubrics validated; fixtures recorded) |
| `trace.promptfooconfig.yaml` | offline golden replay | nothing (models present) | no | traces (JSON) | ✅ ru + en golden green (`make replay CONFIG=embedded-armv7-en`) |
| `device.promptfooconfig.yaml` | utterance → canonical DeviceCommand (producer contract) | Irene + the mock bridge (`make device-auto` wires both) | tier 2 only | no (cases GENERATED from the pinned crossover fixtures) | ✅ tier 1 (default gate): 47/47; tier 2 (`TIER=2 NLU=llm`): 5/8 — red = the deferred relative-adjustment trio («поярче»/«потеплее») |

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
make cli                                        # CLI contracts — runs today, no prerequisites
make device-auto                                # producer contract suite (tier 1 = the green gate): mock bridge + SUT up → suite → teardown
make device-auto TIER=2 NLU=llm                 # the hard-phrasing scoreboard: tier-2 fixtures with the QUAL-50 LLM NLU tier in the cascade (needs DEEPSEEK_API_KEY)
make device TARGET=local                        # ... against an already-running SUT wired to the mock bridge
make record                                     # record the ru WS fixtures (mic; see fixtures/README.md)
make record EVAL_LANG=en                        # record the en fixtures
make ws  TARGET=local CONFIG=embedded-armv7     # Russian WS suite (start the SUT first: make serve)
make ws  TARGET=local CONFIG=embedded-armv7-en  # English WS suite (EVAL_LANG=en derived)
make ws  TARGET=local TRACE=1                    # ... and keep each FAILING case's execution trace (see below)
make ws  TARGET=wb7                              # WS suite vs Irene on the WB7 controller
make ux  TARGET=local CONFIG=embedded-armv7-en   # only the DeepSeek-judged UX cases (en)
make serve CONFIG=embedded-armv7                 # bring Irene up locally with a config (foreground)
make compare CONFIGS="embedded-armv7 standalone" # WER/UX comparison across configs (local bring-up loop)
make view                                        # results UI
```

For model comparison, `make compare` writes `results-ws-<target>-<config>.json` per config so you
can diff WER side by side. Keep the `reference:` fixed; expect WER to differ per model — that's the
measurement (so read the scores, don't lean on a single hard threshold during comparison).

**Debugging a WS failure (`TRACE=1`).** Start the SUT with tracing writing into `TRACES_DIR`
(default `traces/run`; e.g. `[trace] traces_dir = ".../eval/traces/run"` in its config), then
`make ws TRACE=1`. The SUT tags each response with its trace `request_id`; afterwards the harness
keeps only the **failing** cases' traces under `traces/failures/` (the rest are pruned) — the
*actual* failing run, not a re-run that may not reproduce a flaky failure. Replay one to debug it:

```bash
irene-replay-trace -t traces/failures/<request_id>.json --listen --step   # hear it, step each stage
```

(For the offline replay tier, `irene-replay-trace --record-out <dir>` keeps the replayed trace on a
mismatch — the replay already diffs `{text, success, actions}` and names the diverging field.)

**One golden trace → both tiers (`--extract-wav`).** A golden audio trace carries its captured audio,
so it serves *record once, test twice*: replay it offline **and** derive the WS WAV fixture from it
instead of re-recording with a mic.

```bash
irene-replay-trace -t traces/<id>.json --extract-wav fixtures/<case>.wav   # 16 kHz mono PCM
```

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
- **The harness runs cache-disabled** (`PROMPTFOO_CACHE_ENABLED=false`, set in the Makefile). Every
  surface here is a *live* test — CLI argparse, the WS suite against a running SUT, the DeepSeek
  judge — so a cached response can only mask reality. A cached transient failure once replayed for
  every later run and read as a persistent SUT bug; never re-enable the cache for these suites.
- **`irene-config-validate` writes its report (including errors) to STDOUT, not stderr, and exits
  1 on invalid/missing config.** Assert on `stdout` + `exit_code`, never `stderr`.
- **The two axes (TARGET, CONFIG) belong in `profiles/*.env`, never in a test case.** Test YAML
  stays identical across local/wb7 and across configs. If you're tempted to fork a test per
  target/config, that's the signal to use a profile instead.

## Notes / TODO

- **Fixtures are recorded + committed** — `fixtures/{timer_10min,light_unreachable}.wav`, 16 kHz mono PCM16. Re-record
  with **`make record`** (`make setup-record` once first; see `fixtures/README.md`) only if you change the spoken reference.
- **Intent name** `timer.set` is **confirmed against a live run** — the intent case passes.
- **ASR/WER tier works.** Offline ASR (sherpa_onnx/vosk) emits no streaming `partial`s, but the SUT already surfaces
  the *recognized speech* at `metadata.audio_processing.transcribed_text` on the batch path — the provider reads that
  (falling back to a partial, then the reply text), so the WER assertion scores ASR accuracy, not the assistant's
  reply. Confirmed live: `«поставь таймер на десять минут»` → WER 0.
- **DeepSeek-as-judge on Russian is CALIBRATED** (2026-07-02): a 20-case human-labeled set
  (native speaker) measured 16/16 agreement, Cohen's κ = 1.0 in-sample against the shipped shared
  rubrics — see eval-commons `examples/ru-ux-calibration/` for the set, method and caveats.
  Russian UX pass/fail is CI-trustworthy; re-run the calibration set after **any** rubric edit
  (a past fix silently regressed a neighboring criterion), and note the English rubrics carry the
  same structure but are uncalibrated. The live UX cases reference the shared rubric files
  directly (`file://…/shared/rubrics/{ru,en}/*.txt`) — edit them there, never inline.
- **`serve`/`compare`** launch Irene with `uv run irene-webapi --port 6000`; adjust the command in
  the Makefile if your runner takes the config/port differently.
- **Next refinement:** once the WS suite has run once, the inline cases can be split into
  `tests/ws/*.yaml` (one file per scenario). Kept inline for now — only a handful of cases, and it
  avoids assumptions about promptfoo's external-test-file path resolution until verified live.
- **Future surfaces (smart-home / bridge, ARCH-26 §14):** the boundary is the canonical `DeviceCommand`,
  so the contract is tested from both sides against shared `{utterance → canonical}` fixtures + a committed
  golden bridge catalog (all in `eval-commons`), no live bridge needed. A new `device_command` capture
  provider drives an utterance and returns Irene's emitted command for assertion (Irene = producer;
  the bridge repo runs the consumer half). Full end-to-end against a running bridge (REST via promptfoo's
  `https` provider) is a later, separate surface. Tracked as TEST-17 (contract bundle) + TEST-18 (provider).
```
