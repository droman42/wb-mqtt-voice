"""CR-C12: `web_api_components` is the single source of the "iterate components, filter WebAPIPlugin" walk
that was reimplemented in web_server.py and webapi_router.py. It must filter to WebAPIPlugin and degrade
to `[]` (never crash) when the component manager is absent or its lookup fails."""
import unittest
from types import SimpleNamespace

from locveil_voice.core.interfaces.webapi import WebAPIPlugin, web_api_components


class _Plugin(WebAPIPlugin):
    @property
    def name(self) -> str:
        return "p"

    def get_router(self):
        return None


class _NotPlugin:
    pass


def _core(components=None, raises=False):
    class _CM:
        def get_components(self):
            if raises:
                raise RuntimeError("boom")
            return components or {}
    return SimpleNamespace(component_manager=_CM())


class TestWebApiComponents(unittest.TestCase):
    def test_filters_to_webapiplugin(self):
        p = _Plugin()
        self.assertEqual(web_api_components(_core({"p": p, "x": _NotPlugin()})), [("p", p)])

    def test_none_core_degrades(self):
        self.assertEqual(web_api_components(None), [])

    def test_missing_component_manager_degrades(self):
        self.assertEqual(web_api_components(SimpleNamespace()), [])

    def test_get_components_failure_degrades(self):
        self.assertEqual(web_api_components(_core(raises=True)), [])


if __name__ == "__main__":
    unittest.main()
