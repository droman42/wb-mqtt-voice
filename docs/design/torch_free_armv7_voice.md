# Torch-free inference & the armv7 voice stack — ARCH-24 design notes

**Status:** research/analysis session 2026-06-15 (**no code**). Captures findings + decisions-in-principle so we can
resume later. Backs **ARCH-24**. Revises the ARCH-9 thesis ("whisper and silero stay first-class") **for the armv7
target only** — torch stays fully supported on 64-bit installs.

**Trigger:** the deferred torch/transformers Dependabot alerts (see commits `05aa763`/`4e05a38` — torch ×4, transformers
×1, protobuf/sentencepiece) prompted the question: *"torch is heavy ML machinery and we only do inference — are there
slimmer options?"* Plus the user's concrete need: a **self-contained VAD + ASR + TTS on the Wirenboard 7 (armv7l)**.

---

## 1. Where torch actually lives (today)

Torch is **not** a core dependency. It is opt-in via two optional extras, and `transformers` is only ever transitive:

| Dep | How it enters | Imported by |
|---|---|---|
| `torch` / `torchaudio` | `advanced-asr` extra (`pyproject` "Required by Whisper") **+** direct import in Silero TTS | `providers/asr/whisper.py`, `providers/tts/silero_v3.py`, `providers/tts/silero_v4.py` |
| `transformers` | **transitive only** — via `runorm` (`text-multilingual` extra) | **nothing in our code** — `runorm` normalizer is `enabled = false` by default in `config-master.toml` |

So the default ONNX path (sherpa-onnx ASR, openWakeWord, Silero **VAD**) is already torch-free; Whisper ASR and Silero
**TTS** are the only torch holdouts. The codebase philosophy is already "ONNX everywhere" (pyproject annotates the
sherpa/openWakeWord paths "NO torch").

**Migration surface is tiny** (both are 2-call provider seams):
- Whisper: `whisper.load_model(size)` + `model.transcribe(path, language=)` → text.
- Silero: `torch.package.PackageImporter(.pt).load_pickle(...)` + `model.apply_tts(text, speaker, sample_rate)` → waveform.

---

## 2. The two replacements (research-backed)

### 2a. Whisper ASR → sherpa-onnx Whisper  ✅ low risk
- sherpa-onnx (**already shipped**, both arches) supports Whisper natively: `OfflineRecognizer.from_whisper(...)`.
  Same weights → accuracy parity; prebuilt int8 exports `csukuangfj/sherpa-onnx-whisper-*`.
- armv7l wheels confirmed; ORT is statically linked (no separate `onnxruntime` pip package).
- **Rejected alternatives:** faster-whisper/CTranslate2 (no armv7 wheel at all), onnx-asr / standalone-onnxruntime
  (Microsoft ships **no armv7l onnxruntime wheel** — aarch64 only), transformers pipeline (needs torch).
- Fallback if speed disappoints on-device: pywhispercpp (piwheels armv7 build, torch-free GGML).

