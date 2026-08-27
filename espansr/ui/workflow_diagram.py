"""Workflow diagrams for the :coms popup and the main editor window.

Draws a workflow manifest as an interactive graph on a ``QGraphicsScene``:
capability nodes with their triggers, labeled arrows for the optional
relationships, cycle (revisit) edges in the accent color, and any
"feeds every node" source — such as ``context-reset`` — as a dashed node with
a single dashed arrow instead of one arrow per target.

Layout comes from optional ``x``/``y`` hints on manifest nodes; when a manifest
carries none, a deterministic layered auto-layout is used so user-authored
workflows render too. The diagram is a view over the manifests: clicking a
node only selects it and emits a signal — nothing here ever runs a prompt.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)
from PyQt6.QtWidgets import (
    QComboBox,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsPolygonItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from espansr.core.workflows import WorkflowCatalog, WorkflowEdge, WorkflowManifest

NODE_WIDTH = 160.0
NODE_HEIGHT = 56.0
COLUMN_GAP = 240.0
ROW_GAP = 100.0
MARGIN = 24.0


@dataclass(frozen=True)
class DiagramPalette:
    """Colors for one theme. Mirrors the app stylesheet's dark/light grounds."""

    background: str
    surface: str
    line: str
    text: str
    muted: str
    accent: str
    feeder: str

    @classmethod
    def for_theme(cls, theme: str) -> "DiagramPalette":
        if (theme or "dark").lower() == "light":
            return cls(
                background="#f5f5f5",
                surface="#ffffff",
                line="#7a7a7a",
                text="#1e1e1e",
                muted="#5c5c5c",
                accent="#0e639c",
                feeder="#6a58a8",
            )
        return cls(
            background="#1e1e1e",
            surface="#2d2d2d",
            line="#9a9a9a",
            text="#d4d4d4",
            muted="#9a9a9a",
            accent="#5aa9e6",
            feeder="#9f8fd0",
        )


# ── Layout ───────────────────────────────────────────────────────────────────


def feeder_nodes(manifest: WorkflowManifest) -> List[str]:
    """Nodes whose outgoing edges reach every other node (e.g. context-reset).

    These are drawn once, dashed, with a single "feeds any node" arrow rather
    than one arrow per target — the diagram shows the mechanism, not noise.
    """
    ids = manifest.node_ids()
    if len(ids) < 3:
        return []
    feeders = []
    for node_id in ids:
        targets = {e.target for e in manifest.edges if e.source == node_id}
        if targets >= (set(ids) - {node_id}):
            feeders.append(node_id)
    return feeders


def _cycle_edges(manifest: WorkflowManifest) -> set:
    """Edges that close a loop: (a→b) when (b→a) also exists."""
    pairs = {(e.source, e.target) for e in manifest.edges}
    return {(s, t) for (s, t) in pairs if (t, s) in pairs}


