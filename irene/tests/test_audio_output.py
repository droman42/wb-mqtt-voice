"""ARCH-15 PR-8 — local audio/voice SPEECH output + OutputManager conversational fallback.

The SPEECH OutputPort wraps TTS+audio (synthesize → play). The OutputManager gains a designated
conversational fallback (the local speaker) so a voice device's deferred F&F speaks even though its
source label can't be a stable origin key — which is what lets NotificationService retire the PR-5a
legacy-TTS fallback and restore pure D-3.
"""

from pathlib import Path

import pytest

from irene.core.interfaces.output import OutputModality
from irene.core.notifications import NotificationMessage, NotificationPriority, NotificationService
from irene.intents.context_models import RequestContext
from irene.intents.models import IntentResult
from irene.outputs.audio import AudioSpeechOutput
from irene.outputs.console import ConsoleOutput
from irene.outputs.manager import OutputManager

SPEECH, TEXT = OutputModality.SPEECH, OutputModality.TEXT


class _FakeTTS:
    def __init__(self):
        self.calls = []

    async def synthesize_to_file(self, text, path):
        self.calls.append(text)
        Path(path).write_bytes(b"RIFF")  # create the temp file so the adapter's cleanup runs


class _FakeAudio:
    def __init__(self):
        self.played = []

    async def play_file(self, path):
        self.played.append(str(path))


# --- the SPEECH adapter --------------------------------------------------------------------

async def test_speech_output_synthesizes_and_plays():
    tts, audio = _FakeTTS(), _FakeAudio()
    out = AudioSpeechOutput(tts, audio, name="audio")
    assert await out.is_available()
    assert out.supported_modalities() == {SPEECH, TEXT}

    dr = await out.deliver(IntentResult(text="таймер сработал"), RequestContext(source="voice"), SPEECH)

    assert dr.delivered and dr.modality is SPEECH
    assert tts.calls == ["таймер сработал"] and len(audio.played) == 1


async def test_speech_output_unavailable_without_components():
    out = AudioSpeechOutput(None, None)
    assert not await out.is_available()
    dr = await out.deliver(IntentResult(text="x"), RequestContext(source="voice"), SPEECH)
    assert dr.dropped


async def test_speech_output_empty_text_is_noop():
    tts, audio = _FakeTTS(), _FakeAudio()
    out = AudioSpeechOutput(tts, audio)
    dr = await out.deliver(IntentResult(text="  "), RequestContext(source="voice"), SPEECH)
    assert dr.delivered and tts.calls == []


# --- OutputManager conversational fallback -------------------------------------------------

async def test_conversational_fallback_speaks_when_no_origin_match():
    tts, audio = _FakeTTS(), _FakeAudio()
    om = OutputManager()
    await om.add_output("audio", AudioSpeechOutput(tts, audio, name="audio"))
    om.designate_conversational_fallback("audio")

    # a voice-set F&F: source "voice" matches no origin → falls back to the local speaker
    res = await om.deliver(IntentResult(text="таймер"), RequestContext(source="voice"), SPEECH)

    assert len(res) == 1 and res[0].delivered
    assert tts.calls == ["таймер"]


async def test_origin_match_preferred_over_fallback():
    captured = []
    tts, audio = _FakeTTS(), _FakeAudio()
    om = OutputManager()
    await om.add_output("console", ConsoleOutput(sink=captured.append, origin="cli"))
    await om.add_output("audio", AudioSpeechOutput(tts, audio, name="audio"))
    om.designate_conversational_fallback("audio")

    # a cli-originated result goes to the console, NOT the speaker fallback
    res = await om.deliver(IntentResult(text="ok"), RequestContext(source="cli"), TEXT)

    assert captured == ["📝 ok"] and tts.calls == []


async def test_fallback_cleared_on_remove():
    tts, audio = _FakeTTS(), _FakeAudio()
    om = OutputManager()
    await om.add_output("audio", AudioSpeechOutput(tts, audio, name="audio"))
    om.designate_conversational_fallback("audio")
    om.remove_output("audio")
    res = await om.deliver(IntentResult(text="x"), RequestContext(source="voice"), SPEECH)
    assert res == []  # fallback gone with the output


# --- end-to-end: voice F&F speaks via the fallback (D-3 path, no legacy fallback) -----------

async def test_voice_notification_speaks_via_fallback():
    tts, audio = _FakeTTS(), _FakeAudio()
    om = OutputManager()
    await om.add_output("audio", AudioSpeechOutput(tts, audio, name="audio"))
    om.designate_conversational_fallback("audio")
    svc = NotificationService()
    svc.set_output_manager(om)

    note = NotificationMessage(message="таймер сработал", source="voice", session_id="s1",
                               priority=NotificationPriority.HIGH)
    await svc._deliver_notification(note)

    assert tts.calls == ["таймер сработал"]
