# Feature Specification: Authoring + Sync Baseline Flow

## What and Why

This feature establishes a baseline workflow for creating/editing Espanso command templates and syncing them safely from both GUI and CLI surfaces. It matters because fast authoring with predictable validation and sync behavior is the core value promised by the constitution.

**Constitution mapping:** `.specify/constitution.md` -> Core Capability #1, #2, #3, #4

## User Stories

1. As a developer, I want to author and edit template commands in the GUI so that I do not hand-edit raw Espanso YAML.
2. As a CLI-first user, I want validation and dry-run sync commands so that I can automate safely.
3. As a cross-platform user, I want setup/sync behavior to work consistently in Windows/WSL/Linux/macOS contexts.

## Acceptance Criteria

- [ ] **AC-1:** GUI command editing roundtrip
  - EARS: When a user edits a template command in the GUI, the system shall persist the template and keep preview output consistent.
  - GWT: Given an existing template, when the user edits trigger/content/variables in the editor and saves, then the updated template is stored and preview reflects the same values.
  - Verification: `pytest tests/test_gui_editor.py -k "editor or variable"` passes

- [ ] **AC-2:** CLI safe sync pipeline
  - EARS: When a user invokes validation or dry-run sync, the system shall report issues without mutating Espanso files.
  - GWT: Given templates with valid and invalid cases, when the user runs validate and dry-run sync, then warnings/errors are reported and no write occurs in dry-run mode.
  - Verification: `pytest tests/test_validate.py tests/test_dry_run.py` passes

- [ ] **AC-3:** Platform-aware setup and status
  - EARS: While running on supported platforms, when setup/status commands are executed, the system shall detect platform-specific paths and report actionable state.
  - GWT: Given Windows/WSL/Linux/macOS path conditions, when setup/status flows run, then platform handling and messaging are correct for each environment.
  - Verification: `pytest tests/test_platform.py tests/test_setup.py tests/test_status_bar.py` passes

## Non-Goals

- Not: Replacing Espanso runtime behavior or implementing a new expansion engine.
- Not: Expanding into unrelated orchestration features outside template authoring/sync.

## Constraints

- Performance: Common authoring, validation, and sync paths should remain responsive for local developer workflows.
- Security: Validate input and preserve path safety for local filesystem operations.
- Compatibility: Maintain behavior on Windows, WSL, Linux, and macOS without regressions.

## Technical Approach

Filled during Phase 4 (Scaffold Project).

## Execution Linkage

Execution planning is authoritative in `/tasks/1-authoring-sync-baseline.md`.

- Task ordering: defined in the matching task file
- Model assignment: defined per task in the task file
- Branch naming: defined per task in the task file
