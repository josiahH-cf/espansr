# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- **`:project-systems` — Master Systems Process runner** — a new bundled note
	that continues the Master Systems Process from its own files rather than
	from chat: it opens the project tracker as the single entry point, works the
	first incomplete step, triages each unknown as discoverable / testable /
	human-owned / deferred, groups any remaining questions into one round, and
	writes every material result back to the tracker, clarification file, master
	document, diagrams, and project record.

- **Workflow diagrams in `:coms` and `:aopen`** — the process graphs are now
	drawn as interactive diagrams from the workflow manifests: the `:coms`
	Processes view shows the graph with per-node details and copy / scratchpad
	/ show-command actions, and the editor gains a Workflows panel (toolbar
	button or `Ctrl+Shift+W`) where clicking a node selects that template.
	Manifests may carry optional `x`/`y` layout hints on nodes and `short`
	arrow labels on edges; manifests without hints get a deterministic
	auto-layout. Loop edges draw in the accent color and "feeds any node"
	sources draw once, dashed.

- **Capability graph and process layer** — templates can carry additive
	capability metadata (`capability_id`, `intent_tags`, `accepts`, `produces`,
	`use_when`, `avoid_when`, `output_contract`); optional workflow manifests
	under `templates/_meta/workflows/` describe how capabilities relate
	(bundled: `evidence-research-cycle` and `feature-delivery-cycle`); the
	`:coms` popup gains fuzzy search, artifact selectors, Recommended /
	Processes / Recent / Favorites views, per-command guidance, and direct
	copy/scratchpad/packet/editor actions; handoff packets provide explicit,
	user-saved context transport (`espansr packet`); `espansr workflows`
	inspects and validates manifests; `espansr check-output` validates model
	output against a template's structural output contract; and the new
	standalone `:litmus` note authors plain-language human-verification
	checklists. The refined `:feature` note adds honest INPUT COVERAGE and an
	explicit CLARIFICATION STATUS while preserving its nine-phase handoff
	workflow. Everything is optional and local: every trigger works exactly as
	before, no workflow owns a current step, nothing runs automatically, and no
	metadata reaches generated Espanso YAML. See docs/PROCESS.md.

- **In-place reinstall command** — `espansr refresh` identifies the OS and the
	recorded install location, then reruns the correct installer (`install.ps1`
	via PowerShell on Windows, `install.sh` via Bash on Linux/macOS/WSL2). It
	prints a small `ok` notification on success and opens the install folder if
	the reinstall fails. The installers now record this location via
	`espansr record-install` (stored as `install.json` in the config directory).
- **Commands popup scratchpad** — the `:coms` popup now includes an ephemeral,
	expandable scratchpad pinned at the bottom where you can type or paste any
	command, add context, and copy it back out. The scratchpad is throwaway and
	never saved.
- **Commands popup trigger** — espansr now generates an `espansr-commands.yml`
	file with a hardcoded `:coms` trigger that opens a lightweight read-only
	popup showing available Espanso triggers, descriptions, and output previews.
- **Template retirement command** — `espansr retire TARGET` backs up a live
	template, deletes the JSON file, and refreshes managed Espanso output.

### Changed

- **`:reality` rewritten as a comprehensive end-state account** — the note
	now classifies its evidence (verified reality / proposed reality /
	supported inference / unknown), preserves the target material's own logic
	instead of silently repairing it, and returns a headed `# Reality Summary`
	opening with an "If you only read one thing" line and closing with
	`## ✅ Definition of Done`. This supersedes the previous fixed
	two-paragraph, zero-to-ten-bullet output contract.
- **`:coms` "Prompt to scratchpad"** now places the command's full prompt in
	the scratchpad (previously only the trigger); system entries without a
	prompt body still insert their trigger.
- **Default theme is now Dark** — the GUI and `:coms` popup default to dark mode
	everywhere. Light mode must be explicitly selected from the toolbar theme
	selector (Auto/Dark/Light).

### Fixed

- **Retired-template local cleanup** — publishing now removes stale managed
	`espansr.yml` output when no triggered templates remain.
- **GUI delete publishing** — deleting a template from the GUI now publishes the
	remaining templates after the undo window closes.
- **Windows installer compatibility** — `install.ps1` no longer uses
	PowerShell 7-only syntax while declaring PowerShell 5.1 support.
- **WSL candidate path probing hardening** — `espansr doctor` and GUI startup no longer crash when unreadable Windows profile paths exist under `/mnt/c/Users/*`. Unreadable candidate directories are now skipped with warnings so canonical Espanso path detection continues.
- **WSL launcher regeneration reliability** — rerunning `espansr setup` now refreshes the generated `espansr-launcher.yml` safely for Windows-hosted WSL Espanso configs, so the `:aopen` launcher trigger can recover from stale launcher output without manual YAML edits.
- **Windows launcher console suppression** — the generated native Windows `:aopen` launcher now prefers `pythonw.exe` and no longer opens an extra console window when it starts the GUI.
- **First-publish install gap** — `espansr setup` now performs an initial publish when Espanso is detected, so bundled triggers like `:verify` are available immediately after install instead of waiting for a manual save/publish cycle.

