"""Espanso integration for espansr.

Generates Espanso match files from templates that have triggers defined.
Supports Linux, WSL2 (auto-detects Windows Espanso config path), and macOS.
"""

import logging
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
from typing import Optional

import yaml

from espansr.core.atomic import atomic_copy, atomic_write_bytes
from espansr.core.command_catalog import COMMANDS_POPUP_TRIGGER
from espansr.core.config import get_config, get_config_dir, save_config
from espansr.core.platform import (
    get_platform,
    get_platform_config,
    get_wsl_distro_name,
    is_windows,
    is_wsl2,
)
from espansr.core.templates import get_template_manager
from espansr.integrations.validate import validate_all

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a sync_to_espanso() call.

    Attributes:
        success: Whether the sync completed without errors.
        count: Number of templates synced.
        errors: Human-readable error descriptions (empty on success).
    """

    success: bool
    count: int = 0
    errors: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        """Allow truthiness check for backward compatibility."""
        return self.success


# File names managed by espansr — only these are cleaned up
LAUNCHER_FILE_NAME = "espansr-launcher.yml"
COMMANDS_POPUP_FILE_NAME = "espansr-commands.yml"
SYNC_FILE_NAME = "espansr-sync.yml"

_MANAGED_FILES = (
    "espansr.yml",
    LAUNCHER_FILE_NAME,
    COMMANDS_POPUP_FILE_NAME,
    SYNC_FILE_NAME,
)

# Old file names from before the rebrand — cleaned up on sync
_OLD_MANAGED_FILES = ("automatr-espanso.yml", "automatr-launcher.yml")


# ── Section 1: YAML generation ────────────────────────────────────────────────
# Converts template data into Espanso v2 match YAML.
# _convert_to_espanso_placeholders, _build_espanso_var_entry


def _convert_to_espanso_placeholders(content: str, variables) -> str:
    """Convert template placeholders {{var}} to Espanso form placeholders.

    Form variables use {{var.value}} to access the form field value.
    Date and other simple types use {{var}} directly (no conversion).
    """
    updated = content
    for var in variables:
        name = var.name
        var_type = getattr(var, "type", "form")

        if var_type == "form":
            # Espanso v2 form layout returns objects; access via .value
            updated = updated.replace(f"{{{{{name}}}}}", f"{{{{{name}.value}}}}")
            updated = updated.replace(f"{{{{ {name} }}}}", f"{{{{{name}.value}}}}")
        # Date and other simple types use {{var}} directly — no conversion needed
    return updated


def _build_espanso_var_entry(var) -> dict:
    """Build an Espanso variable entry from a Variable object."""
    var_type = getattr(var, "type", "form")
    params = getattr(var, "params", {})

    if var_type == "date":
        var_entry: dict = {
            "name": var.name,
            "type": "date",
        }
        if params:
            var_entry["params"] = params
        return var_entry

    # Default: form type with Espanso v2 [[value]] layout placeholder
    var_entry = {
        "name": var.name,
        "type": "form",
        "params": {
            "layout": f"{var.label}: [[value]]",
        },
    }
    if var.default:
        var_entry["params"]["default"] = var.default
    return var_entry


# ── Section 2: Config discovery ──────────────────────────────────────────────
# Locates the Espanso config and match directories across Windows/WSL2/Linux.
# _get_candidate_paths, get_espanso_config_dir, clean_stale_espanso_files,
# get_match_dir


def _get_candidate_paths() -> list[Path]:
    """Return all known Espanso config candidate directories for the current platform.

    Delegates to get_platform_config() for platform-specific path resolution.

    Returns:
        List of candidate paths (may or may not exist on disk).
    """
    return get_platform_config().espanso_candidate_dirs


def _is_windows_side_wsl_path(path: Path) -> bool:
    """Return True when path points to Windows filesystem from WSL."""
    normalized = str(path).replace("\\", "/")
    parts = [part for part in normalized.split("/") if part]
    return len(parts) >= 2 and parts[0] == "mnt" and len(parts[1]) == 1 and parts[1].isalpha()


def _path_exists_safe(path: Path) -> bool:
    """Return True if path exists, False when missing or unreadable."""
    try:
        return path.exists()
    except PermissionError:
        logger.warning("Skipping unreadable path: %s", path)
        return False
    except OSError as exc:
        logger.warning("Skipping path due to OS error (%s): %s", exc, path)
        return False


def _is_dir_safe(path: Path, *, label: str = "directory path") -> bool:
    """Return True if path is a directory, False when missing or unreadable."""
    try:
        return path.is_dir()
    except PermissionError as exc:
        logger.warning("Skipping unreadable %s %s: %s", label, path, exc)
        return False
    except OSError as exc:
        logger.warning("Skipping %s due to OS error (%s): %s", label, exc, path)
        return False


def get_espanso_config_dir() -> Optional[Path]:
    """Get the Espanso configuration directory.

    Checks (in order):
    1. Persisted path from config.espanso.config_path (re-validated)
    2. Auto-detection from candidate paths

    After successful auto-detection, persists the resolved path so
    subsequent calls skip probing.

    Returns:
        Path to Espanso config directory, or None if not found.
    """
    config = get_config()

    # Use persisted path if set and still valid
    if config.espanso.config_path:
        path = Path(config.espanso.config_path).expanduser()
        if _path_exists_safe(path):
            # In WSL, prefer Windows-side canonical locations to avoid split
            # state when both Linux and Windows Espanso paths exist.
            normalized = str(path).replace("\\", "/")
            linux_style_espanso_path = normalized.endswith(
                "/.config/espanso"
            ) or normalized.endswith("/.espanso")
            if linux_style_espanso_path and is_wsl2() and not _is_windows_side_wsl_path(path):
                for candidate in _get_candidate_paths():
                    if _path_exists_safe(candidate) and _is_windows_side_wsl_path(candidate):
                        logger.info(
                            "Switching Espanso config path from %s to Windows-side %s",
                            path,
                            candidate,
                        )
                        config.espanso.config_path = str(candidate)
                        save_config(config)
                        return candidate
            return path
        # Persisted path is stale — clear and re-detect
        logger.warning(
            "Persisted Espanso path %s no longer exists, re-detecting",
            config.espanso.config_path,
        )
        config.espanso.config_path = ""
        save_config(config)

    # Auto-detect from candidate paths
    for candidate in _get_candidate_paths():
        if _path_exists_safe(candidate):
            # Persist the discovered path
            config.espanso.config_path = str(candidate)
            save_config(config)
            return candidate

    return None


def clean_stale_espanso_files() -> None:
    """Remove espansr-managed files from non-canonical Espanso config dirs.

    Scans all known Espanso config candidate paths and deletes
    `espansr.yml` and `espansr-launcher.yml` from any `match/`
    directory that is NOT the canonical one.

    Also removes old automatr-espanso.yml and automatr-launcher.yml files
    from ALL directories (including canonical) as part of the rebrand migration.

    Silent on permission errors — logs a warning but does not raise.
    Does nothing if no canonical directory is found.
    """
    canonical = get_espanso_config_dir()
    if canonical is None:
        return

    canonical_match = canonical / "match"

    for candidate in _get_candidate_paths():
        match_dir = candidate / "match"

        if not _is_dir_safe(match_dir, label="Espanso match directory"):
            continue

        # Clean old automatr-* files from ALL directories (rebrand migration)
        for filename in _OLD_MANAGED_FILES:
            old_file = match_dir / filename
            if _path_exists_safe(old_file):
                try:
                    old_file.unlink()
                    logger.info("Removed old file (rebrand): %s", old_file)
                except OSError as exc:
                    logger.warning("Could not remove old file %s: %s", old_file, exc)

        # Skip canonical dir for current managed files
        if match_dir == canonical_match:
            continue

        for filename in _MANAGED_FILES:
            stale = match_dir / filename
            if _path_exists_safe(stale):
                try:
                    stale.unlink()
                    logger.info("Removed stale file: %s", stale)
                except OSError as exc:
                    logger.warning("Could not remove stale file %s: %s", stale, exc)


def get_match_dir() -> Optional[Path]:
    """Get the Espanso match directory, creating it if necessary.

    Returns:
        Path to the match directory, or None if Espanso config not found.
    """
    config_dir = get_espanso_config_dir()
    if not config_dir:
        return None

    match_dir = config_dir / "match"
    match_dir.mkdir(parents=True, exist_ok=True)
    return match_dir


# ── Section 3: Launcher / shell execution ─────────────────────────────────────
# Generates the Espanso YAML trigger that launches the espansr GUI, handling
# Windows (.pyw), WSL2 (bash -c), and POSIX differences.
# _quote_powershell, _build_windows_launch_params, _resolve_windows_pythonw_path,
# _resolve_windows_gui_command, _resolve_gui_command, _build_posix_launch_params,
# _generate_gui_trigger_file, generate_launcher_file, generate_commands_popup_file


def _quote_powershell(value: str) -> str:
    """Quote a value for use as a PowerShell single-quoted string."""
    return "'" + value.replace("'", "''") + "'"


def _build_windows_launch_params(executable: str, args: list[str]) -> dict[str, str]:
    """Build shell params for a detached launch via PowerShell."""
    quoted_args = ", ".join(_quote_powershell(arg) for arg in args)
    cmd = f"Start-Process -FilePath {_quote_powershell(executable)}"
    if quoted_args:
        cmd += f" -ArgumentList {quoted_args}"
    return {"cmd": cmd, "shell": "powershell"}


def _resolve_windows_pythonw_path(python_executable: str) -> str:
    """Return the sibling pythonw.exe path for Windows-style or native paths."""
    if ":" in python_executable or "\\" in python_executable:
        return str(PureWindowsPath(python_executable).with_name("pythonw.exe"))
    return str(Path(python_executable).with_name("pythonw.exe"))


def _resolve_windows_gui_command(
    binary: Optional[str],
    python_executable: str,
    extra_args: Optional[list[str]] = None,
) -> tuple[str, list[str]]:
    """Prefer pythonw.exe on Windows so GUI launches do not open a console window."""
    extra_args = extra_args or []
    pythonw = _resolve_windows_pythonw_path(python_executable)
    if _path_exists_safe(Path(pythonw)):
        return pythonw, ["-m", "espansr", "gui", *extra_args]
    if binary:
        return binary, ["gui", *extra_args]
    return python_executable, ["-m", "espansr", "gui", *extra_args]


def _resolve_gui_command(
    binary: Optional[str],
    python_executable: str,
    extra_args: Optional[list[str]] = None,
    *,
    wsl_windows_host: bool = False,
) -> tuple[str, list[str]]:
    """Resolve the executable and argv used to launch an espansr GUI surface."""
    extra_args = extra_args or []

    if wsl_windows_host:
        if binary:
            return binary, ["gui", *extra_args]
        return python_executable, ["-m", "espansr", "gui", *extra_args]

    if is_windows():
        return _resolve_windows_gui_command(binary, python_executable, extra_args)

    if binary:
        return binary, ["gui", *extra_args]
    return python_executable, ["-m", "espansr", "gui", *extra_args]


def _build_posix_launch_params(executable: str, args: list[str]) -> dict[str, str]:
    """Build shell params for a detached launch on Unix-like shells."""
    command = shlex.join([executable, *args])
    return {"cmd": f"nohup {command} >/dev/null 2>&1 &"}


def _build_windows_console_launch_params(executable: str, args: list[str]) -> dict[str, str]:
    """Build shell params that run a console command in a window that stays open.

    ``Start-Process`` on a console executable opens a console that closes the
    moment the process exits, so the ``ok`` line and any failure vanish with it.
    Running the command inside ``powershell -NoProfile -NoExit -Command`` keeps
    the window, and therefore the result, on screen until the user closes it.
    """
    inner = "& " + " ".join(_quote_powershell(part) for part in [executable, *args])
    return _build_windows_launch_params("powershell", ["-NoProfile", "-NoExit", "-Command", inner])


# Terminal emulators probed, in order, for a visible `espansr sync` window on
# Linux; the second element is the flag that introduces the command to run.
_POSIX_TERMINALS: tuple[tuple[str, str], ...] = (
    ("x-terminal-emulator", "-e"),
    ("gnome-terminal", "--"),
    ("konsole", "-e"),
    ("xterm", "-e"),
)


def _find_posix_terminal() -> Optional[tuple[str, str]]:
    """Return ``(path, exec_flag)`` for the first available terminal emulator."""
    import shutil

    for name, exec_flag in _POSIX_TERMINALS:
        found = shutil.which(name)
        if found:
            return found, exec_flag
    return None


def _applescript_string(value: str) -> str:
    """Quote a value as an AppleScript string literal."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _build_posix_console_launch_params(
    executable: str,
    args: list[str],
    *,
    log_path: Path,
) -> dict[str, str]:
    """Build shell params for a console command whose result must stay visible.

    Prefers a terminal window (macOS Terminal via osascript, else the first of
    ``_POSIX_TERMINALS``) that waits for Enter after the command so the ok line
    or failure can be read. Without a terminal, output is appended to
    ``log_path`` and ``notify-send`` reports the outcome when it is installed.
    """
    import shutil

    command = shlex.join([executable, *args])
    label = " ".join(args) if args else Path(executable).name

    if get_platform() == "macos":
        launch = shlex.join(
            [
                "osascript",
                "-e",
                f'tell application "Terminal" to do script {_applescript_string(command)}',
                "-e",
                'tell application "Terminal" to activate',
            ]
        )
        return {"cmd": f"nohup {launch} >/dev/null 2>&1 &"}

    terminal = _find_posix_terminal()
    if terminal is not None:
        terminal_path, exec_flag = terminal
        inner = f'{command}; printf "\\n[espansr] Press Enter to close this window"; read -r _'
        launch = shlex.join([terminal_path, exec_flag, "sh", "-c", inner])
        return {"cmd": f"nohup {launch} >/dev/null 2>&1 &"}

    quoted_log = shlex.quote(str(log_path))
    inner = f"{command} >>{quoted_log} 2>&1"
    if shutil.which("notify-send"):
        inner += (
            f'; rc=$?; if [ "$rc" -eq 0 ]; then notify-send espansr "{label} ok"; '
            f'else notify-send espansr "{label} failed (exit $rc), see "{quoted_log}; fi'
        )
    launch = shlex.join(["sh", "-c", inner])
    return {"cmd": f"nohup {launch} >/dev/null 2>&1 &"}


