"""Characterization tests for ``TextEnhancementIntentHandler`` (TEST-7 Phase D / TEST-8).

Exercises the handler as a domain port: enhance / improve / correct text via an
injected ``LLMPort`` stub, the graceful-degradation path when no LLM is injected,
the "no text to operate on" branch, the LLM-failure branch, donation-driven
``can_handle`` / ``execute`` routing, and the fatal-config template guards.

Method follows the project's new-code recipe (see ``test_cascading_nlu.py``):
- The handler's own ``__init__`` is light (it only sets attributes), so it is
  constructed directly; the heavy collaborators (LLM component, asset loader)
  are stubbed.
- All async entry points run through ``asyncio.run`` — no shared event loop,
  no global singleton/registry/env mutation, so the file is order-independent.
"""

from locveil_voice.core.metadata import SUPPORTED_PLATFORMS
from types import SimpleNamespace

import asyncio
import pytest

from locveil_voice.intents.models import Intent, IntentResult
from locveil_voice.intents.handlers.text_enhancement_handler import TextEnhancementIntentHandler


# --------------------------------------------------------------------------- #
# Stubs
# --------------------------------------------------------------------------- #
class FakeLLM:
    """Minimal stand-in for the injected ``LLMPort``.

    Only the three surfaces the handler actually touches are implemented:
    ``extract_text_from_command`` (sync), ``enhance_text`` (async) and a
    failure toggle so the error branch can be driven deterministically.
    """

    def __init__(self, *, extracted="extracted text", enhanced="ENHANCED", raises=False):
        self._extracted = extracted
        self._enhanced = enhanced
        self._raises = raises
        self.calls = []  # records (text, task, language, focus)

    def extract_text_from_command(self, command):
        return self._extracted

    async def enhance_text(self, text, *, task, language=None, focus=None, trace_context=None):
        self.calls.append(SimpleNamespace(text=text, task=task, language=language, focus=focus))
        if self._raises:
            raise RuntimeError("llm boom")
        return self._enhanced


class FakeAssetLoader:
    """Returns templates from an in-memory map (no filesystem/YAML)."""

    DEFAULT = {
        "enhanced_text": "Enhanced: {enhanced}",
        "improved_text": "Improved: {improved}",
        "corrected_text": "Corrected: {corrected}",
        "error_enhancement": "Error: {error}",
    }

    def __init__(self, templates=None):
        self._templates = self.DEFAULT if templates is None else templates

    def get_template(self, domain, template_name, language):
        return self._templates.get(template_name)


def make_handler(*, llm=None, asset_loader="default"):
    handler = TextEnhancementIntentHandler()
    handler._llm_component = llm
    if asset_loader == "default":
        handler.asset_loader = FakeAssetLoader()
        handler._asset_loader_initialized = True
    elif asset_loader is not None:
        handler.asset_loader = asset_loader
        handler._asset_loader_initialized = True
    return handler


def ctx(language="en"):
    return SimpleNamespace(language=language)


def make_intent(name="text_enhancement.improve", *, raw_text="please improve this", entities=None):
    return Intent(name=name, entities=entities or {}, confidence=1.0, raw_text=raw_text)


# --------------------------------------------------------------------------- #
# enhance_text
# --------------------------------------------------------------------------- #
def test_enhance_text_happy_path():
    llm = FakeLLM(extracted="raw words", enhanced="POLISHED")
    handler = make_handler(llm=llm)
    result = asyncio.run(handler._handle_enhance_text(make_intent(), ctx("en")))

    assert isinstance(result, IntentResult)
    assert result.success is True
    assert result.should_speak is True
    assert result.text == "Enhanced: POLISHED"
    assert result.metadata["action"] == "enhance"
    assert result.metadata["original_text"] == "raw words"
    assert result.metadata["enhanced_text"] == "POLISHED"
    assert result.metadata["language"] == "en"
    # task is always "improve" for enhance
    assert llm.calls[0].task == "improve"


def test_enhance_text_no_llm_degrades_gracefully():
    handler = make_handler(llm=None)
    result = asyncio.run(handler._handle_enhance_text(make_intent(), ctx()))
    assert result.success is False
    assert result.text == "Error: LLM component not available"


def test_enhance_text_no_extractable_text():
    llm = FakeLLM(extracted="")  # nothing to enhance
    handler = make_handler(llm=llm)
    result = asyncio.run(handler._handle_enhance_text(make_intent(), ctx()))
    assert result.success is False
    assert "Could not extract text" in result.text
    assert llm.calls == []  # LLM never invoked


