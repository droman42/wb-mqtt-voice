"""
Centralized API Schemas for Irene Voice Assistant

This module contains all Pydantic schemas for API endpoints across components,
including both HTTP REST APIs and WebSocket message formats.

Organization:
- Base classes for common patterns
- Component-specific message schemas  
- Request/Response models for HTTP APIs
- WebSocket message formats for real-time communication

Follows AsyncAPI and OpenAPI standards for documentation generation.
"""

# QUAL-4d: pyright treats class variables as invariant, so a Pydantic subclass that
# narrows a base field (e.g. `success: Literal[False]`, discriminator `type: Literal[...]`)
# or declares its own inner `class Config` trips reportIncompatibleVariableOverride. That
# narrowing is by-design in Pydantic (it powers the discriminated response unions) and is
# not a bug, so the rule is scoped-off for this module of response/request DTOs only — it
# stays enforced everywhere else in the codebase (user decision, 2026-06-06).
# pyright: reportIncompatibleVariableOverride=false

import time
from typing import Literal, Optional, Dict, Any, List
from pydantic import BaseModel, Field


# ============================================================
# BASE API SCHEMAS
# ============================================================

class BaseAPIMessage(BaseModel):
    """Base class for all API messages"""
    type: str = Field(description="Message type identifier")
    timestamp: float = Field(
        default_factory=time.time,
        description="Unix timestamp when message was created"
    )

    class Config:
        json_encoders = {
            float: lambda v: round(v, 3)  # Round timestamps to milliseconds
        }


class BaseAPIRequest(BaseModel):
    """Base class for API request models"""
    pass


class BaseAPIResponse(BaseModel):
    """Base class for API response models"""
    success: bool = Field(description="Whether the operation was successful")
    timestamp: float = Field(
        default_factory=time.time,
        description="Unix timestamp when response was generated"
    )

    class Config:
        json_encoders = {
            float: lambda v: round(v, 3)
        }


class ErrorResponse(BaseAPIResponse):
    """Standard error response format"""
    success: Literal[False] = Field(default=False)
    error: str = Field(description="Error message describing what went wrong")
    error_code: Optional[str] = Field(
        default=None,
        description="Machine-readable error code"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "success": False,
                    "error": "Provider not available",
                    "error_code": "PROVIDER_UNAVAILABLE",
                    "timestamp": 1704067200.123
                }
            ]
        }


# ============================================================
# ASR (AUTOMATIC SPEECH RECOGNITION) SCHEMAS
# ============================================================

class AudioChunkMessage(BaseAPIMessage):
    """
    WebSocket message containing audio data for real-time transcription
    
    Sent by clients to ASR WebSocket endpoints for streaming speech recognition.
    """
    type: Literal["audio_chunk"] = Field(
        default="audio_chunk",
        description="Message type identifier"
    )
    data: str = Field(
        description="Base64-encoded audio data (PCM, 16kHz, 16-bit, mono recommended)",
        json_schema_extra={"example": "UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqF..."}    )
    language: Optional[str] = Field(
        default="ru",
        description="Language code for transcription (ISO 639-1 format)",
        json_schema_extra={"example": "ru"}    )
    provider: Optional[str] = Field(
        default=None,
        description="Specific ASR provider to use (optional, uses default if not specified)",
        json_schema_extra={"example": "whisper"}    )
    sample_rate: Optional[int] = Field(
        default=16000,
        description="Audio sample rate in Hz (optional, defaults to 16000Hz)",
        json_schema_extra={"example": 16000},        ge=8000,
        le=192000
    )
    channels: Optional[int] = Field(
        default=1,
        description="Number of audio channels (optional, defaults to 1=mono)",
        json_schema_extra={"example": 1},        ge=1,
        le=8
    )
    format: Optional[str] = Field(
        default="pcm16",
        description="Audio format specification (optional, defaults to pcm16)",
        json_schema_extra={"example": "pcm16"}    )
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "type": "audio_chunk",
                    "data": "UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqF...",
                    "language": "ru",
                    "provider": "whisper",
                    "sample_rate": 16000,
                    "channels": 1,
                    "format": "pcm16",
                    "timestamp": 1704067200.123
                },
                {
                    "type": "audio_chunk",
                    "data": "UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqF...",
                    "language": "en",
                    "sample_rate": 44100,
                    "channels": 2,
                    "format": "pcm16",
                    "timestamp": 1704067200.456
                }
            ]
        }


class TranscriptionResultMessage(BaseAPIMessage):
    """
    WebSocket message containing transcription results
    
    Sent by ASR WebSocket endpoints to clients with speech recognition results.
    """
    type: Literal["transcription_result"] = Field(
        default="transcription_result",
        description="Message type identifier"
    )
    text: str = Field(
        description="Transcribed text from the audio chunk",
        json_schema_extra={"example": "привет как дела"}    )
    provider: str = Field(
        description="ASR provider that performed the transcription",
        json_schema_extra={"example": "whisper"}    )
    language: str = Field(
        description="Language code used for transcription",
        json_schema_extra={"example": "ru"}    )
    confidence: Optional[float] = Field(
        default=None,
        description="Confidence score for the transcription (0.0-1.0, if available)",
        ge=0.0,
        le=1.0,
        json_schema_extra={"example": 0.95}    )
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "type": "transcription_result",
                    "text": "привет как дела",
                    "provider": "whisper",
                    "language": "ru",
                    "timestamp": 1704067200.123,
                    "confidence": 0.95
                },
                {
                    "type": "transcription_result",
                    "text": "hello how are you",
                    "provider": "whisper",
                    "language": "en",
                    "timestamp": 1704067201.456
                }
            ]
        }


class TranscriptionErrorMessage(BaseAPIMessage):
    """
    WebSocket message containing transcription error information
    
    Sent by ASR WebSocket endpoints when speech recognition fails.
    """
    type: Literal["error"] = Field(
        default="error",
        description="Message type identifier"
    )
    error: str = Field(
        description="Error message describing what went wrong",
        json_schema_extra={"example": "Audio format not supported"}    )
    provider: Optional[str] = Field(
        default=None,
        description="ASR provider that encountered the error (if known)",
        json_schema_extra={"example": "whisper"}    )
    recoverable: bool = Field(
        default=True,
        description="Whether the client can retry the request",
        json_schema_extra={"example": True}    )
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "type": "error",
                    "error": "Audio format not supported",
                    "timestamp": 1704067200.123,
                    "provider": "whisper",
                    "recoverable": True
                },
                {
                    "type": "error",
                    "error": "Provider temporarily unavailable",
                    "timestamp": 1704067201.456,
                    "recoverable": True
                }
            ]
        }


class BinaryAudioSessionMessage(BaseAPIMessage):
    """
    WebSocket session configuration for binary audio streaming
    
    Initial JSON message sent to configure binary audio streaming session.
    After this message, all subsequent frames are raw binary PCM audio data.
    """
    type: Literal["session_config"] = Field(
        default="session_config",
        description="Message type identifier"
    )
    sample_rate: int = Field(
        default=16000,
        description="Audio sample rate in Hz (16000 recommended for ASR)",
        json_schema_extra={"example": 16000},        ge=8000,
        le=48000
    )
    channels: int = Field(
        default=1,
        description="Number of audio channels (1=mono, 2=stereo)",
        json_schema_extra={"example": 1},        ge=1,
        le=2
    )
    format: str = Field(
        default="pcm_s16le",
        description="Audio format specification (pcm_s16le = 16-bit signed little-endian PCM)",
        json_schema_extra={"example": "pcm_s16le"}    )
    language: Optional[str] = Field(
        default="ru",
        description="Language code for transcription (ISO 639-1 format)",
        json_schema_extra={"example": "ru"}    )
    provider: Optional[str] = Field(
        default=None,
        description="Specific ASR provider to use (optional, uses default if not specified)",
        json_schema_extra={"example": "whisper"}    )
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "type": "session_config",
                    "sample_rate": 16000,
                    "channels": 1,
                    "format": "pcm_s16le",
                    "language": "ru",
                    "provider": "whisper",
                    "timestamp": 1704067200.123
                },
                {
                    "type": "session_config",
                    "sample_rate": 16000,
                    "channels": 1,
                    "format": "pcm_s16le",
                    "language": "en",
                    "timestamp": 1704067200.456
                }
            ]
        }


class BinaryAudioStreamMessage(BaseAPIMessage):
    """
    Documentation schema for binary audio data frames
    
    Note: This schema is for AsyncAPI documentation only. In actual implementation,
    audio data is sent as raw binary WebSocket frames (not JSON) after the initial
    session configuration message.
    
    Binary Format Specification:
    - Raw PCM audio data as configured in session_config
    - Default: 16-bit signed little-endian, mono, 16kHz
    - Frame size: Variable (typically 160-1600 samples = 10-100ms audio)
    - No headers or metadata - pure audio samples
    """
    type: Literal["binary_audio"] = Field(
        default="binary_audio",
        description="Message type identifier (documentation only)"
    )
    description: str = Field(
        default="Raw PCM audio data as binary WebSocket frame",
        description="Binary audio data stream (not JSON - sent as WebSocket binary frames)"
    )
    format_specification: str = Field(
        default="16-bit signed little-endian PCM samples, no headers",
        description="Technical format of the binary data"
    )
    
    class Config:
        json_schema_extra = {
            "description": "This schema documents binary audio frames. Actual data is sent as WebSocket binary frames.",
            "x-binary-format": {
                "type": "binary",
                "format": "pcm_s16le",
                "sample_rate": 16000,
                "channels": 1,
                "frame_size": "variable",
                "notes": "Raw audio samples without headers or metadata"
            },
            "examples": [
                {
                    "type": "binary_audio", 
                    "description": "Raw PCM audio data as binary WebSocket frame",
                    "format_specification": "16-bit signed little-endian PCM samples, no headers",
                    "timestamp": 1704067200.123
                }
            ]
        }


