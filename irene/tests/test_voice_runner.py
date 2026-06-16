"""
Voice runner — config-driven, provider-agnostic behaviour (QUAL-46).

Exercises the two pure config methods: `_modify_config_for_runner` (forces mic-only + the voice
stack incl. VAD, never a specific ASR provider) and `_validate_runner_specific_config` (accepts ANY
configured+enabled ASR provider, not just vosk).
"""

import asyncio
import unittest
from types import SimpleNamespace

from ..runners.voice_runner import VoiceRunner


def _runner():
    return object.__new__(VoiceRunner)  # skip BaseRunner.__init__; the methods don't use self


def _config(*, asr_provider="whisper", providers=None, asr_enabled=True, components_asr=True,
            mic=True, mic_cfg=True, sys_mic=True):
    if providers is None:
        providers = {asr_provider: {"enabled": True}}
    return SimpleNamespace(
        inputs=SimpleNamespace(microphone=mic, web=True, cli=True, default_input="cli",
                               microphone_config=SimpleNamespace(enabled=mic_cfg)),
        system=SimpleNamespace(microphone_enabled=sys_mic),
        components=SimpleNamespace(asr=components_asr, audio=False, intent_system=False,
                                   text_processor=False, nlu=False),
        asr=SimpleNamespace(enabled=asr_enabled, default_provider=asr_provider, providers=providers),
        vad=SimpleNamespace(enabled=False),
    )


class TestModifyConfig(unittest.TestCase):
    def test_forces_mic_primary_plus_web_and_voice_stack_incl_vad(self):
        cfg = _config()
        out = asyncio.run(_runner()._modify_config_for_runner(cfg, SimpleNamespace()))
        self.assertTrue(out.inputs.microphone)
        self.assertTrue(out.inputs.web)          # the standalone serves the web API alongside the mic
        self.assertTrue(out.system.web_api_enabled)
        self.assertFalse(out.inputs.cli)
        self.assertEqual(out.inputs.default_input, "microphone")
        self.assertTrue(out.system.microphone_enabled)
        for comp in ("asr", "audio", "intent_system", "text_processor", "nlu"):
            self.assertTrue(getattr(out.components, comp), comp)
        self.assertTrue(out.vad.enabled)  # the consistency fix — no deep-init failure

    def test_does_not_pin_an_asr_provider(self):
        cfg = _config(asr_provider="sherpa_onnx")
        out = asyncio.run(_runner()._modify_config_for_runner(cfg, SimpleNamespace()))
        self.assertEqual(out.asr.default_provider, "sherpa_onnx")  # left exactly as configured


class TestValidate(unittest.TestCase):
    def _errors(self, cfg):
        return asyncio.run(_runner()._validate_runner_specific_config(cfg, SimpleNamespace()))

    def test_accepts_any_enabled_provider(self):
        for prov in ("vosk", "whisper", "sherpa_onnx", "google_cloud"):
            self.assertEqual(self._errors(_config(asr_provider=prov)), [],
                             f"{prov} should validate clean")

    def test_provider_not_configured_errors(self):
        cfg = _config(asr_provider="whisper", providers={"vosk": {"enabled": True}})
        errs = self._errors(cfg)
        self.assertTrue(any("whisper" in e and "no [asr.providers" in e for e in errs))

    def test_provider_disabled_errors(self):
        cfg = _config(asr_provider="whisper", providers={"whisper": {"enabled": False}})
        errs = self._errors(cfg)
        self.assertTrue(any("must be enabled" in e for e in errs))

    def test_no_provider_selected_errors(self):
        errs = self._errors(_config(asr_provider=""))
        self.assertTrue(any("provider must be selected" in e for e in errs))

    def test_mic_off_errors(self):
        errs = self._errors(_config(mic=False))
        self.assertTrue(any("Microphone input must be enabled" in e for e in errs))

    def test_no_vosk_specific_error_anymore(self):
        # The old runner errored unless default_provider == "vosk". Prove that's gone.
        errs = self._errors(_config(asr_provider="whisper"))
        self.assertFalse(any("must be 'vosk'" in e for e in errs))
        self.assertEqual(errs, [])


if __name__ == "__main__":
    unittest.main()
