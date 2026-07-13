"""Characterization tests for ``locveil_voice.components.nlu_component`` (TEST-7 Phase D).

These tests target the parts of :class:`NLUComponent` and its embedded
:class:`ContextAwareNLUProcessor` that the cascade-focused ``test_cascading_nlu``
suite does not exercise: language detection, context enhancement, the small
cache / threshold / fallback helpers, the heuristic domain/action/entity
analysers, the ``process`` tracing wrapper, and the static/property metadata
surface.

Every object is built with ``object.__new__`` (or a hand-stubbed processor) so
no donations, real providers, or config models are loaded. All async entry
points go through ``asyncio.run`` and no global singleton/env is mutated, so the
tests are hermetic and order-independent.
"""

import asyncio
from types import SimpleNamespace

import pytest

from locveil_voice.intents.models import Intent
from locveil_voice.intents.context_models import UnifiedConversationContext
from locveil_voice.core.trace_context import TraceContext
from locveil_voice.components.nlu_component import (
    NLUComponent,
    ContextAwareNLUProcessor,
)


# --------------------------------------------------------------------------- #
# Builders                                                                     #
# --------------------------------------------------------------------------- #
def make_core(*, default_language="ru", supported=("ru", "en"), nlu=None):
    """A minimal ``core`` with the canonical language policy (QUAL-36)."""
    config = SimpleNamespace(
        default_language=default_language,
        supported_languages=list(supported),
        nlu=nlu,
    )
    return SimpleNamespace(config=config)


def make_processor(*, core=None) -> ContextAwareNLUProcessor:
    """Build a ContextAwareNLUProcessor without touching asset loaders."""
    proc = object.__new__(ContextAwareNLUProcessor)
    import logging

    proc.logger = logging.getLogger("test.nlu.processor")
    proc.nlu_component = SimpleNamespace(core=core or make_core())
    proc.entity_resolver = None  # set per-test where process_with_context is used
    return proc


def make_component(*, providers=None, nlu_config=None) -> NLUComponent:
    comp = object.__new__(NLUComponent)
    comp.providers = providers or {}
    comp.confidence_threshold = 0.7
    comp.fallback_intent = "conversation.general"
    comp.provider_cascade_order = list((providers or {}).keys())
    comp.max_cascade_attempts = 4
    comp.cascade_timeout_ms = 200
    comp.cache_recognition_results = False
    comp.cache_ttl_seconds = 300
    comp._recognition_cache = {}
    comp.default_provider = None
    comp.context_manager = None
    comp.asset_loader = None
    comp.core = make_core(nlu=nlu_config)
    return comp


def ctx(**kwargs) -> UnifiedConversationContext:
    kwargs.setdefault("session_id", "s1")
    return UnifiedConversationContext(**kwargs)


# --------------------------------------------------------------------------- #
# _analyze_text_language                                                       #
# --------------------------------------------------------------------------- #
def test_analyze_text_language_empty_returns_none():
    proc = make_processor()
    assert proc._analyze_text_language("") is None
    assert proc._analyze_text_language("   ") is None


def test_analyze_text_language_cyrillic_is_ru():
    proc = make_processor()
    assert proc._analyze_text_language("привет как дела") == "ru"


def test_analyze_text_language_english_words_is_en():
    proc = make_processor()
    assert proc._analyze_text_language("what time is it now") == "en"


def test_analyze_text_language_latin_no_keyword_is_english():
    proc = make_processor()
    # Latin letters, no English indicator word, no Cyrillic — BUG-3: falls back to SCRIPT
    # (non-Cyrillic ⇒ English), not None→default('ru'), so English without a listed keyword works.
    assert proc._analyze_text_language("zxqv brrm") == "en"


# --------------------------------------------------------------------------- #
# _get_language_confidence                                                     #
# --------------------------------------------------------------------------- #
def test_language_confidence_zero_without_language():
    proc = make_processor()
    c = ctx(language="", conversation_history=[{"user_text": "привет"}])
    assert proc._get_language_confidence(c) == 0.0


