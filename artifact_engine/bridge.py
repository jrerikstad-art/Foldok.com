"""Bridge page-dict DocumentEngine templates → Document AST."""
from __future__ import annotations

from artifact_engine.model.blocks import (
    FeatureCard,
    FeatureGrid,
    HeroBlock,
    SpecRow,
    SpecificationTable,
    block_from_dict,
)
from artifact_engine.model.document import Document
from artifact_engine.model.section import Section


def document_from_pages(tpl: dict, *, theme: str | None = None) -> Document:
    """
    Convert document_engine page list (cover/overview/specs) into a Document AST.
    """
    pages = tpl.get("pages") or []
    hero = None
    sections: list[Section] = []
    title = tpl.get("title") or tpl.get("name") or "Document"
    doc_type = tpl.get("type") or tpl.get("document_species") or "technical"
    theme_name = theme or tpl.get("theme") or (
        "datasheet" if "data" in str(doc_type).lower() else "engineering"
    )

    for i, page in enumerate(pages):
        ptype = (page.get("type") or "").lower()
        layout = (page.get("layout") or "").lower()
        if ptype == "cover" or layout == "hero_split":
            hero = HeroBlock(
                headline=page.get("title") or title,
                summary=page.get("tagline") or page.get("subtitle") or "",
                image=page.get("hero_image"),
                bullets=list(page.get("bullet_points") or []),
            )
            title = page.get("title") or title
            continue

        blocks = []
        if ptype == "overview" or layout == "component_grid":
            items = [
                FeatureCard(
                    title=c.get("name") or c.get("title") or "",
                    description=c.get("description") or "",
                )
                for c in (page.get("components") or [])
                if isinstance(c, dict)
            ]
            if items:
                blocks.append(FeatureGrid(items=items, columns=2))
        elif ptype == "specifications" or layout == "comparison_table":
            table = page.get("table") or {}
            rows = []
            for r in table.get("rows") or []:
                if isinstance(r, (list, tuple)) and r:
                    prop = str(r[0])
                    rest = [str(x) for x in r[1:]]
                    note = rest[-1] if len(rest) >= 1 else None
                    # If headers end with Comments, last cell is note
                    headers = table.get("headers") or []
                    if headers and str(headers[-1]).lower() in (
                        "comments", "comment", "note", "notes", "merknad",
                    ) and len(rest) >= 1:
                        note = rest[-1]
                        vals = rest[:-1]
                    else:
                        vals = rest
                        note = None
                    rows.append(SpecRow(property=prop, values=vals, note=note))
                elif isinstance(r, dict):
                    rows.append(SpecRow(
                        property=r.get("property") or "",
                        values=[str(v) for v in (r.get("values") or [])],
                        note=r.get("note"),
                    ))
            blocks.append(SpecificationTable(
                headers=list(table.get("headers") or []),
                rows=rows,
                footnotes=list(table.get("footnotes") or []),
            ))
        else:
            if page.get("content"):
                blocks.append(block_from_dict({
                    "type": "paragraph", "text": page.get("content") or "",
                }))
            for sec in page.get("sections") or []:
                if sec.get("title"):
                    blocks.append(block_from_dict({
                        "type": "heading", "text": sec["title"], "level": 3,
                    }))
                if sec.get("content"):
                    blocks.append(block_from_dict({
                        "type": "paragraph", "text": sec["content"],
                    }))

        sections.append(Section(
            title=page.get("title"),
            blocks=blocks,
            page_break_before=(i > 0 and ptype in ("specifications", "content")),
        ))

    return Document(
        title=title,
        document_type=str(doc_type),
        theme=theme_name,
        hero=hero,
        sections=sections,
        metadata={"bridged_from": "document_engine_pages"},
    )
