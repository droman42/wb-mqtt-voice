"""LLM NLU provider (QUAL-50) — classify-and-extract cascade fallback returning a plain Intent.

The provider behaves like keyword/spaCy: `recognize_with_parameters` → a plain `Intent` or `None`
(abstain). Confidence is derived (gate on intent∈donations + an evidence span that's actually in the
text); a missing required param still clears the threshold so the handler can clarify. The LLM is a
fake `LLMPort` here — no network."""

import asyncio
import json
from types import SimpleNamespace
from typing import Optional

from locveil_voice.providers.nlu.llm import LLMNLUProvider
from locveil_voice.core.donations import KeywordDonation, ParameterSpec, ParameterType


def _donations():
    return [
        KeywordDonation(
            intent="home.turn_on",
            phrases=["включи свет", "turn on the light"],
            parameters=[
                ParameterSpec(name="device", type=ParameterType.STRING, required=True),
                ParameterSpec(name="room", type=ParameterType.STRING, required=False, aliases=["location"]),
            ],
            handler_domain="home",
        ),
        KeywordDonation(
            intent="weather.get_current",
            phrases=["какая погода", "what's the weather"],
            parameters=[],  # a query: no required params
            handler_domain="weather",
        ),
    ]


class FakeLLM:
    """Minimal LLMPort double: returns a canned reply (or raises), records the messages it saw."""
    def __init__(self, reply: Optional[str] = None, available: bool = True, raises: bool = False):
        self.reply = reply
        self.available = available
        self.raises = raises
        self.last_messages = None

    async def is_available(self) -> bool:
        return self.available

    async def generate_response(self, messages, model=None, provider=None, **kwargs) -> str:
        self.last_messages = messages
        if self.raises:
            raise RuntimeError("boom")
        return self.reply or ""


def _provider(llm: Optional[FakeLLM]):
    p = LLMNLUProvider({})
    asyncio.run(p._initialize_from_donations(_donations()))
    if llm is not None:
        p.set_llm_component(llm)
    return p


def _recognize(provider, text, language="ru"):
    ctx = SimpleNamespace(language=language)
    return asyncio.run(provider.recognize_with_parameters(text, ctx))


# --- abstention paths ------------------------------------------------------------------------------

def test_abstains_with_no_llm_injected():
    assert _recognize(_provider(None), "включи свет на кухне") is None


def test_abstains_when_llm_unavailable():
    assert _recognize(_provider(FakeLLM(available=False)), "включи свет") is None


def test_abstains_on_llm_exception():
    assert _recognize(_provider(FakeLLM(raises=True)), "включи свет") is None


def test_abstains_on_unparseable_reply():
    assert _recognize(_provider(FakeLLM(reply="sorry, no idea")), "включи свет") is None


def test_abstains_on_unknown_intent():
    reply = json.dumps({"intent": "media.play", "params": {}, "evidence": "включи"})
    assert _recognize(_provider(FakeLLM(reply=reply)), "включи свет") is None


def test_abstains_when_evidence_not_in_text():
    # evidence must be a verbatim substring of the user's message (anti-hallucination)
    reply = json.dumps({"intent": "home.turn_on", "params": {"device": "свет"}, "evidence": "play music"})
    assert _recognize(_provider(FakeLLM(reply=reply)), "включи свет") is None


# --- recognition paths -----------------------------------------------------------------------------

def test_recognizes_command_with_full_params_high_confidence():
    reply = json.dumps({"intent": "home.turn_on",
                        "params": {"device": "свет", "room": "кухне"},
                        "evidence": "включи свет"})
    intent = _recognize(_provider(FakeLLM(reply=reply)), "включи свет на кухне")
    assert intent is not None
    assert intent.name == "home.turn_on"
    assert intent.entities == {"device": "свет", "room": "кухне"}
    assert intent.confidence == 0.95          # all (one) required params resolved
    assert intent.domain == "home" and intent.action == "turn_on"
    assert intent.raw_text == "включи свет на кухне"


