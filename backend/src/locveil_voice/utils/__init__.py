"""
Irene Voice Assistant Utilities

Modern utility functions for Irene v13:
- Component loading and dependency management
- Logging configuration
- Text processing and number-to-text conversion
"""

from .loader import safe_import, get_component_status, suggest_installation
from .logging import setup_logging, get_logger
from .text_processing import (
    num_to_text_ru,
    decimal_to_text_ru,
    all_num_to_text,
    num_to_text_ru_async,
    decimal_to_text_ru_async,
    all_num_to_text_async,
    load_language,
)
from .audio_helpers import (
    validate_audio_file,
    normalize_volume,
    format_audio_duration,
    detect_sample_rate,
    get_audio_devices,
    get_default_audio_device,
    get_audio_input_devices,
    get_default_audio_input_device,
    validate_audio_input_device,
    calculate_audio_buffer_size,
    supports_audio_file_format,
    get_audio_info,
    test_audio_playback_capability,
)

__all__ = [
    # Component loading utilities
    'safe_import',
    'get_component_status', 
    'suggest_installation',
    
    # Logging utilities
    'setup_logging',
    'get_logger',
    
    # Text processing utilities (migrated from legacy utils/)
    'num_to_text_ru',
    'decimal_to_text_ru',
    'all_num_to_text',
    'num_to_text_ru_async',
    'decimal_to_text_ru_async', 
    'all_num_to_text_async',
    'load_language',
    
    # Audio processing helpers
    'validate_audio_file',
    'normalize_volume',
    'format_audio_duration',
    'detect_sample_rate',
    'get_audio_devices',
    'get_default_audio_device', 
    'get_audio_input_devices',
    'get_default_audio_input_device',
    'validate_audio_input_device',
    'calculate_audio_buffer_size',
    'supports_audio_file_format',
    'get_audio_info',
    'test_audio_playback_capability'
] 