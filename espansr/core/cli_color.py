"""ANSI color helpers for CLI output.

Provides ``ok()``, ``warn()``, ``fail()``, and ``info()`` helpers that
wrap text in ANSI escape codes.  Colors are automatically suppressed when:

- stdout is not a TTY (piped or redirected)
- the ``NO_COLOR`` environment variable is set (per https://no-color.org/)
"""

import os
import sys

# ANSI escape codes
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_BLUE = "\033[34m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def use_color() -> bool:
    """Return True if colored output should be used.

    Colors are enabled only when stdout is a TTY and the ``NO_COLOR``
    environment variable is not set.
    """
    if "NO_COLOR" in os.environ:
        return False
    try:
        return sys.stdout.isatty()
    except AttributeError:
        return False


def ok(msg: str) -> str:
    """Format an ``[ok]`` status line, green when colors are enabled."""
    if use_color():
        return f"{_BOLD}{_GREEN}[ok]{_RESET}{_GREEN}   {msg}{_RESET}"
    return f"[ok]   {msg}"


def warn(msg: str) -> str:
    """Format a ``[warn]`` status line, yellow when colors are enabled."""
    if use_color():
        return f"{_BOLD}{_YELLOW}[warn]{_RESET}{_YELLOW} {msg}{_RESET}"
    return f"[warn] {msg}"


def fail(msg: str) -> str:
    """Format a ``[FAIL]`` status line, red when colors are enabled."""
    if use_color():
        return f"{_BOLD}{_RED}[FAIL]{_RESET}{_RED} {msg}{_RESET}"
    return f"[FAIL] {msg}"


def info(msg: str) -> str:
    """Format an informational line, blue when colors are enabled."""
    if use_color():
        return f"{_BLUE}{msg}{_RESET}"
    return msg
