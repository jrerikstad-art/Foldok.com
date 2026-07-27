"""Sketch recognition + fill — WORKORDER 0.59.

Geometric facts (shape, position, size, label) → bound block types.
Code-first fill from the index; model only for prose blocks.
"""
from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Optional

SKETCH_TOOLS = (
    "text", "table", "figure", "list", "warning", "signature", "divider", "heading",
)

SECTION_ALIASES: dict[str, list[str]] = {
    "technical_data": [
        "tekniske data", "teknisk data", "tech data", "technical data",
        "spesifikasjoner", "specifications", "parametre", "ratings",
    ],
    "overview": [
        "oversikt", "overview", "beskrivelse", "description", "summary",
        "intro", "innledning", "system overview",
    ],
    "main_components": [
        "komponenter", "components", "hovedkomponenter", "main components",
    ],
    "installation": [
        "installasjon", "installation", "montage", "assembly", "montering",
    ],
    "operation": [
        "drift", "operation", "betjening", "bruk", "use",
    ],
    "maintenance": [
        "vedlikehold", "maintenance", "service",
    ],
    "bom": [
        "bom", "materialliste", "bill of materials", "deler", "parts list",
    ],
    "drawings_register": [
        "tegninger", "drawings", "tegningsliste", "tegningsoversikt",
    ],
    "doc_control": [
        "dokumentkontroll", "doc control", "document control", "revisjon",
    ],
    "revision_history": [
        "revisjonshistorikk", "revision history", "endringer",
    ],
    "warnings": [
        "advarsler", "warnings", "sikkerhet", "safety",
    ],
    "signature": [
        "signatur", "signature", "godkjenning", "approval",
    ],
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def match_section_key(label: str) -> tuple[Optional[str], list[tuple[str, float]]]:
    """Return (best_key|None, top-5 (key, score) suggestions)."""
    lab = _norm(label)
    if not lab:
        return None, []
    scores: list[tuple[str, float]] = []
    for key, aliases in SECTION_ALIASES.items():
        best = 0.0
        for a in aliases + [key.replace("_", " ")]:
            if lab == a:
                best = max(best, 1.0)
            elif lab in a or a in lab:
                best = max(best, 0.85)
            elif lab[:4] and a.startswith(lab[:4]):
                best = max(best, 0.55)
        if best:
            scores.append((key, best))
    scores.sort(key=lambda x: -x[1])
    top = scores[:5]
    best_key = top[0][0] if top and top[0][1] >= 0.55 else None
    return best_key, top


def recognize_geometry(
    *,
    w: float,
    h: float,
    y: float = 0,
    page_h: float = 842,
    tool: Optional[str] = None,
) -> str:
    """Infer block type from aspect ratio & size (C1). Tool hint wins if set."""
    if tool and tool in SKETCH_TOOLS:
        return tool
    if w <= 0 or h <= 0:
        return "text"
    aspect = w / max(h, 1.0)
    area = w * h
    if y > page_h * 0.82 and h < 80:
        return "signature"
    if aspect >= 3.5 and h < 70:
        return "heading"
    if aspect >= 1.6 and h >= 70:
        return "table"
    if 0.7 <= aspect <= 1.4 and min(w, h) >= 120:
        return "figure"
    if aspect < 0.75 and h >= 100:
        return "list"
    if h < 18 and aspect > 5:
        return "divider"
    if area < 8000 and aspect > 2:
        return "heading"
    return "text"


def snap_to_grid(
    x: float, y: float, w: float, h: float,
    *,
    page_w: float = 595.28,
    margin: float = 45.35,
    columns: int = 12,
    gutter: float = 17.0,
) -> dict[str, float]:
    """Snap box to 12-col DesignSystem grid."""
    content_w = page_w - 2 * margin
    col_w = (content_w - (columns - 1) * gutter) / columns if columns > 1 else content_w

    def snap_x(v: float) -> float:
        rel = max(0.0, v - margin)
        col = round(rel / (col_w + gutter))
        col = max(0, min(columns - 1, col))
        return margin + col * (col_w + gutter)

    def snap_span(width: float) -> float:
        n = max(1, round((width + gutter) / (col_w + gutter)))
        n = min(columns, n)
        return n * col_w + (n - 1) * gutter

    sx = snap_x(x)
    sw = snap_span(w)
    if sx + sw > page_w - margin:
        sw = max(col_w, page_w - margin - sx)
    sy = round(y / 7.0) * 7.0
    sh = max(28.0, round(h / 7.0) * 7.0)
    return {"x": sx, "y": sy, "w": sw, "h": sh}


def _prompt_for(t: str) -> str:
    return {
        "table": "Tabell — hva skal stå her?",
        "text": "Tekstblokk — hva skal stå her?",
        "figure": "Figur — hvilken illustrasjon?",
        "list": "Liste — hvilke punkter?",
        "warning": "Advarsel — hvilken fare?",
        "signature": "Signatur — hvem signerer?",
        "divider": "Skille",
        "heading": "Overskrift — tittel?",
    }.get(t, "Blokk — hva skal stå her?")


def new_placeholder(
    *,
    block_type: str,
    x: float,
    y: float,
    w: float,
    h: float,
    label: str = "",
    page: int = 0,
) -> dict:
    """Live document-model block from the moment it is drawn (B5)."""
    geom = snap_to_grid(x, y, w, h)
    tool = block_type if block_type in SKETCH_TOOLS else None
    inferred = recognize_geometry(
        w=geom["w"], h=geom["h"], y=geom["y"], tool=tool,
    )
    bound, suggestions = match_section_key(label) if label else (None, [])
    return {
        "id": f"sk-{abs(hash((round(geom['x'],1), round(geom['y'],1), round(geom['w'],1), label, page))) % 10**10}",
        "type": inferred,
        "label": label or "",
        "bound_section": bound,
        "suggestions": [{"key": k, "score": s} for k, s in suggestions],
        "recognized": bool(bound),
        "x": geom["x"],
        "y": geom["y"],
        "w": geom["w"],
        "h": geom["h"],
        "page": page,
        "filled": False,
        "md": "",
        "prompt": _prompt_for(inferred),
    }


def recognize_placeholder(ph: dict) -> dict:
    """Re-run recognition (C5) — idempotent."""
    out = deepcopy(ph)
    tool = out.get("type") if out.get("type") in SKETCH_TOOLS else None
    out["type"] = recognize_geometry(
        w=float(out.get("w") or 0),
        h=float(out.get("h") or 0),
        y=float(out.get("y") or 0),
        tool=tool,
    )
    bound, suggestions = match_section_key(out.get("label") or "")
    out["bound_section"] = bound
    out["suggestions"] = [{"key": k, "score": s} for k, s in suggestions]
    out["recognized"] = bool(bound)
    out["prompt"] = _prompt_for(out["type"])
    return out


def sort_placeholders(placeholders: list[dict]) -> list[dict]:
    return sorted(
        placeholders or [],
        key=lambda p: (int(p.get("page") or 0), float(p.get("y") or 0), float(p.get("x") or 0)),
    )


def unlabelled_count(placeholders: list[dict]) -> int:
    return sum(1 for p in (placeholders or []) if not (p.get("label") or "").strip())


def export_blocking_placeholders(state: dict) -> list[dict]:
    """D2 — unlabelled placeholders block export."""
    doc = state.get("doc") or {}
    ph = (doc.get("sketch") or {}).get("placeholders") or []
    out = []
    for i, p in enumerate(ph, 1):
        if (p.get("label") or "").strip():
            continue
        out.append({
            "section": "sketch",
            "type": "unlabelled_placeholder",
            "key": p.get("id") or f"placeholder_{i}",
            "label": f"Blokk {i} ({p.get('type') or 'ukjent'}) mangler innhold",
            "severity": "blocking",
        })
    return out


def fill_placeholder_from_index(
    placeholder: dict,
    index: list,
    artifact: Optional[dict] = None,
    *,
    lang: str = "no",
) -> dict:
    """Code-only fill (C3.1) — facts by key → table/list. ZERO tokens."""
    import editorial_layer as ed
    import foldok_compile as fc

    ph = recognize_placeholder(placeholder)
    bound = ph.get("bound_section")
    btype = ph.get("type") or "text"
    artifact = artifact or {}

    all_facts = []
    for e in index or []:
        for f in e.get("facts") or []:
            if f.get("provenance") == "reference":
                continue
            all_facts.append(f)

    key_sets = {
        "technical_data": {
            "weight", "dimensions", "operating_pressure", "torque_values",
            "voltage", "power", "capacity", "material", "swl", "model_no",
            "serial_no", "manufacturer", "temperature", "humidity",
        },
        "main_components": {"component", "part_name", "function"},
        "bom": {"part_no", "quantity", "material", "component"},
        "overview": {"scope_statement", "project_title", "product_name"},
    }
    want = key_sets.get(bound or "", set())
    matched = []
    aliases_map = getattr(fc, "FACT_ALIASES", {}) or {}
    if want:
        for f in all_facts:
            k = f.get("key") or ""
            aliases = set(aliases_map.get(k, []))
            if k in want or aliases & want or any(w in k for w in want):
                matched.append(f)
    if not matched and btype == "table":
        matched = sorted(all_facts, key=lambda f: -float(f.get("confidence") or 0))[:12]

    if btype == "table":
        vocab = "components" if bound == "main_components" else (
            "drawings" if bound == "drawings_register" else "technical_data"
        )
        cols = ed.columns_for(vocab, lang)
        rows = []
        seen = set()
        for f in matched:
            key = f.get("key") or ""
            if key in seen:
                continue
            seen.add(key)
            fid = f.get("id") or ""
            unit = f.get("unit") or "—"
            if vocab == "components":
                cells = {
                    "nr": fc._cell(str(len(rows) + 1), cited=False, plain=True),
                    "component": fc._cell(f.get("value"), cited=True),
                    "function": fc._cell(key.replace("_", " "), cited=False, plain=True),
                    "source": fc._cell(f"{{{{fact:{fid}}}}}" if fid else "—", cited=False, plain=True),
                }
            else:
                cells = {
                    "param": fc._cell(key.replace("_", " "), cited=False, plain=True),
                    "value": fc._cell(f.get("value"), cited=True),
                    "unit": fc._cell(unit, cited=False, plain=True),
                    "source": fc._cell(f"{{{{fact:{fid}}}}}" if fid else "—", cited=False, plain=True),
                }
            rows.append({"row_key": key or fid, "cells": cells})
        if bound == "technical_data":
            for rk in ("weight", "dimensions", "operating_pressure"):
                if rk not in seen:
                    rows.append({
                        "row_key": rk,
                        "cells": {
                            "param": fc._cell(rk.replace("_", " "), cited=False, plain=True),
                            "value": fc._cell(mangler=rk),
                            "unit": fc._cell("—", cited=False, plain=True),
                            "source": fc._cell("—", cited=False, plain=True),
                        },
                    })
        if not rows:
            ph["md"] = (
                "Ingen fakta i indeksen for denne tabellen."
                if lang != "en" else "No facts in index."
            )
        else:
            ph["md"] = fc.render_table_md({"columns": cols, "rows": rows}, lang=lang)
        ph["filled"] = True
        return ph

    if btype == "list":
        lines = []
        for f in matched[:10]:
            fid = f.get("id")
            lines.append(f"- {{{{fact:{fid}}}}}" if fid else f"- **{f.get('value')}**")
        ph["md"] = "\n".join(lines) if lines else "- `[MANGLER: list_item]`"
        ph["filled"] = True
        return ph

    if btype == "heading":
        ph["md"] = f"## {ph.get('label') or 'Overskrift'}"
        ph["filled"] = True
        return ph

    if btype == "divider":
        ph["md"] = "---"
        ph["filled"] = True
        return ph

    if btype == "signature":
        ph["md"] = (
            "| Rolle | Navn | Dato | Signatur |\n|---|---|---|---|\n"
            "| Utarbeidet | `[MANGLER: author_name]` | — | |\n"
            "| Godkjent | `[MANGLER: approved_by]` | — | |\n"
        )
        ph["filled"] = True
        return ph

    if btype == "warning":
        ph["md"] = "> **⚠ ADVARSEL** — `[MANGLER: hazard_description]`\n"
        ph["filled"] = True
        return ph

    if btype == "figure":
        visuals = [
            e for e in (index or [])
            if (e.get("doc_role_hints") or []) or str(e.get("file", "")).lower().endswith(
                (".jpg", ".jpeg", ".png", ".pdf", ".webp")
            )
        ]
        if visuals:
            e = visuals[0]
            cap = e.get("caption") or e.get("file")
            ph["md"] = f"{{{{figure:{e.get('file')}:0|{cap}}}}}\n*{cap}*"
        else:
            ph["md"] = "`[MANGLER: figure]`"
        ph["filled"] = True
        return ph

    if matched:
        bits = [f"{{{{fact:{f.get('id')}}}}}" for f in matched[:6] if f.get("id")]
        ph["md"] = " ".join(bits)
        ph["filled"] = bool(bits)
        ph["needs_prose"] = not bits
    else:
        ph["md"] = ""
        ph["needs_prose"] = True
        ph["filled"] = False
    return ph


def placeholders_to_sections_md(placeholders: list[dict]) -> dict[str, dict]:
    sections: dict[str, dict] = {}
    for i, ph in enumerate(sort_placeholders(placeholders), 1):
        sk = ph.get("bound_section") or f"sketch_block_{i}"
        title = ph.get("label") or ph.get("prompt") or sk
        md = ph.get("md") or ""
        if sk in sections:
            sections[sk]["md"] = (sections[sk].get("md") or "") + "\n\n" + md
        else:
            sections[sk] = {
                "md": md,
                "files": [],
                "sketch_id": ph.get("id"),
                "title_override": title,
            }
    return sections


def sketch_to_owned_template(
    placeholders: list[dict],
    *,
    name: str = "Skisset mal",
    artifact_hint: Optional[dict] = None,
) -> dict:
    """C6 — capture recognised structure as owned template origin=sketched."""
    secs = []
    for i, ph in enumerate(sort_placeholders(placeholders), 1):
        if not (ph.get("label") or "").strip():
            continue
        sk = ph.get("bound_section") or f"custom_{i}"
        btype = ph.get("type") or "text"
        structure = {
            "table": "table", "list": "list", "heading": "prose", "text": "prose",
            "warning": "prose", "figure": "prose", "signature": "table", "divider": "prose",
        }.get(btype, "prose")
        secs.append({
            "section_key": sk,
            "title": ph.get("label"),
            "title_no": ph.get("label"),
            "position": i,
            "required": False,
            "gap_severity": "warning",
            "required_facts": [],
            "required_media": {"min_photos": 1} if btype == "figure" else {},
            "required_content": [],
            "writing_rules": {"structure": structure, "fact_citation": "required"},
            "sketch_type": btype,
        })
    return {
        "template_key": re.sub(r"[^\w]+", "_", (name or "sketched").lower())[:48] or "sketched",
        "name": name,
        "name_no": name,
        "description": "Skisset mal — egen struktur",
        "origin": "sketched",
        "badge": "Egen mal",
        "ai_drafted": False,
        "version": 1,
        "language_default": "no",
        "export_price_tier": "standard",
        "applies_to": [],
        "artifact_hint": {
            "name": (artifact_hint or {}).get("name"),
            "purpose": (artifact_hint or {}).get("purpose"),
        } if artifact_hint else {},
        "sections": secs,
    }
