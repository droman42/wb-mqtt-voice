"""QUAL-20 — microVAD engine (pymicro-vad) as a third VADEngine (real runtime smoke).

Skips cleanly if the optional `pymicro-vad` extra (vad-tflite) isn't installed.
"""
import pytest

pytest.importorskip("pymicro_vad")

from locveil_voice.utils.vad import VADEngine, VADResult
from locveil_voice.utils.vad_microvad import MicroVADEngine
from locveil_voice.utils.audio_data import AudioData


class _Cfg:
    microvad_threshold = 0.5


def _frame(pcm: bytes) -> AudioData:
    return AudioData(data=pcm, timestamp=0.0, sample_rate=16000, channels=1)


def test_is_a_vad_engine():
    assert issubclass(MicroVADEngine, VADEngine)


def test_silence_is_not_voice():
    eng = MicroVADEngine(_Cfg())
    # 200 ms of digital silence, fed as 20 ms frames (640 bytes)
    silence = b"\x00\x00" * 320
    voiced = False
    for _ in range(10):
        res = eng.process_frame(_frame(silence))
        assert isinstance(res, VADResult)
        voiced = voiced or res.is_voice
    assert voiced is False


def test_reset_clears_buffer():
    eng = MicroVADEngine(_Cfg())
    eng.process_frame(_frame(b"\x00" * 100))   # sub-chunk remainder buffered
    eng.reset()
    assert len(eng._buffer) == 0
