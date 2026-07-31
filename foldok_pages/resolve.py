"""Page addresses — accept how people talk, anchor to something that survives.

"Add a wiring diagram to page 6" is how everyone describes a document, and it is
an unstable address.  Page 6 is a *result* of everything above it: insert the
diagram and what was on page 6 is now on page 7, so the instruction stops meaning
what it meant while you are carrying it out.

Refusing the phrasing would be pedantic.  The fix is to accept it, resolve it to
an anchor that survives reflow, and **say what it resolved to**:

    Page 6 is section '4 Verifikasjon', after the insulation-resistance table.
    Adding the wiring diagram there.

Then the user can see whether it understood them before it acts — the same shape
as everything else here: accept the human phrasing, decide in code, show the
mapping.

The page numbers themselves already exist.  ``foldok_boxes`` stamps ``page`` on
every placed box; nothing ever surfaced it.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal, Mapping, Sequence

AddressKind = Literal["page", "section", "after", "before", "end", "start", "unknown"]


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text.lower()).strip()


PAGE_PATTERNS = (
    re.compile(r"\b(?:p\.?|page|side|s\.)\s*(\d{1,3})\b", re.I),
    re.compile(r"\bpa side (\d{1,3})\b", re.I),
    re.compile(r"\bside nr\.? ?(\d{1,3})\b", re.I),
)
SECTION_PATTERNS = (
    re.compile(r"\b(?:section|seksjon|kapittel|kap\.?|punkt)\s*([\dA-Za-z.]{1,8})\b", re.I),
)
LAST = ("last page", "siste side", "bakerst", "at the end", "til slutt", "pa slutten")
FIRST = ("first page", "forste side", "fremst", "at the front", "i starten")
AFTER = ("after ", "etter ", "under ", "below ")
BEFORE = ("before ", "for ", "foran ", "above ", "over ")


@dataclass
class Block:
    """The minimum the resolver needs to know about a block."""

    id: str
    page: int = 1
    order: int = 0
    section: str = ""
    section_title: str = ""
    label: str = ""
    role: str = "text"

    @property
    def name(self) -> str:
        return self.label or self.id


@dataclass
class Anchor:
    """Where something goes, in terms that survive reflow."""

    after_block: str | None
    before_block: str | None = None
    section: str = ""
    section_title: str = ""
    page_seen: int = 0                  # the page it was on when resolved
    after_label: str = ""               # what a person calls it, not its id
    kind: AddressKind = "unknown"
    confidence: float = 0.0
    note: str = ""

    @property
    def resolved(self) -> bool:
        return bool(self.after_block or self.before_block or self.section)

    def describe(self, what: str = "the figure", lang: str = "no") -> str:
        """The sentence shown before acting. This is the whole point."""
        where = self.section_title or self.section
        if lang == "no":
            if not self.resolved:
                return (
                    f"Jeg fant ikke ut hvor {what} skal. "
                    f"{self.note or 'Si hvilken seksjon, så legger jeg den der.'}"
                )
            parts = []
            if self.page_seen:
                parts.append(f"Side {self.page_seen} er")
                parts.append(f"seksjon «{where}»" if where else "i dokumentet")
            elif where:
                parts.append(f"Seksjon «{where}»")
            line = " ".join(parts)
            if self.after_block:
                line += f", etter {self.after_label or self.after_block}"
            line += f". Legger {what} der."
            if self.page_seen:
                line += (
                    " Sidetallet flytter seg når innholdet endres, så den er festet til "
                    "seksjonen, ikke til siden."
                )
            return line
        if not self.resolved:
            return f"I could not work out where {what} goes. {self.note}".strip()
        parts = []
        if self.page_seen:
            parts.append(f"Page {self.page_seen} is")
            parts.append(f"section '{where}'" if where else "in the document")
        elif where:
            parts.append(f"Section '{where}'")
        line = " ".join(parts)
        if self.after_block:
            line += f", after {self.after_label or self.after_block}"
        line += f". Putting {what} there."
        if self.page_seen:
            line += (
                " Page numbers move when content changes, so it is anchored to the "
                "section rather than the page."
            )
        return line

    def to_dict(self) -> dict[str, Any]:
        return {
            "after_block": self.after_block,
            "after_label": self.after_label,
            "before_block": self.before_block,
            "section": self.section,
            "section_title": self.section_title,
            "page_seen": self.page_seen,
            "kind": self.kind,
            "confidence": round(self.confidence, 2),
            "note": self.note,
        }


class PageIndex:
    """Pages, sections and blocks in one lookup."""

    def __init__(self, blocks: Sequence[Block]) -> None:
        self.blocks = sorted(blocks, key=lambda b: (b.page, b.order))

    @classmethod
    def from_geometry(
        cls,
        geometry: Any,
        blocks: Iterable[Mapping[str, Any]] = (),
    ) -> "PageIndex":
        """Build from a ``foldok_boxes`` Geometry plus block metadata.

        The geometry already knows which page every box landed on — it was
        computed and never shown.
        """
        meta = {str(b.get("id")): b for b in blocks}
        out: list[Block] = []
        for order, placed in enumerate(
            sorted(geometry.boxes, key=lambda b: (b.page, b.y, b.col))
        ):
            info = meta.get(placed.block_id, {})
            out.append(
                Block(
                    id=placed.block_id,
                    page=int(placed.page),
                    order=order,
                    section=str(info.get("section", "")),
                    section_title=str(info.get("section_title", info.get("section", ""))),
                    label=str(info.get("label", "")),
                    role=str(getattr(placed, "role", "text")),
                )
            )
        return cls(out)

    # -- lookups ---------------------------------------------------------
    @property
    def page_count(self) -> int:
        return max((b.page for b in self.blocks), default=1)

    def on_page(self, page: int) -> list[Block]:
        return [b for b in self.blocks if b.page == page]

    def sections_on(self, page: int) -> list[tuple[str, str]]:
        seen: list[tuple[str, str]] = []
        for b in self.on_page(page):
            key = (b.section, b.section_title)
            if b.section and key not in seen:
                seen.append(key)
        return seen

    def find_section(self, needle: str) -> tuple[str, str] | None:
        n = _fold(needle)
        for b in self.blocks:
            if not b.section:
                continue
            if n == _fold(b.section) or n in _fold(b.section_title):
                return (b.section, b.section_title)
        return None

    def find_block(self, needle: str) -> Block | None:
        n = _fold(needle)
        if not n:
            return None
        for b in self.blocks:
            if n == _fold(b.id) or n == _fold(b.name):
                return b
        for b in self.blocks:
            if n in _fold(b.name) or n in _fold(b.id):
                return b
        return None

    def outline(self, lang: str = "no") -> str:
        """Page numbers, shown. They existed all along."""
        lines: list[str] = []
        for page in range(1, self.page_count + 1):
            sections = self.sections_on(page)
            titles = ", ".join(t or k for k, t in sections) or ("(tom)" if lang == "no" else "(empty)")
            label = "Side" if lang == "no" else "Page"
            lines.append(f"{label} {page}: {titles}")
        return "\n".join(lines)


# ----------------------------------------------------------------------
def resolve(address: str, index: PageIndex) -> Anchor:
    """Turn what the user said into something that survives reflow."""
    q = _fold(address)

    for phrase in AFTER:
        if phrase in q:
            target = q.split(phrase, 1)[1].strip(" .,:;")
            block = index.find_block(target)
            if block is not None:
                return Anchor(
                    after_block=block.id, after_label=block.label, section=block.section,
                    section_title=block.section_title, page_seen=block.page,
                    kind="after", confidence=0.9,
                )

    for phrase in BEFORE:
        if phrase in q and not q.startswith("for "):
            target = q.split(phrase, 1)[1].strip(" .,:;")
            block = index.find_block(target)
            if block is not None:
                return Anchor(
                    after_block=None, before_block=block.id, section=block.section,
                    section_title=block.section_title, page_seen=block.page,
                    kind="before", confidence=0.9,
                )

    for pattern in SECTION_PATTERNS:
        m = pattern.search(address)
        if m:
            found = index.find_section(m.group(1))
            if found:
                key, title = found
                last = [b for b in index.blocks if b.section == key]
                return Anchor(
                    after_block=last[-1].id if last else None,
                    after_label=last[-1].label if last else "",
                    section=key, section_title=title,
                    page_seen=last[-1].page if last else 0,
                    kind="section", confidence=0.85,
                )

    for pattern in PAGE_PATTERNS:
        m = pattern.search(address)
        if m:
            return _from_page(int(m.group(1)), index)

    if any(w in q for w in LAST):
        blocks = index.blocks
        if blocks:
            b = blocks[-1]
            return Anchor(after_block=b.id, after_label=b.label, section=b.section,
                          section_title=b.section_title,
                          page_seen=b.page, kind="end", confidence=0.8)
    if any(w in q for w in FIRST):
        blocks = index.blocks
        if blocks:
            b = blocks[0]
            return Anchor(after_block=None, before_block=b.id, section=b.section,
                          section_title=b.section_title, page_seen=b.page,
                          kind="start", confidence=0.8)

    return Anchor(
        after_block=None, kind="unknown", confidence=0.0,
        note="Si hvilken seksjon eller hvilket avsnitt den skal etter.",
    )


def _from_page(page: int, index: PageIndex) -> Anchor:
    if page < 1 or page > index.page_count:
        return Anchor(
            after_block=None, kind="page", confidence=0.0, page_seen=page,
            note=(
                f"Dokumentet har {index.page_count} side(r) akkurat nå."
                if index.page_count
                else "Dokumentet har ingen sider ennå."
            ),
        )
    blocks = index.on_page(page)
    if not blocks:
        return Anchor(after_block=None, kind="page", page_seen=page, confidence=0.2,
                      note="Den siden er tom.")
    last = blocks[-1]
    return Anchor(
        after_block=last.id,
        after_label=last.label,
        section=last.section,
        section_title=last.section_title,
        page_seen=page,
        kind="page",
        confidence=0.7,
        note="sidetall er ustabile; festet til seksjonen",
    )


def order_pin(anchor: Anchor, index: PageIndex) -> dict[str, Any] | None:
    """The ``foldok_boxes`` order pin this anchor implies."""
    if not anchor.resolved:
        return None
    ids = [b.id for b in index.blocks]
    if anchor.after_block and anchor.after_block in ids:
        return {"after": anchor.after_block, "index": ids.index(anchor.after_block) + 1}
    if anchor.before_block and anchor.before_block in ids:
        return {"before": anchor.before_block, "index": ids.index(anchor.before_block)}
    return None
