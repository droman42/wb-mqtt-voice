# Declared-but-unconsumed donation parameters — audit (→ QUAL-34)

**Question (user, 2026-06-03):** do the handlers actually consume every parameter their donations declare?
**Answer: No.** 19 of ~56 declared params across **11 of 14 handlers** are never read as `intent.entities[...]`.
Same bug class as QUAL-33 (datetime.format / system.info_type were declared but ignored) — but systemic.

## Method
For each handler's `contract.json`, collect declared param names (method + global); check whether the param
name appears in the handler's `.py`. "NO" is reliable — a handler cannot read a named entity without its name
string appearing. The **A/B bucket** below is tentative except where spot-verified; final classification is part
of the QUAL-34 triage.

## Two buckets
- **A — genuinely dead:** the feature isn't built; the handler does nothing with the intent's parameter
  (e.g. `datetime` reads zero entities). Disposition: **wire it** (build the feature, cf. QUAL-33 datetime.format)
  **or remove it** (don't declare what you don't serve, cf. QUAL-33 system configuration/logs).
- **B — bypassed:** the feature works, but the handler **re-parses `intent.raw_text`** instead of reading the
  NLU-extracted entity (e.g. `voice_synthesis` uses `voice_name` parsed from raw_text, ignoring the `voice` entity).
  Disposition: **migrate to the typed `ParameterSpec`-driven accessor — this is QUAL-11** (consume the declared
  entity, stop re-parsing). The audit's exact-name match under-counts Bucket B (it can't see `voice_name`-style vars).

## The 19 (handler.param · CHOICE? · bucket)
| Handler | Param | CHOICE | Bucket | Note |
|---|---|---|---|---|
| audio_playback | `file_path` | – | A? | |
| conversation | `topic` | – | A? | conversation likely LLM/raw_text-driven |
| conversation | `query_topic` | – | A? | |
| conversation | `context_reference` | – | A? | |
| datetime | `location` | – | A | datetime reads **zero** entities (confirmed) |
| datetime | `relative` | ✅ | A | canonical `[today,tomorrow,yesterday]`; dead (confirmed) |
| datetime | `timezone` | – | A | |
| greetings | `time_of_day` | ✅ | **A** | **confirmed dead** (not referenced) |
| greetings | `return_time` | – | A? | |
| system | `topic` | – | A? | |
| system | `component` | – | A? | |
| system_service | `component` | – | A? | |
| system_service | `metric_type` | ✅ | **A** | **confirmed dead** (not referenced) |
| system_service | `detailed` | – | A? | |
| text_enhancement | `improvement_type` | ✅ | **A** | **confirmed dead** (not referenced) |
| text_enhancement | `correction_type` | ✅ | A? | |
| timer | `retain` | – | A? | global param, unused |
| train_schedule | `language` | ✅ | A? | `language` is often context-derived, not an entity |
| voice_synthesis | `voice` | ✅ | **B** | **confirmed** — handled via `_extract_speech_parameters(raw_text)` |

7 of the 19 are CHOICE params (the most user-visible class). `language` appears as a CHOICE param in most
handlers but is typically satisfied by `context.language` (NLU-detected), not the declared entity — a related
sub-pattern worth deciding during triage.

## Coordination
- **Bucket B → QUAL-11** (typed accessor): the same "no typed accessor / param extracted N ways" finding
  (QUAL-25 P1-r/P1-s). QUAL-34 hands these to QUAL-11 rather than duplicating.
- **Bucket A → QUAL-34**: per-param wire-or-remove decisions (the QUAL-33 precedent: build the feature, or stop
  declaring it). For CHOICE params kept, author bilingual `choice_surfaces` (QUAL-29) so they're reachable.
- Re-run this audit after QUAL-11 + QUAL-34 land; the validator's surface-completeness check is a partial net.
