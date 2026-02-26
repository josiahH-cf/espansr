"""Tests for automatr_espanso.core.platform module.

Covers: get_platform(), is_wsl2(), get_windows_username()
"""

import importlib
from unittest.mock import MagicMock, mock_open, patch


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
        from automatr_espanso.core.platform import get_platform

        importlib.reload(importlib.import_module("automatr_espanso.core.platform"))
        from automatr_espanso.core.platform import get_platform

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
        from automatr_espanso.core.platform import get_platform

        importlib.reload(importlib.import_module("automatr_espanso.core.platform"))
        from automatr_espanso.core.platform import get_platform

        assert get_platform() == "linux"


def test_get_platform_returns_macos_on_darwin():
    """get_platform() returns 'macos' on macOS."""
    with patch("platform.system", return_value="Darwin"):
        from automatr_espanso.core.platform import get_platform

        importlib.reload(importlib.import_module("automatr_espanso.core.platform"))
        from automatr_espanso.core.platform import get_platform

        assert get_platform() == "macos"


def test_get_platform_returns_windows():
    """get_platform() returns 'windows' on Windows."""
    with patch("platform.system", return_value="Windows"):
        from automatr_espanso.core.platform import get_platform

        importlib.reload(importlib.import_module("automatr_espanso.core.platform"))
        from automatr_espanso.core.platform import get_platform

        assert get_platform() == "windows"


def test_get_platform_returns_linux_when_proc_version_unreadable():
    """get_platform() returns 'linux' when /proc/version can't be read."""
    with (
        patch("platform.system", return_value="Linux"),
        patch("builtins.open", side_effect=OSError("Permission denied")),
    ):
        from automatr_espanso.core.platform import get_platform

        importlib.reload(importlib.import_module("automatr_espanso.core.platform"))
        from automatr_espanso.core.platform import get_platform

        assert get_platform() == "linux"


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
        importlib.reload(importlib.import_module("automatr_espanso.core.platform"))
        from automatr_espanso.core.platform import is_wsl2

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
        importlib.reload(importlib.import_module("automatr_espanso.core.platform"))
        from automatr_espanso.core.platform import is_wsl2

        assert is_wsl2() is False


# ─── get_windows_username() tests ────────────────────────────────────────────


def test_get_windows_username_returns_name_on_success():
    """get_windows_username() returns the Windows username when cmd.exe succeeds."""
    mock_result = MagicMock()
    mock_result.stdout = "JohnDoe\r\n"

    with patch("subprocess.run", return_value=mock_result):
        importlib.reload(importlib.import_module("automatr_espanso.core.platform"))
        from automatr_espanso.core.platform import get_windows_username

        assert get_windows_username() == "JohnDoe"


def test_get_windows_username_returns_none_on_failure():
    """get_windows_username() returns None when cmd.exe fails."""
    with patch("subprocess.run", side_effect=FileNotFoundError("cmd.exe not found")):
        importlib.reload(importlib.import_module("automatr_espanso.core.platform"))
        from automatr_espanso.core.platform import get_windows_username

        assert get_windows_username() is None


def test_get_windows_username_returns_none_on_timeout():
    """get_windows_username() returns None when cmd.exe times out."""
    import subprocess

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd.exe", 5)):
        importlib.reload(importlib.import_module("automatr_espanso.core.platform"))
        from automatr_espanso.core.platform import get_windows_username

        assert get_windows_username() is None


def test_get_windows_username_returns_none_on_empty_output():
    """get_windows_username() returns None when cmd.exe returns empty output."""
    mock_result = MagicMock()
    mock_result.stdout = "  \r\n"

    with patch("subprocess.run", return_value=mock_result):
        importlib.reload(importlib.import_module("automatr_espanso.core.platform"))
        from automatr_espanso.core.platform import get_windows_username

        assert get_windows_username() is None
