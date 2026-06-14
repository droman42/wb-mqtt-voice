# Trace persistence + playback (ARCH-19)

**Status:** design COMPLETE 2026-06-14 (D-1..D-18 locked; §13 open questions all resolved — ready for
implementation per the §12 slices). Builds on the existing ephemeral
`core/trace_context.py` (`TraceContext`) and the ARCH-15 observe/event-bus vocabulary. Goal: persist an
utterance-execution trace to a **self-contained JSON file** so it can be (a) **listened to** and (b)
**replayed through the pipeline** — for regression debugging and VAD tuning.

Today a trace is ephemeral (one `TraceContext` per request, GC'd when the handler returns; opt-in only on the
`/trace*` endpoints; per-trace caps `max_stages`/`max_data_size_mb`; no store, no persistence). That stays —
this design adds an opt-in **save + replay** layer on top, it does not change normal-traffic behaviour.

## 1. The two uses (one file)

| Use | Needs |
|---|---|
| **Listen** to the captured utterance | the full audio, inline |
| **Replay** through the pipeline (regression / VAD tuning) | a clean, un-sanitized *replay envelope* + a replay entry point + an oracle to diff against |

Both are served by one **self-contained JSON** file with audio **base64 inline** (decision: no WAV sidecars —
base64 everywhere, consistent with the rest of the system).

## 2. The trace file format

```jsonc
{
  "trace_version": 1,
  "request_id": "…",
  "saved_at": "2026-06-13T…",

  "replay": {                          // FAITHFUL, un-sanitized — what makes it re-runnable + listenable
    "input": { "kind": "audio",        //   or {"kind":"text","text":"…"}
               "format": {"rate":16000,"channels":1},
               "audio_base64": "…",     //   the FULL utterance, NOT the 1 MB sanitiser cap
               "capture_level": "utterance" },   // utterance | segmenter | raw
    "request": {"provider":"vosk","language":"ru","skip_wake_word":true,
                "wants_audio":false,"session_id":"…","room":"kitchen"},
    "canonical": {"rate":16000,"format":"pcm16","channels":1},
    "seed_context": { … },             // the "before" context snapshot — replay seeds a fresh context from it
    "config_subset": {                 // the settings that SHAPED this run — enough to reproduce OR to diff
      "audio": {…}, "vad": {…}, "asr": {…}, "nlu": {…} },   // (a hash alone can't be replayed-from)
    "config_digest": "sha256:…",       // quick equality check against the replayer's config
    "provider_models": {"asr":"vosk-ru-0.22","nlu":"hybrid"}   // for the cross-system mismatch report (models aren't embeddable)
  },

  "execution": {                       // today's export_trace() — SANITISED (redacted/truncated), for reading
    "pipeline_stages": [ … ],
    "context_evolution": { "before":…, "after":…, "changes":… },
    "performance_metrics": { … }
  },

  "vad_frames": [                      // segmenter level only — per-frame verdicts, for VAD tuning
    {"t_ms": 0,  "is_voice": false, "energy": 0.002, "threshold": 0.01},
    {"t_ms": 23, "is_voice": true,  "energy": 0.041, "threshold": 0.01}
  ],

  "logs": [                            // TraceLogger — log records + exceptions captured during the request
    {"t_ms": 31, "level": "ERROR", "logger": "…", "stage": "asr_transcription",
     "message": "…", "exc_text": "Traceback …"}
  ],

  "handler_events": [                  // trace_event() emitted by intent handlers
    {"t_ms": 88, "handler": "timer", "label": "timer_set", "data": {"duration_s": 300}}
  ],

  "recorded_output": {"text":"…","success":true,"actions":[…]}   // the oracle a replay diffs against
}
```

