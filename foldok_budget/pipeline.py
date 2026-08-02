"""Pipeline health — no engine fails silently, and none fails alone.

The instruction was: every engine has to work on its own *and* work together,
because one weak link takes the whole document down. That is exactly what
happened here, twice, and both times the failure was silent:

*   The citation scope discarded 95% of what retrieval produced. Retrieval was
    fine. Extraction was fine. The document was thin and nothing reported a
    problem, because throwing away claims is not an error condition.
*   The gap engine checked a requirement pack against ``Document.entries``. A
    narrative-authored manual creates none, so zero gaps were found and the
    document was declared ready to export. **The check passed because nothing
    was checked**, which is worse than failing.

Both are the same class of bug: a stage that produces nothing, or discards
almost everything, and returns success. So the pipeline needs a contract at each
boundary — what came in, what went out, and whether that ratio is plausible.

``check_pipeline`` runs the boundaries in order and stops describing downstream
stages once an upstream one has collapsed, because "0 claims" is not six separate
findings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Sequence

SCHEMA_VERSION = 1

Health = Literal["ok", "thin", "broken", "unchecked"]

# Ratios below which a stage has effectively collapsed rather than filtered.
YIELD_FLOOR: dict[str, float] = {
    "index_to_claims": 0.5,       # claims per usable file
    "claims_to_cited": 0.15,      # what survives selection into the document
    "sections_filled": 0.6,       # sections that got any content
}


@dataclass
class StageResult:
    stage: str
    health: Health = "unchecked"
    got: int = 0
    produced: int = 0
    detail: str = ""
    fix: str = ""

    @property
    def ratio(self) -> float:
        return self.produced / self.got if self.got else 0.0

    def __str__(self) -> str:
        mark = {"ok": " ok ", "thin": "thin", "broken": "FAIL", "unchecked": " ?  "}[self.health]
        line = f"[{mark}] {self.stage}: {self.got} → {self.produced}"
        if self.detail:
            line += f"\n         {self.detail}"
        if self.fix and self.health != "ok":
            line += f"\n         → {self.fix}"
        return line

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage, "health": self.health, "got": self.got,
            "produced": self.produced, "ratio": round(self.ratio, 3),
            "detail": self.detail, "fix": self.fix,
        }


@dataclass
class PipelineReport:
    stages: list[StageResult] = field(default_factory=list)

    @property
    def health(self) -> Health:
        order = {"ok": 0, "unchecked": 1, "thin": 2, "broken": 3}
        return max((s.health for s in self.stages), key=lambda h: order[h], default="unchecked")

    @property
    def broken(self) -> list[StageResult]:
        return [s for s in self.stages if s.health == "broken"]

    def first_failure(self) -> StageResult | None:
        """Where to look. Downstream symptoms are not separate problems."""
        for stage in self.stages:
            if stage.health in ("broken", "thin"):
                return stage
        return None

    def exportable(self) -> tuple[bool, str]:
        """The question that was answered wrongly.

        A document whose completeness ledger was never populated is not complete
        — it is unchecked, and saying 'ready to export' about it is the worst
        output this product can produce.
        """
        unchecked = [s for s in self.stages if s.health == "unchecked"]
        if self.broken:
            return (False, f"{self.broken[0].stage} produced nothing — {self.broken[0].fix}")
        if unchecked:
            names = ", ".join(s.stage for s in unchecked)
            return (False, f"not checked: {names}. Nothing has verified this document.")
        thin = [s for s in self.stages if s.health == "thin"]
        if thin:
            return (True, f"exportable, but {thin[0].stage} is thin — {thin[0].detail}")
        return (True, "every stage produced what the next one needs")

    def report(self, *, lang: str = "en") -> str:
        lines = [f"PIPELINE [{self.health.upper()}]"]
        lines += [f"  {s}" for s in self.stages]
        ok, why = self.exportable()
        lines.append("")
        lines.append(("EXPORT: " + ("ready — " if ok else "blocked — ") + why))
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        ok, why = self.exportable()
        return {
            "schema_version": SCHEMA_VERSION,
            "health": self.health,
            "exportable": ok,
            "reason": why,
            "stages": [s.to_dict() for s in self.stages],
        }


# ----------------------------------------------------------------------
def check_pipeline(
    *,
    files_indexed: int = 0,
    files_usable: int = 0,
    claims_extracted: int = 0,
    sections_planned: int = 0,
    sections_with_content: int = 0,
    claims_cited: int = 0,
    gap_ledger_entries: int | None = None,
    gaps_found: int | None = None,
) -> PipelineReport:
    """Boundaries in order. Each stage is judged on what the next one needs."""
    report = PipelineReport()

    report.stages.append(_stage(
        "index", got=files_indexed, produced=files_usable,
        floor=0.3,
        thin_detail=f"{files_indexed - files_usable} file(s) yielded no readable content",
        broken_fix="run foldok_scan — the formats are probably unsupported, not the folder",
        thin_fix="check foldok_scan for what was dropped and why",
    ))
    if files_usable == 0:
        return report

    report.stages.append(_stage(
        "extract", got=files_usable, produced=claims_extracted,
        floor=YIELD_FLOOR["index_to_claims"],
        thin_detail="fewer claims than files — most documents yielded nothing",
        broken_fix="the extractor found no statements; check that text is being read at all",
        thin_fix="widen claim patterns, or the sources are image-only and need OCR",
    ))
    if claims_extracted == 0:
        return report

    report.stages.append(_stage(
        "plan", got=claims_extracted, produced=sections_planned,
        floor=0.0,
        thin_detail="",
        broken_fix="the planner produced no outline",
        thin_fix="",
    ))
    if sections_planned == 0:
        return report

    filled = _stage(
        "author", got=sections_planned, produced=sections_with_content,
        floor=YIELD_FLOOR["sections_filled"],
        thin_detail="sections were planned but came back empty",
        broken_fix="no section received content — check the citation scope",
        thin_fix="claims exist but are not reaching sections; check per-section budgets",
    )
    report.stages.append(filled)

    cited = _stage(
        "cite", got=claims_extracted, produced=claims_cited,
        floor=YIELD_FLOOR["claims_to_cited"],
        thin_detail=(
            f"{claims_extracted - claims_cited} of {claims_extracted} claims were "
            "discarded before reaching the page"
        ),
        broken_fix="nothing was cited — the citation scope is discarding everything",
        thin_fix=(
            "a document-wide one-per-file rule will do this; scope it per section "
            "(foldok_budget.CiteScope)"
        ),
    )
    report.stages.append(cited)

    # The false green. Judged separately because a gap count of zero is
    # meaningless when the ledger it counts was never populated.
    if gap_ledger_entries is None:
        report.stages.append(StageResult(
            stage="completeness", health="unchecked", got=0, produced=0,
            detail="the gap engine was never run against this document",
            fix="populate Document.entries from the authored sections, then check",
        ))
    elif gap_ledger_entries == 0:
        report.stages.append(StageResult(
            stage="completeness", health="broken", got=0, produced=0,
            detail=(
                "zero requirements were checked, so zero gaps were found. "
                "'No gaps' here means 'nothing was examined'."
            ),
            fix="attach a requirement pack and populate the ledger before reporting readiness",
        ))
    else:
        report.stages.append(StageResult(
            stage="completeness", health="ok",
            got=gap_ledger_entries, produced=gaps_found or 0,
            detail=f"{gaps_found or 0} open item(s) across {gap_ledger_entries} requirement(s)",
        ))
    return report


def _stage(
    name: str, *, got: int, produced: int, floor: float,
    thin_detail: str, broken_fix: str, thin_fix: str,
) -> StageResult:
    if got == 0:
        return StageResult(name, "unchecked", got, produced,
                           detail="nothing arrived from the previous stage")
    if produced == 0:
        return StageResult(name, "broken", got, produced,
                           detail="produced nothing at all", fix=broken_fix)
    if floor and (produced / got) < floor:
        return StageResult(name, "thin", got, produced, detail=thin_detail, fix=thin_fix)
    return StageResult(name, "ok", got, produced)
