"""Tests for automatr-espanso.

Covers: ConfigManager, EspansoConfig, TemplateManager, iter_with_triggers,
sync_to_espanso YAML output, WSL2 path detection, CLI commands.

Minimum 8 test functions required (currently 12).
"""

import json
import subprocess
import sys
from unittest.mock import mock_open, patch

import yaml

# ─── ConfigManager / EspansoConfig tests ─────────────────────────────────────


def test_config_manager_returns_defaults_when_no_file(tmp_path):
    """ConfigManager returns EspansoConfig defaults when no file exists."""
    from automatr_espanso.core.config import ConfigManager, EspansoConfig, UIConfig

    cm = ConfigManager(config_path=tmp_path / "config.json")
    config = cm.config

    assert isinstance(config.espanso, EspansoConfig)
    assert isinstance(config.ui, UIConfig)
    # Must NOT have LLMConfig
    assert not hasattr(config, "llm")


def test_config_manager_save_and_reload(tmp_path):
    """ConfigManager round-trips espanso config correctly."""
    from automatr_espanso.core.config import ConfigManager

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
    from automatr_espanso.core.config import EspansoConfig

    cfg = EspansoConfig()
    assert cfg.config_path == ""
    assert cfg.auto_sync is False
    assert cfg.last_sync == ""


def test_config_update_nested_key(tmp_path):
    """ConfigManager.update() supports 'espanso.config_path' dot-notation."""
    from automatr_espanso.core.config import ConfigManager

    cm = ConfigManager(config_path=tmp_path / "config.json")
    cm.update(**{"espanso.config_path": "/test/path", "espanso.auto_sync": True})

    assert cm.config.espanso.config_path == "/test/path"
    assert cm.config.espanso.auto_sync is True


# ─── TemplateManager / trigger field tests ────────────────────────────────────


def test_template_loads_trigger_field(tmp_path):
    """Templates load the trigger field from JSON correctly."""
    from automatr_espanso.core.templates import TemplateManager

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
    from automatr_espanso.core.templates import TemplateManager

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
    from automatr_espanso.core.templates import TemplateManager

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "greet.json").write_text(
        json.dumps(
            {"name": "Greet", "content": "Hello, World!", "trigger": ":greet"}
        )
    )

    match_dir = tmp_path / "espanso" / "match"
    match_dir.mkdir(parents=True)

    with (
        patch(
            "automatr_espanso.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch(
            "automatr_espanso.integrations.espanso.get_template_manager"
        ) as mock_mgr,
    ):
        mock_mgr.return_value = TemplateManager(templates_dir=templates_dir)

        from automatr_espanso.integrations.espanso import sync_to_espanso

        result = sync_to_espanso()

    assert result is True
    output = match_dir / "automatr.yml"
    assert output.exists()

    data = yaml.safe_load(output.read_text())
    assert "matches" in data
    assert len(data["matches"]) == 1
    assert data["matches"][0]["trigger"] == ":greet"
    assert data["matches"][0]["replace"] == "Hello, World!"


def test_sync_form_variable_uses_espanso_v2_placeholder(tmp_path):
    """Form variables in sync output use {{var.value}} Espanso v2 syntax."""
    from automatr_espanso.core.templates import TemplateManager

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
            "automatr_espanso.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch(
            "automatr_espanso.integrations.espanso.get_template_manager"
        ) as mock_mgr,
    ):
        mock_mgr.return_value = TemplateManager(templates_dir=templates_dir)
        from automatr_espanso.integrations.espanso import sync_to_espanso

        sync_to_espanso()

    data = yaml.safe_load((match_dir / "automatr.yml").read_text())
    replace_text = data["matches"][0]["replace"]
    # Form vars must use .value accessor
    assert "{{name.value}}" in replace_text
    assert "{{name}}" not in replace_text


def test_sync_succeeds_with_no_triggered_templates(tmp_path):
    """sync_to_espanso() returns True and writes nothing when no triggers exist."""
    from automatr_espanso.core.templates import TemplateManager

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "plain.json").write_text(
        json.dumps({"name": "Plain", "content": "content", "trigger": ""})
    )

    match_dir = tmp_path / "espanso" / "match"
    match_dir.mkdir(parents=True)

    with (
        patch(
            "automatr_espanso.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch(
            "automatr_espanso.integrations.espanso.get_template_manager"
        ) as mock_mgr,
    ):
        mock_mgr.return_value = TemplateManager(templates_dir=templates_dir)
        from automatr_espanso.integrations.espanso import sync_to_espanso

        result = sync_to_espanso()

    assert result is True
    # No file should be written when there are no matches
    assert not (match_dir / "automatr.yml").exists()


def test_sync_returns_false_when_no_match_dir():
    """sync_to_espanso() returns False when Espanso config dir not found."""
    with patch(
        "automatr_espanso.integrations.espanso.get_match_dir", return_value=None
    ):
        from automatr_espanso.integrations.espanso import sync_to_espanso

        result = sync_to_espanso()

    assert result is False


# ─── WSL2 path detection tests ───────────────────────────────────────────────


def test_platform_detection_wsl2():
    """get_platform() returns 'wsl2' when /proc/version contains 'microsoft'."""
    # Reload module to clear any cached results
    import importlib

    with (
        patch("platform.system", return_value="Linux"),
        patch("builtins.open", mock_open(read_data="Linux version 5.15 (Microsoft WSL2)")),
    ):
        import automatr_espanso.core.config as cfg_mod

        importlib.reload(cfg_mod)
        result = cfg_mod.get_platform()

    assert result == "wsl2"


def test_platform_detection_native_linux():
    """get_platform() returns 'linux' on a non-WSL2 Linux system."""
    import importlib

    with (
        patch("platform.system", return_value="Linux"),
        patch("builtins.open", mock_open(read_data="Linux version 5.15 generic ubuntu")),
    ):
        import automatr_espanso.core.config as cfg_mod

        importlib.reload(cfg_mod)
        result = cfg_mod.get_platform()

    assert result == "linux"


# ─── CLI command smoke tests ──────────────────────────────────────────────────


def test_cli_list_runs_without_error(tmp_path):
    """'automatr-espanso list' exits 0 with an empty templates directory."""
    result = subprocess.run(
        [sys.executable, "-m", "automatr_espanso", "list"],
        capture_output=True,
        text=True,
        env={
            **__import__("os").environ,
            "XDG_CONFIG_HOME": str(tmp_path),
        },
    )
    assert result.returncode == 0


def test_cli_status_runs_without_error():
    """'automatr-espanso status' exits 0 (Espanso may or may not be installed)."""
    result = subprocess.run(
        [sys.executable, "-m", "automatr_espanso", "status"],
        capture_output=True,
        text=True,
    )
    # Status reports availability — should not crash regardless of Espanso presence
    assert result.returncode == 0
