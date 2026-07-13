"""
Configuration Schemas - Component-specific configuration schemas

Phase 1 Implementation: Centralized schemas for component configurations
that can be imported and used throughout the system for validation and
type hints.

Phase 2 Implementation: Integration with AutoSchemaRegistry for auto-generated
component schema management.

This module provides:
- Component configuration schemas
- Provider configuration schemas  
- Validation utilities
- Schema versioning support
- Auto-registry integration
"""

from typing import Dict, Any, List, Optional, Type, Literal
from pydantic import BaseModel, Field

from .models import WakeWordSpec  # QUAL-20: the uniform per-provider wake-word unit


# ============================================================
# PROVIDER CONFIGURATION SCHEMAS
# ============================================================

class BaseProviderSchema(BaseModel):
    """Base schema for all providers"""
    enabled: bool = Field(default=True, description="Enable this provider")


class TTSProviderSchema(BaseProviderSchema):
    """Base schema for TTS providers"""
    pass


class AudioProviderSchema(BaseProviderSchema):
    """Base schema for Audio providers"""
    pass


class ASRProviderSchema(BaseProviderSchema):
    """Base schema for ASR providers"""
    pass


class LLMProviderSchema(BaseProviderSchema):
    """Base schema for LLM providers"""
    pass


class VoiceTriggerProviderSchema(BaseProviderSchema):
    """Base schema for Voice Trigger providers"""
    pass


class NLUProviderSchema(BaseProviderSchema):
    """Base schema for NLU providers"""
    pass


class VADProviderSchema(BaseProviderSchema):
    """Base schema for VAD providers (ARCH-18)"""
    pass


class TextProcessorProviderSchema(BaseProviderSchema):
    """Base schema for Text Processor providers"""
    pass


# ============================================================
# TTS PROVIDER SCHEMAS
# ============================================================

class ConsoleProviderSchema(TTSProviderSchema):
    """Console provider configuration schema (used across multiple components)"""
    color: str = Field(default="blue", description="Text color for console output")
    style: str = Field(default="console", description="Output style")
    format: str = Field(default="txt", description="File output format")


class ElevenLabsProviderSchema(TTSProviderSchema):
    """ElevenLabs provider configuration schema"""
    api_key: str = Field(description="ElevenLabs API key (use ${ELEVENLABS_API_KEY})")
    voice_id: str = Field(default="21m00Tcm4TlvDq8ikWAM", description="Voice ID")
    model: str = Field(default="eleven_monolingual_v1", description="Model name")
    stability: float = Field(default=0.5, ge=0.0, le=1.0, description="Voice stability")
    similarity_boost: float = Field(default=0.5, ge=0.0, le=1.0, description="Similarity boost")
    output_pcm_rate: int = Field(default=22050, description="ARCH-21 streaming: PCM sample rate requested from the API (pcm_<rate>); 44100 needs a paid tier")


class SileroV3ProviderSchema(TTSProviderSchema):
    """Silero v3 TTS provider configuration schema"""
    default_speaker: str = Field(default="xenia", description="Default speaker voice")
    sample_rate: int = Field(default=24000, description="Audio sample rate")
    torch_device: str = Field(default="cpu", description="PyTorch device: cpu, cuda")
    put_accent: bool = Field(default=True, description="Enable accent marks in speech")
    put_yo: bool = Field(default=True, description="Use ё character in speech")
    threads: int = Field(default=4, description="Number of processing threads")
    speaker_by_assname: Dict[str, str] = Field(
        default_factory=dict,
        description="Speaker mapping by assistant name (e.g., {'ирина': 'xenia'})"
    )
    preload_models: bool = Field(default=False, description="Preload AI models during provider initialization")


class SileroV4ProviderSchema(TTSProviderSchema):
    """Silero v4 TTS provider configuration schema"""
    default_speaker: str = Field(default="xenia", description="Default speaker voice: xenia, aidar, baya, kseniya, eugene, random")
    sample_rate: int = Field(default=48000, description="Audio sample rate")
    torch_device: str = Field(default="cpu", description="PyTorch device: cpu, cuda")
    preload_models: bool = Field(default=False, description="Preload AI models during provider initialization")


