"""Tests for Espanso config validation.

Covers: validate_template(), validate_all(), ValidationWarning dataclass,
sync integration, and CLI validate command.
"""

from unittest.mock import MagicMock, patch

from espansr.core.templates import Template, Variable

# ─── ValidationWarning dataclass ─────────────────────────────────────────────


def test_validation_warning_has_required_fields():
    """ValidationWarning has severity, message, and template_name."""
    from espansr.integrations.validate import ValidationWarning

    w = ValidationWarning(
        severity="error",
        message="trigger is empty",
        template_name="my_template",
    )
    assert w.severity == "error"
    assert w.message == "trigger is empty"
    assert w.template_name == "my_template"


# ─── validate_template() — valid template ────────────────────────────────────


def test_valid_template_returns_no_warnings():
    """validate_template() returns empty list for a well-formed template."""
    from espansr.integrations.validate import validate_template

    t = Template(
        name="greeting",
        content="Hello {{name}}!",
        trigger=":greet",
        variables=[Variable(name="name")],
    )
    result = validate_template(t)
    assert result == []


# ─── validate_template() — trigger checks ────────────────────────────────────


def test_error_on_empty_trigger():
    """validate_template() returns error when trigger is empty."""
    from espansr.integrations.validate import validate_template

    t = Template(name="test", content="Hello", trigger="")
    result = validate_template(t)
    errors = [w for w in result if w.severity == "error"]
    assert len(errors) >= 1
    assert any(
        "empty" in w.message.lower() or "trigger" in w.message.lower() for w in errors
    )


def test_error_on_short_trigger():
    """validate_template() returns error when trigger is shorter than 2 chars."""
    from espansr.integrations.validate import validate_template

    t = Template(name="test", content="Hello", trigger=":")
    result = validate_template(t)
    errors = [w for w in result if w.severity == "error"]
    assert len(errors) >= 1
    assert any("short" in w.message.lower() or "2" in w.message for w in errors)


def test_warning_on_trigger_bad_prefix():
    """validate_template() warns when trigger doesn't start with : or /."""
    from espansr.integrations.validate import validate_template

    t = Template(name="test", content="Hello", trigger="greet")
    result = validate_template(t)
    warnings = [w for w in result if w.severity == "warning"]
    assert len(warnings) >= 1
    assert any(":" in w.message or "prefix" in w.message.lower() for w in warnings)


def test_valid_trigger_starting_with_colon():
    """validate_template() accepts trigger starting with ':'."""
    from espansr.integrations.validate import validate_template

    t = Template(name="test", content="Hello", trigger=":greet")
    result = validate_template(t)
    # No trigger-related errors or warnings
    trigger_issues = [w for w in result if "trigger" in w.message.lower()]
    assert trigger_issues == []


def test_valid_trigger_starting_with_slash():
    """validate_template() accepts trigger starting with '/' (regex trigger)."""
    from espansr.integrations.validate import validate_template

    t = Template(name="test", content="Hello", trigger="/greet/")
    result = validate_template(t)
    trigger_issues = [w for w in result if "trigger" in w.message.lower()]
    assert trigger_issues == []


# ─── validate_template() — variable checks ──────────────────────────────────


def test_warning_on_unmatched_placeholder():
    """validate_template() warns when content has {{var}} but no matching variable."""
    from espansr.integrations.validate import validate_template

    t = Template(
        name="test",
        content="Hello {{name}} from {{city}}",
        trigger=":greet",
        variables=[Variable(name="name")],
    )
    result = validate_template(t)
    warnings = [w for w in result if w.severity == "warning"]
    assert len(warnings) >= 1
    assert any("city" in w.message for w in warnings)


def test_warning_on_unused_variable():
    """validate_template() warns when variable is defined but not in content."""
    from espansr.integrations.validate import validate_template

    t = Template(
        name="test",
        content="Hello world",
        trigger=":greet",
        variables=[Variable(name="unused_var")],
    )
    result = validate_template(t)
    warnings = [w for w in result if w.severity == "warning"]
    assert len(warnings) >= 1
    assert any("unused_var" in w.message for w in warnings)


def test_no_warning_when_variables_match():
    """validate_template() returns no warnings when all variables match content."""
    from espansr.integrations.validate import validate_template

    t = Template(
        name="test",
        content="Hello {{first}} {{last}}",
        trigger=":greet",
        variables=[Variable(name="first"), Variable(name="last")],
    )
    result = validate_template(t)
    assert result == []


def test_template_name_set_in_warnings():
    """ValidationWarning.template_name matches the validated template."""
    from espansr.integrations.validate import validate_template

    t = Template(name="my_template", content="Hi", trigger="")
    result = validate_template(t)
    assert len(result) >= 1
    assert all(w.template_name == "my_template" for w in result)


# ─── validate_all() — cross-template checks ─────────────────────────────────