class BinaryWebSocketProtocol(BaseAPIMessage):
    """
    Complete protocol documentation for binary WebSocket streaming
    
    This schema documents the full protocol flow for binary audio streaming:
    1. Client sends BinaryAudioSessionMessage (JSON) for configuration
    2. Server responds with session_ready confirmation (JSON)
    3. Client streams BinaryAudioStreamMessage frames (raw binary)
    4. Server responds with TranscriptionResultMessage (JSON)
    
    This wrapper schema allows AsyncAPI to properly document the mixed
    JSON/binary protocol while maintaining tool compatibility.
    """
    type: Literal["binary_websocket_protocol"] = Field(
        default="binary_websocket_protocol",
        description="Protocol documentation identifier"
    )
    session_config: BinaryAudioSessionMessage = Field(
        description="Initial session configuration sent as JSON message"
    )
    audio_streams: List[BinaryAudioStreamMessage] = Field(
        description="Subsequent binary audio frames (sent as WebSocket binary frames, not JSON)",
        default_factory=list
    )
    
    class Config:
        json_schema_extra = {
            "description": "Complete binary WebSocket streaming protocol documentation",
            "protocol_flow": [
                "1. Client → Server: BinaryAudioSessionMessage (JSON)",
                "2. Server → Client: session_ready confirmation (JSON)", 
                "3. Client → Server: Raw PCM binary frames (BinaryAudioStreamMessage format)",
                "4. Server → Client: TranscriptionResultMessage (JSON) or error (JSON)"
            ],
            "notes": [
                "Only the session_config is sent as JSON",
                "All audio_streams are sent as WebSocket binary frames",
                "This schema is for documentation - actual implementation uses mixed message types"
            ],
            "examples": [
                {
                    "type": "binary_websocket_protocol",
                    "session_config": {
                        "type": "session_config",
                        "sample_rate": 16000,
                        "channels": 1,
                        "format": "pcm_s16le",
                        "language": "en",
                        "provider": "whisper",
                        "timestamp": 1704067200.123
                    },
                    "audio_streams": [
                        {
                            "type": "binary_audio",
                            "description": "Raw PCM audio data as binary WebSocket frame",
                            "format_specification": "16-bit signed little-endian PCM samples, no headers",
                            "timestamp": 1704067200.200
                        }
                    ],
                    "timestamp": 1704067200.123
                }
            ]
        }


# ASR HTTP API Schemas
class ASRTranscribeRequest(BaseAPIRequest):
    """HTTP request for file-based transcription"""
    # Note: File upload handled by FastAPI UploadFile
    provider: Optional[str] = Field(
        default=None,
        description="Specific ASR provider to use"
    )
    language: str = Field(
        default="ru",
        description="Language code for transcription"
    )
    enhance: bool = Field(
        default=False,
        description="Whether to enhance audio quality before transcription"
    )


class ASRTranscribeResponse(BaseAPIResponse):
    """HTTP response for file-based transcription"""
    text: str = Field(description="Transcribed text")
    provider: str = Field(description="ASR provider used")
    language: str = Field(description="Language used for transcription")
    confidence: Optional[float] = Field(
        default=None,
        description="Confidence score if available"
    )
    processing_time: Optional[float] = Field(
        default=None,
        description="Processing time in seconds"
    )


class ASRProvidersResponse(BaseAPIResponse):
    """Response containing available ASR providers"""
    providers: Dict[str, Dict[str, Any]] = Field(
        description="Available providers and their capabilities"
    )
    default: str = Field(description="Default provider name")


# ============================================================
# TTS (TEXT-TO-SPEECH) SCHEMAS
# ============================================================

class AudioConfigRequest(BaseModel):
    """Audio output configuration for TTS synthesis"""
    sample_rate: int = Field(
        default=16000,
        description="Output sample rate in Hz",
        ge=8000,
        le=192000,
        json_schema_extra={"example": 16000}    )
    channels: int = Field(
        default=1,
        description="Number of audio channels (1=mono, 2=stereo)",
        ge=1,
        le=2,
        json_schema_extra={"example": 1}    )
    format: str = Field(
        default="pcm16",
        description="Audio format specification",
        json_schema_extra={"example": "pcm16"}    )


class TTSRequest(BaseAPIRequest):
    """HTTP request for text-to-speech synthesis"""
    text: str = Field(description="Text to synthesize")
    provider: Optional[str] = Field(
        default=None,
        description="Specific TTS provider to use"
    )
    speaker: Optional[str] = Field(
        default=None,
        description="Speaker voice to use"
    )
    language: str = Field(
        description="Language code for synthesis (ISO 639-1 format)",
        json_schema_extra={"example": "en"}    )
    audio_config: Optional[AudioConfigRequest] = Field(
        default=None,
        description="Audio output configuration (optional, uses defaults if not specified)"
    )


class TTSResponse(BaseAPIResponse):
    """HTTP response for text-to-speech synthesis"""
    provider: str = Field(description="TTS provider used")
    text: str = Field(description="Original text")
    audio_content: Optional[str] = Field(
        default=None,
        description="Base64 encoded audio data"
    )
    audio_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Audio format metadata (sample_rate, channels, format, duration_ms, file_size)"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if synthesis failed"
    )


class TTSProvidersResponse(BaseAPIResponse):
    """Response containing available TTS providers"""
    providers: Dict[str, Any] = Field(
        description="Available providers and their capabilities"
    )
    default: str = Field(description="Default provider name")


# ============================================================
# NLU (NATURAL LANGUAGE UNDERSTANDING) SCHEMAS
# ============================================================

class NLURequest(BaseAPIRequest):
    """HTTP request for intent recognition"""
    text: str = Field(description="Text to analyze for intent")
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Context information for intent recognition"
    )
    provider: Optional[str] = Field(
        default=None,
        description="Specific NLU provider to use"
    )


class IntentResponse(BaseAPIResponse):
    """HTTP response containing recognized intent"""
    name: str = Field(description="Intent name")
    entities: Dict[str, Any] = Field(description="Extracted entities")
    confidence: float = Field(description="Recognition confidence score")
    provider: str = Field(description="NLU provider used")
    domain: Optional[str] = Field(
        default=None,
        description="Intent domain"
    )
    action: Optional[str] = Field(
        default=None,
        description="Intent action"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session identifier from the conversation context"
    )
    room_context: bool = Field(
        default=False,
        description="Whether the request carried room/client context"
    )


class NLUConfigResponse(BaseAPIResponse):
    """HTTP response for NLU configuration"""
    confidence_threshold: float = Field(description="Current confidence threshold")
    fallback_intent: str = Field(description="Fallback intent name")
    default_provider: Optional[str] = Field(description="Default NLU provider")
    available_providers: List[str] = Field(description="List of available providers")


class NLUProvidersResponse(BaseAPIResponse):
    """Response containing available NLU providers"""
    providers: Dict[str, Dict[str, Any]] = Field(
        description="Available providers and their capabilities"
    )
    default: Optional[str] = Field(description="Default provider name")


class RoomAliasesResponse(BaseAPIResponse):
    """Response model for room aliases endpoint"""
    room_aliases: List[str] = Field(
        description="List of valid room IDs: ['kitchen', 'living_room', ...]"
    )
    language: str = Field(
        description="Language used for response"
    )
    fallback_language: str = Field(
        description="Fallback language if requested not available"
    )
    total_count: int = Field(
        description="Number of room aliases returned"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "room_aliases": ["kitchen", "living_room", "bedroom", "bathroom"],
                "language": "en",
                "fallback_language": "en",
                "total_count": 4,
                "timestamp": 1704067200.123
            }
        }


# ============================================================
# SYSTEM/HEALTH SCHEMAS
# ============================================================

class HealthResponse(BaseAPIResponse):
    """System health check response"""
    status: Literal["healthy", "unhealthy"] = Field(description="System status")
    version: str = Field(description="System version")
    uptime: Optional[float] = Field(
        default=None,
        description="System uptime in seconds"
    )


class ComponentInfo(BaseModel):
    """Information about a system component"""
    name: str = Field(description="Component name")
    status: str = Field(description="Component status")
    version: Optional[str] = Field(default=None, description="Component version")
    capabilities: List[str] = Field(
        default_factory=list,
        description="Component capabilities"
    )


class SystemStatusResponse(BaseAPIResponse):
    """Comprehensive system status response"""
    system: str = Field(description="Overall system status")
    version: str = Field(description="System version")
    mode: str = Field(description="Operating mode")
    uptime: float = Field(description="System uptime in seconds")
    components: Dict[str, ComponentInfo] = Field(
        description="Individual component status"
    )


# ============================================================
# COMMAND EXECUTION SCHEMAS
# ============================================================

class CommandRequest(BaseAPIRequest):
    """Request to execute a command with optional room context"""
    command: str = Field(description="Command text to execute")
    room_alias: Optional[str] = Field(
        default=None,
        description="Optional room identifier for room-scoped execution (e.g., 'kitchen', 'living_room')"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional command metadata"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "command": "turn off the lights",
                "room_alias": "kitchen",
                "metadata": {"source": "mobile_app"}
            }
        }


class CommandResponse(BaseAPIResponse):
    """Response from command execution"""
    response: str = Field(description="Command execution result")
    session_id: str = Field(description="Session ID used for execution")
    room_alias: Optional[str] = Field(default=None, description="Room alias used for execution")
    error: Optional[str] = Field(
        default=None,
        description="Error message if command failed"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional response metadata"
    )


# ============================================================
# TRACE EXECUTION SCHEMAS (PHASE 7 - TODO16)
# ============================================================

