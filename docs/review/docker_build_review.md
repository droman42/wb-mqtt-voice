# Docker build review

> **⚠️ OBSOLETE FINDINGS (annotated 2026-07-02, BUILD-8).** This doc describes the pre-BUG-14 build: the
> armv7 image was still Alpine-based and the two "build-blocking" defects below were live. All of that is
> resolved — the Dockerfiles migrated to Debian bookworm/bullseye, the defects are gone, and the armv7 build
> is proven on the WB7 (BUG-14). Still-live remainder: the BUILD-5 analyzer extras-vs-specs cleanup. The
> current build design is `docs/design/build_release_process.md` (BUILD-8).

**Status:** complete (2026-06-08). **Backs:** BUILD-5 (verify `build_analyzer` against the real Dockerfiles),
BUILD-3 (Docker image build/boot). **Scope:** `Dockerfile.x86_64`, `Dockerfile.armv7`, and their alignment
with the current tooling.

The multi-platform Docker build (analyzer → builder → runtime; port 6000; `IRENE_CONFIG_FILE`) is structurally
sound, but **the documented build does not currently run** — two defects break both images, plus a
planned-vs-actual base-image mismatch to reconcile.

## Build-blocking defects

- **[P1] `irene.tools.intent_validator` does not exist.** Both Dockerfiles invoke it in the analyzer stage
  (`Dockerfile.x86_64:63`, `Dockerfile.armv7:62`) → `ModuleNotFoundError`. The real tools are
  `irene.tools.config_validator_cli` and `irene.tools.dependency_validator`. Either drop the intent-validation
  step or point it at the real validator (and decide what it should validate).
- **[P1] armv7 `ubuntu_packages` NameError.** The Alpine package-mapping block prints
  `f'… (from {len(ubuntu_packages)} Ubuntu packages)'` (`Dockerfile.armv7` ~line 108) but only
  `alpine_packages` is defined in that exec'd block → `NameError` aborts the analyzer stage. Define/derive
  `ubuntu_packages`, or drop it from the message.

## Reconcile during BUILD-5

- **armv7 base still Alpine.** `Dockerfile.armv7` is `python:3.11-alpine`, but **BUILD-5 §6 already plans the
  Alpine→Debian switch** (`arm32v7/python:3.11-slim-bullseye`) because sherpa-onnx has no musl build
  (`onnx_inference_layer.md §4.7/§9`). The two defects above should be fixed as part of that migration.
  (x86_64 is Debian `python:3.11-slim`, correct.)
- **`--extra` emission.** Confirm `build_analyzer --docker` names only extras that exist in `pyproject.toml`
  (`audio-input`, `advanced-asr`, `asr-onnx`, `voice-trigger`, `tts`, `audio-output`, …) — the core of BUILD-5.

## Not bugs (verified correct)

Port `6000` (`--port 6000` + `EXPOSE 6000`); `IRENE_CONFIG_FILE=/app/runtime-config.toml`; the 3-stage
structure; ARG defaults (`minimal` on x86_64, `embedded-armv7` on armv7); the health checks; and the
build-analyzer flags the Dockerfiles use. The procedure in `docs/guides/build-docker.md` reflects this
verified-correct surface.
