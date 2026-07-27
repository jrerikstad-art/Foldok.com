"""LayoutTree — the universal publishing contract.

RULE: No renderer may inspect Document, Section, or Block models for layout.
Renderers receive only a LayoutTree: final geometry + fully resolved styles.

Pipeline:
  Document AST → Composition → Measurement → ConstraintSolver → LayoutTree → Renderer

See artifact_engine/PUBLISHING.md and ARCHITECTURE.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator, List, Optional

from artifact_engine.design_system import DesignSystem
from artifact_engine.layout.pagination import LayoutResult


# ── Resolved styles (no DesignSystem tokens left) ───────────────────────────


@dataclass
class BackgroundStyle:
    color: str = "#FFFFFF"
    image_uri: Optional[str] = None


@dataclass
class RegionStyle:
    background: str = "transparent"
    padding_pt: float = 0.0
    border_color: str = ""
    border_width_pt: float = 0.0


@dataclass
class ContainerStyle:
    background: str = "transparent"
    gap_pt: float = 0.0
    padding_pt: float = 0.0


@dataclass
class ComponentStyle:
    """Fully resolved paint hints — renderers must not look up tokens."""
    font_family: str = ""
    font_size_pt: float = 10.0
    font_weight: int = 400
    color: str = "#16181D"
    line_height: float = 1.4
    background: str = "transparent"
    text_align: str = "left"


# ── Geometric tree ───────────────────────────────────────────────────────────


@dataclass
class ComponentLayout:
    """Leaf paint unit — measured, placed, content resolved."""
    id: str
    type: str                       # heading | paragraph | table | image | …
    x: float
    y: float
    width: float
    height: float
    content: Any                    # prepared content (today: Block instance)
    style: ComponentStyle = field(default_factory=ComponentStyle)
    z_index: int = 0
    page_number: int = 0

    # Legacy alias used by older painters / TOC fill
    @property
    def block(self) -> Any:
        return self.content


@dataclass
class ContainerLayout:
    id: str
    x: float                        # relative to region
    y: float
    width: float
    height: float
    components: List[ComponentLayout] = field(default_factory=list)
    style: ContainerStyle = field(default_factory=ContainerStyle)


@dataclass
class RegionLayout:
    """Page region: hero | main | sidebar | footer | …"""
    id: str
    role: str                       # hero | main | sidebar | footer | running
    x: float
    y: float
    width: float
    height: float
    containers: List[ContainerLayout] = field(default_factory=list)
    style: RegionStyle = field(default_factory=RegionStyle)


@dataclass
class PageLayout:
    width: float                    # points
    height: float
    page_number: int                # 0-based
    regions: List[RegionLayout] = field(default_factory=list)
    background: Optional[BackgroundStyle] = None
    header: Optional[str] = None
    footer: Optional[str] = None

    # ── Compatibility with LayoutPage (index / nodes) ────────────────────

    @property
    def index(self) -> int:
        return self.page_number

    @index.setter
    def index(self, value: int) -> None:
        self.page_number = int(value)

    @property
    def nodes(self) -> List["LayoutNode"]:
        """Flattened absolute components — legacy paint / TOC helpers."""
        out: list[LayoutNode] = []
        for region in self.regions:
            for container in region.containers:
                for comp in container.components:
                    out.append(LayoutNode.from_component(
                        comp,
                        origin_x=region.x + container.x,
                        origin_y=region.y + container.y,
                    ))
        return out

    def iter_components(self) -> Iterator[tuple[RegionLayout, ContainerLayout, ComponentLayout]]:
        for region in self.regions:
            for container in region.containers:
                for comp in container.components:
                    yield region, container, comp


# Legacy names kept as aliases so existing imports keep working
LayoutPage = PageLayout


@dataclass
class LayoutNode:
    """Flattened absolute node (compat). Prefer ComponentLayout in new code."""
    block: Any
    x: float
    y: float
    width: float
    height: float
    page: int = 0
    z_index: int = 0
    id: str = ""
    type: str = ""
    style: ComponentStyle = field(default_factory=ComponentStyle)

    @classmethod
    def from_component(
        cls,
        comp: ComponentLayout,
        *,
        origin_x: float = 0.0,
        origin_y: float = 0.0,
    ) -> "LayoutNode":
        return cls(
            block=comp.content,
            x=origin_x + comp.x,
            y=origin_y + comp.y,
            width=comp.width,
            height=comp.height,
            page=comp.page_number,
            z_index=comp.z_index,
            id=comp.id,
            type=comp.type,
            style=comp.style,
        )


@dataclass
class LayoutTree:
    """
    Final print-ready structure — THE ONLY INPUT renderers may consume.

    No flow, no CSS layout decisions, no unresolved DesignSystem tokens
    on component geometry (styles on ComponentLayout are resolved).
    """
    pages: List[PageLayout]
    design: DesignSystem
    title: str = ""
    document_type: str = "technical"
    language: str = "en"
    contract_version: str = "1.0"

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def iter_components(self) -> Iterator[tuple[PageLayout, RegionLayout, ContainerLayout, ComponentLayout]]:
        for page in self.pages:
            for region, container, comp in page.iter_components():
                yield page, region, container, comp


def _block_type_name(block: Any) -> str:
    if block is None:
        return "empty"
    t = getattr(block, "type", None) or getattr(block, "block_type", None)
    if t:
        return str(t)
    return type(block).__name__.replace("Block", "").lower() or "block"


def _resolve_component_style(design: DesignSystem, block: Any) -> ComponentStyle:
    """Bake DesignSystem tokens into a ComponentStyle (no lookups left for paint)."""
    family = getattr(design, "font_sans", "") or ""
    size = float(getattr(design, "body", 10.0) or 10.0)
    weight = 400
    color = getattr(design, "text", "#111827") or "#111827"
    btype = _block_type_name(block)
    if btype in ("heading", "h1", "h2", "h3") or "Heading" in type(block).__name__:
        level = int(getattr(block, "level", 2) or 2)
        if level <= 1:
            size = float(getattr(design, "h1", 18.0) or 18.0)
            weight = 800
        elif level == 2:
            size = float(getattr(design, "h2", 14.0) or 14.0)
            weight = 700
        else:
            size = float(getattr(design, "h3", 12.0) or 12.0)
            weight = 700
    elif btype in ("footer", "caption"):
        size = float(getattr(design, "footer", 8.0) or 8.0)
        color = getattr(design, "muted", color)
    return ComponentStyle(
        font_family=str(family),
        font_size_pt=size,
        font_weight=weight,
        color=str(color),
        line_height=1.4,
        background="transparent",
        text_align="left",
    )


def layout_result_to_tree(
    result: LayoutResult,
    design: DesignSystem,
    *,
    title: str = "",
    document_type: str = "technical",
    language: str = "en",
    metadata: dict | None = None,
) -> LayoutTree:
    """Bridge placement LayoutResult → region-based LayoutTree contract."""
    meta = metadata or {}
    doc_no = meta.get("document_no") or meta.get("doc_no") or ""
    revision = meta.get("revision") or meta.get("rev") or ""
    company = meta.get("company") or meta.get("manufacturer") or ""
    export_date = meta.get("export_date") or meta.get("date") or ""
    pages: list[PageLayout] = []
    total = max(1, len(result.pages or []))
    margin = float(getattr(design, "margin", 48.0) or 48.0)
    pw = float(design.page_width)
    ph = float(design.page_height)

    for page in result.pages:
        components: list[ComponentLayout] = []
        for i, pb in enumerate(page.blocks or []):
            block = pb.block
            # Coordinates from placement are already page-absolute;
            # store relative to the main content region (margin origin).
            components.append(ComponentLayout(
                id=f"p{page.index}-c{i}",
                type=_block_type_name(block),
                x=float(pb.x) - margin,
                y=float(pb.y) - margin,
                width=float(pb.width),
                height=float(pb.height),
                content=block,
                style=_resolve_component_style(design, block),
                page_number=int(pb.page_index),
            ))

        content_w = max(0.0, pw - 2 * margin)
        content_h = max(0.0, ph - 2 * margin)
        main_container = ContainerLayout(
            id=f"p{page.index}-main-flow",
            x=0.0,
            y=0.0,
            width=content_w,
            height=content_h,
            components=components,
            style=ContainerStyle(gap_pt=float(getattr(design, "space_sm", 8.0) or 8.0)),
        )
        main_region = RegionLayout(
            id=f"p{page.index}-main",
            role="main",
            x=margin,
            y=margin,
            width=content_w,
            height=content_h,
            containers=[main_container],
            style=RegionStyle(),
        )

        n = page.index + 1
        header_bits = [b for b in (doc_no, revision, title) if b]
        header = " · ".join(header_bits) if header_bits else title
        footer_bits = [
            f"Side {n} av {total}" if language != "en" else f"Page {n} of {total}",
        ]
        if company:
            footer_bits.append(company)
        if export_date:
            footer_bits.append(str(export_date))

        pages.append(PageLayout(
            width=pw,
            height=ph,
            page_number=page.index,
            regions=[main_region],
            background=BackgroundStyle(color=str(getattr(design, "background", "#FFFFFF") or "#FFFFFF")),
            header=header,
            footer=" · ".join(footer_bits),
        ))

    if not pages:
        pages.append(PageLayout(
            width=pw,
            height=ph,
            page_number=0,
            regions=[RegionLayout(
                id="p0-main",
                role="main",
                x=margin,
                y=margin,
                width=max(0.0, pw - 2 * margin),
                height=max(0.0, ph - 2 * margin),
                containers=[ContainerLayout(
                    id="p0-main-flow",
                    x=0.0, y=0.0,
                    width=max(0.0, pw - 2 * margin),
                    height=max(0.0, ph - 2 * margin),
                )],
            )],
            background=BackgroundStyle(color=str(getattr(design, "background", "#FFFFFF") or "#FFFFFF")),
            header=title,
            footer="Side 1 av 1" if language != "en" else "Page 1 of 1",
        ))

    tree = LayoutTree(
        pages=pages,
        design=design,
        title=title,
        document_type=document_type,
        language=language,
        contract_version="1.0",
    )
    apply_toc_page_numbers(tree)
    return tree


def apply_toc_page_numbers(tree: LayoutTree) -> LayoutTree:
    """Fill TocEntry.page_hint from HeadingBlock page placements (0 tokens)."""
    from artifact_engine.model.blocks import HeadingBlock, TableOfContentsBlock, TocEntry

    title_to_page: dict[str, int] = {}
    for page, _region, _container, comp in tree.iter_components():
        b = comp.content
        if isinstance(b, HeadingBlock) and b.text:
            title_to_page[b.text.strip()] = page.page_number + 1
    for _page, _region, _container, comp in tree.iter_components():
        b = comp.content
        if not isinstance(b, TableOfContentsBlock):
            continue
        new_entries = []
        for e in b.entries or []:
            pg = title_to_page.get((e.title or "").strip())
            new_entries.append(TocEntry(
                title=e.title,
                level=e.level,
                page_hint=str(pg) if pg else e.page_hint,
            ))
        b.entries = new_entries
    return tree
