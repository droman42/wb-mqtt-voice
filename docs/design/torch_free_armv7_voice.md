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
| **`piper` (new)** | sherpa-onnx runtime | ✅ | base provider — all envs incl. armv7; the WB7 TTS |
| **`piper_ruaccent` (new)** | `piper` + `ruaccent` (onnxruntime + transformers) | ❌ armv7 | subclasses `piper`, adds RU stress; **x86_64/aarch64 only** (ORT wall) |

---

## 4. armv7 ground truth — the real WB7 (SSH 192.168.110.250, 2026-06-15)

| Fact | Value | Consequence |
|---|---|---|
| SoC | Allwinner sun8i **Cortex-A7 quad**, armv7l, NEON/vfpv4 | weak cores → Piper RTF may be 1–3× (consider Piper **"low"** model) |
| RAM | **1 GB total. ~367 MB available *with SprutHub running*; ~712 MB after SprutHub was stopped+disabled (2026-06-15, frees ~343 MB)** + 256 MB swap | the three deploy containers fit in ~712 MB |
| Disk | **`/mnt/data` = 4.7 GB, 2.3 GB free** (docker root = `/mnt/data/.docker`); rootfs `/` has only ~785 MB free **but images + models live on `/mnt/data`** | disk is **NOT** the constraint (my earlier "784 MB" cited the wrong partition); vosk_tts/Whisper-small are barred by **RAM**, not disk |
| glibc | **2.31** | newer `sherpa-onnx-core` needs ≥2.35 → **stays pinned at `sherpa-onnx==1.10.46`** (matches pyproject) |
| Python | **3.9** | wheels must be cp39 |
| Deployment | **dockerized** — Irene runs as a container alongside `wb-mqtt-bridge` + `wb-mqtt-ui` (Irene's own `config-ui` is **NOT** deployed on WB7) | armv7 images already on GHCR (`ghcr.io/droman42/*`, linux/armv7) |

> **Topology (corrected 2026-06-15):** the **ESP32 satellites** own mic capture, **VAD**, **wake-word/voice-trigger**, and
> audio **playback**. WB7's Irene is the **back half only** — it receives a gated, segmented utterance, runs
> **ASR → NLU → intent → TTS**, and streams TTS PCM **back** to the ESP32 (ARCH-21/22 reply channel). So WB7 has **no
> server-side VAD, no voice-trigger, no local mic/speaker** (`skip_wake_word=True`).

**The armv7 ORT wall:** anything depending on the **standalone `onnxruntime` pip package** (RUAccent, vosk_tts,
onnx-asr) is blocked on armv7l — no Microsoft armhf wheel — and **cannot** borrow sherpa-onnx's statically-linked ORT.
So on WB7: **Piper *direct only*** (espeak-ng stress). RUAccent + vosk_tts are **64-bit-only** options.

### Honest per-model memory (disk + approx resident RAM, int8; estimates, not WB7-benchmarked)

| Stage / model | Disk | RAM | WB7 |
|---|---|---|---|
| VAD Silero (ONNX) | ~2 MB | ~30 MB | **ESP32, not WB7** (✅ on 64-bit standalone) |
| ASR vosk-model-small-ru | ~27 MB | ~120 MB | ✅ **recommended** |
| ASR Whisper tiny / base / small int8 | 75 / 145 / 470 MB | ~200 / ~350 / ~800 MB | tiny⚠ base⚠ small❌ |
| TTS Piper ru medium (+espeak-data) | ~75 MB | ~150 MB | ✅ **recommended** |
| TTS pyttsx/espeak | ~5 MB | ~25 MB | ✅ fallback |
| RUAccent | ~50–200 MB | ~300–500 MB | ❌ (ORT wall) |
| vosk_tts model | 746 MB | >1 GB | ❌ |
| torch (any Silero) | — | ~1–2 GB | ❌ |

**Recommended WB7 stack (satellite-server role):** Irene = **ASR (sherpa/vosk-small) + NLU + intent + TTS (Piper-direct)**
only — no VAD/voice-trigger (ESP32's job), no local audio. Models ≈ **~114 MB** (vosk-small 27 + Piper ru-med 75 +
espeak-data 12), runtime ≈ **~280–350 MB RAM**; prefer **lazy TTS load** over the profile's blanket `preload_models = true`.

**Three-container WB7 budget (post-SprutHub, measured 2026-06-15):**

| Container | Disk | RAM (est.) |
|---|---|---|
| wb-mqtt-bridge | ~155 MB | ~120–200 MB |
| wb-mqtt-ui | ~40 MB | ~10–20 MB (nginx static) |
| Irene (backend; no config-ui) | ~120–180 MB img + ~114 MB models | ~280–350 MB |
| **Total** | **~430–490 MB of 2.3 GB free** | **~410–570 MB of 712 MB** (+256 MB swap) |

Fits with ~140–300 MB RAM headroom. Softest number = the bridge's runtime RSS (estimate, not measured).

**Whisper is NOT for WB7** — RAM bars it, and tiny/base are worse at Russian than vosk-small. Whisper-via-sherpa
is the **64-bit** win (small/medium fit there).

---

## 5. Decisions in principle (to confirm when we resume)

1. **Whisper → sherpa-onnx** as a model option behind the existing `sherpa_onnx` provider. 64-bit-focused. **Agreed.**
2. **Silero stays torch**, supported on 64-bit installs; **excluded from armv7** by packaging + a validated profile.
3. **Two Piper TTS providers** via sherpa-onnx `OfflineTts` (not one provider with an optional stage):
   (a) **`piper`** — plain VITS + espeak-ng phonemization, **all environments incl. armv7** (the WB7 TTS);
   (b) **`piper_ruaccent`** — **subclasses `piper`**, injects RUAccent stress/ё preprocessing before synth, overriding
   **only** the text-prep hook; **`x86_64`/`aarch64` only** (RUAccent needs the standalone onnxruntime wheel → armv7 ORT wall).
4. **armv7 role = satellite-*server* (NOT standalone).** The ESP32 satellites own mic + VAD + voice-trigger + playback;
   WB7's Irene is the back half — ASR/NLU/intent/TTS, `skip_wake_word=True`, **no** server VAD, mic, speaker, or
   `config-ui`. It evolves today's headless `embedded-armv7.toml` (which returns text only) by turning **TTS synthesis
   on** + wiring the ESP32 reply-channel transport — *not* by adding local mic/playback. Runs **dockerized** beside
   `wb-mqtt-bridge` + `wb-mqtt-ui`.

## 6. Work threads (for ARCH-24 when scheduled)

- **T1** Whisper-in-sherpa: extend `sherpa_onnx` ASR to load Whisper int8 models (config `model_type`), retire torch
  from `whisper.py` path (or keep `whisper` provider as a 64-bit alias). Verify Russian parity.
- **T2** **Two** Piper TTS providers (sherpa `OfflineTts`/VITS) + a `ru_RU` voice asset:
  - **`PiperTTSProvider`** (entry point `piper`) — base; espeak-ng phonemization; `get_platform_support()` = all incl.
    `armv7l`; deps = the already-shipped sherpa-onnx runtime. This is the WB7 TTS.
  - **`PiperRuAccentTTSProvider(PiperTTSProvider)`** (entry point `piper_ruaccent`) — overrides **only** the text-prep
    hook to run RUAccent (stress `+`/ё) before the inherited synth; adds the `ruaccent` dep; `get_platform_support()` =
    `x86_64`/`aarch64` **only** (armv7 ORT wall). Model load / synth / streaming all inherited from the base.
- **T3** Platform taxonomy + validation: add `armv7l` to provider `get_platform_support()` taxonomy; extend the CI
  `dependency_validator --platforms` to include armv7 so **any armv7 profile enabling a torch provider fails the build**;
  evolve the `embedded-armv7` profile from headless-ASR-satellite → **ASR+TTS satellite-server** (TTS synthesis on +
  stream PCM back to the ESP32; VAD/voice-trigger/mic/playback stay **off** — ESP32's job; no `config-ui`; lazy TTS load).
- **T4 (packaging) → BUILD-3:** **three Docker images**, each one role + one config + one manual `workflow_dispatch`
  buildx→GHCR workflow: **A** 64-bit satellite-server (x86_64 + aarch64 — servers/WB8.5/Pi, bigger models: Whisper small/med
  + Piper`_ruaccent`), **B** armv7 WB7 satellite-server (vosk-small + `piper`-direct, no torch — redo `embedded-armv7.toml`),
  **C** NEW `Dockerfile.standalone` full local `voice` runner (mic→…→playback, audio passthrough, arch TBD). A & B share the
  satellite-server role (ESP32 owns VAD/VT/audio); differ only by HW tier + model allowance. Delivered via interactive
  sessions (config per target → Dockerfile design: baked-in vs mounted volumes, ports, `/dev/snd`, entrypoint → per-image
  workflow). This is **BUILD-3** in the ledger — see it for the running scope.

- **Open checks:** (a) ~~verify `sherpa-onnx==1.10.46` cp39 armv7 wheel exposes `OfflineTts`/VITS on the real WB7~~ —
  **✅ VERIFIED 2026-06-15 on 192.168.110.250.** Downloaded `sherpa_onnx-1.10.46-cp39-cp39-linux_armv7l.whl` (14.5 MB),
  imported under the box's Python 3.9 — the compiled `.so` **loads and runs** on glibc 2.31 / Cortex-A7, and exposes both
  `OfflineRecognizer` (ASR) and `OfflineTts` + `OfflineTtsConfig` + **`OfflineTtsVitsModelConfig`** (Piper/VITS), plus
  Matcha/Kokoro configs. The "one sherpa-onnx engine carries both ASR and TTS on WB7" premise **holds on the real hardware.**
  (b) Piper medium vs "low" RTF on the A7 — still TODO; (c) on-device RAM peak with both models loaded — still TODO.

## 7. Dependabot linkage

Completing T1+T2 (drop torch from the default/armv7 build) is the real resolution for the deferred **torch ×4** and
**transformers ×1** alerts (and the protobuf/sentencepiece weight) — far cleaner than risky major bumps. Until then
those alerts stay deferred (low/medium, only reachable via the opt-in ML extras).

**Caveat on transformers:** the new `piper_ruaccent` provider's `ruaccent` dep pulls `transformers` back in (torch-free,
np-tokenization only) on 64-bit — so `ruaccent` *replaces* `runorm` as the reason transformers exists. The transformers
alert is **fully** cleared only if `ruaccent` is kept out of the default-CI extra set; the **armv7/default build stays
transformers-free regardless** (it uses plain `piper`).
