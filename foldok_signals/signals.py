"""The signals facade.

Two ideas do most of the work here, and neither is a dashboard.

**Every refusal is feedback.**  ``CallRefused``, ``LayoutRefused``,
``PackRefused``, ``ConnectRefused``, ``ResolverRefused``, ``LeakRefused``,
``ExportRefused`` — each one is a moment where the product said no to somebody
trying to work.  ``on_refusal`` turns any of them into a counter, and the UI
puts a one-tap **"this blocked me"** on the message itself.  That is feedback at
the point of friction, which is the only moment anyone bothers.

**Feedback and telemetry are governed differently.**  Telemetry needs consent
because nobody asked for it.  A bug report does not: the user typed it and
pressed send.  Conflating the two either blocks people from reporting bugs, or
smuggles analytics in under the word "feedback".  Both are worse than keeping
them apart.

A bug report attaches the recent content-free trail — purposes, counts, error
codes — shown to the user and editable before it leaves.  Any file the user
attaches goes through ``assert_exportable``, so the entity vault physically
cannot ride along.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Protocol, Sequence, runtime_checkable

from .journey import FUNNEL, Consent, EventLog, Funnel, failure_summary, funnel
from .model import Event, Feedback, SignalRefused, scrub_context, vocabulary

# Exception class name -> reason code. Matching by name keeps this package
# dependency-free: it hooks the other engines without importing them.
REFUSAL_REASONS: dict[str, str] = {
    "CallRefused": "other",
    "LeakRefused": "leak_refused",
    "ExportRefused": "other",
    "LayoutRefused": "locked_block",
    "PackRefused": "redistribution",
    "ConnectRefused": "illegal_medium",
    "ResolverRefused": "no_resolver",
    "EvidentialGuard": "evidential_guard",
}

# Substrings in a refusal message that identify a more precise reason. Only ever
# used to pick a code from the fixed vocabulary — the message itself is never
# recorded, because it can quote the user's content.
MESSAGE_HINTS: tuple[tuple[str, str], ...] = (
    ("budget", "over_budget"),
    ("image", "images_blocked"),
    ("not permitted", "purpose_not_allowed"),
    ("nothing to send", "empty"),
    ("structured", "unstructured_payload"),
    ("findings", "findings_detected"),
    ("approve every call", "policy_requires_approval"),
    ("locked block", "locked_block"),
    ("too tall", "band_too_tall"),
    ("fitting", "pipe_branch_without_fitting"),
    ("redistribut", "redistribution"),
    ("not in the library", "unknown_asset"),
    ("unresolved dependencies", "missing_dependency"),
    ("OCR", "no_text"),
    ("no extractor", "unsupported_format"),
    ("encrypted", "encrypted"),
)


@runtime_checkable
class Sink(Protocol):
    id: str

    def send(self, events: Sequence[Event], install_id: str) -> int: ...

    def send_feedback(self, feedback: Feedback, install_id: str) -> bool: ...


@dataclass
class LocalSink:
    """Default. Nothing leaves; the log is still useful for the Activity panel
    and for bug reports."""

    id: str = "local"
    sent: list[Event] = field(default_factory=list)
    reports: list[Feedback] = field(default_factory=list)

    def send(self, events: Sequence[Event], install_id: str) -> int:
        self.sent.extend(events)
        return len(events)

    def send_feedback(self, feedback: Feedback, install_id: str) -> bool:
        self.reports.append(feedback)
        return True


class Signals:
    def __init__(
        self,
        log: EventLog | str | Path | None = None,
        consent: Consent | None = None,
        sink: Sink | None = None,
        surface: str = "workbench",
        clock=time.time,
    ) -> None:
        self.log = log if isinstance(log, EventLog) else EventLog(log, clock=clock)
        self.consent = consent or Consent()
        self.sink = sink or LocalSink()
        self.surface = surface
        self._clock = clock
        self.session = uuid.uuid4().hex[:12]
        self._unsent: list[Event] = []

    # -- recording --------------------------------------------------------
    def record(self, name: str, **fields: Any) -> Event:
        counters = {k: v for k, v in fields.items() if isinstance(v, (int, float))
                    and not isinstance(v, bool)}
        codes = {k: v for k, v in fields.items() if isinstance(v, str)}
        event = Event(name=name, counters=counters, codes=codes,
                      at=self._clock(), session=self.session)
        self.log.add(event)
        self._unsent.append(event)
        return event

    # -- the funnel, one method per stage ---------------------------------
    def folder_opened(self, files: int = 0) -> Event:
        return self.record("folder_opened", files=files, surface=self.surface)

    def index_finished(self, files: int, chunks: int, seconds: float, failed: int = 0) -> Event:
        return self.record("index_finished", files=files, chunks=chunks,
                           seconds=round(seconds, 2), failed=failed)

    def gaps_shown(self, total: int, blocking: int = 0, mode: str = "build") -> Event:
        return self.record("gaps_shown", total=total, blocking=blocking, mode=mode)

    def gap_resolved(self, resolver: str, seconds: float = 0.0) -> Event:
        return self.record("gap_resolved", resolver=resolver, seconds=round(seconds, 2))

    def document_exported(self, pages: int = 0, gaps_open: int = 0, mode: str = "build") -> Event:
        return self.record("document_exported", pages=pages, gaps_open=gaps_open, mode=mode)

    # -- diagnosis ---------------------------------------------------------
    def extraction_failed(self, file_type: str, reason: str) -> Event:
        return self.record("extraction_failed", file_type=file_type, reason=reason)

    def layout_overflow(self, blocks: int = 1) -> Event:
        return self.record("layout_overflow", blocks=blocks, surface="editor")

    def on_refusal(self, exc: BaseException, *, surface: str | None = None) -> Event | None:
        """Hook this into every ``except`` that shows a refusal to a user.

        The exception *message* is never recorded — refusal messages quote the
        user's content on purpose, which is what makes them good UX and unfit
        for analytics. Only the class and a vocabulary code are kept.
        """
        name = type(exc).__name__
        if name not in REFUSAL_REASONS:
            return None
        reason = REFUSAL_REASONS[name]
        message = str(exc).lower()
        for needle, code in MESSAGE_HINTS:
            if needle.lower() in message:
                reason = code
                break
        event_name = {
            "PackRefused": "pack_refused",
            "LeakRefused": "call_refused",
            "CallRefused": "call_refused",
        }.get(name, "call_refused")
        try:
            return self.record(event_name, reason=reason, surface=surface or self.surface)
        except SignalRefused:
            return self.record(event_name, reason="other", surface=surface or self.surface)

    def blocked_me(self, reason: str = "other", surface: str | None = None) -> Event:
        """The one-tap button on any refusal message. The strongest signal you
        get, because it costs the user nothing at the moment it matters."""
        return self.record("blocked_me", reason=reason, surface=surface or self.surface)

    # -- consent -----------------------------------------------------------
    def ask_consent(self) -> str:
        return Consent.prompt()

    def grant(self) -> Consent:
        self.consent.grant(self._clock)
        self.record("consent_changed", outcome="ok")
        return self.consent

    def revoke(self, *, purge: bool = True) -> int:
        self.consent.revoke(self._clock)
        self._unsent = []
        return self.log.purge() if purge else 0

    # -- sending -----------------------------------------------------------
    def flush(self) -> int:
        """Send pending events, if and only if consent was given."""
        if not self.consent.may_send or not self._unsent:
            return 0
        n = self.sink.send(tuple(self._unsent), self.consent.install_id)
        self._unsent = []
        return n

    # -- feedback ----------------------------------------------------------
    def feedback(
        self,
        kind: str,
        message: str,
        *,
        contact: str = "",
        surface: str | None = None,
        attach_history: bool = True,
        history: int = 20,
    ) -> Feedback:
        """Build a report. Nothing is sent until ``send_feedback``."""
        return Feedback(
            kind=kind,                       # type: ignore[arg-type]
            message=message,
            surface=surface or self.surface,
            contact=contact,
            context=scrub_context(self.log.events(), history) if attach_history else [],
            at=self._clock(),
        )

    def send_feedback(self, feedback: Feedback, *, approved: bool = False) -> bool:
        """A bug report does not need telemetry consent — the user typed it and
        pressed send. It does need them to have seen what goes with it."""
        if not approved:
            raise SignalRefused(
                "show feedback.preview() first and pass approved=True. A report that "
                "attaches a history the user has not seen is the thing this product "
                "exists not to do."
            )
        if not feedback.message.strip():
            raise SignalRefused("an empty report tells us nothing; ask for one sentence")
        ok = self.sink.send_feedback(feedback, self.consent.install_id or "anonymous")
        feedback.sent = ok
        return ok

    def bug_report(
        self,
        message: str,
        *,
        files: Sequence[str | Path] = (),
        contact: str = "",
        surface: str | None = None,
    ) -> tuple[Feedback, list[Path]]:
        """A report plus attachments, with the vault physically excluded.

        ``assert_exportable`` lives in foldok_private and is imported softly, so
        this package stays standalone — but when it is present, a vault cannot
        be attached to a bug report even by accident.
        """
        attachments = [Path(f) for f in files]
        if attachments:
            try:
                from foldok_private.atrest import assert_exportable  # noqa: PLC0415

                assert_exportable(attachments, what="bug report")
            except ImportError:  # pragma: no cover
                from .model import FORBIDDEN  # noqa: PLC0415, F401

                bad = [p for p in attachments if p.name.lower().endswith((".vault", ".jsonl"))]
                if bad:
                    raise SignalRefused(
                        f"refusing to attach {', '.join(p.name for p in bad)} — these can "
                        "contain the entity vault, which stays on this machine"
                    ) from None
        return self.feedback("bug", message, contact=contact, surface=surface), attachments

    # -- the Activity panel -------------------------------------------------
    def activity(self, *, since: float = 0.0) -> dict[str, Any]:
        """Everything the Trust Center shows. Safe to display to anyone."""
        events = self.log.events(since=since)
        f = funnel(events)
        return {
            "consent": self.consent.to_dict(),
            "sink": self.sink.id,
            "session": self.session,
            "events_recorded": len(events),
            "events_pending": len(self._unsent),
            "counts": self.log.counts(),
            "funnel": {stage: f.stages.get(stage, 0) for stage in FUNNEL},
            "worst_step": f.worst_step[0] if f.worst_step else None,
            "failures": failure_summary(events),
            "vocabulary": vocabulary(),
        }

    def report(self) -> str:
        events = self.log.events()
        lines = [funnel(events).report(), ""]
        failures = failure_summary(events)
        if failures:
            lines.append("Where it said no:")
            for name, reasons in failures.items():
                top = ", ".join(f"{k} ({v})" for k, v in list(reasons.items())[:4])
                lines.append(f"  {name:<20} {top}")
        else:
            lines.append("No refusals recorded.")
        lines.append("")
        lines.append(
            f"Telemetry: {'on' if self.consent.may_send else 'off'} · "
            f"{len(self.log)} event(s) recorded locally · sink '{self.sink.id}'"
        )
        return "\n".join(lines)
