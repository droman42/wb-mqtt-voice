"""Output Port — the capability contract for output sinks (ARCH-15 PR-2).

Symmetric twin of `InputPort` (see `io_architecture.md` §3/§3.2). An OutputPort renders a
format-neutral `IntentResult` to one concrete delivery channel (console, ws/web text, local
audio/TTS, MQTT event, bridge actuation). `deliver()` returns a `DeliveryResult` — trivial
ack/nack for terminal channels, **rich** (echo + error_code) for the request/response bridge
actuation channel (D-6). Lives in `core/interfaces` so `core` depends inward on the abstraction;
the concrete adapters live in `irene/outputs/` (PR-3+).

Mirrors the input port: `core/interfaces/input.py` imports `intents.models` directly, and so does
this module (`IntentResult`/`RequestContext`) — `core` may depend inward on the domain.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Set

from ..metadata import EntryPointMetadata
from ...intents.models import IntentResult
from ...intents.context_models import RequestContext


class OutputModality(Enum):
    """What kind of output a result carries — the axis the capability matrix routes on (§3).

    - TEXT: rendered text (console, web, ws text frame, MQTT event payload)
    - SPEECH: synthesized audio played on a local device (TTS + audio)
    - DEVICE_COMMAND: a canonical actuation command sent to the bridge (ARCH-7/8) — the only
      modality whose delivery returns a *rich* DeliveryResult (the synchronous value echo)
    - EVENT: a structured, content-agnostic event published to a sink (Flow 1, e.g. irene/{room}/event)
    """
    TEXT = "text"
    SPEECH = "speech"
    DEVICE_COMMAND = "device_command"
    EVENT = "event"


@dataclass
class DeliveryResult:
    """Outcome of delivering one result to one output (§3.2).

    Terminal channels return a trivial ack/nack; the bridge actuation channel returns the rich
    fields (`echoed_value`/`error_code`) the actuating handler awaits to compose its confirmation.
    """
    output_name: str
    modality: OutputModality          # the modality actually delivered (after any degrade)
    delivered: bool
    dropped: bool = False
    degraded_from: Optional[OutputModality] = None
    detail: Optional[str] = None
    # Rich request/response fields — populated only by the bridge actuation channel (D-6, ARCH-8)
    echoed_value: Any = None
    error_code: Optional[str] = None

    @classmethod
    def ok(cls, output_name: str, modality: OutputModality, **extra: Any) -> "DeliveryResult":
        return cls(output_name=output_name, modality=modality, delivered=True, **extra)

    @classmethod
    def drop(cls, output_name: str, modality: OutputModality, detail: str) -> "DeliveryResult":
        return cls(output_name=output_name, modality=modality, delivered=False,
                   dropped=True, detail=detail)


def negotiate(modality: OutputModality, capabilities: Set[OutputModality]) -> Optional[OutputModality]:
    """Modality negotiation (§3.1): which modality to actually deliver as, or None to drop.

    - carriable as-is → that modality
    - SPEECH not carriable but TEXT is → degrade to TEXT (speak the text instead)
    - otherwise → None (drop; caller logs)

    The *default of the default* is degrade-then-drop, never silently mis-deliver.
    """
    if modality in capabilities:
        return modality
    if modality is OutputModality.SPEECH and OutputModality.TEXT in capabilities:
        return OutputModality.TEXT
    return None


class OutputPort(EntryPointMetadata, ABC):
    """Abstract port for an output sink. Implemented by adapters in `irene/outputs/`."""

    @abstractmethod
    def supported_modalities(self) -> Set[OutputModality]:
        """Modalities this output can carry — the capability half of the §3.1 matrix."""
        ...

    @abstractmethod
    async def deliver(self, result: IntentResult, context: RequestContext,
                      modality: OutputModality) -> DeliveryResult:
        """Render `result` to this channel as `modality`. Returns the delivery outcome."""
        ...

    # --- optional lifecycle / identity (defaults mirror InputPort) -----------------------------

    async def start(self) -> None:
        """Initialise/start the output channel."""
        return None

    async def stop(self) -> None:
        """Stop the output channel and release resources."""
        return None

    async def is_available(self) -> bool:
        """True if the channel can be used."""
        return True

    def get_output_type(self) -> str:
        """Output type identifier (e.g. 'console', 'ws', 'mqtt_event', 'bridge')."""
        return "unknown"

    def origin_key(self) -> Optional[str]:
        """Channel-pairing key (D-2): the `RequestContext.source` this output is paired with for
        origin-addressed conversational delivery (e.g. 'cli', 'ws'). None = not origin-pairable
        (a designated/capability-routed sink like the bridge or an MQTT event topic)."""
        return None

    def get_settings(self) -> Dict[str, Any]:
        return {}
