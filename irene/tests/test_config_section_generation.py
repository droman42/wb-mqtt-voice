"""QUAL-40 regression — generated-TOML section headers must not be dropped.

`ConfigManager._generate_provider_sections` / `_generate_normalizer_sections`
built a `[base_path.<name>]` header per entry but never appended it to the
output list; the closing `"\n".join([section] + sections)` kept only the LAST
header (and placed it at the very top), so every provider/normalizer section
header except the last was dropped from the generated TOML. These tests assert
every header survives, in order, and that the result round-trips through a TOML
parser back to the original nesting.
"""

import tomllib

import pytest

from irene.config.manager import ConfigManager


@pytest.fixture
def manager() -> ConfigManager:
    return ConfigManager()


def test_provider_sections_keep_every_header(manager):
    providers = {
        "whisper": {"enabled": True, "model": "base", "sample_rate": 16000},
        "vosk": {"enabled": False, "model": "small"},
        "google_cloud": {"enabled": True, "languages": ["ru", "en"]},
    }
    out = manager._generate_provider_sections("asr.providers", providers)

    # Every header present (the bug dropped all but the last).
    for name in providers:
        assert f"[asr.providers.{name}]" in out, f"missing header for {name}"

    # Round-trips and reconstructs the full nesting (proves headers precede
    # their own keys, not the wrong section's).
    parsed = tomllib.loads(out)
    assert set(parsed["asr"]["providers"]) == set(providers)
    assert parsed["asr"]["providers"]["whisper"]["model"] == "base"
    assert parsed["asr"]["providers"]["vosk"]["enabled"] is False
    assert parsed["asr"]["providers"]["google_cloud"]["languages"] == ["ru", "en"]


def test_normalizer_sections_keep_every_header(manager):
    normalizers = {
        "numbers": {"enabled": True, "lang": "ru"},
        "prepare": {"enabled": True},
        "runorm": {"enabled": False, "model_size": "small"},
    }
    out = manager._generate_normalizer_sections("text_processor.normalizers", normalizers)

    for name in normalizers:
        assert f"[text_processor.normalizers.{name}]" in out

    parsed = tomllib.loads(out)
    assert set(parsed["text_processor"]["normalizers"]) == set(normalizers)
    assert parsed["text_processor"]["normalizers"]["runorm"]["model_size"] == "small"


def test_empty_input_returns_empty_string(manager):
    assert manager._generate_provider_sections("asr.providers", {}) == ""
    assert manager._generate_normalizer_sections("text_processor.normalizers", {}) == ""
