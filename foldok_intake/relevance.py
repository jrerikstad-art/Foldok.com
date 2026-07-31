"""Relevance — a gate, not a request.

``foldok_compile.map_sections`` asked Haiku to map files to sections with the
instruction *"omit irrelevant files"*.  That is a soft ask to a small model with
nothing checking it on either side, and when it went wrong the prose generator
had no way to disagree: it received the file, and the only action available was
to write a sentence explaining that the file did not belong.

Two rules replace it:

**Score before the model, and gate after it.**  Role overlap and vocabulary
overlap are computable.  The model's mapping is then a *proposal* that has to
clear the same bar, so a bad mapping is caught rather than rendered.

**No section may describe its own contents as irrelevant.**  If generated prose
says a document has no relevance, that is not careful writing — it is the engine
having failed upstream and the model doing the only thing it could.  The sentence
is a bug report, and ``audit_prose`` reads it as one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

DEFAULT_THRESHOLD = 0.25

# The model saying this is a symptom, never a style choice.
IRRELEVANCE_PHRASES: tuple[re.Pattern[str], ...] = (
    re.compile(r"uten\s+(direkte\s+)?relevans", re.I),
    re.compile(r"\bikke\s+relevant\b", re.I),
    re.compile(r"\bikke\s+direkte\s+knyttet\b", re.I),
    re.compile(r"\bno\s+(direct\s+)?relevance\b", re.I),
    re.compile(r"\bnot\s+relevant\b", re.I),
    re.compile(r"\bunrelated\s+to\s+(this|the)\b", re.I),
    re.compile(r"\bincluded\s+for\s+completeness\b", re.I),
)

STOPWORDS = {
    "and", "the", "for", "with", "från", "och", "som", "til", "med", "for", "det",
    "den", "der", "dokumentasjon", "documentation", "document", "dokument",
    "seksjon", "section", "prosjekt", "project",
}


@dataclass
class Match:
    file: str
    section: str
    score: float
    reasons: tuple[str, ...] = ()

    @property
    def passes(self) -> bool:
        return self.score >= DEFAULT_THRESHOLD

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file, "section": self.section,
            "score": round(self.score, 3), "reasons": list(self.reasons),
        }


@dataclass
class GateReport:
    kept: dict[str, list[str]] = field(default_factory=dict)      # section -> files
    dropped: list[Match] = field(default_factory=list)
    threshold: float = DEFAULT_THRESHOLD

    @property
    def dropped_count(self) -> int:
        return len(self.dropped)

    def explain(self) -> str:
        if not self.dropped:
            return "every mapped file cleared the relevance gate"
        lines = [f"{len(self.dropped)} mapping(s) dropped below {self.threshold:.2f}:"]
        for m in self.dropped[:10]:
            lines.append(f"  {m.file} -> {m.section} ({m.score:.2f})")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "threshold": self.threshold,
            "kept": {k: list(v) for k, v in sorted(self.kept.items())},
            "dropped": [m.to_dict() for m in self.dropped],
        }


def score(
    entry: Mapping[str, Any],
    section: Mapping[str, Any],
) -> Match:
    """How well does this file fit this section? Computable, so computed."""
    file = str(entry.get("file", ""))
    key = str(section.get("section_key", ""))
    reasons: list[str] = []
    total = 0.0

    roles = {str(r).lower() for r in (entry.get("doc_role_hints") or [])}
    preferred = {
        str(r).lower()
        for r in (section.get("required_media", {}) or {}).get("preferred_roles", [])
        or section.get("roles", [])
    }
    if roles & preferred:
        total += 0.6
        reasons.append(f"role {sorted(roles & preferred)[0]}")

    caption_words = _words(str(entry.get("caption", "")))
    title_words = _words(str(section.get("title", "")) + " " + key.replace("_", " "))
    overlap = caption_words & title_words
    if overlap:
        total += min(0.4, 0.15 * len(overlap))
        reasons.append(f"shares {', '.join(sorted(overlap)[:3])}")

    if roles and preferred and not (roles & preferred):
        total -= 0.15
        reasons.append("declared role does not match the section")

    doc_class = str(entry.get("doc_class", "project"))
    if doc_class not in ("project", "unknown"):
        total -= 0.8
        reasons.append(f"classified {doc_class}")

    return Match(file=file, section=key, score=max(0.0, round(total, 3)),
                 reasons=tuple(reasons))


def gate(
    file_map: Mapping[str, Sequence[str]],
    index: Iterable[Mapping[str, Any]],
    sections: Sequence[Mapping[str, Any]],
    *,
    threshold: float = DEFAULT_THRESHOLD,
) -> GateReport:
    """Check the model's mapping against a computed score.

    The mapping is a proposal. This is where it becomes a decision, which is the
    part that was missing: a bad mapping could not previously be caught, because
    nothing downstream was allowed to disagree with it.
    """
    by_file = {str(e.get("file", "")): e for e in index}
    by_key = {str(s.get("section_key", "")): s for s in sections}
    report = GateReport(threshold=threshold)

    for section_key, files in file_map.items():
        section = by_key.get(str(section_key))
        if section is None:
            continue
        for file in files or ():
            entry = by_file.get(str(file))
            if entry is None:
                report.dropped.append(
                    Match(file=str(file), section=str(section_key), score=0.0,
                          reasons=("not in the index",))
                )
                continue
            match = score(entry, section)
            if match.score >= threshold:
                report.kept.setdefault(str(section_key), []).append(str(file))
            else:
                report.dropped.append(match)
    return report


# ----------------------------------------------------------------------
@dataclass
class ProseIssue:
    section: str
    phrase: str
    excerpt: str

    def __str__(self) -> str:
        return f"{self.section}: says '{self.phrase}' — …{self.excerpt}…"


def audit_prose(sections: Mapping[str, str]) -> list[ProseIssue]:
    """A section describing its own contents as irrelevant is a bug report.

    The model wrote that sentence because it had the file and could not remove
    it. Finding the sentence means the gate above let something through.
    """
    issues: list[ProseIssue] = []
    for key, text in sections.items():
        for pattern in IRRELEVANCE_PHRASES:
            hit = pattern.search(text or "")
            if not hit:
                continue
            start = max(0, hit.start() - 45)
            end = min(len(text), hit.end() + 45)
            issues.append(
                ProseIssue(section=str(key), phrase=hit.group(0),
                           excerpt=text[start:end].strip())
            )
            break
    return issues


def _words(text: str) -> set[str]:
    return {
        w.lower() for w in re.findall(r"[0-9a-zA-ZÀ-ÿæøåÆØÅ_-]{4,}", text or "")
    } - STOPWORDS
