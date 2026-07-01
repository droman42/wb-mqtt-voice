# English deployment — slim cross-architecture model set & multilingual eval — design notes

**Status:** design/research session 2026-07-01 (**no code**). Captures findings + decisions so implementation
can proceed as separate tasks. Backs **I18N-1**. Deliverable of a design task, not shipped code.

**Goal.** Ship a **real English deployment** (not just eval): the voice assistant answering English speech across all
three Docker architectures we support — **armv7** (WB7 controller, torch-free), **aarch64** (WB8 / Raspberry Pi,
torch-free), **x86_64** (standalone). English models must be **slim** and of a **size class comparable to the Russian
models** already shipped per architecture. English eval rides on top and validates the stack end-to-end.

---

## 1. Findings — how language actually works today (three investigations)

### 1a. Language auto-detection is NOT usable for the voice pipeline
Runtime detection is wired only at the **text-understanding + response-string** layer, never to the acoustic models:
- `ContextAwareNLUProcessor` reads `auto_detect_language` / `language_detection_confidence_threshold`, detects the
  language of the ASR **transcript** (Cyrillic → `ru`, else `en`) and sets `context.language`, so handler templates
  reply in that language (`irene/components/nlu_component.py:203-231`, `irene/utils/text_script.py`).
- **ASR ignores it** — `asr_component.py:214` always transcribes in `self.default_language`; `switch_language` is a TODO
  stub (`asr_component.py:395-398`). **TTS ignores it** — voice/model is pinned per-config. Detection runs *after*
  transcription, so a wrong-language acoustic model has already produced the transcript.
- **Dead config:** `persist_language_preference` and the entire `[nlu_analysis.languages]` block have **zero runtime
  readers** (the analysis component hardcodes `["ru","en"]`).

**Consequence:** the speech-in/speech-out pipeline is **monolingual per config**. This is fine and *intended* — the
system stays slim. **Decision:** EN configs set `auto_detect_language = false`; language is chosen per **deployment /
config**, never auto-switched at runtime.

### 1b. The config language flag drives only the text side; acoustic models are independent
`default_language` auto-drives NLU routing, donation/prompt asset selection (`en.json`), number normalization, and LLM
prompts. But **every ASR/TTS model path is an independent per-provider field** — they do not cascade from the top-level
flag. An English config is therefore `default_language="en"` **plus** an explicit ASR-model swap **plus** a TTS-voice
swap.

### 1c. Eval does not exercise TTS (but real deployment does)
The WS eval registers with `wants_audio=false`, so the SUT never synthesizes speech — the suite asserts on the reply
**text** and the recognized transcript. So the earlier "TTS blocker" is **not** a blocker for eval. It *is* required for
a real deployment — but it turns out to be cheap (§2).

---

## 2. The slim English model set (cross-arch, size-matched)

sherpa-onnx (ASR) + Piper (TTS) span the two **torch-free** satellites; the x86_64 **standalone** is the torch image
(ASR torch-Whisper, TTS torch-Silero). English models exist in the same class/size as the Russian ones on every stage.
**TTS is per-architecture, not unified** (mirroring the Russian split): Piper on the torch-free satellites, torch-Silero
on the standalone.

| Stage | Russian today | English — plan | Size vs RU | New? |
|---|---|---|---|---|
| ASR — **armv7** (torch-free) | `vosk-model-small-ru` sherpa transducer, ~27 MB int8 | **spike: `sherpa-onnx-streaming-zipformer-en-20M` (43.6 MB int8, proven arm32, streaming) vs `moonshine-tiny-en` (27M params, English-only, offline, ~48% lower WER than whisper-tiny, arm32 UNCONFIRMED)** | same tier (~27–44 MB) | **NEW asset** (I18N-2) |
| ASR — **aarch64** | `whisper-small` sherpa (~470 MB, multilingual) | same `whisper-small` — EN is **config-only** | identical | no |
| ASR — **x86_64** | torch `whisper small` (multilingual) | same — EN is **config-only** | identical | no |
| TTS — **armv7 + aarch64** (torch-free) | Piper `irina` ru_RU / `piper_ruaccent` medium, ~60–75 MB | **Piper `en_US-amy-medium`** (same k2-fsa release, same `.tar.bz2` medium format); generalize the `ru_RU`-hardcoded catalog | ~same | catalog code (I18N-3) |
| TTS — **x86_64 standalone** (torch) | `silero_v4` `baya` (torch `.pt`, ~50 MB) | **`silero_v3` `v3_en`** (torch `.pt`, multi-speaker `en_0…en_117`) — torch parity, in-image | ~same size, **v3-tier quality** (Silero froze English at v3 — no `v4_en`/`v5_en` exists) | small provider generalization (I18N-7) |
| NLU / donations | `hybrid_keyword` + `ru.json`; spaCy `ru_core_news` (64-bit) | `en.json` + spaCy `en_core_web` — **already cataloged** | — | content audit (I18N-6) |
| Number norm | pure-Python ru | `ovos-number-parser` en — **already wired** | — | no |
| VAD | silero / energy — language-neutral | same | — | no |
| Wake word | ESP32 on-device (armv7) / disabled | English wake phrase model where wake is enabled | — | out of scope for now |

