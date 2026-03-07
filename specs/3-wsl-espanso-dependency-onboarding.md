# Feature Specification: WSL Espanso Dependency Onboarding

## What and Why

`install.sh` installs `espansr` only; it does not install Espanso itself. In WSL this frequently leaves users in a partially-ready state where espansr is installed but Espanso is missing (or not initialized on the Windows side), causing setup/sync confusion. This feature adds explicit dependency onboarding and guided remediation for WSL so users can complete end-to-end setup without guessing.

**Constitution mapping:** `.specify/constitution.md` -> Core Capability #3, #4

## User Stories

1. As a WSL user, I want install/setup to clearly tell me whether Espanso itself is installed and initialized on Windows.
2. As a user with missing Espanso dependency, I want actionable one-command guidance (copy/paste ready) instead of generic "not found" output.
3. As a user with both Linux and Windows candidates, I want onboarding checks to surface conflicts and tell me what canonical path will be used for sync.

## Acceptance Criteria

- [ ] **AC-1:** Installer reports dependency boundary explicitly
  - EARS: When `install.sh` finishes on WSL and Espanso is unavailable, the installer shall explicitly state that Espanso is an external dependency not installed by espansr.
  - GWT: Given WSL and no detectable Espanso config/binary, when `./install.sh` runs, then output includes a dependency explanation and concrete next steps for Windows-side install/init.
  - Verification: `pytest -q tests/test_setup.py -k "wsl2 guidance"` passes

- [ ] **AC-2:** Guided remediation command output is actionable
  - EARS: When Espanso is missing on WSL, the system shall emit copy/paste-ready remediation commands for PowerShell.
  - GWT: Given WSL and missing Espanso, when `espansr setup` or `espansr doctor` runs, then output includes install/init commands (e.g., install + `espanso start`) and a recheck command.
  - Verification: `pytest -q tests/test_doctor.py -k "wsl and espanso"` passes

- [ ] **AC-3:** Conflict-aware readiness check before sync
  - EARS: While multiple candidate Espanso paths exist, when readiness checks run, the system shall report canonical selection and any non-canonical conflict risk.
  - GWT: Given both Linux and Windows candidate paths in WSL, when `espansr doctor` runs, then it reports chosen canonical path, flags conflict scenarios, and recommends cleanup/retry flow.
  - Verification: `pytest -q tests/test_path_consolidation.py -k "canonical or conflict"` passes

- [ ] **AC-4:** Docs reflect external dependency and WSL workflow
  - EARS: When verification/install docs are viewed, they shall state that espansr does not bundle Espanso and include WSL-specific onboarding.
  - GWT: Given a new WSL user reading docs, when they follow install/verify steps, then they can install Espanso on Windows, initialize it, and re-run checks successfully.
  - Verification: `pytest -q tests/test_doctor.py tests/test_setup.py` passes and docs update reviewed

## Non-Goals

- Not: Silently auto-installing Windows software from WSL without explicit user action.
- Not: Replacing Espanso package management for every OS/distribution.

## Constraints

- Performance: Readiness checks must remain fast and avoid expensive shell calls on every command.
- Security: Any suggested install commands must be explicit and never auto-executed without consent.
- Compatibility: Existing Linux/macOS/native Windows setup behavior must not regress.

## Technical Approach

Filled during Phase 4 (Scaffold Project).

## Execution Linkage

Execution planning is authoritative in `/tasks/3-wsl-espanso-dependency-onboarding.md`.

- Task ordering: defined in the matching task file
- Model assignment: defined per task in the task file
- Branch naming: defined per task in the task file
