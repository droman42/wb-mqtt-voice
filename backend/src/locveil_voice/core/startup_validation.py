"""Startup validation — QUAL-23.

A fail-fast(ish) guard for the systemic *"a configured provider name doesn't
resolve to a real entry-point"* bug class that the QUAL-8/10/12/14 review wave
hit four times (the phantom `console` LLM provider, the non-existent NLU
`provider_cascade_order` defaults, dead text-processor provider/stage names).

After the components initialize, this checks that every **configured** provider
name — `default_provider`, `fallback_providers`, `provider_cascade_order`, and
every enabled ``[<component>.providers.<name>]`` block — corresponds to a
**registered entry-point** in that component's provider namespace. Names are
checked against the registered entry-point *names* (not loaded), so an optional
dependency that fails to import is not mistaken for a missing provider.

Default behavior: log a clear ERROR per unresolved name and continue (non-fatal,
so a shipped config that still carries a known-bad name — e.g. the `console` LLM
fallback pending QUAL-15 — boots with the problem made loud). Set
``IRENE_STARTUP_STRICT=1`` to raise instead; intended for CI / the TEST-0 smoke
harness once the known offenders (QUAL-11/13/15) are fixed.
"""

from __future__ import annotations

import logging
import os
from importlib.metadata import entry_points
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)

# component config key -> provider entry-point namespace
COMPONENT_NAMESPACES: Dict[str, str] = {
    "llm": "locveil_voice.providers.llm",
    "nlu": "locveil_voice.providers.nlu",
    "tts": "locveil_voice.providers.tts",
    "asr": "locveil_voice.providers.asr",
    "audio": "locveil_voice.providers.audio",
    "voice_trigger": "locveil_voice.providers.voice_trigger",
    "text_processor": "locveil_voice.providers.text_processor",
}

# config fields that reference a provider name by value (vs the providers dict keys)
_NAME_REF_FIELDS = ("default_provider", "fallback_providers", "provider_cascade_order")


def _registered_provider_names(namespace: str) -> Set[str]:
    """Registered entry-point names for a namespace (without loading them)."""
    try:
        return {ep.name for ep in entry_points(group=namespace)}
    except Exception as e:  # pragma: no cover - importlib edge cases
        logger.warning(f"[startup-validation] could not enumerate entry-points for '{namespace}': {e}")
        return set()


def _as_dict(config: Any) -> Dict[str, Any]:
    if hasattr(config, "model_dump"):
        try:
            return config.model_dump()
        except Exception:
            pass
    return config if isinstance(config, dict) else {}


def validate_provider_configuration(config: Any) -> List[str]:
    """Return human-readable issues for configured provider names that don't resolve.

    Empty list == every configured name resolves to a registered entry-point.
    """
    issues: List[str] = []
    cfg = _as_dict(config)

    for component, namespace in COMPONENT_NAMESPACES.items():
        section = cfg.get(component)
        if not isinstance(section, dict):
            continue
        if section.get("enabled", True) is False:
            continue  # disabled component — its provider names are inactive

        registered = _registered_provider_names(namespace)
        if not registered:
            continue  # enumeration failed / no providers — nothing to check against

        refs: List[tuple] = []
        for field in _NAME_REF_FIELDS:
            value = section.get(field)
            if isinstance(value, str) and value:
                refs.append((field, value))
            elif isinstance(value, list):
                refs.extend((field, n) for n in value if isinstance(n, str) and n)
        # enabled provider sub-blocks: [<component>.providers.<name>] enabled = true
        providers = section.get("providers", {})
        if isinstance(providers, dict):
            for pname, pconf in providers.items():
                if isinstance(pconf, dict) and pconf.get("enabled", False):
                    refs.append(("providers (enabled)", pname))

        for source, name in refs:
            if name not in registered:
                issues.append(
                    f"{component}.{source}: provider '{name}' is configured but is not a registered "
                    f"'{namespace}' entry-point (available: {sorted(registered)})"
                )

    return issues


def run_startup_validation(config: Any) -> List[str]:
    """Validate + log. Honors ``IRENE_STARTUP_STRICT`` (raise on any issue)."""
    try:
        issues = validate_provider_configuration(config)
    except Exception as e:  # never let the guard itself break boot
        logger.warning(f"[startup-validation] skipped due to internal error: {e}")
        return []

    if issues:
        for msg in issues:
            logger.error(f"[startup-validation] {msg}")
        logger.error(
            f"[startup-validation] {len(issues)} configured provider name(s) do not resolve to a "
            f"registered entry-point (QUAL-23). Fix the config or implement the provider."
        )
        if os.getenv("IRENE_STARTUP_STRICT", "").lower() in ("1", "true", "yes"):
            raise RuntimeError(
                f"Startup validation failed: {len(issues)} unresolved provider name(s) — see logs above."
            )
    else:
        logger.info(
            "[startup-validation] all configured provider names resolve to registered entry-points ✓"
        )
    return issues
