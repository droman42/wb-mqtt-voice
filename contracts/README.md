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
| `ws-protocol` | _arrives with ARCH-47_ — the artifact stays `docs/guides/websocket-api.md` (`ws-protocol-doc-canonical`); `ws-protocol/` will hold STAMP.json + a pointer README | tag `ws-protocol-v1` when stamped |
| `wake-pack` | _arrives with ARCH-47_ — sidecar stamp over the unmodified ASSET-5 pack (third-party manifest, never forked) | tag `wake-pack-v1` when stamped |

## Consumed (pins)

| Pin | Owner | Notes |
|---|---|---|
| [`report-protocol`](pins/report-protocol/README.md) | locveil-commons (tag `report-protocol-v1`) | problem-report machine core; conformance: `irene/tests/test_report_protocol_conformance.py` |
| [`esp32-site`](pins/esp32-site/README.md) | locveil-satellite (pre-tag artifact-copy pin @ `37dcac5`) | Plane-B nginx site template; conformance: `irene/tests/test_arch36_tls_e2e.py` |

_The Irene↔bridge catalog/command contract is pinned into
`../locveil-commons/contracts/pins/{catalog,crossover-fixtures}/` (TEST-17 — the shared
eval framework consumes it there, voice stamps its PIN.json); this directory holds only
pins that this repo's own code/tests validate against._