def test_validate_all_detects_duplicate_triggers():
    """validate_all() reports duplicate triggers across templates."""
    from espansr.integrations.validate import validate_all

    templates = [
        Template(name="template_a", content="A", trigger=":dup"),
        Template(name="template_b", content="B", trigger=":dup"),
    ]
    with patch("espansr.integrations.validate.get_template_manager") as mock_mgr:
        mock_mgr.return_value.iter_with_triggers.return_value = iter(templates)
        result = validate_all()

    errors = [
        w for w in result if w.severity == "error" and "duplicate" in w.message.lower()
    ]
    assert len(errors) >= 1
    assert any(":dup" in w.message for w in errors)


def test_validate_all_returns_per_template_warnings():
    """validate_all() includes single-template warnings alongside cross-template checks."""
    from espansr.integrations.validate import validate_all

    templates = [
        Template(name="bad_trigger", content="Hi", trigger="x"),
        Template(
            name="ok_template",
            content="Hello {{name}}",
            trigger=":ok",
            variables=[Variable(name="name")],
        ),
    ]
    with patch("espansr.integrations.validate.get_template_manager") as mock_mgr:
        mock_mgr.return_value.iter_with_triggers.return_value = iter(templates)
        result = validate_all()

    # Should have issues from bad_trigger template
    bad_issues = [w for w in result if w.template_name == "bad_trigger"]
    assert len(bad_issues) >= 1

    # ok_template should have no issues
    ok_issues = [w for w in result if w.template_name == "ok_template"]
    assert ok_issues == []


def test_validate_all_no_issues_on_clean_templates():
    """validate_all() returns empty list when all templates are valid."""
    from espansr.integrations.validate import validate_all

    templates = [
        Template(
            name="a",
            content="Hello {{x}}",
            trigger=":ta",
            variables=[Variable(name="x")],
        ),
        Template(
            name="b",
            content="World {{y}}",
            trigger=":tb",
            variables=[Variable(name="y")],
        ),
    ]
    with patch("espansr.integrations.validate.get_template_manager") as mock_mgr:
        mock_mgr.return_value.iter_with_triggers.return_value = iter(templates)
        result = validate_all()

    assert result == []


# ─── sync_to_espanso() integration ──────────────────────────────────────────


def test_sync_blocks_on_validation_errors(tmp_path):
    """sync_to_espanso() returns False when validation finds errors."""
    from espansr.integrations.validate import ValidationWarning

    fake_warnings = [
        ValidationWarning(severity="error", message="empty trigger", template_name="t"),
    ]

    match_dir = tmp_path / "match"
    match_dir.mkdir()

    with (
        patch("espansr.integrations.espanso.get_match_dir", return_value=match_dir),
        patch("espansr.integrations.espanso.clean_stale_espanso_files"),
        patch("espansr.integrations.espanso.validate_all", return_value=fake_warnings),
    ):
        from espansr.integrations.espanso import sync_to_espanso

        result = sync_to_espanso()

    assert result is False
    assert not (match_dir / "espansr.yml").exists()


def test_sync_proceeds_with_warnings_only(tmp_path):
    """sync_to_espanso() proceeds when validation has warnings but no errors."""
    from espansr.integrations.validate import ValidationWarning

    fake_warnings = [
        ValidationWarning(
            severity="warning", message="trigger missing prefix", template_name="t"
        ),
    ]

    match_dir = tmp_path / "match"
    match_dir.mkdir()

    templates = [
        Template(name="t", content="Hello", trigger="greet"),
    ]

    with (
        patch("espansr.integrations.espanso.get_match_dir", return_value=match_dir),
        patch("espansr.integrations.espanso.clean_stale_espanso_files"),
        patch("espansr.integrations.espanso.validate_all", return_value=fake_warnings),
        patch("espansr.integrations.espanso.get_template_manager") as mock_mgr,
        patch("espansr.integrations.espanso.is_wsl2", return_value=False),
    ):
        mock_mgr.return_value.iter_with_triggers.return_value = iter(templates)
        from espansr.integrations.espanso import sync_to_espanso

        result = sync_to_espanso()

    assert result is True


# ─── CLI validate command ────────────────────────────────────────────────────


def test_cli_validate_returns_0_on_clean():
    """cmd_validate() returns 0 when no errors found."""
    with patch("espansr.integrations.validate.validate_all", return_value=[]):
        from espansr.__main__ import cmd_validate

        result = cmd_validate(MagicMock())

    assert result == 0


def test_cli_validate_returns_1_on_errors():
    """cmd_validate() returns 1 when validation errors found."""
    from espansr.integrations.validate import ValidationWarning

    errors = [
        ValidationWarning(severity="error", message="bad trigger", template_name="t"),
    ]
    with patch("espansr.integrations.validate.validate_all", return_value=errors):
        from espansr.__main__ import cmd_validate

        result = cmd_validate(MagicMock())

    assert result == 1
