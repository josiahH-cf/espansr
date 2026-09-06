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
| Sync | `espansr sync` | Project checkout and recorded install | Pulls with rebase, commits and pushes local changes, then reruns the installer |

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

Run post-install setup: copies missing bundled templates into the live store, validates them, detects Espanso, generates the `:aopen` launcher, the `:coms` commands popup trigger, and the `:sync` trigger (`espansr-launcher.yml`, `espansr-commands.yml`, and `espansr-sync.yml`), performs an initial publish, writes the orchestratr manifest when orchestratr is found, and ensures the PATH-visible `espansr` command shim.

The bundled-template copy step never overwrites an existing live file, but the initial publish that follows (when Espanso is detected) applies bundled template updates exactly as `espansr publish` does: missing or changed bundled templates are applied to the live store, a changed local copy is backed up under `_versions/` before it is replaced, renamed starters are migrated, and retired starters are removed. Run `espansr starters` first if you want to see that drift before setup or publish applies it.

On native Windows, the generated `:aopen` launcher prefers `pythonw.exe` when
available so the GUI opens without an extra console window.

The generated `:coms` popup trigger opens a lightweight command reference
showing your currently available Espanso triggers. It also includes an
ephemeral scratchpad pinned at the bottom of the popup where you can type or
paste any command, add context, and copy it back out. The scratchpad is
throwaway and never saved.

The generated `:sync` trigger runs `espansr sync` through the console entry
point, so its progress shows in a window; see [`espansr sync`](#espansr-sync).

The command shim is a real `espansr` executable in the user bin directory, so
the command resolves in non-interactive shells such as subprocess calls,
`.desktop` launchers, systemd user units, IDE terminals, and RustDesk/RDP
session shells, where a shell alias never does. On Linux, macOS, and WSL2 it
is a symlink at `~/.local/bin/espansr` to the venv's executable (a small
wrapper script where symlinks are unsupported); on Windows the user bin
directory is the venv `Scripts` folder that `install.ps1` persists to the user
PATH. When a stray non-symlink file blocks the shim path, setup reports a
conflict and `--force-shim` overwrites it. On POSIX, setup warns when the bin
directory is not on PATH.

On WSL2, rerun `espansr setup` after changing install paths or launcher behavior if you need to refresh the generated Windows-side `espansr-launcher.yml` trigger file.

```bash
espansr setup                     # standard setup
espansr setup --verbose           # show per-file detail
espansr setup --strict            # return exit code 1 if Espanso not found
espansr setup --dry-run           # preview without writing
espansr setup --force-shim        # overwrite a file blocking the command shim path
espansr setup --verbose --strict  # flags are combinable
```

### `espansr validate`

Validate templates for common Espanso issues (empty triggers, short triggers, bad prefixes, unmatched placeholders, unused variables, duplicate triggers) and warning-only collisions with the generated system triggers `:aopen`, `:coms`, and `:sync`. Exit code 1 when any error is found; warnings alone exit 0.

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

Run diagnostic health checks: Python version, config directory, templates, Espanso config and binary, the generated `espansr-launcher.yml` and `espansr-commands.yml` files, the PATH-visible `espansr` command shim, WSL candidate-path conflicts, and template validation. The shim check creates the shim when it is missing; a blocked shim path (fix with `espansr setup --force-shim`) or a bin directory that is not on PATH is reported as a warning.

Like `list`, `validate`, and `gui`, `doctor` first pulls the configured template remote when one is set and `remote.auto_pull` is on (the default); a failed auto-pull is logged and never blocks the command.

```bash
espansr doctor
```

Exit code 0 if no check fails, 1 if any check is `[FAIL]`. Shim and PATH warnings do not change the exit code.

### `espansr wsl-install-espanso`

Install and start Windows-side Espanso from WSL2 via PowerShell.

```bash
espansr wsl-install-espanso
```

Use this only when you are intentionally running `espansr` inside WSL2. It
does not install `espansr` into Windows PowerShell, and it does not merge WSL
PATH or shell setup with Windows.

When it succeeds, run `espansr setup` and then `espansr doctor` from WSL:
`doctor` reports failures until `setup` has generated the launcher files.

### `espansr refresh`

Reinstall `espansr` in place by rerunning the OS-appropriate installer. This is
useful after pulling repository updates or when an install looks broken.

```bash
espansr refresh
```

`refresh` identifies the operating system and the recorded install location,
then reruns `install.ps1` through PowerShell on Windows or `install.sh` through
Bash on Linux, macOS, and WSL2. On success it prints a small `ok` notification.
If the reinstall fails, it opens the install folder so you can rerun the
installer manually.

The install location is recorded by `install.sh` / `install.ps1` (which call
`espansr record-install` after setup) and stored as `install.json` in the
espansr config directory. When that metadata is missing, `refresh` falls back to
auto-detecting the repository folder from the installed package.

`espansr record-install` is an installer helper that writes this metadata; you
do not normally run it by hand.

### `espansr sync`

Update this machine in one step: pull the project repository, commit and push
local changes, then reinstall.

```bash
espansr sync             # pull --rebase, commit and push local changes, reinstall
espansr sync --no-push   # pull and reinstall only
```

`sync` resolves the repository folder and installer from the same recorded
install metadata as `refresh`, then runs `git fetch --prune` and
`git pull --rebase` (uncommitted changes are stashed first and restored
afterwards). Unless `--no-push` is given it then stages everything
(`git add -A`), commits with the fixed message `espansr sync: local changes`,
and pushes when the branch is ahead of its upstream; a failed push is reported
and the reinstall still runs. Finally it reruns the recorded installer exactly
as `refresh` does.

