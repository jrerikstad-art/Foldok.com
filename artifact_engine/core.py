"""Shared deterministic print-first pipeline for visual artifacts.

Document AST
    → CompositionEngine
    → MeasurementEngine (inside layout)
    → PrintLayoutEngine → LayoutTree
    → HTML / PDF paint (absolute positions only)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from artifact_engine.composition import CompositionEngine
from artifact_engine.design_system import DesignSystem, get_design_system
from artifact_engine.layout import (
    LayoutResult,
    LayoutTree,
    PrintLayoutEngine,
    build_layout_engine,
    build_print_layout_engine,
    flatten_document,
)
from artifact_engine.model.document import Document
from artifact_engine.render.html import HTMLRenderer
from artifact_engine.render.pdf import PDFRenderer
from artifact_engine.themes import THEMES
from artifact_engine.themes.engineering import ENGINEERING


class ArtifactRenderer(Protocol):
    def render_html(self, artifact: Any) -> str: ...
    def render_pdf(self, artifact: Any, path: str) -> str: ...


class ArtifactEngine:
    """
    Central deterministic pipeline used by DocumentEngine, FormEngine,
    and diagram-in-document embedding.

    Print-first: layout produces a LayoutTree; HTML only paints it.
    """

    def __init__(self, theme_name: str = "engineering"):
        self.theme_name = theme_name
        self.theme = THEMES.get(theme_name, ENGINEERING)
        self.design: DesignSystem = get_design_system(theme_name)
        self.composer = CompositionEngine()
        self.layout_engine = build_layout_engine(self.theme)
        self.print_layout = build_print_layout_engine(self.design)
        self.html_renderer = HTMLRenderer(theme_name)
        self.pdf_renderer = PDFRenderer(theme_name)

    def compose_document(self, doc: Document) -> Document:
        return self.composer.compose(doc)

    def flatten(self, doc: Document) -> list:
        """Composed document → ordered block stream for layout."""
        return flatten_document(doc)

    def build_layout(self, doc: Document, *, compose: bool = True) -> LayoutTree:
        """Compose (optional) → measure → place → LayoutTree."""
        if compose:
            doc = self.composer.compose(doc)
        return self.print_layout.layout(doc, compose=False)

    def layout_document(self, doc: Document, *, compose: bool = True) -> LayoutResult:
        """Legacy LayoutResult (grid placement). Prefer build_layout()."""
        if compose:
            doc = self.composer.compose(doc)
        return self.layout_engine.layout_document(doc)

    def layout_blocks(self, blocks) -> LayoutResult:
        return self.layout_engine.layout(blocks)

    def render_document_html(
        self,
        doc: Document,
        *,
        paginate: bool = True,
        compose: bool = True,
        flow: bool = False,
    ) -> str:
        if compose:
            doc = self.composer.compose(doc)
        if flow or not paginate:
            return self.html_renderer.render(doc, paginate=False, flow=True)
        tree = self.print_layout.layout(doc, compose=False)
        return self.html_renderer.render_tree(tree)

    def render_html(self, doc: Document) -> str:
        """Print-first HTML (LayoutTree paint)."""
        return self.render_document_html(doc, paginate=True, compose=True)

    def render_document_pdf(
        self,
        doc: Document,
        path: str | Path,
        *,
        paginate: bool = True,
        compose: bool = True,
    ) -> Path:
        if compose:
            doc = self.composer.compose(doc)
        # Always paint absolute layout for PDF
        html = self.render_document_html(
            doc, paginate=True, compose=False, flow=False,
        )
        return self.pdf_renderer.render_html_string(html, path)

    def render_pdf(self, doc: Document, path: str | Path) -> Path:
        return self.render_document_pdf(doc, path)


_engines: dict[str, ArtifactEngine] = {}


def get_engine(theme: str = "engineering") -> ArtifactEngine:
    if theme not in _engines:
        _engines[theme] = ArtifactEngine(theme)
    return _engines[theme]
