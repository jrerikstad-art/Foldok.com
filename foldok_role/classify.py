"""Project material or reference material — the distinction the index was missing.

A 30-page SICK technical brochure was added to an EMC installation folder, and
the resulting document became about safety laser scanners. Not a writing failure.
``plan.corpus_sketch`` counts one vote per tag per file::

    for e in usable[:100]:
        for t in e.get("content_tags") or []:
            tag_c[t] += 1
    themes = [t for t, _ in tag_c.most_common(6)]

A vendor brochure produces a dense, confident tag set — *safety laser scanner,
sensor, ESD, PELV, shielding, functional earth*. A folder of the project's own
drawings and correspondence produces fewer and vaguer ones. So the reference
document out-votes the project, and the planner faithfully builds a document
about what the corpus now looks like.

The fix is not better tag counting. It is that **a datasheet and a drawing are
not the same kind of thing**, and nothing in the index said so. Background
material should inform a section; it should never decide what the document is
about.

Signals, in rough order of how much they settle it:

*   a vendor's own document number — ``8027032/2022-07-19`` — is a publication
    identity, and projects do not have those
*   a manufacturer name in the filename, caption or footer
*   a standard designation as the subject rather than as a citation
*   the client or project name appearing nowhere in the file
*   role hints the indexer already produced (``datasheet``, ``drawing``)

None is conclusive alone, which is why they are weighted rather than chained.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping, Sequence

SCHEMA_VERSION = 1

Role = Literal["project", "reference", "ignore", "unknown"]

# Weight per file for theme voting. Reference informs; ignored material does not
# reach the document at all.
#
# The third tier matters: a supplier's marketing brochure is not weak reference
# material, it is not reference material. Letting it in at 0.15 still means a
# price list votes on what an installation document is about.
ROLE_WEIGHT: dict[str, float] = {
    "project": 1.0, "unknown": 0.5, "reference": 0.15, "ignore": 0.0,
}

# A publication identity: long numeric document number, often with a date.
PUB_NUMBER = re.compile(r"\b\d{6,9}\s*[/|]\s*\d{4}(?:-\d{2}){0,2}\b")

VENDORS = (
    "sick", "siemens", "abb", "schneider", "phoenix contact", "weidmüller",
    "weidmuller", "rittal", "pepperl", "ifm", "banner", "omron", "keyence",
    "chalfant", "legrand", "niedax", "atkore", "marco", "obo bettermann",
    "hellermanntyton", "lapp", "igus", "festo", "wago", "eaton", "hager",
    "fluke", "megger", "pilz", "leuze",
)

STANDARD_BODIES = ("iec", "iso", "en", "nek", "bs", "astm", "ieee", "nema", "ul",
                   "din", "vde", "dnv", "mil-std", "mil std")

REFERENCE_WORDS = (
    "technical information", "teknisk informasjon", "background knowledge",
    "datasheet", "datablad", "product catalogue", "product catalog", "katalog",
    "brochure", "brosjyre", "operating instructions", "user manual",
    "installation instructions", "white paper", "application note",
    "subject to change without notice", "all rights reserved",
)

PROJECT_WORDS = (
    "as-built", "som bygget", "site", "anlegg", "prosjekt", "project no",
    "revision", "revisjon", "for construction", "for approval", "issued for",
    "punch", "avvik", "befaring", "sjekkliste", "protokoll", "måleprotokoll",
    "transmittal", "tilbud", "kontrakt", "møtereferat", "korrespondanse",
)

# Sales material. Not a weaker kind of reference — a different kind of thing.
IGNORE_WORDS = (
    "brochure", "brosjyre", "product range", "produktutvalg", "price list",
    "prisliste", "company profile", "om oss", "about us", "our solutions",
    "våre løsninger", "success story", "case study", "kundehistorie",
    "newsletter", "nyhetsbrev", "press release", "pressemelding",
    "contact your local", "request a quote", "be om tilbud", "follow us",
    "why choose", "hvorfor velge", "market leader", "markedsleder",
)

# Strong enough to override the marketing wrapper a real datasheet often has.
TECHNICAL_WORDS = (
    "technical data", "tekniske data", "specification", "spesifikasjon",
    "dimensions", "dimensjoner", "test report", "prøverapport", "declaration",
    "erklæring", "installation", "montering", "wiring", "kobling", "clause",
    "requirement", "krav", "tolerance", "toleranse", "rated", "merkespenning",
)

# Roles the indexer may already have guessed.
HINT_ROLE: dict[str, Role] = {
    "datasheet": "reference", "datablad": "reference", "standard": "reference",
    "catalogue": "reference", "catalog": "reference", "manual": "reference",
    "brochure": "reference", "white_paper": "reference",
    "drawing": "project", "tegning": "project", "photo": "project",
    "test_report": "project", "protocol": "project", "checklist": "project",
    "correspondence": "project", "email": "project", "minutes": "project",
    "declaration": "project", "certificate": "project",
}


@dataclass
class Classification:
    file: str
    role: Role = "unknown"
    confidence: float = 0.0
    reasons: tuple[str, ...] = ()

    @property
    def weight(self) -> float:
        return ROLE_WEIGHT[self.role]

    def explain(self) -> str:
        return f"{self.file}: {self.role} ({self.confidence:.0%})" + (
            f" — {self.reasons[0]}" if self.reasons else ""
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file, "role": self.role,
            "confidence": round(self.confidence, 2), "reasons": list(self.reasons),
        }


@dataclass
class RoleReport:
    classifications: list[Classification] = field(default_factory=list)

    def of(self, role: str) -> list[Classification]:
        return [c for c in self.classifications if c.role == role]

    def by_file(self) -> dict[str, Classification]:
        return {c.file: c for c in self.classifications}

    @property
    def reference_share(self) -> float:
        return len(self.of("reference")) / len(self.classifications) if self.classifications else 0.0

    def summary(self, *, lang: str = "no") -> str:
        p, r, u = len(self.of("project")), len(self.of("reference")), len(self.of("unknown"))
        if lang.startswith("no"):
            line = f"{p} prosjektfil(er), {r} referansefil(er), {u} usikre"
        else:
            line = f"{p} project file(s), {r} reference file(s), {u} unclear"
        if self.reference_share > 0.5:
            line += (
                " — referansematerialet er i flertall; det informerer seksjonene, "
                "men bestemmer ikke hva dokumentet handler om"
                if lang.startswith("no") else
                " — reference material is the majority; it informs sections but does "
                "not decide the subject"
            )
        return line

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "project": len(self.of("project")),
            "reference": len(self.of("reference")),
            "unknown": len(self.of("unknown")),
            "classifications": [c.to_dict() for c in self.classifications],
        }


# ----------------------------------------------------------------------
def classify(
    entry: Mapping[str, Any],
    *,
    project_terms: Sequence[str] = (),
) -> Classification:
    """One file. Weighted signals, because none of them is conclusive alone."""
    path = str(entry.get("file") or "")
    name = Path(path).name
    caption = str(entry.get("caption") or "")
    detail = str(entry.get("detail_summary") or "")
    hints = [str(h).lower() for h in (entry.get("doc_role_hints") or [])]
    tags = [str(t).lower() for t in (entry.get("content_tags") or [])]
    blob = " ".join((name, caption, detail[:2000])).lower()

    score = 0.0                       # positive = reference, negative = project
    reasons: list[str] = []

    for hint in hints:
        role = HINT_ROLE.get(hint)
        if role == "reference":
            score += 0.45
            reasons.append(f"indexer called it a {hint}")
        elif role == "project":
            score -= 0.45
            reasons.append(f"indexer called it a {hint}")

    if PUB_NUMBER.search(blob):
        score += 0.4
        reasons.append("carries a publication number — projects do not have those")

    vendor = next((v for v in VENDORS if v in blob), "")
    if vendor:
        score += 0.35
        reasons.append(f"published by {vendor}")

    marketing = [w for w in IGNORE_WORDS if w in blob]
    technical = [w for w in TECHNICAL_WORDS if w in blob]
    if marketing and not technical:
        # No technical content to redeem it. A catalogue with real data is
        # reference; a brochure about the company is neither.
        return Classification(
            file=path, role="ignore",
            confidence=min(0.9, 0.55 + 0.15 * len(marketing)),
            reasons=(f"sales material ('{marketing[0]}') with no technical content",),
        )

    hits = [w for w in REFERENCE_WORDS if w in blob]
    if hits:
        score += min(0.4, 0.2 * len(hits))
        reasons.append(f"reads as reference material ('{hits[0]}')")

    project_hits = [w for w in PROJECT_WORDS if w in blob]
    if project_hits:
        score -= min(0.5, 0.25 * len(project_hits))
        reasons.append(f"reads as project material ('{project_hits[0]}')")

    named = [t for t in project_terms if t and t.lower() in blob]
    if named:
        score -= 0.5
        reasons.append(f"names the project or client ('{named[0]}')")
    elif project_terms:
        # Knowing the project's name and not finding it is a real signal; not
        # knowing it is no signal at all.
        score += 0.2
        reasons.append("does not mention the project or client anywhere")

    if _is_standard_subject(name, tags):
        score += 0.3
        reasons.append("the standard is the subject, not a citation")

    if score >= 0.35:
        role, confidence = "reference", min(0.95, 0.5 + score / 2)
    elif score <= -0.35:
        role, confidence = "project", min(0.95, 0.5 + abs(score) / 2)
    else:
        role, confidence = "unknown", 0.4

    return Classification(file=path, role=role, confidence=confidence,
                          reasons=tuple(reasons[:4]))


def classify_index(
    index: Iterable[Mapping[str, Any]],
    *,
    project_terms: Sequence[str] = (),
) -> RoleReport:
    report = RoleReport()
    for entry in index or []:
        if entry.get("kind") == "skipped" or not entry.get("file"):
            continue
        report.classifications.append(classify(entry, project_terms=project_terms))
    return report


def _is_standard_subject(name: str, tags: Sequence[str]) -> bool:
    """'EN 50174-2.pdf' is the standard itself; a drawing citing it is not."""
    stem = Path(name).stem.lower()
    for body in STANDARD_BODIES:
        if stem.startswith(body) or stem.startswith(body.replace(" ", "-")):
            return True
    return any(t in ("standard", "norm") for t in tags)
