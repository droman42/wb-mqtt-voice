"""CR-C8: Component._apply_provider_config — the single source of the `/configure` "set default_provider
if it names a loaded provider, else warn and keep" gate (was copy-pasted across 6 component configure
endpoints). Exercised via a duck-typed self so no abstract Component subclass is needed."""
import logging
import unittest
from types import SimpleNamespace

from locveil_voice.components.base import Component


def _component(providers, default):
    return SimpleNamespace(
        providers=providers, default_provider=default,
        name="test", logger=logging.getLogger("test.apply_provider_config"),
    )


class TestApplyProviderConfig(unittest.TestCase):
    def test_switches_to_loaded_provider(self):
        c = _component({"a": object(), "b": object()}, "a")
        Component._apply_provider_config(c, {"default_provider": "b"})
        self.assertEqual(c.default_provider, "b")

    def test_keeps_default_when_provider_not_loaded(self):
        c = _component({"a": object()}, "a")
        Component._apply_provider_config(c, {"default_provider": "ghost"})
        self.assertEqual(c.default_provider, "a")

    def test_noop_when_not_requested(self):
        c = _component({"a": object()}, "a")
        Component._apply_provider_config(c, {})
        self.assertEqual(c.default_provider, "a")


if __name__ == "__main__":
    unittest.main()
