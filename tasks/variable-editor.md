# Tasks: Add Inline Variable Editor to Template Editor Panel

**Spec:** `/specs/variable-editor.md`
**Branch:** `feat/4-variable-editor`

## Task 1 — Write failing tests for variable editor widget

**File:** `tests/test_variable_editor.py`

- Test "Add Variable" button creates an inline row with name, type, and default fields
- Test deleting a variable row removes it from the list
- Test variable name validation: non-empty, alphanumeric + underscores, unique within template
- Test invalid variable name shows inline error message
- Test date-type variable shows format parameter field
- Test form-type variable shows multiline toggle
- Test `get_variables()` returns list of Variable objects matching the UI state
- Test `load_variables()` populates rows from existing Variable list
- Test YAML preview updates when trigger/content/variables change
- Test saving template with variables persists variable data to disk
- Test loading template with existing variables shows correct rows

**Done when:** All tests exist and fail (VariableEditorWidget does not exist yet).

## Task 2 — Create `variable_editor.py` widget

**File:** `automatr_espanso/ui/variable_editor.py` (new)

- `VariableEditorWidget(QWidget)` with "Variables" header + "Add Variable" button
- `VariableRowWidget(QWidget)` for each variable: name QLineEdit, type QComboBox (form/date), default QLineEdit, delete QPushButton
- Form-type: multiline QCheckBox
- Date-type: format QLineEdit (placeholder `%Y-%m-%d`)
- Name validation: non-empty, `^[a-zA-Z_][a-zA-Z0-9_]*$`, unique per template
- Inline error label on invalid name
- `get_variables() -> list[Variable]`
- `load_variables(variables: list[Variable])` — populates rows
- `clear()` — removes all rows
- Signals: `variables_changed()` emitted on any edit

**Done when:** Widget tests for variable CRUD and validation pass.

## Task 3 — Integrate variable editor + YAML preview into template_editor.py

**Files:** `automatr_espanso/ui/template_editor.py` (modify)

- Add `VariableEditorWidget` below content field
- Add YAML preview `QPlainTextEdit` (read-only) below variables
- Wire `_update_yaml_preview()` on trigger/content/variable changes
- Use `_build_espanso_var_entry()` and `_convert_to_espanso_placeholders()` from espanso.py for preview
- Save includes variables from `get_variables()`
- `load_template()` calls `load_variables()` on the variable editor
- `clear()` calls variable editor `clear()`

**Done when:** YAML preview tests and save-with-variables tests pass.

## Task 4 — Update theme.py and run full test suite

**Files:** `automatr_espanso/ui/theme.py` (modify)

- Add styles for variable rows, type dropdown, inline error labels
- Full test suite green across all test files

**Done when:** All tests pass, theme covers new widgets.

## Progress

| Task | Status |
|------|--------|
| 1    | Not Started |
| 2    | Not Started |
| 3    | Not Started |
| 4    | Not Started |
