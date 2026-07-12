"""WebSocket clients for the satellite ↔ controller wire contracts (ARCH-36).

Uplink (`/ws/audio`, design §3): register → registered → PCM16 frames → end → response.
Downlink (`/ws/audio/reply`, design §4): register-reply → registered → speak_begin/PCM/speak_end.

Both ride aiohttp (a base dependency); TLS is a property of the deployment, not the protocol —
pass an `ssl.SSLContext` (built by `provisioning.build_ssl_context`) for mTLS `wss://`, or none
for plain local `ws://`. Reconnect policy (design §3): exponential backoff 1 → 30 s with
re-register on every new connection.
"""

import asyncio
import json
import logging
import ssl
from typing import Any, Awaitable, Callable, Dict, List, Optional

import aiohttp

from ..__version__ import __version__ as IRENE_VERSION
from ..core.ws_protocol import WS_PROTOCOL_VERSION

logger = logging.getLogger(__name__)

BACKOFF_INITIAL_S = 1.0
BACKOFF_MAX_S = 30.0

# Uplink frame size: ~32 ms of 16 kHz mono PCM16 — matches the locveil-eval provider the
# protocol was proven with (frame size, not wall-clock pacing; the server just accumulates).
FRAME_MS = 32


def _frames(pcm: bytes, sample_rate: int, frame_ms: int = FRAME_MS) -> List[bytes]:
    step = max(2, int(sample_rate * 2 * frame_ms / 1000) & ~1)  # 16-bit mono, even-aligned
    return [pcm[i:i + step] for i in range(0, len(pcm), step)]


def _next_backoff(current: float) -> float:
    return min(current * 2, BACKOFF_MAX_S)


