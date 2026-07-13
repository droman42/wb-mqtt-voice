"""QUAL-59 — /system/capabilities must reflect what is actually loaded.

The old endpoint hardcoded provider/workflow lists that drifted from reality: it advertised a
"continuous_listening" workflow that no longer exists and omitted the llm NLU provider.
"""

import pytest


def test_capabilities_derived_from_runtime():
    pytest.importorskip("fastapi")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from locveil_voice.runners.webapi_router import create_webapi_router

    class _NLU:
        providers = {"hybrid_keyword_matcher": object(), "spacy_nlu": object(), "llm": object()}

    class _CM:
        def get_component(self, name):
            return _NLU() if name == "nlu" else None

        def get_available_components(self):
            return {"nlu": _NLU()}

    class _WM:
        workflows = {"unified_voice_assistant": object()}

    class _Core:
        component_manager = _CM()
        workflow_manager = _WM()
        config = None
        plugin_manager = None

    router = create_webapi_router(_Core(), asset_loader=None, web_input=None, start_time=0.0)
    app = FastAPI()
    app.include_router(router)

    caps = TestClient(app).get("/system/capabilities").json()

    assert caps["nlu_providers"] == ["hybrid_keyword_matcher", "llm", "spacy_nlu"]
    assert caps["workflows"] == ["unified_voice_assistant"]
    # components without providers report empty, never a stale hardcoded list
    assert caps["voice_trigger_providers"] == []
    assert "continuous_listening" not in caps["workflows"]
