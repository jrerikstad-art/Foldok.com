"""Foldok intake — the inbound guard.

    kept, report = prepare(index)                     # before mapping
    checked = review(sections, index=..., vault=...)  # after generation

Personal documents stay out of deliverables, relevance is a computed gate rather
than a request to a small model, markdown headings are headings, and the masking
vault is asked whether any real identifier reached the output.
"""

from .classify import (
    EXCLUDED_BY_DEFAULT,
    Classification,
    DocClass,
    IntakeReport,
    classify,
    classify_index,
    filter_index,
)
from .intake import Finding, ReviewReport, prepare, review, sensitive_summary
from .normalise import looks_broken, normalise
from .relevance import (
    DEFAULT_THRESHOLD,
    GateReport,
    Match,
    ProseIssue,
    audit_prose,
    gate,
    score,
)

__all__ = [
    "Classification", "DEFAULT_THRESHOLD", "DocClass", "EXCLUDED_BY_DEFAULT",
    "Finding", "GateReport", "IntakeReport", "Match", "ProseIssue", "ReviewReport",
    "audit_prose", "classify", "classify_index", "filter_index", "gate",
    "looks_broken", "normalise", "prepare", "review", "score", "sensitive_summary",
]

__version__ = "0.84.0"
