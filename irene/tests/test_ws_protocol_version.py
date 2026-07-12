"""ARCH-47 — ws-protocol / wake-pack version-surface conformance (PROD-16 convention, layer 2).

The WS wire protocol's version exists as a TRIPLE — the doc header line in
`docs/guides/websocket-api.md` (`ws-protocol-doc-canonical`), the served constant
`irene/core/ws_protocol.py::WS_PROTOCOL_VERSION`, and `contracts/ws-protocol/STAMP.json` —
and a bump that misses one leg ships a lie (a client checks the served number against the
doc it was built from). The wake-pack sidecar stamp likewise must mirror the in-code
released catalog (`_get_default_model_urls`): a word published in code but absent from the
stamp (or vice versa) breaks the satellite's flash-time hash verification.
"""
import json
import re
from pathlib import Path

from irene.core.ws_protocol import WS_PROTOCOL_VERSION
from irene.providers.voice_trigger.microwakeword import MicroWakeWordProvider

_REPO_ROOT = Path(__file__).resolve().parents[2]
WS_STAMP = json.loads((_REPO_ROOT / "contracts" / "ws-protocol" / "STAMP.json").read_text(encoding="utf-8"))
PACK_STAMP = json.loads((_REPO_ROOT / "contracts" / "wake-pack" / "STAMP.json").read_text(encoding="utf-8"))
DOC = (_REPO_ROOT / "docs" / "guides" / "websocket-api.md").read_text(encoding="utf-8")


def test_ws_protocol_version_triple():
    m = re.search(r"\*\*Protocol version: (\S+)\*\* \(`(ws-protocol-v\S+)`\)", DOC)
    assert m, "websocket-api.md lost its 'Protocol version' header line"
    doc_version, doc_tag = m.group(1), m.group(2)
    assert doc_version == WS_PROTOCOL_VERSION == WS_STAMP["version"]
    assert doc_tag == WS_STAMP["tag"] == f"ws-protocol-v{WS_PROTOCOL_VERSION}"


def test_ws_stamp_core():
    assert WS_STAMP["contract"] == "ws-protocol"
    assert WS_STAMP["owner_repo"] == "locveil-voice"
    assert WS_STAMP["artifact"] == "docs/guides/websocket-api.md"


def test_wake_pack_stamp_mirrors_released_catalog():
    catalog = MicroWakeWordProvider._get_default_model_urls()
    stamped = PACK_STAMP["pack"]
    assert stamped["word"] in catalog, "stamped word not in the released catalog"
    catalog_files = catalog[stamped["word"]]["files"]
    stamp_files = {name: entry["url"] for name, entry in stamped["files"].items()}
    assert stamp_files == catalog_files, "wake-pack STAMP urls drifted from _get_default_model_urls"
    for entry in stamped["files"].values():
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]), "content hash must be sha256 hex"


def test_wake_pack_stamp_core():
    assert PACK_STAMP["contract"] == "wake-pack"
    assert PACK_STAMP["tag"] == f"wake-pack-v{PACK_STAMP['version']}"
    assert PACK_STAMP["owner_repo"] == "locveil-voice"
