"""Overlay renderer — original page image + positioned field widgets.

Never redraws the paper chrome. Values appear as chips/marks on top.
"""
from __future__ import annotations

import html as html_lib

from .model import validate_package

INK = "#16181D"
FACT = "#1450B4"
OK = "#2e7d32"
WARN = "#fbc02d"
BAD = "#d32f2f"
RATING_FILL = {"ok": "g", "attention": "y", "immediate": "r"}


def _pct(bbox: dict, axis: str) -> float:
    # bbox in 0..1000 → percent of page
    v = float(bbox.get(axis) or 0)
    return round(100.0 * v / 1000.0, 3)


def _widget(f: dict) -> str:
    t = f.get("type") or "text"
    val = f.get("value")
    src = f.get("source")
    label = html_lib.escape(f.get("label") or "")
    empty = val in (None, "")
    title = label

    if t == "rating3":
        on = RATING_FILL.get(val) if val else None
        boxes = []
        for color in ("g", "y", "r"):
            cls = f"ov-cb {color}" + (" on" if on == color else "")
            boxes.append(f'<span class="{cls}"></span>')
        return f'<div class="ov-rating" title="{title}">{"".join(boxes)}</div>'

    if t == "check":
        on = " on" if val in (True, "true", "1", "yes", "ok", "x") else ""
        return f'<div class="ov-check" title="{title}"><span class="ov-cb{on}"></span></div>'

    if not empty:
        unit = html_lib.escape(str(f.get("unit") or ""))
        cited = " cited" if src else ""
        text = html_lib.escape(str(val))
        if unit and t == "measure":
            text = f"{text} {unit}"
        return f'<div class="ov-chip{cited}" title="{title}">{text}</div>'

    # Empty — thin underline / box so technician sees the slot without redrawing paper
    return f'<div class="ov-blank" title="{title}"></div>'


def render_overlay(pkg: dict, company: dict | None = None) -> str:
    pkg = validate_package(pkg)
    company = company or pkg.get("company") or {}
    title = html_lib.escape(pkg.get("title") or "Skjema")
    pages = pkg.get("backgrounds") or []
    fields = pkg.get("fields") or []
    by_page: dict[int, list] = {}
    for f in fields:
        by_page.setdefault(int(f.get("page") or 0), []).append(f)

    page_html = []
    for i, bg in enumerate(pages):
        mime = bg.get("mime") or "image/jpeg"
        b64 = bg.get("data_b64") or ""
        widgets = []
        for f in by_page.get(i, []):
            bb = f.get("bbox") or {}
            style = (
                f"left:{_pct(bb,'x')}%;top:{_pct(bb,'y')}%;"
                f"width:{_pct(bb,'w')}%;height:{max(_pct(bb,'h'), 1.2)}%;"
            )
            widgets.append(
                f'<div class="ov-field" style="{style}" data-key="'
                f'{html_lib.escape(f.get("key") or "")}">{_widget(f)}</div>'
            )
        page_html.append(
            f'<section class="ov-page" data-page="{i}">'
            f'<img class="ov-bg" alt="page {i+1}" '
            f'src="data:{mime};base64,{b64}" />'
            f'<div class="ov-layer">{"".join(widgets)}</div>'
            f"</section>"
        )

    logo = (
        f'<div class="logo">{html_lib.escape(company.get("name", ""))}</div>'
        if company.get("name") else ""
    )
    w_in = pkg.get("page_width_in") or 8.5
    return f"""<!DOCTYPE html><html lang="no"><head><meta charset="utf-8">
<title>{title}</title>
<style>
@page{{size:letter portrait;margin:0}}
*{{box-sizing:border-box;margin:0;padding:0;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
html{{background:#E9E7E0}}
body{{font:9pt/1.3 Arial,Helvetica,sans-serif;color:{INK};margin:0;padding:16px 0}}
.banner{{width:{w_in}in;margin:0 auto 10px;display:flex;align-items:baseline;gap:10px;
 padding:0 4px;color:#555;font-size:8pt}}
.banner h1{{font-size:11pt;color:{INK};font-weight:800}}
.logo{{font-weight:900;margin-right:8px;color:{INK}}}
.ov-page{{position:relative;width:{w_in}in;margin:0 auto 18px;
 box-shadow:0 2px 14px rgba(0,0,0,.15);background:#fff}}
.ov-bg{{display:block;width:100%;height:auto}}
.ov-layer{{position:absolute;inset:0}}
.ov-field{{position:absolute;overflow:hidden}}
.ov-chip{{font-family:'IBM Plex Mono',monospace;font-size:8pt;background:rgba(234,241,253,.92);
 color:{FACT};border-bottom:1.6px solid {FACT};padding:1px 4px;border-radius:2px;
 height:100%;display:flex;align-items:center}}
.ov-chip.cited{{box-shadow:inset 0 0 0 1px rgba(20,80,180,.25)}}
.ov-blank{{width:100%;height:70%;margin-top:15%;border-bottom:1px solid rgba(0,0,0,.35)}}
.ov-rating,.ov-check{{display:flex;gap:3px;align-items:center;height:100%}}
.ov-cb{{width:11px;height:11px;border:1.4px solid #111;display:inline-block;background:rgba(255,255,255,.5)}}
.ov-cb.g{{border-color:{OK}}} .ov-cb.y{{border-color:{WARN}}} .ov-cb.r{{border-color:{BAD}}}
.ov-cb.on{{background:#111}} .ov-cb.g.on{{background:{OK}}} .ov-cb.y.on{{background:{WARN}}} .ov-cb.r.on{{background:{BAD}}}
@media print{{html{{background:#fff}} body{{padding:0}} .banner{{display:none}}
 .ov-page{{box-shadow:none;margin:0;page-break-after:always}}}}
</style></head><body>
<div class="banner">{logo}<h1>{title}</h1>
<span>Foldok · faithful overlay — original layout preserved</span></div>
{"".join(page_html) or "<p style='text-align:center'>No page backgrounds — use structure mode.</p>"}
</body></html>"""
