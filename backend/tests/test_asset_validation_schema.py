"""QUAL-41 regression — IntentAssetLoader validator output must match api.schemas.

`validate_template_data` / `validate_prompt_data` / `validate_localization_data`
emit error/warning dicts that the intent_component editing endpoints feed straight
into `ValidationError(**err)` / `ValidationWarning(**warn)`. Before QUAL-41 they
emitted `{field, message, severity}`, but the schemas require `{type, message}`
(+ optional `path`/`line`), so any *real* validation failure raised a pydantic
error → HTTP 500. These tests construct the schema models from the validator
output for inputs that DO fail, which is exactly the path that used to 500.
"""

from pathlib import Path

import pytest

from locveil_voice.api.schemas import ValidationError, ValidationWarning
from locveil_voice.core.intent_asset_loader import IntentAssetLoader


@pytest.fixture
def loader() -> IntentAssetLoader:
    # The validators are pure structural checks; assets_root is never touched.
    return IntentAssetLoader(assets_root=Path("."))


def _roundtrip(error_list, warning_list):
    """Mirror intent_component.py: build the API schema models (used to 500)."""
    errors = [ValidationError(**e) for e in error_list]
    warnings = [ValidationWarning(**w) for w in warning_list]
    # Every error/warning must carry a non-empty discriminating type + message.
    for item in (*errors, *warnings):
        assert item.type
        assert item.message
    return errors, warnings


@pytest.mark.asyncio
async def test_template_validation_errors_match_schema(loader):
    # Non-dict root + an unusual value type → at least one error and one warning.
    is_valid, errs, warns = await loader.validate_template_data("test", "not-a-dict")  # type: ignore[arg-type]
    assert is_valid is False
    e, w = _roundtrip(errs, warns)
    assert e and e[0].type == "structure" and e[0].path == "root"

    _, errs2, warns2 = await loader.validate_template_data("test", {"greeting": object()})
    _roundtrip(errs2, warns2)
    assert any(x.type == "value" for x in [ValidationWarning(**w) for w in warns2])


@pytest.mark.asyncio
async def test_prompt_validation_errors_match_schema(loader):
    # Missing required fields + bad variables type → multiple errors.
    prompt_data = {
        "main": {"description": "d"},  # missing usage_context/prompt_type/content
        "bad": {
            "description": "d",
            "usage_context": "u",
            "prompt_type": "nonsense",  # warning
            "content": "c",
            "variables": "not-a-list",  # error
        },
    }
    is_valid, errs, warns = await loader.validate_prompt_data("test", prompt_data)
    assert is_valid is False
    e, w = _roundtrip(errs, warns)
    assert any(x.type == "missing_field" for x in e)
    assert any(x.path and x.path.endswith(".variables") for x in e)


@pytest.mark.asyncio
async def test_localization_validation_errors_match_schema(loader):
    # Non-dict root → error; datetime domain missing fields → warnings.
    is_valid, errs, warns = await loader.validate_localization_data("datetime", [1, 2, 3])  # type: ignore[arg-type]
    assert is_valid is False
    _roundtrip(errs, warns)

    _, errs2, warns2 = await loader.validate_localization_data("datetime", {"weekdays": ["mon"]})
    e2, w2 = _roundtrip(errs2, warns2)
    assert any(x.type == "missing_field" for x in w2)
