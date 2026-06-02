# QUAL-26 [DFLOW] — Review-of-reviews: reconciliation & decisions log

**Status:** 🟡 IN PROGRESS (started 2026-06-02) · **Format:** live Q&A session. Issues presented one at a time,
ordered by importance; each is **decided → actionable** before moving on. **This doc is the resume point** — it is
committed after every decision, so an interrupted session continues from the first `OPEN` row below.

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
| Q5 | **Conversation history** — pick the canonical representation (3 today) and a single writer | P1-q | 🔵 OPEN |
| Q6 | **Device-context pipeline** — who populates `device_context`/`available_devices` at the entry | P1-j (blocks the PEX device-resolution P0) | ⚪ pending |
| Q7 | **Fail-loud philosophy + typed accessor** (theme #1) — raise vs result-signal; where the typed entity/result accessor lives | P0-9, P1-a/s; the whole handler boundary | ⚪ pending |
| Q8 | **Shared-bases consolidations** (theme #2) — extraction base · prompt source · F&F write-back · collapse text processors · `_create_error_result` signature | P1-f/k/r/t | ⚪ pending |
| Q9 | **Config-truth scope** (theme #3) — cascade phantoms · `language` plumbing · dead config trees · schema↔model drift | P1-e/h/i, P2 tail | ⚪ pending |
| Q10 | **Gate 2 framing + numbering** (meta) — principles block vs discrete tasks (QUAL-27/28/…); number the new P0s | finalizes Gate 2 | ⚪ pending |

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

<!-- next: Q5 -->


