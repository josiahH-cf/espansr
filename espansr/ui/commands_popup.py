"""Lightweight commands popup launched by the hardcoded :coms trigger."""

import sys
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontDatabase, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from espansr.core.command_catalog import CommandCatalogEntry, build_command_catalog
from espansr.core.config import get_config
from espansr.ui.theme import get_theme_stylesheet


class CommandRowWidget(QFrame):
    """Standardized row widget for the commands popup."""

    PREVIEW_HEIGHT = 88

    def __init__(self, entry: CommandCatalogEntry, parent: Optional[QWidget] = None):
        """Build the visual layout for one command entry."""
        super().__init__(parent)
        self._entry = entry
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


class CommandsPopupDialog(QDialog):
    """Popup showing available Espanso triggers plus an ephemeral scratchpad."""

    def __init__(
        self,
        entries: Optional[list[CommandCatalogEntry]] = None,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the popup dialog."""
        super().__init__(parent)
        config = get_config()

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
        # add context, and copy it back out.
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

        self._entries = entries if entries is not None else build_command_catalog()
        self._populate_entries(self._entries)

        self._shortcut_close = QShortcut(QKeySequence("Esc"), self)
        self._shortcut_close.activated.connect(self.reject)

        # Focus the scratchpad so a command can be typed or pasted immediately.
        self._scratchpad.setFocus()

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
            widget = CommandRowWidget(entry)
            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, widget)

    def _scroll_to_entry_row(self, row: int, _column: int) -> None:
        """Jump the detailed card list to the row selected in the summary table."""
        item = self._list.item(row)
        if item is not None:
            self._list.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtTop)

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
