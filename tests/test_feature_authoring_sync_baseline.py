"""Feature tests for 1-authoring-sync-baseline.

These tests move AC-1..AC-3 from pre-test placeholders to executable behavior checks.
"""

import argparse
import json
from unittest.mock import patch

from espansr.core.templates import Template, TemplateManager, Variable
from espansr.integrations.validate import validate_template


def test_gui_editor_roundtrip_persists_and_previews(tmp_path):
    """AC-1: template edit roundtrip persists and preview rendering stays consistent."""
    manager = TemplateManager(templates_dir=tmp_path)

    template = Template(
        name="Greeting",
        content="Hello {{name}}",
        trigger=":greet",
        variables=[Variable(name="name", default="there")],
    )
    assert manager.save(template)

    loaded = manager.get("Greeting")
    assert loaded is not None
    assert loaded.content == "Hello {{name}}"
    assert loaded.render({}) == "Hello there"

    # Simulate editor update + save roundtrip.
    loaded.content = "Hello {{name}} from {{place}}"
    loaded.variables.append(Variable(name="place", default="espansr"))
    assert manager.save(loaded)

    reloaded = manager.get("Greeting")
    assert reloaded is not None
    assert reloaded.content == "Hello {{name}} from {{place}}"
    assert reloaded.render({"name": "Josiah"}) == "Hello Josiah from espansr"


def test_cli_validate_and_dry_run_do_not_mutate_outputs(tmp_path):
    """AC-2: validate reports issues and sync dry-run does not write output files."""
    from espansr.integrations.espanso import sync_to_espanso

    warning_template = Template(
        name="WarnCase",
        content="Hi {{name}} {{unknown}}",
        trigger=":warn",
        variables=[Variable(name="name")],
    )
    warnings = validate_template(warning_template)
    assert any(w.severity == "warning" for w in warnings)

    match_dir = tmp_path / "espanso" / "match"
    match_dir.mkdir(parents=True)
    output_file = match_dir / "espansr.yml"

    class _Stub:
        name = "SyncTemplate"
        trigger = ":sync"
        content = "hello"
        variables = []

    class _ManagerStub:
        def iter_with_triggers(self):
            return iter([_Stub()])

    with (
        patch("espansr.integrations.espanso.get_match_dir", return_value=match_dir),
        patch("espansr.integrations.espanso.get_template_manager", return_value=_ManagerStub()),
        patch("espansr.integrations.espanso.validate_all", return_value=[]),
    ):
        assert sync_to_espanso(dry_run=True) is True

    assert not output_file.exists(), "dry-run must not mutate espansr.yml"


def test_setup_and_status_are_platform_aware(tmp_path, capsys):
    """AC-3: setup and status commands emit platform-specific guidance when needed."""
    from espansr.__main__ import cmd_setup, cmd_status

    config_dir = tmp_path / "config" / "espansr"
    templates_dir = config_dir / "templates"
    bundled_dir = tmp_path / "bundled"
    bundled_dir.mkdir(parents=True)
    (bundled_dir / "sample.json").write_text(
        json.dumps({"name": "Sample", "content": "x", "trigger": ":x"}),
        encoding="utf-8",
    )

    with (
        patch("espansr.__main__.get_config_dir", return_value=config_dir),
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
        patch("espansr.__main__.get_espanso_config_dir", return_value=None),
        patch("espansr.__main__.get_platform", return_value="wsl2"),
    ):
        assert cmd_setup(argparse.Namespace(strict=False, dry_run=False, verbose=False)) == 0

    setup_output = capsys.readouterr().out
    assert "PowerShell" in setup_output
    assert "on Windows" in setup_output

    with (
        patch("espansr.__main__.get_espanso_config_dir", return_value=None),
        patch("espansr.__main__.get_platform", return_value="linux"),
        patch("shutil.which", return_value=None),
    ):
        assert cmd_status(None) == 0

    status_output = capsys.readouterr().out
    assert "https://espanso.org" in status_output
    assert "on Windows" not in status_output
