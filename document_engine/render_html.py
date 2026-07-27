"""Print HTML for multi-page technical documents (datasheet / manual pages).

Visual tokens aligned with form_engine / diagram_engine (Foldok ink),
not generic purple marketing themes.
"""
from __future__ import annotations

import html as html_lib

INK = "#16181D"
PAPER = "#FFFFFF"
MUTED = "#5A6472"
LINE = "#DCD9D0"
SIGNAL = "#F5C400"
SHEET_BG = "#E9E7E0"


def render_document_html(doc: dict) -> str:
    brand = doc.get("brand") or {}
    primary = brand.get("primary_color") or INK
    font = brand.get("font") or "Arial, Helvetica, sans-serif"
    title = html_lib.escape(doc.get("title") or doc.get("name") or "Document")

    pages_html = []
    pages = doc.get("pages") or []
    for i, page in enumerate(pages):
        cls = f"page page-{html_lib.escape(page.get('type') or 'content')}"
        if i == 0:
            cls += " first-page"
        pages_html.append(
            f'<section class="{cls}">{_render_page(page, brand)}</section>'
        )

    return f"""<!DOCTYPE html>
<html lang="no"><head><meta charset="utf-8">
<title>{title}</title>
<style>{_css(primary, font)}</style>
</head><body>
<div class="doc-wrap">
{"".join(pages_html) or "<p>No pages.</p>"}
</div>
</body></html>"""


def _render_page(page: dict, brand: dict) -> str:
    page_type = page.get("type") or "content"
    layout = page.get("layout") or "standard"
    if page_type == "cover" or layout == "hero_split":
        return _cover(page, brand)
    if page_type == "overview" or layout == "component_grid":
        return _overview(page)
    if page_type == "specifications" or layout == "comparison_table":
        return _specifications(page)
    return _standard(page)


def _cover(page: dict, brand: dict) -> str:
    title = html_lib.escape(page.get("title") or "")
    tagline = html_lib.escape(page.get("tagline") or "")
    date = html_lib.escape(str(page.get("date") or ""))
    bullets = "".join(
        f"<li>{html_lib.escape(str(b))}</li>" for b in (page.get("bullet_points") or [])
    )
    hero = page.get("hero_image")
    hero_html = (
        f'<img src="{html_lib.escape(str(hero))}" class="hero-image" alt="">'
        if hero else ""
    )
    brand_name = html_lib.escape(brand.get("name") or "")
    return f"""
<header class="cover-header">
  <div class="brand">{brand_name}</div>
  <div class="date">{date}</div>
</header>
<div class="cover-content">
  <div class="cover-text">
    <h1>{title}</h1>
    <p class="tagline">{tagline}</p>
    <ul class="bullets">{bullets}</ul>
  </div>
  <div class="cover-image">{hero_html}</div>
</div>"""


def _overview(page: dict) -> str:
    title = html_lib.escape(page.get("title") or "System Overview")
    cards = []
    for c in page.get("components") or []:
        name = html_lib.escape(c.get("name") or "")
        desc = html_lib.escape(c.get("description") or "")
        cards.append(
            f'<div class="component-card"><h3>{name}</h3><p>{desc}</p></div>'
        )
    return f"<h2>{title}</h2><div class=\"component-grid\">{''.join(cards)}</div>"


def _specifications(page: dict) -> str:
    title = html_lib.escape(page.get("title") or "Specifications")
    table = page.get("table") or {}
    headers = table.get("headers") or []
    rows = table.get("rows") or []
    footnotes = table.get("footnotes") or []
    thead = "".join(f"<th>{html_lib.escape(str(h))}</th>" for h in headers)
    tbody = []
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            tag = "th" if i == 0 else "td"
            cells.append(f"<{tag}>{html_lib.escape(str(cell))}</{tag}>")
        tbody.append(f"<tr>{''.join(cells)}</tr>")
    notes = "".join(
        f'<p class="footnote">{html_lib.escape(str(n))}</p>' for n in footnotes
    )
    return f"""
<h2>{title}</h2>
<table class="spec-table">
  <thead><tr>{thead}</tr></thead>
  <tbody>{''.join(tbody)}</tbody>
</table>
<div class="footnotes">{notes}</div>"""


