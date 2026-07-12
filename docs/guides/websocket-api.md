# WebSocket API

**Protocol version: 1** (`ws-protocol-v1`) — the server confirms it as `protocol_version` in
every `registered` ack, so a client can check what it was built against instead of trusting
prose. The version only moves on a breaking wire change.

Irene exposes four WebSocket channels. Two of them are the **voice wire protocol** — how a
satellite (an ESP32 in a room, or any client with a microphone) streams speech in and gets the
spoken reply back. The other two are **operator channels** — a push channel for deferred text
results and a live tap on the pipeline's event bus. REST endpoints are documented interactively
at `/docs`; this guide is the equivalent reference for the sockets.

![The four WebSocket channels](../images/ws-protocols.png)

Every channel speaks the same dialect: **JSON text frames** for control (each carries a `type`
field) and **raw binary frames** for audio. Audio is always **16-bit little-endian PCM, mono**;
16 kHz is the pipeline's canonical rate — declare your real rate at registration and keep it
honest, the server does not guess. On any protocol violation the server answers
`{"type": "error", "error": "..."}`.

## `/ws/audio` — voice input

The driving input for a device that already did wake-word detection on its own hardware (the
satellite case). One connection serves **many utterances**; the session — and with it room and
conversation continuity — lives as long as the socket.

**1. Register.** The first frame must be a text frame:

```json
{
  "type": "register",
  "client_id": "kitchen_node",
  "room_name": "Кухня",
  "sample_rate": 16000,
  "wants_audio": true,
  "mode": "streaming",
  "wants_trace": false
}
```

`client_id` is the device's stable identity — replies, timers and missed announcements are
addressed to it. `room_name` is the device's primary room; `covered_rooms` (optional list) adds
rooms it also manages. `wants_audio: true` asks for spoken replies — which arrive on the
**reply channel** (below), never on this socket. `wants_trace: true` (default `false`) asks for
the server's execution trace after each response — see **Execution traces** below. Optional
extras: `name` (human-friendly device name) and `available_devices` (what the device can
actuate — reserved for the smart-home integration).

A device should also report what it was **built against** — three optional version fields:
`protocol_version` (the protocol version its client code implements), `firmware_version`
(its own software version; the bundled satellite runner sends the Irene package version),
and `wake_pack_version` (the wake-word pack it has flashed, e.g. `"wake-pack-v1"` — for
devices that do their own wake-word detection). None of them gates registration; they let
the server's client registry spot a stale device instead of debugging it blind.

The server confirms: `{"type": "registered", "client_id": "...", "session_id": "...",
"trace": false, "protocol_version": "1"}` — `trace` is the explicit answer to `wants_trace`
(it stays `false` unless the server's operator has enabled remote trace requests), and
`protocol_version` is the server's wire-protocol version (the number at the top of this
document): if it isn't what your client was built against, expect breakage and say so loudly.

When the connection comes through the fleet's mutual-TLS gate, the certificate is the
identity: a `client_id` that doesn't match the certificate's common name is refused at
registration. Plain connections on a trusted network are not affected.

**2. Stream audio.** Send binary PCM frames. What ends an utterance depends on the mode:

- **`mode: "streaming"`** — for always-on devices. If the configured speech recognizer supports
  true streaming, the **server** detects the end of the utterance from the audio itself; the
  device just keeps streaming (silence included) and never needs to signal anything. You'll
  receive `{"type": "partial", "text": "..."}` frames as recognition progresses. A device may
  still send `{"type": "end"}` to hard-finalize, and a client that stops sending mid-utterance
  is finalized after a 10-second idle timeout rather than left hanging.
- **default (batch)** — for push-to-talk-style clients. Stream the utterance's PCM, then send
  `{"type": "end"}`. As a safety net, an utterance is force-finalized at 60 seconds if the end
  frame never comes.

**3. Get the result.** One frame per utterance:

```json
{
  "type": "response",
  "text": "Таймер на 5 минут запущен",
  "success": true,
  "error": null,
  "confidence": 1.0,
  "intent_name": "timer.set",
  "timestamp": 1750000000.0,
  "metadata": { "...": "raw execution metadata" }
}
```

This is the same canonical result shape the REST `/execute/command` endpoint returns — `text`
is the reply, `intent_name` says what was recognized, `success`/`error` report the outcome.
Then the loop re-arms for the next utterance.

