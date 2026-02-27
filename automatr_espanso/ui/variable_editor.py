"""Inline variable editor widget for automatr-espanso.

Provides a "Variables" section with add/edit/delete rows for template variables.
Each row has name, type (form/date), default value, and type-specific fields.
"""

import re
from typing import List, Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from automatr_espanso.core.config import get_config
from automatr_espanso.core.templates import Variable

_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class VariableRowWidget(QWidget):
    """A single variable row with name, type, default, and type-specific fields.

    Signals:
        changed: Emitted when any field in the row changes.
        delete_requested: Emitted when the delete button is clicked.
    """

    changed = pyqtSignal()
    delete_requested = pyqtSignal(object)

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the variable row."""
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Build row layout: name, type combo, default, type-specific, delete."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        # Main row
        main_row = QHBoxLayout()

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("variable_name")
        self._name_edit.setMaximumWidth(150)
        main_row.addWidget(self._name_edit)

        self._type_combo = QComboBox()
        self._type_combo.addItems(["form", "date"])
        self._type_combo.setMaximumWidth(80)
        main_row.addWidget(self._type_combo)

        self._default_edit = QLineEdit()
        self._default_edit.setPlaceholderText("default value")
        main_row.addWidget(self._default_edit)

        # Form-specific: multiline checkbox
        self._multiline_cb = QCheckBox("Multiline")
        main_row.addWidget(self._multiline_cb)

        # Date-specific: format field
        self._format_edit = QLineEdit()
        self._format_edit.setPlaceholderText("%Y-%m-%d")
        self._format_edit.setMaximumWidth(120)
        main_row.addWidget(self._format_edit)

        # Delete button
        delete_btn = QPushButton("×")
        delete_btn.setObjectName("danger")
        delete_btn.setMaximumWidth(30)
        delete_btn.setToolTip("Remove variable")
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(self))
        main_row.addWidget(delete_btn)

        layout.addLayout(main_row)

        # Error label (hidden by default)
        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #f14c4c; font-size: 11px;")
        self._error_label.setVisible(False)
        layout.addWidget(self._error_label)

        # Set initial visibility
        self._update_type_fields()

    def _connect_signals(self) -> None:
        """Wire field changes to the changed signal."""
        self._name_edit.textChanged.connect(self._on_changed)
        self._type_combo.currentTextChanged.connect(self._on_type_changed)
        self._default_edit.textChanged.connect(self._on_changed)
        self._multiline_cb.stateChanged.connect(self._on_changed)
        self._format_edit.textChanged.connect(self._on_changed)

    def _on_changed(self) -> None:
        """Emit changed and clear error on any edit."""
        self._error_label.setText("")
        self._error_label.setVisible(False)
        self.changed.emit()

    def _on_type_changed(self, _text: str) -> None:
        """Update visibility of type-specific fields."""
        self._update_type_fields()
        self.changed.emit()

    def _update_type_fields(self) -> None:
        """Show/hide fields based on selected variable type."""
        is_form = self._type_combo.currentText() == "form"
        self._multiline_cb.setVisible(is_form)
        self._format_edit.setVisible(not is_form)

    # ── Public API ──────────────────────────────────────────────────────────

    def is_valid(self) -> bool:
        """Check if the variable name is valid (non-empty, alphanumeric + underscore)."""
        name = self._name_edit.text().strip()
        if not name:
            return False
        return bool(_NAME_RE.match(name))

    def validate(self) -> str:
        """Validate the row and show inline error if invalid.

        Returns:
            Error message string, or empty string if valid.
        """
        name = self._name_edit.text().strip()
        if not name:
            msg = "Variable name is required"
            self._error_label.setText(msg)
            self._error_label.setVisible(True)
            return msg
        if not _NAME_RE.match(name):
            msg = "Name must be alphanumeric and underscores only (start with letter or _)"
            self._error_label.setText(msg)
            self._error_label.setVisible(True)
            return msg
        self._error_label.setText("")
        self._error_label.setVisible(False)
        return ""

    def to_variable(self) -> Variable:
        """Convert the row's UI state to a Variable object."""
        name = self._name_edit.text().strip()
        var_type = self._type_combo.currentText()
        default = self._default_edit.text().strip()

        params = {}
        if var_type == "date":
            fmt = self._format_edit.text().strip()
            if fmt:
                params["format"] = fmt

        return Variable(
            name=name,
            default=default,
            multiline=self._multiline_cb.isChecked() if var_type == "form" else False,
            type=var_type,
            params=params,
        )

    def load_variable(self, var: Variable) -> None:
        """Populate the row fields from a Variable object."""
        self._name_edit.setText(var.name)
        self._type_combo.setCurrentText(var.type)
        self._default_edit.setText(var.default)

        if var.type == "form":
            self._multiline_cb.setChecked(var.multiline)
        elif var.type == "date" and "format" in var.params:
            self._format_edit.setText(var.params["format"])


