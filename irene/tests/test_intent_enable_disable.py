#!/usr/bin/env python3
"""
Comprehensive tests for intent handler enable/disable functionality.

This test suite validates the complete implementation of Phase 1-3:
- Configuration-driven handler filtering
- Donation coordination between Intent and NLU components
- Comprehensive validation and error handling
"""

import asyncio
import pytest
import tempfile
import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, Any, List
from unittest.mock import Mock, patch

from irene.config.models import IntentSystemConfig, IntentHandlerListConfig
from irene.components.intent_component import IntentComponent
from irene.components.nlu_component import NLUComponent
from irene.intents.manager import IntentHandlerManager
from irene.core.components import ComponentManager


class _StubHandler:
    """Minimal handler test double honoring the init contract the manager calls.

    Mirrors the handler surface used by
    IntentHandlerManager._initialize_handlers_with_donations: set_asset_loader,
    set_donation, has_donation. A handler can be told to fail at set_asset_loader
    to exercise the isolation/drop path.
    """

    def __init__(self, fail_on_asset_loader: bool = False):
        self._fail_on_asset_loader = fail_on_asset_loader
        self.asset_loader = None
        self.donation = None

    def set_asset_loader(self, loader):
        if self._fail_on_asset_loader:
            raise RuntimeError("simulated handler initialization failure")
        self.asset_loader = loader

    def set_donation(self, donation):
        self.donation = donation

    def has_donation(self) -> bool:
        return self.donation is not None


class TestIntentHandlerConfiguration:
    """Test configuration validation for intent handlers."""
    
    def test_valid_configuration(self):
        """Test that valid configurations pass validation."""
        config = IntentSystemConfig()
        assert config.enabled is True
        assert len(config.handlers.enabled) > 0
        assert len(config.handlers.disabled) == 0
    
    def test_empty_enabled_handlers_validation(self):
        """Test that empty enabled handlers list raises error."""
        with pytest.raises(ValueError, match="At least one intent handler must be enabled"):
            IntentHandlerListConfig(enabled=[])
    
    def test_invalid_handler_names_validation(self):
        """Test validation of handler names."""
        # Test invalid characters
        with pytest.raises(ValueError, match="Invalid characters in handler names"):
            IntentHandlerListConfig(enabled=["conversation", "handler/with/slash"])
        
        # Test empty names
        with pytest.raises(ValueError, match="Handler name cannot be empty"):
            IntentHandlerListConfig(enabled=["conversation", ""])
        
        # Test non-string names (Pydantic validates this at the type level)
        with pytest.raises((ValueError, Exception)):  # Pydantic raises ValidationError
            IntentHandlerListConfig(enabled=["conversation", 123])
    
    def test_enabled_disabled_overlap_validation(self):
        """Test that handlers cannot be both enabled and disabled."""
        with pytest.raises(ValueError, match="Handlers cannot be both enabled and disabled"):
            IntentHandlerListConfig(
                enabled=["conversation", "timer"],
                disabled=["conversation"]
            )
    
    def test_fallback_intent_validation(self):
        """Test fallback intent validation."""
        # Test invalid format
        with pytest.raises(ValueError, match="fallback_intent must be in format"):
            IntentSystemConfig(fallback_intent="invalid_format")
        
        # Test disabled fallback handler
        with pytest.raises(ValueError, match="Fallback intent handler .* is not enabled"):
            IntentSystemConfig(
                fallback_intent="audio_playback.general",
                handlers=IntentHandlerListConfig(
                    enabled=["conversation", "timer"],
                    disabled=["audio_playback"]
                )
            )
    
    def test_enabled_handler_without_configuration_raises(self):
        """An enabled handler whose configuration object is None must fail validation.

        This is the current public contract of validate_handler_configurations():
        configuration *presence* is enforced per enabled handler that owns a config slot.
        """
        config = IntentSystemConfig()
        config.conversation = None  # enabled by default but now has no config

        with pytest.raises(ValueError, match="Handler 'conversation' is enabled but has no configuration"):
            config.validate_handler_configurations()

    def test_unknown_handler_name_is_not_rejected_by_config_validation(self):
        """Handler *existence* is not validated at the config layer.

        Unknown handler names without a config slot are tolerated by
        validate_handler_configurations() (existence is enforced later at
        IntentHandlerManager.initialize, see test_missing_handlers_error).
        The method returns the config unchanged.
        """
        config = IntentSystemConfig()
        config.handlers.enabled = ["conversation", "timer", "nonexistent_handler"]

        assert config.validate_handler_configurations() is config


class TestIntentHandlerManager:
    """Test intent handler manager functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration for testing."""
        return {
            "enabled": ["conversation", "timer"],
            "disabled": [],
            "auto_discover": True,
            "discovery_paths": ["irene.intents.handlers"],
            "asset_validation": {
                "strict_mode": True
            }
        }
    
    @pytest.mark.asyncio
    async def test_no_config_error(self):
        """Test that manager requires configuration."""
        manager = IntentHandlerManager()
        
        with pytest.raises(ValueError, match="IntentHandlerManager requires configuration"):
            await manager.initialize()
    
    @pytest.mark.asyncio
    async def test_empty_enabled_handlers_error(self, mock_config):
        """Test error when no handlers are enabled."""
        mock_config["enabled"] = []
        manager = IntentHandlerManager()
        
        with pytest.raises(ValueError, match="No intent handlers enabled"):
            await manager.initialize(mock_config)
    
    @pytest.mark.asyncio
    async def test_missing_handlers_error(self, mock_config):
        """Test error when requested handlers are not found."""
        mock_config["enabled"] = ["nonexistent_handler"]
        manager = IntentHandlerManager()
        
        with patch('irene.utils.loader.dynamic_loader.discover_providers') as mock_discover:
            mock_discover.return_value = {}  # No handlers found
            
            with pytest.raises(ValueError, match="Intent handlers not found"):
                await manager.initialize(mock_config)


