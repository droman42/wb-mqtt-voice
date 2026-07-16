"""
Voice Runner - the standalone-microphone, full voice-assistant pipeline.

A thin, fully **configuration-driven** runner: it forces microphone-only input and ensures the
voice stack is on, then delegates to the standard component system. The ASR engine is whatever the
config selects (`[asr] default_provider` — vosk / whisper / sherpa_onnx / …); the runner has no
hardcoded model. Wake word and VAD are honoured from config too. End to end it is:

    Microphone → [VAD] → [Voice Trigger, if configured] → ASR → Text → NLU → Intent → Response (TTS)

It also speaks deferred fire-and-forget results (a voice-set timer) back on the device.
Now using BaseRunner for unified patterns.
"""

import asyncio
import argparse
import logging
import sys
from typing import Optional, List

from ..config.models import CoreConfig
from ..core.session_manager import SessionManager
from .base import BaseRunner, RunnerConfig
from .web_server import WebServerMixin


logger = logging.getLogger(__name__)


def check_voice_dependencies() -> bool:
    """Check the runner's own hard dependency: microphone capture (sounddevice).

    The ASR engine's dependencies are the configured provider's concern — validate those with
    `irene-dependency-validate` — so this runner stays model-agnostic.
    """
    try:
        import sounddevice as sd  # type: ignore  # noqa: F401  # availability probe
        print("✅ Microphone capture available (sounddevice)")
        return True
    except (ImportError, OSError) as e:
        # ImportError = package missing; OSError = package present but the PortAudio native
        # library is absent. A dependency probe must report unavailable, never crash.
        print(f"❌ Microphone capture unavailable: {e}")
        print("💡 Install with: uv add locveil-voice[audio-input]")
        return False


def list_audio_devices():
    """List available audio input devices (legacy function for CLI)"""
    from ..utils.audio_devices import print_audio_devices, is_audio_available
    
    if not is_audio_available():
        print("❌ Sounddevice not available - install audio-input dependencies")
        return
    
    print_audio_devices()


class VoiceRunner(WebServerMixin, BaseRunner):
    """
    Voice Runner - the full voice-assistant pipeline from a local microphone, **plus the web API**.

    Microphone is the primary input; the FastAPI server (WebServerMixin) runs alongside it so the
    standalone also exposes REST/WS (config-ui, control, the reply channel). Everything else is
    **config-driven**: the ASR engine is `[asr] default_provider` (no hardcoded model), wake word runs
    if `voice_trigger` is configured, and VAD segments the stream.
    """

    def __init__(self):
        runner_config = RunnerConfig(
            name="Voice",
            description="Voice assistant mode — microphone input + web API, config-driven ASR",
            requires_config_file=True,
            supports_interactive=False,
            required_dependencies=["sounddevice"]
        )
        super().__init__(runner_config)
        self._init_web_server_state()
        # The mic pipeline runs as a background task (CR-A1) — tracked so it can be cancelled on shutdown
        # and so a crash inside it is surfaced rather than swallowed by the orphaned task.
        self._mic_task: Optional[asyncio.Task] = None

    def _add_runner_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Voice utility option + the shared web-server args (the standalone serves web too)."""
        parser.add_argument(
            "--list-devices",
            action="store_true",
            help="List available audio devices and exit"
        )
        self._add_web_server_arguments(parser)
    
    def _get_usage_examples(self) -> str:
        """Get usage examples for the voice runner"""
        return """
Examples:
  %(prog)s                           # Microphone pipeline + web API (host/port from config or 6000)
  %(prog)s --config my-config.toml   # Use a specific configuration file
  %(prog)s --host 0.0.0.0 --port 6000 # Bind the web API explicitly
  %(prog)s --list-devices            # List available audio devices

