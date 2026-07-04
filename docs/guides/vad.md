# Voice activity detection (VAD)

VAD decides which slices of incoming audio actually contain speech, so the rest of the pipeline (ASR, then
intent) sees real utterances instead of every chunk of silence. It is a **lightweight provider family**
(`irene.providers.vad`) — three interchangeable engines, selected and configured like every other component,
but without the web/manager apparatus (it's a per-frame hot-path primitive, not a request/response service).

It runs only where Irene has a local microphone. On a Wirenboard install the ESP32 satellite does VAD
on-device and streams already-segmented utterances, so this guide is for the standalone-mic case.

## How it's wired

VAD sits in the voice segmenter, ahead of the wake word and ASR. Two switches must **both** be on for it to run:

- `[vad] enabled = true` — the master switch.
- `[workflows.unified_voice_assistant] enable_vad_processing = true` — the pipeline flag.

The microphone is captured at its native rate, transformed **once** to the pipeline's canonical 16 kHz / mono
at the input boundary, and from there VAD, wake word and ASR all see the same canonical audio (see
[audio](audio.md) for the format negotiation).

## Engines (providers)

`[vad] default_provider` picks the engine; each is configured under its own `[vad.providers.<name>]` table:

- **`energy`** (default) — a lightweight energy / zero-crossing detector, no extra dependencies,
  sub-millisecond per chunk. Setting `use_zero_crossing_rate` or `adaptive_threshold` upgrades the simple
  detector to an adaptive one that tracks the noise floor.
- **`silero`** — the Silero VAD ONNX model (run via sherpa-onnx, 64-bit only; reuses the `asr-onnx`
  dependency). More robust in noise; the model is fetched into the assets folder once at startup, like
  any other model. If it can't come up (no network on a fresh install, missing dependency), Irene logs
  the reason and falls back to `energy` so voice detection keeps working.
- **`microvad`** — `pymicro-vad` (64-bit only; the `vad-tflite` extra). Self-contained — bundles its model
  and runtime, nothing to download — and shares its frontend with the microWakeWord trigger, so the two are
  one stack and match what the ESP32 runs on-device. Pick whichever runtime your build already loads:
  `silero` if you're on sherpa-onnx ASR, `microvad` if you're on microWakeWord.

## Configuration

The `[vad]` table holds the segmentation / pipeline knobs; the engine knobs live under
`[vad.providers.<name>]` (only the active provider's table is read):

```toml
[vad]
enabled = true
default_provider = "energy"        # energy | silero | microvad

[vad.providers.energy]
energy_threshold = 0.01
sensitivity = 0.5
# … the energy knobs below
```

**`[vad]` — segmentation & pipeline**

| Field | Default | Range |
|---|---|---|
| `enabled` | true | — |
| `default_provider` | `energy` | energy / silero / microvad |
| `max_segment_duration_s` | 10 | 1–60 |
| `processing_timeout_ms` | 50 | ≥1 |
| `buffer_size_frames` | 100 | ≥10 |
| `normalize_for_asr` | true | — |
| `asr_target_rms` | 0.15 | 0.01–0.3 |
| `enable_fallback_to_original` | true | — |

**`[vad.providers.energy]`**

| Field | Default | Range |
|---|---|---|
| `energy_threshold` | 0.01 | 0–1 |
| `sensitivity` | 0.5 | 0.1–3.0 |
| `voice_frames_required` | 2 | ≥1 |
| `silence_frames_required` | 5 | ≥1 |
| `use_zero_crossing_rate` | true | — (→ advanced) |
| `adaptive_threshold` | false | — (→ advanced) |
| `noise_percentile` | 15 | 1–50 |
| `voice_multiplier` | 3.0 | 1–10 |

**`[vad.providers.silero]`**

| Field | Default | Range |
|---|---|---|
| `threshold` | 0.5 | 0–1 |
| `model_url` | k2-fsa release URL | — |
| `voice_duration_ms` | 100 | 10–1000 |
| `silence_duration_ms` | 200 | 50–2000 |

**`[vad.providers.microvad]`**

| Field | Default | Range |
|---|---|---|
| `threshold` | 0.5 | 0–1 |
| `detection_latency_ms` | 30 | ≥0 |

The last three `[vad]` knobs (`normalize_for_asr`, `asr_target_rms`, `enable_fallback_to_original`) normalise a
detected segment's loudness before ASR. The pre-roll (the audio kept *before* the trigger, so the speech onset
and the wake word aren't clipped) is sized automatically from the active engine's detection latency — energy
from `voice_frames_required`, silero from `voice_duration_ms`, microvad from `detection_latency_ms` — so you
don't tune it directly.

## Tuning

Start from `energy` and adjust by symptom (energy knobs under `[vad.providers.energy]`):

- **Noisy room** — raise `energy_threshold`, lower `sensitivity`, try `adaptive_threshold = true` (or switch
  `default_provider` to `silero`).
- **Quiet speaker, words clipped** — lower `energy_threshold`, raise `sensitivity`.
- **Choppy segments** (one sentence split in two) — raise the silero `silence_duration_ms` /
  energy `silence_frames_required`.
- **Laggy** (waits too long to cut off) — lower them.

To tune by evidence rather than by ear, **record a trace at the `segmenter` level** and read its per-frame
`vad_frames` — voice/silence, energy and the active threshold for every frame — to see exactly where VAD fired,
then replay the same audio after each change and compare. See [tracing & replay](tracing.md).

## Performance

The energy engine is effectively free; Silero adds a small ONNX inference cost but stays real-time. On weak
hardware stay on `energy` and leave `use_zero_crossing_rate` / `adaptive_threshold` off. The real limits on
segment handling are `max_segment_duration_s` (caps a runaway segment) and `buffer_size_frames`.

## Troubleshooting

- **No speech detected** — confirm both switches are on; lower `energy_threshold` / raise `sensitivity`;
  check the mic actually produces audio (see [audio](audio.md)).
- **False positives** (noise triggers it) — raise `energy_threshold`, lower `sensitivity`, try
  `adaptive_threshold` or `silero`.
- **Choppy or merged segments** — tune the timing knobs above.
- **Poor ASR on short commands** — segments may be too small; raise the silero `voice_duration_ms`; keep
  `normalize_for_asr` on.

At startup VAD logs `INFO … VAD audio processor initialized: provider=…, max_segment=…s`, then the pre-roll
size and the negotiated canonical format. To watch live levels, a chunk's RMS is `sqrt(mean(samples²)) / 32768`.

Reference configs to copy: `configs/vad-development.toml`, `configs/vad-production.toml`, and the documented
`[vad]` + `[vad.providers.*]` sections of `configs/config-master.toml`.
