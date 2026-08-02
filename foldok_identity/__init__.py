"""Project identity — what the document is *about* before sections are offered.

Corpus → Project Identity → Narrative Blueprint → Topics → Sections → Author

Without identity, a dense vendor PDF out-votes the project's own notes and the
document becomes a product manual. Identity is not a filename and not a template
name: it is purpose, audience, primary vs secondary subjects, and an excluded set.

Hard rule: no real project, client, or vendor names in this package. Terms come
from the artifact and folder the user already named.
"""

from .blueprint import (
    SCHEMA_VERSION,
    NarrativeBlueprint,
    ProjectIdentity,
    Relevance,
    identify_project,
    score_offer,
    score_topic,
)

__all__ = [
    "SCHEMA_VERSION",
    "NarrativeBlueprint",
    "ProjectIdentity",
    "Relevance",
    "identify_project",
    "score_offer",
    "score_topic",
]

__version__ = "0.112.0"
