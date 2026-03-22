# Workflow Lint Report

- **Generated:** 2026-03-22T11:30:46Z
- **Project root:** `/home/josiah/R/espansr`
- **Files scanned:** 197
- **Total findings:** 157

## Summary

| Category | Count |
|----------|-------|
| Orphan | 2 |
| Length | 6 |
| EOF Newline | 9 |
| Clarity | 140 |

## Orphan Detection

| File | Line | Message |
|------|------|---------|
| `tasks/archive/espansr-orchestratr-connector.md` | — | No inbound reference found |
| `decisions/0001-platform-config-single-source.md` | — | No inbound reference found |

## Length Warnings

| File | Line | Message |
|------|------|---------|
| `specs/archive/install-first-run.md` | — | **282** lines (threshold: 120) |
| `specs/archive/manifest-schema-alignment.md` | — | **166** lines (threshold: 120) |
| `tasks/archive/install-first-run.md` | — | **166** lines (threshold: 120) |
| `tasks/archive/roadmap-v1.0.md` | — | **254** lines (threshold: 120) |
| `workflow/LINT_REPORT.md` | — | **195** lines (threshold: 120) |
| `workflow/ORCHESTRATOR.md` | — | **148** lines (threshold: 120) |

## EOF Newline

| File | Line | Message |
|------|------|---------|
| `./governance/REGISTRY.md` | EOF | Multiple trailing newlines |
| `./meta-prompts/phase-4-scaffold-project.md` | EOF | Multiple trailing newlines |
| `./meta-prompts/phase-4-scaffold.md` | EOF | Multiple trailing newlines |
| `./tasks/001-health-remediation-wsl-permissions-and-lint.md` | EOF | Missing trailing newline |
| `./tasks/archive/cli-colored-output.md` | EOF | Multiple trailing newlines |
| `./tasks/archive/gui-dark-mode.md` | EOF | Multiple trailing newlines |
| `./tasks/archive/gui-status-bar-feedback.md` | EOF | Multiple trailing newlines |
| `./tasks/archive/gui-template-preview.md` | EOF | Multiple trailing newlines |
| `./tasks/archive/setup-platform-resilience.md` | EOF | Multiple trailing newlines |

## Clarity Heuristics

