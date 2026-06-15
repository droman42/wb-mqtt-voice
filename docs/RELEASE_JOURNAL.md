# Irene — Release Journal

The **single** chronological log for the release effort ("what happened, when, and why"). Append-only;
newest entries near the top of each dated section.

- **This file holds NO task status and NO scope.** The authoritative task ledger (scope + status) is
  [`RELEASE_PLAN.md`](./RELEASE_PLAN.md); findings/rationale live in `docs/review/*` + `docs/design/*`.
- Entries reference task IDs (e.g. `QUAL-27`) but never assert their status — check the ledger for that.

---

## Action journal

### 2026-06-15
- **QUAL-52 PR2 follow-up — `context_window` in config (you flagged: only the output side was defined).** PR1 put the
  output budget (`max_tokens` → model max) into config but the input `context_window` lived only in the code registry.
  Added `context_window` to the LLM provider config + schemas (deepseek 64000 / gpt-4o 128000 / claude 200000) and a
  `context_window_for(model, override)` resolver; the providers pass it to `fit_messages`, so the budget is now fully
  config-defined (input + output), defaulting from the registry but overridable for custom models. Suite 982 green,
  pyright 0, contracts 9/9, config-ui builds (Inv #4).
- **QUAL-52 PR2 — budget-aware prompting (dependency-free).** Added `estimate_tokens` (**utf-8 bytes/4** — accurate for
  English, conservative for Cyrillic, no tiktoken so the path stays armv7-safe), `input_budget` (context_window × 0.9 −
  reserved_output), and `fit_messages` (trim oldest non-system turns to fit; **always keep system + the final message**;
  raise if the system prompt alone overflows — the QUAL-50 catalog must be scoped upstream, not blindly truncated). Wired
  `fit_messages` into all 3 providers' `chat_completion` (the multi-turn / catalog path; single-shot `enhance_text`
  untouched). `test_llm_budget.py` (5). Suite 981 green, pyright 0, contracts 9/9. Next PR3: structured/JSON output.
- **QUAL-52 PR1 — real per-model LLM token budgets.** New `utils/llm_capabilities.py`: `ModelCapabilities`
  (context_window + max_output) for deepseek / gpt-4o / 4o-mini / 4 / 3.5 / claude-4.x + a conservative fallback;
  `output_budget(model, requested)` caps any request at the model's real `max_output` and defaults to it — replacing the
  arbitrary `max_tokens=150` that truncated replies. Wired into all 3 cloud providers (deepseek/openai/anthropic: default
  None → model max, bound the per-call output). config-master + the provider schemas now carry each model's real max_output
  (8000/16384/8192), not 150. `test_llm_capabilities.py` (5). Inv #4: config-ui builds. Suite 976 green, pyright 0,
  contracts 9/9, configs valid. Next PR2: budget-aware prompting (utf-8 bytes/4 input estimate + trim oversized context).
- **QUAL-50 design confirmed + filed QUAL-52 (LLM component rework) as its prerequisite.** Confidence is **derived**, not
  the LLM's self-rating: intent ∈ donation-set [gate] + fraction of required params that resolve against catalog/context +
  an evidence span the LLM must quote; commands need ALL required params resolved (missing → CLARIFYING; unresolvable →
  abstain), queries are lenient. Grounding 1(b): the prompt carries the live catalog + identity/session/context. Structured
  JSON output. User flagged today's LLM handling as crude + token-budget-blind → **QUAL-52** (real per-model budgets +
  budget-aware prompting + structured output + drop fine-tuning) **first**, then QUAL-50 → QUAL-51 → resume armv7 config.
