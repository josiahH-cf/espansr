"""GUI acceptance checks for the handoff-packet dialog (ARCH-06, BEH-08/09).

The dialog previews a packet without persisting anything; only the explicit
Save action writes a file; saved packets can be reloaded; and the dialog never
records a current workflow step anywhere.
"""

import pytest

from espansr.core.packets import Packet, load_packet

pytest.importorskip("PyQt6")


def _make_dialog(qtbot, tmp_path, prefill=None):
    from espansr.ui.packet_dialog import PacketDialog

    dialog = PacketDialog(prefill=prefill, packets_dir=tmp_path / "packets")
    qtbot.addWidget(dialog)
    return dialog


def test_preview_persists_nothing(qtbot, tmp_path):
    dialog = _make_dialog(qtbot, tmp_path)
    dialog._title_edit.setText("Preview only")
    dialog._artifact_combo.setCurrentText("evidence-report")
    dialog._section_edits["Objective"].setPlainText("Decide something.")
    dialog._update_preview()
    assert "Preview only" in dialog._preview_text.toPlainText()
    packets_dir = tmp_path / "packets"
    assert not packets_dir.exists() or list(packets_dir.iterdir()) == []


def test_explicit_save_writes_one_packet(qtbot, tmp_path):
    dialog = _make_dialog(qtbot, tmp_path)
    dialog._title_edit.setText("Saved from dialog")
    dialog._artifact_combo.setCurrentText("evidence-report")
    dialog._outcome_combo.setCurrentText("gap-review")
    dialog._section_edits["Objective"].setPlainText("Carry this forward.")
    dialog._save()
    saved = list((tmp_path / "packets").glob("*.md"))
    assert len(saved) == 1
    packet = load_packet(saved[0])
    assert packet.title == "Saved from dialog"
    assert packet.artifact_type == "evidence-report"
    assert packet.requested_outcome == "gap-review"
    assert packet.sections["Objective"] == "Carry this forward."


def test_closing_without_save_leaves_nothing(qtbot, tmp_path):
    dialog = _make_dialog(qtbot, tmp_path)
    dialog._title_edit.setText("Never saved")
    dialog._update_preview()
    dialog.close()
    packets_dir = tmp_path / "packets"
    assert not packets_dir.exists() or list(packets_dir.iterdir()) == []


def test_prefill_from_capability_context(qtbot, tmp_path):
    prefill = Packet(
        title="",
        artifact_type="evidence-report",
        created_from="research-report",
        workflow="evidence-research-cycle",
    )
    dialog = _make_dialog(qtbot, tmp_path, prefill=prefill)
    assert dialog._artifact_combo.currentText() == "evidence-report"
    dialog._update_preview()
    preview = dialog._preview_text.toPlainText()
    assert "created_from: research-report" in preview
    assert "workflow: evidence-research-cycle" in preview


def test_saved_packet_roundtrips_through_dialog_reload(qtbot, tmp_path):
    dialog = _make_dialog(qtbot, tmp_path)
    dialog._title_edit.setText("Round trip")
    dialog._artifact_combo.setCurrentText("gap-review")
    dialog._section_edits["Decisions"].setPlainText("Use OIDC.")
    dialog._notes_edit.setPlainText("A note.")
    dialog._save()
    saved = list((tmp_path / "packets").glob("*.md"))[0]

    reopened = _make_dialog(qtbot, tmp_path)
    reopened.load_packet_file(saved)
    assert reopened._title_edit.text() == "Round trip"
    assert reopened._artifact_combo.currentText() == "gap-review"
    assert reopened._section_edits["Decisions"].toPlainText() == "Use OIDC."
    assert reopened._notes_edit.toPlainText() == "A note."


def test_packet_dialog_never_writes_current_step(qtbot, tmp_path):
    dialog = _make_dialog(qtbot, tmp_path)
    dialog._title_edit.setText("No state")
    dialog._artifact_combo.setCurrentText("evidence-report")
    dialog._save()
    saved = list((tmp_path / "packets").glob("*.md"))[0]
    text = saved.read_text(encoding="utf-8")
    for forbidden in ("current_step", "current_node", "current_capability"):
        assert forbidden not in text
