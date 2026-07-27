"""Policy — a decision you can render, not an exception you have to catch.

The old shape was ``check()`` raises or passes.  That works for a script and is
useless for a UI: you cannot draw "this needs your approval, and here is why"
out of a stack trace.  So policy now returns a ``Decision`` — a verdict, the
reasons behind it, and what the user can do about it.

It also carries the thing masking does **not** solve, and this is worth stating
plainly because it is easy to oversell what the vault does:

    Masking protects identifiers. It does not protect findings.

    "CLIENT_A's weld failed inspection at 3 of 12 joints. VENDOR_A disputes
     the test method."

Every name is gone. The commercially and legally sensitive part is completely
intact — and in an engineering document that part is usually the finding, not
the letterhead. Deviations, failed tests, disputed workmanship, cost
consequences: none of that is anonymised by tokenising a company name.

There is no honest automatic fix for that, so this file does not pretend to one.
It detects the language of findings, marks the envelope, and hands the judgement
to the person — the same way the product handles evidential gaps. Flagging a
human is a real answer; a classifier that silently decides what is commercially
sensitive is not.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal

Verdict = Literal["allowed", "needs_approval", "blocked"]

# Language that signals a finding rather than a description. Deliberately small
# and bilingual — this is a prompt for human judgement, not a classifier.
FINDING_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("non_conformity", re.compile(
        r"\b(non[- ]?conformit\w*|avvik\w*|deviation|ikke godkjent|rejected|reject\b)", re.I)),
    ("failure", re.compile(
        r"\b(fail(?:ed|ure|s)?|feilet|underkjent|did not pass|out of tolerance|"
        r"exceeded the limit|crack\w*|sprekk\w*|leak(?:age|ing)?|lekkasje)", re.I)),
    ("dispute", re.compile(
        r"\b(disput\w*|uenig\w*|claim\w*|krav om|liabilit\w*|ansvar for|"
        r"penalt\w*|dagbot\w*|breach|mislighold)", re.I)),
    ("commercial", re.compile(
        r"\b(price|pris\b|cost overrun|kostnadsoverskridelse|contract sum|"
        r"kontraktsum|margin|rate card|confidential|konfidensiell)", re.I)),
    ("personal", re.compile(
        r"\b(sick leave|sykemeld\w*|injur\w*|skade p\w+ person|accident|ulykke|"
        r"disciplinar\w*|personalsak)", re.I)),
)


@dataclass(frozen=True)
class Flag:
    code: str
    excerpt: str
    note: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "excerpt": self.excerpt, "note": self.note}


def content_flags(text: str, *, limit: int = 6) -> list[Flag]:
    """Findings-language in outbound text.  Advisory, never automatic."""
    out: list[Flag] = []
    seen: set[str] = set()
    for code, pattern in FINDING_PATTERNS:
        for m in pattern.finditer(text or ""):
            if code in seen:
                break
            seen.add(code)
            start, end = max(0, m.start() - 35), min(len(text), m.end() + 35)
            out.append(
                Flag(
                    code=code,
                    excerpt="…" + text[start:end].strip() + "…",
                    note="masking removes names, not findings — decide whether this may leave",
                )
            )
            if len(out) >= limit:
                return out
    return out


@dataclass
class Reason:
    code: str
    message: str
    fix: str = ""

    def __str__(self) -> str:
        return f"{self.message}" + (f" — {self.fix}" if self.fix else "")

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "fix": self.fix}


@dataclass
class Decision:
    verdict: Verdict
    reasons: list[Reason] = field(default_factory=list)
    flags: list[Flag] = field(default_factory=list)

    @property
    def allowed(self) -> bool:
        return self.verdict == "allowed"

    @property
    def blocked(self) -> bool:
        return self.verdict == "blocked"

    @property
    def needs_approval(self) -> bool:
        return self.verdict == "needs_approval"

    def add(self, verdict: Verdict, code: str, message: str, fix: str = "") -> "Decision":
        self.reasons.append(Reason(code, message, fix))
        rank = {"allowed": 0, "needs_approval": 1, "blocked": 2}
        if rank[verdict] > rank[self.verdict]:
            self.verdict = verdict
        return self

    def summary(self) -> str:
        head = {
            "allowed": "Allowed",
            "needs_approval": "Needs your approval",
            "blocked": "Blocked",
        }[self.verdict]
        if not self.reasons and not self.flags:
            return head
        bits = [str(r) for r in self.reasons] + [f.code for f in self.flags]
        return f"{head}: " + "; ".join(bits)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "reasons": [r.to_dict() for r in self.reasons],
            "flags": [f.to_dict() for f in self.flags],
        }


@dataclass(frozen=True)
class Policy:
    """Defaults chosen so the safe thing happens when nobody is watching."""

    allow_images: bool = False
    max_bytes: int = 60_000
    allowed_purposes: tuple[str, ...] = ()          # filled by client from PURPOSES
    require_approval: bool = False                  # every call
    approve_on_flags: bool = True                   # findings-language needs a human
    strict_masking: bool = True
    redact_uncertain: bool = False
    require_structured_payload: tuple[str, ...] = ("gap_fill_code",)
    name: str = "default"

    def describe(self) -> str:
        bits = [
            f"images {'allowed' if self.allow_images else 'blocked'}",
            f"max {self.max_bytes:,} bytes/call",
            f"masking {'strict' if self.strict_masking else 'best effort'}",
        ]
        if self.require_approval:
            bits.append("every call approved by a person")
        elif self.approve_on_flags:
            bits.append("approval when findings are detected")
        return " · ".join(bits)

    def decide(self, envelope: Any) -> Decision:
        d = Decision("allowed")

        if self.allowed_purposes and envelope.purpose not in self.allowed_purposes:
            d.add("blocked", "purpose_not_allowed",
                  f"'{envelope.purpose}' is not permitted by the {self.name} policy",
                  "change the policy deliberately, or do this step locally")

        unapproved = [i for i in envelope.images if not i.approved]
        if unapproved and not self.allow_images:
            d.add("blocked", "images_blocked",
                  f"{len(unapproved)} image(s) would leave unmasked",
                  "a photograph cannot be masked — approve each image individually")

        if envelope.bytes > self.max_bytes:
            d.add("blocked", "over_budget",
                  f"{envelope.bytes:,} bytes exceeds the {self.max_bytes:,} byte budget",
                  "split the passage, or raise the budget deliberately")

        if not envelope.text.strip() and not envelope.images:
            d.add("blocked", "empty", "nothing to send")

        if envelope.purpose in self.require_structured_payload and not envelope.meta.get("structured"):
            d.add("blocked", "unstructured_payload",
                  f"'{envelope.purpose}' may only carry a structured descriptor",
                  "send the gap record, not free project text")

        flags = content_flags(envelope.text)
        d.flags.extend(flags)
        if flags and self.approve_on_flags:
            d.add("needs_approval", "findings_detected",
                  f"{len(flags)} passage(s) read like findings, not description",
                  "masking removes names, not findings — read what leaves before approving")

        if self.require_approval:
            d.add("needs_approval", "policy_requires_approval",
                  "this policy asks a person to approve every call")

        return d


# ----------------------------------------------------------------------
DEFAULT = Policy(name="default")

STRICT = Policy(
    name="strict",
    allow_images=False,
    max_bytes=12_000,
    require_approval=True,
    approve_on_flags=True,
    strict_masking=True,
    redact_uncertain=True,
)

OPEN = Policy(
    name="open",
    allow_images=True,
    max_bytes=250_000,
    require_approval=False,
    approve_on_flags=False,
    redact_uncertain=False,
)

OFFLINE = Policy(name="offline", allowed_purposes=("__none__",))

PRESETS: dict[str, Policy] = {p.name: p for p in (DEFAULT, STRICT, OPEN, OFFLINE)}


def preset(name: str) -> Policy:
    try:
        return PRESETS[name]
    except KeyError as exc:
        raise ValueError(f"unknown policy '{name}'; known: {sorted(PRESETS)}") from exc
