"""Consent, storage, and the one funnel.

**Consent is opt-in and asks once, plainly, with the full event list visible.**
Opt-out telemetry from a product sold on privacy is the exact hypocrisy people
screenshot.  Expect roughly 40% to say yes, which at this stage is fine: you do
not need statistics, you need signal, and forty percent of a handful of users is
still every one of them you can phone.

**Everything is written locally first.**  The log exists whether or not consent
was given — it is how the product diagnoses itself, and how a bug report has a
trail.  Consent governs *sending*, not recording, and revoking it purges what
was recorded.

**One funnel.**  At three users, cohorts and retention curves are noise wearing
a lab coat.  Where people stop is the only number that can change what you build
this week:

    folder opened -> indexed -> gaps shown -> first gap resolved -> exported
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from .model import Event, Feedback, new_install_id, vocabulary

FUNNEL: tuple[str, ...] = (
    "folder_opened",
    "index_finished",
    "gaps_shown",
    "gap_resolved",
    "document_exported",
)

FUNNEL_LABELS: dict[str, str] = {
    "folder_opened": "opened a folder",
    "index_finished": "finished indexing",
    "gaps_shown": "saw the gap list",
    "gap_resolved": "resolved a first gap",
    "document_exported": "exported a document",
}


@dataclass
class Consent:
    """Recorded once, revocable, and purging is real."""

    granted: bool = False
    asked: bool = False
    install_id: str = ""
    at: float = 0.0
    version: int = 1

    @property
    def may_send(self) -> bool:
        return self.granted and bool(self.install_id)

    def grant(self, clock=time.time) -> "Consent":
        self.granted = True
        self.asked = True
        self.install_id = self.install_id or new_install_id()
        self.at = clock()
        return self

    def revoke(self, clock=time.time) -> "Consent":
        self.granted = False
        self.asked = True
        self.install_id = ""          # the pseudonym goes too, or it is not a revocation
        self.at = clock()
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "granted": self.granted, "asked": self.asked,
            "install_id": self.install_id, "at": round(self.at, 3), "version": self.version,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Consent":
        return Consent(
            granted=bool(d.get("granted", False)), asked=bool(d.get("asked", False)),
            install_id=d.get("install_id", ""), at=float(d.get("at", 0.0)),
            version=int(d.get("version", 1)),
        )

    @staticmethod
    def prompt() -> str:
        """What the user is actually asked. The whole list, not a summary."""
        v = vocabulary()
        return (
            "Help improve Foldok?\n\n"
            "Foldok can send anonymous usage counts so we can see where the tool gets in "
            "your way. It is numbers and fixed codes — never file names, project names, "
            "client names, or anything from your documents.\n\n"
            f"Sent:          {', '.join(v['events'])}\n"
            f"Never sent:    {', '.join(v['never_collected'])}\n\n"
            "You can turn this off at any time, and turning it off deletes what was "
            "collected on this machine."
        )


class EventLog:
    """Local, append-only, content-free. Written whether or not consent was given."""

    def __init__(self, path: str | Path | None = None, clock=time.time) -> None:
        self.path = Path(path) if path else None
        self._events: list[Event] = []
        self._clock = clock
        if self.path and self.path.exists():
            self._events = [
                Event.from_dict(json.loads(line))
                for line in self.path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

    def add(self, event: Event) -> Event:
        self._events.append(event)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        return event

    def events(self, *, name: str | None = None, since: float = 0.0) -> list[Event]:
        return [
            e for e in self._events
            if (name is None or e.name == name) and e.at >= since
        ]

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for e in self._events:
            out[e.name] = out.get(e.name, 0) + 1
        return dict(sorted(out.items()))

    def purge(self) -> int:
        n = len(self._events)
        self._events = []
        if self.path and self.path.exists():
            self.path.unlink()
        return n

    def __len__(self) -> int:
        return len(self._events)


# ----------------------------------------------------------------------
@dataclass
class Funnel:
    stages: dict[str, int] = field(default_factory=dict)
    sessions: int = 0

    @property
    def drop_off(self) -> list[tuple[str, int, float]]:
        """Where people stop. The only number worth acting on right now."""
        out: list[tuple[str, int, float]] = []
        previous = self.stages.get(FUNNEL[0], 0)
        for stage in FUNNEL:
            reached = self.stages.get(stage, 0)
            lost = max(0, previous - reached)
            rate = (lost / previous) if previous else 0.0
            out.append((stage, reached, round(rate, 3)))
            previous = reached
        return out

    @property
    def worst_step(self) -> tuple[str, float] | None:
        candidates = [(s, r) for s, _, r in self.drop_off[1:] if r > 0]
        return max(candidates, key=lambda t: t[1]) if candidates else None

    def report(self) -> str:
        lines = [f"{self.sessions} session(s)"]
        for stage, reached, rate in self.drop_off:
            bar = "#" * min(30, reached)
            lines.append(f"  {FUNNEL_LABELS[stage]:<24} {reached:>4} {bar}"
                         + (f"   -{rate:.0%}" if rate else ""))
        worst = self.worst_step
        if worst:
            lines.append(f"\nBiggest drop: {FUNNEL_LABELS[worst[0]]} ({worst[1]:.0%} lost)")
        return "\n".join(lines)


def funnel(events: Iterable[Event]) -> Funnel:
    """Count a session at a stage once, in order. Reaching stage N implies N-1."""
    per_session: dict[str, set[str]] = {}
    for e in events:
        if e.name in FUNNEL:
            per_session.setdefault(e.session or "_", set()).add(e.name)
    stages = {s: 0 for s in FUNNEL}
    for reached in per_session.values():
        deepest = -1
        for i, stage in enumerate(FUNNEL):
            if stage in reached:
                deepest = i
        for i in range(deepest + 1):
            stages[FUNNEL[i]] += 1
    return Funnel(stages=stages, sessions=len(per_session))


def failure_summary(events: Sequence[Event]) -> dict[str, dict[str, int]]:
    """Errors grouped by reason. The other half of what a solo founder can act on."""
    out: dict[str, dict[str, int]] = {}
    for e in events:
        if e.name not in ("extraction_failed", "call_refused", "layout_overflow",
                          "pack_refused", "blocked_me"):
            continue
        bucket = out.setdefault(e.name, {})
        key = e.codes.get("reason") or e.codes.get("file_type") or "other"
        bucket[key] = bucket.get(key, 0) + 1
    return {k: dict(sorted(v.items(), key=lambda kv: -kv[1])) for k, v in sorted(out.items())}