class PipelineStageTrace(BaseModel):
    """Detailed trace information for a single pipeline stage"""
    stage: str = Field(description="Name of the pipeline stage")
    input_data: Any = Field(description="Input data for this stage")
    output_data: Any = Field(description="Output data from this stage")
    metadata: Dict[str, Any] = Field(description="Stage-specific metadata and processing details")
    processing_time_ms: float = Field(description="Processing time for this stage in milliseconds")
    timestamp: float = Field(default_factory=time.time, description="Unix timestamp when stage was executed")


class ContextEvolution(BaseModel):
    """Context state changes during pipeline execution"""
    before: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Conversation context state before processing"
    )
    after: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Conversation context state after processing"
    )
    changes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of changes between before and after states"
    )


class PerformanceMetrics(BaseModel):
    """Performance metrics for pipeline execution"""
    total_processing_time_ms: float = Field(description="Total processing time in milliseconds")
    stage_breakdown: Dict[str, float] = Field(
        default_factory=dict,
        description="Processing time breakdown by stage"
    )
    total_stages: int = Field(description="Total number of stages executed")


class ExecutionTrace(BaseModel):
    """Complete pipeline execution trace"""
    request_id: str = Field(description="Unique identifier for this trace request")
    pipeline_stages: List[PipelineStageTrace] = Field(
        default_factory=list,
        description="Detailed trace of each pipeline stage"
    )
    context_evolution: ContextEvolution = Field(
        default_factory=ContextEvolution,
        description="How conversation context changed during execution"
    )
    performance_metrics: PerformanceMetrics = Field(
        description="Performance timing and metrics"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if trace collection failed"
    )


class TraceCommandResponse(BaseAPIResponse):
    """Response for trace command execution with complete pipeline visibility"""
    final_result: Dict[str, Any] = Field(
        description="Normal command execution result (same as CommandResponse)"
    )
    execution_trace: ExecutionTrace = Field(
        description="Complete pipeline execution trace with detailed stage information"
    )
    session_id: str = Field(description="Session ID used for execution")
    room_alias: Optional[str] = Field(default=None, description="Room alias used for execution")
    error: Optional[str] = Field(
        default=None,
        description="Error message if command execution failed"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional trace metadata"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "success": True,
                    "final_result": {
                        "text": "Playing music",
                        "success": True,
                        "metadata": {"intent": "audio.play"},
                        "confidence": 0.95
                    },
                    "execution_trace": {
                        "request_id": "trace-abc123",
                        "pipeline_stages": [
                            {
                                "stage": "text_processing",
                                "input_data": "play music",
                                "output_data": "play music",
                                "metadata": {"normalizers_applied": []},
                                "processing_time_ms": 2.3,
                                "timestamp": 1704067200.123
                            }
                        ],
                        "context_evolution": {
                            "before": {"active_actions": {}},
                            "after": {"active_actions": {"audio": "play_music"}},
                            "changes": {"active_actions_added": ["audio"]}
                        },
                        "performance_metrics": {
                            "total_processing_time_ms": 45.2,
                            "stage_breakdown": {"text_processing": 2.3, "nlu_cascade": 15.7},
                            "total_stages": 3
                        }
                    },
                    "timestamp": 1704067200.123
                }
            ]
        }


# ============================================================
# LLM (LARGE LANGUAGE MODEL) SCHEMAS
# ============================================================

class ChatMessage(BaseModel):
    """Individual message in a chat conversation"""
    role: Literal["user", "assistant", "system"] = Field(
        description="Role of the message sender",
        json_schema_extra={"example": "user"}    )
    content: str = Field(
        description="Content of the message",
        json_schema_extra={"example": "Hello, how can you help me today?"}    )


class LLMEnhanceRequest(BaseAPIRequest):
    """HTTP request for text enhancement using LLM"""
    text: str = Field(
        description="Text to enhance or improve",
        json_schema_extra={"example": "The weather is very good today"}    )
    task: str = Field(
        default="improve",
        description="Enhancement task type",
        json_schema_extra={"example": "improve"}    )
    provider: Optional[str] = Field(
        default=None,
        description="Specific LLM provider to use",
        json_schema_extra={"example": "openai"}    )
    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional provider-specific parameters"
    )


class LLMEnhanceResponse(BaseAPIResponse):
    """HTTP response for text enhancement"""
    original_text: str = Field(description="Original input text")
    enhanced_text: str = Field(description="Enhanced/improved text")
    task: str = Field(description="Enhancement task that was performed")
    provider: str = Field(description="LLM provider used")


class LLMChatRequest(BaseAPIRequest):
    """HTTP request for chat completion"""
    messages: List[ChatMessage] = Field(
        description="List of chat messages in conversation",
        json_schema_extra={"example": [
            {"role": "user", "content": "What is artificial intelligence?"}
        ]}
    )
    provider: Optional[str] = Field(
        default=None,
        description="Specific LLM provider to use",
        json_schema_extra={"example": "openai"}    )
    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional provider-specific parameters like temperature, max_tokens"
    )


class LLMChatResponse(BaseAPIResponse):
    """HTTP response for chat completion"""
    response: str = Field(description="Generated response from the LLM")
    provider: str = Field(description="LLM provider used")
    usage: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Token usage statistics if available"
    )



class LLMProvidersResponse(BaseAPIResponse):
    """Response containing available LLM providers"""
    providers: Dict[str, Dict[str, Any]] = Field(
        description="Available providers and their capabilities"
    )
    default: str = Field(description="Default provider name")


# ============================================================
# INTENT SYSTEM SCHEMAS  
# ============================================================

# ============================================================
# DONATION MANAGEMENT SCHEMAS
# ============================================================

class DonationMetadata(BaseModel):
    """Metadata about a donation file"""
    handler_name: str = Field(description="Handler name (filename without .json)")
    domain: str = Field(description="Handler domain from donation")
    description: str = Field(description="Donation description")
    methods_count: int = Field(description="Number of method donations")
    global_parameters_count: int = Field(description="Number of global parameters")
    file_size: int = Field(description="File size in bytes")
    last_modified: float = Field(description="Unix timestamp of last modification")


class ValidationError(BaseModel):
    """Validation error details"""
    type: str = Field(description="Error type (schema, method_existence, etc.)")
    message: str = Field(description="Human-readable error message")
    path: Optional[str] = Field(default=None, description="JSON path where error occurred")
    line: Optional[int] = Field(default=None, description="Line number if applicable")


class ValidationWarning(BaseModel):
    """Validation warning details"""
    type: str = Field(description="Warning type")
    message: str = Field(description="Human-readable warning message")
    path: Optional[str] = Field(default=None, description="JSON path where warning occurred")


# ============================================================
# LEGACY DONATION SCHEMAS REMOVED (Phase 3 Cleanup)
# ============================================================
# Old single-file donation request/response models removed:
# - DonationUpdateRequest
# - DonationValidationRequest 
# - DonationListResponse
# - DonationContentResponse
# - DonationUpdateResponse
# - DonationValidationResponse
#
# Replaced by language-aware v2 endpoints below


class DonationSchemaResponse(BaseAPIResponse):
    """Response for donation JSON schema"""
    json_schema: Dict[str, Any] = Field(description="JSON schema for donation structure")
    schema_version: str = Field(description="Schema version")
    supported_versions: List[str] = Field(description="Supported schema versions")


# ============================================================
# LANGUAGE-AWARE DONATION SCHEMAS (Phase 3)
# ============================================================

class HandlerLanguageInfo(BaseModel):
    """Information about a handler's language support"""
    handler_name: str = Field(description="Handler name")
    languages: List[str] = Field(description="Available languages")
    total_languages: int = Field(description="Language count")
    supported_languages: List[str] = Field(description="From system config")
    default_language: str = Field(description="System default language")


class DonationHandlerListResponse(BaseAPIResponse):
    """Response for listing handlers with language info"""
    handlers: List[HandlerLanguageInfo] = Field(description="List of handlers with language info")
    total_handlers: int = Field(description="Total number of handlers")


class CrossLanguageValidation(BaseModel):
    """Cross-language validation results"""
    parameter_consistency: bool = Field(description="Whether parameters are consistent across languages")
    missing_methods: List[str] = Field(description="Methods missing in some language files")
    extra_methods: List[str] = Field(description="Extra methods in some language files")


class LanguageDonationMetadata(BaseModel):
    """Metadata for a language-specific donation file"""
    file_path: str = Field(description="e.g., 'conversation_handler/en.json'")
    language: str = Field(description="Language code")
    file_size: int = Field(description="File size in bytes")
    last_modified: float = Field(description="Last modification timestamp")


class DonationContractResponse(BaseAPIResponse):
    """QUAL-29 v1.1 (QUAL-39): the language-neutral donation contract for a handler.

    The `contract` body is a passthrough of `contract.json` — validated against the
    canonical JSON Schema `assets/donation_contract_v1.1.json` and kept as a free dict
    here so the editor round-trips it losslessly (the schema allows additionalProperties).
    Parallel to `LanguageDonationContentResponse`; the strong contract *type* for
    config-ui is generated from the JSON Schema, the envelope from this model.
    """
    handler_name: str = Field(description="Handler name")
    contract: Dict[str, Any] = Field(description="Language-neutral contract (schema: donation_contract_v1.1.json)")
    available_languages: List[str] = Field(description="Languages with phrasing files for this handler")


class DonationContractUpdateResponse(BaseAPIResponse):
    """QUAL-29 v1.1 (QUAL-39): result of validating + saving a handler's contract.json."""
    handler_name: str = Field(description="Handler name")
    validation_passed: bool = Field(description="Whether contract validation passed")
    reload_triggered: bool = Field(description="Whether the unified donation reload was triggered")
    backup_created: bool = Field(default=False, description="Whether a backup of contract.json was created")
    errors: List[ValidationError] = Field(default=[], description="Validation errors")
    warnings: List[ValidationWarning] = Field(default=[], description="Validation warnings")


