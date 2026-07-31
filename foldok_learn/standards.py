"""Reading a standard the user uploaded — the obligations, never the text.

The distinction this whole file turns on:

    You cannot keep what a standard **says**.
    You can keep what it **requires**.

The sentence "Every final circuit shall be subjected to an insulation
resistance measurement" is copyrighted text belonging to the standards body,
and selling access to it is their entire business.  The *fact* that §6-61
obliges an insulation resistance measurement, per circuit, is a fact about the
world, and encoding it with a citation is what compliance software has always
been.

So what leaves this module is: a clause identifier, an obligation strength, the
kind of artefact required, how often it repeats, and a confidence.  Never a
sentence.  ``quote_length`` records how long the source sentence was — a number
— so a reviewer can judge whether the extraction looks plausible without the
text being stored to judge it against.

Everything produced is born ``local_only``.  The user may hold a licence to read
the standard on their machine; that is not a licence for Foldok to redistribute
a derivative of it, and ``foldok_assets.seal()`` refuses to package these.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from .model import ClauseFinding

# Clause identifiers across the styles Foldok's users actually meet.
CLAUSE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"§\s?(\d{1,3}(?:[-–.]\d{1,3}){0,3})"),                    # NEK / FEL: §6-61
    re.compile(r"\b(?:clause|section|punkt|avsnitt)\s+(\d{1,2}(?:\.\d{1,3}){1,3})\b", re.I),
    re.compile(r"\b(Annex|Vedlegg|Appendix)\s+([IVXLC]{1,5}|[A-Z])\b"),   # Annex II
    re.compile(r"^\s*(\d{1,2}(?:\.\d{1,3}){1,3})\s+\S", re.M),           # ISO: 6.1.2 Heading
)

OBLIGATION = (
    ("shall", re.compile(r"\b(shall|must|is required to|skal|må)\b", re.I)),
    ("should", re.compile(r"\b(should|is recommended|bør|anbefales)\b", re.I)),
    ("may", re.compile(r"\b(may|can|kan)\b", re.I)),
)

ARTIFACT = (
    ("measurement", re.compile(
        r"\b(measur\w*|test(?:ed|ing|s)?|verif\w*|m[åa]l(?:e|ing|es)?|prøv\w*|"
        r"kontrollmål\w*|resistance|impedance|continuity|isolasjonsmotstand)\b", re.I)),
    ("photo", re.compile(
        r"\b(photograph\w*|photo|image|fotografer\w*|bilde\w*|visual\w* record\w*)\b", re.I)),
    ("signature", re.compile(
        r"\b(sign(?:ed|ature|atory)?|declaration of conformity|samsvarserklæring|"
        r"underskr\w*|attest\w*)\b", re.I)),
    ("document", re.compile(
        r"\b(record\w*|document\w*|register\w*|log(?:ged|ging)?|dokumenter\w*|"
        r"journalfør\w*|drawing\w*|tegning\w*|schedule)\b", re.I)),
)

SCOPE = (
    ("circuit", re.compile(r"\b(each|every|per|hver|hvert|pr\.?)\s+(final\s+)?(circuit|kurs|kret\w*)\b", re.I)),
    ("machine", re.compile(r"\b(each|every|per|hver|hvert)\s+(machine|maskin\w*|equipment item)\b", re.I)),
    ("board", re.compile(r"\b(each|every|per|hver|hvert)\s+(board|tavle\w*|distribution board|panel)\b", re.I)),
    ("cage", re.compile(r"\b(each|every|per|hver|hvert)\s+(cage|merd\w*|pen)\b", re.I)),
    ("joint", re.compile(r"\b(each|every|per|hver|hvert)\s+(joint|weld|sveis\w*|skjøt\w*)\b", re.I)),
    ("room", re.compile(r"\b(each|every|per|hver|hvert)\s+(room|rom\b|space)\b", re.I)),
)

SENTENCE = re.compile(r"[^.!?\n]{20,400}[.!?]")


@dataclass
class Extraction:
    findings: list[ClauseFinding]
    sentences_scanned: int = 0
    with_obligation: int = 0
    source: str = ""

    @property
    def evidential(self) -> list[ClauseFinding]:
        return [f for f in self.findings if f.evidential]

    def summary(self) -> str:
        kinds: dict[str, int] = {}
        for f in self.findings:
            kinds[f.artifact] = kinds.get(f.artifact, 0) + 1
        bits = ", ".join(f"{v} {k}" for k, v in sorted(kinds.items(), key=lambda kv: -kv[1]))
        return (
            f"{len(self.findings)} obligation(s) from {self.sentences_scanned} sentence(s)"
            + (f" — {bits}" if bits else "")
        )


def extract(text: str, *, source: str = "", min_confidence: float = 0.35) -> Extraction:
    """Find obligations. Returns citations and kinds; keeps no sentence.

    Walks the text line by line because in a standard the clause identifier is
    usually a heading on its own line and the obligation is in the paragraph
    beneath it. Reading only complete sentences would miss every heading and
    therefore every citation.
    """
    findings: list[ClauseFinding] = []
    seen: set[tuple[str, str]] = set()
    scanned = 0
    with_obligation = 0
    current_clause = ""

    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        found = _clause_in(stripped)
        if found:
            current_clause = found

        pieces = SENTENCE.findall(stripped) or ([stripped] if len(stripped) > 15 else [])
        for sentence in pieces:
            scanned += 1
            obligation = _first(OBLIGATION, sentence)
            if obligation is None:
                continue
            with_obligation += 1
            clause = _clause_in(sentence) or current_clause
            if not clause:
                continue

            artifact = _first(ARTIFACT, sentence) or "text"
            per = _first(SCOPE, sentence) or "document"
            confidence = _confidence(obligation, artifact, per, bool(_clause_in(sentence)))
            if confidence < min_confidence:
                continue

            key = (clause, artifact)
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                ClauseFinding(
                    clause=clause,
                    obligation=obligation,          # type: ignore[arg-type]
                    artifact=artifact,
                    per=per,
                    confidence=confidence,
                    evidence_source=source,
                    quote_length=len(sentence.strip()),
                )
            )

    findings.sort(key=lambda f: (-f.confidence, f.clause, f.artifact))
    return Extraction(
        findings=findings,
        sentences_scanned=scanned,
        with_obligation=with_obligation,
        source=source,
    )


def extract_from_chunks(chunks: Iterable[Any], *, source: str = "") -> Extraction:
    """Convenience for a ``foldok_index`` document: chunks in, obligations out."""
    parts: list[str] = []
    for chunk in chunks:
        parts.append(getattr(chunk, "text", "") or "")
    return extract("\n".join(parts), source=source)


# ----------------------------------------------------------------------
def to_requirements(
    findings: Sequence[ClauseFinding],
    *,
    standard: str,
    section_for: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Turn findings into ``foldok_gaps`` requirement dicts.

    Titles are generated from the obligation, not copied from the standard —
    "Insulation resistance measurement (§6-61)" is Foldok's wording about a
    clause, which is the whole point.
    """
    section_for = section_for or {
        "measurement": "verification",
        "photo": "installation",
        "signature": "handover",
        "document": "drawings",
        "text": "description",
    }
    label = {
        "measurement": "Measurement required",
        "photo": "Photographic record required",
        "signature": "Signature required",
        "document": "Record required",
        "text": "Statement required",
    }
    out: list[dict[str, Any]] = []
    for f in findings:
        key = f"local.{_slug(standard)}.{_slug(f.clause)}.{f.artifact}"
        out.append(
            {
                "key": key,
                "section": section_for.get(f.artifact, "description"),
                "title": f"{label[f.artifact]} ({f.clause})",
                "kind": f.artifact if f.artifact != "document" else "file",
                "evidence": "evidential" if f.evidential else "expository",
                "per": f.per,
                "severity": f.severity,
                "authority": f"{standard} {f.clause}",
                "description": (
                    f"Detected from {standard} {f.clause}. Confirm the wording against your "
                    "copy of the standard before relying on it."
                ),
                "allow_not_applicable": f.obligation != "shall",
                "tags": ["local", "extracted"],
            }
        )
    return out


def _clause_in(sentence: str) -> str:
    for pattern in CLAUSE_PATTERNS:
        m = pattern.search(sentence)
        if m:
            groups = [g for g in m.groups() if g]
            return " ".join(groups) if len(groups) > 1 else f"§{groups[0]}"
    return ""


def _first(table: tuple[tuple[str, re.Pattern[str]], ...], sentence: str) -> str | None:
    for name, pattern in table:
        if pattern.search(sentence):
            return name
    return None


def _confidence(obligation: str, artifact: str, per: str, explicit_clause: bool) -> float:
    score = 0.3
    score += {"shall": 0.35, "should": 0.2, "may": 0.05}[obligation]
    if artifact != "text":
        score += 0.2
    if per != "document":
        score += 0.1
    if explicit_clause:
        score += 0.1
    return min(1.0, round(score, 2))


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")[:40] or "x"
