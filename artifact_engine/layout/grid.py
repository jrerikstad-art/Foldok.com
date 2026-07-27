"""Deterministic page grid. All measurements in points (1 pt = 1/72 in)."""
from __future__ import annotations

from dataclasses import dataclass

from artifact_engine.model.theme import Theme

MM_TO_PT = 2.834645339
PAGE_SIZES = {
    "A4": (595.28, 841.89),
    "Letter": (612.0, 792.0),
}


@dataclass(frozen=True)
class Grid:
    page_width: float
    page_height: float
    margin_top: float
    margin_right: float
    margin_bottom: float
    margin_left: float
    columns: int
    gutter: float
    baseline: float

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
        total_gutter = self.gutter * (self.columns - 1)
        return (self.content_width - total_gutter) / self.columns

    def column_x(self, col: int) -> float:
        return self.margin_left + col * (self.column_width + self.gutter)

    def span_width(self, start_col: int, span: int) -> float:
        span = max(1, span)
        return span * self.column_width + (span - 1) * self.gutter

    def snap_y(self, y: float) -> float:
        relative = y - self.margin_top
        snapped = round(relative / self.baseline) * self.baseline
        return self.margin_top + snapped

    @classmethod
    def from_theme(cls, theme: Theme, page_size: str = "A4") -> "Grid":
        w, h = PAGE_SIZES.get(page_size, PAGE_SIZES["A4"])
        margin = theme.page_margin_mm * MM_TO_PT
        gutter = theme.gutter_mm * MM_TO_PT
        return cls(
            page_width=w,
            page_height=h,
            margin_top=margin,
            margin_right=margin,
            margin_bottom=margin,
            margin_left=margin,
            columns=theme.column_count,
            gutter=gutter,
            baseline=theme.baseline_pt,
        )


def col_span_class(width: str | None, columns: int = 12) -> str:
    w = (width or "full").lower()
    if w in ("full", "1", "12"):
        return "span-12"
    if w in ("half", "6"):
        return "span-6"
    if w in ("third", "4"):
        return "span-4"
    if w in ("two-thirds", "8"):
        return "span-8"
    return "span-12"


def grid_css(column_count: int, gutter_mm: float) -> str:
    return f"""
.grid {{
  display: grid;
  grid-template-columns: repeat({column_count}, 1fr);
  gap: {gutter_mm}mm;
}}
.span-12 {{ grid-column: span {column_count}; }}
.span-8 {{ grid-column: span {max(1, column_count * 2 // 3)}; }}
.span-6 {{ grid-column: span {max(1, column_count // 2)}; }}
.span-4 {{ grid-column: span {max(1, column_count // 3)}; }}
"""
