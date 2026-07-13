"""Characterization tests for SpeechRecognitionIntentHandler (TEST-7 / TEST-8).

Exercises the ASR-configuration handler as a domain object talking to its injected
``ASRPort`` capability through a stub — covering the provider switch (entity- and
text-sourced provider names, success and unavailable outcomes), the show / language /
quality / microphone handlers, donation-driven ``execute`` routing, ``can_handle``
pattern matching, and — the TEST-8 focus — graceful degradation when the ASR
component is absent (every component-backed handler returns a localized error result,
never raises).

The handler is built with ``object.__new__`` so none of the heavy base-class wiring
(donations, asset loader, metrics, notifications) runs; only the attributes each method
actually reads are stubbed. All async entrypoints go through ``asyncio.run`` so no event
loop survives a test, and no global singleton/registry/env is mutated.
"""

import asyncio
import unittest
from types import SimpleNamespace

from locveil_voice.intents.handlers.speech_recognition_handler import SpeechRecognitionIntentHandler
from locveil_voice.intents.models import Intent
from locveil_voice.intents.context_models import UnifiedConversationContext


class FakeASR:
    """Minimal stand-in for the injected ``ASRPort``.

    Records calls so the handler's delegation can be asserted; only the surface the
    handler touches (get_providers_info / set_default_provider /
    parse_provider_name_from_text / switch_language) is implemented.
    """

    def __init__(self, *, switch_ok=True, parsed=None, lang_result=(True, "language switched")):
        self._switch_ok = switch_ok
        self._parsed = parsed
        self._lang_result = lang_result
        self.set_calls = []
        self.switch_lang_calls = []

    def get_providers_info(self) -> str:
        return "providers: whisper, vosk"

    def set_default_provider(self, provider_name: str) -> bool:
        self.set_calls.append(provider_name)
        return self._switch_ok

    def parse_provider_name_from_text(self, text: str):
        return self._parsed

    async def switch_language(self, language: str):
        self.switch_lang_calls.append(language)
        return self._lang_result


class FakeAssetLoader:
    """Returns a format-string template per (category, name, language).

    Templates echo their placeholders so the handler's ``.format(**args)`` rendering
    is observable in the result text.
    """

    TEMPLATES = {
        "provider_switched": "switched to {provider_name}",
        "provider_unavailable": "{provider_name} unavailable",
        "quality_not_implemented": "quality {quality} not implemented",
        "microphone_not_implemented": "mic {microphone} not implemented",
        "error_configuration": "config error: {error}",
    }

    def get_template(self, category, template_name, language):
        return self.TEMPLATES.get(template_name)


def _handler(*, asr=None, asset_loader="default"):
    """Construct the handler without running base __init__ heavy wiring."""
    import logging
    h = object.__new__(SpeechRecognitionIntentHandler)
    h.name = "SpeechRecognitionIntentHandler"
    h.logger = logging.getLogger("test.speech_recognition_handler")
    h._asr_component = asr
    h.donation = None
    h._donation_initialized = False
    if asset_loader == "default":
        asset_loader = FakeAssetLoader()
    h.asset_loader = asset_loader
    h._asset_loader_initialized = asset_loader is not None
    return h


def _ctx(language="ru"):
    return UnifiedConversationContext(session_id="s1", client_id="kitchen", language=language)


def _intent(name="speech_recognition.switch_asr_provider", entities=None, raw_text=""):
    return Intent(name=name, entities=entities or {}, confidence=1.0, raw_text=raw_text)


