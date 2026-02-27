"""Tests for Espanso launcher trigger generation.

Covers: generate_launcher_file(), YAML structure, platform-specific commands,
config trigger override, binary path resolution.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import yaml

from automatr_espanso.integrations.espanso import _MANAGED_FILES


# ─── generate_launcher_file() tests ─────────────────────────────────────────


def test_generate_launcher_creates_valid_yaml(tmp_path):
    """generate_launcher_file() writes valid Espanso v2 shell trigger YAML."""
    match_dir = tmp_path / "match"
    match_dir.mkdir()

    with (
        patch(
            "automatr_espanso.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch(
            "automatr_espanso.integrations.espanso.is_wsl2",
            return_value=False,
        ),
        patch("shutil.which", return_value="/usr/bin/automatr-espanso"),
    ):
        from automatr_espanso.integrations.espanso import generate_launcher_file

        result = generate_launcher_file()

    assert result is True

    launcher = match_dir / "automatr-launcher.yml"
    assert launcher.exists()

    data = yaml.safe_load(launcher.read_text())
    assert "matches" in data
    assert len(data["matches"]) == 1

    match = data["matches"][0]
    assert match["trigger"] == ":aopen"
    assert match["replace"] == "{{output}}"
    assert len(match["vars"]) == 1
    assert match["vars"][0]["name"] == "output"
    assert match["vars"][0]["type"] == "shell"
    assert "automatr-espanso gui" in match["vars"][0]["params"]["cmd"]
    assert match["vars"][0]["params"]["cmd"].endswith("&")


def test_generate_launcher_uses_config_trigger(tmp_path):
    """generate_launcher_file() uses launcher_trigger from config."""
    match_dir = tmp_path / "match"
    match_dir.mkdir()

    with (
        patch(
            "automatr_espanso.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch(
            "automatr_espanso.integrations.espanso.is_wsl2",
            return_value=False,
        ),
        patch("shutil.which", return_value="/usr/bin/automatr-espanso"),
        patch(
            "automatr_espanso.integrations.espanso.get_config"
        ) as mock_config,
    ):
        mock_config.return_value.espanso.launcher_trigger = ":launch"
        from automatr_espanso.integrations.espanso import generate_launcher_file

        result = generate_launcher_file()

    assert result is True
    data = yaml.safe_load((match_dir / "automatr-launcher.yml").read_text())
    assert data["matches"][0]["trigger"] == ":launch"


def test_generate_launcher_wsl2_command(tmp_path):
    """generate_launcher_file() uses wsl.exe -d DISTRO on WSL2."""
    match_dir = tmp_path / "match"
    match_dir.mkdir()

    with (
        patch(
            "automatr_espanso.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch(
            "automatr_espanso.integrations.espanso.is_wsl2",
            return_value=True,
        ),
        patch(
            "automatr_espanso.integrations.espanso.get_wsl_distro_name",
            return_value="Ubuntu",
        ),
        patch(
            "shutil.which",
            return_value="/home/user/.venv/bin/automatr-espanso",
        ),
    ):
        from automatr_espanso.integrations.espanso import generate_launcher_file

        result = generate_launcher_file()

    assert result is True
    data = yaml.safe_load((match_dir / "automatr-launcher.yml").read_text())
    cmd = data["matches"][0]["vars"][0]["params"]["cmd"]
    assert "wsl.exe -d Ubuntu --" in cmd
    assert "/home/user/.venv/bin/automatr-espanso gui" in cmd
    assert cmd.endswith("&")


def test_generate_launcher_wsl2_no_distro_name(tmp_path):
    """generate_launcher_file() omits -d flag when distro name is unavailable."""
    match_dir = tmp_path / "match"
    match_dir.mkdir()

    with (
        patch(
            "automatr_espanso.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch(
            "automatr_espanso.integrations.espanso.is_wsl2",
            return_value=True,
        ),
        patch(
            "automatr_espanso.integrations.espanso.get_wsl_distro_name",
            return_value=None,
        ),
        patch("shutil.which", return_value="/usr/bin/automatr-espanso"),
    ):
        from automatr_espanso.integrations.espanso import generate_launcher_file

        result = generate_launcher_file()

    assert result is True
    data = yaml.safe_load((match_dir / "automatr-launcher.yml").read_text())
    cmd = data["matches"][0]["vars"][0]["params"]["cmd"]
    assert "wsl.exe --" in cmd
    assert "-d" not in cmd


def test_generate_launcher_returns_false_no_match_dir():
    """generate_launcher_file() returns False when no Espanso match dir found."""
    with patch(
        "automatr_espanso.integrations.espanso.get_match_dir",
        return_value=None,
    ):
        from automatr_espanso.integrations.espanso import generate_launcher_file

        assert generate_launcher_file() is False


def test_generate_launcher_fallback_sys_executable(tmp_path):
    """generate_launcher_file() falls back to sys.executable when shutil.which returns None."""
    match_dir = tmp_path / "match"
    match_dir.mkdir()

    with (
        patch(
            "automatr_espanso.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch(
            "automatr_espanso.integrations.espanso.is_wsl2",
            return_value=False,
        ),
        patch("shutil.which", return_value=None),
    ):
        from automatr_espanso.integrations.espanso import generate_launcher_file

        result = generate_launcher_file()

    assert result is True
    data = yaml.safe_load((match_dir / "automatr-launcher.yml").read_text())
    cmd = data["matches"][0]["vars"][0]["params"]["cmd"]
    assert sys.executable in cmd
    assert "-m automatr_espanso gui" in cmd


def test_generate_launcher_with_explicit_match_dir(tmp_path):
    """generate_launcher_file() accepts an explicit match_dir parameter."""
    match_dir = tmp_path / "custom_match"
    match_dir.mkdir()

    with (
        patch(
            "automatr_espanso.integrations.espanso.is_wsl2",
            return_value=False,
        ),
        patch("shutil.which", return_value="/usr/bin/automatr-espanso"),
    ):
        from automatr_espanso.integrations.espanso import generate_launcher_file

        result = generate_launcher_file(match_dir=match_dir)

    assert result is True
    assert (match_dir / "automatr-launcher.yml").exists()


# ─── Integration assertions ─────────────────────────────────────────────────


def test_managed_files_includes_launcher():
    """_MANAGED_FILES includes automatr-launcher.yml for stale cleanup."""
    assert "automatr-launcher.yml" in _MANAGED_FILES
