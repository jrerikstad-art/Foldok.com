"""Artifact Composition Engine — Document AST in, deterministic HTML/PDF out.

Guiding rule: the LLM is an architect, not a designer.
It only produces the Document AST. Every visual decision is code.
Print-first: compose → measure → LayoutTree → absolute paint.
"""
from __future__ import annotations

from .bridge import document_from_pages
from .composition import (
    INDUSTRIAL_REPORT_PROFILE,
    INDUSTRIAL_REPORT_PROFILE_ORDER,
    MANUAL_PROFILE,
    MANUAL_PROFILE_ORDER,
    USER_MANUAL_PROFILE,
    CompositionEngine,
    PageRegion,
    diagram_block_from_svg,
    embed_diagram_engine,
)
from .core import ArtifactEngine, get_engine
from .design_system import (
    DATASHEET_DS,
    DESIGN_SYSTEMS,
    ENGINEERING_DS,
    INDUSTRIAL_REPORT_DS,
    MANUAL_DS,
    DesignSystem,
    get_design_system,
)
from .diagram_style import (
    DiagramStyle,
    diagram_style_for_theme,
    get_diagram_style,
    load_diagram_style,
)
from .fixtures import demo_ccs_document, demo_rotor_spreader_manual
from .layout import (
    GraphEdge,
    GraphLayoutResult,
    GraphNode,
    Grid,
    LayeredGraphLayout,
    LayoutConstraints,
    ConstraintSolver,
    LayoutEngine,
    LayoutNode,
    LayoutPage,
    LayoutResult,
    LayoutTree,
    PageLayout,
    RegionLayout,
    ContainerLayout,
    ComponentLayout,
    MeasurementEngine,
    PrintLayoutEngine,
    Spacing,
    build_layout_engine,
    build_print_layout_engine,
    flatten_document,
)
from .model.blocks import (
    AnyBlock,
    BOMItem,
    BillOfMaterials,
    Block,
    BulletList,
    CalculationBlock,
    CalloutBox,
    ComparisonTable,
    DiagramBlock,
    DrawingReference,
    EngineeringTable,
    EvaluationMatrix,
    FeatureCard,
    FeatureGrid,
    FormField,
    FormSection,
    HeadingBlock,
    HeroBlock,
    ImageBlock,
    MaterialBlock,
    NoteBox,
    ParagraphBlock,
    ParameterGrid,
    ParameterItem,
    Procedure,
    ProcedureStep,
    ProcessFlow,
    ProcessStep,
    Rating,
    RatingLegend,
    RevisionEntry,
    RevisionHistory,
    SignatureBlock,
    SpecRow,
    SpecificationTable,
    StakeholderCard,
    TableOfContentsBlock,
    TechnicalData,
    Timeline,
    TimelineEvent,
    TocEntry,
    WarningBox,
    block_from_dict,
)
from .model.document import Document
from .model.section import Section
from .model.theme import Theme
from .render.html import HTMLRenderer
from .render.pdf import PDFRenderer, pdf_backends_available
from .render.base import Renderer
from .themes import DATASHEET, ENGINEERING, MANUAL, THEMES


def render_document(
    doc: Document | dict,
    theme: str | None = None,
    *,
    paginate: bool = True,
    compose: bool = True,
    flow: bool = False,
) -> str:
    """Print-first HTML via LayoutTree paint. Set flow=True for legacy CSS flow."""
    if isinstance(doc, dict):
        doc = Document.from_dict(doc)
    theme_name = theme or doc.theme or "engineering"
    return get_engine(theme_name).render_document_html(
        doc, paginate=paginate, compose=compose, flow=flow,
    )


def layout_document(
    doc: Document | dict,
    theme: str | None = None,
    *,
    compose: bool = True,
) -> LayoutResult:
    if isinstance(doc, dict):
        doc = Document.from_dict(doc)
    theme_name = theme or doc.theme or "engineering"
    return get_engine(theme_name).layout_document(doc, compose=compose)


def build_layout(
    doc: Document | dict,
    theme: str | None = None,
    *,
    compose: bool = True,
) -> LayoutTree:
    if isinstance(doc, dict):
        doc = Document.from_dict(doc)
    theme_name = theme or doc.theme or "engineering"
    return get_engine(theme_name).build_layout(doc, compose=compose)


def render_pdf(
    doc: Document | dict,
    path: str,
    theme: str | None = None,
    *,
    paginate: bool = True,
    compose: bool = True,
):
    if isinstance(doc, dict):
        doc = Document.from_dict(doc)
    theme_name = theme or doc.theme or "engineering"
    return get_engine(theme_name).render_document_pdf(
        doc, path, paginate=paginate, compose=compose,
    )


__all__ = [
    "Document", "Section", "Theme",
    "DesignSystem", "ENGINEERING_DS", "DATASHEET_DS", "MANUAL_DS",
    "DiagramStyle", "get_diagram_style", "load_diagram_style", "diagram_style_for_theme",
    "INDUSTRIAL_REPORT_DS",
    "DESIGN_SYSTEMS", "get_design_system",
    "Block", "AnyBlock", "ParagraphBlock", "HeadingBlock", "BulletList",
    "FeatureCard", "FeatureGrid", "StakeholderCard", "EvaluationMatrix",
    "ComparisonTable", "Rating", "SpecRow", "SpecificationTable",
    "ImageBlock", "CalloutBox", "HeroBlock", "block_from_dict",
    "Procedure", "ProcedureStep", "Timeline", "TimelineEvent",
    "BillOfMaterials", "BOMItem", "ProcessFlow", "ProcessStep",
    "WarningBox", "NoteBox", "TechnicalData",
    "FormField", "FormSection", "SignatureBlock", "RatingLegend",
    "DiagramBlock", "CalculationBlock", "MaterialBlock",
    "ParameterItem", "ParameterGrid", "DrawingReference",
    "RevisionEntry", "RevisionHistory", "EngineeringTable",
    "TocEntry", "TableOfContentsBlock",
    "HTMLRenderer", "PDFRenderer", "pdf_backends_available",
    "render_document", "layout_document", "build_layout", "render_pdf",
    "ArtifactEngine", "get_engine",
    "CompositionEngine", "PageRegion",
    "MANUAL_PROFILE", "MANUAL_PROFILE_ORDER", "USER_MANUAL_PROFILE",
    "INDUSTRIAL_REPORT_PROFILE", "INDUSTRIAL_REPORT_PROFILE_ORDER",
    "diagram_block_from_svg", "embed_diagram_engine",
    "ENGINEERING", "DATASHEET", "MANUAL", "THEMES",
    "document_from_pages", "demo_ccs_document", "demo_rotor_spreader_manual",
    "Grid", "Spacing", "LayoutConstraints", "ConstraintSolver",
    "LayoutEngine", "LayoutResult",
    "LayoutTree", "LayoutPage", "LayoutNode", "PageLayout",
    "RegionLayout", "ContainerLayout", "ComponentLayout",
    "PrintLayoutEngine",
    "build_layout_engine", "build_print_layout_engine", "flatten_document",
    "MeasurementEngine",
    "LayeredGraphLayout", "GraphNode", "GraphEdge", "GraphLayoutResult",
    "Renderer",
]
