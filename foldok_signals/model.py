"""Signals — content-free by construction.

The trap this package exists to avoid: Foldok's pitch is "106 engine files make
zero network calls" and "here is everything that left this machine".  If the
product then phones home with usage data, the first engineer who opens the
network tab finds it, and the trust story dies in one screenshot.  These users
are exactly the people who check.

So analytics obeys the same discipline as the model calls.  And "content-free"
is enforced rather than requested:

*  An event carries **counters** (numbers) and **codes** (values from a
   registered vocabulary).  Nothing else.
*  A string that is not in the vocabulary is refused at construction.  You
   cannot accidentally log a file name, a client, or a sentence of a document,
   because there is no field that would accept one.
*  Anything shaped like a path, an email or a Windows drive letter is refused
   even if someone registers it, as a second line of defence.

Feedback is deliberately a **separate type**.  Feedback is text a person chose
to write and can edit before it sends.  Telemetry is integers nobody typed.
Mixing them is how privacy-respecting analytics turns into a leak: the moment
one event field accepts free text, everything ends up in it.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal, Mapping

SCHEMA_VERSION = 1

# The whole vocabulary. Ten kinds of thing, because at three users a funnel with
# forty events is noise wearing a lab coat.
EVENTS: tuple[str, ...] = (
    # the one funnel that matters
    "folder_opened", "index_finished", "gaps_shown", "gap_resolved", "document_exported",
    # diagnosis
    "extraction_failed", "call_refused", "layout_overflow", "pack_refused", "blocked_me",
    # lifecycle
    "session_started", "consent_changed",
)

# Allowed values per code field. Anything else raises.
VOCAB: dict[str, frozenset[str]] = {
    "file_type": frozenset({
        "pdf", "docx", "xlsx", "csv", "txt", "md", "json", "image", "dwg", "other",
    }),
    "reason": frozenset({
        # policy / private-call refusals
        "over_budget", "images_blocked", "purpose_not_allowed", "empty",
        "unstructured_payload", "findings_detected", "policy_requires_approval",
        "leak_refused",
        # extraction
        "no_text", "unsupported_format", "corrupt", "encrypted",
        # layout / diagram / packs
        "locked_block", "band_too_tall", "illegal_medium", "pipe_branch_without_fitting",
        "redistribution", "missing_dependency", "unknown_asset",
        # gaps
        "no_resolver", "evidential_guard",
        "other",
    }),
    "resolver": frozenset({
        "measurement_form", "photo_capture", "table_form", "upload", "signature",
        "diagram_scaffold", "diagram_draft", "text_draft", "not_applicable", "defer",
    }),
    "surface": frozenset({
        "workbench", "editor", "diagram", "gaps", "export", "settings", "web", "other",
    }),
    "mode": frozenset({"build", "review", "compliance"}),
    "outcome": frozenset({"ok", "refused", "failed", "abandoned"}),
}

# Second line of defence: shapes that must never appear in a code value.
FORBIDDEN = re.compile(
    r"([A-Za-z]:\\)|(/(?:home|Users|mnt|var)/)|(@[\w.-]+\.\w{2,})|(\.[a-z]{2,4}$)|(\s)"
)

Kind = Literal["event", "feedback"]


class SignalRefused(Exception):
    """Something that is not content-free was about to be recorded."""


def new_install_id() -> str:
    """Random, not derived from anything about the machine or the person."""
    return uuid.uuid4().hex[:16]


def _check_code(field_name: str, value: str) -> str:
    allowed = VOCAB.get(field_name)
    if allowed is None:
        raise SignalRefused(
            f"'{field_name}' is not a registered code field. Add it to VOCAB with the exact "
            f"set of values it may take — a field that accepts arbitrary strings is how a "
            f"file name ends up in analytics."
        )
    if value not in allowed:
        raise SignalRefused(
            f"'{value}' is not a permitted value for '{field_name}'. "
            f"Permitted: {', '.join(sorted(allowed))}. Add it deliberately, or use 'other'."
        )
    if FORBIDDEN.search(value):
        raise SignalRefused(f"'{value}' looks like a path, address or filename")
    return value


@dataclass
class Event:
    name: str
    counters: dict[str, float] = field(default_factory=dict)
    codes: dict[str, str] = field(default_factory=dict)
    at: float = field(default_factory=time.time)
    session: str = ""

    def __post_init__(self) -> None:
        if self.name not in EVENTS:
            raise SignalRefused(
                f"'{self.name}' is not a registered event. Known: {', '.join(EVENTS)}. "
                "Ten event types is deliberate — at this stage you need signal, not a "
                "dashboard."
            )
        for key, value in list(self.counters.items()):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise SignalRefused(
                    f"counter '{key}' must be a number; got {type(value).__name__}. "
                    "Counters are integers nobody typed."
                )
        for key, value in list(self.codes.items()):
            self.codes[key] = _check_code(key, str(value))

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"at": round(self.at, 3), "name": self.name}
        if self.session:
            d["session"] = self.session
        if self.counters:
            d["counters"] = {k: round(v, 3) for k, v in sorted(self.counters.items())}
        if self.codes:
            d["codes"] = dict(sorted(self.codes.items()))
        return d

    @staticmethod
    def from_dict(d: Mapping[str, Any]) -> "Event":
        return Event(
            name=d["name"],
            counters=dict(d.get("counters", {})),
            codes=dict(d.get("codes", {})),
            at=float(d.get("at", 0.0)),
            session=d.get("session", ""),
        )


@dataclass
class Feedback:
    """Text a person chose to write.

    Separate type on purpose. Feedback is reviewed and editable before it sends;
    telemetry is not text at all. The moment one event field accepts free text,
    everything ends up in it.
    """

    kind: Literal["bug", "idea", "blocked", "praise", "other"] = "other"
    message: str = ""
    surface: str = "other"
    contact: str = ""                      # optional, the user types it or does not
    context: list[dict[str, Any]] = field(default_factory=list)   # content-free trail
    at: float = field(default_factory=time.time)
    sent: bool = False

    def __post_init__(self) -> None:
        self.surface = _check_code("surface", self.surface)

    @property
    def has_contact(self) -> bool:
        return bool(self.contact.strip())

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "at": round(self.at, 3),
            "kind": self.kind,
            "surface": self.surface,
            "message": self.message,
        }
        if self.contact:
            d["contact"] = self.contact
        if self.context:
            d["context"] = self.context
        return d

    def preview(self, width: int = 74) -> str:
        """Shown before sending, and editable. Same move as the envelope panel."""
        lines = [
            "WHAT THIS REPORT SENDS",
            f"  type      {self.kind}",
            f"  where     {self.surface}",
            f"  contact   {self.contact or '(none — we cannot reply)'}",
            f"  history   {len(self.context)} content-free event(s)",
            "",
            "Your message:",
            "-" * width,
        ]
        lines += [self.message or "(empty)"]
        lines += ["-" * width]
        if self.context:
            lines.append("Attached history (numbers and codes only, no file or project names):")
            for row in self.context[-8:]:
                bits = " ".join(f"{k}={v}" for k, v in sorted(row.get("codes", {}).items()))
                lines.append(f"  {row.get('name')} {bits}".rstrip())
        return "\n".join(lines)


def scrub_context(events: Iterable[Event], limit: int = 20) -> list[dict[str, Any]]:
    """The trail attached to a bug report: the same content-free events, nothing more."""
    rows = [e.to_dict() for e in list(events)[-limit:]]
    for row in rows:
        row.pop("session", None)
    return rows


def vocabulary() -> dict[str, Any]:
    """What the consent screen shows. The whole list, not a summary."""
    return {
        "schema_version": SCHEMA_VERSION,
        "events": list(EVENTS),
        "code_fields": {k: sorted(v) for k, v in sorted(VOCAB.items())},
        "never_collected": [
            "file names", "folder paths", "project names", "client names",
            "document text", "diagram contents", "measured values",
            "the entity vault", "IP addresses",
        ],
    }


def vocabulary_json(indent: int = 2) -> str:
    return json.dumps(vocabulary(), indent=indent, ensure_ascii=False)
