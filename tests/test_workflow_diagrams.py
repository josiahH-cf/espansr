"""Workflow diagram acceptance checks.

Covers manifest layout hints and short edge labels, the deterministic
auto-layout, the interactive diagram widget (nodes, edges, selection,
keyboard), the :coms Processes view drawing diagrams, the scratchpad carrying
the full prompt, and the main window's Workflows panel selecting templates.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from espansr.core.config import Config
from espansr.core.templates import Template, TemplateManager
from espansr.core.workflows import (
    WorkflowCatalog,
    WorkflowEdge,
    WorkflowManifest,
    WorkflowNode,
    load_workflow_catalog,
    validate_manifest_data,
)

pytest.importorskip("PyQt6")

ROOT = Path(__file__).resolve().parents[1]
BUNDLED_WORKFLOWS_DIR = ROOT / "templates" / "_meta" / "workflows"


def _manifest(with_hints=True):
    def node(cap, x, y):
        return WorkflowNode(
            capability=cap, x=x if with_hints else None, y=y if with_hints else None
        )

    return WorkflowManifest(
        id="demo",
        name="Demo",
        entry_points=["a", "b"],
        nodes=[node("a", 0, 0), node("b", 260, 0), node("c", 520, 0), node("ctx", 260, 200)],
        edges=[
            WorkflowEdge(source="a", target="b", label="A to B", short="go"),
            WorkflowEdge(source="b", target="a", label="B back to A", short="back"),
            WorkflowEdge(source="b", target="c", label="B to C", short="on"),
            WorkflowEdge(source="ctx", target="a", label="feed"),
            WorkflowEdge(source="ctx", target="b", label="feed"),
            WorkflowEdge(source="ctx", target="c", label="feed"),
        ],
    )


# ── Manifest model: hints and short labels ───────────────────────────────────


def test_manifest_hints_and_short_labels_roundtrip():
    data = _manifest().to_dict()
    assert data["nodes"][0]["x"] == 0 and data["nodes"][1]["x"] == 260
    assert data["edges"][0]["short"] == "go"
    again = WorkflowManifest.from_dict(data)
    assert again.nodes[1].x == 260 and again.nodes[1].y == 0
    assert again.edges[0].short == "go"
    assert validate_manifest_data(data) == []


def test_manifest_rejects_non_numeric_layout_hints():
    data = _manifest().to_dict()
    data["nodes"][0]["x"] = "left"
    assert any("layout hint" in e for e in validate_manifest_data(data))
    data = _manifest().to_dict()
    data["edges"][0]["short"] = ["not", "a", "string"]
    assert any("short label" in e for e in validate_manifest_data(data))


def test_seed_manifests_carry_hints_and_short_labels():
    for path in BUNDLED_WORKFLOWS_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        for node in data["nodes"]:
            assert isinstance(node.get("x"), (int, float)), f"{path.name}: {node['capability']} x"
            assert isinstance(node.get("y"), (int, float)), f"{path.name}: {node['capability']} y"
        for edge in data["edges"]:
            assert edge.get("short"), f"{path.name}: {edge['source']}->{edge['target']} short"
    catalog = load_workflow_catalog([BUNDLED_WORKFLOWS_DIR])
    assert catalog.errors == []


# ── Layout ───────────────────────────────────────────────────────────────────


def test_layout_uses_hints_when_complete():
    from espansr.ui.workflow_diagram import layout_workflow

    positions = layout_workflow(_manifest())
    assert positions["b"] == (260.0, 0.0)
    assert positions["ctx"] == (260.0, 200.0)


def test_auto_layout_is_deterministic_and_layered():
    from espansr.ui.workflow_diagram import feeder_nodes, layout_workflow

    manifest = _manifest(with_hints=False)
    assert feeder_nodes(manifest) == ["ctx"]
    first = layout_workflow(manifest)
    second = layout_workflow(manifest)
    assert first == second
    assert set(first) == {"a", "b", "c", "ctx"}
    # a precedes b precedes c left-to-right; the feeder sits on its own bottom row.
    assert first["a"][0] < first["b"][0] < first["c"][0]
    assert first["ctx"][1] > max(first["a"][1], first["b"][1], first["c"][1])


# ── Diagram widget ───────────────────────────────────────────────────────────


def test_diagram_draws_nodes_and_edges_and_emits_selection(qtbot):
    from espansr.ui.workflow_diagram import NodeItem, WorkflowDiagramWidget

    widget = WorkflowDiagramWidget()
    qtbot.addWidget(widget)
    received = []
    widget.capability_selected.connect(received.append)
    widget.set_workflow(_manifest(), {"a": ":a", "b": ":b", "c": ":c", "ctx": ":ctx"})

    assert sorted(widget.node_capabilities()) == ["a", "b", "c", "ctx"]
    nodes = [i for i in widget.scene().items() if isinstance(i, NodeItem)]
    assert len(nodes) == 4
    # First entry point is preselected.
    assert widget.selected_capability() == "a"
    assert received == ["a"]

    widget.select_capability("c")
    assert widget.selected_capability() == "c"
    assert received[-1] == "c"


def test_diagram_keyboard_navigation(qtbot):
    from PyQt6.QtCore import Qt

    from espansr.ui.workflow_diagram import WorkflowDiagramWidget

    widget = WorkflowDiagramWidget()
    qtbot.addWidget(widget)
    activated = []
    widget.capability_activated.connect(activated.append)
    widget.set_workflow(_manifest(), {})
    widget.show()
    first = widget.selected_capability()
    qtbot.keyClick(widget, Qt.Key.Key_Tab)
    assert widget.selected_capability() != first
    qtbot.keyClick(widget, Qt.Key.Key_Return)
    assert activated == [widget.selected_capability()]


def test_diagram_palettes_differ_per_theme():
    from espansr.ui.workflow_diagram import DiagramPalette

    dark = DiagramPalette.for_theme("dark")
    light = DiagramPalette.for_theme("light")
    assert dark.background != light.background
    assert dark.text != light.text
    assert DiagramPalette.for_theme("auto") == dark


def test_panel_detail_lists_trigger_and_next_edges(qtbot):
    from espansr.ui.workflow_diagram import CapabilityInfo, WorkflowPanel

    panel = WorkflowPanel()
    qtbot.addWidget(panel)
    infos = [
        CapabilityInfo("a", trigger=":a", name="A", accepts=("x",), produces=("y",), use_when="u"),
        CapabilityInfo("b", trigger=":b", name="B"),
    ]
    panel.set_catalog(WorkflowCatalog(workflows=[_manifest()]), infos)
    text = panel._detail.toPlainText()
    assert ":a" in text
    assert "A to B" in text  # the outgoing edge's full label
    assert ":b" in text  # and the target's trigger
    assert panel.selected_capability() == "a"


# ── :coms integration ────────────────────────────────────────────────────────


def _entries():
    from espansr.core.command_catalog import CommandCatalogEntry

    return [
        CommandCatalogEntry(
            trigger=":a",
            name="Alpha",
            description="alpha",
            preview="p",
            source="template",
            capability_id="a",
            content="FULL PROMPT BODY OF ALPHA",
        ),
        CommandCatalogEntry(
            trigger=":b",
            name="Beta",
            description="beta",
            preview="p",
            source="template",
            capability_id="b",
            content="beta body",
        ),
    ]


def _make_popup(qtbot):
    from espansr.ui.commands_popup import CommandsPopupDialog

    with (
        patch("espansr.ui.commands_popup.get_config", return_value=Config()),
        patch("espansr.ui.commands_popup.save_config", return_value=True),
        patch("espansr.ui.commands_popup.load_config_fresh", side_effect=Config),
    ):
        dialog = CommandsPopupDialog(
            entries=_entries(), workflow_catalog=WorkflowCatalog(workflows=[_manifest()])
        )
    qtbot.addWidget(dialog)
    return dialog


def test_scratchpad_receives_the_full_prompt_not_the_trigger(qtbot):
    dialog = _make_popup(qtbot)
    with (
        patch("espansr.ui.commands_popup.save_config", return_value=True),
        patch("espansr.ui.commands_popup.load_config_fresh", side_effect=Config),
    ):
        dialog._send_to_scratchpad(_entries()[0])
    text = dialog._scratchpad.toPlainText()
    assert "FULL PROMPT BODY OF ALPHA" in text
    assert text.strip() != ":a"


def test_scratchpad_falls_back_to_trigger_for_system_entries(qtbot):
    from espansr.core.command_catalog import CommandCatalogEntry

    dialog = _make_popup(qtbot)
    system = CommandCatalogEntry(":coms", "Commands", "d", "p", "system")
    with (
        patch("espansr.ui.commands_popup.save_config", return_value=True),
        patch("espansr.ui.commands_popup.load_config_fresh", side_effect=Config),
    ):
        dialog._send_to_scratchpad(system)
    assert dialog._scratchpad.toPlainText().strip() == ":coms"


def test_processes_view_shows_interactive_diagram(qtbot):
    from espansr.ui.workflow_diagram import WorkflowPanel

    dialog = _make_popup(qtbot)
    dialog._view_combo.setCurrentText("Processes")
    assert dialog._list.count() == 1
    panel = dialog._workflow_panel
    assert isinstance(panel, WorkflowPanel)
    assert sorted(panel.diagram().node_capabilities()) == ["a", "b", "c", "ctx"]
    assert dialog._summary_table.item(0, 0).text() == "demo"


def test_processes_diagram_actions_use_the_selected_capability(qtbot):
    dialog = _make_popup(qtbot)
    dialog._view_combo.setCurrentText("Processes")
    panel = dialog._workflow_panel
    panel.diagram().select_capability("a")
    with (
        patch("espansr.ui.commands_popup.save_config", return_value=True),
        patch("espansr.ui.commands_popup.load_config_fresh", side_effect=Config),
    ):
        dialog._send_capability_to_scratchpad("a")
        dialog._show_capability_command("b")
    assert "FULL PROMPT BODY OF ALPHA" in dialog._scratchpad.toPlainText()
    assert dialog._view_combo.currentText() == "All Commands"


# ── :aopen (main window) integration ─────────────────────────────────────────


def _make_window(qtbot, tmp_path, config, tm):
    import contextlib

    from espansr.ui.main_window import MainWindow

    with contextlib.ExitStack() as stack:
        stack.enter_context(patch("espansr.ui.main_window.get_config", return_value=config))
        stack.enter_context(patch("espansr.ui.main_window.get_config_manager"))
        stack.enter_context(patch("espansr.ui.main_window.save_config", return_value=True))
        stack.enter_context(
            patch(
                "espansr.ui.main_window.load_workflow_catalog",
                return_value=WorkflowCatalog(workflows=[_manifest()]),
            )
        )
        stack.enter_context(
            patch("espansr.ui.template_browser.get_template_manager", return_value=tm)
        )
        stack.enter_context(patch("espansr.ui.template_browser.get_config"))
        stack.enter_context(patch("espansr.ui.template_editor.get_config"))
        stack.enter_context(
            patch("espansr.ui.template_editor.get_template_manager", return_value=tm)
        )
        stack.enter_context(patch("espansr.integrations.espanso.get_match_dir", return_value=None))
        stack.enter_context(
            patch("espansr.integrations.espanso.get_espanso_config_dir", return_value=tmp_path)
        )
        stack.enter_context(
            patch("espansr.integrations.espanso._get_candidate_paths", return_value=[])
        )
        window = MainWindow()
        qtbot.addWidget(window)
        return window


@pytest.fixture()
def cap_tm(tmp_path):
    tm = TemplateManager(templates_dir=tmp_path / "templates")
    tm.save(Template(name="Alpha Template", content="a", trigger=":a", capability_id="a"))
    tm.save(Template(name="Beta Template", content="b", trigger=":b", capability_id="b"))
    return tm


def test_main_window_workflows_panel_hidden_by_default(qtbot, tmp_path, cap_tm):
    window = _make_window(qtbot, tmp_path, Config(), cap_tm)
    assert not window._workflow_panel.isVisibleTo(window)
    assert "Show Workflows" in window._workflows_toggle_btn.text()


def test_main_window_toggle_shows_panel_and_persists(qtbot, tmp_path, cap_tm):
    config = Config()
    window = _make_window(qtbot, tmp_path, config, cap_tm)
    with (
        patch("espansr.ui.main_window.save_config", return_value=True) as save_mock,
        patch(
            "espansr.ui.main_window.load_workflow_catalog",
            return_value=WorkflowCatalog(workflows=[_manifest()]),
        ),
    ):
        window._toggle_workflows()
    assert window._workflow_panel.isVisibleTo(window)
    assert config.ui.show_workflows is True
    assert "Hide Workflows" in window._workflows_toggle_btn.text()
    save_mock.assert_called()


def test_main_window_shortcut_binding(qtbot, tmp_path, cap_tm):
    from PyQt6.QtGui import QKeySequence

    window = _make_window(qtbot, tmp_path, Config(), cap_tm)
    assert window._shortcut_workflows.key() == QKeySequence("Ctrl+Shift+W")


def test_main_window_node_click_selects_template(qtbot, tmp_path, cap_tm):
    config = Config()
    config.ui.show_workflows = True
    window = _make_window(qtbot, tmp_path, config, cap_tm)
    assert window._workflow_panel.isVisibleTo(window)
    window._workflow_panel.diagram().select_capability("b")
    current = window._browser.get_current_template()
    assert current is not None and current.name == "Beta Template"
    assert window._editor._name_edit.text() == "Beta Template"


def test_main_window_panel_startup_from_config(qtbot, tmp_path, cap_tm):
    config = Config()
    config.ui.show_workflows = True
    window = _make_window(qtbot, tmp_path, config, cap_tm)
    assert window._workflow_panel_loaded is True
    assert sorted(window._workflow_panel.diagram().node_capabilities()) == ["a", "b", "c", "ctx"]
