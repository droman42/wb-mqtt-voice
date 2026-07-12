# Problem reporting end-to-end («сообщи о проблеме»)

**Status: AGREED 2026-07-06 (interactive design session, ARCH-30). D-1..D-10 all user-approved
(P-1..P-4 accepted as proposed and renumbered D-7..D-10).**

> **Shared truth moved (HK-3/PROD-6, 2026-07-11).** The cross-repo parts of this design are now
> commons-owned: the normative spec is `process/problem-reports.md` in `../locveil-commons`
> (semantics, triage judgment, leak fence, retention/governance), and the wire-visible surface is
> its versioned **machine core** (`report-protocol-vN` tags), pinned here at
> `contracts/pins/report-protocol/report-protocol.json` and conformance-tested in
> `irene/tests/test_report_protocol_conformance.py`. This document remains the voice-side
> implementation design and the frozen ARCH-30 decision record (D-numbers below are referenced
> across repos); where a section duplicates the shared truth, the commons spec wins — the shared
> sections below (§5, §7) have been reduced to pointers.

A user tells Irene something is wrong; Irene collects a support bundle and files a ticket; a
GitHub-hosted Claude triages it — fixing, delegating, or escalating; the owner reviews fixes and
escalations one-by-one with the local Claude. The reporter never needs a GitHub account, an email,
or any identity at all (a user registry is a later release).

## 1. Agreed decisions

- **D-1 — Backend topology: a private triage home.** One private repo, **`wb-user-reports`**
  _(renamed/moved to **`locveil/locveil-reports`** 2026-07-11 with the Locveil productization;
  the old name redirects — mentions of `wb-user-reports` below refer to the same repo)_,
  holds BOTH the tickets (GitHub issues) and the raw bundles. The Claude triage workflow lives in
  this repo — not in the public code repos. Rationale: both code repos are public, and bundles
  narrate the household (rooms, devices, daily rhythms, free-form speech); redacting free-form
  logs for public posting is a losing game. Fix PRs still land on the public code repos.
