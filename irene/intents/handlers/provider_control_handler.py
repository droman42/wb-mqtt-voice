"""
Provider Control Intent Handler - Provider switching across components

Handles provider switching commands that were previously hardcoded
across multiple components. Provides unified provider management.
"""

import logging
from typing import List, Dict, Any, Optional

from .base import IntentHandler
from ..models import Intent, IntentResult
from ..context_models import UnifiedConversationContext
from ..ports import ComponentControlRegistryPort

logger = logging.getLogger(__name__)


class ProviderControlIntentHandler(IntentHandler):
    """
    Handles provider control intents - switching providers across components.
    
    Features:
    - Provider switching for all components (Audio, LLM, ASR, TTS)
    - Provider information display
    - Unified provider management
    """
    
    def __init__(self):
        super().__init__()
        self._components = {}
        self._component_registry: Optional[ComponentControlRegistryPort] = None

    def set_component_registry(self, registry: Optional[ComponentControlRegistryPort]) -> None:
        """Set the injected component-control registry port (QUAL-24)."""
        self._component_registry = registry

    # Build dependency methods (TODO #5 Phase 2)
    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        """Provider control handler needs no external dependencies"""
        return []
        
    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        """Provider control handler has no system dependencies"""
        return {
            "linux.ubuntu": [],
            "linux.alpine": [],
            "macos": [],
            "windows": []
        }
        
    @classmethod
    def get_platform_support(cls) -> List[str]:
        """Provider control handler supports all platforms"""
        return ["linux.ubuntu", "linux.alpine", "macos", "windows"]
        
    async def can_handle(self, intent: Intent) -> bool:
        """Check if this handler can process provider control intents"""
        if not self.has_donation():
            raise RuntimeError(f"ProviderControlIntentHandler: Missing JSON donation file - provider_control_handler.json is required")
        
        # Use JSON donation patterns exclusively
        donation = self.get_donation()
        
        # Check domain patterns
        if hasattr(donation, 'domain_patterns') and intent.domain in donation.domain_patterns:
            return True
        
        # Check intent name patterns
        if hasattr(donation, 'intent_name_patterns') and intent.name in donation.intent_name_patterns:
            return True
        
        # Check action patterns
        if hasattr(donation, 'action_patterns') and intent.action in donation.action_patterns:
            return True
        
        return False
        
    async def execute(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Execute provider control intent"""
        # Use donation-driven routing exclusively
        return await self.execute_with_donation_routing(intent, context)
        
    async def _handle_switch_provider(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle provider switching request"""
        # Extract component and provider from intent entities
        component_type = intent.entities.get("component", "").lower()
        provider_name = intent.entities.get("provider", "")
        
        # If not in entities, try to extract from text
        if not component_type or not provider_name:
            component_type, provider_name = self._parse_provider_switch_command(intent.raw_text)
        
        if not component_type or not provider_name:
            return self._error_result(context, "Component type or provider name not specified")
        
        # Get the appropriate component
        component = await self._get_component(component_type)
        if not component:
            return self._error_result(context, f"Component {component_type} not available")
        
        # Determine language
        language = context.language
        
        # Switch provider based on component type
        success, message = self._switch_component_provider(component, component_type, provider_name, language)
        
        self.logger.info(f"Provider switch {component_type} -> {provider_name} - success: {success}")
        
        return IntentResult(
            text=message,
            should_speak=True,
            metadata={
                "action": "switch_provider",
                "component": component_type,
                "provider": provider_name,
                "success": success,
                "language": language
            },
            success=success
        )
        
    async def _handle_list_providers(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle list providers request"""
        # Extract component type from intent entities
        component_type = intent.entities.get("component", "").lower()
        
        # If not in entities, try to extract from text
        if not component_type:
            component_type = self._parse_list_providers_command(intent.raw_text)
        
        if not component_type:
            # List all providers from all components
            return await self._list_all_providers(intent, context)
        
        # Get the appropriate component
        component = await self._get_component(component_type)
        if not component:
            return self._error_result(context, f"Component {component_type} not available")
        
        # Get provider info based on component type
        info = self._get_component_providers_info(component, component_type)
        
        # Determine language
        language = context.language
        
        self.logger.info(f"List providers request for {component_type}")
        
        return IntentResult(
            text=info,
            should_speak=True,
            metadata={
                "action": "list_providers",
                "component": component_type,
                "language": language
            },
            success=True
        )
        
    async def _list_all_providers(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """List providers from all components"""
        info_parts = []
        
        # Determine language
        language = context.language
        
        info_parts.append(self._get_template("all_providers_header", language))
        
        info_parts.append("")
        
        # Check each component type
        for component_type in ["audio", "llm", "asr", "tts"]:
            component = await self._get_component(component_type)
            if component:
                component_info = self._get_component_providers_info(component, component_type)
                if component_info:
                    info_parts.append(component_info)
                    info_parts.append("")
        
        final_info = "\n".join(info_parts).strip()
        
        return IntentResult(
            text=final_info,
            should_speak=True,
            metadata={
                "action": "list_all_providers",
                "language": language
            },
            success=True
        )
    
    def _switch_component_provider(self, component, component_type: str, provider_name: str, language: str) -> tuple[bool, str]:
        """Switch provider for specific component"""
        try:
            # All components now use set_default_provider()
            success = component.set_default_provider(provider_name)
            
            if success:
                message = self._get_template("provider_switched", language, component_type=component_type, provider_name=provider_name)
            else:
                available = ", ".join(component.providers.keys()) if hasattr(component, 'providers') else "unknown"
                message = self._get_template("provider_unavailable", language, provider_name=provider_name, available=available)
                    
            return success, message
            
        except Exception as e:
            logger.error(f"Error switching {component_type} provider to {provider_name}: {e}")
            return False, self._get_template("provider_switch_error", language, error=e)
    
    def _get_component_providers_info(self, component, component_type: str) -> str:
        """Get provider info for specific component"""
        try:
            if component_type in ["audio", "llm", "asr", "tts"]:
                return component.get_providers_info()
            else:
                return f"Unknown component type: {component_type}"
        except Exception as e:
            logger.error(f"Error getting {component_type} provider info: {e}")
            return f"Error getting provider info: {e}"
    
    def _get_component_mappings(self, language: str) -> Dict[str, str]:
        """Get component mappings from asset loader - raises fatal error if not available"""
        if not self.has_asset_loader():
            raise RuntimeError(
                f"ProviderControlIntentHandler: Asset loader not initialized. "
                f"Cannot access component mappings for language '{language}'. "
                f"This is a fatal configuration error - component mappings must be externalized."
            )
        
        # Get localization data from asset loader
        components_data = self.asset_loader.get_localization("components", language)
        if components_data is None:
            raise RuntimeError(
                f"ProviderControlIntentHandler: Required component mappings for language '{language}' "
                f"not found in assets/localization/components/{language}.yaml. "
                f"This is a fatal error - all component mappings must be externalized."
            )
        
        component_mappings = components_data.get("component_mappings", {})
        if not component_mappings:
            raise RuntimeError(
                f"ProviderControlIntentHandler: Empty component_mappings in "
                f"assets/localization/components/{language}.yaml. "
                f"Component mappings must be defined for language '{language}'."
            )
        
        return component_mappings

    def _parse_provider_switch_command(self, text: str) -> tuple[str, str]:
        """Parse component type and provider name from text"""
        text_lower = text.lower()
        
        # Get component mappings from localization (try both languages)
        try:
            component_mapping = self._get_component_mappings("ru")
            # Add English mappings if needed
            en_mappings = self._get_component_mappings("en")
            component_mapping.update(en_mappings)
        except RuntimeError:
            # Fallback to hardcoded if assets not available
            component_mapping = {
                "аудио": "audio",
                "audio": "audio",
                "звук": "audio",
                "llm": "llm",
                "лл": "llm", 
                "модель": "llm",
                "распознавание": "asr",
                "asr": "asr",
                "распознавание речи": "asr",
                "голос": "tts",
                "tts": "tts",
                "синтез": "tts",
                "речь": "tts"
            }
        
        component_type = ""
        provider_name = ""
        
        # Find component type
        for key, value in component_mapping.items():
            if key in text_lower:
                component_type = value
                break
        
        # Extract provider name after "на"
        if "переключись на" in text_lower:
            parts = text_lower.split("переключись на", 1)
            if len(parts) > 1:
                provider_part = parts[1].strip()
                # Remove component type from provider name
                for key in component_mapping.keys():
                    provider_part = provider_part.replace(key, "").strip()
                provider_name = provider_part.split()[0] if provider_part else ""
        
        return component_type, provider_name
    
    def _parse_list_providers_command(self, text: str) -> str:
        """Parse component type from list providers command"""
        text_lower = text.lower()
        
        # Get component mappings from localization (try both languages)
        try:
            component_mapping = self._get_component_mappings("ru")
            # Add English mappings if needed
            en_mappings = self._get_component_mappings("en")
            component_mapping.update(en_mappings)
        except RuntimeError:
            # Fallback to hardcoded if assets not available
            component_mapping = {
                "аудио": "audio",
                "audio": "audio",
                "звук": "audio",
                "llm": "llm",
                "модель": "llm",
                "распознавание": "asr",
                "asr": "asr",
                "голос": "tts",
                "tts": "tts",
                "синтез": "tts"
            }
        
        # Find component type
        for key, value in component_mapping.items():
            if key in text_lower:
                return value
        
        return ""
    
    async def _get_component(self, component_type: str):
        """Get a controllable component by type via the injected registry (QUAL-24).

        The registry port is injected by the application; the domain never reaches
        into core for it.
        """
        if component_type not in self._components:
            if self._component_registry is None:
                self.logger.error(f"No component registry injected; cannot get {component_type} component")
                return None
            try:
                self._components[component_type] = self._component_registry.get_component(component_type)
            except Exception as e:
                self.logger.error(f"Failed to get {component_type} component: {e}")
                return None

        return self._components[component_type]
        
    def _error_result(self, context: UnifiedConversationContext, error: str) -> IntentResult:
        """Create error result with language awareness"""
        language = context.language
        error_text = self._get_template("provider_control_error", language, error=error)

        return IntentResult(
            text=error_text,
            should_speak=True,
            metadata={
                "error": error,
                "language": language
            },
            success=False
        )

    def _get_template(self, template_name: str, language: str, **format_args) -> str:
        """Get template from asset loader - raises a fatal error if not available (QUAL-38:
        provider-control responses are externalized like every other handler's)."""
        if not self.has_asset_loader():
            raise RuntimeError(
                f"ProviderControlIntentHandler: Asset loader not initialized. "
                f"Cannot access template '{template_name}' for language '{language}'."
            )
        template_content = self.asset_loader.get_template("provider_control", template_name, language)
        if template_content is None:
            raise RuntimeError(
                f"ProviderControlIntentHandler: Required template '{template_name}' for language "
                f"'{language}' not found in assets/templates/provider_control_handler/{language}.yaml."
            )
        try:
            return template_content.format(**format_args)
        except (KeyError, ValueError) as e:
            raise RuntimeError(f"ProviderControlIntentHandler: template '{template_name}' format error: {e}")


    # Build dependency methods (TODO #5 Phase 2)
    # Configuration metadata: No configuration needed
    # This handler uses component registry and asset loader for provider mappings
    # No get_config_schema() method = no configuration required
