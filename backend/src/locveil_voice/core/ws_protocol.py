"""The WS wire-protocol version — the served half of the `ws-protocol` contract (ARCH-47).

`docs/guides/websocket-api.md` is the single source of truth for the wire protocol
(`ws-protocol-doc-canonical`); this constant is its machine-readable twin, sent in every
`registered` ack so a consumer (the satellite runner, ESP32 firmware, locveil-commons'
`ws_audio_provider`) can check what it was built against without parsing prose. The
version triple — the doc's "Protocol version" header line, this constant, and
`contracts/ws-protocol/STAMP.json` — is asserted equal by
`irene/tests/test_ws_protocol_version.py`; bump all three together (and re-tag
`ws-protocol-vN`) on any breaking wire change.
"""

WS_PROTOCOL_VERSION = "1"
