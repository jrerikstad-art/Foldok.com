"""Snapping — pointer geometry to grid geometry.

This is the authority.  ``editor/foldok-box-editor.js`` mirrors these rules
exactly and does no geometry of its own, so the ghost the user drags is the box
they get, and the box they get is what the PDF prints.  If the two ever
disagree, the canvas is lying and the test in parity.py fails.

One decision worth stating: **the north handles change height, they do not move
the box.**  In a flowed document a block's top edge is decided by what is above
it, so dragging it upward cannot move it — pretending otherwise is the kind of
small lie that makes an editor feel untrustworthy.  To move a block you drag its
body, which is the Word and InDesign convention anyway.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .model import HANDLES, Box, Geometry, PageGrid, PlacedBox

MIN_SPAN = 1
GRAB = 6.0                    # handle hit tolerance in points


@dataclass
class SnapResult:
    col: int
    span: int
    rows: int | None
    changed: tuple[str, ...] = ()
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"col": self.col, "span": self.span, "changed": list(self.changed)}
        if self.rows is not None:
            d["rows"] = self.rows
        if self.note:
            d["note"] = self.note
        return d


def resize(
    placed: PlacedBox,
    handle: str,
    dx: float,
    dy: float,
    grid: PageGrid,
    *,
    aspect: float | None = None,
    min_span: int = MIN_SPAN,
    max_span: int | None = None,
) -> SnapResult:
    """A drag on ``handle`` by (dx, dy) points, snapped to the grid."""
    if handle not in HANDLES:
        raise ValueError(f"unknown handle '{handle}'; expected one of {HANDLES}")
    max_span = min(max_span or grid.columns, grid.columns)

    left = placed.x
    right = placed.x + placed.width
    col, span = placed.col, placed.span
    rows: int | None = placed.rows
    changed: list[str] = []
    note = ""

    if "e" in handle:
        new_right = right + dx
        span = grid.span_at(max(grid.column_width, new_right - left))
        span = max(min_span, min(span, max_span, grid.columns - col))
        if span != placed.span:
            changed.append("span")
    if "w" in handle:
        new_left = left + dx
        new_col = grid.col_at(new_left)
        new_col = max(0, min(new_col, col + span - min_span))
        new_span = grid.span_at(max(grid.column_width, right - grid.column_x(new_col)))
        new_span = max(min_span, min(new_span, max_span, grid.columns - new_col))
        if new_col != col:
            changed.append("col")
        if new_span != span:
            changed.append("span")
        col, span = new_col, new_span

    if aspect:
        rows = max(1, round(grid.span_width(span) / aspect / grid.baseline))
        if "rows" not in changed:
            changed.append("rows")
        note = "aspect locked"
    elif "n" in handle or "s" in handle:
        delta = dy if "s" in handle else -dy
        new_h = max(grid.baseline, placed.height + delta)
        rows = max(1, int(round(new_h / grid.baseline)))
        if rows != placed.rows:
            changed.append("rows")
        if "n" in handle:
            note = "height only — a block's top edge follows the flow"

    return SnapResult(col=col, span=span, rows=rows, changed=tuple(dict.fromkeys(changed)), note=note)


def snap_rect(
    x: float,
    y: float,
    width: float,
    height: float,
    grid: PageGrid,
    *,
    min_span: int = MIN_SPAN,
    max_span: int | None = None,
) -> SnapResult:
    """Free rectangle in points to the nearest legal grid box."""
    max_span = min(max_span or grid.columns, grid.columns)
    col = grid.col_at(x)
    span = max(min_span, min(grid.span_at(width), max_span, grid.columns - col))
    rows = max(1, int(round(max(grid.baseline, height) / grid.baseline)))
    return SnapResult(col=col, span=span, rows=rows, changed=("col", "span", "rows"))


def ghost(placed: PlacedBox, result: SnapResult, grid: PageGrid) -> PlacedBox:
    """Exactly what the box will look like if the drag is released now."""
    rows = result.rows if result.rows is not None else placed.rows
    return PlacedBox(
        block_id=placed.block_id,
        page=placed.page,
        row=placed.row,
        col=result.col,
        span=result.span,
        rows=rows,
        x=grid.column_x(result.col),
        y=placed.y,
        width=grid.span_width(result.span),
        height=rows * grid.baseline,
        role=placed.role,
        align=placed.align,
        pinned=placed.pinned,
    )


def handle_at(geometry: Geometry, page: int, x: float, y: float, tolerance: float = GRAB) -> tuple[str, str] | None:
    """(block_id, handle) under the pointer, topmost first."""
    for box in reversed(geometry.on_page(page)):
        h = box.handle_at(x, y, tolerance)
        if h:
            return (box.block_id, h)
    return None


def block_at(geometry: Geometry, page: int, x: float, y: float) -> str | None:
    box = geometry.at(page, x, y)
    return box.block_id if box else None


@dataclass
class DropTarget:
    before_block_id: str | None      # None = append at end of page
    col: int
    side: str                        # "above" | "below" | "beside"

    def to_dict(self) -> dict[str, Any]:
        return {"before_block_id": self.before_block_id, "col": self.col, "side": self.side}


def drop_target(
    geometry: Geometry,
    page: int,
    x: float,
    y: float,
    *,
    dragging: str | None = None,
) -> DropTarget:
    """Where a dragged block would land.

    Dropping on the left or right third of an existing box means "beside it" —
    that is how a two-column band gets made, without a separate grouping gesture.
    """
    grid = geometry.grid
    boxes = [b for b in geometry.on_page(page) if b.block_id != dragging]
    if not boxes:
        return DropTarget(None, 0, "below")

    target = geometry.at(page, x, y)
    if target is not None and target.block_id != dragging:
        third = target.width / 3.0
        if x < target.x + third and target.col > 0:
            return DropTarget(target.block_id, max(0, target.col - 1), "beside")
        if x > target.x + target.width - third and target.col + target.span < grid.columns:
            return DropTarget(target.block_id, target.col + target.span, "beside")
        below = y > target.y + target.height / 2
        after = _next_of(boxes, target.block_id)
        return (
            DropTarget(after, target.col, "below") if below
            else DropTarget(target.block_id, target.col, "above")
        )

    nearest = min(boxes, key=lambda b: abs((b.y + b.height / 2) - y))
    if y > nearest.y + nearest.height / 2:
        return DropTarget(_next_of(boxes, nearest.block_id), grid.col_at(x), "below")
    return DropTarget(nearest.block_id, grid.col_at(x), "above")


def _next_of(boxes: list[PlacedBox], block_id: str) -> str | None:
    ordered = sorted(boxes, key=lambda b: (b.y, b.col))
    for i, b in enumerate(ordered):
        if b.block_id == block_id:
            return ordered[i + 1].block_id if i + 1 < len(ordered) else None
    return None


def cursor_for(handle: str | None, over_block: bool) -> str:
    if handle in ("e", "w"):
        return "ew-resize"
    if handle in ("n", "s"):
        return "ns-resize"
    if handle in ("nw", "se"):
        return "nwse-resize"
    if handle in ("ne", "sw"):
        return "nesw-resize"
    return "move" if over_block else "default"
