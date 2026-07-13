"""Tests for the contract↔code wiring validator (QUAL-42).

Covers: fatal detection of an unwired contract method, the soft (warning) classification of an unread
parameter, the strict_parameters ratchet, reverse `_handle_*` coverage, the AST parameter-reference scan, and a
smoke test that the REAL shipped handlers validate with zero fatal errors (so startup never falsely fails boot).
"""

import json
import glob
import os

import pytest

from locveil_voice.core.contract_validator import (
    ContractWiringValidator,
    _ParamReferenceCollector,
    validate_contracts,
)


# A real, known-good handler module stem + a method/param we know is wired.
def test_real_handler_methods_are_wired():
    v = ContractWiringValidator()
    # timer handler implements _handle_set_timer and reads 'duration' via get_param
    report = v.validate_handler("timer", {"_handle_set_timer": ["duration", "unit", "message"]}, [])
    assert report.handler_class == "TimerIntentHandler"
    assert report.errors == []  # all methods wired
    # duration/unit/message are all read by the timer handler → no param warnings
    assert not any("duration" in w for w in report.warnings)


def test_unwired_method_is_fatal():
    v = ContractWiringValidator()
    report = v.validate_handler("timer", {"_handle_does_not_exist": []}, [])
    assert len(report.errors) == 1
    assert "not wired" in report.errors[0]


def test_unread_parameter_is_soft_warning_by_default():
    v = ContractWiringValidator()
    # invent a declared param the handler never reads
    report = v.validate_handler("timer", {"_handle_set_timer": ["totally_unused_param"]}, [])
    assert report.errors == []  # not fatal
    assert any("totally_unused_param" in w for w in report.warnings)


def test_strict_parameters_promotes_unread_to_fatal():
    v = ContractWiringValidator(strict_parameters=True)
    report = v.validate_handler("timer", {"_handle_set_timer": ["totally_unused_param"]}, [])
    assert any("totally_unused_param" in e for e in report.errors)


def test_reverse_coverage_flags_undeclared_handler_method():
    # QUAL-66 swept the live tree to zero wiring warnings (internal helpers renamed off the
    # `_handle_` prefix), so exercise the check by DECLARING NOTHING for a real handler —
    # every genuine `_handle_*` routing method must then be flagged as undeclared.
    v = ContractWiringValidator()
    report = v.validate_handler("timer", {}, [])
    assert any("_handle_set_timer" in w and "not declared" in w for w in report.warnings)


def test_param_reference_collector_finds_both_access_paths():
    import ast
    src = (
        "class H:\n"
        "    def m(self, intent):\n"
        "        a = self.get_param(intent, 'alpha')\n"
        "        b = intent.entities.get('beta')\n"
        "        c = intent.entities['gamma']\n"
        "        d = self.get_param(intent, name='delta')\n"
    )
    collector = _ParamReferenceCollector()
    collector.visit(ast.parse(src))
    assert collector.names == {"alpha", "beta", "gamma", "delta"}


def test_validate_contracts_over_all_real_handlers_has_no_fatal_errors():
    """The shipped handlers must validate clean (0 fatal) — otherwise startup would refuse to boot."""
    # Build {handler_name(module stem): contract dict} from the real donation contracts.
    mods = {os.path.basename(p)[:-3] for p in glob.glob("irene/intents/handlers/*.py")} - {"base", "__init__"}

    class _MethodDonation:
        def __init__(self, name, params):
            self.method_name = name
            self.parameters = [type("P", (), {"name": n}) for n in params]

    class _Donation:
        def __init__(self, methods, globals_):
            self.method_donations = [_MethodDonation(n, ps) for n, ps in methods.items()]
            self.global_parameters = [type("P", (), {"name": n}) for n in globals_]

    donations = {}
    for d in glob.glob("assets/donations/*/contract.json"):
        asset_dir = os.path.basename(os.path.dirname(d))
        stem = asset_dir[:-len("_handler")] if asset_dir.endswith("_handler") else asset_dir
        handler_name = asset_dir if asset_dir in mods else (stem if stem in mods else asset_dir)
        contract = json.load(open(d))
        methods = ContractWiringValidator.methods_from_contract(contract)
        globals_ = ContractWiringValidator.global_params_from_contract(contract)
        donations[handler_name] = _Donation(methods, globals_)

    report = validate_contracts(donations)
    assert report.total_errors == 0, report.error_summary()
    assert report.ok is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
