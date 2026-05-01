"""Shared test fixtures for espansr test suite."""

from unittest.mock import patch

import pytest

from espansr.core.platform import get_platform, get_platform_config


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
    with patch(
        "espansr.integrations.espanso.restart_espanso", return_value=True
    ):
        yield
