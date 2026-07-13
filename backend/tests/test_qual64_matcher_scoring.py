"""QUAL-64 — pattern-stage scoring: specificity + donation boost (was: load-order ties).

Before the tune, every match in a method tier scored an identical constant, so «включи кино»
(scenario) TIED with «включи» (power) and the stable sort let donation LOAD ORDER pick the
winner; the authored per-method `boost` was never consulted. These tests pin the fix with the
full real donation set — the five collected exhibits route correctly AND the bread-and-butter
routings stay put.
"""

from pathlib import Path

import pytest

from locveil_voice.core.intent_asset_loader import AssetLoaderConfig, IntentAssetLoader
from locveil_voice.intents.context_models import UnifiedConversationContext
from locveil_voice.providers.nlu.hybrid_keyword_matcher import HybridKeywordMatcherProvider

ALL_HANDLERS = ["timer", "random_handler", "system_service_handler", "audio_playback_handler",
                "system", "greetings", "smart_home", "text_enhancement_handler",
                "provider_control_handler", "conversation", "datetime", "translation_handler",
                "voice_synthesis_handler", "speech_recognition_handler", "report"]

CASES = [
    # the QUAL-64 exhibits — longer specific phrases must beat bare verbs
    ("выключи кино", "smart_home.scenario_stop"),
    ("включи кино с видеокассеты", "smart_home.scenario_start"),
    ("переключи субтитры на медиаплеере", "smart_home.tracks_subtitles"),
    ("переключи аудиодорожку", "smart_home.tracks_audio"),
    # regressions — the bread-and-butter routings must not move
    ("включи телек", "smart_home.power_on"),
    ("выключи свет", "smart_home.power_off"),
    ("закрой шторы", "smart_home.cover_close"),
    ("поставь на паузу", "smart_home.playback_pause"),
    ("поставь таймер на 5 минут", "timer.set"),
    ("переключи усилитель на cd", "smart_home.input_select"),
    ("переключи телек на hdmi1", "smart_home.input_select"),
    ("запусти youtube на телеке", "smart_home.app_launch"),
    ("сделай телек громче", "smart_home.volume_up"),
    ("какая температура в душевой", "smart_home.read_state"),
    # QUAL-35 Slice 3 (F96): the bare «кондиционер на» pattern was greedy — a setpoint sentence
    # routed to hvac_mode at full confidence; mode-worded phrases keep both routings honest
    ("поставь в спальне кондиционер на двадцать два градуса", "smart_home.set_setpoint"),
    ("кондиционер на охлаждение", "smart_home.hvac_mode"),
    ("переведи кондиционер в режим осушения", "smart_home.hvac_mode"),
    ("вентилятор на скорость 2", "smart_home.hvac_fan"),
    # BUG-26: authored boosts cancelled the specificity edge EXACTLY (1.4256 == 1.4256) and the
    # tie fell to donation load order — system.about lost its own literal phrase to the
    # two-token «расскажи о» prefix. Tie-break = matched-pattern token count, never load order.
    ("расскажи о себе", "system.about"),
    # ARCH-31: the report intent and its non-collisions
    ("сообщи о проблеме", "report.problem"),
    ("у меня проблема", "report.problem"),
    ("что-то не работает", "report.problem"),
    ("кто ты", "system.about"),
    ("что такое фотосинтез", "conversation.reference"),
    ("расскажи о погоде в москве", "conversation.reference"),
    ("справка", "system.help"),
]


@pytest.fixture(scope="module")
async def provider():
    loader = IntentAssetLoader(Path("assets"), AssetLoaderConfig())
    await loader.load_all_assets(ALL_HANDLERS)
    p = HybridKeywordMatcherProvider({})
    await p._initialize_from_donations(loader.convert_to_keyword_donations())
    return p


@pytest.mark.parametrize("text,expected", CASES)
async def test_routing(provider, text, expected):
    ctx = UnifiedConversationContext(session_id="s", language="ru")
    intent = await provider.recognize(text, ctx)
    assert intent is not None, text
    assert intent.name == expected, f"{text!r} -> {intent.name} (conf {intent.confidence:.2f})"


async def test_donation_boost_is_consulted(provider):
    # the field existed since QUAL-29 but was dead in pattern scoring until QUAL-64
    assert provider.intent_boosts.get("smart_home.scenario_stop") == pytest.approx(1.3)
    assert provider._pattern_score("smart_home.scenario_stop", 1.2, 2) > \
           provider._pattern_score("smart_home.power_off", 1.2, 1)
