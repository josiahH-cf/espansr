"""Handoff-packet dialog: preview, explicit save, and reopen.

The dialog composes a handoff packet from user-selected material. Nothing is
persisted while previewing or when the dialog closes — only the explicit Save
button writes a packet file, into the local config-owned packets directory
(never the git-synced template store). The dialog records no workflow step.
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from espansr.core.capabilities import ARTIFACT_TYPES
from espansr.core.packets import (
    PACKET_SECTIONS,
    Packet,
    PacketError,
    load_packet,
    render_packet,
    save_packet,
)


class PacketDialog(QDialog):
    """Compose, preview, save, and reopen handoff packets."""

    def __init__(
        self,
        prefill: Optional[Packet] = None,
        packets_dir: Optional[Path] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Handoff Packet")
        self.resize(760, 720)
        self._packets_dir = Path(packets_dir) if packets_dir is not None else None
        self._base = prefill or Packet()
        self._saved_path: Optional[Path] = None

        layout = QVBoxLayout(self)

        hint = QLabel(
            "Nothing is saved until you press Save packet. Preview and Copy "
            "never persist anything."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addWidget(QLabel("Title:"))
        self._title_edit = QLineEdit()
        self._title_edit.setText(self._base.title)
        layout.addWidget(self._title_edit)

        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel("Artifact type:"))
        self._artifact_combo = QComboBox()
        self._artifact_combo.setEditable(True)
        self._artifact_combo.addItems(["", *ARTIFACT_TYPES])
        self._artifact_combo.setCurrentText(self._base.artifact_type)
        selector_row.addWidget(self._artifact_combo, 1)
        selector_row.addWidget(QLabel("Requested outcome:"))
        self._outcome_combo = QComboBox()
        self._outcome_combo.setEditable(True)
        self._outcome_combo.addItems(["", *ARTIFACT_TYPES])
        self._outcome_combo.setCurrentText(self._base.requested_outcome)
        selector_row.addWidget(self._outcome_combo, 1)
        layout.addLayout(selector_row)

        sections_area = QScrollArea()
        sections_area.setWidgetResizable(True)
        sections_widget = QWidget()
        sections_layout = QVBoxLayout(sections_widget)
        self._section_edits = {}
        for section in PACKET_SECTIONS:
            sections_layout.addWidget(QLabel(f"{section}:"))
            edit = QPlainTextEdit()
            edit.setPlainText(self._base.sections.get(section, ""))
            edit.setMaximumHeight(72)
            sections_layout.addWidget(edit)
            self._section_edits[section] = edit
        sections_layout.addWidget(QLabel("Notes:"))
        self._notes_edit = QPlainTextEdit()
        self._notes_edit.setPlainText(self._base.notes)
        self._notes_edit.setMaximumHeight(72)
        sections_layout.addWidget(self._notes_edit)
        sections_area.setWidget(sections_widget)
        layout.addWidget(sections_area, 2)

        layout.addWidget(QLabel("Preview:"))
        self._preview_text = QPlainTextEdit()
        self._preview_text.setReadOnly(True)
        layout.addWidget(self._preview_text, 2)

        button_row = QHBoxLayout()
        preview_btn = QPushButton("Preview")
        preview_btn.clicked.connect(self._update_preview)
        button_row.addWidget(preview_btn)
        self._copy_btn = QPushButton("Copy packet")
        self._copy_btn.clicked.connect(self._copy_to_clipboard)
        button_row.addWidget(self._copy_btn)
        self._save_btn = QPushButton("Save packet")
        self._save_btn.clicked.connect(self._save)
        button_row.addWidget(self._save_btn)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        button_row.addWidget(close_btn)
        layout.addLayout(button_row)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

    # ── Packet assembly ─────────────────────────────────────────────────────

    def build_packet(self) -> Packet:
        """Assemble the packet from the current fields. Never persists."""
        sections = {
            name: edit.toPlainText().strip()
            for name, edit in self._section_edits.items()
            if edit.toPlainText().strip()
        }
        # Sections the dialog does not display (hand-added or future ones)
        # are carried forward untouched instead of being silently dropped.
        for name, body in self._base.sections.items():
            if name not in self._section_edits and body:
                sections[name] = body
        return Packet(
            title=self._title_edit.text().strip(),
            artifact_type=self._artifact_combo.currentText().strip(),
            workflow=self._base.workflow,
            created_from=self._base.created_from,
            requested_outcome=self._outcome_combo.currentText().strip(),
            candidates=list(self._base.candidates),
            sections=sections,
            notes=self._notes_edit.toPlainText().strip(),
            packet_id=self._base.packet_id,
            created=self._base.created,
            extra=dict(self._base.extra),
        )

    def _update_preview(self) -> None:
        self._preview_text.setPlainText(render_packet(self.build_packet()))

    def _copy_to_clipboard(self) -> None:
        from PyQt6.QtWidgets import QApplication

        self._update_preview()
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self._preview_text.toPlainText())
        self._status_label.setText("Packet copied to clipboard (not saved).")

    def _save(self) -> None:
        """The one explicit persistence action."""
        packet = self.build_packet()
        try:
            path = save_packet(packet, packets_dir=self._packets_dir)
        except OSError as exc:
            self._status_label.setText(f"Save failed: {exc}")
            return
        self._base = packet  # Keep the assigned ID so re-saving updates in place
        self._saved_path = path
        self._status_label.setText(f"Saved packet to {path}")
        self._update_preview()

    def load_packet_file(self, path: Path) -> bool:
        """Reopen a saved packet into the dialog."""
        try:
            packet = load_packet(path)
        except PacketError as exc:
            self._status_label.setText(f"Could not load packet: {exc}")
            return False
        self._base = packet
        self._title_edit.setText(packet.title)
        self._artifact_combo.setCurrentText(packet.artifact_type)
        self._outcome_combo.setCurrentText(packet.requested_outcome)
        for name, edit in self._section_edits.items():
            edit.setPlainText(packet.sections.get(name, ""))
        self._notes_edit.setPlainText(packet.notes)
        self._update_preview()
        return True
