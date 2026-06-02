# Archived documentation (historical)

These documents are **point-in-time artifacts** from the v13 → v15 refactor: completed-phase reports,
implementation/design plans for work that has since shipped, one-off bug-fix writeups, and migration
guides for migrations that are already done. They are kept for history and rationale, but they do **not**
describe the current system and should not be treated as canonical reference.

For current, maintained documentation see:

- `../../README.md` — project overview
- `../architecture.md` — system architecture
- `../guides/` — audio, VAD, handler-development and donation reference guides
- `../../configs/config-master.toml` — the canonical, fully-commented configuration reference

## Contents

| Category | Files |
|---|---|
| Phase reports | `phase0_pattern_analysis_report.md`, `phase35_completion_summary.md`, `phase35_pattern_analysis_report.md`, `phase35_revised_pattern_analysis.md`, `PHASE3_INTEGRATION.md` |
| Refactor / design plans | `refactoring.md`, `plugin_refactor.md`, `architecture_intents.md`, `intent_implementation.md`, `config_cleanup.md`, `configuration_cleanup.md`, `component_loading.md`, `metrics_unification.md`, `parameter_extraction.md`, `language_detection.md`, `tts_audio_separation.md`, `irene_startup.md`, `vad_improvements.md`, `unify_context.md`, `unify_history.md`, `unify_sessions.md`, `dependency_harmonization.md`, `plugins_migration_guide.md` |
| Bug-fix / issue writeups | `fix_vosk.md`, `VAD_SIBILANT_FIX.md`, `ESP32_LiteRT_Implementation.md` |
| Completed migration guides | `VAD_MIGRATION_GUIDE.md`, `CONTEXTUAL_COMMANDS_MIGRATION_GUIDE.md` |
| Superseded refs / completed plans (ARCH-0 / DOC-6) | `config_schemas.md`, `language_support.md`, `configuration_guide.md` (v13), `PIPELINE_IMPLEMENTATION.md` (plugin-era), `irene_current.md` (pre-refactor VACore/Jaa) |
| Deferred UI designs (never built; idea kept in plan) | `workflow_control.md` (config-ui pipeline-viz page → **UI-4 [WORKFLOWVIZ]**) |

_Archived during the v15 documentation cleanup. Recover any file with `git mv docs/archive/<file> docs/<file>` if it turns out to still be needed._
