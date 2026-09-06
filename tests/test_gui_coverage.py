"""GUI code paths that had no direct coverage.

Covers mouse selection on the workflow diagram, the auto-layout fallback for
manifests with only partial x/y hints, the repo-sync worker behind the main
window's Sync button (with subprocess.run stubbed so no git or installer
runs), and the :coms popup's per-command Packet button.
"""

import subprocess
from unittest.mock import patch

from PyQt6.QtCore import QPointF, Qt

from espansr.core.command_catalog import CommandCatalogEntry
from espansr.core.config import Config
from espansr.core.workflows import WorkflowCatalog, WorkflowEdge, WorkflowManifest, WorkflowNode

# ── Workflow diagram ─────────────────────────────────────────────────────────


def _chain_manifest(hints=None) -> WorkflowManifest:
    """A three-node chain a -> b -> c; ``hints`` maps capability -> (x, y)."""
    hints = hints or {}
    nodes = []
    for capability in ("a", "b", "c"):
        x, y = hints.get(capability, (None, None))
        nodes.append(WorkflowNode(capability=capability, x=x, y=y))
    return WorkflowManifest(
        id="chain",
        name="Chain",
        entry_points=["a"],
        nodes=nodes,
        edges=[
            WorkflowEdge(source="a", target="b", label="A to B", short="go"),
            WorkflowEdge(source="b", target="c", label="B to C", short="on"),
        ],
    )


FULL_HINTS = {"a": (0, 0), "b": (260, 0), "c": (520, 0)}


def test_diagram_mouse_click_selects_node(qtbot):
    from espansr.ui.workflow_diagram import WorkflowDiagramWidget

    widget = WorkflowDiagramWidget()
    qtbot.addWidget(widget)
    widget.resize(800, 400)
    widget.set_workflow(_chain_manifest(FULL_HINTS), {"c": ":c"})
    widget.show()
    qtbot.waitExposed(widget)
    assert widget.selected_capability() == "a"  # first entry point is preselected

    selected = []
    widget.capability_selected.connect(selected.append)
    node = widget._nodes["c"]
    inside_node = node.sceneBoundingRect().topLeft() + QPointF(10, 10)
    qtbot.mouseClick(
        widget.viewport(), Qt.MouseButton.LeftButton, pos=widget.mapFromScene(inside_node)
    )

    assert widget.selected_capability() == "c"
    assert selected == ["c"]


def test_layout_falls_back_to_auto_when_hints_partial():
    from espansr.ui.workflow_diagram import layout_workflow

    partial = layout_workflow(_chain_manifest({"a": (900, 900), "c": (5, 5)}))  # b unhinted

    assert set(partial) == {"a", "b", "c"}
    # The partial hints are ignored wholesale rather than mixed with computed spots ...
    assert partial["a"] != (900.0, 900.0)
    assert partial["c"] != (5.0, 5.0)
    assert partial == layout_workflow(_chain_manifest())
    # ... and the layered auto layout orders the chain left to right.
    assert partial["a"][0] < partial["b"][0] < partial["c"][0]
    # A complete set of hints is still honored verbatim.
    assert layout_workflow(_chain_manifest(FULL_HINTS))["b"] == (260.0, 0.0)


# ── Repo sync worker ─────────────────────────────────────────────────────────


def _fake_run(args, **_kwargs):
    """Answer the git and installer calls _run_sync makes as a clean, current checkout."""
    stdout = ""
    if "--is-inside-work-tree" in args:
        stdout = "true\n"
    elif "rev-list" in args:
        stdout = "0\n"
    return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")


def _record_fake_checkout(tmp_path):
    """Record install metadata (in the isolated config dir) for a stub checkout."""
    from espansr.core.install_meta import record_install_meta

    repo = tmp_path / "checkout"
    repo.mkdir()
    (repo / "install.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    record_install_meta(repo, installer="install.sh", platform="linux")
    return repo


def test_repo_sync_worker_reports_result(tmp_path, qtbot):
    from espansr.ui.main_window import _RepoSyncWorker

    repo = _record_fake_checkout(tmp_path)
    received = []
    worker = _RepoSyncWorker()
    worker.finished.connect(received.append)

    with (
        patch("subprocess.run", side_effect=_fake_run) as run,
        patch("espansr.__main__.shutil.which", return_value="/usr/bin/git"),
        patch("espansr.__main__.get_platform", return_value="linux"),
        patch("espansr.__main__._notify_refresh_ok"),
    ):
        worker.run()

    assert received == [0]
    commands = [call.args[0] for call in run.call_args_list]
    assert ["git", "-C", str(repo), "pull", "--rebase"] in commands
    assert commands[-1] == ["bash", str(repo / "install.sh")]
    assert not any("push" in command for command in commands)  # nothing to push

    # A failing _run_sync is reported as rc 1 rather than raising out of the thread.
    with patch("espansr.__main__._run_sync", side_effect=RuntimeError("boom")):
        worker.run()
    assert received == [0, 1]


def test_repo_sync_button_reports_outcome_in_status_bar(make_window, tmp_path, qtbot):
    _record_fake_checkout(tmp_path)
    window = make_window(Config())

    with (
        patch("subprocess.run", side_effect=_fake_run),
        patch("espansr.__main__.shutil.which", return_value="/usr/bin/git"),
        patch("espansr.__main__.get_platform", return_value="linux"),
        patch("espansr.__main__._notify_refresh_ok"),
        patch.object(window._browser, "refresh"),
    ):
        window._sync_repo_btn.click()
        assert not window._sync_repo_btn.isEnabled()
        qtbot.waitUntil(window._sync_repo_btn.isEnabled, timeout=10000)

    assert window.statusBar().currentMessage() == (
        "Sync complete: pulled latest, pushed local changes, and reinstalled"
    )


# ── :coms popup packet button ────────────────────────────────────────────────


def test_popup_packet_button_opens_dialog_prefilled(qtbot):
    from espansr.core.packets import get_packets_dir
    from espansr.ui.commands_popup import CommandRowWidget, CommandsPopupDialog
    from espansr.ui.packet_dialog import PacketDialog

    entry = CommandCatalogEntry(
        trigger=":research",
        name="Research Report",
        description="research a topic",
        preview="You are research...",
        source="template",
        capability_id="research-report",
        produces=("evidence-report",),
        workflows=("evidence-research-cycle",),
        content="full prompt body",
    )
    with (
        patch("espansr.ui.commands_popup.get_config", return_value=Config()),
        patch("espansr.ui.commands_popup.save_config", return_value=True),
        patch("espansr.ui.commands_popup.load_config_fresh", side_effect=Config),
    ):
        popup = CommandsPopupDialog(entries=[entry], workflow_catalog=WorkflowCatalog())
    qtbot.addWidget(popup)
    popup.show()
    qtbot.waitExposed(popup)

    rows = [row for row in popup.findChildren(CommandRowWidget) if row._entry is entry]
    assert len(rows) == 1
    assert popup.findChild(PacketDialog) is None

    rows[0]._packet_btn.click()

    dialog = popup.findChild(PacketDialog)
    assert dialog is not None
    assert dialog.isVisible()
    assert dialog._artifact_combo.currentText() == "evidence-report"
    assert dialog._base.created_from == "research-report"
    assert dialog._base.workflow == "evidence-research-cycle"
    # Opening the preview persists nothing; only an explicit Save writes a packet.
    assert not get_packets_dir().exists()