class LanguageDonationContentResponse(BaseAPIResponse):
    """Response for language-specific donation content retrieval"""
    handler_name: str = Field(description="Handler name")
    language: str = Field(description="Current language")
    donation_data: Dict[str, Any] = Field(description="Complete donation JSON content")
    metadata: LanguageDonationMetadata = Field(description="File metadata")
    available_languages: List[str] = Field(description="Other available languages")
    cross_language_validation: CrossLanguageValidation = Field(description="Cross-language checks")


class LanguageDonationUpdateRequest(BaseAPIRequest):
    """Request to update a language-specific donation file"""
    donation_data: Dict[str, Any] = Field(description="Complete donation JSON data")
    validate_before_save: bool = Field(default=True, description="Whether to validate before saving")
    trigger_reload: bool = Field(default=True, description="Whether to trigger reload after save")


class LanguageDonationUpdateResponse(BaseAPIResponse):
    """Response for language-specific donation update operation"""
    handler_name: str = Field(description="Updated handler name")
    language: str = Field(description="Updated language")
    validation_passed: bool = Field(description="Whether validation passed")
    reload_triggered: bool = Field(description="Whether unified donation reload was triggered")
    backup_created: bool = Field(description="Whether backup was created")
    errors: List[ValidationError] = Field(default=[], description="Validation errors")
    warnings: List[ValidationWarning] = Field(default=[], description="Validation warnings")


class LanguageDonationValidationRequest(BaseAPIRequest):
    """Request to validate language-specific donation data without saving"""
    donation_data: Dict[str, Any] = Field(description="Donation data to validate")


class LanguageDonationValidationResponse(BaseAPIResponse):
    """Response for language-specific donation validation operation"""
    handler_name: str = Field(description="Handler name being validated")
    language: str = Field(description="Language being validated")
    is_valid: bool = Field(description="Whether donation is valid")
    errors: List[ValidationError] = Field(default=[], description="Validation errors")
    warnings: List[ValidationWarning] = Field(default=[], description="Validation warnings")
    validation_types: List[str] = Field(description="Types of validation performed")


class CreateLanguageRequest(BaseAPIRequest):
    """Request to create a new language file for a handler"""
    copy_from: Optional[str] = Field(default=None, description="Language to copy from")
    use_template: bool = Field(default=False, description="Use empty template instead of copying")


class CreateLanguageResponse(BaseAPIResponse):
    """Response for language creation operation"""
    handler_name: str = Field(description="Handler name")
    language: str = Field(description="Created language")
    created: bool = Field(description="Whether language file was created")
    copied_from: Optional[str] = Field(default=None, description="Language copied from")


class DeleteLanguageResponse(BaseAPIResponse):
    """Response for language deletion operation"""
    handler_name: str = Field(description="Handler name")
    language: str = Field(description="Deleted language")
    deleted: bool = Field(description="Whether language file was deleted")


class ReloadDonationResponse(BaseAPIResponse):
    """Response for unified donation reload operation"""
    handler_name: str = Field(description="Handler name")
    reloaded: bool = Field(description="Whether unified donation was reloaded")
    merged_languages: List[str] = Field(description="Languages that were merged")


# ============================================================
# CROSS-LANGUAGE VALIDATION SCHEMAS (Phase 4)
# ============================================================

class ValidationReportSchema(BaseModel):
    """Schema for parameter consistency validation report"""
    handler_name: str = Field(description="Handler name that was validated")
    languages_checked: List[str] = Field(description="Languages that were included in validation")
    parameter_consistency: bool = Field(description="Whether parameters are consistent across languages")
    missing_parameters: List[str] = Field(description="Parameters missing in some languages (format: 'language: method.parameter')")
    extra_parameters: List[str] = Field(description="Extra parameters in some languages")
    type_mismatches: List[str] = Field(description="Parameter type mismatches across languages")
    warnings: List[str] = Field(description="Validation warnings")
    timestamp: float = Field(default_factory=time.time, description="Validation timestamp")


class CompletenessReportSchema(BaseModel):
    """Schema for method completeness validation report"""
    handler_name: str = Field(description="Handler name that was validated")
    languages_checked: List[str] = Field(description="Languages that were included in validation")
    method_completeness: bool = Field(description="Whether all methods exist in all languages")
    missing_methods: List[str] = Field(description="Methods missing in some languages (format: 'language: method_key')")
    extra_methods: List[str] = Field(description="Extra methods in some languages")
    all_methods: List[str] = Field(description="All unique method keys across languages")
    method_counts_by_language: Dict[str, int] = Field(description="Method count per language")
    warnings: List[str] = Field(description="Validation warnings")
    timestamp: float = Field(default_factory=time.time, description="Validation timestamp")


class CrossLanguageValidationRequest(BaseAPIRequest):
    """Request for cross-language validation"""
    validation_type: str = Field(
        description="Type of validation to perform",
        json_schema_extra={"example": "parameters"}    )


class CrossLanguageValidationResponse(BaseAPIResponse):
    """Response for cross-language validation"""
    validation_type: str = Field(description="Type of validation performed")
    parameter_report: Optional[ValidationReportSchema] = Field(
        default=None,
        description="Parameter consistency report"
    )
    completeness_report: Optional[CompletenessReportSchema] = Field(
        default=None,
        description="Method completeness report"
    )


# QUAL-43: SyncParameters{Request,Response}, SuggestTranslations{Request,Response},
# TranslationSuggestionsSchema and MissingPhraseInfo removed — parameter sync is gone (params are
# single-source under v1.1) and rule-based suggest-translations is superseded by the LLM translate service.


# ============================================================
# CONTRACT↔CODE WIRING VALIDATION SCHEMAS (QUAL-42)
# ============================================================

class ContractWiringReportSchema(BaseModel):
    """Per-handler contract↔code reconciliation result."""
    handler_name: str = Field(description="Handler (donation) name")
    handler_class: Optional[str] = Field(default=None, description="Resolved IntentHandler class name")
    errors: List[str] = Field(default_factory=list, description="Fatal: contract methods not wired in the handler")
    warnings: List[str] = Field(default_factory=list, description="Soft: unread params / undeclared handler methods")
    methods_checked: int = Field(default=0, description="Number of contract methods checked")
    params_checked: int = Field(default=0, description="Number of contract parameters checked")


class ContractValidationResponse(BaseAPIResponse):
    """System-wide contract↔code wiring report (QUAL-42), as computed at startup / on demand."""
    ok: bool = Field(description="True when no handler has a fatal (unwired) error")
    total_errors: int = Field(description="Total fatal wiring errors across all handlers")
    total_warnings: int = Field(description="Total soft warnings across all handlers")
    handlers: List[ContractWiringReportSchema] = Field(default_factory=list, description="Per-handler reports")


# ============================================================
# LLM-BACKED TRANSLATION VALIDATION & SERVICE SCHEMAS (QUAL-42)
# ============================================================

class TranslationIssueSchema(BaseModel):
    """A single cross-language translation problem found by the LLM."""
    language: str = Field(description="Language the issue concerns")
    method_key: str = Field(description="method_name#intent_suffix the issue concerns ('' if handler-wide)")
    severity: str = Field(description="'error' | 'warning' | 'info'")
    message: str = Field(description="Human-readable description of the inconsistency")


class TranslationValidationRequest(BaseAPIRequest):
    """Request to LLM-validate a handler's translations for meaning/consistency."""
    provider: Optional[str] = Field(default=None, description="Preferred LLM provider (default: deepseek/config)")


class TranslationValidationResponse(BaseAPIResponse):
    """Result of LLM translation validation. When no LLM is available, `llm_available` is False and `message`
    instructs the user to validate manually."""
    handler_name: str = Field(description="Handler validated")
    llm_available: bool = Field(description="Whether a real (non-stub) LLM was available to run the check")
    provider: Optional[str] = Field(default=None, description="LLM provider used, if any")
    message: str = Field(description="Status / manual-validation instruction when no LLM is available")
    issues: List[TranslationIssueSchema] = Field(default_factory=list, description="Findings (empty if all good)")


class TranslateRequest(BaseAPIRequest):
    """Request the LLM translation *service*: translate a handler's phrasing from one language to another."""
    source_language: str = Field(description="Language to translate from")
    target_language: str = Field(description="Language to translate to")
    method_keys: Optional[List[str]] = Field(default=None, description="Limit to these method keys (default: all)")
    provider: Optional[str] = Field(default=None, description="Preferred LLM provider (default: deepseek/config)")


class TranslatedMethodSchema(BaseModel):
    """LLM-suggested target-language phrases for one method."""
    method_key: str = Field(description="method_name#intent_suffix")
    source_phrases: List[str] = Field(default_factory=list, description="Source-language phrases")
    suggested_phrases: List[str] = Field(default_factory=list, description="LLM-suggested target-language phrases")


class TranslateResponse(BaseAPIResponse):
    """Result of the LLM translation service. When no LLM is available, `llm_available` is False and `message`
    instructs the user to translate manually."""
    handler_name: str = Field(description="Handler translated")
    source_language: str = Field(description="Source language")
    target_language: str = Field(description="Target language")
    llm_available: bool = Field(description="Whether a real (non-stub) LLM was available")
    provider: Optional[str] = Field(default=None, description="LLM provider used, if any")
    message: str = Field(description="Status / manual instruction when no LLM is available")
    translations: List[TranslatedMethodSchema] = Field(default_factory=list, description="Per-method suggestions")


