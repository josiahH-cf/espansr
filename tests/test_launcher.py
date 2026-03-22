"""Tests for Espanso launcher trigger generation.

Covers: generate_launcher_file(), YAML structure, platform-specific commands,
config trigger override, binary path resolution.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import yaml

from espansr.integrations.espanso import _MANAGED_FILES

# ─── generate_launcher_file() tests ─────────────────────────────────────────


def test_generate_launcher_creates_valid_yaml(tmp_path):
    """generate_launcher_file() writes valid Espanso v2 shell trigger YAML."""
    match_dir = tmp_path / "match"
    match_dir.mkdir()

    with (
        patch(
            "espansr.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch(
            "espansr.integrations.espanso.is_wsl2",
            return_value=False,
        ),
        patch(
            "espansr.integrations.espanso.is_windows",
            return_value=False,
        ),
        patch("shutil.which", return_value="/usr/bin/espansr"),
    ):
        from espansr.integrations.espanso import generate_launcher_file

        result = generate_launcher_file()

    assert result is True

    launcher = match_dir / "espansr-launcher.yml"
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
    assert "espansr gui" in match["vars"][0]["params"]["cmd"]
    assert " >/dev/null 2>&1 &" in match["vars"][0]["params"]["cmd"]


def test_generate_launcher_uses_config_trigger(tmp_path):
    """generate_launcher_file() uses launcher_trigger from config."""
    match_dir = tmp_path / "match"
    match_dir.mkdir()

    with (
        patch(
            "espansr.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch(
            "espansr.integrations.espanso.is_wsl2",
            return_value=False,
        ),
        patch(
            "espansr.integrations.espanso.is_windows",
            return_value=False,
        ),
        patch("shutil.which", return_value="/usr/bin/espansr"),
        patch("espansr.integrations.espanso.get_config") as mock_config,
    ):
        mock_config.return_value.espanso.launcher_trigger = ":launch"
        from espansr.integrations.espanso import generate_launcher_file

        result = generate_launcher_file()

    assert result is True
    data = yaml.safe_load((match_dir / "espansr-launcher.yml").read_text())
    assert data["matches"][0]["trigger"] == ":launch"


def test_generate_launcher_wsl2_command(tmp_path):
    """generate_launcher_file() uses PowerShell Start-Process for WSL launches."""
    match_dir = tmp_path / "match"
    match_dir.mkdir()

    with (
        patch(
            "espansr.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch(
            "espansr.integrations.espanso.is_wsl2",
            return_value=True,
        ),
        patch(
            "espansr.integrations.espanso._is_windows_side_wsl_path",
            return_value=True,
        ),
        patch(
            "espansr.integrations.espanso.get_wsl_distro_name",
            return_value="Ubuntu",
        ),
        patch(
            "shutil.which",
            return_value="/home/user/.venv/bin/espansr",
        ),
    ):
        from espansr.integrations.espanso import generate_launcher_file

        result = generate_launcher_file()

    assert result is True
    data = yaml.safe_load((match_dir / "espansr-launcher.yml").read_text())
    params = data["matches"][0]["vars"][0]["params"]
    cmd = params["cmd"]
    assert params["shell"] == "powershell"
    assert "Start-Process" in cmd
    assert "-FilePath 'wsl.exe'" in cmd
    assert "'-d'" in cmd
    assert "'Ubuntu'" in cmd
    assert "'/home/user/.venv/bin/espansr'" in cmd
    assert "'gui'" in cmd


def test_generate_launcher_wsl2_linux_side_config_uses_posix_shell(tmp_path):
    """WSL with Linux-side Espanso config keeps POSIX shell launcher semantics."""
    match_dir = tmp_path / "match"
    match_dir.mkdir()

    with (
        patch(
            "espansr.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch(
            "espansr.integrations.espanso.is_wsl2",
            return_value=True,
        ),
        patch(
            "espansr.integrations.espanso.is_windows",
            return_value=False,
        ),
        patch(
            "espansr.integrations.espanso._is_windows_side_wsl_path",
            return_value=False,
        ),
        patch("shutil.which", return_value="/home/user/.venv/bin/espansr"),
    ):
        from espansr.integrations.espanso import generate_launcher_file

        result = generate_launcher_file()

    assert result is True
    data = yaml.safe_load((match_dir / "espansr-launcher.yml").read_text())
    params = data["matches"][0]["vars"][0]["params"]
    assert "shell" not in params
    assert params["cmd"].startswith("nohup /home/user/.venv/bin/espansr gui")
    assert params["cmd"].endswith(" >/dev/null 2>&1 &")


def test_generate_launcher_wsl2_no_distro_name(tmp_path):
    """generate_launcher_file() omits -d flag when distro name is unavailable."""
    match_dir = tmp_path / "match"
    match_dir.mkdir()

    with (
        patch(
            "espansr.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch(
            "espansr.integrations.espanso.is_wsl2",
            return_value=True,
        ),
        patch(
            "espansr.integrations.espanso._is_windows_side_wsl_path",
            return_value=True,
        ),
        patch(
            "espansr.integrations.espanso.get_wsl_distro_name",
            return_value=None,
        ),
        patch("shutil.which", return_value="/usr/bin/espansr"),
    ):
        from espansr.integrations.espanso import generate_launcher_file

        result = generate_launcher_file()

    assert result is True
    data = yaml.safe_load((match_dir / "espansr-launcher.yml").read_text())
    params = data["matches"][0]["vars"][0]["params"]
    cmd = params["cmd"]
    assert params["shell"] == "powershell"
    assert "-FilePath 'wsl.exe'" in cmd
    assert "'--'" in cmd
    assert "'-d'" not in cmd


def test_windows_side_wsl_path_accepts_non_c_drive_mounts():
    """Windows-hosted WSL paths are recognized on any mounted drive letter."""
    from espansr.integrations.espanso import _is_windows_side_wsl_path

    assert _is_windows_side_wsl_path(Path("/mnt/d/Users/test/AppData/Roaming/espanso"))
    assert _is_windows_side_wsl_path(Path("/mnt/z/tools/espanso"))
    assert not _is_windows_side_wsl_path(Path("/home/test/.config/espanso"))


def test_generate_launcher_returns_false_no_match_dir():
    """generate_launcher_file() returns False when no Espanso match dir found."""
    with patch(
        "espansr.integrations.espanso.get_match_dir",
        return_value=None,
    ):
        from espansr.integrations.espanso import generate_launcher_file

        assert generate_launcher_file() is False


def test_generate_launcher_fallback_sys_executable(tmp_path):
    """generate_launcher_file() falls back to sys.executable when shutil.which returns None."""
    match_dir = tmp_path / "match"
    match_dir.mkdir()

    with (
        patch(
            "espansr.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch(
            "espansr.integrations.espanso.is_wsl2",
            return_value=False,
        ),
        patch(
            "espansr.integrations.espanso.is_windows",
            return_value=False,
        ),
        patch("shutil.which", return_value=None),
    ):
        from espansr.integrations.espanso import generate_launcher_file

        result = generate_launcher_file()

    assert result is True
    data = yaml.safe_load((match_dir / "espansr-launcher.yml").read_text())
    cmd = data["matches"][0]["vars"][0]["params"]["cmd"]
    assert sys.executable in cmd
    assert "-m espansr gui" in cmd


def test_generate_launcher_windows_command_uses_start_process(tmp_path):
    """generate_launcher_file() uses PowerShell Start-Process on Windows."""
    match_dir = tmp_path / "match"
    match_dir.mkdir()

    with (
        patch(
            "espansr.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch(
            "espansr.integrations.espanso.is_wsl2",
            return_value=False,
        ),
        patch(
            "espansr.integrations.espanso.is_windows",
            return_value=True,
        ),
        patch("shutil.which", return_value=r"C:\Program Files\espansr\espansr.exe"),
    ):
        from espansr.integrations.espanso import generate_launcher_file

        result = generate_launcher_file()

    assert result is True
    data = yaml.safe_load((match_dir / "espansr-launcher.yml").read_text())
    params = data["matches"][0]["vars"][0]["params"]
    cmd = params["cmd"]
    assert params["shell"] == "powershell"
    assert "Start-Process" in cmd
    assert "-FilePath 'C:\\Program Files\\espansr\\espansr.exe'" in cmd
    assert "-ArgumentList 'gui'" in cmd


def test_generate_launcher_windows_fallback_python_module(tmp_path):
    """generate_launcher_file() can launch via python -m espansr on Windows."""
    match_dir = tmp_path / "match"
    match_dir.mkdir()
    fake_python = Path(r"C:\Python311\python.exe")

    with (
        patch(
            "espansr.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch(
            "espansr.integrations.espanso.is_wsl2",
            return_value=False,
        ),
        patch(
            "espansr.integrations.espanso.is_windows",
            return_value=True,
        ),
        patch("shutil.which", return_value=None),
        patch("sys.executable", str(fake_python)),
    ):
        from espansr.integrations.espanso import generate_launcher_file

        result = generate_launcher_file()

    assert result is True
    data = yaml.safe_load((match_dir / "espansr-launcher.yml").read_text())
    params = data["matches"][0]["vars"][0]["params"]
    cmd = params["cmd"]
    assert params["shell"] == "powershell"
    assert "-FilePath 'C:\\Python311\\python.exe'" in cmd
    assert "'-m'" in cmd
    assert "'espansr'" in cmd
    assert "'gui'" in cmd


def test_generate_launcher_with_explicit_match_dir(tmp_path):
    """generate_launcher_file() accepts an explicit match_dir parameter."""
    match_dir = tmp_path / "custom_match"
    match_dir.mkdir()

    with (
        patch(
            "espansr.integrations.espanso.is_wsl2",
            return_value=False,
        ),
        patch(
            "espansr.integrations.espanso.is_windows",
            return_value=False,
        ),
        patch("shutil.which", return_value="/usr/bin/espansr"),
    ):
        from espansr.integrations.espanso import generate_launcher_file

        result = generate_launcher_file(match_dir=match_dir)

    assert result is True
    assert (match_dir / "espansr-launcher.yml").exists()


# ─── Integration assertions ─────────────────────────────────────────────────


def test_managed_files_includes_launcher():
    """_MANAGED_FILES includes espansr-launcher.yml for stale cleanup."""
    assert "espansr-launcher.yml" in _MANAGED_FILES


# ─── GUI first-run tip tests ────────────────────────────────────────────────


def test_first_run_shows_launcher_tip(tmp_path, qtbot):
    """MainWindow shows a status bar tip when launcher file is missing."""
    match_dir = tmp_path / "match"
    match_dir.mkdir()

    with (
        patch(
            "espansr.ui.main_window.get_config",
        ) as mock_config,
        patch(
            "espansr.ui.main_window.get_config_manager",
        ),
        patch(
            "espansr.ui.template_browser.get_config",
        ),
        patch(
            "espansr.ui.template_browser.get_template_manager",
        ),
        patch(
            "espansr.ui.template_editor.get_config",
        ),
        patch(
            "espansr.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch(
            "espansr.integrations.espanso.get_espanso_config_dir",
            return_value=tmp_path,
        ),
        patch(
            "espansr.integrations.espanso._get_candidate_paths",
            return_value=[],
        ),
    ):
        from espansr.core.config import Config

        mock_config.return_value = Config()

        from espansr.ui.main_window import MainWindow

        window = MainWindow()
        qtbot.addWidget(window)

    msg = window.statusBar().currentMessage()
    assert ":aopen" in msg
    assert "Tip" in msg


def test_no_tip_when_launcher_exists(tmp_path, qtbot):
    """MainWindow does not show tip when launcher file already exists."""
    match_dir = tmp_path / "match"
    match_dir.mkdir()
    (match_dir / "espansr-launcher.yml").write_text("matches: []")

    with (
        patch(
            "espansr.ui.main_window.get_config",
        ) as mock_config,
        patch(
            "espansr.ui.main_window.get_config_manager",
        ),
        patch(
            "espansr.ui.template_browser.get_config",
        ),
        patch(
            "espansr.ui.template_browser.get_template_manager",
        ),
        patch(
            "espansr.ui.template_editor.get_config",
        ),
        patch(
            "espansr.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch(
            "espansr.integrations.espanso.get_espanso_config_dir",
            return_value=tmp_path,
        ),
        patch(
            "espansr.integrations.espanso._get_candidate_paths",
            return_value=[],
        ),
    ):
        from espansr.core.config import Config

        mock_config.return_value = Config()

        from espansr.ui.main_window import MainWindow

        window = MainWindow()
        qtbot.addWidget(window)

    msg = window.statusBar().currentMessage()
    assert ":aopen" not in msg
