"""Structure-mode renderer (Form Engine v1 letter sheet).

Used when no page backgrounds exist. Overlay mode lives in render_overlay.py.
Self-test: python -m form_engine
"""
from __future__ import annotations

import html
import re

INK = "#16181D"
PAPER = "#FFFFFF"
LINE = "#111"
SIGNAL = "#F5C400"
OK = "#2e7d32"
WARN = "#fbc02d"
BAD = "#d32f2f"
FACT = "#1450B4"

RATING_FILL = {"ok": "g", "attention": "y", "immediate": "r"}


# ── rendering ────────────────────────────────────────────────────────
def _field(f):
    """One field row. Types: rating3 check measure text date signature photo + extras."""
    t = f.get("type", "text")
    label = html.escape(f.get("label") or f.get("label_no") or "")
    val = f.get("value")
    src = f.get("source")
    req = f.get("required")
    empty = val in (None, "")
    star = '<span class="req">*</span>' if req and empty else ""

    if t == "rating3":
        on = RATING_FILL.get(val) if val else None
        boxes = []
        for color in ("g", "y", "r"):
            cls = f"cb {color}" + (" on" if on == color else "")
            boxes.append(f'<span class="{cls}"></span>')
        return (
            f'<div class="row"><span class="cbs">{"".join(boxes)}</span>'
            f'<span class="lbl">{label}{star}</span></div>'
        )
    if t == "check":
        on = " on" if val in (True, "true", "1", "yes", "ok", "x") else ""
        return (
            f'<div class="row"><span class="cbs"><span class="cb{on}"></span></span>'
            f'<span class="lbl">{label}{star}</span></div>'
        )
    if t == "measure":
        unit = html.escape(f.get("unit") or "")
        cells = f.get("cells") or [""]
        if isinstance(val, dict):
            inner = " ".join(
                f'<span class="mcell">{html.escape(c)}'
                f'<span class="mline">{html.escape(str(val.get(c, "") or ""))}</span>'
                f'<span class="unit">{unit}</span></span>' for c in cells)
            pre = ""
        elif val is not None and val != "":
            chip = (
                f'<span class="chip{" cited" if src else ""}">'
                f'{html.escape(str(val))} {unit}</span>'
            )
            inner = " ".join(
                f'<span class="mcell">{html.escape(c)}<span class="mline"></span>'
                f'<span class="unit">{unit}</span></span>' for c in cells)
            pre = f" {chip}"
        else:
            inner = " ".join(
                f'<span class="mcell">{html.escape(c)}<span class="mline"></span>'
                f'<span class="unit">{unit}</span></span>' for c in cells)
            pre = ""
        return (
            f'<div class="row meas"><span class="lbl">{label}{star}</span>'
            f'<span class="mgrp">{inner}{pre}</span></div>'
        )
    if t == "signature":
        if val:
            return (
                f'<div class="row sig"><span class="lbl">{label}</span>'
                f'<span class="chip">{html.escape(str(val))}</span></div>'
            )
        return (
            f'<div class="row sig"><span class="lbl">{label}</span>'
            f'<span class="sline"></span></div>'
        )

    if t == "vin_boxes":
        n = f.get("count", 17)
        boxes = "".join('<span class="vinb"></span>' for _ in range(n))
        return (
            f'<div class="row vin"><span class="lbl b">{label}</span>'
            f'<span class="vinwrap">{boxes}</span></div>'
        )
    if t == "checkbox_right":
        return (
            f'<div class="row cr"><span class="lbl">{label}</span>'
            f'<span class="sqbox"></span></div>'
        )
    if t == "note":
        return f'<div class="note">{label}</div>'
    if t == "terms":
        return f'<div class="terms">{label}</div>'
    if t == "wedge_chart":
        rows = ""
        for band in f.get("bands", []):
            rows += (
                '<div class="wrow"><span class="wg"></span><span class="wy"></span>'
                '<span class="wr"></span></div>'
                f'<div class="wlab"><span>{html.escape(band[0])}</span>'
                f'<span>{html.escape(band[1])}</span>'
                f'<span>{html.escape(band[2])}</span></div>'
            )
        cap = "".join(
            f'<div class="wcap">{html.escape(c)}</div>' for c in f.get("captions", []))
        return (
            f'<div class="wchart"><div class="wtri">{rows}</div>'
            f'<div class="wcaps">{cap}</div></div>'
        )
    if t == "vehicle_diagram":
        return VEHICLE_SVG
    if t == "multiline":
        n = f.get("lines", 3)
        ls = "".join('<div class="mline2"></div>' for _ in range(n))
        head = f'<div class="row"><span class="lbl b">{label}</span></div>' if label else ""
        return head + ls

    # text / date / photo
    if val is not None and val != "":
        chip = (
            f'<span class="chip{" cited" if src else ""}">'
            f'{html.escape(str(val))}</span>'
        )
        return f'<div class="row"><span class="lbl">{label}</span>{chip}</div>'
    return (
        f'<div class="row"><span class="lbl">{label}{star}</span>'
        f'<span class="line"></span></div>'
    )


