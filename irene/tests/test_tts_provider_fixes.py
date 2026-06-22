"""Regression tests for the standalone-correctness TTS fixes (review CR-A4, CR-A8)."""
import asyncio
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from irene.providers.tts.vosk import VoskTTSProvider
from irene.providers.tts.elevenlabs import ElevenLabsTTSProvider
from irene.providers.tts.silero_v3 import SileroV3TTSProvider
from irene.providers.tts.silero_v4 import SileroV4TTSProvider


def _arun(coro):
    return asyncio.run(coro)


class TestVoskTTSIsAvailable(unittest.TestCase):
    """CR-A4: is_available must probe the correct asset namespace so the model can download on first run."""

    def _provider(self, get_model_info):
        # Bypass __init__ (which wires the real asset manager); set only what is_available reads.
        p = object.__new__(VoskTTSProvider)
        p._available = True
        p.model_path = Path("/nonexistent/vosk_tts_model")  # not downloaded yet → take the asset-manager path
        p.asset_manager = SimpleNamespace(get_model_info=get_model_info)
        return p

    def test_queries_vosk_tts_namespace_not_vosk(self):
        calls = []

        def get_model_info(provider, model_id):
            calls.append((provider, model_id))
            return {"url": "..."} if (provider, model_id) == ("vosk_tts", "ru_multi") else None

        p = self._provider(get_model_info)
        # The bug queried ("vosk","tts") → None → is_available False → model never downloaded.
        self.assertTrue(_arun(p.is_available()))
        self.assertEqual(calls, [("vosk_tts", "ru_multi")])

    def test_unavailable_when_model_info_missing(self):
        p = self._provider(lambda provider, model_id: None)
        self.assertFalse(_arun(p.is_available()))


class TestElevenLabsSynthesizeRaises(unittest.TestCase):
    """CR-A8: synthesize_to_file must raise on failure (not silently write no file)."""

    def test_raises_runtimeerror_on_generation_failure(self):
        p = object.__new__(ElevenLabsTTSProvider)
        p.voice_id, p.stability, p.similarity_boost = "v", 0.5, 0.5
        p._generate_audio = AsyncMock(side_effect=Exception("quota exceeded"))
        out = Path("/tmp/irene_elevenlabs_should_not_exist.wav")
        if out.exists():
            out.unlink()
        with self.assertRaises(RuntimeError):
            _arun(p.synthesize_to_file("hi", out))
        self.assertFalse(out.exists())  # no phantom file left behind


class TestSileroIsAvailableLocalOnly(unittest.TestCase):
    """CR-A12: is_available is local-only (torch present) for both v3 and v4 — no blocking network probe."""

    def _provider(self, cls, torch):
        p = object.__new__(cls)
        p._available = True
        p._torch = torch
        return p

    def test_v3_available_without_model_or_network(self):
        # v3 previously did a blocking requests.head(model_url) here; now torch-present is enough.
        self.assertTrue(_arun(self._provider(SileroV3TTSProvider, object()).is_available()))

    def test_v4_available_with_torch(self):
        self.assertTrue(_arun(self._provider(SileroV4TTSProvider, object()).is_available()))

    def test_unavailable_without_torch(self):
        self.assertFalse(_arun(self._provider(SileroV3TTSProvider, None).is_available()))
        self.assertFalse(_arun(self._provider(SileroV4TTSProvider, None).is_available()))


class TestSileroDownloadUsesModelUrl(unittest.TestCase):
    """CR-A13: _download_model uses self.model_url (v4 previously hardcoded the RU wheel)."""

    def _download_with(self, cls, model_url):
        p = object.__new__(cls)
        p.model_url = model_url
        p._version = "vX"
        calls = []
        p._torch = SimpleNamespace(hub=SimpleNamespace(
            download_url_to_file=lambda url, path: calls.append((url, path))))
        p._download_model(Path("/tmp/irene_silero_model.pt"))
        return calls

    def test_v4_download_uses_self_model_url(self):
        url = "https://example.test/custom_v4.pt"
        self.assertEqual(self._download_with(SileroV4TTSProvider, url),
                         [(url, "/tmp/irene_silero_model.pt")])

    def test_v3_download_uses_self_model_url(self):
        url = "https://example.test/custom_v3.pt"
        self.assertEqual(self._download_with(SileroV3TTSProvider, url),
                         [(url, "/tmp/irene_silero_model.pt")])


if __name__ == "__main__":
    unittest.main()
