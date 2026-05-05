# Tasks: 7-template-workflow-sync-redesign

**Feature ID:** 7-template-workflow-sync-redesign
**Spec:** /specs/7-template-workflow-sync-redesign.md

## Status

- Total: 8
- Complete: 8
- Remaining: 0
- Blocked: 0

## Pre-Implementation Tests

| AC | Test File | Status |
|----|-----------|--------|
| AC-1 | tests/test_feature_authoring_sync_baseline.py::test_template_workflow_metadata_roundtrip | [x] Written |
| AC-1 | tests/test_import.py::test_import_preserves_workflow_metadata | [x] Written |
| AC-1 | tests/test_import.py::test_import_normalizes_malformed_workflow_metadata | [x] Written |
| AC-2 | tests/test_sync_bundled.py::test_bundled_prompt_taxonomy_and_renamed_triggers | [x] Written |
| AC-3 | tests/test_sync_bundled.py::test_bundled_quick_help_uses_renamed_triggers | [x] Written |
| AC-3 | tests/test_commands_popup.py::test_build_command_catalog_exposes_workflow_metadata | [x] Written |
| AC-3 | tests/test_commands_popup.py::test_commands_popup_dialog_renders_entries | [x] Written |
| AC-4 | tests/test_commands_popup.py::test_build_command_catalog_includes_template_and_system_triggers | [x] Written |
| AC-5 | tests/test_remote_sync.py::TestSyncCommandLanes::test_publish_runs_local_espanso_publish | [x] Written |
| AC-5 | tests/test_remote_sync.py::TestSyncCommandLanes::test_pull_refreshes_espanso_output_after_remote_pull | [x] Written |
| AC-5 | tests/test_remote_sync.py::TestSyncCommandLanes::test_top_level_help_lists_source_of_truth_lanes | [x] Written |
| AC-5 | tests/test_completions.py::test_bash_script_contains_subcommands | [x] Written |
| AC-5 | tests/test_completions.py::test_zsh_script_contains_subcommands | [x] Written |
| AC-6 | tests/test_sync_bundled.py::test_sync_bundled_apply_migrates_renamed_starter_with_backup | [x] Written |
| AC-6 | tests/test_sync_bundled.py::test_sync_bundled_blocks_renamed_trigger_collision | [x] Written |
| AC-6 | tests/test_sync_bundled.py::test_sync_to_espanso_blocks_renamed_trigger_collision_before_writing | [x] Written |
| AC-7 | Multiple suites and final checks | [x] Verified |

## Task List

### T-1: Feature contract and breaking decision

- **Files:** `specs/7-template-workflow-sync-redesign.md`, `tasks/7-template-workflow-sync-redesign.md`, `decisions/0002-template-workflow-sync-redesign.md`, `workflow/STATE.json`
- **Test File:** N/A
- **Done when:** The feature contract, execution task list, decision record, and active workflow state identify the redesign scope and migration posture.
- **Criteria covered:** AC-2, AC-5, AC-6, AC-7
- **Branch:** `copilot/feat-template-workflow-sync-redesign`
- **Status:** [x] Complete

### T-2: Template metadata foundation

- **Files:** `espansr/core/templates.py`, `docs/TEMPLATES.md`, `tests/test_feature_authoring_sync_baseline.py`, `tests/test_import.py`
- **Test File:** `tests/test_feature_authoring_sync_baseline.py`, `tests/test_import.py`
- **Done when:** Workflow metadata fields round-trip through core template save/load/version/import paths and are documented.
- **Criteria covered:** AC-1
- **Branch:** `copilot/feat-template-metadata`
- **Status:** [x] Complete

### T-3: Bundled prompt taxonomy and direct renames

- **Files:** `templates/*.json`, `templates/espansr_help.json`, `tests/test_sync_bundled.py`
- **Test File:** `tests/test_sync_bundled.py`
- **Done when:** Bundled starter templates use the new names, triggers, descriptions, categories, stages, and chain hints.
- **Criteria covered:** AC-2, AC-3
- **Branch:** `copilot/feat-prompt-taxonomy`
- **Status:** [x] Complete

### T-4: Starter migration and retirement mechanics

