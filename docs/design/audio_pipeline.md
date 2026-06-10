# Audio pipeline — negotiation + transformation seam (ARCH-17)

The **input twin of ARCH-15**. ARCH-14/15 (`io_architecture.md`) made *output* a configurable, negotiated,
observable adapter set; the audio *input* chain (mic → VAD → wake → ASR) never got the same treatment, and
audio *encoding* (sample rate / format / channels) is handled ad-hoc below the coarse `VOICE/AUDIO/TEXT`
format axis. This design unifies three threads into one seam and **supersedes `onnx_inference_layer.md` §11.2's
"small VAD seam" decision** (the seam grew a third engine, an asset dependency, and platform markers — it is
now component-shaped). Design session 2026-06-10 (decisions §14).

## 1. The three threads (one root)

| Thread | Today | Smell |
|---|---|---|
| **VAD selection** | a 4-way `if/else` in `UniversalAudioProcessor.__init__` keyed on `vad_implementation`; engines are util classes | scattered knowledge → already shipped bugs: a validator that rejects `microvad` (`models.py:457`), an unconditional `calibrate_threshold` only the energy engines implement (`audio_processor.py:211`) |
| **Frame preservation** | a hardcoded `pre_buffer_size = 4` (~100 ms) prepended on voice onset | not coupled to the engine's detection latency → silero/microvad (or a high `voice_frames_required`) can clip the wake-word onset, because the segment feeds the wake word |
| **Format/rate negotiation** | `voice_trigger` capability-negotiates; ASR config-resamples; each provider re-implements int16→float; `AudioProcessor.resample_audio_data` is shared by input *and* output but the TTS side copy-pastes it 3× | no single seam, format barely negotiated, transforms logged-not-traced — i.e. not transparent |

Root cause: **the audio chain has no declared, negotiated, observable contract layer** — the thing ARCH-15
just gave the output side.

## 2. The model — canonical, transform-once, derived

One **canonical internal audio format** flows through the pipeline; the mic is transformed to it **once** at
the input boundary, and every downstream stage (VAD, wake, ASR) consumes canonical.

- **Derived, not configured.** The `AudioNegotiator` computes the canonical from the parties' *declared*
  `AudioContract`s — the common format all consumers require that the capture can be brought **down** to
  (downsample / downmix / reformat; never upsample to invent data). Per dimension:
  - *rate* — the highest rate all consumers need, ≤ the capture rate;
  - *channels* — mono (consumers need mono; stereo capture is downmixed);
  - *sample-format* — int16↔float32 are losslessly inter-convertible, so canonical is a free pick (int16 = the compact capture default; convert where a consumer wants float32).
- **Config can pin.** Optional `[audio] canonical_rate/format/channels` for operators who want determinism;
  an infeasible pin is the same fatal error.
- **Fatal if impossible.** If no canonical satisfies everyone (e.g. a consumer needs 48 kHz but capture is
  16 kHz), it's a **fatal config error at startup** — loud and early. This generalizes today's
  `allow_resampling=false → error` from one hand-set knob to automatic, capability-driven validation.

The **satellite path falls out for free**: the WS adapter declares it delivers 16 kHz/int16/mono → canonical
= no-op transform.

## 3. The harmonized component set (names locked)

| Component | Role | Used by | Layer |
|---|---|---|---|
| **`AudioTranscoder`** (rename of `utils/audio_helpers.AudioProcessor`) | the one transform primitive: rate + channels + sample-format, with `ConversionMethod` quality tiers | **input** negotiator **and** **output** (TTS→playback) | `utils` |
| **`AudioContract`** (new value object) | what a party can deliver / needs | every input adapter + audio consumer | `utils` |
| **`AudioNegotiator`** (new) | derive canonical, validate at startup (fatal), drive the transcoder, emit trace events | input boundary + output | startup: config path · runtime: boundary |
| **`VoiceSegmenter`** (rename of `UniversalAudioProcessor`, minus the if-else) | consume the active VAD provider; own pre-roll; emit `VoiceSegment`s | the audio workflow | `workflows` |
| **`VADPort` + `irene.providers.vad.*`** | per-frame `is_voice` engines (energy / silero / microvad) | the segmenter | `core/interfaces` + `providers` |

