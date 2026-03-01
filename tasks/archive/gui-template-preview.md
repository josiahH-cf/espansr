# Tasks: GUI Template Preview Pane

**Spec:** /specs/gui-template-preview.md

## Status

- Total: 2
- Complete: 2
- Remaining: 0

## Task List

### Task 1: Write failing tests for preview pane

- **Files:** `tests/test_gui_editor.py`
- **Done when:** Tests exist for all 7 acceptance criteria; all new tests fail (preview widget does not exist yet); existing tests still pass
- **Criteria covered:** AC-1 through AC-7
- **Status:** [x] Complete

#### Test plan

1. `test_preview_widget_exists` — editor has `_output_preview` attribute of type `QPlainTextEdit`
2. `test_preview_is_readonly` — `_output_preview.isReadOnly()` is True
3. `test_preview_no_variables` — loading a template with no variables shows content as-is
4. `test_preview_replaces_defaults` — loading a template with variables shows defaults substituted
5. `test_preview_uses_label_when_no_default` — variable with empty default uses label instead
6. `test_preview_updates_on_content_edit` — changing content field updates the preview
7. `test_preview_date_variable` — date-type variable shows formatted current date

### Task 2: Implement preview pane

- **Files:** `espansr/ui/template_editor.py`
- **Done when:** All preview tests pass; existing editor tests pass unchanged; preview section appears below YAML preview
- **Criteria covered:** AC-1 through AC-7
- **Status:** [x] Complete

#### Implementation details

1. In `_setup_ui()`, after the YAML preview section, add:
   - "Output Preview:" label (bold)
   - `self._output_preview = QPlainTextEdit()` — read-only, styled distinctly
2. Add `_update_output_preview()` method:
   - Get content from `_content_edit`
   - Get variables from `_variable_editor.get_variables()`
   - For each variable, replace `{{var.name}}` with:
     - `datetime.now().strftime(var.params.get("format", "%Y-%m-%d"))` if `var.type == "date"`
     - `var.default` if non-empty
     - `var.label` otherwise
   - Set the result on `_output_preview`
3. In `_connect_preview_signals()`, connect same signals to `_update_output_preview()`
4. In `load_template()`, call `_update_output_preview()`
5. In `clear()`, call `self._output_preview.clear()`

## Test Strategy

| Criterion | Test |
|-----------|------|
| AC-1 (preview section exists) | `test_preview_widget_exists` |
| AC-2 (placeholders replaced by defaults) | `test_preview_replaces_defaults` |
| AC-3 (label fallback) | `test_preview_uses_label_when_no_default` |
| AC-4 (live updates) | `test_preview_updates_on_content_edit` |
| AC-5 (read-only) | `test_preview_is_readonly` |
| AC-6 (no variables) | `test_preview_no_variables` |
| AC-7 (visually distinct) | `test_preview_is_readonly` (read-only styling) |

## Session Log

### 2026-02-28 — Tasks 1 & 2 complete
- Added `_output_preview` QPlainTextEdit below YAML preview in template editor
- `_update_output_preview()` replaces `{{var}}` placeholders with defaults, labels, or formatted dates
- Preview is read-only with distinct background styling
- Live updates wired to content and variable change signals
- 7 new tests in `tests/test_gui_editor.py`; 230 total tests pass; lint clean
- **Both tasks complete — feature done**

