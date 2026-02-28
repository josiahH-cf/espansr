"""Tests for espansr.

Covers: ConfigManager, EspansoConfig, TemplateManager, iter_with_triggers,
sync_to_espanso YAML output, WSL2 path detection, CLI commands.

Minimum 8 test functions required (currently 14).
"""

import json
import subprocess
import sys
from unittest.mock import mock_open, patch

import yaml

# ─── ConfigManager / EspansoConfig tests ─────────────────────────────────────


def test_config_manager_returns_defaults_when_no_file(tmp_path):
    """ConfigManager returns EspansoConfig defaults when no file exists."""
    from espansr.core.config import ConfigManager, EspansoConfig, UIConfig

    cm = ConfigManager(config_path=tmp_path / "config.json")
    config = cm.config

    assert isinstance(config.espanso, EspansoConfig)
    assert isinstance(config.ui, UIConfig)


def test_config_manager_save_and_reload(tmp_path):
    """ConfigManager round-trips espanso config correctly."""
    from espansr.core.config import ConfigManager

    path = tmp_path / "config.json"
    cm = ConfigManager(config_path=path)
    cm.config.espanso.config_path = "/custom/espanso"
    cm.config.espanso.auto_sync = True
    cm.save()

    cm2 = ConfigManager(config_path=path)
    assert cm2.config.espanso.config_path == "/custom/espanso"
    assert cm2.config.espanso.auto_sync is True


def test_espanso_config_defaults():
    """EspansoConfig has correct defaults."""
    from espansr.core.config import EspansoConfig

    cfg = EspansoConfig()
    assert cfg.config_path == ""
    assert cfg.auto_sync is False
    assert cfg.last_sync == ""
    assert cfg.launcher_trigger == ":aopen"


def test_config_update_launcher_trigger(tmp_path):
    """ConfigManager.update() persists launcher_trigger via dot-notation."""
    from espansr.core.config import ConfigManager

    cm = ConfigManager(config_path=tmp_path / "config.json")
    cm.update(**{"espanso.launcher_trigger": ":myopen"})

    cm2 = ConfigManager(config_path=tmp_path / "config.json")
    assert cm2.config.espanso.launcher_trigger == ":myopen"


def test_config_update_nested_key(tmp_path):
    """ConfigManager.update() supports 'espanso.config_path' dot-notation."""
    from espansr.core.config import ConfigManager

    cm = ConfigManager(config_path=tmp_path / "config.json")
    cm.update(**{"espanso.config_path": "/test/path", "espanso.auto_sync": True})

    assert cm.config.espanso.config_path == "/test/path"
    assert cm.config.espanso.auto_sync is True


# ─── TemplateManager / trigger field tests ────────────────────────────────────


def test_template_loads_trigger_field(tmp_path):
    """Templates load the trigger field from JSON correctly."""
    from espansr.core.templates import TemplateManager

    data = {
        "name": "Test Template",
        "content": "Hello {{name}}",
        "trigger": ":test",
        "variables": [{"name": "name", "label": "Name"}],
    }
    path = tmp_path / "test.json"
    path.write_text(json.dumps(data))

    manager = TemplateManager(templates_dir=tmp_path)
    template = manager.load(path)

    assert template is not None
    assert template.trigger == ":test"
    assert template.name == "Test Template"
    assert len(template.variables) == 1


def test_iter_with_triggers_filters_correctly(tmp_path):
    """iter_with_triggers() yields only templates with a non-empty trigger."""
    from espansr.core.templates import TemplateManager

    (tmp_path / "with_trigger.json").write_text(
        json.dumps({"name": "With Trigger", "content": "foo", "trigger": ":foo"})
    )
    (tmp_path / "no_trigger.json").write_text(
        json.dumps({"name": "No Trigger", "content": "bar", "trigger": ""})
    )
    (tmp_path / "missing_trigger.json").write_text(
        json.dumps({"name": "Missing Trigger Field", "content": "baz"})
    )

    manager = TemplateManager(templates_dir=tmp_path)
    triggered = list(manager.iter_with_triggers())

    assert len(triggered) == 1
    assert triggered[0].trigger == ":foo"
    assert triggered[0].name == "With Trigger"


# ─── sync_to_espanso() YAML output tests ─────────────────────────────────────


