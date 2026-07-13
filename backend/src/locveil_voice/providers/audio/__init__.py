"""
Audio Providers - Audio playback implementation modules

This package contains audio provider implementations managed by UniversalAudioPlugin.

Available Providers:
- ConsoleAudioProvider: Console-based output for testing
- SoundDeviceAudioProvider: High-quality audio using sounddevice
- AplayAudioProvider: Linux ALSA audio using aplay
- MiniaudioAudioProvider: Self-contained cross-platform streaming (no system libs)

Only the ABC is imported eagerly; concrete providers load through their entry points, or lazily by
name here. `sounddevice` and `miniaudio` import numpy (their own extras) — a hard import here would
drag it into every build (BUG-34).
"""

from typing import Any

from .base import AudioProvider

__all__ = [
    "AudioProvider",
    "ConsoleAudioProvider",
    "SoundDeviceAudioProvider",
    "AplayAudioProvider",
    "MiniaudioAudioProvider",
]

_LAZY = {
    "ConsoleAudioProvider": ".console",
    "SoundDeviceAudioProvider": ".sounddevice",
    "AplayAudioProvider": ".aplay",
    "MiniaudioAudioProvider": ".miniaudio",
}


def __getattr__(name: str) -> Any:  # PEP 562: keep the public API, drop the eager import
    module = _LAZY.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module
    return getattr(import_module(module, __name__), name)
