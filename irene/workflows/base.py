"""Base workflow class for orchestrating assistant operations."""

import logging
from abc import abstractmethod
from typing import Dict, Any, AsyncIterator, Optional, List

from ..intents.models import AudioData, IntentResult
from ..core.interfaces.workflow import WorkflowPort
from ..core.trace_context import TraceContext

logger = logging.getLogger(__name__)




from ..intents.context_models import RequestContext, InputFormat  # ARCH-5 / ARCH-15


class Workflow(WorkflowPort):
    """Base class for all workflow implementations (implements WorkflowPort)."""
    
    def __init__(self):
        """Initialize the workflow."""
        self.name = self.__class__.__name__
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
        self.components: Dict[str, Any] = {}
        self.initialized = False
        
        # Pipeline stage configuration for conditional processing
        self._pipeline_stages = {
            "voice_trigger": True,
            "asr": True, 
            "text_processing": True,
            "nlu": True,
            "intent_execution": True,
            "tts": True
        }
    
    @classmethod 
    def get_dependencies(cls) -> Dict[str, Any]:
        """
        Define workflow dependencies (optional - workflows can override this)
        
        Returns:
            Dict containing dependency information for this workflow
        """
        return {
            "required_components": [],
            "optional_components": [],
            "required_providers": [],
            "description": "Base workflow with no dependencies"
        }

    @abstractmethod
    async def initialize(self):
        """Initialize the workflow and its components."""
        pass
    
    @abstractmethod
    async def process_audio_stream(self, audio_stream: AsyncIterator[AudioData], context: RequestContext) -> AsyncIterator[IntentResult]:
        """
        Process an audio stream through the workflow.

        Args:
            audio_stream: Async iterator of audio data
            context: Request context

        Yields:
            IntentResult objects as they are generated
        """
        # Async-generator stub (overridden by concrete workflows): the unreachable
        # `yield` types this as an async generator, matching the port and the
        # concrete overrides.
        return
        yield
    
    async def process_text_input(self, text: str, context: RequestContext,
                                 trace_context: Optional[TraceContext] = None) -> IntentResult:
        """
        Process text input through the workflow.
        
        Args:
            text: Input text to process
            context: Request context
            
        Returns:
            IntentResult from processing
        """
        # Default implementation - can be overridden
        raise NotImplementedError("Text processing not implemented for this workflow")
    
    def add_component(self, name: str, component: Any):
        """
        Add a component to the workflow.
        
        Args:
            name: Component name
            component: Component instance
        """
        self.components[name] = component
        self.logger.info(f"Added component '{name}' to workflow")
    
    def get_component(self, name: str) -> Optional[Any]:
        """
        Get a component by name.
        
        Args:
            name: Component name
            
        Returns:
            Component instance or None if not found
        """
        return self.components.get(name)
    
    def configure_pipeline_stages(self, context: RequestContext) -> Dict[str, bool]:
        """
        Configure pipeline stages based on request context.
        
        This method determines which pipeline stages should be enabled
        based on the input type and request parameters. Supports the
        unified architecture with conditional stage skipping.
        
        Args:
            context: Request context with skip flags and input type
            
        Returns:
            Dictionary mapping stage names to enabled/disabled status
        """
        stages = self._pipeline_stages.copy()

        # ARCH-15 PR-1 (D-1): the input format selects the entry stage (single source of truth;
        # `skip_wake_word`/`skip_asr` are its derived projection). Equivalent to the prior
        # skip-flag/source checks — VOICE enters at voice-trigger, AUDIO at ASR, TEXT at NLU.
        fmt = context.input_format

        # Voice trigger stage - only for full VOICE input (wake-word needed)
        if fmt is not InputFormat.VOICE:
            stages["voice_trigger"] = False

        # ASR stage - disabled for TEXT (audio formats still need ASR)
        if fmt is InputFormat.TEXT:
            stages["asr"] = False

        # TTS stage - conditional based on wants_audio preference
        if not context.wants_audio:
            stages["tts"] = False

        return stages
    
    def is_stage_enabled(self, stage_name: str, context: RequestContext) -> bool:
        """
        Check if a specific pipeline stage is enabled for this context.
        
        Args:
            stage_name: Name of the pipeline stage
            context: Request context
            
        Returns:
            True if stage is enabled, False otherwise
        """
        configured_stages = self.configure_pipeline_stages(context)
        return configured_stages.get(stage_name, False)
    
    def get_enabled_stages(self, context: RequestContext) -> List[str]:
        """
        Get list of enabled pipeline stages for this context.
        
        Args:
            context: Request context
            
        Returns:
            List of enabled stage names
        """
        configured_stages = self.configure_pipeline_stages(context)
        return [stage for stage, enabled in configured_stages.items() if enabled]
    
    async def shutdown(self):
        """Shutdown the workflow and clean up resources."""
        for name, component in self.components.items():
            if hasattr(component, 'shutdown'):
                try:
                    await component.shutdown()
                    self.logger.info(f"Shutdown component: {name}")
                except Exception as e:
                    self.logger.error(f"Error shutting down component {name}: {e}")
        
        self.initialized = False
        self.logger.info(f"Workflow {self.name} shutdown complete")
    
    async def is_healthy(self) -> bool:
        """
        Check if the workflow is healthy and ready to process requests.
        
        Returns:
            True if workflow is healthy
        """
        if not self.initialized:
            return False
        
        # Check component health
        for name, component in self.components.items():
            if hasattr(component, 'is_healthy'):
                try:
                    if not await component.is_healthy():
                        self.logger.warning(f"Component {name} is not healthy")
                        return False
                except Exception as e:
                    self.logger.error(f"Error checking health of component {name}: {e}")
                    return False
        
        return True
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get workflow capabilities.
        
        Returns:
            Dictionary describing workflow capabilities
        """
        capabilities = {
            "name": self.name,
            "initialized": self.initialized,
            "components": list(self.components.keys()),
            "supports_audio": hasattr(self, 'process_audio_stream'),
            "supports_text": hasattr(self, 'process_text_input')
        }
        
        # Add component capabilities
        component_caps = {}
        for name, component in self.components.items():
            if hasattr(component, 'get_capabilities'):
                try:
                    component_caps[name] = component.get_capabilities()
                except Exception as e:
                    component_caps[name] = {"error": str(e)}
            else:
                component_caps[name] = {"available": True}
        
        capabilities["component_capabilities"] = component_caps
        return capabilities
    

    
    def __str__(self) -> str:
        """String representation of the workflow."""
        return f"<{self.name} initialized={self.initialized} components={len(self.components)}>"
    
    # Build dependency methods (TODO #5 Phase 2)
    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        """Workflows coordinate components - minimal direct dependencies"""
        return []
        
    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        """Workflows have no system dependencies - coordinate components only"""
        return {
            "linux.ubuntu": [],
            "linux.alpine": [],
            "macos": [],
            "windows": []
        }
