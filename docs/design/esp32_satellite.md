# ESP32 voice satellite — consolidated design (ARCH-22) — MOVED

**Moved 2026-07-12** (BUILD-22 / board PROD-15): the ESP32 satellite is its own product repo, and this
design lives there —
[`locveil-satellite/docs/design/esp32_satellite.md`](https://github.com/locveil/locveil-satellite/blob/main/docs/design/esp32_satellite.md)
(sibling working copy: `../locveil-satellite`).

Two things to know on this side of the boundary:

- The **wire protocol truth stays HERE**: [`docs/guides/websocket-api.md`](../guides/websocket-api.md)
  (`ws-protocol-doc-canonical`). The moved design's §4 wire tables were demoted to a pointer back at that
  guide in the same change; the satellite repo pins the protocol by version (voice ARCH-47 adds the stamp).
- Pre-move history is frozen in this repo: `git log --follow -- docs/design/esp32_satellite.md`.
