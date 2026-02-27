"""Espanso integration for automatr-espanso.

Generates Espanso match files from templates that have triggers defined.
Supports Linux, WSL2 (auto-detects Windows Espanso config path), and macOS.
"""

import logging
import platform
from pathlib import Path
from typing import Optional

import yaml

from automatr_espanso.core.config import get_config, save_config
from automatr_espanso.core.platform import get_windows_username, get_wsl_distro_name, is_wsl2
from automatr_espanso.core.templates import get_template_manager

logger = logging.getLogger(__name__)

# File names managed by automatr — only these are cleaned up
_MANAGED_FILES = ("automatr-espanso.yml", "automatr-launcher.yml")


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

    Returns:
        List of candidate paths (may or may not exist on disk).
    """
    candidates: list[Path] = []
    system = platform.system()

    if is_wsl2():
        win_user = get_windows_username()
        if win_user:
            candidates.extend([
                Path(f"/mnt/c/Users/{win_user}/.config/espanso"),
                Path(f"/mnt/c/Users/{win_user}/.espanso"),
                Path(f"/mnt/c/Users/{win_user}/AppData/Roaming/espanso"),
            ])

    if system == "Linux":
        candidates.extend([
            Path.home() / ".config" / "espanso",
            Path.home() / ".espanso",
        ])
    elif system == "Darwin":
        candidates.extend([
            Path.home() / "Library" / "Application Support" / "espanso",
            Path.home() / ".config" / "espanso",
        ])
    elif system == "Windows":
        import os

        appdata = os.environ.get("APPDATA", "")
        if appdata:
            candidates.append(Path(appdata) / "espanso")
        candidates.append(Path.home() / ".espanso")

    return candidates


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
        if path.exists():
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
        if candidate.exists():
            # Persist the discovered path
            config.espanso.config_path = str(candidate)
            save_config(config)
            return candidate

    return None


def clean_stale_espanso_files() -> None:
    """Remove automatr-managed files from non-canonical Espanso config dirs.

    Scans all known Espanso config candidate paths and deletes
    `automatr-espanso.yml` and `automatr-launcher.yml` from any `match/`
    directory that is NOT the canonical one.

    Silent on permission errors — logs a warning but does not raise.
    Does nothing if no canonical directory is found.
    """
    canonical = get_espanso_config_dir()
    if canonical is None:
        return

    canonical_match = canonical / "match"

    for candidate in _get_candidate_paths():
        match_dir = candidate / "match"

        # Skip the canonical dir and non-existent dirs
        if match_dir == canonical_match or not match_dir.is_dir():
            continue

        for filename in _MANAGED_FILES:
            stale = match_dir / filename
            if stale.exists():
                try:
                    stale.unlink()
                    logger.info("Removed stale file: %s", stale)
                except PermissionError as exc:
                    logger.warning(
                        "Could not remove stale file %s: %s", stale, exc
                    )


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


def generate_launcher_file(match_dir: Optional[Path] = None) -> bool:
    """Generate automatr-launcher.yml with a shell trigger to launch the GUI.

    Args:
        match_dir: Override match directory (for testing). Uses get_match_dir() if None.

    Returns:
        True if file was written successfully, False otherwise.
    """
    import shutil
    import sys

    if match_dir is None:
        match_dir = get_match_dir()
    if match_dir is None:
        return False

    config = get_config()
    trigger = config.espanso.launcher_trigger or ":aopen"

    # Resolve binary path
    binary = shutil.which("automatr-espanso")
    if binary:
        gui_cmd = f"{binary} gui"
    else:
        gui_cmd = f"{sys.executable} -m automatr_espanso gui"

    # Build platform-specific shell command
    if is_wsl2():
        distro = get_wsl_distro_name()
        if distro:
            cmd = f"wsl.exe -d {distro} -- {gui_cmd} &"
        else:
            cmd = f"wsl.exe -- {gui_cmd} &"
    else:
        cmd = f"{gui_cmd} &"

    content = {
        "matches": [
            {
                "trigger": trigger,
                "replace": "{{output}}",
                "vars": [
                    {
                        "name": "output",
                        "type": "shell",
                        "params": {"cmd": cmd},
                    }
                ],
            }
        ]
    }

    try:
        output_path = match_dir / "automatr-launcher.yml"
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(content, f, default_flow_style=False, allow_unicode=True)
        logger.info("Generated launcher trigger at %s", output_path)
        return True
    except Exception as exc:
        logger.warning("Failed to generate launcher file: %s", exc)
        return False


def sync_to_espanso() -> bool:
    """Sync templates to Espanso match file.

    Generates a single `automatr-espanso.yml` in the Espanso match directory
    containing all templates that have triggers defined.

    Returns:
        True if sync was successful, False otherwise.
    """
    match_dir = get_match_dir()
    if not match_dir:
        print("Error: Could not find Espanso config directory")
        return False

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
            match_entry["vars"] = [
                _build_espanso_var_entry(var) for var in template.variables
            ]

        matches.append(match_entry)

    if not matches:
        print("No templates with triggers found")
        return True

    output_path = match_dir / "automatr-espanso.yml"
    try:
        content = {"matches": matches}
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(content, f, default_flow_style=False, allow_unicode=True)

        print(f"Synced {len(matches)} trigger(s) to {output_path}")

        # WSL2: file writes via /mnt/c/ don't trigger Windows file watcher — restart Espanso
        if is_wsl2():
            _restart_espanso_wsl2()

        return True
    except Exception as e:
        print(f"Error writing Espanso file: {e}")
        return False


def _restart_espanso_wsl2() -> None:
    """Restart Espanso via PowerShell (WSL2 context)."""
    import subprocess

    try:
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", "cd C:/; espanso service stop"],
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


def restart_espanso() -> bool:
    """Restart the Espanso daemon.

    Returns:
        True if restart was successful, False otherwise.
    """
    import shutil
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

    if shutil.which("espanso"):
        try:
            subprocess.run(["espanso", "restart"], capture_output=True, timeout=10)
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
                match_entry["vars"] = [
                    _build_espanso_var_entry(var) for var in template.variables
                ]

            matches.append(match_entry)

        if not matches:
            return 0

        output_path = self.match_dir / "automatr-espanso.yml"
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
