# QUAL-29 — CHOICE canonical-model decisions (interactive)

## Final model + build plan (validated against runtime consumption)
- **Model (assembled `ParameterSpec`):** `choices` = canonical tokens (from contract) + NEW `choice_surfaces:
  {canonical: [surface forms across all languages]}` (merged from lang files). Handlers switch on canonical;
  NLU matches surfaces → normalizes to canonical.
- **On disk:** contract param `choices` = canonical; lang param `choice_surfaces` = `{canonical: [this-language surfaces]}`.
  Free-entity params (translation.target_language) carry NO choices/surfaces.
- **Consumers (verified):** extraction match + validate at `hybrid_keyword_matcher.py:1094/1155` and
  `spacy_provider.py:867/905`. These get wired to match (canonical ∪ surfaces) → output canonical → validate vs canonical.
- **Why it's a real fix:** `provider_control_handler` already hardcodes RU→EN maps (`"аудио":"audio"`, `"модель":"llm"`)
  — today Russian CHOICE recognition leans on per-handler hacks; the canonical model centralizes it declaratively.
- **Build stages:** (1) model `choice_surfaces` → (2) migration script encodes all choice decisions + re-run →
  (3) loader assembles contract+lang (choices=canonical, choice_surfaces=merged) → (4) extraction ×2 providers
  (surface-match → canonical) → (5) validator shrink → (6) schemas (contract + language) → (7) config-ui (types/AJV/
  editors) → (8) file follow-ups (datetime/system handler wiring) → (9) verify + commit.


Building the canonical+surface model for `choices` (user decision: Option B). For each CHOICE param:
**contract** carries the language-neutral `choices` = canonical tokens; **per-language files** carry
`choice_surfaces` = `{canonical: [spoken surface forms]}`. The NLU matches surface forms → canonical;
handlers switch on canonical. (Surface→canonical extraction normalization is wired here or flagged for QUAL-11.)

## "Parallel" params — alignment verified (count parity ≠ alignment)

**6 clean (index-aligned; auto-derive: canonical = en, ru surface = ru[i], en surface = identity):**
- `datetime.relative`: today↔сегодня, tomorrow↔завтра, yesterday↔вчера
- `greetings.time_of_day`: morning↔утро, afternoon↔день, evening↔вечер, night↔ночь
- `speech_recognition.quality`: low↔низкое, medium↔среднее, high↔высокое, ultra↔максимальное
- `speech_recognition.provider`: whisper↔виспер, vosk↔воск, google_cloud↔гугл, azure↔облако
- `voice_synthesis.provider`: silero↔силеро, silero3↔силеро3, silero4↔силеро4, console↔консоль, system↔системный, vosk↔воск
- `voice_synthesis.voice`: xenia↔ксения, aidar↔айдар, silero↔силеро, console↔консоль, system↔системный

**`provider_control.component` (×2) — MISALIGNED by order; semantic remap (DONE):**
canonical = en `[audio, llm, asr, tts, all]`; surfaces ru: audio→[аудио], llm→[модель], asr→[распознавание],
tts→[голос], all→[все]. en = identity.

**`text_enhancement.improvement_type` — Case 5 (DONE): UNION** canonical = `[grammar, style, clarity, general, vocabulary]`.
surfaces — en: identity + vocabulary→[vocabulary]; ru: grammar→[грамматика], style→[стиль], general→[общее],
clarity→[ясность], vocabulary→[словарь].

## Divergent (4 semantic cases — need per-case decision)

| # | Param (methods) | Handler use | en | ru | DECISION |
|---|---|---|---|---|---|
| 1 | `datetime.format` (current_time/date/datetime) | DEAD (no entity reads) | per-method sets | `[текст,аудио]` | **DONE — Option 3: define canonical per-method (en sets); ru `[текст,аудио]` was corruption, dropped. + FILE handler-wiring follow-up (genuine bug: datetime.py must consume `format`).** |

### Case 1 detail — datetime.format canonical (per method)
- `current_time.format` → canonical `[12hour, 24hour, verbose]`
- `current_date.format` → canonical `[short, full, iso, verbose]`
- `current_datetime.format` → canonical `[iso, readable, unix, verbose]`
- en surfaces = identity. **ru surfaces deferred** to the handler-wiring follow-up (param is dead today → no runtime impact; ru forms authored when the handler actually reads it). Until then ru `choice_surfaces` = `{}` (canonical falls back to itself).
- **Follow-up task:** datetime handler ignores ALL intent entities (formats only from locale templates) — wire it to consume `format` per the canonical set + author ru surfaces.
| 2 | `system.info_type` (info_request) | DEAD (ignored) | `[system,performance,configuration,logs]` | `[краткая,подробная,техническая]` | **DONE — Option 1: canonical = en category `[system,performance,configuration,logs]`; ru verbosity set dropped as corruption. ru surfaces deferred. + FILE handler-wiring follow-up (branch `_handle_info_request` on info_type).** |
| 3 | `speech.language` (switch_language) | → `asr.switch_language(value)` **(STUB — not implemented)** | `[spanish,russian,english,german,french]` | `[русский,английский,немецкий,французский]` | **DONE — Option 2: canonical = all 5 `[spanish,russian,english,german,french]`. Surfaces: en=identity; ru=`[испанский,русский,английский,немецкий,французский]` (added испанский).** |
| 4 | `translation.target_language` (translate_text/specific) | → `llm.enhance_text(target_language=value)` **(open-ended)** | `[spanish,french,german,chinese]` | `[русский,английский]` | **DONE — Option 1: drop the choices enum (free entity, entity_type=generic). LLM accepts any language; extraction via patterns/aliases. default_value stays per-language.** |
