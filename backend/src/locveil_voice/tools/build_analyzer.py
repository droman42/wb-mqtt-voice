"""
Irene Voice Assistant - Runtime Build Analyzer Tool

This module provides the core analysis engine for creating minimal builds
by analyzing TOML configuration + entry-points metadata to determine
precisely which modules and dependencies are required.

Usage:
    python -m locveil_voice.tools.build_analyzer --config config/embedded-armv7.toml
    python -m locveil_voice.tools.build_analyzer --list-profiles
    python -m locveil_voice.tools.build_analyzer --validate-all-profiles
"""

import argparse
import logging
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from ..core.metadata import SUPPORTED_PLATFORMS
from typing import Dict, List, Optional, Set, Any, Tuple
import json

from locveil_voice.utils.loader import dynamic_loader

logger = logging.getLogger(__name__)


@dataclass
class BuildRequirements:
    """Container for analyzed build requirements."""
    # Python modules that need to be included
    python_modules: Set[str] = field(default_factory=set)
    
    # System packages that need to be installed
    system_packages: Dict[str, Set[str]] = field(default_factory=dict)  # platform -> packages
    
    # Python dependencies from entry-point metadata
    python_dependencies: Set[str] = field(default_factory=set)
    
    # Entry-points namespaces and enabled providers
    enabled_providers: Dict[str, List[str]] = field(default_factory=dict)
    
    # Intent JSON configuration files that must be included and validated
    intent_json_files: Set[str] = field(default_factory=set)
    
    # Configuration profile name
    profile_name: str = ""

    # BUG-21: whether the profile serves the web API — a TTS reply can leave through the
    # WS reply channel (ARCH-22 satellites) even with no local audio provider.
    web_api_enabled: bool = False

    # Validation results
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of build profile validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    missing_dependencies: Set[str] = field(default_factory=set)
    conflicting_providers: List[Tuple[str, str]] = field(default_factory=list)


