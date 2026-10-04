"""Shared drag handles and local pane-size restoration for desktop windows."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QSplitter


def prepare_splitter(splitter: QSplitter, label: str, sizes) -> None:
    """Keep panes usable and give their resize handles a clear affordance."""
    splitter.setChildrenCollapsible(False)
    splitter.setHandleWidth(8)
    splitter.setAccessibleName(label)
    cursor = (
        Qt.CursorShape.SplitHCursor
        if splitter.orientation() == Qt.Orientation.Horizontal
        else Qt.CursorShape.SplitVCursor
    )
    for index in range(1, splitter.count()):
        handle = splitter.handle(index)
        handle.setCursor(cursor)
        handle.setToolTip("Drag to resize panes")
        handle.setAccessibleName(f"Resize {label}")
    restore_splitter_sizes(splitter, sizes)


def restore_splitter_sizes(splitter: QSplitter, sizes) -> None:
    """Apply saved proportions after layout without accepting invalid Qt integers."""
    if (
        isinstance(sizes, list)
        and len(sizes) == splitter.count()
        and all(type(size) is int and 0 < size < 2**31 for size in sizes)
    ):
        splitter.setSizes(sizes)


def panel_sizes(saved, key: str, default: list[int]) -> list[int]:
    """Old or malformed config should leave the default layout usable."""
    return saved.get(key, default) if isinstance(saved, dict) else default


def capture_panel_sizes(splitters: dict[str, QSplitter], previous) -> dict:
    """Retain expanded sizes when a panel is temporarily hidden."""
    result = dict(previous) if isinstance(previous, dict) else {}
    for name, splitter in splitters.items():
        sizes = splitter.sizes()
        if len(sizes) > 1 and all(size > 0 for size in sizes):
            result[name] = sizes
    return result
