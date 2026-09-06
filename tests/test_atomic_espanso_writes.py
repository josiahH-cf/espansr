"""Espanso-facing files (and espansr's own JSON state) are replaced atomically.

Covers ``espansr.yml``, the launcher / commands popup / sync trigger files,
Espanso's ``default.yml`` block, ``config.json`` and ``install.json``: content
is complete, no temporary file is left behind, and the write goes through
``espansr.core.atomic``.
"""

import json
from pathlib import Path
from unittest.mock import patch

import yaml

from espansr.core import atomic
from espansr.core.templates import TemplateManager
from espansr.integrations import espanso


def _no_temp_files(directory: Path) -> bool:
    return not any(p.name.endswith(".tmp") for p in directory.iterdir())


def _templates_dir(tmp_path: Path) -> Path:
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "greet.json").write_text(
        json.dumps({"name": "Greet", "content": "Hello!", "trigger": ":greet"})
    )
    return templates_dir


def test_sync_writes_espansr_yml_atomically(tmp_path):
    match_dir = tmp_path / "espanso" / "match"
    match_dir.mkdir(parents=True)
    (match_dir / "espansr.yml").write_text("matches: []\n", encoding="utf-8")

    with (
        patch("espansr.integrations.espanso.get_match_dir", return_value=match_dir),
        patch("espansr.integrations.espanso.clean_stale_espanso_files"),
        patch("espansr.integrations.espanso.get_template_manager") as mock_mgr,
        patch("espansr.integrations.espanso.is_windows", return_value=False),
        patch("espansr.integrations.espanso.is_wsl2", return_value=False),
        patch(
            "espansr.integrations.espanso.atomic_write_bytes",
            wraps=atomic.atomic_write_bytes,
        ) as atomic_write,
    ):
        mock_mgr.return_value = TemplateManager(templates_dir=_templates_dir(tmp_path))
        assert espanso.sync_to_espanso() is True

    output = match_dir / "espansr.yml"
    atomic_write.assert_called_once()
    assert atomic_write.call_args.args[0] == output
    data = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert data["matches"][0]["trigger"] == ":greet"
    assert _no_temp_files(match_dir)


def test_trigger_files_are_written_atomically(tmp_path):
    match_dir = tmp_path / "match"
    match_dir.mkdir()

    with (
        patch("espansr.integrations.espanso.get_match_dir", return_value=match_dir),
        patch("espansr.integrations.espanso.is_wsl2", return_value=False),
        patch("espansr.integrations.espanso.is_windows", return_value=False),
        patch("shutil.which", return_value="/usr/bin/espansr"),
        patch(
            "espansr.integrations.espanso.atomic_write_bytes",
            wraps=atomic.atomic_write_bytes,
        ) as atomic_write,
    ):
        assert espanso.generate_launcher_file() is True
        assert espanso.generate_commands_popup_file() is True
        assert espanso.generate_sync_file() is True

    written = [call.args[0] for call in atomic_write.call_args_list]
    assert written == [
        match_dir / espanso.LAUNCHER_FILE_NAME,
        match_dir / espanso.COMMANDS_POPUP_FILE_NAME,
        match_dir / espanso.SYNC_FILE_NAME,
    ]
    for path in written:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data["matches"][0]["vars"][0]["type"] == "shell"
    assert _no_temp_files(match_dir)


def test_espanso_manager_sync_writes_atomically(tmp_path):
    match_dir = tmp_path / "espanso" / "match"
    match_dir.mkdir(parents=True)

    with (
        patch("espansr.integrations.espanso.get_espanso_config_dir", return_value=tmp_path),
        patch("espansr.integrations.espanso.get_match_dir", return_value=match_dir),
        patch("espansr.integrations.espanso.clean_stale_espanso_files"),
        patch("espansr.integrations.espanso.get_template_manager") as mock_mgr,
        patch(
            "espansr.integrations.espanso.atomic_write_bytes",
            wraps=atomic.atomic_write_bytes,
        ) as atomic_write,
    ):
        mock_mgr.return_value = TemplateManager(templates_dir=_templates_dir(tmp_path))
        assert espanso.EspansoManager().sync() == 1

    atomic_write.assert_called_once()
    assert (match_dir / "espansr.yml").exists()
    assert _no_temp_files(match_dir)


def test_default_yml_block_is_written_atomically(tmp_path):
    cfg = tmp_path / "espanso"
    (cfg / "config").mkdir(parents=True)
    default_yml = cfg / "config" / "default.yml"
    default_yml.write_text("toggle_key: ALT\n", encoding="utf-8")

    with (
        patch.object(espanso, "restart_espanso", return_value=True),
        patch(
            "espansr.integrations.espanso.atomic_write_bytes",
            wraps=atomic.atomic_write_bytes,
        ) as atomic_write,
    ):
        assert espanso.apply_remote_desktop_config(config_dir=cfg) is True
        assert espanso.apply_remote_desktop_config(config_dir=cfg, revert=True) is True

    # apply + revert each replace default.yml; the one-time backup is a copy.
    targets = [call.args[0] for call in atomic_write.call_args_list]
    assert targets.count(default_yml) == 2
    assert default_yml.read_text(encoding="utf-8") == "toggle_key: ALT\n"
    assert _no_temp_files(cfg / "config")


def test_config_json_is_written_atomically(tmp_path):
    from espansr.core.config import ConfigManager

    path = tmp_path / "config.json"
    path.write_text("{}", encoding="utf-8")
    manager = ConfigManager(config_path=path)
    manager.config.espanso.launcher_trigger = ":go"

    with patch("espansr.core.config.atomic_write_json", wraps=atomic.atomic_write_json) as writer:
        assert manager.save() is True

    writer.assert_called_once()
    assert writer.call_args.args[0] == path
    assert json.loads(path.read_text(encoding="utf-8"))["espanso"]["launcher_trigger"] == ":go"
    assert _no_temp_files(tmp_path)


def test_install_json_is_written_atomically(tmp_path):
    from espansr.core import install_meta

    with (
        patch.object(install_meta, "get_config_dir", return_value=tmp_path),
        patch.object(install_meta, "get_platform", return_value="linux"),
        patch.object(install_meta, "atomic_write_json", wraps=atomic.atomic_write_json) as writer,
    ):
        install_meta.record_install_meta(tmp_path / "repo", installer="install.sh")
        loaded = install_meta.load_install_meta()

    writer.assert_called_once()
    assert writer.call_args.args[0] == tmp_path / "install.json"
    assert loaded is not None
    assert loaded.repo_dir == str(tmp_path / "repo")
    assert _no_temp_files(tmp_path)
