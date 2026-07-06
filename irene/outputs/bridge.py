"""BridgeClient — the wb-mqtt-bridge REST adapter (ARCH-8 PR-2).

The ONLY module that knows the bridge exists (`mqtt_integration.md` §4). Lives with the other
output adapters (all OutputPorts in one home — user decision 2026-07-05, superseding §13.1's
`irene.providers.outputs` entry-point group); unlike its channel-sink neighbours it is
config-gated (`[outputs.bridge]`), composition-registered on every profile, and
capability-routed via `designate()`. Two jobs:

1. **Actuation `OutputPort`** (§13.1): delivers `device_command`-modality results by POSTing the
   canonical command to the address-form endpoint — device form → `POST /devices/{id}/canonical`,
   room-group form → `POST /rooms/{room_id}/canonical` (VWB-23) — and returns the **rich**
   `DeliveryResult` (post-action state / per-member aggregate as `echoed_value`, the §5b error
   enum as `error_code`) the handler composes its spoken confirmation from.

2. **Catalog source**: `fetch_catalog()` pulls `GET /system/catalog` and parses it into the domain
   `DeviceCatalog` — wired as the `CatalogService` fetcher (startup pull + ARCH-26 lazy re-pull).

Transport failures never raise out of `deliver()`: the bridge being down is a spoken outcome
("мост не отвечает"), not a crash — `error_code="bridge_unreachable"` (voice-side code, distinct
from the bridge's own `device_unreachable`). Fail-loud in the log, fail-soft to the pipeline (§9).
"""

import asyncio
import logging
from typing import Any, Dict, Optional, Set, Tuple

import aiohttp

from ..core.interfaces.output import DeliveryResult, OutputModality, OutputPort
from ..intents.context_models import RequestContext
from ..intents.device_catalog import (
    CatalogActionSpec,
    CatalogCapability,
    CatalogDevice,
    CatalogFieldSpec,
    CatalogParamSpec,
    CatalogRoom,
    DeviceCatalog,
    ValueLabel,
)
from ..intents.device_commands import (
    DEVICE_COMMAND_METADATA_KEY,
    DeviceCommand,
    RoomGroupCommand,
)
from ..intents.models import IntentResult

logger = logging.getLogger(__name__)

OUTPUT_TYPE = "bridge"

# Voice-side transport error code — the bridge itself did not answer (vs the bridge's own
# `device_unreachable`, which means the bridge answered but the device's echo never came).
BRIDGE_UNREACHABLE = "bridge_unreachable"


# --- catalog parsing (bridge JSON → domain model, coded against the pinned contract) -------------

def _parse_param(raw: Dict[str, Any]) -> CatalogParamSpec:
    values = raw.get("values")
    return CatalogParamSpec(
        name=raw["name"],
        type=raw.get("type", "string"),
        required=bool(raw.get("required", False)),
        default=raw.get("default"),
        min=raw.get("min"),
        max=raw.get("max"),
        unit=raw.get("unit"),
        values=tuple(ValueLabel(wire=v["wire"], canonical=v["canonical"],
                                labels=v.get("labels") or {})
                     for v in values) if values else None,
        options_from=raw.get("options_from"),
    )


def _parse_capability(raw: Dict[str, Any]) -> CatalogCapability:
    return CatalogCapability(
        name=raw["name"],
        group=raw.get("group"),
        actions=tuple(CatalogActionSpec(
            name=a["name"],
            params=tuple(_parse_param(p) for p in (a.get("params") or ())),
        ) for a in (raw.get("actions") or ())),
        fields=tuple(CatalogFieldSpec(
            name=f["name"],
            type=f.get("type", "float"),
            unit=f.get("unit"),
            labels=f.get("labels") or {},
        ) for f in (raw.get("fields") or ())),
    )


def _parse_aliases(raw: Optional[Dict[str, Any]]) -> Dict[str, Tuple[str, ...]]:
    return {locale: tuple(names) for locale, names in (raw or {}).items()}


def parse_catalog(raw: Dict[str, Any]) -> DeviceCatalog:
    """Parse a `GET /system/catalog` response (`CatalogResponse`) into the domain model.

    Best-effort per §5a: unknown keys are ignored; missing optionals default. A malformed
    *required* field (no id, no version) raises — a catalog that can't identify itself is
    a contract violation worth failing loudly on.
    """
    return DeviceCatalog(
        version=raw["version"],
        rooms=tuple(CatalogRoom(
            id=r["id"],
            names=r.get("names") or {},
            aliases=_parse_aliases(r.get("aliases")),
            devices=tuple(r.get("devices") or ()),
            group_defaults=r.get("group_defaults") or {},
        ) for r in (raw.get("rooms") or ())),
        devices=tuple(CatalogDevice(
            id=d["id"],
            room=d.get("room"),
            names=d.get("names") or {},
            aliases=_parse_aliases(d.get("aliases")),
            capabilities=tuple(_parse_capability(c) for c in (d.get("capabilities") or ())),
        ) for d in (raw.get("devices") or ())),
    )


# --- the adapter ----------------------------------------------------------------------------------

