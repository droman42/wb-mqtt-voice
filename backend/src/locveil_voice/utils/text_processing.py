"""
Text Processing Utilities

Modern async-compatible text processing utilities for Irene Voice Assistant.
Migrated from legacy utils/ with improvements:
- Async/await support
- Modern Python 3.11+ patterns  
- Type annotations
- Better error handling
- Optional dependencies
"""

import asyncio
import decimal
import logging
import re
from typing import Union

logger = logging.getLogger(__name__)

# Russian number-to-text conversion constants
# Migrated from utils/num_to_text_ru.py

UNITS = (
    'ноль',
    ('один', 'одна'),
    ('два', 'две'),
    'три', 'четыре', 'пять',
    'шесть', 'семь', 'восемь', 'девять'
)

TEENS = (
    'десять', 'одиннадцать',
    'двенадцать', 'тринадцать',
    'четырнадцать', 'пятнадцать',
    'шестнадцать', 'семнадцать',
    'восемнадцать', 'девятнадцать'
)

TENS = (
    TEENS,
    'двадцать', 'тридцать',
    'сорок', 'пятьдесят',
    'шестьдесят', 'семьдесят',
    'восемьдесят', 'девяносто'
)

HUNDREDS = (
    'сто', 'двести',
    'триста', 'четыреста',
    'пятьсот', 'шестьсот',
    'семьсот', 'восемьсот',
    'девятьсот'
)

ORDERS = (  # plural forms and gender
    (('тысяча', 'тысячи', 'тысяч'), 'f'),
    (('миллион', 'миллиона', 'миллионов'), 'm'),
    (('миллиард', 'миллиарда', 'миллиардов'), 'm'),
)

MINUS = 'минус'


def _thousand(rest: int, sex: str) -> tuple[int, list[str]]:
    """
    Convert numbers from 19 to 999 to Russian text.
    
    Args:
        rest: Number to convert (0-999)
        sex: Gender ('m' for masculine, 'f' for feminine)
        
    Returns:
        Tuple of (plural_form_index, word_list)
    """
    prev = 0
    plural = 2
    name = []
    use_teens = rest % 100 >= 10 and rest % 100 <= 19
    
    if not use_teens:
        data = ((UNITS, 10), (TENS, 100), (HUNDREDS, 1000))
    else:
        data = ((TEENS, 10), (HUNDREDS, 1000))
        
    for names, x in data:
        cur = int(((rest - prev) % x) * 10 / x)
        prev = rest % x
        
        if x == 10 and use_teens:
            plural = 2
            name.append(TEENS[cur])
        elif cur == 0:
            continue
        elif x == 10:
            name_ = names[cur]
            if isinstance(name_, tuple):
                name_ = name_[0 if sex == 'm' else 1]
            name.append(name_)
            if cur >= 2 and cur <= 4:
                plural = 1
            elif cur == 1:
                plural = 0
            else:
                plural = 2
        else:
            name.append(names[cur-1])
            
    return plural, name


def num_to_text_ru(num: int, main_units: tuple[tuple[str, str, str], str] = (('', '', ''), 'm')) -> str:
    """
    Convert integer to Russian text representation.
    
    Args:
        num: Integer to convert
        main_units: Tuple of ((singular, few, many), gender) for the main unit
        
    Returns:
        Russian text representation of the number
        
    Examples:
        >>> num_to_text_ru(123)
        'сто двадцать три'
        >>> num_to_text_ru(1, (('штука', 'штуки', 'штук'), 'f'))
        'одна штука'
    """
    _orders = (main_units,) + ORDERS
    
    if num == 0:
        return ' '.join((UNITS[0], _orders[0][0][2])).strip()
    
    rest = abs(num)
    ord = 0
    name = []
    
    while rest > 0:
        plural, nme = _thousand(rest % 1000, _orders[ord][1])
        if nme or ord == 0:
            name.append(_orders[ord][0][plural])
        name += nme
        rest = int(rest / 1000)
        ord += 1
        
    if num < 0:
        name.append(MINUS)
        
    name.reverse()
    return ' '.join(name).strip()


def decimal_to_text_ru(
    value: Union[str, int, float, decimal.Decimal], 
    places: int = 2,
    int_units: tuple[tuple[str, str, str], str] = (('', '', ''), 'm'),
    exp_units: tuple[tuple[str, str, str], str] = (('', '', ''), 'm')
) -> str:
    """
    Convert decimal number to Russian text representation.
    
    Args:
        value: Decimal value to convert
        places: Number of decimal places
        int_units: Units for the integer part
        exp_units: Units for the decimal part
        
    Returns:
        Russian text representation of the decimal number
        
    Examples:
        >>> decimal_to_text_ru("12.34", int_units=(('рубль', 'рубля', 'рублей'), 'm'), 
        ...                   exp_units=(('копейка', 'копейки', 'копеек'), 'f'))
        'двенадцать рублей тридцать четыре копейки'
    """
    value = decimal.Decimal(str(value))
    q = decimal.Decimal(10) ** -places
    
    integral, exp = str(value.quantize(q)).split('.')
    return '{} {}'.format(
        num_to_text_ru(int(integral), int_units),
        num_to_text_ru(int(exp), exp_units)
    )


