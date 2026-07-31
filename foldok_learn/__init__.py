"""Foldok local learning — Tier 1 only. Nothing leaves this machine.

    learner.observe_layout(session, document_id=...)      confirmed hand edits
    learner.observe_resolvers(session, document_id=...)   how gaps actually close
    learner.observe_standard(text, standard="NEK 400")    citations, never text
    learner.proposals()                                   what it noticed
    learner.accept(id) / revert(id)                       always reversible

Everything produced is born local_only and reference_only, so foldok_assets
refuses to package it. Cross-user sharing is a separate deliberate build with
consent, sanitising and a licence — not a flag in here.
"""

from .learner import Learner, Proposal
from .model import (
    THRESHOLDS,
    ClauseFinding,
    Evidence,
    Lesson,
    SharingRefused,
    assert_local_only,
    lesson_id,
    to_jsonl,
)
from .standards import Extraction, extract, extract_from_chunks, to_requirements

__all__ = [
    "ClauseFinding", "Evidence", "Extraction", "Learner", "Lesson", "Proposal",
    "SharingRefused", "THRESHOLDS", "assert_local_only", "extract",
    "extract_from_chunks", "lesson_id", "to_jsonl", "to_requirements",
]

__version__ = "0.79.0"
