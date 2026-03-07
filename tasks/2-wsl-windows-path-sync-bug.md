# Tasks: 2-wsl-windows-path-sync-bug

**Feature ID:** 2-wsl-windows-path-sync-bug
**Spec:** /specs/2-wsl-windows-path-sync-bug.md

## Status

- Total: 3
- Complete: 3
- Remaining: 0
- Blocked: 0

## Pre-Implementation Tests

| AC | Test File | Status |
|----|-----------|--------|
| AC-1 | tests/test_path_consolidation.py::test_get_candidate_paths_wsl2_falls_back_to_discovered_windows_users | [x] Written |
| AC-2 | tests/test_path_consolidation.py::test_get_espanso_config_dir_prefers_windows_candidate_when_wsl_persisted_linux | [x] Written |
| AC-3 | tests/test_path_consolidation.py::test_clean_stale_uses_windows_canonical_and_cleans_linux_conflict | [x] Written |

## Task List

### T-1: Add WSL fallback discovery + candidate ordering

- **Files:** espansr/core/platform.py, tests/test_path_consolidation.py
- **Test File:** tests/test_path_consolidation.py
- **Done when:** WSL candidate discovery handles username lookup failures and prioritizes Windows Roaming paths.
- **Criteria covered:** AC-1
- **Branch:** implementer/wsl-path-discovery-fallback
- **Status:** [x] Complete

### T-2: Prefer canonical Windows path during config resolution

- **Files:** espansr/integrations/espanso.py, tests/test_path_consolidation.py
- **Test File:** tests/test_path_consolidation.py
- **Done when:** Persisted Linux path is replaced by Windows candidate when appropriate in WSL.
- **Criteria covered:** AC-2
- **Branch:** implementer/wsl-canonical-path-selection
- **Status:** [x] Complete

### T-3: Validate sync conflict cleanup behavior

- **Files:** espansr/integrations/espanso.py, tests/test_path_consolidation.py
- **Test File:** tests/test_path_consolidation.py
- **Done when:** Stale managed files are removed from non-canonical conflict directories.
- **Criteria covered:** AC-3
- **Branch:** reviewer/wsl-sync-conflict-cleanup
- **Status:** [x] Complete

## Routing Plan

| Task | Suggested Model | Rationale | Reviewer | Parallel? | Context Needs |
|------|-----------------|-----------|----------|-----------|---------------|
| T-1 | copilot | Fast targeted path logic + unit tests | codex | no - dependency for canonical selection | small |
| T-2 | claude | Cross-cutting config resolution behavior | copilot | no - depends on T-1 ordering | medium |
| T-3 | codex | Cleanup safety validation in conflict scenarios | claude | yes - after T-2 stabilizes | medium |

## Test Strategy

- AC-1: tests/test_path_consolidation.py::test_get_candidate_paths_wsl2_falls_back_to_discovered_windows_users
- AC-2: tests/test_path_consolidation.py::test_get_espanso_config_dir_prefers_windows_candidate_when_wsl_persisted_linux
- AC-3: tests/test_path_consolidation.py::test_clean_stale_uses_windows_canonical_and_cleans_linux_conflict

## Evidence Log

- [2026-03-07] T-1/T-2/T-3 - commands run: `pytest -q tests/test_path_consolidation.py -k "falls_back_to_discovered_windows_users or prefers_windows_candidate_when_wsl_persisted_linux or cleans_linux_conflict"`, result: pass, notes: WSL Windows path conflict fix implemented and verified.

## Session Log

| Date | Last Completed | Next Action | Blockers | State Link |
|------|---------------|-------------|----------|------------|
| 2026-03-07 | bugfix complete | continue Phase 8 maintenance flow | none | [workflow/STATE.json](../workflow/STATE.json) |
