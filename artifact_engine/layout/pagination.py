"""Deterministic layout + pagination — measure, place, break pages."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from artifact_engine.layout.constraints import LayoutConstraints
from artifact_engine.layout.grid import Grid
from artifact_engine.layout.measurement import MeasurementEngine
from artifact_engine.layout.spacing import Spacing
from artifact_engine.model.blocks import (
    Block,
    FeatureGrid,
    FormSection,
    HeadingBlock,
    ImageBlock,
    ParameterGrid,
)
from artifact_engine.model.document import Document


@dataclass
class PlacedBlock:
    block: Any
    x: float
    y: float
    width: float
    height: float
    page_index: int


@dataclass
class Page:
    index: int
    blocks: list = field(default_factory=list)
    used_height: float = 0.0


@dataclass
class LayoutResult:
    pages: list
    total_height: float
    grid: Grid
    spacing: Spacing

    @property
    def page_count(self) -> int:
        return len(self.pages)


@dataclass
class PageBreak(Block):
    """Forced page break — produced by flatten when section.page_break_before."""
    type: str = "page_break"


def flatten_document(doc: Document) -> list:
    """Document AST → ordered block stream for LayoutEngine."""
    out: list = []
    if doc.hero:
        out.append(doc.hero)
    for section in doc.sections or []:
        if section.page_break_before and out:
            out.append(PageBreak())
        if section.title:
            out.append(HeadingBlock(text=section.title, level=2))
        out.extend(section.blocks or [])
    return out


class LayoutEngine:
    def __init__(
        self,
        grid: Grid,
        spacing: Spacing,
        constraints: LayoutConstraints | None = None,
        measurement: MeasurementEngine | None = None,
    ):
        self.grid = grid
        self.spacing = spacing
        self.constraints = constraints or LayoutConstraints()
        self.measurement = measurement or MeasurementEngine(
            grid, spacing, self.constraints,
        )

    def layout(self, blocks: list) -> LayoutResult:
        pages: list[Page] = [Page(index=0)]
        current_y = self.grid.margin_top
        current_page = pages[0]
        i = 0
        blocks = list(blocks or [])

        while i < len(blocks):
            block = blocks[i]

            if isinstance(block, PageBreak) or getattr(block, "type", None) == "page_break":
                if current_page.blocks:
                    pages.append(Page(index=len(pages)))
                    current_page = pages[-1]
                    current_y = self.grid.margin_top
                i += 1
                continue

            height = self._measure(block)
            available = (
                self.grid.page_height - self.grid.margin_bottom - current_y
            )
            remaining = blocks[i + 1:]
            needs_break = (
                bool(current_page.blocks)
                and self._should_break(block, height, available, remaining)
            )

            if needs_break:
                pages.append(Page(index=len(pages)))
                current_page = pages[-1]
                current_y = self.grid.margin_top

            placed_y = self.grid.snap_y(current_y)
            if (
                placed_y + height
                > self.grid.page_height - self.grid.margin_bottom
                and current_page.blocks
            ):
                pages.append(Page(index=len(pages)))
                current_page = pages[-1]
                current_y = self.grid.margin_top
                placed_y = self.grid.snap_y(current_y)

            # Multi-column blocks: compute column geometry for height,
            # place once at full content width (HTML renders the grid CSS).
            if (
                isinstance(block, (FeatureGrid, FormSection, ParameterGrid))
                and int(getattr(block, "columns", 1) or 1) > 1
            ):
                multi = self._place_multicolumn(block, placed_y, current_page.index)
                if multi:
                    height = max(p.y + p.height for p in multi) - placed_y
                placed = PlacedBlock(
                    block=block,
                    x=self.grid.margin_left,
                    y=placed_y,
                    width=self.grid.content_width,
                    height=height,
                    page_index=current_page.index,
                )
            else:
                placed = PlacedBlock(
                    block=block,
                    x=self.grid.margin_left,
                    y=placed_y,
                    width=self.grid.content_width,
                    height=height,
                    page_index=current_page.index,
                )

            current_page.blocks.append(placed)
            current_page.used_height = (
                placed.y + height - self.grid.margin_top
            )
            current_y = placed.y + height + self._space_after(block)
            i += 1

        total = sum(p.used_height for p in pages)
        return LayoutResult(
            pages=pages,
            total_height=total,
            grid=self.grid,
            spacing=self.spacing,
        )

    def layout_document(self, doc: Document) -> LayoutResult:
        return self.layout(flatten_document(doc))

    def _should_break(
        self,
        block: Any,
        height: float,
        available: float,
        remaining_blocks: list,
    ) -> bool:
        """Smarter page-break decisions — keep headings with content, avoid orphans."""
        if height > available:
            return True

        if (
            self.constraints.keep_with_next
            and isinstance(block, HeadingBlock)
            and remaining_blocks
        ):
            nxt = remaining_blocks[0]
            if not (
                isinstance(nxt, PageBreak)
                or getattr(nxt, "type", None) == "page_break"
            ):
                next_h = self._measure(nxt)
                gap = self._space_after(block)
                if height + gap + next_h > available:
                    return True

        # Figures never split — move whole block (+ caption space) to next page
        if isinstance(block, ImageBlock) and height > available * 0.98:
            return True
        if isinstance(block, ImageBlock) and height > available:
            return True

        # Avoid leaving a tiny orphan strip at the bottom
        if (
            remaining_blocks
            and available - height < self.spacing.space_lg
        ):
            rest_h = sum(
                self._measure(b)
                for b in remaining_blocks[:3]
                if not (
                    isinstance(b, PageBreak)
                    or getattr(b, "type", None) == "page_break"
                )
            )
            if rest_h < self.grid.content_height * 0.35:
                return True

        return False

    def _place_multicolumn(
        self, block: Any, y: float, page_index: int,
    ) -> list[PlacedBlock]:
        """
        Distribute multi-column children across the page grid.
        Returns per-cell placements used for height; caller places one
        full-width container for HTML rendering.
        """
        placed: list[PlacedBlock] = []
        g = self.grid

        if isinstance(block, FeatureGrid):
            cols = max(1, min(int(block.columns or 1), g.columns))
            items = list(block.items or [])
            span = max(1, g.columns // cols)
            col_w = g.span_width(0, span)
            card_h = 62.0
            row_gap = 8.0
            for idx, _item in enumerate(items):
                col = idx % cols
                row = idx // cols
                x = g.column_x(col * span)
                item_y = y + row * (card_h + row_gap)
                placed.append(PlacedBlock(
                    block=block,
                    x=x,
                    y=g.snap_y(item_y),
                    width=col_w,
                    height=card_h,
                    page_index=page_index,
                ))
            return placed

        if isinstance(block, ParameterGrid):
            cols = max(1, min(int(block.columns or 1), g.columns))
            items = list(block.items or [])
            span = max(1, g.columns // cols)
            col_w = g.span_width(0, span)
            row_h = 20.0
            for idx, _item in enumerate(items):
                col = idx % cols
                row = idx // cols
                x = g.column_x(col * span)
                item_y = y + row * row_h
                placed.append(PlacedBlock(
                    block=block,
                    x=x,
                    y=g.snap_y(item_y),
                    width=col_w,
                    height=row_h,
                    page_index=page_index,
                ))
            return placed

        if isinstance(block, FormSection):
            cols = max(1, min(int(block.columns or 1), 2))
            fields = list(block.fields or [])
            span = max(1, g.columns // cols)
            col_w = g.span_width(0, span)
            row_h = 18.0
            for idx, _f in enumerate(fields):
                col = idx % cols
                row = idx // cols
                x = g.column_x(col * span)
                item_y = y + row * row_h
                placed.append(PlacedBlock(
                    block=block,
                    x=x,
                    y=g.snap_y(item_y),
                    width=col_w,
                    height=row_h,
                    page_index=page_index,
                ))
            return placed

        h = self._measure(block)
        placed.append(PlacedBlock(
            block=block,
            x=g.margin_left,
            y=g.snap_y(y),
            width=g.content_width,
            height=h,
            page_index=page_index,
        ))
        return placed

    # ── Measurement delegates to MeasurementEngine ───────────────────

    def _measure(self, block: Any) -> float:
        return float(self.measurement.measure(block))

    def _space_after(self, block: Any) -> float:
        return float(self.measurement.space_after(block))
