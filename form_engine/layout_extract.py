"""Extract field regions from page images / text — fidelity to original layout.

Native PDF path: see pdf_layout.extract_form_layout (PyMuPDF spans + widgets).
Re-exported here so `from form_engine.layout_extract import extract_form_layout`
matches the intended module name.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .model import empty_package, normalize_field_region, validate_package
from .pdf_layout import (  # noqa: F401 — public surface for this module
    extract_form_layout,
    fields_from_pdf_layout,
    package_from_pdf_layout,
)


LAYOUT_SYSTEM = """You extract a FILLABLE FORM layout for faithful overlay rendering.
Return JSON ONLY:
{
  "title": "...",
  "footer": "...",
  "legend": ["OK","Attention","Immediate"] or null,
  "fields": [
    {"key":"snake_case","type":"text|date|measure|rating3|check|signature",
     "label":"verbatim label from the form",
     "page":0,
     "bbox":{"x":0-1000,"y":0-1000,"w":0-1000,"h":0-1000},
     "required":false,"unit":null}
  ]
}
Rules:
- Preserve the paper: bboxes must match where blanks/checkboxes actually sit.
- Coordinates are normalized 0–1000 relative to each page image.
- rating3 = three adjacent rating boxes (ok/attention/immediate).
- Do NOT invent sections that are not on the page.
- Prefer few accurate fields over many wrong ones.
- Map obvious keys: vin, mileage, reg_no, customer_name, date, make, model.
"""

# Engine-root .foldok_ref_cache is ship-contaminated — never write formlayout there.
_ENGINE_ROOT = Path(__file__).resolve().parent.parent
_FORBIDDEN_CACHE_ROOTS = (
    _ENGINE_ROOT / ".foldok_ref_cache",
    _ENGINE_ROOT / ".feltdok_ref_cache",
    _ENGINE_ROOT / "releases",
)


def resolve_formlayout_cache(sha: str, cache_dir: str | Path | None = None) -> Path | None:
    """Project-local formlayout path only. Returns None → no disk cache.

    Never writes under the engine tree's .foldok_ref_cache (ships in zips).
    Prefer ``<project>/.foldok_cache/formlayout-{sha}.json``.
    """
    if not cache_dir:
        return None
    root = Path(cache_dir)
    try:
        resolved = root.resolve()
    except Exception:
        resolved = root
    for bad in _FORBIDDEN_CACHE_ROOTS:
        try:
            if resolved == bad.resolve() or bad.resolve() in resolved.parents:
                return None
        except Exception:
            continue
    root.mkdir(parents=True, exist_ok=True)
    return root / f"formlayout-{sha}.json"


def _cache_path(sha: str, cache_dir: str | Path | None = None) -> Path | None:
    """Back-compat wrapper — project-local only (no engine-global default)."""
    return resolve_formlayout_cache(sha, cache_dir)


def offline_layout_from_text(text: str, name: str = "",
                             backgrounds: list | None = None) -> dict:
    """Zero-token heuristic when vision unavailable — structure mode mostly."""
    sections = _simple_sections(text, name)
    pkg = empty_package(
        layout_mode="overlay" if backgrounds else "structure",
        title=Path(name).stem.replace("_", " ") or "Skjema",
        source_file=name,
        sections=sections,
        backgrounds=backgrounds or [],
    )
    if backgrounds:
        pkg["fields"] = _grid_fields_from_sections(sections)
        pkg["layout_mode"] = "overlay"
    return validate_package(pkg)


def _simple_sections(text: str, name: str) -> list:
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    fields = []
    for ln in lines[:40]:
        if ":" in ln or "___" in ln or "☐" in ln:
            lab = re.split(r"[:_☐]", ln)[0].strip()[:40]
            if not lab:
                continue
            key = re.sub(r"[^a-z0-9]+", "_", lab.lower()).strip("_")[:32] or "field"
            ftype = "rating3" if "☐" in ln or "ok" in ln.lower() else "text"
            fields.append({"key": key, "type": ftype, "label": lab, "required": False})
    if not fields:
        fields = [
            {"key": "customer_name", "type": "text", "label": "Kunde", "required": True},
            {"key": "date", "type": "date", "label": "Dato", "required": True},
        ]
    return [{"title": Path(name).stem or "Skjema", "fields": fields, "side_label": False}]


def _grid_fields_from_sections(sections: list) -> list:
    out = []
    y = 80
    for s in sections:
        for f in s.get("fields") or []:
            nf = normalize_field_region({
                **f, "page": 0,
                "bbox": {"x": 80, "y": y, "w": 420, "h": 32},
            })
            if nf:
                out.append(nf)
            y += 40
            if y > 920:
                y = 80
    return out


def extract_layout(ingest: dict, *, ask_fn=None, force: bool = False,
                   cache_dir: str | Path | None = None) -> dict:
    """
    ingest: return value of ingest_bytes/ingest_path.
    ask_fn(purpose, model, messages, max_tokens=...) → str|dict
    cache_dir: project-local ``.foldok_cache`` (or equivalent). Never the
    engine-global ``.foldok_ref_cache``. Omit to skip disk cache.
    """
    sha = ingest.get("sha256") or "none"
    cache_dir = cache_dir or ingest.get("cache_dir")
    cache = _cache_path(sha, cache_dir)
    if cache is not None and cache.exists() and not force:
        try:
            return validate_package(json.loads(cache.read_text(encoding="utf-8")))
        except Exception:
            pass

    def _persist(pkg: dict) -> dict:
        if cache is not None:
            try:
                cache.write_text(json.dumps(pkg, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass
        return pkg

    backgrounds = ingest.get("backgrounds") or []
    text = ingest.get("text_peek") or ""
    name = ingest.get("name") or "form"
    pdf_native = ingest.get("pdf_native")

    # 1) Native PDF text/widget layout (zero tokens, high fidelity when digital PDF)
    if pdf_native and not pdf_native.get("error"):
        try:
            pkg = package_from_pdf_layout(
                pdf_native, name=name, backgrounds=backgrounds, sha256=sha)
            if pkg and len(pkg.get("fields") or []) >= 2:
                return _persist(pkg)
        except Exception:
            pass

    # 2) Vision layout extract when API available
    if ask_fn and backgrounds:
        # Vision on first page (and second if present)
        content = []
        for bg in backgrounds[:2]:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": bg.get("mime") or "image/jpeg",
                    "data": bg["data_b64"],
                },
            })
        content.append({
            "type": "text",
            "text": (
                f"Form file: {name}\n"
                f"Extract layout for overlay. Text peek (may be empty):\n{text[:3000]}"
            ),
        })
        try:
            raw = ask_fn(
                "form_layout_extract", None,
                [{"role": "user", "content": content}],
                max_tokens=4000,
            )
            if isinstance(raw, dict):
                data = raw
            else:
                data = json.loads(raw) if isinstance(raw, str) else {}
            fields = [
                nf for f in (data.get("fields") or [])
                for nf in [normalize_field_region(f)] if nf
            ]
            pkg = empty_package(
                layout_mode="overlay",
                title=data.get("title") or Path(name).stem,
                footer=data.get("footer") or "",
                legend=data.get("legend"),
                backgrounds=backgrounds,
                source_file=name,
                sha256=sha,
            )
            pkg["fields"] = fields
            # Also build crude sections for form_fill template
            pkg["sections"] = [{
                "title": pkg["title"],
                "fields": [
                    {k: f[k] for k in (
                        "key", "type", "label", "required", "unit", "cells", "options")
                     if k in f}
                    for f in fields
                ],
            }]
            pkg = validate_package(pkg)
            return _persist(pkg)
        except Exception:
            pass

    pkg = offline_layout_from_text(text, name, backgrounds=backgrounds)
    pkg["sha256"] = sha
    pkg["source_file"] = name
    return _persist(pkg)
