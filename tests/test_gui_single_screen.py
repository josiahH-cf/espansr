"""Tests for the single-screen GUI layout (Issue #3).

Covers: toolbar sync button, sync_to_espanso() call, geometry persistence,
and last_template restore on startup.
"""

import base64
import contextlib
from unittest.mock import patch

import pytest

from espansr.core.config import Config
from espansr.core.templates import TemplateManager

# ── Helpers ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def tm(tmp_path):
    """Real TemplateManager backed by a temp directory."""
    return TemplateManager(templates_dir=tmp_path / "templates")


def _make_window(qtbot, config, tm=None, match_dir=None, tmp_path=None):
    """Create a patched MainWindow. Returns the window instance."""
    from espansr.ui.main_window import MainWindow

    tm_patch = (
        patch(
            "espansr.ui.template_browser.get_template_manager",
            return_value=tm,
        )
        if tm is not None
        else patch("espansr.ui.template_browser.get_template_manager")
    )

    with contextlib.ExitStack() as stack:
        stack.enter_context(patch("espansr.ui.main_window.get_config", return_value=config))
        stack.enter_context(patch("espansr.ui.main_window.get_config_manager"))
        stack.enter_context(patch("espansr.ui.template_browser.get_config"))
        stack.enter_context(patch("espansr.ui.template_editor.get_config"))
        stack.enter_context(
            patch(
                "espansr.integrations.espanso.get_match_dir",
                return_value=match_dir,
            )
        )
        stack.enter_context(
            patch(
                "espansr.integrations.espanso.get_espanso_config_dir",
                return_value=tmp_path,
            )
        )
        stack.enter_context(
            patch(
                "espansr.integrations.espanso._get_candidate_paths",
                return_value=[],
            )
        )
        stack.enter_context(tm_patch)

        window = MainWindow()
        qtbot.addWidget(window)

    return window


# ── Toolbar: Sync Now button ─────────────────────────────────────────────────


def test_sync_button_in_toolbar(qtbot, tmp_path):
    """MainWindow has a 'Sync Now' QPushButton in the toolbar."""
    from PyQt6.QtWidgets import QPushButton

    window = _make_window(qtbot, Config(), tmp_path=tmp_path)

    sync_btn = window._sync_btn
    assert isinstance(sync_btn, QPushButton)
    assert "Sync" in sync_btn.text()


def test_pull_latest_button_in_toolbar(qtbot, tmp_path):
    """MainWindow has a 'Pull Latest' QPushButton in the toolbar."""
    from PyQt6.QtWidgets import QPushButton

    window = _make_window(qtbot, Config(), tmp_path=tmp_path)

    pull_btn = window._pull_latest_btn
    assert isinstance(pull_btn, QPushButton)
    assert "Pull" in pull_btn.text()


def test_sync_calls_sync_to_espanso(qtbot, tmp_path):
    """Clicking 'Sync Now' calls sync_to_espanso() exactly once."""
    window = _make_window(qtbot, Config(), tmp_path=tmp_path)

    with patch(
        "espansr.integrations.espanso.sync_to_espanso",
        return_value=True,
    ) as mock_sync:
        window._sync_btn.click()

    mock_sync.assert_called_once_with(update_bundled=True)


def test_pull_latest_calls_remote_and_sync(qtbot, tmp_path):
    """Clicking 'Pull Latest' pulls remote templates and refreshes Espanso output."""
    from espansr.core.remote import RemotePullOutcome

    window = _make_window(qtbot, Config(), tmp_path=tmp_path)

    with (
        patch("espansr.core.remote.RemoteManager") as mock_manager_cls,
        patch("espansr.integrations.espanso.sync_to_espanso", return_value=True) as mock_sync,
        patch.object(window._browser, "refresh"),
        patch.object(window, "_update_espanso_status"),
    ):
        mock_manager_cls.return_value.pull_with_result.return_value = RemotePullOutcome(
            status="changed",
            changed_files=["sig.json"],
            branch="main",
        )

        window._pull_latest_btn.click()

    mock_manager_cls.return_value.pull_with_result.assert_called_once()
    mock_sync.assert_called_once_with(update_bundled=False)
    assert "pulled latest" in window.statusBar().currentMessage().lower()


def test_pull_latest_failure_shows_status_message(qtbot, tmp_path):
    """A pull failure shows a clear status-bar error."""
    from espansr.core.remote import RemoteError

    window = _make_window(qtbot, Config(), tmp_path=tmp_path)

    with (
        patch("espansr.core.remote.RemoteManager") as mock_manager_cls,
        patch.object(window, "_update_espanso_status"),
    ):
        mock_manager_cls.return_value.pull_with_result.side_effect = RemoteError(
            "Failed to fetch from remote: network unavailable"
        )

        window._pull_latest_btn.click()

    msg = window.statusBar().currentMessage().lower()
    assert "pull latest failed" in msg
    assert "network unavailable" in msg


def test_save_triggers_sync_without_bundled_update(qtbot, tmp_path):
    """Saving an edited template immediately regenerates Espanso output."""
    manager = TemplateManager(templates_dir=tmp_path / "templates")
    template = manager.create(name="Meta", content="old body", trigger=":meta")
    window = _make_window(qtbot, Config(), tm=manager, tmp_path=tmp_path)
    window._editor.load_template(template)
    window._editor._content_edit.setPlainText("new body")

    with (
        patch("espansr.ui.template_editor.get_template_manager", return_value=manager),
        patch("espansr.ui.template_browser.get_template_manager", return_value=manager),
        patch("espansr.integrations.validate.validate_all", return_value=[]),
        patch("espansr.ui.main_window.get_config_manager"),
        patch("espansr.integrations.espanso.sync_to_espanso", return_value=True) as mock_sync,
    ):
        window._editor._save()

    reloaded = manager.get("Meta")
    assert reloaded is not None
    assert reloaded.content == "new body"
    mock_sync.assert_called_once_with(update_bundled=False)


