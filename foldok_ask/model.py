"""Minimal data model for question-driven answers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class Question:
    id: str
    text: str
    locale: str = "no"
    source: Literal["user", "suggested", "job_default"] = "user"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "locale": self.locale,
            "source": self.source,
        }


@dataclass
class RetrievalHit:
    chunk_id: str
    score: float
    file_id: str
    path: str = ""
    text: str = ""
    pages: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "score": round(self.score, 4),
            "file_id": self.file_id,
            "path": self.path,
            "text": self.text[:400],
            "pages": self.pages,
        }


@dataclass
class GroundClaim:
    key: str
    value: str
    unit: str = ""
    chunk_id: str = ""
    file_id: str = ""
    quote: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = {"key": self.key, "value": self.value, "chunk_id": self.chunk_id, "file_id": self.file_id}
        if self.unit:
            d["unit"] = self.unit
        if self.quote:
            d["quote"] = self.quote[:240]
        return d


@dataclass
class GroundSet:
    question_id: str
    hits: list[RetrievalHit] = field(default_factory=list)
    claims: list[GroundClaim] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "hits": [h.to_dict() for h in self.hits],
            "claims": [c.to_dict() for c in self.claims],
        }


@dataclass
class Citation:
    span: str
    chunk_id: str
    file_id: str

    def to_dict(self) -> dict[str, Any]:
        return {"span": self.span[:200], "chunk_id": self.chunk_id, "file_id": self.file_id}


@dataclass
class Gap:
    kind: str  # insufficient_coverage | conflict | weak_retrieve
    detail: str
    file_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "detail": self.detail, "file_ids": list(self.file_ids)}


@dataclass
class Answer:
    question_id: str
    question_text: str
    prose: str = ""
    tables: list[dict[str, Any]] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    gaps: list[Gap] = field(default_factory=list)
    grounded: bool = False
    hits: list[RetrievalHit] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "question_text": self.question_text,
            "prose": self.prose,
            "tables": list(self.tables),
            "citations": [c.to_dict() for c in self.citations],
            "gaps": [g.to_dict() for g in self.gaps],
            "grounded": self.grounded,
            "hits": [h.to_dict() for h in self.hits],
        }

    def markdown(self, *, lang: str = "no") -> str:
        parts: list[str] = []
        if self.prose:
            parts.append(self.prose)
        for table in self.tables:
            headers = table.get("headers") or []
            rows = table.get("rows") or []
            if not rows:
                continue
            lines = [
                "| " + " | ".join(str(h) for h in headers) + " |",
                "|" + "|".join("---" for _ in headers) + "|",
            ]
            for row in rows:
                lines.append("| " + " | ".join(str(c) for c in row) + " |")
            title = table.get("title")
            if title:
                parts.append(f"**{title}**")
            parts.append("\n".join(lines))
        if self.citations:
            cite_label = "Kilder" if lang.startswith("no") else "Sources"
            cites = []
            seen = set()
            for c in self.citations:
                if c.file_id in seen:
                    continue
                seen.add(c.file_id)
                cites.append(f"- {c.file_id}")
            parts.append(f"*{cite_label}:*\n" + "\n".join(cites))
        if self.gaps and not self.grounded:
            gap_label = "MANGLER / gap" if lang.startswith("no") else "MISSING / gap"
            for g in self.gaps:
                parts.append(f"**{gap_label}:** {g.detail}")
        elif self.gaps:
            for g in self.gaps:
                parts.append(f"*Gap ({g.kind}):* {g.detail}")
        return "\n\n".join(p for p in parts if p).strip()
