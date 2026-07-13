"""Shared inference policy for the sherpa-onnx provider family (ARCH-24 T5).

The sherpa-onnx ASR, VAD and Piper-TTS providers all run onnxruntime sessions and all need the same
**thread/CPU budget** decision. This was duplicated (a `SherpaInferencePolicy` in the ASR provider, a
`_num_threads()` in the Piper provider, and the silero VAD ignoring it entirely). Factor it here so
every sherpa provider reads one policy and `num_threads` is set consistently on the A7/A53.

This is **not** a shared session — each provider still builds its own sherpa object (the
`from_transducer` / `from_whisper` / `VoiceActivityDetector` / `OfflineTts` APIs don't unify). Only
the thread/CPU budget is shared.
"""

import os
import platform
from dataclasses import dataclass
from typing import Optional


@dataclass
class InferencePolicy:
    """Platform-aware CPU budget for an onnxruntime session.

    armv7 stays conservative (2 threads) so it doesn't oversubscribe the 4 Cortex-A7 cores while
    locveil-bridge runs on the same box; 64-bit uses up to 4.
    """

    num_threads: int
    provider: str = "cpu"  # onnxruntime execution provider

    @classmethod
    def for_platform(cls, override: Optional[int] = None) -> "InferencePolicy":
        if override and override > 0:
            return cls(num_threads=int(override))
        machine = platform.machine().lower()
        if machine.startswith("armv7") or machine.startswith("armv6"):
            return cls(num_threads=2)  # leave headroom for the co-tenant bridge on the WB7
        return cls(num_threads=min(4, os.cpu_count() or 2))
