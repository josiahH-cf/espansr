"""Tests for theme system: light theme, auto-detection, and runtime switching.

Covers spec: /specs/gui-dark-mode.md
"""

import re
from unittest.mock import MagicMock, patch

import pytest

# ── Helpers ──────────────────────────────────────────────────────────────────

# Widget selectors that DARK_THEME covers — LIGHT_THEME must match all of them.
REQUIRED_WIDGET_SELECTORS = [
    "QMainWindow",
    "QLabel",
    "QLineEdit",
    "QTextEdit",
    "QPlainTextEdit",
    "QPushButton",
    "QPushButton:hover",
    "QPushButton:disabled",
    "QPushButton#secondary",
    "QPushButton#danger",
    "QListWidget",
    "QListWidget::item",
    "QListWidget::item:selected",
    "QTreeWidget",
    "QTreeWidget::item:selected",
    "QSplitter::handle",
    "QScrollBar:vertical",
    "QScrollBar::handle:vertical",
    "QScrollBar:horizontal",
    "QScrollBar::handle:horizontal",
    "QMenuBar",
    "QMenu",
    "QStatusBar",
    "QGroupBox",
    "QTabWidget::pane",
    "QTabBar::tab",
    "QTabBar::tab:selected",
    "QComboBox",
    "QComboBox::drop-down",
    "QCheckBox",
    "QCheckBox::indicator",
    "QCheckBox::indicator:checked",
    "QToolTip",
    "QToolBar",
    "VariableRowWidget",
]


# ── AC 1: LIGHT_THEME widget coverage ───────────────────────────────────────


class TestLightThemeWidgetCoverage:
    """LIGHT_THEME must style the same widget set as DARK_THEME."""

    def test_light_theme_is_not_stub(self):
        """LIGHT_THEME contains more than just a base QWidget rule."""
        from espansr.ui.theme import LIGHT_THEME

        assert len(LIGHT_THEME) > 500, "LIGHT_THEME looks like a stub"

    @pytest.mark.parametrize("selector", REQUIRED_WIDGET_SELECTORS)
    def test_light_theme_contains_selector(self, selector):
        """LIGHT_THEME contains a CSS rule for the given widget selector."""
        from espansr.ui.theme import LIGHT_THEME

        # Normalize whitespace — Qt CSS is forgiving
        assert selector in LIGHT_THEME, f"LIGHT_THEME missing selector: {selector}"

    def test_light_theme_uses_light_background(self):
        """LIGHT_THEME uses a light background color for QMainWindow."""
        from espansr.ui.theme import LIGHT_THEME

        # Should have a high-value hex color (light), not #1e1e1e-style dark
        match = re.search(r"background-color:\s*#([0-9a-fA-F]{6})", LIGHT_THEME)
        assert match, "No background-color found in LIGHT_THEME"
        hex_val = match.group(1)
        r, g, b = int(hex_val[:2], 16), int(hex_val[2:4], 16), int(hex_val[4:], 16)
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        assert luminance > 180, f"LIGHT_THEME background is too dark (luminance={luminance:.0f})"


# ── AC 2: System theme detection ────────────────────────────────────────────


class TestDetectSystemTheme:
    """detect_system_theme() returns 'dark' or 'light'; never raises."""

    def test_returns_valid_value(self):
        """detect_system_theme() returns 'dark' or 'light'."""
        from espansr.ui.theme import detect_system_theme

        result = detect_system_theme()
        assert result in ("dark", "light")

    def test_returns_dark_on_dark_system(self):
        """When OS reports dark mode, detect_system_theme() returns 'dark'."""
        from espansr.ui.theme import detect_system_theme

        mock_hints = MagicMock()
        # Qt.ColorScheme.Dark == 2 in Qt 6.5+
        mock_hints.colorScheme.return_value = MagicMock(name="Dark", value=2)

        with patch("espansr.ui.theme.QApplication") as mock_app:
            mock_app.instance.return_value = MagicMock()
            mock_app.instance.return_value.styleHints.return_value = mock_hints
            assert detect_system_theme() == "dark"

    def test_returns_light_on_light_system(self):
        """When OS reports light mode, detect_system_theme() returns 'light'."""
        from espansr.ui.theme import detect_system_theme

        mock_hints = MagicMock()
        # Qt.ColorScheme.Light == 1 in Qt 6.5+
        mock_hints.colorScheme.return_value = MagicMock(name="Light", value=1)

        with patch("espansr.ui.theme.QApplication") as mock_app:
            mock_app.instance.return_value = MagicMock()
            mock_app.instance.return_value.styleHints.return_value = mock_hints
            assert detect_system_theme() == "light"

    def test_falls_back_to_dark_on_exception(self):
        """If detection fails entirely, fall back to 'dark'."""
        from espansr.ui.theme import detect_system_theme

        with patch("espansr.ui.theme.QApplication") as mock_app:
            mock_app.instance.return_value = None
            assert detect_system_theme() == "dark"