def layout_workflow(manifest: WorkflowManifest) -> Dict[str, Tuple[float, float]]:
    """Return ``{capability: (x, y)}`` for every node.

    Uses the manifest's ``x``/``y`` hints when every node has them; otherwise
    computes a deterministic layered layout: entry points first, then layers
    by longest forward path (cycle edges ignored for layering), feeders on a
    bottom row of their own.
    """
    nodes = manifest.nodes
    if nodes and all(n.x is not None and n.y is not None for n in nodes):
        return {n.capability: (float(n.x), float(n.y)) for n in nodes}

    ids = manifest.node_ids()
    feeders = set(feeder_nodes(manifest))
    cycle = _cycle_edges(manifest)
    forward = [
        e
        for e in manifest.edges
        if e.source not in feeders and e.target not in feeders and (e.source, e.target) not in cycle
    ]
    # Also keep one direction of each cycle pair (deterministic: the one whose
    # source sorts first) so mutually-linked nodes still order left to right.
    for s, t in sorted(cycle):
        if s < t and s not in feeders and t not in feeders:
            forward.append(WorkflowEdge(source=s, target=t))

    layer: Dict[str, int] = {n: 0 for n in ids if n not in feeders}
    # Longest-path layering with a bounded relaxation (graph is small).
    for _ in range(len(layer) + 1):
        changed = False
        for e in forward:
            if e.source in layer and e.target in layer and layer[e.target] < layer[e.source] + 1:
                layer[e.target] = layer[e.source] + 1
                changed = True
        if not changed:
            break

    columns: Dict[int, List[str]] = {}
    for node_id in ids:
        if node_id in feeders:
            continue
        columns.setdefault(layer[node_id], []).append(node_id)

    positions: Dict[str, Tuple[float, float]] = {}
    tallest = max((len(col) for col in columns.values()), default=1)
    for col_index in sorted(columns):
        col = columns[col_index]
        offset = (tallest - len(col)) * ROW_GAP / 2
        for row, node_id in enumerate(col):
            positions[node_id] = (MARGIN + col_index * COLUMN_GAP, MARGIN + offset + row * ROW_GAP)

    bottom = MARGIN + tallest * ROW_GAP + 20
    width_cols = max(len(columns), 1)
    for i, node_id in enumerate(sorted(feeders)):
        x = MARGIN + (width_cols - 1) * COLUMN_GAP / 2 + i * COLUMN_GAP
        positions[node_id] = (x, bottom)
    return positions


# ── Scene items ──────────────────────────────────────────────────────────────


class NodeItem(QGraphicsRectItem):
    """A capability node; selecting it notifies the owning widget."""

    def __init__(self, capability: str, rect: QRectF, widget: "WorkflowDiagramWidget"):
        super().__init__(rect)
        self.capability = capability
        self._widget = widget
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._widget.select_capability(self.capability)
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._widget.select_capability(self.capability)
        self._widget.capability_activated.emit(self.capability)
        event.accept()

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self._widget.select_capability(self.capability)
            self._widget.capability_activated.emit(self.capability)
            event.accept()
            return
        super().keyPressEvent(event)

    def focusInEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._widget.select_capability(self.capability)
        super().focusInEvent(event)


