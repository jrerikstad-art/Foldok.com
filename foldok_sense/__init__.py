"""Foldok sense — make sense of this folder.

    passages = passages_from(tier_report, role="project")
    draft = assemble(passages, figures=figures, expected=["installation"])
    print(draft.markdown())

    # Full chain (what generate must call):
    python -m foldok_sense.audit /path/to/folder --out draft.md

Names nothing in advance. Topics come from what recurs across sources, figures
land in the topic their caption matches, and anything the folder does not cover
is reported as a finding rather than rendered as an empty heading.
"""

from .assemble import (
    MIN_SENTENCES,
    MIN_SOURCES,
    SCHEMA_VERSION,
    Draft,
    Group,
    Passage,
    assemble,
    discover_topics,
    passages_from,
)
from .audit import AuditResult, audit
from .integrate import sense_from_folder, sense_from_index, sense_markdown

__all__ = [
    "AuditResult", "Draft", "Group", "MIN_SENTENCES", "MIN_SOURCES", "Passage",
    "SCHEMA_VERSION", "assemble", "audit", "discover_topics", "passages_from",
    "sense_from_folder", "sense_from_index", "sense_markdown",
]

__version__ = "0.114.10"
