"""TEST-0 — minimal end-to-end smoke / integration harness (the refactor safety net).

This is NOT the TEST-7 suite rewrite. It is a small, fast, always-green set of
real-flow assertions whose job is to catch *gross* breakage while the ARCH
refactors move code and the review-wave P0s are fixed. It is the "wire-up
integration test" the QUAL-8/10/12/14 reviews all flagged as missing.

Design rules:
- Drive the system the way it actually runs (boot the WebAPI runner as a
  subprocess, like BUILD-1; one boot shared across the WebAPI flows) — no
  fragile in-process async app construction.
- Green assertions must be STABLE (assert on intent identity / structure, not
  on exact wording that templates may change).
- KNOWN-broken flows are `xfail` with the owning task referenced, so the suite
  stays green and the test auto-flips when the P0 is fixed.

Run: `.venv/bin/python -m pytest irene/tests/test_smoke_e2e.py -v`
(Slow-ish: boots the full stack; not meant for run-on-every-save.)
"""

import json
import signal
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CONFIG = str(REPO / "configs" / "config-master.toml")
VENV_BIN = REPO / ".venv" / "bin"


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _post(base: str, path: str, payload: dict, timeout: int = 25):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base + path, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def _get(base: str, path: str, timeout: int = 15):
    with urllib.request.urlopen(base + path, timeout=timeout) as r:
        return r.status, r.read()


@pytest.fixture(scope="module")
def webapi():
    """Boot the WebAPI runner once for the module; tear it down with SIGINT."""
    port = _free_port()
    base = f"http://127.0.0.1:{port}"
    proc = subprocess.Popen(
        [str(VENV_BIN / "irene-webapi"), "-c", CONFIG, "--host", "127.0.0.1", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    try:
        deadline = time.time() + 120
        ready = False
        while time.time() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(f"irene-webapi exited during startup (rc={proc.returncode})")
            try:
                code, _ = _get(base, "/openapi.json", timeout=3)
                if code == 200:
                    ready = True
                    break
            except Exception:
                time.sleep(1)
        if not ready:
            raise RuntimeError("irene-webapi did not become ready within 120s")
        yield base
    finally:
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()


# --- WebAPI flows (shared boot) -------------------------------------------------

def test_webapi_boots(webapi):
    """The WebAPI runner boots and serves its OpenAPI schema."""
    code, body = _get(webapi, "/openapi.json")
    assert code == 200
    assert b'"paths"' in body


def test_greeting_executes(webapi):
    """A recognized command round-trips: NLU -> intent -> handler -> response."""
    code, r = _post(webapi, "/execute/command", {"command": "привет"})
    assert code == 200, r
    assert r["success"] is True, r
    assert r["metadata"]["intent_name"] == "greeting.hello", r


def test_nlu_recognize_responds(webapi):
    """The NLU recognize endpoint returns a structured intent."""
    code, r = _post(webapi, "/nlu/recognize", {"text": "привет"})
    assert code == 200, r
    assert r["success"] is True, r
    assert "name" in r and "confidence" in r, r


def test_conversation_offline_degrades_gracefully(webapi):
    """With the LLM unavailable offline (no key / phantom `console` provider, QUAL-14/15),
    an open-ended request must DEGRADE (200 + some response), never crash."""
    code, r = _post(webapi, "/execute/command", {"command": "расскажи что-нибудь про космос"})
    assert code == 200, r
    assert r["success"] is True, r
    assert isinstance(r["response"], str) and r["response"].strip(), r


def test_set_timer_end_to_end(webapi):
    """Setting a timer should resolve to a timer intent and succeed.

    Was doubly broken: (1) NLU dropped 'поставь таймер на 5 минут' to conversation.general —
    a Cyrillic normalization asymmetry (NFKD+combining-strip folded «й»→«и» so raw donation
    patterns never matched normalized input) [QUAL-11]; (2) the F&F launch crashed on a
    duplicate session_id kwarg [QUAL-9]. Both now fixed (QUAL-11 normalization + QUAL-28 F&F)."""
    code, r = _post(webapi, "/execute/command", {"command": "поставь таймер на 5 минут"})
    assert code == 200, r
    assert r["success"] is True, r
    assert r["metadata"]["intent_name"].startswith("timer"), r


# --- CLI boot (separate process, BUILD-1 path) ----------------------------------

def test_cli_headless_boots_and_responds():
    """The CLI runner boots headless and executes a single command end-to-end."""
    res = subprocess.run(
        [str(VENV_BIN / "irene-cli"), "-c", CONFIG, "--headless", "--command", "привет"],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert res.returncode == 0, res.stderr[-2000:]
    # success marker printed by the CLI runner; and no execution error
    assert "Response:" in res.stdout, res.stdout[-2000:]
    assert "Error executing command" not in res.stdout, res.stdout[-2000:]
