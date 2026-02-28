# Feature: Cross-Platform Installer Architecture

## Description

The installer and platform-handling code has five structural problems that will compound as features are added. This spec addresses all five with a single architectural change.

**Problem 1 — Platform detection fragmentation.** Despite Issue #1 creating `espansr/core/platform.py` as the "single source of truth," two Python files still call `platform.system()` directly using a different vocabulary (`"Darwin"`, `"Linux"`, `"Windows"`) than the canonical module (`"macos"`, `"linux"`, `"windows"`, `"wsl2"`). The shell installer has a fourth independent implementation. That is 3 Python detection paths plus 1 shell path.

**Problem 2 — Duplicated platform-specific logic.** The Espanso config candidate path list is maintained independently in three places: `_get_candidate_paths()` in `espanso.py`, `detect_espanso()` in `install.sh`, and `clean_stale_espanso_files()` in `install.sh`. The Windows username lookup exists in two implementations (Python and bash). The espansr config directory path is computed independently in `config.py` and `install.sh`. Any change to supported paths must be replicated across all copies.

**Problem 3 — Installer completeness gaps.** After a fresh install, `espansr list` returns "No templates with triggers found" because no seed content is bundled. `espansr status` prints "Espanso config: not found" without platform-specific guidance. The smoke test hides its output behind `/dev/null`.

**Problem 4 — Bootstrap/post-install boundary is wrong.** The installer performs Espanso detection, stale file cleanup, templates-dir setup, and launcher generation in bash, duplicating logic that already exists in Python and becomes available the moment `pip install -e .` completes. Only Python version checking, system dependency installation (apt-get), and venv creation genuinely require bash.

**Problem 5 — Platform coverage gap.** Python code handles 4 platforms (`windows`, `macos`, `linux`, `wsl2`) but the bash installer handles only 3 (no native Windows). There is no install path for native Windows users. (Native Windows installer is tracked separately in `/specs/windows-installer.md`.)

### Approach

1. Introduce a `PlatformConfig` data structure in `espansr/core/platform.py` that maps each platform to its complete set of paths (espansr config dir, Espanso candidate dirs). All platform-specific path logic is defined once in this structure. `config.py` and `espanso.py` consume it instead of computing paths themselves.

2. Add an `espansr setup` CLI command that performs all post-install work using the canonical Python platform module: copy bundled templates, detect Espanso, clean stale files, generate launcher, print summary. This replaces ~130 lines of bash that duplicate Python logic.

3. Restructure `install.sh` into a thin bootstrap (Python check, system deps, venv, pip install) that delegates to `espansr setup` for everything else.

4. Bundle a starter template so the tool has content on first run. Add platform-specific guidance to `espansr status`.

## Audit Evidence

The following details were verified by reading every source file. They are included so an implementer can locate and modify each duplication site without re-auditing.

### Direct `platform.system()` calls outside canonical module

| File | Line | Function | What it does |
|------|------|----------|-------------|
| `espansr/core/config.py` | L8 | top-level | `import platform` (stdlib) |
| `espansr/core/config.py` | L58 | `get_config_dir()` | `platform.system()` — branches on `"Darwin"` to choose macOS path vs XDG |
| `espansr/integrations/espanso.py` | L8 | top-level | `import platform` (stdlib) |
| `espansr/integrations/espanso.py` | L81 | `_get_candidate_paths()` | `platform.system()` — branches on `"Linux"`, `"Darwin"`, `"Windows"` for candidate paths |

### Canonical module already imports (correctly used by some callers)

| File | What it imports from `espansr.core.platform` |
|------|---------------------------------------------|
| `espansr/core/config.py` L14 | `get_platform`, `is_windows` (re-export, not used internally by config.py) |
| `espansr/integrations/espanso.py` L15 | `get_windows_username`, `get_wsl_distro_name`, `is_wsl2` |
| `espansr/__main__.py` L32 | `is_wsl2` |

### Espanso candidate path lists — 3 independent copies

