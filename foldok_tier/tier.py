"""Tiered extraction — the filter that was doing the relevance work.

Measured on a real technical PDF::

    66,333 characters  →  429 sentences  →  104 claims

Four sentences in five are discarded, silently. ``foldok_claims`` emits a claim
only when a sentence matches a pattern — ``skal``, ``shall``, ``krever``, a
quantity, a clause reference — so the patterns are not merely filtering for
quality. They are the only relevance judgement in the pipeline, and removing them
does not make the document four times richer. It fills it with page footers,
contents rows and the copyright notice.

But the line is drawn in the wrong place. It keeps *obligations* and drops
*descriptions*, and an installation manual is mostly description::

    "The shielding is applied over a large area to keep the connection
     as low-impedance as possible."

That matches no pattern, is exactly what a section needs, and is currently
thrown away.

So: three tiers rather than a switch.

    strong      matched a pattern — a rule, a quantity, a decision, a condition
    candidate   a well-formed sentence about the subject, no pattern
    rejected    furniture, fragments, boilerplate, navigation

Sections draw on strong first and fill from candidates when thin. Every candidate
is marked, so a user striking one can see what it is.

**What this costs, stated plainly.** A strong claim carries a type: *this is a
requirement from EN 50174-2*. A candidate carries only a source: *this appeared in
EN 50174-2*. For a handover document that difference matters; for a technical
brief it probably does not. The tier travels with the sentence so the decision
stays visible downstream rather than being made once here.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal, Mapping, Sequence

SCHEMA_VERSION = 1

Tier = Literal["strong", "candidate", "rejected"]

# Sentence-level furniture. Cheap to detect and never content.
REJECT = (
    ("copyright", re.compile(
        r"\b(all rights reserved|subject to change without notice|©|"
        r"opphavsrett|med forbehold om endringer|reproduction of this document|"
        r"legal information|protected by copyright|this work is protected)\b", re.I)),
    ("contact", re.compile(r"([\w.+-]+@[\w-]+\.\w{2,})|(\+\d{2}[\s\d]{7,})|(https?://)")),
    ("navigation", re.compile(
        r"\b(see (figure|table|section|page|chapter)\s*\d+|"
        r"se (figur|tabell|avsnitt|side|kapittel)\s*\d+|"
        r"continued on|fortsetter p[åa]|refer to (figure|table)\s*\d+)\b", re.I)),
    ("contents", re.compile(r"\.{4,}\s*\d+\s*$|^\s*(contents|innhold|index)\s*$", re.I)),
    ("pagination", re.compile(
        r"^\s*(page|side)\s*\d+(\s*(of|av)\s*\d+)?\s*$|^\s*\d+\s*/\s*\d+\s*$", re.I)),
    ("legal_notice", re.compile(
        r"\b(excludes any liability|fraskriver seg ethvert ansvar|"
        r"no warranty|ingen garanti)\b", re.I)),
    ("address_line", re.compile(
        r"\b(germany|deutschland|waldkirch|strasse|street|postfach|gmbh)\b", re.I)),
)

# Structural disqualifiers — a sentence that is not a sentence.
MIN_WORDS = 6
MAX_WORDS = 70
MIN_LETTER_SHARE = 0.55

SENTENCE_END = re.compile(r"[.!?][\"'”’)\]]?\s*$")
HAS_VERB = re.compile(
    r"\b(is|are|was|were|has|have|shall|should|must|may|can|will|does|do|"
    r"er|var|har|skal|b[øo]r|m[åa]|kan|vil|gj[øo]r|blir|ble|brukes|"
    r"provides?|ensures?|reduces?|connects?|applies|serves?|prevents?|requires?|"
    r"gir|sikrer|reduserer|kobles|brukes|hindrer|krever|utf[øo]res)\b", re.I)

# All-caps runs and heading fragments.
HEADING_LIKE = re.compile(r"^[A-ZÆØÅ\s\d.:-]{8,}$")

# Default vocab when filling known section keys (not a document schema).
SECTION_TERMS: dict[str, tuple[str, ...]] = {
    "installation": (
        "install", "installation", "mount", "mounting", "assembly", "monter",
        "montage", "shield", "shielding", "earthing", "bonding", "tray", "cable",
        "connect", "torque", "fasten", "wiring",
    ),
    "operation": ("operate", "operation", "bruk", "drift", "commission", "use"),
    "maintenance": ("maintenance", "inspection", "vedlikehold", "service", "inspect"),
    "safety": ("safety", "hazard", "warning", "ppe", "sikkerhet", "fare"),
    "description": ("system", "product", "component", "overview", "cable", "tray"),
    "technical_data": ("attenuation", "db", "spec", "rating", "voltage", "frequency"),
    "shielding": ("shield", "shielding", "screen", "cable", "attenuation", "bond"),
}


@dataclass
class TieredSentence:
    id: str
    text: str
    tier: Tier
    source: str = ""
    reason: str = ""                 # why rejected, or which pattern matched
    claim_type: str = ""             # only for strong
    topic_overlap: int = 0

    @property
    def citable(self) -> bool:
        return self.tier in ("strong", "candidate")

    def provenance(self, *, lang: str = "no") -> str:
        """What may honestly be said about where this came from."""
        if self.tier == "strong" and self.claim_type:
            return (f"{self.claim_type} fra {self.source}" if lang.startswith("no")
                    else f"{self.claim_type} from {self.source}")
        return (f"nevnt i {self.source}" if lang.startswith("no")
                else f"appears in {self.source}")

    def to_dict(self) -> dict[str, Any]:
        d = {
            "id": self.id, "text": self.text, "tier": self.tier,
            "source": self.source, "citable": self.citable,
        }
        for k in ("reason", "claim_type"):
            if getattr(self, k):
                d[k] = getattr(self, k)
        if self.topic_overlap:
            d["topic_overlap"] = self.topic_overlap
        return d


@dataclass
class TierReport:
    sentences: list[TieredSentence] = field(default_factory=list)

    def of(self, tier: str) -> list[TieredSentence]:
        return [s for s in self.sentences if s.tier == tier]

    @property
    def citable(self) -> list[TieredSentence]:
        return [s for s in self.sentences if s.citable]

    def rejection_reasons(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for s in self.of("rejected"):
            out[s.reason] = out.get(s.reason, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))

    def summary(self, *, lang: str = "no") -> str:
        strong, cand, rej = len(self.of("strong")), len(self.of("candidate")), len(self.of("rejected"))
        total = len(self.sentences)
        if lang.startswith("no"):
            return (f"{total} setninger: {strong} sterke, {cand} kandidater, "
                    f"{rej} forkastet — {strong + cand} kan brukes")
        return (f"{total} sentences: {strong} strong, {cand} candidate, "
                f"{rej} rejected — {strong + cand} usable")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "total": len(self.sentences),
            "strong": len(self.of("strong")),
            "candidate": len(self.of("candidate")),
            "rejected": len(self.of("rejected")),
            "rejection_reasons": self.rejection_reasons(),
            "sentences": [s.to_dict() for s in self.sentences],
        }


# ----------------------------------------------------------------------
def tier_sentences(
    sentences: Sequence[str],
    *,
    source: str = "",
    strong_ids: Mapping[str, str] | None = None,
    topics: Iterable[str] = (),
) -> TierReport:
    """Sort sentences into three tiers.

    ``strong_ids`` maps sentence text to a claim type, so a caller that has
    already run ``foldok_claims`` can mark those without re-running the patterns.
    ``topics`` is the corpus vocabulary — a candidate has to be *about something*,
    or the document fills with true but irrelevant prose.
    """
    strong_ids = strong_ids or {}
    topic_terms = {t.lower() for t in topics}
    report = TierReport()

    for raw in sentences:
        text = re.sub(r"\s+", " ", raw or "").strip()
        if not text:
            continue
        sid = hashlib.sha1(f"{source}|{text}".encode()).hexdigest()[:12]

        matched = _strong_match(text, strong_ids)
        if matched:
            report.sentences.append(TieredSentence(
                id=sid, text=text, tier="strong", source=source,
                claim_type=matched, reason=f"matched {matched}",
            ))
            continue

        rejection = _reject_reason(text)
        if rejection:
            report.sentences.append(TieredSentence(
                id=sid, text=text, tier="rejected", source=source, reason=rejection,
            ))
            continue

        overlap = len(_terms(text) & topic_terms) if topic_terms else 0
        if topic_terms and overlap == 0:
            report.sentences.append(TieredSentence(
                id=sid, text=text, tier="rejected", source=source,
                reason="not about any topic in this corpus",
            ))
            continue

        report.sentences.append(TieredSentence(
            id=sid, text=text, tier="candidate", source=source,
            topic_overlap=overlap, reason="well-formed, no pattern matched",
        ))

    return report


def _strong_match(text: str, strong_ids: Mapping[str, str]) -> str:
    key = re.sub(r"\s+", " ", text).strip()
    if key in strong_ids:
        return strong_ids[key]
    for claim_text, claim_type in strong_ids.items():
        if claim_text and (claim_text in key or key in claim_text):
            return claim_type
    return ""


def _reject_reason(text: str) -> str:
    """Everything a document should never contain, and why."""
    for name, pattern in REJECT:
        if pattern.search(text):
            return name

    words = text.split()
    if len(words) < MIN_WORDS:
        return "too short to be a statement"
    if len(words) > MAX_WORDS:
        return "too long — probably several sentences joined"
    if not SENTENCE_END.search(text):
        return "does not end as a sentence — likely a fragment"
    if HEADING_LIKE.match(text):
        return "reads as a heading, not prose"
    if not HAS_VERB.search(text):
        return "no verb — a label or a list item"

    letters = sum(1 for c in text if c.isalpha() or c.isspace())
    if letters / max(1, len(text)) < MIN_LETTER_SHARE:
        return "mostly digits and symbols — a table row or a code"

    # A line with many single characters is a broken heading: "T E C H N I C A L"
    singles = sum(1 for w in words if len(w) == 1)
    if singles > len(words) / 3:
        return "letter-spaced text — a display heading"
    return ""


def _terms(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-zÀ-ÿÆØÅæøå]{4,}", text or "")}


def section_terms(section_key: str, *extra: str) -> list[str]:
    """Vocabulary for ``fill_section`` from a known section key + extras."""
    base = SECTION_TERMS.get((section_key or "").strip().lower(), ())
    return list(dict.fromkeys([*base, *(e for e in extra if e)]))


# ----------------------------------------------------------------------
def fill_section(
    report: TierReport,
    *,
    section_terms: Iterable[str],
    want: int = 6,
    allow_candidates: bool = True,
) -> list[TieredSentence]:
    """Strong first, candidates only to fill a thin section.

    This is the whole behaviour change: a section that would have been empty gets
    real descriptive prose, and a section with enough requirements is unaffected.
    """
    wanted = {t.lower() for t in section_terms}

    def relevance(s: TieredSentence) -> int:
        return len(_terms(s.text) & wanted)

    strong = sorted(
        (s for s in report.of("strong") if relevance(s)),
        key=lambda s: -relevance(s),
    )
    if len(strong) >= want or not allow_candidates:
        return strong[:want]

    candidates = sorted(
        (s for s in report.of("candidate") if relevance(s)),
        key=lambda s: -relevance(s),
    )
    return (strong + candidates)[:want]


def compare(report: TierReport, *, section_terms: Iterable[str], want: int = 6) -> dict[str, Any]:
    """The experiment, as a number rather than an impression."""
    strict = fill_section(report, section_terms=section_terms, want=want,
                          allow_candidates=False)
    loose = fill_section(report, section_terms=section_terms, want=want)
    return {
        "strict": len(strict),
        "loose": len(loose),
        "added": len(loose) - len(strict),
        "would_be_empty": len(strict) == 0 and len(loose) > 0,
        "added_texts": [s.text[:90] for s in loose if s not in strict][:4],
    }
