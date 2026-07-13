"""CR-C10: shared asset-name / asset-path helpers (deduped from intent_asset_loader +
cross_language_validator, which previously each defined `_get_asset_handler_name` and inlined `[:-8]`)."""
import unittest
from pathlib import Path

from locveil_voice.core.intent_asset_loader import (
    asset_dir_name, base_handler_name, IntentAssetLoader, AssetLoaderConfig,
)


class TestAssetNaming(unittest.TestCase):
    def test_asset_dir_name_appends_suffix(self):
        self.assertEqual(asset_dir_name("timer"), "timer_handler")

    def test_asset_dir_name_is_idempotent(self):
        self.assertEqual(asset_dir_name("audio_playback_handler"), "audio_playback_handler")

    def test_base_handler_name_strips_suffix(self):
        self.assertEqual(base_handler_name("timer_handler"), "timer")

    def test_base_handler_name_noop_without_suffix(self):
        self.assertEqual(base_handler_name("timer"), "timer")

    def test_round_trip(self):
        self.assertEqual(base_handler_name(asset_dir_name("greetings")), "greetings")


class TestAssetPath(unittest.TestCase):
    def _loader(self):
        return IntentAssetLoader(Path("/srv/assets"), AssetLoaderConfig())

    def test_builds_under_assets_root(self):
        self.assertEqual(
            self._loader()._asset_path("donations", "timer_handler", "contract.json"),
            Path("/srv/assets/donations/timer_handler/contract.json"),
        )

    def test_single_segment(self):
        self.assertEqual(self._loader()._asset_path("schema.json"), Path("/srv/assets/schema.json"))


if __name__ == "__main__":
    unittest.main()
