"""Composition Engine — decide page regions before layout.

The LLM (or FormEngine) supplies semantic content. This engine decides
professional arrangement. Deterministic: same Document → same output.

For document_type user_manual / brukermanual:
  - enforce USER_MANUAL_PROFILE section order
  - force professional block types (Procedure, EngineeringTable, …)
  - strip [MANGLER: …] from prose into a final gaps section
"""
from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Optional

from artifact_engine.model.blocks import (
    BillOfMaterials,
    BulletList,
    CalloutBox,
    DiagramBlock,
    DrawingReference,
    EngineeringTable,
    FeatureGrid,
    FormSection,
    HeadingBlock,
    HeroBlock,
    NoteBox,
    ParagraphBlock,
    ParameterGrid,
    Procedure,
    ProcedureStep,
    ProcessFlow,
    RatingLegend,
    RevisionEntry,
    RevisionHistory,
    SignatureBlock,
    SpecificationTable,
    TableOfContentsBlock,
    TechnicalData,
    TocEntry,
    WarningBox,
)
from artifact_engine.model.document import Document
from artifact_engine.model.section import Section

_MANGLER_RE = re.compile(
    r"\[MANGLER:\s*([^\]]+?)\s*(?:—|–|-)?\s*(?:oppgi)?\]"
    r"|\[MANGLER\]",
    re.IGNORECASE,
)


@dataclass
class PageRegion:
    """Semantic region on a page / in reading order."""
    type: str  # hero | overview | diagram | specs | form | signoff | body
    blocks: list = field(default_factory=list)
    columns: int = 1
    span: float = 1.0
    title: Optional[str] = None


# Preferred section order for datasheets / product sheets / technical packages
# WORKORDER 0.49 B3 — editorial rhythm; template position is tiebreak only
_PRIORITY: list[tuple[str, list[str]]] = [
    ("identification", ["cover", "title", "identif", "nameplate", "doc_control"]),
    ("overview", ["overview", "system", "intro", "summary", "scope", "description"]),
    ("technical_data", ["spec", "technical", "data", "parameter", "rating"]),
    ("diagram", ["diagram", "flow", "schematic", "process", "wiring"]),
    ("procedure", ["install", "assembl", "operat", "commission", "procedure", "use"]),
    ("maintenance", ["maintenance", "vedlikehold", "service", "spare", "troubleshoot"]),
    ("storage", ["storage", "transport", "disposal", "lagring"]),
    ("declarations", ["declaration", "compliance", "legal", "warranty", "certificate"]),
    ("registers", ["bom", "drawing", "tegning", "register", "appendix", "revision"]),
    ("features", ["feature", "component", "capability"]),
    ("form", ["inspection", "checklist", "form"]),
]

# Mandatory section order for professional user manuals
USER_MANUAL_PROFILE: list[tuple[str, list[str]]] = [
    ("cover", ["cover", "title page", "front page", "title"]),
    ("legal", ["legal", "copyright", "thank", "standards", "disclaimer", "warranty"]),
    ("symbols", ["symbol", "legend", "safety sign"]),
    ("summary", ["summary", "overview", "intro"]),
    ("glossary", ["glossary", "abbreviation", "definition"]),
    ("toc", ["table of contents", "contents", "innhold", "toc"]),
    ("product_description", [
        "product description", "main components", "1 product",
    ]),
    ("technical_specs", [
        "technical specification", "technical specs", "specification",
        "tech data", "technical data", "2.1",
    ]),
    ("interface", [
        "interface", "compatibility", "other product", "pinout", "i/o",
    ]),
    ("assembly", ["assembly", "assemble", "montage", "assembl"]),
    ("installation", ["installation", "install", "commission", "setup"]),
    ("operation", [
        "operation", "operat", "using", "betjening", "start", "stop",
    ]),
    ("maintenance", ["maintenance", "vedlikehold", "service", "spare"]),
    ("troubleshooting", ["troubleshoot", "fault", "feilsøking", "feilsoking"]),
    ("transport", ["transport", "storage", "lagring", "lifting", "packing"]),
    ("identification", [
        "identification", "producer", "product id", "nameplate", "marking",
    ]),
    ("revision_history", ["revision", "revisjon", "history", "changelog"]),
]

