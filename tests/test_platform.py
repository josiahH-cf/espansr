"""Tests for espansr.core.platform module.

Covers: get_platform(), is_wsl2(), is_windows(), get_windows_username()
"""

import subprocess
from unittest.mock import MagicMock, mock_open, patch

from espansr.core.platform import (
    get_platform,
    get_windows_username,
    get_wsl_distro_name,
    is_windows,
    is_wsl2,
)

# ─── get_platform() tests ────────────────────────────────────────────────────


def test_get_platform_returns_wsl2_when_proc_version_contains_microsoft():
    """get_platform() returns 'wsl2' when /proc/version contains 'microsoft'."""
    with (
        patch("platform.system", return_value="Linux"),
        patch(
            "builtins.open",
            mock_open(read_data="Linux version 5.15 (Microsoft WSL2)"),
        ),
    ):
        assert get_platform() == "wsl2"


def test_get_platform_returns_linux_on_native():
    """get_platform() returns 'linux' on a non-WSL2 Linux system."""
    with (
        patch("platform.system", return_value="Linux"),
        patch(
            "builtins.open",
            mock_open(read_data="Linux version 5.15 generic ubuntu"),
        ),
    ):
        assert get_platform() == "linux"


def test_get_platform_returns_macos_on_darwin():
    """get_platform() returns 'macos' on macOS."""
    with patch("platform.system", return_value="Darwin"):
        assert get_platform() == "macos"


def test_get_platform_returns_windows():
    """get_platform() returns 'windows' on Windows."""
    with patch("platform.system", return_value="Windows"):
        assert get_platform() == "windows"


def test_get_platform_returns_linux_when_proc_version_unreadable():
    """get_platform() returns 'linux' when /proc/version can't be read."""
    with (
        patch("platform.system", return_value="Linux"),
        patch("builtins.open", side_effect=OSError("Permission denied")),
    ):
        assert get_platform() == "linux"


def test_get_platform_returns_unknown_for_unrecognized_system():
    """get_platform() returns 'unknown' for unrecognized platform.system() values."""
    with patch("platform.system", return_value="FreeBSD"):
        assert get_platform() == "unknown"


def test_get_platform_detects_wsl_keyword_in_proc_version():
    """get_platform() detects 'wsl' (lowercase) in /proc/version as WSL2."""
    with (
        patch("platform.system", return_value="Linux"),
        patch(
            "builtins.open",
            mock_open(read_data="Linux version 5.15.90.1-wsl2-standard"),
        ),
    ):
        assert get_platform() == "wsl2"


# ─── is_wsl2() tests ─────────────────────────────────────────────────────────


def test_is_wsl2_returns_true_on_wsl2():
    """is_wsl2() returns True when running under WSL2."""
    with (
        patch("platform.system", return_value="Linux"),
        patch(
            "builtins.open",
            mock_open(read_data="Linux version 5.15 Microsoft WSL2"),
        ),
    ):
        assert is_wsl2() is True


def test_is_wsl2_returns_false_on_native_linux():
    """is_wsl2() returns False on native Linux."""
    with (
        patch("platform.system", return_value="Linux"),
        patch(
            "builtins.open",
            mock_open(read_data="Linux version 5.15 generic ubuntu"),
        ),
    ):
        assert is_wsl2() is False


def test_is_wsl2_returns_false_on_windows():
    """is_wsl2() returns False on native Windows."""
    with patch("platform.system", return_value="Windows"):
        assert is_wsl2() is False


def test_is_wsl2_returns_false_on_macos():
    """is_wsl2() returns False on macOS."""
    with patch("platform.system", return_value="Darwin"):
        assert is_wsl2() is False


# ─── is_windows() tests ──────────────────────────────────────────────────────


def test_is_windows_returns_true_on_windows():
    """is_windows() returns True on native Windows."""
    with patch("platform.system", return_value="Windows"):
        assert is_windows() is True


def test_is_windows_returns_false_on_linux():
    """is_windows() returns False on Linux."""
    with (
        patch("platform.system", return_value="Linux"),
        patch(
            "builtins.open",
            mock_open(read_data="Linux version 5.15 generic"),
        ),
    ):
        assert is_windows() is False


