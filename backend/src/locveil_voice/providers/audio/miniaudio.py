"""
Miniaudio Audio Provider - Self-contained streamable playback (ARCH-20)

pyminiaudio bundles its own cross-platform backends (WASAPI / CoreAudio / ALSA / etc.),
so it needs NO system audio library. It is a real streaming backend: a pull-based
generator feeds raw PCM frames to a PlaybackDevice. This gives a second streamable
backend on every OS (alongside sounddevice; +aplay on Linux).
"""

import asyncio
import logging
import threading
import time
from pathlib import Path
from typing import Dict, Any, List, AsyncIterator

from .base import AudioProvider

logger = logging.getLogger(__name__)


class MiniaudioAudioProvider(AudioProvider):
    """
    Miniaudio audio provider for self-contained, cross-platform streaming playback.

    Features:
    - No system audio library required (backends bundled in the wheel)
    - Real streaming playout via PlaybackDevice + a pull-based PCM generator
    - File playback by decoding to PCM (wav/flac/mp3/vorbis) then streaming it
    - Async operation; graceful handling of a missing dependency
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # Configuration values
        self.device_id = config.get("device", None)  # None = default device
        self.sample_rate = config.get("sample_rate", 44100)
        self.channels = config.get("channels", 2)
        self.buffersize_msec = config.get("buffersize_msec", 200)
        self._volume = config.get("volume", 1.0)

        # Runtime state
        self._device = None
        self._available = False

        # Try to import dependencies
        try:
            import miniaudio  # type: ignore
            self._ma = miniaudio
            self._available = True
            logger.debug("Miniaudio audio provider: dependency available")
        except ImportError as e:
            self._ma = None
            self._available = False
            logger.warning(f"Miniaudio audio provider: dependency missing - {e}")

        # numpy is optional; used only for volume scaling of 16-bit PCM
        try:
            import numpy as np  # type: ignore
            self._np = np
        except ImportError:
            self._np = None

    async def is_available(self) -> bool:
        """Miniaudio is self-contained, so availability == the package being importable."""
        return self._available

    @classmethod
    def _get_default_extension(cls) -> str:
        return ".wav"

    @classmethod
    def _get_default_directory(cls) -> str:
        return "miniaudio"

    @classmethod
    def _get_default_credentials(cls) -> List[str]:
        return []

    @classmethod
    def _get_default_cache_types(cls) -> List[str]:
        return ["temp", "runtime"]

    @classmethod
    def _get_default_model_urls(cls) -> Dict[str, str]:
        return {}

    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        """Miniaudio ships its own native backends via the audio-miniaudio build extra."""
        return ["audio-miniaudio"]  # Build extra: audio-miniaudio

    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        """No system packages — backends are bundled in the wheel."""
        return {
            "linux.ubuntu": [],
            "linux.alpine": [],
            "macos": [],
            "windows": []
        }
    async def play_file(self, file_path: Path, **kwargs) -> None:
        """Decode an audio file to PCM and stream it to the device."""
        if not self._available or not self._ma:
            raise RuntimeError("Miniaudio audio backend not available")

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        try:
            volume = kwargs.get('volume', self._volume)
            decoded = await asyncio.to_thread(self._ma.decode_file, str(file_path))
            await asyncio.to_thread(
                self._play_pcm_blocking, decoded.samples.tobytes(), decoded.sample_rate,
                decoded.nchannels, decoded.sample_width, volume)
        except Exception as e:
            logger.error(f"Failed to play audio file {file_path}: {e}")
            raise RuntimeError(f"Audio playback failed: {e}")

    async def play_stream(self, audio_stream: AsyncIterator[bytes], *, sample_rate: int = 44100,
                          channels: int = 1, sample_width: int = 2, **kwargs) -> None:
        """
        Stream raw PCM frames to the device via miniaudio's PlaybackDevice (ARCH-20).

        Buffer-then-stream: drain the async stream, then feed the PCM to the device's
        pull-based generator on a worker thread.

        Args:
            audio_stream: Async iterator of raw little-endian PCM byte chunks.
            sample_rate: PCM sample rate (Hz).
            channels: Channel count.
            sample_width: Bytes per sample (2 = 16-bit).
            **kwargs: volume (float).
        """
        if not self._available or not self._ma:
            raise RuntimeError("Miniaudio audio backend not available")

        from ...utils.audio_stream import collect_pcm
        try:
            pcm = await collect_pcm(audio_stream)
            if not pcm:
                return
            volume = kwargs.get('volume', self._volume)
            await asyncio.to_thread(
                self._play_pcm_blocking, pcm, sample_rate, channels, sample_width, volume)
        except Exception as e:
            logger.error(f"Failed to play audio stream: {e}")
            raise RuntimeError(f"Audio stream playback failed: {e}")

    def _play_pcm_blocking(self, pcm: bytes, sample_rate: int, channels: int,
                           sample_width: int, volume: float) -> None:
        """Blocking raw-PCM playout via a PlaybackDevice generator (called from a thread)."""
        ma = self._ma
        if not ma:
            return

        sample_format = {
            1: ma.SampleFormat.UNSIGNED8,
            2: ma.SampleFormat.SIGNED16,
            3: ma.SampleFormat.SIGNED24,
            4: ma.SampleFormat.SIGNED32,
        }.get(sample_width, ma.SampleFormat.SIGNED16)
        frame_bytes = max(1, channels * sample_width)

        # Apply volume on 16-bit PCM (the common case) without a decode round-trip.
        if volume != 1.0 and sample_width == 2 and self._np is not None:
            samples = self._np.frombuffer(pcm, dtype=self._np.int16).astype(self._np.float32) * volume
            samples = self._np.clip(samples, -32768, 32767).astype(self._np.int16)
            pcm = samples.tobytes()

        # Trim any trailing partial frame.
        usable = len(pcm) - (len(pcm) % frame_bytes)
        pcm = pcm[:usable]

        finished = threading.Event()

        def producer():
            idx = 0
            required = yield b""  # prime
            while idx < len(pcm):
                want = required * frame_bytes
                chunk = pcm[idx:idx + want]
                idx += want
                if len(chunk) < want:
                    chunk = chunk + b"\x00" * (want - len(chunk))
                required = yield chunk
            finished.set()
            while True:  # feed silence until the device is closed
                required = yield b"\x00" * (required * frame_bytes)

        device = ma.PlaybackDevice(
            output_format=sample_format, nchannels=channels, sample_rate=sample_rate,
            buffersize_msec=self.buffersize_msec, device_id=self.device_id)
        gen = producer()
        next(gen)  # advance to the first yield
        self._device = device
        try:
            device.start(gen)
            finished.wait()
            # let the last buffered frames drain before closing
            time.sleep(self.buffersize_msec / 1000 + 0.05)
        finally:
            device.close()
            self._device = None

    def get_supported_formats(self) -> List[str]:
        """Formats miniaudio can decode for play_file."""
        if not self._available:
            return []
        return ['wav', 'flac', 'mp3', 'ogg', 'vorbis']

    async def set_volume(self, volume: float) -> None:
        """Set playback volume"""
        if not 0.0 <= volume <= 1.0:
            raise ValueError("Volume must be between 0.0 and 1.0")
        self._volume = volume
        logger.debug(f"Audio volume set to: {volume}")

    async def stop_playback(self) -> None:
        """Stop current audio playback"""
        if self._device is not None:
            try:
                self._device.stop()
            except Exception as e:
                logger.warning(f"Error stopping playback: {e}")

    def get_provider_name(self) -> str:
        """Get unique provider identifier"""
        return "miniaudio"

    def get_capabilities(self) -> Dict[str, Any]:
        """Return provider capabilities information"""
        return {
            "formats": self.get_supported_formats(),
            "features": [
                "self_contained",
                "streaming",
                "cross_platform",
                "no_system_deps"
            ] if self._available else ["unavailable"],
            "concurrent_playback": False,
            "devices": True,
            "quality": "high",
            "speed": "fast"
        }

    def get_volume(self) -> float:
        """Get current playback volume"""
        return self._volume

    def is_playing(self) -> bool:
        """Check if audio is currently playing"""
        return self._device is not None

    async def validate_parameters(self, **kwargs) -> bool:
        """Validate provider-specific parameters"""
        try:
            if "volume" in kwargs:
                volume = kwargs["volume"]
                if not isinstance(volume, (int, float)) or not 0.0 <= volume <= 1.0:
                    return False
            return True
        except (ValueError, TypeError):
            return False

    async def configure(self, config: Dict[str, Any]) -> None:
        """Update provider configuration at runtime"""
        self.config.update(config)

        if "sample_rate" in config:
            self.sample_rate = config["sample_rate"]
        if "channels" in config:
            self.channels = config["channels"]
        if "buffersize_msec" in config:
            self.buffersize_msec = config["buffersize_msec"]
        if "device" in config:
            self.device_id = config["device"]
        if "volume" in config:
            self._volume = config["volume"]

        logger.debug(f"Miniaudio audio provider configuration updated: {config}")
