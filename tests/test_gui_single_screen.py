"""Tests for the single-screen GUI layout (Issue #3).

Covers: toolbar publish button, sync_to_espanso() call, geometry persistence,
and last_template restore on startup.

Windows come from the shared ``make_window`` factory in ``tests/conftest.py``.
"""

import base64
from unittest.mock import patch

from espansr.core.config import Config
from espansr.core.templates import TemplateManager

# ── Toolbar: Publish button ──────────────────────────────────────────────────


def test_publish_button_in_toolbar(make_window):
    """MainWindow has a 'Publish' QPushButton in the toolbar."""
    from PyQt6.QtWidgets import QPushButton

    window = make_window(Config())

    sync_btn = window._sync_btn
    assert isinstance(sync_btn, QPushButton)
    assert "Publish" in sync_btn.text()


def test_pull_latest_button_in_toolbar(make_window):
    """MainWindow has a 'Pull Latest' QPushButton in the toolbar."""
    from PyQt6.QtWidgets import QPushButton

    window = make_window(Config())

    pull_btn = window._pull_latest_btn
    assert isinstance(pull_btn, QPushButton)
    assert "Pull" in pull_btn.text()


def test_sync_calls_sync_to_espanso(make_window):
    """Clicking Publish calls sync_to_espanso() exactly once."""
    window = make_window(Config())

    with patch(
        "espansr.integrations.espanso.sync_to_espanso",
        return_value=True,
    ) as mock_sync:
        window._sync_btn.click()

    mock_sync.assert_called_once_with(update_bundled=True)


def test_pull_latest_calls_remote_and_sync(make_window):
    """Clicking 'Pull Latest' pulls remote templates and refreshes Espanso output."""
    from espansr.core.remote import RemotePullOutcome

    window = make_window(Config())

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


def test_pull_latest_failure_shows_status_message(make_window):
    """A pull failure shows a clear status-bar error."""
    from espansr.core.remote import RemoteError

    window = make_window(Config())

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


def test_save_triggers_sync_without_bundled_update(make_window, tmp_path):
    """Saving an edited template immediately regenerates Espanso output."""
    manager = TemplateManager(templates_dir=tmp_path / "templates")
    template = manager.create(name="Meta", content="old body", trigger=":meta")
    window = make_window(Config(), tm=manager)
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


def test_sync_saves_dirty_editor_before_writing(make_window, tmp_path):
    """Publish persists dirty editor state before generating Espanso YAML."""
    manager = TemplateManager(templates_dir=tmp_path / "templates")
    template = manager.create(name="Verify", content="old body", trigger=":verify")
    window = make_window(Config(), tm=manager)
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


def test_sync_success_shows_status_message(make_window):
    """A successful publish shows a success message in the status bar."""
    window = make_window(Config())

    with (
        patch(
            "espansr.integrations.espanso.sync_to_espanso",
            return_value=True,
        ),
        patch.object(window._browser, "refresh"),  # prevent "Loaded N" overwrite
    ):
        window._sync_btn.click()

    assert "successful" in window.statusBar().currentMessage().lower()


def test_sync_failure_shows_status_message(make_window):
    """A failed publish shows a failure message in the status bar."""
    window = make_window(Config())

    with patch(
        "espansr.integrations.espanso.sync_to_espanso",
        return_value=False,
    ):
        window._sync_btn.click()

    assert "fail" in window.statusBar().currentMessage().lower()


def test_delete_publishes_remaining_templates(make_window, tmp_path):
    """Deleting after the undo window publishes the remaining templates."""
    manager = TemplateManager(templates_dir=tmp_path / "templates")
    manager.create(name="Delete Me", content="old body", trigger=":delete")
    window = make_window(Config(), tm=manager)
    window._browser.select_template_by_name("Delete Me")

    with (
        patch("espansr.ui.template_browser.get_template_manager", return_value=manager),
        patch("espansr.integrations.validate.validate_all", return_value=[]),
        patch("espansr.ui.main_window.get_config_manager"),
        patch("espansr.integrations.espanso.sync_to_espanso", return_value=True) as mock_sync,
    ):
        window._browser.start_delete()
        window._browser._finalize_delete()

    assert manager.get("Delete Me") is None
    mock_sync.assert_called_once_with(update_bundled=False)


# ── Geometry persistence ─────────────────────────────────────────────────────


def test_close_event_saves_geometry(make_window):
    """closeEvent() persists window geometry fields to config via save_config."""
    config = Config()
    window = make_window(config)
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


def test_geometry_restored_from_config(make_window):
    """_restore_geometry() applies a saved geometry blob on startup."""
    # Create a throwaway window to capture a real geometry blob.
    config = Config()
    first = make_window(config)
    first.resize(800, 500)
    first.show()
    geometry_blob = first.saveGeometry()
    config.ui.window_geometry = base64.b64encode(geometry_blob.data()).decode()

    # Create a second window using the saved blob.
    second = make_window(config)
    second.show()

    # The restored window must have approximately the same dimensions.
    # The offscreen Qt platform may adjust geometry by a few pixels.
    assert abs(second.width() - first.width()) <= 10
    assert abs(second.height() - first.height()) <= 10


# ── Last-selected template restore ───────────────────────────────────────────


def test_last_template_restored_on_startup(make_window, tmp_path):
    """MainWindow selects the template named in UIConfig.last_template on startup."""
    manager = TemplateManager(templates_dir=tmp_path / "templates")
    manager.create(name="My Snippet", content="hello", trigger=":hi")

    config = Config()
    config.ui.last_template = "My Snippet"

    window = make_window(config, tm=manager)

    selected = window._browser.get_current_template()
    assert selected is not None
    assert selected.name == "My Snippet"


def test_no_selection_when_last_template_empty(make_window):
    """No template is selected when UIConfig.last_template is empty."""
    config = Config()
    config.ui.last_template = ""

    window = make_window(config)

    assert window._browser.get_current_template() is None


def test_last_template_saved_on_close(make_window, tmp_path):
    """closeEvent() writes the currently-selected template name to UIConfig."""
    manager = TemplateManager(templates_dir=tmp_path / "templates")
    manager.create(name="Pick Me", content="body", trigger=":pick")

    config = Config()
    window = make_window(config, tm=manager)

    # Programmatically select a template.
    window._browser.select_template_by_name("Pick Me")

    with patch("espansr.ui.main_window.save_config") as mock_save:
        window.close()

    saved_config = mock_save.call_args[0][0]
    assert saved_config.ui.last_template == "Pick Me"
