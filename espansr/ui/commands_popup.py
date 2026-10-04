"""Local command reference: browse intentions, compare jobs, and see combinations.

Groups overlap and relationships stay optional. Discovery only displays or
copies material; the existing explicit editor and packet actions are retained.
Only window preferences, favorites, and recents are saved, never scratchpad text.
"""

import html
import sys
from typing import Optional
from urllib.parse import quote, unquote

from PyQt6.QtCore import QByteArray, QEvent, QRect, QSize, Qt
from PyQt6.QtGui import QFont, QFontDatabase, QFontMetrics, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from espansr.core.capabilities import ARTIFACT_TYPES
from espansr.core.command_catalog import CommandCatalogEntry, build_command_catalog
from espansr.core.command_groups import COMMAND_GROUPS, CUSTOM_GROUP, command_cue, groups_for
from espansr.core.config import get_config, load_config_fresh, save_config
from espansr.core.recommend import RecommendationQuery, recommend
from espansr.ui.theme import get_theme_stylesheet
from espansr.ui.window_layout import capture_panel_sizes, panel_sizes, prepare_splitter

_VIEWS = ("Browse", "All Commands", "Recommended", "Processes", "Recent", "Favorites")


class CommandRowWidget(QFrame):
    """Standardized row widget for the commands popup."""

    PREVIEW_HEIGHT = 88

    def __init__(
        self,
        entry: CommandCatalogEntry,
        parent: Optional[QWidget] = None,
        actions: Optional[dict] = None,
        related_html: str = "",
        font_size: Optional[int] = None,
    ):
        """Build the visual layout for one command entry."""
        super().__init__(parent)
        if font_size is not None:
            font = QFont(self.font())
            font.setPointSize(font_size)
            self.setFont(font)
        self._entry = entry
        self._actions = actions or {}
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName("commandRow")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(12)

        self._trigger_label = QLabel(entry.trigger)
        fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        fixed_font.setPointSize(self.font().pointSize())
        fixed_font.setBold(True)
        self._trigger_label.setFont(fixed_font)
        self._trigger_label.setMargin(6)
        self._trigger_label.setFrameShape(QFrame.Shape.Box)
        header.addWidget(self._trigger_label, 0)

        self._name_label = QLabel(entry.name)
        name_font = QFont(self._name_label.font())
        name_font.setBold(True)
        self._name_label.setFont(name_font)
        self._name_label.setWordWrap(True)
        header.addWidget(self._name_label, 1)

        monitor = self._actions.get("usage_monitor")
        if monitor is not None:
            from espansr.core.usage import command_key
            from espansr.ui.usage_labels import UsageLabel

            self._usage_label = UsageLabel(monitor, command_key(entry), self)
            header.addWidget(self._usage_label)

        self._workflow_label = QLabel(entry.workflow_label)
        self._workflow_label.setMargin(4)
        self._workflow_label.setFrameShape(QFrame.Shape.Box)
        layout.addLayout(header)
        layout.addLayout(self._build_action_row(entry))

        self._description_label = QLabel(entry.description)
        self._description_label.setWordWrap(True)
        layout.addWidget(self._description_label)

        role, cue = command_cue(entry)
        self._cue_label = QLabel(f"{role}: {cue}")
        self._cue_label.setWordWrap(True)
        layout.addWidget(self._cue_label)

        self._related_label = QLabel(related_html)
        self._related_label.setTextFormat(Qt.TextFormat.RichText)
        self._related_label.setWordWrap(True)
        self._related_label.setOpenExternalLinks(False)
        self._related_label.setVisible(bool(related_html))
        if self._actions.get("show_link"):
            self._related_label.linkActivated.connect(self._actions["show_link"])
        layout.addWidget(self._related_label)

        self._workflow_label.setWordWrap(True)
        layout.addWidget(self._workflow_label)

        self._next_label = QLabel(entry.next_label)
        self._next_label.setWordWrap(True)
        self._next_label.setVisible(bool(entry.next_label))
        layout.addWidget(self._next_label)

        self._use_when_label = QLabel(f"Use when: {entry.use_when}" if entry.use_when else "")
        self._use_when_label.setWordWrap(True)
        self._use_when_label.setVisible(bool(entry.use_when))
        layout.addWidget(self._use_when_label)

        self._avoid_when_label = QLabel(
            f"Avoid when: {entry.avoid_when}" if entry.avoid_when else ""
        )
        self._avoid_when_label.setWordWrap(True)
        self._avoid_when_label.setVisible(bool(entry.avoid_when))
        layout.addWidget(self._avoid_when_label)

        self._process_label = QLabel(self._build_process_text(entry))
        self._process_label.setWordWrap(True)
        self._process_label.setVisible(bool(self._process_label.text()) and not related_html)
        layout.addWidget(self._process_label)

        preview_title = QLabel("Output Preview")
        preview_font = QFont(preview_title.font())
        preview_font.setBold(True)
        preview_title.setFont(preview_font)
        layout.addWidget(preview_title)

        self._preview_text = QPlainTextEdit()
        self._preview_text.setReadOnly(True)
        self._preview_text.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._preview_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._preview_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._preview_text.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._preview_text.setPlainText(entry.preview)
        self._preview_text.setFixedHeight(self.PREVIEW_HEIGHT)
        layout.addWidget(self._preview_text)

        for label in (
            self._trigger_label,
            self._name_label,
            self._workflow_label,
            self._description_label,
            self._cue_label,
            self._next_label,
            self._use_when_label,
            self._avoid_when_label,
            self._process_label,
        ):
            label.setTextFormat(Qt.TextFormat.PlainText)

    @staticmethod
    def _build_process_text(entry: CommandCatalogEntry) -> str:
        """Compact workflow membership plus derived neighbor hints."""
        parts = []
        if entry.workflows:
            parts.append("Process: " + ", ".join(entry.workflows))
        if entry.workflow_next:
            neighbors = ", ".join(
                f"{trigger} ({label})" if label else trigger
                for trigger, label in entry.workflow_next[:4]
            )
            parts.append(f"Optional next: {neighbors}")
        return "  ·  ".join(parts)

    def _build_action_row(self, entry: CommandCatalogEntry) -> QGridLayout:
        """Direct actions: copy, scratchpad, packet, editor, favorite."""
        row = QGridLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        def _run(name: str, fallback=None):
            def _handler():
                action = self._actions.get(name)
                if action is not None:
                    action(self._entry)
                elif fallback is not None:
                    fallback()

            return _handler

        def _copy_trigger_fallback():
            clipboard = QApplication.clipboard()
            if clipboard is not None:
                clipboard.setText(self._entry.trigger)

        def _copy_prompt_fallback():
            clipboard = QApplication.clipboard()
            if clipboard is not None and self._entry.content:
                clipboard.setText(self._entry.content)

        self._copy_trigger_btn = QPushButton("Copy trigger")
        self._copy_trigger_btn.clicked.connect(_run("copy_trigger", _copy_trigger_fallback))
        row.addWidget(self._copy_trigger_btn, 0, 0)

        self._copy_prompt_btn = QPushButton("Copy prompt")
        self._copy_prompt_btn.setVisible(bool(entry.content))
        self._copy_prompt_btn.clicked.connect(_run("copy_prompt", _copy_prompt_fallback))
        row.addWidget(self._copy_prompt_btn, 0, 1)

        self._scratchpad_btn = QPushButton("Prompt to scratchpad")
        self._scratchpad_btn.clicked.connect(_run("scratchpad"))
        row.addWidget(self._scratchpad_btn, 0, 2)

        self._packet_btn = QPushButton("Packet…")
        self._packet_btn.clicked.connect(_run("packet"))
        row.addWidget(self._packet_btn, 1, 0)

        self._edit_btn = QPushButton("Edit…")
        self._edit_btn.setVisible(entry.source == "template")
        self._edit_btn.clicked.connect(_run("edit"))
        row.addWidget(self._edit_btn, 1, 1)

        self._favorite_btn = QPushButton("☆")
        self._favorite_btn.setCheckable(True)
        self._favorite_btn.setChecked(bool(self._actions.get("is_favorite")))
        if self._favorite_btn.isChecked():
            self._favorite_btn.setText("★")
        self._favorite_btn.setFixedWidth(34)
        self._favorite_btn.setStyleSheet("QPushButton { min-width: 0; padding: 4px; }")
        self._favorite_btn.setAccessibleName("Favorite command")
        self._favorite_btn.setToolTip("Add or remove this command from Favorites")
        self._favorite_btn.toggled.connect(self._on_favorite_toggled)
        row.addWidget(self._favorite_btn, 1, 2, alignment=Qt.AlignmentFlag.AlignLeft)

        for button in (
            self._copy_trigger_btn,
            self._copy_prompt_btn,
            self._scratchpad_btn,
            self._packet_btn,
            self._edit_btn,
            self._favorite_btn,
        ):
            button.setAutoDefault(False)
        return row

    def _on_favorite_toggled(self, checked: bool) -> None:
        self._favorite_btn.setText("★" if checked else "☆")
        action = self._actions.get("favorite")
        if action is not None:
            action(self._entry)


