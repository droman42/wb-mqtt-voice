"""TorchModelCache — the shared lazy torch-model cache (ARCH-24 T5).

Dedups the identical silero v3/v4 pattern: load once per key, reuse, and serialize concurrent
first-time loads of the same key.
"""

import asyncio

from irene.utils.torch_model_cache import TorchModelCache


def test_loads_once_then_serves_from_cache():
    cache = TorchModelCache()
    calls = {"n": 0}

    async def loader():
        calls["n"] += 1
        return "MODEL"

    async def run():
        a = await cache.get_or_load("k", loader)
        b = await cache.get_or_load("k", loader)
        return a, b

    a, b = asyncio.run(run())
    assert a == b == "MODEL"
    assert calls["n"] == 1  # second call hit the cache


def test_distinct_keys_load_independently():
    cache = TorchModelCache()

    async def run():
        async def mk(v):
            async def loader():
                return v
            return await cache.get_or_load(v, loader)
        return await mk("A"), await mk("B")

    assert asyncio.run(run()) == ("A", "B")


def test_concurrent_first_load_runs_loader_once():
    cache = TorchModelCache()
    calls = {"n": 0}

    async def loader():
        calls["n"] += 1
        await asyncio.sleep(0)  # yield, so both would interleave without the lock
        return "M"

    async def run():
        return await asyncio.gather(cache.get_or_load("k", loader), cache.get_or_load("k", loader))

    assert asyncio.run(run()) == ["M", "M"]
    assert calls["n"] == 1  # the lock serialized the two first-time loads into one
