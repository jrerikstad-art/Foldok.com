"""Generic Evidence Engine.

Project-agnostic primitives for turning source material into observations,
candidate facts, validated canonical facts, and traceable provenance.

The core intentionally contains no Foldok, tax, payroll, engineering, or other
product/domain vocabulary. Domain semantics live in DomainPack implementations.
"""

from .model import (
    CandidateFact,
    CanonicalFact,
    DocumentRef,
    EvidenceState,
    Observation,
    SourceLocation,
    ValidationIssue,
    ValidationResult,
)
from .contracts import DomainPack, Extractor, Validator
from .pipeline import EvidenceEngine, EngineResult

__all__ = [
    "CandidateFact",
    "CanonicalFact",
    "DocumentRef",
    "DomainPack",
    "EngineResult",
    "EvidenceEngine",
    "EvidenceState",
    "Extractor",
    "Observation",
    "SourceLocation",
    "ValidationIssue",
    "ValidationResult",
    "Validator",
]
