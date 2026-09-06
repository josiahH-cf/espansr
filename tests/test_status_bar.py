"""Tests for GUI persistent status bar and publish feedback.

Spec: /specs/gui-status-bar-feedback.md
Covers: SyncResult dataclass, permanent Espanso status indicator,
publish count feedback in status bar.

Windows come from the shared ``make_window`` factory in ``tests/conftest.py``;
``espanso_dir`` defaults to ``tmp_path`` and ``None`` simulates a missing
Espanso install.
"""

from unittest.mock import patch

from espansr.core.config import Config

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
            patch("espansr.integrations.espanso.get_template_manager") as mock_mgr,
            patch("espansr.integrations.espanso.is_wsl2", return_value=False),
        ):
            mock_mgr.return_value.iter_with_triggers.return_value = []
            result = sync_to_espanso()

        assert result is True


# ── Permanent Espanso status indicator ───────────────────────────────────────


class TestEspansoStatusIndicator:
    """Tests for the permanent Espanso status label in the status bar."""

    def test_espanso_status_label_exists(self, make_window):
        """MainWindow has an _espanso_status QLabel."""
        from PyQt6.QtWidgets import QLabel

        window = make_window(Config())
        assert hasattr(window, "_espanso_status")
        assert isinstance(window._espanso_status, QLabel)

    def test_espanso_status_shows_path(self, make_window, tmp_path):
        """Permanent status shows the Espanso path when detected."""
        window = make_window(Config(), espanso_dir=tmp_path)
        assert window._espanso_status.text() == f"Espanso: {tmp_path}"

    def test_espanso_status_shows_not_found(self, make_window):
        """Permanent status shows 'not found' when Espanso is not detected."""
        window = make_window(Config(), espanso_dir=None)
        assert window._espanso_status.text() == "Espanso: not found"

    def test_espanso_label_prefix(self, make_window):
        """Permanent status text begins with 'Espanso:'."""
        window = make_window(Config())
        assert window._espanso_status.text().startswith("Espanso:")


# ── Publish feedback with template count ─────────────────────────────────────


class TestSyncFeedback:
    """Tests for richer publish feedback in the status bar."""

    def test_sync_success_shows_count(self, make_window):
        """A successful publish shows the template count in the status bar."""
        import espansr.integrations.espanso as espanso_mod

        def _mock_sync(**_kwargs):
            espanso_mod._last_sync_count = 3
            return True

        window = make_window(Config())

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
        assert "published" in msg.lower()

    def test_sync_blocked_shows_error_count(self, make_window):
        """A blocked publish shows the error count in the status bar."""
        from espansr.integrations.validate import ValidationWarning

        window = make_window(Config())

        mock_warnings = [
            ValidationWarning(severity="error", message="bad trigger", template_name="t1"),
            ValidationWarning(severity="error", message="short trigger", template_name="t2"),
        ]

        with patch(
            "espansr.integrations.validate.validate_all",
            return_value=mock_warnings,
        ):
            window._sync_btn.click()

        msg = window.statusBar().currentMessage()
        assert "blocked" in msg.lower() or "error" in msg.lower()
        assert "2" in msg

    def test_espanso_status_updates_after_sync(self, make_window):
        """The permanent indicator refreshes after publish."""
        window = make_window(Config())

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

    def test_transient_message_coexists_with_permanent(self, make_window, tmp_path):
        """Transient status messages don't remove the permanent indicator."""
        window = make_window(Config())

        # Show a transient message
        window.statusBar().showMessage("Transient", 5000)

        # Both the transient message and the permanent widget keep their text
        assert window.statusBar().currentMessage() == "Transient"
        assert window._espanso_status.text() == f"Espanso: {tmp_path}"
