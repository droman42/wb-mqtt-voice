"""
Component Port - The management contract for fundamental components.

ARCH-11 / S2: the abstraction that `core` (ComponentManager) depends on, lifted
into the port layer so `core` no longer imports `components.base` outward. The
fat shared implementation (provider switching, health, status, DI plumbing)
stays in `irene/components/base.Component`, which implements this port.

Rooted on `EntryPointMetadata` (decision (c)), matching the other capability
ports (`ASRPlugin`, `TTSPlugin`, …) and the live `Component` hierarchy.
"""

from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod

from ..metadata import EntryPointMetadata
from ...intents.ports import ComponentControlPort


class ComponentPort(EntryPointMetadata, ComponentControlPort, ABC):
    """
    Port for fundamental components.

    Declares only the generic, manager-facing surface ComponentManager relies
    on. Component-specific capabilities (e.g. TTS `synthesize_to_file`, audio
    `play_file`) are not part of this contract and remain accessed via the
    concrete component types. See `irene/components/base.Component` for the
    shared implementation.

    Extends `ComponentControlPort` (the domain-owned provider-control surface):
    every fundamental component is also controllable, so the component registry
    (`ComponentControlRegistryPort`) can hand out `ComponentPort`s where the
    control surface is expected. `core -> intents` is the established inward
    direction (cf. `core/interfaces/input.py`, `…/workflow.py`).
    """

    # Instance attributes established by the implementation's __init__:
    providers: Dict[str, Any]
    initialized: bool

    # Read-only property supplied by the implementation (concrete components
    # expose `name` as a @property).
    @property
    def name(self) -> str: ...

    @abstractmethod
    async def initialize(self, core: Any) -> None:
        """Initialize the component (and its providers). `core` is required —
        the composition root always passes it (QUAL-4d)."""
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """Shut the component down and release resources."""
        ...

    @abstractmethod
    def inject_dependency(self, name: str, dependency: Any) -> None:
        """Inject a named dependency for cross-component wiring."""
        ...

    @abstractmethod
    def get_dependency(self, name: str) -> Optional[Any]:
        """Return a previously injected dependency, or None."""
        ...

    @abstractmethod
    def get_component_dependencies(self) -> List[str]:
        """Return the names of other components this one depends on."""
        ...

    @abstractmethod
    def get_service_dependencies(self) -> Dict[str, type]:
        """Return the service protocols this component requires from core."""
        ...
