"""Shared test fixtures for espansr test suite."""

import os

# Run GUI tests against Qt's offscreen platform by default, matching CI.
# Locally this keeps pytest from popping real windows and stealing focus.
# setdefault means an explicit choice still wins: run with
# QT_QPA_PLATFORM=windows (or another platform plugin) to see real windows.
# This must be set before PyQt6 creates a QApplication, which is why it
# lives at the top of conftest rather than in a fixture.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import patch  # noqa: E402

import pytest  # noqa: E402

from espansr.core.platform import get_platform, get_platform_config  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_platform_caches():
    """Clear lru_cache on platform functions before and after each test.

    Prevents cached values from leaking between tests that mock
    platform detection at different levels.
    """
    get_platform.cache_clear()
    get_platform_config.cache_clear()
    yield
    get_platform.cache_clear()
    get_platform_config.cache_clear()


@pytest.fixture(autouse=True)
def _mock_restart_espanso():
    """Prevent tests from invoking the real Espanso daemon.

    Any test that specifically verifies restart behaviour already mocks
    restart_espanso itself; this autouse fixture is a no-op for those tests
    and stops accidental real Espanso invocations in every other test.
    """
    with patch("espansr.integrations.espanso.restart_espanso", return_value=True):
        yield