# ── AC 3/4: get_theme_stylesheet resolves "auto" ────────────────────────────


class TestGetThemeStylesheet:
    """get_theme_stylesheet() handles 'auto', 'dark', and 'light'."""

    def test_auto_resolves_to_real_stylesheet(self):
        """Passing 'auto' returns a non-empty stylesheet without crashing."""
        from espansr.ui.theme import get_theme_stylesheet

        result = get_theme_stylesheet(theme="auto")
        assert isinstance(result, str)
        assert len(result) > 500

    def test_dark_returns_dark_theme(self):
        """Explicit 'dark' returns the dark stylesheet."""
        from espansr.ui.theme import DARK_THEME, get_theme_stylesheet

        result = get_theme_stylesheet(theme="dark")
        assert DARK_THEME in result

    def test_light_returns_light_theme(self):
        """Explicit 'light' returns the light stylesheet."""
        from espansr.ui.theme import LIGHT_THEME, get_theme_stylesheet

        result = get_theme_stylesheet(theme="light")
        assert LIGHT_THEME in result

    def test_auto_with_dark_system(self):
        """'auto' on a dark system returns the dark stylesheet."""
        from espansr.ui.theme import DARK_THEME, get_theme_stylesheet

        with patch("espansr.ui.theme.detect_system_theme", return_value="dark"):
            result = get_theme_stylesheet(theme="auto")
            assert DARK_THEME in result

    def test_auto_with_light_system(self):
        """'auto' on a light system returns the light stylesheet."""
        from espansr.ui.theme import LIGHT_THEME, get_theme_stylesheet

        with patch("espansr.ui.theme.detect_system_theme", return_value="light"):
            result = get_theme_stylesheet(theme="auto")
            assert LIGHT_THEME in result


# ── AC 4: UIConfig.theme defaults to "auto" ─────────────────────────────────


class TestUIConfigDefault:
    """UIConfig.theme should default to 'auto'."""

    def test_auto_is_default(self):
        """A fresh UIConfig has theme='auto'."""
        from espansr.core.config import UIConfig

        cfg = UIConfig()
        assert cfg.theme == "auto"


# ── AC 5: Runtime theme switcher (toolbar combo box) ────────────────────────


class TestThemeComboBox:
    """Toolbar contains an Auto/Dark/Light combo box for runtime switching."""

    @pytest.fixture()
    def window(self, qtbot, tmp_path):
        """Create a patched MainWindow."""
        import contextlib
        from unittest.mock import patch as _patch

        from espansr.core.config import Config
        from espansr.ui.main_window import MainWindow

        with contextlib.ExitStack() as stack:
            stack.enter_context(_patch("espansr.ui.main_window.get_config", return_value=Config()))
            stack.enter_context(_patch("espansr.ui.main_window.get_config_manager"))
            stack.enter_context(_patch("espansr.ui.template_browser.get_config"))
            stack.enter_context(_patch("espansr.ui.template_editor.get_config"))
            stack.enter_context(
                _patch("espansr.integrations.espanso.get_match_dir", return_value=None)
            )
            stack.enter_context(
                _patch("espansr.integrations.espanso.get_espanso_config_dir", return_value=tmp_path)
            )
            stack.enter_context(
                _patch("espansr.integrations.espanso._get_candidate_paths", return_value=[])
            )
            stack.enter_context(_patch("espansr.ui.template_browser.get_template_manager"))
            window = MainWindow()
            qtbot.addWidget(window)
            yield window

    def test_combo_exists_in_toolbar(self, window):
        """MainWindow toolbar contains a theme QComboBox."""
        from PyQt6.QtWidgets import QComboBox

        assert hasattr(window, "_theme_combo")
        assert isinstance(window._theme_combo, QComboBox)

    def test_combo_has_three_items(self, window):
        """Theme combo has Auto, Dark, and Light items."""
        combo = window._theme_combo
        items = [combo.itemText(i) for i in range(combo.count())]
        assert items == ["Auto", "Dark", "Light"]

    def test_switching_theme_updates_stylesheet(self, window):
        """Changing the combo applies a new stylesheet."""
        # Force a known starting point so the comparison is deterministic
        window._theme_combo.setCurrentText("Dark")
        old_sheet = window.styleSheet()
        window._theme_combo.setCurrentText("Light")
        new_sheet = window.styleSheet()
        # The stylesheet should change (light vs dark content differs)
        assert old_sheet != new_sheet

    def test_switching_theme_updates_config(self, window):
        """Changing the combo updates config.ui.theme."""
        window._theme_combo.setCurrentText("Dark")
        assert window._config.ui.theme == "dark"

    def test_switching_theme_persists(self, window):
        """Changing the combo calls save_config."""
        with patch("espansr.ui.main_window.save_config") as mock_save:
            window._theme_combo.setCurrentText("Light")
            mock_save.assert_called_once()
