"""Characterization tests for ``TranslationIntentHandler`` (TEST-7 / TEST-8).

The handler is the domain (Invariant #3): it owns the ``LLMPort`` abstraction and
is injected with a concrete component at startup. These tests exercise its PUBLIC
translation behavior against a *stub* LLM port and a *stub* asset loader, plus the
off / degraded / error paths:

  * translate-text and translate-specific happy paths (LLM returns a string);
  * graceful degradation when the injected port is ``None`` ("LLM component not
    available") — TEST-8's core scenario;
  * extraction misses and ``enhance_text`` raising → language-aware error results;
  * the ``_get_template`` fail-loud contract (no asset loader / missing template /
    missing format arg);
  * ``can_handle`` donation gating and the build-dependency class methods.

The handler is built with ``object.__new__`` so none of the heavy startup wiring
(donations, asset loader init, metrics/notification services) runs; only the few
attributes the methods under test actually read are seeded. Every coroutine is
driven with ``asyncio.run`` so no event loop is left open and the tests are
order-independent (no global singletons/registries/env are mutated).
"""

from irene.core.metadata import SUPPORTED_PLATFORMS
import asyncio
import logging
from types import SimpleNamespace

import pytest

from irene.intents.models import Intent
from irene.intents.context_models import UnifiedConversationContext
from irene.intents.handlers.translation_handler import TranslationIntentHandler


# --------------------------------------------------------------------------- #
# Stubs
# --------------------------------------------------------------------------- #
class StubLLMPort:
    """Minimal stand-in for the injected LLM capability.

    Only the two methods the translation handler calls are implemented:
    ``extract_translation_request`` (sync) and ``enhance_text`` (async).
    """

    def __init__(self, *, extraction=("hola", "en"), translation="hello", raises=None):
        self._extraction = extraction
        self._translation = translation
        self._raises = raises
        self.enhance_calls = []

    def extract_translation_request(self, command):
        return self._extraction

    async def enhance_text(self, text, *, task, target_language=None, language=None, trace_context=None):
        self.enhance_calls.append(
            {"text": text, "task": task, "target_language": target_language, "language": language}
        )
        if self._raises is not None:
            raise self._raises
        return self._translation


# Templates the stub asset loader can render. Keys mirror the real
# assets/templates/translation/<lang>/result_messages.yaml placeholders.
_TEMPLATES = {
    "translation_result": "Translation: {translated}",
    "error_translation": "Error: {error}",
    "default_target_language": "en",
}


class StubAssetLoader:
    """Returns canned template strings; ``None`` for unknown templates."""

    def __init__(self, templates=None):
        self._templates = _TEMPLATES if templates is None else templates

    def get_template(self, category, template_name, language):
        assert category == "translation"
        return self._templates.get(template_name)


def _make_handler(*, llm=None, asset_loader="default"):
    """Build a handler bypassing heavy construction; seed only what's read."""
    h = object.__new__(TranslationIntentHandler)
    h.name = "TranslationIntentHandler"
    h.logger = logging.getLogger("test.translation")
    h._llm_component = llm
    h._trace_context = None
    h.asset_loader = StubAssetLoader() if asset_loader == "default" else asset_loader
    return h


def _ctx(language="en"):
    return UnifiedConversationContext(session_id="s1", language=language)


def _intent(raw_text="translate hola to english", entities=None):
    return Intent(
        name="translation.translate_text",
        entities=entities or {},
        confidence=0.9,
        raw_text=raw_text,
    )


# --------------------------------------------------------------------------- #
# TEST-8: translate via a stub LLM port
# --------------------------------------------------------------------------- #
def test_translate_text_happy_path_calls_llm_and_renders_template():
    llm = StubLLMPort(extraction=("hola", "en"), translation="hello")
    h = _make_handler(llm=llm)

    result = asyncio.run(h._handle_translate_text(_intent(), _ctx("ru")))

    assert result.success is True
    assert result.should_speak is True
    assert result.text == "Translation: hello"
    assert result.metadata["action"] == "translate"
    assert result.metadata["original_text"] == "hola"
    assert result.metadata["target_language"] == "en"
    assert result.metadata["translated_text"] == "hello"
    assert result.metadata["language"] == "ru"  # response language comes from context
    # enhance_text invoked once with the extracted text + target language
    assert llm.enhance_calls == [
        {"text": "hola", "task": "translation", "target_language": "en", "language": "ru"}
    ]


