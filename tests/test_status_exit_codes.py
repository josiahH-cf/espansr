"""Exit codes and help text of `espansr status`."""

from pathlib import Path
from unittest.mock import patch

import espansr.__main__ as cli


def test_status_returns_1_when_config_dir_missing(capsys):
    with (
        patch.object(cli, "get_espanso_config_dir", return_value=None),
        patch.object(cli, "get_platform", return_value="linux"),
        patch("shutil.which", return_value="/usr/bin/espanso"),
    ):
        assert cli.cmd_status(None) == 1
    out = capsys.readouterr().out
    assert "[FAIL] Espanso config: not found" in out
    assert "[ok]   Espanso binary: /usr/bin/espanso" in out


def test_status_missing_binary_alone_is_a_warning(tmp_path, capsys):
    with (
        patch.object(cli, "get_espanso_config_dir", return_value=Path(tmp_path)),
        patch.object(cli, "get_platform", return_value="linux"),
        patch("shutil.which", return_value=None),
    ):
        assert cli.cmd_status(None) == 0
    out = capsys.readouterr().out
    assert "[warn] Espanso binary: not found" in out
    assert "[FAIL]" not in out


def test_status_missing_config_and_binary_returns_1(capsys):
    with (
        patch.object(cli, "get_espanso_config_dir", return_value=None),
        patch.object(cli, "get_platform", return_value="linux"),
        patch("shutil.which", return_value=None),
    ):
        assert cli.cmd_status(None) == 1
    out = capsys.readouterr().out
    assert "[FAIL] Espanso config: not found" in out
    assert "[warn] Espanso binary: not found" in out


def test_status_wsl2_binary_on_windows_host_is_a_warning(tmp_path):
    with (
        patch.object(cli, "get_espanso_config_dir", return_value=Path(tmp_path)),
        patch.object(cli, "get_platform", return_value="wsl2"),
        patch("shutil.which", return_value=None),
    ):
        assert cli.cmd_status(None) == 0


def test_status_all_present_returns_0(tmp_path):
    with (
        patch.object(cli, "get_espanso_config_dir", return_value=Path(tmp_path)),
        patch.object(cli, "get_platform", return_value="linux"),
        patch("shutil.which", return_value="/usr/bin/espanso"),
    ):
        assert cli.cmd_status(None) == 0


def test_status_json_always_returns_0():
    with patch("espansr.integrations.orchestratr.get_status_json", return_value="{}"):
        assert cli.cmd_status(type("A", (), {"json": True})()) == 0


def test_status_help_text():
    parser = cli._build_parser()
    help_text = parser.format_help()
    assert "Show Espanso config path and binary location" in help_text
    assert "Show Espanso process status" not in help_text
