"""Support-bundle collection for problem reports (ARCH-32, design §3-5).

Assembles everything triage needs into one in-memory tar.gz: the user's description, the
conversation window, the registry's recent/failed action records, the request-ring dump, the
day's logs, the REDACTED config, and a metadata sheet. The paired `summary` dict is the issue
body's raw material — distilled enough that triage usually needn't open the tarball at all.

Redaction (§4) runs over the config text and every log line before packaging: secret-shaped
values are replaced, room/device names stay (the reports repo is private — design D-1; the
public boundary is guarded by the triage leak fence, §7.4).
"""

import gzip
import io
import json
import platform
import re
import tarfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .. import __version__
from .client_registry import get_client_registry, resolve_physical_id
from .request_ring import get_request_ring
from ..intents.context_models import UnifiedConversationContext

# Secret-shaped material (BUG-20 family): `KEY=value` / `key: value` / TOML `key = "value"`
# assignments whose key smells like a credential, plus bearer headers wherever they appear.
_SECRET_KEY_RE = re.compile(
    r"(?i)((?:[\w.\-]*?)(?:api_key|apikey|token|password|passwd|secret|credential)[\w.\-]*?\s*[=:]\s*)"
    r"(\"[^\"]*\"|'[^']*'|\S+)")
_BEARER_RE = re.compile(r"(?i)(authorization\s*[=:]?\s*bearer\s+)\S+")

_REDACTED = "«REDACTED»"


def redact(text: str) -> str:
    """Strip secret-shaped values from free-form text (config or logs)."""
    text = _SECRET_KEY_RE.sub(lambda m: m.group(1) + _REDACTED, text)
    return _BEARER_RE.sub(lambda m: m.group(1) + _REDACTED, text)


class ReportBundleCollector:
    """Builds (bundle_bytes, summary) for one report. Dependencies are plain callables so tests
    and the composition root wire it without ceremony."""

    def __init__(self,
                 config_path: Optional[Path] = None,
                 logs_dir: Path = Path("logs"),
                 catalog_version: Optional[Callable[[], Optional[str]]] = None):
        self.config_path = config_path
        self.logs_dir = logs_dir
        self._catalog_version = catalog_version or (lambda: None)

    # --- pieces ----------------------------------------------------------------------------------

    def _todays_logs(self) -> List[Tuple[str, bytes]]:
        """The active log + any same-day rotated ones, each gzipped."""
        out: List[Tuple[str, bytes]] = []
        today = datetime.now().strftime("%Y%m%d")
        if not self.logs_dir.exists():
            return out
        candidates = [self.logs_dir / "irene.log"]
        candidates += sorted(self.logs_dir.glob(f"irene_{today}_*.log"))
        for path in candidates:
            if not path.is_file():
                continue
            try:
                raw = redact(path.read_text(encoding="utf-8", errors="replace"))
                out.append((f"logs/{path.name}.gz", gzip.compress(raw.encode("utf-8"))))
            except OSError:
                continue
        return out

    def _redacted_config(self) -> Optional[bytes]:
        if self.config_path is None or not Path(self.config_path).is_file():
            return None
        raw = Path(self.config_path).read_text(encoding="utf-8", errors="replace")
        return redact(raw).encode("utf-8")

    def _metadata(self, context: UnifiedConversationContext, report_id: str) -> Dict[str, Any]:
        return {
            "report_id": report_id,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "version": __version__,
            "profile": Path(self.config_path).stem if self.config_path else None,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "language": context.language,
            "session_id": context.session_id,
            "room": context.room_name or context.client_id,
            "catalog_version": self._catalog_version(),
        }

    # --- assembly --------------------------------------------------------------------------------

    def collect(self, description: str,
                context: UnifiedConversationContext,
                bridge_evidence: Optional[Dict[str, Any]] = None) -> Tuple[bytes, Dict[str, Any]]:
        """One report → (tar.gz bytes, issue-ready summary).

        `bridge_evidence` (ARCH-34) is the status record from `BridgeClient.fetch_report_evidence`
        — filed verbatim under `bridge/` in the tarball. An `attached` record contributes the raw
        `EvidenceEnvelope` (the bridge-owned contract, pinned in eval-commons); any other status
        is itself evidence (`bridge/unavailable.json`)."""
        report_id = uuid.uuid4().hex[:12]
        registry = get_client_registry()
        physical_id = resolve_physical_id(context.client_id, context.room_name,
                                          context.session_id)
        history = list(context.conversation_history)
        actions = {
            "recent": registry.get_recent_actions(physical_id),
            "failed": registry.get_failed_actions(physical_id),
        }
        requests_dump = get_request_ring().dump()
        metadata = self._metadata(context, report_id)
        # ARCH-34 triage discriminators: was the smart home in play, and did the bridge answer?
        metadata["smart_home_involved"] = any(
            str(r.get("intent_name") or "").startswith("smart_home")
            for r in requests_dump)
        metadata["bridge_evidence"] = bridge_evidence["status"] if bridge_evidence else None

        members: List[Tuple[str, bytes]] = [
            ("description.txt", description.encode("utf-8")),
            ("metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2).encode()),
            ("conversation.json", json.dumps(history, ensure_ascii=False, indent=2).encode()),
            ("actions.json", json.dumps(actions, ensure_ascii=False, indent=2).encode()),
            ("requests.json", json.dumps(requests_dump, ensure_ascii=False, indent=2).encode()),
        ]
        config_bytes = self._redacted_config()
        if config_bytes is not None:
            members.append(("config.redacted.toml", config_bytes))
        if bridge_evidence is not None:
            if bridge_evidence.get("status") == "attached":
                members.append(("bridge/evidence.json",
                                json.dumps(bridge_evidence["envelope"],
                                           ensure_ascii=False, indent=2).encode()))
            else:
                members.append(("bridge/unavailable.json",
                                json.dumps(bridge_evidence,
                                           ensure_ascii=False, indent=2).encode()))
        members.extend(self._todays_logs())

        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            for name, data in members:
                info = tarfile.TarInfo(name=name)
                info.size = len(data)
                info.mtime = int(time.time())
                tar.addfile(info, io.BytesIO(data))

        # The distilled issue material (§5): free text verbatim + a last-turns synopsis + versions.
        summary = {
            "report_id": report_id,
            "description": description,
            "metadata": metadata,
            "last_turns": [
                {"user": (t.get("user_text") or "")[:200],
                 "irene": (t.get("response") or "")[:200],
                 "intent": t.get("intent")}
                for t in history[-3:]
            ],
            "recent_requests": requests_dump[-3:],
        }
        return buf.getvalue(), summary
