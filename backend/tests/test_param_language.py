"""BUG-4 — get_param resolves a parameter's default by the REQUEST language, not the ru primary."""
import logging

from locveil_voice.core.donations import ParameterSpec, ParameterType
from locveil_voice.intents.handlers.base import IntentHandler
from locveil_voice.intents.models import Intent


class _Handler(IntentHandler):
    async def execute(self, intent, context):  # the only abstract method
        return None


def _handler():
    h = _Handler.__new__(_Handler)  # bypass __init__; get_param needs only logger + _find_param_spec
    h.logger = logging.getLogger("test")
    return h


def _intent(language):
    return Intent(name="timer.set", entities={}, confidence=1.0, raw_text="x", language=language)


def test_default_resolves_by_request_language(monkeypatch):
    # Only ru declares a default ({"ru": ...}); en declares none — like the timer `message` param.
    spec = ParameterSpec(name="message", type=ParameterType.STRING, required=False,
                         default_value="Таймер завершён!",
                         default_value_by_language={"ru": "Таймер завершён!"})
    h = _handler()
    monkeypatch.setattr(h, "_find_param_spec", lambda intent, name: spec)

    # ru request → the ru default
    assert h.get_param(_intent("ru"), "message", "FALLBACK") == "Таймер завершён!"
    # en request → the param declares no en default → fall through to the caller default
    # (typically a language-aware template), NOT the leaked Russian primary.
    assert h.get_param(_intent("en"), "message", "FALLBACK") == "FALLBACK"


def test_per_language_defaults_both_declared(monkeypatch):
    spec = ParameterSpec(name="greeting", type=ParameterType.STRING, required=False,
                         default_value="привет",
                         default_value_by_language={"ru": "привет", "en": "hi"})
    h = _handler()
    monkeypatch.setattr(h, "_find_param_spec", lambda intent, name: spec)
    assert h.get_param(_intent("ru"), "greeting", "F") == "привет"
    assert h.get_param(_intent("en"), "greeting", "F") == "hi"


def test_neutral_default_used_when_no_per_language(monkeypatch):
    # No per-language defaults (e.g. a neutral default from contract.json) → used for every language.
    spec = ParameterSpec(name="count", type=ParameterType.INTEGER, required=False,
                         default_value=3, default_value_by_language={})
    h = _handler()
    monkeypatch.setattr(h, "_find_param_spec", lambda intent, name: spec)
    assert h.get_param(_intent("ru"), "count", "F") == 3
    assert h.get_param(_intent("en"), "count", "F") == 3
