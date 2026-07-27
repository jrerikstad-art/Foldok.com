"""Form Engine v2 — faithful overlay + structure fallback.

Public API (import form_engine):
  render_form, export_form_html, build_form_doc, fixture_as_template, FIXTURE
  ingest_bytes, extract_layout, package_from_upload, bind_and_render
"""
from __future__ import annotations

from pathlib import Path

from .render_structure import (  # noqa: F401
    FIXTURE,
    build_form_doc,
    fixture_as_template,
    render_form,
)
from . import ingest as ingest_mod
from . import layout_extract
from . import fill as fill_mod
from .model import (
    Field,
    apply_values_to_package,
    package_from_structure_doc,
    to_form_fill_template,
    validate_package,
)
from .pdf_layout import extract_form_layout, fields_from_pdf_layout  # noqa: F401
from .render_overlay import render_overlay
from .engine import FormEngine


ingest_bytes = ingest_mod.ingest_bytes
ingest_path = ingest_mod.ingest_path
extract_layout = layout_extract.extract_layout


def package_from_upload(raw: bytes, name: str, *, ask_fn=None, force: bool = False,
                        cache_dir=None) -> dict:
    """Ingest bytes → FormPackage (overlay when page rasters available).

    cache_dir: project-local ``.foldok_cache``; never engine ``.foldok_ref_cache``.
    """
    ing = ingest_mod.ingest_bytes(raw, name)
    return layout_extract.extract_layout(
        ing, ask_fn=ask_fn, force=force, cache_dir=cache_dir)


def export_form_html(template: dict, state: dict, *, artifact=None,
                     company=None, lang: str = "no",
                     index: list | None = None) -> str:
    """
    Print-faithful HTML. Uses overlay when template carries form_package
    backgrounds; otherwise structure (v1 letter sheet).
    """
    company = company or {}
    fp = (template or {}).get("form_package") or {}
    mode = (
        (template or {}).get("layout_mode")
        or fp.get("layout_mode")
        or "structure"
    )
    backgrounds = fp.get("backgrounds") or []
    if mode == "overlay" and backgrounds:
        pkg = validate_package({
            **fp,
            "layout_mode": "overlay",
            "title": (
                (artifact or {}).get("name")
                or template.get("name_no" if lang != "en" else "name")
                or template.get("name")
                or "Skjema"
            ),
            "footer": template.get("footer") or template.get("footer_no") or fp.get("footer"),
            "legend": template.get("legend") or fp.get("legend"),
            "sections": template.get("sections") or fp.get("sections") or [],
            "fields": fp.get("fields") or [],
            "company": company,
            "template_key": template.get("template_key"),
            "origin": template.get("origin") or "imported",
        })
        # Prefer flat fields from package; rebuild from sections+bboxes if needed
        if not pkg["fields"]:
            flat = []
            for s in template.get("sections") or []:
                for f in s.get("fields") or []:
                    if f.get("bbox"):
                        flat.append({**f, "page": f.get("page", 0)})
            pkg["fields"] = flat
        pkg = fill_mod.bind_package(
            pkg, state or {}, template,
            artifact=artifact, index=index, enable_smart_defaults=True,
        )
        return render_overlay(pkg, company=company)

    doc = build_form_doc(template, state or {}, artifact, lang=lang)
    return render_form(doc, company=company)


def bind_and_render(pkg: dict, state: dict, template: dict | None = None,
                    *, artifact=None, company=None, index=None) -> str:
    """Fill a FormPackage and render (overlay or structure)."""
    pkg = fill_mod.bind_package(
        pkg, state or {}, template or {},
        artifact=artifact, index=index,
    )
    company = company or pkg.get("company") or {}
    pkg = validate_package(pkg)
    if pkg.get("layout_mode") == "overlay" and pkg.get("backgrounds"):
        return render_overlay(pkg, company=company)
    # Structure: rebuild FIXTURE-like doc from package sections
    doc = {
        "title": pkg.get("title") or "Skjema",
        "subtitle": pkg.get("subtitle") or "",
        "footer": pkg.get("footer") or "",
        "legend": pkg.get("legend"),
        "sections": pkg.get("sections") or [],
    }
    # Stamp values onto section fields
    by_key = {f["key"]: f for f in pkg.get("fields") or []}
    for s in doc["sections"]:
        for f in s.get("fields") or []:
            src = by_key.get(f.get("key") or "")
            if src:
                if src.get("value") is not None:
                    f["value"] = src["value"]
                if src.get("source"):
                    f["source"] = src["source"]
    return render_form(doc, company=company)


def template_from_package(pkg: dict) -> dict:
    return to_form_fill_template(pkg)


__all__ = [
    "FormEngine", "Field",
    "FIXTURE", "render_form", "build_form_doc", "export_form_html",
    "fixture_as_template", "ingest_bytes", "ingest_path", "extract_layout",
    "extract_form_layout", "fields_from_pdf_layout",
    "package_from_upload", "bind_and_render", "template_from_package",
    "package_from_structure_doc", "apply_values_to_package", "validate_package",
]
