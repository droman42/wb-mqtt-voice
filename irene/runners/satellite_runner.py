"""
Satellite Runner — a room node without firmware (ARCH-36, design `docs/design/python_satellite.md`).

The full satellite-side pipeline on any Python-capable box (a laptop for testing, a Pi + mic as
a real room node), speaking the same wire contract the ESP32 firmware will implement:

    Microphone → AudioNegotiator (canonical) → VAD segmenter → [wake gate «Ирина»]
        → /ws/audio uplink (single | streaming)          — the controller owns understanding
    Reply: /ws/audio/reply → local audio playback (speak_begin/PCM/speak_end)

Everything below the link is existing machinery (mic input, VAD, voice trigger, audio
component); the controller does ASR/NLU/intents. `single` mode is ESP32-faithful (device-side
endpointing, wake word → then the command as its own utterance); `streaming` mode pumps the
live stream continuously for server-authoritative endpointing (ARCH-10) — VAD/wake are
bypassed there, matching the always-on device model.

TLS (design §5): with `[satellite.tls]` enabled the runner provisions itself on first run
(EC keypair → CSR to the `:80` bootstrap zone → poll while the operator approves) and connects
over mTLS `wss://` through the nginx `/ws/` proxy.
"""

import argparse
import asyncio
import logging
import sys
import time
from typing import Any, List, Optional

from ..config.models import CoreConfig
from .base import BaseRunner, RunnerConfig

logger = logging.getLogger(__name__)

# The wake gate arms a capture window: segments that START inside it are sent as the command
# (the wake word's own segment started before the gate opened, so it is naturally skipped —
# say «Ирина», pause, then the command: the ESP32 two-phrase pattern).
WAKE_ARM_WINDOW_S = 8.0


def _in_armed_window(armed_at: Optional[float], segment_start: float) -> bool:
    """The wake-gate rule: a segment passes only if it STARTED inside the armed window."""
    return armed_at is not None and armed_at <= segment_start <= armed_at + WAKE_ARM_WINDOW_S


