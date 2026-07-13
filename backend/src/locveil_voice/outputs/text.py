"""Callback text output adapter (ARCH-15 PR-3) — the ws/web text channel's sink.

Generic TEXT output that hands the rendered text to an async `send` callback (e.g. a WebSocket
text frame back to the originating connection). Origin-pairable by channel. Its live consumer is
the remote debug-CLI / ws text attach in PR-6; the adapter itself is real and tested here.
"""

from typing import Awaitable, Callable, Optional, Set

from ..core.interfaces.output import DeliveryResult, OutputModality, OutputPort
from ..intents.models import IntentResult
from ..intents.context_models import RequestContext


class CallbackTextOutput(OutputPort):
    """Text sink that forwards rendered text to an async callback (ws/web frame)."""

    def __init__(self, send: Callable[[str], Awaitable[None]], *,
                 name: str = "ws_text", origin: Optional[str] = None) -> None:
        self._send = send
        self._name = name
        self._origin = origin

    def supported_modalities(self) -> Set[OutputModality]:
        return {OutputModality.TEXT}

    async def deliver(self, result: IntentResult, context: RequestContext,
                      modality: OutputModality) -> DeliveryResult:
        await self._send(result.text)
        return DeliveryResult.ok(self._name, OutputModality.TEXT)

    def get_output_type(self) -> str:
        return self._name

    def origin_key(self) -> Optional[str]:
        return self._origin
