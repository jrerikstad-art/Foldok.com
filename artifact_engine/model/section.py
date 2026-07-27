from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .blocks import AnyBlock, block_from_dict


@dataclass
class Section:
    id: Optional[str] = None
    title: Optional[str] = None
    blocks: list = field(default_factory=list)
    page_break_before: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "Section":
        blocks = []
        for b in d.get("blocks") or []:
            blocks.append(block_from_dict(b) if isinstance(b, dict) else b)
        return cls(
            id=d.get("id"),
            title=d.get("title"),
            blocks=blocks,
            page_break_before=bool(d.get("page_break_before")),
        )
