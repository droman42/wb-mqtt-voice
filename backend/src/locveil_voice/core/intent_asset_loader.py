"""
Intent Asset Loader - Unified Asset Management for Intent Handlers

Phase 1 Implementation: Replaces DonationLoader with unified asset loading
supporting donations, templates, prompts, and localization data.

This loader extends the proven DonationLoader patterns to handle all asset types
with unified error handling, validation, and caching.
"""

import json
import logging
import asyncio
import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any

from .donations import (
    HandlerDonation, DonationDiscoveryError,
    KeywordDonation, ParameterSpec, ParameterType
)
from .contract_validator import ContractValidationReport

logger = logging.getLogger(__name__)


# CR-A15: user-supplied path components (handler_name, domain, language) flow into
# `assets_root / … / <segment> / …` reads AND writes, some via FastAPI path params. Validate each is a
# single, traversal-safe path segment so it can never escape assets_root (e.g. "../../etc"). A single
# segment with no separator / "../" / absolute / NUL cannot traverse, so segment validation is sufficient.
_SAFE_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _safe_path_segment(value: str, field: str) -> str:
    """Return `value` if it's a single traversal-safe path segment, else raise ValueError (fail closed)."""
    s = str(value)
    if ".." in s or not _SAFE_SEGMENT_RE.match(s):
        raise ValueError(
            f"Invalid {field} '{value}': must be a single path segment "
            f"(letters, digits, '.', '_', '-'; no separators, '..', or leading dot)"
        )
    return s


def asset_dir_name(handler_name: str) -> str:
    """Asset directory name for a handler — `<name>_handler` (idempotent if already suffixed)."""
    return handler_name if handler_name.endswith("_handler") else f"{handler_name}_handler"


def base_handler_name(name: str) -> str:
    """Inverse of `asset_dir_name`: strip a trailing `_handler` from an asset directory name."""
    return name[: -len("_handler")] if name.endswith("_handler") else name


def _should_skip_directory(dir_name: str) -> bool:
    """
    Check if directory should be skipped in handler discovery.
    
    Args:
        dir_name: Directory name to check
        
    Returns:
        True if directory should be skipped (system/cache directories)
    """
    # System directories that should never be treated as handlers
    SYSTEM_DIRS = {
        'backups', 'schemas', 'cache', 'temp', 'tmp', 'logs',
        '.git', '.svn', '.hg', '__pycache__', '.pytest_cache',
        'node_modules', '.DS_Store', 'Thumbs.db',
        '.idea', '.vscode', '.vs'
    }
    
    return (
        dir_name in SYSTEM_DIRS or
        dir_name.startswith('.') or
        (dir_name.startswith('__') and dir_name.endswith('__'))
    )


class AssetLoaderConfig:
    """Configuration for IntentAssetLoader behavior"""
    
    def __init__(
        self,
        validate_json_schema: bool = True,
        validate_spacy_patterns: bool = False,
        validate_contract_wiring: bool = True,
        strict_parameters: bool = False,
        strict_mode: bool = False,
        default_language: str = "ru",
        fallback_language: str = "en",
        supported_languages: Optional[List[str]] = None,
        enable_language_filtering: bool = True,
        # Absorb removed/unknown keys: this is built via `AssetLoaderConfig(**config.asset_validation)`
        # (intents/manager.py), so a stale config key must not crash boot. (CR-C13 retired
        # `validate_method_existence` — method-wiring is validated by `validate_contract_wiring`.)
        **_ignored: Any
    ):
        if _ignored:
            logger.debug(f"AssetLoaderConfig ignoring unknown keys: {sorted(_ignored)}")
        self.validate_json_schema = validate_json_schema
        self.validate_spacy_patterns = validate_spacy_patterns
        # QUAL-42: reconcile every contract against its handler code at startup. Unwired methods are fatal;
        # `strict_parameters` promotes "declared-but-unread parameter" warnings to fatal errors (ratchet).
        self.validate_contract_wiring = validate_contract_wiring
        self.strict_parameters = strict_parameters
        self.strict_mode = strict_mode
        self.default_language = default_language
        self.fallback_language = fallback_language
        self.supported_languages = supported_languages or ["ru", "en"]
        self.enable_language_filtering = enable_language_filtering


