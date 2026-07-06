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

Volume, playback and household modes answer to voice as well: «сделай громче», «громкость
на телеке 30», «следующий трек», «мы уходим», «режим уборки на 30 минут», «включи
сигнализацию воды». Water valves and heating circuits deliberately have no voice surface.

Inputs and apps are voice-switchable too: «переключи усилитель на cd» validates the
input against the device's own set, and «запусти ютуб на телеке» asks the device
for its installed apps at that moment — so a newly installed app is launchable
immediately, with no configuration anywhere. Latin names answer to their Russian
pronunciation («ютуб» finds YouTube, «эппл ти ви» finds Apple TV), and if a name
doesn't match, Irene reads back what *is* available.

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

## Teaching her your words

Two layers of understanding are at work. The **built-in vocabulary** recognizes commands
instantly and fully offline. Phrasings outside it — slang, unusual word order — fall
through to an **LLM fallback** (enabled in the shipped configurations): «вруби телек» or
«глуши магнитофон» still work when an LLM API key is configured, and without one Irene
simply says she didn't understand rather than guessing.

If a phrase your household actually uses keeps landing on the fallback, you can promote
it into the built-in vocabulary yourself. Command phrases live in *donation* files under
`assets/donations/` — one folder per skill, one file per language. For example, to make
«вруби» a first-class "turn on" verb, find the `_handle_power_on` entry in
`assets/donations/smart_home_handler/ru.json` and add the word to its `phrases` list:

```json
{
  "method_name": "_handle_power_on",
  "phrases": [
    "включи",
    "включить",
    "зажги",
    "вруби"
  ]
}
```

That's the whole change — after a restart the word is recognized offline, with no code
involved. Keep each phrase specific to one command: a word that could mean two different
things (like «поставь») belongs in the more specific entry («поставь таймер»), so the
commands don't compete. The same files can be edited visually in the config UI, which
also validates the format as you type.

## Current limits

- Ambiguous same-room requests always ask a clarifying question; configurable
  preferences (e.g. "degrees means the heater") are planned.
- Relative adjustments («сделай поярче», «сделай потеплее») are recognized but ask for
  an absolute value; adjusting from the current state is planned.
- One command per sentence: «яркость 30 и температуру 22» and exceptions like «весь свет
  кроме торшера» are not split yet. Pronouns need the device named («сделай его погромче»
  won't find "him").
- English phrasing is supported at a basic level; the primary vocabulary is Russian.