def _standard(page: dict) -> str:
    title = html_lib.escape(page.get("title") or "")
    content = page.get("content") or ""
    if isinstance(content, str):
        content = html_lib.escape(content)
    sections = []
    for section in page.get("sections") or []:
        st = html_lib.escape(section.get("title") or "")
        sc = section.get("content") or ""
        if isinstance(sc, str):
            sc = html_lib.escape(sc)
        body = f"<h3>{st}</h3><div class='section-body'>{sc}</div>"
        if section.get("table"):
            body += _specifications({"title": "", "table": section["table"]}).replace(
                "<h2></h2>", ""
            )
        sections.append(body)
    return f"<h2>{title}</h2>{content}{''.join(sections)}"


def _css(primary: str, font: str) -> str:
    return f"""
@page {{ size: A4; margin: 16mm 14mm; }}
* {{ box-sizing: border-box; margin: 0; padding: 0;
 -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
html {{ background: {SHEET_BG}; }}
body {{
  font-family: {font}; font-size: 10pt; color: {INK}; line-height: 1.45;
  margin: 0; padding: 16px 0;
}}
.doc-wrap {{ max-width: 210mm; margin: 0 auto; }}
.page {{
  background: {PAPER}; width: 210mm; min-height: 297mm; margin: 0 auto 18px;
  padding: 16mm 14mm; box-shadow: 0 2px 14px rgba(0,0,0,.12);
  page-break-after: always;
}}
.page:last-child {{ page-break-after: auto; margin-bottom: 0; }}
h1 {{ font-size: 22pt; font-weight: 900; color: {primary}; letter-spacing: -.02em;
 margin-bottom: 8px; }}
h2 {{ font-size: 13pt; font-weight: 800; color: {primary};
 border-bottom: 2.5px solid {primary}; padding-bottom: 4px; margin: 0 0 12px; }}
h3 {{ font-size: 11pt; font-weight: 700; color: {INK}; margin: 14px 0 4px; }}
.cover-header {{
  display: flex; justify-content: space-between; align-items: baseline;
  margin-bottom: 28px; font-size: 9pt; color: {MUTED};
  border-bottom: 2.5px solid {INK}; padding-bottom: 8px;
}}
.brand {{ font-weight: 900; color: {INK}; font-size: 12pt; }}
.brand::after {{
  content: ""; display: block; width: 48px; height: 3px; background: {SIGNAL};
  margin-top: 4px;
}}
.cover-content {{
  display: grid; grid-template-columns: 1.15fr 0.85fr; gap: 22px;
  align-items: center; min-height: 170mm;
}}
.tagline {{ font-size: 12pt; color: {MUTED}; margin: 8px 0 16px; }}
.bullets {{ padding-left: 18px; }}
.bullets li {{ margin-bottom: 6px; }}
.hero-image {{ max-width: 100%; height: auto; display: block; }}
.component-grid {{
  display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 8px;
}}
.component-card {{
  border: 1px solid {LINE}; padding: 12px 14px; background: #f7f6f2;
}}
.component-card h3 {{ margin-top: 0; color: {primary}; }}
.component-card p {{ color: {MUTED}; font-size: 9.5pt; }}
.spec-table {{
  width: 100%; border-collapse: collapse; font-size: 8.5pt; margin-top: 8px;
}}
.spec-table th {{
  background: {primary}; color: #fff; padding: 6px 8px; text-align: left;
  font-weight: 700;
}}
.spec-table td, .spec-table th {{ border: 1px solid {LINE}; padding: 5px 7px; }}
.spec-table tr:nth-child(even) {{ background: #f7f6f2; }}
.spec-table tbody th {{
  background: #eeebe4; color: {INK}; font-weight: 700;
}}
.footnotes {{ margin-top: 12px; font-size: 8pt; color: {MUTED}; }}
.footnote {{ margin: 2px 0; }}
.section-body {{ margin-bottom: 8px; }}
@media print {{
  html {{ background: #fff; }}
  body {{ padding: 0; }}
  .page {{ box-shadow: none; margin: 0; width: auto; min-height: auto; padding: 0; }}
}}
"""
