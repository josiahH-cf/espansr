# Tasks: 001-health-remediation-wsl-permissions-and-lint

**Feature ID:** 001-health-remediation-wsl-permissions-and-lint
**Spec:** /specs/001-health-remediation-wsl-permissions-and-lint.md

## Status

- Total: 3
- Complete: 3
- Remaining: 0
- Blocked: 0

## Pre-Implementation Tests

| AC | Test File | Status |
|----|-----------|--------|
| AC-1 | tests/test_espanso.py::test_sync_succeeds_with_no_triggered_templates | [x] Covered |
| AC-2 | tests/test_import.py::test_gui_import_button_exists | [x] Covered |
| AC-3 | ruff check . | [x] Covered |

## Tasks

### T-1: Guard WSL stale cleanup path probing

- **Files:** espansr/integrations/espanso.py, espansr/core/platform.py, tests/test_launcher.py, tests/test_path_consolidation.py
- **Test File:** tests/test_espanso.py
- **Done when:** Non-canonical inaccessible Espanso paths are skipped without breaking sync or launcher generation behavior.
- **Criteria covered:** AC-1, AC-2
- **Branch:** copilot/chore-worktree-sync
- **Status:** [x] Complete

### T-2: Refresh generated launcher behavior

- **Files:** espansr/integrations/espanso.py, tests/test_launcher.py
- **Test File:** tests/test_launcher.py
- **Done when:** Generated launcher commands match the Windows-hosted WSL execution model used by the active Espanso config.
- **Criteria covered:** AC-1, AC-2
- **Branch:** copilot/chore-worktree-sync
- **Status:** [x] Complete

### T-3: Remove current lint drift and workflow hygiene issues

- **Files:** .gitignore, scripts/workflow-lint.sh, workflow/ORCHESTRATOR.md, workflow/LIFECYCLE.md, meta-prompts/admin/update-workflow.md, .github/prompts/update-workflow.prompt.md, .claude/commands/update-workflow.md
- **Test File:** workflow/LINT_REPORT.md
- **Done when:** The current health-remediation changes no longer leak local artifacts into workflow lint and the workflow docs remain internally consistent.
- **Criteria covered:** AC-3
- **Branch:** copilot/chore-worktree-sync
- **Status:** [x] Complete

## Routing Plan

| Task | Suggested Model | Rationale | Reviewer | Parallel? | Context Needs |
|------|-----------------|-----------|----------|-----------|---------------|
| T-1 | claude | Multi-file platform and WSL path behavior required careful diagnosis | copilot | no - foundational behavior change | medium |
| T-2 | copilot | Launcher generation and regression coverage were localized and iterative | claude | no - depends on T-1 behavior | medium |
| T-3 | codex | Workflow lint and control-plane cleanup are deterministic artifact updates | claude | yes - after behavior stabilized | medium |

## Test Strategy

- AC-1: tests/test_espanso.py coverage plus full `pytest`
- AC-2: tests/test_import.py coverage plus live launcher regeneration via `python -m espansr setup`
- AC-3: `ruff check .` and `scripts/workflow-lint.sh`

## Evidence Log

- [2026-03-22] T-1 - commands run: `.venv/bin/pytest`, result: pass (377 passed), notes: WSL stale cleanup and platform regressions verified in the full suite.
- [2026-03-22] T-2 - commands run: `.venv/bin/python -m espansr setup`, result: pass, notes: regenerated the live Windows-side launcher config with the PowerShell-safe WSL command.
- [2026-03-22] T-3 - commands run: `.venv/bin/ruff check .`, `scripts/workflow-lint.sh`, result: pass/advisory, notes: local build artifacts are excluded from workflow lint and workflow-doc contract mismatches were resolved.

## Session Log

| Date | Last Completed | Next Action | Blockers | State Link |
|------|---------------|-------------|----------|------------|
| 2026-03-22 | plan created | validate launcher fix and workflow hygiene updates | none | [workflow/STATE.json](../workflow/STATE.json) |
| 2026-03-22 | T-3 | run final review and ship from branch | none | [workflow/STATE.json](../workflow/STATE.json) |
| 2026-03-22 | review state aligned | commit and push branch for merge | none | [workflow/STATE.json](../workflow/STATE.json) |
| 2026-03-22 | stale findings cleared | finalize commit and push for merge | none | [workflow/STATE.json](../workflow/STATE.json) |