def _write_match_file(output_path: Path, content: dict) -> None:
    """Serialize an Espanso match mapping and replace ``output_path`` atomically."""
    text = yaml.dump(content, default_flow_style=False, allow_unicode=True)
    atomic_write_bytes(output_path, text.encode("utf-8"))


def _generate_gui_trigger_file(
    *,
    filename: str,
    trigger: str,
    gui_args: Optional[list[str]] = None,
    match_dir: Optional[Path] = None,
) -> bool:
    """Generate a managed Espanso shell trigger that launches a GUI surface.

    Args:
        filename: The file name written into the Espanso match directory.
        trigger: The Espanso trigger keyword.
        gui_args: Extra CLI args forwarded to `espansr gui`.
        match_dir: Override match directory (for testing). Uses get_match_dir() if None.

    Returns:
        True if file was written successfully, False otherwise.
    """
    import shutil
    import sys

    gui_args = gui_args or []

    if match_dir is None:
        match_dir = get_match_dir()
    if match_dir is None:
        return False

    # WSL with a Windows-hosted Espanso config needs a Windows-side launcher,
    # but it must still invoke the WSL executable path rather than pythonw.exe.
    wsl_windows_host = is_wsl2() and _is_windows_side_wsl_path(match_dir.parent)

    # Resolve executable and argument vector.
    binary = shutil.which("espansr")
    executable, args = _resolve_gui_command(
        binary,
        sys.executable,
        gui_args,
        wsl_windows_host=wsl_windows_host,
    )

    # Build platform-specific shell command.
    if wsl_windows_host:
        distro = get_wsl_distro_name()
        wsl_args: list[str] = []
        if distro:
            wsl_args.extend(["-d", distro])
        wsl_args.extend(["--", executable, *args])
        shell_params = _build_windows_launch_params("wsl.exe", wsl_args)
    elif is_windows():
        shell_params = _build_windows_launch_params(executable, args)
    else:
        shell_params = _build_posix_launch_params(executable, args)

    content = {
        "matches": [
            {
                "trigger": trigger,
                "replace": "{{output}}",
                "vars": [
                    {
                        "name": "output",
                        "type": "shell",
                        "params": shell_params,
                    }
                ],
            }
        ]
    }

    try:
        output_path = match_dir / filename
        _write_match_file(output_path, content)
        logger.info("Generated GUI trigger at %s", output_path)
        return True
    except Exception as exc:
        logger.warning("Failed to generate GUI trigger file: %s", exc)
        return False


