"""OO facade — FormEngine v3/v4 over overlay, structure, and ArtifactEngine.

    eng = FormEngine(theme="engineering")
    eng.load_template(tpl)
    eng.set_artifact_model(artifact)
    eng.set_project_facts(facts)
    eng.set_mode("overlay")             # overlay | structure | hybrid | artifact
    html = eng.render("html")

    # Artifact compose path (Document AST → shared layout/PDF):
    doc = eng.to_document()
    html = eng.render_html()
    eng.render_pdf("out.pdf")

Print HTML never stamps [MANGLER] — empty slots stay blank (gap ledger).
Ratings / checks / signatures are never auto-filled.
"""
from __future__ import annotations

import base64
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from artifact_engine.composition import CompositionEngine
from artifact_engine.core import get_engine
from artifact_engine.model.blocks import (
    FormField,
    FormSection,
    RatingLegend,
    SignatureBlock,
)
from artifact_engine.model.document import Document
from artifact_engine.model.section import Section

from . import fill as fill_mod
from . import ingest as ingest_mod
from . import layout_extract
from .model import (
    clamp_bbox,
    to_form_fill_template,
    validate_package,
)
from .render_overlay import render_overlay
from .render_structure import FIXTURE, build_form_doc, render_form

NO_AUTO = frozenset({"rating3", "check", "checkbox", "signature"})
MODES = ("overlay", "structure", "hybrid", "artifact")


def _deep_get(data: dict | None, key: str, default=None):
    if not data or not key:
        return default
    cur: Any = data
    for k in key.split("."):
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def _field_type(f: dict) -> str:
    return (f.get("type") or f.get("field_type") or "text").lower()


def _fact_lookup(facts: dict | list, key: str):
    if isinstance(facts, dict) and key in facts:
        slot = facts[key]
        if isinstance(slot, dict) and "value" in slot:
            return slot.get("value"), slot.get("source") or f"fact:{key}"
        return slot, f"fact:{key}"
    if isinstance(facts, list):
        for row in facts:
            if isinstance(row, dict) and row.get("key") == key and row.get("value") not in (None, ""):
                return row.get("value"), row.get("source") or f"fact:{key}"
    return None, None


