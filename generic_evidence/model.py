from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class SourceLocation:
    """Trace from evidence back to its source without domain semantics."""

    document_id: str
    page: int | None = None
    section: str | None = None
    block_id: str | None = None
    bbox: tuple[float, float, float, float] | None = None
    text: str | None = None


@dataclass(frozen=True)
class Observation:
    """A source-grounded observation before domain interpretation."""

    label: str
    value: Any
    unit: str | None = None
    dimensions: Mapping[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source: SourceLocation | None = None
    extractor: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CandidateFact:
    """A domain pack's proposed interpretation of one or more observations."""

    fact_type: str
    value: Any
    unit: str | None = None
    observation_indexes: tuple[int, ...] = ()
    confidence: float = 1.0
    dimensions: Mapping[str, Any] = field(default_factory=dict)
    rationale: str | None = None


@dataclass(frozen=True)
class CanonicalFact:
    """A validated fact safe for downstream deterministic consumers."""

    fact_type: str
    value: Any
    unit: str | None = None
    dimensions: Mapping[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    evidence: Sequence[SourceLocation] = field(default_factory=tuple)
    status: str = "accepted"


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: str = "error"
    observation_indexes: tuple[int, ...] = ()
    fact_types: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidenceDocument:
    document_id: str
    media_type: str
    content_hash: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
