"""Shared duration (time-unit) parsing — the ONE place value+unit time quantities are read.

Consolidates the bilingual time-unit parsing that used to be duplicated in `timer.py`
(`_parse_timer_from_text`/`unit_multipliers`), `entity_resolver.TemporalEntityResolver`, and the
time entries of `entity_resolver.QuantityEntityResolver`. Spelled-out numbers are normalized to
digits first (десять/ten → 10) so natural speech parses, not only digits.

Scope is deliberately TIME-only for now (the only unit family in use — the timer). A general
unit-of-measurement layer (percent, temperature, …) is intentionally NOT built here; it is designed
together with the smart-home device commands that need those units — see the ledger.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

from .text_processing import normalize_numbers_to_digits
from .text_script import detect_language_by_script

# Canonical time unit → (seconds multiplier, surface forms ru+en, longest-first within the regex).
TIME_UNITS: "dict[str, tuple[int, tuple[str, ...]]]" = {
    "seconds": (1, ("секунд", "секунда", "секунды", "секунду", "сек",
                    "seconds", "second", "secs", "sec")),
    "minutes": (60, ("минут", "минута", "минуты", "минуту", "мин",
                     "minutes", "minute", "mins", "min")),
    "hours":   (3600, ("часов", "часа", "часик", "час", "ч",
                       "hours", "hour", "hrs", "hr")),
    "days":    (86400, ("дней", "дня", "день",
                        "days", "day")),
}

# unit word → canonical, with the longest surfaces first so "минут" wins over "мин", "секунд" over "сек".
_SURFACE_TO_UNIT = {
    s: unit
    for unit, (_mult, surfaces) in TIME_UNITS.items()
    for s in sorted(surfaces, key=len, reverse=True)
}
_DURATION_RE = re.compile(
    r"(\d+)\s*(" + "|".join(re.escape(s) for s in sorted(_SURFACE_TO_UNIT, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def parse_duration(text: str, language: Optional[str] = None) -> Optional[Tuple[int, str]]:
    """Extract the first ``(value, canonical_unit)`` time quantity from `text` (ru + en).

    «поставь таймер на десять минут» / "set a timer for ten minutes" → ``(10, "minutes")``.
    Returns ``None`` when no time quantity is present. Language is by script when not given.
    """
    if not text:
        return None
    lang = language or detect_language_by_script(text)
    norm = normalize_numbers_to_digits(text.lower(), lang)
    m = _DURATION_RE.search(norm)
    if not m:
        return None
    return int(m.group(1)), _SURFACE_TO_UNIT[m.group(2).lower()]


def duration_to_seconds(value: int, unit: str) -> int:
    """Convert a ``(value, unit)`` time quantity to seconds. Unknown unit → treated as seconds."""
    mult = TIME_UNITS.get(unit, (1, ()))[0]
    return int(value) * mult


def parse_duration_seconds(text: str, language: Optional[str] = None) -> Optional[int]:
    """Parse a duration from `text` straight to seconds (``parse_duration`` + ``duration_to_seconds``)."""
    parsed = parse_duration(text, language)
    return duration_to_seconds(*parsed) if parsed else None
