from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .blocks import HeroBlock, block_from_dict
from .section import Section


@dataclass
class Document:
    title: str
    document_type: str = "technical"  # product_sheet | manual | report | datasheet
    language: str = "en"
    hero: Optional[HeroBlock] = None
    sections: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    theme: str = "engineering"  # engineering | datasheet | brochure | manual

    @classmethod
    def from_dict(cls, d: dict) -> "Document":
        hero = None
        if d.get("hero"):
            h = d["hero"]
            hero = block_from_dict(h if isinstance(h, dict) else {"type": "hero"})
            if not isinstance(hero, HeroBlock):
                hero = HeroBlock(
                    headline=getattr(h, "headline", "") if not isinstance(h, dict)
                    else h.get("headline") or "",
                )
        sections = []
        for s in d.get("sections") or []:
            sections.append(Section.from_dict(s) if isinstance(s, dict) else s)
        return cls(
            title=d.get("title") or "Document",
            document_type=d.get("document_type") or "technical",
            language=d.get("language") or "en",
            hero=hero if isinstance(hero, HeroBlock) else None,
            sections=sections,
            metadata=dict(d.get("metadata") or {}),
            theme=d.get("theme") or "engineering",
        )
