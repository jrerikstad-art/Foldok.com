"""Foldok Ask — knowledge → narrative → author → evidence.

Documents are engineering stories with citations, not fact dumps.
Narrative decides the argument; Author writes; Validator binds proof.
"""

from .ask import ask, ask_many, synthesize_scope
from .author_doc import author_document
from .compose_brief import compose_topic_brief, default_brief_questions, render_brief_markdown
from .critic import CriticReport, review_document
from .lead import LeadControls, LeadResult, generate_lead
from .model import Answer, Citation, Gap, GroundClaim, GroundSet, Question, RetrievalHit
from .narrative import (
    DocumentIntent,
    NarrativeBlueprint,
    NarrativePlan,
    plan_blueprint,
    plan_narrative,
    propose_arc_expansion,
)
from .plan import corpus_sketch, plan_document
from .retrieve import index_to_chunks, retrieve, search
from .suggest import suggest_questions

__all__ = [
    "Answer",
    "Citation",
    "CriticReport",
    "DocumentIntent",
    "Gap",
    "GroundClaim",
    "GroundSet",
    "LeadControls",
    "LeadResult",
    "NarrativeBlueprint",
    "NarrativePlan",
    "Question",
    "RetrievalHit",
    "ask",
    "ask_many",
    "author_document",
    "compose_topic_brief",
    "corpus_sketch",
    "default_brief_questions",
    "generate_lead",
    "index_to_chunks",
    "plan_blueprint",
    "plan_document",
    "plan_narrative",
    "propose_arc_expansion",
    "render_brief_markdown",
    "retrieve",
    "review_document",
    "search",
    "suggest_questions",
    "synthesize_scope",
]

__version__ = "0.6.0"
