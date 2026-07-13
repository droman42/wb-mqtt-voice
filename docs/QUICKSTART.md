# Quickstart & Tester Guide

How to install, run, and exercise Irene. Aimed at a tester doing a first pass; no models or cloud
keys are required for the basic text flows.

> **Run from the repository root** (`locveil-voice/`). All paths below are relative to it.

---

## 1. Install

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # if you don't have uv
uv sync --project backend                         # creates the venv + installs deps
```

## 2. (Optional) `.env` — only for cloud providers

The basic text flows need **no** API keys. Only create `.env` if you'll test cloud TTS/ASR/LLM
(OpenAI, Anthropic, ElevenLabs, Google):

```bash
cp docs/env-example.txt .env      # then fill in the keys you need
```

> Leave the `LOCVEIL_VOICE_COMPONENTS__*` lines **commented** (they are by default). Components belong in your
> config file, not `.env`; setting them in `.env` overrides the config and can produce an invalid combo
> (e.g. TTS on / Audio off).

## 3. Pick a config

**A config file is required** — running without one stops with directions instead of guessing.
For a first run, use the shipped starter as-is:

```bash
uv run --project backend locveil-voice-cli -c config/config-example.toml
```

That's the whole text pipeline — type commands, get answers, web API alongside — with **no model
downloads and no API keys**. To grow it, copy it (`cp config/config-example.toml config.toml`) and
lift sections from the reference; the example's comments name which section covers each upgrade.
The shipped configs:

| Config | Use for |
|---|---|
| `config/config-example.toml` | **first run** — curated text-only starter, works out of the box |
| `config/config-master.toml` | the documented reference (every option) — lift sections from it |
| `config/full.toml` | everything enabled (heavy) |
| `config/embedded-armv7.toml` / `config/embedded-aarch64.toml` | Wirenboard controllers (WB7 / WB8) — the home-automation box the satellites talk to |
| `config/standalone-x86_64.toml` | a standalone x86 voice box |

> The **`[components]`** flags are what actually load a component (a sub-section's `enabled = true`
> is ignored while its `[components]` flag is off). For **voice**, turn `asr`/`tts`/`audio` on and
> install the matching models — heavier than the text flows.

---

## 4. Run it

### CLI (interactive text)
```bash
uv run --project backend locveil-voice-cli -c config/config-example.toml   # or your own -c config.toml
```
Then type, e.g.:
- `привет` → a greeting
- `который час` / `какое сегодня число` → date/time
- `поставь таймер на 5 минут` → sets a timer (confirms "5 мин")
- `расскажи что-нибудь` → conversation (degrades gracefully offline)
- `help`, `status` → system info; `quit` to exit

### WebAPI (REST + WebSocket + the config-ui backend)
```bash
uv run --project backend locveil-voice-webapi -c config/config-example.toml --port 8080
```
Smoke-check:
```bash
curl http://localhost:8080/health
curl -X POST http://localhost:8080/execute/command -H 'Content-Type: application/json' \
     -d '{"command":"привет"}'
```
Interactive API docs: open `http://localhost:8080/docs`.

### Voice (microphone)
The full spoken pipeline from a local microphone — **Microphone → VAD → [wake word] → ASR → intent →
spoken reply**:
```bash
uv run --project backend locveil-voice-voice -c config.toml   # a voice-capable config (asr/tts/audio on) + models
```
It always uses microphone-only input (other inputs are overridden), but is otherwise **config-driven**:
the ASR engine is whatever **`[asr] default_provider`** selects (`vosk` / `whisper` / `sherpa_onnx` / …)
— there's no hardcoded model. The wake word runs only if `voice_trigger` is configured (otherwise audio
goes straight to ASR), and VAD is required (the runner turns it on). This needs a **voice-capable config
plus the matching ASR model installed**, so it's heavier than the text flows above. Useful flags:
`--list-devices` (pick a microphone), `--check-deps`, and `--trace` (see [tracing & replay](guides/tracing.md)).

