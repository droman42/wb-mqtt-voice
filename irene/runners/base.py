"""
Base Runner Class - Common patterns for all Irene runners

Provides unified initialization, configuration management, and core lifecycle
patterns shared across CLI, WebAPI, and VOSK runners.
"""

import asyncio
import argparse
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from ..config.models import CoreConfig, ComponentConfig, LogLevel
from ..config.manager import ConfigManager
from ..core.engine import AsyncVACore
from .composition import build_core
from ..utils.logging import setup_logging


logger = logging.getLogger(__name__)


@dataclass
class RunnerConfig:
    """Configuration specific to runner behavior"""
    name: str
    description: str
    requires_config_file: bool = False
    supports_interactive: bool = False
    default_components: Optional[ComponentConfig] = None
    required_dependencies: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.required_dependencies is None:
            self.required_dependencies = []


class BaseRunner(ABC):
    """
    Abstract base class for all Irene runners.
    
    Provides common patterns for:
    - Argument parsing with runner-specific extensions
    - Environment and logging setup
    - Configuration loading and validation
    - Core lifecycle management
    - Error handling and cleanup
    """
    
    def __init__(self, runner_config: RunnerConfig):
        self.runner_config = runner_config
        self.core: Optional[AsyncVACore] = None
        self._logger = logging.getLogger(f"{__name__}.{self.runner_config.name}")

    # Entry-point build-metadata contract (QUAL-3) — runners are `irene.runners`
    # entry-points and must answer the same metadata methods as other entry-points.
    # A runner coordinates components; the enabled components declare the real deps,
    # so a runner has none of its own by default. Specific runners may override.
    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        """Python modules the runner itself requires (default: none)."""
        return []

    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        """System packages the runner itself requires (default: none)."""
        return {"linux.ubuntu": [], "linux.alpine": [], "macos": [], "windows": []}

    @classmethod
    def get_platform_support(cls) -> List[str]:
        """Platforms the runner supports (default: all)."""
        return ["linux.ubuntu", "linux.alpine", "macos", "windows"]

    async def run(self, args: Optional[List[str]] = None) -> int:
        """Main runner entry point with unified pattern"""
        parsed_args: Optional[argparse.Namespace] = None
        try:
            # 1. Load environment variables from .env file first
            from dotenv import load_dotenv
            load_dotenv()
            
            # 2. Parse arguments (base + runner-specific)
            parser = self._create_argument_parser()
            parsed_args = parser.parse_args(args)
            
            # 3. Setup centralized logging
            self._setup_logging(parsed_args)
            
            # 4. Handle utility options (exit early if needed)
            early_exit_code = await self._handle_utility_options(parsed_args)
            if early_exit_code is not None:
                return early_exit_code
            
            # 5. Check dependencies
            if not await self._check_dependencies(parsed_args):
                return 1
            
            # 6. Create and validate configuration
            config = await self._create_and_validate_config(parsed_args)

            # 6b. Install the global trace logging handler (ARCH-19). Inert unless a trace is
            # active, so it is safe to install regardless of whether tracing is enabled.
            self._install_trace_logger(config)

            # 7. Create and start assistant core
            self.core = build_core(config, config_path=parsed_args.config)
            
            if not getattr(parsed_args, 'quiet', False):
                self._logger.info(f"Initializing Irene in {self.runner_config.name} mode...")
                print(f"🔧 Initializing Irene in {self.runner_config.name} mode...")
            
            await self.core.start()
            
            # 8. Runner-specific initialization
            await self._post_core_setup(parsed_args)
            
            # 9. Execute runner-specific logic
            return await self._execute_runner_logic(parsed_args)
            
        except Exception as e:
            self._logger.error(f"{self.runner_config.name} Runner error: {e}")
            if not getattr(parsed_args, 'quiet', False):
                print(f"❌ {self.runner_config.name} Runner error: {e}")
            return 1
        finally:
            if self.core:
                await self.core.stop()
    
    def _create_argument_parser(self) -> argparse.ArgumentParser:
        """Create argument parser with base options + runner-specific extensions"""
        parser = argparse.ArgumentParser(
            description=f"Irene Voice Assistant v15 - {self.runner_config.description}",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=self._get_usage_examples()
        )
        
        # Add base arguments
        self._add_base_arguments(parser)
        
        # Add runner-specific arguments
        self._add_runner_arguments(parser)
        
        return parser
    
    def _add_base_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add common arguments shared by all runners"""
        # Configuration options
        parser.add_argument(
            "--config", "-c",
            type=Path,
            # Default from $IRENE_CONFIG_FILE so containers point at the baked config (or a mounted
            # override) with no entrypoint script; falls back to ./config.toml for a bare invocation.
            default=Path(os.getenv("IRENE_CONFIG_FILE", "config.toml")),
            help="Configuration file path (default: $IRENE_CONFIG_FILE or config.toml)"
        )
        
        # Logging options
        parser.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            default="INFO",
            help="Set logging level"
        )
        parser.add_argument(
            "--quiet", "-q",
            action="store_true",
            help="Reduce output verbosity"
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable debug logging"
        )
        
        # Tracing options (ARCH-19) — opt-in save+replay; off by default, zero overhead when off
        parser.add_argument(
            "--trace",
            action="store_true",
            help="Save a self-contained execution trace for every request (under <assets_root>/traces)"
        )
        parser.add_argument(
            "--trace-raw-mic",
            action="store_true",
            help="Also capture the pre-canonical LIVE mic audio (raw level; heavier rolling buffer). Implies --trace"
        )

        # Utility options
        parser.add_argument(
            "--check-deps",
            action="store_true",
            help="Check dependencies and exit"
        )
    
    def _setup_logging(self, args: argparse.Namespace) -> None:
        """Setup centralized logging"""
        log_level = LogLevel(args.log_level)
        if args.debug:
            log_level = LogLevel.DEBUG
            
        setup_logging(
            level=log_level,
            log_file=Path("logs/irene.log"),
            enable_console=True
        )
    
    def _install_trace_logger(self, config: CoreConfig) -> None:
        """Install the ARCH-19 TraceLogger on the root logger (once), configured from [trace].

        The handler is inert unless a per-request trace is active, so it is installed
        unconditionally; its level + record cap come from config so they stay tunable.
        """
        from ..core.trace_context import TraceLogger
        tcfg = getattr(config, "trace", None)
        level = getattr(logging, tcfg.log_threshold.value, logging.INFO) if tcfg else logging.INFO
        max_records = tcfg.max_log_records if tcfg else 500
        root = logging.getLogger()
        for handler in root.handlers:
            if isinstance(handler, TraceLogger):
                handler.setLevel(level)
                handler.max_records = max_records
                return
        root.addHandler(TraceLogger(level=level, max_records=max_records))

    async def _handle_utility_options(self, args: argparse.Namespace) -> Optional[int]:
        """Handle utility options that should exit early"""
        if args.check_deps:
            success = await self._check_dependencies(args)
            return 0 if success else 1
        
        # Allow runners to handle additional utility options
        return await self._handle_runner_utility_options(args)
    
    async def _create_and_validate_config(self, args: argparse.Namespace) -> CoreConfig:
        """Create configuration with unified pattern"""
        config_manager = ConfigManager()
        
        # Load base configuration
        if args.config.exists():
            config = await config_manager.load_config(args.config)
            if not args.quiet:
                print(f"✅ Loaded configuration from: {args.config}")
        elif self.runner_config.requires_config_file:
            print(f"❌ Configuration file not found: {args.config}")
            print(f"💡 {self.runner_config.name} runner requires a configuration file")
            raise ValueError(f"Configuration file not found: {args.config}")
        else:
            config = config_manager.get_default_config()
            if not args.quiet:
                print("📋 Using default configuration")
        
        # Apply runner-specific configuration modifications
        config = await self._modify_config_for_runner(config, args)
        
        # Apply command line overrides
        if args.debug:
            config.debug = True
            config.log_level = LogLevel.DEBUG
        elif args.log_level:
            config.log_level = LogLevel(args.log_level)

        # ARCH-19: --trace / --trace-raw-mic flip the trace section before startup (D-7).
        # The startup flag is the only gate (D-17): when on, every request is saved.
        if getattr(args, "trace", False) or getattr(args, "trace_raw_mic", False):
            config.trace.enabled = True
        if getattr(args, "trace_raw_mic", False):
            # The raw-mic flag is self-contained: enable the heavier rolling buffer AND select the
            # raw capture level (its whole purpose is "trace what the mic actually heard").
            config.trace.capture_raw_mic = True
            config.trace.capture_level = "raw"

        # Validate configuration
        await self._validate_runner_config(config, args)

        return config
    
    async def _validate_runner_config(self, config: CoreConfig, args: argparse.Namespace) -> None:
        """Validate configuration for runner requirements"""
        errors = []
        
        # Check runner-specific requirements
        runner_errors = await self._validate_runner_specific_config(config, args)
        errors.extend(runner_errors)
        
        if errors:
            error_message = f"{self.runner_config.name} Runner configuration validation failed:\n\n"
            for i, error in enumerate(errors, 1):
                error_message += f"  {i}. {error}\n"
            error_message += f"\nPlease update your configuration file for {self.runner_config.name} mode.\n"
            
            # Add runner-specific configuration examples
            example_config = self._get_configuration_example()
            if example_config:
                error_message += f"\nExample configuration:\n{example_config}"
            
            raise ValueError(error_message)
    
    # Abstract methods that runners must implement
    @abstractmethod
    def _add_runner_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add runner-specific command line arguments"""
        pass
    
    @abstractmethod
    def _get_usage_examples(self) -> str:
        """Get usage examples for help text"""
        pass
    
    @abstractmethod
    async def _check_dependencies(self, args: argparse.Namespace) -> bool:
        """Check runner-specific dependencies"""
        pass
    
    @abstractmethod
    async def _modify_config_for_runner(self, config: CoreConfig, args: argparse.Namespace) -> CoreConfig:
        """Modify configuration for runner-specific needs"""
        pass
    
    @abstractmethod
    async def _validate_runner_specific_config(self, config: CoreConfig, args: argparse.Namespace) -> List[str]:
        """Validate runner-specific configuration requirements. Return list of error messages."""
        pass
    
    @abstractmethod
    async def _execute_runner_logic(self, args: argparse.Namespace) -> int:
        """Execute the main runner logic"""
        pass
    
    # Optional methods that runners can override
    async def _handle_runner_utility_options(self, args: argparse.Namespace) -> Optional[int]:
        """Handle runner-specific utility options. Return exit code if should exit early."""
        return None
    
    async def _post_core_setup(self, args: argparse.Namespace) -> None:
        """Perform runner-specific setup after core is started"""
        pass
    
    def _get_configuration_example(self) -> Optional[str]:
        """Get example configuration for error messages"""
        return None


