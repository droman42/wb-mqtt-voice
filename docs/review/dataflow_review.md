> **📄 FROZEN EVIDENCE — not the task ledger.** Findings/rationale below are a point-in-time record. The
> authoritative **scope + status** is [`docs/RELEASE_PLAN.md`](../RELEASE_PLAN.md); chronology is
> [`docs/RELEASE_JOURNAL.md`](../RELEASE_JOURNAL.md). Inline status notes here (DONE/✅/…) are **historical and NOT
> authoritative** — check the ledger for live status (Invariant #5/#6). Edit this file only to correct a *finding*.

# QUAL-25 [DFLOW] — End-to-end dataflow & context-models review

**Date:** 2026-06-02 · **Scope:** the full input→action→output pipeline of `irene/` · **Method:** five parallel
tracer agents (entry adapters · text-proc/NLU/orchestrator · handler boundary · fire-and-forget/output ·
context/session model lifecycle), each cross-referencing the four prior QUAL reviews, followed by an adversarial
verification pass on the headline NEW findings. **Read-only review — no code changed.**

This is the dataflow counterpart to the subsystem reviews (QUAL-8/10/12/14): instead of one subsystem, it traces a
single datum — a user utterance — from every entry modality through to its action/result/output, and asks *which
data object exists at each hop, what is created, and what is silently dropped*. As predicted, it both **confirms**
prior P0s from a flow angle and surfaces **new** cross-cutting defects the per-subsystem reviews could not see.

> **Re-categorization note:** this task began as DOC-8 ("write `DATA_MODELS.md`"). The user widened it to a full
> input→action flow analysis and made it a review (QUAL-25); `DATA_MODELS.md` (DOC-8) is now the downstream
> write-up that distills §2 below. The cross-review reconciliation (§4 + §6) is the agenda for **QUAL-26**.

---

## 0. Headline findings

1. **A field rename `Intent.text` → `Intent.raw_text` was never propagated — a large fraction of the command
   surface crashes with `AttributeError`, masked as a generic error.** `Intent` defines `raw_text`, **no `text`**
   (`intents/models.py:16-27`), yet `intent.text` is read at **14 unguarded sites across 7 handlers** plus
   `Intent(text=…)` in the orchestrator's contextual-resolution branch (`orchestrator.py:217`). TTS-speak,
   translation, text-enhance/correct, provider-switch, ASR-/audio-provider selection, and every disambiguated
   contextual command ("stop"/"pause"/"resume") raise before producing an `IntentResult`; the orchestrator's
   `try/except` (`orchestrator.py:315-341`) turns the crash into a vague "I encountered an error". **This is the
   single biggest NEW defect — three independent tracers found it — and it explains why the smoke test (timer/
   greeting, which don't read `intent.text`) stays green while much of the command surface is dead.**
2. **Fire-and-forget is broken end-to-end — confirmed still live, on the flow.** Timer launch `TypeError`
   (duplicate `session_id`), the store-by-`action_name` / remove-by-`domain` key mismatch that kills the *entire*
   completion lifecycle (metrics, notifications, timeout-cleanup, eviction all nested in the dead `if`), and the
   non-existent `get_or_create_context` completion call. (Confirms `fire_and_forget_review.md`.)
3. **`session_id="default"` collapses every request into one shared session — cross-request/room/user state leak.**
   All three entry constructors default `session_id="default"` (`workflow_manager.py:452/473/571`) and
   `RequestContext` only auto-mints a real id when `session_id is None` (`context_models.py:922`). Any caller that
   passes the literal `"default"` shares one `UnifiedConversationContext`: history, `active_actions`, devices, and
   room/client identity bleed between unrelated requests. (NEW.)
4. **TTS synthesizes raw, text-processing-unaware text** — the `tts_input` normalization stage never runs before
   synthesis (`voice_assistant.py:708`). Russian TTS gets un-normalized numbers/Latin/symbols. (Confirms
   `text_processing_review.md`.)
5. **Two whole subsystems are wired-but-dead on the flow:** the `InputManager._input_queue` / WebSocket
   `AUDIO_DATA:` input path (captured mic/web audio pushed to a queue nothing drains) and the `MemoryManager`
   cleanup loop (calls `should_trigger_cleanup`/`perform_cleanup`, which don't exist → no session eviction). (NEW.)
6. **The "happy path" that actually works is narrow:** text/voice → NLU → the handlers that read entities *only*
   (`greetings`, `datetime`, `random`, `conversation`, and `timer`'s entity branch). Everything that reaches for
   `intent.text`, fire-and-forget completion, wake-word detection, contextual commands, multi-session isolation, or
   TTS normalization is broken or dead.

**Verdict:** the dataflow has **~9 P0 defects** (≈4 confirmations of prior reviews, ≈5 NEW), **~20 P1s**, and a long
P2 tail. The recurring shape is the same one the four reviews named — *plumbed-but-dead / configured-but-unread /
built-then-dropped* — but the dataflow lens reveals it is **worse and more systemic than per-subsystem reviews
showed**: it is not four isolated subsystems each with a dead corner, it is one pipeline whose data contracts
(`Intent` fields, context scope, action keys, result fields) silently disagree at nearly every boundary.

---

## 1. The real end-to-end dataflow

Three entry methods on `UnifiedVoiceAssistantWorkflow` converge on `_process_pipeline(text)`; the tail fires
actions and (text-entry only) speaks. Each hop notes the live data object and what is dropped.

```
ENTRY A  Text/CLI/REST   process_text_input    RequestContext(source="text",  skip_wake_word=T, skip_asr=T)
ENTRY B  Web single audio process_audio_input   RequestContext(source="audio", skip_*=client flags); VAD bypassed
ENTRY C  Mic stream (VOSK) process_audio_stream  RequestContext(source="voice"/"audio_stream"); VAD-gated
         (dead: InputManager._input_queue, WebSocket AUDIO_DATA: — captured input dropped, §3 P0-8)
                                   │
   A,B,C ─────────────────────────┴──────► RequestContext  ──get_context_with_request_info──►  UnifiedConversationContext
                                                                                                (session-scoped, by session_id)
   _process_pipeline(text):
     1. Text Processing   text_processor.process(text) → improve(text,"general")   stage HARD-CODED "general";
                                                                                    asr_output/tts_input never routed;
                                                                                    context arg dropped            (§3 P1-h)
     2. NLU (always)      nlu.process → recognize_with_context → Intent            providers read ONLY context.session_id;
                                                                                    raw_text := PROCESSED text     (§3 P1-c)
     3. Execute (always)  orchestrator.execute(intent, ctx) → IntentResult         contextual branch Intent(text=) CRASHES (§3 P0-1);
                                                                                    handlers read intent.text → CRASH (§3 P0-1)
     4. F&F metadata      _process_action_metadata(result.action_metadata)         store by action_name; double write-back;
                          (+ workflow_manager._process_action_metadata_integration) completion lifecycle DEAD            (§3 P0-2/3/4)
     5. History update    add_user_turn + add_assistant_turn + add_to_history       SAME turn written 2–3×          (§3 P1-q)
   (TTS→Audio: ENTRY A only, if wants_audio && should_speak → _handle_tts_output)  synthesizes RAW result.text    (§3 P0-5)
```

**VAD (ENTRY C):** raw chunks → `UniversalAudioProcessor.process_audio_chunk` accumulates a `VoiceSegment`, which
goes to voice-trigger (wake-word mode) **or** straight to ASR (`skip_wake_word`). VAD is a segmentation/accumulation
*gate*, not a peer stage. **Wake-word mode itself is broken:** any detection reads `result.wake_word`, which doesn't
exist (`WakeWordResult.word`), → `AttributeError` (§3 P1-b). ENTRY B bypasses VAD entirely.

---

## 2. The model cast — lifecycle & the request-vs-session verdict (the DOC-8 spine)

| Model | Created (file:line) | Populated by | Read by | Scope | Dies when |
|---|---|---|---|---|---|
| **RequestContext** | `context_models.py:892`; built at entry `workflow_manager.py:450/517/605` | entry adapter from `client_context` (source, session_id, wants_audio, skip flags, client/room/device, language) | pipeline methods; `get_context_with_request_info` | **request** | when `process_*` returns (never stored) |
| **UnifiedConversationContext** | `context.py:90` (in `get_context`, on cache miss), keyed by session_id | `get_context_with_request_info` copies room/device/lang; handlers/orchestrator mutate history+actions | NLU, orchestrator, entity_resolver, handlers, MemoryManager | **session** | 1800s timeout / `clear_session` / **or never** (§3 P0-7) |
| **Intent** | NLU providers (`hybrid_keyword_matcher.py:775`, `spacy_provider.py:749`, `nlu_component.py:1025`); orchestrator `:213` | NLU recognition + entity enrichment | orchestrator, handlers, `add_user_turn` | **transient** | after `execute_intent` |
| **IntentResult** | handler `execute()`; orchestrator error path `:362` | handler logic; orchestrator adds `metadata["original_intent"]` | workflow (TTS, history), API response | **transient** | after workflow returns |
| **AudioData** | mic/file/VAD producers | raw bytes + sample params | voice_trigger, ASR, VAD | **transient** | after ASR |
| **WakeWordResult** | `microwakeword.py:269`, `openwakeword.py:299` (`word=`) | provider detection | `voice_assistant.py:588/608`, `voice_trigger_component.py:428/443` (as `.wake_word` → crash) | **transient** | after wake-word stage |
| **ConversationState** | enum default `IDLE` (`context_models.py:68`) | `transition_state` | state helpers | **session** | with context |
| **ContextLayer** | enum; never used as state | — | `resolve_context` (no live caller) | — | — (dead, §3 P2) |

**Request-scoped vs session-scoped — the verdict (resolves the DOC-8 question):**
- `RequestContext` is correctly **request-scoped**: per-utterance routing flags + the *identity keys* (session_id,
  client_id, room_name, device_context) used to look up/hydrate the session. Never persisted — correct.
- `UnifiedConversationContext` is the **session-scoped** store; the *only* bridge between the two is **`session_id`**.
- **The conflation lives in the bridge.** The `"default"` session_id default (§0.3) collapses the bridge, so
  request-scoped identity is lost and session state leaks. Separately, two hydration paths disagree:
  `get_context` (room-blind, `context.py:59`) vs `get_context_with_request_info` (room-aware, `:103`); the workflow
  uses the latter but the NLU API path, `add_user_turn/add_assistant_turn`, and disambiguation helpers use the
  former — so room/device context is present on one path and absent on the others.
- **`Intent.session_id` is duplicated, divergent state** (default `"default"`; hybrid matcher never sets it). All
  real work keys off `context.session_id`; `intent.session_id` is read only for metrics. Candidate for removal.

---

## 3. Findings (ranked, deduped across the five slices)

### P0 — breaks the flow or silently loses/corrupts data

- **P0-1 · `Intent.text` does not exist — 14 unguarded reads + an invalid constructor crash the command surface.**
  `intents/models.py:16-27` (no `text` field). Reads: `voice_synthesis_handler.py:94,159,200,217`;
  `translation_handler.py:90,136`; `text_enhancement_handler.py:87,127,169`; `provider_control_handler.py:91,129`;
  `speech_recognition_handler.py:116`; `audio_playback_handler.py:207`. Constructor:
  `orchestrator.py:217` `Intent(text=processed_intent.text, …)` (invalid attr **and** invalid kwarg). Note
  `voice_synthesis_handler.py:159` `intent.entities.get("text", intent.text)` crashes *even when the entity is
  present* (default is eagerly evaluated). `timer.py:160` `hasattr(intent,'text')` is permanently-dead-but-safe.
  *Impact:* TTS-speak, translation, text-enhance, provider-switch, ASR/audio provider, all contextual commands die →
  masked as generic error. **NEW** (verified against source).
- **P0-2 · Timer launch `TypeError` (duplicate `session_id`).** `base.py:126` passes `session_id=context.session_id`
  *and* `**kwargs`; timer sites also pass it: `timer.py:229,281,348`. Set-timer's `except ValueError`
  (`timer.py:246`) doesn't catch `TypeError`. *Impact:* timers/cancel-all/stop-all never start. **CONFIRMS** FAF P0.
- **P0-3 · Store-by-`action_name` / remove-by-`domain` mismatch kills the completion lifecycle.** Store
  `active_actions[action_name]` (`base.py:500`); remove `remove_completed_action(domain)` (`base.py:637`) always
  returns `False`, so metrics completion, notifications, and timeout-cleanup (nested in that `if`, `base.py:648-700`)
  never fire and entries never evict → unbounded `active_actions` leak; every reader sees actions as perpetually
  running. **CONFIRMS** FAF P0.
- **P0-4 · Completion callback calls non-existent `get_or_create_context`.** `base.py:634` (+ `:761`,
  `notifications.py:174,229`, `debug_tools.py:101`) → `AttributeError`, swallowed at `base.py:704`. The manager's
  `get_context` is already get-or-create. *Impact:* completion write-back dead even independent of P0-3.
  **CONFIRMS** FAF P0.
- **P0-5 · TTS synthesizes raw text** (`voice_assistant.py:708` synthesizes `result.text`; the only
  `text_processor.process` call is on ASR *input*, `:384`). `tts_input`/Runorm normalization never runs. *Impact:*
  un-normalized Russian TTS. **CONFIRMS** TXTPROC P0. *(Coupled fix: requires stage-routing — see P1-h.)*
- **P0-6 · `session_id="default"` collapses all sessions.** `workflow_manager.py:452/473/571` +
  `context_models.py:922` (auto-mint only when `None`). *Impact:* history/`active_actions`/devices/identity leak
  across unrelated requests, rooms, users; room-scoped F&F targets the wrong room. **CONTRADICTS** the
  room-scoped-session design contract (`context_models.py:41-44`). **NEW.**
- **P0-7 · `MemoryManager` cleanup loop is dead.** `memory_manager.py:199,203` call `context.should_trigger_cleanup()`
  / `context.perform_cleanup(...)`, which don't exist on `UnifiedConversationContext` → `AttributeError` per context,
  swallowed at `:219`. *Impact:* documented session eviction is a no-op; only crude per-list trims + the whole-session
  timeout bound memory. **NEW.**
- **P0-8 · Input-adapter queue is a dead seam — captured mic/web audio is dropped.** `InputManager._listen_to_source`
  fills `_input_queue` (`inputs/base.py:299-308`); nothing in `engine.py` drains it (only consumer is
  `examples/async_demo.py:81`). Auto-started mic (`base.py:204-233`) captures audio that the workflow never sees;
  the WebSocket path (`web.py:175-220`, incl. base64 `AUDIO_DATA:` at `:213`) ACKs commands/audio to the client and
  never processes them. Live input exists *only* via the VOSK runner's direct `process_audio_stream` and the REST
  endpoints' direct `process_text_input`. *Impact:* entire WebSocket + auto-start-mic input surface silently inert.
  **NEW.** *(Scope: VOSK/REST deployments unaffected; overlaps ARCH-6's dead-queue note.)*
- **P0-9 · Required parameters are never enforced — missing → silently guessed default.** `validate_entities`
  (`base.py:386`) has **0 call sites**; `timer.py:196`, `random_handler.py:191-199` (missing min/max → 1/100),
  `system.py:297` (missing language → 'ru') all guess. *Impact:* a garbled/absent required entity becomes a wrong
  action, never a user-visible failure — the core of the cross-cutting "fail-loud" issue. **CONFIRMS** PEX L4 P0.

### P1 — real inconsistency / divergence / scoped breakage

- **P1-a · `IntentResult` fields populated inconsistently.** `error` omitted on genuine failures
  (`timer.py:204-211`, `random_handler.py:179-183` return `success=False` with no `error`); `metadata` rich in
  datetime/random/translation but hardcoded `{}` for F&F results (`base.py:1035`); `action_metadata` set only by the
  3 F&F handlers; `confidence` forced 1.0/0.0 by base helpers regardless of intent confidence. *Impact:* consumers
  reading `result.error` get `None` for real failures. **NEW.**
- **P1-b · `WakeWordResult.wake_word` does not exist** (field is `word`); read at `voice_assistant.py:588,608`,
  `voice_trigger_component.py:428,443` → `AttributeError` on any detection. P1 (voice-trigger ships disabled). **NEW.**
- **P1-c · NLU stamps PROCESSED text into `Intent.raw_text`; history records the ORIGINAL** →
  `raw_text` (a misnomer) and history disagree (`hybrid_keyword_matcher.py:779`, `spacy_provider.py:753`;
  `voice_assistant.py:384` vs `:424`). LLM/chat handler interpolates the processed text into prompts. **NEW.**
- **P1-d · NLU recognition is context-blind.** Providers read only `context.session_id`
  (`hybrid_keyword_matcher.py:782`, `spacy_provider.py:703`); `recognize_with_context` sets `context.language` but
  spaCy re-detects it itself (`spacy_provider.py:707`). History, client, room, device capabilities are not consulted
  during recognition — only in post-hoc `_enhance_with_context`. **NEW / CONFIRMS** (LLM-free confirmed by LLM review).
- **P1-e · Default `provider_cascade_order` names three non-existent providers** (`nlu_component.py:381-383`:
  `keyword_matcher`, `spacy_rules_sm`, `spacy_semantic_md`); real entry-points are `hybrid_keyword_matcher`/
  `spacy_nlu`. Masked because shipped configs set the order explicitly. A config omitting the key → every utterance →
  `conversation.general`. **CONFIRMS** PEX/TXTPROC.
- **P1-f · Duplicate, divergent device resolution per request.** `_enhance_with_context` runs both the asset-driven
  `entity_resolver.resolve_entities` (`nlu_component.py:62`) and the hardcoded English-only `_resolve_device_entities`
  (`:88`). **CONFIRMS** PEX L3.
- **P1-g · `_disambiguate_with_device_context` is dead on the live path** — computes enhanced entities then
  `return intent` (the original); the rebuilt intent uses unchanged name/domain/action (`nlu_component.py:159-189`,
  `:107-116`). **CONFIRMS** PEX = QUAL-22.
- **P1-h · Text-processor stage system is decorative.** `process()` hardcodes stage `"general"` and drops the
  `context` arg (`text_processor_component.py:124,222-235`); `asr_output`/`tts_input` unreachable via the pipeline.
  **CONFIRMS** TXTPROC P0. *(Gates P0-5: TTS normalization can't work until stage-routing exists.)*
- **P1-i · `language` is plumbed end-to-end but never populated** — `RequestContext`/context propagate it
  (`context_models.py:905,941`; `context.py:146`), but no caller passes `language=` and `CommandRequest` has no such
  field. Always the `"ru"` default. **NEW.**
- **P1-j · `device_context`/`available_devices` never populated at any entry** → the device entity resolver (PEX's
  fatal-crash P0) is starved from the entry stage on. `workflow_manager.py:459/526/613` read a key no runner sets.
  **CONFIRMS** (upstream cause of the PEX device P0).
- **P1-k · Double write-back of `action_metadata`.** For text input, BOTH `voice_assistant._process_action_metadata`
  (`:685`) and `workflow_manager._process_action_metadata_integration` (`:466`) run on the same result, enriching
  differently (room/session vs raw). State depends on order; both leak. **CONFIRMS** FAF P1 + NEW detail (both run).
- **P1-l · Metrics `_active_actions` keyed by `domain` only** (`metrics.py:100,196,215`) — two concurrent
  `domain="timers"` clobber each other. **CONFIRMS** FAF P1.
- **P1-m · Orphan completion task** — `asyncio.create_task` with no stored ref (`base.py:609`) → GC-cancellable.
  **CONFIRMS** FAF P1.
- **P1-n · Timeout monitor flat-sleeps the full timeout** (`base.py:749` `await asyncio.sleep(300)`) instead of
  awaiting the task; early-cancel depends on the dead `domain` lookup → zombie monitors. **CONFIRMS** FAF P1.
- **P1-o · `extract_room_from_session` mis-parses generated/CLI session ids as rooms** — digit-heuristic on the last
  8 chars (`session_manager.py:63-81`); an all-hex uuid8 (~1/17) makes `cli_<uuid8>` look like a room → phantom
  `client_id` injected into session context. **NEW / CONFIRMS** (FAF room correctness, new angle).
- **P1-p · `get_context` create-vs-fetch ambiguity + duplicate, disagreeing eviction.** No "require existing" mode
  (`context.py:59`); two cleanup loops gated on different clocks `last_updated` (`:258`) vs `last_activity` (`:967`),
  updated by different methods → premature/delayed eviction. **NEW.**
- **P1-q · Conversation history written 2–3× per turn.** `add_user_turn` (`orchestrator.py:297`, which also
  `add_to_history(…, "")`) + `add_assistant_turn` (`:298`) + workflow `add_to_history` (`voice_assistant.py:423`).
  `history` and `conversation_history` are parallel copies with three writers → double-counted LLM context, skewed
  metrics. **NEW** (the conversation turn is modeled twice).
- **P1-r · Same logical parameter extracted differently across handlers** (`text`, `provider`, `language` each read
  3–4 incompatible ways). E.g. `language`: `timer._get_language` Cyrillic-sniff vs `context.language or "ru"` vs
  `intent.entities.get('language','ru')`. **CONFIRMS** PEX "copy-paste-then-diverge".
- **P1-s · No typed accessor — ~11 handlers hand-roll `intent.entities.get(...)`** with per-call divergent defaults,
  inline `int()`-to-default coercion, and the crash-prone `.get("text", intent.text)` idiom. `extract_entity` used by
  1 handler; `validate_entities` by 0. **CONFIRMS** PEX remediation #6 (the typed-accessor gap).
- **P1-t · Two handlers override `_create_error_result` with an incompatible signature** (`(intent,context,error)`
  vs base `(text,error,metadata)`) — `translation_handler.py:214`, `text_enhancement_handler.py:243`. Latent footgun
  at the result-construction boundary. **NEW.**

### P2 — smells / cleanup (abbreviated)

Pipeline-internal metadata (`_recognition_provider`, `_cascade_attempts`, `original_text`, `_contextual_resolution`)
injected into the user-param `intent.entities` namespace (`nlu_component.py:876-877,1019`, `orchestrator.py:224`) —
indistinguishable from extracted params at the handler boundary (**CONFIRMS** PEX L4 P2) · fallback intent emitted
with `confidence=1.0` → corrupts recognition telemetry (`nlu_component.py:1028`) · `Intent.timestamp` refreshed on
cache hit, mutating a shared cached object (`nlu_component.py:833`) · two parallel "source" vocabularies
(`client_context.source` vs `RequestContext.source`) · `update_threshold` writes a read-only property
(`audio_processor.py:652`) · dead `ContextLayer`/`resolve_context`/`resolve_layered_context` machinery
(`context_models.py:785-887`) · `UnifiedConversationContext` is two merged models (`history`/`conversation_history`,
`metadata`/`client_metadata`, four near-duplicate clocks, per-session config blobs) · `disambiguation_context` added
via `setattr` on a dataclass (`context.py:881`) · `add_to_history` ignores configured `max_history_turns`
(`context_models.py:370` hardcodes 10) · `task_id=id(task)` unstable (`base.py:506`) · read-after-pop in completion
metrics (`base.py:652`) · timer dead text-parse fallback (`timer.py:200-202,160`) · `skip_asr` dropped on the
streaming `RequestContext` (`workflow_manager.py:605`) · `random_handler` max-default divergence (config on read,
literal 100 on coercion failure).

---

## 4. Cross-review reconciliation — what this review changes (the QUAL-26 agenda)

The dataflow lens **confirms** prior P0s and **adds** systemic ones the per-subsystem reviews could not see. Mapped
to the three cross-cutting themes already identified (see `irene-review-crosscutting`):

| Theme | What dataflow adds | New evidence |
|---|---|---|
| **Silent-failure → fail-loud** | The crashes are *masked*, not absent: `intent.text` (P0-1) and contextual-resolution (P0-1) AttributeErrors are swallowed into a generic "error"; F&F failures swallowed (P0-3/4); required params guessed (P0-9). A typed accessor (P1-s) + a real `error` contract (P1-a) + raising on missing-required is one fix. | P0-1, P0-9, P1-a, P1-s |
| **Copy-paste-diverge → shared bases** | Same param extracted 3–4 ways (P1-r); `_create_error_result` forked (P1-t); duplicate device resolution (P1-f); double F&F write-back (P1-k); history written by 3 sites (P1-q). | P1-f/k/q/r/t |
| **Config-that-lies → config-truth** | `provider_cascade_order` phantoms (P1-e); `language` plumbed-never-set (P1-i); `device_context` never populated (P1-j); `max_history_turns` ignored (P2); decorative stages (P1-h). | P1-e/h/i/j |
| **(NEW theme) Data-contract drift** | The reviews assumed the *models* were stable and hunted logic. The real rot is the **model contracts silently disagreeing**: `Intent.text` vs `raw_text` (P0-1), `WakeWordResult.word` vs `wake_word` (P1-b), action key `action_name` vs `domain` (P0-3), `session_id` scope (P0-6), `MemoryManager` vs context API (P0-7). These are rename/refactor residue that static checks (the relaxed pyright, Phase 0 §E) were configured not to see. | P0-1/3/6/7, P1-b |

**QUAL-26 must decide, per inconsistency, intended-behaviour-vs-today** (fix-to-intent / accept-current / redesign).
The high-stakes decisions: ① which field carries the *original* utterance (`raw_text` currently = processed text) —
this blocks P0-1's fix and QUAL-13; ② the canonical history representation (3 today); ③ the F&F keying scheme (store
by `action_name`, index by `domain`?) without breaking domain-based readers; ④ whether `Intent.session_id`,
`ContextLayer`/`ConversationState`, and `MemoryManager` are wired or deleted; ⑤ whether `InputManager`/WebSocket
input is revived or removed (overlaps ARCH-6).

---

## 5. The output seam (MQTT / non-audio)

There is **no `irene/outputs/` package and zero MQTT references** in `irene/`. Output is a single hardcoded modality:
`_handle_tts_output` (`voice_assistant.py:696-723`) — TTS-to-temp-file → local playback → unlink — invoked from
exactly one site (`:217`) on the **text-entry** path only, gated on `wants_audio && should_speak`. A non-audio/MQTT
output would attach at this same seam, but it is **inlined, not behind a port**; `RequestContext` has no
channel/modality field beyond `wants_audio`. This confirms the ARCH-7 [MQTT] design-session premise: the output-port
seam must be created (the F&F `notification_service` is the nearest async-push channel, but it is dead per P0-3).

---

## 6. Open questions for QUAL-26 (review-of-reviews)

1. **`Intent.text` → `raw_text`:** was `text` ever a field? If a rename, P0-1 has been crashing the command surface
   since then, uncaught because the smoke test covers only entity-only handlers. Decide the original-vs-processed
   text contract (Q①) before fixing.
2. **Does any contextual command execute end-to-end?** orchestrator.py:213 crashes on resolution — so FAF's
   "perpetually-running actions corrupt disambiguation" may be *moot* (disambiguation never completes). Reconcile.
3. **Canonical conversation history** (`history` vs `conversation_history` vs handler `messages`) and **single writer**
   (orchestrator vs workflow).
4. **Session identity:** forbid the literal `"default"`; split `get`/`get_or_create`; make `RequestContext` always
   derive a real session_id. Unify the two eviction clocks.
5. **F&F keying:** one key end-to-end (`action_name`) with a `domain` index for readers; fix duplicate-`session_id`
   and `get_or_create_context` together.
6. **Wired-or-delete decisions:** `MemoryManager`, `ContextLayer`/progressive-context, `InputManager` queue +
   WebSocket input, `Intent.session_id`, `_disambiguate_with_device_context`.
7. **Device pipeline:** who populates `device_context`/`available_devices` at the entry (P1-j) — required before the
   PEX device-resolution P0 can be fixed.

---

## 7. Tasks emitted to `RELEASE_PLAN.md`

- **QUAL-26** [DFLOW] — the review-of-reviews / reconciliation session consumes §4 + §6 (decide intended-vs-today,
  finalize Gate 2 framing, number the remediations). **Run next.**
- **DOC-8** — `DATA_MODELS.md` distilled from §2 (the model lifecycle table + the request-vs-session verdict).
- **New P0s for the Gate 2 remediation backlog** (to be numbered in QUAL-26): P0-1 (`Intent.text` field-contract
  fix — likely the highest-priority single fix), P0-6 (session_id default), P0-7 (MemoryManager), P0-8
  (InputManager/WebSocket input — coordinate with ARCH-6). P0-2/3/4/5/9 fold into the existing QUAL-9/13/15.
- Confirms and sharpens **QUAL-9** (FAF: P0-2/3/4, P1-k/l/m/n), **QUAL-11** (PEX: P0-9, P1-f/j/r/s), **QUAL-13**
  (TXTPROC: P0-5, P1-h), **QUAL-15** (LLM/raw_text), **QUAL-22** (P1-g), **ARCH-6** (P0-8), **ARCH-7** (§5 output seam).