def test_sync_saves_dirty_editor_before_writing(qtbot, tmp_path):
    """Sync Now persists dirty editor state before generating Espanso YAML."""
    manager = TemplateManager(templates_dir=tmp_path / "templates")
    template = manager.create(name="Verify", content="old body", trigger=":verify")
    window = _make_window(qtbot, Config(), tm=manager, tmp_path=tmp_path)
    window._editor.load_template(template)
    window._editor._content_edit.setPlainText("new body")

    with (
        patch("espansr.ui.template_editor.get_template_manager", return_value=manager),
        patch("espansr.ui.template_browser.get_template_manager", return_value=manager),
        patch("espansr.integrations.validate.validate_all", return_value=[]),
        patch("espansr.ui.main_window.get_config_manager"),
        patch("espansr.integrations.espanso.sync_to_espanso", return_value=True) as mock_sync,
    ):
        window._do_sync()

    reloaded = manager.get("Verify")
    assert reloaded is not None
    assert reloaded.content == "new body"
    mock_sync.assert_called_once_with(update_bundled=False)


def test_sync_success_shows_status_message(qtbot, tmp_path):
    """A successful sync shows 'Sync successful' in the status bar."""
    window = _make_window(qtbot, Config(), tmp_path=tmp_path)

    with (
        patch(
            "espansr.integrations.espanso.sync_to_espanso",
            return_value=True,
        ),
        patch.object(window._browser, "refresh"),  # prevent "Loaded N" overwrite
    ):
        window._sync_btn.click()

    assert "successful" in window.statusBar().currentMessage().lower()


def test_sync_failure_shows_status_message(qtbot, tmp_path):
    """A failed sync shows a failure message in the status bar."""
    window = _make_window(qtbot, Config(), tmp_path=tmp_path)

    with patch(
        "espansr.integrations.espanso.sync_to_espanso",
        return_value=False,
    ):
        window._sync_btn.click()

    assert "fail" in window.statusBar().currentMessage().lower()


# ── Geometry persistence ─────────────────────────────────────────────────────


def test_close_event_saves_geometry(qtbot, tmp_path):
    """closeEvent() persists window geometry fields to config via save_config."""
    config = Config()
    window = _make_window(qtbot, config, tmp_path=tmp_path)
    window.show()

    with patch("espansr.ui.main_window.save_config") as mock_save:
        window.close()

    mock_save.assert_called_once()
    saved_config = mock_save.call_args[0][0]
    # geometry blob must be non-empty
    assert saved_config.ui.window_geometry != ""
    # x/y must be realistic ints
    assert isinstance(saved_config.ui.window_x, int)
    assert isinstance(saved_config.ui.window_y, int)
    assert isinstance(saved_config.ui.window_maximized, bool)


def test_geometry_restored_from_config(qtbot, tmp_path):
    """_restore_geometry() applies a saved geometry blob on startup."""
    # Create a throwaway window to capture a real geometry blob.
    config = Config()
    first = _make_window(qtbot, config, tmp_path=tmp_path)
    first.resize(800, 500)
    first.show()
    geometry_blob = first.saveGeometry()
    config.ui.window_geometry = base64.b64encode(geometry_blob.data()).decode()

    # Create a second window using the saved blob.
    second = _make_window(qtbot, config, tmp_path=tmp_path)
    second.show()

    # The restored window must have approximately the same dimensions.
    # The offscreen Qt platform may adjust geometry by a few pixels.
    assert abs(second.width() - first.width()) <= 10
    assert abs(second.height() - first.height()) <= 10


# ── Last-selected template restore ───────────────────────────────────────────


def test_last_template_restored_on_startup(qtbot, tmp_path):
    """MainWindow selects the template named in UIConfig.last_template on startup."""
    manager = TemplateManager(templates_dir=tmp_path / "templates")
    manager.create(name="My Snippet", content="hello", trigger=":hi")

    config = Config()
    config.ui.last_template = "My Snippet"

    window = _make_window(qtbot, config, tm=manager, tmp_path=tmp_path)

    selected = window._browser.get_current_template()
    assert selected is not None
    assert selected.name == "My Snippet"


def test_no_selection_when_last_template_empty(qtbot, tmp_path):
    """No template is selected when UIConfig.last_template is empty."""
    config = Config()
    config.ui.last_template = ""

    window = _make_window(qtbot, config, tmp_path=tmp_path)

    assert window._browser.get_current_template() is None


def test_last_template_saved_on_close(qtbot, tmp_path):
    """closeEvent() writes the currently-selected template name to UIConfig."""
    manager = TemplateManager(templates_dir=tmp_path / "templates")
    manager.create(name="Pick Me", content="body", trigger=":pick")

    config = Config()
    window = _make_window(qtbot, config, tm=manager, tmp_path=tmp_path)

    # Programmatically select a template.
    window._browser.select_template_by_name("Pick Me")

    with patch("espansr.ui.main_window.save_config") as mock_save:
        window.close()

    saved_config = mock_save.call_args[0][0]
    assert saved_config.ui.last_template == "Pick Me"
