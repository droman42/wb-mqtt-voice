"""Fundamental components for the voice assistant system.

Only the ABC is imported eagerly. Components load through their entry points, or lazily by name
here. Importing one component must not import the other eight (BUG-34): this package's eager import
list meant a single unusable optional dependency — `openwakeword`'s numpy, for a wake-word provider
the armv7 profile disables — failed the whole package, and the components that happened to sit
*above* it in this file survived only by already being in `sys.modules`.
"""

from typing import Any

from .base import Component

__all__ = [
    "Component",
    "TTSComponent",
    "ASRComponent",
    "LLMComponent",
    "AudioComponent",
    "VoiceTriggerComponent",
    "NLUComponent",
    "TextProcessorComponent",
    "IntentComponent",
]

_LAZY = {
    "TTSComponent": ".tts_component",
    "ASRComponent": ".asr_component",
    "LLMComponent": ".llm_component",
    "AudioComponent": ".audio_component",
    "VoiceTriggerComponent": ".voice_trigger_component",
    "NLUComponent": ".nlu_component",
    "TextProcessorComponent": ".text_processor_component",
    "IntentComponent": ".intent_component",
}


def __getattr__(name: str) -> Any:  # PEP 562: keep the public API, drop the eager import
    module = _LAZY.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module
    return getattr(import_module(module, __name__), name)
