# wake-pack — the released wake-word pack (owned, sidecar stamp)

The artifact is the **published two-file v2 pack** (JSON manifest + sibling `.tflite`) on
Hugging Face — a third-party format (microWakeWord) that is **never forked**; this folder is
a **sidecar stamp** (`../locveil-commons/process/contracts.md` §2): `STAMP.json` carries the
pack's version, per-file URLs and sha256 content hashes, so a consumer can pin and verify
bytes without this repo re-hosting them.

- **Source of truth for what's released:** the in-code catalog
  `irene/providers/voice_trigger/microwakeword.py::_get_default_model_urls` (ASSET-5 rung 4);
  `irene/tests/test_ws_protocol_version.py` asserts the stamp's URLs match the catalog, so
  the sidecar cannot silently drift from the code.
- **Consumer:** `../locveil-satellite` — the ESP32 flashes the pack and verifies the hashes
  at flash time (its OPS-1 carries the hash-at-publish requirement); the flashed tag comes
  back as the `wake_pack_version` register field (ARCH-47).
- **Versioning:** adding a validated word extends `pack` (minor bump, new tag); replacing a
  published model file is breaking (major bump) — flashed hashes stop verifying. Training
  lives in the `~/development/wakeword-training` factory; each new word lands as its own
  consume-task (`docs/design/wakeword_models.md`).