`replay` is faithful (un-sanitised) and re-runnable + listenable; `execution` is the sanitised human view (the
existing `export_trace()`, with `_sanitize_for_trace`'s redaction/truncation/caps intact — right for display);
`recorded_output` is what a replay compares to.

## 3. Capture levels (`[trace] capture_level`)

The level fixes *which audio* is stored and *where a replay re-enters*:

- **`utterance`** (default) — the assembled canonical `VoiceSegment` (16 kHz). Replays **ASR-onward** via the
  pre-segmented path (exactly what `/ws/audio` + `/asr/transcribe` do today). Free — already in hand.
- **`segmenter`** — the windowed pre-roll + voiced frames the `VoiceSegmenter` saw, **plus `vad_frames[]`**
  (per-frame voice/silence + energy + the active threshold). Replays **VAD-onward**; the per-frame verdicts let
  you *see where VAD fired* over the audio and tune `[vad.providers.*]`. Free — the segmenter already buffers
  the pre-roll + segment and runs VAD per frame; this just hands that off.
- **`raw`** — the pre-canonical audio. Replays **negotiate-onward** (resample + VAD + wake). Free for
  `/ws/audio` and `/asr/transcribe` (the input is already a bounded utterance). For the **live mic** it needs a
  **continuous rolling buffer** of native-rate frames correlated to the utterance — heavier, always-on while
  capturing — so it is gated behind a **separate flag** (`--trace-raw-mic` / `[trace] capture_raw_mic`).

VAD tuning must run VAD at the **production rate** (canonical 16 kHz), so the capture harness inserts
`to_canonical` *before* VAD (the legacy `vad_recording_test` ran VAD on raw 44.1 kHz — see §10).

## 4. Ambient access — the `current_trace` contextvar

A `TraceLogger` (a global `logging.Handler`) and handler recording can't be served by threading
`trace_context` through every signature — logging is process-global and handlers are deep. The enabler is a
**`current_trace: ContextVar[Optional[TraceContext]]` in `core/trace_context.py`**, set at the request
boundary (`process_audio_input` / `process_text_input`) and reset on exit.

**Hexagon check — clean.** The domain (`irene.intents`, where handlers live) is forbidden from importing
`components/workflows/providers/web_api/runners/inputs/outputs` (ARCH-1), **but it already imports `core`**
(`orchestrator.py` → `core.trace_context`/`core.metrics`/`core.client_registry`, `context.py`, `manager.py`,
`context_models.py` → `core.session_manager`; lint 9/9). So a contextvar + recording helpers in `core` are
reachable by handlers exactly as `core.metrics` already is — no new edge.

## 5. TraceLogger

A global `logging.Handler` installed at startup, **active only when `current_trace` is set + enabled**:
- captures records **≥ `[trace] log_threshold`** (configurable; default INFO/WARNING) **plus full exception
  stack traces**, each tagged with the **current stage** + `t_ms`, appended to `trace.logs`;
- bounded by its own cap (like `max_stages`) so a chatty request can't blow the file up.

## 6. Handler recording — `trace_event(label, data)`

A tiny `core` helper `trace_event(label, data)` that finds `current_trace` and appends a `handler_events`
record — **no-op when no active trace**, so handlers call it unconditionally. Handlers record their own
sub-steps (device command sent, LLM call made, timer set). The orchestrator keeps auto-recording the overall
`intent` stage; this adds granularity *inside* it. (The orchestrator's existing `_current_trace_context` stash
is superseded by the contextvar.)

## 7. Replay

A CLI tool `irene/tools/replay_trace.py` (a `/trace/replay` endpoint is optional, TBD): load the JSON →
rebuild `input` + `request` → **seed a fresh `UnifiedConversationContext` from `seed_context`** → re-inject at
the `capture_level`'s entry point → run with a fresh trace → **diff the new output against `recorded_output`**.

**Where it re-enters (the audio source is not a microphone).** The workflow entry points are source-agnostic
(`process_audio_input(AudioData)`, `process_audio_stream(AsyncIterator[AudioData])`), so replay just constructs
the audio and calls them. The level picks the entry:
- **`segmenter` / `raw`** → replay *through* VAD/negotiate, i.e. as a **stream** → `process_audio_stream`. Model
  the source as a lightweight **`TraceInput`** (an `InputPort` adapter — "the microphone, sourced from the trace
  file"): it decodes the base64 frames, yields them, and carries the envelope's `request` context. This reuses
  the whole input→workflow(→output) seam and composes with the ARCH-16 multi-input daemon ("attach a replay
  input"). The replay tool can drive `TraceInput` directly without standing up the full `InputManager`.
- **`utterance`** → the *pre-segmented* path (skip VAD), exactly like `/asr/transcribe`: one bounded `AudioData`
  → `process_audio_input`. Not a stream, so it bypasses `TraceInput`.

**Two replay modes (cross-system).** The audio is self-contained (base64), so the *input* is portable — but
config and models are not. A trace from a tester with a different config is replayed one of two ways:
- **`--reproduce`** ("what did *their* system do?") — apply the trace's `config_subset` as the replay config;
  use `provider_models` + `config_digest` to **detect + report** what the replayer can't honour.
- **`--local`** (default — "their utterance failed; how does *my* pipeline / my VAD settings handle it?", the
  VAD-tuning case) — ignore the trace's config, run the audio through the local pipeline, and emit a
  **config/model mismatch report** (trace's settings vs the replayer's) so the difference is visible.

`--local` always works (no dependency on the sender's setup); `--reproduce` is faithful only when the same
models are installed. **For now the model gap is moot** — the dev/notebook system is a *superset* of what
testers/hand-picked users run, so the models are always present; a model-availability fallback (fail vs
degrade-and-report) is a future concern, captured below. Note `seed_context` has the same texture — a tester's
room/devices may not exist locally, so under `--local` it is just seeded state, under `--reproduce` another
mismatch to report.

**Playback UX (the CLI tool).**
- **Listen** — reuse the **audio component** (the `sounddevice`/`aplay`/… playback providers) on the OS/system
  output device (the audio provider's configured device, or the OS default — "system settings"). Decode the
  base64 → play from a memory buffer (no temp WAV; base64-everywhere holds). Two listen points: the recorded
  **input utterance**, and a `--local` re-run's live **TTS reply** when `wants_audio`. Audio is offered, never
  forced (a `play` command / `--play`).
- **`--step`** — pause at each **stage boundary** (the same boundaries the trace instruments), print the
  stage's input/output/timing, allow `play`/`inspect`, then resume on a keypress (`c` = run to the end). Needs
  one **async pause hook** at the workflow's stage transitions, reached via the `current_trace` contextvar
  (no-op when not stepping) — `record_stage` itself stays synchronous.
- **`--record-out <file>`** — run the replay **with capture on** and save a **second trace** (default
  `capture_level` = the source trace's). So replaying a tester's trace yields *their* trace + *your* local
  replay trace — two self-contained, comparable files (plus the `recorded_output` diff) to hand over for analysis.

**Determinism caveat (baked in):** ASR is ~deterministic for the same audio; **LLM is not** (temperature),
and time/device state move on. So replay reproduces the **input + starting state**, then diffs — it is a
**regression/tuning aid, not bit-exact reproduction**. Seeding the context is what makes context-dependent
intents (disambiguation, "стоп") replay meaningfully.

## 8. Config & trigger

- **Now:** runner flags — `--trace` (on/off, save every request while on) and `--trace-raw-mic` (the extra
  live-mic rolling-buffer level). Bare `--trace` "just works" on sensible defaults.
- **Later:** a `[trace]` TOML section (config-ui-editable): `enabled`, `capture_level`, `capture_raw_mic`,
  `log_threshold`, `traces_dir`. (No `save_policy` knob — per **D-17** the startup tracing flag is the only
  gate; while on, **every** request is saved. The ring/on-error idea was considered and declined.)
- Files land in `[trace] traces_dir` (under the assets root); **retention is manual** (D-17).

## 9. Hexagon seams (new vs reused)

- **New (all in `core`):** the `current_trace` contextvar, `trace_event()`, the `TraceLogger` handler, the
  envelope fields on `TraceContext` (`record_input`, the un-sanitised audio channel, `to_file`/save), and the
  `[trace]` config.
- **Capture points:** the request boundary (envelope: input + request + `seed_context` + `config_digest` +
  final `recorded_output`); the `VoiceSegmenter` (`vad_frames` + windowed audio); handlers (`trace_event`);
  the logging handler. No new backward edges (domain→core already exists; the segmenter is in `workflows`).

## 10. Reuse + retire `vad_recording_test`

`irene/tools/vad_recording_test.py` (`irene-vad-recording-test`) already builds a **mic → VAD-segmenter
harness** and saves per-segment audio (raw / normalised / 16 kHz). **Decision: retire-and-replace** — port the
meaningful parts into the capture layer (the mic-stream + `voice_segment_handler` harness, the WAV writer
becomes **base64 — no WAV files**), **fix the `to_canonical` ordering** (it VADs on raw 44.1 kHz; production
VADs on canonical 16 kHz), and add what it lacks (`vad_frames`, the structured self-contained JSON, replay).
**The tool is deleted once ported** — the trace system (capture `capture_level=segmenter` on a mic session,
then read `vad_frames`) fully covers its purpose, so there's no second mic-capture path to maintain.

## 11. Decisions (LOCKED 2026-06-13, design session)

- **D-1** Playback = **both** listen + replay; one **self-contained JSON**, audio **base64 inline** (no WAV).
- **D-2** Three configurable **capture levels** (utterance / segmenter+`vad_frames` / raw); **live-mic raw**
  behind a **separate flag**.
- **D-3** Ambient access via a **`current_trace` contextvar in `core`** (hexagon-clean — domain imports core).
- **D-4** **TraceLogger** with a **configurable threshold** + exception stack traces, stage-tagged.
- **D-5** Handlers record via opt-in **`trace_event()`**; orchestrator keeps the auto `intent` stage.
- **D-6** Replay **seeds a fresh context from `seed_context`** and **diffs** vs `recorded_output`; not bit-exact.
- **D-7** Trigger = runner **`--trace` (+ `--trace-raw-mic`)** now → `[trace]` TOML (config-ui) later; **save
  every request** while on; retention manual in v1.
- **D-8** **Retire-and-replace `vad_recording_test`**, porting its harness (base64, not WAV) + fixing the
  `to_canonical` ordering.
- **D-9** Replay's audio source = a lightweight **`TraceInput`** (`InputPort`) for the `segmenter`/`raw` stream
  levels; the `utterance` level reuses `process_audio_input` (pre-segmented). The entry point follows the level.
- **D-10** **Two replay modes** — `--local` (default; run the audio through the replayer's pipeline, emit a
  config/model **mismatch report** — the VAD-tuning case) and `--reproduce` (apply the trace's **`config_subset`**
  as overrides; honour what the replayer can, report what it can't). The envelope therefore carries a captured
  **config subset** (audio/vad/asr/nlu), not just a digest. Model availability is **out of scope for now** (the
  dev system is a superset of testers' setups).
- **D-11** **Listening reuses the audio component** (`sounddevice`/`aplay`/… on the OS/system output device) —
  decode base64 → play from memory (no temp WAV); the input utterance + a `--local` re-run's TTS reply. No new
  playback mechanism.
- **D-12** The CLI is **`--step`-able** — pause at each stage boundary (print in/out/timing, allow listen/inspect,
  resume on keypress) via one **async pause hook** reached through the `current_trace` contextvar.
- **D-13** The CLI can **`--record-out`** a second trace of a replay run (same capture machinery; default
  `capture_level` = the source's), so a tester's trace + the local replay are two comparable files for analysis.
- **D-14** `vad_recording_test` is **deleted** once its harness is ported (no second mic-capture path).
- **D-15** Replay surface = **CLI only for v1**; a `/trace/replay` endpoint is **deferred, not dropped**. The
  rich UX is terminal-native (listen on the OS output D-11, interactive `--step` D-12, `--record-out` D-13),
  none of which survives an HTTP boundary; the workflow entry points are source-agnostic, so an endpoint can be
  added later with no rework and without pulling config-ui into Invariant #4 before a caller exists.
- **D-16** `--reproduce` against a **missing model** → **fail clearly**, naming the absent model(s) and
  suggesting `--local`. `--reproduce` is "what did *their* system do," so a silent substitution would be a
  false reproduction; degrading-and-running is exactly what `--local` already does. Keeps the two modes clean —
  `--reproduce` is faithful-or-nothing, `--local` always works. (Lifts the D-10 "out of scope for now"
  deferral: the rule is decided; the superset assumption just means it rarely fires.)
- **D-17** **Save policy = save every request whenever tracing was enabled at startup** (the runner `--trace`
  flag now / a future `[trace] enabled`). The startup flag is the **only** gate — **no** ring-buffer or
  on-error variant. Retention stays **manual**. (Resolves the deferred ring/on-error idea by declining it: a
  trace session is a deliberate, bounded debugging act, so "all while on" is the whole policy.)
- **D-18** A saved trace stays **file-only** — the full envelope (inline base64 audio, logs, `vad_frames`) is
  too heavy for the observation bus. When ARCH-15's event bus lands, emit only a **lightweight `trace_saved`
  pointer-event** (`request_id` + path + a short summary), never the payload, so observers learn a trace exists
  without it crossing the bus. Until then, strictly file-only.

## 12. Implementation slices (ARCH-19, TBD ordering)

1. **Spine:** `current_trace` contextvar + `trace_event()` + the un-sanitised `replay` envelope on
   `TraceContext` (`record_input`, `seed_context`, `config_digest`, `recorded_output`) + `to_file()`/save.
2. **TraceLogger:** the logging handler + the `[trace]` config + the `--trace` runner flag.
3. **Capture levels:** `utterance` + `segmenter` (`vad_frames` + windowed audio from the `VoiceSegmenter`) +
   `raw` (ws/file now; the live-mic rolling buffer behind `--trace-raw-mic`); ported from `vad_recording_test`.
4. **Handlers** emit `trace_event` at their key steps (device command, LLM, timer).
5. **Replay** tool (`replay_trace.py`) — `TraceInput` (stream levels) / `process_audio_input` (utterance), seed
   + re-inject + diff; `--local`/`--reproduce`; **listen** (audio component), **`--step`** (async pause hook),
   **`--record-out`** a second trace; optional `/trace/replay`.
6. **Delete `vad_recording_test`**; tests; user/dev docs (PR-6 style) + a diagram if warranted.

## 13. Open questions — RESOLVED (design session 2026-06-14)

All five are now decided; nothing left for a further design round before implementation.

- ~~Replay surface: CLI only, or also a `/trace/replay` endpoint?~~ — **resolved (D-15): CLI only for v1**, the
  endpoint deferred (entry points are source-agnostic, addable later without rework).
- ~~`vad_recording_test`: delete vs wrapper~~ — **resolved (D-14): deleted** once ported.
- ~~`config_digest`: hash vs subset~~ — **resolved (D-10): capture a config *subset*** (+ a digest for quick
  equality), since cross-system `--reproduce` can't replay from a hash.
- ~~Model-availability fallback~~ — **resolved (D-16): `--reproduce` fails clearly** (names the missing model,
  points to `--local`); no degrade path — that's what `--local` is for.
- ~~Save policy beyond v1 (on-error / recent-N ring)~~ — **resolved (D-17): save-all, gated solely on the
  startup tracing flag**; no ring/on-error; retention manual.
- ~~Cross-cut with ARCH-15 observe~~ — **resolved (D-18): file-only**; a lightweight `trace_saved` pointer-event
  (not the payload) once ARCH-15's bus exists.
