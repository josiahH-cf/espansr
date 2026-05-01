"""Espanso integration for espansr.

Generates Espanso match files from templates that have triggers defined.
Supports Linux, WSL2 (auto-detects Windows Espanso config path), and macOS.
"""

import logging
import shlex
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
from typing import Optional

import yaml

from espansr.core.command_catalog import COMMANDS_POPUP_TRIGGER
from espansr.core.config import get_config, save_config
from espansr.core.platform import (
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

_MANAGED_FILES = ("espansr.yml", LAUNCHER_FILE_NAME, COMMANDS_POPUP_FILE_NAME)

# Old file names from before the rebrand — cleaned up on sync
_OLD_MANAGED_FILES = ("automatr-espanso.yml", "automatr-launcher.yml")


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
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(content, f, default_flow_style=False, allow_unicode=True)
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

    if result.copied or result.updated or result.forced:
        prefix = "[dry-run] " if dry_run else ""
        print(
            f"{prefix}Bundled sync: "
            f"{result.copied} copied, {result.updated} updated, {result.forced} forced"
        )

    if result.skipped_invalid:
        print("Bundled sync skipped invalid local template(s); run sync-bundled --apply --force:")
        for entry in result.skipped_invalid:
            print(f"  {entry.filename}")
        return False

    return True


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

    if not matches:
        print("No templates with triggers found")
        return True

    output_path = match_dir / "espansr.yml"

    if dry_run:
        print(f"[dry-run] Would write {len(matches)} trigger(s) to {output_path}")
        for m in matches:
            print(f"  {m['trigger']}: {m['replace'][:60]}")
        return True

    try:
        content = {"matches": matches}
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(content, f, default_flow_style=False, allow_unicode=True)

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
                print("Note: Run 'espanso restart' from a new PowerShell window to reload triggers.")

        return True
    except Exception as e:
        print(f"Error writing Espanso file: {e}")
        return False


def _restart_espanso_wsl2() -> None:
    """Restart Espanso via PowerShell (WSL2 context)."""
    import subprocess

    try:
        subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "cd C:/; espanso service stop",
            ],
            capture_output=True,
            timeout=10,
        )
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "cd C:/; Start-Process espanso -ArgumentList 'service','start' -WindowStyle Hidden",
            ],
            capture_output=True,
            timeout=10,
        )
        if result.returncode == 0:
            print("Espanso restarted successfully.")
        else:
            print("Note: Run 'espanso restart' from Windows PowerShell to reload triggers.")
    except Exception:
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
    """Restart the Espanso daemon.

    Returns:
        True if restart was successful, False otherwise.
    """
    import subprocess

    if is_wsl2():
        try:
            subprocess.run(
                ["powershell.exe", "-Command", "espanso restart"],
                capture_output=True,
                timeout=10,
            )
            return True
        except Exception:
            pass

    exe = _find_espanso_executable()
    if exe:
        try:
            kwargs: dict = {"capture_output": True, "timeout": 15}
            if is_windows():
                import subprocess as _sp

                kwargs["creationflags"] = _sp.CREATE_NO_WINDOW
            subprocess.run([exe, "restart"], **kwargs)
            return True
        except Exception:
            pass

    return False


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
            content = {"matches": matches}
            with open(output_path, "w", encoding="utf-8") as f:
                yaml.dump(content, f, default_flow_style=False, allow_unicode=True)
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