# ============================================================
# TEMPLATE MANAGEMENT SCHEMAS (Phase 6)
# ============================================================

class TemplateMetadata(BaseModel):
    """Metadata for a language-specific template file"""
    file_path: str = Field(description="e.g., 'conversation_handler/en.yaml'")
    language: str = Field(description="Language code")
    file_size: int = Field(description="File size in bytes")
    last_modified: float = Field(description="Last modification timestamp")
    template_count: int = Field(description="Number of templates in the file")


class TemplateContentResponse(BaseAPIResponse):
    """Response for language-specific template content retrieval"""
    handler_name: str = Field(description="Handler name")
    language: str = Field(description="Current language")
    template_data: Dict[str, Any] = Field(description="Complete template YAML content")
    metadata: TemplateMetadata = Field(description="File metadata")
    available_languages: List[str] = Field(description="Other available languages")
    schema_info: Dict[str, Any] = Field(description="Expected keys and their types")


class TemplateUpdateRequest(BaseAPIRequest):
    """Request to update a language-specific template file"""
    template_data: Dict[str, Any] = Field(description="Complete template YAML data")
    validate_before_save: bool = Field(default=True, description="Whether to validate before saving")
    trigger_reload: bool = Field(default=True, description="Whether to trigger reload after save")


class TemplateUpdateResponse(BaseAPIResponse):
    """Response for language-specific template update operation"""
    handler_name: str = Field(description="Updated handler name")
    language: str = Field(description="Updated language")
    validation_passed: bool = Field(description="Whether validation passed")
    reload_triggered: bool = Field(description="Whether template reload was triggered")
    backup_created: bool = Field(description="Whether backup was created")
    errors: List[ValidationError] = Field(default=[], description="Validation errors")
    warnings: List[ValidationWarning] = Field(default=[], description="Validation warnings")


class TemplateValidationRequest(BaseAPIRequest):
    """Request to validate language-specific template data without saving"""
    template_data: Dict[str, Any] = Field(description="Template data to validate")


class TemplateValidationResponse(BaseAPIResponse):
    """Response for language-specific template validation operation"""
    handler_name: str = Field(description="Handler name being validated")
    language: str = Field(description="Language being validated")
    is_valid: bool = Field(description="Whether template is valid")
    errors: List[ValidationError] = Field(default=[], description="Validation errors")
    warnings: List[ValidationWarning] = Field(default=[], description="Validation warnings")
    validation_types: List[str] = Field(description="Types of validation performed")


class CreateTemplateLanguageRequest(BaseAPIRequest):
    """Request to create a new language file for template"""
    copy_from: Optional[str] = Field(default=None, description="Language to copy from")
    use_template: bool = Field(default=False, description="Use empty template instead of copying")


class CreateTemplateLanguageResponse(BaseAPIResponse):
    """Response for template language creation operation"""
    handler_name: str = Field(description="Handler name")
    language: str = Field(description="Created language")
    created: bool = Field(description="Whether language file was created")
    copied_from: Optional[str] = Field(default=None, description="Language copied from")


class DeleteTemplateLanguageResponse(BaseAPIResponse):
    """Response for template language deletion operation"""
    handler_name: str = Field(description="Handler name")
    language: str = Field(description="Deleted language")
    deleted: bool = Field(description="Whether language file was deleted")
    backup_created: bool = Field(description="Whether backup was created before deletion")


class TemplateHandlerListResponse(BaseAPIResponse):
    """Response for listing handlers with template language info"""
    handlers: List[HandlerLanguageInfo] = Field(description="List of handlers with language info")
    total_handlers: int = Field(description="Total number of handlers")


# ============================================================
# PROMPT MANAGEMENT SCHEMAS (Phase 7)
# ============================================================

class PromptDefinition(BaseModel):
    """Prompt definition with metadata"""
    description: str = Field(description="Description of the prompt")
    usage_context: str = Field(description="Context where this prompt is used")
    variables: List[Dict[str, str]] = Field(default=[], description="List of variable definitions")
    prompt_type: str = Field(default="system", description="Type of prompt: system, template, user")
    content: str = Field(description="The actual prompt content")


class PromptMetadata(BaseModel):
    """Metadata for a language-specific prompt file"""
    file_path: str = Field(description="e.g., 'conversation_handler/en.yaml'")
    language: str = Field(description="Language code")
    file_size: int = Field(description="File size in bytes")
    last_modified: float = Field(description="Last modification timestamp")
    prompt_count: int = Field(description="Number of prompts in the file")


class PromptContentResponse(BaseAPIResponse):
    """Response for language-specific prompt content retrieval"""
    handler_name: str = Field(description="Handler name")
    language: str = Field(description="Current language")
    prompt_data: Dict[str, PromptDefinition] = Field(description="Complete prompt YAML content")
    metadata: PromptMetadata = Field(description="File metadata")
    available_languages: List[str] = Field(description="Other available languages")
    schema_info: Dict[str, Any] = Field(description="Required fields and prompt types")


class PromptUpdateRequest(BaseAPIRequest):
    """Request to update a language-specific prompt file"""
    prompt_data: Dict[str, PromptDefinition] = Field(description="Complete prompt YAML data")
    validate_before_save: bool = Field(default=True, description="Whether to validate before saving")
    trigger_reload: bool = Field(default=True, description="Whether to trigger reload after save")


class PromptUpdateResponse(BaseAPIResponse):
    """Response for language-specific prompt update operation"""
    handler_name: str = Field(description="Updated handler name")
    language: str = Field(description="Updated language")
    validation_passed: bool = Field(description="Whether validation passed")
    reload_triggered: bool = Field(description="Whether prompt reload was triggered")
    backup_created: bool = Field(description="Whether backup was created")
    errors: List[ValidationError] = Field(default=[], description="Validation errors")
    warnings: List[ValidationWarning] = Field(default=[], description="Validation warnings")


class PromptValidationRequest(BaseAPIRequest):
    """Request to validate language-specific prompt data without saving"""
    prompt_data: Dict[str, PromptDefinition] = Field(description="Prompt data to validate")


class PromptValidationResponse(BaseAPIResponse):
    """Response for language-specific prompt validation operation"""
    handler_name: str = Field(description="Handler name being validated")
    language: str = Field(description="Language being validated")
    is_valid: bool = Field(description="Whether prompt is valid")
    errors: List[ValidationError] = Field(default=[], description="Validation errors")
    warnings: List[ValidationWarning] = Field(default=[], description="Validation warnings")
    validation_types: List[str] = Field(description="Types of validation performed")


class CreatePromptLanguageRequest(BaseAPIRequest):
    """Request to create a new language file for prompt"""
    copy_from: Optional[str] = Field(default=None, description="Language to copy from")
    use_template: bool = Field(default=False, description="Use empty template instead of copying")


class CreatePromptLanguageResponse(BaseAPIResponse):
    """Response for prompt language creation operation"""
    handler_name: str = Field(description="Handler name")
    language: str = Field(description="Created language")
    created: bool = Field(description="Whether language file was created")
    copied_from: Optional[str] = Field(default=None, description="Language copied from")


class DeletePromptLanguageResponse(BaseAPIResponse):
    """Response for prompt language deletion operation"""
    handler_name: str = Field(description="Handler name")
    language: str = Field(description="Deleted language")
    deleted: bool = Field(description="Whether language file was deleted")
    backup_created: bool = Field(description="Whether backup was created before deletion")


class PromptHandlerListResponse(BaseAPIResponse):
    """Response for listing handlers with prompt language info"""
    handlers: List[HandlerLanguageInfo] = Field(description="List of handlers with language info")
    total_handlers: int = Field(description="Total number of handlers")


# ============================================================
# LOCALIZATION MANAGEMENT SCHEMAS (Phase 8)
# ============================================================

class LocalizationMetadata(BaseModel):
    """Metadata for a language-specific localization file"""
    file_path: str = Field(description="Relative file path from assets root")
    language: str = Field(description="Language code")
    file_size: int = Field(description="File size in bytes")
    last_modified: float = Field(description="Last modification timestamp")
    entry_count: int = Field(description="Number of localization entries in the file")


class LocalizationContentResponse(BaseAPIResponse):
    """Response for language-specific localization content retrieval"""
    domain: str = Field(description="Domain name")
    language: str = Field(description="Current language")
    localization_data: Dict[str, Any] = Field(description="Complete localization YAML content")
    metadata: LocalizationMetadata = Field(description="File metadata")
    available_languages: List[str] = Field(description="Other available languages")
    schema_info: Dict[str, Any] = Field(description="Expected keys and their types")


class LocalizationUpdateRequest(BaseAPIRequest):
    """Request to update a language-specific localization file"""
    localization_data: Dict[str, Any] = Field(description="Localization data to save")
    validate_before_save: bool = Field(default=True, description="Whether to validate before saving")
    trigger_reload: bool = Field(default=True, description="Whether to trigger localization reload")


class LocalizationUpdateResponse(BaseAPIResponse):
    """Response for language-specific localization update operation"""
    domain: str = Field(description="Domain name being updated")
    language: str = Field(description="Language being updated")
    validation_passed: bool = Field(description="Whether validation passed")
    reload_triggered: bool = Field(description="Whether localization reload was triggered")
    backup_created: bool = Field(description="Whether backup was created")
    errors: List[ValidationError] = Field(default=[], description="Validation errors")
    warnings: List[ValidationWarning] = Field(default=[], description="Validation warnings")


class LocalizationValidationRequest(BaseAPIRequest):
    """Request to validate localization data without saving"""
    localization_data: Dict[str, Any] = Field(description="Localization data to validate")


