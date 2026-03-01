# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.1.0] — 2026-03-01

All v1.0 roadmap features complete. 298 tests passing.

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
