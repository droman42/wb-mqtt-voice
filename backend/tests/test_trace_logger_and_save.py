"""
ARCH-19 slice 2 — TraceLogger handler, [trace] config, and save-every-request.

Covers the net-new surface: the global `TraceLogger` (inert unless a trace is
active, captures records + exceptions, bounded by its cap), the `TraceConfig`
section + default `traces_root`, and the WorkflowManager save helpers that honour
the D-17 "save only when startup tracing is on" gate.
"""

import json
import logging
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from locveil_voice.config.models import AssetConfig, CoreConfig, TraceConfig
from locveil_voice.core.trace_context import TraceContext, TraceLogger, trace_scope
from locveil_voice.core.workflow_manager import WorkflowManager


class TestTraceLogger(unittest.TestCase):
    def setUp(self):
        self.handler = TraceLogger(level=logging.INFO, max_records=3)
        self.log = logging.getLogger("arch19.test")
        self.log.addHandler(self.handler)
        self.log.setLevel(logging.DEBUG)
        self.log.propagate = False

    def tearDown(self):
        self.log.removeHandler(self.handler)

    def test_inert_without_active_trace(self):
        self.log.info("no trace active")  # must not raise / nowhere to go
        self.assertIsNone(TraceContext(enabled=True).logs or None)

    def test_captures_into_active_trace(self):
        trace = TraceContext(enabled=True)
        with trace_scope(trace):
            self.log.info("hello %s", "world")
        self.assertEqual(len(trace.logs), 1)
        rec = trace.logs[0]
        self.assertEqual(rec["level"], "INFO")
        self.assertEqual(rec["message"], "hello world")
        self.assertEqual(rec["logger"], "arch19.test")
        self.assertIsNone(rec["exc_text"])

    def test_threshold_filters_below_level(self):
        trace = TraceContext(enabled=True)
        with trace_scope(trace):
            self.log.debug("below threshold")   # < INFO → dropped by handler level
            self.log.warning("kept")
        self.assertEqual([r["message"] for r in trace.logs], ["kept"])

    def test_exception_traceback_captured(self):
        trace = TraceContext(enabled=True)
        with trace_scope(trace):
            try:
                raise ValueError("boom")
            except ValueError:
                self.log.error("it failed", exc_info=True)
        self.assertIn("ValueError: boom", trace.logs[0]["exc_text"])

    def test_record_cap_bounds_the_file(self):
        trace = TraceContext(enabled=True)
        with trace_scope(trace):
            for i in range(10):
                self.log.info("msg %d", i)
        self.assertEqual(len(trace.logs), 3)  # max_records

    def test_disabled_trace_captures_nothing(self):
        trace = TraceContext(enabled=False)
        with trace_scope(trace):
            self.log.info("ignored")
        self.assertEqual(trace.logs, [])


class TestTraceConfig(unittest.TestCase):
    def test_defaults_are_off(self):
        cfg = TraceConfig()
        self.assertFalse(cfg.enabled)
        self.assertFalse(cfg.capture_raw_mic)
        self.assertEqual(cfg.capture_level, "utterance")
        self.assertIsNone(cfg.traces_dir)

    def test_coreconfig_has_trace_section(self):
        cfg = CoreConfig()
        self.assertIsInstance(cfg.trace, TraceConfig)
        self.assertFalse(cfg.trace.enabled)

    def test_assets_traces_root_default(self):
        assets = AssetConfig(assets_root=Path("/tmp/irene-assets"))
        self.assertEqual(assets.traces_root, Path("/tmp/irene-assets/traces"))

    def test_trace_is_a_discovered_section(self):
        from locveil_voice.config.auto_registry import AutoSchemaRegistry
        meta = AutoSchemaRegistry.get_section_order_and_titles()
        self.assertIn("trace", meta["section_order"])
        self.assertEqual(meta["section_titles"]["trace"], "🧪 Trace Persistence")


class _WMShim(WorkflowManager):
    """Bypass the heavy __init__ — we only exercise the save helpers."""
    def __init__(self, config):
        self.config = config


class TestSaveEveryRequest(unittest.TestCase):
    def _config(self, *, enabled, traces_dir=None, assets_root="/tmp/x"):
        return SimpleNamespace(
            trace=TraceConfig(enabled=enabled, traces_dir=traces_dir),
            assets=AssetConfig(assets_root=Path(assets_root)),
        )

    def test_no_save_when_disabled(self):
        with tempfile.TemporaryDirectory() as d:
            wm = _WMShim(self._config(enabled=False, traces_dir=d))
            trace = TraceContext(enabled=True, request_id="r1")
            wm._save_trace_if_enabled(trace)
            self.assertEqual(list(Path(d).glob("*.json")), [])

    def test_saves_when_enabled(self):
        with tempfile.TemporaryDirectory() as d:
            wm = _WMShim(self._config(enabled=True, traces_dir=d))
            trace = TraceContext(enabled=True, request_id="r2")
            trace.record_input("text", text="привет")
            wm._save_trace_if_enabled(trace)
            files = list(Path(d).glob("*.json"))
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].name, "r2.json")
            loaded = json.loads(files[0].read_text(encoding="utf-8"))
            self.assertEqual(loaded["request_id"], "r2")

    def test_maybe_create_trace_mints_when_enabled(self):
        wm = _WMShim(self._config(enabled=True))
        created = wm._maybe_create_trace(None)
        self.assertIsNotNone(created)
        self.assertTrue(created.enabled)
        self.assertEqual(created.capture_level, "utterance")

    def test_maybe_create_trace_noop_when_disabled(self):
        wm = _WMShim(self._config(enabled=False))
        self.assertIsNone(wm._maybe_create_trace(None))

    def test_maybe_create_trace_honours_passed_trace(self):
        wm = _WMShim(self._config(enabled=True))
        passed = TraceContext(enabled=True, request_id="explicit")
        self.assertIs(wm._maybe_create_trace(passed), passed)

    def test_traces_dir_defaults_under_assets_root(self):
        wm = _WMShim(self._config(enabled=True, traces_dir=None, assets_root="/tmp/aaa"))
        self.assertEqual(wm._traces_dir(), Path("/tmp/aaa/traces"))


if __name__ == "__main__":
    unittest.main()
