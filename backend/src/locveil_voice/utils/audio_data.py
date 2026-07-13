"""Foundational audio / signal IO primitives.

These are generic data containers for the audio pipeline — they belong to no
domain and depend on nothing inside ``irene``. They were split out of
``irene/intents/models.py`` (ARCH-1) so that low-level producers/consumers
(``utils.audio_helpers``, ``utils.vad``, voice-trigger providers, the workflow)
no longer have to import *up* into the intent domain just to get an IO type.

Home rationale: kept at ``utils`` (rank 0) rather than ``core`` so that the
``utils.*`` importers reference it *sideways* instead of creating a new
``utils → core`` upward edge.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class WakeWordResult:
    """Result of wake word detection."""

    detected: bool
    confidence: float
    word: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    audio_data: Optional[bytes] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AudioData:
    """Audio data container for processing pipeline."""

    data: bytes
    timestamp: float
    sample_rate: int = 16000
    channels: int = 1
    format: str = "pcm16"
    metadata: Dict[str, Any] = field(default_factory=dict)
