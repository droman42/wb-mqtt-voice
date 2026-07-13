"""Regression tests for the NLU-analysis donation loaders (review CR-A6).

Before the fix `_get_context_units` / `_get_all_intent_units` returned `[]`, so conflict detection and the
health score were hollow; `_donation_to_intent_unit` also read the wrong key (`methods` instead of the real
`method_donations` list), producing empty units even on the realtime path.
"""
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from locveil_voice.components.nlu_analysis_component import NLUAnalysisComponent


def _arun(coro):
    return asyncio.run(coro)


_DATA = {
    "timer":   {"ru": {"method_donations": [{"phrases": ["поставь таймер", "засеки время"], "lemmas": ["таймер"]}]}},
    "weather": {"ru": {"method_donations": [{"phrases": ["какая погода"]}]}},
}


class _FakeLoader:
    def get_all_handlers_with_languages(self):
        return {h: ["ru"] for h in _DATA}

    def get_language_phrasing_for_editing(self, handler, language):
        return _DATA.get(handler, {}).get(language)


def _component(with_source=True):
    c = object.__new__(NLUAnalysisComponent)
    c.logger = MagicMock()
    # The NLU component is injected by the manager (declared via get_component_dependencies).
    c.injected_dependencies = {}
    if with_source:
        c.injected_dependencies["nlu"] = SimpleNamespace(asset_loader=_FakeLoader())
    return c


class TestDonationToIntentUnit(unittest.TestCase):
    def test_reads_method_donations_list(self):
        u = _component()._donation_to_intent_unit("timer", "ru", _DATA["timer"]["ru"])
        self.assertEqual(u.phrases, ["поставь таймер", "засеки время"])
        self.assertEqual(u.lemmas, ["таймер"])

    def test_legacy_methods_dict_fallback(self):
        u = _component()._donation_to_intent_unit("x", "ru", {"methods": {"m1": {"phrases": ["hi"]}}})
        self.assertEqual(u.phrases, ["hi"])

    def test_empty_donation(self):
        self.assertEqual(_component()._donation_to_intent_unit("x", "ru", {}).phrases, [])


class TestIntentUnitLoaders(unittest.TestCase):
    def test_all_units_enumerated(self):
        names = sorted(u.handler_name for u in _arun(_component()._get_all_intent_units("ru")))
        self.assertEqual(names, ["timer", "weather"])

    def test_context_excludes_candidate(self):
        ctx = _arun(_component()._get_context_units("ru", exclude_handler="timer"))
        self.assertEqual([u.handler_name for u in ctx], ["weather"])

    def test_context_excludes_candidate_with_handler_suffix(self):
        ctx = _arun(_component()._get_context_units("ru", exclude_handler="timer_handler"))
        self.assertEqual([u.handler_name for u in ctx], ["weather"])

    def test_empty_when_no_source(self):
        self.assertEqual(_arun(_component(with_source=False)._get_all_intent_units("ru")), [])

    def test_declares_nlu_dependency(self):
        # The injected pattern: declaring this drives init order + injection (no core-reach).
        self.assertEqual(_component().get_component_dependencies(), ["nlu"])


if __name__ == "__main__":
    unittest.main()
