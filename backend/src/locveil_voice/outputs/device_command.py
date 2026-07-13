"""Capturing DEVICE_COMMAND output — the fake bridge (ARCH-8 PR-1, `mqtt_integration.md` §14.3).

A request/response `OutputPort` shaped exactly like the real bridge adapter
(PR-2's `BridgeClient`) but terminal: it records each canonical command instead
of POSTing it, and answers with the same rich `DeliveryResult` the handlers
compose spoken confirmations from. This IS the capture point of the TEST-18
producer contract tests — an utterance goes in, the captured `to_dict()`
payload comes out for assertion against the crossover fixtures — and the unit
seam ARCH-8's own tests drive before a live bridge exists.

A scripted `responder` lets tests exercise the §5b error paths (`error_code` →
spoken phrase, `param_invalid` → clarify) without a bridge to misbehave.
"""

from typing import Callable, List, Optional, Set

from ..core.interfaces.output import DeliveryResult, OutputModality, OutputPort
from ..intents.context_models import RequestContext
from ..intents.device_commands import DEVICE_COMMAND_METADATA_KEY, CanonicalCommand
from ..intents.models import IntentResult

OUTPUT_TYPE = "device_command_capture"

# Test-scriptable outcome: given the captured command, produce the DeliveryResult.
CommandResponder = Callable[[CanonicalCommand], DeliveryResult]


def _echo_success(command: CanonicalCommand) -> DeliveryResult:
    """Default responder: success, echoing the command payload (the happy-path bridge)."""
    return DeliveryResult.ok(OUTPUT_TYPE, OutputModality.DEVICE_COMMAND,
                             echoed_value=command.to_dict())


class CapturingDeviceCommandOutput(OutputPort):
    """Records canonical commands; answers like the bridge would."""

    def __init__(self, responder: Optional[CommandResponder] = None) -> None:
        self._responder = responder or _echo_success
        self.captured: List[CanonicalCommand] = []

    def supported_modalities(self) -> Set[OutputModality]:
        return {OutputModality.DEVICE_COMMAND}

    async def deliver(self, result: IntentResult, context: RequestContext,
                      modality: OutputModality) -> DeliveryResult:
        command = result.metadata.get(DEVICE_COMMAND_METADATA_KEY)
        if command is None:
            # A device_command result without a command is a handler bug — fail loudly.
            return DeliveryResult.drop(
                OUTPUT_TYPE, OutputModality.DEVICE_COMMAND,
                detail=f"result carries no '{DEVICE_COMMAND_METADATA_KEY}' metadata")
        self.captured.append(command)
        return self._responder(command)

    def get_output_type(self) -> str:
        return OUTPUT_TYPE

    # origin_key() stays None (base default): this is a designated, capability-routed
    # sink (D-2), never origin-paired.