# Text processing with lingua_franca integration
# Migrated from utils/all_num_to_text.py


# ovos-number-parser (ru) converts only NOMINATIVE numerals; the oblique-case forms common in speech
# («одну секунду», «двух минут», «без пяти», «тридцати пяти») are left as words — and even break
# compounds («тридцать одну» → "30 одну"). Remap the oblique cardinals ovos MISSES to their nominative
# before ovos, so the digit conversion (incl. compounds) still fires. Forms ovos already handles
# (одна/одно/одной/одним → 1, сорока → 40) are intentionally absent; words that collide with non-numeric
# meanings are excluded so plain text is never mangled (семью=family, сорока=magpie — both handled/left
# by ovos anyway). (BUG-7)
_RU_OBLIQUE_NUMERALS = {
    "одну": "один", "одного": "один",
    "двух": "два", "двум": "два", "двумя": "два",
    "трёх": "три", "трех": "три", "трём": "три", "трем": "три", "тремя": "три",
    "четырёх": "четыре", "четырех": "четыре", "четырём": "четыре", "четырем": "четыре", "четырьмя": "четыре",
    "пяти": "пять", "пятью": "пять",
    "шести": "шесть", "шестью": "шесть",
    "семи": "семь",
    "восьми": "восемь", "восьмью": "восемь", "восемью": "восемь",
    "девяти": "девять", "девятью": "девять",
    "десяти": "десять", "десятью": "десять",
    "одиннадцати": "одиннадцать", "двенадцати": "двенадцать", "пятнадцати": "пятнадцать",
    "двадцати": "двадцать", "тридцати": "тридцать", "пятидесяти": "пятьдесят",
    "девяноста": "девяносто", "ста": "сто", "двухсот": "двести",
}
_RU_OBLIQUE_RE = re.compile(r"\b(" + "|".join(_RU_OBLIQUE_NUMERALS) + r")\b", re.IGNORECASE)


def _ru_oblique_to_nominative(text: str) -> str:
    """Map oblique-case ru cardinals ovos can't read to their nominative (BUG-7); idempotent on others."""
    return _RU_OBLIQUE_RE.sub(lambda m: _RU_OBLIQUE_NUMERALS[m.group(0).lower()], text)


def normalize_numbers_to_digits(text: str, language: str = "ru") -> str:
    """Convert spelled-out numbers in `text` to digits — for COMPREHENSION / parameter extraction.

    This is the **reverse** of `num_to_text_ru` / `pronounce_number` (which exist for *synthesis*,
    digits→words): «десять минут» → «10 минут», "ten minutes" → "10 minutes", including compounds
    («двадцать пять» → «25»). Idempotent on digits and on number-free text. Both Russian and English
    (and other `ovos-number-parser` languages); returns the text **unchanged** if the language is
    unsupported or parsing fails — extraction then degrades to the digit-only path, never worse.

    This is the missing direction the extractors needed: every parameter extractor matched `\\d+`
    only, so spoken numerals were silently dropped (BUG-1).
    """
    try:
        from ovos_number_parser import numbers_to_digits  # type: ignore
        if language == "ru":
            text = _ru_oblique_to_nominative(text)  # BUG-7: oblique-case cardinals → nominative first
            # BUG-24: ovos maps a STANDALONE «пол» to 0.5 («тёплый пол» → «тёплый 0.5»),
            # destroying the floor-heating device reference. «пол» means "half" only before a
            # measure word («пол часа»); anywhere else it is the FLOOR — guard it through the
            # conversion. (Inflections «полу»/«пола» are not converted by ovos; only the exact
            # nominative needs the guard.)
            # A Latin token survives ovos untouched (non-word chars get stripped by it);
            # improbable enough to never occur in speech, restored immediately after.
            sentinel = "xxpolguardxx"
            guarded: list = []

            def _guard(match: "re.Match[str]") -> str:
                guarded.append(match.group())
                return sentinel

            text = re.sub(
                r"\bпол\b(?!\s+(?:час|минут|секунд|градус|процент|литр|стакан|метр|кило))",
                _guard, text, flags=re.IGNORECASE)
            converted = numbers_to_digits(text, lang=language)
            for original in guarded:
                converted = converted.replace(sentinel, original, 1)
            return converted
        return numbers_to_digits(text, lang=language)
    except Exception:
        return text


def _convert_one_num_float(match_obj: "re.Match[str]", language: str = "ru") -> str:
    """Convert a single matched number to words.

    Russian goes through the in-repo pure-Python implementation (`num_to_text_ru`/`decimal_to_text_ru`)
    — it's dependency-free (works on the offline/edge target without any extra) and gives proper Russian
    words rather than ovos's literal "точка". Other languages use **ovos-number-parser** (the maintained
    successor of the abandoned lingua-franca; optional `text-multilingual` extra); if it's absent the
    number is left as digits rather than crashing.
    """
    s = match_obj.group()
    if s is None:
        return s
    if language == "ru":
        try:
            return decimal_to_text_ru(s) if '.' in s else num_to_text_ru(int(s))
        except (ValueError, decimal.InvalidOperation):
            logger.warning(f"Could not convert number: {s}")
            return s
    try:
        from ovos_number_parser import pronounce_number  # type: ignore
        return pronounce_number(float(s), lang=language)
    except Exception:
        logger.debug(f"ovos-number-parser unavailable for '{language}' — leaving number raw: {s}")
        return s


