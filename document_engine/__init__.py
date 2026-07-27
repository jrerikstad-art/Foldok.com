"""Document Engine — multi-page datasheets / manuals (print HTML).

    from document_engine import DocumentEngine

    eng = DocumentEngine()
    eng.load_fixture()
    eng.set_project_facts({...})
    html = eng.render("html")
"""
from __future__ import annotations

from .engine import DocumentEngine, render_datasheet_demo
from .fixtures import DATASHEET_FIXTURE, DEMO_FACTS
from .resolve import resolve_placeholder

__all__ = [
    "DocumentEngine",
    "DATASHEET_FIXTURE",
    "DEMO_FACTS",
    "resolve_placeholder",
    "render_datasheet_demo",
]
