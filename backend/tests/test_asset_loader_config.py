"""CR-C13: the retired `validate_method_existence` validator (a duplicate boot-time handler import) is gone,
and AssetLoaderConfig (built via `AssetLoaderConfig(**config.asset_validation)`) absorbs stale/unknown keys
so a leftover config key can't crash boot."""
import unittest

from locveil_voice.core.intent_asset_loader import AssetLoaderConfig, IntentAssetLoader


class TestAssetLoaderConfigForwardCompat(unittest.TestCase):
    def test_absorbs_unknown_keys(self):
        cfg = AssetLoaderConfig(validate_method_existence=True, some_future_key=42)  # stale + unknown
        self.assertTrue(cfg.validate_contract_wiring)            # real flags still applied
        self.assertFalse(hasattr(cfg, "validate_method_existence"))  # retired flag not stored

    def test_method_existence_validator_removed(self):
        # Handler-wiring is now validated only by the contract validator (one import per handler).
        self.assertFalse(hasattr(IntentAssetLoader, "_validate_method_existence"))


if __name__ == "__main__":
    unittest.main()
