# config-ui review — quality, duplication, dead code, correctness (2026-06-28)

Recall-biased review of `config-ui/` (~31.7k LOC) requested with emphasis on **code quality, repeated
code, dead pieces** on top of regular correctness review. 8 finder angles → 1-vote verify. Frozen
evidence; findings worth acting on are tracked by the `→ tracked as <ID>` pointers below.

Baseline at review time: `npm run check` (type-check + strict ESLint + orphan check) and `npm run
build` both pass; `find-orphans.mjs` reports no orphan modules. So the defects below are what those
gates **don't** catch: runtime logic, stale-state, unused *exports* (ESLint flags only unused locals),
type drift behind a still-passing `tsc`, and structural duplication.

## A. Correctness (verified)

| # | File:line | Verdict | Defect |
|---|-----------|---------|--------|
| A1 | `pages/DonationsPage.tsx:735` vs `755-762`, effect `654-662` | **CONFIRMED** | 404-fallback infinite reload loop |
| A2 | `hooks/useRealtimeAnalysis.ts:100-141` | **CONFIRMED** | stale-request guard ineffective → out-of-order overwrite |
| A3 | `components/common/ApplyChangesBar.tsx:71,127-130,190,248` | **CONFIRMED** | enhanced-mode blocking-conflicts dialog unreachable |
| A4 | `pages/DonationsPage.tsx:864-867` vs `878-881` | **CONFIRMED** | validation error stored under wrong key |
| A5 | `pages/DonationsPage.tsx:788-801` | **CONFIRMED** | `globalParamNames` memo missing `selectedLanguage` dep |
| A6 | `hooks/useValidationWorkflow.ts:98-99`, `useRealtimeAnalysis.ts:122` | PLAUSIBLE | `.conflicts.filter`/`.map` unguarded → white-screen on malformed payload |
| A7 | `pages/DonationsPage.tsx:996` → `CrossLanguageValidation.tsx:53` | PLAUSIBLE | `handlersList.find(...)!` → `undefined.languages.length` crash |

**A1 — 404 fallback stores under the wrong key → infinite reload + stuck spinner.** Success keys by
`` `${handlerName}:${targetLanguage}` `` (735); the 404 branch stores the empty fallback under bare
`[handlerName]` (757,761). The load effect re-fires `loadDonation` whenever
`` !donations[`${selectedHandler}:${selectedLanguage}`] `` with `donations` in deps (662). A handler
with no donation file for the active language → 404 → `setDonations` (new object identity) → effect
re-runs → composite key still absent (data under bare key) → 404 → **loops forever**, hammering the
API; the editor (keyed on the composite at 1068) shows the spinner indefinitely.

**A2 — stale-request guard reads the ref, not a per-invocation local.** `performAnalysis` reassigns
`abortControllerRef.current = new AbortController()` (105); the post-await guards check
`abortControllerRef.current?.signal.aborted` (117,141) — by then the ref points at the *newest*
controller. A slow earlier call resolves, its guard passes, and `setConflicts`/`setLastAnalyzedHash`
clobber the newer results. The signal is also never passed to `analyzeDonation`/`fetch` (110-114), so
`abort()` never cancels the network. Fix: capture `const signal = …current.signal` locally and pass it
to the request.

**A3 — the blocking-conflicts dialog can never open in NLU mode.** `canSaveNLU` already requires
`!hasBlockingConflicts` (`useValidationWorkflow.ts:96`); `canApply = …&& canSave` gates the Apply
button's `disabled` (190,248). So when blockers exist the button is disabled → `handleApply` never
runs → its `if (hasBlockingConflicts) setShowBlockingDialog(true)` (127-130) is unreachable. No other
trigger sets `showBlockingDialog` (only `false` at 339,341). `BlockingConflictsDialog` is effectively
dead UI — and the whole enhanced Apply branch (warnings too) is gated the same way.

**A4 — validation error keyed wrong.** Success stores
`` validationResults[`${selectedHandler}:${selectedLanguage}`] `` (864-867); the catch stores bare
`[selectedHandler]` (880). The tab indicator reads the composite key (519,527), so a validation throw
never surfaces on the language tab (stays "loaded"/0 errors).

