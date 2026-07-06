"""ARCH-32 — support bundle + delivery (design docs/design/problem_reports.md §3-6).

Covers: the request ring (rolls, clips), redaction (secrets out, household in), the bundle
(members + metadata), the envelope (§5 shared intake format), and the service flow
(sent / spooled-with-crash-safe-spool / rate-limited / retry drains the spool).
"""

import io
import json
import tarfile
import time
from pathlib import Path

import pytest

from irene.core.report_bundle import ReportBundleCollector, redact
from irene.core.report_service import ReportService, build_envelope
from irene.core.request_ring import RequestRing, get_request_ring
from irene.intents.context_models import UnifiedConversationContext


# --- ring -------------------------------------------------------------------------------------------

def _append(ring, n):
    for i in range(n):
        ring.append(session_id="s", room="kitchen", language="ru",
                    input_text=f"cmd {i}", processed_text=f"cmd {i}",
                    intent_name="x.y", confidence=0.9, nlu_provider="hybrid",
                    result_text="ok", success=True)


def test_ring_rolls_at_capacity():
    ring = RequestRing(size=3)
    _append(ring, 5)
    dump = ring.dump()
    assert len(dump) == 3
    assert dump[0]["input_text"] == "cmd 2" and dump[-1]["input_text"] == "cmd 4"


def test_ring_clips_long_text():
    ring = RequestRing(size=2)
    ring.append(session_id="s", room=None, language="ru",
                input_text="x" * 2000, processed_text="", intent_name="a.b",
                confidence=1.0, nlu_provider=None, result_text="", success=True)
    assert len(ring.dump()[0]["input_text"]) == 500


# --- redaction ---------------------------------------------------------------------------------------

def test_redaction_strips_secret_shapes_keeps_household():
    text = (
        'DEEPSEEK_API_KEY=sk-abc123\n'
        'token_env = "IRENE_REPORTS_TOKEN"\n'
        'my_password: hunter2\n'
        'Authorization: Bearer ghp_secret\n'
        'room = "Спальня"\n'
    )
    out = redact(text)
    assert "sk-abc123" not in out and "hunter2" not in out and "ghp_secret" not in out
    assert "Спальня" in out  # household context stays — the repo is private (D-1)


# --- bundle ------------------------------------------------------------------------------------------

def _context():
    ctx = UnifiedConversationContext(session_id="kitchen_session", client_id="kitchen",
                                     room_name="Кухня", language="ru")
    ctx.record_turn(user_text="включи свет", response="Включаю", intent="smart_home.power_on")
    return ctx


def test_bundle_members_and_summary(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text('name = "Irene"\napi_key = "SECRET-VALUE"\n', encoding="utf-8")
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "irene.log").write_text("2026-07-06 INFO boot\ntoken=abc\n", encoding="utf-8")

    collector = ReportBundleCollector(config_path=config, logs_dir=logs,
                                      catalog_version=lambda: "cat123")
    bundle, summary = collector.collect("что-то сломалось", _context())

    with tarfile.open(fileobj=io.BytesIO(bundle), mode="r:gz") as tar:
        names = tar.getnames()
        config_member = tar.extractfile("config.redacted.toml").read().decode()
    assert {"description.txt", "metadata.json", "conversation.json",
            "actions.json", "requests.json", "config.redacted.toml"} <= set(names)
    assert any(n.startswith("logs/") for n in names)
    assert "SECRET-VALUE" not in config_member

    assert summary["description"] == "что-то сломалось"
    assert summary["metadata"]["catalog_version"] == "cat123"
    assert summary["metadata"]["room"] == "Кухня"
    assert summary["last_turns"][-1]["intent"] == "smart_home.power_on"


# --- envelope (§5) ------------------------------------------------------------------------------------

def test_envelope_shape():
    _, summary = ReportBundleCollector(catalog_version=lambda: "v1").collect("свет мигает", _context())
    env = build_envelope(summary)
    assert env["title"].startswith("[voice] свет мигает")
    assert set(env["labels"]) == {"problem-report", "lens:voice", "new"}
    assert env["bundle_path"].startswith("reports/") and env["bundle_path"].endswith("/bundle.tar.gz")
    assert "свет мигает" in env["body"] and summary["report_id"] in env["body"]


# --- service ------------------------------------------------------------------------------------------

class _FakeClient:
    def __init__(self, fail=False):
        self.fail = fail
        self.issues = []

    async def put_bundle(self, path, data, message):
        if self.fail:
            raise RuntimeError("offline")
        return f"https://example/{path}"

    async def create_issue(self, title, body, labels):
        if self.fail:
            raise RuntimeError("offline")
        self.issues.append((title, labels))
        return "https://example/issue/1"


def _service(tmp_path, client, **kw):
    collector = ReportBundleCollector(config_path=None, logs_dir=tmp_path / "nologs",
                                      catalog_version=lambda: None)
    return ReportService(collector, client, tmp_path / "spool", **kw)


async def test_submit_success_cleans_spool(tmp_path):
    client = _FakeClient()
    svc = _service(tmp_path, client)
    status = await svc.submit("сломалось", _context())
    assert status == "sent"
    assert client.issues and client.issues[0][1] == ["problem-report", "lens:voice", "new"]
    assert svc.spooled_ids() == []


async def test_submit_offline_spools_then_retry_drains(tmp_path):
    client = _FakeClient(fail=True)
    svc = _service(tmp_path, client)
    status = await svc.submit("сломалось", _context())
    assert status == "spooled"
    ids = svc.spooled_ids()
    assert len(ids) == 1
    assert (tmp_path / "spool" / f"{ids[0]}.tar.gz").exists()  # crash-safe: bundle on disk

    client.fail = False  # network returns
    assert await svc.retry_spooled(ids[0]) is True
    assert svc.spooled_ids() == []
    assert client.issues, "the retried report reached the sink"


async def test_rate_limit_blocks_fourth_report_in_hour(tmp_path):
    svc = _service(tmp_path, _FakeClient(), rate_limit_per_hour=3, rate_limit_per_day=10)
    ctx = _context()
    for _ in range(3):
        assert await svc.submit("x", ctx) == "sent"
    assert await svc.submit("x", ctx) == "rate_limited"


async def test_retry_of_missing_spool_counts_done(tmp_path):
    svc = _service(tmp_path, _FakeClient())
    assert await svc.retry_spooled("nonexistent") is True
