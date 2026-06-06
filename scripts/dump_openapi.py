#!/usr/bin/env python3
"""Dump the Irene Web API OpenAPI schema to a committed JSON file (UI-5).

config-ui generates its API types from this committed schema (``openapi-typescript``), mirroring the bridge's
committed-schema model — so the frontend types never drift from the backend and never need a running server to
regenerate. Routes are *built* independently of request-time state (handlers capture ``core``/``asset_loader`` in
closures and only touch them per request), so we assemble a throwaway FastAPI app from the same router factory +
WebAPIPlugin component routers the real runner uses, then serialise ``app.openapi()``.

Run after any contract/endpoint change:  uv run python scripts/dump_openapi.py
"""

import importlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "config-ui" / "openapi.json"

# Components that expose a WebAPIPlugin router (mirrors the runner's discovery, listed explicitly so the dump is
# deterministic and needs no component manager).
WEBAPI_COMPONENTS = [
    ("irene.components.intent_component", "IntentComponent"),
    ("irene.components.configuration_component", "ConfigurationComponent"),
    ("irene.components.monitoring_component", "MonitoringComponent"),
    ("irene.components.tts_component", "TTSComponent"),
    ("irene.components.asr_component", "ASRComponent"),
    ("irene.components.audio_component", "AudioComponent"),
    ("irene.components.llm_component", "LLMComponent"),
    ("irene.components.nlu_component", "NLUComponent"),
    ("irene.components.nlu_analysis_component", "NLUAnalysisComponent"),
    ("irene.components.text_processor_component", "TextProcessorComponent"),
    ("irene.components.voice_trigger_component", "VoiceTriggerComponent"),
]


def build_app():
    from fastapi import FastAPI

    from irene.__version__ import __version__

    app = FastAPI(
        title="Irene Voice Assistant API",
        description="Modern async voice assistant API with WebSocket support",
        version=__version__,
    )

    mounted: list[str] = []

    # Main router (command/system/web endpoints). Handlers capture core/asset_loader but don't touch them at
    # build time, so None is fine for schema generation.
    try:
        from irene.runners.webapi_router import create_webapi_router

        app.include_router(create_webapi_router(core=None, asset_loader=None, web_input=None, start_time=0.0))  # type: ignore[arg-type]
        mounted.append("main_router")
    except Exception as e:  # pragma: no cover - best-effort
        print(f"  ! skipped main_router: {e}", file=sys.stderr)

    # Component routers (donations/intent endpoints live on IntentComponent).
    for module_name, class_name in WEBAPI_COMPONENTS:
        try:
            component = getattr(importlib.import_module(module_name), class_name)()
            router = component.get_router()
            if router is None:
                continue
            app.include_router(router, prefix=component.get_api_prefix(), tags=component.get_api_tags())
            mounted.append(class_name)
        except Exception as e:  # pragma: no cover - best-effort
            print(f"  ! skipped {class_name}: {e}", file=sys.stderr)

    return app, mounted


def main() -> int:
    app, mounted = build_app()
    schema = app.openapi()
    paths = schema.get("paths", {})
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    donation_paths = [p for p in paths if "/donations" in p]
    print(f"Wrote {OUTPUT.relative_to(REPO_ROOT)}: {len(paths)} paths, mounted {len(mounted)} routers.")
    print(f"  donation endpoints: {len(donation_paths)}")
    if not donation_paths:
        print("ERROR: no /donations endpoints in schema — IntentComponent router failed to mount.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
