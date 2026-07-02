"""Characterization tests for VoiceSynthesisIntentHandler (TEST-7 Phase D / TEST-8 part 1).

Covers the TTS-synthesis intent handler as a PORT consumer plus the QUAL-24 injection
wiring. The handler is built with its (lightweight) real constructor; the heavy collaborators
(TTS component, asset loader) are replaced by minimal stubs so no real models / audio / booted
core are touched. Every test drives its own event loop via ``asyncio.run`` and mutates no global
singletons — the fire-and-forget code path (which reaches the global client registry and spawns
background tasks) is deliberately NOT exercised here; only the directly-callable action coroutines
and the synchronous handlers are.

Two behaviours are asserted:
  1. Injection wiring — ``IntentComponent.post_initialize_handler_dependencies`` sets the handler's
     ``_tts_component`` port, and the handler DEGRADES GRACEFULLY when the component/port is None
     (the QUAL-24 bug class).
  2. The TTS speak action through a stub port — every voice-mapping branch and the error path.
"""

import asyncio
from types import SimpleNamespace

import pytest

from irene.intents.models import Intent, IntentResult
from irene.intents.context_models import UnifiedConversationContext
from irene.intents.handlers.voice_synthesis_handler import VoiceSynthesisIntentHandler
from irene.components.intent_component import IntentComponent


# --------------------------------------------------------------------------- stubs


class FakeTTS:
    """Minimal TTS capability-port stub.

    Records ``speak`` calls so a test can assert the chosen provider/params, and exposes
    the handful of methods the synchronous handlers reach for.
    """

    def __init__(self, providers=("silero_v3", "console"), speak_error=None):
        self.providers = list(providers)
        self.speak_error = speak_error
        self.speak_calls = []
        self.stop_called = 0
        self.cancel_called = 0
        self.default_provider = None

    async def speak(self, text, provider=None, **params):
        if self.speak_error is not None:
            raise self.speak_error
        self.speak_calls.append({"text": text, "provider": provider, "params": params})

    def get_providers_info(self):
        return "providers: silero_v3, console"

    def set_default_provider(self, name):
        self.default_provider = name
        return name in self.providers

    async def stop_synthesis(self):
        self.stop_called += 1

    async def cancel_synthesis(self):
        self.cancel_called += 1


class FakeAssetLoader:
    """Returns deterministic templates/localization for the voice_synthesis domain."""

    def __init__(self):
        self._templates = {
            "synthesis_with_voice": "Говорю '{text}' голосом {voice}",
            "synthesis_without_voice": "Говорю '{text}'",
            "synthesis_basic": "Произношу '{text}'",
            "synthesis_error": "Ошибка синтеза: {error}",
            "stop_synthesis": "Синтез остановлен",
            "cancel_synthesis": "Синтез отменён",
            "provider_switch_success": "Провайдер переключён на {provider}",
            "provider_switch_failed": "Не удалось переключить на {provider}",
        }
        self._localization = {
            "ru": {
                "provider_mappings": {
                    "provider_names": {"консоль": "console", "силеро": "silero_v3"},
                    "voice_names": {
                        "ксении": {"provider": "silero_v3", "params": {"speaker": "xenia"}},
                        "консоли": {"provider": "console", "params": {}},
                        "марсианина": {"provider": "mars_tts", "params": {}},
                    },
                }
            },
            "en": {
                "provider_mappings": {
                    "provider_names": {"console": "console"},
                    "voice_names": {},
                }
            },
        }

    def get_template(self, domain, template_name, language):
        return self._templates.get(template_name)

    def get_localization(self, domain, language):
        return self._localization.get(language)


def _make_handler(tts=None, asset_loader="default"):
    handler = VoiceSynthesisIntentHandler()
    handler._tts_component = tts
    if asset_loader == "default":
        handler.asset_loader = FakeAssetLoader()
        handler._asset_loader_initialized = True
    else:
        handler.asset_loader = asset_loader
    return handler


def _ctx(language="ru"):
    return UnifiedConversationContext(session_id="test_session", language=language)


# --------------------------------------------------------------- injection wiring (QUAL-24)


def _make_intent_component(handlers):
    comp = object.__new__(IntentComponent)
    comp.handler_manager = SimpleNamespace(get_handlers=lambda: handlers)
    comp._llm_component = None
    return comp


