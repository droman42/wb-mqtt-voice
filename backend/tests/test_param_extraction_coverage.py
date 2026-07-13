"""
TEST-4 — parameter extraction coverage: the 8 ParameterTypes via HybridKeywordMatcher._extract_by_type.

The hybrid matcher (the live primary NLU provider) was at 0%. This characterizes its type-coercion
surface — the explicit `_extract_by_type` branch per ParameterType, plus `_convert_and_validate_parameter`
(the shared `coerce` contract) and `validate_config`. Hermetic: `_extract_by_type` uses no instance
state, so object.__new__ suffices.
"""

import unittest

from locveil_voice.core.donations import ParameterSpec, ParameterType
from locveil_voice.providers.nlu.hybrid_keyword_matcher import HybridKeywordMatcherProvider


def _m():
    return object.__new__(HybridKeywordMatcherProvider)


def _spec(ptype, **kw):
    return ParameterSpec(name="p", type=ptype, **kw)


class TestExtractByType(unittest.TestCase):
    def setUp(self):
        self.m = _m()

    def test_integer(self):
        self.assertEqual(self.m._extract_by_type("поставь 5 минут", _spec(ParameterType.INTEGER)), 5)
        self.assertIsNone(self.m._extract_by_type("no digits here", _spec(ParameterType.INTEGER)))

    def test_float(self):
        self.assertEqual(self.m._extract_by_type("set to 2.5", _spec(ParameterType.FLOAT)), 2.5)

    def test_boolean_true_false_and_none(self):
        b = _spec(ParameterType.BOOLEAN)
        self.assertIs(self.m._extract_by_type("включи свет", b), True)
        self.assertIs(self.m._extract_by_type("yes please", b), True)
        self.assertIs(self.m._extract_by_type("выключи это", b), False)
        self.assertIs(self.m._extract_by_type("no thanks", b), False)
        self.assertIsNone(self.m._extract_by_type("maybe", b))

    def test_choice_fuzzy_matches_canonical(self):
        s = _spec(ParameterType.CHOICE, choices=["fast", "slow"])
        self.assertEqual(self.m._extract_by_type("use the fast mode", s), "fast")
        self.assertIsNone(self.m._extract_by_type("zzzzz qqqqq", s))

    def test_string_quoted_then_alias_then_none(self):
        self.assertEqual(self.m._extract_by_type('play "my song"', _spec(ParameterType.STRING)), "my song")
        self.assertEqual(
            self.m._extract_by_type("turn on kitchen", _spec(ParameterType.STRING, aliases=["kitchen"])),
            "kitchen")
        self.assertIsNone(self.m._extract_by_type("nothing matches", _spec(ParameterType.STRING)))

    def test_datetime_and_entity_fall_through_to_none(self):
        # _extract_by_type handles 6 of the 8 types explicitly; DATETIME/ENTITY are resolved elsewhere.
        self.assertIsNone(self.m._extract_by_type("at 5 pm", _spec(ParameterType.DATETIME)))
        self.assertIsNone(self.m._extract_by_type("the light", _spec(ParameterType.ENTITY)))


class TestConvertValidateAndConfig(unittest.TestCase):
    def test_convert_and_validate_delegates_to_coerce(self):
        m = _m()
        self.assertEqual(m._convert_and_validate_parameter("5", _spec(ParameterType.INTEGER)), 5)
        self.assertEqual(m._convert_and_validate_parameter("2.5", _spec(ParameterType.FLOAT)), 2.5)

    def test_validate_config_bounds(self):
        m = _m()
        m.confidence_threshold, m.fuzzy_threshold = 0.7, 0.8
        m.pattern_confidence, m.min_pattern_length = 0.5, 2
        self.assertTrue(m.validate_config())
        m.confidence_threshold = 1.5    # out of [0,1]
        self.assertFalse(m.validate_config())
        m.confidence_threshold, m.fuzzy_threshold = 0.7, -0.1
        self.assertFalse(m.validate_config())
        m.fuzzy_threshold, m.min_pattern_length = 0.8, 0  # min_pattern_length must be >= 1
        self.assertFalse(m.validate_config())


if __name__ == "__main__":
    unittest.main()
