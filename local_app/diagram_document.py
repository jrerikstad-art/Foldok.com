"""Bridge foldok_diagram sessions → workbench documents.

Confirmed diagrams are saved under project/diagrams/ and inserted into a
document section as a DiagramBlock-style markdown + SVG payload.
Does not invent IEC clause text or claim conformity.
"""
from __future__ import annotations

from typing import Any

# Registry document type → workbench template + preferred section for diagrams
DOC_TARGETS: dict[str, dict[str, str]] = {
    "installation_guide": {
        "template": "installation_manual.json",
        "section": "system_overview",
        "label": "Installation guide",
    },
    "technical_file": {
        "template": "technical_doc_package.json",
        "section": "description",
        "label": "Technical file",
    },
    "samsvarserklaring": {
        "template": "samsvarserklaering.json",
        "section": "work_description",
        "label": "Samsvarserklæring",
    },
    "inspection_package": {
        "template": "inspection_checklist.json",
        "section": "scope",
        "label": "Inspection package",
    },
    "inspection_report": {
        "template": "inspection_checklist.json",
        "section": "scope",
        "label": "Inspection report",
    },
}


def resolve_target(document_type: str | None, section_key: str | None = None) -> dict[str, str]:
    key = (document_type or "installation_guide").strip().lower().replace("-", "_")
    aliases = {
        "installation_manual": "installation_guide",
        "installasjonsveiledning": "installation_guide",
        "samsvar": "samsvarserklaring",
        "samsvarserklaering": "samsvarserklaring",
        "technical_documentation": "technical_file",
        "teknisk_fil": "technical_file",
    }
    key = aliases.get(key, key)
    target = dict(DOC_TARGETS.get(key) or DOC_TARGETS["installation_guide"])
    if section_key:
        target["section"] = section_key
    target["document_type"] = key if key in DOC_TARGETS else "installation_guide"
    return target


def diagram_markdown(
    *,
    title: str,
    graph_id: str,
    profile: str,
    jurisdiction: str,
    svg: str,
    revision: str = "A",
    citation: str = "",
    lang: str = "en",
) -> str:
    """Workbench markdown embedding the SVG with provenance citation."""
    heading = "System diagram" if lang == "en" else "Systemdiagram"
    lines = [
        f"### {heading}: {title}",
        "",
        f"- Graph: `{graph_id}`",
        f"- Profile: `{profile}`",
        f"- Revision: `{revision}`",
    ]
    if jurisdiction:
        lines.append(f"- Jurisdiction: `{jurisdiction}`")
    if citation:
        lines.append(f"- Source: `{citation}`")
    lines.append("")
    lines.append(
        "> Unconfirmed diagram content until the responsible person reviews export. "
        "Foldok does not claim standard conformity from this figure alone."
        if lang == "en"
        else
        "> Ubekreftet diagraminnhold til ansvarlig person har gjennomgått eksport. "
        "Foldok hevder ikke standard-samsvar ut fra figuren alene."
    )
    lines.append("")
    # Inline SVG — export pipeline already handles raw SVG in section bodies
    lines.append(svg.strip())
    lines.append("")
    return "\n".join(lines)


def insert_into_section(
    state: dict,
    *,
    section_key: str,
    md: str,
    svg: str,
    graph: dict,
    paths: dict[str, str] | None = None,
    profile: str = "wiring",
    replace: bool = True,
) -> dict[str, Any]:
    """Write diagram payload into state.doc.sections[section_key]."""
    if not state.get("doc"):
        state["doc"] = {"sections": {}}
    sections = state["doc"].setdefault("sections", {})
    sec = sections.setdefault(section_key, {"md": "", "files": []})
    if replace or not (sec.get("md") or "").strip():
        sec["md"] = md
    else:
        sec["md"] = ((sec.get("md") or "").rstrip() + "\n\n" + md).strip() + "\n"
    sec["block_type"] = "DiagramBlock"
    sec["svg"] = svg
    sec["foldok_diagram"] = {
        "graph_id": (graph or {}).get("id"),
        "profile": profile,
        "jurisdiction": (graph or {}).get("jurisdiction") or "",
        "paths": paths or {},
        "component_count": len((graph or {}).get("components") or []),
        "connection_count": len((graph or {}).get("connections") or []),
    }
    from doc_state import iso_now, add_version

    sec["updated"] = iso_now()
    add_version(
        state,
        "user",
        "diagram",
        f"Inserted foldok_diagram into {section_key}",
    )
    return sec