class InteractiveRunnerMixin:
    """
    Mixin for runners that support interactive mode.
    
    Provides common interactive loop patterns.
    """

    # Attributes provided by the concrete runner (BaseRunner) this mixin is combined with;
    # declared for type-checking only (set in BaseRunner.__init__/run). QUAL-4c.
    core: Optional[AsyncVACore]
    _logger: logging.Logger
    runner_config: RunnerConfig

    async def _run_interactive_loop(self, args: argparse.Namespace, prompt_text: str = "irene> ") -> int:
        """Consume the single CLI input source and route each line through the workflow.

        ARCH-15 PR-5b: the runner no longer owns a `prompt_toolkit` reader. The InputManager-owned
        `CLIInput` adapter is the **single** reader (its `_input_loop`); this loop CONSUMES its
        `listen()` stream and renders results through the shared OutputManager (`_render_result`).
        One reader + one consumer ⇒ the PR-0 double-reader is structurally impossible. Meta-commands
        (`help`/`status`) are ordinary `system.*` intents now (D-4); only `quit`/`exit`/`q` is
        transport-local (CLIInput already normalises them and stops its reader).
        """
        if not self.core or not self.core.input_manager:
            return 1
        source = self.core.input_manager._sources.get("cli")
        if source is None:
            self._logger.error("CLI input source not available for interactive loop")
            return 1

        if not args.quiet:
            print("\n💬 Type a command, or 'quit' to exit")
            print("-" * 50)

        try:
            async for data in source.listen():
                if not isinstance(data, str):
                    continue
                command = data.strip()
                if not command:
                    continue
                if command.lower() in ("quit", "exit", "q"):
                    break
                try:
                    await self._process_interactive_command(command, args)
                except Exception as e:
                    self._logger.error(f"Error processing command: {e}")
                    if not args.quiet:
                        print(f"❌ Error: {e}")
            return 0
        except Exception as e:
            self._logger.error(f"Interactive loop error: {e}")
            return 1
    
    async def _process_interactive_command(self, command: str, args: argparse.Namespace) -> None:
        """Process a single interactive command"""
        if self.core is None:
            return
        result = await self.core.workflow_manager.process_text_input(
            text=command,
            session_id=f"{self.runner_config.name}_interactive",
            wants_audio=getattr(args, 'enable_tts', False),
            client_context={"source": "cli"}  # channel (ARCH-15 PR-3 origin routing)
        )

        await self._render_result(result, args)

    async def _render_result(self, result, args: argparse.Namespace) -> None:
        """Render a result through the output layer (ARCH-15 PR-3).

        If an OutputManager is wired (CLIRunner builds one with a ConsoleOutput on the `cli`
        channel), the result is delivered origin-paired through the output hexagon; otherwise it
        falls back to a direct print. Superseded by PR-5, where the daemon delivers with the real
        request context instead of the runner constructing one.
        """
        if not result.text:
            return
        output_manager = getattr(self, "_output_manager", None)
        if output_manager is not None:
            from ..intents.context_models import RequestContext
            from ..core.interfaces.output import OutputModality
            ctx = RequestContext(source="cli",
                                 session_id=f"{self.runner_config.name}_interactive")
            delivered = await output_manager.deliver(result, ctx, OutputModality.TEXT)
            if any(d.delivered for d in delivered):
                return
        if not args.quiet:
            print(f"📝 {result.text}")
