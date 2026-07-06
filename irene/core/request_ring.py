"""Rolling ring of recent request summaries (ARCH-32, design §3).

Trace *persistence* (ARCH-19) is opt-in and off in deployments — but a problem report needs to
show what the last few requests actually did. This ring is the always-on, deliberately compact
middle ground: one small dict per request (texts, the NLU verdict, the outcome), dumped ONLY
into support bundles. Depth is `[reports] ring_size` (design D-10); memory cost is a few KB.
"""

import threading
import time
from collections import deque
from typing import Any, Dict, List

_DEFAULT_SIZE = 5
_MAX_TEXT = 500  # per-field clip: the ring is a synopsis, not a transcript


class RequestRing:
    """Thread-safe fixed-depth ring of per-request summary records."""

    def __init__(self, size: int = _DEFAULT_SIZE):
        self._records: deque = deque(maxlen=size)
        self._lock = threading.Lock()

    def resize(self, size: int) -> None:
        with self._lock:
            self._records = deque(self._records, maxlen=size)

    def append(self, *, session_id: str, room: Any, language: Any,
               input_text: str, processed_text: str,
               intent_name: str, confidence: float, nlu_provider: Any,
               result_text: str, success: bool, error: Any = None) -> None:
        record = {
            "timestamp": time.time(),
            "session_id": session_id,
            "room": room,
            "language": language,
            "input_text": (input_text or "")[:_MAX_TEXT],
            "processed_text": (processed_text or "")[:_MAX_TEXT],
            "intent_name": intent_name,
            "confidence": confidence,
            "nlu_provider": nlu_provider,
            "result_text": (result_text or "")[:_MAX_TEXT],
            "success": success,
            "error": error,
        }
        with self._lock:
            self._records.append(record)

    def dump(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._records)


_ring = RequestRing()


def get_request_ring() -> RequestRing:
    """Process-wide ring (the get_client_registry pattern)."""
    return _ring
