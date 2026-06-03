"""
Input Port - The capability contract for input sources

Consolidated port for all input sources (microphone, web, CLI, remote …).

ARCH-11 / decision (c): this is the single input port. It re-roots onto
`EntryPointMetadata` (the live discovery/metadata base shared by Component,
ProviderBase, Workflow, IntentHandler) and lives in `core/interfaces` so that
`core` depends on the abstraction inward, while `irene/inputs/` adapters
implement it. It replaces the former `InputSource` (was in `inputs.base`,
created a `core → inputs.base` edge) and the dead duplicate `InputPlugin`
(was `PluginInterface`-rooted, 0 concrete subclasses).
"""

from typing import AsyncIterator, Dict, Any, Union
from abc import ABC, abstractmethod

from ..metadata import EntryPointMetadata
from ...intents.models import AudioData


# Type alias for input data - can be text commands or raw audio data
InputData = Union[str, AudioData]


class InputPort(EntryPointMetadata, ABC):
    """
    Abstract port for input sources.

    Provides an async-iterator interface for command streams. Implemented by
    the adapters in `irene/inputs/` (CLI/web text → str, microphone → AudioData).
    """

    @abstractmethod
    def listen(self) -> AsyncIterator[InputData]:
        """
        Start listening for input and yield data as it arrives.

        Yields:
            InputData - either text commands (str) or audio data (AudioData)
            - CLI/Web text: str
            - Microphone: AudioData
            - Web audio: Could be either
        """
        # This is an async generator method
        # Implementations should use: async def listen(self) -> AsyncIterator[InputData]:
        # with yield statements inside
        return
        yield  # This makes it an async generator

    @abstractmethod
    async def start_listening(self) -> None:
        """Initialize and start the input source."""
        pass

    @abstractmethod
    async def stop_listening(self) -> None:
        """Stop listening and clean up resources."""
        pass

    def is_listening(self) -> bool:
        """
        Check if currently listening for input.

        Returns:
            True if actively listening
        """
        return False

    def is_available(self) -> bool:
        """
        Check if input source is available.

        Returns:
            True if input source can be used
        """
        return True

    def get_input_type(self) -> str:
        """
        Get the type of input this source handles.

        Returns:
            Input type identifier (e.g., 'microphone', 'web', 'cli')
        """
        return "unknown"

    def get_settings(self) -> Dict[str, Any]:
        """
        Get current input settings.

        Returns:
            Dictionary of current settings
        """
        return {}

    async def configure_input(self, **settings) -> None:
        """
        Configure input source settings.

        Args:
            **settings: Input-specific configuration options
        """
        pass

    async def test_input(self) -> bool:
        """
        Test if input source is working correctly.

        Returns:
            True if input test was successful
        """
        return True
