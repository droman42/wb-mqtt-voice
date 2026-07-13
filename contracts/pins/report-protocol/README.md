# report-protocol — the problem-report wire protocol pin (consumed)

A **pinned, one-way-inward copy** of the `locveil-commons`-owned problem-report machine
core (HK-3/PROD-6). Commons is the source of truth: artifact
`contracts/report-protocol/report-protocol.json` (tag `report-protocol-v1`), normative
prose `process/problem-reports.md`. Never hand-edit any file here — re-pin on a vN bump.

| File | Origin | What it is |
|---|---|---|
| `report-protocol.json` | commons (byte-identical) | The machine core: labels, title prefix, bundle path — what the triage queue queries key on |
| `STAMP.json` | commons (byte-identical) | The owner's version stamp for the artifact |
| `PIN.json` | **voice-stamped** | The pin record: which commons tag/commit voice validates against, file hashes, and when |

Conformance (layer 2): `backend/tests/test_report_protocol_conformance.py` — the
collector's emitted labels, title prefix, and bundle path, plus the deployment profiles'
`[reports].repo`, are asserted against this pin (a label mismatch makes tickets silently
invisible to the triage queue).

Re-pin:

```bash
git -C ../locveil-commons show report-protocol-vN:contracts/report-protocol/report-protocol.json \
  > contracts/pins/report-protocol/report-protocol.json
git -C ../locveil-commons show report-protocol-vN:contracts/report-protocol/STAMP.json \
  > contracts/pins/report-protocol/STAMP.json
# update PIN.json (version, tag, owner_commit, files sha256s, pin_date), then:
uv run pytest backend/tests/test_report_protocol_conformance.py -q
```
