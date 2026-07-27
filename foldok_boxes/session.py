"""The editing session — what a pointer gesture turns into.

Every gesture becomes either a pin (how it is drawn) or an order change (where it
sits in the document).  Nothing becomes raw geometry, which is what keeps the
flow intact and the PDF honest.

    drag body            -> move(before=..., col=...)      order + col pins
    drag corner/edge     -> resize(handle, dx, dy)         col/span/rows pins
    double-click a box   -> release(block)                 back to the template
    lock icon            -> lock(block)                    frozen against promotion
    "Save as my layout"  -> promote_to_template()          the template learns

``history`` records every change with a human-readable summary, so the version
drawer the spec asks for is a read of this list, and layout edits are as
revertable as text edits.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Sequence

from .flow import BlockInput, Measurer, SimpleMeasurer, solve
from .model import Box, Geometry, PageGrid, PlacedBox
from .pins import GLOBAL_SCOPE, PinStore
from .snap import DropTarget, SnapResult, drop_target, ghost, resize as snap_resize
from .template import LayoutTemplate, compliance_a4


class LayoutRefused(Exception):
    """The edit is not allowed, with the reason in the message."""


@dataclass
class Change:
    action: str
    block_id: str
    summary: str
    detail: dict[str, Any] = field(default_factory=dict)
    at: float = 0.0

    def __str__(self) -> str:
        return self.summary


class LayoutSession:
    def __init__(
        self,
        blocks: Sequence[BlockInput],
        template: LayoutTemplate | None = None,
        grid: PageGrid | None = None,
        pins: PinStore | None = None,
        measurer: Measurer | None = None,
        clock=time.time,
    ) -> None:
        self.blocks = list(blocks)
        self.template = template or compliance_a4()
        self.grid = grid or PageGrid(columns=self.template.columns, page_size=self.template.page_size)
        self.pins = pins or PinStore()
        self.measurer = measurer or SimpleMeasurer()
        self.history: list[Change] = []
        self.selection: list[str] = []
        self._clock = clock
        self._geometry: Geometry | None = None

    # -- derived ---------------------------------------------------------
    def invalidate(self) -> None:
        self._geometry = None

    def geometry(self) -> Geometry:
        if self._geometry is None:
            self._geometry = solve(
                self.blocks,
                self.grid,
                self.pins,
                self.template.defaults_for(self.blocks, self.grid),
                self.measurer,
            )
        return self._geometry

    def placed(self, block_id: str) -> PlacedBox:
        box = self.geometry().of(block_id)
        if box is None:
            raise LayoutRefused(f"'{block_id}' is not visible in this document")
        return box

    def block(self, block_id: str) -> BlockInput:
        for b in self.blocks:
            if b.id == block_id:
                return b
        raise LayoutRefused(f"no block '{block_id}'")

    def _log(self, action: str, block_id: str, summary: str, **detail: Any) -> Change:
        c = Change(action, block_id, summary, detail, self._clock())
        self.history.append(c)
        return c

    def _guard(self, block_id: str) -> None:
        if self.template.is_locked(block_id) or self.block(block_id).locked:
            raise LayoutRefused(
                f"'{block_id}' is a locked block — boilerplate and legal text keep their "
                "layout so the document stays comparable across jobs"
            )

    # -- selection -------------------------------------------------------
    def select(self, *block_ids: str, add: bool = False) -> list[str]:
        if add:
            for b in block_ids:
                if b not in self.selection:
                    self.selection.append(b)
        else:
            self.selection = list(block_ids)
        return self.selection

    def deselect(self) -> None:
        self.selection = []

    # -- resize ----------------------------------------------------------
    def preview_resize(self, block_id: str, handle: str, dx: float, dy: float) -> PlacedBox:
        """The ghost under the cursor.  Same maths as commit, so what the user
        sees while dragging is exactly what they get on release."""
        placed = self.placed(block_id)
        box = self._box(block_id)
        result = snap_resize(
            placed, handle, dx, dy, self.grid,
            aspect=box.aspect, min_span=box.min_span, max_span=box.max_span,
        )
        return ghost(placed, result, self.grid)

    def resize(self, block_id: str, handle: str, dx: float, dy: float) -> SnapResult:
        self._guard(block_id)
        placed = self.placed(block_id)
        box = self._box(block_id)
        result = snap_resize(
            placed, handle, dx, dy, self.grid,
            aspect=box.aspect, min_span=box.min_span, max_span=box.max_span,
        )
        scope = self.grid.scoped()
        if "col" in result.changed:
            self.pins.pin(block_id, "col", result.col, scope=scope)
        if "span" in result.changed:
            self.pins.pin(block_id, "span", result.span, scope=scope)
        if "rows" in result.changed and result.rows is not None:
            self.pins.pin(block_id, "rows", result.rows, scope=scope)
        self.invalidate()
        self._log(
            "resize", block_id,
            f"Resized to {result.span}/{self.grid.columns} columns"
            + (f", {result.rows} rows" if "rows" in result.changed else ""),
            handle=handle, **result.to_dict(),
        )
        return result

    def set_span(self, block_id: str, span: int, col: int | None = None) -> None:
        """Keyboard and toolbar path — same pins as the drag."""
        self._guard(block_id)
        box = self._box(block_id)
        span = max(box.min_span, min(int(span), box.max_span, self.grid.columns))
        scope = self.grid.scoped()
        if col is not None:
            col = max(0, min(int(col), self.grid.columns - span))
            self.pins.pin(block_id, "col", col, scope=scope)
        self.pins.pin(block_id, "span", span, scope=scope)
        self.invalidate()
        self._log("set_span", block_id, f"Width {span}/{self.grid.columns}", span=span, col=col)

    def set_rows(self, block_id: str, rows: int | None) -> None:
        self._guard(block_id)
        scope = self.grid.scoped()
        if rows is None:
            self.pins.release(block_id, "rows", scope=scope)
            self._log("auto_height", block_id, "Height back to automatic")
        else:
            self.pins.pin(block_id, "rows", max(1, int(rows)), scope=scope)
            self._log("set_rows", block_id, f"Height {rows} rows", rows=rows)
        self.invalidate()

    def set_align(self, block_id: str, align: str) -> None:
        self._guard(block_id)
        if align not in ("left", "center", "right", "justify"):
            raise LayoutRefused("align must be left, center, right or justify")
        self.pins.pin(block_id, "align", align, scope=self.grid.scoped())
        self.invalidate()
        self._log("align", block_id, f"Aligned {align}", align=align)

    # -- move ------------------------------------------------------------
    def move(self, block_id: str, before_block_id: str | None, col: int | None = None) -> None:
        """Reorder in the document.  Order is a pin like anything else, so a
        move is as revertable as a rewrite."""
        self._guard(block_id)
        order = [b.id for b in self._ordered() if b.id != block_id]
        index = len(order) if before_block_id is None else (
            order.index(before_block_id) if before_block_id in order else len(order)
        )
        order.insert(index, block_id)
        scope = self.grid.scoped()
        for i, bid in enumerate(order):
            self.pins.pin(bid, "order", i, scope=scope, note="reordered")
        if col is not None:
            self.pins.pin(block_id, "col", max(0, int(col)), scope=scope)
        self.invalidate()
        where = f"before {before_block_id}" if before_block_id else "to the end"
        self._log("move", block_id, f"Moved {where}", before=before_block_id, col=col)

    def drop(self, block_id: str, page: int, x: float, y: float) -> DropTarget:
        target = drop_target(self.geometry(), page, x, y, dragging=block_id)
        self.move(block_id, target.before_block_id, target.col if target.side == "beside" else None)
        return target

    def set_break_before(self, block_id: str, value: bool = True) -> None:
        self._guard(block_id)
        self.pins.pin(block_id, "break_before", bool(value), scope=self.grid.scoped())
        self.invalidate()
        self._log("break", block_id, "Starts a new page" if value else "No forced page break")

    def set_keep_with_next(self, block_id: str, value: bool = True) -> None:
        self._guard(block_id)
        self.pins.pin(block_id, "keep_with_next", bool(value), scope=self.grid.scoped())
        self.invalidate()
        self._log("keep", block_id, "Kept with the next block" if value else "May be separated")

    def hide(self, block_id: str, hidden: bool = True) -> None:
        self._guard(block_id)
        self.pins.pin(block_id, "hidden", bool(hidden), scope=self.grid.scoped())
        self.invalidate()
        self._log("hide" if hidden else "show", block_id, "Hidden" if hidden else "Shown")

    # -- give control back -------------------------------------------------
    def release(self, block_id: str, prop: str | None = None, *, force: bool = False) -> int:
        scope = self.grid.scoped()
        if prop:
            n = int(self.pins.release(block_id, prop, scope=scope, force=force))
        else:
            n = self.pins.release_block(block_id, scope=scope, force=force)
            n += self.pins.release_block(block_id, scope=GLOBAL_SCOPE, force=force)
        self.invalidate()
        self._log("release", block_id, f"Back to the template layout ({n} override(s) dropped)")
        return n

    def reset_layout(self, *, force: bool = False) -> int:
        n = 0
        for pin in self.pins.for_scope(self.grid.scoped()):
            block_id = pin.target.split(":", 1)[1]
            if self.pins.release(block_id, pin.prop, scope=pin.scope, force=force):
                n += 1
        self.invalidate()
        self._log("reset", "*", f"Whole document back to the template ({n} override(s) dropped)")
        return n

    def lock(self, block_id: str, prop: str | None = None, locked: bool = True) -> int:
        scope = self.grid.scoped()
        props = [prop] if prop else list(self.pins.pinned_props(block_id, scope))
        n = sum(1 for p in props if self.pins.set_lock(block_id, p, locked, scope=scope))
        self._log("lock" if locked else "unlock", block_id, f"{'Locked' if locked else 'Unlocked'} {n} property(ies)")
        return n

    # -- templates ---------------------------------------------------------
    def promote_to_template(self, *, min_examples: int = 2, note: str = "") -> dict[str, Any]:
        """'Save this as my layout.'  Repeated edits become rules."""
        new_template, report = self.template.promote(
            self.pins, self.blocks, self.grid, min_examples=min_examples, note=note
        )
        self.template = new_template
        self._log(
            "promote", "*",
            f"Saved as template v{new_template.version}: "
            f"{report['rule_count']} rule(s), {report['block_count']} block default(s)",
            **report,
        )
        return report

    def adopt_template(self, template: LayoutTemplate, *, keep_user_pins: bool = True) -> None:
        """Switch template.  User pins survive by default — a new template is a
        new set of defaults, not a reason to throw away someone's work."""
        self.template = template
        self.grid = PageGrid(
            page_width=self.grid.page_width, page_height=self.grid.page_height,
            margin_top=self.grid.margin_top, margin_right=self.grid.margin_right,
            margin_bottom=self.grid.margin_bottom, margin_left=self.grid.margin_left,
            columns=template.columns, gutter=self.grid.gutter,
            baseline=self.grid.baseline, page_size=template.page_size,
        )
        if not keep_user_pins:
            self.reset_layout(force=True)
        self.invalidate()
        self._log("adopt", "*", f"Template '{template.id}' v{template.version} applied")

    def set_page_size(self, page_size: str, columns: int | None = None) -> None:
        """Pins are scoped to the geometry, so switching page size reveals that
        page size's own layout rather than corrupting the one you tuned."""
        from .model import PAGE_SIZES

        w, h = PAGE_SIZES.get(page_size, PAGE_SIZES["A4"])
        self.grid = PageGrid(
            page_width=w, page_height=h,
            margin_top=self.grid.margin_top, margin_right=self.grid.margin_right,
            margin_bottom=self.grid.margin_bottom, margin_left=self.grid.margin_left,
            columns=columns or self.grid.columns, gutter=self.grid.gutter,
            baseline=self.grid.baseline, page_size=page_size,
        )
        self.invalidate()
        self._log("page_size", "*", f"Page size {page_size}")

    # -- reporting ----------------------------------------------------------
    def state(self) -> dict[str, Any]:
        """One payload for the canvas: geometry, selection, and what is pinned."""
        geo = self.geometry()
        return {
            "geometry": geo.to_dict(),
            "selection": list(self.selection),
            "template": {"id": self.template.id, "version": self.template.version},
            "pinned_blocks": self.pins.blocks(),
            "user_override_count": len(self.pins.user_pins()),
            "locked_blocks": [b.id for b in self.blocks if b.locked] + list(self.template.locked_blocks),
            "warnings": geo.warnings,
            "history": [
                {"action": c.action, "block_id": c.block_id, "summary": c.summary}
                for c in self.history[-25:]
            ],
        }

    # -- internals ----------------------------------------------------------
    def _ordered(self) -> list[BlockInput]:
        from .flow import order_blocks

        return order_blocks(self.blocks, self.grid, self.pins)

    def _box(self, block_id: str) -> Box:
        from .flow import resolve_boxes

        boxes = resolve_boxes(
            self.blocks, self.grid, self.pins, self.template.defaults_for(self.blocks, self.grid)
        )
        for b in boxes:
            if b.block_id == block_id:
                return b
        raise LayoutRefused(f"no block '{block_id}'")