def generate_launcher_file(match_dir: Optional[Path] = None) -> bool:
    """Generate espansr-launcher.yml with a shell trigger to launch the full GUI."""
    config = get_config()
    trigger = config.espanso.launcher_trigger or ":aopen"
    return _generate_gui_trigger_file(
        filename=LAUNCHER_FILE_NAME,
        trigger=trigger,
        match_dir=match_dir,
    )


def generate_commands_popup_file(match_dir: Optional[Path] = None) -> bool:
    """Generate espansr-commands.yml with the hardcoded :coms popup trigger."""
    return _generate_gui_trigger_file(
        filename=COMMANDS_POPUP_FILE_NAME,
        trigger=COMMANDS_POPUP_TRIGGER,
        gui_args=["--view", "commands"],
        match_dir=match_dir,
    )


def _resolve_subcommand(
    binary: Optional[str],
    python_executable: str,
    subcommand_args: list[str],
    *,
    wsl_windows_host: bool = False,
) -> tuple[str, list[str]]:
    """Resolve the executable and argv used to run ``espansr <subcommand>``.

    Unlike :func:`_resolve_gui_command`, this targets the *console* entrypoint
    (no pythonw.exe) so long-running commands like ``sync`` show their progress
    in a window — the whole point of running them over RustDesk/RDP.
    """
    if binary:
        return binary, list(subcommand_args)
    return python_executable, ["-m", "espansr", *subcommand_args]