class LocalizationValidationResponse(BaseAPIResponse):
    """Response for language-specific localization validation operation"""
    domain: str = Field(description="Domain name being validated")
    language: str = Field(description="Language being validated")
    is_valid: bool = Field(description="Whether localization is valid")
    errors: List[ValidationError] = Field(default=[], description="Validation errors")
    warnings: List[ValidationWarning] = Field(default=[], description="Validation warnings")
    validation_types: List[str] = Field(description="Types of validation performed")


class CreateLocalizationLanguageRequest(BaseAPIRequest):
    """Request to create a new language file for localization"""
    copy_from: Optional[str] = Field(default=None, description="Language to copy from")
    use_template: bool = Field(default=False, description="Use empty template instead of copying")


class CreateLocalizationLanguageResponse(BaseAPIResponse):
    """Response for localization language creation operation"""
    domain: str = Field(description="Domain name")
    language: str = Field(description="Created language")
    created: bool = Field(description="Whether language file was created")
    copied_from: Optional[str] = Field(default=None, description="Language copied from")


class DeleteLocalizationLanguageResponse(BaseAPIResponse):
    """Response for localization language deletion operation"""
    domain: str = Field(description="Domain name")
    language: str = Field(description="Deleted language")
    deleted: bool = Field(description="Whether language file was deleted")
    backup_created: bool = Field(description="Whether backup was created before deletion")


class DomainLanguageInfo(BaseModel):
    """Information about a domain and its available languages"""
    domain: str = Field(description="Domain name")
    languages: List[str] = Field(description="Available language codes")
    total_languages: int = Field(description="Total number of languages available")
    supported_languages: List[str] = Field(description="Configured supported languages")
    default_language: str = Field(description="System default language")


class LocalizationDomainListResponse(BaseAPIResponse):
    """Response for listing domains with localization language info"""
    domains: List[DomainLanguageInfo] = Field(description="List of domains with language info")
    total_domains: int = Field(description="Total number of domains")


# ============================================================
# INTENT SYSTEM SCHEMAS (EXISTING)
# ============================================================

class IntentHandlerInfo(BaseModel):
    """Information about an intent handler"""
    class_name: str = Field(description="Handler class name", alias="class")
    domains: List[str] = Field(description="Supported domains")
    actions: List[str] = Field(description="Supported actions")
    available: bool = Field(description="Whether handler is available")
    capabilities: Dict[str, Any] = Field(description="Handler capabilities")
    has_donation: bool = Field(description="Whether handler has donation")
    supports_donation_routing: bool = Field(description="Whether handler supports donation routing")
    donation: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Donation information if available"
    )


class IntentSystemStatusResponse(BaseAPIResponse):
    """Response for intent system status"""
    status: str = Field(description="System status")
    handlers_count: int = Field(description="Number of loaded handlers")
    handlers: List[str] = Field(description="List of handler names")
    donations_count: int = Field(description="Number of loaded donations")
    donations: List[str] = Field(description="List of donation names")
    registry_patterns: List[str] = Field(description="Registered intent patterns")
    donation_routing_enabled: bool = Field(description="Whether donation routing is enabled")
    parameter_extraction_integrated: bool = Field(description="Whether parameter extraction is integrated")
    configuration: Optional[Dict[str, Any]] = Field(description="Current configuration")


class IntentHandlersResponse(BaseAPIResponse):
    """Response for intent handlers listing"""
    handlers: Dict[str, IntentHandlerInfo] = Field(description="Available handlers information")


class IntentRegistryResponse(BaseAPIResponse):
    """Response for intent registry patterns"""
    patterns: Dict[str, Dict[str, Any]] = Field(description="Registry patterns information")


class IntentReloadResponse(BaseAPIResponse):
    """Response for handler reload operation"""
    status: str = Field(description="Reload status")
    handlers_count: int = Field(description="Number of handlers loaded")
    handlers: List[str] = Field(description="List of loaded handler names")
    error: Optional[str] = Field(
        default=None,
        description="Error message if reload failed"
    )


# ============================================================
# AUDIO PLAYBACK SCHEMAS
# ============================================================

class AudioPlayRequest(BaseAPIRequest):
    """Request for file-based audio playback (moved from component)"""
    # Note: File upload handled by FastAPI UploadFile
    provider: Optional[str] = Field(
        default=None,
        description="Specific audio provider to use"
    )
    volume: Optional[float] = Field(
        default=None,
        description="Playback volume (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    device: Optional[str] = Field(
        default=None,
        description="Audio output device ID"
    )


class AudioPlayResponse(BaseAPIResponse):
    """Response for audio playback operations"""
    provider: str = Field(description="Audio provider used")
    file: Optional[str] = Field(description="Original filename")
    size: int = Field(description="Audio data size in bytes")


class AudioStreamRequest(BaseAPIRequest):
    """Request for stream-based audio playback"""
    # Note: Audio data handled separately as bytes
    format: str = Field(
        default="wav",
        description="Audio format",
        json_schema_extra={"example": "wav"}    )
    provider: Optional[str] = Field(
        default=None,
        description="Specific audio provider to use"
    )
    volume: Optional[float] = Field(
        default=None,
        description="Playback volume (0.0-1.0)",
        ge=0.0,
        le=1.0
    )


class AudioStreamResponse(BaseAPIResponse):
    """Response for audio stream playback"""
    provider: str = Field(description="Audio provider used")
    format: str = Field(description="Audio format processed")
    size: int = Field(description="Audio data size in bytes")


class AudioStopResponse(BaseAPIResponse):
    """Response for audio stop operation"""
    message: str = Field(description="Stop operation message")


class AudioDeviceInfo(BaseModel):
    """Information about an audio output device"""
    id: str = Field(description="Device ID")
    name: str = Field(description="Device name")
    default: bool = Field(description="Whether this is the default device")


class AudioDevicesResponse(BaseAPIResponse):
    """Response for audio devices listing"""
    provider: str = Field(description="Provider that reported devices")
    devices: List[Dict[str, Any]] = Field(description="Available audio output devices")




class AudioProvidersResponse(BaseAPIResponse):
    """Response containing available audio providers"""
    providers: Dict[str, Dict[str, Any]] = Field(
        description="Available providers and their capabilities"
    )
    default: str = Field(description="Default provider name")
    fallbacks: List[str] = Field(description="Fallback provider names")


# ============================================================
# VOICE TRIGGER SCHEMAS
# ============================================================

class VoiceTriggerStatus(BaseAPIResponse):
    """Response for voice trigger status (moved from component)"""
    active: bool = Field(description="Whether voice trigger is active")
    wake_words: List[str] = Field(description="Current wake words")
    threshold: float = Field(
        description="Detection threshold",
        ge=0.0,
        le=1.0
    )
    provider: str = Field(description="Current provider name")
    providers_available: List[str] = Field(description="Available provider names")






class VoiceTriggerSwitchRequest(BaseAPIRequest):
    """Request to switch voice trigger provider"""
    provider_name: str = Field(description="Provider name to switch to")


class VoiceTriggerSwitchResponse(BaseAPIResponse):
    """Response for provider switch operation"""
    active_provider: str = Field(description="Now active provider")
    wake_words: List[str] = Field(description="Current wake words")
    threshold: float = Field(description="Current threshold")


class VoiceTriggerProvidersResponse(BaseAPIResponse):
    """Response containing available voice trigger providers"""
    providers: Dict[str, Dict[str, Any]] = Field(
        description="Available providers and their capabilities"
    )
    default: Optional[str] = Field(description="Default provider name")
    fallbacks: List[str] = Field(description="Fallback provider names")


# ============================================================
# TEXT PROCESSING SCHEMAS
# ============================================================

class TextProcessingRequest(BaseAPIRequest):
    """Request for text processing and normalization (moved from component)"""
    text: str = Field(description="Text to process")
    stage: str = Field(
        default="general",
        description="Processing stage",
        json_schema_extra={"example": "general"}    )
    normalizer: Optional[str] = Field(
        default=None,
        description="Specific normalizer to use (optional)",
        json_schema_extra={"example": "numbers"}    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional client context (session_id, client_id, room_name, device_context)"
    )


class TextProcessingResponse(BaseAPIResponse):
    """Response for text processing operations (moved from component)"""
    original_text: str = Field(description="Original input text")
    processed_text: str = Field(description="Processed/normalized text")
    stage: str = Field(description="Processing stage used")
    normalizers_applied: List[str] = Field(description="Names of normalizers that were applied")
    session_id: Optional[str] = Field(
        default=None,
        description="Session identifier from the conversation context"
    )
    room_context: bool = Field(
        default=False,
        description="Whether the request carried room/client context"
    )


class NumberConversionRequest(BaseAPIRequest):
    """Request for number-to-words conversion (moved from component)"""
    text: str = Field(description="Text containing numbers to convert")
    language: str = Field(
        default="ru",
        description="Language for number conversion",
        json_schema_extra={"example": "ru"}    )


class NumberConversionResponse(BaseAPIResponse):
    """Response for number-to-words conversion"""
    original_text: str = Field(description="Original input text")
    processed_text: str = Field(description="Text with numbers converted to words")
    language: str = Field(description="Language used for conversion")


class TextNormalizerInfo(BaseModel):
    """Information about a text normalizer"""
    stages: List[str] = Field(description="Available processing stages")
    applies_to: List[str] = Field(description="Stages this normalizer applies to")
    description: str = Field(description="Normalizer description")


class TextProcessingNormalizersResponse(BaseAPIResponse):
    """Response for text processing normalizers listing"""
    normalizers: Dict[str, TextNormalizerInfo] = Field(description="Available normalizers")
    pipeline_stages: List[str] = Field(description="Available pipeline stages")
    available_languages: List[str] = Field(description="Supported languages for number conversion")


