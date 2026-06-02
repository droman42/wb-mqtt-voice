> **📄 FROZEN EVIDENCE — not the task ledger.** Findings/rationale below are a point-in-time record. The
> authoritative **scope + status** is [`docs/RELEASE_PLAN.md`](../RELEASE_PLAN.md); chronology is
> [`docs/RELEASE_JOURNAL.md`](../RELEASE_JOURNAL.md). Inline status notes here (DONE/✅/…) are **historical and NOT
> authoritative** — check the ledger for live status (Invariant #5/#6). Edit this file only to correct a *finding*.

# Parameter Extraction Review — QUAL-10 [PEX]

**Status:** complete (2026-06-01). **Backs:** QUAL-11 (remediation), DOC-7 (guide), UI-1/2/3 [DEDITOR], TEST-4. **Relates:** QUAL-22 (confirmed here), ASSET-3 (number parsing).
**Method:** four parallel deep-reads (donation models · spaCy matching · entity resolvers · consumption/surfaces), then synthesis. Headline P0s spot-verified directly against source.

---

## TL;DR — verdict

**The "donation-driven parameter extraction" the docs describe is largely aspirational. In practice, extraction = generic spaCy NER + per-parameter regex + hardcoded heuristics, with no contract enforcement.** The richest, author-facing mechanisms are dead or stubbed, failures are swallowed silently, and the two NLU providers implement *different* extraction contracts — so the same utterance can yield different parameters depending on which provider wins the cascade. It mostly works for the shipped happy-path donations, but it is brittle, silently lossy, and a footgun for donation authors (which directly motivates the [DEDITOR] UI work).

**Severity tally:** 6 × P0, 11 × P1, 12 × P2.

### Five themes (the real story)
1. **The best extraction mechanisms are dead.** `slot_patterns`, `token_patterns`, and `ParameterSpec.extraction_patterns` are validated then discarded; spaCy parameter extraction self-describes as a "Phase 2" stub; context enhancement is a no-op. Authors can write rich donation patterns that silently do nothing.
2. **No contract enforcement.** Required-parameter failures never raise (the designed `ParameterExtractionError` is unused); per-parameter exceptions are swallowed; there is no typed accessor and no validation at the handler boundary. Missing/garbled params become silent wrong-action.
3. **Two providers, two contracts.** `spacy_nlu` and `hybrid_keyword_matcher` extract independently with different required/default/error semantics → non-deterministic parameter surface across the fallback cascade.
4. **Silent author footguns.** Unknown donation fields are accepted and dropped; spaCy patterns aren't structurally validated at load; the JSON schema has drifted from the Pydantic model.
5. **Inconsistent failure philosophy.** Device/room resolution *fatally crashes* the whole request if its asset loader isn't wired yet — while most of the rest of extraction *silently no-ops*. The two extremes coexist in one pipeline.

---

## The pipeline as-built (live vs dead)

```
utterance
  → NLUComponent.recognize()  [cascade: fast→slow, per-provider confidence gate]   nlu_component.py:840-877
     → provider.recognize_with_parameters()                                          base.py:85-106
        → recognize()            intent name + confidence
        → extract_parameters()   ParameterSpec loop → intent.entities.update(...)
  → ContextAwareNLUProcessor.process_with_context()  (context path)                  nlu_component.py:38
     → resolve_entities()  → writes {name}_resolved/_confidence/_resolution_type     entity_resolver.py:49-82
     → _disambiguate_with_device_context()  ← DEAD: computes then returns original   nlu_component.py:157-187
  → Intent(entities=enhanced_entities)
  → handler reads intent.entities.get(...)  [ad-hoc per handler]
```

**Live:** provider cascade + confidence gate; spaCy NER→type mapping + per-`ParameterSpec.pattern` regex; hybrid regex/fuzzy + `_extract_by_type`; the four entity resolvers (device/location/temporal/quantity); `resolve_entities` flat-key output.
**Dead / no-op:** `slot_patterns`, `token_patterns`, `ParameterSpec.extraction_patterns`; the compiled spaCy `Matcher`/`EntityRuler`; `_disambiguate_with_device_context` enhancement (output_capabilities / context_suggestion / preferred_output_device); `validate_entities`/`ParameterExtractionError`.

---

## Findings

### Layer 1 — donation & parameter models (`irene/core/donations.py`)
All models live in `donations.py` (not `intents/models.py`). `ParameterType` = 8 values (`string, integer, float, duration, datetime, boolean, choice, entity`, `:16-25`); `ParameterSpec` (`:28-57`) carries `type/required/default_value/choices/min_value/max_value/pattern/extraction_patterns/aliases`. Donations are `assets/donations/<handler>/<lang>.json` — **14 handlers × {en,ru} = 28 files**. Two-stage validation: JSON-schema (`assets/v1.0.json`) then Pydantic.

- **[P1]** Model/schema **drift on `language`**: JSON files + `assets/v1.0.json` carry a top-level `language`, but `HandlerDonation` has no such field (`donations.py:96-154`) — it's silently dropped; language is taken from the filename. Evidence the generated schema was hand-edited while the model wasn't.
- **[P1]** **Silent unknown-field acceptance**: no `model_config extra="forbid"` and the schema lacks `additionalProperties:false` — a typo like `"defualt_value"` validates clean and is dropped. Major author footgun.
- **[P1]** **Pydantic V1 `@validator`** (8×, `:46,52,89,121,128,136,142,149`) under pydantic≥2; deprecation is silenced project-wide (`pyproject.toml`), hiding the debt; breaks on v3.
- **[P2]** `assets/v1.0.json` is a generated artifact with **no committed regeneration script** → silent drift (the `language` mismatch already proves it).
- **[P2]** `validate_spacy_patterns` defaults **False** (`:178`) → `token/slot/extraction_patterns` (free-form `Dict[str,Any]`) never structurally validated at load; malformed patterns fail only at runtime.
- **[P2]** Three pattern fields split across two model levels (`extraction_patterns` on `ParameterSpec`; `token/slot_patterns` on `MethodDonation`) with overlapping intent — unclear which drives what.
- **[P2]** `default_value` (not `default`) is non-obvious; `min_value`/`max_value` used in only 2/28 files (near-dead); no validator forbids `pattern` on non-STRING / `choices` on non-CHOICE (stray fields silently ignored).

### Layer 2 — spaCy matching / extraction (`providers/nlu/{spacy_provider,hybrid_keyword_matcher,base}.py`, `components/nlu_component.py`)
- **[P0]** **Default cascade order names don't exist.** `nlu_component.py:380-381` defaults to `["keyword_matcher","spacy_rules_sm","spacy_semantic_md"]`; real entry-points are `hybrid_keyword_matcher`/`spacy_nlu` (`pyproject.toml:222-223`). The `keyword_matcher` fallback (`:394`) is also phantom. A config omitting `provider_cascade_order` → **no provider matches → every utterance falls to the generic fallback intent**. Masked only because shipped configs set the order explicitly (`config-master.toml:333`). *(verified)*
- **[P0]** **`slot_patterns`/`token_patterns` are validated then discarded.** `_validate_and_store_spacy_patterns` adds+removes token patterns purely to validate (`spacy_provider.py:1132-1141`); `slot_patterns` is iterated log-only (`:1144-1156`); both are copied into `advanced_patterns` (`:1161`) which **no runtime path ever reads**. `slot_patterns` — the one field designed for slot/parameter span extraction — is dead. *(verified)*
- **[P0]** **`ParameterSpec.extraction_patterns` is dead** — declared (`donations.py:43`) but hardcoded to `[]` (`spacy_provider.py:1162`) with no reader.
- **[P1]** **`_sm` spaCy models lack word vectors** → `doc.similarity` (classification `:969`, CHOICE extraction `:874`) degrades to ~0 → silent fallback to `conversation.general` / no CHOICE value. Only `_md` works as intended.
- **[P1]** **Brittle NER→type, first-match span→value** (`spacy_provider.py:827-841`, hybrid `numbers[0]` `:1080`): assumes the first entity is the right one and parses cleanly; Russian word-numerals don't `int()`; "2 часа 30 минут" collapses to one value with no association to the right `ParameterSpec`.
- **[P1]** **STRING extraction only returns quoted text or a literal alias** (hybrid `:1120-1129`) — no span-based free-text slot capture in either provider.
- **[P1]** **Required-param failures silent** (spaCy warns `:804`; hybrid never checks `required` `:1043-1059`).
- **[P1]** **`DURATION` inconsistent/lossy**: hybrid returns `{value,unit}` that `_convert_and_validate_parameter` has no branch for (`:1133-1159`); spaCy has no DURATION branch at all.
- **[P1]** **Perf**: `extract_parameters` reprocesses the full doc separately from `recognize` (`:792`); CHOICE calls `self.nlp(choice)` per choice per call (`:875`); `_classify_intent_similarity` is O(N·M) over every example doc on the hot path (`:967-970`).
- **[P2]** Hardcoded magic-number weights/thresholds, not config-driven; spaCy combined score weights sum to 0.85 not 1 (`:983`,`:999-1002`; hybrid `:718-721`).
- **[P2]** `matches[0]` arbitrary first-match in `_classify_intent_similarity` (`:959`); duplicated logic across the two providers (already diverged — see DURATION); spaCy model URL pins 3.7.0 while deps pin 3.8.0 (cache-key drift); empty `EntityRuler` added unconditionally, never populated, cold/warm pipeline composition differs.

### Layer 3 — entity resolvers (`irene/core/entity_resolver.py`, `components/nlu_component.py`)
Four resolvers under `ContextualEntityResolver`: Device (asset-driven, exact→fuzzy→type-inference), Location ("here"-inference + exact/fuzzy room), Temporal (HH:MM/duration/relative dicts), Quantity (number+unit). Resolved values are written as flat siblings `{name}_resolved/_confidence/_resolution_type` (`:71-73`). Asset loader is injected late, during `post_initialize_coordination` (`nlu_component.py:514-551`).

- **[P0]** **Dead-code context enhancement (= QUAL-22).** `_disambiguate_with_device_context` (`nlu_component.py:157-187`) computes `enhanced_entities` (output_capabilities / context_suggestion / preferred_output_device) in two branches then `return intent` — the original, unmodified — "for now, return original" (`:185`). Both writes are dead; the caller uses only name/domain/action. (Note: the method the QUAL-22 entry called `_enhance_intent` is this one.)
- **[P0]** **Fatal-error coupling on asset-loader timing.** Device/Location `resolve()` raise `RuntimeError("...fatal configuration error")` if the asset loader is missing or language data empty (`entity_resolver.py:179,194,306,322`), **uncaught inside `resolve()`** → propagates to `voice_assistant.py:388` and aborts the request. The resolver is built asset-less (`nlu_component.py:36`) and only swapped during deferred coordination, so any device/location utterance before/without successful coordination crashes NLU. Should degrade (return `None`/skip), not crash.
- **[P1]** **Duplicate, divergent device resolution**: the asset-driven `DeviceEntityResolver.resolve` (`entity_resolver.py:225`) **and** a hardcoded English-only `_resolve_device_entities` with an inline keyword list (`nlu_component.py:119-155`) both run, with different strategies and different output keys.
- **[P1]** **Resolvers silently drop entities**: only `str`/non-empty values are resolved (`:64`); all `resolve()` return `None` on no-match with no `_resolution_failed` marker — downstream can't tell "not resolvable" from "unresolved".
- **[P1]** **Location detection is name-only/value-blind** (`_is_location_entity` `:127`) — an entity named `device` holding "here"/"в спальне" never reaches the location resolver.
- **[P2]** Inconsistent externalization: device/room keywords are in YAML (and fatally required), but temporal terms (`:456-473`), quantity units (`:506-550`) and word-numbers (`:567-576`) are hardcoded in code. No NumberEntityResolver — word-numbers cover only 0–10 with risky substring matching ("двадцать"/"twenty-one" fail). Resolver language default `"en"` vs call-site `"ru"` mismatch.

### Layer 4 — consumption & surfaces (`intents/handlers/*`, `config/auto_registry.py`, `analysis/*`)
- **[P0]** **Required-parameter enforcement missing end-to-end.** Hybrid ignores `required` (`hybrid_keyword_matcher.py:1043-1059`); spaCy only logs (`spacy_provider.py:805,811`); designed `ParameterExtractionError` (`donations.py:189`) never raised; handlers never call `validate_entities` (0 call sites). → missing required param = absent key, handler proceeds on a guessed default = silent wrong action.
- **[P1]** **No shared typed accessor at the handler boundary.** `Intent.entities` is `Dict[str,Any]`; 11 handlers each hand-roll `.get(...)` with bespoke defaults and ad-hoc `int()`/`.lower()`. Base helpers `extract_entity`/`validate_entities` (`base.py:385-414`) used by exactly one handler. No accessor consults the donation `ParameterSpec` (type/choices/min/max) at read time. (e.g. `random_handler` `max` default is config on read but literal `100` on coercion failure.)
- **[P1]** **Per-parameter failures silently swallowed** — both providers `try/except → warning → continue`, and hybrid drops the param *without applying its `default_value`* (`:1058`).
- **[P1]** **Two divergent extraction contracts** across the fallback cascade → non-deterministic entity set for handlers.
- **[P2]** spaCy extraction self-describes as a **Phase-2 stub** ("provides basic extraction", `spacy_provider.py:821-825`), contradicting the archive doc's "COMPLETED".
- **[P2]** **Pipeline-internal metadata shares the user-param namespace**: `_recognition_provider`, `_cascade_attempts`, `_fallback_context`, `original_text` ride in `intent.entities` (`conversation.py`) undeclared in any schema. *(This is also the root of the `test_cascading_nlu` failures left in TEST-2 — tests assert a bare `provider` key while the pipeline injects `_recognition_provider`.)*
- **[P2]** **Web-API schema ≠ actual consumption contract**: exposed schemas are the donation `ParameterSpec` (`intent_component.py:378,447`) and provider *config* models (`auto_registry.py:435-465`), but handlers read keys not declared as params (timer's `language`/`timer_id`); no static cross-check (the analysis `_test_parameter_extraction` is itself a stub, `spacy_analyzer.py:557`).
- **[P2]** Dead/duplicated timer parsing (`timer.py:507-560`, TODOs at `:511,546` claim migration to `extraction_patterns` that didn't happen) — two drifting sources of truth.

### Archive-doc drift (`docs/archive/parameter_extraction.md`)
The doc's **architecture** (single-consumer providers, single-pass `recognize_with_parameters`, no separate extractor) is correctly implemented. The **contract** it promised is not:

| Doc claim | Reality |
|---|---|
| `JSONBasedParameterExtractor` deleted | File gone, but live comments still reference it and admit spaCy extraction is "Phase 2" / "basic" (`spacy_provider.py:798,821-825`). |
| `KeywordDonation` bundles `extraction_patterns` | No such field on `KeywordDonation`; it's on `ParameterSpec`. Doc struct wrong. |
| Required-param failure raises `ParameterExtractionError` | Never raised; providers log/swallow. |
| Hybrid honors `default_value` | Only when value is `None`; a coercion exception drops the param with no default. |

---

## Ranked remediation (feeds QUAL-11)

**P0 — correctness/crash (do first):**
1. **Fix the default `provider_cascade_order`** to the real entry-point names (`hybrid_keyword_matcher`, `spacy_nlu`) and the phantom `keyword_matcher` fallback; add a startup assertion that every cascade name resolves to a discovered provider. *(small, high-impact)*
2. **Decide the slot/extraction-pattern story**: either *implement* `slot_patterns` + `ParameterSpec.extraction_patterns` (run the compiled `Matcher`/`EntityRuler` and map spans→ParameterSpec by name), or *remove* the fields and document NER+regex as the contract. Today they are author-visible dead code. (Gates honest [DEDITOR] UI.)
3. **Make required-parameter handling a real contract**: raise/return a structured "missing required param" outcome from a *shared* extraction base; stop swallowing per-param exceptions; always apply `default_value`. Unify spaCy + hybrid onto one extraction/coercion/validation path so the parameter surface is deterministic.
4. **De-fatalize the resolvers**: catch the asset-loader/empty-data `RuntimeError`s inside `resolve()` and degrade (skip + mark `_resolution_failed`) instead of aborting the request; ensure the asset loader is wired before the resolver is reachable, or lazy-load on first use.
5. **Resolve QUAL-22**: finish or delete `_disambiguate_with_device_context` (apply `enhanced_entities` or remove the dead branches + the 2 xfail tests).

**P1 — robustness/consistency:**
6. Introduce a **typed entity accessor** (`get_param(name, type, default, choices)`) on `IntentHandler` driven by the donation `ParameterSpec`; migrate handlers off ad-hoc `.get`. Adopt `validate_entities` (or its successor) at the handler boundary.
7. Fix span→value mapping (associate multiple numbers/durations to the right `ParameterSpec` by slot, not first-match); add span-based free-text STRING capture; unify DURATION shape.
8. Default to `_md` spaCy models for any path using `doc.similarity`, or gate similarity on `doc.has_vector`.
9. Unify the duplicate device-resolution paths; add `_resolution_failed` markers; route location by value, not just name.

**P2 — hygiene:** `extra="forbid"` + `additionalProperties:false` on donations; commit a `v1.0.json` regeneration script + CI drift check; migrate Pydantic V1→V2 validators; config-drive the confidence weights; separate pipeline-internal metadata (`_*`) from user params; align spaCy model version pins; externalize temporal/quantity mappings (ties to ASSET-3 / lingua-franca number parsing).

---

## Impact on other tasks
- **QUAL-11** [PEX] — execute the remediation above (P0s first).
- **QUAL-22** — folded in as P0 #5; method is `_disambiguate_with_device_context` (not `_enhance_intent`).
- **DOC-7** [PEX] — the guide must document the *real* contract (NER+regex today), not the aspirational slot-pattern one, until #2 is decided.
- **UI-1/2/3** [DEDITOR] — the editor cannot honestly expose `slot_patterns`/`extraction_patterns` as functional until P0 #2 lands; the silent-unknown-field footgun (L1) is exactly the human-usability problem the editor targets.
- **TEST-4** [PEX] / **TEST-7** — the `test_cascading_nlu` failures parked in TEST-2 are the `_recognition_provider`-vs-`provider` metadata-namespace issue (L4 P2); the rewrite should test the unified extraction contract from #3.
- **ASSET-3** — number/duration parsing overlaps the hardcoded temporal/quantity maps; coordinate.

## Verification & later findings (TEST-0, 2026-06-01)
- **End-to-end recognition gap found via TEST-0:** `поставь таймер на 5 минут` is **not recognized** — both
  providers miss and it falls to `conversation.general`, even though the `timer` handler/donation is loaded and the
  fallback context correctly infers `likely_domain: timer, ambiguous_entities: [number:5, time:5 минут]`. So the
  donation matching/confidence path (Layer 2: brittle NER+regex, hardcoded thresholds, `_sm`-model similarity)
  fails on a *core* command. **[P1→P0 candidate]** for QUAL-11 — timers are unusable from recognition onward
  (compounding the QUAL-9 F&F launch crash). Repro: `POST /nlu/recognize {"text":"поставь таймер на 5 минут"}`.
- **Guarded by TEST-0** (`irene/tests/test_smoke_e2e.py`): `test_set_timer_end_to_end` is `xfail` on this +
  QUAL-9; it flips green when recognition + F&F land. `/nlu/recognize` responding structurally is a green smoke
  assertion, so regressions in the recognition surface are caught.
- **Now guarded by QUAL-23** (`irene/core/startup_validation.py`): the default `provider_cascade_order` naming
  non-existent providers (P0 above) is caught at startup — any configured cascade name that isn't a registered
  `irene.providers.nlu` entry-point is logged as an ERROR (and fails boot under `IRENE_STARTUP_STRICT=1`). This
  closes the "config omits cascade → phantom default names → total recognition failure" trap.
