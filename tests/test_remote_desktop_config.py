"""Tests for the Espanso remote-desktop (RustDesk/RDP) config helper.

Covers apply/merge/idempotency/revert semantics of
``apply_remote_desktop_config`` in ``espansr.integrations.espanso``.
"""

from pathlib import Path
from unittest.mock import patch

import yaml

from espansr.integrations import espanso


def _cfg_dir(tmp_path: Path) -> Path:
    """Create and return a fake Espanso config dir (with config/ subdir)."""
    d = tmp_path / "espanso"
    (d / "config").mkdir(parents=True)
    return d


def _default_yml(cfg_dir: Path) -> Path:
    return cfg_dir / "config" / "default.yml"


def test_apply_writes_remote_desktop_keys(tmp_path):
    cfg = _cfg_dir(tmp_path)
    with patch.object(espanso, "restart_espanso", return_value=True):
        assert espanso.apply_remote_desktop_config(config_dir=cfg) is True

    text = _default_yml(cfg).read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    assert data["backend"] == "Clipboard"
    assert data["show_icon"] is False
    assert data["show_notifications"] is False
    assert data["key_delay"] == 30
    assert data["backspace_delay"] == 30
    assert espanso.REMOTE_DESKTOP_MARKER in text


def test_apply_preserves_user_keys(tmp_path):
    cfg = _cfg_dir(tmp_path)
    _default_yml(cfg).write_text("toggle_key: ALT\nsearch_shortcut: ALT+SPACE\n")
    with patch.object(espanso, "restart_espanso", return_value=True):
        espanso.apply_remote_desktop_config(config_dir=cfg)

    data = yaml.safe_load(_default_yml(cfg).read_text(encoding="utf-8"))
    assert data["toggle_key"] == "ALT"
    assert data["search_shortcut"] == "ALT+SPACE"
    assert data["backend"] == "Clipboard"


def test_apply_is_idempotent(tmp_path):
    cfg = _cfg_dir(tmp_path)
    with patch.object(espanso, "restart_espanso", return_value=True):
        espanso.apply_remote_desktop_config(config_dir=cfg)
        first = _default_yml(cfg).read_text(encoding="utf-8")
        espanso.apply_remote_desktop_config(config_dir=cfg)
        second = _default_yml(cfg).read_text(encoding="utf-8")
    assert first == second


def test_revert_removes_only_managed_keys(tmp_path):
    cfg = _cfg_dir(tmp_path)
    _default_yml(cfg).write_text("toggle_key: ALT\n")
    with patch.object(espanso, "restart_espanso", return_value=True):
        espanso.apply_remote_desktop_config(config_dir=cfg)
        espanso.apply_remote_desktop_config(config_dir=cfg, revert=True)

    data = yaml.safe_load(_default_yml(cfg).read_text(encoding="utf-8"))
    assert data == {"toggle_key": "ALT"}


def test_revert_deletes_file_when_only_managed_keys(tmp_path):
    cfg = _cfg_dir(tmp_path)
    with patch.object(espanso, "restart_espanso", return_value=True):
        espanso.apply_remote_desktop_config(config_dir=cfg)
        espanso.apply_remote_desktop_config(config_dir=cfg, revert=True)
    assert not _default_yml(cfg).exists()


def test_revert_keeps_user_overridden_value(tmp_path):
    cfg = _cfg_dir(tmp_path)
    path = _default_yml(cfg)
    with patch.object(espanso, "restart_espanso", return_value=True):
        espanso.apply_remote_desktop_config(config_dir=cfg)
        # User re-customizes the backend after espansr applied Clipboard.
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["backend"] = "Inject"
        path.write_text(yaml.safe_dump(data))
        espanso.apply_remote_desktop_config(config_dir=cfg, revert=True)

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["backend"] == "Inject"  # never clobbered by revert


def test_apply_backs_up_invalid_yaml(tmp_path):
    cfg = _cfg_dir(tmp_path)
    # A bare scalar is valid YAML but not a mapping Espanso could use.
    _default_yml(cfg).write_text("just a plain scalar, not a mapping")
    with patch.object(espanso, "restart_espanso", return_value=True):
        assert espanso.apply_remote_desktop_config(config_dir=cfg) is True

    backup = _default_yml(cfg).parent / "default.yml.espansr-bak"
    assert backup.exists()
    data = yaml.safe_load(_default_yml(cfg).read_text(encoding="utf-8"))
    assert data["backend"] == "Clipboard"


def test_apply_returns_false_without_espanso(tmp_path):
    with patch.object(espanso, "get_espanso_config_dir", return_value=None):
        assert espanso.apply_remote_desktop_config() is False
