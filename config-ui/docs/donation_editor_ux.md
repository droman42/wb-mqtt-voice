# Donation Editor UX — human-friendly pattern authoring (UI-1 design)

**Status:** DESIGN (UI-1). Gates the implementation of UI-2 / UI-3 / UI-5.
**Deliverable of:** UI-1 [DEDITOR]. Depends on QUAL-10 [PEX] (done). Sequenced ahead of UI-5 (P1) and UI-2/UI-3 (P2).

## 0. Who this editor is for (the persona that drives every decision)

> The author **knows exactly how the intents/handlers should behave** — what actions exist, what each user might
> ask for, what values to pull out of a sentence. They have **no idea how spaCy works, and no idea what "NLU",
> "token", "lemma", "POS", or "regex" even mean.** They think in **example sentences and values**, not in matchers.

Every label, concept and default below is chosen so this person never meets a spaCy/NLU word. The raw spaCy editors
are not deleted — they survive as an **advanced escape hatch behind a button** (§5) for the rare case the friendly
model can't express. If a screen forces the persona to learn what a lemma is, the design has failed.

> **Scope correction (supersedes the ledger note).** The ledger said *"`ParameterSpecEditor` is already fine."*
> That's wrong. It's fine **only for its structural fields** (name, the 8 ParameterTypes, required, choices,
> min/max, aliases). It also embeds two raw expert surfaces — an **`extraction_patterns`** sub-editor
> (`ExtractionPatternsEditor` → raw spaCy attribute dicts) and a raw **regex `pattern`** field. Under the v1.1 split
> those belong on the *phrasing* side with the other patterns, so **all three editors** are in scope. UI-1 is one
> design across the whole donations editor.

---

## 1. The organizing principle: the v1.1 split *is* the clean/spaCy line

QUAL-29 split every handler donation into two files, and that split is exactly the boundary between
"structural, language-neutral, already human-friendly" and "raw spaCy phrasing":

| `contract.json` — language-neutral core | `<lang>.json` — per-language phrasing |
|---|---|
| `method_donations[]`: `method_name`, `intent_suffix`, `boost`, **`room_context`** | `description`, `phrases`, `lemmas`, `examples` |
| `parameters[]`: `name`, `type` (8), `required`, **canonical** `choices`, `min/max`, `pattern`, **`entity_type`** | `token_patterns`, `slot_patterns`, `negative_patterns`, `additional_recognition_patterns`, `action_patterns`, `stop_command_patterns` |
| `intent_name_patterns`, `action_domain_priority` | per-param: `description`, **`extraction_patterns`**, `aliases`, `default_value`, **`choice_surfaces`** |
| **zero spaCy** | **100 % of the raw spaCy lives here** |

(Confirmed on disk: every handler dir is `contract.json` + `en.json` + `ru.json`; schemas
`assets/donation_contract_v1.1.json`, `assets/donation_language_v1.1.json`.)

**Design consequence — the editor becomes two editors:**

1. **Contract Editor** (one per handler) — structural. The *good half* of today's `ParameterSpecEditor`, promoted to
   first-class. **No spaCy. No UI-2/UI-3 abstraction needed** — already persona-friendly.
2. **Phrasing Editor** (one per handler × language) — the **only** place raw spaCy lives, and therefore the **only**
   place the human-model abstraction (UI-2/UI-3) is concentrated.

This is what lets us ship structurally first (UI-5) and add ergonomics later without rebuilding scaffolding — §7.

---

## 2. What we actually have to abstract (grounded, not theoretical)

A survey of all 28 phrasing files (14 handlers × {en, ru}) shows the **real spaCy vocabulary is small** — so the
human model only has to cover this, with a raw escape hatch for the long tail.

| spaCy attribute | uses | value forms seen | what the author actually means |
|---|---|---|---|
| `TEXT` | 773 | bare · `{IN:[…]}` · `{REGEX:"…"}` | a specific word |
| `LEMMA` | 393 (ru-heavy) | bare · `{IN:[…]}` | a word **and its grammatical forms** |
| `LOWER` | 196 | bare · `{IN:[…]}` | a specific word (case ignored) |
| `IS_ALPHA` | 160 | `true` | any word (a value placeholder) |
| `LIKE_NUM` | 30 | `true` | a number |
| `IN` (value) | 395 | `[…]` (incl. `[]`) | any one of several words |
| `REGEX` (value) | 145 | regex string | *mostly* reducible to the rows above (see §3.3) |
| `OP` | 120 | **only `"+"`** | "can repeat" |
| `IS_SENT_START` | 2 | `false` | (rare → advanced) |
| `POS` | 1 | `"VERB"` | (rare → advanced) |