class IreneBuildAnalyzer:
    """
    Core build analyzer for Irene Voice Assistant.
    
    Analyzes TOML configuration + entry-points metadata to generate
    minimal build requirements for different deployment scenarios.
    
    Phase 3 Implementation (TODO #5): Dynamic metadata queries replace all hardcoded mappings.
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the build analyzer.
        
        Args:
            project_root: Path to project root. If None, auto-detect from current directory.
        """
        self.project_root = project_root or self._find_project_root()
        self.configs_dir = self.project_root / "config"
        self.pyproject_path = self._resolve_pyproject(self.project_root)
        
        # Cache for loaded configurations and entry-points
        self._config_cache: Dict[str, Dict[str, Any]] = {}
        self._entry_points_cache: Optional[Dict[str, List[str]]] = None
        self._metadata_cache: Dict[str, Any] = {}  # Cache for provider metadata
        
        # Platform mapping for backward compatibility
        self._platform_mapping = {
            "ubuntu": "linux.ubuntu",
            "alpine": "linux.alpine",
            "centos": None,  # Removed - will error
            "macos": "macos",
            "windows": "windows"
        }
        
    def _find_project_root(self) -> Path:
        """Find the repo/data root — the directory holding the config/ profile tree
        (and assets/).

        Post-migration (PROD-21/BUILD-36) the backend component lives in backend/ with
        its own pyproject.toml, while config/ and assets/ stay at the repo root; the
        Docker analyzer stage flattens both into one dir. Both shapes carry
        config/config-master.toml, so that is the definitive marker — preferred over a
        bare pyproject.toml, which under the split layout would stop at backend/.
        """
        current = Path.cwd()
        probe = current
        while probe != probe.parent:
            if (probe / "config" / "config-master.toml").exists():
                return probe
            probe = probe.parent
        # Fallback: the component root (pyproject.toml), then cwd.
        probe = current
        while probe != probe.parent:
            if (probe / "pyproject.toml").exists():
                return probe
            probe = probe.parent
        return current

    def _resolve_pyproject(self, root: Path) -> Path:
        """pyproject.toml lives in backend/ under the split layout, or at the data
        root when the Docker analyzer stage has flattened the tree."""
        split = root / "backend" / "pyproject.toml"
        return split if split.exists() else root / "pyproject.toml"
    
    def _normalize_platform_name(self, platform: str) -> str:
        """
        Normalize platform name for backward compatibility.
        
        Args:
            platform: Original platform name (may be old format)
            
        Returns:
            Normalized platform name (new format)
            
        Raises:
            ValueError: If platform is not supported
        """
        if platform in list(SUPPORTED_PLATFORMS):
            # Already using new format
            return platform
        
        if platform in self._platform_mapping:
            mapped = self._platform_mapping[platform]
            if mapped is None:
                raise ValueError(f"Platform '{platform}' is no longer supported (removed in Phase 2)")
            
            logger.warning(f"Platform '{platform}' is deprecated, use '{mapped}' instead")
            return mapped
        
        raise ValueError(f"Unknown platform '{platform}'. Supported platforms: linux.ubuntu, linux.alpine, macos, windows")
    
    def analyze_runtime_requirements(self, config_path: str) -> BuildRequirements:
        """
        Analyze a configuration file to determine runtime requirements.
        
        Args:
            config_path: Path to TOML configuration file
            
        Returns:
            BuildRequirements object with analyzed dependencies
        """
        config_file = Path(config_path)
        if not config_file.exists():
            # Try relative to configs directory
            config_file = self.configs_dir / config_path
            if not config_file.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        # Load and parse configuration
        config = self._load_config(config_file)
        
        # Initialize requirements
        requirements = BuildRequirements(profile_name=config_file.stem)
        # BUG-21: record the web-API reply-channel capability for validation (see
        # _validate_critical_providers — satellite profiles do TTS with no local audio).
        requirements.web_api_enabled = bool(config.get("system", {}).get("web_api_enabled", False))
        
        # Analyze enabled providers across all namespaces
        self._analyze_providers(config, requirements)
        
        # Analyze enabled components
        self._analyze_components(config, requirements)
        
        # Analyze enabled workflows
        self._analyze_workflows(config, requirements)
        
        # Analyze enabled plugins
        self._analyze_plugins(config, requirements)
        
        # Analyze enabled intent handlers
        self._analyze_intent_handlers(config, requirements)
        
        # Generate dependency mappings using dynamic metadata queries
        self._generate_dependencies_from_metadata(requirements)
        
        logger.info(f"Analyzed requirements for profile '{requirements.profile_name}': "
                   f"{len(requirements.python_modules)} modules, "
                   f"{sum(len(pkgs) for pkgs in requirements.system_packages.values())} system packages, "
                   f"{len(requirements.python_dependencies)} Python deps")
        
        return requirements
    
    def list_available_profiles(self) -> List[str]:
        """
        Scan config/ directory for available configuration profiles.
        
        Returns:
            List of available profile names (without .toml extension)
        """
        if not self.configs_dir.exists():
            logger.warning(f"Configs directory not found: {self.configs_dir}")
            return []
        
        profiles = []
        for config_file in self.configs_dir.glob("*.toml"):
            profiles.append(config_file.stem)
        
        logger.info(f"Found {len(profiles)} configuration profiles: {profiles}")
        return sorted(profiles)
    
    def validate_build_profile(self, requirements: BuildRequirements) -> ValidationResult:
        """
        Validate a build profile for completeness and conflicts.
        
        Args:
            requirements: BuildRequirements to validate
            
        Returns:
            ValidationResult with validation status and issues
        """
        result = ValidationResult(is_valid=True)
        
        # Check for missing critical providers
        self._validate_critical_providers(requirements, result)
        
        # Check for dependency conflicts
        self._validate_dependency_conflicts(requirements, result)
        
        # Check for missing entry-points
        self._validate_entry_points(requirements, result)
        
        # Validate provider compatibility using metadata
        self._validate_provider_metadata(requirements, result)
        
        # Validate intent JSON configurations
        self._validate_intent_json_files(requirements, result)
        
        # Set overall validation status
        result.is_valid = len(result.errors) == 0
        
        if result.is_valid:
            logger.info(f"Profile '{requirements.profile_name}' validation: PASSED")
        else:
            logger.error(f"Profile '{requirements.profile_name}' validation: FAILED "
                        f"({len(result.errors)} errors, {len(result.warnings)} warnings)")
        
        return result
    
    def generate_docker_commands(self, requirements: BuildRequirements, platform: str = "linux.ubuntu") -> List[str]:
        """
        Generate Docker commands for installing system dependencies.
        
        Args:
            requirements: BuildRequirements with system packages
            platform: Target platform (linux.ubuntu, linux.alpine, macos, windows)
            
        Returns:
            List of Docker RUN commands
        """
        # Normalize platform name for backward compatibility
        normalized_platform = self._normalize_platform_name(platform)
        packages = requirements.system_packages.get(normalized_platform, set())
        if not packages:
            return []
        
        # Sort packages for consistent output
        sorted_packages = sorted(packages)
        
        if normalized_platform == "linux.alpine":
            commands = [
                "# Install system dependencies for enabled providers",
                "RUN apk update && apk add --no-cache \\",
            ]
            
            # Add packages with proper line continuation
            for i, package in enumerate(sorted_packages):
                is_last = (i == len(sorted_packages) - 1)
                line = f"    {package}"
                if not is_last:
                    line += " \\"
                commands.append(line)
                
        elif normalized_platform == "linux.ubuntu":  # ubuntu/debian
            commands = [
                "# Install system dependencies for enabled providers",
                "RUN apt-get update && apt-get install -y \\",
            ]
            
            # Add packages with proper line continuation
            for i, package in enumerate(sorted_packages):
                is_last = (i == len(sorted_packages) - 1)
                line = f"    {package}"
                if not is_last:
                    line += " \\"
                commands.append(line)
            
            # Clean up apt cache
            commands.extend([
                "    && apt-get clean \\",
                "    && rm -rf /var/lib/apt/lists/*"
            ])
        
        else:
            # For macos and windows, Docker commands are not typically used
            commands = [
                f"# Docker installation not supported for platform: {normalized_platform}",
                f"# System packages needed: {', '.join(sorted_packages)}"
            ]
        
        return commands
    
    def generate_system_install_commands(self, requirements: BuildRequirements, platform: str = "linux.ubuntu") -> List[str]:
        """
        Generate system installation commands for different platforms.
        
        Args:
            requirements: BuildRequirements with system packages
            platform: Target platform (linux.ubuntu, linux.alpine, macos, windows)
            
        Returns:
            List of installation commands
        """
        # Normalize platform name for backward compatibility
        normalized_platform = self._normalize_platform_name(platform)
        packages = requirements.system_packages.get(normalized_platform, set())
        if not packages:
            return []
        
        sorted_packages = sorted(packages)
        package_list = " ".join(sorted_packages)
        
        if normalized_platform == "linux.ubuntu":
            return [
                "# Install system dependencies",
                f"sudo apt-get update",
                f"sudo apt-get install -y {package_list}",
            ]
        elif normalized_platform == "linux.alpine":
            return [
                "# Install system dependencies",
                f"sudo apk update",
                f"sudo apk add {package_list}",
            ]
        elif normalized_platform == "macos":
            return [
                "# Install system dependencies",
                f"brew update",
                f"brew install {package_list}",
            ]
        elif normalized_platform == "windows":
            return [
                "# Install system dependencies",
                f"# Windows system package installation varies by package manager",
                f"# Required packages: {package_list}",
                f"# Consider using chocolatey, winget, or vcpkg",
            ]
        else:
            return [f"# Unknown platform: {normalized_platform}"]
    
    def generate_python_requirements(self, requirements: BuildRequirements) -> List[str]:
        """
        Generate Python requirements for UV installation.
        
        Args:
            requirements: BuildRequirements with Python dependencies
            
        Returns:
            List of specific Python package requirements
        """
        return sorted(requirements.python_dependencies)
    
    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """Load and cache TOML configuration."""
        cache_key = str(config_path)
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]
        
        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)
            self._config_cache[cache_key] = config
            return config
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration {config_path}: {e}")
    
    def _discover_entry_point_namespaces(self) -> List[str]:
        """
        Dynamically discover all entry-point namespaces from pyproject.toml.
        
        Replaces hardcoded namespace list (lines 364-379 in original).
        """
        if not self.pyproject_path.exists():
            logger.warning(f"pyproject.toml not found at {self.pyproject_path}")
            return []
        
        try:
            with open(self.pyproject_path, "rb") as f:
                pyproject = tomllib.load(f)
            
            # Extract all namespaces from entry-points sections
            entry_points = pyproject.get("project", {}).get("entry-points", {})
            namespaces = [ns for ns in entry_points.keys() if ns.startswith("locveil_voice.")]
            
            logger.debug(f"Discovered {len(namespaces)} entry-point namespaces: {namespaces}")
            return sorted(namespaces)
            
        except Exception as e:
            logger.error(f"Failed to discover entry-point namespaces: {e}")
            # Fallback to the canonical registry (ARCH-57 — the old inline list had
            # drifted, naming a phantom `locveil_voice.outputs` group).
            from ..utils.namespaces import ALL_NAMESPACES
            return sorted(ALL_NAMESPACES)
    
    def _get_entry_points_catalog(self) -> Dict[str, List[str]]:
        """Get all entry-points from dynamic discovery."""
        if self._entry_points_cache is not None:
            return self._entry_points_cache
        
        # Use dynamic discovery instead of hardcoded list
        namespaces = self._discover_entry_point_namespaces()
        
        catalog = {}
        for namespace in namespaces:
            providers = dynamic_loader.list_available_providers(namespace)
            catalog[namespace] = providers
        
        self._entry_points_cache = catalog
        return catalog
    
    def _get_provider_metadata(self, namespace: str, provider_name: str) -> Optional[Any]:
        """
        Get provider class metadata using dynamic loading.
        
        Args:
            namespace: Entry-point namespace
            provider_name: Provider name
            
        Returns:
            Provider class with metadata methods or None if not found
        """
        cache_key = f"{namespace}.{provider_name}"
        if cache_key in self._metadata_cache:
            return self._metadata_cache[cache_key]
        
        try:
            provider_class = dynamic_loader.get_provider_class(namespace, provider_name)
            if provider_class is None:
                logger.warning(f"Provider class not found: {namespace}.{provider_name}")
                return None
                
            # Verify the class has metadata methods
            if not hasattr(provider_class, 'get_python_dependencies'):
                logger.warning(f"Provider {provider_name} missing metadata methods")
                return None
                
            self._metadata_cache[cache_key] = provider_class
            return provider_class
            
        except Exception as e:
            logger.error(f"Failed to load provider metadata for {namespace}.{provider_name}: {e}")
            return None

    def validate_architecture(self, config_path: str, arch: str) -> List[str]:
        """ARCH-24 T3 gate: enabled providers in a profile that can't run on `arch`.

        Reuses the standard enabled-provider analysis, then checks each provider's
        `get_supported_architectures()`. Returns a list of human-readable errors (empty = OK), so an
        armv7 image can't be built with a torch / standalone-onnxruntime provider.
        """
        requirements = self.analyze_runtime_requirements(config_path)
        errors: List[str] = []
        for namespace, providers in requirements.enabled_providers.items():
            if not namespace.startswith("locveil_voice.providers."):
                continue  # components/workflows aren't arch-gated here
            component = namespace.rsplit(".", 1)[-1]
            for provider_name in providers:
                provider_class = self._get_provider_metadata(namespace, provider_name)
                if provider_class is None:
                    continue  # unresolved provider is a separate validation concern
                try:
                    archs = provider_class.get_supported_architectures()
                except Exception as e:  # pragma: no cover - defensive
                    errors.append(f"{component}.{provider_name}: get_supported_architectures() raised: {e}")
                    continue
                if arch not in archs:
                    errors.append(
                        f"{component} provider '{provider_name}' does not support '{arch}' (supports {archs}) "
                        f"— remove it from this profile or pick an {arch}-capable provider"
                    )
        return errors

    def _analyze_providers(self, config: Dict[str, Any], requirements: BuildRequirements):
        """
        Analyze enabled providers from configuration.
        
        Supports both array-based and object-based configurations:
        Array-based: providers.tts.enabled = ["elevenlabs", "console"]
        Object-based: providers.tts.elevenlabs.enabled = true
        """
        providers_config = config.get("providers", {})
        
        for provider_type, type_config in providers_config.items():
            if not isinstance(type_config, dict):
                continue
            
            enabled_providers = []
            
            # Method 1: Array-based enabled list (e.g., providers.tts.enabled = ["elevenlabs"])
            enabled_list = type_config.get("enabled", [])
            if enabled_list and isinstance(enabled_list, list):
                enabled_providers.extend(enabled_list)
            
            # Method 2: Object-based individual provider configs (e.g., providers.tts.elevenlabs.enabled = true)
            for key, value in type_config.items():
                if key in ["enabled", "disabled", "default", "fallback_providers"]:
                    continue  # Skip meta-configuration keys
                
                if isinstance(value, dict) and value.get("enabled", False):
                    enabled_providers.append(key)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_enabled = []
            for provider in enabled_providers:
                if provider not in seen:
                    seen.add(provider)
                    unique_enabled.append(provider)
            
            if unique_enabled:
                namespace = f"locveil_voice.providers.{provider_type}"
                requirements.enabled_providers[namespace] = unique_enabled
                
                # Add provider modules to requirements
                for provider_name in unique_enabled:
                    module_path = f"locveil_voice.providers.{provider_type}.{provider_name}"
                    requirements.python_modules.add(module_path)
                
                logger.debug(f"Standard providers found: {namespace} -> {unique_enabled}")
    
    def _analyze_components(self, config: Dict[str, Any], requirements: BuildRequirements):
        """
        Analyze enabled components from configuration.

        ARCH-54: the [components] block is the ONE enablement authority —
        [components] tts = true — replacing the per-section `enabled` flags the
        runtime used to silently overwrite (and this analyzer used to read raw).
        """
        components_config = config.get("components", {})
        unique_enabled = [name for name, on in components_config.items()
                          if isinstance(on, bool) and on]
        
        if unique_enabled:
            requirements.enabled_providers["locveil_voice.components"] = unique_enabled
            # Module paths come from the entry-point VALUES, not a naming convention —
            # the old f"...{name}_component" derivation minted the phantom module
            # `intent_system_component` (the real file is intent_component.py). ARCH-57.
            from importlib.metadata import entry_points
            from ..utils.namespaces import COMPONENTS_NAMESPACE
            component_modules = {ep.name: ep.value.split(":")[0]
                                 for ep in entry_points(group=COMPONENTS_NAMESPACE)}
            for component_name in unique_enabled:
                module_path = component_modules.get(component_name)
                if module_path:
                    requirements.python_modules.add(module_path)
                else:
                    logger.warning(f"Component '{component_name}' has no entry point in "
                                   f"{COMPONENTS_NAMESPACE}; no module recorded")

            logger.debug(f"Components found: {unique_enabled}")
        
        # Analyze component-based providers (e.g., tts.providers.*, nlu.providers.*)
        self._analyze_component_providers(config, requirements)
    
    def _analyze_component_providers(self, config: Dict[str, Any], requirements: BuildRequirements):
        """
        Analyze component-based providers from configuration.
        
        Structure uses individual component sections:
        [tts]
        enabled = true
        default_provider = "elevenlabs"
        
        [tts.providers.elevenlabs]
        enabled = true
        api_key = "${ELEVENLABS_API_KEY}"
        """
        # ARCH-54/ARCH-57: iterate the canonical provider families (incl. vad — the old
        # 8-name hand-list silently skipped it, so VAD provider deps never reached images).
        # Enablement: [components] for component families; [vad].enabled for vad (not a
        # component — model default True).
        from ..utils.namespaces import PROVIDER_NAMESPACES
        components_config = config.get("components", {})

        for component_name, family_namespace in PROVIDER_NAMESPACES.items():
            component_config = config.get(component_name, {})
            if not isinstance(component_config, dict):
                continue

            if component_name == "vad":
                if not component_config.get("enabled", True):
                    continue
            elif not components_config.get(component_name, False):
                continue
                
            # Extract enabled providers from multiple sources
            enabled_providers = []
            
            # Method 1: Explicit provider subsections with enabled flags
            providers_config = component_config.get("providers", {})
            for provider_name, provider_config in providers_config.items():
                if isinstance(provider_config, dict) and provider_config.get("enabled", False):
                    enabled_providers.append(provider_name)
            
            # Method 2: default_provider (always considered enabled if component is enabled)
            default_provider = component_config.get("default_provider")
            if default_provider and default_provider not in enabled_providers:
                enabled_providers.append(default_provider)
                
            # Method 3: fallback_providers (always considered enabled if component is enabled)
            fallback_providers = component_config.get("fallback_providers", [])
            for provider in fallback_providers:
                if provider not in enabled_providers:
                    enabled_providers.append(provider)
            
            # Method 4: provider_cascade_order (if specified, these are enabled)
            cascade_order = component_config.get("provider_cascade_order", [])
            for provider in cascade_order:
                if provider not in enabled_providers:
                    enabled_providers.append(provider)
            
            # Add to requirements if we found enabled providers
            if enabled_providers:
                requirements.enabled_providers[family_namespace] = enabled_providers

                # Add provider modules to requirements
                for provider_name in enabled_providers:
                    requirements.python_modules.add(f"{family_namespace}.{provider_name}")

                logger.debug(f"Component-based providers found: {family_namespace} -> {enabled_providers}")
    

    
    def _analyze_workflows(self, config: Dict[str, Any], requirements: BuildRequirements):
        """Analyze enabled workflows from configuration."""
        workflows_config = config.get("workflows", {})
        enabled = workflows_config.get("enabled", [])
        
        if enabled:
            requirements.enabled_providers["locveil_voice.workflows"] = enabled
            for workflow_name in enabled:
                module_path = f"locveil_voice.workflows.{workflow_name}"
                requirements.python_modules.add(module_path)
    
    def _analyze_plugins(self, config: Dict[str, Any], requirements: BuildRequirements):
        """Analyze enabled plugins from configuration."""
        # The legacy locveil_voice.plugins.builtin system was retired in ARCH-13; only
        # plugin-based providers remain analyzable here.
        self._analyze_plugin_providers(config, requirements)
    
    def _analyze_plugin_providers(self, config: Dict[str, Any], requirements: BuildRequirements):
        """
        Analyze plugin-based providers from configuration.
        
        Handles patterns like:
        [plugins.universal_tts.providers.elevenlabs]
        enabled = true
        voice = "Rachel"
        
        [plugins.universal_tts]
        default_provider = "elevenlabs"
        """
        plugins_config = config.get("plugins", {})
        
        for plugin_name, plugin_config in plugins_config.items():
            if not isinstance(plugin_config, dict):
                continue
            
            # Look for universal_* plugins with provider subsections
            if not plugin_name.startswith("universal_"):
                continue
            
            # Extract provider type from plugin name (universal_tts -> tts)
            provider_type = plugin_name.replace("universal_", "")
            
            # Look for plugin.providers.* subsections
            providers_config = plugin_config.get("providers", {})
            if not providers_config:
                continue
            
            # Extract enabled providers from individual provider configurations
            enabled_providers = []
            for provider_name, provider_config in providers_config.items():
                if isinstance(provider_config, dict) and provider_config.get("enabled", False):
                    enabled_providers.append(provider_name)
            
            # Add to requirements if we found enabled providers
            if enabled_providers:
                namespace = f"locveil_voice.providers.{provider_type}"  # e.g., locveil_voice.providers.tts
                
                # Merge with existing providers from the standard providers.* section
                existing_providers = requirements.enabled_providers.get(namespace, [])
                all_providers = list(set(existing_providers + enabled_providers))
                requirements.enabled_providers[namespace] = all_providers
                
                # Add provider modules to requirements
                for provider_name in enabled_providers:
                    module_path = f"locveil_voice.providers.{provider_type}.{provider_name}"
                    requirements.python_modules.add(module_path)
                
                logger.debug(f"Plugin-based providers found: {namespace} -> {enabled_providers}")
    
    def _analyze_intent_handlers(self, config: Dict[str, Any], requirements: BuildRequirements):
        """
        Analyze enabled intent handlers from configuration.

        Handles the real config shape (ARCH-54 — the old code read a phantom [intents]
        section that no TOML ever had, so this analysis NEVER ran):

        [components]
        intent_system = true

        [intent_system.handlers]
        enabled = ["timer", "greetings", "conversation"]
        disabled = []
        """
        # [components] is the enablement authority (ARCH-54)
        if not config.get("components", {}).get("intent_system", False):
            logger.debug("Intent system is disabled, skipping intent handler analysis")
            return

        handlers_config = config.get("intent_system", {}).get("handlers", {})
        enabled_handlers = []
        
        # Method 1: Array-based enabled list (e.g., intents.handlers.enabled = ["timer", "greetings"])
        enabled_list = handlers_config.get("enabled", [])
        if enabled_list and isinstance(enabled_list, list):
            enabled_handlers.extend(enabled_list)
        
        # Method 2: Object-based individual handler configs (e.g., intents.handlers.timer = true)
        for key, value in handlers_config.items():
            if key in ["enabled", "disabled", "asset_validation"]:
                continue  # Skip meta-configuration keys
            
            # Direct boolean configuration (e.g., timer = true)
            if isinstance(value, bool) and value:
                enabled_handlers.append(key)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_enabled = []
        for handler in enabled_handlers:
            if handler not in seen:
                seen.add(handler)
                unique_enabled.append(handler)
        
        # Remove explicitly disabled handlers
        disabled_handlers = handlers_config.get("disabled", [])
        if disabled_handlers:
            unique_enabled = [h for h in unique_enabled if h not in disabled_handlers]
        
        if unique_enabled:
            namespace = "locveil_voice.intents.handlers"
            requirements.enabled_providers[namespace] = unique_enabled
            
            # Add intent handler modules to requirements
            for handler_name in unique_enabled:
                module_path = f"locveil_voice.intents.handlers.{handler_name}"
                requirements.python_modules.add(module_path)
            
            # Add donation contract files to requirements (v1.1 split: a directory per handler with
            # contract.json + per-language phrasing). These must be present and schema-valid.
            for handler_name in unique_enabled:
                asset_dir = handler_name if handler_name.endswith("_handler") else f"{handler_name}_handler"
                requirements.intent_json_files.add(f"assets/donations/{asset_dir}/contract.json")

            logger.debug(f"Intent handlers found: {namespace} -> {unique_enabled}")
            logger.debug(f"Intent donation contracts required: {requirements.intent_json_files}")
    
    def _generate_dependencies_from_metadata(self, requirements: BuildRequirements):
        """
        Generate dependencies using dynamic metadata queries.
        
        Replaces hardcoded PROVIDER_SYSTEM_DEPENDENCIES and PROVIDER_PYTHON_DEPENDENCIES.
        """
        # Initialize platform containers
        platforms = list(SUPPORTED_PLATFORMS)
        for platform in platforms:
            requirements.system_packages[platform] = set()
        
        for namespace, providers in requirements.enabled_providers.items():
            for provider_name in providers:
                provider_class = self._get_provider_metadata(namespace, provider_name)
                if provider_class is None:
                    logger.warning(f"Skipping dependency analysis for {namespace}.{provider_name}")
                    continue
                
                try:
                    # Get Python dependencies from metadata
                    python_deps = provider_class.get_python_dependencies()
                    requirements.python_dependencies.update(python_deps)
                    
                    # Get platform-specific system dependencies
                    platform_deps = provider_class.get_platform_dependencies()
                    for platform, packages in platform_deps.items():
                        if platform in requirements.system_packages:
                            requirements.system_packages[platform].update(packages)
                    
                    logger.debug(f"Loaded dependencies for {namespace}.{provider_name}: "
                               f"python={python_deps}, platforms={list(platform_deps.keys())}")
                               
                except Exception as e:
                    logger.error(f"Failed to query metadata for {namespace}.{provider_name}: {e}")
                    continue
    
    def _validate_critical_providers(self, requirements: BuildRequirements, result: ValidationResult):
        """Validate that critical providers are available."""
        # Check for audio output if TTS is enabled
        tts_providers = requirements.enabled_providers.get("locveil_voice.providers.tts", [])
        audio_providers = requirements.enabled_providers.get("locveil_voice.providers.audio", [])
        
        # BUG-21: TTS needs SOME way out — a local audio provider OR the web API's reply
        # channel (ARCH-22: satellite profiles synthesize and stream to the ESP32; they
        # deliberately have no local audio output). Only TTS with NEITHER path is dead.
        if tts_providers and not audio_providers and not requirements.web_api_enabled:
            result.errors.append(
                "TTS providers enabled but no output path configured "
                "(no audio provider and web_api_enabled is false)")
        
        # Check for ASR if microphone input is expected
        components = requirements.enabled_providers.get("locveil_voice.components", [])
        asr_providers = requirements.enabled_providers.get("locveil_voice.providers.asr", [])
        
        if "asr" in components and not asr_providers:
            result.errors.append("ASR component enabled but no ASR providers configured")
    
    def _validate_dependency_conflicts(self, requirements: BuildRequirements, result: ValidationResult):
        """Check for conflicting provider dependencies."""
        # Example: Check for conflicting audio systems
        audio_providers = requirements.enabled_providers.get("locveil_voice.providers.audio", [])
        
        # ALSA vs PulseAudio conflicts (example)
        has_alsa = any(p in audio_providers for p in ["aplay"])
        has_pulse = any(p in audio_providers for p in ["sounddevice"])
        
        if has_alsa and has_pulse:
            result.warnings.append("Both ALSA and PulseAudio providers enabled - may cause conflicts")
    
    def _validate_entry_points(self, requirements: BuildRequirements, result: ValidationResult):
        """Validate that all enabled providers have corresponding entry-points."""
        catalog = self._get_entry_points_catalog()
        
        for namespace, providers in requirements.enabled_providers.items():
            available_providers = catalog.get(namespace, [])
            for provider_name in providers:
                if provider_name not in available_providers:
                    result.errors.append(f"Provider '{provider_name}' not found in namespace '{namespace}'")
    
    def _validate_provider_metadata(self, requirements: BuildRequirements, result: ValidationResult):
        """Validate provider metadata compatibility and requirements."""
        for namespace, providers in requirements.enabled_providers.items():
            for provider_name in providers:
                provider_class = self._get_provider_metadata(namespace, provider_name)
                if provider_class is None:
                    result.warnings.append(f"Could not load metadata for provider '{provider_name}'")
                    continue
                
                try:
                    # Validate metadata methods exist and work
                    python_deps = provider_class.get_python_dependencies()
                    platform_deps = provider_class.get_platform_dependencies()
                    platform_support = provider_class.get_platform_support()
                    
                    # Validate return types
                    if not isinstance(python_deps, list):
                        result.errors.append(f"Provider '{provider_name}' get_python_dependencies() must return list")
                    if not isinstance(platform_deps, dict):
                        result.errors.append(f"Provider '{provider_name}' get_platform_dependencies() must return dict")
                    if not isinstance(platform_support, list):
                        result.errors.append(f"Provider '{provider_name}' get_platform_support() must return list")
                        
                except Exception as e:
                    result.errors.append(f"Provider '{provider_name}' metadata validation failed: {e}")
    
    def _validate_intent_json_files(self, requirements: BuildRequirements, result: ValidationResult):
        """Validate that each enabled handler's donation files exist and are valid against the v1.1 schemas.

        QUAL-43: the v1.0 monolithic `<handler>.json` + `assets/v1.0.json` validator was retired with the v1.1
        split. Each handler is now a directory (`assets/donations/<handler>/`) holding a `contract.json`
        (validated against `donation_contract_v1.1.json`) plus per-language phrasing files (validated against
        `donation_language_v1.1.json`)."""
        if not requirements.intent_json_files:
            return  # No intent handlers enabled, nothing to validate

        try:
            import jsonschema
        except ImportError:
            result.warnings.append("jsonschema not available - donation schema validation skipped")
            return

        def _load_schema(name: str) -> Optional[dict]:
            path = self.project_root / "assets" / name
            if not path.exists():
                result.warnings.append(f"v1.1 schema not found: assets/{name} - validation skipped")
                return None
            return json.loads(path.read_text(encoding="utf-8"))

        contract_schema = _load_schema("donation_contract_v1.1.json")
        language_schema = _load_schema("donation_language_v1.1.json")

        for contract_rel in requirements.intent_json_files:
            contract_path = self.project_root / contract_rel
            if not contract_path.exists():
                result.errors.append(f"Required donation contract not found: {contract_rel}")
                continue
            try:
                contract = json.loads(contract_path.read_text(encoding="utf-8"))
                if contract_schema is not None:
                    jsonschema.validate(instance=contract, schema=contract_schema)
            except (json.JSONDecodeError, jsonschema.ValidationError) as e:
                msg = getattr(e, "message", str(e))
                result.errors.append(f"Donation contract invalid ({contract_rel}): {msg}")
                continue

            # Validate the sibling per-language phrasing files.
            donation_dir = contract_path.parent
            lang_files = [p for p in donation_dir.glob("*.json") if p.name != "contract.json"]
            if not lang_files:
                result.warnings.append(f"Donation '{donation_dir.name}' has no language phrasing files")
            for lf in lang_files:
                try:
                    phrasing = json.loads(lf.read_text(encoding="utf-8"))
                    if language_schema is not None:
                        jsonschema.validate(instance=phrasing, schema=language_schema)
                except (json.JSONDecodeError, jsonschema.ValidationError) as e:
                    msg = getattr(e, "message", str(e))
                    result.errors.append(f"Donation phrasing invalid ({lf.relative_to(self.project_root)}): {msg}")