Note: microphone is the primary input; the web API (REST/WS) runs alongside it. The ASR engine is
whatever [asr] default_provider selects — there is no hardcoded model.
        """

    async def _check_dependencies(self, args: argparse.Namespace) -> bool:
        """Check the runner's hard dependency (microphone capture). ASR-provider deps are the
        component system's concern, so this stays model-agnostic."""
        if args.check_deps:
            return check_voice_dependencies()

        try:
            import sounddevice as sd  # type: ignore  # noqa: F401  # availability probe
            return True
        except (ImportError, OSError):
            # package missing OR PortAudio native lib absent — degrade, don't crash.
            if not args.quiet:
                print("❌ Microphone capture unavailable (sounddevice)")
                print("💡 Install with: uv add locveil-voice[audio-input]")
            return False
    
    async def _handle_runner_utility_options(self, args: argparse.Namespace) -> Optional[int]:
        """Handle VOSK-specific utility options"""
        if args.list_devices:
            list_audio_devices()
            return 0
        return None
    
    async def _modify_config_for_runner(self, config: CoreConfig, args: argparse.Namespace) -> CoreConfig:
        """Force microphone input + ensure the voice stack is on, and ALSO enable the web API so the
        standalone serves REST/WS alongside the mic (model-agnostic)."""
        # Microphone is the primary input; web is enabled too (the server runs alongside).
        config.inputs.microphone = True
        config.inputs.web = True
        config.inputs.cli = False
        config.inputs.default_input = "microphone"

        # Enable microphone system capability + the web API service
        config.system.microphone_enabled = True
        config.system.web_api_enabled = True
        self._resolve_web_port(config, args)

        # `[components]` and `[vad]` belong to the config file (BUG-35). The mic pipeline
        # structurally needs several of them, so `_validate_runner_specific_config` refuses to start
        # when they are off — a loud error naming the key, instead of silently flipping the
        # operator's config and making `[components]` a lie. (voice_trigger stays config-driven: the
        # runner auto-skips the wake word when it's absent — see _start_voice_audio_workflow.)
        return config

    async def _validate_runner_specific_config(self, config: CoreConfig, args: argparse.Namespace) -> List[str]:
        """Validate the config is coherent for a microphone voice pipeline — provider-agnostic."""
        errors = []

        # The components the mic pipeline structurally needs. These checks are real now: they used to
        # run *after* _modify_config_for_runner had forced every one of them on (BUG-35).
        if not config.components.asr:
            errors.append("ASR component must be enabled (components.asr = true)")
        if not config.components.intent_system:
            errors.append("Intent system component must be enabled (components.intent_system = true)")
        if not config.components.nlu:
            errors.append("NLU component must be enabled (components.nlu = true)")
        if not config.components.text_processor:
            errors.append("Text processor component must be enabled (components.text_processor = true)")
        if not config.components.audio:
            errors.append("Audio component must be enabled (components.audio = true) — this runner speaks locally")
        # The streaming mic workflow raises deep in init without VAD; fail here, naming the key.
        if not config.vad.enabled:
            errors.append("VAD must be enabled (vad.enabled = true) for the microphone pipeline")

        provider = config.asr.default_provider
        if not provider:
            errors.append("An ASR provider must be selected (asr.default_provider = \"<provider>\")")
        else:
            provider_cfg = config.asr.providers.get(provider, {})
            if not provider_cfg:
                available = ", ".join(config.asr.providers.keys()) or "none"
                errors.append(f"ASR provider '{provider}' has no [asr.providers.{provider}] config "
                              f"(available: {available})")
            elif not provider_cfg.get("enabled", False):
                errors.append(f"ASR provider '{provider}' must be enabled "
                              f"(asr.providers.{provider}.enabled = true)")

        # Microphone input + capability
        if not config.inputs.microphone:
            errors.append("Microphone input must be enabled (inputs.microphone = true)")
        if not config.inputs.microphone_config.enabled:
            errors.append("Microphone input config must be enabled (inputs.microphone_config.enabled = true)")
        if not config.system.microphone_enabled:
            errors.append("System microphone capability must be enabled (system.microphone_enabled = true)")

        return errors
    
    def _get_configuration_example(self) -> Optional[str]:
        """Get example configuration for the voice runner (provider shown is an example)."""
        return """
[components]
asr = true

[system]
microphone_enabled = true

[inputs]
microphone = true

[vad]
enabled = true                 # required by the microphone pipeline

[asr]
enabled = true
default_provider = "vosk"      # or whisper / sherpa_onnx / … — the runner is model-agnostic

[asr.providers.vosk]           # …match this table to your chosen default_provider
enabled = true
default_language = "ru"
preload_models = true

# Note: the voice runner always uses microphone input only.
# Other input configurations will be overridden."""
    
    async def _post_core_setup(self, args: argparse.Namespace) -> None:
        """Voice-runner setup after core is started"""
        # Ensure microphone input is started (guaranteed activation)
        if self.core and self.core.input_manager:
            # Check if microphone source exists and start it if not already active
            if "microphone" in self.core.input_manager._sources:
                if "microphone" not in self.core.input_manager._active_sources:
                    success = await self.core.input_manager.start_source("microphone")
                    if success:
                        logger.info("✅ Explicitly started microphone input")
                    else:
                        logger.warning("⚠️ Failed to start microphone input - check hardware/permissions")
                else:
                    logger.info("✅ Microphone input already active")
            else:
                logger.error("❌ Microphone input source not available - check configuration and hardware")

        # Start the audio workflow (with intelligent wake-word handling) in the BACKGROUND.
        # CR-A1: this MUST NOT be awaited — _start_voice_audio_workflow runs an infinite loop over the
        # live mic, so awaiting it here blocks _post_core_setup forever and the web server below never
        # starts. Run it as a tracked task; the done-callback surfaces a crash the task would otherwise hide.
        self._mic_task = asyncio.create_task(self._start_voice_audio_workflow())
        self._mic_task.add_done_callback(self._on_mic_task_done)

        # Build the web API alongside the mic pipeline (degrade to mic-only if fastapi/uvicorn absent).
        try:
            await self._setup_web_server(args)
        except Exception as e:
            logger.warning(f"⚠️ Web API unavailable, running microphone-only: {e}")
            self.app = None

        if not args.quiet:
            asr_provider = getattr(getattr(self.core, "config", None), "asr", None)
            provider_name = getattr(asr_provider, "default_provider", "?") if asr_provider else "?"
            web = f" + web API on {args.host}:{args.port}" if self.app else ""
            print(f"🎤 Voice assistant active (microphone, ASR = {provider_name}){web}")
            print(f"   Microphone → VAD → [wake word] → ASR → Intent processing")
            print("   Press Ctrl+C to stop")
            print("=" * 60)

    async def _start_voice_audio_workflow(self) -> None:
        """
        Start the audio workflow with intelligent wake word handling.

        Audio gets stuck in wake-word detection when the voice_trigger component is disabled, so
        this sets skip_wake_word=True when voice_trigger is not available, letting audio flow
        directly to ASR. When voice_trigger IS configured, the wake word runs ahead of ASR.
        """
        if not self.core or not self.core.workflow_manager:
            logger.error("❌ Core or workflow manager not available for VOSK audio processing")
            return

        # ARCH-15 PR-8: register the local SPEECH output on the shared OutputManager and designate it
        # the conversational fallback, so deferred fire-and-forget results (a voice-set timer firing)
        # speak on this device — the source label ("voice"/"audio_stream") can't be a stable origin key.
        output_manager = getattr(self.core, "output_manager", None)
        if output_manager is not None and self.core.component_manager is not None:
            from ..outputs.audio import AudioSpeechOutput
            # ARCH-21: deferred F&F speech uses the same file|stream path as sync replies
            playback_mode = getattr(getattr(self.core.config, "audio", None), "playback_mode", "file")
            speech = AudioSpeechOutput(self.core.component_manager.get_component('tts'),
                                       self.core.component_manager.get_component('audio'), name="audio",
                                       playback_mode=playback_mode)
            if await speech.is_available():
                await output_manager.add_output("audio", speech)
                output_manager.designate_conversational_fallback("audio")
                logger.info("✅ Registered local audio/voice SPEECH output (conversational fallback)")
            else:
                logger.info("⏭️ Local audio/voice SPEECH output unavailable (no TTS/audio component)")

        # Check if voice_trigger component is available and enabled
        voice_trigger_available = False
        if self.core.component_manager:
            voice_trigger_component = self.core.component_manager.get_component('voice_trigger')
            voice_trigger_available = voice_trigger_component is not None
            
        # CRITICAL FIX: Automatically skip wake word detection if voice_trigger is disabled
        # This prevents the audio processing from getting stuck in the wake word waiting loop
        skip_wake_word = not voice_trigger_available
        
        logger.info(f"🔧 Voice audio workflow configuration:")
        logger.info(f"   Voice trigger available: {voice_trigger_available}")
        logger.info(f"   Skip wake word detection: {skip_wake_word}")
        logger.info(f"   Audio flow: Microphone → {'Direct ASR' if skip_wake_word else 'Voice Trigger → ASR'}")

        try:
            # Get microphone input source
            mic_input = self.core.input_manager._sources.get("microphone")
            if not mic_input:
                logger.error("❌ Microphone input source not found for the voice workflow")
                return
            
            # Get audio stream from microphone input
            audio_stream = self.core.workflow_manager._get_audio_stream(mic_input)
            
            # Start audio processing through workflow manager with intelligent skip_wake_word setting
            async for result in self.core.workflow_manager.process_audio_stream(
                audio_stream=audio_stream,
                session_id=SessionManager.generate_session_id("voice"),
                skip_wake_word=skip_wake_word,  # Key fix: bypass wake word when voice_trigger disabled
                wants_audio=True,
                client_context={"source": "voice_runner", "runner": "voice"}
            ):
                # Process results as they come in
                if result.text and result.text.strip():
                    logger.info(f"✅ Recognized: '{result.text}'")
                    if result.action_metadata:
                        logger.debug(f"📋 Action metadata: {result.action_metadata}")
                
        except Exception as e:
            logger.error(f"❌ Failed to start the voice audio workflow: {e}")
            raise

    def _on_mic_task_done(self, task: "asyncio.Task") -> None:
        """Surface a crash in the background mic workflow (CR-A1) — an unawaited task would otherwise
        swallow the exception silently and the web server would keep running with a dead mic."""
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.error(f"❌ Microphone workflow stopped unexpectedly: {exc}", exc_info=exc)

    async def _cancel_mic_task(self) -> None:
        """Cancel the background mic workflow on shutdown and wait for it to unwind."""
        task = self._mic_task
        if task is None or task.done():
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def _execute_runner_logic(self, args: argparse.Namespace) -> int:
        """Run the web server (blocks, keeping the process alive) while the mic workflow — already
        started in _post_core_setup — runs in the background on the same loop. With no web server
        (deps absent), fall back to an idle loop driven purely by the mic pipeline."""
        try:
            if self.app:
                return await self._start_server(args)
            while self.core and self.core.is_running:
                await asyncio.sleep(1.0)
            return 0
        except KeyboardInterrupt:
            if not args.quiet:
                print("\n\n🛑 Voice assistant stopped")
            return 0
        finally:
            await self._cancel_mic_task()


def run_voice() -> int:
    """Entry point for the voice runner"""
    try:
        runner = VoiceRunner()
        return asyncio.run(runner.run())
    except KeyboardInterrupt:
        print("\n👋 Voice runner stopped")
        return 0


if __name__ == "__main__":
    sys.exit(run_voice())
