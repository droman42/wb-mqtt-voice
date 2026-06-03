"""
AsyncVACore - The main async voice assistant engine

This is the heart of Irene v13, providing non-blocking command processing
with optional audio/TTS components.
"""

import asyncio
import logging
from typing import Optional, Any
from dataclasses import dataclass
from pathlib import Path

from ..config.models import CoreConfig
from ..intents.context import ContextManager
from .timers import AsyncTimerManager
from .components import ComponentManager
from .workflow_manager import WorkflowManager
from .metrics import MetricsCollector

# NOTE (ARCH-11 / S3): the delivery-layer InputManager (inputs) is intentionally
# NOT imported here — `core` must not depend outward. It is constructed by the
# composition root (`irene/runners/composition.build_core`) and injected; typed
# `Any` to keep the edge out of `core`. (The legacy plugin manager was retired in
# ARCH-13.)

logger = logging.getLogger(__name__)

# Global core instance for component access by handlers
_global_core: Optional['AsyncVACore'] = None


def get_core() -> Optional['AsyncVACore']:
    """Get the global AsyncVACore instance for component access"""
    return _global_core


def set_core(core: 'AsyncVACore') -> None:
    """Set the global AsyncVACore instance"""
    global _global_core
    _global_core = core


class AsyncVACore:
    """
    Modern async voice assistant core engine.
    
    Features:
    - Non-blocking command processing
    - Optional audio/TTS components
    - Plugin system with dependency injection
    - Concurrent request handling
    """
    
    def __init__(
        self,
        config: CoreConfig,
        *,
        component_manager: ComponentManager,
        input_manager: Any,
        context_manager: ContextManager,
        timer_manager: AsyncTimerManager,
        metrics_collector: MetricsCollector,
        workflow_manager: WorkflowManager,
        config_path: Optional[Path] = None,
    ):
        """ARCH-11 / S3: managers are built by the composition root and injected.

        Use `irene.runners.composition.build_core(config, config_path)` to
        construct a fully-wired core; do not construct managers here.
        """
        self.config = config
        self.config_path = config_path  # Store config path for component access
        self.component_manager = component_manager
        self.input_manager = input_manager
        self.context_manager = context_manager
        self.timer_manager = timer_manager
        self.metrics_collector = metrics_collector
        self.workflow_manager = workflow_manager
        self._running = False
        
    async def start(self) -> None:
        """Initialize and start the assistant"""
        logger.info("Starting Irene Voice Assistant v13...")
        
        # Set this instance as the global core for component access
        set_core(self)
        
        try:
            # Initialize components first - PASS CORE REFERENCE
            await self.component_manager.initialize_components(self)
            
            # Make context_manager available to component_manager for workflow injection
            self.component_manager.context_manager = self.context_manager
            
            await self.context_manager.start()
            await self.timer_manager.start()

            # Initialize workflow manager with components
            await self.workflow_manager.initialize()

            # Initialize metrics collector (Phase 2: unified analytics)
            logger.info("Metrics collector initialized for unified analytics")

            await self.input_manager.initialize()
            
            self._running = True
            profile = self.component_manager.get_deployment_profile()
            logger.info(f"Irene started successfully in {profile} mode")
            
        except Exception as e:
            logger.error(f"Failed to start Irene: {e}")
            await self.stop()
            raise
            

            


        
    async def stop(self) -> None:
        """Graceful shutdown"""
        logger.info("Stopping Irene Voice Assistant...")
        
        self._running = False
        
        # Clear global core instance
        set_core(None)
        
        try:
            await self.timer_manager.stop()
            await self.context_manager.stop()
            await self.workflow_manager.cleanup()
            await self.input_manager.close()
            await self.component_manager.shutdown_all()
            
            logger.info("Irene stopped successfully")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            
    @property
    def is_running(self) -> bool:
        """Check if the core engine is running"""
        return self._running 