# Irene — Release Plan

The single active tracker for the road to release. Supersedes the legacy `docs/TODO.md` +
`docs/TODO/TODO0x` (refactor-era, mostly complete — to be archived under DOC-2).

**Target:** milestone — **scope-complete** (release when every `[release]` task is `[x]`; no calendar date; the gate
is `scripts/scope_guard.py --config .scope-guard.toml` clean) · **Status:** active · **Version:** 0.5.0 (REL-4; was `15.0.0`)

> **Completed tasks** (`[x]`) live in the frozen archive **[`RELEASE_PLAN_DONE.md`](./RELEASE_PLAN_DONE.md)** —
> split out to keep this file the *active* working set (open tasks + structure). IDs are preserved there; grep it
> when a reference or reconciliation (`task-start-reconciliation`) needs the detail of a closed task.

## Definition of release (exit criteria) — **SIGNED OFF 2026-07-04 (REL-1, interactive)**

> **Scope gate (`single-task-ledger`):** release ships only when **every task tagged `[release]` is `[x]`**. Tasks default to
> `[release]` unless explicitly marked `[deferred]` (post-release); as of the sign-off every open task carries an
> **explicit** tag. Run `scripts/scope_guard.py --config .scope-guard.toml` at each gate to prove nothing has
> drifted (orphan findings, dead links, contradictory status, missing tags, watermarks — the vendored commons
> scope-guard, BUILD-30). The exit criteria below are the human-readable summary of that gate.
>
> **The release artifact** = a version tag **+ the first real publish dispatch to GHCR** (backend images
> `standalone-x86_64` / `embedded-aarch64` / `embedded-armv7`, RU at minimum, + the config-ui image), each
> boot-validated where the hardware allows (x86_64 locally; ARM boot rides ARCH-25) — owned by **BUILD-11** + **REL-3**.

- [x] Clean `uv sync` (CI: `uv lock --check` + install); boots in CLI **and** WebAPI modes on x86_64
      (smoke e2e, BUG-20-hermetic). _Docker-image boot ✓ BUILD-11 (2026-07-06): all 6 backend images + UI
      published to GHCR, `standalone-x86_64` boot-validated locally (health + live command + first-boot model
      downloads into the mounted volume); ARM on-device boot rides ARCH-25._
- [x] CI green — BUILD-9's gated `ci.yml` (changes-filter, py-dev-gates, config-validator, build-analyzer,
      D-6 no-models guards), green on every push since 2026-07-02.
- [x] No phantom-reference / runtime `NameError` bugs; **pyright (standard) = 0 errors, empty suppression list**
      (QUAL-4 ratchet complete; CI-enforced — the "agreed threshold" is 0).
- [x] Import layering honored — **10 import-linter contracts** (hexagon gate incl. ARCH-28 durable-store seam),
      CI-enforced.
- [x] Test suite green — **the three named nets**: unit suite (1173 pass) + smoke e2e (6, offline-hermetic) +
      eval `make cli`. _No coverage-% criterion (decided 2026-07-04): the layered nets are the safety story._
- [x] Models point to current versions with live download URLs (ASSET-2 sweep; ASSET-4 VAD + ASSET-5 wake-word
      re-homed through the AssetManager with live-download verification 2026-07-04).
- [x] Docs accurate at the release version; quickstart works end-to-end — ✓ REL-2 (2026-07-06):
      `configs/config-example.toml` (curated first-run starter, boots + answers live), friendly no-config
      runner failure (acceptance driven by a live first-touch transcript), README status + first-run
      pointer, QUICKSTART finalized (example-first, smart-home in scope, GHCR images noted).
- [x] **`config-ui` builds + type-checks clean** (CI-gated) **and functional against the release backend** —
      manual pass PASSED 2026-07-06 (REL-3): sections/donations/templates/localizations/monitoring all live on the
      running backend; the pass FOUND + fixed BUG-29 (default port 6000 → 8080, browser-blocked X11).

---

## Invariants (apply to EVERY task)

**The invariants now live in [`CLAUDE.md`](../CLAUDE.md) → “Development process — invariants”** (single source
of truth, always in context). They are referenced by **name** (stable slug), not number — e.g.
`single-task-ledger`, `task-start-reconciliation`, `read-at-start-record-at-completion`. Frozen archives and
review docs still cite the old `#N`; the number→name legend is in `CLAUDE.md`.

---

## Review documents (findings index)

Living findings behind the tasks (`read-at-start-record-at-completion`). `[x]` = exists; others are produced by their review task.

