"""
NLU Plugin Interface — natural-language understanding (intent recognition).

Capability port (ARCH-4) that the NLU component implements. Adapters (the
spaCy / keyword NLU providers) implement the separate `NLUProvider` base in
`providers/nlu/base.py`; this port is the application-facing capability contract.
"""

from abc import abstractmethod

from ..metadata import EntryPointMetadata
from ...intents.models import Intent
from ...intents.context_models import UnifiedConversationContext


class NLUPlugin(EntryPointMetadata):
    """Interface for NLU capability: recognize intent + entities from text (offline-first)."""

    @abstractmethod
    async def recognize(self, text: str, context: UnifiedConversationContext) -> Intent:
        """Recognize the user's intent (name, entities, confidence) from input text."""
        ...
