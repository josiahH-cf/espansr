# CLI Reference

espansr provides a full command-line interface for managing Espanso templates.

Windows PowerShell and WSL are separate environments. PATH changes, shell
aliases, and virtual environments created in one do not automatically apply to
the other.

## Commands

The daily command lanes are:

| Lane | Command | Source of truth | Result |
|------|---------|-----------------|--------|
| Publish | `espansr publish` | Local live templates | Writes Espanso YAML output |
| Pull | `espansr pull` | Configured Git remote | Pulls remote templates, then writes Espanso YAML output |
| Push | `espansr push` | Local live templates | Commits and pushes template JSON to the remote |
| Starters | `espansr starters` | Bundled starter templates | Checks or applies bundled starter updates |
| Retire | `espansr retire TARGET` | Local live templates | Backs up, deletes, then refreshes Espanso YAML output |
| Remote | `espansr remote ...` | Remote configuration | Sets, reports, or removes the Git remote |

### `espansr publish`

Publish local templates to Espanso. Before writing YAML match files, this also applies
missing or changed bundled template updates to the live template store, backing
up changed bundled-matching local files under `_versions/`.

```bash
espansr publish              # publish local templates to Espanso
espansr publish --dry-run    # preview what would be written (no changes)
```

### `espansr starters`

Check whether the live espansr template store has drifted from the bundled starter templates, or apply bundled updates back into the live store.

`espansr publish` applies normal bundled updates automatically before generating
Espanso YAML. Use `starters` when you want to inspect bundled drift directly,
preview the local JSON updates, or force-replace invalid bundled-matching local
JSON after backing it up.

```bash
espansr starters                     # check for bundled drift
espansr starters --verbose           # show per-template drift details
espansr starters --apply             # copy/update bundled templates into the live store
espansr starters --apply --dry-run   # preview bundled updates without writing
espansr starters --apply --force     # back up and replace invalid bundled-matching local JSON
```

Behavior:

- Bundled filenames in the repo/package are treated as canonical.
- Local-only templates are reported but preserved.
- Changed bundled-matching local templates are backed up into `_versions/` before replacement.
- Old renamed starter files are migrated to the new bundled filename when safe.
- Trigger collisions are reported before files are changed or Espanso YAML is written.
- Invalid local JSON files are reported and skipped by default.
- `--apply --force` backs up invalid bundled-matching local JSON into `_versions/` and then replaces it.

### `espansr pull`

Pull the latest template repository state from the configured Git remote, then
refresh Espanso output from the pulled templates.

```bash
espansr remote set git@github.com:USER/REPO.git
espansr pull
espansr pull --template sig.json
```

`pull` reports whether files were updated, templates were already up to
date, the remote was empty, Git was unavailable, or the remote could not be
reached. It uses the existing Git credentials on the machine and does not store
or prompt for authentication.

### `espansr push`

Push local template JSON changes to the configured Git remote.

```bash
espansr push
espansr push --template sig.json
espansr push --message "Update signature template"
```

Use `push` when the local template store is the source of truth and you want to share those template JSON files with other machines through Git.

### `espansr retire`

Back up and delete one local template, then publish the remaining templates to
Espanso with bundled-template updates disabled for that run.

`TARGET` resolves by exact trigger, exact template name, exact filename, or exact
relative path under the live template directory. Ambiguous targets are rejected;
use a relative path when two folders contain the same filename.

```bash
espansr retire :sig
espansr retire sig.json
espansr retire snippets/sig.json
espansr retire "Email Signature"
espansr retire :sig --dry-run
```

Retirement preserves a local backup under `_versions/` where possible. It only
updates espansr-managed Espanso output; unmanaged Espanso YAML files are left
alone. If the retired template was the last triggered template, stale
`espansr.yml` output is removed.

### `espansr remote`

Configure or inspect the Git remote used by `pull` and `push`.

```bash
espansr remote set git@github.com:USER/REPO.git
espansr remote status
espansr remote remove
```

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

Run post-install setup: copies bundled templates, validates them, detects Espanso, performs an initial publish, and generates the launcher, commands popup trigger, and orchestratr manifest.

`setup` is bootstrap-only for bundled templates: it copies missing starter templates, but it does not overwrite existing live templates. Use `espansr starters --apply` if bundled starter templates change later and you want to refresh the live store.

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

Validate templates for common Espanso issues (empty triggers, short triggers, bad prefixes, unmatched placeholders, unused variables, duplicate triggers) and warning-only collisions with generated system triggers such as `:aopen` and `:coms`.

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

The full GUI includes template browsing, editing, variable editing, previews,
import, remote pull, and publishing. `Ctrl+S` publishes, `Ctrl+N` creates a new
template, `Ctrl+I` imports, `Ctrl+F` searches, and `Delete` starts the
delete-with-undo flow.

Deleting a template from the GUI backs it up locally, removes the JSON file
after the undo window, and publishes the remaining templates so managed Espanso
output no longer contains the retired trigger.

### `espansr --version`

Print the installed version.

```bash
espansr --version
```

## Global Behavior

- **`--dry-run`** — Available on `publish`, `retire`, `starters`, and `setup`. Previews changes without writing files.
- **`--verbose`** — Available on `starters` and `setup`. Shows per-file detail.
- **`--strict`** — Available on `setup`. Returns exit code 1 if Espanso is not detected.
- **Colored output** — CLI output uses colors when connected to a TTY. Respects the `NO_COLOR` environment variable.
