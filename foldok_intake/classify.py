"""Intake classification — what kind of document is this, before anything uses it.

A travel insurance certificate reached a technical documentation package: full
name, insurer, policy number and coverage dates, in a deliverable meant for a
client.  The model that wrote the section had already worked out it did not
belong and said so in the prose — because flagging it was the only action
available.  It could not remove the file.

There is an irony worth keeping in view.  ``foldok_private`` masks client and
project names on the way *out* to a model, carefully, with a leak scan and a
refusal path.  Nothing at all guarded personal data flowing *in* from the index
and *into* the document.  One boundary was built and the opposite one was left
open.

So classification happens at intake, deterministically, before mapping and
before generation:

*   Personal, financial, medical and identity documents are **excluded by
    default** and reported, never silently dropped — a user who put a file in
    the folder deserves to know it was held back.
*   Detection is patterns and paths, not a model.  A classifier that sometimes
    lets a payslip through is worse than no classifier, because it earns trust
    it cannot keep.
*   Bilingual, because the documents are.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal

SCHEMA_VERSION = 1

DocClass = Literal[
    "project",      # belongs in the documentation
    "personal",     # insurance, private correspondence, travel
    "financial",    # payslip, bank statement, tax
    "medical",      # sick note, health record
    "identity",     # passport, licence, national id
    "unknown",      # not enough signal — treated as project, but flagged
]

EXCLUDED_BY_DEFAULT: tuple[DocClass, ...] = ("personal", "financial", "medical", "identity")

# Strong content signals. Norwegian and English, because the folders are.
SIGNALS: dict[DocClass, tuple[re.Pattern[str], ...]] = {
    "personal": (
        re.compile(r"\b(reiseforsikring|forsikringsbevis|forsikringspolise|polisenummer|"
                   r"innboforsikring|husforsikring|bilforsikring|dekningsperiode)\b", re.I),
        re.compile(r"\b(travel insurance|insurance certificate|policy number|policy no\.?|"
                   r"coverage period|home insurance|car insurance)\b", re.I),
        re.compile(r"\b(leiekontrakt|husleie|privat korrespondanse|feriedager|permisjon)\b", re.I),
    ),
    "financial": (
        re.compile(r"\b(l[øo]nnsslipp|lønnslipp|kontoutskrift|skattemelding|selvangivelse|"
                   r"kontonummer|saldo|faktura til meg|skatteoppgj[øo]r)\b", re.I),
        re.compile(r"\b(payslip|pay slip|bank statement|tax return|salary statement|"
                   r"account number|IBAN)\b", re.I),
    ),
    "medical": (
        re.compile(r"\b(sykemelding|sykmelding|legeerkl[æa]ring|journal|resept|diagnose|"
                   r"helseopplysninger|fastlege)\b", re.I),
        re.compile(r"\b(sick note|medical certificate|health record|prescription|diagnosis|"
                   r"patient)\b", re.I),
    ),
    "identity": (
        re.compile(r"\b(f[øo]dselsnummer|personnummer|passnummer|f[øo]rerkort|"
                   r"identitetsbevis|bankid)\b", re.I),
        re.compile(r"\b(passport number|driving licence|driver'?s license|national id|"
                   r"social security number)\b", re.I),
        re.compile(r"\b\d{6}\s?\d{5}\b"),          # Norwegian 11-digit personal number
    ),
}

# Path signals. A folder called "Privat" is a strong statement of intent.
PATH_SIGNALS: tuple[tuple[DocClass, re.Pattern[str]], ...] = (
    ("personal", re.compile(r"(?:^|[/\\])(privat|private|personlig|personal|notater|notes|"
                            r"hjemme|home)(?:[/\\]|$)", re.I)),
    ("financial", re.compile(r"(?:^|[/\\])(l[øo]nn|salary|regnskap|accounting|skatt|tax)"
                             r"(?:[/\\]|$)", re.I)),
    ("medical", re.compile(r"(?:^|[/\\])(helse|health|lege|medical)(?:[/\\]|$)", re.I)),
)

# Signals that a document really is project material, which outweigh a weak
# path hint — a datasheet in a folder called "Notater" is still a datasheet.
PROJECT_SIGNALS = re.compile(
    r"\b(datasheet|datablad|samsvarserkl[æa]ring|declaration of conformity|"
    r"ce[- ]?merking|ce marking|typeskilt|rating plate|koblingsskjema|wiring diagram|"
    r"single[- ]line|enlinje|m[åa]leprotokoll|test report|testrapport|kalibrering|"
    r"calibration|installasjon|installation|montering|bruksanvisning|user manual|"
    r"risikovurdering|risk assessment|stykkliste|bill of materials|\bBOM\b)\b", re.I
)


@dataclass
class Classification:
    file: str                        # relative path, as the index knows it
    doc_class: DocClass = "unknown"
    confidence: float = 0.0
    reasons: tuple[str, ...] = ()
    excluded: bool = False
    override: str = ""               # set when a person decides otherwise

    @property
    def sensitive(self) -> bool:
        return self.doc_class in EXCLUDED_BY_DEFAULT

    def explain(self) -> str:
        if not self.sensitive:
            return f"{self.file}: {self.doc_class}"
        return (
            f"{self.file} looks like a {self.doc_class} document "
            f"({'; '.join(self.reasons[:2])}) and was left out of the documentation"
        )

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "file": self.file,
            "class": self.doc_class,
            "confidence": round(self.confidence, 2),
            "excluded": self.excluded,
        }
        if self.reasons:
            d["reasons"] = list(self.reasons)
        if self.override:
            d["override"] = self.override
        return d


@dataclass
class IntakeReport:
    classifications: list[Classification] = field(default_factory=list)

    @property
    def excluded(self) -> list[Classification]:
        return [c for c in self.classifications if c.excluded]

    @property
    def kept(self) -> list[Classification]:
        return [c for c in self.classifications if not c.excluded]

    def of_class(self, doc_class: str) -> list[Classification]:
        return [c for c in self.classifications if c.doc_class == doc_class]

    def notice(self, lang: str = "no") -> str:
        """What the user is told. They put the file there; they get to know."""
        if not self.excluded:
            return ""
        names = ", ".join(c.file for c in self.excluded[:4])
        more = f" (+{len(self.excluded) - 4})" if len(self.excluded) > 4 else ""
        if lang == "no":
            return (
                f"{len(self.excluded)} fil(er) ble holdt utenfor dokumentasjonen fordi de ser ut "
                f"til å være private: {names}{more}. Du kan inkludere dem manuelt hvis de "
                "likevel hører hjemme."
            )
        return (
            f"{len(self.excluded)} file(s) were kept out of the documentation because they look "
            f"personal: {names}{more}. You can include them by hand if they do belong."
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "kept": len(self.kept),
            "excluded": len(self.excluded),
            "classifications": [c.to_dict() for c in self.classifications],
        }


# ----------------------------------------------------------------------
def classify(
    file: str,
    text: str = "",
    *,
    caption: str = "",
    roles: Iterable[str] = (),
) -> Classification:
    """Deterministic. A classifier that sometimes lets a payslip through is
    worse than none, because it earns trust it cannot keep."""
    haystack = " ".join(part for part in (Path(file).name, caption, text[:4000]) if part)
    reasons: list[str] = []
    scores: dict[str, float] = {}

    for doc_class, patterns in SIGNALS.items():
        for pattern in patterns:
            hit = pattern.search(haystack)
            if hit:
                scores[doc_class] = scores.get(doc_class, 0.0) + 0.45
                reasons.append(f"contains '{hit.group(0)[:40]}'")

    for doc_class, pattern in PATH_SIGNALS:
        if pattern.search(file.replace("\\", "/")):
            scores[doc_class] = scores.get(doc_class, 0.0) + 0.3
            reasons.append(f"stored under a '{doc_class}' folder")

    project_hit = PROJECT_SIGNALS.search(haystack)
    role_hit = any(r for r in roles)
    if project_hit:
        reasons.append(f"reads as project material ('{project_hit.group(0)[:30]}')")

    if not scores:
        return Classification(
            file=file,
            doc_class="project" if (project_hit or role_hit) else "unknown",
            confidence=0.6 if project_hit else 0.2,
            reasons=tuple(reasons),
        )

    doc_class = max(scores.items(), key=lambda kv: kv[1])[0]
    confidence = min(0.95, scores[doc_class])

    # A datasheet in a folder called "Notater" is still a datasheet: strong
    # project content beats a weak path hint, but never beats explicit personal
    # content like a policy number.
    if project_hit and confidence <= 0.35:
        return Classification(
            file=file, doc_class="project", confidence=0.6,
            reasons=tuple(reasons),
        )

    return Classification(
        file=file,
        doc_class=doc_class,          # type: ignore[arg-type]
        confidence=confidence,
        reasons=tuple(reasons),
        excluded=doc_class in EXCLUDED_BY_DEFAULT,
    )


def classify_index(index: Iterable[dict[str, Any]]) -> IntakeReport:
    """Classify every entry the indexer produced."""
    report = IntakeReport()
    for entry in index:
        report.classifications.append(
            classify(
                str(entry.get("file", "")),
                text=str(entry.get("text", "") or entry.get("summary", "")),
                caption=str(entry.get("caption", "")),
                roles=entry.get("doc_role_hints", []) or [],
            )
        )
    return report


def filter_index(
    index: Iterable[dict[str, Any]],
    *,
    allow: Iterable[str] = (),
) -> tuple[list[dict[str, Any]], IntakeReport]:
    """The index, minus what should never reach a deliverable.

    ``allow`` is the user's explicit override — a per-file decision, never a
    blanket switch, because "include everything personal" is not a setting
    anybody should be able to leave on.
    """
    allow = set(allow)
    entries = list(index)
    report = classify_index(entries)
    by_file = {c.file: c for c in report.classifications}
    for f in allow:
        if f in by_file:
            by_file[f].excluded = False
            by_file[f].override = "included by the user"
    kept = [e for e in entries if not by_file.get(str(e.get("file", "")), Classification("")).excluded]
    return kept, report
