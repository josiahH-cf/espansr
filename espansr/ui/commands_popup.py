"""Lightweight commands popup launched by the hardcoded :coms trigger.

Beyond the classic alphabetical reference (summary table, detail cards, and
the ephemeral scratchpad), the popup is an intent-aware command palette: a
fuzzy search field, "I currently have" / "I need to produce" artifact
selectors, and view switching between All Commands, Recommended, Processes,
Recent, and Favorites. Everything is local and deterministic — no action in
this popup ever executes another prompt, shell command, model, installer,
sync, or network request; actions only change what is displayed, copy text,
or open the packet/editor dialogs on explicit request.
"""

import sys
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontDatabase, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from espansr.core.capabilities import ARTIFACT_TYPES
from espansr.core.command_catalog import CommandCatalogEntry, build_command_catalog
from espansr.core.config import get_config, load_config_fresh, save_config
from espansr.core.recommend import RecommendationQuery, recommend
from espansr.ui.theme import get_theme_stylesheet

_VIEWS = ("All Commands", "Recommended", "Processes", "Recent", "Favorites")


class CommandRowWidget(QFrame):
    """Standardized row widget for the commands popup."""

    PREVIEW_HEIGHT = 88

    def __init__(
        self,
        entry: CommandCatalogEntry,
        parent: Optional[QWidget] = None,
        actions: Optional[dict] = None,
    ):
        """Build the visual layout for one command entry."""
        super().__init__(parent)
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
        fixed_font.setBold(True)
        self._trigger_label.setFont(fixed_font)
        self._trigger_label.setMargin(6)
        self._trigger_label.setFrameShape(QFrame.Shape.Box)
        header.addWidget(self._trigger_label, 0)

        self._name_label = QLabel(entry.name)
        name_font = QFont(self._name_label.font())
        name_font.setBold(True)
        self._name_label.setFont(name_font)
        header.addWidget(self._name_label, 1)

        self._workflow_label = QLabel(entry.workflow_label)
        self._workflow_label.setMargin(4)
        self._workflow_label.setFrameShape(QFrame.Shape.Box)
        header.addWidget(self._workflow_label, 0)

        layout.addLayout(header)

        self._description_label = QLabel(entry.description)
        self._description_label.setWordWrap(True)
        layout.addWidget(self._description_label)

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
        self._process_label.setVisible(bool(self._process_label.text()))
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

        layout.addLayout(self._build_action_row(entry))

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

    def _build_action_row(self, entry: CommandCatalogEntry) -> QHBoxLayout:
        """Direct actions: copy, scratchpad, packet, editor, favorite."""
        row = QHBoxLayout()
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
        row.addWidget(self._copy_trigger_btn)

        self._copy_prompt_btn = QPushButton("Copy prompt")
        self._copy_prompt_btn.setVisible(bool(entry.content))
        self._copy_prompt_btn.clicked.connect(_run("copy_prompt", _copy_prompt_fallback))
        row.addWidget(self._copy_prompt_btn)

        self._scratchpad_btn = QPushButton("To scratchpad")
        self._scratchpad_btn.clicked.connect(_run("scratchpad"))
        row.addWidget(self._scratchpad_btn)

        self._packet_btn = QPushButton("Packet…")
        self._packet_btn.clicked.connect(_run("packet"))
        row.addWidget(self._packet_btn)

        self._edit_btn = QPushButton("Edit…")
        self._edit_btn.setVisible(entry.source == "template")
        self._edit_btn.clicked.connect(_run("edit"))
        row.addWidget(self._edit_btn)

        self._favorite_btn = QPushButton("☆")
        self._favorite_btn.setCheckable(True)
        self._favorite_btn.setChecked(bool(self._actions.get("is_favorite")))
        if self._favorite_btn.isChecked():
            self._favorite_btn.setText("★")
        self._favorite_btn.setFixedWidth(34)
        self._favorite_btn.toggled.connect(self._on_favorite_toggled)
        row.addWidget(self._favorite_btn)

        row.addStretch()
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
    """Popup showing available Espanso triggers plus an ephemeral scratchpad."""

    def __init__(
        self,
        entries: Optional[list[CommandCatalogEntry]] = None,
        parent: Optional[QWidget] = None,
        workflow_catalog=None,
    ):
        """Initialize the popup dialog."""
        super().__init__(parent)
        config = get_config()
        self._config = config

        self.setWindowTitle("Available Commands")
        self.setModal(False)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.resize(940, 760)
        self.setStyleSheet(
            get_theme_stylesheet(
                theme=config.ui.theme,
                font_size=config.ui.font_size,
            )
        )

        if workflow_catalog is None:
            try:
                from espansr.core.workflows import load_workflow_catalog

                workflow_catalog = load_workflow_catalog()
            except Exception:
                from espansr.core.workflows import WorkflowCatalog

                workflow_catalog = WorkflowCatalog()
        self._workflow_catalog = workflow_catalog

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self._title_label = QLabel("Available Commands")
        title_font = QFont(self._title_label.font())
        title_font.setPointSize(title_font.pointSize() + 4)
        title_font.setBold(True)
        self._title_label.setFont(title_font)
        layout.addWidget(self._title_label)

        self._hint_label = QLabel("Type any trigger below. Press Esc to close.")
        self._hint_label.setWordWrap(True)
        layout.addWidget(self._hint_label)

        # ── Discovery controls ────────────────────────────────────────────
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText(
            "Describe the job you need — e.g. challenge finished research"
        )
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.textChanged.connect(self._refresh_view)
        layout.addWidget(self._search_edit)

        selector_row = QHBoxLayout()
        selector_row.setSpacing(8)
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
        selector_row.addWidget(QLabel("View:"))
        self._view_combo = QComboBox()
        self._view_combo.addItems(list(_VIEWS))
        self._view_combo.currentTextChanged.connect(self._refresh_view)
        selector_row.addWidget(self._view_combo)
        layout.addLayout(selector_row)

        self._summary_label = QLabel("Quick Reference")
        summary_font = QFont(self._summary_label.font())
        summary_font.setBold(True)
        self._summary_label.setFont(summary_font)
        layout.addWidget(self._summary_label)

        self._summary_table = QTableWidget()
        self._summary_table.setColumnCount(3)
        self._summary_table.setHorizontalHeaderLabels(["Command", "Workflow", "Description"])
        self._summary_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._summary_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._summary_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._summary_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._summary_table.setWordWrap(False)
        self._summary_table.setAlternatingRowColors(True)
        self._summary_table.setCornerButtonEnabled(False)
        self._summary_table.verticalHeader().setVisible(False)
        self._summary_table.verticalHeader().setDefaultSectionSize(30)
        self._summary_table.horizontalHeader().setStretchLastSection(True)
        self._summary_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._summary_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._summary_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self._summary_table.cellClicked.connect(self._scroll_to_entry_row)
        layout.addWidget(self._summary_table)

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._list.setSpacing(8)
        layout.addWidget(self._list, 2)

        # Ephemeral scratchpad pinned to the bottom of the popup. It is never
        # persisted — purely a throwaway space to type or paste a command,
        # add context, and copy it back out. Only the explicit packet button
        # below carries selected scratchpad text into a (still unsaved)
        # packet preview.
        self._scratchpad_label = QLabel("Scratchpad")
        scratchpad_font = QFont(self._scratchpad_label.font())
        scratchpad_font.setBold(True)
        self._scratchpad_label.setFont(scratchpad_font)
        layout.addWidget(self._scratchpad_label)

        self._scratchpad_hint = QLabel(
            "Ephemeral — type or paste a command, add context, then copy it. Nothing here is saved."
        )
        self._scratchpad_hint.setWordWrap(True)
        layout.addWidget(self._scratchpad_hint)

        self._scratchpad = QPlainTextEdit()
        self._scratchpad.setObjectName("scratchpad")
        self._scratchpad.setPlaceholderText("Type or paste any command here…")
        self._scratchpad.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._scratchpad.setMinimumHeight(96)
        layout.addWidget(self._scratchpad, 1)

        self._scratchpad_packet_btn = QPushButton("Create packet from scratchpad…")
        self._scratchpad_packet_btn.clicked.connect(self._packet_from_scratchpad)
        layout.addWidget(self._scratchpad_packet_btn)

        self._entries = entries if entries is not None else build_command_catalog()
        self._populate_entries(self._entries)

        self._shortcut_close = QShortcut(QKeySequence("Esc"), self)
        self._shortcut_close.activated.connect(self.reject)

        # Focus the scratchpad so a command can be typed or pasted immediately.
        self._scratchpad.setFocus()

    # ── Discovery state ─────────────────────────────────────────────────────

    def _current_query(self) -> RecommendationQuery:
        return RecommendationQuery(
            text=self._search_edit.text().strip(),
            have_artifact=self._have_combo.currentText().strip(),
            want_artifact=self._want_combo.currentText().strip(),
        )

    def _visible_entries(self) -> list[CommandCatalogEntry]:
        """Entries for the current view/query. Never mutates the catalog."""
        view = self._view_combo.currentText()
        favorites = tuple(self._config.discovery.favorite_triggers)
        recents = tuple(self._config.discovery.recent_triggers)
        query = self._current_query()
        has_query = bool(query.text or query.have_artifact or query.want_artifact)

        if view == "Recent":
            by_trigger = {e.trigger: e for e in self._entries}
            base = [by_trigger[t] for t in recents if t in by_trigger]
        elif view == "Favorites":
            base = [e for e in self._entries if e.trigger in favorites]
        elif view == "Recommended":
            if not has_query:
                return list(self._entries)
            ranked = recommend(self._entries, query, favorites=favorites, recents=recents)
            return [r.entry for r in ranked]
        else:  # All Commands
            base = list(self._entries)

        if has_query:
            ranked = recommend(base, query, favorites=favorites, recents=recents)
            return [r.entry for r in ranked]
        return base

    def _refresh_view(self, *_args) -> None:
        if self._view_combo.currentText() == "Processes":
            self._populate_workflows()
        else:
            self._populate_entries(self._visible_entries())

    # ── Population ──────────────────────────────────────────────────────────

    def _entry_actions(self, entry: CommandCatalogEntry) -> dict:
        return {
            "copy_trigger": self._copy_trigger,
            "copy_prompt": self._copy_prompt,
            "scratchpad": self._send_to_scratchpad,
            "packet": self._open_packet_dialog,
            "edit": self._open_in_editor,
            "favorite": self._toggle_favorite_entry,
            "is_favorite": entry.trigger in self._config.discovery.favorite_triggers,
        }

    def _populate_entries(self, entries: list[CommandCatalogEntry]) -> None:
        """Populate the scrollable list from command catalog entries."""
        fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        fixed_font.setBold(True)

        self._summary_table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            trigger_item = QTableWidgetItem(entry.trigger)
            trigger_item.setFont(fixed_font)
            trigger_item.setToolTip(entry.trigger)
            workflow_item = QTableWidgetItem(entry.workflow_label)
            workflow_item.setToolTip(entry.next_label or entry.workflow_label)
            description_item = QTableWidgetItem(entry.description)
            description_item.setToolTip(entry.description)
            self._summary_table.setItem(row, 0, trigger_item)
            self._summary_table.setItem(row, 1, workflow_item)
            self._summary_table.setItem(row, 2, description_item)

        visible_lines = min(max(len(entries), 4), 12)
        header_height = self._summary_table.horizontalHeader().height()
        row_height = self._summary_table.verticalHeader().defaultSectionSize()
        self._summary_table.setFixedHeight(header_height + (row_height * visible_lines) + 6)
        self._summary_table.resizeColumnToContents(0)

        self._list.clear()
        for entry in entries:
            widget = CommandRowWidget(entry, actions=self._entry_actions(entry))
            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, widget)

    def _populate_workflows(self) -> None:
        """Render the optional workflow manifests (Processes view)."""
        workflows = self._workflow_catalog.workflows
        self._summary_table.setRowCount(len(workflows))
        for row, workflow in enumerate(workflows):
            id_item = QTableWidgetItem(workflow.id)
            id_item.setToolTip(workflow.name)
            entry_item = QTableWidgetItem(f"{len(workflow.entry_points)} entry points")
            description_item = QTableWidgetItem(workflow.description or workflow.name)
            description_item.setToolTip(workflow.description)
            self._summary_table.setItem(row, 0, id_item)
            self._summary_table.setItem(row, 1, entry_item)
            self._summary_table.setItem(row, 2, description_item)

        visible_lines = min(max(len(workflows), 4), 12)
        header_height = self._summary_table.horizontalHeader().height()
        row_height = self._summary_table.verticalHeader().defaultSectionSize()
        self._summary_table.setFixedHeight(header_height + (row_height * visible_lines) + 6)

        self._list.clear()
        for workflow in workflows:
            widget = WorkflowRowWidget(workflow)
            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, widget)

    def _scroll_to_entry_row(self, row: int, _column: int) -> None:
        """Jump the detailed card list to the row selected in the summary table."""
        item = self._list.item(row)
        if item is not None:
            self._list.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtTop)

    # ── Direct actions (display and copy only — nothing executes) ───────────

    def _persist_discovery(self) -> None:
        """Persist favorites/recents without clobbering concurrent changes.

        The popup can stay open a long time in its own process, so a save
        based on its startup Config snapshot would silently revert settings
        written meanwhile by the editor or CLI. Instead, reload the current
        on-disk config, replace only the discovery section, and save that.
        """
        try:
            fresh = load_config_fresh()
        except Exception:
            fresh = None
        if fresh is not None:
            fresh.discovery = self._config.discovery
            save_config(fresh)
        else:
            save_config(self._config)

    def _record_recent(self, trigger: str) -> None:
        recents = self._config.discovery.recent_triggers
        if trigger in recents:
            recents.remove(trigger)
        recents.insert(0, trigger)
        del recents[self._config.discovery.max_recent :]
        self._persist_discovery()

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
        existing = self._scratchpad.toPlainText()
        separator = "" if not existing or existing.endswith("\n") else "\n"
        self._scratchpad.setPlainText(existing + separator + entry.trigger)
        self._record_recent(entry.trigger)

    def _toggle_favorite_entry(self, entry: CommandCatalogEntry) -> None:
        self._toggle_favorite(entry.trigger)

    def _toggle_favorite(self, trigger: str) -> None:
        favorites = self._config.discovery.favorite_triggers
        if trigger in favorites:
            favorites.remove(trigger)
        else:
            favorites.append(trigger)
        self._persist_discovery()

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
    if owns_app:
        dialog.exec()
        return

    dialog.show()
    dialog.activateWindow()
