"""Gaps — required minus satisfied.

Two design rules, both learned from what breaks in practice:

**A gap is an object, not a rendered word.**  You cannot click, assign, batch,
count or prove the resolution of the string "mangler".

**Identity is a hash of (pack, requirement, subject), never a list index.**  If
gaps are numbered by position, resolving number 7 renumbers 8 to 30 and every
link, assignment and audit reference goes stale.

Evaluation is a pure function of (document, pack).  Nothing about the user's
mode enters here — that lives in policy.py.  The consequence is the useful one:
somebody can build in prototype mode for six months and then attach a
compliance pack, and the full gap list appears retroactively over work already
done.  Compliance becomes a view over the document rather than a decision taken
on day one.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal

from .document import DOCUMENT_SUBJECT, Document, Subject
from .requirements import Requirement, RequirementPack, matches

GapState = Literal["open", "in_progress", "resolved", "not_applicable", "deferred"]

OPEN_STATES: tuple[GapState, ...] = ("open", "in_progress", "deferred")


def gap_id(pack_id: str, requirement_key: str, subject_key: str) -> str:
    raw = f"{pack_id}|{requirement_key}|{subject_key}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:12]


@dataclass
class Gap:
    id: str
    requirement: Requirement
    subject: Subject
    state: GapState = "open"
    detail: str = ""                     # why it is in this state
    artifact_id: str | None = None
    pack_id: str = ""

    @property
    def key(self) -> str:
        return f"{self.requirement.key}@{self.subject.key()}"

    @property
    def title(self) -> str:
        if self.subject.kind == DOCUMENT_SUBJECT:
            return self.requirement.title
        label = self.subject.label or self.subject.id
        return f"{self.requirement.title} — {label}"

    @property
    def evidential(self) -> bool:
        return self.requirement.evidence == "evidential"

    @property
    def open(self) -> bool:
        return self.state in OPEN_STATES

    def to_dict(self) -> dict[str, Any]:
        d = {
            "id": self.id,
            "requirement_key": self.requirement.key,
            "subject": self.subject.to_dict(),
            "section": self.requirement.section,
            "kind": self.requirement.kind,
            "evidence": self.requirement.evidence,
            "severity": self.requirement.severity,
            "state": self.state,
            "title": self.title,
        }
        if self.requirement.authority:
            d["authority"] = self.requirement.authority
        if self.detail:
            d["detail"] = self.detail
        if self.artifact_id:
            d["artifact_id"] = self.artifact_id
        return d


@dataclass
class Notice:
    """Something wrong with the *setup*, not with the document's content."""

    code: str
    message: str
    fix: str = ""

    def __str__(self) -> str:
        return f"{self.code}: {self.message}" + (f" — fix: {self.fix}" if self.fix else "")


@dataclass
class Batch:
    """The same requirement open across several subjects — resolvable in one go."""

    requirement: Requirement
    gaps: list[Gap]

    @property
    def size(self) -> int:
        return len(self.gaps)


