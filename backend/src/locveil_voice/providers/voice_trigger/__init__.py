"""
Voice Trigger Providers

Providers for wake word detection and voice trigger functionality.

Only the ABC is imported eagerly. Concrete providers load through their entry points, or lazily by
name here — importing this package must never pull a provider's optional dependencies (BUG-34: a
hard `import numpy` in `openwakeword` took out nine components on an image that disables wake-word
entirely). Same shape as `providers/vad/__init__.py`.
"""

from typing import Any

from .base import VoiceTriggerProvider

__all__ = [
    'VoiceTriggerProvider',
    'OpenWakeWordProvider',
    'MicroWakeWordProvider'
]

_LAZY = {
    'OpenWakeWordProvider': '.openwakeword',
    'MicroWakeWordProvider': '.microwakeword',
}


def __getattr__(name: str) -> Any:  # PEP 562: keep the public API, drop the eager import
    module = _LAZY.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module
    return getattr(import_module(module, __name__), name)