- **D-2 — One Claude, two lenses — handover by label, not transfer.** "Voice Claude" and "bridge
  Claude" are process *roles*, not separate installations. A ticket carries `lens:voice` or
  `lens:bridge`; the triage workflow checks out the corresponding public codebase and applies that
  lens's process file. Voice→bridge delegation = flip the label + post a structured handover
  comment (schema: the machine core's `handover_comment`) on the SAME ticket — full history
  preserved, no cross-repo copy.
- **D-3 — Shared intake.** The bridge UI's future "Report a problem" button files into the same
  repo with the same envelope (§5), `lens:bridge` set at filing. Its payload specifics are the
  bridge's own design session (VWB filing at ARCH-30 completion).
- **D-4 — Bundle retention: 30 days.** A scheduled workflow in `wb-user-reports` prunes bundle
  files older than 30 days; issues and their distilled inline summaries persist. Privacy decays by
  default; triage history does not.
- **D-5 — Verbatim-capture window: configurable, default 90 s.** After Irene asks for the
  description, the next utterance within the window is consumed RAW (§3). On expiry the report
  dies unfiled and commands behave normally. No re-prompt loops.
- **D-6 — No raw audio in v1.** The failing utterance's audio would be diagnostic gold for ASR
  bugs, but it is a voice recording leaving the house — explicitly a later, opt-in feature.

## 2. The dialog (voice side)

New handler + intent **`report.problem`** (own small handler — own donation, templates, wiring;
phrases: «сообщи о проблеме», «у меня проблема», «что-то не работает», «пожаловаться» — routing
checked against the QUAL-64 suite so it collides with nothing).

Turn 1 — `report.problem` fires → Irene answers from a template: «Опишите проблему своими
словами» — and arms a **verbatim-capture** state: the existing pending-clarification slot
(QUAL-30/31) extended with `mode: "verbatim"` and `expires_at`.

Turn 2 — the workflow checks the pending state BEFORE the QUAL-44 arbitration: in verbatim mode
the utterance is **not** re-run through NLU as a potential command — a description like «свет в
спальне не включается» must not be hijacked into `smart_home.power_on` and executed. The raw text
becomes the report's `description`; the bundle is assembled and handed to the delivery path (§6);
Irene confirms: «Отчёт отправлен, спасибо» (or the offline variant, §6).

Escapes and expiry:
- **Cancel words** («отмена», «не важно», «забудь»; en: "cancel", "never mind") end the capture
  with a polite acknowledgement, nothing filed.
- **TTL expiry** (D-5): state cleared silently; the next utterance is an ordinary command. No
  nagging — if the user still cares, they say «сообщи о проблеме» again.
- The dialog is fully template-driven (ru + en; QUAL-71 discipline — no hardcoded strings).

## 3. What the bundle contains

Assembled by a new `ReportBundleCollector` (core service):

| Item | Source | Notes |
|---|---|---|
| user free text | verbatim capture | also inlined into the issue body |
| conversation window | `UnifiedConversationContext.conversation_history` | last 10 turns — NOT just the previous utterance: users retry before complaining, F&F failures surface late, output-side failures leave a clean last turn |
| recent + failed action records | client registry | the F&F/durable view of "what was running" |
| request traces | **new: rolling in-memory ring buffer, last 5 requests** | trace *persistence* is off by default in deployments; the ring is always on, dumped only into bundles (memory cost ≈ a few hundred KB) |
| NLU cascade verdicts | ring-buffer traces | which provider won, at what confidence — half of any misroute diagnosis |
| today's log | `logs/irene.log` + same-day rotated files | gzipped (~10:1); text logs are single-digit MB |
| config | the loaded config file, **redaction pass** (§4) | |
| metadata | version, git commit, config profile, platform/arch, **pinned catalog version**, ASR/TTS/NLU providers, session language, room/client id, timestamp, `smart_home_involved` + `bridge_evidence` status (ARCH-34) | catalog version instantly tells the bridge lens whether the contract is stale |
| bridge evidence (ARCH-34) | `GET /reports/evidence` on the bridge (contract v1.4, B-11), fetched at filing time whenever `[outputs.bridge]` is wired | the bridge's own redacted `EvidenceEnvelope` (dispatch ring, MQTT window, live states, state diffs — the contract the bridge owns, pinned in locveil-commons) under `bridge/evidence.json`; any fetch failure is filed verbatim as `bridge/unavailable.json` — **unreachable IS evidence**, never fatal; 429 (the endpoint's gzip rate guard) handled the same way. Not gated on a smart-home heuristic — over-attaching into the same private repo is free |

**§4 Redaction:** applied to config AND log excerpts before packaging: values of any key matching
`*_API_KEY|token|password|secret|credential` (BUG-20 family), `Authorization:` headers, and
`.env`-style assignments quoted in logs. LAN hostnames/room names stay — the repo is private
(D-1); the *leak fence* (commons spec §3) guards the public boundary instead.

## 5. The envelope (shared voice/bridge intake format)

**Owned by the shared truth.** Filing semantics (one report = one issue + one bundle commit) are
the commons spec §3; the wire shape — labels at filing, per-source title prefixes, the bundle path
template, the envelope's required fields — is the machine core, pinned at
`contracts/pins/report-protocol/report-protocol.json` and asserted against `build_envelope`'s output by
`irene/tests/test_report_protocol_conformance.py`. Voice-side implementation notes only:

- The single writer seam is `build_envelope` in `irene/core/report_service.py`; the issue body it
  composes is the distilled summary, so triage usually needn't open the tarball.
- The bundle commit goes through the contents API (base64; a release asset if ever >25 MB).

## 6. Delivery from the device

- New port **`ReportSinkPort`** + adapter **`GitHubReportSink`** (issues + contents API). Config
  `[reports]`: `enabled`, `repo`, `token_env` (fine-grained PAT: issues:write + contents:write on
  `wb-user-reports` ONLY), `capture_ttl_seconds = 90`, rate limits (below).
- **Offline/failure path = the ARCH-27 durable substrate, used as designed**: the bundle spools to
  `<assets_root>/state/reports/` and submission is launched `durable=True` with re-arm — retries
  survive restarts. Irene says so honestly: «Сейчас нет связи — отправлю отчёт, как только
  появится».
- **D-7 — client-side rate limit (accepted)**: max 3 reports/hour, 10/day per device; the 4th gets
  «Я уже отправила несколько отчётов — дайте мне немного времени». Guards against ASR misfires
  and frustration-mashing.
