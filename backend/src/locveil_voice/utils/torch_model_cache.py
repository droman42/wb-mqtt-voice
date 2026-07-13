"""Process-wide async cache for lazily-loaded torch models (ARCH-24 T5).

Dedups the identical pattern that `silero_v3` and `silero_v4` each carried: a class-level dict + an
`asyncio.Lock` + a get-or-load method. A model is loaded **once** per key (e.g. `(model_file, device)`)
under the lock and shared across all provider instances. Torch is 64-bit only, so this never runs on
armv7.
"""

import asyncio
from typing import Any, Awaitable, Callable, Dict


class TorchModelCache:
    """A small async, lock-guarded cache: `get_or_load(key, loader)` loads once and reuses."""

    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def get_or_load(self, key: str, loader: Callable[[], Awaitable[Any]]) -> Any:
        """Return the cached model for `key`; otherwise `await loader()` once (under the lock) and cache it.

        The lock makes concurrent first-time loads of the same key wait for the single load rather than
        each downloading/initialising their own copy.
        """
        async with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                return cached
            model = await loader()
            self._cache[key] = model
            return model
