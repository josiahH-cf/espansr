# Feature: 6-commands-popup

**Feature ID:** 6-commands-popup

## Description

Add a hardcoded `:coms` Espanso trigger that opens a lightweight, scrollable popup showing the currently available Espanso triggers in a clean read-only layout. The popup is a simpler companion to `:aopen`: it opens quickly, standardizes each row as trigger + description + output preview, and closes immediately on `Esc` so the user can resume their current flow.

**Constitution mapping:** Core Capability #1 (Visual command creation/editing), #3 (Safe sync pipeline), #4 (Platform-aware setup)

## Acceptance Criteria

- [x] **AC-1:** GIVEN Espanso is configured for espansr, WHEN the user runs `espansr setup`, THEN espansr generates a dedicated `espansr-commands.yml` file containing a hardcoded `:coms` trigger that launches the popup instead of the full editor.
- [x] **AC-2:** GIVEN the popup is opened through `:coms` or `espansr gui --view commands`, WHEN espansr loads the popup content, THEN it shows all available Espanso triggers from user templates plus the built-in system triggers, sorted deterministically.
- [x] **AC-3:** GIVEN a popup row is rendered, WHEN the trigger has metadata available, THEN the row shows a standardized trigger label, description, and output preview in a scrollable read-only layout.
- [x] **AC-4:** GIVEN the commands popup is focused, WHEN the user presses `Esc`, THEN the popup closes immediately and the process exits cleanly.
- [x] **AC-5:** GIVEN espansr diagnostics or cleanup run, WHEN they inspect espansr-managed Espanso files, THEN `espansr-commands.yml` is treated the same way as the existing launcher file for generation, doctor checks, and stale-file cleanup.

## Affected Areas

- `espansr/core/command_catalog.py` — new shared trigger catalog for popup rows
- `espansr/ui/commands_popup.py` — new lightweight read-only popup UI
- `espansr/integrations/espanso.py` — generated `:coms` trigger file + stale cleanup
- `espansr/__main__.py` — GUI popup launch path, setup, and doctor output
- `tests/test_commands_popup.py` — new popup/catalog coverage
- `tests/test_launcher.py`, `tests/test_setup.py`, `tests/test_doctor.py`, `tests/test_path_consolidation.py` — lifecycle regression coverage
- `docs/CLI.md`, `docs/TEMPLATES.md`, `docs/VERIFY.md` — user docs

## Constraints

- `:coms` remains hardcoded and distinct from template-managed triggers.
- The popup must stay read-only and simpler than the full editor launched by `:aopen`.
- No new runtime dependencies; use existing PyQt6 widgets and theme styling.
- The popup launch command must reuse the same detached, cross-platform shell strategy as the existing launcher trigger.

## Out of Scope

- Editing templates from the popup
- Search/filter inside the popup
- Listing espansr CLI subcommands in the popup
- Making `:coms` user-configurable

## Dependencies

- Existing launcher-generation flow in `espansr/integrations/espanso.py`
- Existing template metadata from `TemplateManager.iter_with_triggers()`

## Test Planning Intent

**Test approach:** Unit tests for the shared catalog and generated trigger file; GUI tests for popup rendering and `Esc` handling; regression tests for setup, doctor, and stale cleanup.

**Rough test scenarios:**
- [x] Generate a command catalog that includes template and system triggers
- [x] Render the popup with standardized rows and scrollable content
- [x] Close the popup with `Esc`
- [x] Generate `espansr-commands.yml` with the correct trigger and GUI launch args
- [x] Treat the commands popup file as managed during setup, doctor, and stale cleanup

## Verification Map

| AC | Test File | Test Function | Assertion |
|----|-----------|---------------|-----------|
| AC-1 | tests/test_launcher.py | test_generate_commands_popup_creates_valid_yaml | `espansr-commands.yml` contains `:coms` and popup launch args |
| AC-1 | tests/test_setup.py | test_setup_generates_commands_popup_when_espanso_found | setup generates the popup trigger file |
| AC-2 | tests/test_commands_popup.py | test_build_command_catalog_includes_template_and_system_triggers | catalog contains template triggers plus `:aopen` and `:coms` |
| AC-3 | tests/test_commands_popup.py | test_commands_popup_dialog_renders_entries | popup list renders standardized entry widgets |
| AC-4 | tests/test_commands_popup.py | test_commands_popup_dialog_closes_on_escape | `Esc` closes the popup |
| AC-5 | tests/test_doctor.py | test_doctor_reports_commands_popup_file_missing | doctor reports popup trigger file state |
| AC-5 | tests/test_path_consolidation.py | test_clean_stale_deletes_commands_popup_file_from_noncanonical | stale cleanup removes `espansr-commands.yml` from non-canonical dirs |

## Contracts

- **Exposes:** `CommandCatalogEntry` dataclass and `build_command_catalog()` in `espansr/core/command_catalog.py`
- **Exposes:** `CommandsPopupDialog` and `launch_commands_popup()` in `espansr/ui/commands_popup.py`
- **Exposes:** `generate_commands_popup_file()` in `espansr/integrations/espanso.py`
- **Consumes:** `TemplateManager.iter_with_triggers()`, `Config.espanso.launcher_trigger`, existing GUI launch command resolution

## Execution Linkage

Execution planning is authoritative in `/tasks/6-commands-popup.md`.
