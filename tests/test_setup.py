"""Tests for espansr setup command.

Covers: cmd_setup() — bundled template copy, no-overwrite, Espanso
detection fallback, and post-setup listing.
"""

import json
from pathlib import Path
from unittest.mock import patch


def _make_bundled_dir(tmp_path: Path) -> Path:
    """Create a fake bundled templates directory with espansr_help.json."""
    bundled = tmp_path / "bundled"
    bundled.mkdir()
    (bundled / "espansr_help.json").write_text(
        json.dumps(
            {
                "name": "Espansr Quick Help",
                "description": "Quick reference for espansr CLI commands.",
                "trigger": ":espansr",
                "content": "espansr commands: list, sync, status",
            }
        )
    )
    return bundled


# ─── cmd_setup — template copying ────────────────────────────────────────────


def test_setup_copies_bundled_template(tmp_path):
    """cmd_setup copies the bundled template into an empty templates dir."""
    from espansr.__main__ import cmd_setup

    config_dir = tmp_path / "config" / "espansr"
    templates_dir = config_dir / "templates"
    bundled_dir = _make_bundled_dir(tmp_path)

    with (
        patch("espansr.__main__.get_config_dir", return_value=config_dir),
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
        patch("espansr.__main__.get_espanso_config_dir", return_value=None),
    ):
        result = cmd_setup(None)

    assert result == 0
    assert (templates_dir / "espansr_help.json").exists()
    data = json.loads((templates_dir / "espansr_help.json").read_text())
    assert data["name"] == "Espansr Quick Help"


def test_setup_does_not_overwrite_existing(tmp_path):
    """cmd_setup skips bundled templates whose filename already exists."""
    from espansr.__main__ import cmd_setup

    config_dir = tmp_path / "config" / "espansr"
    templates_dir = config_dir / "templates"
    templates_dir.mkdir(parents=True)
    bundled_dir = _make_bundled_dir(tmp_path)

    # Pre-create the target file with different content
    existing = templates_dir / "espansr_help.json"
    existing.write_text(json.dumps({"name": "User Customized"}))

    with (
        patch("espansr.__main__.get_config_dir", return_value=config_dir),
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
        patch("espansr.__main__.get_espanso_config_dir", return_value=None),
    ):
        result = cmd_setup(None)

    assert result == 0
    # Content must be preserved — NOT overwritten
    data = json.loads(existing.read_text())
    assert data["name"] == "User Customized"


def test_setup_succeeds_without_espanso(tmp_path):
    """cmd_setup succeeds even when Espanso config is not found."""
    from espansr.__main__ import cmd_setup

    config_dir = tmp_path / "config" / "espansr"
    templates_dir = config_dir / "templates"
    bundled_dir = _make_bundled_dir(tmp_path)

    with (
        patch("espansr.__main__.get_config_dir", return_value=config_dir),
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
        patch("espansr.__main__.get_espanso_config_dir", return_value=None),
    ):
        result = cmd_setup(None)

    assert result == 0


def test_setup_then_list_shows_template(tmp_path):
    """After cmd_setup, the template manager finds the copied template."""
    from espansr.__main__ import cmd_setup
    from espansr.core.templates import TemplateManager

    config_dir = tmp_path / "config" / "espansr"
    templates_dir = config_dir / "templates"
    bundled_dir = _make_bundled_dir(tmp_path)

    with (
        patch("espansr.__main__.get_config_dir", return_value=config_dir),
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
        patch("espansr.__main__.get_espanso_config_dir", return_value=None),
    ):
        cmd_setup(None)

    mgr = TemplateManager(templates_dir=templates_dir)
    triggered = list(mgr.iter_with_triggers())
    assert len(triggered) >= 1
    names = [t.name for t in triggered]
    assert "Espansr Quick Help" in names


def test_setup_handles_missing_bundled_dir(tmp_path):
    """cmd_setup succeeds even if the bundled dir does not exist."""
    from espansr.__main__ import cmd_setup

    config_dir = tmp_path / "config" / "espansr"
    templates_dir = config_dir / "templates"
    nonexistent = tmp_path / "does_not_exist"

    with (
        patch("espansr.__main__.get_config_dir", return_value=config_dir),
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=nonexistent),
        patch("espansr.__main__.get_espanso_config_dir", return_value=None),
    ):
        result = cmd_setup(None)

    assert result == 0


def test_setup_with_espanso_config(tmp_path):
    """cmd_setup calls cleanup and launcher when Espanso config is found."""
    from espansr.__main__ import cmd_setup

    config_dir = tmp_path / "config" / "espansr"
    templates_dir = config_dir / "templates"
    bundled_dir = _make_bundled_dir(tmp_path)
    espanso_dir = tmp_path / "espanso"
    espanso_dir.mkdir()

    with (
        patch("espansr.__main__.get_config_dir", return_value=config_dir),
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
        patch(
            "espansr.__main__.get_espanso_config_dir",
            return_value=espanso_dir,
        ),
        patch("espansr.__main__.clean_stale_espanso_files") as mock_clean,
        patch("espansr.__main__.generate_launcher_file", return_value=True) as mock_launcher,
    ):
        result = cmd_setup(None)

    assert result == 0
    mock_clean.assert_called_once()
    mock_launcher.assert_called_once()


def test_setup_prints_summary(tmp_path, capsys):
    """cmd_setup prints a summary of actions taken."""
    from espansr.__main__ import cmd_setup

    config_dir = tmp_path / "config" / "espansr"
    templates_dir = config_dir / "templates"
    bundled_dir = _make_bundled_dir(tmp_path)

    with (
        patch("espansr.__main__.get_config_dir", return_value=config_dir),
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
        patch("espansr.__main__.get_espanso_config_dir", return_value=None),
    ):
        cmd_setup(None)

    output = capsys.readouterr().out
    assert "Templates:" in output
    assert "Espanso config:" in output
    assert "Launcher:" in output


# ─── cmd_status — platform-specific guidance ─────────────────────────────────


def test_status_wsl2_guidance(capsys):
    """cmd_status shows WSL2-specific guidance when Espanso config is missing."""
    from espansr.__main__ import cmd_status

    with (
        patch("espansr.__main__.get_espanso_config_dir", return_value=None),
        patch("espansr.__main__.get_platform", return_value="wsl2"),
        patch("shutil.which", return_value=None),
    ):
        cmd_status(None)

    output = capsys.readouterr().out
    assert "on Windows" in output
    assert "PowerShell" in output
    assert "https://espanso.org" in output


def test_status_linux_guidance(capsys):
    """cmd_status shows generic guidance on Linux when Espanso config is missing."""
    from espansr.__main__ import cmd_status

    with (
        patch("espansr.__main__.get_espanso_config_dir", return_value=None),
        patch("espansr.__main__.get_platform", return_value="linux"),
        patch("shutil.which", return_value=None),
    ):
        cmd_status(None)

    output = capsys.readouterr().out
    assert "https://espanso.org" in output
    assert "on Windows" not in output


def test_status_macos_guidance(capsys):
    """cmd_status shows generic guidance on macOS when Espanso config is missing."""
    from espansr.__main__ import cmd_status

    with (
        patch("espansr.__main__.get_espanso_config_dir", return_value=None),
        patch("espansr.__main__.get_platform", return_value="macos"),
        patch("shutil.which", return_value=None),
    ):
        cmd_status(None)

    output = capsys.readouterr().out
    assert "https://espanso.org" in output
    assert "on Windows" not in output
