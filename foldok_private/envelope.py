"""The envelope — exactly what leaves the machine, shown before it leaves.

This is the part a junior engineer at a large company can actually act on.  Not
a promise in a privacy policy, which they cannot verify and would not read, but
the literal payload, on screen, with a byte count, before anything is sent.  It
is the same move the product already makes with citations: replace a claim with
something inspectable.

The audit log follows the rule already set in ``proxy/ledger.py`` — it records
what *kind* of thing happened and never the content:

    purpose, model, bytes, entity token count, hash, timestamp

Never the masked text, never the real values.  A log you would be uncomfortable
handing to the customer's IT department is the wrong log.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .vault import Entity, MaskResult

# The four purposes the engine actually calls the model for. Everything else in
# Foldok — indexing structure, gaps, layout, diagrams, tables, pagination,
# export — runs with the network off.
PURPOSES: tuple[str, ...] = (
    "index_file",             # extract facts from one chunk
    "partition_facts",        # group facts into sections
    "generate_section_prose", # write sentences from confirmed facts
    "gap_fill_code",          # propose how to close a gap
)


@dataclass
class ImageRef:
    """An image the caller wants to send.  Images cannot be masked — a nameplate
    photo carries the serial number, the client logo and often a face — so they
    are refused unless the user opts in per file."""

    path: str
    bytes: int = 0
    approved: bool = False
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "bytes": self.bytes, "approved": self.approved}


@dataclass
class Envelope:
    purpose: str
    text: str                                   # already masked
    model: str = ""
    entities: tuple[Entity, ...] = ()
    images: tuple[ImageRef, ...] = ()
    replacements: int = 0
    created_at: float = field(default_factory=time.time)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def bytes(self) -> int:
        return len(self.text.encode("utf-8")) + sum(i.bytes for i in self.images if i.approved)

    @property
    def tokens_used(self) -> tuple[str, ...]:
        return tuple(sorted({e.token for e in self.entities}))

    @property
    def digest(self) -> str:
        blob = f"{self.purpose}|{self.text}|{','.join(i.path for i in self.images)}"
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]

    # -- the panel --------------------------------------------------------
    def preview(self, width: int = 78, full: bool = False) -> str:
        """What the user reads before pressing send."""
        lines = [
            "WHAT LEAVES THIS MACHINE",
            f"  purpose   {self.purpose}",
            f"  model     {self.model or '(not set)'}",
            f"  size      {self.bytes} bytes",
            f"  masked    {self.replacements} value(s) replaced by "
            f"{len(self.tokens_used)} token(s): {', '.join(self.tokens_used) or 'none'}",
        ]
        if self.images:
            approved = [i for i in self.images if i.approved]
            lines.append(
                f"  images    {len(approved)} of {len(self.images)} approved"
                + (" — images cannot be masked" if self.images else "")
            )
        lines.append("")
        body = self.text if full else _clip(self.text, 1200)
        lines.append("-" * width)
        lines.extend(_wrap(body, width))
        lines.append("-" * width)
        return "\n".join(lines)

    def to_dict(self, *, include_text: bool = False) -> dict[str, Any]:
        d: dict[str, Any] = {
            "purpose": self.purpose,
            "model": self.model,
            "bytes": self.bytes,
            "entity_count": len(self.tokens_used),
            "replacements": self.replacements,
            "images": len([i for i in self.images if i.approved]),
            "digest": self.digest,
            "created_at": round(self.created_at, 3),
        }
        if include_text:
            d["text"] = self.text          # only for the on-screen panel, never the log
        if self.meta:
            d["meta"] = dict(sorted(self.meta.items()))
        return d

    @staticmethod
    def build(
        purpose: str,
        masked: MaskResult,
        *,
        model: str = "",
        images: Iterable[ImageRef] = (),
        meta: dict[str, Any] | None = None,
        clock=time.time,
    ) -> "Envelope":
        return Envelope(
            purpose=purpose,
            text=masked.text,
            model=model,
            entities=masked.entities,
            images=tuple(images),
            replacements=masked.replacements,
            created_at=clock(),
            meta=meta or {},
        )


@dataclass
class Record:
    """One line of the audit log.  Content-free by construction."""

    purpose: str
    model: str
    bytes: int
    entity_count: int
    digest: str
    outcome: str                   # sent | refused | failed
    reason: str = ""
    at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = {
            "at": round(self.at, 3),
            "purpose": self.purpose,
            "model": self.model,
            "bytes": self.bytes,
            "entity_count": self.entity_count,
            "digest": self.digest,
            "outcome": self.outcome,
        }
        if self.reason:
            d["reason"] = self.reason
        return d


class AuditLog:
    """Append-only, local, content-free."""

    def __init__(self, path: str | Path | None = None, clock=time.time) -> None:
        self.path = Path(path) if path else None
        self._records: list[Record] = []
        self._clock = clock

    def add(self, envelope: Envelope, outcome: str, reason: str = "") -> Record:
        rec = Record(
            purpose=envelope.purpose,
            model=envelope.model,
            bytes=envelope.bytes,
            entity_count=len(envelope.tokens_used),
            digest=envelope.digest,
            outcome=outcome,
            reason=reason,
            at=self._clock(),
        )
        self._records.append(rec)
        if self.path:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")
        return rec

    def records(self) -> list[Record]:
        return list(self._records)

    def totals(self) -> dict[str, Any]:
        sent = [r for r in self._records if r.outcome == "sent"]
        return {
            "calls": len(self._records),
            "sent": len(sent),
            "refused": len([r for r in self._records if r.outcome == "refused"]),
            "bytes_sent": sum(r.bytes for r in sent),
            "by_purpose": {
                p: len([r for r in sent if r.purpose == p])
                for p in sorted({r.purpose for r in sent})
            },
        }

    def report(self) -> str:
        t = self.totals()
        lines = [
            f"{t['sent']} call(s) sent, {t['refused']} refused, {t['bytes_sent']} bytes total",
        ]
        for purpose, n in t["by_purpose"].items():
            lines.append(f"  {n:>3}  {purpose}")
        return "\n".join(lines)


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n… ({len(text) - limit} more characters)"


def _wrap(text: str, width: int) -> list[str]:
    out: list[str] = []
    for para in text.splitlines():
        if len(para) <= width:
            out.append(para)
            continue
        line = ""
        for word in para.split(" "):
            if len(line) + len(word) + 1 > width:
                out.append(line)
                line = word
            else:
                line = f"{line} {word}".strip()
        if line:
            out.append(line)
    return out
