"""Foldok corpus — the folder proposes, the user disposes, the engine orders.

    from foldok_identity import identify_project
    blueprint = identify_project(artifact=art, themes=project_themes, ...)
    wide  = extract_many([(source, text), ...])
    offer = build_offer(all_claims, identity=blueprint)  # scored vs identity
    offer.drop("sec.hypothesis")
    outline = to_outline(offer)

Identity first (see PROJECT_IDENTITY.md). Naming the document *label* goes last.
"""

from .integrate import (
    compile_document_corpus_md,
    docs_from_index,
    headings_in,
    inject_corpus_appendix,
)
from .market import (
    BAND,
    MIN_SOURCES,
    MIN_WEIGHT,
    SCHEMA_VERSION,
    CorpusOffer,
    Offer,
    build_offer,
    check_order,
    compare_documents,
    to_outline,
)
from .widen import (
    FEEDS_SECTION,
    WideClaim,
    WideExtraction,
    WideType,
    extract_many,
    extract_wide,
)

__all__ = [
    "BAND", "CorpusOffer", "FEEDS_SECTION", "MIN_SOURCES", "MIN_WEIGHT", "Offer",
    "SCHEMA_VERSION", "WideClaim", "WideExtraction", "WideType", "build_offer",
    "check_order", "compare_documents", "compile_document_corpus_md",
    "docs_from_index", "extract_many", "extract_wide", "headings_in",
    "inject_corpus_appendix", "to_outline",
]

__version__ = "0.112.0"
