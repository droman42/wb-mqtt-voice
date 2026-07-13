"""
Plugin Interfaces - Interface definitions for all plugin types

This module defines the contracts that plugins must implement to integrate
with the Irene v13 async architecture.
"""

# PluginInterface/PluginManager removed in ARCH-13 (legacy plugin system retired).
# CommandPlugin removed in Phase 3
from .tts import TTSPlugin
from .audio import AudioPlugin
from .input import InputPort, InputData
from .webapi import WebAPIPlugin
from .asr import ASRPlugin
from .llm import LLMPlugin
from .nlu import NLUPlugin
from .text_processor import TextProcessorPlugin
from .voice_trigger import VoiceTriggerPlugin

__all__ = [
    "TTSPlugin",
    "AudioPlugin",
    "InputPort",
    "InputData",
    "WebAPIPlugin",
    "ASRPlugin",
    "LLMPlugin",
    "NLUPlugin",
    "TextProcessorPlugin",
    "VoiceTriggerPlugin",
]