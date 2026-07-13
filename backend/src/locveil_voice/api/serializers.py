"""The ONE IntentResult → API projection (QUAL-55).

Five surfaces serialize the same IntentResult — REST ``/execute/command`` and
``/execute/audio`` (CommandResponse), ``/trace/command`` and ``/trace/audio``
(TraceCommandResponse.final_result), and the WS ``/ws/audio`` ``response`` frame.
Before QUAL-55 each hand-built its own dict and the shapes drifted
(`docs/review/api_result_contract_review.md` F1–F4: reply under ``response`` vs
``text``, ``intent_name`` present on one surface only, two different metadata
payloads under one response model, ``confidence`` wandering between levels).

This function is the single projection they all route through. Canonical keys:

- ``text`` — the reply text (F1: canonical name; ``/execute/*`` used ``response``)
- ``success`` / ``error`` — handler outcome (error is None on success)
- ``confidence`` — always top-level (F4)
- ``intent_name`` — lifted from the orchestrator's ``original_intent`` metadata
  key, the one key it actually writes (F2)
- ``timestamp`` — the result's own timestamp
- ``metadata`` — the RAW internal metadata dict; endpoint-specific extras merge
  into it (F3: one response shape, extras inside metadata — never a replacement)
"""

from typing import Any, Dict, Optional

from ..intents.models import IntentResult


def serialize_intent_result(result: IntentResult,
                            extra_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Project an IntentResult onto the canonical API payload (see module docstring)."""
    metadata = dict(result.metadata or {})
    if extra_metadata:
        metadata.update(extra_metadata)
    return {
        "text": result.text or "",
        "success": result.success,
        "error": result.error,
        "confidence": result.confidence,
        "intent_name": metadata.get("original_intent"),
        "timestamp": result.timestamp,
        "metadata": metadata,
    }