### Changed

- **Windows vs WSL install guidance** — installer output and user docs now make it explicit that Windows PowerShell and WSL are separate environments with separate PATH, shell integration, and `espansr` installs.
- **Windows installer startup check** — `install.ps1` now verifies Espanso startup registration and starts the service when possible, so native Windows installs do not rely on an implicit prior Espanso boot configuration.
- **Publish-first wording** — README, verification docs, installers, and quick
	help now present `publish` as the primary local Espanso output command and
	keep `sync` only as legacy compatibility wording.

## [1.1.0] — 2026-03-01

Completes the v1.0 feature roadmap with the test suite passing.

### Added

- **Shell Tab Completion** — `espansr completions bash` and `espansr completions zsh` generate shell completion scripts from argparse introspection. `install.sh` prints a sourcing hint after install.
- **`espansr doctor`** — Diagnostic command that checks Python version, config dir, templates, Espanso config, binary, launcher file, and template validation. Returns exit 0/1.
- **CLI Dry-Run and Verbose Modes** — `espansr sync --dry-run` and `espansr setup --dry-run` preview changes without writing. `espansr setup --verbose` shows per-file detail. Flags are combinable.
- **Colored CLI Output** — `ok()`, `warn()`, `fail()`, `info()` helpers in `cli_color.py` with TTY detection and `NO_COLOR` support. Applied to doctor, status, validate, and setup output.
- **Setup and Platform Resilience** — Bundled template path fallback to `importlib.resources`. `espansr setup --strict` returns 1 if Espanso not found. Bundled templates validated during setup. Platform config caching with `@lru_cache`.
- **GUI Status Bar and Sync Feedback** — Permanent status indicator showing Espanso config path. Sync result messages with template count or error details.
- **GUI Template Preview Pane** — Live output preview that substitutes variables with defaults, labels, or formatted dates.
- **GUI Dark/Light Mode** — Auto-detection via `QStyleHints.colorScheme()` with `QPalette` luminance fallback. Runtime theme switcher (Auto/Dark/Light) in toolbar.
- **GUI Keyboard Shortcuts** — Ctrl+S sync, Ctrl+N new, Ctrl+I import, Ctrl+F search, Delete/Ctrl+D delete. Platform-native key sequences.

## [1.0.0] — 2026-02-28

First public release.

### Added

- **Template Import** — `espansr import <path>` CLI command and GUI toolbar button for importing external template JSON files or directories. Strips unrecognized fields, de-duplicates names with numeric suffixes.
- **Espanso Config Validation** — `espansr validate` CLI command with six validation rules (empty trigger, short trigger, bad prefix, unmatched placeholders, unused variables, duplicate triggers). Sync blocks on errors, proceeds with warnings. GUI surfaces validation messages in the status bar.
- **Espanso Launcher Trigger** — `generate_launcher_file()` writes `espansr-launcher.yml` with a shell trigger to open the GUI from Espanso. WSL2-aware command construction. Configurable trigger keyword.
- **Inline Variable Editor** — `VariableEditorWidget` with add/edit/delete rows, name validation, date-type format field, form-type multiline toggle, and live YAML preview.
- **GUI Single-Screen Layout** — Splitter-based browser/editor layout with toolbar (Sync Now, auto-sync toggle), inline template editor, inline delete confirmation, and window geometry persistence.
- **Cross-Platform Installer Architecture** — `PlatformConfig` dataclass as single source of truth for all platform-specific paths. `espansr setup` CLI command performs all post-install work. `install.sh` restructured to a thin bootstrap that delegates to `espansr setup`.
- **Windows Installer** — `install.ps1` PowerShell script (5.1+ compatible) with Python version check, venv creation, and delegation to `espansr setup`.
- **Bundled starter template** (`espansr_help.json`) copied on first install.
- **`espansr --version`** flag prints the installed version.
- **CI pipeline** with Ruff lint, Black format check, and pytest across Python 3.11, 3.12, 3.13.

### Changed

- **WSL/Platform Utility Module** — All platform detection consolidated into `espansr/core/platform.py` (`get_platform()`, `is_wsl2()`, `get_windows_username()`). Callers no longer read `/proc/version` or call `cmd.exe` directly.
- **Espanso Path Consolidation** — `get_espanso_config_dir()` persists resolved path to config. `clean_stale_espanso_files()` removes managed files from non-canonical directories. All Espanso candidate paths defined once in `PlatformConfig`.
- **`espansr status`** shows platform-specific guidance when Espanso is not found.

## [0.1.0] — 2025-01-01

### Added

- Initial standalone build with template CRUD, JSON storage, Espanso YAML generation.
- CLI interface (`sync`, `status`, `list`, `gui` commands).
- PyQt6 GUI with template browser and editor.
- WSL2 support for Windows-side Espanso config detection.