VEHICLE_SVG = """<svg class="cardiag" viewBox="0 0 120 150">
<rect x="34" y="10" width="52" height="130" rx="16" fill="none" stroke="#111" stroke-width="1.6"/>
<rect x="41" y="30" width="38" height="26" rx="4" fill="none" stroke="#111" stroke-width="1.2"/>
<rect x="41" y="66" width="38" height="34" rx="3" fill="none" stroke="#111" stroke-width="1.2"/>
<ellipse cx="28" cy="34" rx="11" ry="13" fill="none" stroke="#111" stroke-width="1.6"/>
<ellipse cx="92" cy="34" rx="11" ry="13" fill="none" stroke="#111" stroke-width="1.6"/>
<ellipse cx="28" cy="116" rx="11" ry="13" fill="none" stroke="#111" stroke-width="1.6"/>
<ellipse cx="92" cy="116" rx="11" ry="13" fill="none" stroke="#111" stroke-width="1.6"/>
</svg>"""


def _section(s):
    cols = s.get("columns", 1)
    side = s.get("side_label")
    if s.get("kind") == "header_grid":
        cells = "".join(
            f'<div class="hg-col">'
            + (f'<div class="redhead">{html.escape(c["title"])}</div>'
               if c.get("title") else "")
            + "".join(_field(f) for f in c.get("fields", []))
            + "</div>"
            for c in s.get("columns_data") or [])
        return f'<div class="hgrid">{cells}</div>'
    body = "".join(_field(f) for f in s.get("fields", []))
    # Nested column-count on secbody is for dense single sections only;
    # page-level .grid already balances sections across two columns.
    grid = ' style="column-count:2;column-gap:14px"' if cols == 2 and not side else ""
    lab = (
        f'<div class="side">{html.escape(s["title"])}</div>' if side else
        f'<div class="sechead">{html.escape(s.get("title", ""))}</div>'
    )
    return f'<div class="sec">{lab}<div class="secbody"{grid}>{body}</div></div>'


