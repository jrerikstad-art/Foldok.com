"""Block types — visual atoms. LLM may propose these; code alone draws."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Optional, Union


@dataclass
class Block:
    type: str
    id: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ParagraphBlock(Block):
    type: Literal["paragraph"] = "paragraph"
    text: str = ""
    style: Literal["body", "lead", "caption", "note"] = "body"


@dataclass
class HeadingBlock(Block):
    type: Literal["heading"] = "heading"
    text: str = ""
    level: Literal[1, 2, 3] = 2


@dataclass
class BulletList(Block):
    type: Literal["bullet_list"] = "bullet_list"
    items: list[str] = field(default_factory=list)
    style: Literal["standard", "check", "feature"] = "standard"


@dataclass
class FeatureCard:
    title: str
    description: str
    icon: Optional[str] = None
    metric: Optional[str] = None  # e.g. "40+ lines"
    rating: Optional[int] = None  # 1–5 when used as a summary card
    role: Optional[str] = None


@dataclass
class FeatureGrid(Block):
    """Grid of FeatureCard and/or StakeholderCard summary cards."""
    type: Literal["feature_grid"] = "feature_grid"
    items: list = field(default_factory=list)  # FeatureCard | StakeholderCard
    columns: int = 2


@dataclass
class StakeholderCard(Block):
    """Stakeholder view with rating, needs, and pain points."""
    type: Literal["stakeholder_card"] = "stakeholder_card"
    name: str = ""
    rating: int = 3
    needs: list[str] = field(default_factory=list)
    pain_points: list[str] = field(default_factory=list)
    role: Optional[str] = None


@dataclass
class EvaluationMatrix(Block):
    """Frequency × Impact, risk, or priority matrix (2D grid)."""
    type: Literal["evaluation_matrix"] = "evaluation_matrix"
    title: str = ""
    rows: list[str] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    values: list[list[str]] = field(default_factory=list)
    highlight: Optional[str] = None  # "row,col" or cell text to emphasize
    legend: Optional[dict] = None


@dataclass
class ComparisonTable(Block):
    """Today vs future / current vs proposed comparison."""
    type: Literal["comparison_table"] = "comparison_table"
    title: str = ""
    left_header: str = "Today"
    right_header: str = "With solution"
    rows: list[dict] = field(default_factory=list)
    # each row: {"aspect": "...", "today": "...", "future": "..."}
    # aliases left/right also accepted in block_from_dict


@dataclass
class Rating(Block):
    """1–5 (or custom max) star / bar rating for tables and cards."""
    type: Literal["rating"] = "rating"
    value: int = 0
    max_value: int = 5
    label: Optional[str] = None


@dataclass
class ParameterItem:
    name: str
    value: str
    unit: Optional[str] = None
    note: Optional[str] = None


@dataclass
class ParameterGrid(Block):
    """Key engineering parameters in a clean multi-column grid."""
    type: Literal["parameter_grid"] = "parameter_grid"
    items: list[ParameterItem] = field(default_factory=list)
    title: Optional[str] = None
    columns: int = 2


@dataclass
class DrawingReference(Block):
    """Reference to a drawing / P&ID / GA with revision."""
    type: Literal["drawing_reference"] = "drawing_reference"
    number: str = ""
    title: str = ""
    revision: str = ""
    date: Optional[str] = None
    sheet: Optional[str] = None


@dataclass
class RevisionEntry:
    rev: str
    date: str
    description: str
    author: str


@dataclass
class RevisionHistory(Block):
    type: Literal["revision_history"] = "revision_history"
    entries: list[RevisionEntry] = field(default_factory=list)
    title: str = "Revision History"


@dataclass
class EngineeringTable(Block):
    """
    Professional engineering table with numeric alignment,
    optional unit row, and footnotes.
    """
    type: Literal["engineering_table"] = "engineering_table"
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    units: Optional[list[str]] = None
    caption: Optional[str] = None
    footnotes: list[str] = field(default_factory=list)
    numeric_cols: list[int] = field(default_factory=list)


@dataclass
class SpecRow:
    property: str
    values: list[str] = field(default_factory=list)
    unit: Optional[str] = None
    note: Optional[str] = None


@dataclass
class SpecificationTable(Block):
    type: Literal["specification_table"] = "specification_table"
    headers: list[str] = field(default_factory=list)
    rows: list[SpecRow] = field(default_factory=list)
    footnotes: list[str] = field(default_factory=list)
    caption: Optional[str] = None


@dataclass
class ImageBlock(Block):
    type: Literal["image"] = "image"
    src: str = ""
    alt: str = ""
    role: Literal["hero", "figure", "exploded", "component", "diagram"] = "figure"
    caption: Optional[str] = None
    width: Optional[str] = None  # full | half | third | auto


@dataclass
class CalloutBox(Block):
    type: Literal["callout"] = "callout"
    text: str = ""
    variant: Literal[
        "note", "warning", "important", "tip", "requirement",
        "insight", "quote",
    ] = "note"
    title: Optional[str] = None
    attribution: Optional[str] = None  # e.g. "— Head of Operations"
    icon: Optional[str] = None


@dataclass
class TocEntry:
    title: str
    level: int = 1
    page_hint: Optional[str] = None


@dataclass
class TableOfContentsBlock(Block):
    """Auto-filled from section titles by CompositionEngine."""
    type: Literal["table_of_contents"] = "table_of_contents"
    entries: list[TocEntry] = field(default_factory=list)
    title: str = "Table of Contents"


@dataclass
class HeroBlock(Block):
    type: Literal["hero"] = "hero"
    headline: str = ""
    summary: str = ""
    image: Optional[str] = None
    bullets: list[str] = field(default_factory=list)


@dataclass
class ProcedureStep:
    number: int
    title: str
    description: str
    warning: Optional[str] = None
    image: Optional[str] = None


@dataclass
class Procedure(Block):
    type: Literal["procedure"] = "procedure"
    title: str = ""
    steps: list = field(default_factory=list)
    prerequisite: Optional[str] = None


@dataclass
class TimelineEvent:
    date: str
    title: str
    description: str
    status: Literal["done", "current", "upcoming"] = "done"


@dataclass
class Timeline(Block):
    type: Literal["timeline"] = "timeline"
    events: list = field(default_factory=list)


@dataclass
class BOMItem:
    part_number: str
    description: str
    quantity: str
    unit: str = "pcs"
    material: Optional[str] = None
    remark: Optional[str] = None


@dataclass
class BillOfMaterials(Block):
    type: Literal["bom"] = "bom"
    title: str = "Bill of Materials"
    items: list = field(default_factory=list)
    caption: Optional[str] = None


@dataclass
class ProcessStep:
    number: int
    title: str
    description: str
    icon: Optional[str] = None


@dataclass
class ProcessFlow(Block):
    type: Literal["process_flow"] = "process_flow"
    steps: list = field(default_factory=list)
    direction: Literal["horizontal", "vertical"] = "horizontal"


@dataclass
class WarningBox(Block):
    type: Literal["warning"] = "warning"
    title: str = "Warning"
    text: str = ""


@dataclass
class NoteBox(Block):
    type: Literal["note"] = "note"
    title: str = "Note"
    text: str = ""


@dataclass
class TechnicalData(Block):
    """Key-value technical data (property → value)."""
    type: Literal["technical_data"] = "technical_data"
    items: list = field(default_factory=list)  # list[tuple[str, str]]
    title: Optional[str] = None


# ── Form-specific blocks ─────────────────────────────────────────────

FIELD_TYPES = (
    "text", "number", "date", "email", "checkbox",
    "rating3", "measure", "signature", "photo", "select", "check",
)


@dataclass
class FormField:
    key: str
    label: str
    field_type: str = "text"
    value: Any = None
    unit: Optional[str] = None
    required: bool = False
    options: list = field(default_factory=list)
    source: Optional[str] = None
    note: str = ""


@dataclass
class FormSection(Block):
    type: Literal["form_section"] = "form_section"
    title: str = ""
    fields: list = field(default_factory=list)  # list[FormField]
    columns: int = 1


@dataclass
class SignatureBlock(Block):
    type: Literal["signature"] = "signature"
    label: str = "Technician signature"
    name: Optional[str] = None
    date: Optional[str] = None
    image: Optional[str] = None


@dataclass
class RatingLegend(Block):
    """Fixed visual legend for green / yellow / red rating3."""
    type: Literal["rating_legend"] = "rating_legend"


@dataclass
class DiagramBlock(Block):
    """Embedded engineering figure (SVG) — print-safe, not photoreal.

    Caption + figure_number + source_citation make manuals coherent.
    Geometry always comes from DiagramEngine (deterministic), never free-draw AI.
    """
    type: Literal["diagram"] = "diagram"
    svg: str = ""
    src: Optional[str] = None
    caption: Optional[str] = None
    title: Optional[str] = None
    height_pt: float = 240.0
    figure_number: Optional[str] = None       # e.g. "3.2" or "12"
    source_citation: Optional[str] = None     # e.g. "BOM rev B · panel schedule"
    diagram_type: Optional[str] = None        # single_line | wiring | piping | …
    revision: Optional[str] = None
    graph_id: Optional[str] = None            # link back to confirmed graph
    style_id: Optional[str] = None            # DiagramStyle id, e.g. engineering_default


@dataclass
class CalculationBlock(Block):
    """Verified calculation section — library formula + cited inputs + confirm.

    Engine evaluates curated formula_code only. Never an LLM numeric result.
    Formal report use requires status=confirmed.
    """
    type: Literal["calculation"] = "calculation"
    title: Optional[str] = None
    profile: Optional[str] = None
    formula_latex: Optional[str] = None
    formula_code: Optional[str] = None
    inputs: list = field(default_factory=list)   # list[dict]
    outputs: list = field(default_factory=list)
    assumptions: list = field(default_factory=list)
    status: str = "draft"                        # draft|needs_input|ready_for_review|confirmed
    status_label: Optional[str] = None
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[str] = None
    revision: int = 1
    calculation_id: Optional[str] = None
    disclaimer: Optional[str] = None
    text: Optional[str] = None                   # plain-text fallback
    material_id: Optional[str] = None
    section_id: Optional[str] = None
    binding: Optional[dict] = None


@dataclass
class MaterialBlock(Block):
    """Material / section property table for design-report groundwork."""
    type: Literal["material"] = "material"
    title: Optional[str] = None
    binding: Optional[dict] = None
    disclaimer: Optional[str] = None
    text: Optional[str] = None
    code_compliance_claimed: bool = False


AnyBlock = Union[
    ParagraphBlock,
    HeadingBlock,
    BulletList,
    FeatureGrid,
    StakeholderCard,
    EvaluationMatrix,
    ComparisonTable,
    Rating,
    SpecificationTable,
    ImageBlock,
    CalloutBox,
    HeroBlock,
    Procedure,
    Timeline,
    BillOfMaterials,
    ProcessFlow,
    WarningBox,
    NoteBox,
    TechnicalData,
    FormSection,
    SignatureBlock,
    RatingLegend,
    DiagramBlock,
    CalculationBlock,
    MaterialBlock,
    ParameterGrid,
    DrawingReference,
    RevisionHistory,
    EngineeringTable,
    TableOfContentsBlock,
]


def block_from_dict(d: dict) -> AnyBlock | Block:
    """Deserialize a plain dict (e.g. from JSON / LLM) into a block."""
    if not isinstance(d, dict):
        return Block(type="unknown")
    t = (d.get("type") or "").lower()
    if t == "paragraph":
        return ParagraphBlock(
            text=d.get("text") or "", style=d.get("style") or "body", id=d.get("id"))
    if t == "heading":
        lvl = int(d.get("level") or 2)
        lvl = 1 if lvl < 1 else 3 if lvl > 3 else lvl
        return HeadingBlock(text=d.get("text") or "", level=lvl, id=d.get("id"))  # type: ignore[arg-type]
    if t in ("bullet_list", "bullets"):
        return BulletList(
            items=list(d.get("items") or []),
            style=d.get("style") or "standard", id=d.get("id"))
    if t == "feature_grid":
        items = []
        for it in d.get("items") or []:
            if isinstance(it, (FeatureCard, StakeholderCard)):
                items.append(it)
            elif isinstance(it, dict):
                kind = (it.get("type") or it.get("kind") or "").lower()
                if kind in ("stakeholder_card", "stakeholder") or (
                    "needs" in it or "pain_points" in it
                ):
                    items.append(StakeholderCard(
                        name=it.get("name") or it.get("title") or "",
                        rating=int(it.get("rating") or 3),
                        needs=list(it.get("needs") or []),
                        pain_points=list(it.get("pain_points") or []),
                        role=it.get("role"),
                        id=it.get("id"),
                    ))
                else:
                    rating = it.get("rating")
                    items.append(FeatureCard(
                        title=it.get("title") or it.get("name") or "",
                        description=it.get("description") or "",
                        icon=it.get("icon"),
                        metric=it.get("metric"),
                        rating=int(rating) if rating is not None else None,
                        role=it.get("role"),
                    ))
        return FeatureGrid(items=items, columns=int(d.get("columns") or 2), id=d.get("id"))
    if t in ("stakeholder_card", "stakeholder"):
        return StakeholderCard(
            name=d.get("name") or "",
            rating=int(d.get("rating") or 3),
            needs=list(d.get("needs") or []),
            pain_points=list(d.get("pain_points") or []),
            role=d.get("role"),
            id=d.get("id"),
        )
    if t in ("evaluation_matrix", "risk_matrix", "priority_matrix"):
        values = []
        for row in d.get("values") or []:
            if isinstance(row, (list, tuple)):
                values.append([str(c) for c in row])
            else:
                values.append([str(row)])
        legend = d.get("legend")
        return EvaluationMatrix(
            title=d.get("title") or "",
            rows=[str(r) for r in (d.get("rows") or [])],
            columns=[str(c) for c in (d.get("columns") or [])],
            values=values,
            highlight=d.get("highlight"),
            legend=legend if isinstance(legend, dict) else None,
            id=d.get("id"),
        )
    if t in ("comparison_table", "comparison"):
        rows = []
        for r in d.get("rows") or []:
            if isinstance(r, dict):
                rows.append({
                    "aspect": str(r.get("aspect") or r.get("label") or ""),
                    "today": str(
                        r.get("today") or r.get("left") or r.get("current") or ""
                    ),
                    "future": str(
                        r.get("future") or r.get("right") or r.get("proposed") or ""
                    ),
                })
        return ComparisonTable(
            title=d.get("title") or "",
            left_header=d.get("left_header") or "Today",
            right_header=d.get("right_header") or "With solution",
            rows=rows,
            id=d.get("id"),
        )
    if t == "rating":
        return Rating(
            value=int(d.get("value") or 0),
            max_value=int(d.get("max_value") or 5),
            label=d.get("label"),
            id=d.get("id"),
        )
    if t == "parameter_grid":
        items = []
        for it in d.get("items") or []:
            if isinstance(it, ParameterItem):
                items.append(it)
            elif isinstance(it, dict):
                items.append(ParameterItem(
                    name=it.get("name") or it.get("property") or "",
                    value=str(it.get("value") or ""),
                    unit=it.get("unit"),
                    note=it.get("note"),
                ))
            elif isinstance(it, (list, tuple)) and len(it) >= 2:
                items.append(ParameterItem(
                    name=str(it[0]), value=str(it[1]),
                    unit=str(it[2]) if len(it) > 2 else None,
                ))
        return ParameterGrid(
            items=items,
            title=d.get("title"),
            columns=int(d.get("columns") or 2),
            id=d.get("id"),
        )
    if t in ("drawing_reference", "drawing_ref"):
        return DrawingReference(
            number=d.get("number") or "",
            title=d.get("title") or "",
            revision=d.get("revision") or d.get("rev") or "",
            date=d.get("date"),
            sheet=d.get("sheet"),
            id=d.get("id"),
        )
    if t in ("revision_history", "revisions"):
        entries = []
        for e in d.get("entries") or []:
            if isinstance(e, RevisionEntry):
                entries.append(e)
            elif isinstance(e, dict):
                entries.append(RevisionEntry(
                    rev=str(e.get("rev") or e.get("revision") or ""),
                    date=str(e.get("date") or ""),
                    description=str(e.get("description") or ""),
                    author=str(e.get("author") or ""),
                ))
        return RevisionHistory(
            entries=entries,
            title=d.get("title") or "Revision History",
            id=d.get("id"),
        )
    if t == "engineering_table":
        rows = []
        for r in d.get("rows") or []:
            if isinstance(r, (list, tuple)):
                rows.append([str(c) for c in r])
            elif isinstance(r, dict):
                rows.append([str(c) for c in (r.get("cells") or r.get("values") or [])])
        units = d.get("units")
        return EngineeringTable(
            headers=list(d.get("headers") or []),
            rows=rows,
            units=list(units) if units else None,
            caption=d.get("caption"),
            footnotes=list(d.get("footnotes") or []),
            numeric_cols=[int(i) for i in (d.get("numeric_cols") or [])],
            id=d.get("id"),
        )
    if t in ("specification_table", "spec_table"):
        rows = []
        for r in d.get("rows") or []:
            if isinstance(r, SpecRow):
                rows.append(r)
            elif isinstance(r, dict):
                vals = r.get("values")
                if vals is None and isinstance(r.get("cells"), list):
                    # [property, *values, note?]
                    cells = r["cells"]
                    prop = str(cells[0]) if cells else ""
                    vals = [str(c) for c in cells[1:]]
                    rows.append(SpecRow(property=prop, values=vals))
                else:
                    rows.append(SpecRow(
                        property=r.get("property") or r.get("name") or "",
                        values=[str(v) for v in (vals or [])],
                        unit=r.get("unit"),
                        note=r.get("note"),
                    ))
            elif isinstance(r, (list, tuple)) and r:
                rows.append(SpecRow(
                    property=str(r[0]),
                    values=[str(x) for x in r[1:]],
                ))
        return SpecificationTable(
            headers=list(d.get("headers") or []),
            rows=rows,
            footnotes=list(d.get("footnotes") or []),
            caption=d.get("caption"),
            id=d.get("id"),
        )
    if t == "image":
        role = (d.get("role") or "figure").lower()
        if role not in ("hero", "figure", "exploded", "component", "diagram"):
            role = "figure"
        return ImageBlock(
            src=d.get("src") or "", alt=d.get("alt") or "",
            role=role, caption=d.get("caption"),
            width=d.get("width"), id=d.get("id"))
    if t == "callout":
        variant = (d.get("variant") or "note").lower()
        allowed = (
            "note", "warning", "important", "tip", "requirement",
            "insight", "quote",
        )
        if variant not in allowed:
            variant = "note"
        return CalloutBox(
            text=d.get("text") or d.get("content") or "",
            variant=variant,  # type: ignore[arg-type]
            title=d.get("title"),
            attribution=d.get("attribution"),
            icon=d.get("icon"),
            id=d.get("id"),
        )
    if t in ("table_of_contents", "toc"):
        entries = []
        for e in d.get("entries") or []:
            if isinstance(e, TocEntry):
                entries.append(e)
            elif isinstance(e, dict):
                entries.append(TocEntry(
                    title=str(e.get("title") or ""),
                    level=int(e.get("level") or 1),
                    page_hint=e.get("page_hint") or e.get("page"),
                ))
            elif isinstance(e, str):
                entries.append(TocEntry(title=e))
        return TableOfContentsBlock(
            entries=entries,
            title=d.get("title") or "Table of Contents",
            id=d.get("id"),
        )
    if t == "hero":
        return HeroBlock(
            headline=d.get("headline") or d.get("title") or "",
            summary=d.get("summary") or d.get("tagline") or "",
            image=d.get("image"),
            bullets=list(d.get("bullets") or d.get("bullet_points") or []),
            id=d.get("id"),
        )
    if t == "procedure":
        steps = []
        for s in d.get("steps") or []:
            if isinstance(s, ProcedureStep):
                steps.append(s)
            elif isinstance(s, dict):
                steps.append(ProcedureStep(
                    number=int(s.get("number") or len(steps) + 1),
                    title=s.get("title") or "",
                    description=s.get("description") or "",
                    warning=s.get("warning"),
                    image=s.get("image"),
                ))
        return Procedure(
            title=d.get("title") or "", steps=steps,
            prerequisite=d.get("prerequisite"), id=d.get("id"))
    if t == "timeline":
        events = []
        for e in d.get("events") or []:
            if isinstance(e, TimelineEvent):
                events.append(e)
            elif isinstance(e, dict):
                st = e.get("status") or "done"
                if st not in ("done", "current", "upcoming"):
                    st = "done"
                events.append(TimelineEvent(
                    date=e.get("date") or "", title=e.get("title") or "",
                    description=e.get("description") or "", status=st))
        return Timeline(events=events, id=d.get("id"))
    if t == "bom":
        items = []
        for it in d.get("items") or []:
            if isinstance(it, BOMItem):
                items.append(it)
            elif isinstance(it, dict):
                items.append(BOMItem(
                    part_number=it.get("part_number") or it.get("pn") or "",
                    description=it.get("description") or "",
                    quantity=str(it.get("quantity") or ""),
                    unit=it.get("unit") or "pcs",
                    material=it.get("material"),
                    remark=it.get("remark"),
                ))
        return BillOfMaterials(
            title=d.get("title") or "Bill of Materials",
            items=items, caption=d.get("caption"), id=d.get("id"))
    if t == "process_flow":
        steps = []
        for s in d.get("steps") or []:
            if isinstance(s, ProcessStep):
                steps.append(s)
            elif isinstance(s, dict):
                steps.append(ProcessStep(
                    number=int(s.get("number") or len(steps) + 1),
                    title=s.get("title") or "",
                    description=s.get("description") or "",
                    icon=s.get("icon"),
                ))
        direction = d.get("direction") or "horizontal"
        if direction not in ("horizontal", "vertical"):
            direction = "horizontal"
        return ProcessFlow(steps=steps, direction=direction, id=d.get("id"))
    if t == "warning":
        return WarningBox(
            title=d.get("title") or "Warning", text=d.get("text") or "", id=d.get("id"))
    if t == "note":
        return NoteBox(
            title=d.get("title") or "Note", text=d.get("text") or "", id=d.get("id"))
    if t == "technical_data":
        items = []
        for it in d.get("items") or []:
            if isinstance(it, (list, tuple)) and len(it) >= 2:
                items.append((str(it[0]), str(it[1])))
            elif isinstance(it, dict):
                items.append((
                    str(it.get("property") or it.get("key") or ""),
                    str(it.get("value") or ""),
                ))
        return TechnicalData(
            items=items, title=d.get("title"), id=d.get("id"))
    if t == "form_section":
        fields = []
        for f in d.get("fields") or []:
            if isinstance(f, FormField):
                fields.append(f)
            elif isinstance(f, dict):
                ft = (f.get("field_type") or f.get("type") or "text").lower()
                if ft == "check":
                    ft = "checkbox"
                fields.append(FormField(
                    key=f.get("key") or "",
                    label=f.get("label") or f.get("key") or "",
                    field_type=ft,
                    value=f.get("value"),
                    unit=f.get("unit"),
                    required=bool(f.get("required")),
                    options=list(f.get("options") or []),
                    source=f.get("source"),
                    note=f.get("note") or "",
                ))
        cols = int(d.get("columns") or 1)
        if cols not in (1, 2):
            cols = 1
        return FormSection(
            title=d.get("title") or "", fields=fields,
            columns=cols, id=d.get("id"))
    if t == "signature":
        return SignatureBlock(
            label=d.get("label") or "Technician signature",
            name=d.get("name"), date=d.get("date"),
            image=d.get("image"), id=d.get("id"))
    if t == "rating_legend":
        return RatingLegend(id=d.get("id"))
    if t == "diagram":
        return DiagramBlock(
            svg=d.get("svg") or "",
            src=d.get("src"),
            caption=d.get("caption"),
            title=d.get("title"),
            height_pt=float(d.get("height_pt") or 240),
            figure_number=d.get("figure_number") or d.get("figure_no"),
            source_citation=d.get("source_citation") or d.get("citation"),
            diagram_type=d.get("diagram_type") or d.get("layout"),
            revision=d.get("revision"),
            graph_id=d.get("graph_id"),
            style_id=d.get("style_id"),
            id=d.get("id"),
        )
    if t in ("calculation", "calc", "calculation_block"):
        return CalculationBlock(
            title=d.get("title") or d.get("name"),
            profile=d.get("profile"),
            formula_latex=d.get("formula_latex"),
            formula_code=d.get("formula_code"),
            inputs=list(d.get("inputs") or []),
            outputs=list(d.get("outputs") or []),
            assumptions=list(d.get("assumptions") or []),
            status=str(d.get("status") or "draft"),
            status_label=d.get("status_label"),
            confirmed_by=d.get("confirmed_by"),
            confirmed_at=d.get("confirmed_at"),
            revision=int(d.get("revision") or 1),
            calculation_id=d.get("calculation_id") or d.get("calc_id"),
            disclaimer=d.get("disclaimer"),
            text=d.get("text"),
            material_id=d.get("material_id"),
            section_id=d.get("section_id"),
            binding=d.get("binding") if isinstance(d.get("binding"), dict) else None,
            id=d.get("id"),
        )
    if t in ("material", "material_block"):
        return MaterialBlock(
            title=d.get("title"),
            binding=d.get("binding") if isinstance(d.get("binding"), dict) else None,
            disclaimer=d.get("disclaimer"),
            text=d.get("text"),
            code_compliance_claimed=bool(d.get("code_compliance_claimed")),
            id=d.get("id"),
        )
    return Block(type=t or "unknown", id=d.get("id"))
