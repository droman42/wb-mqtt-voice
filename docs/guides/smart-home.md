# Smart-home control

Irene can control a Wirenboard-based smart home by voice — lights, curtains, climate,
brightness, media pause, whole-house scenarios — and answer sensor questions like
«какая температура в спальне?». She does it through **wb-mqtt-bridge**, a companion
service that knows every device in the house; Irene itself never talks MQTT and never
hardcodes a device list.

## How it works

![How a spoken command becomes a device action](../images/smart-home-flow.png)

On startup (and whenever something looks stale) Irene pulls the **device catalog** from
the bridge: every room and device with its spoken names and aliases, what each device can
do, and which values are allowed. Your utterance is matched against that live catalog —
so adding or renaming a device on the bridge side needs **no change to Irene at all**.

Commands resolve only as deep as you phrase them:

- **A named device** («включи телек», «закрой тюль слева») becomes a command to that
  exact device. Names and aliases come from the catalog, and inflected forms work
  («поставь на радиаторах 22 градуса»).
- **A bare noun** («включи свет», «закрой шторы», «подними жалюзи») becomes a
  *room-level* command — the bridge picks the right device for that room, or fans out to
  all of them when you say «весь»/«все» («выключи весь свет в спальне»).
- **No room mentioned** — the room you're speaking from is assumed; name another room to
  reach it («включи свет в детской», «в зале», even «во всей квартире»).

When a request is genuinely ambiguous — «поставь на паузу» in a room with both a TV and
an Apple TV — Irene asks which one you meant, and your next reply answers just that
question. Out-of-range values get corrected before anything is sent («Значение от 5 до
30 °C»), and if a device doesn't respond during a room-wide command, Irene tells you
which one («…, но не ответили: Бра»).

Scenario devices work like everything else: «включи кино с видеокассеты» starts the
scenario whose name matches, «выключи кино» stops it.

Sensor questions are read live from the bridge: «какая температура в душевой?»,
«какая влажность?» — dedicated sensors are preferred, and on climate units Irene reads
the measured room temperature, not the thermostat setting.

Inputs and apps are voice-switchable too: «переключи усилитель на cd» validates the
input against the device's own set, and «запусти youtube на телеке» asks the device
for its installed apps at that moment — so a newly installed app is launchable
immediately, with no configuration anywhere. If the name doesn't match, Irene reads
back what *is* available.

## Enabling it

Point Irene at your bridge in the configuration (`[outputs.bridge]` section, editable in
the config UI under **Output Channels**):

```toml
[outputs.bridge]
enabled = true
base_url = "http://localhost:8000"   # your wb-mqtt-bridge REST endpoint
timeout_seconds = 5.0
```

That's the whole setup: the catalog pull, the room vocabulary, and the device commands
all follow from it. With the bridge disabled or unreachable, smart-home phrases get an
honest spoken answer («умный дом не подключён») and everything else keeps working.

## Current limits

- Ambiguous same-room requests always ask a clarifying question; configurable
  preferences (e.g. "degrees means the heater") are planned.
- App and input names are matched as the device reports them (usually Latin —
  "YouTube", "hdmi1"); speaking them in Cyrillic («ютуб») is planned.
- English phrasing is supported at a basic level; the primary vocabulary is Russian.
