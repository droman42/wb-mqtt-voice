# esp32-site — the Plane-B nginx site template pin (consumed)

A **pinned, one-way-inward copy** of the `locveil-satellite`-owned nginx site template
`provisioning/ansible/templates/esp32-site.conf.j2` (moved there from this repo's
`nginx/` 2026-07-12, BUILD-22/PROD-15). The satellite provisions the real thing; voice
pins it because its hermetic TLS e2e proves the provisioning dance against exactly this
template. Never hand-edit — re-pin when the satellite's template moves.

This is an **artifact-copy pin ahead of the owner's first family tag**: `PIN.json` holds
the owner commit + content hash; `version`/`tag` are null until the satellite stamps
this surface (its PROD-16 delegation), at which point a re-pin fills them in and adds
the owner `STAMP.json` verbatim.

| File | Origin | What it is |
|---|---|---|
| `esp32-site.conf.j2` | satellite (byte-identical) | The Plane-B (:8081/:443) nginx site template — mTLS termination for satellite traffic |
| `PIN.json` | **voice-stamped** | The pin record: owner commit, content hash, pin date |

Conformance (layer 2): `irene/tests/test_arch36_tls_e2e.py` — renders this template and
drives the real provisioning dance against it (throwaway CA), so a satellite-side change
that breaks the voice contract surfaces at the next re-pin, not on a rack.

Re-pin:

```bash
git -C ../locveil-satellite show main:provisioning/ansible/templates/esp32-site.conf.j2 \
  > contracts/pins/esp32-site/esp32-site.conf.j2
# update PIN.json (owner_commit, files sha256, pin_date), then:
uv run pytest irene/tests/test_arch36_tls_e2e.py -q
```