def _generate_subcommand_trigger_file(
    *,
    filename: str,
    trigger: str,
    subcommand_args: list[str],
    match_dir: Optional[Path] = None,
) -> bool:
    """Generate a managed Espanso shell trigger that runs ``espansr <subcommand>``.

    Args:
        filename: The file name written into the Espanso match directory.
        trigger: The Espanso trigger keyword.
        subcommand_args: CLI args passed to the espansr console entrypoint.
        match_dir: Override match directory (for testing). Uses get_match_dir() if None.

    Returns:
        True if the file was written successfully, False otherwise.
    """
    import shutil
    import sys

    if match_dir is None:
        match_dir = get_match_dir()
    if match_dir is None:
        return False

    # WSL with a Windows-hosted Espanso config needs a Windows-side launch that
    # still invokes the WSL executable through wsl.exe.
    wsl_windows_host = is_wsl2() and _is_windows_side_wsl_path(match_dir.parent)

    binary = shutil.which("espansr")
    executable, args = _resolve_subcommand(
        binary,
        sys.executable,
        subcommand_args,
        wsl_windows_host=wsl_windows_host,
    )

    # The result of a subcommand must stay readable after it finishes: on
    # Windows the command runs inside a PowerShell window that stays open, on
    # POSIX inside a terminal emulator when one exists, else into a log file.
    if wsl_windows_host:
        distro = get_wsl_distro_name()
        wsl_args: list[str] = []
        if distro:
            wsl_args.extend(["-d", distro])
        wsl_args.extend(["--", executable, *args])
        shell_params = _build_windows_console_launch_params("wsl.exe", wsl_args)
    elif is_windows():
        shell_params = _build_windows_console_launch_params(executable, args)
    else:
        log_name = f"{subcommand_args[0] if subcommand_args else 'espansr'}.log"
        shell_params = _build_posix_console_launch_params(
            executable, args, log_path=get_config_dir() / log_name
        )

    content = {
        "matches": [
            {
                "trigger": trigger,
                "replace": "{{output}}",
                "vars": [
                    {
                        "name": "output",
                        "type": "shell",
                        "params": shell_params,
                    }
                ],
            }
        ]
    }

    try:
        output_path = match_dir / filename
        _write_match_file(output_path, content)
        logger.info("Generated subcommand trigger at %s", output_path)
        return True
    except Exception as exc:
        logger.warning("Failed to generate subcommand trigger file: %s", exc)
        return False


def generate_sync_file(match_dir: Optional[Path] = None) -> bool:
    """Generate espansr-sync.yml with a trigger that runs ``espansr sync``."""
    config = get_config()
    trigger = getattr(config.espanso, "sync_trigger", "") or ":sync"
    return _generate_subcommand_trigger_file(
        filename=SYNC_FILE_NAME,
        trigger=trigger,
        subcommand_args=["sync"],
        match_dir=match_dir,
    )


# Tracks the number of templates written by the most recent sync_to_espanso() call.
# The GUI reads this after sync to display a richer feedback message.
_last_sync_count: int = 0


def _sync_bundled_templates_before_espanso(
    dry_run: bool = False,
    templates_dir: Optional[Path] = None,
    bundled_dir: Optional[Path] = None,
) -> bool:
    """Apply bundled template updates before writing Espanso output."""
    from espansr.core.templates import sync_bundled_templates_to_live

    report, result = sync_bundled_templates_to_live(
        templates_dir=templates_dir,
        bundled_dir=bundled_dir,
        dry_run=dry_run,
    )

    for error in report.errors:
        print(f"Error: {error}")

    if report.errors:
        return False

    if result.copied or result.updated or result.migrated or result.retired or result.forced:
        prefix = "[dry-run] " if dry_run else ""
        print(
            f"{prefix}Bundled sync: "
            f"{result.copied} copied, {result.updated} updated, "
            f"{result.migrated} migrated, {result.retired} retired, "
            f"{result.forced} forced"
        )

    if result.skipped_invalid:
        print(
            "Bundled sync skipped invalid local template(s); "
            "run 'espansr starters --apply --force':"
        )
        for entry in result.skipped_invalid:
            print(f"  {entry.filename}")
        return False

    return True


# ── Section 4: Sync entrypoint ────────────────────────────────────────────────
# Orchestrates bundled-template drift application, YAML writing, and
# Espanso daemon restart. Public API: sync_to_espanso().


def sync_to_espanso(
    dry_run: bool = False,
    update_bundled: bool = False,
    templates_dir: Optional[Path] = None,
    bundled_dir: Optional[Path] = None,
) -> bool:
    """Sync templates to Espanso match file.

    Generates a single `espansr.yml` in the Espanso match directory
    containing all templates that have triggers defined.

    After a successful call, ``_last_sync_count`` holds the number
    of templates that were written.

    Args:
        dry_run: If True, print what would be written without writing.
        update_bundled: If True, apply bundled template updates to the live
            template store before generating Espanso output.
        templates_dir: Optional live template directory override, primarily
            used by tests.
        bundled_dir: Optional bundled template directory override, primarily
            used by tests.

    Returns:
        True if sync was successful, False otherwise.
    """
    global _last_sync_count
    _last_sync_count = 0

    if update_bundled and not _sync_bundled_templates_before_espanso(
        dry_run=dry_run,
        templates_dir=templates_dir,
        bundled_dir=bundled_dir,
    ):
        return False

    match_dir = get_match_dir()
    if not match_dir:
        print("Error: Could not find Espanso config directory")
        return False

    if not dry_run:
        clean_stale_espanso_files()

    # Validate before writing
    warnings = validate_all()
    errors = [w for w in warnings if w.severity == "error"]
    non_errors = [w for w in warnings if w.severity != "error"]

    for w in non_errors:
        print(f"Warning [{w.template_name}]: {w.message}")
    for w in errors:
        print(f"Error [{w.template_name}]: {w.message}")

    if errors:
        print(f"Sync aborted: {len(errors)} validation error(s) found")
        return False

    template_manager = get_template_manager()
    matches = []

    for template in template_manager.iter_with_triggers():
        replace_text = _convert_to_espanso_placeholders(template.content, template.variables or [])
        match_entry: dict = {
            "trigger": template.trigger,
            "replace": replace_text,
        }

        if template.variables:
            match_entry["vars"] = [_build_espanso_var_entry(var) for var in template.variables]

        matches.append(match_entry)

    output_path = match_dir / "espansr.yml"

    if not matches:
        if dry_run:
            print(f"[dry-run] No templates with triggers found; would leave {output_path} empty")
            return True

        removed_stale_output = False
        try:
            if output_path.exists():
                output_path.unlink()
                removed_stale_output = True
        except OSError as e:
            print(f"Error removing Espanso file: {e}")
            return False

        if removed_stale_output:
            print(f"No templates with triggers found; removed {output_path}")
            if is_wsl2():
                _restart_espanso_wsl2()
            elif is_windows():
                if restart_espanso():
                    print("Espanso restarted successfully.")
                else:
                    print(
                        "Note: Run 'espanso restart' from a new PowerShell window "
                        "to reload triggers."
                    )
        else:
            print("No templates with triggers found")
        return True

    if dry_run:
        print(f"[dry-run] Would write {len(matches)} trigger(s) to {output_path}")
        for m in matches:
            print(f"  {m['trigger']}: {m['replace'][:60]}")
        return True

    try:
        _write_match_file(output_path, {"matches": matches})

        _last_sync_count = len(matches)
        print(f"Synced {len(matches)} trigger(s) to {output_path}")

        # Restart Espanso so new triggers become active immediately.
        # WSL2: file writes via /mnt/c/ bypass the Windows file watcher — use PowerShell restart.
        # Windows native: file-watcher polling is unreliable for newly added template files.
        if is_wsl2():
            _restart_espanso_wsl2()
        elif is_windows():
            if restart_espanso():
                print("Espanso restarted successfully.")
            else:
                print(
                    "Note: Run 'espanso restart' from a new PowerShell window to reload triggers."
                )

        return True
    except Exception as e:
        print(f"Error writing Espanso file: {e}")
        return False


