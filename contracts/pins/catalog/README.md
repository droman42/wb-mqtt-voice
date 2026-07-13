# catalog — the Irene ↔ bridge contract pin (consumed, local complete copy)

A **pinned, one-way-inward copy** of the `locveil-bridge` catalog contract artifacts at a
`catalog-vN` tag — the owner's FULL tagged set, byte-identical (a pin is always complete;
usage never shapes it — `../locveil-commons/process/contracts.md` §2). Never hand-edit.

This is the **push-time** copy (PROD-16 follow-up, BUILD-34): voice consumes the catalog
REST API at runtime (`parse_catalog` reads `CatalogResponse`; emitted canonical commands
are `CanonicalActionRequest`/`RoomCanonicalRequest` bodies), so its schema conformance is
checked hermetically on every push against this pin. The **commons copy**
(`../locveil-commons/contracts/pins/catalog/`) is the shared crossover pin — the eval
framework's mock bridge and the release-cadence cross-suite run against it.

| File | Origin | What it is |
|---|---|---|
| `catalog.golden.json` | bridge (byte-identical) | The golden catalog instance |
| `openapi.json` | bridge (byte-identical) | The API schema of record |
| `STAMP.json` | bridge (byte-identical) | The bridge's version stamp |
| `PIN.json` | **voice-stamped** | The pin record (tag, owner commit, sha256s) |

Conformance (layer 2): `backend/tests/test_catalog_contract_conformance.py`.

Re-pin — ONE command updates this copy AND the commons crossover copy at the same tag
(they must never diverge):

```bash
make -C eval repin CONTRACT=catalog          # newest bridge catalog-vN (or TAG=…)
make -C eval repin-check                     # staleness gate across every pin copy
```
