# Feature: Template Import

**Status:** Complete

## Description

Allow users to import template JSON files from external sources via CLI and GUI. Imported files are normalized to the internal schema: unrecognized fields are stripped, variable entries are mapped to the Espanso-compatible `Variable` format, and name collisions with existing templates are handled gracefully. This enables sharing templates between espansr instances and adopting templates authored in other tools.

## Acceptance Criteria

- [x] `import_template(path)` loads a JSON file, strips unrecognized top-level fields, and returns a valid `Template`
- [x] Variable entries in imported JSON are mapped to the internal `Variable` schema (name, label, default, type, params, multiline); unknown variable fields are dropped
- [x] When an imported template's name collides with an existing template, the import function renames it with a numeric suffix (e.g., "My Template (2)") and returns the de-duplicated name
- [x] `import_templates(path)` accepts a directory path and imports all `*.json` files, returning a summary of successes, skips, and errors
- [x] `espansr import <path>` CLI command imports a file or directory and prints a summary
- [x] The GUI template browser exposes an "Import" toolbar button that opens a file dialog and imports the selected file(s), refreshing the browser list afterward
- [x] Malformed JSON files produce a clear error message without crashing

## Affected Areas

- `espansr/core/templates.py` — new `import_template()` / `import_templates()` functions
- `espansr/__main__.py` — new `import` CLI subcommand
- `espansr/ui/main_window.py` — Import toolbar button
- `tests/test_import.py` — new test file

## Constraints

- No network access — import is file-system only (no URLs, no `requests`)
- Must not overwrite existing templates without explicit user intent (rename-on-collision is the default)
- Imported templates are saved through `TemplateManager.save()` to preserve all existing versioning behavior

## Out of Scope

- Importing Espanso YAML match files (potential future feature)
- Importing from URLs or remote sources
- Export functionality
- Batch conflict resolution strategies beyond auto-rename (e.g., interactive overwrite prompts)

## Dependencies

- Existing `Template.from_dict()` and `TemplateManager` in `espansr/core/templates.py`

## Notes

- `Template.from_dict()` already ignores unknown keys because it uses explicit `data.get()` calls, but the import layer should explicitly filter to the known schema for clarity and forward-compatibility.
- The known top-level fields are: `name`, `content`, `description`, `trigger`, `variables`, `refinements`.
- The known variable fields are: `name`, `label`, `default`, `multiline`, `type`, `params`.
- Imported files that lack a `name` field default to the filename stem (e.g., `my_template.json` → "my template").
