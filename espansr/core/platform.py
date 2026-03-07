"""Platform detection utilities for espansr.

Single source of truth for OS and WSL2 detection across the codebase.
"""

import os
import platform
import subprocess
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional


_RESERVED_WINDOWS_USER_DIRS = {
    "all users",
    "default",
    "default user",
    "public",
}


def _discover_wsl_windows_usernames() -> list[str]:
    """Discover Windows profile names from /mnt/c/Users when running in WSL.

    Returns:
        Sorted list of likely Windows usernames. Returns empty list when
        the directory is unavailable or unreadable.
    """
    users_root = Path("/mnt/c/Users")
    if not users_root.is_dir():
        return []

    names: list[str] = []
    try:
        for entry in users_root.iterdir():
            if not entry.is_dir():
                continue
            lowered = entry.name.lower()
            if lowered in _RESERVED_WINDOWS_USER_DIRS:
                continue
            names.append(entry.name)
    except OSError:
        return []

    return sorted(names, key=str.lower)


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    """Deduplicate paths while preserving order."""
    seen: set[str] = set()
    ordered: list[Path] = []
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(path)
    return ordered


@dataclass(frozen=True)
class PlatformConfig:
    """Platform-specific path configuration.

    Maps each platform to its complete set of paths so that
    platform-specific path logic is defined in exactly one place.
    """

    platform: str  # "linux", "macos", "wsl2", "windows", "unknown"
    espansr_config_dir: Path  # where espansr stores its own config and templates
    espanso_candidate_dirs: list[Path] = field(
        default_factory=list
    )  # ordered dirs to probe for Espanso config


@lru_cache(maxsize=1)
def get_platform_config() -> PlatformConfig:
    """Build a PlatformConfig for the detected platform.

    Cached: returns the same object on repeated calls within a process.
    Call ``get_platform_config.cache_clear()`` in tests that mock platform.

    Returns:
        PlatformConfig with all platform-specific paths resolved.
    """
    plat = get_platform()

    if plat == "macos":
        base = Path.home() / "Library" / "Application Support"
        return PlatformConfig(
            platform=plat,
            espansr_config_dir=base / "espansr",
            espanso_candidate_dirs=[
                base / "espanso",
                Path.home() / ".config" / "espanso",
            ],
        )

    if plat == "windows":
        appdata = os.environ.get("APPDATA", "")
        candidates: list[Path] = []
        if appdata:
            candidates.append(Path(appdata) / "espanso")
            config_dir = Path(appdata) / "espansr"
        else:
            config_dir = Path.home() / "espansr"
        candidates.append(Path.home() / ".espanso")
        return PlatformConfig(
            platform=plat,
            espansr_config_dir=config_dir,
            espanso_candidate_dirs=candidates,
        )

    if plat == "wsl2":
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg) if xdg else Path.home() / ".config"

        candidates: list[Path] = []
        ordered_users: list[str] = []

        win_user = get_windows_username()
        if win_user:
            ordered_users.append(win_user)

        for discovered in _discover_wsl_windows_usernames():
            if discovered.lower() not in {u.lower() for u in ordered_users}:
                ordered_users.append(discovered)

        for user in ordered_users:
            candidates.extend(
                [
                    # Espanso on Windows typically uses AppData/Roaming.
                    Path(f"/mnt/c/Users/{user}/AppData/Roaming/espanso"),
                    Path(f"/mnt/c/Users/{user}/.config/espanso"),
                    Path(f"/mnt/c/Users/{user}/.espanso"),
                ]
            )

        candidates.extend(
            [
                Path.home() / ".config" / "espanso",
                Path.home() / ".espanso",
            ]
        )

        return PlatformConfig(
            platform=plat,
            espansr_config_dir=base / "espansr",
            espanso_candidate_dirs=_dedupe_paths(candidates),
        )

    if plat == "linux":
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg) if xdg else Path.home() / ".config"
        return PlatformConfig(
            platform=plat,
            espansr_config_dir=base / "espansr",
            espanso_candidate_dirs=[
                Path.home() / ".config" / "espanso",
                Path.home() / ".espanso",
            ],
        )

    # Unknown platform — no paths
    return PlatformConfig(
        platform=plat,
        espansr_config_dir=Path.home() / ".config" / "espansr",
        espanso_candidate_dirs=[],
    )


@lru_cache(maxsize=1)
def get_platform() -> str:
    """Get the current platform.

    Cached: returns the same string on repeated calls within a process.
    Call ``get_platform.cache_clear()`` in tests that mock platform.

    Returns:
        'windows', 'linux', 'wsl2', or 'macos'
    """
    system = platform.system()

    if system == "Windows":
        return "windows"
    elif system == "Darwin":
        return "macos"
    elif system == "Linux":
        try:
            with open("/proc/version", "r") as f:
                version = f.read().lower()
                if "microsoft" in version or "wsl" in version:
                    return "wsl2"
        except (OSError, IOError):
            pass
        return "linux"
    return "unknown"


def is_wsl2() -> bool:
    """Check if running under WSL2.

    Returns:
        True if the current environment is WSL2, False otherwise.
    """
    return get_platform() == "wsl2"


def is_windows() -> bool:
    """Check if running on native Windows.

    Returns:
        True if the current environment is native Windows, False otherwise.
    """
    return get_platform() == "windows"


def get_wsl_distro_name() -> Optional[str]:
    """Get the WSL2 distribution name.

    Checks the WSL_DISTRO_NAME environment variable first, then falls back
    to parsing ``wsl.exe -l -q`` output.

    Returns:
        The distro name string (e.g. "Ubuntu"), or None if unavailable.
    """
    import os

    name = os.environ.get("WSL_DISTRO_NAME")
    if name:
        return name

    try:
        result = subprocess.run(
            ["wsl.exe", "-l", "-q"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        distro = result.stdout.strip()
        return distro if distro else None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def get_windows_username() -> Optional[str]:
    """Get the Windows username via cmd.exe (for WSL2 environments).

    Returns:
        The Windows username string, or None if unavailable.
    """
    try:
        result = subprocess.run(
            ["cmd.exe", "/c", "echo %USERNAME%"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        username = result.stdout.strip()
        return username if username else None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
