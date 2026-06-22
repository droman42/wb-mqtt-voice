"""Base component class for fundamental voice assistant components."""

import asyncio
import importlib.util
import logging
from abc import abstractmethod
from typing import Dict, Any, List, Optional, Type

from pydantic import BaseModel
from ..core.interfaces.component import ComponentPort
from ..core.metrics import get_metrics_collector
from ..config.models import CoreConfig

logger = logging.getLogger(__name__)


class MetricsPushMixin:
    """Periodic push of runtime metrics to the unified collector.

    Shared by components that expose ``get_runtime_metrics()`` and maintain a
    ``self._metrics_push_task`` / ``self._metrics_push_interval`` pair. Extracted
    verbatim from the previously duplicated ASR/voice-trigger implementations.

    The three label attributes below are kept distinct (rather than derived from
    one another) so the emitted log lines and the collector key stay byte-for-byte
    identical to the original per-component code, including the original casing.
    Subclasses must set them. Logging deliberately resolves the subclass module
    logger (``self.__module__``) so log records keep their original logger name.
    """

    # Per-component identifiers (set by each subclass):
    _metrics_component_key: str   # collector key, e.g. "asr" / "voice_trigger"
    _metrics_task_label: str      # start/stop logs, e.g. "ASR component" / "Voice trigger component"
    _metrics_loop_label: str      # push/error logs, e.g. "ASR" / "voice trigger"
    _metrics_push_interval: float  # seconds between pushes (set by each subclass)
    _metrics_push_task: Optional[asyncio.Task]  # set by each subclass __init__

    def get_runtime_metrics(self) -> Dict[str, Any]:
        """Provided by the component subclass; the push loop reports its values."""
        raise NotImplementedError

    def _start_metrics_push_task(self) -> None:
        """Start the periodic metrics push task"""
        if self._metrics_push_task is None:
            self._metrics_push_task = asyncio.create_task(self._metrics_push_loop())
            logging.getLogger(self.__module__).debug(
                f"{self._metrics_task_label} metrics push task started"
            )

    async def _stop_metrics_push_task(self) -> None:
        """Stop the periodic metrics push task"""
        if self._metrics_push_task:
            self._metrics_push_task.cancel()
            try:
                await self._metrics_push_task
            except asyncio.CancelledError:
                pass
            self._metrics_push_task = None
            logging.getLogger(self.__module__).debug(
                f"{self._metrics_task_label} metrics push task stopped"
            )

    async def _metrics_push_loop(self) -> None:
        """Periodic loop to push runtime metrics to unified collector"""
        log = logging.getLogger(self.__module__)
        while True:
            try:
                # Get current runtime metrics
                runtime_metrics = self.get_runtime_metrics()

                # Push to unified metrics collector
                metrics_collector = get_metrics_collector()
                metrics_collector.record_component_metrics(self._metrics_component_key, runtime_metrics)

                log.debug(f"Pushed {self._metrics_loop_label} metrics to unified collector: {len(runtime_metrics)} metrics")

                # Wait for next push cycle
                await asyncio.sleep(self._metrics_push_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error in {self._metrics_loop_label} metrics push loop: {e}")
                await asyncio.sleep(10)  # Brief pause before retrying


class Component(ComponentPort):
    """Base class for all fundamental components (implements ComponentPort)."""
    
    def __init__(self):
        """Initialize the component."""
        # `name` is a read-only @property on every concrete component (and on the
        # ComponentPort it implements), so there is nothing to assign here.
        # Use property-compatible name access for logging.
        component_name = getattr(self, 'name', self.__class__.__name__)
        self.logger = logging.getLogger(f"{__name__}.{component_name}")
        self.providers: Dict[str, Any] = {}
        self.default_provider: Optional[str] = None
        self.initialized = False
        self.injected_dependencies: Dict[str, Any] = {}  # For dependency injection
    

    @abstractmethod
    def get_providers_info(self) -> str:
        """
        Get human-readable information about available providers.
        
        Returns:
            Formatted string with provider information for user display
        """
        pass
    
    @classmethod
    @abstractmethod
    def get_config_class(cls) -> Type[BaseModel]:
        """Return the Pydantic config model for this component"""
        pass
    
    @classmethod  
    @abstractmethod
    def get_config_path(cls) -> str:
        """Return the TOML path to this component's config"""
        pass
    
    def get_config(self, core_config: CoreConfig) -> Optional[BaseModel]:
        """Get this component's configuration instance"""
        config_class = self.get_config_class()
        config_path = self.get_config_path()
        # TODO: This will be implemented in Phase 2 - Config Path Resolution System
        from ..config.resolver import extract_config_by_path
        return extract_config_by_path(core_config, config_path, config_class)
    
    def is_api_available(self) -> bool:
        """Check if web API dependencies (FastAPI + Pydantic) are available.

        Hoisted from the previously duplicated, byte-identical copies in the
        NLU / text-processor / monitoring components. This overrides the
        FastAPI-only ``WebAPIPlugin.is_api_available`` for every component (all of
        which list ``Component`` ahead of ``WebAPIPlugin`` in their bases). Pydantic
        is a hard base dependency (imported unconditionally at the top of this
        module), so the added pydantic check is always satisfied when this code
        runs and the result is identical to the inherited FastAPI-only check.
        """
        return (
            importlib.util.find_spec("fastapi") is not None
            and importlib.util.find_spec("pydantic") is not None
        )

    def inject_dependency(self, name: str, dependency: Any) -> None:
        """Inject a dependency into this component"""
        self.injected_dependencies[name] = dependency
        
    def get_dependency(self, name: str) -> Optional[Any]:
        """Get an injected dependency"""
        return self.injected_dependencies.get(name)
    
    def is_enabled(self, core_config: CoreConfig) -> bool:
        """Check if this component is enabled via its config"""
        config = self.get_config(core_config)
        if config is None:
            return False
        return getattr(config, 'enabled', True)
    
    @classmethod
    def is_enabled_in_config(cls, core_config: CoreConfig) -> bool:
        """Class method to check if component is enabled without instantiation"""
        try:
            config_class = cls.get_config_class()
            config_path = cls.get_config_path()
            # TODO: This will be implemented in Phase 2 - Config Path Resolution System
            from ..config.resolver import extract_config_by_path
            config = extract_config_by_path(core_config, config_path, config_class)
            if config is None:
                return False
            return getattr(config, 'enabled', True)
        except Exception:
            return False
    
    def parse_provider_name_from_text(self, text: str) -> Optional[str]:
        """
        Extract provider name from user text/voice command.
        
        Args:
            text: User input text (voice command, API request, etc.)
            
        Returns:
            Provider name if found, None otherwise
            
        Note: Default implementation provides basic keyword matching.
              Components can override for component-specific aliases.
        """
        text_lower = text.lower()
        
        # Try direct provider name match
        for provider_name in self.providers.keys():
            if provider_name.lower() in text_lower:
                return provider_name
        
        return None
    
    def switch_provider(self, provider_name: str) -> bool:
        """
        Switch to a different provider (alias for set_default_provider).
        
        Args:
            provider_name: Name of provider to switch to
            
        Returns:
            True if switch successful, False otherwise
        """
        return self.set_default_provider(provider_name)
    
    def get_provider_capabilities(self) -> Dict[str, Any]:
        """
        Get capabilities of all providers.
        
        Returns:
            Dictionary mapping provider names to their capabilities
        """
        capabilities = {}
        for name, provider in self.providers.items():
            if hasattr(provider, 'get_capabilities'):
                try:
                    capabilities[name] = provider.get_capabilities()
                except Exception as e:
                    capabilities[name] = {"error": str(e)}
            else:
                capabilities[name] = {"available": True}
        
        return capabilities
    
    def list_available_providers(self) -> List[str]:
        """Get list of available provider names."""
        return list(self.providers.keys())
    
    def is_provider_available(self, provider_name: str) -> bool:
        """Check if a specific provider is available."""
        return provider_name in self.providers

    def _apply_provider_config(self, config_dict: dict) -> None:
        """Apply a `/configure` request's `default_provider`: switch to it when it names a loaded
        provider, else warn and keep the current default. Shared by the provider components' configure
        endpoints (CR-C8) — the single source of the "is this provider loaded?" gate."""
        requested = config_dict.get("default_provider")
        if requested:
            if requested in self.providers:
                self.default_provider = requested
            else:
                self.logger.warning(f"{self.name}: provider '{requested}' not available")

    async def initialize(self, core):
        """Initialize the component and its providers.

        `core` is required — the composition root always passes it; the prior
        `core=None` default made overrides' `core.config` accesses infer `None`
        (QUAL-4d/4b). Overrides may still widen it back to `core=None` if they guard.
        """
        self.logger.info(f"Initializing component: {self.name}")
        self.initialized = True
    
    async def shutdown(self):
        """Shutdown the component and clean up resources."""
        for name, provider in self.providers.items():
            if hasattr(provider, 'shutdown'):
                try:
                    await provider.shutdown()
                    self.logger.info(f"Shutdown provider: {name}")
                except Exception as e:
                    self.logger.error(f"Error shutting down provider {name}: {e}")
        
        self.initialized = False
        self.logger.info(f"Component {self.name} shutdown complete")
    
    def add_provider(self, name: str, provider: Any):
        """
        Add a provider to this component.
        
        Args:
            name: Provider name
            provider: Provider instance
        """
        self.providers[name] = provider
        if self.default_provider is None:
            self.default_provider = name
        self.logger.info(f"Added provider '{name}' to component {self.name}")
    
    def set_default_provider(self, provider_name: str) -> bool:
        """
        Set the default provider for this component.

        Args:
            provider_name: Provider name to set as default

        Returns:
            True if provider was set successfully, False otherwise
        """
        if provider_name in self.providers:
            self.default_provider = provider_name
            self.logger.info(f"Set default provider for {self.name}: {provider_name}")
            return True
        else:
            self.logger.warning(f"Provider '{provider_name}' not found in component {self.name}")
            return False
    
    def get_current_provider(self) -> Optional[Any]:
        """
        Get the current default provider.
        
        Returns:
            Current provider instance or None
        """
        if self.default_provider and self.default_provider in self.providers:
            return self.providers[self.default_provider]
        elif self.providers:
            # Return first available provider
            return next(iter(self.providers.values()))
        return None
    
    async def is_available(self) -> bool:
        """
        Check if the component is available and functioning.
        
        Returns:
            True if component is available
        """
        if not self.initialized:
            return False
        
        provider = self.get_current_provider()
        if provider and hasattr(provider, 'is_available'):
            try:
                return await provider.is_available()
            except Exception:
                return False
        
        return provider is not None
    
    async def is_healthy(self) -> bool:
        """
        Check if the component is healthy and ready for use.
        
        Returns:
            True if component is healthy
        """
        return await self.is_available()
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get component capabilities and provider information.
        
        Returns:
            Dictionary describing component capabilities
        """
        capabilities = {
            "name": self.name,
            "initialized": self.initialized,
            "providers": list(self.providers.keys()),
            "default_provider": self.default_provider,
            "dependencies": self.get_component_dependencies()
        }
        
        # Add provider capabilities
        provider_caps = {}
        for name, provider in self.providers.items():
            if hasattr(provider, 'get_capabilities'):
                try:
                    provider_caps[name] = provider.get_capabilities()
                except Exception as e:
                    provider_caps[name] = {"error": str(e)}
            else:
                provider_caps[name] = {"available": True}
        
        capabilities["provider_capabilities"] = provider_caps
        return capabilities
    
    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about available providers.
        
        Returns:
            Dictionary with provider information
        """
        info = {}
        for name, provider in self.providers.items():
            provider_info = {
                "name": name,
                "class": provider.__class__.__name__,
                "is_default": name == self.default_provider
            }
            
            if hasattr(provider, 'get_info'):
                try:
                    provider_info.update(provider.get_info())
                except Exception as e:
                    provider_info["error"] = str(e)
            
            info[name] = provider_info
        
        return info
    
    def configure_provider(self, provider_name: str, config: Dict[str, Any]):
        """
        Configure a specific provider.
        
        Args:
            provider_name: Name of provider to configure
            config: Configuration dictionary
        """
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not found")
        
        provider = self.providers[provider_name]
        if hasattr(provider, 'configure'):
            provider.configure(config)
            self.logger.info(f"Configured provider {provider_name}")
        else:
            self.logger.warning(f"Provider {provider_name} does not support configuration")
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get current component status.

        Returns:
            Dictionary with component status information
        """
        return {
            "name": self.name,
            "initialized": self.initialized,
            "provider_count": len(self.providers),
            "default_provider": self.default_provider,
            "providers": list(self.providers.keys())
        }
    
    # Build dependency methods - ComponentManager integration
    @classmethod
    @abstractmethod
    def get_python_dependencies(cls) -> List[str]:
        """Return list of required Python modules"""
        pass
        
    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        """Components have no system dependencies - coordinate providers only"""
        return {
            "linux.ubuntu": [],
            "linux.alpine": [],
            "macos": [],
            "windows": []
        }
    def get_component_dependencies(self) -> list[str]:
        """Return list of required component dependencies"""
        return []  # Default: no dependencies

    def get_service_dependencies(self) -> Dict[str, type]:
        """Return dict of required service dependencies {name: expected_type}"""
        return {}  # Default: no service dependencies
    
    async def stop(self) -> None:
        """Stop the component with cleanup (used by ComponentManager)"""
        if not self.initialized:
            return
            
        try:
            await self.shutdown()
            self.initialized = False
            self.logger.info(f"Component {self.name} stopped successfully")
        except Exception as e:
            self.logger.error(f"Error stopping component {self.name}: {e}") 