def test_language_confidence_zero_without_history():
    proc = make_processor()
    c = ctx(language="ru", conversation_history=[])
    assert proc._get_language_confidence(c) == 0.0


def test_language_confidence_consistent_detections():
    proc = make_processor()
    c = ctx(
        language="ru",
        conversation_history=[
            {"user_text": "привет как дела"},
            {"user_text": "спасибо большое"},
        ],
    )
    # Both entries detect as ru → full confidence.
    assert proc._get_language_confidence(c) == 1.0


def test_language_confidence_partial():
    proc = make_processor()
    c = ctx(
        language="ru",
        conversation_history=[
            {"user_text": "привет как дела"},  # ru
            {"user_text": "what time is it"},  # en
        ],
    )
    assert proc._get_language_confidence(c) == 0.5


# --------------------------------------------------------------------------- #
# _should_redetect_language                                                    #
# --------------------------------------------------------------------------- #
def test_should_redetect_no_nlu_config_defaults_true():
    proc = make_processor(core=make_core(nlu=None))
    assert proc._should_redetect_language(ctx(language="ru")) is True


def test_should_redetect_auto_detect_disabled_returns_false():
    nlu = SimpleNamespace(auto_detect_language=False)
    proc = make_processor(core=make_core(nlu=nlu))
    assert proc._should_redetect_language(ctx(language="ru")) is False


def test_should_redetect_no_language_returns_true():
    nlu = SimpleNamespace(auto_detect_language=True)
    proc = make_processor(core=make_core(nlu=nlu))
    assert proc._should_redetect_language(ctx(language="")) is True


def test_should_redetect_short_history_returns_true():
    nlu = SimpleNamespace(auto_detect_language=True)
    proc = make_processor(core=make_core(nlu=nlu))
    c = ctx(language="ru", conversation_history=[{"user_text": "привет"}])
    assert proc._should_redetect_language(c) is True


def test_should_redetect_high_confidence_returns_false():
    nlu = SimpleNamespace(
        auto_detect_language=True,
        language_detection_confidence_threshold=0.5,
    )
    proc = make_processor(core=make_core(nlu=nlu))
    # 4 consistent ru entries → confidence 1.0 >= threshold, history len >= 3.
    c = ctx(
        language="ru",
        conversation_history=[
            {"user_text": "привет как дела"},
            {"user_text": "спасибо большое друг"},
            {"user_text": "что сейчас время"},
            {"user_text": "где сейчас"},
        ],
    )
    assert proc._should_redetect_language(c) is False


def test_should_redetect_low_confidence_returns_true():
    nlu = SimpleNamespace(
        auto_detect_language=True,
        language_detection_confidence_threshold=0.9,
    )
    proc = make_processor(core=make_core(nlu=nlu))
    # 3 entries, only some consistent → confidence below 0.9.
    c = ctx(
        language="ru",
        conversation_history=[
            {"user_text": "привет как дела"},
            {"user_text": "what time is it now"},
            {"user_text": "hello there friend"},
        ],
    )
    assert proc._should_redetect_language(c) is True


# --------------------------------------------------------------------------- #
# _detect_language                                                             #
# --------------------------------------------------------------------------- #
def test_detect_language_user_preference_wins():
    proc = make_processor(core=make_core(supported=("ru", "en")))
    c = ctx(user_preferences={"language": "en"})
    assert asyncio.run(proc._detect_language("привет", c)) == "en"


def test_detect_language_user_preference_unsupported_ignored():
    proc = make_processor(core=make_core(default_language="ru", supported=("ru", "en")))
    c = ctx(user_preferences={"language": "fr"})
    # Unsupported preference falls through to Cyrillic text detection → ru.
    assert asyncio.run(proc._detect_language("привет как дела", c)) == "ru"


def test_detect_language_text_based_english():
    proc = make_processor(core=make_core(default_language="ru", supported=("ru", "en")))
    c = ctx(language="")
    assert asyncio.run(proc._detect_language("what time is it now", c)) == "en"


