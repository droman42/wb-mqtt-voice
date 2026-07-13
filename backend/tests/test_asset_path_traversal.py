"""Regression tests for the asset-loader path-traversal hardening (review CR-A15)."""
import tempfile
import unittest
from pathlib import Path

from locveil_voice.core.intent_asset_loader import (
    IntentAssetLoader, AssetLoaderConfig, _safe_path_segment,
)


class TestSafeSegment(unittest.TestCase):
    def test_accepts_valid_segments(self):
        for v in ["ru", "en", "timer_handler", "audio_playback", "v1.1", "en-US"]:
            self.assertEqual(_safe_path_segment(v, "x"), v)

    def test_rejects_traversal_and_separators(self):
        for v in ["..", "../etc", "a/b", "a\\b", "/abs", "", ".", ".hidden",
                  "a..b", "x\x00y", "~", "a/../b", "../../../../etc/passwd"]:
            with self.assertRaises(ValueError):
                _safe_path_segment(v, "x")


class TestAssetLoaderPathTraversal(unittest.TestCase):
    """Verify the SECURITY invariant (traversal is blocked) regardless of the fail-closed mechanism —
    a method may raise ValueError or return its failure sentinel ((False, _) / None); both are fine."""

    def _loader(self, root):
        return IntentAssetLoader(Path(root), AssetLoaderConfig())

    def _blocked(self, fn):
        """Call fn; assert it fails closed (raises ValueError, or returns (False,_) / None)."""
        try:
            res = fn()
        except ValueError:
            return
        if isinstance(res, tuple):
            self.assertFalse(res[0], "save should not report success on traversal input")
        else:
            self.assertIsNone(res, "get should not return data on traversal input")

    def test_save_localization_traversal_domain_writes_nothing_outside_root(self):
        with tempfile.TemporaryDirectory() as d:
            loader = self._loader(d)
            self._blocked(lambda: loader.save_localization_for_domain("../../evil", "ru", {"x": 1}))
            self.assertEqual(list(Path(d).parent.glob("evil*")), [])  # nothing escaped the root

    def test_save_phrasing_traversal_language(self):
        with tempfile.TemporaryDirectory() as d:
            loader = self._loader(d)
            self._blocked(lambda: loader.save_language_phrasing("timer", "../../../etc/passwd", {"x": 1}))

    def test_get_localization_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            loader = self._loader(d)
            self._blocked(lambda: loader.get_localization_for_domain_editing("../../etc", "passwd"))

    def test_handler_name_validated_centrally(self):
        with tempfile.TemporaryDirectory() as d:
            loader = self._loader(d)
            # _get_asset_handler_name is the single choke point for handler-derived paths.
            self._blocked(lambda: loader.get_contract_for_editing("../../../etc/passwd"))
            self._blocked(lambda: loader.save_contract("../../evil", {"x": 1}))

    def test_valid_inputs_still_work(self):
        with tempfile.TemporaryDirectory() as d:
            loader = self._loader(d)
            ok, _ = loader.save_localization_for_domain("timer", "ru", {"greeting": "привет"})
            self.assertTrue(ok)
            self.assertTrue((Path(d) / "localization" / "timer" / "ru.yaml").exists())


if __name__ == "__main__":
    unittest.main()
