"""
Irene Core Module - Async Engine and Core Components

This module contains the main AsyncVACore engine and core system components.
"""

from .engine import AsyncVACore
# CommandResult removed - use IntentResult instead
# AsyncTimerManager removed (QUAL-61): it never scheduled anything — the durable-action
# store + startup reconciler (ARCH-28) is the scheduler.
from .components import ComponentManager, ComponentNotAvailable
from .metadata import EntryPointMetadata

__all__ = [
    "AsyncVACore",
    "ComponentManager",
    "ComponentNotAvailable",
    "EntryPointMetadata"
]