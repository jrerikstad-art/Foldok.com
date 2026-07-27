"""Index model.

The symptom "I uploaded files, they were indexed, the agent didn't see them" is
almost never one bug.  It is six, and they need to be distinguishable:

    extracted?  chunked?  embedded?  written?  visible?  retrieved?

So every document carries an explicit ``status`` and, when it failed, the reason.
A pipeline that reports "indexed: ok" after producing zero chunks is the single
most common cause of this complaint, and it is a lie the model here cannot tell:
zero chunks is ``empty``, not ``indexed``.

``seq`` is the other load-bearing field.  It is a monotonic write counter, and it
is what makes "what is new since I last looked" an exact question with an exact
answer, rather than a similarity search — see index.py.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal

SCHEMA_VERSION = 1

Status = Literal["indexed", "empty", "failed", "unsupported", "tombstoned"]


@dataclass
class SourceDoc:
    doc_id: str                       # stable across edits; identity is the path
    path: str
    title: str = ""
    content_hash: str = ""            # changes when the file changes
    bytes: int = 0
    mtime: float = 0.0
    version: int = 1
    status: Status = "indexed"
    error: str = ""
    chunk_count: int = 0
    ingested_at: float = 0.0
    seq: int = 0                      # monotonic; the recency axis
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def usable(self) -> bool:
        return self.status == "indexed" and self.chunk_count > 0

    def to_dict(self) -> dict[str, Any]:
        d = {
            "doc_id": self.doc_id,
            "path": self.path,
            "title": self.title,
            "content_hash": self.content_hash,
            "bytes": self.bytes,
            "mtime": round(self.mtime, 3),
            "version": self.version,
            "status": self.status,
            "chunk_count": self.chunk_count,
            "ingested_at": round(self.ingested_at, 3),
            "seq": self.seq,
        }
        if self.error:
            d["error"] = self.error
        if self.meta:
            d["meta"] = dict(sorted(self.meta.items()))
        return d

    def __str__(self) -> str:
        head = f"{self.path} [{self.status}, {self.chunk_count} chunks, seq {self.seq}]"
        return f"{head} — {self.error}" if self.error else head


@dataclass
class Chunk:
    chunk_id: str                     # "{doc_id}@v{version}#{ordinal}"
    doc_id: str
    ordinal: int
    text: str
    heading: str = ""
    start: int = 0
    end: int = 0
    seq: int = 0

    def citation(self, doc: SourceDoc | None = None) -> str:
        """What a retrieved fact must carry with it into a document."""
        where = doc.path if doc else self.doc_id
        return f"{where}#chunk={self.ordinal}" + (f" ({self.heading})" if self.heading else "")


@dataclass
class Hit:
    chunk: Chunk
    doc: SourceDoc
    score: float
    channel: str = "hybrid"           # lexical | semantic | hybrid | recency
    ranks: dict[str, int] = field(default_factory=dict)

    @property
    def citation(self) -> str:
        return self.chunk.citation(self.doc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk.chunk_id,
            "path": self.doc.path,
            "ordinal": self.chunk.ordinal,
            "heading": self.chunk.heading,
            "score": round(self.score, 6),
            "channel": self.channel,
            "ranks": dict(sorted(self.ranks.items())),
            "citation": self.citation,
            "text": self.chunk.text,
        }


@dataclass
class IngestResult:
    doc: SourceDoc
    action: Literal["created", "updated", "unchanged", "skipped", "failed", "deleted"]
    chunks: int = 0
    embedded: int = 0
    cached: int = 0
    detail: str = ""

    def __str__(self) -> str:
        return f"{self.action}: {self.doc.path} ({self.chunks} chunks)" + (
            f" — {self.detail}" if self.detail else ""
        )


@dataclass
class Drift:
    """One disagreement between the folder and the index."""

    code: Literal["not_indexed", "stale", "orphaned", "failed", "empty", "unsupported"]
    path: str
    detail: str = ""
    fix: str = ""

    def __str__(self) -> str:
        return f"[{self.code}] {self.path}" + (f" — {self.detail}" if self.detail else "")


@dataclass
class ReconcileReport:
    root: str
    scanned: int = 0
    in_index: int = 0
    drift: list[Drift] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.drift

    def of(self, code: str) -> list[Drift]:
        return [d for d in self.drift if d.code == code]

    def summary(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for d in self.drift:
            out[d.code] = out.get(d.code, 0) + 1
        return dict(sorted(out.items()))

    def __str__(self) -> str:
        head = (
            f"{self.root}: {self.scanned} file(s) on disk, {self.in_index} in the index"
        )
        if not self.drift:
            return head + " — no drift"
        lines = [head, f"drift: {self.summary()}"]
        lines += [f"  {d}" for d in self.drift[:50]]
        if len(self.drift) > 50:
            lines.append(f"  ... and {len(self.drift) - 50} more")
        return "\n".join(lines)


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""
    fix: str = ""

    def __str__(self) -> str:
        mark = "PASS" if self.ok else "FAIL"
        line = f"[{mark}] {self.name}" + (f": {self.detail}" if self.detail else "")
        return line + (f"\n       fix: {self.fix}" if (self.fix and not self.ok) else "")


@dataclass
class Diagnosis:
    checks: list[Check] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks)

    @property
    def failures(self) -> list[Check]:
        return [c for c in self.checks if not c.ok]

    def add(self, name: str, ok: bool, detail: str = "", fix: str = "") -> Check:
        c = Check(name, ok, detail, fix)
        self.checks.append(c)
        return c

    def __str__(self) -> str:
        head = "INDEX OK" if self.ok else f"INDEX HAS {len(self.failures)} PROBLEM(S)"
        body = "\n".join(str(c) for c in self.checks)
        stats = json.dumps(self.stats, indent=2, sort_keys=True)
        return f"{head}\n{body}\n\nstats:\n{stats}"
