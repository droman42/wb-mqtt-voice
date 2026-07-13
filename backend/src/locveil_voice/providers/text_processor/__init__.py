"""
Text Processing Providers

QUAL-13: one config-driven processor (`UnifiedTextProcessor`) with per-stage normalizer chains,
replacing the 4 stage-specific providers (which were decorative routing around one number call).
"""

from .base import TextProcessingProvider
from .unified import UnifiedTextProcessor

__all__ = [
    'TextProcessingProvider',
    'UnifiedTextProcessor',
]
