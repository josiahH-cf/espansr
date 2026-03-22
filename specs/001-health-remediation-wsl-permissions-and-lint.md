# Feature Specification: Health Remediation WSL Permission Handling and Lint Cleanup

> Use this template for every feature spec. Copy to `/specs/[feature-id]-[slug].md` and fill in all sections.

## What and Why

R found one confirmed espansr product defect and one concrete lint drift set in the March 9, 2026 health snapshot. In WSL, `clean_stale_espanso_files()` can raise `PermissionError` while probing non-canonical Windows-side Espanso paths, which breaks both sync flows and GUI startup; the same snapshot also identified named `ruff` violations that should be removed without expanding scope into connector or git-state work.

**Constitution mapping:** Links to `.specify/constitution.md` -> Core Capability #3, #4

## User Stories

1. As a WSL user, I want sync and GUI startup to survive inaccessible Espanso candidate directories so that espansr remains usable even when some Windows paths cannot be probed.
2. As a developer, I want stale cleanup to treat permission-denied non-canonical paths as non-fatal so that accessible managed files are still handled correctly.
3. As a contributor, I want the reported `ruff` violations removed so that lint failures represent new regressions instead of known drift.

## Acceptance Criteria

- [ ] **AC-1:** _WSL-safe stale cleanup during sync_
  - EARS: When stale Espanso cleanup encounters a non-canonical match directory that cannot be stat'ed or read in WSL, the system shall skip that path and continue sync without raising `PermissionError`.
  - GWT: Given a writable canonical test match directory and an inaccessible `/mnt/c/.../espanso/match` candidate, when `sync_to_espanso()` runs, then sync succeeds and produces expected output without crashing.
  - Verification: `pytest -q tests/test_espanso.py -k "sync_produces_valid_yaml_v2_match_file or sync_form_variable_uses_espanso_v2_placeholder or sync_succeeds_with_no_triggered_templates"` passes

- [ ] **AC-2:** _WSL-safe stale cleanup during GUI startup_
  - EARS: When GUI startup triggers stale cleanup and an inaccessible candidate path is present, the system shall continue launching the window and only treat the inaccessible path as a non-fatal condition.
  - GWT: Given WSL and an inaccessible non-canonical Espanso candidate, when `MainWindow()` initializes, then startup completes without `PermissionError`.
  - Verification: `pytest -q tests/test_import.py -k "gui_import_button_exists"` passes

- [ ] **AC-3:** _Reported lint drift removed_
  - EARS: When the project lint command runs after remediation, it shall pass without the reported `I001`, `E501`, and `F401` findings from the health snapshot.
  - GWT: Given the current espansr tree, when `ruff check .` runs, then the import-order, line-length, and unused-import violations called out by R are gone.
  - Verification: `ruff check .` passes

## Non-Goals

- Not: Reworking espansr's orchestratr connector or manifest-generation flow.
- Not: Turning clean or dirty git state into an espansr remediation task.

## Constraints

- Performance: Stale cleanup must stay lightweight across candidate path scanning.
- Security: Cleanup must not expand deletion scope beyond the existing managed-file set.
- Compatibility: Existing sync output and cross-platform path selection semantics must remain unchanged outside the inaccessible-path guard.

## Technical Approach

## Execution Linkage

_Execution planning is authoritative in `/tasks/001-health-remediation-wsl-permissions-and-lint.md`._

- Task ordering: defined in the matching task file
- Model assignment: defined per task in the task file
- Branch naming: defined per task in the task file
