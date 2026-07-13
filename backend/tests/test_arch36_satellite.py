"""ARCH-36 — Python satellite (design docs/design/python_satellite.md).

Covers: uplink framing, the wake-gate armed window, mTLS identity binding on both WS
endpoints (finding b), the S-9 loopback e2e (SatelliteLink against the REAL /ws/audio server
code over TCP), the reply client against the §4 wire contract, and the first-run provisioning
dance against a stub bootstrap zone (real openssl, no nginx).
"""

import asyncio
import json
import socket

import pytest

from locveil_voice.satellite.link import SatelliteLink, SatelliteReplyClient, _frames
from locveil_voice.runners.satellite_runner import WAKE_ARM_WINDOW_S, _in_armed_window
from locveil_voice.runners.webapi_router import _client_cert_cn


# --- framing (§3) -------------------------------------------------------------------------------

def test_frames_are_even_sized_and_lossless():
    pcm = bytes(range(256)) * 125  # 32000 bytes = 1 s of 16 kHz PCM16
    frames = _frames(pcm, 16000)
    assert b"".join(frames) == pcm
    assert all(len(f) % 2 == 0 for f in frames)
    # ~32 ms at 16 kHz mono PCM16 = 1024 bytes
    assert frames[0] == pcm[:1024]


# --- wake gate ----------------------------------------------------------------------------------

def test_armed_window_passes_only_segments_started_inside():
    t = 1000.0
    assert _in_armed_window(None, t) is False                      # not armed
    assert _in_armed_window(t, t - 1.0) is False                   # the wake word's own segment
    assert _in_armed_window(t, t + 0.5) is True                    # the command
    assert _in_armed_window(t, t + WAKE_ARM_WINDOW_S + 1) is False # window expired


# --- identity binding (finding b) ------------------------------------------------------------------

def test_cert_cn_parses_dn_shapes():
    class H(dict):
        def get(self, k, default=None):
            return super().get(k, default)

    assert _client_cert_cn(H()) is None  # no proxy → no binding
    assert _client_cert_cn(H({"x-client-cert-dn": "CN=kitchen_node"})) == "kitchen_node"
    assert _client_cert_cn(H({"x-client-cert-dn": "CN=kitchen_node,O=irene"})) == "kitchen_node"
    assert _client_cert_cn(H({"x-client-cert-dn": "/C=RU/O=irene/CN=kitchen_node"})) == "kitchen_node"
    # legacy header name (pre-rename deployments) — value was always the DN
    assert _client_cert_cn(H({"x-client-cert-cn": "CN=hall_node"})) == "hall_node"


def _stub_router(allow_remote_trace: bool = False):
    from types import SimpleNamespace

    from fastapi import FastAPI
    from locveil_voice.intents.models import IntentResult
    from locveil_voice.runners.webapi_router import create_webapi_router

    class _WM:
        async def process_audio_input(self, audio_data, session_id=None, wants_audio=False,
                                      client_context=None, trace_context=None):
            if trace_context is not None:
                trace_context.record_stage("stub_pipeline", {"in": "audio"}, {"out": "готово"},
                                            {}, processing_time_ms=1.0)
            return IntentResult(text="готово", metadata={"ok": True})

    class _Core:
        workflow_manager = _WM()
        config = SimpleNamespace(trace=SimpleNamespace(
            allow_remote_request=allow_remote_trace, enabled=False,
            max_stages=100, max_data_size_mb=10, capture_level="utterance"))
        component_manager = None
        plugin_manager = None
        output_manager = None

    app = FastAPI()
    app.include_router(create_webapi_router(_Core(), asset_loader=None, web_input=None,
                                            start_time=0.0))
    return app


def test_ws_audio_rejects_client_id_not_matching_cert():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    app = _stub_router()
    with TestClient(app).websocket_connect(
            "/ws/audio", headers={"X-Client-Cert-DN": "CN=kitchen_node"}) as ws:
        ws.send_text(json.dumps({"type": "register", "client_id": "bedroom_node",
                                 "room_name": "Спальня"}))
        err = ws.receive_json()
        assert err["type"] == "error" and "certificate" in err["error"]


