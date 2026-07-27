"""Detection — finding what to mask.

No named-entity model here, on purpose.  Foldok already knows who the client is,
what the project is called, which tags exist and which people signed, because
those are *facts with citations* in the fact base.  Detection is therefore mostly
lookup, plus deterministic patterns for the things that follow a shape.

Deterministic beats clever here for the same reason it does everywhere else in
this product: a regex that misses is a bug you can fix once, while a model that
misses is a bug that comes back with different wording next week.  Anything the
patterns are unsure about is reported for the user to confirm, not guessed.

Norwegian-aware: æøå, AS/ASA/ANS company suffixes, 9-digit organisation numbers,
and +47 phone shapes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from .vault import EntityKind, EntityVault

# Ordered: the first pattern to claim a span wins.
PATTERNS: tuple[tuple[str, EntityKind, re.Pattern[str]], ...] = (
    ("email", "email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]{2,}\b")),
    ("url", "url", re.compile(r"\bhttps?://[^\s<>\"')]+")),
    ("path", "path", re.compile(r"\b[A-Za-z]:\\[^\s\"'<>|]+|(?<![\w])/(?:home|Users|mnt|var)/[^\s\"'<>|]+")),
    ("org_no", "org_no", re.compile(r"\b(?:NO\s?)?\d{3}\s?\d{3}\s?\d{3}(?:\s?MVA)?\b")),
    ("phone", "phone", re.compile(r"(?:\+47[\s-]?)?(?:\d{2}[\s-]?){3}\d{2}\b")),
    ("coordinate", "coordinate", re.compile(r"\b\d{1,3}[.,]\d{4,}\s*[°º]?\s*[NSEW]?[,;]\s*\d{1,3}[.,]\d{4,}\s*[°º]?\s*[NSEW]?\b")),
    # Equipment tags: P-101, -Q1, K3, TT-2041A. Common in every discipline.
    ("tag", "tag", re.compile(r"(?<![\w])-?[A-Z]{1,3}-?\d{1,4}[A-Z]?(?![\w-])")),
    # Drawing / document numbers: ABC-1234-567, DOC-2026-0031
    ("document_no", "document_no", re.compile(r"\b[A-Z]{2,5}-\d{2,5}-\d{2,6}[A-Z]?\b")),
    ("serial", "serial", re.compile(r"\b(?:S/?N|serienr\.?|serial)[\s:]*([A-Z0-9][A-Z0-9-]{4,})\b", re.IGNORECASE)),
)

COMPANY_SUFFIX = re.compile(
    r"\b([A-ZÆØÅ][\wÆØÅæøå&.-]*(?:\s+[A-ZÆØÅ][\wÆØÅæøå&.-]*){0,3})\s+(AS|ASA|ANS|DA|SA|AB|A/S|Ltd|GmbH|Inc)\b"
)


@dataclass
class Candidate:
    value: str
    kind: EntityKind
    detector: str
    start: int = 0
    confident: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "value": self.value, "kind": self.kind,
            "detector": self.detector, "confident": self.confident,
        }


def detect(text: str, *, include_uncertain: bool = True) -> list[Candidate]:
    """Everything in ``text`` that looks like an identifier."""
    out: list[Candidate] = []
    claimed: list[tuple[int, int]] = []

    def free(a: int, b: int) -> bool:
        return not any(a < y and x < b for x, y in claimed)

    for name, kind, pattern in PATTERNS:
        for m in pattern.finditer(text or ""):
            span = m.span(1) if m.groups() else m.span()
            if not free(*span):
                continue
            claimed.append(span)
            out.append(
                Candidate(
                    value=m.group(1) if m.groups() else m.group(0),
                    kind=kind, detector=name, start=span[0],
                    # A bare tag like "K3" is common but also matches ordinary
                    # text, so it is offered rather than assumed.
                    confident=name not in ("tag",),
                )
            )

    for m in COMPANY_SUFFIX.finditer(text or ""):
        if free(*m.span()):
            claimed.append(m.span())
            out.append(Candidate(m.group(0), "vendor", "company_suffix", m.start()))

    if not include_uncertain:
        out = [c for c in out if c.confident]
    return sorted(out, key=lambda c: c.start)


def from_facts(facts: Iterable[dict]) -> list[Candidate]:
    """Turn the fact base into candidates.

    Expects records like ``{"key": "client_name", "value": "Equinor ASA"}``.
    This is the high-value path: these are confirmed, cited values, so masking
    them is not a guess.
    """
    mapping: tuple[tuple[str, EntityKind], ...] = (
        ("client", "client"), ("customer", "client"), ("kunde", "client"),
        ("project", "project"), ("prosjekt", "project"),
        ("vendor", "vendor"), ("supplier", "vendor"), ("leverandor", "vendor"),
        ("person", "person"), ("signed", "person"), ("installer", "person"),
        ("engineer", "person"), ("ansvarlig", "person"), ("utfort_av", "person"),
        ("site", "site"), ("address", "site"), ("adresse", "site"), ("anlegg", "site"),
        ("tag", "tag"), ("serial", "serial"), ("serienr", "serial"),
        ("document", "document_no"), ("drawing", "document_no"), ("tegning", "document_no"),
    )
    out: list[Candidate] = []
    for fact in facts or ():
        key = str(fact.get("key", "")).lower()
        value = str(fact.get("value", "")).strip()
        if not value or len(value) < 2:
            continue
        for needle, kind in mapping:
            if needle in key:
                out.append(Candidate(value, kind, f"fact:{key}"))
                break
    return out


def populate(
    vault: EntityVault,
    text: str = "",
    facts: Iterable[dict] = (),
    *,
    include_uncertain: bool = False,
    source: str = "auto",
) -> list[Candidate]:
    """Fill a vault from facts and text.  Facts first — they are confirmed.

    ``include_uncertain`` is off by default: an over-eager tag detector that
    masks the word "K3" out of ordinary prose makes the model's output worse for
    no privacy gain. Uncertain candidates are returned for the user to confirm.
    """
    found: list[Candidate] = []
    for c in from_facts(facts):
        vault.add(c.value, c.kind, source=c.detector or source)
        found.append(c)
    for c in detect(text, include_uncertain=include_uncertain):
        vault.add(c.value, c.kind, source=f"{source}:{c.detector}")
        found.append(c)
    return found


def review(text: str) -> list[Candidate]:
    """Candidates worth showing the user before the first call.

    The uncertain ones especially — this is the "is K3 a circuit or a word"
    question, and the user answers it once per project.
    """
    return [c for c in detect(text, include_uncertain=True) if not c.confident]