class SatelliteLink:
    """Persistent `/ws/audio` uplink client (one per satellite).

    `connect()` performs the register handshake; `ensure_connected()` adds the backoff loop.
    In `single` mode each utterance is `send_utterance(pcm)` — frames + `end` + await the
    final `response`. In `streaming` mode the caller pumps `send_frame()` continuously and
    consumes `receive()` (partials + responses) — server-authoritative endpointing (ARCH-10).
    """

    def __init__(self, server_url: str, client_id: str, room_name: str, *,
                 sample_rate: int = 16000, mode: str = "single",
                 wants_audio: bool = True, wants_trace: bool = False,
                 ssl_context: Optional[ssl.SSLContext] = None,
                 response_timeout_s: float = 30.0) -> None:
        self.server_url = server_url.rstrip("/")
        self.client_id = client_id
        self.room_name = room_name
        self.sample_rate = sample_rate
        self.mode = mode
        self.wants_audio = wants_audio
        # ARCH-37: ask the controller for its execution trace after each response. The grant
        # is explicit in the `registered` ack (`trace_granted`); when granted, `send_utterance`
        # also consumes the trace frame into `last_trace`.
        self.wants_trace = wants_trace
        self.trace_granted = False
        self.last_trace: Optional[Dict[str, Any]] = None
        self.response_timeout_s = response_timeout_s
        self._ssl = ssl_context
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.session_id: Optional[str] = None

    @property
    def connected(self) -> bool:
        return self._ws is not None and not self._ws.closed

    async def connect(self) -> None:
        """One connect + register attempt; raises on any failure (see `ensure_connected`)."""
        await self.close()
        self._session = aiohttp.ClientSession()
        try:
            ws = await self._session.ws_connect(
                f"{self.server_url}/ws/audio",
                ssl=self._ssl if self._ssl is not None else True, heartbeat=30.0)
            self._ws = ws
            await ws.send_json({
                "type": "register", "client_id": self.client_id, "room_name": self.room_name,
                "sample_rate": self.sample_rate, "wants_audio": self.wants_audio,
                "mode": self.mode, "wants_trace": self.wants_trace,
                # ARCH-47 version reporting: what this client was built against. The Python
                # runner IS the irene tree, so firmware == package version; wake_pack_version
                # is the flashed pack's tag — ESP32 territory, not reported from here.
                "protocol_version": WS_PROTOCOL_VERSION,
                "firmware_version": IRENE_VERSION,
            })
            reply = json.loads(await asyncio.wait_for(
                ws.receive_str(), timeout=self.response_timeout_s))
            if reply.get("type") != "registered":
                raise ConnectionError(f"registration rejected: {reply}")
            self.session_id = reply.get("session_id")
            self.trace_granted = bool(reply.get("trace", False))
            if self.wants_trace and not self.trace_granted:
                logger.info("Controller declined the trace request "
                            "([trace] allow_remote_request is off there)")
            logger.info(f"Uplink registered as '{self.client_id}' (session {self.session_id})")
        except BaseException:
            await self.close()
            raise

    async def ensure_connected(self) -> None:
        """Re-register with exponential backoff (1 → 30 s) until connected (design §3)."""
        backoff = BACKOFF_INITIAL_S
        while not self.connected:
            try:
                await self.connect()
                return
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"Uplink connect failed ({e}); retrying in {backoff:.0f}s")
                await asyncio.sleep(backoff)
                backoff = _next_backoff(backoff)

    async def close(self) -> None:
        if self._ws is not None and not self._ws.closed:
            await self._ws.close()
        self._ws = None
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    # --- single mode ---------------------------------------------------------------------------

    async def send_utterance(self, pcm: bytes) -> Dict[str, Any]:
        """One `single`-mode cycle: PCM frames → `end` → the final `response` dict.
        Raises `ConnectionError` if the socket drops mid-cycle (caller reconnects; the
        utterance is lost, which is the ESP32 contract too — no client-side replay)."""
        ws = self._ws
        if ws is None or ws.closed:
            raise ConnectionError("uplink not connected")
        try:
            for frame in _frames(pcm, self.sample_rate):
                await ws.send_bytes(frame)
            await ws.send_json({"type": "end"})
        except (aiohttp.ClientError, ConnectionResetError) as e:
            raise ConnectionError(f"uplink dropped mid-utterance: {e}") from e
        self.last_trace = None
        response = await self._await_response()
        if self.trace_granted:
            self.last_trace = await self._await_trace()
        return response

    async def _await_response(self) -> Dict[str, Any]:
        ws = self._ws
        if ws is None:
            raise ConnectionError("uplink not connected")
        deadline = asyncio.get_running_loop().time() + self.response_timeout_s
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise TimeoutError("no response within response_timeout_s")
            msg = await asyncio.wait_for(ws.receive(), timeout=remaining)
            if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING,
                            aiohttp.WSMsgType.ERROR):
                raise ConnectionError("uplink closed while awaiting response")
            if msg.type != aiohttp.WSMsgType.TEXT:
                continue
            payload = json.loads(msg.data)
            kind = payload.get("type")
            if kind == "response":
                return payload
            if kind == "error":
                raise ConnectionError(f"server error: {payload.get('error')}")
            # partials and unknown control frames are informational in single mode

    async def _await_trace(self) -> Optional[Dict[str, Any]]:
        """The granted trace frame following a response (ARCH-37). Bounded wait; a missing
        frame degrades to None (recorded as such in the merged file), never an error."""
        ws = self._ws
        if ws is None:
            return None
        deadline = asyncio.get_running_loop().time() + self.response_timeout_s
        try:
            while True:
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    logger.warning("Trace frame did not arrive within response_timeout_s")
                    return None
                msg = await asyncio.wait_for(ws.receive(), timeout=remaining)
                if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING,
                                aiohttp.WSMsgType.ERROR):
                    return None
                if msg.type != aiohttp.WSMsgType.TEXT:
                    continue
                payload = json.loads(msg.data)
                if payload.get("type") == "trace":
                    return payload
        except asyncio.TimeoutError:
            logger.warning("Trace frame did not arrive within response_timeout_s")
            return None

    # --- streaming mode ------------------------------------------------------------------------

    async def send_frame(self, pcm: bytes) -> None:
        ws = self._ws
        if ws is None or ws.closed:
            raise ConnectionError("uplink not connected")
        try:
            await ws.send_bytes(pcm)
        except (aiohttp.ClientError, ConnectionResetError) as e:
            raise ConnectionError(f"uplink dropped: {e}") from e

    async def receive(self) -> Dict[str, Any]:
        """Next TEXT control frame (`partial` / `response` / `error`) — streaming-mode reader."""
        ws = self._ws
        if ws is None or ws.closed:
            raise ConnectionError("uplink not connected")
        while True:
            msg = await ws.receive()
            if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING,
                            aiohttp.WSMsgType.ERROR):
                raise ConnectionError("uplink closed")
            if msg.type == aiohttp.WSMsgType.TEXT:
                return json.loads(msg.data)