def test_command_missing_required_param_still_passes_threshold_for_clarification():
    # device (required) absent → confidence floors at the threshold so the handler's _clarify runs,
    # NOT abstention. The required param is simply not in entities.
    reply = json.dumps({"intent": "home.turn_on", "params": {"room": "кухне"}, "evidence": "включи"})
    intent = _recognize(_provider(FakeLLM(reply=reply)), "включи на кухне")
    assert intent is not None
    assert intent.confidence == 0.7           # 0/1 required resolved → 0.7 (>= threshold)
    assert "device" not in intent.entities
    assert intent.entities.get("room") == "кухне"


def test_query_with_no_required_params_is_high_confidence():
    reply = json.dumps({"intent": "weather.get_current", "params": {}, "evidence": "погода"})
    intent = _recognize(_provider(FakeLLM(reply=reply)), "какая погода сегодня")
    assert intent is not None and intent.confidence == 0.95


def test_drops_hallucinated_param_keys_and_canonicalizes_aliases():
    reply = json.dumps({"intent": "home.turn_on",
                        "params": {"device": "свет", "location": "кухне", "color": "blue"},
                        "evidence": "включи свет"})
    intent = _recognize(_provider(FakeLLM(reply=reply)), "включи свет на кухне")
    assert intent is not None
    assert "color" not in intent.entities          # not declared for this intent → dropped
    assert intent.entities.get("room") == "кухне"  # 'location' alias canonicalized to 'room'


def test_handles_markdown_fenced_json():
    reply = "```json\n" + json.dumps({"intent": "weather.get_current", "params": {}, "evidence": "погода"}) + "\n```"
    intent = _recognize(_provider(FakeLLM(reply=reply)), "какая погода")
    assert intent is not None and intent.name == "weather.get_current"


# --- taxonomy / prompt -----------------------------------------------------------------------------

def test_supported_intents_from_donations():
    assert set(_provider(FakeLLM()).get_supported_intents()) == {"home.turn_on", "weather.get_current"}


def test_prompt_carries_taxonomy_not_catalog():
    llm = FakeLLM(reply=json.dumps({"intent": "weather.get_current", "params": {}, "evidence": "погода"}))
    _recognize(_provider(llm), "какая погода")
    system = llm.last_messages[0]["content"]
    assert "home.turn_on" in system and "weather.get_current" in system
    assert "device" in system  # parameter names are listed for extraction


# --- QUAL-51: tightened prompt — language filtering + few-shot --------------------------------------

def _donations_with_examples():
    return [
        KeywordDonation(
            intent="home.turn_on",
            phrases=["включи свет", "включи", "turn on the light", "turn on"],
            parameters=[ParameterSpec(name="device", type=ParameterType.STRING, required=True)],
            examples=[{"text": "включи свет на кухне", "parameters": {"device": "свет"}},
                      {"text": "turn on the kitchen light", "parameters": {"device": "light"}}],
            handler_domain="home",
        ),
    ]


def _prompt(language):
    p = LLMNLUProvider({})
    asyncio.run(p._initialize_from_donations(_donations_with_examples()))
    return p._build_system_prompt(language)


def test_taxonomy_phrases_filtered_to_utterance_language():
    ru = _prompt("ru")
    en = _prompt("en")
    # the taxonomy line shows the language's own phrases, not the other language's
    assert "включи свет" in ru and "turn on the light" not in ru
    assert "turn on the light" in en and "включи свет" not in en


def test_few_shot_includes_abstain_examples_in_language():
    ru = _prompt("ru")
    assert "есть ли жизнь на Марсе" in ru          # ru abstain exemplar
    assert '"intent": "none"' in ru                 # taught to abstain
    assert "meaning of life" not in ru              # not the en exemplar


def test_few_shot_positive_sourced_from_donation_examples():
    ru = _prompt("ru")
    # a real donation example (ru) appears as a positive few-shot mapped to its intent
    assert "включи свет на кухне" in ru
    assert '"intent": "home.turn_on"' in ru


def test_examples_stored_from_donations():
    p = LLMNLUProvider({})
    asyncio.run(p._initialize_from_donations(_donations_with_examples()))
    examples = p._intents["home.turn_on"]["examples"]
    assert ("включи свет на кухне", {"device": "свет"}) in examples


def test_lang_of_detects_script():
    assert LLMNLUProvider._lang_of("включи свет") == "ru"
    assert LLMNLUProvider._lang_of("turn on the light") == "en"