This collapses the two colliding `AudioProcessor`s and the 3 duplicated TTS resample blocks into one named,
direction-shared transcoder.

## 4. `AudioContract` (replaces the scattered capability methods)

Supersedes the per-provider `get_supported_sample_rates` / `get_default_sample_rate` / `supports_resampling`
/ `get_default_channels` (inconsistently consulted today):

```
AudioContract {
    supported_rates:    list[int]          # e.g. [16000]
    preferred_rate:     int
    supported_formats:  list[str]          # "pcm16" | "float32"
    preferred_format:   str
    channels:           int                # 1
    detection_latency_ms: int | None       # VAD only — drives pre-roll (§6)
}
```

Each **input adapter** (microphone / web / ws) declares what it *delivers*; each **consumer** (VAD / wake /
ASR provider) declares what it *needs*. The negotiator intersects them.

## 5. VAD as a lightweight provider family

The 8th provider family, but **without the component web/manager apparatus** (it's a per-frame hot-path
primitive, not a request/response service):

- `VADPort` (`core/interfaces/vad.py`) — `process_frame(AudioData) -> VADResult`, `reset()`,
  `detection_latency_ms` (property), `calibrate(frames) -> bool` **with a default no-op** (engines opt in).
- `irene.providers.vad`: `energy` (today's `SimpleVAD`/`AdvancedVAD`), `silero`, `microvad`. As adapters they
  may import `core/assets` directly — **the silero model-path injection workaround disappears**.
- Selection = the standard entry-points discovery + `default_provider` single-active pattern (the
  `voice_trigger` template), replacing the if-else. Config nests `[vad.providers.*]` like every component.

## 6. Pre-roll as a contract (Q1)

`VoiceSegmenter` sizes the pre-buffer from the **active VAD provider's `detection_latency_ms`**:
`preroll_frames = ceil(detection_latency_ms / frame_ms) + margin`. Energy ≈ `voice_frames_required·frame`;
silero/microvad ≈ their `min_speech_duration` / sliding window. This replaces the magic `4` and guarantees
the wake-word onset survives across engines and tunings (the segment feeds the wake word, so this is a
detection-correctness fix, not just nicety).

## 7. Transparency — first-class trace events

Every transform (`resample 44.1k→16k`, `downmix 2→1`, `int16→float32`) is recorded as a **trace event** via
the existing `trace_context`/observe vocabulary (ARCH-15), so a `/trace` shows the full chain end-to-end.
Plus a **one-time startup summary**: the negotiated canonical + every party's contract (and the fatal-error
detail when negotiation fails).

## 8. Symmetric output

The negotiator is built **both directions**: input derives canonical from consumers; **output** negotiates
TTS-rate → playback-device-rate through the *same* `AudioTranscoder`, also traced. This collapses the TTS
duplication and ties the audio-encoding layer of ARCH-15's output seam to the same machinery. (ARCH-15's
*modality* negotiation — degrade-then-drop — stays; this is the finer audio-encoding layer beneath it.)

## 9. Hexagon seams (new vs reused)

- **New:** `AudioContract`, `AudioNegotiator` (logic), `VADPort`, `irene.providers.vad`, the `[vad.providers.*]`
  schemas (auto_registry + config-ui get them like the QUAL-20 WakeWordSpec work).
- **Reused/renamed:** `AudioTranscoder` (was `AudioProcessor`), `VoiceSegmenter` (was `UniversalAudioProcessor`),
  `trace_context` (ARCH-15), the entry-points discovery + single-active selection (`voice_trigger`).
- **Layer check:** `utils` stays leaf (`AudioTranscoder`/`AudioContract` have no upward deps — ARCH-12 holds);
  `VADPort` in `core/interfaces`; VAD adapters in `providers` may reach `core` inward; `VoiceSegmenter` in
  `workflows` consumes the VAD component. No new backwards edges.

## 10. The two live bugs — folded in, not obsoleted

- `vad_implementation` validator (`models.py:457`, rejects `microvad`) → **deleted**; entry-points discovery
  is the source of "what engines exist," exactly like every other provider family.
- unconditional `calibrate_threshold` (`audio_processor.py:211`) → a `VADPort.calibrate` method with a default
  no-op; the segmenter calls the port, engines opt in.

Both are fixed *as a consequence* of the design (PR-2), so no separate patch is wasted.

