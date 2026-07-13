"""
Characterization tests for ASRComponent (TEST-7 Phase D).

Covers the provider-selection surface that does NOT require real ASR models:
  * set_default_provider (atomic success / unknown-provider no-op)
  * reset_provider_state (all providers, single provider, not-found, reset()==False,
    reset() raising, empty-registry)
  * provider selection on process_audio / transcribe_audio (fast path, unavailable
    provider -> raise, trace path success + error re-raise)
  * provider-name parsing helpers and the formatted providers-info string
  * switch_language stub

Built with object.__new__ + hand-set attributes so no heavy construction (entry-point
discovery, metrics push task) runs. Fully hermetic: asyncio.run only, no global mutation.
"""

import asyncio
import unittest
from types import SimpleNamespace

from fastapi import HTTPException  # type: ignore

from locveil_voice.components.asr_component import ASRComponent
from locveil_voice.intents.models import AudioData


class _FakeProvider:
    """Minimal stand-in for an ASRProvider (no real model)."""

    def __init__(self, *, text="hello", languages=None, reset_result=True,
                 reset_exc=None, transcribe_exc=None):
        self._text = text
        self._languages = languages or ["ru", "en", "de", "fr"]
        self._reset_result = reset_result
        self._reset_exc = reset_exc
        self._transcribe_exc = transcribe_exc
        self.reset_calls = []
        self.last_confidence = 0.87

    async def transcribe_audio(self, audio_data, **kwargs):
        if self._transcribe_exc is not None:
            raise self._transcribe_exc
        return self._text

    def reset(self, language=None):
        self.reset_calls.append(language)
        if self._reset_exc is not None:
            raise self._reset_exc
        return self._reset_result

    def get_supported_languages(self):
        return list(self._languages)

    def get_capabilities(self):
        return {"streaming": False}


def _component(providers=None, default="vosk", language="ru"):
    comp = object.__new__(ASRComponent)
    comp.providers = providers if providers is not None else {}
    comp.default_provider = default
    comp.default_language = language
    comp.core = None
    return comp


def _audio(data=b"\x00\x01" * 100):
    return AudioData(data=data, timestamp=0.0, sample_rate=16000, channels=1,
                     format="pcm16_wav", metadata={})


class TestSetDefaultProvider(unittest.TestCase):
    def test_switch_to_known_provider(self):
        comp = _component({"vosk": _FakeProvider(), "whisper": _FakeProvider()})
        self.assertTrue(comp.set_default_provider("whisper"))
        self.assertEqual(comp.default_provider, "whisper")

    def test_unknown_provider_is_noop(self):
        comp = _component({"vosk": _FakeProvider()}, default="vosk")
        self.assertFalse(comp.set_default_provider("nope"))
        self.assertEqual(comp.default_provider, "vosk")  # unchanged

    def test_switch_provider_alias_delegates(self):
        comp = _component({"vosk": _FakeProvider(), "whisper": _FakeProvider()})
        self.assertTrue(comp.switch_provider("whisper"))
        self.assertEqual(comp.default_provider, "whisper")


class TestResetProviderState(unittest.TestCase):
    def test_reset_all_providers(self):
        p1, p2 = _FakeProvider(), _FakeProvider()
        comp = _component({"vosk": p1, "whisper": p2})
        self.assertTrue(comp.reset_provider_state(language="ru"))
        self.assertEqual(p1.reset_calls, ["ru"])
        self.assertEqual(p2.reset_calls, ["ru"])

    def test_reset_all_with_no_providers_returns_false(self):
        comp = _component({})
        self.assertFalse(comp.reset_provider_state())

    def test_reset_specific_provider(self):
        p = _FakeProvider()
        comp = _component({"vosk": p})
        self.assertTrue(comp.reset_provider_state("vosk"))
        self.assertEqual(p.reset_calls, [None])

    def test_reset_unknown_provider_returns_false(self):
        comp = _component({"vosk": _FakeProvider()})
        self.assertFalse(comp.reset_provider_state("missing"))

    def test_reset_returning_false_is_not_counted_as_success(self):
        comp = _component({"vosk": _FakeProvider(reset_result=False)})
        self.assertFalse(comp.reset_provider_state("vosk"))

    def test_reset_all_partial_success(self):
        good = _FakeProvider(reset_result=True)
        bad = _FakeProvider(reset_result=False)
        comp = _component({"good": good, "bad": bad})
        # at least one succeeded -> True overall
        self.assertTrue(comp.reset_provider_state())

    def test_reset_provider_raising_is_swallowed(self):
        comp = _component({"vosk": _FakeProvider(reset_exc=RuntimeError("boom"))})
        # exception inside the per-provider try -> counted as failure, returns False
        self.assertFalse(comp.reset_provider_state("vosk"))

    def test_reset_all_raising_provider_swallowed(self):
        ok = _FakeProvider(reset_result=True)
        boom = _FakeProvider(reset_exc=RuntimeError("boom"))
        comp = _component({"ok": ok, "boom": boom})
        self.assertTrue(comp.reset_provider_state())  # the ok one still succeeds


