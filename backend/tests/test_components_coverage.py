"""
TEST-7 Phase D — characterization tests for irene/core/components.py.

Targets the ComponentManager registry surface (get_component / get_components /
get_component_info / has_component / get_active_components), the deployment-profile
detector, registration + graceful-failure bookkeeping, shutdown, and the
DependencyResolver topological sort.

Heavy construction is bypassed: ComponentManager only needs a CoreConfig (a cheap
Pydantic settings object) and a fake ComponentPort, so no real components / models /
entry-point discovery are exercised. Everything runs under asyncio.run for hermeticity.
"""

import asyncio
import unittest

from locveil_voice.config.models import CoreConfig, ComponentConfig, InputConfig, SystemConfig
from locveil_voice.core.components import (
    ComponentManager,
    ComponentInfo,
    DependencyResolver,
    ComponentNotAvailable,
)


def _arun(coro):
    return asyncio.run(coro)


class _FakeComponent:
    """Minimal ComponentPort stand-in for registry tests."""

    def __init__(self, name, initialized=True, py_deps=None):
        self._name = name
        self.initialized = initialized
        self._py_deps = py_deps or []
        self.shutdown_called = False
        self.shutdown_should_raise = False

    @property
    def name(self):
        return self._name

    def get_python_dependencies(self):
        return list(self._py_deps)

    async def shutdown(self):
        self.shutdown_called = True
        if self.shutdown_should_raise:
            raise RuntimeError("boom")


def _make_manager(config=None):
    return ComponentManager(config or CoreConfig())


class TestRegistryAccessors(unittest.TestCase):
    def test_get_component_missing_returns_none(self):
        mgr = _make_manager()
        self.assertIsNone(mgr.get_component("nope"))

    def test_get_component_returns_registered(self):
        mgr = _make_manager()
        comp = _FakeComponent("tts")
        mgr._components["tts"] = comp
        self.assertIs(mgr.get_component("tts"), comp)

    def test_get_components_returns_copy(self):
        mgr = _make_manager()
        comp = _FakeComponent("tts")
        mgr._components["tts"] = comp
        snapshot = mgr.get_components()
        self.assertEqual(snapshot, {"tts": comp})
        # Mutating the returned dict must not affect the manager's registry.
        snapshot["extra"] = _FakeComponent("extra")
        self.assertNotIn("extra", mgr._components)

    def test_get_active_components(self):
        mgr = _make_manager()
        mgr._components["a"] = _FakeComponent("a")
        mgr._components["b"] = _FakeComponent("b")
        self.assertEqual(set(mgr.get_active_components()), {"a", "b"})

    def test_has_component_requires_initialized(self):
        mgr = _make_manager()
        mgr._components["ready"] = _FakeComponent("ready", initialized=True)
        mgr._components["pending"] = _FakeComponent("pending", initialized=False)
        self.assertTrue(mgr.has_component("ready"))
        self.assertFalse(mgr.has_component("pending"))
        self.assertFalse(mgr.has_component("absent"))


class TestComponentInfo(unittest.TestCase):
    def test_info_for_success_and_failure(self):
        mgr = _make_manager()
        mgr._components["tts"] = _FakeComponent("tts", initialized=True, py_deps=["torch"])
        mgr._failed_components["asr"] = ValueError("missing model")

        info = mgr.get_component_info()
        self.assertEqual(set(info), {"tts", "asr"})

        good = info["tts"]
        self.assertIsInstance(good, ComponentInfo)
        self.assertTrue(good.available)
        self.assertTrue(good.initialized)
        self.assertEqual(good.dependencies, ["torch"])
        self.assertIsNone(good.error_message)

        bad = info["asr"]
        self.assertFalse(bad.available)
        self.assertFalse(bad.initialized)
        self.assertEqual(bad.error_message, "missing model")
        self.assertEqual(bad.dependencies, [])

    def test_componentinfo_defaults(self):
        ci = ComponentInfo(name="x", available=True)
        # __post_init__ normalises None dependencies to an empty list.
        self.assertEqual(ci.dependencies, [])
        self.assertFalse(ci.initialized)


class TestFailureBookkeeping(unittest.TestCase):
    def test_failed_components_copy_and_query(self):
        mgr = _make_manager()
        err = RuntimeError("nope")
        mgr._failed_components["llm"] = err

        failed = mgr.get_failed_components()
        self.assertEqual(failed, {"llm": err})
        # Returned mapping is a copy.
        failed["other"] = RuntimeError("x")
        self.assertNotIn("other", mgr._failed_components)

        self.assertTrue(mgr.is_component_failed("llm"))
        self.assertFalse(mgr.is_component_failed("tts"))


class TestEnabledAndConfigLookup(unittest.TestCase):
    def test_is_component_enabled(self):
        # TTS requires Audio (CoreConfig cross-validator), so enable both.
        cfg = CoreConfig(components=ComponentConfig(tts=True, audio=True, asr=False))
        mgr = _make_manager(cfg)
        self.assertTrue(mgr._is_component_enabled("tts"))
        self.assertFalse(mgr._is_component_enabled("asr"))
        # intent_system defaults to enabled (essential).
        self.assertTrue(mgr._is_component_enabled("intent_system"))
        # Unknown component name → graceful False.
        self.assertFalse(mgr._is_component_enabled("ghost"))

    def test_get_component_config(self):
        mgr = _make_manager()
        # Each real component has a typed config section on CoreConfig.
        self.assertIsNotNone(mgr._get_component_config("tts"))
        # Unknown name → None, not an error.
        self.assertIsNone(mgr._get_component_config("ghost"))


