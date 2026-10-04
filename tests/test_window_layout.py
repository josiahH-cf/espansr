"""Desktop window and pane behavior, including reopening and concurrent saves."""

from pathlib import Path

import pytest
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QApplication

from espansr.core.command_catalog import build_command_catalog
from espansr.core.config import Config, load_config_fresh, save_config
from espansr.core.templates import TemplateManager
from espansr.core.workflows import load_workflow_catalog
from espansr.ui.commands_popup import CommandsPopupDialog, launch_commands_popup

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def reference(qtbot):
    config = Config()
    config.ui.theme_default_migrated = True
    save_config(config)
    catalog = load_workflow_catalog([ROOT / "templates" / "_meta" / "workflows"])
    entries = build_command_catalog(TemplateManager(ROOT / "templates"), config, catalog)
    dialog = CommandsPopupDialog(entries=entries, workflow_catalog=catalog)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.resize(1280, 1100)
    QApplication.processEvents()
    return dialog


def _drag(qtbot, splitter, distance):
    handle = splitter.handle(1)
    start = handle.rect().center()
    delta = (
        QPoint(distance, 0)
        if splitter.orientation() == Qt.Orientation.Horizontal
        else QPoint(0, distance)
    )
    qtbot.mousePress(handle, Qt.MouseButton.LeftButton, pos=start)
    qtbot.mouseMove(handle, start + delta)
    qtbot.mouseRelease(handle, Qt.MouseButton.LeftButton, pos=start + delta)
    QApplication.processEvents()


def _ratio(splitter):
    sizes = splitter.sizes()
    return sizes[0] / sum(sizes)


def test_reference_maximizes_restores_and_keeps_work_when_pin_changes(reference, qtbot):
    assert reference.windowFlags() & Qt.WindowType.WindowMinimizeButtonHint
    assert reference.windowFlags() & Qt.WindowType.WindowMaximizeButtonHint
    if QApplication.platformName() == "windows":
        import ctypes

        style = ctypes.windll.user32.GetWindowLongW(int(reference.winId()), -16)
        assert style & 0x00010000  # Native WS_MAXIMIZEBOX
        assert style & 0x00020000  # Native WS_MINIMIZEBOX
    reference._search_edit.setText("finance")
    reference._scratchpad.setPlainText("Keep working")
    reference.showMaximized()
    qtbot.waitUntil(reference.isMaximized)
    QApplication.processEvents()
    reference._pin_check.setChecked(False)
    qtbot.waitUntil(reference.isMaximized)
    QApplication.processEvents()
    assert reference.isVisible()
    assert reference._scratchpad.toPlainText() == "Keep working"
    assert reference._search_edit.text() == "finance"
    reference.showNormal()
    qtbot.waitUntil(lambda: not reference.isMaximized())
    assert reference._scratchpad.toPlainText() == "Keep working"
    reference._selected_entry = next(
        entry for entry in reference._entries if entry.trigger == ":finance-review"
    )
    reference._copy_prompt(reference._selected_entry)
    assert QApplication.clipboard().text() == reference._selected_entry.content


def test_modeless_launch_remains_open_after_function_returns_and_releases_on_close(qtbot):
    app = QApplication.instance()
    launch_commands_popup(entries=[])
    reference = app._espansr_references[-1]
    assert reference.isVisible()
    assert not reference.isModal()
    reference.showMinimized()
    QApplication.processEvents()
    assert reference.isMinimized()
    reference.showNormal()
    QApplication.processEvents()
    assert reference.isVisible() and not reference.isMinimized()
    reference.close()
    qtbot.waitUntil(lambda: reference not in app._espansr_references)


def test_reference_reopens_maximized_with_adjusted_panes_and_empty_scratchpad(reference, qtbot):
    _drag(qtbot, reference._body, 220)
    assert reference._groups.width() > 300
    _drag(qtbot, reference._reference_splitter, -200)
    assert reference._scratchpad.height() > 110
    reference._scratchpad.setPlainText("Do not persist")
    reference.showMaximized()
    qtbot.waitUntil(reference.isMaximized)
    QApplication.processEvents()
    sidebar_ratio = _ratio(reference._body)
    scratchpad_ratio = _ratio(reference._reference_splitter)
    reference.close()
    second = CommandsPopupDialog(
        entries=reference._entries, workflow_catalog=reference._workflow_catalog
    )
    qtbot.addWidget(second)
    second.show()
    qtbot.waitUntil(second.isMaximized)
    QApplication.processEvents()
    assert abs(_ratio(second._body) - sidebar_ratio) < 0.08
    assert abs(_ratio(second._reference_splitter) - scratchpad_ratio) < 0.08
    assert second._scratchpad.toPlainText() == ""


