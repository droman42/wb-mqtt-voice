"""BUG-1 — spelled-out numbers must reach numeric parameter extraction (ru + en)."""
import pytest

from locveil_voice.utils.text_processing import normalize_numbers_to_digits


@pytest.mark.parametrize("text, lang, expected_substr", [
    ("поставь таймер на десять минут", "ru", "10 минут"),
    ("на двадцать пять минут", "ru", "25 минут"),        # compound
    ("set a timer for ten minutes", "en", "10 minutes"),
    ("for twenty five minutes", "en", "25 minutes"),     # compound
])
def test_spelled_numbers_become_digits(text, lang, expected_substr):
    assert expected_substr in normalize_numbers_to_digits(text, lang)


@pytest.mark.parametrize("text, lang", [
    ("на 10 минут", "ru"),
    ("for 5 minutes", "en"),
])
def test_idempotent_on_digits(text, lang):
    assert normalize_numbers_to_digits(text, lang) == text


@pytest.mark.parametrize("text, lang", [
    ("поставь таймер", "ru"),
    ("hello there", "en"),
])
def test_number_free_text_unchanged(text, lang):
    assert normalize_numbers_to_digits(text, lang) == text


def test_unsupported_language_degrades_to_unchanged():
    # No exception, no worse than the old digit-only path — returns the text as-is.
    assert normalize_numbers_to_digits("десять минут", "zz") == "десять минут"


def test_ru_oblique_case_numerals():
    # BUG-7: ovos (ru) reads only NOMINATIVE numerals; oblique-case forms common in speech are
    # remapped to nominative first, including compounds. Ambiguous/non-numeric words stay intact.
    nd = normalize_numbers_to_digits
    assert nd("на одну секунду", "ru") == "на 1 секунду"
    assert nd("тридцать одну секунду", "ru") == "31 секунду"      # compound (was "30 одну секунду")
    assert nd("двух минут", "ru") == "2 минут"
    assert nd("двадцати пяти градусов", "ru") == "25 градусов"    # compound oblique
    assert nd("около ста метров", "ru") == "около 100 метров"
    # ambiguous / non-numeric words must NOT be mangled
    assert nd("о семью детях", "ru") == "о семью детях"           # семью = family, left alone
    assert nd("семья из пяти человек", "ru") == "семья из 5 человек"


def test_timer_duration_parses_spelled_and_english():
    # BUG-6: the timer's duration now comes from the shared bilingual parser (locveil_voice.utils.units), the
    # one place time quantities are read. Spelled ru/en, ru-compound, and digit regression.
    from locveil_voice.utils.units import parse_duration
    assert parse_duration("поставь таймер на десять минут") == (10, "minutes")
    assert parse_duration("на двадцать пять минут") == (25, "minutes")
    assert parse_duration("set a timer for ten minutes") == (10, "minutes")
    assert parse_duration("на 10 минут") == (10, "minutes")            # digit regression
