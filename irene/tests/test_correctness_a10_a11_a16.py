"""Regression tests for review CR-A10 (ASR rate negotiation), CR-A11 (null text entity),
CR-A16 (self-routing handlers must clarify, not swallow, ParameterExtractionError)."""
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from irene.providers.asr.base import ASRProvider
from irene.intents.handlers.voice_synthesis_handler import VoiceSynthesisIntentHandler
from irene.intents.handlers.datetime import DateTimeIntentHandler
from irene.core.donations import ParameterExtractionError


def _arun(coro):
    return asyncio.run(coro)


class TestAsrAudioContract(unittest.TestCase):
    """CR-A10: audio_contract must read get_preferred_sample_rates (was get_supported_sample_rates,
    a voice-trigger-only name, so rates were always [16000])."""

    def test_honors_preferred_rates(self):
        fake = SimpleNamespace(get_preferred_sample_rates=lambda: [48000, 16000])
        self.assertEqual(ASRProvider.audio_contract(fake).supported_rates, [48000, 16000])

    def test_defaults_to_16k_when_none(self):
        fake = SimpleNamespace(get_preferred_sample_rates=lambda: None)
        self.assertEqual(ASRProvider.audio_contract(fake).supported_rates, [16000])


class TestVoiceSynthesisNullText(unittest.TestCase):
    """CR-A11: an explicit `text: null` entity must not crash `.strip()`."""

    def test_null_text_entity_does_not_crash(self):
        h = object.__new__(VoiceSynthesisIntentHandler)
        h._get_tts_component = AsyncMock(return_value=object())  # truthy component
        sentinel = object()
        h._error_result = MagicMock(return_value=sentinel)
        intent = SimpleNamespace(entities={"text": None}, raw_text=None)
        res = _arun(h._handle_speak_text(intent, SimpleNamespace(language="ru")))
        self.assertIs(res, sentinel)  # returned the "No text to speak" error, no AttributeError
        h._error_result.assert_called_once()


class TestSelfRoutingClarification(unittest.TestCase):
    """CR-A16: a self-routing handler's execute() must route ParameterExtractionError to _clarify
    (the QUAL-30 boundary) instead of swallowing it in the broad except."""

    def _handler(self, side_effect):
        h = object.__new__(DateTimeIntentHandler)
        h.logger = MagicMock()
        h._handle_date_request = AsyncMock(side_effect=side_effect)
        return h

    def test_parameter_error_routed_to_clarify(self):
        h = self._handler(ParameterExtractionError("missing day"))
        sentinel = object()
        h._clarify = AsyncMock(return_value=sentinel)
        intent = SimpleNamespace(action="current_date", name="datetime.current_date")
        res = _arun(h.execute(intent, SimpleNamespace()))
        self.assertIs(res, sentinel)
        h._clarify.assert_awaited_once()

    def test_generic_error_not_clarified(self):
        h = self._handler(RuntimeError("boom"))
        h._clarify = AsyncMock()
        intent = SimpleNamespace(action="current_date", name="datetime.current_date")
        res = _arun(h.execute(intent, SimpleNamespace()))
        h._clarify.assert_not_awaited()           # generic error stays a terminal error
        self.assertFalse(res.success)


if __name__ == "__main__":
    unittest.main()
