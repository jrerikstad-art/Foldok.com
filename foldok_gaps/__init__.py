"""Foldok completion engine — from "30 mangler" to a finished document.

    document + requirement pack
        -> evaluate()          gaps, as objects with stable ids
        -> options(gap)        what Foldok can offer for this one
        -> resolve(gap)        an artifact, or an empty form, or a signed N/A
        -> gate()              can this be exported, and as what

Two rules hold the whole thing together:

*  Evaluation is pure, so compliance is a view over the document rather than a
   decision taken on day one.
*  A model may draft what someone intends and never author what someone
   observed.  Enforced in resolvers.py, not in a prompt.
"""

from .completion import CompletionSession, Offer
from .document import Artifact, Document, Entry, Provenance, Subject
from .gaps import Batch, Gap, GapSet, Notice, diff, evaluate, gap_id
from .packs import PACKS
from .policy import BUILD, COMPLIANCE, MODES, REVIEW, Gate, Mode, gate, progress
from .requirements import (
    FOLDOK_SPINE,
    FormField,
    Requirement,
    RequirementPack,
    Section,
    matches,
)
from .resolvers import (
    Drafter,
    EvidentialGuard,
    Resolution,
    Resolver,
    ResolverRefused,
    ResolverRegistry,
    default_registry,
)

__all__ = [
    "Artifact",
    "BUILD",
    "Batch",
    "COMPLIANCE",
    "CompletionSession",
    "Document",
    "Drafter",
    "Entry",
    "EvidentialGuard",
    "FOLDOK_SPINE",
    "FormField",
    "Gap",
    "GapSet",
    "Gate",
    "MODES",
    "Mode",
    "Notice",
    "Offer",
    "PACKS",
    "Provenance",
    "REVIEW",
    "Requirement",
    "RequirementPack",
    "Resolution",
    "Resolver",
    "ResolverRefused",
    "ResolverRegistry",
    "Section",
    "Subject",
    "default_registry",
    "diff",
    "evaluate",
    "gap_id",
    "gate",
    "matches",
    "progress",
]

__version__ = "0.64.0"
