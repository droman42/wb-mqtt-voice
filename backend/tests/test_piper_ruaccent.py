"""PiperRuAccentTTSProvider — Piper + RUAccent stress pass (ARCH-24 T2, PR3).

The subclass overrides ONLY `_prepare_text` (everything else inherited from PiperTTSProvider).
Tests mock the accentizer so no RUAccent model is downloaded.
"""

import asyncio

from locveil_voice.providers.tts.piper import PiperTTSProvider
from locveil_voice.providers.tts.piper_ruaccent import PiperRuAccentTTSProvider


def test_subclass_of_piper_with_own_identity():
    assert issubclass(PiperRuAccentTTSProvider, PiperTTSProvider)
    p = PiperRuAccentTTSProvider({})
    assert p.get_provider_name() == "piper_ruaccent"
    # Shares the base voice packs (inherited descriptors) — same models, just an extra text pass.
    assert "irina" in PiperRuAccentTTSProvider._get_default_model_urls()


def test_deps_include_both_extras():
    # sherpa runtime (inherited need) + the 64-bit-only ruaccent stack.
    assert PiperRuAccentTTSProvider.get_python_dependencies() == ["asr-onnx", "tts-ruaccent"]


def test_capabilities_advertise_accentor():
    caps = PiperRuAccentTTSProvider({}).get_capabilities()
    assert "ru_stress_accentor" in caps["features"]
    assert caps["quality"] == "medium-high"
    assert "irina" in caps["voices"]  # inherited


def test_prepare_text_runs_accentizer_not_identity():
    # Base piper's _prepare_text is identity; this subclass marks stress. Mock the accentizer so the
    # test doesn't pull the RUAccent model (load() downloads from HF).
    class FakeAcc:
        def process_all(self, text):
            return text.replace("привет", "приве+т")

    p = PiperRuAccentTTSProvider({})
    p._accentizer = FakeAcc()  # short-circuits _ensure_accentizer
    assert asyncio.run(p._prepare_text("привет мир")) == "приве+т мир"


def test_omograph_config_defaults_and_override():
    assert PiperRuAccentTTSProvider({}).omograph_model_size == "turbo"
    assert PiperRuAccentTTSProvider({"omograph_model_size": "big"}).omograph_model_size == "big"
    assert PiperRuAccentTTSProvider({"use_dictionary": False}).use_dictionary is False
