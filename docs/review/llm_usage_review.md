> **📄 FROZEN EVIDENCE — not the task ledger.** Findings/rationale below are a point-in-time record. The
> authoritative **scope + status** is [`docs/RELEASE_PLAN.md`](../RELEASE_PLAN.md); chronology is
> [`docs/RELEASE_JOURNAL.md`](../RELEASE_JOURNAL.md). Inline status notes here (DONE/✅/…) are **historical and NOT
> authoritative** — check the ledger for live status (Invariant #5/#6). Edit this file only to correct a *finding*.

# LLM Usage & Offline-First Review — QUAL-14 [LLM]

**Status:** complete (2026-06-01). **Backs:** QUAL-15 (act-on), QUAL-16 [PROMPTS]. **Relates:** QUAL-11 (cascade-order P0), ARCH-9/10 [INFER] (a local-model runtime).
**Method:** three parallel deep-reads (LLM infra · use-sites/prompts · offline-first posture), then synthesis. Headline P0 (missing `console` LLM provider) spot-verified directly.

---

## TL;DR — verdict

**The offline-first posture is real for everything *except the LLM stage*, and the LLM stage's "offline fallback" is a phantom.** The deterministic pipeline — ASR (vosk), NLU (spaCy + keyword), and all recognized intent handlers — runs fully offline with the shipped defaults. NLU is **confirmed LLM-free**. But the LLM component is configured to fall back to a `console` provider **that does not exist**, `fallback_providers` is never actually used for runtime fallback, and the chat entry point hard-fails offline. The pipeline only survives offline because the conversation handler *independently* checks `is_available()` and drops to templates — a lucky guard, not a designed fallback.

**Severity tally:** 3 × P0, 9 × P1, 12 × P2.

### Themes
1. **The offline LLM fallback is fictional.** `console` LLM provider is referenced in every config but has no class/entry-point; `fallback_providers` is logged, never used; `generate_response` re-raises offline. An "offline-first" assistant has no working LLM offline.
2. **NLU is correctly LLM-free** — and the only "LLM in the understanding path" is the *conditional, degrades-offline* conversation fallback. The separation (deterministic offline NLU + optional online chat) is the posture working as intended.
3. **Prompts are immature and mostly inline.** Only the conversation handler has asset prompts; translation/enhancement prompts are **triplicated inline across the 3 providers**, language-locked to the provider (not the user), with bare one-line system prompts, no format/length guardrails (everything is spoken via TTS), and raw-user-text interpolation (injection surface). → QUAL-16.
4. **Silent-success failure modes.** `enhance_text` swallows provider errors and returns the *original* text, so a failed translation returns the untranslated input as a "successful" translation. ASR LLM-enhancement is dead code (wrong lookup). `task="correct"` silently degrades to "improve".
5. **Robustness gaps.** No timeouts on any LLM call; a new SDK client per request; `openai.is_available()` returns `True` even when the network probe fails.

---

## The LLM subsystem as-built

**Component API** (`irene/components/llm_component.py`): handlers call `enhance_text(text, task=...)` (`:156`) and `generate_response(messages=...)` (`:264`). Providers discovered via entry-points from the enabled list (`:114-132`); a provider is kept only if `await is_available()` passes.

**Providers** (entry-points: openai, vsegpt, anthropic — `pyproject.toml:213-215`):

| Provider | SDK | Internet | Default model | Notes |
|---|---|---|---|---|
| openai | `AsyncOpenAI` | runtime | `gpt-4o-mini` (provider) / `gpt-4o` (TOML) | shipped `default_provider` |
| anthropic | `AsyncAnthropic` | runtime | claude-* | `enabled=false`; **ignores** configured `base_url` |
| vsegpt | `AsyncOpenAI`→api.vsegpt.ru | runtime | `openai/gpt-4o-mini` | Russian gateway; `enabled=false` |
| **console** | — | — | — | **DOES NOT EXIST** — no `console.py`, no entry-point, not in `llm/__init__.py`; yet `[llm.providers.console]` + `fallback_providers=["console"]` are configured |

**Fallback reality:** `fallback_providers` (config) is **never consumed at runtime** — it's only logged in `/configure` (`llm_component.py:572-574`). When the chosen provider is missing, `enhance_text` picks `list(self.providers.keys())[0]` (arbitrary dict order, `:179`), and `generate_response` raises `ValueError` (`:298`). On a provider exception, `enhance_text` returns the original text (`:188-190`); `generate_response` **re-raises** (`:353`). Contrast TTS/audio/voice_trigger components, which all iterate `self.fallback_providers` for real.

---

## Offline-first posture

**NLU is LLM-free (confirmed).** Neither `spacy_provider.py` (`recognize()` `:676-756`, local spaCy) nor `hybrid_keyword_matcher.py` (regex + rapidfuzz, `:400-590`) nor `nlu_component.py` makes any LLM/network call. The *only* LLM-in-understanding is the low-confidence fallback: NLU emits `conversation.general` (`nlu_component.py:885-903`), and `ConversationIntentHandler.execute()` routes it to the LLM **only if `await llm_component.is_available()`** (`conversation.py:128-137`), else to offline templates (`_handle_fallback_without_llm` `:466`).

**Internet-dependency map** (download = one-time fetch, offline after cache; runtime = every request):

| Stage | OFFLINE (local) | ONLINE (runtime) |
|---|---|---|
| ASR | vosk, whisper | google_cloud |
| TTS | console, silero_v3*/v4, pyttsx, vosk | elevenlabs |
| NLU | spacy_nlu, hybrid_keyword_matcher | — |
| voice_trigger | openwakeword, microwakeword | — |
| LLM | **(none — `console` missing)** | openai, anthropic, vsegpt |

\* `silero_v3.is_available()` does a live `requests.head(model_url, timeout=5)` (`tts/silero_v3.py:139-141`) — an availability probe that blocks on the network, unlike v4 which checks locally (`:81-83`).

**End-to-end offline?** **Yes for recognized intents; the LLM stage is the only gap.** Shipped defaults: ASR=vosk (offline), NLU=hybrid_keyword_matcher (offline), TTS/audio=console (offline), LLM=openai+`["console"]` fallback. Offline, `openai.is_available()` is false and the `console` fallback doesn't exist → LLM component has **zero usable providers**. The pipeline survives only because `conversation.py:134-137` independently template-falls-back. All recognized intents (timer, datetime, system, greetings, …) work fully offline. Caveats: ASR `fallback_providers=["whisper"]` but whisper is `enabled=false` (dead fallback); air-gapped installs need models pre-staged (download-time internet is undocumented in config).

---

## The NLU-LLM question — recommendation

**Should NLU use an LLM? — Not as a default, and not cloud. Keep NLU deterministic and offline-first; treat any LLM assist as an opt-in, local-only future layer.**

Reasoning, grounded in the code:
- **The current design is correct for the product.** Deterministic offline NLU handles recognized commands; the LLM is an optional online enhancement for open-ended chat only, behind an `is_available()` gate that degrades to templates. That *is* offline-first working.
- **"LLM NLU" today literally means "cloud NLU."** There is no local LLM provider (the `console` LLM is a phantom; openai/anthropic/vsegpt are all cloud). Routing understanding through them would break the core offline promise and add per-request cost/latency.
- **But there is a real gap an LLM could fill** — the low-confidence path already dumps everything to `conversation.general`, and parameter extraction is brittle (see QUAL-10: first-match heuristics, fixed token lists, no slot patterns). An LLM is genuinely better at slot-filling and paraphrase.
- **Therefore:** (1) fix the offline-first *foundation* first — implement a real local/console LLM fallback so "offline LLM" stops being fictional; (2) fix parameter extraction deterministically (QUAL-11) before reaching for an LLM; (3) only then consider an **optional, opt-in, local LLM** (llama.cpp/ollama-class) NLU-assist for low-confidence utterances, never as the default and never cloud. This pairs naturally with **ARCH-9/10 [INFER]** (a local-model runtime already entering the architecture) — a local LLM provider would both unblock offline LLM *and* enable opt-in LLM-assist without a cloud dependency.

---

## Findings

### Offline-first / infrastructure
- **[P0]** **`console` LLM provider does not exist** — no `irene/providers/llm/console.py`, no entry-point (`pyproject.toml:213-215`), not in `llm/__init__.py`; yet it's the configured `fallback_providers`/`[llm.providers.console]` in every config (`config-master.toml:242,276`). The declared offline fallback is a phantom; `discover_providers` silently drops it. *(verified)*
- **[P0]** **`fallback_providers` is never used for runtime fallback** — only logged in `/configure` (`llm_component.py:572-574`); the real "fallback" is `list(self.providers.keys())[0]` (`:179,208`), arbitrary order. Unlike TTS/audio/voice_trigger.
- **[P0]** **`generate_response` hard-fails offline** — missing provider → `ValueError` (`:298,333`); call exception → re-raise (`:353`). The chat entry point has no graceful offline path for an offline-first assistant.
- **[P1]** **`openai.is_available()` returns `True` on network failure** during the `models.list()` probe (`openai.py:130-138`) — an offline-but-keyed provider loads, then every call fails at runtime instead of being excluded at init.
- **[P1]** **No timeouts anywhere** — all SDK clients built without `timeout=` (`openai.py:102,177,235`; anthropic `:104,130`; vsegpt `:112,138`); an offline call can hang on SDK defaults.
- **[P1]** **New SDK client per call** (same lines) — no reuse/pooling.
- **[P1]** **`silero_v3.is_available()` does a live network HEAD** (`tts/silero_v3.py:139-141`) — availability blocks on the network; v4 is net-free. Offline-first violation + 5s stall.
- **[P2]** ASR fallback chain dead (`config-master.toml:203` whisper, but whisper `enabled=false` `:212`); config drift (`api_key`/`model`/sampling params in TOML vs `api_key_env`/`default_model` read by providers, sampling params ignored, `LLMConfig` is a loose `Dict`); anthropic ignores `base_url`; stale model defaults (provider vs TOML); bare `except` swallowing in init (`:135,145`); `initialize` only logs on failure so a broken LLM config never surfaces; unused `import asyncio` (anthropic/vsegpt); download-vs-runtime internet undocumented in config.

### Use-sites & prompts (→ QUAL-16 for the rewrite)
- **[P1]** **ASR LLM-enhancement is dead code** — `asr_component.py:595` calls `plugin_manager.get_plugin("universal_llm")`, but the LLM is a *component* (`'llm'`) and `"universal_llm"` is never a plugin → returns `None`; `enhance=True` post-ASR cleanup silently never runs.
- **[P1]** **`enhance_text` swallows failures → silent wrong success** — returns the original text on provider error (`llm_component.py:183,190,228`); for translation (`translation_handler.py:97`) a failure returns the *untranslated input* as a successful "translation".
- **[P1]** **Inline prompts, triplicated and provider-language-locked** — the real translation/enhancement task prompts live inline in `openai.py:161` (en), `anthropic.py:88` (en), `vsegpt.py:95` (ru), three divergent copies; language follows the *provider*, not the user (`context.language`). Only the conversation handler has asset prompts (`assets/prompts/conversation_handler/{ru,en}.yaml`). Contradicts handler docstrings claiming externalization.
- **[P1]** **Prompt-injection surface** — `reference_template` does `template.format(query)` with raw `intent.raw_text` (`conversation.py:349-350`); `translation` interpolates user-derived `target_language` (`openai.py:173`); bare one-line system prompts give no instruction-hierarchy defense.
- **[P2]** `task="correct"` (`text_enhancement_handler.py:174`) isn't a defined prompt key → silently falls to "improve" (`openai.py:170`); inconsistent availability checks (conversation uses `is_available()`, translation/enhancement use null-checks only); bare system prompts have no length/"no-markdown" constraint though output is spoken; hardcoded-English context-injection system messages in a Russian-first assistant (`conversation.py:542-620`); stale path strings in error messages (`conversation.py:194,214`).

---

## Ranked remediation (feeds QUAL-15 / QUAL-16)

**P0 — offline-first foundation:**
1. **Implement a real local LLM fallback** (a `console`/echo provider at minimum, ideally a local-model provider — see ARCH-9/10 [INFER]) and register its entry-point, OR remove `console` from configs and explicitly document the LLM stage as online-only with no fallback. Add a startup assertion that every configured `default_provider`/`fallback_providers` resolves to a discovered provider (same class of bug as QUAL-11's cascade-order).
2. **Make `fallback_providers` real** — iterate the configured chain on missing/failed provider (mirror TTS/audio), instead of `keys()[0]`.
3. **Give `generate_response` a graceful offline path** — return a clean "LLM unavailable" outcome instead of raising; unify with `enhance_text`'s degradation but *signal* failure rather than silently returning the input.

**P1:** fix `openai.is_available()` to a local check; add per-call timeouts + client reuse; fix the dead ASR `universal_llm` lookup (use the `'llm'` component or remove); stop `enhance_text` masking failures (return a typed failure, not the original text); fix `silero_v3.is_available()` to a local check.

**P2 (→ QUAL-16 [PROMPTS] for the prompt items):** externalize + de-duplicate the inline task prompts into `assets/prompts/` keyed by user language; harden system prompts (guardrails, output-format/length, "no markdown — spoken", injection resistance); fix `task="correct"`; unify availability checks; clean config drift / stale models / dead asyncio imports / stale path strings.

## Cross-references
- **QUAL-15** — execute the P0/P1 remediation (offline-first foundation first).
- **QUAL-16 [PROMPTS]** — owns the prompt rewrite/externalization/hardening (this review is the inventory).
- **QUAL-11** — the missing-console-provider and assert-providers-exist fix is the same family as the cascade-order P0.
- **ARCH-9/10 [INFER]** — a local-model runtime is the clean way to make "offline LLM" and an optional local LLM-NLU assist real without cloud.

## Verification (TEST-0, 2026-06-01)
- **Guarded by TEST-0** (`irene/tests/test_smoke_e2e.py::test_conversation_offline_degrades_gracefully`): with the
  LLM unavailable offline (no key / phantom `console` provider), an open-ended request returns HTTP 200 + a
  non-empty response (the conversation handler's `is_available()` template/canned fallback) rather than crashing.
  This pins the *graceful-degradation* invariant — QUAL-15 must keep this green while implementing the real
  fallback. (Note: the response today is a canned "Sorry, I couldn't process that request." — degradation works,
  quality is the QUAL-15/16 story.)
- **Now guarded by QUAL-23** (`irene/core/startup_validation.py`): the phantom `console` LLM provider is flagged at
  startup with a clear ERROR (`llm.fallback_providers` + `llm.providers (enabled)`), and `IRENE_STARTUP_STRICT=1`
  turns it into a boot failure. QUAL-15 is *not done* until that startup ERROR clears (implement the provider or
  remove it from configs).
