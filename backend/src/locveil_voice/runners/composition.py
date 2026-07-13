"""
Composition root - assembles a fully-wired AsyncVACore from its managers.

ARCH-11 / S3: construction of ALL managers is moved OUT of `AsyncVACore` into
this composition module. The runners are the composition root — the layer
permitted to depend outward on `inputs`/`components`/`workflows` — so the
delivery-layer `InputManager` is imported and built here, then injected into the
core. This is what lets `core` itself stop importing `inputs.manager` (edge 4 of
ARCH-11). (The legacy `AsyncPluginManager` was retired in ARCH-13.)
"""

import logging
from pathlib import Path
from typing import Optional

from ..config.models import CoreConfig
from ..core.engine import AsyncVACore
from ..core.catalog_service import CatalogService
from ..core.components import ComponentManager
from ..core.interfaces.output import OutputModality
from ..core.workflow_manager import WorkflowManager
from ..core.metrics import get_metrics_collector
from ..intents.context import ContextManager
from ..core.event_bus import EventBus
from ..inputs.manager import InputManager
from ..outputs.manager import OutputManager
from ..outputs.bridge import BridgeClient

logger = logging.getLogger(__name__)


def build_core(config: CoreConfig, config_path: Optional[Path] = None) -> AsyncVACore:
    """Construct every manager and assemble the AsyncVACore.

    Construction order preserves the original `AsyncVACore.__init__` wiring:
    `InputManager` and `WorkflowManager` depend on the `ComponentManager`.
    """
    component_manager = ComponentManager(config)
    input_manager = InputManager(component_manager, config.inputs)
    # ARCH-15 PR-6: one process-wide pipeline event bus. The WorkflowManager publishes lifecycle
    # events; the OutputManager publishes `output.delivered`; the observation tap (PR-6b) and metrics
    # subscribe. Built here and shared across both managers + the engine.
    event_bus = EventBus()
    # ARCH-15 PR-5: the process-wide output delivery layer (symmetric to InputManager). Built here
    # and injected; runners/profiles register the concrete output adapters onto it.
    output_manager = OutputManager(event_bus=event_bus)
    context_manager = ContextManager(  # QUAL-36: seed sessions from the one canonical language source
        default_language=config.default_language,
        supported_languages=config.supported_languages,
    )
    metrics_collector = get_metrics_collector()  # Phase 2: unified metrics
    workflow_manager = WorkflowManager(component_manager, config, event_bus=event_bus)

    # ARCH-8 PR-2: the device-catalog holder. Built unconditionally (handlers/resolver depend on
    # the port regardless); its fetcher + the bridge output are wired in setup_bridge_output()
    # only when `[outputs.bridge]` is enabled.
    catalog_service = CatalogService()

    return AsyncVACore(
        config,
        config_path=config_path,
        component_manager=component_manager,
        input_manager=input_manager,
        output_manager=output_manager,
        event_bus=event_bus,
        context_manager=context_manager,
        metrics_collector=metrics_collector,
        workflow_manager=workflow_manager,
        catalog_service=catalog_service,
    )


async def setup_bridge_output(core: AsyncVACore) -> None:
    """Register + designate the locveil-bridge actuation output when configured (ARCH-8 PR-2).

    Called by the base runner after `core.start()` — runner-agnostic (every profile gets the
    DEVICE_COMMAND channel from the same `[outputs.bridge]` config). Also wires the catalog:
    the `BridgeClient` becomes the `CatalogService` fetcher and one startup pull is attempted
    (§5a); failure is non-fatal — the ARCH-26 lazy refresh retries on the first resolution miss.
    """
    bridge_cfg = getattr(core.config.outputs, "bridge", None)
    if bridge_cfg is None or not bridge_cfg.enabled:
        return
    output_manager = core.output_manager
    if output_manager is None:
        logger.warning("[outputs.bridge] enabled but no OutputManager — bridge output not registered")
        return

    bridge = BridgeClient(base_url=bridge_cfg.base_url,
                          timeout_seconds=bridge_cfg.timeout_seconds)
    await bridge.start()
    await output_manager.add_output(bridge.get_output_type(), bridge)
    output_manager.designate(OutputModality.DEVICE_COMMAND, bridge.get_output_type())
    core.catalog_service.set_fetcher(bridge.fetch_catalog)
    core.catalog_service.set_state_reader(bridge.get_device_state)
    core.catalog_service.set_options_reader(bridge.get_device_options)
    logger.info(f"✅ Bridge output registered + designated for DEVICE_COMMAND ({bridge_cfg.base_url})")

    snapshot = await core.catalog_service.refresh()
    if snapshot is None:
        logger.warning("Device catalog unavailable at startup — lazy refresh will retry on first use")

async def setup_problem_reporting(core: AsyncVACore) -> None:
    """Wire the problem-report delivery service when configured (ARCH-32, design §6).

    Called by the base runner after `core.start()`, beside `setup_bridge_output` — runner-agnostic.
    The request ring is sized regardless (it is the always-on diagnosis buffer); the delivery
    service exists only when `[reports]` is enabled AND the repo + token are present — otherwise
    the report intent keeps answering honestly that reporting isn't set up.
    """
    import os

    from ..core.request_ring import get_request_ring

    cfg = getattr(core.config, "reports", None)
    if cfg is None:
        return
    get_request_ring().resize(cfg.ring_size)
    if not cfg.enabled:
        return

    token = os.getenv(cfg.token_env, "")
    if not cfg.repo or not token:
        logger.warning(f"[reports] enabled but repo/token missing (repo='{cfg.repo}', "
                       f"env {cfg.token_env} {'set' if token else 'EMPTY'}) — reporting stays off")
        return

    from ..core.report_bundle import ReportBundleCollector
    from ..core.report_service import ReportService
    from ..outputs.github_report import GitHubReportClient

    client = GitHubReportClient(cfg.repo, token)
    await client.start()

    def _catalog_version():
        snapshot = core.catalog_service.catalog() if core.catalog_service else None
        return snapshot.version if snapshot else None

    collector = ReportBundleCollector(
        config_path=core.config_path,
        catalog_version=_catalog_version,
    )
    # ARCH-34: when the bridge output is wired (setup_bridge_output ran just before us), every
    # report also carries the bridge's evidence envelope — don't gate on a smart-home heuristic;
    # over-attaching into the same private repo is free, and unreachable is itself evidence.
    bridge_fetcher = None
    if core.output_manager is not None:
        bridge = core.output_manager.get_output("bridge")
        if bridge is not None and hasattr(bridge, "fetch_report_evidence"):
            bridge_fetcher = bridge.fetch_report_evidence

    spool_dir = core.config.assets.assets_root / "state" / "reports"
    service = ReportService(collector, client, spool_dir,
                            rate_limit_per_hour=cfg.rate_limit_per_hour,
                            rate_limit_per_day=cfg.rate_limit_per_day,
                            bridge_evidence_fetcher=bridge_fetcher)

    intent_component = core.component_manager.get_component("intent_system")
    handler_manager = getattr(intent_component, "handler_manager", None)
    if handler_manager is None:
        logger.warning("[reports] enabled but the intent system is unavailable — reporting stays off")
        return
    injected = 0
    for name, handler in handler_manager.get_handlers().items():
        if hasattr(handler, "set_report_service"):
            handler.set_report_service(service, capture_ttl_seconds=cfg.capture_ttl_seconds)
            injected += 1
    logger.info(f"✅ Problem reporting wired ({cfg.repo}, spool {spool_dir}, "
                f"{injected} handler(s), bridge evidence "
                f"{'on' if bridge_fetcher else 'off'})")
