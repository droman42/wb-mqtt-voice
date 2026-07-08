"""ARCH-36 S-7 — hermetic fleet-TLS e2e (design §5): the full device-side provisioning dance
and mTLS operation against the REAL nginx Plane-B config, no WB7 and no ansible run needed.

The cycle, all in one test:
  render `nginx/ansible/templates/esp32-site.conf.j2` (throwaway CA, high ports)
  → docker nginx serves both zones (host network)
  → `ensure_credentials` does the first-run dance (EC key → PUT CSR via the :80 dav zone → poll)
  → the "operator" approves (scripted openssl sign — what `esp32-provision approve` runs)
  → `SatelliteLink` connects wss:// through the mTLS `/ws/` proxy to a stub Irene upstream
  → the REAL /ws/audio server enforces the cert↔client_id identity binding (finding b),
    with nginx injecting X-Client-Cert-DN from the verified certificate.

Skipped cleanly when docker/openssl/jinja2 are unavailable (CI has all three).
"""

import asyncio
import json
import shutil
import socket
import subprocess
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    shutil.which("docker") is None or shutil.which("openssl") is None,
    reason="docker + openssl required for the hermetic TLS e2e")

TEMPLATE = Path(__file__).resolve().parents[2] / "nginx/ansible/templates/esp32-site.conf.j2"

HTTP_PORT = 8480   # the :80 bootstrap zone, remapped (unprivileged)
HTTPS_PORT = 8443  # the :443 mTLS zone, remapped


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _openssl(*args: str) -> None:
    subprocess.run(["openssl", *args], check=True, capture_output=True)


def _make_throwaway_ca(ca_dir: Path) -> None:
    """CA + a localhost server cert (SAN) — what `esp32-ca-init.sh` produces on the controller."""
    ca_dir.mkdir(parents=True)
    _openssl("ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", str(ca_dir / "ca.key"))
    _openssl("req", "-x509", "-new", "-key", str(ca_dir / "ca.key"),
             "-subj", "/CN=irene-test-ca", "-days", "5", "-out", str(ca_dir / "ca.crt"))
    _openssl("ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", str(ca_dir / "server.key"))
    _openssl("req", "-new", "-key", str(ca_dir / "server.key"),
             "-subj", "/CN=localhost", "-out", str(ca_dir / "server.csr"))
    ext = ca_dir / "san.ext"
    ext.write_text("subjectAltName=DNS:localhost\n")
    _openssl("x509", "-req", "-in", str(ca_dir / "server.csr"),
             "-CA", str(ca_dir / "ca.crt"), "-CAkey", str(ca_dir / "ca.key"),
             "-CAcreateserial", "-days", "5", "-extfile", str(ext),
             "-out", str(ca_dir / "server.crt"))


def _render_site_conf(upstream_port: int) -> str:
    import jinja2
    # No test-plumbing deviation left: the listen ports are template variables
    # since ARCH-41 (the bootstrap zone must stay off the WB admin UI's :80).
    return jinja2.Template(TEMPLATE.read_text()).render(
        esp32_server_name="localhost",
        esp32_web_root="/srv/www",
        esp32_srv_dir="/srv/www/esp32",
        esp32_ca_dir="/etc/esp32-ca",
        esp32_irene_upstream=f"127.0.0.1:{upstream_port}",
        esp32_http_port=HTTP_PORT,
        esp32_https_port=HTTPS_PORT,
    )


def _approve(web_root: Path, ca_dir: Path, client_id: str) -> None:
    """The operator's `esp32-provision approve` step, scripted (same openssl call as
    `esp32-sign-csr.sh`): sign the pending CSR into the polled cert location."""
    pending = web_root / "esp32/provision/pending" / f"{client_id}.csr"
    cert = web_root / "esp32/provision/cert" / f"{client_id}.crt"
    _openssl("req", "-in", str(pending), "-noout", "-verify")
    _openssl("x509", "-req", "-in", str(pending),
             "-CA", str(ca_dir / "ca.crt"), "-CAkey", str(ca_dir / "ca.key"),
             "-CAcreateserial", "-days", "5", "-out", str(cert))


async def _wait_for(predicate, timeout_s: float, what: str) -> None:
    deadline = asyncio.get_running_loop().time() + timeout_s
    while not predicate():
        if asyncio.get_running_loop().time() > deadline:
            raise TimeoutError(f"timed out waiting for {what}")
        await asyncio.sleep(0.2)