# Public aliases (LLM / docs / tests)
MANUAL_PROFILE = USER_MANUAL_PROFILE
MANUAL_PROFILE_ORDER: list[str] = [name for name, _ in USER_MANUAL_PROFILE]
_MANUAL_PRIORITY = USER_MANUAL_PROFILE

# Flexible industrial / decision-support report (matrices, stakeholders)
INDUSTRIAL_REPORT_PROFILE: list[tuple[str, list[str]]] = [
    ("cover", ["cover", "title page", "front page", "title"]),
    ("executive_summary", ["executive", "summary", "sammendrag", "abstract"]),
    ("identification", ["identification", "project id", "system id", "identifikasjon"]),
    ("revision_history", ["revision", "revisjon", "history", "changelog"]),
    ("problem_and_context", ["problem", "context", "background", "bakgrunn", "challenge"]),
    ("stakeholders", ["stakeholder", "interessent", "user need", "persona"]),
    ("current_situation", ["current", "today", "as-is", "nåsituasjon", "status"]),
    ("evaluation_or_impact", [
        "evaluation", "impact", "risk", "matrix", "priority", "frequency",
    ]),
    ("proposed_approach", ["proposed", "approach", "solution", "løsning", "design"]),
    ("comparison", ["comparison", "compare", "today vs", "versus", "gap"]),
    ("recommendations", ["recommend", "anbefaling", "next action"]),
    ("next_steps", ["next step", "roadmap", "plan", "action"]),
    ("technical_details", ["technical", "detail", "appendix tech", "spesifikasjon"]),
    ("appendices", ["appendix", "vedlegg", "attachment"]),
    ("location_map", ["location", "map", "site", "kart"]),
    ("photo_evidence", ["photo", "evidence", "bilde", "figur"]),
]
INDUSTRIAL_REPORT_PROFILE_ORDER: list[str] = [
    name for name, _ in INDUSTRIAL_REPORT_PROFILE
]

# Shells we may create when missing (force-block fills content)
_AUTO_SHELLS = frozenset({"symbols", "toc", "revision_history"})


def _title_l(section: Section) -> str:
    return (section.title or "").lower()


def _section_has(section: Section, *klasses) -> bool:
    return any(isinstance(b, klasses) for b in (section.blocks or []))


def _is_manual(doc: Document) -> bool:
    dtype = (doc.document_type or "").lower().replace("-", "_").replace(" ", "_")
    return dtype in (
        "user_manual", "installation_manual", "manual",
        "operating_manual", "service_manual", "brukermanual",
    )


def _is_industrial_report(doc: Document) -> bool:
    dtype = (doc.document_type or "").lower().replace("-", "_").replace(" ", "_")
    return dtype in (
        "industrial_report", "decision_report", "technical_evaluation",
        "compliance_package", "monitoring_report",
    )


def _match_manual_procedure(title: str) -> str:
    if any(k in title for k in ("assembl", "montage", "mount")):
        return "assembly"
    if any(k in title for k in ("install", "commission", "setup")):
        return "installation"
    if any(k in title for k in ("troubleshoot", "fault", "feils")):
        return "troubleshooting"
    if any(k in title for k in ("maintenance", "vedlikehold", "service", "spare")):
        return "maintenance"
    if any(k in title for k in ("operat", "betjening", "using", "start", "stop")):
        return "operation"
    if any(k in title for k in ("transport", "storage", "lagring", "lifting")):
        return "transport"
    return "assembly"


def _match_priority(section: Section, *, manual: bool = False) -> str:
    title = _title_l(section)
    priority = USER_MANUAL_PROFILE if manual else _PRIORITY

    if _section_has(section, TableOfContentsBlock):
        return "toc"
    if manual and _section_has(section, RevisionHistory):
        return "revision_history"

    if manual:
        for name, keywords in priority:
            if any(k in title for k in keywords):
                return name

    if _section_has(section, DiagramBlock, ProcessFlow):
        return "diagram"
    if _section_has(section, SpecificationTable, TechnicalData,
                    ParameterGrid, EngineeringTable):
        if manual and any(k in title for k in ("glossary", "abbreviation")):
            return "glossary"
        return "technical_specs" if manual else "technical_data"
    if _section_has(section, DrawingReference, RevisionHistory):
        return "revision_history" if manual else "registers"
    if _section_has(section, BillOfMaterials):
        return "registers" if not manual else "bom"
    if _section_has(section, Procedure):
        if manual:
            return _match_manual_procedure(title)
        return "procedure"
    if _section_has(section, FormSection, RatingLegend, SignatureBlock):
        if manual and any(k in title for k in ("maintenance", "inspect", "service")):
            return "maintenance"
        return "form"
    if _section_has(section, FeatureGrid):
        if any(k in title for k in ("overview", "system", "summary", "intro", "scope")):
            return "overview" if not manual else "summary"
        return "features" if not manual else "product_description"
    for name, keywords in priority:
        if any(k in title for k in keywords):
            return name
    return "other"


