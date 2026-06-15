"""
Test spaCy Asset Management Integration

Contract-level tests for the spaCy NLU provider's integration with the standard
asset-management system. These assert the PUBLIC/PORT behaviour:

  - the asset-config contract (`get_asset_config`) the asset manager consumes,
  - that initialization routes model verification through
    `asset_manager.ensure_model_available(provider_name="spacy_nlu", ...)`,
  - the per-language fallback order (md -> sm), graceful degradation when the
    asset manager fails, and the no-model / no-spacy off-paths,
  - backwards compatibility without an asset manager.

The provider is constructed directly (its __init__ is lightweight: no model is
loaded until is_available/recognize/_initialize_* is called). `spacy` is replaced
via the module-bound `safe_import` so no real model download is required.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from irene.providers.nlu.spacy_provider import SpaCyNLUProvider


# Patch target: `safe_import` is bound into the provider module at import time.
SAFE_IMPORT = "irene.providers.nlu.spacy_provider.safe_import"


def _make_spacy(load=None):
    """Build a fake `spacy` module whose `.load` is controllable."""
    mock_spacy = MagicMock()
    mock_spacy.__version__ = "3.7.0"
    if load is None:
        mock_spacy.load.return_value = MagicMock(name="nlp")
    else:
        mock_spacy.load.side_effect = load
    return mock_spacy


class TestSpaCyAssetConfigContract:
    """The asset-config dict the asset manager relies on."""

    def test_get_asset_config_shape(self):
        cfg = SpaCyNLUProvider.get_asset_config()

        assert isinstance(cfg, dict)
        # spaCy models are installed as Python packages, not downloaded files.
        assert cfg["uses_python_packages"] is True
        assert cfg["directory_name"] == "spacy"
        assert cfg["cache_types"] == ["runtime"]
        assert cfg["credential_patterns"] == []

    def test_language_support_lists_known_models(self):
        cfg = SpaCyNLUProvider.get_asset_config()
        lang = cfg["language_support"]

        assert "ru_core_news_sm" in lang["ru"]
        assert "en_core_web_sm" in lang["en"]
        # md preferred over sm within each language.
        assert lang["ru"].index("ru_core_news_md") < lang["ru"].index("ru_core_news_sm")

    def test_package_dependencies_are_pinned_wheels(self):
        cfg = SpaCyNLUProvider.get_asset_config()
        deps = cfg["package_dependencies"]

        assert deps, "expected at least one packaged model dependency"
        for dep in deps:
            assert dep.endswith(".whl")
            assert "3.7.0" in dep

    def test_language_preferences_mirror_asset_config(self):
        """Runtime model-resolution order must match the declared asset config."""
        provider = SpaCyNLUProvider({})
        cfg = SpaCyNLUProvider.get_asset_config()
        assert provider.language_preferences["ru"] == cfg["language_support"]["ru"]
        assert provider.language_preferences["en"] == cfg["language_support"]["en"]


class TestSpaCyAssetInitialization:
    """Initialization routing through the asset manager + spaCy loading."""

    @pytest.fixture
    def asset_manager(self):
        """Async asset manager whose ensure_model_available yields a wheel path."""
        manager = MagicMock()

        async def ensure(provider_name, model_name, asset_config):
            return Path(f"/tmp/test/{model_name}-3.7.0-py3-none-any.whl")

        manager.ensure_model_available = AsyncMock(side_effect=ensure)
        return manager

    @pytest.fixture
    def provider(self):
        return SpaCyNLUProvider({"confidence_threshold": 0.7})

    @pytest.mark.asyncio
    async def test_routes_through_asset_manager_then_loads(self, provider, asset_manager):
        provider.asset_manager = asset_manager
        mock_spacy = _make_spacy()

        with patch(SAFE_IMPORT, return_value=mock_spacy):
            await provider._initialize_spacy_with_assets()

        # Asset manager was consulted with the provider's own name + asset config.
        asset_manager.ensure_model_available.assert_awaited()
        call = asset_manager.ensure_model_available.call_args
        assert call.kwargs["provider_name"] == "spacy_nlu"
        assert call.kwargs["model_name"] in (
            provider.language_preferences["ru"] + provider.language_preferences["en"]
        )
        assert call.kwargs["asset_config"] == SpaCyNLUProvider.get_asset_config()

        # First model verified is the most-preferred Russian model.
        first_model = asset_manager.ensure_model_available.call_args_list[0].kwargs["model_name"]
        assert first_model == provider.language_preferences["ru"][0]

        # spaCy model loaded; primary nlp set to the Russian model.
        mock_spacy.load.assert_called()
        assert provider.nlp is not None
        assert "ru" in provider.available_models

    @pytest.mark.asyncio
    async def test_per_language_fallback_md_to_sm(self, provider, asset_manager):
        """When the preferred md model is unavailable, the sm model is used."""
        provider.asset_manager = asset_manager

        def load(model_name):
            if model_name.endswith("_md"):
                raise OSError(f"{model_name} not installed")
            return MagicMock(name=model_name)

        mock_spacy = _make_spacy(load=load)

        with patch(SAFE_IMPORT, return_value=mock_spacy):
            await provider._initialize_spacy_with_assets()

        mock_spacy.load.assert_any_call("ru_core_news_sm")
        mock_spacy.load.assert_any_call("en_core_web_sm")
        assert provider.nlp is not None
        assert set(provider.available_models) == {"ru", "en"}

    @pytest.mark.asyncio
    async def test_graceful_degradation_when_asset_manager_fails(self, provider):
        """If the asset manager raises, the provider still loads via standard spaCy."""
        failing = MagicMock()
        failing.ensure_model_available = AsyncMock(side_effect=Exception("download failed"))
        provider.asset_manager = failing

        mock_spacy = _make_spacy()

        with patch(SAFE_IMPORT, return_value=mock_spacy):
            await provider._initialize_spacy_with_assets()

        mock_spacy.load.assert_called()
        assert provider.nlp is not None

    @pytest.mark.asyncio
    async def test_no_models_available_raises_runtime_error(self, provider, asset_manager):
        """Every spaCy.load failing is a configuration error, surfaced as RuntimeError."""
        provider.asset_manager = asset_manager
        mock_spacy = _make_spacy(load=OSError("no model installed"))

        with patch(SAFE_IMPORT, return_value=mock_spacy):
            with pytest.raises(RuntimeError):
                await provider._initialize_spacy_with_assets()

        assert provider.nlp is None
        assert provider.available_models == {}

    @pytest.mark.asyncio
    async def test_spacy_not_installed_raises(self, provider, asset_manager):
        provider.asset_manager = asset_manager

        with patch(SAFE_IMPORT, return_value=None):
            with pytest.raises(ImportError):
                await provider._initialize_spacy_with_assets()

        assert provider.nlp is None


class TestSpaCyBackwardsCompatibility:
    """Provider must work with no asset manager wired (the legacy path)."""

    @pytest.mark.asyncio
    async def test_initialize_without_asset_manager(self):
        provider = SpaCyNLUProvider({})
        assert provider.asset_manager is None  # nothing wired by default

        mock_spacy = _make_spacy()
        with patch(SAFE_IMPORT, return_value=mock_spacy):
            await provider._initialize_spacy()

        mock_spacy.load.assert_called()
        assert provider.nlp is not None
        # Standard path does not touch any asset manager.
        assert provider.asset_manager is None
