"""Coherence — what free synthesis structurally cannot tell you.

NotebookLM will summarise a folder of standards beautifully and will never say
that two of them disagree, or that a project's own hypothesis contradicts its
customer's hard specification. That is not a gap in its writing; it is what
summarising *is*. A summary reconciles by construction — it produces one coherent
account and the disagreements dissolve into it.

Finding disagreement needs claims held apart, with their sources, modalities and
scopes intact, and then compared. Six checks, each of which a reviewer would make
by hand:

``contradicts``      two binding rules that cannot both be satisfied
``contested``        a hypothesis that runs against a binding rule
``unsupported``      a rule with no evidence claim that meets it
``scope_gap``        a required range that the evidence does not cover
``duplicate``        the same rule from several sources — cite one, not five
``inadequate``       a stated inadequacy that other claims rely on anyway

The last one is the interesting one. "Armering alene er en dårlig skjerm for høye
frekvenser" is a warning that only matters if something else in the library
depends on armouring for shielding. A summary keeps both sentences and lets the
reader notice. This says so.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal, Sequence

from .model import Claim, ClaimSet, Quantity, Scope

FindingKind = Literal[
    "contradicts", "contested", "unsupported", "scope_gap", "duplicate", "inadequate",
]

SEVERITY: dict[str, str] = {
    "contradicts": "high",
    "contested": "high",
    "unsupported": "medium",
    "scope_gap": "medium",
    "inadequate": "medium",
    "duplicate": "low",
}

# Pairs whose co-occurrence in one requirement is a real design tension.
# Stems, not forms. "lukket" never matches "lukkede", and Norwegian inflects
# every one of these — which is why the first version found nothing.
# (pattern, pattern, human label A, human label B). The labels exist because an
# earlier version printed the regex into the user's finding.
OPPOSED: tuple[tuple[str, str, str, str], ...] = (
    (r"lukke\w*", r"[åa]pne\w*", "lukket", "åpen"),
    (r"lukke\w*", r"tr[åa]dstige\w*", "lukket bane", "trådstige"),
    (r"lukke\w*", r"wire tray", "closed tray", "wire tray"),
    (r"\bclosed\b", r"\bopen\b", "closed", "open"),
    (r"skjermet|skjerma", r"uskjermet", "skjermet", "uskjermet"),
    (r"\bshielded\b", r"\bunshielded\b", "shielded", "unshielded"),
    (r"separate|separert", r"felles|sammen", "separert", "felles"),
)


@dataclass
class Finding:
    kind: FindingKind
    summary: str
    claims: tuple[str, ...] = ()
    detail: str = ""
    question: str = ""            # what a person has to decide

    @property
    def severity(self) -> str:
        return SEVERITY[self.kind]

    def __str__(self) -> str:
        line = f"[{self.severity}] {self.kind}: {self.summary}"
        if self.detail:
            line += f"\n      {self.detail}"
        if self.question:
            line += f"\n      → {self.question}"
        return line

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind, "severity": self.severity, "summary": self.summary,
            "detail": self.detail, "question": self.question, "claims": list(self.claims),
        }


@dataclass
class CoherenceReport:
    findings: list[Finding] = field(default_factory=list)
    claim_count: int = 0
    source_count: int = 0

    @property
    def ok(self) -> bool:
        return not [f for f in self.findings if f.severity in ("high", "medium")]

    def of(self, kind: str) -> list[Finding]:
        return [f for f in self.findings if f.kind == kind]

    def report(self) -> str:
        head = (
            f"{self.claim_count} claim(s) from {self.source_count} source(s); "
            f"{len(self.findings)} finding(s)"
        )
        if not self.findings:
            return head + " — no conflicts found"
        order = {"high": 0, "medium": 1, "low": 2}
        lines = [head]
        for f in sorted(self.findings, key=lambda x: order[x.severity]):
            lines.append(f"  {f}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "claims": self.claim_count,
            "sources": self.source_count,
            "ok": self.ok,
            "findings": [f.to_dict() for f in self.findings],
        }


def check(claims: ClaimSet | Sequence[Claim]) -> CoherenceReport:
    items = list(claims.claims if isinstance(claims, ClaimSet) else claims)
    report = CoherenceReport(
        claim_count=len(items),
        source_count=len({c.source for c in items if c.source}),
    )
    binding = [c for c in items if c.binding]

    _contradictions(binding, report)
    _contested(binding, [c for c in items if c.contestable], report)
    _unsupported(binding, items, report)
    _scope_gaps(binding, items, report)
    _duplicates(binding, report)
    _inadequacies(items, report)
    return report


# ----------------------------------------------------------------------
def _contradictions(binding: list[Claim], report: CoherenceReport) -> None:
    for i, a in enumerate(binding):
        for b in binding[i + 1:]:
            if a.source == b.source and a.predicate == b.predicate and a.id == b.id:
                continue
            if not a.scope.overlaps(b.scope):
                continue

            if a.quantity and b.quantity and a.predicate and a.predicate == b.predicate:
                if a.quantity.unit == b.quantity.unit and not a.quantity.overlaps(b.quantity):
                    report.findings.append(Finding(
                        kind="contradicts",
                        summary=f"{a.predicate}: {a.quantity} vs {b.quantity}",
                        claims=(a.id, b.id),
                        detail=f"{_cite(a)} — {_cite(b)}",
                        question="which value governs, and under what condition?",
                    ))
                    continue

            opposed = _opposed_terms(a.text, b.text)
            if opposed and a.predicate and a.predicate == b.predicate:
                report.findings.append(Finding(
                    kind="contradicts",
                    summary=f"{a.predicate}: '{opposed[0]}' required in one place, "
                            f"'{opposed[1]}' in another",
                    claims=(a.id, b.id),
                    detail=f"{_cite(a)} — {_cite(b)}",
                    question="are these two different zones, or a genuine conflict?",
                ))


def _contested(binding: list[Claim], hypotheses: list[Claim], report: CoherenceReport) -> None:
    """A hypothesis against a hard requirement.

    This is the finding a summary cannot produce, because a summary states both
    and moves on. In the EMC notes the project hypothesises that wire trays may
    outperform closed trays, while Aker's hard spec requires fully closed
    systems. Both sentences are true reports; together they are a decision.
    """
    for h in hypotheses:
        for rule in binding:
            if not h.scope.overlaps(rule.scope):
                continue
            opposed = _opposed_terms(h.text, rule.text)
            shared = _shared_terms(h.text, rule.text)
            if not opposed and len(shared) < 2:
                continue
            report.findings.append(Finding(
                kind="contested",
                summary=(
                    "a hypothesis runs against a binding requirement"
                    + (f" ({opposed[0]} vs {opposed[1]})" if opposed else "")
                ),
                claims=(h.id, rule.id),
                detail=f"hypothesis: {_short(h.text)}\n      requirement: {_short(rule.text)}",
                question=(
                    "the requirement governs until the hypothesis is tested — is that "
                    "written down anywhere the customer can see?"
                ),
            ))


def _unsupported(binding: list[Claim], items: list[Claim], report: CoherenceReport) -> None:
    """A requirement nothing in the library shows is met."""
    evidence = [c for c in items if c.type in ("quantity", "reference") or c.quantity]
    for rule in binding:
        if not rule.quantity and not rule.scope.known:
            continue
        supported = any(
            e.source != rule.source
            and (e.predicate == rule.predicate or rule.scope.overlaps(e.scope))
            and (e.quantity is not None or e.type == "reference")
            for e in evidence
        )
        if supported:
            continue
        report.findings.append(Finding(
            kind="unsupported",
            summary=f"no evidence in the library meets: {_short(rule.text, 70)}",
            claims=(rule.id,),
            detail=_cite(rule),
            question="is there a test report for this, or is it an open requirement?",
        ))


def _scope_gaps(binding: list[Claim], items: list[Claim], report: CoherenceReport) -> None:
    """A required range the evidence does not cover.

    The EMC case: testing is required DC to 1 GHz; the product is characterised
    from 150 kHz. The band below 150 kHz is unevidenced, and nobody reading a
    summary of both documents would notice.
    """
    required = [c for c in binding if c.scope.frequency and c.scope.frequency.known]
    evidenced = [
        c for c in items
        if c.scope.frequency and c.scope.frequency.known and c.type in ("quantity", "reference")
        or (c.quantity and c.quantity.unit == "dB" and c.scope.frequency)
    ]
    for rule in required:
        need = rule.scope.frequency
        for ev in evidenced:
            have = ev.scope.frequency
            if have is None or not need.overlaps(have):
                continue
            if have.covers(need):
                continue
            low_gap = (need.low or 0) < (have.low or 0)
            high_gap = (need.high or 0) > (have.high or 0)
            if not (low_gap or high_gap):
                continue
            missing = []
            if low_gap:
                missing.append(f"below {_hz(have.low)}")
            if high_gap:
                missing.append(f"above {_hz(have.high)}")
            report.findings.append(Finding(
                kind="scope_gap",
                summary=(
                    f"required {_band(need)}, evidenced {_band(have)} — "
                    f"{' and '.join(missing)} uncovered"
                ),
                claims=(rule.id, ev.id),
                detail=f"{_cite(rule)} — {_cite(ev)}",
                question="is the uncovered band out of scope, or untested?",
            ))


def _duplicates(binding: list[Claim], report: CoherenceReport) -> None:
    groups: dict[str, list[Claim]] = {}
    for c in binding:
        groups.setdefault(_fingerprint(c.text), []).append(c)
    for group in groups.values():
        sources = {c.source for c in group}
        if len(group) > 1 and len(sources) > 1:
            report.findings.append(Finding(
                kind="duplicate",
                summary=f"the same requirement appears in {len(sources)} sources",
                claims=tuple(c.id for c in group),
                detail=", ".join(sorted(s for s in sources if s)),
                question="cite the governing one, not all of them",
            ))


def _inadequacies(items: list[Claim], report: CoherenceReport) -> None:
    """A stated inadequacy that something else relies on anyway."""
    warnings = [c for c in items if c.negated and c.type in ("distinction", "risk", "rule")]
    for warning in warnings:
        subject_terms = _terms(warning.text)
        relied = [
            c for c in items
            if c.id != warning.id and c.binding
            and len(subject_terms & _terms(c.text)) >= 2
        ]
        if not relied:
            continue
        report.findings.append(Finding(
            kind="inadequate",
            summary=f"a stated limitation that {len(relied)} requirement(s) depend on",
            claims=(warning.id, *[c.id for c in relied[:3]]),
            detail=f"limitation: {_short(warning.text)}",
            question="does the design compensate for this, or inherit the weakness?",
        ))


# ----------------------------------------------------------------------
STOP = {
    "skal", "må", "er", "som", "for", "til", "det", "den", "med", "alle", "kan",
    "the", "and", "for", "with", "that", "this", "are", "shall", "must", "from",
    "ved", "har", "ikke", "eller", "under", "over", "hele", "vi", "av", "og", "i", "en", "et",
}


def _terms(text: str) -> set[str]:
    return {
        w.lower() for w in re.findall(r"[A-Za-zÀ-ÿÆØÅæøå]{4,}", text or "")
    } - STOP


def _shared_terms(a: str, b: str) -> set[str]:
    return _terms(a) & _terms(b)


def _opposed_terms(a: str, b: str) -> tuple[str, str] | None:
    """Human labels, never the patterns that found them."""
    la, lb = (a or "").lower(), (b or "").lower()
    for left, right, label_left, label_right in OPPOSED:
        if re.search(left, la) and re.search(right, lb):
            return (label_left, label_right)
        if re.search(right, la) and re.search(left, lb):
            return (label_right, label_left)
    return None


def _fingerprint(text: str) -> str:
    return " ".join(sorted(list(_terms(text))[:8]))


def _short(text: str, limit: int = 100) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[:limit] + "…"


def _cite(claim: Claim) -> str:
    return claim.citation or claim.source or "(uncited)"


def _band(q: Quantity) -> str:
    """0–1000000000 Hz is not how anybody states a frequency range."""
    if q is None or not q.known:
        return "unscoped"
    low = "DC" if (q.low or 0) == 0 else _hz(q.low)
    return f"{low}–{_hz(q.high)}"


def _hz(value: float | None) -> str:
    if value is None:
        return "?"
    for scale, unit in ((1e9, "GHz"), (1e6, "MHz"), (1e3, "kHz")):
        if value >= scale:
            return f"{value / scale:g} {unit}"
    return f"{value:g} Hz"
