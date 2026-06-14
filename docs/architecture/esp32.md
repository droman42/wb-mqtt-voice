# ESP32 voice satellite

A voice satellite is a cheap microphone-and-speaker node in a room. It does the parts that have to be local
— capture audio, run a wake word, play a reply — and leaves the thinking to Irene over the network. One
Irene can serve a house full of them.

> **Status: Irene's side built, firmware pending.** The WebSocket transport, the identity handshake, *and*
> the spoken reply back to the device all exist today (`/ws/audio` in, `/ws/audio/reply` out). What's left is
> the **ESP32 firmware**: mic capture, the on-device wake word (a per-satellite microWakeWord model, loaded at
> runtime from a flash partition so a new word doesn't need a reflash), and playing the reply. The whole
> satellite — wire protocol, provisioning, models, OTA — is laid out in the
> [satellite design](../design/esp32_satellite.md).

## A turn

![A satellite turn](../images/esp32-turn.png)

When a satellite connects it **registers once**: it tells Irene its room and the devices in it, which Irene
records as the connection's identity. Then, per utterance:

- the **wake word fires on the device** — each satellite carries its own word as a small tflite model, so
  Irene isn't streaming or transcribing all day;
- the satellite **streams the audio** to Irene over the open socket;
- Irene runs the full pipeline — **ASR → NLU → intent** — exactly as for any audio input;
- the **spoken reply comes back as audio** — Irene synthesizes it, conforms it down to what the satellite can
  play, and streams it over a **second socket the satellite keeps open for output**; a short text
  acknowledgement still returns on the input socket.

To Irene this is simply an **input adapter** of format `audio` with the wake word already done — no special
case. The satellite is thin on purpose: no models, no intent logic, just ears and a mouth.

## How it fits

![Voice satellites in the picture](../images/esp32-fit.png)

The wake word is also how you choose a room. Each satellite is trained for its **own** word — say "Irene"
in the kitchen, "Boris" in the living room — so the word you speak already selects the node, and the node
already knows its room (it said so at registration). The command is scoped before Irene has parsed a thing:
"включи свет" addressed to the kitchen node means the *kitchen's* lights. Any territorial division in the
house works this way, not only rooms — the wake word names the territory.

That same room/device identity is what the smart-home layer addresses ([MQTT](mqtt.md)), and what a
deferred result uses to find its way home: a timer set at the kitchen node speaks at the kitchen node.

Many ears, one brain — the heavy machinery lives in a single Irene; the rooms just need cheap nodes that
listen and speak.
