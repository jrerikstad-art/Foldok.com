"""Native PDF layout extract (PyMuPDF) — text spans + AcroForm widgets.

Coordinates from fitz are page points; we normalize to 0–1000 for FormPackage.
Does not invent fields: only labeled blanks, widgets, and clear form cues.
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any

from .model import normalize_field_region

# Label → likely fillable type
DATE_RE = re.compile(r"\b(dato|date)\b", re.I)
SIGN_RE = re.compile(r"\b(signatur|signature|underskrift)\b", re.I)
MEASURE_RE = re.compile(
    r"\b(km|mileage|bar|mm|nm|trykk|dybde|belegg|mønster)\b", re.I)
RATING_RE = re.compile(
    r"\b(ok|attention|immediate|kontrollert|rating)\b|☐|☑|\[\s*\]", re.I)
CHECK_RE = re.compile(r"☐|☑|\[\s*\]|checkbox", re.I)
BLANK_RE = re.compile(r"_{3,}|…{2,}|\.{4,}")
LABELISH_RE = re.compile(r"[:：]\s*$|:\s*$")

KEY_ALIASES = {
    "regnr": "reg_no", "reg_nr": "reg_no", "registreringsnummer": "reg_no",
    "kjennemerke": "reg_no", "vin": "vin", "chassisnummer": "vin",
    "km": "mileage", "kilometerstand": "mileage", "odometer": "mileage",
    "kunde": "customer_name", "customer": "customer_name", "kundenavn": "customer_name",
    "dato": "date", "date": "date", "tekniker": "technician",
    "signatur": "signature", "signature": "signature",
}


def _slug_key(label: str) -> str:
    k = re.sub(r"[^a-z0-9]+", "_", (label or "").lower()).strip("_")[:48] or "field"
    return KEY_ALIASES.get(k, k)


def _norm_bbox(x0, y0, x1, y1, page_w: float, page_h: float) -> dict:
    pw = page_w or 1.0
    ph = page_h or 1.0
    return {
        "x": round(1000.0 * float(x0) / pw, 2),
        "y": round(1000.0 * float(y0) / ph, 2),
        "w": round(1000.0 * max(0.0, float(x1) - float(x0)) / pw, 2),
        "h": round(1000.0 * max(0.0, float(y1) - float(y0)) / ph, 2),
    }


def extract_form_layout(pdf_path: str | Path | None = None, *,
                        raw: bytes | None = None,
                        max_pages: int = 6) -> dict[str, Any]:
    """
    Extract text spans + AcroForm widgets from a PDF.
    Returns structure ready to promote into FormEngine fields.
    """
    try:
        import fitz
    except ImportError:
        return {"pages": 0, "page_info": [], "raw_fields": [], "widgets": [],
                "source": str(pdf_path or ""), "error": "pymupdf_missing"}

    tmp: Path | None = None
    path = Path(pdf_path) if pdf_path else None
    if raw is not None:
        fd, name = tempfile.mkstemp(suffix=".pdf")
        import os
        os.close(fd)
        tmp = Path(name)
        tmp.write_bytes(raw)
        path = tmp
    if not path or not path.exists():
        return {"pages": 0, "page_info": [], "raw_fields": [], "widgets": [],
                "source": "", "error": "no_pdf"}

    doc = fitz.open(path)
    pages_data = []
    all_spans = []
    all_widgets = []

    try:
        for page_num, page in enumerate(doc):
            if page_num >= max_pages:
                break
            pw, ph = page.rect.width, page.rect.height
            page_dict = {
                "page": page_num,  # 0-based — matches FormPackage
                "page_display": page_num + 1,
                "width": pw,
                "height": ph,
                "blocks": [],
                "widgets": [],
            }
            blocks = page.get_text("dict").get("blocks") or []
            for block in blocks:
                if block.get("type") != 0:
                    continue
                for line in block.get("lines") or []:
                    for span in line.get("spans") or []:
                        text = (span.get("text") or "").strip()
                        if not text:
                            continue
                        bbox = span.get("bbox") or (0, 0, 0, 0)
                        field = {
                            "page": page_num,
                            "text": text,
                            "bbox_pt": {
                                "x": round(bbox[0], 1),
                                "y": round(bbox[1], 1),
                                "w": round(bbox[2] - bbox[0], 1),
                                "h": round(bbox[3] - bbox[1], 1),
                            },
                            "bbox": _norm_bbox(bbox[0], bbox[1], bbox[2], bbox[3], pw, ph),
                            "font": span.get("font", "Arial"),
                            "size": round(float(span.get("size") or 10), 1),
                            "color": span.get("color", 0),
                        }
                        page_dict["blocks"].append(field)
                        all_spans.append(field)

            try:
                for w in (page.widgets() or []):
                    r = w.rect
                    wtype = (w.field_type_string or w.field_type or "text")
                    name = (w.field_name or "").strip() or f"widget_{page_num}_{len(all_widgets)}"
                    widget = {
                        "page": page_num,
                        "name": name,
                        "type_hint": str(wtype).lower(),
                        "bbox_pt": {
                            "x": round(r.x0, 1), "y": round(r.y0, 1),
                            "w": round(r.x1 - r.x0, 1), "h": round(r.y1 - r.y0, 1),
                        },
                        "bbox": _norm_bbox(r.x0, r.y0, r.x1, r.y1, pw, ph),
                    }
                    page_dict["widgets"].append(widget)
                    all_widgets.append(widget)
            except Exception:
                pass

            pages_data.append(page_dict)
    finally:
        doc.close()
        if tmp:
            tmp.unlink(missing_ok=True)

    return {
        "pages": len(pages_data),
        "page_info": pages_data,
        "raw_fields": all_spans,
        "widgets": all_widgets,
        "source": str(pdf_path or "bytes"),
    }


def _infer_type(label: str) -> str:
    if SIGN_RE.search(label):
        return "signature"
    if DATE_RE.search(label):
        return "date"
    if MEASURE_RE.search(label):
        return "measure"
    if RATING_RE.search(label) or CHECK_RE.search(label):
        return "rating3" if RATING_RE.search(label) else "check"
    return "text"


def _widget_type(hint: str) -> str:
    h = (hint or "").lower()
    if "check" in h:
        return "check"
    if "sign" in h:
        return "signature"
    if "button" in h:
        return "check"
    return "text"


def fields_from_pdf_layout(layout: dict) -> list[dict]:
    """
    Promote PDF spans/widgets → FormPackage field regions (0–1000).
    Value box is placed to the right of a label when the label ends with ':'
    or sits next to underscores; widgets map 1:1.
    """
    fields: list[dict] = []
    seen: set[str] = set()

    for w in layout.get("widgets") or []:
        key = _slug_key(w.get("name") or "field")
        base = key
        n = 2
        while key in seen:
            key = f"{base}_{n}"
            n += 1
        seen.add(key)
        nf = normalize_field_region({
            "key": key,
            "type": _widget_type(w.get("type_hint") or ""),
            "label": w.get("name") or key,
            "page": int(w.get("page") or 0),
            "bbox": w.get("bbox"),
            "required": False,
        })
        if nf:
            fields.append(nf)

    # Text labels that look like form prompts
    for span in layout.get("raw_fields") or []:
        text = (span.get("text") or "").strip()
        if len(text) < 2 or len(text) > 80:
            continue
        is_label = bool(LABELISH_RE.search(text) or BLANK_RE.search(text)
                        or text.endswith(":") or "___" in text)
        # Short title-case / known keys without colon still count
        low = text.lower().rstrip(":").strip()
        known = _slug_key(low) in KEY_ALIASES.values() or low in KEY_ALIASES
        if not is_label and not known:
            continue
        label = re.split(r"[:_]+", text)[0].strip() or text
        if BLANK_RE.fullmatch(text.strip("_.")):
            continue
        key = _slug_key(label)
        if key in seen:
            continue
        seen.add(key)

        bb = span.get("bbox") or {}
        # Fill slot: to the right of the label, same height
        x = float(bb.get("x") or 0) + float(bb.get("w") or 0) + 8
        if x > 850:
            x = float(bb.get("x") or 80)
            y = float(bb.get("y") or 0) + float(bb.get("h") or 20) + 4
        else:
            y = float(bb.get("y") or 0)
        w = min(420.0, 980.0 - x)
        h = max(float(bb.get("h") or 22), 22.0)
        ftype = _infer_type(label)
        nf = normalize_field_region({
            "key": key,
            "type": ftype,
            "label": label.rstrip(":"),
            "page": int(span.get("page") or 0),
            "bbox": {"x": x, "y": y, "w": w, "h": h},
            "required": key in ("customer_name", "date", "reg_no", "vin", "technician"),
        })
        if nf:
            fields.append(nf)

    return fields


def package_from_pdf_layout(layout: dict, *, name: str = "",
                            backgrounds: list | None = None,
                            sha256: str | None = None) -> dict | None:
    """Build a FormPackage when native extract yields usable fields."""
    from .model import empty_package, validate_package

    fields = fields_from_pdf_layout(layout)
    if len(fields) < 2 and not (layout.get("widgets") or []):
        return None

    title = Path(name or layout.get("source") or "Skjema").stem.replace("_", " ")
    # Prefer first large-ish span as title candidate
    for span in (layout.get("raw_fields") or [])[:8]:
        t = (span.get("text") or "").strip()
        if 8 <= len(t) <= 60 and not LABELISH_RE.search(t):
            title = t
            break

    pkg = empty_package(
        layout_mode="overlay" if backgrounds else "structure",
        title=title,
        source_file=name or layout.get("source"),
        sha256=sha256,
        backgrounds=backgrounds or [],
    )
    pkg["fields"] = fields
    pkg["sections"] = [{
        "section_key": "page_0",
        "title": title,
        "title_no": title,
        "position": 1,
        "fields": [
            {k: f[k] for k in (
                "key", "type", "label", "label_no", "required", "unit",
                "cells", "options", "bbox", "page") if k in f}
            for f in fields
        ],
    }]
    pkg.setdefault("meta", {})["extract"] = "pdf_native"
    pkg["meta"]["span_count"] = len(layout.get("raw_fields") or [])
    pkg["meta"]["widget_count"] = len(layout.get("widgets") or [])
    return validate_package(pkg)
