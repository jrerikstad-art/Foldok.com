"""Capabilities — derived from the engines, never hand-written.

This package exists because of a specific failure.  A user asked Foldok for a
schematic and it answered "I have no drawing tools, only text" — while the same
build shipped 45 diagram symbols, orthogonal routing, SVG output and green
golden tests.

Nothing was broken.  ``hub_chat.py`` tells the model, as a hard rule, that
capability claims must come from ``capabilities.json``, and that file contained
the word "diagram" exactly zero times.  The anti-hallucination guardrail was
stricter than the capability list was complete, so it suppressed a real feature.
Correct behaviour, wrong inputs, and it would have answered that way for every
user forever.

Two design decisions follow from that, and the second one is the important one.

**Capabilities are derived, not declared.**  A hand-maintained manifest drifts
from the code the moment either changes, and nothing notices.  Everything here
is read from the asset library, the requirement packs and the engines
themselves, so the manifest cannot claim less than the product does.

**A limit belongs to its capability.**  The old ``cannot`` list carried
``tegne eller modellere i 3D`` — written to disclaim CAD, and a model reading it
under pressure generalises "cannot draw".  A boundary attached to a capability
is scoped by the thing it qualifies:

    diagrams: single-line and interconnection for installations
      limit: board-level electronics (no GPIO, bus or header symbols)
      limit: native CAD formats (DWG, STEP) are not read

A free-floating negative gets over-generalised. A qualified one cannot.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal

SCHEMA_VERSION = 1

Confidence = Literal["shipped", "partial", "planned"]


@dataclass(frozen=True)
class Limit:
    """What a capability does *not* reach, stated next to what it does."""

    text: str
    reason: str = ""

    def to_dict(self) -> dict[str, str]:
        d = {"text": self.text}
        if self.reason:
            d["reason"] = self.reason
        return d


@dataclass
class Capability:
    id: str
    verb: str                        # "produce", "read", "check", "export"
    object: str                      # "single-line and interconnection diagrams"
    summary: str = ""                # one line the assistant may say
    domains: tuple[str, ...] = ()
    produces: tuple[str, ...] = ()   # "svg", "pdf", "md", "xlsx"
    limits: tuple[Limit, ...] = ()
    anchors: tuple[str, ...] = ()    # words that must appear for this to count as declared
    evidence: dict[str, Any] = field(default_factory=dict)   # counts, module, tests
    confidence: Confidence = "shipped"
    engine: str = ""

    @property
    def keywords(self) -> set[str]:
        """The declared claim: verb, object, domains. Never the summary.

        The summary is prose and will always contain accidental verbs — the
        privacy capability says "every model request", and matching on that made
        a denial about 3D *modelling* look like a contradiction. A capability's
        verb is declared, not inferred from a sentence about it.
        """
        raw = f"{self.verb} {self.object} {' '.join(self.domains)}"
        return {w for w in _words(raw) if len(w) > 3}

    def sentence(self) -> str:
        base = self.summary or f"{self.verb.capitalize()} {self.object}"
        if self.limits:
            base += " — " + "; ".join(l.text for l in self.limits[:2])
        return base

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "verb": self.verb,
            "object": self.object,
            "summary": self.summary or self.sentence(),
            "confidence": self.confidence,
        }
        for name, value in (("domains", self.domains), ("produces", self.produces)):
            if value:
                d[name] = list(value)
        if self.limits:
            d["limits"] = [l.to_dict() for l in self.limits]
        if self.evidence:
            d["evidence"] = dict(sorted(self.evidence.items()))
        if self.anchors:
            d["anchors"] = list(self.anchors)
        if self.engine:
            d["engine"] = self.engine
        return d


@dataclass
class Denial:
    """One line of the old ``cannot`` list, kept only so it can be checked."""

    text: str
    source: str = "capabilities.json"

    @property
    def keywords(self) -> set[str]:
        return {w for w in _words(self.text) if len(w) > 3}

    def to_dict(self) -> dict[str, str]:
        return {"text": self.text, "source": self.source}


@dataclass
class Drift:
    code: Literal["undeclared", "contradicted", "overclaimed", "unqualified_denial"]
    detail: str
    capability: str = ""
    denial: str = ""
    fix: str = ""

    @property
    def severity(self) -> str:
        return {
            "contradicted": "fail",     # the manifest actively denies a shipped feature
            "undeclared": "fail",       # the assistant will never mention it
            "overclaimed": "warn",      # the manifest promises what does not exist
            "unqualified_denial": "warn",
        }[self.code]

    def __str__(self) -> str:
        line = f"[{self.code}] {self.detail}"
        return f"{line}\n      fix: {self.fix}" if self.fix else line

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code, "severity": self.severity, "detail": self.detail,
            "capability": self.capability, "denial": self.denial, "fix": self.fix,
        }


@dataclass
class Reconciliation:
    capabilities: list[Capability] = field(default_factory=list)
    declared: list[str] = field(default_factory=list)
    denials: list[Denial] = field(default_factory=list)
    drift: list[Drift] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.drift

    @property
    def blocking(self) -> list[Drift]:
        return [d for d in self.drift if d.severity == "fail"]

    def of(self, code: str) -> list[Drift]:
        return [d for d in self.drift if d.code == code]

    def report(self) -> str:
        lines = [
            f"{len(self.capabilities)} capability(ies) found in the engines, "
            f"{len(self.declared)} declared in the manifest"
        ]
        if not self.drift:
            lines.append("no drift — the manifest says what the product does")
            return "\n".join(lines)
        lines.append(f"{len(self.blocking)} blocking, {len(self.drift) - len(self.blocking)} advisory")
        for d in self.drift:
            lines.append(f"  {d}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": self.ok,
            "capabilities": [c.to_dict() for c in self.capabilities],
            "declared": list(self.declared),
            "denials": [d.to_dict() for d in self.denials],
            "drift": [d.to_dict() for d in self.drift],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# Words that turn a denial into a generalisable one. "tegne" (draw) in a line
# about 3D teaches a model that drawing is impossible.
BROAD_VERBS: dict[str, str] = {
    "tegne": "draw", "draw": "draw", "drawing": "draw", "tegning": "draw",
    "diagram": "diagram", "diagrammer": "diagram", "diagrams": "diagram",
    "schematic": "diagram", "schematics": "diagram", "skjemaer": "diagram",
    "skjema": "diagram", "modellere": "model", "model": "model",
    # make / generate / produce are one act. Keeping them apart meant
    # "lage diagrammer" did not contradict "produce diagrams", which is the
    # contradiction most likely to appear in a hand-written cannot list.
    "generere": "produce", "generate": "produce", "lage": "produce",
    "make": "produce", "produsere": "produce", "produce": "produce",
    "vise": "show", "show": "show",
    # -ing forms, because limits are written in English prose and denials in
    # Norwegian; without these the two never match and the dangerous line stays.
    "modelling": "model", "modeling": "model", "drawings": "draw", "drawn": "draw",
    "producing": "produce", "generating": "generate", "showing": "show",
}


def _words(text: str) -> set[str]:
    import re

    return {w.lower() for w in re.findall(r"[0-9a-zA-ZÀ-ÿæøåÆØÅ_-]+", text or "")}
