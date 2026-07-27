"""ConstraintSolver — publishing rules applied after measurement, before LayoutTree.

Owns widow/orphan, keep-with-next, figure+caption, and page-break policy.
Must never invent content. Placement geometry comes only from measured sizes.
"""
from __future__ import annotations

from typing import Any, Sequence

from artifact_engine.layout.constraints import LayoutConstraints
from artifact_engine.layout.grid import Grid
from artifact_engine.layout.measurement import MeasurementEngine
from artifact_engine.layout.pagination import LayoutEngine, LayoutResult, flatten_document
from artifact_engine.layout.spacing import Spacing
from artifact_engine.model.document import Document


class ConstraintSolver:
    """
    Resolve page breaks and spacing from measured components.

    Today this wraps LayoutEngine (placement) so the publishing pipeline has an
    explicit solver stage. Future work: stronger table-split, balanced columns,
    region-aware packing (hero / main / sidebar / footer).
    """

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
        self._placement = LayoutEngine(
            grid=grid,
            spacing=spacing,
            constraints=self.constraints,
            measurement=self.measurement,
        )

    def solve_document(self, doc: Document) -> LayoutResult:
        """Measure every block, then place under publishing constraints."""
        return self.solve_blocks(flatten_document(doc))

    def solve_blocks(self, blocks: Sequence[Any]) -> LayoutResult:
        # MeasurementEngine runs inside LayoutEngine.layout for each block;
        # calling measure upfront documents the contract and warms sizes.
        for b in blocks:
            self.measurement.measure(b)
        return self._placement.layout(list(blocks))

    def publishing_checks(self) -> list[str]:
        """Questions every layout pass should be able to answer (policy surface)."""
        c = self.constraints
        return [
            f"widow_lines>={c.min_widow_lines}",
            f"orphan_lines>={c.min_orphan_lines}",
            f"keep_with_next={c.keep_with_next}",
            f"min_space_after_heading={c.min_space_after_heading}",
            f"max_image_height_ratio={c.max_image_height_ratio}",
            f"table_header_repeat={c.table_header_repeat}",
            f"allow_section_split={c.allow_section_split}",
        ]