**Copy 1** — `espansr/integrations/espanso.py` `_get_candidate_paths()` (L80–L112):
- WSL2: `/mnt/c/Users/{user}/.config/espanso`, `/mnt/c/Users/{user}/.espanso`, `/mnt/c/Users/{user}/AppData/Roaming/espanso`
- Linux: `~/.config/espanso`, `~/.espanso`
- macOS: `~/Library/Application Support/espanso`, `~/.config/espanso`
- Windows: `%APPDATA%/espanso`, `~/.espanso`

**Copy 2** — `install.sh` `detect_espanso()` (L122–L153):
- WSL2: `/mnt/c/Users/$win_user/.config/espanso`, `/mnt/c/Users/$win_user/.espanso`, `/mnt/c/Users/$win_user/AppData/Roaming/espanso`
- Linux: `~/.config/espanso`, `~/.espanso`
- macOS: `~/Library/Application Support/espanso`, `~/.config/espanso`

**Copy 3** — `install.sh` `clean_stale_espanso_files()` (L161–L200):
- Same paths as Copy 2, independently constructed

### Espansr config dir — 2 independent implementations

| Implementation | Location | macOS path | Linux/WSL path |
|---------------|----------|------------|----------------|
| Python | `config.py` `get_config_dir()` L55–L68 | `~/Library/Application Support/espansr` | `$XDG_CONFIG_HOME/espansr` or `~/.config/espansr` |
| Bash | `install.sh` `setup_templates_dir()` L254–L261 | `~/Library/Application Support/espansr` | `${XDG_CONFIG_HOME:-$HOME/.config}/espansr` |

### Windows username — 2 independent implementations

| Implementation | Location | Technique |
|---------------|----------|-----------|
| Python | `platform.py` `get_windows_username()` L80–L93 | `subprocess.run(["cmd.exe", "/c", "echo %USERNAME%"])` |
| Bash | `install.sh` L125, L165 | `cmd.exe /c "echo %USERNAME%" 2>/dev/null \| tr -d '\r'` |

### install.sh step-by-step (current state)

| Step | Lines | Could be Python? | Reason |
|------|-------|-------------------|--------|
| Platform detection | L32–L40 | No | Needed before Python is available, for apt-get decision |
| Python version check | L46–L63 | No | Python might not exist yet |
| System deps (apt-get) | L66–L91 | No | Must run before pip install (PyQt6 needs xcb libs) |
| Venv creation | L94–L106 | No | Bootstrapping the environment |
| pip install | L108–L112 | No | Installing the package |
| Espanso detection | L116–L156 | **Yes** — `get_espanso_config_dir()` does this | Duplicates Python logic |
| Stale file cleanup | L159–L234 | **Yes** — `clean_stale_espanso_files()` does this | Duplicates Python logic |
| Launcher generation | L237–L243 | **Yes** — already calls Python inline | Already delegates, but in isolation |
| Templates dir setup | L246–L272 | **Yes** — `get_templates_dir()` does this | Duplicates Python logic |
| Shell alias | L275–L295 | No | Modifies `~/.bashrc`/`~/.zshrc` — must be bash |
| Smoke test | L298–L303 | Partially | Runs CLI commands, could show richer output |
| Banner | L306–L314 | No | User-facing output |

### Files with NO platform logic (confirmed clean)

`espansr/core/templates.py`, `espansr/integrations/validate.py`, `espansr/ui/main_window.py`, `espansr/ui/template_browser.py`, `espansr/ui/template_editor.py`, `espansr/ui/variable_editor.py`, `espansr/ui/theme.py`, `espansr/__init__.py`

## Acceptance Criteria