On a rebase conflict, `sync` aborts the rebase, restores the stash, lists the
conflicted files, and skips the reinstall so a broken tree is never
reinstalled (exit code 1); the same applies when the restored stash conflicts.
When the folder is not a git checkout, or `git fetch` fails (for example
offline), `sync` skips the pull and push and reinstalls the current checkout.

The generated `:sync` Espanso trigger runs this command (see `setup`), and the
GUI toolbar **Sync** button runs the same flow; the GUI refuses to start it
while the editor has unsaved changes.

### `espansr configure-remote-desktop`

Tune Espanso for the machine's role so espansr expansions fire and paste
reliably, including over RustDesk/RDP.

```bash
espansr configure-remote-desktop           # remote-desktop host mode
espansr configure-remote-desktop --local   # local workstation mode (clipboard preserved)
espansr configure-remote-desktop --auto    # workstation mode unless host mode was declared
espansr configure-remote-desktop --revert  # remove the espansr-managed remote-desktop settings
```

- With no flag: remote-desktop host mode, for a machine you reach over
  RustDesk/RDP.
- `--local`: workstation mode, for a machine you sit at physically;
  expansions paste correctly while your clipboard is preserved.
- `--auto`: applies workstation mode unless the machine was previously put in
  host mode, which then stays sticky across reinstalls and `espansr refresh`.
- `--revert`: removes the espansr-managed remote-desktop settings.

`install.ps1` runs this on every Windows install: `--auto` by default, host
mode with `.\install.ps1 -RemoteDesktop`, and workstation mode with
`.\install.ps1 -LocalOnly`. The command restarts Espanso after a change and
exits 1 when no Espanso config directory is detected.

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
delete-with-undo flow. `Ctrl+Shift+W` (or the "Show Workflows" toolbar
button) opens the workflow diagram panel: the bundled process graphs drawn
from the manifests, where clicking a node selects that template in the
browser and editor. See [PROCESS.md](PROCESS.md#diagrams).

The toolbar theme selector (Auto/Dark/Light) defaults to Dark. The GUI and the
`:coms` popup start in dark mode; choose Light or Auto from the selector to
switch.

Deleting a template from the GUI backs it up locally, removes the JSON file
after the undo window, and publishes the remaining templates so managed Espanso
output no longer contains the retired trigger.

### `espansr check-output`

Validate a model-generated output file against a template's structural output
contract (for templates that declare one, such as `:feature` and `:litmus`).
For `:feature`, the checked file is the final-artifact reply that follows your
approval — the reply carrying the FINAL IMPLEMENTATION META-PROMPT and REALITY
SUMMARY — not the approval-round packet, which the contract never checks.
Validation is read-only, reports every unmet obligation rather than only the
first, and proves structural conformance only — it never claims semantic
correctness.

```bash
espansr check-output --template :feature run-output.txt
espansr check-output --template :litmus checklist.md --json
```

Exit codes: `0` contract passed, `1` contract failed, `2` the template
declares no output contract, `3` template not found or the output file cannot
be read. The template is resolved by trigger, name, or capability ID, first in
the live store and then among the bundled templates.

### `espansr workflows`

Inspect the optional workflow manifests that describe how capabilities relate.
Workflows are informational: every capability stays directly invocable, no
current step is tracked, and nothing ever runs automatically.

```bash
espansr workflows list                          # list manifests
espansr workflows show evidence-research-cycle  # entry points, nodes, edges
espansr workflows validate                      # exit 1 on any manifest error
```

Bundled manifests live beside the bundled templates in
`templates/_meta/workflows/`; user manifests may be added under the live
store's `_meta/workflows/` directory (which stays local-only — `_meta/` is
gitignored by remote template sync).

### `espansr packet`

Inspect saved handoff packets — explicit, user-controlled context transports
created from the `:coms` popup. Packets live in the local config directory
(`<config>/packets/`), outside the git-synced template store, and are never
created, synced, or deleted automatically.

```bash
espansr packet list                 # saved packets with artifact types
espansr packet show my_packet       # print one packet (ID or path)
espansr packet validate packet.md   # exit 1 with every validation error
espansr packet delete my_packet     # explicitly delete one packet
```

### `espansr --version`

Print the installed version.

```bash
espansr --version
```

## Global Behavior

- **`--dry-run`** — Available on `publish`, `retire`, `starters`, and `setup`. Previews changes without writing files.
- **`--verbose`** — Available on `starters` and `setup`. Shows per-file detail.
- **`--strict`** — Available on `setup`. Returns exit code 1 if Espanso is not detected.
- **`--force-shim`** — Available on `setup`. Overwrites a non-symlink file that blocks the command shim path.
- **`--no-push`** — Available on `sync`. Pulls and reinstalls without committing or pushing local changes.
- **Auto-pull** — `doctor`, `list`, `validate`, and `gui` first pull the configured template remote when `remote.auto_pull` is on (the default). A failed pull is logged and never blocks the command.
- **Exit codes** — `starters` exits 1 when it finds drift (without `--apply`) or when `--apply` skipped invalid local JSON, and 2 when the report has errors or `--force` is given without `--apply`. `import DIR` exits 0 whenever at least one file imported, 1 only when every file failed or the path does not exist. `validate` exits 1 on errors, `doctor` exits 1 on any failed check, `sync` exits 1 when a conflict stops the reinstall, and `check-output` uses 0/1/2/3 as described above.
- **Colored output** — CLI output uses colors when connected to a TTY. Respects the `NO_COLOR` environment variable.