class PyttSXProviderSchema(TTSProviderSchema):
    """PyTTSX provider configuration schema"""
    voice_id: int = Field(default=0, description="Voice ID (system-dependent)")
    voice_rate: int = Field(default=200, ge=50, le=500, description="Speech rate (words per minute)")
    voice_volume: float = Field(default=1.0, ge=0.0, le=1.0, description="Volume level")


class PiperProviderSchema(TTSProviderSchema):
    """Piper TTS provider configuration schema (ARCH-24: VITS via sherpa-onnx, torch-free, armv7)"""
    voice: str = Field(default="irina", description="ru_RU voice: irina | ruslan | denis | dmitri")
    speaker_id: int = Field(default=0, description="Speaker id within the voice model (single-speaker = 0)")
    speed: float = Field(default=1.0, ge=0.1, le=3.0, description="Speech speed multiplier (length_scale)")
    num_threads: int = Field(default=0, description="onnxruntime threads (0 = auto: armv7=2, else min(4,cores))")
    preload_models: bool = Field(default=False, description="Preload model during init (pay graph-init at boot)")


class PiperRuAccentProviderSchema(PiperProviderSchema):
    """Piper + RUAccent TTS provider schema (ARCH-24: Russian stress/homograph accentor, 64-bit only)"""
    omograph_model_size: str = Field(default="turbo", description="RUAccent homograph model: turbo | tiny | big")
    use_dictionary: bool = Field(default=True, description="Use RUAccent's stress dictionary")


# ============================================================
# AUDIO PROVIDER SCHEMAS
# ============================================================

class SoundDeviceProviderSchema(AudioProviderSchema):
    """SoundDevice provider configuration schema"""
    device: int = Field(default=-1, description="Audio output device ID for playback")
    sample_rate: int = Field(default=44100, description="Audio sample rate")
    volume: float = Field(default=1.0, ge=0.0, le=1.0, description="Playback volume")


class APlayProviderSchema(AudioProviderSchema):
    """APlay provider configuration schema"""
    device: str = Field(default="default", description="ALSA device name for audio output")
    volume: float = Field(default=1.0, ge=0.0, le=1.0, description="Playback volume")


class MiniaudioProviderSchema(AudioProviderSchema):
    """Miniaudio provider configuration schema (self-contained streaming backend)"""
    device: Optional[int] = Field(default=None, description="Playback device id (None = system default)")
    sample_rate: int = Field(default=44100, description="Output sample rate (Hz)")
    channels: int = Field(default=2, ge=1, le=2, description="Output channel count")
    buffersize_msec: int = Field(default=200, ge=10, le=2000, description="Device buffer size (ms)")
    volume: float = Field(default=1.0, ge=0.0, le=1.0, description="Playback volume")


class ConsoleAudioProviderSchema(AudioProviderSchema):
    """Console Audio provider configuration schema"""
    device: str = Field(default="console", description="Console output device mode")
    volume: float = Field(default=1.0, ge=0.0, le=1.0, description="Playback volume") 
    simulate_timing: bool = Field(default=True, description="Simulate playback timing")


# ============================================================
# ASR PROVIDER SCHEMAS
# ============================================================

class WhisperProviderSchema(ASRProviderSchema):
    """Whisper provider configuration schema"""
    model_size: str = Field(default="base", description="Model size (tiny, base, small, medium, large)")
    device: str = Field(default="cpu", description="Device to run on (cpu, cuda)")
    default_language: Optional[str] = Field(default=None, description="Default language (None for auto-detect)")
    preload_models: bool = Field(default=False, description="Preload AI models during provider initialization")