class SatelliteReplyClient:
    """`/ws/audio/reply` downlink: registers the reply channel and plays framed PCM.

    `play` is an async callable `(pcm: bytes, rate: int, channels: int) -> None` — the runner
    wires it to the audio component's `play_stream`. `run()` owns its own reconnect loop; on
    every (re)connect the controller drains undelivered completion notices to us (ARCH-28 D-6),
    so a timer that rang during a reboot speaks as soon as we're back.
    """

    def __init__(self, server_url: str, client_id: str,
                 play: Callable[[bytes, int, int], Awaitable[None]], *,
                 rate: int = 22050, channels: int = 1,
                 ssl_context: Optional[ssl.SSLContext] = None) -> None:
        self.server_url = server_url.rstrip("/")
        self.client_id = client_id
        self.play = play
        self.rate = rate
        self.channels = channels
        self._ssl = ssl_context
        self._stop = asyncio.Event()

    def stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        backoff = BACKOFF_INITIAL_S
        while not self._stop.is_set():
            try:
                await self._serve_once()
                backoff = BACKOFF_INITIAL_S  # a served connection resets the ladder
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"Reply channel dropped ({e}); reconnecting in {backoff:.0f}s")
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=backoff)
                except asyncio.TimeoutError:
                    pass
                backoff = _next_backoff(backoff)

    async def _serve_once(self) -> None:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                    f"{self.server_url}/ws/audio/reply",
                    ssl=self._ssl if self._ssl is not None else True, heartbeat=30.0) as ws:
                await ws.send_json({"type": "register-reply", "client_id": self.client_id,
                                    "audio_out": {"rate": self.rate, "channels": self.channels}})
                reply = json.loads(await ws.receive_str())
                if reply.get("type") != "registered":
                    raise ConnectionError(f"reply registration rejected: {reply}")
                logger.info(f"Reply channel registered as '{self.client_id}'")
                await self._speak_loop(ws)

    async def _speak_loop(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        """speak_begin → BINARY PCM* → speak_end, repeated until disconnect (design §4)."""
        pcm = bytearray()
        rate, channels = self.rate, self.channels
        speaking = False
        while True:
            msg = await ws.receive()
            if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING,
                            aiohttp.WSMsgType.ERROR):
                raise ConnectionError("reply channel closed")
            if msg.type == aiohttp.WSMsgType.BINARY:
                if speaking:
                    pcm.extend(msg.data)
                continue
            if msg.type != aiohttp.WSMsgType.TEXT:
                continue
            control = json.loads(msg.data)
            kind = control.get("type")
            if kind == "speak_begin":
                speaking = True
                pcm.clear()
                rate = int(control.get("rate", self.rate))
                channels = int(control.get("channels", self.channels))
            elif kind == "speak_end" and speaking:
                speaking = False
                if pcm:
                    try:
                        await self.play(bytes(pcm), rate, channels)
                    except Exception as e:
                        logger.error(f"Reply playback failed: {e}")
                pcm.clear()
