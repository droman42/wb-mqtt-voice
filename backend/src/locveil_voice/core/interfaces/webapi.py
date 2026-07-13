"""
Web API Plugin Interface - For plugins that provide web endpoints

Defines the interface for plugins that expose functionality via REST APIs
using FastAPI routers.
"""

import importlib.util
import logging
from typing import Optional, Any, List, Tuple
from abc import abstractmethod

from ..metadata import EntryPointMetadata

logger = logging.getLogger(__name__)


class WebAPIPlugin(EntryPointMetadata):
    """
    Interface for plugins that provide web API endpoints.
    
    WebAPI plugins extend functionality by exposing REST endpoints
    that can be integrated into the main FastAPI application.
    """

    # The plugin's identifier, used here to derive the default API prefix/tags.
    # Read-only property supplied by the implementation (always mixed in
    # alongside Component, whose concrete subclasses expose it as a property).
    @property
    def name(self) -> str: ...

    @abstractmethod
    def get_router(self) -> Optional[Any]:
        """
        Get FastAPI router with plugin endpoints.
        
        Returns:
            APIRouter instance with endpoints, or None if not available
        """
        pass
        
    def get_api_prefix(self) -> str:
        """
        Get URL prefix for this plugin's API endpoints.
        
        Returns:
            URL prefix (e.g., '/tts', '/audio', '/timer')
        """
        return f"/{self.name}"
        
    def get_api_tags(self) -> list[str]:
        """
        Get OpenAPI tags for this plugin's endpoints.
        
        Returns:
            List of tags for API documentation grouping
        """
        return [self.name]
        
    def requires_authentication(self) -> bool:
        """
        Whether this plugin's endpoints require authentication.
        
        Returns:
            True if authentication is required
        """
        return False
        
    def is_api_available(self) -> bool:
        """
        Check if web API functionality is available.
        
        Returns:
            True if FastAPI dependencies are available
        """
        return importlib.util.find_spec("fastapi") is not None

    def get_openapi_schema(self) -> Optional[dict]:
        """
        Get custom OpenAPI schema additions for this plugin.
        
        Returns:
            OpenAPI schema dict or None for auto-generation
        """
        return None
        

def web_api_components(core: Any) -> List[Tuple[str, "WebAPIPlugin"]]:
    """Return ``(name, component)`` for every component implementing :class:`WebAPIPlugin`.

    Single source of the "iterate the component manager, filter ``WebAPIPlugin``" walk used by router
    mounting and OpenAPI spec generation. Degrades gracefully — returns ``[]`` (logging a
    warning) when there is no component manager or the lookup fails, so callers never crash on it.
    """
    cm = getattr(core, "component_manager", None) if core else None
    if cm is None:
        logger.warning("Core does not have component_manager")
        return []
    try:
        available = cm.get_components()
    except Exception as e:
        logger.warning(f"Could not get components from component manager: {e}")
        return []
    return [(name, c) for name, c in available.items() if isinstance(c, WebAPIPlugin)]