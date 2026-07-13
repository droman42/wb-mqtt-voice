"""
Text Processor Plugin Interface — text normalization / processing.

Capability port (ARCH-4) that the text-processor component implements. Adapters
(the stage-specific text processors) implement the separate `TextProcessingProvider`
base in `providers/text_processor/base.py`.
"""

from abc import abstractmethod

from ..metadata import EntryPointMetadata
from ...intents.context_models import UnifiedConversationContext


class TextProcessorPlugin(EntryPointMetadata):
    """Interface for text-processing capability: normalize/transform text for the pipeline."""

    @abstractmethod
    async def process(self, text: str, context: UnifiedConversationContext) -> str:
        """Process/normalize the input text and return the result."""
        ...