def _fill_toc(sections: list[Section]) -> list[Section]:
    """Populate TableOfContentsBlock entries from section titles."""
    toc_titles: list[TocEntry] = []
    for s in sections:
        if not s.title:
            continue
        if _section_has(s, TableOfContentsBlock):
            continue
        # Skip the gaps section from TOC noise
        if (s.title or "").lower().startswith("information still required"):
            continue
        title = s.title.strip()
        level = 1
        if title[:1].isdigit():
            level = 1 + title.count(".")
            level = min(3, max(1, level))
        toc_titles.append(TocEntry(title=title, level=level))

    out: list[Section] = []
    for s in sections:
        blocks = []
        for b in (s.blocks or []):
            if isinstance(b, TableOfContentsBlock):
                blocks.append(TableOfContentsBlock(
                    id=b.id,
                    title=b.title or "Table of Contents",
                    entries=list(toc_titles),
                ))
            else:
                blocks.append(b)
        out.append(Section(
            id=s.id,
            title=s.title,
            blocks=blocks,
            page_break_before=s.page_break_before,
        ))
    return out


def _strip_mangler(text: str) -> tuple[str, list[str]]:
    missing: list[str] = []

    def repl(m: re.Match) -> str:
        key = (m.group(1) or "unspecified").strip()
        # Drop trailing "oppgi" residue if captured in group
        key = re.sub(r"\s*[—–-]\s*oppgi\s*$", "", key, flags=re.I).strip()
        if key:
            missing.append(key)
        return ""

    cleaned = _MANGLER_RE.sub(repl, text or "")
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    cleaned = re.sub(r"\s+([.,;:])", r"\1", cleaned)
    return cleaned, missing


