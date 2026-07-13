"""
NLU Providers

Natural Language Understanding providers for intent recognition and entity extraction.

Only the ABC is imported eagerly; concrete providers load through their entry points, or lazily by
name here. `spacy_provider` imports numpy, which ships with its `nlu-spacy` extra — a hard import
here would drag it into builds that run the keyword/LLM cascade (BUG-34).
"""

from typing import Any

from .base import NLUProvider

__all__ = [
    'NLUProvider',
    'SpaCyNLUProvider'
]

_LAZY = {'SpaCyNLUProvider': '.spacy_provider'}


def __getattr__(name: str) -> Any:  # PEP 562: keep the public API, drop the eager import
    module = _LAZY.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module
    return getattr(import_module(module, __name__), name)
