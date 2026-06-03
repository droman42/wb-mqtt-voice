"""
Composition root - assembles a fully-wired AsyncVACore from its managers.

ARCH-11 / S3: construction of ALL managers is moved OUT of `AsyncVACore` into
this composition module. The runners are the composition root — the layer
permitted to depend outward on `inputs`/`components`/`workflows` — so the
delivery-layer `InputManager` is imported and built here, then injected into the
core. This is what lets `core` itself stop importing `inputs.manager` (edge 4 of
ARCH-11). (The legacy `AsyncPluginManager` was retired in ARCH-13.)
"""

from pathlib import Path
from typing import Optional

from ..config.models import CoreConfig
from ..core.engine import AsyncVACore
from ..core.components import ComponentManager
from ..core.workflow_manager import WorkflowManager
from ..core.timers import AsyncTimerManager
from ..core.metrics import get_metrics_collector
from ..intents.context import ContextManager
from ..inputs.manager import InputManager


def build_core(config: CoreConfig, config_path: Optional[Path] = None) -> AsyncVACore:
    """Construct every manager and assemble the AsyncVACore.

    Construction order preserves the original `AsyncVACore.__init__` wiring:
    `InputManager` and `WorkflowManager` depend on the `ComponentManager`.
    """
    component_manager = ComponentManager(config)
    input_manager = InputManager(component_manager, config.inputs)
    context_manager = ContextManager(  # QUAL-36: seed sessions from the one canonical language source
        default_language=config.default_language,
        supported_languages=config.supported_languages,
    )
    timer_manager = AsyncTimerManager()
    metrics_collector = get_metrics_collector()  # Phase 2: unified metrics
    workflow_manager = WorkflowManager(component_manager, config)

    return AsyncVACore(
        config,
        config_path=config_path,
        component_manager=component_manager,
        input_manager=input_manager,
        context_manager=context_manager,
        timer_manager=timer_manager,
        metrics_collector=metrics_collector,
        workflow_manager=workflow_manager,
    )