class VoskASRProviderSchema(ASRProviderSchema):
    """Vosk ASR provider configuration schema"""
    default_language: str = Field(default="ru", description="Default language: ru, en")
    sample_rate: int = Field(default=16000, description="Audio sample rate")
    preload_models: bool = Field(default=False, description="Preload AI models during provider initialization")


class SherpaOnnxASRProviderSchema(ASRProviderSchema):
    """sherpa-onnx ASR provider configuration schema (ARCH-10: ONNX VOSK Zipformer2)"""
    model: str = Field(default="vosk-model-small-ru", description="Model pack id: vosk-model-small-ru | vosk-model-ru")
    model_type: str = Field(default="vosk-transducer", description="Model family: vosk-transducer (whisper-onnx in PR-2)")
    default_language: str = Field(default="ru", description="Model language (alphacep VOSK packs are Russian)")
    sample_rate: int = Field(default=16000, description="Audio sample rate (Zipformer2 frontend is 16 kHz)")
    num_threads: int = Field(default=4, description="Inference threads (platform default: armv7=2, else min(4,cores))")
    decoding_method: str = Field(default="greedy_search", description="greedy_search | modified_beam_search")
    preload_models: bool = Field(default=False, description="Preload model during init (pay graph-init at boot)")


class VoskTTSProviderSchema(TTSProviderSchema):
    """Vosk TTS provider configuration schema"""
    default_language: str = Field(default="ru", description="Default language: ru, en, de, fr")
    sample_rate: int = Field(default=22050, description="Audio sample rate")
    voice_speed: float = Field(default=1.0, ge=0.1, le=3.0, description="Voice speed multiplier")
    preload_models: bool = Field(default=False, description="Preload AI models during provider initialization")


class GoogleCloudProviderSchema(ASRProviderSchema):
    """Google Cloud provider configuration schema"""
    credentials_path: str = Field(description="Path to credentials (use ${GOOGLE_APPLICATION_CREDENTIALS})")
    project_id: str = Field(description="Google Cloud project ID")
    default_language: str = Field(default="en-US", description="Default language")
    sample_rate_hertz: int = Field(default=16000, description="Sample rate in Hz")
    encoding: str = Field(default="LINEAR16", description="Audio encoding")


# ============================================================
# LLM PROVIDER SCHEMAS
# ============================================================

class OpenAIProviderSchema(LLMProviderSchema):
    """OpenAI provider configuration schema"""
    api_key: str = Field(description="OpenAI API key (use ${OPENAI_API_KEY})")
    model: str = Field(default="gpt-4", description="Model to use")
    max_tokens: int = Field(default=16384, ge=1, description="Maximum tokens")
    context_window: int = Field(default=128000, description="Input context window (tokens); default = the model capability (QUAL-52)")
    target_language: str = Field(default="English", description="Target language for translation")


class AnthropicProviderSchema(LLMProviderSchema):
    """Anthropic provider configuration schema"""
    api_key: str = Field(description="Anthropic API key (use ${ANTHROPIC_API_KEY})")
    model: str = Field(default="claude-3-haiku-20240307", description="Model to use")
    max_tokens: int = Field(default=8192, ge=1, description="Maximum tokens")
    context_window: int = Field(default=200000, description="Input context window (tokens); default = the model capability (QUAL-52)")


class DeepSeekProviderSchema(LLMProviderSchema):
    """DeepSeek provider configuration schema (OpenAI-compatible API)"""
    api_key: str = Field(description="DeepSeek API key (use ${DEEPSEEK_API_KEY})")
    base_url: str = Field(default="https://api.deepseek.com", description="DeepSeek API base URL")
    model: str = Field(default="deepseek-chat", description="Model: deepseek-chat (V3) | deepseek-reasoner (R1)")
    max_tokens: int = Field(default=8000, description="Maximum response tokens")
    context_window: int = Field(default=64000, description="Input context window (tokens); default = the model capability (QUAL-52)")


class ConsoleLLMProviderSchema(LLMProviderSchema):
    """Console (offline-floor) LLM provider config — deterministic, no network, no key."""
    pass


