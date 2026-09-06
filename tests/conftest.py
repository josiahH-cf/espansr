"""Shared test fixtures for espansr test suite.

Besides Qt/offscreen setup this file holds the suite-wide isolation guards:
every test runs against a config directory under its own ``tmp_path``, never
auto-pulls a git remote, never restarts a real Espanso service, and never
re-points a real ``~/.local/bin/espansr`` shim. ``tests/test_isolation.py``
pins each of those guarantees.
"""

import contextlib
import os
import platform as _platform_module
from pathlib import Path

# Run GUI tests against Qt's offscreen platform by default, matching CI.
# Locally this keeps pytest from popping real windows and stealing focus.
# setdefault means an explicit choice still wins: run with
# QT_QPA_PLATFORM=windows (or another platform plugin) to see real windows.
# This must be set before PyQt6 creates a QApplication, which is why it
# lives at the top of conftest rather than in a fixture.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import patch  # noqa: E402

import pytest  # noqa: E402

import espansr.core.config as _config_module  # noqa: E402
import espansr.core.templates as _templates_module  # noqa: E402
from espansr.core.config import Config  # noqa: E402
from espansr.core.platform import ShimResult, get_platform, get_platform_config  # noqa: E402

REAL_COMMAND_SHIM_MARK = "real_command_shim"


def pytest_configure(config):
    """Register the opt-out marker used by the direct command-shim unit tests."""
    config.addinivalue_line(
        "markers",
        f"{REAL_COMMAND_SHIM_MARK}: exercise the real command-shim helpers instead of "
        "the autouse stub that keeps every other test away from ~/.local/bin",
    )


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


def _reset_process_singletons() -> None:
    """Drop the process-wide ConfigManager / TemplateManager singletons.

    Both cache the config path resolved on first use, so without this a
    manager created under one test's tmp_path would serve the next test.
    """
    _config_module._config_manager = None
    _templates_module._template_manager = None


@pytest.fixture(autouse=True)
def isolated_config_env(tmp_path):
    """Resolve the espansr config directory under this test's ``tmp_path``.

    ``espansr.core.platform.get_platform_config`` derives the config dir from
    ``APPDATA`` on Windows and ``XDG_CONFIG_HOME`` on Linux/WSL2 (those are the
    only environment variables it consults for it); macOS derives it from the
    home directory, so ``HOME`` is redirected there as well. The platform
    caches and the process singletons are reset so nothing computed under a
    previous test leaks in. Returns the overrides so subprocess tests can pass
    the same isolation explicitly: ``env={**os.environ, **isolated_config_env}``.

    A private MonkeyPatch is used (rather than the ``monkeypatch`` fixture) so
    this autouse fixture never changes the setup/teardown order of a test's
    own ``monkeypatch`` relative to module-level autouse fixtures.
    """
    overrides = {
        "APPDATA": str(tmp_path / "appdata"),
        "XDG_CONFIG_HOME": str(tmp_path / "xdg-config"),
    }
    if _platform_module.system() == "Darwin":
        overrides["HOME"] = str(tmp_path / "home")
    with pytest.MonkeyPatch.context() as mp:
        for key, value in overrides.items():
            Path(value).mkdir(parents=True, exist_ok=True)
            mp.setenv(key, value)
        get_platform_config.cache_clear()
        _reset_process_singletons()
        yield overrides
    _reset_process_singletons()


@pytest.fixture(autouse=True)
def _no_auto_pull():
    """Never let a CLI handler auto-pull the developer's real template remote.

    ``cmd_doctor``, ``cmd_validate``, ``cmd_list`` and ``cmd_gui`` all call
    ``_auto_pull_if_configured`` unconditionally; tests that cover the pull
    itself drive ``RemoteManager`` directly.
    """
    with patch("espansr.__main__._auto_pull_if_configured", lambda: None):
        yield


