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
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CONFIG = str(REPO / "configs" / "config-master.toml")
# Console scripts live next to the running interpreter — .venv/bin locally, the runner's
# tool env in CI (which has no .venv; the old hardcoded REPO/.venv/bin broke there).
VENV_BIN = Path(sys.executable).parent


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


def _offline_env() -> dict:
    """SUT env with every LLM key BLANKED (BUG-20). Covers keys from the shell AND the
    repo ``.env`` (dotenv never overrides an existing var, so empty wins over both)."""
    env = dict(os.environ)
    key_names = {k for k in env if k.endswith("_API_KEY")}
    dotenv = REPO / ".env"
    if dotenv.exists():
        for line in dotenv.read_text().splitlines():
            name = line.split("=", 1)[0].strip()
            if name.endswith("_API_KEY"):
                key_names.add(name)
    for name in key_names:
        env[name] = ""
    return env


@pytest.fixture(scope="module")
def webapi():
    """Boot the WebAPI runner once for the module; tear it down with SIGINT.

    BUG-20: the SUT's LLM ``*_API_KEY`` env vars are BLANKED (not stripped) — the smoke
    suite asserts OFFLINE behavior (LLM degrade), but real keys leak in from two places:
    the developer shell (e.g. the eval judge's DEEPSEEK_API_KEY) and the repo-root
    ``.env`` that every runner ``load_dotenv()``s. Blanking works for both, because
    dotenv does not override an env var that already exists — stripping alone would
    leave the ``.env`` leak, silently turning "offline degrade" into a live DeepSeek
    call that flakes on slow API responses.
    """
    port = _free_port()
    base = f"http://127.0.0.1:{port}"
    proc = subprocess.Popen(
        [str(VENV_BIN / "irene-webapi"), "-c", CONFIG, "--host", "127.0.0.1", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        env=_offline_env(),
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
    assert r["intent_name"] == "greeting.hello", r  # QUAL-55: canonical top-level key


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
    assert isinstance(r["text"], str) and r["text"].strip(), r  # QUAL-55: reply under `text`


def test_set_timer_end_to_end(webapi):
    """Setting a timer should resolve to a timer intent and succeed.

    Was doubly broken: (1) NLU dropped 'поставь таймер на 5 минут' to conversation.general —
    a Cyrillic normalization asymmetry (NFKD+combining-strip folded «й»→«и» so raw donation
    patterns never matched normalized input) [QUAL-11]; (2) the F&F launch crashed on a
    duplicate session_id kwarg [QUAL-9]. Both now fixed (QUAL-11 normalization + QUAL-28 F&F)."""
    code, r = _post(webapi, "/execute/command", {"command": "поставь таймер на 5 минут"})
    assert code == 200, r
    assert r["success"] is True, r
    assert r["intent_name"].startswith("timer"), r  # QUAL-55: canonical top-level key
    # Correctness, not just success: the unit must be MINUTES (→ 300s, rendered "5 мин"), not the old
    # hardcoded-seconds default ("5 сек"). Guards the QUAL-11 unit-surface + get_param fix.
    assert "5 мин" in r["text"], r


# --- CLI boot (separate process, BUILD-1 path) ----------------------------------

def test_cli_headless_boots_and_responds():
    """The CLI runner boots headless and executes a single command end-to-end."""
    res = subprocess.run(
        [str(VENV_BIN / "irene-cli"), "-c", CONFIG, "--headless", "--command", "привет"],
        capture_output=True,
        text=True,
        timeout=180,
        env=_offline_env(),  # BUG-20: hermetic — blanked LLM keys beat shell AND .env
    )
    assert res.returncode == 0, res.stderr[-2000:]
    # A response was rendered through the output hexagon (ARCH-15 PR-3: the CLI now delivers via
    # ConsoleOutput, prefix "📝 ", replacing the old "📝 Response: " single-command print), plus the
    # runner's success marker; and no execution error.
    assert "📝 " in res.stdout, res.stdout[-2000:]
    assert "Command executed successfully" in res.stdout, res.stdout[-2000:]
    assert "Error executing command" not in res.stdout, res.stdout[-2000:]
