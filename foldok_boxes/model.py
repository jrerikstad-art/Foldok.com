"""Box model.

The editor problem in one line: the block model stored ``width: full|half|third``,
so a corner drag had nowhere to land.  Meanwhile ``artifact_engine/layout/grid.py``
could already place a box at any column span and snap heights to the baseline.
The renderer was more capable than the editor allowed.

So a Box is a rectangle **on the page grid**, not in pixels:

    col   which column it starts in      0 .. columns-1
    span  how many columns wide          1 .. columns
    rows  height in baseline units       None = as tall as its content

That is continuous enough that dragging a corner feels like dragging a corner,
and discrete enough that the PDF can honour it exactly.  Free pixel geometry
would feel marginally better for about a day and then start lying: pagination
cannot reflow a box pinned to a coordinate, and "which section is this in" stops
having an answer — which is what gap detection and template requirements are
built on.

Word gives you flow. InDesign gives you a grid. Figma gives you direct
manipulation. This is the grid, flowed, manipulated directly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Any, Literal

MM_TO_PT = 2.834645339
PAGE_SIZES: dict[str, tuple[float, float]] = {
    "A4": (595.28, 841.89),
    "A5": (419.53, 595.28),
    "Letter": (612.0, 792.0),
    "Legal": (612.0, 1008.0),
}

Align = Literal["left", "center", "right", "justify"]
HANDLES = ("nw", "n", "ne", "e", "se", "s", "sw", "w")


# ----------------------------------------------------------------------
@dataclass(frozen=True)
class PageGrid:
    """The one coordinate system.  Canvas and PDF both measure in these points."""

    page_width: float = PAGE_SIZES["A4"][0]
    page_height: float = PAGE_SIZES["A4"][1]
    margin_top: float = 56.0
    margin_right: float = 48.0
    margin_bottom: float = 64.0
    margin_left: float = 48.0
    columns: int = 12
    gutter: float = 12.0
    baseline: float = 12.0
    page_size: str = "A4"

    # -- derived -------------------------------------------------------
    @property
    def content_width(self) -> float:
        return self.page_width - self.margin_left - self.margin_right

    @property
    def content_height(self) -> float:
        return self.page_height - self.margin_top - self.margin_bottom

    @property
    def column_width(self) -> float:
        if self.columns <= 1:
            return self.content_width
        return (self.content_width - self.gutter * (self.columns - 1)) / self.columns

    @property
    def rows_per_page(self) -> int:
        return max(1, int(self.content_height // self.baseline))

    def column_x(self, col: int) -> float:
        col = max(0, min(int(col), self.columns - 1))
        return self.margin_left + col * (self.column_width + self.gutter)

    def span_width(self, span: int) -> float:
        span = max(1, min(int(span), self.columns))
        return span * self.column_width + (span - 1) * self.gutter

    def row_y(self, row: int) -> float:
        return self.margin_top + max(0, int(row)) * self.baseline

    def rows_for(self, height_pt: float) -> int:
        return max(1, math.ceil(round(height_pt / self.baseline, 6)))

    # -- pixel <-> grid -------------------------------------------------
    def col_at(self, x_pt: float) -> int:
        pitch = self.column_width + self.gutter
        raw = (x_pt - self.margin_left) / pitch if pitch else 0.0
        return max(0, min(self.columns - 1, int(round(raw))))

    def span_at(self, width_pt: float) -> int:
        pitch = self.column_width + self.gutter
        raw = (width_pt + self.gutter) / pitch if pitch else 1.0
        return max(1, min(self.columns, int(round(raw))))

    def row_at(self, y_pt: float) -> int:
        return max(0, int(round((y_pt - self.margin_top) / self.baseline)))

    @classmethod
    def from_theme(cls, theme: Any, page_size: str = "A4", columns: int = 12) -> "PageGrid":
        """Accepts artifact_engine Theme, or anything with the same fields."""
        w, h = PAGE_SIZES.get(page_size, PAGE_SIZES["A4"])
        margin = float(getattr(theme, "page_margin_mm", 18.0)) * MM_TO_PT
        gutter = float(getattr(theme, "gutter_mm", 4.5)) * MM_TO_PT
        baseline = float(getattr(theme, "baseline_pt", 12.0))
        return cls(
            page_width=w, page_height=h,
            margin_top=margin, margin_right=margin,
            margin_bottom=margin * 1.15, margin_left=margin,
            columns=columns, gutter=gutter, baseline=baseline, page_size=page_size,
        )

    def scoped(self) -> str:
        """Pin scope key.  A layout tuned for A4 must not corrupt Letter."""
        return f"{self.page_size}/{self.columns}"


# ----------------------------------------------------------------------
@dataclass
class Box:
    """What a block wants.  Resolved from template defaults, then pins."""

    block_id: str
    col: int = 0
    span: int = 12
    rows: int | None = None            # None = height from content
    align: Align = "left"
    min_span: int = 1
    max_span: int = 12
    aspect: float | None = None        # width / height, locked for images
    keep_with_next: bool = False
    break_before: bool = False
    role: str = "text"                 # text | image | diagram | table | callout | ...

    def clamped(self, grid: PageGrid) -> "Box":
        max_span = min(self.max_span, grid.columns)
        span = max(self.min_span, min(int(self.span), max_span))
        col = max(0, min(int(self.col), grid.columns - span))
        rows = None if self.rows is None else max(1, int(self.rows))
        return replace(self, col=col, span=span, rows=rows, max_span=max_span)

    @property
    def full_width(self) -> bool:
        return self.col == 0 and self.span >= self.max_span

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "block_id": self.block_id,
            "col": self.col,
            "span": self.span,
            "align": self.align,
            "role": self.role,
        }
        if self.rows is not None:
            d["rows"] = self.rows
        if self.aspect:
            d["aspect"] = round(self.aspect, 4)
        if self.keep_with_next:
            d["keep_with_next"] = True
        if self.break_before:
            d["break_before"] = True
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Box":
        return Box(
            block_id=d["block_id"],
            col=int(d.get("col", 0)),
            span=int(d.get("span", 12)),
            rows=None if d.get("rows") is None else int(d["rows"]),
            align=d.get("align", "left"),
            min_span=int(d.get("min_span", 1)),
            max_span=int(d.get("max_span", 12)),
            aspect=d.get("aspect"),
            keep_with_next=bool(d.get("keep_with_next", False)),
            break_before=bool(d.get("break_before", False)),
            role=d.get("role", "text"),
        )


@dataclass
class PlacedBox:
    """Final geometry.  This is what both the canvas and the PDF draw."""

    block_id: str
    page: int
    row: int                    # row index within the page, in baseline units
    col: int
    span: int
    rows: int
    x: float
    y: float
    width: float
    height: float
    role: str = "text"
    align: Align = "left"
    pinned: tuple[str, ...] = ()
    overflow: bool = False

    def rect(self) -> tuple[float, float, float, float]:
        return (self.x, self.y, self.width, self.height)

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height

    def handle_at(self, px: float, py: float, tolerance: float = 6.0) -> str | None:
        """Which resize handle is under the pointer.  The JS layer mirrors this
        exactly — one hit-test rule, so the cursor never lies about what a drag
        will do."""
        near_l = abs(px - self.x) <= tolerance
        near_r = abs(px - (self.x + self.width)) <= tolerance
        near_t = abs(py - self.y) <= tolerance
        near_b = abs(py - (self.y + self.height)) <= tolerance
        inside_x = self.x - tolerance <= px <= self.x + self.width + tolerance
        inside_y = self.y - tolerance <= py <= self.y + self.height + tolerance
        if not (inside_x and inside_y):
            return None
        vertical = "n" if near_t else ("s" if near_b else "")
        horizontal = "w" if near_l else ("e" if near_r else "")
        return (vertical + horizontal) or None

    def to_dict(self) -> dict[str, Any]:
        d = {
            "block_id": self.block_id,
            "page": self.page,
            "row": self.row,
            "col": self.col,
            "span": self.span,
            "rows": self.rows,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "width": round(self.width, 2),
            "height": round(self.height, 2),
            "role": self.role,
            "align": self.align,
        }
        if self.pinned:
            d["pinned"] = list(self.pinned)
        if self.overflow:
            d["overflow"] = True
        return d


@dataclass
class Geometry:
    """The whole document's resolved layout.  Canvas and renderer consume this
    same object — that is what makes print parity structural instead of a
    weekly eyeball check."""

    grid: PageGrid
    boxes: list[PlacedBox] = field(default_factory=list)
    page_count: int = 1
    warnings: list[str] = field(default_factory=list)

    def of(self, block_id: str) -> PlacedBox | None:
        for b in self.boxes:
            if b.block_id == block_id:
                return b
        return None

    def on_page(self, page: int) -> list[PlacedBox]:
        return [b for b in self.boxes if b.page == page]

    def at(self, page: int, x: float, y: float) -> PlacedBox | None:
        """Topmost box under a point.  Later blocks win ties, matching z-order."""
        for b in reversed(self.on_page(page)):
            if b.contains(x, y):
                return b
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "grid": {
                "page_size": self.grid.page_size,
                "page_width": round(self.grid.page_width, 2),
                "page_height": round(self.grid.page_height, 2),
                "margin_top": round(self.grid.margin_top, 2),
                "margin_right": round(self.grid.margin_right, 2),
                "margin_bottom": round(self.grid.margin_bottom, 2),
                "margin_left": round(self.grid.margin_left, 2),
                "columns": self.grid.columns,
                "gutter": round(self.grid.gutter, 2),
                "baseline": round(self.grid.baseline, 2),
            },
            "page_count": self.page_count,
            "boxes": [b.to_dict() for b in self.boxes],
            "warnings": list(self.warnings),
        }
