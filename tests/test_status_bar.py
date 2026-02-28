"""Tests for GUI persistent status bar and sync feedback.

Spec: /specs/gui-status-bar-feedback.md
Covers: SyncResult dataclass, permanent Espanso status indicator,
sync count feedback in status bar.
"""

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


def _make_window(qtbot, config, tm=None, match_dir=None, tmp_path=None, espanso_dir=...):
    """Create a patched MainWindow.

    Args:
        espanso_dir: Path to mock as Espanso config dir.
            Defaults to *tmp_path* when the sentinel (``...``) is passed.
            Pass ``None`` explicitly to simulate missing Espanso.
    """
    from espansr.ui.main_window import MainWindow

    if espanso_dir is ...:
        espanso_dir = tmp_path

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
                return_value=espanso_dir,
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


# ── SyncResult dataclass ─────────────────────────────────────────────────────


class TestSyncResult:
    """Tests for the SyncResult dataclass."""

    def test_sync_result_fields(self):
        """SyncResult has success, count, and errors fields."""
        from espansr.integrations.espanso import SyncResult

        result = SyncResult(success=True, count=5, errors=[])
        assert result.success is True
        assert result.count == 5
        assert result.errors == []

    def test_sync_result_bool_true(self):
        """bool(SyncResult) returns True when success is True."""
        from espansr.integrations.espanso import SyncResult

        result = SyncResult(success=True, count=3, errors=[])
        assert bool(result) is True

    def test_sync_result_bool_false(self):
        """bool(SyncResult) returns False when success is False."""
        from espansr.integrations.espanso import SyncResult

        result = SyncResult(success=False, count=0, errors=["err"])
        assert bool(result) is False

    def test_sync_to_espanso_returns_bool(self, tmp_path):
        """sync_to_espanso() returns a bool for backward compatibility."""
        from espansr.integrations.espanso import sync_to_espanso

        with (
            patch(
                "espansr.integrations.espanso.get_match_dir",
                return_value=tmp_path,
            ),
            patch("espansr.integrations.espanso.clean_stale_espanso_files"),
            patch("espansr.integrations.espanso.validate_all", return_value=[]),
            patch(
                "espansr.integrations.espanso.get_template_manager"
            ) as mock_mgr,
            patch("espansr.integrations.espanso.is_wsl2", return_value=False),
        ):
            mock_mgr.return_value.iter_with_triggers.return_value = []
            result = sync_to_espanso()

        assert result is True


# ── Permanent Espanso status indicator ───────────────────────────────────────


class TestEspansoStatusIndicator:
    """Tests for the permanent Espanso status label in the status bar."""

    def test_espanso_status_label_exists(self, qtbot, tmp_path):
        """MainWindow has an _espanso_status QLabel."""
        from PyQt6.QtWidgets import QLabel

        window = _make_window(qtbot, Config(), tmp_path=tmp_path)
        assert hasattr(window, "_espanso_status")
        assert isinstance(window._espanso_status, QLabel)

    def test_espanso_status_shows_path(self, qtbot, tmp_path):
        """Permanent status shows the Espanso path when detected."""
        window = _make_window(
            qtbot, Config(), tmp_path=tmp_path, espanso_dir=tmp_path
        )
        assert str(tmp_path) in window._espanso_status.text()

    def test_espanso_status_shows_not_found(self, qtbot, tmp_path):
        """Permanent status shows 'not found' when Espanso is not detected."""
        window = _make_window(
            qtbot, Config(), tmp_path=tmp_path, espanso_dir=None
        )
        assert "not found" in window._espanso_status.text().lower()

    def test_espanso_label_prefix(self, qtbot, tmp_path):
        """Permanent status text begins with 'Espanso:'."""
        window = _make_window(qtbot, Config(), tmp_path=tmp_path)
        assert window._espanso_status.text().startswith("Espanso:")


# ── Sync feedback with template count ────────────────────────────────────────


class TestSyncFeedback:
    """Tests for richer sync feedback in the status bar."""

    def test_sync_success_shows_count(self, qtbot, tmp_path):
        """A successful sync shows the template count in the status bar."""
        import espansr.integrations.espanso as espanso_mod

        def _mock_sync():
            espanso_mod._last_sync_count = 3
            return True

        window = _make_window(qtbot, Config(), tmp_path=tmp_path)

        with (
            patch(
                "espansr.integrations.espanso.sync_to_espanso",
                side_effect=_mock_sync,
            ),
            patch.object(window._browser, "refresh"),
        ):
            window._sync_btn.click()

        msg = window.statusBar().currentMessage()
        assert "3" in msg
        assert "synced" in msg.lower()

    def test_sync_blocked_shows_error_count(self, qtbot, tmp_path):
        """A blocked sync shows the error count in the status bar."""
        from espansr.integrations.validate import ValidationWarning

        window = _make_window(qtbot, Config(), tmp_path=tmp_path)

        mock_warnings = [
            ValidationWarning(
                severity="error", message="bad trigger", template_name="t1"
            ),
            ValidationWarning(
                severity="error", message="short trigger", template_name="t2"
            ),
        ]

        with patch(
            "espansr.integrations.validate.validate_all",
            return_value=mock_warnings,
        ):
            window._sync_btn.click()

        msg = window.statusBar().currentMessage()
        assert "blocked" in msg.lower() or "error" in msg.lower()
        assert "2" in msg

    def test_espanso_status_updates_after_sync(self, qtbot, tmp_path):
        """The permanent indicator refreshes after a sync."""
        window = _make_window(qtbot, Config(), tmp_path=tmp_path)

        with (
            patch(
                "espansr.integrations.espanso.sync_to_espanso",
                return_value=True,
            ),
            patch.object(window._browser, "refresh"),
            patch.object(window, "_update_espanso_status") as mock_update,
        ):
            window._sync_btn.click()

        mock_update.assert_called()

    def test_transient_message_coexists_with_permanent(self, qtbot, tmp_path):
        """Transient status messages don't remove the permanent indicator."""
        window = _make_window(qtbot, Config(), tmp_path=tmp_path)

        # Show a transient message
        window.statusBar().showMessage("Transient", 5000)

        # Permanent widget should still have text
        assert window._espanso_status.text() != ""