**NLU last-resort (LLM) note — bilingual, no change needed (verified 2026-07-01).** The `[nlu.providers.llm]`
classifier tier (QUAL-50/51) is already language-parameterized on `context.language`: `_build_system_prompt(language)`
filters the intent taxonomy to the utterance language by script, `_ABSTAIN_EXAMPLES` carries **both `ru` and `en`**
anti-hallucination exemplars, and positive few-shot is sourced from the language-matched donation examples; instructions
are language-neutral English and output is language-neutral JSON. Verified by rendering the EN prompt: English taxonomy +
English abstain/positive exemplars, zero Russian leakage. So the conservative "abstain over guess" safety holds for
English too — no adjustment required for the English deployment.

**Standalone TTS note.** The standalone runs `silero_v4` (torch) for Russian, but **Silero never shipped an improved
English model** — the official `models.yml` has `v3_ru→v4_ru→v5_ru` for Russian yet English stops at `v3_en` (no
`v4_en`/`v5_en`; the code comment at `silero_v4.py:54` confirms it). So torch parity on the standalone means accepting
**`v3_en`** (torch, ~same size, one quality generation below the RU `v4_ru`) — the deliberate trade to keep the
standalone image torch-only rather than pulling the sherpa-onnx runtime in for Piper.

**armv7 is the crux and it is solvable.** The 20M English streaming zipformer is 43.6 MB int8 — same order as
`vosk-model-small-ru` — and sherpa-onnx ships `linux_armv7l` wheels + arm32 prebuilt binaries. Whisper stays 64-bit-only,
so it is *not* the armv7 answer.

Sources: sherpa-onnx `zipformer-en-20M` (HF `csukuangfj/sherpa-onnx-streaming-zipformer-en-20M-2023-02-17`),
sherpa-onnx arm-embedded install docs + `linux_armv7l` PyPI wheels, Piper en_US voices in the k2-fsa `tts-models`
release, sherpa-onnx Moonshine support (`sherpa-onnx-moonshine-tiny-en-int8`).

### 2a. "Config-only" for the 64-bit Whisper path — what it means, and that it is already wired
For aarch64/x86_64, English needs **no code and no new asset** because Whisper is multilingual **and the
`default_language` flag is already consumed at inference** — verified end-to-end:
- **Torch Whisper (x86_64)** reads `default_language` (`irene/providers/asr/whisper.py:50`) and passes it **per
  transcribe** → `model.transcribe(..., language=language)` (`whisper.py:105,124`).
- **Sherpa Whisper (aarch64)** bakes it into the recognizer **at construction** → `from_whisper(..., language=language)`
  (`irene/providers/asr/sherpa_onnx.py:112,121`), from `[asr.providers.sherpa_onnx].default_language` (`:55`).
- The ASR component forwards `[asr].default_language` on every call (`asr_component.py:161,214,243/282`).

So an EN config just flips the flag — but at **two levels that must agree**: `[asr].default_language` (component;
drives torch-Whisper + is passed down) **and** `[asr.providers.<provider>].default_language` (provider; drives
sherpa-Whisper at build). The shipped RU configs set both to `"ru"` (`config-master.toml:264,282`); EN sets both to
`"en"`. **Contrast armv7:** `vosk-model-small-ru` is a *monolingual* transducer — no flag can make it emit English,
hence the model swap (I18N-2). This is the exact line between "config-only" (64-bit) and "new asset" (armv7).

### 2c. armv7 ASR decision (I18N-2 ✓) — **zipformer-en-20M**, measured
Both candidates were run locally (WER is architecture-independent, so the head-to-head is valid off-WB7):

| | zipformer-en-20M | moonshine-tiny-en |
|---|---|---|
| int8 on-disk | **43.6 MB** (≈ `vosk-small-ru` 27 MB tier) | 123.5 MB (~3×; whisper-base tier) |
| WER (2 LibriSpeech clips, shared refs) | 0.091 | **0.030** |
| streaming | yes (online transducer) | no (offline) |
| arm32 wheels | **proven** (`linux_armv7l`) | unconfirmed |
| code delta | **~zero** (reuses the `_is_streaming` online-transducer path) | new `model_type` + `from_moonshine` (4-file pack) |

