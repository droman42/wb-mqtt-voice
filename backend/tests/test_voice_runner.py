"""
Voice runner — config-driven, provider-agnostic behaviour (QUAL-46, BUG-35).

Exercises the two pure config methods: `_modify_config_for_runner` (forces the mic-only INPUT
topology and nothing else — `[components]`/`[vad]` belong to the config file) and
`_validate_runner_specific_config` (accepts ANY configured+enabled ASR provider, not just vosk, and
refuses to start when a structurally required component is off).
"""

import asyncio
import unittest
from types import SimpleNamespace

from locveil_voice.runners.voice_runner import VoiceRunner


def _runner():
    return object.__new__(VoiceRunner)  # skip BaseRunner.__init__; the methods don't use self


def _config(*, asr_provider="whisper", providers=None, asr_enabled=True, components_asr=True,
            mic=True, mic_cfg=True, sys_mic=True, audio=True, intent_system=True,
            text_processor=True, nlu=True, vad=True):
    if providers is None:
        providers = {asr_provider: {"enabled": True}}
    return SimpleNamespace(
        inputs=SimpleNamespace(microphone=mic, web=True, cli=True, default_input="cli",
                               microphone_config=SimpleNamespace(enabled=mic_cfg)),
        system=SimpleNamespace(microphone_enabled=sys_mic),
        components=SimpleNamespace(asr=components_asr, audio=audio, intent_system=intent_system,
                                   text_processor=text_processor, nlu=nlu),
        asr=SimpleNamespace(enabled=asr_enabled, default_provider=asr_provider, providers=providers),
        vad=SimpleNamespace(enabled=vad),
    )


class TestModifyConfig(unittest.TestCase):
    def test_forces_mic_primary_plus_web(self):
        cfg = _config()
        out = asyncio.run(_runner()._modify_config_for_runner(cfg, SimpleNamespace()))
        self.assertTrue(out.inputs.microphone)
        self.assertTrue(out.inputs.web)          # the standalone serves the web API alongside the mic
        self.assertTrue(out.system.web_api_enabled)
        self.assertFalse(out.inputs.cli)
        self.assertEqual(out.inputs.default_input, "microphone")
        self.assertTrue(out.system.microphone_enabled)

    def test_never_rewrites_components_or_vad(self):
        """BUG-35: the preset owns the input-set, not `[components]`. Operator intent survives."""
        cfg = _config(audio=False, intent_system=False, text_processor=False, nlu=False,
                      components_asr=False, vad=False)
        out = asyncio.run(_runner()._modify_config_for_runner(cfg, SimpleNamespace()))
        for comp in ("asr", "audio", "intent_system", "text_processor", "nlu"):
            self.assertFalse(getattr(out.components, comp), f"{comp} must not be forced on")
        self.assertFalse(out.vad.enabled, "vad.enabled must not be forced on")

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

    def test_required_components_off_error_instead_of_being_forced_on(self):
        """BUG-35: what the runner used to switch on silently now fails loudly, naming the key."""
        for kw, needle in (({"audio": False}, "components.audio = true"),
                           ({"intent_system": False}, "components.intent_system = true"),
                           ({"nlu": False}, "components.nlu = true"),
                           ({"text_processor": False}, "components.text_processor = true"),
                           ({"vad": False}, "vad.enabled = true")):
            errs = self._errors(_config(**kw))
            self.assertTrue(any(needle in e for e in errs), f"{kw} should error mentioning {needle}")

    def test_no_vosk_specific_error_anymore(self):
        # The old runner errored unless default_provider == "vosk". Prove that's gone.
        errs = self._errors(_config(asr_provider="whisper"))
        self.assertFalse(any("must be 'vosk'" in e for e in errs))
        self.assertEqual(errs, [])


if __name__ == "__main__":
    unittest.main()
