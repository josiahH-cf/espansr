"""Install metadata recording for espansr.

Records *where* and *how* espansr was installed so ``espansr refresh`` can
rerun the correct OS-specific installer without guessing. The metadata is
written by ``install.sh`` / ``install.ps1`` (through the hidden
``espansr record-install`` command) and read back by the ``refresh`` command.

The metadata file lives in the espansr config directory as ``install.json``.
This module is the single source of truth for its path and schema.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from espansr.core.config import get_config_dir
from espansr.core.platform import get_platform

INSTALL_META_FILENAME = "install.json"


@dataclass
class InstallMeta:
    """Recorded facts about how espansr was installed."""

    platform: str  # "linux", "macos", "wsl2", "windows", "unknown"
    repo_dir: str  # repository folder containing the installer scripts
    installer: str  # "install.sh" or "install.ps1"
    venv_dir: str = ""  # virtual environment directory, if known
    recorded_at: str = ""  # ISO timestamp of when the metadata was written


def installer_for_platform(platform: Optional[str] = None) -> str:
    """Return the installer script name appropriate for ``platform``.

    Windows uses the PowerShell installer; every other platform (Linux,
    macOS, and WSL2) uses the POSIX shell installer.
    """
    plat = platform or get_platform()
    return "install.ps1" if plat == "windows" else "install.sh"


def get_install_meta_path() -> Path:
    """Return the path to the install metadata file."""
    return get_config_dir() / INSTALL_META_FILENAME


def infer_repo_dir() -> Optional[Path]:
    """Best-effort discovery of the repository folder for editable installs.

    Derived from this module's location: ``espansr/core/install_meta.py`` sits
    two directories below the repository root. Returns the root only when it
    actually contains an installer script, otherwise ``None``.
    """
    try:
        candidate = Path(__file__).resolve().parents[2]
    except (OSError, IndexError):
        return None
    if (candidate / "install.sh").exists() or (candidate / "install.ps1").exists():
        return candidate
    return None


def record_install_meta(
    repo_dir,
    installer: Optional[str] = None,
    venv_dir: str = "",
    platform: Optional[str] = None,
) -> InstallMeta:
    """Write install metadata to the config directory and return it."""
    plat = platform or get_platform()
    meta = InstallMeta(
        platform=plat,
        repo_dir=str(Path(repo_dir)),
        installer=installer or installer_for_platform(plat),
        venv_dir=str(venv_dir) if venv_dir else "",
        recorded_at=datetime.now(timezone.utc).isoformat(),
    )
    path = get_install_meta_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(meta), indent=2), encoding="utf-8")
    return meta


def load_install_meta() -> Optional[InstallMeta]:
    """Load install metadata, or ``None`` when missing or unreadable."""
    path = get_install_meta_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None

    known = set(InstallMeta.__dataclass_fields__)
    filtered = {k: v for k, v in data.items() if k in known}
    if not filtered.get("platform") or not filtered.get("repo_dir"):
        return None
    filtered.setdefault("installer", installer_for_platform(filtered.get("platform")))
    return InstallMeta(**filtered)
