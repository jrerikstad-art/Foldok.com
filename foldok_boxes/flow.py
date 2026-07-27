"""The flow solver.

Two phases, kept separate because they fail differently and should be debugged
separately:

**Band packing.**  Blocks are laid into horizontal bands in document order.  A
block takes the first free column range wide enough for it; if nothing fits, the
band closes and a new one starts.  Everything in a band shares a top edge, and
the band is as tall as its tallest member.  That is what makes a two-column
figure row work, and it is why document order survives: a block can never land
in an earlier band than the block before it.

**Pagination.**  Bands are atomic — never split across a page.  For a compliance
document that is the right trade: a table half on page 3 and half on page 4 with
a signature line stranded is worse than a slightly short page.  ``keep_with_next``
drags a band forward with the one after it, and a band taller than the page is
reported as an overflow rather than silently clipped.

Determinism is the whole point.  Same blocks, same pins, same theme → same
geometry, every time, in the canvas and in the PDF.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence, runtime_checkable

from .model import Box, Geometry, PageGrid, PlacedBox
from .pins import PinStore


@dataclass
class BlockInput:
    """What the solver needs to know about a block.  Content stays elsewhere."""

    id: str
    role: str = "text"                 # text | heading | image | diagram | table | callout | spacer
    section: str = ""
    text: str = ""                     # only used by the fallback measurer
    rows_hint: int | None = None       # e.g. table row count
    aspect: float | None = None        # width / height for images and diagrams
    locked: bool = False               # boilerplate/legal — layout not user-editable


@runtime_checkable
class Measurer(Protocol):
    def height(self, block: BlockInput, width_pt: float, grid: PageGrid) -> float: ...


class SimpleMeasurer:
    """Deterministic fallback so the solver is testable on its own.

    Wire artifact_engine's real measurement in production; this exists so that
    the geometry contract can be tested without a font stack, and so a missing
    measurer degrades to something plausible rather than to zero-height boxes.
    """

    def __init__(self, chars_per_pt: float = 0.19, line_height: float = 14.0) -> None:
        self.chars_per_pt = chars_per_pt
        self.line_height = line_height

    def height(self, block: BlockInput, width_pt: float, grid: PageGrid) -> float:
        role = block.role
        if role == "spacer":
            return grid.baseline
        if role in ("image", "diagram"):
            aspect = block.aspect or 4 / 3
            return max(grid.baseline, width_pt / aspect)
        if role == "table":
            rows = block.rows_hint or 4
            return 22.0 + rows * 18.0
        if role == "heading":
            return 26.0
        chars_per_line = max(12.0, width_pt * self.chars_per_pt * 5.2)
        lines = max(1, math.ceil(len(block.text or "x" * 240) / chars_per_line))
        pad = 16.0 if role == "callout" else 0.0
        return lines * self.line_height + pad


# ----------------------------------------------------------------------
@dataclass
class Band:
    """One horizontal row of boxes sharing a top edge."""

    index: int
    rows: int = 1
    items: list[PlacedBox] = field(default_factory=list)
    break_before: bool = False
    keep_with_next: bool = False

    @property
    def height(self) -> float:
        return 0.0 if not self.items else max(b.height for b in self.items)


# ----------------------------------------------------------------------
def resolve_boxes(
    blocks: Sequence[BlockInput],
    grid: PageGrid,
    pins: PinStore | None = None,
    defaults: dict[str, Box] | None = None,
) -> list[Box]:
    """Template default, then pins on top.  Pins always win."""
    pins = pins or PinStore()
    defaults = defaults or {}
    scope = grid.scoped()
    out: list[Box] = []
    for block in blocks:
        base = defaults.get(block.id)
        if base is None:
            base = Box(block_id=block.id, col=0, span=grid.columns, role=block.role)
        box = Box(
            block_id=block.id,
            col=base.col,
            span=base.span,
            rows=base.rows,
            align=base.align,
            min_span=base.min_span,
            max_span=min(base.max_span, grid.columns),
            aspect=base.aspect if base.aspect is not None else block.aspect,
            keep_with_next=base.keep_with_next,
            break_before=base.break_before,
            role=base.role or block.role,
        )
        for prop in ("col", "span", "rows", "align", "break_before", "keep_with_next"):
            pinned = pins.resolve(block.id, prop, scope)
            if pinned is not None:
                setattr(box, prop, pinned.value)
        out.append(box.clamped(grid))
    return out


def order_blocks(
    blocks: Sequence[BlockInput],
    grid: PageGrid,
    pins: PinStore | None = None,
) -> list[BlockInput]:
    """Document order, with explicit reorder pins applied.  Stable."""
    pins = pins or PinStore()
    scope = grid.scoped()
    decorated = []
    for i, block in enumerate(blocks):
        pinned = pins.value(block.id, "order", scope, None)
        decorated.append((float(pinned) if pinned is not None else float(i), i, block))
    decorated.sort(key=lambda t: (t[0], t[1]))
    return [b for _, _, b in decorated]


def pack(
    blocks: Sequence[BlockInput],
    boxes: Sequence[Box],
    grid: PageGrid,
    measurer: Measurer,
    pins: PinStore | None = None,
) -> tuple[list[Band], list[str]]:
    pins = pins or PinStore()
    scope = grid.scoped()
    by_id = {b.id: b for b in blocks}
    warnings: list[str] = []

    bands: list[Band] = []
    band = Band(index=0)
    occupied = [False] * grid.columns

    def close() -> None:
        nonlocal band, occupied
        if band.items:
            band.rows = max(grid.rows_for(b.height) for b in band.items)
            bands.append(band)
        band = Band(index=len(bands))
        occupied = [False] * grid.columns

    for box in boxes:
        block = by_id[box.block_id]
        if pins.value(box.block_id, "hidden", scope, False):
            continue

        col_pinned = pins.resolve(box.block_id, "col", scope) is not None
        span = max(1, min(box.span, grid.columns))

        if box.break_before:
            if band.items:
                close()
            band.break_before = True

        col = box.col if col_pinned else _first_fit(occupied, span)
        if col is None or col + span > grid.columns or _busy(occupied, col, span):
            if band.items:
                close()
            col = box.col if col_pinned else 0
            col = max(0, min(col, grid.columns - span))
            if _busy(occupied, col, span):
                warnings.append(
                    f"block '{box.block_id}' could not be placed at column {col}; moved to a new band"
                )
                col = 0

        width = grid.span_width(span)
        if box.rows is not None:
            height = box.rows * grid.baseline
        else:
            height = measurer.height(block, width, grid)
            height = max(grid.baseline, grid.rows_for(height) * grid.baseline)

        placed = PlacedBox(
            block_id=box.block_id,
            page=0, row=0,
            col=col, span=span,
            rows=grid.rows_for(height),
            x=grid.column_x(col), y=0.0,
            width=width, height=height,
            role=box.role, align=box.align,
            pinned=pins.pinned_props(box.block_id, scope),
        )
        band.items.append(placed)
        for i in range(col, col + span):
            occupied[i] = True
        band.keep_with_next = box.keep_with_next
        if span >= grid.columns:
            close()

    close()
    for b in bands:
        b.items.sort(key=lambda p: (p.col, p.block_id))
    return bands, warnings


def _busy(occupied: list[bool], col: int, span: int) -> bool:
    if col < 0 or col + span > len(occupied):
        return True
    return any(occupied[col : col + span])


def _first_fit(occupied: list[bool], span: int) -> int | None:
    for start in range(0, len(occupied) - span + 1):
        if not any(occupied[start : start + span]):
            return start
    return None


def paginate(bands: Sequence[Band], grid: PageGrid) -> tuple[list[PlacedBox], int, list[str]]:
    """Bands are atomic.  A band never straddles a page."""
    warnings: list[str] = []
    out: list[PlacedBox] = []
    page = 1
    cursor = 0.0                       # points consumed on this page
    max_h = grid.content_height
    pending_keep: list[Band] = []

    def emit(b: Band, page_no: int, top: float) -> None:
        for item in b.items:
            item.page = page_no
            item.y = grid.margin_top + top
            item.row = grid.row_at(item.y)
            out.append(item)

    i = 0
    band_list = list(bands)
    while i < len(band_list):
        b = band_list[i]
        h = b.height

        if b.break_before and cursor > 0:
            page += 1
            cursor = 0.0

        if h > max_h:
            warnings.append(
                f"band {b.index} is {h:.0f} pt tall and the page holds {max_h:.0f} pt — "
                "it will overflow; shorten it, pin fewer rows, or allow it to split"
            )
            if cursor > 0:
                page += 1
                cursor = 0.0
            emit(b, page, cursor)
            for item in b.items:
                item.overflow = True
            cursor = max_h
            i += 1
            continue

        group = [b]
        j = i
        while band_list[j].keep_with_next and j + 1 < len(band_list):
            j += 1
            group.append(band_list[j])
        group_h = sum(g.height for g in group)

        if cursor > 0 and cursor + group_h > max_h:
            page += 1
            cursor = 0.0
            if group_h > max_h:
                group = [b]           # cannot keep them together; give up gracefully
                warnings.append(
                    f"bands {b.index}–{band_list[j].index} are kept together but do not fit "
                    "on one page; they were split"
                )

        for g in group:
            emit(g, page, cursor)
            cursor += g.height
        i += len(group)

    return out, page, warnings


def solve(
    blocks: Sequence[BlockInput],
    grid: PageGrid | None = None,
    pins: PinStore | None = None,
    defaults: dict[str, Box] | None = None,
    measurer: Measurer | None = None,
) -> Geometry:
    """Blocks in, geometry out.  The only function the canvas and the renderer
    both call, which is what keeps them honest."""
    grid = grid or PageGrid()
    pins = pins or PinStore()
    measurer = measurer or SimpleMeasurer()

    ordered = order_blocks(blocks, grid, pins)
    boxes = resolve_boxes(ordered, grid, pins, defaults)
    bands, warn_pack = pack(ordered, boxes, grid, measurer, pins)
    placed, pages, warn_page = paginate(bands, grid)

    orphans = pins.orphans([b.id for b in blocks])
    warn_pin = [
        f"pin '{p.prop}' targets '{p.target}', which is not in this document"
        for p in orphans
    ]
    return Geometry(
        grid=grid,
        boxes=placed,
        page_count=pages,
        warnings=warn_pack + warn_page + warn_pin,
    )
