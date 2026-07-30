"""Foldok Ask — question-driven retrieval over the project index.

Documents are compositions of grounded answers, not templates filled from
the full fact graph. Domain YAML packs are optional seasoning, not the brain.
"""

from .ask import ask, ask_many, synthesize_scope
from .compose_brief import compose_topic_brief, default_brief_questions
from .model import Answer, Citation, Gap, GroundClaim, GroundSet, Question, RetrievalHit
from .retrieve import index_to_chunks, retrieve, search
from .suggest import suggest_questions

__all__ = [
    "Answer",
    "Citation",
    "Gap",
    "GroundClaim",
    "GroundSet",
    "Question",
    "RetrievalHit",
    "ask",
    "ask_many",
    "compose_topic_brief",
    "default_brief_questions",
    "index_to_chunks",
    "retrieve",
    "search",
    "suggest_questions",
    "synthesize_scope",
]

__version__ = "0.2.0"
