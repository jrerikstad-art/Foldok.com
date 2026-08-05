"""Claim extraction — deterministic, bilingual, and honest about confidence.

Patterns first, for the same reason as everywhere else in this product: a regex
that misses is a bug you fix once, and a model that misses comes back with
different wording next week. A model is worth calling to *classify borderline
sentences*, not to decide what a claim is.

What each pattern family is looking for:

    rule            skal / shall / må / must / påkrevd / required
    constraint      maksimalt / minst / ikke mer enn / at most / no more than
    practice        bør / should / anbefales / preferred / foretrukket
    definition      X er Y / X is defined as / X beskriver
    classification  Klasse N omfatter / Class N covers
    hypothesis      kan / may / antas / hypotese / foreløpig
    risk            risiko / kan føre til / can cause / vanskelig å
    distinction     skille mellom / differs from / i motsetning til

Scope is lifted separately — a frequency band or a cable class attaches to the
claim rather than sitting inside its text, because that is what makes two claims
comparable later.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Sequence

from .model import Claim, ClaimSet, ClaimType, Modality, Quantity, Scope, claim_id

# --- scope -------------------------------------------------------------
UNIT_SCALE = {
    "hz": 1.0, "khz": 1e3, "mhz": 1e6, "ghz": 1e9,
    "db": 1.0, "mm": 1.0, "m": 1.0, "kv": 1e3, "v": 1.0, "a": 1.0, "ma": 1e-3,
}
FREQ_RANGE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(hz|khz|mhz|ghz)?\s*(?:[-–—]|til|to)\s*(\d+(?:[.,]\d+)?)\s*(hz|khz|mhz|ghz)",
    re.I,
)
FREQ_FROM_DC = re.compile(r"\b(?:dc|likestr[øo]m)\s*(?:[-–—]|til|to)\s*(\d+(?:[.,]\d+)?)\s*(hz|khz|mhz|ghz)", re.I)
CLASS_REF = re.compile(r"\bklasse\s*(\d[ab]?)\b|\bclass\s*(\d[ab]?)\b", re.I)
DB_RANGE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:[-–—]|til|to)\s*(\d+(?:[.,]\d+)?)\s*db\b", re.I
)
SINGLE_QTY = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*(db|ghz|mhz|khz|hz|kv|mm|grader|degrees?|gjenger|threads?)\b", re.I
)

# --- claim families ----------------------------------------------------
PATTERNS: tuple[tuple[ClaimType, Modality, re.Pattern[str]], ...] = (
    ("rule", "shall", re.compile(
        r"\b(skal|må|er p[åa]krevd|kreves|krever|er obligatorisk|shall|must|is required|"
        # "er kritisk" and "er avgjørende" are obligations in engineering prose
        # even without a modal verb, and the EMC notes use them that way.
        # Norwegian puts the predicate adjective at the end — "er skjermede
        # kabler og bonding kritisk" — so requiring "er kritisk" adjacently
        # missed every one of them. These adjectives mark an obligation on their
        # own in engineering prose.
        r"are required|is mandatory|kritisk|avgj[øo]rende|obligatorisk|"
        r"is critical|is essential|mandatory)\b",
        re.I)),
    ("constraint", "shall", re.compile(
        r"\b(maksimalt|maks\.?|minst|ikke mer enn|ikke under|h[øo]yst|at most|no more than|"
        r"at least|not exceed|kun tillatt)\b", re.I)),
    ("practice", "should", re.compile(
        r"\b(b[øo]r|anbefales|er foretrukket|foretrekkes|best practice|should|"
        r"is preferred|recommended)\b", re.I)),
    ("hypothesis", "hypothesis", re.compile(
        r"\b(hypotese|antas|kan ha|kan i visse|kan gi|forel[øo]pig|det er begrenset|"
        r"har direkte korrelasjon|correlates directly|"
        r"hypothesis|may have|might|is assumed|preliminary|limited evidence)\b", re.I)),
    ("risk", "is", re.compile(
        # An adverb between "er" and "vanskelig" was enough to hide these:
        # "er ekstremt vanskelig å lokalisere" matched nothing.
        r"\b(risiko|kan f[øo]re til|kan medf[øo]re|vanskelig\s+[åa]|svekke|erstatningskrav|"
        r"ikke m[åa]lbar|ikke m[åa]lbare|risk|can cause|may lead to|difficult to|"
        r"not measurable|liability)\b", re.I)),
    ("distinction", "is", re.compile(
        r"\b(skille mellom|i motsetning til|forskjellen mellom|distinguish between|"
        r"differs from|as opposed to|versus|"
        # A stated inadequacy is a claim worth keeping: "armering alene er en
        # dårlig skjerm for høye frekvenser" is exactly the kind of sentence a
        # quantity schema throws away.
        r"alene er en d[åa]rlig|er ikke tilstrekkelig|alene er ikke|"
        r"is a poor|is not sufficient|alone is not)\b", re.I)),
    ("classification", "is", re.compile(
        r"\b(klasse\s*\d[ab]?\s*(?:gjelder|omfatter|dekker)|class\s*\d[ab]?\s*(?:covers|applies))",
        re.I)),
    ("definition", "is", re.compile(
        r"\b(beskriver|defineres som|er definert som|betyr|is defined as|describes|means)\b",
        re.I)),
    ("reference", "is", re.compile(
        r"\b(verifiseres mot|i henhold til|testet til|according to|tested to|"
        r"in accordance with|per)\s+([A-Z]{2,}[\w\s\-:/]{2,30}\d)", re.I)),
)

CLASSIFICATION_ALSO = re.compile(
    r"\b(klasse\s*\d[ab]?\s*(?:gjelder|omfatter|dekker)|"
    r"class\s*\d[ab]?\s*(?:covers|applies|includes))", re.I
)

QUANTITY_CLAIM = re.compile(
    r"\b(er|is|are|har|has|m[åa]les|measured|oppn[åa]s|achieves?|yields?|"
    r"attenuation|demping|capability|kapasitet)\b", re.I
)

NEGATION = re.compile(
    r"\b(ikke|aldri|d[åa]rlig|utilstrekkelig|kan ikke|not|never|poor|inadequate|cannot)\b", re.I
)

# Sentences that are never claims: contact details, marketing, navigation.
NOISE = re.compile(
    r"(\+\d{2,}[\d\s]{6,})|([\w.+-]+@[\w-]+\.\w{2,})|(https?://)|"
    r"\b(kontakt oss|contact us|les mer|read more|copyright|all rights reserved)\b",
    re.I,
)

SENTENCE = re.compile(r"[^.!?\n]{25,400}[.!?]|^[^\n]{25,200}$", re.M)


@dataclass
class Extraction:
    claims: ClaimSet
    sentences: int = 0
    skipped_noise: int = 0
    source: str = ""

    def summary(self) -> str:
        counts = ", ".join(f"{v} {k}" for k, v in self.claims.counts().items())
        return (
            f"{len(self.claims)} claim(s) from {self.sentences} sentence(s)"
            + (f" — {counts}" if counts else "")
            + (f"; {self.skipped_noise} noise sentence(s) dropped" if self.skipped_noise else "")
        )


def extract(text: str, *, source: str = "", min_confidence: float = 0.4) -> Extraction:
    claims: list[Claim] = []
    seen: set[str] = set()
    sentences = _sentences(text)
    noise = 0

    for sentence in sentences:
        if NOISE.search(sentence):
            noise += 1
            continue
        scope = _scope(sentence)
        subject = _subject(sentence)
        for claim_type, modality, pattern in PATTERNS:
            if not pattern.search(sentence):
                continue
            quantity = _quantity(sentence)
            confidence = _confidence(claim_type, sentence, scope, quantity)
            if confidence < min_confidence:
                continue
            cid = claim_id(source, sentence)
            if cid in seen:
                break
            seen.add(cid)
            claims.append(
                Claim(
                    id=cid,
                    type=claim_type,
                    subject=subject,
                    text=_tidy(sentence),
                    modality=modality,
                    predicate=_predicate(sentence),
                    quantity=quantity,
                    scope=scope,
                    source=source,
                    negated=bool(NEGATION.search(sentence)),
                    confidence=confidence,
                )
            )
            # A sentence can legitimately be two claims: "Klasse 1B omfatter
            # Ethernet ... skjermet kabel kreves" both defines the class and
            # states its requirement. Losing the classification is what left the
            # cable-class section empty.
            if claim_type == "classification":
                break
            second = CLASSIFICATION_ALSO.search(sentence)
            if second:
                extra_id = claim_id(source, "class::" + sentence)
                if extra_id not in seen:
                    seen.add(extra_id)
                    claims.append(
                        Claim(
                            id=extra_id, type="classification", subject=subject,
                            text=_tidy(sentence), modality="is",
                            predicate=_predicate(sentence), quantity=quantity,
                            scope=scope, source=source,
                            confidence=max(0.5, confidence - 0.05),
                        )
                    )
            break
        else:
            # No family matched. If the sentence carries a measured value it is
            # still a claim — the kind a datasheet is made of.
            quantity = _quantity(sentence)
            if quantity is None or not QUANTITY_CLAIM.search(sentence):
                continue
            cid = claim_id(source, sentence)
            if cid in seen:
                continue
            seen.add(cid)
            claims.append(
                Claim(
                    id=cid, type="quantity", subject=subject, text=_tidy(sentence),
                    modality="is", predicate=_predicate(sentence), quantity=quantity,
                    scope=scope, source=source,
                    negated=bool(NEGATION.search(sentence)),
                    confidence=_confidence("quantity", sentence, scope, quantity),
                )
            )

    return Extraction(claims=ClaimSet(claims), sentences=len(sentences),
                      skipped_noise=noise, source=source)


def extract_many(documents: Iterable[tuple[str, str]]) -> ClaimSet:
    """``[(source_id, text), ...]`` -> one claim set across the library."""
    out: list[Claim] = []
    for source, text in documents:
        out.extend(extract(text, source=source).claims.claims)
    return ClaimSet(out)


# ----------------------------------------------------------------------
def _sentences(text: str) -> list[str]:
    """Split into claim candidates.

    Prefer ``foldok_reflow``: PDF extractors emit visual rows, and a newline-based
    splitter turns one sentence into four unusable fragment claims.
    """
    raw = (text or "").replace("\r\n", "\n")
    try:
        from foldok_reflow import reflow, split_sentences as reflow_split
        body = reflow(raw).text or raw
        sents = [s.strip() for s in reflow_split(body) if len(s.strip()) >= 25]
        if sents:
            return sents
    except Exception:  # noqa: BLE001 - fall through to legacy splitter
        pass
    out: list[str] = []
    for line in raw.split("\n"):
        stripped = line.strip(" \t*-•")
        if len(stripped) < 25:
            continue
        found = SENTENCE.findall(stripped)
        pieces = [p for p in (found if isinstance(found, list) else []) if isinstance(p, str) and p.strip()]
        out.extend(p.strip() for p in pieces) if pieces else out.append(stripped)
    return out


def _scope(sentence: str) -> Scope:
    freq: Quantity | None = None
    m = FREQ_RANGE.search(sentence)
    if m:
        lo_unit = (m.group(2) or m.group(4)).lower()
        freq = Quantity(
            low=_scale(m.group(1), lo_unit), high=_scale(m.group(3), m.group(4).lower()),
            unit="Hz", raw=m.group(0),
        )
    else:
        m = FREQ_FROM_DC.search(sentence)
        if m:
            freq = Quantity(low=0.0, high=_scale(m.group(1), m.group(2).lower()),
                            unit="Hz", raw=m.group(0))
    klass = ""
    m = CLASS_REF.search(sentence)
    if m:
        klass = (m.group(1) or m.group(2) or "").upper()
    return Scope(frequency=freq, cable_class=klass)


def _quantity(sentence: str) -> Quantity | None:
    m = DB_RANGE.search(sentence)
    if m:
        return Quantity(low=_f(m.group(1)), high=_f(m.group(2)), unit="dB", raw=m.group(0))
    m = SINGLE_QTY.search(sentence)
    if m:
        unit = m.group(2).lower()
        unit = {"grader": "deg", "degrees": "deg", "degree": "deg",
                "gjenger": "threads", "thread": "threads"}.get(unit, unit)
        value = _f(m.group(1))
        if unit in ("hz", "khz", "mhz", "ghz"):
            return Quantity(low=_scale(m.group(1), unit), high=_scale(m.group(1), unit),
                            unit="Hz", raw=m.group(0))
        return Quantity(low=value, high=value, unit=unit.upper() if unit == "db" else unit,
                        raw=m.group(0))
    return None


def _subject(sentence: str) -> str:
    """First noun-ish phrase. Crude, and better than nothing for grouping."""
    words = re.findall(r"[A-Za-zÀ-ÿÆØÅæøå0-9\-/]+", sentence)
    if not words:
        return ""
    stop = {"det", "en", "et", "the", "a", "an", "for", "i", "av", "og", "som", "vi", "må",
            "skal", "er", "kan", "alle", "all", "this", "these", "der", "til"}
    head = [w for w in words[:9] if w.lower() not in stop]
    return " ".join(head[:4]) or words[0]


def _predicate(sentence: str) -> str:
    for word, name in (
        ("skjerm", "shielding"), ("shield", "shielding"), ("demping", "attenuation"),
        ("attenuation", "attenuation"), ("jording", "earthing"), ("bonding", "bonding"),
        ("separasjon", "separation"), ("separation", "separation"), ("radius", "geometry"),
        ("radier", "geometry"), ("korona", "corona"), ("corona", "corona"),
        ("emc", "emc"), ("emi", "emi"), ("st[øo]y", "noise"), ("noise", "noise"),
    ):
        if re.search(word, sentence, re.I):
            return name
    return ""


def _confidence(claim_type: str, sentence: str, scope: Scope, quantity: Quantity | None) -> float:
    score = 0.45
    if claim_type in ("rule", "constraint"):
        score += 0.2
    if scope.known:
        score += 0.15
    if quantity is not None:
        score += 0.1
    if len(sentence) > 220:
        score -= 0.1
    return max(0.0, min(0.95, round(score, 2)))


def _tidy(sentence: str) -> str:
    return re.sub(r"\s+", " ", sentence).strip()


def _f(text: str) -> float:
    return float(str(text).replace(",", "."))


def _scale(text: str, unit: str) -> float:
    return _f(text) * UNIT_SCALE.get((unit or "hz").lower(), 1.0)