class TestDeploymentProfile(unittest.TestCase):
    def test_voice_profile(self):
        cfg = CoreConfig(
            components=ComponentConfig(tts=True, audio=True, asr=True),
            inputs=InputConfig(microphone=True),
        )
        self.assertEqual(_make_manager(cfg).get_deployment_profile(), "voice")

    def test_api_profile_default(self):
        # Defaults: web input, no microphone, web_api_enabled, no tts → api.
        self.assertEqual(_make_manager().get_deployment_profile(), "api")

    def test_headless_profile(self):
        cfg = CoreConfig(
            components=ComponentConfig(tts=False),
            inputs=InputConfig(microphone=False, web=False, cli=True),
            system=SystemConfig(web_api_enabled=False),
        )
        self.assertEqual(_make_manager(cfg).get_deployment_profile(), "headless")

    def test_custom_profile_counts_enabled(self):
        # tts requires audio; asr disabled + microphone disabled keeps it out of "voice".
        cfg = CoreConfig(
            components=ComponentConfig(tts=True, audio=True, llm=True, asr=False),
            inputs=InputConfig(microphone=False),
            system=SystemConfig(web_api_enabled=True),
        )
        profile = _make_manager(cfg).get_deployment_profile()
        # tts True defeats both api and headless; microphone False defeats voice → custom.
        self.assertTrue(profile.startswith("custom("))
        # enabled among [tts, audio, asr, llm, voice_trigger, nlu, text_processor] → tts, audio, llm.
        self.assertIn("3 components", profile)


class TestShutdown(unittest.TestCase):
    def test_shutdown_when_not_initialized_is_noop(self):
        mgr = _make_manager()
        mgr._components["tts"] = _FakeComponent("tts")
        # Not initialized → early return, registry untouched.
        _arun(mgr.shutdown_all())
        self.assertIn("tts", mgr._components)

    def test_shutdown_clears_and_calls_components(self):
        mgr = _make_manager()
        a = _FakeComponent("a")
        b = _FakeComponent("b")
        mgr._components["a"] = a
        mgr._components["b"] = b
        mgr._failed_components["c"] = RuntimeError("x")
        mgr._initialized = True

        _arun(mgr.shutdown_all())

        self.assertTrue(a.shutdown_called)
        self.assertTrue(b.shutdown_called)
        self.assertEqual(mgr._components, {})
        self.assertEqual(mgr._failed_components, {})
        self.assertFalse(mgr._initialized)

    def test_shutdown_swallows_component_errors(self):
        mgr = _make_manager()
        bad = _FakeComponent("bad")
        bad.shutdown_should_raise = True
        mgr._components["bad"] = bad
        mgr._initialized = True

        # A failing component.shutdown() is logged, not raised; teardown still completes.
        _arun(mgr.shutdown_all())
        self.assertTrue(bad.shutdown_called)
        self.assertFalse(mgr._initialized)
        self.assertEqual(mgr._components, {})


class _DepComponent:
    """No-arg component used by DependencyResolver (it instantiates the class)."""

    deps_by_name = {}

    def __init__(self):
        # The resolver builds a transient instance per class; pick deps off a name
        # bound by the closure factory below.
        self._deps = []

    def get_component_dependencies(self):
        return self._deps


def _dep_class(deps):
    class _C(_DepComponent):
        def __init__(self):
            super().__init__()
            self._deps = list(deps)

    return _C


class TestDependencyResolver(unittest.TestCase):
    def test_topological_order_respects_dependencies(self):
        # b depends on a, c depends on b → order must place a before b before c.
        config = {
            "a": _dep_class([]),
            "b": _dep_class(["a"]),
            "c": _dep_class(["b"]),
        }
        resolver = DependencyResolver(config)
        order = resolver.resolve_initialization_order(["a", "b", "c"])
        self.assertEqual(order, ["a", "b", "c"])

    def test_resolver_handles_unknown_and_bad_components(self):
        # 'x' is enabled but not in config; 'boom' raises on instantiation.
        class _Boom:
            def __init__(self):
                raise RuntimeError("cannot construct")

        config = {"a": _dep_class([]), "boom": _Boom}
        resolver = DependencyResolver(config)
        order = resolver.resolve_initialization_order(["a", "boom", "x"])
        # All enabled nodes still appear; failure to read deps is treated as no deps.
        self.assertEqual(set(order), {"a", "boom", "x"})

    def test_topological_sort_directly(self):
        resolver = DependencyResolver({})
        graph = {"a": ["b"], "b": ["c"], "c": []}
        self.assertEqual(resolver._topological_sort(graph), ["a", "b", "c"])


class TestMisc(unittest.TestCase):
    def test_component_not_available_is_exception(self):
        with self.assertRaises(ComponentNotAvailable):
            raise ComponentNotAvailable("x")

    def test_get_component_dependencies_for_unknown(self):
        mgr = _make_manager()
        # Unknown name resolves to [] without raising (entry-point discovery miss).
        self.assertEqual(mgr._get_component_dependencies_for("ghost-xyz"), [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
