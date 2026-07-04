"""
Asset Management System

Centralized management of models, cache, and credentials for Irene Voice Assistant.
Supports environment variable configuration for Docker-friendly deployments.

Enhanced in TODO #4 Phase 2 with configuration-driven asset management.
"""

import os
import asyncio
import logging
import pickle
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
import json

# ARCH-2: real import now that config no longer runs schema validation at import time
# (and no longer reaches up into core), so core->config.models is a clean downward edge.
from ..config.models import AssetConfig

logger = logging.getLogger(__name__)


class AssetManager:
    """Centralized asset manager for models, cache, and credentials"""

    def __init__(self, config: "AssetConfig"):
        self.config = config
        self._download_locks: Dict[str, asyncio.Lock] = {}
        self._provider_asset_cache: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def from_env(cls) -> "AssetManager":
        """Create AssetManager from environment variables"""
        config = AssetConfig()
        return cls(config)
    
    def _get_provider_asset_config(self, provider: str) -> Dict[str, Any]:
        """
        Get asset configuration for a provider by querying the provider class.
        
        This replaces hardcoded mappings with configuration-driven approach.
        Uses provider class asset methods implemented in TODO #4 Phase 1.
        
        Args:
            provider: Provider name (e.g., 'whisper', 'silero', 'elevenlabs')
            
        Returns:
            Asset configuration dictionary with defaults and TOML overrides
        """
        # Check cache first
        if provider in self._provider_asset_cache:
            return self._provider_asset_cache[provider]
        
        # Discover provider class and get asset config
        from ..utils.loader import dynamic_loader
        
        # Map asset names to namespaces. A tuple value maps an asset name to a DIFFERENT
        # entry-point name — needed when two provider families share an entry-point name
        # (e.g. 'silero' is silero TTS here; the silero VAD provider's assets live under
        # the distinct asset name 'silero_vad'). ASSET-4.
        provider_namespace_map = {
            'whisper': 'irene.providers.asr',
            'silero': 'irene.providers.tts',
            'silero_vad': ('irene.providers.vad', 'silero'),
            'vosk': 'irene.providers.asr',
            'openwakeword': 'irene.providers.voice_trigger',
            'microwakeword': 'irene.providers.voice_trigger',
            'elevenlabs': 'irene.providers.tts',
            'openai': 'irene.providers.llm',
            'anthropic': 'irene.providers.llm',
            'google_cloud': 'irene.providers.asr',
            'sounddevice': 'irene.providers.audio',
            'console': 'irene.providers.audio',
        }

        # Try to find the provider in appropriate namespace
        provider_class = None
        if provider in provider_namespace_map:
            entry = provider_namespace_map[provider]
            namespace, ep_name = entry if isinstance(entry, tuple) else (entry, provider)
            provider_class = dynamic_loader.get_provider_class(namespace, ep_name)
        else:
            # Search across all provider namespaces
            namespaces = [
                'irene.providers.tts',
                'irene.providers.asr',
                'irene.providers.audio',
                'irene.providers.llm',
                'irene.providers.voice_trigger',
                'irene.providers.vad',
                'irene.providers.nlu',
                'irene.providers.text_processor'
            ]
            for namespace in namespaces:
                provider_class = dynamic_loader.get_provider_class(namespace, provider)
                if provider_class:
                    break
        
        if provider_class and hasattr(provider_class, 'get_asset_config'):
            try:
                # Always call the provider's actual get_asset_config method to respect overrides
                asset_config = provider_class.get_asset_config()
                logger.debug(f"Loaded asset config for provider '{provider}': {asset_config}")
            except Exception as e:
                logger.warning(f"Failed to get class-level asset config for provider '{provider}': {e}")
                # Fallback to generic defaults if class method fails
                asset_config = self._get_fallback_asset_config(provider)
        else:
            logger.debug(f"Provider '{provider}' not found or no asset config method, using fallback")
            asset_config = self._get_fallback_asset_config(provider)
        
        # Cache the result
        self._provider_asset_cache[provider] = asset_config
        return asset_config
    
    def _get_fallback_asset_config(self, provider: str) -> Dict[str, Any]:
        """
        Minimal fallback asset configuration for providers without explicit config.
        
        Uses generic defaults instead of hardcoded provider-specific mappings.
        All known providers should implement asset configuration methods.
        """
        logger.warning(f"Provider '{provider}' not found or missing asset config - using generic defaults")
        
        # Generic defaults that work for any provider
        return {
            "file_extension": "",                  # No extension assumption
            "directory_name": provider,            # Use provider name as directory
            "credential_patterns": [],             # No credentials assumed
            "cache_types": ["runtime"],            # Minimal cache usage
            "model_urls": {}                       # No model URLs
        }
    
    def get_model_path(self, provider: str, model_id: str, filename: Optional[str] = None) -> Path:
        """Get standardized model path using provider asset configuration"""
        # Get provider asset configuration instead of hardcoded mapping
        asset_config = self._get_provider_asset_config(provider)
        
        # Use configured directory name
        directory_name = asset_config.get("directory_name", provider)
        provider_dir = self.config.models_root / directory_name
        
        if filename:
            return provider_dir / filename
        
        # Use configured file extension
        file_extension = asset_config.get("file_extension", "")
        if file_extension:
            return provider_dir / f"{model_id}{file_extension}"
        else:
            return provider_dir / model_id
    
    def get_cache_path(self, cache_type: str = "runtime") -> Path:
        """Get cache directory path"""
        cache_attr = f"{cache_type}_cache_dir"
        return getattr(self.config, cache_attr, self.config.cache_root / cache_type)
    
    def get_provider_cache_path(self, provider_name: str) -> Path:
        """Get provider-specific cache directory path"""
        return self.config.cache_root / provider_name
    
    async def get_cached_data(self, cache_key: str, provider_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached data by key with comprehensive error handling.
        
        Args:
            cache_key: Unique cache identifier
            provider_name: Optional provider name for provider-specific cache directory
            
        Returns:
            Cached data dictionary or None if not found/invalid
        """
        if not cache_key or not isinstance(cache_key, str):
            logger.error(f"Invalid cache key: {cache_key}")
            return None
        
        try:
            if provider_name:
                cache_dir = self.get_provider_cache_path(provider_name)
            else:
                cache_dir = self.get_cache_path("runtime")
            cache_file = cache_dir / f"{cache_key}.cache"
            
            if not cache_file.exists():
                logger.debug(f"Cache miss: {cache_key}")
                return None
            
            # Check file size and age
            file_stat = cache_file.stat()
            if file_stat.st_size == 0:
                logger.warning(f"Empty cache file: {cache_key}")
                cache_file.unlink()  # Remove corrupted file
                return None
            
            # Load cached data with additional error handling
            try:
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
            except (pickle.PickleError, EOFError) as e:
                logger.warning(f"Corrupted cache file {cache_key}: {e}")
                cache_file.unlink()  # Remove corrupted file
                return None
            except PermissionError as e:
                logger.error(f"Permission denied reading cache file {cache_key}: {e}")
                return None
            
            # Basic validation
            if not isinstance(cached_data, dict):
                logger.warning(f"Invalid cache data format for {cache_key}")
                cache_file.unlink()  # Remove invalid file
                return None
            
            logger.debug(f"Cache hit: {cache_key} ({file_stat.st_size} bytes)")
            return cached_data
            
        except Exception as e:
            logger.warning(f"Failed to load cached data for {cache_key}: {e}")
            return None
    
    async def set_cached_data(self, cache_key: str, data: Dict[str, Any], provider_name: Optional[str] = None) -> bool:
        """
        Store data in cache with given key and comprehensive error handling.
        
        Args:
            cache_key: Unique cache identifier
            data: Data to cache
            provider_name: Optional provider name for provider-specific cache directory
            
        Returns:
            True if successful, False otherwise
        """
        if not cache_key or not isinstance(cache_key, str):
            logger.error(f"Invalid cache key: {cache_key}")
            return False
        
        if not isinstance(data, dict):
            logger.error(f"Invalid data type for caching: {type(data)}")
            return False
        
        try:
            if provider_name:
                cache_dir = self.get_provider_cache_path(provider_name)
            else:
                cache_dir = self.get_cache_path("runtime")
            
            # Ensure cache directory exists with proper permissions
            try:
                cache_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError as e:
                logger.error(f"Permission denied creating cache directory {cache_dir}: {e}")
                return False
            
            cache_file = cache_dir / f"{cache_key}.cache"
            temp_file = cache_dir / f"{cache_key}.cache.tmp"
            
            # Store to temporary file first (atomic operation)
            try:
                with open(temp_file, 'wb') as f:
                    pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
                
                # Atomic move to final location
                temp_file.rename(cache_file)
                
            except (pickle.PickleError, PermissionError, OSError) as e:
                logger.error(f"Failed to serialize/write cache data for {cache_key}: {e}")
                # Clean up temporary file
                if temp_file.exists():
                    temp_file.unlink()
                return False
            
            # Verify the file was written correctly
            file_stat = cache_file.stat()
            if file_stat.st_size == 0:
                logger.error(f"Cache file written with zero size: {cache_key}")
                cache_file.unlink()
                return False
            
            logger.debug(f"Cached data: {cache_key} ({file_stat.st_size} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache data for {cache_key}: {e}")
            return False
    
    async def invalidate_cache(self, cache_pattern: Optional[str] = None, provider_name: Optional[str] = None) -> int:
        """
        Invalidate cached data based on pattern or clear all cache.
        
        Args:
            cache_pattern: Pattern to match cache keys (None = clear all)
            
        Returns:
            Number of cache files removed
        """
        try:
            if provider_name:
                cache_dir = self.get_provider_cache_path(provider_name)
            else:
                cache_dir = self.get_cache_path("runtime")
            if not cache_dir.exists():
                return 0
            
            removed_count = 0
            
            for cache_file in cache_dir.glob("*.cache"):
                if cache_pattern is None or cache_pattern in cache_file.stem:
                    try:
                        cache_file.unlink()
                        removed_count += 1
                        logger.debug(f"Removed cache file: {cache_file.name}")
                    except Exception as e:
                        logger.warning(f"Failed to remove cache file {cache_file}: {e}")
            
            logger.info(f"Cache invalidation: removed {removed_count} files")
            return removed_count
            
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")
            return 0
    
    async def get_cache_stats(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get cache statistics and health information.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            if provider_name:
                cache_dir = self.get_provider_cache_path(provider_name)
            else:
                cache_dir = self.get_cache_path("runtime")
            if not cache_dir.exists():
                return {"cache_files": 0, "total_size": 0, "cache_dir": str(cache_dir)}
            
            cache_files = list(cache_dir.glob("*.cache"))
            total_size = sum(f.stat().st_size for f in cache_files)
            
            stats = {
                "cache_files": len(cache_files),
                "total_size": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "cache_dir": str(cache_dir),
                "files": []
            }
            
            # Add details for each cache file
            for cache_file in cache_files:
                try:
                    file_stat = cache_file.stat()
                    stats["files"].append({
                        "name": cache_file.name,
                        "size": file_stat.st_size,
                        "modified": file_stat.st_mtime
                    })
                except Exception as e:
                    logger.debug(f"Failed to stat cache file {cache_file}: {e}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"error": str(e)}
    
    def get_credentials_path(self, provider: str, filename: Optional[str] = None) -> Path:
        """Get credentials file path"""
        if filename:
            return self.config.credentials_root / filename
        return self.config.credentials_root / f"{provider}.json"
    
    def get_credentials(self, provider: str) -> Dict[str, Any]:
        """Get credentials from environment variables or files using provider configuration"""
        credentials = {}
        
        # Get credential patterns from provider configuration
        asset_config = self._get_provider_asset_config(provider)
        credential_patterns = asset_config.get("credential_patterns", [])
        
        # Try environment variables from provider config
        for env_var in credential_patterns:
            value = os.getenv(env_var)
            if value:
                credentials[env_var.lower()] = value
        
        # Fallback to legacy hardcoded patterns for backward compatibility
        if not credentials:
            env_patterns = {
                "openai": ["OPENAI_API_KEY"],
                "anthropic": ["ANTHROPIC_API_KEY"],
                "elevenlabs": ["ELEVENLABS_API_KEY"],
                "google_cloud": ["GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT_ID"],
                "deepseek": ["DEEPSEEK_API_KEY"]
            }
            
            if provider in env_patterns:
                for env_var in env_patterns[provider]:
                    value = os.getenv(env_var)
                    if value:
                        credentials[env_var.lower()] = value
        
        # Try credentials file
        cred_file = self.get_credentials_path(provider)
        if cred_file.exists():
            try:
                with open(cred_file, 'r') as f:
                    file_creds = json.load(f)
                credentials.update(file_creds)
            except Exception as e:
                logger.warning(f"Failed to load credentials from {cred_file}: {e}")
        
        return credentials
    
    @staticmethod
    def _is_populated_download(path: Path) -> bool:
        """True if `path` looks like a *complete* download: a non-empty file, or a directory that
        holds at least one file. An empty directory (or empty file) is a partial/failed download — a
        cache-existence check must not treat it as a hit (rglob short-circuits on the first file)."""
        if path.is_dir():
            return any(p.is_file() for p in path.rglob("*"))
        return path.is_file() and path.stat().st_size > 0

    @staticmethod
    def _remove_partial(path: Path) -> None:
        """Best-effort recursive remove of a file or directory (clearing a partial/stale download)."""
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.exists():
            try:
                path.unlink()
            except OSError:
                pass

    async def download_model(self, provider: str, model_id: str, force: bool = False,
                             url_override: Optional[str] = None) -> Path:
        """Download model if not cached, return path.

        `url_override` replaces the class-declared model URL (a TOML per-provider `model_url`
        override, ASSET-4) while keeping the whole robust path — lock, temp+rename, partial healing.
        """
        # Get download lock to prevent concurrent downloads of same model
        lock_key = f"{provider}:{model_id}"
        if lock_key not in self._download_locks:
            self._download_locks[lock_key] = asyncio.Lock()

        async with self._download_locks[lock_key]:
            return await self._download_model_impl(provider, model_id, force, url_override)

    async def _download_model_impl(self, provider: str, model_id: str, force: bool,
                                   url_override: Optional[str] = None) -> Path:
        """Internal download implementation"""
        model_path = self.get_model_path(provider, model_id)

        # Check if already present. A *populated* path (a non-empty file, or a directory holding at
        # least one file) is a complete download; an empty/partial path — left by an extraction that
        # was interrupted or failed (a killed container, a full disk, a missing bz2 module) — must NOT
        # be trusted, or "already exists" skips it forever. Clear the partial and re-download.
        if model_path.exists() and not force:
            if self._is_populated_download(model_path):
                logger.info(f"Model already exists: {model_path}")
                return model_path
            logger.warning(f"Model path exists but is empty/partial — re-downloading: {model_path}")
            self._remove_partial(model_path)
        
        # Get model info from provider configuration (replaces model_registry)
        model_info = self.get_model_info(provider, model_id)
        if not model_info and not url_override:
            raise ValueError(f"No model configuration found for {provider}/{model_id}")

        # Extract URL from model info (a caller-supplied override wins — ASSET-4)
        model_url = url_override or model_info.get("url")

        # Generic URL validation - no provider-specific logic
        if not model_url:
            raise ValueError(f"No download URL configured for {provider}/{model_id}")
        
        # Handle special URL types generically
        if model_url == "auto":
            # Provider expects to handle download internally - return path for provider to manage
            logger.info(f"Model {provider}/{model_id} configured for auto-download by provider")
            return model_path
            
        if model_url == "local":
            # Provider expects local file - check if it exists
            logger.info(f"Model {provider}/{model_id} configured as local file: {model_path}")
            if not model_path.exists():
                raise FileNotFoundError(f"Local model not found: {model_path}")
            return model_path
            
        logger.info(f"Downloading {provider}/{model_id} from {model_url}")
        
        # Create parent directory
        model_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Download to temporary file first
        downloads_dir = self.config.cache_root / "downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        temp_path = downloads_dir / f"{provider}_{model_id}_downloading"
        
        try:
            await self._download_file(model_url, temp_path)

            # Handle extraction if needed
            if model_info.get("extract", False):
                # Extract into a staging dir and swap into place only on success, so a failed or
                # interrupted extraction never leaves a partial pack at model_path (which the
                # populated-check above would otherwise trust on the next run).
                staging = model_path.parent / f".{model_path.name}.incomplete"
                self._remove_partial(staging)
                try:
                    await self._extract_archive(temp_path, staging, model_url)
                except Exception:
                    self._remove_partial(staging)
                    raise
                self._remove_partial(model_path)   # clear any stale target
                staging.rename(model_path)         # atomic on the same filesystem
                temp_path.unlink()  # Remove downloaded archive
            else:
                # Move to final location
                temp_path.rename(model_path)

            logger.info(f"Successfully downloaded: {model_path}")
            return model_path

        except Exception as e:
            # Clean up on failure
            if temp_path.exists():
                temp_path.unlink()
            logger.error(f"Failed to download {provider}/{model_id}: {e}")
            raise
    
    async def _download_file(self, url: str, target_path: Path) -> None:
        """Download file with progress tracking"""
        try:
            import aiohttp  # type: ignore
        except ImportError:
            raise RuntimeError("aiohttp required for model downloads. Install with: pip install aiohttp")
        
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                
                with open(target_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)
    
    async def _extract_archive(self, archive_path: Path, target_dir: Path, model_url: Optional[str] = None) -> None:
        """Extract archive to target directory"""
        import zipfile
        import tarfile
        
        target_dir.mkdir(parents=True, exist_ok=True)
        
        def extract_sync():
            # Try to detect format from URL first, then from file. tar variants include .tar.bz2/.tbz2
            # and .tar.xz/.txz — Piper TTS voices (ARCH-24 T2) ship as k2-fsa `.tar.bz2`; tarfile's
            # `r:*` mode decompresses all of them transparently, so only the *dispatch* needs them.
            _tar_exts = ['.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tbz2', '.tar.xz', '.txz']
            archive_format = None
            if model_url:
                if model_url.endswith('.zip'):
                    archive_format = 'zip'
                elif any(model_url.endswith(ext) for ext in _tar_exts):
                    archive_format = 'tar'

            # Fallback to file extension — match the full name, since Path.suffix is only the LAST
            # component (`foo.tar.bz2`.suffix == '.bz2', which would miss the tar dispatch).
            if not archive_format:
                name = archive_path.name.lower()
                if name.endswith('.zip'):
                    archive_format = 'zip'
                elif any(name.endswith(ext) for ext in _tar_exts):
                    archive_format = 'tar'

            # Try to detect by reading file header if still unknown
            if not archive_format:
                try:
                    with open(archive_path, 'rb') as f:
                        header = f.read(6)
                        if header.startswith(b'PK'):  # ZIP magic
                            archive_format = 'zip'
                        elif (header.startswith(b'\x1f\x8b')        # gzip
                              or header.startswith(b'BZh')          # bzip2
                              or header.startswith(b'\xfd7zXZ\x00')):  # xz
                            archive_format = 'tar'
                except Exception:
                    pass
            
            if archive_format == 'zip':
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(target_dir)
            elif archive_format == 'tar':
                with tarfile.open(archive_path, 'r:*') as tar_ref:
                    tar_ref.extractall(target_dir)
            else:
                raise ValueError(f"Unsupported archive format: {archive_path.suffix} (URL: {model_url})")
        
        await asyncio.to_thread(extract_sync)
    
    async def download_model_pack(self, provider: str, model_id: str, force: bool = False) -> Dict[str, "Path"]:
        """Resolve a multi-file model pack to local files, downloading on first run.

        For sherpa-onnx transducer models (ARCH-10), a "model" is a set of files
        (encoder/decoder/joiner/tokens), not a single URL. The pack descriptor lives in
        the provider's ``_get_default_model_urls()`` as ``{"type": "sherpa-pack",
        "repo": "<hf-repo>", "prefer": "int8"}``; the actual filenames are discovered via
        the HuggingFace API (robust to repo layout) and int8 variants are preferred.

        Returns a dict ``{"encoder": Path, "decoder": Path, "joiner": Path, "tokens": Path}``.
        Files persist under the models root (a mounted volume in production) so the
        download happens once and is reused across container recreation.
        """
        lock_key = f"{provider}:{model_id}:pack"
        if lock_key not in self._download_locks:
            self._download_locks[lock_key] = asyncio.Lock()
        async with self._download_locks[lock_key]:
            return await self._download_model_pack_impl(provider, model_id, force)

    async def _download_model_pack_impl(self, provider: str, model_id: str, force: bool) -> Dict[str, "Path"]:
        info = self.get_model_info(provider, model_id)
        repo = info.get("repo")
        if not repo:
            raise ValueError(f"No 'repo' configured for model pack {provider}/{model_id}")
        # Member set is descriptor-driven: transducer = encoder/decoder/joiner/tokens,
        # whisper = encoder/decoder/tokens (no joiner).
        member_names = info.get("members", ["encoder", "decoder", "joiner", "tokens"])
        prefer = info.get("prefer", "int8")

        pack_dir = self.get_model_path(provider, model_id)
        members = {
            m: pack_dir / ("tokens.txt" if m == "tokens" else f"{m}.onnx")
            for m in member_names
        }

        def complete() -> bool:
            return all(p.exists() and p.stat().st_size > 0 for p in members.values())

        if not force and complete():
            return members

        siblings = await self._hf_list_repo_files(repo)
        picks = self._pick_pack_files(siblings, prefer, member_names)
        missing = [m for m in member_names if m not in picks]
        if missing:
            raise ValueError(
                f"Could not resolve pack member(s) {missing} in HF repo '{repo}' "
                f"({len(siblings)} files listed)"
            )

        pack_dir.mkdir(parents=True, exist_ok=True)
        for member, target in members.items():
            if force or not (target.exists() and target.stat().st_size > 0):
                url = f"https://huggingface.co/{repo}/resolve/main/{picks[member]}?download=true"
                logger.info(f"Downloading model-pack file {provider}/{model_id}:{member} <- {picks[member]}")
                await self._download_file(url, target)

        if not complete():
            raise RuntimeError(f"Model pack {provider}/{model_id} incomplete after download")
        return members

    async def _hf_list_repo_files(self, repo: str) -> List[str]:
        """List file names in a HuggingFace model repo via its public API."""
        try:
            import aiohttp  # type: ignore
        except ImportError:
            raise RuntimeError("aiohttp required for model downloads")
        url = f"https://huggingface.co/api/models/{repo}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
        return [s.get("rfilename", "") for s in data.get("siblings", [])]

    @staticmethod
    def _pick_pack_files(
        siblings: List[str],
        prefer: str,
        members=("encoder", "decoder", "joiner", "tokens"),
    ) -> Dict[str, str]:
        """Pick the requested pack members by keyword (.onnx, ``prefer`` variant first; tokens.txt)."""
        onnx = [f for f in siblings if f.lower().endswith(".onnx")]

        def pick(keyword: str) -> Optional[str]:
            cands = [f for f in onnx if keyword in f.lower()]
            if not cands:
                return None
            preferred = [f for f in cands if prefer in f.lower()]
            return (preferred or cands)[0]

        picks: Dict[str, str] = {}
        for member in members:
            if member == "tokens":
                tokens = next((f for f in siblings if f.lower().endswith("tokens.txt")), None)
                if tokens:
                    picks["tokens"] = tokens
            else:
                chosen = pick(member)
                if chosen:
                    picks[member] = chosen
        return picks

    def model_exists(self, provider: str, model_id: str) -> bool:
        """Check if model exists - supports both file-based and package-based models"""
        # Check if this provider uses Python packages for models
        asset_config = self._get_provider_asset_config(provider)
        uses_packages = asset_config.get("uses_python_packages", False)
        
        if uses_packages:
            return self._python_package_installed(model_id)
        
        # Default file-based check for other providers
        model_path = self.get_model_path(provider, model_id)
        return model_path.exists()
    
    def _python_package_installed(self, package_name: str) -> bool:
        """Check if a Python package is installed and importable"""
        try:
            __import__(package_name)
            return True
        except ImportError:
            return False
    
    def get_model_info(self, provider: str, model_id: str) -> Dict[str, Any]:
        """Get model information from provider configuration (replaces model_registry)"""
        try:
            # Use provider asset configuration - purely configuration-driven
            asset_config = self._get_provider_asset_config(provider)
            model_urls = asset_config.get("model_urls", {})
            
            if model_id in model_urls:
                model_config = model_urls[model_id]
                
                # Handle both simple URL strings and complex config dictionaries
                if isinstance(model_config, str):
                    # Simple URL string format
                    return {
                        "url": model_config,
                        "size": "unknown"
                    }
                elif isinstance(model_config, dict):
                    # Complex config dictionary format
                    return model_config
                else:
                    logger.warning(f"Invalid model config format for {provider}/{model_id}: {type(model_config)}")
                    return {}
            
            # No hardcoded provider checks - if no URL configured, return empty
            # Providers will handle their own fallback logic
            return {}
        except Exception as e:
            logger.debug(f"Failed to get model info for {provider}/{model_id}: {e}")
            return {}
    
    async def ensure_model_available(self, provider_name: str, model_name: str, asset_config: Dict[str, Any]) -> Optional[Path]:
        """
        Ensure model is available, downloading if necessary.
        
        This method bridges the gap between provider asset configurations
        and actual model availability, following patterns from existing
        ASR and TTS providers.
        
        Args:
            provider_name: Provider identifier (e.g., "spacy", "vosk")
            model_name: Model identifier (e.g., "ru_core_news_sm", "en_core_web_sm")
            asset_config: Provider asset configuration
            
        Returns:
            Path to available model, or None if model cannot be ensured
        """
        try:
            logger.info(f"Ensuring model availability: {provider_name}/{model_name}")
            
            # Check if model already exists
            if self.model_exists(provider_name, model_name):
                model_path = self.get_model_path(provider_name, model_name)
                logger.info(f"Model already available: {model_path}")
                return model_path
            
            # Check if this provider uses Python packages instead of file downloads
            uses_packages = asset_config.get("uses_python_packages", False)
            if uses_packages:
                # For package-based models (like SpaCy), just verify they're installed
                if self._python_package_installed(model_name):
                    logger.info(f"Package-based model verified: {model_name}")
                    # Return a symbolic path for compatibility
                    model_path = self.get_model_path(provider_name, model_name)
                    model_path.parent.mkdir(parents=True, exist_ok=True)
                    marker_file = model_path.parent / f"{model_name}.verified"
                    marker_file.touch()
                    return marker_file
                else:
                    logger.error(f"Package-based model not installed: {model_name} (install via pyproject.toml dependencies)")
                    return None
            
            # For other providers, attempt download through registry
            try:
                model_path = await self.download_model(provider_name, model_name)
                logger.info(f"Model downloaded and available: {model_path}")
                return model_path
            except Exception as e:
                logger.warning(f"Failed to download model {provider_name}/{model_name}: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to ensure model availability {provider_name}/{model_name}: {e}")
            return None
    


# Global asset manager instance (lazy-loaded)
_asset_manager: Optional[AssetManager] = None


def get_asset_manager() -> AssetManager:
    """Get global asset manager instance"""
    global _asset_manager
    if _asset_manager is None:
        _asset_manager = AssetManager.from_env()
    return _asset_manager 