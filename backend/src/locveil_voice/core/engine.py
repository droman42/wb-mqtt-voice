"""
AsyncVACore - The main async voice assistant engine

This is the heart of Irene v15, providing non-blocking command processing
with optional audio/TTS components.
"""

import logging
from typing import Optional, Any
from pathlib import Path

from ..config.models import CoreConfig
from ..intents.context import ContextManager
from .components import ComponentManager
from .workflow_manager import WorkflowManager
from .metrics import MetricsCollector
from .catalog_service import CatalogService
from .durable_actions import get_durable_action_store, reconcile_durable_actions
from .notifications import get_notification_service

# NOTE (ARCH-11 / S3): the delivery-layer InputManager (inputs) is intentionally
# NOT imported here — `core` must not depend outward. It is constructed by the
# composition root (`irene/runners/composition.build_core`) and injected; typed
# `Any` to keep the edge out of `core`. (The legacy plugin manager was retired in
# ARCH-13.)

logger = logging.getLogger(__name__)

# QUAL-24: the global-core service-locator (`get_core`/`set_core`/`_global_core`)
# was removed once the intent handlers stopped reaching into core for components
# (they now depend on domain-owned ports injected by the application). Components
# receive what they need via DI; nothing reads a global core.


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
        output_manager: Any = None,
        event_bus: Any = None,
        context_manager: ContextManager,
        metrics_collector: MetricsCollector,
        workflow_manager: WorkflowManager,
        catalog_service: Optional[CatalogService] = None,
        config_path: Optional[Path] = None,
    ):
        """ARCH-11 / S3: managers are built by the composition root and injected.

        Use `locveil_voice.runners.composition.build_core(config, config_path)` to
        construct a fully-wired core; do not construct managers here.
        """
        self.config = config
        self.config_path = config_path  # Store config path for component access
        self.component_manager = component_manager
        self.input_manager = input_manager
        self.output_manager = output_manager  # ARCH-15 PR-5: delivery layer (typed Any; core keeps no edge to locveil_voice.outputs)
        self.event_bus = event_bus            # ARCH-15 PR-6: process-wide pipeline event bus
        self.context_manager = context_manager
        self.metrics_collector = metrics_collector
        self.workflow_manager = workflow_manager
        # ARCH-8 PR-2: the application-layer device-catalog holder (implements the domain's
        # DeviceCatalogPort). The composition wires its fetcher when the bridge output is enabled.
        self.catalog_service = catalog_service if catalog_service is not None else CatalogService()
        self.audio_negotiator = None  # ARCH-18: shared audio negotiator (built at startup, see start())
        self._running = False

    def _build_audio_negotiator(self):
        """Build the shared audio negotiator from config + the active wake/asr providers (ARCH-18). The VAD
        contract is fixed 16 kHz, so `vad_provider=None` (from_pipeline falls back to it)."""
        from .audio_negotiator import AudioNegotiator

        def _active(name: str):
            comp = self.component_manager.get_component(name)
            providers = getattr(comp, "providers", None) or {}
            return providers.get(getattr(comp, "default_provider", None)) if comp else None

        return AudioNegotiator.from_pipeline(self.config, wake_provider=_active("voice_trigger"),
                                             asr_provider=_active("asr"), audio_provider=_active("audio"))

    async def start(self) -> None:
        """Initialize and start the assistant"""
        logger.info("Starting Irene Voice Assistant v15...")

        try:
            # Initialize components first - PASS CORE REFERENCE
            await self.component_manager.initialize_components(self)

            # ARCH-18: build the SHARED audio negotiator once components/providers are ready — used by the
            # workflow for the mic/web boundary AND by the ASR /transcribe endpoint. Fatal here if no
            # canonical format satisfies the capture + every audio consumer (loud, at startup).
            self.audio_negotiator = self._build_audio_negotiator()
            self.component_manager.audio_negotiator = self.audio_negotiator  # for workflow injection

            # Make context_manager available to component_manager for workflow injection
            self.component_manager.context_manager = self.context_manager
            
            await self.context_manager.start()

            # Initialize workflow manager with components
            await self.workflow_manager.initialize()

            # Initialize metrics collector (Phase 2: unified analytics)
            logger.info("Metrics collector initialized for unified analytics")

            # ARCH-28 (D-3): reconcile persisted durable actions — re-arm future deadlines,
            # fire recently-missed ones with an apology, announce older ones as expired.
            # After components (handlers + notification service) are up, BEFORE inputs
            # accept traffic. Never blocks startup.
            await self._reconcile_durable_actions()

            await self.input_manager.initialize()
            
            self._running = True
            profile = self.component_manager.get_deployment_profile()
            logger.info(f"Irene started successfully in {profile} mode")
            
        except Exception as e:
            logger.error(f"Failed to start Irene: {e}")
            await self.stop()
            raise
            

            


        
    async def _reconcile_durable_actions(self) -> None:
        """ARCH-28: recover persisted durable actions at startup (best-effort, never fatal)."""
        try:
            handlers_by_class = {}
            intent_component = self.component_manager.get_component('intent_system')
            handler_manager = getattr(intent_component, 'handler_manager', None)
            if handler_manager is not None:
                handlers_by_class = {h.__class__.__name__: h
                                     for h in handler_manager.get_handlers().values()}
            service = await get_notification_service()
            await reconcile_durable_actions(get_durable_action_store(), handlers_by_class, service)
        except Exception as e:
            logger.error(f"Durable-action reconciliation failed (continuing startup): {e}")

    async def stop(self) -> None:
        """Graceful shutdown"""
        logger.info("Stopping Irene Voice Assistant...")
        
        self._running = False

        try:
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