def test_detect_language_latin_no_keyword_is_english():
    # BUG-3: no keyword signal but Latin script ⇒ English (not None→default), when en is supported.
    proc = make_processor(core=make_core(default_language="ru", supported=("ru", "en")))
    c = ctx(language="")
    assert asyncio.run(proc._detect_language("zxqv brrm", c)) == "en"


def test_detect_language_unsupported_detected_clamps_to_default():
    # English detected but not in the supported set → canonical default.
    proc = make_processor(core=make_core(default_language="ru", supported=("ru",)))
    c = ctx(language="")
    assert asyncio.run(proc._detect_language("what time is it now", c)) == "ru"


def test_detect_language_conversation_history_high_confidence():
    proc = make_processor(core=make_core(default_language="ru", supported=("ru", "en")))
    c = ctx(
        language="en",
        conversation_history=[
            {"user_text": "what time is it now"},
            {"user_text": "hello there how are you"},
            {"user_text": "yes thanks no time"},
        ],
    )
    # All-en history → confidence > 0.8 → keep the established language.
    assert asyncio.run(proc._detect_language("ambiguous zzz", c)) == "en"


# --------------------------------------------------------------------------- #
# process_with_context / _enhance_with_context                                 #
# --------------------------------------------------------------------------- #
class _StubResolver:
    async def resolve_entities(self, intent, context):
        # Echo back the original entities plus a resolved marker.
        out = dict(intent.entities)
        out["resolved_marker"] = True
        return out


def test_process_with_context_enhances_intent():
    proc = make_processor(core=make_core(default_language="ru", supported=("ru", "en")))
    proc.entity_resolver = _StubResolver()

    async def fake_recognize(text, context):
        return Intent(
            name="test.intent",
            entities={"foo": "bar"},
            confidence=0.9,
            raw_text=text,
        )

    proc.nlu_component.recognize = fake_recognize

    c = ctx(
        language="en",
        client_id="kitchen",
        room_name="Кухня",
        timezone="Europe/Moscow",
        conversation_history=[
            {"user_text": "hello", "intent": "greet.hi"},
        ],
    )

    result = asyncio.run(proc.process_with_context("turn on the light", c))

    assert isinstance(result, Intent)
    assert result.name == "test.intent"
    assert result.entities["resolved_marker"] is True
    assert result.entities["client_id"] == "kitchen"
    assert result.entities["room_id"] == "kitchen"
    assert result.entities["room_name"] == "Кухня"
    # language != ru → preference recorded
    assert result.entities["language_preference"] == "en"
    assert result.entities["timezone"] == "Europe/Moscow"
    assert result.entities["recent_intents"] == ["greet.hi"]


def test_process_with_context_detects_language_when_missing():
    proc = make_processor(core=make_core(default_language="ru", supported=("ru", "en")))
    proc.entity_resolver = _StubResolver()

    captured = {}

    async def fake_recognize(text, context):
        captured["language"] = context.language
        return Intent(name="x.y", entities={}, confidence=0.5, raw_text=text)

    proc.nlu_component.recognize = fake_recognize
    # No nlu config → _should_redetect returns True; empty language triggers detect.
    c = ctx(language="")

    asyncio.run(proc.process_with_context("привет как дела", c))
    assert captured["language"] == "ru"
    assert c.language == "ru"


# --------------------------------------------------------------------------- #
# small helpers                                                                #
# --------------------------------------------------------------------------- #
def test_get_provider_cascade_order():
    comp = make_component()
    comp.provider_cascade_order = ["a", "b"]
    assert comp._get_provider_cascade_order() == ["a", "b"]


def test_get_cache_key_stable_and_context_scoped():
    comp = make_component()
    c = ctx(client_id="kitchen", language="ru")
    k1 = comp._get_cache_key("Hello", c)
    k2 = comp._get_cache_key("hello", c)  # case/strip normalized
    assert k1 == k2
    assert "kitchen" in k1


def test_is_cache_valid():
    import time

    comp = make_component()
    comp.cache_ttl_seconds = 300
    assert comp._is_cache_valid({}) is False
    assert comp._is_cache_valid({"timestamp": time.time()}) is True
    assert comp._is_cache_valid({"timestamp": time.time() - 9999}) is False


