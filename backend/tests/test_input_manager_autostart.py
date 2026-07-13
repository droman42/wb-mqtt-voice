"""ARCH-15 PR-5b — the InputManager auto-starts the `cli` source (PR-0 stopgap removed).

PR-0 temporarily stopped auto-starting `cli` to avoid a double-reader (the runner ran its own
prompt_toolkit reader AND the InputManager auto-started a second one whose queue nothing drained).
PR-5b removes that stopgap: the interactive runner no longer reads stdin itself — it CONSUMES the
single CLIInput source's `listen()` stream. So there is exactly one reader (CLIInput._input_loop,
spawned by auto-start) and one consumer; the double-reader is structurally impossible. These tests
assert the source is auto-started again.
"""

from locveil_voice.config.models import InputConfig
from locveil_voice.inputs.manager import InputManager


async def test_cli_source_auto_started():
    """With cli enabled + default, `cli` is discovered AND auto-started (the single reader)."""
    cfg = InputConfig(microphone=False, web=False, cli=True, default_input="cli")
    mgr = InputManager(component_manager=None, input_config=cfg)

    await mgr.initialize()

    assert "cli" in mgr._sources, "CLI source should be registered"
    assert "cli" in mgr._active_sources, "CLI source should be auto-started (PR-0 stopgap removed)"
    assert mgr._sources["cli"].is_listening() is True

    await mgr.close()


async def test_cli_listen_stream_available_for_consumer():
    """The auto-started CLIInput exposes a listen() stream for the runner's consume loop."""
    cfg = InputConfig(microphone=False, web=False, cli=True, default_input="cli")
    mgr = InputManager(component_manager=None, input_config=cfg)

    await mgr.initialize()
    source = mgr._sources["cli"]
    # The adapter is listening and its async listen() generator is usable by the consumer.
    assert source.is_listening() is True
    assert hasattr(source, "listen")

    await mgr.close()
