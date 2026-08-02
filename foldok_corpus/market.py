"""The section market — the corpus proposes, the user disposes, the engine orders.

Five documents from one folder came out looking alike: same six sections, same
name-only difference, three pages each. Two causes, and they were being confused.

The three pages was the citation blocker (see ``foldok_budget``). The *sameness*
is this: a template asks "what document are you making?" **before anything has
been read**, and then its section list becomes a ceiling. A folder with fourteen
topics loses eight of them regardless of which template is chosen, and every
template draws from the same narrow claim pool.

So identity comes first, naming last:

    0  identify the project (purpose, audience, primary vs secondary topics)
    1  read the folder, report what it can support *for that identity*
    2  offer every section the material justifies, scored for relevance
    3  the user keeps, deletes, reorders
    4  the engine enforces the arc — some orders are simply wrong
    5  the document's *label* emerges from the selection

What abundance alone does not fix: a pile of sections in no order is not a
document. Section 3 assuming section 2 is what makes prose readable, so ordering
is a constraint the engine holds even when the user is free to choose content.

And templates do not disappear — they invert. Instead of "installation manual =
these six sections", a template becomes "a handover package must contain a
declaration and test records": a **requirement over the selection** rather than a
recipe for it. That is ``foldok_gaps`` already, and it puts the relationship the
right way round. The user knows what they need; Foldok checks whether they have
it.

See ``PROJECT_IDENTITY.md`` and ``foldok_identity``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal, Mapping, Sequence

SCHEMA_VERSION = 1

# Narrative position. A section may move within its band but not across it —
# results before method reads as a mistake even when every sentence is correct.
BAND: dict[str, int] = {
    "frame": 0,        # identification, scope, purpose, audience
    "basis": 1,        # assumptions, standards, conditions, decisions
    "body": 2,         # the subject matter itself
    "evidence": 3,     # measurements, tests, observations, problems
    "exception": 4,    # deviations, open items, changes
    "close": 5,        # conclusions, responsibilities, handover, declaration
}

# Which band a section type belongs in, by the claim types that feed it.
TYPE_BAND: dict[str, str] = {
    "definition": "frame", "classification": "frame",
    "condition": "basis", "decision": "basis", "justification": "basis",
    "reference": "basis", "rule": "basis", "constraint": "basis",
    "quantity": "body", "practice": "body", "distinction": "body",
    "sequence": "body", "consequence": "body", "hypothesis": "body",
    "problem": "evidence", "risk": "evidence",
    "exception": "exception", "change": "exception", "open_question": "exception",
    "responsibility": "close",
}

BAND_TITLE: dict[str, tuple[str, str]] = {
    "frame": ("Ramme", "Frame"),
    "basis": ("Grunnlag", "Basis"),
    "body": ("Innhold", "Body"),
    "evidence": ("Dokumentasjon", "Evidence"),
    "exception": ("Avvik og åpne punkter", "Exceptions and open items"),
    "close": ("Avslutning", "Close"),
}

# Two statements from two *different* sources is corroboration, and corroboration
# is the signal that matters — a topic two documents independently raise is real.
# Requiring three statements suppressed exactly the sections that make documents
# differ from one another: decisions, conditions, problems, open questions. They
# are rarer than requirements by nature, not less important.
MIN_WEIGHT = 2
MIN_SOURCES = 2

# A single source can still justify a section if it says enough about the topic.
SINGLE_SOURCE_WEIGHT = 4


@dataclass
class Offer:
    """One section the corpus can support, with what justifies it."""

    key: str
    title: str
    band: str
    claim_types: tuple[str, ...] = ()
    weight: int = 0
    sources: tuple[str, ...] = ()
    samples: tuple[str, ...] = ()
    kept: bool = True                 # abundance: offered as kept, user deletes
    relevance: str = "somewhat"       # vs ProjectIdentity: relevant|somewhat|background|ignore

    @property
    def justified(self) -> bool:
        return self.weight >= MIN_WEIGHT and len(self.sources) >= MIN_SOURCES

    @property
    def rank(self) -> int:
        return BAND.get(self.band, 2)

    def explain(self, *, lang: str = "no") -> str:
        base = (
            f"{self.title} — {self.weight} utsagn fra {len(self.sources)} kilde(r)"
            if lang.startswith("no") else
            f"{self.title} — {self.weight} statement(s) from {len(self.sources)} source(s)"
        )
        if self.relevance and self.relevance != "somewhat":
            return f"{base} [{self.relevance}]"
        return base

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key, "title": self.title, "band": self.band,
            "weight": self.weight, "sources": list(self.sources),
            "claim_types": list(self.claim_types), "kept": self.kept,
            "justified": self.justified, "samples": list(self.samples[:3]),
            "relevance": self.relevance,
        }


@dataclass
class CorpusOffer:
    """Everything the folder can support. No document type named."""

    offers: list[Offer] = field(default_factory=list)
    claim_total: int = 0
    source_total: int = 0

    def kept(self) -> list[Offer]:
        return [o for o in self.offers if o.kept]

    def ordered(self) -> list[Offer]:
        """Narrative order. Weight decides within a band, never across one."""
        return sorted(self.kept(), key=lambda o: (o.rank, -o.weight, o.key))

    def by_band(self) -> dict[str, list[Offer]]:
        out: dict[str, list[Offer]] = {}
        for offer in self.ordered():
            out.setdefault(offer.band, []).append(offer)
        return out

    def keep_only(self, keys: Iterable[str]) -> "CorpusOffer":
        wanted = set(keys)
        for offer in self.offers:
            offer.kept = offer.key in wanted
        return self

    def drop(self, *keys: str) -> "CorpusOffer":
        for offer in self.offers:
            if offer.key in keys:
                offer.kept = False
        return self

    def report(self, *, lang: str = "no") -> str:
        no = lang.startswith("no")
        head = (
            f"Mappen støtter {len(self.offers)} seksjon(er) fra {self.claim_total} "
            f"utsagn i {self.source_total} kilder. Ingen dokumenttype er valgt."
            if no else
            f"The folder supports {len(self.offers)} section(s) from {self.claim_total} "
            f"statements across {self.source_total} sources. No document type chosen."
        )
        lines = [head, ""]
        for band, offers in self.by_band().items():
            lines.append(f"  {BAND_TITLE[band][0 if no else 1]}")
            for offer in offers:
                lines.append(f"    {offer.explain(lang=lang)}")
        lines.append("")
        lines.append(
            "Slett det du ikke vil ha. Dokumentet blir det du beholder."
            if no else
            "Delete what you do not want. The document is what you keep."
        )
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "claim_total": self.claim_total,
            "source_total": self.source_total,
            "offers": [o.to_dict() for o in self.offers],
        }


# ----------------------------------------------------------------------
def build_offer(
    claims: Sequence[Mapping[str, Any]],
    *,
    lang: str = "no",
    min_weight: int = MIN_WEIGHT,
    min_sources: int = MIN_SOURCES,
    identity: Any = None,
) -> CorpusOffer:
    """What this folder can support for an optional ProjectIdentity.

    Without ``identity``, offers are availability-only (legacy). With it, each
    offer is scored Relevant / Somewhat / Background / Ignore, and Ignore is
    dropped from the default kept set so OEM density cannot become the document.

    ``claims`` is anything with ``type``, ``text`` and ``source`` — the union of
    ``foldok_claims`` and ``foldok_corpus.widen`` output.
    """
    by_type: dict[str, list[Mapping[str, Any]]] = {}
    sources: set[str] = set()
    for claim in claims:
        ctype = str(claim.get("type") or "")
        if not ctype:
            continue
        by_type.setdefault(ctype, []).append(claim)
        if claim.get("source"):
            sources.add(str(claim["source"]))

    proj = None
    if identity is not None:
        proj = getattr(identity, "identity", identity)

    offers: list[Offer] = []
    for ctype, group in by_type.items():
        group_sources = tuple(sorted({str(c.get("source") or "") for c in group if c.get("source")}))
        corroborated = len(group) >= min_weight and len(group_sources) >= min_sources
        substantial = len(group_sources) == 1 and len(group) >= SINGLE_SOURCE_WEIGHT
        if not (corroborated or substantial):
            continue
        offer = Offer(
            key=f"sec.{ctype}",
            title=_title_for(ctype, lang),
            band=TYPE_BAND.get(ctype, "body"),
            claim_types=(ctype,),
            weight=len(group),
            sources=group_sources,
            samples=tuple(str(c.get("text") or "")[:120] for c in group[:3]),
        )
        if proj is not None:
            try:
                from foldok_identity import score_offer
                offer.relevance = score_offer(offer, proj)
            except Exception:
                offer.relevance = "somewhat"
            if offer.relevance == "ignore":
                offer.kept = False
        offers.append(offer)

    offers.sort(key=lambda o: (o.rank, -o.weight))
    return CorpusOffer(offers=offers, claim_total=len(claims), source_total=len(sources))


def to_outline(offer: CorpusOffer, *, title: str = "") -> list[dict[str, Any]]:
    """The kept sections, in narrative order, as an outline the author can use."""
    return [
        {
            "key": o.key,
            "title": o.title,
            "purpose": f"material of type {', '.join(o.claim_types)}",
            "query": o.title,
            "claim_types": list(o.claim_types),
            "band": o.band,
            "weight": o.weight,
            "sources": list(o.sources),
        }
        for o in offer.ordered()
    ]


def check_order(outline: Sequence[Mapping[str, Any]]) -> list[str]:
    """Orders that read as mistakes even when every sentence is correct."""
    problems: list[str] = []
    seen: list[tuple[int, str]] = []
    for section in outline:
        band = str(section.get("band") or "body")
        rank = BAND.get(band, 2)
        for prev_rank, prev_title in seen:
            if prev_rank > rank + 1:
                problems.append(
                    f"'{section.get('title')}' ({band}) comes after "
                    f"'{prev_title}' — evidence before its basis reads as a mistake"
                )
                break
        seen.append((rank, str(section.get("title") or "")))
    return problems


# ----------------------------------------------------------------------
def compare_documents(offers: Sequence[CorpusOffer], names: Sequence[str]) -> str:
    """How five documents from one folder actually differ.

    Abundance cannot manufacture distinctness that is not in the corpus. What it
    can do is say so plainly — which sections are unique to a document and which
    appear in all of them — rather than hiding the overlap behind five names.
    """
    if not offers:
        return ""
    sets = [{o.key for o in offer.kept()} for offer in offers]
    shared = set.intersection(*sets) if sets else set()
    lines = [f"{len(offers)} dokument(er) fra samme mappe:"]
    for name, keys in zip(names, sets):
        unique = keys - shared
        lines.append(
            f"  {name}: {len(keys)} seksjon(er), {len(unique)} unik"
            + (f" ({', '.join(sorted(unique)[:3])})" if unique else "")
        )
    if shared:
        lines.append(f"  felles for alle: {len(shared)} seksjon(er)")
    else:
        lines.append("  felles for alle: ingen — dokumentene deler ikke innhold")
    if len(shared) == max(len(s) for s in sets):
        lines.append(
            "  → dokumentene er identiske i innhold; mappen støtter foreløpig ett dokument"
        )
    return "\n".join(lines)


def _title_for(claim_type: str, lang: str) -> str:
    from .widen import FEEDS_SECTION

    if claim_type in FEEDS_SECTION:
        return FEEDS_SECTION[claim_type][0 if lang.startswith("no") else 1]
    titles = {
        "quantity": ("Tekniske data", "Technical data"),
        "definition": ("Begreper", "Definitions"),
        "classification": ("Klassifisering", "Classification"),
        "rule": ("Krav", "Requirements"),
        "constraint": ("Begrensninger", "Constraints"),
        "practice": ("Anbefalt praksis", "Recommended practice"),
        "distinction": ("Avgrensninger", "Distinctions"),
        "hypothesis": ("Antakelser", "Hypotheses"),
        "risk": ("Risiko", "Risks"),
        "reference": ("Referanser", "References"),
    }
    pair = titles.get(claim_type, (claim_type.title(), claim_type.title()))
    return pair[0 if lang.startswith("no") else 1]
