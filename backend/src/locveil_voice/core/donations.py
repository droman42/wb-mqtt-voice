"""
JSON Donation System - Pydantic Models and Validation

Core models for the intent donation system implementing keyword-first NLU architecture
with cascading spaCy semantic fallbacks and integrated parameter extraction.
"""

import logging
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Union
from enum import Enum

logger = logging.getLogger(__name__)


class ParameterType(str, Enum):
    """Types of parameters that can be extracted from user input"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    CHOICE = "choice"
    ENTITY = "entity"


class EntityType(str, Enum):
    """QUAL-29 (Q6): what kind of entity a parameter resolves to — selects the resolver and drives
    declarative device/room resolution (consumed by the QUAL-11 typed accessor). Language-neutral."""
    DEVICE = "device"
    LOCATION = "location"
    ROOM = "room"
    PERSON = "person"
    GENERIC = "generic"


class RoomContext(str, Enum):
    """QUAL-29 (Q6): per-method room-context enforcement policy. Language-neutral.

    - ``required``    — always resolve room/device or fail-loud.
    - ``none``        — never resolve (room-independent command).
    - ``conditional`` — resolve iff the request carries room context (ESP32/WS registration or an
      explicit REST ``room_alias``); otherwise skip with no failure. Only hard-fails when room context
      IS present but the device can't be matched.
    """
    REQUIRED = "required"
    NONE = "none"
    CONDITIONAL = "conditional"


class ParameterSpec(BaseModel):
    """Specification for a parameter that can be extracted from user input"""
    name: str = Field(..., description="Parameter name")
    type: ParameterType = Field(..., description="Parameter type")
    required: bool = Field(True, description="Is this parameter mandatory?")
    default_value: Any = Field(None, description="Default if not provided (the primary-language value)")
    # BUG-4: per-language defaults, assembled at load time from each language file's `default_value`
    # ({lang: value}). `get_param` resolves by the request language so an English request doesn't get
    # the Russian default. Runtime-only (populated by assembly, not authored in donation files), so the
    # per-file ParameterSpec shape config-ui edits is unchanged.
    default_value_by_language: Dict[str, Any] = Field(default_factory=dict, description="{lang: default_value}")
    description: str = Field("", description="Human-readable description")
    
    # Type-specific configurations
    choices: Optional[List[str]] = Field(None, description="Canonical (language-neutral) choices for CHOICE type")
    # QUAL-29 (Q6): per-language spoken surface forms mapping each canonical choice to the words a user may say
    # in a given language. Assembled at load time as {canonical: [surfaces across all languages]}; the NLU matches
    # surfaces and normalizes back to the canonical token (centralizes the RU→EN maps handlers hand-rolled before).
    choice_surfaces: Optional[Dict[str, List[str]]] = Field(None, description="{canonical: [spoken surface forms]}")
    min_value: Optional[Union[int, float]] = Field(None, description="Minimum value for numeric types")
    max_value: Optional[Union[int, float]] = Field(None, description="Maximum value for numeric types")
    pattern: Optional[str] = Field(None, description="Regex pattern for STRING type")

    # QUAL-29 (Q6): language-neutral entity classification — selects the resolver for ENTITY params
    # (and informs device/room resolution). Defaults to GENERIC; refined per handler.
    entity_type: EntityType = Field(EntityType.GENERIC, description="Entity classification (device/location/room/person/generic)")
    
    # Extraction configuration
    extraction_patterns: List[Dict[str, Any]] = Field(default_factory=list, description="spaCy extraction patterns")
    aliases: List[str] = Field(default_factory=list, description="Alternative parameter names")
    
    @validator('choices')
    def choices_required_for_choice_type(cls, v, values):
        if values.get('type') == ParameterType.CHOICE and not v:
            raise ValueError('choices required for CHOICE parameter type')
        return v
    
    @validator('min_value', 'max_value')
    def numeric_validators_for_numeric_types(cls, v, values):
        param_type = values.get('type')
        if v is not None and param_type not in [ParameterType.INTEGER, ParameterType.FLOAT]:
            raise ValueError(f'min_value/max_value only valid for numeric types, got {param_type}')
        return v

    def surface_to_canonical(self) -> Dict[str, str]:
        """QUAL-29: map every spoken surface form (lowercased, all languages) → its canonical choice token.

        The canonical token always maps to itself (it is self-matchable). Returns {} for non-CHOICE params.
        Used by the NLU to recognise a value spoken in any language and emit the language-neutral canonical.
        """
        mapping: Dict[str, str] = {}
        surfaces = self.choice_surfaces or {}
        for canonical in (self.choices or []):
            mapping[canonical.lower()] = canonical
            for surface in surfaces.get(canonical, []):
                mapping[surface.lower()] = canonical
        return mapping

    def coerce(self, value: Any) -> Any:
        """QUAL-11: the single, shared type-coercion + validation step for an extracted value.

        Used by **both** the NLU providers (extraction time) and the handler typed accessor
        (`IntentHandler.get_param`, read time) so the parameter surface is identical no matter which
        provider won the cascade or whether the handler re-reads it. Raises ``ValueError`` on a
        range/choice violation or an un-coercible value (the caller decides whether to apply
        ``default_value`` or fail loud — never silently swallow).
        """
        # Type conversion
        if self.type == ParameterType.INTEGER:
            value = int(value)
        elif self.type == ParameterType.FLOAT:
            value = float(value)
        elif self.type == ParameterType.STRING:
            value = str(value)
        elif self.type == ParameterType.BOOLEAN:
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in ("true", "yes", "1", "да", "вкл", "включи"):
                    value = True
                elif lowered in ("false", "no", "0", "нет", "выкл", "выключи"):
                    value = False
                else:
                    value = bool(value)
            else:
                value = bool(value)

        # Range validation for numeric types
        if self.type in (ParameterType.INTEGER, ParameterType.FLOAT):
            if self.min_value is not None and value < self.min_value:
                raise ValueError(f"Value {value} below minimum {self.min_value}")
            if self.max_value is not None and value > self.max_value:
                raise ValueError(f"Value {value} above maximum {self.max_value}")

        # Choice validation (normalise a surface form to its canonical token first)
        if self.type == ParameterType.CHOICE and self.choices:
            value = self.surface_to_canonical().get(str(value).lower(), value)
            if value not in self.choices:
                raise ValueError(f"Value {value!r} not in allowed choices {self.choices}")

        return value


class TrainingExample(BaseModel):
    """Training example with expected parameters"""
    text: str = Field(..., description="Example user input text")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Expected extracted parameters")


class MethodDonation(BaseModel):
    """Donation for a specific handler method"""
    method_name: str = Field(..., description="Python method name in handler")
    intent_suffix: str = Field(..., description="Intent suffix after domain")
    description: Optional[str] = Field("", description="Method description")
    
    # Recognition patterns
    phrases: List[str] = Field(..., min_length=1, description="Trigger phrases")
    lemmas: List[str] = Field(default_factory=list, description="Key lemmas")
    
    # Parameter specifications
    parameters: List[ParameterSpec] = Field(default_factory=list, description="Method parameters")
    
    # spaCy patterns
    token_patterns: List[List[Dict[str, Any]]] = Field(default_factory=list, description="spaCy token patterns")
    slot_patterns: Dict[str, List[List[Dict[str, Any]]]] = Field(default_factory=dict, description="spaCy slot patterns")
    
    # Training data
    examples: List[TrainingExample] = Field(default_factory=list, description="Training examples")
    
    # Configuration
    boost: float = Field(1.0, ge=0.0, le=10.0, description="Pattern strength multiplier")

    # QUAL-29 (Q6): language-neutral room-context enforcement policy for this method.
    room_context: RoomContext = Field(RoomContext.NONE, description="Room-context policy (required/none/conditional)")

    @validator('method_name')
    def method_name_valid_identifier(cls, v):
        if not v.isidentifier():
            raise ValueError(f'method_name must be valid Python identifier, got: {v}')
        return v


class HandlerDonation(BaseModel):
    """Complete donation from a handler with metadata and validation"""
    schema_version: str = Field(..., description="JSON schema version")
    donation_version: str = Field("1.0", description="Donation content version for caching and telemetry")
    handler_domain: str = Field(..., description="Handler domain name")
    description: Optional[str] = Field("", description="Handler description")
    
    # NEW: Handler-level pattern matching fields for can_handle logic
    intent_name_patterns: Optional[List[str]] = Field(default_factory=list, description="Intent name patterns for can_handle")
    action_patterns: Optional[List[str]] = Field(default_factory=list, description="Action patterns for can_handle")
    domain_patterns: Optional[List[str]] = Field(default_factory=list, description="Domain patterns for can_handle")
    fallback_conditions: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Fallback conditions for can_handle")
    
    # Additional recognition patterns (for NLU providers)
    additional_recognition_patterns: Optional[List[str]] = Field(default_factory=list, description="Additional patterns for NLU recognition")
    language_detection: Optional[Dict[str, List[str]]] = Field(default_factory=dict, description="Language detection patterns")
    train_keywords: Optional[List[str]] = Field(default_factory=list, description="Train-specific keywords")
    
    # Method donations
    method_donations: List[MethodDonation] = Field(..., min_length=1, description="Method-specific donations")
    
    # Global configuration
    global_parameters: List[ParameterSpec] = Field(default_factory=list, description="Shared parameters")
    negative_patterns: List[List[Dict[str, Any]]] = Field(default_factory=list, description="Negative patterns")
    
    @validator('schema_version')
    def supported_schema_version(cls, v):
        # QUAL-29: v1.1 is the split format (language-neutral contract + per-language phrasing).
        supported_versions = ['1.1']
        if v not in supported_versions:
            raise ValueError(f'Unsupported schema version: {v}. Supported: {supported_versions}')
        return v
    
    @validator('donation_version')
    def supported_donation_version(cls, v):
        # Validate semantic version format (major.minor or major.minor.patch)
        import re
        if not re.match(r'^\d+\.\d+(\.\d+)?$', v):
            raise ValueError(f'donation_version must be in semantic version format (e.g., "1.0", "1.0.1"), got: {v}')
        return v
    
    @validator('handler_domain')
    def domain_valid_identifier(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError(f'handler_domain must be alphanumeric with hyphens/underscores, got: {v}')
        return v
    
    @validator('method_donations')
    def unique_method_names(cls, v):
        method_names = [method.method_name for method in v]
        if len(method_names) != len(set(method_names)):
            raise ValueError('method_name must be unique within handler')
        return v
    
    @validator('method_donations')
    def unique_intent_suffixes(cls, v):
        intent_suffixes = [method.intent_suffix for method in v]
        if len(intent_suffixes) != len(set(intent_suffixes)):
            raise ValueError('intent_suffix must be unique within handler')
        return v


class KeywordDonation(BaseModel):
    """Converted donation format for keyword matching providers"""
    intent: str = Field(..., description="Full intent name (domain.suffix)")
    phrases: List[str] = Field(..., min_length=1, description="Trigger phrases")
    lemmas: List[str] = Field(default_factory=list, description="Key lemmas")
    parameters: List[ParameterSpec] = Field(default_factory=list, description="Parameter specifications")
    token_patterns: List[List[Dict[str, Any]]] = Field(default_factory=list, description="spaCy token patterns")
    slot_patterns: Dict[str, List[List[Dict[str, Any]]]] = Field(default_factory=dict, description="spaCy slot patterns")
    examples: List[Dict[str, Any]] = Field(default_factory=list, description="Training examples")
    boost: float = Field(1.0, ge=0.0, le=10.0, description="Pattern strength multiplier")
    
    # Metadata for caching and telemetry
    donation_version: str = Field("1.0", description="Donation content version")
    handler_domain: str = Field(..., description="Handler domain for telemetry")


class DonationValidationConfig(BaseModel):
    """Configuration for donation validation"""
    strict_mode: bool = Field(True, description="Fail on any validation error")
    warn_unused_patterns: bool = Field(True, description="Warn about unused patterns")
    # CR-C13: `validate_method_existence` retired — method-wiring is validated by the contract validator
    # (`validate_contract_wiring`), which imports each handler once and does the stricter callable check.
    validate_spacy_patterns: bool = Field(False, description="Validate spaCy pattern syntax - disabled at startup, validated at runtime by providers")
    validate_json_schema: bool = Field(True, description="Validate JSON files against JSON Schema")
    max_methods_per_handler: int = Field(1000, description="Maximum methods per handler")
    max_phrases_per_method: int = Field(100, description="Maximum phrases per method")


class DonationDiscoveryError(Exception):
    """Raised when donation discovery or validation fails"""
    pass


class ParameterExtractionError(Exception):
    """Raised when parameter extraction fails. Caught at the handler-execute boundary and converted
    into a conversational clarification (QUAL-30), not a terminal error."""
    pass


class MissingRequiredParameter(ParameterExtractionError):
    """A declared `required` parameter was absent with no default (raised by `IntentHandler.get_param`).

    Carries structured fields so the QUAL-30 clarification boundary can phrase an explain-and-ask
    ("I need <description>") without re-deriving them — deterministically or via an LLM.
    """
    def __init__(self, param_name: str, intent_name: str, description: str = ""):
        self.param_name = param_name
        self.intent_name = intent_name
        self.description = description or param_name
        super().__init__(f"Missing required parameter '{param_name}' for intent '{intent_name}'")