def main():
    """Command-line interface for the build analyzer."""
    parser = argparse.ArgumentParser(
        description="Irene Voice Assistant - Runtime Build Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a specific configuration profile
  python -m locveil_voice.tools.build_analyzer --config config/embedded-armv7.toml

  # List all available profiles
  python -m locveil_voice.tools.build_analyzer --list-profiles

  # Validate all profiles
  python -m locveil_voice.tools.build_analyzer --validate-all-profiles

  # Generate Docker commands for specific platform
  python -m locveil_voice.tools.build_analyzer --config embedded-armv7.toml --docker --platform alpine

  # Generate system install commands
  python -m locveil_voice.tools.build_analyzer --config embedded-armv7.toml --system-install --platform ubuntu
        """
    )
    
    parser.add_argument(
        "--config", 
        help="Path to configuration file (relative to config/ or absolute path)"
    )
    parser.add_argument(
        "--list-profiles", 
        action="store_true",
        help="List all available configuration profiles in config/"
    )
    parser.add_argument(
        "--validate-all-profiles", 
        action="store_true",
        help="Validate all configuration profiles"
    )
    parser.add_argument(
        "--docker", 
        action="store_true",
        help="Generate Docker installation commands"
    )
    parser.add_argument(
        "--system-install", 
        action="store_true",
        help="Generate system installation commands"
    )
    parser.add_argument(
        "--python-deps", 
        action="store_true",
        help="Generate Python dependency requirements"
    )
    parser.add_argument(
        "--platform",
        choices=list(SUPPORTED_PLATFORMS),
        default="linux.ubuntu",
        help="Target platform for system dependencies"
    )
    parser.add_argument(
        "--json", 
        action="store_true",
        help="Output results in JSON format"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Analyze but don't generate actual commands"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--arch",
        choices=["x86_64", "aarch64", "armv7l"],
        help="Target CPU architecture (ARCH-24 T3): with --config, FAIL if a profile enables a provider "
             "that does not support this arch (e.g. a torch/onnxruntime provider on armv7l)."
    )

    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(levelname)s: %(message)s'
    )
    
    try:
        analyzer = IreneBuildAnalyzer()
        
        if args.list_profiles:
            profiles = analyzer.list_available_profiles()
            if args.json:
                print(json.dumps(profiles))
            else:
                print("Available configuration profiles:")
                for profile in profiles:
                    print(f"  - {profile}")
            return 0
        
        if args.validate_all_profiles:
            profiles = analyzer.list_available_profiles()
            if not profiles:
                print("No configuration profiles found in config/")
                return 1
            
            results = {}
            for profile in profiles:
                try:
                    # Bare filename: analyze_runtime_requirements resolves it against
                    # configs_dir, so this works regardless of cwd (repo root vs backend/).
                    config_path = f"{profile}.toml"
                    requirements = analyzer.analyze_runtime_requirements(config_path)
                    validation = analyzer.validate_build_profile(requirements)
                    results[profile] = {
                        "valid": validation.is_valid,
                        "errors": validation.errors,
                        "warnings": validation.warnings
                    }
                except Exception as e:
                    results[profile] = {
                        "valid": False,
                        "errors": [str(e)],
                        "warnings": []
                    }
            
            if args.json:
                print(json.dumps(results, indent=2))
            else:
                for profile, result in results.items():
                    status = "✅ VALID" if result["valid"] else "❌ INVALID"
                    print(f"{profile}: {status}")
                    for error in result["errors"]:
                        print(f"  ERROR: {error}")
                    for warning in result["warnings"]:
                        print(f"  WARNING: {warning}")

            # BUG-21: this used to `return 0` unconditionally — the CI gate that runs
            # --validate-all-profiles was decorative. Invalid profiles now fail the run.
            return 0 if all(r["valid"] for r in results.values()) else 1
        
        if not args.config:
            parser.error("--config is required unless using --list-profiles or --validate-all-profiles")

        # ARCH-24 T3 gate: fail the build if a profile enables a provider the target arch can't run.
        if args.arch:
            arch_errors = analyzer.validate_architecture(args.config, args.arch)
            if arch_errors:
                print(f"❌ Architecture gate FAILED for '{args.config}' on {args.arch}:")
                for err in arch_errors:
                    print(f"   - {err}")
                return 1
            print(f"✅ Architecture gate passed: '{args.config}' is {args.arch}-compatible")
            return 0

        # Analyze specific configuration
        requirements = analyzer.analyze_runtime_requirements(args.config)
        validation = analyzer.validate_build_profile(requirements)
        
        if args.json:
            # Convert sets to lists for JSON serialization
            output = {
                "profile": requirements.profile_name,
                "python_modules": sorted(requirements.python_modules),
                "system_packages": {
                    platform: sorted(packages) 
                    for platform, packages in requirements.system_packages.items()
                },
                "python_dependencies": sorted(requirements.python_dependencies),
                "enabled_providers": requirements.enabled_providers,
                "intent_json_files": sorted(requirements.intent_json_files),
                "validation": {
                    "valid": validation.is_valid,
                    "errors": validation.errors,
                    "warnings": validation.warnings
                }
            }
            print(json.dumps(output, indent=2))
            return 0
        
        # Human-readable output
        print(f"🔍 Build Analysis for Profile: {requirements.profile_name}")
        print(f"📦 Python Modules: {len(requirements.python_modules)}")
        for module in sorted(requirements.python_modules):
            print(f"  - {module}")
        
        print(f"🖥️  System Packages ({args.platform}): {len(requirements.system_packages.get(args.platform, set()))}")
        for package in sorted(requirements.system_packages.get(args.platform, set())):
            print(f"  - {package}")
        
        print(f"🐍 Python Dependencies: {len(requirements.python_dependencies)}")
        for dep in sorted(requirements.python_dependencies):
            print(f"  - {dep}")
        
        print(f"📄 Intent JSON Files: {len(requirements.intent_json_files)}")
        for json_file in sorted(requirements.intent_json_files):
            print(f"  - {json_file}")
        
        # Generate commands if requested
        if args.docker:
            print(f"\n🐳 Docker Commands ({args.platform}):")
            commands = analyzer.generate_docker_commands(requirements, args.platform)
            if commands:
                for cmd in commands:
                    print(cmd)
            else:
                print("# No system dependencies required")
        
        if args.system_install:
            print(f"\n💻 System Install Commands ({args.platform}):")
            commands = analyzer.generate_system_install_commands(requirements, args.platform)
            if commands:
                for cmd in commands:
                    print(cmd)
            else:
                print("# No system dependencies required")
        
        if args.python_deps:
            print("\n🐍 Python Dependencies:")
            deps = analyzer.generate_python_requirements(requirements)
            if deps:
                for dep in deps:
                    print(f"  - {dep}")
            else:
                print("# No additional Python dependencies required")
        
        # Show validation results
        print(f"\n✅ Validation: {'PASSED' if validation.is_valid else 'FAILED'}")
        for error in validation.errors:
            print(f"  ❌ ERROR: {error}")
        for warning in validation.warnings:
            print(f"  ⚠️  WARNING: {warning}")
        
        return 0 if validation.is_valid else 1
        
    except Exception as e:
        logger.error(f"Build analysis failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 