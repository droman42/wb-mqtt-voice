# Whole-codebase review (2026-06-21)

**Status:** findings filed; **resolved 2026-06-22:** CR-A1 group (A1/A2/A3/A14/B2/D5) + BUILD-7 doc/dup cluster (C1/C2/C4/D1–D4) + dead-code
sweep (all CR-B except B4 KEPT) + provider-base dedup (C6/C7/C8) + standalone correctness (A4/A8) + silero cleanups (A12/A13) + tracing pair (A7/A9) + path-traversal hardening (A15) + correctness trio (A10/A11/A16) + Cyrillic dedup (C3) + nlu-analysis loaders (A6) + audio playback (A5) + handler base-class consolidation (C11) + asset-name/path helper (C10) + spaCy init dedup (C5) + WebAPIPlugin walk dedup (C12) — see Resolution log. **§A FULLY CLEAR.** Remainder open. **Backs:** general health pass (post-BUILD-7); individual items
cross-ref
their owning task below. **Scope:** entire `irene/` tree + `docker/` + `pyproject.toml` + `docs/guides/`. **Method:**
7 parallel finder passes (subsystem deep-reads + cross-cutting dead-code / duplication / doc-claim specialists);
the highest-severity correctness items (CR-A1, A2, A4, A7) were re-verified against source by hand.

**Emphasis (as requested):** dead/unused code, logic/data duplication, and verification of user-facing doc claims —
plus any correctness bugs surfaced along the way. These are to be addressed one-by-one or in groups later.

**Confidence:** _Confirmed_ = read the code, bug is constructible. _Likely_ = strong finder evidence, not hand-re-verified.
_Plausible_ = realistic but depends on a reachable runtime state / framework behavior.

---

## Triage summary

