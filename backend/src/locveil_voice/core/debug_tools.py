"""
Developer Tools and Debugging - Phase 3.4 Implementation

Debugging status for the monitoring /debug endpoint. (QUAL-61: the per-action
inspection path — inspect_active_action + its dataclasses — was dead code and
was removed; live action observability is /monitoring/actions, ARCH-28 D-9.)
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ActionDebugger:
    """Debugging and inspection tool for fire-and-forget actions"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.ActionDebugger")
        
        # Component references
        self.context_manager = None
        self.metrics_collector = None
        
        # Debug configuration (QUAL-61: inspection history / test-action state removed
        # with the dead inspect_active_action path)
        self._debug_enabled = True
        
    def initialize(self, components: Dict[str, Any]) -> None:
        """Initialize debugger with system components"""
        self.context_manager = components.get('context_manager')
        self.metrics_collector = components.get('metrics_collector')
        
        self.logger.info("Action debugger initialized")
    
    def get_debugging_status(self) -> Dict[str, Any]:
        """Get current debugging system status"""
        return {
            "debug_enabled": self._debug_enabled,
            "component_availability": {
                "context_manager": self.context_manager is not None,
                "metrics_collector": self.metrics_collector is not None
            }
        }


# Global debugger instance
_action_debugger: Optional[ActionDebugger] = None


def get_action_debugger() -> ActionDebugger:
    """Get the global action debugger instance"""
    global _action_debugger
    if _action_debugger is None:
        _action_debugger = ActionDebugger()
    return _action_debugger


def initialize_action_debugger(components: Dict[str, Any]) -> ActionDebugger:
    """Initialize the global action debugger"""
    debugger = get_action_debugger()
    debugger.initialize(components)
    return debugger
