# Feature: 7-template-workflow-sync-redesign

**Feature ID:** 7-template-workflow-sync-redesign

## Description

Redesign espansr's bundled prompt library and sync command surface so the product behaves like a coherent workflow system instead of a flat collection of prompts and overlapping sync commands. This includes direct bundled trigger renames, prompt chain metadata, refreshed help surfaces, and a clearer source-of-truth model for live templates, remote sync, starter templates, and Espanso output publishing.

## Acceptance Criteria

- [ ] **AC-1:** GIVEN a template JSON file includes workflow metadata fields, WHEN it is loaded, saved, versioned, or imported through espansr, THEN supported metadata is preserved while unrelated unknown fields continue to be stripped.
- [ ] **AC-2:** GIVEN the bundled starter prompts are installed or reconciled, WHEN the new taxonomy is applied, THEN renamed triggers, display names, descriptions, categories, and chain metadata are present and old bundled trigger names are handled by an explicit migration contract.
- [ ] **AC-3:** GIVEN a user wants a repeatable AI-assisted workflow, WHEN they inspect the bundled prompts through quick help, the commands popup, docs, or template metadata, THEN the intended chain from goal clarification through project setup, feature execution, verification, documentation QA, and state save is discoverable without relying on chat memory.
- [ ] **AC-4:** GIVEN `:espansr`, `:coms`, CLI help, README examples, and template docs are generated or maintained, WHEN the command and trigger surface changes, THEN those help surfaces remain consistent with the parser, bundled templates, and generated triggers.
- [ ] **AC-5:** GIVEN a user manages local, remote, starter, and Espanso output state, WHEN they use the redesigned CLI, THEN the daily commands communicate distinct source-of-truth lanes for publishing local templates, pulling and publishing remote templates, pushing local templates, and managing bundled starters.
- [ ] **AC-6:** GIVEN an old bundled starter file or trigger is replaced by a renamed bundled template, WHEN starter migration runs, THEN user-modified local templates are preserved or reported, bundled-matching templates are backed up before replacement/removal, and trigger collisions are detected before Espanso output is written.
- [ ] **AC-7:** GIVEN the redesign is complete, WHEN focused and full verification run, THEN schema, import, bundled migration, popup catalog, CLI/completion, remote sync, and documentation behavior are covered by tests or explicitly documented verification.

## Affected Areas

- `templates/*.json`
- `templates/espansr_help.json`
- `espansr/core/templates.py`
- `espansr/core/command_catalog.py`
- `espansr/ui/commands_popup.py`
- `espansr/integrations/espanso.py`
- `espansr/__main__.py`
- `espansr/core/remote.py`
- `espansr/core/config.py`
- `docs/CLI.md`
- `docs/TEMPLATES.md`
- `docs/VERIFY.md`
- `README.md`
- `tests/test_sync_bundled.py`
- `tests/test_commands_popup.py`
- `tests/test_launcher.py`
- `tests/test_remote_sync.py`
- `tests/test_completions.py`
- `tests/test_feature_authoring_sync_baseline.py`
- `tests/test_import.py`

## Constraints

- Preserve user-authored live templates during starter migration.
- Treat direct trigger and command renames as a breaking product change with explicit documentation.
- Keep remote Git credentials and authentication delegated to Git; do not add credential storage.
- Keep generated Espanso YAML as output, not the template source of truth.
- Preserve current local-only template behavior unless a file is explicitly identified as an old bundled starter under the migration contract.
- Do not require Bash verification on native Windows.

## Out of Scope

- Cloud-specific sync APIs beyond the existing Git remote model.
- Editing user live config stores directly during repository development.
- Rebuilding the full GUI editor outside command discovery and pull/publish surface changes.
- Adding a large project-management system beyond prompt chain metadata and existing workflow files.

## Dependencies

- Existing `Template`, `TemplateManager`, bundled drift, remote sync, command catalog, and Espanso integration behavior.
- Git CLI for remote sync operations.
- Existing PyQt6 popup surface for `:coms`.

## Test Planning Intent

**Test approach:** Unit tests for metadata round-tripping, import stripping, catalog grouping, parser/completion changes, and bundled migration; integration-style tests for remote pull/publish behavior and starter migration safety; documentation verification through targeted assertions where practical.