## 11. Config shape

```toml
[vad]
enabled = true
default_provider = "energy"        # energy | silero | microvad (single-active)

[vad.providers.energy]
energy_threshold = 0.01
sensitivity = 0.5
# … the existing energy knobs

[vad.providers.silero]
threshold = 0.5
model_url = "…silero_vad.onnx"

[vad.providers.microvad]
threshold = 0.5

[audio]                            # optional canonical pin (else auto-derived)
# canonical_rate = 16000
# canonical_format = "pcm16"
```

The flat `silero_*` / `microvad_*` fields move under their provider; `vad_implementation` → `default_provider`.

## 12. Decisions (LOCKED 2026-06-10, design session)

- **D-1** Canonical transform-once; canonical **derived** (common denominator), config-pin optional, **fatal**
  if no canonical satisfies all parties.
- **D-2** VAD = **lightweight provider family** (port + providers + entry-points; no web/manager).
- **D-3** Contract scope = rate + channels + **sample-format** (int16/float32).
- **D-4** Transparency = **first-class trace events** + startup summary.
- **D-5** Names: `AudioTranscoder`, `VoiceSegmenter`, `AudioNegotiator`, `irene.providers.vad`.
- **D-6** **Symmetric** input+output through the one transcoder, both traced.
- **D-7** The 2 live bugs fold into PR-2.

## 13. Implementation slices (ARCH-18 unless noted)

1. **PR-1 — `AudioTranscoder` rename** (done 2026-06-10): rename `AudioProcessor` → `AudioTranscoder`
   everywhere (kills the `UniversalAudioProcessor` name collision). Behavior-preserving; pure rename.
   _Reconciliation:_ `AudioFormatConverter` turned out to be a **used, tested convenience layer** atop the
   engine (`convert_audio_data`/`_streaming` used internally + tested; `supports_format` used by the mic input),
   **not** the dead duplicate the original plan assumed — so its dissolution moved out of PR-1 (below).
2. **PR-2 — VAD provider family + `VoiceSegmenter`**: `VADPort` + `energy`/`silero`/`microvad` providers +
   entry-points + `[vad.providers.*]` config/schemas (config-ui via auto_registry); extract the if-else into
   the segmenter; **fold the 2 bug fixes**.
3. **PR-3 — `AudioContract` + `AudioNegotiator`**: declare contracts; derive canonical + startup validation
   (fatal) + input transform-once at the boundary; trace events. **Fold `AudioFormatConverter`'s
   convert/streaming into the transcoder/negotiator** (the rate/format/channel transform belongs on the one
   primitive) and relocate `supports_format` to a plainly-named file-format helper.
4. **PR-4 — symmetric output**: route TTS→playback through the negotiator/transcoder + collapse the 3
   duplicated TTS resample blocks; trace. **`AudioFormatConverter` is deleted by the end of ARCH-18** — its
   methods live on the harmonized transcoder/negotiator, no permanent second tier.
5. **PR-5 — pre-roll contract**: `detection_latency_ms` → `VoiceSegmenter` pre-roll sizing.
6. **PR-6 — user-facing docs + diagrams (END of ARCH-17/18)**: update `docs/guides/{vad,voice-trigger,audio}.md`
   and the architecture docs for the new component + negotiation seam; **re-author the affected dataflow/audio
   diagrams** in `docs/images/` (the mic→VAD→wake→ASR flow + the transform/negotiation seam — PNG/JPEG per the
   docs rules, no mermaid). This is the explicit final step, not an afterthought.

## 14. Relationships

- **ARCH-15** (`io_architecture.md`) — this is its input twin; shares `trace_context`, mirrors the negotiation
  shape (transform-or-error here vs degrade-then-drop there), and reuses the same `AudioTranscoder` for the
  output audio-encoding layer beneath ARCH-15's modality negotiation.
- **onnx_inference_layer.md §11.2** — **superseded**: the "small VAD seam" becomes this provider family.
- **ARCH-16** (deferred I/O daemon) — fits naturally: each input adapter declares its `AudioContract`; the
  negotiator derives canonical per pipeline at attach time.
- **QUAL-20** — the VAD provider family reuses the per-provider schema + config-ui pattern just built for wake
  words; `microvad`/`silero`/`energy` providers wrap the existing engines.