@pytest.fixture(autouse=True)
def _mock_restart_espanso():
    """Prevent tests from invoking the real Espanso daemon.

    Any test that specifically verifies restart behaviour already mocks
    restart_espanso itself; this autouse fixture is a no-op for those tests
    and stops accidental real Espanso invocations in every other test.
    The WSL2 path (``_restart_espanso_wsl2`` stops and starts the Windows
    service through powershell.exe) is stubbed for the same reason.
    """
    with (
        patch("espansr.integrations.espanso.restart_espanso", return_value=True),
        patch("espansr.integrations.espanso._restart_espanso_wsl2", return_value=None),
    ):
        yield


@pytest.fixture(autouse=True)
def _no_real_shim_mutation(request, tmp_path):
    """Keep ``cmd_setup`` / ``cmd_doctor`` from re-pointing a real command shim.

    Every CLI handler resolves the shim helpers from ``espansr.core.platform``
    at call time, so stubbing the module attributes covers all of them (and
    any future caller). ``tests/test_command_shim.py`` exercises the real
    helpers against tmp directories and opts out with the
    ``real_command_shim`` marker.
    """
    if request.node.get_closest_marker(REAL_COMMAND_SHIM_MARK):
        yield
        return

    fake_bin = tmp_path / "fake-user-bin"
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "espansr.core.platform.ensure_command_shim",
            lambda *a, **kw: ShimResult(
                path=fake_bin / "espansr",
                target=tmp_path / "fake-target",
                status="unchanged",
                message="patched in test",
            ),
        )
        mp.setattr("espansr.core.platform.is_user_bin_on_path", lambda *a, **kw: True)
        mp.setattr("espansr.core.platform.get_user_bin_dir", lambda: fake_bin)
        yield


@pytest.fixture()
def make_window(qtbot, tmp_path):
    """Factory for a ``MainWindow`` whose disk and Espanso lookups are patched.

    The patches are active only while the window is constructed; tests then
    patch whatever their own scenario needs. Keyword arguments:

    - ``config``: the ``Config`` served by ``get_config`` (default: fresh).
    - ``tm``: a ``TemplateManager`` served to the browser and editor; when
      omitted the browser gets a MagicMock manager (an empty template list).
    - ``match_dir`` / ``espanso_dir``: what the Espanso integration reports;
      ``espanso_dir`` defaults to ``tmp_path`` and ``None`` means "not found".
    - ``workflow_catalog``: served by ``load_workflow_catalog`` when given.
    """

    def _make(config=None, tm=None, *, match_dir=None, espanso_dir=..., workflow_catalog=None):
        from espansr.ui.main_window import MainWindow

        if espanso_dir is ...:
            espanso_dir = tmp_path

        with contextlib.ExitStack() as stack:
            stack.enter_context(
                patch("espansr.ui.main_window.get_config", return_value=config or Config())
            )
            stack.enter_context(patch("espansr.ui.main_window.get_config_manager"))
            stack.enter_context(patch("espansr.ui.main_window.save_config", return_value=True))
            stack.enter_context(patch("espansr.ui.template_browser.get_config"))
            stack.enter_context(patch("espansr.ui.template_editor.get_config"))
            if tm is not None:
                stack.enter_context(
                    patch("espansr.ui.template_browser.get_template_manager", return_value=tm)
                )
                stack.enter_context(
                    patch("espansr.ui.template_editor.get_template_manager", return_value=tm)
                )
            else:
                stack.enter_context(patch("espansr.ui.template_browser.get_template_manager"))
            if workflow_catalog is not None:
                stack.enter_context(
                    patch(
                        "espansr.ui.main_window.load_workflow_catalog",
                        return_value=workflow_catalog,
                    )
                )
            stack.enter_context(
                patch("espansr.integrations.espanso.get_match_dir", return_value=match_dir)
            )
            stack.enter_context(
                patch(
                    "espansr.integrations.espanso.get_espanso_config_dir",
                    return_value=espanso_dir,
                )
            )
            stack.enter_context(
                patch("espansr.integrations.espanso._get_candidate_paths", return_value=[])
            )
            window = MainWindow()
            qtbot.addWidget(window)
        return window

    return _make
