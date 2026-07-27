"""Form Engine v2 — layout package model (overlay + structure)."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Field:
    """Optional typed field — dict templates remain the wire format."""
    key: str
    label: str
    field_type: str = "text"
    value: Any = None
    required: bool = False
    options: list = field(default_factory=list)
    unit: str | None = None
    placeholder: str = ""
    help_text: str = ""
    visible: bool = True
    condition: dict | None = None
    format_string: str | None = None
    fallback_keys: list = field(default_factory=list)
    page: int = 0
    bbox: dict | None = None
    font: dict | None = None
    style: dict | None = None
    source: str | None = None
    note: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["type"] = d.pop("field_type", "text")
        return d


# Normalized page coordinates: 0..1000 on each axis (independent of px).
def clamp_bbox(b: dict | None) -> dict:
    b = b or {}
    def c(v, default=0):
        try:
            return max(0, min(1000, float(v)))
        except (TypeError, ValueError):
            return default
    return {
        "x": c(b.get("x"), 0),
        "y": c(b.get("y"), 0),
        "w": c(b.get("w"), 100),
        "h": c(b.get("h"), 28),
    }


def normalize_field_region(f: dict) -> dict | None:
    if not isinstance(f, dict):
        return None
    key = (f.get("key") or "").strip()
    if not key:
        return None
    ftype = (f.get("type") or "text").strip().lower()
    if ftype not in (
        "text", "date", "measure", "rating3", "check", "signature", "photo",
        "vin_boxes", "checkbox_right", "note", "terms", "multiline",
    ):
        ftype = "text"
    out = {
        "key": key,
        "type": ftype,
        "label": f.get("label") or f.get("label_no") or key,
        "label_no": f.get("label_no") or f.get("label") or key,
        "page": int(f.get("page") or 0),
        "bbox": clamp_bbox(f.get("bbox")),
        "required": bool(f.get("required")),
        "unit": f.get("unit"),
        "cells": f.get("cells"),
        "options": f.get("options"),
        "verbatim_style": f.get("verbatim_style", True),
        "value": f.get("value"),
        "source": f.get("source"),
    }
    if ftype == "rating3" and not out.get("options"):
        out["options"] = ["ok", "attention", "immediate"]
    return out


def empty_package(**meta) -> dict:
    return {
        "layout_mode": meta.get("layout_mode") or "structure",
        "page_width_in": meta.get("page_width_in") or 8.5,
        "page_height_in": meta.get("page_height_in") or 11.0,
        "title": meta.get("title") or "",
        "subtitle": meta.get("subtitle") or "",
        "footer": meta.get("footer") or "",
        "legend": meta.get("legend"),
        "company": meta.get("company") or {},
        "backgrounds": [],  # [{page, mime, data_b64|path, width_px, height_px}]
        "fields": [],
        "sections": meta.get("sections") or [],  # structure-mode sections
        "source_file": meta.get("source_file"),
        "sha256": meta.get("sha256"),
        "template_key": meta.get("template_key"),
        "document_species": "form_fill",
        "origin": meta.get("origin") or "imported",
        "badge": meta.get("badge") or "Egen mal",
    }


def package_from_structure_doc(doc: dict, company: dict | None = None) -> dict:
    """Wrap a v1 FIXTURE-style doc as a structure-mode package."""
    pkg = empty_package(
        layout_mode="structure",
        title=doc.get("title") or "",
        subtitle=doc.get("subtitle") or "",
        footer=doc.get("footer") or "",
        legend=doc.get("legend"),
        company=company or {},
        sections=deepcopy(doc.get("sections") or []),
    )
    # Flatten fields for fill/bind (no bboxes → structure render)
    flat = []
    for si, s in enumerate(pkg["sections"]):
        for f in s.get("fields") or []:
            nf = normalize_field_region({**f, "page": 0})
            if nf:
                nf["section"] = s.get("title") or s.get("section_key") or f"s{si}"
                # Drop empty bbox meaning for structure mode
                flat.append(nf)
    pkg["fields"] = flat
    return pkg


def validate_package(pkg: dict) -> dict:
    pkg = deepcopy(pkg or {})
    mode = pkg.get("layout_mode") or "structure"
    if mode not in ("overlay", "structure"):
        mode = "structure"
    pkg["layout_mode"] = mode
    pkg["fields"] = [
        nf for f in (pkg.get("fields") or [])
        for nf in [normalize_field_region(f)] if nf
    ]
    pkg.setdefault("backgrounds", [])
    pkg.setdefault("sections", [])
    pkg.setdefault("document_species", "form_fill")
    if mode == "overlay" and not pkg.get("backgrounds"):
        # Cannot overlay without paper — fall back
        pkg["layout_mode"] = "structure"
    return pkg


def to_form_fill_template(pkg: dict) -> dict:
    """Owned Foldok template JSON from a FormPackage (for picker / prefill)."""
    pkg = validate_package(pkg)
    # Prefer section grouping when present
    sections = []
    if pkg.get("sections"):
        for i, s in enumerate(pkg["sections"], 1):
            fields = []
            for f in s.get("fields") or []:
                nf = normalize_field_region(f)
                if not nf:
                    continue
                fields.append({
                    "key": nf["key"], "type": nf["type"],
                    "label": nf["label"], "label_no": nf["label_no"],
                    "required": nf["required"], "unit": nf.get("unit"),
                    "cells": nf.get("cells"), "options": nf.get("options"),
                    "severity": "warning" if nf["required"] else "info",
                    "bbox": nf.get("bbox"), "page": nf.get("page", 0),
                })
            sections.append({
                "section_key": s.get("section_key") or f"sec_{i}",
                "title": s.get("title") or f"Section {i}",
                "title_no": s.get("title_no") or s.get("title") or f"Seksjon {i}",
                "position": s.get("position") or i,
                "block_type": "form_section",
                "columns": s.get("columns") or 1,
                "side_label": bool(s.get("side_label")),
                "fields": fields,
            })
    else:
        # One section per page of fields
        by_page: dict[int, list] = {}
        for f in pkg["fields"]:
            by_page.setdefault(int(f.get("page") or 0), []).append(f)
        for page, fields in sorted(by_page.items()):
            sections.append({
                "section_key": f"page_{page}",
                "title": f"Page {page + 1}",
                "title_no": f"Side {page + 1}",
                "position": page + 1,
                "block_type": "form_section",
                "columns": 1,
                "fields": [{
                    "key": f["key"], "type": f["type"],
                    "label": f["label"], "label_no": f["label_no"],
                    "required": f["required"], "unit": f.get("unit"),
                    "cells": f.get("cells"), "options": f.get("options"),
                    "severity": "warning" if f["required"] else "info",
                    "bbox": f.get("bbox"), "page": f.get("page", 0),
                } for f in fields],
            })
    return {
        "template_key": pkg.get("template_key") or "imported_form",
        "name": pkg.get("title") or "Imported form",
        "name_no": pkg.get("title") or "Importert skjema",
        "description": "Faithful overlay form_fill (Form Engine v2)",
        "document_species": "form_fill",
        "layout_mode": pkg.get("layout_mode"),
        "form_package": {
            "layout_mode": pkg.get("layout_mode"),
            "backgrounds": pkg.get("backgrounds") or [],
            "fields": pkg.get("fields") or [],
            "page_width_in": pkg.get("page_width_in"),
            "page_height_in": pkg.get("page_height_in"),
            "sha256": pkg.get("sha256"),
            "source_file": pkg.get("source_file"),
        },
        "applies_to": ["vehicle", "inspection", "form"],
        "version": 2,
        "language_default": "no",
        "export_price_tier": "basic",
        "origin": pkg.get("origin") or "imported",
        "badge": pkg.get("badge") or "Egen mal",
        "legend": pkg.get("legend"),
        "footer": pkg.get("footer"),
        "subtitle": pkg.get("subtitle"),
        "sections": sections,
    }


def apply_values_to_package(pkg: dict, values: dict[str, Any]) -> dict:
    """Stamp field values onto package fields (and nested section fields)."""
    pkg = deepcopy(validate_package(pkg))
    for f in pkg["fields"]:
        slot = values.get(f["key"])
        if isinstance(slot, dict):
            if "value" in slot:
                f["value"] = slot["value"]
            if slot.get("source"):
                f["source"] = slot["source"]
            if slot.get("unit"):
                f["unit"] = slot["unit"]
        elif slot is not None:
            f["value"] = slot
    for s in pkg.get("sections") or []:
        for f in s.get("fields") or []:
            key = f.get("key")
            if not key:
                continue
            slot = values.get(key)
            if isinstance(slot, dict):
                if "value" in slot:
                    f["value"] = slot["value"]
                if slot.get("source"):
                    f["source"] = slot["source"]
            elif slot is not None:
                f["value"] = slot
    return pkg
