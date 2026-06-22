"""QUAL-34 — declared params are now consumed (offline/deterministic wirings).

Covers the wire-decisions that don't need an LLM/components: datetime.relative (date offset),
greetings.time_of_day (explicit time-of-day greeting), voice_synthesis.voice (NLU entity migration).
The remove-decisions are covered by the donations simply no longer declaring those params.
"""
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from irene.core.intent_asset_loader import IntentAssetLoader, AssetLoaderConfig
from irene.intents.handlers.datetime import DateTimeIntentHandler
from irene.intents.handlers.greetings import GreetingsIntentHandler
from irene.intents.handlers.voice_synthesis_handler import VoiceSynthesisIntentHandler
from irene.intents.models import Intent
from irene.intents.context_models import UnifiedConversationContext


def _run(c):
    return asyncio.run(c)


def _handler(cls, name):
    loader = IntentAssetLoader(Path("assets"), AssetLoaderConfig())
    _run(loader.load_all_assets([name]))
    h = cls()
    h.set_asset_loader(loader)
    h.set_donation(loader.donations[name])
    return h


def _ctx(lang="ru"):
    c = UnifiedConversationContext(session_id="s")
    c.language = lang
    return c


def test_datetime_relative_offsets_the_date():
    h = _handler(DateTimeIntentHandler, "datetime")
    def day(rel):
        i = Intent(name="datetime.current_date", action="current_date",
                   entities=({"relative": rel} if rel else {}), confidence=0.9, raw_text="дата")
        return _run(h._handle_date_request(i, _ctx("ru"))).text
    assert day("tomorrow").startswith("Завтра")
    assert day("yesterday").startswith("Вчера")
    assert day(None).startswith("Сегодня")
    # the english side leads differently
    i = Intent(name="datetime.current_date", action="current_date",
               entities={"relative": "tomorrow"}, confidence=0.9, raw_text="date")
    assert _run(h._handle_date_request(i, _ctx("en"))).text.startswith("Tomorrow")


def test_greetings_time_of_day_overrides_clock():
    h = _handler(GreetingsIntentHandler, "greetings")
    i = Intent(name="greetings.hello", entities={"time_of_day": "evening"}, confidence=0.9, raw_text="добрый вечер")
    assert "вечер" in _run(h._handle_greeting(i, _ctx("ru"))).text.lower()
    i_en = Intent(name="greetings.hello", entities={"time_of_day": "morning"}, confidence=0.9, raw_text="good morning")
    assert "morning" in _run(h._handle_greeting(i_en, _ctx("en"))).text.lower()


def test_voice_synthesis_consumes_voice_entity():
    h = _handler(VoiceSynthesisIntentHandler, "voice_synthesis")
    # voice CHOICE coerces against its declared choices; absent → None (optional)
    i = Intent(name="voice_synthesis.voice", entities={"voice": "xenia", "text": "привет"},
               confidence=0.9, raw_text="скажи привет голосом ксения")
    assert h.get_param(i, "voice", default=None) == "xenia"
    assert h.get_param(i, "text", default=None) == "привет"
    i2 = Intent(name="voice_synthesis.voice", entities={}, confidence=0.9, raw_text="скажи привет")
    assert h.get_param(i2, "voice", default=None) is None
