"""
Input Abstraction Layer - Multiple input source support

Provides abstraction for different input sources: microphone, web, CLI, etc.
V14 features configuration-driven input source discovery and management.
"""

from ..core.interfaces.input import InputPort  # the port (canonical home: core/interfaces; ARCH-11/S1)
from .manager import InputManager              # the orchestrator / input-layer composition point
from .cli import CLIInput
from .microphone import MicrophoneInput
from .web import WebInput

__all__ = [
    "InputManager",
    "InputPort",
    "CLIInput",
    "MicrophoneInput",
    "WebInput"
] 