# ============================================================
# VOICE TRIGGER PROVIDER SCHEMAS
# ============================================================

class OpenWakeWordProviderSchema(VoiceTriggerProviderSchema):
    """OpenWakeWord provider configuration schema (QUAL-20: uniform per-provider WakeWordSpec list)."""
    wake_words: List[WakeWordSpec] = Field(
        default_factory=lambda: [WakeWordSpec(name="hey_jarvis", model="hey_jarvis")],
        description="Wake words to detect (uniform shape shared with microWakeWord)")
    inference_framework: str = Field(default="onnx", description="Inference framework: onnx (default, no torch) | tflite")
    preload_models: bool = Field(default=False, description="Preload AI models during provider initialization")


class MicroWakeWordProviderSchema(VoiceTriggerProviderSchema):
    """microWakeWord provider configuration schema (QUAL-20: thin adapter over pymicro-wakeword).

    The frontend/inference params (MFCC window/stride, feature buffer, detection window) are owned by
    the library now and were removed — only the uniform wake-word list and the micro-specific
    sliding window remain.
    """
    wake_words: List[WakeWordSpec] = Field(
        default_factory=lambda: [WakeWordSpec(name="okay_nabu", model="okay_nabu")],
        description="Wake words to detect (uniform shape shared with openWakeWord). `model` is a built-in "
                    "name or a path to a custom .tflite/manifest (a per-unit Russian model)")
    sliding_window_size: int = Field(default=5, ge=1, description="Probabilities averaged per detection (micro-specific)")
    preload_models: bool = Field(default=False, description="Preload AI models")


# ============================================================
# VAD PROVIDER SCHEMAS (ARCH-18)
# ============================================================

class EnergyVADProviderSchema(VADProviderSchema):
    """Energy / zero-crossing VAD provider configuration schema."""
    energy_threshold: float = Field(default=0.01, ge=0.0, le=1.0, description="RMS energy threshold for voice detection")
    sensitivity: float = Field(default=0.5, ge=0.1, le=3.0, description="Detection sensitivity multiplier")
    voice_frames_required: int = Field(default=2, ge=1, description="Consecutive voice frames to confirm onset")
    silence_frames_required: int = Field(default=5, ge=1, description="Consecutive silence frames to confirm voice end")
    use_zero_crossing_rate: bool = Field(default=True, description="Enable zero-crossing-rate analysis (adaptive engine)")
    adaptive_threshold: bool = Field(default=False, description="Enable adaptive threshold (adaptive engine)")
    noise_percentile: int = Field(default=15, ge=1, le=50, description="Percentile for noise floor estimation")
    voice_multiplier: float = Field(default=3.0, ge=1.0, le=10.0, description="Multiplier above noise floor for voice threshold")


class SileroVADProviderSchema(VADProviderSchema):
    """SileroVAD-ONNX (via sherpa-onnx) provider configuration schema. 64-bit only."""
    threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Speech-probability threshold")
    model_url: str = Field(default="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx", description="SileroVAD ONNX model URL (downloaded once into the asset folder)")
    voice_duration_ms: int = Field(default=100, ge=10, le=1000, description="Minimum speech duration (ms)")
    silence_duration_ms: int = Field(default=200, ge=50, le=2000, description="Minimum silence duration to end a segment (ms)")


class MicroVADProviderSchema(VADProviderSchema):
    """microVAD (pymicro-vad) provider configuration schema. 64-bit Linux only."""
    threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Speech-probability threshold")
    detection_latency_ms: int = Field(default=30, ge=0, description="Onset detection latency (ms) used to size the VAD pre-roll")


# ============================================================
# NLU PROVIDER SCHEMAS
# ============================================================