# ── Section 5: Process management ────────────────────────────────────────────
# Restarts the Espanso daemon after sync. Handles WSL2 (via powershell.exe)
# and Windows native (probes %LOCALAPPDATA%\Programs\Espanso\espanso.cmd).
# _restart_espanso_wsl2, _find_espanso_executable, restart_espanso


_NOT_WORD_RE = re.compile(r"\bnot\b", re.IGNORECASE)

# `espanso status` run on the Windows host from inside WSL. `cd C:/` keeps
# PowerShell off the UNC path of the WSL working directory.
_WSL_STATUS_ARGV = ["powershell.exe", "-NoProfile", "-Command", "cd C:/; espanso status"]


def _output_reports_running(output: str) -> bool:
    """Return True when ``espanso status`` output carries a positive running line.

    Espanso prints ``espanso is running`` or ``espanso is not running``; a bare
    keyword match would accept the negative form, so a line only counts when it
    mentions running without a ``not``.
    """
    for line in output.splitlines():
        if "running" in line.lower() and not _NOT_WORD_RE.search(line):
            return True
    return False


def _run_quiet(argv: list[str], *, timeout: float) -> subprocess.CompletedProcess:
    """Run a process with captured output and, on Windows, no console window."""
    kwargs: dict = {
        "capture_output": True,
        "text": True,
        "timeout": timeout,
        "check": False,
    }
    if is_windows():
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(argv, **kwargs)


def _run_detached(argv: list[str], *, timeout: float) -> subprocess.CompletedProcess:
    """Run a process without capturing its output.

    Espanso's restart and service-start commands spawn the long-lived daemon,
    which inherits any stdout/stderr pipes handed to the command. With captured
    pipes ``subprocess.run`` then waits for an end-of-file that never arrives
    while the daemon lives, even after the CLI itself has exited. Routing all
    three standard handles to the null device leaves nothing to inherit, so
    the call returns as soon as the CLI exits.
    """
    kwargs: dict = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "timeout": timeout,
        "check": False,
    }
    if is_windows():
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(argv, **kwargs)


def _wait_for_espanso_running(
    status_argv: list[str],
    *,
    attempts: int = 5,
    delay: float = 1.0,
) -> bool:
    """Poll ``espanso status`` until it reports running (or the attempts run out)."""
    import time

    for attempt in range(attempts):
        try:
            result = _run_quiet(status_argv, timeout=10)
        except (OSError, subprocess.SubprocessError):
            return False
        if result.returncode == 0 and _output_reports_running(result.stdout + result.stderr):
            return True
        if attempt < attempts - 1:
            time.sleep(delay)
    return False


def _restart_espanso_wsl2() -> None:
    """Restart the Windows-side Espanso from WSL2 and verify it came back up."""
    try:
        _run_detached(
            ["powershell.exe", "-NoProfile", "-Command", "cd C:/; espanso service stop"],
            timeout=10,
        )
        result = _run_detached(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "cd C:/; Start-Process espanso -ArgumentList 'service','start' -WindowStyle Hidden",
            ],
            timeout=10,
        )
        if result.returncode == 0 and _wait_for_espanso_running(_WSL_STATUS_ARGV):
            print("Espanso restarted successfully.")
            return
    except (OSError, subprocess.SubprocessError):
        pass
    print("Note: Run 'espanso restart' from Windows PowerShell to reload triggers.")


def _find_espanso_executable() -> str | None:
    """Return the path to the Espanso executable, or None if not found.

    Checks (in order):
    1. PATH (shutil.which)
    2. Known Windows per-user install location: %LOCALAPPDATA%/Programs/Espanso/espanso.cmd
    """
    import os
    import shutil

    if found := shutil.which("espanso"):
        return found

    localappdata = os.environ.get("LOCALAPPDATA", "")
    if localappdata:
        candidate = Path(localappdata) / "Programs" / "Espanso" / "espanso.cmd"
        if candidate.exists():
            return str(candidate)

    return None


def restart_espanso() -> bool:
    """Restart the Espanso daemon and verify it reports running afterwards.

    Returns:
        True only when the restart command succeeded and ``espanso status``
        subsequently reported the daemon running. Prints why when it did not;
        returns False silently only when no Espanso executable is available.
    """
    if is_wsl2():
        restart_argv = ["powershell.exe", "-NoProfile", "-Command", "cd C:/; espanso restart"]
        status_argv = _WSL_STATUS_ARGV
        hint = "run 'espanso restart' from Windows PowerShell"
    else:
        exe = _find_espanso_executable()
        if not exe:
            return False
        restart_argv = [exe, "restart"]
        status_argv = [exe, "status"]
        hint = "run 'espanso restart' manually"

    try:
        result = _run_detached(restart_argv, timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"Espanso restart failed ({exc}); {hint}.")
        return False
    if result.returncode != 0:
        detail = ((result.stderr or result.stdout) or "").strip()
        suffix = f": {detail}" if detail else ""
        print(f"Espanso restart failed (exit {result.returncode}){suffix}; {hint}.")
        return False
    if not _wait_for_espanso_running(status_argv):
        print(f"Espanso did not report running after the restart; {hint}.")
        return False
    return True


