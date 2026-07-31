"""Intake — the inbound guard, in two calls.

    kept, report = prepare(index)                    # before mapping
    checked = review(sections, index, template)      # after generation

``prepare`` keeps personal documents out of the deliverable and hands back what
was held, so the user can be told rather than surprised.

``review`` normalises the markdown, gates the mapping against a computed score,
and scans the finished prose for two things: sentences apologising for a
document's presence, and personal identifiers that got through anyway.

That last scan is the point.  ``foldok_private`` already knows what a real
client, project or person is called — it built a vault of them to mask outbound
requests.  The same vault can be asked whether any of those values ended up in
the deliverable.  The boundary existed; it was only ever pointed one way.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from .classify import Classification, IntakeReport, classify, classify_index, filter_index
from .normalise import looks_broken, normalise
from .relevance import DEFAULT_THRESHOLD, GateReport, ProseIssue, audit_prose, gate, score


@dataclass
class Finding:
    code: str
    detail: str
    severity: str = "warn"           # fail | warn
    fix: str = ""

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.code}: {self.detail}" + (
            f"\n      fix: {self.fix}" if self.fix else ""
        )

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "detail": self.detail,
                "severity": self.severity, "fix": self.fix}


@dataclass
class ReviewReport:
    sections: dict[str, str] = field(default_factory=dict)
    gate: GateReport | None = None
    findings: list[Finding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not [f for f in self.findings if f.severity == "fail"]

    def add(self, code: str, detail: str, *, severity: str = "warn", fix: str = "") -> Finding:
        f = Finding(code=code, detail=detail, severity=severity, fix=fix)
        self.findings.append(f)
        return f

    def report(self) -> str:
        if not self.findings:
            return "nothing to flag — the document says only what it should"
        lines = [f"{len(self.findings)} finding(s):"]
        lines += [f"  {f}" for f in self.findings]
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "findings": [f.to_dict() for f in self.findings],
            "gate": self.gate.to_dict() if self.gate else None,
        }


def prepare(
    index: Iterable[Mapping[str, Any]],
    *,
    allow: Iterable[str] = (),
) -> tuple[list[dict[str, Any]], IntakeReport]:
    """Call this before ``map_sections``. Returns the index a deliverable may see."""
    kept, report = filter_index(index, allow=allow)      # type: ignore[arg-type]
    by_file = {c.file: c for c in report.classifications}
    for entry in kept:
        klass = by_file.get(str(entry.get("file", "")))
        if klass is not None:
            entry["doc_class"] = klass.doc_class          # so the gate can see it
    return kept, report


def review(
    sections: Mapping[str, str],
    *,
    index: Sequence[Mapping[str, Any]] = (),
    template_sections: Sequence[Mapping[str, Any]] = (),
    file_map: Mapping[str, Sequence[str]] | None = None,
    vault: Any = None,
    threshold: float = DEFAULT_THRESHOLD,
) -> ReviewReport:
    """Call this on generated prose, before it becomes a document."""
    result = ReviewReport()

    for key, text in sections.items():
        broken = looks_broken(text or "")
        result.sections[str(key)] = normalise(text or "")
        if broken:
            result.add(
                "markdown_not_rendered",
                f"{key}: {broken[0]} — it would print as literal text",
                fix="normalise model output before it reaches the renderer",
            )

    for issue in audit_prose(sections):
        result.add(
            "section_apologises_for_its_contents",
            str(issue),
            severity="fail",
            fix=(
                "the model wrote that because it had the file and could not remove it — "
                "the relevance gate let something through; drop the file instead of "
                "explaining it"
            ),
        )

    if file_map is not None and index and template_sections:
        result.gate = gate(file_map, index, template_sections, threshold=threshold)
        for dropped in result.gate.dropped:
            result.add(
                "mapping_below_threshold",
                f"{dropped.file} was mapped to {dropped.section} at {dropped.score:.2f}"
                + (f" ({dropped.reasons[0]})" if dropped.reasons else ""),
                fix="excluded from the section; nothing to do unless it really belongs",
            )

    if vault is not None:
        leaked = _leak_scan(vault, sections)
        for value, key in leaked:
            result.add(
                "identifier_in_deliverable",
                f"section '{key}' contains '{value}', which the vault holds as a real identifier",
                severity="fail",
                fix=(
                    "this document may be sent to a client — remove it, or confirm it "
                    "belongs there deliberately"
                ),
            )
    return result


def _leak_scan(vault: Any, sections: Mapping[str, str]) -> list[tuple[str, str]]:
    """Ask the masking vault whether anything it knows reached the output.

    Uses the private-call vault's own scan, so the definition of "a real
    identifier" is the same in both directions rather than two lists that drift.
    """
    hits: list[tuple[str, str]] = []
    scan = getattr(vault, "_scan", None)
    for key, text in sections.items():
        if not text:
            continue
        try:
            found = scan(text) if callable(scan) else []
        except Exception:  # noqa: BLE001
            found = []
        for value in found or []:
            hits.append((value, str(key)))
    return hits


def sensitive_summary(report: IntakeReport, lang: str = "no") -> str:
    return report.notice(lang)