# --------------------------------------------------------------------------- #
# Provider switch (TEST-8 main path)
# --------------------------------------------------------------------------- #
class TestSwitchProvider(unittest.TestCase):
    def test_switch_success_from_entity(self):
        asr = FakeASR(switch_ok=True)
        h = _handler(asr=asr)
        intent = _intent(entities={"provider": "whisper"})
        result = asyncio.run(h._handle_switch_asr_provider(intent, _ctx()))

        self.assertTrue(result.success)
        self.assertEqual(asr.set_calls, ["whisper"])
        self.assertEqual(result.text, "switched to whisper")
        self.assertEqual(result.metadata["action"], "switch_provider")
        self.assertEqual(result.metadata["provider"], "whisper")
        self.assertTrue(result.metadata["success"])

    def test_switch_unavailable_renders_unavailable_template(self):
        asr = FakeASR(switch_ok=False)
        h = _handler(asr=asr)
        intent = _intent(entities={"provider": "sherpa_onnx"})
        result = asyncio.run(h._handle_switch_asr_provider(intent, _ctx()))

        self.assertFalse(result.success)
        self.assertEqual(result.text, "sherpa_onnx unavailable")
        self.assertFalse(result.metadata["success"])

    def test_provider_name_parsed_from_text_when_no_entity(self):
        asr = FakeASR(switch_ok=True, parsed="vosk")
        h = _handler(asr=asr)
        intent = _intent(entities={}, raw_text="use vosk please")
        result = asyncio.run(h._handle_switch_asr_provider(intent, _ctx()))

        self.assertTrue(result.success)
        self.assertEqual(asr.set_calls, ["vosk"])
        self.assertEqual(result.metadata["provider"], "vosk")

    def test_no_provider_name_returns_error_result(self):
        asr = FakeASR(parsed=None)  # nothing in entities, nothing parsed
        h = _handler(asr=asr)
        intent = _intent(entities={}, raw_text="switch the engine")
        result = asyncio.run(h._handle_switch_asr_provider(intent, _ctx()))

        self.assertFalse(result.success)
        self.assertEqual(asr.set_calls, [])  # never delegated to the port
        self.assertEqual(result.text, "config error: Provider name not specified")


# --------------------------------------------------------------------------- #
# Other handlers
# --------------------------------------------------------------------------- #
class TestOtherHandlers(unittest.TestCase):
    def test_show_recognition_returns_providers_info(self):
        asr = FakeASR()
        h = _handler(asr=asr)
        result = asyncio.run(h._handle_show_recognition(_intent(), _ctx(language="en")))

        self.assertTrue(result.success)
        self.assertEqual(result.text, "providers: whisper, vosk")
        self.assertEqual(result.metadata["action"], "show_recognition")
        self.assertEqual(result.metadata["language"], "en")

    def test_switch_language_success(self):
        asr = FakeASR(lang_result=(True, "switched to english"))
        h = _handler(asr=asr)
        intent = _intent(name="speech_recognition.switch_language",
                         entities={"language": "english"})
        result = asyncio.run(h._handle_switch_language(intent, _ctx()))

        self.assertTrue(result.success)
        self.assertEqual(asr.switch_lang_calls, ["english"])
        self.assertEqual(result.text, "switched to english")
        self.assertEqual(result.metadata["target_language"], "english")

    def test_switch_language_defaults_to_russian_and_can_fail(self):
        asr = FakeASR(lang_result=(False, "unsupported language"))
        h = _handler(asr=asr)
        result = asyncio.run(h._handle_switch_language(_intent(), _ctx()))

        self.assertFalse(result.success)
        self.assertEqual(asr.switch_lang_calls, ["русский"])  # default when no entity
        self.assertEqual(result.text, "unsupported language")

    def test_configure_quality_not_implemented(self):
        # No ASR component needed — this handler never touches the port.
        h = _handler(asr=None)
        intent = _intent(name="speech_recognition.configure_quality",
                         entities={"quality": "low"})
        result = asyncio.run(h._handle_configure_quality(intent, _ctx()))

        self.assertFalse(result.success)
        self.assertFalse(result.metadata["implemented"])
        self.assertEqual(result.metadata["quality"], "low")
        self.assertEqual(result.text, "quality low not implemented")

    def test_configure_quality_default_quality_high(self):
        h = _handler(asr=None)
        result = asyncio.run(h._handle_configure_quality(_intent(), _ctx()))
        self.assertEqual(result.metadata["quality"], "high")

    def test_configure_microphone_not_implemented(self):
        h = _handler(asr=None)
        intent = _intent(name="speech_recognition.configure_microphone",
                         entities={"microphone": "usb_mic"})
        result = asyncio.run(h._handle_configure_microphone(intent, _ctx()))

        self.assertFalse(result.success)
        self.assertFalse(result.metadata["implemented"])
        self.assertEqual(result.metadata["microphone"], "usb_mic")
        self.assertEqual(result.text, "mic usb_mic not implemented")


