"""Inline template editor widget for espansr.

Right-panel editor with name, trigger, content, variables, YAML preview,
and output preview.  Saves new or existing templates via TemplateManager.
"""

from datetime import datetime
from typing import Optional

import yaml
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from espansr.core.config import get_config
from espansr.core.templates import Template, get_template_manager
from espansr.integrations.espanso import (
    _build_espanso_var_entry,
    _convert_to_espanso_placeholders,
)
from espansr.ui.variable_editor import VariableEditorWidget


class TemplateEditorWidget(QWidget):
    """Inline editor for template name, trigger, content, variables, and YAML preview.

    Emits:
        template_saved(Template): Fired after a successful save.
        status_message(str, int): Fired with a message and duration (ms).
    """

    template_saved = pyqtSignal(object)
    status_message = pyqtSignal(str, int)

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the template editor."""
        super().__init__(parent)
        self._current_template: Optional[Template] = None
        self._setup_ui()
        self._connect_preview_signals()

    def _setup_ui(self) -> None:
        """Build the editor layout: name, trigger, content, variables, YAML preview, save."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 10, 10, 10)

        config = get_config()
        label_size = config.ui.font_size + 1

        # Header
        header = QLabel("Editor")
        header.setStyleSheet(f"font-weight: bold; font-size: {label_size}pt;")
        layout.addWidget(header)

        # Name field
        layout.addWidget(QLabel("Name:"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Template name")
        layout.addWidget(self._name_edit)

        # Trigger field
        trigger_row = QHBoxLayout()
        trigger_row.addWidget(QLabel("Trigger:"))
        hint = QLabel("(start with ':' for Espanso)")
        hint.setStyleSheet("color: #808080;")
        trigger_row.addWidget(hint)
        trigger_row.addStretch()
        layout.addLayout(trigger_row)

        self._trigger_edit = QLineEdit()
        self._trigger_edit.setPlaceholderText(":mytrigger")
        layout.addWidget(self._trigger_edit)

        # Content field
        layout.addWidget(QLabel("Content:"))
        self._content_edit = QPlainTextEdit()
        self._content_edit.setPlaceholderText("Template content…")
        layout.addWidget(self._content_edit)

        # Variable editor
        self._variable_editor = VariableEditorWidget()
        layout.addWidget(self._variable_editor)

        # Preview container (togglable)
        self._preview_container = QWidget()
        preview_layout = QVBoxLayout(self._preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        # YAML preview
        preview_label = QLabel("YAML Preview:")
        preview_label.setStyleSheet("font-weight: bold;")
        preview_layout.addWidget(preview_label)

        self._yaml_preview = QPlainTextEdit()
        self._yaml_preview.setReadOnly(True)
        self._yaml_preview.setPlaceholderText("Set a trigger to see YAML preview…")
        self._yaml_preview.setMaximumHeight(200)
        preview_layout.addWidget(self._yaml_preview)

        # Output preview
        output_label = QLabel("Output Preview:")
        output_label.setStyleSheet("font-weight: bold;")
        preview_layout.addWidget(output_label)

        self._output_preview = QPlainTextEdit()
        self._output_preview.setReadOnly(True)
        self._output_preview.setPlaceholderText("Enter content to see expanded output…")
        self._output_preview.setMaximumHeight(200)
        self._output_preview.setStyleSheet("background-color: #f5f5f5;")
        preview_layout.addWidget(self._output_preview)

        layout.addWidget(self._preview_container)

        # Save button
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)

    def _connect_preview_signals(self) -> None:
        """Wire field changes to YAML and output preview updates."""
        self._trigger_edit.textChanged.connect(self._update_yaml_preview)
        self._content_edit.textChanged.connect(self._update_yaml_preview)
        self._content_edit.textChanged.connect(self._update_output_preview)
        self._variable_editor.variables_changed.connect(self._update_yaml_preview)
        self._variable_editor.variables_changed.connect(self._update_output_preview)

    # ── Public API ──────────────────────────────────────────────────────────

    def set_previews_visible(self, visible: bool) -> None:
        """Show or hide the YAML preview and output preview panes."""
        self._preview_container.setVisible(visible)

    def load_template(self, template: Template) -> None:
        """Populate editor fields from a Template object."""
        self._current_template = template
        self._name_edit.setText(template.name)
        self._trigger_edit.setText(template.trigger)
        self._content_edit.setPlainText(template.content)
        self._variable_editor.load_variables(template.variables or [])
        self._update_yaml_preview()
        self._update_output_preview()

    def clear(self) -> None:
        """Clear all fields for creating a new template."""
        self._current_template = None
        self._name_edit.clear()
        self._trigger_edit.clear()
        self._content_edit.clear()
        self._variable_editor.clear()
        self._yaml_preview.clear()
        self._output_preview.clear()

    # ── YAML Preview ────────────────────────────────────────────────────────

    def _update_yaml_preview(self) -> None:
        """Regenerate the YAML preview from current editor state."""
        trigger = self._trigger_edit.text().strip()
        if not trigger:
            self._yaml_preview.clear()
            return

        content = self._content_edit.toPlainText()
        variables = self._variable_editor.get_variables()

        replace_text = _convert_to_espanso_placeholders(content, variables)
        match_entry: dict = {
            "trigger": trigger,
            "replace": replace_text,
        }

        if variables:
            match_entry["vars"] = [_build_espanso_var_entry(var) for var in variables]

        preview = yaml.dump(
            {"matches": [match_entry]},
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
        self._yaml_preview.setPlainText(preview)

    # ── Output Preview ───────────────────────────────────────────────────────

    def _update_output_preview(self) -> None:
        """Regenerate the output preview with variables expanded."""
        content = self._content_edit.toPlainText()
        if not content:
            self._output_preview.clear()
            return

        variables = self._variable_editor.get_variables()
        result = content
        for var in variables:
            placeholder = "{{" + var.name + "}}"
            if var.type == "date":
                fmt = var.params.get("format", "%Y-%m-%d")
                value = datetime.now().strftime(fmt)
            elif var.default:
                value = var.default
            else:
                value = var.label
            result = result.replace(placeholder, value)

        self._output_preview.setPlainText(result)

    # ── Internal ────────────────────────────────────────────────────────────

    def _save(self) -> None:
        """Save the current editor state as a new or existing template."""
        name = self._name_edit.text().strip()
        if not name:
            self.status_message.emit("Template name is required", 3000)
            return

        trigger = self._trigger_edit.text().strip()
        content = self._content_edit.toPlainText()
        variables = self._variable_editor.get_variables()
        manager = get_template_manager()

        try:
            if self._current_template is None:
                template = manager.create(
                    name=name,
                    content=content,
                    trigger=trigger,
                )
                template.variables = variables
                manager.save(template)
                self._current_template = template
                self.status_message.emit(f"Created '{name}'", 3000)
            else:
                self._current_template.name = name
                self._current_template.trigger = trigger
                self._current_template.content = content
                self._current_template.variables = variables
                manager.save(self._current_template)
                self.status_message.emit(f"Saved '{name}'", 3000)
            self.template_saved.emit(self._current_template)
        except Exception as exc:
            self.status_message.emit(f"Save failed: {exc}", 5000)
