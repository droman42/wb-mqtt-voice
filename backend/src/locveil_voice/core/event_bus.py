"""Pipeline event bus — one stream, two kinds of subscriber (ARCH-15 PR-2 / io_architecture §5).

A single in-process async pub/sub stream of pipeline-lifecycle events. The OutputManager
subscribes for **delivery** (origin-filtered); the debug tap subscribes for **observation**
(identity-filtered, read-only). The bus itself is generic — it does not know about either.

The event vocabulary is defined **once** here and reused for `/trace`, live-observe, and metrics.
Subscriber failures are isolated so one bad observer can never break delivery or the pipeline.
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class EventType(Enum):
    """The canonical pipeline-event vocabulary (§5)."""
    INPUT_RECEIVED = "input.received"
    ASR_TRANSCRIPT = "asr.transcript"
    INTENT_RECOGNIZED = "intent.recognized"
    RESULT_PRODUCED = "result.produced"
    OUTPUT_DELIVERED = "output.delivered"
    ERROR = "error"


@dataclass
class PipelineEvent:
    """One lifecycle event. Identity fields (session/client/room/source) carry the origin so both
    delivery (origin-paired) and observation (identity-filtered) subscribers can route/filter."""
    type: EventType
    session_id: Optional[str] = None
    client_id: Optional[str] = None
    room_name: Optional[str] = None
    source: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


EventFilter = Callable[[PipelineEvent], bool]
EventHandler = Callable[[PipelineEvent], Awaitable[None]]


def identity_filter(*, session_id: Optional[str] = None, client_id: Optional[str] = None,
                    room_name: Optional[str] = None, source: Optional[str] = None,
                    types: Optional[List[EventType]] = None) -> EventFilter:
    """Build a filter matching only the provided fields (others ignored). Used by the delivery
    subscriber (origin pairing) and the observation tap (watch a room/client/session)."""
    def _match(ev: PipelineEvent) -> bool:
        if types is not None and ev.type not in types:
            return False
        if session_id is not None and ev.session_id != session_id:
            return False
        if client_id is not None and ev.client_id != client_id:
            return False
        if room_name is not None and ev.room_name != room_name:
            return False
        if source is not None and ev.source != source:
            return False
        return True
    return _match


@dataclass
class _Subscription:
    handler: EventHandler
    filter: Optional[EventFilter]


class EventBus:
    """Generic async pub/sub. `subscribe()` returns an unsubscribe callable."""

    def __init__(self) -> None:
        self._subs: List[_Subscription] = []

    def subscribe(self, handler: EventHandler,
                  event_filter: Optional[EventFilter] = None) -> Callable[[], None]:
        sub = _Subscription(handler, event_filter)
        self._subs.append(sub)

        def _unsubscribe() -> None:
            if sub in self._subs:
                self._subs.remove(sub)

        return _unsubscribe

    @property
    def subscriber_count(self) -> int:
        return len(self._subs)

    async def publish(self, event: PipelineEvent) -> None:
        """Fan out to all matching subscribers. A subscriber that raises is logged and skipped —
        it never propagates to the publisher (delivery/observation must not break the pipeline)."""
        for sub in list(self._subs):
            if sub.filter is not None and not sub.filter(event):
                continue
            try:
                await sub.handler(event)
            except Exception as e:  # noqa: BLE001 — isolate subscriber failures by design
                logger.error(f"Event subscriber failed for {event.type.value}: {e}")
