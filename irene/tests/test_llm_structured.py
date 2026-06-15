"""Structured / JSON LLM output (QUAL-52 PR3) — the path the QUAL-50 classifier returns through."""

import asyncio

from irene.components.llm_component import _parse_json_response, LLMComponent


def test_parse_clean_json_object():
    assert _parse_json_response('{"a": 1, "b": "x"}') == {"a": 1, "b": "x"}


def test_parse_markdown_fenced_json():
    assert _parse_json_response('```json\n{"a": 1}\n```') == {"a": 1}
    assert _parse_json_response('```\n{"a": 1}\n```') == {"a": 1}


def test_parse_json_with_surrounding_prose():
    assert _parse_json_response('Sure! Here you go:\n{"a": 1}\nHope that helps.') == {"a": 1}


def test_parse_returns_none_on_garbage_or_non_object():
    assert _parse_json_response("sorry, not available") is None
    assert _parse_json_response("[1, 2, 3]") is None   # a JSON array, not an object
    assert _parse_json_response("") is None


def test_generate_structured_returns_parsed_dict_and_requests_json():
    comp = object.__new__(LLMComponent)  # bypass heavy init
    comp.providers = {}

    async def fake_chat(messages, preferred, model, **kwargs):
        assert kwargs.get("response_format") == {"type": "json_object"}  # PR3 default applied
        return '{"intent": "home.turn_on", "confidence": 0.9}'

    comp._chat_with_fallback = fake_chat  # type: ignore[method-assign]
    out = asyncio.run(comp.generate_structured([{"role": "user", "content": "lights on"}]))
    assert out == {"intent": "home.turn_on", "confidence": 0.9}


def test_generate_structured_abstains_on_non_json():
    comp = object.__new__(LLMComponent)
    comp.providers = {}

    async def fake_chat(messages, preferred, model, **kwargs):
        return "Sorry, a language model isn't available right now."  # the offline floor text

    comp._chat_with_fallback = fake_chat  # type: ignore[method-assign]
    assert asyncio.run(comp.generate_structured([{"role": "user", "content": "x"}])) is None
