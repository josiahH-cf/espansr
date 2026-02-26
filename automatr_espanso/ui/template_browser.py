"""Template browser widget for automatr-espanso.

Shows templates organized by folder with trigger info prominently displayed:
- Trigger column shown alongside template name
- Preview pane shows content + trigger
- Search filters by name, trigger, or description
"""

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from automatr_espanso.core.config import get_config
from automatr_espanso.core.templates import Template, get_template_manager


class TemplateBrowserWidget(QWidget):
    """Widget for browsing Espanso templates with trigger info.

    Emits:
        template_selected(Template): Fired when a template is clicked.
        status_message(str, int): Fired with a message and duration (ms).
    """

    template_selected = pyqtSignal(object)
    status_message = pyqtSignal(str, int)

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the template browser."""
        super().__init__(parent)
        self._current_template: Optional[Template] = None
        self._all_templates: list[Template] = []
        self._setup_ui()
        self.load_templates()

    def _setup_ui(self) -> None:
        """Build the layout: header, search, tree, preview."""
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

        refresh_btn = QPushButton("↺")
        refresh_btn.setObjectName("secondary")
        refresh_btn.setMaximumWidth(30)
        refresh_btn.setToolTip("Refresh template list")
        refresh_btn.clicked.connect(self.load_templates)
        header_layout.addWidget(refresh_btn)
        layout.addLayout(header_layout)

        # Search bar
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search by name, trigger, or description…")
        self._search.textChanged.connect(self._filter_templates)
        layout.addWidget(self._search)

        # Tree with trigger + name columns
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Trigger", "Template Name"])
        self.tree.setColumnWidth(0, 130)
        self.tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.tree)

        # Preview section
        preview_label = QLabel("Content preview:")
        preview_label.setStyleSheet("font-weight: bold; margin-top: 4px;")
        layout.addWidget(preview_label)

        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setMaximumHeight(130)
        self._preview.setPlaceholderText("Select a template to preview…")
        layout.addWidget(self._preview)

        # Trigger display row
        trigger_row = QHBoxLayout()
        trigger_row.addWidget(QLabel("Trigger:"))
        self._trigger_label = QLabel("—")
        self._trigger_label.setStyleSheet(
            "font-family: monospace; font-weight: bold; color: #4fc1ff;"
        )
        trigger_row.addWidget(self._trigger_label)
        trigger_row.addStretch()

        self._no_trigger_hint = QLabel("(no trigger — set one to sync)")
        self._no_trigger_hint.setStyleSheet("color: #808080; font-style: italic;")
        self._no_trigger_hint.setVisible(False)
        trigger_row.addWidget(self._no_trigger_hint)
        layout.addLayout(trigger_row)

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
            item = QTreeWidgetItem([t.trigger or "—", t.name])
            item.setData(0, Qt.ItemDataRole.UserRole, t)
            if not t.trigger:
                # Dim templates without triggers
                for col in range(2):
                    item.setForeground(col, item.foreground(col))
            if t.description:
                item.setToolTip(1, t.description)
            return item

        # Root-level templates
        for template in sorted(
            templates_by_folder.get("", []), key=lambda t: t.name.lower()
        ):
            self.tree.addTopLevelItem(_make_item(template))

        # Folders
        for folder in sorted(k for k in templates_by_folder if k):
            folder_item = QTreeWidgetItem(["📁", folder])
            folder_item.setData(0, Qt.ItemDataRole.UserRole, None)
            folder_item.setExpanded(True)
            for template in sorted(
                templates_by_folder[folder], key=lambda t: t.name.lower()
            ):
                folder_item.addChild(_make_item(template))
            self.tree.addTopLevelItem(folder_item)

        self.tree.resizeColumnToContents(0)

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
        """Handle click on a tree item — update preview and emit signal."""
        template: Optional[Template] = item.data(0, Qt.ItemDataRole.UserRole)
        if template is None:
            # Folder click
            return

        self._current_template = template
        self._preview.setPlainText(template.content)
        self._trigger_label.setText(template.trigger or "—")
        self._no_trigger_hint.setVisible(not bool(template.trigger))
        self.template_selected.emit(template)
