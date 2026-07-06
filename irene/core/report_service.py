"""Problem-report delivery service (ARCH-32, design §5-6).

Owns the submit flow: rate limit (D-7) → collect the bundle → SPOOL it to durable state (crash
safety first) → try the upload; on success the spool entry is deleted, on failure it stays and
the handler launches the durable retry (ARCH-27 substrate — the "I'll send it later" promise
must survive a restart, so it lives in a durable action, not an ad-hoc loop here).

Statuses returned to the handler: "sent" | "spooled" | "rate_limited" — each maps to its own
spoken template. The spool lives under `<assets_root>/state/reports/` (asset-managed, volume-
mounted — never the deletable cache/, per the durable-actions invariant).
"""

import json
import logging
import time
from collections import deque
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .report_bundle import ReportBundleCollector
from ..intents.context_models import UnifiedConversationContext

logger = logging.getLogger(__name__)


def build_envelope(summary: Dict[str, Any], source: str = "voice") -> Dict[str, Any]:
    """The shared intake format (design §5): issue title/body/labels + the bundle's repo path."""
    meta = summary["metadata"]
    stamp = meta["created_utc"].replace(":", "").replace("-", "")[:15]
    room = meta.get("room") or "unknown"
    title_text = " ".join(str(summary["description"]).split())[:60]
    turns = "\n".join(
        f"- «{t['user']}» → `{t['intent']}` → «{t['irene']}»" for t in summary["last_turns"]
    ) or "- (no prior turns)"
    bridge_note = f" · bridge evidence: {meta['bridge_evidence']}" if meta.get("bridge_evidence") else ""
    body = (
        f"**Reported (verbatim):**\n\n> {summary['description']}\n\n"
        f"**Last turns:**\n{turns}\n\n"
        f"**Environment:** v{meta['version']} · profile `{meta['profile']}` · {meta['machine']} · "
        f"language {meta['language']} · room {room} · catalog `{meta.get('catalog_version')}`"
        f"{bridge_note}\n\n"
        f"**Bundle:** `{{bundle_url}}`\n\n"
        f"`report-id: {meta['report_id']}`"
    )
    return {
        "title": f"[{source}] {title_text}",
        "body": body,
        "labels": ["problem-report", f"lens:{'bridge' if source == 'bridge-ui' else 'voice'}", "new"],
        "bundle_path": f"reports/{stamp}-{source}-{room}/bundle.tar.gz",
    }


class ReportService:
    """The handler-facing submit seam (injected via `set_report_service`, ARCH-31)."""

    def __init__(self, collector: ReportBundleCollector, client: Any, spool_dir: Path,
                 rate_limit_per_hour: int = 3, rate_limit_per_day: int = 10,
                 bridge_evidence_fetcher: Optional[Callable[[], Awaitable[Dict[str, Any]]]] = None):
        self.collector = collector
        self.client = client  # GitHubReportClient-shaped: put_bundle / create_issue
        self.spool_dir = spool_dir
        self.rate_limit_per_hour = rate_limit_per_hour
        self.rate_limit_per_day = rate_limit_per_day
        # ARCH-34: BridgeClient.fetch_report_evidence when [outputs.bridge] is wired, else None.
        self.bridge_evidence_fetcher = bridge_evidence_fetcher
        self._filed_at: deque = deque(maxlen=max(rate_limit_per_day, rate_limit_per_hour))

    # --- rate limiting (D-7) -----------------------------------------------------------------------

    def _rate_limited(self) -> bool:
        now = time.time()
        last_hour = sum(1 for t in self._filed_at if now - t < 3600)
        last_day = sum(1 for t in self._filed_at if now - t < 86400)
        return last_hour >= self.rate_limit_per_hour or last_day >= self.rate_limit_per_day

    # --- spool ---------------------------------------------------------------------------------------

    def _spool_write(self, report_id: str, bundle: bytes, envelope: Dict[str, Any]) -> Path:
        self.spool_dir.mkdir(parents=True, exist_ok=True)
        (self.spool_dir / f"{report_id}.tar.gz").write_bytes(bundle)
        envelope_path = self.spool_dir / f"{report_id}.json"
        envelope_path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
        return envelope_path

    def _spool_delete(self, report_id: str) -> None:
        for suffix in (".tar.gz", ".json"):
            try:
                (self.spool_dir / f"{report_id}{suffix}").unlink(missing_ok=True)
            except OSError:
                pass

    def spooled_ids(self) -> List[str]:
        if not self.spool_dir.exists():
            return []
        return sorted(p.stem for p in self.spool_dir.glob("*.json"))

    # --- delivery ------------------------------------------------------------------------------------

    async def _upload(self, report_id: str, bundle: bytes, envelope: Dict[str, Any]) -> None:
        """The two GitHub calls. Raises on any failure (caller decides spool fate)."""
        bundle_url = await self.client.put_bundle(
            envelope["bundle_path"], bundle,
            message=f"report {report_id}")
        await self.client.create_issue(
            title=envelope["title"],
            body=envelope["body"].replace("{bundle_url}", bundle_url),
            labels=envelope["labels"])

    async def submit(self, description: str, context: UnifiedConversationContext) -> str:
        """The handler-facing call: returns 'sent' | 'spooled' | 'rate_limited'."""
        if self._rate_limited():
            logger.warning("Problem report rate-limited (D-7)")
            return "rate_limited"

        # ARCH-34: pull the bridge's evidence envelope at filing time (a snapshot — the retry
        # path re-sends the spooled bundle as collected here). The fetcher never raises by
        # contract, but a failure here must not lose the report either.
        evidence: Optional[Dict[str, Any]] = None
        if self.bridge_evidence_fetcher is not None:
            try:
                evidence = await self.bridge_evidence_fetcher()
            except Exception as e:
                evidence = {"status": "unreachable", "error": str(e)}

        bundle, summary = self.collector.collect(description, context, bridge_evidence=evidence)
        report_id = summary["report_id"]
        envelope = build_envelope(summary)
        self._spool_write(report_id, bundle, envelope)  # crash safety before any network
        self._filed_at.append(time.time())

        try:
            await self._upload(report_id, bundle, envelope)
        except Exception as e:
            logger.warning(f"Report {report_id} not delivered ({e}); spooled for durable retry")
            return "spooled"
        self._spool_delete(report_id)
        logger.info(f"Problem report {report_id} filed")
        return "sent"

    async def retry_spooled(self, report_id: str) -> bool:
        """One retry attempt for a spooled report (driven by the durable action). True = delivered
        (or nothing left to deliver — an already-cleaned spool counts as done)."""
        envelope_path = self.spool_dir / f"{report_id}.json"
        bundle_path = self.spool_dir / f"{report_id}.tar.gz"
        if not envelope_path.exists() or not bundle_path.exists():
            return True
        envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
        bundle = bundle_path.read_bytes()
        try:
            await self._upload(report_id, bundle, envelope)
        except Exception as e:
            logger.debug(f"Report {report_id} retry failed: {e}")
            return False
        self._spool_delete(report_id)
        logger.info(f"Problem report {report_id} delivered on retry")
        return True
