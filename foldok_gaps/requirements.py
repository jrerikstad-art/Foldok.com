"""Requirements — what a document must contain.

The breadth question ("will 21 sections cover marine, machinery, aquaculture,
not just electrical?") is not answered by adding sections.  It is answered by
where the schema lives.

    Sections are labels.  Requirements are the schema.

A section model is a table of contents: an ordering and some headings.  A
requirement pack is the machine-readable statement of what must exist, per
subject, under which conditions, with what authority.  If a new segment needs a
new section, that is a line in a pack.  If a new segment needs new *code*, the
model has failed and the product forks per segment.

So the test for any pack is: could someone who has never seen the Foldok source
write it?  If it needs a code change, the requirement model is too narrow.

Four properties every requirement carries, and each one is load-bearing:

``evidence``
    EXPOSITORY  — describes intent; a model may draft it.
    EVIDENTIAL  — records what was measured, seen, or done on site.  A model may
    build the empty form and nothing else.  This is enforced in resolvers.py,
    not by prompt.

``per``
    The subject the requirement repeats over: the document as a whole, or every
    circuit, machine, room, vessel, cage, weld.  Thirty mangler usually means
    six requirements times five circuits, and that structure is what makes them
    batch-resolvable.

``applies_when``
    Conditions against document facts.  Half of all real gaps are legitimately
    not applicable, and the cheapest way to resolve a gap is for it never to
    have been raised.

``authority``
    The clause the requirement comes from.  A gap that cannot cite why it is a
    gap is an opinion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Evidence = Literal["expository", "evidential"]
Severity = Literal["blocking", "required", "recommended", "optional"]
ArtifactKind = Literal[
    "text", "diagram", "table", "photo", "measurement", "file", "signature", "none"
]

SEVERITY_RANK: dict[str, int] = {
    "optional": 0,
    "recommended": 1,
    "required": 2,
    "blocking": 3,
}


@dataclass(frozen=True)
class Section:
    id: str
    title: str
    order: int = 0
    description: str = ""


# The default spine.  Packs may add sections; nothing in the engine assumes this
# list, which is the point — reconcile it with the live 21-section model, but do
# not let code depend on either.
FOLDOK_SPINE: tuple[Section, ...] = (
    Section("identification", "Identification and revision", 10),
    Section("parties", "Parties and responsibilities", 20),
    Section("scope", "Scope of work", 30),
    Section("basis", "Design basis and assumptions", 40),
    Section("standards", "Standards and references", 50),
    Section("description", "Technical description", 60),
    Section("drawings", "Drawings and schematics", 70),
    Section("components", "Components and materials", 80),
    Section("installation", "Installation record", 90),
    Section("verification", "Verification and testing", 100),
    Section("deviations", "Deviations and non-conformities", 110),
    Section("operation", "Operation and maintenance", 120),
    Section("handover", "Handover and declarations", 130),
)


@dataclass(frozen=True)
class FormField:
    """One field of an evidential form.  The engine creates these empty."""

    key: str
    label: str
    unit: str | None = None
    kind: Literal["number", "text", "choice", "bool", "date"] = "text"
    choices: tuple[str, ...] = ()
    required: bool = True


@dataclass(frozen=True)
class Requirement:
    key: str                                   # stable id, e.g. "nek400.drawings.single_line"
    section: str
    title: str
    kind: ArtifactKind = "text"
    evidence: Evidence = "expository"
    per: str = "document"                      # "document" | subject kind
    severity: Severity = "required"
    authority: str = ""                        # "NEK 400:2022 §8-1"
    description: str = ""
    applies_when: dict[str, Any] = field(default_factory=dict)
    allow_not_applicable: bool = True
    resolvers: tuple[str, ...] = ()             # preference order; empty = registry decides
    fields: tuple[FormField, ...] = ()          # for measurement/table kinds
    capture_prompt: str = ""                    # for photo kinds
    template: str = ""                          # for diagram/text scaffolds
    tags: tuple[str, ...] = ()

    def rank(self) -> int:
        return SEVERITY_RANK[self.severity]

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "key": self.key,
            "section": self.section,
            "title": self.title,
            "kind": self.kind,
            "evidence": self.evidence,
            "per": self.per,
            "severity": self.severity,
        }
        for name in ("authority", "description", "capture_prompt", "template"):
            val = getattr(self, name)
            if val:
                d[name] = val
        if self.applies_when:
            d["applies_when"] = dict(sorted(self.applies_when.items()))
        if not self.allow_not_applicable:
            d["allow_not_applicable"] = False
        if self.resolvers:
            d["resolvers"] = list(self.resolvers)
        if self.fields:
            d["fields"] = [
                {k: v for k, v in vars(f).items() if v not in ((), None, "")} for f in self.fields
            ]
        if self.tags:
            d["tags"] = list(self.tags)
        return d


@dataclass(frozen=True)
class RequirementPack:
    id: str
    title: str
    segment: str                                # "electrical" | "machinery" | "prototype" | ...
    version: str = "1"
    jurisdiction: str | None = None
    standards: tuple[str, ...] = ()
    sections: tuple[Section, ...] = FOLDOK_SPINE
    requirements: tuple[Requirement, ...] = ()
    applies_when: dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def section(self, section_id: str) -> Section | None:
        for s in self.sections:
            if s.id == section_id:
                return s
        return None

    def requirement(self, key: str) -> Requirement | None:
        for r in self.requirements:
            if r.key == key:
                return r
        return None

    def sorted_requirements(self) -> list[Requirement]:
        order = {s.id: s.order for s in self.sections}
        return sorted(
            self.requirements,
            key=lambda r: (order.get(r.section, 9999), -r.rank(), r.key),
        )

    def subject_kinds(self) -> list[str]:
        return sorted({r.per for r in self.requirements if r.per != "document"})

    def validate(self) -> list[str]:
        """Structural problems in the pack itself.  Run this in pack CI."""
        problems: list[str] = []
        seen: set[str] = set()
        section_ids = {s.id for s in self.sections}
        for r in self.requirements:
            if r.key in seen:
                problems.append(f"duplicate requirement key '{r.key}'")
            seen.add(r.key)
            if r.section not in section_ids:
                problems.append(f"'{r.key}' points at unknown section '{r.section}'")
            if r.evidence == "evidential" and r.kind == "text":
                problems.append(
                    f"'{r.key}' is evidential but its artifact kind is free text; "
                    "evidential requirements need a structured kind "
                    "(measurement/photo/table/file) so the record can be checked"
                )
            if r.kind == "measurement" and not r.fields:
                problems.append(f"'{r.key}' is a measurement with no fields to fill in")
            if r.kind == "photo" and not r.capture_prompt:
                problems.append(f"'{r.key}' is a photo requirement with no capture prompt")
            if r.severity == "blocking" and r.allow_not_applicable and not r.applies_when:
                problems.append(
                    f"'{r.key}' is blocking, always applies, and can still be waived as "
                    "not applicable — decide which"
                )
        return problems

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "segment": self.segment,
            "version": self.version,
            "jurisdiction": self.jurisdiction,
            "standards": list(self.standards),
            "sections": [
                {"id": s.id, "title": s.title, "order": s.order} for s in self.sections
            ],
            "requirements": [r.to_dict() for r in self.sorted_requirements()],
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "RequirementPack":
        sections = tuple(
            Section(
                id=s["id"],
                title=s.get("title", s["id"]),
                order=int(s.get("order", i * 10)),
                description=s.get("description", ""),
            )
            for i, s in enumerate(d.get("sections", []))
        ) or FOLDOK_SPINE
        reqs = []
        for r in d.get("requirements", []):
            fields = tuple(
                FormField(
                    key=f["key"],
                    label=f.get("label", f["key"]),
                    unit=f.get("unit"),
                    kind=f.get("kind", "text"),
                    choices=tuple(f.get("choices", ())),
                    required=bool(f.get("required", True)),
                )
                for f in r.get("fields", [])
            )
            reqs.append(
                Requirement(
                    key=r["key"],
                    section=r["section"],
                    title=r.get("title", r["key"]),
                    kind=r.get("kind", "text"),
                    evidence=r.get("evidence", "expository"),
                    per=r.get("per", "document"),
                    severity=r.get("severity", "required"),
                    authority=r.get("authority", ""),
                    description=r.get("description", ""),
                    applies_when=dict(r.get("applies_when", {})),
                    allow_not_applicable=bool(r.get("allow_not_applicable", True)),
                    resolvers=tuple(r.get("resolvers", ())),
                    fields=fields,
                    capture_prompt=r.get("capture_prompt", ""),
                    template=r.get("template", ""),
                    tags=tuple(r.get("tags", ())),
                )
            )
        return RequirementPack(
            id=d["id"],
            title=d.get("title", d["id"]),
            segment=d.get("segment", "general"),
            version=str(d.get("version", "1")),
            jurisdiction=d.get("jurisdiction"),
            standards=tuple(d.get("standards", ())),
            sections=sections,
            requirements=tuple(reqs),
            applies_when=dict(d.get("applies_when", {})),
            description=d.get("description", ""),
        )


# ----------------------------------------------------------------------
# condition matching
# ----------------------------------------------------------------------
def matches(facts: dict[str, Any], condition: dict[str, Any]) -> bool:
    """Tiny condition language.  Deliberately small — packs are written by
    domain people, not programmers.

        {"has_hot_water": True}
        {"voltage_v": {"gte": 400}}
        {"segment": {"in": ["marine", "offshore"]}}
        {"machine_count": {"gt": 0}}
        {"ce_marking": {"not": None}}
    """
    for key, want in sorted(condition.items()):
        have = facts.get(key)
        if isinstance(want, dict):
            for op, val in sorted(want.items()):
                if op == "eq" and have != val:
                    return False
                if op == "not" and have == val:
                    return False
                if op == "in" and have not in val:
                    return False
                if op == "not_in" and have in val:
                    return False
                if op == "gt" and not (_num(have) > _num(val)):
                    return False
                if op == "gte" and not (_num(have) >= _num(val)):
                    return False
                if op == "lt" and not (_num(have) < _num(val)):
                    return False
                if op == "lte" and not (_num(have) <= _num(val)):
                    return False
                if op == "exists" and (have is not None) != bool(val):
                    return False
        elif have != want:
            return False
    return True


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("-inf")