**A5 — stale memo.** `globalParamNames` computes its key from `selectedHandler`+`selectedLanguage` but
deps are `[donations, selectedHandler]` (eslint-disabled), missing `selectedLanguage`. Switching to an
already-cached language changes neither dep, so `ExamplesEditor` gets the *previous* language's global
param names for autocomplete/validation.

→ tracked as **BUG-8** (A1, A4, A5, A7), **BUG-9** (A2, A6), **BUG-10** (A3).

## B. Contract drift — `src/types/api.ts` behind the backend (defeats the type-check gate)

`config-ui-stays-functional` relies on `npm run check` to catch contract drift, but the editor renders
from the backend-supplied **schema** (`ConfigSection.tsx:210-299`), so the app keeps working while the
hand-written `src/types/api.ts` (what `apiClient` actually consumes via `types/index.ts:6`) silently
rots. The generated `openapi.gen.ts` is current but unused by the app. Drifts:

- **B1** `CoreConfig` missing `outputs` + `trace` sections — `api.ts:544-561` vs `irene/config/models.py:1266,1283`.
- **B2** `CoreConfig` missing canonical `default_language`/`supported_languages` (QUAL-36) — `api.ts:536-572` vs `models.py:1291-1292`.
- **B3** `NLUConfig` carries phantom required `default_language`/`supported_languages` — `api.ts:689-690` vs `models.py:335-363` (moved to CoreConfig).
- **B4** `VADConfig` is the pre-ARCH-18 shape (~10 phantom flat fields; missing `default_provider`/`providers`) — `api.ts:734-752` vs `models.py:415-436`.

Net: typed access to these is `undefined` at runtime / forces `as any`; the type-check half of the
gate gives false confidence. Fix: regenerate/realign `api.ts` or point `apiClient` at `openapi.gen.ts`.
**Confirmed clean:** DURATION fully removed (schema+gen+derived type); `default_value_by_language`
correctly absent (runtime-only); every REST path/method matches a backend route; `ajv`/`ajv-formats`
declared but **unused** in `src/` (client validation is delegated to backend `validate*` endpoints —
an unused dependency, not drift).

→ tracked as **UI-11**.

## C. Duplication (repeated code)

- **C1** `apiClient.ts` — the per-resource CRUD quintet copy-pasted ×4 (donations `245-339`, templates
  `483-567`, prompts `583-667`, localizations `897-981`), ~250 near-identical lines differing only by
  URL prefix / request key / response type. → a `resourceCrud(prefix, dataKey)` factory.