def test_post_initialize_injects_tts_port():
    """The application injects the real TTS component into the handler's ``_tts_component`` port."""
    handler = _make_handler(tts=None)
    fake_tts = FakeTTS()
    comp = _make_intent_component({"voice_synthesis_handler": handler})
    component_manager = SimpleNamespace(get_components=lambda: {"tts": fake_tts, "llm": None})

    asyncio.run(comp.post_initialize_handler_dependencies(component_manager))

    assert handler._tts_component is fake_tts


def test_post_initialize_tts_absent_sets_none_and_does_not_raise():
    """QUAL-24 graceful degradation: a missing TTS component injects None, no exception."""
    handler = _make_handler(tts=FakeTTS())  # start non-None to prove it gets overwritten
    comp = _make_intent_component({"voice_synthesis_handler": handler})
    component_manager = SimpleNamespace(get_components=lambda: {})  # no 'tts'

    # Must complete without raising even though the port is unavailable.
    asyncio.run(comp.post_initialize_handler_dependencies(component_manager))

    assert handler._tts_component is None


# --------------------------------------------------------------- port accessor + degradation


def test_get_tts_component_returns_injected_port():
    fake_tts = FakeTTS()
    handler = _make_handler(tts=fake_tts)
    assert asyncio.run(handler._get_tts_component()) is fake_tts


def test_get_tts_component_none_when_not_injected():
    handler = _make_handler(tts=None)
    assert asyncio.run(handler._get_tts_component()) is None


def test_handle_list_voices_without_port_returns_error_result():
    handler = _make_handler(tts=None)
    result = asyncio.run(handler._handle_list_voices(Intent(name="voice_synthesis.list", entities={}, confidence=1.0, raw_text="x"), _ctx()))
    assert isinstance(result, IntentResult)
    assert result.success is False
    assert "TTS component not available" in result.metadata["error"]


def test_handle_speak_with_voice_without_port_returns_error_result():
    handler = _make_handler(tts=None)
    intent = Intent(name="voice_synthesis.speak", entities={}, confidence=1.0, raw_text="скажи привет")
    result = asyncio.run(handler._handle_speak_with_voice(intent, _ctx()))
    assert result.success is False
    assert result.metadata["error"] == "TTS component not available"


def test_handle_switch_provider_without_port_returns_error_result():
    handler = _make_handler(tts=None)
    intent = Intent(name="voice_synthesis.switch", entities={}, confidence=1.0, raw_text="переключи на консоль")
    result = asyncio.run(handler._handle_switch_tts_provider(intent, _ctx()))
    assert result.success is False


def test_stop_action_without_port_returns_false():
    handler = _make_handler(tts=None)
    assert asyncio.run(handler._stop_synthesis_action("ru")) is False


def test_cancel_action_without_port_returns_false():
    handler = _make_handler(tts=None)
    assert asyncio.run(handler._cancel_synthesis_action("ru")) is False


# --------------------------------------------------------------- TTS speak action (the port call)


def test_synthesize_default_voice_calls_speak_with_text_only():
    tts = FakeTTS()
    handler = _make_handler(tts=tts)
    ok = asyncio.run(handler._synthesize_speech_action("привет", None, "ru", tts))
    assert ok is True
    assert tts.speak_calls == [{"text": "привет", "provider": None, "params": {}}]


def test_synthesize_named_voice_available_uses_mapped_provider_and_params():
    tts = FakeTTS(providers=("silero_v3",))
    handler = _make_handler(tts=tts)
    ok = asyncio.run(handler._synthesize_speech_action("привет", "ксении", "ru", tts))
    assert ok is True
    assert tts.speak_calls == [{"text": "привет", "provider": "silero_v3", "params": {"speaker": "xenia"}}]


def test_synthesize_named_voice_provider_unavailable_falls_back_to_default():
    # "марсианина" maps to provider "mars_tts", which is NOT in the port's providers.
    tts = FakeTTS(providers=("silero_v3", "console"))
    handler = _make_handler(tts=tts)
    ok = asyncio.run(handler._synthesize_speech_action("привет", "марсианина", "ru", tts))
    assert ok is True
    assert tts.speak_calls == [{"text": "привет", "provider": None, "params": {}}]


def test_synthesize_unrecognized_voice_falls_back_to_default():
    tts = FakeTTS()
    handler = _make_handler(tts=tts)
    ok = asyncio.run(handler._synthesize_speech_action("привет", "неизвестный", "ru", tts))
    assert ok is True
    assert tts.speak_calls == [{"text": "привет", "provider": None, "params": {}}]


