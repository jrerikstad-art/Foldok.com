"""Foldok tier — strong, candidate, rejected.

    report = tier_sentences(sentences, source=..., strong_ids=claims, topics=topics)
    chosen = fill_section(report, section_terms=[...], want=6)

Four sentences in five were being discarded silently by pattern matching. The
patterns were doing the only relevance work in the pipeline, so removing them
fills a document with page footers. Tiering keeps the filtering and lets
descriptive prose through where a section would otherwise be empty.
"""

from .tier import (
    MAX_WORDS,
    MIN_WORDS,
    SCHEMA_VERSION,
    SECTION_TERMS,
    Tier,
    TierReport,
    TieredSentence,
    compare,
    fill_section,
    section_terms,
    tier_sentences,
)
from .integrate import (
    candidate_chunks,
    tier_from_prose,
    tier_report_from_index,
)

__all__ = [
    "MAX_WORDS", "MIN_WORDS", "SCHEMA_VERSION", "SECTION_TERMS", "Tier",
    "TierReport", "TieredSentence", "candidate_chunks", "compare",
    "fill_section", "section_terms", "tier_from_prose",
    "tier_report_from_index", "tier_sentences",
]

__version__ = "0.114.8"
