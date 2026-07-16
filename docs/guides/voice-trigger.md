# Voice trigger (wake word)

The voice trigger listens for a wake word and only then wakes the rest of the pipeline, so Irene isn't
transcribing all day. It runs where Irene has a local microphone; on a Wirenboard install the ESP32
satellite does this on-device instead (its own product — see
[locveil-satellite](https://github.com/locveil/locveil-satellite)).

## Two providers

- **OpenWakeWord** (`openwakeword`) — general-purpose detection with pre-trained models, auto-downloaded.
  Runs on ONNX by default. The easy default for common English words.
- **microWakeWord** (`microwakeword`) — runs a **custom-trained** TF-Lite model via
  [pymicro-wakeword](https://github.com/OHF-Voice/pymicro-wakeword), which bundles the feature frontend and
  the runtime (no full TensorFlow). It's the same engine, and the **same model file**, the ESP32 satellites
  run on-device — so you train a wake word once and deploy it both places.

Exactly one provider is active, picked by `default_provider`. There's no fallback chain — they're
alternatives, not a cascade.

## Configuration

Wake words are declared **per provider**, as a list of entries with the same shape for both.
The component itself is switched on in the `[components]` block:

```toml
[components]
voice_trigger = true

[voice_trigger]
default_provider = "microwakeword"

[voice_trigger.providers.microwakeword]
enabled = true
wake_words = [
    { name = "irina", model = "irina", threshold = 0.97, language = "ru" },
    { name = "alexa", model = "alexa", threshold = 0.9, language = "en" },
]

[voice_trigger.providers.openwakeword]
enabled = false
inference_framework = "onnx"             # or "tflite"
wake_words = [
    { name = "hey_jarvis", model = "hey_jarvis", threshold = 0.7, language = "en" },
]
```

Each entry is `{ name, model, threshold, language }`:

- **`name`** — the label you'll see on a detection, and the key that lets a wake word *name a room*
  («Ирина» for the kitchen, «Валера» for the living room).
- **`model`** — where the model comes from. For microWakeWord, in order of preference: a **built-in**
  name (`alexa`, `okay_nabu`, `hey_jarvis`, `hey_mycroft` — English, bundled with the library, nothing
  to download), a **released catalog** word (`irina` — downloaded once into the models folder, like any
  other model), a **URL to a model manifest** (e.g. a [microwakeword.com](https://microwakeword.com/)
  model or one on Hugging Face — the model file is fetched along with it), or a **local path** to a
  manifest you just trained. For OpenWakeWord: a built-in name (`hey_jarvis`, `alexa`, `hey_mycroft`)
  or a path to a custom `.onnx`/`.tflite`.
- **`threshold`** — detection cut-off, 0–1. (microWakeWord models carry their own tuned cut-off in the
  manifest; the manifest's value wins for them.)
- **`language`** — two-letter tag, for your own bookkeeping.

Audio is 16 kHz / 16-bit mono PCM — the pipeline's canonical format, which the microphone is transformed to
once at the input boundary (see [audio](audio.md)).

## Russian wake words

Built-in models are English. Russian names are trained in-house and released as ready-to-use catalog
words — **«Ирина»** (`irina`) is the first: put it in `wake_words` and the model is fetched on startup
(published at [droman42/microwakeword-irina-ru](https://huggingface.co/droman42/microwakeword-irina-ru)).
More names («Валера», «Наташа») join the catalog as they validate. The same two files a catalog word
downloads are what an ESP32 satellite gets flashed with — server-side and on-device detection run one
artifact.

For a word that isn't in the catalog yet, point `model` at a manifest URL (a
[microwakeword.com](https://microwakeword.com/) model, or any hosted one) or at a local manifest fresh
out of training — that's how a new word is tested before it's released. Expect to listen for false
accepts on anything freshly trained; a model earns its catalog spot by holding up on real recordings.

## Dependencies

Each provider declares its own extra (64-bit only — on a Wirenboard the satellite wakes on-device, so the
server runs none of this):

| Provider | Extra | Pulls |
|---|---|---|
| OpenWakeWord | `wake-onnx` | `openwakeword`, `onnxruntime` |
| microWakeWord | `wake-tflite` | `pymicro-wakeword` |

`voice-trigger` installs both. Adding a different engine follows the [provider recipe](howto-new-model.md).

## Web API

The component mounts endpoints under `/voice_trigger`:

| Endpoint | Does |
|---|---|
| `GET /voice_trigger/status` | current state + config |
| `POST /voice_trigger/configure` | update wake words / threshold |
| `GET /voice_trigger/providers` | list providers |
| `POST /voice_trigger/switch_provider` | switch the active provider |

## Troubleshooting

- **Model not found** (microWakeWord) — check a custom entry's `model` points at a real `.tflite`/manifest.
- **Never triggers** — lower the entry's `threshold`, confirm the word is listed, and that audio is 16 kHz mono.
- **`irene` on OpenWakeWord does nothing** — OpenWakeWord only knows its English catalog; a custom Russian
  word needs microWakeWord (or a custom OpenWakeWord model file).
- **False triggers** — raise `threshold`, or retrain with more negatives.
- **Debug** — set the `locveil_voice.components.voice_trigger_component` and `locveil_voice.providers.voice_trigger` loggers
  to `DEBUG`.
