# Tasks: 1-authoring-sync-baseline

**Feature ID:** 1-authoring-sync-baseline
**Spec:** /specs/1-authoring-sync-baseline.md

## Status

- Total: 3
- Complete: 3
- Remaining: 0
- Blocked: 0

## Pre-Implementation Tests

| AC | Test File | Status |
|----|-----------|--------|
| AC-1 | tests/test_feature_authoring_sync_baseline.py::test_gui_editor_roundtrip_persists_and_previews | [x] Written (failing as expected) |
| AC-2 | tests/test_feature_authoring_sync_baseline.py::test_cli_validate_and_dry_run_do_not_mutate_outputs | [x] Written (failing as expected) |
| AC-3 | tests/test_feature_authoring_sync_baseline.py::test_setup_and_status_are_platform_aware | [x] Written (failing as expected) |

## Tasks

### T-1: Define pre-implementation failing tests

- **Files:** tests/test_feature_authoring_sync_baseline.py
- **Test File:** tests/test_feature_authoring_sync_baseline.py
- **Done when:** Failing tests exist for AC-1, AC-2, and AC-3 with clear expected outcomes.
- **Criteria covered:** AC-1, AC-2, AC-3
- **Branch:** copilot/test-authoring-sync-pretests
- **Status:** [x] Complete

### T-2: Implement GUI and CLI behavior for criteria

- **Files:** espansr/ui/main_window.py, espansr/core/templates.py, espansr/integrations/espanso.py, espansr/integrations/validate.py
- **Test File:** tests/test_feature_authoring_sync_baseline.py
- **Done when:** All AC behavior is implemented and pre-tests are green.
- **Criteria covered:** AC-1, AC-2
- **Branch:** implementer/feature-authoring-sync-impl
- **Status:** [x] Complete

### T-3: Verify platform handling and regression coverage

- **Files:** espansr/core/platform.py, espansr/__main__.py, tests/test_platform.py, tests/test_setup.py
- **Test File:** tests/test_feature_authoring_sync_baseline.py
- **Done when:** Platform behavior is validated and regressions are covered by tests.
- **Criteria covered:** AC-3
- **Branch:** reviewer/platform-verification-pass
- **Status:** [x] Complete

## Routing Plan

| Task | Suggested Model | Rationale | Reviewer | Parallel? | Context Needs |
|------|-----------------|-----------|----------|-----------|---------------|
| T-1 | copilot | Fast test scaffolding and criterion mapping | codex | no - establishes baseline tests first | small |
| T-2 | claude | Multi-file behavior implementation across GUI/CLI/integrations | copilot | no - depends on T-1 failing tests | large |
| T-3 | codex | Cross-file verification and platform regression review | claude | yes - after T-2 code stabilizes | medium |

## Test Strategy

- AC-1: tests/test_feature_authoring_sync_baseline.py::test_gui_editor_roundtrip_persists_and_previews
- AC-2: tests/test_feature_authoring_sync_baseline.py::test_cli_validate_and_dry_run_do_not_mutate_outputs
- AC-3: tests/test_feature_authoring_sync_baseline.py::test_setup_and_status_are_platform_aware

## Evidence Log

- [2026-03-07] T-plan - commands run: state bootstrap checks, result: pass, notes: feature spec and task plan created.
- [2026-03-07] T-1 - commands run: `pytest -q tests/test_feature_authoring_sync_baseline.py`, result: expected fail (3 failing tests), notes: pre-implementation tests now exist for AC-1..AC-3.
- [2026-03-07] T-2 - commands run: `pytest -q tests/test_feature_authoring_sync_baseline.py`, result: pass (3 passed), notes: implemented concrete AC behavior checks for persistence, validation, and dry-run safety.
- [2026-03-07] T-3 - commands run: `pytest -q`, result: pass (360 passed), notes: no regressions; platform/setup/status verification completed.
- [2026-03-07] test-post - commands run: `pytest -q tests/test_gui_editor.py -k "editor or variable"`, `pytest -q tests/test_validate.py tests/test_dry_run.py`, `pytest -q tests/test_platform.py tests/test_setup.py tests/test_status_bar.py`, result: pass, notes: AC verification commands from spec all passed.

## Session Log

| Date | Last Completed | Next Action | Blockers | State Link |
|------|---------------|-------------|----------|------------|
| 2026-03-07 | plan created | run /test pre for 1-authoring-sync-baseline | none | [workflow/STATE.json](../workflow/STATE.json) |
| 2026-03-07 | T-1 | run /implement for T-2 and T-3 to satisfy AC-1..AC-3 | none | [workflow/STATE.json](../workflow/STATE.json) |
| 2026-03-07 | T-3 | run /test post and advance to review-ship | none | [workflow/STATE.json](../workflow/STATE.json) |
| 2026-03-07 | test post pass | complete review-ship checks and move to maintain | none | [workflow/STATE.json](../workflow/STATE.json) |
| 2026-03-08 | Phase 8 maintain pass (standard) | run /operationalize interview and generate automation config/workflows | human input required: automation preferences | [workflow/STATE.json](../workflow/STATE.json) |
| 2026-03-08 | Phase 9 interview complete | validate generated maintenance workflows and continue in re-enterable operationalize mode | none | [workflow/STATE.json](../workflow/STATE.json) |
