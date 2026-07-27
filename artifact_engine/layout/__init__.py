from .constraints import LayoutConstraints
from .engine import PrintLayoutEngine
from .graph import (
    GraphEdge,
    GraphLayoutResult,
    GraphNode,
    LayeredGraphLayout,
)
from .grid import Grid, col_span_class, grid_css
from .measurement import MeasurementEngine
from .pagination import (
    LayoutEngine,
    LayoutResult,
    Page,
    PageBreak,
    PlacedBlock,
    flatten_document,
)
from .solver import ConstraintSolver
from .spacing import Spacing, block_gap_pt, section_gap_pt
from .tree import (
    BackgroundStyle,
    ComponentLayout,
    ComponentStyle,
    ContainerLayout,
    ContainerStyle,
    LayoutNode,
    LayoutPage,
    LayoutTree,
    PageLayout,
    RegionLayout,
    RegionStyle,
    layout_result_to_tree,
)


def build_layout_engine(theme, *, page_size: str = "A4",
                        constraints: LayoutConstraints | None = None) -> LayoutEngine:
    grid = Grid.from_theme(theme, page_size=page_size)
    spacing = Spacing.from_theme(theme)
    constraints = constraints or LayoutConstraints()
    measurement = MeasurementEngine(grid, spacing, constraints)
    return LayoutEngine(
        grid=grid, spacing=spacing,
        constraints=constraints, measurement=measurement,
    )


def build_print_layout_engine(
    design_or_theme,
    *,
    page_size: str = "A4",
    constraints: LayoutConstraints | None = None,
) -> PrintLayoutEngine:
    """Build print-first engine from DesignSystem or legacy Theme."""
    from artifact_engine.design_system import DesignSystem
    from artifact_engine.model.theme import Theme

    if isinstance(design_or_theme, DesignSystem):
        design = design_or_theme
    elif isinstance(design_or_theme, Theme):
        design = DesignSystem.from_theme(design_or_theme, page_size=page_size)
    else:
        design = DesignSystem.from_theme(design_or_theme, page_size=page_size)
    return PrintLayoutEngine(design, constraints=constraints)


__all__ = [
    "Grid", "Spacing", "LayoutConstraints", "ConstraintSolver",
    "LayoutEngine", "LayoutResult", "Page", "PlacedBlock", "PageBreak",
    "flatten_document", "build_layout_engine", "build_print_layout_engine",
    "PrintLayoutEngine",
    "LayoutTree", "LayoutPage", "LayoutNode", "PageLayout",
    "RegionLayout", "ContainerLayout", "ComponentLayout",
    "BackgroundStyle", "RegionStyle", "ContainerStyle", "ComponentStyle",
    "layout_result_to_tree",
    "col_span_class", "grid_css", "block_gap_pt", "section_gap_pt",
    "LayeredGraphLayout", "GraphNode", "GraphEdge", "GraphLayoutResult",
    "MeasurementEngine",
]
