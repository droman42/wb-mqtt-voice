# ws-protocol — the WebSocket wire protocol (owned)

The normative artifact **lives at [`docs/guides/websocket-api.md`](../../docs/guides/websocket-api.md)**
(`ws-protocol-doc-canonical` — a hand-written reference that doubles as the user guide; owned
surfaces that legitimately live elsewhere keep their home, per
`../locveil-commons/process/contracts.md` §2). This folder holds the version authority only.

The version exists in a **triple**, asserted equal by
`irene/tests/test_ws_protocol_version.py`:

1. the doc's "Protocol version" header line,
2. the served constant `irene/core/ws_protocol.py::WS_PROTOCOL_VERSION`
   (sent in every `registered` ack),
3. `STAMP.json` here.

Bump all three together on a breaking wire change and tag `ws-protocol-vN` (family-named;
STAMP + tag are the only version authority — no prose version history). Consumers:
the satellite runner (`irene/satellite/link.py`), the future ESP32 firmware, and
locveil-commons' `ws_audio_provider`; `../locveil-satellite` pins this contract
(`contracts/pins/ws-protocol/`) and reports `protocol_version` at register.
