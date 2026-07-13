"""Device-side TLS provisioning for the fleet plane (ARCH-36 S-5/S-6, design §5).

Implements the CSR-approval dance against the nginx bootstrap zone (`:8081` by default —
`../locveil-satellite/provisioning/README.md`, the Plane-B home since 2026-07-12): generate an
EC keypair locally (the private key never leaves the box),
submit `PUT /esp32/provision/pending/<client_id>.csr`, then poll
`GET /esp32/provision/cert/<client_id>.crt` while the operator approves over SSH
(`esp32-provision approve <client_id>` — printed verbatim while polling). Key material lives
at `<assets_root>/credentials/satellite/` (asset-managed, never in git or configs).

Key/CSR generation shells out to the `openssl` CLI — the same tool the controller-side
scripts use, present on every Linux the satellite targets; no new Python dependency.
"""

import asyncio
import logging
import ssl
from pathlib import Path
from typing import Optional, Tuple

import aiohttp

from ..config.models import SatelliteTLSConfig

logger = logging.getLogger(__name__)

CA_PATH = "/esp32/provision/ca.crt"
CSR_PATH = "/esp32/provision/pending/{client_id}.csr"
CERT_PATH = "/esp32/provision/cert/{client_id}.crt"

POLL_INTERVAL_S = 5.0


class ProvisioningError(Exception):
    """Provisioning cannot proceed (missing bootstrap_url, openssl failure, HTTP error)."""


def credential_paths(cfg: SatelliteTLSConfig, assets_root: Path) -> Tuple[Path, Path, Path]:
    """(ca_cert, client_cert, client_key) — config overrides or the S-6 default location."""
    base = assets_root / "credentials" / "satellite"
    return (Path(cfg.ca_cert) if cfg.ca_cert else base / "ca.crt",
            Path(cfg.client_cert) if cfg.client_cert else base / "sat.crt",
            Path(cfg.client_key) if cfg.client_key else base / "sat.key")


def build_ssl_context(ca_cert: Path, client_cert: Path, client_key: Path) -> ssl.SSLContext:
    """mTLS client context: home CA as the only trust anchor + our cert/key pair."""
    ctx = ssl.create_default_context(cafile=str(ca_cert))
    ctx.load_cert_chain(certfile=str(client_cert), keyfile=str(client_key))
    return ctx


async def _openssl(*args: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        "openssl", *args,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise ProvisioningError(f"openssl {args[0]} failed: {stderr.decode(errors='replace').strip()}")


async def _generate_key_and_csr(key_path: Path, csr_path: Path, client_id: str) -> None:
    key_path.parent.mkdir(parents=True, exist_ok=True)
    await _openssl("ecparam", "-name", "prime256v1", "-genkey", "-noout",
                   "-out", str(key_path))
    key_path.chmod(0o600)
    await _openssl("req", "-new", "-key", str(key_path),
                   "-subj", f"/CN={client_id}", "-out", str(csr_path))


async def ensure_credentials(cfg: SatelliteTLSConfig, assets_root: Path, client_id: str, *,
                             poll_timeout_s: Optional[float] = None) -> Tuple[Path, Path, Path]:
    """Make sure ca/cert/key exist, provisioning on first run; returns their paths.

    Blocks polling until the operator approves (or `poll_timeout_s` elapses) — first-run
    provisioning is interactive by design (D-17: human approval is the only gate)."""
    ca, crt, key = credential_paths(cfg, assets_root)
    if ca.is_file() and crt.is_file() and key.is_file():
        return ca, crt, key

    if not cfg.bootstrap_url:
        raise ProvisioningError(
            "TLS is enabled but credentials are missing and [satellite.tls] bootstrap_url "
            "is empty — set it to the controller's provisioning zone (e.g. 'http://wb7:8081')")
    base = cfg.bootstrap_url.rstrip("/")
    csr = key.parent / f"{client_id}.csr"
    if not (key.is_file() and csr.is_file()):
        logger.info("Generating EC keypair + CSR (private key never leaves this box)")
        await _generate_key_and_csr(key, csr, client_id)

    async with aiohttp.ClientSession() as session:
        async with session.get(base + CA_PATH) as resp:
            if resp.status != 200:
                raise ProvisioningError(f"CA download failed: HTTP {resp.status} ({base + CA_PATH})")
            ca.parent.mkdir(parents=True, exist_ok=True)
            ca.write_bytes(await resp.read())

        csr_url = base + CSR_PATH.format(client_id=client_id)
        async with session.put(csr_url, data=csr.read_bytes()) as resp:
            if resp.status not in (200, 201, 204):
                raise ProvisioningError(f"CSR submit failed: HTTP {resp.status} ({csr_url})")
        logger.info(f"CSR submitted for '{client_id}' — waiting for operator approval")
        print(f"\n  Approve on the controller (as root):\n"
              f"    esp32-provision approve {client_id}\n")

        cert_url = base + CERT_PATH.format(client_id=client_id)
        deadline = (asyncio.get_running_loop().time() + poll_timeout_s
                    if poll_timeout_s is not None else None)
        while True:
            async with session.get(cert_url) as resp:
                if resp.status == 200:
                    crt.write_bytes(await resp.read())
                    logger.info(f"Certificate issued → {crt}")
                    return ca, crt, key
                if resp.status != 404:
                    raise ProvisioningError(f"cert poll failed: HTTP {resp.status} ({cert_url})")
            if deadline is not None and asyncio.get_running_loop().time() >= deadline:
                raise ProvisioningError("certificate was not approved within poll_timeout_s")
            await asyncio.sleep(POLL_INTERVAL_S)
