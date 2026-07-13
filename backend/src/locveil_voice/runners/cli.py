"""
CLI Runner - Command line interface for Irene

Enhanced with dependency checking and graceful fallback handling.
Now using BaseRunner for unified patterns.
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Optional, List


from ..config.models import CoreConfig, ComponentConfig
from ..core.session_manager import SessionManager
from ..utils.loader import get_component_status, suggest_installation
from .base import BaseRunner, RunnerConfig, InteractiveRunnerMixin
from .web_server import WebServerMixin




def check_dependencies() -> bool:
    """
    Check and report component dependencies.
    
    Returns:
        True if all requested components are available
    """
    print("🔍 Checking Component Dependencies")
    print("=" * 50)
    
    status = get_component_status()
    all_available = True
    
    for component, info in status.items():
        status_icon = "✅" if info["available"] else "❌"
        print(f"{status_icon} {component.capitalize()}: {'Available' if info['available'] else 'Not Available'}")
        
        if info["available"]:
            print(f"   Dependencies: {', '.join(info['dependencies'])}")
        else:
            all_available = False
            print(f"   Missing: {', '.join(info['missing'])}")
            suggestion = suggest_installation(component)
            if suggestion:
                print(f"   💡 Install with: {suggestion}")
        print()
    
    if all_available:
        print("🎉 All components are available!")
    else:
        print("⚠️  Some components are missing. Irene will run with available components only.")
    
    return all_available


def list_deployment_profiles():
    """List available deployment profiles"""
    print("🚀 Available Deployment Profiles")
    print("=" * 40)
    
    profiles = [
        ("headless", "Text command processing — NLU + intents (no audio/web; requires the 'nlu' extra)"),
        ("api-only", "Web API server (requires fastapi, uvicorn)"),
        ("tts-only", "Text-to-speech output (requires pyttsx3)"),
        ("voice", "Full voice assistant (all components)"),
        ("custom", "Custom configuration via config file")
    ]
    
    for name, description in profiles:
        print(f"📋 {name}")
        print(f"   {description}")
        
        # Check availability
        if name == "headless":
            print("   ✅ Available (requires NLU: spaCy + language model)")
        elif name == "custom":
            print("   ⚙️  Depends on configuration")
        else:
            # Check specific requirements
            status = get_component_status()
            required_components = {
                "api-only": ["web_api"],
                "tts-only": ["tts"],
                "voice": ["microphone", "tts", "web_api"]
            }
            
            if name in required_components:
                missing = []
                for comp in required_components[name]:
                    if not status.get(comp, {}).get("available", False):
                        missing.append(comp)
                
                if missing:
                    print(f"   ❌ Missing: {', '.join(missing)}")
                    for comp in missing:
                        suggestion = suggest_installation(comp)
                        if suggestion:
                            print(f"      Install: {suggestion}")
                else:
                    print("   ✅ Available")
        print()






class CLIRunner(WebServerMixin, BaseRunner, InteractiveRunnerMixin):
    """
    CLI Runner class - Provides command line interface for Irene.

    CLI is the primary input; the web API (WebServerMixin) runs alongside it in the background — ON by
    default, OFF for --headless. So the same instance gives you the terminal REPL **and** REST/WS.
    """

    def __init__(self):
        runner_config = RunnerConfig(
            name="CLI",
            description="Command line interface for Irene (CLI input + web API)",
            # REL-2: a config is required — the built-in default has no NLU providers, so the
            # old silent fall-back always died on the first command with internals-speak.
            requires_config_file=True,
            supports_interactive=True,
            required_dependencies=["core"]
        )
        super().__init__(runner_config)
        self._init_web_server_state()
    
    def _add_runner_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add CLI-specific command line arguments"""
        # Deployment profile shortcuts
        profile_group = parser.add_mutually_exclusive_group()
        profile_group.add_argument(
            "--headless",
            action="store_true",
            help="Run in headless mode (no audio, no web API)"
        )
        profile_group.add_argument(
            "--api-only",
            action="store_true", 
            help="Run as API server only (no audio components)"
        )
        profile_group.add_argument(
            "--voice",
            action="store_true",
            help="Full voice assistant mode (all components if available)"
        )
        
        # Utility options
        parser.add_argument(
            "--list-profiles",
            action="store_true",
            help="List available deployment profiles and exit"
        )
        
        # Command execution options
        parser.add_argument(
            "--command", "-e",
            type=str,
            help="Execute a single command and exit (like legacy runva_cmdline.py)"
        )
        parser.add_argument(
            "--interactive", "-i",
            action="store_true",
            help="Force interactive mode even when --command is specified"
        )
        parser.add_argument(
            "--test-greeting",
            action="store_true",
            help="Test greeting command and exit (legacy compatibility)"
        )
        parser.add_argument(
            "--enable-tts", 
            action="store_true",
            help="Enable TTS audio output for CLI responses (Phase 5 support)"
        )
        
        # Data directory override
        parser.add_argument(
            "--data-dir",
            type=Path,
            help="Override data directory path"
        )

        # Web-server args (the CLI serves the web API alongside the REPL, unless --headless)
        self._add_web_server_arguments(parser)

    def _get_usage_examples(self) -> str:
        """Get usage examples for CLI runner"""
        return """
Examples:
  %(prog)s                           # Start with default config (CLI input only)
  %(prog)s --config config.toml      # Use specific config file (CLI input only)
  %(prog)s --headless                # Run in headless mode
  %(prog)s --api-only                # Run as API server only
  %(prog)s --check-deps              # Check component dependencies
  %(prog)s --voice                   # Full voice assistant mode
  %(prog)s -e "hello"                # Execute single command and exit
  %(prog)s -i                        # Force interactive mode

Note: CLI runner always uses CLI input only, regardless of config file settings.
        """
    
    async def _check_dependencies(self, args: argparse.Namespace) -> bool:
        """Check CLI runner dependencies"""
        if args.check_deps:
            # Full dependency check for utility option
            success = check_dependencies()
            return success
        
        # Basic core dependencies always available for CLI
        return True
    
    async def _handle_runner_utility_options(self, args: argparse.Namespace) -> Optional[int]:
        """Handle CLI-specific utility options"""
        if args.list_profiles:
            list_deployment_profiles()
            return 0
        return None
    
    async def _modify_config_for_runner(self, config: CoreConfig, args: argparse.Namespace) -> CoreConfig:
        """Modify configuration for CLI-specific needs"""
        # Handle deployment profile overrides (V14 Architecture)
        if args.headless:
            # Headless: text-command pipeline, no audio/voice/web.
            # NLU + text_processor are REQUIRED — the UnifiedVoiceAssistantWorkflow cannot
            # turn text into an intent without the NLU component (otherwise workflow creation
            # fails with "Required component 'nlu' not available"). LLM stays off (optional;
            # conversation/translation handlers degrade to console fallback).
            config.components = ComponentConfig(
                tts=False, audio=False, asr=False, voice_trigger=False,
                llm=False, nlu=True, text_processor=True, intent_system=True
            )
            # Also update system capabilities
            config.system.microphone_enabled = False
            config.system.audio_playback_enabled = False
            config.system.web_api_enabled = False
        elif args.api_only:
            # API-only: text processing only, no voice components
            config.components = ComponentConfig(
                tts=False, audio=False, asr=False, voice_trigger=False,
                llm=True, nlu=True, text_processor=True, intent_system=True
            )
            # Update system capabilities  
            config.system.microphone_enabled = False
            config.system.audio_playback_enabled = False
            config.system.web_api_enabled = True
        elif args.voice:
            # Voice: full voice assistant with all components
            config.components = ComponentConfig(
                tts=True, audio=True, asr=True, voice_trigger=True,
                llm=True, nlu=True, text_processor=True, intent_system=True
            )
            # Update system capabilities
            config.system.microphone_enabled = True
            config.system.audio_playback_enabled = True
            config.system.web_api_enabled = True
        
        # CLI is the primary input; the web API runs alongside it — ON by default, OFF for --headless
        # (--api-only / --voice already enabled it above). This overrides the config file's inputs.
        serve_web = not args.headless
        config.inputs.microphone = False
        config.inputs.cli = True
        config.inputs.web = serve_web
        config.inputs.default_input = "cli"
        config.system.web_api_enabled = serve_web
        if serve_web:
            self._resolve_web_port(config, args)
        
        # Apply other command line overrides
        if args.data_dir:
            # V14: Update assets root instead of data_directory
            config.assets.assets_root = Path(args.data_dir)
        
        return config
    
    async def _validate_runner_specific_config(self, config: CoreConfig, args: argparse.Namespace) -> List[str]:
        """Validate CLI-specific configuration requirements"""
        errors = []
        
        # CLI runner is very flexible - only requires intent system for command processing
        if not config.components.intent_system:
            errors.append("Intent system must be enabled for CLI command processing (components.intent_system = true)")
        
        return errors
    
    async def _post_core_setup(self, args: argparse.Namespace) -> None:
        """CLI-specific setup after core is started"""
        # Handle test greeting (legacy compatibility)
        if args.test_greeting:
            args.command = "привет"
            if not args.quiet:
                print("🧪 Testing greeting command (legacy compatibility mode)")

        if not args.quiet and self.core:
            profile = self.core.component_manager.get_deployment_profile()
            print(f"🚀 Irene started successfully in {profile} mode (CLI input only)")
            
            # Show available components
            component_info = self.core.component_manager.get_component_info()
            active_components = [name for name, info in component_info.items() 
                               if info.initialized]
            
            if active_components:
                print(f"📦 Active components: {', '.join(active_components)}")
            else:
                print("📦 Running in minimal mode (no optional components)")

            print("💻 Input mode: CLI only (other inputs disabled)")

            # ARCH-15 PR-3/PR-5: render results through the output hexagon (origin-paired console
            # output) instead of bare prints. Registers ConsoleOutput on the *shared* process-wide
            # OutputManager (built by the composition root), so sync renders AND deferred F&F
            # notifications (routed by NotificationService) both reach the terminal. Non-quiet only
            # (quiet suppresses result echo, matching prior behaviour).
            from ..outputs.console import ConsoleOutput
            self._output_manager = self.core.output_manager
            out_cfg = getattr(self.core.config, "outputs", None)  # ARCH-15 PR-7: config-driven
            if self._output_manager is not None and (out_cfg is None or out_cfg.console):
                prefix = out_cfg.console_prefix if out_cfg is not None else "📝 "
                await self._output_manager.add_output("console", ConsoleOutput(origin="cli", prefix=prefix))

        # Build the web API alongside the CLI (unless --headless / web deps absent).
        if self.core and getattr(self.core.config.system, "web_api_enabled", False):
            try:
                await self._setup_web_server(args)
            except Exception as e:
                self._logger.warning(f"Web API unavailable, CLI-only: {e}")
                self.app = None
    
    async def _execute_runner_logic(self, args: argparse.Namespace) -> int:
        """Execute CLI runner logic — the REPL/command in the foreground, the web API (if built) on a
        background task that's stopped when the CLI exits."""
        if not self.core:
            return 1
        server, task = (None, None)
        if self.app:
            server, task = await self._serve_in_background(args)
        try:
            return await self._cli_logic(args)
        finally:
            await self._stop_background_server(server, task)

    async def _cli_logic(self, args: argparse.Namespace) -> int:
        # Handle single command execution
        if args.command:
            try:
                if not args.quiet:
                    print(f"🔤 Executing command: '{args.command}'")
                # Use unified workflow interface
                result = await self.core.workflow_manager.process_text_input(
                    text=args.command,
                    session_id=SessionManager.generate_session_id("cli"),
                    wants_audio=getattr(args, 'enable_tts', False),  # Phase 5: TTS support
                    client_context={"source": "cli", "quiet": args.quiet}
                )
                await self._render_result(result, args)
                
                # Exit unless interactive mode is forced
                if not args.interactive:
                    if not args.quiet:
                        print("✅ Command executed successfully")
                    return 0
            except Exception as e:
                self._logger.error(f"Error executing command '{args.command}': {e}")
                if not args.quiet:
                    print(f"❌ Error executing command: {e}")
                return 1
        
        # Interactive mode
        return await self._run_interactive_loop(args, "irene> ")


def run_cli() -> int:
    """Entry point for CLI runner"""
    try:
        runner = CLIRunner()
        return asyncio.run(runner.run())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        return 0


if __name__ == "__main__":
    sys.exit(run_cli()) 