class FormEngine:
    def __init__(
        self,
        missing_marker: str = "[MANGLER]",
        theme: str = "engineering",
    ):
        self.template: dict | None = None
        self.package: dict | None = None
        self.artifact_model: dict = {}
        self.project_facts: dict | list = {}
        self.company: dict = {}
        self.lang: str = "no"
        self.state: dict = {}
        self.missing_marker = missing_marker
        self.render_mode = "hybrid"  # overlay if backgrounds else structure
        self._extract: dict | None = None
        self.theme_name = theme or "engineering"
        self.artifact = get_engine(self.theme_name)
        self.composer = CompositionEngine()

    # ── Loading ──────────────────────────────────────────────────────
    def load_template(self, template_data: dict) -> "FormEngine":
        if not isinstance(template_data, dict):
            raise TypeError("template_data must be a dict")
        self.template = deepcopy(template_data)
        fp = self.template.get("form_package")
        if fp:
            self.package = validate_package({
                **fp,
                "title": (
                    self.template.get("name_no")
                    or self.template.get("name")
                    or fp.get("title")
                    or "Skjema"
                ),
                "sections": self.template.get("sections") or fp.get("sections") or [],
                "legend": self.template.get("legend"),
                "footer": self.template.get("footer") or self.template.get("footer_no"),
            })
            if self.package.get("backgrounds"):
                self.render_mode = "overlay"
        else:
            self.package = None
            self.render_mode = "structure"
        return self

    def load_fixture(self) -> "FormEngine":
        from .render_structure import fixture_as_template
        return self.load_template(fixture_as_template(FIXTURE))

    def load_upload(self, raw: bytes, name: str, *, ask_fn=None, cache_dir=None) -> "FormEngine":
        ing = ingest_mod.ingest_bytes(raw, name)
        pkg = layout_extract.extract_layout(ing, ask_fn=ask_fn, cache_dir=cache_dir)
        self.package = pkg
        self.template = to_form_fill_template(pkg)
        self._extract = ing.get("pdf_native")
        self.render_mode = "overlay" if pkg.get("backgrounds") else "structure"
        return self

    def set_artifact_model(self, artifact: dict | None) -> "FormEngine":
        self.artifact_model = artifact or {}
        return self

    def set_project_facts(self, facts: dict | list | None) -> "FormEngine":
        self.project_facts = facts or {}
        return self

    def set_company(self, company: dict | None) -> "FormEngine":
        self.company = company or {}
        return self

    def set_state(self, state: dict | None) -> "FormEngine":
        self.state = state or {}
        return self

    def set_theme(self, theme: str) -> "FormEngine":
        self.theme_name = theme or "engineering"
        self.artifact = get_engine(self.theme_name)
        return self

    def set_mode(self, mode: str) -> "FormEngine":
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        self.render_mode = mode
        return self

    def set_backgrounds(self, images: list, page_sizes: list | None = None) -> "FormEngine":
        """
        Set original page images for overlay.
        Each item: file path, data-URL, raw bytes, or {mime, data_b64|path}.
        """
        backgrounds = []
        for i, img in enumerate(images or []):
            bg = self._coerce_background(img, page=i)
            if bg:
                if page_sizes and i < len(page_sizes):
                    sz = page_sizes[i] or {}
                    bg["width_px"] = sz.get("width") or sz.get("width_px")
                    bg["height_px"] = sz.get("height") or sz.get("height_px")
                backgrounds.append(bg)
        if not self.package:
            self.package = validate_package({
                "layout_mode": "overlay" if backgrounds else "structure",
                "title": (self.template or {}).get("name") or "Skjema",
                "sections": (self.template or {}).get("sections") or [],
                "fields": [],
            })
        self.package["backgrounds"] = backgrounds
        self.package["layout_mode"] = "overlay" if backgrounds else "structure"
        if backgrounds:
            self.render_mode = "overlay"
            if self.template is not None:
                self.template.setdefault("form_package", {})
                self.template["form_package"]["backgrounds"] = backgrounds
                self.template["form_package"]["layout_mode"] = "overlay"
                self.template["layout_mode"] = "overlay"
        return self

    def set_layout_from_extract(self, extract_result: dict) -> "FormEngine":
        """Match extract spans/widgets onto template fields by label/key."""
        if not self.template:
            raise ValueError("Load a template first")
        self._extract = extract_result
        raw = list(extract_result.get("raw_fields") or [])
        widgets = list(extract_result.get("widgets") or [])

        def match_bbox(label: str, key: str) -> tuple[dict | None, int]:
            needle = (label or key or "").lower().strip()
            if not needle:
                return None, 0
            for block in raw:
                text = (block.get("text") or "").lower()
                if needle in text or text.rstrip(":") in needle:
                    bb = block.get("bbox")
                    if bb and ("x" in bb):
                        return bb, int(block.get("page") or 0)
            for w in widgets:
                name = (w.get("name") or "").lower()
                if needle in name or key.lower() == name:
                    return w.get("bbox"), int(w.get("page") or 0)
            return None, 0

        for f in self._all_fields(self.template):
            label = f.get("label") or f.get("label_no") or f.get("key") or ""
            key = f.get("key") or ""
            bb, page = match_bbox(label, key)
            if not bb:
                continue
            if max(float(bb.get("x") or 0), float(bb.get("y") or 0),
                   float(bb.get("w") or 0)) > 1000:
                pw = ((extract_result.get("page_info") or [{}])[0].get("width") or 612)
                ph = ((extract_result.get("page_info") or [{}])[0].get("height") or 792)
                bb = {
                    "x": 1000.0 * float(bb.get("x") or 0) / pw,
                    "y": 1000.0 * float(bb.get("y") or 0) / ph,
                    "w": 1000.0 * float(bb.get("w") or 0) / pw,
                    "h": 1000.0 * float(bb.get("h") or 0) / ph,
                }
            f["bbox"] = clamp_bbox(bb)
            f["page"] = page if page >= 0 else 0
            if page >= 1 and not any(
                int(b.get("page") or 0) == 0 for b in raw[:3]
            ):
                f["page"] = max(0, page - 1)

        if self.package is not None:
            by_key = {f.get("key"): f for f in self._all_fields(self.template) if f.get("key")}
            for pf in self.package.get("fields") or []:
                src = by_key.get(pf.get("key"))
                if src and src.get("bbox"):
                    pf["bbox"] = src["bbox"]
                    pf["page"] = src.get("page", 0)
            self.package = validate_package(self.package)
            self.template["form_package"] = {
                **(self.template.get("form_package") or {}),
                "fields": self.package.get("fields") or [],
                "backgrounds": self.package.get("backgrounds") or [],
                "layout_mode": self.package.get("layout_mode"),
            }
        return self

    # ── resolve / fill ───────────────────────────────────────────────
    def _coerce_background(self, img, *, page: int) -> dict | None:
        if isinstance(img, dict) and img.get("data_b64"):
            return {
                "page": page,
                "mime": img.get("mime") or "image/jpeg",
                "data_b64": img["data_b64"],
                "width_px": img.get("width_px"),
                "height_px": img.get("height_px"),
            }
        if isinstance(img, (bytes, bytearray)):
            return {
                "page": page, "mime": "image/jpeg",
                "data_b64": base64.b64encode(bytes(img)).decode("ascii"),
            }
        if isinstance(img, str):
            if img.startswith("data:") and ";base64," in img:
                header, b64 = img.split(";base64,", 1)
                mime = header.replace("data:", "") or "image/jpeg"
                return {"page": page, "mime": mime, "data_b64": b64}
            path = Path(img)
            if path.is_file():
                raw = path.read_bytes()
                ext = path.suffix.lower()
                mime = {
                    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                    ".webp": "image/webp",
                }.get(ext, "image/jpeg")
                return {
                    "page": page, "mime": mime,
                    "data_b64": base64.b64encode(raw).decode("ascii"),
                }
        return None

    def _all_fields(self, data: dict | None) -> list[dict]:
        data = data or {}
        out = list(data.get("fields") or [])
        for s in data.get("sections") or []:
            out.extend(s.get("fields") or [])
        return out

    def _is_visible(self, f: dict) -> bool:
        cond = f.get("condition")
        if not cond:
            return True
        target = self._resolve_value(cond.get("field") or "", {})
        if "equals" in cond:
            return target == cond.get("equals")
        if "truthy" in cond:
            return bool(target) == bool(cond.get("truthy"))
        return True

    def _resolve_value(self, key: str, field: dict) -> Any:
        if not key:
            return None
        val = _deep_get(self.artifact_model, key)
        if val is not None and val != "":
            return val, "artifact"
        got, src = _fact_lookup(self.project_facts, key)
        if got not in (None, ""):
            return got, src
        for fb in field.get("fallback_keys") or []:
            got = self._resolve_value(fb, {})
            if isinstance(got, tuple):
                if got[0] not in (None, ""):
                    return got
            elif got not in (None, ""):
                return got, f"fallback:{fb}"
        if field.get("value") not in (None, ""):
            return field.get("value"), field.get("source")
        return None, None

    def _apply_format(self, fmt: str, value: Any) -> str:
        ctx = {**(self.artifact_model or {}), "value": value}
        if isinstance(self.project_facts, dict):
            for k, v in self.project_facts.items():
                ctx[k] = v.get("value") if isinstance(v, dict) and "value" in v else v
        try:
            return fmt.format(**ctx)
        except Exception:
            return str(value)

    def _facts_as_index(self) -> list:
        facts = self.project_facts
        if isinstance(facts, list):
            return facts
        if not isinstance(facts, dict):
            return []
        out = []
        for k, v in facts.items():
            if isinstance(v, dict) and "value" in v:
                out.append({"key": k, **v})
            else:
                out.append({"key": k, "value": v, "source": f"fact:{k}"})
        return out

    def _state_from_facts(self) -> dict:
        state = deepcopy(self.state or {})
        if state.get("doc") or not self.template:
            if not self.template:
                return state
        sections = deepcopy((state.get("doc") or {}).get("sections") or {})
        for sdef in self.template.get("sections") or []:
            sk = sdef.get("section_key")
            if not sk:
                continue
            fields = sections.setdefault(sk, {"fields": {}}).setdefault("fields", {})
            for fdef in sdef.get("fields") or []:
                key = fdef.get("key")
                if not key or not self._is_visible(fdef):
                    continue
                if key in fields and fields[key].get("value") not in (None, ""):
                    continue
                ftype = _field_type(fdef)
                if ftype in NO_AUTO:
                    continue
                value, source = self._resolve_value(key, fdef)
                if value in (None, ""):
                    continue
                if fdef.get("format_string"):
                    value = self._apply_format(fdef["format_string"], value)
                fields[key] = {
                    "value": value,
                    "source": source or "resolved",
                    "unit": fdef.get("unit"),
                }
        state["doc"] = {"sections": sections}
        if self.artifact_model:
            state["artifact"] = self.artifact_model
        return state

    def fill(self) -> dict:
        if not self.template and not self.package:
            return {}
        state = self._state_from_facts()
        index = self._facts_as_index()
        if self.package:
            pkg = fill_mod.bind_package(
                self.package, state, self.template or {},
                artifact=self.artifact_model, index=index,
                enable_smart_defaults=True,
            )
            by_tpl = {f.get("key"): f for f in self._all_fields(self.template) if f.get("key")}
            for f in pkg.get("fields") or []:
                tdef = by_tpl.get(f.get("key")) or f
                if not self._is_visible(tdef):
                    f["visible"] = False
                    continue
                if f.get("value") in (None, "") and _field_type(tdef) not in NO_AUTO:
                    value, source = self._resolve_value(f["key"], tdef)
                    if value not in (None, ""):
                        if tdef.get("format_string"):
                            value = self._apply_format(tdef["format_string"], value)
                        f["value"] = value
                        f["source"] = source
            self.package = pkg
            return pkg
        return build_form_doc(
            self.template, state, self.artifact_model, lang=self.lang)

    def resolve_mode(self) -> str:
        mode = self.render_mode or "hybrid"
        if mode == "artifact":
            return "artifact"
        has_bg = bool(self.package and self.package.get("backgrounds"))
        if mode == "hybrid":
            return "overlay" if has_bg else "structure"
        if mode == "overlay" and not has_bg:
            return "structure"
        return mode

    # ── Artifact compose (Document AST → ArtifactEngine) ─────────────
    def _has_rating3(self) -> bool:
        for f in self._all_fields(self.template):
            if _field_type(f) == "rating3":
                return True
        return False

    def _ast_value(self, key: str, field: dict) -> tuple[Any, str | None]:
        """Resolve value for Document AST. Ratings/checks/signatures never auto-filled."""
        ftype = _field_type(field)
        if ftype in NO_AUTO:
            if field.get("value") not in (None, ""):
                return field.get("value"), field.get("source")
            return None, None
        value, source = self._resolve_value(key, field)
        if isinstance(value, tuple):
            value, source = value[0], value[1] if len(value) > 1 else source
        if value in (None, "", self.missing_marker):
            return None, None
        if field.get("format_string"):
            value = self._apply_format(field["format_string"], value)
        return value, source

    def _build_form_section(self, raw: dict) -> FormSection:
        fields: list[FormField] = []
        for f in raw.get("fields") or []:
            key = f.get("key")
            if not key or not self._is_visible(f):
                continue
            ftype = _field_type(f)
            if ftype == "check":
                ftype = "checkbox"
            value, source = self._ast_value(key, f)
            fields.append(FormField(
                key=key,
                label=f.get("label") or f.get("label_no") or key,
                field_type=ftype,
                value=value,
                unit=f.get("unit"),
                required=bool(f.get("required")),
                options=list(f.get("options") or []),
                source=source,
                note=f.get("note") or "",
            ))
        cols = int(raw.get("columns") or 1)
        if cols not in (1, 2):
            cols = 1
        return FormSection(
            title=raw.get("title") or raw.get("label") or "",
            fields=fields,
            columns=cols,
        )

    def build_document(self) -> Document:
        if not self.template:
            raise ValueError("No template loaded")
        title = (
            self.template.get("title")
            or self.template.get("name_no")
            or self.template.get("name")
            or "Inspection Form"
        )
        sections: list[Section] = []
        if self._has_rating3():
            sections.append(Section(title=None, blocks=[RatingLegend()]))

        for raw_section in self.template.get("sections") or []:
            form_section = self._build_form_section(raw_section)
            sections.append(Section(
                title=raw_section.get("title") or raw_section.get("label"),
                blocks=[form_section],
            ))

        tech_name, _ = _fact_lookup(self.project_facts, "technician_name")
        if tech_name in (None, ""):
            tech_name = _deep_get(self.artifact_model, "technician_name")
        insp_date, _ = _fact_lookup(self.project_facts, "inspection_date")
        if insp_date in (None, ""):
            insp_date = _deep_get(self.artifact_model, "inspection_date")

        sections.append(Section(
            title="Sign-off",
            blocks=[
                SignatureBlock(
                    label="Technician",
                    name=str(tech_name) if tech_name not in (None, "") else None,
                    date=str(insp_date) if insp_date not in (None, "") else None,
                )
            ],
        ))

        doc = Document(
            title=str(title),
            document_type="form",
            theme=self.theme_name,
            sections=sections,
            metadata={
                "species": "form_fill",
                "template_key": (
                    self.template.get("key")
                    or self.template.get("template_key")
                    or self.template.get("name")
                ),
            },
        )
        return self.composer.compose(doc)

    def to_document(self) -> Document:
        return self.build_document()

    def render_html(self, *, paginate: bool = True) -> str:
        doc = self.build_document()
        return self.artifact.render_document_html(doc, paginate=paginate)

    def render_pdf(self, path: str, *, paginate: bool = True) -> str:
        doc = self.build_document()
        return str(self.artifact.render_document_pdf(doc, path, paginate=paginate))

    def render(self, output_format: str = "html", mode: str | None = None) -> str:
        if not self.template and not self.package:
            return "<p>No template loaded.</p>"
        if mode:
            self.set_mode(mode)

        use = self.resolve_mode()
        if use == "artifact":
            if output_format == "json":
                from dataclasses import asdict
                return json.dumps(asdict(self.build_document()), indent=2, ensure_ascii=False)
            if output_format == "markdown":
                return self._to_markdown(self.fill(), show_missing=True)
            html = self.render_html()
            return html.replace(self.missing_marker, "")

        filled = self.fill()
        company = self.company

        if output_format == "json":
            return json.dumps(filled, indent=2, ensure_ascii=False)
        if output_format == "markdown":
            return self._to_markdown(filled, show_missing=True)

        if use == "overlay" and self.package and self.package.get("backgrounds"):
            return render_overlay(self.package, company=company)

        if self.template:
            from . import export_form_html
            return export_form_html(
                self.template, self._state_from_facts(),
                artifact=self.artifact_model,
                company=company,
                lang=self.lang,
                index=self._facts_as_index(),
            )
        if isinstance(filled, dict) and filled.get("sections"):
            return render_form(filled, company=company)
        return render_form(FIXTURE, company=company)

    def to_dict(self) -> dict:
        return {
            "template": self.template,
            "render_mode": self.render_mode,
            "resolved_mode": self.resolve_mode(),
            "theme": self.theme_name,
            "package": {
                "layout_mode": (self.package or {}).get("layout_mode"),
                "fields": len((self.package or {}).get("fields") or []),
                "backgrounds": len((self.package or {}).get("backgrounds") or []),
            } if self.package else None,
        }

    def _to_markdown(self, data: dict, *, show_missing: bool = False) -> str:
        title = data.get("title") or (self.template or {}).get("name") or "Form"
        marker = self.missing_marker if show_missing else "_empty_"
        lines = [f"# {title}", ""]
        fields = data.get("fields") or []
        sections = data.get("sections") or []
        if not fields and sections:
            for s in sections:
                lines.append(f"## {s.get('title') or ''}")
                for f in s.get("fields") or []:
                    if f.get("visible") is False:
                        continue
                    val = f.get("value")
                    shown = marker if val in (None, "") else str(val)
                    lines.append(f"- **{f.get('label') or f.get('key')}:** {shown}")
                lines.append("")
        else:
            for f in fields:
                if f.get("visible") is False:
                    continue
                val = f.get("value")
                shown = marker if val in (None, "") else str(val)
                lines.append(f"- **{f.get('label') or f.get('key')}:** {shown}")
        return "\n".join(lines)
