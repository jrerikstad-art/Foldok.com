"""Measurement Engine — content-aware height estimates before placement.

All heights are in points and deterministic. Used by LayoutEngine.
"""
from __future__ import annotations

from typing import Any

from artifact_engine.layout.constraints import LayoutConstraints
from artifact_engine.layout.grid import Grid
from artifact_engine.layout.spacing import Spacing
from artifact_engine.model.blocks import (
    BillOfMaterials,
    BulletList,
    CalloutBox,
    ComparisonTable,
    DiagramBlock,
    DrawingReference,
    EngineeringTable,
    EvaluationMatrix,
    FeatureGrid,
    FormSection,
    HeadingBlock,
    HeroBlock,
    ImageBlock,
    NoteBox,
    ParagraphBlock,
    ParameterGrid,
    Procedure,
    ProcessFlow,
    Rating,
    RatingLegend,
    RevisionHistory,
    SignatureBlock,
    SpecificationTable,
    StakeholderCard,
    TableOfContentsBlock,
    TechnicalData,
    Timeline,
    WarningBox,
)


class MeasurementEngine:
    """Measures every block before placement."""

    def __init__(
        self,
        grid: Grid,
        spacing: Spacing,
        constraints: LayoutConstraints | None = None,
    ):
        self.grid = grid
        self.spacing = spacing
        self.constraints = constraints or LayoutConstraints()

    def measure(self, block: Any) -> float:
        g = self.grid

        if getattr(block, "type", None) == "page_break":
            return 0.0

        if isinstance(block, HeadingBlock):
            return float({1: 36.0, 2: 24.0, 3: 18.0}.get(int(block.level), 20.0))

        if isinstance(block, ParagraphBlock):
            chars_per_line = max(42, int(g.content_width / 5.6))
            text = block.text or ""
            lines = max(1, (len(text) + chars_per_line - 1) // chars_per_line)
            return float(lines * 14.5 + 4.0)

        if isinstance(block, BulletList):
            total = 0.0
            chars_per_line = max(40, int(g.content_width / 5.6))
            for item in block.items or []:
                lines = max(1, (len(str(item)) + chars_per_line - 1) // chars_per_line)
                total += lines * 14.0
            return float(total + 6.0)

        if isinstance(block, FeatureGrid):
            cols = max(1, int(getattr(block, "columns", 2) or 2))
            rows = (len(block.items or []) + cols - 1) // cols
            # Stakeholder cards are taller than feature cards
            row_h = 68.0
            for it in block.items or []:
                if isinstance(it, StakeholderCard) or getattr(it, "type", "") == "stakeholder_card":
                    row_h = 96.0
                    break
            return float(rows * row_h + 12.0)

        if isinstance(block, StakeholderCard):
            needs = len(block.needs or [])
            pains = len(block.pain_points or [])
            return float(52.0 + (needs + pains) * 12.0 + 10.0)

        if isinstance(block, EvaluationMatrix):
            title_h = 18.0 if block.title else 0.0
            legend_h = 16.0 if block.legend else 0.0
            return float(
                title_h + 22.0 + len(block.rows or []) * 18.0 + legend_h + 10.0
            )

        if isinstance(block, ComparisonTable):
            title_h = 18.0 if block.title else 0.0
            return float(title_h + 24.0 + len(block.rows or []) * 18.0 + 10.0)

        if isinstance(block, Rating):
            return 18.0

        if isinstance(block, ParameterGrid):
            cols = max(1, int(getattr(block, "columns", 2) or 2))
            n = len(block.items or [])
            rows = (n + cols - 1) // cols
            title_h = 18.0 if block.title else 0.0
            return float(title_h + rows * 22.0 + 10.0)

        if isinstance(block, SpecificationTable):
            header = 24.0
            row_h = 17.0
            foot = 14.0 if getattr(block, "footnotes", None) else 0.0
            return float(header + len(block.rows or []) * row_h + foot + 8.0)

        if isinstance(block, EngineeringTable):
            header = 24.0
            unit_row = 14.0 if block.units else 0.0
            foot = 12.0 if block.footnotes else 0.0
            cap = 14.0 if block.caption else 0.0
            return float(
                header + unit_row + len(block.rows or []) * 17.0 + foot + cap + 8.0
            )

        if isinstance(block, RevisionHistory):
            return float(28.0 + len(block.entries or []) * 18.0 + 8.0)

        if isinstance(block, DrawingReference):
            return 52.0

        if isinstance(block, TableOfContentsBlock):
            return float(22.0 + len(block.entries or []) * 16.0 + 8.0)

        if isinstance(block, BillOfMaterials):
            return float(26.0 + len(block.items or []) * 16.0 + 8.0)

        if isinstance(block, TechnicalData):
            title_h = 18.0 if block.title else 0.0
            return float(title_h + len(block.items or []) * 15.5 + 12.0)

        if isinstance(block, ImageBlock):
            max_h = g.content_height * float(
                getattr(self.constraints, "max_image_height_ratio", 0.45) or 0.45
            )
            defaults = {
                "hero": 210.0,
                "figure": 160.0,
                "exploded": 220.0,
                "component": 120.0,
                "diagram": 180.0,
            }
            return float(min(defaults.get(getattr(block, "role", "figure") or "figure", 150.0), max_h))

        if isinstance(block, HeroBlock):
            return 200.0

        if isinstance(block, (CalloutBox, WarningBox, NoteBox)):
            chars_per_line = max(40, int(g.content_width / 5.4))
            text = getattr(block, "text", "") or ""
            lines = max(1, (len(text) + chars_per_line - 1) // chars_per_line)
            attr = 14.0 if getattr(block, "attribution", None) else 0.0
            return float(20.0 + lines * 13.0 + attr)

        if isinstance(block, Procedure):
            h = 22.0
            for step in block.steps or []:
                h += 44.0
                if getattr(step, "warning", None):
                    h += 14.0
            return float(h + 8.0)

        if isinstance(block, Timeline):
            return float(len(block.events or []) * 38.0 + 10.0)

        if isinstance(block, ProcessFlow):
            if getattr(block, "direction", "horizontal") == "horizontal":
                return 80.0
            return float(len(block.steps or []) * 54.0)

        if isinstance(block, FormSection):
            rows = len(block.fields or [])
            if int(getattr(block, "columns", 1) or 1) == 2:
                rows = (rows + 1) // 2
            return float(rows * 22.0 + 8.0)

        if isinstance(block, SignatureBlock):
            return 48.0

        if isinstance(block, RatingLegend):
            return 20.0

        if isinstance(block, DiagramBlock):
            # Prefer explicit height_pt; else page-relative cap
            if block.height_pt:
                return float(min(float(block.height_pt), g.content_height * 0.55, 260.0))
            return float(min(260.0, g.content_height * 0.55))

        return 40.0

    def space_after(self, block: Any) -> float:
        s = self.spacing
        if isinstance(block, HeadingBlock):
            return float({
                1: s.after_h1,
                2: s.after_h2,
                3: s.after_h3,
            }.get(int(block.level), s.after_h2))
        if isinstance(block, HeroBlock):
            return float(s.after_hero)
        if isinstance(block, ParagraphBlock):
            return float(s.after_paragraph)
        if isinstance(block, (SpecificationTable, BillOfMaterials, TechnicalData,
                              EngineeringTable, RevisionHistory, ParameterGrid)):
            return float(s.space_md)
        if isinstance(block, DrawingReference):
            return float(s.space_sm)
        if isinstance(block, TableOfContentsBlock):
            return float(s.space_md)
        if isinstance(block, FormSection):
            return float(s.space_sm)
        if isinstance(block, DiagramBlock):
            return float(s.space_lg)
        return float(s.after_block)
