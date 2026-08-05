"""Make sense of this folder — the first step, which was never built.

Everything so far has answered *"what fills the Installation section?"* — a
template names the sections, then retrieval hunts for sentences that match. When
the hunt fails the section is reported empty, which is what produced::

    Shielding      strict 6 → loose 6
    Installation   strict 0 → loose 0

Loosening the filter moved usable sentences from 103 to 252 and left Installation
at zero, because a 40-page document about EMC background contains no installation
prose. No amount of loosening creates content that is not there.

The opposite motion is what a new engineer actually needs: read everything, see
what is in there, group it, and let the groups *be* the document. That discovers
the folder contains shielding, bonding, protection classes, ground loops and ESD
— and no installation procedure — which is the truth, and more useful than an
empty heading.

So this module names nothing in advance. It assembles what exists:

    folder in  →  grouped, cited, figure-bearing draft out

and reports what the folder does **not** contain as a finding rather than as a
shortfall. Gap checking and completeness come afterwards, on a draft that exists.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = 1

# A group needs enough to be worth a heading, and corroboration beats volume.
MIN_SENTENCES = 3
MIN_SOURCES = 2
SINGLE_SOURCE_MIN = 6

STOP = {
    "the", "and", "for", "with", "this", "that", "from", "not", "are", "was",
    "og", "av", "til", "med", "som", "det", "den", "der", "ikke", "kan", "skal",
    "document", "dokument", "information", "informasjon", "technical", "teknisk",
    "system", "product", "produkt", "shall", "should", "must", "used", "using",
    "also", "other", "which", "when", "where", "these", "such", "than", "then",
    # Document furniture that survives sentence-level filtering and then becomes
    # a topic heading: "Page 17" appears in every cross-reference.
    "page", "side", "figure", "figur", "table", "tabell", "section", "seksjon",
    "chapter", "kapittel", "annex", "vedlegg", "appendix", "note", "notat",
    # Function words that recur across every document precisely because they are
    # prose. Frequency cannot distinguish them from subject matter — only the
    # grammar can. "Separate", "Over" and "Under" became topic headings.
    "separate", "separately", "over", "under", "above", "below", "between",
    "within", "during", "through", "before", "after", "against", "without",
    "mellom", "innen", "etter", "foran", "uten", "gjennom", "langs", "under",
    "over", "hver", "hvert", "alle", "andre", "samme", "slik", "både",
    "possible", "necessary", "required", "recommended", "suitable", "different",
    "mulig", "nødvendig", "anbefalt", "egnet", "ulike", "andre",
    "example", "eksempel", "case", "tilfelle", "general", "generelt",
}

# A topic has to be a *thing*. These endings mark verbs and adjectives, which
# recur across documents as reliably as nouns do.
# Suffix rules are the wrong tool here. "-ing" and "-ed" mark verbs in general
# English and mark *nouns* in this domain: shielding, earthing, bonding, jording,
# skjerming are the subjects. Blanket-filtering them removed every real topic and
# left nothing. So this lists verb stems explicitly and leaves endings alone.
NOT_A_TOPIC = re.compile(
    r"^("
    r"separat|requir|recommend|provid|ensur|contain|includ|perform|appli|"
    r"consist|indicat|describ|specifi|permitt|allow|prevent|reduc|increas|"
    r"achiev|obtain|maintain|establish|consider|determin|"
    r"utf[øo]r|krev|angi|anvend|benytt|sikre|omfatt|innehold|medf[øo]r|innebær|"
    r"gjennomf[øo]r|oppn[åa]|opprett|vurder|bestem"
    r")",
    re.I,
)


def _stem(term: str) -> str:
    """Crude conflation so "cable"/"cables" and "connection"/"connected" are one
    topic rather than two headings about the same thing.

    Not linguistics — a suffix table for the two languages in use. Wrong
    occasionally, and the cost of being wrong is two topics that should have been
    one, which is what happens without it anyway.
    """
    lowered = term.lower()
    # Longest suffix first, and applied repeatedly: "cables" -> "cable" -> "cabl"
    # only converges if a single pass does not stop at the first match. Stopping
    # early is why "cable" and "cables" stayed two topics.
    suffixes = ("ingene", "ingen", "asjonen", "asjoner", "asjon", "ations",
                "ation", "ions", "ion", "enes", "ene", "ers", "ing", "ed",
                "es", "er", "en", "et", "e", "s")
    # "kabel" -> "kabl" only if the epenthetic e is removed first; Norwegian
    # drops it when inflecting, so the stem has to as well or the singular and
    # plural never meet.
    previous = ""
    while lowered != previous:
        previous = lowered
        for suffix in suffixes:
            if lowered.endswith(suffix) and len(lowered) - len(suffix) >= 4:
                lowered = lowered[: -len(suffix)]
                break
    # Norwegian drops the epenthetic e when inflecting ("kabel" -> "kabler"), so
    # the stem must too. After suffix stripping, never before: doing it first
    # turned "kabler" into "kablr".
    return re.sub(r"([bdgklmnprstv])e([lnr])$", r"\1\2", lowered)


@dataclass
class Passage:
    """One citable sentence, with where it came from and how strong it is."""

    text: str
    source: str
    tier: str = "candidate"          # strong | candidate
    claim_type: str = ""
    role: str = "unknown"            # project | reference

    @property
    def provenance(self) -> str:
        if self.tier == "strong" and self.claim_type:
            return f"{self.claim_type}, {self.source}"
        return self.source

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text, "source": self.source, "tier": self.tier,
            "claim_type": self.claim_type, "role": self.role,
        }


@dataclass
class Group:
    """A topic the folder actually contains."""

    key: str
    title: str
    passages: list[Passage] = field(default_factory=list)
    figures: list[dict[str, Any]] = field(default_factory=list)
    sources: tuple[str, ...] = ()

    @property
    def weight(self) -> int:
        return len(self.passages)

    @property
    def strong_share(self) -> float:
        if not self.passages:
            return 0.0
        return sum(1 for p in self.passages if p.tier == "strong") / len(self.passages)

    @property
    def justified(self) -> bool:
        if len(self.sources) >= MIN_SOURCES and self.weight >= MIN_SENTENCES:
            return True
        # One source can carry a topic if it says enough about it. Requiring two
        # sources absolutely means a single-document folder yields nothing.
        return len(self.sources) == 1 and self.weight >= SINGLE_SOURCE_MIN

    def markdown(self, *, lang: str = "no", limit: int = 12) -> str:
        lines = [f"## {self.title}", ""]
        for passage in self.passages[:limit]:
            mark = "" if passage.tier == "strong" else " ^"
            lines.append(f"- {passage.text}{mark}  *({passage.provenance})*")
        for figure in self.figures[:4]:
            caption = figure.get("caption") or figure.get("id")
            lines.append("")
            lines.append(f"![{caption}]({figure.get('id')})  *{figure.get('source', '')}*")
        if any(p.tier != "strong" for p in self.passages[:limit]):
            lines.append("")
            lines.append(
                "*^ beskrivende tekst uten eksplisitt krav — slett hvis den ikke hører hjemme.*"
                if lang.startswith("no") else
                "*^ descriptive text with no explicit requirement — delete if it does not belong.*"
            )
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key, "title": self.title, "weight": self.weight,
            "sources": list(self.sources), "strong_share": round(self.strong_share, 2),
            "justified": self.justified,
            "passages": [p.to_dict() for p in self.passages],
            "figures": self.figures,
        }


@dataclass
class Draft:
    """What the folder contains — and, as plainly, what it does not."""

    groups: list[Group] = field(default_factory=list)
    orphan_figures: list[dict[str, Any]] = field(default_factory=list)
    files_read: int = 0
    sentences_seen: int = 0
    sentences_used: int = 0
    absent: list[str] = field(default_factory=list)
    title: str = ""
    corroborated: bool = True
    """False when no term recurred across sources and topics came from frequency
    within single documents. The draft is still useful; it is just weaker
    evidence, and a compliance engineer signing it should know which."""

    @property
    def coverage(self) -> float:
        return self.sentences_used / self.sentences_seen if self.sentences_seen else 0.0

    def justified(self) -> list[Group]:
        return [g for g in self.groups if g.justified]

    def summary(self, *, lang: str = "no") -> str:
        groups = self.justified()
        figures = sum(len(g.figures) for g in groups) + len(self.orphan_figures)
        if lang.startswith("no"):
            line = (f"{self.files_read} filer → {len(groups)} tema, "
                    f"{self.sentences_used} siterte setninger, {figures} figurer")
            if self.absent:
                line += f". Ikke dekket i mappen: {', '.join(self.absent[:4])}"
            if not self.corroborated:
                line += (". Ingen tema går igjen i flere kilder — dette er tema "
                         "per dokument, ikke bekreftet på tvers")
            return line
        line = (f"{self.files_read} files → {len(groups)} topics, "
                f"{self.sentences_used} cited sentences, {figures} figures")
        if self.absent:
            line += f". Not covered by this folder: {', '.join(self.absent[:4])}"
        if not self.corroborated:
            line += (". No topic appears in more than one source — these are "
                     "per-document topics, not corroborated themes")
        return line

    def markdown(self, *, lang: str = "no") -> str:
        no = lang.startswith("no")
        parts = [f"# {self.title or ('Utkast fra mappen' if no else 'Draft from the folder')}", ""]
        parts.append(f"*{self.summary(lang=lang)}*")
        parts.append("")
        for group in self.justified():
            parts.append(group.markdown(lang=lang))
            parts.append("")
        if self.absent:
            parts.append("## " + ("Ikke dekket av kildene" if no else "Not covered by the sources"))
            parts.append("")
            parts.append(
                "Disse temaene finnes ikke i mappen. De må skrives eller kildene må utvides:"
                if no else
                "These topics are not in the folder. They must be written, or sources added:"
            )
            parts += [f"- {a}" for a in self.absent]
            parts.append("")
        if self.orphan_figures:
            parts.append("## " + ("Figurer uten tema" if no else "Unplaced figures"))
            parts.append("")
            for figure in self.orphan_figures[:12]:
                parts.append(f"- {figure.get('caption') or figure.get('id')} "
                             f"*({figure.get('source', '')})*")
        return "\n".join(parts).strip() + "\n"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "title": self.title,
            "files_read": self.files_read,
            "sentences_seen": self.sentences_seen,
            "sentences_used": self.sentences_used,
            "coverage": round(self.coverage, 3),
            "groups": [g.to_dict() for g in self.justified()],
            "absent": list(self.absent),
            "orphan_figures": self.orphan_figures,
        }


# ----------------------------------------------------------------------
def discover_topics(
    passages: Sequence[Passage],
    *,
    limit: int = 14,
    min_sources: int = MIN_SOURCES,
) -> list[str]:
    """What the folder is about, from the folder.

    A topic is a term that recurs *across sources*. Within one document a writer
    repeats their own vocabulary; between documents, only the subject matter
    recurs.
    """
    per_term_sources: dict[str, set[str]] = {}
    per_term_count: Counter = Counter()
    surface: dict[str, Counter] = {}
    for passage in passages:
        for term in _terms(passage.text):
            if NOT_A_TOPIC.search(term):
                continue
            stem = _stem(term)
            per_term_sources.setdefault(stem, set()).add(passage.source)
            per_term_count[stem] += 1
            surface.setdefault(stem, Counter())[term] += 1

    # Cross-source recurrence is the right signal for a folder and impossible
    # for a single document, where every term has exactly one source. Fall back
    # to frequency within the document rather than returning nothing — a folder
    # of one file is still a folder somebody wants sense made of.
    available = len({p.source for p in passages})
    effective_min = min(min_sources, available)

    ranked = [
        (term, len(sources), per_term_count[term])
        for term, sources in per_term_sources.items()
        if len(sources) >= effective_min and per_term_count[term] >= MIN_SENTENCES
    ]

    # Cross-source recurrence is the right signal and it can legitimately find
    # nothing: a folder whose documents are in different languages, or about
    # genuinely separate subjects, shares no vocabulary. Measured on a real
    # mixed folder — one English PDF plus two Norwegian files — *zero* stems
    # appeared in two sources.
    #
    # Returning nothing there is the wrong answer. The folder still has topics;
    # they are just per-document. So fall back to frequency and mark the
    # difference, rather than handing back an empty draft.
    if not ranked:
        ranked = [
            (term, len(sources), per_term_count[term])
            for term, sources in per_term_sources.items()
            if per_term_count[term] >= max(MIN_SENTENCES, 4)
        ]
    ranked.sort(key=lambda t: (-t[1], -t[2]))
    # Report the commonest surface form, so a heading reads as a word rather
    # than a stem.
    return [surface[stem].most_common(1)[0][0] for stem, _, _ in ranked[:limit]]


def assemble(
    passages: Sequence[Passage],
    *,
    figures: Sequence[Mapping[str, Any]] = (),
    title: str = "",
    files_read: int = 0,
    sentences_seen: int = 0,
    expected: Iterable[str] = (),
    limit: int = 14,
    lang: str = "no",
) -> Draft:
    """Folder in, grouped and cited draft out. Names nothing in advance.

    ``expected`` is optional — topics the user hoped to find. Anything absent is
    reported rather than rendered as an empty heading, because "your folder does
    not contain installation procedures" is useful and "Installation: (empty)" is
    not.
    """
    topics = discover_topics(passages, limit=limit)
    groups: dict[str, Group] = {}
    used: set[int] = set()

    for topic in topics:
        stem = _stem(topic)
        matched = [
            (i, p) for i, p in enumerate(passages)
            if stem in {_stem(t) for t in _terms(p.text)}
        ]
        if not matched:
            continue
        group = Group(key=f"grp.{topic}", title=_title(topic, lang))
        # Strong passages lead; descriptive ones follow and are marked.
        matched.sort(key=lambda t: (0 if t[1].tier == "strong" else 1,
                                    0 if t[1].role == "project" else 1))
        for index, passage in matched:
            group.passages.append(passage)
            used.add(index)
        group.sources = tuple(sorted({p.source for p in group.passages}))
        groups[topic] = group

    placed: set[str] = set()
    for figure in figures:
        caption = str(figure.get("caption") or "")
        target = _figure_topic(caption, groups)
        if target:
            groups[target].figures.append(dict(figure))
            placed.add(str(figure.get("id")))

    orphans = [dict(f) for f in figures if str(f.get("id")) not in placed]

    multi_source = any(len(g.sources) >= MIN_SOURCES for g in groups.values())
    draft = Draft(
        corroborated=multi_source,
        groups=sorted(groups.values(), key=lambda g: -g.weight),
        orphan_figures=orphans,
        files_read=files_read or len({p.source for p in passages}),
        sentences_seen=sentences_seen or len(passages),
        sentences_used=len(used),
        title=title,
    )

    # Compare stems, not surface forms. "skjerming" must match a group whose
    # passages are about "skjerm" — comparing raw terms made the conflation work
    # for grouping and not for anything else.
    covered: set[str] = set()
    for group in draft.justified():
        covered |= {_stem(t) for t in _terms(group.title)}
        for passage in group.passages:
            covered |= {_stem(t) for t in _terms(passage.text)}
    for want in expected:
        if not ({_stem(t) for t in _terms(want)} & covered):
            draft.absent.append(want)
    return draft


# ----------------------------------------------------------------------
def passages_from(
    tier_report: Any,
    *,
    role: str = "unknown",
    include_candidates: bool = True,
) -> list[Passage]:
    """Bridge from ``foldok_tier``. Keeps the tier, because it decides how a
    passage may be cited."""
    out: list[Passage] = []
    for sentence in getattr(tier_report, "sentences", []):
        if sentence.tier == "rejected":
            continue
        if sentence.tier == "candidate" and not include_candidates:
            continue
        out.append(Passage(
            text=sentence.text, source=sentence.source, tier=sentence.tier,
            claim_type=getattr(sentence, "claim_type", ""), role=role,
        ))
    return out


def _figure_topic(caption: str, groups: Mapping[str, Group]) -> str:
    """Place a figure by its caption. A figure with no matching topic stays
    unplaced rather than being dropped into the nearest group."""
    words = {_stem(t) for t in _terms(caption)}
    best, score = "", 0
    for topic, group in groups.items():
        group_terms = {_stem(t) for t in _terms(group.title)} | {_stem(topic)}
        overlap = len(words & group_terms)
        if overlap > score:
            best, score = topic, overlap
    return best if score else ""


def _terms(text: str) -> set[str]:
    return {
        w.lower() for w in re.findall(r"[A-Za-zÀ-ÿÆØÅæøå]{4,}", text or "")
    } - STOP


def _title(topic: str, lang: str) -> str:
    return topic.replace("_", " ").capitalize()
