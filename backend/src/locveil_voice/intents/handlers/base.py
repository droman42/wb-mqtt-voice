"""Base intent handler class."""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable, Coroutine

from ..models import Intent, IntentResult
from ..context_models import UnifiedConversationContext
from ...core.client_registry import get_client_registry, resolve_physical_id, ActionRecord
from ...core.durable_actions import get_durable_action_store, DurableActionRecord
from ...core.metadata import EntryPointMetadata
from ...core.notifications import get_notification_service, NotificationService
from ...core.metrics import get_metrics_collector, MetricsCollector
from ...core.trace_context import TraceContext, trace_event

logger = logging.getLogger(__name__)


class IntentHandler(EntryPointMetadata, ABC):
    """
    Enhanced base class for intent handlers with JSON donation support.
    
    Features:
    - JSON donation integration for pattern-free operation
    - Donation-driven method routing
    - Parameter extraction from donation specifications
    """

    # Template name `_error_result` renders; handlers override to point at their own error template.
    _error_template: str = "error_general"

    def __init__(self):
        """Initialize the intent handler."""
        self.name = self.__class__.__name__
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
        self.donation: Optional[Any] = None  # Will be HandlerDonation
        self._donation_initialized = False
        self.asset_loader: Optional[Any] = None  # Will be IntentAssetLoader
        self._asset_loader_initialized = False
        self.context_manager: Optional[Any] = None  # Context manager for fire-and-forget actions
        self._timeout_tasks: Dict[str, asyncio.Task] = {}  # Track timeout monitoring tasks
        self._completion_tasks: set = set()  # Strong refs to async completion tasks (avoid GC/orphan)
        self._notification_service: Optional[NotificationService] = None  # Phase 3.1: Notification service
        self._metrics_collector: Optional[MetricsCollector] = None  # Phase 3.2: Metrics collector
        self._trace_context: Optional[TraceContext] = None  # Phase 6: Trace context for component calls
    
    def set_context_manager(self, context_manager: Any) -> None:
        """Set the context manager for fire-and-forget action tracking."""
        self.context_manager = context_manager
    
    async def set_notification_service(self, notification_service: Optional[NotificationService] = None) -> None:
        """Set the notification service for user notifications (Phase 3.1)"""
        if notification_service is None:
            self._notification_service = await get_notification_service()
        else:
            self._notification_service = notification_service
    
    def set_metrics_collector(self, metrics_collector: Optional[MetricsCollector] = None) -> None:
        """Set the metrics collector for performance tracking (Phase 3.2)"""
        if metrics_collector is None:
            self._metrics_collector = get_metrics_collector()
        else:
            self._metrics_collector = metrics_collector
    
    # Phase 2: Intent analytics helper methods
    def record_intent_recognition(self, intent_name: str, confidence: float, processing_time: float, session_id: Optional[str] = None) -> None:
        """Record intent recognition metrics through unified metrics collector"""
        if self._metrics_collector:
            self._metrics_collector.record_intent_recognition(intent_name, confidence, processing_time, session_id)
    
    def record_intent_execution(self, intent_name: str, success: bool, execution_time: float, 
                               error: Optional[str] = None, session_id: Optional[str] = None) -> None:
        """Record intent execution metrics through unified metrics collector"""
        if self._metrics_collector:
            self._metrics_collector.record_intent_execution(intent_name, success, execution_time, error, session_id)
    
    def record_session_start(self, session_id: str) -> None:
        """Record conversation session start through unified metrics collector"""
        if self._metrics_collector:
            self._metrics_collector.record_session_start(session_id)
    
    def record_session_end(self, session_id: str, user_satisfaction: Optional[float] = None) -> None:
        """Record conversation session end through unified metrics collector"""
        if self._metrics_collector:
            self._metrics_collector.record_session_end(session_id, user_satisfaction)
    
    async def rearm_durable_action(self, record: DurableActionRecord) -> bool:
        """Re-launch a persisted durable action after a restart (ARCH-28 D-3).

        A handler that launches with ``durable=True`` MUST override this: recompute what
        remains (e.g. a timer's remaining seconds from the record's deadline), then relaunch
        through the normal F&F path REUSING ``record.action_name`` (stable identity, D-8) with
        ``durable=True`` again. Return True on successful re-arm; the default refuses, which
        makes the reconciler announce the action as expired rather than silently drop it.
        """
        self.logger.error(f"{self.__class__.__name__} launched durable action "
                          f"'{record.action_name}' but does not implement rearm_durable_action")
        return False

    async def execute_fire_and_forget_with_context(
        self,
        action_func: Callable[..., Coroutine[Any, Any, Any]],
        action_name: str,
        domain: str,
        context: UnifiedConversationContext,
        timeout: Optional[float] = None,
        completion_message: Optional[str] = None,
        durable: bool = False,
        redeliver_on_reconnect: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Launch a fire-and-forget action, registered in the runtime action store (QUAL-28).

        ``durable=True`` (ARCH-28): the launch also persists a `DurableActionRecord` so the
        promise survives a restart — declare it iff the action promises effects beyond the
        current interaction, and implement :meth:`rearm_durable_action`. ``kwargs`` must then
        be JSON-serializable (they are the persisted re-arm params). ``redeliver_on_reconnect``
        additionally queues the completion notice for redelivery if the owning reply channel is
        offline when it fires (D-6). See docs/design/durable_actions.md §3 for the full contract.

        `completion_message` (optional) is the text to announce when the action completes, already
        rendered in the REQUEST language by the handler. It is captured with `context.language` into
        the action record so the deferred completion is delivered in the user's language (BUG-4 / F&F):
        the action fires later, detached from the request, so the language can't be re-derived then.

        Resolves the action's stable ``physical_id`` from the context (room/device, falling back to
        the session id) so the action survives conversation-session eviction. ``**kwargs`` are passed
        verbatim to ``action_func`` — the F&F machinery takes no ``session_id`` parameter, so an
        action coroutine is free to take its own ``session_id`` kwarg without any collision.
        """
        physical_id = resolve_physical_id(context.client_id, context.room_name, context.session_id)
        result = await self.execute_fire_and_forget_action(
            action_func,
            action_name=action_name,
            domain=domain,
            physical_id=physical_id,
            owner_session_id=context.session_id,
            room_id=context.client_id or context.room_name,
            source=getattr(context, "request_source", None),
            timeout=timeout,
            language=getattr(context, "language", None),
            completion_message=completion_message,
            durable=durable,
            redeliver_on_reconnect=redeliver_on_reconnect,
            **kwargs
        )
        # ARCH-19 (D-5): trace EVERY fire-and-forget launch uniformly at this choke point — covers
        # timer, voice_synthesis, audio_playback and any future F&F handler. The action itself runs
        # in a detached task (where the contextvar is a stale snapshot), so the event is recorded
        # here in the synchronous request path. No-op when no trace is active.
        trace_event("action_launched", {"domain": domain, "action": action_name},
                    handler=getattr(self, "name", "") or type(self).__name__)
        return result
    
    @abstractmethod
    async def execute(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """
        Execute the intent and return a result.
        
        Args:
            intent: The intent to execute
            context: Current conversation context
            
        Returns:
            IntentResult with response and metadata
        """
        pass
    
    async def can_handle(self, intent: Intent) -> bool:
        """Donation-driven routing: match the intent against this handler's contract patterns
        (domain → intent-name → action). Handlers needing extra logic (e.g. a low-confidence
        fallback) override this. A missing donation is a fatal wiring error.

        Note: handlers whose contract has no ``domain_patterns`` won't match by domain here — declare
        ``domain_patterns`` in the contract rather than hardcoding a domain check in an override."""
        if not self.has_donation():
            raise RuntimeError(f"{type(self).__name__}: Missing JSON donation file - a donation is required")
        donation = self.get_donation()
        if donation is None:
            return False
        if donation.domain_patterns and intent.domain in donation.domain_patterns:
            return True
        if donation.intent_name_patterns and intent.name in donation.intent_name_patterns:
            return True
        if donation.action_patterns and intent.action in donation.action_patterns:
            return True
        return False
    
    async def is_available(self) -> bool:
        """
        Check if this handler is currently available.
        
        Returns:
            True if the handler is available and functioning
        """
        return True
    
    def set_donation(self, donation: Any) -> None:
        """
        Set the JSON donation for this handler.
        
        Args:
            donation: HandlerDonation object with method specifications
        """
        self.donation = donation
        self._donation_initialized = True
        self.logger.info(f"Handler {self.name} initialized with donation containing {len(donation.method_donations)} methods")
    
    def get_donation(self) -> Optional[Any]:
        """
        Get the JSON donation for this handler.
        
        Returns:
            HandlerDonation object or None if not set
        """
        return self.donation
    
    def has_donation(self) -> bool:
        """
        Check if this handler has a JSON donation set.
        
        Returns:
            True if donation is set and initialized
        """
        return self._donation_initialized and self.donation is not None
    
    def set_asset_loader(self, asset_loader: Any) -> None:
        """
        Set the IntentAssetLoader for this handler.
        
        Args:
            asset_loader: IntentAssetLoader object for accessing external assets
        """
        self.asset_loader = asset_loader
        self._asset_loader_initialized = True
        self.logger.info(f"Handler {self.name} initialized with asset loader")
    
    def get_asset_loader(self) -> Optional[Any]:
        """
        Get the IntentAssetLoader for this handler.
        
        Returns:
            IntentAssetLoader object or None if not set
        """
        return self.asset_loader
    
    def has_asset_loader(self) -> bool:
        """
        Check if this handler has an asset loader set.

        Returns:
            True if asset loader is set and initialized
        """
        return self._asset_loader_initialized and self.asset_loader is not None

    @property
    def _template_asset(self) -> str:
        """Asset namespace under assets/templates/ for this handler. Defaults to the handler's module
        name minus a trailing `_handler` (e.g. `audio_playback_handler` → `audio_playback`); override
        if a handler's templates live under a different name."""
        return type(self).__module__.rsplit(".", 1)[-1].removesuffix("_handler")

    def _get_template(self, template_name: str, language: str, **format_args) -> str:
        """Resolve a template from the asset loader and format it with `format_args`. Templates are
        externalized assets, so a missing loader, a missing template, or an unfilled placeholder is a
        fatal configuration error (raises)."""
        loader = self.asset_loader
        if loader is None:
            raise RuntimeError(
                f"{type(self).__name__}: Asset loader not initialized. Cannot access template "
                f"'{template_name}' for language '{language}'. Templates must be externalized."
            )
        content = loader.get_template(self._template_asset, template_name, language)
        if content is None:
            raise RuntimeError(
                f"{type(self).__name__}: Required template '{template_name}' (language '{language}', asset "
                f"'{self._template_asset}') not found. All templates must be externalized."
            )
        try:
            return content.format(**format_args)
        except KeyError as e:
            raise RuntimeError(
                f"{type(self).__name__}: template '{template_name}' missing required format argument: {e}."
            )

    def _template_or(self, template_name: str, language: str, fallback: str) -> str:
        """Error-path variant of `_get_template`: a template problem must never mask the
        ORIGINAL failure being reported (QUAL-71). Healthy assets → the localized template;
        broken/absent assets → the given last-resort literal."""
        try:
            return self._get_template(template_name, language)
        except Exception:
            return fallback

    def _error_result(self, context: UnifiedConversationContext, error: str) -> IntentResult:
        """Language-aware error result rendered via this handler's error template (`_error_template`)."""
        language = context.language
        return IntentResult(
            text=self._get_template(self._error_template, language, error=error),
            should_speak=True,
            metadata={"error": error, "language": language},
            success=False,
        )

    def find_method_for_intent(self, intent: Intent) -> Optional[str]:
        """
        Find method name for intent using JSON donation.
        
        Args:
            intent: Intent to find method for
            
        Returns:
            Method name or None if not found
        """
        if not self.has_donation():
            return None
        
        expected_suffix = intent.name.split('.', 1)[1] if '.' in intent.name else intent.name

        donation = self.donation
        if donation is None:
            return None
        for method_donation in donation.method_donations:
            if method_donation.intent_suffix == expected_suffix:
                return method_donation.method_name
        
        return None
    
    async def execute_with_donation_routing(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """
        Execute intent using donation-driven method routing.
        
        Args:
            intent: The intent to execute
            context: Current conversation context
            
        Returns:
            IntentResult with response and metadata
        """
        if not self.has_donation():
            return self._create_error_result(
                "Handler not properly initialized with donation",
                "donation_missing"
            )
        
        # Find matching method donation
        method_name = self.find_method_for_intent(intent)
        if not method_name:
            return self._create_error_result(
                f"No method found for intent {intent.name}",
                "method_not_found"
            )
        
        # Call the method
        if hasattr(self, method_name):
            from ...core.donations import ParameterExtractionError
            method = getattr(self, method_name)
            try:
                return await method(intent, context)
            except ParameterExtractionError as e:
                # QUAL-30: a structured parameter failure (e.g. missing-required from get_param) is
                # fail-loud → conversational CLARIFICATION, not a terminal error. Caught at this single
                # boundary and turned into an explain-and-ask response.
                self.logger.info(f"Clarification needed for {intent.name}: {e}")
                return await self._clarify(intent, context, e)
            except Exception as e:
                self.logger.error(f"Method {method_name} execution failed: {e}")
                return self._create_error_result(
                    f"Method execution failed: {str(e)}",
                    "method_execution_error"
                )
        else:
            return self._create_error_result(
                f"Method {method_name} not implemented in handler",
                "method_not_implemented"
            )
    
    async def _clarify(self, intent: Intent, context: UnifiedConversationContext,
                       exc: Exception) -> IntentResult:
        """QUAL-30 Grade-1 clarification responder. Turns a structured parameter failure (e.g. a
        missing-required param from `get_param`) into a single-turn **explain-and-ask** response —
        not a silent wrong-action and not a generic error dump.

        Deterministic + localized via the shared `clarification` template set (`assets/templates/
        clarification/<lang>.yaml`); `asset_loader.get_template` handles the language→default fallback,
        so no language is hardcoded here. (Optional LLM phrasing — "use an LLM if present" — is a later
        enhancement gated on the QUAL-15 LLM foundation; deterministic is the offline guarantee.)
        Returns a SUCCESSFUL conversational turn (`success=True`) flagged in metadata, so the boundary
        and Grade-2 slot-filling (QUAL-31) can detect it.

        QUAL-31: also arms a one-shot `pending_clarification` on the session, so the NEXT turn is read
        as the answer and used to resume `intent` (see `BaseWorkflow._process_pipeline` pre-check).
        """
        description = getattr(exc, 'description', '') or getattr(exc, 'param_name', '') or ''
        param_name = getattr(exc, 'param_name', None)

        # QUAL-31 Grade 2: remember the original command + the slot we just asked for, so the user can
        # answer with just the missing value next turn. `intent.raw_text` is the literal utterance that
        # triggered this (already the COMBINED text on a resumed turn → re-asks append naturally).
        context.set_pending_clarification(
            intent_name=intent.name,
            missing_param=param_name or '',
            original_text=getattr(intent, 'raw_text', '') or '',
        )

        text = None
        loader = self.asset_loader
        if self.has_asset_loader() and loader is not None:
            tmpl = loader.get_template("clarification", "missing_parameter", context.language)
            if tmpl:
                try:
                    text = tmpl.format(detail=description)
                except Exception:
                    text = tmpl
        if not text:
            # Only reached if the clarification template set is missing (misconfiguration).
            text = f"I need a bit more information: {description}".strip()

        return IntentResult(
            text=text, should_speak=True, success=True, confidence=1.0,
            metadata={"clarification": True, "clarification_reason": "missing_parameter",
                      "parameter": param_name, "intent_name": intent.name},
        )

    def get_supported_domains(self) -> List[str]:
        """
        Get list of domains this handler supports.

        Returns:
            List of supported domain names
        """
        return []
    
    def get_supported_actions(self) -> List[str]:
        """
        Get list of actions this handler supports.
        
        Returns:
            List of supported action names
        """
        return []
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get handler capabilities and metadata.
        
        Returns:
            Dictionary describing handler capabilities
        """
        return {
            "name": self.name,
            "domains": self.get_supported_domains(),
            "actions": self.get_supported_actions(),
            "available": True
        }
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get general information about this handler.
        
        Returns:
            Dictionary with handler information
        """
        return {
            "class": self.__class__.__name__,
            "module": self.__class__.__module__,
            "description": self.__doc__ or "No description available"
        }
    
    def _create_success_result(self, 
                             text: str, 
                             should_speak: bool = True,
                             metadata: Optional[Dict[str, Any]] = None,
                             actions: Optional[List[str]] = None) -> IntentResult:
        """
        Helper method to create a successful intent result.
        
        Args:
            text: Response text
            should_speak: Whether response should be spoken
            metadata: Additional metadata
            actions: Additional actions to perform
            
        Returns:
            IntentResult indicating success
        """
        return IntentResult(
            text=text,
            should_speak=should_speak,
            metadata=metadata or {},
            actions=actions or [],
            success=True,
            confidence=1.0
        )
    
    def _create_error_result(self,
                           text: str,
                           error: str,
                           metadata: Optional[Dict[str, Any]] = None) -> IntentResult:
        """The single canonical error-result primitive: `(text, error, metadata)` → failure IntentResult.

        QUAL-11 P1-t: 6 handlers used to **shadow** this name with an incompatible
        `_create_error_result(intent, context, error)` signature (a footgun — the same call meant
        different things per handler). Those localized builders are now uniformly named
        `_error_result(context, error)` and render a per-handler template before delegating here.

        Args:
            text: Error message to display
            error: Error type or description
            metadata: Additional metadata

        Returns:
            IntentResult indicating failure
        """
        return IntentResult(
            text=text,
            should_speak=True,
            metadata=metadata or {},
            success=False,
            error=error,
            confidence=0.0
        )
    
    async def validate_entities(self, intent: Intent, required_entities: List[str]) -> bool:
        """
        Validate that required entities are present in the intent.
        
        Args:
            intent: Intent to validate
            required_entities: List of required entity names
            
        Returns:
            True if all required entities are present
        """
        for entity in required_entities:
            if entity not in intent.entities or intent.entities[entity] is None:
                self.logger.warning(f"Missing required entity '{entity}' in intent {intent.name}")
                return False
        return True
    
    def extract_entity(self, intent: Intent, entity_name: str, default: Any = None) -> Any:
        """
        Extract an entity value from the intent.

        Args:
            intent: Intent to extract from
            entity_name: Name of the entity to extract
            default: Default value if entity is not found

        Returns:
            Entity value or default
        """
        return intent.entities.get(entity_name, default)

    def _find_param_spec(self, intent: Intent, name: str) -> Optional[Any]:
        """Find the donation `ParameterSpec` for `name` on the method matching `intent` (else a global
        param). Returns None if there's no donation or no such declared parameter."""
        donation = self.donation
        if donation is None:
            return None
        # Match the method whose full intent name (handler_domain.intent_suffix) equals intent.name.
        domain = getattr(donation, 'handler_domain', None)
        for method in getattr(donation, 'method_donations', []) or []:
            if domain is not None and f"{domain}.{method.intent_suffix}" != intent.name:
                continue
            for spec in list(method.parameters) + list(getattr(donation, 'global_parameters', []) or []):
                if spec.name == name:
                    return spec
        # Fall back to global parameters even if the method didn't match (e.g. intent-name drift).
        for spec in getattr(donation, 'global_parameters', []) or []:
            if spec.name == name:
                return spec
        return None

    # Sentinel so get_param can tell "no caller default given" from "default is None".
    _UNSET = object()

    def get_param(self, intent: Intent, name: str, default: Any = _UNSET) -> Any:
        """QUAL-11: the typed, donation-`ParameterSpec`-driven accessor — the single handler-boundary
        read for a declared parameter. Whichever NLU provider populated `intent.entities`, this returns
        a coerced/validated value, applies the declared `default_value`, and enforces required-vs-optional
        in one place (replacing ad-hoc `intent.entities.get(...)` with bespoke per-handler defaults).

        - present value → `spec.coerce(value)` (type/choices/range); on a coercion error, fall back to
          the declared default (or the caller's `default`), never silently return a bad value;
        - absent value → declared `default_value`, else the caller's `default` if given;
        - absent + required + no default → raise `ParameterExtractionError` (fail loud; the orchestrator
          boundary turns this into a clarification — QUAL-30). For an undeclared param it behaves like
          `extract_entity` (plain get with the caller default).
        """
        from ...core.donations import MissingRequiredParameter
        spec = self._find_param_spec(intent, name)
        raw = intent.entities.get(name)

        if raw is not None and raw != "":
            if spec is not None:
                try:
                    return spec.coerce(raw)
                except Exception as e:
                    self.logger.warning(f"get_param('{name}') coercion failed for {raw!r} on "
                                        f"intent '{intent.name}': {e}")
                    # fall through to default handling below
                else:
                    pass
            else:
                return raw

        # Missing (or coercion failed): apply the declared default, then the caller default.
        # BUG-4: prefer the default declared for the REQUEST language; an English request whose
        # en donation declares the default as null (or omits it) falls through to the caller default
        # (typically an en template) instead of getting the Russian primary default.
        if spec is not None:
            by_lang = getattr(spec, "default_value_by_language", None) or {}
            # When the param declares per-language defaults at all, resolve STRICTLY by request
            # language (a language that doesn't declare one ⇒ no default here ⇒ fall through to the
            # caller default, typically a language-aware template) — don't leak the primary language's
            # default. Only when NO per-language default exists do we use the single/neutral default.
            declared = by_lang.get(intent.language) if by_lang else spec.default_value
            if declared is not None:
                return declared
        if default is not IntentHandler._UNSET:
            return default
        if spec is not None and spec.required:
            raise MissingRequiredParameter(
                param_name=name, intent_name=intent.name,
                description=getattr(spec, 'description', '') or name,
            )
        return None
    
    async def preprocess_intent(self, intent: Intent, context: UnifiedConversationContext) -> Intent:
        """
        Preprocess the intent before execution (can be overridden).
        
        Args:
            intent: Original intent
            context: Conversation context
            
        Returns:
            Processed intent (may be modified)
        """
        return intent
    
    async def postprocess_result(self, result: IntentResult, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """
        Postprocess the result after execution (can be overridden).
        
        Args:
            result: Original result
            intent: The intent that was executed
            context: Conversation context
            
        Returns:
            Processed result (may be modified)
        """
        return result
    
    # Action execution helper methods (QUAL-28: store-centric fire-and-forget)
    async def execute_fire_and_forget_action(
        self,
        action_func: Callable[..., Coroutine[Any, Any, Any]],
        action_name: str,
        domain: str,
        *,
        physical_id: Optional[str] = None,
        owner_session_id: Optional[str] = None,
        room_id: Optional[str] = None,
        source: Optional[str] = None,
        timeout: Optional[float] = None,
        language: Optional[str] = None,
        completion_message: Optional[str] = None,
        durable: bool = False,
        redeliver_on_reconnect: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Launch ``action_func`` as a background task and register it in the runtime action store.

        The identity params (``physical_id``/``owner_session_id``/``room_id``) are **keyword-only**,
        so they can never collide with the action coroutine's own kwargs — ``**kwargs`` flows
        verbatim to ``action_func``. The store holds the task ref authoritatively; completion and
        timeout reap the action via :meth:`_on_action_done` (no session lookup, no leak).

        Returns informational action metadata (for ``create_action_result`` / API), NOT the storage
        mechanism — the action is already registered in the store before this returns.
        """
        if timeout is None:
            timeout = 300.0
        if physical_id is None:
            physical_id = resolve_physical_id(None, None, owner_session_id or action_name)
        # BUG-19: the handler action-coroutine convention is `return True/False`, but the return
        # value used to be IGNORED — a coroutine that caught its own exception and returned False
        # was recorded as a SUCCESS. Enforce the convention centrally: False → failure.
        async def _checked_action(**kw):
            result = await action_func(**kw)
            if result is False:
                raise RuntimeError(f"Action '{action_name}' reported failure (returned False)")
            return result

        try:
            rearm_params: Dict[str, Any] = {}
            if durable:
                # ARCH-28: fail LOUD at launch, not at recovery — the kwargs are the persisted
                # re-arm params and must round-trip JSON. Raises before the task is created.
                rearm_params = json.loads(json.dumps(kwargs))

            # QUAL-61 (ARCH-27 D-7): the generic retry wrapper was cut — blind whole-coroutine
            # re-invocation is unsafe without per-action idempotency; a handler that needs
            # retries owns them domain-specifically, backstopped by the failure announcement.
            task = asyncio.create_task(_checked_action(**kwargs))

            record = ActionRecord(
                action_name=action_name,
                domain=domain,
                physical_id=physical_id,
                task=task,
                started_at=time.time(),
                expected_end=(time.time() + timeout) if timeout and timeout > 0 else None,
                status="running",
                durable=durable,
                redeliver=redeliver_on_reconnect,
                session_id=owner_session_id,
                room_id=room_id,
                source=source,
                metadata={"handler": self.__class__.__name__, "timeout": timeout,
                          # BUG-4/F&F: carry the request language + the request-language-rendered
                          # completion message so the deferred completion announces in the user's language.
                          "language": language, "completion_message": completion_message},
            )
            get_client_registry().add_action(record)

            if durable:
                # ARCH-28 (D-2): persist the intent so it survives a restart. kwargs are the
                # re-arm params — they MUST be JSON-serializable (fail loud at launch, not at
                # recovery). Completion deletes this record in _on_action_done.
                get_durable_action_store().save(DurableActionRecord(
                    action_name=action_name,
                    domain=domain,
                    handler=self.__class__.__name__,
                    physical_id=physical_id,
                    started_at=record.started_at,
                    deadline=record.expected_end,
                    session_id=owner_session_id,
                    room_id=room_id,
                    source=source,
                    redeliver=redeliver_on_reconnect,
                    rearm={"method": getattr(action_func, "__name__", ""),
                           "params": rearm_params},
                    metadata={"language": language, "completion_message": completion_message},
                ))

            if self._metrics_collector:
                self._metrics_collector.record_action_start(
                    domain=domain, action_name=action_name,
                    handler=self.__class__.__name__, session_id=owner_session_id
                )

            # Reaper layer 1: completion removes from the store + fires metrics/notifications.
            task.add_done_callback(lambda t: self._on_action_done(record, t))

            # Timeout monitor: cancel an overrunning task (the done-callback then reaps it).
            if timeout and timeout > 0:
                timeout_key = f"{physical_id}:{action_name}"
                self._timeout_tasks[timeout_key] = asyncio.create_task(
                    self._monitor_action_timeout(record, timeout_key, timeout)
                )

            self.logger.info(f"Started fire-and-forget action: {action_name} "
                             f"(domain: {domain}, scope: {physical_id})")
            return {"active_actions": {action_name: {
                "handler": self.__class__.__name__, "action": action_name, "domain": domain,
                "physical_id": physical_id, "started_at": record.started_at,
                "status": "running", "timeout": timeout}}}

        except Exception as e:
            self.logger.error(f"Failed to start action {action_name}: {e}")
            if self._metrics_collector:
                try:
                    self._metrics_collector.record_action_completion(domain=domain, action_name=action_name, success=False, error=str(e))
                except Exception:
                    pass
            return {"active_actions": {action_name: {
                "handler": self.__class__.__name__, "action": action_name, "domain": domain,
                "started_at": time.time(), "completed_at": time.time(),
                "status": "failed", "error": str(e), "failed_at_startup": True}}}

    def _on_action_done(self, record: 'ActionRecord', task: asyncio.Task) -> None:
        """Done-callback: reap the action from the store and fire metrics/notifications off the record."""
        try:
            if task.cancelled():
                # BUG-19: a timeout-cancel is a failure of the action, not a user decision.
                success, error = False, ("timeout" if record.timed_out else "cancelled")
            elif task.exception() is not None:
                success, error = False, str(task.exception())
            else:
                success, error = True, None
        except Exception:
            success, error = True, None

        # An unmarked cancellation (no timeout, no deliberate-cancel marker) is process teardown:
        # every path that revokes the promise marks the record first (BUG-19 pattern). The
        # in-flight promise is exactly what restart reconciliation needs (ARCH-28 shutdown
        # discipline), so teardown must not reap it durably or announce it as failed.
        teardown_cancel = (task.cancelled() and not record.timed_out
                           and not record.deliberate_cancel)

        # Reaper layer 1 — remove from the active store + record in the per-identity history
        # (the single completion chokepoint, so history is recorded exactly once).
        try:
            registry = get_client_registry()
            registry.remove_action(record.physical_id, record.action_name, expected=record)
            registry.record_completed_action(record, success, error)
            if record.durable:
                if teardown_cancel:
                    self.logger.info(f"Durable action '{record.action_name}' cancelled by "
                                     f"teardown — keeping its persisted record for reconciliation")
                else:
                    # ARCH-28 (D-2): the persisted record dies WITH the in-memory one — a completed
                    # action must never resurrect on restart (the bridge's stale-intent lesson).
                    get_durable_action_store().delete(record.action_name)
        except Exception as e:
            self.logger.error(f"Failed to reap/record completed action {record.action_name}: {e}")

        # Cancel this action's timeout monitor, if any.
        mon = self._timeout_tasks.pop(f"{record.physical_id}:{record.action_name}", None)
        if mon is not None and not mon.done():
            mon.cancel()

        if self._metrics_collector:
            try:
                self._metrics_collector.record_action_completion(
                    domain=record.domain, action_name=record.action_name, success=success, error=error,
                    timeout_occurred=record.timed_out)
            except Exception as me:
                self.logger.error(f"Failed to record action completion metrics: {me}")

        # Notifications are async — schedule and hold a strong ref to avoid GC/orphan.
        # A teardown-cancelled durable action is NOT a failure — it re-arms at the next start —
        # so announcing "failed: cancelled" for it would be a lie.
        if record.durable and teardown_cancel:
            return
        if self._notification_service and record.session_id:
            t = asyncio.create_task(self._notify_action_result(record, success, error))
            self._completion_tasks.add(t)
            t.add_done_callback(self._completion_tasks.discard)

    async def _notify_action_result(self, record: 'ActionRecord', success: bool, error: Optional[str]) -> None:
        """Send the completion/failure notification, routed by the action's owner."""
        service = self._notification_service
        if service is None:
            return
        session_id = record.session_id
        if session_id is None:
            return
        try:
            duration = time.time() - record.started_at
            # ARCH-15 PR-4: carry the action's addressing identity so the OutputManager can deliver
            # the deferred result back to the originating channel / room-device (else drop+log, D-3).
            # BUG-4/F&F: the language + the request-language-rendered completion message captured at
            # registration, so the deferred completion announces in the user's language.
            language = (record.metadata or {}).get("language")
            completion_message = (record.metadata or {}).get("completion_message")
            if success:
                await service.send_action_completion_notification(
                    session_id=session_id, domain=record.domain,
                    action_name=record.action_name, duration=duration, success=True,
                    source=record.source, physical_id=record.physical_id, room_name=record.room_id,
                    language=language, completion_message=completion_message,
                    redeliver=record.redeliver)  # ARCH-28 D-6: survives an offline reply channel
            else:
                await service.send_action_failure_notification(
                    session_id=session_id, domain=record.domain,
                    action_name=record.action_name, error=error or "Unknown error", is_critical=False,
                    source=record.source, physical_id=record.physical_id, room_name=record.room_id,
                    language=language)
        except Exception as e:
            self.logger.error(f"Failed to send action notification for {record.action_name}: {e}")

    async def _monitor_action_timeout(self, record: 'ActionRecord',
                                      timeout_key: str, timeout: float) -> None:
        """Cancel an action that overruns its timeout; the done-callback then reaps it from the store.

        Uses ``wait_for`` (not a flat ``sleep(timeout)``) so a normally-completing action ends the
        monitor immediately instead of leaving a zombie sleeper for the full timeout. Marks the
        record ``timed_out`` BEFORE cancelling (BUG-19) so the done-callback records "timeout"
        rather than a plain "cancelled" (indistinguishable from user cancellation otherwise).
        """
        task = record.task
        if task is None:
            return
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
        except asyncio.TimeoutError:
            if not task.done():
                self.logger.warning(f"Action {record.action_name} timed out after {timeout}s — cancelling")
                record.timed_out = True
                task.cancel()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Error in timeout monitoring for action {record.action_name}: {e}")
        finally:
            self._timeout_tasks.pop(timeout_key, None)

    async def cleanup_timeout_tasks(self) -> None:
        """Clean up all timeout monitoring tasks during shutdown"""
        if self._timeout_tasks:
            self.logger.info(f"Cleaning up {len(self._timeout_tasks)} timeout monitoring tasks")
            
            # Cancel all timeout tasks
            for timeout_key, task in self._timeout_tasks.items():
                if not task.done():
                    task.cancel()
            
            # Wait for all tasks to complete cancellation
            if self._timeout_tasks:
                await asyncio.gather(*self._timeout_tasks.values(), return_exceptions=True)
            
            # Clear the tracking dictionary
            self._timeout_tasks.clear()
            self.logger.debug("All timeout monitoring tasks cleaned up")
    
    def create_action_result(
        self, 
        response_text: str, 
        action_name: str,
        domain: str,
        should_speak: bool = True,
        action_metadata: Optional[Dict[str, Any]] = None
    ) -> IntentResult:
        """
        Create an IntentResult with action metadata for fire-and-forget actions.
        
        Args:
            response_text: Immediate response text
            action_name: Human-readable action name
            domain: Action domain for ambiguity resolution
            should_speak: Whether response should be spoken
            action_metadata: Pre-generated action metadata (from execute_fire_and_forget_action)
            
        Returns:
            IntentResult with action tracking metadata
        """
        return IntentResult(
            text=response_text,
            should_speak=should_speak,
            metadata={},
            action_metadata=action_metadata or {},
            success=True,
            confidence=1.0
        )
    
    def _get_stop_patterns(self, language: str) -> List[str]:
        """Get stop command patterns from asset loader - raises fatal error if not available"""
        if not self.has_asset_loader():
            raise RuntimeError(
                f"BaseIntentHandler: Asset loader not initialized. "
                f"Cannot access stop patterns for language '{language}'. "
                f"This is a fatal configuration error - command patterns must be externalized."
            )
        
        # Get patterns from asset loader
        loader = self.asset_loader
        if loader is None:
            raise RuntimeError(
                f"BaseIntentHandler: Asset loader not initialized. "
                f"Cannot access stop patterns for language '{language}'."
            )
        commands_data = loader.get_localization("commands", language)
        if commands_data is None:
            raise RuntimeError(
                f"BaseIntentHandler: Required command patterns for language '{language}' "
                f"not found in assets/localization/commands/{language}.yaml. "
                f"This is a fatal error - all command patterns must be externalized."
            )
        
        stop_patterns = commands_data.get("stop_patterns", [])
        if not stop_patterns:
            raise RuntimeError(
                f"BaseIntentHandler: Empty stop_patterns in assets/localization/commands/{language}.yaml. "
                f"At least one stop pattern must be defined for language '{language}'."
            )
        
        return stop_patterns
    
    def _get_domain_hints(self, language: str) -> Dict[str, List[str]]:
        """Get domain hints from asset loader - raises fatal error if not available"""
        if not self.has_asset_loader():
            raise RuntimeError(
                f"BaseIntentHandler: Asset loader not initialized. "
                f"Cannot access domain hints for language '{language}'. "
                f"This is a fatal configuration error - domain patterns must be externalized."
            )
        
        # Get domain hints from asset loader
        loader = self.asset_loader
        if loader is None:
            raise RuntimeError(
                f"BaseIntentHandler: Asset loader not initialized. "
                f"Cannot access domain hints for language '{language}'."
            )
        domains_data = loader.get_localization("domains", language)
        if domains_data is None:
            raise RuntimeError(
                f"BaseIntentHandler: Required domain hints for language '{language}' "
                f"not found in assets/localization/domains/{language}.yaml. "
                f"This is a fatal error - all domain patterns must be externalized."
            )
        
        domain_hints = domains_data.get("domain_hints", {})
        if not domain_hints:
            raise RuntimeError(
                f"BaseIntentHandler: Empty domain_hints in assets/localization/domains/{language}.yaml. "
                f"At least one domain hint must be defined for language '{language}'."
            )
        
        return domain_hints
    
    
    # Build dependency methods (TODO #5 Phase 2)
    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        """Intent handlers process intents - minimal dependencies"""
        return []
        
    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        """Intent handlers have no system dependencies - pure logic"""
        return {
            "linux.ubuntu": [],
            "linux.alpine": [],
            "macos": [],
            "windows": []
        }