def test_sync_produces_valid_yaml_v2_match_file(tmp_path):
    """sync_to_espanso() writes a valid Espanso v2 YAML match file."""
    from espansr.core.templates import TemplateManager

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "greet.json").write_text(
        json.dumps({"name": "Greet", "content": "Hello, World!", "trigger": ":greet"})
    )

    match_dir = tmp_path / "espanso" / "match"
    match_dir.mkdir(parents=True)

    with (
        patch(
            "espansr.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch("espansr.integrations.espanso.get_template_manager") as mock_mgr,
    ):
        mock_mgr.return_value = TemplateManager(templates_dir=templates_dir)

        from espansr.integrations.espanso import sync_to_espanso

        result = sync_to_espanso()

    assert result is True
    output = match_dir / "espansr.yml"
    assert output.exists()

    data = yaml.safe_load(output.read_text())
    assert "matches" in data
    assert len(data["matches"]) == 1
    assert data["matches"][0]["trigger"] == ":greet"
    assert data["matches"][0]["replace"] == "Hello, World!"


def test_sync_form_variable_uses_espanso_v2_placeholder(tmp_path):
    """Form variables in sync output use {{var.value}} Espanso v2 syntax."""
    from espansr.core.templates import TemplateManager

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "form.json").write_text(
        json.dumps(
            {
                "name": "Form Template",
                "content": "Hi {{name}}!",
                "trigger": ":hi",
                "variables": [{"name": "name", "label": "Name"}],
            }
        )
    )

    match_dir = tmp_path / "espanso" / "match"
    match_dir.mkdir(parents=True)

    with (
        patch(
            "espansr.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch("espansr.integrations.espanso.get_template_manager") as mock_mgr,
    ):
        mock_mgr.return_value = TemplateManager(templates_dir=templates_dir)
        from espansr.integrations.espanso import sync_to_espanso

        sync_to_espanso()

    data = yaml.safe_load((match_dir / "espansr.yml").read_text())
    replace_text = data["matches"][0]["replace"]
    # Form vars must use .value accessor
    assert "{{name.value}}" in replace_text
    assert "{{name}}" not in replace_text


def test_sync_succeeds_with_no_triggered_templates(tmp_path):
    """sync_to_espanso() returns True and writes nothing when no triggers exist."""
    from espansr.core.templates import TemplateManager

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "plain.json").write_text(
        json.dumps({"name": "Plain", "content": "content", "trigger": ""})
    )

    match_dir = tmp_path / "espanso" / "match"
    match_dir.mkdir(parents=True)

    with (
        patch(
            "espansr.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch("espansr.integrations.espanso.get_template_manager") as mock_mgr,
    ):
        mock_mgr.return_value = TemplateManager(templates_dir=templates_dir)
        from espansr.integrations.espanso import sync_to_espanso

        result = sync_to_espanso()

    assert result is True
    # No file should be written when there are no matches
    assert not (match_dir / "espansr.yml").exists()


def test_sync_returns_false_when_no_match_dir():
    """sync_to_espanso() returns False when Espanso config dir not found."""
    with patch("espansr.integrations.espanso.get_match_dir", return_value=None):
        from espansr.integrations.espanso import sync_to_espanso

        result = sync_to_espanso()

    assert result is False


# ─── WSL2 path detection tests ───────────────────────────────────────────────


def test_platform_detection_wsl2():
    """get_platform() returns 'wsl2' when /proc/version contains 'microsoft'."""
    # Reload module to clear any cached results
    import importlib

    with (
        patch("platform.system", return_value="Linux"),
        patch(
            "builtins.open", mock_open(read_data="Linux version 5.15 (Microsoft WSL2)")
        ),
    ):
        import espansr.core.config as cfg_mod

        importlib.reload(cfg_mod)
        result = cfg_mod.get_platform()

    assert result == "wsl2"


def test_platform_detection_native_linux():
    """get_platform() returns 'linux' on a non-WSL2 Linux system."""
    import importlib

    with (
        patch("platform.system", return_value="Linux"),
        patch(
            "builtins.open", mock_open(read_data="Linux version 5.15 generic ubuntu")
        ),
    ):
        import espansr.core.config as cfg_mod

        importlib.reload(cfg_mod)
        result = cfg_mod.get_platform()

    assert result == "linux"


# ─── CLI command smoke tests ──────────────────────────────────────────────────


def test_cli_list_runs_without_error(tmp_path):
    """'espansr list' exits 0 with an empty templates directory."""
    result = subprocess.run(
        [sys.executable, "-m", "espansr", "list"],
        capture_output=True,
        text=True,
        env={
            **__import__("os").environ,
            "XDG_CONFIG_HOME": str(tmp_path),
        },
    )
    assert result.returncode == 0


def test_cli_status_runs_without_error():
    """'espansr status' exits 0 (Espanso may or may not be installed)."""
    result = subprocess.run(
        [sys.executable, "-m", "espansr", "status"],
        capture_output=True,
        text=True,
    )
    # Status reports availability — should not crash regardless of Espanso presence
    assert result.returncode == 0


# ─── Config dir migration tests ──────────────────────────────────────────────


def test_migrate_config_dir_moves_old_to_new(tmp_path):
    """_migrate_config_dir() moves automatr-espanso dir to espansr."""
    from espansr.core.config import _migrate_config_dir

    old_dir = tmp_path / "automatr-espanso"
    old_dir.mkdir()
    (old_dir / "config.json").write_text('{"test": true}')
    (old_dir / "templates").mkdir()
    (old_dir / "templates" / "t.json").write_text('{"name": "test"}')

    result = _migrate_config_dir(tmp_path)

    assert result is True
    assert not old_dir.exists()
    new_dir = tmp_path / "espansr"
    assert new_dir.is_dir()
    assert (new_dir / "config.json").read_text() == '{"test": true}'
    assert (new_dir / "templates" / "t.json").read_text() == '{"name": "test"}'


def test_migrate_config_dir_skips_when_new_exists(tmp_path):
    """_migrate_config_dir() does nothing when espansr dir already exists."""
    from espansr.core.config import _migrate_config_dir

    old_dir = tmp_path / "automatr-espanso"
    old_dir.mkdir()
    (old_dir / "old.json").write_text("{}")

    new_dir = tmp_path / "espansr"
    new_dir.mkdir()
    (new_dir / "new.json").write_text("{}")

    result = _migrate_config_dir(tmp_path)

    assert result is False
    # Both dirs still exist — no migration
    assert old_dir.exists()
    assert new_dir.exists()
    assert (new_dir / "new.json").exists()


def test_migrate_config_dir_skips_when_no_old(tmp_path):
    """_migrate_config_dir() does nothing when old dir doesn't exist."""
    from espansr.core.config import _migrate_config_dir

    result = _migrate_config_dir(tmp_path)

    assert result is False


def test_get_config_dir_triggers_migration(tmp_path):
    """get_config_dir() automatically migrates old config dir."""
    import os

    from espansr.core.config import get_config_dir

    old_dir = tmp_path / "automatr-espanso"
    old_dir.mkdir()
    (old_dir / "config.json").write_text('{"migrated": true}')

    with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_path)}):
        config_dir = get_config_dir()

    assert config_dir == tmp_path / "espansr"
    assert not old_dir.exists()
    assert (config_dir / "config.json").read_text() == '{"migrated": true}'