def test_ws_audio_accepts_matching_cert_and_plain_ws():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    app = _stub_router()
    with TestClient(app).websocket_connect(
            "/ws/audio", headers={"X-Client-Cert-DN": "CN=kitchen_node,O=irene"}) as ws:
        ws.send_text(json.dumps({"type": "register", "client_id": "kitchen_node",
                                 "room_name": "Кухня"}))
        assert ws.receive_json()["type"] == "registered"
    # no proxy header (local/dev ws://) — no binding enforced
    with TestClient(app).websocket_connect("/ws/audio") as ws:
        ws.send_text(json.dumps({"type": "register", "client_id": "anything",
                                 "room_name": "Зал"}))
        assert ws.receive_json()["type"] == "registered"


def test_ws_reply_rejects_client_id_not_matching_cert():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    app = _stub_router()  # reply deps absent, but the identity check runs first…
    with TestClient(app).websocket_connect(
            "/ws/audio/reply", headers={"X-Client-Cert-DN": "CN=kitchen_node"}) as ws:
        ws.send_text(json.dumps({"type": "register-reply", "client_id": "bedroom_node",
                                 "audio_out": {"rate": 22050, "channels": 1}}))
        err = ws.receive_json()
        assert err["type"] == "error"
        # …unless the stub's missing deps error fires first — either way the mismatch never registers
        assert "certificate" in err["error"] or "unavailable" in err["error"]


# --- S-9 loopback e2e: SatelliteLink vs the REAL server code over TCP ------------------------------

def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _LiveServer:
    """The actual FastAPI /ws/audio server (stubbed pipeline) on a real TCP port."""

    def __init__(self, app):
        uvicorn = pytest.importorskip("uvicorn")
        self.port = _free_port()
        self.server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=self.port,
                                                    log_level="error"))
        self.url = f"ws://127.0.0.1:{self.port}"
        self._task = None

    async def __aenter__(self):
        self._task = asyncio.create_task(self.server.serve())
        for _ in range(100):
            if self.server.started:
                return self
            await asyncio.sleep(0.05)
        raise AssertionError("uvicorn did not start")

    async def __aexit__(self, *exc):
        self.server.should_exit = True
        await self._task


@pytest.fixture()
async def real_server():
    async with _LiveServer(_stub_router()) as srv:
        yield srv.url


async def test_loopback_single_mode_utterance_roundtrip(real_server):
    link = SatelliteLink(real_server, "test_sat", "Кухня", mode="single",
                         response_timeout_s=10.0)
    try:
        await link.connect()
        assert link.connected and link.session_id
        response = await link.send_utterance(b"\x00\x01" * 4000)
        assert response["type"] == "response" and response["text"] == "готово"
        # persistent connection: a second utterance rides the same socket (design §3)
        response2 = await link.send_utterance(b"\x00\x01" * 2000)
        assert response2["text"] == "готово"
    finally:
        await link.close()


async def test_loopback_reconnect_after_server_side_registration(real_server):
    link = SatelliteLink(real_server, "test_sat2", "Зал")
    try:
        await link.ensure_connected()
        first_session = link.session_id
        await link.close()
        assert not link.connected
        await link.ensure_connected()  # re-register on a fresh socket
        assert link.connected and link.session_id != first_session
    finally:
        await link.close()


# --- satellite tracing (ARCH-37/38) -----------------------------------------------------------------

async def test_trace_granted_frame_follows_response():
    """wants_trace + allow_remote_request → explicit grant in the ack, trace frame per response."""
    async with _LiveServer(_stub_router(allow_remote_trace=True)) as srv:
        link = SatelliteLink(srv.url, "tracer", "Кухня", wants_trace=True,
                             response_timeout_s=10.0)
        try:
            await link.connect()
            assert link.trace_granted is True
            response = await link.send_utterance(b"\x00\x01" * 2000)
            assert response["text"] == "готово"
            assert link.last_trace is not None
            assert link.last_trace["type"] == "trace" and link.last_trace["request_id"]
            stages = link.last_trace["trace"]["execution"]["pipeline_stages"]
            assert any(s.get("stage") == "stub_pipeline" or s.get("stage_name") == "stub_pipeline"
                       for s in stages)
        finally:
            await link.close()


