"""Tests for template import feature.

Covers: import_template(), import_templates(), CLI import command,
GUI import button.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from espansr.core.templates import TemplateManager

# ─── Helpers ─────────────────────────────────────────────────────────────────


def _write_json(path: Path, data: dict) -> Path:
    """Write a dict as pretty-printed JSON and return the path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path


# ─── import_template — field stripping ───────────────────────────────────────


def test_import_strips_unknown_fields(tmp_path):
    """import_template() drops top-level fields not in the internal schema."""
    from espansr.core.templates import import_template

    src = _write_json(
        tmp_path / "src" / "greeting.json",
        {
            "name": "Greeting",
            "content": "Hello {{name}}",
            "trigger": ":greet",
            "author": "someone",
            "tags": ["hello", "friendly"],
            "id": 42,
        },
    )
    mgr = TemplateManager(templates_dir=tmp_path / "templates")
    result = import_template(src, mgr)

    assert result.template is not None
    assert result.template.name == "Greeting"
    assert result.template.content == "Hello {{name}}"
    assert result.template.trigger == ":greet"
    # Unknown fields must not appear in the saved JSON
    saved_data = json.loads(result.template._path.read_text())
    assert "author" not in saved_data
    assert "tags" not in saved_data
    assert "id" not in saved_data


# ─── import_template — variable mapping ──────────────────────────────────────


def test_import_maps_variables(tmp_path):
    """Variables are correctly mapped to the internal Variable schema."""
    from espansr.core.templates import import_template

    src = _write_json(
        tmp_path / "src" / "dated.json",
        {
            "name": "Dated Note",
            "content": "Date: {{today}}",
            "variables": [
                {"name": "today", "type": "date", "params": {"format": "%Y-%m-%d"}},
            ],
        },
    )
    mgr = TemplateManager(templates_dir=tmp_path / "templates")
    result = import_template(src, mgr)

    assert result.template is not None
    assert len(result.template.variables) == 1
    v = result.template.variables[0]
    assert v.name == "today"
    assert v.type == "date"
    assert v.params == {"format": "%Y-%m-%d"}


def test_import_drops_unknown_variable_fields(tmp_path):
    """Unknown fields inside variable entries are dropped on import."""
    from espansr.core.templates import import_template

    src = _write_json(
        tmp_path / "src" / "extra_vars.json",
        {
            "name": "Extra Vars",
            "content": "{{user}}",
            "variables": [
                {
                    "name": "user",
                    "label": "User Name",
                    "default": "world",
                    "unknown_field": True,
                    "color": "red",
                },
            ],
        },
    )
    mgr = TemplateManager(templates_dir=tmp_path / "templates")
    result = import_template(src, mgr)

    assert result.template is not None
    v = result.template.variables[0]
    assert v.name == "user"
    assert v.label == "User Name"
    assert v.default == "world"
    # Unknown variable fields must not survive
    saved_data = json.loads(result.template._path.read_text())
    saved_var = saved_data["variables"][0]
    assert "unknown_field" not in saved_var
    assert "color" not in saved_var


# ─── import_template — name collision ────────────────────────────────────────


def test_import_renames_on_collision(tmp_path):
    """When the imported name already exists, a numeric suffix is added."""
    from espansr.core.templates import import_template

    mgr = TemplateManager(templates_dir=tmp_path / "templates")
    mgr.create(name="Greeting", content="Hi")

    src = _write_json(
        tmp_path / "src" / "greeting.json",
        {"name": "Greeting", "content": "Hello again"},
    )
    result = import_template(src, mgr)

    assert result.template is not None
    assert result.template.name == "Greeting (2)"
    # Original is untouched
    original = mgr.get("Greeting")
    assert original is not None
    assert original.content == "Hi"


def test_import_renames_increments_on_multiple_collisions(tmp_path):
    """Suffix increments when multiple collisions exist."""
    from espansr.core.templates import import_template

    mgr = TemplateManager(templates_dir=tmp_path / "templates")
    mgr.create(name="Greeting", content="v1")
    mgr.create(name="Greeting (2)", content="v2")

    src = _write_json(
        tmp_path / "src" / "greeting.json",
        {"name": "Greeting", "content": "v3"},
    )
    result = import_template(src, mgr)

    assert result.template is not None
    assert result.template.name == "Greeting (3)"


# ─── import_template — name from filename ───────────────────────────────────


def test_import_uses_filename_when_name_missing(tmp_path):
    """When JSON lacks a 'name' field, the filename stem is used."""
    from espansr.core.templates import import_template

    src = _write_json(
        tmp_path / "src" / "my_template.json",
        {"content": "Hello there"},
    )
    mgr = TemplateManager(templates_dir=tmp_path / "templates")
    result = import_template(src, mgr)

    assert result.template is not None
    assert result.template.name == "my template"


# ─── import_template — malformed JSON ───────────────────────────────────────


def test_import_malformed_json_error(tmp_path):
    """Malformed JSON files produce a clear error without crashing."""
    from espansr.core.templates import import_template

    bad_file = tmp_path / "src" / "broken.json"
    bad_file.parent.mkdir(parents=True, exist_ok=True)
    bad_file.write_text("{invalid json", encoding="utf-8")

    mgr = TemplateManager(templates_dir=tmp_path / "templates")
    result = import_template(bad_file, mgr)

    assert result.template is None
    assert result.error is not None
    assert "broken.json" in result.error or "JSON" in result.error


