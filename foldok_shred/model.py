"""Shred result types — structure and numbers only. No body-text field exists."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Grade = Literal["sample", "ours", "exemplary"]

# What each grade is allowed to turn into proposals.
GRADE_LEARNS: dict[str, tuple[str, ...]] = {
    "sample": (),
    "ours": (),
    "exemplary": ("skeleton", "design", "obligations"),
}


@dataclass
class Skeleton:
    """Section titles and counts — never section bodies."""

    headings: list[tuple[int, str]] = field(default_factory=list)  # (level, title)
    numbering: str = ""  # e.g. "decimal", "none"
    tables: int = 0
    figures: int = 0

    @property
    def section_count(self) -> int:
        return len(self.headings)

    @property
    def depth(self) -> int:
        return max((lvl for lvl, _ in self.headings), default=0)

    def titles(self, level: int | None = None) -> list[str]:
        if level is None:
            return [t for _, t in self.headings]
        return [t for lvl, t in self.headings if lvl == level]

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_count": self.section_count,
            "depth": self.depth,
            "numbering": self.numbering,
            "tables": self.tables,
            "figures": self.figures,
            "titles": [{"level": lvl, "title": t} for lvl, t in self.headings],
        }


@dataclass
class DesignProfile:
    """Page geometry measured from the file — numbers only."""

    page_size: str = ""
    margin_left_pt: float = 0.0
    margin_right_pt: float = 0.0
    margin_top_pt: float = 0.0
    margin_bottom_pt: float = 0.0
    body_size_pt: float = 0.0
    columns: int = 1
    measured_from: str = "structure"
    confidence: float = 0.0

    @property
    def usable(self) -> bool:
        return self.confidence >= 0.4 and bool(self.page_size)

    def to_grid(self) -> dict[str, Any]:
        return {
            "page_size": self.page_size,
            "margins_pt": {
                "left": self.margin_left_pt,
                "right": self.margin_right_pt,
                "top": self.margin_top_pt,
                "bottom": self.margin_bottom_pt,
            },
            "body_size_pt": self.body_size_pt,
            "columns": self.columns,
        }

    def to_dict(self) -> dict[str, Any]:
        d = self.to_grid()
        d.update({
            "measured_from": self.measured_from,
            "confidence": self.confidence,
            "usable": self.usable,
        })
        return d


@dataclass
class ShredProposal:
    """Something the shredder noticed — never applied until the console accepts."""

    kind: str
    title: str
    detail: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "title": self.title,
            "detail": self.detail,
            "payload": self.payload,
            "confidence": self.confidence,
            "source": self.source,
        }


@dataclass
class Shred:
    """What survives after text is dropped. No field can hold body text."""

    source_id: str
    grade: Grade = "sample"
    kind: str = ""
    skeleton: Skeleton = field(default_factory=Skeleton)
    design: DesignProfile = field(default_factory=DesignProfile)
    bytes_in: int = 0
    proposals: list[ShredProposal] = field(default_factory=list)
    obligations: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def learns(self) -> tuple[str, ...]:
        return GRADE_LEARNS.get(self.grade, ())

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "grade": self.grade,
            "kind": self.kind,
            "bytes_in": self.bytes_in,
            "learns": list(self.learns),
            "skeleton": self.skeleton.to_dict(),
            "design": self.design.to_dict(),
            "proposals": [p.to_dict() for p in self.proposals],
            "obligations": self.obligations,
            "notes": list(self.notes),
        }

    def report(self) -> str:
        lines = [
            f"SHRED  {self.source_id}  grade={self.grade}  kind={self.kind or '?'}",
            f"  sections={self.skeleton.section_count}  depth={self.skeleton.depth}  "
            f"bytes={self.bytes_in}",
        ]
        if self.design.usable:
            lines.append(
                f"  design: {self.design.page_size}, body {self.design.body_size_pt:.1f} pt"
            )
        for p in self.proposals:
            lines.append(f"  [{p.kind}] {p.title}")
            if p.detail:
                lines.append(f"         {p.detail}")
        for n in self.notes:
            lines.append(f"  note: {n}")
        return "\n".join(lines)
