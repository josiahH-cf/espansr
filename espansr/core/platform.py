"""Platform detection utilities for espansr.

Single source of truth for OS and WSL2 detection across the codebase.
"""

import os
import platform
import re
import subprocess
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal, Mapping, Optional

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

        # Only the current Windows user's profile is a candidate: every
        # candidate is also a cleanup target for espansr-managed files, so
        # other users' Espanso configs must never be touched. When cmd.exe
        # cannot report the user name, a single discovered profile is
        # unambiguous; several profiles are not guessed at.
        win_user = get_windows_username()
        if not win_user:
            discovered = _discover_wsl_windows_usernames()
            if len(discovered) == 1:
                win_user = discovered[0]

        if win_user:
            candidates.extend(
                [
                    # Espanso on Windows typically uses AppData/Roaming.
                    Path(f"/mnt/c/Users/{win_user}/AppData/Roaming/espanso"),
                    Path(f"/mnt/c/Users/{win_user}/.config/espanso"),
                    Path(f"/mnt/c/Users/{win_user}/.espanso"),
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


# ─── Command shim (cross-platform `espansr` on PATH) ─────────────────────────
#
# Background: on POSIX the install script historically exposed `espansr` only
# via a shell alias appended to ~/.bashrc or ~/.zshrc. Aliases never resolve
# in non-interactive shells (subprocess, scripts, `.desktop` launchers,
# systemd-user units, IDE terminals, or the non-interactive shells that
# remote-desktop session managers like RustDesk/RDP commonly spawn). Windows
# already installs a real PATH entry via install.ps1, so it does not suffer
# the same gap. The helpers below give POSIX the same property by placing a
# real executable shim on PATH at ~/.local/bin/espansr.

ShimStatus = Literal[
    "created",
    "updated",
    "unchanged",
    "conflict",
    "skipped",
    "unavailable",
]


@dataclass(frozen=True)
class ShimResult:
    """Outcome of an ensure_command_shim() call."""

    path: Path
    target: Optional[Path]
    status: ShimStatus
    message: str


def get_venv_bin_dir(executable: Optional[str] = None) -> Path:
    """Return the bin/Scripts directory of the venv hosting the interpreter.

    Uses ``sys.executable`` by default. On Windows the directory is
    ``<prefix>\\Scripts``; elsewhere it is ``<prefix>/bin``.
    """
    exe = Path(executable) if executable else Path(sys.executable)
    return exe.parent


def _shim_executable_name() -> str:
    return "espansr.cmd" if get_platform() == "windows" else "espansr"


def get_user_bin_dir() -> Path:
    """Return the canonical user-level executable directory for this platform.

    On POSIX returns ``~/.local/bin`` (XDG/freedesktop standard, on default
    PATH for Debian/Ubuntu/Fedora login shells and respected by systemd-user
    and desktop launchers). On Windows returns ``%LOCALAPPDATA%\\espansr\\bin``,
    the launcher directory ``install.ps1`` persists to the user PATH (falling
    back to the venv ``Scripts`` directory when LOCALAPPDATA is unset).
    """
    if get_platform() == "windows":
        localappdata = os.environ.get("LOCALAPPDATA", "")
        if localappdata:
            return Path(localappdata) / "espansr" / "bin"
        return get_venv_bin_dir()
    return Path.home() / ".local" / "bin"


def symlink_target(shim_path: Path, bin_dir: Path) -> Path:
    r"""Return the resolved target of the symlink at ``shim_path``.

    ``os.readlink`` on Windows returns absolute targets in extended-length form
    (``\\?\C:\...``); strip that prefix so the result compares equal to a
    normally spelled path. Relative targets resolve against ``bin_dir``.
    """
    raw = os.readlink(shim_path)
    if raw.startswith("\\\\?\\UNC\\"):
        raw = "\\\\" + raw[len("\\\\?\\UNC\\") :]
    elif raw.startswith("\\\\?\\"):
        raw = raw[len("\\\\?\\") :]
    return (bin_dir / raw).resolve()


def is_user_bin_on_path(
    user_bin: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
) -> bool:
    """Return True if ``user_bin`` appears on PATH in the given environment."""
    target = (user_bin or get_user_bin_dir()).resolve()
    raw = (env or os.environ).get("PATH", "")
    sep = ";" if get_platform() == "windows" else ":"
    for entry in raw.split(sep):
        if not entry:
            continue
        try:
            if Path(entry).resolve() == target:
                return True
        except OSError:
            continue
    return False


def _find_venv_espansr(venv_bin: Path) -> Optional[Path]:
    """Locate the installed espansr executable inside a venv bin dir."""
    for name in ("espansr", "espansr.exe"):
        candidate = venv_bin / name
        if candidate.exists():
            return candidate
    return None


def _read_managed_wrapper_target(shim_path: Path) -> Optional[Path]:
    """Return the target from a fallback wrapper created by _create_shim()."""
    try:
        text = shim_path.read_text(encoding="utf-8")
    except OSError:
        return None

    match = re.fullmatch(r'#!/usr/bin/env sh\nexec "(.+)" "\$@"\n?', text)
    if match is None:
        return None
    return Path(match.group(1)).resolve()


def ensure_command_shim(
    target_executable: Optional[Path] = None,
    user_bin: Optional[Path] = None,
    force: bool = False,
) -> ShimResult:
    """Ensure a PATH-visible ``espansr`` shim exists for the running install.

    POSIX: idempotently maintain a symlink at ``<user_bin>/espansr`` pointing
    to the venv's ``espansr`` executable. If a non-symlink regular file is in
    the way, return status ``conflict`` unless ``force=True`` (which replaces
    it). Falls back to a tiny wrapper script when symlinks are unsupported
    (rare; e.g. FAT/exFAT home dirs).

    Windows: verify-only. ``install.ps1`` is the source of truth: it writes an
    ``espansr.cmd`` launcher into the user bin directory and persists that
    directory on the user PATH; this helper reports whether that directory (or,
    for installs made before the launcher existed, the venv Scripts directory)
    is currently on PATH so doctor and tests can surface the state.
    """
    plat = get_platform()
    venv_bin = get_venv_bin_dir()
    target = target_executable or _find_venv_espansr(venv_bin)
    bin_dir = user_bin or get_user_bin_dir()
    shim_path = bin_dir / _shim_executable_name()

    if plat == "windows":
        if target is None:
            return ShimResult(
                path=shim_path,
                target=None,
                status="unavailable",
                message="espansr executable not found in venv Scripts directory",
            )
        launcher = shim_path if shim_path.exists() else target
        if is_user_bin_on_path(bin_dir) or is_user_bin_on_path(venv_bin):
            return ShimResult(
                path=launcher,
                target=target,
                status="unchanged",
                message=f"Windows: {launcher.parent} is on user PATH (managed by install.ps1)",
            )
        return ShimResult(
            path=launcher,
            target=target,
            status="skipped",
            message=f"Windows: {bin_dir} is not on PATH; rerun install.ps1 to persist it",
        )

    if target is None:
        return ShimResult(
            path=shim_path,
            target=None,
            status="unavailable",
            message=f"espansr executable not found in {venv_bin}",
        )

    try:
        bin_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return ShimResult(
            path=shim_path,
            target=target,
            status="unavailable",
            message=f"could not create {bin_dir}: {exc}",
        )

    # Inspect existing entry.
    if shim_path.is_symlink():
        try:
            current = symlink_target(shim_path, bin_dir)
        except OSError:
            current = None
        if current == target.resolve():
            return ShimResult(
                path=shim_path,
                target=target,
                status="unchanged",
                message=f"shim already points to {target}",
            )
        try:
            shim_path.unlink()
        except OSError as exc:
            return ShimResult(
                path=shim_path,
                target=target,
                status="unavailable",
                message=f"could not replace stale shim at {shim_path}: {exc}",
            )
        return _create_shim(shim_path, target, status_on_success="updated")

    if shim_path.exists():
        wrapper_target = _read_managed_wrapper_target(shim_path)
        if wrapper_target is not None:
            if wrapper_target == target.resolve():
                return ShimResult(
                    path=shim_path,
                    target=target,
                    status="unchanged",
                    message=f"wrapper shim already points to {target}",
                )
            try:
                shim_path.unlink()
            except OSError as exc:
                return ShimResult(
                    path=shim_path,
                    target=target,
                    status="unavailable",
                    message=f"could not replace stale wrapper at {shim_path}: {exc}",
                )
            return _create_shim(shim_path, target, status_on_success="updated")

        if not force:
            return ShimResult(
                path=shim_path,
                target=target,
                status="conflict",
                message=(
                    f"non-symlink file at {shim_path}; rerun with --force-shim " "to overwrite"
                ),
            )
        try:
            shim_path.unlink()
        except OSError as exc:
            return ShimResult(
                path=shim_path,
                target=target,
                status="unavailable",
                message=f"could not remove existing file at {shim_path}: {exc}",
            )

    return _create_shim(shim_path, target, status_on_success="created")


def _create_shim(shim_path: Path, target: Path, *, status_on_success: ShimStatus) -> ShimResult:
    """Create the shim as a symlink, falling back to a wrapper script."""
    try:
        shim_path.symlink_to(target)
        return ShimResult(
            path=shim_path,
            target=target,
            status=status_on_success,
            message=f"symlink {shim_path} -> {target}",
        )
    except (OSError, NotImplementedError):
        # Fall back to a tiny POSIX wrapper script.
        try:
            shim_path.write_text(
                "#!/usr/bin/env sh\n" f'exec "{target}" "$@"\n',
                encoding="utf-8",
            )
            shim_path.chmod(0o755)
            return ShimResult(
                path=shim_path,
                target=target,
                status=status_on_success,
                message=f"wrapper script {shim_path} -> {target}",
            )
        except OSError as exc:
            return ShimResult(
                path=shim_path,
                target=target,
                status="unavailable",
                message=f"could not create shim at {shim_path}: {exc}",
            )
