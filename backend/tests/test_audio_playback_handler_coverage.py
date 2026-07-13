"""Characterization tests for AudioPlaybackIntentHandler (TEST-7 Phase D / TEST-8).

Covers the two behaviours the handler is responsible for:

1. The fire-and-forget *launch* path (`_handle_play_audio` / `_handle_stop_audio`) — that the
   handler hands the right action coroutine + kwargs to the F&F machinery and turns the returned
   action metadata into an action ``IntentResult``. The F&F machinery itself touches the global
   client registry, so it is stubbed on the instance (kept hermetic — no global mutation).
2. Graceful degradation when the injected audio port is ``None`` — every action coroutine returns
   ``False`` and the provider-management intents return a localized error result, instead of crashing.

Handlers are built with ``object.__new__`` to skip the heavy ``IntentHandler.__init__`` (donations,
notification/metrics services, timeout-task registries). Only the attributes each method actually
reads are wired up.
"""

import asyncio
import logging
import tempfile
import unittest
from pathlib import Path

from locveil_voice.intents.handlers.audio_playback_handler import AudioPlaybackIntentHandler
from locveil_voice.intents.models import Intent, IntentResult
from locveil_voice.intents.context_models import UnifiedConversationContext


class _FakeAssetLoader:
    """Stub IntentAssetLoader — returns format-strings for known template names only."""

    def __init__(self, templates=None, assets_root=None):
        self._templates = templates or {}
        self.assets_root = assets_root

    def get_template(self, handler_name, template_name, language):
        return self._templates.get(template_name)


class _StubAudioPort:
    """Stub AudioPort capturing which capability calls the handler makes."""

    def __init__(self, *, pause_raises=False, resume_raises=False, stop_raises=False):
        self.calls = []
        self._pause_raises = pause_raises
        self._resume_raises = resume_raises
        self._stop_raises = stop_raises
        self.providers = {"sounddevice": object(), "aplay": object()}

    async def pause_audio(self):
        self.calls.append("pause")
        if self._pause_raises:
            raise RuntimeError("pause boom")

    async def resume_audio(self):
        self.calls.append("resume")
        if self._resume_raises:
            raise RuntimeError("resume boom")

    async def stop_playback(self):
        self.calls.append("stop")
        if self._stop_raises:
            raise RuntimeError("stop boom")

    async def play_file(self, file_path, **kwargs):
        self.calls.append(("play_file", file_path))

    def parse_provider_name_from_text(self, text):
        return None

    def set_default_provider(self, name):
        self.calls.append(("set_default", name))
        return name in self.providers

    def get_providers_info(self):
        return "providers: sounddevice, aplay"


_DEFAULT_TEMPLATES = {
    "start_playback": "Playing {audio_file}",
    "stop_audio": "Stopped",
    "error_general": "Error: {error}",
    "provider_switched": "Switched to {provider_name}",
    "provider_unknown": "Unknown, available: {available}",
}


def _handler(*, audio_component=None, asset_loader="default"):
    h = object.__new__(AudioPlaybackIntentHandler)
    h._audio_component = audio_component
    h.logger = logging.getLogger("test.audio_playback")
    if asset_loader == "default":
        asset_loader = _FakeAssetLoader(_DEFAULT_TEMPLATES)
    h.asset_loader = asset_loader
    return h


def _context():
    return UnifiedConversationContext(session_id="s1", client_id="kitchen", language="en")


class TestAudioComponentInjection(unittest.TestCase):
    def test_get_audio_component_returns_injected_port(self):
        port = _StubAudioPort()
        h = _handler(audio_component=port)
        self.assertIs(asyncio.run(h._get_audio_component()), port)

    def test_get_audio_component_none_when_not_injected(self):
        h = _handler(audio_component=None)
        self.assertIsNone(asyncio.run(h._get_audio_component()))