def test_provider_confidence_threshold_provider_specific():
    nlu = SimpleNamespace(providers={"p1": {"confidence_threshold": 0.55}})
    comp = make_component(nlu_config=nlu)
    assert comp._get_provider_confidence_threshold("p1") == 0.55


def test_provider_confidence_threshold_falls_back_to_global():
    nlu = SimpleNamespace(providers={"p1": {"confidence_threshold": 0.55}})
    comp = make_component(nlu_config=nlu)
    comp.confidence_threshold = 0.7
    # Unknown provider → global.
    assert comp._get_provider_confidence_threshold("unknown") == 0.7


def test_provider_confidence_threshold_no_nlu_config():
    comp = make_component(nlu_config=None)
    comp.confidence_threshold = 0.42
    assert comp._get_provider_confidence_threshold("anything") == 0.42


# --------------------------------------------------------------------------- #
# fallback intent + heuristic analysers                                        #
# --------------------------------------------------------------------------- #
def test_create_fallback_intent_basic():
    comp = make_component()
    intent = comp._create_fallback_intent("some text")
    assert intent.name == "conversation.general"
    assert intent.confidence == 0.0
    assert intent.domain == "conversation"
    assert intent.action == "general"
    assert intent.entities["original_text"] == "some text"
    assert "_fallback_context" not in intent.entities


def test_create_fallback_intent_with_context():
    comp = make_component()
    intent = comp._create_fallback_intent("t", {"total_attempts": 3})
    assert intent.entities["_fallback_context"] == {"total_attempts": 3}


def test_analyze_likely_domain_keyword_match():
    comp = make_component()
    assert comp._analyze_likely_domain("play music", ctx()) == "audio"
    assert comp._analyze_likely_domain("поставь таймер", ctx()) == "timer"


def test_analyze_likely_domain_no_match_returns_none():
    comp = make_component()
    # No domain keyword and no active actions → None.
    assert comp._analyze_likely_domain("xyzzy nothing", ctx()) is None


def test_analyze_likely_action_keyword_match():
    comp = make_component()
    assert comp._analyze_likely_action("включи свет", ctx()) == "play"
    assert comp._analyze_likely_action("останови музыку", ctx()) == "stop"
    assert comp._analyze_likely_action("nothing here", ctx()) is None


def test_extract_potential_entities():
    comp = make_component()
    ents = comp._extract_potential_entities('set timer for 5 минут at 12:30 "kitchen"', ctx())
    assert "number:5" in ents
    assert "number:12" in ents
    assert 'quoted:kitchen' in ents
    assert any(e.startswith("time:") for e in ents)


# --------------------------------------------------------------------------- #
# configure / get_providers_info                                              #
# --------------------------------------------------------------------------- #
def test_configure_updates_settings():
    comp = make_component()
    comp.configure({"confidence_threshold": 0.9, "fallback_intent": "chitchat.x"})
    assert comp.confidence_threshold == 0.9
    assert comp.fallback_intent == "chitchat.x"


def test_configure_partial_noop_keys():
    comp = make_component()
    comp.configure({})  # nothing changes
    assert comp.confidence_threshold == 0.7


def test_get_providers_info_empty():
    comp = make_component()
    assert "Нет доступных" in comp.get_providers_info()


def test_get_providers_info_with_providers():
    prov = SimpleNamespace(
        get_capabilities=lambda: {"languages": ["ru", "en"], "domains": ["audio"]}
    )
    comp = make_component(providers={"p1": prov})
    comp.default_provider = "p1"
    info = comp.get_providers_info()
    assert "p1" in info
    assert "по умолчанию" in info
    assert "Порог уверенности" in info


# --------------------------------------------------------------------------- #
# recognize_with_context + process (trace and fast path)                       #
# --------------------------------------------------------------------------- #
def _component_with_stub_processor(intent: Intent) -> NLUComponent:
    comp = make_component()

    class _Proc:
        async def process_with_context(self, text, context):
            return intent

    comp.context_processor = _Proc()
    return comp