class HybridKeywordMatcherProviderSchema(NLUProviderSchema):
    """Hybrid Keyword Matcher provider configuration schema (Phase 1: Updated for complete feature set)"""
    provider_class: str = Field(default="HybridKeywordMatcherProvider", description="Provider class name")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum confidence for intent acceptance (normalized for Phase 1 consistency)")
    fuzzy_enabled: bool = Field(default=True, description="Enable fuzzy matching capabilities")
    fuzzy_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="Minimum fuzzy matching score threshold")
    pattern_confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="Base confidence for pattern matches")
    case_sensitive: bool = Field(default=False, description="Enable case-sensitive pattern matching")
    normalize_unicode: bool = Field(default=True, description="Enable improved Unicode normalization (Phase 1 enhancement)")
    cache_fuzzy_results: bool = Field(default=True, description="Enable caching of fuzzy matching results")
    max_fuzzy_keywords_per_intent: int = Field(default=50, ge=1, le=1000, description="Maximum fuzzy keywords per intent")
    min_pattern_length: int = Field(default=2, ge=1, le=100, description="Minimum pattern length for processing")


class SpaCyNLUProviderSchema(NLUProviderSchema):
    """SpaCy NLU provider configuration schema (Phase 1: Updated for multi-model support)"""
    provider_class: str = Field(default="SpaCyNLUProvider", description="Provider class name")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum confidence for intent acceptance")
    entity_types: List[str] = Field(
        default=["PERSON", "ORG", "GPE", "DATE", "TIME", "MONEY", "QUANTITY"],
        description="spaCy entity types to extract"
    )
    language_preferences: Dict[str, List[str]] = Field(
        default={
            "ru": ["ru_core_news_md", "ru_core_news_sm"],
            "en": ["en_core_web_md", "en_core_web_sm"]
        },
        description="Language-specific model preferences (Phase 1: Multi-model support)"
    )


class LLMNLUProviderSchema(NLUProviderSchema):
    """LLM NLU classifier — cascade fallback after keyword/spaCy (QUAL-50)."""
    provider_class: str = Field(default="LLMNLUProvider", description="Provider class name")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum confidence for intent acceptance")
    model: Optional[str] = Field(default=None, description="Pin a model (provider/model or model); None = the LLM component's default")
    provider: Optional[str] = Field(default=None, description="Pin an LLM provider; None = the LLM component's default chain")
    max_phrases_per_intent: int = Field(default=3, ge=0, le=20, description="Sample phrases per intent included in the classifier prompt (taxonomy budget)")


# ============================================================
# TEXT PROCESSOR PROVIDER SCHEMAS
# ============================================================

class PrepareOptions(BaseModel):
    """Structured configuration for PrepareNormalizer"""
    change_numbers: Literal["process", "skip"] = Field(default="process", description="How to handle numbers in text")
    change_latin: Literal["process", "skip"] = Field(default="process", description="How to handle Latin characters")
    change_symbols: str = Field(default=r"#$%&*+-/<=>@~[\]_`{|}№", description="Symbols to replace with words")
    keep_symbols: str = Field(default=r",.?!;:() ", description="Symbols to keep unchanged")
    delete_unknown_symbols: bool = Field(default=True, description="Delete unrecognized symbols")


class NumberOptions(BaseModel):
    """Structured configuration for NumberNormalizer"""
    decimal_places: int = Field(default=2, ge=0, le=10, description="Number of decimal places to preserve in conversion")
    handle_percentages: bool = Field(default=True, description="Convert percentage numbers to text (e.g., '15%' → 'пятнадцать процентов')")
    handle_ranges: bool = Field(default=True, description="Process number ranges (e.g., '5-10' → 'от пяти до десяти')")
    handle_negatives: bool = Field(default=True, description="Convert negative numbers (e.g., '-5' → 'минус пять')")
    handle_fractions: bool = Field(default=True, description="Process fractional numbers (e.g., '1/2' → 'одна вторая')")
    handle_ordinals: bool = Field(default=True, description="Handle ordinal numbers (e.g., '1st' → 'первый')")
    max_number_length: int = Field(default=15, ge=1, le=50, description="Maximum digits in a number to process (longer numbers remain as digits)")


