"""Deterministic Document AST → HTML. Print-first: paint LayoutTree only."""
from __future__ import annotations

import html as html_lib

from artifact_engine.design_system import DesignSystem, get_design_system
from artifact_engine.layout import build_layout_engine, build_print_layout_engine
from artifact_engine.layout.grid import col_span_class, grid_css
from artifact_engine.layout.pagination import LayoutResult
from artifact_engine.layout.tree import LayoutNode, LayoutTree
from artifact_engine.model.blocks import (
    BillOfMaterials,
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
from artifact_engine.model.document import Document
from artifact_engine.model.theme import Theme
from artifact_engine.themes import THEMES
from artifact_engine.themes.engineering import ENGINEERING


class HTMLRenderer:
    def __init__(self, theme_name: str = "engineering"):
        self.theme_name = theme_name
        self.theme: Theme = THEMES.get(theme_name, ENGINEERING)
        self.design: DesignSystem = get_design_system(theme_name)

    def render(self, doc: Document, *, paginate: bool = True, flow: bool = False) -> str:
        """
        Convenience: Document → LayoutTree → paint.
        Prefer render_layout(tree) when you already have a LayoutTree.

        flow=True is LEGACY CSS-flow only — not part of the publishing contract.
        New code must not use flow for production export.
        """
        if flow or not paginate:
            return self._render_flow(doc)
        tree = build_print_layout_engine(self.design).layout(doc, compose=False)
        return self.render_layout(tree)

    def render_layout(self, layout: LayoutTree) -> str:
        """Renderer protocol entry — paint LayoutTree only."""
        return self.render_tree(layout)

    def render_tree(self, tree: LayoutTree) -> str:
        """Pure paint of an already-composed LayoutTree — absolute positions."""
        ds = tree.design
        lang = html_lib.escape(tree.language or "en")
        pages_html = []
        for page in tree.pages:
            items = []
            # Prefer region walk; nodes property flattens for paint
            for node in page.nodes:
                items.append(self._paint_node(node))
            bg = ""
            if page.background and page.background.color:
                bg = f"background:{html_lib.escape(page.background.color)};"
            pages_html.append(
                f'<section class="page print-page" data-page="{page.page_number}" '
                f'data-regions="{len(page.regions)}" '
                f'style="width:{page.width:.2f}pt;height:{page.height:.2f}pt;{bg}">'
                f'{self._paint_running(page, ds)}'
                f'{"".join(items)}</section>'
            )
        return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<title>{html_lib.escape(tree.title)}</title>
<style>
{self._css_paginated()}
</style>
</head>
<body>
<div class="document theme-{html_lib.escape(ds.name)} paginated"
 data-foldok="artifact_document" data-layout="paginated"
 data-layout-contract="{html_lib.escape(getattr(tree, 'contract_version', '1.0'))}"
 data-pages="{len(tree.pages)}"
 data-type="{html_lib.escape(tree.document_type)}">
{"".join(pages_html)}
</div>
</body>
</html>"""

    def _paint_running(self, page, ds: DesignSystem) -> str:
        """Running header / footer (WORKORDER 0.49 B4)."""
        parts = []
        if page.header:
            parts.append(
                f'<div class="running-header" style="position:absolute;'
                f'left:{ds.margin:.2f}pt;top:{ds.margin * 0.35:.2f}pt;'
                f'width:{ds.page_width - 2 * ds.margin:.2f}pt;'
                f'font-size:{ds.footer:.2f}pt;color:{html_lib.escape(ds.muted)};'
                f'text-align:right">{html_lib.escape(page.header)}</div>'
            )
        if page.footer:
            parts.append(
                f'<div class="running-footer" style="position:absolute;'
                f'left:{ds.margin:.2f}pt;'
                f'top:{ds.page_height - ds.margin * 0.65:.2f}pt;'
                f'width:{ds.page_width - 2 * ds.margin:.2f}pt;'
                f'font-size:{ds.footer:.2f}pt;color:{html_lib.escape(ds.muted)};'
                f'text-align:left">{html_lib.escape(page.footer)}</div>'
            )
        return "".join(parts)

    def _paint_node(self, node: LayoutNode) -> str:
        inner = self._render_block(node.block)
        return (
            f'<div class="placed" data-page="{node.page}" '
            f'style="position:absolute;left:{node.x:.2f}pt;top:{node.y:.2f}pt;'
            f'width:{node.width:.2f}pt;min-height:{node.height:.2f}pt">'
            f"{inner}</div>"
        )

    def render_layout_result(
        self,
        layout: LayoutResult,
        *,
        title: str = "Document",
        document_type: str = "technical",
        language: str = "en",
    ) -> str:
        """Legacy bridge: LayoutResult → LayoutTree → paint. Prefer render_layout."""
        from artifact_engine.layout.tree import layout_result_to_tree

        tree = layout_result_to_tree(
            layout,
            self.design,
            title=title,
            document_type=document_type,
            language=language,
        )
        return self.render_tree(tree)

    def _render_flow(self, doc: Document) -> str:
        t = self.theme
        lang = html_lib.escape(doc.language or "en")
        parts = [
            "<!DOCTYPE html>",
            f'<html lang="{lang}">',
            "<head>",
            '<meta charset="UTF-8">',
            f"<title>{html_lib.escape(doc.title)}</title>",
            "<style>",
            self._css(),
            "</style>",
            "</head>",
            "<body>",
            f'<div class="document theme-{html_lib.escape(t.name)}" '
            f'data-foldok="artifact_document" data-type="'
            f'{html_lib.escape(doc.document_type)}">',
        ]
        if doc.hero:
            parts.append(self._render_hero(doc.hero))
        for section in doc.sections:
            parts.append(self._render_section(section))
        parts.extend(["</div>", "</body>", "</html>"])
        return "\n".join(parts)

    def _render_hero(self, hero: HeroBlock) -> str:
        bullets = "".join(
            f"<li>{html_lib.escape(b)}</li>" for b in (hero.bullets or [])
        )
        image = (
            f'<img src="{html_lib.escape(hero.image)}" alt="" class="hero-img">'
            if hero.image else ""
        )
        return f"""
<header class="hero">
  <div class="hero-text">
    <div class="accent-bar"></div>
    <h1>{html_lib.escape(hero.headline)}</h1>
    <p class="summary">{html_lib.escape(hero.summary)}</p>
    <ul class="hero-bullets">{bullets}</ul>
  </div>
  <div class="hero-media">{image}</div>
</header>"""

    def _render_section(self, section) -> str:
        title = (
            f"<h2>{html_lib.escape(section.title)}</h2>" if section.title else ""
        )
        blocks = "".join(self._render_block(b) for b in (section.blocks or []))
        pb = ' style="break-before:page"' if section.page_break_before else ""
        sid = f' id="{html_lib.escape(section.id)}"' if section.id else ""
        return f'<section class="section"{sid}{pb}>{title}{blocks}</section>'

    def _render_block(self, block) -> str:
        if isinstance(block, ParagraphBlock):
            return (
                f'<p class="p-{html_lib.escape(block.style)}">'
                f"{html_lib.escape(block.text)}</p>"
            )
        if isinstance(block, HeadingBlock):
            tag = f"h{int(block.level)}"
            return f"<{tag}>{html_lib.escape(block.text)}</{tag}>"
        if isinstance(block, BulletList):
            items = "".join(
                f"<li>{html_lib.escape(i)}</li>" for i in (block.items or [])
            )
            return f'<ul class="list-{html_lib.escape(block.style)}">{items}</ul>'
        if isinstance(block, FeatureGrid):
            cards = []
            for item in block.items or []:
                if isinstance(item, StakeholderCard):
                    cards.append(self._render_stakeholder_card(item))
                    continue
                metric = (
                    f'<div class="feature-metric">'
                    f"{html_lib.escape(item.metric)}</div>"
                    if getattr(item, "metric", None) else ""
                )
                rating = ""
                if getattr(item, "rating", None) is not None:
                    rating = self._render_rating_inline(
                        int(item.rating), 5, getattr(item, "role", None),
                    )
                role = (
                    f'<div class="feature-role">{html_lib.escape(item.role)}</div>'
                    if getattr(item, "role", None) and getattr(item, "rating", None) is None
                    else ""
                )
                cards.append(
                    "<div class=\"feature-card\">"
                    f"{metric}{rating}{role}"
                    f"<h3>{html_lib.escape(item.title)}</h3>"
                    f"<p>{html_lib.escape(item.description)}</p>"
                    "</div>"
                )
            cols = int(block.columns or 2)
            return (
                f'<div class="feature-grid cols-{cols}">'
                f"{''.join(cards)}</div>"
            )
        if isinstance(block, StakeholderCard):
            return self._render_stakeholder_card(block)
        if isinstance(block, EvaluationMatrix):
            return self._render_evaluation_matrix(block)
        if isinstance(block, ComparisonTable):
            return self._render_comparison_table(block)
        if isinstance(block, Rating):
            return self._render_rating_inline(
                int(block.value), int(block.max_value or 5), block.label,
            )
        if isinstance(block, ParameterGrid):
            return self._render_parameter_grid(block)
        if isinstance(block, EngineeringTable):
            return self._render_engineering_table(block)
        if isinstance(block, RevisionHistory):
            return self._render_revision_history(block)
        if isinstance(block, DrawingReference):
            return self._render_drawing_reference(block)
        if isinstance(block, TableOfContentsBlock):
            return self._render_toc(block)
        if isinstance(block, SpecificationTable):
            return self._render_spec_table(block)
        if isinstance(block, ImageBlock):
            cap = (
                f"<figcaption>{html_lib.escape(block.caption)}</figcaption>"
                if block.caption else ""
            )
            span = col_span_class(block.width)
            return (
                f'<figure class="img-{html_lib.escape(block.role)} {span}">'
                f'<img src="{html_lib.escape(block.src)}" '
                f'alt="{html_lib.escape(block.alt)}">{cap}</figure>'
            )
        if isinstance(block, CalloutBox):
            title = (
                f"<strong>{html_lib.escape(block.title)}</strong> "
                if block.title else ""
            )
            attr = (
                f'<footer class="callout-attr">'
                f"{html_lib.escape(block.attribution)}</footer>"
                if block.attribution else ""
            )
            icon = (
                f'<span class="callout-icon">{html_lib.escape(block.icon)}</span> '
                if block.icon else ""
            )
            return (
                f'<aside class="callout callout-{html_lib.escape(block.variant)}">'
                f"{icon}{title}{html_lib.escape(block.text)}{attr}</aside>"
            )
        if isinstance(block, HeroBlock):
            return self._render_hero(block)
        if isinstance(block, Procedure):
            return self._render_procedure(block)
        if isinstance(block, Timeline):
            return self._render_timeline(block)
        if isinstance(block, BillOfMaterials):
            return self._render_bom(block)
        if isinstance(block, ProcessFlow):
            return self._render_process_flow(block)
        if isinstance(block, WarningBox):
            return (
                f'<aside class="callout callout-warning">'
                f"<strong>{html_lib.escape(block.title)}</strong> "
                f"{html_lib.escape(block.text)}</aside>"
            )
        if isinstance(block, NoteBox):
            return (
                f'<aside class="callout callout-note">'
                f"<strong>{html_lib.escape(block.title)}</strong> "
                f"{html_lib.escape(block.text)}</aside>"
            )
        if isinstance(block, TechnicalData):
            return self._render_technical_data(block)
        if isinstance(block, FormSection):
            return self._render_form_section(block)
        if isinstance(block, SignatureBlock):
            return self._render_signature(block)
        if isinstance(block, RatingLegend):
            return self._render_rating_legend()
        if isinstance(block, DiagramBlock):
            return self._render_diagram(block)
        if isinstance(block, CalculationBlock):
            return self._render_calculation(block)
        if isinstance(block, MaterialBlock):
            return self._render_material(block)
        return f"<!-- unknown block: {html_lib.escape(getattr(block, 'type', '?'))} -->"

    def _render_rating_inline(
        self, value: int, max_value: int = 5, label: str | None = None,
    ) -> str:
        ds = self.design
        filled = max(0, min(int(value), int(max_value)))
        empty = max(0, int(max_value) - filled)
        stars = (
            f'<span class="rating-filled">{"★" * filled}</span>'
            f'<span class="rating-empty">{"☆" * empty}</span>'
        )
        lab = (
            f'<span class="rating-label">{html_lib.escape(label)}</span> '
            if label else ""
        )
        size = getattr(ds, "rating_size", 11.0)
        return (
            f'<div class="rating" style="font-size:{size}pt">'
            f"{lab}{stars}</div>"
        )

    def _render_stakeholder_card(self, s: StakeholderCard) -> str:
        role = (
            f'<div class="stakeholder-role">{html_lib.escape(s.role)}</div>'
            if s.role else ""
        )
        rating = self._render_rating_inline(int(s.rating or 0), 5)
        needs = "".join(
            f"<li>{html_lib.escape(n)}</li>" for n in (s.needs or [])
        )
        pains = "".join(
            f"<li>{html_lib.escape(p)}</li>" for p in (s.pain_points or [])
        )
        needs_block = (
            f'<div class="stakeholder-list"><h4>Needs</h4><ul>{needs}</ul></div>'
            if needs else ""
        )
        pains_block = (
            f'<div class="stakeholder-list"><h4>Pain points</h4><ul>{pains}</ul></div>'
            if pains else ""
        )
        return (
            '<div class="stakeholder-card feature-card">'
            f"<h3>{html_lib.escape(s.name)}</h3>{role}{rating}"
            f"{needs_block}{pains_block}</div>"
        )

    def _matrix_cell_class(self, val: str) -> str:
        v = (val or "").strip().lower()
        if v in ("h", "high", "høy", "hoy", "red", "3"):
            return "matrix-high"
        if v in ("m", "medium", "med", "amber", "yellow", "2"):
            return "matrix-medium"
        if v in ("l", "low", "lav", "green", "1"):
            return "matrix-low"
        return ""

    def _render_evaluation_matrix(self, m: EvaluationMatrix) -> str:
        title = (
            f"<h3 class=\"matrix-title\">{html_lib.escape(m.title)}</h3>"
            if m.title else ""
        )
        cols = m.columns or []
        head = "".join(
            f"<th>{html_lib.escape(c)}</th>" for c in cols
        )
        highlight = (m.highlight or "").strip().lower()
        body_rows = []
        for ri, row_label in enumerate(m.rows or []):
            cells = (m.values[ri] if ri < len(m.values or []) else []) or []
            tds = []
            for ci, col in enumerate(cols):
                val = cells[ci] if ci < len(cells) else ""
                cls = self._matrix_cell_class(val)
                key_match = (
                    highlight
                    and (
                        highlight == f"{ri},{ci}"
                        or highlight == (val or "").strip().lower()
                        or highlight == f"{(row_label or '').lower()}:{col.lower()}"
                    )
                )
                if key_match:
                    cls = (cls + " matrix-highlight").strip()
                tds.append(
                    f'<td class="{cls}">{html_lib.escape(str(val))}</td>'
                )
            body_rows.append(
                f"<tr><th>{html_lib.escape(row_label)}</th>{''.join(tds)}</tr>"
            )
        legend = ""
        if m.legend and isinstance(m.legend, dict):
            bits = "".join(
                f"<span class=\"matrix-legend-item\">"
                f"<strong>{html_lib.escape(str(k))}</strong> "
                f"{html_lib.escape(str(v))}</span>"
                for k, v in m.legend.items()
            )
            legend = f'<div class="matrix-legend">{bits}</div>'
        return (
            f'<div class="evaluation-matrix">{title}'
            f'<table class="matrix-table"><thead><tr><th></th>{head}</tr></thead>'
            f'<tbody>{"".join(body_rows)}</tbody></table>{legend}</div>'
        )

    def _render_comparison_table(self, c: ComparisonTable) -> str:
        title = (
            f"<h3 class=\"comparison-title\">{html_lib.escape(c.title)}</h3>"
            if c.title else ""
        )
        rows = []
        for r in c.rows or []:
            rows.append(
                "<tr>"
                f"<th>{html_lib.escape(str(r.get('aspect') or ''))}</th>"
                f"<td>{html_lib.escape(str(r.get('today') or ''))}</td>"
                f"<td>{html_lib.escape(str(r.get('future') or ''))}</td>"
                "</tr>"
            )
        return (
            f'<div class="comparison-table">{title}'
            f'<table class="spec-table comparison">'
            f"<thead><tr><th></th>"
            f"<th>{html_lib.escape(c.left_header)}</th>"
            f"<th>{html_lib.escape(c.right_header)}</th>"
            f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        )

    def _render_diagram(self, d: DiagramBlock) -> str:
        title = (
            f"<h3 class=\"diagram-title\">{html_lib.escape(d.title)}</h3>"
            if d.title else ""
        )
        # Figure N — caption (+ optional citation / revision)
        cap_bits = []
        if d.figure_number:
            cap_bits.append(f"Figure {d.figure_number}")
        if d.caption:
            cap_bits.append(d.caption)
        elif d.title and d.figure_number:
            cap_bits.append(d.title)
        cap_main = " — ".join(cap_bits) if cap_bits else ""
        meta = []
        if d.source_citation:
            meta.append(html_lib.escape(d.source_citation))
        if d.revision:
            meta.append(f"Rev {html_lib.escape(d.revision)}")
        if d.diagram_type:
            meta.append(html_lib.escape(d.diagram_type))
        meta_html = (
            f'<div class="diagram-meta">{" · ".join(meta)}</div>' if meta else ""
        )
        cap = (
            f"<figcaption>{html_lib.escape(cap_main)}</figcaption>"
            if cap_main else ""
        )
        h = float(d.height_pt or 240)
        dtype = html_lib.escape(d.diagram_type or "")
        fig_attrs = f' class="diagram-block" style="min-height:{h:.0f}pt"'
        if dtype:
            fig_attrs += f' data-diagram-type="{dtype}"'
        if d.figure_number:
            fig_attrs += f' data-figure="{html_lib.escape(d.figure_number)}"'
        if d.svg and "<svg" in d.svg:
            body = d.svg
        elif d.src:
            body = (
                f'<img src="{html_lib.escape(d.src)}" alt="" '
                f'class="diagram-img" style="max-height:{h:.0f}pt">'
            )
        else:
            body = '<div class="diagram-empty">Diagram</div>'
        return (
            f"<figure{fig_attrs}>"
            f"{title}{body}{cap}{meta_html}</figure>"
        )

    def _render_calculation(self, c: CalculationBlock) -> str:
        title = html_lib.escape(c.title or c.profile or "Calculation")
        status = html_lib.escape(c.status_label or c.status or "")
        formula = html_lib.escape(c.formula_latex or c.formula_code or "")
        bind = c.binding or {}
        mat = bind.get("material") or {}
        sec = bind.get("section") or {}
        bind_html = ""
        if mat or sec:
            bits = []
            if mat:
                bits.append(html_lib.escape(str(mat.get("label") or mat.get("grade") or "")))
            if sec:
                bits.append(html_lib.escape(str(sec.get("designation") or "")))
            bind_html = f'<p class="calc-binding">{" · ".join(bits)}</p>'
        rows = []
        for inp in c.inputs or []:
            if not isinstance(inp, dict):
                continue
            key = html_lib.escape(str(inp.get("key") or ""))
            val = inp.get("value")
            unit = html_lib.escape(str(inp.get("unit") or ""))
            src = html_lib.escape(str(inp.get("source") or "—"))
            st = html_lib.escape(str(inp.get("status") or ""))
            if val is None:
                vcell = f'<span class="calc-missing">missing ({st})</span>'
            else:
                vcell = f"{html_lib.escape(str(val))} {unit}".strip()
            rows.append(
                f"<tr><td><code>{key}</code></td><td>{vcell}</td>"
                f"<td class=\"calc-src\">{src}</td></tr>"
            )
        out_rows = []
        for out in c.outputs or []:
            if not isinstance(out, dict):
                continue
            key = html_lib.escape(str(out.get("key") or ""))
            val = out.get("value")
            unit = html_lib.escape(str(out.get("unit") or ""))
            if val is None:
                vcell = "—"
            else:
                vcell = f"<strong>{html_lib.escape(str(val))} {unit}</strong>".strip()
            out_rows.append(f"<tr><td><code>{key}</code></td><td>{vcell}</td></tr>")
        assumptions = ""
        if c.assumptions:
            items = "".join(
                f"<li>{html_lib.escape(str(a))}</li>" for a in c.assumptions
            )
            assumptions = (
                f'<p class="calc-assump-h">Assumptions</p>'
                f'<ul class="calc-assump">{items}</ul>'
            )
        conf = ""
        if c.status == "confirmed" and c.confirmed_at:
            by = f" by {html_lib.escape(c.confirmed_by)}" if c.confirmed_by else ""
            conf = (
                f'<p class="calc-confirmed">Confirmed{by}'
                f" · {html_lib.escape(str(c.confirmed_at)[:10])}"
                f" · rev {int(c.revision or 1)}</p>"
            )
        disc = html_lib.escape(
            c.disclaimer
            or "Library formula only — confirm before formal use."
        )
        return (
            f'<aside class="calculation-block" data-status="{html_lib.escape(c.status or "")}"'
            f' data-profile="{html_lib.escape(c.profile or "")}">'
            f'<h3 class="calc-title">{title}</h3>'
            f'<p class="calc-status">{status}</p>'
            f"{bind_html}"
            f'<p class="calc-formula"><code>{formula}</code></p>'
            f'<table class="calc-inputs"><thead><tr>'
            f"<th>Input</th><th>Value</th><th>Source</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
            f'<table class="calc-outputs"><thead><tr>'
            f"<th>Output</th><th>Value</th></tr></thead>"
            f"<tbody>{''.join(out_rows)}</tbody></table>"
            f"{assumptions}{conf}"
            f'<p class="calc-disclaimer">{disc}</p>'
            f"</aside>"
        )

    def _render_material(self, m: MaterialBlock) -> str:
        binding = m.binding or {}
        mat = binding.get("material") or {}
        sec = binding.get("section") or {}
        title = html_lib.escape(
            m.title or mat.get("label") or sec.get("designation") or "Material"
        )
        rows = []
        for pk, pv in (mat.get("properties") or {}).items():
            if not isinstance(pv, dict):
                continue
            val = pv.get("value")
            unit = html_lib.escape(str(pv.get("unit") or ""))
            note = html_lib.escape(str(pv.get("note") or ""))
            if val is None:
                vcell = '<span class="calc-missing">missing — datasheet</span>'
            else:
                vcell = f"{html_lib.escape(str(val))} {unit}".strip()
            rows.append(
                f"<tr><td><code>{html_lib.escape(str(pk))}</code></td>"
                f"<td>{vcell}</td><td>{note}</td></tr>"
            )
        sec_html = ""
        if sec:
            sec_rows = []
            for pk, pv in (sec.get("properties") or {}).items():
                if not isinstance(pv, dict) or pv.get("value") is None:
                    continue
                sec_rows.append(
                    f"<tr><td><code>{html_lib.escape(str(pk))}</code></td>"
                    f"<td>{html_lib.escape(str(pv['value']))} "
                    f"{html_lib.escape(str(pv.get('unit') or ''))}</td></tr>"
                )
            sec_html = (
                f'<p class="calc-assump-h">Section: '
                f'{html_lib.escape(str(sec.get("designation") or ""))}</p>'
                f'<table class="calc-outputs"><tbody>{"".join(sec_rows)}</tbody></table>'
            )
        notes = "".join(
            f"<li>{html_lib.escape(str(n))}</li>"
            for n in (binding.get("notes") or mat.get("design_notes") or [])
        )
        notes_html = f'<ul class="calc-assump">{notes}</ul>' if notes else ""
        disc = html_lib.escape(
            m.disclaimer
            or "Material catalog for documentation groundwork only."
        )
        return (
            f'<aside class="material-block calculation-block">'
            f'<h3 class="calc-title">{title}</h3>'
            f'<table class="calc-inputs"><thead><tr>'
            f"<th>Property</th><th>Value</th><th>Note</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
            f"{sec_html}{notes_html}"
            f'<p class="calc-disclaimer">{disc}</p>'
            f"</aside>"
        )

    def _render_form_section(self, section: FormSection) -> str:
        cols = "cols-2" if int(section.columns or 1) == 2 else "cols-1"
        fields_html = "".join(
            self._render_form_field(f) for f in (section.fields or [])
        )
        return f'<div class="form-section {cols}">{fields_html}</div>'

    def _render_form_field(self, f: FormField) -> str:
        label = html_lib.escape(f.label or f.key or "")
        required = " required" if f.required else ""
        missing = f.value is None or f.value == "" or f.value == "[MANGLER]"
        ftype = (f.field_type or "text").lower()
        if ftype == "check":
            ftype = "checkbox"

        if ftype == "rating3":
            return self._render_rating3_field(f)
        if ftype == "checkbox":
            checked = " checked" if f.value else ""
            return (
                f'<div class="form-field checkbox{required}">'
                f"<label>{label}</label>"
                f'<input type="checkbox"{checked} disabled>'
                f"</div>"
            )
        if ftype == "measure":
            if missing:
                val = "—"
            else:
                val = f"{f.value} {f.unit or ''}".strip()
            miss = " missing" if missing else ""
            return (
                f'<div class="form-field measure{miss}{required}">'
                f"<label>{label}</label>"
                f'<span class="value">{html_lib.escape(val)}</span>'
                f"</div>"
            )
        if ftype == "signature":
            return (
                f'<div class="form-field{required}">'
                f"<label>{label}</label>"
                f'<div class="signature-line"></div></div>'
            )

        display = "—" if missing else str(f.value)
        miss = " missing" if missing else ""
        return (
            f'<div class="form-field{miss}{required}">'
            f"<label>{label}</label>"
            f'<span class="value">{html_lib.escape(display)}</span>'
            f"</div>"
        )

    def _render_rating3_field(self, f: FormField) -> str:
        colors = [("ok", "green"), ("attention", "yellow"), ("immediate", "red")]
        # Also accept 1/2/3 or g/y/r aliases
        raw = f.value
        aliases = {
            "ok": "ok", "green": "ok", "g": "ok", "1": "ok",
            "attention": "attention", "yellow": "attention", "y": "attention", "2": "attention",
            "immediate": "immediate", "red": "immediate", "r": "immediate", "3": "immediate",
        }
        active_key = aliases.get(str(raw).lower().strip()) if raw not in (None, "") else None
        boxes = []
        for key, css in colors:
            active = " active" if active_key == key else ""
            boxes.append(f'<span class="rating-box {css}{active}"></span>')
        return (
            f'<div class="form-field rating3">'
            f"<label>{html_lib.escape(f.label or f.key or '')}</label>"
            f'<div class="rating-group">{"".join(boxes)}</div></div>'
        )

    def _render_signature(self, sig: SignatureBlock) -> str:
        name = html_lib.escape(sig.name or "")
        date = html_lib.escape(sig.date or "")
        img = ""
        if sig.image:
            img = (
                f'<img class="sig-image" src="{html_lib.escape(sig.image)}" '
                f'alt="signature">'
            )
        return (
            '<div class="signature-block">'
            f"{img}"
            '<div class="sig-line"></div>'
            '<div class="sig-meta">'
            f"<span>{html_lib.escape(sig.label)}</span>"
            f"<span>{name}</span>"
            f"<span>{date}</span>"
            "</div></div>"
        )

    def _render_rating_legend(self) -> str:
        return (
            '<div class="rating-legend">'
            '<span class="rating-box green active"></span> OK'
            '<span class="rating-box yellow active"></span> May require future attention'
            '<span class="rating-box red active"></span> Requires immediate attention'
            "</div>"
        )

    def _render_procedure(self, proc: Procedure) -> str:
        steps = []
        for s in proc.steps or []:
            warn = (
                f'<div class="step-warning">{html_lib.escape(s.warning)}</div>'
                if s.warning else ""
            )
            steps.append(
                '<div class="procedure-step">'
                f'<div class="step-number">{int(s.number)}</div>'
                '<div class="step-body">'
                f"<h4>{html_lib.escape(s.title)}</h4>"
                f"<p>{html_lib.escape(s.description)}</p>{warn}"
                "</div></div>"
            )
        prereq = (
            f'<p class="prerequisite"><strong>Prerequisite:</strong> '
            f"{html_lib.escape(proc.prerequisite)}</p>"
            if proc.prerequisite else ""
        )
        return (
            f'<div class="procedure"><h3>{html_lib.escape(proc.title)}</h3>'
            f"{prereq}{''.join(steps)}</div>"
        )

    def _render_timeline(self, tl: Timeline) -> str:
        events = []
        for e in tl.events or []:
            events.append(
                f'<div class="timeline-event status-{html_lib.escape(e.status)}">'
                f'<div class="timeline-date">{html_lib.escape(e.date)}</div>'
                '<div class="timeline-content">'
                f"<strong>{html_lib.escape(e.title)}</strong>"
                f"<p>{html_lib.escape(e.description)}</p>"
                "</div></div>"
            )
        return f'<div class="timeline">{"".join(events)}</div>'

    def _render_bom(self, bom: BillOfMaterials) -> str:
        rows = []
        for item in bom.items or []:
            rows.append(
                "<tr>"
                f"<td>{html_lib.escape(item.part_number)}</td>"
                f"<td>{html_lib.escape(item.description)}</td>"
                f'<td class="num">{html_lib.escape(item.quantity)}</td>'
                f"<td>{html_lib.escape(item.unit)}</td>"
                f"<td>{html_lib.escape(item.material or '')}</td>"
                f"<td>{html_lib.escape(item.remark or '')}</td>"
                "</tr>"
            )
        caption = (
            f"<caption>{html_lib.escape(bom.caption)}</caption>"
            if bom.caption else ""
        )
        title = f"<h3>{html_lib.escape(bom.title)}</h3>" if bom.title else ""
        return f"""
{title}
<table class="bom-table">
  {caption}
  <thead><tr>
    <th>Part No.</th><th>Description</th><th>Qty</th>
    <th>Unit</th><th>Material</th><th>Remark</th>
  </tr></thead>
  <tbody>{''.join(rows)}</tbody>
</table>"""

    def _render_process_flow(self, flow: ProcessFlow) -> str:
        steps = []
        for s in flow.steps or []:
            steps.append(
                '<div class="process-step">'
                f'<div class="process-number">{int(s.number)}</div>'
                f'<div class="process-title">{html_lib.escape(s.title)}</div>'
                f'<div class="process-desc">{html_lib.escape(s.description)}</div>'
                "</div>"
            )
        direction = "horizontal" if flow.direction == "horizontal" else "vertical"
        return f'<div class="process-flow {direction}">{"".join(steps)}</div>'

    def _render_technical_data(self, data: TechnicalData) -> str:
        rows = []
        for pair in data.items or []:
            if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                k, v = pair[0], pair[1]
            else:
                continue
            rows.append(
                f"<tr><th>{html_lib.escape(str(k))}</th>"
                f"<td>{html_lib.escape(str(v))}</td></tr>"
            )
        title = f"<h3>{html_lib.escape(data.title)}</h3>" if data.title else ""
        return f'{title}<table class="tech-data">{"".join(rows)}</table>'

    def _render_parameter_grid(self, grid: ParameterGrid) -> str:
        title = (
            f"<h3>{html_lib.escape(grid.title)}</h3>" if grid.title else ""
        )
        items = []
        for p in grid.items or []:
            unit = f" {html_lib.escape(p.unit)}" if p.unit else ""
            items.append(
                '<div class="param-item">'
                f'<span class="param-name">{html_lib.escape(p.name)}</span>'
                f'<span class="param-value">{html_lib.escape(p.value)}{unit}</span>'
                "</div>"
            )
        cols = int(grid.columns or 2)
        return (
            f'<div class="parameter-grid cols-{cols}">'
            f"{title}{''.join(items)}</div>"
        )

    def _render_engineering_table(self, table: EngineeringTable) -> str:
        thead = "".join(
            f"<th>{html_lib.escape(h)}</th>" for h in (table.headers or [])
        )
        unit_row = ""
        if table.units:
            cells = "".join(
                f'<td class="unit">{html_lib.escape(u)}</td>'
                for u in table.units
            )
            unit_row = f'<tr class="units">{cells}</tr>'
        rows_html = []
        numeric = set(table.numeric_cols or [])
        for row in table.rows or []:
            cells = []
            for i, cell in enumerate(row):
                align = " num" if i in numeric else ""
                cells.append(
                    f'<td class="{align.strip()}">'
                    f"{html_lib.escape(str(cell))}</td>"
                )
            rows_html.append(f"<tr>{''.join(cells)}</tr>")
        footnotes = "".join(
            f'<p class="footnote">{html_lib.escape(f)}</p>'
            for f in (table.footnotes or [])
        )
        caption = (
            f"<caption>{html_lib.escape(table.caption)}</caption>"
            if table.caption else ""
        )
        return f"""
<table class="eng-table spec-table">
  {caption}
  <thead><tr>{thead}</tr></thead>
  <tbody>{unit_row}{''.join(rows_html)}</tbody>
</table>
<div class="footnotes">{footnotes}</div>"""

    def _render_revision_history(self, rev: RevisionHistory) -> str:
        rows = []
        for e in rev.entries or []:
            rows.append(
                "<tr>"
                f"<td>{html_lib.escape(e.rev)}</td>"
                f"<td>{html_lib.escape(e.date)}</td>"
                f"<td>{html_lib.escape(e.description)}</td>"
                f"<td>{html_lib.escape(e.author)}</td>"
                "</tr>"
            )
        return f"""
<div class="revision-history">
  <h3>{html_lib.escape(rev.title)}</h3>
  <table class="rev-table">
    <thead><tr>
      <th>Rev</th><th>Date</th><th>Description</th><th>Author</th>
    </tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</div>"""

    def _render_drawing_reference(self, d: DrawingReference) -> str:
        sheet = f" · Sheet {html_lib.escape(d.sheet)}" if d.sheet else ""
        date = f" {html_lib.escape(d.date)}" if d.date else ""
        return (
            '<div class="drawing-reference">'
            '<div class="drawing-label">Drawing</div>'
            f'<div class="drawing-id">{html_lib.escape(d.number)}'
            f" — {html_lib.escape(d.title)}</div>"
            f'<div class="drawing-meta">Rev {html_lib.escape(d.revision)}'
            f"{date}{sheet}</div></div>"
        )

    def _render_toc(self, toc: TableOfContentsBlock) -> str:
        items = []
        for e in toc.entries or []:
            pad = max(0, int(e.level or 1) - 1) * 12
            page = (
                f'<span class="toc-page">{html_lib.escape(str(e.page_hint))}</span>'
                if e.page_hint else '<span class="toc-dots"></span>'
            )
            items.append(
                f'<div class="toc-entry level-{int(e.level or 1)}" '
                f'style="padding-left:{pad}pt">'
                f'<span class="toc-title">{html_lib.escape(e.title)}</span>'
                f"{page}</div>"
            )
        title = f"<h3>{html_lib.escape(toc.title)}</h3>" if toc.title else ""
        return f'<nav class="toc table-of-contents">{title}{"".join(items)}</nav>'

    def _render_spec_table(self, table: SpecificationTable) -> str:
        headers = list(table.headers or [])
        # If rows carry notes and last header looks like Comments, include note col
        thead = "".join(f"<th>{html_lib.escape(h)}</th>" for h in headers)
        rows_html = []
        n_value_cols = max(0, len(headers) - 1)
        has_comment_col = bool(headers) and headers[-1].lower() in (
            "comments", "comment", "note", "notes", "merknad",
        )
        if has_comment_col:
            n_value_cols = max(0, len(headers) - 2)
        for row in table.rows or []:
            cells = [f"<th scope=\"row\">{html_lib.escape(row.property)}</th>"]
            vals = list(row.values or [])
            for i in range(n_value_cols):
                v = vals[i] if i < len(vals) else ""
                if row.unit and i == 0 and v and row.unit not in v:
                    v = f"{v} {row.unit}"
                cells.append(f"<td>{html_lib.escape(v)}</td>")
            if has_comment_col:
                note = row.note or (vals[n_value_cols] if len(vals) > n_value_cols else "")
                cells.append(f"<td>{html_lib.escape(note or '')}</td>")
            elif row.note and not has_comment_col:
                # append note into last value cell if no comment column
                if cells:
                    last = cells[-1]
                    cells[-1] = last.replace(
                        "</td>",
                        f" <span class=\"cell-note\">"
                        f"{html_lib.escape(row.note)}</span></td>",
                    )
            rows_html.append(f"<tr>{''.join(cells)}</tr>")
        footnotes = "".join(
            f'<p class="footnote">{html_lib.escape(f)}</p>'
            for f in (table.footnotes or [])
        )
        caption = (
            f"<caption>{html_lib.escape(table.caption)}</caption>"
            if table.caption else ""
        )
        return f"""
<table class="spec-table">
  {caption}
  <thead><tr>{thead}</tr></thead>
  <tbody>{''.join(rows_html)}</tbody>
</table>
<div class="footnotes">{footnotes}</div>"""

    def _css(self) -> str:
        t = self.theme
        return f"""
@page {{ size: A4; margin: {t.page_margin_mm}mm; }}
* {{ box-sizing: border-box; margin: 0; padding: 0;
 -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
html {{ background: {t.page_chrome}; }}
body {{
  font-family: {t.font_sans};
  font-size: {t.body}pt;
  color: {t.text_color};
  line-height: 1.45;
  margin: 0;
  padding: 16px 0;
}}
.document {{
  max-width: 210mm; margin: 0 auto; background: {t.background};
  padding: {t.page_margin_mm}mm; box-shadow: 0 2px 14px rgba(0,0,0,.12);
}}
{grid_css(t.column_count, t.gutter_mm)}
h1 {{ font-size: {t.h1}pt; color: {t.primary_color}; margin: 0 0 8pt;
 font-weight: 900; letter-spacing: -.02em; }}
h2 {{ font-size: {t.h2}pt; color: {t.primary_color};
 border-bottom: 2pt solid {t.primary_color}; padding-bottom: 4pt;
 margin: 18pt 0 10pt; font-weight: 800; }}
h3 {{ font-size: {t.h3}pt; margin: 10pt 0 4pt; font-weight: 700; }}
.accent-bar {{ width: 48px; height: 3px; background: {t.accent}; margin-bottom: 10pt; }}
.hero {{
  display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 16pt;
  margin-bottom: 20pt; align-items: center;
}}
.summary {{ font-size: {t.body + 1}pt; color: {t.muted_color}; }}
.hero-bullets {{ padding-left: 16pt; margin-top: 10pt; }}
.hero-bullets li {{ margin-bottom: 4pt; }}
.hero-img {{ max-width: 100%; height: auto; display: block; }}
.feature-grid {{ display: grid; gap: 10pt; margin: 12pt 0; }}
.feature-grid.cols-2 {{ grid-template-columns: 1fr 1fr; }}
.feature-grid.cols-3 {{ grid-template-columns: 1fr 1fr 1fr; }}
.feature-card, .stakeholder-card {{
  border: {getattr(self.design, 'card_border_width', 0.5)}pt solid {getattr(self.design, 'card_border_color', t.border_color)};
  border-radius: {getattr(self.design, 'radius_card', 6.0)}pt;
  padding: {getattr(self.design, 'card_padding', 16.0) * 0.65:.1f}pt {getattr(self.design, 'card_padding', 16.0) * 0.75:.1f}pt;
  background: {getattr(self.design, 'card_background', '#FFFFFF')};
}}
.feature-card h3, .stakeholder-card h3 {{
  margin-top: 0; color: {t.primary_color}; font-size: {t.h3}pt; font-weight: 600;
}}
.feature-card p {{ color: {t.muted_color}; font-size: {t.caption}pt; }}
.feature-role, .stakeholder-role {{
  font-size: {t.caption}pt; color: {t.muted_color}; margin-bottom: 4pt;
}}
.stakeholder-list h4 {{
  margin: 8pt 0 2pt; font-size: {t.caption}pt; font-weight: 600; color: {t.muted_color};
}}
.stakeholder-list ul {{ margin: 0; padding-left: 14pt; font-size: {t.caption}pt; }}
.rating {{ margin: 2pt 0 6pt; letter-spacing: 0.05em; }}
.rating-filled {{ color: {getattr(self.design, 'rating_filled', '#1F2937')}; }}
.rating-empty {{ color: {getattr(self.design, 'rating_empty', '#D1D5DB')}; }}
.rating-label {{ color: {t.muted_color}; margin-right: 4pt; font-size: {t.caption}pt; }}
.evaluation-matrix, .comparison-table {{ margin: 12pt 0; }}
.matrix-title, .comparison-title {{
  font-size: {t.h3}pt; font-weight: 600; margin: 0 0 6pt; color: {t.primary_color};
}}
.matrix-table {{
  width: 100%; border-collapse: collapse; font-size: {t.table}pt; margin: 6pt 0;
}}
.matrix-table th, .matrix-table td {{
  border: 1px solid {t.border_color}; padding: 5pt 6pt; text-align: center;
}}
.matrix-table thead th, .matrix-table tbody th {{
  background: #F9FAFB; color: {t.text_color}; font-weight: 600; text-align: left;
}}
.matrix-low {{ background: #ECFDF5; color: #047857; }}
.matrix-medium {{ background: #FFFBEB; color: #D97706; }}
.matrix-high {{ background: #FEF2F2; color: #B91C1C; }}
.matrix-highlight {{ outline: 1.5pt solid {t.primary_color}; font-weight: 700; }}
.matrix-legend {{
  display: flex; flex-wrap: wrap; gap: 8pt; margin-top: 6pt;
  font-size: {t.caption}pt; color: {t.muted_color};
}}
.comparison th:first-child {{ width: 28%; }}
.spec-table {{
  width: 100%; border-collapse: collapse; font-size: {t.table}pt; margin: 10pt 0;
}}
.spec-table th {{
  background: {t.primary_color}; color: #fff; padding: 5pt 6pt;
  text-align: left; font-weight: 700;
}}
.spec-table td, .spec-table tbody th {{
  border: 1px solid {t.border_color}; padding: 4pt 6pt;
}}
.spec-table tbody th {{
  background: #eeebe4; color: {t.text_color}; font-weight: 700; width: 22%;
}}
.spec-table tr:nth-child(even) td {{ background: #f7f6f2; }}
.cell-note {{ color: {t.muted_color}; font-size: {t.caption}pt; }}
.footnotes {{ font-size: {t.caption}pt; color: {t.muted_color}; margin-top: 6pt; }}
.callout {{
  border-left: 3pt solid {t.primary_color}; padding: 8pt 12pt;
  margin: 10pt 0; background: #f7f6f2; font-size: {t.body}pt;
}}
.callout-warning {{ border-left-color: #b45309; background: #fff8eb; }}
.callout-important {{ border-left-color: #b91c1c; background: #fef2f2; }}
.callout-requirement {{ border-left-color: #1d4ed8; background: #eff6ff; }}
.callout-tip {{ border-left-color: {t.accent}; }}
.callout-insight {{ border-left-color: #0f766e; background: #f0fdfa; }}
.callout-quote {{ border-left-color: {t.border_color}; background: #fff; font-style: italic; }}
.callout-attr {{
  display: block; margin-top: 6pt; font-size: {t.caption}pt;
  color: {t.muted_color}; font-style: normal;
}}
.callout-icon {{ margin-right: 4pt; }}
.p-lead {{ font-size: {t.body + 1}pt; color: {t.muted_color}; }}
.p-caption, .p-note {{ font-size: {t.caption}pt; color: {t.muted_color}; }}
figure {{ margin: 12pt 0; }}
figcaption {{ font-size: {t.caption}pt; color: {t.muted_color}; margin-top: 4pt; font-style: italic; }}
.diagram-meta {{ font-size: {t.caption}pt; color: {t.muted_color}; margin-top: 2pt; font-style: normal; }}
.calculation-block {{
  margin: 12pt 0; padding: 10pt 12pt; border: 0.6pt solid {t.border_color};
  page-break-inside: avoid; background: {t.background};
}}
.calc-title {{ font-size: {t.h3}pt; margin: 0 0 4pt; }}
.calc-status {{ font-size: {t.caption}pt; color: {t.muted_color}; margin: 0 0 6pt; }}
.calc-formula {{ margin: 4pt 0 8pt; }}
.calc-inputs, .calc-outputs {{ width: 100%; border-collapse: collapse; margin: 6pt 0; font-size: {t.body}pt; }}
.calc-inputs th, .calc-outputs th, .calc-inputs td, .calc-outputs td {{
  border-bottom: 0.4pt solid {t.border_color}; padding: 3pt 4pt; text-align: left;
}}
.calc-src, .calc-disclaimer, .calc-confirmed {{ font-size: {t.caption}pt; color: {t.muted_color}; }}
.calc-assump-h {{ font-size: {t.caption}pt; margin: 8pt 0 2pt; font-weight: 600; }}
.calc-assump {{ margin: 0 0 6pt 14pt; font-size: {t.caption}pt; }}
.calc-missing {{ color: {t.muted_color}; font-style: italic; }}
.diagram-block {{ margin: 12pt 0; page-break-inside: avoid; }}
.diagram-block svg {{ max-width: 100%; height: auto; display: block; }}
.list-check {{ list-style: none; padding-left: 0; }}
.list-check li::before {{ content: "✓ "; color: {t.primary_color}; font-weight: 700; }}
.procedure-step {{ display: flex; gap: 12pt; margin: 10pt 0; }}
.step-number {{
  width: 28pt; height: 28pt; border-radius: 50%;
  background: {t.primary_color}; color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; flex-shrink: 0;
}}
.step-warning {{ color: #b45309; font-size: 9pt; margin-top: 4pt; }}
.prerequisite {{ font-size: {t.caption}pt; color: {t.muted_color}; margin-bottom: 8pt; }}
.timeline-event {{
  display: flex; gap: 12pt; margin: 8pt 0; padding-left: 8pt;
  border-left: 2pt solid {t.border_color};
}}
.timeline-event.status-current {{ border-left-color: {t.primary_color}; }}
.timeline-date {{ width: 90pt; font-size: 9pt; color: {t.muted_color}; flex-shrink: 0; }}
.bom-table {{ width: 100%; border-collapse: collapse; font-size: {t.table}pt; }}
.bom-table th {{ background: {t.primary_color}; color: #fff; padding: 4pt 6pt; }}
.bom-table td, .bom-table th {{ border: 1px solid {t.border_color}; padding: 3pt 5pt; }}
.bom-table .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
.process-flow.horizontal {{ display: flex; gap: 8pt; flex-wrap: wrap; }}
.process-flow.vertical {{ display: flex; flex-direction: column; gap: 8pt; }}
.process-step {{
  flex: 1; min-width: 120pt; border: 1px solid {t.border_color};
  padding: 8pt; text-align: center; background: #f7f6f2;
}}
.process-number {{
  width: 22pt; height: 22pt; border-radius: 50%;
  background: {t.primary_color}; color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 10pt; margin-bottom: 4pt;
}}
.tech-data {{ width: 100%; border-collapse: collapse; font-size: {t.table}pt; }}
.tech-data th {{
  text-align: left; width: 40%; padding: 3pt 6pt; background: #eeebe4;
}}
.tech-data td {{ padding: 3pt 6pt; border-bottom: 1px solid {t.border_color}; }}
.callout-note {{ border-left-color: {t.secondary_color}; }}
.form-section {{ display: grid; gap: 6pt 12pt; margin: 8pt 0; }}
.form-section.cols-2 {{ grid-template-columns: 1fr 1fr; }}
.form-field {{ display: flex; align-items: baseline; gap: 8pt; min-height: 18pt; }}
.form-field label {{ min-width: 140pt; font-weight: 500; font-size: 9.5pt; }}
.form-field .value {{
  flex: 1; border-bottom: 0.75pt solid {t.border_color};
  padding: 1pt 4pt; font-size: 9.5pt;
}}
.form-field.missing .value {{ background: #fffbeb; color: #92400e; }}
.form-field.required label::after {{ content: " *"; color: #b91c1c; }}
.rating-group {{ display: flex; gap: 4pt; }}
.rating-box {{
  width: 14pt; height: 14pt; border: 1pt solid {t.text_color};
  display: inline-block;
}}
.rating-box.green {{ background: #c6f6d5; }}
.rating-box.yellow {{ background: #fefcbf; }}
.rating-box.red {{ background: #fed7d7; }}
.rating-box.active {{ border-width: 2pt; border-color: {t.primary_color}; }}
.rating-legend {{
  font-size: 8.5pt; margin-bottom: 10pt;
  display: flex; gap: 12pt; align-items: center; flex-wrap: wrap;
}}
.signature-block {{ margin-top: 20pt; }}
.sig-line {{ border-bottom: 1pt solid {t.primary_color}; height: 28pt; margin-bottom: 4pt; }}
.signature-line {{ border-bottom: 1pt solid {t.border_color}; height: 18pt; flex: 1; }}
.sig-meta {{
  display: flex; justify-content: space-between;
  font-size: 8.5pt; color: {t.muted_color};
}}
.sig-image {{ max-height: 36pt; display: block; margin-bottom: 4pt; }}
.diagram-block {{ margin: 12pt 0; }}
.diagram-block svg {{ width: 100%; height: auto; display: block; }}
.diagram-title {{ font-size: {t.h3}pt; margin-bottom: 6pt; }}
.diagram-empty {{
  border: 1px dashed {t.border_color}; padding: 24pt; text-align: center;
  color: {t.muted_color};
}}
@media print {{
  html {{ background: #fff; }}
  body {{ padding: 0; }}
  .document {{ box-shadow: none; max-width: none; padding: 0; }}
}}
"""

    def _css_paginated(self) -> str:
        t = self.theme
        return f"""
@page {{ size: A4; margin: 0; }}
* {{ box-sizing: border-box; margin: 0; padding: 0;
 -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
html {{ background: {t.page_chrome}; }}
body {{
  font-family: {t.font_sans}; font-size: {t.body}pt; color: {t.text_color};
  line-height: 1.45; margin: 0; padding: 16px 0;
}}
.document.paginated {{ max-width: none; margin: 0 auto; background: transparent;
  padding: 0; box-shadow: none; }}
.print-page {{
  position: relative; background: {t.background};
  margin: 0 auto 16px; box-shadow: 0 2px 14px rgba(0,0,0,.12);
  overflow: hidden; page-break-after: always;
}}
.print-page:last-child {{ page-break-after: auto; margin-bottom: 0; }}
.placed {{ overflow: hidden; }}
.placed .hero {{ margin-bottom: 0; height: 100%; }}
.placed h2 {{ margin-top: 0; }}
{grid_css(t.column_count, t.gutter_mm)}
h1 {{ font-size: {t.h1}pt; color: {t.primary_color}; margin: 0 0 8pt;
 font-weight: 900; letter-spacing: -.02em; }}
h2 {{ font-size: {t.h2}pt; color: {t.primary_color};
 border-bottom: 2pt solid {t.primary_color}; padding-bottom: 4pt;
 margin: 0 0 10pt; font-weight: 800; }}
h3 {{ font-size: {t.h3}pt; margin: 10pt 0 4pt; font-weight: 700; }}
.accent-bar {{ width: 48px; height: 3px; background: {t.accent}; margin-bottom: 10pt; }}
.hero {{
  display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 16pt; align-items: center;
}}
.summary {{ font-size: {t.body + 1}pt; color: {t.muted_color}; }}
.hero-bullets {{ padding-left: 16pt; margin-top: 10pt; }}
.hero-img {{ max-width: 100%; height: auto; display: block; }}
.feature-grid {{ display: grid; gap: 10pt; margin: 0; }}
.feature-grid.cols-2 {{ grid-template-columns: 1fr 1fr; }}
.feature-grid.cols-3 {{ grid-template-columns: 1fr 1fr 1fr; }}
.feature-card {{
  border: 1px solid {t.border_color}; padding: 10pt 12pt; background: #f7f6f2;
}}
.feature-card h3 {{ margin-top: 0; color: {t.primary_color}; }}
.feature-card p {{ color: {t.muted_color}; font-size: {t.caption}pt; }}
.feature-metric {{
  font-size: 14pt; font-weight: 700; color: {t.primary_color}; margin-bottom: 2pt;
}}
.img-hero img, .img-figure img, .img-exploded img, .img-component img, .img-diagram img {{
  max-width: 100%; height: auto; display: block;
}}
.img-exploded {{
  border: 0.5pt solid {t.border_color}; padding: 6pt; background: #fafaf8;
}}
.img-hero {{ margin: 0 0 8pt; }}
.img-component {{ max-width: 55%; }}
.parameter-grid {{ display: grid; gap: 4pt 16pt; margin: 0; }}
.parameter-grid.cols-2 {{ grid-template-columns: 1fr 1fr; }}
.param-item {{
  display: flex; justify-content: space-between; gap: 8pt;
  border-bottom: 0.5pt solid {t.border_color}; padding: 3pt 0;
  font-size: {t.table}pt;
}}
.param-value {{ font-variant-numeric: tabular-nums; font-weight: 600; }}
.drawing-reference {{
  border: 0.75pt solid {t.border_color}; padding: 8pt 10pt; background: #f7f6f2;
}}
.drawing-label {{ font-size: {t.caption}pt; color: {t.muted_color}; }}
.drawing-id {{ font-weight: 700; }}
.drawing-meta {{ font-size: {t.caption}pt; color: {t.muted_color}; }}
.revision-history h3 {{ margin: 0 0 6pt; }}
.rev-table, .eng-table {{
  width: 100%; border-collapse: collapse; font-size: {t.table}pt;
}}
.rev-table th, .eng-table th {{
  background: {t.primary_color}; color: #fff; padding: 4pt 6pt; text-align: left;
}}
.rev-table td, .eng-table td {{
  border: 0.5pt solid {t.border_color}; padding: 3pt 5pt;
}}
.eng-table td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
.eng-table tr.units td {{
  font-size: {t.caption}pt; color: {t.muted_color}; background: #f7f6f2;
}}
.spec-table {{
  width: 100%; border-collapse: collapse; font-size: {t.table}pt; margin: 0;
}}
.spec-table th {{
  background: {t.primary_color}; color: #fff; padding: 5pt 6pt;
  text-align: left; font-weight: 700;
}}
.spec-table td, .spec-table tbody th {{
  border: 1px solid {t.border_color}; padding: 4pt 6pt;
}}
.spec-table tbody th {{
  background: #eeebe4; color: {t.text_color}; font-weight: 700; width: 22%;
}}
.spec-table tr:nth-child(even) td {{ background: #f7f6f2; }}
.footnotes {{ font-size: {t.caption}pt; color: {t.muted_color}; margin-top: 6pt; }}
.callout {{
  border-left: 3pt solid {t.primary_color}; padding: 8pt 12pt;
  background: #f7f6f2; font-size: {t.body}pt;
}}
.callout-warning {{ border-left-color: #b45309; background: #fff8eb; }}
.callout-important {{ border-left-color: #b91c1c; background: #fef2f2; }}
.callout-requirement {{ border-left-color: #1d4ed8; background: #eff6ff; }}
.toc-entry {{
  display: flex; justify-content: space-between; gap: 8pt;
  padding: 2pt 0; border-bottom: 0.4pt dotted {t.border_color};
}}
.procedure-step {{ display: flex; gap: 12pt; margin: 10pt 0; }}
.step-number {{
  width: 28pt; height: 28pt; border-radius: 50%;
  background: {t.primary_color}; color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; flex-shrink: 0;
}}
.bom-table {{ width: 100%; border-collapse: collapse; font-size: {t.table}pt; }}
.bom-table th {{ background: {t.primary_color}; color: #fff; padding: 4pt 6pt; }}
.bom-table td, .bom-table th {{ border: 1px solid {t.border_color}; padding: 3pt 5pt; }}
.process-flow.horizontal {{ display: flex; gap: 8pt; flex-wrap: wrap; }}
.process-step {{
  flex: 1; min-width: 120pt; border: 1px solid {t.border_color};
  padding: 8pt; text-align: center; background: #f7f6f2;
}}
.process-number {{
  width: 22pt; height: 22pt; border-radius: 50%;
  background: {t.primary_color}; color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 10pt; margin-bottom: 4pt;
}}
.tech-data {{ width: 100%; border-collapse: collapse; font-size: {t.table}pt; }}
.tech-data th {{ text-align: left; width: 40%; padding: 3pt 6pt; background: #eeebe4; }}
.tech-data td {{ padding: 3pt 6pt; border-bottom: 1px solid {t.border_color}; }}
.timeline-event {{
  display: flex; gap: 12pt; margin: 8pt 0; padding-left: 8pt;
  border-left: 2pt solid {t.border_color};
}}
.form-section {{ display: grid; gap: 6pt 12pt; margin: 8pt 0; }}
.form-section.cols-2 {{ grid-template-columns: 1fr 1fr; }}
.form-field {{ display: flex; align-items: baseline; gap: 8pt; min-height: 18pt; }}
.form-field label {{ min-width: 140pt; font-weight: 500; font-size: 9.5pt; }}
.form-field .value {{
  flex: 1; border-bottom: 0.75pt solid {t.border_color};
  padding: 1pt 4pt; font-size: 9.5pt;
}}
.form-field.missing .value {{ background: #fffbeb; color: #92400e; }}
.rating-group {{ display: flex; gap: 4pt; }}
.rating-box {{
  width: 14pt; height: 14pt; border: 1pt solid {t.text_color};
  display: inline-block;
}}
.rating-box.green {{ background: #c6f6d5; }}
.rating-box.yellow {{ background: #fefcbf; }}
.rating-box.red {{ background: #fed7d7; }}
.rating-box.active {{ border-width: 2pt; border-color: {t.primary_color}; }}
.rating-legend {{
  font-size: 8.5pt; margin-bottom: 10pt;
  display: flex; gap: 12pt; align-items: center; flex-wrap: wrap;
}}
.signature-block {{ margin-top: 8pt; }}
.sig-line {{ border-bottom: 1pt solid {t.text_color}; height: 28pt; margin-bottom: 4pt; }}
.sig-meta {{
  display: flex; justify-content: space-between;
  font-size: {t.caption}pt; color: {t.muted_color};
}}
.diagram-block {{ text-align: center; }}
.diagram-block svg {{ max-width: 100%; height: auto; }}
@media print {{
  html, body {{ background: #fff; padding: 0; }}
  .print-page, .page {{
    box-shadow: none; margin: 0; page-break-after: always;
  }}
  .print-page:last-child, .page:last-child {{ page-break-after: auto; }}
}}
"""
