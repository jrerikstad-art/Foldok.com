"""Foldok corpus — the folder proposes, the user disposes, the engine orders.

    wide  = extract_many([(source, text), ...])       # 10 more content types
    offer = build_offer(all_claims)                   # no document type named
    offer.drop("sec.hypothesis")                      # the user deletes
    outline = to_outline(offer)                       # narrative order enforced

Naming the document first made a template into a ceiling: a folder with fourteen
topics lost eight of them whichever template was chosen. Naming goes last, and
the document's identity emerges from what the user keeps.
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

__version__ = "0.110.2"
