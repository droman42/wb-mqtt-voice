"""
Contract wiring validator — donation contract ↔ handler-code reconciliation (QUAL-42).

The cross-language validator (``cross_language_validator.py``) checks that *language files* agree with the
contract. This module checks that the **contract agrees with the Python handler**: every method a contract
declares must be a real callable on the handler class, and every parameter it declares should actually be read
by the handler. It closes the gap the donation review flagged — nothing previously reconciled a contract against
the code it claims to drive (only contract→method existence, never params or reverse coverage).

Two severities, by design:

* **errors (fatal):** a contract method that is *not wired* — no callable of that name on the handler class.
  These raise ``DonationDiscoveryError`` at startup (a contract pointing at a non-existent method is always a
  bug). This is the "raise an exception if they aren't wired" requirement.

* **warnings (soft):** a declared parameter that is never read via ``get_param``/``intent.entities`` anywhere in
  the handler module, or a ``_handle_*`` method on the handler that no contract declares. These are NOT fatal
  because they have legitimate causes — a param read from ``context`` (e.g. ``language``) or in a helper, an
  internal ``_handle_*`` helper, etc. Promote them to errors with ``strict_parameters=True`` once a codebase is
  known clean (a ratchet).

Hexagon: lives in ``core`` and imports only the domain handler package (``core → intents`` is an allowed inward
edge); it never reaches into components/providers. Handler introspection is static (``ast`` over the module
source) — it does not execute handler code.
"""

import ast
import importlib
import inspect
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Set

logger = logging.getLogger(__name__)

HANDLERS_PACKAGE = "locveil_voice.intents.handlers"


@dataclass
class HandlerWiringReport:
    """Per-handler contract↔code reconciliation result."""
    handler_name: str
    handler_class: Optional[str] = None
    errors: List[str] = field(default_factory=list)     # fatal — unwired contract methods
    warnings: List[str] = field(default_factory=list)   # soft — unread params / undeclared handler methods
    methods_checked: int = 0
    params_checked: int = 0


@dataclass
class ContractValidationReport:
    """System-wide roll-up across all validated handlers."""
    handlers: List[HandlerWiringReport] = field(default_factory=list)
    timestamp: float = 0.0

    @property
    def total_errors(self) -> int:
        return sum(len(h.errors) for h in self.handlers)

    @property
    def total_warnings(self) -> int:
        return sum(len(h.warnings) for h in self.handlers)

    @property
    def ok(self) -> bool:
        return self.total_errors == 0

    def error_summary(self) -> str:
        lines: List[str] = []
        for h in self.handlers:
            for e in h.errors:
                lines.append(f"  - {h.handler_name}: {e}")
        return "\n".join(lines)


class _ParamReferenceCollector(ast.NodeVisitor):
    """Collect string-literal parameter names a handler module reads, via the two real access paths:
    ``self.get_param(intent, "name")`` / ``get_typed_param(..., "name")`` and ``intent.entities.get("name")`` /
    ``intent.entities["name"]``. Scanning the whole module (not just one method) folds in helper-method reads,
    which keeps the "unread parameter" warning low-noise."""

    PARAM_ACCESSORS = {"get_param", "get_typed_param"}

    def __init__(self) -> None:
        self.names: Set[str] = set()

    @staticmethod
    def _string_consts(args) -> List[str]:
        return [a.value for a in args if isinstance(a, ast.Constant) and isinstance(a.value, str)]

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Attribute):
            # self.get_param(intent, "name", ...) / get_typed_param(...)
            if func.attr in self.PARAM_ACCESSORS:
                for s in self._string_consts(node.args):
                    self.names.add(s)
                for kw in node.keywords:
                    if kw.arg == "name" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                        self.names.add(kw.value.value)
            # <...>.entities.get("name", ...)
            elif func.attr == "get" and isinstance(func.value, ast.Attribute) and func.value.attr == "entities":
                for s in self._string_consts(node.args[:1]):
                    self.names.add(s)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        # <...>.entities["name"]
        if (isinstance(node.value, ast.Attribute) and node.value.attr == "entities"
                and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str)):
            self.names.add(node.slice.value)
        self.generic_visit(node)