# ── Section 6: Espanso default.yml managed block ─────────────────────────────
# Over RustDesk/RDP the keys you type are *software-injected* on the host with no
# physical HID source. Espanso's default `win32_exclude_orphan_events: true`
# discards exactly those events, so triggers like :coms are never even detected.
# Setting it false lets Espanso see RustDesk/RDP input — this is THE fix for
# "commands don't fire over RustDesk." We also switch to the clipboard backend so
# text expansions paste cleanly instead of garbling, and quiet the tray. Because
# the clipboard backend restores the user's prior clipboard shortly after
# pasting, we also disable that restore so it never races the paste. Mirrors
# install.sh's Linux/Wayland fix; here the lever is Espanso's config/default.yml.
# All keys are espansr-managed and reversible via the --revert path.
_REMOTE_DESKTOP_KEYS: dict = {
    # Detection: stop espanso from filtering out RustDesk/RDP-injected keystrokes.
    "win32_exclude_orphan_events": False,
    # Injection: paste expansions instead of per-key typing (clean over remote).
    "backend": "Clipboard",
    # Clipboard safety: the clipboard backend copies the expansion, sends paste,
    # then restores the prior clipboard ~300ms later. In apps that paste
    # asynchronously (browser/Electron chats) that restore wins the race and the
    # app pastes the *previously copied* text instead of the expansion. Disabling
    # the restore removes the race so the expansion always wins (the clipboard
    # then simply holds the expanded text).
    "preserve_clipboard": False,
    "show_icon": False,
    "show_notifications": False,
    "key_delay": 30,
    "backspace_delay": 30,
}

# espansr templates all exceed Espanso's clipboard_threshold, so every expansion
# pastes via the clipboard. Keep the clipboard (preserve_clipboard) but restore
# it late enough that the paste finished AND the target app released its clipboard
# lock; large templates in slow apps held the clipboard past a 700ms restore, so
# the restore failed and left the template behind (clipboard "clobbered").
# win32_exclude_orphan_events must be false so triggers still fire when you remote
# INTO this machine (RDP/RustDesk inject keystrokes Espanso would otherwise drop).
_WORKSTATION_KEYS: dict = {
    "win32_exclude_orphan_events": False,
    "preserve_clipboard": True,
    "restore_clipboard_delay": 1500,
}

# espansr owns exactly ONE marked block in default.yml and edits the file as
# text. Every byte outside the block (comments, key order, `toggle_key: OFF`,
# quoted times) is preserved verbatim; a YAML load/dump round trip would drop
# the comments and retype YAML 1.1 scalars (`OFF` -> false, `12:30` -> 750).
#
#   # espansr-managed BEGIN (host) - reapply: ...; revert: ...
#   # espansr-prev: backend: Inject        <- the user's original line, verbatim
#   win32_exclude_orphan_events: false
#   backend: Clipboard
#   ...
#   # espansr-managed END
#
# A managed key that the user already set at top level is moved into the block
# as an `espansr-prev` comment (Espanso rejects duplicate top-level keys) and
# put back, in place of the block, by --revert. The first modification of a
# file that has no block yet is preceded by a one-time copy to
# `default.yml.espansr-orig` next to it.
MANAGED_BLOCK_BEGIN_PREFIX = "# espansr-managed BEGIN"
MANAGED_BLOCK_END = "# espansr-managed END"
_MANAGED_PREV_PREFIX = "# espansr-prev: "
# Mode-specific BEGIN line prefixes (the written line appends a reapply/revert hint).
REMOTE_DESKTOP_MARKER = f"{MANAGED_BLOCK_BEGIN_PREFIX} (host)"
WORKSTATION_MARKER = f"{MANAGED_BLOCK_BEGIN_PREFIX} (workstation)"
# First-line markers written by earlier espansr versions, which were followed by
# bare managed keys and no END marker. Recognized so those files migrate to the
# block layout on the next apply and can still be reverted.
LEGACY_REMOTE_DESKTOP_MARKER = "# espansr-remote-desktop"
LEGACY_WORKSTATION_MARKER = "# espansr-workstation"
ORIGINAL_BACKUP_SUFFIX = ".espansr-orig"