### 2b. Silero TTS → **no torch-free Silero exists**; use Piper  ⚠️ quality trade-off
- **Definitive finding:** nobody has ported Silero TTS to ONNX/sherpa, and it's **blocked at the source.** Silero
  refuses ONNX export of the TTS net (issue #283, verbatim: exposing it would reveal the accentor/homograph internals);
  no Russian ONNX TTS exists in `models.yml`; architecture is undisclosed Tacotron-lineage (not VITS); sherpa-onnx has
  no Silero loader and would need new C++ even given an ONNX. **Every** public "Silero TTS" artifact is still torch.
- **The clean torch-free path = Piper** (OHF-Voice/piper1-gpl), VITS, ONNX-native, **also runs through sherpa-onnx**
  (`OfflineTts`, VITS family). Official `ru_RU` voices: irina/denis/dmitri/ruslan, pre-packaged in the k2-fsa zoo
  (`vits-piper-ru_RU-*-medium`), tiny (~60–75 MB), armv7-capable.
- **Trade-off:** Piper Russian phonemizes via **espeak-ng**, weaker on lexical stress/homographs than Silero's bundled
  accentor. Mitigation: **RUAccent** (Den4ikAI/ruaccent, Apache-2.0, onnxruntime+numpy, **torch-free**, ~0.96 acc,
  homographs + ё) as a **preprocessing step** — but see the armv7 wall in §4.

---

## 3. Provider inventory & armv7 viability

**ASR** (one provider runs on armv7: `sherpa_onnx`; the Kaldi `vosk` provider does **not**):

| Provider | armv7? | Note |
|---|---|---|
| `sherpa_onnx` | ✅ | the armv7 ASR; loads vosk-model **or** whisper-int8 (one provider, choice of model) |
| `vosk` (Kaldi) | ❌ | not on armv7 |
| `whisper` (torch) | ❌ | → folds into sherpa_onnx |
| `google_cloud` | ✅* | cloud, not offline |

**VAD** — already solved torch-free: `silero` VAD loads `silero_vad.onnx` (dep `asr-onnx`, reuses sherpa runtime) ✅;
`energy` (pure-python) ✅; `microvad` (tflite) ❌ 64-bit only.

**TTS:**

| Provider | Dep | armv7? | Note |
|---|---|---|---|
| `console` | none | ✅ | debug only (current armv7 default) |
| `pyttsx` | pyttsx3 → espeak-ng | ✅ | works today, tiny, torch-free — robotic |
| `elevenlabs` | httpx (cloud) | ✅* | needs internet + key, not offline |
| `vosk_tts` | onnxruntime + 746 MB model | ❌ | no armv7 ORT wheel **and** OOM/disk — aarch64/x86 only |
| `silero_v3/v4` | torch | ❌ | excluded |
| **`piper` (new)** | sherpa-onnx runtime | ✅ | recommended offline quality option |

---

## 4. armv7 ground truth — the real WB7 (SSH 192.168.110.250, 2026-06-15)

| Fact | Value | Consequence |
|---|---|---|
| SoC | Allwinner sun8i **Cortex-A7 quad**, armv7l, NEON/vfpv4 | weak cores → Piper RTF may be 1–3× (consider Piper **"low"** model) |
| RAM | **1 GB total, ~367 MB *available*** (java 352 MB + wb services use ~600 MB) + 256 MB swap | Irene's whole stack must fit ~367 MB + swap backstop |
| Disk | **784 MB free** (2 GB rootfs, 58% used) | rules out Whisper small (470 MB) & vosk_tts (746 MB) on disk alone |
| glibc | **2.31** | newer `sherpa-onnx-core` needs ≥2.35 → **stays pinned at `sherpa-onnx==1.10.46`** (matches pyproject) |
| Python | **3.9** | wheels must be cp39 |
| Irene installed? | **No** — vanilla WB7 | numbers above are the baseline to deploy *into* |

**The armv7 ORT wall:** anything depending on the **standalone `onnxruntime` pip package** (RUAccent, vosk_tts,
onnx-asr) is blocked on armv7l — no Microsoft armhf wheel — and **cannot** borrow sherpa-onnx's statically-linked ORT.
So on WB7: **Piper *direct only*** (espeak-ng stress). RUAccent + vosk_tts are **64-bit-only** options.

### Honest per-model memory (disk + approx resident RAM, int8; estimates, not WB7-benchmarked)

| Stage / model | Disk | RAM | WB7 |
|---|---|---|---|
| VAD Silero (ONNX) | ~2 MB | ~30 MB | ✅ |
| ASR vosk-model-small-ru | ~27 MB | ~120 MB | ✅ **recommended** |
| ASR Whisper tiny / base / small int8 | 75 / 145 / 470 MB | ~200 / ~350 / ~800 MB | tiny⚠ base⚠ small❌ |
| TTS Piper ru medium (+espeak-data) | ~75 MB | ~150 MB | ✅ **recommended** |
| TTS pyttsx/espeak | ~5 MB | ~25 MB | ✅ fallback |
| RUAccent | ~50–200 MB | ~300–500 MB | ❌ (ORT wall) |
| vosk_tts model | 746 MB | >1 GB | ❌ |
| torch (any Silero) | — | ~1–2 GB | ❌ |

**Recommended WB7 standalone stack:** Silero-VAD + sherpa_onnx/vosk-small + Piper-direct ≈ **~105 MB disk / ~300 MB
RAM** — fits, but tight; prefer **lazy TTS load** over the profile's blanket `preload_models = true`.

**Whisper is NOT for WB7** — disk + RAM bar it, and tiny/base are worse at Russian than vosk-small. Whisper-via-sherpa
is the **64-bit** win (small/medium fit there).

---

## 5. Decisions in principle (to confirm when we resume)

1. **Whisper → sherpa-onnx** as a model option behind the existing `sherpa_onnx` provider. 64-bit-focused. **Agreed.**
2. **Silero stays torch**, supported on 64-bit installs; **excluded from armv7** by packaging + a validated profile.
3. **New `piper` TTS provider** via sherpa-onnx `OfflineTts`: **direct** (armv7 + 64-bit) and **+RUAccent** (64-bit only).
4. **armv7 role change:** today `embedded-armv7.toml` is a **headless satellite** (mic/playback/TTS **off**, ESP32 wakes
   on-device). A self-contained voice WB7 is a **new profile** (mic + playback + TTS on).

## 6. Work threads (for ARCH-24 when scheduled)

- **T1** Whisper-in-sherpa: extend `sherpa_onnx` ASR to load Whisper int8 models (config `model_type`), retire torch
  from `whisper.py` path (or keep `whisper` provider as a 64-bit alias). Verify Russian parity.
- **T2** New `piper` TTS provider (sherpa `OfflineTts`/VITS); `ru_RU` voice asset; direct + optional RUAccent stage.
- **T3** Platform taxonomy + validation: add `armv7l` to provider `get_platform_support()` taxonomy; extend the CI
  `dependency_validator --platforms` to include armv7 so **any armv7 profile enabling a torch provider fails the build**;
  author a real standalone `embedded-armv7` profile (mic/playback/TTS on, lazy TTS load).
- **Open checks:** (a) **verify `sherpa-onnx==1.10.46` cp39 armv7 wheel exposes `OfflineTts`/VITS** on the real WB7
  (the one must-pass before committing to Piper-via-sherpa); (b) Piper medium vs "low" RTF on the A7; (c) on-device RAM
  peak with all three models loaded.

## 7. Dependabot linkage

Completing T1+T2 (drop torch from the default/armv7 build) is the real resolution for the deferred **torch ×4** and
**transformers ×1** alerts (and the protobuf/sentencepiece weight) — far cleaner than risky major bumps. Until then
those alerts stay deferred (low/medium, only reachable via the opt-in ML extras).
