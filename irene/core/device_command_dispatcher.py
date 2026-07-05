"""DeviceCommandDispatcher — awaited DEVICE_COMMAND delivery for the smart-home handler (ARCH-8 PR-4).

Implements the domain's `DeviceCommandDeliveryPort` over the OutputManager (typed `Any` — core
keeps no import edge to `irene.outputs`, same convention as `NotificationService`). One command
in, one rich `DeliveryResult` out:

- wraps the command into a `device_command`-modality `IntentResult` (`mqtt_integration.md` §13.2)
  and routes it through the OutputManager's designated bridge output — no fan-out, no
  double-actuation (D-2);
- bounds the wait: past `timeout_seconds` the handler gets `None` and speaks the degraded
  confirmation («не уверена, что получилось») instead of blocking the turn;
- `None` also means no designated output (bridge disabled) — same spoken degradation path.
"""

import asyncio
import logging
from typing import Any, Optional

from ..intents.device_commands import DEVICE_COMMAND_METADATA_KEY
from ..intents.models import IntentResult
from ..intents.ports import DeviceCommandDeliveryPort
from .interfaces.output import OutputModality

logger = logging.getLogger(__name__)

# Above the BridgeClient's per-request HTTP timeout (5 s default) so the transport layer's own
# failure surfaces as a DeliveryResult (error_code) rather than being cut off mid-request here.
DEFAULT_DELIVERY_TIMEOUT_S = 7.0


class DeviceCommandDispatcher(DeviceCommandDeliveryPort):
    """Routes one canonical command through the OutputManager and returns the rich outcome."""

    def __init__(self, output_manager: Any, timeout_seconds: float = DEFAULT_DELIVERY_TIMEOUT_S) -> None:
        self._output_manager = output_manager
        self._timeout = timeout_seconds

    async def deliver_device_command(self, command: Any, context: Any) -> Optional[Any]:
        if self._output_manager is None:
            logger.warning("device command emitted but no OutputManager is wired")
            return None
        carrier = IntentResult(text="", should_speak=False,
                               metadata={DEVICE_COMMAND_METADATA_KEY: command})
        try:
            results = await asyncio.wait_for(
                self._output_manager.deliver(carrier, context, OutputModality.DEVICE_COMMAND),
                timeout=self._timeout)
        except asyncio.TimeoutError:
            logger.warning(f"device command delivery timed out after {self._timeout}s: {command!r}")
            return None
        if not results:
            # no designated DEVICE_COMMAND output — bridge disabled or not registered
            logger.warning("device command had no delivery target (bridge output not designated)")
            return None
        return results[0]
