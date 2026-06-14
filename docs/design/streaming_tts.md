# Streaming TTS + output-seam delivery unification (ARCH-21)

**Status:** DRAFT 2026-06-14 · backs **ARCH-21** · follows **ARCH-20** (streamable audio *output*; this is the
producer twin) · builds on **ARCH-14/15** (the output seam) · substrate for **ARCH-6/QUAL-45** (ESP32-over-WS) ·
intersects **ARCH-9/10** (sherpa-onnx TTS).

## 1. Problem

ARCH-20 made the *playback* path stream raw PCM, but the **TTS producer is file-only at the contract level**:
the only synthesis primitive is `TTSProvider.synthesize_to_file(text, output_path)` (and the capability port
`TTSPlugin.speak/to_file`). Every consumer synthesizes to a temp WAV and reads it back. As a result:

- **ARCH-20 PR-4's `stream` mode is an interim bridge** — `synthesize_to_file → parse_wav → to_sink →
  play_stream`. It gains the §8 conform-to-sink and the real streaming backend, but **no latency win** (it waits
  for the full file); the `parse_wav` step exists *only* because the port can't hand back PCM. It is retired the
  moment the port can stream.
- **Delivery is fragmented across three surfaces** doing the same "synthesize + emit" logic:

  | Path | Where | Role | Playout today |
  |---|---|---|---|
  | `_handle_tts_output` | `workflows/voice_assistant.py:233` | synchronous in-turn reply | `play_file` / (PR-4) `play_stream`+conform |
  | `AudioSpeechOutput.deliver` | `outputs/audio.py:51` (ARCH-15 `OutputPort`) | deferred / fire-and-forget | `synthesize_to_file`→`play_file` — **PR-4 did NOT touch this** |
  | `WS /tts/stream` + `/tts/binary` | `components/tts_component.py:782/1041` | remote streaming to a socket | synth→WAV→read→**chunk a finished buffer** |

## 2. Decisions

### D-1 — Delivery belongs at the **output seam**, not in the TTS component and not as an audio provider.
- An audio **provider** is a config-selected, singleton, *local-device* backend (`default_provider`). A WS client
  is dynamic and **per-connection**, declaring its own contract at registration — a poor fit for the provider
  abstraction (it would force the audio component to own a client registry + routing, which is the
  `OutputManager`/`ClientRegistry` job).
- Leaving WS delivery **in the TTS component** conflates synthesis (the capability) with transport (an output
  concern) and duplicates the chunk-and-send loop.
- **TTS becomes a pure producer of a PCM stream.** A remote client is an `OutputPort` / remote **`AudioSink`**
  sibling to `AudioSpeechOutput`, consuming that stream via the shared `play_stream`/`AudioSink` contract with
  `AudioNegotiator.to_sink` doing the conform. Foreseen by `audio_pipeline.md` §8 D-13. **Audio providers stay
  local-device-only.**

### D-2 — Keep every TTS provider; **simulate** streaming by default, **override** where the engine supports it.
"Streaming" at the delivery layer is a buffering/chunking concern, **decoupled** from whether the engine streams.
Dropping non-streaming engines would leave only elevenlabs (cloud/paid/online) and gut the offline-first RU local
stack (silero/vosk). So:
- **Base-class default** `synthesize_to_stream` = synth→read→yield PCM chunks (covers *every* provider, incl.
  file-native ones, with no per-provider work).
- **Native overrides** where the engine does better (see §4).

### D-3 — The port grows a streaming method; `synthesize_to_file` **stays**.
File output remains the `/tts` file deliverable and the `playback_mode="file"` path. The port gains a second,
additive method — it does not replace the first.

## 3. Target shape

```
TTS provider (producer)                Output seam (delivery)                 Sink
  synthesize_to_stream(text)  ──PCM──▶  OutputManager / AudioSink  ──to_sink──▶  local device (audio provider)
  [base sim | native override]                                                   remote WS/binary client
                                                                                 ESP32 satellite
```

- Producer yields raw PCM frames (+ rate/channels/width), the same contract ARCH-20 established for `play_stream`.
- The sink conforms DOWN (`to_sink`, §8) and consumes the `AsyncIterator[bytes]`.
- Local playback, deferred F&F, and remote streaming all become *sinks behind one seam* — the three paths
  collapse into one.

## 4. Per-engine capability matrix (PR-3 status)

| Provider | Engine reality | Native streaming | PR-3 outcome |
|---|---|---|---|
| **silero_v4** | `apply_tts()` → tensor (same call `synthesize_to_file` uses) | whole utterance | **override DONE** — `apply_tts` → `float_to_pcm16` → PCM stream (no WAV round-trip) |
| **silero_v3** | `save_wav()` today; `apply_tts` available | whole utterance | **override DONE** — `apply_tts(put_accent/put_yo)` → int16 PCM (base sim was a working fallback) |
| **elevenlabs** | API → **MP3** bytes | true network streaming | **override DONE** — request `output_format=pcm_<rate>` (signed-16 mono); base sim was BROKEN (MP3 ≠ WAV). True incremental network streaming deferred (PR-4-adjacent) |
| **vosk** | `synth.synth(text, path)` | no | base simulation (WAV read-back) — works as-is |
| **pyttsx** | `engine.save_to_file()` | no | base simulation (WAV read-back) — works as-is |
| **sherpa-onnx TTS** (ARCH-9/10, future) | VITS, per-chunk **generation callback** | yes (callback) | override when the provider lands |
| **console** | writes text | n/a | degenerate — base sim raises `NotImplementedError`, caller falls back to file |

**Caveats:** elevenlabs `pcm_44100` needs a paid tier (default `pcm_22050`); silero overrides are whole-utterance
(no latency win vs base sim, but they skip the temp-file round-trip); a broken neural override degrades to file
playback (the conform helper returns `False`). True low-latency token streaming = elevenlabs `/stream` + sherpa
callback, addressed when the remote-sink path (PR-4) lands.

## 5. Slices (proposed)

- **PR-1 — Port + base simulation.** Add `synthesize_to_stream(text, **kw) -> AsyncIterator[bytes]` to
  `TTSProvider` with a concrete base default (synth temp WAV → `parse_wav` → yield PCM chunks). Component-level
  `synthesize_to_stream` on the TTS component. No behavior change yet — every provider can now stream.
- **PR-2 — Local playout consumes the producer.** `_handle_tts_output` `stream` mode and `AudioSpeechOutput`
  both switch to `synthesize_to_stream → to_sink → play_stream`; retire PR-4's `parse_wav` bridge; bring the
  ARCH-15 output port onto the same conform+stream path (fixes the PR-4 inconsistency).
- **PR-3 — Native overrides.** silero_v4/v3 (samples), elevenlabs (true stream + MP3 decode). Capabilities
  matrix doc finalized.
- **PR-4 — Output-seam remote sink.** Move WS `/tts/stream` + `/tts/binary` out of the TTS component into a
  remote `AudioSink`/`OutputPort`; retire the duplicate handlers; route via `OutputManager`. Substrate for
  ESP32-over-WS.

## 6. Open questions

- Streaming unit: byte-chunk iterator vs sentence-segmented synth (latency vs simplicity)?
- `AudioSink` contract registration shape for remote clients (ties to ARCH-6 `ClientRegistry`).
- Does `synthesize_to_stream` carry `(rate, channels)` out-of-band (return a header first) or via a typed
  result object? (ARCH-20 `play_stream` takes them as kwargs — mirror that.)
- Trace integration (ARCH-19): a streamed synthesis should still record a synthesis stage.