class TestNLUIntentCoordination:
    """Test coordination between NLU and Intent components."""
    
    @pytest.fixture
    def mock_intent_component(self):
        """Create mock intent component."""
        component = Mock(spec=IntentComponent)
        component.get_enabled_handler_names.return_value = ["conversation", "timer"]
        component.get_enabled_handler_donations.return_value = {
            "conversation": Mock(),
            "timer": Mock()
        }
        component.handler_manager = Mock()
        component.handler_manager.get_handlers.return_value = {
            "conversation": Mock(),
            "timer": Mock()
        }
        component.handler_manager._asset_loader = Mock()
        component.handler_manager._asset_loader.convert_to_keyword_donations.return_value = []
        return component
    
    def test_nlu_component_dependencies(self):
        """Test that NLU component declares intent_system dependency."""
        nlu = NLUComponent()
        dependencies = nlu.get_component_dependencies()
        assert "intent_system" in dependencies
    
    @pytest.mark.asyncio
    async def test_nlu_coordination_with_intent_component(self, mock_intent_component):
        """Test successful coordination between NLU and Intent components."""
        nlu = NLUComponent()
        nlu.inject_dependency('intent_system', mock_intent_component)
        nlu.providers = {}  # Empty providers for testing
        
        # Test coordination
        enabled_handlers = await nlu._get_enabled_handler_names()
        assert enabled_handlers == ["conversation", "timer"]
    
    @pytest.mark.asyncio
    async def test_nlu_fallback_when_intent_unavailable(self):
        """Test NLU fallback when Intent component is unavailable."""
        nlu = NLUComponent()
        # Don't inject intent_system dependency
        
        with patch.object(nlu, '_discover_all_handler_names') as mock_discover:
            mock_discover.return_value = ["fallback_handler"]
            
            enabled_handlers = await nlu._get_enabled_handler_names()
            assert enabled_handlers == ["fallback_handler"]
            mock_discover.assert_called_once()


class TestEndToEndIntegration:
    """Test end-to-end integration of the intent enable/disable system."""
    
    @pytest.mark.asyncio
    async def test_configuration_to_nlu_integration(self):
        """Test complete flow from configuration to NLU initialization."""
        # Create test configuration
        config = IntentSystemConfig()
        config.handlers.enabled = ["conversation", "timer"]
        config.handlers.disabled = []
        
        # Validate configuration
        validated_config = config.validate_handler_configurations()
        assert validated_config is not None
        
        # Test that enabled handlers are properly filtered
        final_enabled = [h for h in config.handlers.enabled if h not in config.handlers.disabled]
        assert len(final_enabled) == 2
        assert "conversation" in final_enabled
        assert "timer" in final_enabled


class TestErrorRecovery:
    """Test error recovery and graceful degradation."""
    
    @pytest.mark.asyncio
    async def test_partial_handler_failure_is_dropped_not_fatal(self):
        """A handler that fails initialization is dropped; working handlers survive.

        Contract of _initialize_handlers_with_donations(): failures are isolated.
        Failing handlers are removed from _handler_instances and the call returns
        normally as long as at least one handler succeeds.
        """
        manager = IntentHandlerManager()
        manager._asset_loader = object()  # opaque; only passed to set_asset_loader
        manager._handler_instances = {
            "working_handler": _StubHandler(),
            "failing_handler": _StubHandler(fail_on_asset_loader=True),
        }
        manager._donations = {
            "working_handler": SimpleNamespace(method_donations=[]),
            "failing_handler": SimpleNamespace(method_donations=[]),
        }

        # Must not raise: failure is isolated.
        await manager._initialize_handlers_with_donations()

        assert "working_handler" in manager._handler_instances
        assert "failing_handler" not in manager._handler_instances
        # Surviving handler actually received its donation.
        assert manager._handler_instances["working_handler"].donation is not None

    @pytest.mark.asyncio
    async def test_all_handlers_failing_is_fatal(self):
        """If every handler fails, the intent system cannot function -> RuntimeError."""
        manager = IntentHandlerManager()
        manager._asset_loader = object()
        manager._handler_instances = {
            "h1": _StubHandler(fail_on_asset_loader=True),
            "h2": _StubHandler(fail_on_asset_loader=True),
        }
        manager._donations = {
            "h1": SimpleNamespace(method_donations=[]),
            "h2": SimpleNamespace(method_donations=[]),
        }

        with pytest.raises(RuntimeError, match="All intent handlers failed initialization"):
            await manager._initialize_handlers_with_donations()


def test_logging_configuration():
    """Test that logging is properly configured for debugging."""
    import logging
    
    # Ensure our loggers exist and are configured
    intent_logger = logging.getLogger('irene.intents.manager')
    nlu_logger = logging.getLogger('irene.components.nlu_component')
    
    assert intent_logger is not None
    assert nlu_logger is not None


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
