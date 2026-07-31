"""Foldok console — what is true about the product right now.

    from foldok_console import Console
    print(Console(".").report())
    ok, blockers = Console(".").gate()      # in CI, before a deploy

Aggregates the reports every engine already produces, adds the release checks
that were previously done by hand, and ranks what is worth doing next.
"""

from .console import Console
from .model import Finding, Health, Panel, Snapshot, merge
from .probes import (
    ENGINES,
    probe_assets,
    probe_capabilities,
    probe_engines,
    probe_index,
    probe_learning,
    probe_shredder,
    probe_signals,
    probe_tests,
    probe_trust,
)
from .release import check_release

__all__ = [
    "Console", "ENGINES", "Finding", "Health", "Panel", "Snapshot", "check_release",
    "merge", "probe_assets", "probe_capabilities", "probe_engines", "probe_index", "probe_learning",
    "probe_shredder", "probe_signals", "probe_tests", "probe_trust",
]

__version__ = "0.80.0"