**Decision: zipformer-en-20M.** Moonshine is more accurate but **has no home** — on armv7 it is ~3× the size budget and
arm32-unproven; on aarch64/x86_64 it is redundant with multilingual Whisper (which beats both). The armv7 tier is
*slim + arm32-proven + torch-free*, and zipformer fits it, accepting small-model WER (the same accuracy-for-size trade
`vosk-small-ru` makes for Russian). Shipped: catalog entry `zipformer-en-20M` + `model_type="zipformer-streaming"`
(routes through the existing online-transducer path) in `irene/providers/asr/sherpa_onnx.py`; gates green (pyright 0,
suite 1105, import-linter 9/9, config-validator 100%). **Residual (not blocking):** on-WB7 RAM/latency is a deployment
checkbox folded into I18N-4 — it cannot flip a size/arch decision this lopsided. The ~9% WER is indicative (2 clips,
quick harness); the real English WER measurement rides with I18N-5's English fixtures through the live provider.

---

## 3. Eval design — one bulk per language (I18N-5, harness ✓; fixtures pending)

The voice pipeline is monolingual-per-config (§1a), so language is a **run-level axis**, exactly like `TARGET`/`CONFIG`.
As built:
- **`EVAL_LANG` axis** in `eval/Makefile` (default `ru`), **derived from the CONFIG name** (`*-en` → `en`) so it tracks
  the SUT config; override-able for a remote SUT. Named `EVAL_LANG`, **not `LANG`** — the latter is the POSIX locale var
  and would leak into the SUT/promptfoo environment.
- **Fixtures + traces are language subdirectories** — `fixtures/<lang>/`, `traces/<lang>/`, same scenario filenames
  across languages (coverage parity = a directory diff). Cases resolve `fixtures/{{env.EVAL_LANG}}/…` and
  `traces/{{env.EVAL_LANG}}/…`, so the *path* is language-agnostic; only the fixture bytes + `reference` + rubric differ.
- Each case carries **`metadata.language`**; a run filters `--filter-metadata language=$(EVAL_LANG)` (composes with
  `kind=ux` — promptfoo ANDs multiple `--filter-metadata`). One test file, both languages, one language per run.
- **`EVAL_ROOM`** (derived from `EVAL_LANG`: `Кухня`/`Kitchen`) — the WS room name is echoed in the "no devices in
  session <room>" failure reply, so it must match the run language or an English reply carries a Russian word.
- **EN config profiles** `profiles/configs/*-en.env` point local bring-up at the `-en` toml (I18N-4).
- **EN rubrics** `shared/rubrics/en-ux.yaml` (`polite_helpful_en`/`confirms_action_en`/`graceful_failure_en`) — co-equal
  conditions mirroring the TEST-16 Russian structure. **Validated live** against DeepSeek: 7/7 agreement (passes genuine
  English, fails Russian/error/rude/non-confirmation). The RU ws cases were also migrated to the co-equal rubrics.
- **Verified:** the Russian suite is green under the new layout (`make ws CONFIG=embedded-armv7` = 4/4).
- **Remaining (mic-dependent):** record `fixtures/en/{timer_10min,light_unreachable}.wav` and the `traces/en/`
  golden — the only piece that needs a person at a microphone; everything else (axis, rubrics, cases, configs) is done.

---

## 4. Config plan — `*-en.toml` per architecture

Config-only overrides (from the §2 matrix), one variant per deployment arch. **Language flag = set `default_language`
at BOTH levels and keep them equal** (per §2a): `[asr].default_language` **and** `[asr.providers.<active>].default_language`,
plus the top-level/workflow `default_language`.
- `embedded-armv7-en.toml` — top-level `default_language="en"` + `supported_languages`; ASR `model` → the spike winner +
  matching `model_type` + `[asr]`/`[asr.providers.sherpa_onnx].default_language="en"`; TTS Piper `voice="amy"`;
  `auto_detect_language=false`; workflow `default_language="en"`. (armv7 is the ASR **model swap**, not just a flag.)
- `embedded-aarch64-en.toml` — ASR `whisper-small` stays (multilingual); flip `[asr]` + `[asr.providers.sherpa_onnx].default_language="en"`
  (already wired at inference, §2a); TTS Piper `amy` (replaces `piper_ruaccent`, which is Russian-stress-specific).
