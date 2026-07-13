"""Silero TTS model-id routing (QUAL-49).

Regression: silero v3/v4 used to place the model at `<dir>/<config:model_file>` with a shared
default (`v3_ru.pt`), bypassing the AssetManager model-id router — so two v3 languages that both
left `model_file` at the default resolved to the *same* file. The fix routes the path through
`get_model_path("silero_v{3,4}", model_id)` so distinct models always get distinct paths.
"""

from locveil_voice.providers.tts.silero_v3 import SileroV3TTSProvider
from locveil_voice.providers.tts.silero_v4 import SileroV4TTSProvider


def test_v3_model_id_routes_to_distinct_paths():
    # Different v3 languages must never collide on a shared default file.
    ru = SileroV3TTSProvider({"model": "v3_ru"}).model_file
    en = SileroV3TTSProvider({"model": "v3_en"}).model_file
    assert ru.name == "v3_ru.pt"
    assert en.name == "v3_en.pt"
    assert ru != en                       # anti-collision: the whole point of the fix
    assert ru.parent == en.parent         # same provider dir, distinct files


def test_v3_default_is_russian():
    p = SileroV3TTSProvider({})
    assert p.model_id == "v3_ru"
    assert p.model_file.name == "v3_ru.pt"
    # RU model keeps the Russian speaker set + accent controls (I18N-7 regression guard).
    assert p.default_speaker == "xenia"
    assert p.put_accent is True and p.put_yo is True
    assert p.get_capabilities()["languages"] == ["ru-RU"]
    assert "stress_placement" in p.get_capabilities()["features"]


def test_v3_en_selects_english_speakers_and_disables_accent():
    # I18N-7: model=v3_en pulls the English speaker set + drops the Russian accent/yo path.
    p = SileroV3TTSProvider({"model": "v3_en"})
    assert p._speakers[:2] == ["en_0", "en_1"] and len(p._speakers) == 118
    assert p.default_speaker == "en_0"            # ru default "xenia" is invalid → model's first
    assert p.put_accent is False and p.put_yo is False
    assert p.get_capabilities()["languages"] == ["en-US"]
    assert "stress_placement" not in p.get_capabilities()["features"]
    assert p.speaker_by_assname == {}             # Russian-persona mapping is off for English


def test_v4_routes_by_model_id():
    p = SileroV4TTSProvider({"model": "v4_ru"})
    assert p.model_file.name == "v4_ru.pt"
    # model_url is derived from the descriptor for the selected model_id (legacy-fallback safety).
    assert p.model_url == p._get_default_model_urls()["v4_ru"]


def test_explicit_model_file_override_still_honored():
    # Back-compat: an explicit model_file wins over model-id routing.
    p = SileroV4TTSProvider({"model_file": "custom.pt"})
    assert p.model_file.name == "custom.pt"
