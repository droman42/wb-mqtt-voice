"""
Silero TTS base provider (CR-C6) - shared logic for Silero v3 and v4 TTS providers.

`SileroV3TTSProvider` and `SileroV4TTSProvider` were ~80% identical: torch device handling,
the cross-instance `TorchModelCache` plumbing (cache key ``f"{model_file}:{torch_device}"``),
config-schema scaffolding, asset-manager model-path routing, text normalization and warm-up
were duplicated verbatim. This base class holds that shared body; the subclasses override ONLY
the parts that genuinely differ (model URLs/directory, speaker handling, synthesis call, and the
version-specific defaults/log labels via overridable class attributes).
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List

from .base import TTSProvider

logger = logging.getLogger(__name__)


class SileroTTSBase(TTSProvider):
    """
    Shared base for Silero neural TTS providers (v3 / v4).

    Subclasses MUST set the version-specific class attributes below and provide a
    `_model_cache` (a per-class `TorchModelCache` instance), plus override
    `get_provider_name`, `get_capabilities`, `_get_default_directory`,
    `_get_default_model_urls`, `_load_model_async` and the synthesis methods.
    (`is_available` and `_download_model` are shared here — CR-A12/CR-A13.)
    """

    # --- Version-specific class attributes (overridden by subclasses) -----------------
    _version: str = ""                 # short label used in log strings, e.g. "v3" / "v4"
    _default_model_id: str = ""        # default `model` config value, e.g. "v3_ru" / "v4_ru"
    _default_sample_rate: int = 24000  # default `sample_rate`
    _default_speakers: List[str] = []  # available speaker list
    _model_info_id: str = ""           # id used for the asset-manager size lookup

    def __init__(self, config: Dict[str, Any]):
        """Initialize shared Silero provider state from configuration."""
        super().__init__(config)
        self._available = False
        self._model = None
        self._device = None
        self._torch: Any = None  # dynamically-imported optional torch module handle

        # Asset management integration - single source of truth
        from ...core.assets import get_asset_manager
        self.asset_manager = get_asset_manager()

        # Use asset manager for model paths - unified pattern
        # Get the provider directory (not a specific model file)
        provider_name = self.get_provider_name()
        asset_config = self.asset_manager._get_provider_asset_config(provider_name)
        directory_name = asset_config.get("directory_name", provider_name)
        self.model_path = self.asset_manager.config.models_root / directory_name

        # Model selection is model_id-routed (consistent with sherpa/whisper/vosk): the file lands at
        # get_model_path(provider_name, model_id). `model_file` is still honored as an explicit path
        # override; `model_url` defaults to the selected model_id's descriptor URL.
        self.model_id = config.get("model", self._default_model_id)
        _model_urls = self._get_default_model_urls()
        self.model_url = config.get(
            "model_url", _model_urls.get(self.model_id, _model_urls[self._default_model_id])
        )
        self.model_file = (
            self.model_path / config["model_file"] if config.get("model_file")
            else self.asset_manager.get_model_path(provider_name, self.model_id)
        )
        # QUAL-38: number-spelling language matches the loaded MODEL (default model is Russian).
        self.language = config.get("language", "ru")
        self.default_speaker = config.get("default_speaker", "xenia")
        self.sample_rate = config.get("sample_rate", self._default_sample_rate)
        self.torch_device = config.get("torch_device", "cpu")

        # Available speakers (per-version list)
        self._speakers = list(self._default_speakers)

        # Try to import dependencies
        try:
            import torch  # type: ignore
            self._torch = torch
            self._device = torch.device(self.torch_device)
            self._available = True
            logger.info(f"Silero {self._version} TTS provider dependencies available")
        except ImportError:
            self._available = False
            logger.warning(
                f"Silero {self._version} TTS provider dependencies not available (torch required)"
            )

        # Initialize model on startup if requested
        preload_models = config.get("preload_models", False)
        if preload_models and self._available:
            # Schedule model loading for startup
            import asyncio
            self._warmup_task = asyncio.create_task(self.warm_up())  # QUAL-58: hold the ref (unreferenced tasks are GC-cancellable mid-load)

    # --- Shared config-schema scaffolding ---------------------------------------------
    @classmethod
    def _get_default_extension(cls) -> str:
        """Silero models use PyTorch .pt format"""
        return ".pt"

    @classmethod
    def _get_default_credentials(cls) -> List[str]:
        """Silero is open source, no credentials needed"""
        return []

    @classmethod
    def _get_default_cache_types(cls) -> List[str]:
        """Uses models cache for PyTorch models and runtime cache for temporary audio"""
        return ["models", "runtime"]

    @classmethod
    def _get_default_model_urls(cls) -> Dict[str, str]:
        """Per-version model URLs (must be provided by subclass)."""
        raise NotImplementedError

    # Subclass-provided members (declared so the shared body type-checks; real values live on the subclass).
    _model_cache: Any  # a per-class TorchModelCache instance

    async def _load_model_async(self) -> None:
        """Download (if needed) + load the model into ``self._model``. Provided by subclass."""
        raise NotImplementedError

    async def is_available(self) -> bool:
        """Whether the provider can run. Local-only (CR-A12): torch present is enough — the model
        downloads lazily at synthesis/preload time and fails through the fallback chain. An async
        availability check must not do a blocking network/file probe (QUAL-15)."""
        return self._available and self._torch is not None

    def _download_model(self, model_path: Path) -> None:
        """Download the model via the legacy torch.hub path (called from a worker thread). CR-A13:
        always uses ``self.model_url`` (v4 previously hardcoded the RU wheel, ignoring model_url/model_id)."""
        if not self._torch:
            return
        try:
            self._torch.hub.download_url_to_file(self.model_url, str(model_path))
            logger.info(f"Silero {self._version} model downloaded to: {model_path}")
        except Exception as e:
            logger.error(f"Failed to download Silero {self._version} model: {e}")
            raise

    # --- Shared build-dependency methods ----------------------------------------------
    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        """Silero requires runtime dependencies for model inference"""
        return ["tts-silero"]  # Build extra: tts-silero

    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        """Platform-specific system packages for Silero"""
        return {
            "linux.ubuntu": ["libsndfile1"],
            "linux.alpine": ["libsndfile"],
            "macos": ["libsndfile"],  # macOS includes audio libraries
            "windows": []  # Windows package management differs
        }
    @classmethod
    def get_supported_architectures(cls) -> List[str]:
        return ["x86_64", "aarch64"]  # torch has no armv7 wheel (ARCH-24 T3)

    # --- Shared model-cache plumbing --------------------------------------------------
    async def _ensure_model_loaded(self) -> None:
        """Ensure the model is loaded — cached across instances by (model_file, device) (ARCH-24 T5)."""
        if not self._available:
            raise RuntimeError(
                f"Silero {self._version} TTS provider not available (torch dependency missing)"
            )
        if not self._model:
            cache_key = f"{self.model_file}:{self.torch_device}"
            self._model = await self._model_cache.get_or_load(cache_key, self._load_model_returning)
        if not self._model:
            raise RuntimeError(f"Failed to load Silero {self._version} model")

    async def _load_model_returning(self) -> Any:
        """Loader for the shared cache: download (if needed) + load, returning the model."""
        await self._load_model_async()  # sets self._model
        return self._model

    def _load_model(self, model_path: Path) -> None:
        """Load model from file (called from thread)"""
        if not self._torch:
            return

        try:
            self._model = self._torch.package.PackageImporter(str(model_path)).load_pickle("tts_models", "model")
            self._model.to(self._device)
            logger.info(f"Silero {self._version} model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Silero {self._version} model: {e}")
            raise

    async def warm_up(self) -> None:
        """Warm up by preloading the Silero model"""
        try:
            logger.info(f"Warming up Silero {self._version} TTS model...")
            await self._ensure_model_loaded()
            logger.info(f"Silero {self._version} TTS model warmed up successfully")
        except Exception as e:
            logger.error(f"Failed to warm up Silero {self._version} model: {e}")
            # Don't raise - let the provider work with lazy loading

    async def _normalize_text_async(self, text: str) -> str:
        """Normalize text asynchronously"""
        # Basic text normalization
        normalized = text.replace("…", "...")

        # Modern number-to-text conversion using migrated utilities
        try:
            from ...utils.text_processing import all_num_to_text_async
            normalized = await all_num_to_text_async(normalized, language=self.language)
            logger.debug("Applied number-to-text normalization")
        except Exception as e:
            logger.debug(f"Text normalization failed, using original: {e}")

        return normalized
