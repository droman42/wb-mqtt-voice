"""
ASR (Automatic Speech Recognition) Providers

This module contains ASR provider implementations following the ABC inheritance pattern.
All providers inherit from the abstract ASRProvider base class.

Only the ABC is imported eagerly; concrete providers load through their entry points, or lazily by
name here, so importing this package never pulls a provider's optional dependencies (BUG-34).
"""

from typing import Any

from .base import ASRProvider

__all__ = [
    "ASRProvider",
    "VoskASRProvider",
    "WhisperASRProvider",
    "GoogleCloudASRProvider"
]

_LAZY = {
    "VoskASRProvider": ".vosk",
    "WhisperASRProvider": ".whisper",
    "GoogleCloudASRProvider": ".google_cloud",
}


def __getattr__(name: str) -> Any:  # PEP 562: keep the public API, drop the eager import
    module = _LAZY.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module
    return getattr(import_module(module, __name__), name)