- [ ] **AC-1**: `espansr/core/platform.py` exports a `PlatformConfig` dataclass and a `get_platform_config()` function that returns the espansr config dir path and the ordered list of Espanso candidate config dir paths for the detected platform
- [ ] **AC-2**: `espansr/core/config.py` `get_config_dir()` delegates to the platform module for path resolution — no `import platform` or direct `platform.system()` call remains in `config.py`
- [ ] **AC-3**: `espansr/integrations/espanso.py` `_get_candidate_paths()` delegates to the platform module — no `import platform` or direct `platform.system()` call remains in `espanso.py`
- [ ] **AC-4**: There is exactly one place in the Python codebase that defines each platform-specific path (espansr config dir path, each Espanso candidate dir path) — that place is `espansr/core/platform.py`
- [ ] **AC-5**: A new `espansr setup` CLI command performs: (a) ensure espansr config dir exists, (b) copy bundled templates with no-overwrite, (c) detect and persist Espanso config path, (d) clean stale files, (e) generate launcher trigger, (f) print human-readable summary of results
- [ ] **AC-6**: `install.sh` is restructured so that Espanso detection, stale cleanup, templates-dir creation, and launcher generation are removed from bash and replaced by a single `$VENV_CMD setup` call
- [ ] **AC-7**: The repo `templates/` directory contains at least one bundled JSON template with a trigger that passes `espansr validate`
- [ ] **AC-8**: `espansr setup` copies bundled templates into the user config templates dir; existing same-named files are never overwritten
- [ ] **AC-9**: After a fresh `./install.sh` run, `espansr list` returns at least one triggered template without any manual steps
- [ ] **AC-10**: When Espanso config is not found, `espansr status` prints platform-specific next-step guidance (see Notes for exact strings per platform)
- [ ] **AC-11**: Adding support for a new platform requires editing only `espansr/core/platform.py` (path definitions) and optionally `install.sh` (system deps) — no other Python source files need platform-specific changes
- [ ] **AC-12**: All new logic is covered by pytest tests; all 126 existing tests continue to pass without modification

## Affected Areas

| Area | Files | Change type |
|------|-------|-------------|
| Platform module | `espansr/core/platform.py` | Modify — add `PlatformConfig` dataclass and `get_platform_config()` factory |
| Config module | `espansr/core/config.py` | Modify — remove `import platform`; rewrite `get_config_dir()` to use `get_platform_config()` |
| Espanso integration | `espansr/integrations/espanso.py` | Modify — remove `import platform`; rewrite `_get_candidate_paths()` to use `get_platform_config()` |
| CLI entry point | `espansr/__main__.py` | Modify — add `cmd_setup()` and `setup` subcommand; add guidance to `cmd_status()` |
| Installer | `install.sh` | Modify — remove ~130 lines (espanso detection, stale cleanup, templates-dir, launcher); add `$VENV_CMD setup` call |
| Bundled templates | `templates/espansr_help.json` | Create — starter template |
| Tests | `tests/test_platform.py` | Modify — add tests for `PlatformConfig` / `get_platform_config()` |
| Tests | `tests/test_setup.py` | Create — tests for `espansr setup` command behavior |

## Constraints

- **No new dependencies**: no `requests`, no external downloads during install (per AGENTS.md dependency list)
- **No overwrite on copy**: bundled templates must never replace user-edited files (skip if target filename exists)
- **Backward compatible**: existing installs continue to work; re-running `install.sh` is safe and idempotent
- **WSL safety**: do not attempt to install, configure, or manage Espanso itself — it runs on the Windows host
- **Single `import platform`**: after this work, only `espansr/core/platform.py` may import the stdlib `platform` module in the entire Python codebase
- **Deterministic tests**: all tests must use tmp dirs, never the user's real config directory
- **Shell installer remains bash**: `install.sh` must remain a working entry point (some users run it directly), just thinner
- **Diff under 300 lines per PR**: if implementation exceeds this, split into multiple PRs per AGENTS.md rules
- **No test modification**: existing tests must pass without changes — fix the implementation, not the tests (per AGENTS.md)

## Out of Scope