def render_form(doc, company=None):
    """doc: {title, subtitle?, sections:[...], legend?, footer?}"""
    company = company or {}
    secs = "".join(_section(s) for s in doc.get("sections", []))
    legend = ""
    if doc.get("legend"):
        items = "".join(
            f'<span class="lg"><span class="lgb" style="background:{c}"></span>'
            f'{html.escape(t)}</span>'
            for c, t in zip((OK, WARN, BAD), doc["legend"]))
        legend = f'<div class="legend">{items}</div>'
    logo = (
        f'<div class="logo">{html.escape(company.get("name", ""))}</div>'
        if company.get("name") else ""
    )
    return f"""<!DOCTYPE html><html lang="no"><head><meta charset="utf-8">
<title>{html.escape(doc.get('title', ''))}</title><style>
@page{{size:letter portrait;margin:11mm}}
*{{box-sizing:border-box;margin:0;padding:0;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
html{{background:#E9E7E0}}
body{{font:8.6pt/1.25 Arial,Helvetica,sans-serif;color:{INK};background:{PAPER};
 width:8.5in;min-height:11in;margin:14px auto;padding:11mm 10mm;
 box-shadow:0 2px 14px rgba(0,0,0,.15)}}
@media print{{html{{background:#fff}} body{{width:auto;margin:0;padding:0;box-shadow:none}}}}
.head{{display:flex;align-items:flex-end;border-bottom:2.5px solid {INK};padding-bottom:6px;margin-bottom:9px}}
.head h1{{font-size:17pt;font-weight:900;letter-spacing:-.02em}}
.head .sub{{font-size:8pt;color:#555;margin-left:auto;text-align:right}}
.logo{{font-weight:900;font-size:12pt;margin-right:12px}}
.grid{{column-count:2;column-gap:16px;column-fill:balance}}
.grid > *{{break-inside:avoid;-webkit-column-break-inside:avoid}}
.hgrid{{column-span:all}}
.sec{{display:flex;gap:6px;margin-bottom:9px;break-inside:avoid}}
.side{{writing-mode:vertical-rl;transform:rotate(180deg);text-align:center;font-weight:700;
 font-size:7.6pt;padding:2px;border:1px solid {LINE};background:#f2f2f2;width:16px;flex:0 0 16px;letter-spacing:.02em}}
.sechead{{font-weight:800;font-size:9pt;border-bottom:1.5px solid {LINE};margin-bottom:4px;width:100%}}
.sec:has(.sechead){{display:block}}
.secbody{{flex:1}}
.row{{display:flex;align-items:center;gap:5px;font-size:7.6pt;margin-bottom:2.6px;break-inside:avoid}}
.cbs{{display:flex;gap:2.5px;flex:0 0 auto}}
.cb{{width:11px;height:11px;border:1.4px solid {LINE};display:inline-block}}
.cb.g{{border-color:{OK}}} .cb.y{{border-color:{WARN}}} .cb.r{{border-color:{BAD}}}
.cb.on{{background:{LINE}}} .cb.g.on{{background:{OK}}} .cb.y.on{{background:{WARN}}} .cb.r.on{{background:{BAD}}}
.lbl{{flex:1}} .req{{color:{BAD};font-weight:700}}
.line{{flex:1;border-bottom:1px solid {LINE};height:11px;min-width:60px}}
.sline{{flex:1;border-bottom:1px solid {LINE};height:20px}}
.row.meas{{align-items:flex-start;flex-wrap:wrap}}
.meas .lbl{{flex:0 0 auto;margin-right:6px}}
.meas .mgrp{{display:inline-flex;gap:6px;flex-wrap:wrap;align-items:flex-end;flex:1 1 auto}}
.mcell{{font-size:7pt}} .mline{{display:inline-block;border-bottom:1px solid {LINE};width:26px;height:9px;margin:0 2px;min-width:26px}}
.unit{{font-size:6.5pt;color:#555}}
.chip{{font-family:'IBM Plex Mono',monospace;font-size:7.4pt;background:#EAF1FD;color:{FACT};
 border-bottom:1.6px solid {FACT};padding:0 3px;border-radius:2px}}
.legend{{display:flex;gap:16px;border-top:1px solid {LINE};margin-top:8px;padding-top:5px;font-size:7.6pt;font-weight:700;column-span:all}}
.lg{{display:flex;align-items:center;gap:4px}} .lgb{{width:12px;height:12px;border:1px solid {LINE}}}
.hgrid{{display:grid;grid-template-columns:1fr 128px 1fr;gap:13px;margin-bottom:9px;
 border-bottom:2px solid {LINE};padding-bottom:9px}}
.hg-col{{min-width:0}}
.redhead{{color:{BAD};font-size:7.4pt;font-weight:700;text-transform:uppercase;
 border-bottom:1px solid {BAD};padding-bottom:1px;margin-bottom:4px}}
.vinwrap{{display:flex;gap:1.5px;flex-wrap:wrap}}
.vinb{{width:13px;height:16px;border:1px solid {LINE};background:#f7f7f7}}
.row.vin{{align-items:flex-start;gap:6px}}
.lbl.b{{font-weight:700;flex:0 0 auto}}
.sqbox{{width:12px;height:12px;border:1px solid {LINE};flex:0 0 auto}}
.row.cr{{justify-content:space-between}}
.terms{{font-size:6.2pt;line-height:1.18;text-align:justify;margin:4px 0 5px}}
.note{{font-size:7pt;color:#333;margin:2px 0 4px}}
.mline2{{border-bottom:1px solid {LINE};height:13px;margin-bottom:2px}}
.cardiag{{width:118px;height:auto;display:block;margin:6px auto}}
.wchart{{display:flex;gap:10px;align-items:flex-start;margin:5px 0 6px}}
.wtri{{flex:0 0 auto}}
.wrow{{display:flex;align-items:center;margin-top:5px}}
.wg{{width:0;height:0;border-top:9px solid transparent;border-bottom:9px solid transparent;border-left:44px solid {OK}}}
.wy{{width:0;height:0;border-top:9px solid transparent;border-bottom:9px solid transparent;border-left:26px solid {WARN}}}
.wr{{width:0;height:0;border-top:9px solid transparent;border-bottom:9px solid transparent;border-left:17px solid {BAD}}}
.wlab{{display:flex;font-size:6.2pt;color:#333}}
.wlab span{{width:44px}} .wlab span:nth-child(2){{width:26px}}
.wcaps{{font-size:6.8pt;font-weight:700;padding-top:4px}}
.wcap{{margin-bottom:22px}}
.itemnum{{font-size:6.4pt;color:#666;margin-right:3px}}
.foot{{text-align:center;font-size:7.4pt;font-weight:700;margin-top:5px;color:#333;column-span:all}}
</style></head><body>
<div class="head">{logo}<h1>{html.escape(doc.get('title', ''))}</h1>
<div class="sub">{html.escape(doc.get('subtitle', ''))}</div></div>
<div class="grid">{secs}</div>
{legend}<div class="foot">{html.escape(doc.get('footer', ''))}</div>
</body></html>"""