- **Files:** `espansr/core/templates.py`, `espansr/__main__.py`, `tests/test_sync_bundled.py`
- **Test File:** `tests/test_sync_bundled.py`
- **Done when:** Old bundled filenames/triggers are migrated, backed up, preserved, or reported according to the migration contract.
- **Criteria covered:** AC-2, AC-6
- **Branch:** `copilot/feat-starter-migration`
- **Status:** [x] Complete

### T-5: Help catalog and commands popup redesign

- **Files:** `espansr/core/command_catalog.py`, `espansr/ui/commands_popup.py`, `espansr/integrations/espanso.py`, `templates/espansr_help.json`, `tests/test_commands_popup.py`, `tests/test_launcher.py`
- **Test File:** `tests/test_commands_popup.py`, `tests/test_launcher.py`
- **Done when:** `:coms` and `:espansr` surface categories, stages, generated system triggers, and no stale trigger names.
- **Criteria covered:** AC-3, AC-4
- **Branch:** `copilot/feat-command-catalog-taxonomy`
- **Status:** [x] Complete

### T-6: Sync command model redesign

- **Files:** `espansr/__main__.py`, `espansr/core/remote.py`, `espansr/core/config.py`, `tests/test_remote_sync.py`, `tests/test_completions.py`
- **Test File:** `tests/test_remote_sync.py`, `tests/test_completions.py`
- **Done when:** Public CLI commands communicate publish, pull, push, starter, and remote lanes with clear behavior and completion coverage.
- **Criteria covered:** AC-5, AC-7
- **Branch:** `copilot/feat-sync-command-model`
- **Status:** [x] Complete

### T-7: Documentation and quick-start refresh

- **Files:** `docs/CLI.md`, `docs/TEMPLATES.md`, `docs/VERIFY.md`, `README.md`, `templates/espansr_help.json`
- **Test File:** N/A
- **Done when:** Docs and quick help tell the same command, sync, and prompt-chain story.
- **Criteria covered:** AC-3, AC-4, AC-5, AC-7
- **Branch:** `copilot/docs-template-workflow-sync`
- **Status:** [x] Complete

### T-8: Full verification and follow-up cleanup

- **Files:** `tasks/7-template-workflow-sync-redesign.md`, possibly `bugs/LOG.md`
- **Test File:** Multiple suites
- **Done when:** Focused suites, full pytest, and ruff are run or explicitly skipped with evidence; any residual risk is documented.
- **Criteria covered:** AC-7
- **Branch:** `copilot/verify-template-workflow-sync`
- **Status:** [x] Complete

## Routing Plan

| Task | Suggested Model | Rationale | Reviewer | Parallel? | Context Needs |
|------|-----------------|-----------|----------|-----------|---------------|
| T-1 | Copilot | Contract and decision are grounded in the current analysis | Claude | No | Small |
| T-2 | Copilot | Focused schema and docs/test update | Claude | No | Small |
| T-3 | Copilot | Template wording and metadata consistency | Claude | No, depends on T-2 | Medium |
| T-4 | Claude | Migration behavior requires careful safety logic | Copilot | No, depends on T-3 | Medium |
| T-5 | Copilot | Catalog and popup updates follow existing tests | Claude | Yes after T-2/T-3 | Medium |
| T-6 | Claude | CLI behavior changes are user-facing and riskier | Copilot | No | Large |
| T-7 | Copilot | Documentation consolidation | Claude | Yes after behavior settles | Medium |
| T-8 | Copilot | Verification and evidence capture | Claude | No | Small |

## Test Strategy

- AC-1: `tests/test_feature_authoring_sync_baseline.py::test_template_workflow_metadata_roundtrip`; `tests/test_import.py::test_import_preserves_workflow_metadata`; `tests/test_import.py::test_import_normalizes_malformed_workflow_metadata`
- AC-2: bundled taxonomy and migration tests in `tests/test_sync_bundled.py`
- AC-3: prompt chain and category tests in `tests/test_commands_popup.py` plus docs review
- AC-4: quick help, launcher, popup, and completions tests
- AC-5: CLI parser, completions, and remote/publish behavior tests
- AC-6: starter migration tests in `tests/test_sync_bundled.py`
- AC-7: focused suites, `pytest`, `ruff check .`, and documented Windows workflow-lint skip

