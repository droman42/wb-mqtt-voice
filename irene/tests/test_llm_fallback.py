"""QUAL-15 — LLM offline foundation: real fallback chain + console floor.

Contract under test (component-level, no network):
  * the provider chain is preferred/default → fallback_providers → console (terminal floor);
  * `is_available()` reports a REAL model only — the console stub never counts;
  * `generate_response`/`enhance_text` never raise offline: they fall through to the console floor
    (localized "unavailable" message / unchanged text) and, with no providers at all, still return
    the last-resort text rather than crashing.

Construction is bypassed with `object.__new__` (the methods only touch a handful of attrs), matching
the new-code recipe used in test_voice_runner.py.
"""
from irene.components.llm_component import LLMComponent, _LLM_UNAVAILABLE_LAST_RESORT
from irene.providers.llm.console import ConsoleLLMProvider


class _FakeProvider:
    """A real (non-stub) provider; raises when `fail=True` to exercise the fall-through."""
    is_stub = False

    def __init__(self, name, fail=False):
        self._name = name
        self._fail = fail

    async def chat_completion(self, messages, **kwargs):
        if self._fail:
            raise RuntimeError(f"{self._name} offline")
        return f"{self._name}-response"

    async def enhance_text(self, text, task="improve", **kwargs):
        if self._fail:
            raise RuntimeError(f"{self._name} offline")
        return f"{self._name}-enhanced"


def _component(providers, default="deepseek", fallback=("console",), initialized=True):
    c = object.__new__(LLMComponent)  # skip heavy construction; the methods use only these attrs
    c.providers = providers
    c.default_provider = default
    c.fallback_providers = list(fallback)
    c.initialized = initialized
    c._default_language = "ru"
    c._messages_loaded = True        # skip the asset load in unit tests
    c._unavailable_messages = {}
    c._cached_asset_loader = None     # _get_task_prompt falls back to the generic last-resort prompt
    return c


def _console(**responses):
    p = ConsoleLLMProvider({})
    p._responses.update(responses)
    return p


# --- provider chain ordering (the QUAL-15 contract) -------------------------------------------------

def test_provider_chain_orders_preferred_default_then_fallback_then_console():
    c = _component({"deepseek": _FakeProvider("deepseek"),
                    "openai": _FakeProvider("openai"),
                    "console": _console()},
                   default="deepseek", fallback=["openai", "console"])
    # default first, configured fallbacks next, console terminal
    assert c._provider_chain() == ["deepseek", "openai", "console"]
    # an explicit `preferred` REPLACES the default at the head (then the configured fallbacks follow)
    assert c._provider_chain("openai") == ["openai", "console"]


def test_console_is_appended_as_terminal_floor_even_when_unconfigured():
    c = _component({"deepseek": _FakeProvider("deepseek"), "console": _console()},
                   default="deepseek", fallback=[])
    assert c._provider_chain() == ["deepseek", "console"]


def test_provider_chain_drops_unloaded_names_and_dedupes():
    # "ghost" is configured but not loaded → dropped; duplicate console not appended twice
    c = _component({"deepseek": _FakeProvider("deepseek"), "console": _console()},
                   default="deepseek", fallback=["ghost", "console"])
    assert c._provider_chain() == ["deepseek", "console"]


# --- is_available excludes the stub -----------------------------------------------------------------

async def test_is_available_excludes_console_stub():
    only_console = _component({"console": _console()})
    real = _component({"deepseek": _FakeProvider("deepseek"), "console": _console()})
    not_ready = _component({"deepseek": _FakeProvider("deepseek")}, initialized=False)
    assert await only_console.is_available() is False   # the floor is not a real model
    assert await real.is_available() is True
    assert await not_ready.is_available() is False      # off path: never initialized


# --- generate_response never raises offline ---------------------------------------------------------

async def test_generate_response_uses_real_provider_when_available():
    c = _component({"deepseek": _FakeProvider("deepseek"), "console": _console()})
    assert await c.generate_response([{"role": "user", "content": "hi"}]) == "deepseek-response"


async def test_generate_response_falls_through_to_console_localized_floor():
    c = _component({"deepseek": _FakeProvider("deepseek", fail=True),
                    "console": _console(ru="недоступна", en="unavailable")})
    out = await c.generate_response([{"role": "user", "content": "hi"}], language="en")
    assert out == "unavailable"


async def test_generate_response_with_no_providers_returns_last_resort_text():
    c = _component({})  # nothing loaded — must still not raise
    out = await c.generate_response([{"role": "user", "content": "hi"}])
    assert out == _LLM_UNAVAILABLE_LAST_RESORT


# --- enhance_text falls through to the no-op floor --------------------------------------------------

async def test_enhance_text_uses_real_provider_when_available():
    c = _component({"deepseek": _FakeProvider("deepseek"), "console": _console()})
    assert await c.enhance_text("text", task="improve") == "deepseek-enhanced"


async def test_enhance_text_falls_through_to_console_returns_original_unchanged():
    # real provider offline → console floor returns the input text verbatim (honest no-op)
    c = _component({"deepseek": _FakeProvider("deepseek", fail=True), "console": _console()})
    assert await c.enhance_text("original text", task="improve") == "original text"
