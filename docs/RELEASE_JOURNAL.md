# Irene — Release Journal

The single **active** chronological log for the release effort ("what happened, when, and why"). Append-only;
newest entries near the top of each dated section.

- **This file holds NO task status and NO scope.** The authoritative task ledger (scope + status) is
  [`RELEASE_PLAN.md`](./RELEASE_PLAN.md); findings/rationale live in `docs/review/*` + `docs/design/*`.
- Entries reference task IDs (e.g. `QUAL-27`) but never assert their status — check the ledger for that.
- **Older entries are frozen in archives** (`one-active-journal`), newest first:
  [`docs/archive/journal/2026-06-15_to_2026-06-22.md`](archive/journal/2026-06-15_to_2026-06-22.md)
  (2026-06-15 … 2026-06-22), [`docs/archive/journal/pre-2026-06-15.md`](archive/journal/pre-2026-06-15.md)
  (2026-05-31 … 2026-06-14). This file keeps **2026-06-23 onward**; grep an archive when reconciliation needs older history.

---

## Action journal

- **2026-07-06 — BUILD-12 DONE — the reporting loop closed, live, and immediately did its job.**
  Bootstrapped `../wb-user-reports` (repo, labels, workflows, lens files, secrets, app install,
  PATs) and ran the real smoke: «сообщи о проблеме» through the web API produced a ticket + a
  committed bundle, and the triage workflow — one Claude, voice lens — analyzed it, labelled
  `fix-pr-open`, and OPENED a fix PR on wb-mqtt-voice. Every leg of device→ticket→triage→PR
  worked. The smoke earned its keep by flushing three CI-config gaps the authored workflow
  couldn't reveal without running (`id-token: write`, `GH_TOKEN`, and the decisive one:
  `--allowedTools`, whose absence silently denied all 26 of Claude's tool calls across two
  confusing green-but-inert runs). Loop safety proved itself too — the bot's own edits
  re-fired the workflow and were correctly skipped. The opened PR #1 claims a durable-action
  restart bug: plausible, touches the right files, but read from a bundle full of MY dev-session
  process kills — so it is a PROPOSAL for owner review, exactly what the design intends. That
  the bot can safely open a PR at all is the whole point of the leak-fence + human-review model.
  The workstream now needs only ARCH-33 (`/inbox`) to give that review its interactive home —
  PR #1 is its first customer.


- **2026-07-06 — BUILD-12 authored + ready (awaiting owner actions) — the reports repo in a
  box.** Everything `wb-user-reports` needs, authored as the SIBLING working copy
  `../wb-user-reports/` (git-initialized, content committed — the user corrected the first
  placement under `ops/`: repos in this constellation are siblings owning their own files;
  a mirror here would drift) and validated:
  the triage workflow (loop-safe, per-ticket concurrency, both codebases checked out, the
  D-11 model pinned in exactly one env var), the two lens process files (dedup-first, repro
  recipes, four outcomes, the §7.3 handover schema verbatim, ping-pong guard, replies drafted
  in the reporter's language), the 30-day retention pruner (stamp-parsed, logic unit-tested),
  and an idempotent `bootstrap.sh` that does repo+labels+push+checklist-issue in one run. A
  worthy note: the permission fence BLOCKED the agent from `gh repo create` on the owner's
  account — which is exactly where the design put the owner boundary anyway; the script now
  IS the owner's one-command step, followed by the app-install/secrets/PAT clicks no script
  can do. Completion criterion: the live smoke — «сообщи о проблеме» → ticket → triage run.


- **2026-07-06 — ARCH-32 DONE — the bundle, the sink, and a promise that survives reboots.**
  The delivery half of problem reporting: an always-on ring of request synopses (the diagnosis
  material trace persistence would carry if it were on — added as a deliberately DEFENSIVE tap
  after the coverage suite instantly proved that a diagnostics buffer can crash a pipeline),
  a bundle collector whose redaction strips every secret-shaped value while keeping household
  context (the repo is private — that's the design's whole point), the two-call GitHub client,
  and a service that spools to durable state BEFORE touching the network. The nicest part is
  the offline story: «отправлю, как только появится связь» is exactly the kind of promise the
  durable-actions invariant exists for, so it IS one — a durable `report_retry` action with a
  48-hour window, re-armed across restarts, completing in the reporter's language. User guide
  + diagram shipped; README Highlights gained the bullet (user) and lost a stale «planned» on
  smart-home. Suite 1327, device gate 48/48. BUILD-12 (repo bootstrap + owner checklist) is the
  remaining gap between this code and a real filed ticket.


- **2026-07-06 — ARCH-31 DONE — the problem-report dialog, and the capture that must not obey.**
  The heart of the build is a single inversion: for one turn, Irene deliberately does NOT
  understand you. Verbatim mode on the pending-clarification state makes the workflow consume
  the next utterance raw — no text processing, no NLU, no QUAL-44 arbitration — because a
  problem description («свет в спальне не включается») IS a confident smart-home command to the
  matcher, and executing it instead of recording it would be the feature disproving itself. The
  test suite pins exactly that. Expiry per D-5 (90 s, configurable) dies silently; cancel words
  end it politely; with `[reports]` disabled the intent answers «Отправка отчётов не настроена»
  at turn one and never arms. One discovery the smoke net caught: handlers register via
  pyproject ENTRY-POINTS, not by existing as files — the report handler booted only after the
  registration (+ a lesson relearned: bare `uv sync` strips extras AND the editable eval-commons;
  full-extras + `make setup` restore). All 8 configs updated (master + example + 6 docker:
  handler lists; [reports] section in master/example), config-ui type parity green. Suite 1318,
  device gate 48/48, donation gate 15/0/0. Next: ARCH-32 (bundle + delivery).

- **2026-07-06 — ARCH-30 DONE (same-day interactive design session) — problem reporting
  end-to-end, design AGREED.** «Сообщи о проблеме» → verbatim-captured description → support
  bundle → private ticket → GitHub-Claude triage → fix PRs / handovers / owner escalations.
  The session's pivotal finding: both code repos are PUBLIC, so the naive "file an issue in the
  voice repo" would publish the household's logs and rooms — the design landed on a private
  triage home (`wb-user-reports`, shared intake with the future bridge UI button) which then
  SIMPLIFIED the original two-Claude choreography into one Claude with two lens process files,
  handover by label flip on the same ticket. Alternatives weighed at the user's request (Google
  Drive / Yandex Disk / Jira) — all lose to "the ticket must be a GitHub issue for the Claude
  action to trigger at all". Other decisions: verbatim capture checked BEFORE QUAL-44 (a problem
  description must never execute as a command), bundle carries the last-10 turns + action records
  + a new always-on 5-trace ring (Q2 "is it the previous utterance?" — no, measurably), ARCH-27
  durable spool for offline, 30-day bundle retention, leak fence, replies pre-drafted in the
  reporter's language, `claude-fable-5` pinned for the whole triage run (D-11 — volume is
  household-scale; capability dominates on unattended code work). Implementation filed:
  ARCH-31/32/33 + BUILD-12 here, VWB-25 to the bridge (uncommitted).

- **2026-07-06 — BUG-26 + BUG-27 + QUAL-71 DONE (one live-testing session, three fixes).**
  The user's config-example session kept paying out. **BUG-26:** «расскажи о себе» belonged to
  system.about all along (the literal phrase is authored there) but lost to conversation.reference
  on an EXACT raw-score tie — the hand-authored boosts cancelled the QUAL-64 specificity edge to
  the fourth decimal (1.4256 == 1.4256) and the sort fell to donation load order. The matcher now
  tie-breaks on matched-pattern token count then intent name (never load order), and about's boost
  went 1.1 → 1.2; the self-introduction now answers offline. **BUG-27:** "12:54 PM" in a Russian
  reply — the ru donation's default_value "12hour" preempted the handler's own natural-language
  default; ru default → verbose, and explicit ru 12-hour speaks the day period in words («1:11
  дня»). **QUAL-71:** seven hardcoded Russian strings swept from handlers into templates (ru+en),
  with a new `_template_or` base helper for error paths so a template problem can never mask the
  original failure being reported. Suite 1307, device gate 48/48, pyright 0.

- **2026-07-06 — BUG-25 DONE (filed + completed same day) — the CLI was eating every other
  command, and had been since ARCH-15.** The user's first real multi-turn CLI session exposed
  it: «привет» answered, «расскажи о себе» vanished — the log shows the second utterance never
  reached NLU at all. Two consumers were racing `CLIInput`'s single queue: the runner's
  interactive loop and `InputManager._listen_to_source`, which fed an internal queue nothing
  drains — the dataflow review's P0-8 dead pipe, still alive and STEALING alternate commands
  (PR-5b had fixed the double reader but missed the double consumer). The dead pipe is deleted,
  not repaired: the manager owns source lifecycle only. Second symptom, same session: the reply
  printed OVER the already-drawn next prompt, so the terminal looked hung until the next Enter —
  fixed with `prompt_async` + `patch_stdout`, which also means a timer firing minutes later now
  prints above a live prompt instead of through it. Interactive multi-turn was simply never
  exercised before — every prior session was single-command. Two regression tests pin both
  halves; suite 1302.

- **2026-07-06 — QUAL-70 DONE (filed + completed same day, user) — a clean REPL.** The CLI's
  console was a log firehose with an `irene>` prompt drowning in it. Two sources silenced:
  the root console handler (interactive runners now log to file + trace only — `--debug`
  brings the console back on purpose) and the embedded background uvicorn (its own handlers
  bypass root logging entirely; now built with `log_config=None` so it propagates to the
  file like everything else). The foreground webapi server is untouched — docker logs
  depend on its console output. The CLI now shows exactly: banners, prompt, replies.

- **2026-07-06 — REL-2 DONE — the first-run story, written by a live stumble.** The morning's
  bare-`irene-cli` transcript became the acceptance test, and everything followed from it.
  `configs/config-example.toml`: a curated text-first starter — hybrid NLU only, zero downloads,
  zero keys, web API alongside, smart_home enabled with the bridge off (so the first device
  command earns the honest «умный дом не подключён» instead of a mystery) — and every disabled
  capability comments which config-master section to lift. The silent default-config fall-back is
  gone from the CLI/WebAPI runners (it could NEVER work — the built-in default has an empty NLU
  provider list): bare and `--headless` runs now stop with directions naming the example config,
  `IRENE_CONFIG_FILE`, and the QUICKSTART. README lost its stale "smart-home not yet built /
  not packaged" status (both false since ARCH-8 and BUILD-11) and gained the first-run one-liner;
  QUICKSTART finalized around example-first flow with console-script invocations. Verified live:
  example boots, «который час» answers, «включи свет» degrades honestly; suite 1300; config gate
  13/13; pyright 0. The exit-criterion checkbox for docs/quickstart flipped — REL-3 + ARCH-25 are
  all that remain.

- **2026-07-06 — DOC-8 DONE — the data-models map, shipped where it belongs.** The task predates
  the `docs/architecture/` family, so the deliverable moved there (user: user-facing naming, family
  prose, diagrams): `docs/architecture/data-models.md` + `docs/images/data-models.dot/png`. The
  page reframes the request-vs-session confusion as **three lifetimes** — dies with the request
  (RequestContext as routing+identity-never-memory, Intent deliberately session-blind, IntentResult
  with the failure-carries-reason contract, the audio primitives), lives with the session (a session
  is a ROOM; windowed single-writer history; pending clarification; ~30 min expiry; one minting
  path), survives restarts (the registry, physical identity — why a timer still knows its room).
  Facts verified against today's code rather than transcribed from the defect-era QUAL-25 snapshot
  it distills. Linked from README's architecture list; cross-linked from dataflow.md.

- **2026-07-06 — BUG-5 DONE (pulled forward from deferred — an EN tester is waiting) — donation
  EN enrichment, smart_home included.** The BUG-4-era gap held almost exactly (27 alias params,
  10 choice params). EN aliases added everywhere; EN choice surfaces ONLY for concept choices
  (language, timer units, quality, component) — identifier choices (provider/voice names) got
  nothing on purpose: canonicals self-match in EN. smart_home was structurally at parity but
  phrase-thin on 9 methods (menu-nav had 2 EN phrases vs 9 RU) — enriched. The valuable catch
  came from A/B probing the work instead of trusting it: "set a timer for ten minutes" had NO
  exact pattern (the phrases were article-blind) and won at HEAD on a 0.01 fuzzy margin that
  the new keywords tipped over to timer.cancel — fixed at the root with article-tolerant
  phrases (exact match 1.00), the same fix-T1-not-the-fallback lesson QUAL-64/Slice-3 taught.
  Probing also surfaced four PRE-EXISTING EN misroutes (cancel-the-timer, switch-asr-to,
  translate-hello, bare pause) — untouched here, recorded as seed evidence for the EN
  system-test discussion. Validator 0/0, suite 1299, RU device gate 48/48.

- **2026-07-06 — QUAL-69 DONE (filed + completed same day) — wardrobe «свет» alias consumed,
  re-pin @ `acc1e18b`.** The bridge's open-questions resolution gave `wardrobe_spots` the ru
  alias «свет» — a device now carries the group noun as a NAME. Analysis before consuming:
  the depth doctrine is ordering-protected (group-noun check precedes device resolution on
  every path, including the fresh Slice-3 legs), so voice behavior is unchanged — bare «свет»
  stays a room-group command and the bridge's `group_default` picks the spots. Re-pinned all
  three artifacts from bridge commit `aa031d2` (the openapi also carried a committed schema
  rename we hadn't synced since the VWB-19 era). Fixture F17 pins the alias-vs-doctrine
  interaction; device tier-1 gate **48/48**.

- **2026-07-06 — BUILD-11 DONE — the first real GHCR publish, and the images are honest.**
  Dispatch `28774806674` (all targets × all languages + config-ui): every job green on the
  first attempt — six backend images + the UI image are the repo's first artifacts ever on
  GHCR. The D-6 guards fired for real on each: `/app/assets` empty by digest, size within
  budget. **Real uncompressed sizes: armv7 248 MB, aarch64 718 MB, standalone 2.86 GB** —
  the torch-free armv7 diet earned its keep (the placeholder budget had 14× slack). Budgets
  tightened to 500 MB / 1.5 GB / 4 GB. `standalone-x86_64` boot-validated locally through
  the real `ops/docker-compose.yml` contract (override: standalone image + scratch assets
  root seeded per `update.sh`): health on :6000 in ~15 s, «который час» answered end-to-end,
  and first-boot downloads landed in the mounted volume exactly as designed (whisper
  `small.pt`, the microwakeword `irina` v2 pack from HF, silero_v4, spaCy cache). Zero
  defects — no BUGs filed. One observation parked for ARCH-25/REL-2: the RU image logs
  harmless `en_core_web_md not installed` ERRORs (en in the spaCy preference list; degrades
  cleanly to ru). Local test artifacts fully cleaned after (containers, images, scratch).

- **2026-07-06 — QUAL-35 Slice 3 DONE → QUAL-35 CLOSED (evidence-first, interactive) — the
  hard-phrasing tier measured, and the scoreboard rewrote the plan.** Authored the tier-2
  fixtures (F90–F98 measurable + F100–F102 relative adjustments) and ran the two-leg
  measurement: baseline vs the QUAL-50 LLM tier flipped into the derived SUT config (new
  `make device-auto TIER=… NLU=llm` knobs). Baseline 1/12; the LLM leg exposed the real
  blockers — none of them a new NLU tier. Built instead: group-noun routing for raw LLM
  entities («свет» arrives in `target`, not the CHOICE param — was «Не нашла устройство
  "свет"»), power-verb → playback fallback (the tape-deck class), a resolver utterance scan
  for pre-verbal device words («на кухне вытяжку включи» — stem-grade only, no re-pull on
  miss), and two donation pattern fixes for confidently-wrong T1 (greedy «кондиционер на» at
  conf 1.00 — no fallback tier can EVER rescue a confident misroute; «звук на» vs the fuzzy
  volume coin-flip). Colloquial verbs («вруби»/«глуши») deliberately NOT enumerated in
  donations — the LLM tier covers them (found ALREADY enabled in all 6 deployment configs;
  the "disabled in deployments" note was stale) and the smart-home guide now teaches the
  add-a-word donation recipe instead. spaCy T2 leg dropped on evidence → QUAL-53 addendum
  owns any revival; relative adjustments deferred → QUAL-68 (fixtures already red in the
  suite). **Tier-1 gate 47/47 (F94/F96/F97/F98 graduated in), tier-2 `NLU=llm` 5/8 (red =
  the deferred trio), suite 1299, pyright 0.** Guide updated (stale «ютуб» limitation
  removed — Slice 1 shipped it; new limits stated honestly).

- **2026-07-05 — QUAL-67 DONE (filed + completed same day) — donation validation is a CI/build
  gate, warnings-as-errors.** The natural payoff of QUAL-66: with the wiring warnings at zero,
  `irene-donation-validate` fails the build on ANY new one — dead params and undeclared routing
  methods can no longer accumulate as ambient noise. The gate validates every donation directory
  that ships (module-aware discovery; handler module names are inconsistent about the `_handler`
  suffix), not just what some config enables, and sits in backend-health beside the
  config/dependency/build-analyzer gates, so it fences every image publish. Proven both
  directions: 14 handlers / 86 contract methods green, and an injected canary param turns it red.


- **2026-07-05 — QUAL-66 DONE (filed + completed same day) — contract-wiring warnings 21 → 0.**
  The user asked what the boot-time "Contract wiring" warnings were; the answer became a sweep.
  Dead `language` globals dropped from 9 donations (request language lives on the context since
  QUAL-36) + conversation's `session_id`; voice_synthesis's unread `provider` param dropped
  (parsed from raw text); two internal helpers renamed off the `_handle_` routing prefix. The
  near-misses were the lesson: `system` and `speech_recognition` ALSO declare `language` — but
  theirs is the TARGET language for switching, genuinely read, and the validator had correctly
  stayed silent about them (an over-eager first sweep removed them; the warning list itself
  caught the error). One test had relied on the drift existing as its live example and now
  exercises the check synthetically. With zero ambient warnings the validator is a tripwire
  again. Suite 1289 green, device suite 43/43 intact, pyright 0.


- **2026-07-05 — QUAL-64 DONE (interactive) — device suite 43/43 (100%) for the first time.**
  Diagnosis: not a weighting preference but a TIE broken by accident — identical per-tier
  constants + stable sort = donation load-order routing, and the per-method `boost` (authored
  since QUAL-29, docstring promising "pattern strength multiplier") was never read by the pattern
  stage. User picked the specificity+boost score; with the RIGHT winner chosen, the coverage
  factor lifts confidence to 0.98–1.00 on the exhibits. F70's workaround retired («переключи
  субтитры» now wins on merit; fixture restored as regression). 15-case routing test pins
  exhibits + bread-and-butter over all 14 donations. The stale-mock pkill needed the `[e]`
  bracket trick — it was killing its own recipe shell. Suite 1329, pyright 0, 11/11 contracts.
  QUAL-35 Slice 3 is now unblocked on a tuned first tier.