class CompositionEngine:
    """
    Decides visual structure and region order before layout.
    Pipeline: Document AST → compose → MeasurementEngine → LayoutEngine → paint.
    """

    def compose(self, doc: Document) -> Document:
        if not doc:
            return Document(title="Document")
        species = (doc.metadata or {}).get("species") or ""
        dtype = (doc.document_type or "").lower()
        if dtype in ("form", "form_fill") or species == "form_fill":
            out = self._compose_form(doc)
        elif _is_manual(doc):
            out = self._compose_user_manual(doc)
        elif _is_industrial_report(doc):
            out = self._compose_industrial_report(doc)
        else:
            out = self._compose_document(doc)
        out.sections = _fill_toc(list(out.sections or []))
        meta = dict(out.metadata or {})
        meta["composed"] = True
        if _is_manual(doc):
            meta["composition"] = "user_manual"
            meta["manual_profile"] = list(MANUAL_PROFILE_ORDER)
        elif _is_industrial_report(doc):
            meta["composition"] = "industrial_report"
            meta["industrial_report_profile"] = list(INDUSTRIAL_REPORT_PROFILE_ORDER)
        out.metadata = meta
        return out

    def regions(self, doc: Document) -> list[PageRegion]:
        composed = self.compose(doc)
        manual = _is_manual(composed)
        out: list[PageRegion] = []
        if composed.hero:
            out.append(PageRegion(type="hero", blocks=[composed.hero], span=1.0))
        for s in composed.sections or []:
            rtype = _match_priority(s, manual=manual)
            if rtype == "other":
                rtype = "body"
            cols = 1
            for b in s.blocks or []:
                if isinstance(b, (FeatureGrid, FormSection)):
                    cols = max(cols, int(getattr(b, "columns", 1) or 1))
            out.append(PageRegion(
                type=rtype,
                blocks=list(s.blocks or []),
                columns=cols,
                title=s.title,
            ))
        return out

    def embed_diagram(
        self,
        doc: Document,
        svg: str,
        *,
        title: str | None = "System diagram",
        caption: str | None = None,
        height_pt: float = 240.0,
        page_break_before: bool = False,
        figure_number: str | None = None,
        source_citation: str | None = None,
        diagram_type: str | None = None,
        revision: str | None = None,
        graph_id: str | None = None,
        style_id: str | None = None,
    ) -> Document:
        """Append a DiagramBlock section (automatic diagram inclusion)."""
        out = deepcopy(doc)
        out.sections = list(out.sections or [])
        out.sections.append(Section(
            title=title,
            page_break_before=page_break_before,
            blocks=[DiagramBlock(
                svg=svg or "",
                caption=caption,
                title=title,
                height_pt=float(height_pt),
                figure_number=figure_number,
                source_citation=source_citation,
                diagram_type=diagram_type,
                revision=revision,
                graph_id=graph_id,
                style_id=style_id,
            )],
        ))
        return self.compose(out)

    # ── Industrial report composition ───────────────────────────────────

    def _compose_industrial_report(self, doc: Document) -> Document:
        """Reorder sections to INDUSTRIAL_REPORT_PROFILE; sanitize blocks."""
        src = deepcopy(doc)
        cleaned: list[Section] = []
        missing_facts: list[str] = []
        for section in src.sections or []:
            new_blocks = []
            for b in section.blocks or []:
                nb, miss = self._sanitize_block(b)
                missing_facts.extend(miss)
                if nb is not None:
                    new_blocks.append(nb)
            if new_blocks or section.title:
                cleaned.append(Section(
                    id=section.id,
                    title=section.title,
                    blocks=new_blocks,
                    page_break_before=section.page_break_before,
                ))
        used: set[int] = set()
        ordered: list[Section] = []
        for key, keywords in INDUSTRIAL_REPORT_PROFILE:
            section = self._take_matching_section(cleaned, keywords, used)
            if section is None and key == "revision_history":
                section = Section(
                    id="revision_history",
                    title="Revision History",
                    blocks=[RevisionHistory()],
                )
            if section is None:
                continue
            if not section.id:
                section.id = key
            ordered.append(section)
        for section in cleaned:
            if id(section) not in used:
                ordered.append(section)
        meta = dict(src.metadata or {})
        if missing_facts:
            meta["missing_facts"] = list(dict.fromkeys(missing_facts))
        return Document(
            title=src.title,
            document_type="industrial_report",
            theme=src.theme or "industrial_report",
            hero=src.hero,
            sections=ordered,
            metadata=meta,
            language=src.language,
        )

    # ── User-manual composition ─────────────────────────────────────────

    def _compose_user_manual(self, doc: Document) -> Document:
        src = deepcopy(doc)
        missing_facts: list[str] = []
        hero = src.hero

        # Sanitize prose in every section; lift HeroBlocks to document.hero
        cleaned_sections: list[Section] = []
        for section in src.sections or []:
            heroes = [b for b in (section.blocks or []) if isinstance(b, HeroBlock)]
            other = [b for b in (section.blocks or []) if not isinstance(b, HeroBlock)]
            if heroes and hero is None:
                hero = heroes[0]
            new_blocks = []
            for b in other:
                nb, miss = self._sanitize_block(b)
                missing_facts.extend(miss)
                if nb is not None:
                    new_blocks.append(nb)
            if new_blocks or section.title:
                cleaned_sections.append(Section(
                    id=section.id,
                    title=section.title,
                    blocks=new_blocks,
                    page_break_before=section.page_break_before,
                ))
        src.sections = cleaned_sections
        if hero and isinstance(hero, HeroBlock):
            hero, miss = self._sanitize_hero(hero)
            missing_facts.extend(miss)

        used: set[int] = set()
        ordered: list[Section] = []

        for key, keywords in USER_MANUAL_PROFILE:
            section = self._take_matching_section(src.sections, keywords, used)
            if section is None and key in _AUTO_SHELLS:
                title = {
                    "symbols": "Symbols",
                    "toc": "Table of Contents",
                    "revision_history": "Revision History",
                }.get(key, key.replace("_", " ").title())
                blocks: list = []
                if key == "toc":
                    blocks = [TableOfContentsBlock()]
                section = Section(title=title, blocks=blocks)

            if section is None:
                continue

            section = self._force_block_types(key, section)
            # Drop cover leftovers into hero; keep non-hero cover blocks
            if key == "cover":
                heroes = [b for b in section.blocks if isinstance(b, HeroBlock)]
                other = [b for b in section.blocks if not isinstance(b, HeroBlock)]
                if heroes and hero is None:
                    hero = heroes[0]
                section.blocks = other
                if not section.blocks and not section.title:
                    continue
                if not section.blocks:
                    continue
            ordered.append(section)

        # Leftover unmatched sections
        leftovers = [
            s for s in (src.sections or []) if id(s) not in used
        ]
        if leftovers:
            extra_blocks = []
            for s in leftovers:
                if s.title:
                    extra_blocks.append(HeadingBlock(text=s.title, level=2))
                extra_blocks.extend(s.blocks or [])
            if extra_blocks:
                ordered.append(Section(
                    title="Additional Information",
                    blocks=extra_blocks,
                ))

        # Dedupe missing facts (stable order)
        seen: set[str] = set()
        unique_missing: list[str] = []
        for m in missing_facts:
            if m not in seen:
                seen.add(m)
                unique_missing.append(m)

        if unique_missing:
            ordered.append(Section(
                title="Information Still Required",
                page_break_before=True,
                blocks=[
                    CalloutBox(
                        variant="warning",
                        title="Missing facts",
                        text=(
                            "The following items could not be filled from the "
                            "project sources. They must be supplied before the "
                            "manual is released."
                        ),
                    ),
                    EngineeringTable(
                        headers=["Field", "Status"],
                        rows=[[m, "Required"] for m in unique_missing],
                        caption="Gaps that block a complete manual",
                    ),
                ],
            ))

        return Document(
            title=src.title,
            document_type="user_manual",
            language=src.language,
            hero=hero,
            theme=src.theme or "engineering",
            metadata=dict(src.metadata or {}),
            sections=ordered,
        )

    def _take_matching_section(
        self,
        sections: list[Section],
        keywords: list[str],
        used: set[int],
    ) -> Section | None:
        for sec in sections:
            sid = id(sec)
            if sid in used:
                continue
            title = (sec.title or "").lower()
            if any(k in title for k in keywords):
                used.add(sid)
                return Section(
                    id=sec.id,
                    title=sec.title,
                    blocks=list(sec.blocks or []),
                    page_break_before=sec.page_break_before,
                )
        return None

    def _force_block_types(self, key: str, section: Section) -> Section:
        """Convert loose content into the correct professional blocks."""
        blocks = list(section.blocks or [])

        if key in ("technical_specs", "glossary"):
            tables = [
                b for b in blocks
                if isinstance(b, (
                    EngineeringTable, SpecificationTable,
                    ParameterGrid, TechnicalData,
                ))
            ]
            if tables:
                blocks = tables
            else:
                rows: list[list[str]] = []
                for b in blocks:
                    if isinstance(b, ParagraphBlock) and ":" in (b.text or ""):
                        parts = b.text.split(":", 1)
                        rows.append([parts[0].strip(), parts[1].strip()])
                    elif isinstance(b, BulletList):
                        for item in b.items or []:
                            if ":" in str(item):
                                parts = str(item).split(":", 1)
                                rows.append([parts[0].strip(), parts[1].strip()])
                if rows:
                    headers = (
                        ["Term", "Definition"] if key == "glossary"
                        else ["Parameter", "Specification"]
                    )
                    blocks = [EngineeringTable(
                        headers=headers,
                        rows=rows,
                        caption=section.title,
                    )]

        elif key in (
            "assembly", "installation", "operation",
            "maintenance", "troubleshooting",
        ):
            procs = [b for b in blocks if isinstance(b, Procedure)]
            warns = [
                b for b in blocks
                if isinstance(b, (WarningBox, CalloutBox, NoteBox))
            ]
            if procs:
                blocks = procs + warns
            else:
                steps: list[ProcedureStep] = []
                n = 1
                for b in blocks:
                    if isinstance(b, ParagraphBlock) and (b.text or "").strip():
                        steps.append(ProcedureStep(
                            number=n, title=f"Step {n}",
                            description=b.text.strip(),
                        ))
                        n += 1
                    elif isinstance(b, BulletList):
                        for item in b.items or []:
                            steps.append(ProcedureStep(
                                number=n, title=f"Step {n}",
                                description=str(item),
                            ))
                            n += 1
                if steps:
                    blocks = [
                        Procedure(
                            title=section.title or "Procedure",
                            steps=steps,
                        ),
                        *warns,
                    ]

        elif key == "revision_history":
            revs = [b for b in blocks if isinstance(b, RevisionHistory)]
            if revs:
                blocks = revs
            else:
                blocks = [RevisionHistory(
                    title="Revision History",
                    entries=[RevisionEntry(
                        rev="—", date="—",
                        description="No revision data supplied",
                        author="—",
                    )],
                )]

        elif key == "symbols":
            callouts = [
                b for b in blocks
                if isinstance(b, (CalloutBox, WarningBox, NoteBox))
            ]
            if callouts:
                blocks = callouts
            else:
                blocks = [
                    CalloutBox(
                        variant="warning", title="WARNING",
                        text="Serious health risk or damage to equipment.",
                    ),
                    CalloutBox(
                        variant="note", title="NOTE",
                        text="Useful hints and recommendations.",
                    ),
                    CalloutBox(
                        variant="requirement", title="REQUIREMENT",
                        text="Mandatory action or condition.",
                    ),
                ]

        elif key == "toc":
            if not any(isinstance(b, TableOfContentsBlock) for b in blocks):
                blocks = [TableOfContentsBlock(), *blocks]

        section.blocks = blocks
        return section

    def _sanitize_block(self, block: Any) -> tuple[Any | None, list[str]]:
        """Remove [MANGLER: …] from running prose. Return (block, missing keys)."""
        if isinstance(block, ParagraphBlock):
            text, missing = _strip_mangler(block.text or "")
            if not text:
                return None, missing
            return ParagraphBlock(
                text=text, style=block.style, id=block.id,
            ), missing
        if isinstance(block, BulletList):
            cleaned: list[str] = []
            missing: list[str] = []
            for item in block.items or []:
                t, m = _strip_mangler(str(item))
                missing.extend(m)
                if t:
                    cleaned.append(t)
            if not cleaned:
                return None, missing
            return BulletList(
                items=cleaned, style=block.style, id=block.id,
            ), missing
        if isinstance(block, CalloutBox):
            text, missing = _strip_mangler(block.text or "")
            return CalloutBox(
                text=text, variant=block.variant,
                title=block.title, id=block.id,
                attribution=getattr(block, "attribution", None),
                icon=getattr(block, "icon", None),
            ), missing
        if isinstance(block, (WarningBox, NoteBox)):
            text, missing = _strip_mangler(getattr(block, "text", "") or "")
            block_copy = deepcopy(block)
            block_copy.text = text
            return block_copy, missing
        if isinstance(block, Procedure):
            missing: list[str] = []
            steps = []
            for s in block.steps or []:
                title, m1 = _strip_mangler(getattr(s, "title", "") or "")
                desc, m2 = _strip_mangler(getattr(s, "description", "") or "")
                warn = getattr(s, "warning", None)
                m3: list[str] = []
                if warn:
                    warn, m3 = _strip_mangler(warn)
                    if not warn:
                        warn = None
                missing.extend(m1 + m2 + m3)
                steps.append(ProcedureStep(
                    number=int(getattr(s, "number", len(steps) + 1)),
                    title=title or f"Step {len(steps) + 1}",
                    description=desc,
                    warning=warn,
                    image=getattr(s, "image", None),
                ))
            return Procedure(
                title=block.title, steps=steps,
                prerequisite=block.prerequisite, id=block.id,
            ), missing
        return block, []

    def _sanitize_hero(self, hero: HeroBlock) -> tuple[HeroBlock, list[str]]:
        missing: list[str] = []
        headline, m1 = _strip_mangler(hero.headline or "")
        summary, m2 = _strip_mangler(hero.summary or "")
        missing.extend(m1 + m2)
        bullets = []
        for b in hero.bullets or []:
            t, m = _strip_mangler(str(b))
            missing.extend(m)
            if t:
                bullets.append(t)
        return HeroBlock(
            headline=headline, summary=summary,
            image=hero.image, bullets=bullets, id=hero.id,
        ), missing

    # ── Form / datasheet ────────────────────────────────────────────────

    def _compose_form(self, doc: Document) -> Document:
        """Keep form reading order: legend → fields → sign-off."""
        legend: list[Section] = []
        signoff: list[Section] = []
        body: list[Section] = []
        for s in doc.sections or []:
            if _section_has(s, RatingLegend) and not _section_has(s, FormSection):
                legend.append(s)
            elif _section_has(s, SignatureBlock) and not _section_has(s, FormSection):
                signoff.append(s)
            else:
                body.append(s)
        return Document(
            title=doc.title,
            document_type=doc.document_type,
            language=doc.language,
            hero=doc.hero,
            theme=doc.theme,
            metadata=dict(doc.metadata or {}),
            sections=legend + body + signoff,
        )

    def _compose_manual(self, doc: Document) -> Document:
        """Alias — user manuals use _compose_user_manual."""
        return self._compose_user_manual(doc)

    def _compose_document(self, doc: Document) -> Document:
        """Priority keyword + block-type order for datasheets / product sheets."""
        return self._order_sections(doc, _PRIORITY, manual=False)

    def _order_sections(
        self,
        doc: Document,
        priority: list[tuple[str, list[str]]],
        *,
        manual: bool,
    ) -> Document:
        hero = doc.hero
        remaining: list[Section] = []

        for section in doc.sections or []:
            heroes = [b for b in (section.blocks or []) if isinstance(b, HeroBlock)]
            other = [b for b in (section.blocks or []) if not isinstance(b, HeroBlock)]
            if heroes and hero is None:
                hero = heroes[0]
            if heroes:
                if other or section.title:
                    remaining.append(Section(
                        id=section.id,
                        title=section.title,
                        blocks=other,
                        page_break_before=section.page_break_before,
                    ))
            else:
                remaining.append(section)

        buckets: dict[str, list[Section]] = {name: [] for name, _ in priority}
        buckets["other"] = []
        used: set[int] = set()

        for name, _keywords in priority:
            for section in remaining:
                sid = id(section)
                if sid in used:
                    continue
                if _match_priority(section, manual=manual) == name:
                    buckets[name].append(section)
                    used.add(sid)

        for section in remaining:
            if id(section) not in used:
                buckets["other"].append(section)
                used.add(id(section))

        ordered: list[Section] = []
        for name, _ in priority:
            ordered.extend(buckets[name])
        ordered.extend(buckets["other"])

        return Document(
            title=doc.title,
            document_type=doc.document_type,
            language=doc.language,
            hero=hero,
            theme=doc.theme,
            metadata=dict(doc.metadata or {}),
            sections=ordered,
        )


