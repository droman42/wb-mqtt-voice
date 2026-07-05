"""
Domain capability ports (QUAL-24).

Hexagon (Invariant #3): intent **handlers are the domain** (innermost layer) and
must depend only on abstractions the domain owns — never reach outward into the
application/composition root. Previously the handlers fetched components via
`from ...core.engine import get_core` (a service-locator that made the domain
reach into core, transitively pulling components/inputs/workflows).

These ABCs are those domain-owned abstractions. Handlers depend on them
(sideways, within `intents/`); the application-layer components **inherit** them
(`components → intents.ports` is application→domain, i.e. inward) and the
application injects the components into the handlers. Making them abstract base
classes (not structural Protocols) means a component that fails to implement a
port method cannot be instantiated — the gap fails loudly at startup instead of
surfacing as a latent `AttributeError`.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .device_catalog import DeviceCatalog


class ComponentControlPort(ABC):
    """Provider-management surface shared by capability components.

    These are the `Component`-base operations the system/control handlers use to
    introspect and switch providers (concrete implementations live in
    `irene/components/base.Component`).
    """
    providers: Dict[str, Any]

    @abstractmethod
    def get_providers_info(self) -> str: ...

    @abstractmethod
    def set_default_provider(self, provider_name: str) -> bool: ...

    @abstractmethod
    def parse_provider_name_from_text(self, text: str) -> Optional[str]: ...


class LLMPort(ABC):
    """LLM capability used by conversation / translation / text-enhancement."""

    @abstractmethod
    async def is_available(self) -> bool: ...

    @abstractmethod
    async def generate_response(self, *args: Any, **kwargs: Any) -> Any: ...

    @abstractmethod
    async def enhance_text(self, text: str, *, task: str, **kwargs: Any) -> Any: ...

    @abstractmethod
    def extract_text_from_command(self, command: str) -> Any: ...

    @abstractmethod
    def extract_translation_request(self, command: str) -> Any: ...


class TTSPort(ComponentControlPort):
    """Text-to-speech capability used by the voice-synthesis handler."""

    @abstractmethod
    async def speak(self, text: str, *args: Any, **kwargs: Any) -> Any: ...

    @abstractmethod
    async def stop_synthesis(self) -> Any: ...

    @abstractmethod
    async def cancel_synthesis(self) -> Any: ...


class AudioPort(ComponentControlPort):
    """Audio-playback capability used by the audio-playback handler."""

    @abstractmethod
    async def play_file(self, file_path: Path, **kwargs: Any) -> Any: ...

    @abstractmethod
    async def pause_audio(self) -> Any: ...

    @abstractmethod
    async def resume_audio(self) -> Any: ...

    @abstractmethod
    async def stop_playback(self) -> Any: ...


class ASRPort(ComponentControlPort):
    """Speech-recognition capability used by the speech-recognition handler."""

    @abstractmethod
    async def switch_language(self, language: str) -> Tuple[bool, str]: ...


class DeviceCatalogPort(ABC):
    """Read/query access to the bridge's device catalog (ARCH-8, `mqtt_integration.md` §4/§13.3).

    The smart-home handlers and the `DeviceEntityResolver` depend on this port to
    resolve spoken surfaces against the catalog snapshot; the application-layer
    `CatalogService` (`core/catalog_service.py`) implements it. Strictly a read
    port — actuation is NOT here (the bridge is an `OutputPort`; a handler emits
    a `device_command`-modality result, §13.1/13.2).
    """

    @abstractmethod
    def catalog(self) -> Optional[DeviceCatalog]:
        """The current catalog snapshot, or None before the first successful pull."""
        ...

    @abstractmethod
    async def refresh(self) -> Optional[DeviceCatalog]:
        """Re-pull the catalog from its source and return the fresh snapshot.

        The ARCH-26 lazy-refresh seam: the resolver calls this on a resolution/
        actuation miss (unresolved name, or a bridge 4xx that smells stale) —
        self-correcting, at most one stale round-trip. Returns None if no source
        is wired or the pull fails (the caller keeps the previous snapshot).
        """
        ...


class DeviceCommandDeliveryPort(ABC):
    """Awaited delivery of one canonical device command to the designated bridge output
    (ARCH-8 PR-4, `mqtt_integration.md` §13.2).

    The smart-home handler builds a `CanonicalCommand` and awaits the rich delivery outcome
    to compose its spoken confirmation. The application implementation
    (`core/device_command_dispatcher.py`) wraps the OutputManager's DEVICE_COMMAND routing
    under a bounded timeout. Signatures are `Any`-typed on purpose: the outcome is the
    delivery layer's rich `DeliveryResult`, which the domain must not import (this module is
    pinned pure by the import contracts); `None` means undeliverable/timed out — the handler
    speaks a degraded confirmation instead of blocking.
    """

    @abstractmethod
    async def deliver_device_command(self, command: Any, context: Any) -> Any: ...


class ComponentControlRegistryPort(ABC):
    """Lookup of controllable components by name/type.

    Used only by the provider-control handler, which manages providers across
    *all* component types and therefore needs a registry rather than a single
    capability.
    """

    @abstractmethod
    def get_component(self, name: str) -> Optional[ComponentControlPort]: ...
