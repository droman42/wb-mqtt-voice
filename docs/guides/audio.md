# Audio

The audio component plays sound out — TTS replies, prompts, notifications. It's a capability with
interchangeable **playback providers**; which one you use depends on the platform and what's installed.
(Microphone *input* and resampling are configured alongside ASR; this guide is about output.)

## Playback providers

`[audio]` selects among four, discovered via `irene.providers.audio`. Every real backend **streams** raw
PCM straight to the device — there's no intermediate WAV file at playout:

| Provider | Needs | Platforms | Notes |
|---|---|---|---|
| **console** | nothing | all | headless/testing stub; the default and the fallback |
| **sounddevice** | `sounddevice`, `soundfile` + PortAudio & libsndfile | all | high-quality playback (`RawOutputStream`) + device enumeration |
| **aplay** | ALSA `alsa-utils` | Linux only | shells out to `aplay`, streams raw PCM over stdin |
| **miniaudio** | `miniaudio` | all | self-contained streaming — backends bundled in the wheel, **no system library** |

## Installation

The playback engines ship behind the **`audio-output`** extra (sounddevice, soundfile, miniaudio, plus
numpy/librosa). `sounddevice` and `aplay` need a system library; `miniaudio` brings its own:

- **sounddevice** — PortAudio + libsndfile: `libportaudio2 libsndfile1` (Debian/Ubuntu), `portaudio
  libsndfile` (Alpine/macOS).
- **aplay** — `alsa-utils`.
- **miniaudio** — nothing. Its WASAPI / CoreAudio / ALSA backends are compiled into the wheel, so it works
  cross-platform (including Raspberry Pi) with no system package.

`console` needs nothing either — which is why a fresh, model-free deployment still "speaks" (to the log).

## Configuration

```toml
[components]
audio = true

[audio]
enabled = true
default_provider = "sounddevice"
fallback_providers = ["console"]
concurrent_playback = false
playback_mode = "file"           # "file" = play the synthesized WAV; "stream" = conform + stream raw PCM
# output_rate = 44100              # optional: override the playback sink rate (else the provider's, else CD)
# output_channels = 2             # optional: override the playback sink channels
```

`components.audio = true` turns the component on; `[audio]` picks the provider and a fallback (`console` is
the safe fallback everywhere). **If you've declared local playback** (`system.audio_playback_enabled = true`),
enabling `[tts]` without `[audio]` is rejected at startup — TTS would have nowhere to play. A **headless box
with no speaker** (`audio_playback_enabled = false`, e.g. a satellite that streams its reply back to a remote
device) may run TTS with the Audio component off.

`playback_mode` chooses how a TTS reply reaches the speaker: `file` synthesizes to a temp WAV and hands the
file to the provider; `stream` conforms the audio **down to the sink** (below) and streams the raw PCM through
the provider's streaming backend. `stream` degrades to `file` automatically for text-only providers (e.g.
`console`) or if the audio negotiator isn't wired, so it's always safe to enable.

## Sample rates & hardware

**Input.** Irene derives one **canonical** internal format — 16 kHz / mono for a voice pipeline — and transforms
the captured audio to it **once** at the input boundary; a 44.1 / 48 kHz mic is downsampled there, and VAD /
wake / ASR all see the canonical audio. The canonical is computed from what the consumers need, so it's never
upsampled to invent detail; an impossible combination is a fatal error at startup. Capture-side rate and
`resample_quality` (`fast` · `medium` · `high` · `best`) live with the microphone input (see
[configuration](configuration.md)).

**Output.** TTS and other producers conform **down** to the playback **sink** — the output device's capability.
That capability is the active provider's (e.g. `sounddevice`'s configured `sample_rate` / `channels`), with an
optional `[audio] output_rate` / `output_channels` override, defaulting to **CD — 44.1 kHz / 16-bit / stereo**
when nothing's declared. Any device plays *lower*, so a 22 kHz TTS engine is played as-is and only audio that
*exceeds* the sink is downsampled — never upsampled. On a machine with several output devices, `sounddevice`
can target a specific one. (Only raw PCM/WAV is handled today; MP3/FLAC are not.)

## Troubleshooting

- **No sound** — confirm `components.audio` is on and `default_provider` isn't `console`; check the OS can
  play at all (`aplay test.wav`, `pactl list sinks`).
- **"No module / library" on startup** — the provider's system package is missing (PortAudio, libsndfile or
  ALSA, above), or the `audio-output` extra wasn't installed. (`miniaudio` needs no system package — if it
  fails, the wheel itself didn't install.)
- **Device not found / wrong output** — list devices (`aplay -l`, `pactl list`), select one, and make sure
  your user is in the `audio` group.
- **Distorted or wrong-speed playback** — a sample-rate mismatch; the output conform-down handles a producer
  that exceeds the sink, so check the sink itself (`[audio] output_rate`/`output_channels` or the provider's
  `sample_rate`) matches the device.

For choosing or adding the TTS engine that *generates* the audio, see [adding a model](howto-new-model.md);
for how the component sits in the pipeline, see [components](../architecture/components.md).
