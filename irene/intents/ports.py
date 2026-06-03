"""
Domain capability ports (QUAL-24).

Hexagon (Invariant #3): intent **handlers are the domain** (innermost layer) and
must depend only on abstractions the domain owns — never reach outward into the
application/composition root. Previously the handlers fetched components via
`from ...core.engine import get_core` (a service-locator that made the domain
reach into core, transitively pulling components/inputs/workflows).

These Protocols are those domain-owned abstractions. Handlers depend on them
(sideways, within `intents/`); the application layer (`IntentComponent`) injects
the real components inward as **structural** implementations — the components do
not import these Protocols, so no new edges are created and dependencies point
inward. Consumer-defined: each method/attribute is exactly what some handler
uses, nothing more.
"""

from typing import Any, Optional, Protocol, Tuple


class ComponentControlPort(Protocol):
    """Provider-management surface shared by capability components.

    These are the `Component`-base operations the system/control handlers use to
    introspect and switch providers.
    """
    providers: dict

    def get_providers_info(self) -> str: ...
    def set_default_provider(self, name: str) -> bool: ...
    def parse_provider_name_from_text(self, text: str) -> Optional[str]: ...


class LLMPort(Protocol):
    """LLM capability used by conversation / translation / text-enhancement."""

    async def is_available(self) -> bool: ...
    async def generate_response(self, *args: Any, **kwargs: Any) -> Any: ...
    async def enhance_text(self, text: str, *, task: str, **kwargs: Any) -> Any: ...
    def extract_text_from_command(self, text: str) -> Any: ...
    def extract_translation_request(self, text: str) -> Any: ...


class TTSPort(ComponentControlPort, Protocol):
    """Text-to-speech capability used by the voice-synthesis handler."""

    async def speak(self, text: str, *args: Any, **kwargs: Any) -> Any: ...
    async def stop_synthesis(self) -> Any: ...
    async def cancel_synthesis(self) -> Any: ...


class AudioPort(ComponentControlPort, Protocol):
    """Audio-playback capability used by the audio-playback handler."""

    async def pause_audio(self) -> Any: ...
    async def resume_audio(self) -> Any: ...
    async def stop_playback(self) -> Any: ...


class ASRPort(ComponentControlPort, Protocol):
    """Speech-recognition capability used by the speech-recognition handler."""

    async def switch_language(self, language: str) -> Tuple[bool, str]: ...


class ComponentControlRegistryPort(Protocol):
    """Lookup of controllable components by name/type.

    Used only by the provider-control handler, which manages providers across
    *all* component types and therefore needs a registry rather than a single
    capability.
    """

    def get_component(self, name: str) -> Optional[ComponentControlPort]: ...