# ─── Old Espanso file cleanup tests ──────────────────────────────────────────


def test_sync_cleans_old_automatr_files(tmp_path):
    """sync_to_espanso() removes old automatr-espanso.yml and automatr-launcher.yml."""
    from espansr.core.templates import TemplateManager

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "greet.json").write_text(
        json.dumps({"name": "Greet", "content": "Hello!", "trigger": ":greet"})
    )

    match_dir = tmp_path / "espanso" / "match"
    match_dir.mkdir(parents=True)

    # Create old-named files in the canonical match dir
    (match_dir / "automatr-espanso.yml").write_text("matches: []")
    (match_dir / "automatr-launcher.yml").write_text("matches: []")

    with (
        patch("espansr.integrations.espanso.get_match_dir", return_value=match_dir),
        patch("espansr.integrations.espanso.get_template_manager") as mock_mgr,
        patch(
            "espansr.integrations.espanso.get_espanso_config_dir",
            return_value=tmp_path / "espanso",
        ),
        patch(
            "espansr.integrations.espanso._get_candidate_paths",
            return_value=[tmp_path / "espanso"],
        ),
    ):
        mock_mgr.return_value = TemplateManager(templates_dir=templates_dir)
        from espansr.integrations.espanso import sync_to_espanso

        result = sync_to_espanso()

    assert result is True
    # Old files should be cleaned up
    assert not (match_dir / "automatr-espanso.yml").exists()
    assert not (match_dir / "automatr-launcher.yml").exists()
    # New file should exist
    assert (match_dir / "espansr.yml").exists()
