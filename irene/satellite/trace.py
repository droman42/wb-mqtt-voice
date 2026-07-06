"""Satellite-side trace recorder (ARCH-38, design `docs/design/satellite_tracing.md`).

One merged self-contained file per sent utterance (T-3): the device story — raw mic ring,
per-frame VAD verdicts, wake-gate decisions, uplink lifecycle — with the controller's
execution trace nested under `controller_trace` and the reply audio (as played) under
`reply_audio`. Files land in the satellite's own `<assets_root>/traces/` with the standard
ARCH-19 rotation.

Finalization is deterministic (T-5, no timers): a pending trace is written when its reply
audio arrives, when the next utterance is sent, or at shutdown — whichever comes first.
"""

import base64
import logging
import time
from collections import deque
from typing import Any, Dict, List, Optional

from ..core.trace_context import TraceContext, resolve_traces_dir, _prune_trace_dir

logger = logging.getLogger(__name__)

# Raw-mic ring bound: enough to cover VAD pre-roll + the longest utterance the satellite
# sends (the segmenter's max_segment_duration_s ceiling is 10s by default) with headroom.
RAW_RING_SECONDS = 30.0

# Wake/gate decisions are captured as a rolling window attached to the NEXT sent utterance —
# a skipped segment doesn't get its own file (noise), but its skip verdict stays visible.
GATE_EVENTS_KEPT = 20


class SatelliteTraceRecorder:
    """Collects device-side stages per utterance and writes the merged envelope."""

    def __init__(self, trace_config: Any, assets_config: Any, *,
                 client_id: str, room_name: str, mode: str) -> None:
        self._cfg = trace_config
        self._assets = assets_config
        self._identity = {"source": "satellite", "client_id": client_id,
                          "room": room_name, "mode": mode}
        self._raw_ring: deque = deque()  # (timestamp, AudioData) when capture_raw_mic
        self._gate_events: deque = deque(maxlen=GATE_EVENTS_KEPT)
        self._pending: Optional[Dict[str, Any]] = None  # envelope awaiting reply audio

    # --- rolling capture (before any utterance exists) ---------------------------------------------

    def on_raw_chunk(self, audio: Any) -> None:
        """Pre-canonical mic audio into the bounded ring (only with --trace-raw-mic)."""
        if not getattr(self._cfg, "capture_raw_mic", False):
            return
        now = getattr(audio, "timestamp", None) or time.time()
        self._raw_ring.append((now, audio))
        while self._raw_ring and now - self._raw_ring[0][0] > RAW_RING_SECONDS:
            self._raw_ring.popleft()

    def on_wake(self, *, confidence: float, armed_at: float) -> None:
        self._gate_events.append({"t": armed_at, "event": "wake_detected",
                                  "confidence": confidence})

    def on_gate_skip(self, *, segment_start: float, armed_at: Optional[float]) -> None:
        self._gate_events.append({"t": time.time(), "event": "segment_skipped",
                                  "segment_start": segment_start, "armed_at": armed_at})

    # --- per-utterance lifecycle --------------------------------------------------------------------

    def complete_utterance(self, *, segment: Any, pcm: bytes, sample_rate: int,
                           response: Optional[Dict[str, Any]], error: Optional[str],
                           rtt_ms: float, trace_granted: bool,
                           controller_trace: Optional[Dict[str, Any]]) -> None:
        """Assemble the merged envelope for one SENT utterance; held pending for reply audio."""
        self.flush()  # a previous pending trace is finalized by the next utterance (T-5)

        trace = TraceContext(enabled=True,
                             max_stages=getattr(self._cfg, "max_stages", 100),
                             max_data_size_mb=getattr(self._cfg, "max_data_size_mb", 10))
        trace.capture_level = getattr(self._cfg, "capture_level", "utterance")
        trace.record_input("audio", audio_bytes=pcm,
                           audio_format={"rate": sample_rate, "channels": 1, "format": "pcm16"})
        trace.record_request(dict(self._identity))
        for frame in getattr(segment, "vad_frames", None) or []:
            trace.add_vad_frame(t_ms=frame.get("t_ms", 0), is_voice=frame.get("is_voice", False),
                                energy=frame.get("energy", 0.0),
                                threshold=frame.get("threshold", 0.0))
        trace.record_stage("wake_gate",
                           input_data={"recent_events": list(self._gate_events)},
                           output_data={"sent": True},
                           metadata={}, processing_time_ms=0.0)
        trace.record_stage("uplink",
                           input_data={"pcm_bytes": len(pcm), "mode": self._identity["mode"]},
                           output_data=response if response is not None else {"error": error},
                           metadata={}, processing_time_ms=rtt_ms)
        self._gate_events.clear()

        envelope = trace.build_envelope()
        if not trace_granted:
            envelope["controller_trace"] = {"declined": True}
        elif controller_trace is None:
            envelope["controller_trace"] = {"missing": "trace frame did not arrive"}
        else:
            envelope["controller_trace"] = controller_trace.get("trace", controller_trace)
        raw = self._raw_window(getattr(segment, "start_timestamp", 0.0) - 3.0)
        if raw is not None:
            envelope["raw_mic"] = raw
        self._pending = {"request_id": trace.request_id, "envelope": envelope}

    def on_reply(self, pcm: bytes, rate: int, channels: int) -> None:
        """Reply audio as played — attaches to the pending utterance and finalizes it."""
        if self._pending is None:
            return
        self._pending["envelope"]["reply_audio"] = {
            "audio_base64": base64.b64encode(pcm).decode("utf-8"),
            "rate": rate, "channels": channels,
        }
        self.flush()

    def flush(self) -> None:
        """Write the pending envelope, if any (next-utterance / shutdown finalization)."""
        pending, self._pending = self._pending, None
        if pending is None:
            return
        try:
            import json
            out = resolve_traces_dir(self._cfg, self._assets) / f"{pending['request_id']}.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(pending["envelope"], ensure_ascii=False, indent=2),
                           encoding="utf-8")
            _prune_trace_dir(out.parent)
            logger.info(f"Satellite trace saved → {out}")
        except Exception as e:
            logger.error(f"Satellite trace not saved: {e}")

    # --- helpers --------------------------------------------------------------------------------------

    def _raw_window(self, since: float) -> Optional[Dict[str, Any]]:
        if not getattr(self._cfg, "capture_raw_mic", False) or not self._raw_ring:
            return None
        chunks: List[bytes] = [getattr(a, "data", b"") for (t, a) in self._raw_ring if t >= since]
        if not chunks:
            return None
        first = next(a for (t, a) in self._raw_ring if t >= since)
        return {
            "audio_base64": base64.b64encode(b"".join(chunks)).decode("utf-8"),
            "rate": getattr(first, "sample_rate", 16000),
            "channels": getattr(first, "channels", 1),
            "window_since": since,
        }