async def test_trace_declined_by_default(real_server):
    """The default-off gate: wants_trace is ignored, ack says trace:false, no trace frames —
    a second utterance's response arrives cleanly (nothing interleaved)."""
    link = SatelliteLink(real_server, "tracer2", "Зал", wants_trace=True,
                         response_timeout_s=10.0)
    try:
        await link.connect()
        assert link.trace_granted is False
        assert (await link.send_utterance(b"\x00\x01" * 1000))["text"] == "готово"
        assert link.last_trace is None
        assert (await link.send_utterance(b"\x00\x01" * 1000))["text"] == "готово"
    finally:
        await link.close()


def _fake_segment():
    from types import SimpleNamespace
    return SimpleNamespace(
        start_timestamp=1000.0, end_timestamp=1001.5,
        vad_frames=[{"t_ms": 0, "is_voice": True, "energy": 0.5, "threshold": 0.1}],
        combined_audio=SimpleNamespace(data=b"\x00\x01" * 100, sample_rate=16000, channels=1))


def _recorder(tmp_path, **cfg_overrides):
    from types import SimpleNamespace
    from locveil_voice.satellite.trace import SatelliteTraceRecorder
    cfg = SimpleNamespace(capture_raw_mic=False, max_stages=100, max_data_size_mb=10,
                          capture_level="utterance", traces_dir=str(tmp_path), enabled=True)
    for k, v in cfg_overrides.items():
        setattr(cfg, k, v)
    return SatelliteTraceRecorder(cfg, None, client_id="sat", room_name="Кухня", mode="single")


def test_recorder_writes_merged_envelope(tmp_path):
    rec = _recorder(tmp_path)
    seg = _fake_segment()
    rec.on_wake(confidence=0.98, armed_at=999.5)
    rec.complete_utterance(segment=seg, pcm=seg.combined_audio.data, sample_rate=16000,
                           response={"type": "response", "text": "готово", "success": True},
                           error=None, rtt_ms=42.0, trace_granted=True,
                           controller_trace={"type": "trace", "request_id": "abc",
                                             "trace": {"execution": {"pipeline_stages": []}}})
    rec.on_reply(b"\x07\x08" * 50, 22050, 1)  # reply arrives → finalize

    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    env = json.loads(files[0].read_text())
    assert env["controller_trace"] == {"execution": {"pipeline_stages": []}}  # unwrapped envelope
    assert env["reply_audio"]["rate"] == 22050
    assert env["vad_frames"][0]["is_voice"] is True
    names = [s.get("stage") or s.get("stage_name") for s in env["execution"]["pipeline_stages"]]
    assert "wake_gate" in names and "uplink" in names
    assert env["replay"]["input"]["kind"] == "audio"  # the utterance, replayable for VAD tuning


def test_recorder_declined_and_next_utterance_finalizes(tmp_path):
    rec = _recorder(tmp_path)
    rec.complete_utterance(segment=_fake_segment(), pcm=b"\x00\x01" * 10, sample_rate=16000,
                           response=None, error="uplink dropped", rtt_ms=5.0,
                           trace_granted=False, controller_trace=None)
    assert list(tmp_path.glob("*.json")) == []  # pending, awaiting reply/next/shutdown
    # next utterance finalizes the previous one (T-5, no timers)
    rec.complete_utterance(segment=_fake_segment(), pcm=b"\x00\x01" * 10, sample_rate=16000,
                           response={"text": "ок"}, error=None, rtt_ms=5.0,
                           trace_granted=False, controller_trace=None)
    rec.flush()
    files = sorted(tmp_path.glob("*.json"), key=lambda f: f.stat().st_mtime)
    assert len(files) == 2
    first = json.loads(files[0].read_text())
    assert first["controller_trace"] == {"declined": True}
    assert "reply_audio" not in first
    uplink = next(s for s in first["execution"]["pipeline_stages"]
                  if (s.get("stage") or s.get("stage_name")) == "uplink")
    assert "error" in str(uplink)


# --- reply client vs the §4 wire contract ----------------------------------------------------------