def test_recognize_with_context_delegates():
    intent = Intent(name="a.b", entities={}, confidence=0.8, raw_text="hi")
    comp = _component_with_stub_processor(intent)
    out = asyncio.run(comp.recognize_with_context("hi", ctx()))
    assert out is intent


def test_process_fast_path_sets_raw_text_from_original():
    intent = Intent(name="a.b", entities={}, confidence=0.8, raw_text="normalized")
    comp = _component_with_stub_processor(intent)
    out = asyncio.run(comp.process("normalized", ctx(), None, original_text="ORIGINAL"))
    assert out.raw_text == "ORIGINAL"


def test_process_fast_path_defaults_original_to_text():
    intent = Intent(name="a.b", entities={}, confidence=0.8, raw_text="x")
    comp = _component_with_stub_processor(intent)
    out = asyncio.run(comp.process("the text", ctx()))
    assert out.raw_text == "the text"


def test_process_trace_path_records_stage():
    intent = Intent(name="a.b", entities={"e": 1}, confidence=0.8, raw_text="x")
    comp = _component_with_stub_processor(intent)
    trace = TraceContext(enabled=True, request_id="req1")
    out = asyncio.run(comp.process("the text", ctx(), trace, original_text="orig"))
    assert out.raw_text == "orig"
    stage_names = [s["stage"] for s in trace.stages]
    assert "nlu_cascade" in stage_names


def test_process_trace_path_propagates_errors():
    comp = make_component()

    class _Proc:
        async def process_with_context(self, text, context):
            raise RuntimeError("boom")

    comp.context_processor = _Proc()
    trace = TraceContext(enabled=True, request_id="req2")
    with pytest.raises(RuntimeError):
        asyncio.run(comp.process("the text", ctx(), trace))


# --------------------------------------------------------------------------- #
# property / metadata surface                                                 #
# --------------------------------------------------------------------------- #
def test_property_surface():
    comp = make_component()
    assert comp.name == "nlu"
    assert comp.version == "1.0.0"
    assert "Natural Language" in comp.description
    assert "spacy" in comp.optional_dependencies
    assert comp.enabled_by_default is True
    assert comp.category == "nlu"
    assert comp.platforms == []
    assert comp.get_component_dependencies() == ["intent_system"]


def test_api_metadata():
    comp = make_component()
    assert comp.get_api_prefix() == "/nlu"
    assert comp.get_api_tags() == ["Natural Language Understanding"]
    assert isinstance(comp.is_api_available(), bool)


def test_service_dependencies_and_injection():
    comp = make_component()
    deps = comp.get_service_dependencies()
    assert "context_manager" in deps

    sentinel = object()
    comp.inject_dependency("context_manager", sentinel)
    assert comp.context_manager is sentinel


def test_classmethod_build_metadata():
    # BUILD-7: get_python_dependencies returns pyproject extra-NAMES, not raw pip specs.
    assert NLUComponent.get_python_dependencies() == ["web-api"]
    plat = NLUComponent.get_platform_dependencies()
    assert "linux.ubuntu" in plat
    assert "macos" in NLUComponent.get_platform_support()
    assert NLUComponent.get_config_path() == "nlu"
    # Config class is the pydantic NLUConfig model.
    cfg_cls = NLUComponent.get_config_class()
    assert cfg_cls.__name__ == "NLUConfig"


# --------------------------------------------------------------------------- #
# discovery / conversion error paths                                          #
# --------------------------------------------------------------------------- #
def test_discover_handler_files_missing_dir(tmp_path):
    comp = make_component()
    missing = tmp_path / "does_not_exist"
    assert comp._discover_handler_files(missing) == []


def test_discover_handler_files_skips_base_and_init(tmp_path):
    comp = make_component()
    (tmp_path / "base.py").write_text("# base")
    (tmp_path / "__init__.py").write_text("")
    (tmp_path / "timer.py").write_text("# handler")
    found = {p.name for p in comp._discover_handler_files(tmp_path)}
    assert found == {"timer.py"}
