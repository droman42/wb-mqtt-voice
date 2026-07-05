"""
TEST-5 — text-processor / normalizer coverage.

UnifiedTextProcessor (the provider) is covered by test_text_processing.py; this targets the actual
normalizers (irene/utils/text_normalizers.py 25%): the two LIVE ones — NumberNormalizer (number→words,
ru dependency-free path) and PrepareNormalizer (Cyrillic passthrough / symbol replacement / Latin→Cyrillic
/ inline number processing). RunormNormalizer is deliberately NOT exercised (it downloads a HuggingFace
model on first call) beyond its missing-dependency degradation. Hermetic, asyncio.run only.
"""

import asyncio
import unittest

import logging

from irene.utils.text_normalizers import NumberNormalizer, PrepareNormalizer, RunormNormalizer
from irene.components.text_processor_component import TextProcessorComponent


def _arun(coro):
    return asyncio.run(coro)


class TestNumberNormalizer(unittest.TestCase):
    def setUp(self):
        self.n = NumberNormalizer(language="ru")

    def test_digits_become_words(self):
        out = _arun(self.n.normalize("У меня 5 яблок"))
        self.assertNotIn("5", out)          # the digit is gone
        self.assertIn("пять", out.lower())  # ...replaced by the ru word

    def test_text_without_numbers_is_unchanged(self):
        self.assertEqual(_arun(self.n.normalize("просто текст без чисел")),
                         "просто текст без чисел")

    def test_empty_string(self):
        self.assertEqual(_arun(self.n.normalize("")), "")


class TestPrepareNormalizer(unittest.TestCase):
    def setUp(self):
        self.p = PrepareNormalizer(language="ru")

    def test_pure_cyrillic_and_punctuation_is_passthrough(self):
        # the fast early-return branch: nothing outside Cyrillic + allowed punctuation
        text = "привет, как дела?"
        self.assertEqual(_arun(self.p.normalize(text)), text)

    def test_latin_is_transcribed_to_cyrillic(self):
        out = _arun(self.p.normalize("test"))
        self.assertNotEqual(out, "test")
        # output should be Cyrillic (no Latin letters left)
        self.assertFalse(any("a" <= c.lower() <= "z" for c in out), out)

    def test_inline_numbers_are_processed(self):
        out = _arun(self.p.normalize("дай 3 штуки"))
        self.assertNotIn("3", out)

    def test_changelatin_disabled_keeps_latin(self):
        p = PrepareNormalizer(options={
            "changeNumbers": "process", "changeLatin": "skip",
            "changeSymbols": "", "keepSymbols": ",.?!;:() ", "deleteUnknownSymbols": False,
        }, language="ru")
        out = _arun(p.normalize("abc привет"))
        self.assertIn("abc", out)  # Latin left intact when changeLatin != 'process'


class TestRunormDegrades(unittest.TestCase):
    def test_missing_runorm_dependency_returns_text_unchanged(self):
        # Force the optional `runorm` import to fail → must degrade to the input text, never crash
        # (and never trigger a model download).
        import builtins
        real_import = builtins.__import__

        def fake_import(name, *a, **k):
            if name == "runorm":
                raise ImportError("no runorm")
            return real_import(name, *a, **k)

        r = RunormNormalizer()
        from unittest.mock import patch
        with patch.object(builtins, "__import__", side_effect=fake_import):
            self.assertEqual(_arun(r.normalize("текст 5")), "текст 5")


class TestComponentLiveMethods(unittest.TestCase):
    """The TextProcessorComponent's live, provider-independent methods (the bulk of the component is
    the review-confirmed dead stage routing / broken WebAPI — not exercised here)."""

    def _component(self):
        c = object.__new__(TextProcessorComponent)
        c.logger = logging.getLogger("test.txtproc")
        return c

    def test_process_without_providers_returns_text_unchanged(self):
        c = self._component()
        c.providers = {}  # no provider wired → degrade to passthrough
        self.assertEqual(_arun(c.process("У меня 5 яблок")), "У меня 5 яблок")

    def test_convert_numbers_to_words_converts(self):
        c = self._component()
        out = _arun(c.convert_numbers_to_words("ровно 7 штук", "ru"))
        self.assertNotIn("7", out)
        self.assertIn("семь", out.lower())

    def test_convert_numbers_to_words_degrades_on_error(self):
        c = self._component()
        # a non-string slips through the shared utility's guard → caught → original returned
        self.assertEqual(_arun(c.convert_numbers_to_words("no digits", "ru")), "no digits")


class TestDeviceSuiteRegressions(unittest.TestCase):
    """BUG-23/BUG-24 — input corruption caught live by the TEST-18 device suite."""

    def test_bug24_standalone_pol_is_the_floor_not_a_half(self):
        from irene.utils.text_processing import normalize_numbers_to_digits
        # «пол» = the FLOOR device reference; must survive words→digits normalization
        self.assertEqual(normalize_numbers_to_digits("тёплый пол на двадцать пять градусов", "ru"),
                         "тёплый пол на 25 градусов")
        # ... while «пол» before a measure word is still "half"
        self.assertEqual(normalize_numbers_to_digits("пол часа", "ru"), "0.5 часа")
        # alphanumeric values pass through untouched
        self.assertEqual(normalize_numbers_to_digits("переключи телек на hdmi1", "ru"),
                         "переключи телек на hdmi1")

    def test_bug23_numbers_normalizer_defaults_to_tts_only(self):
        from irene.config.models import TextProcessorConfig
        # the digits→words converter is SYNTHESIS-direction: it must never run before NLU
        # (asr_output), where it corrupted «hdmi1»→«hdmiодин» and «25»→«двадцать пять»
        stages = TextProcessorConfig().normalizers["numbers"]["stages"]
        self.assertEqual(stages, ["tts_input"])


if __name__ == "__main__":
    unittest.main()