**Not used at all:** `NOT_IN`, `TAG`, `ENT_TYPE`, `IS_DIGIT`, `IS_PUNCT`; operators `?` `*` `!`.
**Volume:** 1–10 patterns per method (typically 2–3); most patterns are 1–4 tokens long.

**Takeaway:** the persona never needs to see a token attribute. Five everyday concepts + "advanced" cover everything.

---

## 3. The human authoring model

### 3.1 The mental model: *example sentences → cards*, never "patterns"

The persona thinks: *"to set a timer, the user says something like **‘set a timer for 5 minutes’**, and I need to grab
the **5** and the **minutes**."* The UI is built around that, in two questions per action (method):

- **"What might the user say?"** — a list of **ways of saying it**. Each one reads left-to-right like a fill-in-the-blank
  sentence made of **word cards** (§3.2). The persona can also just type plain **example sentences** (the existing
  `phrases`/`examples`), and §6 lets them test those against the real recognizer.
- **"Where is each value in the sentence?"** — per parameter (from the contract), a **"how to find this value"** block,
  built from the same word cards (§3.4).

The word "pattern"/"token"/"slot"/"lemma" appears **nowhere** in the persona's UI. (Internally these map 1:1 to
`token_patterns` / `slot_patterns` / `extraction_patterns`; see §3.4, §4.)

### 3.2 The word-card vocabulary (the entire persona-facing language)

Each "way of saying it" is an ordered row of cards. A card is one of:

| Card (persona label) | what they enter | help text (no jargon) | compiles to |
|---|---|---|---|
| **A word** | one word + a toggle **“include its forms”** | *"matches this word. Turn on ‘include its forms’ so ‘set / sets / setting’ all match — important for Russian."* | toggle off → `{LOWER:"w"}` · on → `{LEMMA:"w"}` |
| **One of several words** | a chip list of synonyms | *"matches if the user says any one of these — e.g. timer / alarm / countdown."* | `{LOWER:{IN:[…]}}` (or `{LEMMA:{IN:[…]}}` if "forms" on) |
| **A number** | (nothing) | *"matches a number, like 5 or 10."* | `{LIKE_NUM:true}` |
| **Any word** | (nothing) | *"a placeholder for a single word you’ll capture — e.g. a name or label."* | `{IS_ALPHA:true}` |
| **The rest of the sentence** | (nothing) | *"captures everything the user says after this point — e.g. a timer note."* | `{TEXT:{REGEX:".*"}}` |
| **Advanced rule** | the raw editor (§5) | *"for an unusual case the cards above can’t express."* | the dict verbatim |

Two plain-English per-card modifiers (default off):
- **Optional** — *"the user might not say this."* → `OP:"?"`
- **Can repeat** — *"the user might say this more than once."* → `OP:"+"`

**Case is handled for them.** New "A word" cards default to case-insensitive (`LOWER`); the `TEXT` vs `LOWER`
distinction is never surfaced (round-trip preserves whichever the file already had — §4). The **“include its forms”**
toggle is the *only* linguistic choice we expose, and it's framed in terms the persona owns ("set / sets / setting"),
with a sensible default per content language (Russian → on, English → off).

### 3.3 Regex disappears into the cards

145 regex uses sounds scary, but in the real files they are **overwhelmingly the friendly cards in disguise**, so the
translation layer (§4) maps them on load and the persona never sees a regex:

- `{TEXT:{REGEX:".*"}}` → **The rest of the sentence**
- `{TEXT:{REGEX:"^\\d+$"}}` / `"\\d+"` → **A number**
- `{TEXT:{REGEX:"set|start|begin"}}` → **One of several words** [set, start, begin]

Only genuinely complex regex (a handful: date/time formats, Russian capture groups) can't reduce — those land on an
**Advanced rule** card (§5), clearly flagged, never silently dropped.

### 3.4 "How to find each value" (unifying `slot_patterns` + `extraction_patterns`)

Today patterns live in **three** places in **two** shapes — method `token_patterns`, method `slot_patterns`, and
per-param `extraction_patterns` (`{pattern, label}`). The persona should never know this. The model collapses it to:

- **Recognition** (`token_patterns`) → the **"What might the user say?"** list (§3.1).
- **Value extraction** (`slot_patterns` **+** `parameters[].extraction_patterns`, joined by the slot label) → a
  **"How to find this value"** block shown **under each contract parameter**, built from the same word cards.

Example, under parameter **duration**: *"Find it as: ① a number  ② a number then the word ‘minutes’."* — same card
widget, reused. On load the two underlying shapes are merged per parameter; on save they're re-split to the exact
shapes the schema expects. The merge/split is part of the translation layer (§4) and is invisible to the author.

### 3.5 `choice_surfaces` — "how people say each option"