def test_synthesize_speak_failure_raises():
    """BUG-19: a failing synthesis must PROPAGATE so the F&F store records a failure —
    the old `return False` was recorded as success."""
    tts = FakeTTS(speak_error=RuntimeError("audio device busy"))
    handler = _make_handler(tts=tts)
    with pytest.raises(RuntimeError, match="audio device busy"):
        asyncio.run(handler._synthesize_speech_action("привет", None, "ru", tts))


# --------------------------------------------------------------- stop / cancel actions (port set)


def test_stop_action_with_port_calls_stop_synthesis():
    tts = FakeTTS()
    handler = _make_handler(tts=tts)
    ok = asyncio.run(handler._stop_synthesis_action("ru"))
    assert ok is True
    assert tts.stop_called == 1


def test_cancel_action_with_port_calls_cancel_synthesis():
    tts = FakeTTS()
    handler = _make_handler(tts=tts)
    ok = asyncio.run(handler._cancel_synthesis_action("ru"))
    assert ok is True
    assert tts.cancel_called == 1


def test_stop_action_swallows_port_exception_and_returns_false():
    tts = FakeTTS()

    async def boom():
        raise RuntimeError("stop failed")

    tts.stop_synthesis = boom
    handler = _make_handler(tts=tts)
    assert asyncio.run(handler._stop_synthesis_action("ru")) is False


def test_cancel_action_swallows_port_exception_and_returns_false():
    tts = FakeTTS()

    async def boom():
        raise RuntimeError("cancel failed")

    tts.cancel_synthesis = boom
    handler = _make_handler(tts=tts)
    assert asyncio.run(handler._cancel_synthesis_action("ru")) is False


# --------------------------------------------------------------- synchronous handlers


def test_handle_list_voices_returns_provider_info():
    tts = FakeTTS()
    handler = _make_handler(tts=tts)
    result = asyncio.run(handler._handle_list_voices(Intent(name="voice_synthesis.list", entities={}, confidence=1.0, raw_text="x"), _ctx()))
    assert result.success is True
    assert result.text == "providers: silero_v3, console"
    assert result.metadata["action"] == "list_voices"


def test_handle_switch_provider_success():
    tts = FakeTTS(providers=("console", "silero_v3"))
    handler = _make_handler(tts=tts)
    intent = Intent(name="voice_synthesis.switch", entities={}, confidence=1.0, raw_text="переключи на консоль")
    result = asyncio.run(handler._handle_switch_tts_provider(intent, _ctx()))
    assert result.success is True
    assert tts.default_provider == "console"
    assert "console" in result.text


def test_handle_switch_provider_unknown_name_fails():
    tts = FakeTTS()
    handler = _make_handler(tts=tts)
    intent = Intent(name="voice_synthesis.switch", entities={}, confidence=1.0, raw_text="переключи на нечто")
    result = asyncio.run(handler._handle_switch_tts_provider(intent, _ctx()))
    assert result.success is False


# --------------------------------------------------------------- text/voice extraction


def test_extract_speech_parameters_voice_syntax():
    handler = _make_handler()
    text, voice = handler._extract_speech_parameters("скажи привет мир голосом ксении")
    assert text == "привет мир"
    assert voice == "ксении"


def test_extract_speech_parameters_voice_keyword_without_value():
    handler = _make_handler()
    text, voice = handler._extract_speech_parameters("скажи привет голосом")
    assert text == "привет"
    assert voice is None


def test_extract_speech_parameters_command_word_only():
    handler = _make_handler()
    text, voice = handler._extract_speech_parameters("скажи привет")
    assert text == "привет"
    assert voice is None


def test_extract_speech_parameters_plain_text_passthrough():
    handler = _make_handler()
    text, voice = handler._extract_speech_parameters("hello world")
    assert text == "hello world"
    assert voice is None


# --------------------------------------------------------------- provider-name parsing


def test_parse_tts_provider_name_from_localization():
    handler = _make_handler()
    assert handler._parse_tts_provider_name("переключи на консоль") == "console"


def test_parse_tts_provider_name_no_match_returns_empty():
    handler = _make_handler()
    assert handler._parse_tts_provider_name("переключи на нечто") == ""


def test_parse_tts_provider_name_fallback_when_no_asset_loader():
    # asset_loader None -> _get_provider_mappings raises RuntimeError -> hardcoded fallback table.
    handler = _make_handler(asset_loader=None)
    assert handler._parse_tts_provider_name("включи консоль") == "console"