class RunormOptions(BaseModel):
    """Structured configuration for RunormNormalizer (advanced Russian text normalization)"""
    model_size: Literal["small", "medium", "large"] = Field(default="small", description="RUNorm model size (affects quality vs speed)")
    device: Literal["cpu", "cuda"] = Field(default="cpu", description="Processing device for model inference")
    batch_size: int = Field(default=1, ge=1, le=64, description="Batch size for processing (affects memory usage)")
    model_cache: bool = Field(default=True, description="Cache loaded model in memory")
    streaming_mode: bool = Field(default=False, description="Enable streaming processing for long texts")


class TTSPerformanceOptions(BaseModel):
    """Performance tuning options for TTS text processor"""
    max_text_length: int = Field(default=1000, ge=1, le=10000, description="Maximum text length to process")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Processing timeout in seconds")
    fallback_on_error: bool = Field(default=True, description="Fallback to simpler processing on errors")
    skip_number_normalization: bool = Field(default=False, description="Skip number normalization step")
    skip_prepare_normalization: bool = Field(default=False, description="Skip text preparation step")
    skip_advanced_normalization: bool = Field(default=False, description="Skip RunormNormalizer step")


class UnifiedTextProcessorProviderSchema(TextProcessorProviderSchema):
    """Unified text-processor provider config (QUAL-13). The provider's own config is just `enabled`
    (inherited); the live per-stage normalizer chains live in the sibling `text_processor.normalizers`
    tree, which the component threads into the provider at construction."""
    pass


# ============================================================
# COMPONENT CONFIGURATION SCHEMAS
# ============================================================

class ComponentProviderConfigSchema(BaseModel):
    """Base schema for component provider configurations"""
    enabled: bool = Field(default=True, description="Enable component")
    default_provider: str = Field(description="Default provider name")
    fallback_providers: List[str] = Field(default_factory=list, description="Fallback providers")
    providers: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Provider configurations")


class TTSComponentSchema(ComponentProviderConfigSchema):
    """TTS component configuration schema"""
    default_provider: str = Field(default="console", description="Default TTS provider")
    fallback_providers: List[str] = Field(default_factory=lambda: ["console"], description="Fallback TTS providers")


class AudioComponentSchema(ComponentProviderConfigSchema):
    """Audio component configuration schema"""
    default_provider: str = Field(default="console", description="Default audio provider")
    fallback_providers: List[str] = Field(default_factory=lambda: ["console"], description="Fallback audio providers")
    concurrent_playback: bool = Field(default=False, description="Allow concurrent audio playback")


class ASRComponentSchema(ComponentProviderConfigSchema):
    """ASR component configuration schema"""
    # D (BUG-11): no provider-implying default (was "whisper", which invited configs that named a
    # provider with no matching [asr.providers.whisper] section → zero providers → every request failed).
    # Empty = "pick one explicitly"; mirrors the runtime ASRConfig staying off/None until configured.
    default_provider: str = Field(default="", description="Default ASR provider")
    fallback_providers: List[str] = Field(default_factory=list, description="Fallback ASR providers")


class LLMComponentSchema(ComponentProviderConfigSchema):
    """LLM component configuration schema"""
    default_provider: str = Field(default="openai", description="Default LLM provider")
    fallback_providers: List[str] = Field(default_factory=lambda: ["console"], description="Fallback LLM providers")


class VoiceTriggerComponentSchema(ComponentProviderConfigSchema):
    """Voice trigger component configuration schema"""
    default_provider: str = Field(default="openwakeword", description="Default voice trigger provider")
    wake_words: List[str] = Field(default_factory=lambda: ["irene", "jarvis"], description="Wake words to detect")
    confidence_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="Detection confidence threshold")
    buffer_seconds: float = Field(default=1.0, gt=0.0, description="Audio buffer duration in seconds")
    timeout_seconds: float = Field(default=5.0, gt=0.0, description="Detection timeout in seconds")