class WorkflowDiagramWidget(QGraphicsView):
    """Interactive graph of one workflow manifest."""

    capability_selected = pyqtSignal(str)
    capability_activated = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None, theme: str = "dark"):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumHeight(240)
        self._palette = DiagramPalette.for_theme(theme)
        self._manifest: Optional[WorkflowManifest] = None
        self._trigger_lookup: Dict[str, str] = {}
        self._nodes: Dict[str, NodeItem] = {}
        self._selected: Optional[str] = None
        self.setBackgroundBrush(QBrush(QColor(self._palette.background)))

    # ── Public API ─────────────────────────────────────────────────────────

    def set_theme(self, theme: str) -> None:
        self._palette = DiagramPalette.for_theme(theme)
        self.setBackgroundBrush(QBrush(QColor(self._palette.background)))
        if self._manifest is not None:
            self.set_workflow(self._manifest, self._trigger_lookup)

    def set_workflow(
        self, manifest: WorkflowManifest, trigger_lookup: Optional[Dict[str, str]] = None
    ) -> None:
        """Rebuild the scene for *manifest*. Triggers are looked up by capability ID."""
        self._manifest = manifest
        self._trigger_lookup = dict(trigger_lookup or {})
        self._scene.clear()
        self._nodes = {}
        previous = self._selected
        self._selected = None

        positions = layout_workflow(manifest)
        feeders = set(feeder_nodes(manifest))
        cycle = _cycle_edges(manifest)
        rects = {cap: QRectF(x, y, NODE_WIDTH, NODE_HEIGHT) for cap, (x, y) in positions.items()}

        for edge in manifest.edges:
            if edge.source in feeders:
                continue  # drawn once below as the feeder arrow
            if edge.source not in rects or edge.target not in rects:
                continue
            obstacles = [r for cap, r in rects.items() if cap not in (edge.source, edge.target)]
            self._draw_edge(
                rects[edge.source],
                rects[edge.target],
                edge,
                edge_is_cycle=((edge.source, edge.target) in cycle),
                obstacles=obstacles,
            )

        for feeder in feeders:
            if feeder not in rects:
                continue
            self._draw_feeder_arrow(rects[feeder], rects)

        for cap, rect in rects.items():
            self._draw_node(cap, rect, dashed=cap in feeders)

        self._scene.setSceneRect(self._scene.itemsBoundingRect().adjusted(-16, -16, 16, 16))
        self._fit()
        if previous in self._nodes:
            self.select_capability(previous)
        elif manifest.entry_points and manifest.entry_points[0] in self._nodes:
            self.select_capability(manifest.entry_points[0])

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        self._fit()

    def _fit(self) -> None:
        """Scale the whole graph into view when it is larger than the viewport;
        never upscale a small graph."""
        rect = self._scene.sceneRect()
        if rect.isEmpty():
            return
        self.resetTransform()
        viewport = self.viewport().rect()
        if rect.width() > viewport.width() or rect.height() > viewport.height():
            self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    def select_capability(self, capability: str) -> None:
        if capability not in self._nodes:
            return
        for cap, item in self._nodes.items():
            pen = item.pen()
            pen.setWidthF(2.4 if cap == capability else 1.2)
            pen.setColor(
                QColor(self._palette.accent) if cap == capability else QColor(self._palette.line)
            )
            item.setPen(pen)
        changed = capability != self._selected
        self._selected = capability
        if changed:
            self.capability_selected.emit(capability)

    def selected_capability(self) -> Optional[str]:
        return self._selected

    def node_capabilities(self) -> List[str]:
        return list(self._nodes)

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Tab / Shift+Tab move between nodes; Enter activates the selection."""
        caps = list(self._nodes)
        if not caps:
            super().keyPressEvent(event)
            return
        if event.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            index = caps.index(self._selected) if self._selected in caps else -1
            step = -1 if event.key() == Qt.Key.Key_Backtab else 1
            self.select_capability(caps[(index + step) % len(caps)])
            event.accept()
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self._selected:
            self.capability_activated.emit(self._selected)
            event.accept()
            return
        super().keyPressEvent(event)

    # ── Drawing ────────────────────────────────────────────────────────────

    def _draw_node(self, capability: str, rect: QRectF, dashed: bool) -> None:
        item = NodeItem(capability, rect, self)
        pen = QPen(QColor(self._palette.line), 1.2)
        if dashed:
            pen.setStyle(Qt.PenStyle.DashLine)
        item.setPen(pen)
        item.setBrush(QBrush(QColor(self._palette.surface)))
        item.setToolTip(self._trigger_lookup.get(capability, capability))
        self._scene.addItem(item)
        self._nodes[capability] = item

        title = QGraphicsSimpleTextItem(capability, item)
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setBrush(QBrush(QColor(self._palette.text)))
        title.setPos(rect.x() + (NODE_WIDTH - title.boundingRect().width()) / 2, rect.y() + 10)

        trigger = self._trigger_lookup.get(capability, "(no template)")
        sub = QGraphicsSimpleTextItem(trigger, item)
        sub_font = QFont("IBM Plex Mono, Consolas, monospace")
        sub_font.setPointSize(9)
        sub.setFont(sub_font)
        sub.setBrush(QBrush(QColor(self._palette.muted)))
        sub.setPos(rect.x() + (NODE_WIDTH - sub.boundingRect().width()) / 2, rect.y() + 32)

    @staticmethod
    def _anchor(rect: QRectF, toward: QPointF) -> QPointF:
        """Point on *rect*'s border facing *toward*."""
        center = rect.center()
        dx, dy = toward.x() - center.x(), toward.y() - center.y()
        if dx == 0 and dy == 0:
            return center
        half_w, half_h = rect.width() / 2, rect.height() / 2
        scale = min(
            half_w / abs(dx) if dx else float("inf"),
            half_h / abs(dy) if dy else float("inf"),
        )
        return QPointF(center.x() + dx * scale, center.y() + dy * scale)

    @staticmethod
    def _segment_hits(start: QPointF, end: QPointF, obstacles: List[QRectF]) -> bool:
        """True when the straight segment passes through any obstacle rect."""
        steps = 24
        for i in range(1, steps):
            t = i / steps
            point = QPointF(
                start.x() + (end.x() - start.x()) * t, start.y() + (end.y() - start.y()) * t
            )
            if any(r.adjusted(-4, -4, 4, 4).contains(point) for r in obstacles):
                return True
        return False

    def _draw_edge(
        self,
        src: QRectF,
        dst: QRectF,
        edge: WorkflowEdge,
        edge_is_cycle: bool,
        obstacles: Optional[List[QRectF]] = None,
    ) -> None:
        color = QColor(self._palette.accent if edge_is_cycle else self._palette.line)
        start = self._anchor(src, dst.center())
        end = self._anchor(dst, src.center())
        mid = QPointF((start.x() + end.x()) / 2, (start.y() + end.y()) / 2)
        dx, dy = end.x() - start.x(), end.y() - start.y()
        length = max((dx * dx + dy * dy) ** 0.5, 1.0)
        nx, ny = -dy / length, dx / length  # left normal
        path = QPainterPath(start)
        if edge_is_cycle:
            # Bow the two directions apart so a loop reads as two arrows.
            control = QPointF(mid.x() + nx * 34, mid.y() + ny * 34)
            path.quadTo(control, end)
            apex = path.pointAtPercent(0.5)
            label_pos = QPointF(apex.x() + nx * 12, apex.y() + ny * 12)
        elif obstacles and self._segment_hits(start, end, obstacles):
            # Bow around whatever sits on the straight line, on the side
            # whose control point is farther from every obstacle.
            def clearance(sign: float) -> float:
                c = QPointF(mid.x() + nx * 70 * sign, mid.y() + ny * 70 * sign)
                return min(((c - r.center()).manhattanLength() for r in obstacles), default=0)

            sign = 1.0 if clearance(1.0) >= clearance(-1.0) else -1.0
            control = QPointF(mid.x() + nx * 120 * sign, mid.y() + ny * 120 * sign)
            path.quadTo(control, end)
            apex = path.pointAtPercent(0.5)
            label_pos = QPointF(apex.x() + nx * 12 * sign, apex.y() + ny * 12 * sign)
        else:
            path.lineTo(end)
            along = path.pointAtPercent(0.4)
            label_pos = QPointF(along.x() + nx * 11, along.y() + ny * 11)

        line = QGraphicsPathItem(path)
        line.setPen(QPen(color, 1.8 if edge_is_cycle else 1.2))
        line.setZValue(-1)
        line.setToolTip(edge.label or edge.short)
        self._scene.addItem(line)
        self._draw_arrowhead(path, color)

        if edge.short:
            text = QGraphicsSimpleTextItem(edge.short)
            font = QFont()
            font.setPointSize(8)
            text.setFont(font)
            text.setBrush(QBrush(color if edge_is_cycle else QColor(self._palette.muted)))
            box = text.boundingRect()
            text.setPos(label_pos.x() - box.width() / 2, label_pos.y() - box.height() / 2 - 8)
            text.setToolTip(edge.label)
            text.setZValue(2)
            self._scene.addItem(text)

    def _draw_feeder_arrow(self, feeder: QRectF, rects: Dict[str, QRectF]) -> None:
        others = [r for cap, r in rects.items() if r is not feeder]
        if not others:
            return
        # Aim at the nearest node's bottom edge, dashed, once.
        target_rect = min(others, key=lambda r: (r.center() - feeder.center()).manhattanLength())
        start = self._anchor(feeder, target_rect.center())
        end = self._anchor(target_rect, feeder.center())
        path = QPainterPath(start)
        path.lineTo(end)
        color = QColor(self._palette.feeder)
        line = QGraphicsPathItem(path)
        pen = QPen(color, 1.4)
        pen.setStyle(Qt.PenStyle.DashLine)
        line.setPen(pen)
        line.setZValue(-1)
        line.setToolTip(
            "Feeds any node: use the compact context as the input to whichever you pick."
        )
        self._scene.addItem(line)
        self._draw_arrowhead(path, color)
        text = QGraphicsSimpleTextItem("feeds any node")
        font = QFont()
        font.setPointSize(8)
        text.setFont(font)
        text.setBrush(QBrush(color))
        mid = QPointF((start.x() + end.x()) / 2 + 8, (start.y() + end.y()) / 2)
        text.setPos(mid)
        self._scene.addItem(text)

    def _draw_arrowhead(self, path: QPainterPath, color: QColor) -> None:
        end = path.pointAtPercent(1.0)
        before = path.pointAtPercent(0.97)
        dx, dy = end.x() - before.x(), end.y() - before.y()
        length = max((dx * dx + dy * dy) ** 0.5, 1.0)
        ux, uy = dx / length, dy / length
        size = 8.0
        left = QPointF(
            end.x() - ux * size - uy * size * 0.55, end.y() - uy * size + ux * size * 0.55
        )
        right = QPointF(
            end.x() - ux * size + uy * size * 0.55, end.y() - uy * size - ux * size * 0.55
        )
        head = QGraphicsPolygonItem(QPolygonF([end, left, right]))
        head.setBrush(QBrush(color))
        head.setPen(QPen(color, 1))
        head.setZValue(-1)
        self._scene.addItem(head)


