"""Generic, domain-neutral evidence engine.

The core intentionally knows nothing about Foldok, tax, payroll, engineering,
or any other product domain. Products provide domain packs and storage/runtime
adapters around these primitives.
"""

from .model import (
    CandidateFact,
    CanonicalFact,
    EvidenceDocument,
    Observation,
    SourceLocation,
    ValidationIssue,
)
from .contracts import DomainPack, EvidenceExtractor, EvidenceValidator
from .engine import EvidenceEngine, EngineResult

__all__ = [
    "CandidateFact",
    "CanonicalFact",
    "DomainPack",
    "EngineResult",
    "EvidenceDocument",
    "EvidenceEngine",
    "EvidenceExtractor",
    "EvidenceValidator",
    "Observation",
    "SourceLocation",
    "ValidationIssue",
]