def test_translate_specific_uses_entities_over_extraction():
    llm = StubLLMPort(translation="bonjour")
    h = _make_handler(llm=llm)
    intent = _intent(entities={"text": "hello", "target_language": "fr"})

    result = asyncio.run(h._handle_translate_specific(intent, _ctx("en")))

    assert result.success is True
    assert result.text == "Translation: bonjour"
    assert result.metadata["action"] == "translate_specific"
    assert result.metadata["original_text"] == "hello"
    assert result.metadata["target_language"] == "fr"
    assert llm.enhance_calls[0]["text"] == "hello"
    assert llm.enhance_calls[0]["target_language"] == "fr"


def test_translate_specific_falls_back_to_extraction_when_no_entity_text():
    llm = StubLLMPort(extraction=("from cmd", "de"), translation="aus")
    h = _make_handler(llm=llm)
    intent = _intent(entities={})  # no "text" entity → extraction path

    result = asyncio.run(h._handle_translate_specific(intent, _ctx("en")))

    assert result.success is True
    assert result.metadata["original_text"] == "from cmd"
    assert result.metadata["target_language"] == "de"


def test_translate_specific_defaults_target_language_from_template():
    # entities supply text but NOT target_language → default_target_language template used
    llm = StubLLMPort(translation="x")
    h = _make_handler(llm=llm)
    intent = _intent(entities={"text": "hi"})

    result = asyncio.run(h._handle_translate_specific(intent, _ctx("en")))

    assert result.success is True
    assert result.metadata["target_language"] == "en"  # from default_target_language template


def test_get_llm_component_returns_injected_port():
    llm = StubLLMPort()
    h = _make_handler(llm=llm)
    assert asyncio.run(h._get_llm_component()) is llm


# --------------------------------------------------------------------------- #
# Graceful degradation: port is None
# --------------------------------------------------------------------------- #
def test_translate_text_degrades_when_llm_port_is_none():
    h = _make_handler(llm=None)

    result = asyncio.run(h._handle_translate_text(_intent(), _ctx("en")))

    assert result.success is False
    assert result.text == "Error: LLM component not available"
    assert result.metadata["error"] == "LLM component not available"


def test_translate_specific_degrades_when_llm_port_is_none():
    h = _make_handler(llm=None)
    intent = _intent(entities={"text": "hi", "target_language": "fr"})

    result = asyncio.run(h._handle_translate_specific(intent, _ctx("en")))

    assert result.success is False
    assert result.metadata["error"] == "LLM component not available"


# --------------------------------------------------------------------------- #
# Error / no-op paths
# --------------------------------------------------------------------------- #
def test_translate_text_when_extraction_returns_none():
    llm = StubLLMPort(extraction=None)
    h = _make_handler(llm=llm)

    result = asyncio.run(h._handle_translate_text(_intent(), _ctx("en")))

    assert result.success is False
    assert result.metadata["error"] == "Could not extract text to translate"
    assert llm.enhance_calls == []  # never reached the LLM


def test_translate_specific_when_text_missing_and_extraction_fails():
    llm = StubLLMPort(extraction=None)
    h = _make_handler(llm=llm)
    intent = _intent(entities={})

    result = asyncio.run(h._handle_translate_specific(intent, _ctx("en")))

    assert result.success is False
    assert result.metadata["error"] == "Text to translate not found"


def test_translate_text_wraps_llm_exception_as_error_result():
    llm = StubLLMPort(extraction=("hola", "en"), raises=RuntimeError("boom"))
    h = _make_handler(llm=llm)

    result = asyncio.run(h._handle_translate_text(_intent(), _ctx("en")))

    assert result.success is False
    assert "Translation failed: boom" in result.metadata["error"]