## Evidence Log

- 2026-05-05 T-1/T-2 - commands run: `pytest tests/test_feature_authoring_sync_baseline.py::test_template_workflow_metadata_roundtrip tests/test_import.py::test_import_preserves_workflow_metadata`; `pytest tests/test_feature_authoring_sync_baseline.py tests/test_import.py`; `ruff check espansr/core/templates.py tests/test_feature_authoring_sync_baseline.py tests/test_import.py`; editor diagnostics, result: pass, notes: feature contract, breaking decision, active state, metadata schema, docs, and tests added
- 2026-05-05 verification repair - commands run: `pytest tests/test_import.py::test_import_preserves_workflow_metadata tests/test_import.py::test_import_normalizes_malformed_workflow_metadata tests/test_feature_authoring_sync_baseline.py::test_template_workflow_metadata_roundtrip`; `pytest tests/test_feature_authoring_sync_baseline.py tests/test_import.py`; `pytest tests/test_sync_bundled.py tests/test_commands_popup.py`; `ruff check espansr/core/templates.py tests/test_feature_authoring_sync_baseline.py tests/test_import.py`; `git diff --check`; editor diagnostics, result: pass, notes: normalized malformed workflow metadata and updated AC-1 traceability
- 2026-05-05 T-3 - commands run: `pytest tests/test_sync_bundled.py`; `black tests/test_sync_bundled.py`; `pytest tests/test_sync_bundled.py tests/test_commands_popup.py`; `ruff check espansr/core/templates.py tests/test_feature_authoring_sync_baseline.py tests/test_import.py tests/test_sync_bundled.py`; editor diagnostics, result: pass, notes: bundled starter files renamed, trigger taxonomy applied, metadata added, and `:espansr` quick help refreshed
- 2026-05-05 T-4 - commands run: `pytest tests/test_sync_bundled.py::test_sync_bundled_apply_migrates_renamed_starter_with_backup tests/test_sync_bundled.py::test_sync_bundled_blocks_renamed_trigger_collision tests/test_sync_bundled.py::test_sync_to_espanso_blocks_renamed_trigger_collision_before_writing` before and after implementation; `black espansr/core/templates.py espansr/__main__.py espansr/integrations/espanso.py tests/test_sync_bundled.py`; `pytest tests/test_sync_bundled.py tests/test_commands_popup.py`; `ruff check espansr/core/templates.py espansr/__main__.py espansr/integrations/espanso.py tests/test_sync_bundled.py tests/test_feature_authoring_sync_baseline.py tests/test_import.py`; editor diagnostics, result: pass, notes: old renamed starter files migrate with version backups and renamed-trigger collisions block before Espanso output is written
- 2026-05-05 T-5 - commands run: `pytest tests/test_commands_popup.py::test_build_command_catalog_exposes_workflow_metadata tests/test_commands_popup.py::test_commands_popup_dialog_renders_entries` before and after implementation; `black espansr/core/command_catalog.py espansr/ui/commands_popup.py tests/test_commands_popup.py`; `pytest tests/test_commands_popup.py tests/test_launcher.py tests/test_sync_bundled.py`; `ruff check espansr/core/command_catalog.py espansr/ui/commands_popup.py espansr/integrations/espanso.py espansr/core/templates.py espansr/__main__.py tests/test_commands_popup.py tests/test_launcher.py tests/test_sync_bundled.py tests/test_feature_authoring_sync_baseline.py tests/test_import.py`; editor diagnostics, result: pass, notes: command catalog entries now expose category, stage, and next-trigger hints, and the popup renders workflow metadata
- 2026-05-05 T-6 - commands run: `pytest tests/test_remote_sync.py::TestSyncCommandLanes::test_publish_runs_local_espanso_publish tests/test_remote_sync.py::TestSyncCommandLanes::test_pull_refreshes_espanso_output_after_remote_pull tests/test_remote_sync.py::TestSyncCommandLanes::test_top_level_help_lists_source_of_truth_lanes tests/test_completions.py::test_bash_script_contains_subcommands` before and after implementation; `black espansr/__main__.py tests/test_remote_sync.py tests/test_completions.py`; `pytest tests/test_remote_sync.py tests/test_completions.py tests/test_sync_bundled.py tests/test_commands_popup.py tests/test_launcher.py`; `ruff check espansr/__main__.py espansr/core/remote.py espansr/core/config.py espansr/core/completions.py espansr/core/templates.py espansr/core/command_catalog.py espansr/integrations/espanso.py espansr/ui/commands_popup.py tests/test_remote_sync.py tests/test_completions.py tests/test_sync_bundled.py tests/test_commands_popup.py tests/test_launcher.py tests/test_feature_authoring_sync_baseline.py tests/test_import.py`; editor diagnostics, result: pass, notes: `publish` and `starters` lanes added, `pull` now refreshes Espanso output, legacy `sync`/`sync-down`/`sync-bundled` aliases remain, and completions include the public command lanes
- 2026-05-05 T-7 - commands run: `grep`/workspace search for stale `sync-bundled`, `sync-down`, `espansr sync`, and old trigger names across docs, README, and quick help; `pytest tests/test_sync_bundled.py::test_bundled_quick_help_uses_renamed_triggers tests/test_sync_bundled.py::test_bundled_prompt_taxonomy_and_renamed_triggers tests/test_completions.py tests/test_remote_sync.py::TestSyncCommandLanes`; editor diagnostics, result: pass, notes: CLI reference, README, template docs, verification guide, and `:espansr` quick help now present `publish`, `pull`, `push`, `starters`, and `remote` as the primary lanes while documenting legacy aliases intentionally
- 2026-05-05 T-8 - commands run: `pytest`; `ruff check .`; `git diff --check`; `black --check .`; `black --check espansr/__main__.py espansr/core/templates.py espansr/core/command_catalog.py espansr/integrations/espanso.py espansr/ui/commands_popup.py tests/test_feature_authoring_sync_baseline.py tests/test_import.py tests/test_sync_bundled.py tests/test_commands_popup.py tests/test_remote_sync.py tests/test_completions.py`; `git diff -- tests/conftest.py`; `git status --short`; `git diff --stat`; editor diagnostics, result: pass with one unrelated known formatting note, notes: full pytest passed 441 tests after the inline context footer contract was added, full ruff passed, diff whitespace check passed, changed Python files passed Black check, full Black check would reformat untouched `tests/conftest.py`, and native-Windows workflow lint was skipped because Bash verification is not required for this feature
- 2026-05-05 review-bot fixes - commands run: `pytest tests/test_sync_bundled.py::test_sync_bundled_apply_retires_old_starter_when_new_exists tests/test_sync_bundled.py::test_sync_to_espanso_invalid_bundled_hint_uses_starters_command tests/test_setup.py::test_setup_warns_when_initial_sync_fails tests/test_dry_run.py::test_setup_dry_run_with_espanso_uses_publish_language`; `ruff check espansr/core/templates.py espansr/__main__.py espansr/integrations/espanso.py espansr/ui/main_window.py tests/test_sync_bundled.py tests/test_setup.py tests/test_dry_run.py`; `pytest`; `ruff check .`; `git diff --check`; `black --check espansr/__main__.py espansr/core/templates.py espansr/core/command_catalog.py espansr/integrations/espanso.py espansr/ui/commands_popup.py espansr/ui/main_window.py tests/test_feature_authoring_sync_baseline.py tests/test_import.py tests/test_sync_bundled.py tests/test_commands_popup.py tests/test_remote_sync.py tests/test_completions.py tests/test_setup.py tests/test_dry_run.py`, result: pass, notes: review-bot findings fixed by retiring old renamed starter files even when new files already exist, refreshing runtime guidance to `publish`/`starters`, and adding regression coverage; full pytest passed 444 tests

## Session Log

| Date | Last Completed | Next Action | Blockers | State Link |
|------|---------------|-------------|----------|------------|
| 2026-05-05 | T-8 complete | Feature ready for review phase | None | [workflow/STATE.json](../workflow/STATE.json) |
