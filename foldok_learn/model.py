"""Local learning — the tool gets better at your work, on your machine.

Tier 1 only, deliberately.  Nothing here shares anything with anyone.  That is
not a limitation to be lifted later by loosening a flag: every artefact this
package produces is born ``local_only`` and ``reference_only``, so
``foldok_assets.seal()`` refuses to put it in a pack.  Cross-user sharing, if it
ever happens, has to be built as a separate deliberate act with consent,
sanitising and a licence — not by flipping a boolean in here.

Three rules make learning trustworthy rather than creepy:

**Learn only from confirmed things.**  A draft the user never confirmed is not
evidence of preference; it is evidence that Foldok guessed.  The same
provenance discipline the rest of the product uses decides what counts.

**Never generalise from one example.**  Every lesson carries its evidence count
and a threshold.  One hand-resized image is a hand-resized image; five is a
preference.

**Everything is visible and revertable.**  A tool that silently changes its own
behaviour is worse than one that never learns, because the user cannot tell the
difference between a feature and a fault.  Every lesson lists what it learned,
from how many examples, and can be undone in one call.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal

SCHEMA_VERSION = 1

LessonKind = Literal[
    "layout",        # this role sits at this width in this template
    "resolver",      # this gap kind is usually closed this way
    "symbol",        # these symbols are the ones actually used
    "requirement",   # a clause from a standard the user has licensed
    "section",       # this document type usually contains these sections
    "naming",        # tag and document-number shapes this user uses
]

# How much evidence before a lesson is offered at all.
THRESHOLDS: dict[str, int] = {
    "layout": 3,
    "resolver": 4,
    "symbol": 3,
    "requirement": 1,      # a clause is a fact about a document, not a habit
    "section": 3,
    "naming": 5,
}

Status = Literal["proposed", "active", "rejected", "reverted"]


@dataclass(frozen=True)
class Evidence:
    """One confirmed observation. Content-free: ids, kinds and numbers."""

    source: str                       # document id, file id, session id
    detail: str = ""                  # short, from a fixed vocabulary where possible
    at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"source": self.source}
        if self.detail:
            d["detail"] = self.detail
        if self.at:
            d["at"] = round(self.at, 3)
        return d


@dataclass
class Lesson:
    """Something Foldok noticed about how this person works."""

    id: str
    kind: LessonKind
    subject: str                      # what it is about: "image", "el.board_photo", ...
    prop: str                         # what varies: "span", "resolver", "sections"
    value: Any                        # what it learned
    evidence: list[Evidence] = field(default_factory=list)
    status: Status = "proposed"
    scope: str = "*"                  # template id, document type, or "*"
    rationale: str = ""
    local_only: bool = True           # never negotiable in this package
    created_at: float = field(default_factory=time.time)
    applied_at: float = 0.0

    @property
    def support(self) -> int:
        return len(self.evidence)

    @property
    def threshold(self) -> int:
        return THRESHOLDS.get(self.kind, 3)

    @property
    def ready(self) -> bool:
        return self.support >= self.threshold

    @property
    def active(self) -> bool:
        return self.status == "active"

    def describe(self) -> str:
        base = f"{self.subject}.{self.prop} = {self.value!r}"
        return f"{base} — from {self.support} confirmed example(s)" + (
            f"; {self.rationale}" if self.rationale else ""
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "id": self.id,
            "kind": self.kind,
            "subject": self.subject,
            "prop": self.prop,
            "value": self.value,
            "scope": self.scope,
            "status": self.status,
            "support": self.support,
            "threshold": self.threshold,
            "local_only": True,
            "rationale": self.rationale,
            "evidence": [e.to_dict() for e in self.evidence],
            "created_at": round(self.created_at, 3),
            "applied_at": round(self.applied_at, 3) if self.applied_at else 0,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Lesson":
        return Lesson(
            id=d["id"], kind=d["kind"], subject=d["subject"], prop=d["prop"],
            value=d["value"], scope=d.get("scope", "*"), status=d.get("status", "proposed"),
            rationale=d.get("rationale", ""),
            evidence=[Evidence(**e) for e in d.get("evidence", [])],
            created_at=float(d.get("created_at", 0.0)),
            applied_at=float(d.get("applied_at", 0.0)),
        )


def lesson_id(kind: str, scope: str, subject: str, prop: str) -> str:
    """Content-addressed, so the same observation always lands on the same lesson."""
    import hashlib

    raw = f"{kind}|{scope}|{subject}|{prop}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:12]


# ----------------------------------------------------------------------
@dataclass
class ClauseFinding:
    """One obligation spotted in a standard the user has uploaded.

    Note what is stored: the clause identifier, the kind of obligation, and how
    often it repeats. **Not the clause text.** The user may hold a licence to
    read the standard on their machine; that is not a licence for Foldok to keep
    a copy of it, and the difference is exactly the difference between a
    requirement profile and an infringement.
    """

    clause: str                       # "§6-61", "6.1.2", "Annex II(1)(A)"
    obligation: Literal["shall", "should", "may"] = "shall"
    artifact: str = "text"            # measurement | photo | document | signature | text
    per: str = "document"             # document | circuit | machine | cage | ...
    confidence: float = 0.5
    evidence_source: str = ""         # file id, never file name
    quote_length: int = 0             # how long the sentence was — a number, not the text

    @property
    def severity(self) -> str:
        return {"shall": "blocking", "should": "recommended", "may": "optional"}[self.obligation]

    @property
    def evidential(self) -> bool:
        return self.artifact in ("measurement", "photo", "signature")

    def to_dict(self) -> dict[str, Any]:
        return {
            "clause": self.clause,
            "obligation": self.obligation,
            "artifact": self.artifact,
            "per": self.per,
            "severity": self.severity,
            "confidence": round(self.confidence, 2),
            "evidence_source": self.evidence_source,
            "quote_length": self.quote_length,
        }


class SharingRefused(Exception):
    """Something local-only was about to be shared. Tier 1 does not share."""


def assert_local_only(items: Iterable[Any], *, what: str = "operation") -> None:
    """Guard for any future export path.

    This exists so that when someone eventually builds contribution, they hit a
    deliberate wall rather than discovering that Tier 1 output flowed straight
    into it.
    """
    offenders = [
        getattr(i, "id", str(i)) for i in items
        if getattr(i, "local_only", True)
    ]
    if offenders:
        raise SharingRefused(
            f"{len(offenders)} locally-learned item(s) cannot leave this machine in a "
            f"{what}: {', '.join(str(o) for o in offenders[:5])}. "
            "Local learning is derived from the user's own documents and, for standards, "
            "from a copyrighted work they licensed. Sharing needs consent, sanitising and "
            "a licence — build that deliberately, do not route through here."
        )


def to_jsonl(lessons: Iterable[Lesson]) -> str:
    return "\n".join(
        json.dumps(l.to_dict(), ensure_ascii=False, sort_keys=True)
        for l in sorted(lessons, key=lambda x: (x.kind, x.scope, x.subject, x.prop))
    )
