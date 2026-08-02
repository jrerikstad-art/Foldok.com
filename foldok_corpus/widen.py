"""Wider extraction — because the document can only be as diverse as the claims.

``foldok_claims`` recognises ten types, and every one of them is propositional:
quantity, definition, classification, rule, constraint, practice, distinction,
hypothesis, risk, reference. All answer *"what is true?"*

That is why five documents from one folder came out looking alike. A section can
only be about something the extractor can see, so no matter how the sections are
chosen, they are all built from statements of fact about the same subject. The
template was blamed; the vocabulary was the ceiling.

Engineering folders contain other kinds of content entirely, and each supports a
*different kind of section*:

    decision      "vi valgte lukkede baner framfor trådstiger"     -> rationale
    problem       "korrosjon i skjøtene ble oppdaget i mai"         -> issues log
    consequence   "dette gir 40 mm større bøyeradius"               -> impact
    condition     "ved temperaturer under -20 °C gjelder ikke"      -> limits
    responsibility "leverandøren skal levere sertifikat"            -> RACI
    change        "revidert fra 4 mm² til 6 mm² i rev C"            -> revision log
    open_question "ikke avklart om kabelbro skal jordes i begge"    -> open items
    exception     "unntatt sone 2 der kravet ikke gjelder"          -> deviations
    sequence      "etter at kabelbroen er montert, trekkes kabel"   -> procedure
    justification "fordi armering alene skjermer dårlig ved HF"     -> reasoning

Ten more types, none of them a statement of fact, and every one of them the seed
of a section a fact-only extractor cannot produce.

Deterministic patterns, bilingual, same discipline as the rest: a regex that
misses is a bug fixed once.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal, Mapping, Sequence

SCHEMA_VERSION = 1

WideType = Literal[
    "decision", "problem", "consequence", "condition", "responsibility",
    "change", "open_question", "exception", "sequence", "justification",
]

# What kind of section each type feeds. This is the whole point: extraction
# variety is what widens the range of documents a folder can support.
FEEDS_SECTION: dict[str, tuple[str, str]] = {
    "decision":       ("Valg og begrunnelse", "Decisions and rationale"),
    "problem":        ("Problemer og funn", "Problems and findings"),
    "consequence":    ("Konsekvenser", "Consequences"),
    "condition":      ("Forutsetninger og gyldighet", "Conditions and validity"),
    "responsibility": ("Ansvar og roller", "Responsibilities"),
    "change":         ("Endringslogg", "Change log"),
    "open_question":  ("Åpne punkter", "Open items"),
    "exception":      ("Avvik og unntak", "Deviations and exceptions"),
    "sequence":       ("Rekkefølge og fremdrift", "Sequence"),
    "justification":  ("Begrunnelse", "Reasoning"),
}

PATTERNS: tuple[tuple[WideType, re.Pattern[str]], ...] = (
    ("decision", re.compile(
        r"\b(vi valgte|det ble valgt|valget falt p[åa]|besluttet|vedtatt|"
        r"framfor|fremfor|i stedet for|we chose|it was decided|selected|"
        r"opted for|instead of|rather than)\b", re.I)),
    ("change", re.compile(
        r"\b(revidert fra|endret fra|oppdatert fra|erstattet med|tidligere var|"
        r"i rev(?:isjon)?\s*[A-Z0-9]|changed from|revised from|superseded by|"
        r"previously|updated from|was\s+\S+\s+now)\b", re.I)),
    ("open_question", re.compile(
        r"\b(ikke avklart|uavklart|m[åa] avklares|gjenst[åa]r [åa]|til vurdering|"
        r"tbc\b|tbd\b|to be confirmed|to be decided|not yet (?:clear|decided|agreed)|"
        r"open (?:point|item|question)|remains to be)\b", re.I)),
    ("exception", re.compile(
        r"\b(unntatt|med unntak av|gjelder ikke for|fritatt|dispensasjon|"
        r"avvik fra|except(?:ed)? for|does not apply to|exempt|waiver|"
        r"deviation from)\b", re.I)),
    ("responsibility", re.compile(
        r"\b(?:leverand[øo]ren|entrepren[øo]ren|byggherren|kunden|"
        r"the supplier|the contractor|the client|the owner)\s+"
        r"(?:skal|m[åa]|er ansvarlig|shall|must|is responsible)\b|"
        r"\b(ansvarlig for|har ansvaret for|responsible for|accountable for)\b", re.I)),
    ("problem", re.compile(
        r"\b(ble oppdaget|viste seg|feilet|sviktet|korrosjon|skade|mangel ved|"
        r"problem(?:et)? med|utfordring|was discovered|turned out|failed|"
        r"defect|damage|issue with|shortcoming)\b", re.I)),
    ("condition", re.compile(
        r"\b(forutsatt at|gitt at|dersom|ved temperaturer|ved forhold|"
        r"gjelder kun|kun n[åa]r|betinget av|provided that|assuming|"
        r"only (?:when|if|where)|subject to|valid for)\b", re.I)),
    ("consequence", re.compile(
        r"\b(dette (?:gir|medf[øo]rer|f[øo]rer til|betyr)|som f[øo]lge av|"
        r"konsekvensen er|resulterer i|derfor m[åa]|this (?:gives|means|leads to)|"
        r"as a result|consequently|resulting in|therefore)\b", re.I)),
    ("sequence", re.compile(
        r"\b(etter at|f[øo]r (?:kabel|montering|installasjon)|deretter|"
        r"til slutt|f[øo]rste steg|neste steg|after (?:the|installation)|"
        r"once the|then the|finally|first step|next step|prior to)\b", re.I)),
    ("justification", re.compile(
        r"\b(fordi|siden|begrunnelsen er|[åa]rsaken er|dette skyldes|"
        r"because|since the|the reason is|this is due to|on the grounds)\b", re.I)),
)

# Sentences that carry no content worth a section.
NOISE = re.compile(
    r"(\+\d{2,}[\d\s]{6,})|([\w.+-]+@[\w-]+\.\w{2,})|(https?://)|"
    r"\b(subject to change|all rights reserved|copyright|side \d+ av \d+|page \d+ of \d+)\b",
    re.I,
)


@dataclass
class WideClaim:
    id: str
    type: WideType
    text: str
    source: str = ""
    subject: str = ""
    confidence: float = 0.55

    @property
    def section_hint(self) -> tuple[str, str]:
        return FEEDS_SECTION[self.type]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "type": self.type, "text": self.text,
            "source": self.source, "subject": self.subject,
            "confidence": round(self.confidence, 2),
            "feeds": self.section_hint[0],
        }


@dataclass
class WideExtraction:
    claims: list[WideClaim] = field(default_factory=list)
    sentences: int = 0

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for c in self.claims:
            out[c.type] = out.get(c.type, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))

    def of_type(self, *types: str) -> list[WideClaim]:
        return [c for c in self.claims if c.type in types]

    def summary(self, *, lang: str = "no") -> str:
        counts = ", ".join(f"{v} {k}" for k, v in self.counts().items())
        if lang.startswith("no"):
            return f"{len(self.claims)} utsagn utover fakta" + (f" — {counts}" if counts else "")
        return f"{len(self.claims)} non-factual statement(s)" + (f" — {counts}" if counts else "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "count": len(self.claims),
            "counts": self.counts(),
            "claims": [c.to_dict() for c in self.claims],
        }


def extract_wide(text: str, *, source: str = "") -> WideExtraction:
    """Content that is not a statement of fact.

    Runs alongside ``foldok_claims.extract`` rather than replacing it — a
    sentence can be both a rule and a justification, and both readings feed
    different sections.
    """
    import hashlib

    out: list[WideClaim] = []
    seen: set[str] = set()
    sentences = _sentences(text)

    for sentence in sentences:
        if NOISE.search(sentence):
            continue
        for wide_type, pattern in PATTERNS:
            if not pattern.search(sentence):
                continue
            cid = hashlib.sha1(f"{source}|{wide_type}|{sentence}".encode()).hexdigest()[:12]
            if cid in seen:
                continue
            seen.add(cid)
            out.append(WideClaim(
                id=cid, type=wide_type, text=_tidy(sentence), source=source,
                subject=_subject(sentence),
                confidence=_confidence(wide_type, sentence),
            ))
            # No break: "vi valgte lukkede baner fordi armering skjermer dårlig"
            # is a decision *and* a justification, and they feed different
            # sections. Forcing one reading is what made documents look alike.

    return WideExtraction(claims=out, sentences=len(sentences))


def extract_many(documents: Iterable[tuple[str, str]]) -> WideExtraction:
    out: list[WideClaim] = []
    total = 0
    for source, text in documents:
        found = extract_wide(text, source=source)
        out.extend(found.claims)
        total += found.sentences
    return WideExtraction(claims=out, sentences=total)


# ----------------------------------------------------------------------
def _sentences(text: str) -> list[str]:
    raw = (text or "").replace("\r\n", "\n")
    out: list[str] = []
    for line in raw.split("\n"):
        stripped = line.strip(" \t*-•")
        if len(stripped) < 25:
            continue
        parts = re.split(r"(?<=[.!?])\s+", stripped)
        out.extend(p.strip() for p in parts if len(p.strip()) >= 25)
    return out


def _subject(sentence: str) -> str:
    words = re.findall(r"[A-Za-zÀ-ÿÆØÅæøå0-9\-/]+", sentence)
    stop = {"vi", "det", "en", "et", "the", "a", "we", "for", "i", "av", "og", "som", "er"}
    head = [w for w in words[:8] if w.lower() not in stop]
    return " ".join(head[:4]) or (words[0] if words else "")


def _confidence(wide_type: str, sentence: str) -> float:
    score = 0.5
    if wide_type in ("decision", "change", "exception", "open_question"):
        score += 0.15          # these have distinctive markers
    if len(sentence) > 240:
        score -= 0.1
    return max(0.2, min(0.9, round(score, 2)))


def _tidy(sentence: str) -> str:
    return re.sub(r"\s+", " ", sentence).strip()