def test_enhance_text_llm_failure_is_caught():
    llm = FakeLLM(extracted="some text", raises=True)
    handler = make_handler(llm=llm)
    result = asyncio.run(handler._handle_enhance_text(make_intent(), ctx()))
    assert result.success is False
    assert "Text enhancement failed" in result.text


# --------------------------------------------------------------------------- #
# improve_text
# --------------------------------------------------------------------------- #
def test_improve_text_from_entities():
    llm = FakeLLM(enhanced="BETTER")
    handler = make_handler(llm=llm)
    intent = make_intent(entities={"text": "entity text"})
    result = asyncio.run(handler._handle_improve_text(intent, ctx("en")))

    assert result.success is True
    assert result.text == "Improved: BETTER"
    assert result.metadata["action"] == "improve"
    assert result.metadata["original_text"] == "entity text"
    # entity text was used directly, no command extraction
    assert llm.calls[0].text == "entity text"
    assert llm.calls[0].task == "improve"
    # no improvement_type entity declared → focus None
    assert llm.calls[0].focus is None


def test_improve_text_falls_back_to_command_extraction():
    llm = FakeLLM(extracted="from command", enhanced="BETTER")
    handler = make_handler(llm=llm)
    intent = make_intent(entities={})  # no "text" entity
    result = asyncio.run(handler._handle_improve_text(intent, ctx()))
    assert result.success is True
    assert result.metadata["original_text"] == "from command"


def test_improve_text_not_found():
    llm = FakeLLM(extracted="")  # neither entity nor command yields text
    handler = make_handler(llm=llm)
    result = asyncio.run(handler._handle_improve_text(make_intent(entities={}), ctx()))
    assert result.success is False
    assert "Text to improve not found" in result.text


def test_improve_text_no_llm():
    handler = make_handler(llm=None)
    result = asyncio.run(handler._handle_improve_text(make_intent(), ctx()))
    assert result.success is False
    assert result.text == "Error: LLM component not available"


def test_improve_text_llm_failure_is_caught():
    llm = FakeLLM(enhanced="x", raises=True)
    handler = make_handler(llm=llm)
    intent = make_intent(entities={"text": "stuff"})
    result = asyncio.run(handler._handle_improve_text(intent, ctx()))
    assert result.success is False
    assert "Text improvement failed" in result.text


# --------------------------------------------------------------------------- #
# correct_text
# --------------------------------------------------------------------------- #
def test_correct_text_from_entities():
    llm = FakeLLM(enhanced="FIXED")
    handler = make_handler(llm=llm)
    intent = make_intent(name="text_enhancement.correct", entities={"text": "teh cat"})
    result = asyncio.run(handler._handle_correct_text(intent, ctx("en")))

    assert result.success is True
    assert result.text == "Corrected: FIXED"
    assert result.metadata["action"] == "correct"
    assert result.metadata["original_text"] == "teh cat"
    assert llm.calls[0].task == "grammar_correction"


def test_correct_text_falls_back_to_command_extraction():
    llm = FakeLLM(extracted="teh dog", enhanced="FIXED")
    handler = make_handler(llm=llm)
    intent = make_intent(name="text_enhancement.correct", entities={})
    result = asyncio.run(handler._handle_correct_text(intent, ctx()))
    assert result.success is True
    assert result.metadata["original_text"] == "teh dog"


def test_correct_text_not_found():
    llm = FakeLLM(extracted="")
    handler = make_handler(llm=llm)
    result = asyncio.run(handler._handle_correct_text(make_intent(entities={}), ctx()))
    assert result.success is False
    assert "Text to correct not found" in result.text


def test_correct_text_no_llm():
    handler = make_handler(llm=None)
    result = asyncio.run(handler._handle_correct_text(make_intent(), ctx()))
    assert result.success is False
    assert result.text == "Error: LLM component not available"


def test_correct_text_llm_failure_is_caught():
    llm = FakeLLM(enhanced="x", raises=True)
    handler = make_handler(llm=llm)
    intent = make_intent(name="text_enhancement.correct", entities={"text": "stuff"})
    result = asyncio.run(handler._handle_correct_text(intent, ctx()))
    assert result.success is False
    assert "Text correction failed" in result.text


# --------------------------------------------------------------------------- #
# _get_llm_component
# --------------------------------------------------------------------------- #
def test_get_llm_component_returns_injected_port():
    llm = FakeLLM()
    handler = make_handler(llm=llm)
    assert asyncio.run(handler._get_llm_component()) is llm