# ─── get_windows_username() tests ────────────────────────────────────────────


def test_get_windows_username_returns_name_on_success():
    """get_windows_username() returns the Windows username when cmd.exe succeeds."""
    mock_result = MagicMock()
    mock_result.stdout = "JohnDoe\r\n"

    with patch("subprocess.run", return_value=mock_result):
        assert get_windows_username() == "JohnDoe"


def test_get_windows_username_returns_none_on_failure():
    """get_windows_username() returns None when cmd.exe fails."""
    with patch("subprocess.run", side_effect=FileNotFoundError("cmd.exe not found")):
        assert get_windows_username() is None


def test_get_windows_username_returns_none_on_timeout():
    """get_windows_username() returns None when cmd.exe times out."""
    with patch(
        "subprocess.run",
        side_effect=subprocess.TimeoutExpired("cmd.exe", 5),
    ):
        assert get_windows_username() is None


def test_get_windows_username_returns_none_on_empty_output():
    """get_windows_username() returns None when cmd.exe returns empty output."""
    mock_result = MagicMock()
    mock_result.stdout = "  \r\n"

    with patch("subprocess.run", return_value=mock_result):
        assert get_windows_username() is None


def test_get_windows_username_returns_none_on_os_error():
    """get_windows_username() returns None on generic OSError."""
    with patch("subprocess.run", side_effect=OSError("Unexpected error")):
        assert get_windows_username() is None


# ─── get_wsl_distro_name() tests ─────────────────────────────────────────────


def test_get_wsl_distro_name_from_env():
    """get_wsl_distro_name() returns distro name from WSL_DISTRO_NAME env var."""
    with patch.dict("os.environ", {"WSL_DISTRO_NAME": "Ubuntu"}):
        assert get_wsl_distro_name() == "Ubuntu"


def test_get_wsl_distro_name_fallback_wsl_exe():
    """get_wsl_distro_name() falls back to wsl.exe -l -q when env var is missing."""
    mock_result = MagicMock()
    mock_result.stdout = "Ubuntu\r\n"

    with (
        patch.dict("os.environ", {}, clear=False),
        patch(
            "os.environ.get",
            side_effect=lambda k, d=None: None if k == "WSL_DISTRO_NAME" else d,
        ),
        patch("subprocess.run", return_value=mock_result),
    ):
        assert get_wsl_distro_name() == "Ubuntu"


def test_get_wsl_distro_name_returns_none_on_failure():
    """get_wsl_distro_name() returns None when both env var and wsl.exe fail."""
    with (
        patch.dict("os.environ", {}, clear=False),
        patch(
            "os.environ.get",
            side_effect=lambda k, d=None: None if k == "WSL_DISTRO_NAME" else d,
        ),
        patch("subprocess.run", side_effect=FileNotFoundError("wsl.exe not found")),
    ):
        assert get_wsl_distro_name() is None


def test_get_wsl_distro_name_returns_none_on_empty_output():
    """get_wsl_distro_name() returns None when wsl.exe returns empty output."""
    mock_result = MagicMock()
    mock_result.stdout = "  \r\n"

    with (
        patch.dict("os.environ", {}, clear=False),
        patch(
            "os.environ.get",
            side_effect=lambda k, d=None: None if k == "WSL_DISTRO_NAME" else d,
        ),
        patch("subprocess.run", return_value=mock_result),
    ):
        assert get_wsl_distro_name() is None


# ─── config.py re-export tests ───────────────────────────────────────────────


def test_config_reexports_get_platform():
    """config.py re-exports get_platform from platform module."""
    from espansr.core.config import get_platform as config_get_platform

    assert callable(config_get_platform)
    assert config_get_platform is get_platform


def test_config_reexports_is_windows():
    """config.py re-exports is_windows from platform module."""
    from espansr.core.config import is_windows as config_is_windows

    assert callable(config_is_windows)
    assert config_is_windows is is_windows
