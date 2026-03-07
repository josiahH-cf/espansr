# Tasks: 3-wsl-espanso-dependency-onboarding

**Feature ID:** 3-wsl-espanso-dependency-onboarding
**Spec:** /specs/3-wsl-espanso-dependency-onboarding.md

## Status

- Total: 3
- Complete: 3
- Remaining: 0
- Blocked: 0

## Pre-Implementation Tests

| AC | Test File | Status |
|----|-----------|--------|
| AC-1 | tests/test_setup.py::test_setup_wsl2_missing_espanso_prints_actionable_remediation | [x] Written |
| AC-2 | tests/test_doctor.py::test_doctor_wsl_missing_espanso_prints_dependency_remediation | [x] Written |
| AC-3 | tests/test_doctor.py::test_doctor_wsl_conflict_reports_non_canonical_candidates | [x] Written |
| AC-4 | docs/VERIFY.md + README.md updates | [x] Updated |

## Task List

### T-1: Add explicit WSL dependency onboarding messages

- **Files:** espansr/__main__.py, install.sh
- **Test File:** tests/test_setup.py
- **Done when:** setup/status/install output clearly states Espanso is external and provides actionable PowerShell steps.
- **Criteria covered:** AC-1, AC-2
- **Branch:** implementer/wsl-dependency-onboarding
- **Status:** [x] Complete

### T-2: Add conflict-aware WSL doctor diagnostics

- **Files:** espansr/__main__.py
- **Test File:** tests/test_doctor.py
- **Done when:** doctor reports canonical path and warns about non-canonical candidate conflicts in WSL.
- **Criteria covered:** AC-3
- **Branch:** implementer/wsl-doctor-conflict-visibility
- **Status:** [x] Complete

### T-3: Update onboarding docs for WSL dependency flow

- **Files:** docs/VERIFY.md, README.md
- **Test File:** tests/test_doctor.py tests/test_setup.py
- **Done when:** docs explicitly describe Windows-host Espanso requirement and re-check flow from WSL.
- **Criteria covered:** AC-4
- **Branch:** reviewer/wsl-onboarding-docs
- **Status:** [x] Complete

## Routing Plan

| Task | Suggested Model | Rationale | Reviewer | Parallel? | Context Needs |
|------|-----------------|-----------|----------|-----------|---------------|
| T-1 | copilot | CLI/installer messaging and onboarding text changes | codex | no - messaging baseline first | small |
| T-2 | claude | doctor behavior and conflict diagnostics in one command surface | copilot | no - depends on onboarding helper output | medium |
| T-3 | codex | docs alignment and verification consistency pass | claude | yes - after code/tests stable | small |

## Test Strategy

- AC-1: tests/test_setup.py::test_setup_wsl2_missing_espanso_prints_actionable_remediation
- AC-2: tests/test_doctor.py::test_doctor_wsl_missing_espanso_prints_dependency_remediation
- AC-3: tests/test_doctor.py::test_doctor_wsl_conflict_reports_non_canonical_candidates
- AC-4: docs review + tests/test_doctor.py tests/test_setup.py

## Evidence Log

- [2026-03-07] T-1/T-2/T-3 - commands run: `pytest -q tests/test_setup.py -k "wsl2 guidance or actionable_remediation"`, `pytest -q tests/test_doctor.py -k "wsl and espanso or non_canonical"`, `pytest -q tests/test_doctor.py tests/test_setup.py`, result: pass, notes: onboarding remediation + conflict diagnostics + docs completed.

## Session Log

| Date | Last Completed | Next Action | Blockers | State Link |
|------|---------------|-------------|----------|------------|
| 2026-03-07 | bugfix + onboarding feature complete | resume Phase 8 maintenance flow | none | [workflow/STATE.json](../workflow/STATE.json) |
