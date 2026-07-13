# esp32-site — the Plane-B nginx site template pin (consumed)

A **pinned, one-way-inward copy** of the `locveil-satellite`-owned nginx site template
(owned surface `contracts/esp32-site/` there; artifact
`provisioning/ansible/templates/esp32-site.conf.j2`, tag **`esp32-site-v1`**). The
satellite provisions the real thing; voice pins it because its hermetic TLS e2e proves the
provisioning dance against exactly this template. Never hand-edit — re-pin on a vN bump.

| File | Origin | What it is |
|---|---|---|
| `esp32-site.conf.j2` | satellite (byte-identical) | The Plane-B (:8081/:443) nginx site template — mTLS termination for satellite traffic |
| `STAMP.json` | satellite (byte-identical) | The owner's version stamp for the surface |
| `PIN.json` | **voice-stamped** | The pin record: tag, owner commit, content hashes |

Conformance (layer 2): `backend/tests/test_arch36_tls_e2e.py` — renders this template and
drives the real provisioning dance against it (throwaway CA), so a satellite-side change
that breaks the voice contract surfaces at the next re-pin, not on a rack.

Re-pin:

```bash
make -C eval repin CONTRACT=esp32-site       # newest satellite esp32-site-vN tag
uv run pytest backend/tests/test_arch36_tls_e2e.py -q
```