class TextProcessingConfigResponse(BaseAPIResponse):
    """Response for text processing configuration"""
    normalizer_count: int = Field(description="Number of loaded normalizers")
    supported_stages: List[str] = Field(description="Supported processing stages")
    supported_languages: List[str] = Field(description="Supported languages")
    dependencies: List[str] = Field(description="Component dependencies")


# ============================================================
# MONITORING SCHEMAS
# ============================================================

class MonitoringStatusResponse(BaseAPIResponse):
    """Response for monitoring system status (moved from component)"""
    status: str = Field(description="Overall monitoring status")
    services: Dict[str, bool] = Field(description="Status of monitoring services")
    uptime: float = Field(description="System uptime in seconds")


class MetricsResponse(BaseAPIResponse):
    """Response for system metrics (moved from component)"""
    system_metrics: Dict[str, Any] = Field(description="System-level metrics")
    domain_metrics: Dict[str, Any] = Field(description="Domain-specific metrics")
    performance_summary: Dict[str, Any] = Field(description="Performance summary")


class MemoryStatusResponse(BaseAPIResponse):
    """Response for memory status (moved from component)"""
    memory_usage: Dict[str, Any] = Field(description="Current memory usage")
    cleanup_needed: Dict[str, bool] = Field(description="Areas requiring cleanup")
    recommendations: List[Dict[str, Any]] = Field(description="Memory optimization recommendations")


class NotificationResponse(BaseAPIResponse):
    """Response for notification operations (moved from component)"""
    message: str = Field(description="Notification result message")


class DebugResponse(BaseAPIResponse):
    """Response for debug operations (moved from component)"""
    debug_status: Dict[str, Any] = Field(description="Current debug status")
    inspection_history: List[Dict[str, Any]] = Field(description="Debug inspection history")


class DashboardResponse(BaseAPIResponse):
    """Response for analytics dashboard (moved from component)"""
    dashboard_data: Dict[str, Any] = Field(description="Dashboard visualization data")
    health_summary: Dict[str, Any] = Field(description="System health summary")


class AnalyticsReportResponse(BaseAPIResponse):
    """Response for comprehensive analytics report (moved from component)"""
    timestamp: float = Field(default_factory=time.time, description="Report generation timestamp")
    report_type: str = Field(description="Type of analytics report")
    intents: Dict[str, Any] = Field(description="Intent analytics data")
    sessions: Dict[str, Any] = Field(description="Session analytics data")
    system: Dict[str, Any] = Field(description="System analytics data")


class PerformanceValidationResponse(BaseAPIResponse):
    """Response for performance validation (moved from component)"""
    performance_score: float = Field(
        description="Overall performance score",
        ge=0.0,
        le=1.0
    )
    meets_criteria: bool = Field(description="Whether performance meets criteria")
    validation_criteria: Dict[str, float] = Field(description="Performance validation criteria")
    performance_analysis: Dict[str, Any] = Field(description="Detailed performance analysis")
    recommendations: List[Dict[str, str]] = Field(description="Performance improvement recommendations")
    generated_at: str = Field(description="Validation generation timestamp")


class SessionSatisfactionRequest(BaseAPIRequest):
    """Request for rating session satisfaction"""
    satisfaction_score: float = Field(
        description="User satisfaction score",
        ge=0.0,
        le=1.0,
        json_schema_extra={"example": 0.8}    )


class SessionSatisfactionResponse(BaseAPIResponse):
    """Response for session satisfaction rating"""
    session_id: str = Field(description="Session identifier")
    satisfaction_score: float = Field(description="Recorded satisfaction score")
    message: str = Field(description="Operation result message")


class IntentAnalyticsResponse(BaseAPIResponse):
    """Response for intent analytics"""
    total_intents_processed: int = Field(description="Total number of intents processed")
    unique_intent_types: int = Field(description="Number of unique intent types")
    intent_breakdown: Dict[str, Any] = Field(description="Detailed intent breakdown")
    overall_success_rate: float = Field(description="Overall intent success rate")
    timestamp: float = Field(default_factory=time.time, description="Analytics timestamp")


class SessionAnalyticsResponse(BaseAPIResponse):
    """Response for session analytics"""
    active_sessions: int = Field(description="Number of active sessions")
    total_sessions: int = Field(description="Total number of sessions")
    average_session_duration: float = Field(description="Average session duration")
    average_user_satisfaction: float = Field(description="Average user satisfaction score")
    uptime_seconds: float = Field(description="System uptime in seconds")
    timestamp: float = Field(default_factory=time.time, description="Analytics timestamp")


class PerformanceAnalyticsResponse(BaseAPIResponse):
    """Response for performance analytics"""
    system: Dict[str, Any] = Field(description="System performance metrics")
    vad: Dict[str, Any] = Field(description="Voice Activity Detection metrics")
    components: Dict[str, Any] = Field(description="Component-specific metrics")
    timestamp: float = Field(default_factory=time.time, description="Analytics timestamp")


# ============================================================
# CONFIGURATION MANAGEMENT SCHEMAS
# ============================================================

class ConfigUpdateResponse(BaseAPIResponse):
    """Response for configuration section updates"""
    message: str = Field(description="Update status message")
    reload_triggered: bool = Field(description="Whether hot-reload was triggered")
    backup_created: Optional[str] = Field(default=None, description="Path to backup file if created")


class ConfigValidationResponse(BaseAPIResponse):
    """Response for configuration validation"""
    valid: bool = Field(description="Whether the configuration is valid")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Validated configuration data")
    validation_errors: Optional[List[Dict[str, Any]]] = Field(default=None, description="Validation error details")


class ConfigStatusResponse(BaseAPIResponse):
    """Response for configuration system status"""
    config_path: Optional[str] = Field(description="Path to active configuration file")
    config_exists: bool = Field(description="Whether configuration file exists")
    hot_reload_active: bool = Field(description="Whether hot-reload monitoring is active")
    component_initialized: bool = Field(description="Whether ConfigurationComponent is initialized")
    last_modified: Optional[float] = Field(default=None, description="Configuration file last modified timestamp")
    file_size: Optional[int] = Field(default=None, description="Configuration file size in bytes")


# ============================================================
# RAW TOML CONFIGURATION SCHEMAS (Phase 4)
# ============================================================

class RawTomlRequest(BaseAPIRequest):
    """Request to save raw TOML content"""
    toml_content: str = Field(description="Raw TOML content to save")
    validate_before_save: bool = Field(default=True, description="Whether to validate before saving")


class RawTomlResponse(BaseAPIResponse):
    """Response containing raw TOML content"""
    toml_content: str = Field(description="Raw TOML configuration content with comments preserved")
    config_path: str = Field(description="Path to configuration file")
    file_size: int = Field(description="File size in bytes")
    last_modified: float = Field(description="File last modified timestamp")


class RawTomlSaveResponse(BaseAPIResponse):
    """Response for raw TOML save operation"""
    message: str = Field(description="Save operation result message")
    backup_created: Optional[str] = Field(default=None, description="Path to backup file if created")
    config_cached: bool = Field(description="Whether configuration was successfully cached")


class RawTomlValidationRequest(BaseAPIRequest):
    """Request to validate raw TOML content"""
    toml_content: str = Field(description="Raw TOML content to validate")


class RawTomlValidationResponse(BaseAPIResponse):
    """Response for raw TOML validation"""
    valid: bool = Field(description="Whether TOML content is valid")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Parsed configuration data if valid")
    errors: Optional[List[Dict[str, Any]]] = Field(default=None, description="Validation errors if invalid")


class SectionToTomlRequest(BaseAPIRequest):
    """Request to apply section changes to raw TOML"""
    section_data: Dict[str, Any] = Field(description="Section configuration data")


class SectionToTomlResponse(BaseAPIResponse):
    """Response for section-to-TOML operation"""
    toml_content: str = Field(description="Updated TOML content with section applied")
    section_name: str = Field(description="Section that was updated")
    comments_preserved: bool = Field(description="Whether comments were preserved")


# ============================================================
# NLU ANALYSIS SCHEMAS (Phase 2)
# ============================================================

class AnalyzeDonationRequest(BaseAPIRequest):
    """Request for real-time donation analysis"""
    handler_name: str = Field(description="Handler name to analyze")
    language: str = Field(description="Language of the donation", json_schema_extra={"example": "en"})
    donation_data: Dict[str, Any] = Field(description="Complete donation data to analyze")


class NLUAnalysisResult(BaseAPIResponse):
    """Response for NLU analysis operations"""
    conflicts: List[Dict[str, Any]] = Field(description="Detected conflicts")
    scope_issues: List[Dict[str, Any]] = Field(description="Scope creep issues")
    performance_metrics: Dict[str, Any] = Field(description="Detailed analysis performance metrics from analyzers")
    language_coverage: Dict[str, float] = Field(description="Language coverage analysis")
    analysis_time_ms: float = Field(description="Time taken for analysis")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "success": True,
                    "timestamp": 1704067200.123,
                    "conflicts": [
                        {
                            "intent_a": "timer.set",
                            "intent_b": "datetime.current_time",
                            "language": "en",
                            "severity": "warning",
                            "score": 0.75,
                            "conflict_type": "phrase_overlap",
                            "signals": {
                                "shared_phrases": ["set time", "time setting"],
                                "overlap_percentage": 0.4
                            },
                            "suggestions": [
                                "Make 'timer.set' phrases more specific: 'set timer for X'",
                                "Consider removing generic 'set time' from timer domain"
                            ]
                        }
                    ],
                    "scope_issues": [],
                    "performance_metrics": {
                        "hybrid": {
                            "keyword_analysis": {
                                "collision_count": 2,
                                "efficiency_score": 0.95
                            },
                            "pattern_analysis": {
                                "complexity_score": 0.8,
                                "optimization_suggestions": []
                            }
                        },
                        "spacy": {
                            "similarity_analysis": {
                                "semantic_conflicts": [],
                                "confidence_scores": [0.92, 0.87]
                            },
                            "entity_analysis": {
                                "entity_coverage": 0.85
                            }
                        }
                    },
                    "language_coverage": {
                        "en": 0.85
                    },
                    "analysis_time_ms": 8.5
                }
            ]
        }


