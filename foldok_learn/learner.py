"""The learner — observe confirmed work, propose, apply, revert.

What it watches, and why only these:

*  **Layout pins the user made themselves.** ``foldok_boxes`` already separates
   the user layer from the template layer, so "what did a person deliberately
   change" is already a query rather than a guess.
*  **Which resolver actually closed a gap.** Over a few jobs this says whether
   someone attaches existing test reports or fills forms in the app, which is a
   real difference in how the product should behave for them.
*  **Which symbols they actually place**, out of ninety in the pack.
*  **Obligations from standards they uploaded**, as citations.

What it deliberately does not watch: anything a model produced and nobody
confirmed. A draft the user never accepted is evidence that Foldok guessed, not
evidence of preference, and learning from it would compound the guess.

Nothing here proposes a lesson from one example except a clause, which is a fact
rather than a habit. Everything else needs its threshold met, and every lesson
is listed with its evidence count and can be reverted in one call — because a
tool that silently changes its own behaviour is worse than one that never
learns.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from .model import (
    THRESHOLDS,
    ClauseFinding,
    Evidence,
    Lesson,
    SharingRefused,
    assert_local_only,
    lesson_id,
    to_jsonl,
)
from .standards import Extraction, extract, extract_from_chunks, to_requirements


@dataclass
class Proposal:
    """A lesson offered to the user, with what it would change."""

    lesson: Lesson
    effect: str

    def to_dict(self) -> dict[str, Any]:
        return {"lesson": self.lesson.to_dict(), "effect": self.effect}


class Learner:
    def __init__(
        self,
        path: str | Path | None = None,
        clock=time.time,
    ) -> None:
        self.path = Path(path) if path else None
        self._lessons: dict[str, Lesson] = {}
        self._clock = clock
        if self.path and self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    lesson = Lesson.from_dict(json.loads(line))
                    self._lessons[lesson.id] = lesson

    # -- recording -------------------------------------------------------
    def _note(
        self,
        kind: str,
        subject: str,
        prop: str,
        value: Any,
        *,
        scope: str = "*",
        source: str,
        detail: str = "",
        rationale: str = "",
    ) -> Lesson:
        lid = lesson_id(kind, scope, subject, prop)
        lesson = self._lessons.get(lid)
        if lesson is None:
            lesson = Lesson(
                id=lid, kind=kind, subject=subject, prop=prop, value=value,  # type: ignore[arg-type]
                scope=scope, rationale=rationale, created_at=self._clock(),
            )
            self._lessons[lid] = lesson
        if lesson.status in ("rejected", "reverted"):
            return lesson                      # the user said no; do not keep asking
        if lesson.value != value:
            # The habit changed. Start the evidence again rather than averaging
            # two different preferences into one that is nobody's.
            lesson.value = value
            lesson.evidence = []
            lesson.status = "proposed"
        if not any(e.source == source and e.detail == detail for e in lesson.evidence):
            lesson.evidence.append(Evidence(source=source, detail=detail, at=self._clock()))
        return lesson

    # -- observers --------------------------------------------------------
    def observe_layout(self, session: Any, *, document_id: str) -> list[Lesson]:
        """User layout pins -> role-level lessons.

        Only ``layer == 'user'`` pins count: template defaults are not evidence
        of anything, they are what the user was given.
        """
        out: list[Lesson] = []
        scope = getattr(getattr(session, "template", None), "id", "*")
        roles: dict[str, dict[str, list[Any]]] = {}
        blocks = {b.id: b for b in getattr(session, "blocks", [])}
        for pin in session.pins.user_pins():
            block_id = pin.target.split(":", 1)[-1]
            block = blocks.get(block_id)
            if block is None or pin.prop not in ("span", "col", "align", "rows"):
                continue
            roles.setdefault(block.role, {}).setdefault(pin.prop, []).append(pin.value)

        for role, props in sorted(roles.items()):
            for prop, values in sorted(props.items()):
                if len(set(map(str, values))) != 1:
                    continue                   # inconsistent inside one document
                out.append(
                    self._note(
                        "layout", role, prop, values[0], scope=scope,
                        source=document_id, detail=f"{len(values)} block(s)",
                        rationale="this role was hand-set to the same value throughout",
                    )
                )
        return out

    def observe_resolvers(self, session: Any, *, document_id: str) -> list[Lesson]:
        """Which resolver actually closed each requirement kind."""
        out: list[Lesson] = []
        pack = getattr(session, "pack", None)
        scope = getattr(pack, "id", "*")
        for entry in session.document.sorted_entries():
            artifact = entry.artifact
            if artifact is None or artifact.empty or not artifact.produced_by:
                continue
            if not artifact.provenance.confirmed and artifact.provenance.source == "ai":
                continue                       # unconfirmed draft is not a preference
            requirement = pack.requirement(entry.requirement_key) if pack else None
            kind = requirement.kind if requirement else artifact.kind
            out.append(
                self._note(
                    "resolver", kind, "resolver", artifact.produced_by, scope=scope,
                    source=document_id, detail=entry.requirement_key,
                    rationale="this is how gaps of this kind actually get closed here",
                )
            )
        return out

    def observe_symbols(self, graph: Any, *, document_id: str) -> list[Lesson]:
        """Which symbols out of the pack are the ones in real use."""
        counts: dict[str, int] = {}
        for component in getattr(graph, "components", []):
            counts[component.type] = counts.get(component.type, 0) + 1
        out: list[Lesson] = []
        for symbol_type, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            out.append(
                self._note(
                    "symbol", getattr(graph, "domain", "electrical"), "used", symbol_type,
                    scope=symbol_type, source=document_id, detail=f"x{n}",
                    rationale="offer this near the top of the symbol picker",
                )
            )
        return out

    def observe_standard(
        self,
        text: str = "",
        *,
        standard: str,
        source: str,
        chunks: Iterable[Any] | None = None,
    ) -> tuple[Extraction, list[Lesson]]:
        """Read an uploaded standard into citations. Never stores its text."""
        extraction = (
            extract_from_chunks(chunks, source=source) if chunks is not None
            else extract(text, source=source)
        )
        out: list[Lesson] = []
        for finding in extraction.findings:
            out.append(
                self._note(
                    "requirement", standard, finding.clause, finding.to_dict(),
                    scope=standard, source=source,
                    detail=f"{finding.artifact}/{finding.per}",
                    rationale=f"confidence {finding.confidence:.0%} — confirm against your copy",
                )
            )
        return extraction, out

    # -- offering ---------------------------------------------------------
    def proposals(self, *, kind: str | None = None) -> list[Proposal]:
        """Lessons with enough evidence, not yet applied or refused."""
        out: list[Proposal] = []
        for lesson in sorted(self._lessons.values(), key=lambda l: (-l.support, l.id)):
            if lesson.status != "proposed" or not lesson.ready:
                continue
            if kind and lesson.kind != kind:
                continue
            out.append(Proposal(lesson=lesson, effect=_effect(lesson)))
        return out

    def lessons(self, *, status: str | None = None, kind: str | None = None) -> list[Lesson]:
        return [
            l for l in sorted(self._lessons.values(), key=lambda l: (l.kind, l.subject, l.prop))
            if (status is None or l.status == status) and (kind is None or l.kind == kind)
        ]

    def get(self, lesson_id_: str) -> Lesson | None:
        return self._lessons.get(lesson_id_)

    # -- deciding ---------------------------------------------------------
    def accept(self, lesson_id_: str) -> Lesson:
        lesson = self._require(lesson_id_)
        if not lesson.ready:
            raise ValueError(
                f"'{lesson_id_}' has {lesson.support} example(s) and needs {lesson.threshold}. "
                "One hand-resized image is a hand-resized image; several is a preference."
            )
        lesson.status = "active"
        lesson.applied_at = self._clock()
        return lesson

    def reject(self, lesson_id_: str) -> Lesson:
        lesson = self._require(lesson_id_)
        lesson.status = "rejected"
        return lesson

    def revert(self, lesson_id_: str) -> Lesson:
        lesson = self._require(lesson_id_)
        lesson.status = "reverted"
        lesson.applied_at = 0.0
        return lesson

    def forget_all(self) -> int:
        n = len(self._lessons)
        self._lessons = {}
        if self.path and self.path.exists():
            self.path.unlink()
        return n

    def _require(self, lesson_id_: str) -> Lesson:
        lesson = self._lessons.get(lesson_id_)
        if lesson is None:
            raise KeyError(f"no lesson '{lesson_id_}'")
        return lesson

    # -- applying ----------------------------------------------------------
    def apply_layout(self, template: Any) -> list[str]:
        """Fold active layout lessons into a template's role defaults."""
        applied: list[str] = []
        for lesson in self.lessons(status="active", kind="layout"):
            if lesson.scope not in ("*", getattr(template, "id", "*")):
                continue
            template.role_defaults.setdefault(lesson.subject, {})[lesson.prop] = lesson.value
            applied.append(lesson.id)
        return applied

    def preferred_resolver(self, requirement_kind: str, pack_id: str = "*") -> str | None:
        for lesson in self.lessons(status="active", kind="resolver"):
            if lesson.subject == requirement_kind and lesson.scope in ("*", pack_id):
                return str(lesson.value)
        return None

    def favourite_symbols(self, domain: str = "electrical", limit: int = 12) -> list[str]:
        ranked = [
            l for l in self._lessons.values()
            if l.kind == "symbol" and l.subject == domain and l.status != "rejected"
        ]
        ranked.sort(key=lambda l: (-l.support, str(l.value)))
        return [str(l.value) for l in ranked[:limit]]

    def local_pack(
        self,
        standard: str,
        *,
        pack_id: str = "",
        title: str = "",
        segment: str = "general",
        only_accepted: bool = True,
    ) -> dict[str, Any]:
        """A ``foldok_gaps`` pack dict built from clauses of one standard.

        Born ``reference_only``: it is derived from a copyrighted work the user
        licensed for their own use. ``foldok_assets.seal()`` will refuse to
        package it, which is the intended behaviour, not a limitation to route
        around.
        """
        findings: list[ClauseFinding] = []
        for lesson in self.lessons(kind="requirement"):
            if lesson.subject != standard:
                continue
            if only_accepted and lesson.status != "active":
                continue
            # to_dict() includes derived fields (severity); rebuild from the
            # stored ones only.
            fields = {
                k: v for k, v in dict(lesson.value).items()
                if k in ClauseFinding.__dataclass_fields__
            }
            findings.append(ClauseFinding(**fields))
        return {
            "id": pack_id or f"local.{standard.lower().replace(' ', '_')}",
            "title": title or f"{standard} — local profile",
            "segment": segment,
            "version": "1",
            "standards": [standard],
            "description": (
                f"Obligations extracted locally from {standard}. Citations only — no text "
                "from the standard is stored. Confirm each requirement against your own "
                "copy before relying on it."
            ),
            "requirements": to_requirements(findings, standard=standard),
            "local_only": True,
            "redistribution": "reference_only",
        }

    # -- persistence --------------------------------------------------------
    def save(self, path: str | Path | None = None) -> Path:
        target = Path(path) if path else self.path
        if target is None:
            raise ValueError("no path given and this learner has none")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(to_jsonl(self._lessons.values()), encoding="utf-8")
        self.path = target
        return target

    def export(self, *_args: Any, **_kw: Any) -> None:
        """Deliberately not implemented.

        Everything here is derived from the user's own documents and, for
        standards, from a copyrighted work they licensed. Sharing needs consent,
        sanitising and a licence; it is a separate deliberate build, not a method
        on the local learner.
        """
        assert_local_only(self._lessons.values(), what="export")

    # -- reporting -----------------------------------------------------------
    def report(self) -> str:
        by_status: dict[str, int] = {}
        for lesson in self._lessons.values():
            by_status[lesson.status] = by_status.get(lesson.status, 0) + 1
        lines = [
            f"{len(self._lessons)} lesson(s) — "
            + ", ".join(f"{v} {k}" for k, v in sorted(by_status.items()))
        ]
        ready = self.proposals()
        if ready:
            lines.append("\nReady to apply:")
            for p in ready[:10]:
                lines.append(f"  {p.lesson.describe()}")
                lines.append(f"      -> {p.effect}")
        waiting = [l for l in self._lessons.values() if l.status == "proposed" and not l.ready]
        if waiting:
            lines.append(f"\n{len(waiting)} still gathering evidence:")
            for l in sorted(waiting, key=lambda x: -x.support)[:5]:
                lines.append(f"  {l.subject}.{l.prop} — {l.support}/{l.threshold}")
        lines.append("\nEverything here stays on this machine.")
        return "\n".join(lines)


def _effect(lesson: Lesson) -> str:
    if lesson.kind == "layout":
        return f"new {lesson.subject} blocks start at {lesson.prop}={lesson.value}"
    if lesson.kind == "resolver":
        return f"'{lesson.value}' offered first for {lesson.subject} gaps"
    if lesson.kind == "symbol":
        return f"'{lesson.value}' moves up the symbol picker"
    if lesson.kind == "requirement":
        clause = lesson.value.get("clause") if isinstance(lesson.value, dict) else lesson.prop
        return f"adds a requirement citing {lesson.subject} {clause}"
    return "adjusts a default"