| Doc (`docs/review/` unless noted) | Covers | Backs |
|---|---|---|
| `docs/design/build_release_process.md` `[x]` (AGREED 2026-07-02, interactive) | BUILD-8 — bridge-aligned build/release: one gated `ci.yml` (changes-filter, CI ledger-guard, py-dev-gates), manual dispatch targets×languages matrix (RU unsuffixed / EN `-en`), config-ui nginx image (multi-arch, not on controller yet), `ops/` deploy-by-pull + git-pull assets sync, models-not-baked audit + guards | BUILD-8 ✓ → BUILD-9, BUILD-10 |
| `docs/design/durable_actions.md` `[x]` (AGREED 2026-07-02, interactive) | ARCH-27 — durable-action substrate: opt-in `durable=` launches, atomic-JSON store behind a port, re-arm-by-relaunch reconciler, fire-with-apology ≤1h grace, failures announced by default, handler-declared redelivery, retry machinery cut, minimal read-only actions API, handler-authoring rules (§3) → howto-new-intent + CLAUDE.md invariant | ARCH-27 ✓ → ARCH-28, QUAL-61 |
| `faf_durable_execution_review.md` `[x]` (2026-07-02) | QUAL-56 — F&F vs the durable-execution reference model (8 dimensions, all zero by design; delivery = at-most-once with 5 drop points; retry machinery dead) + comparative `wb-mqtt-bridge` persistence analysis (patterns to borrow + persist-without-restore / stale-intent pitfalls) | QUAL-56 ✓, ARCH-27 ✓, BUG-19 ✓, QUAL-61 ✓, VWB-18 ✓ (bridge — accepted, verified + fixed 2026-07-02, incl. one aggravation found at intake) |
| `arch_memory_review_2026-07-02.md` `[x]` (2026-07-02) | QUAL-57 — general architecture assessment (SOTA gaps A1–A7) + memory-overconsumption audit (M1–M8, ranked) + F&F QUAL-8 re-verification (all 10 resolved) + `create_task` census + verified-fine list | QUAL-57 ✓, BUG-16/17/18, QUAL-58/59, QUAL-56 (premise confirmed) |
| `phase0_static_baseline.md` `[x]` | static baseline: phantom refs, hidden type debt, dead code, layering | QUAL-1/2 ✓, QUAL-3/4/5/6, TEST-1 |
| `phase1_architecture_map.md` `[x]` | architecture map, doc-harmonization audit, hexagon target | ARCH-0 ✓, ARCH-1..8, ARCH-11/12, DOC-4/5✓/5b/6✓ |
| `fire_and_forget_review.md` `[x]` | F&F lifecycle + gap analysis (6 legacy issues re-validated) | QUAL-8 ✓, QUAL-9, TEST-3, DOC-4 |
| `parameter_extraction_review.md` `[x]` | text→parameters review + gaps | QUAL-10 ✓, QUAL-11, QUAL-35, TEST-4, DOC-7, UI-1/2/3, QUAL-22 |
| `text_processing_review.md` `[x]` | text-processor subsystem review + LLM-text-proc question | QUAL-12 ✓, QUAL-13, TEST-5 |
| `llm_usage_review.md` `[x]` | LLM usage + offline-first + NLU-LLM decision | QUAL-14 ✓, QUAL-15, QUAL-16 |
| `dataflow_review.md` `[x]` | full input→action flow map + defect hunt (~9 P0/~20 P1; gates Gate 2) | QUAL-25 ✓, QUAL-26 ✓, DOC-8 |
| `dataflow_reconciliation.md` `[x]` | QUAL-26 review-of-reviews — 10 intended-vs-today decisions + Gate 2 framing | QUAL-26 ✓ → QUAL-27..31, QUAL-9/11/13/15/16/22/23, ARCH-6/7, DOC-7/8 |
| `qual29_choices_decisions.md` | QUAL-29 interactive CHOICE canonical-model decisions (5 cases + parallel-set map + build plan) | QUAL-29 |
| `declared_param_audit.md` | audit: 19 declared-but-unconsumed donation params across 11 handlers (Bucket A dead / B bypassed) | QUAL-34, QUAL-11 |
| `streaming_api_review.md` `[x]` | AsyncAPI streaming-API tooling — Hybrid: replace renderer / keep+improve generator | QUAL-17 ✓, QUAL-18 |
| `esp32_wakeword_review.md` `[x]` | ESP32 + wakeword keep/fix/cut + microWakeWord upstream study | QUAL-19 ✓, QUAL-20 ✓ |
| `docker_build_review.md` `[x]` | Docker/build verification (entry-point renames, armv7 base, build-analyzer drift) | BUILD-5, BUILD-3 |
| `docs/design/wakeword_models.md` `[x]` (AGREED 2026-07-04, interactive) | ARCH-29 — server-side wake-word model acquisition: v2 two-file packs (manifest + sibling tflite), 4-rung resolution (local path → wheel built-ins → v2 manifest URL → released catalog starting with `irina`@HF), AssetManager multi-file `files:` support, trigger layer stays semantics-free (word→room deferred to ARCH-22/QUAL-35), roster «Ирина»→«Валера»/«Наташа» («Борис» dropped) | ARCH-29 ✓ → ASSET-5 |
| `docs/design/problem_reports.md` `[x]` (AGREED 2026-07-06, interactive) | ARCH-30 — problem reporting end-to-end: private triage home `wb-user-reports` (tickets + bundles; both code repos are public), one-Claude-two-lenses with handover-by-label + ping-pong guard, verbatim-capture dialog (pre-QUAL-44, TTL 90s, cancel words), bundle (last-10 turns + action records + 5-trace ring + day log + redacted config + catalog version), ARCH-27 durable spool, D-7 rate limits, leak fence, reply-in-reporter's-language, D-11 model policy (`claude-fable-5` pinned) | ARCH-30 ✓ → ARCH-31/32/33, BUILD-12, VWB-25 |
| `docs/design/python_satellite.md` `[x]` (AGREED 2026-07-06, interactive) | ARCH-35 — python satellite (`irene-satellite`): first-class room node + the ARCH-25 test client; both /ws/audio modes (default single), wake-on + `--no-wake`, `[satellite]`+`[satellite.tls]` config, §3/§4 = the wire contract's single written truth (ESP32 implements the same doc), device-side CSR-approval dance + mTLS wss through nginx Plane B (S-5), S-6 credentials location, S-7 hermetic TLS e2e, S-8 Pi image deferred, S-9 loopback e2e | ARCH-35 ✓ → ARCH-36, BUILD-13 |
| `docs/design/mqtt_integration.md` `[x]` (DONE 2026-06-06; bridge contract AGREED) | smart-home integration — bridge is the single device authority, Irene speaks canonical commands | ARCH-7/8, ARCH-26 |
| `docs/design/ws_esp32_transport.md` `[x]` | WS streaming-input driving adapter + ESP32 satellite transport | ARCH-6 |
| `docs/design/onnx_inference_layer.md` `[x]` (complete 2026-06-04; ASR/platform/build + VAD/wake-word all resolved) | shared sherpa-onnx inference layer — ASR-centric; WB7 armv7 feasibility proven on hardware | ARCH-9/10 |
| `docs/design/io_architecture.md` (DRAFT 2026-06-07) | symmetric configurable hexagonal I/O — format-vs-input, OutputPort + modality matrix, daemon multiplexing, event-bus delivery+observation, F&F via OutputManager, runners-as-presets | ARCH-14/15 |
| `docs/design/audio_pipeline.md` `[x]` (2026-06-10) | audio I/O negotiation+transformation seam (input twin of ARCH-15) — VAD provider family, canonical transform-once + derived/fatal negotiation, pre-roll contract, AudioTranscoder/VoiceSegmenter/AudioNegotiator, symmetric in+out, traced | ARCH-17 ✓, ARCH-18 |
| `docs/design/trace_persistence.md` (COMPLETE 2026-06-14; D-1..D-18; **ARCH-19 shipped slices 1–6**) | persist utterance traces to self-contained JSON (base64 audio) for listen + pipeline replay (regression + VAD tuning) — capture levels, `current_trace` contextvar, TraceLogger, handler `trace_event`, seed+diff replay | ARCH-19 ✓ |
| `docs/design/trace_system_testing.md` `[x]` (AGREED 2026-06-27; D-1..D-14) | trace-driven system testing — offline golden-trace replay surface (deterministic regression via `cli_provider`, `trace-system`/`trace-ux` tiers) + failure-trace capture (always-trace keep-on-failure live; `--record-out` offline) + trace↔WAV unification | TEST-11 ✓ → TEST-12/13/14 |
| `docs/design/streaming_tts.md` (DRAFT 2026-06-14) | producer twin of ARCH-20 — streaming TTS synthesis + output-seam delivery unification: `synthesize_to_stream` port + base simulation/native overrides, remote `AudioSink` OutputPort, collapse the 3 fragmented playout paths, retire PR-4's parse_wav bridge | ARCH-21 |
| `docs/design/esp32_satellite.md` (DRAFT 2026-06-14) | **consolidated** ESP32 voice-satellite design — supersedes `ws_esp32_transport.md`, folds `esp32_wakeword_review.md` + `onnx §10/11` + ARCH-21; D-1..D-18 (device shape, wire protocol in+reply, micro stack, models/push, identity/multi-room, provisioning/CSR/OTA); backend plan §12 | ARCH-22 |
| `docs/design/torch_free_armv7_voice.md` `[x]` (2026-06-15; research/analysis, no code) | torch-free inference for the armv7 voice stack — canonical three-image matrix (§5): torch contained to the x86_64 standalone image; both ARM satellites (armv7 WB7 + aarch64 WB8/Pi) are torch-free sherpa-onnx; Whisper→sherpa-Whisper, Silero TTS→Piper/RUAccent seams | ARCH-24 ✓ |
| `docs/design/multilingual_deployment.md` `[x]` (2026-07-01; design, no code) | real English deployment across all 3 Docker arches + English eval — slim cross-arch model set size-matched to Russian (armv7 EN ASR spike zipformer-en-20M vs moonshine-tiny-en; EN Piper amy; whisper multilingual on 64-bit); one-bulk-per-language eval; auto-detect NOT wired to ASR/TTS so language is a per-config choice | I18N-1 ✓ → I18N-2..6 |
| `../locveil-commons/docs/design/productization.md` `[x]` (AGREED 2026-07-08, joint session, both repos; MIGRATED to the commons 2026-07-11 per D-2 — local file is a pointer; name executed as **Locveil**) | BUILD-20 — the productization umbrella (written as "Domovoy"): product name (D-1), ONE commons repo = eval-commons renamed `locveil-commons` with three ownership regimes (D-2/D-3), PROD-board cross-repo idea discipline + board-as-outbox (D-4/D-5), `locveil-satellite` third product repo + ESP32 estate relocation (D-6/D-7), rule-of-two extractions loader+logging (D-8), two-apps-shared-kit config UI (D-9), ledgers kept over trackers (D-10), semver components + calver suite manifests + contract tagging/scripted re-pin (D-11), normative ops spec + CLAUDE.md invariant blocks/drift guard + landing page + report-policy spec (D-12), drift inventory (§2), commons seed backlog (§3) | BUILD-20 ✓ → BUILD-21/22/23/24, ARCH-42/43, BUILD-18 (narrowed); bridge intake VWB-29, CORE-7, OPS-14/15/16 |
| `config-ui/docs/donation_editor_ux.md` | human-friendly donations editor design | UI-1/2/3 |
| `docs/review/test7_triage.md` (2026-06-15) | TEST-7 Phase-B worklist — 82-failure triage (delete/rewrite/fix) + risk-ranked coverage tiers + fix-code suspects | TEST-7 ✓ |
| `docs/review/api_result_contract_review.md` `[x]` (2026-06-27) | API execution-result response-contract consistency — 5 findings (reply field name, 3-way intent split, divergent metadata under one model, confidence placement, live `None` internal misread); root cause = no shared serializer | QUAL-54 ✓, QUAL-55 |
| `docs/review/codebase_review_2026-06-21.md` (2026-06-21; CR-A1 group resolved 2026-06-22) | whole-codebase health pass — 16 correctness (CR-A1 P0: standalone `voice_runner` web API never starts), 13 dead/zombie (CR-B), 13 duplication (CR-C), 5 stale user-facing doc claims (CR-D). **DONE 2026-06-22:** CR-A1 group (A1/A2/A3/A14/B2/D5 + masking-test fix) + BUILD-7 doc/dup cluster (C1/C2/C4/D1–D4) + dead-code sweep (all CR-B; B4 kept as ARCH-22/25 scaffolding, B12 was QUAL-20) + provider-base dedup (CR-C6/C7, C8 partial — route helpers deferred) + standalone correctness (CR-A4/A8) + silero cleanups (CR-A12/A13) + tracing pair (CR-A7/A9) + path-traversal hardening (CR-A15, security) + correctness trio (CR-A10/A11/A16) + Cyrillic dedup (CR-C3) + nlu-analysis loaders (CR-A6) + audio playback (CR-A5) + dup boot-validator removed (CR-C13) + handler base-class consolidation (CR-C11) + asset-name/path helper (CR-C10) + spaCy init dedup (CR-C5) + WebAPIPlugin walk dedup (CR-C12) + provider /configure gate (CR-C8) + platform-list centralization (CR-C9); **review §A + §B + §C + §D ALL fully resolved**. ARCH-25 (WB7/WB8 hardware bring-up) remains as a separate hardware-gated task, not a review item. Cross-refs: CR-B1→BUILD-7, CR-C1/2/4/D1-4→BUILD-7, CR-C9→ARCH-25, CR-A12→QUAL-15, CR-A16→QUAL-30 | (new findings) |
| `docs/review/config_ui_review.md` `[x]` (2026-06-28) | config-ui quality/dup/dead/correctness pass — 5 confirmed + 2 plausible correctness bugs (404 reload loop, stale-request overwrite, unreachable blocking dialog, wrong-key validation error, stale memo), type-contract drift in `types/api.ts` (CoreConfig/NLUConfig/VADConfig behind backend → defeats the type-check gate), 6 duplications (apiClient quintet, page clones, editor primitives), unused-export dead code, efficiency + hardcoded-list/altitude smells | BUG-8/9/10, UI-11/12/13/14 |