- **2026-07-05 — QUAL-35 Slice 2a DONE — VWB-24 consumed same-day; device suite 41/43.** The bridge
  typed the HVAC params (v1.3): full ru/en/de triplets, and for the first time wire ≠ canonical
  ("COOL"/"cool") — the fixture guard now validates the CANONICAL set, which is what Irene sends
  (§5a). `_hvac_choice` matches the spoken word against the device's OWN triplets (labels +
  canonicals through the shared option matcher, transliteration hints included) with an
  ACTION-aware device pick — only the HVACs carry set_mode, so «кондиционер на охлаждение» never
  clarifies against a plain heater; set_fan's param is named `fan`, not `speed`. F80
  («охлаждение»→cool) and F81 («скорость 2»→speed_2) green live. One ops gotcha burned an hour:
  a STALE mock bridge from earlier debugging still owned the port and served the pre-VWB-24
  golden — empty mode values, while every in-process repro passed; `device-auto` now kills any
  squatter first. The only red anywhere remains F40/F42 — the parked QUAL-64 pair.


- **2026-07-05 — QUAL-35 Slice 2 COMPLETE (Part B, code pushed with the guide; ledger line landed
  one commit later) — device suite 39/41; the only red anywhere is the parked QUAL-64 pair.**
  Part B: tracks audio/subtitles (subtitles got its own verb «смени» — «переключи» scores as
  input_select in the untuned matcher, one more QUAL-64 exhibit), screen aspects as CHOICE+target
  (two screen-capable devices in the living room), menu navigation as a 7-way CHOICE, presence
  «мы дома»/«мы уходим», cleaning start + «уборка на 30 минут», and the water alarm — device found
  by its alarm+leaks capability PAIR (never an id literal), keeping the heating alarm out per the
  user decision. Adjudications settled: no further units abstraction needed (one catalog-range
  path serves dB/%/°C); declarative room_context enforcement closed as satisfied-by-implementation.
  Suite 1314 green, pyright 0, 11/11 contracts. **Immediately after: bridge accepted + implemented
  VWB-24 (typed HVAC set_mode/set_fan) — folded in as Slice 2a** (re-pin + CHOICE wiring +
  fixtures), starting now.


- **2026-07-05 — QUAL-35 Slice 2 Part A DONE (`bedc867`) — device suite 33/35; all eight new
  fixtures green on the first live run.** Wired per the interactive decisions: volume
  up/down/set/mute_toggle (the processor's dB range −96..0 honestly enforced by the shared catalog
  range pre-validation), playback play/stop/next/previous + a seek CHOICE (ff/rewind) with
  `play_pause` fallback for split-action-less devices (the Zappiti), cover.set_position in both
  address forms («наполовину»→50; the room form rides VWB-23 `params`), and the power-verb
  fallback — «включи обогрев» → climate.on, «включи вытяжку» → fan.set(2) — closing the census gap
  where climate/fan devices ignored on/off verbs. The routing-risk fixture (F62 «выключи звук на
  телеке» vs the power_off phrase) routed correctly. +10 donation methods; one extractor trap
  re-learned: target regexes must keep a SINGLE capture group. Part B
  (tracks/screen/menu-nav/presence/cleaning/water-alarm) follows; scope already in the ledger.


- **2026-07-05 — QUAL-35 Slice 2 scope decided (interactive, capability-by-capability from the
  pinned-golden census).** Eleven decisions: volume all-four; playback everything incl. ff/rewind
  (play_pause only as the fallback for split-action-less devices); cover.set_position in both
  address forms with «наполовину»→50; climate on/off via power-verb fallback (the census showed
  «включи обогрев» silently fails today); hood fan with «включи»→speed 2; tracks audio/subtitles +
  screen aspects + a menu nav subset (user overrode the skip-lean: track dialogs need navigation on
  some devices; pointer stays out); presence home/away; cleaning start+delay; water_supply alarm
  only. Skipped with intent: power.toggle, seasonal_mode, heating_control alarm — and ALL FOUR
  VALVES as a permanent voice fence. One contract gap found while checking facts: HVAC
  set_mode/set_fan params are bare strings (no triplets/options_from — the G5 disease again) →
  **bridge VWB-24 filed uncommitted**; «кондиционер на охлаждение» waits for the typing re-pin.
  Implementation follows in this session; scope recorded first so the decisions survive it.

- **2026-07-05 — QUAL-35 restructured (3 slices; the local-LLM T3 concept retired) + Slice 1 DONE —
  device suite 25/27; every red is now QUAL-64's.** Reconciliation first (user): most of QUAL-35's
  historical scope was already satisfied by today's arc — typed donations, the Q7b swap, D-15,
  `options_from`, the units requirement, and the "compound numerals need T2" theory (dead — it was
  BUG-23/24). The T3 bullet's "dependency-parse / local-LLM, opt-in local-only" framing predated
  QUAL-50 and is retired: the third cascade tier EXISTS (the donation-grounded LLM NLU provider
  through LLMPort — DeepSeek with an API key, abstains offline) but is not enabled in any deployment
  config; Slice 3 measures it instead of building anything new. The plan: Slice 1 transliteration,
  Slice 2 capability breadth (volume, playback rest, cover positions, HVAC mode, fan + two
  adjudications; menu/pointer and the global valve/mode specials held for explicit user decision),
  Slice 3 hard-phrasing fixtures measured against spaCy patterns + the enabled QUAL-50 tier (after
  the QUAL-64 matcher tune, so fallback tiers aren't built against an untuned first tier).
  **Slice 1 landed the same session:** `latin_to_cyrillic_hint` reuses the in-house TTS transcription
  engine — "YouTube" renders as «ютуб» *exactly* — plus an acronym letter-name table (TV→«ти ви»,
  where the engine would say «тэлевижен»); option matching and scenario-label scoring now also
  compare against the hint, with «э»→«е» folding. One iteration bump: the hint transcriber must
  carry the FULL PrepareNormalizer option shape (a partial dict KeyError'd on the mixed-script
  label «Кино с LD-проигрывателя» — caught live by the suite, of course). F41 + F53 green;
  F41/F42/F53 retiered to 1. Suite 1269 green, pyright 0, 11/11 contracts.

- **2026-07-05 — QUAL-44 DONE (+ BUG-23/BUG-24 found & fixed under it) — device suite 23/27; every
  remaining red is deliberate.** The arbitration landed exactly as the entry scoped it: on a
  clarifying turn the pipeline now runs NLU on the BARE new utterance first — a confident,
  non-fallback recognition is a fresh command (pending dropped, logged, processed clean); fragments
  and low-confidence turns combine as before. One extra NLU pass, clarifying turns only; abandonment
  is silent. The regression fakes became text-aware — an everything-recognizes-at-0.9 fake would have
  defeated the arbitration invisibly. Chasing the residual F51 red through the live stack
  (`spoken: "hdmiодин"` in the new clarification metadata) unearthed two real input-corruption bugs:
  **BUG-23** — the `numbers` normalizer (digits→words, the SYNTHESIS direction) ran on `asr_output`,
  fighting BUG-1's pre-NLU words→digits and garbling «hdmi1»/«25» (the true cause of F06's range
  error, previously misread as a T2 compound-numeral limit); now `tts_input`-only in defaults +
  config-master + explicit normalizer blocks in all 6 docker configs (user request). **BUG-24** —
  ovos maps standalone «пол» to 0.5, so «тёплый пол» lost its device noun; now sentinel-guarded
  unless a measure word follows («пол часа» still converts). A user question caught a third latent
  one en route: the `-en` configs inherited `latin_to_cyrillic: true` — an English deployment would
  transliterate its whole TTS input; the `-en` blocks now pin `latin_to_cyrillic = false` +
  `language = "en"`. **Result: `make device-auto` 23/27** — F05/F06/F07 retiered to 1 in the fixtures
  (eval-commons `3b959e0`; the "T2 compound numerals" theory is dead, it was pipeline corruption);
  the 4 red are exactly F40/F42 (QUAL-64 matcher tune, user-parked) and F41/F53 (genuine T2
  transliteration). Suite 1266 green, pyright 0, 11/11 contracts.

- **2026-07-05 — QUAL-65 DONE — input switching + app launch by voice (bridge VWB-19 consumed);
  the options_from dance built; QUAL-44 un-deferred by what the suite caught.** Re-pinned @ bridge
  `3bed556` / catalog `dbfd2855` (select-form canonical routing, `canonical_first.md` §11): by_value
  inputs (mf_amplifier, upscaler) carry static value triplets with `labels: null` — technical
  identifiers, wire=canonical=table key — so the ru-labels pin guard learned the distinction (null
  legal, non-null still requires ru); parametric inputs + apps carry `options_from`. The QUAL-35
  resolver-note-(1) machinery arrived ahead of schedule: `read_options(device_id, kind)` on the read
  port, 30s TTL cache in CatalogService, fail-soft `BridgeClient.get_device_options`. Two handler
  methods share one option matcher built on the resolver's own normalization; an unmatched value
  clarifies by reading back what IS available. Four new fixtures (F50–F53) + mock-bridge options
  endpoint; the input-switching exclusion is lifted from fixtures, QUAL-35 note (3), and the user
  guide. **Live: F50 green end-to-end** («переключи усилитель на cd» — validated offline, zero
  round-trips); 20/27. **F51–F53's red turned out to be gold:** not routing at all (the matcher probe
  routes all three correctly, 0.75–0.79) but **QUAL-44 in the flesh** — F20's legitimately-armed
  clarification consumed the next same-room case as its "answer" («поставь на паузу переключи телек
  на hdmi1»), re-armed, and poisoned the cascade; the same bleed retroactively explains part of
  F42's earlier behavior. User decision: QUAL-44 un-deferred and implemented next; the device suite
  runs `-j 1` from now on (shared per-room sessions make parallel cases one interleaved
  conversation, not independent tests). Suite 1262 green, pyright 0, 11/11 contracts,
  eval-commons 40 (`cc1cba9`).

- **2026-07-05 — ARCH-8 PR-5 DONE → ARCH-8 CLOSES — the whole MQTT smart-home arc landed in one day;
  device suite 19/23.** The sensor-read flow: `read_state(device_id)` joined `DeviceCatalogPort` as a
  QUERY (reads never ride the OutputManager, §13.3), `CatalogService` carries a wired state-reader,
  `BridgeClient.get_device_state` GETs `/devices/{id}/state` fail-soft, and the handler's
  `_handle_read_state` (donation: quantity CHOICE temperature/humidity with RU surfaces, room via
  D-15) picks the reading source with two deliberate preferences the tests pin: a dedicated `sensor`
  capability beats a climate unit, and on climate devices the MEASURED `room_temperature` is read —
  the bare `temperature` field there is the thermostat SETPOINT («уставка» per the catalog's own
  labels), a silent wrong-value trap. Live: F30–F32 went green (`make device-auto` → **19/23**; the
  4 red are all owned: F40/F42 → QUAL-64, F41/F06 → QUAL-35 T2). Suite 1255 green, pyright 0, 11/11
  contracts. **The deferred user-facing promise is delivered with ARCH-8's completion:**
  `docs/guides/smart-home.md` — how voice control works (catalog-driven vocabulary, depth of
  phrasing, clarifications, sensor questions), how to enable `[outputs.bridge]`, current limits —
  linked from the README. Remaining in the MQTT lane: QUAL-35 T2/units + breadth (evidence now
  flowing from the suite), QUAL-64 matcher tune, then the hardware tiers (ARCH-25).

- **2026-07-05 — TEST-18 DONE (Slice B) — the producer contract suite is EXECUTABLE; first scoreboard
  16/23.** The capture side landed as a **mock bridge** (eval-commons `1bc7b03`), refining §14.3's
  in-process capture into something strictly more end-to-end: `eval_commons/mock_bridge.py` serves the
  PINNED golden catalog at `/system/catalog` and records every canonical POST fixture-shaped — so a run
  exercises the real BridgeClient wire serialization AND the real startup catalog pull, not just the
  handler. `device_command_provider` drives `/execute/command`; `device_command_assert` compares
  against the fixture `expect`; `fixtures_to_tests` GENERATES the promptfoo cases so the pinned
  fixtures stay the single source of truth. Voice side: `eval/device.promptfooconfig.yaml`,
  `make device / device-auto` (the auto target derives the SUT config from config-master because
  pydantic-settings init kwargs beat env for nested sections), target-profile URLs, eval README.
  **Scoreboard: 16/23** — every tier-1 actuation + clarify fixture green end-to-end (device forms,
  all six VWB-23 room-group forms incl. scope auto/all and room aliases, both clarifications). The
  7 red, each owned: F30–F32 reads → ARCH-8 PR-5; F41 transliteration + F06 compound numeral
  («двадцать пять» mis-extracted; «двадцать два» fine) → QUAL-35 T2's first suite-collected evidence;
  F40/F42 scenario routing → **QUAL-64** (filed): the keyword matcher — never tuned — scores short
  verb phrases over longer specific ones («выключи кино» → power_off despite scenario_stop carrying
  that exact phrase at boost 1.3), then dips under the 0.7 threshold live → LLM fallback. User
  decision: leave them red, tune the matcher deliberately (a drafted handler-level scenario fallback
  was reverted in favor of that). En route, **BUG-22** found + fixed: `/execute/command`'s room_alias
  validation NEVER worked — web_server built a web-templates-only asset loader, so localization
  consumers saw empty data; it now reuses the intent system's fully-loaded loader, and the rooms
  localization gained the house's rooms. TEST-18 moved active → done; next: ARCH-8 PR-5 (the reads
  go green).

- **2026-07-05 — ARCH-8 PR-4 DONE (+ QUAL-35 T1 donations & clarify policy) — «включи свет в
  детской» now travels the whole pipeline: NLU → resolver → handler → canonical command → spoken
  outcome.** The reference smart-home handler (`smart_home.py`, 9 donation-routed methods) closes
  the vertical slice. The T1 donation is the first with non-generic `entity_type` declarations
  (target=device, room=room) — the PR-3 Q7b swap now runs its declarative path in production. The
  noun lexicon landed as donation data, not code: the `group_noun` CHOICE param's canonical values
  ARE the catalog's semantic group names (light/cover) with the RU surfaces
  (свет/шторы/жалюзи/занавески) as choice_surfaces — bound to catalog truth at execution (the
  handler refuses a room-group command for a room with no such group members), guarded by a
  word-boundary check so a device NAMED «Подсветка потолка» never false-triggers the light group.
  «весь/все» flips `scope: auto → all`. Delivery goes through a new Any-typed domain port
  (`DeviceCommandDeliveryPort` — pure per the import contract) implemented by
  `DeviceCommandDispatcher` over the OutputManager with a 7-second bound; a timeout, a missing
  bridge, or a missing catalog each get their own honest spoken degradation. The §5b error enum
  maps to feminine-ru templates; `param_invalid`, same-room ambiguity (F20/F21 — the v1 clarify
  decision), out-of-range setpoints (pre-validated against the pinned catalog's min/max — most
  param_invalid never round-trips) and missing slots all arm the QUAL-30/31 one-shot
  clarification; a partial room-group aggregate names its failed members («…, но не ответили:
  Бра»). 22 fixture-mirroring tests drive the REAL resolver → handler → OutputManager → capturing
  bridge and assert byte-equal fixture `expect` shapes; a live webapi run confirmed the real NLU
  cascade routes «включи свет в детской»/«включи телек» to `smart_home.power_on` while greetings
  and timers stay untouched. Suite 1250 green, pyright 0, 11/11 contracts. Handler enabled in
  config-master + all 6 docker configs (domain priority 80). TEST-18's tier-1 fixtures are now
  green-able — Slice B makes them executable. Two side-fixes: the smoke-e2e 500 was a stale
  editable-install entry-point map (uv sync refreshes it), and the recurring dev-venv trap's root
  cause fell out — the untracked `.python-version` pinned the broken /usr/local 3.11.4; it now
  pins the uv-managed 3.11.12 (memory updated). Next: PR-5 (sensor read) closes ARCH-8.