- Installing, configuring, or upgrading Espanso itself (upstream tool; Espanso's responsibility)
- Creating an Espanso config directory if one doesn't exist (Espanso creates this on `espanso start`)
- Native Windows installer (PowerShell `.ps1`) — tracked separately in `/specs/windows-installer.md`
- Auto-sourcing the shell rc file (unsafe in non-interactive shells)
- Building a comprehensive template library (one starter template is sufficient for v1)
- README.md or AGENTS.md documentation updates (separate task/PR to keep diffs under 300 lines)
- Any changes to the GUI
- PyPI publishing
- Caching or memoization of platform detection results

## Dependencies

- All prerequisite features (Issues #1–#7) are complete — no blockers
- No external service or network dependencies

## Notes

### Architecture: PlatformConfig

Add to `espansr/core/platform.py` a dataclass and factory function:

```python
@dataclass
class PlatformConfig:
    platform: str                          # "linux", "macos", "wsl2", "windows", "unknown"
    espansr_config_dir: Path               # where espansr stores its own config and templates
    espanso_candidate_dirs: list[Path]     # ordered list of dirs to probe for Espanso config
```

`get_platform_config()` calls `get_platform()` once and builds the appropriate `PlatformConfig`. Platform-to-path mapping:

| Platform | `espansr_config_dir` | `espanso_candidate_dirs` |
|----------|---------------------|--------------------------|
| `macos` | `~/Library/Application Support/espansr` | `~/Library/Application Support/espanso`, `~/.config/espanso` |
| `linux` | `$XDG_CONFIG_HOME/espansr` or `~/.config/espansr` | `~/.config/espanso`, `~/.espanso` |
| `wsl2` | `$XDG_CONFIG_HOME/espansr` or `~/.config/espansr` | `/mnt/c/Users/{win_user}/.config/espanso`, `/mnt/c/Users/{win_user}/.espanso`, `/mnt/c/Users/{win_user}/AppData/Roaming/espanso`, `~/.config/espanso`, `~/.espanso` |
| `windows` | `%APPDATA%/espansr` or `~/espansr` | `%APPDATA%/espanso`, `~/.espanso` |

The WSL2 entry calls `get_windows_username()` internally. If the username cannot be resolved, the `/mnt/c/Users/` entries are omitted (preserves current behavior in `_get_candidate_paths()`).

**Key invariant**: every platform-specific path literal appears exactly once, inside `get_platform_config()`.

### Architecture: Consumers of PlatformConfig

**`config.py` `get_config_dir()`** — replace `platform.system()` branching with:
```python
from espansr.core.platform import get_platform_config
pc = get_platform_config()
base = pc.espansr_config_dir.parent
# ... migration logic stays the same, using base ...
config_dir = pc.espansr_config_dir
```

Remove the `import platform` line (L8) entirely. Remove the re-export of `get_platform` and `is_windows` from L14 — but first grep the codebase for any imports of these names from `espansr.core.config`. If any exist (test files especially), update them to import directly from `espansr.core.platform`. Then remove the re-export line.

**`espanso.py` `_get_candidate_paths()`** — replace entire function body with:
```python
from espansr.core.platform import get_platform_config
return get_platform_config().espanso_candidate_dirs
```

Remove the `import platform` line (L8) entirely.

### Architecture: `espansr setup`

New CLI subcommand registered in `__main__.py`. Implementation in a new function `cmd_setup()`. Steps in order:

1. Call `get_config_dir()` — ensures espansr config dir exists (already does `mkdir -p`)
2. Call `get_templates_dir()` — ensures templates subdir exists
3. Locate bundled templates: use `Path(__file__).resolve().parent.parent / "templates"` to find the repo-level `templates/` directory (this works for editable installs; if the path doesn't exist, skip gracefully)
4. Copy each `.json` file from bundled dir to user templates dir, skipping files whose filename already exists at the destination (no-overwrite). Use `shutil.copy2` only if target does not exist.
5. Call `get_espanso_config_dir()` — auto-detects and persists Espanso path
6. Call `clean_stale_espanso_files()`
7. Call `generate_launcher_file()`
8. Print human-readable summary to stdout:
   - "Templates: copied N bundled template(s) to {path}" or "Templates: {path} (N existing, no changes)"
   - "Espanso config: {path}" or "Espanso config: not found — {platform-specific guidance}"
   - "Launcher: generated" or "Launcher: skipped (no Espanso config)"

This command is idempotent — safe to run on every install and re-install.

### Architecture: Thin install.sh

After restructuring, `install.sh` contains only these sections:

1. **`detect_platform()`** — bash-native, 3 branches (`macos`, `wsl2`, `linux`). Must remain in bash because it decides whether to run `apt-get` before Python is available. This is the only remaining duplication with the Python module — it is 6 lines and produces no paths.
2. **`check_python()`** — find suitable Python ≥3.11 binary. Must remain in bash.
3. **`install_system_deps()`** — `apt-get install` for PyQt6 xcb libs on Linux/WSL. Must remain in bash.
4. **Venv creation** + `pip install -e .` — bootstrapping. Must remain in bash.
5. **`$VENV_CMD setup`** — single line that delegates ALL post-install work to Python. This replaces the old `detect_espanso()` (L116–L156), `clean_stale_espanso_files()` (L159–L234), `generate_launcher()` (L237–L243), and `setup_templates_dir()` (L246–L272) bash functions.
6. **`setup_shell_alias()`** — modifies `~/.bashrc` or `~/.zshrc`. Must remain in bash.
7. **Smoke test** — runs `$VENV_CMD list` and `$VENV_CMD status` with visible output (not suppressed).
8. **Completion banner**.

### Starter template

Create `templates/espansr_help.json` in the repo root:

```json
{
  "name": "Espansr Quick Help",
  "description": "Quick reference for espansr CLI commands.",
  "trigger": ":espansr",
  "content": "espansr commands:\n  list       — show templates with triggers\n  sync       — sync to Espanso\n  status     — show config paths\n  validate   — check for errors\n  import     — import templates\n  gui        — launch editor\n\nConfig: ~/.config/espansr/\nSync:   espansr sync"
}
```

This must be valid against `Template.from_dict()` and pass `espansr validate`. No variables — simple trigger-to-text expansion.

### Platform-specific status guidance

When `espansr status` finds no Espanso config dir, print one of these based on `get_platform()`:

| `get_platform()` | Message |
|-------------------|---------|
| `wsl2` | `Espanso config: not found — install Espanso on Windows (https://espanso.org), then run 'espanso start' from PowerShell` |
| `linux` | `Espanso config: not found — install Espanso (https://espanso.org), then run 'espanso start' to initialize` |
| `macos` | `Espanso config: not found — install Espanso (https://espanso.org), then run 'espanso start' to initialize` |
| `windows` | `Espanso config: not found — install Espanso (https://espanso.org), then run 'espanso start' to initialize` |

### Migration path

Existing installs have bash-generated launcher files and config that continue to work. Re-running `install.sh` after this change invokes `espansr setup`, which re-generates the launcher and performs cleanup — strictly a superset of the old behavior. No manual migration is needed.

### Adding a new platform (future)

To add support for a hypothetical new platform (e.g., FreeBSD):

1. Add a branch to `get_platform()` in `platform.py` returning `"freebsd"`
2. Add a branch to `get_platform_config()` with the appropriate config dir and Espanso candidate paths
3. Optionally add a system-deps block in `install.sh` if the platform uses a different package manager
4. No other source files need changes — `config.py`, `espanso.py`, CLI, and GUI all consume `PlatformConfig` generically

### Re-export cleanup in config.py

Line 14 of `config.py` currently re-exports `get_platform` and `is_windows` from the platform module:
```python
from espansr.core.platform import get_platform, is_windows  # noqa: F401
```
Before removing this, grep the entire codebase and test suite for any imports of `get_platform` or `is_windows` from `espansr.core.config`. If any exist, update them to import from `espansr.core.platform` directly. Then remove the re-export line and the `import platform` line.