class VariableEditorWidget(QWidget):
    """Variables section with add/edit/delete rows.

    Signals:
        variables_changed: Emitted when any variable is added, removed, or edited.
    """

    variables_changed = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the variable editor."""
        super().__init__(parent)
        self._rows: List[VariableRowWidget] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build layout: header, variable rows container, add button."""
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 5, 0, 0)

        # Header row
        header_row = QHBoxLayout()
        header = QLabel("Variables")
        header.setStyleSheet("font-weight: bold;")
        header_row.addWidget(header)
        header_row.addStretch()

        add_btn = QPushButton("+ Add Variable")
        add_btn.setObjectName("secondary")
        add_btn.clicked.connect(self._add_variable)
        header_row.addWidget(add_btn)
        self._layout.addLayout(header_row)

        # Container for variable rows
        self._rows_layout = QVBoxLayout()
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addLayout(self._rows_layout)

    # ── Public API ──────────────────────────────────────────────────────────

    def row_count(self) -> int:
        """Return the number of variable rows."""
        return len(self._rows)

    def get_row(self, index: int) -> Optional[VariableRowWidget]:
        """Return the row widget at the given index, or None."""
        if 0 <= index < len(self._rows):
            return self._rows[index]
        return None

    def get_variables(self) -> List[Variable]:
        """Return Variable objects for all rows."""
        return [row.to_variable() for row in self._rows]

    def load_variables(self, variables: List[Variable]) -> None:
        """Clear existing rows and populate from a list of Variables."""
        self.clear()
        for var in variables:
            row = self._create_row()
            row.load_variable(var)

    def clear(self) -> None:
        """Remove all variable rows."""
        for row in list(self._rows):
            self._remove_row(row)

    def validate(self) -> List[str]:
        """Validate all rows: individual + duplicate name check.

        Returns:
            List of error messages; empty if all valid.
        """
        errors = []
        names_seen: dict[str, int] = {}

        for i, row in enumerate(self._rows):
            err = row.validate()
            if err:
                errors.append(f"Variable {i + 1}: {err}")

            name = row._name_edit.text().strip().lower()
            if name:
                if name in names_seen:
                    dup_msg = f"Duplicate variable name '{name}'"
                    errors.append(dup_msg)
                    row._error_label.setText("Duplicate name")
                    row._error_label.setVisible(True)
                else:
                    names_seen[name] = i

        return errors

    def delete_row(self, index: int) -> None:
        """Delete the row at the given index."""
        if 0 <= index < len(self._rows):
            self._remove_row(self._rows[index])

    # ── Internal ────────────────────────────────────────────────────────────

    def _add_variable(self) -> None:
        """Add a new empty variable row."""
        self._create_row()
        self.variables_changed.emit()

    def _create_row(self) -> VariableRowWidget:
        """Create a new row widget and add it to the layout."""
        row = VariableRowWidget()
        row.changed.connect(self.variables_changed.emit)
        row.delete_requested.connect(self._on_delete_requested)
        self._rows.append(row)
        self._rows_layout.addWidget(row)
        return row

    def _on_delete_requested(self, row: VariableRowWidget) -> None:
        """Handle delete button click on a row."""
        self._remove_row(row)
        self.variables_changed.emit()

    def _remove_row(self, row: VariableRowWidget) -> None:
        """Remove a row widget from the layout and list."""
        if row in self._rows:
            self._rows.remove(row)
            self._rows_layout.removeWidget(row)
            row.deleteLater()