class WorkflowRowWidget(QFrame):
    """Read-only card describing one optional workflow (Processes view)."""

    def __init__(self, workflow, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName("commandRow")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self._name_label = QLabel(f"{workflow.name}  ({workflow.id})")
        name_font = QFont(self._name_label.font())
        name_font.setBold(True)
        self._name_label.setFont(name_font)
        layout.addWidget(self._name_label)

        if workflow.description:
            description = QLabel(workflow.description)
            description.setWordWrap(True)
            layout.addWidget(description)

        entries = QLabel(
            "Entry points (every capability stays directly invocable): "
            + ", ".join(workflow.entry_points)
        )
        entries.setWordWrap(True)
        layout.addWidget(entries)

        edge_lines = "\n".join(
            f"{edge.source} → {edge.target}" + (f": {edge.label}" if edge.label else "")
            for edge in workflow.edges
        )
        edges_text = QPlainTextEdit()
        edges_text.setReadOnly(True)
        edges_text.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        edges_text.setPlainText(edge_lines)
        edges_text.setFixedHeight(min(200, 24 + 18 * max(1, len(workflow.edges))))
        layout.addWidget(edges_text)

        note = QLabel("No relationship is required and no arrow runs another command.")
        note.setWordWrap(True)
        layout.addWidget(note)


class CommandsPopupDialog(QDialog):
    """Reference window with overlapping browse groups and ephemeral scratchpad."""

    def __init__(
        self,
        entries: Optional[list[CommandCatalogEntry]] = None,
        parent: Optional[QWidget] = None,
        workflow_catalog=None,
    ):
        super().__init__(parent)
        self._config = get_config()
        self._workflow_catalog = (
            workflow_catalog if workflow_catalog is not None else self._load_workflows()
        )
        self._entries = (
            entries
            if entries is not None
            else build_command_catalog(workflow_catalog=self._workflow_catalog)
        )
        from espansr.ui.usage_labels import UsageMonitor

        self._usage_monitor = UsageMonitor(lambda: self._entries, self)
        self._group_id = ""
        self._shown_entries: list[CommandCatalogEntry] = []
        self._selected_entry: Optional[CommandCatalogEntry] = None
        self._detail_widget: Optional[CommandRowWidget] = None
        self._workflow_panel = None

        self.setWindowTitle("Command Reference")
        self.setModal(False)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinMaxButtonsHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self._config.discovery.stay_on_top)
        self.resize(1040, 820)
        self.setStyleSheet(
            get_theme_stylesheet(theme=self._config.ui.theme, font_size=self._config.ui.font_size)
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        title_row = QHBoxLayout()
        self._title_label = QLabel("Command Reference")
        title_font = QFont(self._title_label.font())
        title_font.setPointSize(title_font.pointSize() + 4)
        title_font.setBold(True)
        self._title_label.setFont(title_font)
        title_row.addWidget(self._title_label, 1)
        self._refresh_btn = QPushButton("Refresh catalog")
        self._refresh_btn.setAutoDefault(False)
        self._refresh_btn.clicked.connect(self._refresh_catalog)
        title_row.addWidget(self._refresh_btn)
        self._pin_check = QCheckBox("Stay on top")
        self._pin_check.setChecked(self._config.discovery.stay_on_top)
        self._pin_check.toggled.connect(self._set_stay_on_top)
        title_row.addWidget(self._pin_check)
        layout.addLayout(title_row)
        self._hint_label = QLabel(
            "Browse what you want to accomplish, or search. Ctrl+F to search; Esc to close."
        )
        self._hint_label.setWordWrap(True)
        layout.addWidget(self._hint_label)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Describe the job — e.g. resume work or carry context")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.textChanged.connect(self._refresh_view)
        self._search_edit.returnPressed.connect(self._focus_commands)
        layout.addWidget(self._search_edit)
        view_row = QHBoxLayout()
        view_row.addWidget(QLabel("View:"))
        self._view_combo = QComboBox()
        self._view_combo.addItems(list(_VIEWS))
        self._view_combo.currentTextChanged.connect(self._view_changed)
        view_row.addWidget(self._view_combo)
        self._all_btn = QPushButton("Show all commands")
        self._all_btn.setAutoDefault(False)
        self._all_btn.clicked.connect(self._show_all)
        view_row.addWidget(self._all_btn)
        view_row.addStretch()
        self._artifact_toggle = QToolButton()
        self._artifact_toggle.setText("Filter by artifacts")
        self._artifact_toggle.setCheckable(True)
        view_row.addWidget(self._artifact_toggle)
        layout.addLayout(view_row)
        self._artifact_controls = QWidget()
        selector_row = QHBoxLayout(self._artifact_controls)
        selector_row.setContentsMargins(0, 0, 0, 0)
        selector_row.addWidget(QLabel("I currently have:"))
        self._have_combo = QComboBox()
        self._have_combo.setEditable(True)
        self._have_combo.addItems(["", *ARTIFACT_TYPES])
        self._have_combo.currentTextChanged.connect(self._refresh_view)
        selector_row.addWidget(self._have_combo, 1)
        selector_row.addWidget(QLabel("I need to produce:"))
        self._want_combo = QComboBox()
        self._want_combo.setEditable(True)
        self._want_combo.addItems(["", *ARTIFACT_TYPES])
        self._want_combo.currentTextChanged.connect(self._refresh_view)
        selector_row.addWidget(self._want_combo, 1)
        self._artifact_controls.hide()
        self._artifact_toggle.toggled.connect(self._artifact_controls.setVisible)
        layout.addWidget(self._artifact_controls)

        self._body = QSplitter(Qt.Orientation.Horizontal)
        self._groups = QListWidget()
        self._groups.setAccessibleName("Browse command groups")
        self._groups.setWordWrap(True)
        self._groups.setResizeMode(QListView.ResizeMode.Adjust)
        self._groups.setTextElideMode(Qt.TextElideMode.ElideNone)
        self._groups.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._groups.setMinimumWidth(180)
        self._groups.viewport().installEventFilter(self)
        self._groups.installEventFilter(self)
        self._groups.currentItemChanged.connect(self._group_changed)
        self._body.addWidget(self._groups)
        self._pages = QStackedWidget()
        self._body.addWidget(self._pages)
        self._body.setStretchFactor(1, 1)
        self._body.setSizes([230, 810])
        self._reference_splitter = QSplitter(Qt.Orientation.Vertical)
        self._reference_splitter.addWidget(self._body)
        layout.addWidget(self._reference_splitter, 1)

        self._command_page = QWidget()
        command_layout = QVBoxLayout(self._command_page)
        command_layout.setContentsMargins(8, 0, 0, 0)
        self._summary_label = QLabel("All commands")
        label_font = QFont(self._summary_label.font())
        label_font.setBold(True)
        self._summary_label.setFont(label_font)
        command_layout.addWidget(self._summary_label)
        self._group_description = QLabel()
        self._group_description.setWordWrap(True)
        command_layout.addWidget(self._group_description)
        self._empty_label = QLabel("No commands match these filters.")
        self._empty_label.setWordWrap(True)
        command_layout.addWidget(self._empty_label)
        self._search_everywhere_btn = QPushButton("Search all commands")
        self._search_everywhere_btn.setAutoDefault(False)
        self._search_everywhere_btn.clicked.connect(self._search_everywhere)
        command_layout.addWidget(self._search_everywhere_btn)
        self._command_splitter = QSplitter(Qt.Orientation.Vertical)
        self._summary_table = self._make_table(["Command", "Choose it when", "Role"])
        table_font = QFont(self._summary_table.font())
        table_font.setPointSize(self._config.ui.font_size)
        self._summary_table.setFont(table_font)
        self._summary_table.setMinimumHeight(100)
        self._summary_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._summary_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._summary_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self._summary_table.currentCellChanged.connect(self._command_selected)
        self._command_splitter.addWidget(self._summary_table)
        self._detail_pages = QStackedWidget()
        self._guide_browser = QTextBrowser()
        self._guide_browser.setAccessibleName("Group guidance and optional combinations")
        self._guide_browser.setOpenLinks(False)
        link_color = "#6cb6ff" if self._config.ui.theme != "light" else "#005a9e"
        self._link_color = link_color
        self._guide_browser.document().setDefaultStyleSheet(f"a {{ color: {link_color}; }}")
        self._guide_browser.anchorClicked.connect(lambda url: self._follow_link(url.toString()))
        self._detail_pages.addWidget(self._guide_browser)
        self._detail_scroll = QScrollArea()
        self._detail_scroll.setWidgetResizable(True)
        self._detail_pages.addWidget(self._detail_scroll)
        self._detail_pages.setMinimumHeight(100)
        self._command_splitter.addWidget(self._detail_pages)
        self._command_splitter.setSizes([300, 240])
        command_layout.addWidget(self._command_splitter, 1)
        self._pages.addWidget(self._command_page)

        self._process_page = QWidget()
        process_layout = QVBoxLayout(self._process_page)
        process_layout.setContentsMargins(8, 0, 0, 0)
        process_hint = QLabel(
            "Optional relationships. Select a command in the diagram to see its details."
        )
        process_hint.setWordWrap(True)
        process_layout.addWidget(process_hint)
        self._process_table = self._make_table(["Process", "Entry points", "Description"])
        self._process_table.setMinimumHeight(80)
        self._process_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self._process_table.currentCellChanged.connect(self._process_selected)
        self._process_splitter = QSplitter(Qt.Orientation.Vertical)
        self._process_splitter.addWidget(self._process_table)
        process_layout.addWidget(self._process_splitter, 1)
        self._pages.addWidget(self._process_page)

        # Only the reference window preferences are durable. This text is throwaway.
        self._scratchpad_container = QWidget()
        scratchpad_layout = QVBoxLayout(self._scratchpad_container)
        scratchpad_layout.setContentsMargins(0, 0, 0, 0)
        self._scratchpad_label = QLabel("Scratchpad")
        scratchpad_font = QFont(self._scratchpad_label.font())
        scratchpad_font.setBold(True)
        self._scratchpad_label.setFont(scratchpad_font)
        scratchpad_layout.addWidget(self._scratchpad_label)
        self._scratchpad_hint = QLabel(
            "Ephemeral — type or paste a command, add context, then copy it. Nothing here is saved."
        )
        self._scratchpad_hint.setWordWrap(True)
        scratchpad_layout.addWidget(self._scratchpad_hint)
        self._scratchpad = QPlainTextEdit()
        self._scratchpad.setObjectName("scratchpad")
        self._scratchpad.setPlaceholderText("Type or paste any command here…")
        self._scratchpad.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._scratchpad.setMinimumHeight(64)
        scratchpad_layout.addWidget(self._scratchpad, 1)
        self._scratchpad_packet_btn = QPushButton("Create packet from scratchpad…")
        self._scratchpad_packet_btn.setAutoDefault(False)
        self._scratchpad_packet_btn.clicked.connect(self._packet_from_scratchpad)
        scratchpad_layout.addWidget(self._scratchpad_packet_btn)
        self._reference_splitter.addWidget(self._scratchpad_container)
        self._layout_splitters = {
            "sidebar": self._body,
            "commands": self._command_splitter,
            "scratchpad": self._reference_splitter,
            "processes": self._process_splitter,
        }
        defaults = {
            "sidebar": [230, 810],
            "commands": [300, 240],
            "scratchpad": [540, 160],
            "processes": [150, 390],
        }
        for name, splitter in self._layout_splitters.items():
            prepare_splitter(
                splitter,
                name,
                panel_sizes(self._config.discovery.panel_sizes, name, defaults[name]),
            )
            splitter.splitterMoved.connect(self._save_layout)
        self._populate_groups()
        self._refresh_view()
        geometry = self._config.discovery.window_geometry
        if isinstance(geometry, str) and geometry:
            self.restoreGeometry(QByteArray.fromBase64(geometry.encode("ascii", errors="ignore")))

        self._shortcut_close = QShortcut(QKeySequence("Esc"), self)
        self._shortcut_close.activated.connect(self.reject)
        self._shortcut_search = QShortcut(QKeySequence("Ctrl+F"), self)
        self._shortcut_search.activated.connect(self._search_edit.setFocus)
        self._search_edit.setFocus()

    @staticmethod
    def _load_workflows():
        from espansr.core.workflows import load_workflow_catalog

        return load_workflow_catalog()

    def _make_table(self, headers: list[str]) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setWordWrap(True)
        table.setAlternatingRowColors(True)
        table.setCornerButtonEnabled(False)
        table.verticalHeader().setVisible(False)
        dark = self._config.ui.theme != "light"
        alternate = "#2d2d2d" if dark else "#f5f5f5"
        header = "#2d2d2d" if dark else "#eeeeee"
        foreground = "#d4d4d4" if dark else "#333333"
        selected = "#094771" if dark else "#cce8ff"
        selected_text = "#ffffff" if dark else "#111111"
        table.setStyleSheet(
            f"QTableWidget {{ alternate-background-color: {alternate}; "
            f"selection-background-color: {selected}; selection-color: {selected_text}; }} "
            f"QHeaderView::section {{ background-color: {header}; color: {foreground}; "
            "padding: 4px; border: 0; }"
        )
        return table

    def _populate_groups(self) -> None:
        selected = self._group_id
        self._groups.blockSignals(True)
        self._groups.clear()
        all_item = QListWidgetItem(f"All commands ({len(self._entries)})")
        all_item.setData(Qt.ItemDataRole.UserRole, "")
        self._groups.addItem(all_item)
        for group in (*COMMAND_GROUPS, CUSTOM_GROUP):
            count = sum(group in groups_for(entry) for entry in self._entries)
            if not count:
                continue
            item = QListWidgetItem(f"{group.title} ({count})")
            item.setToolTip(group.description)
            item.setData(Qt.ItemDataRole.UserRole, group.id)
            self._groups.addItem(item)
        row = next(
            (
                i
                for i in range(self._groups.count())
                if self._groups.item(i).data(Qt.ItemDataRole.UserRole) == selected
            ),
            0,
        )
        self._groups.setCurrentRow(row)
        self._group_id = self._groups.currentItem().data(Qt.ItemDataRole.UserRole)
        self._groups.blockSignals(False)
        self._resize_group_rows()

    def _resize_group_rows(self) -> None:
        # QListView's cached delegate height can elide wrapped labels after
        # the splitter narrows. Reserve their actual wrapped height instead.
        width = max(60, self._groups.viewport().width() - 24)
        metrics = QFontMetrics(self._groups.font())
        for row in range(self._groups.count()):
            item = self._groups.item(row)
            bounds = metrics.boundingRect(
                QRect(0, 0, width, 1000), int(Qt.TextFlag.TextWordWrap), item.text()
            )
            size = QSize(0, bounds.height() + 20)
            if item.sizeHint() != size:
                item.setSizeHint(size)

    def eventFilter(self, watched, event) -> bool:
        if (watched is self._groups.viewport() and event.type() == QEvent.Type.Resize) or (
            watched is self._groups
            and event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange)
        ):
            self._resize_group_rows()
        return super().eventFilter(watched, event)

    def _group_changed(self, item, _previous) -> None:
        self._group_id = item.data(Qt.ItemDataRole.UserRole) if item else ""
        if self._view_combo.currentText() in ("All Commands", "Processes"):
            self._view_combo.setCurrentText("Browse")
        else:
            self._refresh_view()

    def _view_changed(self, view: str) -> None:
        if view == "All Commands":
            self._groups.blockSignals(True)
            self._groups.setCurrentRow(0)
            self._group_id = ""
            self._groups.blockSignals(False)
        self._refresh_view()

    def _show_all(self) -> None:
        self._search_edit.clear()
        self._have_combo.setCurrentText("")
        self._want_combo.setCurrentText("")
        self._view_combo.setCurrentText("All Commands")
        self._groups.setCurrentRow(0)
        self._group_id = ""
        self._refresh_view()

    def _search_everywhere(self) -> None:
        self._view_combo.setCurrentText("All Commands")
        self._groups.setCurrentRow(0)
        self._group_id = ""
        self._refresh_view()

    def _focus_commands(self) -> None:
        if self._summary_table.rowCount() and self._view_combo.currentText() != "Processes":
            self._summary_table.setFocus()
            if self._summary_table.currentRow() < 0:
                self._summary_table.setCurrentCell(0, 0)

    def _refresh_catalog(self) -> None:
        """Reload the live files explicitly without touching scratchpad contents."""
        try:
            workflows = self._load_workflows()
            entries = build_command_catalog(workflow_catalog=workflows)
        except Exception as exc:
            self._hint_label.setText(f"Could not refresh the catalog: {exc}")
            return
        self._entries = entries
        self._workflow_catalog = workflows
        self._populate_groups()
        self._refresh_view()
        self._hint_label.setText("Catalog refreshed. Browse a group or search; Esc to close.")

    def _follow_link(self, link: str) -> None:
        if link.startswith("capability:"):
            self._show_capability_command(unquote(link[len("capability:") :]))
        elif link.startswith("group:"):
            group_id = unquote(link[len("group:") :])
            for row in range(self._groups.count()):
                if self._groups.item(row).data(Qt.ItemDataRole.UserRole) == group_id:
                    self._groups.setCurrentRow(row)
                    break

    def _command_link(self, entry: CommandCatalogEntry) -> str:
        target = quote(entry.capability_id, safe="")
        return (
            f'<a style="color: {self._link_color}" href="capability:{target}">'
            f"{html.escape(entry.trigger)}</a>"
        )

    def _guide_html(self) -> str:
        group = next((g for g in (*COMMAND_GROUPS, CUSTOM_GROUP) if g.id == self._group_id), None)
        parts = ["<p>Select a command above to see its full description, preview, and actions.</p>"]
        if group is None:
            parts.append("<h3>Remember what you can do</h3>")
            for candidate in COMMAND_GROUPS:
                if any(candidate in groups_for(e) for e in self._entries):
                    parts.append(
                        f'<p><a href="group:{candidate.id}">{html.escape(candidate.title)}</a>'
                        f"<br>{html.escape(candidate.description)}</p>"
                    )
        else:
            for workflow in self._workflow_catalog.workflows:
                if workflow.id not in group.workflows:
                    continue
                available = [
                    (node, self._entry_for_capability(node.capability)) for node in workflow.nodes
                ]
                available = [(node, entry) for node, entry in available if entry is not None]
                if not available:
                    continue
                parts.append(
                    f"<h3>{html.escape(workflow.name)}</h3><p>{html.escape(workflow.description)}</p>"
                )
                for node, entry in available:
                    parts.append(
                        f"<p>{self._command_link(entry)} — "
                        f"{html.escape(node.role or entry.description)}</p>"
                    )
                if workflow.notes:
                    parts.append(f"<p>{html.escape(workflow.notes)}</p>")
        return "".join(parts)

    def _related_html(self, entry: CommandCatalogEntry) -> str:
        parts = []
        seen = set()
        group = next((g for g in COMMAND_GROUPS if g.id == self._group_id), None)
        priorities = group.workflows if group else ()
        workflows = sorted(
            self._workflow_catalog.workflows,
            key=lambda w: priorities.index(w.id) if w.id in priorities else len(priorities),
        )
        for workflow in workflows:
            for edge in workflow.edges:
                if entry.capability_id not in (edge.source, edge.target):
                    continue
                incoming = entry.capability_id == edge.target
                other = self._entry_for_capability(edge.source if incoming else edge.target)
                if other is None or (
                    self._group_id and not any(g.id == self._group_id for g in groups_for(other))
                ):
                    continue
                key = (edge.source, edge.target)
                if key in seen:
                    continue
                seen.add(key)
                direction = "From" if incoming else "To"
                parts.append(
                    f"<p>{direction} {self._command_link(other)} — {html.escape(edge.label)}</p>"
                )
        return "<b>Optional combinations</b>" + "".join(parts) if parts else ""

    # ── Discovery state ─────────────────────────────────────────────────────

    def _current_query(self) -> RecommendationQuery:
        return RecommendationQuery(
            text=self._search_edit.text().strip(),
            have_artifact=self._have_combo.currentText().strip(),
            want_artifact=self._want_combo.currentText().strip(),
        )

    def _visible_entries(self) -> list[CommandCatalogEntry]:
        """Apply membership before ranking, including Favorites and Recent."""
        view = self._view_combo.currentText()
        favorites = tuple(self._config.discovery.favorite_triggers)
        recents = tuple(self._config.discovery.recent_triggers)
        query = self._current_query()
        base = [
            entry
            for entry in self._entries
            if not self._group_id or any(g.id == self._group_id for g in groups_for(entry))
        ]
        group = next((g for g in COMMAND_GROUPS if g.id == self._group_id), None)
        if group is not None:
            order = {capability: i for i, capability in enumerate(group.capabilities)}
            base.sort(key=lambda entry: order[entry.capability_id])
        if view == "Recent":
            by_trigger = {e.trigger: e for e in base}
            base = [by_trigger[t] for t in recents if t in by_trigger]
        elif view == "Favorites":
            base = [e for e in base if e.trigger in favorites]
        if query.text or query.have_artifact or query.want_artifact:
            return [r.entry for r in recommend(base, query, favorites=favorites, recents=recents)]
        return base

    def _refresh_view(self, *_args) -> None:
        processes = self._view_combo.currentText() == "Processes"
        self._groups.setEnabled(not processes)
        self._search_edit.setEnabled(not processes)
        self._artifact_toggle.setEnabled(not processes)
        self._artifact_controls.setEnabled(not processes)
        self._pages.setCurrentWidget(self._process_page if processes else self._command_page)
        if processes:
            self._populate_workflows()
        else:
            self._populate_entries(self._visible_entries())
        artifacts_active = bool(self._have_combo.currentText() or self._want_combo.currentText())
        self._artifact_toggle.setText(
            "Filter by artifacts" + (" (active)" if artifacts_active else "")
        )

    def _entry_actions(self, entry: CommandCatalogEntry) -> dict:
        return {
            "copy_trigger": self._copy_trigger,
            "copy_prompt": self._copy_prompt,
            "scratchpad": self._send_to_scratchpad,
            "packet": self._open_packet_dialog,
            "edit": self._open_in_editor,
            "favorite": self._toggle_favorite_entry,
            "is_favorite": entry.trigger in self._config.discovery.favorite_triggers,
            "show_link": self._follow_link,
        }

    def _populate_entries(self, entries: list[CommandCatalogEntry]) -> None:
        previous = self._selected_entry
        self._shown_entries = entries
        group = next((g for g in (*COMMAND_GROUPS, CUSTOM_GROUP) if g.id == self._group_id), None)
        title = group.title if group else "All commands"
        if self._view_combo.currentText() in ("Favorites", "Recent", "Recommended"):
            title = f"{self._view_combo.currentText()} · {title}"
        self._summary_label.setText(f"{title} — {len(entries)} commands")
        self._group_description.setText(
            group.description
            if group
            else "Pick a group to remember your options. Commands may belong to several groups."
        )
        self._empty_label.setVisible(not entries)
        self._search_everywhere_btn.setVisible(
            not entries
            and bool(self._group_id or self._view_combo.currentText() in ("Favorites", "Recent"))
        )
        fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        fixed_font.setPointSize(self._config.ui.font_size)
        fixed_font.setBold(True)
        self._summary_table.blockSignals(True)
        self._summary_table.setRowCount(len(entries))
        self._summary_table.setCurrentCell(-1, -1)
        self._summary_table.clearSelection()
        for row, entry in enumerate(entries):
            role, cue = command_cue(entry)
            trigger = QTableWidgetItem(entry.trigger)
            trigger.setFont(fixed_font)
            trigger.setToolTip(f"{entry.name}\n{entry.description}")
            trigger.setData(Qt.ItemDataRole.UserRole, entry.capability_id)
            cue_item = QTableWidgetItem(cue)
            cue_item.setToolTip(entry.use_when or entry.description)
            role_item = QTableWidgetItem(role)
            role_item.setToolTip(entry.name)
            for column, item in enumerate((trigger, cue_item, role_item)):
                self._summary_table.setItem(row, column, item)
        self._summary_table.resizeRowsToContents()
        self._summary_table.blockSignals(False)
        self._guide_browser.setHtml(self._guide_html())
        selected_row = next(
            (
                i
                for i, entry in enumerate(entries)
                if previous is not None
                and (
                    entry.capability_id == previous.capability_id
                    if previous.capability_id
                    else entry.trigger == previous.trigger
                )
            ),
            -1,
        )
        if selected_row >= 0:
            self._summary_table.setCurrentCell(selected_row, 0)
        else:
            self._command_selected(-1, -1, -1, -1)

    def _command_selected(self, row: int, _column: int, _old_row: int, _old_column: int) -> None:
        if row < 0 or row >= len(self._shown_entries):
            self._selected_entry = None
            self._detail_widget = None
            self._detail_pages.setCurrentWidget(self._guide_browser)
            return
        entry = self._shown_entries[row]
        self._selected_entry = entry
        old = self._detail_scroll.takeWidget()
        if old is not None:
            old.deleteLater()
        self._detail_widget = CommandRowWidget(
            entry,
            actions={**self._entry_actions(entry), "usage_monitor": self._usage_monitor},
            related_html=self._related_html(entry),
            font_size=self._config.ui.font_size,
        )
        self._detail_scroll.setWidget(self._detail_widget)
        self._detail_pages.setCurrentWidget(self._detail_scroll)

    def _build_workflow_panel(self):
        from espansr.ui.workflow_diagram import WorkflowPanel, capability_infos_from_entries

        if self._workflow_panel is None:
            self._workflow_panel = WorkflowPanel(
                theme=self._config.ui.theme,
                actions=[
                    ("Copy prompt", self._copy_capability_prompt),
                    ("Prompt to scratchpad", self._send_capability_to_scratchpad),
                    ("Show command", self._show_capability_command),
                ],
            )
            self._workflow_panel.capability_activated.connect(self._show_capability_command)
            self._process_splitter.addWidget(self._workflow_panel)
            prepare_splitter(
                self._process_splitter,
                "processes",
                panel_sizes(self._config.discovery.panel_sizes, "processes", [150, 390]),
            )
        self._workflow_panel.set_catalog(
            self._workflow_catalog, capability_infos_from_entries(self._entries)
        )
        return self._workflow_panel

    def _populate_workflows(self) -> None:
        workflows = self._workflow_catalog.workflows
        self._process_table.blockSignals(True)
        self._process_table.setRowCount(len(workflows))
        for row, workflow in enumerate(workflows):
            for column, text in enumerate(
                (
                    workflow.id,
                    str(len(workflow.entry_points)),
                    workflow.description or workflow.name,
                )
            ):
                item = QTableWidgetItem(text)
                item.setToolTip(workflow.name if column == 0 else text)
                self._process_table.setItem(row, column, item)
        self._process_table.resizeRowsToContents()
        self._process_table.blockSignals(False)
        self._build_workflow_panel()
        if workflows:
            self._process_table.setCurrentCell(0, 0)

    def _process_selected(self, row: int, _column: int, _old_row: int, _old_column: int) -> None:
        if self._workflow_panel is not None and 0 <= row < len(self._workflow_catalog.workflows):
            self._workflow_panel.show_workflow(self._workflow_catalog.workflows[row].id)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "_summary_table"):
            self._summary_table.resizeRowsToContents()

    # ── Direct actions (display and copy only — nothing executes) ───────────

    def _persist_discovery(self, *fields: str) -> None:
        """Save only touched preferences, preserving changes from the editor
        or another reference window since this window was opened."""
        try:
            fresh = load_config_fresh()
        except Exception:
            fresh = None
        if fresh is not None:
            for name in fields:
                setattr(fresh.discovery, name, getattr(self._config.discovery, name))
            saved = save_config(fresh)
        else:
            saved = save_config(self._config)
        if not saved:
            self._hint_label.setText(
                "Could not save local reference preferences. This window remains usable."
            )

    def _set_stay_on_top(self, checked: bool) -> None:
        visible = self.isVisible()
        geometry = self.saveGeometry()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, checked)
        self.restoreGeometry(geometry)
        if visible:
            self.show()
        self._config.discovery.stay_on_top = checked
        self._persist_discovery("stay_on_top")

    def _save_layout(self, *_args) -> None:
        self._config.discovery.panel_sizes = capture_panel_sizes(
            self._layout_splitters, self._config.discovery.panel_sizes
        )
        self._persist_discovery("panel_sizes")

    def done(self, result: int) -> None:
        geometry = bytes(self.saveGeometry().toBase64()).decode("ascii")
        self._config.discovery.window_geometry = geometry
        self._config.discovery.panel_sizes = capture_panel_sizes(
            self._layout_splitters, self._config.discovery.panel_sizes
        )
        self._persist_discovery("window_geometry", "panel_sizes")
        super().done(result)

    def _record_recent(self, trigger: str) -> None:
        recents = self._config.discovery.recent_triggers
        if trigger in recents:
            recents.remove(trigger)
        recents.insert(0, trigger)
        del recents[self._config.discovery.max_recent :]
        self._persist_discovery("recent_triggers")

    def _copy_trigger(self, entry: CommandCatalogEntry) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(entry.trigger)
        self._record_recent(entry.trigger)

    def _copy_prompt(self, entry: CommandCatalogEntry) -> None:
        if not entry.content:
            return
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(entry.content)
        self._record_recent(entry.trigger)

    def _send_to_scratchpad(self, entry: CommandCatalogEntry) -> None:
        """Place the full prompt in the scratchpad (the trigger only for
        system entries that have no prompt body)."""
        existing = self._scratchpad.toPlainText()
        separator = "" if not existing or existing.endswith("\n") else "\n"
        payload = entry.content if entry.content else entry.trigger
        self._scratchpad.setPlainText(existing + separator + payload)
        cursor = self._scratchpad.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self._scratchpad.setTextCursor(cursor)
        self._record_recent(entry.trigger)

    def _send_capability_to_scratchpad(self, capability: str) -> None:
        entry = self._entry_for_capability(capability)
        if entry is not None:
            self._send_to_scratchpad(entry)

    def _copy_capability_prompt(self, capability: str) -> None:
        entry = self._entry_for_capability(capability)
        if entry is not None:
            self._copy_prompt(entry)

    def _entry_for_capability(self, capability: str) -> Optional[CommandCatalogEntry]:
        for entry in self._entries:
            if entry.capability_id == capability:
                return entry
        return None

    def _show_capability_command(self, capability: str) -> None:
        """Reveal an explicitly selected capability even with stale filters."""
        entry = self._entry_for_capability(capability)
        if entry is None:
            return
        self._show_all()
        for row, visible in enumerate(self._shown_entries):
            if visible.trigger == entry.trigger:
                self._summary_table.setCurrentCell(row, 0)
                self._summary_table.scrollToItem(self._summary_table.item(row, 0))
                break

    def _toggle_favorite_entry(self, entry: CommandCatalogEntry) -> None:
        self._toggle_favorite(entry.trigger)

    def _toggle_favorite(self, trigger: str) -> None:
        favorites = self._config.discovery.favorite_triggers
        if trigger in favorites:
            favorites.remove(trigger)
        else:
            favorites.append(trigger)
        self._persist_discovery("favorite_triggers")
        self._refresh_view()

    def _open_packet_dialog(self, entry: CommandCatalogEntry) -> None:
        """Open a packet preview prefilled from the capability. Save stays explicit."""
        from espansr.core.packets import Packet
        from espansr.ui.packet_dialog import PacketDialog

        prefill = Packet(
            artifact_type=entry.produces[0] if entry.produces else "",
            created_from=entry.capability_id,
            workflow=entry.workflows[0] if entry.workflows else "",
        )
        dialog = PacketDialog(prefill=prefill, parent=self)
        dialog.setStyleSheet(self.styleSheet())
        dialog.show()

    def _packet_from_scratchpad(self) -> None:
        """Explicitly carry the scratchpad text into an (unsaved) packet preview."""
        from espansr.core.packets import Packet
        from espansr.ui.packet_dialog import PacketDialog

        prefill = Packet(sections={"Confirmed facts and evidence": self._scratchpad.toPlainText()})
        dialog = PacketDialog(prefill=prefill, parent=self)
        dialog.setStyleSheet(self.styleSheet())
        dialog.show()

    def _open_in_editor(self, entry: CommandCatalogEntry) -> None:
        """Open the full editor with this template selected.

        The editor launches as its own detached process (exactly like the
        generated :aopen trigger does): the popup usually runs a modal event
        loop, so an in-process window would be input-blocked behind it.
        """
        try:
            fresh = load_config_fresh()
            fresh.ui.last_template = entry.name
            save_config(fresh)
        except Exception:
            pass
        try:
            from pathlib import Path

            from PyQt6.QtCore import QProcess

            executable = sys.executable
            pythonw = Path(sys.executable).with_name("pythonw.exe")
            if pythonw.exists():
                executable = str(pythonw)
            QProcess.startDetached(executable, ["-m", "espansr", "gui"])
        except Exception:
            pass  # The popup stays useful even when the full editor cannot open.

    def keyPressEvent(self, event) -> None:
        """Close the popup on Escape."""
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)


def launch_commands_popup(entries: Optional[list[CommandCatalogEntry]] = None) -> None:
    """Create the QApplication and launch the commands popup."""
    app: Optional[QApplication] = QApplication.instance()  # type: ignore[assignment]
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)

    dialog = CommandsPopupDialog(entries=entries)
    dialog.show()
    dialog.activateWindow()
    if owns_app:
        app.exec()
        return

    # Keep modeless windows alive when called from an existing Qt application.
    windows = getattr(app, "_espansr_references", [])
    app._espansr_references = windows
    windows.append(dialog)
    dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    dialog.destroyed.connect(lambda: windows.remove(dialog) if dialog in windows else None)