def test_get_llm_component_returns_none_when_not_injected():
    handler = make_handler(llm=None)
    assert asyncio.run(handler._get_llm_component()) is None


# --------------------------------------------------------------------------- #
# _get_template fatal-config guards
# --------------------------------------------------------------------------- #
def test_get_template_no_asset_loader_raises():
    handler = make_handler(llm=None, asset_loader=None)
    with pytest.raises(RuntimeError, match="Asset loader not initialized"):
        handler._get_template("enhanced_text", "en", enhanced="x")


def test_get_template_missing_template_raises():
    handler = make_handler(llm=None, asset_loader=FakeAssetLoader(templates={}))
    with pytest.raises(RuntimeError, match="not found"):
        handler._get_template("enhanced_text", "en", enhanced="x")


def test_get_template_bad_placeholder_raises():
    # Template references a key the handler does not supply → KeyError → fatal RuntimeError.
    bad = {"enhanced_text": "Enhanced: {unknown_key}"}
    handler = make_handler(llm=None, asset_loader=FakeAssetLoader(templates=bad))
    with pytest.raises(RuntimeError, match="missing required format argument"):
        handler._get_template("enhanced_text", "en", enhanced="x")


# --------------------------------------------------------------------------- #
# can_handle (donation-pattern matching)
# --------------------------------------------------------------------------- #
def _donation(**kw):
    base = dict(domain_patterns=[], intent_name_patterns=[], action_patterns=[], method_donations=[])
    base.update(kw)
    return SimpleNamespace(**base)


def test_can_handle_without_donation_raises():
    handler = make_handler(llm=None)  # no donation set
    with pytest.raises(RuntimeError, match="Missing JSON donation"):
        asyncio.run(handler.can_handle(make_intent()))


def test_can_handle_matches_domain_pattern():
    handler = make_handler(llm=None)
    handler.donation = _donation(domain_patterns=["text_enhancement"])
    handler._donation_initialized = True
    intent = Intent(name="text_enhancement.improve", entities={}, confidence=1.0, raw_text="x")
    assert asyncio.run(handler.can_handle(intent)) is True


def test_can_handle_matches_intent_name_pattern():
    handler = make_handler(llm=None)
    handler.donation = _donation(intent_name_patterns=["text_enhancement.improve"])
    handler._donation_initialized = True
    intent = Intent(name="text_enhancement.improve", entities={}, confidence=1.0, raw_text="x")
    assert asyncio.run(handler.can_handle(intent)) is True


def test_can_handle_matches_action_pattern():
    handler = make_handler(llm=None)
    handler.donation = _donation(action_patterns=["improve"])
    handler._donation_initialized = True
    intent = Intent(name="text_enhancement.improve", entities={}, confidence=1.0, raw_text="x")
    assert asyncio.run(handler.can_handle(intent)) is True


def test_can_handle_no_match_returns_false():
    handler = make_handler(llm=None)
    handler.donation = _donation()  # all pattern lists empty
    handler._donation_initialized = True
    intent = Intent(name="other.thing", entities={}, confidence=1.0, raw_text="x")
    assert asyncio.run(handler.can_handle(intent)) is False


# --------------------------------------------------------------------------- #
# execute() donation routing
# --------------------------------------------------------------------------- #
def test_execute_routes_to_improve_method():
    llm = FakeLLM(enhanced="ROUTED")
    handler = make_handler(llm=llm)
    method = SimpleNamespace(intent_suffix="improve", method_name="_handle_improve_text",
                             parameters=[])
    handler.donation = SimpleNamespace(method_donations=[method],
                                       handler_domain="text_enhancement",
                                       global_parameters=[])
    handler._donation_initialized = True
    intent = make_intent(name="text_enhancement.improve", entities={"text": "go"})
    result = asyncio.run(handler.execute(intent, ctx()))
    assert result.success is True
    assert result.text == "Improved: ROUTED"


# --------------------------------------------------------------------------- #
# Static build-dependency metadata
# --------------------------------------------------------------------------- #
def test_build_dependency_metadata():
    cls = TextEnhancementIntentHandler
    assert cls.get_python_dependencies() == []
    platform_deps = cls.get_platform_dependencies()
    assert set(platform_deps) == {"linux.ubuntu", "linux.alpine", "macos", "windows"}
    assert all(v == [] for v in platform_deps.values())
    assert cls.get_platform_support() == SUPPORTED_PLATFORMS