def test_import_nonexistent_file_error(tmp_path):
    """Importing a nonexistent path produces an error."""
    from espansr.core.templates import import_template

    mgr = TemplateManager(templates_dir=tmp_path / "templates")
    result = import_template(tmp_path / "no_such_file.json", mgr)

    assert result.template is None
    assert result.error is not None


# ─── import_templates — directory import ─────────────────────────────────────


def test_import_directory_summary(tmp_path):
    """import_templates() processes all JSON files and returns a summary."""
    from espansr.core.templates import import_templates

    src_dir = tmp_path / "src"
    _write_json(src_dir / "a.json", {"name": "Alpha", "content": "a"})
    _write_json(src_dir / "b.json", {"name": "Beta", "content": "b"})
    # Non-JSON file should be skipped
    (src_dir / "readme.txt").write_text("not a template", encoding="utf-8")

    mgr = TemplateManager(templates_dir=tmp_path / "templates")
    summary = import_templates(src_dir, mgr)

    assert summary.succeeded == 2
    assert summary.failed == 0
    assert summary.skipped == 0
    assert len(summary.results) == 2


def test_import_directory_with_errors(tmp_path):
    """Directory import counts errors in the summary."""
    from espansr.core.templates import import_templates

    src_dir = tmp_path / "src"
    _write_json(src_dir / "good.json", {"name": "Good", "content": "ok"})
    bad = src_dir / "bad.json"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("not json!", encoding="utf-8")

    mgr = TemplateManager(templates_dir=tmp_path / "templates")
    summary = import_templates(src_dir, mgr)

    assert summary.succeeded == 1
    assert summary.failed == 1


def test_import_directory_nonexistent_path(tmp_path):
    """import_templates() returns error summary for nonexistent directory."""
    from espansr.core.templates import import_templates

    mgr = TemplateManager(templates_dir=tmp_path / "templates")
    summary = import_templates(tmp_path / "no_such_dir", mgr)

    assert summary.succeeded == 0
    assert summary.error is not None


# ─── CLI import command ──────────────────────────────────────────────────────


def test_cli_import_file(tmp_path, capsys):
    """espansr import <file> imports a single template and prints a summary."""
    import espansr.core.templates as _tmod

    src = _write_json(
        tmp_path / "src" / "greeting.json",
        {"name": "CLI Greeting", "content": "hi", "trigger": ":cligreet"},
    )

    old_mgr = _tmod._template_manager
    _tmod._template_manager = None
    try:
        with patch(
            "espansr.core.templates.get_templates_dir",
            return_value=tmp_path / "templates",
        ):
            from espansr.__main__ import cmd_import

            args = MagicMock()
            args.path = str(src)
            code = cmd_import(args)
    finally:
        _tmod._template_manager = old_mgr

    assert code == 0
    captured = capsys.readouterr()
    assert "1" in captured.out  # 1 imported


def test_cli_import_directory(tmp_path, capsys):
    """espansr import <dir> imports all JSON files and prints a summary."""
    import espansr.core.templates as _tmod

    src_dir = tmp_path / "src"
    _write_json(src_dir / "a.json", {"name": "A", "content": "a"})
    _write_json(src_dir / "b.json", {"name": "B", "content": "b"})

    old_mgr = _tmod._template_manager
    _tmod._template_manager = None
    try:
        with patch(
            "espansr.core.templates.get_templates_dir",
            return_value=tmp_path / "templates",
        ):
            from espansr.__main__ import cmd_import

            args = MagicMock()
            args.path = str(src_dir)
            code = cmd_import(args)
    finally:
        _tmod._template_manager = old_mgr

    assert code == 0
    captured = capsys.readouterr()
    assert "2" in captured.out


def test_cli_import_nonexistent_path(tmp_path, capsys):
    """espansr import <bad-path> exits with non-zero code."""
    from espansr.__main__ import cmd_import

    args = MagicMock()
    args.path = str(tmp_path / "nope.json")
    code = cmd_import(args)

    assert code == 1


# ─── GUI import button ──────────────────────────────────────────────────────


def test_gui_import_button_exists(tmp_path):
    """MainWindow toolbar contains an Import button."""
    pytest.importorskip("PyQt6.QtWidgets")

    from PyQt6.QtWidgets import QApplication, QPushButton

    _app = QApplication.instance() or QApplication([])

    with (
        patch("espansr.ui.main_window.get_config") as mock_cfg,
        patch("espansr.ui.main_window.get_config_manager"),
        patch("espansr.ui.main_window.save_config"),
        patch("espansr.core.templates.get_templates_dir", return_value=tmp_path),
        patch("espansr.integrations.espanso.get_match_dir", return_value=None),
    ):
        from espansr.core.config import EspansoConfig, UIConfig

        cfg = MagicMock()
        cfg.espanso = EspansoConfig()
        cfg.ui = UIConfig()
        cfg.ui.splitter_sizes = [200, 400]
        cfg.ui.window_geometry = ""
        cfg.ui.last_template = ""
        mock_cfg.return_value = cfg

        from espansr.ui.main_window import MainWindow

        window = MainWindow()
        buttons = window.findChildren(QPushButton)
        import_buttons = [b for b in buttons if b.text() == "Import"]
        assert len(import_buttons) == 1
        window.close()