def build_form_doc(template: dict, state: dict, artifact: dict | None = None,
                   *, lang: str = "no") -> dict:
    """Bridge Foldok form_fill template + doc state → render_form input."""
    title = (
        (artifact or {}).get("name")
        or template.get("name_no" if lang != "en" else "name")
        or template.get("name")
        or "Skjema"
    )
    badge = template.get("badge") or ""
    subtitle = badge or "Foldok · form_fill"
    if template.get("origin") == "imported":
        subtitle = f"Egen mal · {subtitle}" if badge else "Egen mal · form_fill"

    doc_secs = (state.get("doc") or {}).get("sections") or {}
    sections = []
    for sdef in sorted(template.get("sections") or [],
                       key=lambda x: x.get("position", 99)):
        sk = sdef.get("section_key") or ""
        stitle = sdef.get("title_no") if lang != "en" else sdef.get("title")
        stitle = stitle or sdef.get("title") or sk
        vals = (doc_secs.get(sk) or {}).get("fields") or {}
        fields = []
        for fdef in sdef.get("fields") or []:
            key = fdef.get("key")
            if not key:
                continue
            ftype = fdef.get("type") or "text"
            label = fdef.get("label_no") if lang != "en" else fdef.get("label")
            label = label or fdef.get("label") or key
            slot = vals.get(key) or {}
            row = {
                "key": key,
                "type": ftype,
                "label": label,
                "required": bool(fdef.get("required")),
                "unit": fdef.get("unit") or slot.get("unit"),
                "value": slot.get("value"),
                "source": slot.get("source") or slot.get("source_fact_id"),
            }
            if ftype == "measure":
                row["cells"] = fdef.get("cells") or [""]
            fields.append(row)
        if not fields and sdef.get("boilerplate_no"):
            continue
        sections.append({
            "title": stitle,
            "columns": sdef.get("columns") or 1,
            "side_label": bool(sdef.get("side_label")),
            "kind": sdef.get("kind"),
            "columns_data": sdef.get("columns_data"),
            "fields": fields,
        })

    legend = template.get("legend") or [
        "Kontrollert og OK",
        "Kan kreve tiltak senere",
        "Krever tiltak nå",
    ]
    footer = template.get("footer") or template.get("footer_no") or ""
    return {
        "title": title,
        "subtitle": subtitle,
        "footer": footer,
        "legend": legend,
        "sections": sections,
        "template_key": template.get("template_key"),
    }


