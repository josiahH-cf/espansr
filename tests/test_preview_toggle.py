"""Tests for toggleable YAML preview feature.

Spec: /specs/toggleable-yaml-preview.md
Covers: toggle shows/hides previews, persistence via config, default state,
keyboard shortcut, tooltip reflects state, previews update when visible.

Windows come from the shared ``make_window`` factory in ``tests/conftest.py``.
"""

from unittest.mock import patch

import pytest
from PyQt6.QtGui import QKeySequence

from espansr.core.config import Config, UIConfig
from espansr.core.templates import Template, TemplateManager

# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture()
def tm(tmp_path):
    """Create a TemplateManager backed by a temp directory."""
    return TemplateManager(templates_dir=tmp_path / "templates")


@pytest.fixture()
def _patch_editor(tm):
    """Patch get_template_manager and get_config for editor tests."""
    with (
        patch(
            "espansr.ui.template_editor.get_template_manager",
            return_value=tm,
        ),
        patch("espansr.ui.template_editor.get_config"),
    ):
        yield


@pytest.fixture()
def editor(qtbot, _patch_editor):
    """Create a TemplateEditorWidget for testing."""
    from espansr.ui.template_editor import TemplateEditorWidget

    widget = TemplateEditorWidget()
    qtbot.addWidget(widget)
    return widget


# ── Config default ──────────────────────────────────────────────────────────


def test_default_show_previews_false():
    """UIConfig defaults show_previews to False."""
    ui = UIConfig()
    assert ui.show_previews is False


def test_show_previews_round_trips():
    """show_previews survives to_dict / from_dict serialization."""
    config = Config()
    config.ui.show_previews = True
    data = config.to_dict()
    restored = Config.from_dict(data)
    assert restored.ui.show_previews is True


def test_from_dict_missing_show_previews():
    """from_dict with no show_previews key defaults to False."""
    data = {"ui": {"theme": "dark"}}
    config = Config.from_dict(data)
    assert config.ui.show_previews is False


# ── Editor container visibility ─────────────────────────────────────────────


def test_editor_has_preview_container(editor):
    """Editor exposes a _preview_container QWidget."""
    assert hasattr(editor, "_preview_container")
    from PyQt6.QtWidgets import QWidget

    assert isinstance(editor._preview_container, QWidget)


def test_set_previews_visible_shows(editor):
    """set_previews_visible(True) makes the preview container visible."""
    editor.set_previews_visible(True)
    assert not editor._preview_container.isHidden()


def test_set_previews_visible_hides(editor):
    """set_previews_visible(False) hides the preview container."""
    editor.set_previews_visible(False)
    assert editor._preview_container.isHidden()


def test_hidden_previews_not_visible(editor):
    """When hidden, the preview container is fully removed from layout."""
    editor.set_previews_visible(False)
    assert editor._preview_container.isHidden()
    # Child widgets are not individually hidden — they become invisible
    # because their parent container is hidden
    assert not editor._preview_container.isVisibleTo(editor)


def test_previews_update_when_visible(editor):
    """Previews still live-update when shown."""
    editor.set_previews_visible(True)
    t = Template(name="Test", content="Hello world", trigger=":test")
    editor.load_template(t)
    assert "Hello world" in editor._output_preview.toPlainText()
    assert "trigger" in editor._yaml_preview.toPlainText()


def test_previews_update_silently_when_hidden(editor):
    """Signal connections stay wired — previews update even when hidden."""
    editor.set_previews_visible(False)
    t = Template(name="Test", content="Hello world", trigger=":test")
    editor.load_template(t)
    # Content is there even though container is hidden
    assert "Hello world" in editor._output_preview.toPlainText()


# ── MainWindow toggle button ────────────────────────────────────────────────


def test_toggle_button_exists(make_window):
    """MainWindow has a preview toggle button in the toolbar."""
    window = make_window(Config())
    assert hasattr(window, "_preview_toggle_btn")


def test_toggle_hides_and_shows_previews(make_window):
    """Clicking toggle button shows/hides the editor preview container."""
    config = Config()
    config.ui.show_previews = False
    window = make_window(config)

    # Default is false → hidden
    assert window._editor._preview_container.isHidden()

    # Click to show
    window._preview_toggle_btn.click()
    assert not window._editor._preview_container.isHidden()

    # Click to hide
    window._preview_toggle_btn.click()
    assert window._editor._preview_container.isHidden()


def test_toggle_persists_to_config(make_window):
    """Toggling preview updates config.ui.show_previews."""
    config = Config()
    config.ui.show_previews = False
    window = make_window(config)

    window._preview_toggle_btn.click()
    assert config.ui.show_previews is True

    window._preview_toggle_btn.click()
    assert config.ui.show_previews is False


def test_toggle_button_tooltip_reflects_state(make_window):
    """Toggle button tooltip changes based on state."""
    config = Config()
    config.ui.show_previews = False
    window = make_window(config)

    # Previews are hidden → tooltip should say "Show"
    assert "Show" in window._preview_toggle_btn.toolTip()

    window._preview_toggle_btn.click()
    # Previews are visible → tooltip should say "Hide"
    assert "Hide" in window._preview_toggle_btn.toolTip()


def test_shortcut_toggles_preview(make_window):
    """Ctrl+Shift+P shortcut is bound and toggles previews."""
    config = Config()
    window = make_window(config)

    assert hasattr(window, "_shortcut_preview")
    assert window._shortcut_preview.key() == QKeySequence("Ctrl+Shift+P")

    with patch.object(window, "_toggle_preview") as mock_toggle:
        window._shortcut_preview.activated.emit()

    mock_toggle.assert_called_once()


def test_previews_visible_on_startup_when_config_true(make_window):
    """When config.ui.show_previews is True, previews are visible at launch."""
    config = Config()
    config.ui.show_previews = True
    window = make_window(config)

    assert not window._editor._preview_container.isHidden()


def test_previews_hidden_on_startup_when_config_false(make_window):
    """When config.ui.show_previews is False (default), previews are hidden at launch."""
    config = Config()
    config.ui.show_previews = False
    window = make_window(config)

    assert window._editor._preview_container.isHidden()