- **C2** Page clones — `TemplatesPage.tsx:40-355` ≈ `PromptsPage.tsx:40-315` (the file header says "exact
  same pattern"); same state set + `loadHandlers`/dirty-effect/`languageInfos`-effect/save/validate/
  create/delete; `DonationsPage`/`LocalizationsPage` share the shape. ~250-300 lines. → a
  `useHandlerLanguageResource(api)` hook + one `ResourceEditorLayout`.
- **C3** "List of strings" add/remove/edit reimplemented ×4 — canonical `ArrayOfStringsEditor.tsx:13-63`
  vs hand-rolled in `LemmasEditor.tsx:31-46,143-212`, `SpacyValueEditor.tsx:100-162`,
  `LocalizationKeyEditor.tsx:104-166`. → route through `ArrayOfStringsEditor`.
- **C4** Type-aware key editor near-clones — `TemplateKeyEditor.tsx:33-175` ≈ `LocalizationKeyEditor.tsx:37-245`
  (same `getValueType` + string/array/object trio, ~150 lines). → one `TypedValueEditor`.
- **C5** Object/key-value map editor re-implemented inside C4's object branches vs canonical
  `KeyValueEditor.tsx:28-59`. → reuse `KeyValueEditor`.
- **C6** Controlled decompile→compile scaffold duplicated — `CardPatternsEditor.tsx:33-57` ≈
  `ExtractionFillersEditor.tsx:29-54` (same `useState(decompile)` + `lastEmitted` ref + re-sync effect +
  `emit`). → a `useDecompiledPatterns` hook.

→ tracked as **UI-12**.

## D. Dead code (unused exports — ESLint flags only unused *locals*)

- **D1** `types/index.ts:12-23` — 8 never-imported utility aliases: `Maybe`, `Optional`, `RequiredKeys`,
  `ChangeHandler`, `ClickHandler`, `AsyncClickHandler`, `ApiMethod`, `LoadingState` (`ConnectionStatus`
  IS used — keep).
- **D2** `types/components.ts` — dead exported interfaces: `TokenPatternsEditorProps` (90),
  `SlotPatternsEditorProps` (100), `HandlerListProps` (115, superseded by `HandlerLanguageListProps`),
  `ConfigSection` (202) + `ConfigField` (209), `SearchFilters` (184), `BulkOperationResult` (191),
  `MonitoringData` (225) — 0 references each.
- **D3** `utils/spacyAttributeHelpers.ts:261` `validateSpacyAttribute` — exported, never called.
- **D4** `utils/safeStringify.ts:77` `wouldShowObjectObject` — exported, never called.

→ tracked as **UI-13**.

## E. Efficiency + altitude / hardcoded lists

Efficiency:
- **E1** `hasChanges` state synced via effect (`PromptsPage.tsx:77-82`, `TemplatesPage.tsx:77-82`) —
  derivable; should be `useMemo`.
- **E2** `TomlPreview.tsx:59,96-108` debounce timer stored in `useState` → re-render per keystroke +
  unstable callback; use a `useRef` (the pattern `useRealtimeAnalysis` already uses).
- **E3** `JSON.parse(JSON.stringify(x))` deep-copy ×8 on large config objects — `ConfigurationPage.tsx:277,
  284,388,432,543,553,734,930`; use `structuredClone`.
- **E4** double-hash per change — `useRealtimeAnalysis.ts` `currentHash` memo (70-73) **and** again inside
  `performAnalysis` (85); thread the memoized hash in.
- **E5** unmemoized per-render/per-row work — `LemmasEditor.tsx:56-91,145` (`getSuggestedLemmas` + per-row
  conflict filter); `useValidationWorkflow.ts:98-99` (`.filter` rebuilds fresh arrays each render).

Altitude / hardcoded lists that duplicate a source of truth and will drift:
- **E6** `ContractEditor.tsx:21-25` — `PARAMETER_TYPES`/`ENTITY_TYPES`/`ROOM_CONTEXTS` literals re-state the
  generated unions in `donation-contract.gen.ts:35,40,49`; a new backend enum value silently drops from
  the dropdown. Derive from the generated union.
- **E7** `ConfigSection.tsx:98,105-114` — hardcoded component-section roster + `section→component` map (the
  `text_processor→text_processing` remap shows the fragility); a renamed/added component silently loses
  its Test/Workflow buttons.
- **E8** `LanguageTabs.tsx:58-72` (10-entry language-label map) + `DonationsPage.tsx:534` (`|| ['en','ru']`
  fallback) — hardcoded language assumptions that drift from the backend `supported_languages` contract.
- **E9** `ConfigWidgets.tsx:706-743` — widget selection is a stack of `name===… && path.some(includes(…))`
  heuristics (incl. a "legacy" arm); should be schema-driven (`widget` hint on the field schema).
- **E10** `spacyAttributeHelpers.ts:232-256` — hardcoded English-only attribute descriptions (i18n bypass)
  + an attribute/operator vocab that duplicates the NLU matcher's.

→ tracked as **UI-14**.

## Non-findings (checked, clean)
- `donation-choice-surfaces-rule`: `ChoiceSurfacesEditor.tsx:32` renders the canonical token read-only
  (`font-mono`, never translated); `ContractEditor` keeps `method_name`/`intent_suffix`/canonical
  `choices` as the canonical surface — compliant.
- No client-side AJV (delegated to backend); `types/donations.ts` correctly **derives** from the gen
  files (no hand-duplication); i18n spot-check (monitoring/configuration) clean.
