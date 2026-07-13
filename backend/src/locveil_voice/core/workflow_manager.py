"""
Workflow Manager - Coordinates workflows with input sources

This manager handles the coordination between input sources and workflows,
supporting both voice assistant mode (with wake words) and continuous mode.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, AsyncIterator, List, Union
from enum import Enum

from .trace_context import (
    TraceContext, trace_scope, make_trace, save_trace, resolve_traces_dir, replay_request,
)
from .interfaces.workflow import WorkflowPort
from ..intents.context_models import RequestContext, InputFormat
from .event_bus import EventType, PipelineEvent
from ..utils.audio_data import AudioData
from ..intents.models import IntentResult
from .interfaces.input import InputPort
from ..utils.loader import dynamic_loader

logger = logging.getLogger(__name__)


class WorkflowMode(Enum):
    """Available processing modes for unified workflow"""
    UNIFIED = "unified"  # Single unified workflow handles all input types


class WorkflowState(Enum):
    """Available states for workflow lifecycle"""
    INITIALIZING = "initializing"
    WARMING_UP = "warming_up"  
    READY = "ready"
    ERROR = "error"


class WorkflowManager:
    """
    Manages workflow execution and input coordination.
    
    Provides the interface for processing text and audio input
    through the unified workflow with conditional pipeline stages.
    """
    
    def __init__(self, component_manager, config, event_bus=None):
        self.component_manager = component_manager
        self.config = config
        self.event_bus = event_bus  # ARCH-15 PR-6: process-wide pipeline event bus (optional)
        self.workflows: Dict[str, WorkflowPort] = {}
        self.workflow_states: Dict[str, WorkflowState] = {}
        self.active_workflow: Optional[WorkflowPort] = None
        self.active_mode: Optional[WorkflowMode] = None
        self.input_manager = None
        self._workflow_task: Optional[asyncio.Task] = None
        self._progress_monitor_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Cache for discovered workflows
        self._available_workflows: Optional[Dict[str, type]] = None

    def discover_workflows(self) -> Dict[str, type]:
        """
        Discover available workflow classes via entry-points
        
        Returns:
            Dictionary mapping workflow names to their classes
        """
        if self._available_workflows is None:
            try:
                self._available_workflows = dynamic_loader.discover_providers("locveil_voice.workflows")
                
                if not self._available_workflows:
                    logger.warning("No workflows discovered via entry-points. This may indicate a configuration issue.")
                else:
                    logger.info(f"Discovered {len(self._available_workflows)} workflows: {list(self._available_workflows.keys())}")
                    
            except Exception as e:
                logger.error(f"Failed to discover workflows via entry-points: {e}")
                self._available_workflows = {}
        
        return self._available_workflows

    def get_workflow_class(self, workflow_name: str) -> Optional[type]:
        """
        Get a specific workflow class by name
        
        Args:
            workflow_name: Name of the workflow to get
            
        Returns:
            Workflow class or None if not found
        """
        try:
            workflows = self.discover_workflows()
            workflow_class = workflows.get(workflow_name)
            
            if workflow_class is None:
                logger.error(f"Workflow '{workflow_name}' not found in discovered workflows: {list(workflows.keys())}")
                return None
            
            # Validate that the class is actually a workflow
            if not issubclass(workflow_class, WorkflowPort):
                logger.error(f"Class for workflow '{workflow_name}' does not implement the WorkflowPort contract")
                return None
            
            return workflow_class
            
        except Exception as e:
            logger.error(f"Error getting workflow class '{workflow_name}': {e}")
            return None

    def list_available_workflow_names(self) -> List[str]:
        """
        Get list of all available workflow names from entry-points
        
        Returns:
            List of workflow names
        """
        return list(self.discover_workflows().keys())
        
    async def initialize(self) -> None:
        """Initialize the workflow manager with available workflows"""
        logger.info("Initializing WorkflowManager...")
        
        # Create workflow instances
        await self._create_workflows()
        
        initialized_workflows = list(self.workflows.keys())
        logger.info(f"WorkflowManager initialized with workflows: {initialized_workflows}")

        if self.active_workflow:
            logger.info(f"Active workflow: {self.active_workflow.name}")
        else:
            logger.info("No active workflow set - will create on-demand")
        
        # Start progress monitoring if workflows are warming up
        warming_up_workflows = [name for name, state in self.workflow_states.items() 
                               if state == WorkflowState.WARMING_UP]
        if warming_up_workflows:
            await self.start_progress_monitoring()
            logger.info(f"Started progress monitoring for warming workflows: {warming_up_workflows}")
        
    async def _create_workflows(self) -> None:
        """Create and initialize workflow instances from configuration"""
        
        # Read workflow configuration
        workflow_config = getattr(self.config, 'workflows', None)
        if not workflow_config:
            logger.warning("No workflow configuration found, falling back to on-demand creation")
            return
        
        enabled_workflows = workflow_config.enabled or ["unified_voice_assistant"]
        default_workflow = workflow_config.default or "unified_voice_assistant"
        
        logger.info(f"Initializing enabled workflows: {enabled_workflows}")
        
        # Initialize enabled workflows in parallel for better performance
        if len(enabled_workflows) > 1:
            logger.info("Initializing workflows in parallel for better performance...")
            workflow_tasks = []
            for workflow_name in enabled_workflows:
                task = asyncio.create_task(
                    self._create_and_initialize_workflow_with_logging(workflow_name),
                    name=f"init_workflow_{workflow_name}"
                )
                workflow_tasks.append((workflow_name, task))
            
            # Wait for all workflows to complete
            for workflow_name, task in workflow_tasks:
                try:
                    await task
                except Exception as e:
                    logger.error(f"❌ Failed to initialize workflow '{workflow_name}': {e}")
        else:
            # Single workflow - no need for parallel processing
            for workflow_name in enabled_workflows:
                try:
                    await self._create_and_initialize_workflow(workflow_name)
                    logger.info(f"✅ Workflow '{workflow_name}' initialized successfully")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize workflow '{workflow_name}': {e}")
        
        # Set default workflow as active
        if default_workflow in self.workflows:
            self.active_workflow = self.workflows[default_workflow]
            self.active_mode = WorkflowMode.UNIFIED
            logger.info(f"Set default workflow: {default_workflow}")
        else:
            logger.warning(f"Default workflow '{default_workflow}' not available")

    async def _create_and_initialize_workflow(self, workflow_name: str) -> None:
        """Create and initialize a specific workflow using entry-points discovery"""
        # Set initial state
        self.set_workflow_state(workflow_name, WorkflowState.INITIALIZING)
        
        try:
            # Get workflow class via entry-points discovery
            workflow_class = self.get_workflow_class(workflow_name)
            if workflow_class is None:
                raise ValueError(f"Workflow '{workflow_name}' not found in entry-points. "
                               f"Available workflows: {self.list_available_workflow_names()}. "
                               f"Register the workflow in pyproject.toml under [project.entry-points.\"locveil_voice.workflows\"]")
            
            # Create workflow instance
            workflow = workflow_class()
            await self._inject_components(workflow)
            
            # Get workflow-specific configuration
            workflow_config = self._get_workflow_config(workflow_name)
            await workflow.initialize(workflow_config)
            self.workflows[workflow_name] = workflow
            
            # Set state to warming up (models may still be loading)
            self.set_workflow_state(workflow_name, WorkflowState.WARMING_UP)
            logger.debug(f"Successfully created workflow '{workflow_name}' using class {workflow_class.__name__}")
            
        except Exception as e:
            self.set_workflow_state(workflow_name, WorkflowState.ERROR)
            logger.error(f"Failed to create workflow '{workflow_name}': {e}")
            raise

    def _get_workflow_config(self, workflow_name: str):
        """
        Get workflow-specific configuration dynamically
        
        Args:
            workflow_name: Name of the workflow
            
        Returns:
            Workflow-specific configuration object
            
        Raises:
            ValueError: If no configuration found for the workflow
        """
        # Get the workflows configuration object
        workflows_config = self.config.workflows
        
        # Try to get the workflow-specific config by attribute name
        if hasattr(workflows_config, workflow_name):
            return getattr(workflows_config, workflow_name)
        else:
            # List available workflow configurations
            available_configs = [attr for attr in dir(workflows_config) 
                               if not attr.startswith('_') and attr not in ['enabled', 'default']]
            raise ValueError(f"No configuration found for workflow '{workflow_name}'. "
                           f"Available workflow configurations: {available_configs}. "
                           f"Add '{workflow_name}' configuration to WorkflowConfig model.")

    async def _create_and_initialize_workflow_with_logging(self, workflow_name: str) -> None:
        """Create and initialize a workflow with success/failure logging"""
        try:
            await self._create_and_initialize_workflow(workflow_name)
            logger.info(f"✅ Workflow '{workflow_name}' initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize workflow '{workflow_name}': {e}")
            raise

    def set_workflow_state(self, workflow_name: str, state: WorkflowState) -> None:
        """Update workflow state and log changes"""
        old_state = self.workflow_states.get(workflow_name)
        self.workflow_states[workflow_name] = state
        
        if old_state != state:
            logger.info(f"Workflow '{workflow_name}' state: {old_state} → {state}")

    async def check_workflow_readiness(self, workflow_name: str) -> bool:
        """Check if workflow is fully ready (all models loaded)"""
        workflow = self.workflows.get(workflow_name)
        if not workflow:
            return False
        
        # Check if all required components have loaded models
        for component_name, component in workflow.components.items():
            if hasattr(component, 'providers'):
                # Note: component.providers only contains ENABLED providers
                for provider_name, provider in component.providers.items():
                    # Only check file-based model providers
                    if hasattr(provider, '_model') and provider._model is None:
                        return False  # Model still loading
                    # SpaCy and other package-based providers are always "ready"
        
        return True

    async def update_workflow_readiness(self) -> None:
        """Update workflow states based on model loading progress"""
        for workflow_name, workflow in self.workflows.items():
            current_state = self.workflow_states.get(workflow_name, WorkflowState.INITIALIZING)
            
            if current_state == WorkflowState.WARMING_UP:
                if await self.check_workflow_readiness(workflow_name):
                    self.set_workflow_state(workflow_name, WorkflowState.READY)

    async def monitor_model_loading_progress(self) -> Dict[str, Any]:
        """Monitor real-time model loading progress across all workflows"""
        progress_report = {
            "overall_progress": 0.0,
            "total_models": 0,
            "loaded_models": 0,
            "loading_models": [],
            "failed_models": [],
            "workflows": {}
        }
        
        total_models = 0
        loaded_models = 0
        
        for workflow_name, workflow in self.workflows.items():
            workflow_progress = await self._get_model_loading_progress(workflow)
            progress_report["workflows"][workflow_name] = {
                "state": self.workflow_states.get(workflow_name, WorkflowState.INITIALIZING).value,
                "progress": workflow_progress,
                "progress_percentage": (
                    (workflow_progress["loaded_providers"] / max(workflow_progress["total_providers"], 1)) * 100
                ) if workflow_progress["total_providers"] > 0 else 100.0
            }
            
            total_models += workflow_progress["total_providers"]
            loaded_models += workflow_progress["loaded_providers"]
            progress_report["loading_models"].extend(workflow_progress["loading_providers"])
            progress_report["failed_models"].extend(workflow_progress.get("failed_providers", []))
        
        progress_report["total_models"] = total_models
        progress_report["loaded_models"] = loaded_models
        progress_report["overall_progress"] = (loaded_models / max(total_models, 1)) * 100 if total_models > 0 else 100.0
        
        return progress_report

    async def start_progress_monitoring(self, update_interval: float = 2.0) -> None:
        """Start continuous progress monitoring with periodic updates"""
        if hasattr(self, '_progress_monitor_task') and self._progress_monitor_task:
            return  # Already running
        
        async def monitor_loop():
            while not self._shutdown_event.is_set():
                try:
                    progress = await self.monitor_model_loading_progress()
                    
                    # Update workflow readiness based on progress
                    await self.update_workflow_readiness()
                    
                    # Log progress for workflows still loading
                    for workflow_name, workflow_data in progress["workflows"].items():
                        if workflow_data["state"] == "warming_up" and workflow_data["progress_percentage"] < 100:
                            loading_providers = workflow_data["progress"]["loading_providers"]
                            if loading_providers:
                                logger.info(f"Workflow '{workflow_name}' loading progress: "
                                          f"{workflow_data['progress_percentage']:.1f}% "
                                          f"(waiting for: {', '.join(loading_providers)})")
                    
                    # Stop monitoring when all workflows are ready
                    if progress["overall_progress"] >= 100.0:
                        logger.info("All workflows ready - stopping progress monitoring")
                        break
                        
                except Exception as e:
                    logger.error(f"Error in progress monitoring: {e}")
                
                await asyncio.sleep(update_interval)
        
        self._progress_monitor_task = asyncio.create_task(monitor_loop())
        logger.info("Started model loading progress monitoring")

    async def stop_progress_monitoring(self) -> None:
        """Stop progress monitoring"""
        if hasattr(self, '_progress_monitor_task') and self._progress_monitor_task:
            self._progress_monitor_task.cancel()
            try:
                await self._progress_monitor_task
            except asyncio.CancelledError:
                pass
            self._progress_monitor_task = None
            logger.info("Stopped progress monitoring")
    
    async def _inject_components(self, workflow: WorkflowPort) -> None:
        """Inject required components into a workflow"""
        try:
            # Get actual component instances, not classes
            component_instances = self.component_manager.get_components()
            
            # Inject component instances into workflow
            for name, component in component_instances.items():
                workflow.add_component(name, component)
            
            # NEW: Inject intent orchestrator from IntentComponent if available
            intent_component = self.component_manager.get_component('intent_system')
            if intent_component and hasattr(intent_component, 'get_orchestrator'):
                intent_orchestrator = intent_component.get_orchestrator()
                if intent_orchestrator:
                    workflow.add_component('intent_orchestrator', intent_orchestrator)
                    logger.debug("Injected intent_orchestrator from IntentComponent")
            
            # Also inject the context manager if available
            if hasattr(self.component_manager, 'context_manager'):
                workflow.add_component('context_manager', self.component_manager.context_manager)

            # ARCH-18: inject the shared audio negotiator (built on core at startup)
            if getattr(self.component_manager, 'audio_negotiator', None) is not None:
                workflow.add_component('audio_negotiator', self.component_manager.audio_negotiator)

            # Inject configuration for temp_audio_dir access
            workflow.add_component('config', self.component_manager.config)
                
            logger.debug(f"Injected {len(workflow.components)} components into {workflow.name}")
            
        except Exception as e:
            logger.error(f"Component injection failed for {workflow.name}: {e}")
            raise
    
    async def process_text_input(
        self,
        text: str,
        session_id: Optional[str] = None,
        wants_audio: bool = False,
        client_context: Optional[Dict[str, Any]] = None,
        trace_context: Optional[TraceContext] = None
    ) -> IntentResult:
        """
        Process text input through the unified workflow (enhanced interface).
        
        This method implements the Q1 decision for unified entry points.
        Skips voice trigger and ASR stages, processes text directly through NLU → Intent → Response.
        
        Args:
            text: Input text to process
            session_id: Session identifier for conversation context
            wants_audio: Whether the response should include audio output (TTS)
            client_context: Optional client context and metadata
            trace_context: Optional trace context for detailed execution tracking
            
        Returns:
            IntentResult from processing with optional action metadata
        """
        # Use active workflow or create unified workflow on-demand
        if not self.active_workflow:
            await self.create_workflow_on_demand("unified_voice_assistant")
            if "unified_voice_assistant" in self.workflows:
                self.active_workflow = self.workflows["unified_voice_assistant"]
                self.active_mode = WorkflowMode.UNIFIED
        
        if not self.active_workflow:
            raise RuntimeError("No active workflow available and failed to create unified_voice_assistant workflow")
        
        unified_workflow = self.active_workflow
        
        # Create enhanced request context.
        # ARCH-15 PR-3: `source` is the *channel* (cli/web/ws/…) for origin-addressed output —
        # taken from client_context; the *format* is carried separately by input_format (PR-1),
        # so source no longer doubles as the format label "text". Defaults to "text" when the
        # caller gives no channel (back-compat).
        context = RequestContext(
            source=(client_context or {}).get("source", "text"),
            session_id=session_id,
            wants_audio=wants_audio,
            input_format=InputFormat.TEXT,  # enters at Text Processing (skips wake-word + ASR)
            metadata=client_context or {"mode": "text_input"},
            client_id=client_context.get("client_id") if client_context else None,
            room_name=client_context.get("room_name") if client_context else None,
            device_context=client_context.get("device_context") if client_context else None
        )
        # Reflect the derived session id (RequestContext forbids "default"/empty → mints a real one)
        session_id = context.session_id

        # ARCH-19 — when startup tracing is on, mint a trace so this request is saved (D-7/D-17);
        # bind it to the ambient contextvar and capture the faithful replay envelope at the boundary.
        # `trace_scope` is no-op-safe when trace_context is None.
        trace_context = self._maybe_create_trace(trace_context)
        if trace_context and trace_context.enabled:
            trace_context.record_input("text", text=text)
            trace_context.record_request(self._replay_request(context))
        try:
            with trace_scope(trace_context):
                await self._publish_pipeline_event(EventType.INPUT_RECEIVED, context,
                                                   {"text": text, "format": "text"})
                result = await unified_workflow.process_text_input(text, context, trace_context)
                await self._publish_pipeline_event(EventType.RESULT_PRODUCED, context, {
                    "text": result.text, "success": result.success,
                    "intent": result.metadata.get("original_intent") if result.metadata else None})
            if trace_context and trace_context.enabled:
                trace_context.record_output(result)
                # D-6 (TEST-13): surface the trace id on the result so a consumer (the /ws/audio
                # response metadata, REST) can correlate each request → its saved <request_id>.json —
                # exact mapping instead of fragile time-based matching. Additive, gated on tracing.
                if result.metadata is None:
                    result.metadata = {}
                result.metadata["request_id"] = trace_context.request_id
            self._save_trace_if_enabled(trace_context)
            # (QUAL-28) F&F actions are registered in the store by the launch — no write-back needed.
            return result
        except Exception as e:
            # CR-A7: persist the trace on the error path too (mirror process_audio_input). The text path
            # previously skipped _save_trace_if_enabled when the workflow raised, so the trace — and the
            # failing stage — were lost exactly when a bug fired. Re-raise to preserve the caller contract
            # (endpoints convert this to HTTP 500); only the trace handling is added here.
            logger.error(f"Text processing error in WorkflowManager: {e}")
            if trace_context:
                trace_context.record_stage(
                    stage_name="workflow_manager_text_error",
                    input_data={"text": text},
                    output_data=None,
                    metadata={"error": str(e), "error_type": type(e).__name__, "session_id": session_id},
                    processing_time_ms=0.0,
                )
            self._save_trace_if_enabled(trace_context)
            raise

    # `_replay_request` kept as a thin alias over the shared core helper (call sites unchanged).
    _replay_request = staticmethod(replay_request)

    # --- ARCH-19 slice 2/3: save-every-request when tracing is enabled at startup (D-7/D-17).
    # Create/save logic lives in core.trace_context (shared with the streaming path); these are
    # thin config-bound wrappers. ---

    def _maybe_create_trace(self, trace_context: Optional[TraceContext]) -> Optional[TraceContext]:
        """When global tracing is on and the caller passed none, mint one so the request is saved.

        An explicitly-passed trace (e.g. the /trace endpoint) is honoured as-is.
        """
        if trace_context is not None:
            return trace_context
        return make_trace(getattr(self.config, "trace", None))

    def _traces_dir(self) -> Path:
        return resolve_traces_dir(getattr(self.config, "trace", None), self.config.assets)

    def _save_trace_if_enabled(self, trace_context: Optional[TraceContext]) -> None:
        """Persist the trace — only when startup tracing is on (delegates to core.save_trace)."""
        save_trace(trace_context, getattr(self.config, "trace", None),
                   getattr(self.config, "assets", None))

    async def _publish_pipeline_event(self, event_type: EventType, context, payload: Dict[str, Any]) -> None:
        """Publish a canonical pipeline event onto the bus (ARCH-15 PR-6), if one is wired.

        Carries the origin identity (session/client/room/source) so the observation tap and the
        delivery subscriber can filter/route. No-op when no bus is configured.
        """
        if self.event_bus is None:
            return
        try:
            await self.event_bus.publish(PipelineEvent(
                type=event_type,
                session_id=getattr(context, "session_id", None),
                client_id=getattr(context, "client_id", None),
                room_name=getattr(context, "room_name", None),
                source=getattr(context, "source", None),
                payload=payload,
            ))
        except Exception as e:
            logger.error(f"Failed to publish pipeline event {event_type.value}: {e}")
    
    async def process_audio_input(
        self,
        audio_data: Union[bytes, 'AudioData'],
        session_id: Optional[str] = None,
        wants_audio: bool = True,
        client_context: Optional[Dict[str, Any]] = None,
        trace_context: Optional[TraceContext] = None
    ) -> IntentResult:
        """
        Process audio input (file bytes or AudioData) through the unified workflow.
        
        This method implements the audio processing entry point with trace support.
        Handles audio conversion and processing through voice trigger → ASR → text pipeline.
        
        Args:
            audio_data: Audio input - either raw bytes from uploaded file or AudioData object
            session_id: Session identifier for conversation context
            wants_audio: Whether the response should include audio output (TTS)
            client_context: Optional client context and metadata
            trace_context: Optional trace context for detailed execution tracking
            
        Returns:
            IntentResult from processing with optional action metadata
        """
        from ..utils.audio_data import AudioData
        
        # Use active workflow or create unified workflow on-demand
        if not self.active_workflow:
            await self.create_workflow_on_demand("unified_voice_assistant")
            if "unified_voice_assistant" in self.workflows:
                self.active_workflow = self.workflows["unified_voice_assistant"]
                self.active_mode = WorkflowMode.UNIFIED
        
        if not self.active_workflow:
            raise RuntimeError("No active workflow available and failed to create unified_voice_assistant workflow")
        
        unified_workflow = self.active_workflow
        
        try:
            # Ensure we have AudioData object (bytes should be converted by caller)
            if isinstance(audio_data, bytes):
                raise ValueError("Workflow manager expects AudioData objects, not raw bytes. "
                               "Convert bytes to AudioData in the calling endpoint.")
            elif not isinstance(audio_data, AudioData):
                raise ValueError(f"audio_data must be bytes or AudioData, got {type(audio_data)}")
            
            # Create enhanced request context for audio processing
            context = RequestContext(
                source="audio",
                session_id=session_id,
                wants_audio=wants_audio,
                skip_wake_word=client_context.get("skip_wake_word", False) if client_context else False,
                skip_asr=client_context.get("skip_asr", False) if client_context else False,
                metadata=client_context or {"mode": "audio_input"},
                client_id=client_context.get("client_id") if client_context else None,
                room_name=client_context.get("room_name") if client_context else None,
                device_context=client_context.get("device_context") if client_context else None
            )
            # Reflect the derived session id (RequestContext forbids "default"/empty → mints a real one)
            session_id = context.session_id

            # ARCH-19 — mint a trace when startup tracing is on (save-every-request, D-7/D-17),
            # capture the faithful replay input (FULL audio inline, no cap) + request, bind the
            # trace to the ambient contextvar, then capture the oracle output.
            trace_context = self._maybe_create_trace(trace_context)
            if trace_context and trace_context.enabled:
                trace_context.record_input(
                    "audio",
                    audio_bytes=getattr(audio_data, "data", b""),
                    audio_format={
                        "rate": getattr(audio_data, "sample_rate", None),
                        "channels": getattr(audio_data, "channels", None),
                        "format": getattr(audio_data, "format", None),
                    },
                )
                trace_context.record_request(self._replay_request(context))

            # Process audio through unified workflow with trace support.
            # `process_audio_input` is a concrete-only entry point (not part of
            # the WorkflowPort contract — see the port docstring), so resolve it
            # dynamically off the active workflow.
            process_audio_input = getattr(unified_workflow, "process_audio_input")
            with trace_scope(trace_context):
                await self._publish_pipeline_event(EventType.INPUT_RECEIVED, context,
                                                   {"format": "audio"})
                result = await process_audio_input(audio_data, context, trace_context)
                await self._publish_pipeline_event(EventType.RESULT_PRODUCED, context, {
                    "text": result.text, "success": result.success,
                    "intent": result.metadata.get("original_intent") if result.metadata else None})
            if trace_context and trace_context.enabled:
                trace_context.record_output(result)
                # D-6 (TEST-13): surface the trace id on the result so a consumer (the /ws/audio
                # response metadata, REST) can correlate each request → its saved <request_id>.json —
                # exact mapping instead of fragile time-based matching. Additive, gated on tracing.
                if result.metadata is None:
                    result.metadata = {}
                result.metadata["request_id"] = trace_context.request_id
            self._save_trace_if_enabled(trace_context)
            # (QUAL-28) F&F actions are registered in the store by the launch — no write-back needed.
            return result

        except Exception as e:
            logger.error(f"Audio processing error in WorkflowManager: {e}")
            
            # Record error in trace if available
            if trace_context:
                trace_context.record_stage(
                    stage_name="workflow_manager_audio_error",
                    input_data={"audio_type": type(audio_data).__name__},
                    output_data=None,
                    metadata={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "session_id": session_id
                    },
                    processing_time_ms=0.0
                )
            # Persist the trace even on the error path (it carries the error stage).
            self._save_trace_if_enabled(trace_context)

            # Return error result
            return IntentResult(
                text=f"Audio processing failed: {str(e)}",
                success=False,
                metadata={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "source": "workflow_manager_audio"
                },
                error=str(e),
                confidence=0.0
            )
    
    async def process_audio_stream(
        self,
        audio_stream: AsyncIterator[AudioData],
        session_id: Optional[str] = None,
        skip_wake_word: bool = False,
        wants_audio: bool = True,
        client_context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[IntentResult]:
        """
        Process audio stream through the unified workflow (enhanced interface).
        
        This method implements the Q1 decision for unified entry points.
        Processes audio through conditional pipeline stages based on skip_wake_word parameter.
        
        Args:
            audio_stream: Async iterator of audio data to process
            session_id: Session identifier for conversation context
            skip_wake_word: Whether to skip wake word detection (True for WebAPI, False for Voice)
            wants_audio: Whether the response should include audio output (TTS)
            client_context: Optional client context and metadata
            
        Yields:
            IntentResult objects as they are generated
        """
        # Use active workflow or create unified workflow on-demand
        if not self.active_workflow:
            await self.create_workflow_on_demand("unified_voice_assistant")
            if "unified_voice_assistant" in self.workflows:
                self.active_workflow = self.workflows["unified_voice_assistant"]
                self.active_mode = WorkflowMode.UNIFIED
        
        if not self.active_workflow:
            raise RuntimeError("No active workflow available and failed to create unified_voice_assistant workflow")
        
        unified_workflow = self.active_workflow
        
        # Create enhanced request context
        context = RequestContext(
            source="audio_stream" if skip_wake_word else "voice",
            session_id=session_id,
            wants_audio=wants_audio,
            skip_wake_word=skip_wake_word,
            metadata=client_context or {"mode": "audio_stream"},
            client_id=client_context.get("client_id") if client_context else None,
            room_name=client_context.get("room_name") if client_context else None,
            device_context=client_context.get("device_context") if client_context else None
        )
        # Reflect the derived session id (RequestContext forbids "default"/empty → mints a real one)
        session_id = context.session_id

        async for result in unified_workflow.process_audio_stream(audio_stream, context):
            # (QUAL-28) F&F actions are registered in the store by the launch — no write-back needed.
            yield result
    
    async def _get_audio_stream(self, input_source: InputPort) -> AsyncIterator[AudioData]:
        """
        Convert input source to audio stream.
        
        Handles both legacy text input sources and modern AudioData sources.
        Microphone input now provides AudioData objects directly.
        """
        async for data in input_source.listen():
            # Handle different input data types
            if isinstance(data, AudioData):
                # Modern AudioData from microphone input - pass through directly
                yield data
            elif hasattr(data, 'data') and hasattr(data, 'timestamp'):
                # InputData that contains audio data - convert to AudioData
                yield AudioData(
                    data=getattr(data, 'data'),
                    timestamp=getattr(data, 'timestamp', time.time()),
                    sample_rate=getattr(data, 'sample_rate', 16000),
                    channels=getattr(data, 'channels', 1),
                    format=getattr(data, 'format', 'pcm16')
                )
            elif isinstance(data, str):
                # Legacy text input - skip (not audio data)
                logger.debug(f"Skipping text input in audio stream: {data[:50]}...")
                continue
            else:
                # Unknown data type - log warning but continue
                logger.warning(f"Unknown input data type in audio stream: {type(data)}")
                continue
    
    async def stop_current_workflow(self) -> None:
        """Stop the currently active workflow"""
        if self._workflow_task:
            self._workflow_task.cancel()
            try:
                await self._workflow_task
            except asyncio.CancelledError:
                pass
            self._workflow_task = None
        
        if self.active_workflow:
            logger.info(f"Stopped workflow: {self.active_workflow.name}")
            self.active_workflow = None
            self.active_mode = None
    
    def get_current_mode(self) -> Optional[WorkflowMode]:
        """Get the current workflow mode"""
        return self.active_mode
    
    def get_available_workflows(self) -> list[str]:
        """Get list of available workflow names from entry-points discovery"""
        return self.list_available_workflow_names()

    async def create_workflow_on_demand(self, workflow_name: str) -> bool:
        """
        Create a new workflow on-demand if it doesn't exist
        
        Args:
            workflow_name: Name of the workflow to create
            
        Returns:
            bool: True if creation was successful, False otherwise
        """
        if workflow_name in self.workflows:
            logger.info(f"Workflow '{workflow_name}' already exists")
            return True
        
        # Check if the workflow is available via entry-points first
        available_workflows = self.list_available_workflow_names()
        if workflow_name not in available_workflows:
            logger.error(f"Workflow '{workflow_name}' not found in available workflows: {available_workflows}")
            return False
        
        try:
            logger.info(f"Creating workflow on-demand: {workflow_name}")
            await self._create_and_initialize_workflow(workflow_name)
            logger.info(f"✅ Successfully created workflow: {workflow_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create workflow '{workflow_name}': {e}")
            return False

    async def get_workflow_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all workflows"""
        status = {
            "active_mode": self.active_mode.value if self.active_mode else None,
            "active_workflow": self.active_workflow.name if self.active_workflow else None,
            "available_workflows": self.get_available_workflows(),
            "workflows": {}
        }
        
        for name, workflow in self.workflows.items():
            workflow_state = self.workflow_states.get(name, WorkflowState.INITIALIZING)
            is_ready = await self.check_workflow_readiness(name)
            
            status["workflows"][name] = {
                "initialized": workflow.initialized,
                "state": workflow_state.value,
                "ready": is_ready,
                "components": len(workflow.components),
                "model_loading_progress": await self._get_model_loading_progress(workflow)
            }
        
        return status

    async def _get_model_loading_progress(self, workflow: WorkflowPort) -> Dict[str, Any]:
        """Get model loading progress for workflow components"""
        progress = {
            "total_providers": 0,
            "loaded_providers": 0,
            "loading_providers": [],
            "failed_providers": []
        }
        
        for component_name, component in workflow.components.items():
            if hasattr(component, 'providers'):
                for provider_name, provider in component.providers.items():
                    progress["total_providers"] += 1
                    
                    # Categorize providers by type
                    if hasattr(provider, '_model'):
                        # File-based AI model provider
                        if provider._model is not None:
                            progress["loaded_providers"] += 1
                        else:
                            progress["loading_providers"].append(f"{component_name}.{provider_name}")
                    else:
                        # Package-based, API-based, or console provider (always ready)
                        progress["loaded_providers"] += 1
        
        return progress
    
    async def cleanup(self) -> None:
        """Clean up workflow manager resources"""
        await self.stop_current_workflow()
        
        # Stop progress monitoring
        await self.stop_progress_monitoring()
        
        # Clean up workflows (`cleanup` is an optional concrete-only hook,
        # not part of the WorkflowPort contract)
        for workflow in self.workflows.values():
            workflow_cleanup = getattr(workflow, 'cleanup', None)
            if workflow_cleanup is not None:
                try:
                    await workflow_cleanup()
                except Exception as e:
                    logger.error(f"Workflow cleanup error: {e}")
        
        logger.info("WorkflowManager cleaned up") 