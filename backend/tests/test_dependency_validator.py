"""Unit tests for the shared PEP 508 package-name extractor in the dependency validator (CR-C2).

The extractor replaced two hand-rolled `>=`/`==`-only ladders that silently mis-parsed `<`/`~=`/`!=`
specs (e.g. base `numpy<2` was treated as the literal package name `numpy<2`). These cases lock in the
operator coverage and the URL / marker / extras stripping.
"""
import unittest

from locveil_voice.tools.dependency_validator import _extract_package_name


class TestExtractPackageName(unittest.TestCase):
    def test_version_operators(self):
        cases = {
            "numpy<2": "numpy",                 # the bug the old ladder missed (fell through to literal)
            "fastapi>=0.100.0": "fastapi",
            "mypy==1.15.0": "mypy",
            "torch~=2.1": "torch",
            "pkg!=1.0": "pkg",
            "uvicorn>0.20": "uvicorn",
            "spacy<=3.9,>=3.8": "spacy",
        }
        for spec, expected in cases.items():
            self.assertEqual(_extract_package_name(spec), expected, spec)

    def test_extras_marker_and_url(self):
        self.assertEqual(_extract_package_name("uvicorn[standard]>=0.20"), "uvicorn")
        self.assertEqual(
            _extract_package_name("pymicro-wakeword>=2.0.0; platform_machine != 'armv7l'"),
            "pymicro-wakeword",
        )
        self.assertEqual(
            _extract_package_name(
                "ru_core_news_md @ https://github.com/explosion/spacy-models/releases/download/"
                "ru_core_news_md-3.8.0/ru_core_news_md-3.8.0-py3-none-any.whl"
            ),
            "ru_core_news_md",
        )

    def test_bare_extra_name_passes_through(self):
        # An extra-group name (the metadata contract) has no operators → returned unchanged.
        self.assertEqual(_extract_package_name("web-api"), "web-api")
        self.assertEqual(_extract_package_name("nlu-spacy"), "nlu-spacy")


if __name__ == "__main__":
    unittest.main()