- **D-8 — no client-side dedup (accepted).** Volume is household-scale; dedup is the triage
  Claude's job (its process file: search open tickets first; a duplicate becomes a comment on the
  existing ticket, not a new fix).

## 7. Triage choreography (the reports repo)

**Owned by the shared truth — this section's ARCH-30 body was lifted out 2026-07-11 (ARCH-46;
consult the commons spec, not this doc's git history).** The normative semantics — the workflow
trigger and loop safety, the triage outcomes, handover-by-label, the ping-pong guard, the terminal
state, the leak fence, and the one-strong-model policy — live in
`../locveil-commons/process/problem-reports.md` §3–§5; the enums behind them (state buckets,
transitions, `ping_pong_max`, the handover-comment header + fields) are the machine core's,
pinned at `contracts/pins/report-protocol/report-protocol.json`. Per-lens judgment (how to reproduce against THIS
repo, what to rule out before a handover) is maintained in the co-owned lens file —
`.github/claude/lens-voice.md` in the reports repo — not here.

Voice-side remainder (decision record, referenced by the commons spec):

- **D-11 — model-policy rationale.** The policy itself (one strong model, pinned in ONE place —
  the workflow env) is the commons spec's; the reasoning was decided here: report volume is
  household-scale, so there is nothing to optimize by tiering models — while the code path
  performs UNATTENDED root-cause analysis and authors PRs, exactly the work where capability
  dominates cost. Subscription note: action runs share the owner's plan usage with local sessions.
- **Outcome 3a (later):** when identity channels exist (§11), the "unclear reporter" outcome
  gains a direct "ask the reporter" variant instead of always escalating to the owner.

## 8. The owner's review loop (local Claude, both code repos)

- New user-invocable skill **`/inbox`** in `locveil-voice` and `locveil-bridge`: lists (a) open
  fix PRs on that repo, (b) `needs-owner` tickets in `wb-user-reports` for that repo's lens — then
  walks them ONE BY ONE interactively (approve/revise the drafted reply, review the PR diff,
  merge/close decisions stay with the owner).
- One line in each repo's CLAUDE.md: at session start, mention (not auto-run) when `/inbox` has
  items — the owner decides when to enter review mode.

## 9. Config & secrets summary

| Where | What |
|---|---|
| device (`[reports]` in config + env) | fine-grained PAT → `wb-user-reports` only |
| `wb-user-reports` secrets | Claude OAuth token (owner's subscription) |
| Claude GitHub App installs | reports + voice + bridge repos |
| public repos | nothing new |

## 10. Implementation plan (tasks to file at design completion)

1. Verbatim-capture mode on the pending-clarification state + workflow pre-check (before QUAL-44).
2. `report` handler + donation + templates (ru/en) + routing regression cases.
3. Trace ring buffer (last 5 requests, always on).
4. `ReportBundleCollector` + redaction pass + envelope builder.
5. `ReportSinkPort` + `GitHubReportSink` + `[reports]` config + durable spool/retry + rate limit.
6. `wb-user-reports` repo bootstrap: labels, triage workflow, two lens process files, retention
   pruning workflow, Claude app installs + secrets (owner actions listed step-by-step).
7. `/inbox` skill (voice repo) + CLAUDE.md line.
8. Cross-repo filings (uncommitted, per `cross-repo-source-of-truth`): bridge `/inbox` skill +
   CLAUDE.md line; bridge UI "Report a problem" button (same envelope, `lens:bridge`).
9. Eval: the dialog flow (arm → verbatim → cancel/TTL) as unit tests; a mock-sink e2e for the
   bundle path.

## 11. Later (explicitly out of v1)

User registry + direct-reply channels (mail/Telegram/GitHub identity); raw-audio opt-in; curated
public issues for confirmed OSS-relevant bugs; auto-close policies; bridge-side bundle specifics.

**D-9 (accepted)**: the `report.problem` phrases as authored in §2 (native-speaker pass done at
the AGREED sign-off).
**D-10 (accepted)**: ring buffer depth 5 and the D-7 rate-limit numbers are tunable defaults in
`[reports]`.