---

## How to use this file

- **Workstreams** are stable buckets. **Tasks** are the unit of work — sized to one coherent commit/PR,
  with a stable ID (referenced in commit messages, e.g. `ARCH-1: …`).
- Status: `- [ ]` open · `- [x]` done · `- [~]` paused/partial · annotate `BLOCKED`/`DEFERRED`/`DOING` + reason inline. Priority `P0–P2`.
- **On completion, a task moves** out of this file into **[`RELEASE_PLAN_DONE.md`](./RELEASE_PLAN_DONE.md)** (frozen,
  by workstream) — flip its status, cut the block here, paste it under its workstream there, in the same change as the
  journal entry. This file holds only **open + paused/partial** tasks so it stays small and readable.
- Individual lint findings live in the review docs (e.g. `docs/review/phase0_static_baseline.md`) and
  **roll up** into a task here — keep this file a spine, not a dumping ground.
- **This file = scope + status only.** Record what happened / decisions in **`RELEASE_JOURNAL.md`** (`one-active-journal`).
  Tag each task **`[release]`** or **`[deferred]`**; the release gate is "every `[release]` task `[x]`" (`single-task-ledger`).

---

## Sequencing (phased roadmap — decided 2026-06-01)

The review wave (QUAL-8/10/12/14) is done. Its P0s are **not one species**: some are *surgical bug fixes*
(architecture-independent), some are *refactor-flavored* (they ARE subsystem architecture work). They sequence
differently. Key constraint: **there is no test safety net right now** (TEST-2 paused; full rewrite = TEST-7 later),
and the structural refactors **move code** — so blind refactoring/fixing is the main risk. Phases:

- **Gate 0 — verification net + cheap guard (do FIRST, before touching structure):**
  - **TEST-0** — a minimal end-to-end smoke harness (boot + a few real flows: command→intent, set a timer, extract
    a parameter). Small refactor safety net, **distinct from the TEST-7 rewrite**. It's the "wire-up integration
    test" all four reviews said is missing — would have caught every review P0.
  - **QUAL-23** — the startup-assertion ("every configured provider/stage/action name resolves to something real").
    Cheap; catches 3 of 4 review P0 *classes* (cascade names, console provider, dead stages) and stops regressions.
- **Gate 1 — structural foundation:** **ARCH-1** (split god-module) → **ARCH-2** (config↔core cycle) →
  **ARCH-4** (formalize ports) → **ARCH-5** (import-linter; folds in QUAL-23). **DOC-4** in parallel (pin the target).
  **✓ COMPLETE 2026-06-02.**
- **Gate 1.5 — dataflow review + reconciliation. ✓ COMPLETE 2026-06-02.** **QUAL-25** (full input→action flow map +
  defect hunt → `dataflow_review.md`, ~9 P0/~20 P1) → **QUAL-26** (review-of-reviews, live: 10 intended-vs-today
  decisions + finalized Gate 2 framing → `dataflow_reconciliation.md`). Surfaced a 4th cross-cutting theme
  (data-contract integrity) and emitted QUAL-27..31.
- **Gate 2 — the cross-cutting systemic remediation + review P0s (downstream of Gate 1.5; framing per QUAL-26):**
  - **Cross-cutting principles** (the lens; full text in the QUAL section): **① fail-loud** · **② shared bases** ·
    **③ config-truth (deployment-aware)** · **④ data-contract integrity**.
  - **Foundational tasks first:** **QUAL-27** (data-contract fixes; ✓ DONE) + **QUAL-28** (context & action-store
    refactor; ✓ DONE 2026-06-02) as the structural base → **QUAL-29** (donation format split; precedes declarative
    device-resolution) remains.
  - **Per-subsystem on top:** **QUAL-9** [FAF], **QUAL-11** [PEX], **QUAL-13** [TXTPROC], **QUAL-15** [LLM],
    **QUAL-16** [PROMPTS], **QUAL-22**, **QUAL-23** + **QUAL-30** (clarification Grade 1).
  - **Later / design-gated:** **QUAL-31** (slot-filling feature) · **ARCH-6** (WS ESP32 input) + **ARCH-7** (output
    seam / MQTT) design sessions · **DOC-7/DOC-8**.

**One-line rule:** *fix the data contracts and the context split first; the per-subsystem P0s ride that foundation.*

---

## Workstreams

### Architecture & Refactor (ARCH)
Target pattern: **Hexagonal (Ports & Adapters)** — SIGNED OFF 2026-06-01. Code is already ~80% there
(interfaces=ports, providers=adapters, components=app services, entry-points=registry).
See `docs/review/phase1_architecture_map.md` §5.

