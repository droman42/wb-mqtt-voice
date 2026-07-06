"""
WebAPI Router - FastAPI routes for Irene Voice Assistant

Extracted from webapi_runner.py to separate routing concerns from server setup.
Contains all endpoint definitions and request handlers.
"""

import asyncio
import json
import logging
import re
import time
import uuid
from typing import Dict, Any, List, Optional

# Types used in the public signatures below. This module is only ever imported
# lazily from the WebAPI runner (after fastapi is confirmed installed) and from
# tests, so these imports are always satisfiable at the point of use. Importing
# them unconditionally keeps them as real types (the previous try/except fallback
# rebound them to `object`, which makes them unusable in type annotations).
from ..core.engine import AsyncVACore
from ..core.intent_asset_loader import IntentAssetLoader
from ..inputs.web import WebInput
from fastapi import APIRouter  # type: ignore

logger = logging.getLogger(__name__)

# BUG-17: hard per-utterance bound for the /ws/audio batch floor. A client that never sends
# {"type":"end"} (buggy satellite firmware) must not grow the PCM accumulator without limit
# (~115 MB/h at 16 kHz). Generous for a voice command; on overflow the utterance is
# force-finalized (the VAD path's `max_segment_duration_s` semantics) and the loop continues.
WS_MAX_UTTERANCE_SECONDS = 60

# BUG-13: the streaming branch's read-idle bound. A bounded client that stops sending
# without {"type":"end"} would otherwise hang forever — silence-less bounded audio never
# trips the model's endpoint detector, and the receive() blocks indefinitely. After this
# many seconds with NO frames, the current utterance is force-finalized. Always-on devices
# stream continuously (silence included), so this never fires for them.
WS_STREAMING_IDLE_TIMEOUT_SECONDS = 10.0

# ARCH-36 finding (b): behind the nginx mTLS proxy (Plane B) the verified client-cert subject
# arrives on every proxied request. The canonical header is X-Client-Cert-DN (the value is the
# FULL subject DN, e.g. "CN=kitchen_node,O=irene"); X-Client-Cert-CN is accepted for deployments
# rendered before the rename — its value was always the DN too ($ssl_client_s_dn).
_CERT_DN_HEADERS = ("x-client-cert-dn", "x-client-cert-cn")
_CERT_CN_RE = re.compile(r"(?:^|[,/])\s*CN=([^,/]+)", re.IGNORECASE)


def _client_cert_cn(headers: Any) -> Optional[str]:
    """CN extracted from the proxy-injected client-cert subject DN, or None when the request
    did not come through the mTLS proxy (plain ws://, local/dev — no binding to enforce)."""
    for name in _CERT_DN_HEADERS:
        dn = headers.get(name)
        if dn:
            m = _CERT_CN_RE.search(dn)
            return m.group(1).strip() if m else dn.strip()
    return None


