"""orchestratr integration for espansr.

Generates an orchestratr app manifest and provides machine-readable
status output so orchestratr can discover, launch, and health-check espansr.

This module is passive — it writes a YAML manifest file and provides
a JSON status helper. espansr never imports or depends on orchestratr code.
"""

import json
import os
from pathlib import Path
from typing import Optional

import yaml

from espansr import __version__
from espansr.core.config import get_config, get_config_dir, get_templates_dir
from espansr.core.platform import get_platform, get_windows_username
from espansr.integrations.espanso import get_espanso_config_dir

MANIFEST_FILENAME = "espansr.yml"

# Required top-level keys for a valid flat manifest.
_FLAT_SCHEMA_KEYS = {
    "name",
    "chord",
    "command",
    "environment",
    "description",
    "ready_cmd",
    "ready_timeout_ms",
}


def resolve_orchestratr_apps_dir() -> Optional[Path]:
    """Resolve the orchestratr apps.d/ directory for the current platform.

    Returns None if orchestratr is not installed (base directory doesn't exist).
    Does not create directories — only orchestratr should create its own config.

    Returns:
        Path to the apps.d/ directory, or None if orchestratr is not installed.
    """
    platform = get_platform()

    if platform == "wsl2":
        base = _wsl2_orchestratr_base()
    elif platform == "windows":
        appdata = os.environ.get("APPDATA", "")
        base = Path(appdata) / "orchestratr" if appdata else None
    elif platform == "macos":
        base = Path.home() / "Library" / "Application Support" / "orchestratr"
    else:  # linux
        xdg = os.environ.get("XDG_CONFIG_HOME")
        config_base = Path(xdg) if xdg else Path.home() / ".config"
        base = config_base / "orchestratr"

    if base is None or not base.exists():
        return None

    return base / "apps.d"


def _wsl2_orchestratr_base() -> Optional[Path]:
    """Resolve the Windows-side orchestratr config directory from WSL2.

    Returns:
        Path under /mnt/c/Users/<username>/AppData/Roaming/orchestratr,
        or None if the Windows username cannot be determined.
    """
    win_user = get_windows_username()
    if not win_user:
        return None
    return Path(f"/mnt/c/Users/{win_user}/AppData/Roaming/orchestratr")


def generate_manifest(apps_dir: Path) -> Path:
    """Generate the orchestratr app manifest in the given apps.d/ directory.

    Produces a flat YAML file matching orchestratr's AppEntry schema.
    The manifest is idempotent — calling this function multiple times
    produces the same file.

    Args:
        apps_dir: The orchestratr apps.d/ directory where the manifest is written.

    Returns:
        The path to the written manifest file.
    """
    platform = get_platform()
    environment = "wsl" if platform == "wsl2" else "native"

    manifest = {
        "name": "espansr",
        "chord": "e",
        "command": "espansr gui",
        "environment": environment,
        "description": "Espanso template manager",
        "ready_cmd": "espansr status --json",
        "ready_timeout_ms": 3000,
    }

    apps_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = apps_dir / MANIFEST_FILENAME
    with open(manifest_path, "w", encoding="utf-8") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)

    return manifest_path


def manifest_needs_update(apps_dir: Path) -> bool:
    """Check whether the orchestratr manifest is missing or outdated.

    Detects both missing manifests and old nested-format manifests that
    need regeneration.

    Args:
        apps_dir: The orchestratr apps.d/ directory containing the manifest.

    Returns:
        True if the manifest should be regenerated.
    """
    manifest_path = apps_dir / MANIFEST_FILENAME
    if not manifest_path.exists():
        return True

    try:
        existing = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(existing, dict):
            return True

        # Detect old nested format: if 'launch' or 'hotkey' or 'version' keys
        # are present, this is the old schema and needs regeneration.
        if any(k in existing for k in ("launch", "hotkey", "version")):
            return True

        # Verify all required flat keys are present
        if not _FLAT_SCHEMA_KEYS.issubset(existing.keys()):
            return True

        # Check content matches what we would generate
        platform = get_platform()
        expected_env = "wsl" if platform == "wsl2" else "native"
        if existing.get("environment") != expected_env:
            return True

        return False
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
