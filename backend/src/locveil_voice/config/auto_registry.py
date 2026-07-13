"""
Auto Schema Registry - Automatically generate schema registries from Pydantic models

This module implements the AutoSchemaRegistry class which eliminates manual schema
dictionaries by auto-generating them from Pydantic model introspection. This serves
as the single source of truth for all schema-related operations.

Key Features:
- Auto-generates section model registry from CoreConfig fields
- Auto-discovers component schemas with validation
- Auto-generates provider schema registry from discovery
- Validates schema coverage and returns comprehensive reports
- Validates config-master.toml completeness against all provider schemas
- Caches results for performance with cache invalidation support

Design Principles:
- Single Source of Truth: Pydantic CoreConfig model is authoritative
- Automatic Generation: All registries auto-generated via introspection
- Fail-Fast Validation: Schema mismatches detected at startup
- Zero Manual Sync: No manual dictionary maintenance
"""

import logging
import inspect
import re
import tomllib
from pathlib import Path
from typing import Dict, Any, Type, Optional, get_origin, get_args
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AutoSchemaRegistry:
    """Auto-generates schema registries from Pydantic CoreConfig model"""
    
    _section_models_cache: Optional[Dict[str, Type[BaseModel]]] = None
    _component_schemas_cache: Optional[Dict[str, Type[BaseModel]]] = None
    _provider_schemas_cache: Optional[Dict[str, Dict[str, Type[BaseModel]]]] = None
    
    @staticmethod
    def _is_scalar_annotation(annotation: Any) -> bool:
        """True if the annotation is a plain scalar (str/int/float/bool), incl. Optional[scalar].

        Used by the master-config completeness check (ARCH-15 PR-9.2): only scalar fields are
        validated by key-presence (`field = ...`); Dict/List/BaseModel fields appear as tables and
        are checked at section granularity instead, so they are skipped here.
        """
        args = get_args(annotation)
        if args and type(None) in args:  # Optional[X] / Union[X, None]
            non_none = [a for a in args if a is not type(None)]
            if len(non_none) == 1:
                annotation = non_none[0]
        return annotation in (str, int, float, bool)

    @staticmethod
    def _resolve_section_model(annotation: Any) -> Optional[Type[BaseModel]]:
        """Return the Pydantic section model a CoreConfig field annotation denotes, if any.

        A *section* is a top-level CoreConfig field whose type is a Pydantic model
        — directly, or wrapped in Optional[...] / Union[..., None]. Scalar fields
        (str/int/bool/enum/list) are NOT sections: they are instance-identity and
        runtime knobs that live directly on CoreConfig and legitimately have no
        section model. Returns None for those. (QUAL-6: single predicate shared by
        the registry and the coverage check, so the two cannot disagree.)
        """
        # Direct BaseModel subclass
        if (inspect.isclass(annotation) and
                issubclass(annotation, BaseModel) and
                annotation != BaseModel):
            return annotation

        # Optional[BaseModel] / Union[BaseModel, None]
        if get_origin(annotation) is not None:
            for arg in get_args(annotation):
                if (inspect.isclass(arg) and
                        issubclass(arg, BaseModel) and
                        arg != BaseModel):
                    return arg

        return None

    @classmethod
    def get_section_models(cls) -> Dict[str, Type[BaseModel]]:
        """Auto-generate section model registry from CoreConfig fields"""
        if cls._section_models_cache is None:
            cls._section_models_cache = {}

            from .models import CoreConfig

            for field_name, field_info in CoreConfig.model_fields.items():
                annotation = getattr(field_info, 'annotation', None)
                model_class = cls._resolve_section_model(annotation)
                if model_class:
                    cls._section_models_cache[field_name] = model_class
                    logger.debug(f"Auto-registered: {field_name} -> {model_class.__name__}")

            logger.info(f"Auto-generated {len(cls._section_models_cache)} section models")

        return cls._section_models_cache.copy()
    
    @classmethod
    def get_section_model(cls, section_name: str) -> Optional[Type[BaseModel]]:
        """Get specific section model by name"""
        section_models = cls.get_section_models()
        return section_models.get(section_name)
    
    @classmethod
    def get_component_schemas(cls) -> Dict[str, Type[BaseModel]]:
        """Auto-generate component schema registry with validation"""
        if cls._component_schemas_cache is None:
            cls._component_schemas_cache = {}
            
            from .models import ComponentConfig
            component_fields = ComponentConfig.model_fields
            
            for component_name, field_info in component_fields.items():
                if field_info.annotation == bool:  # Component enablement flag
                    schema_class = cls._find_component_schema(component_name)
                    if schema_class:
                        cls._component_schemas_cache[component_name] = schema_class
                        logger.debug(f"Auto-registered component: {component_name} -> {schema_class.__name__}")
                    else:
                        logger.warning(f"No component schema found: {component_name}")
            
            logger.info(f"Auto-generated {len(cls._component_schemas_cache)} component schemas")
        
        return cls._component_schemas_cache.copy()
    
    @classmethod 
    def get_provider_schemas(cls) -> Dict[str, Dict[str, Type[BaseModel]]]:
        """Auto-generate provider schema registry from discovery"""
        if cls._provider_schemas_cache is None:
            cls._provider_schemas_cache = {}
            
            # Auto-discover provider schemas by importing and introspecting schema classes
            provider_schemas = cls._discover_provider_schemas()
            cls._provider_schemas_cache = provider_schemas
            
            logger.info(f"Provider schemas auto-discovered: {sum(len(providers) for providers in cls._provider_schemas_cache.values())} providers")
        
        return cls._provider_schemas_cache.copy()
    
    @classmethod
    def _discover_provider_schemas(cls) -> Dict[str, Dict[str, Type[BaseModel]]]:
        """Auto-discover provider schemas by importing and analyzing schema classes"""
        try:
            # Import all provider schema classes
            from .schemas import (
                # TTS providers
                ConsoleProviderSchema, ElevenLabsProviderSchema, SileroV3ProviderSchema,
                SileroV4ProviderSchema, VoskTTSProviderSchema, PyttSXProviderSchema, PiperProviderSchema,
                PiperRuAccentProviderSchema,
                # Audio providers
                SoundDeviceProviderSchema, APlayProviderSchema, ConsoleAudioProviderSchema, MiniaudioProviderSchema,
                # ASR providers
                WhisperProviderSchema, VoskASRProviderSchema, GoogleCloudProviderSchema, SherpaOnnxASRProviderSchema,
                # LLM providers
                OpenAIProviderSchema, AnthropicProviderSchema, DeepSeekProviderSchema, ConsoleLLMProviderSchema,
                # Voice trigger providers
                OpenWakeWordProviderSchema, MicroWakeWordProviderSchema,
                # VAD providers (ARCH-18)
                EnergyVADProviderSchema, SileroVADProviderSchema, MicroVADProviderSchema,
                # NLU providers
                HybridKeywordMatcherProviderSchema, SpaCyNLUProviderSchema, LLMNLUProviderSchema,
                # Text processor provider (QUAL-13: one unified processor)
                UnifiedTextProcessorProviderSchema
            )
            
            # Auto-discover provider mappings based on naming conventions and schema inheritance
            provider_schemas = {
                "tts": {
                    "console": ConsoleProviderSchema,
                    "elevenlabs": ElevenLabsProviderSchema,
                    "silero_v3": SileroV3ProviderSchema,
                    "silero_v4": SileroV4ProviderSchema,
                    "vosk": VoskTTSProviderSchema,
                    "pyttsx": PyttSXProviderSchema,
                    "piper": PiperProviderSchema,
                    "piper_ruaccent": PiperRuAccentProviderSchema,
                },
                "audio": {
                    "console": ConsoleAudioProviderSchema,
                    "sounddevice": SoundDeviceProviderSchema,
                    "aplay": APlayProviderSchema,
                    "miniaudio": MiniaudioProviderSchema,
                },
                "asr": {
                    "whisper": WhisperProviderSchema,
                    "vosk": VoskASRProviderSchema,
                    "google_cloud": GoogleCloudProviderSchema,
                    "sherpa_onnx": SherpaOnnxASRProviderSchema,
                },
                "llm": {
                    "openai": OpenAIProviderSchema,
                    "anthropic": AnthropicProviderSchema,
                    "deepseek": DeepSeekProviderSchema,
                    "console": ConsoleLLMProviderSchema,
                },
                "voice_trigger": {
                    "openwakeword": OpenWakeWordProviderSchema,
                    "microwakeword": MicroWakeWordProviderSchema,
                },
                "vad": {
                    "energy": EnergyVADProviderSchema,
                    "silero": SileroVADProviderSchema,
                    "microvad": MicroVADProviderSchema,
                },
                "nlu": {
                    "hybrid_keyword_matcher": HybridKeywordMatcherProviderSchema,
                    "spacy_nlu": SpaCyNLUProviderSchema,
                    "llm": LLMNLUProviderSchema,
                },
                "text_processor": {
                    "unified_text_processor": UnifiedTextProcessorProviderSchema,
                }
            }
            
            logger.debug("Provider schemas auto-discovered successfully")
            return provider_schemas
            
        except ImportError as e:
            logger.error(f"Failed to auto-discover provider schemas: {e}")
            # Fallback to empty registry
            return {}
    
    @classmethod
    def extract_all_schemas(cls) -> Dict[str, Any]:
        """Extract complete configuration schema (auto-generated only)"""
        schema = {}
        section_models = cls.get_section_models()
        
        for section_name, model_class in section_models.items():
            schema[section_name] = cls._extract_model_schema(model_class)
        
        return schema
    
    # ARCH-2: schema-extraction cluster moved here from ConfigurationComponent
    # (schema logic belongs in the schema registry; removes the auto_registry ->
    # components.configuration_component upward import / SCC-1 edge).
    @classmethod
    def _extract_model_schema(cls, model_class: Type[BaseModel]) -> Dict[str, Any]:
        """Extract field metadata from Pydantic model for widget generation"""
        if not model_class:
            return {}
        
        try:
            from pydantic_core import PydanticUndefined
        except ImportError:
            # Fallback for older Pydantic versions
            PydanticUndefined = None
            
        schema = {
            "fields": {},
            "title": getattr(model_class, "__name__", "Configuration"),
            "description": getattr(model_class, "__doc__", "").strip() if getattr(model_class, "__doc__", "") else ""
        }
        
        # Get Pydantic model fields
        model_fields = model_class.model_fields if hasattr(model_class, 'model_fields') else {}
        
        for field_name, field_info in model_fields.items():
            try:
                # Safely extract field information
                field_type = cls._get_field_type(field_info)
                
                # Get field description - check multiple possible locations
                description = ""
                if hasattr(field_info, 'description') and field_info.description:
                    description = field_info.description
                elif hasattr(field_info, 'json_schema_extra') and isinstance(field_info.json_schema_extra, dict):
                    description = field_info.json_schema_extra.get('description', '')
                
                # For Pydantic v2, check if field is required by looking at default value
                is_required = True
                default_value = None
                
                if hasattr(field_info, 'default') and PydanticUndefined is not None:
                    if field_info.default is not PydanticUndefined:
                        is_required = False
                        default_value = field_info.default
                elif hasattr(field_info, 'default'):
                    # Fallback for when PydanticUndefined is not available
                    try:
                        if field_info.default is not ...:  # Ellipsis is often used as undefined
                            is_required = False
                            default_value = field_info.default
                    except:
                        pass
                
                field_schema = {
                    "type": field_type,
                    "description": description,
                    "required": is_required,
                    "default": default_value
                }
                
                # For object types (nested models), extract nested schema
                if field_type == "object" and hasattr(field_info, 'annotation'):
                    model_name = getattr(model_class, "__name__", "")
                    nested_schema = cls._extract_nested_object_schema(field_info.annotation, field_name, model_name)
                    if nested_schema:
                        field_schema["properties"] = nested_schema

                # For arrays of nested models (e.g. List[WakeWordSpec]), extract the item schema so the
                # schema-driven UI can render a structured editor instead of a string list (QUAL-20).
                if field_type == "array" and hasattr(field_info, 'annotation'):
                    item_schema = cls._extract_array_item_schema(field_info.annotation)
                    if item_schema:
                        field_schema["items"] = item_schema
                
                # Add constraints if available (from field annotations)
                if hasattr(field_info, 'json_schema_extra') and isinstance(field_info.json_schema_extra, dict):
                    field_schema.update(field_info.json_schema_extra)
                
                schema["fields"][field_name] = field_schema
                
            except Exception as e:
                logger.warning(f"Failed to extract schema for field {field_name}: {e}")
                # Add a basic fallback schema
                schema["fields"][field_name] = {
                    "type": "string",
                    "description": f"Field {field_name}",
                    "required": False,
                    "default": None
                }
        
        return schema
    
    @classmethod
    def _get_field_type(cls, field_info) -> str:
        """Determine field type for widget generation"""
        try:
            # Extract type from Pydantic field info
            field_type = field_info.annotation if hasattr(field_info, 'annotation') else str
            
            return cls._get_field_type_from_annotation(field_type)
        except Exception as e:
            logger.warning(f"Failed to determine field type: {e}")
            return "string"  # Safe fallback
    
    @classmethod
    def _get_field_type_from_annotation(cls, annotation) -> str:
        """Helper to get field type from type annotation"""
        try:
            # Handle direct types
            if annotation == bool:
                return "boolean"
            elif annotation == int:
                return "integer"
            elif annotation == float:
                return "number"
            elif annotation == str:
                return "string"
            elif hasattr(annotation, '__origin__'):
                # Handle generic types like List, Dict, Optional
                from typing import Union
                origin = annotation.__origin__
                if origin == list:
                    return "array"
                elif origin == dict:
                    return "object"
                elif origin == Union:
                    # Handle Optional types
                    args = annotation.__args__
                    if len(args) == 2 and type(None) in args:
                        # Optional type - get the non-None type
                        non_none_type = next(arg for arg in args if arg != type(None))
                        return cls._get_field_type_from_annotation(non_none_type)
            
            # Check if it's a Pydantic BaseModel (nested configuration)
            if hasattr(annotation, '__bases__') and any(
                issubclass(base, BaseModel) for base in annotation.__bases__ 
                if hasattr(base, '__name__')
            ):
                return "object"  # Nested Pydantic models should be objects
            
            # Check if it's an Enum
            if hasattr(annotation, '__bases__') and any(base.__name__ == 'Enum' for base in annotation.__bases__):
                return "string"  # Enums are represented as string choices
                
            return "string"  # Default fallback
        except Exception as e:
            logger.warning(f"Failed to parse annotation {annotation}: {e}")
            return "string"
    
    @classmethod
    def _extract_nested_object_schema(cls, annotation, field_name: str = "", parent_model_name: str = "") -> Optional[Dict[str, Any]]:
        """Extract schema for nested Pydantic models"""
        try:
            # Handle Optional[Model] types
            from typing import Union
            if hasattr(annotation, '__origin__') and annotation.__origin__ == Union:
                args = annotation.__args__
                if len(args) == 2 and type(None) in args:
                    # Optional type - get the non-None type
                    annotation = next(arg for arg in args if arg != type(None))
            
            # Special handling for provider fields using AutoSchemaRegistry
            if field_name == "providers" and parent_model_name:
                return cls._extract_provider_schemas(parent_model_name)
            
            # Check if it's a Pydantic BaseModel
            if (hasattr(annotation, '__bases__') and 
                any(issubclass(base, BaseModel) for base in annotation.__bases__ if hasattr(base, '__name__'))):
                
                # Recursively extract schema for the nested model
                nested_model_schema = cls._extract_model_schema(annotation)
                return nested_model_schema.get("fields", {})
            
            return None
        except Exception as e:
            logger.warning(f"Failed to extract nested schema for {annotation}: {e}")
            return None
    
    @classmethod
    def _extract_array_item_schema(cls, annotation) -> Optional[Dict[str, Any]]:
        """For a `List[Model]` annotation, return the item's object schema
        (`{"type": "object", "properties": {...}}`); ``None`` for plain arrays like `List[str]`."""
        try:
            if get_origin(annotation) is not list:
                return None
            args = get_args(annotation)
            if not args:
                return None
            item_type = args[0]
            if (hasattr(item_type, '__bases__') and
                    any(issubclass(base, BaseModel) for base in item_type.__bases__ if hasattr(base, '__name__'))):
                fields = cls._extract_model_schema(item_type).get("fields", {})
                return {"type": "object", "properties": fields}
            return None
        except Exception as e:
            logger.warning(f"Failed to extract array item schema for {annotation}: {e}")
            return None

    @classmethod
    def _extract_provider_schemas(cls, component_type: str) -> Dict[str, Any]:
        """Extract provider schemas for a specific component type using AutoSchemaRegistry"""
        try:
            # Map config model names to component types
            component_type_mapping = {
                "TTSConfig": "tts",
                "AudioConfig": "audio", 
                "ASRConfig": "asr",
                "LLMConfig": "llm",
                "VoiceTriggerConfig": "voice_trigger",
                "VADConfig": "vad",
                "NLUConfig": "nlu",
                "TextProcessorConfig": "text_processor"
            }
            
            component_name = component_type_mapping.get(component_type, component_type.lower().replace("config", ""))
            
            # Get provider schemas from AutoSchemaRegistry
            provider_schemas = AutoSchemaRegistry.get_provider_schemas()
            component_providers = provider_schemas.get(component_name, {})
            
            provider_properties = {}
            for provider_name, schema_class in component_providers.items():
                try:
                    # Generate schema for this provider (no instantiation needed)
                    provider_schema = cls._extract_model_schema(schema_class)
                    provider_properties[provider_name] = {
                        "type": "object",
                        "description": f"{provider_name} provider configuration",
                        "properties": provider_schema.get("fields", {})
                    }
                except Exception as e:
                    logger.warning(f"Failed to extract schema for provider {provider_name}: {e}")
                    
            return provider_properties
            
        except Exception as e:
            logger.warning(f"Failed to extract provider schemas for {component_type}: {e}")
            return {}
    
    @classmethod
    def validate_schema_coverage(cls) -> Dict[str, Any]:
        """Validate schema coverage and return validation report"""
        report = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "recommendations": []
        }
        
        # Validate section model coverage.
        # QUAL-6: only fields whose type *is* a Pydantic section model are expected to
        # appear in the registry. Scalar top-level fields (name/version/debug/log_level/
        # language knobs/timeouts) legitimately have no section model, so comparing the
        # registry against *all* CoreConfig fields produced a permanent false-positive
        # warning on every startup. Compare against the actual section fields instead;
        # a non-empty diff now means a real registration drop worth surfacing.
        section_models = cls.get_section_models()
        from .models import CoreConfig
        expected_sections = {
            field_name
            for field_name, field_info in CoreConfig.model_fields.items()
            if cls._resolve_section_model(getattr(field_info, 'annotation', None)) is not None
        }
        section_model_fields = set(section_models.keys())

        missing_sections = expected_sections - section_model_fields
        if missing_sections:
            report["warnings"].append(f"Section-model fields missing from registry: {missing_sections}")
        
        # Validate component schema coverage
        component_schemas = cls.get_component_schemas()
        from .models import ComponentConfig
        component_fields = set(ComponentConfig.model_fields.keys())
        schema_fields = set(component_schemas.keys())
        
        missing_component_schemas = component_fields - schema_fields
        if missing_component_schemas:
            # Phase 2: Missing component schemas are now errors (all schemas should exist)
            report["errors"].append(f"Components without schemas: {missing_component_schemas}")
            report["valid"] = False
            
            for missing in missing_component_schemas:
                report["recommendations"].append(f"Create {missing.title()}ComponentSchema class")
        
        return report
    
    @classmethod
    def _find_component_schema(cls, component_name: str) -> Optional[Type[BaseModel]]:
        """Find component schema class by component name (auto-discovery only)"""
        # Import all component schemas and find by naming convention
        try:
            from .schemas import (
                TTSComponentSchema, AudioComponentSchema, ASRComponentSchema, 
                LLMComponentSchema, VoiceTriggerComponentSchema, NLUComponentSchema,
                TextProcessorComponentSchema, IntentSystemComponentSchema,
                MonitoringComponentSchema, NLUAnalysisComponentSchema, ConfigurationComponentSchema
            )
            
            # Map component names to schema classes
            component_schema_map = {
                "tts": TTSComponentSchema,
                "audio": AudioComponentSchema,
                "asr": ASRComponentSchema,
                "llm": LLMComponentSchema,
                "voice_trigger": VoiceTriggerComponentSchema,
                "nlu": NLUComponentSchema,
                "text_processor": TextProcessorComponentSchema,
                "intent_system": IntentSystemComponentSchema,
                "monitoring": MonitoringComponentSchema,
                "nlu_analysis": NLUAnalysisComponentSchema,
                "configuration": ConfigurationComponentSchema,
            }
            
            return component_schema_map.get(component_name)
            
        except ImportError as e:
            logger.warning(f"Failed to import component schema for {component_name}: {e}")
            return None
    
    @classmethod
    def get_master_config_completeness(cls, master_config_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Analyze config-master.toml completeness against provider schemas AND (ARCH-15 PR-9.2) the
        top-level config sections + their scalar fields. Returns a report of missing/orphaned items.

        `master_config_path` defaults to ``configs/config-master.toml``; override it (e.g. with a
        drifted copy) to test drift detection.
        """
        report = {
            "missing_sections": [],
            "orphaned_sections": [],
            "coverage_percentage": 0.0,
            "valid": True
        }

        try:
            # Load master config
            if master_config_path is None:
                master_config_path = Path("configs/config-master.toml")
            if not master_config_path.exists():
                report["valid"] = False
                report["missing_sections"].append("ENTIRE_MASTER_CONFIG_MISSING")
                return report
            
            with open(master_config_path, "rb") as f:
                master_config = tomllib.load(f)
            
            # Get all provider schemas
            provider_schemas = cls.get_provider_schemas()
            
            expected_sections = set()
            for component_type, providers in provider_schemas.items():
                for provider_name in providers.keys():
                    expected_sections.add(f"{component_type}.providers.{provider_name}")
            
            # Check config-master.toml sections
            actual_sections = set()
            for component_type, component_config in master_config.items():
                if isinstance(component_config, dict) and "providers" in component_config:
                    for provider_name in component_config["providers"].keys():
                        actual_sections.add(f"{component_type}.providers.{provider_name}")
            
            # Calculate missing and orphaned
            report["missing_sections"] = list(expected_sections - actual_sections)
            report["orphaned_sections"] = list(actual_sections - expected_sections)
            
            if expected_sections:
                report["coverage_percentage"] = (len(actual_sections & expected_sections) / len(expected_sections)) * 100

            # ARCH-15 PR-9.2: also validate TOP-LEVEL config sections + their scalar fields against the
            # schema (the provider check above only covers `*.providers.*`). This catches reference
            # drift like the missing `[outputs]` section / `observe_*` fields (synced 2026-06-07).
            # A scalar field counts as documented if its key appears anywhere in the file TEXT — live
            # OR a commented example (so an intentionally-commented optional like `observe_token` is not
            # a false positive). Dict/List/nested-model fields are tables, validated at section
            # granularity, so they are skipped at field level.
            master_text = master_config_path.read_text(encoding="utf-8")
            missing_top_level_sections = []
            missing_fields = []
            for section_name, model in cls.get_section_models().items():
                if section_name not in master_config:
                    missing_top_level_sections.append(section_name)
                    continue
                for field_name, field_info in model.model_fields.items():
                    if not cls._is_scalar_annotation(getattr(field_info, "annotation", None)):
                        continue
                    if re.search(rf"(?m)^\s*#?\s*{re.escape(field_name)}\s*=", master_text) is None:
                        missing_fields.append(f"{section_name}.{field_name}")
            report["missing_top_level_sections"] = missing_top_level_sections
            report["missing_fields"] = missing_fields
            if missing_top_level_sections or missing_fields:
                report["valid"] = False

            logger.debug(f"Master config analysis: {len(expected_sections)} expected, {len(actual_sections)} actual")
            
        except Exception as e:
            logger.error(f"Master config analysis failed: {e}")
            report["valid"] = False
        
        return report
    
    @classmethod
    def validate_provider_config(cls, component_type: str, provider_name: str, config: Dict[str, Any]) -> bool:
        """Validate provider configuration using auto-discovery"""
        provider_schemas = cls.get_provider_schemas()
        
        if component_type not in provider_schemas:
            return False
        
        if provider_name not in provider_schemas[component_type]:
            return False
        
        schema_class = provider_schemas[component_type][provider_name]
        try:
            schema_class.model_validate(config)
            return True
        except Exception:
            return False
    
    @classmethod
    def validate_component_config(cls, component_type: str, config: Dict[str, Any]) -> bool:
        """Validate component configuration using auto-discovery"""
        component_schemas = cls.get_component_schemas()
        
        if component_type not in component_schemas:
            return False
        
        schema_class = component_schemas[component_type]
        try:
            schema_class.model_validate(config)
            return True
        except Exception:
            return False
    
    @classmethod
    def get_section_order_and_titles(cls) -> Dict[str, Any]:
        """Get section order and titles for frontend auto-generation"""
        section_models = cls.get_section_models()
        
        # Define logical ordering for sections
        preferred_order = [
            'system', 'inputs', 'outputs', 'components',  # Core sections first
            'tts', 'audio', 'asr', 'llm',      # Main components
            'voice_trigger', 'nlu', 'nlu_analysis', 'text_processor', 'intent_system',  # Advanced components
            'vad', 'monitoring', 'trace',      # Utility components
            'assets', 'workflows'              # System components
        ]
        
        # Generate section order based on available sections and preferred order
        available_sections = set(section_models.keys())
        section_order = []
        
        # Add sections in preferred order if they exist
        for section in preferred_order:
            if section in available_sections:
                section_order.append(section)
                available_sections.remove(section)
        
        # Add any remaining sections not in preferred order
        section_order.extend(sorted(available_sections))
        
        # Generate titles with emojis
        section_titles = {
            'system': '🔧 Core Settings',
            'inputs': '📝 Input Sources',
            'outputs': '📤 Output Channels',
            'components': '🔌 Components',
            'tts': '🗣️ Text-to-Speech',
            'audio': '🔊 Audio Playback',
            'asr': '🎤 Speech Recognition',
            'llm': '🤖 Language Models',
            'voice_trigger': '👂 Voice Trigger',
            'nlu': '🧠 Natural Language Understanding',
            'nlu_analysis': '🔍 NLU Analysis',
            'text_processor': '📝 Text Processing',
            'intent_system': '🎯 Intent System',
            'vad': '🔊 Voice Activity Detection',
            'monitoring': '📊 Monitoring',
            'trace': '🧪 Trace Persistence',
            'assets': '📁 Asset Management',
            'workflows': '⚡ Workflows'
        }
        
        # Generate titles for sections not in the predefined map
        for section in section_order:
            if section not in section_titles:
                # Convert snake_case to Title Case
                title = section.replace('_', ' ').title()
                section_titles[section] = f"⚙️ {title}"
        
        return {
            "section_order": section_order,
            "section_titles": section_titles,
            "total_sections": len(section_order)
        }
    
    @classmethod
    def get_provider_parameter_schema(cls, component_type: str, provider_name: str) -> Dict[str, Any]:
        """
        Auto-generate runtime parameter schema from Pydantic model.
        Eliminates need for manual get_parameter_schema() implementations.
        """
        provider_schemas = cls.get_provider_schemas()
        
        if component_type not in provider_schemas:
            logger.warning(f"Component type not found: {component_type}")
            return {}
        
        if provider_name not in provider_schemas[component_type]:
            logger.warning(f"Provider not found: {component_type}.{provider_name}")
            return {}
        
        schema_class = provider_schemas[component_type][provider_name]
        
        try:
            # Generate JSON Schema from Pydantic model
            json_schema = schema_class.model_json_schema()
            
            # Convert to runtime parameter format expected by Web API
            parameter_schema = cls._convert_json_schema_to_parameter_format(json_schema)
            
            logger.debug(f"Auto-generated parameter schema for {component_type}.{provider_name}")
            return parameter_schema
            
        except Exception as e:
            logger.error(f"Failed to generate parameter schema for {component_type}.{provider_name}: {e}")
            return {}

    @classmethod
    def _convert_json_schema_to_parameter_format(cls, json_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Pydantic JSON Schema to parameter schema format"""
        parameters = {}
        definitions = json_schema.get("$defs", {})
        
        def resolve_ref(ref_path: str) -> Dict[str, Any]:
            """Resolve $ref path to actual definition"""
            if ref_path.startswith("#/$defs/"):
                ref_name = ref_path.replace("#/$defs/", "")
                return definitions.get(ref_name, {})
            return {}
        
        def convert_field_schema(field_schema: Dict[str, Any]) -> Dict[str, Any]:
            """Convert individual field schema, handling $ref references"""
            # Handle $ref references
            if "$ref" in field_schema:
                resolved_schema = resolve_ref(field_schema["$ref"])
                if resolved_schema:
                    return convert_nested_object(resolved_schema, field_schema.get("description", ""))
            
            # Handle direct object types
            if field_schema.get("type") == "object" and "properties" in field_schema:
                return convert_nested_object(field_schema, field_schema.get("description", ""))
            
            # Handle simple types
            param_schema = {
                "type": field_schema.get("type", "string"),
                "description": field_schema.get("description", ""),
            }
            
            # Add constraints
            if "minimum" in field_schema:
                param_schema["minimum"] = field_schema["minimum"]
            if "maximum" in field_schema:
                param_schema["maximum"] = field_schema["maximum"]
            if "enum" in field_schema:
                param_schema["options"] = field_schema["enum"]
            if "default" in field_schema:
                param_schema["default"] = field_schema["default"]
                
            return param_schema
        
        def convert_nested_object(obj_schema: Dict[str, Any], description: str = "") -> Dict[str, Any]:
            """Convert nested object to parameter format with properties"""
            nested_params = {}
            
            for prop_name, prop_schema in obj_schema.get("properties", {}).items():
                nested_params[prop_name] = convert_field_schema(prop_schema)
            
            return {
                "type": "object",
                "description": description,
                "properties": nested_params
            }
        
        properties = json_schema.get("properties", {})
        for field_name, field_schema in properties.items():
            # Skip non-runtime fields
            if field_name in ["enabled"]:  # Configuration-only fields
                continue
                
            parameters[field_name] = convert_field_schema(field_schema)
        
        return parameters

    @classmethod
    def clear_cache(cls) -> None:
        """Clear all cached registries (for testing/development)"""
        cls._section_models_cache = None
        cls._component_schemas_cache = None
        cls._provider_schemas_cache = None
        logger.debug("Auto-schema registry cache cleared")
