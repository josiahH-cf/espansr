<!-- This file is generated during Phase 2 (Compass). During Phase 2, this is the primary write target — Compass directly populates sections based on the discovery interview. After Phase 2 completes, this file is read-only. Post-Compass edits require /compass-edit or equivalent. -->

# Project Constitution

This document defines the project's identity, goals, and boundaries. It is the source of truth that every downstream phase references. Nothing gets built that isn't traceable to this document.

The sections below are guiding themes — not a rigid checklist. Compass populates them with depth proportional to the project's needs. Some projects need extensive security coverage; others need minimal. The interview adapts.

## Problem & Context

People who rely on Espanso still spend too much time hand-authoring and debugging YAML match files.
`espansr` solves this by providing a GUI + CLI workflow for creating, validating, and syncing expansion commands.
Without this project, users continue to manage brittle manual YAML edits, slower command iteration, and higher error rates when scaling their snippet libraries.

## Target User

Primary users are developers and workflow optimizers who automate repetitive typing tasks.
Typical environments include Windows, WSL, and Linux, with macOS support as an expected cross-platform target.
Pain points include managing many triggers, validating command definitions quickly, and keeping local command sets synchronized with Espanso and adjacent tooling.

## Success Criteria

Success means Espanso installation, detection, and sync flows are reliable and low-friction.
Command editing must feel intuitive in the GUI, with CLI parity for automation workflows.
Existing functionality remains stable release-to-release, while users can add new commands with high throughput and minimal validation failures.
Integration paths with external tools remain dependable.

## Core Capabilities

Core capabilities mapped to user needs:

1. Visual command creation/editing: Build and maintain Espanso commands in a GUI instead of raw YAML hand-editing.
2. CLI-first automation: Provide sync, validation, import, status, and diagnostics commands for terminal-heavy workflows.
3. Safe sync pipeline: Validate templates and generate Espanso-compatible output with dry-run support before writes.
4. Platform-aware setup: Detect and operate correctly across Windows/WSL/Linux/macOS environments.
5. External tool compatibility: Keep integration points (for example launcher/manifests) functioning through updates.

## Out-of-Scope Boundaries

The project is not a general automation platform or replacement for Espanso itself.
It focuses on command/template authoring and sync workflows, not arbitrary desktop orchestration.

- Not: Building a full replacement text-expansion engine.
- Not: Owning lifecycle management for every external integration tool.
- Not: Becoming a cloud-hosted collaboration service.

## Inviolable Principles

These principles remain fixed even when roadmap pressure is high:

1. Reliability first: Never trade sync correctness for feature speed.
2. Usability parity: GUI and CLI must both remain practical, not second-class surfaces.
3. Backward stability: Existing command workflows should not silently regress.

## Security Posture

This is a local-first desktop/CLI application with no built-in remote authentication surface.
Security focus is on safe filesystem writes, predictable config path handling, and avoiding unintended command/file injection.
No regulated-data compliance target is currently declared; hardening priorities are input validation, path safety, and deterministic sync outputs.

## Testing Strategy

Use test-first or test-concurrent development for behavior changes, with acceptance criteria mapped to tests.
Required suite types: unit tests for core logic, integration tests for sync/integration boundaries, and GUI behavior tests for key interaction flows.
Primary framework is `pytest`; CI enforces lint + test green before merge.
Regression tests are mandatory for bug fixes affecting sync, parsing, or platform detection.

## Ambiguity Tracking

Document what remains unresolved after the Compass interview. This section is expected to have content — not everything can be decided upfront.

- **Unknown:** Quantitative UX targets for "intuitive editing" (time-to-create-command, error-rate goals) are not yet baseline-measured.
- **Unknown:** Long-term macOS packaging and distribution strategy needs explicit scope.
- **Deferred:** Type-checking policy is deferred until Phase 4 tooling refinement.
- **Deferred:** External integrations beyond current launcher/manifest paths stay opt-in until feature specs define expansion scope.