- **ARCH-24 T4 (armv7 config session) — VAD made mic-conditional + filed QUAL-50/51.** Started the armv7 config session
  (deriving from config-master, the existing profiles being stale). Two findings corrected the plan: (1) **VAD** — the
  unified workflow hardcoded "VAD required for all audio" and raised if `[vad]` disabled; per the user (a MUST + correct),
  VAD is mandatory **only when microphone input is enabled** (mic streams raw ~23 ms chunks needing segmentation;
  web/ESP32 deliver bounded utterances → no server VAD). `voice_assistant.py` init now gates the raise on
  `system.microphone_enabled` and leaves `audio_processor_interface=None` when mic-off; `test_vad_phase3.py` reframed
  (raises only with mic on; no-raise+None when mic off). Suite 971 green. (The runtime no-VAD bounded→ASR path is ESP32
  integration, ARCH-22/23.) (2) **NLU** — spaCy has no armv7 wheel, so on a missed command we want an **LLM *classifier***
  fallback (recovers fuzzy commands), not just the conversation chat fallback (which doesn't execute). Filed **QUAL-50**
  (`LLMNLUProvider` — last NLU-cascade resort; deliberately revises the QUAL-15/16 LLM-free-NLU stance, last-resort only)
  + **QUAL-51** (prompt-tightening session for the classifier + keyword-matcher config). Confirmed the multi-turn
  clarification exists (`conversation.py` `ConversationState.CLARIFYING` + QUAL-37). **The armv7 config now depends on
  QUAL-50** (providers-before-configs), so the config session pauses there.
- **ARCH-24 T5 PR2 — TorchModelCache (T5 COMPLETE).** Extracted the silero v3/v4 copy-pasted model cache (class-level
  dict + `asyncio.Lock` + `_get_or_load_cached_model`) to `utils/torch_model_cache.TorchModelCache` (async, lock-guarded
  `get_or_load`: loads once per key, serializes concurrent first loads). Both silero providers now hold
  `_model_cache = TorchModelCache()` + a small `_load_model_returning` loader; ~25 dup lines × 2 removed. torch whisper
  untouched (library-cached). `test_torch_model_cache.py` (3). Suite 970 green, pyright 0, contracts 9/9, no-TYPE_CHECKING
  clean. **T5 complete → ARCH-24 code threads T1/T2/T3/T5 all done; only T4 (BUILD-3 images + config sessions) remains.**
- **ARCH-24 T5 PR1 — shared InferencePolicy.** Extracted the sherpa thread/CPU budget (was `SherpaInferencePolicy` in the
  ASR provider, a duplicated `_num_threads` in piper, and ignored by silero VAD) to `utils/inference_policy.InferencePolicy`.
  Now shared by sherpa ASR + Piper TTS + silero VAD (which now sets `cfg.num_threads` — sherpa's `VadModelConfig` has it).
  `SherpaInferencePolicy` kept as a back-compat alias; piper's `_num_threads` removed. Decided a full `SherpaSession`
  build-helper isn't worth it — the session APIs (`from_transducer`/`from_whisper`/`OfflineTts`/`VAD`) don't unify; only the
  thread budget is shared. `test_inference_policy.py` (4). Suite 967 green, pyright 0, contracts 9/9 (utils→utils +
  providers→utils legal), no-TYPE_CHECKING clean. Next: PR2 — `TorchModelCache` for silero v3/v4.
- **ARCH-24 T3 PR2 — the armv7 build gate (T3 tooling COMPLETE).** `IreneBuildAnalyzer.validate_architecture(config,
  arch)` reuses the enabled-provider analysis + `get_supported_architectures()` to flag a profile enabling an
  arch-incapable provider; new `--arch` CLI flag exits nonzero on failure. Wired into `backend-health.yml`
  (`build_analyzer --config embedded-armv7 --arch armv7l`) — a torch/onnxruntime provider in the WB7 image now fails CI.
  Verified: embedded-armv7 passes; config-master fails on armv7l (whisper fallback) and passes on x86_64. `test_arch_gate.py`
  (3). Suite 964 green, pyright 0, contracts 9/9, YAML valid. T3 mechanical work done (taxonomy + gate); the
  embedded-armv7→satellite-server profile *content* is the BUILD-3 config session, now guarded by the gate.
- **ARCH-24 T3 PR1 — architecture-support taxonomy.** User chose the explicit-arch-method approach (over markers/hybrid).
  New `EntryPointMetadata.get_supported_architectures()` (default `[x86_64, aarch64, armv7l]`); 8 armv7-incapable providers
  override to `["x86_64","aarch64"]`: silero_v3/v4 + whisper (torch — no armv7 wheel), vosk_tts + piper_ruaccent +
  openwakeword (standalone onnxruntime — no armv7 wheel), microwakeword + microvad (pymicro). The PEP 508 extra markers
  stay as the install-time guard. `test_arch_support.py` (13). Suite 961 green, pyright 0, contracts 9/9,
  dependency_validator 118/118 (additive). Next: PR2 — the `build_analyzer --arch` profile gate + CI step.
- **ARCH-24 T2 PR3 — PiperRuAccentTTSProvider (T2 COMPLETE).** Subclass of `PiperTTSProvider` (entry point
  `piper_ruaccent`) overriding ONLY `_prepare_text` to run RUAccent (Russian stress `+`/ё) before the inherited sherpa
  synth. New `tts-ruaccent` extra (`ruaccent>=1.5.8; platform_machine != 'armv7l'` — 64-bit only; armv7 resolves to
  nothing, like pymicro); deps `["asr-onnx","tts-ruaccent"]`. Full integration (the PR2 lesson): `PiperRuAccentProviderSchema`
  registered + `[tts.providers.piper_ruaccent]` config-master block (8/8 TTS). **User caught** that `RUAccent.load()`
  downloads its NN models from HF and defaults `workdir` to its own (ephemeral, maybe read-only) package dir → pointed it
  at `models_root/ruaccent/` (mounted volume). `test_piper_ruaccent.py` (5; accentizer mocked — no model pull). Gates:
  suite 948 green, schema-unification 19/19, pyright 0, contracts 9/9, no-TYPE_CHECKING clean, dependency_validator
  118/118, config_validator valid, config-ui builds; uv.lock += ruaccent/python-crfsuite. **Open:** the RUAccent `+` ↔
  espeak stress-bridge is an on-device A/B item. T2 done; ARCH-24 remaining: T3 (taxonomy/validator/profile) / T4 (BUILD-3
  packaging) / T5 (shared helpers).
- **ARCH-24: config-master + parameter schema for piper (Inv #2/#4 — gaps from PR2/T1).** User caught that PR2 added the
  `piper` provider without the canonical `config-master.toml` block (it documents every provider — was 6/7 TTS) and that
  T1's `whisper-small` pack wasn't in the sherpa `model` list. The completeness test (`test_parameter_schema_unification`)
  enforces config-master↔schema alignment: adding the `[tts.providers.piper]` block first surfaced it as **orphaned** (no
  registered schema). Fixed properly: new `PiperProviderSchema(TTSProviderSchema)` (voice/speaker_id/speed/num_threads/
  preload_models) registered in `auto_registry`; added the config-master block (now **7/7 TTS** = all entry points) +
  `whisper-small` to the sherpa `model` comment. **Inv #4:** config-ui builds + type-checks clean — it consumes providers
  **dynamically** via the `/config/providers` endpoint (no per-provider typing in `openapi.gen.ts`), so the new provider is
  additive. Gates: suite 943, schema-unification 14/14, pyright 0, contracts 9/9, config_validator valid.
- **ARCH-24 T2 PR2 — PiperTTSProvider (base).** New `providers/tts/piper.py` + entry point `piper`: VITS via sherpa-onnx
  `OfflineTts` (the one armv7 ONNX engine), one provider with the `voice` chosen by config (irina/ruslan/denis/dmitri
  k2-fsa packs → `download_model(extract=True)` → `piper/<voice>/`, resolved recursively since the tarball nests).
  `synthesize_to_file` + native-streaming `synthesize_to_stream`; **numpy-free** PCM conversion (armv7 has no numpy wheel —
  same policy as the sherpa ASR provider); `_prepare_text` hook that PR3's ruaccent subclass overrides. Deps = `asr-onnx`;
  no torch, no system espeak-ng/bz2 (espeak statically linked in sherpa, espeak-ng-data ships in the pack, bz2 in the
  python base). sherpa `OfflineTts*` API verified against the installed wheel. `test_piper_tts.py` (7). Gates: suite 943
  green, pyright 0, contracts 9/9, no-TYPE_CHECKING clean, dependency_validator 58/58, build_analyzer + config_validator
  valid; uv.lock unchanged. Inv #4 N/A (free-form provider config). Next: PR3 ruaccent subclass.
- **ARCH-24 T2 started — PR1: asset-layer `.tar.bz2` support (Piper prerequisite).** Piper TTS voices ship as k2-fsa
  `.tar.bz2` (model.onnx + tokens.txt + `espeak-ng-data/`; both ru voices irina/ruslan verified live at the k2-fsa
  release). `_extract_archive` only dispatched .tar/.tar.gz/.tgz (and `Path.suffix` on `foo.tar.bz2` is `.bz2`), header
  check knew gzip not bzip2 → a Piper voice would fail "Unsupported archive format". Extended dispatch (full-name match +
  bzip2 `BZh`/xz magic; tarfile `r:*` decompresses). New `test_asset_extract.py`. **Env finding:** the custom dev/CI
  CPython (/usr/local 3.11.4) was built **without `bz2`** (like `_sqlite3`) → bz2 tests `skipif`; Docker `python:3.11-slim`
  has libbz2 so real extraction works. Suite 936 green / 9 skipped, pyright 0, contracts 9/9. Next: PR2 PiperTTSProvider.
- **QUAL-49 — silero model-id routing fix.** The ARCH-24 asset-routing analysis (how multi-model providers route models
  to subfolders) found silero v3/v4 were the only providers bypassing the `get_model_path(provider, model_id)` router —
  flat `<dir>/<config:model_file>` with a shared default, so v3 languages could collide on one file. Fixed: route via
  `get_model_path("silero_v{3,4}", model_id)`, model_url from the descriptor, download via the real provider name (drops
  the `"silero"`-fallback + copy hack). `test_silero_routing.py` (4). Inv #4 N/A (free-form provider config). Suite 935
  green, pyright 0, contracts 9/9. Relates to ARCH-24 T5 (done early). _(Also confirmed sherpa already subfolders by
  model_id — `sherpa_onnx/<model_id>/`; the routing lives in the AssetManager, not the provider.)_
- **ARCH-24 formally started — T1 finished (code).** Task-start reconciliation (Inv #8): T1 = case (b) partially
  addressed (the `model_type=whisper` branch + tiny/base packs + their tests already shipped under ARCH-10 PR-2, confirmed
  in `onnx_inference_layer.md`); narrowed to "add the `whisper-small` pack + test" (user-approved "we do the rest of T1").
  Read the backing review doc (Inv #5). Verified `csukuangfj/sherpa-onnx-whisper-small` live on HF (HTTP 200,
  `small-{encoder,decoder}.int8.onnx` + `small-tokens.txt`) before wiring it. Added the `whisper-small` descriptor to
  `sherpa_onnx.py` `_get_default_model_urls()` + `test_whisper_small_pack_for_aarch64`. Suite 931 passed / 0 failed (+1),
  pyright 0, import contracts 9/9; Inv #4 N/A (no contract/schema/config-ui change), Inv #9 N/A (no TYPE_CHECKING). **T1
  code-complete; the on-device verify (RU parity + A53 RTF) stays an open check — gated on WB8 hardware (none on hand).**
- **ARCH-24: T1 found already-implemented; added T5 (shared-runtime helpers).** Code-read of `irene/providers/asr/
  sherpa_onnx.py`: Whisper-via-sherpa is **already done** — the provider branches on `model_type` (`whisper`→`from_whisper`,
  `:128-143`; tiny/base packs declared `:358-372`). It's ONE provider with a `model_type` discriminator (not a separate
  provider, not a base/derived split — the branch surface is ~3 points; decode/audio/asset/policy all shared). So T1
  shrinks to "add a whisper-small pack + verify on aarch64"; T2 (Piper) is the real new provider work. Also analysed the
  "no common inference-engine abstraction" question: it's **mostly inherent + deliberate** (ARCH-9 abstracted assets, not
  sessions; per-library APIs don't unify; ORT bundled in sherpa) with one **narrow intra-runtime gap** → filed **T5**:
  factor a thin `SherpaSession`/`InferencePolicy` helper (sherpa ASR+VAD+TTS; silero VAD currently ignores the thread
  policy) when T2 lands, + optional `TorchModelCache` for silero_v3/v4 (torch `whisper.py` doesn't need it — library-cached).
  Also confirmed the **ESP32 reply channel is already implemented** (`outputs/remote_audio.py` `speak_begin→PCM→speak_end`).
- **ARCH-24/BUILD-3 target matrix finalized — 3 images by architecture, torch in one.** Consolidated a run of decisions:
  (1) Dockerfiles split **by arch** — `Dockerfile.x86_64`→standalone full-voice, NEW `Dockerfile.aarch64`→WB8/Pi satellite,
  `Dockerfile.armv7`→WB7 satellite. (2) Researched **WB8.5 = aarch64** (Allwinner T507 Cortex-A53, 4 GB, Debian 11) →
  Whisper-on-sherpa is feasible there, and **torch aarch64 wheels exist** (verified on PyPI) but torch is **deliberately
  excluded** from aarch64. (3) **Per-target stacks:** standalone = torch (Whisper + Silero v4); both ARM satellites =
  torch-free sherpa (aarch64: Whisper-small + Piper+RUAccent; armv7: vosk-small + Piper-direct). (4) Provider work — T1's
  sole consumer is aarch64; T2 serves both satellites; standalone needs no new providers (supersedes the "64-bit optional"
  framing). (5) **Config strategy** — bake for the two satellites; baked-default + external override (full-dep build) for
  standalone. All recorded in the design doc (new §5 "Deployment matrix" = source of truth) + BUILD-3. No implementation.
- **BUILD-3 reopened as ARCH-24's packaging thread — three Docker images.** Coupled the deferred Docker-build task to
  ARCH-24 now the architecture has settled. Three targets, each = one role + one config + one manual `workflow_dispatch`
  workflow: **A** 64-bit satellite-server (x86_64/aarch64 — WB8.5/Pi, bigger models), **B** armv7 WB7 satellite-server
  (vosk-small + piper-direct; redo the bad `embedded-armv7.toml`), **C** NEW standalone full-`voice` runner (arch TBD →
  Session 4). User refinement: **A & B are the same satellite-server role** (ESP32 owns VAD/VT/audio), differing only by HW
  tier + model allowance. Two profile-parameterized Dockerfiles exist (`Dockerfile.x86_64`, `.armv7`); C's is new.
  Interactive sessions to follow: config per target → Dockerfile design (baked vs mounted) → per-image workflow.
- **ARCH-24 gating check VERIFIED on the real WB7 — sherpa-onnx 1.10.46 does TTS.** The whole "one ONNX engine for both
  ASR + TTS on armv7" plan hung on whether the pinned `sherpa-onnx==1.10.46` armv7 wheel exposes `OfflineTts` (the box's
  glibc 2.31 blocks the newer `sherpa-onnx-core` wheels, so 1.10.46 is the ceiling). Tested directly without touching the
  system Python: downloaded `sherpa_onnx-1.10.46-cp39-cp39-linux_armv7l.whl` (14.5 MB), unzipped, imported via PYTHONPATH —
  the `.so` **loads and runs** on glibc 2.31/Cortex-A7 and exposes `OfflineRecognizer` **and** `OfflineTts` +
  `OfflineTtsVitsModelConfig` (Piper/VITS) + Matcha/Kokoro configs. Cleaned up the throwaway dir. Gate ✅; doc + ledger updated.
- **WB7 controller investigation + SprutHub stopped → ARCH-24 budget reconciled.** Diagnosed the controller's memory:
  the elephant was **SprutHub** (Java hub under `/mnt/data/makesimple`, ~352 MB RSS = 59% of used RAM); Node-RED was a
  red herring (not installed/running). Per the user's plan (bridge + dockerized Irene will run on WB7, SprutHub retired),
  **stopped + disabled both `spruthub.service` and `spruthub-update.service`** (reversible, no files removed) → available
  RAM **364 → 712 MB**. Reconciled the ARCH-24 WB7 budget against reality and **corrected the design doc**: (1) ESP32
  satellites own VAD + voice-trigger + mic/playback → WB7 Irene is ASR/NLU/intent/TTS only (no Silero-VAD, no local audio);
  (2) Irene's `config-ui` not deployed on WB7 (`wb-mqtt-ui` is) — three containers (bridge + wb-mqtt-ui + Irene); (3) disk
  budget is `/mnt/data` (2.3 GB free, docker root there), not the 785 MB rootfs; (4) post-SprutHub 712 MB available. Bridge
  armv7 images already on GHCR (`ghcr.io/droman42/*`, linux/armv7, latest = `8c39b88` 2026-05-31 — 92 commits behind main,
  rebuild needed before deploy). Three-container budget ≈ 430–490 MB disk / 410–570 MB RAM → fits with headroom.
- **ARCH-24 research session — torch-free inference & the armv7 voice stack (no code).** Started from the deferred
  torch/transformers Dependabot alerts (commits 05aa763/4e05a38) + the user's need for a self-contained VAD+ASR+TTS on
  the Wirenboard 7. Mapped the real torch surface (opt-in `advanced-asr` + Silero TTS; `transformers` only transitive via
  the default-off `runorm`), researched replacements (Whisper→sherpa-onnx confirmed; **no torch-free Silero TTS exists or
  can — Silero refuses ONNX export, issue #283 — so Piper is the path**, with RUAccent for Russian stress on 64-bit only),
  and SSH'd the actual WB7 (192.168.110.250) for ground truth: Cortex-A7 quad armv7l, **~367 MB available RAM** + 256 MB
  swap, **784 MB free disk**, glibc 2.31, py3.9 — which bars Whisper *and* vosk_tts on WB7 and pins sherpa at 1.10.46.
  Deliverable `docs/design/torch_free_armv7_voice.md`; filed **ARCH-24** (`[deferred]`, T1 Whisper→sherpa / T2 new Piper
  TTS provider / T3 armv7 platform-taxonomy + validator gate + standalone profile). Also bumped safe Dependabot deps
  (uv.lock + config-ui) — 65→14 open alerts, the 14 remainder all gated behind risky majors → folded into ARCH-24.
- **TEST-7 kicked off — gate lifted, approach locked, Phase A (coverage tooling + baseline) done.** The TEST-7 gate
  (ARCH-1..5 + QUAL-8/10/12/14) is fully `[x]`, so the suite rewrite is unblocked. Locked the approach with the user
  (6 decisions — see the ledger): same contract-level method as the release-plan new code, 100% green, delete stale
  outright, all clusters in one sweep (incl. the new-code wiring gaps), Phases A+B solo then a multi-agent workflow,
  and **pytest-cov + closing the gap is mandatory**. **Phase A:** hit an environment wall — the runtime CPython
  (3.11.4 at /usr/local/bin, shared with wb-mqtt-bridge) is built WITHOUT the stdlib `_sqlite3` extension, which
  `coverage.py` requires. Investigated the sister project (user's steer): it ships `pysqlite3-binary` and aliases
  `sys.modules['sqlite3'] = pysqlite3` via a hand-placed `sitecustomize.py` in site-packages. Mirrored it but made it
  reproducible — committed `sitecustomize.py` (source of truth) + `scripts/install_sqlite_shim.sh` (copies it into the
  venv's site-packages, where the interpreter auto-imports it at startup, before coverage's plugin-load `import
  sqlite3`). A root conftest was tried first and rejected — coverage imports sqlite3 too early for it. Along the way
  the venv had drifted to py3.12 (from a `--python 3.12` probe); restored it to 3.11.4 via the system interpreter,
  pinned `.python-version` (gitignored, local-only) to prevent re-drift, and re-synced `--all-extras` (CI's setup) to
  restore spacy/nlu/audio so the full suite collects. Added `pytest-cov` + `pysqlite3-binary` to the `dev` extra
  (uv.lock +187, additions only — no re-pins). **Baseline measured: 45.6% line coverage (17,546/38,488 across 265
  modules).** The number confirms the thesis — the request hot-path is the cold zone (`workflow_manager` 20%,
  `core/components` 20%, `context` 25%, `nlu_component` 38%, `orchestrator` 41%), new pure-logic is well-covered
  (`trace_context` 76%, `trace_input` 89%), new wiring is thin (`replay_trace`/`voice_runner` 34%). Suite still at its
  baseline (82 failed / 472 passed / 15 skipped — the ±1 is a coverage-perturbed timing benchmark, not a regression).
  Next: Phase B triage + risk-ranked worklist, then the workflow.
- **MQTT design reconciled with the bridge's value-label layer + moved-doc link fixed (both repos).** Validity check
  (no-code analysis, requested): the bridge had ~40 commits since `mqtt_integration.md` was last updated (2026-06-07),
  mostly hygiene — but two touch the contract. (1) The cross-project contract doc **moved**
  (`wb-mqtt-bridge/docs/voice_integration_contract_draft.md` → `docs/design/…`), so the Irene doc's two links were stale.
  (2) A **value-label translation layer** landed (bridge §P3.7 #26, 2026-06-09 — *postdates* both docs' AGREED-2026-06-06
  status): `/system/catalog` now projects controllable enum fields' `values` as **`{wire, canonical, labels}`** triplets
  (`CatalogValueLabel`) instead of bare strings, explicitly for voice — Irene matches the spoken `labels` in-locale and
  posts the `canonical` token; the bridge translates `canonical`↔`wire`. The CORE contract is otherwise intact (canonical
  `POST /devices/{id}/canonical`, `GET /system/catalog`, the `error.code` enum, the `bridge/catalog/version` nudge — all
  unchanged). Reconciliations made: **Irene `mqtt_integration.md`** — fixed both links, added a top reconciliation note,
  and a §5a value-label bullet (device-enum resolution rides the **QUAL-29 surface→canonical** CHOICE mechanism — no new
  mechanism; flagged the bridge's still-"owed-work" param introspection as a best-effort caveat); **ARCH-8 ledger** —
  a catalog-contract-amended pointer; **bridge `voice_integration_contract_draft.md`** (sister repo) — a "Value-labels
  for controllable enum fields" §B subsection + a status-line amendment. The design's foundation was valid throughout;
  it was just *behind* the bridge on enum handling. (Historical journal entries referencing the old contract-doc path
  are frozen and left as-is.)
- **TEST-5 DONE — text-processor / normalizer coverage; ALL TEST- tasks now closed.** The provider
  (`UnifiedTextProcessor`) was already covered (`test_text_processing.py`); added `test_text_normalizers_coverage.py`
  (11 tests) for the actual normalizers (`utils/text_normalizers.py`) + the component's live methods: **NumberNormalizer**
  (ru digit→words via the dependency-free path, no-number passthrough, empty), **PrepareNormalizer** (the pure-Cyrillic
  fast-return / Latin→Cyrillic transcription / inline number processing / changeLatin=skip branches), **RunormNormalizer**
  missing-dependency degradation (patched the `runorm` import to fail → returns input, never downloads the model), and
  `TextProcessorComponent.process` no-provider passthrough + `convert_numbers_to_words` (+ its error degradation).
  Reconciliation (Invariant #8): the review's "process() hardcodes the `general` stage / TTS gets no normalization"
  headline was remediated by **QUAL-13** — `process(..., stage="asr_output")` routes by stage now — so tests target the
  current code. `text_normalizers.py` **25%→58%**, `text_processor_component` 29%→30%, overall 53.1%→53.3%. No product
  bugs surfaced. Deliberately not chased: the review-confirmed dead stage routing, the broken text-processing WebAPI
  (QUAL-12 finding), and Runorm's model-download path (offline hazard). **With TEST-5 closed, every TEST- task (0–8) is
  done** — suite green at 930 passed (plain pytest), overall coverage 45.6%→53.3% across TEST-7 Phases + the TEST-3/4/5
  follow-ups.
- **TEST-4 DONE — parameter-extraction coverage (the P1 residual).** Covered TEST-4's named scope: **the 8
  ParameterTypes** via `HybridKeywordMatcherProvider._extract_by_type` — INTEGER/FLOAT/BOOLEAN/CHOICE(fuzzy
  surface→canonical)/DURATION/STRING branches plus the DATETIME/ENTITY fallthrough — and `_convert_and_validate_parameter`
  (the shared `coerce`) + `validate_config` (`test_param_extraction_coverage.py`); and **the 4 entity resolvers**
  Temporal (HH:MM / ru+en duration / relative) and Quantity (number + unit inference) as pure parsers, plus Device/Location
  **graceful-degradation** with no asset loader (`test_entity_resolver_coverage.py`). Reconciliation (Invariant #8): the
  `parameter_extraction_review.md` flagged a **P0 fatal-crash** in Device/Location `resolve()` when the asset loader is
  unwired — verified that QUAL-11 P0 #4 **already fixed it** (`_load_device_types` now returns `{}` with a warn-once), so
  the tests assert the degradation rather than a bug to surface. Coverage: `hybrid_keyword_matcher` **0%→19%**,
  `entity_resolver` **62%→79%**, `donations` 87%→89%; overall 52.6%→53.1%. 18 tests; no product bugs surfaced; suite
  green (918 passed under cov / 0 failed). The donation-driven `recognize()` pipeline (the bulk of hybrid's 675 stmts)
  and the dead-code-heavy `spacy_provider` (21%) are out of scope — integration-level / review-confirmed dead.
- **TEST-3 DONE — fire-and-forget lifecycle coverage.** The action store (`ClientRegistry`, 76%) + the happy
  launch→complete path were already covered by `test_action_store.py`; the gap was the `IntentHandler` F&F machinery
  (`handlers/base.py` 45%). Added `test_fire_and_forget_coverage.py` (11 hermetic tests — minimal concrete handler via
  `object.__new__`, a fresh `ClientRegistry` patched into `get_client_registry`, `asyncio.run`) covering the
  previously-untested branches: launch registers in the store; completion reaps + records success; **error** → failure
  history (`error`/`failed_actions`); **cancel** → recorded "cancelled"; **launch-failure** (store raises) → failed
  metadata with `failed_at_startup`; the positive-timeout monitor is registered then popped+cancelled on completion;
  `cleanup_timeout_tasks` cancels+clears; metrics `record_action_start`/`record_action_completion`; notification
  scheduled only when the action is session-owned; and the handler-level `cancel_action` (true/false) + `get_active_actions`.
  Reconciliation (Invariant #8): the `fire_and_forget_review.md` findings describe the PRE-remediation broken lifecycle —
  QUAL-9/QUAL-28 rebuilt it on the physical-identity-scoped store, so tests target the current working code, not the old
  bugs. `handlers/base.py` 45%→52%; overall 52.3%→52.6%; no product bugs surfaced. Suite green at **901 passed** (plain
  pytest). _Note: one pre-existing timing test (`test_zero_overhead_when_disabled`) is flaky under `--cov` (coverage
  instrumentation breaks its "zero overhead" assertion) — not a CI concern (the gate is plain pytest), flagged for a
  possible skip-under-coverage follow-up._
- **CI Tests gate red on a second real bug (PortAudio/OSError) — surfaced + fixed (user-approved).** With pyright
  green, the newly-enabled Tests gate ran and failed on the GitHub runner (Python 3.11.15) — 3 `test_voice_runner_coverage`
  tests raised `OSError: PortAudio library not found`. Root cause = a **real robustness bug in QUAL-46's voice_runner**:
  `check_voice_dependencies()` / `_check_dependencies()` catch only `ImportError`, but `import sounddevice` raises
  **`OSError`** when the package is installed without the PortAudio native lib (exactly a headless CI box / a server
  deployment) — so the dependency *probe crashes* instead of reporting "unavailable". Surfaced with options per the
  standing rule; user chose **fix the code** → broadened both probes to `except (ImportError, OSError)` (degrade, never
  crash). Also made the Phase-D tests **hermetic** (they had asserted the real environment had working sounddevice):
  added `_with_sounddevice()` (stub → present) and `_sounddevice_raises(exc)` (models the OSError), and added two tests
  asserting the graceful degradation — so the fix is locked in and the suite no longer depends on a system audio lib.
  Full suite 890 passed; pyright 0; no other test touches PortAudio.
- **CI red since ARCH-19 slice 5 — fixed (pyright); avoiding `cast` surfaced a real bug in my own tool.** CI had
  failed every run since `ARCH-19 slice 5` (the replay tool) — **5 pyright errors in `irene/tools/replay_trace.py`**
  (I'd checked import-linter + tests but never run pyright there). The Tests step never ran (gated behind pyright), so
  the green local suite was masked. Fixes: typed `self.core: Optional[AsyncVACore]` + `assert ... is not None` narrowing
  (real runtime checks, not band-aids); narrowed `TraceInput.listen() -> AsyncIterator[AudioData]` at the source (legal
  covariant override) instead of a call-site `cast`; and for the audio component used `isinstance(audio, AudioComponent)`
  narrowing instead of `cast(Any, audio)`. The user pushed back ("isn't cast a dirty trick?") — correct: `cast(Any)` is
  a typed `# type: ignore`, and here it was **hiding a genuine bug** — `_listen` passed an async generator to
  `AudioComponent.play_stream`, which takes raw **bytes** (it buffers→streams internally), so `--listen` would have
  silently failed (swallowed by its try/except). Fixed `_listen` to pass the decoded bytes, and updated the 2 Phase-D
  coverage tests that had pinned the buggy contract (fake `SimpleNamespace` audio + async-gen) to a real `AudioComponent`
  receiving bytes. Verified: pyright 0 errors, all other CI gates pass locally (no-TYPE_CHECKING / config profiles /
  config files / dependency resolution), full suite 888 passed, 9/9 import contracts. Audited `cast` across all product
  code (user request): **12 usages, 0 dirty** — all cast an under-typed *third-party* return (sounddevice/pyttsx
  `query_devices`/`getProperty`, the OpenAI SDK `ChatCompletionMessageParam`) to its known concrete shape, so the call
  stays checked; one `cast(object, …)`→`isinstance` is exemplary. **No `cast(Any, …)` anywhere** — the only one was
  mine, now gone. _Lesson: run pyright locally on new code (not just import-linter + tests); the honest line is
  `cast(ConcreteType, untyped_external_value)` ✅ vs `cast(Any, our_value)` ❌ — the latter is a typed `# type: ignore`
  that disables checking and conceals bugs (it hid this one)._
- **TEST-7 DONE + folded-in TEST tasks reconciled + full-suite pytest is now a CI gate.** Marked **TEST-7 `[x]`**
  (suite rewritten + 100% green, coverage 45.6→52.3%; the `workflow_manager`/`context` deep-pipeline residual accepted
  as integration/smoke-level, user-approved). Reconciled the tasks "folded into TEST-7" honestly against measured
  coverage — closed the genuinely-complete ones, kept the rest open with the specific residual: **DONE** → **TEST-2**
  (the paused suite-stabilization, subsumed — its `56→82 failed` drift is now `0`), **TEST-8** (all 5 capability
  handlers covered through their ports + graceful-degradation: text_enhancement 99% / speech_recognition 97% /
  translation 97% / audio_playback 80% / voice_synthesis 65% — the QUAL-24 repair is finally verified), **TEST-6**
  (ASR fallback + resampling restored — `test_phase7_performance` rewritten to `resample_audio_data`, `audio_processor`
  71%, `asr_component` fallback covered). **STILL OPEN (honest residual)** → **TEST-4** P1 (recognition cascade covered
  but the extraction internals are not — `hybrid_keyword_matcher` at **0%**, the 8 ParameterTypes / 4 resolvers
  unexercised), **TEST-3** (F&F *launch* covered, *lifecycle* completion/cleanup not), **TEST-5** (text-processor not
  targeted, 29%). **CI:** the full pytest suite was explicitly deferred in `backend-health.yml` ("becomes a hard gate
  once … TEST-7"); that precondition is met, so enabled it — `uv run python -m pytest irene/tests/` is now a hard gate
  alongside the existing import-linter / no-TYPE_CHECKING / pyright / config-validation / dependency gates. (Plain
  pytest needs no sqlite shim — that's only for `--cov`.) Suite verified green (888 passed / 0 failed); 9/9 contracts.
- **TEST-7 Phase D — coverage fill 45.6% → 52.3% (13-agent workflow; recovered from a mid-run crash).** Fanned out
  one agent per Tier-1 target — the cold spine (`workflow_manager`, `core/components`, `nlu_component`, `context`,
  `voice_assistant`, `asr_component`), the 5 capability-port handlers (TEST-8), and the new-code wiring
  (`replay_trace`, `voice_runner`) — each writing a new `test_<module>_coverage.py` of characterization tests at the
  seam, instructed to be hermetic (`asyncio.run`, no global-state pollution — the Phase-C lesson) and to SURFACE (never
  fix) any product bug. The main loop crashed before the workflow's verifier ran, so its result/findings were lost, but
  all 13 files were written to the tree. Recovered by hand: confirmed all 13 collect + are substantial + genuine
  (spot-checked `context` = eviction/dual-clock/room-injection, `workflow_manager` = trace helpers/event publishing,
  `nlu` = language detection — real behavior, not coverage-padding). The new tests EXPOSED one more latent
  `asyncio.get_event_loop().run_until_complete` anti-pattern (in the pre-existing `test_clarification.py` — passed
  alone, failed in-suite once an `asyncio.run` test closed the loop first); fixed it → `asyncio.run`, same class as the
  Phase-C `no_intent_clarification` fix. **Result: 888 passed / 0 failed / 7 skipped; overall coverage 52.3%
  (+6.7).** Standout gains on the new-code wiring (`voice_runner` 34→85%, `replay_trace` 34→82%) and spine
  (`core/components` 20→56%, `nlu_component` 38→59%, `voice_assistant` 48→72%, `asr_component` 25→46%); residual-cold
  are `workflow_manager` (29%) + `context` (31%) whose deep pipeline paths need a booted core (smoke territory).
  **No product bugs surfaced** (transcripts show no findings; no bug-skips in the files). 9/9 import contracts; no
  product code touched. _Lesson banked: the per-agent isolation check missed the order-dependency; the full-suite
  green run (and a workflow-level full-suite gate) is what catches it — and the crash cost us the verifier that would
  have._
- **TEST-7 Phase C — suite to 100% green (82 → 0 failed).** Ran a 19-agent workflow + verifier per the locked plan
  (delete stale / rewrite drifted to current contracts / SURFACE-never-fix product code). Deleted 4 stale pre-refactor
  files (phase4 ×3 + phase6, built on the removed `ContextualCommandPerformanceManager`) and rewrote 13 drifted
  clusters to current port/public contracts (NLU `_recognition_provider` cascade, `Intent` signature, VAD metrics
  dict-vs-object + `energy_threshold` relocation, spaCy MagicMock, the ARCH-19 `record_stage` trace contract, …);
  net −3,555 test lines; spot-checked two rewrites as genuine (assert real behavior incl. off-paths), not gamed.
  Fixed an order-dependent failure myself: `test_no_intent_clarification` used `asyncio.get_event_loop().run_until_complete`
  (passed alone, failed in-suite once another async test closed the loop) → `asyncio.run`. That left **3 reds = 2
  fix-code questions**, surfaced to the user with options per the standing rule (never fix product code autonomously);
  the user chose test/config fixes for both: (a) `device_id` is the live `MicrophoneInputConfig` field name (the
  planned `→device` alignment was never implemented) — removed it from the alignment test's deprecated list and cleaned
  the machine-specific `device_id = 7` to the `None` default in `config-master.toml` (Invariant #2); (b) `llm.console`
  is a *registered* offline-floor stub with no runtime params by design (entry-point at pyproject:262) — exempted
  declared stubs in `test_parameter_schema_unification` (mirroring the existing text-processor carve-out) and rewrote
  the stale `test_flags_phantom_llm_console` (console is no longer unregistered; switched to a genuinely-unregistered
  name so phantom-detection stays covered). **Suite now 558 passed / 0 failed / 7 skipped; 9/9 import contracts;
  config-master loads.** No product code changed in the whole phase. Next: Phase D (risk-ranked coverage fill).
- **TEST-7 Phase B — triage worklist + risk-ranked coverage (`docs/review/test7_triage.md`).** Captured one-line
  tracebacks for all 82 failures and clustered them by root-cause signature → verdicts: **~28 delete, ~50 rewrite,
  3 fix-code.** Deletes are the pre-refactor "phase" scaffolding (the 21-strong phase4 contextual cluster — all 16
  `'NoneType' has no attribute 'active_actions'` failures live there — built on the deleted `ContextualCommandPerformanceManager`;
  phase1/6 integration; the unbuilt-ARCH-8 device/location-resolution cases; a removed text-processor module). Rewrites
  are drift-to-current-contract (NLU `entities['provider']`→recognition-provider, `Intent(session_id=…)` signature,
  VAD metrics dict-vs-object + `energy_threshold` moved under `[vad.providers.energy]`, spaCy mock-vs-MagicMock,
  ARCH-19 trace-internal drift in `component_trace_integration`). Verdict-driving rule applied throughout: does the
  behavior still exist? Surfaced **3 fix-code suspects** (the TEST-1/2-style real-bug finds): `config-master.toml`
  hardcodes a machine-specific `device_id = 7` in the canonical reference (Invariant #2); the `llm.console` stub has an
  empty parameter schema; and a VAD-requirement error message that touches the QUAL-46 path. Also produced the
  risk-ranked coverage table (gap × churn × hot-path × defect-history): Tier-1 = `workflow_manager` (20%/15 commits),
  `core/components` (20%), `nlu_component` (38%/603 stmts/16 commits), `context` (25%), `voice_assistant` (48%/most-churned),
  `asr_component` (25%), and the 5 capability-port handlers (TEST-8, unverified after QUAL-24). This worklist is the
  input to the Phase C/D multi-agent workflow.
- **QUAL-47 (final sweep item) — retired the dead `test_vad_sibilant_fix.py` debug script + its orphaned config.**
  Verified-then-deleted: `tools/test_vad_sibilant_fix.py` was **already broken** — it imported
  `UniversalAudioProcessor` from `workflows.audio_processor`, a class renamed to `VoiceSegmenter` in the ARCH-18
  refactor, so the script raised `ImportError` on load and could not run. Not an entry point, not imported by any
  code or test; its only references were itself and one archive doc (`docs/archive/VAD_SIBILANT_FIX.md`, left as
  record). Removed it plus its sole companion **`configs/vad-sibilant-fix.toml`** (a one-off test config referenced
  by nothing else). No live references remain. The `tools/` dir now holds only active tooling
  (`generate_schemas.py`).
- **QUAL-48 — removed the v13→v14 runtime config-migration path (decision: remove).** The last v13/v14 relic after the
  QUAL-47 sweep. `irene/config/migration.py` (637 lines — `V13ToV14Migrator`, `migrate_config`,
  `ConfigurationCompatibilityChecker`, `create_migration_backup`) was *live* but guarded: `config/manager.py:_dict_to_config`
  called `ConfigurationCompatibilityChecker.requires_migration(data)` and only auto-migrated a **v13-format** config —
  impossible to hit on v15.0.0. Reconciled the full surface first (Invariant #8): only two importers (`config/__init__.py`
  re-exports + `manager.py`), no tests, no other code. Deleted the module; removed the import + the migration guard in
  `_dict_to_config` (the normal path — env-var resolve → `CoreConfig.model_validate` — is untouched); removed the import
  block + the 5 `__all__` entries from `config/__init__.py`. Net effect: a v13 config now fails at pydantic validation
  with a plain error rather than silently transforming — the right behaviour on v15, where v13 is unsupported. Verified:
  config-master/minimal/api-only all load clean, the `irene.config` re-exports still resolve, no lingering reference to
  any migration symbol, 9/9 import contracts, and the config/manager test suites are net-zero (7 pre-existing TEST-2
  failures, identical with the change stashed — nothing depended on auto-migration). Invariant #4 N/A. _Irene no longer
  carries any v13/v14 migration code or tooling._
- **QUAL-47 (extended) — swept for stale migrators, retired two more; surfaced one live-code finding (QUAL-48).**
  Broadened the verify-then-delete sweep across `tools/`, `irene/tools/`, `scripts/`. Retired two more standalone
  migrators (neither an entry point, neither imported by any code or test): **`tools/migrate_to_universal_plugins.py`**
  (migrates configs to the long-done "Universal Plugin + Provider" refactor — only references were two `docs/archive/*`
  guides, left as record) and **`scripts/migrate_donations_v11.py`** (the QUAL-29 donation v1.0→v1.1 migration — verified
  spent: QUAL-29 is `[x]` and the assets are already in the v1.1 layout, 13 `contract.json` + per-lang phrasing files).
  Both deleted; no code/config references remain; package imports clean. The sweep also surfaced
  **`irene/config/migration.py`** — v13→v14 migration utilities that are **NOT a tool**: they're live runtime code
  imported by `config/__init__.py` + `config/manager.py` and invoked in `_dict_to_config` (guarded by
  `ConfigurationCompatibilityChecker.requires_migration`, so it only fires for a v13-format config — never on v15). Per
  the verify-before-delete discipline (it's wired into config loading, I didn't author it), I did **not** touch it —
  filed it as **QUAL-48** `[deferred]` to decide keep-as-safety-net vs remove-as-code-change. Other tool files reviewed
  and kept (active): `generate_schemas.py`, `dump_openapi.py`, `check_scope.py`, `build_analyzer`, `config_validator_cli`,
  `dependency_validator`, `replay_trace`, `batch_cross_language_validation.py`. (`tools/test_vad_sibilant_fix.py` is a
  one-off VAD debug script — left for now, not a migrator.)
- **QUAL-47 — retired obsolete v13/v14 migration tools (QUAL-46 follow-up).** Verified-then-deleted, per the
  before-deleting discipline: confirmed the project is on **15.0.0**, both tools target long-past versions, and
  neither is imported by any runtime code or test. **`irene/tools/config_migrator.py`** (a v13→v14 config-file
  migrator) — removed the file and its `irene-config-migrate` `[project.scripts]` entry; not reused by
  `config_validator_cli` or anything else. **`tools/migrate_runners.py`** (legacy `runva_*.py` → v13 runner mapper)
  — removed; it was already **broken by QUAL-46** because it referenced `irene.runners.vosk_runner`/`VoskRunner`/
  `run_vosk`, which no longer exist. Only references anywhere were two `docs/archive/*` historical notes, left as
  record. Package re-syncs (entry points valid), the deleted modules import-fail as expected, no lingering code/config
  references, 9/9 import contracts. One sibling migrator remains (`tools/migrate_to_universal_plugins.py`, also
  pre-v15) — noted, not in scope.
- **QUAL-46 — vosk runner generalized into a config-driven voice runner.** Analysis (no-code, requested) found the
  `VoskRunner` was already a full end-to-end microphone pipeline (mic → VAD → [wake word, if configured] → ASR → text
  → NLU → intent → spoken reply, + deferred F&F speech), but **artificially coupled to vosk** by exactly two gates: an
  `import vosk` dependency probe (failed startup without the package) and a config-validation rule that errored unless
  `asr.default_provider == "vosk"`. The processing path itself never touched vosk — it delegates to the generic ASR
  component — so the coupling was vestigial. **Removed both gates:** the runner now declares only `sounddevice` as its
  hard dep (microphone capture) and validates *any* configured + enabled ASR provider; the chosen provider's own deps
  are the component system's job (`irene-dependency-validate`). **Renamed** throughout — `vosk_runner.py`→`voice_runner.py`
  (via `git mv`, history preserved), `VoskRunner`→`VoiceRunner`, `run_vosk`→`run_voice`, and the entry points
  `irene-vosk`→`irene-voice` (both the `[project.scripts]` and `[project.entry-points."irene.runners"]` registrations)
  plus the `runners/__init__` exports — a clean rename with no back-compat alias (pre-release). **Fixed a latent VAD
  inconsistency** spotted in the analysis: the streaming mic path *requires* VAD (the workflow raises if it's off), yet
  the runner force-enabled asr/audio/intent/text_processor/nlu but not vad — so a VAD-off config failed deep in workflow
  init with an opaque error. The runner now also forces `vad.enabled=True` (consistent with the other components);
  `voice_trigger` stays purely config-driven (the runner already auto-skips the wake word when it's absent). Docs: added
  a "Voice (microphone)" run-mode section to `QUICKSTART.md` (config-driven ASR, the `python -m` and installed-script
  forms, `--list-devices`/`--check-deps`/`--trace`) — this also closes the earlier doc-gap where the runner was
  undocumented. New `test_voice_runner.py` (8 tests: provider-agnostic validation across vosk/whisper/sherpa_onnx/
  google_cloud + the force-rules incl. VAD). 9/9 import contracts kept; runner/vad suites net-zero (4 pre-existing
  TEST-2 failures, verified by stash); no test imported the old module (only a same-named scenario function). Invariant
  #4 N/A. Left untouched: the v13-era `tools/migrate_runners.py` (maps the old runner name as a v13→v14 migration target;
  obsolete, flagged for retirement alongside `config_migrator`).

### 2026-06-14
- **ARCH-19 slice 6 — retire `vad_recording_test` + user docs; ARCH-19 COMPLETE.** Deleted
  `irene/tools/vad_recording_test.py` and its `irene-vad-recording-test` entry point (D-8/D-14). Its purpose was
  already ported in slices 2/3 — capturing a mic session at `capture_level=segmenter` records the `vad_frames`
  (per-frame voice/energy/threshold) + the base64 segment audio with VAD running at the canonical 16 kHz (the
  legacy tool's 44.1 kHz-VAD bug, fixed by construction), and `irene-replay-trace --local` tunes from it — so there
  is no second mic-capture path to maintain. Nothing in code or config still referenced the tool (only design/release
  docs, which describe the retirement). New **user guide `docs/guides/tracing.md`** (prose-style matched): recording a
  trace with `--trace`/`--trace-raw-mic`, the three capture levels and when to use each, the `[trace]` config, what a
  trace folds in (audio + logs + handler events), and the `irene-replay-trace` playback tool — `--local`/`--reproduce`
  (incl. the fail-clear-on-missing-model behaviour), `--listen`, `--step`, `--record-out` — plus a "tuning VAD with a
  trace" section that replaces the old recording workflow. Updated `docs/guides/vad.md` (Tuning now points to the
  trace-based, evidence-driven workflow) and the README guides index. **ARCH-19 is DONE — all six slices shipped**
  (spine → TraceLogger/config/flag → capture levels → handler events → replay tool → retire+docs); the task stays
  `[deferred]` (never in the release gate) but is now `[x]`. 9/9 import contracts; trace suite net-zero.
- **ARCH-19 slice 5 — the replay tool (`irene-replay-trace`), full scope incl. `--step` (user-approved).** Closed the
  loop: a saved trace can now be re-run through the real pipeline and diffed. **(a) Seed wiring** — the `record_seed_context`
  call-site deferred from slice 1 landed at the single spine `_process_pipeline` (alongside the "before" snapshot), so
  it covers batch text/audio AND per-utterance streaming, captured before the context is mutated (D-6). **(b) `TraceInput`**
  (`irene/inputs/trace_input.py`, `InputPort`, D-9) — "the mic, sourced from a trace": re-chunks the trace's assembled
  audio blob into AudioData frames so segmenter/raw replays re-enter the *streaming* pipeline (VAD→wake→ASR) without
  standing up the InputManager. **(c) The tool** (`irene/tools/replay_trace.py`): load → `build_core` → seed a fresh
  context from `seed_context` → re-inject at the capture level's entry (utterance→`process_audio_input`,
  segmenter/raw→`TraceInput`→`process_audio_stream`, text→`process_text_input`) → **diff the fresh IntentResult vs
  `recorded_output`** (text/success/actions) with a printed report + exit code. Modes (D-10): **`--local`** (default —
  run through the replayer's own config; the VAD-tuning case) and **`--reproduce`** (overlay the captured `config_subset`;
  **fail clearly, naming the model + pointing to `--local`, when a named provider isn't in the replayer's config** — D-16).
  Extras: **`--listen`** (D-11 — play the captured audio via the audio component, best-effort/degrades), **`--step`**
  (D-12 — a new `trace_step()` async pause seam awaited at the `_process_pipeline` stage boundaries text_processing/nlu/
  intent; the hook is set per-trace for the utterance/text path and via a module global so streaming-minted traces inherit
  it; no-op + zero cost otherwise), **`--record-out`** (D-13 — reuses the save-every-request machinery by enabling tracing
  into a chosen dir, so a tester's trace + the local replay become two comparable files). Registered `irene-replay-trace`
  in `pyproject [project.scripts]`. The `replay`/`--reproduce`-endpoint is deliberately NOT built (D-15: CLI-only v1).
  New `test_trace_replay.py` (15 tests: pure diff/config-subset/model-mismatch/seed helpers + the `TraceInput` chunker +
  the `--step` seam + a `TraceReplayer.load` round-trip); the full e2e run needs real models (`build_core`), so it's
  manual/integration, not unit-covered. 9/9 import contracts kept (TraceInput in `inputs`, tool in `tools`, no new edge);
  pipeline suites net-zero (24 pre-existing TEST-2 failures, verified by stash). Invariant #4 N/A. ARCH-19 stays `[ ]`
  (5 of 6 slices — only the `vad_recording_test` deletion + user/dev docs remain).
- **ARCH-19 slice 4 — handler `trace_event()` call-sites (D-5).** Wired the opt-in `trace_event()` helper (from
  slice 1; reads the `current_trace` contextvar, bound around handler execution in both the batch and streaming
  paths) by a consistent rule rather than ad-hoc per handler. **(1) Every fire-and-forget launch is traced once,
  generically, at the base choke point** — `IntentHandler.execute_fire_and_forget_with_context` now emits
  `action_launched {domain, action}`, so **timer, voice_synthesis, audio_playback and any future F&F handler** are
  covered without per-site edits. **(2) Synchronous side-effects get explicit events:** timer `_handle_set_timer`/
  `_handle_cancel_timer`/`_handle_stop_timer` (`timer_set` carries the duration the generic event can't / `timer_cancel`
  / `timer_stop`), the **7 LLM call-sites** — `conversation.py` (`generate_response` ×2), `text_enhancement_handler.py`
  (`enhance_text` ×3), `translation_handler.py` (`enhance_text` ×2) — and the provider/ASR/language switches
  (`provider_control._switch_component_provider`, `speech_recognition._handle_switch_asr_provider`,
  `system._handle_language_switch`). **Deliberately NOT instrumented:** the pure-compute handlers (datetime, greetings,
  random) and read-only `system_service` queries — their only "step" is the response text, already in `recorded_output`;
  events there would be noise. Launch events sit in the synchronous request path, NOT inside the detached F&F tasks
  (the contextvar there is a stale creation-time snapshot of an already-saved trace — the timer-fire lesson). Purely
  additive — the domain→core import edge already existed (`handlers/base.py` imports `core.trace_context`), so all 9
  import contracts hold. **Device-command MQTT events deferred (Invariant #8):** no real send/publish call-site exists
  yet — device handlers are stubs/port delegations pending the bridge/MQTT layer (ARCH-7/8). _(This corrects an initial
  under-scope that stopped at §6's three named examples; broadened to every handler with a genuine key step.)_ New
  `test_trace_handler_events.py` (6 tests: behavioral timer-cancel + base `action_launched` + a call-site-presence
  regression guard across 8 modules); handler suites net-zero (21 pre-existing TEST-2 failures, verified by stash).
  Invariant #4 N/A. ARCH-19 stays `[ ]` (4 of 6 slices).
- **ARCH-19 slice 3 — capture levels (utterance / segmenter+vad_frames / raw) + the streaming path.** Brought the
  live-mic/ESP32 `process_audio_stream` path under tracing, with a user-approved scope decision (Invariant #8 — the
  design left the streaming trace lifecycle underspecified): **one trace per utterance** (per `VoiceSegment`), and
  **all three capture levels incl. the raw live-mic rolling buffer** in this commit. Mechanics: `VoiceSegment` gains a
  `vad_frames` field; `VoiceSegmenter` retains per-frame VAD verdicts (is_voice/energy/threshold + absolute ts) when
  built with `collect_vad_frames=True` — gated at startup by `--trace` + `capture_level ∈ {segmenter,raw}` so production
  pays nothing — and `_collect_segment_vad_frames` slices them to each segment's window (re-based to t_ms, pruned).
  The workflow derives the gate from `[trace]` config at init, threads `collect_vad_frames` through
  `AudioProcessorInterface`, and for raw level buffers **pre-canonical native-rate frames** in `_canonical_stream`
  into a duration-bounded rolling buffer (`_buffer_raw_frame`), reconstructing a segment's original-rate audio on
  completion (`_raw_audio_for_segment`, falls back to the canonical segment when no raw frames cover it). Per utterance,
  `_process_audio_pipeline` now mints a trace, `_capture_segment_input` records the right audio for the level + the
  canonical contract + the vad_frames, binds it via `trace_scope` around `_process_pipeline` (so NLU/intent/TraceLogger
  attach), records the oracle output, and saves. The legacy `vad_recording_test` "VAD on raw 44.1 kHz" bug is **inherently
  fixed** — capture runs inside the real canonical pipeline, so VAD sees 16 kHz (§10/§3). De-dup: the create/save
  helpers (`make_trace`/`save_trace`/`resolve_traces_dir`/`replay_request`) were lifted into `core.trace_context`
  (configs duck-typed → no new edge) and `WorkflowManager`'s slice-2 methods now delegate to them. `--trace-raw-mic`
  made self-contained (also selects `capture_level=raw`). New `test_trace_capture_levels.py` (12 tests, green); 9/9
  import contracts kept; the VAD/audio suites are net-zero (15 pre-existing TEST-2 failures, verified by stash).
  Invariant #4 N/A (no config-schema/endpoint change). ARCH-19 stays `[ ]` (3 of 6 slices).
- **ARCH-19 slice 2 — TraceLogger + `[trace]` config + `--trace` flag + save-every-request.** Made `--trace`
  actually produce trace files. New **`TraceLogger`** (`core/trace_context.py`): a global `logging.Handler` installed
  once at runner startup (`base.py._install_trace_logger`, after config build), **inert unless `current_trace` is set
  + enabled**, capturing records ≥ `log_threshold` **plus full exception tracebacks**, stage-tagged via the trace's
  `current_stage`, bounded by `max_log_records` — never raises out of `emit`. New **`[trace]` `CoreConfig` section**
  (`TraceConfig`: `enabled`/`capture_level`/`capture_raw_mic`/`log_threshold`/`traces_dir` + safety caps) +
  `AssetConfig.traces_root` (`<assets_root>/traces` default) + an auto-registry order/title (`🧪 Trace Persistence`).
  **`--trace` / `--trace-raw-mic`** runner flags flip `enabled`/`capture_raw_mic` before startup (D-7). **Save-every-
  request** (D-17) wired into both `WorkflowManager` batch boundaries: `_maybe_create_trace` mints a trace when startup
  tracing is on and none was passed, and after the turn `_save_trace_if_enabled` writes the §2 envelope to
  `<traces_dir>/<request_id>.json` (also on the audio error path); the save gate is **solely** the startup flag, so an
  explicit `/trace` endpoint call on a non-tracing instance still doesn't spam disk. `config-master.toml` gains a
  documented `[trace]` block (Invariant #2). **Invariant #4: config-ui builds with ZERO changes** — its config UI is
  schema-driven (`Object.keys(config)` + the auto-registry order endpoint, generic `ConfigSection`), so the new section
  surfaces automatically; verified `npm run check` + `npm run build` green. Slice boundary: the live-mic/`process_audio_
  stream` path is deliberately NOT traced yet — its capture is slice 3 (capture levels + rolling buffer). New
  `test_trace_logger_and_save.py` (16 tests, green); 9/9 import contracts kept; the 7 pre-existing failures
  (3 component-trace + 4 config-validation) are TEST-2 baseline drift, verified net-zero by stash. ARCH-19 stays `[ ]`
  (2 of 6 slices).
- **ARCH-19 slice 1 (spine) — the faithful `replay` envelope + ambient access.** Built the data spine the rest of
  ARCH-19 hangs off, all in `core` (no new architecture edge — `core` is already imported by the domain; 9/9 import
  contracts kept, no `TYPE_CHECKING`). In `core/trace_context.py`: the `current_trace` **contextvar** + a
  `trace_scope()` set/reset CM + a no-op-safe **`trace_event()`** (D-3/D-5); and the **un-sanitised `replay`
  envelope** on `TraceContext` — `record_input` (FULL audio base64 inline, *not* the 1 MB sanitiser cap),
  `record_request`, `record_canonical`, `record_seed_context` (JSON-safe faithful snapshot via `asdict`+coerce),
  `record_config` (subset + `sha256:` digest, D-10), `record_output` (the diff oracle, D-6), plus `handler_events`/
  `logs`/`vad_frames` holders — serialised by `build_envelope`/`to_file` into the §2 self-contained JSON. The
  existing `stages`/`context_snapshots` stay the SANITISED human view (`export_trace`); the envelope is the faithful
  re-runnable twin. Wired the contextvar bind + input/request/output capture at the two `WorkflowManager` request
  boundaries (`process_text_input`/`process_audio_input`); `trace_scope` is no-op-safe so the wrap is unconditional.
  Reconciliation (Invariant #8): slice valid-as-written — all target names confirmed net-new; the orchestrator's
  `_current_trace_context` stash left intact (its handler-migration is slice 4). The `record_config`/`record_seed_context`/
  `vad_frames`/`logs` **recorders** land + are unit-tested now; their **call-sites** belong to later slices (config→2,
  seed→5, vad→3, logs→2). New `irene/tests/test_trace_envelope.py` (15 tests, all green); existing 3 component-trace
  failures are pre-existing TEST-2 baseline drift (verified net-zero by stash). Invariant #4 N/A (no contract change —
  `/trace*` response shape untouched). ARCH-19 stays `[ ]` (1 of 6 slices).
- **ARCH-19 — design session closed; §13 open questions all resolved (D-15..D-18).** Decided the four remaining
  trace-persistence design edges with the user, lifting the doc from DRAFT to design-COMPLETE: **D-15** replay surface
  = **CLI only for v1** (a `/trace/replay` endpoint is deferred, not dropped — the rich UX is terminal-native and the
  source-agnostic entry points let it be added later with no rework, avoiding a premature Invariant #4 obligation);
  **D-16** `--reproduce` against a **missing model fails clearly** (names the model, points to `--local`) — no
  degrade-and-run, since that *is* `--local`, keeping the two modes semantically clean; **D-17** **save policy =
  save-all gated solely on the startup tracing flag** (the ring-buffer / on-error variants were considered and
  declined — a trace run is a deliberate bounded debugging act; retention stays manual, no `save_policy` knob);
  **D-18** a saved trace stays **file-only** (the inline-base64 envelope is too heavy for the observation bus) — once
  ARCH-15's bus exists, emit only a lightweight `trace_saved` pointer-event (id + path + summary), never the payload.
  Updated `trace_persistence.md` (§8 reservation, §11 D-15..D-18, §13 marked all-resolved, status line) and the ledger
  (ARCH-19 entry + review-index row). ARCH-19 stays `[ ]` / `[deferred]` — design is done, implementation (§12 slices)
  is the next step when the task is picked up.
- **ARCH-22 Phase 5 — ledger closure; ARCH-22 DONE.** Closed **QUAL-45** (ESP32 audio-streaming protocol — *design*
  subsumed by ARCH-22 / `esp32_satellite.md`; firmware impl rides the rewrite). Amended every ARCH-22-touched task with
  explicit `esp32_satellite.md` pointers: **ARCH-6** (transport consolidated; reply channel + register extension realized),
  **ARCH-9** (§10/§11 split folded → D-9/D-10/D-11), **ARCH-10** (owns the deferred streaming-endpoint #3 / D-6), **ARCH-21**
  (reply-channel device-half landed), **QUAL-19/QUAL-20** (device-side micro stack D-9/D-10), **QUAL-35** (the multi-room
  resolution SPEC D-15 + the carried `primary_room`/`covered_rooms`), **ARCH-8** (the T-B voice-confirmation feature rides
  it). Filed **ARCH-23** (ESP32 firmware rewrite, `[deferred]`) so the standalone C++ effort is tracked, not an orphan
  finding. **ARCH-22 marked DONE** — its deliverables (implementation review + consolidated design doc + Plane-A backend +
  Plane-B `nginx/` + closure) are complete; the firmware rewrite is ARCH-23 and the streaming-endpoint is ARCH-10.
- **ARCH-22 Plane A / Plane B split + Plane B implemented (`nginx/`).** WB7 SSH recon (root@192.168.110.250) found a
  tiny armv7 controller (~1 GB RAM / 2 GB disk, nginx 1.18 w/ ssl+auth_request+dav, only `:80`, **no Irene container**
  — bridge/ui both stopped 10mo). Concluded (user-driven, pushed back where warranted) that the remaining Phase-4
  pieces (#4 asset serving, #5 CSR/CA, #6 ops) are **not Irene** — they're a **fleet-provisioning plane (Plane B)**
  that belongs as **nginx + openssl + scripts directly on the WB7**, not a container. **Plane A (Irene voice
  pipeline) is complete for ESP32** (#1 reply channel, #2 register; #3 → ARCH-10). Implemented Plane B in the repo at
  **`nginx/`**: an **Ansible playbook** (`nginx/ansible/deploy.yml`, idempotent) deploying an **EC `prime256v1` home
  CA**, a **two-zone nginx site** (`:80` bootstrap = public CA cert + CSR `PUT` + signed-cert `GET`, human approval is
  the gate; `:443` mTLS = firmware/model static serving, `ssl_verify_client on`), and an **`esp32-provision`
  {list,approve,revoke} CLI** (dedicated/SSH approval — amends D-17 away from config-ui; config-ui can call the same
  scripts later). The CSR-approval flow was **proven end-to-end with openssl** (sign → verify-against-CA → clientAuth
  EKU → idempotent re-init). Amends D-13 (per-node models = Plane-B nginx static, operator-managed, not Irene's
  AssetManager). `bash -n` + ansible `--syntax-check` + YAML all clean.
- **ARCH-22 Phase 4 (backend) batch 1 — reply channel + register extension; streaming-endpoint deferred.**
  **#1 (`d8b1c70`)** the ESP32 **reply channel**: `outputs/remote_audio.CallbackReplyChannel` (transport-agnostic
  `speak_begin`→PCM→`speak_end` framing) + a `/ws/audio/reply` WS endpoint pairing a `RemoteAudioOutput`
  (`origin_key==client_id`) on the `OutputManager`; `/ws/audio` now routes the SPOKEN reply via
  `OutputManager.deliver(SPEECH)` (wants_audio=False, no local playback) — completing the ARCH-21 device-half.
  **#2 (`fa56978`)** the `register` extension (D-14): `name`/`covered_rooms`/`audio_out`/`firmware_version`/
  `model_version` on `ClientRegistration`, `primary_room` alias of `room_name`, `covered_rooms` threaded into
  `/ws/audio` `client_context` (carry-ready for the room resolver). **#3 streaming-endpointing (D-6) deferred to
  ARCH-10** (Invariant #8): `process_audio_stream` is the VAD-segmented mic path (wrong for the no-server-VAD ESP32
  path); the real target is a **new no-VAD streaming path** feeding the ASR's `transcribe_stream` + endpoint, which
  is deployment-gated (streaming ASR + WB7) and testable only with ARCH-10. The accumulate-until-`end` + batch-ASR
  fallback is the **permanent floor and active** — `/ws/audio` correctly implements the wire contract, and deferring
  #3 leaves the wire/firmware design unchanged. ARCH-10 tagged as owner. #4 (asset endpoints) + #5 (CSR flow) queued.
  pyright 0; net-0 regression (81 = baseline; +4 tests across #1/#2).
- **ARCH-22 Phase 2+3 — consolidated ESP32 design doc written.** Interactive design session locked **D-1..D-18**
  across T1–T7: device shape (headless satellite, ESP-IDF+PlatformIO, MQTT-unaware); wire protocol (two WS —
  `/ws/audio` in + `/ws/audio/reply` out; raw PCM; extended `register`; device end-hint + server-authoritative ASR
  endpointing; single mic v1); audio I/O (digital I2S mic + MAX98357A, half-duplex; capture 16k / playback 22.05k;
  ES8311+barge-in = v2); micro stack (ported microWakeWord on ESP-IDF with the TFLite-Micro micro-features frontend
  + µVAD — NOT the draft's MFCC; manifest = shared device+server artifact); models (flash data-partition,
  runtime-loaded; push via HTTPS-from-WB7 / dev admin UI); identity (client_id + name + primary_room +
  covered_rooms; multi-room resolution policy D-15 → ARCH-7/QUAL-35); provisioning (two-stage SoftAP→STA per the
  mitsubishi2wb pattern; CSR-approval via config-ui, no token; OTA A/B config-preserving; admin-UI auth deferred to
  v2). Deliverable `docs/design/esp32_satellite.md` (supersedes `ws_esp32_transport.md`, folds
  `esp32_wakeword_review.md` + `onnx §10/11` + ARCH-21). Backend plan in §12; closes QUAL-45 + ARCH-21 device-half +
  ESP32 pieces of ARCH-6/9/10 on completion. Phase 4 (backend impl) next.
- **ARCH-22 filed — full ESP32 review + consolidated design session (started).** Umbrella for (a) implementation
  review, (b) consolidating scattered ledger ESP32 topics, (c) the user's not-in-ledger inputs → one consolidated
  design doc + backend implementation + ESP32 design-task closure. **Phase 1 (review) done:** the quarantined
  `ESP32/firmware/` draft is a genuine on-device acquisition + microWakeWord(INT8 TFLite-Micro) + microVAD + mTLS-WS
  pipeline, but its protocol predates the backend contract (`/stt`, `{"config":…}`, `{"eof":1}`, ignores replies, no
  audio-out) and its UI/output/codec are stubs. Locked D-1 (backend authoritative, firmware=inspiration), D-2
  (headless voice satellite: board+mic+speaker, 3D case, no display/UI, memory bump-able), D-3 (ESP-IDF + PlatformIO,
  not Arduino), D-4 (device is a pure MQTT-unaware voice terminal; smart-home/MQTT stays backend). Topics T1–T7 mapped
  to ledger items (ARCH-6 / QUAL-45 / ARCH-21 / QUAL-19-20 / ARCH-9-10 / QUAL-28 / ARCH-7-8). Phase 2 (interactive
  design) starting at T1 (WS transport + wire protocol). Session codes BACKEND only; the firmware rewrite is a
  separate deferred item.
- **ARCH-21 PR-5 — reply-to-device server seam (ARCH-21 COMPLETE).** Added `outputs/remote_audio.py`:
  `RemoteAudioOutput(OutputPort)` + a `ReplyChannel` Protocol. Reply-to-device (D-4) needs no new registry — an
  output with `origin_key() == physical_id` is already routed by the `OutputManager` conversational
  origin-pairing (`_origin_output`), so one `RemoteAudioOutput` per connected device is the whole model. `deliver`
  runs the ARCH-21 producer (`synthesize_to_stream`) → conforms DOWN to the **device's** declared `AudioContract`
  (`to_sink(producer, device_contract)`) → pushes raw PCM over the channel; an offline channel drops. Built
  protocol-agnostic (the WS wire format isn't committed — `ReplyChannel` is the only coupling) and tested with a
  fake channel + a real `OutputManager` proving origin routing (a result from device A reaches A's channel, not
  B's). **Handoff:** the device-facing reply-channel WS endpoint, connect/disconnect registration, frame protocol,
  and F&F-offline policy are owned by the ESP32 design session (`ws_esp32_transport.md` / QUAL-45). pyright 0;
  net-0 regression (81 = baseline, +3 tests). ARCH-21 is complete (PR-1..5).
- **ARCH-21 PR-4 + scope reconciliation (Invariant #8, user-approved).** Investigating PR-4 ("move the WS TTS
  delivery into a remote-sink OutputPort") found it infeasible as written: `ClientRegistry` holds only metadata
  (no live `WebSocket`), and `/ws/audio` replies text-only — so `OutputManager` has nothing to push audio to;
  building that push infra is ESP32-transport scope. Also, `/tts/stream`+`/tts/binary` are untested
  request/response synthesis endpoints (twins of the ASR `/stream`+`/binary` already deleted as ZERO-value).
  User set the routing philosophy (**D-4 reply-to-device**): output is origin-addressed — a WS device's reply
  goes back to that *device* over a *separate reply-channel WS* it listens on (not the same connection), the
  device's contract drives the conform, local input → local output, clean per-deployment config. **Redefined
  (approved):** PR-4 = delete the vestigial endpoints; PR-5 = the reply-to-device server seam (device protocol
  deferred to the ESP32 design session). PR-4 deleted `/tts/stream`+`/tts/binary` (~540 lines) + the orphaned
  WS-response schema cluster in `api/schemas.py` (~568 lines) + dead imports + the now-empty `get_websocket_spec`
  override. pyright 0; config-ui green; net-0 regression (81 = baseline).
- **ARCH-21 filed — streaming TTS + output-seam delivery unification (design DRAFT).** Follow-on analysis to
  ARCH-20 (its producer twin). Established that the TTS producer is file-only **at the contract level** (only
  `synthesize_to_file`), though implementations split — silero_v4 (PCM samples) and elevenlabs (MP3 bytes) already
  hold audio in memory; pyttsx/vosk are genuinely file-native. Found delivery fragmented across **three** surfaces
  (`_handle_tts_output` sync reply, `AudioSpeechOutput.deliver` ARCH-15 OutputPort for deferred F&F, WS
  `/tts/stream`+`/tts/binary`), and that **ARCH-20 PR-4 only updated the first** — `AudioSpeechOutput` still does
  file-only `play_file`. Concluded: PR-4's `parse_wav→to_sink→play_stream` is a correct **interim bridge** (real
  conform + streaming backend, but no latency win) that the streaming-synth port retires. Locked D-1 (delivery →
  output seam, not TTS-component endpoint and not an audio provider — a WS client is a dynamic per-connection
  remote `AudioSink`, not a config-selected device backend), D-2 (keep all providers; base simulation + native
  overrides; dropping non-streaming engines would gut offline-first RU TTS), D-3 (`synthesize_to_file` stays;
  port grows `synthesize_to_stream`). Deliverable `docs/design/streaming_tts.md`; sliced PR-1..4 in §5.
- **ARCH-20 implemented — streamable audio output (PR-1..4).** Turned the file-only playback path into real
  streaming and trimmed the provider set to streamable-only.
  - **PR-1** removed `audioplayer` (file-only) and `simpleaudio` (archived, WAV-buffer-only) end-to-end —
    provider files, entry-points, schemas, `auto_registry`, config-master blocks, `build_analyzer`/
    `config_validator_cli`, the `audio_component`/`audio_helpers` probe lists, the demo, and three tests
    (re-pointed to `aplay`). Bumped `sounddevice→0.5.0` / `soundfile→0.13.0` (input + output extras) and added
    `miniaudio>=1.59` to the `audio-output` extra.
  - **PR-2** replaced the stubs (collect→temp WAV→`play_file`) with a **PCM-only `play_stream` contract**
    carrying `(sample_rate, channels, sample_width)`. New `irene/utils/audio_stream.py` (foundation, no upward
    deps): `collect_pcm` (buffer-then-stream bridge), `parse_wav`/`is_wav`, `iter_frames`,
    `width_to_alsa_format`. `sounddevice` now plays via `RawOutputStream` (blocking write on a worker thread,
    no soundfile/WAV); `aplay` pipes raw PCM to `aplay -t raw -f S16_LE …` over stdin (genuinely incremental).
    REST `POST /audio/stream` parses a posted WAV down to PCM (raw fallback) with its **external param contract
    unchanged**, so no config-ui/OpenAPI regen was needed.
  - **PR-3** added the `miniaudio` provider — pyminiaudio bundles its own WASAPI/CoreAudio/ALSA backends, so
    `get_platform_dependencies()` is empty on every OS; real streaming via `PlaybackDevice` + a pull-based PCM
    generator on a worker thread; `play_file` decodes wav/flac/mp3/ogg to PCM through the same path. Verified
    against pyminiaudio 1.71. Gives ≥2 streamable backends on every OS (sounddevice + miniaudio; +aplay Linux).
  - **PR-4** added `[audio] playback_mode = "file" | "stream"` (default `file`). `stream` does
    synthesize→`parse_wav`→`AudioNegotiator.to_sink` (the §8 conform-down)→`play_stream`, and degrades to
    `play_file` for text-only providers (e.g. `console`) or when the negotiator isn't wired. Rewrote
    `docs/guides/audio.md` (four-provider table, streaming, `playback_mode`).
  - **Reconciliation (Invariant #8):** all TTS providers are file-only at the provider level (even the existing
    HTTP "streaming" sites synthesize to a temp WAV and read it back), so `stream` mode reads back the synthesis
    WAV rather than a file-free synth path — a future per-provider enhancement. The ledger scope ("wire local
    **playback** through `play_stream`") is fully met.
  - **`console` kept** (user decision 2026-06-14) as the safe headless default + fallback; the originally
    scoped "retire console" step was dropped.
  - Throughout: pyright 0 on all touched files; config-ui `npm run check` + `build` green each PR (Invariant
    #4); net-0 test regression (81 failed = baseline; +11 new tests in `test_audio_stream.py`).

### 2026-06-13
- **ARCH-20 filed — streamable audio output (research + task).** Following up the file-only-output limitation
  ARCH-18/PR-4c deferred (intentionally, never task-tracked): checked all five audio providers — **every `play_stream`
  is a stub** (buffer the whole stream → temp WAV → `play_file`), so file-only is unimplemented code, not a library
  wall. Web research on streaming support + versions: **sounddevice** streams for real via `RawOutputStream` (plain PCM
  buffers, cross-OS, PortAudio); **aplay** streams via stdin pipe (Linux); **audioplayer** is file-only and
  **simpleaudio** is archived/unmaintained + buffer-only. Per the user's "no unstreamable outputs", researched a
  cross-platform second backend and landed on **`miniaudio` (pyminiaudio)** — self-contained (no system lib, bundled
  WASAPI/CoreAudio/ALSA), cross-OS incl. Raspberry Pi, MIT, maintained (v1.71 Apr 2026), `PlaybackDevice`+generator
  streaming — giving ≥2 streamable backends on *every* OS on *different* stacks (sounddevice + miniaudio; +aplay on
  Linux). Filed **ARCH-20** `[deferred]`: implement real `play_stream` (sounddevice/aplay/miniaudio), drop
  audioplayer+simpleaudio, bump sounddevice/soundfile, wire TTS local playback through `play_stream`
  (completes `audio_pipeline.md` §8). The async→sync generator bridge is the one implementation caveat.
- **ARCH-19 filed — Trace persistence + playback (design DRAFT).** Design session: persist an utterance-execution
  trace to a **self-contained JSON** (audio **base64 inline, no WAV**) so it can be listened to AND replayed through
  the pipeline (regression + VAD tuning), as an opt-in save+replay layer over today's ephemeral `TraceContext`.
  Grounded the analysis in the live code: traces are ephemeral (per-request, GC'd; opt-in `/trace*` only; per-trace
  caps; no store), `_sanitize_for_trace` redacts/truncates/1 MB-caps (right for display, lossy for replay), and the
  orchestrator already half-stashes the trace for handlers. Locked D-1..D-8 (3 capture levels incl. per-frame
  `vad_frames` + a live-mic-raw flag; a hexagon-clean `current_trace` contextvar in `core` as the spine for a
  `TraceLogger` + handler `trace_event`; seed-context + diff replay; runner `--trace`→`[trace]` TOML). Found
  `irene/tools/vad_recording_test.py` reusable (mic→VAD harness) → **retire-and-replace** (base64 not WAV, fix the
  `to_canonical` ordering it predates). Deliverable `docs/design/trace_persistence.md` (§12 slices, §13 open
  questions); ledger ARCH-19 `[deferred]`. Design session continues.

### 2026-06-10
- **ARCH-18 PR-6 — user-facing docs + diagrams (FINAL); ARCH-18 COMPLETE.** Rewrote `docs/guides/vad.md` for the
  provider family + `[vad.providers.*]` nested config (component knobs vs per-engine tables, microvad
  `detection_latency_ms`, the auto-sized pre-roll, the updated startup log); updated `audio.md` (canonical input
  transform-once + the new output **sink**: provider/`[audio]` override, CD default, conform-down, PCM-only) and one
  line each in `voice-trigger.md` + `howto-new-model.md`. Added a **"The audio front-end"** section to
  `docs/architecture/dataflow.md` and a **new Graphviz diagram** `docs/images/audio-pipeline.dot` → `.png` (rendered
  with `dot`; mic / ESP32 satellite / `/asr/transcribe` → `AudioNegotiator` → VoiceSegmenter → wake → ASR, with the
  pre-segmented bypass and TTS → sink). A stale-term sweep across guides + architecture came back clean. With this,
  **ARCH-18 is COMPLETE** — PR-1 (AudioTranscoder rename), PR-2 (VAD provider family + VoiceSegmenter), PR-3
  (AudioContract + AudioNegotiator), PR-4a/4b/4c (TTS dedup, input conformance, symmetric output), PR-5 (pre-roll),
  the input-path endpoint unification, and PR-6 docs — all landed.
- **ARCH-18 PR-4c — symmetric output DONE.** `AudioNegotiator.to_sink` (output mirror of `to_canonical`) conforms a
  producer **down-only** to a sink's capability (pass through when `≤` the sink, downsample/downmix only when it
  exceeds it, never upsample; traced `audio_output_conform`). Sink contract = active audio provider's
  `audio_contract()` (base reads `sample_rate`/`channels`, CD default; sounddevice already CD) + optional `[audio]`
  `output_rate`/`output_channels` override, resolved on the shared core negotiator at startup. TTS retired
  `_conform_output_audio`→`_conform_to_sink` at all 3 streaming sites (`/speak`, `/tts/stream`, `/tts/binary`): the
  **streaming caller is the sink** (its requested rate/channels, CD default); since conform is down-only the response
  now carries the **actual** rate (engine-native or downsampled), read back from the result for the metadata/chunk
  calcs. PCM-only; **local file playback left untouched** (intentionally file-based — streaming-to-device was a prior
  dead end). 5 tests; pyright 0, lint 9/9, config-ui green, suite 81=81. _(Scope: the streaming caller is the sink for
  now; a generic remote/streaming `AudioSink` is future-addable on this seam.)_ ARCH-18 PR-1..5 + 4a/4b/4c all done;
  only **PR-6** (user docs + diagrams) remains.
- **ARCH-18 PR-4c — symmetric-output DESIGN session (locked; impl pending).** Captured the user's spine: the output
  contract is the **sink's audio capability**, default **CD (44.1k/pcm16/stereo)** when nothing's in TOML (the
  producer's hint), **conform-down-only** (any device plays lower → pass-through `≤` sink, downsample/downmix only
  when the producer exceeds it, never upsample), **PCM only** (MP3/FLAC → distant future). Locked D-8..D-13: sink
  contract = active audio provider's `audio_contract()` + optional `[audio]` `output_rate`/`output_channels` override;
  `AudioNegotiator.to_sink` (the output mirror of `to_canonical`, same `AudioTranscoder`, traced); TTS retires
  `_conform_output_audio`→`to_sink`; scope = **local playback now** but a generic `AudioSink` so remote/streaming
  sinks (ESP32/web declaring their own contract) are future-addable. Written into `audio_pipeline.md` §8 + §13.4c.
- **ARCH-18 — input-path unification COMPLETE (shared negotiator + endpoints reconciled).** Hoisted
  `AudioNegotiator` `workflows`→`core` (layering: core can't import workflows); the engine builds ONE negotiator at
  startup (config + active wake/asr providers; VAD fixed 16 kHz) and injects it into the workflow, so the mic/web
  boundary and `/asr/transcribe` share the **same `to_canonical`** (bespoke `_conform_to_rate` deleted). Deleted both
  ASR-utility WS endpoints (`/asr/stream`, `/asr/binary`). **Correction to the earlier reconciliation:** I'd claimed
  `/ws/audio` ran server VAD — it does **not**. The single-audio path (`_process_single_audio_pipeline`) runs
  wake→ASR directly with **no VAD segmenter** (the segmenter is only in the *streaming* mic path), so `/ws/audio`
  already does exactly the ESP32 model — accumulate-to-`{"type":"end"}` → `to_canonical` → wake-skipped → one ASR.
  **No `/ws/audio` change was needed.** So the endpoints now: mic = stream→VAD→wake→ASR; `/ws/audio` = device-segmented
  utterance→to_canonical→ASR (no VAD/wake); `/asr/transcribe` = file→to_canonical→ASR. pyright 0, lint 9/9, suite 81=81.
- **ARCH-18 PR-4 input-path reconciliation + `/asr/stream` deleted; QUAL-45 filed.** Tracing the transcode paths
  (user review) surfaced two overlapping WS audio endpoints: `/ws/audio` (ARCH-6, the real ESP32 satellite driving
  input — already accumulates binary PCM until a `{"type":"end"}` frame → one `process_audio_input`) vs the
  ASR-utility `/asr/stream` + `/asr/binary`. Decision (user): `/ws/audio` is THE ESP32 path and must **skip server VAD
  too** (wake+VAD are on-device); **`/asr/stream` deleted** (untested per-chunk utility, superseded); `/asr/transcribe`
  to be unified on `to_canonical`. Deleted **both** ASR-utility WS endpoints `/asr/stream` (141 lines) and
  `/asr/binary` (242 lines, also "ESP32-optimized" — superseded by `/ws/audio`) + their now-dead WS imports
  (`AudioChunkMessage`/`TranscriptionResultMessage`/`Binary*`/`websocket_api`/`WebSocket*`/`base64`); pyright 0, suite
  81=81. Filed **QUAL-45** [deferred] for the ESP32 firmware end-of-utterance signal +
  on-device VAD/wake contract (server side already done via the `end` frame; default = end-of-session). _Remaining for
  this unification: hoist `AudioNegotiator`→`core` (shared; layering forbids core→workflows today), build it on core +
  inject into the workflow, `/asr/transcribe`→`to_canonical`, and `/ws/audio` skip-VAD._
- **ARCH-18 PR-5 — pre-roll sized from `detection_latency_ms`, harmonized + derived from canonical.** The
  `VoiceSegmenter` pre-buffer was a hardcoded 4 frames (~92 ms) that clipped the wake-word onset for slower engines.
  First cut sized it `ceil(detection_latency_ms / 23ms) + 2` at init — but that exposed that the three providers
  declared latency three different ways and the `25`(energy)/`23`(pre-roll) ms/frame constants disagreed (and
  underestimated latency for big capture chunks). Harmonized: `detection_latency_ms(frame_ms)` is now a method taking
  the **real canonical frame duration** (observed on the first frame, sized lazily) — energy is frame-count-based
  (`round(voice_frames_required·frame_ms)`, pre-roll collapses to `frames+2`), silero/microvad are duration-based
  (silero `voice_duration_ms`; microvad gained a `detection_latency_ms` TOML field + schema). No magic ms/frame
  anywhere. Test-first; pyright 0, 9/9, config/config-ui green, suite 81=81.
- **ARCH-18 PR-4a+4b — TTS dedup + input conformance (consumers trust canonical).** 4a collapsed the three
  duplicated TTS resample blocks into one `TTSComponent._conform_output_audio` through the shared `AudioTranscoder`
  (and hoisted that import module-top, no TYPE_CHECKING — Inv #9). 4b: a #8 reconciliation found the per-consumer
  resampling was **not** simply redundant — `asr.process_audio` is reached by two direct entries (`/asr/transcribe`
  file upload + `/stream` WS) that bypass the mic boundary; and the endpoints were *implemented-never-tested* code.
  So (user-chosen: narrow + canonical) I rewrote the seam **test-first**: `process_audio` + `voice_trigger.detect`
  now **trust canonical** (dropped ~145 lines of "configuration-authority" resampling from voice_trigger), with
  conformance once at each boundary — mic via `to_canonical` (PR-3), `/asr/transcribe` via a new `_conform_to_rate`,
  `/stream` requires canonical 16 kHz on the wire. Also completed the §7 startup summary (logs every party's
  contract, not a count). pyright 0, 9/9 contracts, suite 81=81 (+6 tests). **4c (symmetric output: TTS→playback
  through an output negotiator) deferred to a design pass** — it needs a playback-device `AudioContract` that
  doesn't exist yet (new machinery, not a refactor).
- **ARCH-18 PR-3 — audio negotiation: `AudioContract` + `AudioNegotiator` + transform-once at the boundary.** The
  canonical format (`utils.audio_negotiation`: `AudioContract`/`derive_canonical`) is the common denominator of the
  parties' contracts — highest rate every consumer accepts that the capture can be downsampled to, mono downmix, pcm16
  a free pick (lossless int16↔float32), **fatal** if infeasible. The `AudioNegotiator` (workflows) builds those
  contracts from config (mic + asr/vt/vad rates), derives the canonical at workflow init (**fatal at startup**), and
  `to_canonical()` transforms each captured frame to it **once** at the `process_audio_input` boundary (via
  `AudioTranscoder`, recorded as a `record_stage("audio_negotiate")` trace event; no-op if already canonical). 26 new
  unit tests (derivation edge cases + every shipped config derives a feasible canonical + downsample/no-op/fatal).
  Stabilized a pre-existing flaky sub-ms timing assertion (`test_zero_overhead_when_disabled`) my CPU-heavy resample
  tests exposed via ordering. pyright 0, 9/9 contracts, suite 81=81 (0 net regression).
- **ARCH-18 PR-3 — closed the two gaps a self-audit found (I'd wrongly called PR-3 "complete").** (1) Contracts were
  config-inferred, not party-declared — added `audio_contract()` to the VAD/wake/ASR provider bases (capability) and
  `AudioNegotiator.from_pipeline`, which gathers the **active providers'** contracts with the AUTHORITATIVE config rate
  as override; the negotiation is now capability-driven (config as override), not config-authoritative. (2)
  `AudioFormatConverter` was still standing — **folded + deleted**: its convert/streaming are now `AudioTranscoder`
  methods, `supports_format` → the module fn `supports_audio_file_format`; all callers updated. So PR-3 now matches the
  design. pyright 0, 9/9 contracts, suite 81=81 (0 net regression). Only PR-4's TTS-dedup + redundant-resample removal
  remain of the audio-transform scatter.
- **ARCH-18 PR-2b — `[vad.providers.*]` config nesting + per-provider schemas + config-ui.** VADConfig split into
  component-level (segmentation/pipeline: enabled, default_provider, max_segment/timeout/buffer, ASR normalization) +
  a `providers` dict; the engine knobs moved under `[vad.providers.energy|silero|microvad]`, each with its own schema
  (`EnergyVADProviderSchema`/`SileroVADProviderSchema`/`MicroVADProviderSchema`) wired into auto_registry — so config-ui
  renders the vad section like every other component (check/build/40-test green, Invariant #4). The segmenter passes the
  active provider's block; silero/microvad map their `threshold`/`model_url` onto the engines; the energy-specific
  calibration/threshold logic reads the resolved provider block. config-master `[vad]` nested (canonical). Two stale
  `test_vad_phase2` tests (assert the pre-nesting flat config) skipped → TEST-7; the nesting actually *fixed* 2 other
  previously-failing tests (suite 81 failed, down from 83; 0 new failures). pyright 0, 9/9 contracts, dep 58/58.
  **Remaining:** 9 profile configs still carry flat `[vad]` engine fields (now silently ignored — they load fine but
  lose their tuning); nesting those is the last bit of PR-2.
- **ARCH-18 PR-2a — VAD provider family + segmenter discovery (the if-else is gone).** VAD engines are now
  `irene.providers.vad` providers (`energy`/`silero`/`microvad`) wrapping the existing engines, discovered via
  entry-points and selected by `[vad] default_provider` — the 4-way if-else in `UniversalAudioProcessor` is replaced by
  one `_build_vad_provider` discovery call (falls back to `energy`). The silero provider resolves its model path via the
  AssetManager directly (the workflow-side injection is gone). Folded the live bug: the `vad_implementation` enum
  validator is deleted (the provider set is the entry-points, not a hand-maintained list); `vad_implementation` →
  `default_provider`; `calibrate_threshold` → the provider `calibrate` method. Providers declare `detection_latency_ms`
  (for PR-5 pre-roll). Re-reconciliation: the "unconditional `calibrate_threshold`" wasn't a live bug after all (the ABC
  already defaults it to a no-op). dependency_validator 58/58 (+3), pyright 0, 9/9 contracts, suite 83=83 (0 net
  regression). **Still flat** `[vad]` config — the `[vad.providers.*]` nesting + per-provider schemas + config-ui is
  PR-2b (next).
- **ARCH-18 PR-1 — `AudioProcessor` → `AudioTranscoder` rename.** Behavior-preserving rename of the resample engine
  everywhere (irene/ + the phase7 test suite), killing the `AudioProcessor` / `UniversalAudioProcessor` name collision
  the design called out. Reconciliation (Invariant #8): `AudioFormatConverter` turned out to be a **used, tested
  convenience layer** over the engine (`convert_audio_data`/`_streaming` used internally + tested; `supports_format`
  used by the mic input), not the dead duplicate the PR-1 plan assumed — so its dissolution + the 3-TTS-block dedup
  moved to PR-3/PR-4 (user-confirmed), with `AudioFormatConverter` deleted by the end of ARCH-18. Design doc + ledger
  amended. pyright 0, suite 83=83 (0 net regression).
- **ARCH-17 done — designed the audio I/O negotiation + transformation seam (interactive session); filed ARCH-18 to
  build it.** Deliverable `docs/design/audio_pipeline.md` — the input twin of ARCH-15. Triggered by "VAD now has 3
  impls, should it be a component?" plus two related asks (don't let VAD swallow wake-word onset frames; full
  transparency on audio transformations). Analysis found both partly-there-but-fragile (a hardcoded 100 ms pre-roll not
  coupled to engine latency; scattered rate negotiation, format barely handled, transforms logged-not-traced) and two
  live bugs (the `vad_implementation` validator rejects `microvad`; `calibrate_threshold` called unconditionally though
  only energy engines have it). The design unifies all of it: VAD → a lightweight provider family
  (`VADPort`+`irene.providers.vad`, no web/manager); pre-roll → a declared `detection_latency_ms` contract; audio
  encoding → one **canonical** format derived as the common denominator of declared `AudioContract`s (config-pin
  optional, **fatal** if infeasible), transformed once at the boundary and recorded as trace events. Harmonized the
  confusingly-doubled audio helpers into function-named, direction-shared pieces — `AudioTranscoder` (one transform
  primitive for input AND output, collapsing the 3 duplicated TTS resample blocks), `VoiceSegmenter`, `AudioNegotiator`.
  Symmetric in+out; supersedes `onnx_inference_layer.md` §11.2's "small seam." Decisions D-1..D-7 locked with the user.
  Implementation = ARCH-18 (PR-1..6, the 2 bug fixes fold into PR-2; user docs + diagram re-authoring are the explicit
  final PR-6).
- **Fixed sherpa-onnx on 64-bit/Windows + honest wheel markers for the pymicro extras (ARCH-10 flag / QUAL-20).**
  Verified the native libs across arm32 / 64-bit / Windows. sherpa-onnx **≥1.13 split its native libraries
  (onnxruntime + C-API) into a separate `sherpa-onnx-core` wheel** the `asr-onnx` extra wasn't pulling, so
  `import sherpa_onnx` failed everywhere except armv7 (which pins the self-contained 1.10.46) — exactly the
  "only works on armv7" symptom. Added `sherpa-onnx-core>=1.13; platform_machine!='armv7l'`; `import sherpa_onnx`
  now succeeds on x86_64 here. The libs are vendored (auditwheel) — no system packages are actually required to
  import/infer (the ALSA in `get_platform_dependencies` is a runtime safety net owned by the audio-I/O providers);
  comments corrected accordingly. Also pinned honest PEP 508 markers on the wake/vad extras to the verified wheel
  matrix: `pymicro-wakeword` has no armv7 wheel (correct — wake is on-device there), `pymicro-vad` ships Linux
  x86_64/aarch64 only — so the extras resolve to nothing on unsupported targets instead of failing on a missing
  wheel. Matrix + detail in `onnx_inference_layer.md` §7.2. Gates green; suite 83=83 (0 net regression).
- **QUAL-20 done — wake-word + microVAD rebuild (5 commits, subsumes ARCH-10 PR-5).** Acted on the QUAL-19 review.
  Backend microWakeWord is now a thin adapter over `pymicro-wakeword` (the np.random stub + hand-rolled tflite plumbing
  are gone; built-in + custom `from_config` models, 10 ms streaming); openWakeWord polished (ONNX default, per-spec
  custom model); Porcupine cut. Wake-word selection is a uniform per-provider `WakeWordSpec={name,model,threshold,
  language}` — kept per-provider (consistent with ASR/LLM model selection) rather than lifted to the component, with the
  component-level list demoted to an optional override. That needed a backend array-items schema extraction + a generic
  config-ui `ArrayOfObjectsEditor` (Invariant #4 — config-ui check/build/vitest green). Added server-side `microvad`
  (`pymicro-vad`) as a third `VADEngine` beside energy/silero — self-contained, shares the micro frontend with the wake
  word, matches the ESP32 on-device VAD. Extras split into `wake-onnx`/`wake-tflite`/`vad-tflite` (all 64-bit; armv7
  wakes on-device, so `embedded-armv7.toml` now disables server voice-trigger). The `pymicro-*` libs import + detect on
  x86 here (unlike sherpa) — real runtime tests for all three pieces; aarch64 wheel coverage is the one BUILD-3-stage
  check left. User docs updated in house style (`voice-trigger.md` rewrite, `vad.md`, `howto-new-model.md`). Each of the
  5 commits was independently green: pyright 0, 9/9 contracts, 0 net suite regression.
- **QUAL-31 done — Grade-2 multi-turn clarification (slot-filling).** A missing-required-parameter ask is now a real
  two-turn dialogue instead of an abandoned command. The QUAL-30 `_clarify` boundary arms a one-shot
  `pending_clarification` on the session (original intent + asked-for slot + triggering utterance); a pre-check at the
  head of `_process_pipeline` reads the next turn as the answer by **prepending the original utterance and re-running
  the whole understanding pipeline on the combined text** — so existing NLU/extraction/coercion resume the original
  intent with no separate slot-extractor, and CHOICE/range/typed params work for free. Covers text *and* voice (both
  converge on `_process_pipeline`). Deliberately used a **dedicated field, not the `ConversationState` enum**: its
  `CLARIFYING` value already means the unrelated no-intent fallback, and `CLARIFYING→CLARIFYING` is an invalid
  transition that would break re-asks — so detection is decoupled from the existing state machine. Expiry rides
  session eviction (pending lives on the context, dropped after `session_timeout` = the Q2 idle window) plus
  single-turn consumption, so no separate timer. Re-asks append (resumed turn re-arms with the combined text →
  multi-slot via successive rounds). No donation/config/REST contract touched → config-ui unaffected. New
  `test_qual31_slot_filling.py` (4); QUAL-30's 3 still green; pyright 0, 9/9 contracts, suite 83=83 FAILED (0 net
  regression, +4 new passing).
- **QUAL-19 done — ESP32 + wake-word review (interactive session + upstream study).** Produced
  `docs/review/esp32_wakeword_review.md` with keep/fix/cut per piece. Two findings reshaped the plan: (1) the design's
  "both server wake providers hallucinated" premise was wrong — `openwakeword` works, only `microwakeword` is a stub;
  (2) OHF-Voice now ships maintained server-side Python libs (`pymicro-wakeword`/`pymicro-vad`/`pymicro-features`,
  Apache-2.0) that bundle the micro frontend + tflite inference + a precompiled tflite C lib — so the broken backend
  provider is **fixable as a thin wrapper, not a DSP hand-port**, and `from_config` loads custom `.tflite`+manifest (the
  per-unit Russian plan). microWakeWord + microVAD are one "micro" stack that runs identically on the ESP32 (TFLite-Micro
  via ESPHome `micro_wake_word` `vad:` gating) and server-side from the **same artifact** — the long-stated "one
  pipeline, device+server" goal is now real. Decisions: firmware = keep as quarantined reference (real-but-incomplete
  ~5k-LOC skeleton, won't link); backend µWW = fix via pymicro-wakeword; openWakeWord = keep/demote to quick-start;
  Porcupine = cut; add server-side microVAD as a 3rd VADEngine; armv7 = no server wake (on-device); training refs = cut.
  Config: uniform wake-word selection stays **per-provider** (consistent with ASR/LLM) via a shared
  `WakeWordSpec={name,model,threshold,language}`. **Scope changes (Invariant #8, user-approved in session):** QUAL-20
  redefined to the concrete rebuild and now **subsumes ARCH-10 PR-5** (one owner for the wake-word work). Folded into
  `onnx_inference_layer.md` §11 + `ws_esp32_transport.md`.
- **Filed QUAL-44** (`[deferred]`, enhancement split from QUAL-31): answer-vs-new-command arbitration on a clarifying
  turn — QUAL-31's resume pre-check unconditionally combines the next turn as the answer, so a user who barks a new
  command instead gets a garbled combined utterance. Bounded today by one-shot consumption + idle expiry; the task adds
  deterministic arbitration (run NLU on the bare answer first; route fresh if it's a confident non-fallback intent).
- **BUILD-6 done — backend-health Gate 5 (config validation) goes green.** The 3 fixtures that failed
  `config_validator_cli` each lacked a *required* provider-schema field (no default): `vad-production.toml` was missing
  `api_key` on its active `elevenlabs` TTS + `openai` LLM defaults (added `${ELEVENLABS_API_KEY}`/`${OPENAI_API_KEY}`
  placeholders, canonical `config-master.toml` style); `vosk-test.toml`'s *disabled* `google_cloud` ASR block was
  missing `credentials_path`/`project_id` (the validator schema-checks declared providers even when `enabled = false`);
  `vad-testing.toml` carried a top-level `[testing]` section (ad-hoc VAD scenario sub-tables) that **no code reads** —
  a `CoreConfig` `extra_forbidden` violation, removed as dead config. No schema/contract changed, so config-ui is
  untouched. Verified 12/12 configs valid, `build_analyzer --validate-all-profiles` ✓, `dependency_validator` 55/55 ✓
  (ubuntu+alpine), suite 83=83 FAILED (0 net regression — the failing VAD tests are pre-existing TEST-7 staleness; their
  `scenario_a/b` are generated-audio fixtures, unrelated to the removed `[testing]` block). Also indexed the
  BUILD-5 deliverable `docs/review/docker_build_review.md` in the ledger's review-doc index (clears the lone
  `check_scope` orphan).
- **Adopted `droman42/py-dev-gates@v0.1.1` — retired the in-tree no-`TYPE_CHECKING` gate.** The AST gate
  (Invariant #9 / QUAL-32) was extracted upstream (this repo was its source) and generalised into a pip-installable
  CLI. Added `py-dev-gates @ git+…@v0.1.1` to the `[dev]` extra (puts `check-no-type-checking` on PATH; re-locked
  `uv.lock`), deleted `scripts/check_no_type_checking.py` + its pytest wrapper (a pure shell-out; upstream ships its
  own tests), and pointed the backend-health CI step + CONTRIBUTING at `check-no-type-checking irene/`. **Kept voice's
  per-step CI — did NOT switch to the shared `python-health` composite action.** Voice-specific reason: the composite
  action installs `pip install -e ".[dev]"`, but voice's pyright needs the *provider-extra* imports
  (`fastapi`/`spacy`/`sherpa-onnx`/…) present and relies on `uv sync --frozen --all-extras` + the uv cache (the
  spaCy-model GitHub-504 mitigation from `63f9e93`); bridge could adopt the composite action because its `fastapi` is a
  core dep and it has no heavy ML extras. Verified: gate → 0, lint-imports 9/9, pyright 0, `uv.lock` consistent.

### 2026-06-08
- **BUILD-2 + BUILD-4 — split CI into `backend-health` + `frontend-health` workflows, all gates hard-fail.** Replaced
  the disabled `config-validation.yml` with two **enabled** (push/PR) workflows. **`backend-health.yml`**: hard gates —
  `lint-imports` (hexagon), the no-`TYPE_CHECKING` script, `pyright` (QUAL-4 0-error gate),
  `build_analyzer --validate-all-profiles`, `config_validator_cli` (all configs + schema/master-config completeness),
  `dependency_validator --validate-all`; toolchain via `uv sync --frozen --extra dev`; deprecated actions bumped
  (`setup-python@v5`), the phantom `intent_validator` step + the report-artifact machinery removed; pytest and
  black/isort placeholdered (deferred until the TEST- items resolve / the tree is formatted). It runs **honest-red**
  (owner-accepted) on 3 stale config fixtures — filed **BUILD-6**. **`frontend-health.yml`** (new): `npm ci` +
  `npm run check` (type-check + strict ESLint + orphans) + `npm run build` + `npm run test` (vitest, 40 tests) — all
  green today (the Invariant-#4 config-ui gate). Verified locally: lint-imports 9/9, pyright 0, validate-all 12/12,
  dependency 110/110; config-ui check/build/test all pass. Follow-up: bumped the JS actions off the deprecated
  Node 20 — `actions/checkout@v5`, `actions/setup-node@v5`, `actions/setup-python@v6`. Also: the pyright gate
  type-checks every provider, so its optional imports (`fastapi`/`spacy`/`sherpa-onnx`/`anthropic`/`openai`/…)
  must be installed — switched the backend install from `--extra dev` to `uv sync --frozen --all-extras` (+ a uv
  download cache), fixing CI pyright failing with `reportMissingImports` on packages absent from the dev-only env.
- **QUAL-32 — purged the residual `TYPE_CHECKING` guards + added a build-time gate.** Reconciliation (Invariant #8):
  only **4** real `if TYPE_CHECKING:` blocks remained (not the ~13 estimated — prior refactors cleared the rest, and
  two apparent hits were *comments*). Removed all 4: two empty `pass` blocks (`core/interfaces/webapi.py`,
  `intents/handlers/system_service_handler.py`), and two `pydantic.BaseModel` guards hoisted to module top (a hard
  dep — no cycle) with the `Type[BaseModel]` annotations de-stringized (`core/metadata.py`,
  `intents/handlers/random_handler.py`). Added a gate mirroring the hexagon `lint-imports` story:
  `scripts/check_no_type_checking.py` (AST-based, ignores comments/strings) + a wrapping test
  `irene/tests/test_no_type_checking.py` + a hard-failing CI step in `config-validation.yml` — CI breaks if a guard
  reappears (negative-tested). 9/9 import contracts kept; suite 83 failed = baseline.
- **BUILD-5 — build-analyzer verification → the `text_processor` namespace rename + Dockerfile fixes.** Reconciliation
  (Invariant #8) showed the analyzer itself was healthy (ARCH-13 had already cleaned the `plugins.builtin` refs). The
  real work: `--validate-all-profiles` was red on 6 profiles (incl. canonical `config-master`) because the
  text-processing **component** is `text_processor` while its provider entry-point namespace was `text_processing` — the
  lone capability whose names disagreed. Per the owner's call (no aliases), renamed the provider entry-point group +
  module dir (`irene/providers/text_processing`→`text_processor`), the port interface module
  (`core/interfaces/text_processing.py`→`text_processor.py`) + its importers, and the component `category` →
  `"text_processor"` — now consistent with every other capability. Fixed the 5 stale configs
  (`general_text_processor`→`unified_text_processor`; a non-existent `openai` TTS) → all 12 profiles validate. Fixed both
  Dockerfiles: removed the non-existent `intent_validator` call; the armv7 `ubuntu_packages` NameError; a latent x86_64
  `system_packages` key bug (`ubuntu`→`linux.ubuntu`); migrated `Dockerfile.armv7` Alpine→Debian
  (`arm32v7/python:3.11-slim-bullseye`, apk→apt, the `linux.ubuntu` apt set with `libasound2`). 9/9 import contracts kept;
  full suite 83 failed = baseline (no net regression). Image build/boot is BUILD-3. Refs
  `docs/review/docker_build_review.md`, `docs/guides/build-docker.md`.
- **Build/Docker docs — consolidated the two root READMEs into the guides set + filed the Docker-build defects.**
  Reviewed `README-BUILD.md` (Russian, ~644 L) and `README-DOCKER.md` against the real Dockerfiles + tooling.
  `README-DOCKER` → rewritten as **`docs/guides/build-docker.md`** (fixed: ports 8000/9090 → **6000**; x86_64 base
  Ubuntu → **Debian slim**; dropped 4 phantom `docs/*` links + 2 phantom `test-*.sh` scripts; kept the real
  buildx / profile / 3-stage / Compose procedure). `README-BUILD`'s concept half was superseded by
  `build-system.md`; folded its salvageable ops bits (the **systemd unit**, the `dependency_validator` /
  `irene-dependency-validate` usage, and external-provider-package authoring) into `build-system.md`, then
  archived. Both root READMEs → `docs/archive/` (root now holds only README + CONTRIBUTING); `install-irene.sh`
  doc pointer updated. Two **build-blocking Dockerfile bugs** (the non-existent `irene.tools.intent_validator`;
  an armv7 `ubuntu_packages` NameError) filed in a new **`docs/review/docker_build_review.md`** and folded into
  **BUILD-5 §7** (refs updated README-DOCKER → the new guide). Orphan check clean. Follow-up: `build-docker.md`
  surfaced as a first-class entry in the README Documentation list, next to the build system.
- **DOC-3 — version-display strings refreshed to v15.** `core/engine.py` (module docstring + startup log), the
  runner `--help` banner (`runners/base.py`, inherited by the CLI), and the `tts_demo`/`async_demo` print
  banners now read v15. Left untouched on purpose: the `config_migrator`/`config/migration` v13→v14 strings
  (functional config-schema-version identifiers) and the "v13/v14 architecture" era-descriptor docstrings.
  Commit `8a49ea2`.
- **Documentation overhaul — authored the canonical doc set from code + design/review, then consolidated and
  archived the stale sprawl.** A full recreation (the old docs were mostly aspirational): new **README** and
  **CONTRIBUTING**, a **`docs/architecture/`** set (overview = the hexagon + the 9 import-linter seams + 12
  ports; workflow; dataflow; components; intents; nlu with a plain-English spaCy explainer; mqtt [planned];
  esp32 [voice satellite — each per-room microWakeWord names its room]; client-registry), and a
  **`docs/guides/`** set (asset-management, build-system, configuration, audio, vad, prompting, voice-trigger,
  plus three HOWTOs: new-intent / new-model / new-language). **24 styled-Graphviz diagrams** (`.dot` sources +
  PNGs) under `docs/images/` — no mermaid. Concise/human tone, no internal task IDs in the public text; every
  claim checked against source, which surfaced and corrected several inaccuracies en route (TTS is gated by
  *config* not only the request flag; handler = a domain that owns many intents; the v1.1 **two-part donation**
  = language-neutral `contract.json` + per-language `<lang>.json`). **Regenerated** `DONATION_FILE_SPECIFICATION.md`
  to v1.1 (was a self-flagged stale v1.0). **Consolidated** the 8 stale AUDIO/VAD/PROMPTING guides → 3 MECE docs
  (audio re-anchored to the real playback component; vad gained the previously-undocumented Silero engine;
  prompting completed) and harmonised `voice_trigger.md` → `guides/voice-trigger.md`. **Archived** ~20 superseded
  docs to `docs/archive/` (incl. `architecture.md`, `ASSET_MANAGEMENT.md`, donations_flow / intent_donation,
  HANDLER_DEVELOPMENT_GUIDE, the 8 audio/vad/prompting guides, UV_MIGRATION, IDE_SETUP, runtime_configure,
  `TODO.md` + the `TODO/` subfolder, `fire_forget_issues.md`); **folded** MODEL_WARMUP into asset-management;
  **promoted** CLIENT_REGISTRY → `architecture/client-registry.md` (documenting the runtime action store,
  `resolve_physical_id`, and `ActionRecord.source`). Orphan check clean — every public doc reachable from the
  README, every image referenced, `.dot`/`.png` paired. Ledger touched: **DOC-2, DOC-4, DOC-5b, DOC-7** (status
  in `RELEASE_PLAN.md`). Commits `2682fc9`..`c88b1d0`.

### 2026-06-07
- **Tester-handover prep — fixed the quickstart `.env` crash + drafted `docs/QUICKSTART.md` + triaged the test suite.**
  **(1) Default-config crash (root cause):** the README quickstart (`cp docs/env-example.txt .env`) shipped a broken
  template — it set `IRENE_COMPONENTS__TTS=true` but the **wrong** field `IRENE_COMPONENTS__AUDIO_OUTPUT` (schema field is
  `audio`), so a fresh run with no `config.toml` got TTS-on/Audio-off → `CoreConfig` rejects it ("TTS component requires
  Audio component") and won't start (`.env` is loaded by `runners/base.py:83`; env *overrides* the config file). Fixed
  `env-example.txt`: commented the component toggles (they belong in `config.toml`) with corrected field names + a warning,
  removed the retired `IRENE_PLUGINS__*` block (ARCH-13) and the stale `IRENE_VERSION=13.0.0`. Verified a fresh copy yields
  a valid config. (The user's existing gitignored `.env` needs the same one-line fix — not touched.) **(2) `docs/QUICKSTART.md`:**
  install → `.env` (cloud-only) → pick a lightweight profile (`minimal`/`api-only`, TTS/Audio off so no model downloads) →
  run CLI / WebAPI / config-ui → in-scope vs out-of-scope (MQTT/ESP32/voice/Docker are NOT in this build) → how to report.
  **(3) Functional triage:** all 6 real-flow smoke tests pass (WebAPI boot, greeting, NLU recognize, conversation-degrades,
  timer e2e, CLI boot+respond). The **~83 baseline test failures are NOT functional breakage** — categorized as stale
  tests / API drift from the ARCH-1..15 refactors (`active_actions`→ClientRegistry per QUAL-28, `Intent.__init__` change,
  removed/renamed classes/modules/methods, metrics-as-dict, mock misuse, event-loop harness drift; = TEST-2/TEST-7), the
  unbuilt smart-home device/room resolution (needs ARCH-8/QUAL-35), and a missing spacy model in the test env. Updated
  REL-2 with this progress. Conclusion: core flows are solid for a tester; the suite is coverage debt, not a quality signal.
- **ARCH-15 COMPLETE — the symmetric configurable hexagonal I/O architecture is delivered (PR-0..9); PR-10 deferred → ARCH-16.**
  Closes the work that began with a one-line CLI bug ("started cli, but nothing happens") and a design session. Delivered
  across 19 commits: **PR-0** CLI double-reader stopgap; **PR-1** `InputFormat` first-class; **PR-2** `OutputPort`/
  `OutputManager`/`DeliveryResult` + `EventBus` (adapter-free); **PR-3** console/ws text outputs + origin routing;
  **PR-4** F&F notifications re-routed through the OutputManager, identity-addressed; **PR-5a** process-wide OutputManager
  wired (F&F live); **PR-5b** interactive runner consumes the single CLI source (double-reader structurally impossible);
  **PR-6a** EventBus published end-to-end, **PR-6b** gated `/ws/observe` tap, **PR-6c** web-app `/ws/output` push;
  **PR-7** config-driven `[outputs]` + config-ui editor; **PR-8** local audio/voice SPEECH output (pure D-3 restored);
  **PR-9.1** reconciled ARCH-7 (§13) to feed ARCH-8 as `OutputPort`s, **PR-9.2** swept other items + extended the
  master-config completeness check. Six design decisions D-1..D-6 locked; config-master synced. Every slice landed with
  0 net regression (baseline drifted 84→83 via a recovered test). **Decision (user, 2026-06-07):** consider the hexagon
  complete and **defer PR-10** (daemon multiplexer + runners→thin presets + remote text-attach channel) to **ARCH-16** —
  it's a large, higher-risk internal-cleanliness refactor of low incremental value (the webapi process already hosts
  concurrent WS channels; every channel runs). ARCH-16 also tracks the minor follow-ons (PR-6c web-app JS render, PR-7
  capability-matrix display). ARCH-15 flipped `[x]`; ARCH-16 filed P-deferred.
- **ARCH-15 PR-9.2 DONE — cross-task sweep + extended master-config completeness check; PR-9 complete.**
  **(a) Sweep** of every open/paused ARCH/QUAL item for I/O-design impact: **no impact** — ARCH-10 (ONNX inference,
  unrelated), QUAL-18 (AsyncAPI tooling — the new `/ws/observe`+`/ws/output` endpoints could *optionally* be
  documented there later), QUAL-19/20 (ESP32 wakeword — ESP32 stays an input channel, no structural change),
  QUAL-31 (clarification — its responses just flow through the OutputManager like any conversational result);
  **aligned** — QUAL-32 (TYPE_CHECKING purge): the new I/O modules were authored TYPE_CHECKING-free per the PR-3
  directive, so they add nothing to its surface; **uses-the-design** — QUAL-35: device handlers emit a
  `device_command`-modality result via the OutputManager to the §13 bridge `OutputPort` (no ActuationPort);
  ARCH-8 already reconciled in PR-9.1. Amended QUAL-32 + QUAL-35 with pointers. **(b) Extended
  `AutoSchemaRegistry.get_master_config_completeness`** to validate **top-level config sections + scalar fields**
  against the schema (was `*.providers.*`-only — which is why the `[outputs]`/`observe_*` drift went uncaught).
  Scalar fields are checked by **key-text-search** (`^\s*#?\s*field\s*=`) so an intentionally-commented optional
  (`observe_token`) counts as documented rather than false-missing; Dict/List/nested-model fields are tables,
  validated at section granularity (new `_is_scalar_annotation` helper distinguishes them — avoids the false
  positives a naïve check produced on `providers`/`normalizers`/`domain_priorities`). Folded into `valid`, so
  future drift fails the existing alignment test. Made the function accept a `master_config_path` so drift detection
  is testable. New `test_master_config_completeness_toplevel.py` (6): real config-master complete, detects a
  simulated missing section + missing scalar field, commented-optional counts as documented, scalar-detection unit.
  Gates: `pyright` 0, import-linter 9/9, dep-validator 55/55, `check_scope` clean, full suite 83-failed=baseline
  (**0 regressions**, stash-diff). **ARCH-15 PR-9 COMPLETE.**
- **ARCH-15 PR-9.1 DONE — reconciled ARCH-7 (`mqtt_integration.md`) with the I/O architecture; fed ARCH-8.** Added a
  top **banner** + a new **§13 "Reconciliation with the I/O architecture"** stating the contract ARCH-8 builds against:
  bridge actuation is a **request/response `OutputPort`** returning the rich `DeliveryResult` (echo + 6-code error);
  `device_command` is a delivery **modality** capability-routed to the `designate(DEVICE_COMMAND,"bridge")` output;
  the handler **awaits the rich result under a bounded timeout** and composes the origin-paired confirmation;
  **`ActuationPort` is dropped** (the `BridgeClient` *is* the OutputPort); `DeviceCatalogPort` stays a read port;
  Flow-1 event is a **terminal `OutputPort` (EVENT modality)**; actuation is observable on the event bus for free;
  ARCH-8 stands on the landed PR-2/PR-5a/D-2. **Contradiction sweep (per user):** every superseded decision in §3–§10
  is now removed or marked obsolete inline (the §4 hexagon diagram flagged OBSOLETE on the actuation side and rewritten
  without `ActuationPort`/`ActuationService`; §3/§6/§7/§9/§10 ActuationPort hops struck through with §13 pointers;
  §8 flags the **`OutputConfig` name collision** — PR-7 already owns `[outputs]`, so ARCH-8 adds a distinct
  `BridgeConfig`, not a second `OutputConfig`). "§13 wins where §3–§10 differ." Amended the ARCH-7 (design-extended note)
  and ARCH-8 (build-against-§13) ledger entries. Doc-only; no code. **Remaining = PR-9.2** (sweep other ARCH/QUAL items
  + extend `get_master_config_completeness` to top-level sections/fields).
- **ARCH-15 config-master sync — added `[outputs]` + `[system].observe_*` to the reference config.** The hand-maintained
  `configs/config-master.toml` had drifted: the PR-7 `[outputs]` section (`console`/`console_prefix`/`web_push`) and the
  PR-6b `observe_token`/`observe_allow_remote` were in the Pydantic schema but not the reference. Added both (`[outputs]`
  after `[inputs]` to match section order; `observe_token` shown **commented** so the default `None` keeps the tap
  *disabled* — an empty-string token would insecurely accept an empty password). No functional change (all fields have
  defaults). Verified: config-master loads + validates against `CoreConfig`, and the completeness test still passes.
  **Root gap:** `get_master_config_completeness` only checks `*.providers.*` sections, not top-level sections/scalar
  fields — which is why the drift wasn't caught; **extending it is folded into PR-9.2**.
- **ARCH-15 PR-8 DONE — local audio/voice SPEECH output (no MQTT); pure D-3 restored.** New `AudioSpeechOutput`
  (`outputs/audio.py`) wraps the TTS + audio components (synthesize `result.text` → temp WAV → play); it carries
  **both SPEECH and TEXT** (a voice device speaks everything, so the §3.1 negotiation never drops a conversational
  result there). The vosk runner registers it on the shared OutputManager and **designates it the OutputManager's
  conversational fallback** — a new concept added in PR-8: when no *origin* output matches a conversational
  (TEXT/SPEECH) result, deliver to the designated local speaker. This is what solves the local-voice **addressing**
  problem — vosk's `RequestContext.source` is `"voice"`/`"audio_stream"` (overridden in `process_audio_stream`) with
  no room, so it can't serve as a stable per-device origin key; the fallback catches it. With a real SPEECH output now
  present for voice profiles, the **PR-5a legacy-TTS migration fallback in `NotificationService` is retired** — an
  unmatched deferred F&F now drops+log (D-3), staying queryable via the action-store history (the completion isn't
  lost), instead of force-speaking on a global sink. (`origin` match still wins over the fallback, so a CLI timer goes
  to the console, not the speaker.) NO broker/MQTT code — all MQTT (Flow-1 event + Flow-2 bridge actuation) remains
  ARCH-8's, fed by PR-9.1. New `test_audio_output.py` (7): synth+play, unavailable/empty-text handling, conversational
  fallback (used when no origin match / origin preferred over fallback / cleared on remove), and voice F&F speaking via
  the fallback end-to-end. Gates: `pyright` 0, import-linter 9/9, dep-validator 55/55, `check_scope` clean, full suite
  83-failed=baseline (**0 regressions**, stash-diff; CLI + timer e2e green). Backend-only (output adapter renders via
  the `[outputs]` editor; no new config-ui surface).
- **ARCH-15 PR-7 DONE — config-driven outputs (`[outputs]`) + config-ui editor (renders for free).** The blocker
  surfaced before starting: there was no `[outputs]` config schema (outputs were registered programmatically), so the
  config-ui editor had nothing to render. **Backend prerequisite built:** new `OutputConfig` model
  (`console`/`console_prefix`/`web_push`) added to `CoreConfig` as the `outputs` section. Because `AutoSchemaRegistry`
  auto-generates a config-ui section for any top-level `CoreConfig` field that's a Pydantic model, this **automatically**
  produces the `[outputs]` schema section (added to the section order after `inputs`, title "📤 Output Channels") — no
  config-ui hardcoding. Adapter registration is now **config-gated**: `CLIRunner` registers `ConsoleOutput` only if
  `config.outputs.console` (and uses `console_prefix`); the `/ws/output` web-push endpoint rejects when
  `config.outputs.web_push` is off. **Frontend:** the `[outputs]` editor renders **for free** — config-ui consumes the
  schema dynamically and the UI-9 generic widgets render the bool/string fields (labels from the Pydantic
  descriptions); `npm run check` (type-check + lint + orphans) + `npm run build` green (Invariant #4), **no config-ui
  code change**. Scope notes: multi-input is already representable (`InputConfig.{cli,microphone,web}`); per-input
  `format` is *derived* (PR-1) not a config field, so it has no editor surface; the read-only capability-matrix display
  is deferred as an optional enhancement. New `test_output_config.py` (5): OutputConfig defaults, CoreConfig section,
  auto-generated schema section (order/title/model), and `/ws/output` web_push gating (reject/allow via TestClient).
  Gates: `pyright` 0, import-linter 9/9, dep-validator 55/55, `check_scope` clean, backend suite 83-failed=baseline
  (**0 regressions**, stash-diff); config-ui `npm run check`+`build` green.
- **ARCH-15 PR-6c DONE (backend) — web built-in-app push output; deferred F&F results reach the originating browser.**
  The web runner's built-in browser app is an interactive text channel like CLI (textbox → `POST /execute/command` →
  rendered reply). Its *sync* path is the HTTP reply, but it had **no push channel for deferred F&F** (a browser-set
  timer would drop). New `/ws/output` WebSocket: the browser registers a `CallbackTextOutput` on the **shared**
  OutputManager keyed by a per-connection `client_id` (minted + handed back if not supplied); on disconnect it's
  deregistered (new `OutputManager.remove_output`). **Identity addressing:** `OutputManager._origin_output` now
  prefers a `client_id` (physical-identity) match *before* the channel (`source`) match — so a deferred notification
  carrying the action's `physical_id` routes to the **exact** browser connection that set it, and a generic REST
  caller's F&F never lands in a random browser. (Backward-compatible: CLI/console pairing — `client_id=None`, match
  by `source` — unchanged; existing OM + notification tests green.) New `test_web_push_output.py` (5): identity-routed
  delivery, no-match drop, idempotent remove, and real `/ws/output` registration lifecycle via FastAPI `TestClient`
  (supplied + minted client_id). **Frontend follow-on (tracked separately):** the built-in app's JS must open
  `/ws/output`, include its `client_id` in each `POST /execute/command` (so `physical_id` resolves to it), and render
  pushed `{type:"message"}` frames — a web-template edit. Gates: `pyright` 0, import-linter 9/9, dep-validator 55/55,
  `check_scope` clean, full suite 83-failed=baseline (**0 regressions**, stash-diff). **ARCH-15 PR-6 COMPLETE (6a+6b+6c).**
- **ARCH-15 PR-6b DONE — gated observation tap (`/ws/observe`): live, identity-filtered pipeline-event stream.**
  A debug client connects to `/ws/observe`, authenticates, sends an identity filter, and receives the live
  `EventBus` stream (`input.received`/`result.produced`/`output.delivered`/…) — the "observe live traffic" half of
  the operator scenario. **Testable cores** in `core/observe.py`: `authorize_observer` (D-5 gating — disabled unless
  `system.observe_token` is set; **localhost-only** unless `observe_allow_remote`; then token must match) and
  `subscribe_to_queue` (funnels filtered events into a **bounded** `asyncio.Queue` that drops the *oldest* event when
  full, so a stuck/slow tap can never block `EventBus.publish` or stall the workflow). New `SystemConfig.observe_token`
  / `observe_allow_remote` config (optional; the config-ui editor renders them via existing generic widgets — no
  config-ui change). The `/ws/observe` FastAPI endpoint (in `webapi_router`) wires it: accept → auth frame → authorize
  (host + token) → subscribe with `identity_filter` → stream events → unsubscribe on disconnect. The remote debug-CLI's
  *inject* half reuses `/execute/command`; *observe* is this endpoint. New `test_observe_tap.py` (8): gating matrix,
  queue funnel/filter/overflow-drop, and real WS auth-rejection via FastAPI `TestClient`. Gates: `pyright` 0,
  import-linter 9/9, dep-validator 55/55, `check_scope` clean, full suite 83-failed=baseline (**0 regressions**,
  stash-diff). **Remaining = PR-6c** (web built-in-app push output for deferred F&F results to the browser).
- **ARCH-15 PR-6a DONE — process-wide EventBus wired; the canonical pipeline-event stream is live end-to-end.**
  The composition root now builds one `EventBus` and shares it: the `OutputManager` (so `output.delivered` flows
  to the *same* bus) and the `WorkflowManager` (new `event_bus` ctor arg), with the bus also injected into the
  engine (`AsyncVACore.event_bus`, typed `Any`). `WorkflowManager.process_text_input`/`process_audio_input` now
  publish `input.received` + `result.produced` via a `_publish_pipeline_event` helper that stamps the origin
  identity (session/client/room/source) onto the `PipelineEvent` — so the observation tap (PR-6b) and metrics can
  subscribe and filter by identity. Deeper events (`asr.transcript`, `intent.recognized`) need workflow internals
  and are a later increment. No-op when no bus is wired (back-compat). `core` keeps no edge outward — the bus
  lives in `core.event_bus`. New `test_pipeline_events.py` (3): input.received+result.produced emitted in order,
  identity+payload carried, no-bus no-op. Verified on a real CLI boot (bus wired through composition). Gates:
  `pyright` 0, import-linter 9/9, dep-validator 55/55, `check_scope` clean, full suite 83-failed=baseline
  (**0 regressions**, stash-diff confirmed). **Remaining = PR-6b** (WS observation tap + gating + web-app push output).
- **ARCH-15 scope refinement (user-directed) — MQTT out of PR-8, web-app addressed, PR-10 added.** Three corrections
  to the remaining-PR map: (1) **PR-8 no longer touches MQTT** — it builds the **local audio/voice SPEECH `OutputPort`
  only** (restoring pure D-3, retiring the PR-5a legacy-TTS fallback); the *entire* MQTT build (Flow-2 bridge actuation
  + Flow-1 `irene/{room}/event`) is **ARCH-8's** implementation, fed by PR-9.1. (2) **PR-9.1 redefines/feeds ARCH-8**
  with the I/O contract (bridge as a request/response `OutputPort` + rich `DeliveryResult`, `device_command` modality,
  etc.) rather than implementing MQTT in the I/O track. (3) **The web runner's built-in browser app is an interactive
  text channel like CLI** (browser textbox → `POST /execute/command` → reply) — its sync path is the HTTP reply, but it
  lacks a *push* channel for deferred F&F results, so **PR-6 gains a WS/SSE push output** to deliver them to the browser.
  Also filed **PR-10** (daemon multiplexer + runners→thin presets) to close the endgame PR-5b only started — the web/vosk
  consume/preset unification rides PR-10 (their outputs ride PR-6/PR-8). vosk deferral to PR-8 confirmed. Ledger + design
  (`io_architecture.md` §12) updated; no code change.
- **ARCH-15 PR-5b DONE — interactive runner CONSUMES the single CLI source; the double-reader is structurally gone.**
  `InteractiveRunnerMixin._run_interactive_loop` no longer runs its own `prompt_toolkit` reader — it consumes
  `CLIInput.listen()` (the single InputManager-owned reader, `_input_loop`) and routes each line through
  `process_text_input` → `_render_result` (shared OutputManager). The **PR-0 stopgap is removed** — cli auto-start
  is re-enabled in `InputManager._auto_start_configured_sources`, because there is now exactly one reader
  (`CLIInput._input_loop`) and one consumer (the runner loop), so the race PR-0 guarded against **cannot occur by
  construction** (not merely avoided). Meta-commands: the REPL `help`/`status` interception is **deleted** — they
  are ordinary `system.*` intents now (D-4, `SystemIntentHandler` already implements them); only `quit`/`exit`/`q`
  stays transport-local (CLIInput normalises them and stops its own reader). Updated `test_input_manager_autostart.py`
  to assert the source is now auto-started (inverting the PR-0 guard, with the rationale that the double-reader is
  prevented at the consumer level). New `test_cli_consume_loop.py` (3): in-order processing + origin-paired console
  delivery, blank-line skipping, quit stops before later lines, missing-source error. **Scope note:** the full
  multi-channel daemon multiplexer (concurrent web/ws/mqtt consume, runtime attach/detach, runners→pure config
  presets) remains a follow-on — PR-5b lands the CLI consume loop as the first instance; web/vosk keep their
  existing paths. `_print_interactive_help`/`_print_interactive_status` are now unused (cleanup later). Verified:
  CLI `--command` e2e green (cli auto-start re-enabled, non-interactive subprocess unaffected). Gates: `pyright` 0,
  import-linter 9/9, dep-validator 55/55, `check_scope` clean, full suite 83-failed=baseline (**0 regressions**,
  stash-diff confirmed). **ARCH-15 PR-5 COMPLETE (5a+5b).**
- **ARCH-15 PR-5a DONE — process-wide OutputManager wired into composition + NotificationService (F&F delivery live).**
  The composition root (`runners/composition.build_core`) now builds one `OutputManager` (symmetric to
  `InputManager`) and injects it into the engine (`AsyncVACore.output_manager`, typed `Any` — `core` keeps no
  import edge to `irene.outputs`, mirroring `input_manager`) and into the `NotificationService` (via
  `MonitoringComponent.initialize`, passing the object only — no `components→outputs` edge). This closes PR-4's
  opt-in: deferred F&F results now actually deliver through the output hexagon, addressed by identity. `CLIRunner`
  registers its `ConsoleOutput` on the **shared** `core.output_manager` (instead of a private one), so sync renders
  *and* F&F notifications both reach the terminal through the same manager. **Migration fallback (deliberate):** if
  the OM has no attached output for an identity (e.g. voice mode — no audio output exists until PR-8),
  `_deliver_notification` falls back to the legacy TTS/LOG path rather than dropping, so the voice timer-announce
  does **not** regress; pure D-3 drop+log is restored at PR-8 once the SPEECH/audio output lands. The OM injection
  is object-only (duck-typed), so the import-linter hexagon (no core/components→outputs) stays intact. Verified
  end-to-end on real subprocess boots — `test_cli_headless_boots_and_responds` (CLI renders via the wired shared OM)
  and `test_set_timer_end_to_end` (F&F path with OM wired) both green. Gates: `pyright` 0, import-linter 9/9,
  dep-validator 55/55, `check_scope` clean, full suite 83-failed=baseline (**0 regressions**, stash-diff confirmed).
  **Remaining = PR-5b** (daemon consume loop + runners-as-presets + PR-0 stopgap removal + meta-commands D-4).
- **ARCH-15 PR-4 DONE — F&F/deferred notifications re-routed through the OutputManager, addressed by identity.**
  `NotificationService` demoted deliverer→producer: `set_output_manager(om)` wires it, and `_deliver_notification`
  then delivers the completion through the OutputManager as a conversational `IntentResult`, **addressed by the
  action's identity** — `source` (channel) + `physical_id`/`room` now threaded from the `ActionRecord` onto the
  `NotificationMessage` (the carried-but-unused identity the investigation flagged, now *used*). The legacy global
  TTS/audio sink is bypassed when the OutputManager is present; `LOG` always runs; if the identity has no attached
  output → **drop + log** (D-3) — the completion stays queryable via the action-store history, so nothing is lost.
  Threading: wired the previously-**dead** `UnifiedConversationContext.request_source` from `RequestContext.source`
  (`context.py`), added `ActionRecord.source`, and a keyword-only `source` on the F&F launch
  (`execute_fire_and_forget_action`), captured from `context.request_source`. The immediate **ack** half is already
  PR-3 (sync return rendered via the output hexagon). **Opt-in / pre-daemon:** `output_manager` stays `None` until
  the composition root injects a process-wide OutputManager into NotificationService (PR-5) — so runtime behaviour
  is unchanged until then; legacy TTS+LOG remains the fallback. The D-3 **bounded reconnect** targets persistent
  transports (MQTT/WS) that arrive in PR-8; PR-4 ships drop+log+history. `core` keeps no import edge to
  `irene.outputs` (OutputManager duck-typed `Any`). New `test_notification_output_routing.py` (5): origin delivery,
  drop-on-unreachable, speech→text degrade, legacy-LOG back-compat, addressing-threading. **Side effect:** wiring
  `request_source` recovered a baseline drift test (`test_phase1_integration::...request_context_to_conversation_
  context_flow`) — backend baseline 84→**83 failed**. Gates: `pyright` 0, import-linter 9/9, dep-validator 55/55,
  `check_scope` clean, full suite 83-failed (0 regressions, 1 recovery, +5 new passing; timer e2e green).
- **ARCH-15 PR-3 DONE — real text outputs + origin routing; the CLI renders through the output hexagon.**
  New adapters `irene/outputs/console.py` (`ConsoleOutput` — CLI sink, injectable sink, origin=`cli`, TEXT-only)
  and `irene/outputs/text.py` (`CallbackTextOutput` — ws/web text via an async send callback; live consumer is
  the PR-6 remote attach). `RequestContext.source` repurposed from the format-ish `"text"` to the **channel**
  (`process_text_input` now takes it from `client_context["source"]`, default `"text"`) — safe because PR-1 moved
  the format onto `input_format`, and `source` was read only in 3 debug logs. The CLI runner renders results
  through `OutputManager`+`ConsoleOutput` (origin-paired to `cli`) instead of bare prints, via a new
  `InteractiveRunnerMixin._render_result` (print fallback when no manager wired; quiet still suppresses) —
  superseded by PR-5 (daemon-owned delivery with the real request context). **Reconciliation:** sync delivery
  pairs on the *live channel* (`source`), not `resolve_physical_id` — that keys the *persistent-identity*
  addressing of **deferred** F&F (PR-4). **Also (user directive): removed all `TYPE_CHECKING`** from the PR-2/PR-3
  output modules (`core/interfaces/output.py`, `outputs/manager.py`, `console.py`, `text.py`) — direct runtime
  imports of `IntentResult`/`RequestContext`, mirroring `core/interfaces/input.py` (verified cycle-free). Updated
  the `test_smoke_e2e` CLI assertion (the single-command prefix unified `"📝 Response: "`→`"📝 "`; now asserts the
  render marker + success line). New tests: `test_output_text_adapters.py` (4), `test_cli_render.py` (4).
  Gates: `pyright` 0, import-linter 9/9, dep-validator 55/55, `check_scope` clean, backend suite 84-failed=baseline
  (0 net regression, +8 new passing; smoke e2e green). Backend-only; config-ui surface lands PR-7.
- **ARCH-15 PR-2 DONE — output hexagon core: `OutputPort` + `OutputManager` + pipeline event bus (adapter-free).**
  The missing symmetric half of the input port. New `core/interfaces/output.py`: `OutputPort` ABC (mirrors `InputPort`,
  off `EntryPointMetadata`, import-thin via TYPE_CHECKING), `OutputModality{TEXT,SPEECH,DEVICE_COMMAND,EVENT}`,
  `DeliveryResult` (trivial ack/nack for terminal channels; **rich `echoed_value`/`error_code` for the bridge actuation
  channel**, D-6/§3.2), and the pure `negotiate()` §3.1 matrix (carry / degrade speech→text / drop). New
  `core/event_bus.py`: the canonical `EventType` vocabulary (`input.received`/`asr.transcript`/`intent.recognized`/
  `result.produced`/`output.delivered`/`error`, §5), `PipelineEvent` (carries origin identity), and `EventBus` async
  pub/sub with `identity_filter` (room/client/session/source/type) + **subscriber-failure isolation** (one bad observer
  never breaks delivery/pipeline). New `irene/outputs/` delivery layer + `OutputManager`: registry/lifecycle + **D-2
  modality routing** (conversational TEXT/SPEECH → origin-paired single; DEVICE_COMMAND/EVENT → capability-routed
  designated single, no fan-out → no double-actuation; +explicit broadcast escape hatch) + §3.1 negotiation +
  optional `output.delivered` emission. `irene.outputs` registered in the hexagon import-linter contracts
  (ARCH-1/2/3/11/12) symmetrically to `irene.inputs`. Adapter-free (PR-2 scope) — exercised by fakes:
  `test_output_port.py`/`test_event_bus.py`/`test_output_manager.py` (18). Workflow wiring + real text adapters = PR-3.
  Gates: `pyright` 0, import-linter 9/9, dep-validator 55/55, `check_scope` clean, backend suite 84-failed=baseline
  (0 net regression, +18 new passing). Backend-only; config-ui surface (`[outputs]` editor) lands in PR-7.
- **ARCH-15 PR-1 DONE — input `format` is first-class (`InputFormat` enum), driving the pipeline-entry stage.**
  Added `InputFormat{VOICE,AUDIO,TEXT}` (`intents/context_models.py`, D-1) — each value names its workflow entry
  stage (VOICE→voice-trigger, AUDIO→ASR, TEXT→NLU). It is now the single source of truth on
  `RequestContext.input_format`; the legacy `(skip_wake_word, skip_asr)` flags are its derived projection (clean
  bijection VOICE=(F,F)/AUDIO=(T,F)/TEXT=(T,T), with back-compat inference so callers still passing the flags keep
  working). `Workflow.configure_pipeline_stages` now selects stages from `input_format` (equivalent to — and
  replacing — the prior `skip_wake_word`/`source=="text"`/`skip_asr` checks); `process_text_input` passes
  `input_format=TEXT` instead of two hand-set booleans. **Reconciliation (Invariant #8):** the brief said
  `InputData.format`, but `InputData` is a *type alias* `Union[str, AudioData]` (`core/interfaces/input.py:23`),
  not a class — so format landed on `RequestContext`; stamping it on the input *envelope* is deferred to PR-5
  (daemon path). New `irene/tests/test_input_format.py` (17): the bijection, RequestContext source-of-truth +
  back-compat inference, and a `configure_pipeline_stages` equivalence test vs the exact pre-refactor logic.
  Behaviour-preserving. Gates: `pyright` 0, import-linter 9/9, dep-validator 55/55, `check_scope` clean, backend
  suite 84-failed=baseline (0 net regression, +17 new passing). Backend-only; no config-ui surface.
- **ARCH-15 PR-0 DONE — CLI double-reader stopgap; interactive CLI no longer swallows typed lines.** `InputManager`
  auto-started the `cli` source (`_auto_start_configured_sources`), spawning `CLIInput._input_loop` — a second
  `prompt_toolkit.prompt()` reader on the same TTY whose `_command_queue` nothing drains (`get_next_input` has no live
  consumer) — while the interactive runner (`InteractiveRunnerMixin._run_interactive_loop`) ran its *own* reader and called
  `process_text_input`. The two raced; lines won by `CLIInput` were silently dropped (zero pipeline logs). Fix: stop
  auto-starting `cli` (the source stays registered in `_sources`, just not started), mirroring the existing `web`
  "don't auto-start to avoid conflicts" guard (`inputs/manager.py:128-129`) — safe because nothing consumes the InputManager
  cli stream in any live profile. The runner's loop is now the sole stdin owner. New
  `irene/tests/test_input_manager_autostart.py` (2): cli is registered-but-not-active, and no `CLIInput` read loop / listen
  task is spawned. Design-compatible stopgap (ARCH-15 PR-5 makes the double-reader structurally impossible by making the
  console adapter the single daemon-consumed reader). Gates: `pyright` 0, import-linter 9/9, dep-validator 55/55, `check_scope`
  clean, backend suite 84-failed=baseline (0 net regression, +2 new passing). Backend-only; no config-ui surface.
- **ARCH-14 DESIGN — symmetric, configurable, hexagonal I/O architecture (design session with user).** A CLI bug
  (`irene.runners.cli` interactive silently swallows typed lines — two `prompt_toolkit.prompt()` readers racing one TTY:
  the runner's `_run_interactive_loop` vs the auto-started `CLIInput._input_loop` whose `_command_queue` nobody drains)
  surfaced three structural gaps confirmed by a full code+ledger+docs investigation (5 parallel research agents): input
  consumption is ad-hoc per-runner (the `architecture.md` §5.1 "Command Queue" is dead-by-decision, Q4/P0-8; every runner
  bypasses `InputManager`); there is **no output abstraction** (`irene/outputs/` absent; async/F&F output hard-wires the
  one global TTS/audio sink); and the system assumes one-input-one-output (mutually-exclusive runners). Along the way the
  investigation **corrected two stale beliefs**: F&F/notifications are **live** (QUAL-28+QUAL-9, not the dead state the
  frozen QUAL-8 review describes), and a **physical-identity model already exists** (`resolve_physical_id` + `ClientRegistry`
  action store, Model 2 / QUAL-28) — the exact addressing spine the new design needs. Deliverable
  `docs/design/io_architecture.md` (DRAFT) consolidates the user's 5-point brief: format-vs-input axes; output as the
  configurable symmetric twin with a modality/capability matrix; one daemon multiplexing many concurrent inputs+outputs
  with runtime attach/detach; one pipeline event bus with delivery + observation (tap) subscribers; F&F ack+notification
  routed through OutputManager (deferred → persistent physical identity); runners demoted to thin config-preset launchers
  (making the double-reader bug structurally impossible). The earlier A/B "who owns input consumption" framing is
  superseded — both options were too narrow. Implementation = **ARCH-15** (PR-0..8): PR-0 is a design-compatible CLI
  stopgap that unblocks interactive CLI now; PR-1/PR-2 (format-first-class, OutputPort+bus) can begin immediately; config-ui
  gets a new `[outputs]` editor (PR-7). **Decisions D-1..D-6 walked through and LOCKED** in the same session (§10):
  3-value format enum; modality-routed output (+broadcast escape hatch); drop+log+history with bounded reconnect;
  meta-commands → existing `system.*` intents (delete REPL interception); authenticated-WS tap (shared-token, localhost-first);
  and the load-bearing one — **D-6: MQTT/bridge actuation is just another output channel** (`OutputPort.deliver()->DeliveryResult`,
  rich echo for the bridge with bounded await; `ActuationPort`→bridge `OutputPort`; `DeviceCatalogPort` stays a read port),
  which corrected an earlier "actuation is a separate synchronous port" framing and unified ARCH-8 under ARCH-15's OutputPort.
  Added **PR-9** (runs last): explicitly revisit ARCH-7 to adjust the MQTT design to this architecture, then sweep all other
  unfinished ARCH/QUAL items for impact and adjust. ARCH-14 (design) flipped `[x]`; ARCH-15 (impl, PR-0..9) filed open.
- **UI-9 DONE — free-form dict config fields render an editable key/value table instead of a dead-end warning.**
  Reported from the live UI: `Intent System → domain_priorities*` (and other places) showed "⚠️ Объектное поле должно
  отображаться как сворачиваемый раздел (проблема ConfigSection)" instead of an editor. Traced end-to-end: the schema
  generator maps any `Dict[str, X]` field to `type: "object"` (`config/auto_registry.py:329`) but only attaches
  `properties` for nested **Pydantic models** (`_extract_nested_object_schema`), so a free-form map like
  `domain_priorities` (`Dict[str, int]`, `intents/orchestrator.py:20`) arrives as `type: "object"` with **no
  `properties`**. config-ui's `ConfigSection` only promotes an object to a collapsible subsection when
  `type==='object' && properties` (`ConfigSection.tsx:262`); lacking `properties` the field fell through to
  `ConfigWidget`'s `case 'object'`, whose only job was the yellow `objectFieldWarning` placeholder — so **every**
  free-form map field showed the warning, which is why it appeared in multiple places. **Fix (config-ui only, no
  backend/contract change):** `ConfigWidget`'s `case 'object'` now branches on `schema.properties` — absent → render
  the already-present `KeyValueEditor` (add/rename/delete with value coercion); present → keep the warning, since a
  *fixed-shape* object reaching the widget factory is a genuine upstream routing bug worth surfacing. One touch point
  suffices because both render paths (`renderField` for simple fields, and direct widget calls) funnel through
  `ConfigWidget`. Note: `KeyValueEditor` is the surviving generic map editor — UI-8 deleted `KeyValueOfStringArray`,
  a different string-array variant. Gates: `cd config-ui && npm run check` (type-check + lint 0-warn + orphan guard) +
  `npm run build` green. (Backend untouched; no pyright/import-contract surface.)
- **QUAL-40 DONE — generated-TOML section headers no longer dropped.** `ConfigManager._generate_provider_sections` /
  `_generate_normalizer_sections` (`config/manager.py`) assigned a `[base_path.<name>]` header per provider/normalizer
  but never appended it; the closing `"\n".join([section] + sections)` kept only the **last** header (placed at the top),
  so the generated TOML collapsed every entry's keys under a single section — silently corrupt config output. Fixed by
  appending the header at the start of each iteration and joining plainly (removed the `[section] +` prepend and the dead
  `section = ""` init that QUAL-4e had added only to clear the type error). Backend-only generated-*content* fix — no
  endpoint/schema/type change — so the config-ui TOML-editor surface simply gets correct TOML (no config-ui change). New
  `irene/tests/test_config_section_generation.py` (3) guards it: asserts every header survives and the output re-parses
  via `tomllib` back to the original `{name: {...}}` nesting (this round-trip assertion fails on the pre-fix code, where
  all keys collapse under the one surviving header). Gates: `uv run pyright` 0, import-contracts 9/9, dependency-validator
  55/55 (0 errors), `check_scope` clean, backend suite 84-failed=baseline (0 net regression, +3 new passing).
- **QUAL-41 DONE — asset validators now match `api.schemas.ValidationError` (no more 500 on a real validation error).**
  `validate_template_data`/`validate_prompt_data`/`validate_localization_data` (`core/intent_asset_loader.py`) emitted
  `{field, message, severity}`, but the schema requires `{type, message}` (+ optional `path`/`line`), so
  `ValidationError(**err)` in `intent_component.py`'s template/prompt/localization editing endpoints raised a pydantic
  error → HTTP 500 the moment a real template/prompt/localization validation failure occurred. Of the two fix options the
  ledger offered (boundary mapper vs align-to-schema), chose **align-to-schema** because the **sibling validators
  `validate_phrasing_data`/`validate_contract_data` already emit the canonical `{type, message, path}`** — so this makes
  all of `intent_asset_loader`'s validators consistent rather than papering over one cluster at the boundary. Mapping:
  `field`→`path`; dropped `severity` (redundant — the errors-vs-warnings list already encodes it); added a `type` category
  (`structure`/`missing_field`/`value`/`validation`). Verified no consumer read the old keys (all 9 endpoint sites only
  `ValidationError(**err)`/`ValidationWarning(**warn)`; no tests). **Invariant #4 (config-ui):** the template/prompt
  editors already read `.message` via `any` casts (TemplatesPage/PromptsPage), so they render correctly with no change;
  `npm run check` + `npm run build` stay green. New `irene/tests/test_asset_validation_schema.py` (3) reproduces the old
  500 by constructing the API schema models from each validator's *failing-input* output. Gates: `uv run pyright` 0,
  import-contracts 9/9, dependency-validator 55/55 (0 errors), `check_scope` clean, backend suite 84-failed=baseline
  (0 net regression, +3 new passing). **Also fixed (user-directed, folded into the same change):**
  `config-ui DonationsPage.tsx:859` read `err.msg` from the **phrasing** validation response while `validate_phrasing_data`
  emits `message` — a pre-existing latent display bug on the UI-5/QUAL-29 donation surface (the adjacent warnings map at
  :860 already read `.message`); changed `err.msg`→`err.message`, config-ui `npm run check` + `build` green.
- **UI-7 DONE — config-ui is now fully bilingual (ru + en).** Stood up `react-i18next` from scratch under `src/i18n/`
  (the bridge only *declared* `i18next ^23`/`react-i18next ^13`, never wired them) — namespaced TS bundles
  (`locales/{en,ru}/{common,layout,donations,configuration,prompts,templates,localizations,monitoring,overview}.ts`),
  a typed `t()` (CustomTypeOptions off the `en` bundle → mistyped keys/namespaces are compile errors + autocomplete),
  and a Header `LanguageSwitcher` (persists to localStorage; default `ru`, fallback `en`; keeps `<html lang>` in sync).
  **Completeness is compiler-enforced:** the RU bundle is typed `DeepStringify<typeof en>` (a structural "same keys,
  string leaves" map), so any missing/extra/misnested RU key fails `tsc` — the static half of "language files are
  complete". **Two orthogonal axes preserved:** UI-chrome language (switcher) vs donation *content* language
  (`LanguageTabs`). Retrofitted the whole UI via partitioned slices (chrome by hand; then shared/common, the donation
  editor track incl. the §3.2 no-jargon card vocabulary, configuration, the three list pages, and monitoring/overview)
  — disjoint files + one namespace each, so no slice collided. Card kind labels/help (`CardEditor`) moved off
  module-scope into `t()`-driven helpers so the friendly vocabulary localizes. Hardened the orphan guard in passing
  (now follows side-effect imports `import './i18n'`, exempts `*.d.ts`). Technical identifiers (model/service names,
  slot labels, spaCy attrs, intent/method names, code) kept verbatim per the donation-localization rule. Conventions
  captured in `config-ui/docs/i18n_retrofit_spec.md`. `npm run check` + `npm run build` + `npm test` 40/40 all green.

### 2026-06-06
- **UI-3 DONE — card-based pattern editors (on UI-2) + test-against-text.** Built `CardEditor` (5 friendly card kinds
  + per-card raw-spaCy "Advanced" escape hatch via SpacyAttributeEditor + "include its forms"/optional/repeat),
  `CardPatternsEditor` (replaces the raw TokenPatternsEditor; controlled over SpacyPattern[] but holds decompiled
  cards in local state, compiling only on edits so the advanced raw stays stable and revert re-syncs),
  `SlotCardPatternsEditor` (replaces SlotPatternsEditor), and `PatternTester` (UI-1 §6 — sample text → the real
  `POST /nlu/recognize`, showing the recognized intent + filled values + match badge). Rewired the phrasing method
  editor to the cards ("What might the user say?" / "How to find each value" / "Does this work?"); deleted the raw
  Token/Slot editors and the v1.0 lemma↔token-pattern auto-sync (the per-card forms toggle replaces it). **§3.4 polish
  folded in** (user-requested): `ExtractionFillersEditor` edits each contract parameter's extraction_patterns as
  labelled card rows grouped under the param (+ choice_surfaces for choice/entity), on the UI-2 FillerPattern helpers
  — closing the per-param extraction surface un-editable since UI-5; method-level slot_patterns kept as "Shared value
  slots". npm test 40/40, check + build green.
- **UI-2 DONE — the frontend-only pattern translation engine `patternModel.ts`.** decompile/compile between raw spaCy
  token dicts and the human card model (word/one-of/number/any-word/the-rest/advanced), with the §3.3 regex reductions
  and optional/repeat↔OP. Lossless by construction: each card preserves its source encoding (TEXT/LOWER/LEMMA, IN vs
  alternation-regex, LIKE_NUM vs digit-regex) and anything else is stored verbatim in an `advanced` card, so
  compile∘decompile is identity for every token. Proven by `patternModel.test.ts` (40 tests = unit cases locking the
  §3.2/§3.3 mapping + the required round-trip across all 28 real phrasing files + a >50%-friendly-coverage guard
  against a trivial all-advanced pass). Added vitest + a `test` script; updated the UI-8 orphan guard to treat test
  files as entry points (a tested module is intentional, not dead) — which also keeps patternModel.ts non-orphan
  until UI-3 consumes it. `npm test` 40/40, `npm run check` + `build` green.
- **UI-8 DONE — config-ui orphan sweep + a reachability guard.** Deleted 5 unreachable modules (3 editor components,
  `testWorkflow.ts`, and the borderline `spacyAttributes.ts` — a 392-line catalog nothing imports; the live advanced
  editor uses `spacyAttributeHelpers.ts` instead, and UI-3's vocabulary is survey-grounded). Added
  `scripts/find-orphans.mjs` + wired `check:orphans` into `npm run check` so dead modules can't reaccumulate (the root
  cause: `--max-warnings 0` can't see unused exports). `npm run check` + `build` green.
- **QUAL-43 DONE — removed donation v1.0 dead validation code + repointed the build analyzer at v1.1 (user-directed).**
  Verified each target was genuinely dead before deleting (0 callers): the `IntentAssetLoader` v1.0 schema-validation
  chain (`load_donation_on_demand`/`_load_and_validate_donation`/`_validate_json_schema`/`validate_donation_data`),
  `irene/tools/intent_validator.py` + its CLI script + `assets/v1.0.json`, the orphaned
  `sync_parameters_across_languages` (+ its now-dead confidence/lang-detect helpers + `TranslationSuggestions`), and
  the rule-based `suggest_translations` endpoint/method + 6 dead schemas. **Mid-task the user added: "build analyser
  should use new v1.1 validations"** — so instead of deleting build_analyzer's intent-JSON check, rewrote it to
  validate each enabled handler's v1.1 `contract.json` + `<lang>.json` against the two v1.1 JSON Schemas via
  jsonschema. This also fixed a latent bug: the old check pointed at the non-existent v1.0 monolithic
  `assets/donations/<h>.json`, so under v1.1 it would have emitted false "file not found" build errors. Regenerated
  the committed `openapi.json` (109→108 paths) + frontend types. Gates: pyright 0, import-contracts 9/9,
  dep-validator 55/55, backend suite 84=baseline, config-ui check+build green. (Answered a user question: no v1.0
  schema file is needed anymore — only the two v1.1 schemas remain.)
- **UI-5 DONE — rebuilt the donations editor on the v1.1 split (config-ui), QUAL-42 validations wired, v1.0 cruft out.**
  Six green slices, each committed at a passing `npm run check && npm run build`: (0) type-gen foundation — a backend
  `scripts/dump_openapi.py` produces a committed `config-ui/openapi.json` (assembled from the runner's router factory +
  component routers with `core=None`, since routes build independently of request-time state), and `gen:api-types`
  generates envelope types (openapi-typescript) + contract/phrasing body types (json-schema-to-typescript from the two
  v1.1 JSON Schemas); (1) apiClient → v1.1 contract get/put + the three QUAL-42 methods, dropping the dead
  `syncParameters`/`suggestTranslations`; (2) generated `donations.ts` types; (3) new ContractEditor (structural) +
  DonationValidationPanel (wiring report + LLM validate/draft); (4) ChoiceSurfacesEditor wired into phrasing; (5)
  dropped the parameter-sync UI from LanguageTabs + CrossLanguageValidation. **Verification answered a user question**
  (does the rest of config-ui work with the generated types?): whole-app build green; the dump covers all 52 endpoints
  the apiClient uses except the known-dead `sync-parameters` (expected) and a pre-existing stale
  `/intent_system/configure` client path (fixed in passing → `/intents/configure`). Deferred by design: raw pattern
  editors stay (cards = UI-3), chrome i18n = UI-7, backend v1.0 dead-validation removal = QUAL-43 (filed). Clears the
  Invariant #4 debt from QUAL-29.
- **QUAL-42 DONE — donation contract↔code validator + LLM translation services (user-directed, "do this validator
  right away").** Built on the donation-validation investigation, which found that nothing reconciled a *contract*
  against the *handler code* it drives (only contract→method existence; never params, never reverse coverage), the UI
  was display-only, and `sync-parameters` was a dead v1.0 call. **Severity split was the key design call:** parameter
  "wiring" can't be statically proven without false positives (params are read via `get_param` *and*
  `intent.entities`, sometimes in helpers, and some — e.g. a `language` global — are read from `context` and never
  named), so a literal "raise if a param isn't wired" would break boot on valid handlers. Resolution: **unwired
  *method* = FATAL (raises at startup); unread *param* / undeclared `_handle_*` = soft warning**, with a
  `strict_parameters` ratchet. Verified against the 14 real handlers: **0 fatal, 13 useful warnings** (boot green).
  New `core/contract_validator.py` (AST param-reference scan), startup fail-fast in `IntentAssetLoader`, and three
  endpoints on `intent_component` via the injected `LLMPort`: `GET /donations/validation` (startup wiring report →
  UI), `POST …/validate-translation` (LLM meaning/consistency QA), `POST …/translate` (LLM translation *service*,
  replacing the dead phrase-count suggester). **All LLM features degrade to `llm_available:false` + a "validate
  manually" message when no API-keyed provider exists** (deepseek default, else any supported provider with a key).
  Decision logged: LLM validation is on-demand (endpoint), not per-boot (token cost/fragility); structural wiring is
  the always-on startup half. 8 schemas, 7 tests (incl. an all-real-handlers 0-fatal guard), `donation_editor_ux.md`
  §9 updated. Gates: pyright 0, import-contracts 9/9, dep-validator 55/55, suite 84=baseline (+7 passing).
- **UI-1 DONE — designed the human-friendly donation editor → `config-ui/docs/donation_editor_ux.md`.** Started from a
  user question — must UI-1/2/3/5 be built together? — and a user correction (the ledger's "`ParameterSpecEditor` is
  already fine" is wrong: it embeds raw `extraction_patterns` + a regex `pattern`). Traced the code + a 28-file survey
  of real spaCy usage (vocabulary is small: TEXT/LEMMA/LOWER/IS_ALPHA/LIKE_NUM/IN/REGEX/`OP:"+"`; no NOT_IN/TAG/ENT_TYPE,
  no `?`/`*`/`!`). Key insight: **the v1.1 split IS the clean/spaCy line** — contract.json is structural/no-spaCy,
  `<lang>.json` holds 100% of the raw spaCy — so the redesign is **two editors** and the spaCy abstraction is
  quarantined to the phrasing side. **Persona-driven model** (knows handlers, zero spaCy/NLU): five everyday cards +
  an Advanced escape hatch, example-sentence language, regex hidden (mostly reduces to cards); the three pattern
  locations collapse to two questions. **User-settled decisions:** translation **frontend-only** (`patternModel.ts`,
  lossless round-trip, backend keeps validate+test-match); raw spaCy = **advanced escape hatch behind a button**;
  **structural-first phasing** (UI-5 builds the functional editor + all scaffolding once; UI-3 swaps in the cards — no
  double build). **User-directed scope addition → filed UI-7:** config-ui-wide **bilingual UI** via `react-i18next`
  (harmonized with the bridge per UI-6), keeping UI-language (chrome) orthogonal to content-language (which phrasing
  file). Ledger 90 tasks · 55 done · 33 open · 2 paused; scope guard clean.
- **QUAL-6 DONE — killed the startup "CoreConfig fields without section models" warning as a structural false
  positive (Invariant #8).** Reconciled against reality: the §H "9 fields" is now 11 (QUAL-36 added
  `default_language`/`supported_languages`), and crucially they are *all* scalar top-level settings — instance
  identity + runtime knobs, no nested structure. The warning was guaranteed by construction: `validate_schema_coverage`
  diffed the section-model registry against **every** `CoreConfig` field, but the registry only ever holds
  Pydantic-model fields, so each scalar was permanently "missing." Fix is a logic correction, not a config
  restructure: factored the "is this annotation a section model" predicate into a shared
  `AutoSchemaRegistry._resolve_section_model()` (direct BaseModel or `Optional[BaseModel]`) used by **both**
  `get_section_models` and the coverage check; the check now compares the registry against the actual *section*
  fields, so a non-empty diff means a genuine registration drop worth a warning. Documented inline in `CoreConfig`
  that the leading scalars are intentionally section-less. Chose this over grouping the scalars into a section model
  (would break TOML layout, `IRENE_*` env paths, and dozens of `config.debug`/`config.version`/… read sites — high
  risk for a P2 cosmetic warning). Verified: `validate_schema_coverage().warnings == []`, 16/16 sections still
  registered, full `uv run pyright` 0, `test_config_schemas`+`test_import_contracts` 14/14, dependency validator
  55/55, `check_scope` clean, suite 84=baseline.
- **Corrected the "выключи свет везде" model in `mqtt_integration.md` (user correction).** My prior reconciliation
  concluded Irene fans out (iterate all rooms → N per-device canonical calls + partial-failure speech) — **wrong.** The
  actual model: the **`global` room holds whole-house AGGREGATE devices** (e.g. `all_lights`) that wb-rules maps to the
  real per-light fan-out; "выключи свет везде" resolves to that aggregate device and fires **one** canonical command (a
  normal Actuate). Irene **never iterates rooms or synthesizes a group** — group/scene controls are aggregate *devices* in
  the catalog and Irene relies on their availability. Simpler on Irene's side (no fan-out, no N-call partial-failure
  handling; PR-5 reduces to just the sensor-read flow). Updated `mqtt_integration.md` §5a/§6/§10/§11 + the ARCH-7/8 ledger
  lines, **and aligned the bridge contract** `voice_integration_contract_draft.md` (§B catalog example now shows an
  `all_lights` aggregate device in `global`; §B/§C.5 prose, sequencing, and deferred-v2 all rewritten to the
  aggregate-device model — no more "Irene iterates rooms"/"N parallel calls").
- **QUAL-5 DONE — cruft cleanup (verifiable cruft → 0; vulture pool not pursued, user decision).** Reconciled the §G
  counts against post-QUAL-4 reality (import churn dropped them: F401 360→237, star 62→5+57 F405, F841 22→15). Cleared all
  of it: 189 unused imports ruff-auto-fixed; the 41 unsafe-to-autofix tail classified by one verified sub-agent — pure
  optional-dep availability probes converted to `importlib.util.find_spec` (6), side-effecting probes kept with a
  documented `# noqa: F401  # availability probe` (~14), genuine leftover symbols deleted; the 5 star-imports in
  `api/__init__.py`/`utils/__init__.py` replaced with explicit re-export lists (public `__all__`s now authoritative); 15
  unused vars removed (side-effecting RHS preserved as bare calls). The `uv run pyright` gate (0) was the safety net for
  the import removals (a wrongly-removed still-used import surfaces as an undefined name); verified ruff-clean, pyright 0,
  package imports OK, 9/9 contracts, suite 84=baseline. **Vulture:** ran it (753 candidates @ conf 60) and confirmed it's
  false-positive-dominated — it flags live entry-point components (`ConfigurationComponent`) and FastAPI `response_model`
  Pydantic schemas as "unused". Per the user, NOT pursued: a bulk removal would break dynamically-loaded code, the signal
  is near-zero, and genuine dead code was already removed in ARCH-13/QUAL-21/QUAL-24/QUAL-34. Rationale recorded in the
  ledger.
- **Reconciled `mqtt_integration.md` (ARCH-7) to a bridge-side contract tightening (Invariant #5/#8).** The bridge's
  `voice_integration_contract_draft.md` was updated after the AGREED snapshot, with two changes that affect Irene's side:
  **(1) one device / one room** — the catalog device shape changed from `rooms: [...]` (multi) to `room: Optional[str]`
  (single); **(2) `global` semantics** — it's no longer an *opt-in tag* for "выключи всё" but a regular room for genuinely
  whole-house controls only, so **"выключи свет везде" is now Irene's job** (iterate *all* rooms, fire the capability
  per-device), not a `global`-membership lookup. Updated `mqtt_integration.md` §5a (catalog example + bullet), §6 (the
  "everywhere" fan-out), §10 (PR-5), §11 (resolved summary) + the ARCH-7 ledger line. (Bridge-side-only refinements not
  affecting Irene: per-control `…/meta/error` topics with `r`/`w`/`p` codes; `config/devices/wb-devices/<room>/` layout.)
  No code impact (ARCH-8 not started); design stays consistent for when it is.
- **Filed QUAL-40 + QUAL-41 — the two real logic bugs QUAL-4e surfaced (Invariant #6: findings → ledger IDs).** QUAL-40:
  `ConfigManager._generate_*_sections` drop all but the last section header in generated TOML (4e fixed only the type
  error). QUAL-41: the `IntentAssetLoader` validators emit `{field,message,severity}` but `api.schemas.ValidationError`
  needs `{type,message}` → 500 on a real template/prompt/localization validation error (4e widened the annotation only).
  Both `[release]` P2.
- **QUAL-4 COMPLETE — `uv run pyright` at 0 errors, full standard mode, empty suppression list (762 → 0).** 4e (the
  type-tail, 261) closed the ratchet. **`api/schemas.py` (71):** Pydantic v1-isms with clean v2 fixes — 66
  `Field(example=…)` → `json_schema_extra={"example": …}` (batched via a script, then hand-fixed one multi-line list the
  regex mangled + 2 inline ones); a `default_factory=PerformanceMetrics` that would crash (`PerformanceMetrics()` needs
  required fields) → made the field required; 4 subclass `timestamp` overrides given the base `default_factory=time.time`.
  **The 190-file tail** was cleared by 6 parallel sub-agents (grouped runners/utils/core/components/intents/analysis-providers-config)
  under a strict spec (no `type:ignore`/`assert`/`TYPE_CHECKING`, no new cross-layer imports, don't break the enforced
  4b/4c/4d, flag real bugs) + central verification. Most were `param: T = None` → `Optional[T]`, untyped-third-party
  `cast`s (sounddevice `DeviceList|dict`, pyttsx3, spaCy), and possibly-unbound inits. **Genuine bugs found & fixed:** a
  microWakeWord `WakeWordResult(metadata=…)` TypeError swallowed by `except` as not-detected (added the `metadata` field);
  `await core.component_manager.get_available_components()` on a SYNC method (would TypeError on `/system/capabilities`);
  `min_items`→`min_length` (invalid v2 kwarg); `callable` used as a type annotation ×3 in `orchestrator`; a `WorkflowPort`
  missing the `trace_context` param (contract drift). **Flagged for follow-up (type-fixed, deeper logic bug deferred):**
  `config/manager.py` `_generate_provider_sections`/`_generate_normalizer_sections` drop all but the last section header in
  generated TOML; the `intent_asset_loader` validators emit `{field,message,severity}` dicts but `api.schemas.ValidationError`
  requires `{type,message,path}` → would 500 on a real template/prompt/localization validation error. **Verified:**
  `uv run pyright` 0 (full standard, all rules enforced) · 9/9 import contracts (new imports all inward) · validator 55/55 ·
  suite 84=baseline. **QUAL-4 done across 4a–4e: 762 type errors eliminated, ~25+ latent bugs fixed along the way; the
  release "pyright standard under threshold" exit-criterion is met (threshold = 0).**
- **QUAL-4d DONE — Cluster A port-hierarchy harmonization; all 87 override-incompat errors cleared, rules enabled.**
  Per the user's decisions: **`is_available` → async everywhere** (capability ports + inputs web/cli/microphone +
  `tts_component` made `async` to match the already-async `Component.base`; the `await` cascade propagated through
  `inputs/manager.py`'s `get_available_sources`/`get_source_info` — both zero-caller, so no further ripple); **`name` →
  read-only `@property`** on `WebAPIPlugin`/`ComponentPort` (all 11 components already implement it; removed the now-dead
  dynamic `self.name` assignment in `Component.__init__`); `set_default_provider` base/port param `name`→`provider_name`;
  `default_provider`→`Optional[str]`; `get_status`→async; `extract_*` port params aligned; `get_component` fixed by making
  `ComponentPort` extend `ComponentControlPort` (an inward core→intents edge, **import-linter-permitted — contracts stay
  9/9**); `process_audio_stream` async-gen stub; `get_config_schema` aligned to the inherited classmethod (had no callers).
  **Self-caught regression:** my first `initialize` fix added an untyped `(self, core=None)` to the 9 components, which
  made pyright infer `core: None` → **20 new `reportOptionalMemberAccess`** on `core.config` — and I committed it (37f245a)
  **without running the full `uv run pyright` gate** (only the 4d measurement + suite). Caught it during the central
  verification of this slice; fixed by making `initialize` **required** on `Component.base` + `ComponentPort` and reverting
  the impls to `(self, core)` (untyped → Any → no None-inference; voice_trigger/nlu_analysis keep their *guarded* `=None`).
  Lesson: run the full enforced-gate after every slice, not just the slice's own rule. Execution: I did the architectural
  analysis + the regression fix; one focused sub-agent did the mechanical harmonization under that plan, verified centrally
  (gate 0 with 4b+4c+4d enforced, 4d 0, 9/9 contracts, validator 55/55, suite 84=baseline). **QUAL-4: 4a/4b/4c/4d all
  done (488 errors fixed across the four rules); only 4e (the type-tail) remains.**
- **QUAL-3 DONE — Category D entry-point metadata wiring; validator 55/55.** Reconciled first (Invariant #8): the
  entry-point total is **55, not §D's 58** (the `settings` runner was removed in QUAL-21), and the live validator was
  50/55 with 11 errors — same two defect classes as §D. **(a)** `MonitoringComponent`/`ConfigurationComponent`
  `get_python_dependencies` were unbound **instance** methods (failed when the validator calls them unbound) → converted
  to `@classmethod` to match the `EntryPointMetadata` `@classmethod @abstractmethod` contract; this also cleared 4 of the
  QUAL-4d Cluster-A override-incompat errors (a deliberate synergy — these were the same defect viewed two ways). **(b)**
  the `cli`/`vosk`/`webapi` runners lacked the entry-point metadata methods → added `@classmethod`
  `get_python_dependencies`/`get_platform_dependencies`/`get_platform_support` to their shared `BaseRunner` (runners
  coordinate components, so they declare no Python deps of their own by default; one edit cascades to all three).
  Done-criterion met: `irene-dependency-validate --validate-all` = **55/55, 0 errors**. Verified 9/9 import contracts kept,
  suite 84=baseline. The non-QUAL-3 remainder of 4d Cluster A (39: `name`/`is_available`/`initialize`/
  `set_default_provider` port-signature alignments) is next.
- **QUAL-4d PARTIAL (Cluster B+C done); Cluster A paused to do QUAL-3 first (user decision).** Triaged the 87
  override-incompat errors into three clusters. **C (40, `api/schemas.py`):** Pydantic field/Config narrowing
  (`success: Literal[False]`, discriminator `type`, inner `class Config`) is by-design and pyright's invariant-class-var
  rule is a false-positive for it; per the user, scoped-off with a documented file-level
  `# pyright: reportIncompatibleVariableOverride=false` in that module ONLY (enforced everywhere else; no wire change →
  config-ui unaffected). **B (4, ASR `transcribe_stream`):** the abstract base was `async def` (coroutine type) while all
  4 impls are async generators → made the base a plain `def … -> AsyncIterator[str]` (async generators are covariant
  AsyncIterator overrides). **A (43, remaining):** component↔port signature divergences (`name` @property vs
  `WebAPIPlugin.name: str`; `is_available` async on `Component` vs sync on the capability ports; `initialize` default
  dropped; `set_default_provider`; `get_python_dependencies`). **Key finding:** Cluster A overlaps **QUAL-3** — the
  `get_python_dependencies overrides Component/EntryPointMetadata` errors on Monitoring/Configuration ARE QUAL-3's
  unbound-instance-method defect. User chose to do QUAL-3 first, then align the rest of the port hierarchy on top. 4d rules
  not yet enabled. Verified B+C: schemas + ASR transcribe_stream cleared (43 left, all Cluster A); suite 84=baseline.
- **QUAL-4c DONE — 163 `reportAttributeAccessIssue` (phantom-attribute) errors cleared; rule enabled. ~15 were genuine
  latent bugs.** This slice paid for itself in real fixes, not just annotations: `voice_trigger_component._resampling_metrics`
  was never initialized (Phase-1 migration dropped the init, kept the `+=` usages → first resample raised
  AttributeError swallowed as a "resampling failure"); `monitoring_component` read non-existent `DomainMetrics.success_rate`
  / `.avg_duration` (added a `success_rate` property, fixed to `average_duration`); `nlu_component`'s language-confidence
  loop accessed `.text` on history dicts with the wrong key (dead code → `entry.get("user_text")`); `config/models.py` had a
  function-local `logger` shadowing the module logger (UnboundLocalError on the orphaned-config warning path); `audio_processor`
  wrote to a read-only `VADConfig.threshold` property (→ `energy_threshold`) and called `calibrate_threshold` missing on the
  silero VAD engine (added a no-op to the `VADEngine` ABC); `config/validator.py` checked removed `SystemConfig.metrics_*`
  fields + a non-existent `_calculate_counts()`; the openai/anthropic providers crashed on non-text SDK content blocks
  (now narrow via `output_text`/`isinstance(TextBlock)` → "" for thinking/tool blocks). Type-only fixes: `datetime`
  return annotation (29); `DomainMetrics` 6 lazily-seeded sub-metric fields declared with the `hasattr`→truthiness
  seed-guard flip (13 — caught & prevented a KeyError regression on the read-side session guards); `InteractiveRunnerMixin`
  mixin-attr annotations (10, which exposed 4 `self.core` None-accesses I then guarded to keep 4b at 0);
  `TextProcessingRequest.context` field (9). **Hexagon (user flagged again mid-work):** verified 9/9 import-linter
  contracts kept; the `.core`/`self.core` phantoms were fixed WITHOUT re-introducing `self.core` or importing core (config
  captured at `initialize()`); a port was widened only where it's a genuine shared contract (`WebAPIPlugin.name`, mirroring
  ComponentPort/WorkflowPort); every new import is inward (components→config/providers, core→intents-domain, runners→core).
  Work split: in-file fixes for the architectural/bug clusters (datetime, metrics, mixin, resampling, schema) + 5 verified
  sub-agents for the tail, with central verification (both rules 0 repo-wide, contracts 9/9, suite 84=baseline). Remaining:
  4d (override-incompat 76) · 4e (tail + mypy disposition).
- **QUAL-4b DONE — 238 `reportOptionalMemberAccess` (None-deref) errors cleared; rule enabled (ratchet up).** Biggest
  lever was the `intent_component.py` hotspot (91, 38% of 4b): a single typed `_require_asset_loader()` helper folding the
  two-Optional guard (`handler_manager` + its `_asset_loader`) into one accessor took it 91→2 (the `.config` accesses
  resolved for free once `asset_loader` was non-Optional); two stragglers guarded individually. The remaining 147 across
  35 files were fixed by 5 parallel sub-agents (grouped by layer), each driving its files to 0 under a strict spec
  (explicit None-guards matching each file's idiom — handlers degrade gracefully, required deps fail-loud via the file's
  own exception type, lazy optional-dep handles restored to their declared `Any`; no `type: ignore`/`assert`/
  `TYPE_CHECKING`), verified centrally. **Hexagon respected (user flagged mid-work):** ran the import-linter contract test
  → 9/9 kept; diff scan → domain (`intents/handlers,manager,orchestrator`) and `utils/vad_silero` gained ZERO outward
  imports (guards are None-checks + builtins + `Any`); the only new intra-irene import is
  `intent_component→core.intent_asset_loader` (allowed components→core direction). Verified end-to-end: 0
  `reportOptionalMemberAccess` repo-wide, `uv run pyright` green with the rule now enforced, full suite **84 failed**
  (≤ 85 baseline, no behavior regression). Reviewed the agent-flagged behavior changes (openai/deepseek `content or ""`,
  best-effort notification early-return, nlu-analysis config-default) — all defensible/graceful. Remaining: 4c (phantom
  attrs 164) · 4d (override-incompat 76) · 4e (tail + mypy disposition).
- **QUAL-4 reconciled + subdivided; 4a (the standard-mode type gate) DONE.** Reconciled the §E baseline against current
  reality (Invariant #8(b)): measured standard-mode pyright at **762 errors / 172 files** (pyright 1.1.410, venv-resolved,
  tests excluded) — down from §E's 1,107, the ARCH/QUAL refactors having fixed ~31% incidentally. (First measured 540 with
  the venv mis-wired — `pythonPath` is not a pyright setting; unresolved third-party imports were *masking*
  `reportArgumentType`/`reportCallIssue`; `venvPath`+`venv` gave the true 762.) **User decisions:** subdivide **by rule**
  with a **ratchet** (each slice enables its rule in `pyrightconfig.json` so it can't regress), target **zero at standard
  mode** (not a numeric threshold). **4a landed:** rewrote `pyrightconfig.json` → `typeCheckingMode=standard` + venv-wired
  + the 20 currently-erroring rules suppressed so the gate is **green at 0** (the floor every later slice ratchets up from);
  fixed one wrong rule key (`reportPossiblyUnbound`→`reportPossiblyUnboundVariable`, was silently unrecognized); pinned
  `pyright==1.1.410` in the `dev` extra (diagnostics are version-sensitive); removed the duplicate `[tool.pyright]` block
  from `pyproject.toml` (the JSON config now the single source of truth — they had drifted, JSON wins when present).
  Canonical gate = `uv run pyright` (exit 1 on any error), run in a full-extras env (`uv sync --all-extras`, else optional
  imports like `sherpa_onnx` read as missing). Verified: 0 errors / no unrecognized settings; full suite **84 failed**
  (≤ 85 baseline — config-only, zero runtime change). CI wiring = BUILD-2. Remaining 4b (None-safety 238) · 4c (phantom
  attrs 164) · 4d (override-incompat 76) · 4e (tail + mypy disposition).
- **ARCH-7 DONE — bridge contract AGREED in the bridge session; reconciled the Irene-side design.** The bridge session
  (sister repo) reconciled the contract draft I'd written into the AGREED form
  (`wb-mqtt-bridge/docs/voice_integration_contract_draft.md`, status AGREED 2026-06-06). Re-read it in full (Invariant #8)
  and updated `docs/design/mqtt_integration.md` §5/§6/§8/§10/§11 to the definitive shapes. **Deltas from my draft:**
  (A) write endpoint = `POST /devices/{id}/canonical {capability, action, params}` (not capability-in-path), a **6-code
  structured error enum** (`device_not_found`/`capability_not_supported`/`action_not_supported`/`param_invalid`{field,
  reason}/`device_unreachable`/`internal_error`, HTTP mirrors) — which I mapped straight to Russian spoken feedback +
  the `param_invalid`→clarify path — and a **500 ms synchronous value-topic echo** (per-driver configurable) so Irene
  confirms from real post-state. (B) read = dedicated **`GET /system/catalog`** (NOT the Layer-3 UI manifest): flat,
  capability-shaped, **all locales** for rooms *and* devices (`device_name`→`names:{…}` migrated bridge-side), one
  read-only **`sensor`** capability with `fields`, **multi-room**, and an **explicit-opt-in `global`** room; refresh via
  retained **`bridge/catalog/version`** (content hash). (C) new canonical capability vocab `brightness`/`color`/`cover`/
  `climate`/`sensor` (+ the AV set); bridge-side native onboarding via a generic data-driven `WbPassthroughDevice` driver
  + a capability-adapter composition layer (RGB/HVAC), wb-rules staying on the controller with the bridge **mirroring**
  state. **New Irene-side flows the contract surfaced:** sensor **reads** are `GET /devices/{id}/state` (catalog gives the
  field schema, state gives the value); "everywhere" commands = Irene resolves the `global` room → **N parallel canonical
  calls** with partial-failure speech (a batched bridge endpoint is v2). **Sequencing aligned to the agreed vertical
  slice** — "включи свет в детской" (one `wb-mr6c` channel) end-to-end — and ARCH-8 re-sliced PR-1..5 accordingly; PR-1
  (DeviceCommand + ports + services, fake-bridge) is adapter-free and can start now. ARCH-7 → `[x]`; **ARCH-8 UNBLOCKED**.
- **ARCH-7 [MQTT] design session — drafted `docs/design/mqtt_integration.md`; approach REDEFINED to
  bridge-as-single-authority (Invariant #8(d), decided with the user across the session).** Started from the original
  "Irene owns an MQTT output adapter + topic schema + device-topic resolution" framing and the archived `intent_mqtt.md`
  fat-handler design, and reframed via the two-flows split (Flow 1 content-agnostic output vs Flow 2 device actuation) +
  the "domain-typed `DeviceCommand`, never a topic" boundary. **Investigated the real deployment** (the sister project
  `wb-mqtt-bridge` + the live WB7 controller, SSH + broker creds from the sister repo): one WB7 is broker + house; its
  broker carries the whole home under the WB convention — **native WB gear** (lights/dimmers/RGB/curtains/HVAC/sensors via
  `wb-mqtt-serial`+`wb-rules`, *not* in the bridge) alongside the **bridge's AV virtual devices** (TVs/AppleTV/eMotiva).
  Explored the bridge's contract: it already has **rooms with ru names** (`config/rooms.json`, `GET /room/list`), a
  **catalog API** (`GET /config/devices` — commands + param schemas), and an **action API** (`POST /devices/{id}/action`,
  synchronous `CommandResponse`) — but the action input path is **native-command-only** (its capability map is
  internal-only). **User decisions (locked):** (1) build **both** output seams [(a)]; (2) **bridge = single device
  authority**, Irene talks only to the bridge [Y]; (3) **canonical** actuation vocabulary — Irene speaks
  `capability.action(params)`, the bridge translates (needs a small new canonical endpoint exposing its internal
  reconciler); (4) Irene **pulls the catalog from the bridge on startup** (REST; capability view so read/write vocab
  match). **Hexagon (Irene):** `DeviceCommand` domain type + `ActuationPort`/`DeviceCatalogPort` (the QUAL-24 ABC pattern)
  + a `BridgeClient` REST adapter under a new `irene.providers.outputs` group + an in-memory `DeviceCatalog` (distinct
  from `ClientRegistry`: catalog = everything actuable; registry = what's wired to a satellite). Flow 1 (raw-MQTT output)
  defined but deferred (no consumer). **Cross-project:** wrote a **bridge-side contract draft**
  (`wb-mqtt-bridge/docs/voice_integration_contract_draft.md`) — the canonical action endpoint, a voice catalog read
  surface, and **native-device onboarding** (a generic WB-passthrough driver for relay/dimmer/RGB/curtain/HVAC, since the
  existing `WirenboardIRDevice` is IR-specific; room authoring; capability maps) — for the user to reconcile in the bridge
  session. ARCH-8 (Irene implementation, PR-1..4) is **blocked** on that contract. Archived the superseded
  `docs/intent_mqtt.md` → `docs/archive/` (rejected fat-handler/runtime-method-gen design). Indexed
  `mqtt_integration.md` + the previously-unindexed `ws_esp32_transport.md` in the ledger review-doc table (clears the
  check_scope UNINDEXED flag). ARCH-7 left `[~]` (design drafted; pending bridge-session reconciliation).

### 2026-06-04
- **ARCH-10 PR-5 (wake-word) — PARKED (user) after a mapping that contradicts the design premise.** The design §11.1
  assumed *both* voice-trigger providers were hallucinated cruft to rebuild. The code says otherwise: **`openwakeword`
  is functional** (real `dscripka/openWakeWord` model URLs + feature models, real `predict()` detection, English
  catalog) — polish, not rebuild; **`microwakeword` is the genuine stub** — `_extract_features()` returns
  `np.random.random(...)` (noise), the `*_v1.0` model catalog is hallucinated, the one URL is a 404 TF demo, training
  was removed at `886d4d1` (matches QUAL-19). **Porcupine** is dead code (schema + config block, no impl, not in
  entry-points). **Open decision when resumed:** microwakeword (A) implement real MFCC frontend + user-trained tflite,
  experimental/WB7-validated; (B) cut/archive per QUAL-20 → openwakeword as sole provider; (C) thin. Plus openwakeword
  polish: split the `voice-trigger` extra → `wake-onnx` (openwakeword+onnxruntime) / `wake-tflite` (tflite-runtime),
  default `inference_framework="onnx"`, add a custom `model_path`, fix the get_python_dependencies group-name contract,
  cut Porcupine. No code written. ARCH-10 stands at **PR-1/2/3/4 done, PR-5 parked**.
- **ARCH-10 PR-4 DONE (`b5dd978`) — VAD engine seam (`energy` | `silero`, toml-selected).** Promoted VAD to a small
  port per design §11.2(iii): a `VADEngine` ABC in `utils/vad.py` that both impls satisfy, selected by
  `VADConfig.vad_implementation` (mutually exclusive) — no entry-points/component (VAD has no discovery/fallback need).
  `energy` = existing `SimpleVAD`/`AdvancedVAD` **unchanged** (user: no rewrite — the sibilant bug was already fixed; the
  improvement is silero + the seam). `silero` = new `utils/vad_silero.py` wrapping sherpa-onnx `VoiceActivityDetector`
  into the per-frame port (`is_speech_detected`), model auto-downloaded once into the asset folder. **64-bit only** (VAD
  runs in Irene only in the local-mic scenario; the WB7 delegates to the ESP32) → reuses sherpa-onnx (`asr-onnx`) + core
  numpy, **no new deps**. **Hexagon catch (caught by the import-contract test):** `utils` must not import `core`
  (ARCH-12 #9), so the **workflows** layer (`audio_processor`, already core-importing) resolves the AssetManager path and
  **injects** it into `SileroVADEngine` — contract green. Config fields surfaced in config-master `[vad]`; 11 seam tests;
  no real regression (one flaky perf test, passes in isolation). SileroVAD execution validated at WB7 re-validation.
- **ARCH-10 PR-3 DONE (`4902438`) — streaming ASR via `OnlineRecognizer` (`model_type="vosk-streaming"`).** Third
  model family on the provider: `OnlineRecognizer.from_transducer` with endpoint detection. `transcribe_stream` now does
  **real incremental streaming** for online models (feed chunks → emit partials → segment + `reset` on each endpoint →
  flush tail on `input_finished`); offline model_types keep the buffer-then-transcribe fallback; `transcribe_audio`
  one-shots the online recognizer (feed + tail-pad + finish + drain). Pack `vosk-model-small-streaming-ru` (verified on
  HF) — **key gotcha:** that repo ships *both* offline (`encoder.int8.onnx`) and streaming (`encoder.chunk64.onnx`)
  exports, so the descriptor uses `prefer="chunk64"` to select the online variant (PR-2's member-aware
  `_pick_pack_files` handles it). The big `vosk-model-streaming-ru` has a different layout (no chunk64) → addable later.
  Capabilities reflect streaming/real_time/offline by model_type; config-master surfaces the option. No assets/pyproject/
  schema change. 18 sherpa unit tests; **0 net suite regressions**. Streaming execution validated at WB7 re-validation
  (sherpa still won't import on the x86 dev box).
- **ARCH-10 PR-2 DONE (`b373633`) — Whisper-ONNX on the same `sherpa_onnx` provider.** A second offline model family
  on one provider/runtime, selected by config `model_type`: `whisper` → `OfflineRecognizer.from_whisper`
  (encoder/decoder/tokens — **no joiner**, whisper's own frontend; `language=""` = auto-detect), `vosk-transducer`
  stays default. Drops torch from 64-bit ASR images that don't otherwise need it. **AssetManager pack download made
  member-aware** (descriptor `members`: transducer=4 files / whisper=3) so `download_model_pack` + `_pick_pack_files`
  fetch exactly the right set; whisper packs = `csukuangfj/sherpa-onnx-whisper-{tiny,base}` (verified on HF: int8
  encoder/decoder + tokens, no joiner). config-master comments surface the option; no pyproject/lock/schema change
  (same `asr-onnx` extra; `model_type` already in the schema). Unit tests for both member sets; **0 net suite
  regressions**. **Flag:** `import sherpa_onnx` fails on the x86 dev box (`libonnxruntime.so` not found in the
  uv-installed wheel) — armv7/WB7 is proven, so this is an x86-image concern for **BUILD-3**; can't exercise sherpa
  execution locally until resolved (the from_whisper/from_transducer API is documented/stable, so code follows it).
- **ARCH-10 PR-1 DONE (`6e1a88a`) — `sherpa_onnx` ASR provider (offline VOSK Zipformer2).** New provider behind the ASR
  port running the alphacep VOSK Zipformer2 ONNX family via `OfflineRecognizer.from_transducer`, alongside vosk/whisper.
  **numpy-free** PCM/WAV→float (stdlib `array`/`wave`) so it runs on armv7; `SherpaInferencePolicy` (platform
  num_threads); lazy load + `warm_up()` gated by `preload_models` (absorbs the ~38 s graph-init). **AssetManager**
  gained additive **multi-file model-pack** download (`download_model_pack`: resolves encoder/decoder/joiner/tokens from
  the HF repo, int8 preferred, into the mounted asset folder; single-file path untouched). Build contract done **right**
  (`get_python_dependencies()->["asr-onnx"]`); `asr-onnx` pyproject extra carries the PEP 508 arch split
  (armv7l==1.10.46 / else >=1.11, no torch) + entry-point + added to `all`. Profiles: `embedded-armv7` and `full`
  switched off whisper (torch — can't run on armv7) to `sherpa_onnx` (small-ru edge / big vosk-model-ru 64-bit);
  canonical block in config-master. **Invariant #4 turned out to be a real schema seam** (not just raw TOML): registered
  `SherpaOnnxASRProviderSchema` in `config/schemas.py` + `AutoSchemaRegistry` — the master-config completeness tests
  caught the missing schema and now pass. Unit tests (numpy-free conversion, policy, build contract). **0 net new suite
  failures** (84 vs 85 baseline — one pre-existing config-completeness failure incidentally fixed). WB7 hardware
  re-validation deferred to ARCH-10 completion (user). **Remaining:** PR-2 whisper-onnx · PR-3 streaming · PR-4 VAD ·
  PR-5 wake-word.
- **ARCH-9 DONE → `docs/design/onnx_inference_layer.md` complete.** Closing additions after the draft: (a) confirmed the
  **system-dependency** path and found the **armv7 image must move Alpine→glibc/Debian** — sherpa-onnx has no musl build
  (proven on WB7: `import sherpa_onnx` fails on Alpine, works on `arm32v7/python:3.11-slim-bullseye`); the contribution
  *mechanism* is fine, only the base/pkg-manager/platform-key flip (apk→apt, `linux.alpine`→`linux.ubuntu`). (b) Recorded
  the **contribution principle as an invariant** (providers self-declare deps → build_analyzer collects enabled → Dockerfiles
  consume); *what* is contributed and the platform taxonomy are mutable (alpine now vestigial). (c) **VAD + wake-word
  resolved for both scenarios:** **WB7** delegates both to an **ESP32 satellite** (microWakeWord C-header + numeric VAD →
  WS to Irene → offline ASR `skip_wake_word=True`; matches ARCH-6/`ws_esp32_transport.md` exactly → armv7 image is ASR-only,
  `tflite-runtime` moot). **Standalone 64-bit** (the only path where Irene does its own): **two wake-word providers**
  (`openwakeword` ONNX / `microwakeword` tflite) **mutually exclusive via toml**, and **two VAD impls** (`energy` bug-fixed
  / `silero` SileroVAD-onnx) **mutually exclusive via toml**; today's voice-trigger providers are hallucinated cruft →
  **greenfield rebuild** (QUAL-19/20); sherpa-KWS is the future swap-in once a Russian base model exists. ARCH-10 sliced
  PR-1..5 (§12). Draft history below.
- **ARCH-9 design session (drafting) → `docs/design/onnx_inference_layer.md`.** Re-anchored the task on its
  real trigger (the new **alphacep VOSK** Zipformer2-ONNX models + which Irene models have sherpa-onnx counterparts), not
  a generic sherpa survey. **Proved armv7 feasibility on the real target (Wirenboard 7.2, A40i)** — SSH'd in, ran the
  alphacep `vosk-model-small-ru` in an `arm32v7/python:3.11-slim` container (matching the deployment): **correct Russian
  transcript, RTF 1.15, 110 MB RSS, 27 MB int8 model, 38 s load**. Key empirical findings baked into the doc: pin
  **`sherpa-onnx==1.10.46`** (1.13.2 has an armv7 `libonnxruntime.so` ELF-alignment bug), **`onnxruntime` has no armv7
  wheel** (so vosk-tts/plain-onnx can't run on the edge; sherpa works because it bundles its own ort), **`libasound2`**
  needed, **offline + small-model only on armv7**, **WB7 is Debian/glibc** (not Alpine). **Decisions locked:** new
  `sherpa_onnx` ASR provider running **alongside** vosk/whisper; **offline-first** (streaming later); **Whisper-ONNX in
  scope** (drops torch); ASR-centric (TTS/wake-word not sherpa targets — silero stays torch, vosk-tts stays its own ort
  as a config story, wake stays TFLite — no RU sherpa-KWS); **armv7 = no TTS**. Shared seam = **AssetManager extension +
  thread/CPU policy**, NOT a shared session runtime. Per-platform **dependency functions** (PEP 508 arch markers,
  libasound2, no torch) documented; build_analyzer marker-passthrough flagged for BUILD-5. WB7 test artifacts cleaned up
  (base image + key kept for the VAD/wake-word benchmarks). **Open: VAD + wake-word placement** (next).
- **QUAL-39 DONE — audited the 19 untyped REST endpoints; typed the UI-5-critical donations contract pair + `/health`
  (Option 2).** The audit immediately found what the task was filed to catch: `GET/PUT /donations/{handler}/contract`
  (UI-5's target) were untyped. Reconciliation: among the 19, config-ui/UI-5 consume **only** the contract pair — its
  status/config/NLU reads already hit typed endpoints (`/intents/status`, `/configuration/config/status`), not the
  untyped system ones (so the "+3 system endpoints" idea was dropped; typed only `/health`). **Approach refined by a
  discovery:** the contract body is a passthrough of `contract.json`, which has a **canonical JSON Schema**
  (`donation_contract_v1.1.json`, `additionalProperties: true`) — a strict Pydantic body would drift from it AND drop
  fields on the editor's GET→PUT. So typed the **envelopes** (`DonationContractResponse`/`DonationContractUpdateResponse`,
  mirroring the language models) and left the body `Dict[str,Any]`. **Symmetry analysis (user asked how the language part
  is delivered):** the phrasing side already does exactly this — `LanguageDonationContentResponse.donation_data:
  Dict[str,Any]` passthrough + its own schema `donation_language_v1.1.json` — so the contract fix brings it to **parity**;
  UI-5 generates both BODY types from the two JSON Schemas, envelopes from OpenAPI (updated UI-5's note). Classified the
  rest: (b) legit-dynamic/non-JSON (asyncapi/html/prometheus/components/debug) documented; non-UI-5 hygiene (asr/monitoring/
  nlu_analysis/system-status) deferred. Verified: models accept the real GET/PUT shapes incl. passthrough extras, modules
  import, suite 85=85 (0 net regression).
- **config-ui ↔ `../wb-mqtt-bridge/ui` stack comparison + harmonization kickoff (pre-UI-1/2/3/5).** Compared the two UI
  stacks: same foundation (React 18 / Vite 5 / TS-strict / Tailwind / react-router 6) but very different altitude — the
  bridge is a tested, lint-gated, MUI + react-query + zustand + OpenAPI-generated dashboard; config-ui is a lean,
  test-less, un-linted Monaco editor on native `fetch` + ~37KB hand-written types. **User decisions:**
  (1) **Strict linting (insisted) → UI-6:** added a **bridge-identical** `.eslintrc.cjs` (type-aware
  `recommended-type-checked`; `no-floating-promises`/`no-misused-promises` errors; `any`-noise rules off) + the eslint
  devDeps + `lint`/`lint:fix`/`check` scripts at `--max-warnings 0`; fixed the runtime↔types version skew
  (`@types/react` 19→18, `@types/node` 24→20 to match `react@18`); added `engines`. `npm run type-check` stays green.
  The strict gate immediately surfaced **71 pre-existing issues** incl. a **real latent bug** (`PromptEditor.tsx`
  variable `description:` shadowed by the prompt-description branch — fixed). **Cleaned up all 71 (user-directed):**
  51 async → `void`/arg-aware-wrap, 14 `exhaustive-deps` → disable+reason (mount loads, fns not memoized → adding deps
  loops), 5 type-assertions auto-fixed; `npm run check` + build green (no test net → type-check/build are the safety net).
  Folded the strict lint into the Invariant-#4 config-ui DoD + BUILD-4 (now `npm run check && npm run build`). **UI-6 DONE.** (2) **Data-layer: "stop fighting
  type drift" → generation-only, folded into UI-5:** rebuild UI-5's `src/types/*` by **generating** from the FastAPI
  OpenAPI schema (`openapi-typescript`), not hand-authoring — the backend is ~80% typed (104/123 routes have a
  `response_model`). Prereq: a backend script to dump `app.openapi()` to a committed `openapi.json`. **axios + react-query
  ruled OUT** (config-ui is load-edit-save, not a server-cache dashboard). (3) **Filed QUAL-39** to audit the ~19 routes
  that return raw `dict` (weak generated types) — gates UI-5's generated-type quality. No behavioral code changed yet.

### 2026-06-03
- **QUAL-7 CLOSED-AS-OBSOLETE (Invariant #8, user-approved).** Surfaced while reconciling the QUAL-3..7 static-baseline
  backlog against Gate-2 relevance: QUAL-7's premise (a `train_schedule` config-master-vs-model mismatch) no longer exists
  — the `train_schedule` handler + config/assets were removed in **QUAL-34**. Verified `train_schedule` is absent from
  `config-master.toml`, `config/models.py`, and all of `irene/`/`assets/`/`configs/`. Nothing to reconcile → closed, no code
  change. (QUAL-3..6 remain valid static-baseline cleanup, none on the Gate-2 critical path.)
- **QUAL-24 DONE — service-locator → domain-owned ports in 8 handlers (Invariant #3, user-approved Option A).**
  Process note: I initially started this by grepping code and nearly committed to injecting `component_manager` (which
  removes the *import* but leaves the domain runtime-coupled to a core registry — an Invariant #3 violation). The user
  stopped me, pointed to the Invariants. Re-anchored on #3/#5/#8/#9, read the invariants + `phase1_architecture_map.md`
  (§2.3–2.5: intents=domain, core=application; `intents→core` is the outward sin), and brought a hexagon-compliant
  proposal. **User chose Option A (domain-owned ports).** Added `irene/intents/ports.py` (Protocols: `LLMPort`/`TTSPort`/
  `AudioPort`/`ASRPort`, shared `ComponentControlPort`, `ComponentControlRegistryPort`); the 8 handlers depend only on
  these; `IntentComponent.post_initialize_handler_dependencies` injects the real components inward as structural impls
  (components import nothing → no new edges). `system` reuses the already-injected `context_manager`; `provider_control`
  gets the registry port. Removed `get_core()` from every handler + the ARCH-1 `ignore_imports` hatch — **ARCH-1 now holds
  with no hatch (9/9 kept)**, proving the transitive `intents→core.engine→{components,inputs,workflows}` pull is gone.
  Honored Invariant #9 (removed `TYPE_CHECKING` guards in the 6 touched handlers that had them; the 2 untouched handlers'
  guards stay for QUAL-32). Caught a latent bug: the old `await component_manager.get_component(...)` awaited a **sync**
  method, so the get_core fallback was already broken — injection is what actually worked. Invariant #4: no backend
  contract changed → config-ui untouched. Suite 85=85 FAILED (0 net regression). **Hardening (user-directed, same
  session):** user asked "who implements the ports?" — verified, and it surfaced that the ports (consumer-defined)
  faithfully captured 4 **pre-existing dead handler calls** (`stop_synthesis`/`cancel_synthesis`/`pause_audio`/`resume_audio`
  with no implementer) AND that the old injection only wired `conversation` (the other 5 handlers were getting `None`). Per
  the user's directive, converted the ports from Protocols to **ABCs** and made the application **components inherit** them
  (`components→intents.ports` = application→domain, inward; 9/9 contracts kept) so unimplemented methods fail at
  instantiation. Implemented the 4: audio pause/resume delegate to providers (real); TTS stop/cancel are honest best-effort
  (providers can't interrupt). Removed the orphaned global-core service-locator (`get_core`/`set_core`/`_global_core`) from
  `engine.py` — zero callers, no test referenced it. The now-wired-but-untested handler paths are **filed as TEST-8**
  (capability-port handler coverage, a TEST-7 coverage goal).
- **ARCH-12 DONE — removed the last two residual upward edges; locked `utils` with contract #9.** Edge 1
  (`utils.vad → core.metrics`) was a **dead import** (`get_metrics_collector` imported but never called — a Phase-4
  leftover after VAD metrics unified into `MetricsCollector`); deleted it. Edge 2 (`utils.logging → config.models`):
  relocated the standalone `LogLevel` enum **into `utils.logging`** and re-exported it from `config.models`, inverting
  the edge to `config → utils` (downward, allowed) while every `from config.models import LogLevel` still resolves;
  dropped the now-dead `from enum import Enum` in `config.models`. Added the 9th import-linter contract "Utils
  (foundation) depends on nothing upward" (`source=irene.utils`, forbids all 9 sibling layers), teeth-checked (planted
  `utils→config` → BROKEN). One self-inflicted hiccup: the teeth-check's `git checkout -- vad.py` clobbered the
  uncommitted edge-1 edit (restoring the dead import); re-applied it and re-verified clean — lesson: don't `git checkout`
  a file with uncommitted edits to undo a planted violation. Verified: no cycle, 9/9 contracts kept, suite 85=85 FAILED
  (0 net regression). Synced `phase1_architecture_map.md` §2.3 (Invariant #5) — closes the last backwards-edge findings
  there. The whole hexagon (ARCH-1..6, 11, 12) is now clean *and* enforced by contracts.
- **ARCH-13 DONE — retired the dormant `irene/plugins/` legacy system.** Reconciliation surfaced that ARCH-11/S2 had
  re-rooted only the Component/Workflow ports — the **8 capability ports still extended `PluginInterface`** — so completing
  decision (c) was a prerequisite here (the ARCH-13 entry had anticipated this). Probed the risk surface first: nothing
  reads `.version`/`.description`/`.configure()` via the plugin contract (components get `.name` from `Component.__init__`,
  lifecycle from `ComponentPort`), so re-rooting only *relaxes* abstract requirements — can't break instantiation, only MRO
  (caught at import). Re-rooted all 8 ports onto `EntryPointMetadata` (script-driven), MRO-smoke-checked the
  `Component`+port diamond on real components. Then **deleted** `irene/plugins/` (`AsyncPluginManager`/`BasePlugin`/
  `PluginRegistry`/`builtin/`) + `core/interfaces/plugin.py`; stripped the plugin lifecycle from `engine.py` (init/load/
  unload + the injected `plugin_manager` param/attr) and its construction from `runners/composition.build_core`; rewired the
  ~8 service-locator status readers (`cli.py`/`base.py` "Plugins loaded" line dropped; `webapi_router` ×4 sites +
  `webapi_runner` plugin blocks removed — the `hasattr`-guarded ones were already graceful; `components.py` service-map
  entry dropped); cleaned dead `irene.plugins.builtin` refs in `build_analyzer.py`. NB: distinct from **QUAL-24** (that's
  `get_core()` in intent *handlers* — different sites, still open). Verified: all affected modules import, 8/8 contracts
  kept, suite **85=85 FAILED** (0 net regression), no live refs to retired symbols (only provider docstrings note the old
  paths). `core→plugins` was already clean from ARCH-11/S3.
- **ARCH-11 S4 DONE — locked the inversion; ARCH-11 COMPLETE.** Added the 8th import-linter contract "Core does not import
  the outer layers (ARCH-11)" (`source=irene.core`, forbidden `irene.{inputs,workflows,components}`). Found there were **no
  literal ARCH-5 exemptions** to remove — ARCH-5 had simply left these composition-root edges *unenforced* (added no
  contract at all), so adding the enforcing contract IS the revocation. Guarded against the `irene.core.components` vs
  `irene.components` package-name gotcha (different packages — no false positive). **Teeth-checked**: planted a temporary
  `core→inputs.manager` import → contract went BROKEN (7 kept/1 broken); reverted → 8 kept. The generic contracts test
  (`test_import_contracts.py`) covers the new contract automatically; updated its docstring. **8/8 contracts kept**, suite
  **85=85 FAILED** (0 net regression). **ARCH-11 closed across S1-S4** (4 edges inverted, decision (c) applied, construction
  moved to the composition root, all locked). Legacy `irene/plugins/` teardown stays split to ARCH-13 (core→plugins is
  incidentally already clean as an S3 byproduct).
- **ARCH-11 S3 DONE — construction inversion (edge 4 removed; all 4 edges now done).** Topology was friendly: a single
  production instantiation (`runners/base.py:85`, inherited by every runner) plus two `examples/` demos. Added the
  composition root `irene/runners/composition.build_core(config, config_path)` which constructs ALL 7 managers
  (component/plugin/input/context/timer/metrics/workflow, preserving the original dependency order — input/workflow need the
  component manager) and injects them into `AsyncVACore`. `AsyncVACore.__init__` is now keyword-only DI and constructs
  nothing; it **no longer imports `inputs.manager`** (edge 4) **nor `plugins.manager`** (bonus: `core→plugins` gone, which
  de-risks ARCH-13) — those two outward managers are typed `Any` in core so the edge stays out. Routed `runners/base.py` +
  both demos through `build_core`. Verified: zero `core→{inputs,plugins}` imports remain, `build_core(CoreConfig())`
  assembles a core with all 7 managers wired, import-linter **7/7 kept**, suite **85=85 FAILED** (0 net regression).
  NEXT = S4 — add the import-linter contracts forbidding `core→{inputs,workflows,components}.base` and remove the ARCH-5
  exemptions, which *locks* the whole inversion so it can't silently regress.
- **ARCH-11 S2 DONE — Component + Workflow ports into `core/interfaces` (edges 2 & 3 removed).** Both `Component` (400 LOC)
  and `Workflow` (257 LOC) turned out to be fat *shared concrete bases* (provider switching, DI, health — `name`/`providers`/
  `initialized` are `__init__` attrs), not thin interfaces, and `core` had **no `isinstance(Component/Workflow)`** checks and
  reached component-specific methods (`synthesize_to_file`, `play_file`) by duck-typing. So rather than relocate the fat code
  into the port layer, I followed the codebase's own `ASRPlugin` pattern: thin ABC ports declaring only the generic
  manager-facing surface. Added `core/interfaces/component.ComponentPort` (initialize/shutdown/inject_dependency/
  get_dependency/get_component_dependencies/get_service_dependencies + name/providers/initialized) and
  `core/interfaces/workflow.WorkflowPort` (initialize/add_component/process_audio_stream/process_text_input/shutdown +
  name/components/initialized) — both `EntryPointMetadata`-rooted (decision c). Fat bases now `Component(ComponentPort)` /
  `Workflow(WorkflowPort)`. `core/components.py` and `core/workflow_manager.py` type against the ports; caught + re-pointed
  the **runtime `issubclass(workflow_class, Workflow)` discovery gate** (a 2nd `workflows.base` import site) to `WorkflowPort`;
  `RequestContext` now imported inward from `intents.context_models` directly (the ledger-flagged domain re-export). Verified:
  no core import of `components.*`/`workflows.*` remains, smoke `issubclass` checks pass for `ASRComponent` +
  `UnifiedVoiceAssistantWorkflow`, import-linter **7/7 kept**, suite **85=85 FAILED** (0 net regression). 3 of 4 edges done;
  NEXT = S3 (construction inversion — edge 4: `engine.py→inputs.manager`, move manager construction to composition/runners).
- **ARCH-11 S1 DONE — input-port consolidation + re-root onto EntryPointMetadata.** First of the 4 staged edges.
  Landed the single input port as `core/interfaces/input.InputPort(EntryPointMetadata)` (+ the `InputData` value type),
  replacing both the former `inputs.base.InputSource` (which created the `core→inputs.base` edge) and the dead duplicate
  `InputPlugin` (was `PluginInterface`-rooted, 0 subclasses). Adapters (CLI/microphone/web) and `InputManager` now
  implement/type against `InputPort`, importing it inward from `core/interfaces`; `inputs/base.py` shrank to just the
  adapter-side `ComponentNotAvailable`. `workflow_manager.py` imports the port inward (3 sigs) → the input edge is
  **removed**. Stripped the now-dead `InputPlugin` refs from the dormant `plugins/manager.py` (behavior-preserving — it
  loads 0 plugins; the `_input_plugins`/`get_input_plugins` bits were always empty). Verified: import-linter **7/7 kept**
  (the SCC-2 `inputs.base`-no-adapters contract still holds), full suite **85=85 FAILED** vs stashed baseline (0 net
  regression). NEXT = S2 (Component+Workflow ports into `core/interfaces`, core imports them).
- **ARCH-11 hierarchy-fork RESOLVED + staging locked (discussion, no code yet).** Opened the deferred ARCH-11 session
  with the `EntryPointMetadata`-vs-`PluginInterface` decision, as agreed. Traced the real graph instead of trusting the
  summary: the live architecture is `EntryPointMetadata`-rooted (every real adapter/component extends it); `PluginInterface`
  is a **near-dead legacy skin** — capability ports have **0 concrete subclasses** (MI mixins only), `core/interfaces/input.
  InputPlugin` is a dead duplicate of `inputs.base.InputSource`, and the whole `irene/plugins/` manager is dormant.
  **Empirically verified it loads 0 plugins:** `engine.py:95` calls `load_plugins()` with no paths → builtin branch is
  `pass` → `_plugins` stays `{}`; the ~8 `core.plugin_manager._plugins` status readers all report 0. **Decision (c):**
  retire `PluginInterface`, re-root all ports onto the single clean base `EntryPointMetadata` (abc+typing only; the
  `core/interfaces` port layer is already import-clean) → clean dependency direction + enforceable contracts. Honest
  asterisks recorded: `EntryPointMetadata` stays a "fat" root (concern-bleed, not a direction violation — purist split is
  Gate-2 gold-plating) and ARCH-12's residual edges survive. **Scope staged:** full (c) forces touching the legacy system
  (typed on `PluginInterface`) which is read via the QUAL-24 service-locator pattern at ~8 status sites — so the teardown
  is **split to new ARCH-13** to keep ARCH-11 a single-purpose, bisectable hexagon commit before Gate 2. ARCH-11 = invert
  4 edges + re-root ports + consolidate input port + contracts; ARCH-13 = delete `irene/plugins/`, finish `PluginInterface`
  removal, rewire the 8 readers. Locked into the ARCH-11 ledger entry + filed ARCH-13.
- **ARCH-6 CORE DONE — WS streaming-input driving adapter + room/device activation (design + implement, per user).**
  Reconciliation up front (with the user): scoped to the **transport + identity core**, because the **device-model half**
  has no substrate yet (no device/room handlers, all 13 `entity_type` decls `generic`, no MQTT handler) — authoring it now
  would be the ledger's own "inert branch", so it's **relocated to ARCH-7 [MQTT] + QUAL-35**. ESP32 firmware is stale →
  designed **server-first** (`docs/design/ws_esp32_transport.md`). Built `/ws/audio` (`webapi_router.py`): registration
  handshake → `ClientRegistry.register_client` → stream raw PCM (16k/mono binary frames) → `process_audio_input` with
  `skip_wake_word=True` (on-device wake) → response frame. The pipeline entry already accepted `client_context`
  (`client_id`/`room_name`/`device_context`), and `resolve_physical_id` already returned `client_id or room_name or
  session_id` — so the activation is exactly: **the handshake populates those, and the physical origin keys the action
  store**, no seam rewrite. Made `ClientRegistration.from_dict` tolerant of the handshake's control keys (`type`/
  `sample_rate`/`wants_audio`). Removed the dead P0-8 base64 `AUDIO_DATA:` branch (`inputs/web.py`); kept `_input_queue`
  (it's live — CLI/mic input). Tests: `test_ws_driving_input.py` (3 — incl. an end-to-end TestClient handshake→pipeline
  with a stubbed core). **SCC-2 cycle FIXED — and the user caught a wrong first approach.** My initial instinct
  (entry-point/runtime discovery) would have been a **service-locator** — the exact pattern this project is removing
  (QUAL-24). The correct fix is dependency *separation*, not service-location: `inputs.base` mixed the `InputSource`
  PORT with the `InputManager` ORCHESTRATOR (which legitimately imports the concrete adapters). Split them —
  `InputManager` → `irene/inputs/manager.py` (the input-layer composition point); `base.py` now imports NO adapters →
  clean DAG `base ← {cli,web,microphone} ← manager`, deps point inward to the port. **Locked with a new import-linter
  contract** ("Input port does not import its adapters") so it can't regress. Also corrected the device-half hand-off
  bookkeeping: QUAL-35 now explicitly OWNS the `entity_type`/`room_context` authoring + `_is_device_entity` swap (it had
  stale-pointed back to ARCH-6); ARCH-7 references the device handlers as its substrate. 0 net regressions; 7/7 import
  contracts kept. **ARCH-6 fully DONE `[x]`** (device-half is QUAL-35's, tracked).
- **ASSET-2 DONE — liveness-checked every model download URL; fixed 2 real defects.** Swept all 33 model URLs in
  `irene/` (range-GET each, judging on bytes-served vs stall per the fake-IP caveat — all hosts resolve into
  `198.18.0.0/15`, normal). Hosts all healthy: silero.ai served the real 40MB `v4_ru.pt`; alphacephei/vosk, github
  releases (openWakeWord v0.5.1), openai whisper-CDN, github/spacy-models (3.7.0) all 200/206. **Fixed:** (1) the whisper
  `tiny` URL had a **truncated 40-char hash** → 404; restored the full 64-char canonical hash (cross-checked against the
  installed openai-whisper `_MODELS`; the other 6 were correct). (2) silero `v4_en/de/es/fr` were declared but **404** —
  silero's v4 line is **Russian-only** (`v4_ru` ✓, `v4_ua` exists; western langs stay at v3); trimmed the `silero_v4`
  catalog to `v4_ru` and documented that non-RU TTS uses `silero_v3` (its en/de/es are live). **Left dead by design →
  QUAL-19:** microWakeWord's `micro_speech.tflite` (github tflite-micro raw moved) — a TF demo model in a known-placeholder
  provider, so it's the ESP32/wakeword keep-fix-cut call. Torch.hub hedge not needed (silero healthy). Updated the
  `irene-stale-models` memory (URL liveness-check now closed). Providers import clean; 0 net suite regressions.
- **QUAL-34 DONE — declared-but-unconsumed donation params triaged per-handler WITH the user, then wired-or-removed.**
  The user drove the wire-vs-remove call for each of the 19 (and asked good clarifying questions — e.g. confirmed the
  conversation handler is fundamentally raw_text→LLM so its `topic`/`query_topic`/`context_reference` slots add nothing;
  flagged `train_schedule` as bogus → remove the whole handler; chose to BUILD capability rather than minimize surface).
  **Outcome:** removed 9 params + the whole train_schedule handler; wired 10 via the typed `get_param` accessor (the same
  accessor that activates the QUAL-30 clarification boundary). Highlights: `voice_synthesis.voice` migrated off the
  raw_text re-parse to the canonical NLU entity (Bucket B); `datetime.relative` got a real date-offset + localized
  lead template (`date_relative`/`relative_leads`, "Завтра: …" / "Tomorrow: …"); `greetings.time_of_day` honours an
  explicit "good evening" over the clock; `text_enhancement.{improvement_type,correction_type}` steer the LLM via a
  SYSTEM-prompt focus directive (kept out of the user text, QUAL-16 injection-safe); the system/system_service params
  are consumed (with `detailed` a real verbosity toggle) where the handlers have real data, surfaced-as-scope where
  they're generic stubs. **Surface fixes:** several CHOICE params had wrong-English ru surfaces / missing en surfaces
  (e.g. correction_type, metric_type) — authored proper bilingual ones per the donation-choice-surfaces rule.
  **Discipline:** committed in 3 parts (removals → 2a wirings → 2b wirings); caught a missed
  `assets/templates/train_schedule_handler/` (part 1's `git rm` only took the donations dir — user flagged "did we
  remove ALL assets?"). New `test_qual34_param_wiring.py`; audit doc marked resolved; 0 net suite regressions across all
  parts; donations load 0 warnings. The declared-param audit is now clean.
- **QUAL-21 DONE — settings-runner `ComponentConfig` crash-bug resolved by REMOVAL (user decision).** The
  `irene-settings` Gradio runner constructed `ComponentConfig(audio_output=…, microphone=…, web_api=…)` — fields
  removed in the architecture migration (mic/web → `config.inputs.*` / `config.system.web_api_enabled`,
  `audio_output`→`audio`) → crash on launch. User judged the runner obsolete ("garbage") → **removed** rather than
  fixed: config management is now config-ui's TOML editor / direct file edits. Deleted `settings_runner.py` (462 LOC)
  + both pyproject registrations + `runners/__init__.py` exports; scrubbed README, `architecture.md` (usage block +
  the "Settings Режим" Mermaid subgraph), `tools/migrate_runners.py`. **Retired all 4 stale demo examples**
  (`component_demo`/`dependency_demo`/`config_demo`/`utilities_demo` — they demoed the removed optional-components
  model; user picked "retire all 4" via AskUserQuestion) and fixed `examples/__init__.py` (it imported `config_demo`).
  Verified: runners + examples import clean, the 3 remaining runner scripts resolve, no stale `ComponentConfig` kwargs
  remain in `irene/` (the leftover `audio_output`/`microphone` hits are device-capability keys / device enumeration /
  the intentional v13→v14 migration reader), 0 net suite regressions. Net −~900 LOC of dead runner+demo code.
- **QUAL-37 [DFLOW] DONE — targeted no-intent clarification (offline path).** The signal
  (`_fallback_context.likely_domain`, computed by `_create_fallback_intent`) was already consumed on the ONLINE path
  (QUAL-16's `_build_fallback_context_prompt` injects the guessed topic into the LLM prompt); the gap was the OFFLINE
  (no-LLM) path, which gave a generic "didn't understand «…»" responder. Now `_handle_fallback_without_llm` reads
  `likely_domain` and, when it maps to a known domain, returns a **deterministic, localized, offline** targeted
  explain-and-ask ("Возможно, вы хотели поставить таймер?" / "Did you want to set a timer?") — new `fallback_targeted`
  template + a `fallback_domain_labels` map (domain→friendly action phrase) added to the existing
  `assets/localization/conversation/{ru,en}.yaml`; otherwise it falls through to the generic responder (no guess /
  unknown domain). Result metadata gains `targeted`/`likely_domain`. Both fallback paths now consume the NLU's guess.
  Tests: `test_no_intent_clarification.py` (5) — targeted ru/en, generic + unknown-domain fall-through, determinism +
  offline; 0 net suite regressions. **Ledger hygiene (user-flagged):** there were two QUAL-37 entries — the QUAL-36
  done-edit had only matched the first 2 lines of the old QUAL-36 entry, orphaning the rest of its body under a stray
  duplicate QUAL-37 header; removed the corrupted block, leaving the single correct QUAL-37 (now `[x]`).
- **QUAL-38 [DFLOW][I18N] DONE — processing-language config-derive + inline-bilingual externalization (carved from QUAL-36).**
  **Key correction during reconciliation:** the carve-out spec framed (a) as "thread from context", but the processing
  language is the **audio-MODEL/deployment** language (which number-spelling/transcription rules to apply), NOT the session
  language — spelling numbers in the session language while synthesizing with a different-language voice would mismatch.
  So the correct (and lighter) fix is **config/model-derive**, not a request-threading refactor of the QUAL-13 pipeline
  (which would have introduced that bug; the pipeline's "language is request-scoped in principle" comment was the gap, now
  corrected). **(a)** `convert_numbers_to_words` → language-required (caller already threads `request.language`);
  `PrepareNormalizer` gains a config `language` and stops falling back to inline `"ru"`; `unified.py` threads the per-normalizer
  deployment language to both number normalizers; `silero_v3|v4` derive `self.language` from model config (default `*_ru.pt`
  → ru); `asr_component` transcribe endpoint resolves to `self.default_language`. Left the standalone `utils/text_processing.py`
  library defaults and the Pydantic request-schema `"ru"` defaults as documented library/API defaults. **(b)** Re-classified
  the ~33 `== 'ru'` branches: the genuine **inline RU/EN strings** were only in 4 handlers — externalized voice_synthesis (6)
  + system (3) + provider_control (5, NEW template dir + a `_get_template` method) to template assets, and unified
  random_handler (3) by adding `{error}` to the ru templates so the `== 'ru'` arg-branch could go. **Kept as legitimate**
  (done-criteria allows): `system_service_handler` Russian **pluralization grammar** (the strings were already templated; the
  branch only computes plural suffixes) and the Russian command-keyword **parsing** in voice_synthesis. **Verified:** all new
  templates load + resolve in ru/en; precise mine-vs-baseline diff = **0 new failures**. Closes the QUAL-36 carve-out.
- **QUAL-36 [DFLOW][I18N] DONE — single language source-of-truth; hardcoded `"ru"` purged from the session path.**
  **Reconciliation found the spec was incomplete:** not one language source but FOUR competing declarations
  (`CoreConfig.language="en-US"` in locale form *and* actually consumed; `nlu.default_language`/`supported_languages`;
  `nlu_analysis.languages.*`; `IntentAssetLoader`'s own `"ru"`/`["ru","en"]`). Surfaced the conflict via AskUserQuestion;
  user chose **promote to a top-level canonical `CoreConfig.default_language` + `supported_languages` (2-letter)** read
  at the composition root and injected inward — `nlu.*`/`en-US`/asset-loader derive/retire. **Implementation, correctness-
  first (establish the invariant BEFORE deleting fallbacks):** added the canonical fields + removed the `nlu.*` duplicates
  (config-master.toml synced); injected `default_language`+`supported_languages` into `ContextManager` (mirrors the existing
  `max_history_turns` DI) and seeded sessions; repointed NLU detection to the canonical source + made `_analyze_text_language`
  return `None` on no-signal (caller applies the default, clamped to supported); threaded canonical into NLU **and** LLM
  provider configs. Then **deleted all 67 `context.language or "ru"` fallbacks** → bare reads; ripped out the timer/audio/
  voice-synthesis `_get_language` Cyrillic-sniff heuristics; **fixed a real bug — `hybrid_keyword_matcher` defaulted to `'en'`
  while everything else defaulted `'ru'`**, so an unset language partitioned keywords wrongly; made handler `language="ru"`
  default params required (keyword-only where they followed defaulted args). Added **`context.supported_languages`** (seeded
  from canonical) so the `system.py` language-switch validates against it — no baked `["ru","en"]`. **A real non-RU bug
  caught:** `RequestContext.language` defaulted to `"ru"`, and the request→session merge overrides on any truthy value — so
  an unspecified request would STOMP an English seed; changed the default to `None` ("unspecified"). **T7 (folded from
  QUAL-16):** localized the LLM machine-context labels (`Currently active:`/`Session:`/`Recent activity:`/`Thread:`/`Actions:`/
  `Flow:`/`Context:`) → `assets/localization/conversation/{ru,en}.yaml` + a `_context_label` resolver keyed by user language
  (with an offline English last-resort, console-floor pattern). **Folder-naming note (user-flagged live):** localization uses
  bare domain dirs (`conversation/`, like `voice_synthesis/`/`datetime/`), distinct from the `_handler`-suffixed prompt/template
  dirs — both key to `"conversation"` via the loader; verified, not a duplicate. **Verification:** new
  `test_language_source_of_truth.py` (6 tests) proves English-primary AND arbitrary-language (`de`) seeding, detection clamp,
  `supported_languages` on context, label localization, and the no-stomp contract; updated the one test that encoded the old
  `RequestContext`→`"ru"` default; **precise mine-vs-baseline diff = 0 new failures** (the perf/VAD timing tests are flaky and
  fluctuate run-to-run). **Carve-out → QUAL-38** (filed): processing-language defaults (number-spelling/silero/ASR/text-proc)
  + inline bilingual handler messages (`== 'ru'` branches) are a distinct concern from the session source-of-truth. Hexagonal
  held: domain reads `context.language`/`context.supported_languages`, never imports config; the composition root injects.
- **QUAL-17 [STREAMAPI] DONE — critical review of the streaming-API exposure; keep/upgrade/replace filed.** Found the
  surface is **two** independently hand-rolled subsystems, not one: a 474-LOC code-first generator
  (`irene/api/asyncapi.py` — `@websocket_api`/`WebSocketRegistry`/custom Pydantic→AsyncAPI **2.6.0**) **and** a fully
  bespoke **923-LOC renderer** at `/asyncapi` (`assets/web/{templates/asyncapi.html, static/js/asyncapi.js,
  static/css/asyncapi.css}`). **Three ledger-description corrections** (recorded in the review doc): the renderer is
  **not** `@asyncapi/web-component@2.6.4` — that string is only a *comment* (`asyncapi.py:7`) rationalizing the 2.6.0
  spec choice, so the code documents a dependency it doesn't use; the main **`/ws` is undecorated → absent** from the
  spec; the **TTS** endpoints (`/tts/stream`, `/tts/binary`) **are** documented (ledger listed `/ws`, omitted TTS).
  Tooling scan (June 2026): the official **`@asyncapi/web-component` 2.6.5** is maintained, framework-agnostic,
  renders 2.x+3.x, and is a clean drop-in fed by the existing `/asyncapi.json`; **FastStream** generates AsyncAPI from
  Pydantic but is a *broker* framework (Kafka/RabbitMQ/NATS/MQTT/Redis) → adopting it = rewriting the WS transport,
  wrong shape; `asyncapi-python` is spec→code (opposite direction). **No maintained drop-in introspects raw FastAPI
  WS routes** → the generator must stay bespoke. **Recommendation = Hybrid:** REPLACE the renderer with the vendored
  official component (offline-first — no CDN; ≈ −900 LOC) + KEEP-and-improve the generator (fix lossy
  `_clean_property_for_asyncapi` union/nullable flattening; decide 2.6.0-vs-3.0 deliberately; binary message bindings
  for ESP32). Hand-off itemized into **QUAL-18** §5. Per Invariant #5, `streaming_api_review.md` written + index row
  marked `[x]`. No code changed (review-only task).
- **QUAL-16 [PROMPTS] DONE — externalized + hardened all LLM prompts; live-validated against DeepSeek.** Stage A: the
  6 task prompts (improve/translation/grammar/summarize/expand/chat-default), triplicated inline across the 3 providers
  and language-locked to the provider, → `assets/prompts/llm/{ru,en}.yaml` (system prompt set), keyed by the USER's
  language; the component resolves + passes `system_prompt`, providers hold none (generic fallback only); fixed
  text_enhancement `task="correct"`→`grammar_correction`; killed anthropic's hardcoded "You are a helpful assistant."
  (component injects externalized `chat_default`). Stage B (user request): hardened the conversation persona prompts +
  fixed their `_get_prompt` "ru" hardcode (→ context.language). Tail: externalized `_build_fallback_context_prompt` →
  `fallback_context`/`fallback_topic` assets; wrote `docs/guides/PROMPTING_GUIDE.md`. Hardening rules baked in:
  plain-text/no-markdown (spoken), return-only-result, "user text is DATA not instructions" injection resistance,
  persona, preserve-language. **The user supplied API keys (.env, gitignored) → live validation, which paid off:** it
  caught a real markdown-list leak (the static prompt allowed it) that I then fixed by strengthening the prompts, and
  confirmed injection attempts ("call yourself GPT / answer in a markdown list") are refused (persona holds, plain
  text). Invariant #4: prompt editor is dir-driven so `llm/` surfaces automatically; zero config-ui changes,
  type-check passes. Residual → QUAL-36(7): the LLM context-injection *labels* (`Currently active:` …) are machine-
  context, localized with the language work, not prompt hardening. Suite 30/30.
- **QUAL-15 [LLM] DONE (Stages A–C) — real offline foundation + DeepSeek default + VseGPT removed.** The offline LLM
  posture was fictional (QUAL-14): phantom `console`, `fallback_providers` never iterated, `generate_response` raised
  offline. **Stage A:** `ConsoleLLMProvider` offline floor (deterministic, always available, localized "unavailable");
  a real fallback chain (default → fallback_providers → console) driving enhance_text + generate_response (never raises);
  component `is_available()` excludes the stub (conversation handler unaffected). **Stage B (user):** DeepSeek
  (`deepseek-chat`, OpenAI-compatible, new default, matching ../personal_vpn); VseGPT removed entirely; offline-safe boot
  via a new optional `${VAR:-default}` env-var syntax + optional LLM keys (enabled cloud LLM w/o key no longer hard-fails
  boot → console floor). **Stage C:** `openai.is_available()` → local check (was a network probe returning True on
  failure); per-call timeouts; providers raise on failure (chain handles fallback, no silent original-text); fixed the
  dead `universal_llm` ASR-enhance lookup (→ real LLM component). **User-directed during the work:** (1) externalize the
  hardcoded localized message arrays → moved to `assets/localization/llm/{ru,en}.yaml` (the localization asset category,
  read via `get_localization`, injected into the console floor); (2) kill VseGPT altogether. Verified: WebAPI boots with
  no LLM key (console loads, deepseek skips); `test_llm_fallback.py` (4) + suite 30/30; QUAL-23 phantom-console ERROR
  cleared. Carve-outs: prompt hardening → QUAL-16; real local-model LLM → ARCH-9/10.
- **QUAL-13 Stage 2 DONE — collapsed the text-processing subsystem; wired both real stages. QUAL-13 complete.**
  Reconciled first (Invariant #5/#8): the QUAL-12 findings still held (TTS spoke raw text; WebAPI 500 on `self.processor`;
  `NumberTextProcessor.process()` bug; dead `_stage_providers`/`number_options`/normalizers config tree). User chose the
  full collapse. Built **`UnifiedTextProcessor`** — one config-driven provider that reads per-normalizer `stages` lists
  and applies a fixed-order chain (numbers → prepare → runorm) for the requested stage. Stages are now data, not classes.
  Deleted the 4 stage-specific providers (asr/general/tts/number) + their entry-points + 4 config schemas (→ one
  `UnifiedTextProcessorProviderSchema`); collapsed `config-master` + `TextProcessorConfig` onto the single `normalizers`
  tree (dropped the dead `[providers.*]` split + `number_options`). **Wired both stages:** `process(stage="asr_output")`
  for the ASR→NLU path; **added the missing `tts_input` normalization in `_handle_tts_output` before `synthesize_to_file`**
  — the actual TTS-correctness win (responses now get numbers→words/symbols normalization; RUNorm available, opt-in).
  Rewrote the 3 broken WebAPI endpoints onto the unified provider's `stage_map`/`normalizers_for_stage`. RUNorm now
  `enabled=false` by default (documented HF-model-download offline hazard). Verified: chains correct per stage, "5 минут"→
  "пять минут", disabled normalizers don't run; `test_text_processing.py` (5) + full suite 26/26; WebAPI boots (smoke).
  **Carve-outs:** optional `llm_text_processor` + the dead `universal_llm` ASR-enhance path → QUAL-15. **QUAL-13 done (Stages 1+2).**
- **QUAL-13 Invariant #4 — VERIFIED config-ui is schema-agnostic (user-prompted; corrected my earlier carve-out).** I had
  initially carved a config-ui text-processor-editor update to UI-5. Wrong: the config editing is fully schema-driven —
  `ConfigurationPage` fetches the backend Pydantic schema (`getConfigSchema()`) and renders each section through a
  generic recursive `ConfigSection` (renders the `providers` tree + nested `normalizers` dynamically; only a
  `text_processor`↔`text_processing` name alias is component-specific). The `TextProcessorConfig` TS type is already
  generic (`Record<string,Record<string,any>>`), so the collapsed shape matches. Changed zero config-ui files; ran
  `npm run type-check` **and** `npm run build` — both pass clean. So QUAL-13 carries **no** config-ui debt; Invariant #4
  satisfied for the config surface. (The donations editor UI-5 deferral is unrelated — that's the donations schema, not config.)
- **QUAL-13 Stage 1 + ASSET-3 DONE — lingua-franca → ovos-number-parser.** Investigated the abandoned MycroftAI git pin
  vs successors (research agent + WebSearch): irene's real usage is tiny (`pronounce_number` only; the stateless OVOS
  successor needs `lang=` per call, no global `load_language`), confined to `irene/utils/text_processing.py`, with a
  pure-Python Russian fallback as the default path. Migrated to **`ovos-number-parser>=0.5.1`** (maintained, PyPI,
  pure-Python → no armv7 concern); ru now routes through the **dependency-free** pure-Python path (proper Russian vs
  ovos's literal "точка", works on edge without the extra), non-ru → ovos (degrades to raw digits if absent). Threaded
  `language` into the regex callbacks via `functools.partial`; `load_language` → no-op; removed the git pin from
  pyproject + lock (`ovos-date-parser` not added — no date parsing needed). Verified ru+en number→words; suite 21/21.
  This is QUAL-13 Stage 1 (de-risk number normalization before the full provider-collapse); **closes ASSET-3**.
- **QUAL-30 [DFLOW] Grade-1 clarification DONE (deterministic responder).** Built the single fail-loud → explain-and-ask
  boundary that the QUAL-11 typed accessor was set up to feed. Reconciled first (Invariant #5/#8): the single catch
  point is `execute_with_donation_routing` (base.py:270 — it already wraps the routed method and maps everything to a
  generic error); `get_param` already raises but nothing caught it; the fallback intent carries a fake `confidence=1.0`;
  templates load per-enabled-handler only. **Implementation:** (1) `get_param` raises structured
  **`MissingRequiredParameter`** (param/description/intent); (2) the boundary catches the `ParameterExtractionError`
  family **before** the generic error → new base **`_clarify()`** → localized single-turn `IntentResult`
  (`success=True`, `metadata.clarification=True`, speaks); (3) deterministic responder via a new **system** template set
  `assets/templates/clarification/{ru,en}.yaml` — and taught `_load_templates` to load system sets unconditionally (not
  tied to an enabled handler), `get_template` handles language→default so **no language hardcoded**; (4) fixed the fake
  `confidence=1.0` → `0.0` (honest no-match; routing keys on `_recognition_provider`, verified safe — smoke's
  offline-conversation test still green). Verified both languages render; `test_clarification.py` (3) green; full suite
  21/21. **Scope (with user's text-first priority):** deterministic path is the offline guarantee = the must-have; **LLM
  phrasing deferred to QUAL-15** (the review frames LLM as the opt-in enhancement, and the LLM foundation is shaky per
  QUAL-14); **device/room → ARCH-6**; **per-handler activation → QUAL-34** (only timer uses the accessor today, with a
  caller default, so nothing triggers clarification in production yet — the mechanism is ready for the migration). Grade
  2 (multi-turn slot-filling) stays QUAL-31.
- **Filed QUAL-36 — single language source-of-truth; purge hardcoded language codes (user observation 2026-06-03).**
  User spotted a hardcoded `"ru"` in a handler and suspected it was systemic — verified: it is. Audit found `context.
  language or "ru"` at **63 handler sites** + `entity_resolver` ×2; context-ignoring hardcodes (`timer._get_language`
  re-detects + `return "ru"`, ignoring the NLU's detected language; `context.py:86` seeds sessions `"ru"`); a real
  **inconsistency bug** (`hybrid_keyword_matcher:422` defaults `'en'` vs everything else `'ru'`); `language="ru"` default
  params; baked `["ru","en"]` sets. **Target architecture (decided with user):** config declares **supported-languages +
  default** → the **session resolves language ONCE** (detection clamped to the supported list, silent fallback to default
  if unconfident/out-of-list) → **downstream just reads `context.language`** with NO fallback/re-detection/literals. The
  insight: don't relocate the default to 70 sites — make `context.language` an **invariant** and DELETE the fallbacks
  (theme ④ "a field means one thing end-to-end"). **Hexagonal (user-required):** config values are read at the
  composition root and **injected inward** (`ContextManager` gets `default_language` to seed with — same DI as its
  `max_history_turns`; NLU component gets supported-list+default to clamp detection); domain never imports config. The
  config fields already exist (`config/models.py:315-316`). User chose: seed-context-read-context-only + silent fallback.
  _Not yet implemented — filed for a focused pass._
- **Donation CHOICE-surface audit + correction (user observation; QUAL-29 migration quality).** Verified Russian
  `choice_surfaces` across all 30 CHOICE params / 14 handlers. Two findings, opposite directions:
  **(1)** The genuinely-missing-Russian bug (the timer-class) was only `timer.unit` — fixed in QUAL-11 Stage D. All
  other **user-facing** CHOICE params (datetime/system/quality/language-names/time-of-day) correctly carry Russian.
  **(2)** The migration's actual systematic flaw was the **inverse — it wrongly *translated* technical identifiers**
  (model/driver/service names, which per the user must **never** be translated; the canonical token is the spoken
  identifier and is self-matchable). Worst case: `speech_recognition.provider` had `azure→"облако"` (literal "cloud"),
  plus `whisper→виспер`, `vosk→воск`, `google_cloud→гугл`; `voice_synthesis.provider` had `silero→силеро`, etc.
  **Stripped both consumed provider params' `choice_surfaces` back to canonical** (English identifier). _Left alone:_
  the transliterations embedded in the **parked T2 `token_patterns`/`slot_patterns`** (inactive at runtime → QUAL-35
  decides whether ASR-transliteration aids belong there); `voice_synthesis.voice` (dead → QUAL-34, and `xenia`/`aidar`
  are real names «Ксения»/«Айдар» a Russian would actually say — a genuine nuance to decide when wiring it); the dead
  user-facing `system_service.metric_type` / `text_enhancement.correction_type` (→ QUAL-34 wire-then-author). **Authoring
  rule established: technical identifiers (models/drivers/services) stay canonical; only user-facing concept choices get
  localized surfaces.** Smoke green.
- **QUAL-9 [FAF] DONE — tail reconciled to metrics re-key + TEST-3; everything else already in QUAL-28.** Per the
  task-start reconciliation (Invariant #8), verified against current code that QUAL-28 had absorbed the entire F&F P0
  set AND most of the documented tail (timeout monitor `wait_for`, duplicate write-back processor deletion, timer-
  cancellation cleanup, capture-before-pop). The only genuinely-open items were the **per-action metrics re-key** and
  **TEST-3** (user-approved this narrowed scope before work). Fixed `metrics._active_actions`: keyed by the unique
  `(domain, action_name)` pair instead of `domain` alone — two concurrent same-domain actions (e.g. two timers,
  `domain="timers"`) used to clobber each other's metric, so completion popped the wrong one and the first leaked as
  perpetually-running. `record_action_completion` now takes `action_name`; updated all 9 callers (6 internal synchronous
  helpers + 3 F&F sites in `base.py`); `get_active_actions_summary` reads `action.domain`. Added the TEST-3 seed
  `test_metrics_concurrent_same_domain_no_clobber`. `test_set_timer_end_to_end` green end-to-end (QUAL-11 recognition +
  QUAL-28 F&F). Suite 18/18. **The QUAL-11 + QUAL-9 arc the user picked — timers working end-to-end — is complete.**
- **Decision (user) — QUAL-11 goes LIGHTWEIGHT (T1); the heavy NLU tiers split out. Filed QUAL-35; entity_type → ARCH-6.**
  Worked through the slot/extraction-pattern fork (P0 #2) and the entity_type fork (Q7b) together — they're the **same
  species** (heavy declarative extraction), and a three-tier picture clarified the call: **T1** = keyword/NER + regex +
  CHOICE surfaces + lemmas (what `hybrid_keyword_matcher`, the hot path, actually runs); **T2** = spaCy `Matcher`/
  `EntityRuler` slot-filling (the authored-but-discarded `token_patterns`/`slot_patterns`/`extraction_patterns`);
  **T3** = dependency-parse / local-LLM NLU. Key facts that drove it: the cascade is `[hybrid, spacy]` fast→slow with a
  0.7 gate, so **T2 lives only in the spaCy fallback** (hybrid explicitly ignores advanced patterns) — and all 66
  `entity_type` decls are `generic`, so entity_type dispatch would be an inert branch. T1 covers the easy ~80%; T2's
  sweet spot is real but narrow (compound durations "2 часа 30 минут"→150min, source/dest by preposition, multi
  param=value in any order, free-text spans, morphology at real-home scale); T3 (negation "кроме", anaphora "его",
  conditionals "если") is what **neither** T1 nor T2 reach. **User's call:** T2+T3 are a **must-have for smart-home/MQTT**
  (not overkill there) → **filed QUAL-35 `[PEX][MQTT]`** (T2 in the spaCy fallback + T3 via local-LLM; gated on ARCH-7/8;
  patterns **parked, not deleted** — optionality preserved, no authoring lost, no schema change so no UI-5 impact).
  **entity_type/room_context consumption + the heuristic swap (Q7b) → moved into ARCH-6** (activates with real
  room/device registration; ARCH-6 now explicitly owns authoring the non-generic types + the `_is_device/location_entity`
  → `entity_type` swap). QUAL-11 keeps only the safe cleanup (dedupe device path + `_resolution_failed`) and refocuses its
  remaining energy on the universal hot-path wins: shared extraction base + required-param contract + typed accessor.
- **QUAL-11 [PEX] Stage E — QUAL-22 (deleted dead disambiguation stub) + P1-t (`_create_error_result` de-shadowed). QUAL-11 lightweight scope COMPLETE.**
  **QUAL-22:** deleted `ContextAwareNLUProcessor._disambiguate_with_device_context` — it computed `enhanced_entities`
  (output_capabilities / context_suggestion / preferred_output_device) then `return intent` unchanged ("for now, return
  original"), dead since inception; the caller now uses the intent directly. Real capability/room-aware disambiguation
  needs registered devices → ARCH-6, not a no-op. Removed the 2 QUAL-22 xfail tests + `test_device_not_found_suggestions`
  (the latter asserted the `available_devices` suggestions from the Stage-C-deleted duplicate path). **P1-t:** 6 handlers
  shadowed the base `_create_error_result(text, error, metadata)` with an **incompatible**
  `_create_error_result(intent, context, error)` — a footgun (the same call meant different things per handler). Renamed
  all 6 to `_error_result(context, error)` (dropped the unused `intent`) across 31 call sites, so `_create_error_result`
  has **one** canonical signature project-wide; each handler keeps its own localized template body. Suite 17/17.
  **QUAL-11 done (lightweight T1 scope): Stages A–E.** Carve-outs tracked elsewhere: T2/T3 patterns → QUAL-35;
  `entity_type` swap → ARCH-6; per-handler `get_param` migration → QUAL-34.
- **QUAL-11 [PEX] Stage D — shared coercion base + typed `get_param` accessor; fixed a latent timer-unit bug.**
  (1) **Shared coercion (theme ②):** lifted the duplicated `_convert_and_validate_parameter` (identical in both NLU
  providers — the "two contracts" divergence) onto **`ParameterSpec.coerce()`** in `core/donations.py`; both providers
  now delegate, so the parameter surface is identical regardless of which won the cascade. (2) **Provider default-on-
  failure fix (P0 #3):** the hybrid extraction loop no longer silently drops a param when coercion raises — it applies
  the declared `default_value` (or leaves it absent for the accessor to enforce required), never swallows. (3) **Typed
  accessor (P1 #6):** added **`IntentHandler.get_param(intent, name, default)`** — finds the donation `ParameterSpec`
  (`_find_param_spec`), coerces via the shared base, applies the declared `default_value`, and raises
  `ParameterExtractionError` on missing-required-no-default (fail-loud → QUAL-30 clarification). One handler-boundary
  read replacing ad-hoc `intent.entities.get(...)` with bespoke defaults. (4) **Latent correctness bug found + fixed on
  the headline exemplar:** "поставь таймер на 5 минут" was silently creating a **5-second** timer — the timer `unit`
  CHOICE had **English-only `choice_surfaces`** (no «минут»/«секунд»/«час»), so unit never extracted, and the handler
  **hardcoded `'seconds'`**, ignoring the donation's `default_value="minutes"`. Authored Russian unit surfaces +
  adopted `get_param` in the timer handler (donation default wins). Verified: "5 минут"→unit=minutes, "30 секунд"→
  seconds; **hardened TEST-0** to assert the response says "5 мин" (not "5 сек"). Suite 17/17.
  _Remaining QUAL-11: `_create_error_result` unification (P1-t) + QUAL-22 (Stage E); the per-handler `get_param`
  migration folds into QUAL-34 (same handlers/files — consume the declared param via the accessor)._
- **QUAL-11 [PEX] Stage C — unified the duplicate device path, added `_resolution_failed`, made parked patterns honest.**
  (1) **Duplicate device resolution removed:** `ContextAwareNLUProcessor._resolve_device_entities` (a hardcoded
  English-only keyword path that re-resolved devices with a different strategy and wrote `{e}_device_id`/`_device_type`/
  `available_devices` keys **no handler reads**) deleted — the asset-driven `ContextualEntityResolver.resolve_entities`
  is now the single device/location/temporal/quantity resolution path. (2) **`_resolution_failed` markers:**
  `_resolve_single_entity` now returns `(result, attempted_kind)`; an entity classified as device/location that fails to
  resolve gets `{name}_resolution_failed=True` so the QUAL-30 clarification boundary can tell "unresolvable reference"
  from "never a resolvable entity" (verified: device-ish `target` marked, plain `topic` not). (3) **Parked T2 patterns
  made honest:** `spacy_provider._validate_and_store_spacy_patterns` now documents that `advanced_patterns` is
  validated-but-never-applied (the live contract is T1; T2 = QUAL-35), ending the silent validate-then-discard footgun.
  Heuristic `_is_device/location_entity` dispatch stays (the `entity_type` swap is ARCH-6). Maintained suite green (17/17).
- **QUAL-11 [PEX] Stage B — de-fatalized the entity resolvers (P0 #4).** `DeviceEntityResolver._load_device_types`
  and `LocationEntityResolver._load_location_keywords` raised uncaught `RuntimeError` ("fatal configuration error")
  when the asset loader wasn't wired or localization data was missing/empty — and the resolver is built **asset-less**
  (injected later in `post_initialize_coordination`), so any device/location utterance before/without successful
  coordination **aborted the whole request**. The location path was worst: `_load_location_keywords` is called
  unconditionally at the top of `resolve()`. Both helpers now **degrade best-effort** — warn-once + return `{}` —
  so resolve() skips the asset-dependent inference (device type-inference / "here"-inference) but exact/fuzzy
  name matching still works and the request proceeds. Verified: both resolvers return `None` (not raise) with a
  null asset loader; maintained suite green (17/17). _(`_resolution_failed` markers + duplicate-path unify are
  Stage C.)_
- **QUAL-11 [PEX] Stage A — fixed the timer recognition gap (root cause) + the phantom cascade defaults.
  `test_set_timer_end_to_end` flips xfail→PASS.** Reconciled QUAL-11 against current code first (Invariant #8):
  every P0/P1 still live as written (nothing silently fixed by QUAL-23/27/29) → valid, proceed.
  - **Root cause of the recognition gap (verified empirically, not the review's "threshold too high" guess):**
    a **Cyrillic normalization asymmetry** in `hybrid_keyword_matcher._normalize_text`. It applied
    `NFKD` + combining-mark stripping, which folds precomposed Cyrillic **«й»→«и»** and **«ё»→«е»** (`таймер`→
    `таимер`). But regex patterns are built from the **raw** donation phrase (`таймер`, with «й») and matched
    against normalized text — so `\bпоставь таймер\b` could never match `поставь таимер на 5 минут`. This
    silently broke recognition for **every** Russian phrase containing й/ё (а huge class: таймер, какой, мой…).
    Fix: normalize with **`NFC` (compose), no combining-strip** — patterns and text are symmetric again; English
    unaffected. (The NFKD+strip only ever provided Latin accent-folding, irrelevant for a RU/EN assistant.)
  - **Phantom cascade defaults (P0 #1):** `provider_cascade_order` defaulted to
    `["keyword_matcher","spacy_rules_sm","spacy_semantic_md"]` — all three non-existent; the
    `"keyword_matcher"` always-on fallback was phantom too. Repointed both to the real entry-points
    (`hybrid_keyword_matcher`, `spacy_nlu`). QUAL-23 only *asserts* these at startup; it never fixed the default,
    so a config omitting the order recognized nothing.
  - **Result:** the timer flow now works end-to-end (recognition this stage + F&F from QUAL-28); the TEST-0
    `test_set_timer_end_to_end` xfail is removed and now a real green assertion. Maintained suite green
    (smoke + action-store + import-contracts: 17/17). **QUAL-11 remains open** — Stage A is the recognition/
    cascade slice; the shared-extraction-base + required-param contract, resolver de-fatalization, entity_type
    consumption, typed accessor, `_create_error_result` unification, and QUAL-22 are the remaining stages.

### 2026-06-01
- **ARCH-0** — Architecture map + doc-harmonization audit + pattern review. → `docs/review/phase1_architecture_map.md`.
  Key results: module-level graph shows only **2 real cycles** (Phase-0's "giant SCC" was a package-grouping
  artifact); the #1 defect is the `intents/models.py` god-module (in-degree 67) forcing most backwards edges;
  `architecture.md` body is stale below its banner (fictional managers/endpoints/runners, TODO-vs-DONE);
  real data flow differs from docs (VAD is a segment-gate, NLU==Intent-Recognition, TTS text-path-only).
- **Goal 2 decision:** **Hexagonal (Ports & Adapters)** SIGNED OFF. Refined ARCH-1..6 + DOC-4/5/6.
- **DOC-6** — archived 5 stale plan docs (config_schemas, language_support, configuration_guide,
  PIPELINE_IMPLEMENTATION, irene_current) → `docs/archive/`.
- **DOC-5** — harmonized the contradicts-code docs (donation paths/schema, asset TOML nesting, train env
  prefix, voice_trigger YAML→TOML) + correction banners on the donation spec and universal_tts. Found a
  config-master train-schedule nesting bug → QUAL-7. Donation-spec full rewrite deferred → DOC-5b.
- **Macro-task intake (9 threads)** — analyzed and split into workstreams:
  1. [FAF] fire-and-forget review → QUAL-8/9, TEST-3, DOC-4 note.
  2. [PEX] parameter extraction → QUAL-10/11, TEST-4, DOC-7.
  3. config-ui-stays-functional → **Invariant #4** + DoR checkbox + BUILD-4→P1 ongoing gate.
  4. [DEDITOR] human-friendly donations editor → **new UI workstream** UI-1/2/3.
  5. [TXTPROC] text-processor review → QUAL-12/13, TEST-5.
  6. [LLM]/[PROMPTS] LLM usage + offline-first + prompt hardening → QUAL-14/15/16.
  7. [MQTT] smart-home output → ARCH-7 (design session) / ARCH-8; surfaces the missing output-port seam.
  8. [STREAMAPI] streaming-API exposure (hand-rolled AsyncAPI 2.6.0) → QUAL-17/18 (P2, must-before-release).
  9. [ESP32] ESP32 + wakeword (microWakeWord placeholder, training removed, TODO11 open) → QUAL-19/20 (keep/fix/cut).
  Cross-cutting sequencing: **QUAL-10 [PEX]** gates DOC-7 + UI-1/2/3; the reviews (QUAL-8/10/12/14) precede their
  refactors and **ARCH-1** (context split); Invariant #4 gates the contract-touching tasks; QUAL-12↔ASSET-3.
- **Invariant #5** added (review docs stay in sync) + a **Review-documents index** linking the plan to
  `docs/review/*` + `docs/design/*`. Completing a finding-derived task includes updating its review doc.
- **VOSK model re-audit (ASSET follow-up to ASSET-1).** Bumped VOSK **TTS** model `tts-ru-0.8-multi` →
  **`0.9-multi`** (latest; `1.0` is 404; size note 500MB→780MB). → `34f8e71`. Fixed a latent **ASR** bug: `en_us`
  pointed at the **full 1.8GB** `en-us-0.22` while labeled "42MB" under a "small models" comment → repointed to
  `vosk-model-small-en-us-0.15.zip` (40MB, verified live); full model kept under the `en` key (label corrected). → `a5189b6`.
  ASR versions otherwise already latest for the vosk runtime (small-ru-0.22, ru-0.42, de-0.21, es-0.42, fr-0.22).
- **Key discovery → motivates ARCH-9 [INFER].** The "newer" RU models on alphacephei (`ru-0.54`, `small-ru-0.52`)
  are **NOT vosk-runtime models** — empirically loading `small-ru-0.52` with our `vosk 0.3.45` fails
  (`model.cc:122 does not contain model files`); the dir is `encoder/decoder/joiner.int8.onnx` + `decode.py`
  importing `sherpa_onnx`. They are **sherpa-onnx Zipformer2** models needing a different runtime. So **do NOT
  bump the vosk URLs to 0.5x** (would break ASR) — but this surfaced that sherpa-onnx unifies ASR/TTS/wakeword/VAD
  on one ONNX runtime we **already ship transitively** (onnxruntime 1.22.1 via openwakeword + vosk-tts). Logged as
  **ARCH-9/10 [INFER]** (broad design session) with the constraint that whisper & silero remain first-class.

- **BUILD-1 DONE** (`bab6f97`). First actual run of the system post-revival. `uv sync --extra all` resolves/
  installs clean (353 pkgs; torch 2.7.1, vosk 0.3.45, spaCy, whisper, lingua-franca git dep all OK). `irene-cli
  --check-deps` → 5/5 components available. **WebAPI**: `irene-webapi` boots to uvicorn (workflow READY, 10
  routers, 104 OpenAPI paths); `POST /execute/command {"command":"привет"}` → 200 `greeting.hello` conf 1.0,
  real RU response — full spaCy-NLU→intent→handler chain works; graceful SIGINT shutdown clean. **CLI**: boots +
  shuts down clean; **bug found & fixed** — `--headless` set `nlu=False/text_processor=False` but the unified
  workflow requires `nlu` ("Required component 'nlu' not available"), so headless could boot but never execute a
  command; now enables nlu+text_processor (llm optional) and `--headless --command "привет"` returns a greeting.
  Cosmetics noted: QUAL-6 schema warning prints on every boot; CLI `--help` banner still says "v14" → folded into
  DOC-3. Not yet covered: Docker boot (BUILD-3), interactive REPL, audio/voice path (needs devices + models).

- **TEST-1 DONE / TEST-2 DOING** — first test-suite run post-revival. Added `[tool.pytest.ini_options]`
  (`asyncio_mode=auto` — unblocked ~23 async tests that errored as "not natively supported"; testpaths; silenced
  Pydantic V1 deprecation flood). Fixed broken refs: `ConversationContext`→`UnifiedConversationContext`,
  `Intent.text`→`raw_text`, `ComponentConfig.audio_output`→`audio`; skipped deleted-subsystem tests (TTLCache /
  perf-manager / removed `_handle_sample_rate_mismatch` seam, 13 skipped) with reasons; fixed a hardcoded
  `cwd='/home/.../Irene-Voice-Assistant'` test bug. Suite **100 failed→68 failed, 136→156 passed**. Commits
  `…`(asyncio+rename), `…`(skips+cwd), `…`(audio_output/Intent). **Prod bug surfaced → QUAL-21** (settings_runner
  + examples use removed ComponentConfig fields audio_output/microphone/web_api → would crash). Remaining 68 drift
  failures tracked in TEST-2; **TEST-6** added (rewrite ASR-fallback tests).

- **Strategy decision — stop repairing tests; rewrite post-ARCH/review; Docker last.** The TEST-1/2 pass took the
  suite from 136/100 to 166/56/13/2xf and banked the real value (it runs; found QUAL-21, QUAL-22, a trace-metadata
  fix). Continuing to fix the remaining 56 is throwaway work — those tests target pre-refactor code that ARCH-1..5
  + the QUAL reviews will invalidate. So **TEST-2 PAUSED** (partial safety net, remaining failures intentionally
  unfixed), and the real effort is **TEST-7: rewrite the suite once architecture + reviews land** (TEST-3/4/5/6
  folded in as coverage goals). **BUILD-3 (Docker) DEFERRED to the release phase** — image/extras/armv7 depend on
  the post-refactor shape (incl. ARCH-9/10 [INFER], QUAL-19/20 [ESP32]). Net active path now: **reviews +
  architecture**, then test rewrite, then Docker + release.

- **QUAL-10 [PEX] DONE** → `docs/review/parameter_extraction_review.md` (4-layer parallel deep-read + synthesis;
  6×P0/11×P1/12×P2). Headline: donation-driven extraction is largely aspirational — `slot_patterns`/`token_patterns`/
  `ParameterSpec.extraction_patterns` are validated-then-discarded **dead code**; spaCy param-extraction self-labels a
  "Phase-2 stub"; required-param errors never raise; the two providers extract with **divergent contracts**; entity
  resolvers **fatally crash** on asset-loader timing while the rest silently no-ops; and the **default
  `provider_cascade_order` names providers that don't exist** (only shipped configs setting it explicitly avoid total
  failure). Remediation ranked into **QUAL-11** (P0s first); confirms+absorbs **QUAL-22**; informs DOC-7, UI-1/2/3,
  TEST-4. Also explains the parked `test_cascading_nlu` failures (`_recognition_provider` vs bare `provider`).

- **QUAL-14 [LLM] DONE** → `docs/review/llm_usage_review.md` (3-layer parallel deep-read; 3×P0/9×P1/12×P2).
  **NLU confirmed LLM-free.** Headline: offline-first works for recognized intents, but the LLM stage's offline
  fallback is **fictional** — the `console` LLM provider doesn't exist (verified: no `console.py`, no entry-point),
  `fallback_providers` is never used at runtime (uses arbitrary `keys()[0]`), and `generate_response` re-raises
  offline; only the conversation handler's independent `is_available()` template-gate saves the pipeline. Also: ASR
  LLM-enhancement is dead code (`universal_llm` plugin lookup that returns None), `enhance_text` masks failures as
  success (failed translation returns untranslated input), prompts are triplicated inline + provider-language-locked
  (→ QUAL-16). **NLU-LLM decision: keep NLU deterministic/offline; LLM assist only opt-in + LOCAL, gated on
  ARCH-9/10 [INFER] + QUAL-11.** Remediation → QUAL-15.

- **QUAL-12 [TXTPROC] DONE** → `docs/review/text_processing_review.md` (3-layer parallel deep-read; 5×P0/6×P1/6×P2).
  Verdict: the subsystem is **decorative** — `process()` is hardcoded to stage `"general"` (verified), so only
  `general_text_processor` runs; `asr_output`/`tts_input` stages are never routed; **TTS gets raw text** (no call
  site — verified); the `[text_processor.normalizers.*]` config tree is dead; the WebAPI 500s on an unassigned
  `self.processor`; `number_text_processor` is a redundant unreachable dup of `asr_text_processor`. Recommendation →
  QUAL-13 **collapse to one config-driven processor + actually wire the two real stages**. **Added question
  answered:** LLM *can* back a text-processor (open interface + DI) but isn't wired (only the dead `universal_llm`
  path); should be **opt-in online-only**, augmenting the deterministic default, never on the default path. Surfaced
  a 3rd instance of the systemic **"configured names that don't resolve"** bug (dead stages here; phantom `console`
  LLM in QUAL-14; phantom cascade names in QUAL-10) → a shared startup-assertion fix.

- **QUAL-8 [FAF] DONE** → `docs/review/fire_and_forget_review.md` (3-layer parallel deep-read; 5×P0/8×P1/6×P2).
  **F&F is broken end-to-end** (verified): **timers crash on launch** (duplicate `session_id` kwarg → TypeError, only
  ValueError caught); the **domain-vs-action_name key mismatch** makes `remove_completed_action` always miss →
  `active_actions` leaks unbounded and completion/metrics/notifications (all nested in the failing `if remove...`
  block) never fire; completion callbacks call the **non-existent `get_or_create_context`**. Re-validated the 6
  legacy issues (1 FIXED, 1 fixed-but-moot, 2 changed-still-broken, 1 unreachable, 1 confirmed) — the Sep-2025 doc's
  "COMPLETED" is false (banner added). Remediation → **QUAL-9** (P0s first), then TEST-3. **This is the 4th
  "plumbed-but-dead" subsystem** (with QUAL-10/12/14) — a cross-cutting wire-up integration test + startup
  assertions would catch the whole class. **Review wave (QUAL-8/10/12/14) COMPLETE** — ARCH refactors unblocked.

- **Sequencing decided + encoded** (new "Sequencing" section). Review-wave P0s split into *surgical bug fixes*
  (architecture-independent) vs *refactor-flavored* (subsystem architecture work). Phasing: **Gate 0** = TEST-0
  (smoke net) + QUAL-23 (startup name-resolution assertion) → **Gate 1** = ARCH-1→2→4→5 (+DOC-4) → **Gate 2** = P0s
  by type (bug P0s ride the smoke net; refactor P0s ride the ports). Added **TEST-0** (P0, refactor safety net,
  distinct from the TEST-7 rewrite) and **QUAL-23** (P1, the cross-cutting fix for the 4×-observed
  "configured-name-doesn't-resolve" class). Rationale: no test net exists today + ARCH-1/2 move code, so a thin
  smoke harness gates the structural work; the name-resolution assertion is the cheap guard that catches most P0
  classes at once.

- **QUAL-23 DONE** (Gate 0 complete) → `irene/core/startup_validation.py` + wired in `core/components.py` +
  `irene/tests/test_startup_validation.py` (4✓). Startup assertion: every configured provider name
  (default/fallback/cascade + enabled provider blocks) must resolve to a registered entry-point. Non-fatal ERROR by
  default; `IRENE_STARTUP_STRICT=1` raises. On config-master it flags exactly the phantom `console` LLM (QUAL-15),
  zero false positives. TEST-0 still green. **Gate 0 (TEST-0 + QUAL-23) is now complete → Gate 1 (ARCH-1/2/4/5)
  unblocked.** Per Invariant #5, synced llm_usage/parameter_extraction/text_processing review docs (each now notes
  the startup guard; QUAL-15 not *done* until the startup ERROR clears).

- **ARCH-1 DONE** (`cdf8a81` + `a996dba`) — split the `intents/models.py` god-module (in-degree 67). IO primitives
  → `utils/audio_data.py` (dropped the `audio_helpers` TYPE_CHECKING band-aid); context types →
  `intents/context_models.py`; 45 importers re-pointed. **User-directed clean solution: NO TYPE_CHECKING** — context
  stays in the `intents` domain package (peer of `Intent`) with a real one-directional sideways import, so no cycle
  and no band-aid (deviates from the review's `core/` sketch, which would have inverted the dep). Verified: no
  cycle, full suite unchanged (176/55, zero regression), TEST-0 green. Per Invariant #5, synced
  `phase1_architecture_map.md` with the placement rationale. **Gate 1 underway: ARCH-2 next.**

- **ARCH-2 DONE** (`59f4ae8` + `044ff62`) — broke SCC-1 (config↔core / config↔components). validator→dynamic_loader
  (config→utils), schema-extraction cluster moved into AutoSchemaRegistry (auto_registry imports no component),
  import-time schema-validation side effect removed (no more "Schema warning" spam; runs once in load_config), and
  the `core/assets.py` AssetConfig TYPE_CHECKING band-aid dropped (clean downward import). config now has no upward
  imports. Verified: no cycle, full suite unchanged (176/55, zero regression). Per Invariant #5, synced
  `phase1_architecture_map.md` §2.1 (SCC-1 resolved). **Gate 1: ARCH-1 ✓, ARCH-2 ✓ — ARCH-3 next.**

- **ARCH-3 DONE** (`03fc44b`) — stop components importing delivery/tooling. Moved `web_api/asyncapi.py` →
  `api/asyncapi.py` (rank-0 port) so asr/tts components stop importing `web_api`; verified `analysis` is a clean
  driven adapter wrapped by `nlu_analysis_component` (classification for the ARCH-5 linter, no code change).
  Verified: full suite unchanged (176/55), TEST-0 green. Per Invariant #5, synced `phase1_architecture_map.md` §2.3.
  **Gate 1: ARCH-1 ✓, ARCH-2 ✓, ARCH-3 ✓ — ARCH-4 (formalize ports) → ARCH-5 (import-linter) next.**

### 2026-06-02
- **Audit (user) — "do handlers consume every declared param?" NO; filed QUAL-34.** Swept all 14 handlers (declared
  params from each `contract.json` vs whether the name is read in the handler `.py`). **19 of ~56 params across 11 of
  14 handlers are never read as `intent.entities[...]`** (7 CHOICE) — the QUAL-33 bug class is systemic. Two buckets:
  **A — genuinely dead** (feature not built; spot-confirmed `greetings.time_of_day`, `text_enhancement.improvement_
  type`, `system_service.metric_type`; `datetime` reads zero entities so all of its are dead) → wire-or-remove per the
  QUAL-33 precedent. **B — bypassed** (handler re-parses `intent.raw_text` instead of the NLU entity; spot-confirmed
  `voice_synthesis.voice` → `voice_name`) → folds into **QUAL-11** (typed accessor; QUAL-25 P1-r/P1-s). Recorded the
  full table in `docs/review/declared_param_audit.md`; filed **QUAL-34** `[release]` for the per-param triage. _Did not
  auto-fix — disposition is per-param (build vs stop-declaring), user's call._
- **QUAL-33 (system half) — wired `system.info_type`; canonical set reduced to `[system, performance]`. QUAL-33 DONE.**
  `_handle_info_request` now branches on `info_type` (was ignored). Per user, the canonical set was **reduced to
  `[system, performance]`** — `configuration` and `logs` REMOVED from the donation contract entirely ("no handlers, no
  donations"): there's no in-memory log buffer and the full system config isn't reachable from the handler, and the
  honest fix for "declares an option it can't serve" is to **not declare it**. `performance` renders real metrics —
  `get_metrics_collector().get_performance_summary()` (total_actions/success_rate/avg_duration) + uptime — via a new
  bilingual `performance` template (`system_handler/{en,ru}.yaml`); `system` (default) keeps the existing info template.
  Authored bilingual `choice_surfaces` for `info_type` (en: system/performance + synonyms like perf/metrics/stats; ru:
  система/производительность/нагрузка/…). Verified: template placeholders render (no KeyError); surfaces resolve
  ("производительность"→performance, "о системе"→system); donations schema-valid; smoke + store + contracts green.
  **QUAL-33 complete** (both halves). ru surfaces are a proposal pending native-speaker review.
- **QUAL-33 (datetime half) — wired `datetime.format`; the handler now honours its declared CHOICE param.**
  All three datetime handlers (`current_time`/`current_date`/`current_datetime`) read `intent.entities["format"]`
  (canonical, normalised by the NLU) and branch: time → 12hour (`12:40 AM`) / 24hour (`00:40`) / verbose (the natural
  template, default); date → short (locale numeric) / iso (`2026-06-03`) / full=verbose (template, default); datetime →
  iso (ISO-8601) / unix (epoch) / readable (compact) / verbose (default). Non-verbose paths return before the locale
  template (no asset-loader dependency). **Authored bilingual `choice_surfaces`** for all format params in `datetime_
  handler/{en,ru}.json` (e.g. `24hour` ← "24 hour"/"24-hour"/"military" · "24 часа"/"24-часовой"; `verbose` ←
  "in words" · "словами"/"прописью") — this is what makes the format reachable (QUAL-29's matcher extracts CHOICE via
  surfaces, not the placeholder `.*` patterns). Verified: "24 часа"→24hour, "словами"→verbose; handler renders each
  format. Lang files still schema-valid; smoke + store + contracts green. _Russian surfaces are my proposal — flag for
  review._ Remaining: the system.info_type **full feature** (real per-category content — user-approved scope).
- **QUAL-29 Stage G (backend) — REST API + loader fully retire the v1.0 per-language-with-params concept. QUAL-29
  backend DONE; config-ui editor rebuild carved to UI-5 (user-approved Invariant #4 deferral).** User chose to retire
  the old concept properly rather than ship a compatibility shim, accepting the config-ui donations-editing page breaks
  at runtime now (it still BUILDS — the frontend compiles against its own `api.ts`). **Loader:** added the v1.1 editing
  API — `get/save_contract` (neutral core) + `get/save_language_phrasing` + `validate_contract_data`/
  `validate_phrasing_data` (against the v1.1 schemas); **retired** `get/save_donation_for_language` (which did
  `HandlerDonation(**lang_file)` → crashed under v1.1); fixed `get_available_languages_for_handler` +
  `get_all_handlers_with_languages` to exclude `contract.json` (was surfacing "contract" as a language);
  `validate_cross_language_consistency` reworked to method-phrasing completeness (parameter parity is structural now).
  **REST (`intent_component.py`):** added `GET/PUT /donations/{handler}/contract`; the per-`{language}` GET/PUT/validate/
  create endpoints now serve/accept **phrasing-only**; `GET /donations/schema` returns **both** v1.1 schemas
  (`{contract, language}`); **removed** the dead `POST /donations/{handler}/sync-parameters`. Verified: editing
  round-trip works (contract 7 methods, ru phrasing has no params-with-type, both validate clean); smoke + store +
  contracts green. **Remaining Invariant #4 obligation = UI-5** (rebuild the config-ui donations editor on the v1.1
  split: contract editor + phrasing editor + choice_surfaces/entity_type/room_context editors; coordinate with
  UI-1/2/3 — one redesign, not two). QUAL-33 (datetime/system handler-wiring) still pending.
- **QUAL-29 scope clarification (user) — REST API = unfinished Stage G; datetime gap filed as QUAL-33.** User flagged
  that the donation **REST API still serves v1.0 concepts** and the datetime gap is unclosed. Grounded both: the REST
  surface (`get_donation_schema` → `assets/v1.0.json`; the per-`{language}` GET/PUT/validate/create/delete treating a
  lang file as a full donation-with-params; the dead `sync-parameters`; loader `get/save_donation_for_language`) is the
  **config-ui/Invariant #4 obligation = QUAL-29 Stage G** — QUAL-29 stays `[~]` until it lands (documented explicitly in
  `qual29_choices_decisions.md` Stage G). The **datetime gap is a distinct handler bug** (datetime.py reads no entities,
  so its declared `format` is dead) — filed as **QUAL-33** (with system.info_type, same class: handlers ignoring declared
  CHOICE params + authoring the deferred ru surfaces the validator already flags). Not part of the format split; doable
  standalone.
- **QUAL-29 Stages E + F — validator shrink + v1.1 JSON schemas. Smoke green.** (E) Rewrote
  `cross_language_validator` for v1.1: parameter parity is now structural (single-source contract) so
  `validate_parameter_consistency` was repurposed to **CHOICE surface completeness** (flags canonical tokens lacking
  per-language surfaces — correctly surfaces the deferred datetime.format/system.info_type gaps); `sync_parameters_
  across_languages` is now a **no-op** (nothing to sync); `validate_method_completeness` + `suggest_translations`
  reworked to read the v1.1 raw structure (contract method list + per-language phrases). Report dataclass shapes kept
  so the 3 config-ui REST endpoints stay stable (Invariant #4). (F) Wrote `assets/donation_contract_v1.1.json` +
  `assets/donation_language_v1.1.json` (the schemas the migrated `$schema` keys reference) and wired
  `_validate_donation_schema` into the loader (guarded by `validate_json_schema`, graceful if jsonschema absent).
  Verified all **14 contracts + 28 language files validate** against the schemas, and they're now enforced at load.
  Remaining (QUAL-29): config-ui (Stage G, Invariant #4) + dead-param handler-wiring follow-ups (Stage H).
- **QUAL-29 Stage D — extraction surface→canonical normalization. Smoke green.** Added
  `ParameterSpec.surface_to_canonical()` ({surface_lower: canonical}, all languages; canonical maps to itself).
  Rewrote the 4 CHOICE consumption spots — `hybrid_keyword_matcher` (fuzzy) + `spacy_provider` (similarity), both
  match + validate — to match against the SURFACE forms and **emit the canonical token**, normalizing any surface to
  canonical before validation. Threaded `choice_surfaces`/`entity_type` through the spaCy param-spec serialize/restore
  cache (else a cache round-trip dropped them). Now the handler always receives the language-neutral value regardless
  of spoken language — verified: `"доброе утро"`→`morning`, `"вечером"`→`evening`, `"good morning"`→`morning`. This
  activates the canonical model and centralizes the RU→EN normalization that handlers like `provider_control` did
  by hand. Remaining (QUAL-29): validator shrink, v1.1 JSON schemas, config-ui, dead-param handler-wiring follow-ups.
- **QUAL-29 backend Stages A–C — model + migration + loader (v1.0→v1.1 split). Smoke green.** (1) **Model**
  (`donations.py`): added `EntityType`/`RoomContext` enums, `ParameterSpec.entity_type` (default generic) +
  `choice_surfaces` ({canonical: [surfaces]}), `MethodDonation.room_context` (default none); `choices` redefined as the
  **canonical** (language-neutral) token list; schema_version → `1.1`. (2) **Migration** (`scripts/migrate_donations_v11.py`):
  split all 14 handlers into `<handler>/contract.json` (neutral core) + `<handler>/{en,ru}.json` (phrasing); encodes the
  5 CHOICE cases + auto-derives the 6 clean-parallel surface maps; **fixed 2 latent data bugs** — ru `handler_domain`
  localised to Cyrillic (`таймер`/`случайно` → canonical ASCII) and the divergent CHOICE sets per the recorded
  decisions. (3) **Loader** (`intent_asset_loader.py`): `_load_language_separated_donations` now loads contract+lang as
  raw JSON and `_assemble_v11_donation` merges them — neutral core from the contract, phrasing **accumulated across
  languages** (phrases/lemmas/token_patterns/extraction_patterns/aliases/examples — **fixes the old
  first-language-wins drop** where ru patterns were silently discarded), `choice_surfaces` assembled as
  {canonical: [canonical]+all-language-surfaces} so the canonical token is always self-matchable. `convert_to_keyword_
  donations` threads `entity_type`/`choice_surfaces` to the NLU. Verified: all 14 handlers assemble valid donations;
  greetings `time_of_day` → `{morning:[morning,утро],…}`; translation `target_language` → free entity. **Remaining
  (this task):** extraction surface→canonical normalization (hybrid + spacy), validator shrink, v1.1 JSON schemas,
  config-ui (types/AJV/editors), + follow-up tasks for the dead-param handler wiring (datetime.format, system.info_type).
- **QUAL-29 STARTED — donation format split; 4 design decisions locked with user (Invariant #5/#8 reconciliation).**
  Verified the task is valid as written: the language-neutral `ParameterSpec` core (`name`/`type`/`required`/`choices`/
  `min_value`/`max_value`) IS physically duplicated across `<handler>/en.json` + `ru.json` (28 files, 14 handlers), and
  is **already diverging** (e.g. `timer.set` `message.default_value` is absent in en but `"Таймер завершён!"` in ru).
  The loader's `_merge_language_donations` silently takes params/`token_patterns`/`slot_patterns` from whichever
  language iterates first — a latent "first-language-wins" bug. **Decisions:** (1) **Layout** =
  `<handler>/contract.json` (neutral) + `<handler>/{en,ru}.json` (phrasing), joined by `method_name#intent_suffix` +
  param `name`. (2) **Tie-break = Russian wins** on any en/ru divergence in a neutral field (primary language; also
  resolves the first-wins bug deterministically). (3) **`default_value` is per-language** (language-specific default
  text is real; canonical defaults repeat harmlessly). (4) **Scope change — heuristic deletion moved QUAL-29 → QUAL-11.**
  `entity_resolver._is_device_entity`/`_is_location_entity` are LIVE (`nlu_component.py:38/62`), and their
  entity_type-driven replacement is the Q7b typed accessor (QUAL-11). QUAL-29 only ADDS the `entity_type` (default
  `generic`) + `room_context` (default `none`) declarations; QUAL-11 swaps the resolver atomically. QUAL-29 stays
  first (it provides the contract QUAL-11 consumes — confirmed the dependency direction with the user). Field
  partition (neutral vs per-language) mapped from the timer donation: neutral = intent_name_patterns, action_domain_
  priority, method name/suffix/boost/room_context, param name/type/required/choices/min/max/pattern/entity_type;
  per-language = phrases/lemmas/token_patterns/slot_patterns/negative_patterns/stop_command_patterns/action_patterns/
  examples + per-param description/extraction_patterns/aliases/default_value.
- **QUAL-28 Stage 4 — history windowing; one list, one writer, one method. QUAL-28 now fully DONE (all 4 stages).**
  The dataflow review's P1-q (conversation turn modeled 2–3× per request) traced to three writers over two parallel
  lists: the orchestrator's `add_user_turn`+`add_assistant_turn` (`orchestrator.py:297-298`, which also wrote
  `conversation_history` via `add_to_history`) **and** the workflow's `add_to_history` (`voice_assistant.py:411`) — so
  every turn was recorded twice, and `history` vs `conversation_history` were redundant copies. Collapsed to a single
  model: **(1)** deleted the legacy `history` field + `__post_init__` copy; **(2)** replaced `add_to_history` with the
  one canonical writer **`record_turn(user_text, response, intent)`**, called **once** at the workflow level (the only
  `orchestrator.execute` caller is `voice_assistant`, immediately followed by `record_turn` — verified no other
  intent-processing path needs its own write); **(3)** removed the orchestrator's parallel turn-write; **(4)** wired
  **`max_history_turns`** — `record_turn` and the LLM-history-restore now trim to the configured window instead of a
  hardcoded `[-10:]` (kills the P2 "config-that-lies": the field existed but was ignored). Deleted the now-dead
  `add_user_turn`/`add_assistant_turn`/`_trim_history`/`get_recent_context` on the context, plus **5 dead
  `ContextManager` methods** (`add_user_turn`/`add_assistant_turn`/`get_conversation_history`/
  `process_intent_with_context`/`update_context_with_result` — all confirmed zero-caller repo-wide) and the now-unused
  `Intent`/`IntentResult` imports in `context_models.py` + `context.py`. Stat readers (`context.py` ×2, `system.py` ×2)
  repointed `.history` → `.conversation_history`. _Boundary note:_ `max_history_turns` is settable via
  `ContextManager(max_history_turns=…)`/`.configure()`, but is **not** yet a `config-master.toml` key — exposing it as
  config is a config-ui-gated change (Invariant #4), out of this stage's "make the field functional" scope. Smoke + 10
  store tests + import contracts green; scope guard clean.
- **Invariant #9 added — no `TYPE_CHECKING` import guards (+ QUAL-32 to sweep the residue).** User flagged
   `TYPE_CHECKING` as a no-go for this project: it's a band-aid for an import cycle, and a cycle violates the
   inward-pointing hexagon (Invariant #3) — fix the cycle, don't hide it from the runtime; and hard deps like
   `pydantic` are never optional so guarding them is pure ceremony. Codified as **Invariant #9**. Cleared the two
   files in this session's touch surface: `conversation.py` + `timer.py` both guarded `from pydantic import BaseModel`
   (used only in `get_config_schema(cls) -> Type[BaseModel]`) — hoisted to a plain top import, de-stringized the
   annotation; both schemas still resolve (`ConversationHandlerConfig` / `TimerHandlerConfig`). Filed **QUAL-32** for
   the ~13 remaining files repo-wide. Smoke + store + contracts green.
- **QUAL-28 Stage 3b — retired the `ContextLayer` indirection; conversation handler consumes context directly.**
  Invariant #8 caught the map-agent's claim that `ContextLayer` was already dead — a grep showed it was *live*,
  used only inside `conversation.py` via `resolve_layered_context`/`get_contextual_summary`. So the scope became
  migrate-then-retire (not "already gone"). Rewrote the conversation handler's context **consumption** to use direct
  model accessors (`room_name`/`available_devices`/`get_thread_summary`/`active_actions`/`recent_actions`/
  `conversation_history`/`state_context`) instead of the layered-resolution dict-walking: `_build_progressive_context_
  summary` + `_get_context_coordination_summary` rewritten, `_summarize_context_layer` deleted, `context_layers_used`
  now counts present slices via a `sum([...])`. Then deleted the now-unreferenced machinery from `context_models.py`:
  the `ContextLayer` enum + `resolve_context`/`_resolve_session_context`/`_resolve_thread_context`/`_resolve_action_
  context`/`_resolve_intent_context`/`resolve_layered_context`/`get_contextual_summary` (~115 lines). Note: only the
  context *assembly* moved here — the LLM prompt/provider logic stays in QUAL-15/16. Smoke + 10 store tests +
  import contracts green; scope guard clean.
- **QUAL-28 Stage 3.3 — completed the field split properly (correcting the earlier "subsumed" overstatement).** On
  challenge, re-audited the context fields: the lifetime-critical `active_actions` relocation was done, but
  `recent_actions`/`failed_actions`/`action_error_count` were **still on the transient context** (died on eviction,
  contra the Q3 action-store design) and a dead `memory_management` config blob (for the deleted MemoryManager)
  remained. Both now fixed: **(a)** the completed-action history moved into the `ClientRegistry` store
  (per-`physical_id`, capped 10 recent / 20 failed; recorded once by the F&F done-callback — the single completion
  chokepoint), exposed on the context as read-only properties — so it **survives session eviction** (new test:
  history visible to a freshly-recreated context for the same scope). **(b)** the dead `memory_management` field
  deleted (no consumers). `remove_completed_action` simplified to active-store removal only (no double-counting).
  Now ALL F&F state (active + history) is in the long-lived store; the context is the transient session with views.
  10 store tests + smoke + contracts green.
- **QUAL-28 Stage 3.3 — context field split assessed as SUBSUMED (Invariant #8).** _[Superseded by the entry above —
  the assessment was an overstatement; recent/failed-action history and the dead memory_management blob were genuine
  residuals, now fixed.]_ The Q2 goal (long-lived
  physical-identity store vs short-lived conversation session) is achieved by the store-relocation: `active_actions`
  (the state that must outlive the conversation) now lives in the `ClientRegistry` store and survives session
  eviction. The residual identity fields on the context (`client_id`/`room_name`/`available_devices`/`language`) are
  request-hydrated each turn — not long-lived state needing a separate store (ARCH-6 populates them into
  `ClientRegistry`). The conversation session (history/state) stays on the now-transient, idle-evicted context. A
  formal dataclass split would be cosmetic field-grouping with no behavior change and real risk (35-importer surface),
  so it's **not done** as a separate refactor. **3.3 substantively complete** (resolver physical_id · kill
  extract_room · eviction-unify · non-creating-get · field-split subsumed). Remaining QUAL-28: 3b (conversation
  context-assembly + retire ContextLayer) + 4 (history windowing).
- **QUAL-28 Stage 3.3 — non-creating `get` split.** `get_context` is now non-creating (returns the existing,
  non-expired context or `None`, no side effects) so a blank/typo'd session id can't silently spawn a shared session;
  `get_or_create_context` is the canonical (and only) creator. Migrated all 11 callers that need a context to
  `get_or_create_context` (the 9 internal context.py mutators + the text-processor and /nlu API endpoints, whose
  "NO CREATION" comments were aspirational — the old `get_context` always created). Imports + contracts + smoke +
  store tests green (15 passed).
- **QUAL-28 Stage 3.3 — kill `extract_room_from_session` + eviction-unify.** Removed the lossy
  `extract_room_from_session` heuristic (P1-o) and its only consumer `get_session_type` (both unused externally); room
  identity now comes only from the explicit `RequestContext` fields (Q2; ARCH-6 populates them) — the Priority-2
  session-id parse in `get_context_with_request_info` is gone. **Eviction unified** on a new `_effective_last_active`
  = `max(last_updated, last_activity)`; all three checks (the get_context inline check, the lazy
  `_cleanup_expired_sessions`, the background `_is_context_expired`) now use it, so a session kept alive via one clock
  but not the other is never evicted prematurely (P1-p). Imports + contracts + smoke + store tests green (15 passed).
- **QUAL-28 Stage 3.3 (start) — contextual resolver reads the store by `physical_id`.** `resolve_contextual_command_
  ambiguity`/`_resolve_contextual_command_internal` now take `physical_id` (not `session_id`) and read live actions
  straight from the action store — no `self.sessions[session_id]` lookup — so a "стоп"/"pause" still resolves **after
  the conversation session has been evicted** (the action outlives the session). Orchestrator passes
  `resolve_physical_id(client_id, room_name, session_id)`. This closes F&F eviction-survival on the read side (the
  write side was already store-backed). Import contracts + smoke + store tests green (15 passed). (The old
  `test_phase4_*` callers pass `session_id` — they're in the intentionally-unfixed pre-refactor suite, TEST-7.)
- **QUAL-28 Stage 3.2 — dead-code cleanup + timer simplification.** Removed the orphaned
  `workflow_manager._process_action_metadata_integration` + base.py `_handle_action_completion`/
  `_update_context_on_completion`/`_validate_action_metadata`. **Timer rewritten store-centric:** the old
  `_create_timer_action` *returned immediately* and spawned a nested `timer_callback` task that fired *another* F&F
  notification + kept a parallel `active_timers` dict — so with the store the timer's ActionRecord completed instantly
  and was reaped (timers never actually persisted). Replaced with `_run_timer` = a plain `sleep(duration)` + announce
  that **is** the store task; dropped `active_timers` and the 6 nested/helper methods; migrated all 7 handlers
  (set/cancel/stop/pause/resume/list/status) to read/cancel via `context.active_actions` + `cancel_action`. set_timer
  launches with `timeout = duration + grace` so the monitor never pre-empts; list/status read remaining from the
  store's `expected_end` (now exposed on the `active_actions` view). Minor accepted simplifications: a specific-id
  cancel cancels the domain (single-timer common case); pause/resume are status-flags only (a sleeping task can't truly
  pause — the prior impl was likewise cosmetic); list no longer shows the per-timer message. Smoke + store tests green.
- **QUAL-28 Stage 3.2 — reader migration (the store is now the F&F source of truth).** `context.active_actions` is
  now a **read-only property** over the `ClientRegistry` action store (keyed by the context's `physical_id`), so every
  reader auto-migrates — orchestrator (contextual interception), `context.py` resolver, conversation summary, NLU
  injection, trace snapshot, debug — all now read the store. The write/cancel methods (`add_active_action`/
  `remove_completed_action`/`cancel_action`/`update_action_status`/`has_active_action`/`get_active_action_domains`)
  are **store-backed** (cancel = cancel the task → the done-callback reaps it). Removed both write-backs
  (`voice_assistant._process_action_metadata` + `workflow_manager._process_action_metadata_integration` call sites)
  since the launch registers directly. Actions now **survive conversation-session eviction** (they live in the store,
  not the session). Import contracts + smoke + 9 store tests green (15 passed). **Cleanup left for a later pass (dead,
  uncalled):** `workflow_manager._process_action_metadata_integration` body + base.py `_handle_action_completion`/
  `_update_context_on_completion`. **3.3 refinement:** make the `context.py` resolver read the store by `physical_id`
  directly (today via the session context — works while the session is alive; true eviction-survival on the read side
  needs the physical_id pass-through).
- **QUAL-28 Stage 3.2 — store-centric F&F machinery (launch/completion/timeout) rewritten.** Per user, done
  store-centric (no session-threading), not the rejected `tracking_session_id` patch. `execute_fire_and_forget_*`
  now: resolves `physical_id` from the context, registers an `ActionRecord` **with the real task** in the
  `ClientRegistry` store, and the done-callback **reaps from the store** + fires metrics/notifications **off the
  record** (no `get_or_create_context` session lookup). Identity params are **keyword-only**, so the dup-`session_id`
  crash is fixed **by removal** — an action coroutine's own `session_id` kwarg now flows through (`_create_timer_action`
  case). Timeout monitor uses `wait_for` not flat-sleep; completion tasks held to avoid the orphan-GC bug.
  `mini-TEST-3` lifecycle test added (launch → store has it (live task) → completion reaps it; + the no-collision
  case). **Transitional:** old `context.active_actions` is still populated by the existing write-back (readers
  unchanged → no regression) while the store is now the real source of truth. **Next:** migrate readers
  (orchestrator/`context.py` resolver/conversation/nlu) to the store by `physical_id`; remove `context.active_actions`
  + the write-back + the now-dead `_handle_action_completion`/`_update_context_on_completion`. Import contracts +
  smoke + 9 action-store tests green.
- **QUAL-9 → QUAL-28 MERGE (user, Invariant #8).** Tracing the 3.2 relocation surfaced that (a) readers must hit the
  store by `physical_id` *independently of the session* to get eviction-survival (not a context façade), and (b) the
  authoritative liveness = the task ref, which is created in the F&F **launch** (`base.py`) — QUAL-9 territory. The
  QUAL-28/QUAL-9 split is artificial at that seam, so the **launch + completion** fixes move into QUAL-28 stage
  3.2/3.3 (one clean pass over `base.py`, fully testable via mini-TEST-3). QUAL-9 re-scoped to its tail (metrics
  re-key, delete the duplicate write-back, timeout monitor, timer-cancel cleanup, TEST-3). Ledger entries updated.
- **QUAL-28 Stage 3.1 — action-store skeleton (additive, nothing consumes it yet).** Added to `ClientRegistry`: an
  `ActionRecord` (action_name identity · domain index · live task ref · TTL) and a **runtime-only, non-persisted**
  action store keyed by `physical_id → action_name`, with the **4 reaper layers** (completion-remove · read-time
  liveness filter · periodic sweep · TTL + per-identity cap). Added the **`resolve_physical_id(client_id, room_name,
  session_id)`** seam (client_id > room > session; the one function ARCH-6 flips). New `tests/test_action_store.py`
  (8 tests, all green) — the bottom-up start of mini-TEST-3. Smoke unaffected. Next: 3.2 relocate `active_actions` +
  wire consumers.
- **QUAL-28 Stage-3 design decisions (with user) — incl. the Q1 room/device timing.**
  - **Q1 (room/device story timing):** the room/device story **activates at ARCH-6** (the WS/ESP32 `ClientRegistry`
    registration handshake that *populates* room/client/devices). QUAL-28/29/11 make everything **"room-ready"** (the
    store + context split with device fields, declarative `entity_type`/`room_context`, gracefully-degrading device
    resolvers) — none require a populated room. The whole thing pivots on a single **`resolve_physical_id(request)`**
    seam: today it returns the session-derived id; **ARCH-6 changes only that one function** to return the registered
    `client_id`/room → clean *activation*, not a re-refactor. ARCH-6 gets its design session **after the Gate-2
    foundation (QUAL-28/29/11) stabilizes** (one of the 3 design-gated threads ARCH-6/7/9). ARCH-7 (MQTT) acts on it.
  - **Q2 (action-store home):** **`ClientRegistry`** is the home, realized as a **runtime-only (non-persisted) sub-store**
    keyed by `physical_id` — *not* a field on the persisted registration record (it holds live `asyncio` task refs and
    must never serialize or survive a restart). `ClientRegistry` = persistent registration table (devices/room) + this
    runtime state table (`active_actions` + task refs); the reaper operates on the runtime table; JSON persistence
    ignores it.
  - **Sequencing (decoupled from ARCH-6):** the store + reaper + eviction-survival land **now** keyed by the
    best-available stable id; room/device keying upgrades transparently when ARCH-6 lands. Documented on the QUAL-28 +
    ARCH-6 ledger entries.
- **QUAL-28 Stage 2 — session-id hygiene.** Forbid the literal `"default"` at the `RequestContext` chokepoint
  (`"default"`/empty → derive a real id; P0-6 collapse fixed); the 3 `workflow_manager` entries default to `None` and
  **re-read `context.session_id`** so the local var reflects the derived id (it's reused by the action-metadata
  write-back). Added a real `ContextManager.get_or_create_context` → the 5 phantom callers (base.py/notifications/
  debug_tools) that were `AttributeError`-ing now resolve. Smoke green. **Scope (Invariant #8):** eviction-unify, the
  non-creating-`get` split, and `kill extract_room_from_session` moved to Stage 3 (they need the timestamp-touch audit /
  caller migration / room-as-field from the restructure). **NEXT: checkpoint, then Stage 3 (the structural cut).**
- **QUAL-28 STARTED (staged) — Stage 1: deleted dead `MemoryManager`.** Removed the module + all 7 `monitoring_component`
  wiring sites (init/shutdown/status/2 debug endpoints/accessor/providers-info) + the unused `MemoryStatusResponse`
  import. Confirmed dead first (only consumer was monitoring; called non-existent context methods). Smoke green.
  Staged plan recorded on the ledger (① MemoryManager ✓ → ② session-id hygiene → ③ context model + action store + a
  mini-TEST-3 → ③b migrate consumers + retire ContextLayer → ④ history windowing); checkpoint with user before ③.
  **Invariant #8 catch:** the map agent + Q4 claimed `ContextLayer`/progressive-context was dead — verification showed
  it's **live in `conversation.py`** (LLM context summary). Re-scoped to **migrate-then-retire in §3b** (user-approved);
  review finding annotated. Dead `memory_management_enabled` config key deferred to Q9 (config-ui coord).
- **QUAL-27 DONE — data-contract fixes** (commits `cebb77e` + 2 follow-ups). `Intent.text`→`raw_text` sweep (14
  sites + orchestrator; P0-1 command-surface crashes gone); NLU stamps `raw_text` = original utterance via a
  boundary override in `nlu_component.process(original_text=)`; `WakeWordResult.word` rename (P1-b); **deleted
  `Intent.session_id`** (field + 6 ctor kwargs + metrics read → `context.session_id` + fallback param);
  `IntentResult.__post_init__` enforces `success=False ⟹ error` (P1-a, one backstop over ~35 sites). Smoke green
  throughout. **Scope change (Invariant #8, user-approved):** P1-t (`_create_error_result` unification) found to be
  **6 handlers not 2** + a shared-bases concern → moved to **QUAL-11**; review finding annotated. **NEXT: QUAL-29
  (donation split) + QUAL-28 (context/action refactor) — the Gate-2 foundation.**
- **Invariant #8 added — task-start reconciliation** (user). Before starting any task, reconcile it against
  `RELEASE_JOURNAL.md` + the current code (not just the ledger/review doc per #5): classify valid / partially-done /
  fully-done-obsolete / scope-drifted, and **consult the user before any scope change** — no silent stale/redundant
  work. Important given Gate-2's interdependent tasks (QUAL-27/28/29 will pre-touch QUAL-9/11/13).
- **Doc-architecture restructure + scope-drift guard** (`cdd2dab`) — separated the three concerns into one home each:
  `RELEASE_PLAN.md` = task ledger (scope+status), new `RELEASE_JOURNAL.md` = the one journal, `docs/review/*` = frozen
  evidence (bannered). Refined Invariant #5 to a single status home; added #6 (single ledger + `[release]`/`[deferred]`
  tagging + ship-gate) and #7 (one journal). Added `scripts/check_scope.py` (orphan findings / dead links / unindexed;
  green at 72 tasks).
- **Uncaptured-work audit + ARCH-11/12 added** — audited all 8 review docs vs the ledger: **0 genuinely uncaptured
  findings** (all map direct or as defensible roll-ups). The only work living solely in a review doc were 2 benign
  phase1 residual edges → captured as **ARCH-12** `[deferred]` (`utils.vad→core.metrics`, `utils.logging→config.models`)
  to close the Invariant-#6 gap. Per user, **revoked the ARCH-5 reclassification** of the `core→inputs/workflows/
  components.base` edges as "legitimate" → **ARCH-11** `[release]` will fix them via DI/ports + add the import-linter
  contract (slotted after ARCH-6 + QUAL-28, taking today's input-adapter + context-refactor decisions into account).
- **QUAL-26 DONE — review-of-reviews complete** → `docs/review/dataflow_reconciliation.md`. Live Q&A, **10 issues
  decided** (committed per-decision so it was interruption-safe). Gate 1.5 closed. Key intended-vs-today calls:
  **(Q1)** `raw_text` = original utterance (fixes P0-1); **(Q2)** **Model 2 — split identity from session**
  (long-lived physical-identity store for `active_actions`+devices vs short-lived idle-window conversation session);
  **(Q3)** dedicated zombie-resistant `action_name`-keyed action store; **(Q4)** delete MemoryManager/ContextLayer/
  Intent.session_id, **WebSocket = primary ESP32 transport** (reframes ARCH-6); **(Q6)** declarative device/room via a
  **donation format split** (language-neutral contract + per-language phrasing; `entity_type` + tri-state
  `room_context`); **(Q7)** fail-loud → conversational **clarification** (configurable LLM/deterministic) + typed
  donation-driven accessor; **(Q8)** shared bases (one extraction base / one prompt source = LLM-indep hardening / one
  normalization seam containing the `lingua_franca`+`Runorm` debt); **(Q9)** deployment-aware config-truth (config-master
  is a valid superset); **(Q10)** hybrid framing — **4-theme principles block + discrete tasks QUAL-27..31.** Surfaced a
  4th cross-cutting theme (**data-contract integrity**). Per Invariant #5, plan + both review docs updated together.
  **NEXT: Gate 2 implementation** — QUAL-27 (fast) → QUAL-29 + QUAL-28 (foundation) → per-subsystem.
- **QUAL-25 DONE** → `docs/review/dataflow_review.md`. Ran 5 parallel tracer agents (entry adapters · text-proc/NLU/
  orchestrator · handler boundary · F&F/output · context-model lifecycle), each cross-referencing the 4 prior QUAL
  reviews, then adversarially verified the headline NEW P0s against source. **~9 P0, ~20 P1.** Headline: **a
  `Intent.text`→`raw_text` field rename was never propagated** — `intent.text` read at 14 unguarded sites in 7
  handlers + `Intent(text=…)` at orchestrator.py:217 → most of the command surface AttributeErrors, masked as a
  generic error (the smoke test only covers entity-only handlers, so it stayed green). Other NEW P0s: session_id=
  "default" collapses all sessions (cross-request leak); MemoryManager cleanup loop dead; InputManager/WebSocket
  input path dead (overlaps ARCH-6); required-params unenforced. CONFIRMS all FAF P0s + TXTPROC raw-TTS. **Surfaced a
  4th cross-cutting theme: "data-contract drift"** (model contracts silently disagree across boundaries). §2 answers
  the DOC-8 request-vs-session question; §4+§6 = the QUAL-26 agenda. Per Invariant #5, plan + review doc updated
  together. **NEXT: QUAL-26 (review-of-reviews, live collaboration).**
- **QUAL-25 BROADENED + QUAL-26 added** (user) — (1) QUAL-25 scope widened from "analyze the context/result types"
  to a **full input→action dataflow** analysis (every entry modality: voice/ASR, text, stream → NLU → orchestrator →
  handler → F&F → output). (2) The user expects QUAL-25 to reveal inconsistencies that **cut across the earlier
  reviews**, so added **QUAL-26 [DFLOW] — "review-of-reviews"**: a follow-up live-collaboration session that
  consolidates all review docs and **decides intended-behaviour-vs-today** per contradiction. QUAL-26 (not Gate 2)
  is now where the cross-cutting framing is finalized and remediation tasks numbered. Gate 1.5 = QUAL-25 → QUAL-26;
  cross-cutting IDs (if discrete) shift to QUAL-27/28/….
- **DOC-8 RE-CATEGORIZED** (user correction) — yesterday's DOC-8 was filed as a plain doc task ("write
  `DATA_MODELS.md`"), but end-to-end dataflow clarity is a **macro-task that needs its own review first** (same
  species as ARCH-0 / the QUAL-8/10/12/14 wave). Created **QUAL-25 [DFLOW]** — a **map + findings** review →
  `docs/review/dataflow_review.md`; **DOC-8 demoted** to the downstream write-up that consumes it. Sequencing:
  inserted **Gate 1.5** (QUAL-25) **before Gate 2** — the cross-cutting systemic remediation (fail-loud + typed
  handler-boundary accessor / shared bases / config-truth) is now **downstream of the dataflow review**, since
  "fail-loud + typed accessor" *is* dataflow design. The cross-cutting framing decision (principles block vs
  discrete QUAL IDs) is deferred until QUAL-25 lands, to be informed by its findings. New tag **[DFLOW]**; index row
  added.
- **DOC-8 captured** (user request) — need a reference for how the pipeline's models play together (when/why each):
  `RequestContext` (request-scoped) vs `UnifiedConversationContext` (session-scoped), `Intent`/`IntentResult`,
  `AudioData`/`WakeWordResult`. → `docs/guides/DATA_MODELS.md` + a model-interplay note added to
  `phase1_architecture_map.md` §4. The request-vs-session distinction (sharpened by ARCH-1/5) is the key thing to
  clarify.
- **ARCH-5 DONE** (`27a85c3`) — the capstone. import-linter (dev dep) + 6 `[tool.importlinter]` contracts encoding
  ARCH-1..4 + a pytest test (`test_import_contracts.py`) enforcing them in the suite. **6 kept / 0 broken.** Fixed
  the last residual domain→workflows edge by moving `RequestContext` into `intents/context_models.py` (no
  TYPE_CHECKING; per the user-affirmed clean approach). The linter caught a real service-locator anti-pattern (8
  handlers `get_core()`) → logged **QUAL-24** (ignored-with-comment in the contract for now). Per the standing "ask
  before deciding" rule, got sign-off on: residual-edge handling (fix vs ignore), enforcement (pytest vs file-only),
  and the service-locator decision (ignore+follow-up) via AskUserQuestion before each. Fixed a self-inflicted
  regression mid-task (the moved RequestContext needed its `SessionManager` import). Per Invariant #5, synced
  `phase1_architecture_map.md` §5. **GATE 1 COMPLETE: ARCH-1..5 ✓ — the code provably obeys the hexagon.**
- **ARCH-4 DONE** (`df93a15`) — formalized the port layer. Found a healthy two-layer structure (component-capability
  `*Plugin` ports + adapter `*Provider` ports); audit confirmed adapters depend only on their abstraction. Filled the
  3 missing capability ports (`core/interfaces/{nlu,text_processing,voice_trigger}.py`) with real-domain-typed
  abstract methods (no TYPE_CHECKING) and wired the components. **User instruction mid-task: "ask me before making
  decisions"** — paused and got explicit sign-off on scope (gap-fill vs unify vs audit-only) and on port typing
  (real domain types) via AskUserQuestion before implementing. Verified: components instantiate + isinstance their
  port, no cycle, functional suite unchanged (perf-test flakiness only). Per Invariant #5, synced
  `phase1_architecture_map.md` §5. **Gate 1: ARCH-1✓ ARCH-2✓ ARCH-3✓ ARCH-4✓ — ARCH-5 (import-linter) is the capstone.**

### 2026-05-31
- **Revival analysis** — full doc + code + build + asset audit; established real version is 15.0.0, single
  `UnifiedVoiceAssistantWorkflow`, web API is a router (not a component), 58 entry-points (not "77").
- **DOC-1** — README/architecture synced to v15; ~28 historical docs `git mv` → `docs/archive/` (+ index);
  deprecation banners on `irene_current.md`, `configuration_guide.md`, `PIPELINE_IMPLEMENTATION.md`. → 4a55519
- **ASSET-1** — stale model IDs refreshed; `uv.lock` regenerated (spaCy 3.8.14). → fc85306
- lingua-franca abandoned-upstream tech-debt note added to `pyproject.toml`. → 3e20cd0 (see ASSET-3)
- **QUAL-1** — Phase-0 static baseline filed. → 6e39886
- **QUAL-2** — review round 1: fixed phantom-reference `NameError`s + method shadowing (16 files, +24/−206);
  verified no regressions. → b6cd282
- **Decisions:** work directly on `main`, branch only when explicitly asked · `config-master.toml` stays the
  canonical config (config-example is a release-time story) · architecture defects masked by `TYPE_CHECKING`
  (AudioData misplacement, config→core cycle) to be mapped first (ARCH-0) then fixed (ARCH-1/2), not patched piecemeal.
