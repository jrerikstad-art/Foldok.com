"""Claims — because engineering knowledge is mostly not quantities.

The evidence that forced this file: given a folder of EMC standards and cable
tray datasheets, Foldok's extractor returned eight facts — an author, a product
name, a test lab, `measurement equipment capability = 100 dB`. NotebookLM, on the
same folder, produced a six-class cable taxonomy, the conducted/radiated
distinction, aggressor versus victim, three explicit hypotheses and five ranked
risks.

Count how many of those are (key, value, unit, source). Zero.

They are definitions, classifications, conditional rules, distinctions,
hypotheses and risks. That is what the knowledge in a standards library *is*, and
the fact schema had nowhere to put any of it. So the extractor asked for
parameters and faithfully returned the only eight it could find, and every
section downstream had nothing else to say.

A Claim is the wider container. A quantity is one kind of claim, not the only
kind.

Two fields do the work that makes claims worth more than prose:

``modality``  shall / should / may / is — an obligation is not a description, and
              a hypothesis is not a finding. Collapsing them is how a proposal
              gets read as a requirement.
``scope``     the conditions under which the claim holds: frequency band, cable
              class, environment. Two claims only conflict if their scopes
              overlap, and without scope every comparison is a guess.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal

SCHEMA_VERSION = 1

ClaimType = Literal[
    "quantity",        # 70-120 dB attenuation           (the old Fact)
    "definition",      # EMC is the ability to ...
    "classification",  # Class 1A covers millivolt transducers
    "rule",            # shielded cable shall be used
    "constraint",      # at most two threads may protrude
    "practice",        # 45 degree radii are preferred
    "distinction",     # conducted noise differs from radiated
    "hypothesis",      # wire trays may outperform closed trays
    "risk",            # EMC faults are not measurable until in service
    "reference",       # verified against IEC 61914:2021
]

Modality = Literal["shall", "should", "may", "is", "hypothesis"]

# Which types are obligations. A rule and a practice are not the same weight,
# and a hypothesis is not an obligation at all.
BINDING: tuple[str, ...] = ("rule", "constraint")


@dataclass(frozen=True)
class Quantity:
    """A number or a range, with a unit. Comparable, which is the point."""

    low: float | None = None
    high: float | None = None
    unit: str = ""
    raw: str = ""

    @property
    def known(self) -> bool:
        return self.low is not None or self.high is not None

    def overlaps(self, other: "Quantity") -> bool:
        if not (self.known and other.known) or self.unit != other.unit:
            return False
        a_lo = self.low if self.low is not None else float("-inf")
        a_hi = self.high if self.high is not None else float("inf")
        b_lo = other.low if other.low is not None else float("-inf")
        b_hi = other.high if other.high is not None else float("inf")
        return a_lo <= b_hi and b_lo <= a_hi

    def covers(self, other: "Quantity") -> bool:
        """Does this range contain the whole of the other?"""
        if not (self.known and other.known) or self.unit != other.unit:
            return False
        a_lo = self.low if self.low is not None else float("-inf")
        a_hi = self.high if self.high is not None else float("inf")
        b_lo = other.low if other.low is not None else float("-inf")
        b_hi = other.high if other.high is not None else float("inf")
        return a_lo <= b_lo and b_hi <= a_hi

    def __str__(self) -> str:
        if self.low is not None and self.high is not None and self.low != self.high:
            return f"{_num(self.low)}–{_num(self.high)} {self.unit}".strip()
        value = self.low if self.low is not None else self.high
        return f"{_num(value)} {self.unit}".strip() if value is not None else self.raw

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        for k in ("low", "high"):
            v = getattr(self, k)
            if v is not None:
                d[k] = v
        if self.unit:
            d["unit"] = self.unit
        return d


@dataclass(frozen=True)
class Scope:
    """When and where a claim holds. Without this, conflicts cannot be judged."""

    frequency: Quantity | None = None      # 150 kHz – 1 GHz
    cable_class: str = ""                  # "1A", "4", "6"
    environment: str = ""                  # "HVDC platform", "offshore"
    note: str = ""

    @property
    def known(self) -> bool:
        return bool(self.frequency or self.cable_class or self.environment)

    def overlaps(self, other: "Scope") -> bool:
        """Unscoped claims are treated as universal, so they overlap everything.

        That is the safe reading: a rule stated without a limit is usually meant
        to apply generally, and treating it as narrow would hide real conflicts.
        """
        if self.cable_class and other.cable_class and self.cable_class != other.cable_class:
            return False
        if self.frequency and other.frequency and not self.frequency.overlaps(other.frequency):
            return False
        return True

    def __str__(self) -> str:
        bits = []
        if self.frequency:
            bits.append(str(self.frequency))
        if self.cable_class:
            bits.append(f"class {self.cable_class}")
        if self.environment:
            bits.append(self.environment)
        return ", ".join(bits) or "unscoped"

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.frequency:
            d["frequency"] = self.frequency.to_dict()
        for k in ("cable_class", "environment", "note"):
            if getattr(self, k):
                d[k] = getattr(self, k)
        return d


@dataclass
class Claim:
    id: str
    type: ClaimType
    subject: str                      # what the claim is about
    text: str                         # the claim in Foldok's words, not the source's
    modality: Modality = "is"
    predicate: str = ""               # normalised property: "attenuation", "shielding"
    quantity: Quantity | None = None
    scope: Scope = field(default_factory=Scope)
    source: str = ""                  # file id
    citation: str = ""
    negated: bool = False             # "armering alene er en dårlig skjerm"
    confidence: float = 0.6

    @property
    def binding(self) -> bool:
        return self.type in BINDING and self.modality in ("shall", "should")

    @property
    def contestable(self) -> bool:
        return self.type == "hypothesis" or self.modality == "hypothesis"

    def key(self) -> str:
        return f"{_norm(self.subject)}|{_norm(self.predicate or self.type)}"

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "subject": self.subject,
            "text": self.text,
            "modality": self.modality,
            "confidence": round(self.confidence, 2),
        }
        for k in ("predicate", "source", "citation"):
            if getattr(self, k):
                d[k] = getattr(self, k)
        if self.quantity:
            d["quantity"] = self.quantity.to_dict()
        if self.scope.known:
            d["scope"] = self.scope.to_dict()
        if self.negated:
            d["negated"] = True
        return d

    def __str__(self) -> str:
        head = f"[{self.type}/{self.modality}] {self.subject}: {self.text}"
        if self.scope.known:
            head += f"  ({self.scope})"
        return head


def claim_id(source: str, text: str) -> str:
    return hashlib.sha1(f"{source}|{_norm(text)}".encode("utf-8")).hexdigest()[:12]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _num(value: float | None) -> str:
    if value is None:
        return ""
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


@dataclass
class ClaimSet:
    claims: list[Claim] = field(default_factory=list)

    def __iter__(self) -> Iterable[Claim]:
        return iter(self.claims)

    def __len__(self) -> int:
        return len(self.claims)

    def of_type(self, *types: str) -> list[Claim]:
        return [c for c in self.claims if c.type in types]

    def binding(self) -> list[Claim]:
        return [c for c in self.claims if c.binding]

    def hypotheses(self) -> list[Claim]:
        return [c for c in self.claims if c.contestable]

    def by_subject(self) -> dict[str, list[Claim]]:
        out: dict[str, list[Claim]] = {}
        for c in self.claims:
            out.setdefault(_norm(c.subject), []).append(c)
        return out

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for c in self.claims:
            out[c.type] = out.get(c.type, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "count": len(self.claims),
            "counts": self.counts(),
            "claims": [c.to_dict() for c in self.claims],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
