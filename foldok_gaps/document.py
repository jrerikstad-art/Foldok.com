"""The document — what actually exists, as opposed to what is required.

A gap is the difference between the two, so this file has to be honest about
one thing in particular: an artifact existing is not the same as an artifact
being *done*.  Three states matter and they are all different:

    empty        a form or capture task was created, no data in it yet
    unconfirmed  a model drafted it and no human has agreed
    confirmed    a person put their name to it

Only the third resolves a gap in compliance mode.  This is the same provenance
rule the diagram engine uses, applied to the whole document, so there is one
concept to teach and one place to break.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Literal

from .requirements import ArtifactKind

Source = Literal["user", "ai", "import", "engine"]


@dataclass(frozen=True)
class Subject:
    """A thing requirements repeat over: a circuit, a machine, a room, a cage."""

    kind: str
    id: str
    label: str = ""

    def key(self) -> str:
        return f"{self.kind}:{self.id}"

    def to_dict(self) -> dict[str, str]:
        d = {"kind": self.kind, "id": self.id}
        if self.label:
            d["label"] = self.label
        return d


DOCUMENT_SUBJECT = "document"


@dataclass
class Provenance:
    source: Source = "user"
    ref: str | None = None                 # "BOM.xlsx#row=14", "photo_0031.jpg"
    confirmed_by: str | None = None
    confirmed_at: float | None = None
    note: str | None = None

    @property
    def confirmed(self) -> bool:
        return bool(self.confirmed_by)

    def confirm(self, by: str, clock=time.time) -> None:
        self.confirmed_by = by
        self.confirmed_at = clock()

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"source": self.source}
        for k in ("ref", "confirmed_by", "note"):
            v = getattr(self, k)
            if v:
                d[k] = v
        if self.confirmed_at:
            d["confirmed_at"] = round(self.confirmed_at, 3)
        return d


@dataclass
class Artifact:
    id: str
    kind: ArtifactKind
    title: str = ""
    body: str | None = None                # inline text, or SVG for a diagram
    path: str | None = None                # external file
    data: dict[str, Any] = field(default_factory=dict)   # form values, table rows
    pending_fields: tuple[str, ...] = ()   # fields still to fill in
    instruction: str = ""                  # what the person must do, if pending
    produced_by: str = ""                  # resolver id
    provenance: Provenance = field(default_factory=Provenance)

    @property
    def empty(self) -> bool:
        if self.pending_fields:
            return True
        if self.kind in ("text", "diagram"):
            return not (self.body or self.path)
        if self.kind in ("photo", "file"):
            return not self.path
        if self.kind in ("measurement", "table"):
            return not (self.data or self.path)
        if self.kind == "signature":
            return not self.provenance.confirmed
        return False

    @property
    def needs_confirmation(self) -> bool:
        return self.provenance.source == "ai" and not self.provenance.confirmed

    def fill(self, values: dict[str, Any], *, by: str | None = None) -> None:
        self.data.update(values)
        self.pending_fields = tuple(f for f in self.pending_fields if f not in values)
        if by:
            self.provenance.source = "user"
            self.provenance.confirm(by)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"id": self.id, "kind": self.kind}
        for k in ("title", "body", "path", "instruction", "produced_by"):
            v = getattr(self, k)
            if v:
                d[k] = v
        if self.data:
            d["data"] = dict(sorted(self.data.items()))
        if self.pending_fields:
            d["pending_fields"] = list(self.pending_fields)
        d["provenance"] = self.provenance.to_dict()
        return d


@dataclass
class Entry:
    """A requirement instance that has something against it."""

    requirement_key: str
    subject: Subject
    artifact: Artifact | None = None
    not_applicable: bool = False
    reason: str = ""                       # required when not_applicable
    signed_by: str = ""                    # required when not_applicable
    deferred: bool = False                 # "not now" — build mode
    note: str = ""

    def key(self) -> str:
        return f"{self.requirement_key}@{self.subject.key()}"

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "requirement_key": self.requirement_key,
            "subject": self.subject.to_dict(),
        }
        if self.artifact:
            d["artifact"] = self.artifact.to_dict()
        if self.not_applicable:
            d["not_applicable"] = True
            d["reason"] = self.reason
            d["signed_by"] = self.signed_by
        if self.deferred:
            d["deferred"] = True
        if self.note:
            d["note"] = self.note
        return d


@dataclass
class Document:
    id: str
    title: str = ""
    segment: str = "general"
    jurisdiction: str | None = None
    facts: dict[str, Any] = field(default_factory=dict)
    subjects: list[Subject] = field(default_factory=list)
    entries: list[Entry] = field(default_factory=list)
    pack_id: str | None = None
    mode: str = "build"                    # see policy.py
    schema_version: int = 1

    # -- lookup ---------------------------------------------------------
    def subjects_of(self, kind: str) -> list[Subject]:
        if kind == DOCUMENT_SUBJECT:
            return [Subject(DOCUMENT_SUBJECT, self.id, self.title)]
        return sorted(
            [s for s in self.subjects if s.kind == kind], key=lambda s: (s.id, s.kind)
        )

    def entry(self, requirement_key: str, subject: Subject) -> Entry | None:
        want = f"{requirement_key}@{subject.key()}"
        for e in self.entries:
            if e.key() == want:
                return e
        return None

    def put(self, entry: Entry) -> Entry:
        existing = self.entry(entry.requirement_key, entry.subject)
        if existing is not None:
            self.entries.remove(existing)
        self.entries.append(entry)
        return entry

    def artifact(self, artifact_id: str) -> Artifact | None:
        for e in self.entries:
            if e.artifact and e.artifact.id == artifact_id:
                return e.artifact
        return None

    def artifacts(self) -> list[Artifact]:
        return [e.artifact for e in self.sorted_entries() if e.artifact]

    def sorted_entries(self) -> list[Entry]:
        return sorted(self.entries, key=lambda e: e.key())

    def add_subject(self, kind: str, sid: str, label: str = "") -> Subject:
        s = Subject(kind, sid, label)
        if s not in self.subjects:
            self.subjects.append(s)
        return s

    # -- serialisation --------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "title": self.title,
            "segment": self.segment,
            "jurisdiction": self.jurisdiction,
            "pack_id": self.pack_id,
            "mode": self.mode,
            "facts": dict(sorted(self.facts.items())),
            "subjects": [s.to_dict() for s in sorted(self.subjects, key=lambda s: s.key())],
            "entries": [e.to_dict() for e in self.sorted_entries()],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Document":
        doc = Document(
            id=d["id"],
            title=d.get("title", ""),
            segment=d.get("segment", "general"),
            jurisdiction=d.get("jurisdiction"),
            facts=dict(d.get("facts", {})),
            subjects=[Subject(**s) for s in d.get("subjects", [])],
            pack_id=d.get("pack_id"),
            mode=d.get("mode", "build"),
        )
        for e in d.get("entries", []):
            art = None
            if e.get("artifact"):
                a = e["artifact"]
                art = Artifact(
                    id=a["id"],
                    kind=a["kind"],
                    title=a.get("title", ""),
                    body=a.get("body"),
                    path=a.get("path"),
                    data=dict(a.get("data", {})),
                    pending_fields=tuple(a.get("pending_fields", ())),
                    instruction=a.get("instruction", ""),
                    produced_by=a.get("produced_by", ""),
                    provenance=Provenance(**a.get("provenance", {"source": "user"})),
                )
            doc.entries.append(
                Entry(
                    requirement_key=e["requirement_key"],
                    subject=Subject(**e["subject"]),
                    artifact=art,
                    not_applicable=bool(e.get("not_applicable", False)),
                    reason=e.get("reason", ""),
                    signed_by=e.get("signed_by", ""),
                    deferred=bool(e.get("deferred", False)),
                    note=e.get("note", ""),
                )
            )
        return doc
