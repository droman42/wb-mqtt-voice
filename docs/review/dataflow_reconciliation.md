> **📄 FROZEN EVIDENCE — not the task ledger.** Findings/rationale below are a point-in-time record. The
> authoritative **scope + status** is [`docs/RELEASE_PLAN.md`](../RELEASE_PLAN.md); chronology is
> [`docs/RELEASE_JOURNAL.md`](../RELEASE_JOURNAL.md). Inline status notes here (DONE/✅/…) are **historical and NOT
> authoritative** — check the ledger for live status (Invariant #5/#6). Edit this file only to correct a *finding*.

# QUAL-26 [DFLOW] — Review-of-reviews: reconciliation & decisions log

**Status:** ✅ COMPLETE (2026-06-02) — all 10 issues decided; Gate 2 framing finalized + tasks numbered (Q10).
**Format:** live Q&A session. Issues presented one at a time, ordered by importance; each **decided → actionable**.

**Inputs:** `dataflow_review.md` (§4 reconciliation, §6 open questions) + the four QUAL reviews
(`fire_and_forget`, `parameter_extraction`, `text_processing`, `llm_usage`) + the 4 cross-cutting themes
(fail-loud / shared-bases / config-truth / data-contract-drift).

**Purpose:** for each cross-review inconsistency, decide **intended behaviour vs what exists today**
(fix-to-intent / accept-current / redesign), then **finalize the Gate 2 framing** and number the remediation tasks.

---

## Agenda (ordered by importance)

| # | Issue | What it blocks / why | Status |
|---|---|---|---|
| Q1 | **Text contract** — what does `Intent.raw_text` carry (original vs processed), and how is normalized text threaded? | P0-1 (biggest defect), P1-c, QUAL-13, the LLM/chat path | ✅ DECIDED |
| Q2 | **Session identity** — forbid `"default"`; `get` vs `get_or_create`; always derive a real session_id; unify eviction clocks | P0-6 (cross-request leak), P1-p | ✅ DECIDED |
| Q3 | **Fire-and-forget keying** — one key end-to-end (`action_name`) + a `domain` index; fix dup-`session_id` + `get_or_create_context` together | P0-2/3/4, P1-k/l/m/n | ✅ DECIDED |
| Q4 | **Wired-or-delete** — MemoryManager · ContextLayer/progressive-context · InputManager queue + WebSocket input · `Intent.session_id` · `_disambiguate_with_device_context` · dead text-proc stages | P0-7, P0-8, P1-g; scopes how much code is deleted vs fixed | ✅ DECIDED |
| Q5 | **Conversation history** — pick the canonical representation (3 today) and a single writer | P1-q | ✅ DECIDED (by consequence) |
| Q6 | **Device-context pipeline** — who populates `device_context`/`available_devices` at the entry | P1-j (blocks the PEX device-resolution P0) | ✅ DECIDED |
| Q7 | **Fail-loud philosophy + typed accessor** (theme #1) — raise vs result-signal; where the typed entity/result accessor lives | P0-9, P1-a/s; the whole handler boundary | ✅ DECIDED |
| Q8 | **Shared-bases consolidations** (theme #2) — extraction base · prompt source · F&F write-back · collapse text processors · `_create_error_result` signature | P1-f/k/r/t | ✅ DECIDED |
| Q9 | **Config-truth scope** (theme #3) — cascade phantoms · `language` plumbing · dead config trees · schema↔model drift | P1-e/h/i, P2 tail | ✅ DECIDED |
| Q10 | **Gate 2 framing + numbering** (meta) — principles block vs discrete tasks (QUAL-27/28/…); number the new P0s | finalizes Gate 2 | ✅ DECIDED |

**Mechanical fixes confirmed with no decision needed** (fold into the relevant remediation task): `WakeWordResult.word`
vs `.wake_word` consumer rename (P1-b); the `intent.text` → correct-field replacement is mechanical *once Q1 sets the
contract*.

---

## Decisions log

_(filled per question as we resolve them — each entry: decision · rationale · resulting action/task)_

### Q1 — Text contract · ✅ DECIDED (Option A)
**Decision:** `Intent.raw_text` carries the **literal original user utterance**. NLU stops overwriting it with
processed text. The **normalized/processed text is a pipeline-internal intermediate** (local to `_process_pipeline`,
passed into NLU for matching only) — it does **not** become a persisted field on `Intent`. NLU matches on the
normalized text but stamps `raw_text = original`.
**Rationale:** nothing downstream of NLU needs the normalized form — handlers (translation, text-enhance, TTS-speak,
provider-switch) want the actual user words, and TTS normalizes the *response* via a separate `tts_input` stage.
Makes the field name honest and the LLM/chat path get real input. Resolves P0-1 **and** P1-c together.
**Actions (→ numbered in Q10):** (1) replace the 14 `intent.text` reads (7 handlers) + `Intent(text=…)` at
`orchestrator.py:217` with `raw_text`; (2) thread original+normalized into NLU `recognize`, provider sets
`raw_text=original`, matches on normalized; (3) remove the NLU sites that set `raw_text=processed_text`
(`hybrid_keyword_matcher.py:779`, `spacy_provider.py:753`, `nlu_component.py`). Intersects QUAL-11/13.

### Q2 — Session identity · 🔵 OPEN (analysis captured, awaiting decision)
**Analysis (2 investigation agents, 2026-06-02).** Two user questions reframed this:
- **F&F follow-up linkage:** a later "stop"/"louder" binds to a running action *only* via `active_actions` on the
  session context, found *only if* request #2 shares request #1's `session_id`. Orchestrator intercepts
  `domain=="contextual"` (`orchestrator.py:146`), reads `active_actions`, picks a **target domain** by priority+recency
  (`context.py:571-742`), re-dispatches `{domain}.{cmd}`. Designed scope = **room** (`session_id="{room}_session"`,
  `context_models.py:44` "sessions represent physical locations"). Broken 4 ways → **no contextual command executes
  today**: `"default"` collapse, `Intent(text=…)` crash (P0-1), action_name/domain key mismatch, timer launch crash.
  Emerging model: **session_id = scope · action_name = identity · domain = router index.**
- **Room concept:** intended chain source→`client_id`+`room_name`+`available_devices`→context→entity resolution
  (stamp room + filter devices by room)→MQTT. Reality: structures REAL, but **both ends missing** — `ClientRegistry`
  orphaned (tests-only), `device_context`/`available_devices` never populated (P1-j), MQTT deferred (zero code),
  ESP32-wake-word→room absent (doc-only). Only WebAPI `room_alias` sets a room-session (client_id only). "turn on the
  light"→"in kitchen" today only **stamps a room label** (`nlu_component.py:79-85`), doesn't filter devices by room.

**Key insight:** `session_id` is overloaded with two orthogonal scopes — **physical origin** (room/device; stable;
needed for F&F linkage + IoT + MQTT) and **conversation** (transient). F&F follow-up *requires the stable scope*.

**Two models on the table:**
- **Model 1 — session *is* the room:** `session_id` derived from stable origin (room→client→generated), forbid
  `"default"`; room encoded in the id; `active_actions` room-session-scoped; history = windowed per-room thread.
- **Model 2 (recommended) — split identity from session:** room/client/device = explicit first-class identity on
  `RequestContext` (populated by entry adapter from `ClientRegistry`; kill `extract_room_from_session`); `active_actions`
  bind to that physical identity; `session_id` = conversation token. Lines up with the future MQTT `{room_name}` target.

Mechanical either way: split `get` vs `get_or_create` (2b ✓), unify eviction on `last_activity` (2c ✓). **Crux for
user:** Model 1 vs Model 2 (the physical-scope fork). Note: full room→device→MQTT chain can't complete now (MQTT
deferred, registry orphaned) — but the *scoping* decision is needed for F&F to work at all. Relates to Q3 (F&F keying),
Q6 (device-pipeline ownership), ARCH-7 (MQTT consumer).

**✅ DECIDED — Model 2 (split identity from session).**
- **Two stores, two lifetimes:** (1) **physical-identity store** (room/device/client — the `ClientRegistry` record is
  the device/room source-of-truth) holds `active_actions` + device capabilities, **long-lived** (survives across
  conversations; drains as actions complete). (2) **conversation session** holds history + state + disambiguation,
  **short-lived**.
- **`active_actions` live on the physical identity, NOT the session** (load-bearing decision) — so session expiry never
  kills a running timer/music; a later "стоп" still finds it via the room/device identity.
- **Session lifecycle:** default **idle-window** — a session persists while turns arrive; after **T min** silence it
  closes and the next utterance opens a fresh one. Plus a **sliding history window** of **N turns** (wire the
  ignored `max_history_turns`, P1-q). **Values: T = 10 min global / ~5 min voice (configurable); N = 15 turns.**
  Per-modality boundaries: **voice** = wake-word-delimited burst; **web/WS** = the connection (reconnect/"new chat" =
  new session); **REST** = caller-supplied conversation id else single-turn ephemeral.
- **Room/device = explicit first-class identity** on `RequestContext` (populated by the entry adapter from
  `ClientRegistry`). **Kill `extract_room_from_session`** (P1-o) — room travels as a field, never parsed from the id.
- **`session_id` = conversation token**, never the literal `"default"` (P0-6). **Split `get` vs `get_or_create`**
  (2b ✓ — `get` returns existing-or-None, only `get_or_create` mints). **Unify eviction on `last_activity`**, delete
  the second cleanup loop (2c ✓).
**Actions (→ Q10):** split `UnifiedConversationContext` into a long-lived physical-identity/action store + a
short-lived conversation session; relocate `active_actions`; wire entry adapter → `ClientRegistry` (ties Q6); forbid
`"default"`; get/get_or_create split; window history; drop `extract_room_from_session`. Big-ticket — spans QUAL-9/11 +
context refactor. Full room→device→**MQTT** chain completes later (ARCH-7/8).

### Q3 — Fire-and-forget keying & write-back · ✅ DECIDED
- **3a (confirmed):** `active_actions` keyed by unique **`action_name`** (identity); **`domain`** is a secondary
  **index** for the contextual router (priority + recency); **N concurrent actions per domain supported** (fixes the
  same-domain clobber).
- **3b — dedicated long-lived action store** keyed by physical identity (room/device/client), `ClientRegistry` as the
  device/room source-of-truth. **Zombie-resistant by design — authoritative rule: an action is live iff its asyncio
  task is live.** Four removal layers: (1) completion callback (primary, action_name-keyed); (2) read-time liveness
  filter (resolver skips `done()` tasks before targeting); (3) periodic reaper sweep (catches missed callbacks /
  crashed-GC'd tasks — the exact historical failure); (4) TTL + grace for bounded actions (timers) + hard
  max-concurrent cap per identity. Store holds the task ref authoritatively (also fixes orphan-task P1-m).
- **3c (confirmed):** single write-back path — keep workflow-level `voice_assistant._process_action_metadata`
  (the funnel all modalities pass through); **delete** `workflow_manager._process_action_metadata_integration` (P1-k).
- **Mechanical → QUAL-9** (no decision): dup-`session_id` launch crash (P0-2), wire real `get_or_create_context` from
  Q2 (P0-4), fire completion lifecycle (metrics/notifications/timeout-cleanup), key metrics by `action_name` (P1-l),
  replace timeout flat-sleep with task-await/cancel (P1-n).

### Q4 — Wired-or-delete · ✅ DECIDED
**DELETE (4 dead items):** `Intent.session_id` (use `context.session_id` per Q2; it's data-contract drift) ·
`MemoryManager` (P0-7 — its job is now Q2's idle-timeout+history-window + Q3's action-store reaper) · `ContextLayer`/
progressive-context (`resolve_context`/`resolve_layered_context`/`get_contextual_summary` — dead, never wired) ·
`_disambiguate_with_device_context` (P1-g/QUAL-22 — dead + EN-hardcoded; fold the *intent* into the Q6 device rework).
**WIRE (not delete):** the `asr_output`/`tts_input` text-proc stages — `tts_input` is required for the TTS-normalization
fix (P0-5); handled as QUAL-13 stage-routing (Q9).
**WebSocket input = BUILD (first-class), NOT delete — KEY ARCHITECTURE DECISION (user):** WebSocket is the **primary
ESP32 transport**. Design: **wake word runs on-device (ESP32)** → device streams audio over WS (`skip_wake_word=True`
server-side) → server ASR → pipeline. The WS connection is also where the device **registers its physical identity**
(room + `available_devices`) into `ClientRegistry` — i.e. WS is the linchpin that finally populates the Q2/Q3
physical-identity store (resolves P1-j device starvation at its root). The current dead `InputManager._input_queue` +
base64 `AUDIO_DATA:` path (P0-8) is a broken placeholder to be **replaced by a proper WS streaming driving adapter**,
not revived. Server-side voice-trigger (and the `WakeWordResult.word`/`.wake_word` bug P1-b) is only for *non-ESP32*
local-mic deployments. **Needs a design session** — intertwined with **ARCH-6** (input seam) + **ARCH-7** (output
seam / audio-response-back-to-ESP32 + MQTT smart-home actuation). **Action (→ Q10):** reframe/expand **ARCH-6** into
"WebSocket streaming-input driving adapter (primary ESP32 transport) + ClientRegistry registration handshake"; flag a
design session; note two output channels for ESP32 (WS audio response + MQTT device control) feed ARCH-7.

### Q5 — Conversation history · ✅ DECIDED (by consequence of Q1+Q2+Q3)
No new deliberation — determined by earlier calls: **text stored = original utterance** (Q1); **history on the
short-lived conversation session, sliding-window N=15** (Q2); **single writer at the workflow funnel** (Q3's 3c
principle). Residual resolved by single-source-of-truth: **one structured turn log** (keep `conversation_history`'s
structured rows: original user_text, response, intent, timestamp); the LLM `messages` list is a **derived projection**;
**delete the legacy `history` list** and the orchestrator's `add_user_turn`/`add_assistant_turn` double-write.
**Action (→ Q10, into QUAL-9/11):** collapse the 3 writers into one `record_turn(...)` on the conversation context
(which applies the Q2 window); history-write moves out of the domain orchestrator into the application/workflow layer.

### Q6 — Device-context pipeline · ✅ DECIDED
- **`ClientRegistry` = single source of device truth.** No registration → no device inventory → device resolution
  returns a clean "no devices known for this room" (fail-loud, never crash/guess; de-fatalizes the PEX device P0).
  Populated by the entry adapter — primarily the **ESP32/WS registration handshake** (Q4), or REST `room_alias`.
- **"Requires room context" is DECLARED, not guessed.** Today it's a brittle heuristic
  (`entity_resolver._is_device_entity`: `intent.domain ∈ {device,smart_home,iot,home_automation}` OR entity-name
  substring patterns) — **delete that** + the hardcoded device-domain set.
- **Declaration lives in the donation, made first-class via the format split (Option B):**
  - **Per-parameter `entity_type`** on `ParameterSpec` (`device | location | room | person | generic`; required when
    `type=ENTITY`) → selects the resolver.
  - **Per-method `room_context` tri-state** (`required | none | conditional`) → enforcement policy.
    `required` = always resolve or fail-loud; `none` = skip; **`conditional`** = resolve **iff the request carries room
    context** (ESP32/WS registration *or* explicit REST `room_alias`), else skip with no failure — only hard-fails when
    room context IS present but the device can't be matched. *(Working definition; user to confirm vs strictly
    transport-keyed.)*
- **DONATION FORMAT SPLIT FIRST (Option B, user).** Verified: `ParameterSpec` (incl. `type`) is **duplicated across
  per-language files today**, policed by `cross_language_validator` (a band-aid). Split into: **language-neutral
  contract** (method list + invariant `ParameterSpec` core: name/type/entity_type/required/choices/min-max + the
  `room_context` flag) + **per-language files** (phrases/lemmas/token_patterns/slot_patterns + language-specific
  `extraction_patterns`/`aliases`). Gives `entity_type`/`room_context` **one home — inconsistency impossible by
  construction**; shrinks the validator to "every method has phrasings per language"; simplifies the [DEDITOR] UI.
- **Spawns (→ Q10): new task — "Donation format split (language-neutral contract + per-language phrasing)"** — touches
  the donation loader (`core/donations.py`, `core/intent_asset_loader.py`), schema (`assets/donations/v1.0.json`→v1.1),
  all donation files, `cross_language_validator`, DOC-5b, DOC-7, and the config-ui editor (UI-1/2/3). **Precedes** the
  declarative device-resolution fix (entity_type/room_context born in the new contract). Fail-loud behavior → Q7.

### Q7 — Fail-loud philosophy + typed accessor · ✅ DECIDED
- **7a — one failure convention:** **raise structured domain exceptions** at the point of failure → **catch at ONE
  boundary** (handler-execute / orchestrator wrapper) → map to a typed `IntentResult`. No silent swallowing, no
  return-original-on-failure, no uncaught fatal crashes (the device resolver's `RuntimeError` becomes a structured,
  caught error). *(Chosen over a threaded `Result`/`Outcome` type — fits the existing try/except boundary, least churn.)*
- **7b — donation-driven typed accessor** on the handler base: reads `intent.entities` against the `ParameterSpec`
  (type/required/choices/min-max/default + Q6 `entity_type`/`room_context`); coerces, validates, **raises**
  `MissingRequiredParameter`/`InvalidParameter`/`UnresolvedDevice`. Replaces the ~11 hand-rolled `.get` sites + the
  dead `validate_entities` (P1-s); drives device/room resolution per the Q6 declarations.
- **7c — result contract:** `success=False` ⟹ **non-empty `error`** (base `_create_*_result` helpers enforce; the
  boundary auto-fills from the exception). Fixes P1-a + the forked `_create_error_result` signatures (P1-t).
- **7d — fail-loud manifests as conversational CLARIFICATION, not a terminal error or a silent guess.** The boundary
  converts structured failures (missing-required, unresolved device/room, **no-intent-identified**) into an
  **explain-and-ask** response: "fall back to conversation, explain the problem, ask for clarification." Also fix the
  fake `confidence=1.0` on the NLU fallback (P2).
- **Responder = CONFIGURABLE (user):** **if an LLM is present → use it** (natural clarification from the failure
  context); **else deterministic + localized** (templated from `ParameterSpec.description` + per-language prompt). The
  deterministic path always exists (offline guarantee); LLM is the enhancement — same offline-first/LLM-opt-in shape as
  QUAL-14/15.
- **Phasing (user):** **Grade 1 (single-turn explain-and-ask) → Gate 2** with the typed-accessor work (into QUAL-9/11).
  **Grade 2 (multi-turn slot-filling) → follow-up FEATURE TASK:** `pending_clarification` on the **conversation
  session** + `ConversationState = awaiting-clarification` + next-turn slot-fill + a pipeline pre-check (symmetric to
  the F&F `contextual` check — but on the transient conversation store, since a half-finished command should expire
  with the Q2 idle window). **`ConversationState` is KEPT** (gets a real job here) — only `ContextLayer` was deleted
  (Q4).
- **Symmetry:** F&F follow-up → `active_actions` on the **physical identity** (stable, Q3); clarification follow-up →
  `pending_clarification` on the **conversation session** (transient). **Spawns (→ Q10):** clarification responder
  (Gate 2, configurable LLM/deterministic) + multi-turn slot-filling feature task.

### Q8 — Shared-bases consolidations · ✅ DECIDED
**Already settled earlier:** F&F write-back → Q3 (one workflow-level path); `_create_error_result` → Q7c (unified
contract); handler-side extraction → Q7b (typed accessor). **Three remaining, all confirmed:**
1. **NLU provider extraction base** (P1-r) — one **shared, donation-`ParameterSpec`-driven** extraction contract both
   `hybrid_keyword_matcher` and `spacy_nlu` use, so extraction is provider-independent (fixes the DURATION divergence).
   → QUAL-11 [PEX].
2. **One LLM prompt source** (P1, triplicated) — **confirmed WITH the condition that centralization *is* the
   LLM-independent prompt-hardening layer**: written once, applied to all providers, using provider-agnostic
   techniques (instruction/data separation + delimited user content, no model-specific features), with **deterministic
   output validation + fail-safe fallback** (Q7) as the backstop and the offline path always available so prompts are
   never load-bearing. → QUAL-16 [PROMPTS].
3. **Collapse the 4 text processors** (P1-h) into one config-driven processor with stages wired (Q4) — **confirmed WITH
   the condition it covers normalization/lingua_franca:** verified `lingua_franca` is scattered across all 4 processors
   + `utils/text_processing.py` + the component, plus `Runorm` (Russian) in `tts`/`utils/text_normalizers.py`.
   Consolidate both into the unified processor's normalization layer **behind a normalization seam** that (a) contains
   the abandoned-MycroftAI `lingua_franca` debt in one place, (b) makes the eventual **OVOS migration a localized
   swap**, (c) selects multilingual vs Russian normalization per stage/language via config. → QUAL-13 [TXTPROC] +
   lingua-franca-techdebt.

### Q9 — Config-truth · ✅ DECIDED
**Deployment model confirmed (user):** `config-master.toml` = canonical fully-commented **superset** reference
(dev/test + docs; 57 `enabled=true` / 20 `enabled=false` — a *curated* superset, not blindly-all-on); **real
deployments use a minimal config** with only needed components (already exist: `minimal/api-only/voice/full/
embedded-armv7/development.toml`; profile auto-detected by `get_deployment_profile()`; `REL-2` finalizes the canonical
minimal starter).
- **9a — config-truth check is DEPLOYMENT-AWARE (refined):** two layers — (1) **schema-parity + no dead trees** (every
  key is schema-known; no config tree consumed by *no* codepath in *any* profile) applies to ALL configs incl.
  config-master; (2) **enabled-set resolvability** (every *enabled* component/provider/stage resolves to real code)
  applies per-loaded-config (QUAL-23, already deployment-aware). **NOT** "every key active this run" (would wrongly flag
  the superset). Extend QUAL-23 + add a schema↔model parity test.
- **9b — remove dead config trees** (`[text_processor.normalizers.*]`, `number_options`, …) now that Q8 defines the
  real normalization config.
- **9c — sync schema↔model drift** (e.g. `LLMConfig` catch-all `Dict` → typed; train-schedule nesting QUAL-7).
- **`language` (P1-i): WIRE, don't delete** — populate from the `ClientRegistry` client record / global config
  (deployment/client language), per-utterance detection as fallback/override. Consumed + robust + aligns with the
  per-language donation/normalization model.

### Q10 — Gate 2 framing + task numbering · ✅ DECIDED
- **Framing = HYBRID:** a short **4-theme cross-cutting principles block** (the lens) + **discrete numbered tasks**.
  Principles: **① fail-loud** · **② shared bases** · **③ config-truth (deployment-aware)** · **④ data-contract
  integrity**.
- **New tasks (foundational, land first):**
  - **QUAL-27** [DFLOW] — **Data-contract fixes:** `Intent.text`→`raw_text` (P0-1), `WakeWordResult.word` (P1-b),
    delete `Intent.session_id`, `IntentResult` error contract. Fast; unblocks the command surface. (Q1, theme ④)
  - **QUAL-28** [DFLOW] — **Context & session refactor:** split `UnifiedConversationContext` → physical-identity store
    + conversation session; zombie-resistant `action_name`-keyed **action store**; session lifecycle (idle-window
    T=10m/voice~5m, history window N=15); forbid `"default"`; `get`/`get_or_create`; kill `extract_room_from_session`.
    (Q2, Q3)
  - **QUAL-29** [DFLOW] — **Donation format split:** language-neutral contract + per-language phrasing; `entity_type` +
    `room_context` fields; schema v1.1; loader; validator. **Precedes declarative device-resolution.** (Q6)
  - **QUAL-30** [DFLOW] — **Clarification UX (Grade 1):** explain-and-ask at the fail-loud boundary; configurable
    LLM/deterministic responder. (Q7, theme ①)
  - **QUAL-31** [DFLOW] — **Multi-turn slot-filling (Grade 2, feature):** `pending_clarification` + `ConversationState`
    + next-turn slot-fill. (Q7)
- **Existing tasks updated:** QUAL-9 [FAF], QUAL-11 [PEX], QUAL-13 [TXTPROC], QUAL-15 [LLM], QUAL-16 [PROMPTS],
  QUAL-22, QUAL-23, DOC-7, DOC-8; **ARCH-6 reframed** → WebSocket ESP32 input adapter; **ARCH-7** → output seam (WS
  audio response + MQTT).
- **Sequencing (Gate 2):** QUAL-27 (fast data-contract) → QUAL-29 (donation split) + QUAL-28 (context/action) as the
  foundation → per-subsystem QUAL-9/11/13/15/16 + QUAL-30 on top → QUAL-31 + ARCH-6/7 design sessions later.

---

## Outcome
All 10 issues decided. The reconciliation upheld the four review docs' findings and added a 4th cross-cutting theme
(**data-contract integrity**). The biggest single fix is **P0-1** (`Intent.text`→`raw_text`). The largest structural
move is the **Q2 context split** (physical-identity store vs conversation session) which unblocks F&F follow-ups,
the room/device pipeline, and the eventual ESP32-WS + MQTT story. Gate 2 framing finalized → written to
`RELEASE_PLAN.md` (principles block + QUAL-27…31 + updated tasks). **QUAL-26 DONE.**


