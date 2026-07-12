# contracts/ — pinned copies of externally-owned contracts

Inward, version-stamped syncs per the `cross-repo-source-of-truth` invariant: each file here is
owned elsewhere, vendored at a tagged version, and **never hand-edited** — re-pin from the owner's
tag when it moves.

| File | Owner | Pinned at | Re-pin from |
|---|---|---|---|
| `report-protocol.pin.json` | `../locveil-commons` (HK-3/PROD-6 machine core) | `report-protocol-v1` (`8fb983f`) | `git -C ../locveil-commons show report-protocol-vN:process/report-protocol/report-protocol.json` |
| `esp32-site.conf.j2` | `../locveil-satellite` (`provisioning/ansible/templates/`; moved from this repo's `nginx/` 2026-07-12, BUILD-22/PROD-15) | satellite `37dcac5` | `git -C ../locveil-satellite show main:provisioning/ansible/templates/esp32-site.conf.j2` |

`report-protocol.pin.json` is validated by `irene/tests/test_report_protocol_conformance.py` — the
collector's emitted labels, title prefix, and bundle path, plus the deployment profiles'
`[reports].repo`, are asserted against the pin (a label mismatch makes tickets silently invisible
to the triage queue queries). `esp32-site.conf.j2` is exercised by `irene/tests/test_arch36_tls_e2e.py`
— the hermetic TLS e2e renders it and drives the real provisioning dance against it, so a satellite-side
template change that breaks the voice contract surfaces here at the next re-pin.

_The Irene↔bridge catalog/command contract is pinned separately into `../locveil-commons/contracts/`
(TEST-17 — the eval framework consumes it there); this directory holds only pins that this repo's
own code/tests validate against._