- `standalone-x86_64-en.toml` — ASR torch-whisper model stays; flip `[asr]` + `[asr.providers.whisper].default_language="en"`
  (already wired, §2a); TTS → **`silero_v3` `v3_en`** (torch parity; `silero_v4` has no English). `default_provider="silero_v3"`,
  `[tts.providers.silero_v3] model_id="v3_en"`, an `en_*` `default_speaker`, `put_accent=false`/`put_yo=false`.

`config-master.toml` stays the canonical reference; these are deployment variants (`config-master-canonical`).

**Symmetry — the RU configs are now explicitly RU-only.** Previously the three Russian configs set only the legacy
`language = "ru"` with `auto_detect_language = true`, so `default_language` fell to the schema default and
`supported_languages` to `["ru","en"]` — implicitly bilingual at the text layer. Since the voice pipeline is
monolingual-per-config (§1a) and auto-detect only ever changed the response *string* (never ASR/TTS), the RU configs now
set `default_language="ru"` + `supported_languages=["ru"]` + `auto_detect_language=false` — parallel to the `-en`
variants, one honest language per config. (`config-master.toml` keeps `["ru","en"]` — it is the comprehensive reference,
not a deployment.)

---

## 5. Code deltas (small)
- **sherpa ASR catalog** (`irene/providers/asr/sherpa_onnx.py`): add the EN pack (spike winner) + a `zipformer-streaming`
  (and/or `moonshine`) `model_type` if not already handled by the transducer path.
- **Piper TTS catalog** (`irene/providers/tts/piper.py`): generalize the hardcoded `ru_RU` URL to a locale parameter;
  add `en_US-amy-medium` (+ `lessac`/`ryan`). No provider/runtime change — same `.tar.bz2` packs, same sherpa runtime.
- **Silero v3 English** (`irene/providers/tts/silero_v3.py`): the provider **already exists** — this is an *adjustment*,
  not a new provider. `v3_en` is already in its catalog (`:78`); it just needs to **pull the model by language**: select
  `model_id` (`v3_ru`/`v3_en`) + the matching speaker set (`en_0…en_117`) from config/language instead of the current
  Russian hardcode (`_default_speakers`/`speaker_by_assname` ru, `get_capabilities` → `languages: ["ru-RU"]` at `:136`),
  and skip the Russian `put_accent`/`put_yo` path for English. Same torch runtime — no new dependency.

## 6. Scope boundaries / non-goals
- **No auto-detect wiring.** Language stays a per-config/deployment choice (§1a). ASR/TTS runtime language-switching is
  explicitly out of scope.
- **config-ui unaffected.** No new `CoreConfig` schema fields — the `*-en.toml` variants only change existing field
  *values* (`config-ui-stays-functional` has nothing to update; noted so it isn't re-checked).
- **Wake word** — English wake-phrase models are deferred (armv7 wake is ESP32/on-device; 64-bit wake is usually
  disabled in these profiles).
- **Real EN deployment ≠ perfect EN UX.** Small ASR models trade accuracy for size (same tradeoff as `vosk-small-ru` on
  armv7); acceptable for a command-oriented assistant with keyword NLU.

## 7. Implementation tasks (filed off this design)
- **I18N-2** [ASSET] ✓ — armv7 EN ASR spike → **zipformer-en-20M** chosen + added to the sherpa catalog (§2c).
- **I18N-3** [ASSET] ✓ — EN Piper voices (satellites): catalog generalized to a locale param, added `en_US-amy`/`lessac`/`ryan`; capabilities report per-instance language.
- **I18N-7** [ASSET] ✓ — Silero v3 English (standalone): `silero_v3` now pulls speakers/accent/language by model (`v3_en` → `en_0…en_117`, no Russian `put_accent`). Real `v3_en` synthesis verified (57 MB, `en_0` OK).
- **I18N-4** [CONFIG] ✓ — the three `*-en.toml` variants (§4); also made the three RU configs explicitly RU-only (symmetry: `default_language`/`supported_languages`/`auto_detect_language=false`).
- **I18N-5** [EVAL] ✓ — bilingual eval harness: `EVAL_LANG` axis, language-subdir fixtures/traces, en config profiles, en rubrics validated 7/7, ru suite green.
- **I18N-8** [EVAL] — record `fixtures/en/*` + a `traces/en/` golden (mic-dependent tail of I18N-5), then the English suite runs green.
- **I18N-6** [CONTENT] ✓ — audited `en.json` donations: functional parity across all 13 handlers (structure + phrases); empty English lemmas are appropriate (additive, morphological — English needs none). No fill required.
