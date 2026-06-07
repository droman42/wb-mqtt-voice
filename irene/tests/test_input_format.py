"""ARCH-15 PR-1 (D-1) — `InputFormat` as the first-class pipeline-entry selector.

Proves: the format↔skip-flags bijection, that RequestContext makes `input_format` the single
source of truth (deriving the legacy flags), back-compat inference from the flags, and that the
workflow's `configure_pipeline_stages` selects the same stages as the pre-refactor skip-flag logic.
"""

import pytest

from irene.intents.context_models import InputFormat, RequestContext


# format -> (skip_wake_word, skip_asr) and the entry stage each implies
CASES = [
    (InputFormat.VOICE, (False, False)),
    (InputFormat.AUDIO, (True, False)),
    (InputFormat.TEXT, (True, True)),
]


@pytest.mark.parametrize("fmt,flags", CASES)
def test_to_flags_bijection(fmt, flags):
    assert fmt.to_flags() == flags
    assert InputFormat.from_flags(*flags) is fmt


def test_from_flags_maps_nonsensical_combo_to_text():
    # (wake-word on, ASR off) never occurs; skip_asr implies TEXT.
    assert InputFormat.from_flags(False, True) is InputFormat.TEXT


@pytest.mark.parametrize("fmt,flags", CASES)
def test_request_context_format_is_source_of_truth(fmt, flags):
    """Passing input_format derives the legacy flags consistently."""
    ctx = RequestContext(source="x", input_format=fmt)
    assert ctx.input_format is fmt
    assert (ctx.skip_wake_word, ctx.skip_asr) == flags


@pytest.mark.parametrize("fmt,flags", CASES)
def test_request_context_infers_format_from_legacy_flags(fmt, flags):
    """Back-compat: callers still passing skip_* flags get the right format inferred."""
    skip_wake_word, skip_asr = flags
    ctx = RequestContext(source="x", skip_wake_word=skip_wake_word, skip_asr=skip_asr)
    assert ctx.input_format is fmt
    assert (ctx.skip_wake_word, ctx.skip_asr) == flags


def test_request_context_defaults_to_voice():
    """No format, no flags → VOICE (full pipeline), matching the prior default."""
    ctx = RequestContext(source="x")
    assert ctx.input_format is InputFormat.VOICE
    assert (ctx.skip_wake_word, ctx.skip_asr) == (False, False)


# --- configure_pipeline_stages equivalence -------------------------------------------------

def _legacy_stages(base_stages, source, skip_wake_word, skip_asr, wants_audio):
    """The exact pre-refactor logic from base.configure_pipeline_stages, for equivalence."""
    stages = dict(base_stages)
    if skip_wake_word or source == "text":
        stages["voice_trigger"] = False
    if source == "text" or skip_asr:
        stages["asr"] = False
    if not wants_audio:
        stages["tts"] = False
    return stages


@pytest.mark.parametrize("fmt,flags", CASES)
@pytest.mark.parametrize("wants_audio", [True, False])
def test_configure_pipeline_stages_matches_legacy(fmt, flags, wants_audio):
    from irene.workflows.base import Workflow

    # A minimal Workflow subclass — we only exercise configure_pipeline_stages.
    class _W(Workflow):
        async def initialize(self): ...
        async def process_audio_stream(self, *a, **k): ...

    wf = _W()
    base = dict(wf._pipeline_stages)

    source = "text" if fmt is InputFormat.TEXT else "voice"
    ctx = RequestContext(source=source, input_format=fmt, wants_audio=wants_audio)

    got = wf.configure_pipeline_stages(ctx)
    expected = _legacy_stages(base, source, flags[0], flags[1], wants_audio)
    assert got == expected
