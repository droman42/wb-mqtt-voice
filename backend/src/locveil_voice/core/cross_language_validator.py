"""
Cross-Language Validation System for Intent Donations

QUAL-29 (v1.1): with the language-neutral ``contract.json`` holding the single source of every
``ParameterSpec`` (name/type/required/choices=canonical/min-max/entity_type), parameter divergence across
languages is **impossible by construction** — so the validator no longer checks parameter parity and parameter
synchronization is a no-op. What remains genuinely cross-language is **phrasing**:
- method completeness — every contract method has phrases in each language file;
- CHOICE surface completeness — every canonical choice has spoken surface forms in each non-canonical language;
- translation suggestions — phrases present in one language but missing in another.

Report dataclasses keep their shape so the config-ui REST endpoints stay stable (Invariant #4).
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass

from .intent_asset_loader import asset_dir_name

logger = logging.getLogger(__name__)


@dataclass
class ValidationReport:
    """Report for cross-language parameter validation (v1.1: CHOICE surface completeness)."""
    handler_name: str
    languages_checked: List[str]
    parameter_consistency: bool
    missing_parameters: List[str]  # "language: method_key.param missing surfaces [canonicals]"
    extra_parameters: List[str]    # unused under v1.1 (kept for API compatibility)
    type_mismatches: List[str]     # impossible under v1.1 (kept for API compatibility)
    warnings: List[str]
    timestamp: float


@dataclass
class CompletenessReport:
    """Report for method completeness validation"""
    handler_name: str
    languages_checked: List[str]
    method_completeness: bool
    missing_methods: List[str]     # Format: "language: method_name#intent_suffix"
    extra_methods: List[str]       # Format: "language: method_name#intent_suffix"
    all_methods: Set[str]          # All method keys declared in the contract
    method_counts_by_language: Dict[str, int]
    warnings: List[str]
    timestamp: float


# The language whose surface forms equal the canonical tokens (canonical is authored in English),
# so it never needs an explicit choice_surfaces map.
CANONICAL_IDENTITY_LANG = "en"


class CrossLanguageValidator:
    """Cross-language validation for v1.1 split donations (phrasing-completeness focused)."""

    def __init__(self, assets_root: Path, asset_loader=None):
        self.assets_root = Path(assets_root)
        self.asset_loader = asset_loader

    # ----- loading (v1.1 raw structure: neutral contract + per-language phrasing) -----

    def _load_v11(self, handler_name: str) -> Tuple[Optional[dict], Dict[str, dict]]:
        """Return (contract_dict, {language: phrasing_dict}) as raw JSON. Neither is a full HandlerDonation."""
        lang_dir = self.assets_root / "donations" / asset_dir_name(handler_name)
        contract: Optional[dict] = None
        languages: Dict[str, dict] = {}
        if not lang_dir.exists():
            return contract, languages
        contract_path = lang_dir / "contract.json"
        if contract_path.exists():
            try:
                contract = json.loads(contract_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Failed to load contract.json for '{handler_name}': {e}")
        for lang_file in lang_dir.glob("*.json"):
            if lang_file.name == "contract.json":
                continue
            try:
                languages[lang_file.stem] = json.loads(lang_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Failed to load {lang_file.stem} phrasing for '{handler_name}': {e}")
        return contract, languages

    @staticmethod
    def _contract_methods(contract: Optional[dict]) -> Dict[str, dict]:
        return {f"{m['method_name']}#{m['intent_suffix']}": m
                for m in (contract or {}).get('method_donations', [])}

    @staticmethod
    def _lang_method_phrases(lang_doc: dict) -> Dict[str, List[str]]:
        return {f"{m['method_name']}#{m['intent_suffix']}": (m.get('phrases') or [])
                for m in (lang_doc or {}).get('method_donations', [])}

    # ----- validations -----

    def validate_parameter_consistency(self, handler_name: str) -> ValidationReport:
        """v1.1: parameter parity is structural (single-source contract). The only remaining cross-language
        concern is CHOICE *surface* completeness — every canonical choice should have spoken forms in each
        non-canonical language (a missing surface = that value is unrecognisable when spoken in that language)."""
        import time
        contract, languages = self._load_v11(handler_name)
        warnings: List[str] = []
        if not contract:
            warnings.append(f"No contract.json (v1.1) for handler '{handler_name}'")
            return ValidationReport(handler_name, list(languages), True, [], [], [], warnings, time.time())

        def lang_param_surfaces(doc: dict) -> Dict[str, Dict[str, dict]]:
            out: Dict[str, Dict[str, dict]] = {}
            for m in doc.get('method_donations', []):
                mk = f"{m['method_name']}#{m['intent_suffix']}"
                for p in m.get('parameters', []):
                    out.setdefault(mk, {})[p['name']] = p.get('choice_surfaces') or {}
            return out

        lsurf = {lang: lang_param_surfaces(doc) for lang, doc in languages.items()}
        missing_parameters: List[str] = []
        for mk, method in self._contract_methods(contract).items():
            for p in method.get('parameters', []):
                canonical = p.get('choices')
                if not canonical:
                    continue
                for lang in languages:
                    if lang == CANONICAL_IDENTITY_LANG:
                        continue  # canonical tokens ARE this language's surfaces (identity)
                    surfaces = lsurf.get(lang, {}).get(mk, {}).get(p['name'], {})
                    missing = [c for c in canonical if not surfaces.get(c)]
                    if missing:
                        missing_parameters.append(f"{lang}: {mk}.{p['name']} missing surfaces {missing}")

        consistent = not missing_parameters
        if not consistent:
            warnings.append("CHOICE canonical tokens without per-language surface forms — "
                            "those values are unrecognisable when spoken in that language.")
        return ValidationReport(handler_name, list(languages), consistent,
                                missing_parameters, [], [], warnings, time.time())

    def validate_method_completeness(self, handler_name: str) -> CompletenessReport:
        """Every method declared in the contract must have phrases in each language file."""
        import time
        contract, languages = self._load_v11(handler_name)
        warnings: List[str] = []
        if not contract:
            warnings.append(f"No contract.json (v1.1) for handler '{handler_name}'")
            return CompletenessReport(handler_name, list(languages), True, [], [], set(), {}, warnings, time.time())

        contract_methods = set(self._contract_methods(contract).keys())
        missing_methods: List[str] = []
        extra_methods: List[str] = []
        counts: Dict[str, int] = {}
        for lang, doc in languages.items():
            phrased = {mk for mk, phrases in self._lang_method_phrases(doc).items() if phrases}
            counts[lang] = len(phrased)
            for mk in sorted(contract_methods - phrased):
                missing_methods.append(f"{lang}: {mk}")
            for mk in sorted(phrased - contract_methods):
                extra_methods.append(f"{lang}: {mk}")

        complete = not missing_methods and not extra_methods
        return CompletenessReport(handler_name, list(languages), complete, missing_methods, extra_methods,
                                  contract_methods, counts, warnings, time.time())

    # QUAL-43: suggest_translations + its confidence/language-detection helpers were removed — the rule-based
    # phrase-gap suggester is superseded by the LLM translation service (POST /donations/{h}/translate).

    # ----- helpers -----
