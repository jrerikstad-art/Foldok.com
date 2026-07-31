"""The operator console — what is true about Foldok right now.

Not a SaaS admin panel.  Those exist to watch users, and there are not any yet.
This exists because the thing that actually went wrong over the last five builds
was invisible: two release blockers survived from 0.73 to 0.78 untouched, and
were found by reading files by hand rather than by anything in the product.

So the console has two jobs, and the second one matters more:

**Report state.**  Every engine already produces a report — assets, index
diagnostics, gap counts, private-call audit, signals funnel, learning proposals.
The console aggregates; it does not compute anything new.  Nothing here is a
subsystem, which is why it is cheap and why it will not rot.

**Rank decisions.**  A wall of metrics is something to look at.  A queue of
decisions is something to do.  Every finding carries evidence, an effort
estimate and a suggested action, and the queue sorts by what would change most
per hour spent.  At this stage the useful output is not "here are your numbers",
it is "these three things are worth your Tuesday".
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal

SCHEMA_VERSION = 1

Health = Literal["ok", "warn", "fail", "unknown"]
Effort = Literal["minutes", "hours", "days"]

HEALTH_RANK: dict[str, int] = {"ok": 0, "unknown": 1, "warn": 2, "fail": 3}
EFFORT_HOURS: dict[str, float] = {"minutes": 0.25, "hours": 4.0, "days": 24.0}


@dataclass
class Finding:
    """Something true that may deserve an action."""

    code: str
    title: str
    health: Health = "warn"
    detail: str = ""
    action: str = ""                    # what to do about it
    effort: Effort = "hours"
    impact: int = 2                     # 1 cosmetic .. 5 blocks a customer
    evidence: dict[str, Any] = field(default_factory=dict)
    area: str = ""

    @property
    def value_per_hour(self) -> float:
        """Crude on purpose. The ranking only has to beat reading a list."""
        weight = {"fail": 3.0, "warn": 1.5, "ok": 0.2, "unknown": 0.5}[self.health]
        return round((self.impact * weight) / EFFORT_HOURS[self.effort], 2)

    def to_dict(self) -> dict[str, Any]:
        d = {
            "code": self.code,
            "title": self.title,
            "health": self.health,
            "area": self.area,
            "impact": self.impact,
            "effort": self.effort,
            "score": self.value_per_hour,
        }
        if self.detail:
            d["detail"] = self.detail
        if self.action:
            d["action"] = self.action
        if self.evidence:
            d["evidence"] = self.evidence
        return d

    def __str__(self) -> str:
        mark = {"ok": " ok ", "warn": "warn", "fail": "FAIL", "unknown": " ?  "}[self.health]
        line = f"[{mark}] {self.title}"
        if self.detail:
            line += f"\n         {self.detail}"
        if self.action:
            line += f"\n         -> {self.action} ({self.effort})"
        return line


@dataclass
class Panel:
    """One area of the system: an engine, the release, the content library."""

    area: str
    title: str
    health: Health = "unknown"
    metrics: dict[str, Any] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    note: str = ""

    def add(
        self,
        code: str,
        title: str,
        *,
        health: Health = "warn",
        detail: str = "",
        action: str = "",
        effort: Effort = "hours",
        impact: int = 2,
        evidence: dict[str, Any] | None = None,
    ) -> Finding:
        f = Finding(
            code=code, title=title, health=health, detail=detail, action=action,
            effort=effort, impact=impact, evidence=evidence or {}, area=self.area,
        )
        self.findings.append(f)
        if HEALTH_RANK[health] > HEALTH_RANK[self.health]:
            self.health = health
        return f

    def settle(self) -> "Panel":
        """A panel with no findings is healthy, not unknown."""
        if not self.findings and self.health == "unknown":
            self.health = "ok"
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "area": self.area,
            "title": self.title,
            "health": self.health,
            "metrics": self.metrics,
            "note": self.note,
            "findings": [f.to_dict() for f in self.findings],
        }

    def __str__(self) -> str:
        head = f"{self.title}  [{self.health}]"
        bits = "  ".join(f"{k}={v}" for k, v in self.metrics.items())
        lines = [head] + ([f"  {bits}"] if bits else [])
        lines += [f"  {line}" for f in self.findings for line in str(f).splitlines()]
        return "\n".join(lines)


@dataclass
class Snapshot:
    panels: list[Panel] = field(default_factory=list)
    at: float = field(default_factory=time.time)
    version: str = ""
    root: str = ""

    @property
    def health(self) -> Health:
        if not self.panels:
            return "unknown"
        return max((p.health for p in self.panels), key=lambda h: HEALTH_RANK[h])

    def panel(self, area: str) -> Panel | None:
        for p in self.panels:
            if p.area == area:
                return p
        return None

    def findings(self, *, health: Health | None = None) -> list[Finding]:
        out = [f for p in self.panels for f in p.findings]
        if health:
            out = [f for f in out if f.health == health]
        return out

    def decisions(self, limit: int = 8) -> list[Finding]:
        """The queue. Ranked by what would change most per hour spent."""
        ranked = [f for f in self.findings() if f.health in ("fail", "warn")]
        ranked.sort(key=lambda f: (-f.value_per_hour, -f.impact, f.code))
        return ranked[:limit]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "at": round(self.at, 3),
            "version": self.version,
            "root": self.root,
            "health": self.health,
            "panels": [p.to_dict() for p in self.panels],
            "decisions": [f.to_dict() for f in self.decisions()],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def report(self, *, width: int = 74) -> str:
        rule = "-" * width
        lines = [
            f"FOLDOK CONSOLE  v{self.version or '?'}  [{self.health.upper()}]",
            rule,
        ]
        for panel in self.panels:
            lines.append(str(panel))
            lines.append("")
        decisions = self.decisions()
        lines.append(rule)
        if not decisions:
            lines.append("Nothing needs a decision. Go and talk to a customer.")
            return "\n".join(lines)
        lines.append("WORTH YOUR TUESDAY")
        for i, f in enumerate(decisions, start=1):
            lines.append(f"  {i}. {f.title}  [{f.area}, {f.effort}, score {f.value_per_hour}]")
            if f.action:
                lines.append(f"     {f.action}")
        return "\n".join(lines)


def merge(panels: Iterable[Panel], *, version: str = "", root: str = "", clock=time.time) -> Snapshot:
    return Snapshot(
        panels=[p.settle() for p in panels], at=clock(), version=version, root=root
    )
