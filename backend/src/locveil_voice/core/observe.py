"""Observation-tap helpers (ARCH-15 PR-6b) — gating + bus→queue bridging.

The tap lets a debug client subscribe to the pipeline event bus (§5). These two helpers are the
testable core of the `/ws/observe` endpoint:

- `authorize_observer` — the gating decision (D-5): disabled unless a token is configured;
  localhost-only unless `allow_remote`; then the token must match.
- `subscribe_to_queue` — funnels matching events into a bounded `asyncio.Queue`, decoupling a slow
  observer from the publishing pipeline (a full queue drops the OLDEST event rather than blocking
  `EventBus.publish`, so a stuck tap can never stall the workflow).
"""

import asyncio
from typing import Callable, Optional, Tuple

from .event_bus import EventBus, EventFilter, PipelineEvent

# Loopback hosts treated as "local" for the localhost-first gate.
LOCAL_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", "::ffff:127.0.0.1"})


def authorize_observer(client_host: Optional[str], provided_token: Optional[str], *,
                       configured_token: Optional[str], allow_remote: bool) -> bool:
    """Return True iff this observer connection is allowed (D-5 gating)."""
    if configured_token is None:
        return False  # tap is disabled unless a token is configured
    if not allow_remote and client_host not in LOCAL_HOSTS:
        return False  # localhost-first
    return provided_token == configured_token


def subscribe_to_queue(bus: EventBus, event_filter: Optional[EventFilter] = None,
                       maxsize: int = 1000) -> Tuple["asyncio.Queue[PipelineEvent]", Callable[[], None]]:
    """Subscribe `bus` and funnel matching events into a bounded queue. Returns (queue, unsubscribe)."""
    queue: "asyncio.Queue[PipelineEvent]" = asyncio.Queue(maxsize=maxsize)

    async def _handler(ev: PipelineEvent) -> None:
        if queue.full():
            try:
                queue.get_nowait()  # drop oldest to stay non-blocking
            except asyncio.QueueEmpty:
                pass
        try:
            queue.put_nowait(ev)
        except asyncio.QueueFull:
            pass

    unsubscribe = bus.subscribe(_handler, event_filter)
    return queue, unsubscribe
