"""Trigger editor dialog for automatr-espanso.

Allows editing a template's Espanso trigger string with a live YAML preview
showing exactly what will be written to automatr.yml.
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
)

from automatr_espanso.core.templates import Template, get_template_manager
from automatr_espanso.integrations.espanso import (
    _build_espanso_var_entry,
    _convert_to_espanso_placeholders,
)


class TriggerEditorDialog(QDialog):
    """Dialog for editing a template's Espanso trigger string.

    Shows a live YAML preview of the Espanso match entry as the trigger
    or content changes, so the user can verify the output before saving.
    """

    def __init__(self, template: Template, parent: Optional[object] = None):
        """Initialize with the template to edit."""
        super().__init__(parent)
        self._template = template
        self.setWindowTitle(f"Edit Trigger — {template.name}")
        self.setMinimumWidth(560)
        self.setMinimumHeight(400)
        self._setup_ui()
        self._update_preview(template.trigger or "")

    def _setup_ui(self) -> None:
        """Build the dialog layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Template name (read-only info)
        name_label = QLabel(f"Template: <b>{self._template.name}</b>")
        layout.addWidget(name_label)

        if self._template.description:
            desc_label = QLabel(self._template.description)
            desc_label.setStyleSheet("color: #808080; font-style: italic;")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)

        # Trigger input
        trigger_layout = QHBoxLayout()
        trigger_layout.addWidget(QLabel("Trigger:"))

        self._trigger_edit = QLineEdit(self._template.trigger or "")
        self._trigger_edit.setPlaceholderText(":mytrigger")
        self._trigger_edit.textChanged.connect(self._update_preview)
        trigger_layout.addWidget(self._trigger_edit)

        hint = QLabel("(start with ':' for Espanso default mode)")
        hint.setStyleSheet("color: #808080; font-size: 11pt;")
        trigger_layout.addWidget(hint)
        layout.addLayout(trigger_layout)

        # YAML preview
        preview_label = QLabel("Espanso match preview (automatr.yml):")
        preview_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(preview_label)

        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        layout.addWidget(self._preview)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_preview(self, trigger: str) -> None:
        """Re-render the YAML preview when the trigger text changes."""
        import yaml

        replace_text = _convert_to_espanso_placeholders(
            self._template.content, self._template.variables or []
        )
        entry: dict = {
            "trigger": trigger or ":example",
            "replace": replace_text,
        }

        if self._template.variables:
            entry["vars"] = [
                _build_espanso_var_entry(var) for var in self._template.variables
            ]

        try:
            preview = yaml.dump(
                {"matches": [entry]},
                default_flow_style=False,
                allow_unicode=True,
            )
        except Exception as e:
            preview = f"# Preview error: {e}"

        self._preview.setPlainText(preview)

    def _save(self) -> None:
        """Persist the new trigger to the template JSON file."""
        new_trigger = self._trigger_edit.text().strip()
        manager = get_template_manager()
        self._template.trigger = new_trigger

        if manager.save(self._template):
            self.accept()
        else:
            QMessageBox.warning(
                self, "Save Failed", "Could not save template to disk."
            )

    def get_trigger(self) -> str:
        """Return the current trigger string (after dialog closes)."""
        return self._trigger_edit.text().strip()
