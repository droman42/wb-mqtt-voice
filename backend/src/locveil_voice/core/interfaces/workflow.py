"""
Workflow Port - The orchestration contract for workflows.

ARCH-11 / S2: the abstraction that `core` (WorkflowManager) depends on, lifted
into the port layer so `core` no longer imports `workflows.base` outward. The
shared pipeline implementation stays in `irene/workflows/base.Workflow`, which
implements this port.

Rooted on `EntryPointMetadata` (decision (c)), matching the live `Workflow`
hierarchy. `RequestContext` is NOT re-exported here — it is a domain type
(`intents/context_models.py`) that `core` imports directly inward.
"""

from typing import Any, AsyncIterator, Dict, Optional
from abc import ABC, abstractmethod

from ..metadata import EntryPointMetadata
from ..trace_context import TraceContext
from ...intents.models import AudioData, IntentResult
from ...intents.context_models import RequestContext


class WorkflowPort(EntryPointMetadata, ABC):
    """
    Port for workflows.

    Declares only the generic surface WorkflowManager relies on for
    generically-typed workflows. Concrete-only entry points used via the
    specific workflow type (e.g. `process_audio_input`, `cleanup`) are not part
    of this contract. See `irene/workflows/base.Workflow` for the shared
    implementation.
    """

    # Instance attributes established by the implementation's __init__:
    name: str
    components: Dict[str, Any]
    initialized: bool

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the workflow."""
        ...

    @abstractmethod
    def add_component(self, name: str, component: Any) -> None:
        """Inject a component the workflow's pipeline stages depend on."""
        ...

    @abstractmethod
    async def process_audio_stream(
        self, audio_stream: AsyncIterator[AudioData], context: RequestContext
    ) -> AsyncIterator[IntentResult]:
        """Process a continuous audio stream, yielding intent results."""
        # Async-generator stub: the unreachable `yield` types this as an async
        # generator so concrete implementations (which yield results) override it
        # compatibly. Same pattern as `InputPort.listen`.
        return
        yield

    @abstractmethod
    async def process_text_input(self, text: str, context: RequestContext,
                                 trace_context: Optional[TraceContext] = None) -> IntentResult:
        """Process a single text command end-to-end."""
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """Shut the workflow down and release resources."""
        ...
