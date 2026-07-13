"""Voice-activity-detection provider family (ARCH-18 PR-2).

A lightweight provider family — discovered via the `locveil_voice.providers.vad` entry-points and selected by
`[vad] default_provider`, consumed by the `VoiceSegmenter`. No component/manager (VAD is a per-frame
primitive). Providers: `energy` (built-in), `silero` (sherpa-onnx), `microvad` (pymicro-vad).
"""

from .base import VADProvider

__all__ = ["VADProvider"]
