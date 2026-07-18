# locveil-voice — contract registry

The direction-labeled index required by `../locveil-commons/process/contracts.md` §2.
Every contract this repo OWNS and every pin it CONSUMES, one line each; details live in
the per-contract READMEs. Layout is the uniform org shape: `contracts/<name>/` owned,
`contracts/pins/<name>/` consumed. Pins are one-way-inward, version-stamped copies per
the `cross-repo-source-of-truth` invariant — owned elsewhere, **never hand-edited**;
re-pin from the owner when it moves.

## Owned

| Contract | Where | Version authority |
|---|---|---|
| [`ws-protocol`](ws-protocol/README.md) | artifact stays `docs/guides/websocket-api.md` (`ws-protocol-doc-canonical`); `ws-protocol/` holds the STAMP + pointer README; served as `protocol_version` in every `registered` ack | `ws-protocol/STAMP.json` + tag `ws-protocol-v1` (triple-checked by `backend/tests/test_ws_protocol_version.py`) |
| [`wake-pack`](wake-pack/README.md) | sidecar stamp over the unmodified ASSET-5 HF pack (third-party manifest, never forked); in-code catalog is the release list | `wake-pack/STAMP.json` + tag `wake-pack-v1` (URL/catalog coherence in the same test) |
| [`ui-openapi`](ui-openapi/README.md) | repo-internal GENERATED contract — artifact stays `config-ui/openapi.json` (generator `scripts/dump_openapi.py`, consumer `npm run gen:api-types`) | `ui-openapi/STAMP.json` + tag `ui-openapi-v1`; drift guard `backend/tests/test_openapi_drift.py` |
| [`docs-manifest`](docs-manifest/README.md) | repo-INTERNAL contract — artifact stays `docs/manifest.json` (the user-facing docs registry; schema is commons-owned) | `docs-manifest/STAMP.json` + tag `docs-manifest-v1`; coherence test `backend/tests/test_docs_manifest.py` |

## Consumed (pins)

| Pin | Owner | Notes |
|---|---|---|
| [`catalog`](pins/catalog/README.md) | locveil-bridge (tag `catalog-v1.5`) | LOCAL complete copy for the push-time schema check (`backend/tests/test_catalog_contract_conformance.py`); one `make repin` updates it and the commons crossover copy at the same tag |
| [`report-protocol`](pins/report-protocol/README.md) | locveil-commons (tag `report-protocol-v1`) | problem-report machine core; conformance: `backend/tests/test_report_protocol_conformance.py` |
| [`esp32-site`](pins/esp32-site/README.md) | locveil-satellite (tag `esp32-site-v1`) | Plane-B nginx site template; conformance: `backend/tests/test_arch36_tls_e2e.py` |

_The shared crossover instruments stay in `../locveil-commons/contracts/pins/`:
`crossover-fixtures/` (co-owned, both product repos' cross-suites assert against it) and
the commons `catalog/` copy the eval framework's mock bridge serves (voice stamps both
catalog PIN.jsons via `scripts/repin.py` — the two copies move together or not at all)._

Guards: layer 1 is the vendored `scripts/contract_guard.py` (commons
`packages/contract-guard/`, pinned at tag **`contract-guard-v3`** — never edit the
vendored file, re-pin to move; runs in `hooks/pre-commit` with `--relax-tags` (mid-bump
tolerance) and strict in the path-gated `contract-guard` CI job, `--check` only); layer 2
is the per-pin conformance tests listed above. Staleness (a pin trailing its owner) is
the vendored repin tool's job — `.repin.toml` + the `process/contracts.md` §5 severity
ladder (BUILD-43).
