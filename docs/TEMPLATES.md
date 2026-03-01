# Template Format

espansr templates are JSON files that define text expansion snippets for [Espanso](https://espanso.org/).

## Storage Locations

Templates are stored in a platform-specific config directory:

| Platform | Path |
|----------|------|
| Linux | `~/.config/espansr/templates/` |
| macOS | `~/Library/Application Support/espansr/templates/` |
| Windows | `%APPDATA%/espansr/templates/` |
| WSL2 | `~/.config/espansr/templates/` |

A bundled starter template (`espansr_help.json`) is automatically copied on first install via `espansr setup`.

## Schema

Each template is a JSON file with the following fields:

```json
{
  "name": "Greeting",
  "content": "Hello, {{name}}!",
  "trigger": ":greet",
  "variables": [
    {"name": "name", "label": "Name", "default": "World"}
  ]
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Display name for the template |
| `content` | string | Yes | The expansion text. Use `{{variable_name}}` for placeholders. |
| `trigger` | string | No | Espanso trigger string (e.g., `:greet`). Templates without a trigger are shown in the browser but excluded from sync. |
| `variables` | array | No | List of variable definitions for placeholders in `content`. |

### Variable Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Variable name (matches `{{name}}` in content) |
| `label` | string | No | Human-readable label shown in the editor |
| `default` | string | No | Default value for the variable |
| `type` | string | No | Variable type: `"date"` enables date format field, `"form"` enables multiline |

## Sync Behavior

When you run `espansr sync` (or click "Sync Now" in the GUI):

1. Templates with a `trigger` field are converted to Espanso YAML match format
2. The generated YAML is written to the Espanso config directory
3. Templates without a trigger are skipped during sync
4. Duplicate triggers and validation issues are reported before sync

## Importing Templates

You can import external template files:

```bash
espansr import /path/to/template.json       # single file
espansr import /path/to/templates/           # entire directory
```

Import strips unrecognized fields and de-duplicates names with numeric suffixes.

## Validation Rules

`espansr validate` checks templates for:

- Empty trigger strings
- Short triggers (< 2 characters)
- Bad trigger prefix (missing recommended `:` prefix)
- Unmatched placeholders (`{{var}}` in content with no matching variable)
- Unused variables (defined but not referenced in content)
- Duplicate triggers across templates
