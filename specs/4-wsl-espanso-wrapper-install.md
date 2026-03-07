# Feature Specification: WSL Espanso Wrapper Install + PATH Recovery

## What and Why

WSL users can successfully install Espanso via `winget` in Windows PowerShell but still fail at `espanso start` because the executable is not available in the current shell PATH/session yet. This feature adds a WSL-first wrapper flow that installs Espanso non-interactively, starts it using robust executable discovery, and gives deterministic recovery guidance when PATH propagation lags.

**Constitution mapping:** `.specify/constitution.md` -> Core Capability #3, #4

## User Stories

1. As a WSL user, I want a single espansr command that installs and starts Espanso on Windows from WSL.
2. As a user affected by delayed PATH propagation, I want fallback execution by absolute path and clear next steps when auto-start cannot resolve the binary.
3. As a user onboarding from install/setup output, I want to see this wrapper command as the recommended path instead of manual trial-and-error.

## Acceptance Criteria

- [ ] **AC-1:** Wrapper command exists and is WSL-scoped
  - EARS: When the wrapper command is run outside WSL2, the system shall fail with a clear unsupported-platform message.
  - GWT: Given non-WSL platform, when `espansr wsl-install-espanso` runs, then it exits non-zero and explains WSL-only scope.
  - Verification: `pytest -q tests/test_wsl_install_wrapper.py -k "non_wsl"` passes

- [ ] **AC-2:** Wrapper performs non-interactive install and startup attempt
  - EARS: When run in WSL2, the wrapper shall invoke PowerShell to install Espanso with accepted agreements and attempt startup.
  - GWT: Given WSL2, when wrapper runs, then PowerShell command includes `winget install ... --accept-package-agreements --accept-source-agreements` and executes startup.
  - Verification: `pytest -q tests/test_wsl_install_wrapper.py -k "success"` passes

- [ ] **AC-3:** PATH-lag fallback and recovery guidance
  - EARS: While Espanso is installed but not resolved by command name, the wrapper shall probe known executable locations and surface deterministic recovery steps.
  - GWT: Given install success and `espanso` command unresolved in-session, when wrapper runs, then it tries known paths and if still unresolved prints actionable recovery steps.
  - Verification: `pytest -q tests/test_wsl_install_wrapper.py -k "path or unresolved"` passes

- [ ] **AC-4:** Installer/setup messaging points to wrapper
  - EARS: When WSL Espanso is missing, the system shall recommend wrapper usage in install/setup/status/doctor output.
  - GWT: Given WSL and missing Espanso config, when setup/status/doctor/install smoke output appears, then it includes `espansr wsl-install-espanso` as primary remediation path.
  - Verification: `pytest -q tests/test_setup.py tests/test_doctor.py` passes

## Non-Goals

- Not: Installing Espanso natively on Linux/macOS via this wrapper.
- Not: Modifying Windows user PATH permanently outside installer/provider behavior.

## Constraints

- Security: Wrapper must never auto-run arbitrary scripts; only explicit PowerShell command payload.
- Compatibility: Existing Linux/macOS/native Windows flows remain unchanged.
- UX: Failure output must include exact next commands and expected context (PowerShell vs WSL).

## Technical Approach

Filled during Phase 4 (Scaffold Project).

## Execution Linkage

Execution planning is authoritative in `/tasks/4-wsl-espanso-wrapper-install.md`.

- Task ordering: defined in the matching task file
- Model assignment: defined per task in the task file
- Branch naming: defined per task in the task file