class AnalyzeChangesRequest(BaseAPIRequest):
    """Request for analyzing impact of multiple changes"""
    changes: Dict[str, Dict[str, Any]] = Field(description="Dictionary of changes to analyze")
    language: Optional[str] = Field(default=None, description="Optional language filter")


class ChangeImpactAnalysisResponse(BaseAPIResponse):
    """Response for change impact analysis"""
    changes: Dict[str, Any] = Field(description="Summary of proposed changes")
    affected_intents: List[str] = Field(description="Intents affected by changes")
    new_conflicts: List[Dict[str, Any]] = Field(description="New conflicts introduced")
    resolved_conflicts: List[Dict[str, Any]] = Field(description="Conflicts resolved by changes")
    impact_score: float = Field(description="Overall impact score (0.0-1.0)", ge=0.0, le=1.0)
    recommendations: List[str] = Field(description="Recommendations based on impact")
    analysis_time_ms: float = Field(description="Time taken for impact analysis")


class ValidateRequest(BaseAPIRequest):
    """Request for pre-save validation"""
    handler_name: str = Field(description="Handler name to validate")
    language: str = Field(description="Language of the donation", json_schema_extra={"example": "en"})
    donation_data: Dict[str, Any] = Field(description="Complete donation data to validate")


class NLUValidationResult(BaseAPIResponse):
    """Response for pre-save validation"""
    is_valid: bool = Field(description="Whether donation is valid for saving")
    has_blocking_conflicts: bool = Field(description="Whether there are blocking conflicts")
    has_warnings: bool = Field(description="Whether there are warning-level issues")
    conflicts: List[Dict[str, Any]] = Field(description="All detected conflicts")
    suggestions: List[str] = Field(description="General improvement suggestions")
    validation_time_ms: float = Field(description="Time taken for validation")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "success": True,
                    "timestamp": 1704067200.123,
                    "is_valid": False,
                    "has_blocking_conflicts": True,
                    "has_warnings": False,
                    "conflicts": [
                        {
                            "intent_a": "timer.set",
                            "intent_b": "timer.cancel",
                            "severity": "blocker",
                            "conflict_type": "keyword_collision"
                        }
                    ],
                    "suggestions": ["Resolve keyword collisions before saving"],
                    "validation_time_ms": 15.2
                }
            ]
        }


class ConflictReport(BaseModel):
    """Individual conflict report"""
    intent_a: str = Field(description="First intent in conflict")
    intent_b: str = Field(description="Second intent in conflict")
    language: str = Field(description="Language where conflict occurs")
    severity: Literal['blocker', 'warning', 'info'] = Field(description="Conflict severity")
    score: float = Field(description="Conflict strength score (0.0-1.0)", ge=0.0, le=1.0)
    conflict_type: str = Field(description="Type of conflict detected")
    signals: Dict[str, Any] = Field(description="Evidence and analysis details")
    suggestions: List[str] = Field(description="Suggested resolutions")


class BatchAnalysisResponse(BaseAPIResponse):
    """Response for full system batch analysis"""
    summary: Dict[str, int] = Field(description="Summary statistics")
    conflicts: List[ConflictReport] = Field(description="All detected conflicts")
    scope_issues: List[Dict[str, Any]] = Field(description="All scope issues")
    system_health: Dict[str, float] = Field(description="System health metrics")
    language_breakdown: Dict[str, Dict[str, int]] = Field(description="Per-language statistics")
    performance_metrics: Dict[str, float] = Field(description="System performance metrics")
    recommendations: List[str] = Field(description="System-wide recommendations")
    analysis_time_ms: float = Field(description="Total analysis time")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "success": True,
                    "timestamp": 1704067200.123,
                    "summary": {
                        "total_intents": 45,
                        "total_conflicts": 3,
                        "blockers": 1,
                        "warnings": 2,
                        "scope_issues": 1
                    },
                    "conflicts": [],
                    "scope_issues": [],
                    "system_health": {
                        "overall_score": 0.87,
                        "conflict_ratio": 0.067,
                        "coverage_ratio": 0.92
                    },
                    "language_breakdown": {
                        "ru": {"intents": 22, "conflicts": 2},
                        "en": {"intents": 23, "conflicts": 1}
                    },
                    "performance_metrics": {
                        "avg_analysis_time": 12.5,
                        "memory_usage_mb": 28.4
                    },
                    "recommendations": [
                        "Resolve blocking conflict in timer domain",
                        "Consider splitting broad patterns in conversation handler"
                    ],
                    "analysis_time_ms": 156.7
                }
            ]
        }


class SystemHealthResponse(BaseAPIResponse):
    """Response for NLU system health check"""
    status: Literal['healthy', 'degraded', 'critical'] = Field(description="Overall system status")
    health_score: float = Field(description="Overall health score (0.0-1.0)", ge=0.0, le=1.0)
    component_status: Dict[str, str] = Field(description="Status of individual components")
    conflict_summary: Dict[str, int] = Field(description="Conflict summary by severity")
    performance_summary: Dict[str, float] = Field(description="Performance metrics summary")
    recommendations: List[str] = Field(description="Health improvement recommendations")
    last_analysis: float = Field(description="Timestamp of last analysis")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "success": True,
                    "timestamp": 1704067200.123,
                    "status": "healthy",
                    "health_score": 0.87,
                    "component_status": {
                        "hybrid_analyzer": "operational",
                        "spacy_analyzer": "operational",
                        "conflict_detector": "operational"
                    },
                    "conflict_summary": {
                        "blockers": 0,
                        "warnings": 2,
                        "info": 5
                    },
                    "performance_summary": {
                        "avg_analysis_time": 12.5,
                        "memory_usage_mb": 28.4,
                        "success_rate": 0.98
                    },
                    "recommendations": [
                        "Monitor warning-level conflicts",
                        "Consider optimization for large datasets"
                    ],
                    "last_analysis": 1704067200.123
                }
            ]
        }


# ============================================================
# TEXT PROCESSOR CONFIGURATION SCHEMAS (Phase 1)
# ============================================================

class TextProcessorConfigureResponse(BaseAPIResponse):
    """Response for text processor configuration using unified TOML schema"""
    message: str = Field(description="Configuration operation message")
    enabled_providers: List[str] = Field(description="List of enabled text processing providers")
    stages: List[str] = Field(description="Configured processing stages")
    normalizers: List[str] = Field(description="Configured normalizer names")


# ============================================================
# INTENT SYSTEM CONFIGURATION SCHEMAS (Phase 1)
# ============================================================

class IntentSystemConfigureResponse(BaseAPIResponse):
    """Response for intent system configuration using unified TOML schema"""
    message: str = Field(description="Configuration operation message")
    confidence_threshold: float = Field(description="Applied confidence threshold")
    fallback_intent: str = Field(description="Configured fallback intent")
    enabled_handlers: List[str] = Field(description="List of enabled intent handlers")
    loaded_donations: List[str] = Field(description="List of handlers with loaded donations")
    handler_count: int = Field(description="Total number of active handlers")


# ============================================================
# PHASE 2: UNIFIED CONFIGURE RESPONSE SCHEMAS
# ============================================================

class TTSConfigureResponse(BaseAPIResponse):
    """Response for TTS configuration using unified TOML schema"""
    message: str = Field(description="Configuration operation message")
    default_provider: Optional[str] = Field(description="Current default TTS provider")
    enabled_providers: List[str] = Field(description="List of enabled TTS providers")
    fallback_providers: List[str] = Field(description="Configured fallback providers")


class ASRConfigureResponse(BaseAPIResponse):
    """Response for ASR configuration using unified TOML schema"""
    message: str = Field(description="Configuration operation message")
    default_provider: Optional[str] = Field(description="Current default ASR provider")
    enabled_providers: List[str] = Field(description="List of enabled ASR providers")
    language: Optional[str] = Field(description="Configured language")


class AudioConfigureResponse(BaseAPIResponse):
    """Response for Audio configuration using unified TOML schema"""
    message: str = Field(description="Configuration operation message")
    default_provider: Optional[str] = Field(description="Current default audio provider")
    enabled_providers: List[str] = Field(description="List of enabled audio providers")
    fallback_providers: List[str] = Field(description="Configured fallback providers")


class LLMConfigureResponse(BaseAPIResponse):
    """Response for LLM configuration using unified TOML schema"""
    message: str = Field(description="Configuration operation message")
    default_provider: Optional[str] = Field(description="Current default LLM provider")
    enabled_providers: List[str] = Field(description="List of enabled LLM providers")
    fallback_providers: List[str] = Field(description="Configured fallback providers")


class NLUConfigureResponse(BaseAPIResponse):
    """Response for NLU configuration using unified TOML schema"""
    message: str = Field(description="Configuration operation message")
    default_provider: Optional[str] = Field(description="Current default NLU provider")
    enabled_providers: List[str] = Field(description="List of enabled NLU providers")
    confidence_threshold: Optional[float] = Field(description="Applied confidence threshold")


class VoiceTriggerConfigureResponse(BaseAPIResponse):
    """Response for Voice Trigger configuration using unified TOML schema"""
    message: str = Field(description="Configuration operation message")
    default_provider: Optional[str] = Field(description="Current default voice trigger provider")
    enabled_providers: List[str] = Field(description="List of enabled voice trigger providers")
    wake_words: List[str] = Field(description="Configured wake words")