- **2026-07-05 — ARCH-8 PR-3 DONE (with the QUAL-35 resolver half) — spoken references now resolve
  against the real device catalog.** Three moves in `entity_resolver.py`. **The Q7b atomic swap
  (QUAL-35 b):** dispatch is declarative-first — a donation-declared `entity_type` routes the param
  straight to the device/room resolver (map built from the loaded donations); the old
  `_is_device_entity`/`_is_location_entity` name-heuristics remain only as the fallback for
  generic/undeclared params, so every existing handler behaves identically until PR-4's smart-home
  donations declare real types. **Catalog-backed device resolution:** name+alias surfaces per locale,
  exact then RU-morphology-tolerant (a shared-stem heuristic — ≥4-char stem with ≤3-char endings —
  because plain fuzz.ratio scores «детской»/«детская» at 71, under any sane threshold), room-context
  disambiguation for shared aliases, name-level ambiguity surfaced as candidates for the clarify path
  («ночники» → both sconces, per the v1 decision), and the ARCH-26 lazy re-pull exactly once on a
  miss. **Room resolution + D-15:** catalog rooms by name/alias/id, then the ARCH-22 coverage policy —
  a mentioned room the client covers is the target, a real room it does not cover returns
  `uncovered_room` (spoken error, no actuation), and `global` is exempt so whole-house asks
  («выключи весь свет в квартире») work from any satellite; `resolve_default_room` implements
  rule 3 (no room → primary). The legacy client-context paths survive untouched for catalog-less
  deployments. Wiring rides `nlu_component` → `core.catalog_service`. 14 new tests; live
  spot-checks against the real pinned golden: 12/12, including the resolution leg of every
  device-form crossover fixture (телек/эппл/радиаторах/пол/розетки/тюль слева + room aliases
  зал/квартире/сынарник). Suite 1228 passed, pyright 0, 11/11 contracts. QUAL-35 keeps (a) T1
  donations and the handler-side room_context policy for PR-4, and the heavy tiers for after the
  suite runs. Next: PR-4 — the reference device handler end-to-end.

