"""orchestratr integration for espansr.

Generates an orchestratr app manifest and provides machine-readable
status output so orchestratr can discover, launch, and health-check espansr.

This module is passive — it writes a YAML manifest file and provides
a JSON status helper. espansr never imports or depends on orchestratr code.
"""

import json
from pathlib import Path

import yaml

from espansr import __version__
from espansr.core.config import get_config, get_config_dir, get_templates_dir
from espansr.core.platform import get_platform, get_wsl_distro_name
from espansr.integrations.espanso import get_espanso_config_dir

MANIFEST_FILENAME = "orchestratr.yml"


def generate_manifest(config_dir: Path) -> Path:
    """Generate the orchestratr app manifest in the given config directory.

    The manifest is a declarative YAML file that tells orchestratr how to
    discover, launch, and health-check espansr. It is idempotent — calling
    this function multiple times produces the same file.

    Args:
        config_dir: The espansr config directory where the manifest is written.

    Returns:
        The path to the written manifest file.
    """
    platform = get_platform()
    launch_cmd = _build_launch_command(platform)
    ready_cmd = _build_ready_command(platform)

    manifest = {
        "name": "espansr",
        "description": "Espanso template manager",
        "version": __version__,
        "launch": {
            "command": launch_cmd,
        },
        "ready_cmd": ready_cmd,
        "ready_timeout_ms": 3000,
        "hotkey": {
            "suggested_chord": "e",
        },
    }

    manifest_path = config_dir / MANIFEST_FILENAME
    with open(manifest_path, "w", encoding="utf-8") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)

    return manifest_path


def manifest_needs_update(config_dir: Path) -> bool:
    """Check whether the orchestratr manifest is missing or outdated.

    Args:
        config_dir: The espansr config directory containing the manifest.

    Returns:
        True if the manifest should be regenerated.
    """
    manifest_path = config_dir / MANIFEST_FILENAME
    if not manifest_path.exists():
        return True

    try:
        existing = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(existing, dict):
            return True
        return existing.get("version") != __version__
    except (yaml.YAMLError, OSError):
        return True


def get_status_json() -> str:
    """Build a JSON status string for orchestratr health checks.

    Collects current espansr state — version, config path, template count,
    sync status — and returns a stable JSON contract.

    Returns:
        A JSON string with status information.
    """
    config_dir = get_config_dir()
    templates_dir = get_templates_dir()
    espanso_dir = get_espanso_config_dir()
    config = get_config()

    template_count = len(list(templates_dir.glob("*.json")))
    espanso_synced = espanso_dir is not None
    last_sync = config.espanso.last_sync or ""

    errors: list[str] = []
    if template_count == 0:
        errors.append("No templates found")
    if not espanso_synced:
        errors.append("Espanso not detected")

    status = "ok" if not errors else "degraded"

    data: dict = {
        "version": __version__,
        "status": status,
        "config_dir": str(config_dir),
        "espanso_synced": espanso_synced,
        "template_count": template_count,
        "last_sync": last_sync,
    }

    if errors:
        data["errors"] = errors

    return json.dumps(data, indent=2)


# ─── Internal helpers ────────────────────────────────────────────────────────


def _build_launch_command(platform: str) -> str:
    """Build the launch command string for the given platform.

    On WSL2, wraps the command with ``wsl.exe -d <distro>`` so that
    orchestratr running on Windows can launch espansr inside WSL.

    Args:
        platform: One of "linux", "macos", "windows", "wsl2".

    Returns:
        The shell command string to launch espansr GUI.
    """
    if platform == "wsl2":
        distro = get_wsl_distro_name() or "Ubuntu"
        return f"wsl.exe -d {distro} -- espansr gui"
    return "espansr gui"


def _build_ready_command(platform: str) -> str:
    """Build the ready_cmd string for the given platform.

    On WSL2, wraps the command with ``wsl.exe -d <distro>``.

    Args:
        platform: One of "linux", "macos", "windows", "wsl2".

    Returns:
        The shell command string to check espansr readiness.
    """
    if platform == "wsl2":
        distro = get_wsl_distro_name() or "Ubuntu"
        return f"wsl.exe -d {distro} -- espansr status --json"
    return "espansr status --json"
