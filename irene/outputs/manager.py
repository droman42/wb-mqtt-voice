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

import logging
from typing import Dict, List, Optional

from ..core.interfaces.output import DeliveryResult, OutputModality, OutputPort, negotiate
from ..core.event_bus import EventBus, EventType, PipelineEvent
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
        # ARCH-15 PR-8: a default conversational sink (the local speaker) used when no origin output
        # matches — so a voice-device's deferred F&F speaks even though its source label ("voice"/
        # "audio_stream", no room) can't be a stable origin key.
        self._conversational_fallback: Optional[str] = None
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

    def remove_output(self, name: str) -> None:
        """Deregister an output (e.g. a browser WS push channel on disconnect). Idempotent."""
        self._outputs.pop(name, None)
        if name in self._active:
            self._active.remove(name)
        for modality, designated in list(self._designated.items()):
            if designated == name:
                del self._designated[modality]
        if self._conversational_fallback == name:
            self._conversational_fallback = None

    def designate(self, modality: OutputModality, output_name: str) -> None:
        """Designate the single output that carries a capability-routed modality (D-2)."""
        if output_name not in self._outputs:
            raise KeyError(f"unknown output '{output_name}'")
        self._designated[modality] = output_name

    def designate_conversational_fallback(self, output_name: str) -> None:
        """Designate the default conversational sink (the local speaker) for unmatched results (PR-8)."""
        if output_name not in self._outputs:
            raise KeyError(f"unknown output '{output_name}'")
        self._conversational_fallback = output_name

    # --- selection (D-2) -----------------------------------------------------------------------

    def _origin_output(self, context: RequestContext) -> Optional[OutputPort]:
        """Pair a conversational result to its origin output (D-2).

        Prefer a **physical-identity** match (`origin_key() == client_id`) — this is how a deferred
        F&F result reaches the specific room/device/browser connection it belongs to — then fall back
        to the **channel** match (`origin_key() == source`) for live sync delivery.
        """
        client_id = getattr(context, "client_id", None)
        if client_id is not None:
            for out in self._outputs.values():
                if out.origin_key() == client_id:
                    return out
        source = getattr(context, "source", None)
        if source is not None:
            for out in self._outputs.values():
                if out.origin_key() is not None and out.origin_key() == source:
                    return out
        return None

    def select(self, modality: OutputModality, context: RequestContext,
               broadcast: bool = False) -> List[OutputPort]:
        """Return the target output(s) for `modality` under D-2 (may be empty)."""
        if broadcast:
            return [o for o in self._outputs.values() if negotiate(modality, o.supported_modalities())]
        if modality in _CONVERSATIONAL:
            origin = self._origin_output(context)
            if origin is not None:
                return [origin]
            # no origin match → the default conversational sink (local speaker), if one is designated
            fallback = self._conversational_fallback
            return [self._outputs[fallback]] if fallback is not None and fallback in self._outputs else []
        name = self._designated.get(modality)
        return [self._outputs[name]] if name is not None else []

    # --- delivery ------------------------------------------------------------------------------

    async def _deliver_one(self, out: OutputPort, result: IntentResult,
                           context: RequestContext, modality: OutputModality) -> DeliveryResult:
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

    async def deliver(self, result: IntentResult, context: RequestContext,
                      modality: OutputModality, broadcast: bool = False) -> List[DeliveryResult]:
        """Route + deliver `result` as `modality`. Returns one DeliveryResult per target."""
        targets = self.select(modality, context, broadcast=broadcast)
        results: List[DeliveryResult] = []
        for out in targets:
            dr = await self._deliver_one(out, result, context, modality)
            results.append(dr)
            await self._emit_delivered(dr, context)
        return results

    async def _emit_delivered(self, dr: DeliveryResult, context: RequestContext) -> None:
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