| ID | Sev | Conf. | One-liner | Owner / ref |
|----|-----|-------|-----------|-------------|
| **CR-A1** | **P0** | ✅ FIXED | `voice_runner` `await`s the infinite mic loop → standalone web API never starts | standalone runtime; **not** covered by BUILD-3 (used `webapi_runner`) |
| CR-A2 | P1 | ✅ FIXED | ASR never reconciles `default_provider` to a loaded provider → ASR hard-fails | new |
| CR-A3 | P1 | ✅ FIXED | `ASRComponent.initialize` swallows exceptions but stays `initialized=True` | new (compounds CR-A2) |
| CR-A4 | P1 | ✅ FIXED | `tts/vosk` `is_available` probes wrong asset namespace → dead on first run | new |
| CR-A5 | P2 | ✅ FIXED | `audio_playback` "play" is a shipped simulation (commented-out call + 10% dice fail) | new |
| CR-A6 | P2 | ✅ FIXED | `nlu_analysis` context loaders are stubs → endpoints always "healthy/no conflicts" | new |
| CR-A7 | P2 | ✅ FIXED | `process_text_input` drops the trace when the workflow raises (audio path doesn't) | tracing |
| CR-A8 | P2 | ✅ FIXED | `elevenlabs.synthesize_to_file` swallows error, writes no file | new |
| CR-A9 | P3 | ✅ FIXED | Over-broad substring trace redaction nukes `session_id`/`keyword`/`author` | tracing |
| CR-A10 | P3 | ✅ FIXED | `asr/base.audio_contract` reads a voice-trigger method name → rates always `[16000]` | new |
| CR-A11 | P3 | ✅ FIXED | `voice_synthesis._handle_speak_text` AttributeError on `text:null` entity | new |
| CR-A12 | P3 | ✅ FIXED | `silero_v3.is_available` does a blocking `requests.head` in async | QUAL-15 (same anti-pattern) |
| CR-A13 | P3 | ✅ FIXED | `silero_v4._download_model` hardcodes the RU URL, ignores `model_id` | ASSET-2 |
| CR-A14 | P3 | ✅ FIXED | monitoring `uptime` always ~0 (`_start_time` never assigned) | new |
| CR-A15 | P2 | ✅ FIXED | asset-loader save/load: `assets_root / domain / language` unsanitized (path traversal) | new (security) |
| CR-A16 | P3 | ✅ FIXED | self-routing handlers' broad `except Exception` can swallow `ParameterExtractionError` | QUAL-30 boundary |
| CR-B1..13 | — | ✅ swept | dead/zombie code (see §B) | FIXED 2026-06-22 (CR-B4 KEPT — ARCH-22/25; B12 was QUAL-20) |
| CR-C1..13 | — | C1–C13 ✅ (C9 standalone dedup done; ARCH-25 = separate HW task) | duplication / drift risk (see §C) | C1–C13 all FIXED 2026-06-22 (CR-C9 dedup standalone; ARCH-25 hardware bring-up separate) |
| CR-D1..5 | — | D1-D4 ✅ | stale user-facing doc claims (see §D) | D1–D4 FIXED 2026-06-22; D5 done in CR-A1 group |

---

## Resolution log

- **2026-06-22 — Platform-list centralization (CR-C9).** The OS-platform list
  `["linux.ubuntu","linux.alpine","macos","windows"]` was hardcoded in 52 `get_platform_support()` overrides +
  `build_analyzer` (×3) + the `dependency_validator` argparse `choices` + 2 test assertions, with `metadata.py`'s
  canonical method as the would-be source but unused. Added a `SUPPORTED_PLATFORMS` constant to `core/metadata.py` (the
  canonical `EntryPointMetadata.get_platform_support` now returns it). **Deleted 46 redundant overrides** — handlers /
  components / providers / workflows / inputs that returned the default now inherit it (validator uses `hasattr`, so
  inherited satisfies the metadata contract). Kept `aplay` (genuine linux-only restriction) and the 3 single-platform
  test fixtures; `BaseRunner` / `InputManager` (don't inherit `EntryPointMetadata`), the two tool consumers, and the 2
  test assertions now reference the constant. **Build-safety proof:** a golden snapshot of all **60 entry points'**
  `get_platform_support()` is byte-identical before/after (only `aplay` non-default) and `--validate-all` stays 60/60 —
  so the docker build (`build_analyzer:868`) sees identical values. **CPU-arch gating** (`get_supported_architectures`,
  the armv7/torch/sherpa lib path) is a *separate* method and is untouched. Net **−244 LOC across 53 files**. Gates:
  suite 1066 passed, pyright 0, import-linter 9/9, 12 profiles valid. **§C fully complete (incl. CR-C9).**
- **2026-06-22 — Provider `/configure` gate dedup (CR-C8, completing the partial).** The "set `default_provider` if it
  names a loaded provider, else warn and keep" block was byte-identical (modulo the log label) in 6 components' `/configure`
  endpoints (audio/asr/tts/llm/nlu/voice_trigger). Extracted `Component._apply_provider_config(config_dict)` (base) — the
  single source of the "is this provider loaded?" gate; all 6 call it. (`text_processor`/`intent` `/configure` don't have
  the block — left alone.) **`/providers` (×6) deliberately NOT unified:** the handlers genuinely diverge — only asr/llm
  wrap per-provider in try/except, audio/tts/voice_trigger don't, nlu uses defensive `getattr(...)`, and the per-provider
  capability fields + response models all differ; a shared skeleton would impose try/except on 4 endpoints (a behavior
  change on the error path) or become a leaky callback abstraction. Shallow 3-line loop, real variation → not worth it.
  New `test_apply_provider_config.py`. Gates: suite 1063 passed, pyright 0, import-linter 9/9. **CR-C8 complete.**
- **2026-06-22 — WebAPIPlugin component-walk dedup (CR-C12).** The "iterate `component_manager.get_components()`, filter
  `isinstance(.., WebAPIPlugin)`, build `(name, component)`" walk was reimplemented with different guarding/logging in
  `web_server._mount_component_routers` and `webapi_router` (AsyncAPI spec gen). Extracted `web_api_components(core)` into
  `core/interfaces/webapi.py` (next to `WebAPIPlugin`) — degrades to `[]` (warns) when no component manager / on lookup
  failure. Both walks now call it; the `/debug/asyncapi` endpoint (the 3rd `get_components()` site, which lists *all*
  components) also uses it to report `web_api_component_names`. New `test_web_api_components.py`. Gates: suite 1059
  passed, pyright 0, import-linter 9/9.
- **2026-06-22 — spaCy init dedup (CR-C5).** `_initialize_spacy` (plain) and `_initialize_spacy_with_assets` were ~75
  near-identical lines, and the call sites diverged: `is_available()` / `recognize()` branched
  `if self.asset_manager: _with_assets() else: _initialize_spacy()` while `_do_initialize` always used `_with_assets` —
  so a fix could land on only some paths. Merged into a single `_initialize_spacy` whose per-model asset-manager step is
  guarded by `if self.asset_manager:` (best-effort → degrades to a direct `spacy.load`). Dropped the duplicate's
  self-acquisition block (always a no-op: callers only reached `_with_assets` with `asset_manager` already set, and
  `_do_initialize` acquires it just before) — so the no-asset-manager "legacy path" still leaves `asset_manager`
  untouched (backwards-compat test holds). All three call sites collapse to the one method. Existing
  `test_spacy_asset_integration.py` (asset path + legacy path) now exercises both branches through the single method.
  Net −70 LOC. Gates: suite 1059 passed, pyright 0, import-linter 9/9.
- **2026-06-22 — Asset-name / asset-path helper dedup (CR-C10).** `_get_asset_handler_name` was defined verbatim in
  `intent_asset_loader.py` and `cross_language_validator.py` (and they'd *drifted* — only the loader's validated via
  `_safe_path_segment`), the inverse `[:-8]` was inlined 3×, and `assets_root / "<category>" / …` construction was
  repeated in ~30 methods. Extracted two pure module-level helpers — `asset_dir_name` (append `_handler`, idempotent) and
  `base_handler_name` (strip it) — plus a `_asset_path(*segments)` method (the single source of the `assets/<category>/…`
  layout). The loader's `_get_asset_handler_name` keeps the CR-A15 validation choke point
  (`asset_dir_name(_safe_path_segment(...))`); `cross_language_validator` imports `asset_dir_name` and drops its copy;
  the 3 `[:-8]` blocks → `base_handler_name`; 32 path constructions → `_asset_path`. New `test_asset_naming.py`. Gates:
  suite 1052 passed, pyright 0, import-linter 9/9 (new core→core import edge holds), 12 profiles valid.
- **2026-06-22 — Handler base-class consolidation (CR-C11).** `can_handle` / `_get_template` / `_error_result` were
  copy-pasted across ~13 handlers and had drifted. Hoisted canonical versions to `IntentHandler`: `can_handle`
  (donation domain/intent-name/action patterns), `_get_template` (asset key derived from the module via a
  `_template_asset` property; always-format → an unfilled placeholder is fatal), `_error_result` (renders
  `self._error_template`, default `error_general`). Removed 12 `can_handle` (all but `conversation`, which has a genuine
  `fallback_conditions` low-confidence override), 12 `_get_template`, 6 `_error_result`; 5 handlers set the
  `_error_template` class attr. **Drift fixed via data, not code:** `timer`/`datetime` were the *only* handlers missing
  `domain_patterns` in their contract — the exact reason they carried a hardcoded `if intent.domain == …: return True`
  override; added `domain_patterns: ["timer"]` / `["datetime"]` to their `contract.json` (language-neutral → `ru/en`
  unchanged) so the base matches them by domain, and dropped the overrides. `greetings` keeps its distinct
  `_get_template_data` (returns `List[str]`). Base methods use `type(self).__name__` (robust under `object.__new__`).
  **Net −665 LOC across 14 files.** Gates: suite 1052 passed, pyright 0, import-linter 9/9, 12 profiles valid.
- **2026-06-22 — Retired the duplicate boot-time handler validator (CR-C13).** `intent_asset_loader._validate_method_existence`
  ran per handler during donation load — importing each handler module + scanning its classes to check declared methods
  exist (`hasattr`) — duplicating the contract validator (`validate_contract_wiring` → `validate_contracts`), which
  imports each handler once (cached) and does the stricter `callable(getattr(...))` check, also raising
  `DonationDiscoveryError`. Deleted the method + its call. Full config-schema removal (user-approved, since config-ui has
  no specific reference — `asset_validation` is a free-form dict): dropped the `validate_method_existence` flag from
  `AssetLoaderConfig`, `DonationValidationConfig`, the `asset_validation` default, **4 config TOMLs**, and 5 tests.
  Made `AssetLoaderConfig` absorb unknown/stale keys (`**_ignored`) so the `AssetLoaderConfig(**config.asset_validation)`
  unpack can't crash on a leftover config key. New `test_asset_loader_config.py`. Gates: 12 profiles valid (Invariant
  #2), suite 1050 passed, pyright 0, import-linter 9/9.
- **2026-06-22 — Audio playback made real (CR-A5).** Purpose (per user): system/notification sounds (e.g. a
  timer-done chime) from a local media library. The "play" and "stop" fire-and-forget actions were simulated (`sleep` +
  a 10% `random` failure; the real call commented out) — and `play` couldn't even be wired because **`AudioPort` didn't
  expose `play_file`** (only the component did). Fixes: (1) added `play_file` to `AudioPort` (the component already
  implements it — the handler now reaches playback through the domain port like pause/resume/stop); (2) real wiring —
  `_start_audio_playback_action` resolves the media file and calls `audio_component.play_file(path)`,
  `_stop_audio_playback_action` calls `stop_playback()` honestly (no more "assume success"); dropped `random`/`sleep`;
  (3) **provisional** `_resolve_media_file` — `<assets_root>/audio/<name>` with a single-safe-segment + stay-in-dir
  traversal guard (name comes from an utterance), clearly marked to be replaced when the text→media mapping is redone.
  `source` other than `local` → clean "unsupported". New/updated `test_audio_playback_handler_coverage.py` (plays the
  resolved file via a console-style stub port, media-not-found / unsupported-source / traversal-rejected). Gates: suite
  1050 passed / 0 failed, pyright 0, import-linter 9/9. **§A fully clear.**
- **2026-06-22 — NLU-analysis donation loaders (CR-A6).** `_get_context_units` / `_get_all_intent_units` were
  `return []` stubs, so conflict detection always found nothing and the health score was always `1.0`. Implemented them
  to enumerate the loaded donations off the NLU component's `IntentAssetLoader`
  (`get_all_handlers_with_languages` → `get_language_phrasing_for_editing`) and build one `IntentUnit` per
  (handler, language); `_get_context_units` excludes the candidate handler. Uses the component **DI** pattern — declares
  `get_component_dependencies() → ["nlu"]`, so the manager topo-orders NLU first and injects it; the loader is read
  lazily off the injected component (degrades to empty if NLU is absent — no core-reach, no init-order crash). **Bonus
  fix:** `_donation_to_intent_unit` read
  the wrong key `methods` (a dict) — real donations use `method_donations` (a **list**), so even the realtime path
  produced empty units; now reads `method_donations` with a legacy `methods` fallback, so realtime analysis works too.
  New `test_nlu_analysis_loaders.py`. Gates: suite 1047 passed / 0 failed, pyright 0, import-linter 9/9. (§A now clear
  except CR-A5.)
- **2026-06-22 — Cyrillic/script detection dedup (CR-C3).** The `Ѐ–ӿ` Cyrillic test (and the latin/CJK
  ranges) was copy-pasted across 6 sites in 5 files — `spacy_provider`, `hybrid_keyword_matcher`, `nlu/llm` (which used
  literal `"Ѐ"`/`"ӿ"` bounds), `nlu_component` (char-count→ratio), and `analysis/hybrid_analyzer` (×2). Extracted one
  source of truth `irene/utils/text_script.py` (`is_cyrillic`/`is_latin`/`is_cjk`, `contains_cyrillic`,
  `cyrillic_char_count`, `detect_language_by_script`) and refactored all six to use it; the three NLU providers in one
  cascade can no longer disagree on the ru/en split if the range is tweaked. Pure foundation module (ARCH-12 import
  contract holds). New `test_text_script.py`. Gates: suite 1040 passed / 0 failed, pyright 0, import-linter 9/9.
- **2026-06-22 — Correctness trio (CR-A10 / CR-A11 / CR-A16).** **CR-A10:** `asr/base.audio_contract` read the
  voice-trigger-only method name `get_supported_sample_rates` (always absent on ASR), so the contract was always
  `[16000]`; now calls the real `get_preferred_sample_rates()` and defaults to `[16000]` only when it returns nothing.
  **CR-A11:** `voice_synthesis._handle_speak_text` used `entities.get("text", raw_text)` (only falls back when the key
  is *absent*) then `.strip()` — an explicit `text: null` crashed; now coalesces `entities.get("text") or raw_text or
  ""`. **CR-A16:** the 5 self-routing handlers (`conversation`, `datetime`, `greetings`, `system`, `timer`) override
  `execute()` and bypass `execute_with_donation_routing`'s QUAL-30 boundary, so their broad `except Exception` would
  swallow a `ParameterExtractionError`; added an `except ParameterExtractionError → self._clarify(...)` clause ahead of
  it in each, restoring the explain-and-ask clarification path. New `test_correctness_a10_a11_a16.py`. Gates: suite
  1036 passed / 0 failed, pyright 0, import-linter 9/9. (§A now clear except CR-A5/A6, genuine feature-completion.)
- **2026-06-22 — Asset-loader path traversal (CR-A15, security).** User-supplied `handler_name` / `domain` /
  `language` flow into `assets_root / … / <segment> / …` reads AND writes in `intent_asset_loader.py` (some via FastAPI
  path params). Added `_safe_path_segment()` (single segment only — no separators, `..`, leading dot, absolute, or NUL;
  raises `ValueError`) and applied it at every entry: `handler_name` is validated in the single choke point
  `_get_asset_handler_name` (covers all handler-derived paths), and `domain`/`language` are validated at the top of the
  10 editing/save/reload methods. Fail-closed (a method raises `ValueError` or returns its failure sentinel; both block
  traversal). New `test_asset_path_traversal.py` asserts the security invariant (nothing escapes the root) plus valid
  inputs still work. Gates: suite 1031 passed / 0 failed, pyright 0, import-linter 9/9.
- **2026-06-22 — Tracing pair (CR-A7 / CR-A9).** **CR-A7:** `workflow_manager.process_text_input` now mirrors the
  audio path — wraps the workflow call in try/except that records a `workflow_manager_text_error` stage and calls
  `_save_trace_if_enabled` before re-raising. Previously a text-path exception unwound past the save, so the trace and
  the failing stage were lost exactly when a bug fired. Re-raises (not return-error-result) to preserve the caller
  contract — `webapi_router` wraps the call in `except → HTTPException(500)`, so swallowing would have turned 500s into
  200s. **CR-A9:** trace-value redaction switched from raw-substring to word-TOKEN matching (`_key_tokens` splits on
  separators + camelCase) and dropped `session` from the secret set — so `session_id` / `keyword` / `matched_keys` /
  `author` survive while real secrets (`api_key`→{api,key}, `access_token`→{access,token}, `authorization`, `password`,
  …) are still `[REDACTED]`. New `test_trace_fixes.py` covers both. Gates: suite 1024 passed / 0 failed, pyright 0,
  import-linter 9/9.
- **2026-06-22 — Silero cleanups (CR-A12 / CR-A13).** **CR-A12:** `silero_v3.is_available` dropped its blocking
  `requests.head(model_url, timeout=5)` network probe (QUAL-15 anti-pattern) — now local-only (`torch` present), like
  v4; the model still downloads lazily and fails through the fallback chain. **CR-A13:** `silero_v4._download_model`
  now uses `self.model_url` (was a hardcoded RU wheel URL ignoring `model_url`/`model_id`). Since both fixes made the
  methods identical across v3/v4 (modulo the `self._version` log label the base already parameterizes), **hoisted
  `is_available` and `_download_model` into `SileroTTSBase`** and removed both per-class overrides — completing the
  CR-C6 dedup these bugs had blocked. New regression tests in `test_tts_provider_fixes.py` (local-only availability for
  v3+v4; `_download_model` honors `self.model_url`). Net ~−29 lines. Gates: suite 1021 passed / 0 failed, pyright 0,
  import-linter 9/9.
- **2026-06-22 — Standalone correctness (CR-A4 / CR-A8).** **CR-A4:** `tts/vosk.py` `is_available` now probes the
  correct asset namespace `("vosk_tts","ru_multi")` (was `("vosk","tts")`, which matched nothing → on a clean install
  the provider reported unavailable and the model was never downloaded). **CR-A8:** `tts/elevenlabs.py`
  `synthesize_to_file` now re-raises `RuntimeError` on failure like the sibling providers (was logging-and-returning,
  so the caller read a non-existent WAV and the TTS fallback chain never engaged). New
  `test_tts_provider_fixes.py` covers both (correct-namespace probe + raise-on-failure / no-phantom-file). Gates: suite
  1016 passed / 0 failed, pyright 0, import-linter 9/9.
- **2026-06-22 — Provider-base duplication (CR-C6/C7/C8).** Behavior-preserving base/mixin extractions (suite 1013
  passed / 0 failed, pyright 0, import-linter 9/9). **CR-C6:** new `irene/providers/tts/silero_base.py` `SileroTTSBase`
  holds the ~80%-shared body (torch-device handling, the `f"{model_file}:{torch_device}"` cache plumbing, config
  scaffolding, `_ensure_model_loaded`/`_load_model`/`warm_up`/`_normalize_text_async`, build-dep methods); `silero_v3`/
  `silero_v4` subclass it and override only what genuinely differs (model URLs/dir, `is_available`, `_load_model_async`,
  `_download_model`, the synthesis engines, speaker handling) — net ~−73 lines. **CR-C7:** hoisted the byte-identical
  `_GENERIC_SYSTEM_FALLBACK` / `_LLM_TEMPERATURE` constants + the default `get_supported_tasks` into `LLMProvider`, and
  dropped the redundant all-platforms `get_platform_*` overrides (the grandparent default is identical); left genuinely
  per-provider bits (`_get_default_credentials`, the credential-load idiom, the three distinct `is_available`s) alone —
  net ~−55 lines. **CR-C8 (partial):** `is_api_available` collapsed to one `Component.base` copy (3 dupes removed);
  the byte-identical metrics-push trio extracted to a `MetricsPushMixin` (ASR + voice_trigger), with the per-component
  label/key parameterized so log lines stay identical. **Deferred:** the `/configure` (×7) + `/providers` (×6) route
  handlers — they're FastAPI closures with per-component response models; left for a dedicated pass to avoid risking a
  route behavior change. Added typed stubs on the new base/mixin for subclass-provided members (`_load_model_async`,
  `_model_cache`, `get_runtime_metrics`, `_metrics_push_interval`) to keep pyright at 0 without `TYPE_CHECKING`
  (Invariant #9).
- **2026-06-22 — Dead-code sweep (CR-B).** Deleted (all verified 0 callers; suite/pyright/import-linter re-run green):
  **CR-B1** `Component.start` + `is_dependencies_available` (`components/base.py`); **CR-B2** remainder — `switch_workflow`,
  `hot_reload_workflow`, `get_workflow_dependencies`, `optimize_component_sharing`, `get_startup_performance_metrics`
  (`workflow_manager.py`; the audio-start subset went with the CR-A1 group); **CR-B5** `create_test_action` /
  `execute_test_action` (`debug_tools.py`); **CR-B6** `get_performance_report` / `export_metrics_json`
  (`analytics_dashboard.py`); **CR-B7** five dead reporting helpers (`metrics.py`); **CR-B8** `_print_interactive_help`/
  `_print_interactive_status` (both `cli.py` + `base.py` copies) + `check_component_dependencies` /
  `print_dependency_status` (`runners/base.py`); **CR-B13** `_parse_and_speak_with_voice`,
  `_get_context_coordination_summary`, and the duplicate unreachable `raise` in `silero_v3.py`. **CR-B3** —
  `_attempt_fallback_initialization` (a no-op stub that always returned False) removed and `_handle_component_failure`
  collapsed to its real behavior (record → log → warn dependents). **CR-B9** — dropped the unused `python-modules.txt`
  build output from `derive_build_reqs.py`. **CR-B10** — removed the empty `config-writing` extra + its 3 umbrella
  references (`headless` is now an explicit base-only profile). **CR-B11** — deleted `irene/examples/` (6 orphaned demo
  modules). **CR-B12** — already resolved (QUAL-20 cut Porcupine; only a test comment remained). **CR-B4 — KEPT, NOT
  deleted:** the `client_registry` ESP32 methods are *not* dead — `register_esp32_node` is called by
  `test_phase1_integration.py` and the methods are documented in the current `docs/architecture/client-registry.md`
  (ESP32 fleet = ARCH-22/25). `uv.lock` regenerated. Gates: suite 1013 passed / 0 failed, pyright 0, import-linter 9/9.
- **2026-06-22 — BUILD-7 doc/dup cluster.** **CR-C1:** spaCy model `@`-URL wheel specs collapsed to one module
  constant `_SPACY_MODEL_SPECS` in `spacy_provider.py`, referenced by both `get_python_dependencies()` and
  `get_asset_config()` (was 2 in-code copies + the pyproject `nlu` mirror → 1 in-code + the mirror, cross-ref
  commented). **CR-C2:** the two hand-rolled `>=`/`==`-only package-name ladders in `dependency_validator.py`
  replaced by one shared `_extract_package_name()` (regex-based) — also fixes the latent bug where `<`/`~=`/`!=` specs
  (e.g. base `numpy<2`) fell through to a literal and produced false "not found" warnings; new
  `test_dependency_validator.py` covers it. **CR-C4:** dropped the redundant `numpy>=1.21.0` / `aiohttp>=3.8.0`
  re-listings from the `wake-onnx` / `wake-tflite` extras (both are base deps; eliminates the divergent floors).
  **CR-D1** (`howto-new-model.md`), **CR-D2** (`build-system.md`), **CR-D3** (`howto-new-intent.md`): doc examples/prose
  now teach the extra-NAME contract (`get_python_dependencies` returns pyproject extra names, not raw specs).
  **CR-D4:** the `[tool.uv.index]` comment's stale "~2.5 GB" estimate replaced with the confirmed 6.44 → 3.16 GB.
  `uv.lock` regenerated. Gates: suite 1013 passed / 0 failed, pyright 0, import-linter 9/9.
- **2026-06-22 — CR-A1 group (the standalone-runtime cluster).** Fixed **CR-A1** (background the mic task via
  `asyncio.create_task` + done-callback to surface crashes + cancel-on-shutdown), **CR-D5** (web banner → real
  `/ws/audio` routes), **CR-B2** (deleted the dead `set_input_manager` + `_start_audio_workflow`→`_run_workflow`→
  `_get_input_source` audio-start cluster; kept the live `_get_audio_stream`), **CR-A2** (ASR reconciles
  `default_provider` to a loaded provider), **CR-A3** (ASR `initialize` re-raises so the degradation path engages),
  **CR-A14** (monitoring `_start_time` set in `__init__`). Added a CR-A1 regression test
  (`test_voice_runner_coverage.py::TestMicTaskLifecycle` — boots `_post_core_setup` with a never-returning mic workflow
  and asserts web setup still runs) replacing the `AsyncMock` stub that hid the bug; also fixed 2 stale BUILD-7
  metadata tests (`test_miniaudio_provider_metadata`, `test_classmethod_build_metadata`). Gates: suite 1010 passed / 0
  failed, pyright 0, import-linter 9/9. **CR-A5 / CR-A6 re-confirmed but deferred** (feature-completion, not quick
  fixes — `audio_playback` real `play_file` call + `nlu_analysis` real context loaders).

---

## A. Correctness bugs

### CR-A1 — [P0, ✅ FIXED 2026-06-22] `voice_runner` blocks before the web server starts
`irene/runners/voice_runner.py:232`. `_post_core_setup` does `await self._start_voice_audio_workflow()`, whose body
ends in `async for result in process_audio_stream(...)` (`:306`) — an infinite loop over the live mic. The `await`
never returns, so `_setup_web_server` (`:236`) never runs, `self.app` stays `None`, and `_execute_runner_logic` →
`_start_server` (`:329`) never binds port 6000. The method's own docstring (`:324`) says the workflow "runs in the
background on the same loop" → the intent was `asyncio.create_task(...)`, not `await`.
**Impact:** the shipped x86_64 standalone image (`Dockerfile.x86_64` CMD = `voice_runner --port 6000`, EXPOSE 6000)
boots the mic pipeline but **never serves REST / WS / config-UI**. CI is green only because
`test_voice_runner_coverage.py:246` stubs `_start_voice_audio_workflow` with `AsyncMock`. Not covered by BUILD-3
hardware verification, which used `webapi_runner` (aarch64/armv7).

### CR-A2 — [P1, ✅ FIXED 2026-06-22] ASR never reconciles `default_provider` to a loaded provider
`irene/components/asr_component.py:155-167`. Sets `self.default_provider` from config (default `"vosk"`) and only logs
whether `providers` is empty. Missing the reconciliation every sibling has — `tts_component.py:161-163`,
`audio_component.py:192`, `voice_trigger_component.py:217`: `if default not in providers and providers: default =
list(providers)[0]`.
**Impact:** config `default_provider="vosk"`; vosk fails (missing model) but whisper loads → every `process_audio`
hits `if provider_name not in self.providers: raise ValueError` (`:202`) and `/transcribe` 404s (`:278`). ASR fully
dead despite a healthy provider. (LLM `llm_component.py:160` has the same gap but is masked by its console fallback;
ASR has no mask.)

### CR-A3 — [P1, ✅ FIXED 2026-06-22] `ASRComponent.initialize` swallows all exceptions yet stays `initialized=True`
`irene/components/asr_component.py:93-173`. Whole body under `try/except Exception` that only logs (`:172`), but
`super().initialize()` (`:95`) already set `initialized=True`. A mid-init failure → component reports healthy with
`providers=={}`; defeats the ComponentManager's degrade-on-raise path (`core/components.py:204-212`). Compounds CR-A2.

### CR-A4 — [P1, ✅ FIXED 2026-06-22] `tts/vosk.is_available` probes the wrong asset namespace
`irene/providers/tts/vosk.py:90`. `get_model_info("vosk","tts")` — every other call uses `("vosk_tts","ru_multi")`
(`:181,:186`, registered under `vosk_tts`). The pair matches nothing → `None`.
**Impact:** on a clean install the model isn't downloaded, `model_path.exists()` is False, fallback returns `None` →
`is_available()` False → component drops `vosk_tts` and **never triggers the download**. Permanently dead on first run.

### CR-A5 — [P2, ✅ FIXED 2026-06-22] `audio_playback` "play" action is a shipped simulation
`irene/intents/handlers/audio_playback_handler.py:314-347`. Real `audio_component.play_file(...)` is commented out
(`:339`); body sleeps 0.5s then `random.random()<0.1` raises a fake load failure. Handler is live (in entry-points).
**Impact:** "включи музыку" → optimistic "starting playback" reply, plays nothing, ~10% of calls report a spurious
failure from the dice roll.

### CR-A6 — [P2, ✅ FIXED 2026-06-22] `nlu_analysis` context loaders are permanent stubs
`irene/components/nlu_analysis_component.py:520-530`. `_get_context_units()` / `_get_all_intent_units()` both
`return []` ("simplified implementation"). So conflicts always `[]`, batch `total_intents=0`, health always `1.0`.
**Impact:** every NLU-analysis endpoint (`/analyze/donation`, `/analysis/batch`, `/conflicts/{handler}`, `/health`)
reports "healthy / no conflicts" regardless of reality.

### CR-A7 — [P2, ✅ FIXED 2026-06-22] `process_text_input` loses the trace when the workflow raises
`irene/core/workflow_manager.py:444-492`. The text path has no try/except and `_save_trace_if_enabled` (`:490`) is
after the `with trace_scope` block; `process_audio_input` (`:576`) records an error stage and saves. With tracing on,
a text-path exception → trace never written, no error stage. The "save every request" guarantee is violated for text.

### CR-A8 — [P2, ✅ FIXED 2026-06-22] `elevenlabs.synthesize_to_file` swallows the error, writes no file
`irene/providers/tts/elevenlabs.py:104-121`. Catches + logs, **no `raise`** (silero/vosk/piper all raise). Returns
normally without creating `output_path` → caller reads a non-existent WAV; fallback chain never engages.

### CR-A9 — [P3, ✅ FIXED 2026-06-22] Over-broad trace redaction
`irene/core/trace_context.py:412-426`. `sensitive_keys` includes short tokens `'key'`,`'session'`,`'auth'`,`'cert'`,
matched by substring → `session_id`, `keyword`/`matched_keys`, `author` get `[REDACTED]`. Non-secret diagnostic data
destroyed in every exported trace.

### CR-A10 — [P3, ✅ FIXED 2026-06-22] `asr/base.audio_contract` reads a non-existent method
`irene/providers/asr/base.py:191`. `getattr(self, "get_supported_sample_rates", None)` is the *voice_trigger*
convention; ASR providers define `get_preferred_sample_rates` (`whisper:259`, `vosk:402`, `sherpa_onnx:294`,
`google_cloud:251`). Branch never fires → contract always `rates=[16000]`, discarding declared preferences.

### CR-A11 — [P3, ✅ FIXED 2026-06-22] `voice_synthesis._handle_speak_text` crashes on null text entity
`irene/intents/handlers/voice_synthesis_handler.py:164-166`. `entities.get("text", raw_text).strip()` — the default
only applies when the key is absent; `entities["text"] = None` → `.strip()` throws `AttributeError`. Sibling
`_handle_speak_with_voice` (`:98`) uses the correct `get_param(... default=None) or parsed_text`.

### CR-A12 — [P3, ✅ FIXED 2026-06-22] `silero_v3.is_available` blocks on a network probe
`irene/providers/tts/silero_v3.py:150-155`. Synchronous `requests.head(self.model_url, timeout=5)` inside an async
method — the anti-pattern QUAL-15 removed from the OpenAI provider. `silero_v4.is_available` (`:91`) is local-only.
Blocks the loop up to 5s and marks v3 unavailable whenever offline (even with torch installed).

### CR-A13 — [P3, ✅ FIXED 2026-06-22] `silero_v4._download_model` hardcodes the RU URL
`irene/providers/tts/silero_v4.py:285-294`. `model_url = "https://models.silero.ai/.../v4_ru.pt"` ignores
`self.model_url`/`model_id` (v3 `:306` uses `self.model_url`). Latent today (v4 is RU-only per ASSET-2) but the legacy
path fetches RU for any `model_id`. Both v3/v4 `_load_model_async` log `get_model_info("silero","v3_ru"/"v4_ru")`
regardless of the selected model.

### CR-A14 — [P3, ✅ FIXED 2026-06-22] monitoring `uptime` always ~0
`irene/components/monitoring_component.py:242`. `_start_time` is never assigned, so reported uptime is ~0.

### CR-A15 — [P2, ✅ FIXED 2026-06-22] Path-traversal gap in asset-loader save/load helpers
`irene/core/intent_asset_loader.py` — `save_localization_for_domain` (`:1043`), `get_localization_for_domain_editing`
(`:1021`), `save/get_language_phrasing` (`:657,:671`), `save_prompt_for_language` (`:954`), etc. build
`assets_root / "localization" / domain / f"{language}.yaml"` and `mkdir(parents=True)` + write, with no validation of
`domain`/`language`. These are FastAPI path params (`intent_component.py:1855` `/localizations/{domain}/{language}`).
**Impact:** arbitrary read/**write** outside `assets_root` if a traversal value reaches the helper. HTTP-exploitability
is limited (Starlette single-segment `{param}` doesn't capture `/`, and normalizes `..`), but the helpers have no
defensive clamp and are also callable internally. Clamp each component to one path segment / verify the resolved path
is under `assets_root`. (Fix once via the shared helper proposed in CR-C10.)

### CR-A16 — [P3, ✅ FIXED 2026-06-22] Self-routing handlers' broad `except` can swallow `ParameterExtractionError`
Self-routing handlers (`conversation`, `datetime`, `greetings`, `system`, `timer`) wrap `execute()` in
`except Exception`, which would swallow `ParameterExtractionError` and defeat the QUAL-30 clarification boundary if any
of their `get_param` calls ever drops its caller-supplied default.

---

## B. Dead / zombie code

- **CR-B1** — ✅ **FIXED 2026-06-22**. `irene/components/base.py:219,376` `is_dependencies_available()` + `Component.start()`. Dead
  (ComponentManager uses `initialize()` at `core/components.py:204`; zero `.start()` callers) **and** broken since
  BUILD-7 (`__import__("web-api")`). _Ref: already flagged in **BUILD-7**._
- **CR-B2** — ✅ **FIXED 2026-06-22** (audio-start subset in CR-A1 group; remainder in the dead-code sweep). `irene/core/workflow_manager.py`: ~250 lines dead — `set_input_manager` (`:414`, 0 callers →
  `input_manager` always `None`); the `_start_audio_workflow`→`_run_workflow`→`_get_input_source` cluster (`:719+`);
  `switch_workflow` (`:815`), `hot_reload_workflow` (`:847`), `optimize_component_sharing` (`:969`),
  `get_workflow_dependencies` (`:927`), `get_startup_performance_metrics` (`:1007`). (`_get_audio_stream`,
  `monitor_model_loading_progress`, `update_workflow_readiness` are live — keep.)
- **CR-B3** — ✅ **FIXED 2026-06-22**. `irene/core/components.py:321` `_attempt_fallback_initialization` always `return False` (stub). The whole
  `fallback_mapping` subsystem logs "Attempting fallback… would be initialized here" while doing nothing.
- **CR-B4** — ⏸ **KEPT (not dead)** — tested + current arch doc (ARCH-22/25). `irene/core/client_registry.py`: `register_esp32_node` (`:212`), `get_devices_by_type` (`:335`),
  `cleanup_expired_clients` (`:393`), `get_registry_stats` (`:415`) — 0 non-test callers.
- **CR-B5** — ✅ **FIXED 2026-06-22**. `irene/core/debug_tools.py:172,180` `create_test_action` / `execute_test_action` — 0 callers.
- **CR-B6** — ✅ **FIXED 2026-06-22**. `irene/core/analytics_dashboard.py:152,218` `get_performance_report` / `export_metrics_json` — 0 callers.
- **CR-B7** — ✅ **FIXED 2026-06-22**. `irene/core/metrics.py`: `update_vad_cache_sizes` (`:560`), `get_component_metrics` (`:643`),
  `update_session_activity` (`:775`), `generate_analytics_report` (`:971`), `record_resampling_operation` (`:994`) —
  0 callers; the ingestion ones are never fed → silently-empty metrics.
- **CR-B8** — ✅ **FIXED 2026-06-22**. `irene/runners/cli.py:374-407` `_print_interactive_help/_status` are byte-for-byte dead duplicates of
  `irene/runners/base.py:435-467` (both 0 callers — help/status became intents). Also `runners/base.py:471,491`
  `check_component_dependencies` / `print_dependency_status` — 0 callers.
- **CR-B9** — ✅ **FIXED 2026-06-22**. `docker/derive_build_reqs.py:98` writes `python-modules.txt`; no Dockerfile `COPY`s it. Dead build output.
- **CR-B10** — ✅ **FIXED 2026-06-22**. `pyproject.toml:180` empty `config-writing` extra (`# tomli-w moved to core`), still pulled by `all` /
  `api` / `headless` umbrellas. Vestigial.
- **CR-B11** — ✅ **FIXED 2026-06-22**. `irene/examples/*.py` (6 demo modules) — not imported, not entry-points, `__all__ = []`. Orphaned.
- **CR-B12** — ✅ **ALREADY DONE** (QUAL-20). Porcupine voice-trigger: config block + schema exist, **no implementation** (ledger-confirmed zombie).
- **CR-B13** — ✅ **FIXED 2026-06-22**. Misc: `voice_synthesis_handler._parse_and_speak_with_voice` (`:360`),
  `conversation._get_context_coordination_summary` (`:1022`), `silero_v3.py:310` duplicate unreachable `raise`.

---

## C. Duplication / drift risk

- **CR-C1** — ✅ **FIXED 2026-06-22**. spaCy model `@`-URL specs in **3 places**: `pyproject.toml:172-177` (`nlu` extra),
  `spacy_provider.py:1202` (`get_asset_config`), `spacy_provider.py:1224` (`get_python_dependencies`). A version bump
  must hit all three or dev `uv sync` and the Docker image install different model versions. _Ref: **BUILD-7**._
- **CR-C2** — ✅ **FIXED 2026-06-22**. pip-spec parser written **3×** with divergent operator sets: `derive_build_reqs.py:79` (regex + `@`-split)
  vs `dependency_validator.py:453` **and** `:475` (hand-rolled `>=`/`==`/`[`/` @ ` ladder, twice in one method).
  Disagree on `<`,`~=`,`!=`,markers → validator "passes CI" while build buckets the same spec differently.
  _Ref: **BUILD-7 / BUILD-5**._
- **CR-C3** — ✅ **FIXED 2026-06-22**. Cyrillic detection (`Ѐ-ӿ`) re-implemented in 5+ files: `spacy_provider.py:76`,
  `hybrid_keyword_matcher.py:349`, `nlu/llm.py:264`, `nlu_component.py:172`, `analysis/hybrid_analyzer.py:571,589`.
  Three NLU providers in one cascade can disagree on language if anyone tweaks the range. Extract one `utils` helper.
- **CR-C4** — ✅ **FIXED 2026-06-22**. base-dep re-listings with inconsistent floors: `numpy` base `<2` vs extras `>=1.21.0`; `aiohttp` base
  `>=3.12.15` vs `wake-onnx`/`wake-tflite` `>=3.8.0`. (In-code pattern already prefers "don't re-list base deps" — see
  the `# base dependency` comments — so the extras are inconsistent with the intended convention.) _Ref: **BUILD-7**._
- **CR-C5** — ✅ **FIXED 2026-06-22**. `spacy_provider._initialize_spacy` (`:110`) vs `_initialize_spacy_with_assets` (`:165`): ~75 near-identical
  lines; `recognize()` re-init and `is_available()` each pick a different one → a fix can land on only some paths.
- **CR-C6** — ✅ **FIXED 2026-06-22**. `silero_v3.py` vs `silero_v4.py`: ~80% shared body, **shared `torch_model_cache` key** → device/cache
  changes must mirror; source of the CR-A8/A12/A13-class divergence. Candidate `SileroTTSBase`.
- **CR-C7** — ✅ **FIXED 2026-06-22**. cloud-LLM providers (openai/deepseek/anthropic) duplicate `_GENERIC_SYSTEM_FALLBACK`/`_LLM_TEMPERATURE`
  (byte-identical), `_get_default_credentials`, `get_supported_tasks`, credential-load idiom, import-probe
  `is_available`. Belongs in `LLMProvider`.
- **CR-C8** — ✅ **FIXED 2026-06-22** (is_api_available + metrics mixin + /configure `_apply_provider_config`; /providers assessed — not unified, see Resolution log). component web scaffolding copy-paste: `_metrics_push_*` (`asr_component.py:702` ≡
  `voice_trigger_component.py:565`, byte-identical), `is_api_available` (×3: nlu/text_processor/monitoring),
  `/configure` POST (×7), `/providers` (×6). Candidate `MetricsPushMixin` + shared `_apply_provider_config`.
- **CR-C9** — ✅ **FIXED 2026-06-22** (standalone dedup; ARCH-25 hardware bring-up is separate). `["linux.ubuntu","linux.alpine","macos","windows"]` `get_platform_support()` literal hardcoded in ~25
  files (handlers/inputs/workflows/components) + `dependency_validator.py:678` (`argparse choices`) +
  `build_analyzer.py:122,134` (allow-list) + a test assertion. `core/metadata.py:134` is the would-be canonical source
  but isn't reused. _Ref: **ARCH-25** (adding an armv7/WB platform would touch all of them)._
- **CR-C10** — ✅ **FIXED 2026-06-22**. `_get_asset_handler_name` defined verbatim in `intent_asset_loader.py:606` and
  `cross_language_validator.py:170`; the inverse `[:-8]` inlined 3× (`:762,:852,:1008`); `assets_root / "donations"|…`
  path construction repeated in ~20 methods with no shared helper. (Fixing CR-A15 once depends on this helper existing.)
- **CR-C11** — ✅ **FIXED 2026-06-22**. handler `can_handle` / `_get_template` / `_error_result` copy-pasted across 13 handlers and **already
  drifted** (`datetime`/`timer` added an extra short-circuit). Candidate base-class defaults.
- **CR-C12** — ✅ **FIXED 2026-06-22**. the "iterate components, filter `isinstance(.., WebAPIPlugin)`" walk reimplemented 3× with different
  guarding: `web_server.py:161`, `webapi_router.py:37` and `:1094`.
- **CR-C13** — ✅ **FIXED 2026-06-22**. `intent_asset_loader._validate_method_existence` (`:1501`) duplicates `contract_validator.py:142`
  (both default-on) → **every handler module is `importlib.import_module`-ed twice at boot** for one logical check.

---

## D. Stale user-facing doc claims

> Doc-claims pass verified ~50 concrete claims across `docs/guides/`; almost all are accurate. The stale ones cluster
> on the BUILD-7 `get_python_dependencies` contract change (Invariant #10: user-facing docs are part of "done").

- **CR-D1** — ✅ **FIXED 2026-06-22**. `docs/guides/howto-new-model.md:24-25` teaches `get_python_dependencies` returning a **raw spec**
  (`["my-asr-lib>=1.0"]`); the real contract is extra-**names** (`whisper.py:224` → `["advanced-asr"]`). The guide's own
  step 2 then defines an extra the step-1 code never references → a new-provider author produces a provider whose extra
  is never installed. _Highest-impact doc bug._ _Ref: **BUILD-7**._
- **CR-D2** — ✅ **FIXED 2026-06-22**. `docs/guides/build-system.md:9` — "`get_python_dependencies` (the pip packages)" — wrong contract. _Ref:
  **BUILD-7**._
- **CR-D3** — ✅ **FIXED 2026-06-22**. `docs/guides/howto-new-intent.md:73` — comment "add libs here if the handler needs any" invites the same
  raw-spec mistake.
- **CR-D4** — ✅ **FIXED 2026-06-22**. `pyproject.toml` `[tool.uv.index]` comment says "image: ~6.4 GB → ~2.5 GB"; confirmed actual is
  **3.16 GB** (BUILD-7 ledger has the right number). Self-inflicted; correct alongside the docs.
- **CR-D5** — ✅ **FIXED 2026-06-22**. `irene/runners/web_server.py:230` `_web_banner` still advertises `/asr/stream, /asr/binary` as the ESP32
  path; those endpoints were deleted (transport is now `/ws/audio`).

---

## Cross-checks that came back clean

No lingering `intent_validator` refs (py/Dockerfile/toml); every `irene/utils/*` module has importers; every provider
module is registered in `[project.entry-points]`; the 3 Dockerfiles are internally consistent post cpu-torch-two-step
removal; deepseek correctly uses its own `base_url`/`DEEPSEEK_API_KEY` (no leakage from the shared OpenAI client).
