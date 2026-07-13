"""ARCH-46 — report-protocol conformance (HK-3/PROD-6; spec ../locveil-commons/process/problem-reports.md §2).

The problem-report wire surface (labels, title prefixes, bundle path, envelope fields) is a
commons-owned machine core, vendored at `contracts/pins/report-protocol/` (tag
`report-protocol-vN` — see the pin folder's README for the re-pin command). This test asserts the
collector's EMITTED surface against the pin: a label mismatch makes tickets silently invisible to
the triage workflow's label-gated trigger and the `/inbox` queue queries, so the copies scattered
through skills/configs are kept honest here rather than trusted.
"""
import json
import re
import tomllib
from pathlib import Path

import pytest

from locveil_voice.core.report_service import build_envelope

_REPO_ROOT = Path(__file__).resolve().parents[2]
PIN = json.loads(
    (_REPO_ROOT / "contracts" / "pins" / "report-protocol" / "report-protocol.json").read_text(encoding="utf-8"))
PROBLEM_REPORT = PIN["types"]["problem-report"]

# The six deployment profiles (config-master/example are curated supersets with a placeholder repo).
DEPLOYMENT_CONFIGS = [
    "embedded-armv7.toml", "embedded-armv7-en.toml",
    "embedded-aarch64.toml", "embedded-aarch64-en.toml",
    "standalone-x86_64.toml", "standalone-x86_64-en.toml",
]


def _summary(room="спальня"):
    return {
        "description": "свет в спальне не включается",
        "report_id": "r-20260711-abc123",
        "last_turns": [
            {"user": "включи свет", "intent": "smart_home.power_on", "irene": "Включаю свет"},
        ],
        "metadata": {
            "created_utc": "2026-07-11T10:30:00Z",
            "room": room,
            "version": "15.0.0",
            "profile": "embedded-armv7",
            "machine": "armv7l",
            "language": "ru",
            "catalog_version": "1.4.0",
            "report_id": "r-20260711-abc123",
        },
    }


class TestCollectorEmitsThePinnedSurface:
    """`build_envelope` is the single writer seam — everything GitHub sees goes through it."""

    def test_labels_match_filed_with(self):
        envelope = build_envelope(_summary(), source="voice")
        lens_label = PIN["lenses"]["voice"]["label"]
        expected = [lens_label if l == "<lens label>" else l for l in PROBLEM_REPORT["filed_with"]]
        assert envelope["labels"] == expected

    def test_bridge_ui_source_files_under_the_bridge_lens(self):
        # The shared-intake seam (design D-3): same envelope builder, bridge lens at filing.
        envelope = build_envelope(_summary(), source="bridge-ui")
        assert PIN["lenses"]["bridge"]["label"] in envelope["labels"]
        assert envelope["title"].startswith(PROBLEM_REPORT["title_prefixes"]["bridge"] + " ")

    def test_title_prefix(self):
        envelope = build_envelope(_summary(), source="voice")
        assert envelope["title"].startswith(PROBLEM_REPORT["title_prefixes"]["voice"] + " ")

    def test_bundle_path_matches_the_template(self):
        envelope = build_envelope(_summary(room="kitchen"), source="voice")
        pattern = re.escape(PIN["bundle_path"])
        pattern = pattern.replace(re.escape("<utc_stamp>"), r"[0-9TZ]+")
        pattern = pattern.replace(re.escape("<source>"), "voice")
        pattern = pattern.replace(re.escape("<room>"), "kitchen")
        assert re.fullmatch(pattern, envelope["bundle_path"]), envelope["bundle_path"]

    def test_envelope_carries_every_required_field(self):
        summary = _summary()
        envelope = build_envelope(summary, source="voice")
        body = envelope["body"]
        # The pin names the required fields; map each to its concrete rendering in the body.
        renderings = {
            "free_text_verbatim": summary["description"],
            "last_turns_synopsis": "**Last turns:**",
            "environment": "**Environment:**",
            "bundle_link": "{bundle_url}",  # substituted with the real URL at upload time
            "report_id": f"report-id: {summary['metadata']['report_id']}",
        }
        assert set(renderings) == set(PROBLEM_REPORT["envelope_required"])
        for field, marker in renderings.items():
            assert marker in body, f"envelope_required field {field!r} missing from the body"


class TestConfiguredRepoMatchesThePin:
    """The pin's `repos` object is the slug registry — deployment configs must agree with it."""

    @pytest.mark.parametrize("config_name", DEPLOYMENT_CONFIGS)
    def test_deployment_profile_points_at_the_pinned_reports_repo(self, config_name):
        with open(_REPO_ROOT / "configs" / config_name, "rb") as f:
            config = tomllib.load(f)
        assert config["reports"]["enabled"] is True
        assert config["reports"]["repo"] == PIN["repos"]["reports"]
