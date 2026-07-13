"""
Durable-action substrate (ARCH-28, design: docs/design/durable_actions.md).

Fire-and-forget actions launched with ``durable=True`` persist a record here so the promise
they made ("I'll ring in 10 minutes") survives a process restart / container replacement.
The store is one atomic-JSON file under the asset-managed tree
(``<assets_root>/state/durable_actions.json`` — D-2: volume-mounted, NOT deletable cache/),
behind a small hexagonal port (SQLite is a drop-in swap if write rates ever demand it).

Lifecycle contract (D-2, learned from the bridge's failure modes):
- persist at launch, **delete at completion in the same operation** as the in-memory store
  removal (anti stale-intent resurrection);
- the persisted record carries NO live-task bookkeeping (ephemeral-field filter) — only what
  re-arm needs;
- persist + restore + the restart test ship together (anti persist-without-restore rot).

Recovery (D-3/D-4): at startup :func:`reconcile_durable_actions` re-arms future deadlines by
relaunching through each handler's ``rearm_durable_action`` hook, fires recently-missed
deadlines with an apology (≤ :data:`GRACE_WINDOW_SECONDS`), and announces older ones as
expired. The API is synchronous on purpose: writes are a few KB and the completion-side
caller (the task done-callback) is a sync function.
"""

import json
import logging
import os
import tempfile
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config.models import AssetConfig

logger = logging.getLogger(__name__)

# D-4: a deadline missed by no more than this fires immediately with an apology; older ones
# get an expiry announcement. Also the TTL for undelivered completion notices (D-6). A
# constant, not config — recovery policy, not a user tunable (BUG-17 precedent).
GRACE_WINDOW_SECONDS = 3600.0

SCHEMA_VERSION = 1

# D-4 recovery announcements. In-code (not donation templates) because recovery runs in core,
# before/independent of any handler's asset scope; user-facing text is localized ru-first
# per the project's localization rule.
_APOLOGY_PREFIX = {
    "ru": "Извините, пока меня не было, сработал таймер: ",
    "en": "Sorry — while I was away, a timer went off: ",
}
_EXPIRED_TEXT = {
    "ru": "Пока меня не было, истёк таймер: {message} (более часа назад)",
    "en": "While I was away, a timer expired: {message} (more than an hour ago)",
}


@dataclass
class DurableActionRecord:
    """Persisted intent of a durable action — schema v1 (D-2). No live-task refs, ever."""
    action_name: str                     # stable identity; re-arm REUSES it (D-8)
    domain: str
    handler: str                         # launching handler's class name (rearm dispatch key)
    physical_id: str
    started_at: float
    deadline: Optional[float]            # started_at + duration(+grace); None = unbounded
    session_id: Optional[str] = None
    room_id: Optional[str] = None
    source: Optional[str] = None
    redeliver: bool = False              # D-6: handler-declared redelivery of the completion
    rearm: Dict[str, Any] = field(default_factory=dict)   # {"method": name, "params": JSON-safe kwargs}
    metadata: Dict[str, Any] = field(default_factory=dict)  # {"language", "completion_message"}
    schema: int = SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DurableActionRecord":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class UndeliveredNotice:
    """A completion notice whose owning reply channel was offline (D-6). TTL = grace window."""
    physical_id: str
    action_name: str
    domain: str
    message: str                         # final, localized announcement text
    language: Optional[str] = None
    session_id: Optional[str] = None
    room_id: Optional[str] = None
    source: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UndeliveredNotice":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


class DurableActionStorePort(ABC):
    """Hexagonal port for durable-action persistence (D-2)."""

    @abstractmethod
    def load_all(self) -> List[DurableActionRecord]: ...

    @abstractmethod
    def save(self, record: DurableActionRecord) -> None:
        """Upsert by ``action_name`` — called at durable launch."""

    @abstractmethod
    def delete(self, action_name: str) -> None:
        """Remove the record — called at completion, atomically with the in-memory removal."""

    @abstractmethod
    def add_undelivered(self, notice: UndeliveredNotice) -> None: ...

    @abstractmethod
    def pop_undelivered(self, physical_ids: List[str]) -> List[UndeliveredNotice]:
        """Drain (remove + return) non-expired notices for any of the given identities."""


