# Tasks: 4-wsl-espanso-wrapper-install

**Feature ID:** 4-wsl-espanso-wrapper-install
**Spec:** /specs/4-wsl-espanso-wrapper-install.md

## Status

- Total: 3
- Complete: 3
- Remaining: 0
- Blocked: 0

## Pre-Implementation Tests

| AC | Test File | Status |
|----|-----------|--------|
| AC-1 | tests/test_wsl_install_wrapper.py::test_wsl_install_wrapper_fails_outside_wsl | [x] Written |
| AC-2 | tests/test_wsl_install_wrapper.py::test_wsl_install_wrapper_invokes_powershell_with_winget | [x] Written |
| AC-3 | tests/test_wsl_install_wrapper.py::test_wsl_install_wrapper_path_lag_returns_guidance | [x] Written |
| AC-4 | tests/test_setup.py + tests/test_doctor.py onboarding assertions | [x] Updated |

## Task List

### T-1: Implement WSL wrapper command

- **Files:** espansr/__main__.py
- **Test File:** tests/test_wsl_install_wrapper.py
- **Done when:** `espansr wsl-install-espanso` installs/starts Espanso through PowerShell in WSL and handles non-WSL failure.
- **Criteria covered:** AC-1, AC-2, AC-3
- **Branch:** implementer/wsl-wrapper-command
- **Status:** [x] Complete

### T-2: Integrate onboarding guidance with wrapper

- **Files:** espansr/__main__.py, install.sh
- **Test File:** tests/test_setup.py, tests/test_doctor.py
- **Done when:** setup/status/doctor/install guidance points users to wrapper first.
- **Criteria covered:** AC-4
- **Branch:** implementer/wsl-wrapper-onboarding
- **Status:** [x] Complete

### T-3: Completion/doc alignment

- **Files:** tests/test_completions.py, docs/VERIFY.md, README.md
- **Test File:** tests/test_completions.py
- **Done when:** command appears in completion output and docs mention wrapper path.
- **Criteria covered:** AC-4
- **Branch:** reviewer/wsl-wrapper-alignment
- **Status:** [x] Complete

## Routing Plan

| Task | Suggested Model | Rationale | Reviewer | Parallel? | Context Needs |
|------|-----------------|-----------|----------|-----------|---------------|
| T-1 | copilot | CLI wrapper logic and subprocess contract | codex | no - core implementation | medium |
| T-2 | claude | messaging integration across installer and doctor/setup | copilot | no - depends on wrapper command | medium |
| T-3 | codex | completion/doc consistency pass | claude | yes - after command lands | small |

## Test Strategy

- AC-1: tests/test_wsl_install_wrapper.py::test_wsl_install_wrapper_fails_outside_wsl
- AC-2: tests/test_wsl_install_wrapper.py::test_wsl_install_wrapper_invokes_powershell_with_winget
- AC-3: tests/test_wsl_install_wrapper.py::test_wsl_install_wrapper_path_lag_returns_guidance
- AC-4: tests/test_setup.py, tests/test_doctor.py, tests/test_completions.py

## Evidence Log

- [2026-03-07] T-1/T-2/T-3 - commands run: `pytest -q tests/test_wsl_install_wrapper.py`, `pytest -q tests/test_doctor.py tests/test_setup.py tests/test_completions.py`, result: pass, notes: wrapper command and onboarding integration complete.

## Session Log

| Date | Last Completed | Next Action | Blockers | State Link |
|------|---------------|-------------|----------|------------|
| 2026-03-07 | wrapper feature complete | merge/push then resume Phase 8 maintenance | none | [workflow/STATE.json](../workflow/STATE.json) |