class SatelliteRunner(BaseRunner):
    """Room-node mode: local mic/VAD/wake word, understanding on the controller."""

    def __init__(self):
        super().__init__(RunnerConfig(
            name="Satellite",
            description="Satellite room node — mic + VAD + wake word here, understanding on the controller",
            requires_config_file=True,
            supports_interactive=False,
            required_dependencies=["sounddevice"],
        ))
        self._reply_task: Optional[asyncio.Task] = None

    # --- BaseRunner contract -----------------------------------------------------------------------

    def _add_runner_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--server", help="Controller WebSocket base (overrides [satellite] server_url), e.g. ws://wb7:8080")
        parser.add_argument("--room", help="Room name to register (overrides [satellite] room_name)")
        parser.add_argument("--client-id", help="Client identity to register (overrides [satellite] client_id)")
        parser.add_argument("--mode", choices=["single", "streaming"], help="Uplink mode (overrides [satellite] mode)")
        parser.add_argument("--no-wake", action="store_true",
                            help="Bypass the wake-word gate: every VAD utterance is streamed (rapid testing)")

    def _get_usage_examples(self) -> str:
        return """
Examples:
  %(prog)s -c configs/satellite.toml                       # room node per config
  %(prog)s -c configs/satellite.toml --no-wake             # stream every utterance (testing)
  %(prog)s -c configs/satellite.toml --server ws://wb7:8080 --room "Кухня"
  %(prog)s -c configs/satellite.toml --mode streaming      # server-authoritative endpointing

Note: this box only listens and speaks — ASR/NLU/intents run on the controller. With
[satellite.tls] enabled the first run provisions a client certificate (the operator approves
with `esp32-provision approve <client_id>` on the controller) and connects over mTLS wss://.
        """

    async def _check_dependencies(self, args: argparse.Namespace) -> bool:
        try:
            import sounddevice  # type: ignore  # noqa: F401  # availability probe
            if args.check_deps:
                print("✅ Microphone capture available (sounddevice)")
            return True
        except (ImportError, OSError) as e:
            print(f"❌ Microphone capture unavailable: {e}")
            print("💡 Install with: uv add irene-voice-assistant[audio-input]")
            return False

    async def _modify_config_for_runner(self, config: CoreConfig, args: argparse.Namespace) -> CoreConfig:
        """Force the satellite shape: mic + VAD (+ wake + playback) on, understanding OFF —
        the controller owns it (design §2). CLI flags override individual [satellite] fields."""
        if args.server:
            config.satellite.server_url = args.server
        if args.room:
            config.satellite.room_name = args.room
        if args.client_id:
            config.satellite.client_id = args.client_id
        if args.mode:
            config.satellite.mode = args.mode
        if args.no_wake:
            config.satellite.wake_word_required = False

        config.inputs.microphone = True
        config.inputs.web = False
        config.inputs.cli = False
        config.inputs.default_input = "microphone"
        config.system.microphone_enabled = True
        config.system.web_api_enabled = False
        config.vad.enabled = True

        config.components.audio = True  # reply-channel playback
        config.components.voice_trigger = config.satellite.wake_word_required
        config.voice_trigger.enabled = config.satellite.wake_word_required
        # The controller owns understanding — never load these here.
        config.components.asr = False
        config.components.nlu = False
        config.components.llm = False
        config.components.tts = False
        config.components.intent_system = False
        config.components.text_processor = False
        config.asr.enabled = False
        return config

    async def _validate_runner_specific_config(self, config: CoreConfig, args: argparse.Namespace) -> List[str]:
        errors = []
        sat = config.satellite
        if not sat.enabled:
            errors.append("Satellite mode must be enabled ([satellite] enabled = true — "
                          "see configs/satellite.toml)")
        if not sat.server_url:
            errors.append("A controller must be configured ([satellite] server_url or --server)")
        if sat.tls.enabled and sat.server_url.startswith("ws://"):
            errors.append("[satellite.tls] is enabled but server_url is plain ws:// — use wss://<host>")
        if not sat.tls.enabled and sat.server_url.startswith("wss://"):
            errors.append("server_url is wss:// but [satellite.tls] is disabled — enable it "
                          "(mTLS is required by the nginx /ws/ proxy)")
        if not config.inputs.microphone_config.enabled:
            errors.append("Microphone input config must be enabled (inputs.microphone_config.enabled = true)")
        return errors

    def _get_configuration_example(self) -> Optional[str]:
        return """
[satellite]
enabled = true
server_url = "ws://wb7:8080"
client_id = "kitchen_satellite"
room_name = "Кухня"

# See configs/satellite.toml for the full curated profile
# (mic + vad + voice_trigger + audio on; asr/nlu/tts/intents off)."""

    # --- pipeline ------------------------------------------------------------------------------------

    async def _execute_runner_logic(self, args: argparse.Namespace) -> int:
        assert self.core is not None
        config: CoreConfig = self.core.config
        sat = config.satellite

        ssl_context = None
        if sat.tls.enabled:
            from ..satellite.provisioning import build_ssl_context, ensure_credentials
            ca, crt, key = await ensure_credentials(sat.tls, config.assets.assets_root,
                                                    sat.client_id)
            ssl_context = build_ssl_context(ca, crt, key)

        # Mic source (started by the input manager, the voice-runner pattern)
        input_manager = self.core.input_manager
        if input_manager is None or "microphone" not in input_manager._sources:
            logger.error("Microphone input source not available — check configuration and hardware")
            return 1
        if "microphone" not in input_manager._active_sources:
            if not await input_manager.start_source("microphone"):
                logger.error("Failed to start microphone input — check hardware/permissions")
                return 1
        mic = input_manager._sources["microphone"]

        from ..core.audio_negotiator import AudioNegotiator
        from ..workflows.audio_processor import VoiceSegmenter

        # ARCH-38: --trace on a satellite = the merged end-to-end file (device story + the
        # controller's execution trace via wants_trace). Single mode only (design T-5).
        recorder = None
        tracing = bool(getattr(config.trace, "enabled", False))
        if tracing and sat.mode == "streaming":
            logger.warning("--trace applies to single mode (streaming has no device-side "
                           "story to trace) — continuing without satellite tracing")
            tracing = False
        if tracing:
            from ..satellite.trace import SatelliteTraceRecorder
            recorder = SatelliteTraceRecorder(config.trace, config.assets,
                                              client_id=sat.client_id, room_name=sat.room_name,
                                              mode=sat.mode)

        negotiator = AudioNegotiator.from_pipeline(config)
        segmenter = VoiceSegmenter(config.vad, collect_vad_frames=tracing)
        await segmenter.initialize()

        trigger = None
        if sat.wake_word_required and self.core.component_manager is not None:
            trigger = self.core.component_manager.get_component("voice_trigger")
            if trigger is None:
                logger.error("wake_word_required but the voice_trigger component is unavailable "
                             "— fix [voice_trigger] or run with --no-wake")
                return 1

        from ..satellite.link import SatelliteLink, SatelliteReplyClient
        link = SatelliteLink(sat.server_url, sat.client_id, sat.room_name,
                             sample_rate=negotiator.canonical.rate, mode=sat.mode,
                             wants_trace=tracing, ssl_context=ssl_context)

        reply_client = None
        # Any: get_component returns the ComponentPort base; playback is the audio component's
        # duck-typed surface (play_stream), same access pattern the voice runner uses.
        audio: Any = self.core.component_manager.get_component("audio") if self.core.component_manager else None
        if audio is not None:
            async def _play(pcm: bytes, rate: int, channels: int) -> None:
                await audio.play_stream(pcm, sample_rate=rate, channels=channels, sample_width=2)
                if recorder is not None:
                    recorder.on_reply(pcm, rate, channels)
            reply_client = SatelliteReplyClient(sat.server_url, sat.client_id, _play,
                                                rate=sat.audio_out_rate,
                                                channels=sat.audio_out_channels,
                                                ssl_context=ssl_context)
            self._reply_task = asyncio.create_task(reply_client.run())
        else:
            logger.warning("Audio component unavailable — replies will not be played locally")

        if not args.quiet:
            gate = "wake word «armed window»" if trigger else "no wake gate (--no-wake)"
            print(f"🛰  Satellite '{sat.client_id}' ({sat.room_name or 'no room'}) → {sat.server_url}")
            print(f"   mode={sat.mode} · {gate} · canonical {negotiator.canonical.rate} Hz")
            if trigger is not None:
                print("   Say the wake word, pause, then the command.")
            print("   Press Ctrl+C to stop")
            print("=" * 60)

        try:
            if sat.mode == "streaming":
                await self._run_streaming(mic, negotiator, link)
            else:
                await self._run_single(mic, negotiator, segmenter, trigger, link, config, recorder)
            return 0
        except KeyboardInterrupt:
            return 0
        finally:
            if recorder is not None:
                recorder.flush()
            if reply_client is not None:
                reply_client.stop()
            if self._reply_task is not None:
                self._reply_task.cancel()
                try:
                    await self._reply_task
                except (asyncio.CancelledError, Exception):
                    pass
            await link.close()

    async def _run_single(self, mic: Any, negotiator: Any, segmenter: Any,
                          trigger: Any, link: Any, config: CoreConfig,
                          recorder: Any = None) -> None:
        """ESP32-faithful mode: VAD endpoints locally; the wake gate arms a capture window;
        each passing utterance is one frames+end cycle awaiting the final response."""
        from ..intents.models import AudioData

        await link.ensure_connected()
        armed_at: Optional[float] = None

        async for raw in mic.listen():
            if not isinstance(raw, AudioData):
                continue
            if recorder is not None:
                recorder.on_raw_chunk(raw)
            canonical = await negotiator.to_canonical(raw)

            if trigger is not None:
                try:
                    wake = await trigger.process_audio(canonical)
                except Exception as e:
                    logger.debug(f"wake detection error (chunk skipped): {e}")
                    wake = None
                if wake is not None and wake.detected:
                    armed_at = time.time()
                    if recorder is not None:
                        recorder.on_wake(confidence=wake.confidence, armed_at=armed_at)
                    logger.info(f"Wake word detected ({wake.confidence:.2f}) — listening for a command")
                    print("🔔 Слушаю…")

            segment = await segmenter.process_audio_chunk(canonical)
            if segment is None or segment.combined_audio is None:
                continue

            if trigger is not None:
                if not _in_armed_window(armed_at, segment.start_timestamp):
                    if recorder is not None:
                        recorder.on_gate_skip(segment_start=segment.start_timestamp,
                                              armed_at=armed_at)
                    continue  # outside the armed window (includes the wake word's own segment)
                armed_at = None  # one command per wake

            if config.vad.normalize_for_asr:
                segment = segment.normalize_for_asr(config.vad.asr_target_rms)
            await self._send_segment(link, segment, recorder)

    async def _send_segment(self, link: Any, segment: Any, recorder: Any = None) -> None:
        pcm = segment.combined_audio.data
        sample_rate = segment.combined_audio.sample_rate
        started = time.time()
        response, error = None, None
        try:
            await link.ensure_connected()
            response = await link.send_utterance(pcm)
        except (ConnectionError, TimeoutError) as e:
            # The ESP32 contract too: a dropped utterance is lost, the connection heals.
            error = str(e)
            logger.warning(f"Utterance not delivered ({e}); reconnecting")
            await link.close()
        if recorder is not None:
            recorder.complete_utterance(segment=segment, pcm=pcm, sample_rate=sample_rate,
                                        response=response, error=error,
                                        rtt_ms=(time.time() - started) * 1000.0,
                                        trace_granted=link.trace_granted,
                                        controller_trace=link.last_trace)
        if response is None:
            return
        text = response.get("text") or ""
        if text:
            print(f"💬 {text}")
        logger.info(f"response: success={response.get('success')} "
                    f"intent={response.get('intent_name')} text='{text[:120]}'")

    async def _run_streaming(self, mic: Any, negotiator: Any, link: Any) -> None:
        """Always-on mode: pump every canonical frame; the server owns endpointing (ARCH-10).
        A reader task prints partials/responses as they arrive."""
        from ..intents.models import AudioData

        await link.ensure_connected()

        async def _reader() -> None:
            while True:
                try:
                    msg = await link.receive()
                except ConnectionError:
                    await asyncio.sleep(0.5)  # the sender loop owns reconnection
                    continue
                kind = msg.get("type")
                if kind == "partial":
                    print(f"… {msg.get('text', '')}", end="\r", flush=True)
                elif kind == "response":
                    text = msg.get("text") or ""
                    print(f"\n💬 {text}" if text else "")

        reader = asyncio.create_task(_reader())
        try:
            async for raw in mic.listen():
                if not isinstance(raw, AudioData):
                    continue
                canonical = await negotiator.to_canonical(raw)
                try:
                    await link.send_frame(canonical.data)
                except ConnectionError:
                    await link.ensure_connected()
        finally:
            reader.cancel()
            try:
                await reader
            except asyncio.CancelledError:
                pass


def run_satellite() -> int:
    """Entry point for the satellite runner"""
    try:
        return asyncio.run(SatelliteRunner().run())
    except KeyboardInterrupt:
        print("\n👋 Satellite stopped")
        return 0


if __name__ == "__main__":
    sys.exit(run_satellite())