def diagram_block_from_svg(
    svg: str,
    *,
    title: str | None = None,
    caption: str | None = None,
    height_pt: float = 240.0,
    figure_number: str | None = None,
    source_citation: str | None = None,
    diagram_type: str | None = None,
    revision: str | None = None,
    graph_id: str | None = None,
    style_id: str | None = None,
) -> DiagramBlock:
    return DiagramBlock(
        svg=svg or "",
        title=title,
        caption=caption,
        height_pt=float(height_pt),
        figure_number=figure_number,
        source_citation=source_citation,
        diagram_type=diagram_type,
        revision=revision,
        graph_id=graph_id,
        style_id=style_id,
    )


def embed_diagram_engine(doc: Document, diagram_engine: Any, **kwargs) -> Document:
    """Render a DiagramEngine to SVG and embed via CompositionEngine."""
    svg = diagram_engine.render_svg() if hasattr(diagram_engine, "render_svg") else str(diagram_engine)
    title = kwargs.pop("title", None) or getattr(diagram_engine, "title", None) or "System diagram"
    if kwargs.get("diagram_type") is None and hasattr(diagram_engine, "resolve_render_profile"):
        try:
            kwargs["diagram_type"] = diagram_engine.resolve_render_profile()
        except Exception:
            pass
    if kwargs.get("graph_id") is None and hasattr(diagram_engine, "spec"):
        spec = diagram_engine.spec or {}
        if isinstance(spec, dict) and spec.get("id"):
            kwargs["graph_id"] = str(spec["id"])
    if kwargs.get("style_id") is None and hasattr(diagram_engine, "diagram_style_id"):
        kwargs["style_id"] = getattr(diagram_engine, "diagram_style_id", None)
    return CompositionEngine().embed_diagram(doc, svg, title=title, **kwargs)
