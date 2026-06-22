"""Unicode script helpers — the single source of truth for Cyrillic/Latin/CJK character ranges and the
script-based ru/en language guess (CR-C3).

These were copy-pasted across the NLU providers/components (spaCy, hybrid keyword matcher, LLM NLU, the
NLU component's language detection, and the analysis hybrid_analyzer), with one site even using literal
`"Ѐ"`/`"ӿ"` bounds. Centralising prevents the cascade from disagreeing when the ranges are tweaked.
"""


def is_cyrillic(ch: str) -> bool:
    """True for the basic Cyrillic block (U+0400–U+04FF)."""
    return "Ѐ" <= ch <= "ӿ"


def is_latin(ch: str) -> bool:
    """True for ASCII Latin letters (A–Z, a–z)."""
    return "A" <= ch <= "Z" or "a" <= ch <= "z"


def is_cjk(ch: str) -> bool:
    """True for the CJK Unified Ideographs block (U+4E00–U+9FFF)."""
    return "一" <= ch <= "鿿"


def contains_cyrillic(text: str) -> bool:
    """Whether `text` contains any Cyrillic character."""
    return any(is_cyrillic(ch) for ch in text)


def cyrillic_char_count(text: str) -> int:
    """Number of Cyrillic characters in `text`."""
    return sum(1 for ch in text if is_cyrillic(ch))


def detect_language_by_script(text: str) -> str:
    """The cross-NLU language split: 'ru' if any Cyrillic character is present, else 'en'."""
    return "ru" if contains_cyrillic(text) else "en"
