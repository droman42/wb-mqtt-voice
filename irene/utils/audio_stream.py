"""Raw-PCM streaming helpers (ARCH-20).

Foundation-layer utilities for the streamable audio-output path: drain an async PCM
stream into a buffer (the "buffer-then-stream" bridge), parse a WAV container down to
raw PCM + format, and map a sample width to an ALSA format token. PCM-only
(`audio_pipeline.md` §8 D-12). No upward dependencies (ARCH-12).
"""

import io
import wave
from typing import AsyncIterator, Iterator, Tuple


async def collect_pcm(stream: AsyncIterator[bytes]) -> bytes:
    """Drain an async byte stream into a single buffer.

    The buffer-then-stream bridge: a backend with a pull-based (sync) device API plays
    the whole utterance in one streamed pass rather than interleaving with the async
    producer. True incremental streaming (for a future streaming sink) can consume the
    iterator directly instead.
    """
    chunks = []
    async for chunk in stream:
        chunks.append(chunk)
    return b"".join(chunks)


def iter_frames(pcm: bytes, frame_bytes: int) -> Iterator[bytes]:
    """Yield ``pcm`` in ``frame_bytes``-sized blocks (the last block may be short)."""
    if frame_bytes <= 0:
        raise ValueError("frame_bytes must be positive")
    for i in range(0, len(pcm), frame_bytes):
        yield pcm[i:i + frame_bytes]


def is_wav(data: bytes) -> bool:
    """True if ``data`` opens with a RIFF/WAVE container header."""
    return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE"


def parse_wav(data: bytes) -> Tuple[bytes, int, int, int]:
    """Parse WAV-container bytes into ``(pcm, sample_rate, channels, sample_width)``.

    Raises ``wave.Error`` / ``EOFError`` on malformed input.
    """
    with wave.open(io.BytesIO(data), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        pcm = wav.readframes(wav.getnframes())
    return pcm, sample_rate, channels, sample_width


def width_to_alsa_format(sample_width: int) -> str:
    """Map a PCM sample width (bytes) to an ``aplay -f`` format token."""
    return {1: "U8", 2: "S16_LE", 3: "S24_3LE", 4: "S32_LE"}.get(sample_width, "S16_LE")