class ContractWiringValidator:
    """Validate that donation contracts are wired into their Python handlers."""

    def __init__(self, strict_parameters: bool = False):
        # When True, "declared but unread" parameters become fatal errors (ratchet for a clean codebase).
        self.strict_parameters = strict_parameters
        self._handler_class_cache: Dict[str, Optional[type]] = {}
        self._param_ref_cache: Dict[str, Optional[Set[str]]] = {}

    # ----- public API -----

    def validate_handler(
        self,
        handler_name: str,
        methods: Dict[str, List[str]],
        global_params: Optional[List[str]] = None,
    ) -> HandlerWiringReport:
        """Validate one handler. ``methods`` maps contract method_name → declared parameter names;
        ``global_params`` are the contract's global parameter names."""
        report = HandlerWiringReport(handler_name=handler_name)
        handler_class = self._resolve_handler_class(handler_name, report)
        if handler_class is None:
            return report  # import failure already recorded as a warning; can't validate further
        report.handler_class = handler_class.__name__

        # (1) Method wiring — FATAL. Every contract method must be a callable on the class.
        for method_name in methods:
            report.methods_checked += 1
            if not callable(getattr(handler_class, method_name, None)):
                report.errors.append(
                    f"contract method '{method_name}' is not wired: no callable '{method_name}' on "
                    f"{handler_class.__name__}"
                )

        # (2) Parameter reads — SOFT (or fatal under strict_parameters).
        referenced = self._referenced_param_names(handler_name)
        sink = report.errors if self.strict_parameters else report.warnings
        if referenced is not None:
            for method_name, pnames in methods.items():
                for pname in pnames:
                    report.params_checked += 1
                    if pname not in referenced:
                        sink.append(
                            f"parameter '{pname}' of method '{method_name}' is declared in the contract but "
                            f"never read by the handler (no get_param/entities access)"
                        )
            for pname in (global_params or []):
                report.params_checked += 1
                if pname not in referenced:
                    sink.append(
                        f"global parameter '{pname}' is declared in the contract but never read by the handler"
                    )

        # (3) Reverse method coverage — SOFT. A handler method that no contract method declares.
        contract_method_names = set(methods)
        for name, member in handler_class.__dict__.items():
            if name.startswith("_handle_") and callable(member) and name not in contract_method_names:
                report.warnings.append(
                    f"handler method '{name}' is not declared in any contract method (possible missing donation)"
                )

        return report

    def validate_donation(self, handler_name: str, donation) -> HandlerWiringReport:
        """Convenience: validate against a loaded ``HandlerDonation`` (the assembled v1.1 object)."""
        methods: Dict[str, List[str]] = {}
        for md in getattr(donation, "method_donations", []) or []:
            methods[md.method_name] = [p.name for p in (getattr(md, "parameters", None) or [])]
        global_params = [p.name for p in (getattr(donation, "global_parameters", None) or [])]
        return self.validate_handler(handler_name, methods, global_params)

    @staticmethod
    def methods_from_contract(contract: dict) -> Dict[str, List[str]]:
        """Extract method_name → [param names] from a raw contract.json dict."""
        out: Dict[str, List[str]] = {}
        for m in (contract or {}).get("method_donations", []):
            out[m["method_name"]] = [p["name"] for p in (m.get("parameters") or [])]
        return out

    @staticmethod
    def global_params_from_contract(contract: dict) -> List[str]:
        return [p["name"] for p in (contract or {}).get("global_parameters", []) or []]

    # ----- internals -----

    def _resolve_handler_class(self, handler_name: str, report: HandlerWiringReport) -> Optional[type]:
        if handler_name in self._handler_class_cache:
            return self._handler_class_cache[handler_name]
        cls: Optional[type] = None
        try:
            module = importlib.import_module(f"{HANDLERS_PACKAGE}.{handler_name}")
            for item_name in dir(module):
                item = getattr(module, item_name)
                if (isinstance(item, type) and hasattr(item, "__bases__")
                        and any("IntentHandler" in base.__name__ for base in item.__bases__)):
                    cls = item
                    break
            if cls is None:
                report.warnings.append(
                    f"could not validate wiring: no IntentHandler class found in module "
                    f"'{HANDLERS_PACKAGE}.{handler_name}'"
                )
        except Exception as e:
            # Import failure (e.g. an optional dependency) — can't validate, but don't block boot on it.
            report.warnings.append(f"could not import handler module to validate wiring: {e}")
        self._handler_class_cache[handler_name] = cls
        return cls

    def _referenced_param_names(self, handler_name: str) -> Optional[Set[str]]:
        if handler_name in self._param_ref_cache:
            return self._param_ref_cache[handler_name]
        names: Optional[Set[str]] = None
        try:
            module = importlib.import_module(f"{HANDLERS_PACKAGE}.{handler_name}")
            source = inspect.getsource(module)
            collector = _ParamReferenceCollector()
            collector.visit(ast.parse(source))
            names = collector.names
        except Exception as e:
            logger.debug(f"Could not scan parameter references for '{handler_name}': {e}")
            names = None  # unknown → skip param warnings rather than emit false positives
        self._param_ref_cache[handler_name] = names
        return names


def validate_contracts(
    donations: Mapping[str, object],
    strict_parameters: bool = False,
) -> ContractValidationReport:
    """Validate a set of loaded ``{handler_name: HandlerDonation}`` donations. Used at startup."""
    validator = ContractWiringValidator(strict_parameters=strict_parameters)
    report = ContractValidationReport(timestamp=time.time())
    for handler_name, donation in donations.items():
        report.handlers.append(validator.validate_donation(handler_name, donation))
    return report