@dataclass
class GapSet:
    gaps: list[Gap] = field(default_factory=list)
    notices: list[Notice] = field(default_factory=list)
    pack_id: str = ""

    def __iter__(self):
        return iter(self.gaps)

    def __len__(self) -> int:
        return len(self.gaps)

    def get(self, gid: str) -> Gap | None:
        for g in self.gaps:
            if g.id == gid:
                return g
        return None

    # -- filters --------------------------------------------------------
    def open(self) -> list[Gap]:
        return [g for g in self.gaps if g.open]

    def of_state(self, *states: GapState) -> list[Gap]:
        return [g for g in self.gaps if g.state in states]

    def of_kind(self, kind: str) -> list[Gap]:
        return [g for g in self.gaps if g.requirement.kind == kind]

    def of_section(self, section: str) -> list[Gap]:
        return [g for g in self.gaps if g.requirement.section == section]

    def of_subject(self, subject_key: str) -> list[Gap]:
        return [g for g in self.gaps if g.subject.key() == subject_key]

    def evidential(self) -> list[Gap]:
        return [g for g in self.gaps if g.evidential]

    def at_least(self, severity: str) -> list[Gap]:
        from .requirements import SEVERITY_RANK

        floor = SEVERITY_RANK[severity]
        return [g for g in self.gaps if g.requirement.rank() >= floor]

    # -- grouping -------------------------------------------------------
    def by_section(self, pack: RequirementPack | None = None) -> list[tuple[str, list[Gap]]]:
        order = {s.id: s.order for s in (pack.sections if pack else ())}
        buckets: dict[str, list[Gap]] = {}
        for g in self.gaps:
            buckets.setdefault(g.requirement.section, []).append(g)
        return sorted(buckets.items(), key=lambda kv: (order.get(kv[0], 9999), kv[0]))

    def batches(self, *, only_open: bool = True) -> list[Batch]:
        """Group open gaps by requirement.

        Thirty mangler is rarely thirty problems.  It is usually six
        requirements across five circuits, and saying so is the difference
        between a wall of red and one afternoon's work.
        """
        buckets: dict[str, list[Gap]] = {}
        reqs: dict[str, Requirement] = {}
        for g in self.gaps:
            if only_open and not g.open:
                continue
            buckets.setdefault(g.requirement.key, []).append(g)
            reqs[g.requirement.key] = g.requirement
        out = [
            Batch(requirement=reqs[k], gaps=sorted(v, key=lambda g: g.subject.key()))
            for k, v in buckets.items()
        ]
        return sorted(out, key=lambda b: (-b.size, b.requirement.key))

    # -- counts ---------------------------------------------------------
    def summary(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for g in self.gaps:
            counts[g.state] = counts.get(g.state, 0) + 1
        openg = self.open()
        return {
            "total": len(self.gaps),
            "open": len(openg),
            "resolved": counts.get("resolved", 0),
            "not_applicable": counts.get("not_applicable", 0),
            "in_progress": counts.get("in_progress", 0),
            "deferred": counts.get("deferred", 0),
            "open_evidential": len([g for g in openg if g.evidential]),
            "open_blocking": len([g for g in openg if g.requirement.severity == "blocking"]),
            "by_state": dict(sorted(counts.items())),
        }

    @property
    def complete(self) -> bool:
        return not self.open()


# ----------------------------------------------------------------------
def evaluate(document: Document, pack: RequirementPack) -> GapSet:
    """Required minus satisfied.  Pure; safe to call on every keystroke."""
    gaps: list[Gap] = []
    notices: list[Notice] = []

    if pack.applies_when and not matches(document.facts, pack.applies_when):
        notices.append(
            Notice(
                "pack_not_applicable",
                f"pack '{pack.id}' declares conditions this document does not meet",
                "check the project facts, or attach a different pack",
            )
        )

    missing_subject_kinds: dict[str, list[str]] = {}

    for req in pack.sorted_requirements():
        if req.applies_when and not matches(document.facts, req.applies_when):
            continue

        subjects = document.subjects_of(req.per)
        if not subjects and req.per != DOCUMENT_SUBJECT:
            missing_subject_kinds.setdefault(req.per, []).append(req.key)
            continue

        for subject in subjects:
            entry = document.entry(req.key, subject)
            state, detail, artifact_id = _state_of(entry)
            gaps.append(
                Gap(
                    id=gap_id(pack.id, req.key, subject.key()),
                    requirement=req,
                    subject=subject,
                    state=state,
                    detail=detail,
                    artifact_id=artifact_id,
                    pack_id=pack.id,
                )
            )

    for kind, keys in sorted(missing_subject_kinds.items()):
        notices.append(
            Notice(
                "no_subjects_declared",
                f"{len(keys)} requirement(s) repeat per '{kind}' but no {kind} is declared, "
                "so they are silently absent from the gap list",
                f"declare the {kind}s on the document, or the count will look complete when it is not",
            )
        )

    for problem in pack.validate():
        notices.append(Notice("pack_problem", problem, "fix the requirement pack"))

    gaps.sort(key=lambda g: (g.requirement.section, -g.requirement.rank(), g.requirement.key, g.subject.key()))
    return GapSet(gaps=gaps, notices=notices, pack_id=pack.id)


def _state_of(entry) -> tuple[GapState, str, str | None]:
    if entry is None:
        return ("open", "nothing recorded", None)
    if entry.not_applicable:
        if not entry.reason or not entry.signed_by:
            return ("open", "marked not applicable without a reason and a name", None)
        return ("not_applicable", entry.reason, None)
    art = entry.artifact
    if art is None:
        return ("deferred" if entry.deferred else "open", entry.note or "nothing recorded", None)
    if art.empty:
        return (
            "in_progress",
            art.instruction or "created but not filled in",
            art.id,
        )
    if art.needs_confirmation:
        return ("in_progress", "drafted by Foldok, not yet confirmed by a person", art.id)
    return ("resolved", "", art.id)


def diff(before: GapSet, after: GapSet) -> dict[str, list[str]]:
    """What changed between two evaluations.  Stable ids make this trivial."""
    b = {g.id: g.state for g in before.gaps}
    a = {g.id: g.state for g in after.gaps}
    return {
        "appeared": sorted(set(a) - set(b)),
        "disappeared": sorted(set(b) - set(a)),
        "changed": sorted(k for k in set(a) & set(b) if a[k] != b[k]),
    }
