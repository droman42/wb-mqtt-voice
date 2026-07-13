"""
Shared web-server machinery for runners that expose the FastAPI app.

Extracted from `webapi_runner` so the standalone `voice_runner` can serve the same REST + WebSocket API
*alongside* the local microphone pipeline. A runner gains the web server by inheriting `WebServerMixin`
(plus calling `_init_web_server_state()` in `__init__`, adding `_add_web_server_arguments(parser)`,
building the app with `_setup_web_server(args)`, and serving with `_start_server(args)`).

The mixin owns: the server CLI args, the asset loader for web templates, the WebInput source, FastAPI
app creation + router mounting, and the uvicorn server loop. It expects the host runner to provide
`self.core` (set by BaseRunner) and the standard parsed args (`debug`, `quiet`, `log_level`).
"""

import argparse
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from ..__version__ import __version__

logger = logging.getLogger(__name__)


class WebServerMixin:
    """FastAPI/uvicorn server, shared by webapi_runner and voice_runner."""

    # Attributes provided by BaseRunner (core) and _init_web_server_state (the rest) at runtime —
    # declared here so the mixin type-checks on its own.
    core: Any
    app: Any
    web_input: Any
    _asset_loader: Optional[Any]
    _start_time: float

    # --- state + args ------------------------------------------------------------------------------

    def _init_web_server_state(self) -> None:
        """Initialise the web-server instance attributes (call from the runner's __init__)."""
        self.app = None
        self.web_input = None
        self._asset_loader = None
        self._start_time = time.time()

    def _add_web_server_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add the server CLI args (host/port/workers/ssl/reload/cors/tts)."""
        parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
        parser.add_argument("--port", "-p", type=int, default=None,
                            help="Port to bind to (default: from config or 6000)")
        parser.add_argument("--workers", type=int, default=1,
                            help="Number of worker processes (default: 1)")
        parser.add_argument("--ssl-cert", type=Path, help="SSL certificate file path")
        parser.add_argument("--ssl-key", type=Path, help="SSL private key file path")
        parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
        parser.add_argument("--cors-origins", nargs="*",
                            default=["http://localhost:3000", "http://127.0.0.1:3000"],
                            help="Allowed CORS origins")

    def _resolve_web_port(self, config, args) -> None:
        """Port precedence: --port > config.system.web_port > 6000."""
        if getattr(args, "port", None) is None:
            args.port = getattr(config.system, "web_port", None) or 6000

    # --- app build ---------------------------------------------------------------------------------

    async def _setup_web_server(self, args) -> None:
        """Build the FastAPI app: asset loader + WebInput source + app + routers."""
        await self._setup_web_asset_loader()
        await self._setup_web_components(args)
        self.app = await self._create_fastapi_app(args)

    async def _setup_web_asset_loader(self) -> None:
        """Setup the asset loader the web API serves from.

        BUG-22: prefer the intent system's FULLY-LOADED loader (donations, templates,
        localizations, web templates). The previous fresh instance loaded ONLY web templates,
        so every localization consumer in the router — notably the `room_alias` validation on
        /execute/command — saw empty data and rejected every room ("Valid aliases: []").
        The fresh web-templates-only loader remains as the fallback for a core without the
        intent system."""
        try:
            intent_component = (self.core.component_manager.get_component('intent_system')
                                if self.core and self.core.component_manager else None)
            loaded = getattr(getattr(intent_component, 'handler_manager', None),
                             '_asset_loader', None)
            if loaded is not None:
                if not getattr(loaded, 'web_templates', None):
                    await loaded._load_web_templates()
                self._asset_loader = loaded
                logger.info("✅ Web asset loader: reusing the intent system's loaded assets "
                            f"({len(loaded.web_templates)} web templates, "
                            f"{len(loaded.localizations)} localization sets)")
                return

            from ..core.intent_asset_loader import IntentAssetLoader, AssetLoaderConfig

            assets_root = Path("assets")
            if not assets_root.exists():
                # package-relative fallback: assets/ lives at repo root, and this file is
                # backend/src/locveil_voice/runners/web_server.py → parents[4] is the repo root.
                assets_root = Path(__file__).resolve().parents[4] / "assets"

            self._asset_loader = IntentAssetLoader(assets_root, AssetLoaderConfig())
            await self._asset_loader._load_web_templates()
            logger.info(f"✅ Web asset loader initialized with {len(self._asset_loader.web_templates)} templates")
        except Exception as e:
            logger.error(f"❌ Failed to initialize web asset loader: {e}")
            logger.warning("Web templates will fallback to inline HTML")
            self._asset_loader = None

    async def _setup_web_components(self, args) -> None:
        """Setup the WebInput source (output handled via the unified workflow)."""
        from ..inputs.web import WebInput

        self.web_input = WebInput(host=args.host, port=args.port)
        if self.core:
            await self.core.input_manager.add_source("web", self.web_input)
            await self.core.input_manager.start_source("web")
            logger.info("✅ Web components initialized")

    async def _create_fastapi_app(self, args):
        """Create and configure the FastAPI application."""
        from fastapi import FastAPI  # type: ignore
        from fastapi.middleware.cors import CORSMiddleware  # type: ignore
        from .webapi_router import create_webapi_router

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            yield
            logger.info("Shutting down Web API server")
            if self.web_input:
                await self.web_input.stop_listening()

        app = FastAPI(
            title="Irene Voice Assistant API",
            description="Modern async voice assistant API with WebSocket support",
            version=__version__,
            debug=args.debug,
            lifespan=lifespan,
        )
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,  # must be False when allow_origins=["*"]
            allow_methods=["*"],
            allow_headers=["*"],
        )

        await self._mount_static_files(app)

        if self.core is None:
            raise RuntimeError("Runner core not initialized before router creation")
        main_router = create_webapi_router(
            core=self.core,
            asset_loader=self._asset_loader,
            web_input=self.web_input,
            start_time=self._start_time,
        )
        app.include_router(main_router)
        await self._mount_component_routers(app)
        return app

    async def _mount_static_files(self, app) -> None:
        """Mount static files for CSS/JS assets."""
        try:
            from fastapi.staticfiles import StaticFiles  # type: ignore

            static_path = Path("assets/web/static")
            if not static_path.exists():
                # package-relative fallback: repo-root assets/ (see initialize()); this file sits
                # at backend/src/locveil_voice/runners/ → parents[4] is the repo root.
                static_path = Path(__file__).resolve().parents[4] / "assets" / "web" / "static"

            if static_path.exists():
                app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
                logger.info(f"✅ Static files mounted from {static_path}")
            else:
                logger.warning(f"⚠️ Static files directory not found: {static_path}")
        except ImportError:
            logger.warning("FastAPI StaticFiles not available, skipping static file mounting")
        except Exception as e:
            logger.error(f"❌ Failed to mount static files: {e}")

    async def _mount_component_routers(self, app):
        """Mount each component's router (universal WebAPIPlugin pattern)."""
        if not self.core:
            logger.warning("Core not available for router mounting")
            return
        try:
            from ..core.interfaces.webapi import web_api_components

            web_components = web_api_components(self.core)

            mounted = 0
            for name, component in web_components:
                try:
                    router = component.get_router()
                    if router:
                        app.include_router(router, prefix=component.get_api_prefix(),
                                           tags=component.get_api_tags())
                        mounted += 1
                        logger.info(f"✅ Mounted {name} router at {component.get_api_prefix()}")
                    else:
                        logger.warning(f"Component {name} returned no router")
                except Exception as e:
                    logger.error(f"❌ Failed to mount router for {name}: {e}")
            logger.info(f"✅ Mounted {mounted} component routers")
        except ImportError:
            logger.warning("FastAPI not available, skipping router mounting")
        except Exception as e:
            logger.error(f"Error mounting component routers: {e}")

    # --- serve -------------------------------------------------------------------------------------

    def _build_uvicorn_server(self, args, quiet_logging: bool = False):
        """Build a configured uvicorn.Server from the app + args (None if the app isn't built).

        quiet_logging: skip uvicorn's OWN logging config (its handlers write straight to the
        terminal, bypassing the root handlers) — uvicorn's loggers then propagate to the root
        logger, i.e. wherever the runner routed logs (file-only for the CLI REPL)."""
        import uvicorn  # type: ignore

        if not self.app:
            logger.error("FastAPI app not initialized")
            return None

        ssl_config = {}
        if args.ssl_cert and args.ssl_key:
            ssl_config = {"ssl_certfile": str(args.ssl_cert), "ssl_keyfile": str(args.ssl_key)}
        config_kwargs = {
            "app": self.app,
            "host": args.host,
            "port": args.port,
            "log_level": args.log_level.lower(),
            "reload": args.reload,
            "workers": args.workers if not args.reload else 1,
        }
        if quiet_logging:
            config_kwargs["log_config"] = None
            config_kwargs["access_log"] = False
        config_kwargs.update(ssl_config)
        return uvicorn.Server(uvicorn.Config(**config_kwargs))  # type: ignore

    def _web_banner(self, args, *, alongside: str = "") -> None:
        if not args.quiet:
            protocol = "https" if (args.ssl_cert and args.ssl_key) else "http"
            tail = f" (alongside {alongside})" if alongside else ""
            print(f"🌐 Web API server at {protocol}://{args.host}:{args.port}{tail}")
            print(f"📚 REST docs: {protocol}://{args.host}:{args.port}/docs")
            print(f"🔌 WebSockets: /ws/audio + /ws/audio/reply (ESP32 satellite), /ws/observe, /ws/output")

    async def _start_server(self, args) -> int:
        """Run uvicorn in the FOREGROUND (blocks until shutdown). Background tasks (e.g. the mic
        pipeline) keep running on the same event loop."""
        server = self._build_uvicorn_server(args)
        if server is None:
            return 1
        self._web_banner(args)
        if not args.quiet:
            print("Press Ctrl+C to stop")
        try:
            await server.serve()
            return 0
        except KeyboardInterrupt:
            if not args.quiet:
                print("\n🛑 Web API server stopped")
            return 0
        except Exception as e:
            logger.error(f"Server error: {e}")
            return 1

    async def _serve_in_background(self, args):
        """Start uvicorn as a BACKGROUND task — for a runner whose primary loop is the foreground
        (e.g. the CLI REPL). Returns (server, task); to stop: `server.should_exit = True; await task`.
        Returns (None, None) if the app isn't built."""
        import asyncio
        # quiet_logging: the foreground here is a REPL — uvicorn's own console handlers would
        # scribble over the prompt; its logs propagate to the root handlers (file) instead.
        server = self._build_uvicorn_server(args, quiet_logging=True)
        if server is None:
            return None, None
        self._web_banner(args, alongside="the console")
        return server, asyncio.create_task(server.serve())

    async def _stop_background_server(self, server, task) -> None:
        """Signal a background uvicorn server to stop and wait for it (best-effort)."""
        import asyncio
        if server is not None:
            server.should_exit = True
        if task is not None:
            try:
                await asyncio.wait_for(task, timeout=5)
            except Exception:
                task.cancel()