async def test_full_plane_b_cycle(tmp_path):
    uvicorn = pytest.importorskip("uvicorn")
    pytest.importorskip("jinja2")
    from fastapi import FastAPI
    from irene.config.models import SatelliteTLSConfig
    from irene.intents.models import IntentResult
    from irene.runners.webapi_router import create_webapi_router
    from irene.satellite.link import SatelliteLink
    from irene.satellite.provisioning import build_ssl_context, ensure_credentials
    import irene.satellite.provisioning as prov

    client_id = "e2e_kitchen"

    # --- layout: web root (both provisioning dirs) + CA dir -------------------------------------
    web_root = tmp_path / "www"
    (web_root / "esp32/provision/pending").mkdir(parents=True)
    (web_root / "esp32/provision/cert").mkdir(parents=True)
    ca_dir = tmp_path / "esp32-ca"
    _make_throwaway_ca(ca_dir)
    shutil.copy(ca_dir / "ca.crt", web_root / "esp32/provision/ca.crt")
    # nginx worker (uid 101) must write pending/ and read cert/
    for p in web_root.rglob("*"):
        p.chmod(0o777 if p.is_dir() else 0o644)
    web_root.chmod(0o777)

    # --- stub Irene upstream (the REAL /ws/audio server code, pipeline stubbed) ------------------
    class _WM:
        async def process_audio_input(self, audio_data, session_id=None, wants_audio=False,
                                      client_context=None, trace_context=None):
            return IntentResult(text="готово")

    class _Core:
        workflow_manager = _WM()
        config = None
        component_manager = None
        plugin_manager = None
        output_manager = None

    app = FastAPI()
    app.include_router(create_webapi_router(_Core(), asset_loader=None, web_input=None,
                                            start_time=0.0))
    upstream_port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=upstream_port,
                                           log_level="error"))
    server_task = asyncio.create_task(server.serve())
    await _wait_for(lambda: server.started, 10, "uvicorn upstream")

    # --- docker nginx with the rendered Plane-B site --------------------------------------------
    conf = tmp_path / "esp32-site.conf"
    conf.write_text(_render_site_conf(upstream_port))
    container = f"arch36-tls-e2e-{uuid.uuid4().hex[:8]}"
    run = subprocess.run(
        ["docker", "run", "-d", "--rm", "--name", container, "--network", "host",
         "-v", f"{conf}:/etc/nginx/conf.d/default.conf:ro",
         "-v", f"{web_root}:/srv/www",
         "-v", f"{ca_dir}:/etc/esp32-ca:ro",
         "nginx:alpine"],
        capture_output=True, text=True)
    if run.returncode != 0:
        pytest.skip(f"docker nginx unavailable: {run.stderr.strip()[:200]}")

    prov_interval = prov.POLL_INTERVAL_S
    prov.POLL_INTERVAL_S = 0.3
    link = None
    try:
        # nginx up on the bootstrap zone?
        async def _nginx_up() -> bool:
            import aiohttp
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.get(f"http://localhost:{HTTP_PORT}/esp32/provision/ca.crt") as r:
                        return r.status == 200
            except aiohttp.ClientError:
                return False
        for _ in range(50):
            if await _nginx_up():
                break
            await asyncio.sleep(0.2)
        else:
            logs = subprocess.run(["docker", "logs", container], capture_output=True, text=True)
            pytest.fail(f"nginx bootstrap zone never came up: {logs.stderr[-500:]}")

        # --- the device's first-run dance, with the operator approving mid-poll ------------------
        tls_cfg = SatelliteTLSConfig(enabled=True, bootstrap_url=f"http://localhost:{HTTP_PORT}")
        dance = asyncio.create_task(
            ensure_credentials(tls_cfg, tmp_path / "assets", client_id, poll_timeout_s=30))
        pending_csr = web_root / "esp32/provision/pending" / f"{client_id}.csr"
        await _wait_for(pending_csr.is_file, 15, "CSR to land via the dav zone")
        _approve(web_root, ca_dir, client_id)
        ca, crt, key = await asyncio.wait_for(dance, timeout=30)

        # --- mTLS wss through the /ws/ proxy: the whole plane, end to end ------------------------
        ssl_ctx = build_ssl_context(ca, crt, key)
        link = SatelliteLink(f"wss://localhost:{HTTPS_PORT}", client_id, "Кухня",
                             ssl_context=ssl_ctx, response_timeout_s=15)
        await link.connect()
        response = await link.send_utterance(b"\x00\x01" * 2000)
        assert response["text"] == "готово"
        await link.close()

        # --- identity binding through REAL header injection (finding b) --------------------------
        # same certificate, different claimed client_id → the server must refuse.
        impostor = SatelliteLink(f"wss://localhost:{HTTPS_PORT}", "bedroom_node", "Спальня",
                                 ssl_context=ssl_ctx, response_timeout_s=15)
        with pytest.raises(ConnectionError, match="certificate|registration"):
            await impostor.connect()
        await impostor.close()

        # --- no client cert → nginx itself refuses the handshake ---------------------------------
        import ssl as _ssl
        naked_ctx = _ssl.create_default_context(cafile=str(ca))  # trusts the CA, presents no cert
        naked = SatelliteLink(f"wss://localhost:{HTTPS_PORT}", client_id, "Кухня",
                              ssl_context=naked_ctx, response_timeout_s=15)
        with pytest.raises(Exception):
            await naked.connect()
        await naked.close()
    finally:
        prov.POLL_INTERVAL_S = prov_interval
        if link is not None:
            await link.close()
        subprocess.run(["docker", "rm", "-f", container], capture_output=True)
        server.should_exit = True
        await server_task
