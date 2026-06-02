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
| Q1 | **Text contract** — what does `Intent.raw_text` carry (original vs processed), and how is normalized text threaded? | P0-1 (biggest defect), P1-c, QUAL-13, the LLM/chat path | 🔵 OPEN |
| Q2 | **Session identity** — forbid `"default"`; `get` vs `get_or_create`; always derive a real session_id; unify eviction clocks | P0-6 (cross-request leak), P1-p | ⚪ pending |
| Q3 | **Fire-and-forget keying** — one key end-to-end (`action_name`) + a `domain` index; fix dup-`session_id` + `get_or_create_context` together | P0-2/3/4, P1-k/l/m/n | ⚪ pending |
| Q4 | **Wired-or-delete** — MemoryManager · ContextLayer/progressive-context · InputManager queue + WebSocket input · `Intent.session_id` · `_disambiguate_with_device_context` · dead text-proc stages | P0-7, P0-8, P1-g; scopes how much code is deleted vs fixed | ⚪ pending |
| Q5 | **Conversation history** — pick the canonical representation (3 today) and a single writer | P1-q | ⚪ pending |
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

<!-- Q1 ... -->