# --------------------------------------------------------------------------- #
# Graceful degradation — ASR component absent (TEST-8 focus)
# --------------------------------------------------------------------------- #
class TestGracefulDegradationWhenAbsent(unittest.TestCase):
    def test_get_asr_component_returns_none_when_not_injected(self):
        h = _handler(asr=None)
        self.assertIsNone(asyncio.run(h._get_asr_component()))

    def test_show_recognition_degrades(self):
        h = _handler(asr=None)
        result = asyncio.run(h._handle_show_recognition(_intent(), _ctx()))
        self.assertFalse(result.success)
        self.assertEqual(result.text, "config error: ASR component not available")

    def test_switch_provider_degrades(self):
        h = _handler(asr=None)
        intent = _intent(entities={"provider": "whisper"})
        result = asyncio.run(h._handle_switch_asr_provider(intent, _ctx()))
        self.assertFalse(result.success)
        self.assertEqual(result.text, "config error: ASR component not available")

    def test_switch_language_degrades(self):
        h = _handler(asr=None)
        result = asyncio.run(h._handle_switch_language(_intent(), _ctx()))
        self.assertFalse(result.success)
        self.assertEqual(result.text, "config error: ASR component not available")


# --------------------------------------------------------------------------- #
# can_handle pattern matching + execute routing
# --------------------------------------------------------------------------- #
class TestCanHandleAndRouting(unittest.TestCase):
    def test_can_handle_missing_donation_raises(self):
        h = _handler(asr=None)  # _donation_initialized False
        with self.assertRaises(RuntimeError):
            asyncio.run(h.can_handle(_intent()))

    def _with_donation(self, **patterns):
        h = _handler(asr=None)
        h.donation = SimpleNamespace(**patterns)
        h._donation_initialized = True
        return h

    def test_can_handle_matches_domain_pattern(self):
        h = self._with_donation(domain_patterns=["speech_recognition"],
                                intent_name_patterns=[], action_patterns=[])
        intent = _intent(name="speech_recognition.show", entities={})
        self.assertTrue(asyncio.run(h.can_handle(intent)))

    def test_can_handle_matches_intent_name_pattern(self):
        h = self._with_donation(domain_patterns=[],
                                intent_name_patterns=["speech_recognition.switch_asr_provider"],
                                action_patterns=[])
        self.assertTrue(asyncio.run(h.can_handle(_intent())))

    def test_can_handle_matches_action_pattern(self):
        h = self._with_donation(domain_patterns=[], intent_name_patterns=[],
                                action_patterns=["switch_asr_provider"])
        intent = _intent(name="speech_recognition.switch_asr_provider")
        self.assertTrue(asyncio.run(h.can_handle(intent)))

    def test_can_handle_no_match_returns_false(self):
        h = self._with_donation(domain_patterns=["other"], intent_name_patterns=[],
                                action_patterns=[])
        self.assertFalse(asyncio.run(h.can_handle(_intent(name="weather.get"))))

    def test_execute_routes_through_donation_to_switch_provider(self):
        asr = FakeASR(switch_ok=True)
        h = _handler(asr=asr)
        # donation-driven routing: intent_suffix -> method_name
        h.donation = SimpleNamespace(
            method_donations=[SimpleNamespace(intent_suffix="switch_asr_provider",
                                              method_name="_handle_switch_asr_provider")],
        )
        h._donation_initialized = True
        intent = _intent(name="speech_recognition.switch_asr_provider",
                         entities={"provider": "whisper"})
        result = asyncio.run(h.execute(intent, _ctx()))
        self.assertTrue(result.success)
        self.assertEqual(asr.set_calls, ["whisper"])


# --------------------------------------------------------------------------- #
# Template / asset-loader contract
# --------------------------------------------------------------------------- #
class TestTemplateContract(unittest.TestCase):
    def test_missing_asset_loader_is_fatal(self):
        h = _handler(asr=None, asset_loader=None)
        with self.assertRaises(RuntimeError):
            h._get_template("provider_switched", "ru", provider_name="x")

    def test_missing_template_is_fatal(self):
        h = _handler(asr=None)
        with self.assertRaises(RuntimeError):
            h._get_template("does_not_exist", "ru")

    def test_template_missing_format_arg_is_fatal(self):
        # Template references {provider_name} but the call supplies none → KeyError → RuntimeError.
        class BadLoader:
            def get_template(self, category, name, language):
                return "needs {provider_name}"

        h = _handler(asr=None, asset_loader=BadLoader())
        with self.assertRaises(RuntimeError):
            h._get_template("provider_switched", "ru")

    def test_static_dependency_metadata(self):
        self.assertEqual(SpeechRecognitionIntentHandler.get_python_dependencies(), [])
        self.assertIn("linux.ubuntu", SpeechRecognitionIntentHandler.get_platform_dependencies())
        self.assertIn("macos", SpeechRecognitionIntentHandler.get_platform_support())


if __name__ == "__main__":
    unittest.main()
