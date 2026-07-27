"""Modes — the same document, three levels of insistence.

Most people opening Foldok are not chasing a certificate today.  They are
building a prototype, writing up a rig, documenting something for themselves.
If the app greets them with thirty red MANGLER and refuses to export, they
close it.

But the answer is not a stripped-down "lite" product, because that fragments
the data model and the work does not carry forward.  The answer is:

    Evaluation is pure.  Only *gating* changes with mode.

The same gap objects are computed either way.  In build mode they are offers —
"thirty things Foldok can fill in for you" — nothing blocks, export always
works, and the document is watermarked as a working document.  Attach a
compliance pack later and the full list appears retroactively, over work
already done.  Nobody has to choose on day one, and nobody's early work is
wasted.

This is also the honest position commercially.  A prototype pack is a
requirement pack like any other; it just asks for less.  The person recording
a rig build gets a tool that helps them finish, and the day their rig becomes a
product, the compliance view is one selection away.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .document import Document
from .gaps import GapSet, evaluate
from .requirements import SEVERITY_RANK, RequirementPack

Level = Literal["error", "warning", "info"]


@dataclass
class Issue:
    level: Level
    code: str
    target: str
    message: str
    fix: str = ""

    def __str__(self) -> str:
        head = f"[{self.level.upper()}] {self.code} @ {self.target}: {self.message}"
        return f"{head}\n    fix: {self.fix}" if self.fix else head


@dataclass
class Gate:
    ok: bool
    mode: str
    issues: list[Issue] = field(default_factory=list)
    watermark: str | None = None
    statement: str = ""

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "warning"]

    def __str__(self) -> str:
        head = f"{'PASS' if self.ok else 'BLOCKED'} ({self.mode})"
        body = "\n".join(str(i) for i in self.issues)
        return f"{head}\n{body}" if body else head


@dataclass(frozen=True)
class Mode:
    id: str
    title: str
    close_from: str                  # lowest severity that must be closed
    blocks_export: bool
    require_confirmation: bool       # AI drafts must be confirmed
    require_na_signature: bool
    allow_defer: bool
    framing: Literal["offer", "gap"] # the language the UI should use
    watermark: str | None = None
    hint: str = ""


BUILD = Mode(
    id="build",
    title="Building",
    close_from="none",
    blocks_export=False,
    require_confirmation=False,
    require_na_signature=False,
    allow_defer=True,
    framing="offer",
    watermark="Working document — not a compliance package",
    hint="Nothing is blocked. Foldok offers to fill things in; ignore what you do not need.",
)

REVIEW = Mode(
    id="review",
    title="Review",
    close_from="required",
    blocks_export=True,
    require_confirmation=True,
    require_na_signature=True,
    allow_defer=True,
    framing="gap",
    watermark="Draft for review",
    hint="Blocking and required items must be resolved or explicitly marked not applicable.",
)

COMPLIANCE = Mode(
    id="compliance",
    title="Compliance",
    close_from="recommended",
    blocks_export=True,
    require_confirmation=True,
    require_na_signature=True,
    allow_defer=False,
    framing="gap",
    watermark=None,
    hint="Everything down to recommended must be closed, and every drafted item confirmed by a person.",
)

MODES: dict[str, Mode] = {m.id: m for m in (BUILD, REVIEW, COMPLIANCE)}


def get(mode_id: str) -> Mode:
    try:
        return MODES[mode_id]
    except KeyError as exc:
        raise ValueError(f"unknown mode '{mode_id}'; known: {sorted(MODES)}") from exc


# ----------------------------------------------------------------------
def must_close(mode: Mode, severity: str) -> bool:
    if mode.close_from == "none":
        return False
    return SEVERITY_RANK[severity] >= SEVERITY_RANK[mode.close_from]


def gate(
    document: Document,
    pack: RequirementPack,
    mode: Mode | str | None = None,
    gaps: GapSet | None = None,
) -> Gate:
    """Can this document be exported, and as what?"""
    mode = get(mode) if isinstance(mode, str) else (mode or get(document.mode))
    gaps = gaps if gaps is not None else evaluate(document, pack)
    issues: list[Issue] = []

    for notice in gaps.notices:
        issues.append(
            Issue(
                "warning" if mode is BUILD else "error",
                notice.code,
                pack.id,
                notice.message,
                notice.fix,
            )
        )

    for gap in gaps.gaps:
        if not gap.open:
            continue
        if not must_close(mode, gap.requirement.severity):
            issues.append(
                Issue("info", "open_item", gap.id, f"{gap.title} — {gap.state}", "")
            )
            continue
        if gap.state == "deferred" and mode.allow_defer:
            issues.append(
                Issue("warning", "deferred_item", gap.id, f"{gap.title} is parked", "resolve before handover")
            )
            continue
        issues.append(
            Issue(
                "error",
                f"open_{gap.requirement.severity}",
                gap.id,
                f"{gap.title} is {gap.state}"
                + (f" ({gap.requirement.authority})" if gap.requirement.authority else ""),
                gap.detail or "resolve it, or mark it not applicable with a reason",
            )
        )

    if mode.require_confirmation:
        for entry in document.sorted_entries():
            art = entry.artifact
            if art and art.needs_confirmation:
                issues.append(
                    Issue(
                        "error",
                        "unconfirmed_draft",
                        art.id,
                        f"'{art.title}' was drafted by Foldok and no person has confirmed it",
                        "read it and confirm, or replace it",
                    )
                )

    if mode.require_na_signature:
        for entry in document.sorted_entries():
            if entry.not_applicable and not (entry.reason and entry.signed_by):
                issues.append(
                    Issue(
                        "error",
                        "unsigned_not_applicable",
                        entry.key(),
                        "marked not applicable without a reason and a name",
                        "state why it does not apply, and who says so",
                    )
                )

    ok = not (mode.blocks_export and any(i.level == "error" for i in issues))
    statement = _statement(mode, gaps, ok)
    return Gate(ok=ok, mode=mode.id, issues=issues, watermark=mode.watermark, statement=statement)


def _statement(mode: Mode, gaps: GapSet, ok: bool) -> str:
    """The words that go on the document.

    'Complete' must never render as 'compliant'.  Completeness is a fact about
    the document that Foldok can check.  Compliance is a judgement made by
    somebody with a licence.
    """
    s = gaps.summary()
    if not ok:
        return f"{s['open']} item(s) still open."
    if mode is BUILD:
        return (
            f"{s['resolved']} of {s['total']} items recorded. "
            "Working document — Foldok has not checked this against any standard."
        )
    return (
        f"All {s['total']} items are resolved or marked not applicable, and every "
        "drafted item has been confirmed by a person. "
        "This states that the documentation is complete — it is not a statement of compliance."
    )


def progress(document: Document, pack: RequirementPack, mode: Mode | str | None = None) -> dict[str, Any]:
    """Numbers for the header.  Counts only what this mode actually asks for."""
    mode = get(mode) if isinstance(mode, str) else (mode or get(document.mode))
    gaps = evaluate(document, pack)
    in_scope = [g for g in gaps.gaps if must_close(mode, g.requirement.severity)] or gaps.gaps
    closed = [g for g in in_scope if not g.open]
    return {
        "mode": mode.id,
        "framing": mode.framing,
        "total": len(in_scope),
        "closed": len(closed),
        "open": len(in_scope) - len(closed),
        "percent": round(100 * len(closed) / len(in_scope), 1) if in_scope else 100.0,
        "label": (
            f"{len(in_scope) - len(closed)} things Foldok can help with"
            if mode.framing == "offer"
            else f"{len(in_scope) - len(closed)} open"
        ),
    }
