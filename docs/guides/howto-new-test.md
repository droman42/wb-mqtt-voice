# Adding a test

Tests are **declarative YAML** — you describe a case (an input and what to assert) and a shared runner executes
it. There's no test code to write here: the providers, scorers and the judge all live in the shared `locveil-commons`
package; this repo carries only the cases. Pick the surface that matches what you're checking, write a few lines of
YAML, and run it with `make`.

![Choosing a test surface](../images/howto-test.png)

Everything lives in **`eval/`**. Read [`eval/README.md`](../../eval/README.md) once for the reference (the two run
axes, conventions, gotchas); this guide is the recipe for adding a case.

## Pick a surface

| If you're checking… | Surface | File | Needs |
|---|---|---|---|
| a command-line tool's output / exit code | **CLI contract** | `cli.promptfooconfig.yaml` | nothing (fastest) |
| that speech is transcribed and understood | **WS system** | `ws.promptfooconfig.yaml` | a running Irene + an audio fixture |
| that the spoken reply is *good* (natural, polite) | **WS UX** (judged) | `ws.promptfooconfig.yaml` | the above + `DEEPSEEK_API_KEY` |
| that a known interaction *still behaves the same* | **Golden-trace** | `trace.promptfooconfig.yaml` | the models (offline; no SUT) |

## A CLI-contract case

The fastest tests check a console script: give it a command line, assert on its output. The `cmd` var is the
command line; the result is JSON `{stdout, stderr, exit_code}`.

```yaml
- description: validate config — embedded-armv7.toml
  vars: { cmd: "locveil-voice-config-validate --config-file config/embedded-armv7.toml --ci-mode" }
  assert:
    - { type: javascript, value: "JSON.parse(output).exit_code === 0" }
```

A failure contract is just different assertions:

```yaml
- description: missing config exits non-zero and says so
  vars: { cmd: "locveil-voice-config-validate --config-file nope.toml" }
  assert:
    - { type: javascript, value: "JSON.parse(output).exit_code !== 0" }
    - { type: javascript, value: "/not found/i.test(JSON.parse(output).stdout)" }   # the report prints to stdout
```

Run with **`make cli`** — no service, no key, no fixtures.

## A WS system case (speech → transcript / intent)

These stream an audio fixture at the live `/ws/audio` endpoint (protocol: the
[WebSocket API guide](websocket-api.md)) and assert on the result. The `audio` var is the
fixture; `reference` is what was spoken.

Transcript accuracy (word error rate, scored by `jiwer`):

```yaml
- description: ASR — «поставь таймер на десять минут»
  metadata: { kind: system }
  vars:
    audio: fixtures/timer_10min.wav
    reference: поставь таймер на десять минут
    wer_threshold: 0.15
  assert:
    - type: python
      value: file://../../locveil-commons/eval/eval_commons/assertions/wer_scorer.py
```

Intent recognition (the reply is JSON, so assert on a field):

```yaml
- description: Intent — timer set is recognized
  metadata: { kind: system }
  vars: { audio: fixtures/timer_10min.wav }
  assert:
    - type: is-json
    - type: javascript
      value: JSON.parse(output).intent_name === 'timer.set' && JSON.parse(output).success === true
```

Run with **`make ws TARGET=local`** (start Irene first: `make serve`), or **`make ws TARGET=wb7`** against the
controller.

## A WS UX case (is the reply *good*?)

When "correct" isn't a string match but a judgement — natural Russian, a polite failure — let the judge (DeepSeek)
grade the reply against a rubric. `transform` hands the judge only the reply text, not the JSON; write the rubric in
the language you're judging.

```yaml
- description: UX — confirms the timer in natural Russian
  metadata: { kind: ux }
  vars: { audio: fixtures/timer_10min.wav }
  assert:
    - type: llm-rubric
      transform: JSON.parse(output).response_text
      value: >
        Ассистент явно подтвердил на естественном русском, что таймер установлен,
        без англоязычных вставок и без сырых технических ошибок.
```

Run with **`make ux TARGET=local`** (needs `DEEPSEEK_API_KEY`). Russian judging is still being calibrated — treat
verdicts as indicative until you've checked a few against hand-scored replies.

## Recording the audio fixture

A WS case needs its `audio` file as **16 kHz / mono / 16-bit PCM** WAV. The recorder prompts you with the
`reference` line, captures from the mic, lets you re-take, and saves a conformant file:

```bash
cd eval
make setup-record                 # once — adds the mic dependencies
make record FIXTURE=timer_10min   # or `make record` to record every missing fixture
```

Device setup, the keep/redo loop and the TTS alternative are in [`eval/fixtures/README.md`](../../eval/fixtures/README.md).

## A golden-trace regression case

Record a known-good interaction once; replay it offline forever to catch behavior drift. A recorded
trace carries its input and an **oracle** (the reply, success, and actions it produced); replaying re-runs
the input through the *current* pipeline and diffs against that oracle — exit `0` means it still matches.
No server, no mic, no judge: a case is just a console invocation whose exit code is the verdict.

```yaml
- description: golden — «поставь таймер на 10 минут» still sets the timer
  metadata: { kind: trace-system }
  vars:
    cmd: "locveil-voice-replay-trace -t eval/traces/timer_set_10min.json --config config/embedded-armv7.toml"
  assert:
    - { type: javascript, value: "JSON.parse(output).exit_code === 0" }
```

Run with **`make replay`** (needs the models present; offline). Use `trace-system` only for deterministic
paths (ASR + cheap NLU + rule-handlers); LLM replies vary run-to-run, so mark those `trace-ux` and judge
the reply instead. Recording a golden and the determinism tiering are covered in
[`eval/traces/README.md`](../../eval/traces/README.md). The oracle drifts *on purpose* when you change
behavior — re-record and review the JSON diff.

## Keep cases endpoint-agnostic

A case never names an endpoint or a config — two things vary *outside* the YAML so the same case runs anywhere:

- **TARGET** — *where* Irene runs: `local` vs `wb7`. The endpoint is injected from the target profile as
  `{{env.WS_AUDIO_URL}}`, never hard-coded.
- **CONFIG** — *which* config a local Irene runs: `make serve CONFIG=voice`.

If you're tempted to fork a case per target or config, add a profile under `eval/profiles/` instead.

## Try it

Add your case, then `make cli` / `make ws TARGET=local` / `make ux`; `make view` opens the results UI. If a WS case
can't connect, start Irene first (`make serve`); if a Python provider fails to import, you skipped `make setup`. The
full reference — axes, surfaces, conventions — is [`eval/README.md`](../../eval/README.md).