def _slug(title: str) -> str:
    s = (title or "section").lower()
    for a, b in (("æ", "ae"), ("ø", "o"), ("å", "a")):
        s = s.replace(a, b)
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s or "section"


def fixture_as_template(fixture: dict | None = None) -> dict:
    """Convert FIXTURE (render doc) → Foldok form_fill template JSON."""
    src = fixture or FIXTURE
    sections = []
    for i, s in enumerate(src.get("sections") or [], 1):
        fields = []
        for f in s.get("fields") or []:
            if not f.get("key"):
                continue
            row = {
                "key": f["key"],
                "type": f.get("type") or "text",
                "label": f.get("label") or f["key"],
                "label_no": f.get("label") or f["key"],
                "required": bool(f.get("required")),
                "severity": "warning" if f.get("required") else "info",
            }
            if f.get("unit"):
                row["unit"] = f["unit"]
            if f.get("cells") is not None:
                row["cells"] = f["cells"]
            if row["type"] == "rating3":
                row["options"] = ["ok", "attention", "immediate"]
            fields.append(row)
        sections.append({
            "section_key": _slug(s.get("title") or f"sec_{i}"),
            "title": s.get("title") or f"Section {i}",
            "title_no": s.get("title") or f"Seksjon {i}",
            "position": i,
            "required": True,
            "gap_severity": "warning",
            "block_type": "form_section",
            "columns": 1,
            "side_label": bool(s.get("side_label")),
            "fields": fields,
        })
    return {
        "template_key": "sample_multipoint",
        "name": src.get("title") or "Multipoint Inspection",
        "name_no": src.get("title") or "Multipoint Inspection",
        "description": "Print-faithful multipoint inspection form_fill (form_engine sample fixture).",
        "document_species": "form_fill",
        "applies_to": ["vehicle", "inspection"],
        "version": 1,
        "language_default": "no",
        "export_price_tier": "basic",
        "origin": "imported",
        "badge": "Egen mal",
        "legend": src.get("legend"),
        "footer": src.get("footer"),
        "subtitle": src.get("subtitle"),
        "sections": sections,
    }


# ── fixture: sample multipoint form AS DATA (what template import produces) ──
R3 = lambda k, l: {"key": k, "type": "rating3", "label": l, "required": False}