class BridgeClient(OutputPort):
    """REST adapter to wb-mqtt-bridge: the designated DEVICE_COMMAND output + catalog source."""

    def __init__(self, base_url: str, timeout_seconds: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._session: Optional[aiohttp.ClientSession] = None

    # --- lifecycle -------------------------------------------------------------------------------

    async def start(self) -> None:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)

    async def stop(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    # --- transport (one seam; tests stub this) ----------------------------------------------------

    async def _request_json(self, method: str, path: str,
                            body: Optional[Dict[str, Any]] = None) -> Tuple[int, Dict[str, Any]]:
        """One HTTP round-trip → (status, parsed JSON body). Raises on transport failure."""
        if self._session is None or self._session.closed:
            await self.start()
        assert self._session is not None
        async with self._session.request(method, f"{self._base_url}{path}", json=body) as resp:
            return resp.status, await resp.json(content_type=None)

    # --- OutputPort ------------------------------------------------------------------------------

    def supported_modalities(self) -> Set[OutputModality]:
        return {OutputModality.DEVICE_COMMAND}

    async def deliver(self, result: IntentResult, context: RequestContext,
                      modality: OutputModality) -> DeliveryResult:
        command = result.metadata.get(DEVICE_COMMAND_METADATA_KEY)
        if command is None:
            return DeliveryResult.drop(
                OUTPUT_TYPE, OutputModality.DEVICE_COMMAND,
                detail=f"result carries no '{DEVICE_COMMAND_METADATA_KEY}' metadata")

        if isinstance(command, DeviceCommand):
            path = f"/devices/{command.device_id}/canonical"
        elif isinstance(command, RoomGroupCommand):
            path = f"/rooms/{command.room_id}/canonical"
        else:
            return DeliveryResult.drop(
                OUTPUT_TYPE, OutputModality.DEVICE_COMMAND,
                detail=f"unknown command type {type(command).__name__}")

        try:
            status, payload = await self._request_json("POST", path, command.request_body())
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            logger.warning(f"bridge unreachable delivering {command!r}: {e}")
            return DeliveryResult(
                output_name=OUTPUT_TYPE, modality=OutputModality.DEVICE_COMMAND,
                delivered=False, detail=str(e), error_code=BRIDGE_UNREACHABLE)

        return self._to_delivery_result(command, status, payload)

    @staticmethod
    def _to_delivery_result(command: Any, status: int,
                            payload: Dict[str, Any]) -> DeliveryResult:
        """Map a canonical response (either address form, §5b/VWB-23) to the rich DeliveryResult."""
        success = bool(payload.get("success"))
        error = payload.get("error") or {}
        error_code = error.get("code")
        if not success and error_code is None:
            # a non-2xx without the structured error body — still spoken as a failure
            error_code = "internal_error"
            logger.warning(f"bridge returned HTTP {status} without a structured error: {payload}")
        # device form echoes post-action `state`; the room form returns per-member `results`
        echoed = payload.get("state") if "state" in payload else payload.get("results")
        detail = error.get("message")
        if error.get("field") or error.get("reason"):
            # param_invalid carries field+reason — the clarify path consumes them (§5b)
            detail = f"{detail or ''} [field={error.get('field')}, reason={error.get('reason')}]".strip()
        return DeliveryResult(
            output_name=OUTPUT_TYPE, modality=OutputModality.DEVICE_COMMAND,
            delivered=success, detail=detail, echoed_value=echoed, error_code=error_code)

    # --- catalog source (the CatalogService fetcher, §5a) -----------------------------------------

    async def fetch_catalog(self) -> DeviceCatalog:
        """Pull + parse one catalog snapshot. Raises on transport/shape failure —
        `CatalogService.refresh()` catches and keeps the previous snapshot."""
        status, payload = await self._request_json("GET", "/system/catalog")
        if status != 200:
            raise RuntimeError(f"catalog pull failed: HTTP {status}")
        return parse_catalog(payload)

    async def get_device_state(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Live device state (`GET /devices/{id}/state`, §5c) — the PR-5 read flow's source.
        Returns the state dict, or None when the bridge/device did not answer (the caller
        speaks the degradation; never raises into the pipeline)."""
        try:
            status, payload = await self._request_json("GET", f"/devices/{device_id}/state")
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            logger.warning(f"bridge unreachable reading state of '{device_id}': {e}")
            return None
        if status != 200:
            logger.warning(f"state read for '{device_id}' failed: HTTP {status} {payload}")
            return None
        state = payload.get("state")
        return state if isinstance(state, dict) else payload

    async def get_device_options(self, device_id: str, kind: str) -> Optional[list]:
        """Runtime option set (`GET /devices/{id}/options/{kind}`, VWB-19 §11.2) — installed
        apps, parametric inputs. Fail-soft None; the handler clarifies instead of crashing."""
        try:
            status, payload = await self._request_json("GET", f"/devices/{device_id}/options/{kind}")
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            logger.warning(f"bridge unreachable reading options '{kind}' of '{device_id}': {e}")
            return None
        if status != 200 or not payload.get("success", True):
            logger.warning(f"options read '{device_id}/{kind}' failed: HTTP {status} {payload}")
            return None
        data = payload.get("data")
        return list(data) if isinstance(data, list) else None

    async def fetch_report_evidence(self) -> Dict[str, Any]:
        """The bridge's redacted evidence envelope (`GET /reports/evidence`, contract v1.4 B-11)
        for a problem-report bundle (ARCH-34). Never raises — a failure to fetch IS evidence,
        so every outcome comes back as a status record the collector files verbatim:
        `attached` (envelope present) | `rate_limited` (the endpoint's gzip-guard 429) |
        `unreachable` | `error` (unexpected HTTP status)."""
        try:
            status, payload = await self._request_json("GET", "/reports/evidence")
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            return {"status": "unreachable", "error": str(e)}
        if status == 429:
            return {"status": "rate_limited", "http_status": 429}
        if status != 200:
            return {"status": "error", "http_status": status, "body": payload}
        return {"status": "attached", "envelope": payload}

    # --- identity --------------------------------------------------------------------------------

    async def is_available(self) -> bool:
        # Registration-time gate: config said enabled, so register; reachability is probed per
        # request (a bridge that is down at boot must not unregister the actuation channel).
        return True

    def get_output_type(self) -> str:
        return OUTPUT_TYPE