Phrasing-side, for `choice`/`entity` parameters. A two-column table: **option** (read-only canonical token from the
contract's `choices`) → **what people say for it** (editable chip list, in this content language). Honors the
donation-choice rule: canonical tokens are language-neutral identifiers and are **never** translated — only the
spoken forms are. Persona framing: *"the option is `quiet`; people say ‘тихо’, ‘потише’, ‘тихий режим’."*

---

## 4. The translation layer (UI-2) — **frontend-only**, backend owns what needs real spaCy

**Decision (settled in UI-1, per user):** the human↔spaCy mapping is a **pure, frontend, structural transform** —
`patternModel.ts` exporting `compile(model) → spaCyDict[]` and `decompile(spaCyDict[]) → model` (incl. the §3.4
merge/split and the §3.3 regex reductions). **No new backend endpoint.**

Why frontend-only is safe here:
- It's **representation only** — JSON-shape ↔ friendly cards. It never decides what text *matches*, so there's no
  matcher-semantics to drift.
- Scoped to the small real vocabulary **+ an Advanced card**, the transform is **total and lossless by construction**:
  the round-trip invariant `compile(decompile(x)) === x` holds for **every** input because anything unmapped is stored
  verbatim in an Advanced card. **Required UI-2 test:** load all 28 real phrasing files, decompile→compile, assert
  deep-equal.

What stays on the backend (we do *not* reimplement these):
- **Validation** — `POST /donations/{handler}/{language}/validate` (real JSON-schema + Pydantic).
- **Test-against-text** — the real NLU recognize path (§6).

**Rejected:** a backend `compile/decompile` endpoint — it adds API surface for a transform that needs no spaCy
runtime. `patternModel.ts` is the single seam if server-side compilation is ever needed later.

---

## 5. The escape hatch (raw spaCy = advanced, behind a button)

End state (after UI-3): the **cards are the default**; raw spaCy is an **advanced mode reached by a button / fold**,
never shown unless asked for. Two levels:
- **Per-card "Advanced rule"** (§3.2) — one token the cards can't express, edited via the existing
  `SpacyAttributeEditor`.
- **Per–"way of saying it" "Edit as advanced"** toggle — swaps the whole card row for the raw editor and back.
  Switching *to* advanced is always available; switching *back* to cards is offered only when the raw content is
  representable as cards (otherwise the card view stays disabled with a *"too advanced to show as cards"* note —
  data is never corrupted or lost).

This keeps the model **additive**: experts are never blocked, unrepresentable patterns are never mangled.
(Interim note: UI-5 ships the pattern slots wired to the *existing raw editors* as a placeholder so the page is
functional before the cards exist; UI-3 then makes cards the default and demotes raw to this escape hatch.)

---

## 6. "Does this actually work?" — test against sample text (UI-3)

A sample-sentence box under each action/value. On **Test**, call the **real recognizer** (the same path production
uses — no JS re-implementation, no fictional endpoint) and show what was recognized and which values were filled, so
the persona validates phrasings by example without talking to a device. Exact endpoint wiring is a UI-3 detail; UI-1
fixes only that it must use the real matcher.

---

## 7. Bilingual editor UI (i18n) — a cross-cutting requirement

**Requirement (user):** the **entire config-ui** must become fully bilingual (Russian + English), with adding more
languages later being cheap. This concerns the **editor’s own chrome** — labels, buttons, help text, validation
messages — not the donation content.

**Two orthogonal language axes — must never be conflated:**

| | **Content language** | **UI language** |
|---|---|---|
| what it is | which phrasing file you’re editing (`en.json` / `ru.json`) | the language the editor’s buttons/labels are written in |
| control | the existing `LanguageTabs` | a new global UI-language switcher |
| example | *editing the **English** phrasing…* | *…with a **Russian** interface* |

A Russian author editing the English phrasing with a Russian UI must be a normal, supported case.

**Mechanism — harmonize with the bridge (UI-6 stack-alignment):** `../wb-mqtt-bridge/ui` already uses
**`react-i18next`** (`i18next ^23` / `react-i18next ^13`); config-ui has none. Adopt the same: a `react-i18next`
setup with `en` + `ru` resource bundles and a language switcher. All persona-facing strings — *especially the §3.2
card labels and help text, which carry the whole "no-jargon" promise* — are authored as **i18n keys from day one**,
so UI-1/2/3/5 never bake in English that must be retrofitted.

**Scope:** localizing all of config-ui is cross-cutting (every page), so it is its own task — **UI-7** (filed). But it
must be *foreseen now*: UI-2/3/5 author their new strings through the i18n layer immediately, even before UI-7
retrofits the older pages. The card vocabulary in §3.2 is the first resource bundle.

---

## 8. Editor architecture & phasing (build the scaffolding once)

Per the user's chosen **structural-first** sequencing; file ownership split so nothing is built twice:

```
DonationsPage  (+ global UI-language switcher — UI-7)
├── HandlerList                         (exists)
├── ContractEditor            ← UI-5    structural; the good half of ParameterSpecEditor, promoted
│   └── ParameterSpecEditor'  ← UI-5    name/type/required/canonical choices/min-max/entity_type/room_context
│                                       (extraction_patterns + regex REMOVED → moved to phrasing)
└── LanguageTabs              (exists)  ← CONTENT language (independent of UI language)
    └── PhrasingEditor         ← UI-5    shell: description/phrases/lemmas/examples + the two card areas
        ├── "What might the user say?"   ← hosts the way-of-saying-it widget
        ├── "How to find each value"     ← hosts the same widget, grouped by contract param
        ├── ChoiceSurfaces     ← UI-5    option → spoken-forms table
        └── <card widget>:
              UI-5 ships: existing raw editors (TokenPatterns/SlotPatterns) as interim placeholder
              UI-3 swaps in: the word-card editor (built on patternModel.ts) + advanced escape hatch + test box
```

- **UI-5 (P1, release)** — `apiClient.ts` → v1.1 endpoints (drop `syncParameters`); generated types; **ContractEditor**;
  **PhrasingEditor shell**; **ChoiceSurfaces**. Pattern areas use the existing raw editors so the page works again.
  Unblocks the release **without** the human model. New strings go through i18n (§7).
- **UI-2 (P2)** — `patternModel.ts` (`compile`/`decompile` + merge/split + regex reduction), with the 28-file
  round-trip test. Pure module, no UI.
- **UI-3 (P2)** — the **word-card editor** + advanced escape hatch + test-against-text, dropped into the two card areas.
  **Touches only the card widget** — page, types, apiClient, contract editor, shell are settled by UI-5 → no rebuild.
- **UI-7** — config-ui-wide `react-i18next` adoption + ru/en bundles + UI-language switcher.

**Net:** the structural rebuild happens **once** (UI-5); UI-3 replaces only the card-authoring guts, which were always
going to be replaced. UI-5's "don't build the editor twice" constraint is satisfied.

---

## 9. Backend touchpoints (all confirmed to exist — UI-1/2/3 add none)

`GET /donations` · `GET|PUT /donations/{handler}/contract` · `GET|PUT /donations/{handler}/{language}` ·
`POST /donations/{handler}/{language}/{validate,create}` · `DELETE /donations/{handler}/{language}` ·
`GET /donations/{handler}/cross-validation` · `POST /donations/{handler}/suggest-translations` ·
`POST /donations/{handler}/reload`. (`sync-parameters` is gone — UI-5 drops the client call.)
Only backend prerequisite is **UI-5's** committed `openapi.json` dump (for type generation).

---

## 10. Open decisions (resolve during implementation)

1. **`negative_patterns` / `additional_recognition_patterns`** — same card model applies; surface in an
   *"Advanced recognition"* disclosure (low edit volume) rather than the main flow. *Lean: disclosure.*
2. **Operators** — real data uses only `+`; expose **Optional (`?`)** and **Can repeat (`+`)**; `*`/`!` via Advanced
   only. *Lean: yes.*
3. **Empty `{LEMMA:{IN:[]}}` placeholders** (common in en) — decompile to an empty **"One of several words"** card so
   they stay editable, not an Advanced card. *Lean: yes.*
4. **"Start from an example"** — a helper that turns a typed example sentence into a first draft of cards (then
   editable). Nice-to-have; not core. *Defer to a UI-3 stretch.*
5. **Cross-language panel** — param parity is structural now (contract-side); the phrasing cross-check is
   surface-completeness + method-phrasing only. Owned by UI-5's panel rework.

---

## 11. Summary

- One design, **two editors**, drawn on the v1.1 split: a clean **Contract Editor** (no spaCy) and a **Phrasing
  Editor** that quarantines all raw spaCy.
- The model is built for a persona who knows **handlers but not spaCy/NLU**: **five everyday cards + Advanced**, all in
  example-sentence language; "token/lemma/regex/pattern" never appear. Regex and the three-place pattern split are
  hidden by the translation layer.
- Translation is **frontend-only** (`patternModel.ts`), lossless by construction; the backend keeps **validate** and
  **test-match** (the only jobs that need real spaCy).
- Raw spaCy survives as an **advanced escape hatch behind a button**, never the default.
- The whole config-ui goes **bilingual (ru/en, extensible)** via `react-i18next` (harmonized with the bridge) — a
  cross-cutting task **UI-7**, with UI language kept orthogonal to content language. New editor strings are i18n keys
  from day one.
- Phasing is **structural-first**: UI-5 ships the functional v1.1 editor + all scaffolding; UI-2 adds the pure
  translation module; UI-3 swaps the cards into the one widget — no double build.