**4. Execution traces (optional).** If registration asked for traces *and* the server granted
them (`"trace": true` in the confirmation), each response is followed by exactly one extra
text frame:

```json
{ "type": "trace", "request_id": "…", "trace": { "…": "the full execution trace" } }
```

The payload is the same self-contained trace document the server's own tracing writes —
every pipeline stage with its timing, the recognition verdicts, the recorded output (see
[tracing & replay](tracing.md)). Granting is the server operator's decision:
`[trace] allow_remote_request = true` in the server's configuration; without it,
`wants_trace` is answered with `"trace": false` and no trace frames are ever sent. A client
that didn't ask never sees this frame — firmware can ignore the feature entirely by
registering with the default.

## `/ws/audio/reply` — spoken replies

The return half of the satellite pair. The device opens this socket, registers, and then only
**listens** — the server pushes synthesized speech whenever a reply (or a later event, like a
timer firing) is addressed to this device.

Register with the device's *output* audio contract:

```json
{ "type": "register-reply", "client_id": "kitchen_node", "audio_out": { "rate": 22050, "channels": 1 } }
```

The same certificate rule as `/ws/audio` applies behind the mutual-TLS gate: a device can only
claim its own reply channel — otherwise it would receive another room's speech.

After `{"type": "registered", "client_id": "...", "protocol_version": "1"}`, each spoken
reply arrives as a bracketed binary burst:

```
{"type": "speak_begin", "rate": 22050, "channels": 1, "width": 16, "seq": 1}
<binary PCM frames>
{"type": "speak_end", "seq": 1}
```

The audio is already converted to the rate/channel count you registered — play it as it comes.
`seq` pairs the begin/end brackets. One more thing happens at connect time: if anything fired
while the device was offline — a timer that rang during a reboot — the missed announcement is
spoken to the device as soon as the channel is up.

## `/ws/output` — pushed text results

The push channel for text clients (the built-in web app uses it). Synchronous commands get
their answer in the HTTP response of `POST /execute/command`; this socket exists for the
**deferred** results — a timer set from the browser fires ten minutes later, and the
notification needs somewhere to go.

Send a first frame with your identity, or an empty `{}` to have one minted:

```json
{ "client_id": "web_abc123" }
```

The server answers `{"type": "connected", "client_id": "web_abc123"}`. Include that same
`client_id` in your `POST /execute/command` metadata, and deferred results addressed to it
arrive here as `{"type": "message", "text": "..."}` frames. Requires `[outputs] web_push`
(on by default).

## `/ws/observe` — live pipeline tap

A read-only debugging tap on the event bus: watch inputs arrive, results being produced and
outputs delivered, live, for the whole system or one room. Off by default — it exposes what the
household says. Enable it by setting `[system] observe_token`; remote (non-localhost) access
additionally needs `[system] observe_allow_remote = true`.

Authenticate and optionally filter in the first frame:

```json
{ "token": "...", "filter": { "room_name": "Кухня", "types": ["result.produced"] } }
```

After `{"type": "subscribed"}`, events stream in:

```json
{ "type": "event", "event": "result.produced", "session_id": "...", "client_id": "kitchen_node",
  "room_name": "Кухня", "source": "ws_audio", "payload": { "...": "..." }, "timestamp": 1750000000.0 }
```

The filter accepts `types`, `session_id`, `client_id`, `room_name` and `source`; omit it to see
everything. See [the workflow guide](../architecture/workflow.md) for what the events mean.

## Trying it from Python

A minimal batch-mode exchange, start to finish:

```python
import asyncio, json, wave, websockets

async def say(wav_path: str):
    async with websockets.connect("ws://localhost:6000/ws/audio") as ws:
        await ws.send(json.dumps({"type": "register", "client_id": "probe",
                                  "room_name": "Тест", "sample_rate": 16000}))
        print(json.loads(await ws.recv()))          # {"type": "registered", ...}
        with wave.open(wav_path, "rb") as w:        # 16 kHz mono PCM16
            await ws.send(w.readframes(w.getnframes()))
        await ws.send(json.dumps({"type": "end"}))
        print(json.loads(await ws.recv()))          # {"type": "response", "text": ...}

asyncio.run(say("command.wav"))
```

For scripted testing against these endpoints, the evaluation suite in [`eval/`](../../eval/README.md)
drives `/ws/audio` with recorded fixtures — see [how to add a test](howto-new-test.md).
