"""Document length decided by the corpus, not by a template.

Hundreds of pages went in and three came out. Not a bug — arithmetic::

    _plan_topic_brief -> 6 OutlineSection(...)
    _plan_install     -> 7 OutlineSection(...)
    extract_claims(hits, limit=6)

Six or seven fixed sections, at most six claims each. Forty claims, whatever the
folder holds. The outline is a template, so the document's size is settled before
the corpus is read, and a folder of four files produces the same shape as a
folder of four hundred.

The instinct behind this module — generate wide, let the user delete — is right,
and it is right for an asymmetric reason. **Deleting a section costs a click.
Discovering that a section is missing costs a site visit**, or a rejected
handover, or a conversation with an inspector. The two errors are not equally
expensive, so the default should not sit in the middle.

What this does *not* do is pad. Volume from repetition is worse than brevity:
it buries the real content and teaches the reader to skim. Sections come from
**uncovered material** — themes and claim clusters in the corpus that the fixed
outline has nowhere to put. Every proposed section carries the evidence that
justified it, so a user deleting one can see exactly what they are dropping.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = 1

# Below this, a theme is an accident of one document rather than a topic.
MIN_EVIDENCE = 3
MIN_SOURCES = 2

STOP = {
    "the", "and", "for", "with", "this", "that", "from", "og", "av", "til", "med",
    "som", "det", "den", "der", "en", "et", "i", "på", "om", "er", "skal",
    "document", "dokument", "project", "prosjekt", "system", "product", "information",
    "technical", "teknisk", "general", "generell", "overview", "oversikt",
}

# Frequency cannot separate a verb from a noun: "utføres" and "krever" recur
# across documents exactly as reliably as "jording" does, because engineering
# prose is full of them. A theme has to be a *thing*, so the grammar is filtered
# rather than the statistics.
NOT_A_TOPIC = re.compile(
    r"("
    r"es$|ere$|eres$|ende$|ende[rn]?$|"          # Norwegian verb forms
    r"^(utf[øo]r|krev|angi|anvend|benytt|gjennomf[øo]r|foretas|sikre|"
    r"omfatt|inneholde|medf[øo]r|innebær|forutsett)|"
    r"^(require|ensure|provide|contain|include|perform|apply|consist|"
    r"should|shall|must|always|never|connect|using|used|make|made|"
    r"take|taken|give|given|keep|kept|show|shown)|"
    r"ing$|"                                       # English gerunds
    r"^(mellom|under|over|innen|etter|foran|uten|gjennom|langs|"
    r"between|within|during|through|across|before|after|about|"
    r"other|these|those|which|where|when|both|sides|cross|above)$"   # prep / filler
    r")",
    re.I,
)

# Filename stems / TOC labels are not evidence.
_HOLLOW_CLAIM = re.compile(
    r"(?i)^(?:"
    r"[\w]+(?:_[\w]+)+|"
    r"installation(?:[_\s-]*(?:guide|guidance|manual))?\.?|"
    r"installasjon(?:[_\s-]*(?:veiledning|manual|guide))?\.?"
    r")$"
)


def _quote_usable(text: str) -> bool:
    q = (text or "").strip()
    if len(q) < 28:
        return False
    if "_" in q and q.count(" ") <= 1:
        return False
    if _HOLLOW_CLAIM.match(q):
        return False
    return True


@dataclass
class Evidence:
    """Why a section is being proposed. Shown, so deleting is informed."""

    source: str
    quote: str = ""
    kind: str = "claim"

    def to_dict(self) -> dict[str, str]:
        return {"source": self.source, "quote": self.quote[:160], "kind": self.kind}


@dataclass
class ProposedSection:
    key: str
    title: str
    theme: str
    evidence: list[Evidence] = field(default_factory=list)
    sources: tuple[str, ...] = ()
    covered_by: str = ""             # an existing section, if the theme is already handled

    @property
    def weight(self) -> int:
        return len(self.evidence)

    @property
    def justified(self) -> bool:
        return self.weight >= MIN_EVIDENCE and len(self.sources) >= MIN_SOURCES

    def explain(self, *, lang: str = "no") -> str:
        if lang.startswith("no"):
            return (f"{self.title} — {self.weight} utsagn fra "
                    f"{len(self.sources)} kilde(r)")
        return f"{self.title} — {self.weight} statement(s) from {len(self.sources)} source(s)"

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key, "title": self.title, "theme": self.theme,
            "weight": self.weight, "sources": list(self.sources),
            "justified": self.justified, "covered_by": self.covered_by,
            "evidence": [e.to_dict() for e in self.evidence[:6]],
        }


@dataclass
class CoverageReport:
    proposed: list[ProposedSection] = field(default_factory=list)
    covered: list[ProposedSection] = field(default_factory=list)
    total_claims: int = 0
    placed_claims: int = 0

    @property
    def coverage(self) -> float:
        return self.placed_claims / self.total_claims if self.total_claims else 1.0

    def justified(self) -> list[ProposedSection]:
        # ``analyse`` already applied min_evidence / min_sources when appending.
        # Do not re-filter with module defaults — callers may lower the bar
        # (e.g. one focused OEM PDF with page-grain sources).
        return list(self.proposed)

    def summary(self, *, lang: str = "no") -> str:
        n = len(self.justified())
        if lang.startswith("no"):
            line = (f"{self.placed_claims} av {self.total_claims} utsagn "
                    f"({self.coverage:.0%}) passer i den faste disposisjonen")
            if n:
                line += (f"; {n} seksjon(er) foreslås for resten — "
                         "slett det du ikke vil ha")
            return line
        line = (f"{self.placed_claims} of {self.total_claims} statements "
                f"({self.coverage:.0%}) fit the fixed outline")
        if n:
            line += f"; {n} section(s) proposed for the rest — delete what you do not want"
        return line

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "total_claims": self.total_claims,
            "placed_claims": self.placed_claims,
            "coverage": round(self.coverage, 3),
            "proposed": [p.to_dict() for p in self.proposed],
            "covered": [p.to_dict() for p in self.covered],
        }


# ----------------------------------------------------------------------
def analyse(
    claims: Sequence[Mapping[str, Any]],
    outline: Sequence[Mapping[str, Any]],
    *,
    min_evidence: int = MIN_EVIDENCE,
    min_sources: int = MIN_SOURCES,
    limit: int = 12,
) -> CoverageReport:
    """What the corpus contains that the outline has nowhere to put.

    ``claims`` is anything with ``text`` and ``source``. ``outline`` is anything
    with ``key`` and ``title``.
    """
    report = CoverageReport(total_claims=len(claims))
    if not claims:
        return report

    section_terms = {
        str(s.get("key") or ""): _terms(
            f"{s.get('title', '')} {s.get('purpose', '')} {s.get('query', '')}"
        )
        for s in outline or []
    }

    vocabulary = themes_of_corpus(
        claims, min_documents=min_sources, min_count=min_evidence,
    )
    themes: dict[str, list[Mapping[str, Any]]] = {}
    for claim in claims:
        text = str(claim.get("text") or "")
        placed = False
        for key, terms in section_terms.items():
            if len(_terms(text) & terms) >= 2:
                report.placed_claims += 1
                placed = True
                break
        if placed:
            continue
        for theme in _themes_of(text, vocabulary):
            themes.setdefault(theme, []).append(claim)

    ranked = sorted(themes.items(), key=lambda kv: -len(kv[1]))
    for theme, group in ranked[:limit * 2]:
        sources = tuple(sorted({str(c.get("source") or "") for c in group if c.get("source")}))
        proposal = ProposedSection(
            key=f"auto.{re.sub(r'[^a-z0-9]+', '_', theme)[:40]}",
            title=_title_for(theme),
            theme=theme,
            sources=sources,
            evidence=[
                Evidence(source=str(c.get("source") or ""), quote=str(c.get("text") or ""),
                         kind=str(c.get("type") or "claim"))
                for c in group[:8]
                if _quote_usable(str(c.get("text") or ""))
            ],
        )
        covered = _covered_by(theme, section_terms)
        if covered:
            proposal.covered_by = covered
            report.covered.append(proposal)
        elif len(group) >= min_evidence and len(sources) >= min_sources:
            # Need enough *usable* quotes — otherwise Installation_guide noise
            # becomes a fake section.
            if len(proposal.evidence) < min_evidence:
                continue
            report.proposed.append(proposal)

    report.proposed = report.proposed[:limit]
    return report


def widen(
    outline: Sequence[Mapping[str, Any]],
    report: CoverageReport,
    *,
    mark_optional: bool = True,
) -> list[dict[str, Any]]:
    """The fixed outline plus a proposed section per uncovered theme.

    Proposed sections are marked, so the editor can show them differently and a
    user can strike them in one pass. They are not silently blended in — a
    document that grew for reasons nobody can see is worse than a short one.
    """
    out = [dict(s) for s in outline or []]
    for proposal in report.justified():
        out.append({
            "key": proposal.key,
            "title": proposal.title,
            "purpose": f"Material in the folder about {proposal.theme}",
            "query": proposal.theme,
            "proposed": True,
            "optional": mark_optional,
            "weight": proposal.weight,
            "sources": list(proposal.sources),
            "evidence": [e.to_dict() for e in proposal.evidence[:4]],
        })
    return out


def claim_budget(
    claims_available: int,
    sections: int,
    *,
    floor: int = 6,
    ceiling: int = 24,
) -> int:
    """Claims per section, scaled to what exists.

    ``extract_claims(hits, limit=6)`` is a constant, so a folder of four hundred
    files gets the same six statements per section as a folder of four. Scaling
    keeps sections readable while letting a rich corpus produce a real document.
    """
    if sections <= 0:
        return floor
    fair_share = claims_available // sections
    return max(floor, min(ceiling, fair_share))


# ----------------------------------------------------------------------
def _terms(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-zÆØÅæøå0-9]{4,}", text or "")} - STOP


def themes_of_corpus(
    claims: Sequence[Mapping[str, Any]],
    *,
    min_documents: int = 2,
    min_count: int | None = None,
) -> dict[str, set[str]]:
    """Themes derived from the corpus, not from single sentences.

    Picking the longest word in each claim gave "Punkt" and "Mellom" — filler
    that happens to be long — and split one topic across "Kabler" and
    "Terminering". A theme has to be a term that recurs *across documents*:
    filler recurs within one writer's prose, subject matter recurs between
    sources.
    """
    need = MIN_EVIDENCE if min_count is None else max(1, int(min_count))
    per_term_docs: dict[str, set[str]] = {}
    per_term_count: Counter = Counter()
    for claim in claims:
        source = str(claim.get("source") or "?")
        for term in _terms(str(claim.get("text") or "")):
            if len(term) < 5 or NOT_A_TOPIC.search(term):
                continue
            per_term_docs.setdefault(term, set()).add(source)
            per_term_count[term] += 1

    return {
        term: docs for term, docs in per_term_docs.items()
        if len(docs) >= min_documents and per_term_count[term] >= need
    }


def _themes_of(text: str, vocabulary: Mapping[str, set[str]], *, top: int = 2) -> list[str]:
    """Which corpus themes this claim belongs to. Rarer term first, because the
    rarer one is the more specific topic."""
    present = [t for t in _terms(text) if t in vocabulary]
    if not present:
        return []
    present.sort(key=lambda t: len(vocabulary[t]))
    return present[:top]


def _covered_by(theme: str, section_terms: Mapping[str, set[str]]) -> str:
    for key, terms in section_terms.items():
        if theme in terms:
            return key
    return ""


def _title_for(theme: str) -> str:
    return theme.replace("_", " ").strip().capitalize()