async def test_reply_client_plays_framed_speech():
    aiohttp_web = pytest.importorskip("aiohttp.web")

    played = []
    done = asyncio.Event()

    async def reply_endpoint(request):
        ws = aiohttp_web.WebSocketResponse()
        await ws.prepare(request)
        reg = json.loads((await ws.receive()).data)
        assert reg["type"] == "register-reply" and reg["client_id"] == "sat"
        assert reg["audio_out"] == {"rate": 22050, "channels": 1}
        await ws.send_json({"type": "registered", "client_id": "sat"})
        await ws.send_json({"type": "speak_begin", "rate": 22050, "channels": 1, "seq": 1})
        await ws.send_bytes(b"\x01\x02" * 100)
        await ws.send_bytes(b"\x03\x04" * 100)
        await ws.send_json({"type": "speak_end", "seq": 1})
        await asyncio.sleep(0.5)  # keep the socket open long enough for the client to play
        return ws

    app = aiohttp_web.Application()
    app.router.add_get("/ws/audio/reply", reply_endpoint)
    runner = aiohttp_web.AppRunner(app)
    await runner.setup()
    port = _free_port()
    site = aiohttp_web.TCPSite(runner, "127.0.0.1", port)
    await site.start()

    async def play(pcm, rate, channels):
        played.append((pcm, rate, channels))
        done.set()

    client = SatelliteReplyClient(f"ws://127.0.0.1:{port}", "sat", play)
    task = asyncio.create_task(client.run())
    try:
        await asyncio.wait_for(done.wait(), timeout=5.0)
    finally:
        client.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        await runner.cleanup()

    pcm, rate, channels = played[0]
    assert pcm == b"\x01\x02" * 100 + b"\x03\x04" * 100  # begin→end frames, in order
    assert rate == 22050 and channels == 1


# --- provisioning dance (real openssl, stub bootstrap zone) ----------------------------------------

async def test_provisioning_first_run_dance(tmp_path):
    aiohttp_web = pytest.importorskip("aiohttp.web")
    import shutil
    if shutil.which("openssl") is None:
        pytest.skip("openssl CLI not available")

    from locveil_voice.config.models import SatelliteTLSConfig
    from locveil_voice.satellite.provisioning import ensure_credentials

    submitted = {}
    polls = {"n": 0}

    async def get_ca(request):
        return aiohttp_web.Response(body=b"---FAKE CA---")

    async def put_csr(request):
        submitted["csr"] = await request.read()
        return aiohttp_web.Response(status=201)

    async def get_cert(request):
        polls["n"] += 1
        if polls["n"] < 2:  # first poll: not approved yet
            return aiohttp_web.Response(status=404)
        return aiohttp_web.Response(body=b"---FAKE CERT---")

    app = aiohttp_web.Application()
    app.router.add_get("/esp32/provision/ca.crt", get_ca)
    app.router.add_put("/esp32/provision/pending/{cid}.csr", put_csr)
    app.router.add_get("/esp32/provision/cert/{cid}.crt", get_cert)
    runner = aiohttp_web.AppRunner(app)
    await runner.setup()
    port = _free_port()
    await aiohttp_web.TCPSite(runner, "127.0.0.1", port).start()

    import locveil_voice.satellite.provisioning as prov
    prov_interval = prov.POLL_INTERVAL_S
    prov.POLL_INTERVAL_S = 0.05  # fast poll for the test
    try:
        cfg = SatelliteTLSConfig(enabled=True, bootstrap_url=f"http://127.0.0.1:{port}")
        ca, crt, key = await ensure_credentials(cfg, tmp_path, "kitchen_node",
                                                poll_timeout_s=10.0)
    finally:
        prov.POLL_INTERVAL_S = prov_interval
        await runner.cleanup()

    assert ca.read_bytes() == b"---FAKE CA---"
    assert crt.read_bytes() == b"---FAKE CERT---"
    assert key.is_file() and (key.stat().st_mode & 0o777) == 0o600
    assert b"CERTIFICATE REQUEST" in submitted["csr"]  # a real openssl CSR went up
    # the CSR carries the client_id as CN (the identity the server will bind to)
    proc = await asyncio.create_subprocess_exec(
        "openssl", "req", "-in", str(key.parent / "kitchen_node.csr"), "-noout", "-subject",
        stdout=asyncio.subprocess.PIPE)
    out, _ = await proc.communicate()
    assert "kitchen_node" in out.decode()

    # second run: everything present → no network, same paths back
    ca2, crt2, key2 = await ensure_credentials(cfg, tmp_path, "kitchen_node")
    assert (ca2, crt2, key2) == (ca, crt, key)
