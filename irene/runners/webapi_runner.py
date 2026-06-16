"""
Web API Runner - FastAPI server for Irene (web input only).

The FastAPI/uvicorn machinery lives in WebServerMixin (shared with voice_runner). This runner adds the
web-only input policy on top.
"""

import asyncio
import argparse
import logging
import sys
from typing import Optional, List

from ..config.models import CoreConfig
from .base import BaseRunner, RunnerConfig
from .web_server import WebServerMixin


logger = logging.getLogger(__name__)


def check_webapi_dependencies() -> bool:
    """Check if Web API dependencies are available"""
    try:
        import fastapi  # type: ignore  # noqa: F401  # availability probe
        import uvicorn  # type: ignore  # noqa: F401  # availability probe
        logger.info("✅ Web API dependencies available")
        return True
    except ImportError as e:
        logger.error(f"❌ Web API dependencies missing: {e}")
        print("💡 Install with: uv add irene-voice-assistant[web-api]")
        return False


class WebAPIRunner(WebServerMixin, BaseRunner):
    """
    Web API Server Runner — ALWAYS uses web input only, regardless of config file settings.
    The FastAPI server itself comes from WebServerMixin.
    """

    def __init__(self):
        runner_config = RunnerConfig(
            name="WebAPI",
            description="Web API Server Mode (web input only)",
            requires_config_file=False,
            supports_interactive=False,
            required_dependencies=["fastapi", "uvicorn"]
        )
        super().__init__(runner_config)
        self._init_web_server_state()

    def _add_runner_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add the shared web-server args."""
        self._add_web_server_arguments(parser)

    def _get_usage_examples(self) -> str:
        return """
Examples:
  %(prog)s                           # Start on default host:port (from config or 6000)
  %(prog)s --host 0.0.0.0 --port 6000 # Custom host and port (overrides config)
  %(prog)s --ssl-cert cert.pem       # Enable HTTPS

Note: WebAPI runner always uses web input only, regardless of config file settings.
Port priority: command line > config file > 6000
        """

    async def _check_dependencies(self, args: argparse.Namespace) -> bool:
        if args.check_deps:
            return check_webapi_dependencies()
        try:
            import fastapi  # type: ignore  # noqa: F401  # availability probe
            import uvicorn  # type: ignore  # noqa: F401  # availability probe
            return True
        except ImportError:
            if not args.quiet:
                print("❌ Web API dependencies missing")
                print("💡 Install with: uv add irene-voice-assistant[web-api]")
            return False

    async def _modify_config_for_runner(self, config: CoreConfig, args: argparse.Namespace) -> CoreConfig:
        """Force web-only input + resolve the port."""
        config.system.web_api_enabled = True
        self._resolve_web_port(config, args)

        # WebAPI runner ALWAYS forces web-only input (overrides the config file)
        config.inputs.microphone = False
        config.inputs.web = True
        config.inputs.cli = False
        config.inputs.default_input = "web"
        config.system.microphone_enabled = False

        config.components.tts = args.enable_tts
        config.components.audio = args.enable_tts
        config.components.intent_system = True
        config.components.asr = True
        config.components.voice_trigger = False
        config.components.text_processor = True
        config.components.nlu = True
        config.components.monitoring = True
        config.debug = args.debug
        return config

    async def _validate_runner_specific_config(self, config: CoreConfig, args: argparse.Namespace) -> List[str]:
        errors = []
        if not config.system.web_api_enabled:
            errors.append("Web API service must be enabled (system.web_api_enabled = true)")
        if not config.inputs.web:
            errors.append("Web input source must be enabled (inputs.web = true)")
        if not config.components.intent_system:
            errors.append("Intent system component must be enabled (components.intent_system = true)")
        return errors

    def _get_configuration_example(self) -> Optional[str]:
        return """
[system]
web_api_enabled = true
web_port = 6000

[inputs]
web = true

[components]
intent_system = true
text_processor = true
nlu = true
tts = true
audio = true
asr = true
monitoring = true
"""

    async def _post_core_setup(self, args: argparse.Namespace) -> None:
        """Build the FastAPI app (asset loader + web input + routers)."""
        await self._setup_web_server(args)

    async def _execute_runner_logic(self, args: argparse.Namespace) -> int:
        return await self._start_server(args)


def run_webapi() -> int:
    """Entry point for Web API runner"""
    try:
        runner = WebAPIRunner()
        return asyncio.run(runner.run())
    except KeyboardInterrupt:
        return 0
    except Exception as e:
        logger.error(f"Failed to start Web API runner: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(run_webapi())