class NLUComponentSchema(ComponentProviderConfigSchema):
    """NLU component configuration schema"""
    default_provider: str = Field(default="hybrid_keyword_matcher", description="Default NLU provider")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Global confidence threshold")
    fallback_intent: str = Field(default="conversation.general", description="Fallback intent name")
    provider_cascade_order: List[str] = Field(
        default_factory=lambda: ["hybrid_keyword_matcher", "spacy_nlu"],
        description="Provider cascade order (fast to slow)"
    )
    max_cascade_attempts: int = Field(default=4, ge=1, description="Maximum cascade attempts")
    cascade_timeout_ms: int = Field(default=200, gt=0, description="Cascade timeout in milliseconds")
    cache_recognition_results: bool = Field(default=False, description="Cache recognition results")
    cache_ttl_seconds: int = Field(default=300, gt=0, description="Cache TTL in seconds")


class TextProcessorComponentSchema(BaseModel):
    """Text processor component configuration schema"""
    enabled: bool = Field(default=True, description="Enable text processor component")
    stages: List[str] = Field(
        default_factory=lambda: ["asr_output", "tts_input", "command_input", "general"],
        description="Processing stages"
    )
    normalizers: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Text normalizer configurations"
    )


class IntentSystemComponentSchema(BaseModel):
    """Intent system component configuration schema"""
    enabled: bool = Field(default=True, description="Enable intent system component")
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for intent recognition"
    )
    fallback_intent: str = Field(
        default="conversation.general",
        description="Fallback intent when recognition fails"
    )
    handlers: Dict[str, Any] = Field(
        default_factory=dict,
        description="Intent handler configuration"
    )


class MonitoringComponentSchema(ComponentProviderConfigSchema):
    """Monitoring component configuration schema"""
    enabled: bool = Field(default=True, description="Enable monitoring component")
    default_provider: str = Field(default="console", description="Default monitoring provider")
    fallback_providers: List[str] = Field(default_factory=lambda: ["console"], description="Fallback monitoring providers")
    metrics_enabled: bool = Field(default=True, description="Enable metrics collection")
    dashboard_enabled: bool = Field(default=True, description="Enable dashboard")


class NLUAnalysisComponentSchema(ComponentProviderConfigSchema):
    """NLU Analysis component configuration schema"""
    enabled: bool = Field(default=True, description="Enable NLU analysis component")
    default_provider: str = Field(default="console", description="Default NLU analysis provider")
    fallback_providers: List[str] = Field(default_factory=lambda: ["console"], description="Fallback NLU analysis providers")
    conflict_detection_enabled: bool = Field(default=True, description="Enable conflict detection")
    performance_analysis_enabled: bool = Field(default=True, description="Enable performance analysis")


class ConfigurationComponentSchema(ComponentProviderConfigSchema):
    """Configuration component configuration schema"""
    enabled: bool = Field(default=False, description="Enable configuration management component")
    default_provider: str = Field(default="console", description="Default configuration provider")
    fallback_providers: List[str] = Field(default_factory=lambda: ["console"], description="Fallback configuration providers")
    web_api_enabled: bool = Field(default=True, description="Enable web API endpoints")
    hot_reload_enabled: bool = Field(default=True, description="Enable hot configuration reload")


# ============================================================
# AUDIO DEVICE SCHEMAS
# ============================================================

class AudioDeviceInfo(BaseModel):
    """Audio input device information schema"""
    id: int = Field(description="Device ID for selection")
    name: str = Field(description="Human-readable device name")
    channels: int = Field(description="Maximum input channels supported")
    sample_rate: int = Field(description="Default sample rate in Hz")
    is_default: bool = Field(description="Whether this is the system default input device")


class AudioDevicesResponse(BaseModel):
    """Response schema for available audio devices endpoint"""
    success: bool = Field(default=True, description="Operation success status")
    devices: List[AudioDeviceInfo] = Field(description="List of available audio input devices")
    total_count: int = Field(description="Total number of devices found")
    message: Optional[str] = Field(default=None, description="Optional status message")