FIXTURE = {
    "title": "Multipoint Inspection",
    "subtitle": "Foldok · form_fill · felt-utfyllbar",
    "footer": "Øverst — kundekopi / Nederst — verkstedkopi",
    "legend": ["Kontrollert og OK", "Kan kreve tiltak senere", "Krever tiltak nå"],
    "sections": [
        {"title": "Kunde og kjøretøy", "fields": [
            {"key": "date", "type": "date", "label": "Dato", "required": True},
            {"key": "customer_name", "type": "text", "label": "Kunde", "required": True},
            {"key": "reg_no", "type": "text", "label": "Reg.nr", "required": True,
             "value": "AB 12345", "source": "fact:user-0007"},
            {"key": "model_year", "type": "text", "label": "År/merke/modell",
             "value": "2013 Eksempel SUV", "source": "fact:a12"},
            {"key": "mileage", "type": "measure", "label": "Km-stand", "unit": "km",
             "cells": [""], "required": True},
            {"key": "vin", "type": "text", "label": "VIN", "required": True},
        ]},
        {"title": "Eksteriør", "side_label": True, "fields": [
            R3("horn", "Horn"), R3("lights", "Lys / blinklys / bremselys"),
            R3("wipers", "Vindusviskere og spylere"), R3("windshield", "Frontrute"),
            R3("fuel_cap", "Tanklokk-pakning")]},
        {"title": "Interiør", "side_label": True, "fields": [
            R3("dome_light", "Innvendig lys / instrumentbelysning"),
            R3("cabin_filter", "Kupéfilter"), R3("parking_brake", "Parkeringsbrems"),
            R3("floormat", "Fastmontering av førermatte")]},
        {"title": "Motorrom", "side_label": True, "fields": [
            R3("air_filter", "Luftfilter"), R3("battery_cond", "Batteri (kabler/klemmer/korrosjon)"),
            R3("battery_health", "Batteritilstand"), R3("cooling", "Kjølesystem (lekkasje)"),
            R3("hoses", "Slanger (sprekker/skade/lekkasje)"),
            R3("belts", "Drivremmer (sprekker/skade/slitasje)"),
            R3("radiator", "Radiator / AC-kondensator")]},
        {"title": "Væsker", "side_label": True, "fields": [
            R3("washer_fluid", "Spylervæske"), R3("coolant", "Kjølevæske"),
            R3("power_steering", "Servostyring"), R3("brake_fluid", "Bremsevæske"),
            R3("transmission", "Girkasse / transaksel"), R3("differential", "Differensial")]},
        {"title": "Understell", "side_label": True, "fields": [
            R3("driveshaft", "Drivaksel / kardang (skade/lekkasje/kryss)"),
            R3("cv_boots", "Drivaksel-mansjetter"), R3("hub_bearing", "Navlager (skade/lyd)"),
            R3("steering", "Styring (skade/slitasje)"), R3("suspension", "Fjæring (skade/slitasje)"),
            R3("fluid_leaks", "Væskelekkasjer"), R3("exhaust", "Eksosanlegg (skade/korrosjon)"),
            R3("fuel_lines", "Drivstoffledninger og tank")]},
        {"title": "Dekk", "side_label": True, "fields": [
            {"key": "tire_pressure", "type": "measure", "label": "Dekktrykk justert til",
             "unit": "bar", "cells": ["VF", "HF", "VB", "HB", "Res"]},
            {"key": "tread_depth", "type": "measure", "label": "Mønsterdybde", "unit": "mm",
             "cells": ["VF", "HF", "VB", "HB"], "required": True},
            R3("tire_damage", "Dekkskade / unormal slitasje"),
            R3("rims", "Felger / hjulmuttere"),
            {"key": "torque_spec", "type": "measure", "label": "Tiltrekkingsmoment",
             "unit": "Nm", "cells": [""]}]},
        {"title": "Bremser", "side_label": True, "fields": [
            {"key": "brake_lining", "type": "measure", "label": "Bremsebelegg", "unit": "mm",
             "cells": ["VF", "HF", "VB", "HB"], "required": True},
            R3("brake_lines", "Bremserør / slanger / håndbrekkvaier"),
            R3("discs", "Skiver / trommler / kalipere")]},
        {"title": "Kommentarer og signatur", "fields": [
            {"key": "comments", "type": "text", "label": "Kommentarer"},
            {"key": "comments2", "type": "text", "label": ""},
            {"key": "technician", "type": "text", "label": "Tekniker", "required": True},
            {"key": "signature", "type": "signature", "label": "Signatur"}]},
    ],
}

