"""ARCH-21 PR-5: reply-to-device remote audio output + origin routing."""

import pytest

from locveil_voice.core.interfaces.output import OutputModality
from locveil_voice.intents.context_models import RequestContext
from locveil_voice.intents.models import AudioData, IntentResult
from locveil_voice.outputs.remote_audio import RemoteAudioOutput
from locveil_voice.utils.audio_negotiation import AudioContract
from locveil_voice.utils.audio_stream import PCMStream


class _FakeChannel:
    def __init__(self, contract, connected=True):
        self._contract = contract
        self._connected = connected
        self.sent = []

    @property
    def contract(self):
        return self._contract

    def is_connected(self):
        return self._connected

    async def send_audio(self, pcm, *, sample_rate, channels, sample_width):
        self.sent.append((pcm, sample_rate, channels, sample_width))


class _FakeTTS:
    def __init__(self, pcm, rate, channels):
        self._pcm, self._rate, self._channels = pcm, rate, channels

    async def synthesize_to_stream(self, text, **kwargs):
        async def _frames():
            yield self._pcm

        return PCMStream(sample_rate=self._rate, channels=self._channels, sample_width=2, frames=_frames())


class _PassThroughNegotiator:
    async def to_sink(self, audio_data, sink=None, trace_context=None):
        return audio_data


def _contract(rate=16000, channels=1):
    return AudioContract([rate], rate, ["pcm16"], "pcm16", channels)


def _result(text="привет"):
    return IntentResult(text=text, should_speak=True)


@pytest.mark.asyncio
async def test_remote_output_pushes_conformed_pcm_to_channel():
    pcm = b"\x01\x00\x02\x00" * 50
    channel = _FakeChannel(_contract(16000, 1))
    out = RemoteAudioOutput("kitchen_node", channel, _FakeTTS(pcm, 16000, 1), _PassThroughNegotiator())

    res = await out.deliver(_result(), RequestContext(session_id="s", client_id="kitchen_node"),
                            OutputModality.SPEECH)

    assert res.delivered is True
    assert channel.sent == [(pcm, 16000, 1, 2)]
    assert out.origin_key() == "kitchen_node"


@pytest.mark.asyncio
async def test_remote_output_drops_when_channel_offline():
    channel = _FakeChannel(_contract(), connected=False)
    out = RemoteAudioOutput("node", channel, _FakeTTS(b"\x00\x00", 16000, 1), _PassThroughNegotiator())

    res = await out.deliver(_result(), RequestContext(session_id="s", client_id="node"),
                            OutputModality.SPEECH)

    assert res.delivered is False
    assert channel.sent == []


@pytest.mark.asyncio
async def test_origin_routing_delivers_only_to_the_source_device():
    """A result from device A routes through OutputManager to A's reply channel, not B's."""
    from locveil_voice.outputs.manager import OutputManager

    chan_a = _FakeChannel(_contract())
    chan_b = _FakeChannel(_contract())
    out_a = RemoteAudioOutput("device_a", chan_a, _FakeTTS(b"\xaa\xaa" * 10, 16000, 1), _PassThroughNegotiator())
    out_b = RemoteAudioOutput("device_b", chan_b, _FakeTTS(b"\xbb\xbb" * 10, 16000, 1), _PassThroughNegotiator())

    manager = OutputManager()
    await manager.add_output("device_a", out_a)
    await manager.add_output("device_b", out_b)

    context = RequestContext(session_id="s", client_id="device_a")
    targets = manager.select(OutputModality.SPEECH, context)

    assert targets == [out_a]
    await targets[0].deliver(_result(), context, OutputModality.SPEECH)
    assert len(chan_a.sent) == 1
    assert chan_b.sent == []
