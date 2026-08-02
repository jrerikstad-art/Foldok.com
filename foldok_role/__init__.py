"""Foldok role — project material, reference material, and photos that exist.

    roles   = classify_index(index, project_terms=["Dogger", "Bank"])
    patch   = sketch_patch(index, artifact=artifact, project_name=name)
    offers  = offers_for(session.gaps(), index)

Three fixes to three located bugs: a vendor brochure deciding the document's
subject, file sort order naming documents, and the engine reporting a photo
missing while it sits in the folder.
"""

from .classify import (
    ROLE_WEIGHT,
    SCHEMA_VERSION,
    Classification,
    Role,
    RoleReport,
    classify,
    classify_index,
)
from .photos import Candidate, Offer, offers_for, photos_in, rank, summary
from .subject import Subject, decide_subject, sketch_patch, weighted_themes

__all__ = [
    "Candidate", "Classification", "Offer", "ROLE_WEIGHT", "Role", "RoleReport",
    "SCHEMA_VERSION", "Subject", "classify", "classify_index", "decide_subject",
    "offers_for", "photos_in", "rank", "sketch_patch", "summary", "weighted_themes",
]

__version__ = "0.106.1"
