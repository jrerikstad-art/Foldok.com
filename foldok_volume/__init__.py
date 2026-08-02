"""Foldok volume — document length decided by the corpus, not by a template.

    report  = analyse(claims, outline)
    outline = widen(outline, report)          # + a section per uncovered theme
    budget  = claim_budget(len(claims), len(outline))   # replaces limit=6

Hundreds of pages produced three, because 6-7 fixed sections x 6 claims is
about forty claims whatever the folder holds. Sections now come from material
the outline has nowhere to put, each carrying its evidence so deleting is an
informed choice.
"""

from .coverage import (
    MIN_EVIDENCE,
    MIN_SOURCES,
    SCHEMA_VERSION,
    CoverageReport,
    Evidence,
    ProposedSection,
    analyse,
    claim_budget,
    themes_of_corpus,
    widen,
)

__all__ = [
    "CoverageReport", "Evidence", "MIN_EVIDENCE", "MIN_SOURCES", "ProposedSection",
    "SCHEMA_VERSION", "analyse", "claim_budget", "themes_of_corpus", "widen",
]

__version__ = "0.108.0"
