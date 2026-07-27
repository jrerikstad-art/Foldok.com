"""Deterministic PDF export — WeasyPrint first, Playwright fallback.

PDF paint path: LayoutTree → HTMLRenderer.render_layout → PDF bytes.
Document convenience wrappers must build a LayoutTree first.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from artifact_engine.layout.tree import LayoutTree
from artifact_engine.model.document import Document
from artifact_engine.render.html import HTMLRenderer


class PDFRenderer:
    def __init__(self, theme_name: str = "engineering"):
        self.html_renderer = HTMLRenderer(theme_name=theme_name)
        self.theme_name = theme_name

    def render_layout(self, layout: LayoutTree, output_path: str | Path | None = None) -> bytes:
        """Renderer protocol — PDF from LayoutTree only."""
        html = self.html_renderer.render_layout(layout)
        if output_path is not None:
            path = self.render_html_string(html, output_path)
            return path.read_bytes()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "out.pdf"
            self.render_html_string(html, path)
            return path.read_bytes()

    def render(
        self,
        doc: Document,
        output_path: str | Path,
        *,
        paginate: bool = True,
    ) -> Path:
        """Convenience: Document → LayoutTree → PDF file."""
        from artifact_engine.layout import build_print_layout_engine

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not paginate:
            html = self.html_renderer.render(doc, paginate=False)
            return self.render_html_string(html, output_path)
        tree = build_print_layout_engine(self.html_renderer.design).layout(doc, compose=False)
        self.render_layout(tree, output_path)
        return Path(output_path)

    def render_html_string(self, html: str, output_path: str | Path) -> Path:
        """PDF from an already-built HTML string (e.g. diagram wrapper)."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if self._try_weasyprint(html, output_path):
            return output_path
        if self._try_playwright(html, output_path):
            return output_path
        raise RuntimeError(
            "Neither WeasyPrint nor Playwright is available. "
            "Install one of:\n"
            "  pip install weasyprint\n"
            "  pip install playwright && playwright install chromium"
        )

    def _try_weasyprint(self, html: str, output_path: Path) -> bool:
        try:
            from weasyprint import HTML
        except ImportError:
            return False
        try:
            HTML(string=html).write_pdf(str(output_path))
            return output_path.is_file() and output_path.stat().st_size > 0
        except Exception:
            return False

    def _try_playwright(self, html: str, output_path: Path) -> bool:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return False
        tmp_html = None
        try:
            with tempfile.NamedTemporaryFile(
                suffix=".html", delete=False, mode="w", encoding="utf-8",
            ) as f:
                f.write(html)
                tmp_html = f.name
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(Path(tmp_html).as_uri())
                page.pdf(
                    path=str(output_path),
                    format="A4",
                    print_background=True,
                    margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                )
                browser.close()
            return output_path.is_file() and output_path.stat().st_size > 0
        except Exception:
            return False
        finally:
            if tmp_html:
                Path(tmp_html).unlink(missing_ok=True)


def pdf_backends_available() -> dict:
    out = {"weasyprint": False, "playwright": False}
    try:
        import weasyprint  # noqa: F401
        out["weasyprint"] = True
    except ImportError:
        pass
    try:
        import playwright  # noqa: F401
        out["playwright"] = True
    except ImportError:
        pass
    return out
