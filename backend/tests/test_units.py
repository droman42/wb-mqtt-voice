"""BUG-6 — the shared time-unit parser (irene/utils/units.py), the one place time quantities are read."""
import pytest

from locveil_voice.utils.units import parse_duration, duration_to_seconds, parse_duration_seconds


@pytest.mark.parametrize("text,language,expected", [
    ("set a timer for one second", "en", (1, "seconds")),     # the BUG-6 case (was → minutes)
    ("set a timer for 5 minutes", "en", (5, "minutes")),
    ("for 2 hours", "en", (2, "hours")),
    ("поставь таймер на десять минут", "ru", (10, "minutes")),  # spelled ru → digits
    ("на 30 секунд", "ru", (30, "seconds")),
    ("3 дня", "ru", (3, "days")),
    ("what time is it", "en", None),                            # no duration
])
def test_parse_duration(text, language, expected):
    assert parse_duration(text, language) == expected


def test_language_inferred_when_omitted():
    assert parse_duration("десять минут") == (10, "minutes")
    assert parse_duration("ten minutes") == (10, "minutes")


def test_longest_surface_wins():
    # "минут" must win over the shorter "мин" so the unit is minutes, not a mis-split.
    assert parse_duration("на 5 минут", "ru") == (5, "minutes")


@pytest.mark.parametrize("value,unit,seconds", [
    (1, "seconds", 1), (5, "minutes", 300), (2, "hours", 7200), (1, "days", 86400),
    (3, "unknown", 3),  # unknown unit → treated as seconds
])
def test_duration_to_seconds(value, unit, seconds):
    assert duration_to_seconds(value, unit) == seconds


def test_parse_duration_seconds():
    assert parse_duration_seconds("one second", "en") == 1
    assert parse_duration_seconds("две минуты", "ru") == 120
    assert parse_duration_seconds("no duration here", "en") is None
