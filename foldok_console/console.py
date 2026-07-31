"""The console facade.

    console = Console(root=".")
    print(console.snapshot().report())

One call, one page, and a queue of decisions rather than a wall of metrics.
Tests are opt-in because they are slow, and a dashboard that takes thirty
seconds is a dashboard you stop opening.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .model import Panel, Snapshot, merge
from .probes import (
    probe_assets,
    probe_capabilities,
    probe_engines,
    probe_index,
    probe_learning,
    probe_signals,
    probe_shredder,
    probe_tests,
    probe_trust,
)
from .release import check_release


class Console:
    def __init__(
        self,
        root: str | Path = ".",
        *,
        index_db: str | Path | None = None,
        events: str | Path | None = None,
        audit: str | Path | None = None,
        lessons: str | Path | None = None,
        shreds: str | Path | None = None,
    ) -> None:
        self.root = Path(root)
        self.index_db = index_db
        self.events = events
        self.audit = audit
        self.lessons = lessons
        self.shreds = shreds

    def version(self) -> str:
        p = self.root / "VERSION"
        return p.read_text(encoding="utf-8").strip() if p.exists() else ""

    def snapshot(self, *, with_tests: bool = False) -> Snapshot:
        panels: list[Panel] = [
            probe_engines(self.root),
            check_release(self.root),
            probe_capabilities(self.root),
            probe_assets(self.root),
            probe_index(self.root, self.index_db),
            probe_trust(self.audit),
            probe_signals(self.events),
            probe_learning(self.lessons),
            probe_shredder(self.shreds),
        ]
        if with_tests:
            panels.append(probe_tests(self.root))
        return merge(panels, version=self.version(), root=str(self.root))

    def report(self, *, with_tests: bool = False) -> str:
        return self.snapshot(with_tests=with_tests).report()

    def json(self, *, with_tests: bool = False, indent: int = 2) -> str:
        return self.snapshot(with_tests=with_tests).to_json(indent=indent)

    def gate(self, *, with_tests: bool = True) -> tuple[bool, list[str]]:
        """Ship or not. Call this in CI before a deploy."""
        snap = self.snapshot(with_tests=with_tests)
        blockers = [f"{f.area}: {f.title}" for f in snap.findings(health="fail")]
        return (not blockers, blockers)
