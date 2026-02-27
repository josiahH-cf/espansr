"""Inline template editor widget for automatr-espanso.

Right-panel editor with name, trigger, and content fields.
Saves new or existing templates via TemplateManager.
"""

from typing import Optional

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

from automatr_espanso.core.config import get_config
from automatr_espanso.core.templates import Template, get_template_manager


class TemplateEditorWidget(QWidget):
    """Inline editor for template name, trigger, and content.

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

    def _setup_ui(self) -> None:
        """Build the editor layout: name, trigger, content, save button."""
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
        hint.setStyleSheet("color: #808080; font-style: italic;")
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

        # Save button
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)

    # ── Public API ──────────────────────────────────────────────────────────

    def load_template(self, template: Template) -> None:
        """Populate editor fields from a Template object."""
        self._current_template = template
        self._name_edit.setText(template.name)
        self._trigger_edit.setText(template.trigger)
        self._content_edit.setPlainText(template.content)

    def clear(self) -> None:
        """Clear all fields for creating a new template."""
        self._current_template = None
        self._name_edit.clear()
        self._trigger_edit.clear()
        self._content_edit.clear()

    # ── Internal ────────────────────────────────────────────────────────────

    def _save(self) -> None:
        """Save the current editor state as a new or existing template."""
        name = self._name_edit.text().strip()
        if not name:
            self.status_message.emit("Template name is required", 3000)
            return

        trigger = self._trigger_edit.text().strip()
        content = self._content_edit.toPlainText()
        manager = get_template_manager()

        try:
            if self._current_template is None:
                template = manager.create(
                    name=name, content=content, trigger=trigger,
                )
                self._current_template = template
                self.status_message.emit(f"Created '{name}'", 3000)
            else:
                self._current_template.name = name
                self._current_template.trigger = trigger
                self._current_template.content = content
                manager.save(self._current_template)
                self.status_message.emit(f"Saved '{name}'", 3000)
            self.template_saved.emit(self._current_template)
        except Exception as exc:
            self.status_message.emit(f"Save failed: {exc}", 5000)