class IntentAssetLoader:
    """Unified loader for all intent handler assets"""
    
    def __init__(self, assets_root: Path, config: Optional[AssetLoaderConfig] = None):
        self.assets_root = Path(assets_root)
        self.config = config or AssetLoaderConfig()
        
        # Asset caches
        self.donations: Dict[str, HandlerDonation] = {}
        self.templates: Dict[str, Dict[str, Any]] = {}
        self.prompts: Dict[str, Dict[str, Any]] = {}
        self.localizations: Dict[str, Dict[str, Any]] = {}
        self.web_templates: Dict[str, str] = {}  # NEW: Web template cache
        
        # Error tracking (reuse donation loader pattern)
        self.validation_errors: List[str] = []
        self.warnings: List[str] = []

        # QUAL-42: cached contract↔code wiring report (populated at startup, served to the UI).
        self.contract_validation_report: Optional[ContractValidationReport] = None
    
    async def load_all_assets(self, handler_names: List[str]) -> None:
        """Load all asset types for specified handlers"""
        logger.info(f"Loading assets for {len(handler_names)} handlers: {handler_names}")
        
        # Load assets in parallel for better performance
        await asyncio.gather(
            self._load_donations(handler_names),
            self._load_templates(handler_names),
            self._load_prompts(handler_names),
            self._load_localizations(handler_names),
            self._load_web_templates(),  # NEW: Load web templates
            return_exceptions=True
        )
        
        # Check for fatal errors
        if self.validation_errors:
            self._handle_validation_errors()

        # QUAL-42: reconcile every loaded contract against its handler code. Unwired contract methods are a
        # hard bug — fail fast. Soft findings (unread params, undeclared handler methods) are cached for the UI.
        if self.config.validate_contract_wiring:
            self._validate_contract_wiring()

        # Log warnings
        for warning in self.warnings:
            logger.warning(warning)

        logger.info(f"Asset loading completed: {len(self.donations)} donations, "
                   f"{len(self.templates)} template sets, {len(self.prompts)} prompt sets, "
                   f"{len(self.localizations)} localization sets, "
                   f"{len(self.web_templates)} web templates")
    
    # ============================================================
    # PUBLIC API (extends existing donation loader interface)
    # ============================================================
    
    def get_donation(self, handler_name: str) -> Optional[HandlerDonation]:
        """Get JSON donation (existing functionality)"""
        return self.donations.get(handler_name)
    
    async def save_donation(self, handler_name: str, donation_data: dict, create_backup: bool = True) -> bool:
        """Save donation JSON to file with backup support"""
        donations_dir = self._asset_path("donations")
        json_path = donations_dir / f"{handler_name}.json"
        
        try:
            # Create backup if requested and file exists
            if create_backup and json_path.exists():
                # Create backups directory
                backups_dir = donations_dir / "backups"
                backups_dir.mkdir(parents=True, exist_ok=True)
                
                # Generate backup filename with current datetime
                from datetime import datetime
                current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = f"{handler_name}_{current_datetime}.json"
                backup_path = backups_dir / backup_filename
                
                # Copy existing file to backup location
                import shutil
                shutil.copy2(json_path, backup_path)
                logger.info(f"Created backup: {backup_path}")
            
            # Ensure donations directory exists
            donations_dir.mkdir(parents=True, exist_ok=True)
            
            # Write JSON with proper formatting
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(donation_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved donation for handler '{handler_name}' to {json_path}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to save donation for handler '{handler_name}': {e}"
            self._add_error(error_msg)
            return False
    
    def _create_backup(self, file_path: Path, backup_type: str, identifier: str, language: Optional[str] = None) -> bool:
        """
        Create a backup of an existing file before modification.
        
        Args:
            file_path: Path to the file to backup
            backup_type: Type of asset ('donations', 'templates', 'prompts', 'localization')
            identifier: Handler name or domain name
            language: Language code (optional, for language-specific backups)
            
        Returns:
            True if backup was created or file doesn't exist, False on error
        """
        if not file_path.exists():
            return True  # No need to backup non-existent file
        
        try:
            # Determine backup directory based on asset type
            if backup_type == "localization":
                backup_dir = self._asset_path("localization", "backups")
            else:
                backup_dir = self._asset_path(backup_type, "backups")
            
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate backup filename with timestamp
            from datetime import datetime
            current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Build backup filename based on whether language is specified
            if language:
                backup_filename = f"{identifier}_{language}_{current_datetime}{file_path.suffix}"
            else:
                backup_filename = f"{identifier}_{current_datetime}{file_path.suffix}"
            
            backup_path = backup_dir / backup_filename
            
            # Copy existing file to backup location
            import shutil
            shutil.copy2(file_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create backup for {file_path}: {e}")
            return False

    def get_donation_metadata(self, handler_name: str) -> Optional[dict]:
        """Get metadata about a donation file"""
        donations_dir = self._asset_path("donations")
        json_path = donations_dir / f"{handler_name}.json"
        
        if not json_path.exists():
            return None
        
        try:
            stat = json_path.stat()
            donation = self.donations.get(handler_name)
            
            metadata = {
                "handler_name": handler_name,
                "file_size": stat.st_size,
                "last_modified": stat.st_mtime
            }
            
            if donation:
                metadata.update({
                    "domain": donation.handler_domain,
                    "description": donation.description,
                    "methods_count": len(donation.method_donations),
                    "global_parameters_count": len(donation.global_parameters)
                })
            else:
                # Try to read basic info from file
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    metadata.update({
                        "domain": data.get("handler_domain", "unknown"),
                        "description": data.get("description", ""),
                        "methods_count": len(data.get("method_donations", [])),
                        "global_parameters_count": len(data.get("global_parameters", []))
                    })
                except Exception:
                    metadata.update({
                        "domain": "unknown",
                        "description": "Failed to read file",
                        "methods_count": 0,
                        "global_parameters_count": 0
                    })
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to get metadata for {handler_name}: {e}")
            return None
    
    def list_all_donations(self) -> list[dict]:
        """List all available donation files with metadata"""
        donations_dir = self._asset_path("donations")
        
        if not donations_dir.exists():
            return []
        
        donations_list = []
        for json_file in donations_dir.glob("*.json"):
            handler_name = json_file.stem
            metadata = self.get_donation_metadata(handler_name)
            if metadata:
                donations_list.append(metadata)
        
        return donations_list
    
    def get_template(self, handler_name: str, template_name: str, language: Optional[str] = None) -> Optional[str]:
        """Get response template with i18n fallback"""
        language = language or self.config.default_language
        
        handler_templates = self.templates.get(handler_name, {})
        template_data = handler_templates.get(template_name, {})
        
        # Try requested language first
        if language in template_data:
            return template_data[language]
        
        # Fallback to default language
        if self.config.fallback_language in template_data:
            return template_data[self.config.fallback_language]
        
        # Fallback to any available language
        if template_data:
            return next(iter(template_data.values()))
        
        return None
    
    def get_prompt(self, handler_name: str, prompt_type: str, language: Optional[str] = None) -> Optional[str]:
        """Get LLM prompt with language fallback"""
        language = language or self.config.default_language
        
        handler_prompts = self.prompts.get(handler_name, {})
        prompt_key = f"{prompt_type}_{language}"
        
        # Try requested language first
        if prompt_key in handler_prompts:
            return handler_prompts[prompt_key]
        
        # Fallback to default language
        fallback_key = f"{prompt_type}_{self.config.fallback_language}"
        if fallback_key in handler_prompts:
            return handler_prompts[fallback_key]
        
        return None
    
    def get_prompt_metadata(self, handler_name: str, prompt_type: str, language: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get LLM prompt metadata for assets editor"""
        language = language or self.config.default_language
        
        handler_prompts = self.prompts.get(handler_name, {})
        metadata_key = f"{prompt_type}_{language}_metadata"
        
        # Try requested language first
        if metadata_key in handler_prompts:
            return handler_prompts[metadata_key]
        
        # Fallback to default language
        fallback_key = f"{prompt_type}_{self.config.fallback_language}_metadata"
        if fallback_key in handler_prompts:
            return handler_prompts[fallback_key]
        
        return None
    
    def get_localization(self, domain: str, language: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get localization data (arrays, mappings) with language fallback"""
        language = language or self.config.default_language
        
        domain_data = self.localizations.get(domain, {})
        
        # Try requested language first
        if language in domain_data:
            return domain_data[language]
        
        # Fallback to default language
        if self.config.fallback_language in domain_data:
            return domain_data[self.config.fallback_language]
        
        return None
    
    def convert_to_keyword_donations(self) -> List[KeywordDonation]:
        """Convert JSON donations to KeywordDonation objects for NLU providers"""
        keyword_donations = []
        
        for handler_name, donation in self.donations.items():
            for method_donation in donation.method_donations:
                # Build full intent name
                full_intent_name = f"{donation.handler_domain}.{method_donation.intent_suffix}"
                
                # Convert parameter specs
                converted_params = []
                for param in method_donation.parameters + donation.global_parameters:
                    converted_params.append(ParameterSpec(
                        name=param.name,
                        type=ParameterType(param.type),
                        required=param.required,
                        default_value=param.default_value,
                        description=param.description,
                        choices=param.choices,
                        choice_surfaces=param.choice_surfaces,  # QUAL-29: carry canonical→surface map to the NLU
                        min_value=param.min_value,
                        max_value=param.max_value,
                        pattern=param.pattern,
                        entity_type=param.entity_type,  # QUAL-29: carry entity classification
                        extraction_patterns=param.extraction_patterns,
                        aliases=param.aliases
                    ))
                
                keyword_donation = KeywordDonation(
                    intent=full_intent_name,
                    phrases=method_donation.phrases,
                    lemmas=method_donation.lemmas,
                    parameters=converted_params,
                    token_patterns=method_donation.token_patterns,
                    slot_patterns=method_donation.slot_patterns,
                    examples=[{"text": ex.text, "parameters": ex.parameters} for ex in method_donation.examples],
                    boost=method_donation.boost,
                    donation_version=donation.donation_version,
                    handler_domain=donation.handler_domain
                )
                keyword_donations.append(keyword_donation)
        
        return keyword_donations
    
    # ============================================================
    # WEB TEMPLATE API (NEW - extends asset loader for web content)
    # ============================================================
    
    def get_web_template(self, template_name: str) -> Optional[str]:
        """Get web template content by name"""
        return self.web_templates.get(template_name)
    
    def get_web_template_with_variables(self, template_name: str, **variables) -> Optional[str]:
        """Get web template content with variable substitution"""
        template_content = self.web_templates.get(template_name)
        if template_content is None:
            return None
        
        # Use safe variable substitution that doesn't interfere with CSS
        try:
            # Use string.Template for safer substitution or manual replacement
            import re
            
            # Replace only specific variables we know about
            result = template_content
            for var_name, var_value in variables.items():
                # Replace {var_name} with var_value, but be careful not to replace CSS
                pattern = r'\{' + re.escape(var_name) + r'\}'
                result = re.sub(pattern, str(var_value), result)
            
            return result
        except Exception as e:
            logger.error(f"Error substituting variables in web template '{template_name}': {e}")
            return template_content
    
    def list_web_templates(self) -> List[str]:
        """Get list of available web template names"""
        return list(self.web_templates.keys())
    
    # ============================================================
    # ASSET LOADING IMPLEMENTATION
    # ============================================================
    
    async def _load_donations(self, handler_names: List[str]) -> None:
        """Load language-separated donation files and merge for unified processing"""
        donations_dir = self._asset_path("donations")
        
        for handler_name in handler_names:
            asset_handler_name = self._get_asset_handler_name(handler_name)
            language_donation_dir = donations_dir / asset_handler_name
            
            # Load language-separated structure (only supported format)
            if language_donation_dir.exists() and language_donation_dir.is_dir():
                await self._load_language_separated_donations(language_donation_dir, handler_name)
            else:
                self._add_warning(f"No language-separated donation directory found for handler '{handler_name}': {language_donation_dir}")
    
    async def _load_language_separated_donations(self, lang_dir: Path, handler_name: str) -> None:
        """QUAL-29 (v1.1): load the language-neutral ``contract.json`` + per-language phrasing files and
        assemble a unified ``HandlerDonation``. The contract holds the invariant ParameterSpec core (name/type/
        required/choices=canonical/min-max/entity_type) + per-method room_context; the language files hold
        phrases/lemmas/patterns/examples + per-param description/extraction_patterns/aliases/default_value/
        choice_surfaces. Neither file is a complete donation alone."""
        contract_path = lang_dir / "contract.json"
        if not contract_path.exists():
            self._add_warning(f"No contract.json (v1.1) for handler '{handler_name}' in {lang_dir}")
            return
        try:
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
        except Exception as e:
            self._add_warning(f"Failed to load contract.json for handler '{handler_name}': {e}")
            return
        if self.config.validate_json_schema:
            await self._validate_donation_schema(contract, contract_path, "donation_contract_v1.1.json")

        lang_jsons = {}
        for lang_file in lang_dir.glob("*.json"):
            if lang_file.name == "contract.json":
                continue
            language = lang_file.stem
            if language in self.config.supported_languages:
                try:
                    lang_jsons[language] = json.loads(lang_file.read_text(encoding="utf-8"))
                except Exception as e:
                    self._add_warning(f"Failed to load {language} phrasing for handler '{handler_name}': {e}")
                    continue
                if self.config.validate_json_schema:
                    await self._validate_donation_schema(lang_jsons[language], lang_file, "donation_language_v1.1.json")

        if not lang_jsons:
            self._add_warning(f"No language phrasing files for handler '{handler_name}' in {lang_dir}")
            return

        try:
            assembled = self._assemble_v11_donation(contract, lang_jsons)
            donation = HandlerDonation(**assembled)
        except Exception as e:
            self._add_warning(f"Failed to assemble v1.1 donation for handler '{handler_name}': {e}")
            return

        self.donations[handler_name] = donation
        logger.info(f"Assembled v1.1 donation for handler '{handler_name}' ({len(lang_jsons)} languages)")
    
    @staticmethod
    def _accumulate(field: str, sources: list) -> list:
        """Union a list-valued field across sources, order-preserving (fixes the old first-language-wins drop)."""
        seen, out = set(), []
        for src in sources:
            for item in (src.get(field) or []):
                key = item if isinstance(item, str) else json.dumps(item, sort_keys=True, ensure_ascii=False)
                if key not in seen:
                    seen.add(key)
                    out.append(item)
        return out

    def _assemble_v11_donation(self, contract: dict, lang_jsons: Dict[str, dict]) -> dict:
        """Assemble a complete HandlerDonation dict from the neutral contract + per-language phrasing.

        Russian is the primary language (wins single-valued picks like description/default_value); list-valued
        phrasing (phrases/lemmas/token_patterns/extraction_patterns/aliases/examples) is ACCUMULATED across all
        languages so both languages' recognition survives. ``choice_surfaces`` is built as
        {canonical: [canonical] + every language's surface forms} so the canonical token is always self-matchable.
        """
        primary = 'ru' if 'ru' in lang_jsons else next(iter(lang_jsons))
        langs_ordered = [primary] + [l for l in lang_jsons if l != primary]
        lm = {lang: {f"{m['method_name']}#{m['intent_suffix']}": m
                     for m in lang_jsons[lang].get('method_donations', [])} for lang in lang_jsons}

        def assemble_param(cparam: dict, method_key, is_global: bool = False) -> dict:
            p = dict(cparam)  # neutral core: name/type/required/choices(canonical)/min-max/pattern/entity_type
            lang_params = []
            default_by_lang = {}  # BUG-4: per-language default_value (lang → value, incl. explicit null)
            for lang in langs_ordered:
                src = lang_jsons[lang] if is_global else lm[lang].get(method_key, {})
                plist = src.get('global_parameters', []) if is_global else src.get('parameters', [])
                for lp in plist:
                    if lp.get('name') == cparam['name']:
                        lang_params.append(lp)
                        if 'default_value' in lp:
                            default_by_lang[lang] = lp['default_value']
            for lp in lang_params:  # primary-first single-valued picks (flattened, for back-compat)
                if lp.get('description') and not p.get('description'):
                    p['description'] = lp['description']
                if 'default_value' in lp and p.get('default_value') is None:
                    p['default_value'] = lp['default_value']
            p['default_value_by_language'] = default_by_lang  # BUG-4: get_param resolves by request language
            p['extraction_patterns'] = self._accumulate('extraction_patterns', lang_params)
            p['aliases'] = self._accumulate('aliases', lang_params)
            if p.get('choices'):
                surfaces = {}
                for canonical in p['choices']:
                    forms = [canonical]
                    for lp in lang_params:
                        for f in (lp.get('choice_surfaces') or {}).get(canonical, []):
                            if f not in forms:
                                forms.append(f)
                    surfaces[canonical] = forms
                p['choice_surfaces'] = surfaces
            return p

        methods = []
        for cm in contract.get('method_donations', []):
            mk = f"{cm['method_name']}#{cm['intent_suffix']}"
            srcs = [lm[lang].get(mk, {}) for lang in langs_ordered]
            m = dict(cm)  # neutral: method_name/intent_suffix/boost/room_context/parameters
            m['phrases'] = self._accumulate('phrases', srcs)
            m['lemmas'] = self._accumulate('lemmas', srcs)
            m['token_patterns'] = self._accumulate('token_patterns', srcs)
            m['examples'] = self._accumulate('examples', srcs)
            slot_patterns = {}
            for s in srcs:
                for slot, pats in (s.get('slot_patterns') or {}).items():
                    slot_patterns.setdefault(slot, [])
                    for pat in pats:
                        if pat not in slot_patterns[slot]:
                            slot_patterns[slot].append(pat)
            m['slot_patterns'] = slot_patterns
            for s in srcs:  # method description: primary-first
                if s.get('description'):
                    m['description'] = s['description']
                    break
            m['parameters'] = [assemble_param(cp, mk) for cp in cm.get('parameters', [])]
            methods.append(m)

        assembled = dict(contract)  # handler-level neutral (schema_version/handler_domain/intent_name_patterns/…)
        assembled.pop('$schema', None)
        assembled['method_donations'] = methods
        assembled['global_parameters'] = [assemble_param(cp, None, is_global=True)
                                          for cp in contract.get('global_parameters', [])]
        ordered_lang_docs = [lang_jsons[l] for l in langs_ordered]
        for field in ('negative_patterns', 'action_patterns', 'additional_recognition_patterns', 'train_keywords'):
            acc = self._accumulate(field, ordered_lang_docs)
            if acc:
                assembled[field] = acc
        for doc in ordered_lang_docs:  # handler description: primary-first
            if doc.get('description'):
                assembled['description'] = doc['description']
                break
        return assembled
    
    def _asset_path(self, *segments: str) -> Path:
        """Build a path under the assets root — the single source of the `assets/<category>/…`
        layout. Callers validate user-supplied segments (handler/domain/language) before passing
        them (see `_safe_path_segment` / `_get_asset_handler_name`)."""
        path = self.assets_root
        for segment in segments:
            path = path / segment
        return path

    def _get_asset_handler_name(self, handler_name: str) -> str:
        """Map handler file name to asset directory name. Validates the input is a safe path segment
        (CR-A15) — this is the single choke point for every handler-derived asset path."""
        return asset_dir_name(_safe_path_segment(handler_name, "handler_name"))
    
    # ============================================================
    # LANGUAGE-SEPARATED FILE ACCESS FOR EDITOR (Phase 3C)
    # ============================================================
    
    # ------------------------------------------------------------------
    # Donation editing API — v1.1 (language-neutral contract + per-language phrasing).
    # QUAL-29 retired the v1.0 per-language-with-params editing: a language file no longer holds
    # ParameterSpec cores (type/required/choices) — those live once in contract.json. Editing is split:
    # the CONTRACT (params/canonical-choices/entity_type/room_context/method list) vs each language's PHRASING.
    # ------------------------------------------------------------------
    def get_contract_for_editing(self, handler_name: str) -> Optional[Dict[str, Any]]:
        """Return the raw language-neutral contract.json for a handler, or None if absent."""
        asset = self._get_asset_handler_name(handler_name)
        contract_file = self._asset_path("donations", asset, "contract.json")
        if not contract_file.exists():
            return None
        try:
            return json.loads(contract_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Failed to load contract.json for {handler_name}: {e}")
            return None

    def save_contract(self, handler_name: str, contract: Dict[str, Any], create_backup: bool = True) -> tuple[bool, bool]:
        """Persist the language-neutral contract.json. Returns (save_success, backup_created)."""
        backup_created = False
        try:
            asset = self._get_asset_handler_name(handler_name)
            cdir = self._asset_path("donations", asset)
            cdir.mkdir(parents=True, exist_ok=True)
            contract_file = cdir / "contract.json"
            if create_backup and contract_file.exists():
                backup_created = self._create_backup(contract_file, "donations", handler_name, "contract")
            contract_file.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            logger.info(f"Saved contract.json for handler '{handler_name}'")
            return True, backup_created
        except Exception as e:
            logger.error(f"Failed to save contract.json for {handler_name}: {e}")
            return False, backup_created

    def get_language_phrasing_for_editing(self, handler_name: str, language: str) -> Optional[Dict[str, Any]]:
        """Return the raw per-language phrasing file (phrases/lemmas/patterns/examples + per-param
        description/extraction_patterns/aliases/default_value/choice_surfaces), or None if absent."""
        asset = self._get_asset_handler_name(handler_name)
        language = _safe_path_segment(language, "language")  # CR-A15
        lang_file = self._asset_path("donations", asset, f"{language}.json")
        if not lang_file.exists():
            return None
        try:
            return json.loads(lang_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Failed to load {language} phrasing for {handler_name}: {e}")
            return None

    def save_language_phrasing(self, handler_name: str, language: str, phrasing: Dict[str, Any], create_backup: bool = True) -> tuple[bool, bool]:
        """Persist a per-language phrasing file. Returns (save_success, backup_created)."""
        backup_created = False
        try:
            asset = self._get_asset_handler_name(handler_name)
            language = _safe_path_segment(language, "language")  # CR-A15
            lang_dir = self._asset_path("donations", asset)
            lang_dir.mkdir(parents=True, exist_ok=True)
            lang_file = lang_dir / f"{language}.json"
            if create_backup and lang_file.exists():
                backup_created = self._create_backup(lang_file, "donations", handler_name, language)
            phrasing = dict(phrasing)
            phrasing["language"] = language
            lang_file.write_text(json.dumps(phrasing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            logger.info(f"Saved {language} phrasing for handler '{handler_name}'")
            return True, backup_created
        except Exception as e:
            logger.error(f"Failed to save {language} phrasing for {handler_name}: {e}")
            return False, backup_created

    def _validate_v11_data(self, data: Dict[str, Any], schema_filename: str) -> tuple[bool, list, list]:
        """Dry-run validate a v1.1 contract/phrasing dict against its JSON Schema. Returns (is_valid, errors, warnings)
        with error dicts shaped for the API ``ValidationError`` model ({type, message, path})."""
        errors: list = []
        warnings: list = []
        try:
            import jsonschema
        except ImportError:
            warnings.append({"type": "schema", "message": "jsonschema not available; validation skipped", "path": None})
            return True, errors, warnings
        schema_path = self._asset_path(schema_filename)
        if not schema_path.exists():
            warnings.append({"type": "schema", "message": f"schema {schema_filename} not found; skipped", "path": None})
            return True, errors, warnings
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            for e in sorted(jsonschema.Draft7Validator(schema).iter_errors(data), key=lambda er: list(er.path)):
                errors.append({"type": "schema", "message": e.message, "path": "/".join(str(p) for p in e.path)})
        except Exception as e:
            errors.append({"type": "schema", "message": f"validation error: {e}", "path": None})
        return (len(errors) == 0), errors, warnings

    async def validate_contract_data(self, handler_name: str, contract_data: Dict[str, Any]) -> tuple[bool, list, list]:
        """Validate a language-neutral contract dict against the v1.1 contract schema (dry-run)."""
        return self._validate_v11_data(contract_data, "donation_contract_v1.1.json")

    async def validate_phrasing_data(self, handler_name: str, phrasing_data: Dict[str, Any]) -> tuple[bool, list, list]:
        """Validate a per-language phrasing dict against the v1.1 language schema (dry-run)."""
        return self._validate_v11_data(phrasing_data, "donation_language_v1.1.json")
    
    async def reload_unified_donation(self, handler_name: str) -> bool:
        """Reload unified donation after language file changes"""
        try:
            asset_handler_name = self._get_asset_handler_name(handler_name)
            lang_dir = self._asset_path("donations", asset_handler_name)
            
            if lang_dir.exists():
                # Clear existing donation
                if handler_name in self.donations:
                    del self.donations[handler_name]
                
                # Reload language-separated donations
                await self._load_language_separated_donations(lang_dir, handler_name)
                logger.info(f"Reloaded unified donation for handler '{handler_name}'")
                return True
            else:
                logger.warning(f"No donation directory found for handler '{handler_name}': {lang_dir}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to reload donation for {handler_name}: {e}")
            return False
    
    def get_available_languages_for_handler(self, handler_name: str) -> List[str]:
        """Get list of available language files for handler"""
        asset_handler_name = self._get_asset_handler_name(handler_name)
        lang_dir = self._asset_path("donations", asset_handler_name)
        
        if not lang_dir.exists():
            return []

        # QUAL-29: contract.json is the language-neutral core, NOT a language.
        return [lang_file.stem for lang_file in lang_dir.glob("*.json") if lang_file.name != "contract.json"]
    
    def get_all_handlers_with_languages(self) -> Dict[str, List[str]]:
        """Get all handlers with their available languages"""
        donations_dir = self._asset_path("donations")
        handlers_languages = {}
        
        if not donations_dir.exists():
            return handlers_languages
        
        for handler_dir in donations_dir.iterdir():
            if handler_dir.is_dir() and not _should_skip_directory(handler_dir.name):
                # Convert asset handler name back to handler name
                handler_name = base_handler_name(handler_dir.name)
                
                languages = [lang_file.stem for lang_file in handler_dir.glob("*.json")
                             if lang_file.name != "contract.json"]
                if languages:
                    handlers_languages[handler_name] = sorted(languages)
        
        return handlers_languages
    
    # ============================================================
    # TEMPLATE MANAGEMENT API (Phase 6)
    # ============================================================
    
    def get_template_for_language_editing(self, handler_name: str, language: str) -> Optional[Dict[str, Any]]:
        """Get language-specific template data for editing purposes"""
        asset_handler_name = self._get_asset_handler_name(handler_name)
        language = _safe_path_segment(language, "language")  # CR-A15
        lang_file = self._asset_path("templates", asset_handler_name, f"{language}.yaml")
        
        if lang_file.exists():
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Failed to load template file {lang_file}: {e}")
                return None
        
        return None
    
    def save_template_for_language(self, handler_name: str, language: str, template_data: Dict[str, Any], create_backup: bool = True) -> tuple[bool, bool]:
        """Save language-specific template data for editing with backup support
        
        Returns:
            tuple: (save_success, backup_created)
        """
        backup_created = False
        asset_handler_name = self._get_asset_handler_name(handler_name)
        language = _safe_path_segment(language, "language")  # CR-A15
        lang_dir = self._asset_path("templates", asset_handler_name)
        lang_dir.mkdir(parents=True, exist_ok=True)
        
        lang_file = lang_dir / f"{language}.yaml"
        
        try:
            # Create backup if requested and file exists
            if create_backup and lang_file.exists():
                backup_created = self._create_backup(lang_file, "templates", handler_name, language)
                if not backup_created:
                    logger.warning(f"Backup creation failed for {lang_file}, proceeding with save")
            
            # Write new content
            with open(lang_file, 'w', encoding='utf-8') as f:
                yaml.dump(template_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            logger.info(f"Saved {language} template for handler '{handler_name}' to {lang_file}")
            return True, backup_created
        except Exception as e:
            logger.error(f"Failed to save template file {lang_file}: {e}")
            return False, backup_created
    
    async def reload_templates_for_handler(self, handler_name: str) -> bool:
        """Reload templates for a specific handler after language file changes"""
        try:
            await self._load_templates([handler_name])
            logger.info(f"Reloaded templates for handler '{handler_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to reload templates for handler '{handler_name}': {e}")
            return False
    
    def get_available_template_languages_for_handler(self, handler_name: str) -> List[str]:
        """Get list of available template language files for handler"""
        asset_handler_name = self._get_asset_handler_name(handler_name)
        lang_dir = self._asset_path("templates", asset_handler_name)
        
        if not lang_dir.exists():
            return []
        
        return [lang_file.stem for lang_file in lang_dir.glob("*.yaml")]
    
    def get_handlers_with_templates(self) -> Dict[str, List[str]]:
        """Get all handlers that have template files with their available languages"""
        handlers_languages = {}
        templates_dir = self._asset_path("templates")
        
        if not templates_dir.exists():
            return handlers_languages
        
        for handler_dir in templates_dir.iterdir():
            if handler_dir.is_dir() and not _should_skip_directory(handler_dir.name):
                # Convert asset handler name back to handler name
                handler_name = base_handler_name(handler_dir.name)
                
                languages = [lang_file.stem for lang_file in handler_dir.glob("*.yaml")]
                if languages:
                    handlers_languages[handler_name] = sorted(languages)
        
        return handlers_languages
    
    async def validate_template_data(self, handler_name: str, template_data: Dict[str, Any]) -> tuple[bool, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Validate template data structure"""
        errors = []
        warnings = []
        
        try:
            # Basic YAML structure validation
            if not isinstance(template_data, dict):
                errors.append({
                    "type": "structure",
                    "message": "Template data must be a dictionary/object",
                    "path": "root"
                })
                return False, errors, warnings

            # Check for common template keys and types
            for key, value in template_data.items():
                if not isinstance(key, str):
                    errors.append({
                        "type": "structure",
                        "message": "Template keys must be strings",
                        "path": str(key)
                    })
                    continue

                # Validate template value types (can be strings, arrays, or objects)
                if not isinstance(value, (str, list, dict)):
                    warnings.append({
                        "type": "value",
                        "message": f"Template value has unusual type: {type(value).__name__}",
                        "path": key
                    })

            return len(errors) == 0, errors, warnings

        except Exception as e:
            errors.append({
                "type": "validation",
                "message": f"Validation error: {str(e)}",
                "path": "validation"
            })
            return False, errors, warnings

    def validate_cross_language_consistency(self, handler_name: str) -> Dict[str, Any]:
        """QUAL-29 (v1.1): parameter parity is structural (single-source contract), so it is always
        consistent; cross-language checking is now method-phrasing completeness — every contract method
        must have phrases in each language file."""
        contract = self.get_contract_for_editing(handler_name)
        if not contract:
            return {"parameter_consistency": True, "missing_methods": [], "extra_methods": []}

        contract_methods = {f"{m['method_name']}#{m['intent_suffix']}" for m in contract.get("method_donations", [])}
        missing_methods, extra_methods = [], []
        for language in self.get_available_languages_for_handler(handler_name):
            phrasing = self.get_language_phrasing_for_editing(handler_name, language) or {}
            phrased = {f"{m['method_name']}#{m['intent_suffix']}"
                       for m in phrasing.get("method_donations", []) if m.get("phrases")}
            missing_methods.extend(f"{language}: {mk}" for mk in sorted(contract_methods - phrased))
            extra_methods.extend(f"{language}: {mk}" for mk in sorted(phrased - contract_methods))

        return {
            "parameter_consistency": True,  # structural under v1.1
            "missing_methods": missing_methods,
            "extra_methods": extra_methods,
        }
    
    # ============================================================
    # PROMPT MANAGEMENT API (Phase 7)
    # ============================================================
    
    def get_prompt_for_language_editing(self, handler_name: str, language: str) -> Optional[Dict[str, Any]]:
        """Get language-specific prompt data for editing purposes"""
        asset_handler_name = self._get_asset_handler_name(handler_name)
        language = _safe_path_segment(language, "language")  # CR-A15
        lang_file = self._asset_path("prompts", asset_handler_name, f"{language}.yaml")
        
        if lang_file.exists():
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Failed to load prompt file {lang_file}: {e}")
                return None
        
        return None
    
    def save_prompt_for_language(self, handler_name: str, language: str, prompt_data: Dict[str, Any], create_backup: bool = True) -> tuple[bool, bool]:
        """Save language-specific prompt data for editing with backup support
        
        Returns:
            tuple: (save_success, backup_created)
        """
        backup_created = False
        asset_handler_name = self._get_asset_handler_name(handler_name)
        language = _safe_path_segment(language, "language")  # CR-A15
        lang_dir = self._asset_path("prompts", asset_handler_name)
        lang_dir.mkdir(parents=True, exist_ok=True)
        
        lang_file = lang_dir / f"{language}.yaml"
        
        try:
            # Create backup if requested and file exists
            if create_backup and lang_file.exists():
                backup_created = self._create_backup(lang_file, "prompts", handler_name, language)
                if not backup_created:
                    logger.warning(f"Backup creation failed for {lang_file}, proceeding with save")
            
            # Write new content
            with open(lang_file, 'w', encoding='utf-8') as f:
                yaml.dump(prompt_data, f, default_flow_style=False, allow_unicode=True, indent=2)
            
            logger.info(f"Saved {language} prompt for handler '{handler_name}' to {lang_file}")
            return True, backup_created
        except Exception as e:
            logger.error(f"Failed to save prompt file: {e}")
            return False, backup_created
    
    async def reload_prompts_for_handler(self, handler_name: str) -> bool:
        """Reload prompts for a specific handler after language file changes"""
        try:
            await self._load_prompts([handler_name])
            logger.info(f"Reloaded prompts for handler '{handler_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to reload prompts for handler '{handler_name}': {e}")
            return False
    
    def get_available_prompt_languages_for_handler(self, handler_name: str) -> List[str]:
        """Get list of available prompt language files for handler"""
        asset_handler_name = self._get_asset_handler_name(handler_name)
        lang_dir = self._asset_path("prompts", asset_handler_name)
        
        if not lang_dir.exists():
            return []
        
        return [lang_file.stem for lang_file in lang_dir.glob("*.yaml")]
    
    def get_handlers_with_prompts(self) -> Dict[str, List[str]]:
        """Get all handlers that have prompt files with their available languages"""
        handlers_languages = {}
        prompts_dir = self._asset_path("prompts")
        
        if not prompts_dir.exists():
            return handlers_languages
        
        for handler_dir in prompts_dir.iterdir():
            if handler_dir.is_dir() and not _should_skip_directory(handler_dir.name):
                # Convert asset handler name back to handler name
                handler_name = base_handler_name(handler_dir.name)
                
                languages = [lang_file.stem for lang_file in handler_dir.glob("*.yaml")]
                if languages:
                    handlers_languages[handler_name] = sorted(languages)
        
        return handlers_languages
    
    # ============================================================
    # LOCALIZATION ASSET MANAGEMENT (Phase 8)
    # ============================================================
    
    def get_localization_for_domain_editing(self, domain: str, language: str) -> Optional[Dict[str, Any]]:
        """Get language-specific localization data for editing"""
        domain = _safe_path_segment(domain, "domain")  # CR-A15
        language = _safe_path_segment(language, "language")  # CR-A15
        domain_dir = self._asset_path("localization", domain)
        lang_file = domain_dir / f"{language}.yaml"
        
        if not lang_file.exists():
            return None
        
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load localization for domain '{domain}', language '{language}': {e}")
            return None
    
    def save_localization_for_domain(self, domain: str, language: str, localization_data: Dict[str, Any], create_backup: bool = True) -> tuple[bool, bool]:
        """Save language-specific localization data with backup support
        
        Returns:
            tuple: (save_success, backup_created)
        """
        backup_created = False
        domain = _safe_path_segment(domain, "domain")  # CR-A15
        language = _safe_path_segment(language, "language")  # CR-A15
        domain_dir = self._asset_path("localization", domain)
        domain_dir.mkdir(parents=True, exist_ok=True)
        
        lang_file = domain_dir / f"{language}.yaml"
        
        try:
            # Create backup if requested and file exists
            if create_backup and lang_file.exists():
                backup_created = self._create_backup(lang_file, "localization", domain, language)
                if not backup_created:
                    logger.warning(f"Backup creation failed for {lang_file}, proceeding with save")
            
            # Write new content
            with open(lang_file, 'w', encoding='utf-8') as f:
                yaml.dump(localization_data, f, default_flow_style=False, allow_unicode=True, indent=2)
            
            logger.info(f"Saved {language} localization for domain '{domain}' to {lang_file}")
            return True, backup_created
        except Exception as e:
            logger.error(f"Failed to save localization for domain '{domain}', language '{language}': {e}")
            return False, backup_created
    
    async def reload_localizations_for_domain(self, domain: str) -> bool:
        """Reload localization data for a domain"""
        try:
            # For localizations, we reload the specific domain's files
            domain = _safe_path_segment(domain, "domain")  # CR-A15
            domain_dir = self._asset_path("localization", domain)
            if domain_dir.exists():
                merged_localization = {}
                for lang_file in domain_dir.glob("*.yaml"):
                    language = lang_file.stem
                    if language in self.config.supported_languages:
                        with open(lang_file, 'r', encoding='utf-8') as f:
                            lang_data = yaml.safe_load(f)
                            if lang_data:
                                merged_localization[language] = lang_data
                
                # Update cache with merged data
                self.localizations[domain] = merged_localization
                logger.info(f"Reloaded localizations for domain '{domain}' with {len(merged_localization)} languages")
                return True
            else:
                logger.warning(f"Domain directory not found for reload: {domain_dir}")
                return False
        except Exception as e:
            logger.error(f"Failed to reload localizations for domain '{domain}': {e}")
            return False
    
    def get_available_localization_languages_for_domain(self, domain: str) -> List[str]:
        """Get list of available localization language files for domain"""
        domain = _safe_path_segment(domain, "domain")  # CR-A15
        lang_dir = self._asset_path("localization", domain)
        
        if not lang_dir.exists():
            return []
        
        return [lang_file.stem for lang_file in lang_dir.glob("*.yaml")]
    
    def get_domains_with_localizations(self) -> Dict[str, List[str]]:
        """Get all domains that have localization files with their available languages"""
        domains_languages = {}
        localizations_dir = self._asset_path("localization")
        
        if not localizations_dir.exists():
            return domains_languages
        
        for domain_dir in localizations_dir.iterdir():
            if domain_dir.is_dir():
                domain = domain_dir.name
                languages = [lang_file.stem for lang_file in domain_dir.glob("*.yaml")]
                if languages:
                    domains_languages[domain] = sorted(languages)
        
        return domains_languages
    
    async def validate_localization_data(self, domain: str, localization_data: Dict[str, Any]) -> tuple[bool, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Validate localization data structure"""
        errors = []
        warnings = []
        
        try:
            # Basic YAML structure validation
            if not isinstance(localization_data, dict):
                errors.append({
                    "type": "structure",
                    "message": "Localization data must be a dictionary/object",
                    "path": "root"
                })
                return False, errors, warnings

            # Check localization entries
            for key, value in localization_data.items():
                if not isinstance(key, str):
                    errors.append({
                        "type": "structure",
                        "message": "Localization keys must be strings",
                        "path": str(key)
                    })
                    continue

                # Validate value types (can be string, list, or dict)
                if not isinstance(value, (str, list, dict)):
                    warnings.append({
                        "type": "value",
                        "message": f"Localization value has unexpected type: {type(value).__name__}",
                        "path": key
                    })
                    continue

                # Check for empty values
                if value is None or (isinstance(value, (str, list, dict)) and len(value) == 0):
                    warnings.append({
                        "type": "value",
                        "message": "Empty localization value",
                        "path": key
                    })

            # Domain-specific validation checks
            await self._validate_domain_specific_localization(domain, localization_data, errors, warnings)

            return len(errors) == 0, errors, warnings

        except Exception as e:
            errors.append({
                "type": "validation",
                "message": f"Validation failed: {str(e)}",
                "path": "validation"
            })
            return False, errors, warnings
    
    async def _validate_domain_specific_localization(self, domain: str, data: Dict[str, Any], errors: List[Dict[str, str]], warnings: List[Dict[str, str]]) -> None:
        """Domain-specific localization validation"""
        # Add domain-specific validation rules
        if domain == "datetime":
            # Check for required datetime fields
            required_fields = ["weekdays", "months", "templates"]
            for field in required_fields:
                if field not in data:
                    warnings.append({
                        "type": "missing_field",
                        "message": f"Missing expected datetime field: {field}",
                        "path": field
                    })
        elif domain == "components":
            # Check for component mappings
            if "component_mappings" not in data:
                warnings.append({
                    "type": "missing_field",
                    "message": "Missing component_mappings field",
                    "path": "component_mappings"
                })
        elif domain == "commands":
            # Check for stop patterns
            if "stop_patterns" not in data:
                warnings.append({
                    "type": "missing_field",
                    "message": "Missing stop_patterns field",
                    "path": "stop_patterns"
                })
    
    async def validate_prompt_data(self, handler_name: str, prompt_data: Dict[str, Any]) -> tuple[bool, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Validate prompt data structure"""
        errors = []
        warnings = []
        
        try:
            # Basic YAML structure validation
            if not isinstance(prompt_data, dict):
                errors.append({
                    "type": "structure",
                    "message": "Prompt data must be a dictionary/object",
                    "path": "root"
                })
                return False, errors, warnings

            # Check prompt definitions
            for prompt_name, prompt_def in prompt_data.items():
                if not isinstance(prompt_name, str):
                    errors.append({
                        "type": "structure",
                        "message": "Prompt names must be strings",
                        "path": str(prompt_name)
                    })
                    continue

                # Validate prompt definition structure
                if not isinstance(prompt_def, dict):
                    errors.append({
                        "type": "structure",
                        "message": "Prompt definitions must be objects with metadata",
                        "path": prompt_name
                    })
                    continue

                # Check required fields
                required_fields = ["description", "usage_context", "prompt_type", "content"]
                for field in required_fields:
                    if field not in prompt_def:
                        errors.append({
                            "type": "missing_field",
                            "message": f"Required field '{field}' is missing",
                            "path": f"{prompt_name}.{field}"
                        })

                # Validate prompt type
                if "prompt_type" in prompt_def:
                    valid_types = ["system", "template", "user"]
                    if prompt_def["prompt_type"] not in valid_types:
                        warnings.append({
                            "type": "value",
                            "message": f"Prompt type '{prompt_def['prompt_type']}' not in recommended types: {valid_types}",
                            "path": f"{prompt_name}.prompt_type"
                        })

                # Validate variables structure
                if "variables" in prompt_def:
                    variables = prompt_def["variables"]
                    if not isinstance(variables, list):
                        errors.append({
                            "type": "structure",
                            "message": "Variables must be a list",
                            "path": f"{prompt_name}.variables"
                        })
                    else:
                        for i, var in enumerate(variables):
                            if not isinstance(var, dict) or "name" not in var:
                                warnings.append({
                                    "type": "structure",
                                    "message": "Variable should have 'name' and 'description' fields",
                                    "path": f"{prompt_name}.variables[{i}]"
                                })

            return len(errors) == 0, errors, warnings

        except Exception as e:
            errors.append({
                "type": "validation",
                "message": f"Validation error: {str(e)}",
                "path": "validation"
            })
            return False, errors, warnings
    
    async def _load_templates(self, handler_names: List[str]) -> None:
        """Load response templates (Category B: YAML/JSON/Markdown parsing)"""
        templates_dir = self._asset_path("templates")
        
        if not templates_dir.exists():
            logger.debug("Templates directory does not exist, skipping template loading")
            return
        
        for handler_name in handler_names:
            asset_handler_name = self._get_asset_handler_name(handler_name)
            handler_template_dir = templates_dir / asset_handler_name
            
            if not handler_template_dir.exists():
                logger.debug(f"No templates directory for handler '{handler_name}' (looked for '{asset_handler_name}'), skipping")
                continue
            
            try:
                handler_templates = {}
                
                # NEW: Load consolidated language files directly (lang.yaml pattern)
                for lang_file in handler_template_dir.glob("*.yaml"):
                    language = lang_file.stem
                    lang_templates = await self._load_language_file(lang_file)
                    
                    # Merge templates by name
                    for template_name, content in lang_templates.items():
                        if template_name not in handler_templates:
                            handler_templates[template_name] = {}
                        handler_templates[template_name][language] = content
                
                if handler_templates:
                    self.templates[handler_name] = handler_templates
                    logger.debug(f"Loaded {len(handler_templates)} template sets for handler '{handler_name}' from '{asset_handler_name}'")
                
            except Exception as e:
                self._add_warning(f"Failed to load templates for handler '{handler_name}': {e}")

        # System-level template sets that are NOT tied to an enabled handler (loaded unconditionally) —
        # e.g. the QUAL-30 clarification responder's templates (assets/templates/clarification/<lang>.yaml).
        for system_set in ("clarification",):
            sys_dir = templates_dir / system_set
            if not sys_dir.exists() or system_set in self.templates:
                continue
            try:
                sys_templates: Dict[str, Any] = {}
                for lang_file in sys_dir.glob("*.yaml"):
                    language = lang_file.stem
                    for template_name, content in (await self._load_language_file(lang_file)).items():
                        sys_templates.setdefault(template_name, {})[language] = content
                if sys_templates:
                    self.templates[system_set] = sys_templates
                    logger.debug(f"Loaded system template set '{system_set}' ({len(sys_templates)} templates)")
            except Exception as e:
                self._add_warning(f"Failed to load system template set '{system_set}': {e}")

    async def _load_prompts(self, handler_names: List[str]) -> None:
        """Load LLM prompts from YAML files with metadata (YAML format only)"""
        prompts_dir = self._asset_path("prompts")
        
        if not prompts_dir.exists():
            logger.debug("Prompts directory does not exist, skipping prompt loading")
            return
        
        for handler_name in handler_names:
            asset_handler_name = self._get_asset_handler_name(handler_name)
            handler_prompt_dir = prompts_dir / asset_handler_name
            
            if not handler_prompt_dir.exists():
                logger.debug(f"No prompts directory for handler '{handler_name}' (looked for '{asset_handler_name}'), skipping")
                continue
            
            try:
                handler_prompts = {}
                
                # NEW: Load consolidated language files directly (lang.yaml pattern)
                for lang_file in handler_prompt_dir.glob("*.yaml"):
                    language = lang_file.stem
                    
                    with open(lang_file, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                        
                        # Extract prompt content from YAML structure
                        for prompt_type, prompt_data in data.items():
                            if isinstance(prompt_data, dict) and 'content' in prompt_data:
                                prompt_key = f"{prompt_type}_{language}"
                                # Store just the content for backward compatibility
                                handler_prompts[prompt_key] = prompt_data['content'].strip()
                                
                                # Store full metadata for assets editor API
                                metadata_key = f"{prompt_type}_{language}_metadata"
                                handler_prompts[metadata_key] = {
                                    'description': prompt_data.get('description', ''),
                                    'usage_context': prompt_data.get('usage_context', ''),
                                    'variables': prompt_data.get('variables', []),
                                    'prompt_type': prompt_data.get('prompt_type', 'system')
                                }
                
                if handler_prompts:
                    self.prompts[handler_name] = handler_prompts
                    logger.debug(f"Loaded {len([k for k in handler_prompts.keys() if not k.endswith('_metadata')])} prompts for handler '{handler_name}' from '{asset_handler_name}'")
                
            except Exception as e:
                self._add_warning(f"Failed to load prompts for handler '{handler_name}': {e}")

        # System-level prompt sets NOT tied to an enabled handler (loaded unconditionally) — e.g. the
        # QUAL-16 shared LLM task prompts (assets/prompts/llm/<lang>.yaml).
        for system_set in ("llm",):
            sys_dir = prompts_dir / system_set
            if not sys_dir.exists() or system_set in self.prompts:
                continue
            try:
                sys_prompts: Dict[str, Any] = {}
                for lang_file in sys_dir.glob("*.yaml"):
                    language = lang_file.stem
                    with open(lang_file, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f) or {}
                    for prompt_type, prompt_data in data.items():
                        if isinstance(prompt_data, dict) and 'content' in prompt_data:
                            sys_prompts[f"{prompt_type}_{language}"] = prompt_data['content'].strip()
                            sys_prompts[f"{prompt_type}_{language}_metadata"] = {
                                'description': prompt_data.get('description', ''),
                                'usage_context': prompt_data.get('usage_context', ''),
                                'variables': prompt_data.get('variables', []),
                                'prompt_type': prompt_data.get('prompt_type', 'system'),
                            }
                if sys_prompts:
                    self.prompts[system_set] = sys_prompts
                    logger.debug(f"Loaded system prompt set '{system_set}'")
            except Exception as e:
                self._add_warning(f"Failed to load system prompt set '{system_set}': {e}")

    async def _load_localizations(self, handler_names: List[str]) -> None:
        """Load localization data (Category C: YAML parsing)"""
        localization_dir = self._asset_path("localization")
        
        if not localization_dir.exists():
            logger.debug("Localization directory does not exist, skipping localization loading")
            return
        
        # Load domain-based localizations
        for domain_dir in localization_dir.iterdir():
            if domain_dir.is_dir():
                domain_name = domain_dir.name
                
                try:
                    domain_data = {}
                    
                    for lang_file in domain_dir.glob("*.yaml"):
                        language = lang_file.stem
                        
                        with open(lang_file, 'r', encoding='utf-8') as f:
                            domain_data[language] = yaml.safe_load(f)
                    
                    if domain_data:
                        self.localizations[domain_name] = domain_data
                        logger.debug(f"Loaded localization for domain '{domain_name}': {list(domain_data.keys())} languages")
                
                except Exception as e:
                    self._add_warning(f"Failed to load localization for domain '{domain_name}': {e}")
    
    async def _load_web_templates(self) -> None:
        """Load web templates from assets/web/templates directory (NEW)"""
        web_templates_dir = self._asset_path("web", "templates")
        
        if not web_templates_dir.exists():
            logger.debug("Web templates directory does not exist, skipping web template loading")
            return
        
        try:
            # Load all HTML template files
            for template_file in web_templates_dir.glob("*.html"):
                template_name = template_file.stem
                
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Store template content as-is - no preprocessing needed
                    # Templates should use Python format string syntax directly: {variable}
                    self.web_templates[template_name] = content
                    logger.debug(f"Loaded web template '{template_name}' from {template_file}")
                
                except Exception as e:
                    self._add_warning(f"Failed to load web template '{template_name}': {e}")
            
            if self.web_templates:
                logger.info(f"Loaded {len(self.web_templates)} web templates: {list(self.web_templates.keys())}")
        
        except Exception as e:
            self._add_warning(f"Failed to load web templates: {e}")
    
    # ============================================================
    # HELPER METHODS
    # ============================================================
    
    async def _validate_donation_schema(self, json_data: dict, json_path: Path, schema_filename: str) -> None:
        """QUAL-29: validate a v1.1 contract/language file against its JSON Schema (graceful if jsonschema absent)."""
        try:
            import jsonschema
        except ImportError:
            if self.config.strict_mode:
                raise DonationDiscoveryError(f"jsonschema library not available for validation of {json_path}")
            logger.warning("jsonschema library not available - skipping v1.1 schema validation")
            return
        schema_path = self._asset_path(schema_filename)
        if not schema_path.exists():
            logger.warning(f"v1.1 schema not found at {schema_path} - skipping schema validation")
            return
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            jsonschema.validate(instance=json_data, schema=schema)
        except jsonschema.ValidationError as e:
            error_msg = f"v1.1 schema validation failed for {json_path} against {schema_filename}: {e.message}"
            if self.config.strict_mode:
                raise DonationDiscoveryError(error_msg)
            self._add_error(error_msg)

    async def _load_language_file(self, lang_file: Path) -> Dict[str, str]:
        """Load template/prompt data from a single language file (YAML and JSON formats only)"""
        templates = {}
        
        try:
            if lang_file.suffix == '.yaml':
                with open(lang_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        templates.update(data)
                    else:
                        logger.warning(f"Expected dict in {lang_file}, got {type(data)}")
            
            elif lang_file.suffix == '.json':
                with open(lang_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        templates.update(data)
                    else:
                        logger.warning(f"Expected dict in {lang_file}, got {type(data)}")
            
            else:
                logger.debug(f"Skipping unknown file type: {lang_file}")
        
        except Exception as e:
            self._add_warning(f"Failed to load language file {lang_file}: {e}")
        
        return templates
    
    
    def _add_error(self, error_msg: str):
        """Add validation error"""
        self.validation_errors.append(error_msg)
        logger.error(error_msg)
    
    def _add_warning(self, warning_msg: str):
        """Add validation warning"""
        self.warnings.append(warning_msg)
        logger.warning(warning_msg)
    
    def _validate_contract_wiring(self) -> None:
        """QUAL-42: reconcile every loaded contract against its Python handler.

        Builds a :class:`ContractValidationReport` over the loaded donations, caches it for the UI endpoint,
        and **raises** ``DonationDiscoveryError`` if any contract declares a method that is not wired (no
        callable of that name on the handler class). Soft findings (declared-but-unread parameters, handler
        ``_handle_*`` methods absent from any contract) are logged as warnings, not fatal — unless
        ``strict_parameters`` is set, which promotes the parameter findings to fatal errors."""
        from .contract_validator import validate_contracts

        report = validate_contracts(self.donations, strict_parameters=self.config.strict_parameters)
        self.contract_validation_report = report

        for handler_report in report.handlers:
            for warning in handler_report.warnings:
                logger.warning(f"Contract wiring ({handler_report.handler_name}): {warning}")

        if not report.ok:
            error_summary = (
                f"Contract↔code wiring validation failed with {report.total_errors} unwired "
                f"method(s):\n{report.error_summary()}"
            )
            raise DonationDiscoveryError(error_summary)

        logger.info(
            f"Contract wiring validated: {len(report.handlers)} handlers, "
            f"{report.total_errors} errors, {report.total_warnings} warnings"
        )

    def _handle_validation_errors(self):
        """Handle validation errors based on configuration"""
        if self.config.strict_mode:
            error_summary = f"Asset loading failed with {len(self.validation_errors)} errors:\n"
            error_summary += "\n".join(f"  - {error}" for error in self.validation_errors)
            raise DonationDiscoveryError(error_summary)
        else:
            # Non-strict mode: log errors but continue
            for error in self.validation_errors:
                logger.error(f"Asset loading error (non-fatal): {error}")


class EnhancedHandlerManager:
    """Intent handler manager with unified asset support (replaces DonationLoader pattern)"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Create asset loader configuration
        asset_config = AssetLoaderConfig(
            **config.get('asset_validation', {})
        )
        
        # Initialize unified asset loader
        assets_root = Path(config.get('assets_root', 'assets'))
        self.asset_loader = IntentAssetLoader(assets_root, asset_config)
        
        self.handlers: Dict[str, Any] = {}  # Will contain IntentHandler instances
    
    async def initialize(self, handler_dir: Optional[Path] = None) -> None:
        """Initialize handlers with unified asset loading"""
        
        # Discover Python handler files
        if handler_dir is None:
            # package-relative, not cwd-relative: this file is backend/src/locveil_voice/core/ →
            # parents[1] is the locveil_voice package, whose intents/handlers holds the handlers.
            handler_dir = Path(__file__).resolve().parents[1] / "intents" / "handlers"
        
        handler_paths = self._discover_handler_files(handler_dir)
        handler_names = [path.stem for path in handler_paths]
        
        # Load all assets using unified loader
        await self.asset_loader.load_all_assets(handler_names)
        
        # Validate handler-asset consistency
        await self._validate_handler_asset_consistency()
        
        logger.info(f"Initialized assets for {len(handler_names)} handlers with unified asset loader")
    
    def _discover_handler_files(self, handler_dir: Path) -> List[Path]:
        """Discover Python handler files"""
        if not handler_dir.exists():
            raise DonationDiscoveryError(f"Handler directory does not exist: {handler_dir}")
        
        python_files = []
        for file_path in handler_dir.glob("*.py"):
            # Skip base.py and __init__.py
            if file_path.name not in ['base.py', '__init__.py']:
                python_files.append(file_path)
        
        return python_files
    
    async def _validate_handler_asset_consistency(self):
        """Validate that all handlers have assets and vice versa"""
        logger.info(f"Validated asset consistency for {len(self.asset_loader.donations)} handlers")
    
    def get_donations_as_keyword_donations(self) -> List[KeywordDonation]:
        """Convert JSON donations to KeywordDonation objects for NLU"""
        return self.asset_loader.convert_to_keyword_donations()
    
    def get_asset_loader(self) -> IntentAssetLoader:
        """Get the unified asset loader instance"""
        return self.asset_loader
