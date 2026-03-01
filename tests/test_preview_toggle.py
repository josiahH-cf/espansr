"""Tests for toggleable YAML preview feature.

Spec: /specs/toggleable-yaml-preview.md
Covers: toggle shows/hides previews, persistence via config, default state,
keyboard shortcut, tooltip reflects state, previews update when visible.
"""

import contextlib
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


def _make_window(qtbot, config, tm=None, tmp_path=None):
    """Create a patched MainWindow for toggle tests."""
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
        stack.enter_context(patch("espansr.ui.main_window.save_config"))
        stack.enter_context(patch("espansr.ui.template_browser.get_config"))
        stack.enter_context(patch("espansr.ui.template_editor.get_config"))
        stack.enter_context(
            patch(
                "espansr.integrations.espanso.get_match_dir",
                return_value=None,
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


def test_toggle_button_exists(qtbot, tmp_path):
    """MainWindow has a preview toggle button in the toolbar."""
    window = _make_window(qtbot, Config(), tmp_path=tmp_path)
    assert hasattr(window, "_preview_toggle_btn")


def test_toggle_hides_and_shows_previews(qtbot, tmp_path):
    """Clicking toggle button shows/hides the editor preview container."""
    config = Config()
    config.ui.show_previews = False
    window = _make_window(qtbot, config, tmp_path=tmp_path)

    # Default is false → hidden
    assert window._editor._preview_container.isHidden()

    # Click to show
    window._preview_toggle_btn.click()
    assert not window._editor._preview_container.isHidden()

    # Click to hide
    window._preview_toggle_btn.click()
    assert window._editor._preview_container.isHidden()


def test_toggle_persists_to_config(qtbot, tmp_path):
    """Toggling preview updates config.ui.show_previews."""
    config = Config()
    config.ui.show_previews = False
    window = _make_window(qtbot, config, tmp_path=tmp_path)

    window._preview_toggle_btn.click()
    assert config.ui.show_previews is True

    window._preview_toggle_btn.click()
    assert config.ui.show_previews is False


def test_toggle_button_tooltip_reflects_state(qtbot, tmp_path):
    """Toggle button tooltip changes based on state."""
    config = Config()
    config.ui.show_previews = False
    window = _make_window(qtbot, config, tmp_path=tmp_path)

    # Previews are hidden → tooltip should say "Show"
    assert "Show" in window._preview_toggle_btn.toolTip()

    window._preview_toggle_btn.click()
    # Previews are visible → tooltip should say "Hide"
    assert "Hide" in window._preview_toggle_btn.toolTip()


def test_shortcut_toggles_preview(qtbot, tmp_path):
    """Ctrl+Shift+P shortcut is bound and toggles previews."""
    config = Config()
    window = _make_window(qtbot, config, tmp_path=tmp_path)

    assert hasattr(window, "_shortcut_preview")
    assert window._shortcut_preview.key() == QKeySequence("Ctrl+Shift+P")

    with patch.object(window, "_toggle_preview") as mock_toggle:
        window._shortcut_preview.activated.emit()

    mock_toggle.assert_called_once()


def test_previews_visible_on_startup_when_config_true(qtbot, tmp_path):
    """When config.ui.show_previews is True, previews are visible at launch."""
    config = Config()
    config.ui.show_previews = True
    window = _make_window(qtbot, config, tmp_path=tmp_path)

    assert not window._editor._preview_container.isHidden()


def test_previews_hidden_on_startup_when_config_false(qtbot, tmp_path):
    """When config.ui.show_previews is False (default), previews are hidden at launch."""
    config = Config()
    config.ui.show_previews = False
    window = _make_window(qtbot, config, tmp_path=tmp_path)

    assert window._editor._preview_container.isHidden()
