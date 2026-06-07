"""OutputManager — registry + lifecycle + modality routing for output sinks (ARCH-15 PR-2).

The delivery-side coordinator (symmetric to `InputManager`). Holds the active `OutputPort`
adapters, selects the target(s) for a result by **modality** (D-2):

  - conversational (TEXT / SPEECH) → **origin-paired** (the output whose `origin_key()` matches
    the request's `source`); exactly one target,
  - actuation / event (DEVICE_COMMAND / EVENT) → **capability-routed to a single designated**
    output (no fan-out → no double-actuation),
  - plus an explicit **broadcast** escape hatch (handler-chosen) for whole-home announce.

For each selected output it applies the §3.1 capability negotiation (carry / degrade speech→text /
drop) and returns a `DeliveryResult`. Adapter-free in PR-2: exercised by fakes; wired into the
workflow in PR-3. Optionally publishes `output.delivered` to the event bus.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, List, Optional

from ..core.interfaces.output import DeliveryResult, OutputModality, OutputPort, negotiate
from ..core.event_bus import EventBus, EventType, PipelineEvent

if TYPE_CHECKING:
    from ..intents.models import IntentResult
    from ..intents.context_models import RequestContext

logger = logging.getLogger(__name__)

_CONVERSATIONAL = (OutputModality.TEXT, OutputModality.SPEECH)


class OutputManager:
    """Registry of output adapters + modality-routed delivery."""

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self._outputs: Dict[str, OutputPort] = {}
        self._active: List[str] = []
        # capability-routed designations for non-conversational modalities (D-2)
        self._designated: Dict[OutputModality, str] = {}
        self._event_bus = event_bus

    # --- registry / lifecycle ------------------------------------------------------------------

    async def add_output(self, name: str, output: OutputPort) -> None:
        if not await output.is_available():
            logger.warning(f"Output '{name}' is not available; not registered")
            return
        self._outputs[name] = output

    async def start(self) -> None:
        for name, out in self._outputs.items():
            await out.start()
            if name not in self._active:
                self._active.append(name)

    async def stop(self) -> None:
        for name in list(self._active):
            await self._outputs[name].stop()
        self._active.clear()

    def designate(self, modality: OutputModality, output_name: str) -> None:
        """Designate the single output that carries a capability-routed modality (D-2)."""
        if output_name not in self._outputs:
            raise KeyError(f"unknown output '{output_name}'")
        self._designated[modality] = output_name

    # --- selection (D-2) -----------------------------------------------------------------------

    def _origin_output(self, context: "RequestContext") -> Optional[OutputPort]:
        for out in self._outputs.values():
            if out.origin_key() is not None and out.origin_key() == context.source:
                return out
        return None

    def select(self, modality: OutputModality, context: "RequestContext",
               broadcast: bool = False) -> List[OutputPort]:
        """Return the target output(s) for `modality` under D-2 (may be empty)."""
        if broadcast:
            return [o for o in self._outputs.values() if negotiate(modality, o.supported_modalities())]
        if modality in _CONVERSATIONAL:
            origin = self._origin_output(context)
            return [origin] if origin is not None else []
        name = self._designated.get(modality)
        return [self._outputs[name]] if name is not None else []

    # --- delivery ------------------------------------------------------------------------------

    async def _deliver_one(self, out: OutputPort, result: "IntentResult",
                           context: "RequestContext", modality: OutputModality) -> DeliveryResult:
        target_modality = negotiate(modality, out.supported_modalities())
        if target_modality is None:
            dr = DeliveryResult.drop(out.get_output_type(), modality,
                                     detail="output cannot carry modality")
            logger.info(f"dropped {modality.value} for {out.get_output_type()} (no degrade path)")
            return dr
        dr = await out.deliver(result, context, target_modality)
        if target_modality is not modality:
            dr.degraded_from = modality
        return dr

    async def deliver(self, result: "IntentResult", context: "RequestContext",
                      modality: OutputModality, broadcast: bool = False) -> List[DeliveryResult]:
        """Route + deliver `result` as `modality`. Returns one DeliveryResult per target."""
        targets = self.select(modality, context, broadcast=broadcast)
        results: List[DeliveryResult] = []
        for out in targets:
            dr = await self._deliver_one(out, result, context, modality)
            results.append(dr)
            await self._emit_delivered(dr, context)
        return results

    async def _emit_delivered(self, dr: DeliveryResult, context: "RequestContext") -> None:
        if self._event_bus is None:
            return
        await self._event_bus.publish(PipelineEvent(
            type=EventType.OUTPUT_DELIVERED,
            session_id=getattr(context, "session_id", None),
            client_id=getattr(context, "client_id", None),
            room_name=getattr(context, "room_name", None),
            source=getattr(context, "source", None),
            payload={"output": dr.output_name, "modality": dr.modality.value,
                     "delivered": dr.delivered, "dropped": dr.dropped,
                     "degraded_from": dr.degraded_from.value if dr.degraded_from else None},
        ))
