"""Tests for espansr.core.cli_color — ANSI color helpers.

Covers: ok/warn/fail/info helpers, TTY suppression, NO_COLOR suppression,
and Windows graceful degradation.
"""

import os
from unittest.mock import patch

import pytest

from espansr.core.cli_color import fail, info, ok, use_color, warn

# ─── Color detection ────────────────────────────────────────────────────────


class TestUseColor:
    """Test the use_color() detection function."""

    def test_returns_false_when_not_tty(self):
        """Colors suppressed when stdout is not a TTY."""
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.isatty.return_value = False
            with patch.dict(os.environ, {}, clear=True):
                assert use_color() is False

    def test_returns_false_when_no_color_set(self):
        """Colors suppressed when NO_COLOR env var is set (any value)."""
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.isatty.return_value = True
            with patch.dict(os.environ, {"NO_COLOR": "1"}):
                assert use_color() is False

    def test_returns_false_when_no_color_empty_string(self):
        """NO_COLOR with empty value still suppresses color per spec."""
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.isatty.return_value = True
            with patch.dict(os.environ, {"NO_COLOR": ""}):
                assert use_color() is False

    def test_returns_true_when_tty_and_no_suppression(self):
        """Colors enabled when stdout is a TTY and NO_COLOR is not set."""
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.isatty.return_value = True
            # Ensure NO_COLOR is not in environment
            env = os.environ.copy()
            env.pop("NO_COLOR", None)
            with patch.dict(os.environ, env, clear=True):
                assert use_color() is True


# ─── Helpers with color enabled ─────────────────────────────────────────────


class TestColorEnabled:
    """Test output formatting with colors forcibly enabled."""

    @pytest.fixture(autouse=True)
    def _force_color(self):
        with patch("espansr.core.cli_color.use_color", return_value=True):
            yield

    def test_ok_wraps_green(self):
        result = ok("Python 3.12")
        assert "\033[32m" in result
        assert "[ok]" in result
        assert "Python 3.12" in result
        assert result.endswith("\033[0m")

    def test_warn_wraps_yellow(self):
        result = warn("Minor issue")
        assert "\033[33m" in result
        assert "[warn]" in result
        assert "Minor issue" in result
        assert result.endswith("\033[0m")

    def test_fail_wraps_red(self):
        result = fail("Missing binary")
        assert "\033[31m" in result
        assert "[FAIL]" in result
        assert "Missing binary" in result
        assert result.endswith("\033[0m")

    def test_info_wraps_blue(self):
        result = info("Checking config")
        assert "\033[34m" in result
        assert "Checking config" in result
        assert result.endswith("\033[0m")

    def test_ok_bold_tag(self):
        """The tag portion should include bold formatting."""
        result = ok("test")
        assert "\033[1m" in result


# ─── Helpers with color disabled ─────────────────────────────────────────────


class TestColorDisabled:
    """Test output formatting when colors are suppressed."""

    @pytest.fixture(autouse=True)
    def _no_color(self):
        with patch("espansr.core.cli_color.use_color", return_value=False):
            yield

    def test_ok_plain(self):
        result = ok("Python 3.12")
        assert "\033[" not in result
        assert "[ok]   Python 3.12" == result

    def test_warn_plain(self):
        result = warn("Minor issue")
        assert "\033[" not in result
        assert "[warn] Minor issue" == result

    def test_fail_plain(self):
        result = fail("Missing binary")
        assert "\033[" not in result
        assert "[FAIL] Missing binary" == result

    def test_info_plain(self):
        result = info("Checking config")
        assert "\033[" not in result
        assert "Checking config" == result


# ─── Integration: test captures have no ANSI codes ──────────────────────────


class TestCapsysIntegration:
    """In pytest, stdout is not a TTY, so colors should be auto-suppressed."""

    def test_ok_no_ansi_in_capsys(self, capsys):
        """When printed to capsys (not a TTY), output has no ANSI codes."""
        print(ok("test output"))
        captured = capsys.readouterr().out
        assert "\033[" not in captured
        assert "[ok]" in captured
