"""Foldok budget — citation scope, claim budgets, and pipeline health.

    scope = CiteScope()
    scope.enter_section("shielding")     # per section, not per document
    scope.may_cite(file_id)

    print(check_pipeline(...).report())  # where the document went thin, and why

Fixes the blocker that kept every document thin: a document-wide one-claim-per-
file rule that discarded 95% of what the engines produced, silently.
"""

from .pipeline import (
    PipelineReport,
    StageResult,
    YIELD_FLOOR,
    check_pipeline,
)
from .registry import (
    DOCUMENT_SHARE_DEFAULT,
    PER_SECTION_DEFAULT,
    SCHEMA_VERSION,
    CiteScope,
    rank_key,
    section_budget,
)

__all__ = [
    "CiteScope", "DOCUMENT_SHARE_DEFAULT", "PER_SECTION_DEFAULT", "PipelineReport",
    "SCHEMA_VERSION", "StageResult", "YIELD_FLOOR", "check_pipeline", "rank_key",
    "section_budget",
]

__version__ = "0.109.0"
