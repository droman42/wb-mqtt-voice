# Text-Processing Subsystem Review — QUAL-12 [TXTPROC]

**Status:** complete (2026-06-01). **Backs:** QUAL-13 (refactor). **Relates:** ASSET-3 (lingua-franca), QUAL-14/15 [LLM] (the LLM-text-processing question), QUAL-11 (config-names-don't-resolve pattern).
**Method:** three parallel deep-reads (providers+pipeline · normalizers+config+redundancy · the LLM question), then synthesis. Structural headline spot-verified directly.

---

## TL;DR — verdict

**The text-processing subsystem is mostly decorative at runtime.** It ships 4 providers, 3 normalizers, a stage-routing system, and a parallel config tree — but in the running pipeline **exactly one path executes**: `process()` is hardcoded to stage `"general"`, so only `general_text_processor` (Number + Prepare normalizers) ever runs, and it runs on **ASR output** (despite the `"general"` name). The two stages the architecture is ostensibly built around — `asr_output` and `tts_input` — are never routed; the TTS path synthesizes raw text with no normalization at all; the entire text-processing WebAPI 500s on a phantom attribute; and one of the two config trees is dead. It's an over-engineered shell around a single number-normalizing call.

**Severity tally:** 5 × P0, 6 × P1, 6 × P2 (ASSET-3 tracked separately).

### Themes
1. **The stage architecture is bypassed.** `process()` always passes `"general"`; the `asr_output`/`tts_input`/`number_processing`/`command_input` stages are dead routing. Only `general_text_processor` is reachable.
2. **TTS gets no text processing.** The only call site is ASR→NLU (`voice_assistant.py:383`); TTS synthesizes `result.text` raw (`:707`). So `tts_text_processor`, `RunormNormalizer`, and all advanced Russian TTS normalization are dead at runtime (and the provider is `enabled=false` anyway).
3. **Two divergent config trees, one dead.** `[text_processor.normalizers.*].stages` (the per-stage/enabled tree) is **never read**; providers read `[text_processor.providers.*.*_options]`. Editing the normalizer stage config is a silent no-op.
4. **Redundant / broken providers.** `asr_text_processor` and `number_text_processor` are functionally identical (NumberNormalizer-only); `number_text_processor` is unreachable via the pipeline; `NumberTextProcessor.process()` calls a non-existent method; the WebAPI references an unassigned `self.processor`.
5. **Misleading config & deps.** `number_options` (fractions/ordinals/ranges) describe logic that doesn't exist; providers claim to "require lingua-franca" but degrade without it; `RunormNormalizer` downloads a HF model at runtime (offline hazard); lingua-franca is the abandoned-git ASSET-3 pin.

---

## The subsystem as-built

| Provider | Normalizers | Declared stage | Reachable at runtime? | Default |
|---|---|---|---|---|
| `asr_text_processor` | NumberNormalizer | `asr_output` | **No** — `process()` never passes `asr_output` | enabled |
| `general_text_processor` | Number + Prepare | `general` | **Yes — the only live one** | enabled |
| `tts_text_processor` | Number + Prepare + Runorm | `tts_input` | **No** — no TTS call site + `enabled=false` | disabled |
| `number_text_processor` | NumberNormalizer | (all, but unmapped) | **No** — absent from `improve()` stage map | enabled |

**Normalizers** (`irene/utils/text_normalizers.py`): `NumberNormalizer` (number→words via lingua-franca + a ru-only pure-Python fallback), `PrepareNormalizer` (symbol→word, Latin→Cyrillic via eng-to-ipa), `RunormNormalizer` (advanced Russian TTS normalization via `runorm`, **downloads a HuggingFace model on first call** — `text_normalizers.py:273`).

**Runtime path (verified):** `process(text, context, trace)` → hardcodes `improve(text, context, "general")` (`text_processor_component.py:123,133`) → `stage_provider_map["general"]` → `general_text_processor.process_pipeline(text, "general")` → Number + Prepare normalization. That is the entire live behavior.

### The double-routing
- **(a) Provider-per-stage classes** — each provider hardcodes its stage in `get_supported_stages()` and the component maps stage→provider in `improve()` (`text_processor_component.py:221-225`). **This is the only mechanism that runs** — but it's defeated by `process()` always passing `"general"`.
- **(b) Config `[text_processor.normalizers.*].stages`** (`config-master.toml:378-392`) — never read by the provider/component path (`initialize()` reads only `config["providers"]`, `:61`). Confirmed dead: the only readers are TOML-generation, v13→v14 migration, and a config-echo log. **Editing it has zero runtime effect.**

The two trees also **disagree** (config binds normalizers to stage-lists; provider classes bind whole normalizer-sets to single stages) — but since (b) is dead, the disagreement is silent.

---

## The LLM-for-text-processing question (your added question)

**Can the LLM be used for text processing, if configured? — Yes architecturally; no, it isn't wired today; and it should only ever be an opt-in, online-only stage.**

- **What exists:** all three LLM providers define an `improve_speech_recognition` task (plus `grammar_correction`, `summarize`, etc.) reachable via `LLMComponent.enhance_text(text, task=...)` (`openai.py:162`, etc.). That is the conceptual surface for LLM text cleanup.
- **What's wired:** **nothing.** The only hook is the **dead** ASR-enhancement path — `asr_component.py:595` looks up `plugin_manager.get_plugin("universal_llm")`, a name **never registered** (a v13→v14 migration leftover; the LLM is the `'llm'` *component*, not a plugin), so it's a permanent no-op. There is no path from the text-processing pipeline into the LLM.
- **Could a provider be LLM-backed?** **Yes, cleanly.** The provider contract is minimal (`process_pipeline(text, stage)` + `get_supported_stages()`, `base.py:33-46`); discovery is entry-point + config driven (`text_processor_component.py:64-72`); and there's a DI injection point (`get_service_dependencies`, `:505-518`). A `llm_text_processor` claiming the `asr_output` stage and delegating to `enhance_text(..., "improve_speech_recognition")` would need no core changes.
- **`asr_text_processor` vs `improve_speech_recognition`:** complementary, not redundant. The deterministic processor only normalizes numbers (despite its name); the LLM task is the broad homophone/segmentation/grammar correction the name implies but the code never delivers.
- **Offline-first constraint:** all LLM providers are cloud and the `console` fallback is a phantom (QUAL-14), so an LLM text processor unconditionally needs internet.

**Recommendation:** permit it as a **separate, disabled-by-default, online-only `llm_text_processor`** on the `asr_output` stage, gated on a configured cloud (or future local — ARCH-9/10 [INFER]) LLM, **augmenting never replacing** the always-on deterministic default, and preserving original text alongside enhanced (the shape the dead ASR `enhance` flag already intended). As prerequisites: fix/remove the dead `universal_llm` path and implement-or-remove the phantom `console` LLM (QUAL-15). **Do not** put an LLM on the default text-processing path.

---

## Findings

- **[P0]** **`process()` is stage-blind** — always passes `"general"` (`text_processor_component.py:123,133`), so `improve()` can only ever select `general_text_processor`. `asr_text_processor`/`tts_text_processor` are unreachable via the public entry; the stage system is decorative. *(verified)*
- **[P0]** **TTS path has no text processing** — the only `text_processor.process` call site is `voice_assistant.py:383` (ASR→NLU); TTS synthesizes `result.text` raw (`:707`). `tts_input` stage, `tts_text_processor`, and `RunormNormalizer` are dead at runtime. *(verified)*
- **[P0]** **Text-processing WebAPI is broken** — `/text_processing/process`, `/normalizers`, `/config` reference `self.processor.normalizers` / `normalizer.applies_to_stage(...)` (`text_processor_component.py:359,391,412`), but `self.processor` is **never assigned** and no normalizer defines `applies_to_stage` → `AttributeError`/HTTP 500. *(verified)*
- **[P0]** **Dead config tree** — `[text_processor.normalizers.*].stages`/`enabled` (`config-master.toml:375-392`) is never consumed at runtime; operators tuning it get silent no-ops.
- **[P0]** **`NumberTextProcessor.process()` calls a non-existent method** — `number_text_processor.py:328` calls `self.process_numbers()`; only `process_numbers_only` exists → `AttributeError` for any caller of `.process()`.
- **[P1]** **`number_text_processor` is redundant dead weight** — identical to `asr_text_processor` (NumberNormalizer-only) and absent from `improve()`'s stage map → unreachable via the pipeline; only the direct `normalize_numbers()` REST path hits it.
- **[P1]** **`number_options` parsed but never applied** — `handle_fractions/handle_ordinals/handle_ranges` (`config-master.toml:419-422`) are read into `self.number_options` but never wired into `NumberNormalizer`, which ignores everything but language; and the underlying `all_num_to_text` implements no fraction/ordinal logic. Misleading config surface.
- **[P1]** **`RunormNormalizer` downloads a HF model at runtime** (`text_normalizers.py:273`) — an undocumented network dependency for an offline assistant (and dead by default since its host is disabled).
- **[P1]** **`_stage_providers` is dead** — initialized `{}` and never populated (`text_processor_component.py:33`); the trace loop over it never runs, so `normalizers_applied` is always empty.
- **[P1]** **Dead `universal_llm` ASR-enhance path** (`asr_component.py:595`) — see the LLM section; permanent no-op.
- **[P1]** **ASSET-3** — `NumberNormalizer` → lingua-franca, the abandoned-MycroftAI git pin (`pyproject.toml:127`); ru-only fallback means a silent non-ru regression if the pin breaks. (Tracked as ASSET-3.)
- **[P2]** `command_input` stage declared (`config-master.toml:375`) with no provider mapping; stale double-negative fallback guard (`text_processor_component.py:68`); provider-stage mismatch only warns then processes anyway (stage arg is advisory); `context` param accepted by every provider but unused ("reserved for future" — the context-aware surface is a no-op); `requires_dependencies` claims lingua-franca is required but code degrades without it (inaccurate); `asr` vs `number` functionally identical.

---

## Keep / merge / collapse recommendation (→ QUAL-13)

The subsystem has **two legitimately distinct real needs** (number normalization for ASR output before NLU; full Russian normalization for TTS input) wrapped in **a non-functional abstraction**. Recommendation — **collapse + wire**:

1. **Collapse the 4 providers into ONE config-driven `TextProcessor`** that applies an **ordered, per-stage normalizer chain** read from config — i.e. make config-tree (b) *real* and delete mechanism (a) and the redundant `number`/`asr` provider split. Stages become data (`asr_output: [numbers]`, `tts_input: [numbers, prepare, runorm]`), not classes.
2. **Actually wire the two real stages:** `process(text, stage)` must pass the *caller's* stage — `asr_output` from `voice_assistant.py:383` (already the call site) — and **add the missing `tts_input` call** before TTS synthesis (`voice_assistant.py:707`). Without this the TTS normalization that justifies the whole subsystem never runs.
3. **Delete the dead:** the `[text_processor.normalizers.*]`-vs-`providers.*` duplication (keep one tree), the redundant `number_text_processor`, `_stage_providers`, the `self.processor` WebAPI bug, `NumberTextProcessor.process()`, and the `number_options` keys that map to nothing.
4. **Document the real deps:** RUNorm's runtime model download; lingua-franca's ru-only fallback; make `requires_dependencies` honest.
5. **LLM stage** — add (optionally) a disabled-by-default online `llm_text_processor` on `asr_output` per the LLM section; never on the default path.

Net: from 4 providers + 3 normalizers + 2 routing systems + a broken API → **one config-driven processor with explicit per-stage normalizer chains, both real stages wired, plus an optional online LLM stage.**

## Cross-references
- **QUAL-13** [TXTPROC] — execute the collapse+wire above.
- **ASSET-3** — lingua-franca migration (NumberNormalizer); coordinate.
- **QUAL-14/15 [LLM]** — the LLM-text-processing stage depends on a working LLM provider (the phantom `console` / local-LLM story).
- **QUAL-11** — same systemic bug class as the cascade-order and console-provider phantoms: **config names (stages/providers) that don't resolve at runtime**. Worth a shared "validate every configured name resolves" startup check.
