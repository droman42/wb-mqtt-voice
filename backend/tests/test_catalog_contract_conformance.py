"""BUILD-34 — catalog contract conformance against the LOCAL complete pin (PROD-16 follow-up).

The hermetic push-time half of the catalog contract check (the crossover suite in
locveil-commons stays the release-cadence deep gate). Voice consumes the bridge's catalog
REST API at runtime — `parse_catalog` reads `CatalogResponse`, the emitted canonical
commands' `request_body()` are `CanonicalActionRequest`/`RoomCanonicalRequest` wire bodies
— and until this pin existed, a bridge schema reshape only surfaced when the cross-suite
ran. Now it fails here, on every push, against `contracts/pins/catalog/` (the owner's FULL
tagged artifact set — a pin is always complete; usage never shapes it, contracts.md §2).

Re-pin: `make -C eval repin CONTRACT=catalog` — updates this pin AND the commons crossover
pin in one run at the same tag; they must never diverge.
"""
import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

from locveil_voice.intents.device_commands import DeviceCommand, GroupScope, RoomGroupCommand
from locveil_voice.outputs.bridge import parse_catalog

PIN_DIR = Path(__file__).resolve().parents[2] / "contracts" / "pins" / "catalog"
GOLDEN = json.loads((PIN_DIR / "catalog.golden.json").read_text(encoding="utf-8"))
OPENAPI = json.loads((PIN_DIR / "openapi.json").read_text(encoding="utf-8"))
STAMP = json.loads((PIN_DIR / "STAMP.json").read_text(encoding="utf-8"))
PIN = json.loads((PIN_DIR / "PIN.json").read_text(encoding="utf-8"))


def _schema(name: str) -> dict:
    return {"$ref": f"#/components/schemas/{name}", "components": OPENAPI["components"]}


# ------------------------------------------------------------------ pin coherence

def test_pin_matches_owner_stamp():
    assert PIN["tag"] == STAMP["tag"]
    assert PIN["bridge_commit"] == STAMP["bridge_commit"]
    assert PIN["catalog_version"] == STAMP["catalog_version"] == GOLDEN["version"]


# ------------------------------------------------------------------ client side (inbound)

def test_golden_is_a_catalog_response():
    """The pinned golden IS a CatalogResponse — the shape voice's fetcher receives."""
    jsonschema.validate(GOLDEN, _schema("CatalogResponse"))


def test_voice_client_parses_the_pinned_catalog():
    """`parse_catalog` (the ARCH-26 fetch path) accepts the pinned bytes end-to-end."""
    catalog = parse_catalog(GOLDEN)
    assert catalog is not None
    assert catalog.devices, "pinned golden parsed to an empty device set"
    assert catalog.rooms, "pinned golden parsed to an empty room set"


# ------------------------------------------------------------------ emit side (outbound)

def test_device_command_body_is_a_canonical_action_request():
    """What voice POSTs to /devices/{id}/canonical validates against the pinned schema —
    built from the golden's own first actionable capability, so the example stays real."""
    device = next(d for d in GOLDEN["devices"]
                  for cap in (d.get("capabilities") or [])
                  if cap.get("actions"))
    cap = next(c for c in device["capabilities"] if c.get("actions"))
    action = cap["actions"][0]
    cmd = DeviceCommand(device_id=device["id"], capability=cap["name"],
                        action=action["name"], params=None)
    jsonschema.validate(cmd.request_body(), _schema("CanonicalActionRequest"))


def test_room_group_command_body_is_a_room_canonical_request():
    """What voice POSTs to /rooms/{id}/canonical validates against the pinned schema."""
    room = GOLDEN["rooms"][0]
    cmd = RoomGroupCommand(room_id=room["id"], group="light", action="turn_on",
                           scope=GroupScope.AUTO)
    jsonschema.validate(cmd.request_body(), _schema("RoomCanonicalRequest"))
