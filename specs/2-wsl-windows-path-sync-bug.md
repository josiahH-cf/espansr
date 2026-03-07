# Feature Specification: WSL Windows Path + Sync Conflict Fix

## What and Why

This bug feature ensures WSL-to-Windows Espanso path detection consistently selects the canonical Windows install path, handles path conflicts, and keeps sync behavior deterministic. It matters because incorrect path selection causes failed installs, stale files, and confusing split-state sync outcomes.

**Constitution mapping:** `.specify/constitution.md` -> Core Capability #3, #4

## User Stories

1. As a WSL user with Espanso installed on Windows, I want espansr to target the correct Windows config path automatically.
2. As a user with both Linux and Windows candidate paths present, I want conflict handling to preserve one canonical destination and clean stale managed outputs.
3. As a CLI user, I want sync behavior to remain safe and predictable while path selection logic changes.

## Acceptance Criteria

- [ ] **AC-1:** WSL candidate discovery is resilient
  - EARS: When WSL username lookup is unavailable, the system shall still discover Windows user candidate paths.
  - GWT: Given WSL and unavailable `cmd.exe` username resolution, when candidate paths are built, then Windows profile candidates are included.
  - Verification: `pytest -q tests/test_path_consolidation.py -k "falls_back_to_discovered_windows_users"` passes

- [ ] **AC-2:** Canonical path preference resolves conflicts
  - EARS: While both Linux and Windows Espanso paths exist in WSL, when config resolution runs, the system shall prefer Windows-side canonical path and persist it.
  - GWT: Given a persisted Linux config path and an available Windows candidate, when `get_espanso_config_dir()` runs, then the Windows path is selected and saved.
  - Verification: `pytest -q tests/test_path_consolidation.py -k "prefers_windows_candidate_when_wsl_persisted_linux"` passes

- [ ] **AC-3:** Sync cleanup removes stale managed files from non-canonical conflict paths
  - EARS: When canonical path is Windows-side, the system shall remove managed stale files from non-canonical Linux-side match directories.
  - GWT: Given managed files in both Linux and Windows candidate match directories, when stale cleanup runs, then only non-canonical managed files are removed.
  - Verification: `pytest -q tests/test_path_consolidation.py -k "cleans_linux_conflict"` passes

## Non-Goals

- Not: Rewriting Espanso matching semantics.
- Not: Changing user-authored non-managed Espanso files.

## Constraints

- Performance: Candidate discovery should remain lightweight.
- Security: Path discovery and cleanup must not broaden deletion scope beyond managed file names.
- Compatibility: Existing Linux/macOS/native Windows behavior must remain unchanged.

## Technical Approach

Filled during Phase 4 (Scaffold Project).

## Execution Linkage

Execution planning is authoritative in `/tasks/2-wsl-windows-path-sync-bug.md`.

- Task ordering: defined in the matching task file
- Model assignment: defined per task in the task file
- Branch naming: defined per task in the task file
