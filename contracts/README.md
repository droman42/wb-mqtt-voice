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
| [`ws-protocol`](ws-protocol/README.md) | artifact stays `docs/guides/websocket-api.md` (`ws-protocol-doc-canonical`); `ws-protocol/` holds the STAMP + pointer README; served as `protocol_version` in every `registered` ack | `ws-protocol/STAMP.json` + tag `ws-protocol-v1` (triple-checked by `irene/tests/test_ws_protocol_version.py`) |
| [`wake-pack`](wake-pack/README.md) | sidecar stamp over the unmodified ASSET-5 HF pack (third-party manifest, never forked); in-code catalog is the release list | `wake-pack/STAMP.json` + tag `wake-pack-v1` (URL/catalog coherence in the same test) |
| [`ui-openapi`](ui-openapi/README.md) | repo-internal GENERATED contract — artifact stays `config-ui/openapi.json` (generator `scripts/dump_openapi.py`, consumer `npm run gen:api-types`) | `ui-openapi/STAMP.json` + tag `ui-openapi-v1`; drift guard `irene/tests/test_openapi_drift.py` |

## Consumed (pins)

| Pin | Owner | Notes |
|---|---|---|
| [`report-protocol`](pins/report-protocol/README.md) | locveil-commons (tag `report-protocol-v1`) | problem-report machine core; conformance: `irene/tests/test_report_protocol_conformance.py` |
| [`esp32-site`](pins/esp32-site/README.md) | locveil-satellite (pre-tag artifact-copy pin @ `37dcac5`) | Plane-B nginx site template; conformance: `irene/tests/test_arch36_tls_e2e.py` |

_The Irene↔bridge catalog/command contract is pinned into
`../locveil-commons/contracts/pins/{catalog,crossover-fixtures}/` (TEST-17 — the shared
eval framework consumes it there, voice stamps its PIN.json); this directory holds only
pins that this repo's own code/tests validate against._

Guards: layer 1 is the vendored `scripts/contract_guard.py` (commons
`packages/contract-guard/`, pinned at tag **`contract-guard-v1`** — never edit the
vendored file, re-pin to move; runs in `hooks/pre-commit` and the path-gated
`contract-guard` CI job, `--check` only); layer 2 is the per-pin conformance tests
listed above.
