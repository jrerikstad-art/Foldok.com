"""DocumentEngine — multi-page datasheets / manuals / product sheets.

Fills page templates from artifact + facts. Does not invent values.
Print HTML leaves unresolved placeholders blank; markdown may show
missing_marker. Narrative Foldok drafts still use assemble_draft → .md;
this engine is the print HTML path for page-structured templates.
"""
from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from .fixtures import DATASHEET_FIXTURE, DEMO_FACTS
from .render_html import render_document_html
from .resolve import deep_get, resolve_placeholder


class DocumentEngine:
    def __init__(
        self,
        missing_marker: str | None = None,
        theme: str = "engineering",
    ):
        """
        missing_marker: used only for markdown / json gap display.
        Print HTML always uses blank for unresolved placeholders.
        theme: ArtifactEngine theme for the shared compose→layout→HTML path.
        """
        self.template: dict | None = None
        self.artifact_model: dict = {}
        self.project_facts: dict | list = {}
        self.missing_marker = missing_marker  # None = blank in md too unless set
        self.theme_name = theme or "engineering"
        self.brand: dict = {
            "name": "Foldok",
            "primary_color": "#16181D",
            "secondary_color": "#5A6472",
            "logo": None,
            "font": "Arial, Helvetica, sans-serif",
        }
        # Lazy: set after template type known; default engineering
        self._artifact = None

    @property
    def artifact(self):
        if self._artifact is None or self._artifact.theme_name != self.theme_name:
            from artifact_engine.core import get_engine
            self._artifact = get_engine(self.theme_name)
        return self._artifact

    def set_theme(self, theme: str) -> "DocumentEngine":
        self.theme_name = theme or "engineering"
        self._artifact = None
        return self

    def load_template(self, template: dict) -> "DocumentEngine":
        if not isinstance(template, dict):
            raise TypeError("template must be a dict")
        self.template = deepcopy(template)
        if isinstance(template.get("brand"), dict):
            self.brand.update(template["brand"])
        return self

    def load_fixture(self, name: str = "datasheet") -> "DocumentEngine":
        _ = name
        return self.load_template(DATASHEET_FIXTURE)

    def set_artifact_model(self, artifact: dict | None) -> "DocumentEngine":
        self.artifact_model = artifact or {}
        return self

    def set_project_facts(self, facts: dict | list | None) -> "DocumentEngine":
        self.project_facts = facts or {}
        return self

    def set_brand(self, brand: dict | None) -> "DocumentEngine":
        if brand:
            self.brand.update(brand)
        return self

    def load_from_foldok_sections(
        self,
        template: dict,
        *,
        state: dict | None = None,
        title: str | None = None,
    ) -> "DocumentEngine":
        """
        Bridge Foldok section templates → simple page list.
        Uses section titles + draft markdown bodies when present in state.doc.
        """
        state = state or {}
        doc = (state.get("doc") or {}).get("sections") or {}
        pages = []
        for sdef in sorted(template.get("sections") or [],
                           key=lambda x: x.get("position", 99)):
            sk = sdef.get("section_key") or ""
            stitle = sdef.get("title_no") or sdef.get("title") or sk
            body = (doc.get(sk) or {}).get("content") or (doc.get(sk) or {}).get("md") or ""
            if not body and (doc.get(sk) or {}).get("fields"):
                # form-ish section — list field values
                lines = []
                for k, slot in ((doc.get(sk) or {}).get("fields") or {}).items():
                    if isinstance(slot, dict) and slot.get("value") not in (None, ""):
                        lines.append(f"{k}: {slot['value']}")
                body = "\n".join(lines)
            pages.append({
                "type": "content",
                "title": stitle,
                "content": body or "",
                "sections": [],
            })
        self.load_template({
            "name": template.get("name_no") or template.get("name") or "Document",
            "title": title or template.get("name_no") or template.get("name") or "Document",
            "type": "manual",
            "document_species": template.get("document_species") or "technical_doc",
            "pages": pages,
            "brand": self.brand,
        })
        return self

    def build(self) -> dict:
        if not self.template:
            return {}
        doc = deepcopy(self.template)
        doc["brand"] = deepcopy(self.brand)
        doc["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        # Title on doc may be placeholder
        if isinstance(doc.get("title"), str):
            doc["title"] = self._resolve(doc["title"], print_safe=True)
        for page in doc.get("pages") or []:
            self._resolve_page(page, print_safe=True)
        return doc

    def _resolve(self, text: str, *, print_safe: bool) -> str:
        missing = None if print_safe else self.missing_marker
        return resolve_placeholder(
            text,
            artifact=self.artifact_model,
            facts=self.project_facts,
            missing=missing,
        )

    def _resolve_page(self, page: dict, *, print_safe: bool):
        for key in ("title", "tagline", "subtitle", "date", "content"):
            if key in page and isinstance(page[key], str):
                page[key] = self._resolve(page[key], print_safe=print_safe)
        if "bullet_points" in page:
            page["bullet_points"] = [
                self._resolve(bp, print_safe=print_safe) if isinstance(bp, str) else bp
                for bp in page["bullet_points"]
            ]
        for comp in page.get("components") or []:
            for k in ("name", "description"):
                if k in comp and isinstance(comp[k], str):
                    comp[k] = self._resolve(comp[k], print_safe=print_safe)
        if "table" in page and isinstance(page["table"], dict):
            self._resolve_table(page["table"], print_safe=print_safe)
        for section in page.get("sections") or []:
            self._resolve_section(section, print_safe=print_safe)

    def _resolve_section(self, section: dict, *, print_safe: bool):
        for key in ("title", "content"):
            if key in section and isinstance(section[key], str):
                section[key] = self._resolve(section[key], print_safe=print_safe)
        if "table" in section:
            self._resolve_table(section["table"], print_safe=print_safe)
        for item in section.get("items") or []:
            if isinstance(item, dict):
                for k, v in list(item.items()):
                    if isinstance(v, str):
                        item[k] = self._resolve(v, print_safe=print_safe)

    def _resolve_table(self, table: dict, *, print_safe: bool):
        if "rows" not in table:
            return
        table["rows"] = [
            [
                self._resolve(cell, print_safe=print_safe) if isinstance(cell, str) else cell
                for cell in row
            ]
            for row in table["rows"]
        ]
        if "footnotes" in table:
            table["footnotes"] = [
                self._resolve(n, print_safe=print_safe) if isinstance(n, str) else n
                for n in table["footnotes"]
            ]

    def render(self, output_format: str = "html") -> str:
        if not self.template:
            return "<p>No document template loaded.</p>"
        if output_format == "html":
            # Full pipeline: Document AST → Composition → Layout → HTML
            try:
                from artifact_engine import document_from_pages
                built = self.build()
                dtype = (built.get("type") or "").lower()
                theme = (
                    "datasheet" if dtype in ("datasheet", "product_sheet", "product")
                    else self.theme_name
                )
                if theme != self.theme_name:
                    self.set_theme(theme)
                ast = document_from_pages(built, theme=theme)
                if ast.hero or any(s.blocks for s in ast.sections):
                    return self.artifact.render_document_html(
                        ast, compose=True, paginate=True,
                    )
            except Exception:
                pass
            return render_document_html(self.build())
        if output_format == "markdown":
            return self._to_markdown(self.build_for_markdown())
        if output_format == "json":
            return json.dumps(self.build(), indent=2, ensure_ascii=False, default=str)
        return render_document_html(self.build())

    def build_for_markdown(self) -> dict:
        """Same as build but may stamp missing_marker into unresolved slots."""
        if not self.template:
            return {}
        doc = deepcopy(self.template)
        doc["brand"] = deepcopy(self.brand)
        print_safe = self.missing_marker is None
        if isinstance(doc.get("title"), str):
            doc["title"] = self._resolve(doc["title"], print_safe=print_safe)
        for page in doc.get("pages") or []:
            self._resolve_page(page, print_safe=print_safe)
        return doc

    def _to_markdown(self, doc: dict) -> str:
        lines = [f"# {doc.get('title') or 'Document'}", ""]
        for page in doc.get("pages") or []:
            lines.append(f"## {page.get('title') or ''}")
            lines.append("")
            if page.get("tagline"):
                lines.append(f"*{page['tagline']}*")
                lines.append("")
            for b in page.get("bullet_points") or []:
                lines.append(f"- {b}")
            if page.get("bullet_points"):
                lines.append("")
            for c in page.get("components") or []:
                lines.append(f"### {c.get('name') or ''}")
                lines.append(c.get("description") or "")
                lines.append("")
            table = page.get("table")
            if table:
                headers = table.get("headers") or []
                if headers:
                    lines.append("| " + " | ".join(str(h) for h in headers) + " |")
                    lines.append("| " + " | ".join("---" for _ in headers) + " |")
                    for row in table.get("rows") or []:
                        lines.append("| " + " | ".join(str(c) for c in row) + " |")
                    lines.append("")
            if page.get("content"):
                lines.append(str(page["content"]))
                lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "template": (self.template or {}).get("name"),
            "brand": self.brand.get("name"),
            "pages": len((self.template or {}).get("pages") or []),
        }


def render_datasheet_demo() -> str:
    """Self-test helper — fixture + demo facts → HTML."""
    return (
        DocumentEngine()
        .load_fixture()
        .set_project_facts(DEMO_FACTS)
        .set_brand({"name": "DemoTek"})
        .render("html")
    )