class JsonFileDurableActionStore(DurableActionStorePort):
    """Default adapter: one JSON file, every mutation an atomic temp-file + rename write."""

    def __init__(self, path: Path):
        self.path = Path(path)

    # -- file plumbing ------------------------------------------------------

    def _read(self) -> Dict[str, Any]:
        try:
            if not self.path.exists():
                return {"schema": SCHEMA_VERSION, "actions": {}, "undelivered": []}
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("store root is not an object")
            data.setdefault("actions", {})
            data.setdefault("undelivered", [])
            return data
        except Exception as e:
            # Never wedge on a bad file (D-3): recovery must survive a corrupt store.
            logger.error(f"Durable-action store unreadable ({self.path}): {e} — starting fresh")
            return {"schema": SCHEMA_VERSION, "actions": {}, "undelivered": []}

    def _write(self, data: Dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=f".{self.path.name}.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    # -- port ----------------------------------------------------------------

    def load_all(self) -> List[DurableActionRecord]:
        records = []
        for name, raw in self._read()["actions"].items():
            try:
                records.append(DurableActionRecord.from_dict(raw))
            except Exception as e:
                logger.error(f"Skipping undecodable durable-action record '{name}': {e}")
        return records

    def save(self, record: DurableActionRecord) -> None:
        data = self._read()
        data["actions"][record.action_name] = record.to_dict()
        self._write(data)

    def delete(self, action_name: str) -> None:
        data = self._read()
        if data["actions"].pop(action_name, None) is not None:
            self._write(data)

    def add_undelivered(self, notice: UndeliveredNotice) -> None:
        data = self._read()
        data["undelivered"].append(notice.to_dict())
        self._write(data)

    def pop_undelivered(self, physical_ids: List[str]) -> List[UndeliveredNotice]:
        wanted = {pid for pid in physical_ids if pid}
        data = self._read()
        now = time.time()
        drained: List[UndeliveredNotice] = []
        kept: List[Dict[str, Any]] = []
        for raw in data["undelivered"]:
            try:
                notice = UndeliveredNotice.from_dict(raw)
            except Exception:
                continue  # drop undecodable
            if now - notice.created_at > GRACE_WINDOW_SECONDS:
                continue  # TTL-expired — drop silently (the moment has passed)
            if notice.physical_id in wanted or (notice.room_id and notice.room_id in wanted):
                drained.append(notice)
            else:
                kept.append(raw)
        if len(kept) != len(data["undelivered"]):
            data["undelivered"] = kept
            self._write(data)
        return drained


# ---------------------------------------------------------------------------
# Startup reconciliation (D-3/D-4)
# ---------------------------------------------------------------------------

async def reconcile_durable_actions(store: DurableActionStorePort,
                                    handlers_by_class: Dict[str, Any],
                                    notification_service: Optional[Any]) -> Dict[str, int]:
    """Re-derive the schedule from persisted intent (reconcile-by-diff, no log replay).

    For each record: future deadline → the owning handler's ``rearm_durable_action`` relaunches
    it (reusing the persisted ``action_name``); missed by ≤ grace → fire now with an apology;
    older / unknown handler / re-arm failure → expiry announcement. A consumed record (fired
    late / expired) is DELETED; a successful re-arm already REPLACED it — the relaunch persists
    a fresh record under the same ``action_name`` (D-8), so deleting here would destroy the
    re-armed promise and the timer would die silently at the next restart.
    """
    now = time.time()
    stats = {"rearmed": 0, "fired_late": 0, "expired": 0}
    for record in store.load_all():
        outcome = "expired"
        try:
            handler = handlers_by_class.get(record.handler)
            deadline = record.deadline if record.deadline is not None else now
            if deadline > now:
                # Future promise: re-arm via its handler; a missing/refusing handler means the
                # promise is LOST — announce it as expired rather than fire it early or drop it.
                if handler is not None and await handler.rearm_durable_action(record):
                    outcome = "rearmed"
            elif now - deadline <= GRACE_WINDOW_SECONDS:
                outcome = "fired_late"
        except Exception as e:
            logger.error(f"Re-arm failed for durable action '{record.action_name}': {e}")
            outcome = "expired"
        if outcome != "rearmed":
            # Consumed (announced) — delete. Rearmed records were upserted in place (same key)
            # by the relaunch and MUST survive for the next restart's reconciliation.
            store.delete(record.action_name)

        if outcome in ("fired_late", "expired"):
            await _announce_missed(record, notification_service, late=(outcome == "fired_late"))
        stats[outcome] += 1

    if any(stats.values()):
        logger.info(f"Durable-action reconciliation: {stats}")
    return stats


async def _announce_missed(record: DurableActionRecord, notification_service: Optional[Any],
                           late: bool) -> None:
    """D-4: fire-with-apology (late=True) or expiry announcement, to the owning room."""
    language = (record.metadata or {}).get("language") or "ru"
    message = (record.metadata or {}).get("completion_message") or record.action_name
    if late:
        text = _APOLOGY_PREFIX.get(language, _APOLOGY_PREFIX["ru"]) + message
    else:
        text = _EXPIRED_TEXT.get(language, _EXPIRED_TEXT["ru"]).format(message=message)
    if notification_service is None or record.session_id is None:
        logger.warning(f"Missed durable action (no delivery path): {text}")
        return
    try:
        await notification_service.send_action_completion_notification(
            session_id=record.session_id, domain=record.domain, action_name=record.action_name,
            duration=time.time() - record.started_at, success=True,
            source=record.source, physical_id=record.physical_id, room_name=record.room_id,
            language=language, completion_message=text)
    except Exception as e:
        logger.error(f"Failed to announce missed durable action '{record.action_name}': {e}")


# ---------------------------------------------------------------------------
# Global instance (path resolved through the asset-managed tree — D-2)
# ---------------------------------------------------------------------------

_store: Optional[DurableActionStorePort] = None


def get_durable_action_store() -> DurableActionStorePort:
    """Global store instance; default path `<assets_root>/state/durable_actions.json`."""
    global _store
    if _store is None:
        _store = JsonFileDurableActionStore(AssetConfig().state_root / "durable_actions.json")
    return _store


def set_durable_action_store(store: Optional[DurableActionStorePort]) -> None:
    """Override the global store (tests / alternative adapters)."""
    global _store
    _store = store