class TestProviderSelectionProcessAudio(unittest.TestCase):
    def test_fast_path_uses_default_provider(self):
        comp = _component({"vosk": _FakeProvider(text="привет")}, default="vosk")
        out = asyncio.run(comp.process_audio(_audio()))
        self.assertEqual(out, "привет")

    def test_explicit_provider_override(self):
        comp = _component({"vosk": _FakeProvider(text="a"),
                           "whisper": _FakeProvider(text="b")}, default="vosk")
        out = asyncio.run(comp.process_audio(_audio(), provider="whisper"))
        self.assertEqual(out, "b")

    def test_unavailable_provider_raises_valueerror(self):
        comp = _component({"vosk": _FakeProvider()}, default="vosk")
        with self.assertRaises(ValueError):
            asyncio.run(comp.process_audio(_audio(), provider="ghost"))

    def test_trace_path_success_records_stage(self):
        comp = _component({"vosk": _FakeProvider(text="traced")}, default="vosk")
        recorded = {}

        def record_stage(**kwargs):
            recorded.update(kwargs)

        trace = SimpleNamespace(enabled=True, record_stage=record_stage)
        out = asyncio.run(comp.process_audio(_audio(), trace_context=trace))
        self.assertEqual(out, "traced")
        self.assertEqual(recorded["stage_name"], "asr_transcription")
        attempts = recorded["metadata"]["provider_attempts"]
        self.assertEqual(attempts[0]["success"], True)
        self.assertEqual(attempts[0]["provider"], "vosk")

    def test_trace_path_error_is_reraised_and_recorded(self):
        comp = _component(
            {"vosk": _FakeProvider(transcribe_exc=RuntimeError("asr down"))},
            default="vosk")
        attempts_seen = {}

        def record_stage(**kwargs):  # should NOT be called on the error path
            attempts_seen.update(kwargs)

        trace = SimpleNamespace(enabled=True, record_stage=record_stage)
        with self.assertRaises(RuntimeError):
            asyncio.run(comp.process_audio(_audio(), trace_context=trace))
        # error path re-raises before record_stage, so nothing recorded
        self.assertEqual(attempts_seen, {})

    def test_trace_disabled_uses_fast_path(self):
        comp = _component({"vosk": _FakeProvider(text="fast")}, default="vosk")
        trace = SimpleNamespace(enabled=False, record_stage=lambda **k: None)
        out = asyncio.run(comp.process_audio(_audio(), trace_context=trace))
        self.assertEqual(out, "fast")


class TestProviderSelectionTranscribeAudio(unittest.TestCase):
    def test_transcribe_success(self):
        comp = _component({"vosk": _FakeProvider(text="ok")}, default="vosk")
        out = asyncio.run(comp.transcribe_audio(b"\x00" * 10))
        self.assertEqual(out, "ok")

    def test_transcribe_empty_result(self):
        comp = _component({"vosk": _FakeProvider(text="   ")}, default="vosk")
        out = asyncio.run(comp.transcribe_audio(b"\x00" * 10))
        self.assertEqual(out, "   ")

    def test_transcribe_unavailable_provider_raises_http_404(self):
        comp = _component({"vosk": _FakeProvider()}, default="vosk")
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(comp.transcribe_audio(b"x", provider="ghost"))
        self.assertEqual(ctx.exception.status_code, 404)


class TestProviderNameParsing(unittest.TestCase):
    def test_parse_direct_name_match_via_base(self):
        comp = _component({"vosk": _FakeProvider(), "whisper": _FakeProvider()})
        self.assertEqual(
            comp.parse_provider_name_from_text("switch to whisper please"),
            "whisper")

    def test_parse_russian_alias(self):
        comp = _component({"vosk": _FakeProvider()})
        # 'воск' alias -> 'vosk' (present), base match fails first
        self.assertEqual(comp.parse_provider_name_from_text("включи воск"), "vosk")

    def test_parse_no_match_returns_none(self):
        comp = _component({"vosk": _FakeProvider()})
        self.assertIsNone(comp.parse_provider_name_from_text("какая погода"))

    def test_internal_parse_alias_for_absent_provider_is_none(self):
        # alias 'гугл' -> google_cloud, but google_cloud not registered -> None
        comp = _component({"vosk": _FakeProvider()})
        self.assertIsNone(comp._parse_provider_name("используй гугл"))


class TestProvidersInfoAndLanguage(unittest.TestCase):
    def test_info_empty(self):
        comp = _component({})
        self.assertEqual(comp.get_providers_info(), "Нет доступных провайдеров ASR")

    def test_info_lists_providers_and_marks_default(self):
        comp = _component({"vosk": _FakeProvider(), "whisper": _FakeProvider()},
                          default="vosk")
        info = comp.get_providers_info()
        self.assertIn("vosk", info)
        self.assertIn("whisper", info)
        self.assertIn("по умолчанию", info)  # default marker present

    def test_switch_language_is_unimplemented_stub(self):
        comp = _component({"vosk": _FakeProvider()})
        ok, msg = asyncio.run(comp.switch_language("en"))
        self.assertFalse(ok)
        self.assertIn("не реализовано", msg)


if __name__ == "__main__":
    unittest.main()