@pytest.mark.parametrize("pane", ["commands", "processes"])
def test_reference_central_panes_resize_by_dragging_and_preserve_selection(reference, qtbot, pane):
    if pane == "processes":
        reference._view_combo.setCurrentText("Processes")
    else:
        reference._summary_table.setCurrentCell(0, 0)
    QApplication.processEvents()
    splitter = reference._layout_splitters[pane]
    before = splitter.sizes()
    _drag(qtbot, splitter, 80)
    assert abs(splitter.sizes()[0] - before[0]) > 30
    assert all(size > 0 for size in splitter.sizes())
    if pane == "commands":
        assert reference._selected_entry is not None
        reference._detail_widget._copy_prompt_btn.click()
        assert QApplication.clipboard().text() == reference._selected_entry.content
    else:
        assert reference._process_table.currentRow() == 0


def test_editor_maximizes_and_reopens_with_panes_and_preview_content(make_window, qtbot):
    config = Config()
    config.ui.show_previews = True
    config.ui.theme_default_migrated = True
    save_config(config)
    first = make_window(config)
    first.show()
    first.resize(1280, 1100)
    first._editor._trigger_edit.setText(":example")
    first._editor._content_edit.setPlainText("Still editable")
    QApplication.processEvents()
    _drag(qtbot, first._splitter, 130)
    _drag(qtbot, first._editor._editor_splitter, -100)
    _drag(qtbot, first._editor._preview_container, 35)
    first.showMaximized()
    qtbot.waitUntil(first.isMaximized)
    QApplication.processEvents()
    assert "Still editable" in first._editor._output_preview.toPlainText()
    first.showNormal()
    qtbot.waitUntil(lambda: not first.isMaximized())
    first.showMaximized()
    qtbot.waitUntil(first.isMaximized)
    QApplication.processEvents()
    first.close()
    saved = load_config_fresh()
    assert saved.ui.window_maximized
    assert set(saved.ui.panel_sizes) >= {"editor", "previews"}
    second = make_window(saved)
    second.show()
    qtbot.waitUntil(second.isMaximized)
    QApplication.processEvents()
    assert not second._editor._preview_container.isHidden()
    for name in ("editor", "previews"):
        assert (
            abs(_ratio(second._layout_splitters[name]) - _ratio(first._layout_splitters[name]))
            < 0.08
        )
    assert abs(_ratio(second._splitter) - _ratio(first._splitter)) < 0.08


def test_hidden_editor_previews_retain_their_expanded_sizes(make_window):
    config = Config()
    config.ui.show_previews = True
    config.ui.theme_default_migrated = True
    save_config(config)
    window = make_window(config)
    window.show()
    window.resize(1280, 1100)
    QApplication.processEvents()
    window._editor._editor_splitter.setSizes([600, 300])
    window._on_splitter_moved(0, 1)
    previous = list(load_config_fresh().ui.panel_sizes["editor"])
    window._toggle_preview()
    window.close()
    saved = load_config_fresh()
    assert saved.ui.panel_sizes["editor"] == previous
    saved.ui.show_previews = True
    save_config(saved)
    second = make_window(saved)
    second.show()
    QApplication.processEvents()
    assert abs(_ratio(second._editor._editor_splitter) - previous[0] / sum(previous)) < 0.08


def test_open_editor_and_reference_preserve_each_others_preferences(make_window, reference, qtbot):
    window = make_window(load_config_fresh())
    window.show()
    external = load_config_fresh()
    external.discovery.favorite_triggers = [":finance-review"]
    save_config(external)
    _drag(qtbot, reference._body, 150)
    reference._pin_check.setChecked(False)
    reference.close()
    reference_geometry = load_config_fresh().discovery.window_geometry
    window._on_theme_changed("Light")
    window._toggle_preview()
    window.close()
    saved = load_config_fresh()
    assert saved.discovery.favorite_triggers == [":finance-review"]
    assert saved.discovery.stay_on_top is False
    assert saved.discovery.window_geometry == reference_geometry
    assert "sidebar" in saved.discovery.panel_sizes
    assert saved.ui.theme == "light"
    assert saved.ui.show_previews


@pytest.mark.parametrize("sizes", [None, "bad", [0, 0], [-5, 20], [1], [True, 20], [2**60, 20]])
def test_invalid_saved_layout_does_not_prevent_either_window_opening(qtbot, make_window, sizes):
    config = Config()
    config.ui.theme_default_migrated = True
    config.ui.window_geometry = "invalid geometry"
    config.discovery.window_geometry = "invalid geometry"
    config.ui.splitter_sizes = sizes
    config.ui.panel_sizes = {"editor": sizes, "previews": sizes}
    config.discovery.panel_sizes = {"sidebar": sizes, "scratchpad": sizes}
    save_config(config)
    reference = CommandsPopupDialog(entries=[])
    window = make_window(config)
    qtbot.addWidget(reference)
    reference.show()
    window.show()
    QApplication.processEvents()
    assert reference.isVisible() and window.isVisible()
    assert all(size > 0 for size in reference._body.sizes())
    assert all(size > 0 for size in window._splitter.sizes())
