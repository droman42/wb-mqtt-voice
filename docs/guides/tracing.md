# Tracing & replay

A trace is a self-contained recording of one request — the audio that came in, the settings that shaped the
run, every pipeline stage, and the answer that came out — saved as a single JSON file you can **listen to** and
**replay through the pipeline**. It's the tool for the two questions that are otherwise hard to answer after the
fact: *why did that command misfire?* and *did my VAD/config change make things better or worse?*

Tracing is **off by default and costs nothing when off**. You turn it on for a debugging session, capture a few
requests, and turn it back off — normal traffic is never touched.

## Recording a trace

Pass `--trace` to any runner. While it's on, **every request is saved** to one JSON file per request under
`<assets_root>/traces/` (named by request id):

```bash
uv run --project backend locveil-voice-cli --trace
uv run --project backend locveil-voice-webapi --trace
```

That's the whole switch — there's no per-request flag and no ring buffer. A trace session is a deliberate,
bounded act: turn it on, reproduce the problem, turn it off. Retention is manual — the files are yours to keep
or delete.

### What a trace captures — the three levels

`[trace] capture_level` fixes *which audio* is stored and *where a replay re-enters the pipeline*:

| Level | Captures | A replay re-enters at | Use it for |
|---|---|---|---|
| `utterance` (default) | the assembled 16 kHz segment ASR saw | ASR → NLU → intent | "the words were right but the answer was wrong" |
| `segmenter` | the same audio **plus per-frame VAD verdicts** (`vad_frames`) | VAD → … | tuning [VAD](vad.md) — *seeing where it fired* |
| `raw` | the pre-canonical microphone audio | resample → VAD → … | "did the mic even hear it right?" |

The `raw` level for a **live microphone** keeps a continuous rolling buffer, so it's the one heavier mode — it's
gated behind its own flag:

```bash
uv run --project backend locveil-voice-cli --trace-raw-mic   # implies --trace, and selects the raw level
```

### Tuning the rest

The knobs live in the `[trace]` section (config-ui-editable), but the defaults are sensible and the runner flags
set what you usually need:

```toml
[trace]
enabled = false              # or pass --trace
capture_level = "utterance"  # utterance | segmenter | raw
log_threshold = "INFO"       # log records at/above this are folded into the trace (exceptions always are)
# traces_dir = "/var/lib/irene/traces"   # defaults to <assets_root>/traces
```

A saved trace also folds in the **log records** for that request (at `log_threshold` and above, plus any
exception stack traces) and any **handler events** — the timer that was set, the LLM call that was made, the
provider that was switched — each tagged with where in the run it happened. So a single file tells you what was
heard, what was decided, what was logged, and what was done.

## Replaying a trace

`locveil-voice-replay-trace` re-runs a saved trace through the **real pipeline** and diffs the fresh answer against the
recorded one. It seeds the conversation context from the trace's "before" snapshot, re-injects the captured
audio at the right entry point for its level, and reports what changed:

```bash
uv run --project backend locveil-voice-replay-trace -t ~/.cache/irene/traces/<id>.json
```

Replay is **not** bit-exact — the LLM isn't deterministic and time and device state move on — so it reproduces
the *input and the starting state*, then shows you the difference. That's exactly what you want for a regression
or a tuning sweep, not a recording playback.

### The two modes

- **`--local`** (default) — ignore the trace's settings and run the audio through **your** pipeline. This is the
  VAD-tuning case: take a trace a tester captured, change your `[vad]` knobs, replay, and see whether the segment
  comes out cleaner. The report flags any difference between their settings and yours.
- **`--reproduce`** — run it as faithfully as the trace allows, applying the settings it captured. If it needs a
  model you don't have installed, it **stops and tells you which one**, and points you back to `--local` — it
  won't quietly substitute a different model and pretend it reproduced the run.

### While you're at it

- **`--listen`** — play the captured audio on your system output, so you can hear what the microphone actually
  sent before you reason about it.
- **`--step`** — pause at each pipeline stage (text-processing, NLU, intent), printing the stage's input and
  output, and wait for a keypress. Press `c` to run to the end, `q` to quit. The slow-motion view of one request.
- **`--record-out <dir>`** — capture the replay run as a *second* trace. So a tester's trace plus your local
  replay become two comparable files you can hand off for analysis.

```bash
uv run --project backend locveil-voice-replay-trace -t their-trace.json --local --listen --step
uv run --project backend locveil-voice-replay-trace -t their-trace.json --record-out ./replays/
```

## Tuning VAD with a trace

This is the workflow that replaces the old standalone recording tool. Capture a mic session at the `segmenter`
level, then read the `vad_frames` in the saved file — each frame carries the moment, the voice/silence verdict,
the energy and the active threshold, so you can *see* exactly where VAD fired over the audio. Adjust the
[`[vad]`](vad.md) knobs, replay the same trace with `--local`, and compare. Because the capture runs inside the
real pipeline, VAD is measured at the production 16 kHz rate — the same audio your live system sees.

## Satellite traces — one utterance, two machines

A [satellite room node](satellite.md) run with `--trace` writes a *merged* trace per utterance: its own
device story (raw mic, VAD frames, wake-gate decisions, the wire exchange, the reply as played) with the
controller's execution trace nested inside — so a single file answers whether the failure was the room's
hearing or the controller's understanding. The controller shares its half only when its config says
`[trace] allow_remote_request = true`; print that nested half with:

```bash
uv run --project backend locveil-voice-replay-trace -t traces/<id>.json --show-controller
```

A satellite trace replays like any other: its captured utterance audio runs through a full local pipeline
for VAD tuning or recognition comparison.

## Where the files live

Traces land in `<assets_root>/traces/` unless you set `[trace] traces_dir`. Each is a plain JSON file with the
audio inline (base64, no sidecar WAVs), so a trace is portable — copy one off the box and replay it anywhere the
same models are installed.