**Rough test scenarios:**
- [ ] Metadata fields survive template load/save/import/version paths while unrelated fields are stripped.
- [ ] Renamed bundled templates expose the new triggers and categories.
- [ ] Starter migration backs up or preserves old bundled templates according to the migration contract.
- [ ] `:coms` and `:espansr` display the redesigned trigger and command surface without stale names.
- [ ] `publish`, redesigned `pull`, `push`, and starter commands behave according to their source-of-truth lane.
- [ ] Docs and README examples use the new command model.

## Verification Map

| AC | Test File | Test Function | Assertion |
|----|-----------|---------------|-----------|
| AC-1 | tests/test_feature_authoring_sync_baseline.py | test_template_workflow_metadata_roundtrip | Template metadata survives save/load/version paths |
| AC-1 | tests/test_import.py | test_import_preserves_workflow_metadata | Import preserves supported metadata and strips unknown fields |
| AC-1 | tests/test_import.py | test_import_normalizes_malformed_workflow_metadata | Malformed workflow metadata is normalized before save |
| AC-2 | tests/test_sync_bundled.py | test_bundled_prompt_taxonomy_and_renamed_triggers | Bundled files expose renamed triggers and workflow metadata |
| AC-3 | tests/test_sync_bundled.py | test_bundled_quick_help_uses_renamed_triggers | `:espansr` quick help exposes the redesigned prompt chain without stale trigger names |
| AC-3 | tests/test_commands_popup.py | test_build_command_catalog_exposes_workflow_metadata | Catalog entries expose workflow category, stage, and next-trigger hints |
| AC-3 | tests/test_commands_popup.py | test_commands_popup_dialog_renders_entries | Popup renders workflow metadata in summary and detail rows |
| AC-4 | tests/test_commands_popup.py | test_build_command_catalog_includes_template_and_system_triggers | Catalog still includes template triggers plus generated system triggers |
| AC-4 | docs/CLI.md / docs/TEMPLATES.md / docs/VERIFY.md / README.md / templates/espansr_help.json | documentation review | Public docs and quick help describe publish, pull, push, starters, remote, and generated discovery triggers consistently |
| AC-5 | tests/test_remote_sync.py | TestSyncCommandLanes::test_publish_runs_local_espanso_publish | `publish` publishes local templates without invoking remote auto-pull |
| AC-5 | tests/test_remote_sync.py | TestSyncCommandLanes::test_pull_refreshes_espanso_output_after_remote_pull | `pull` pulls remote templates and refreshes Espanso output |
| AC-5 | tests/test_remote_sync.py | TestSyncCommandLanes::test_top_level_help_lists_source_of_truth_lanes | Top-level help exposes publish, pull, push, starters, and remote lanes |
| AC-5 | tests/test_completions.py | test_bash_script_contains_subcommands / test_zsh_script_contains_subcommands | Shell completions include the redesigned public command lanes and exclude removed legacy aliases |
| AC-6 | tests/test_sync_bundled.py | test_sync_bundled_apply_migrates_renamed_starter_with_backup | Old starter files are backed up before renamed bundled starters replace them |
| AC-6 | tests/test_sync_bundled.py | test_sync_bundled_blocks_renamed_trigger_collision | Renamed starter migration reports trigger collisions before applying changes |
| AC-6 | tests/test_sync_bundled.py | test_sync_to_espanso_blocks_renamed_trigger_collision_before_writing | Espanso YAML is not written when renamed starter migration has trigger collisions |
| AC-7 | Multiple suites and final checks | T-8 verification pass | Full pytest, full ruff, diff whitespace, changed-file Black check, docs/help searches, and editor diagnostics verify the redesigned surface; full Black check only reports an unrelated untouched `tests/conftest.py` formatting mismatch |

## Contracts

- Exposes: optional template metadata fields `category`, `stage`, `next_triggers`, `replaces`, and `deprecated`.
- Exposes: redesigned public command model for publishing, remote pull/push, and starter management.
- Consumes: existing live template store, bundled starter templates, optional Git remote, and generated Espanso output paths.

## Execution Linkage

- Task file: /tasks/7-template-workflow-sync-redesign.md
- Task ordering, model assignment, and branch naming live in the task file.

## Notes

- This feature intentionally prioritizes a cleaner future mental model over perfect backward compatibility.
- If implementation risk grows too large, split delivery into prompt taxonomy/metadata first and sync command redesign second.
