"""Tests for the shared Unicode-script helpers (review CR-C3)."""
import unittest

from irene.utils.text_script import (
    is_cyrillic, is_latin, is_cjk, contains_cyrillic, cyrillic_char_count,
    detect_language_by_script,
)


class TestTextScript(unittest.TestCase):
    def test_cyrillic_boundaries(self):
        self.assertTrue(all(is_cyrillic(c) for c in ("Ѐ", "ӿ", "п", "Я")))  # U+0400..U+04FF
        self.assertFalse(any(is_cyrillic(c) for c in ("Ͽ", "Ԁ", "a", "5")))  # U+03FF / U+0500 / latin

    def test_latin_and_cjk(self):
        self.assertTrue(is_latin("A") and is_latin("z") and not is_latin("5") and not is_latin("п"))
        self.assertTrue(is_cjk("一") and is_cjk("鿿") and not is_cjk("a"))  # U+4E00..U+9FFF

    def test_detect_language_by_script(self):
        self.assertEqual(detect_language_by_script("привет"), "ru")
        self.assertEqual(detect_language_by_script("hello"), "en")
        self.assertEqual(detect_language_by_script("hi привет"), "ru")  # any cyrillic → ru
        self.assertEqual(detect_language_by_script(""), "en")

    def test_counts(self):
        self.assertEqual(cyrillic_char_count("aбвc"), 2)
        self.assertTrue(contains_cyrillic("aбc"))
        self.assertFalse(contains_cyrillic("abc123"))


if __name__ == "__main__":
    unittest.main()
