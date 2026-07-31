"""Foldok claims — engineering knowledge is mostly not quantities.

    claims = extract_many([(source_id, text), ...])
    print(check(claims).report())

Built because a folder of EMC standards yielded eight facts under a
(key, value, unit) schema, while the same folder contains a six-class taxonomy,
conditional rules, three hypotheses and five risks. None of those fit in a
quantity, so none of them survived extraction.

Coherence is the part free synthesis cannot do: a summary reconciles by
construction, so disagreements dissolve into it. Claims held apart — with their
sources, modalities and scopes — can be compared.
"""

from .coherence import CoherenceReport, Finding, check
from .integrate import (
    IndexedClaims,
    apply_ranking_patch,
    as_chunks,
    claims_from_index,
    coherence_section,
    register_markdown,
    standards_register,
)
from .extract import Extraction, extract, extract_many
from .model import (
    BINDING,
    SCHEMA_VERSION,
    Claim,
    ClaimSet,
    ClaimType,
    Modality,
    Quantity,
    Scope,
    claim_id,
)

__all__ = [
    "BINDING", "Claim", "ClaimSet", "ClaimType", "CoherenceReport", "Extraction",
    "Finding", "IndexedClaims", "Modality", "Quantity", "SCHEMA_VERSION", "Scope",
    "apply_ranking_patch", "as_chunks", "check", "claim_id", "claims_from_index",
    "coherence_section", "extract", "extract_many", "register_markdown",
    "standards_register",
]

__version__ = "0.88.0"
