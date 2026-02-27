"""Tests for VariableEditorWidget — inline variable CRUD and validation.

Covers add/delete rows, name validation, type-specific fields,
get/load/clear, YAML preview, and round-trip save with variables.
"""

from unittest.mock import patch

import pytest

from automatr_espanso.core.templates import Template, TemplateManager, Variable


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture()
def tm(tmp_path):
    """Create a TemplateManager backed by a temp directory."""
    return TemplateManager(templates_dir=tmp_path)


@pytest.fixture()
def _patch_config():
    """Patch get_config for variable editor widget tests."""
    with patch("automatr_espanso.ui.variable_editor.get_config"):
        yield


@pytest.fixture()
def var_editor(qtbot, _patch_config):
    """Create a standalone VariableEditorWidget for testing."""
    from automatr_espanso.ui.variable_editor import VariableEditorWidget

    widget = VariableEditorWidget()
    qtbot.addWidget(widget)
    return widget


# ── Add / Delete ────────────────────────────────────────────────────────────


def test_add_variable_creates_row(var_editor, qtbot):
    """Clicking 'Add Variable' creates an inline row with name, type, and default."""
    assert var_editor.row_count() == 0
    var_editor._add_variable()
    assert var_editor.row_count() == 1

    row = var_editor.get_row(0)
    assert row is not None
    # Row should have name, type combo, and default fields
    assert hasattr(row, "_name_edit")
    assert hasattr(row, "_type_combo")
    assert hasattr(row, "_default_edit")


def test_delete_variable_removes_row(var_editor, qtbot):
    """Deleting a variable row removes it from the list."""
    var_editor._add_variable()
    var_editor._add_variable()
    assert var_editor.row_count() == 2

    var_editor.delete_row(0)
    assert var_editor.row_count() == 1


# ── Name Validation ────────────────────────────────────────────────────────


def test_valid_variable_name(var_editor, qtbot):
    """Alphanumeric + underscore names are valid."""
    var_editor._add_variable()
    row = var_editor.get_row(0)
    row._name_edit.setText("my_var_1")
    assert row.is_valid()


def test_empty_name_invalid(var_editor, qtbot):
    """Empty variable name is invalid."""
    var_editor._add_variable()
    row = var_editor.get_row(0)
    row._name_edit.setText("")
    assert not row.is_valid()


def test_special_chars_invalid(var_editor, qtbot):
    """Variable names with special characters are invalid."""
    var_editor._add_variable()
    row = var_editor.get_row(0)
    row._name_edit.setText("my-var!")
    assert not row.is_valid()


def test_duplicate_name_invalid(var_editor, qtbot):
    """Duplicate variable names within the same template are invalid."""
    var_editor._add_variable()
    var_editor._add_variable()
    row0 = var_editor.get_row(0)
    row1 = var_editor.get_row(1)
    row0._name_edit.setText("dupe")
    row1._name_edit.setText("dupe")
    # Validation is at the editor level
    errors = var_editor.validate()
    assert len(errors) > 0
    assert "duplicate" in errors[0].lower() or "unique" in errors[0].lower()


def test_invalid_name_shows_error(var_editor, qtbot):
    """Invalid name shows an inline error label on the row."""
    var_editor._add_variable()
    row = var_editor.get_row(0)
    row._name_edit.setText("bad name!")
    row.validate()
    assert row._error_label.text() != ""


# ── Type-specific Fields ───────────────────────────────────────────────────


def test_date_type_shows_format(var_editor, qtbot):
    """Selecting date type shows a format parameter field."""
    var_editor._add_variable()
    row = var_editor.get_row(0)
    row._type_combo.setCurrentText("date")
    assert row._format_edit.isVisible()


def test_form_type_shows_multiline(var_editor, qtbot):
    """Form type shows a multiline toggle checkbox."""
    var_editor._add_variable()
    row = var_editor.get_row(0)
    row._type_combo.setCurrentText("form")
    assert row._multiline_cb.isVisible()


def test_date_type_hides_multiline(var_editor, qtbot):
    """Date type hides the multiline toggle."""
    var_editor._add_variable()
    row = var_editor.get_row(0)
    row._type_combo.setCurrentText("date")
    assert not row._multiline_cb.isVisible()


def test_form_type_hides_format(var_editor, qtbot):
    """Form type hides the format field."""
    var_editor._add_variable()
    row = var_editor.get_row(0)
    row._type_combo.setCurrentText("form")
    assert not row._format_edit.isVisible()


# ── Get / Load / Clear ─────────────────────────────────────────────────────


def test_get_variables_returns_variable_list(var_editor, qtbot):
    """get_variables() returns Variable objects matching UI state."""
    var_editor._add_variable()
    row = var_editor.get_row(0)
    row._name_edit.setText("user_name")
    row._type_combo.setCurrentText("form")
    row._default_edit.setText("Alice")

    variables = var_editor.get_variables()
    assert len(variables) == 1
    v = variables[0]
    assert v.name == "user_name"
    assert v.type == "form"
    assert v.default == "Alice"
    assert v.label == "User Name"  # auto-generated from name


