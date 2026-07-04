"""
Irene API Module

Centralized API definitions, schemas, and utilities for all
API endpoints (REST, WebSocket, etc.) across Irene components.
"""

from .schemas import (
    # Base schemas
    BaseAPIRequest,
    BaseAPIResponse,
    ErrorResponse,
    # ASR schemas
    ASRTranscribeRequest,
    ASRTranscribeResponse,
    ASRProvidersResponse,
    # TTS schemas
    TTSRequest,
    TTSResponse,
    TTSProvidersResponse,
    # NLU schemas
    NLURequest,
    IntentResponse,
    RoomAliasesResponse,
    # System schemas
    HealthResponse,
    ComponentInfo,
    SystemStatusResponse,
    CommandRequest,
    CommandResponse,
    # Configuration schemas
    ConfigUpdateResponse,
    ConfigValidationResponse,
    ConfigStatusResponse,
    # Trace execution schemas (Phase 7 - TODO16)
    PipelineStageTrace,
    ContextEvolution,
    PerformanceMetrics,
    ExecutionTrace,
    TraceCommandResponse,
)

__all__ = [
    # Base schemas
    "BaseAPIRequest", 
    "BaseAPIResponse",
    "ErrorResponse",
    # ASR schemas
    "ASRTranscribeRequest",
    "ASRTranscribeResponse", 
    "ASRProvidersResponse",
    # TTS schemas
    "TTSRequest",
    "TTSResponse",
    "TTSProvidersResponse",
    # NLU schemas
    "NLURequest",
    "IntentResponse",
    "RoomAliasesResponse",
    # System schemas
    "HealthResponse",
    "ComponentInfo",
    "SystemStatusResponse",
    "CommandRequest",
    "CommandResponse",
    # Configuration schemas
    "ConfigUpdateResponse",
    "ConfigValidationResponse",
    "ConfigStatusResponse",
    # Trace execution schemas (Phase 7 - TODO16)
    "PipelineStageTrace",
    "ContextEvolution", 
    "PerformanceMetrics",
    "ExecutionTrace",
    "TraceCommandResponse"
]
