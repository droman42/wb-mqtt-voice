"""Console text output adapter (ARCH-15 PR-3) — the CLI channel's sink.

Renders `result.text` to a sink (stdout by default; injectable for tests). Origin-pairable on the
`cli` channel so the OutputManager routes a CLI-originated conversational result back to the
terminal (D-2). TEXT-only — SPEECH degrades to TEXT via the §3.1 negotiation upstream.
"""

from typing import Callable, Optional, Set

from ..core.interfaces.output import DeliveryResult, OutputModality, OutputPort
from ..intents.models import IntentResult
from ..intents.context_models import RequestContext


def _default_sink(line: str) -> None:
    print(line)


class ConsoleOutput(OutputPort):
    """Terminal text sink."""

    def __init__(self, sink: Optional[Callable[[str], None]] = None,
                 origin: str = "cli", prefix: str = "📝 ") -> None:
        self._sink = sink or _default_sink
        self._origin = origin
        self._prefix = prefix

    def supported_modalities(self) -> Set[OutputModality]:
        return {OutputModality.TEXT}

    async def deliver(self, result: IntentResult, context: RequestContext,
                      modality: OutputModality) -> DeliveryResult:
        self._sink(f"{self._prefix}{result.text}")
        return DeliveryResult.ok("console", OutputModality.TEXT)

    def get_output_type(self) -> str:
        return "console"

    def origin_key(self) -> Optional[str]:
        return self._origin