def test_get_variables_date_with_format(var_editor, qtbot):
    """Date variable captures format param."""
    var_editor._add_variable()
    row = var_editor.get_row(0)
    row._name_edit.setText("today")
    row._type_combo.setCurrentText("date")
    row._format_edit.setText("%Y-%m-%d")

    variables = var_editor.get_variables()
    assert len(variables) == 1
    v = variables[0]
    assert v.type == "date"
    assert v.params == {"format": "%Y-%m-%d"}


def test_get_variables_form_multiline(var_editor, qtbot):
    """Form variable captures multiline flag."""
    var_editor._add_variable()
    row = var_editor.get_row(0)
    row._name_edit.setText("body")
    row._type_combo.setCurrentText("form")
    row._multiline_cb.setChecked(True)

    variables = var_editor.get_variables()
    assert variables[0].multiline is True


def test_load_variables_populates_rows(var_editor, qtbot):
    """load_variables() creates rows from existing Variable list."""
    variables = [
        Variable(name="user", default="Alice"),
        Variable(name="today", type="date", params={"format": "%Y-%m-%d"}),
    ]
    var_editor.load_variables(variables)
    assert var_editor.row_count() == 2

    row0 = var_editor.get_row(0)
    assert row0._name_edit.text() == "user"
    assert row0._default_edit.text() == "Alice"

    row1 = var_editor.get_row(1)
    assert row1._name_edit.text() == "today"
    assert row1._type_combo.currentText() == "date"
    assert row1._format_edit.text() == "%Y-%m-%d"


def test_clear_removes_all_rows(var_editor, qtbot):
    """clear() removes all variable rows."""
    var_editor._add_variable()
    var_editor._add_variable()
    assert var_editor.row_count() == 2
    var_editor.clear()
    assert var_editor.row_count() == 0


# ── Signal ──────────────────────────────────────────────────────────────────


def test_variables_changed_signal(var_editor, qtbot):
    """Adding a variable emits the variables_changed signal."""
    with qtbot.waitSignal(var_editor.variables_changed, timeout=1000):
        var_editor._add_variable()


# ── YAML Preview (integrated into template editor) ─────────────────────────


@pytest.fixture()
def _patch_editor_deps(tm):
    """Patch dependencies for TemplateEditorWidget."""
    with (
        patch(
            "automatr_espanso.ui.template_editor.get_template_manager",
            return_value=tm,
        ),
        patch("automatr_espanso.ui.template_editor.get_config"),
    ):
        yield


@pytest.fixture()
def editor(qtbot, _patch_editor_deps):
    """Create a TemplateEditorWidget for testing YAML preview."""
    from automatr_espanso.ui.template_editor import TemplateEditorWidget

    widget = TemplateEditorWidget()
    qtbot.addWidget(widget)
    return widget


def test_yaml_preview_updates_on_trigger_change(editor, qtbot):
    """YAML preview reflects trigger changes."""
    editor._trigger_edit.setText(":greet")
    editor._content_edit.setPlainText("Hello")
    preview = editor._yaml_preview.toPlainText()
    assert ":greet" in preview


def test_yaml_preview_shows_variables(editor, qtbot):
    """YAML preview includes variable entries."""
    editor._trigger_edit.setText(":greet")
    editor._content_edit.setPlainText("Hello {{name}}")
    editor._variable_editor._add_variable()
    row = editor._variable_editor.get_row(0)
    row._name_edit.setText("name")
    row._type_combo.setCurrentText("form")
    # Force preview update
    editor._update_yaml_preview()
    preview = editor._yaml_preview.toPlainText()
    assert "name" in preview
    assert "form" in preview


def test_yaml_preview_empty_when_no_trigger(editor, qtbot):
    """YAML preview is empty/placeholder when trigger is blank."""
    editor._trigger_edit.setText("")
    editor._content_edit.setPlainText("some content")
    editor._update_yaml_preview()
    preview = editor._yaml_preview.toPlainText()
    # Should be empty or show a hint — no YAML match block
    assert "trigger" not in preview.lower() or preview.strip() == ""


# ── Save with Variables ─────────────────────────────────────────────────────


def test_save_persists_variables(editor, tm, qtbot):
    """Saving a template with variables persists variable data to disk."""
    editor._name_edit.setText("With Vars")
    editor._trigger_edit.setText(":vars")
    editor._content_edit.setPlainText("Hello {{name}}")

    editor._variable_editor._add_variable()
    row = editor._variable_editor.get_row(0)
    row._name_edit.setText("name")
    row._type_combo.setCurrentText("form")
    row._default_edit.setText("World")

    with qtbot.waitSignal(editor.template_saved, timeout=1000):
        editor._save()

    saved = tm.get("With Vars")
    assert saved is not None
    assert len(saved.variables) == 1
    assert saved.variables[0].name == "name"
    assert saved.variables[0].default == "World"
    assert saved.variables[0].type == "form"


def test_load_template_with_variables(editor, tm, qtbot):
    """Loading a template with existing variables populates variable rows."""
    t = tm.create(
        name="Has Vars",
        content="Today is {{today}}",
        trigger=":date",
    )
    t.variables = [
        Variable(name="today", type="date", params={"format": "%Y-%m-%d"}),
    ]
    tm.save(t)

    editor.load_template(t)
    assert editor._variable_editor.row_count() == 1
    row = editor._variable_editor.get_row(0)
    assert row._name_edit.text() == "today"
    assert row._type_combo.currentText() == "date"