class TestFireAndForgetLaunch(unittest.TestCase):
    """The launch path: handler -> execute_fire_and_forget_with_context -> action IntentResult."""

    def _launch(self, coro_factory):
        captured = {}

        async def fake_ff(action_func, action_name, domain, context, **kwargs):
            captured["action_func"] = action_func
            captured["action_name"] = action_name
            captured["domain"] = domain
            captured["kwargs"] = kwargs
            return {"active_actions": {action_name: {"status": "running"}}}

        async def run():
            h = _handler(audio_component=_StubAudioPort())
            h.execute_fire_and_forget_with_context = fake_ff
            return await coro_factory(h)

        result = asyncio.run(run())
        return result, captured

    def test_play_audio_launches_start_action_with_entities(self):
        intent = Intent(name="audio.play",
                        entities={"file": "song.mp3", "source": "stream"},
                        confidence=1.0, raw_text="play song.mp3")
        result, captured = self._launch(lambda h: h._handle_play_audio(intent, _context()))

        # Immediate, spoken action result rendered from the template.
        self.assertIsInstance(result, IntentResult)
        self.assertTrue(result.success)
        self.assertTrue(result.should_speak)
        self.assertEqual(result.text, "Playing song.mp3")
        self.assertEqual(result.action_metadata,
                         {"active_actions": {captured["action_name"]: {"status": "running"}}})

        # Correct action coroutine + domain + kwargs were handed to the F&F machinery.
        self.assertEqual(captured["domain"], "audio")
        self.assertTrue(captured["action_name"].startswith("audio_"))
        self.assertEqual(captured["action_func"].__name__, "_start_audio_playback_action")
        self.assertEqual(captured["kwargs"],
                         {"audio_file": "song.mp3", "source": "stream", "language": "en"})

    def test_play_audio_defaults_when_no_entities(self):
        intent = Intent(name="audio.play", entities={}, confidence=1.0, raw_text="play")
        result, captured = self._launch(lambda h: h._handle_play_audio(intent, _context()))
        self.assertEqual(result.text, "Playing default_audio")
        self.assertEqual(captured["kwargs"],
                         {"audio_file": "default_audio", "source": "local", "language": "en"})

    def test_stop_audio_launches_stop_action(self):
        intent = Intent(name="audio.stop", entities={}, confidence=1.0, raw_text="stop")
        result, captured = self._launch(lambda h: h._handle_stop_audio(intent, _context()))
        self.assertEqual(result.text, "Stopped")
        self.assertEqual(captured["domain"], "audio")
        self.assertTrue(captured["action_name"].startswith("audio_stop_all_"))
        self.assertEqual(captured["action_func"].__name__, "_stop_audio_playback_action")
        self.assertEqual(captured["kwargs"], {"language": "en"})


class TestActionCoroutinesGracefulDegradation(unittest.TestCase):
    """When the audio port is None every action coroutine degrades to False (no crash)."""

    def test_start_action_returns_false_without_component(self):
        h = _handler(audio_component=None)
        self.assertFalse(asyncio.run(
            h._start_audio_playback_action("a.mp3", "local", "en")))

    def test_pause_action_returns_false_without_component(self):
        h = _handler(audio_component=None)
        self.assertFalse(asyncio.run(h._pause_audio_playback_action("en")))

    def test_resume_action_returns_false_without_component(self):
        h = _handler(audio_component=None)
        self.assertFalse(asyncio.run(h._resume_audio_playback_action("en")))

    def test_stop_action_returns_false_without_component(self):
        h = _handler(audio_component=None)
        self.assertFalse(asyncio.run(h._stop_audio_playback_action("en")))


class TestActionCoroutinesWithPort(unittest.TestCase):
    """Happy + error paths of each action coroutine against a stub port."""

    def test_start_action_plays_resolved_media_file(self):
        # The real wiring: resolve <assets_root>/audio/timer.wav and dispatch it to the port's play_file.
        with tempfile.TemporaryDirectory() as d:
            media = Path(d) / "audio"
            media.mkdir()
            (media / "timer.wav").write_bytes(b"RIFF\x00\x00\x00\x00WAVE")
            port = _StubAudioPort()
            h = _handler(audio_component=port,
                         asset_loader=_FakeAssetLoader(_DEFAULT_TEMPLATES, assets_root=d))
            self.assertTrue(asyncio.run(h._start_audio_playback_action("timer", "local", "en")))
            self.assertEqual(port.calls, [("play_file", (media / "timer.wav").resolve())])

    def test_start_action_media_not_found_returns_false(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "audio").mkdir()
            port = _StubAudioPort()
            h = _handler(audio_component=port,
                         asset_loader=_FakeAssetLoader(_DEFAULT_TEMPLATES, assets_root=d))
            self.assertFalse(asyncio.run(h._start_audio_playback_action("missing", "local", "en")))
            self.assertEqual(port.calls, [])  # never dispatched

    def test_start_action_unsupported_source_returns_false(self):
        port = _StubAudioPort()
        h = _handler(audio_component=port)
        self.assertFalse(asyncio.run(h._start_audio_playback_action("timer", "url", "en")))
        self.assertEqual(port.calls, [])

    def test_start_action_rejects_traversal_name(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "audio").mkdir()
            port = _StubAudioPort()
            h = _handler(audio_component=port,
                         asset_loader=_FakeAssetLoader(_DEFAULT_TEMPLATES, assets_root=d))
            self.assertFalse(asyncio.run(h._start_audio_playback_action("../secret", "local", "en")))
            self.assertEqual(port.calls, [])

    def test_pause_action_calls_port_and_succeeds(self):
        port = _StubAudioPort()
        h = _handler(audio_component=port)
        self.assertTrue(asyncio.run(h._pause_audio_playback_action("en")))
        self.assertIn("pause", port.calls)

    def test_pause_action_port_error_returns_false(self):
        port = _StubAudioPort(pause_raises=True)
        h = _handler(audio_component=port)
        self.assertFalse(asyncio.run(h._pause_audio_playback_action("en")))

    def test_resume_action_calls_port_and_succeeds(self):
        port = _StubAudioPort()
        h = _handler(audio_component=port)
        self.assertTrue(asyncio.run(h._resume_audio_playback_action("en")))
        self.assertIn("resume", port.calls)

    def test_resume_action_port_error_returns_false(self):
        port = _StubAudioPort(resume_raises=True)
        h = _handler(audio_component=port)
        self.assertFalse(asyncio.run(h._resume_audio_playback_action("en")))

    def test_stop_action_calls_port_and_succeeds(self):
        port = _StubAudioPort()
        h = _handler(audio_component=port)
        self.assertTrue(asyncio.run(h._stop_audio_playback_action("en")))
        self.assertIn("stop", port.calls)

    def test_stop_action_port_error_returns_false(self):
        # Honest stop: a component-level failure surfaces as failure (no "assume success anyway").
        port = _StubAudioPort(stop_raises=True)
        h = _handler(audio_component=port)
        self.assertFalse(asyncio.run(h._stop_audio_playback_action("en")))
        self.assertIn("stop", port.calls)