def _convert_diapazon(match_obj: re.Match, language: str = "ru") -> str:
    """Convert range (e.g., '120-130') to text."""
    if match_obj.group() is not None:
        text = str(match_obj.group())
        text = text.replace("-", " тире ")
        return all_num_to_text(text, language)
    return match_obj.group()


def all_num_to_text(text: str, language: str = "ru") -> str:
    """
    Convert all numbers in text to spoken representation.
    
    This function processes various number formats:
    - Integers: "123" → "сто двадцать три"
    - Decimals: "12.34" → "двенадцать целых тридцать четыре сотых"
    - Ranges: "120-130" → "сто двадцать тире сто тридцать"
    - Negative numbers: "-10" → "минус десять"
    - Percentages: "50%" → "пятьдесят процентов"
    
    Args:
        text: Input text containing numbers
        language: Language code (default: "ru" for Russian)
        
    Returns:
        Text with numbers converted to words
        
    Examples:
        >>> all_num_to_text("У меня 5 яблок и 2.5 кг груш")
        'У меня пять яблок и два целых пять десятых кг груш'
        >>> all_num_to_text("Температура -10 градусов")
        'Температура минус десять градусов'
    """
    # Bind the per-call language into the regex callbacks (ovos-number-parser is stateless — no global
    # `load_language` as lingua-franca had; QUAL-13/ASSET-3).
    from functools import partial
    conv = partial(_convert_one_num_float, language=language)
    diap = partial(_convert_diapazon, language=language)

    # Process different number patterns in order of complexity
    # Decimal ranges (e.g., "120.1-120.8")
    text = re.sub(r'[\d]*[.][\d]+-[\d]*[.][\d]+', diap, text)

    # Negative decimals (e.g., "-30.1")
    text = re.sub(r'-[\d]*[.][\d]+', conv, text)

    # Positive decimals (e.g., "44.05")
    text = re.sub(r'[\d]*[.][\d]+', conv, text)

    # Integer ranges (e.g., "5-10")
    text = re.sub(r'[\d]-[\d]+', diap, text)

    # Negative integers (e.g., "-10")
    text = re.sub(r'-[\d]+', conv, text)

    # Positive integers (e.g., "123")
    text = re.sub(r'[\d]+', conv, text)

    # Convert percentages
    text = text.replace("%", " процентов")

    return text


# Async versions for modern v13 architecture

async def num_to_text_ru_async(num: int, main_units: tuple[tuple[str, str, str], str] = (('', '', ''), 'm')) -> str:
    """Async version of num_to_text_ru for non-blocking operation."""
    return await asyncio.to_thread(num_to_text_ru, num, main_units)


async def decimal_to_text_ru_async(
    value: Union[str, int, float, decimal.Decimal], 
    places: int = 2,
    int_units: tuple[tuple[str, str, str], str] = (('', '', ''), 'm'),
    exp_units: tuple[tuple[str, str, str], str] = (('', '', ''), 'm')
) -> str:
    """Async version of decimal_to_text_ru for non-blocking operation."""
    return await asyncio.to_thread(decimal_to_text_ru, value, places, int_units, exp_units)


async def all_num_to_text_async(text: str, language: str = "ru") -> str:
    """
    Async version of all_num_to_text for non-blocking operation.
    
    This is the main function that should be used in v13 async plugins.
    """
    return await asyncio.to_thread(all_num_to_text, text, language)


# Legacy compatibility functions for migration period

def load_language(lang: str) -> None:
    """No-op kept for back-compat. lingua-franca needed a global `load_language`; its successor
    ovos-number-parser is stateless (language is passed per call), so there is nothing to load."""
    logger.debug(f"load_language({lang!r}) is a no-op (ovos-number-parser is stateless)")


# Phase 4 Enhancement: Unified Text Processing Pipeline
# Following the document specification for normalizer migration

# Number-normalization helpers only. The text-processing pipeline is the single config-driven
# UnifiedTextProcessor (locveil_voice.providers.text_processor.unified) with per-stage normalizer chains (QUAL-13).


# Original normalizer classes moved to irene/utils/text_normalizers.py
# Backward compatibility maintained through __getattr__ above


# Normalizer classes have been moved to locveil_voice.utils.text_normalizers
# Import them directly from there:
# from locveil_voice.utils.text_normalizers import NumberNormalizer, PrepareNormalizer, RunormNormalizer

# Export commonly used functions
__all__ = [
    'num_to_text_ru',
    'decimal_to_text_ru', 
    'all_num_to_text',
    'num_to_text_ru_async',
    'decimal_to_text_ru_async',
    'all_num_to_text_async',
    'load_language'
] 