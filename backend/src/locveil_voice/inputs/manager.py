"""
Input-layer orchestrator (InputManager).

Separated from the input PORT (`InputPort`, ARCH-11/S1 now in `core/interfaces/input.py`) so the port no
longer imports its own concrete adapters — breaking the inputs.base ⇄ {cli,microphone,web} cycle (SCC-2)
with explicit composition-point wiring, NOT a runtime service-locator (cf. QUAL-24). This module is the
input layer's composition point: it legitimately depends outward on the concrete adapters it orchestrates.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from ..core.interfaces.input import InputPort, InputData
from .base import ComponentNotAvailable
from ..core.metadata import SUPPORTED_PLATFORMS
from .cli import CLIInput
from .microphone import MicrophoneInput
from .web import WebInput

logger = logging.getLogger(__name__)


class InputManager:
    """
    Manages multiple input sources and coordinates input collection.
    
    Features:
    - Multiple input source support
    - Automatic source discovery based on configuration
    - Non-blocking input collection
    - Graceful component handling
    - V14 input configuration integration
    """
    
    def __init__(self, component_manager, input_config=None):
        self.component_manager = component_manager
        self.input_config = input_config
        self._sources: dict[str, InputPort] = {}
        self._active_sources: list[str] = []
        self._shutdown_event = asyncio.Event()
        
    async def initialize(self) -> None:
        """Initialize the input manager"""
        self._running = True
        
        # Try to load available input sources
        await self._discover_input_sources()
        
        logger.info("InputManager initialized")
        
    async def _discover_input_sources(self) -> None:
        """Discover available input sources based on V14 configuration"""
        try:
            # Add CLI input if enabled in configuration
            if self.input_config is None or self.input_config.cli:
                cli_input = CLIInput()
                if self.input_config and self.input_config.cli_config:
                    await cli_input.configure_input(**self.input_config.cli_config.model_dump())
                await self.add_source("cli", cli_input)
                logger.info("Added CLI input source")
            
            # Add microphone input if enabled in configuration
            if self.input_config is None or self.input_config.microphone:
                try:
                    mic_input = MicrophoneInput()
                    if await mic_input.is_available():
                        # Apply microphone configuration
                        if self.input_config and self.input_config.microphone_config:
                            mic_config = self.input_config.microphone_config
                            await mic_input.configure_input(
                                device_id=mic_config.device_id,
                                samplerate=mic_config.sample_rate,
                                blocksize=mic_config.chunk_size,
                                buffer_queue_size=getattr(mic_config, 'buffer_queue_size', 50)
                            )
                        
                        # Initialize microphone with the configured settings
                        await mic_input.initialize()
                        
                        await self.add_source("microphone", mic_input)
                        logger.info("Added microphone input source with V14 configuration")
                    else:
                        logger.info("Microphone hardware not available")
                except (ImportError, ComponentNotAvailable) as e:
                    logger.info(f"Microphone input not available: {e}")
                    
            # Add web input if enabled in configuration
            if self.input_config is None or self.input_config.web:
                try:
                    web_input = WebInput()
                    if await web_input.is_available():
                        if self.input_config and self.input_config.web_config:
                            await web_input.configure_input(**self.input_config.web_config.model_dump())
                        await self.add_source("web", web_input)
                        logger.info("Added web input source")
                except (ImportError, ComponentNotAvailable) as e:
                    logger.info(f"Web input not available: {e}")
                    
        except Exception as e:
            logger.error(f"Error discovering input sources: {e}")
        
        # Auto-start input sources based on configuration and deployment context
        await self._auto_start_configured_sources()
    
    async def _auto_start_configured_sources(self) -> None:
        """Automatically start input sources based on configuration and deployment context"""
        try:
            # Determine which sources should auto-start based on configuration
            sources_to_start = []
            
            # Start microphone if it's the default input or explicitly enabled
            if (self.input_config and 
                (self.input_config.default_input == "microphone" or 
                 self.input_config.microphone) and 
                "microphone" in self._sources):
                sources_to_start.append("microphone")
            
            # Start CLI if it's the default input or enabled (ARCH-15 PR-5b — the PR-0 stopgap is
            # removed). The interactive runner no longer runs its own prompt_toolkit reader; it
            # CONSUMES this single source's listen() stream. So there is exactly one reader
            # (CLIInput._input_loop) and one consumer — the PR-0 double-reader can no longer occur.
            if (self.input_config and
                (self.input_config.default_input == "cli" or
                 self.input_config.cli) and
                "cli" in self._sources):
                sources_to_start.append("cli")

            # Note: Web input is typically started explicitly by WebAPIRunner
            # so we don't auto-start it here to avoid conflicts
            
            # Start the identified sources
            for source_name in sources_to_start:
                success = await self.start_source(source_name)
                if success:
                    logger.info(f"Auto-started input source: {source_name}")
                else:
                    logger.warning(f"Failed to auto-start input source: {source_name}")
                    
        except Exception as e:
            logger.error(f"Error auto-starting input sources: {e}")
    
    async def add_source(self, name: str, source: InputPort) -> None:
        """Add an input source"""
        if not await source.is_available():
            logger.warning(f"Input source '{name}' is not available")
            return
            
        self._sources[name] = source
        logger.info(f"Added input source: {name} ({source.get_input_type()})")
        
    async def start_source(self, name: str) -> bool:
        """Start a specific input source"""
        if name not in self._sources:
            logger.warning(f"Input source '{name}' not found")
            return False
            
        try:
            source = self._sources[name]
            await source.start_listening()

            if name not in self._active_sources:
                self._active_sources.append(name)

            # NOTE (BUG-25): the manager does NOT consume the source's listen() stream. It used
            # to spawn a per-source consumer feeding an internal queue that nothing drained
            # (dataflow review P0-8) — a second consumer racing the real one, so every other
            # interactive CLI command was swallowed. The manager owns source LIFECYCLE only;
            # whoever needs the data consumes listen() itself (the CLI REPL loop, the workflow).

            logger.info(f"Started input source: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start input source '{name}': {e}")
            return False
            
    async def stop_source(self, name: str) -> bool:
        """Stop a specific input source"""
        if name not in self._active_sources:
            return False
            
        try:
            source = self._sources[name]
            await source.stop_listening()

            self._active_sources.remove(name)
            logger.info(f"Stopped input source: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop input source '{name}': {e}")
            return False
            
    async def start_all_sources(self) -> None:
        """Start all available input sources"""
        for name in list(self._sources.keys()):
            await self.start_source(name)
            
    async def get_available_sources(self) -> List[str]:
        """Get list of available input source names"""
        return [name for name, source in self._sources.items() if await source.is_available()]
        
    def get_active_sources(self) -> List[str]:
        """Get list of active input source names"""
        return self._active_sources.copy()
        
    async def get_source_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific input source"""
        if name not in self._sources:
            return None

        source = self._sources[name]
        return {
            "name": name,
            "type": source.get_input_type(),
            "available": await source.is_available(),
            "listening": source.is_listening(),
            "settings": source.get_settings()
        }
        
    async def close(self) -> None:
        """Close all input sources"""
        self._running = False
        
        # Stop all sources
        for name in list(self._active_sources):
            await self.stop_source(name)
            
        logger.info("InputManager closed")
        
    @property
    def active_source_count(self) -> int:
        """Get number of active input sources"""
        return len(self._active_sources)
        
    @property
    def available_source_count(self) -> int:
        """Get number of available input sources"""
        return len([s for s in self._sources.values() if s is not None])
    
    # Build dependency methods (TODO #5 Phase 2)
    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        """Input sources provide user interface - minimal dependencies"""
        return []
        
    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        """Input sources have no system dependencies - interface logic only"""
        return {
            "linux.ubuntu": [],
            "linux.alpine": [],
            "macos": [],
            "windows": []
        }
        
    @classmethod
    def get_platform_support(cls) -> List[str]:
        """Input sources support all platforms"""
        return list(SUPPORTED_PLATFORMS)