| File | Line | Message |
|------|------|---------|
| `specs/001-health-remediation-wsl-permissions-and-lint.md` | 7 | Line exceeds 200 characters (421 chars) |
| `specs/001-health-remediation-wsl-permissions-and-lint.md` | 20 | Line exceeds 200 characters (203 chars) |
| `specs/001-health-remediation-wsl-permissions-and-lint.md` | 21 | Line exceeds 200 characters (211 chars) |
| `specs/001-health-remediation-wsl-permissions-and-lint.md` | 25 | Line exceeds 200 characters (206 chars) |
| `specs/1-authoring-sync-baseline.md` | 5 | Line exceeds 200 characters (275 chars) |
| `specs/2-wsl-windows-path-sync-bug.md` | 5 | Line exceeds 200 characters (304 chars) |
| `specs/3-wsl-espanso-dependency-onboarding.md` | 5 | Line exceeds 200 characters (395 chars) |
| `specs/4-wsl-espanso-wrapper-install.md` | 5 | Line exceeds 200 characters (389 chars) |
| `specs/archive/cli-colored-output.md` | 7 | Line exceeds 200 characters (222 chars) |
| `specs/archive/cli-doctor.md` | 7 | Line exceeds 200 characters (303 chars) |
| `specs/archive/cli-doctor.md` | 13 | Line exceeds 200 characters (201 chars) |
| `specs/archive/cli-dry-run-verbose.md` | 9 | Line exceeds 200 characters (204 chars) |
| `specs/archive/cli-dry-run-verbose.md` | 45 | Line exceeds 200 characters (228 chars) |
| `specs/archive/cli-tab-completion.md` | 7 | Line exceeds 200 characters (271 chars) |
| `specs/archive/espanso-config-validation.md` | 8 | Line exceeds 200 characters (443 chars) |
| `specs/archive/espanso-config-validation.md` | 12 | Line exceeds 200 characters (215 chars) |
| `specs/archive/espanso-config-validation.md` | 13 | Line exceeds 200 characters (315 chars) |
| `specs/archive/espanso-launcher-trigger.md` | 8 | Line exceeds 200 characters (378 chars) |
| `specs/archive/espanso-path-consolidation.md` | 8 | Line exceeds 200 characters (340 chars) |
| `specs/archive/espanso-path-consolidation.md` | 13 | Line exceeds 200 characters (208 chars) |
| `specs/archive/espansr-orchestratr-connector.md` | 8 | Line exceeds 200 characters (423 chars) |
| `specs/archive/espansr-orchestratr-connector.md` | 15 | Line exceeds 200 characters (224 chars) |
| `specs/archive/first-public-release.md` | 7 | Line exceeds 200 characters (362 chars) |
| `specs/archive/gui-dark-mode.md` | 7 | TODO/FIXME: Detect the operating system's color scheme preference and apply the matching the |
| `specs/archive/gui-dark-mode.md` | 53 | TODO/FIXME: /* TODO: Complete light theme */ |
| `specs/archive/gui-dark-mode.md` | 7 | Line exceeds 200 characters (325 chars) |
| `specs/archive/gui-keyboard-shortcuts.md` | 53 | Line exceeds 200 characters (313 chars) |
| `specs/archive/gui-single-screen.md` | 44 | TODO/FIXME: - Light theme completion (`theme.py` TODO) |
| `specs/archive/gui-single-screen.md` | 8 | Line exceeds 200 characters (378 chars) |
| `specs/archive/gui-status-bar-feedback.md` | 9 | Line exceeds 200 characters (308 chars) |
| `specs/archive/gui-status-bar-feedback.md` | 11 | Line exceeds 200 characters (273 chars) |
| `specs/archive/gui-status-bar-feedback.md` | 49 | Line exceeds 200 characters (266 chars) |
| `specs/archive/gui-template-preview.md` | 7 | Line exceeds 200 characters (239 chars) |
| `specs/archive/gui-template-preview.md` | 50 | Line exceeds 200 characters (276 chars) |
| `specs/archive/install-first-run.md` | 9 | Line exceeds 200 characters (444 chars) |
| `specs/archive/install-first-run.md` | 11 | Line exceeds 200 characters (502 chars) |
| `specs/archive/install-first-run.md` | 13 | Line exceeds 200 characters (301 chars) |
| `specs/archive/install-first-run.md` | 15 | Line exceeds 200 characters (398 chars) |
| `specs/archive/install-first-run.md` | 17 | Line exceeds 200 characters (301 chars) |
| `specs/archive/install-first-run.md` | 21 | Line exceeds 200 characters (322 chars) |
| `specs/archive/install-first-run.md` | 23 | Line exceeds 200 characters (272 chars) |
| `specs/archive/install-first-run.md` | 99 | Line exceeds 200 characters (238 chars) |
| `specs/archive/install-first-run.md` | 103 | Line exceeds 200 characters (244 chars) |
| `specs/archive/install-first-run.md` | 106 | Line exceeds 200 characters (208 chars) |
| `specs/archive/install-first-run.md` | 107 | Line exceeds 200 characters (285 chars) |
| `specs/archive/install-first-run.md` | 108 | Line exceeds 200 characters (204 chars) |
| `specs/archive/install-first-run.md` | 113 | Line exceeds 200 characters (222 chars) |
| `specs/archive/install-first-run.md` | 196 | Line exceeds 200 characters (333 chars) |
| `specs/archive/install-first-run.md` | 212 | Line exceeds 200 characters (212 chars) |
| `specs/archive/install-first-run.md` | 228 | Line exceeds 200 characters (273 chars) |
| `specs/archive/install-first-run.md` | 232 | Line exceeds 200 characters (274 chars) |
| `specs/archive/install-first-run.md` | 246 | Line exceeds 200 characters (291 chars) |
| `specs/archive/install-first-run.md` | 265 | Line exceeds 200 characters (280 chars) |
| `specs/archive/install-first-run.md` | 282 | Line exceeds 200 characters (277 chars) |
| `specs/archive/manifest-schema-alignment.md` | 8 | Line exceeds 200 characters (653 chars) |
| `specs/archive/manifest-schema-alignment.md` | 12 | Line exceeds 200 characters (250 chars) |
| `specs/archive/manifest-schema-alignment.md` | 40 | Line exceeds 200 characters (203 chars) |
| `specs/archive/manifest-schema-alignment.md` | 41 | Line exceeds 200 characters (247 chars) |
| `specs/archive/manifest-schema-alignment.md` | 64 | Line exceeds 200 characters (202 chars) |
| `specs/archive/manifest-schema-alignment.md` | 94 | Line exceeds 200 characters (289 chars) |
| `specs/archive/setup-platform-resilience.md` | 9 | Line exceeds 200 characters (331 chars) |
| `specs/archive/setup-platform-resilience.md` | 11 | Line exceeds 200 characters (295 chars) |
| `specs/archive/setup-platform-resilience.md` | 13 | Line exceeds 200 characters (232 chars) |
| `specs/archive/setup-platform-resilience.md` | 15 | Line exceeds 200 characters (202 chars) |
| `specs/archive/setup-platform-resilience.md` | 60 | Line exceeds 200 characters (312 chars) |
| `specs/archive/template-import.md` | 7 | Line exceeds 200 characters (414 chars) |
| `specs/archive/template-import.md` | 45 | Line exceeds 200 characters (203 chars) |
| `specs/archive/toggleable-yaml-preview.md` | 7 | Line exceeds 200 characters (299 chars) |
| `specs/archive/toggleable-yaml-preview.md` | 48 | Line exceeds 200 characters (342 chars) |
| `specs/archive/variable-editor.md` | 8 | Line exceeds 200 characters (322 chars) |
| `specs/archive/windows-installer.md` | 7 | Line exceeds 200 characters (311 chars) |
| `specs/archive/windows-installer.md` | 9 | Line exceeds 200 characters (281 chars) |
| `specs/archive/windows-installer.md` | 81 | Line exceeds 200 characters (217 chars) |
| `specs/archive/windows-installer.md` | 85 | Line exceeds 200 characters (223 chars) |
| `specs/archive/wsl-platform-utility.md` | 8 | Line exceeds 200 characters (374 chars) |
| `tasks/001-health-remediation-wsl-permissions-and-lint.md` | 43 | Line exceeds 200 characters (217 chars) |
| `tasks/001-health-remediation-wsl-permissions-and-lint.md` | 68 | Line exceeds 200 characters (224 chars) |
| `tasks/1-authoring-sync-baseline.md` | 68 | Line exceeds 200 characters (214 chars) |
| `tasks/1-authoring-sync-baseline.md` | 70 | Line exceeds 200 characters (309 chars) |
| `tasks/2-wsl-windows-path-sync-bug.md` | — | Task missing `## Tasks` section |
| `tasks/2-wsl-windows-path-sync-bug.md` | 66 | Line exceeds 200 characters (288 chars) |
| `tasks/3-wsl-espanso-dependency-onboarding.md` | — | Task missing `## Tasks` section |
| `tasks/3-wsl-espanso-dependency-onboarding.md` | 68 | Line exceeds 200 characters (331 chars) |
| `tasks/4-wsl-espanso-wrapper-install.md` | — | Task missing `## Tasks` section |
| `tasks/4-wsl-espanso-wrapper-install.md` | 68 | Line exceeds 200 characters (243 chars) |
| `tasks/archive/cli-colored-output.md` | — | Task missing `## Tasks` section |
| `tasks/archive/cli-colored-output.md` | 23 | Line exceeds 200 characters (243 chars) |
| `tasks/archive/cli-doctor.md` | — | Task missing `## Tasks` section |
| `tasks/archive/cli-dry-run-verbose.md` | — | Task missing `## Tasks` section |
| `tasks/archive/cli-tab-completion.md` | — | Task missing `## Tasks` section |
| `tasks/archive/espanso-config-validation.md` | — | Task missing `## Tasks` section |
| `tasks/archive/espanso-launcher-trigger.md` | — | Task missing `## Tasks` section |
| `tasks/archive/espanso-path-consolidation.md` | — | Task missing `## Tasks` section |
| `tasks/archive/espansr-orchestratr-connector.md` | — | Task missing `## Tasks` section |
| `tasks/archive/first-public-release.md` | — | Task missing `## Tasks` section |
| `tasks/archive/gui-dark-mode.md` | — | Task missing `## Tasks` section |
| `tasks/archive/gui-dark-mode.md` | 16 | Line exceeds 200 characters (207 chars) |
| `tasks/archive/gui-keyboard-shortcuts.md` | — | Task missing `## Tasks` section |
| `tasks/archive/gui-single-screen.md` | — | Task missing `## Tasks` section |
| `tasks/archive/gui-single-screen.md` | 54 | Line exceeds 200 characters (223 chars) |
| `tasks/archive/gui-status-bar-feedback.md` | — | Task missing `## Tasks` section |
| `tasks/archive/gui-status-bar-feedback.md` | 16 | Line exceeds 200 characters (289 chars) |
| `tasks/archive/gui-status-bar-feedback.md` | 42 | Line exceeds 200 characters (214 chars) |
| `tasks/archive/gui-status-bar-feedback.md` | 62 | Line exceeds 200 characters (257 chars) |
| `tasks/archive/gui-template-preview.md` | — | Task missing `## Tasks` section |
| `tasks/archive/install-first-run.md` | — | Task missing `## Tasks` section |
| `tasks/archive/install-first-run.md` | 16 | Line exceeds 200 characters (348 chars) |
| `tasks/archive/install-first-run.md` | 24 | Line exceeds 200 characters (290 chars) |
| `tasks/archive/install-first-run.md` | 41 | Line exceeds 200 characters (265 chars) |
| `tasks/archive/install-first-run.md` | 76 | Line exceeds 200 characters (394 chars) |
| `tasks/archive/manifest-schema-alignment.md` | — | Task missing `## Tasks` section |
| `tasks/archive/roadmap-v1.0.md` | — | Task missing `## Tasks` section |
| `tasks/archive/setup-platform-resilience.md` | — | Task missing `## Tasks` section |
| `tasks/archive/setup-platform-resilience.md` | 29 | Line exceeds 200 characters (218 chars) |
| `tasks/archive/template-import.md` | — | Task missing `## Tasks` section |
| `tasks/archive/toggleable-yaml-preview.md` | — | Task missing `## Tasks` section |
| `tasks/archive/variable-editor.md` | — | Task missing `## Tasks` section |
| `tasks/archive/windows-installer.md` | — | Task missing `## Tasks` section |
| `tasks/archive/windows-installer.md` | 16 | Line exceeds 200 characters (302 chars) |
| `tasks/archive/windows-installer.md` | 25 | Line exceeds 200 characters (216 chars) |
| `tasks/archive/windows-installer.md` | 29 | Line exceeds 200 characters (202 chars) |
| `tasks/archive/wsl-platform-utility.md` | — | Task missing `## Tasks` section |
| `decisions/0001-platform-config-single-source.md` | 9 | Line exceeds 200 characters (345 chars) |
| `decisions/0001-platform-config-single-source.md` | 13 | Line exceeds 200 characters (212 chars) |
| `decisions/0001-platform-config-single-source.md` | 19 | Line exceeds 200 characters (354 chars) |
| `workflow/FILE_CONTRACTS.md` | 1–5 | No H1 heading in first 5 lines |
| `workflow/LIFECYCLE.md` | 28 | Line exceeds 200 characters (679 chars) |
| `workflow/LIFECYCLE.md` | 32 | Line exceeds 200 characters (367 chars) |
| `workflow/LIFECYCLE.md` | 59 | Line exceeds 200 characters (202 chars) |
| `workflow/LINT_CONTRACT.md` | 20 | Line exceeds 200 characters (213 chars) |
| `workflow/ORCHESTRATOR.md` | 3 | Line exceeds 200 characters (316 chars) |
| `workflow/ORCHESTRATOR.md` | 9 | Line exceeds 200 characters (357 chars) |
| `workflow/ORCHESTRATOR.md` | 10 | Line exceeds 200 characters (311 chars) |
| `workflow/ORCHESTRATOR.md` | 20 | Line exceeds 200 characters (218 chars) |
| `workflow/ORCHESTRATOR.md` | 47 | Line exceeds 200 characters (276 chars) |
| `workflow/ORCHESTRATOR.md` | 88 | Line exceeds 200 characters (255 chars) |
| `workflow/ROUTING.md` | 7 | Line exceeds 200 characters (225 chars) |
| `workflow/ROUTING.md` | 28 | Line exceeds 200 characters (265 chars) |
| `.specify/constitution.md` | 1 | Line exceeds 200 characters (283 chars) |
| `.specify/constitution.md` | 7 | Line exceeds 200 characters (224 chars) |

---
_Generated by `scripts/workflow-lint.sh`. See `workflow/LINT_CONTRACT.md` for check definitions._