def create_webapi_router(
    core: AsyncVACore, 
    asset_loader: Optional[IntentAssetLoader], 
    web_input: Optional[WebInput], 
    start_time: float
) -> APIRouter:
    """
    Create FastAPI router with all WebAPI endpoints
    
    Args:
        core: AsyncVACore instance for processing commands and component access
        asset_loader: IntentAssetLoader instance for serving HTML templates (can be None)
        web_input: WebInput instance for connection info (can be None)
        start_time: Server start time for uptime calculation
    
    Returns:
        FastAPI router with all endpoints configured
    """
    from fastapi import APIRouter, HTTPException, UploadFile, File  # type: ignore
    from fastapi.responses import HTMLResponse, Response  # type: ignore
    from pydantic import BaseModel  # type: ignore
    
    # Import centralized API schemas
    from ..api.schemas import CommandRequest, CommandResponse, TraceCommandResponse, ExecutionTrace
    from ..api.serializers import serialize_intent_result
    from ..core.trace_context import TraceContext
    from ..core.session_manager import SessionManager
    from ..utils.loader import get_component_status
    from ..__version__ import __version__
    
    router = APIRouter()
    
    # Local response models for specific endpoints
    class StatusResponse(BaseModel):
        status: str
        components: Dict[str, Any]
        web_clients: int

    class HealthResponse(BaseModel):  # QUAL-39: type the /health envelope
        status: str
        version: str
        timestamp: float

    class HistoryResponse(BaseModel):
        messages: list[Dict[str, Any]]
        total_count: int
    
    class SystemCapabilitiesResponse(BaseModel):
        version: str
        components: Dict[str, Any]
        intent_handlers: List[str]
        nlu_providers: List[str]
        voice_trigger_providers: List[str]
        text_processing_providers: List[str]
        workflows: List[str]
    
    # Root endpoint
    @router.get("/", response_class=HTMLResponse, tags=["General"])
    async def root():
        """Serve a simple web interface"""
        if asset_loader:
            html_content = asset_loader.get_web_template_with_variables(
                "index",
                version=__version__
            )
            if html_content:
                return HTMLResponse(content=html_content)
            else:
                logger.error("Web template 'index' not found")
                raise HTTPException(status_code=500, detail="Web interface template not available")
        else:
            logger.error("Web asset loader not initialized")
            raise HTTPException(status_code=500, detail="Web asset system not available")
    
    # Status endpoint
    @router.get("/status", response_model=StatusResponse, tags=["General"])
    async def get_status():
        """Get assistant status and component information"""
        components = get_component_status()
        web_clients = 0  # WebSocket clients now handled by individual components
        
        return StatusResponse(
            status="running",
            components=components,
            web_clients=web_clients
        )
    
    # Room alias validation helper function
    async def _validate_and_resolve_room_alias(
        room_alias: str, 
        asset_loader: Optional[IntentAssetLoader]
    ) -> tuple[bool, str]:
        """Validate room alias against localization files and return session_id
        
        Args:
            room_alias: Room identifier to validate (e.g., 'kitchen')
            asset_loader: Asset loader for accessing room localization data
            
        Returns:
            Tuple of (is_valid, session_id_or_error_message)
        """
        if not asset_loader:
            return False, f"Room alias '{room_alias}' cannot be validated - asset loader unavailable"
        
        try:
            # Get room aliases from localization files
            room_localization = asset_loader.localizations.get("rooms", {})
            room_data = room_localization.get("en", {})  # Default to English
            
            # Fallback to Russian if English not available
            if not room_data:
                room_data = room_localization.get("ru", {})
            
            room_aliases = room_data.get("room_keywords", {}).get("room_aliases", {})
            
            if room_alias not in room_aliases:
                available_aliases = list(room_aliases.keys())
                return False, f"Invalid room alias '{room_alias}'. Valid aliases: {available_aliases}"
            
            # Generate session_id using SessionManager from Phase 4
            session_id = SessionManager.generate_session_id("api", room_id=room_alias)
            
            return True, session_id
            
        except Exception as e:
            return False, f"Room alias validation failed: {str(e)}"
    
    # Command execution endpoint
    @router.post("/execute/command", response_model=CommandResponse, tags=["General"])
    async def execute_command(request: CommandRequest):
        """Execute a voice assistant command via REST API with optional room context"""
        try:
            if not core:
                raise HTTPException(status_code=503, detail="Assistant not initialized")
            
            # NEW: Room alias validation and session_id generation
            if request.room_alias:
                is_valid, session_id_or_error = await _validate_and_resolve_room_alias(
                    request.room_alias, asset_loader
                )
                if not is_valid:
                    raise HTTPException(status_code=400, detail=session_id_or_error)
                
                session_id = session_id_or_error
                client_id = request.room_alias
                logger.debug(f"Using room-scoped session: {session_id} for room '{request.room_alias}'")
            else:
                # Existing behavior - use metadata or fallback
                session_id = request.metadata.get("session_id", SessionManager.generate_session_id("webapi")) if request.metadata else SessionManager.generate_session_id("webapi")
                client_id = None
            
            # Enhanced client context with room information
            client_context = {
                "source": "api",
                "room_alias": request.room_alias,
                "client_id": client_id
            }
            if request.metadata:
                client_context.update(request.metadata)
            
            # Execute command with enhanced context
            result = await core.workflow_manager.process_text_input(
                text=request.command,
                session_id=session_id,
                wants_audio=False,
                client_context=client_context
            )
            
            # QUAL-55: the canonical result projection — one serializer for all five surfaces.
            return CommandResponse(
                **serialize_intent_result(result),
                session_id=session_id,
                room_alias=request.room_alias,
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            raise HTTPException(status_code=500, detail=f"Command execution failed: {str(e)}")
    
    # Audio execution endpoint
    @router.post("/execute/audio", response_model=CommandResponse, tags=["General"])
    async def execute_audio(audio_file: UploadFile = File(...), room_alias: Optional[str] = None, skip_asr: bool = False):
        """Execute audio processing via REST API with optional room context"""
        session_id = "unknown"
        try:
            if not core:
                raise HTTPException(status_code=503, detail="Assistant not initialized")

            # NEW: Room alias validation and session_id generation
            if room_alias:
                is_valid, session_id_or_error = await _validate_and_resolve_room_alias(
                    room_alias, asset_loader
                )
                if not is_valid:
                    raise HTTPException(status_code=400, detail=session_id_or_error)
                
                session_id = session_id_or_error
                client_id = room_alias
                logger.debug(f"Using room-scoped session: {session_id} for audio in room '{room_alias}'")
            else:
                # Existing behavior - hardcoded session
                session_id = SessionManager.generate_session_id("api")
                client_id = None
            
            # Validate file size (limit to 10MB for safety)
            MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
            file_size = 0
            audio_data = b""
            
            # Read audio data with size check
            while True:
                chunk = await audio_file.read(8192)  # Read in 8KB chunks
                if not chunk:
                    break
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413, 
                        detail=f"Audio file too large (max {MAX_FILE_SIZE / 1024 / 1024:.1f}MB)"
                    )
                audio_data += chunk
            
            logger.info(f"Audio processing: {audio_file.filename}, size: {file_size} bytes, room: {room_alias or 'none'}")
            
            # Convert uploaded audio bytes to AudioData object
            from ..utils.audio_helpers import load_audio_file_to_audiodata_from_bytes
            
            try:
                audio_data_obj = await load_audio_file_to_audiodata_from_bytes(
                    audio_bytes=audio_data,
                    filename=audio_file.filename
                )
            except Exception as e:
                logger.error(f"Failed to process audio file '{audio_file.filename}': {e}")
                raise HTTPException(status_code=400, detail=f"Invalid audio file: {str(e)}")
            
            # Enhanced client context with room information
            client_context = {
                "source": "audio_api",
                "filename": audio_file.filename,
                "skip_wake_word": True,  # Skip wake word for uploaded files
                "skip_asr": skip_asr,  # Allow ASR to be skipped
                "file_size_bytes": file_size,
                "room_alias": room_alias,
                "client_id": client_id
            }
            
            # Process audio through workflow manager with enhanced context
            result = await core.workflow_manager.process_audio_input(
                audio_data=audio_data_obj,  # Now passing AudioData object
                session_id=session_id,
                wants_audio=False,  # Don't generate TTS for API endpoint
                client_context=client_context
            )
            
            # QUAL-55: canonical projection; the file-info extras ride INSIDE metadata (F3).
            return CommandResponse(
                **serialize_intent_result(result, extra_metadata={
                    "processed_via": "audio_api",
                    "filename": audio_file.filename,
                    "file_size_bytes": file_size,
                    "room_context": bool(room_alias),
                }),
                session_id=session_id,
                room_alias=room_alias,
            )

        except HTTPException:
            # Re-raise HTTP exceptions (like file too large)
            raise

        except Exception as e:
            logger.error(f"Audio execution error: {e}")
            return CommandResponse(
                success=False,
                text="",
                session_id=session_id,
                error=str(e)
            )
    
    # Health check endpoint
    @router.get("/health", response_model=HealthResponse, tags=["General"])
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "version": __version__,
            "timestamp": asyncio.get_event_loop().time()
        }
    
    # PHASE 7 - TODO16: Trace endpoints for detailed pipeline execution visibility
    @router.post("/trace/command", response_model=TraceCommandResponse, tags=["Tracing"])
    async def trace_command_execution(request: CommandRequest):
        """Execute command with full execution trace and optional room context"""
        trace_context: Optional[TraceContext] = None
        session_id = "unknown"
        try:
            if not core:
                raise HTTPException(status_code=503, detail="Assistant not initialized")

            # NEW: Room alias validation and session_id generation (same as execute)
            if request.room_alias:
                is_valid, session_id_or_error = await _validate_and_resolve_room_alias(
                    request.room_alias, asset_loader
                )
                if not is_valid:
                    raise HTTPException(status_code=400, detail=session_id_or_error)
                
                session_id = session_id_or_error
                client_id = request.room_alias
            else:
                session_id = request.metadata.get("session_id", SessionManager.generate_session_id("trace")) if request.metadata else SessionManager.generate_session_id("trace")
                client_id = None
            
            # Create trace context for detailed execution tracking
            trace_context = TraceContext(
                enabled=True, 
                request_id=str(uuid.uuid4()),
                max_stages=50,
                max_data_size_mb=5
            )
            
            # Enhanced client context with room information and tracing
            client_context = {
                "source": "trace_api", 
                "trace_enabled": True,
                "room_alias": request.room_alias,
                "client_id": client_id
            }
            if request.metadata:
                client_context.update(request.metadata)
            
            # Execute with tracing and room context
            result = await core.workflow_manager.process_text_input(
                text=request.command,
                session_id=session_id,
                wants_audio=False,
                client_context=client_context,
                trace_context=trace_context
            )
            
            return TraceCommandResponse(
                success=result.success,
                final_result=serialize_intent_result(result),  # QUAL-55: canonical projection
                execution_trace=ExecutionTrace.model_validate({
                    "request_id": trace_context.request_id,
                    "pipeline_stages": [
                        {
                            "stage": stage.get("stage", "unknown"),
                            "input_data": stage.get("input"),
                            "output_data": stage.get("output"),
                            "metadata": stage.get("metadata", {}),
                            "processing_time_ms": stage.get("processing_time_ms", 0.0),
                            "timestamp": stage.get("timestamp", time.time())
                        }
                        for stage in trace_context.stages
                    ],
                    "context_evolution": {
                        "before": trace_context.context_snapshots.get("before"),
                        "after": trace_context.context_snapshots.get("after"),
                        "changes": trace_context._calculate_context_changes()
                    },
                    "performance_metrics": {
                        "total_processing_time_ms": sum(
                            stage.get("processing_time_ms", 0) for stage in trace_context.stages
                        ),
                        "stage_breakdown": {
                            stage.get("stage", "unknown"): stage.get("processing_time_ms", 0)
                            for stage in trace_context.stages
                        },
                        "total_stages": len(trace_context.stages)
                    }
                }),
                session_id=session_id,
                room_alias=request.room_alias,  # NEW: Include room alias in trace response
                metadata={
                    "trace_id": trace_context.request_id,
                    "total_stages": len(trace_context.stages),
                    "execution_time": sum(stage.get("processing_time_ms", 0) for stage in trace_context.stages)
                },
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"Trace command execution error: {e}")
            trace_request_id = trace_context.request_id if trace_context is not None else "unknown"
            return TraceCommandResponse(
                success=False,
                final_result={},
                execution_trace=ExecutionTrace.model_validate({
                    "request_id": trace_request_id,
                    "pipeline_stages": [],
                    "context_evolution": {
                        "before": None,
                        "after": None,
                        "changes": {}
                    },
                    "performance_metrics": {
                        "total_processing_time_ms": 0.0,
                        "stage_breakdown": {},
                        "total_stages": 0
                    },
                    "error": str(e)
                }),
                session_id=session_id,
                timestamp=time.time(),
                error=str(e)
            )
    
    @router.post("/trace/audio", response_model=TraceCommandResponse, tags=["Tracing"])
    async def trace_audio_execution(audio_file: UploadFile = File(...), room_alias: Optional[str] = None, skip_asr: bool = False):
        """Execute audio processing with full execution trace and optional room context"""
        trace_context: Optional[TraceContext] = None
        session_id = "unknown"
        try:
            if not core:
                raise HTTPException(status_code=503, detail="Assistant not initialized")

            # NEW: Room alias validation and session_id generation (same as execute/audio)
            if room_alias:
                is_valid, session_id_or_error = await _validate_and_resolve_room_alias(
                    room_alias, asset_loader
                )
                if not is_valid:
                    raise HTTPException(status_code=400, detail=session_id_or_error)
                
                session_id = session_id_or_error
                client_id = room_alias
            else:
                session_id = SessionManager.generate_session_id("trace_audio")
                client_id = None
            
            # Validate file size (limit to 10MB for safety)
            MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
            file_size = 0
            audio_data = b""
            
            # Read audio data with size check
            while True:
                chunk = await audio_file.read(8192)  # Read in 8KB chunks
                if not chunk:
                    break
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413, 
                        detail=f"Audio file too large (max {MAX_FILE_SIZE / 1024 / 1024:.1f}MB)"
                    )
                audio_data += chunk
            
            # Create trace context with production limits for audio
            trace_context = TraceContext(
                enabled=True, 
                request_id=str(uuid.uuid4()),
                max_stages=75,  # More stages for audio processing
                max_data_size_mb=15  # Higher limit for audio traces (includes audio data)
            )
            
            logger.info(f"Trace audio processing: {audio_file.filename}, size: {file_size} bytes, room: {room_alias or 'none'}")
            
            # Convert uploaded audio bytes to AudioData object with tracing
            from ..utils.audio_helpers import load_audio_file_to_audiodata_from_bytes

            # Record audio file loading stage for tracing
            stage_start = time.time()
            
            try:
                audio_data_obj = await load_audio_file_to_audiodata_from_bytes(
                    audio_bytes=audio_data,
                    filename=audio_file.filename
                )
                
                # Record the audio file loading stage in trace context
                trace_context.record_stage(
                    stage_name="audio_file_loading",
                    input_data={"size_bytes": len(audio_data), "format": "auto_detected"},
                    output_data=audio_data_obj,
                    metadata={
                        "original_size_bytes": len(audio_data),
                        "converted_sample_rate": audio_data_obj.sample_rate,
                        "converted_channels": audio_data_obj.channels,
                        "detected_format": audio_data_obj.metadata.get("detected_format"),
                        "source_type": "uploaded_bytes",
                        "filename": audio_file.filename
                    },
                    processing_time_ms=(time.time() - stage_start) * 1000
                )
                
            except Exception as e:
                logger.error(f"Failed to process audio file '{audio_file.filename}': {e}")
                raise HTTPException(status_code=400, detail=f"Invalid audio file: {str(e)}")
            
            # Enhanced client context with room information and tracing
            client_context = {
                "source": "trace_audio_api",
                "filename": audio_file.filename,
                "skip_wake_word": True,  # Skip wake word for uploaded files
                "skip_asr": skip_asr,  # Allow ASR to be skipped
                "file_size_bytes": file_size,
                "trace_enabled": True,
                "room_alias": room_alias,
                "client_id": client_id
            }
            
            # Process audio through workflow manager with tracing and room context
            result = await core.workflow_manager.process_audio_input(
                audio_data=audio_data_obj,  # Now passing AudioData object
                session_id=session_id,
                wants_audio=False,  # Don't generate TTS for trace endpoint
                client_context=client_context,
                trace_context=trace_context
            )
            
            return TraceCommandResponse(
                success=result.success,
                final_result=serialize_intent_result(result),  # QUAL-55: canonical projection
                execution_trace=ExecutionTrace.model_validate({
                    "request_id": trace_context.request_id,
                    "pipeline_stages": [
                        {
                            "stage": stage.get("stage", "unknown"),
                            "input_data": stage.get("input"),
                            "output_data": stage.get("output"),
                            "metadata": stage.get("metadata", {}),
                            "processing_time_ms": stage.get("processing_time_ms", 0.0),
                            "timestamp": stage.get("timestamp", time.time())
                        }
                        for stage in trace_context.stages
                    ],
                    "context_evolution": {
                        "before": trace_context.context_snapshots.get("before"),
                        "after": trace_context.context_snapshots.get("after"),
                        "changes": trace_context._calculate_context_changes()
                    },
                    "performance_metrics": {
                        "total_processing_time_ms": sum(
                            stage.get("processing_time_ms", 0) for stage in trace_context.stages
                        ),
                        "stage_breakdown": {
                            stage.get("stage", "unknown"): stage.get("processing_time_ms", 0)
                            for stage in trace_context.stages
                        },
                        "total_stages": len(trace_context.stages)
                    }
                }),
                session_id=session_id,
                room_alias=room_alias,  # NEW: Include room alias in trace response
                metadata={
                    "trace_id": trace_context.request_id,
                    "total_stages": len(trace_context.stages),
                    "execution_time": sum(stage.get("processing_time_ms", 0) for stage in trace_context.stages),
                    "filename": audio_file.filename,
                    "file_size_bytes": file_size,
                    "room_context": bool(room_alias)
                },
                timestamp=time.time()
            )
            
        except HTTPException:
            # Re-raise HTTP exceptions (like file too large)
            raise
            
        except Exception as e:
            logger.error(f"Trace audio execution error: {e}")
            trace_request_id = trace_context.request_id if trace_context is not None else "unknown"
            return TraceCommandResponse(
                success=False,
                final_result={},
                execution_trace=ExecutionTrace.model_validate({
                    "request_id": trace_request_id,
                    "pipeline_stages": trace_context.stages if trace_context is not None else [],
                    "context_evolution": {
                        "before": trace_context.context_snapshots.get("before") if trace_context is not None else None,
                        "after": trace_context.context_snapshots.get("after") if trace_context is not None else None,
                        "changes": trace_context._calculate_context_changes() if trace_context is not None else {}
                    },
                    "performance_metrics": {
                        "total_processing_time_ms": sum(
                            stage.get("processing_time_ms", 0) for stage in trace_context.stages
                        ) if trace_context is not None else 0.0,
                        "stage_breakdown": {
                            stage.get("stage", "unknown"): stage.get("processing_time_ms", 0)
                            for stage in trace_context.stages
                        } if trace_context is not None else {},
                        "total_stages": len(trace_context.stages) if trace_context is not None else 0
                    },
                    "error": str(e)
                }),
                session_id=session_id,
                timestamp=time.time(),
                error=str(e)
            )
    
    # Component info endpoint
    @router.get("/components", tags=["General"])
    async def get_component_info():
        """Get detailed component information"""
        info = {}
        
        if web_input:
            info["web_input"] = web_input.get_connection_info()
        
        # Web output handled via HTTP responses (unified workflow)
        
        if core:
            info["core"] = {
                "input_sources": list(core.input_manager._sources.keys()),
                "workflows": list(core.workflow_manager.workflows.keys())
            }
        
        return info
    
    # System capabilities endpoint
    @router.get("/system/capabilities", response_model=SystemCapabilitiesResponse, tags=["General"])
    async def get_system_capabilities():
        """Get comprehensive system capabilities"""
        try:
            # QUAL-59: derive provider/workflow lists from what is actually loaded — the old
            # hardcoded lists drifted (they advertised a "continuous_listening" workflow that no
            # longer exists and missed the llm NLU provider).
            def _provider_names(component_name: str) -> List[str]:
                comp = core.component_manager.get_component(component_name) \
                    if core and getattr(core, "component_manager", None) else None
                providers = getattr(comp, "providers", None)
                return sorted(providers.keys()) if isinstance(providers, dict) else []

            workflows: List[str] = []
            if core and getattr(core, "workflow_manager", None):
                workflows = sorted(core.workflow_manager.workflows.keys())

            capabilities = {
                "version": __version__,
                "components": {},
                "intent_handlers": [],
                "nlu_providers": _provider_names("nlu"),
                "voice_trigger_providers": _provider_names("voice_trigger"),
                "text_processing_providers": _provider_names("text_processor"),
                "workflows": workflows
            }
            
            # Get component status if available
            if core and hasattr(core, 'component_manager'):
                try:
                    component_status = core.component_manager.get_available_components()
                    capabilities["components"] = {
                        name: {"available": True, "type": type(comp).__name__}
                        for name, comp in component_status.items()
                    }
                except Exception as e:
                    logger.warning(f"Could not get component status: {e}")
            
            return SystemCapabilitiesResponse(**capabilities)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # Enhanced system status endpoint
    @router.get("/system/status", tags=["General"])
    async def get_enhanced_system_status():
        """Enhanced system status with intent system information"""
        try:
            status = {
                "system": "healthy",
                "version": __version__,
                "mode": "intent_system" if hasattr(core, 'workflow_manager') else "legacy",
                "timestamp": time.time(),
                "uptime": time.time() - start_time
            }
            
            # Add component information
            if core:
                status["core"] = {
                    "running": core.is_running,
                    "input_sources": len(getattr(core.input_manager, '_sources', {}))
                }
            
            # Web client information now handled by individual components
            status["web_clients"] = 0  # Component-specific WebSockets handle client tracking
            
            return status
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # ARCH-6: WebSocket streaming-input DRIVING adapter (ESP32 mic-node primary transport).
    # Registration handshake → ClientRegistry → stream raw PCM → FULL pipeline → response.
    # Wake-word is on-device, so skip_wake_word=True. Distinct from the ASR-utility /asr/* endpoints
    # (those return transcription only). See docs/design/ws_esp32_transport.md.
    from fastapi import WebSocket  # local import: fastapi is an optional/web extra

    @router.websocket("/ws/audio")
    async def ws_audio_driving_input(websocket: WebSocket):
        from fastapi import WebSocketDisconnect
        from ..core.client_registry import get_client_registry, ClientRegistration
        from ..intents.models import AudioData

        await websocket.accept()
        session_id = uuid.uuid4().hex  # stable across utterances on this connection (room/device continuity)
        try:
            # Step 1 — registration handshake (first TEXT frame): the identity linchpin (QUAL-28 store).
            reg = json.loads(await websocket.receive_text())
            if reg.get("type") != "register":
                await websocket.send_json({"type": "error", "error": "first frame must be type=register"})
                await websocket.close()
                return
            registration = ClientRegistration.from_dict(reg)
            # ARCH-36 finding (b) — mTLS identity binding: behind the nginx Plane-B proxy the
            # verified client-cert subject DN arrives as a header; when present, the claimed
            # client_id MUST match the cert's CN (a cert for the kitchen node cannot register
            # as the bedroom). Absent header (plain ws://, local/dev) skips the check.
            cert_cn = _client_cert_cn(websocket.headers)
            if cert_cn is not None and cert_cn != registration.client_id:
                await websocket.send_json({"type": "error",
                                           "error": f"client_id does not match certificate identity ({cert_cn})"})
                await websocket.close()
                return
            await get_client_registry().register_client(registration)
            sample_rate = int(reg.get("sample_rate", 16000))
            wants_audio = bool(reg.get("wants_audio", False))
            # client_context flows into RequestContext → context.client_id/room_name → resolve_physical_id
            # returns the PHYSICAL origin (room/device) instead of the ephemeral session id. ARCH-6 activation.
            client_context = {
                "source": "ws_audio",
                "skip_wake_word": True,  # on-device wake word
                "client_id": registration.client_id,
                "room_name": registration.room_name,  # primary room (ARCH-22 D-14)
                "covered_rooms": registration.covered_rooms,  # ARCH-22 D-14: ready for the room resolver
                "device_context": {"available_devices": [
                    {"id": d.id, "name": d.name, "type": d.type, "capabilities": d.capabilities,
                     "location": d.location} for d in registration.available_devices]},
            }
            await websocket.send_json({"type": "registered", "client_id": registration.client_id,
                                       "session_id": session_id})

            # ARCH-22: the SPOKEN reply goes back to the device's reply channel (/ws/audio/reply), never
            # local playback — so processing runs with wants_audio=False and we route the SPEECH modality
            # origin-paired via the OutputManager (reaches this client's RemoteAudioOutput if its reply
            # channel is connected; else it's dropped/fallback).
            async def _route_reply(result):
                output_manager = getattr(core, "output_manager", None)
                if (wants_audio and output_manager is not None
                        and getattr(result, "should_speak", True) and (result.text or "")):
                    from ..core.interfaces.output import OutputModality
                    from ..intents.context_models import RequestContext
                    reply_ctx = RequestContext(session_id=session_id, client_id=registration.client_id)
                    await output_manager.deliver(result, reply_ctx, OutputModality.SPEECH)

            # ARCH-10: server-authoritative streaming path. If the device asks for mode="streaming" AND
            # the configured ASR does real endpointing (sherpa OnlineRecognizer), the SERVER marks
            # end-of-utterance from the model — no {"type":"end"} needed (the always-on / no-VAD case).
            # Any other case falls through to the device-signalled batch loop, the permanent floor.
            asr: Any = core.component_manager.get_component('asr') if core.component_manager else None
            if reg.get("mode") == "streaming" and asr is not None and getattr(asr, "supports_streaming", None) \
                    and asr.supports_streaming():
                # BUG-13 (re-scoped): the streaming path serves MULTIPLE utterances per
                # connection (batch-floor parity — each {"type":"end"} / idle force-finalize
                # ends one utterance and the loop re-arms), and a bounded client that stops
                # sending WITHOUT an end frame is force-finalized after the idle timeout
                # instead of hanging on an endpoint that bounded audio never triggers.
                disconnected = False

                async def _pcm_frames():
                    nonlocal disconnected
                    while True:
                        try:
                            msg = await asyncio.wait_for(
                                websocket.receive(), timeout=WS_STREAMING_IDLE_TIMEOUT_SECONDS)
                        except asyncio.TimeoutError:
                            return  # idle — force-finalize whatever was streamed (BUG-13)
                        if msg.get("type") == "websocket.disconnect":
                            disconnected = True
                            return
                        if msg.get("bytes") is not None:
                            yield msg["bytes"]
                        elif msg.get("text") is not None and (json.loads(msg["text"]) or {}).get("type") == "end":
                            return  # a device hard-finalize is still honored

                while not disconnected:
                    async for text, is_final in asr.transcribe_stream_segments(_pcm_frames()):
                        if not is_final:
                            await websocket.send_json({"type": "partial", "text": text})
                            continue
                        result = await core.workflow_manager.process_text_input(
                            text=text, session_id=session_id, wants_audio=False,
                            client_context=client_context)
                        # QUAL-55: canonical projection (supersedes the QUAL-54 metadata injection —
                        # `intent_name` is now a top-level key on every execution surface).
                        await websocket.send_json({"type": "response", **serialize_intent_result(result)})
                        await _route_reply(result)
                    # Utterance ended (end frame / idle / disconnect) — re-arm unless the
                    # client is gone. A fresh recognizer stream is created per utterance.
                return

            # Step 2 (batch floor) — utterance loop: accumulate binary PCM until an {"type":"end"}
            # frame, bounded by WS_MAX_UTTERANCE_SECONDS (BUG-17: force-finalize on overflow so a
            # client that never signals end can't grow the accumulator without limit).
            max_utterance_bytes = sample_rate * 2 * WS_MAX_UTTERANCE_SECONDS  # 16-bit mono PCM
            while True:
                frames = bytearray()
                overflow = False
                while True:
                    msg = await websocket.receive()
                    if msg.get("type") == "websocket.disconnect":
                        return
                    if msg.get("bytes") is not None:
                        frames.extend(msg["bytes"])
                        if len(frames) >= max_utterance_bytes:
                            overflow = True
                            logger.warning(
                                f"/ws/audio utterance exceeded the {WS_MAX_UTTERANCE_SECONDS}s cap "
                                f"({len(frames)} bytes) for client {registration.client_id} "
                                f"(session {session_id}) — force-finalizing (BUG-17)")
                            break
                    elif msg.get("text") is not None:
                        if (json.loads(msg["text"]) or {}).get("type") == "end":
                            break
                if not frames:
                    continue
                _audio_meta: Dict[str, Any] = {"source": "ws_audio", "client_id": registration.client_id}
                if overflow:
                    _audio_meta["overflow"] = True
                audio = AudioData(data=bytes(frames), timestamp=time.time(), sample_rate=sample_rate,
                                  channels=1, metadata=_audio_meta)
                result = await core.workflow_manager.process_audio_input(
                    audio_data=audio, session_id=session_id, wants_audio=False,
                    client_context=client_context)
                # QUAL-55: canonical projection (supersedes the QUAL-54 metadata injection —
                # `intent_name` is now a top-level key on every execution surface).
                await websocket.send_json({"type": "response", **serialize_intent_result(result)})
                await _route_reply(result)
        except WebSocketDisconnect:
            logger.debug(f"WS audio driving input disconnected (session {session_id})")
        except Exception as e:
            logger.error(f"WS audio driving input error (session {session_id}): {e}")
            try:
                await websocket.send_json({"type": "error", "error": str(e)})
            except Exception:
                pass

    # ARCH-15 PR-6b: gated observation tap. A debug client subscribes to the pipeline event bus and
    # receives a live, identity-filtered stream of {input.received, result.produced, output.delivered,
    # …}. Disabled unless system.observe_token is set; localhost-only unless observe_allow_remote.
    @router.websocket("/ws/observe")
    async def ws_observe(websocket: WebSocket):
        from fastapi import WebSocketDisconnect
        from ..core.observe import authorize_observer, subscribe_to_queue
        from ..core.event_bus import identity_filter, EventType

        await websocket.accept()
        sys_cfg = core.config.system
        client_host = websocket.client.host if websocket.client else None
        unsubscribe = None
        try:
            auth = json.loads(await websocket.receive_text())
            if not authorize_observer(client_host, auth.get("token"),
                                      configured_token=getattr(sys_cfg, "observe_token", None),
                                      allow_remote=getattr(sys_cfg, "observe_allow_remote", False)):
                await websocket.send_json({"type": "error", "error": "unauthorized"})
                await websocket.close()
                return
            if core.event_bus is None:
                await websocket.send_json({"type": "error", "error": "event bus unavailable"})
                await websocket.close()
                return

            f = auth.get("filter") or {}
            types = [EventType(t) for t in f.get("types", [])] or None
            ev_filter = identity_filter(session_id=f.get("session_id"), client_id=f.get("client_id"),
                                        room_name=f.get("room_name"), source=f.get("source"), types=types)
            queue, unsubscribe = subscribe_to_queue(core.event_bus, ev_filter)
            await websocket.send_json({"type": "subscribed"})
            while True:
                ev = await queue.get()
                await websocket.send_json({
                    "type": "event", "event": ev.type.value, "session_id": ev.session_id,
                    "client_id": ev.client_id, "room_name": ev.room_name, "source": ev.source,
                    "payload": ev.payload, "timestamp": ev.timestamp})
        except WebSocketDisconnect:
            logger.debug("WS observe tap disconnected")
        except Exception as e:
            logger.error(f"WS observe tap error: {e}")
            try:
                await websocket.send_json({"type": "error", "error": str(e)})
            except Exception:
                pass
        finally:
            if unsubscribe is not None:
                unsubscribe()

    # ARCH-15 PR-6c: web built-in-app push channel. The browser opens this WS and registers a
    # CallbackTextOutput on the shared OutputManager, keyed by a per-connection client_id. The app's
    # *sync* commands still go via POST /execute/command (the HTTP reply is the sync delivery); this
    # WS exists so DEFERRED results (a browser-set timer firing) can be PUSHED back — the OutputManager
    # pairs them by physical identity (client_id). Commands carry that client_id so the action's
    # physical_id resolves to it, and the deferred notification routes here.
    @router.websocket("/ws/output")
    async def ws_output(websocket: WebSocket):
        from fastapi import WebSocketDisconnect
        from ..outputs.text import CallbackTextOutput

        await websocket.accept()
        output_manager = getattr(core, "output_manager", None)
        out_cfg = getattr(getattr(core, "config", None), "outputs", None)  # ARCH-15 PR-7: config-driven
        if output_manager is None or (out_cfg is not None and not out_cfg.web_push):
            await websocket.send_json({"type": "error", "error": "web push output unavailable"})
            await websocket.close()
            return

        # First frame may supply a client_id; otherwise mint one (and hand it back so the app can
        # include it in its POST /execute/command calls for identity-addressed deferred delivery).
        client_id = None
        try:
            first = json.loads(await websocket.receive_text())
            client_id = first.get("client_id")
        except Exception:
            client_id = None
        if not client_id:
            client_id = f"web_{uuid.uuid4().hex[:8]}"

        async def _send(text: str) -> None:
            await websocket.send_json({"type": "message", "text": text})

        output = CallbackTextOutput(_send, name=client_id, origin=client_id)
        await output_manager.add_output(client_id, output)
        await websocket.send_json({"type": "connected", "client_id": client_id})
        try:
            while True:
                msg = await websocket.receive()
                if msg.get("type") == "websocket.disconnect":
                    break
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error(f"WS output channel error ({client_id}): {e}")
        finally:
            output_manager.remove_output(client_id)
            logger.debug(f"WS output channel deregistered ({client_id})")

    # ARCH-22 §4.2: the ESP32 reply channel. A satellite opens this WS and LISTENS; its `register-reply`
    # carries client_id + its output AudioContract. The server pairs a RemoteAudioOutput (origin_key ==
    # client_id) on the shared OutputManager, so a SPEECH result from that device routes back to it
    # (synthesize_to_stream → conform to the device's contract → speak_begin/PCM/speak_end). Disconnect
    # deregisters. The device-facing wire protocol is finalized in the firmware (esp32_satellite.md).
    @router.websocket("/ws/audio/reply")
    async def ws_audio_reply(websocket: WebSocket):
        from fastapi import WebSocketDisconnect
        from ..outputs.remote_audio import CallbackReplyChannel, RemoteAudioOutput
        from ..utils.audio_negotiation import AudioContract

        await websocket.accept()
        output_manager = getattr(core, "output_manager", None)
        negotiator = getattr(core, "audio_negotiator", None)
        tts = core.component_manager.get_component('tts') if core.component_manager else None
        if output_manager is None or negotiator is None or tts is None:
            await websocket.send_json({"type": "error", "error": "reply channel unavailable"})
            await websocket.close()
            return

        reg = json.loads(await websocket.receive_text())
        client_id = reg.get("client_id")
        if reg.get("type") != "register-reply" or not client_id:
            await websocket.send_json({"type": "error",
                                       "error": "first frame must be type=register-reply with client_id"})
            await websocket.close()
            return
        # ARCH-36 finding (b): same mTLS identity binding as /ws/audio — a cert can only
        # claim its own reply channel (it would otherwise receive another room's speech).
        cert_cn = _client_cert_cn(websocket.headers)
        if cert_cn is not None and cert_cn != client_id:
            await websocket.send_json({"type": "error",
                                       "error": f"client_id does not match certificate identity ({cert_cn})"})
            await websocket.close()
            return

        ao = reg.get("audio_out") or {}
        rate, ch = int(ao.get("rate", 22050)), int(ao.get("channels", 1))
        contract = AudioContract([rate], rate, ["pcm16"], "pcm16", ch)
        channel = CallbackReplyChannel(contract, websocket.send_json, websocket.send_bytes)
        output = RemoteAudioOutput(client_id, channel, tts, negotiator)
        await output_manager.add_output(client_id, output)
        await websocket.send_json({"type": "registered", "client_id": client_id})

        # ARCH-28 (D-6): the reply channel just came up — deliver any completion notices that
        # fired while this client was offline (e.g. a timer that rang during a satellite reboot).
        try:
            from ..core.notifications import get_notification_service
            await (await get_notification_service()).drain_undelivered([client_id])
        except Exception as e:
            logger.error(f"Undelivered-notice drain failed for {client_id}: {e}")
        try:
            while True:
                msg = await websocket.receive()
                if msg.get("type") == "websocket.disconnect":
                    break
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error(f"WS audio reply channel error ({client_id}): {e}")
        finally:
            channel.disconnect()
            output_manager.remove_output(client_id)
            logger.debug(f"WS audio reply channel deregistered ({client_id})")

    return router
