# contracts/ — pinned copies of externally-owned contracts

Inward, version-stamped syncs per the `cross-repo-source-of-truth` invariant: each file here is
owned elsewhere, vendored at a tagged version, and **never hand-edited** — re-pin from the owner's
tag when it moves.

| File | Owner | Pinned at | Re-pin from |
|---|---|---|---|
| `report-protocol.pin.json` | `../locveil-commons` (HK-3/PROD-6 machine core) | `report-protocol-v1` (`8fb983f`) | `git -C ../locveil-commons show report-protocol-vN:process/report-protocol/report-protocol.json` |

Validated by `irene/tests/test_report_protocol_conformance.py` — the collector's emitted labels,
title prefix, and bundle path, plus the deployment profiles' `[reports].repo`, are asserted against
the pin (a label mismatch makes tickets silently invisible to the triage queue queries).

_The Irene↔bridge catalog/command contract is pinned separately into `../locveil-commons/contracts/`
(TEST-17 — the eval framework consumes it there); this directory holds only pins that this repo's
own code/tests validate against._
