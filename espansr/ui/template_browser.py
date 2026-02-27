"""Template browser widget for espansr.

Left-panel template list with search, new, and delete controls.
Templates organized by folder; search filters by name, trigger, or description.
"""

from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from espansr.core.config import get_config
from espansr.core.templates import Template, get_template_manager


class TemplateBrowserWidget(QWidget):
    """Widget for browsing and managing Espanso templates.

    Emits:
        template_selected(Template): Fired when a template is clicked.
        new_template_requested(): Fired when "New" is clicked.
        status_message(str, int): Fired with a message and duration (ms).
    """

    template_selected = pyqtSignal(object)
    new_template_requested = pyqtSignal()
    status_message = pyqtSignal(str, int)

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the template browser."""
        super().__init__(parent)
        self._current_template: Optional[Template] = None
        self._all_templates: list[Template] = []
        self._pending_delete: Optional[Template] = None
        self._delete_timer: Optional[QTimer] = None
        self._setup_ui()
        self.load_templates()

    def _setup_ui(self) -> None:
        """Build the layout: header with buttons, search, tree."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 5, 10)

        # Header row
        config = get_config()
        label_size = config.ui.font_size + 1
        header_layout = QHBoxLayout()
        label = QLabel("Templates")
        label.setStyleSheet(f"font-weight: bold; font-size: {label_size}pt;")
        header_layout.addWidget(label)
        header_layout.addStretch()

        new_btn = QPushButton("New")
        new_btn.setObjectName("secondary")
        new_btn.setToolTip("Create a new template")
        new_btn.clicked.connect(self.new_template_requested.emit)
        header_layout.addWidget(new_btn)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setObjectName("danger")
        self._delete_btn.setToolTip("Delete selected template")
        self._delete_btn.clicked.connect(self._start_delete)
        header_layout.addWidget(self._delete_btn)

        layout.addLayout(header_layout)

        # Undo row (hidden by default)
        self._undo_row = QWidget()
        undo_layout = QHBoxLayout(self._undo_row)
        undo_layout.setContentsMargins(0, 0, 0, 0)
        self._undo_label = QLabel()
        undo_layout.addWidget(self._undo_label)
        undo_btn = QPushButton("Undo")
        undo_btn.setObjectName("secondary")
        undo_btn.clicked.connect(self._cancel_delete)
        undo_layout.addWidget(undo_btn)
        undo_layout.addStretch()
        self._undo_row.setVisible(False)
        layout.addWidget(self._undo_row)

        # Search bar
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search by name, trigger, or description…")
        self._search.textChanged.connect(self._filter_templates)
        layout.addWidget(self._search)

        # Tree (single column — trigger is shown in the editor)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Template"])
        self.tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.tree)

    # ── Public API ──────────────────────────────────────────────────────────

    def load_templates(self) -> None:
        """Reload templates from disk and repopulate the tree."""
        manager = get_template_manager()
        self._all_templates = manager.list_all()
        self._populate_tree(self._all_templates)
        self.status_message.emit(f"Loaded {len(self._all_templates)} templates", 3000)

    def refresh(self) -> None:
        """Alias for load_templates."""
        self.load_templates()

    def get_current_template(self) -> Optional[Template]:
        """Return the currently selected template, or None."""
        return self._current_template

    def select_template_by_name(self, name: str) -> None:
        """Programmatically select a template in the tree by name."""

        def _find(item: QTreeWidgetItem) -> bool:
            t = item.data(0, Qt.ItemDataRole.UserRole)
            if t is not None and t.name == name:
                self.tree.setCurrentItem(item)
                self._on_item_clicked(item, 0)
                return True
            for i in range(item.childCount()):
                if _find(item.child(i)):
                    return True
            return False

        for i in range(self.tree.topLevelItemCount()):
            if _find(self.tree.topLevelItem(i)):
                break

    # ── Delete with inline undo ─────────────────────────────────────────────

    def _start_delete(self) -> None:
        """Begin a timed delete — show undo row for 5 seconds."""
        if self._current_template is None:
            return
        self._pending_delete = self._current_template
        self._undo_label.setText(f"Deleted '{self._pending_delete.name}'.")
        self._delete_btn.setVisible(False)
        self._undo_row.setVisible(True)

        self._delete_timer = QTimer()
        self._delete_timer.setSingleShot(True)
        self._delete_timer.timeout.connect(self._finalize_delete)
        self._delete_timer.start(5000)

    def _cancel_delete(self) -> None:
        """Cancel a pending delete."""
        if self._delete_timer is not None:
            self._delete_timer.stop()
            self._delete_timer = None
        self._pending_delete = None
        self._undo_row.setVisible(False)
        self._delete_btn.setVisible(True)

    def _finalize_delete(self) -> None:
        """Execute the pending delete after timeout."""
        template = self._pending_delete
        self._pending_delete = None
        self._delete_timer = None
        self._undo_row.setVisible(False)
        self._delete_btn.setVisible(True)

        if template is None:
            return

        manager = get_template_manager()
        if manager.delete(template):
            self._current_template = None
            self.load_templates()
            self.status_message.emit(f"Deleted '{template.name}'", 3000)
        else:
            self.status_message.emit(f"Failed to delete '{template.name}'", 5000)

    # ── Internal helpers ────────────────────────────────────────────────────

    def _populate_tree(self, templates: list[Template]) -> None:
        """Populate tree from a list of templates."""
        self.tree.clear()
        manager = get_template_manager()

        templates_by_folder: dict[str, list[Template]] = {"": []}
        for folder in manager.list_folders():
            templates_by_folder[folder] = []

        for template in templates:
            folder = manager.get_template_folder(template)
            templates_by_folder.setdefault(folder, [])
            templates_by_folder[folder].append(template)

        def _make_item(t: Template) -> QTreeWidgetItem:
            item = QTreeWidgetItem([t.name])
            item.setData(0, Qt.ItemDataRole.UserRole, t)
            if t.description:
                item.setToolTip(0, t.description)
            return item

        # Root-level templates
        for template in sorted(
            templates_by_folder.get("", []), key=lambda t: t.name.lower()
        ):
            self.tree.addTopLevelItem(_make_item(template))

        # Folders
        for folder in sorted(k for k in templates_by_folder if k):
            folder_item = QTreeWidgetItem([folder])
            folder_item.setData(0, Qt.ItemDataRole.UserRole, None)
            folder_item.setExpanded(True)
            for template in sorted(
                templates_by_folder[folder], key=lambda t: t.name.lower()
            ):
                folder_item.addChild(_make_item(template))
            self.tree.addTopLevelItem(folder_item)

    def _filter_templates(self, text: str) -> None:
        """Filter tree to templates matching the search text."""
        query = text.strip().lower()
        if not query:
            self._populate_tree(self._all_templates)
            return

        filtered = [
            t
            for t in self._all_templates
            if query in t.name.lower()
            or query in (t.trigger or "").lower()
            or query in (t.description or "").lower()
        ]
        self._populate_tree(filtered)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle click on a tree item — emit signal."""
        template: Optional[Template] = item.data(0, Qt.ItemDataRole.UserRole)
        if template is None:
            return
        self._current_template = template
        self.template_selected.emit(template)
