"""Authoring — intent decides how to write, facts decide what may be said.

Built after a specific failure: a fact ledger of (key, value, unit, source) fed
straight to a model produces pages of "Parameter | Verdi | Enhet | Kilde",
because that is all the generator was given. Intent fixes the phrasing.

It does **not** fix what is available to say, and that distinction is the whole
reason this package is smaller than the design that prompted it.

Two intents ship. Four do not, and the refusal is deliberate:

    describe_component, specify_parameters, declare_conformity,
    record_evidence, identify_product, summarize_system     -> fact-shaped

    instruct_procedure, troubleshoot, warn_hazard, explain_process
        -> need an action, an order, a precondition and a failure branch.
           None of those are in a (key, value, unit) tuple, and none of them
           are in a datasheet. The procedure lives in the builder's head.

Writing them anyway turns an obviously bad document into a convincingly bad
one, and somebody signs the convincing kind. Procedures are authored (see
procedure.py), not generated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

SCHEMA_VERSION = 1

IntentId = Literal[
    "describe_component", "specify_parameters", "declare_conformity",
    "record_evidence", "identify_product", "summarize_system",
]

# Named so a caller asking for one gets a straight answer rather than silence.
AUTHORED_NOT_GENERATED: tuple[str, ...] = (
    "instruct_procedure", "troubleshoot", "warn_hazard", "explain_process",
)


@dataclass(frozen=True)
class Fact:
    id: str
    key: str
    value: Any
    unit: str = ""
    label: str = ""
    citation: str = ""

    def phrase(self) -> str:
        bit = f"{self.label or self.key.replace('_', ' ')} = {self.value}"
        return f"{bit} {self.unit}".strip()

    def tokens(self) -> set[str]:
        out = {str(self.value).lower()}
        if self.unit:
            out.add(f"{self.value} {self.unit}".lower())
        if self.label:
            out.add(self.label.lower())
        return {t for t in out if t}


@dataclass
class Claim:
    text: str
    fact_ids: list[str] = field(default_factory=list)
    status: Literal["grounded", "ungrounded", "unverifiable"] = "ungrounded"
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = {"text": self.text, "fact_ids": list(self.fact_ids), "status": self.status}
        if self.reason:
            d["reason"] = self.reason
        return d


@dataclass
class Plan:
    intent: IntentId
    beats: list[str]
    fact_ids: list[str]
    must_include: list[str]
    style: list[str] = field(default_factory=list)


@dataclass
class Result:
    intent: IntentId
    prose: str
    plan: Plan
    claims: list[Claim] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    unused_facts: list[str] = field(default_factory=list)

    @property
    def grounded(self) -> bool:
        return not any(c.status != "grounded" for c in self.claims)

    @property
    def publishable(self) -> bool:
        """Grounded, and it actually used the facts it was told to use."""
        return self.grounded and not self.unused_facts

    def report(self) -> str:
        lines = [f"{self.intent}: {len(self.claims)} claim(s), "
                 f"{'grounded' if self.grounded else str(len(self.gaps)) + ' ungrounded'}"]
        for c in self.claims:
            if c.status != "grounded":
                lines.append(f"  [{c.status}] {c.text}"
                             + (f" — {c.reason}" if c.reason else ""))
        if self.unused_facts:
            lines.append(f"  facts required but not used: {', '.join(self.unused_facts)}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "intent": self.intent,
            "prose": self.prose,
            "grounded": self.grounded,
            "publishable": self.publishable,
            "gaps": list(self.gaps),
            "unused_facts": list(self.unused_facts),
            "claims": [c.to_dict() for c in self.claims],
        }


class IntentRefused(Exception):
    """Asked for an intent this engine will not generate, and why."""