- **2026-07-05 — PR-2 placement amendment (user decision): one home for all OutputPorts + explicit
  bridge surface in the 6 deployment configs.** `BridgeClient` moved
  `providers/outputs/bridge.py` → `outputs/bridge.py`; the `irene.providers.outputs` entry-point
  group is retired (nothing discovered outputs via entry-points — the composition imports and
  registers directly from `[outputs.bridge]` config) and its ARCH-4 independence entry removed;
  `mqtt_integration.md` §4/§8/§10/§13.1 amended with dated notes so the design doc matches reality.
  The 6 docker-image configs (standalone-x86_64, embedded-aarch64, embedded-armv7 × ru/en) — which
  carried no `[outputs]` section at all (silent defaults) — now declare `[outputs]` +
  `[outputs.bridge]` explicitly (disabled; the flip-on belongs to the ARCH-25 hardware bring-up
  once the bridge's ops cutover lands); all 6 validate against `CoreConfig`. Suite 1214 green,
  11/11 contracts, pyright 0.

- **2026-07-05 — ARCH-8 PR-2 DONE — the real bridge adapter; Irene can now (config-gated) speak REST to
  wb-mqtt-bridge and pull the device catalog.** `BridgeClient` (`providers/outputs/bridge.py`, the only
  module that knows the bridge exists) implements the designated DEVICE_COMMAND OutputPort: device-form
  commands POST to `/devices/{id}/canonical`, room-group commands to `/rooms/{room_id}/canonical`
  (VWB-23), responses map to the rich DeliveryResult — post-action `state` / per-member `results` as
  the echo, the §5b error enum as `error_code` with `param_invalid`'s field+reason preserved for the
  clarify path, and a bridge that is down becomes a spoken `bridge_unreachable`, never an exception in
  the pipeline. Its `parse_catalog` builds the domain `DeviceCatalog` and was verified against the real
  pinned golden (79 devices / 11 rooms @ `91909b54`; children_room light default, global→all_lights
  membership, °C/% typed params, scenario ru labels, `options_from`, «зал»/«радиаторы» aliases all
  survive the round-trip). Wiring: new `[outputs.bridge]` config section (enabled/base_url/timeout;
  documented in config-master, config-ui `OutputConfig`/`BridgeOutputConfig` types co-changed — the
  section editor renders nested objects generically; `npm run check` + `build` clean),
  `CatalogService` now built by `build_core` and carried on the engine, and a runner-agnostic
  `setup_bridge_output()` hook in the composition (called by the base runner after `core.start()`)
  registers + designates the output, wires the catalog fetcher, and attempts one non-fatal startup
  pull — the ARCH-26 lazy refresh covers a bridge that boots later. Placement decision recorded (user
  question): BridgeClient sits under the `irene.providers.outputs` entry-point group per §13.1 —
  an external-system adapter (configured, designated), not a channel sink like `irene/outputs/`;
  the category joined the ARCH-4 independence contract. One test-harness fix along the way:
  the master-config completeness test's section-rename mutation now renames `[outputs.*]` sub-tables
  too (a surviving `[outputs.bridge]` implicitly recreates the parent — TOML super-table semantics).
  13 new tests; suite 1214 passed, pyright 0 errors, 11/11 import contracts, config-ui clean.
  Smart-home user-guide prose deliberately waits for PR-4/PR-5. Next: PR-3 — catalog into the
  resolver.

- **2026-07-05 — ARCH-8 PR-1 DONE — the canonical-command boundary exists in code; the MQTT arc's spine
  starts.** Adapter-free by design, built the same day as the fixtures it must eventually satisfy.
  Domain (`irene/intents/`): `device_commands.py` — `DeviceCommand` (device form; scenarios ride it) and
  `RoomGroupCommand` + `GroupScope` (VWB-23 room form), each with the fixture-shaped `to_dict()` (kinds
  `actuate`/`room-group`, matching `crossover_fixtures.json` vocabulary) and the wire-shaped
  `request_body()`; commands travel in `IntentResult.metadata["device_command"]` per §13.2.
  `device_catalog.py` — the typed catalog model mirroring the pinned contract (params
  values-XOR-`options_from` with units/ranges, capability `group` tags, room `group_defaults`, and the
  `group_members`/`group_default` queries the resolver will use). `DeviceCatalogPort` joined
  `intents/ports.py` (QUAL-24 pattern) carrying the ARCH-26 lazy-refresh seam as `async refresh()`.
  Application: `core/catalog_service.py` holds the snapshot, serializes concurrent refreshes, and never
  discards the last good catalog on a failed pull; PR-2 wires its fetcher. Delivery:
  `outputs/device_command.py` — `CapturingDeviceCommandOutput`, the fake bridge that IS the TEST-18
  capture point (records both address forms, returns the rich echo `DeliveryResult`, scriptable §5b
  error responder). No `ActuationPort` — the bridge is an OutputPort (§13.6). 15 new unit tests incl.
  end-to-end designated routing through the OutputManager; suite 1201 passed, pyright 0 errors.
  Follow-up hardening (user question, same session): a new import-linter contract — "Domain ports and
  boundary types stay pure" — pins `intents/{ports,models,device_commands,device_catalog}` against
  `irene.core`, closing a gap ARCH-1 cannot cover (intents as a whole carries sanctioned core edges:
  donations, trace, the durable seam — so only a module-scoped rule can forbid the port→application
  inversion, same shape as the SCC-2 input-port contract); 11/11 contracts kept.
  TEST-18 Slice B ungated. Next: PR-2 (BridgeClient adapter + catalog pull).

- **2026-07-05 — TEST-18 Slice A DONE — the crossover fixture set exists; the MQTT arc now builds against
  a failing suite.** Resumed the paused interactive session; the three open decisions closed (user):
  light-subset pair nouns («ночники»/«тумбочки»/«полки») dropped from v1 — bridge-side compound devices
  will come later and re-enter via a re-pin; same-room capability ambiguity clarifies in v1 with priority
  rules filed as QUAL-63 for a later release; sensor reads included. Authored
  `eval-commons/contracts/crossover_fixtures.json` (`941e245`): 23 `{utterance → canonical command}`
  fixtures against pinned catalog `91909b54` spanning all four expect kinds — device-form actuation via
  aliases and typed °C/% params, VWB-23 room-group commands (scope `auto` vs «весь»→`all`, room aliases
  «зал»/«квартира»), reads (with `any_of` for the two physically-equivalent bedroom temperature sources),
  clarifications (F20 playback, F21 climate), plus the scenario enum by RU label and a transliteration
  case. Each fixture carries a tier (1 = green-able with the QUAL-35 T1 donation baseline at ARCH-8 PR-4;
  2 = needs T2 units/transliteration). A new 8-test guard suite (`test_crossover_fixtures.py`) binds every
  fixture to catalog truth — device ids, actions, param ranges, enum wires, groups, sensor fields — and
  pins the fixtures' `catalog_version` to `PIN.json`, so the next re-pin points at exactly which fixtures
  go stale; 16/16 green with the pin guards. The bridge's VWB-16 consumer half can consume the file as-is.
  Next per the recorded sequence: ARCH-8 PR-1.

- **2026-07-05 — VWB-23 analyzed + contract RE-PINNED — «включи свет» became one REST call; the boundary
  is now address-form polymorphic.** The bridge shipped room-scoped group addressing (`canonical_first.md`
  §10, surfaced by this side's TEST-18 Slice A question "what does «включи свет в детской» resolve to?"):
  `POST /rooms/{room_id}/canonical {group, action, scope: auto|all|one}` — the depth doctrine (resolve only
  as deep as the utterance specifies; the device pick is bridge POLICY via `group_defaults`, not resolver
  heuristics), a `group` overlay on capabilities (37 illumination `power` caps tagged `light`; oven/plugs
  split to `power_switch` so «свет» can never reach them), all 10 rooms defaulting `light` → `<room>_spots`,
  fan-out allow-listed to `light`+`cover`, per-member aggregate responses. Verified against the committed
  artifacts and **re-pinned** into eval-commons (`e0d6b45`, catalog `91909b54`, all 8 pin guards green —
  the guard suite did its job on its first real re-pin). Ledger adjusted: ARCH-8 gained the
  three-address-form addendum (PR-1 models device + room-group commands; PR-4 noun lexicon bound to catalog
  `group` truth + singular/«весь»→scope mapping + aggregate-response speech); QUAL-35 gained the depth
  doctrine + the no-power-fan-out fence; TEST-18 Slice A: **Q1 (room lights) RESOLVED by VWB-23**, Q2
  narrowed to light-subset pairs only («ночники»/«тумбочки» — cover pairs dissolved into room-group
  fan-out), Q3/Q4 still open, fixture schema gains the `room-group` expect kind. Slice A stays paused on
  the three remaining user decisions.

- **2026-07-05 — TEST-17 DONE — the contract is pinned; both repos now test against the same committed
  boundary.** The bridge's v1.1 artifacts (bridge `59f4f46`, catalog `7a1149c7`) copied byte-identical into
  `eval-commons/contracts/` with a voice-side `PIN.json` and a consumer README (bridge generates, voice
  re-pins, both suites read this copy — no cross-repo writes, §14 publish boundary). The pin is load-bearing,
  not decorative: 8 new eval-commons tests validate the golden against the pinned `CatalogResponse` schema
  itself (the two halves of the pin cannot disagree), check STAMP↔PIN↔golden version agreement, and assert
  the v1.1 shape guarantees (authored aliases, ru enum labels, °C/% units, `values`-XOR-`options_from`, no
  empty capability husks) — so accidentally re-pinning a pre-patch artifact fails in seconds. Deliberately
  sequenced pin-after-patch: the first pin is the only pin. Carve-outs recorded in the ledger entry: the
  real WB7 dump rides the bridge's controller cutover; the crossover fixtures co-develop with ARCH-8
  PR-1/TEST-18. The MQTT arc's opening move is done — ARCH-8 PR-1 is next.

- **2026-07-05 — The bridge contract is voice-ready; ARCH-8's gate is met and the conclusions are in the
  ledger.** Closes the loop opened 2026-07-04, when the user asked how smart-home intents get their donations
  before starting ARCH-8. The analysis of the freshly committed bridge `contracts/` established the story —
  **donations are NEVER generated from the contract**: donations carry the static device-agnostic grammar
  (verbs, typed slots), the catalog supplies the entity/value vocabulary at runtime (lazy, ARCH-26), the
  resolver marries them — and found five gaps (schema-less `CatalogAction.params`, no aliases, EN-only enum
  labels, no units on params, enum-in-disguise `apps.launch`). Filed bridge-side; intake verified 4 of 5 and
  **refuted the G5 remedy** (the app set is runtime-dynamic — a static enum in the golden would drift on
  every app install, the exact disease QUAL-18 diagnosed; corrected to an `options_from` hint +
  `GET /devices/{id}/options/<kind>`, which adds a clean THIRD vocabulary tier: fully-dynamic per-device
  sets). Bridge landed **VWB-20 contract patch v1.1** (typed `CatalogParam` with unit/values/options_from,
  ru+en enum labels, aliases schema, husks suppressed) **and VWB-21** (household alias vocabulary: 34
  devices + 3 rooms) — all six items verified against the committed artifacts (catalog `7a1149c7`, bridge
  `59f4f46`). Ledger annotated so the conclusions survive this chat: ARCH-8 gate flipped to MET with the
  PR-2/PR-3 build notes; QUAL-35 gained the resolver-design notes (options_from as a second CHOICE source
  with lazy-miss + short-TTL cache; Cyrillic↔Latin transliteration-tolerant matching for device-reported
  proper nouns — «ютуб» vs "YouTube"; v1 command set excludes input switching until bridge VWB-19);
  TEST-17 un-deferred → `[release]` P2 with the pin target recorded. Next: TEST-17 pin → ARCH-8 PR-1.

- **2026-07-04 — QUAL-18 DONE (re-scoped) — the AsyncAPI subsystem is retired; the WebSocket protocols
  finally have accurate documentation.** The user asked for a deep dig before implementation, and the dig
  changed everything: the live `/asyncapi.json` emitted **zero channels** (verified against a running
  server) — all four documented endpoints had been deleted by ARCH-21/ARCH-10 while the four real ones
  (`/ws/audio`, `/ws/audio/reply`, `/ws/observe`, `/ws/output`) were never in the spec. ~1,400 LOC of
  bespoke generator+renderer were rendering an empty page, and the "code-first docs can't drift" premise
  had self-refuted (decorators document claims, not what `send_json` does). The 2026 ecosystem check found
  the renderer side solved (`@asyncapi/react-component` v3.1.3, offline-vendorable) but still no maintained
  FastAPI-WS→AsyncAPI introspector (fastws dead since 2023; FastStream still broker-shaped). Presented
  spec-as-artifact / code-first-rebuild / retire; **user chose retire + a user-facing guide.** Deleted
  ~2,000 LOC (generator, renderer, `irene/web_api/`, 7 dead WS message models, the interface method, 4
  routes, contract refs); wrote `docs/guides/websocket-api.md` — all four protocols frame-by-frame, the
  QUAL-55 canonical response frame, the reply channel's `speak_begin/PCM/speak_end` brackets,
  missed-announcement redelivery, a runnable Python example — plus a house-style diagram
  (`ws-protocols.dot/png`) and links from dataflow/esp32/howto-new-test. The web index page was also lying
  (linked `/asyncapi` and listed the deleted `/asr/stream|binary`) — repointed. Verified live: `/asyncapi*`
  404, index shows the guide pointer. Suite 1180 + smoke + 10 contracts green.

- **2026-07-04 — QUAL-55 DONE — the five execution surfaces speak one result shape.** The review's root
  cause (`api_result_contract_review.md`: no shared serializer, five hand-built dicts drifting apart) is
  closed with `irene/api/serializers.py::serialize_intent_result` — canonical
  `text`/`success`/`error`/`confidence`/`intent_name`/`timestamp`/`metadata`, with `intent_name` lifted from
  the orchestrator's `original_intent` and endpoint extras merged INTO the raw metadata rather than replacing
  it. REST `/execute/*` renamed `response`→`text` (the planned breaking change; `CommandResponse` reshaped),
  `/trace/*` `final_result` and both WS `response` frames now emit the same payload (superseding QUAL-54's
  metadata-injection stopgap). The "executed successfully" invented-prose fallbacks died with it (fail-loud).
  Cross-repo co-changes: config-ui types regenerated from the re-dumped OpenAPI (check+build green; no
  runtime consumer of the old field existed), eval-commons `ws_audio_provider` reads top-level `intent_name`
  with a metadata fallback so it spans SUT versions. The WS test fakes were replaced with the real
  `IntentResult` — hand-rolled fakes lacking `error` broke immediately, re-proving the review's F5 lesson
  that wrong-shaped fakes hide live bugs. Suite 1180 + smoke (live server asserts the canonical keys) +
  hexagon gate green.

- **2026-07-04 — REL-1 DONE — the Definition of Release is signed off; the road to release is now a closed,
  explicit list.** Interactive session. The checklist was reconciled criterion-by-criterion against current
  reality first: 6 of 8 exit criteria are already met with evidence (clean `uv sync` + CLI/WebAPI boots via the
  hermetic smoke suite; CI green since BUILD-9; pyright standard mode at 0 errors with an empty suppression
  list; 10 import-linter contracts; the test nets green; live model URLs re-verified this week by ASSET-4/5).
  The reconciliation surfaced one real gap: **no publish dispatch has ever run — no Docker image has ever been
  built for real**, so the Docker-boot clause was unproven → filed **BUILD-11** (first GHCR publish + boot
  validation + replace placeholder size budgets with real-size-derived ones). User decisions: the release
  artifact is a tag + published GHCR images (RU backends + config-ui); QUAL-18 and DOC-8 both STAY in release
  scope (all previously untagged tasks now carry explicit tags — the implicit-default ambiguity is gone);
  the vague "coverage understood" criterion replaced by the three named nets (unit + smoke e2e + eval CLI), no
  coverage-%; the target is the "scope-complete" milestone, not a calendar date. Remaining to release, in
  full: ARCH-8 (5 PRs) + QUAL-35 + QUAL-55 + QUAL-18 + DOC-8 (code/docs), ARCH-25 (hardware validation),
  BUILD-11 + REL-2 + REL-3 (release mechanics).

- **2026-07-04 — ARCH-29 + ASSET-5 DONE — «Ирина» lives in the server: wake-word model acquisition designed
  (interactive) and implemented; the training factory's first handoff consumed.** The user announced the first
  validated RU microWakeWord model (HF `droman42/microwakeword-irina-ru`, trained in
  `~/development/wakeword-training`) and asked for the model-sourcing architecture discussion. Design
  (`docs/design/wakeword_models.md`): a wake-word model is a v2 two-file pack (manifest + sibling `.tflite`);
  resolution is a 4-rung chain — local manifest path (pre-release testing) → wheel built-ins (the 4 stock EN
  packs ship inside pymicro-wakeword byte-identical to the esphome v2 repo, so «Alexa» as «Ирина»'s EN
  counterpart costs zero downloads) → v2 manifest URL (the escape hatch for microwakeword.com and
  not-yet-released HF models, per the user's "what if I train more?" question) → the released catalog on the
  provider class (piper-voices pattern; one line per validated word). Trigger layer stays semantics-free —
  word→room mapping waits for multi-room (ARCH-22/QUAL-35). Implementation: AssetManager multi-file packs
  (`files:` entries, staging + atomic rename) + `download_model_files()`; the provider's broken QUAL-20
  asset stub replaced by the real chain; both standalone configs switched to microwakeword («Ирина» RU /
  Alexa EN, per user request); voice-trigger guide rewritten; roster fixed everywhere («Борис» dropped — 2
  syllables; next: «Валера», «Наташа»; diagram regenerated). Live verification through the real provider:
  pack fetched from HF via the AssetManager, silence stays negative, and **16/16 synthetic + 6/6 real
  household «Ирина» recordings detect at the manifest's 0.97 cutoff** — an initial 0/16 scare was the harness
  truncating clips at the word's last sample (the sliding window needs trailing audio; a live mic always
  provides it). Suite 1173 green; both config validators green; smoke e2e green.

- **2026-07-04 — ASSET-4 DONE — silero VAD model download re-homed into the AssetManager; VAD warmup moved
  off the audio hot path.** A user-requested deep review of the VAD code ("where does the microVAD model come
  from?") answered the question two ways: **microVAD's model is compiled into the `pymicro-vad` wheel**
  (`micro_vad_cpp.abi3.so` — nothing to download, correctly outside asset management), but **silero VAD was
  self-downloading** — a synchronous, timeout-less `urllib.urlretrieve` fired on the *first audio frame*,
  blocking the event loop, retrying every frame when offline, and able to strand a truncated model file that
  its `size > 0` guard would trust forever. Root cause of the bypass: the AssetManager had no identity for the
  VAD family (`silero` is claimed by silero TTS in `provider_namespace_map`). Fixed by introducing the
  `silero_vad` asset name via a `(namespace, entry-point)` tuple mapping, declaring the model URL on
  `SileroVADProvider`, downloading in the provider's async `_do_initialize` through
  `download_model(..., url_override=)` (TOML `model_url` override kept), and adding a
  `VoiceSegmenter.initialize()` warmup seam that falls back to `energy` when the configured provider can't
  come up — so a fresh offline install degrades to working energy VAD instead of going silently deaf. On-disk
  path unchanged (`models/vad/silero_vad.onnx` — deployed volumes unaffected). Dead
  `create_audio_processor`/`process_audio_with_vad` deleted; stale VADEngine/vad_silero docstrings and
  `docs/guides/vad.md` updated. Suite 1162 green + `test_vad_assets.py` (10 new); verified live both ways
  (real download through the AssetManager; dead URL → energy fallback with the reason logged).

- **2026-07-02 — TEST-16 DONE — the Russian UX judge is calibrated against the user's own gold labels
  (κ = 1.0 in-sample).** The user suspected the task obsolete; reconciliation showed the opposite — it was
  blocked on exactly one thing only they could provide, so it was finished interactively: a regenerated 20-case
  set (the old probe died with its session scratchpad) was labeled live by the user (16 confident + 4 genuine
  borderlines, excluded from κ), then graded through the same llm-rubric→DeepSeek path as production. The human
  labels **inverted** the Claude-labeled probe's bias profile — the judge was too STRICT on terse voice replies
  («Окей.» is a fine confirmation) and too LENIENT on bureaucratese («код 502, обратитесь к администратору») —
  vindicating the human-gold gate. Two disciplined rubric iterations (re-measure everything each time):
  81%/κ0.625 → 94%/κ0.875 → **16/16, κ=1.0, stable across repeat runs**. En route, a real infrastructure find:
  the documented `file://…yaml#anchor` rubric-reference pattern NEVER worked in promptfoo (the fragment is
  treated as part of the filename — which is why the live suite carried inline copies); shared rubrics are now
  per-rubric `{ru,en}/*.txt` files, the yamls retired, and all four live UX cases reference the shared files
  directly (path proven live from `eval/`). Calibration set + gold + scorer + method housed in eval-commons
  `examples/ru-ux-calibration/` (their commit `4dd73d7`); ARCHITECTURE §7.1 flipped to CALIBRATED; EN rubrics
  got the same structural improvements, marked uncalibrated. **Russian UX pass/fail is now CI-trustworthy**,
  with the recorded caveats: κ is in-sample (fresh negatives as suites grow) and the set must be re-run after
  ANY rubric edit. TEST-16 moved active→done.

- **2026-07-02 — BUG-13 DONE (re-scoped with the user) — the streaming-branch hang is unreproducible; three
  real defects found by the repro are fixed.** Reconciliation ran a live repro (RU streaming pack, bounded
  utterance + `end`): the response arrives — the EOF-finalize has been in the tree since 2026-06-04, and the
  filed 30s hang belonged to the few-hours zipformer window (model rejected + removed same day; its
  endpoint-chops-bounded-commands behavior confirmed live — the online model loses "10 минут", exactly why
  satellites use offline Moonshine). Per the user's "re-scope + fix now": **(1)** the streaming branch now
  serves multiple utterances per connection (used to close after the first response — batch-floor parity
  restored); **(2)** a bounded client that stops sending without `end` no longer hangs forever — a 10s read-idle
  timeout force-finalizes (the plausible original culprit and a real hole regardless); **(3)** warm-up and the
  first request no longer race `_load_recognizer` into TWO model instances (2× RAM on the WB7) — double-checked
  lock in the base loader, subclass inherits. Stale zipformer claim in the EN config header corrected.
  Verified three ways: 2 new WS regression tests + 1 legacy fake made sherpa-honest; live SUT run (3 utterances
  on one socket, with and without `end`, all answered; recognizer loaded ONCE — was twice). Suite 1158 / 7
  skipped; pyright clean. BUG-13 moved active→done.

- **2026-07-02 — BUILD-10 DONE — the `ops/` deploy story lands; the BUILD-8 arc closes.** First: CI run 5
  (`7e2c50b`) is **fully green** — the new `ci.yml` gate side is validated end to end after the four-defect
  shakeout. Then the bridge's "deploy = pull, not build" pattern arrived here: `ops/docker-compose.yml` (Irene
  `:6000`, gitignored `../.assets` mount, 800m/1.5cpu with a tune-at-bring-up note; config-ui behind a compose
  `ui` profile per D-4), `ops/update.sh` (explicit per-subtree `rsync --delete` of the git-owned assets —
  donations/localization/prompts/templates/web + the contract schemas — then compose pull/up/prune; a sandbox
  test proved a planted model file and a durable-action record survive the sync), a systemd oneshot unit, and
  `ops/INSTALL.md` (install/update/rollback/EN-variant/recovery). The controller loop is now
  `git pull && ./ops/update.sh`, and the manual assets-artifact download is fully retired.
  `build-docker.md` deployment section rewritten around `ops/`. Remaining from the arc: the first real publish
  **dispatch** (validates the matrix + D-6 guards, yields actual sizes to tighten the budgets) and the on-WB7
  `update.sh` run (folds into ARCH-25 bring-up).

- **2026-07-02 — BUG-21 DONE + BUILD-9 CI shakeout — four live runs, four real defects, none of them the
  workflow's logic.** Greening the new `ci.yml` on real pushes surfaced, in order: **(1)** `.python-version` is a
  gitignored local pin → py-dev-gates needs an explicit `python-version: "3.11"`; **(2)** the `all` extra wasn't
  all — `tts-ruaccent` + `vad-tflite` missing (masked for months by `uv sync --all-extras`; exposed by the
  action's `pip install .[all,dev]`; pyright failed on `ruaccent`/`pymicro_vad` imports — packaging metadata, NOT
  a TTS-provider regression); **(3)** the config-validator step lost its `--config-dir configs/` arg in the port;
  **(4) = BUG-21**, spotted by the user's local run: the build-analyzer's "TTS but no audio output" rule predates
  ARCH-22 (satellites synthesize + stream to the ESP32 reply channel with no local audio — all four satellite
  profiles ❌ INVALID), AND `--validate-all-profiles` returned 0 regardless — the CI gate had been decorative in
  the old workflow too. Fixed: the rule now errors only when TTS has neither a local audio provider nor
  `web_api_enabled` (recorded on `BuildRequirements`), the tool exits 1 on any invalid profile, and
  `test_smoke_e2e.VENV_BIN` resolves next to `sys.executable` (the hardcoded `.venv/bin` broke in the pip-based
  CI env). All 12 profiles VALID; suite 1156 passed / 7 skipped locally.

- **2026-07-02 — BUILD-9 DONE — the one gated CI/publish workflow is live in the tree.** `ci.yml` replaces the
  three disconnected workflows (`backend-health`/`frontend-health`/`build-images`, deleted): a `changes`
  path-filter fans out to `ledger-guard` (`check_scope.py` finally runs in CI), `backend-health` (the shared
  **py-dev-gates@v0.1.1** trio with `install-extras: all,dev`, a NEW `uv lock --check` step to keep lockfile
  honesty since the gate env is pip-resolved, plus the voice-specific analyzer/config/dependency/arch gates and
  pytest), and `frontend-health`; publishing is dispatch-only, a `plan` job expands `targets`×`languages`
  inputs (default: all 6 backend images), every publish `needs:` green health — the publish-from-red-tree hole
  is closed. RU images keep unsuffixed names, EN adds `-en`; buildx cache per `<target>-<language>`. **D-6
  guards are live:** each pushed image is pulled by digest and the run fails if `/app/assets` is non-empty;
  size is budget-checked (placeholders 3.5/4.5/10 GB, to be tightened from the first dispatch's summary).
  **config-ui ships:** `config-ui/Dockerfile` (node:22 → nginx:alpine, one multi-arch manifest) with the
  runtime-config pattern — D-4 amended at implementation: NO nginx proxy (Irene's API has no path prefix and
  already serves permissive CORS); the entrypoint writes `/runtime-config.js` from `API_BASE_URL`, and the app
  defaults to `http://<page-hostname>:6000`. Verified locally: image built and smoke-run (env injection, SPA
  fallback, 200s), config-ui `check`/`build`/`test` green (40 tests). The assets GHA artifact is dropped
  (BUILD-10's git-pull sync replaces it; `build-docker.md` bridges the gap with a manual rsync note and now
  documents the 7-package family, EN pulls, dispatch UX, and the models-never-baked guarantee). Note: the
  workflow YAML parses clean; its live expression paths get validated by the first real dispatch. BUILD-9
  moved active→done; BUILD-10 (`ops/`) is next.

- **2026-07-02 — BUILD-8 DONE — build/release redesigned bridge-style (interactive; design at
  `docs/design/build_release_process.md`).** Requirements finalized with the user: organize the build the way
  `wb-mqtt-bridge` does. Two comparative maps showed we already share the tagging/GHCR/3-stage-lean-venv DNA
  (and are AHEAD on the analyzer-driven minimal deps + buildx caching), but diverge on organization: three
  disconnected workflows (an image can publish from a red tree), no CI ledger-guard, no `ops/` deploy story,
  gates inlined instead of the shared `py-dev-gates` action, one-target-per-dispatch (6 dispatches once EN
  lands). Decisions (all user-confirmed): one gated `ci.yml` with changes-filtering; **manual dispatch drives
  the full targets×languages matrix** gated on green health; **RU images keep unsuffixed names, EN adds
  `-en`**; **config-ui ships as a multi-arch nginx image** (`wb-mqtt-voice-ui`) but is not deployed to the
  controller yet; **`ops/` deploy-by-pull** with assets synced from a controller-side `git pull` (replaces the
  manual GHA-artifact download). **User hard requirement audited: model files are NOT baked into images** —
  runtime stages ship only code+venv, `/app/assets` is empty, models download at runtime; the one deliberate
  exception is the profile's spaCy NLU wheel, and the perceived image bulk is dependency weight (torch on
  standalone). Guards specified (empty-assets assertion + size budgets in the publish workflow). Stale
  `docker_build_review.md` annotated obsolete (pre-BUG-14 findings). BUILD-8 moved active→done; **BUILD-9**
  (ci.yml/matrix/guards/UI image) + **BUILD-10** (`ops/`) filed `[release]` per `design-then-implement`.

- **2026-07-02 — VWB-18 accepted + fixed bridge-side; cross-repo loop closed.** The bridge maintainer verified
  the QUAL-56-filed restart-durability triad against live code at intake (per their `cross-repo-source-of-truth`),
  confirmed all three findings, found one aggravation our review missed (boot persisted default device state
  *before* the restore stub ran — clobbering the last-good snapshot every boot), and fixed everything same day:
  `deactivate()` now clears the persisted `active_scenario` atomically (no restart resurrection), device state is
  restored at boot via a new `DevicePort.restore_state` seam (persist-without-restore rot closed — they chose
  *implement restore* over re-scoping the doc), and the toggle-power inversion closes as a consequence. Bridge
  suite 502 passing; their §7.1 doc overpromise corrected. Voice-side: review-index row + a one-time status
  pointer in `faf_durable_execution_review.md` updated (the frozen findings stand — they were verified correct).
  No voice-side scope change: VWB-18 was bridge-internal; TEST-17 still gates on VWB-15 (contract artifact),
  which remains open bridge-side.

- **2026-07-02 — QUAL-61 + BUG-20 DONE — the durability arc closed with the cuts, and the gate run flushed out
  a real test-hermeticity bug.** **QUAL-61** (all three ARCH-27 D-7 cuts): the never-invoked retry machinery
  deleted from `handlers/base.py` (−98 LOC + the `max_retries`/`retry_delay` launch params); `AsyncTimerManager`
  deleted entirely (`core/timers.py` + engine/composition wiring — the durable store + reconciler IS the
  scheduler); the dead `inspect_active_action` path + its dataclasses trimmed from `debug_tools.py` (the live
  `/debug` status endpoint kept) and the never-read `NotificationMessage.retry_count`/`max_retries` fields
  removed. **BUG-20** (filed + fixed same day): the recurring `test_conversation_offline_degrades_gracefully`
  flake was NOT machine load — the "offline" smoke SUT inherited real LLM keys from the developer shell AND the
  repo `.env` (`load_dotenv()` in every runner), so the test made a **live DeepSeek call** that flaked on slow
  API responses; the ARCH-28 journal note's load hypothesis had causality backwards (the 59s suite runs were the
  slow-API runs). Fix: smoke fixtures launch the SUT with every `*_API_KEY` **blanked, not stripped** — dotenv
  never overrides an existing var, so empty beats both leak paths. Proof: smoke 6/6 in 12.5s truly offline, and
  the full suite dropped 24–59s → **~20s** (it had been calling DeepSeek every run). Gates: 1156 passed /
  7 skipped ×2 consecutive runs; pyright clean; lint-imports 10/10. Both moved active→done. **The QUAL-56
  durability arc is fully closed:** review → ARCH-27 design → BUG-19 → ARCH-28 substrate → QUAL-62 gate →
  QUAL-61 cuts. Journal rotated per `one-active-journal` (this file exceeded the ~1500-line high-water).

- **2026-07-02 — QUAL-62 DONE — the ARCH-28 seam is now in the hexagon gate (user: "shouldn't we reflect it
  in our hexagon gate?").** New 10th import-linter contract *"Durable-action store is reached only through its
  seam (ARCH-28)"*: no application/delivery/adapter layer may import `irene.core.durable_actions`; the three
  sanctioned gateways (F&F choke point in `intents.handlers.base`, reconciler in `core.engine`, redelivery in
  `core.notifications`) are `ignore_imports` edges, so chains THROUGH the seam pass while any new direct import
  from an outer layer fails. The contract demonstrated it bites during introduction — it flagged the transitive
  `webapi_router → notifications → durable_actions` drain chain until the gateway edges were sanctioned. Design
  doc D-2 annotated with the gate. lint-imports 10/10 kept; contract test green. Filed + completed same day.

- **2026-07-02 — ARCH-28 DONE — durable-action substrate implemented (all 7 design slices, same-day as the
  design).** A timer is now literally restart-proof end-to-end: launch persists a schema-v1 intent record to
  `<assets_root>/state/durable_actions.json` (new `AssetConfig.state_root`, asset-managed + volume-mounted;
  atomic temp+rename writes; corrupt-file-safe), completion deletes it inside the done-callback, and
  `engine.start()` reconciles at boot — future deadlines re-arm via the handler's `rearm_durable_action` hook
  (timer relaunches with remaining time, reuses the persisted name, bumps its counter past it), deadlines missed
  ≤1h fire with a localized apology, older ones announce as expired. Completions flagged
  `redeliver_on_reconnect` survive an offline satellite: queued (TTL 1h, `created_at` preserved) and drained
  when `/ws/audio/reply` re-attaches. Failure notifications now announced by default (D-5). Read-only
  `/monitoring/actions` + `/monitoring/actions/history` shipped (contract regenerated, config-ui green).
  `client_registry.json` re-homed to `state/` with legacy `cache/` read-fallback (its registrations used to die
  with the container). Docs: `howto-new-intent.md` gained the "Long-running actions" authoring section, CLAUDE.md
  gained the **`durable-actions` invariant**, `client-registry.md` documents the durable twin (+ corrected its
  stale auto-expiry claim from QUAL-58). The restart test shipped WITH the substrate (12 tests in
  `test_durable_actions.py`) and immediately earned its keep: the reconciler's future-deadline-with-missing-
  handler branch mis-classified as fire-late and was fixed to announce-expired. Gates: 1156 passed / 7 skipped;
  pyright clean on 11 touched files; import-linter 9/9; openapi 108 paths + config-ui `check`/`build` green.
  _Note: `test_smoke_e2e.py::test_conversation_offline_degrades_gracefully` flaked twice under heavy machine
  load during this work (59s full-suite runs), passing in isolation and in two consecutive normal-load full
  runs — watched, not chased; file a task if it recurs._ QUAL-61 (cuts) is now fully unblocked. ARCH-28 moved
  active→done.

- **2026-07-02 — ARCH-27 DONE — durable-action substrate designed (interactive session, all decisions
  user-confirmed).** Recorded at `docs/design/durable_actions.md` (D-1…D-10 + the §3 handler-authoring
  contract). The decisions, both rounds: durability is an **explicit per-launch opt-in** (`durable=True`; timer
  is the only consumer today — confirmed — TTS/audio stay ephemeral); store = **atomic JSON file**
  (`cache/durable_actions.json`, temp+rename) behind a `DurableActionStorePort` (SQLite stays a drop-in swap);
  recovery = **re-arm by relaunch** through the normal launch path with the remaining duration (reconcile-by-diff,
  not log replay), missed deadlines **fire-with-apology** within a 1h grace window, expiry-announcement beyond it;
  **failures announced by default** (flip `critical_only`; sub-30s success suppression stays); redelivery of
  offline completions is a **handler-declared flag** (`redeliver_on_reconnect` — timer sets it; at-least-once for
  flagged, best-effort otherwise); the dead **retry machinery is cut** (QUAL-61 annotated UNBLOCKED — all three
  cuts confirmed, incl. `AsyncTimerManager`: the store + reconciler IS the scheduler); naming/identity rides
  BUG-19 (re-arm reuses the persisted action_name); observability = **minimal read-only**
  `/monitoring/actions[/history]`; rules bind via a new **`howto-new-intent.md` durability section +
  a `CLAUDE.md` `durable-actions` invariant**, both landing with the implementation. Bridge lessons baked in:
  delete-at-completion atomic with the in-memory clear (anti stale-intent resurrection), persist+restore+restart
  test ship together (anti persist-without-restore rot), ephemeral-field filter, shutdown discipline. Per
  `design-then-implement`: ARCH-27 moved active→done; **ARCH-28** filed (7 implementation slices, `[release]`).
  _Corrected same day (user review of the design): the store must live under the **asset-managed tree**, not
  `cache/` — new `<assets_root>/state/` folder (`AssetConfig.state_root`), because `assets_root`
  (`IRENE_ASSETS_ROOT`) is what's volume-mounted outside the Docker container; a redeploy must not wipe the
  records that exist to survive restarts, and `cache/` semantics (deletable) are wrong for durable state.
  Verification also surfaced that `client_registry.json` defaults to cwd-relative `cache/` (= `/app/cache`
  **inside** the container) — registrations already don't survive a container replacement; its relocation to
  `state/` (with old-path read-fallback) folded into ARCH-28 slice 1. D-2 + §4 amended._

- **2026-07-02 — BUG-19 DONE — F&F action-store correctness (the QUAL-56 fixes that don't wait for ARCH-27).**
  Four fixes: **(1)** audio/TTS action names are collision-proof (uuid suffix — same-millisecond launches used
  to collide), and the store is identity-safe: `remove_action(expected=)` guard means a displaced record's
  done-callback can no longer evict a live successor under the same key; `add_action` logs an error on live
  displacement. **(2)** The per-identity cap eviction now cancels the evicted task instead of leaving an
  untracked zombie. **(3)** Failure unmasking at the single choke point: the launch wraps every action coroutine
  with a falsy-return check — the handler `return True/False` convention was ignored, so TTS/audio coroutines
  that swallowed their own exceptions were recorded as SUCCESS; now `False` raises and the failure path runs
  (the two swallow blocks re-raise to keep the real error text). Centralized, so all 14 current bool-convention
  sites and every future handler inherit it. **(4)** Timeout is no longer indistinguishable from user
  cancellation: the monitor marks `ActionRecord.timed_out` before cancelling; history says `"timeout"` and
  metrics finally receive `timeout_occurred=True`. Gates: 1144 passed / 7 skipped (6 new regression tests; 1
  outdated test updated to the new raise contract); pyright clean on the 4 touched files. BUG-19 moved
  active→done. Next from QUAL-56: ARCH-27 (substrate design + handler rules), then QUAL-61 rides its
  keep-or-cut calls.

- **2026-07-02 — QUAL-56 DONE — F&F durability critique + comparative bridge persistence analysis
  (user-requested).** Deliverable frozen at `docs/review/faf_durable_execution_review.md` (two parallel
  deep-reads: the F&F subsystem across 8 durability dimensions; how `../wb-mqtt-bridge` persists device state).
  **Verdict: zero on every durable-execution axis, by explicit design** — the action store is deliberately
  runtime-only, so a restart silently loses a 24h timer ("list timers" then denies it existed); delivery of
  deferred completions is at-most-once with five independent silent-drop points (incl. a preference gate that
  suppresses sub-30s completions and *all* non-critical failures by default); the retry machinery is dead config
  (`max_retries=0` everywhere); TTS/audio coroutines mask their own failures as success; name collisions can
  silently overwrite a *live* store record; `AsyncTimerManager` is instantiated-but-never-used dead capability.
  **Bridge comparison** sharpened the design brief: borrow its generic key→JSON SQLite store behind a hexagonal
  port, chokepoint dirty-write, ephemeral-field filter, and reconcile-by-diff restore — and design against its
  two demonstrated failure modes: persist-without-restore rot (device-state restore is still a logging stub) and
  the stale-intent key (deactivated scenario **resurrects on restart** and powers AV gear back on — filed to the
  bridge as **VWB-18**, left uncommitted per `cross-repo-source-of-truth`, with the restore-stub and
  toggle-inversion findings). **User scope statements recorded in the review:** durability is a platform
  requirement (future smart-home handlers), and the remedy = "a fix + rules for new handlers". Follow-ups filed
  accordingly: **ARCH-27** `[release]` (design: durable-action substrate at the F&F choke point + the
  handler-authoring durability rules, per `design-then-implement`), **BUG-19** `[release]` (collision-safe
  names + identity-safe add/remove, cancel-on-cap-evict, unmask TTS/audio failures, timeout≠cancel), **QUAL-61**
  `[deferred]` (dead-capability removal, gated on ARCH-27's keep-or-cut calls). QUAL-56 moved active→done.

- **2026-07-02 — QUAL-59 DONE — capability drift fixed + dead code deleted (user directive: "I prefer dead code
  to be removed").** **(A6)** `/system/capabilities` now derives its provider/workflow lists from what is actually
  loaded (components' `providers` dicts + `workflow_manager.workflows`) instead of hardcoded lists that advertised
  the long-gone `continuous_listening` workflow and missed the `llm` NLU provider; regression test added.
  **(A7)** deleted outright rather than repaired: the entire dead Phase-3.5 action-management interface in
  `handlers/base.py` (7 zero-caller methods incl. the domain-keyed `cancel_all_actions`/`get_action_status` that
  would mis-cancel/double-record if ever wired — ~300 LOC, `base.py` 1350→1043 lines), the handler-side
  action-debugger wiring it existed for, the two `/intents/actions/*` REST stubs + their 3 orphaned schema
  classes, the zero-caller ContextManager introspection machinery (`get_context_for_intent_processing` +
  4 siblings incl. `cleanup_session`, which bypassed the BUG-16 metrics seam), and the 2 tests that only
  exercised deleted methods. Live-but-fragile code fixed instead: `nlu_component`'s cwd-dependent
  `Path("irene/...")`/`Path("assets")` are now package-relative. Because REST endpoints were removed, the
  committed contract was regenerated end-to-end: `scripts/dump_openapi.py` (106 paths) → config-ui
  `npm run gen:api-types` → `check` + `build` green (apiClient never used the stubs;
  `config-ui-stays-functional` upheld). Gates: 1138 passed / 7 skipped; pyright clean on all 7 touched files;
  import-linter 9/9 kept. QUAL-59 moved active→done — the QUAL-57 review's filed follow-ups are now ALL closed
  except QUAL-60 (deferred summarization enhancement).

- **2026-07-02 — QUAL-58 DONE — memory-hygiene sweep (QUAL-57 M4–M8), all five items, user-requested same-day.**
  **(M4)** the resampling cache is now byte-bounded: 4 MB total budget + 1 MB per-entry bypass (full synthesized
  TTS replies are never cached — that was the tens-of-MB retention), FIFO on either bound, `cache_bytes` surfaced
  in stats. **(M5)** new `ClientRegistry.prune_stale_history()` drops per-identity completed-action history keys
  once their newest entry is an hour stale — the keysets grew monotonically with session-derived physical ids.
  **(M6)** the ContextManager cleanup loop now drives the registry's hygiene each cycle: `reap_dead_actions()`
  (the advertised layer-3 sweep finally has a runtime caller; the 4-layer docstring corrected) + the M5 prune.
  Judgment call: `cleanup_expired_clients` deliberately left manual — nothing refreshes `last_seen` during a
  live WS connection, so auto-expiry would unregister a live-but-quiet satellite mid-connection; documented in
  its docstring (the ledger text offered wire-or-document). **(M7)** `NotificationService` queue bounded
  (maxsize 1000; `put_nowait` + drop-with-warning so the F&F completion path never blocks) and
  `send_notification` lazily starts the processing loop — the consumer-less getter-minted-instance path is dead;
  the six provider `warm_up` preloads now hold their task refs (were GC-cancellable mid-model-load). **(M8)**
  the trace dir is rotated to the newest `MAX_TRACE_FILES = 500` on every save (each file embeds full base64
  audio); constant not config, same safety-net reasoning as BUG-17's cap. Gates: full suite 1139 passed /
  7 skipped (7 new tests in `test_memory_hygiene.py`; cache-stats shape test extended); pyright clean on all 11
  touched files; no user-facing doc describes any of these internals (checked); no config/REST shape change →
  config-ui untouched. QUAL-58 moved active→done. Of the QUAL-57 memory findings only QUAL-60 (deferred
  summarization enhancement) remains.

- **2026-07-02 — BUG-18 DONE — LLM conversation store bounded; `max_context_length` finally real (user chose
  "window now + file summarization").** The config key was read and never applied — the conversation handler's
  message store and domain threads grew per turn for the session's life, and every turn shipped the full history
  to the LLM. Now: `UnifiedConversationContext.trim_handler_messages` windows the store to the last
  `max_context_length` **turns** (×2 messages) with the seed system prompt pinned (reusing the
  `clear_handler_context(keep_system=True)` convention); `add_to_thread` gained a `max_messages` bound applied at
  both handler thread sites; the handler trims at both append seams — after the user append (before the LLM call,
  so the prompt is capped too) and after the assistant append. Config descriptions clarified (turns kept in the
  window) in `config/models.py` + `config-master.toml` — shape unchanged, config-ui `check` + `build` pass. Filed
  **QUAL-60** `[deferred]` for the summarize-then-truncate continuity enhancement (the trim call is the single
  choke point, so it slots in cleanly later). Gates: full suite 1132 passed / 7 skipped (4 new tests in
  `test_conversation_window.py`, incl. an 8-turn e2e proving the per-turn LLM prompt stops growing); pyright
  clean. BUG-18 moved active→done. All three QUAL-57 `[release]` memory findings are now fixed.

- **2026-07-02 — BUG-16 + BUG-17 DONE — the two high-severity QUAL-57 memory leaks fixed same-day (user: "fix
  BUG-16 and BUG-17 right away").** **BUG-16 (metrics session leak):** `record_session_end` now completes the
  session action under its real QUAL-9 key (`"session_{sid}:session"` — the old bare-domain check never matched)
  and **removes** the per-session `DomainMetrics` entry instead of retaining it forever; ended sessions leave a
  compact summary in a bounded `_recent_sessions` deque(100) + a lifetime counter; `get_session_analytics`
  active-check fixed to the real key and aggregates fold in the recent ring. Eviction now closes metrics through
  one seam: `ContextManager.remove_context` calls `record_session_end`, and the lazy sweep + `get_context` expiry
  both route through it (the sweep previously skipped metrics entirely). Side benefit: `current_concurrent_actions`
  is no longer permanently inflated by zombie session actions. **BUG-17 (`/ws/audio` unbounded batch buffer):**
  the batch-floor utterance loop is now capped at `WS_MAX_UTTERANCE_SECONDS = 60` (bytes derived from the
  registered sample rate); on overflow the utterance is **force-finalized** (processed, `metadata.overflow=true`,
  warning logged) and the loop continues — VAD-path max-duration semantics; a stuck client is bounded at ~1.9 MB
  instead of ~115 MB/h. Constant, not config, by design (safety net, not a tunable — avoids dragging
  CoreConfig/config-ui along). Gates: full suite 1128 passed / 7 skipped (incl. 8 new regression tests:
  `test_metrics_sessions.py`, 2 eviction-seam tests, 1 WS overflow e2e); pyright clean on the 3 touched files;
  `/monitoring/sessions` REST contract unchanged (built from system metrics) → config-ui unaffected;
  `dataflow.md` updated (`user-facing-docs-are-done`). Both moved active→done.

- **2026-07-02 — QUAL-57 DONE — general architecture review + memory-overconsumption audit (user-requested).**
  Deliverable frozen at `docs/review/arch_memory_review_2026-07-02.md`. Ran as 3 parallel deep-reads (architecture
  map / multi-turn memory / F&F re-verification + `create_task` census); the 3 headline memory findings were then
  spot-verified directly in code. Architecture verdict: top-quartile bones (enforced hexagonal layering with zero
  live violations, entry-point provider discovery, donation-driven NLU cascade, real streaming-ASR seam for ESP32),
  with the SOTA gaps at the interaction layer — no barge-in, whole-utterance TTS, no per-client concurrency
  isolation, weak session continuity (A1–A4, recorded for user decision). F&F: **all 10** QUAL-8 findings verified
  resolved by the QUAL-28 store redesign — the historically-worst memory offender is now clean. The live memory risk
  sits in the request path instead: filed **BUG-16** (metrics session leak — `record_session_end` key mismatch makes
  every REST call/WS connection permanently grow the singleton collector), **BUG-17** (`/ws/audio` batch floor
  accumulates PCM with no cap — ~115 MB/h per stuck client), **BUG-18** (LLM conversation store unbounded;
  `max_context_length` config is dead), plus **QUAL-58** (M4–M8 hygiene sweep) and **QUAL-59** (capability drift +
  dead Phase-3.5 code). A5 (in-memory action store, nothing survives restart) confirms QUAL-56's premise — that
  deferred task stands unchanged. Ledger: QUAL-57 moved active→done; review index row added.

- **ARCH-26 DONE — Irene↔bridge catalog contract settled (interactive design session).** Both questions decided with
  the user and recorded in `mqtt_integration.md` (banner + §5a/§8/§12/§13.3 + new **§14**). **(1)** Catalog refresh is
  **lazy** (startup pull + re-pull on a resolution/actuation miss) — Irene runs **no MQTT client**, does not subscribe
  to `bridge/catalog/version`, which resolves the §5a-vs-§8 contradiction in favour of no-MQTT; so "Irene never speaks
  MQTT" is now literally true, and the retained topic stays a bridge concern. **(2)** A committed, openapi-based
  **development contract artifact** (bridge `/openapi.json` = `CatalogResponse` + action-request body; a curated golden
  catalog "the works" + a real WB7 dump; canonical home **eval-commons**) plus a **bidirectional contract-testing seam**:
  the canonical `DeviceCommand` is the boundary, `{utterance → canonical}` crossover fixtures are the shared truth, Irene
  is the producer (via PR-1's capturing fake bridge = a new eval-commons `device_command` provider, text-first) and the
  bridge is the consumer — neither needs the other running. Filed **TEST-17** (contract bundle) + **TEST-18** (capture
  provider + producer tests) here; **VWB-15** (emit artifact) + **VWB-16** (consumer test) added to the `wb-mqtt-bridge`
  ledger (uncommitted there, per the user). ARCH-26 moved active→done; eval README "Future surfaces" updated.
  _Clarified same day (publish boundary): the bridge is the generator and commits its reference artifacts in the **bridge
  repo** — it does NOT write to eval-commons; TEST-17 owns the one-way pin into `eval-commons/contracts/`. Tightened §14,
  TEST-17, and VWB-15 so a bridge dev isn't left guessing where to publish._
- **ARCH-26 filed — two Irene↔bridge catalog-contract clarifications to settle before ARCH-8 PR-2.** A multi-agent MQTT
  status review surfaced a real design gap: `mqtt_integration.md` §5a/PR-2 have Irene *subscribe* to the retained MQTT
  topic `bridge/catalog/version`, while §8 asserts Flow 2 adds no MQTT dependency — contradictory (you can't subscribe
  with an HTTP client), and the bridge exposes the version hash only over that topic (no lightweight REST/SSE signal). So
  the earlier "Irene never speaks MQTT" framing is only true once this is decided (MQTT-subscribe vs REST-poll vs
  bridge-adds-a-cheap-signal). Bundled with a second, development-unblocking ask (user-requested): a committed
  **openapi.json-style catalog contract artifact** — a JSON Schema of the `/system/catalog` response + a sample dump,
  shared cross-project — so Irene's PR-1/PR-3 can build the `DeviceCatalog`/resolver against a concrete contract with no
  live bridge. Design task (deliverable = an `mqtt_integration.md` edit + filed follow-ups); `[deferred]` to match the
  P-TBD parent ARCH-8. Registered in the design index against `mqtt_integration.md`.
- **BUG-15 DONE — AssetManager no longer wedges on a partial download (filed + fixed on request).** The I18N-8 note
  became a task: `download_model` trusted `model_path.exists()` as "download complete", so an interrupted/failed
  extraction left a broken-but-present pack that was never re-downloaded (the empty `piper/amy` + `piper/irina` dirs that
  failed Piper warm-up). Fixed both roots in `irene/core/assets.py`: (1) extraction now **stages into
  `.<name>.incomplete` and renames into place only on success** (was: unpacked straight into the final path, and the
  `except` cleaned only the archive) — so a failure never leaves a partial; (2) the cache check skips only a **populated**
  path (`_is_populated_download`: non-empty file, or dir with ≥1 file), clearing an empty/partial one and re-downloading.
  `download_model_pack` already validated members, so it was fine. 4 regression tests in `test_asset_extract.py`. Gates:
  pyright 0, suite 1120, import-linter 9/9. Tagged `[release]` (any interrupted first-boot download on a satellite would
  otherwise wedge a model).
- **I18N-8 DONE — English eval suite green end-to-end (+ a base-provider runtime fix it exposed).** Brought up
  `embedded-armv7-en` locally (Moonshine downloaded + extracted cleanly — the `_bz2` venv fix proven in the real asset
  path) and ran the English suites: **`make ws CONFIG=embedded-armv7-en` = 4/4** (Moonshine WER ✓ + intent ✓ +
  DeepSeek-UX ✓) and recorded **`traces/en/timer_set_10min.json`** — an *audio-input* golden captured from the live run
  (so `make replay` re-runs the real ASR, a stronger regression than the ru text-golden) → **`make replay
  CONFIG=embedded-armv7-en` = 1/1** (offline, matches oracle). **The first component-level EN run exposed a real bug:** the
  base sherpa `is_available()` hardcoded the `sherpa_onnx` asset namespace, so the ASR component evaluated the
  `sherpa_moonshine` subclass under the wrong namespace, judged it "not available (dependencies missing)", and dropped it
  — `/ws/audio` then rejected every fixture with `asr_required_for_audio` (0/4). Fixed at the base (altitude): key
  `is_available()` + `download_model_pack()` on `get_provider_name()` so any subclass resolves its own namespace
  (behavior-preserving for the base, whose name *is* `sherpa_onnx`); added a regression test. This means I18N-2's
  "end-to-end" validation had only exercised the provider directly, not through the ASR component gate — I18N-8 is where
  the true integration closed. Also verified the full EN stack boots clean incl. Piper `amy` TTS (an earlier amy warm-up
  error was a **stale pre-`_bz2` empty model dir** that `AssetManager`'s existence check skipped re-downloading; cleared
  amy + irina, both re-download fine). Gates: pyright 0, suite **1116** (+1 regression), import-linter 9/9. The
  dir-existence fragility this surfaced (re-using a broken partial after an interrupted extraction) is now **BUG-15**.
- **Doc + dev-env follow-ups to BUG-14 (no repo behavior change).** (1) Annotated the stale
  `docs/design/onnx_inference_layer.md` §4 — its `sherpa-onnx==1.10.46` armv7 pin was **superseded** by BUG-14 (the
  ELF-alignment failure is now patched in-build via `patch_onnx_align.py` + bookworm base; pin is **1.12.36**). Added a
  supersession banner + inline notes on the two live-reading pin recommendations, pointing to `multilingual_deployment.md`
  §2d and the Dockerfile.armv7 header. (2) Confirmed the user-facing `docs/guides/build-docker.md` needs **no** change —
  it abstracts above the base OS / onnxruntime, and BUG-14's patch runs in the *builder* stage so "nothing build-only is
  left behind" still holds. (3) Rebased the local dev `.venv` off the source-built `/usr/local` Python 3.11.4 (compiled
  **without `_bz2`** → `.tar.bz2` model extraction failed locally, though deployment images are fine) onto uv-managed
  **cpython-3.11.12** (`_bz2` present); identical 204-dep closure, both editables (irene + eval-commons) restored, suite
  **1115 passed / 7 skipped** (2 formerly-skipped bz2-gated tests now run). Unblocks a fully-local I18N-8 run.
- **I18N-2 DONE — offline Moonshine wired as the armv7 English ASR (subclass, end-to-end validated).** Implemented
  **`SherpaMoonshineASRProvider(SherpaOnnxASRProvider)`** (`irene/providers/asr/sherpa_moonshine.py`, entry point
  `sherpa_moonshine`) for `sherpa-onnx-moonshine-tiny-en-quantized-2026-02-27` (43 MB merged `.ort`, English-only,
  offline). Subclass (not a base `model_type`) because Moonshine diverges from the VOSK/Whisper families on all three
  axes the base assumes shared: **distribution** — a k2-fsa GitHub `.tar.bz2` via `AssetManager.download_model`
  (URL+extract, like Piper voices), not an HF model-pack; **pack shape** — merged `encoder_model.ort` +
  `decoder_model_merged.ort` + `tokens.txt` (resolved recursively); **construction** — the merged decoder isn't exposed
  by `OfflineRecognizer.from_moonshine()`, so the recognizer is built directly from `OfflineMoonshineModelConfig(…,
  merged_decoder=…)` using the internal `_Recognizer` grabbed from the factory's globals (version-agnostic). Mirrors
  `piper_ruaccent ⊂ piper`. Everything else inherits — crucially the **offline** path (`supports_streaming` False →
  `/ws/audio` batch branch → **dodges BUG-13**, the streaming-head-drop that sank the original zipformer pick). Swapped
  `configs/embedded-armv7-en.toml` ASR to `sherpa_moonshine` and **retired** the rejected `zipformer-en-20M` catalog
  entry in `sherpa_onnx.py` (kept the `zipformer-streaming` model_type as a generic online-transducer alias). The
  dynamic sherpa construction is annotated against `Any` (its Python objects are built at import and the merged-decoder
  path isn't in the typed API) — honest imports, no `# type: ignore`. **Validated end-to-end on x86_64** (sherpa
  1.13.2): both real recorded fixtures transcribe cleanly (`light_unreachable`, `timer_10min`). Gates: pyright 0,
  config-validator ✓, suite **1113** (+3 new Moonshine unit tests), import-linter 9/9. Unblocked by BUG-14 (bookworm +
  p_align patch + sherpa 1.12.36, proven on the WB7). Remaining follow-up **I18N-8** — a green English `make ws` — needs
  a bz2-capable env for the `.tar.bz2` extraction (the dev `.venv` Python lacks `libbz2`, the same gap that blocks Piper
  amy locally; the WB7/Docker image has it).
- **BUG-14 DONE — armv7 Docker fixed to run sherpa 1.12.36 + Moonshine (proven on the WB7).** Implemented the
  user-approved "build the libs in Docker" fix in `docker/Dockerfile.armv7`: base bullseye→**bookworm** (for
  GLIBCXX_3.4.30, which sherpa ≥1.12's C++ module needs; +4.4 MB on the WB7), a new **`docker/patch_onnx_align.py`** step
  that rewrites the bundled onnxruntime `.so` `PT_LOAD` `p_align` 64K→4K (the ELF-alignment fix; verified: patches the
  armv7 `.so`, idempotent, safe no-op on 64-bit / non-ONNX configs), and bumped the armv7 sherpa pin **1.10.46→1.12.36**
  (`pyproject.toml` + `uv.lock` — scoped: only sherpa armv7 changed, 64-bit stays 1.13.3). One pin serves **both** RU
  (vosk `from_transducer`, API-compatible) and EN (Moonshine merged `.ort`) — the ru/en split needs no per-config build
  machinery, `CONFIG_PROFILE` already drives the analyzer. **Proven end-to-end on the WB7** (root@192.168.110.250): patched
  sherpa 1.12.36 on bookworm imports and runs Moonshine — RTF ~0.7 (faster than RU vosk's 1.15), 134 MB RSS, both
  fixtures perfect. Also reconciled the "proven on hardware" claim (§4 pinned 1.10.46 for this exact ELF issue — I'd
  tested the wrong versions). Unblocks **I18N-2** (wire the Moonshine subclass). Config-validator green; the full
  `docker buildx build` of the armv7 image stays a deploy checkpoint (untested even before, per §4.7). WB7 left clean.
- **WB7 on-hardware test → BUG-14 filed; Moonshine is the armv7 English ASR, gated on an onnxruntime build.** SSH'd to
  the WB7 (root@192.168.110.250) and ran Moonshine in the deployment-base container. Found `import sherpa_onnx` fails at
  the native lib — `libonnxruntime.so: ELF load command address/offset not properly aligned` — for sherpa 1.13.2 (PyPI)
  **and** 1.12.36 (PiWheels), on the host py3.9 (cp39) **and** a py3.11 container (cp311). Digging into the "proven on
  hardware" evidence reconciled it: `onnx_inference_layer.md` §4 **already documented this** and pinned
  `sherpa-onnx==1.10.46` (applied at `pyproject.toml:59`) — I'd tested the wrong versions. But 1.10.46 has **no**
  `OfflineMoonshineModelConfig`, and the merged Moonshine needs sherpa ≥1.12 → a version pincer. Filed **BUG-14** (the
  onnxruntime armv7 alignment defect, now load-bearing for English). **User decision:** this does not block Moonshine —
  build the corrected onnxruntime in the armv7 Docker (patchelf/rebuild) + bump the pin. So the ledger now reads:
  **armv7 English ASR = Moonshine (chosen), sequence BUG-14 → I18N-2.** WB7 left clean (workdir removed, no new
  containers/images — all reused/`--rm`). aarch64/x86_64 unaffected.
- **I18N-2 leading candidate = `moonshine-tiny-en-quantized-2026-02-27` (offline, 43 MB); WER `ten`/`10` fix applied.**
  ChatGPT surfaced a newer Moonshine build; verified it: it's the *merged-`.ort`* quantized export at **43 MB** (not the
  123 MB `-int8` that was rejected), offline (no head-drop), **loads on our sherpa-onnx 1.13.2 with no bump** (merged
  decoder via `OfflineMoonshineModelConfig(encoder=, merged_decoder=)`, since `from_moonshine` doesn't expose it), and
  transcribes the real recorded fixtures cleanly (a slower re-record of the timer fixed the earlier fast-speech miss —
  pace, not the model). `linux_armv7l` wheels ship; offline → batch → dodges BUG-13. Distributed as a k2-fsa GitHub
  `.tar.bz2` (not HF), so it uses the URL+extract download path. **Planned wiring: a subclass**
  `SherpaMoonshineASRProvider(SherpaOnnxASRProvider)` (mirrors `piper_ruaccent ⊂ piper`) to isolate the tarball
  download + merged-decoder construction; the base stays clean. Recorded as the I18N-2 leading candidate (design §2d).
  Applied the `ten`/`10` fix in eval-commons `wer_scorer` (`a7b8a1e`: fold English number-words to digits) — the timer
  case now scores 0.000. **Only open gate: on-device armv7 runtime/RAM on the WB7** (currently unreachable).
- **I18N-2 REOPENED + BUG-13 filed — the first real English `make ws` exposed that zipformer-en-20M is unusable.** The
  recorded English fixtures (I18N-8) are good (offline Moonshine transcribed them, one perfectly), but `make ws
  CONFIG=embedded-armv7-en` came back 4/4 TimeoutError. Diagnosis: `zipformer-en-20M` (the I18N-2 pick) is a **streaming**
  (online) transducer — it **drops the utterance head** on bounded commands ("set a timer for ten minutes" → `''`;
  "turn on the light in the garage" → `"T IN THE GARRAGE"`), and it routes `/ws/audio` into a streaming branch that
  **hangs** for bounded delivery (no partial/response, 30 s timeout). RU works because vosk-small-ru is **offline**
  (whole-buffer). The I18N-2 spike scored zipformer on clean LibriSpeech clips (lead-in silence), which masked the
  head-drop — the lesson is to benchmark on the actual utterance shape, not corpus clips. **Reopened I18N-2** for a
  small OFFLINE arm32 English ASR (**Moonshine rejected — 124 MB too big**, per user); **filed BUG-13** for the
  streaming-branch hang. aarch64/x86_64 English is unaffected (Whisper is offline). The English harness + rubrics remain
  proven; the suite can be greened on an offline 64-bit config meanwhile. Committed the validated `fixtures/en/*`.
- **Recorder made language-aware (enables I18N-8).** The fixture recorder read raw YAML, so the bilingual ws config
  broke it two ways: `fixtures/{{env.EVAL_LANG}}/…` stayed literal and the ru+en cases collided on the fixture key with
  different reference text (spurious conflict) — a gap in the I18N-5 harness (I'd validated the eval run, not the record
  path). Fixed in eval-commons `629fb8d`: `resolve_worklist(yaml, language=)` filters by `metadata.language` (`EVAL_LANG`)
  and resolves `{{env.VAR}}` in the audio path. Verified: `make record-list EVAL_LANG=en` lists the two `fixtures/en/*`
  with English prompts; `=ru` lists the existing ones. 5 recorder tests green. `make record EVAL_LANG=en` now works.
- **I18N-5 closed as DONE (harness); English audio recording split to I18N-8.** The harness is a complete, committed,
  validated unit, so it moves to the done ledger; the one mic-dependent remainder (record `fixtures/en/*` + a `traces/en/`
  golden) is now its own task **I18N-8** rather than a long-lived partial. No code change — a ledger split for accuracy.
- **I18N-5 (harness DONE) — bilingual eval; only mic-recorded English audio remains.** Built the multilingual eval
  harness and verified it end-to-end. Design decision (user-confirmed): **fixtures/traces partitioned by language
  subdirectory** (`fixtures/<lang>/`, `traces/<lang>/`) — same scenario filenames across languages so parity is a
  directory diff; moved the Russian assets into `ru/`. Added an **`EVAL_LANG`** axis to `eval/Makefile` (default `ru`,
  derived from the `*-en` CONFIG name; deliberately *not* `LANG`, which is the POSIX locale var), driving the fixture/
  trace subdir (`{{env.EVAL_LANG}}`) + `--filter-metadata language=$(EVAL_LANG)` (promptfoo ANDs it with `kind=ux`), plus
  an `EVAL_ROOM` (Кухня/Kitchen) since the room name is echoed in the failure reply. Cases are duplicated per language and
  tagged `metadata.language`; added EN config profiles and **EN rubrics** `shared/rubrics/en-ux.yaml` (co-equal, mirroring
  the TEST-16 structure). **Validated:** RU suite green under the new layout (`make ws CONFIG=embedded-armv7` = 4/4), and
  the EN rubrics scored **7/7** live against DeepSeek (pass genuine English; fail Russian/error/rude/non-confirmation) —
  first-try clean, consistent with DeepSeek's better English. Also migrated the RU ws cases to the co-equal rubrics
  (closes the TEST-16 loop) and fixed a stale `voice` config ref in `eval/README`. **Only remaining:** record
  `fixtures/en/*` + a `traces/en/` golden (needs a mic). The English stack is otherwise complete and runnable.
- **I18N-6 DONE — English donation audit: functional parity, no fill needed.** Compared `en.json` vs `ru.json` across
  all 13 handlers (structure, phrase coverage, examples/patterns). Result: full structural parity (identical methods +
  parameters, no stubs) and adequate idiomatic English phrases throughout. The only systematic difference is empty
  English lemmas — and that's correct, not a gap: lemmas are *additive* matcher keywords, Russian needs them for its
  heavy inflection (roots like `поставить`/`таймер`), English carries base forms in multi-word phrases and leans on
  fuzzy matching; single-word English lemmas (`set`/`stop`/`time`) would over-match and hurt precision. Closed as
  audit-only (user-confirmed) — no donation changes. This completes the buildable English stack (I18N-2/3/4/6/7);
  I18N-5 (English eval + fixtures) is the last open slice.
- **I18N-4 DONE — English deployment configs for all three arches; RU configs made explicitly RU-only.** Added
  `configs/{embedded-armv7,embedded-aarch64,standalone-x86_64}-en.toml` as full copies of their Russian counterparts
  with only the language-bearing fields swapped: armv7 → `zipformer-en-20M`/`zipformer-streaming` + Piper `amy`; aarch64
  → `whisper-small` (multilingual, config-only) + plain Piper `amy` (`piper_ruaccent` disabled); standalone →
  torch-whisper (config-only) + `silero_v3 v3_en` (`put_accent`/`put_yo` off), wake word already `hey_jarvis`. Each sets
  `default_language`/`supported_languages`=en at the top level, `[asr]` + `[asr.providers.*].default_language=en`,
  `auto_detect_language=false`, workflow + keyword-matcher language. **Symmetry (user-raised):** the three RU configs
  were implicitly bilingual (legacy `language="ru"` only → schema-default `supported_languages=["ru","en"]` +
  auto-detect on, which only ever changed the reply *string*, never ASR/TTS); they now declare `default_language="ru"` +
  `supported_languages=["ru"]` + `auto_detect_language=false` — one honest language per config, parallel to the `-en`
  files. `config-master.toml` stays the comprehensive `["ru","en"]` reference. Added an English worked-example pointer
  to `docs/guides/howto-new-language.md`. Gates: config-validator ✓ (12 configs), suite 1110, pyright 0. No schema
  change (config-ui unaffected). Remaining I18N: I18N-5 (EN eval + fixtures), I18N-6 (`en.json` donation audit).
- **I18N-3 + I18N-7 DONE — English TTS on all three arches (Piper on the satellites, Silero v3 on the standalone).**
  I18N-3: generalized the `ru_RU`-hardcoded Piper catalog to a locale param and added `en_US-amy`(default)/`lessac`/`ryan`
  — same `.tar.bz2` packs + sherpa runtime, no provider change; capabilities now report per-instance language so
  `piper_ruaccent` (always RU) stays RU. I18N-7: adjusted the *existing* `silero_v3` provider (not a new one) to pull
  speakers/accent/language **by model** — `v3_en` → `en_0…en_117`, default-speaker fallback, and the Russian
  `put_accent`/`put_yo` omitted for non-RU models (verified via real `v3_en` synthesis: 57 MB `.pt`, 119 speakers,
  `apply_tts(en_0)` clean — and put_accent turned out to be *accepted* by v3_en, so the guard is about semantics, not
  crashes; comment corrected). Gates: pyright 0, suite **1107**, import-linter 9/9. Both TTS tasks were hardware-
  independent and are fully done; the EN *configs* that wire these (I18N-4) and EN fixtures/eval (I18N-5) remain.
- **I18N-2 DONE — armv7 English ASR = `zipformer-en-20M` (measured, not guessed).** Downloaded both candidates and ran
  them locally on a shared LibriSpeech clip set (WER is architecture-independent, so the head-to-head is valid off the
  WB7): `zipformer-en-20M` = 43.6 MB int8, WER 0.091, streaming, proven `linux_armv7l`, ~zero code delta (reuses the
  existing online-transducer path); `moonshine-tiny-en` = 123.5 MB int8 (~3×), WER 0.030, offline, arm32 unproven, new
  `from_moonshine` branch. Moonshine is more accurate but **has no home** — too big/unproven for the armv7 tier,
  redundant with multilingual Whisper on the 64-bit arches — so zipformer wins the *slim + arm32-proven + torch-free*
  WB7 slot (small-model WER is the same accuracy-for-size trade `vosk-small-ru` makes for Russian). Wired: catalog
  `zipformer-en-20M` + `model_type="zipformer-streaming"` + language-derived `get_supported_languages` in
  `irene/providers/asr/sherpa_onnx.py`; streaming-alias test updated. Gates: pyright 0, suite 1105, import-linter 9/9,
  config-validator 100%. Residual on-WB7 RAM/latency folded into I18N-4; real English WER rides with I18N-5 fixtures.
- **I18N design refinement — standalone TTS is torch Silero, not Piper; Silero English caps at `v3_en`.** Corrected an
  over-unification in the I18N-1 design: TTS is per-architecture (Piper on the two torch-free satellites; the x86_64
  standalone runs `silero_v4` torch for Russian). The authoritative Silero `models.yml` shows Russian advanced
  `v3→v4→v5` but **English never left `v3`** (no `v4_en`/`v5_en`; confirmed at `silero_v4.py:54`). Decision (user):
  keep **torch parity** on the standalone with **`silero_v3 v3_en`** — same `.pt` size, one quality tier below RU
  `v4_ru`, accepted to avoid pulling the sherpa-onnx runtime into the torch image. The `silero_v3` provider already
  exists and already lists `v3_en` — the work is an *adjustment* (pull model + speakers by language), filed as
  **I18N-7**; I18N-3 (Piper) is now scoped to the satellites, and I18N-4 points the standalone config at `silero_v3`.
- **I18N-1 (design) — real English deployment: slim cross-arch model set + one-bulk-per-language eval.** Three
  read-only investigations settled the architecture question raised while adding EN UX rubrics: language auto-detection
  is wired only to text-understanding + response strings, **not** ASR/TTS (`switch_language` is a TODO stub;
  `persist_language_preference` + `[nlu_analysis.languages]` are dead config) — so the voice pipeline is **monolingual
  per config**, and language is a per-deployment choice, not a runtime switch (staying slim, as intended). The config
  language flag drives the text side automatically but ASR/TTS model paths are independent per-provider fields. **Model
  finding (web-sourced):** sherpa-onnx (ASR) + Piper (TTS) already span all three Docker arches torch-free with English
  models size-matched to the Russian stack — only **one new ASR asset** is genuinely required (armv7), because whisper is
  multilingual on 64-bit (config-only) and English Piper voices are the *same* k2-fsa `.tar.bz2` medium packs (a catalog
  generalization, not the "TTS blocker" it first looked like). armv7 EN ASR is a measured spike:
  `sherpa-onnx-streaming-zipformer-en-20M` (43.6 MB int8, proven arm32, streaming) vs `moonshine-tiny-en` (English-only,
  offline, better WER than whisper-tiny, arm32 unconfirmed). EN Piper voice = `amy`. Design →
  `docs/design/multilingual_deployment.md`; filed implementation slices I18N-2/3/4/5/6 (ASR spike, Piper catalog,
  `*-en.toml` configs, EN eval `LANG` axis + rubrics + fixtures, `en.json` donation audit). No code shipped.
- **TEST-16 (partial) — calibrated the DeepSeek Russian UX judge; hardened the shared rubrics.** The live UX suite's
  two cases are both expected-PASS happy paths, so they can't tell a working judge from one that rubber-stamps. A
  12-case balanced probe (both classes, run through the *same* `llm-rubric`→DeepSeek path, in scratchpad) showed the
  judge is **deterministic at temp 0** (stable across 4 runs) but **PASS-biased** — every disagreement was a
  false-accept, including an all-English graceful-failure reply passing. Fix attempt #1 (an emphatic "оцени как НЕ
  пройдено, если ответ не на русском" *override*) fixed English but **regressed the tone check** — the rude reply
  flipped FAIL→PASS (verified stable under both old and new rubric, so a real rubric side-effect, not variance): the
  override hijacked the judge's attention. Fix #2 (shipped) restructures `confirms_action_ru` + `graceful_failure_ru`
  in `../eval-commons/shared/rubrics/ru-ux.yaml` into **co-equal numbered conditions** (language is one condition among
  several, not an override) → probe agreement 83%→92%, `graceful_failure` 6/6, 0 false-rejects, 1 residual borderline
  false-accept. **Lesson:** happy-path-only judge suites are blind to the judge's dominant failure mode (leniency), and
  patching one rubric criterion can silently degrade another — re-measure ALL cases after any rubric edit. Full
  calibration (human/Russian-speaker gold labels, more negatives, Cohen's κ, propagate the rubrics into the live
  suite) stays open under TEST-16; the probe stays in scratchpad (not committed).
- **TEST-15 DONE — WS suite now scores ASR/WER, and the whole `make ws` is green live (WER + intent + UX).** The
  ledger assumed the SUT had to be changed to expose the recognized transcript; a live probe flipped that
  (`task-start-reconciliation`): the SUT **already** surfaces it at `metadata.audio_processing.transcribed_text` on the
  batch path (`_process_single_audio_pipeline` writes it, `/ws/audio` forwards it in `_meta`), matching the spoken
  reference exactly. User-confirmed approach = **eval-side only, no SUT change**: `ws_audio_provider` (in
  `../eval-commons`) now resolves the transcript in priority order — `metadata.audio_processing.transcribed_text` →
  last streaming `partial` → reply text — so WER scores the *recognized speech*, not the reply. Verified live vs
  `configs/embedded-armv7` with `DEEPSEEK_API_KEY` set: `make ws TARGET=local` = **4/4 pass** (WER 0 on «поставь таймер
  на десять минут»; intent `timer.set`; both DeepSeek-judged UX cases pass — 726 grading tokens confirm the judge ran),
  `make cli` still 5/5. Cleared the now-confirmed intent-name + unreachable-device TODOs in `ws.promptfooconfig.yaml`;
  refreshed `eval/README`. **Lesson:** reconcile against the *code*, not just the task text — the "missing" contract was
  already there; the only gap was the harness not reading it. Closes the trace-driven system-testing slices
  (TEST-12/13/14/15). DeepSeek Russian-judge *calibration* stays advisory (a standing UX-tier caveat, not a task).
- **BUG-12 DONE — the `make ws` "SUT failure" was promptfoo's response cache, not a hang/provider/SUT bug.** Chasing
  the apparent hang: it wasn't a hang (my Bash timeout) and the eval-commons `ws_audio_provider` is correct (`call_api`
  succeeds directly). The real cause: an early `make ws` against a mis-launched SUT cached "ASR provider 'whisper' not
  available" per fixture in `~/.promptfoo/cache`, and every later run **replayed the cached failure without contacting
  `:6000`** — the SUT log showed zero `/ws/audio` requests, while `PROMPTFOO_CACHE_ENABLED=false` made the same run hit
  the live SUT (sherpa_onnx) and return «Таймер установлен на 10 мин». Fix: `eval/Makefile` now exports
  `PROMPTFOO_CACHE_ENABLED := false` (every surface here is a live test — caching can only mask reality) + cleared the
  poisoned cache. Verified: plain `make ws` runs live, ASR case passes, intent confirms `timer.set`; `make cli` still
  5/5. Filed **TEST-15** for the WER-vs-reply-text gap (offline ASR emits no partials, so the provider returns reply
  text — WER needs the SUT to surface the recognized transcript in metadata). UX still needs `DEEPSEEK_API_KEY`.
  **Lesson:** a test harness that caches *live* tests is a footgun — a transient failure poisons every later run and
  reads as a persistent SUT bug. The user's "isn't the ws port different?" reframed it to "the request never reaches the
  SUT," which pointed straight at the cache.
- **BUG-11 DONE — the WS e2e "whisper" error was a broken config, not a `/ws/audio` provider bug.** Deep research
  (static-map agent + live instrumented repro) **disproved** the original hypothesis: a clean `embedded-armv7` SUT
  transcribes the recording correctly via `sherpa_onnx` (verified «Таймер установлен на 10 мин» success:true). The error
  came from running `voice.toml` — `[asr] default_provider="whisper"` with no `[asr.providers.whisper]` → zero providers
  → every request failed (the CR-A2 reconcile only fires when providers is non-empty). User-approved fixes: **(B)**
  deleted the 4 stale broken configs (voice/minimal/development/api-only) + repointed every ref (test→full,
  build_analyzer/validator/cli-test, eval Makefile/profile, QUICKSTART rewritten to copy config-master + toggle
  components, 3 guides, issue template, env-example, build-system diagram regenerated); **(A)** asr_component raises at
  init on enabled-but-zero-providers (was a silent warning → per-request 404s); **(C)** eval WS default config voice →
  embedded-armv7; **(D)** schema ASR default "whisper"/["whisper"] → ""/[] to match the runtime ASRConfig. Configs 13→9.
  Gates: pyright 0, config-validator 9/9, suite 1105, import-linter 9/9; armv7 re-verified. **Lesson:** the recordings +
  harness were vindicated — the system test did its job (surfaced a real config-robustness gap), and a stale-process
  artifact (my own `pkill -f irene-webapi` self-kill) muddied the early diagnosis. _Open: the promptfoo `make ws` run
  hangs where a direct WS client succeeds — a harness-level follow-up before WS is green e2e._
- **UI-14 DONE — config-ui §E completed: efficiency + E6 drift-guard done; E7/E9/E10 → UI-16; E8 non-issue.** Added the
  altitude half: E6 makes the `ContractEditor` enum dropdowns derive from `satisfies Record<Union,…>` keys, so a backend
  donation-enum change fails the build rather than silently dropping options (a TS union can't be enumerated at runtime,
  so a compile-time exhaustiveness guard is the right fix). Assessing the rest surfaced (UI-12-style) that §E's altitude
  items were partly over-credited: E7 (component roster) + E9 (widget heuristics) need backend schema metadata that
  doesn't exist (`is_component`/`widget` hints) → spun out as **UI-16**; E10 (spaCy-attr i18n) is niche → UI-16; E8
  (language labels/fallback) is a non-issue (display names are inherently UI; the `['en','ru']` fallback is defensible).
  Gate: config-ui check + build green.
- **UI-14 efficiency half DONE — config-ui perf fixes (behavior-preserving).** E1 derived `hasChanges` (removed the
  state-via-effect + the redundant `setHasChanges(false)` calls on the Templates/Prompts pages — verified each
  coincided with `data===original`, so equivalent); E2 `TomlPreview` debounce moved to a `useRef` (no re-render per
  keystroke); E3 all 14 `JSON.parse(JSON.stringify)` deep-copies → `structuredClone`; E5 memoized LemmasEditor's
  nested-loop suggestion scan + a per-row conflict map. **E4 skipped** (threading the memoized hash risks a cache-key
  mismatch on the manual-analyze path — minor perf, real risk). Gate: config-ui check + build green. UI-14 stays open
  `[~]`; the hardcoded-list/altitude half (E6–E10) is UX-touching / backend-contract-coupled — left as a separate call.
- **UI-13 DONE — config-ui dead-export removal (the clean one).** Verified 0 external refs for each (ESLint flags only
  unused *locals*; type-check would catch a mis-call), then deleted: 8 utility aliases (`types/index.ts`), 8 dead
  interfaces (`types/components.ts`, 239→174), `validateSpacyAttribute`, `wouldShowObjectObject`. Folded in: the 12
  hand-written `*Request` types in `api.ts` that C1 orphaned (the same-named `openapi.gen.ts` schemas are generated/
  separate), and the unused `ajv`/`ajv-formats` deps (UI-11 §B finding; `npm uninstall`). Gate green (check + build),
  confirming all dead. Contrast with UI-12: unlike presentation-coupled "duplication", dead exports ARE cleanly
  removable — verify-then-delete, gate-caught.
- **UI-12 DONE — config-ui duplication consolidation: the 2 clean dedups done, C2–C5 assessed-declined.** **C1** (apiClient
  per-language CRUD quintet → 6 shared helpers + thin typed wrappers, `123ce3b`) and **C6** (decompile scaffold →
  `useDecompiledPatterns` hook, `99c1432`) — ~280 lines genuinely removed, type-proven & behavior-preserving. Pushing
  into C2–C5 (per user's push-through choice) **surfaced that review §C over-credited them**: the pages/editors are
  same-concept-divergent-presentation, not clones (C2 ~10 page behaviors, many intentional; C3 Lemmas' per-row conflict
  badges + Spacy's index/styling; C4/C5 Template already uses ArrayOfStringsEditor + read-only keys vs Localization's
  type-switch/domain-hints) — merging changes UX, so assessed & declined (annotated in the review doc; user closed).
  Lesson: the config-ui "duplication" that's truly faithful is the pure-logic/byte-identical kind (C1/C6); concept-level
  similarity in presentation-coupled React components is not safely auto-dedup-able. Gate: config-ui check + build green.
- **UI-11 DONE — config-ui type-contract drift realigned (restores the type-check gate).** `src/types/api.ts` (what
  `apiClient` consumes) had fallen behind backend `CoreConfig` while the generated `openapi.gen.ts` sat current-but-
  unused. Realigned the 4 drifted types to the backend (verified vs the gen file + `models.py`): added `outputs`/`trace`
  + canonical `default_language`/`supported_languages` to CoreConfig, removed the phantom NLU language fields, rewrote
  VADConfig to the ARCH-18 shape (per-engine knobs now under `providers`). Zero consumer churn (no component read any
  drifted field — pure type-accuracy), so `config-ui-stays-functional`'s type-check no longer passes on false types.
  Gate: config-ui `check` + `build` green. Durable follow-up (derive `api.ts` from the generated schema) noted but left
  as a larger structural call. Review cleanup remaining: UI-12 (dup) / UI-13 (dead) / UI-14 (efficiency) / UI-15 (feature).
- **BUG-10 DONE — config-ui blocking-conflicts dialog made reachable (read-only).** Blocking conflicts disable Apply, so
  the dialog's only opener (a branch inside the disabled handler) could never fire. Added a "Review blocking conflicts"
  trigger that opens it read-only (dropped the `console.log` `onResolve` stub → no dead Resolve buttons), removed the
  unreachable branch, +i18n (en/ru). User triaged to **build real resolution** → filed **UI-15** (design-then-implement);
  this is the foundation it builds on. Gate: config-ui `check` + `build` green. Closes the review's correctness cluster
  (BUG-8/9/10); cleanup UI-11..14 + feature UI-15 remain.
- **BUG-9 DONE — config-ui real-time analysis stale-request overwrite.** The post-await guard read the abort signal off
  the ref (newest controller), so a slow earlier response clobbered newer conflicts; fixed by guarding on a
  per-invocation local `AbortController` (the ref still drives abort-previous + unmount cleanup). Also threaded the
  signal through `analyzeDonation`→`post`→`fetch` so a superseded analysis cancels its network request, and hardened the
  `.conflicts` derefs against a malformed payload. Gate: config-ui `npm run check` + `build` green. BUG-10 remains.
- **BUG-8 DONE — config-ui DonationsPage composite-key + stale-state defects (the first remediation from the config-ui
  review).** Everything keyed by `${handler}:${language}` now: the 404-fallback no longer stores under the bare handler
  (which caused an **infinite reload loop** + stuck spinner), the validation *catch* stores the error under the key the
  tab indicator reads, the `globalParamNames` memo gained its missing `selectedLanguage` dep (and shed a copy-pasted
  `eslint-disable`), and CrossLanguageValidation renders behind a guarded `selectedHandlerInfo` instead of a non-null
  assertion that crashed if the handler left the list mid-reload. Gate: config-ui `npm run check` + `build` green.
  Remaining review correctness findings: BUG-9 (stale-request overwrite), BUG-10 (unreachable blocking dialog).
- **config-ui review (`config_ui_review.md`) — quality/dup/dead/correctness pass.** 8 finder angles → 1-vote verify.
  Found **5 confirmed + 2 plausible correctness bugs** (404 reload loop, stale-request overwrite, unreachable blocking
  dialog, wrong-key validation error, stale memo), **type-contract drift** in `types/api.ts` (CoreConfig/NLUConfig/
  VADConfig behind the backend — defeats the type-check half of `config-ui-stays-functional` while the editor keeps
  working off the backend schema), **6 duplications** (~500+ lines: apiClient CRUD quintet ×4, Templates/Prompts page
  clones, list/key/card editor primitives), **dead exports** (ESLint only flags unused *locals*), and efficiency +
  hardcoded-list/altitude smells. Baseline `npm run check`/`build` pass — the defects are exactly what those gates
  don't catch. Remediation filed: **BUG-8/9/10** (correctness) + **UI-11** (drift) / **UI-12** (dup) / **UI-13** (dead)
  / **UI-14** (efficiency+altitude), all `[deferred]`. No fixes applied (review → tasks, per `review-then-remediate`).
- **TEST-14 DONE — trace↔WAV unification (record once, test twice).** A golden audio trace already carries its captured
  audio (the bytes `--listen` plays), so a new `irene-replay-trace --extract-wav <file.wav>` decodes it to a standard
  WAV — one golden trace now serves both the offline replay tier AND the live WS suite, no re-recording with a mic.
  Pure trace→WAV transform (standalone CLI mode, no core/replay); writes at the captured rate/channels (Irene's 16 kHz
  mono PCM16 → directly usable as a fixture). Documented in `eval/README`. Gates: suite 1109 passed (+3 tests),
  pyright 0, import-linter 9/9. **Closes the trace-driven system-testing series** (TEST-11→12→13→14); no trace-playback
  TEST- tasks remain open.
- **TEST-13 DONE — failure-trace capture for the live WS suite (S2).** Two pieces: (D-6) when tracing is on, the
  `WorkflowManager` entry points stamp the trace `request_id` onto `result.metadata` — the `/ws/audio` response already
  spreads `result.metadata`, so each case correlates exactly to its saved `<request_id>.json` (no handler change,
  additive, config-ui N/A); (D-13) a new project-agnostic `eval_commons.failures` helper (eval-commons `e740c80`) reads
  the promptfoo results JSON and keeps only the FAILING cases' traces under `traces/failures/`, pruning the rest —
  reusable by wb-mqtt-bridge unchanged. Wired into `eval/Makefile`'s `ws` target behind `TRACE=1` and documented in
  `eval/README` (incl. the offline `--record-out`-on-mismatch tier, D-7, which already existed). A failed case is now
  replayable from the *actual* failing run (`irene-replay-trace --listen --step`). Gates: suite 1106 passed (+ 2
  workflow_manager tests; eval-commons +6), pyright 0, import-linter 9/9. Trace-playback wiring now leaves only
  **TEST-14** (trace↔WAV unification) open.
- **BUG-7 DONE — ru oblique-case numerals normalize to digits.** ovos (ru) reads only nominative numerals, so «одну
  секунду»/«двух минут»/«тридцати пяти» stayed as words and «тридцать одну» even broke to "30 одну". Fix at the
  normalizer altitude (`text_processing.py`): remap the oblique cardinals ovos misses → nominative before ovos (digit
  conversion incl. compounds then fires). Mapped only the forms ovos actually misses; excluded words that collide with
  non-numeric meanings so plain text is never mangled («о семью детях» stays). Verified «одну секунду» → "1 сек",
  «тридцать одну секунду» → "31 сек". Suite 1104 passed, pyright 0, import-linter 9/9. Normalizer-only. Surfaced as the
  BUG-6 bonus finding (had been parked on QUAL-35; resolved here instead).
- **BUG-6 DONE — the "unit story": timer-unit fix + consolidate 3 parsers to one + remove the dead DURATION stub.**
  "set a timer for one second" → "1 min" because the en `unit` param lacked `choice_surfaces` (ru had them) so the weak
  CHOICE extraction defaulted to "minutes", and the correct text fallback was bypassed once `duration` was extracted.
  Right altitude: one shared bilingual parser `irene/utils/units.py` (`TIME_UNITS` + `parse_duration`), made
  authoritative in the timer. Consolidated the 3 unconnected time-unit parsers (timer, `TemporalEntityResolver`,
  `QuantityEntityResolver`) to it. Removed `ParameterType.DURATION` (declared, never coerced, unused) across enum +
  hybrid matcher + contract JSON schema + config-ui (incl. regenerated gen types). Verified "one second" → "1 sec".
  Gates: suite 1103 passed, pyright 0, import-linter 9/9, 12/12 profiles, config-ui green. The general units layer
  (percent/°C) is filed onto **QUAL-35** to be designed *with* smart-home (units come from the bridge device catalog);
  ru «одну/одна» normalize gap noted there. Scoped time-only for now, per user.
- **BUG-4 DONE — per-language defaults + fire-and-forget completion language (all 3 sub-issues, right altitude).**
  Three related defects, one theme (per-language state not threaded to where messages render): (1) donation
  `default_value` flattened to ru → now assembled per-language (`ParameterSpec.default_value_by_language`), threaded via
  `Intent.language` (set in the orchestrator), resolved strictly by request language in `get_param`; (2) **fire-and-
  forget completion language** (the user's catch — a timer is F&F): capture the request language + the rendered
  completion message into the `ActionRecord`, replay at completion; the notification service stopped hardcoding English.
  Verified: en timer → "Timer set for 10 min. Message: Timer completed!" + the deferred completion fires "Timer
  completed!"; ru unchanged. (3) datetime en localization filled (`days_ordinal`/`hours`/`periods`/`special_hours`).
  Suite 1086 passed, pyright 0, import-linter 9/9, 12/12 profiles, config-ui green. The donation en alias/choice
  *enrichment* sweep (non-functional, respect the technical-identifier rule) split out as **BUG-5**.
- **BUG-3 DONE — English replies, at the right altitude: a TTS normalizer was corrupting NLU input.** Deeper analysis
  (per request, "not only timer related") found the en→ru reply was a *symptom of input corruption*: the `prepare`
  normalizer transliterates Latin→Cyrillic ("set a timer"→«сэт е таймё») and ran at the `asr_output` (pre-NLU) stage,
  so English never reached NLU as English → script detection saw Cyrillic → `ru` → every handler replied Russian.
  `prepare` is TTS-only (also spells symbols out), so the fix is to run it at `tts_input` only — schema default +
  `config-master` (the only config pinning it; the rest inherit the default; all 12 profiles validate). Plus: the
  detector's no-signal case now falls back to script (non-Cyrillic ⇒ English) instead of None→default; and the timer's
  own literals are localized (`_format_duration` units, message fallback). English now understood + replied correctly
  across handlers. Suite 1086 passed (2 old-behavior tests updated), pyright 0, import-linter 9/9. Residual noted: the
  timer donation's `message` default_value is Russian (a separate donation-localization concern).
- **BUG-1 DONE — spelled-out numbers now reach parameter extraction (general fix, ru + en).** Research (not just ru)
  found the codebase only ever did DIGITS→WORDS (synthesis) and every extractor matched `\d+` — so English ("ten
  minutes") was broken identically. Added `normalize_numbers_to_digits` (ovos `numbers_to_digits`, ru+en, idempotent,
  safe-degrade) and — after a good catch that a provider-local fix misses spaCy/LLM — applied it **once at the cascade
  entry** (`ContextAwareNLUProcessor.process_with_context`), so every recognizer + the spaCy donation patterns + (via
  normalized `raw_text`) handler text-fallbacks see digits. Also gave the timer's `_parse_timer_from_text` English
  units (it was ru-only). Verified ru/en spelled + compound + digit regression all set the timer; suite 1086 passed,
  pyright 0, import-linter 9/9, 10 new tests. Unblocks a natural-speech timer golden + the WS UX timer case.
- **TEST-12 DONE — config overrides (`--set`) + offline golden-trace replay surface; BUG-2 fixed, BUG-1 filed.**
  Trying to record a golden trace exposed that you couldn't override config settings without hand-editing files.
  Fixed: **`--set DOTTED.KEY=VALUE`** on the base runner (`config/manager.py apply_dotted_overrides`, applied
  pre-validation so Pydantic coerces+validates; strict — an explicit `--set` never silently falls back; 8 tests).
  Built the **golden-trace surface**: `eval/trace.promptfooconfig.yaml` drives `irene-replay-trace` through the
  existing `cli_provider` (assert `exit_code === 0`), `make replay`/`replay-judge`, a committed seed golden
  (`timer_set_10min.json`) that replays green under the WB7 config, `eval/traces/README.md`, the 4th surface in
  `howto-new-test.md`. Also made `diff_output` normalize volatile timestamps (a timer's `started_at`) so deterministic
  handlers stay green goldens. Two bugs surfaced and a new **`BUG` workstream** filed:
  - **BUG-2 (fixed)** — stale `TTS requires Audio` check in `voice_assistant.py` (a drifted duplicate of the canonical
    `CoreConfig` validator, missing the `audio_playback_enabled` condition) rejected the valid WB7 satellite config in
    any runner that didn't force audio on. It was masked by `webapi_runner` hard-setting `components.audio`. Removed the
    duplicate; suite 1074 passed; the WB7 golden replays green with no workaround.
  - **BUG-1 (open)** — spelled-out Russian numerals don't set a timer («десять минут» → no timer; «10 минут» works);
    the golden uses the digit form pending the fix.
  (Reverted the reactive `--set` I'd added to the replay tool — BUG-2's fix made the local-replay workaround unneeded.)
- **TEST-11 DONE (design) — trace-driven system testing → `docs/design/trace_system_testing.md`.** Uses the shipped
  trace record/replay (ARCH-19) two ways: an **offline deterministic regression surface** (committed golden traces
  replayed via `irene-replay-trace --local` through the existing `cli_provider`, asserting `exit_code === 0`; tiered
  `trace-system` vs DeepSeek-judged `trace-ux`) and **failure-trace capture** (always-trace + keep-on-failure for the
  live WS suite via a small `request_id`-in-metadata enabler; `--record-out`-on-mismatch offline) so a failed case is
  replayable (`--listen`/`--step`). No new `eval-commons` code for the core surface. Design done ≠ shipped → filed
  **TEST-12** (offline surface), **TEST-13** (failure-tracing + SUT enabler), **TEST-14** (trace↔WAV, phase 2).
  **Resolved the design's three open questions** (now D-12/13/14; design AGREED): D-12 — `trace-system` is not
  release-gating yet but promotes on a trigger (covers the core paths + 2 consecutive green CI runs); D-13 — the
  keep-on-failure post-step is a generic `eval-commons` helper (reusable by the bridge), not a per-project step; D-14 —
  seed a small deterministic golden set now and grow it from real failures (failure-tracing feeds the golden set).
- **TEST-10 DONE — WS audio fixtures are now versioned.** A blanket `*.wav` ignore had accidentally swept the eval
  fixtures in, making the WS suite un-runnable in CI (no mic) and non-reproducible (re-record → different WER). Carved
  `!eval/fixtures/*.wav` out of the ignore; other `*.wav` stay ignored. Fixtures are test inputs, not stray audio.
  `fixtures/README.md` updated. The deeper "golden traces as reviewable regression inputs" direction is in the
  trace-system-testing design.
- **DOC-9 DONE — user-facing eval guide.** Added `docs/guides/howto-new-test.md` (+ decision diagram
  `howto-test.dot/png`) in the established `howto-*` voice: pick a surface (CLI contract / WS system / WS UX-judged),
  author a case in each, record the fixture (`make record`), keep cases endpoint-agnostic (TARGET/CONFIG). Wired into
  the howto index (`CONTRIBUTING.md` "Add a test" + the top-level `README` pointer, beside add-an-intent/model/language)
  and cross-linked from `eval/README.md` as the walkthrough to its reference. Closes the "how do I add a test?" gap
  surfaced once the recorder made the WS suite actually authorable.
- **TEST-9 DONE — voice-fixture recorder wired into `eval/` (W6).** The recorder itself (design + W1–W5) was built and
  pushed in the sibling **eval-commons** repo (`eval-fixture-record`: mic capture → 16 kHz/mono/PCM16, worklist derived
  from the promptfoo YAML, interactive keep/redo); it lives there because eval-commons is the shared lower layer and
  must not import a consumer's audio stack (cycle). This repo's W6 wiring: `make record`/`record-list`/`record-devices`/
  `setup-record`; `profiles/recording.env.example` (real file git-ignored); `reference` added to the `light_unreachable`
  judge case so the recorder has a script (§5 decision); `fixtures/README.md` + `eval/README.md` repointed at
  `make record`. Verified end-to-end (`record-list` derives both fixtures, console script resolves, `make cli` 5/5).
  Unblocks the WS suite's fixture gap — recording the WAVs is now a clean manual step. eval-commons has no ledger; its
  side is tracked in its design doc §13 + commit `965153c`.
- **API execution-result contract review → QUAL-54 (done) + QUAL-55 (filed).** Surfaced while wiring the `eval/` WS
  suite: the `ws_audio_provider` reads `metadata.intent_name`, which `/ws/audio` never emits. Reviewed the execution
  surfaces and found a **family** of inconsistencies (no shared result serializer) — captured in
  `docs/review/api_result_contract_review.md` (F1 reply field `response` vs `text`; F2 3-way intent split; F3 one
  response model, two metadata payloads; F4 `confidence` placement; F5 internal `intent_name` read always `None`).
  **QUAL-54 (targeted, done):** `/ws/audio` now surfaces `intent_name` (remapped from `original_intent`) at both send
  sites + `workflow_manager` pipeline events read `original_intent` (fixing the live `None`). `test_pipeline_events`'s
  fake used the wrong key (`intent_name`), masking the bug — corrected to `original_intent`, now a faithful regression.
  Full suite 1066 passed, pyright 0, import-linter 9/9. **QUAL-55 (open):** one canonical serializer across all five
  surfaces (retires F1/F3/F4 + rest of F2; `config-ui` co-change). Unblocks the eval WS intent case.
- **UI-10 DONE — config-ui major dependency upgrades; all 8 Dependabot alerts cleared.** The 6 the housekeeping pass
  couldn't touch needed breaking majors outside the declared ranges, so they were a deliberate version decision (filed
  as UI-10, done same session): `vite ^5`→`^8.1.0` (+ `@vitejs/plugin-react`→`^6`; vite 8 = rolldown bundler) cleared
  the 3 vite advisories + esbuild; `react-syntax-highlighter ^15`→`^16` cleared prismjs (the only runtime one — `Prism`
  API unchanged); `@typescript-eslint ^6`→`^8` (eslint kept at 8.57 — stayed on eslintrc, no flat-config migration)
  cleared the minimatch ReDoS. ts-eslint 8's stricter type-checked config surfaced 6 lint errors (5 auto-fixed, 1
  optional-catch). `npm run check` + `build` + vitest 40/40 green; `npm audit` → 0 vulnerabilities. Upgraded
  incrementally (gate after each major) so breakage stayed isolated.
- **config-ui dependency housekeeping — lockfile-only, no ledger ID** (per the `every-task-in-the-ledger`
  carve-out). `npm audit fix` lifted `@babel/core`→7.29.7 and `js-yaml`→4.2.0 in `config-ui/package-lock.json`;
  `package.json` intent unchanged, `npm run check && npm run build` green. Cleared 2 of 8 Dependabot alerts. The
  other 6 need **breaking major upgrades outside the declared ranges** — `vite ^5`→6/8 (3 vite alerts + esbuild),
  `react-syntax-highlighter ^15`→16 (prismjs), `@typescript-eslint ^6`→8 (minimatch) — i.e. deliberate version
  decisions, not housekeeping; to be carried as a ledger task, not auto-applied.
- **Work-process redesign: ledger split + journal rotation (size control).** The ledger and journal had grown to
  ~71k / ~88k tokens (~159k combined; 106 of 127 ledger tasks done, 264 journal entries), past the point where the
  harness keeps them resident — every task that obeys `read-at-start-record-at-completion`/`task-start-reconciliation` was paying to load mostly-closed history.
  Completed work is reference-by-ID, not working-set, so it can be archived without losing the trail. Changes:
  - **`one-active-journal` amended** — "one journal" → "one *active* journal + frozen dated archives." The old wording ("no
    dated journals anywhere else") forbade the fix, though its real target is *drift* (two competing **live** logs).
    Reworded to permit append-only, frozen, greppable archives under `docs/archive/journal/` outside the default-read
    path, with a discoverability pointer at the top of the active journal.
  - **`single-task-ledger` extended** — the ledger now spans two files: active `RELEASE_PLAN.md` (open + paused/partial) +
    frozen `RELEASE_PLAN_DONE.md` (completed `[x]`, by workstream). One ledger, every ID in exactly one file; on
    completion a task **moves** active → done. `scripts/check_scope.py` now reads both for declarations (else
    references to completed tasks read as orphans) — verified 0 orphans / 0 dead links after the split.
  - **Split executed:** 106 completed tasks moved to `RELEASE_PLAN_DONE.md`; active ledger 71k → ~10k tokens.
  - **First journal rotation:** sections dated 2026-05-31 … 2026-06-14 frozen into
    `docs/archive/journal/pre-2026-06-15.md`; active journal keeps 2026-06-15 onward, 88k → ~23k tokens.
  - **Invariants relocated to `CLAUDE.md` + numbering retired.** All 10 invariants moved to `CLAUDE.md` →
    "Development process — invariants" (single source of truth, always in context = always enforced); the ledger's
    Invariants section is now just a pointer. To kill drift permanently, invariants are referenced by **stable name**
    (slug: `work-on-main`, `single-task-ledger`, `task-start-reconciliation`, …), **not number** — names survive
    add/remove/reorder so references never break. The ~134 `#N` refs in the frozen archives + review docs are left
    intact and resolve via a one-time number→name **legend** in `CLAUDE.md`; the 27 live refs in the active
    ledger/journal were converted to slugs. Net default-read working set: ~159k → ~33k tokens.
  - **Three development-process invariants added** (numbering retired, so no renumbering): `every-task-in-the-ledger`
    (file every task before working it, regardless of source — chat / GitHub issue / code-review finding),
    `design-then-implement` (a feature/redesign task delivers a **design doc**; implementation is filed as follow-up
    tasks on completion), `review-then-remediate` (a review — chat-requested or via `/code-review` — is a task that
    delivers a **review doc**; findings are filed as fresh tasks). Formalizes the intake + design/review pipelines the
    repo already followed informally.
  - **Journal rotation trigger defined** in `one-active-journal` (was permissive-but-undated): at each gate, if the
    active journal exceeds ~1500 lines / ~40k tokens, freeze the oldest whole dated sections into the newest archive
    until back under ~1000 lines / ~25k tokens. Closes the only "when" gap — task-moves were already per-completion.
  - **`user-facing-docs-are-done` scope widened** to add `docs/QUICKSTART.md` (always) + non-root `README*` (e.g.
    `eval/README.md`) — the latter **only when the task touches that README's directory/subsystem** (locality gate, so
    it isn't a "re-audit every README" burden). Closes the scope gaps surfaced when reviewing the invariant.
  - **`every-task-in-the-ledger` carve-out for routine dependency housekeeping** (surfaced while porting the
    invariants to the sister project `wb-mqtt-bridge`): a lockfile-only bump that doesn't change `pyproject.toml` /
    `config-ui/package.json` intent (`npm audit fix`, `uv lock` refresh, Dependabot lock refresh) needs no ledger ID —
    just a journal line on completion; deliberate version decisions still need a task. Keeps the two repos' invariant
    sets in sync (same rule, two dialects).
