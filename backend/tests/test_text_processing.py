"""QUAL-13 — unified text processor (the collapsed subsystem).

One config-driven processor with per-stage normalizer chains replaced the 4 stage-specific providers.
Verifies: stages are data (config-driven chains), the two real stages (asr_output / tts_input) apply
the right normalizers in order, disabled normalizers don't run, and number normalization is dependency-free
for Russian.
"""

from locveil_voice.providers.text_processor.unified import UnifiedTextProcessor, NORMALIZER_ORDER


def _cfg(numbers=True, prepare=True, runorm=False):
    return {
        "enabled": True,
        "normalizers": {
            "numbers": {"enabled": numbers, "stages": ["asr_output", "tts_input"]},
            "prepare": {"enabled": prepare, "stages": ["asr_output", "tts_input"]},
            "runorm": {"enabled": runorm, "stages": ["tts_input"]},
        },
    }


async def test_stage_chains_are_config_driven():
    p = UnifiedTextProcessor(_cfg(runorm=True))
    assert await p.is_available() is True
    assert p.get_supported_stages() == ["asr_output", "tts_input"]
    # asr_output: numbers + prepare (runorm is tts-only); order follows NORMALIZER_ORDER
    assert p.normalizers_for_stage("asr_output") == ["numbers", "prepare"]
    # tts_input: numbers + prepare + runorm
    assert p.normalizers_for_stage("tts_input") == ["numbers", "prepare", "runorm"]
    # order invariant
    assert NORMALIZER_ORDER == ["numbers", "prepare", "runorm"]


async def test_disabled_normalizer_does_not_run():
    p = UnifiedTextProcessor(_cfg(prepare=False))
    await p.is_available()
    assert p.normalizers_for_stage("asr_output") == ["numbers"]
    assert "prepare" not in p.normalizers


async def test_number_normalization_runs_per_stage_dependency_free():
    p = UnifiedTextProcessor(_cfg())
    await p.is_available()
    # Russian numbers normalize through the dependency-free pure-Python path
    assert await p.process_pipeline("5 минут", "asr_output") == "пять минут"
    assert await p.process_pipeline("осталось 10 секунд", "tts_input") == "осталось десять секунд"


async def test_unknown_stage_is_a_noop():
    p = UnifiedTextProcessor(_cfg())
    await p.is_available()
    # a stage with no mapped normalizers returns the text unchanged (not an error)
    assert p.normalizers_for_stage("general") == []
    assert await p.process_pipeline("5 минут", "general") == "5 минут"


async def test_disabled_processor_is_unavailable():
    p = UnifiedTextProcessor({"enabled": False, "normalizers": {}})
    assert await p.is_available() is False
