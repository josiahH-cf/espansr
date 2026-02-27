"""Platform detection utilities for espansr.

Single source of truth for OS and WSL2 detection across the codebase.
"""

import platform
import subprocess
from typing import Optional


def get_platform() -> str:
    """Get the current platform.

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
