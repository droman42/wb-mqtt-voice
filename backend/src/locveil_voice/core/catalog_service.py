"""CatalogService — the application-layer holder of the device catalog (ARCH-8 PR-1).

Implements the domain's `DeviceCatalogPort` (QUAL-24 pattern: the application
inherits the port and is injected inward). Holds the current `DeviceCatalog`
snapshot and the ARCH-26 lazy-refresh seam: a `fetcher` coroutine — wired by
the composition root once the `BridgeClient` adapter exists (PR-2) — pulls
`GET /system/catalog` and this service swaps the snapshot atomically. Until a
fetcher is wired (or while the bridge is unreachable) the service simply serves
the last good snapshot; a refresh failure never discards it (fail-loud in the
log, fail-soft on the data — `mqtt_integration.md` §9).
"""

import asyncio
import logging
from typing import Awaitable, Callable, Optional

from ..intents.device_catalog import DeviceCatalog
from ..intents.ports import DeviceCatalogPort

logger = logging.getLogger(__name__)

# The PR-2 BridgeClient supplies this: pull + parse one catalog snapshot.
CatalogFetcher = Callable[[], Awaitable[DeviceCatalog]]
# The PR-5 BridgeClient supplies this: live state of one device (None on failure).
StateReader = Callable[[str], Awaitable[Optional[dict]]]
# QUAL-65: runtime option-set enumeration (options_from) — list of option strings, None on failure.
OptionsReader = Callable[[str, str], Awaitable[Optional[list]]]

# options_from sets are dynamic but not per-utterance dynamic — a short TTL keeps repeated
# commands («запусти ютуб», «нет, нетфликс») from re-fetching inside one conversation.
OPTIONS_CACHE_TTL_S = 30.0


class CatalogService(DeviceCatalogPort):
    """Holds the catalog snapshot; refreshes lazily through the wired fetcher."""

    def __init__(self, fetcher: Optional[CatalogFetcher] = None,
                 state_reader: Optional[StateReader] = None,
                 options_reader: Optional[OptionsReader] = None) -> None:
        self._fetcher = fetcher
        self._state_reader = state_reader
        self._options_reader = options_reader
        self._catalog: Optional[DeviceCatalog] = None
        # (device_id, kind) -> (monotonic deadline, options)
        self._options_cache: dict = {}
        # serialize concurrent lazy refreshes (two misses in flight → one pull)
        self._refresh_lock = asyncio.Lock()

    def set_fetcher(self, fetcher: CatalogFetcher) -> None:
        """Wire the catalog source (composition root, once the adapter exists)."""
        self._fetcher = fetcher

    def set_state_reader(self, reader: StateReader) -> None:
        """Wire the live-state source (composition root, with the fetcher)."""
        self._state_reader = reader

    def set_options_reader(self, reader: OptionsReader) -> None:
        """Wire the dynamic option-set source (composition root, with the fetcher)."""
        self._options_reader = reader

    def set_catalog(self, catalog: DeviceCatalog) -> None:
        """Install a snapshot directly (startup pull result, or tests)."""
        self._catalog = catalog

    # --- DeviceCatalogPort ----------------------------------------------------------------------

    def catalog(self) -> Optional[DeviceCatalog]:
        return self._catalog

    async def refresh(self) -> Optional[DeviceCatalog]:
        if self._fetcher is None:
            logger.debug("catalog refresh requested but no fetcher is wired (pre-PR-2 / no bridge)")
            return None
        async with self._refresh_lock:
            try:
                fresh = await self._fetcher()
            except Exception as e:
                logger.warning(f"catalog refresh failed; keeping the previous snapshot: {e}")
                return None
            previous = self._catalog
            self._catalog = fresh
            if previous is None or previous.version != fresh.version:
                logger.info(
                    f"device catalog refreshed: version "
                    f"{previous.version if previous else '(none)'} -> {fresh.version}, "
                    f"{len(fresh.devices)} devices / {len(fresh.rooms)} rooms")
            return fresh

    async def read_state(self, device_id: str) -> Optional[dict]:
        if self._state_reader is None:
            logger.debug("state read requested but no reader is wired (pre-PR-2 / no bridge)")
            return None
        try:
            return await self._state_reader(device_id)
        except Exception as e:
            logger.warning(f"state read for '{device_id}' failed: {e}")
            return None

    async def read_options(self, device_id: str, kind: str) -> Optional[list]:
        if self._options_reader is None:
            logger.debug("options read requested but no reader is wired (pre-PR-2 / no bridge)")
            return None
        key = (device_id, kind)
        cached = self._options_cache.get(key)
        now = asyncio.get_event_loop().time()
        if cached is not None and cached[0] > now:
            return cached[1]
        try:
            options = await self._options_reader(device_id, kind)
        except Exception as e:
            logger.warning(f"options read for '{device_id}/{kind}' failed: {e}")
            return None
        if options is not None:
            self._options_cache[key] = (now + OPTIONS_CACHE_TTL_S, options)
        return options
