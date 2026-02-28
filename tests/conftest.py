"""Shared test fixtures for espansr test suite."""

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
