"""Regression tests for the Linux/macOS/WSL shell installer."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _installer_text() -> str:
    return (ROOT / "install.sh").read_text(encoding="utf-8")


def test_shell_installer_does_not_advertise_unsupported_no_desktop_flag():
    text = _installer_text()

    assert "--no-desktop" not in text


def test_shell_installer_fails_when_setup_fails():
    text = _installer_text()

    assert 'if "$VENV_CMD" setup; then' in text
    assert (
        'die "Post-install setup failed. Resolve the message above and rerun ./install.sh"' in text
    )
    assert "Setup completed with warnings" not in text


def test_shell_installer_recreates_incomplete_existing_venv():
    text = _installer_text()

    assert '[[ -f "$VENV_DIR/pyvenv.cfg" && -x "$VENV_PYTHON" ]]' in text
    assert "Existing venv is incomplete - recreating $VENV_DIR" in text
    assert 'rm -rf "$VENV_DIR"' in text


def test_shell_installer_checks_debian_dependencies_only_when_tools_exist():
    text = _installer_text()

    assert "command -v dpkg" in text
    assert "command -v apt-get" in text
    assert "Skipping automatic PyQt6 system package check" in text
    assert "Checking Debian/Ubuntu system packages for PyQt6" in text


def test_shell_installer_prints_missing_espanso_next_steps():
    text = _installer_text()

    assert "espansr wsl-install-espanso" in text
    assert "Install and start Espanso from https://espanso.org" in text
    assert "espansr setup" in text
    assert "espansr doctor" in text


def test_shell_installer_prints_list_output_when_smoke_test_fails():
    text = _installer_text()

    assert 'LIST_OUTPUT="$("$VENV_CMD" list 2>&1)"' in text
    assert "Smoke test failed: 'espansr list' exited non-zero" in text