def test_translate_specific_wraps_llm_exception_as_error_result():
    llm = StubLLMPort(raises=RuntimeError("kapow"))
    h = _make_handler(llm=llm)
    intent = _intent(entities={"text": "hi", "target_language": "fr"})

    result = asyncio.run(h._handle_translate_specific(intent, _ctx("en")))

    assert result.success is False
    assert "Translation failed: kapow" in result.metadata["error"]


# --------------------------------------------------------------------------- #
# _get_template fail-loud contract + _error_result
# --------------------------------------------------------------------------- #
def test_get_template_raises_without_asset_loader():
    h = _make_handler(asset_loader=None)
    with pytest.raises(RuntimeError, match="Asset loader not initialized"):
        h._get_template("translation_result", "en", translated="x")


def test_get_template_raises_for_unknown_template():
    h = _make_handler(asset_loader=StubAssetLoader(templates={}))
    with pytest.raises(RuntimeError, match="not found"):
        h._get_template("translation_result", "en", translated="x")


def test_get_template_raises_on_missing_format_argument():
    h = _make_handler()  # default loader: translation_result needs {translated}
    with pytest.raises(RuntimeError, match="missing required format argument"):
        h._get_template("translation_result", "en")  # no translated= kwarg


def test_error_result_is_language_aware_failure():
    h = _make_handler()
    result = h._error_result(_ctx("en"), "some problem")
    assert result.success is False
    assert result.text == "Error: some problem"
    assert result.metadata["language"] == "en"
    assert result.metadata["error"] == "some problem"


# --------------------------------------------------------------------------- #
# can_handle donation gating
# --------------------------------------------------------------------------- #
def test_can_handle_raises_without_donation():
    h = _make_handler()
    h.has_donation = lambda: False
    with pytest.raises(RuntimeError, match="Missing JSON donation file"):
        asyncio.run(h.can_handle(_intent()))


def test_can_handle_returns_false_when_donation_is_none():
    h = _make_handler()
    h.has_donation = lambda: True
    h.get_donation = lambda: None
    assert asyncio.run(h.can_handle(_intent())) is False


def test_can_handle_matches_domain_then_name_then_action():
    h = _make_handler()
    h.has_donation = lambda: True

    # domain match
    h.get_donation = lambda: SimpleNamespace(domain_patterns=["translation"])
    intent = Intent(name="translation.translate_text", entities={}, confidence=1.0, raw_text="x")
    assert asyncio.run(h.can_handle(intent)) is True

    # intent-name match (domain misses)
    h.get_donation = lambda: SimpleNamespace(
        domain_patterns=["other"], intent_name_patterns=["translation.translate_text"]
    )
    assert asyncio.run(h.can_handle(intent)) is True

    # action match (domain + name miss)
    h.get_donation = lambda: SimpleNamespace(
        domain_patterns=["other"], intent_name_patterns=["nope"], action_patterns=["translate_text"]
    )
    assert asyncio.run(h.can_handle(intent)) is True

    # nothing matches
    h.get_donation = lambda: SimpleNamespace(
        domain_patterns=["other"], intent_name_patterns=["nope"], action_patterns=["nada"]
    )
    assert asyncio.run(h.can_handle(intent)) is False


# --------------------------------------------------------------------------- #
# Build-dependency class methods (pure, no state)
# --------------------------------------------------------------------------- #
def test_build_dependency_class_methods():
    assert TranslationIntentHandler.get_python_dependencies() == []

    platform_deps = TranslationIntentHandler.get_platform_dependencies()
    assert set(platform_deps) == {"linux.ubuntu", "linux.alpine", "macos", "windows"}
    assert all(v == [] for v in platform_deps.values())

    support = TranslationIntentHandler.get_platform_support()
    assert support == SUPPORTED_PLATFORMS