_MANAGED_MODES: dict[str, dict] = {
    "host": _REMOTE_DESKTOP_KEYS,
    "workstation": _WORKSTATION_KEYS,
}
_MODE_HINTS = {
    "host": (
        "reapply: espansr configure-remote-desktop; "
        "revert: espansr configure-remote-desktop --revert"
    ),
    "workstation": (
        "reapply: espansr configure-remote-desktop --local; "
        "revert: espansr configure-remote-desktop --revert"
    ),
}
_BEGIN_MODE_RE = re.compile(r"^# espansr-managed BEGIN \((host|workstation)\)")
# A top-level YAML mapping key at column 0: `key:`, `"key":`, or `'key':`
# followed by a space or the end of the line.
_TOP_LEVEL_KEY_RE = re.compile(
    r"""^(?P<quote>["']?)(?P<key>[A-Za-z0-9_][A-Za-z0-9_.\-]*)(?P=quote)[ \t]*:(?:[ \t]|$)"""
)
_LINE_RE = re.compile(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+$")


def get_espanso_default_config_path(config_dir: Optional[Path] = None) -> Optional[Path]:
    """Return ``<config_dir>/config/default.yml``.

    Resolves the Espanso config dir when ``config_dir`` is None. Returns None
    only when no Espanso config directory can be located.
    """
    if config_dir is None:
        config_dir = get_espanso_config_dir()
    if config_dir is None:
        return None
    return Path(config_dir) / "config" / "default.yml"


@dataclass
class _ManagedLayout:
    """Where espansr's managed region sits in a default.yml text."""

    mode: Optional[str] = None  # "host" | "workstation" | None when unknown
    legacy: bool = False  # True for the pre-block first-line marker layout
    block_start: int = -1  # index of the BEGIN line (block layout only)
    block_end: int = -1  # index one past the END line (block layout only)
    prev_lines: list[str] = field(default_factory=list)  # recorded original lines

    @property
    def is_managed(self) -> bool:
        return self.block_start >= 0 or self.legacy


def _split_keepends(text: str) -> list[str]:
    """Split on ``\\r\\n``, ``\\r`` or ``\\n`` only, keeping the line endings."""
    return [match.group(0) for match in _LINE_RE.finditer(text)]


def _line_body(line: str) -> str:
    return line.rstrip("\r\n")


def _newline_for(lines: list[str]) -> str:
    return "\r\n" if any(line.endswith("\r\n") for line in lines) else "\n"


def _parse_top_level_key(body: str) -> Optional[str]:
    match = _TOP_LEVEL_KEY_RE.match(body)
    return match.group("key") if match else None


def _is_continuation(line: str) -> bool:
    """True for an indented, non-blank line (part of the preceding key's value)."""
    body = _line_body(line)
    return bool(body.strip()) and body[0] in " \t"


def _managed_begin_line(mode: str) -> str:
    return f"{MANAGED_BLOCK_BEGIN_PREFIX} ({mode}) - {_MODE_HINTS[mode]}"


def _render_managed_key(key: str, value) -> str:
    """Render one managed key as a YAML line (PyYAML quotes where needed)."""
    dumped = yaml.safe_dump(
        {key: value}, default_flow_style=False, sort_keys=False, allow_unicode=True
    )
    return dumped.rstrip("\r\n")


def _parse_managed_layout(lines: list[str]) -> _ManagedLayout:
    """Locate the managed block (or legacy first-line marker) in ``lines``."""
    layout = _ManagedLayout()
    for index, line in enumerate(lines):
        body = _line_body(line).lstrip("\ufeff")
        if not body.startswith(MANAGED_BLOCK_BEGIN_PREFIX):
            continue
        match = _BEGIN_MODE_RE.match(body)
        layout.mode = match.group(1) if match else None
        layout.block_start = index
        layout.block_end = len(lines)  # a block missing its END runs to the end
        for later in range(index + 1, len(lines)):
            inner = _line_body(lines[later])
            if inner.strip() == MANAGED_BLOCK_END:
                layout.block_end = later + 1
                break
            if inner.startswith(_MANAGED_PREV_PREFIX):
                layout.prev_lines.append(inner[len(_MANAGED_PREV_PREFIX) :])
        return layout

    for line in lines:
        body = _line_body(line).lstrip("\ufeff")
        if body.startswith(LEGACY_REMOTE_DESKTOP_MARKER):
            layout.mode, layout.legacy = "host", True
            return layout
        if body.startswith(LEGACY_WORKSTATION_MARKER):
            layout.mode, layout.legacy = "workstation", True
            return layout
    return layout


def _line_holds_espansr_value(body: str, managed: dict) -> bool:
    """True when a bare top-level line carries exactly the value espansr wrote."""
    key = _parse_top_level_key(body)
    if key is None or key not in managed:
        return False
    try:
        parsed = yaml.safe_load(body)
    except yaml.YAMLError:
        return False
    return isinstance(parsed, dict) and parsed.get(key) == managed[key]


def _extract_top_level_lines(lines: list[str], should_extract) -> tuple[list[str], list[str]]:
    """Split ``lines`` into (kept lines, extracted line bodies).

    ``should_extract`` receives the body of each column-0 line; an extracted
    line takes its indented continuation lines with it, verbatim.
    """
    kept: list[str] = []
    extracted: list[str] = []
    index = 0
    while index < len(lines):
        body = _line_body(lines[index])
        if index == 0:
            body = body.lstrip("\ufeff")
        if should_extract(body):
            extracted.append(body)
            index += 1
            while index < len(lines) and _is_continuation(lines[index]):
                extracted.append(_line_body(lines[index]))
                index += 1
            continue
        kept.append(lines[index])
        index += 1
    return kept, extracted


def _revert_lines(lines: list[str], layout: _ManagedLayout) -> list[str]:
    """Remove espansr's managed region and put the recorded originals back."""
    if layout.legacy:
        managed = _MANAGED_MODES[layout.mode]
        markers = (LEGACY_REMOTE_DESKTOP_MARKER, LEGACY_WORKSTATION_MARKER)
        without_marker = [
            line for line in lines if not _line_body(line).lstrip("\ufeff").startswith(markers)
        ]
        # The old layout recorded nothing, so only lines still holding the
        # value espansr wrote are espansr's; a re-customized value stays.
        kept, _ = _extract_top_level_lines(
            without_marker, lambda body: _line_holds_espansr_value(body, managed)
        )
        return kept

    newline = _newline_for(lines)
    before = lines[: layout.block_start]
    after = lines[layout.block_end :]
    restored = [prev + newline for prev in layout.prev_lines]
    return before + restored + after


def _apply_lines(lines: list[str], mode: str) -> list[str]:
    """Return ``lines`` with the managed block for ``mode`` as the only espansr region."""
    layout = _parse_managed_layout(lines)
    body = _revert_lines(lines, layout) if layout.is_managed else list(lines)
    managed = _MANAGED_MODES[mode]
    body, prev_lines = _extract_top_level_lines(
        body, lambda text: _parse_top_level_key(text) in managed
    )
    newline = _newline_for(lines)
    if body and not body[-1].endswith(("\n", "\r")):
        body[-1] = body[-1] + newline
    block = [_managed_begin_line(mode) + newline]
    block.extend(f"{_MANAGED_PREV_PREFIX}{prev}{newline}" for prev in prev_lines)
    block.extend(_render_managed_key(key, value) + newline for key, value in managed.items())
    block.append(MANAGED_BLOCK_END + newline)
    return body + block


def _apply_managed_text(text: str, mode: str) -> str:
    """Text-level apply: keep every byte outside the managed block as it was."""
    result = "".join(_apply_lines(_split_keepends(text), mode))
    if text.startswith("\ufeff") and not result.startswith("\ufeff"):
        result = "\ufeff" + result
    return result


def _revert_managed_text(text: str) -> tuple[str, bool]:
    """Text-level revert; the flag reports whether a managed region was found."""
    lines = _split_keepends(text)
    layout = _parse_managed_layout(lines)
    if not layout.is_managed:
        return text, False
    result = "".join(_revert_lines(lines, layout))
    if text.startswith("\ufeff") and result and not result.startswith("\ufeff"):
        result = "\ufeff" + result
    return result, True


def _read_default_config_text(path: Path) -> str:
    # surrogateescape keeps undecodable bytes intact so they are written back unchanged.
    return path.read_bytes().decode("utf-8", errors="surrogateescape")


def _write_default_config_text(path: Path, text: str) -> None:
    atomic_write_bytes(path, text.encode("utf-8", errors="surrogateescape"))


def _original_backup_path(path: Path) -> Path:
    return path.with_name(path.name + ORIGINAL_BACKUP_SUFFIX)


def _ensure_original_backup(path: Path) -> bool:
    """Copy the user's pre-espansr default.yml next to it, once, before the first edit."""
    backup = _original_backup_path(path)
    if backup.exists():
        return True
    try:
        atomic_copy(path, backup)
    except OSError as exc:
        logger.warning("Could not back up %s to %s: %s", path, backup, exc)
        return False
    logger.info("Backed up original %s to %s", path.name, backup)
    return True


def _warn_if_not_mapping(path: Path, text: str) -> None:
    """Warn when default.yml does not parse as a mapping (Espanso would reject it)."""
    try:
        loaded = yaml.safe_load(text)
    except Exception as exc:  # PyYAML raises several error types; never fail here
        logger.warning(
            "%s is not valid YAML after applying the espansr block (%s); Espanso may "
            "reject it. The original is kept at %s",
            path,
            exc,
            _original_backup_path(path),
        )
        return
    if loaded is not None and not isinstance(loaded, dict):
        logger.warning(
            "%s is not a YAML mapping; Espanso may reject it. The original is kept at %s",
            path,
            _original_backup_path(path),
        )


def _resolve_default_config_path(config_dir: Optional[Path], purpose: str) -> Optional[Path]:
    if config_dir is None:
        config_dir = get_espanso_config_dir()
    if config_dir is None:
        logger.warning("Espanso config directory not found; skipping %s", purpose)
        return None
    return get_espanso_default_config_path(config_dir)


def _apply_managed_default_config(path: Path, mode: str, *, restart: bool) -> bool:
    """Write the managed block for ``mode`` into ``path``, creating the file if needed."""
    text = ""
    if path.exists():
        try:
            text = _read_default_config_text(path)
        except OSError as exc:
            logger.warning("Could not read %s: %s", path, exc)
            return False
        if not _parse_managed_layout(_split_keepends(text)).is_managed:
            if not _ensure_original_backup(path):
                return False
    new_text = _apply_managed_text(text, mode)
    try:
        _write_default_config_text(path, new_text)
    except OSError as exc:
        logger.warning("Could not write %s config to %s: %s", mode, path, exc)
        return False
    _warn_if_not_mapping(path, new_text)
    if restart:
        restart_espanso()
    return True


def _revert_managed_default_config(path: Path, *, restart: bool) -> bool:
    """Remove the managed block (either mode, or the legacy layout) from ``path``."""
    if not path.exists():
        return True
    try:
        text = _read_default_config_text(path)
    except OSError as exc:
        logger.warning("Could not read %s: %s", path, exc)
        return False
    new_text, changed = _revert_managed_text(text)
    if not changed:
        logger.info("No espansr-managed block in %s; nothing to revert", path)
        return True
    try:
        if new_text.strip("\ufeff \t\r\n"):
            _write_default_config_text(path, new_text)
        else:
            path.unlink()  # espansr created the file; leave nothing behind
    except OSError as exc:
        logger.warning("Could not revert espansr-managed config in %s: %s", path, exc)
        return False
    if restart:
        restart_espanso()
    return True


def apply_remote_desktop_config(
    config_dir: Optional[Path] = None,
    *,
    revert: bool = False,
    restart: bool = True,
) -> bool:
    """Apply (or with ``revert`` remove) espansr's remote-desktop host block in default.yml.

    Idempotent and text-preserving: only the managed block changes, every
    other byte of the file stays as it was. ``revert`` removes the block in
    either mode (host or workstation) and restores the recorded original lines.

    Returns True on success or no-op; False only when Espanso config is missing
    or the file could not be read or written.
    """
    path = _resolve_default_config_path(config_dir, "remote-desktop config")
    if path is None:
        return False
    if revert:
        return _revert_managed_default_config(path, restart=restart)
    return _apply_managed_default_config(path, "host", restart=restart)


def apply_workstation_config(
    config_dir: Optional[Path] = None,
    *,
    restart: bool = True,
) -> bool:
    """Tune Espanso so espansr expansions paste correctly while preserving the
    user's clipboard, for a machine you sit at physically (not remote into).

    Replaces any host block first (its recorded originals go back into the
    file) so a former remote-desktop host becomes a clean workstation.
    """
    path = _resolve_default_config_path(config_dir, "workstation config")
    if path is None:
        return False
    return _apply_managed_default_config(path, "workstation", restart=restart)


def get_managed_default_config_mode(config_dir: Optional[Path] = None) -> Optional[str]:
    """Return ``"host"`` or ``"workstation"`` when default.yml carries an espansr block.

    Recognizes the block layout and the legacy first-line markers. Returns
    None when the file is missing, unreadable, or not managed by espansr.
    """
    path = get_espanso_default_config_path(config_dir)
    if path is None or not path.exists():
        return None
    try:
        text = _read_default_config_text(path)
    except OSError:
        return None
    layout = _parse_managed_layout(_split_keepends(text))
    return layout.mode if layout.is_managed else None


def default_config_has_remote_desktop_marker(config_dir: Optional[Path] = None) -> bool:
    """Return True if Espanso's default.yml is managed in remote-desktop host mode."""
    return get_managed_default_config_mode(config_dir) == "host"


class EspansoManager:
    """High-level manager for Espanso integration."""

    def __init__(self):
        """Initialize, detecting config and match directories."""
        self.config_dir = get_espanso_config_dir()
        self.match_dir = get_match_dir()

    def is_available(self) -> bool:
        """Return True if Espanso config directory was found."""
        return self.match_dir is not None

    def sync(self) -> int:
        """Sync templates to Espanso and return count of synced templates."""
        if not self.match_dir:
            return 0

        clean_stale_espanso_files()

        template_manager = get_template_manager()
        matches = []

        for template in template_manager.iter_with_triggers():
            replace_text = _convert_to_espanso_placeholders(
                template.content, template.variables or []
            )
            match_entry: dict = {
                "trigger": template.trigger,
                "replace": replace_text,
            }

            if template.variables:
                match_entry["vars"] = [_build_espanso_var_entry(var) for var in template.variables]

            matches.append(match_entry)

        if not matches:
            return 0

        output_path = self.match_dir / "espansr.yml"
        try:
            _write_match_file(output_path, {"matches": matches})
            return len(matches)
        except Exception:
            return 0

    def generate_launcher(self) -> bool:
        """Generate the Espanso launcher trigger file."""
        return generate_launcher_file(self.match_dir)

    def generate_commands_popup(self) -> bool:
        """Generate the Espanso commands popup trigger file."""
        return generate_commands_popup_file(self.match_dir)

    def restart(self) -> bool:
        """Restart the Espanso daemon."""
        return restart_espanso()


# Global instance
_espanso_manager: Optional[EspansoManager] = None


def get_espanso_manager() -> EspansoManager:
    """Get the global EspansoManager instance."""
    global _espanso_manager
    if _espanso_manager is None:
        _espanso_manager = EspansoManager()
    return _espanso_manager
