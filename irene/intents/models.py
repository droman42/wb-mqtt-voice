"""Core domain data models for the intent system.

Holds the intent-domain types ``Intent`` / ``IntentResult``. Conversation-context
types live in the sibling ``context_models`` module (ARCH-1); audio IO primitives
live in ``utils.audio_data`` (re-exported below only as a back-compat shim).
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ARCH-1 back-compat shim: AudioData/WakeWordResult canonical home is utils.audio_data
from ..utils.audio_data import AudioData, WakeWordResult  # noqa: F401


@dataclass
class Intent:
    """Represents a recognized user intent with extracted entities."""
    
    name: str                          # "weather.get_current"
    entities: Dict[str, Any]           # {"location": "Moscow", "time": "now"}
    confidence: float                  # 0.95
    raw_text: str                      # Original user text
    timestamp: float = field(default_factory=time.time)
    domain: Optional[str] = None       # "weather", "timer", "conversation"
    action: Optional[str] = None       # "get_current", "set", "cancel"
    session_id: str = "default"       # Session identifier
    
    def __post_init__(self):
        """Extract domain and action from intent name if not provided."""
        if self.domain is None or self.action is None:
            parts = self.name.split(".", 1)
            if len(parts) == 2:
                self.domain = self.domain or parts[0]
                self.action = self.action or parts[1]
            else:
                self.domain = self.domain or "general"
                self.action = self.action or parts[0]


@dataclass  
class IntentResult:
    """Result of intent execution with response and metadata."""
    
    text: str                          # Response text
    should_speak: bool = True          # Whether to use TTS
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional data
    actions: List[str] = field(default_factory=list)        # Additional actions to perform (deprecated - kept for compatibility)
    action_metadata: Dict[str, Any] = field(default_factory=dict)  # NEW: Action context updates for fire-and-forget execution
    success: bool = True               # Whether execution was successful
    error: Optional[str] = None        # Error message if failed
    confidence: float = 1.0            # Confidence in the response
    timestamp: float = field(default_factory=time.time)

