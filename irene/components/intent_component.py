"""
Intent Component - Intent system integration with component architecture

This component wraps the IntentHandlerManager and provides the intent system
(registry, orchestrator, handlers) as a unified component that can be
integrated into workflows and the component lifecycle.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Type, Union

from pydantic import BaseModel
from .base import Component
from ..core.interfaces.webapi import WebAPIPlugin
from ..intents.manager import IntentHandlerManager
from ..intents.registry import IntentRegistry
from ..intents.orchestrator import IntentOrchestrator
from ..core.intent_asset_loader import IntentAssetLoader
from ..config.models import IntentSystemConfig

logger = logging.getLogger(__name__)


class IntentComponent(Component, WebAPIPlugin):
    """
    Intent system component providing intent recognition and handling.
    
    Features:
    - Dynamic intent handler discovery and registration
    - Configuration-driven handler filtering
    - Intent orchestration and execution
    - Web API endpoints for intent management
    - Integration with workflow system
    """
    
    def __init__(self):
        super().__init__()
        self.handler_manager: Optional[IntentHandlerManager] = None
        self.intent_orchestrator: Optional[IntentOrchestrator] = None
        self.intent_registry: Optional[IntentRegistry] = None
        self._config: Optional[Union[Dict[str, Any], IntentSystemConfig]] = None
        # QUAL-42: LLM capability port, injected post-init; used by the donation translation endpoints.
        self._llm_component: Optional[Any] = None

    async def initialize(self, core) -> None:
        """Initialize the intent system with configuration-driven handler discovery"""
        await super().initialize(core)
        
        # Get intent system configuration (Phase 5: Use proper Pydantic IntentSystemConfig)
        intent_config = getattr(core.config, 'intent_system', None)
        
        # Configuration must be provided - no fallback defaults
        if not intent_config:
            raise ValueError("IntentComponent requires configuration from CoreConfig.intent_system")
        
        self._config = intent_config
        
        # Initialize intent handler manager (Phase 5: Pass full intent system config)
        self.handler_manager = IntentHandlerManager()
        # Extract handler configuration from IntentSystemConfig
        if isinstance(intent_config, dict):
            handler_config = intent_config.get("handlers", {})
        else:
            # For Pydantic IntentSystemConfig, convert IntentHandlerListConfig to dict
            handlers_obj = getattr(intent_config, "handlers", None)
            if handlers_obj:
                handler_config = {
                    "enabled": handlers_obj.enabled,
                    "disabled": handlers_obj.disabled,
                    "auto_discover": handlers_obj.auto_discover,
                    "discovery_paths": handlers_obj.discovery_paths,
                    "asset_validation": handlers_obj.asset_validation
                }
            else:
                handler_config = {}

        # QUAL-36: inject the ONE canonical language policy (CoreConfig top level) into the asset-loader
        # config so the handler-facing IntentAssetLoader derives its default/supported languages from the
        # single source instead of its own hardcoded "ru"/["ru","en"] dataclass defaults.
        asset_validation = dict(handler_config.get("asset_validation", {}) or {})
        asset_validation.setdefault("default_language", core.config.default_language)
        asset_validation.setdefault("supported_languages", list(core.config.supported_languages))
        handler_config["asset_validation"] = asset_validation

        # Phase 5: Pass full intent system config for handler-specific configurations
        await self.handler_manager.initialize(handler_config, intent_system_config=intent_config)
        
        # Get registry and orchestrator from manager
        self.intent_registry = self.handler_manager.get_registry()
        self.intent_orchestrator = self.handler_manager.get_orchestrator()
        
        # NOTE: Component dependencies will be injected during post-initialization coordination
        # This ensures all components are available before dependency injection
        
        # Validate initialization results
        await self._validate_initialization_results()
        
        # Log initialization status  
        handlers = self.handler_manager.get_handlers()
        donations = self.handler_manager.get_donations()
        logger.info(f"Intent component initialized with {len(handlers)} handlers: {list(handlers.keys())}")
        logger.info(f"Loaded {len(donations)} JSON donations for donation-driven execution")
    
    async def shutdown(self) -> None:
        """Shutdown intent component and clean up handler resources"""
        await super().shutdown()
        
        # Clean up timeout tasks from all handlers
        if self.handler_manager and self.handler_manager.get_handlers():
            cleanup_tasks = []
            for handler_name, handler in self.handler_manager.get_handlers().items():
                if hasattr(handler, 'cleanup_timeout_tasks'):
                    cleanup_tasks.append(handler.cleanup_timeout_tasks())
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
                logger.info("Cleaned up timeout tasks from all intent handlers")

        # Clear handlers and reset the intent system
        if self.handler_manager:
            self.handler_manager._handler_instances.clear()
            self.handler_manager._handler_classes.clear()

        self.intent_orchestrator = None
        self.intent_registry = None
        self.handler_manager = None

        logger.info("Intent component shutdown completed")
    
    def set_context_manager(self, context_manager: Any) -> None:
        """Set the context manager on all intent handlers for fire-and-forget action tracking."""
        if self.handler_manager:
            self.handler_manager.set_context_manager(context_manager)
            logger.info("Context manager injected into intent handlers for fire-and-forget action tracking")
        
    def get_enabled_handler_names(self) -> List[str]:
        """
        Get list of enabled intent handler names.
        
        Returns:
            List of enabled handler names
        """
        if self.handler_manager:
            return list(self.handler_manager.get_handlers().keys())
        return []
    
    def get_enabled_handler_donations(self) -> Dict[str, Any]:
        """
        Get donations for enabled intent handlers.
        
        Returns:
            Dictionary of handler donations
        """
        if self.handler_manager:
            return self.handler_manager.get_donations()
        return {}
    
    async def _validate_initialization_results(self) -> None:
        """
        Validate that initialization completed successfully with comprehensive checks.
        """
        try:
            # Check that handler manager was created
            if not self.handler_manager:
                raise RuntimeError("IntentHandlerManager was not initialized")
            
            # Check that registry and orchestrator were created
            if not self.intent_registry:
                raise RuntimeError("Intent registry was not initialized")
            
            if not self.intent_orchestrator:
                raise RuntimeError("Intent orchestrator was not initialized")

            if self._config is None:
                raise RuntimeError("Intent configuration was not initialized")

            # Get enabled handlers from configuration
            if isinstance(self._config, dict):
                enabled_config = self._config.get("handlers", {}).get("enabled", [])
                disabled_config = self._config.get("handlers", {}).get("disabled", [])
            else:
                enabled_config = self._config.handlers.enabled
                disabled_config = self._config.handlers.disabled
            
            expected_handlers = [h for h in enabled_config if h not in disabled_config]
            
            # Check that expected handlers were loaded
            actual_handlers = self.get_enabled_handler_names()
            
            if not actual_handlers:
                raise RuntimeError("No intent handlers were successfully loaded")
            
            missing_handlers = set(expected_handlers) - set(actual_handlers)
            if missing_handlers:
                logger.error(f"Expected handlers not loaded: {missing_handlers}")
                logger.error(f"Configuration enabled: {enabled_config}")
                logger.error(f"Configuration disabled: {disabled_config}")
                logger.error(f"Actually loaded: {actual_handlers}")
                raise RuntimeError(f"Critical intent handlers failed to load: {missing_handlers}")
            
            # Check that donations were loaded
            donations = self.get_enabled_handler_donations()
            if not donations:
                raise RuntimeError("No intent handler donations were loaded")
            
            missing_donations = set(actual_handlers) - set(donations.keys())
            if missing_donations:
                logger.warning(f"Handlers missing donations: {missing_donations}")
                # This is a warning, not a fatal error
            
            # Validate registry has patterns
            if hasattr(self.intent_registry, 'handlers') and not self.intent_registry.handlers:
                logger.warning("Intent registry has no registered handlers")
            
            logger.info("✅ Intent component initialization validation passed")
            
        except Exception as e:
            logger.error(f"❌ Intent component initialization validation failed: {e}")
            raise RuntimeError(f"Intent component failed validation: {e}")
        
    # NOTE: This method has been replaced by post_initialize_handler_dependencies()
    # which is called during post-initialization coordination to ensure proper timing
    # 
    # async def _inject_handler_dependencies(self, core) -> None:
    #     # This method had timing issues because it ran during component initialization
    #     # when other components (like LLM) might not be available yet.
    #     # Replaced by post_initialize_handler_dependencies() for proper deferred injection.

    async def post_initialize_handler_dependencies(self, component_manager) -> None:
        """
        Post-initialization method to inject component dependencies into intent handlers.
        
        This method is called during post-initialization coordination after all components
        are fully initialized, ensuring proper dependency injection timing.
        
        Args:
            component_manager: The component manager containing all initialized components
        """
        # QUAL-24: handlers depend only on the domain-owned ports in
        # `irene/intents/ports.py`; here the application injects the real
        # components (which satisfy those Protocols structurally) inward, so the
        # domain never reaches into core via get_core(). Map: handler entry-point
        # name -> (handler attribute, component name).
        capability_ports = {
            'conversation': ('llm_component', 'llm'),
            'translation_handler': ('_llm_component', 'llm'),
            'text_enhancement_handler': ('_llm_component', 'llm'),
            'voice_synthesis_handler': ('_tts_component', 'tts'),
            'audio_playback_handler': ('_audio_component', 'audio'),
            'speech_recognition_handler': ('_asr_component', 'asr'),
        }
        try:
            logger.info("Starting intent handler capability-port injection (post-initialization)...")

            # Get available components - all should be initialized at this point
            components = component_manager.get_components()
            # QUAL-42: keep the LLM port for the donation translation/validation endpoints (graceful if absent).
            self._llm_component = components.get('llm')
            if self.handler_manager is None:
                raise RuntimeError("IntentHandlerManager was not initialized")
            handlers = self.handler_manager.get_handlers()

            injection_results = []

            for handler_name, handler in handlers.items():
                if handler_name in capability_ports:
                    attr, comp_name = capability_ports[handler_name]
                    component = components.get(comp_name)
                    setattr(handler, attr, component)
                    injection_results.append(
                        f"{handler_name}: {comp_name} {'injected' if component else 'unavailable'}"
                    )
                elif handler_name == 'provider_control_handler' and hasattr(handler, 'set_component_registry'):
                    # provider_control manages providers across ALL component types -> registry port
                    handler.set_component_registry(component_manager)
                    injection_results.append(f"{handler_name}: component registry injected")

            logger.info(f"Intent handler capability-port injection completed: {injection_results}")

        except Exception as e:
            logger.error(f"Failed to inject intent handler capability ports during post-initialization: {e}")
            # Don't re-raise - this is graceful degradation

    def get_providers_info(self) -> str:
        """Implementation of abstract method - Intent system doesn't use traditional providers"""
        if not self.handler_manager:
            return "Система интентов не инициализирована"
        
        handlers = self.handler_manager.get_handlers()
        donations = self.handler_manager.get_donations()
        
        info_lines = [f"Система обработки интентов ({len(handlers)} обработчиков):"]
        for name, handler in handlers.items():
            status = "✓"
            domains = getattr(handler, 'get_supported_domains', lambda: ["general"])()
            info_lines.append(f"  {status} {name}: {', '.join(domains[:2])}")
        
        info_lines.append(f"Загружено JSON-пожертвований: {len(donations)}")
        info_lines.append("Используется система обработчиков, а не провайдеров")
        
        return "\n".join(info_lines)
    
    # PluginInterface implementation (required by WebAPIPlugin)
    @property
    def name(self) -> str:
        """Get plugin name"""
        return "intent_system"
    
    @property
    def version(self) -> str:
        """Get plugin version"""
        return "1.0.0"
    
    @property
    def description(self) -> str:
        """Get plugin description"""
        return "Intent recognition and handling system with dynamic handler discovery"

    # ============================================================
    # QUAL-42: LLM-backed translation validation & service helpers
    # ============================================================

    async def _pick_llm_provider(self, requested: Optional[str]) -> Optional[str]:
        """Pick a usable real (non-stub, API-key-present) LLM provider, preferring the requested one, then the
        configured default, then deepseek. Returns None when no real LLM is available."""
        llm = self._llm_component
        if llm is None:
            return None
        try:
            if not await llm.is_available():
                return None
        except Exception:
            return None
        real = [n for n, p in getattr(llm, 'providers', {}).items() if not getattr(p, 'is_stub', False)]
        if not real:
            return None
        if requested and requested in real:
            return requested
        default = getattr(llm, 'default_provider', None)
        if default in real:
            return default
        if 'deepseek' in real:
            return 'deepseek'
        return real[0]

    @staticmethod
    def _parse_json_blob(text: Optional[str]) -> Optional[dict]:
        """Best-effort JSON extraction from an LLM reply (tolerates ```json fences / surrounding prose)."""
        import json, re
        if not text:
            return None
        t = text.strip()
        if t.startswith('```'):
            t = re.sub(r'^```[a-zA-Z]*\n?', '', t)
            t = re.sub(r'\n?```$', '', t).strip()
        start, end = t.find('{'), t.rfind('}')
        if start == -1 or end == -1 or end < start:
            return None
        try:
            return json.loads(t[start:end + 1])
        except Exception:
            return None

    async def _llm_json(self, provider: str, system: str, user: str) -> Optional[dict]:
        if self._llm_component is None:
            return None
        raw = await self._llm_component.generate_response(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            provider=provider,
        )
        return self._parse_json_blob(raw)

    async def _llm_validate_translations(self, provider: str, contract: Dict[str, Any],
                                         phrasing: Dict[str, Any]) -> List[Dict[str, str]]:
        """Ask the LLM to find meaning/consistency problems across a handler's per-language phrasing."""
        import json
        methods = [f"{m['method_name']}#{m['intent_suffix']}" for m in contract.get('method_donations', [])]
        data: Dict[str, Any] = {"methods": methods, "languages": {}}
        for lang, doc in phrasing.items():
            data["languages"][lang] = {
                f"{m['method_name']}#{m['intent_suffix']}": {
                    "phrases": m.get('phrases') or [],
                    "choice_surfaces": {p['name']: p.get('choice_surfaces') or {}
                                        for p in m.get('parameters', []) if p.get('choice_surfaces')},
                } for m in doc.get('method_donations', [])
            }
        system = (
            "You are a localization QA reviewer for a voice assistant. For each handler method you are given the "
            "example phrases users say and the spoken surface forms for choice values, per language. Find problems: "
            "(1) a phrase that does not match its method's meaning; (2) phrasings that contradict each other across "
            "languages; (3) a choice surface that mistranslates the canonical option; (4) a language whose phrasing "
            "is missing or clearly incomplete. Respond with ONLY JSON: "
            '{"issues":[{"language":"..","method_key":"..","severity":"error|warning|info","message":".."}]}. '
            "Use an empty list when everything is consistent."
        )
        result = await self._llm_json(provider, system, json.dumps(data, ensure_ascii=False))
        issues: List[Dict[str, str]] = []
        if isinstance(result, dict):
            for it in (result.get('issues') or []):
                if isinstance(it, dict):
                    issues.append({
                        "language": str(it.get('language', '')),
                        "method_key": str(it.get('method_key', '')),
                        "severity": str(it.get('severity', 'warning')),
                        "message": str(it.get('message', '')),
                    })
        return issues

    async def _llm_translate(self, provider: str, source_lang: str, target_lang: str,
                             src_phrases: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Ask the LLM to translate per-method example phrases from source to target language."""
        import json
        system = (
            f"You translate voice-assistant example phrases from {source_lang} to {target_lang}. Keep them "
            "natural, in the imperative, and varied (a user can phrase a command several ways); preserve any "
            "{placeholder} tokens verbatim. Respond with ONLY JSON: "
            '{"translations":[{"method_key":"..","suggested_phrases":["..",".."]}]}.'
        )
        user = json.dumps({"source_language": source_lang, "target_language": target_lang,
                           "methods": src_phrases}, ensure_ascii=False)
        result = await self._llm_json(provider, system, user)
        out: Dict[str, List[str]] = {}
        if isinstance(result, dict):
            for t in (result.get('translations') or []):
                if isinstance(t, dict) and t.get('method_key'):
                    out[str(t['method_key'])] = [str(p) for p in (t.get('suggested_phrases') or [])
                                                 if isinstance(p, str)]
        return out

    def get_router(self) -> Optional[Any]:
        """Get FastAPI router for Web API integration using centralized schemas"""
        try:
            from fastapi import APIRouter, HTTPException, Body
            from ..api.schemas import (
                IntentSystemStatusResponse, IntentHandlersResponse, IntentHandlerInfo,
                IntentActionCancelRequest, IntentActionResponse, IntentActiveActionsResponse,
                IntentRegistryResponse, IntentReloadResponse,
                # Language-aware donation management schemas (Phase 3)
                DonationContractResponse, DonationContractUpdateResponse,
                DonationHandlerListResponse, HandlerLanguageInfo, LanguageDonationContentResponse,
                LanguageDonationUpdateRequest, LanguageDonationUpdateResponse,
                LanguageDonationValidationRequest, LanguageDonationValidationResponse,
                CreateLanguageRequest, CreateLanguageResponse, DeleteLanguageResponse,
                ReloadDonationResponse, CrossLanguageValidation, LanguageDonationMetadata,
                # Schema-related types still needed
                DonationSchemaResponse, ValidationError, ValidationWarning,
                # Phase 4: Cross-language validation schemas
                CrossLanguageValidationResponse, ValidationReportSchema, CompletenessReportSchema,
                # QUAL-42: contract↔code wiring + LLM translation validation/service
                ContractValidationResponse, ContractWiringReportSchema,
                TranslationValidationRequest, TranslationValidationResponse, TranslationIssueSchema,
                TranslateRequest, TranslateResponse, TranslatedMethodSchema,
                # Phase 6: Template management schemas
                TemplateContentResponse, TemplateUpdateRequest, TemplateUpdateResponse,
                TemplateValidationRequest, TemplateValidationResponse,
                # Phase 7: Prompt management schemas  
                PromptContentResponse, PromptUpdateRequest, PromptUpdateResponse,
                PromptValidationRequest, PromptValidationResponse, PromptDefinition, PromptMetadata,
                CreatePromptLanguageRequest, CreatePromptLanguageResponse, DeletePromptLanguageResponse,
                PromptHandlerListResponse,
                CreateTemplateLanguageRequest, CreateTemplateLanguageResponse, DeleteTemplateLanguageResponse,
                TemplateHandlerListResponse, TemplateMetadata,
                # Phase 8: Localization management schemas
                LocalizationContentResponse, LocalizationUpdateRequest, LocalizationUpdateResponse,
                LocalizationValidationRequest, LocalizationValidationResponse, LocalizationMetadata,
                CreateLocalizationLanguageRequest, CreateLocalizationLanguageResponse, DeleteLocalizationLanguageResponse,
                LocalizationDomainListResponse, DomainLanguageInfo,
                # Phase 1: Configuration response schemas
                IntentSystemConfigureResponse
            )
            from ..config.models import IntentSystemConfig
            
            router = APIRouter()
            
            @router.get("/status", response_model=IntentSystemStatusResponse)
            async def get_intent_status():
                """Get intent system status"""
                status_data = await self.get_status()
                return IntentSystemStatusResponse(
                    success=True,
                    **status_data
                )
            
            @router.get("/handlers", response_model=IntentHandlersResponse)
            async def get_intent_handlers():
                """Get available intent handlers"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                handlers_info = {}
                donations = self.handler_manager.get_donations()
                
                for name, handler in self.handler_manager.get_handlers().items():
                    handler_info_data = {
                        "class": handler.__class__.__name__,
                        "domains": getattr(handler, 'get_supported_domains', lambda: [])(),
                        "actions": getattr(handler, 'get_supported_actions', lambda: [])(),
                        "available": await handler.is_available() if hasattr(handler, 'is_available') else True,
                        "capabilities": getattr(handler, 'get_capabilities', lambda: {})(),
                        "has_donation": hasattr(handler, 'has_donation') and handler.has_donation(),
                        "supports_donation_routing": hasattr(handler, 'execute_with_donation_routing')
                    }
                    
                    # Add donation information if available
                    if name in donations:
                        donation = donations[name]
                        handler_info_data["donation"] = {
                            "domain": donation.handler_domain,
                            "methods_count": len(donation.method_donations),
                            "methods": [
                                {
                                    "name": method.method_name,
                                    "intent_suffix": method.intent_suffix,
                                    "full_intent": f"{donation.handler_domain}.{method.intent_suffix}",
                                    "parameters_count": len(method.parameters),
                                    "phrases_count": len(method.phrases)
                                }
                                for method in donation.method_donations
                            ],
                            "global_parameters_count": len(donation.global_parameters)
                        }
                    
                    handlers_info[name] = IntentHandlerInfo(**handler_info_data)
                
                return IntentHandlersResponse(
                    success=True,
                    handlers=handlers_info
                )
            
            @router.post("/actions/cancel", response_model=IntentActionResponse)
            async def cancel_action_endpoint(request: IntentActionCancelRequest):
                """Cancel an active fire-and-forget action"""
                try:
                    # This would need session_id parameter or session management
                    # For now, return method availability info
                    return IntentActionResponse(
                        success=True,
                        message="Action cancellation endpoint available",
                        domain=request.domain,
                        reason=request.reason,
                        note="Full implementation requires session context"
                    )
                except Exception as e:
                    raise HTTPException(500, f"Error cancelling action: {str(e)}")
            
            @router.get("/actions/active", response_model=IntentActiveActionsResponse)
            async def get_active_actions_endpoint():
                """Get list of active fire-and-forget actions"""
                try:
                    # This would need session context to be useful
                    return IntentActiveActionsResponse(
                        success=True,
                        message="Active actions endpoint available",
                        note="Full implementation requires session context"
                    )
                except Exception as e:
                    raise HTTPException(500, f"Error getting active actions: {str(e)}")

            @router.get("/registry", response_model=IntentRegistryResponse)
            async def get_intent_registry():
                """Get intent registry patterns"""
                if not self.intent_registry:
                    raise HTTPException(503, "Intent registry not initialized")
                
                handlers = await self.intent_registry.get_all_handlers()
                patterns_info = {}
                
                for pattern, handler in handlers.items():
                    patterns_info[pattern] = {
                        "handler_class": handler.__class__.__name__,
                        "metadata": self.intent_registry.get_handler_info(pattern)
                    }
                
                return IntentRegistryResponse(
                    success=True,
                    patterns=patterns_info
                )
            
            # ============================================================
            # DONATION SCHEMA ENDPOINT
            # ============================================================
            
            @router.get("/schema", response_model=DonationSchemaResponse)
            async def get_donation_schema():
                """QUAL-29 (v1.1): return BOTH donation schemas — the language-neutral `contract` and the
                per-language `language` (phrasing) — under `json_schema = {contract, language}`."""
                try:
                    asset_loader = self.handler_manager._asset_loader if self.handler_manager else None
                    assets_root = asset_loader.assets_root if asset_loader else Path("assets")
                    schemas = {}
                    for key, fname in (("contract", "donation_contract_v1.1.json"),
                                       ("language", "donation_language_v1.1.json")):
                        path = assets_root / fname
                        if path.exists():
                            schemas[key] = json.loads(path.read_text(encoding="utf-8"))
                    return DonationSchemaResponse(
                        success=True,
                        json_schema=schemas,
                        schema_version="1.1",
                        supported_versions=["1.1"]
                    )
                except Exception as e:
                    raise HTTPException(500, f"Failed to load donation schema: {str(e)}")
            
            # ============================================================
            # EXISTING ENDPOINTS
            # ============================================================
            
            @router.post("/reload", response_model=IntentReloadResponse)
            async def reload_intent_handlers():
                """Reload intent handlers with current configuration"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    # Handle both dict and Pydantic config objects
                    if isinstance(self._config, dict):
                        handlers_config = self._config.get("handlers", {})
                    else:
                        handlers_config = getattr(self._config, "handlers", {})
                    await self.handler_manager.reload_handlers(handlers_config)
                    
                    # Update references
                    self.intent_registry = self.handler_manager.get_registry()
                    self.intent_orchestrator = self.handler_manager.get_orchestrator()
                    
                    handlers = self.handler_manager.get_handlers()
                    return IntentReloadResponse(
                        success=True,
                        status="reloaded",
                        handlers_count=len(handlers),
                        handlers=list(handlers.keys())
                    )
                except Exception as e:
                    logger.error(f"Failed to reload intent handlers: {e}")
                    return IntentReloadResponse(
                        success=False,
                        status="failed",
                        handlers_count=0,
                        handlers=[],
                        error=f"Reload failed: {str(e)}"
                    )
            
            # ============================================================
            # LANGUAGE-AWARE DONATION ENDPOINTS
            # ============================================================
            
            @router.get("/donations", response_model=DonationHandlerListResponse)
            async def list_donation_handlers():
                """List all handlers with language information"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    handlers_languages = asset_loader.get_all_handlers_with_languages()
                    
                    handlers_info = []
                    for handler_name, languages in handlers_languages.items():
                        handlers_info.append(HandlerLanguageInfo(
                            handler_name=handler_name,
                            languages=languages,
                            total_languages=len(languages),
                            supported_languages=asset_loader.config.supported_languages,
                            default_language=asset_loader.config.default_language
                        ))
                    
                    return DonationHandlerListResponse(
                        success=True,
                        handlers=handlers_info,
                        total_handlers=len(handlers_info)
                    )
                except Exception as e:
                    raise HTTPException(500, f"Failed to list donation handlers: {str(e)}")
            
            # ============================================================
            # Phase 4: Cross-Language Validation and Synchronization
            # ============================================================
            
            @router.get("/donations/{handler_name}/cross-validation", response_model=CrossLanguageValidationResponse)
            async def get_cross_language_validation(handler_name: str):
                """Get cross-language validation report for a handler"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    
                    # Import the validator
                    from ..core.cross_language_validator import CrossLanguageValidator
                    validator = CrossLanguageValidator(asset_loader.assets_root, asset_loader)
                    
                    # Run both validations
                    parameter_report = validator.validate_parameter_consistency(handler_name)
                    completeness_report = validator.validate_method_completeness(handler_name)
                    
                    # Convert to schema objects
                    
                    parameter_schema = ValidationReportSchema(
                        handler_name=parameter_report.handler_name,
                        languages_checked=parameter_report.languages_checked,
                        parameter_consistency=parameter_report.parameter_consistency,
                        missing_parameters=parameter_report.missing_parameters,
                        extra_parameters=parameter_report.extra_parameters,
                        type_mismatches=parameter_report.type_mismatches,
                        warnings=parameter_report.warnings,
                        timestamp=parameter_report.timestamp
                    )
                    
                    completeness_schema = CompletenessReportSchema(
                        handler_name=completeness_report.handler_name,
                        languages_checked=completeness_report.languages_checked,
                        method_completeness=completeness_report.method_completeness,
                        missing_methods=completeness_report.missing_methods,
                        extra_methods=completeness_report.extra_methods,
                        all_methods=list(completeness_report.all_methods),
                        method_counts_by_language=completeness_report.method_counts_by_language,
                        warnings=completeness_report.warnings,
                        timestamp=completeness_report.timestamp
                    )
                    
                    return CrossLanguageValidationResponse(
                        success=True,
                        validation_type="comprehensive",
                        parameter_report=parameter_schema,
                        completeness_report=completeness_schema
                    )
                    
                except Exception as e:
                    raise HTTPException(500, f"Failed to validate cross-language consistency: {str(e)}")
            
            # QUAL-43: the rule-based POST /donations/{handler}/suggest-translations was removed — it only counted
            # phrase gaps and is superseded by the LLM translation service (POST .../translate, below).

            # ============================================================
            # QUAL-42: contract↔code wiring report + LLM translation validation/service
            # ============================================================

            @router.get("/donations/validation", response_model=ContractValidationResponse)
            async def get_contract_validation():
                """The contract↔code wiring report computed at startup (every contract's methods+params
                reconciled against the Python handler). Unwired methods fail boot, so a running system always
                has `ok=True` for errors; this surfaces the soft warnings (unread params, undeclared handler
                methods) to the UI."""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                asset_loader = self._require_asset_loader()
                report = asset_loader.contract_validation_report
                if report is None:
                    # Not computed at load (e.g. wiring validation disabled) — compute on demand.
                    from ..core.contract_validator import validate_contracts
                    report = validate_contracts(asset_loader.donations)
                return ContractValidationResponse(
                    success=True,
                    ok=report.ok,
                    total_errors=report.total_errors,
                    total_warnings=report.total_warnings,
                    timestamp=report.timestamp,
                    handlers=[ContractWiringReportSchema(
                        handler_name=h.handler_name, handler_class=h.handler_class,
                        errors=h.errors, warnings=h.warnings,
                        methods_checked=h.methods_checked, params_checked=h.params_checked,
                    ) for h in report.handlers],
                )

            @router.post("/donations/{handler_name}/validate-translation",
                         response_model=TranslationValidationResponse)
            async def validate_translation(handler_name: str, request: TranslationValidationRequest):
                """LLM-validate that a handler's per-language phrasing is meaningful and non-contradicting.
                Requires a real (non-stub) LLM with an API key; if none is configured the response reports
                `llm_available=false` and asks the user to validate manually."""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                asset_loader = self._require_asset_loader()
                contract = asset_loader.get_contract_for_editing(handler_name)
                if contract is None:
                    raise HTTPException(404, f"No contract.json for handler '{handler_name}'")

                provider = await self._pick_llm_provider(request.provider)
                if provider is None:
                    return TranslationValidationResponse(
                        success=True, handler_name=handler_name, llm_available=False, provider=None,
                        message=("No LLM with an API key is configured (set one of DEEPSEEK_API_KEY / "
                                 "OPENAI_API_KEY / ANTHROPIC_API_KEY in .env). Translation quality must be "
                                 "validated manually."),
                        issues=[])

                languages = asset_loader.get_available_languages_for_handler(handler_name)
                phrasing = {lang: asset_loader.get_language_phrasing_for_editing(handler_name, lang) or {}
                            for lang in languages}
                try:
                    issues = await self._llm_validate_translations(provider, contract, phrasing)
                except Exception as e:
                    raise HTTPException(502, f"LLM translation validation failed: {e}")
                return TranslationValidationResponse(
                    success=True, handler_name=handler_name, llm_available=True, provider=provider,
                    message=("No translation issues found" if not issues
                             else f"{len(issues)} translation issue(s) found"),
                    issues=[TranslationIssueSchema(**i) for i in issues])

            @router.post("/donations/{handler_name}/translate", response_model=TranslateResponse)
            async def translate_donation(handler_name: str, request: TranslateRequest):
                """LLM translation *service*: suggest target-language phrases for a handler's methods, from the
                source language. Requires a real LLM; otherwise reports `llm_available=false` for manual work."""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                asset_loader = self._require_asset_loader()
                contract = asset_loader.get_contract_for_editing(handler_name)
                if contract is None:
                    raise HTTPException(404, f"No contract.json for handler '{handler_name}'")

                source = asset_loader.get_language_phrasing_for_editing(handler_name, request.source_language)
                if not source:
                    raise HTTPException(404, f"No '{request.source_language}' phrasing for handler '{handler_name}'")

                provider = await self._pick_llm_provider(request.provider)
                if provider is None:
                    return TranslateResponse(
                        success=True, handler_name=handler_name, source_language=request.source_language,
                        target_language=request.target_language, llm_available=False, provider=None,
                        message=("No LLM with an API key is configured (set one of DEEPSEEK_API_KEY / "
                                 "OPENAI_API_KEY / ANTHROPIC_API_KEY in .env). Translate manually."),
                        translations=[])

                # method_key -> source phrases
                src_phrases = {f"{m['method_name']}#{m['intent_suffix']}": (m.get('phrases') or [])
                               for m in source.get('method_donations', [])}
                if request.method_keys:
                    src_phrases = {k: v for k, v in src_phrases.items() if k in set(request.method_keys)}
                try:
                    suggestions = await self._llm_translate(
                        provider, request.source_language, request.target_language, src_phrases)
                except Exception as e:
                    raise HTTPException(502, f"LLM translation failed: {e}")
                return TranslateResponse(
                    success=True, handler_name=handler_name, source_language=request.source_language,
                    target_language=request.target_language, llm_available=True, provider=provider,
                    message=f"Translated {len(suggestions)} method(s) to '{request.target_language}'",
                    translations=[TranslatedMethodSchema(
                        method_key=k, source_phrases=src_phrases.get(k, []), suggested_phrases=v)
                        for k, v in suggestions.items()])

            @router.get("/donations/{handler_name}/languages", response_model=List[str])
            async def get_handler_languages(handler_name: str):
                """Get available languages for a handler"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    languages = asset_loader.get_available_languages_for_handler(handler_name)
                    
                    if not languages:
                        raise HTTPException(404, f"No language files found for handler '{handler_name}'")
                    
                    return languages
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(500, f"Failed to get handler languages: {str(e)}")
            
            @router.get("/donations/{handler_name}/contract", response_model=DonationContractResponse)
            async def get_donation_contract(handler_name: str):
                """QUAL-29 (v1.1): the language-neutral contract for a handler — param core (name/type/required/
                canonical choices/min-max/entity_type), per-method room_context, and the method list."""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                asset_loader = self._require_asset_loader()
                contract = asset_loader.get_contract_for_editing(handler_name)
                if contract is None:
                    raise HTTPException(404, f"No contract.json for handler '{handler_name}'")
                return {"success": True, "handler_name": handler_name, "contract": contract,
                        "available_languages": asset_loader.get_available_languages_for_handler(handler_name)}

            @router.put("/donations/{handler_name}/contract", response_model=DonationContractUpdateResponse)
            async def update_donation_contract(handler_name: str, request: Dict[str, Any] = Body(...)):
                """Validate + save the language-neutral contract, then reload the unified donation. Body:
                {contract: {...}, validate_before_save?: bool, trigger_reload?: bool}."""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                asset_loader = self._require_asset_loader()
                contract = request.get("contract")
                if not isinstance(contract, dict):
                    raise HTTPException(400, "Body must contain a 'contract' object")

                errors, warnings = [], []
                if request.get("validate_before_save", True):
                    is_valid, error_list, warning_list = await asset_loader.validate_contract_data(handler_name, contract)
                    errors = [ValidationError(**e) for e in error_list]
                    warnings = [ValidationWarning(**w) for w in warning_list]
                    if not is_valid:
                        return {"success": False, "handler_name": handler_name, "validation_passed": False,
                                "reload_triggered": False, "errors": [e.dict() for e in errors],
                                "warnings": [w.dict() for w in warnings]}

                saved, backup_created = asset_loader.save_contract(handler_name, contract)
                if not saved:
                    raise HTTPException(500, "Failed to save contract.json")

                reload_triggered = False
                if request.get("trigger_reload", True):
                    try:
                        reload_triggered = await asset_loader.reload_unified_donation(handler_name)
                    except Exception as e:
                        logger.warning(f"Contract saved but reload failed: {e}")
                return {"success": True, "handler_name": handler_name, "validation_passed": True,
                        "reload_triggered": reload_triggered, "backup_created": backup_created,
                        "errors": [], "warnings": [w.dict() for w in warnings]}

            @router.get("/donations/{handler_name}/{language}", response_model=LanguageDonationContentResponse)
            async def get_language_donation(handler_name: str, language: str):
                """Get language-specific donation content for editing"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    
                    # QUAL-29 (v1.1): a language file is phrasing-only; the param core lives in contract.json
                    # (see GET /donations/{handler}/contract).
                    phrasing = asset_loader.get_language_phrasing_for_editing(handler_name, language)
                    if phrasing is None:
                        raise HTTPException(404, f"Language '{language}' not found for handler '{handler_name}'")
                    
                    # Get metadata
                    asset_handler_name = asset_loader._get_asset_handler_name(handler_name)
                    lang_file = asset_loader.assets_root / "donations" / asset_handler_name / f"{language}.json"
                    
                    if not lang_file.exists():
                        raise HTTPException(404, f"Language file not found: {lang_file}")
                    
                    stat = lang_file.stat()
                    metadata = LanguageDonationMetadata(
                        file_path=f"{asset_handler_name}/{language}.json",
                        language=language,
                        file_size=stat.st_size,
                        last_modified=stat.st_mtime
                    )
                    
                    # Get available languages
                    available_languages = asset_loader.get_available_languages_for_handler(handler_name)
                    
                    # Get cross-language validation
                    cross_validation = asset_loader.validate_cross_language_consistency(handler_name)
                    
                    return LanguageDonationContentResponse(
                        success=True,
                        handler_name=handler_name,
                        language=language,
                        donation_data=phrasing,
                        metadata=metadata,
                        available_languages=available_languages,
                        cross_language_validation=CrossLanguageValidation(**cross_validation)
                    )
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(500, f"Failed to get language donation: {str(e)}")
            
            @router.put("/donations/{handler_name}/{language}", response_model=LanguageDonationUpdateResponse)
            async def update_language_donation(handler_name: str, language: str, request: LanguageDonationUpdateRequest):
                """Update language-specific donation and trigger unified reload"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    validation_passed = True
                    errors = []
                    warnings = []
                    
                    # QUAL-29 (v1.1): validate + save PHRASING (no param core — that lives in contract.json).
                    if request.validate_before_save:
                        is_valid, error_list, warning_list = await asset_loader.validate_phrasing_data(
                            handler_name, request.donation_data
                        )
                        validation_passed = is_valid
                        errors = [ValidationError(**err) for err in error_list]
                        warnings = [ValidationWarning(**warn) for warn in warning_list]

                        if not is_valid:
                            return LanguageDonationUpdateResponse(
                                success=False,
                                handler_name=handler_name,
                                language=language,
                                validation_passed=False,
                                reload_triggered=False,
                                backup_created=False,
                                errors=errors,
                                warnings=warnings
                            )

                    saved, backup_created = asset_loader.save_language_phrasing(
                        handler_name, language, request.donation_data
                    )
                    if not saved:
                        raise HTTPException(500, "Failed to save language phrasing file")
                    
                    # Trigger unified donation reload if requested
                    reload_triggered = False
                    if request.trigger_reload:
                        try:
                            reload_success = await asset_loader.reload_unified_donation(handler_name)
                            if reload_success:
                                # Also trigger handler reload if this is an enabled handler
                                if isinstance(self._config, dict):
                                    handlers_config = self._config.get("handlers", {})
                                else:
                                    handlers_config = getattr(self._config, "handlers", {})
                                
                                enabled_handlers = handlers_config.get("enabled", [])
                                if handler_name in enabled_handlers:
                                    await self.handler_manager.reload_handlers(handlers_config)
                                    self.intent_registry = self.handler_manager.get_registry()
                                    self.intent_orchestrator = self.handler_manager.get_orchestrator()
                                
                                reload_triggered = True
                        except Exception as e:
                            logger.warning(f"Language donation saved but reload failed: {e}")
                    
                    return LanguageDonationUpdateResponse(
                        success=True,
                        handler_name=handler_name,
                        language=language,
                        validation_passed=validation_passed,
                        reload_triggered=reload_triggered,
                        backup_created=backup_created,
                        errors=errors,
                        warnings=warnings
                    )
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(500, f"Failed to update language donation: {str(e)}")
            
            @router.post("/donations/{handler_name}/{language}/validate", response_model=LanguageDonationValidationResponse)
            async def validate_language_donation(handler_name: str, language: str, request: LanguageDonationValidationRequest):
                """Validate language-specific donation without saving"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    
                    is_valid, error_list, warning_list = await asset_loader.validate_phrasing_data(
                        handler_name, request.donation_data
                    )

                    errors = [ValidationError(**err) for err in error_list]
                    warnings = [ValidationWarning(**warn) for warn in warning_list]

                    validation_types = ["v1.1-language-schema"]
                    
                    return LanguageDonationValidationResponse(
                        success=True,
                        handler_name=handler_name,
                        language=language,
                        is_valid=is_valid,
                        errors=errors,
                        warnings=warnings,
                        validation_types=validation_types
                    )
                except Exception as e:
                    raise HTTPException(500, f"Failed to validate language donation: {str(e)}")
            
            @router.delete("/donations/{handler_name}/{language}", response_model=DeleteLanguageResponse)
            async def delete_language(handler_name: str, language: str):
                """Delete a language file for a handler"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    asset_handler_name = asset_loader._get_asset_handler_name(handler_name)
                    lang_file = asset_loader.assets_root / "donations" / asset_handler_name / f"{language}.json"
                    
                    if not lang_file.exists():
                        raise HTTPException(404, f"Language '{language}' not found for handler '{handler_name}'")
                    
                    # Check if this is the last language
                    available_languages = asset_loader.get_available_languages_for_handler(handler_name)
                    if len(available_languages) <= 1:
                        raise HTTPException(400, "Cannot delete the last language file for a handler")
                    
                    lang_file.unlink()
                    
                    return DeleteLanguageResponse(
                        success=True,
                        handler_name=handler_name,
                        language=language,
                        deleted=True
                    )
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(500, f"Failed to delete language: {str(e)}")
            
            @router.post("/donations/{handler_name}/{language}/create", response_model=CreateLanguageResponse)
            async def create_language(handler_name: str, language: str, request: CreateLanguageRequest):
                """Create a new language file for a handler"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    asset_handler_name = asset_loader._get_asset_handler_name(handler_name)
                    lang_file = asset_loader.assets_root / "donations" / asset_handler_name / f"{language}.json"
                    
                    if lang_file.exists():
                        raise HTTPException(409, f"Language '{language}' already exists for handler '{handler_name}'")
                    
                    # QUAL-29 (v1.1): a new language file is PHRASING only; the method/param skeleton comes from
                    # the contract (joined by method_name#intent_suffix), so a blank template just lists the methods.
                    copied_from = None
                    if request.copy_from and not request.use_template:
                        source = asset_loader.get_language_phrasing_for_editing(handler_name, request.copy_from)
                        if source is None:
                            raise HTTPException(404, f"Source language '{request.copy_from}' not found")
                        saved, _ = asset_loader.save_language_phrasing(handler_name, language, source)
                        copied_from = request.copy_from
                    else:
                        contract = asset_loader.get_contract_for_editing(handler_name)
                        if not contract:
                            raise HTTPException(400, "Cannot create language file: handler has no contract.json")
                        template = {
                            "schema_version": "1.1",
                            "handler_domain": contract.get("handler_domain"),
                            "language": language,
                            "method_donations": [
                                {"method_name": m["method_name"], "intent_suffix": m["intent_suffix"], "phrases": []}
                                for m in contract.get("method_donations", [])
                            ],
                        }
                        saved, _ = asset_loader.save_language_phrasing(handler_name, language, template)
                    
                    if not saved:
                        raise HTTPException(500, "Failed to save new language file")
                    
                    return CreateLanguageResponse(
                        success=True,
                        handler_name=handler_name,
                        language=language,
                        created=True,
                        copied_from=copied_from
                    )
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(500, f"Failed to create language: {str(e)}")
            
            @router.post("/donations/{handler_name}/reload", response_model=ReloadDonationResponse)
            async def reload_handler_donation(handler_name: str):
                """Trigger unified donation reload for a handler"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    
                    # Get available languages before reload
                    available_languages = asset_loader.get_available_languages_for_handler(handler_name)
                    
                    # Reload unified donation
                    reloaded = await asset_loader.reload_unified_donation(handler_name)
                    
                    if reloaded:
                        # Also trigger handler reload if this is an enabled handler
                        if isinstance(self._config, dict):
                            handlers_config = self._config.get("handlers", {})
                        else:
                            handlers_config = getattr(self._config, "handlers", {})
                        
                        enabled_handlers = handlers_config.get("enabled", [])
                        if handler_name in enabled_handlers:
                            await self.handler_manager.reload_handlers(handlers_config)
                            self.intent_registry = self.handler_manager.get_registry()
                            self.intent_orchestrator = self.handler_manager.get_orchestrator()
                    
                    return ReloadDonationResponse(
                        success=True,
                        handler_name=handler_name,
                        reloaded=reloaded,
                        merged_languages=available_languages
                    )
                except Exception as e:
                    raise HTTPException(500, f"Failed to reload donation: {str(e)}")
            
            # ============================================================
            # TEMPLATE MANAGEMENT ENDPOINTS (Phase 6)
            # ============================================================
            
            @router.get("/templates", response_model=TemplateHandlerListResponse)
            async def get_template_handlers():
                """List all handlers with template language info"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    handlers_languages = asset_loader.get_handlers_with_templates()
                    
                    handlers_info = []
                    for handler_name, languages in handlers_languages.items():
                        handlers_info.append(HandlerLanguageInfo(
                            handler_name=handler_name,
                            languages=languages,
                            total_languages=len(languages),
                            supported_languages=asset_loader.config.supported_languages,
                            default_language=asset_loader.config.default_language
                        ))
                    
                    return TemplateHandlerListResponse(
                        success=True,
                        handlers=handlers_info,
                        total_handlers=len(handlers_info)
                    )
                except Exception as e:
                    raise HTTPException(500, f"Failed to get template handlers: {str(e)}")
            
            @router.get("/templates/{handler_name}/languages", response_model=List[str])
            async def get_template_handler_languages(handler_name: str):
                """Get available languages for a handler's templates"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    languages = asset_loader.get_available_template_languages_for_handler(handler_name)
                    
                    if not languages:
                        raise HTTPException(404, f"No template language files found for handler '{handler_name}'")
                    
                    return languages
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(500, f"Failed to get template handler languages: {str(e)}")
            
            @router.get("/templates/{handler_name}/{language}", response_model=TemplateContentResponse)
            async def get_language_template(handler_name: str, language: str):
                """Get language-specific template content for editing"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    
                    # Get language-specific template data
                    template_data = asset_loader.get_template_for_language_editing(handler_name, language)
                    if template_data is None:
                        raise HTTPException(404, f"Language '{language}' not found for handler '{handler_name}' templates")
                    
                    # Get metadata
                    asset_handler_name = asset_loader._get_asset_handler_name(handler_name)
                    lang_file = asset_loader.assets_root / "templates" / asset_handler_name / f"{language}.yaml"
                    
                    if not lang_file.exists():
                        raise HTTPException(404, f"Template language file not found: {lang_file}")
                    
                    stat = lang_file.stat()
                    metadata = TemplateMetadata(
                        file_path=f"{asset_handler_name}/{language}.yaml",
                        language=language,
                        file_size=stat.st_size,
                        last_modified=stat.st_mtime,
                        template_count=len(template_data) if isinstance(template_data, dict) else 0
                    )
                    
                    # Get available languages
                    available_languages = asset_loader.get_available_template_languages_for_handler(handler_name)
                    
                    # Schema info for template structure
                    schema_info = {
                        "expected_keys": list(template_data.keys()) if isinstance(template_data, dict) else [],
                        "key_types": {
                            key: type(value).__name__.lower() for key, value in template_data.items()
                        } if isinstance(template_data, dict) else {}
                    }
                    
                    return TemplateContentResponse(
                        success=True,
                        handler_name=handler_name,
                        language=language,
                        template_data=template_data,
                        metadata=metadata,
                        available_languages=available_languages,
                        schema_info=schema_info
                    )
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(500, f"Failed to get language template: {str(e)}")
            
            @router.put("/templates/{handler_name}/{language}", response_model=TemplateUpdateResponse)
            async def update_language_template(handler_name: str, language: str, request: TemplateUpdateRequest):
                """Update language-specific template and trigger reload"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    validation_passed = True
                    errors = []
                    warnings = []
                    
                    # Validate before saving if requested
                    if request.validate_before_save:
                        is_valid, error_list, warning_list = await asset_loader.validate_template_data(
                            handler_name, request.template_data
                        )
                        validation_passed = is_valid
                        errors = [ValidationError(**err) for err in error_list]
                        warnings = [ValidationWarning(**warn) for warn in warning_list]
                        
                        if not is_valid:
                            return TemplateUpdateResponse(
                                success=False,
                                handler_name=handler_name,
                                language=language,
                                validation_passed=False,
                                reload_triggered=False,
                                backup_created=False,
                                errors=errors,
                                warnings=warnings
                            )
                    
                    # Save template data
                    try:
                        saved, backup_created = asset_loader.save_template_for_language(handler_name, language, request.template_data)
                        if not saved:
                            raise HTTPException(500, "Failed to save template language file")
                    except Exception as e:
                        raise HTTPException(400, f"Invalid template data: {str(e)}")
                    
                    # Trigger template reload if requested
                    reload_triggered = False
                    if request.trigger_reload:
                        try:
                            reload_success = await asset_loader.reload_templates_for_handler(handler_name)
                            if reload_success:
                                reload_triggered = True
                        except Exception as e:
                            logger.warning(f"Template saved but reload failed: {e}")
                    
                    return TemplateUpdateResponse(
                        success=True,
                        handler_name=handler_name,
                        language=language,
                        validation_passed=validation_passed,
                        reload_triggered=reload_triggered,
                        backup_created=False,  # TODO: Implement backup functionality
                        errors=errors,
                        warnings=warnings
                    )
                    
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(500, f"Failed to update language template: {str(e)}")
            
            @router.post("/templates/{handler_name}/{language}/validate", response_model=TemplateValidationResponse)
            async def validate_language_template(handler_name: str, language: str, request: TemplateValidationRequest):
                """Validate language-specific template data without saving"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    
                    is_valid, error_list, warning_list = await asset_loader.validate_template_data(
                        handler_name, request.template_data
                    )
                    
                    errors = [ValidationError(**err) for err in error_list]
                    warnings = [ValidationWarning(**warn) for warn in warning_list]
                    
                    return TemplateValidationResponse(
                        success=True,
                        handler_name=handler_name,
                        language=language,
                        is_valid=is_valid,
                        errors=errors,
                        warnings=warnings,
                        validation_types=["yaml_structure", "template_types"]
                    )
                    
                except Exception as e:
                    raise HTTPException(500, f"Failed to validate template: {str(e)}")
            
            @router.delete("/templates/{handler_name}/{language}", response_model=DeleteTemplateLanguageResponse)
            async def delete_template_language(handler_name: str, language: str):
                """Delete language-specific template file"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    asset_handler_name = asset_loader._get_asset_handler_name(handler_name)
                    lang_file = asset_loader.assets_root / "templates" / asset_handler_name / f"{language}.yaml"
                    
                    if not lang_file.exists():
                        raise HTTPException(404, f"Template language file not found: {lang_file}")
                    
                    # Delete the file
                    lang_file.unlink()
                    
                    # Reload templates to update cache
                    await asset_loader.reload_templates_for_handler(handler_name)
                    
                    return DeleteTemplateLanguageResponse(
                        success=True,
                        handler_name=handler_name,
                        language=language,
                        deleted=True,
                        backup_created=False  # TODO: Implement backup functionality
                    )
                    
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(500, f"Failed to delete template language: {str(e)}")
            
            @router.post("/templates/{handler_name}/{language}", response_model=CreateTemplateLanguageResponse)
            async def create_template_language(handler_name: str, language: str, request: CreateTemplateLanguageRequest):
                """Create new language file for template"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    asset_handler_name = asset_loader._get_asset_handler_name(handler_name)
                    lang_file = asset_loader.assets_root / "templates" / asset_handler_name / f"{language}.yaml"
                    
                    if lang_file.exists():
                        raise HTTPException(409, f"Template language file already exists: {lang_file}")
                    
                    # Create new template data
                    template_data = {}
                    copied_from = None
                    
                    if request.copy_from and not request.use_template:
                        # Copy from existing language
                        source_data = asset_loader.get_template_for_language_editing(handler_name, request.copy_from)
                        if source_data:
                            template_data = source_data
                            copied_from = request.copy_from
                        else:
                            raise HTTPException(404, f"Source language '{request.copy_from}' not found for copying")
                    elif request.use_template:
                        # Use empty template
                        template_data = {
                            "success": "Operation completed successfully",
                            "error": "An error occurred",
                            "welcome": "Welcome to the system"
                        }
                    
                    # Save the new language file
                    saved, _ = asset_loader.save_template_for_language(handler_name, language, template_data)
                    if not saved:
                        raise HTTPException(500, "Failed to create template language file")
                    
                    # Reload templates to update cache
                    await asset_loader.reload_templates_for_handler(handler_name)
                    
                    return CreateTemplateLanguageResponse(
                        success=True,
                        handler_name=handler_name,
                        language=language,
                        created=True,
                        copied_from=copied_from
                    )
                    
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(500, f"Failed to create template language: {str(e)}")
            
            # ============================================================
            # PROMPT MANAGEMENT ENDPOINTS (Phase 7)
            # ============================================================
            
            @router.get("/prompts", response_model=PromptHandlerListResponse)
            async def get_prompt_handlers():
                """List all handlers with prompt language info"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    handlers_languages = asset_loader.get_handlers_with_prompts()
                    
                    handlers_info = []
                    for handler_name, languages in handlers_languages.items():
                        handlers_info.append(HandlerLanguageInfo(
                            handler_name=handler_name,
                            languages=languages,
                            total_languages=len(languages),
                            supported_languages=asset_loader.config.supported_languages,
                            default_language=asset_loader.config.default_language
                        ))
                    
                    return PromptHandlerListResponse(
                        success=True,
                        handlers=handlers_info,
                        total_handlers=len(handlers_info)
                    )
                except Exception as e:
                    raise HTTPException(500, f"Failed to get prompt handlers: {str(e)}")
            
            @router.get("/prompts/{handler_name}/languages", response_model=List[str])
            async def get_prompt_handler_languages(handler_name: str):
                """Get available languages for a handler's prompts"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    languages = asset_loader.get_available_prompt_languages_for_handler(handler_name)
                    
                    if not languages:
                        raise HTTPException(404, f"No prompt language files found for handler '{handler_name}'")
                    
                    return languages
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(500, f"Failed to get prompt handler languages: {str(e)}")
            
            @router.get("/prompts/{handler_name}/{language}", response_model=PromptContentResponse)
            async def get_language_prompt(handler_name: str, language: str):
                """Get language-specific prompt content for editing"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    
                    # Get language-specific prompt data
                    prompt_data = asset_loader.get_prompt_for_language_editing(handler_name, language)
                    if prompt_data is None:
                        raise HTTPException(404, f"Language '{language}' not found for handler '{handler_name}' prompts")
                    
                    # Convert to PromptDefinition objects
                    structured_prompts = {}
                    for prompt_name, prompt_def in prompt_data.items():
                        if isinstance(prompt_def, dict):
                            structured_prompts[prompt_name] = PromptDefinition(
                                description=prompt_def.get("description", ""),
                                usage_context=prompt_def.get("usage_context", ""),
                                variables=prompt_def.get("variables", []),
                                prompt_type=prompt_def.get("prompt_type", "system"),
                                content=prompt_def.get("content", "")
                            )
                    
                    # Get metadata
                    asset_handler_name = asset_loader._get_asset_handler_name(handler_name)
                    lang_file = asset_loader.assets_root / "prompts" / asset_handler_name / f"{language}.yaml"
                    
                    if not lang_file.exists():
                        raise HTTPException(404, f"Prompt language file not found: {lang_file}")
                    
                    stat = lang_file.stat()
                    metadata = PromptMetadata(
                        file_path=f"{asset_handler_name}/{language}.yaml",
                        language=language,
                        file_size=stat.st_size,
                        last_modified=stat.st_mtime,
                        prompt_count=len(structured_prompts)
                    )
                    
                    # Get available languages
                    available_languages = asset_loader.get_available_prompt_languages_for_handler(handler_name)
                    
                    # Schema info for prompt structure
                    schema_info = {
                        "required_fields": ["description", "usage_context", "prompt_type", "content"],
                        "prompt_types": ["system", "template", "user"]
                    }
                    
                    return PromptContentResponse(
                        success=True,
                        handler_name=handler_name,
                        language=language,
                        prompt_data=structured_prompts,
                        metadata=metadata,
                        available_languages=available_languages,
                        schema_info=schema_info
                    )
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(500, f"Failed to get language prompt: {str(e)}")
            
            @router.put("/prompts/{handler_name}/{language}", response_model=PromptUpdateResponse)
            async def update_language_prompt(handler_name: str, language: str, request: PromptUpdateRequest):
                """Update language-specific prompt and trigger reload"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    validation_passed = True
                    errors = []
                    warnings = []
                    
                    # Convert PromptDefinition objects to dict format for saving
                    prompt_data_dict = {}
                    for prompt_name, prompt_def in request.prompt_data.items():
                        if hasattr(prompt_def, 'dict'):
                            prompt_data_dict[prompt_name] = prompt_def.dict()
                        else:
                            prompt_data_dict[prompt_name] = prompt_def
                    
                    # Validate before saving if requested
                    if request.validate_before_save:
                        is_valid, error_list, warning_list = await asset_loader.validate_prompt_data(
                            handler_name, prompt_data_dict
                        )
                        validation_passed = is_valid
                        errors = [ValidationError(**err) for err in error_list]
                        warnings = [ValidationWarning(**warn) for warn in warning_list]
                        
                        if not is_valid:
                            return PromptUpdateResponse(
                                success=False,
                                handler_name=handler_name,
                                language=language,
                                validation_passed=False,
                                reload_triggered=False,
                                backup_created=False,
                                errors=errors,
                                warnings=warnings
                            )
                    
                    # Save prompt data
                    try:
                        saved, backup_created = asset_loader.save_prompt_for_language(handler_name, language, prompt_data_dict)
                        if not saved:
                            raise HTTPException(500, "Failed to save prompt language file")
                    except Exception as e:
                        raise HTTPException(400, f"Invalid prompt data: {str(e)}")
                    
                    # Trigger prompt reload if requested
                    reload_triggered = False
                    if request.trigger_reload:
                        try:
                            reload_success = await asset_loader.reload_prompts_for_handler(handler_name)
                            if reload_success:
                                reload_triggered = True
                        except Exception as e:
                            logger.warning(f"Prompt saved but reload failed: {e}")
                    
                    return PromptUpdateResponse(
                        success=True,
                        handler_name=handler_name,
                        language=language,
                        validation_passed=validation_passed,
                        reload_triggered=reload_triggered,
                        backup_created=False,  # TODO: Implement backup functionality
                        errors=errors,
                        warnings=warnings
                    )
                    
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(500, f"Failed to update language prompt: {str(e)}")
            
            @router.post("/prompts/{handler_name}/{language}/validate", response_model=PromptValidationResponse)
            async def validate_language_prompt(handler_name: str, language: str, request: PromptValidationRequest):
                """Validate language-specific prompt data without saving"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    
                    # Convert PromptDefinition objects to dict format for validation
                    prompt_data_dict = {}
                    for prompt_name, prompt_def in request.prompt_data.items():
                        if hasattr(prompt_def, 'dict'):
                            prompt_data_dict[prompt_name] = prompt_def.dict()
                        else:
                            prompt_data_dict[prompt_name] = prompt_def
                    
                    is_valid, error_list, warning_list = await asset_loader.validate_prompt_data(
                        handler_name, prompt_data_dict
                    )
                    
                    errors = [ValidationError(**err) for err in error_list]
                    warnings = [ValidationWarning(**warn) for warn in warning_list]
                    
                    return PromptValidationResponse(
                        success=True,
                        handler_name=handler_name,
                        language=language,
                        is_valid=is_valid,
                        errors=errors,
                        warnings=warnings,
                        validation_types=["yaml_structure", "prompt_metadata", "prompt_types"]
                    )
                    
                except Exception as e:
                    raise HTTPException(500, f"Failed to validate prompt: {str(e)}")
            
            @router.delete("/prompts/{handler_name}/{language}", response_model=DeletePromptLanguageResponse)
            async def delete_prompt_language(handler_name: str, language: str):
                """Delete language-specific prompt file"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    asset_handler_name = asset_loader._get_asset_handler_name(handler_name)
                    lang_file = asset_loader.assets_root / "prompts" / asset_handler_name / f"{language}.yaml"
                    
                    if not lang_file.exists():
                        raise HTTPException(404, f"Prompt language file not found: {lang_file}")
                    
                    # Delete the file
                    lang_file.unlink()
                    
                    # Reload prompts to update cache
                    await asset_loader.reload_prompts_for_handler(handler_name)
                    
                    return DeletePromptLanguageResponse(
                        success=True,
                        handler_name=handler_name,
                        language=language,
                        deleted=True,
                        backup_created=False  # TODO: Implement backup functionality
                    )
                    
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(500, f"Failed to delete prompt language: {str(e)}")
            
            @router.post("/prompts/{handler_name}/{language}", response_model=CreatePromptLanguageResponse)
            async def create_prompt_language(handler_name: str, language: str, request: CreatePromptLanguageRequest):
                """Create new language file for prompt"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    asset_handler_name = asset_loader._get_asset_handler_name(handler_name)
                    lang_file = asset_loader.assets_root / "prompts" / asset_handler_name / f"{language}.yaml"
                    
                    if lang_file.exists():
                        raise HTTPException(409, f"Prompt language file already exists: {lang_file}")
                    
                    # Create new prompt data
                    prompt_data = {}
                    copied_from = None
                    
                    if request.copy_from and not request.use_template:
                        # Copy from existing language
                        source_data = asset_loader.get_prompt_for_language_editing(handler_name, request.copy_from)
                        if source_data:
                            prompt_data = source_data
                            copied_from = request.copy_from
                        else:
                            raise HTTPException(404, f"Source language '{request.copy_from}' not found for copying")
                    elif request.use_template:
                        # Use empty template
                        prompt_data = {
                            "main_prompt": {
                                "description": "Main system prompt for this handler",
                                "usage_context": "Used when processing user requests",
                                "variables": [
                                    {"name": "user_input", "description": "The user's input text"},
                                    {"name": "context", "description": "Current conversation context"}
                                ],
                                "prompt_type": "system",
                                "content": "You are a helpful AI assistant. Process the user's request: {user_input}"
                            }
                        }
                    
                    # Save the new language file
                    saved, _ = asset_loader.save_prompt_for_language(handler_name, language, prompt_data)
                    if not saved:
                        raise HTTPException(500, "Failed to create prompt language file")
                    
                    # Reload prompts to update cache
                    await asset_loader.reload_prompts_for_handler(handler_name)
                    
                    return CreatePromptLanguageResponse(
                        success=True,
                        handler_name=handler_name,
                        language=language,
                        created=True,
                        copied_from=copied_from
                    )
                    
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(500, f"Failed to create prompt language: {str(e)}")
            
            # ============================================================
            # LOCALIZATION MANAGEMENT ENDPOINTS (Phase 8)
            # ============================================================
            
            @router.get("/localizations", response_model=LocalizationDomainListResponse)
            async def get_localization_domains():
                """List all domains with localization language info"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    domains_languages = asset_loader.get_domains_with_localizations()
                    
                    domains_info = []
                    for domain, languages in domains_languages.items():
                        domains_info.append(DomainLanguageInfo(
                            domain=domain,
                            languages=languages,
                            total_languages=len(languages),
                            supported_languages=asset_loader.config.supported_languages,
                            default_language=asset_loader.config.default_language
                        ))
                    
                    return LocalizationDomainListResponse(
                        success=True,
                        domains=domains_info,
                        total_domains=len(domains_info)
                    )
                except Exception as e:
                    raise HTTPException(500, f"Failed to get localization domains: {str(e)}")
            
            @router.get("/localizations/{domain}/languages", response_model=List[str])
            async def get_localization_domain_languages(domain: str):
                """Get available languages for a domain's localizations"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    languages = asset_loader.get_available_localization_languages_for_domain(domain)
                    
                    if not languages:
                        raise HTTPException(404, f"No localization language files found for domain '{domain}'")
                    
                    return languages
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(500, f"Failed to get localization domain languages: {str(e)}")
            
            @router.get("/localizations/{domain}/{language}", response_model=LocalizationContentResponse)
            async def get_language_localization(domain: str, language: str):
                """Get language-specific localization content for editing"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    
                    # Get language-specific localization data
                    localization_data = asset_loader.get_localization_for_domain_editing(domain, language)
                    if localization_data is None:
                        raise HTTPException(404, f"Language '{language}' not found for domain '{domain}' localizations")
                    
                    # Get metadata
                    lang_file = asset_loader.assets_root / "localization" / domain / f"{language}.yaml"
                    
                    if not lang_file.exists():
                        raise HTTPException(404, f"Localization language file not found: {lang_file}")
                    
                    stat = lang_file.stat()
                    metadata = LocalizationMetadata(
                        file_path=f"{domain}/{language}.yaml",
                        language=language,
                        file_size=stat.st_size,
                        last_modified=stat.st_mtime,
                        entry_count=len(localization_data) if isinstance(localization_data, dict) else 0
                    )
                    
                    # Get available languages
                    available_languages = asset_loader.get_available_localization_languages_for_domain(domain)
                    
                    # Schema info for localization structure
                    schema_info = {
                        "expected_keys": list(localization_data.keys()) if isinstance(localization_data, dict) else [],
                        "key_types": {
                            key: type(value).__name__.lower() for key, value in localization_data.items()
                        } if isinstance(localization_data, dict) else {},
                        "domain_description": f"Localization data for {domain} domain"
                    }
                    
                    return LocalizationContentResponse(
                        success=True,
                        domain=domain,
                        language=language,
                        localization_data=localization_data,
                        metadata=metadata,
                        available_languages=available_languages,
                        schema_info=schema_info
                    )
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(500, f"Failed to get language localization: {str(e)}")
            
            @router.put("/localizations/{domain}/{language}", response_model=LocalizationUpdateResponse)
            async def update_language_localization(domain: str, language: str, request: LocalizationUpdateRequest):
                """Update language-specific localization and trigger reload"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    validation_passed = True
                    errors = []
                    warnings = []
                    
                    # Validate before saving if requested
                    if request.validate_before_save:
                        is_valid, error_list, warning_list = await asset_loader.validate_localization_data(
                            domain, request.localization_data
                        )
                        validation_passed = is_valid
                        errors = [ValidationError(**err) for err in error_list]
                        warnings = [ValidationWarning(**warn) for warn in warning_list]
                        
                        if not is_valid:
                            return LocalizationUpdateResponse(
                                success=False,
                                domain=domain,
                                language=language,
                                validation_passed=False,
                                reload_triggered=False,
                                backup_created=False,
                                errors=errors,
                                warnings=warnings
                            )
                    
                    # Save localization data
                    try:
                        saved, backup_created = asset_loader.save_localization_for_domain(domain, language, request.localization_data)
                        if not saved:
                            raise HTTPException(500, "Failed to save localization language file")
                    except Exception as e:
                        raise HTTPException(400, f"Invalid localization data: {str(e)}")
                    
                    # Trigger localization reload if requested
                    reload_triggered = False
                    if request.trigger_reload:
                        try:
                            reload_success = await asset_loader.reload_localizations_for_domain(domain)
                            if reload_success:
                                reload_triggered = True
                        except Exception as e:
                            logger.warning(f"Localization saved but reload failed: {e}")
                    
                    return LocalizationUpdateResponse(
                        success=True,
                        domain=domain,
                        language=language,
                        validation_passed=validation_passed,
                        reload_triggered=reload_triggered,
                        backup_created=False,  # TODO: Implement backup functionality
                        errors=errors,
                        warnings=warnings
                    )
                    
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(500, f"Failed to update language localization: {str(e)}")
            
            @router.post("/localizations/{domain}/{language}/validate", response_model=LocalizationValidationResponse)
            async def validate_language_localization(domain: str, language: str, request: LocalizationValidationRequest):
                """Validate language-specific localization data without saving"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    
                    is_valid, error_list, warning_list = await asset_loader.validate_localization_data(
                        domain, request.localization_data
                    )
                    
                    errors = [ValidationError(**err) for err in error_list]
                    warnings = [ValidationWarning(**warn) for warn in warning_list]
                    
                    return LocalizationValidationResponse(
                        success=True,
                        domain=domain,
                        language=language,
                        is_valid=is_valid,
                        errors=errors,
                        warnings=warnings,
                        validation_types=["yaml_structure", "localization_types", "domain_specific"]
                    )
                    
                except Exception as e:
                    raise HTTPException(500, f"Failed to validate localization: {str(e)}")
            
            @router.delete("/localizations/{domain}/{language}", response_model=DeleteLocalizationLanguageResponse)
            async def delete_localization_language(domain: str, language: str):
                """Delete language-specific localization file"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    lang_file = asset_loader.assets_root / "localization" / domain / f"{language}.yaml"
                    
                    if not lang_file.exists():
                        raise HTTPException(404, f"Localization language file not found: {lang_file}")
                    
                    # Delete the file
                    lang_file.unlink()
                    
                    # Reload localizations to update cache
                    await asset_loader.reload_localizations_for_domain(domain)
                    
                    return DeleteLocalizationLanguageResponse(
                        success=True,
                        domain=domain,
                        language=language,
                        deleted=True,
                        backup_created=False  # TODO: Implement backup functionality
                    )
                    
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(500, f"Failed to delete localization language: {str(e)}")
            
            @router.post("/localizations/{domain}/{language}", response_model=CreateLocalizationLanguageResponse)
            async def create_localization_language(domain: str, language: str, request: CreateLocalizationLanguageRequest):
                """Create new language file for localization"""
                if not self.handler_manager:
                    raise HTTPException(503, "Intent system not initialized")
                
                try:
                    asset_loader = self._require_asset_loader()
                    lang_file = asset_loader.assets_root / "localization" / domain / f"{language}.yaml"
                    
                    if lang_file.exists():
                        raise HTTPException(409, f"Localization language file already exists: {lang_file}")
                    
                    # Create new localization data
                    localization_data = {}
                    copied_from = None
                    
                    if request.copy_from and not request.use_template:
                        # Copy from existing language
                        source_data = asset_loader.get_localization_for_domain_editing(domain, request.copy_from)
                        if source_data:
                            localization_data = source_data
                            copied_from = request.copy_from
                        else:
                            raise HTTPException(404, f"Source language '{request.copy_from}' not found for copying")
                    elif request.use_template:
                        # Use domain-specific template
                        if domain == "commands":
                            localization_data = {
                                "stop_patterns": ["stop", "halt", "cancel"]
                            }
                        elif domain == "components":
                            localization_data = {
                                "component_mappings": {
                                    "audio": "audio",
                                    "sound": "audio"
                                }
                            }
                        elif domain == "datetime":
                            localization_data = {
                                "weekdays": ["Monday", "Tuesday", "Wednesday"],
                                "months": ["January", "February", "March"],
                                "templates": {
                                    "date_full": "Today is {weekday}, {month} {day}, {year}"
                                }
                            }
                        else:
                            localization_data = {
                                "example_key": "example_value",
                                "example_list": ["item1", "item2"],
                                "example_dict": {"key": "value"}
                            }
                    
                    # Save the new language file
                    saved, _ = asset_loader.save_localization_for_domain(domain, language, localization_data)
                    if not saved:
                        raise HTTPException(500, "Failed to create localization language file")
                    
                    # Reload localizations to update cache
                    await asset_loader.reload_localizations_for_domain(domain)
                    
                    return CreateLocalizationLanguageResponse(
                        success=True,
                        domain=domain,
                        language=language,
                        created=True,
                        copied_from=copied_from
                    )
                    
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(500, f"Failed to create localization language: {str(e)}")
            
            @router.post("/configure", response_model=IntentSystemConfigureResponse)
            async def configure_intent_system(config_update: IntentSystemConfig):
                """Configure intent system settings using unified TOML schema"""
                try:
                    # Apply runtime configuration without TOML persistence
                    # Store the new configuration
                    self._config = config_update
                    
                    # Re-initialize handler manager with new configuration
                    if self.handler_manager:
                        # Extract handler configuration from IntentSystemConfig
                        handlers_obj = getattr(config_update, "handlers", None)
                        if handlers_obj:
                            handler_config = {
                                "enabled": handlers_obj.enabled,
                                "disabled": handlers_obj.disabled,
                                "auto_discover": handlers_obj.auto_discover,
                                "discovery_paths": handlers_obj.discovery_paths,
                                "asset_validation": handlers_obj.asset_validation
                            }
                        else:
                            handler_config = {}
                        
                        # Reinitialize handler manager with new config
                        await self.handler_manager.initialize(handler_config, intent_system_config=config_update)
                        
                        # Update references
                        self.intent_registry = self.handler_manager.get_registry()
                        self.intent_orchestrator = self.handler_manager.get_orchestrator()
                        
                        logger.info("Runtime reconfigured intent system successfully")
                    
                    # Get updated handler list
                    handlers = self.handler_manager.get_handlers() if self.handler_manager else {}
                    donations = self.handler_manager.get_donations() if self.handler_manager else {}
                    
                    return IntentSystemConfigureResponse(
                        success=True,
                        message="Intent system configuration applied successfully",
                        confidence_threshold=config_update.confidence_threshold,
                        fallback_intent=config_update.fallback_intent,
                        enabled_handlers=list(handlers.keys()),
                        loaded_donations=list(donations.keys()),
                        handler_count=len(handlers)
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to configure intent system: {e}")
                    # Get current state for error response
                    handlers = self.handler_manager.get_handlers() if self.handler_manager else {}
                    donations = self.handler_manager.get_donations() if self.handler_manager else {}
                    current_config = self._config if self._config else config_update
                    
                    return IntentSystemConfigureResponse(
                        success=False,
                        message=f"Failed to apply intent system configuration: {str(e)}",
                        confidence_threshold=getattr(current_config, 'confidence_threshold', 0.7),
                        fallback_intent=getattr(current_config, 'fallback_intent', 'conversation.general'),
                        enabled_handlers=list(handlers.keys()),
                        loaded_donations=list(donations.keys()),
                        handler_count=len(handlers)
                    )
            
            return router
            
        except ImportError:
            logger.warning("FastAPI not available, Web API routes disabled")
            return None
    
    def get_api_prefix(self) -> str:
        """Get URL prefix for intent system API endpoints"""
        return "/intents"
    
    def get_api_tags(self) -> List[str]:
        """Get OpenAPI tags for intent system endpoints"""
        return ["Intent System"]
    
    @classmethod
    def get_config_schema(cls) -> Optional[Type[BaseModel]]:
        """Return the Pydantic configuration schema (EntryPointMetadata contract)."""
        return cls.get_config_class()

    async def get_status(self) -> Dict[str, Any]:
        """Get intent system status for Web API"""
        if not self.handler_manager:
            return {"status": "not_initialized"}
        
        handlers = self.handler_manager.get_handlers()
        donations = self.handler_manager.get_donations()
        registry_handlers = await self.intent_registry.get_all_handlers() if self.intent_registry else {}
        
        # Get orchestrator capabilities for donation information
        orchestrator_capabilities = {}
        if self.intent_orchestrator:
            orchestrator_capabilities = await self.intent_orchestrator.get_capabilities()

        # _config may be a dict, a Pydantic model, or None (dynamic) — hold as Any so the
        # hasattr() guard governs at runtime (QUAL-4b: None-safety).
        config_repr: Any = self._config

        return {
            "status": "active",
            "handlers_count": len(handlers),
            "handlers": list(handlers.keys()),
            "donations_count": len(donations),
            "donations": list(donations.keys()),
            "registry_patterns": list(registry_handlers.keys()),
            "donation_routing_enabled": orchestrator_capabilities.get("donation_routing_enabled", False),
            "parameter_extraction_integrated": orchestrator_capabilities.get("parameter_extraction_integrated", True),  # PHASE 6: Updated to reflect new architecture
            "configuration": config_repr.model_dump() if hasattr(config_repr, 'model_dump') else config_repr
        }
    

    
    # Helper methods for workflow integration
    def get_orchestrator(self) -> Optional[IntentOrchestrator]:
        """Get the intent orchestrator for workflow integration"""
        return self.intent_orchestrator
    
    def get_registry(self) -> Optional[IntentRegistry]:
        """Get the intent registry for direct access"""
        return self.intent_registry
    
    def get_handler_manager(self) -> Optional[IntentHandlerManager]:
        """Get the handler manager for advanced operations"""
        return self.handler_manager

    def _require_asset_loader(self) -> IntentAssetLoader:
        """The intent asset loader, or a 503 if the intent system isn't fully initialized.

        Folds the two-Optional guard (handler_manager + its `_asset_loader`) into one
        typed accessor so the donation/phrasing API endpoints narrow cleanly instead of
        risking an AttributeError-on-None (QUAL-4b: None-safety).
        """
        from fastapi import HTTPException
        loader = self.handler_manager._asset_loader if self.handler_manager else None
        if loader is None:
            raise HTTPException(503, "Intent system not initialized")
        return loader

    # Build dependency methods (TODO #5 Phase 2)
    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        """Intent component needs web API functionality"""
        return ["web-api"]  # FastAPI/uvicorn web stack
        
    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        """Intent component has no system dependencies - coordinates providers only"""
        return {
            "linux.ubuntu": [],
            "linux.alpine": [],
            "macos": [],
            "windows": []
        }
    # Config interface methods (Phase 3 - Configuration Architecture Cleanup)
    @classmethod
    def get_config_class(cls) -> Type[BaseModel]:
        """Return the Pydantic config model for this component"""
        from ..config.models import IntentSystemConfig
        return IntentSystemConfig
    
    @classmethod
    def get_config_path(cls) -> str:
        """Return the TOML path to this component's config (V14 Architecture)"""
        return "intent_system" 