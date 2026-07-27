"""Print-first layout facade — DesignSystem in, LayoutTree out."""
from __future__ import annotations

from typing import Any, List

from artifact_engine.composition import CompositionEngine
from artifact_engine.design_system import DesignSystem
from artifact_engine.layout.constraints import LayoutConstraints
from artifact_engine.layout.grid import Grid
from artifact_engine.layout.measurement import MeasurementEngine
from artifact_engine.layout.pagination import LayoutEngine as PlacementEngine
from artifact_engine.layout.spacing import Spacing
from artifact_engine.layout.solver import ConstraintSolver
from artifact_engine.layout.tree import LayoutTree, layout_result_to_tree
from artifact_engine.model.document import Document


class PrintLayoutEngine:
    """
    Pure print-first layout.
    Input  : Document AST (compose optional)
    Output : LayoutTree (absolute positions) — the only thing renderers see
    Pipeline: compose → measure → ConstraintSolver → LayoutTree
    """

    def __init__(
        self,
        design: DesignSystem,
        constraints: LayoutConstraints | None = None,
    ):
        self.ds = design
        self.constraints = constraints or LayoutConstraints()
        self.grid = Grid(
            page_width=design.page_width,
            page_height=design.page_height,
            margin_top=design.margin,
            margin_right=design.margin,
            margin_bottom=design.margin,
            margin_left=design.margin,
            columns=design.columns,
            gutter=design.gutter,
            baseline=design.baseline,
        )
        self.spacing = Spacing(
            baseline=design.baseline,
            space_xs=design.space_xs,
            space_sm=design.space_sm,
            space_md=design.space_md,
            space_lg=design.space_lg,
            space_xl=design.space_xl,
            space_2xl=getattr(design, "space_2xl", 48.0),
            space_section=getattr(design, "space_section", 56.0),
            after_h1=design.space_md,
            after_h2=design.space_sm,
            after_h3=design.space_xs * 1.5,
            after_paragraph=design.space_sm,
            after_block=design.space_md * 0.85,
            before_section=getattr(design, "space_section", design.space_lg),
            after_hero=design.space_lg,
        )
        self.measure = MeasurementEngine(
            self.grid, self.spacing, self.constraints,
        )
        self.solver = ConstraintSolver(
            self.grid, self.spacing, self.constraints, self.measure,
        )
        # Legacy alias — prefer self.solver
        self._placement = PlacementEngine(
            grid=self.grid,
            spacing=self.spacing,
            constraints=self.constraints,
            measurement=self.measure,
        )
        self._composer = CompositionEngine()

    def layout(self, doc: Document, *, compose: bool = True) -> LayoutTree:
        if compose:
            doc = self._composer.compose(doc)
        result = self.solver.solve_document(doc)
        return layout_result_to_tree(
            result,
            self.ds,
            title=doc.title,
            document_type=doc.document_type,
            language=getattr(doc, "language", "en") or "en",
            metadata=dict(doc.metadata or {}),
        )

    def layout_blocks(self, blocks: List[Any]) -> LayoutTree:
        result = self.solver.solve_blocks(blocks)
        return layout_result_to_tree(result, self.ds)
