# CLI Reference

espansr provides a full command-line interface for managing Espanso templates.

Windows PowerShell and WSL are separate environments. PATH changes, shell
aliases, and virtual environments created in one do not automatically apply to
the other.

## Commands

### `espansr sync`

Sync templates to Espanso. Writes YAML match files to the Espanso config directory.

```bash
espansr sync              # sync all templates
espansr sync --dry-run    # preview what would be written (no changes)
espansr sync --verbose    # show per-file detail
```

### `espansr sync-bundled`

Check whether the live espansr template store has drifted from the bundled starter templates, or apply bundled updates back into the live store.

This is separate from `espansr sync`: it reconciles JSON template files in the espansr template store, not generated Espanso YAML output.

```bash
espansr sync-bundled                     # check for bundled drift
espansr sync-bundled --verbose          # show per-template drift details
espansr sync-bundled --apply            # copy/update bundled templates into the live store
espansr sync-bundled --apply --dry-run  # preview bundled updates without writing
espansr sync-bundled --apply --force    # back up and replace invalid bundled-matching local JSON
```

Behavior:

- Bundled filenames in the repo/package are treated as canonical.
- Local-only templates are reported but preserved.
- Changed bundled-matching local templates are backed up into `_versions/` before replacement.
- Invalid local JSON files are reported and skipped by default.
- `--apply --force` backs up invalid bundled-matching local JSON into `_versions/` and then replaces it.

### `espansr status`

Show Espanso connection status and config path.

```bash
espansr status            # human-readable output
espansr status --json     # machine-readable JSON (for orchestratr or scripting)
```

### `espansr list`

List all templates with their trigger strings.

```bash
espansr list
```

### `espansr setup`

Run post-install setup: copies bundled templates, validates them, detects Espanso, performs an initial sync, and generates the launcher, commands popup trigger, and orchestratr manifest.

`setup` is bootstrap-only for bundled templates: it copies missing starter templates, but it does not overwrite existing live templates. Use `espansr sync-bundled --apply` if bundled starter templates change later and you want to refresh the live store.

On native Windows, the generated `:aopen` launcher prefers `pythonw.exe` when
available so the GUI opens without an extra console window.

The generated `:coms` popup trigger opens a lightweight read-only command
reference showing your currently available Espanso triggers.

On WSL2, rerun `espansr setup` after changing install paths or launcher behavior if you need to refresh the generated Windows-side `espansr-launcher.yml` trigger file.

```bash
espansr setup                     # standard setup
espansr setup --verbose           # show per-file detail
espansr setup --strict            # return exit code 1 if Espanso not found
espansr setup --dry-run           # preview without writing
espansr setup --verbose --strict  # flags are combinable
```

### `espansr validate`

Validate templates for common Espanso issues (empty triggers, short triggers, bad prefixes, unmatched placeholders, unused variables, duplicate triggers).

```bash
espansr validate
```

### `espansr import`

Import an external template JSON file or directory of template files.

```bash
espansr import /path/to/template.json
espansr import /path/to/templates/
```

### `espansr doctor`

Run diagnostic health checks: Python version, config directory, templates, Espanso config, binary, launcher file, and template validation.

```bash
espansr doctor
```

Exit code 0 if all checks pass, 1 if any fail.

### `espansr wsl-install-espanso`

Install and start Windows-side Espanso from WSL2 via PowerShell.

```bash
espansr wsl-install-espanso
```

Use this only when you are intentionally running `espansr` inside WSL2. It
does not install `espansr` into Windows PowerShell, and it does not merge WSL
PATH or shell setup with Windows.

### `espansr completions`

Generate shell tab completion scripts.

```bash
eval "$(espansr completions bash)"   # bash
eval "$(espansr completions zsh)"    # zsh
```

Add the appropriate line to your shell profile (`~/.bashrc`, `~/.zshrc`) for persistent completion.

### `espansr gui`

Launch the graphical interface.

```bash
espansr gui
espansr gui --view commands
```

Use `--view commands` to open the lightweight commands popup directly instead of
the full editor. This is the same popup launched by the generated `:coms`
Espanso trigger.

### `espansr --version`

Print the installed version.

```bash
espansr --version
```

## Global Behavior

- **`--dry-run`** — Available on `sync` and `setup`. Previews changes without writing files.
- **`--verbose`** — Available on `setup`. Shows per-file detail.
- **`--strict`** — Available on `setup`. Returns exit code 1 if Espanso is not detected.
- **Colored output** — CLI output uses colors when connected to a TTY. Respects the `NO_COLOR` environment variable.