- [ ] **ARCH-16** [IO] (P-deferred) — **I/O daemon multiplexer + runners→thin presets (deferred ARCH-15 PR-10).**
      The I/O hexagon (ARCH-15) is complete and every channel runs; this is the internal-cleanliness endgame, deferred
      2026-06-07 as low-incremental-value / higher-risk. Scope: (a) **remote interactive text-attach channel** (e.g.
      `/ws/cli` — attach a debug-CLI from a notebook, text in/out, routed through the workflow + OutputManager,
      origin-paired; the *reproduce* half of the operator scenario, pairing with the PR-6b `/ws/observe` *observe* half) —
      the highest-value, low-risk piece, additive + testable; (b) **runners → thin config-preset launchers** over **one
      daemon multiplexer** that consumes all active input sources concurrently (generalising PR-5b's CLI consume loop) +
      **runtime attach/detach** (§4/§8) — fuses the CLI/webapi/vosk shapes; the larger, riskier refactor (low e2e
      coverage on interactive paths). Also carries the small ARCH-15 follow-ons: **PR-6c web-app JS** (open `/ws/output`,
      thread `client_id` into POSTs, render pushed frames — web-template edit) and **PR-7 capability-matrix display**
      (read-only outputs×modalities). Refs: `io_architecture.md` §4/§8/§12 (PR-10), ARCH-15, ARCH-6.
- [ ] **ARCH-23** [ESP32] (P-TBD) `[deferred]` — **ESP32 firmware rewrite (ESP-IDF + PlatformIO).** Build the headless
      voice-satellite firmware to the ARCH-22 contract (**`docs/design/esp32_satellite.md`**), replacing the quarantined
      `ESP32/firmware/` draft (rev 2, inspiration only — its protocol predates the backend; UI/output/codec are stubs). Per
      D-1..D-18: board + digital I2S mic + MAX98357A speaker, half-duplex (D-2/D-7); ESP-IDF/PlatformIO not Arduino (D-3);
      the wire protocol §4 (register → PCM → `{"type":"end"}`; reply channel `speak_begin`/PCM/`speak_end`); ported
      microWakeWord on `esp-tflite-micro` with the **TFLite-Micro micro-features frontend** + µVAD (D-9, NOT the draft's
      MFCC/energy VAD); models in a flash data-partition, runtime-loaded (D-12); two-stage SoftAP→STA provisioning + the
      device admin UI + CSR submission (D-16/D-17, against Plane-B `nginx/`); config-preserving OTA (D-18). Likely a separate
      firmware repo eventually (per `esp32_wakeword_review.md` quarantine). Substantial standalone C++ effort; tracked here so
      it's not an orphan finding. Depends on hardware selection finalised (mic/speaker parts) + the Plane-B controller deploy.
- [ ] **ARCH-39** [MQTT][NLU] (P-post-release) `[deferred]` — **DESIGN: device-level force-confirm — the 2-turn
      idempotence-skip escape hatch via voice.** The bridge's DRV-5 (pinned @ QUAL-77) marks idempotence-skipped
      commands (`success: true, no_op: true, skipped_reason: "idempotence"` — nothing transmitted, belief may be
      wrong: one-way IR power, eMotiva, Auralic/LG power_on) and reserves `params.force` to bypass the guard.
      Voice fit (analyzed 2026-07-08): surface `no_op`/`skipped_reason` on `DeliveryResult`
      (`irene/outputs/bridge.py` `_to_delivery_result` currently drops both), then the smart-home handler offers
      proactively («мост считает, что он уже включён — отправить принудительно?») and arms the existing one-shot
      `pending_clarification` session slot (QUAL-31; needs a "confirmation" kind next to "missing param") — resume
      = re-dispatch the remembered command with `force: true`. Safety: never auto-force — the slot IS the user
      confirmation. Bonus already free: the bridge's fix turned the old already-on-IR 503 `device_unreachable`
      timeout into a clean no-op success. Needs NO bridge changes. Deliverable: design doc under `docs/design/`
      + implementation follow-up task(s). Refs: bridge `ab7eb6c`, bridge `docs/design/ui_backend_contract.md`
      ("Force re-tap"), locveil-commons pin `7cfd5a7`.
- [ ] **ARCH-40** [MQTT][NLU] (P-post-release) `[deferred]` — **DESIGN: scenario force-reconcile via voice
      («что-то не так с киносценой»).** The bridge's SCN-11 (pinned @ QUAL-77) adds `GET
      /scenario/{id}/reconcile_preview` (pure read: per-device believed-vs-desired comparisons, `in_sync`,
      forced-chain `steps`, `eta_ms` — note the inversion: `in_sync: true` rows are where force matters) and
      `POST /scenario/{id}/force_reconcile {device_id}` (server-side forced single-device plan, worst case ~25 s).
      Voice shape to design: two new REST methods on the bridge output port, a new intent family on the existing
      scenario support (`smart_home.py` `_handle_scenario_*`), speaking the preview diff + the device-pick turn,
      and the multi-second execution as acknowledge-then-report — a natural ARCH-28 durable F&F with a completion
      notice (`durable-actions` invariant applies). Same safety posture as ARCH-39: preview → user picks →
      confirm → execute, never blanket. Deliverable: design doc under `docs/design/` + implementation follow-up
      task(s). Refs: bridge `43c504c`, bridge `docs/design/ui_backend_contract.md` ("Scenario force-reconcile
      dialog"), locveil-commons pin `7cfd5a7`.
- [ ] **ARCH-42** `[deferred]` [COMMONS][PROCESS] — **DESIGN: extract the dynamic code loader to
      `locveil-commons/packages/core-py`** (BUILD-20 D-8; voice becomes consumer #1, bridge #2 — ownership
      flips to the commons on extraction). Design first (`design-then-implement`): inventory what the loader
      actually is today (entry-point discovery, provider/plugin instantiation, the `provider_namespace_map`
      seams), decide the package's public surface so BOTH products can consume it (bridge wants it for
      driver/module loading — their intake CORE-7), then file the voice-side migration implementation task.
      Gated on BUILD-21 (the package home must exist). Ref: `docs/design/productization.md` D-3/D-8.
- [ ] **ARCH-43** `[deferred]` [COMMONS][PROCESS] — **DESIGN: extract the logging scheme to
      `locveil-commons/packages/core-py`** (BUILD-20 D-8). The startup-rollover + midnight
      TimedRotatingFileHandler + retention-prune family exists twice by hand-copy (bridge OPS-12 → voice
      BUG-30 "ported verbatim") — the exact drift pattern the productization design retires. Design the
      shared package surface (rollover naming family, retention constants, prune sweep, report-bundle
      same-day glob compatibility both sides), then file the voice-side adoption task (bridge intake:
      OPS-14). Gated on BUILD-21. Ref: `docs/design/productization.md` D-8.
- [ ] **ARCH-44** [HW][SEC] `[deferred]` — **DESIGN: device certificate lifecycle — revocation and renewal.**
      Plane B can *issue* device certs but never *withdraw* them. `esp32-provision revoke` only deletes a
      **pending CSR** (`esp32-provision.sh` `revoke` = `rm -f "$PEND/$id.csr"`); once `approve` signs, the cert is
      trusted for its full **825 days** because the mTLS zone runs `ssl_verify_client on` with
      `ssl_client_certificate` and **no `ssl_crl`**. Deleting the published `/srv/esp32/provision/cert/<id>.crt`
      changes nothing — the device already holds its copy. So a lost/stolen/decommissioned satellite keeps
      firmware + model + `/ws/` access until expiry, and the only lever today is re-issuing the whole CA (which
      re-provisions every device). Symmetrically there is **no renewal story**: every device provisioned in the
      same week silently expires in the same week, 825 days on. Design (post-release, before a real fleet exists):
      a CRL (`ssl_crl` + a `revoke-cert` verb regenerating it, nginx reload on change) or short-lived certs with
      auto-renew over mTLS; the operator verb naming needs to distinguish *drop a pending CSR* from *revoke an
      issued cert*. Surfaced 2026-07-09 by the ARCH-25 provisioning round-trip (`probe_node`). Deliverable:
      design doc + implementation follow-up(s). Refs: `docs/design/esp32_satellite.md` D-17, `nginx/README.md`.
- [ ] **ARCH-45** [INFER][OPS] `[deferred]` — **DESIGN: split readiness from liveness on `/health`.** `/health`
      returns a static `{"status": "healthy", version, timestamp}` (`webapi_router.py` ~L343) — it reports the
      process is alive and nothing more. Observed on the WB7 first boot (2026-07-09): uvicorn binds ~8 s in,
      right after `core.start()`, while TTS runs `lazy loading: True` and the piper voice downloads for another
      ~90 s afterwards. So the container is `healthy`, and answering 200, while it **cannot yet speak**. Docker,
      systemd and any future orchestrator all read that as ready. Design a readiness signal: what "ready" means
      per component (ASR model resident? TTS voice loaded? bridge reachable?), whether it is a second endpoint
      (`/ready`, 503 until satisfied) or a status field on `/health`, and which consumers must learn it
      (`config-ui`'s status view, the Dockerfiles' `HEALTHCHECK`, `ops/INSTALL.md`'s first-boot guidance). Note
      the healthcheck's start-period (300s ARM / 180s x86) was sized for a download that turns out **not** to be
      on the critical path — revisit it once readiness is real. Deliverable: design doc + implementation
      follow-up(s).
### Code Quality & Review (QUAL)

#### Cross-cutting systemic remediation — principles (the Gate 2 lens)
_Apply to every remediation task below (from the 4 review docs + QUAL-25/26). Source: `dataflow_reconciliation.md`._
- **① Fail-loud** — raise structured exceptions → catch at ONE handler/orchestrator boundary → typed
  `IntentResult(success=False, error=…)`; **never swallow, guess a default, or return-original-on-failure.** The
  user-facing form is a **conversational clarification** (explain + ask), not an error dump; missing-required and
  no-intent both clarify. Backed by a **donation-driven typed accessor** (one place enforces required-vs-optional).
- **② Shared bases** — one NLU extraction base (donation-`ParameterSpec`-driven), one LLM prompt source (= the
  LLM-independent hardening layer), one normalization seam (contains the `lingua_franca`/`Runorm` debt), one F&F
  write-back, one result-construction contract. No copy-paste-then-diverge.
- **③ Config-truth (deployment-aware)** — every key is schema-known with **no dead trees** (consumed by *some*
  codepath in *some* profile) **and** every *enabled* component/provider/stage resolves to real code. `config-master`
  is a valid curated **superset**; deployment configs are minimal subsets — the check must not flag the superset.
- **④ Data-contract integrity** — a model field means **one thing end-to-end**; no rename residue
  (`Intent.text`/`raw_text`, `WakeWordResult.word`/`wake_word`, action key `action_name`/`domain`, session scope).

- [ ] **QUAL-53** [NLU] (P3) `[deferred]` — **Trace-driven improvement of the cheap NLU tiers** (split from QUAL-51,
      2026-06-16). When an utterance falls through to the LLM classifier, that's a signal the cheap deterministic tiers
      (keyword matcher, spaCy) *should* have caught it. Build an **offline analysis process, integrated with trace
      playback**, that examines such fall-throughs and proposes concrete fixes — donation phrases/patterns, spaCy config,
      keyword/fuzzy thresholds — so the cheap layers catch more and the LLM is reserved for genuine fuzz. **Prerequisite
      (real gap found 2026-06-16):** the NLU cascade trace currently records only the **final** result
      (`nlu_component.py` `record_stage("nlu_cascade")`), not each provider's attempt/confidence — so it can't yet explain
      *why* a fall-through happened. First enrich the cascade trace to record per-provider attempts (which tried, each
      one's confidence, why it abstained), then build the analyzer over recorded traces. Needs real usage data → deferred.
      **2026-07-06 addendum (QUAL-35 Slice 3 evidence — this task now owns the spaCy lane, user decision):** the
      spaCy T2 leg was DROPPED from Slice 3 on the scoreboard (no fixture uniquely needed it). Facts for whoever picks
      this up: `smart_home` has ZERO parked token/slot patterns (the handler postdates the parked authoring), and
      `spacy_provider.recognize` never consumes `token_patterns` — they're validated then stashed in
      `advanced_patterns` only. Reviving the spaCy tier therefore means BOTH halves: authoring smart-home patterns
      AND building the Matcher/EntityRuler recognition+slot-filling path the provider currently lacks.
- [ ] **QUAL-60** [INTENTS][LLM] (P3) `[deferred]` — **Summarize-then-truncate for the LLM conversation window
      (BUG-18 follow-up; user chose "window now + file summarization" 2026-07-02).** BUG-18 bounds the conversation
      store with a plain rolling window (last `max_context_length` turns; seed system prompt pinned) — older context
      is simply forgotten. This task adds continuity for long conversations: when the window overflows, compress the
      dropped turns into a pinned summary message via one LLM call. Needs: a Russian-capable summarization prompt
      (localized, prompt-asset-driven like the handler's other prompts), a fallback to plain windowing when the LLM
      call fails/times out, and a decision on re-summarization cadence (every overflow vs. every K overflows). Seam:
      `ConversationIntentHandler._trim_llm_context` / `UnifiedConversationContext.trim_handler_messages` — the trim
      call is already the single choke point, so summarization slots in front of it without touching call sites.
      _Filed 2026-07-02 from BUG-18._
- [ ] **QUAL-63** `[deferred]` [PEX][MQTT] (P3) — **Priority rules for same-room capability ambiguity**
      (filed from TEST-18 Slice A; user 2026-07-05: clarify "for v1, but actually it can be done thru
      priorities — later release"). When one utterance matches several same-room devices on the same
      capability («поставь на паузу» → TV+AppleTV; «22 градуса» → обогрев+кондиционер), v1 asks a
      clarification (fixtures F20/F21). This task adds configurable resolver priorities so common cases skip
      the question — e.g. playback → the transport actually playing / a preferred device; climate → a
      seasonal heating-vs-cooling default — with clarify remaining the fallback when no rule decides.
      Builds on the QUAL-35 resolver (note 6); fixture impact = NEW priority-variant fixtures beside
      F20/F21, not edits. Any config surface added → the `config-ui-stays-functional` gate applies.
- [ ] **QUAL-68** `[deferred]` [PEX][MQTT] — **Relative adjustments by voice («сделай поярче», «потеплее»,
      «притуши») — read-modify-write (filed 2026-07-06; QUAL-35 Slice 3 scope decision: not for first release).**
      Today the LLM NLU tier classifies these correctly (set_brightness/set_setpoint) and asks for the absolute
      value — honest v1 UX. The build: read the device's current level/setpoint through the EXISTING state-read
      path, apply a step (fixtures assume ±10 % brightness / ±1 °C), emit the absolute `set`; add the donation
      phrases («поярче», «потемнее», «потеплее», «похолоднее», «притуши») — dedicated methods or a `delta` param.
      **Fixtures F100–F102 are already authored RED** in locveil-commons `crossover_fixtures.json` (mock static state
      carries `level: 60`; deltas recorded in the fixture notes) — flipping them green completes this.
- [ ] **QUAL-78** [OPS] `[deferred]` — **The container healthcheck spams the log with one access line per probe.**
      Since the honest `HEALTHCHECK` landed (ARCH-25, 2026-07-09) uvicorn access-logs every probe:
      `INFO: 127.0.0.1:… - "GET /health HTTP/1.1" 200 OK` every 30 s, forever — ~2.9k lines/day in
      `logs/irene.log`, drowning real events and burning the rotation budget BUG-30 just installed. Filter it:
      a `logging.Filter` on `uvicorn.access` dropping 2xx `/health` (and `/ready`, per ARCH-45), installed where
      `web_server.py` builds the uvicorn config (`_build_uvicorn_server`, which already special-cases uvicorn's
      logging so its loggers propagate to the root handlers). Keep non-2xx — a failing probe is exactly the
      event worth seeing. Surfaced on the WB7 bring-up.
- [ ] **QUAL-79** [APICONTRACT] `[deferred]` — **`confidence` on the intent-result contract is a success flag, not
      a confidence.** `IntentResult.confidence` (`intents/models.py:55`, *"Confidence in the response"*) is set by
      only **4 of 120** `IntentResult(...)` constructions — all in `handlers/base.py`, `1.0` on the success helper
      and `0.0` on the error helper; everything else takes the `1.0` default. `api/serializers.py:38` (the single
      canonical serializer QUAL-55 introduced) lifts that value to the response's top level, so every
      intent-executing surface reports a constant. Meanwhile the **recognition** confidence — `Intent.confidence`,
      logged at `nlu_component.py:793`, and the number the cascade actually gates on
      (`voice_assistant.py:558`, `>= threshold`) — never reaches a client. Observed on the WB7 (2026-07-09):
      «включи свет в кабинете» recognized at **0.76** against a 0.70 threshold, response said `confidence: 1.0`;
      and a *failed* read-state reply also said `confidence: 1.0` (`success: false`), so it is not even reliably
      the success flag it duplicates. QUAL-55 canonicalized *where* the field sits without asking *what* it means.
      Fix: `confidence` should carry the recognition confidence (`success` already encodes the rest); the
      orchestrator holds the `Intent` when it builds the result. **Contract change across three surfaces** —
      the REST response (`openapi.json` → config-ui's generated types), the WS response frame
      (`docs/guides/websocket-api.md`, which `ws-protocol-doc-canonical` makes authoritative), and
      `locveil-commons/eval/eval_commons/providers/ws_audio_provider.py`, which documents the field. Nothing currently *consumes* the
      value, which is why this is deferrable rather than urgent. Interim alternative if the break is unwelcome:
      add `recognition_confidence` alongside — purely additive, but it leaves the misleading field in place.
- [ ] **QUAL-82** [MQTT][NLU] `[deferred]` — **FEATURE: voice control for the AC louvers (`vane`/`widevane`) —
      gated on the VWB-33 language-ownership convention.** DRV-28 (consumed as QUAL-81) gave the three
      MitsubishiHvac ACs `vane.set{value}` (auto, качание, положение 1–5) and `widevane.set{value}` (качание,
      крайне влево…крайне вправо, разделено); voice deliberately exposes neither — the old `climate.set_vane`
      never had a voice consumer either (`git log -S set_vane` over `irene/` is empty), so QUAL-81 preserved
      exact feature parity and invented nothing.
      **The plumbing is an afternoon by design** — QUAL-81's binding table means
      `_CHOICE_BINDINGS["vane"] = (("vane", "set", "value"),)`, one donation method riding `_hvac_choice`
      (label matching, clarification, delivery all generalize), templates, tests. **The linguistics is the
      work**, and it is the actual scope:
      (1) **the noun collision** — the natural Russian word for the louver, «жалюзи», is already a `cover`-group
      surface (the cabinet rollers), so «поверни жалюзи» would fight the depth-doctrine group routing; the
      capability needs a chosen spoken noun («шторка»? «обдув»?) and it must not poison cover routing;
      (2) **two utterance shapes** — vane is positional («положение три»: a number into a choice param),
      widevane is directional and verb-led («направь обдув влево», unlike mode's noun-led «кондиционер на
      охлаждение») — new T1 patterns plus intent names the LLM tier can classify into;
      (3) **ownership** — the catalog carries the value labels; whether the capability noun and verb patterns
      live catalog-side or donation-side is exactly what the bridge's **VWB-33** design decides, and this
      feature is its first real test case — building before the convention exists risks building what it then
      forbids. Also honest-UX: mode/fan are daily speech; vane is a set-once remote-in-hand tweak — no demand
      recorded yet. Ref: QUAL-81 (binding table), `docs/design/mqtt_integration.md` §14, bridge VWB-33.

### Bugs (BUG)
_Discrete functional defects (distinct from QUAL refactors/quality work). Surfaced from any source; filed before fixing._

- [ ] **BUG-37** [NLU][TTS][UX] `[deferred]` — **Spoken sensor readings are unrounded, mis-vocalized and
      ungrammatical.** Latent since the read-state path was written; **invisible until 2026-07-09**, when the
      bridge's DRV-23 fix made `smart_home.read_state` return a value for the first time. «какая температура в
      кабинете» now answers `«Сейчас 24.125 градусов — Тёплый пол»`. Three defects compound:
      **(a) no rounding.** `smart_home.py:636` only narrows a float when it is already integral
      (`value == int(value)`), so a sensor's `24.125` reaches the template verbatim. A person says «двадцать
      четыре градуса».
      **(b) the decimal is vocalized wrongly — RUSSIAN ONLY** (verified 2026-07-09; English is correct:
      `"It is 24.125 degrees"` → *"twenty four point one two five"*, via `ovos_number_parser.pronounce_number`).
      Root cause: `utils/text_processing.decimal_to_text_ru` (`:177-183`) is a **money formatter** —
      `value.quantize(10**-places)` with `places=2`, then it speaks the fraction as a bare whole number through
      `num_to_text_ru(int(exp), exp_units)`. With `int_units=рубль, exp_units=копейка` it correctly says
      «двенадцать рублей тридцать четыре копейки»; called with no units, as the spoken path does, it truncates
      (`24.125 → 24.12`) and reads the remainder as an integer: `24.125 → «двадцать четыре двенадцать»`,
      `24.5 → «двадцать четыре пятьдесят»`, `12.34 → «двенадцать тридцать четыре»`. Its own docstring promises
      «двенадцать целых тридцать четыре сотых» — never implemented.
      **(c) no numeral agreement — both languages, different rules.** `ru.yaml:42` hardcodes «градусов»:
      `1 → «один градусов»` (should be «градус»), `24 → «двадцать четыре градусов»` (should be «градуса»);
      Russian needs three forms. `en.yaml:41` needs only singular/plural: `"1 degrees"` → `"1 degree"`.
      Fix: round sensor values at the handler (integer for temperature) — language-agnostic, and it makes (b)
      moot for this feature; decline the unit by the numeral in both template sets; and repair the Russian
      fraction path independently, since **`all_num_to_text` feeds the TTS text-processing stage
      (`text_processor_component.py:241`) and the silero provider, so every spoken Russian decimal in the system
      is mangled, not just temperatures.** Blast radius for (b): 4 call sites — check timers/percentages before
      touching it. Not release-blocking (v0.5.0 is tagged), but it is the first sentence a user hears from a
      headline feature; worth fixing before the feature is mentioned to anyone.

- [ ] **BUG-39** [MQTT][UX] `[deferred]` — **The ambiguity clarification lists identical names, so it cannot be
      answered.** «включи кондиционер в гостиной» asks: *«Какой именно: Кондиционер или Кондиционер или
      Кондиционер?»* `_ambiguous_result` (`smart_home.py:255`) builds the prompt from `c.get("name")` alone,
      while the candidate payloads carry `room` (`bedroom_hvac`, `children_room_hvac`, `living_room_hvac` — all
      named «Кондиционер»). The user can only repeat themselves; a clarification they cannot answer is worse
      than none. Qualify each option by its room («Кондиционер в спальне, в детской или в гостиной?»), falling
      back to a further distinguishing attribute when the rooms also coincide. **Independent of BUG-38 and
      survives it:** genuine within-room ambiguity («ночники» = two sconces in one room) still yields identical
      names. Same code serves the capability-level ambiguity path, so fix once. Related: QUAL-63 (priority rules
      for ambiguity) may later avoid asking at all in some of these cases; this task is about the question being
      answerable when it *is* asked.

- [ ] **BUG-42** [TEST] `[deferred]` — **Order-dependent flake:
      `test_arch36_satellite.py::test_recorder_declined_and_next_utterance_finalizes` fails in the full
      suite, passes in isolation** (its file also passes alone, 14/14). Reproduced identically on
      2026-07-11 pre- and post-BUILD-29 trees (1 failed / 1379 passed both times), so it is
      cross-file state leakage (another test's residue), not a recent regression. Diagnose with
      `pytest -p no:randomly`-style bisection or `--lf`-adjacent ordering; fix the leaking fixture
      or isolate the recorder state.
### Tests (TEST)
> **Strategy (decided 2026-06-01): do NOT keep repairing the existing suite.** Most tests were written against
> pre-refactor code and will be invalidated by the ARCH refactors (ARCH-1..5) and the code reviews (QUAL-8/10/12/14).
> Fixing them now is throwaway work. The TEST-1/TEST-2 pass already extracted the real value — it **proved the suite
> runs** and surfaced concrete prod findings (QUAL-21, QUAL-22, the text_processor trace fix). The current state
> (166 pass / 56 fail / 13 skip / 2 xfail, all committed) stands as a **partial safety net**; the remaining 56
> failures are left **intentionally unfixed**. The real test effort is **TEST-7: rewrite the suite after the
> architecture + code reviews land** (gated). TEST-3/4/5/6 are coverage goals folded into that rewrite.

_Trace-driven system testing (design `docs/design/trace_system_testing.md`, TEST-11 ✓) — all implementation slices
(TEST-12/13/14/15) done; see `RELEASE_PLAN_DONE.md`._

- [ ] **TEST-19** `[deferred]` [TEST][I18N][MQTT] — **English axis for the device suite + EN misroute fixes**
      (filed 2026-07-06 from the BUG-5 probing session; post-release per user — an external EN tester exists, RU
      ships first). **Scope (one task, fixtures + fixes together, user decision):** (1) `utterance.en` on the
      crossover fixtures where an EN phrasing is meaningful + `fixtures_to_tests` emits per-language cases +
      an `eval/Makefile` `LANG=en` knob (SUT config derived from the `standalone-x86_64-en` profile — the suite
      is text-driven, no audio, so this is cheap); (2) run the EN scoreboard and fix what's red at the right
      altitude (donation patterns first — the QUAL-64/Slice-3 lesson; BUG-5 already fixed the article-blind
      timer phrases this way). **Seed evidence — four PRE-EXISTING EN misroutes found by probing 2026-07-06**
      (all reproduce at pre-BUG-5 HEAD too): "cancel the timer" → `voice_synthesis.cancel` (0.89, bare-cancel
      greed); "switch asr to whisper" → `smart_home.input_select` (0.71, «switch…to» greed); "translate hello
      to german" → `greeting.hello` (0.86, keyword beats verb); bare "pause" → `audio.stop` (1.00 — note the
      RU twin «поставь на паузу» routes `smart_home.playback_pause`; decide the intended EN owner before
      fixing). Consumer half unaffected: `expect` stays canonical, the bridge replays language-blind.
- [ ] **TEST-20** [TEST] `[deferred]` — **`test_arch36_satellite.py::test_recorder_declined_and_next_utterance_finalizes`
      is flaky (~3/8).** Fails intermittently in isolation on a clean tree (measured 2026-07-09, 3 failures in 8
      consecutive runs; confirmed **not** caused by the BUG-35 change — reproduced with that diff stashed). A
      timing/ordering dependency in the recorder-declined path, not a product bug as far as anyone has shown.
      Fix the test's synchronization (or the race it is accidentally documenting — decide which at task start).
      Until then it can red a clean CI run at random, which is corrosive: it teaches everyone to ignore failures.

### Build & CI (BUILD)
_Real English deployment across all three Docker arches (armv7/aarch64/x86_64) + English eval. Design
`docs/design/multilingual_deployment.md` (I18N-1 ✓) → the implementation slices below. English models are slim and
size-matched to the Russian stack; language is a per-config/deployment choice (auto-detect is NOT wired to ASR/TTS)._

- [ ] **BUILD-13** `[deferred]` [SATELLITE][DOCKER] — **Pi/aarch64 satellite docker image** (ARCH-35 S-8:
      explicit deferred follow-up — `uv run irene-satellite` covers the release need). A slim aarch64 image
      on the `satellite.toml` profile (mic device passthrough, credentials volume for the S-6 material),
      published beside the backend images; compose snippet for a Pi room node.
- [ ] **BUILD-14** `[deferred]` [CI][FEEDBACK] — **Retire the pre-ARCH-30 public-repo issue triage; consolidate
      intake on `wb-user-reports`** (filed 2026-07-06, user; post-release-1). This repo still carries the
      old deterministic triage from before the problem-reporting system existed:
      `.github/workflows/issue-triage.yml` (keyword → `area:*`/`platform:*` labels + ack comment, no AI)
      and the `.github/ISSUE_TEMPLATE/` intake forms — now the strictly weaker of the two intake paths
      (the reports repo has Claude triage with lens process files, the /inbox loop, and — since ARCH-34 —
      bundles with bridge evidence). Scope: move/adapt what's worth keeping into `wb-user-reports` and
      retire the rest — decide at task start whether public GitHub issues should (a) flow into the reports-
      repo triage (e.g. a forwarding workflow that mirrors them as tickets, minus the private-bundle parts),
      or (b) keep lightweight templates here with the triage workflow simply deleted. Mind the leak fence
      either way: public issues carry no household data, so mirroring is safe in that direction only.
      Cross-repo: any reports-repo workflow change is committed there; the bridge repo has the same
      question — file the sibling task into its ledger (uncommitted) if (a) is chosen.
- [ ] **BUILD-18** `[deferred]` [BUILD][OPS][PROCESS] — **Cross-project build/installation/rules
      harmonization (voice ↔ bridge), next release** (filed 2026-07-08, user: "we will need to address
      build/installation/rules/etc harmonization across projects in the next release"). The two repos
      converged on the same ops patterns piecemeal — sdcard-clone + `/mnt/data/<name>-config` runtime tree,
      repo-owns-config rsync, `ops/.env` secrets, systemd oneshot units, GHCR pull-not-build, log rotation
      (BUG-30 ported the bridge's scheme verbatim), problem-report plumbing — but each convergence was a
      hand-copy with local dialects (naming, `update.sh` shapes, INSTALL.md structure, retention constants,
      CLAUDE.md invariant wording). Scope at task start: inventory the drift, decide what becomes a shared
      convention (a common ops template? a shared doc both CLAUDE.mds cite? extracted tooling?) vs what
      stays deliberately repo-local, and file the per-repo implementation tasks each side (bridge side
      uncommitted, per `cross-repo-source-of-truth`). **Design landed 2026-07-08 (BUILD-20,
      `docs/design/productization.md` D-12): the shared convention = a normative ops spec in
      `locveil-commons/process/` + per-repo conformance; the drift inventory is recorded there (§2). This
      task NARROWS to the voice-side conformance pass once that spec exists (gated on BUILD-21).**
- [ ] **BUILD-22** `[deferred]` [SATELLITE][PROCESS] — **locveil-satellite bootstrap + ESP32 estate
      relocation out of this repo** (BUILD-20 D-6/D-7; repo creation = OWNER ACTION, sibling working copy
      per the repos-are-siblings rule). Create the third product repo (own CLAUDE.md in the invariant
      family + `HW-GATED` marker, ledger, journal; scope: SKIDL/KiCad PCB + ESP-IDF firmware + enclosure).
      MOVE the satellite-side design corpus (`docs/design/esp32_satellite.md`, superseded
      `ws_esp32_transport.md` lineage, `docs/architecture/esp32.md`, `docs/images/esp32-*.dot/png`) —
      leaving pointers; **DELETE the top-level `ESP32/` tree outright** (user verdict 2026-07-08:
      outdated — dead-code rule, not migrated). STAYS here: the WS protocol doc
      (`ws-protocol-doc-canonical` — satellite PINS it by version), `irene/satellite/`, client
      registry/provisioning/CSR code, nginx Plane-B ansible glue, frozen review/archive docs. Re-home
      ARCH-22's remaining design intent into the new repo's ledger at task start (reconcile: parts are
      superseded by ARCH-35/python-satellite). Ref: `docs/design/productization.md` D-6.
- [ ] **BUILD-23** `[deferred]` [PROCESS] — **Shared CLAUDE.md invariant blocks + drift guard — voice-side
      adoption** (BUILD-20 D-12). Once the normative blocks exist in `locveil-commons/process/`: fence the
      shared invariants in this repo's CLAUDE.md between markers, keep per-repo invariants
      (`ws-protocol-doc-canonical`, `durable-actions`, …) outside, adopt the drift-guard script into the
      gate list beside scope-guard, and take the same-slug renames (`config-master-canonical` splits
      — design §2). Bridge intake: OPS-16. Gated on BUILD-21 + the commons PROD task authoring the blocks.
- [ ] **BUILD-24** `[deferred]` [COMMONS][TEST] — **Scripted contract re-pin + staleness gate — voice
      side** (BUILD-20 D-11). Replace the hand-copy re-pin with `make repin CONTRACT=vN` (fetch from the
      bridge's `contract-vN` tag, write `locveil-commons/contracts/STAMP.json`/`PIN.json`) + a gate check
      that goes red when the pin trails the newest bridge contract tag — staleness becomes a machine
      failure, not a memory note. Pairs with bridge intake VWB-29 (they tag + attach artifacts; gated on
      it). Ref: `docs/design/productization.md` D-11.
- [ ] **BUILD-26** [BUILD][UI] `[deferred]` — **`config-ui/openapi.json` is a committed generated artifact that
      nothing regenerates.** Found during REL-4 (2026-07-09): re-running `scripts/dump_openapi.py` produced 241
      inserted lines — four schemas (`BridgeOutputConfig`, `ReportsConfig`, `SatelliteConfig`,
      `SatelliteTLSConfig`) had been added to the API by earlier work and never re-dumped, besides
      `info.version` and `HealthResponse.inactive_providers`. `config-ui`'s TypeScript types are generated
      *from* that file (`npm run gen:api-types`), so the editor has been type-checking against a stale view of
      the backend and silently lacks types for those config sections. Fix: a CI gate that regenerates and fails
      on drift (the scope-guard / contract-pin mechanic applied to a generated file), or drop the artifact
      from git and generate it during the build. Pairs with `config-ui-stays-functional`, which assumes the
      schema the UI is built against is the schema the backend serves.
- [ ] **BUILD-28** [OPS][PROCESS] `[deferred]` — **One compose file for the controller, with a real startup
      order.** Three containers run on the WB7 today — `locveil-bridge`, `locveil-bridge-ui`, `locveil-voice`
      (post-BUILD-29 names) — from **two** compose projects (`locveil-bridge-config`, `locveil-voice-config`),
      each with its own systemd unit, no
      `depends_on` between them and no ordering guarantee. Voice pulls the bridge's catalog at startup, so today
      it simply races and relies on the ARCH-26 lazy refresh to paper over losing (BUILD-27). Owner's framing
      (2026-07-09): the permanent answer is a single compose file managing all three, with the startup sequence
      expressed rather than hoped for — and since it spans both product repos, it belongs on the **commons PROD
      board** (D-4/D-5), seeded when BUILD-21 lands, not decided unilaterally here. Scope for that design: which
      repo owns the unified compose, health-gated `depends_on` vs. tolerant clients, whether the units collapse
      into one, and how `update.sh` stays per-repo when the compose is not. Related: BUILD-18 (ops conformance).
- [ ] **BUILD-30** `[release]` [PROCESS][CI] — **Scope-guard cutover — consume the commons ledger guard at
      `scope-v2`** (PROD-13 / HK-1 delegation, board entry `../locveil-commons/board/BOARD.md`; normative
      convention `../locveil-commons/process/ledger-discipline.md`). Replace `scripts/check_scope.py` with the
      commons-owned, config-driven `scope_guard.py`, vendored at the pinned tag (regime 2 — behavior changes in
      commons only, moves by re-pin): (1) vendor `scripts/scope_guard.py` + author `.scope-guard.toml`; (2) retire
      the local checker and re-point the CI `ledger-guard` job + `ledger` paths-filter; (3) committed `hooks/` +
      `core.hooksPath` running the check pre-commit; (4) invariant text updates (`single-task-ledger`,
      `one-active-journal`, gate wording here) in the same change; (5) DONE-ledger rotation adopted + the overdue
      journal rotation, via `--rotate` in its own commit; (6) required-task-tags rule ON. Pre-existing findings
      the cutover fixes (invisible to the old checker): unsorted DONE I18N section, DONE ledger over the
      4000-line hard ceiling. Cutover proof: vendored tool green before the local script is deleted.
      Delegation originally named `scope-v1`; its journal rotation corrupted archives (char-per-line) — hit
      here and by bridge OPS-22 concurrently, fixed commons-side as `scope-v2` (the pin this task consumes).

### UI / config-ui (UI)
React/Vite donation+config editor. Front-end feature/UX work (the BUILD-4 build gate stays under Build & CI).
Governed by `config-ui-stays-functional` (config-ui must stay functional).

- [ ] **UI-4** [WORKFLOWVIZ] (P-deferred) — A config-ui **"Workflow Control" / pipeline-visualization page** (live
      React-Flow DAG of the component/provider pipeline, per-stage input/output inspection, provider switching, SSE
      updates). **Source design archived** at `docs/archive/workflow_control.md` (Sep-2025, never built). **Strongly
      gated — do NOT start before Gate 2:** the design assumes a clean pipeline, but QUAL-25 proved the real dataflow
      is broken at many hops (visualizing it now would faithfully render broken flow), and it specs `/workflow/*`
      endpoints that `architecture.md` §7 flags as **fictional** (they'd have to be built for real). Relates to the
      `MonitoringPage` placeholder and the **ARCH-7 [MQTT]** output-seam work (both touch live pipeline observability).
      Re-scope against the *fixed* pipeline + real endpoints when it's actually picked up. Captured from a config-ui
      doc reviewed during QUAL-25 (2026-06-02).
- [ ] **UI-15** [UI] (P3) `[deferred]` — **★ DESIGN — donation blocking-conflict resolution** (`design-then-implement`;
      user chose "build real resolution" when triaging BUG-10, 2026-06-28). BUG-10 made `BlockingConflictsDialog`
      reachable **read-only** (a "Review blocking conflicts" trigger; no Resolve buttons). This task designs+builds the
      real thing: define what *resolving/overriding* a blocking NLU conflict means in the donations editor (override-to-
      save? jump-to-edit the conflicting method/param? apply a suggested fix then re-validate?), then implement
      `BlockingConflictsDialog.onResolve` + the gating change that lets save proceed once blockers are resolved/overridden
      (today `canSaveNLU` hard-requires `!hasBlockingConflicts`). Deliverable: a design doc under `docs/design/` first,
      then implementation follow-up(s). The inline `ValidationIndicator` already surfaces blockers, so scope the modal's
      added value deliberately (resolution UX, not just a second display).
- [ ] **UI-16** [UI] (P3) `[deferred]` — **config-ui schema-driven sections/widgets + spaCy-attr i18n** (review §E
      altitude; spun out of UI-14 on completion, 2026-06-28 — these need backend support or are low-value, unlike the
      E6 part UI-14 did). **E7** schema-drive the `ConfigSection` component roster + `section→component` map, and **E9**
      schema-drive `ConfigWidgets`' per-name/path widget heuristics — **both blocked on backend schema metadata** (a
      per-section `is_component` signal / per-field `widget` hint; the config schema carries neither today), so this is
      a backend+frontend task, not a config-ui-only fix. **E10** i18n the spaCy attribute descriptions
      (`getSpacyAttributeSuggestions`, 21 entries) — config-ui-only but niche (a power-user raw-pattern editor; the
      attribute *keys* stay technical per `donation-choice-surfaces-rule`). _Assessed non-issue (not filed): E8 — the
      `LanguageTabs` display-name map is inherently a UI concern (the backend has no display names) and degrades to
      `code.toUpperCase()`; the `DonationsPage` `['en','ru']` fallback is a defensible default for a rare miss._

### Release Readiness (REL)

---

_**Chronology lives in [`RELEASE_JOURNAL.md`](./RELEASE_JOURNAL.md)** — this file is the task ledger only
(scope + status). Findings/rationale: `docs/review/*` + `docs/design/*`._
