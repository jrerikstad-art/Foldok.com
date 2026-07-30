"""Procedures are authored, not generated.

The same shape as the capture app: Foldok does not invent a photograph, it asks
for one and then holds it to a form. A procedure is the same kind of thing — the
knowledge is in the builder's head, not in the folder — so the engine's job is
to structure, number, cross-reference and check what a person wrote, and to say
what is missing.

What it checks is what a reviewer would check: a hazard warning that sits after
the step it warns about, a step referring to a tool nobody listed, an outcome
nobody stated. Those are findable in code. The steps themselves are not.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence


@dataclass
class Step:
    text: str
    hazard: str = ""                 # printed *before* this step
    tools: tuple[str, ...] = ()
    expected: str = ""               # what the person should see afterwards
    fact_ids: tuple[str, ...] = ()   # values quoted in the step

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"text": self.text}
        for k in ("hazard", "expected"):
            if getattr(self, k):
                d[k] = getattr(self, k)
        if self.tools:
            d["tools"] = list(self.tools)
        if self.fact_ids:
            d["fact_ids"] = list(self.fact_ids)
        return d


@dataclass
class Procedure:
    title: str
    steps: list[Step] = field(default_factory=list)
    prerequisites: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    outcome: str = ""
    author: str = ""

    def issues(self) -> list[str]:
        """What a reviewer would send back."""
        out: list[str] = []
        if not self.steps:
            out.append("no steps — a procedure with none is a heading")
        declared = {t.lower() for t in self.tools}
        for i, step in enumerate(self.steps, start=1):
            for tool in step.tools:
                if tool.lower() not in declared:
                    out.append(f"step {i} uses '{tool}', which is not in the tools list")
            if len(step.text.split()) > 40:
                out.append(f"step {i} is long enough to be two steps")
            if " and then " in step.text.lower():
                out.append(f"step {i} contains two actions — split it")
        if not self.outcome:
            out.append("no expected result — the reader cannot tell when they are done")
        if not self.author:
            out.append("no author — a procedure nobody signed is not evidence")
        return out

    def render(self, *, lang: str = "en") -> str:
        """Numbered, with hazards before the step they belong to."""
        lines: list[str] = []
        if self.prerequisites:
            head = "Forutsetninger" if lang.startswith("no") else "Before you start"
            lines.append(f"**{head}**")
            lines += [f"- {p}" for p in self.prerequisites]
            lines.append("")
        if self.tools:
            head = "Verktøy" if lang.startswith("no") else "Tools"
            lines.append(f"**{head}**: " + ", ".join(self.tools))
            lines.append("")
        for i, step in enumerate(self.steps, start=1):
            if step.hazard:
                marker = "ADVARSEL" if lang.startswith("no") else "WARNING"
                lines.append(f"> **{marker}** — {step.hazard}")
            lines.append(f"{i}. {step.text}")
            if step.expected:
                label = "Forventet" if lang.startswith("no") else "Expected"
                lines.append(f"   *{label}: {step.expected}*")
        if self.outcome:
            lines.append("")
            label = "Resultat" if lang.startswith("no") else "Result"
            lines.append(f"**{label}**: {self.outcome}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "author": self.author,
            "prerequisites": list(self.prerequisites),
            "tools": list(self.tools),
            "outcome": self.outcome,
            "steps": [s.to_dict() for s in self.steps],
            "issues": self.issues(),
        }