# ============================================================
# SCHEMA VALIDATION UTILITIES
# ============================================================

class SchemaValidator:
    """Schema validation using auto-generated registries ONLY"""
    
    # NOTE: Manual PROVIDER_SCHEMAS registry removed in Phase 4.4.7
    # Provider discovery now happens ONLY through auto-registry and entry-points
    
    @classmethod
    def validate_provider_config(cls, component_type: str, provider_name: str, config: Dict[str, Any]) -> bool:
        """Validate using auto-discovery ONLY"""
        from .auto_registry import AutoSchemaRegistry
        return AutoSchemaRegistry.validate_provider_config(component_type, provider_name, config)
    
    @classmethod
    def validate_component_config(cls, component_type: str, config: Dict[str, Any]) -> bool:
        """Validate using auto-discovery ONLY"""
        from .auto_registry import AutoSchemaRegistry
        return AutoSchemaRegistry.validate_component_config(component_type, config)
    
    @classmethod
    def get_component_schemas(cls) -> Dict[str, Type[BaseModel]]:
        """Get component schemas (auto-generated from registry)"""
        from .auto_registry import AutoSchemaRegistry
        return AutoSchemaRegistry.get_component_schemas()
    
    @classmethod
    def get_provider_schemas(cls) -> Dict[str, Dict[str, Type[BaseModel]]]:
        """Get provider schemas (auto-generated from registry)"""
        from .auto_registry import AutoSchemaRegistry
        return AutoSchemaRegistry.get_provider_schemas()
    
    @classmethod
    def get_provider_schema(cls, component_type: str, provider_name: str) -> Optional[type]:
        """Get provider schema class (auto-generated)"""
        provider_schemas = cls.get_provider_schemas()
        if component_type not in provider_schemas:
            return None
        return provider_schemas[component_type].get(provider_name)
    
    @classmethod
    def get_component_schema(cls, component_type: str) -> Optional[type]:
        """Get component schema class (auto-generated)"""
        component_schemas = cls.get_component_schemas()
        return component_schemas.get(component_type)
    
    @classmethod
    def list_supported_providers(cls, component_type: str) -> List[str]:
        """List supported providers for a component type (auto-generated)"""
        provider_schemas = cls.get_provider_schemas()
        if component_type not in provider_schemas:
            return []
        return list(provider_schemas[component_type].keys())
    
    @classmethod
    def list_supported_components(cls) -> List[str]:
        """List supported component types (auto-generated)"""
        component_schemas = cls.get_component_schemas()
        return list(component_schemas.keys())


# ============================================================
# SCHEMA VERSION SUPPORT
# ============================================================

class SchemaVersion(BaseModel):
    """Schema version information"""
    major: int = Field(default=14, description="Major version")
    minor: int = Field(default=0, description="Minor version")
    patch: int = Field(default=0, description="Patch version")
    
    @property
    def version_string(self) -> str:
        """Get version as string"""
        return f"{self.major}.{self.minor}.{self.patch}"
    
    def is_compatible_with(self, other: 'SchemaVersion') -> bool:
        """Check if this version is compatible with another"""
        # Same major version is compatible
        return self.major == other.major


# Current schema version
CURRENT_SCHEMA_VERSION = SchemaVersion(major=14, minor=0, patch=0)


def get_schema_version() -> SchemaVersion:
    """Get current schema version"""
    return CURRENT_SCHEMA_VERSION


def validate_schema_compatibility(config_version: str) -> bool:
    """Validate if config version is compatible with current schema"""
    try:
        parts = config_version.split(".")
        config_schema_version = SchemaVersion(
            major=int(parts[0]),
            minor=int(parts[1]) if len(parts) > 1 else 0,
            patch=int(parts[2]) if len(parts) > 2 else 0
        )
        return CURRENT_SCHEMA_VERSION.is_compatible_with(config_schema_version)
    except (ValueError, IndexError):
        return False
