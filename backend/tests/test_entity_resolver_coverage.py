"""
TEST-4 — entity-resolver coverage: the 4 resolvers (Temporal/Quantity/Device/Location).

Temporal + Quantity are pure parsers (no asset loader); Device + Location use the localization asset
loader and — since QUAL-11 — must DEGRADE (not crash) when it's unwired (the review's old P0 #4).
Hermetic, asyncio.run only.
"""

import asyncio
import unittest
from types import SimpleNamespace

from locveil_voice.core.entity_resolver import (
    TemporalEntityResolver,
    QuantityEntityResolver,
    DeviceEntityResolver,
    LocationEntityResolver,
)
from locveil_voice.intents.context_models import UnifiedConversationContext


def _arun(coro):
    return asyncio.run(coro)


_CTX = SimpleNamespace()  # Temporal/Quantity ignore context; Device/Location read device/room lists


class TestTemporal(unittest.TestCase):
    def setUp(self):
        self.r = TemporalEntityResolver()

    def test_hhmm_time(self):
        res = _arun(self.r.resolve("set it for 14:30", _CTX))
        self.assertEqual(res.resolved_value, {"hours": 14, "minutes": 30})
        self.assertEqual(res.resolution_type, "exact")
        self.assertEqual(res.metadata["format"], "HH:MM")

    def test_duration_ru_and_en(self):
        self.assertEqual(_arun(self.r.resolve("5 минут", _CTX)).resolved_value,
                         {"value": 5, "unit": "minutes"})
        self.assertEqual(_arun(self.r.resolve("2 hours", _CTX)).resolved_value,
                         {"value": 2, "unit": "hours"})

    def test_relative(self):
        res = _arun(self.r.resolve("tomorrow", _CTX))
        self.assertEqual(res.resolved_value["relative"], "tomorrow")
        self.assertEqual(res.resolution_type, "contextual")

    def test_no_match_returns_none(self):
        self.assertIsNone(_arun(self.r.resolve("absolutely nothing temporal", _CTX)))


class TestQuantity(unittest.TestCase):
    def setUp(self):
        self.r = QuantityEntityResolver()

    def test_degrees(self):
        res = _arun(self.r.resolve("set to 5 градусов", _CTX))
        self.assertEqual(res.resolved_value["value"], 5.0)
        self.assertEqual(res.resolved_value["unit"], "degrees")

    def test_percent_and_float(self):
        res = _arun(self.r.resolve("dim to 42.5 percent", _CTX))
        self.assertEqual(res.resolved_value["value"], 42.5)
        self.assertEqual(res.resolved_value["unit"], "percent")

    def test_no_number_returns_none(self):
        self.assertIsNone(_arun(self.r.resolve("some words", _CTX)))


class TestDeviceLocationDegradeGracefully(unittest.TestCase):
    """QUAL-11 P0 #4: with no asset loader these must return None / skip, NOT raise."""

    def _ctx(self):
        # a real context with no devices / no room — so resolution must degrade to None
        return UnifiedConversationContext(session_id="s")

    def test_device_resolver_without_asset_loader(self):
        r = DeviceEntityResolver(asset_loader=None)
        try:
            res = _arun(r.resolve("kitchen light", self._ctx()))
        except Exception as e:  # the old P0 raised RuntimeError here — must not happen now
            self.fail(f"DeviceEntityResolver.resolve crashed without asset loader: {e!r}")
        self.assertIsNone(res)

    def test_location_resolver_without_asset_loader(self):
        r = LocationEntityResolver(asset_loader=None)
        try:
            res = _arun(r.resolve("в спальне", self._ctx()))
        except Exception as e:
            self.fail(f"LocationEntityResolver.resolve crashed without asset loader: {e!r}")
        # may resolve to None (no rooms known) — the point is it degraded, not crashed
        self.assertTrue(res is None or hasattr(res, "resolved_value"))


if __name__ == "__main__":
    unittest.main()