### Satellite (room node — mic here, understanding on the controller)
The satellite pipeline: **Microphone → VAD → wake word «Ирина» → the controller over WebSocket**,
with spoken replies played back locally. Nothing heavy runs on the box — no ASR, no models beyond
the wake word pack:
```bash
uv run --project backend locveil-voice-satellite -c config/satellite.toml --server ws://localhost:8080 --room "Кухня"
```
Point `--server` at a running WebAPI/standalone instance (the step above works). Say «Ирина»,
pause, then the command; `--no-wake` streams every utterance for rapid testing. Full story,
including the mutual-TLS enrollment for real deployments: [satellite guide](guides/satellite.md).

### config-ui (browser config editor)
Needs the WebAPI backend running (step above), which it talks to at `http://localhost:8080`.
```bash
cd config-ui
npm ci
npm run dev          # opens a Vite dev server (printed URL, usually http://localhost:3000)
```

---

## 5. What's in scope for this build

**Test these:**
- Text commands via CLI and `POST /execute/command`: greetings, date/time, timers, conversation, system (`help`/`status`/`version`).
- WebAPI endpoints: `/health`, `/status`, `/execute/command`, `/docs`.
- config-ui: browse + edit config sections (incl. the **Output Channels** `[outputs]` section), donation/prompt editors, language switch.
- **Smart-home commands** («включи свет», «закрой шторы») — but only with a running
  [locveil-bridge](guides/smart-home.md) and `[outputs.bridge]` enabled. Without one, the honest
  spoken answer is «умный дом не подключён» — that reply is correct behavior, not a bug.

**NOT in this build (don't file these as bugs):**
- **ESP32 voice satellite** and the wake-word path.
- **Voice/ASR** end-to-end unless you deliberately enable `asr`/`tts`/`audio` in `[components]` + install models.

**Docker images** are published to GHCR (`ghcr.io/locveil/locveil-voice-*`); running from an image
instead of a checkout is covered by [`ops/INSTALL.md`](../ops/INSTALL.md) (controller deployment).

## 6. Tests & coverage

Run the backend test suite (it's green, and a hard CI gate):
```bash
uv run --project backend --extra dev python -m pytest -c backend/pyproject.toml backend/tests/
```

**Coverage needs a one-time sqlite shim.** Coverage (`pytest --cov`) keeps its data in a SQLite file,
but the CPython this project runs on (the same build `locveil-bridge` uses) is compiled **without** the
stdlib `_sqlite3` module — so `coverage.py` can't start and you'd see `No module named '_sqlite3'`. We
ship `pysqlite3-binary` and a tiny installer that aliases it onto `sqlite3` at interpreter startup. Run
it **once after `uv sync --project backend`** — a sync rewrites the venv, so re-run it whenever you (re)create the venv:
```bash
bash scripts/install_sqlite_shim.sh                                   # enables coverage on this Python
uv run --project backend --extra dev python -m pytest -c backend/pyproject.toml backend/tests/ --cov=locveil_voice --cov-report=term
```
You only need it for **coverage** runs — plain `pytest` never touches SQLite, so it works without the
shim. And on a Python that already has stdlib `sqlite3`, the installer is a harmless no-op (the shim
checks first and only aliases when native sqlite is missing).

## 7. Known state (so you can calibrate)
- The **test suite is green** (~1300 passing) and enforced in CI (`backend-health`); the user-facing
  flows above are verified working (see `backend/tests/test_smoke_e2e.py`).
- If a **core text flow** (greeting, time, timer, conversation, a WebAPI endpoint, or config-ui editing)
  misbehaves — **that** is worth reporting.

## 8. Reporting findings
For each issue, include: the **mode** (CLI / WebAPI / config-ui), the **config** used (`-c …`), the
**exact input** (command or request), what you **expected** vs **saw**, and the relevant **log lines**
(`logs/irene.log`). A copy-pasteable repro beats a description.