class TestProviderManagementDegradation(unittest.TestCase):
    """Provider switch/list intents degrade to a localized error result when the port is None."""

    def test_switch_provider_without_component_is_error_result(self):
        h = _handler(audio_component=None)
        intent = Intent(name="audio.switch_provider", entities={"provider": "aplay"},
                        confidence=1.0, raw_text="use aplay")
        result = asyncio.run(h._handle_switch_audio_provider(intent, _context()))
        self.assertFalse(result.success)
        self.assertEqual(result.text, "Error: Audio component not available")

    def test_list_providers_without_component_is_error_result(self):
        h = _handler(audio_component=None)
        intent = Intent(name="audio.list_providers", entities={}, confidence=1.0, raw_text="list")
        result = asyncio.run(h._handle_list_audio_providers(intent, _context()))
        self.assertFalse(result.success)
        self.assertEqual(result.text, "Error: Audio component not available")

    def test_switch_provider_success_with_port(self):
        port = _StubAudioPort()
        h = _handler(audio_component=port)
        intent = Intent(name="audio.switch_provider", entities={"provider": "aplay"},
                        confidence=1.0, raw_text="use aplay")
        result = asyncio.run(h._handle_switch_audio_provider(intent, _context()))
        self.assertTrue(result.success)
        self.assertEqual(result.text, "Switched to aplay")
        self.assertIn(("set_default", "aplay"), port.calls)

    def test_switch_provider_unknown_provider_reports_available(self):
        port = _StubAudioPort()
        h = _handler(audio_component=port)
        intent = Intent(name="audio.switch_provider", entities={"provider": "nope"},
                        confidence=1.0, raw_text="use nope")
        result = asyncio.run(h._handle_switch_audio_provider(intent, _context()))
        self.assertFalse(result.success)
        self.assertIn("Unknown, available:", result.text)

    def test_switch_provider_no_name_specified_is_error(self):
        port = _StubAudioPort()  # parse_provider_name_from_text returns None
        h = _handler(audio_component=port)
        intent = Intent(name="audio.switch_provider", entities={}, confidence=1.0, raw_text="switch")
        result = asyncio.run(h._handle_switch_audio_provider(intent, _context()))
        self.assertFalse(result.success)
        self.assertEqual(result.text, "Error: Provider name not specified")

    def test_list_providers_returns_info_with_port(self):
        port = _StubAudioPort()
        h = _handler(audio_component=port)
        intent = Intent(name="audio.list_providers", entities={}, confidence=1.0, raw_text="list")
        result = asyncio.run(h._handle_list_audio_providers(intent, _context()))
        self.assertTrue(result.success)
        self.assertEqual(result.text, "providers: sounddevice, aplay")


class TestTemplateGuards(unittest.TestCase):
    def test_get_template_without_asset_loader_raises(self):
        h = _handler(audio_component=None, asset_loader=None)
        with self.assertRaises(RuntimeError):
            h._get_template("start_playback", "en", audio_file="x")

    def test_get_template_missing_template_raises(self):
        h = _handler(audio_component=None, asset_loader=_FakeAssetLoader({}))
        with self.assertRaises(RuntimeError):
            h._get_template("start_playback", "en", audio_file="x")


if __name__ == "__main__":
    unittest.main()