# ── Composite panel ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CapabilityInfo:
    """What the detail panel knows about one capability (from the templates)."""

    capability_id: str
    trigger: str = ""
    name: str = ""
    accepts: Tuple[str, ...] = ()
    produces: Tuple[str, ...] = ()
    use_when: str = ""
    avoid_when: str = ""


class WorkflowPanel(QWidget):
    """Workflow picker + interactive diagram + detail text + host actions.

    ``actions`` is a list of ``(label, callable(capability_id))`` pairs the
    host supplies; the panel never executes anything on its own.
    """

    capability_selected = pyqtSignal(str)
    capability_activated = pyqtSignal(str)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        theme: str = "dark",
        actions: Optional[Sequence[Tuple[str, Callable[[str], None]]]] = None,
    ):
        super().__init__(parent)
        self._catalog: Optional[WorkflowCatalog] = None
        self._info: Dict[str, CapabilityInfo] = {}
        self._actions = list(actions or [])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.addWidget(QLabel("Process:"))
        self._workflow_combo = QComboBox()
        self._workflow_combo.currentIndexChanged.connect(self._on_workflow_changed)
        header.addWidget(self._workflow_combo, 1)
        hint = QLabel("Click a node · Tab moves · Enter opens — nothing runs automatically")
        hint.setWordWrap(True)
        header.addWidget(hint, 2)
        layout.addLayout(header)

        self._diagram = WorkflowDiagramWidget(theme=theme)
        self._diagram.capability_selected.connect(self._on_capability_selected)
        self._diagram.capability_activated.connect(self.capability_activated.emit)
        layout.addWidget(self._diagram, 1)

        self._detail = QTextBrowser()
        self._detail.setOpenExternalLinks(False)
        self._detail.setMaximumHeight(150)
        self._detail.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self._detail)

        self._action_row = QHBoxLayout()
        self._action_buttons: List[QPushButton] = []
        for label, handler in self._actions:
            button = QPushButton(label)
            button.clicked.connect(self._make_action(handler))
            self._action_row.addWidget(button)
            self._action_buttons.append(button)
        self._action_row.addStretch()
        layout.addLayout(self._action_row)

    def _make_action(self, handler: Callable[[str], None]):
        def _run() -> None:
            cap = self._diagram.selected_capability()
            if cap:
                handler(cap)

        return _run

    # ── Public API ─────────────────────────────────────────────────────────

    def set_catalog(
        self, catalog: WorkflowCatalog, infos: Sequence[CapabilityInfo], theme: Optional[str] = None
    ) -> None:
        """Load workflows plus the template-derived info used for triggers/details."""
        self._catalog = catalog
        self._info = {i.capability_id: i for i in infos}
        if theme is not None:
            self._diagram.set_theme(theme)
        self._workflow_combo.blockSignals(True)
        self._workflow_combo.clear()
        for workflow in catalog.workflows:
            self._workflow_combo.addItem(workflow.name, workflow.id)
        self._workflow_combo.blockSignals(False)
        if catalog.workflows:
            self._on_workflow_changed(0)
        else:
            self._detail.setHtml("No workflow manifests found.")

    def show_workflow(self, workflow_id: str) -> None:
        index = self._workflow_combo.findData(workflow_id)
        if index >= 0:
            self._workflow_combo.setCurrentIndex(index)

    def current_workflow(self) -> Optional[WorkflowManifest]:
        if self._catalog is None:
            return None
        return self._catalog.get(self._workflow_combo.currentData() or "")

    def diagram(self) -> WorkflowDiagramWidget:
        return self._diagram

    def selected_capability(self) -> Optional[str]:
        return self._diagram.selected_capability()

    def info_for(self, capability: str) -> Optional[CapabilityInfo]:
        return self._info.get(capability)

    # ── Internals ──────────────────────────────────────────────────────────

    def _on_workflow_changed(self, index: int) -> None:
        workflow = self.current_workflow()
        if workflow is None:
            return
        lookup = {cap: info.trigger for cap, info in self._info.items() if info.trigger}
        self._diagram.set_workflow(workflow, lookup)
        selected = self._diagram.selected_capability()
        if selected:
            self._on_capability_selected(selected)

    def _on_capability_selected(self, capability: str) -> None:
        workflow = self.current_workflow()
        info = self._info.get(capability)
        parts = [f"<b>{capability}</b>"]
        if info and info.trigger:
            parts[0] += f" &nbsp;·&nbsp; type <code>{info.trigger}</code> anywhere"
        if info:
            if info.accepts:
                parts.append(f"<i>accepts</i> {', '.join(info.accepts)}")
            if info.produces:
                parts.append(f"<i>produces</i> {', '.join(info.produces)}")
            if info.use_when:
                parts.append(f"<i>use when</i> {info.use_when}")
            if info.avoid_when:
                parts.append(f"<i>avoid when</i> {info.avoid_when}")
        else:
            parts.append("<i>no template with this capability ID is installed</i>")
        if workflow is not None:
            nexts = [e for e in workflow.edges if e.source == capability]
            if nexts:
                lines = []
                for e in nexts:
                    target_info = self._info.get(e.target)
                    trig = (
                        f" ({target_info.trigger})" if target_info and target_info.trigger else ""
                    )
                    lines.append(f"→ {e.target}{trig}" + (f" — {e.label}" if e.label else ""))
                parts.append("<i>optional next</i><br>" + "<br>".join(lines))
        self._detail.setHtml("<br>".join(parts))
        self.capability_selected.emit(capability)


def capability_infos_from_templates(templates) -> List[CapabilityInfo]:
    """Build detail info from Template objects (browser/editor side)."""
    from espansr.core.capabilities import effective_capability_id

    infos = []
    for t in templates:
        infos.append(
            CapabilityInfo(
                capability_id=effective_capability_id(t),
                trigger=t.trigger or "",
                name=t.name,
                accepts=tuple(t.accepts or ()),
                produces=tuple(t.produces or ()),
                use_when=t.use_when or "",
                avoid_when=t.avoid_when or "",
            )
        )
    return infos


def capability_infos_from_entries(entries) -> List[CapabilityInfo]:
    """Build detail info from command-catalog entries (:coms side)."""
    infos = []
    for e in entries:
        if not e.capability_id:
            continue
        infos.append(
            CapabilityInfo(
                capability_id=e.capability_id,
                trigger=e.trigger,
                name=e.name,
                accepts=tuple(e.accepts),
                produces=tuple(e.produces),
                use_when=e.use_when,
                avoid_when=e.avoid_when,
            )
        )
    return infos
